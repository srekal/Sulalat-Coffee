# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
import itertools

from odoo import api, fields, models, _
from odoo.addons.magento1x_odoo_bridge.tools.const import CHANNELDOMAIN

_logger = logging.getLogger(__name__)

class ImportMagento1xattributes(models.TransientModel):
    _inherit = ['channel.operation']
    _name = "import.magento1x.attributes.sets"

            
    @staticmethod
    def get_mage1x_attribute_set_vals(data,**kwargs):
        """Parse  data in odoo format and return as dict vals ."""


        attribute_set_id = data.get('set_id')
        odoo_attribute_ids = kwargs.get('odoo_attribute_ids')
        return dict(
        set_name = data.get('name'),
        store_id = attribute_set_id,
        attribute_ids = [(6,0,odoo_attribute_ids)]
        )


    @staticmethod
    def _magento1x_update_attribute_set_feed(match,vals,**kwargs):
        """Update  attribute set  with then vals."""
        return match.write(vals)


    @staticmethod
    def _magento1x_create_attribute_set_feed(set_obj,channel_id,  attribute_set_id, vals,**kwargs):
        """Create new  attribute set for given vals."""
        vals['store_id']=attribute_set_id
        return  channel_id._create_obj(set_obj, vals)


    def _magento1x_import_attribute_set(self, set_obj,channel_id, attribute_set_id, data,**kwargs):
        """
        Import attributes set in odoo.
        :param set_obj: attributes set model ==> self.env['magento.attributes.set']
        :param channel_id: channel instance of magento   ==> multi.channel.sale(1)
        :attribute_set_id: magento attribute set id ==> 4
        :data: magento attribute set data dict
        :return: error in example pointed by example number.
        Note: If attributes set exits, then don't create a new attributes set.
        """

        match = channel_id._match_feed(
            set_obj, [('store_id', '=', attribute_set_id)])
        update =False

        # extact  attribute set vals from  magento 1.x attribute set  data .
        vals = self.get_mage1x_attribute_set_vals(data, **kwargs)

        if match:
            update=self._magento1x_update_attribute_set_feed( match,  vals)
            update  =True
        else:
            match= self._magento1x_create_attribute_set_feed(set_obj,channel_id, attribute_set_id, vals)
        return dict(
            feed_id=match,
            update=update
        )


    def get_magento1x_odoo_attribute_ids(self,set_id,channel_id,**kwargs):
        attribute_res = channel_id._fetch_magento1x_product_attributes(
            session=kwargs.get('session'),client=kwargs.get('client'),set_id=set_id
        )
        message = ''
        message+= attribute_res.get('message','')
        attributes =  attribute_res.get('data')
        attributes_mapping = self._magento1x_import_attributes(channel_id, attributes,**kwargs)
        odoo_attribute_ids = attributes_mapping.mapped('odoo_attribute_id')
        return odoo_attribute_ids
        
        



    

    def _magento1x_import_attribute_sets(self, set_obj, channel_id, items,**kwargs):
        """Import attributes sets in odoo.

        Args:
            set_obj: Attributes set model ==> self.env['magento.attributes.set']
            channel_id: Channel instance of magento   ==> multi.channel.sale(1)
            items: Magento attribute sets data dict
        Returns:
            A dict (create_ids , update_ids) of newly created and updated attributes sets ids.
        """

        create_ids ,update_ids = [] , []

        for item in items:
            set_id = item.get('set_id')
            odoo_attribute_ids = self.get_magento1x_odoo_attribute_ids(
                set_id = set_id,channel_id=channel_id,**kwargs
            )
            import_res =   self._magento1x_import_attribute_set(
                set_obj = set_obj,
                channel_id = channel_id,
                attribute_set_id = set_id,
                odoo_attribute_ids = odoo_attribute_ids,
                data = item,
                **kwargs
            )
            feed_id = import_res.get('feed_id')

            if import_res.get('update'):
                update_ids.append(feed_id)
            else:
                create_ids.append(feed_id)

        return dict(
            create_ids = create_ids,
            update_ids = update_ids,
        )

    @api.model
    def _magento1x_import_attributes(self, channel_id, attributes,**kwargs):
        """Import magento attributes in odoo."""
        

        
        
        ImportMagento2xAttributes = self.env['import.magento1x.attributes']
        AttributesMappping = self.env['channel.attribute.mappings']
        Attribute = self.env['product.attribute']

        # Create import.magento1x.attributes instance with source=all and operation=import.
        vals =dict(
            channel_id=channel_id.id,
            source='all',
            operation= 'import',
        )
        record =ImportMagento2xAttributes.create(vals)

        #Import magento1x attributes in odoo.
        res= record._magento1x_import_attributes(
            attribute_obj = Attribute,
            channel_id = channel_id,
            items = attributes,
            **kwargs
        )

        #Merge all crated and updated attributes odoo mapping.
        AttributesMappping+=res.get('create_ids')
        AttributesMappping+=res.get('update_ids')
        return AttributesMappping


    @api.multi
    def import_now(self):
        """Import magento attributes sets in odoo."""
        create_ids,update_ids,map_create_ids,map_update_ids=[],[],[],[]
        message=''
        AttributesSet = self.env['magento.attributes.set']

        for record in self:
            channel_id = record.channel_id
            res =channel_id.get_magento1x_session()
            session = res.get('session')
            client = res.get('client')
            if not session:
                message+=res.get('message')
            else:
        
                fetch_res =channel_id._fetch_magento1x_product_attributes_sets(session=session,client=client)
                attribute_sets = fetch_res.get('data', {})
                message+= fetch_res.get('message','')
                if not attribute_sets:
                    message+="Attribute Sets data not received."
                else:

                    # Import  all attributes  sets .
                    feed_res=record._magento1x_import_attribute_sets(
                        set_obj = AttributesSet,
                        channel_id = channel_id,
                        items = attribute_sets,
                        session = session,
                        client = client,
                    )
                    create_ids+=feed_res.get('create_ids')
                    update_ids+=feed_res.get('update_ids')

        # Get Message about create and updated  attributes  sets .
        message+=self.env['multi.channel.sale'].get_operation_message_v1(
            obj = 'attribute set',
            obj_model = 'record',
            operation = 'created',
            obj_ids = create_ids
        )
        message+=self.env['multi.channel.sale'].get_operation_message_v1(
            obj = 'attribute set',
            obj_model = 'record',
            operation = 'updated',
            obj_ids = update_ids
        )
        return self.env['multi.channel.sale'].display_message(message)


    @api.model
    def _cron_magento1x_import_attributes_sets(self):
        """Import magento 1.x attribute set in odoo using cron."""
        # Iterate all  magento 1.x channel(channel=magento1x) .

        for channel_id in self.env['multi.channel.sale'].search(CHANNELDOMAIN):
            vals =dict(
                channel_id=channel_id.id,
                source='all',
                operation= 'import',
            )
            obj=self.create(vals)
            # It's time to import.
            obj.import_now()
