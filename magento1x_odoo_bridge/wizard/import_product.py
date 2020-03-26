# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, _
from odoo.addons.odoo_multi_channel_sale.tools import MapId
from odoo.addons.magento1x_odoo_bridge.tools.const import InfoFields,CHANNELDOMAIN
from odoo.addons.odoo_multi_channel_sale.tools import chunks, ensure_string as ES

from odoo.exceptions import  UserError,RedirectWarning, ValidationError
Status = [
    ('all', 'All'),
    ('1', 'True'),
    ('0', 'False'),
]
Type  =[
    ('all','All (Exclude Configurable Product)'),
    ('simple','Simple Product'),
    ('downloadable','Downloadable Product'),
    ('grouped','Grouped Product'),
    ('virtual','Virtual Product'),
    ('bundle','Bundle Product'),
]
OdooType = [
    ('simple','product'),
    ('downloadable','service'),#digital
    ('grouped','service'),
    ('virtual','service'),
    ('bundle','service'),
]

class Importmagento1xProducts(models.TransientModel):
    _inherit = ['import.templates']
    _name = "import.magento1x.products"
    status =  fields.Selection(Status, required=1, default='all')
    type = fields.Selection(Type, required=1, default='all')

    @staticmethod
    def get_product_vals(channel_id,product_data,qty_available,**kwargs ):
        product_id = product_data.get('product_id')
        category_ids=product_data.get('category_ids',[])
        extra_categ_ids =','.join(category_ids)
        vals = dict(
            name=product_data.get('name'),
            default_code=product_data.get('sku'),
            type = dict(OdooType).get(product_data.get('type'),'service'),
            store_id=product_id,
            qty_available=qty_available,
            extra_categ_ids=extra_categ_ids,
        )
        res = channel_id._fetch_magento1x_product_data(product_id=product_id,channel_id=channel_id,**kwargs)
        data = res.get('data')
        if data:
            vals['name'] =data.get('name')
            vals['description_sale'] =data.get('description')
            vals['weight'] =data.get('weight')
            vals['list_price'] =data.get('price')
            vals['standard_price'] =data.get('cost')
            media = data.get('media',{})
            if len(media.get('media',[])):
                res_img= channel_id._magento1x_get_product_images_vals(media)
                # vals['image'] = res_img.get('image')
                vals['image_url'] = res_img.get('image_url')
        return vals

    @staticmethod
    def _magento1x_update_product_feed(match,vals):
        vals['state']='update'
        match.write(dict(feed_variants=[(5,0,0)]))
        return match.write(vals)

    @staticmethod
    def _magento1x_create_product_feed(channel_id,product_id,feed_obj,vals):
        vals['store_id'] =product_id
        feed_id = channel_id._create_feed(feed_obj, vals)
        return feed_id

    def _magento1x_create_product_categories(self,channel_id,data,**kwargs):
        category_ids= data.get('category_ids')
        mapping_obj = self.env['channel.category.mappings']
        domain = [('store_category_id', 'in',category_ids)]
        mapped = channel_id._match_mapping(mapping_obj,domain).mapped('store_category_id')
        category_ids=list(set(category_ids)-set(mapped))
        if len(category_ids):
            message='For order category imported %s'%(category_ids)
            _logger.info("item===%r==="%(message))
            try:
                import_category_obj=self.env['import.magento1x.categories']
                vals =dict(
                    channel_id=channel_id.id,
                    source='all',
                    operation= 'import',
                )
                import_category_id=import_category_obj.create(vals)
                import_category_id.import_now()
            except Exception as e:
                message = "Error while  order product import %s"%(e)

    def _magento1x_import_product(self, channel_id, product_id, data, qty_available,**kwargs):
        feed_obj = self.env['product.feed']
        match = channel_id._match_feed(
            feed_obj, [('store_id', '=', product_id)],limit=1)
        update=False
        vals =self.get_product_vals(
            channel_id=channel_id,product_data=data,
            qty_available=qty_available,**kwargs
        )
        if match:
            self._magento1x_create_product_categories(channel_id=channel_id,data=data)
            update=self._magento1x_update_product_feed(match=match,  vals=vals)
        else:
            self._magento1x_create_product_categories(channel_id=channel_id,data=data)
            match= self._magento1x_create_product_feed(
                channel_id=channel_id,feed_obj=feed_obj,
                product_id=product_id,vals=vals
            )
        return dict(
            feed_id=match,
            update=update
        )
    def _get_mage1x_qty_data(self,channel_id,items,**kwargs):
        store_product_ids =[ str(item.get('product_id')) for item in items]
        operation = self.operation
        match_store_product_ids = []
        product_ids = []
        if operation=='import':
            domain= [('store_product_id','in',store_product_ids)]
            match_store_product_ids = channel_id.match_product_mappings(domain=domain,limit=None).mapped('store_product_id')
            if len(match_store_product_ids):
                store_product_ids = set(store_product_ids)-set(match_store_product_ids)
        else:
            domain= [('store_product_id','not in',store_product_ids)]
            match_store_product_ids = channel_id.match_product_mappings(domain=domain,limit=None).mapped('store_product_id')
            if len(match_store_product_ids):
                store_product_ids = set(store_product_ids)-set(match_store_product_ids)
        qty_data = channel_id._fetch_magento1x_qty_data(product_ids=list(set(store_product_ids)),**kwargs)
        return qty_data
    def _magento1x_import_products(self,channel_id,items,condition_type,**kwargs):
        create_ids=[]
        update_ids=[]
        message =''
        qty_data = self._get_mage1x_qty_data(channel_id,items,**kwargs)
        for item in items:

            product_id = item.get('product_id')
            _logger.info("item===%r==="%(product_id))

            qty_available =qty_data.get(product_id)
            import_res =   self._magento1x_import_product(
                channel_id=channel_id,  product_id=product_id, data=item,
                qty_available=qty_available,**kwargs
            )
            feed_id = import_res.get('feed_id')
            _logger.info("item===%r==="%(feed_id))

            if  import_res.get('update'):
                update_ids.append(feed_id)
            else:
                create_ids.append(feed_id)
        return dict(
            create_ids=create_ids,
            update_ids=update_ids,
            message=message,
        )
    def _get_magento1x_import_products(self,record,channel_id,**kwargs):
        message=''
        store_product_ids=''
        product_tmpl_ids = record.product_tmpl_ids
        condition_type = 'nin' if record.operation=='import' else 'in'
        if self._context.get('condition_type'):
            condition_type = condition_type
        if not product_tmpl_ids:
            match = channel_id.match_product_mappings(limit=None)
            if match:
                store_product_ids =','.join(map(str,match.mapped('store_product_id')))
        fetch_res = channel_id._fetch_magento1x_products(
            product_tmpl_ids=store_product_ids,
            condition_type = condition_type,
            channel_id=channel_id,
            from_date =  record.operation=='import'  and self._context.get('get_date',1) and record.import_product_date,
            to_date =  record.operation=='import'  and self._context.get('get_date',1) and record.to_date,
            **kwargs
        )
        items = fetch_res.get('data') or []
        if not items:
            message+=fetch_res.get('message')
        return dict(item_ids=items,message=message)
    @api.multi
    def import_now(self):
        create_ids,update_ids,map_create_ids,map_update_ids =[],[],[],[]
        message=''
        for record in self:
            channel_id = record.channel_id
            debug = channel_id.debug=='enable'

            res =channel_id.get_magento1x_session()
            if not res.get('session'):
                message+=res.pop('message')
            else:
                product_ids_res = record._get_magento1x_import_products(record,channel_id,**res)
                item_ids = product_ids_res.get('item_ids')
                message+=product_ids_res.get('message')
                if len(item_ids):
                    _logger.info("item_ids===%r==="%(len(item_ids)))
                    for item_chuncks in chunks(item_ids,self.api_record_limit):
                        if debug:
                            _logger.info("item_chuncks===%r==="%(len(item_chuncks)))
                        feed_res = self._magento1x_import_products(
                            channel_id,item_chuncks,'in',**res)
                        message +=res.get('message')
                        post_res = self.post_feed_import_process(channel_id,feed_res)
                        create_ids+=post_res.get('create_ids')
                        update_ids+=post_res.get('update_ids')
                        map_create_ids+=post_res.get('map_create_ids')
                        map_update_ids+=post_res.get('map_update_ids')
                        if len(create_ids):channel_id.set_channel_date('import','product')
                        if len(update_ids):channel_id.set_channel_date('update','product')
                        self._cr.commit()

        message+=self.env['multi.channel.sale'].get_feed_import_message(
            'product',create_ids,update_ids,map_create_ids,map_update_ids
        )
        return self.env['multi.channel.sale'].display_message(message)
    @api.model
    def _cron_magento1x_import_products(self):
        for channel_id in self.env['multi.channel.sale'].search(CHANNELDOMAIN):
            vals =dict(
                channel_id=channel_id.id,
                source='all',
                operation= 'import',
            )
            obj=self.create(vals)
            obj.import_now()
