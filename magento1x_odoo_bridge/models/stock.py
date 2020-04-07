# -*- coding: utf-8 -*-
##########################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2017-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
# Developed By: PRAKASH KUMAR
##########################################################################
from itertools import groupby
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

# store_product_id
# store_variant_id
class StockMove(models.Model):
    _inherit = "stock.move"
    @api.model
    def sync_magento1x_item(self,channel_id,qty_data,mapping,product_qty,**kwargs):
        result = {'status': True, 'message': ''}
        store_id = mapping.store_product_id
        qty_available = 0
        if qty_data and qty_data.get(store_id):
            qty_available =float(qty_data.get(store_id,0))
        qty_available+=product_qty
        data=dict(
            sku = mapping.default_code,
            stock_data=dict(
               qty= qty_available,
               is_in_stock= qty_available and 1 or 0,
            )
        )
        res=channel_id.magento1x_update_product(product_id=store_id,data=data,channel_id=channel_id,**kwargs)
        result.update(res)
        return result

    @api.model
    def sync_magento1x_items(self,mappings,product_qty,source_loc_id,dest_loc_id):
        mapping_items = groupby(mappings, lambda item: item.channel_id)
        message=''
        for channel_id,mapping_item in groupby(mappings, lambda item: item.channel_id):
            product_qty = channel_id.location_id.id == dest_loc_id and product_qty or -(product_qty)
            product_mapping =list(mapping_item)
            product_ids = list(set([m.store_product_id for m in product_mapping]))
            res = channel_id.get_magento1x_session()
            qty_data = channel_id._fetch_magento1x_qty_data(product_ids=product_ids,**res)
            if not res.get('session'):
                message+=res.pop('message')
            else:
                for mapping in product_mapping:
                    sync_res = self.sync_magento1x_item(channel_id,qty_data,mapping,product_qty,**res)
                    message+=sync_res.get('message')
        return True
    def multichannel_sync_quantity(self, pick_details):
        product_id = pick_details.get('product_id')
        product_qty = pick_details.get('product_qty')
        source_loc_id = pick_details.get('source_loc_id')
        dest_loc_id = pick_details.get('location_dest_id')
        channel_ids = pick_details.get('channel_ids')
        product_obj = self.env['product.product'].browse(pick_details.get('product_id'))
        channels = self.env['multi.channel.sale'].search(
            [('id','in',channel_ids),('channel','=','magento1x'),('auto_sync_stock','=',True)],
        )
        mappings = product_obj.channel_mapping_ids.filtered(
            lambda m:m.channel_id in channels
            and m.channel_id.location_id.id in [source_loc_id,dest_loc_id]
        )
        if mappings:
            self.sync_magento1x_items(mappings,product_qty,source_loc_id,dest_loc_id)
        return super(StockMove,self).multichannel_sync_quantity(pick_details)
