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


class exportmagento1xcategories(models.TransientModel):
    _inherit = ['export.categories']

    @api.model
    def magento1x_get_category_data(self, category_id, channel_id,store_parent_id):
        data = {
          "parent_id": int(store_parent_id),
          "name": category_id.name,
          "is_active": True,
          'include_in_menu':True,
          'available_sort_by':'position',
          'default_sort_by':'position'

        }
        return data


    @api.model
    def magento1x_create_category_data(self, category_id,  channel_id,**kwargs):
        mapping_obj = self.env['channel.category.mappings']
        result=dict(
            mapping_id=None,
            message=''
        )
        message=''
        mapping_id = None
        store_parent_id = 2
        if category_id.parent_id:
            match = self.channel_id.match_category_mappings(
                odoo_category_id =category_id.parent_id.id
            )
            if match:
                store_parent_id = match.store_category_id
        data_res = self.magento1x_get_category_data(
            category_id = category_id,
            channel_id = channel_id,
            store_parent_id=store_parent_id
        )
        categories_res =channel_id.magento1x_create_category(data=data_res,**kwargs)
        if categories_res.get('message'):
            result['message']+=categories_res.get('message')
            return result
        else:
            store_id  =categories_res.get('obj_id')
            mapping_id = channel_id.create_category_mapping(
                erp_id=category_id,
                store_id=store_id,
            )
            result['mapping_id'] = mapping_id

        return result

    @api.model
    def magento1x_update_category_data(self,channel_id,category_id,**kwargs):
        mapping_obj = self.env['channel.category.mappings']
        result=dict(
            mapping_id=None,
            message=''
        )
        message=''
        mapping_id = None
        match = self.channel_id.match_category_mappings(
            odoo_category_id =category_id.id
        )
        if not match:
            message+='Mapping not exits for category %s [%s].'%(category_id.name,category_id.id)
        else:
            store_parent_id = 2
            if category_id.parent_id:
                store_parent_id = self.channel_id.match_category_mappings(
                    odoo_category_id =category_id.parent_id.id
                ).store_category_id
            data_res = self.magento1x_get_category_data(
                category_id = category_id,
                channel_id = channel_id,
                store_parent_id=store_parent_id
            )
            data_res['store_id'] = int(match.store_category_id)
            categories_res =channel_id.magento1x_update_category(data=data_res,**kwargs)
            msz = categories_res.get('message','')
            if msz: message+='While Categories %s Export %s'%(data_res.get('name'),categories_res.get('message',''))
            mapping_id=match
            match.need_sync='no'
        result['mapping_id']=mapping_id
        return result



    @api.model
    def magento1x_post_categories_data(self,channel_id,category_ids,**kwargs):
        message = ''
        create_ids = self.env['channel.category.mappings']
        update_ids = self.env['channel.category.mappings']

        operation = self.operation
        category_dict = dict()
        for category_id in category_ids.sorted('id'):
            try:
                sync_vals = dict(
                    status ='error',
                    action_on ='category',
                    action_type ='export',
                )
                post_res = dict()
                if operation == 'export':
                    post_res=self.magento1x_create_category_data(category_id,channel_id,**kwargs)
                    if post_res.get('mapping_id'):
                        create_ids+=post_res.get('mapping_id')
                else:
                    post_res=self.magento1x_update_category_data(channel_id,category_id,**kwargs)
                    if post_res.get('mapping_id'):
                        update_ids+=post_res.get('mapping_id')
                msz = post_res.get('message')
                _logger.info("%s=====++%s"%(post_res,category_id))
                if post_res.get('mapping_id'):
                    sync_vals['status'] = 'success'
                    sync_vals['ecomstore_refrence'] =post_res.get('mapping_id').store_category_id
                    sync_vals['odoo_id'] = category_id.id
                sync_vals['summary'] = msz or '%s %sed'%(category_id.name,operation)
                channel_id._create_sync(sync_vals)
                if msz:message += '%r' % msz
            except Exception as e:
                message += ' %r' % e
        self._cr.commit()
        return dict(
            message=message,
            update_ids=update_ids,
            create_ids=create_ids,

        )


    def magento1x_export_categories(self):
        message = ''
        ex_create_ids,ex_update_ids,create_ids,update_ids= [],[],[],[]
        for record in self:
            channel_id = record.channel_id
            res =channel_id.get_magento1x_session()
            if res.get('session'):
                exclude_res=record.exclude_export_data(
                    record.category_ids,channel_id,record.operation,model='category'
                )
                categories=exclude_res.get('object_ids')

                if not len(categories):
                    message+='No Category filter for %s over magento.'%(record.operation)
                else:
                    post_res=record.magento1x_post_categories_data(channel_id,categories,**res)
                    create_ids+=post_res.get('create_ids')
                    update_ids+=post_res.get('update_ids')
                    message+=post_res.get('message')
        message+=self.export_message(ex_create_ids,ex_update_ids,create_ids,update_ids)
        return self.env['multi.channel.sale'].display_message(message)
