# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
from odoo import api, fields, models, _
from odoo.addons.magento1x_odoo_bridge.tools.const import CHANNELDOMAIN

_logger = logging.getLogger(__name__)


class ImportMagento1xattributes(models.TransientModel):
    _inherit = ['channel.operation']
    _name = "import.magento1x.attributes"


    @staticmethod
    def get_attribute_value_vals(data,attribute_id,**kwargs):
        return dict(
        name = data.get('label'),
        attribute_id =attribute_id
        )


    @staticmethod
    def get_attribute_vals(data,**kwargs):
        return dict(
            name = data.get('frontend_label') and data.get('frontend_label')[0].get('label'),
        )


    @staticmethod
    def _magento1x_update_attribute_value(mapping,vals,**kwargs):
        # mapping.attribute_name.write(vals)
        mapping.write(dict(store_attribute_value_name=vals.get('label')))
        return  mapping


    @staticmethod
    def _magento1x_create_attribute_value(attribute_value_obj,
        channel_id, attribute_id, store_id, vals,data,**kwargs):

        erp_id = channel_id.get_store_attribute_value_id(vals.get('name'),attribute_id)
        if not erp_id:
            erp_id = attribute_value_obj.create(vals)
        return channel_id.create_attribute_value_mapping(
            erp_id=erp_id, store_id=store_id,
            store_attribute_value_name= data.get('label')
        )


    @staticmethod
    def _magento1x_update_attribute(mapping,vals,data,**kwargs):
        # mapping.attribute_name.write(vals)
        mapping.write(dict(store_attribute_name=data.get('attribute_code')))
        return  mapping


    @staticmethod
    def _magento1x_create_attribute(attribute_obj, channel_id,
        store_id, vals,data,**kwargs):
        erp_id = channel_id.get_store_attribute_id(vals.get('name'))
        if not erp_id:
            erp_id = attribute_obj.create(vals)
        return channel_id.create_attribute_mapping(
            erp_id=erp_id, store_id=store_id, store_attribute_name= data.get('attribute_code')
        )


    @classmethod
    def _magento1x_import_attribute(cls, attribute_obj, channel_id,
        store_id, data,**kwargs):
        match = channel_id.match_attribute_mappings(store_attribute_id=store_id)
        update =False
        vals = cls.get_attribute_vals(data)
        if match:
            update=cls._magento1x_update_attribute( match, vals, data)
        else:
            match= cls._magento1x_create_attribute(attribute_obj, channel_id, store_id, vals, data)
        return dict(
            mapping_id=match,
            update=update
        )


    @api.model
    def _magento1x_import_attribute_value(self, data,
        channel_id, store_id, attribute_id, **kwargs):
        Attributevalue = self.env['product.attribute.value']
        update = False
        match = channel_id.match_attribute_value_mappings(
            store_attribute_value_id=store_id,
        )
        vals = self.get_attribute_value_vals(data,attribute_id)
        if match:
            update=self._magento1x_update_attribute_value( match, vals)
        else:
            match= self._magento1x_create_attribute_value(
                Attributevalue,
                channel_id,
                attribute_id,
                store_id,
                vals,
                data
            )
        return dict(
            mapping_id=match,
            update=update
        )


    @api.model
    def _magento1x_import_attribute_values(self, attribute_mapping_id, options,
        channel_id,  **kwargs):
        attribute_id = attribute_mapping_id.odoo_attribute_id
        create_ids = self.env['channel.attribute.value.mappings']
        update_ids = self.env['channel.attribute.value.mappings']

        for item in options:
            store_id  =item.get('value')
            import_res = self._magento1x_import_attribute_value(
                data = item,
                channel_id = channel_id,
                store_id = store_id,
                attribute_id =attribute_id,
                **kwargs
            )
            mapping_id = import_res.get('mapping_id')
            if  import_res.get('update'):
                update_ids += mapping_id
            else:
                create_ids += mapping_id

        return dict(
            create_ids=create_ids,
            update_ids=update_ids,
        )


    @api.model
    def _magento1x_import_attributes(self,attribute_obj,channel_id, items,  **kwargs):
        message = ''
        create_ids = self.env['channel.attribute.mappings']
        update_ids = self.env['channel.attribute.mappings']
        CustomAtts = lambda attr:attr.get('scope')=='global' and attr.get('type')=='select' #and  attr.get('required')=='0'
        for item in filter(CustomAtts,items):
            _logger.info("==item=%r===="%(item))
            attribute_id = int(item.get('attribute_id'))
            attribute_res =channel_id._fetch_magento1x_product_attributes(set_id=None,attribute_id=attribute_id,**kwargs)
            attribute_info = attribute_res.get('data')
            message+=attribute_res.get('message')
            if attribute_info.get('is_configurable')!='1':continue
            _logger.info("==attribute_info=%r===="%(attribute_info))
            import_res =   self._magento1x_import_attribute(
                attribute_obj,
                channel_id,
                attribute_id,
                attribute_info,
            )
            mapping_id = import_res.get('mapping_id')
            options = attribute_info.get('options')
            _logger.info("=options==%r===="%(options))

            if mapping_id and len(options):
                self._magento1x_import_attribute_values(
                    attribute_mapping_id = mapping_id,
                    options = options,
                    channel_id = channel_id,
                )
            if  import_res.get('update'):
                update_ids += mapping_id
            else:
                create_ids += mapping_id
        return dict(
            create_ids=create_ids,
            update_ids=update_ids,
            message = message
        )

    def import_now(self):
        create_ids,update_ids,map_create_ids,map_update_ids=[],[],[],[]
        message=''
        Attribute = self.env['product.attribute']

        for record in self:
            channel_id = record.channel_id
            res =channel_id.get_magento1x_session()
            session = res.get('session')
            client = res.get('client')
            if not session:
                message+=res.get('message')
            else:
                fetch_res = channel_id._fetch_magento1x_product_attributes(**res)
                attributes = fetch_res.get('data', {})
                message+= fetch_res.get('message','')
                if not attributes:
                    message+="Attributes data not received."
                else:
                    feed_res=record._magento1x_import_attributes(
                        Attribute,
                        channel_id,
                        attributes,
                        sdk
                    )
                    create_ids+=feed_res.get('create_ids')
                    update_ids+=feed_res.get('update_ids')
        message+=self.env['multi.channel.sale'].get_operation_message_v1(
            obj = 'attribute',
            obj_model = 'record',
            operation = 'updated',
            obj_ids = create_ids
        )
        message+=self.env['multi.channel.sale'].get_operation_message_v1(
            obj = 'attribute',
            obj_model = 'record',
            operation = 'updated',
            obj_ids = update_ids
        )

        return self.env['multi.channel.sale'].display_message(message)


    @api.model
    def _cron_magento1x_import_attributes(self):
        for channel_id in self.env['multi.channel.sale'].search(CHANNELDOMAIN):
            vals =dict(
                channel_id=channel_id.id,
                source='all',
                operation= 'import',
            )
            obj=self.create(vals)
            obj.import_now()
