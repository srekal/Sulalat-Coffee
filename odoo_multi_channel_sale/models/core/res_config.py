# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>
##############################################################################
from odoo import api,fields,models


class MultiChannelSaleConfig(models.TransientModel):
	_name = 'multi.channel.sale.config'
	_description = 'Multi Channel Sale Config'
	_inherit = 'res.config.settings'

	avoid_duplicity = fields.Boolean(
		string = 'Avoid Duplicity (Default Code)',
		help   = "Check this if you want to avoid the duplicity of the imported products. In this case the product with same default code/sku will not create again and again."
	)

	avoid_duplicity_using = fields.Selection(
		selection = [
			('default_code','Default Code/SKU'),
			('barcode','Barcode/UPC/EAN/ISBN'),
			('both','Both')
		],
		string  = "Avoid Duplicity Using",
		default = 'both',
		help    = "In Both option the the uniqueness will be wither on sku/Default or UPC/EAN/Barcode usign OR operator and it should be always be given high priority"
	)

	def set_values(self):
		super(MultiChannelSaleConfig,self).set_values()
		IrDefault = self.env['ir.default'].sudo()
		IrDefault.set(
			'multi.channel.sale.config',
			'avoid_duplicity',
			self.avoid_duplicity
		)
		IrDefault.set(
			'multi.channel.sale.config',
			'avoid_duplicity_using',
			self.avoid_duplicity_using
		)
		return True

	@api.model
	def get_values(self):
		res       = super(MultiChannelSaleConfig,self).get_values()
		IrDefault = self.env['ir.default'].sudo()
		res.update(
			{
				'avoid_duplicity'      : IrDefault.get(
					'multi.channel.sale.config',
					'avoid_duplicity'
				),
				'avoid_duplicity_using': IrDefault.get(
					'multi.channel.sale.config',
					'avoid_duplicity_using' or 'both'
				)
			}
		)
		return res
