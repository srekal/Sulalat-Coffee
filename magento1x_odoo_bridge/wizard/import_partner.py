# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, _
from odoo.addons.magento1x_odoo_bridge.tools.const import CHANNELDOMAIN
from odoo.addons.odoo_multi_channel_sale.tools import chunks, ensure_string as ES

customerInfoFields = [
]
Boolean = [

    ('all', 'True/False'),
    ('1', 'True'),
    ('0', 'False'),
]
Source = [
    ('all', 'All'),
    ('partner_ids', 'Partner ID(s)'),
]


class ImportMagento1xpartners(models.TransientModel):
    _inherit = ['import.partners']
    _name = "import.magento1x.partners"
    @api.model
    def _get_parent_categ_domain(self):
        return self._get_ecom_store_domain()
    @api.model
    def _get_magento1x_group(self):
        groups=[('all','All')]
        return groups
    source = fields.Selection(Source, required=1, default='all')
    group_id = fields.Selection(
        selection = _get_magento1x_group,
        string='Group ID',
        required=1,
        default='all'
    )
    @staticmethod
    def _get_magento1x_customer_address_vals(data,customer_id,channel_id,**kwargs):
        res=[]
        for item in data:
            name = item.get('firstname')
            if item.get('lastname'):
                name+=' %s'%(item.get('lastname'))
            _type = 'invoice'
            if item.get('is_default_shipping'):
                _type = 'delivery'
            store_id = channel_id.get_magento1x_address_hash(item)
            vals= dict(
                name=name,
                email=item.get('email'),
                street=item.get('street'),
                phone=item.get('telephone'),
                city=item.get('city'),
                state_name=item.get('region'),
                country_id=item.get('country_id'),
                zip=item.get('postcode'),
                store_id=store_id,
                parent_id = customer_id,
                type=_type
            )
            res+=[vals]
        return res
    @staticmethod
    def get_customer_vals(customer_data):
        vals = dict(
            name=customer_data.get('firstname'),
            last_name = customer_data.get('lastname'),
            email=customer_data.get('email'),
            type = 'contact'
        )
        return vals

    @staticmethod
    def _magento1x_update_customer_feed(match,vals):
        vals['state']='update'
        return match.write(vals)

    @staticmethod
    def _magento1x_create_customer_feed(channel_id,customer_id, feed_obj,vals,**kwargs):
        vals['store_id'] =customer_id
        feed_id = channel_id._create_feed(feed_obj, vals)
        return feed_id

    @classmethod
    def _magento1x_manage_address(cls,channel_id,customer_id,feed_obj,**kwargs):
        res_address = channel_id._fetch_magento1x_customer_address(customer_id=customer_id,**kwargs)
        data = res_address.get('data')
        if data:
            add_vals=cls._get_magento1x_customer_address_vals(data,customer_id,channel_id)
            for add_val in add_vals:
                feed_id = channel_id._create_feed(feed_obj, add_val)
    @classmethod
    def _magento1x_import_customer(cls, channel_id,feed_obj,customer_id, data,**kwargs):
        match = channel_id._match_feed(
            feed_obj, [('store_id', '=', customer_id),('type','=','contact')])
        update =False
        vals =cls.get_customer_vals(data)
        if match:
            update=cls._magento1x_update_customer_feed(match, vals)
        else:
            cls._magento1x_manage_address(customer_id=customer_id,feed_obj=feed_obj,
            channel_id=channel_id,**kwargs)
            match= cls._magento1x_create_customer_feed(channel_id,customer_id,feed_obj, vals)
        return dict(
            feed_id=match,
            update=update
        )
    @classmethod
    def _magento1x_import_partners(cls,channel_id,feed_obj, items,**kwargs):
        create_ids=[]
        update_ids=[]
        for item in items:
            customer_id = item.get('customer_id')
            import_res =   cls._magento1x_import_customer(
            channel_id=channel_id,feed_obj=feed_obj,customer_id=customer_id, data=item,**kwargs)
            feed_id = import_res.get('feed_id')
            if  import_res.get('update'):
                update_ids.append(feed_id)
            else:
                create_ids.append(feed_id)
        return dict(
            create_ids=create_ids,
            update_ids=update_ids,
        )

    def import_now(self):
        create_ids,update_ids,map_create_ids,map_update_ids=[],[],[],[]
        message=''
        feed_obj = self.env['partner.feed']
        for record in self:
            channel_id = record.channel_id
            debug = channel_id.debug=='enable'
            channel_id=record.channel_id
            if channel_id.magento1x_is_child_store:
                default_store_id = channel_id.magento1x_default_store_id
                if not default_store_id:
                    message+='No default channel set in configurable .'
                record.write(dict(channel_id=default_store_id.id))
                channel_id = default_store_id

            res =channel_id.get_magento1x_session()
            if not res.get('session'):
                message+=res.pop('message','')
            else:
                fetch_res =channel_id._fetch_magento1x_partners(
                    from_date =  record.operation=='import' and record.import_customer_date,
                    to_date =  record.operation=='import' and record.to_date,
                    **res
                )
                partners = fetch_res.get('data') or []
                message+= fetch_res.pop('message','')
                if not(partners and len(partners)):
                    message+="Partners data not received."
                else:
                    _logger.info("partners===%r==="%(len(partners)))
                    for item_chuncks in chunks(partners,self.api_record_limit):
                        if debug:
                            _logger.info("item_chuncks===%r==="%(len(item_chuncks)))
                        feed_res=record._magento1x_import_partners(
                            channel_id=channel_id,feed_obj=feed_obj,items=item_chuncks,**res
                        )
                        message +=res.get('message')
                        post_res = self.post_feed_import_process(channel_id,feed_res)
                        create_ids+=post_res.get('create_ids')
                        update_ids+=post_res.get('update_ids')
                        map_create_ids+=post_res.get('map_create_ids')
                        map_update_ids+=post_res.get('map_update_ids')
                        if len(create_ids):channel_id.set_channel_date('import','customer')
                        if len(update_ids):channel_id.set_channel_date('update','customer')
                        self._cr.commit()
        message+=self.env['multi.channel.sale'].get_feed_import_message(
            'partner',create_ids,update_ids,map_create_ids,map_update_ids
        )
        return self.env['multi.channel.sale'].display_message(message)
    @api.model
    def _cron_magento1x_import_partners(self):
        for channel_id in self.env['multi.channel.sale'].search(CHANNELDOMAIN):
            vals =dict(
                channel_id=channel_id.id,
                source='all',
                operation= 'import',
            )
            obj=self.create(vals)
            obj.import_now()
