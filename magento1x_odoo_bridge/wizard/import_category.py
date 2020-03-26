# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
from  xmlrpc.client import Error
import logging
import itertools
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, _
from odoo.addons.magento1x_odoo_bridge.tools.const import CHANNELDOMAIN
CategoryInfoFields = [
]
Boolean = [

    ('all', 'True/False'),
    ('1', 'True'),
    ('0', 'False'),
]
Source = [
    ('all', 'All'),
    ('parent_categ_id', 'Parent ID'),
]


class ImportMagento1xCategories(models.TransientModel):
    _inherit = ['import.categories']
    _name = "import.magento1x.categories"
    @api.model
    def _get_parent_categ_domain(self):
        res = self._get_ecom_store_domain()
        return res

    source = fields.Selection(Source, required=1, default='all')
    parent_categ_id = fields.Many2one(
        'channel.category.mappings',
        'Parent Category',
        domain = _get_parent_categ_domain
    )

    def _fetch_magento1x_categories(self,session, client):
        message=''
        data= None
        args = []
        if not self.source=='all':
            args+=[self.parent_categ_id.store_category_id]
        try:
            data=  client.call(session, 'category.tree',args)
        except Error as e:
            e =str(e).strip('<').strip('>')
            message+='<br/>%s'%(e)
        except Exception as e:
            message+='<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )

    def _magento1x_update_category_feed(self,mapping,category_id,vals):
        mapping.write(vals)
        mapping.state='update'
        return mapping

    def _magento1x_create_category_feed(self, category_id, vals,channel_id):
        feed_obj = self.env['category.feed']
        feed_id = channel_id._create_feed(feed_obj, vals)
        return feed_id

    def _magento1x_import_category(self, category_id, data,channel_id):
        feed_obj = self.env['category.feed']
        match = channel_id._match_feed(
            feed_obj, [('store_id', '=', category_id)])
        update =False
        if match:
            self._magento1x_update_category_feed(match, category_id, data)
            update =True
        else:
            match= self._magento1x_create_category_feed( category_id, data,channel_id)
        return dict(
            feed_id=match,
            update=update
        )
    def magento1x_extract_categ_data(self,data):
        parent_id = data.get('parent_id')
        return [(
            data.get('category_id'),
            dict(
            name=data.get('name'),
            store_id=data.get('category_id'),
            parent_id=parent_id not in ['0',0,None,False] and parent_id
            )
        )]
    def magento1x_get_product_categ_data(self,data):
        res=[]
        child =len(data.get('children'))
        index = 0
        while len(data.get('children'))>0:
            item = data.get('children')[index]
            res +=self.magento1x_get_product_categ_data(item)
            res+=self.magento1x_extract_categ_data(data.get('children').pop(index))
        return res
    def _magento1x_import_categories(self,items,channel_id):
        create_ids=[]
        update_ids=[]
        categ_items=dict(self.magento1x_get_product_categ_data(items)+self.magento1x_extract_categ_data(items))
        for category_id,item in categ_items.items():
            import_res =   self._magento1x_import_category(category_id, item,channel_id)
            feed_id = import_res.get('feed_id')
            if  import_res.get('update'):
                update_ids.append(feed_id)
            else:
                create_ids.append(feed_id)
        return dict(
            create_ids=create_ids,
            update_ids=update_ids,
        )


    @api.multi
    def import_now(self):
        create_ids,update_ids,map_create_ids,map_update_ids=[],[],[],[]
        message=''
        feed_obj = self.env['category.feed']
        for record in self:
            channel_id = record.channel_id
            res =channel_id.get_magento1x_session()
            session = res.get('session')
            client = res.get('client')
            if not session:
                message+=res.get('message')
            else:
                fetch_res =record._fetch_magento1x_categories(session=session,client=client)
                categories = fetch_res.get('data', {})
                message+= fetch_res.get('message','')
                if not categories:
                    message+="Category data not received."
                else:
                    feed_res=record._magento1x_import_categories(categories,channel_id)
                    post_res = self.post_feed_import_process(channel_id,feed_res)
                    create_ids+=post_res.get('create_ids')
                    update_ids+=post_res.get('update_ids')
                    map_create_ids+=post_res.get('map_create_ids')
                    map_update_ids+=post_res.get('map_update_ids')
        message+=self.env['multi.channel.sale'].get_feed_import_message(
            'category',create_ids,update_ids,map_create_ids,map_update_ids
        )
        return self.env['multi.channel.sale'].display_message(message)

    @api.model
    def _cron_magento1x_import_categories(self):
        for channel_id in self.env['multi.channel.sale'].search(CHANNELDOMAIN):
            vals =dict(
                channel_id=channel_id.id,
                source='all',
                operation= 'import',
            )
            obj=self.create(vals)
            obj.import_now()
