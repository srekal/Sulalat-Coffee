# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class ImportOperation(models.TransientModel):
	_inherit = 'import.operation'

	object = fields.Selection(
		selection_add=[
			('res.partner','Customer'),
			('product.category','Category'),
			('product.template','Product'),
			('sale.order','Order'),
		]
	)

	magento1x_filter_type = fields.Selection(
		string='Filter Type',
		selection=[
			# ('all','All'),
			('data_range','Date Range'),
			# ('id','By ID'),
			# ('since_id','Since ID')
		],
		default='data_range',
		required=True,
	)
	# shopify_object_id      = fields.Char('Object ID')
	# shopify_updated_at_min = fields.Date('Updated From')
	# shopify_updated_at_max = fields.Date('Updated Till')
	# shopify_since_id       = fields.Char('From ID')
	# shopify_limit          = fields.Integer('Limit')


	# def shopify_get_filter(self):
	# 	kw = {'filter_type':self.shopify_filter_type}
	# 	if self.shopify_filter_type == 'id':
	# 		kw['object_id'] = self.shopify_object_id
	# 	elif self.shopify_filter_type == 'data_range':
	# 		kw['updated_at_min'] = self.shopify_updated_at_min
	# 		kw['updated_at_max'] = self.shopify_updated_at_max
	# 	elif self.shopify_filter_type == 'since_id':
	# 		kw['since_id'] = self.shopify_since_id
	# 		if self.shopify_limit:
	# 			kw['limit'] = self.shopify_limit
	# 	return kw
