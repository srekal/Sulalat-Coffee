# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
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
#################################################################################
{
  "name"                 :  "Odoo Multi-Channel Sale",
  "summary"              :  "The module is Multiple platform connector with Odoo. You can connect and manage various platforms in odoo with the help of Odoo multi-channel bridge.",
  "category"             :  "Website",
  "version"              :  "2.1.3",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Multi-Channel-Sale.html",
  "description"          :  """Odoo multi-channel bridge
Multi channel connector
Multi platform connector
Multiple platforms bridge
Connect Amazon with odoo
Amazon bridge
Flipkart Bridge
Magento Odoo Bridge
Odoo magento bridge
Woocommerce odoo bridge
Odoo woocommerce bridge
Ebay odoo bridge
Odoo ebay bridge
Multi channel bridge
Prestashop odoo bridge
Odoo prestahop
Akeneo bridge
Etsy bridge
Marketplace bridge
Multi marketplace connector
Multiple marketplace platform""",
  "live_test_url"        :  "https://store.webkul.com/Odoo-Multi-Channel-Sale.html#",
  "depends"              :  ['delivery'],
  "data"                 :  [
                             'security/security.xml',
                             'security/ir.model.access.csv',
                             'wizard/wizard_view.xml',
                             'wizard/feeds_wizard_view.xml',
                             'views/template.xml',
                             'views/res_config_view.xml',
                             'views/multi_channel_sale_view.xml',
                             'views/channel_syncronization_view.xml',
                             'views/category_skeleton_view.xml',
                             'views/account_skeleton_view.xml',
                             'views/product_skeleton_view.xml',
                             'views/partner_skeleton_view.xml',
                             'views/order_skeleton_view.xml',
                             'views/pricelist_skeleton_view.xml',
                             'wizard/export_products_wizard_view.xml',
                             'wizard/export_templates_wizard_view.xml',
                             'wizard/export_categ_wizard_view.xml',
                             'views/shipping_skeleton_view.xml',
                             'views/inherits.xml',
                             'views/feeds_view.xml',
                             'views/shipping_feed_view.xml',
                             'views/multi_channel_skeleton_view.xml',
                             'views/order_feed_view.xml',
                             'views/attribute_value_skeleton.xml',
                             'views/menu_items.xml',
                             'data/server_action.xml',
                             'data/demo.xml',
                             'data/cron.xml',
                            ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  99,
  "currency"             :  "EUR",
  "pre_init_hook"        :  "pre_init_check",
}