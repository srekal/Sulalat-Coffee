# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################
import logging
import re
import  xmlrpc.client
from  xmlrpc.client import Error
from datetime import date, datetime,timedelta
MageDateTimeFomat = '%Y-%m-%d %H:%M:%S'
_logger = logging.getLogger(__name__)
from odoo.addons.magento1x_odoo_bridge.tools.const import InfoFields
from odoo.addons.odoo_multi_channel_sale.tools import get_hash_dict
from odoo.addons.odoo_multi_channel_sale.tools import extract_list as EL
from odoo.addons.odoo_multi_channel_sale.tools import ensure_string as ES
from odoo.addons.odoo_multi_channel_sale.tools import JoinList as JL
from odoo.addons.odoo_multi_channel_sale.tools import MapId
from odoo import api,fields, models,_
from odoo.exceptions import UserError
Boolean = [
    ('1', 'True'),
    ('0', 'False'),
]
Visibility = [
    ('1', 'Not Visible Individually'),
    ('2', 'Catalog'),
    ('3', 'Catalog'),
    ('4', 'Catalog, Search'),

]
Type = [
    ('simple','Simple Product'),
    ('downloadable','Downloadable Product'),
    ('grouped','Grouped Product'),
    ('virtual','Virtual Product'),
    ('bundle','Bundle Product'),
]
ShortDescription = [
    ('same','Same As Product Description'),
    ('custom','Custom')
]
TaxType = [
    ('include','Include In Price'),
    ('exclude','Exclude In Price')
]
DefaultStore = _("""***While using multi store***\n
Select the default store/parent store
from where the order and partner will imported for this child store.
""")


class MagentoAttributesSet(models.Model):
    _rec_name='set_name'
    _name = "magento.attributes.set"
    _inherit = ['channel.mappings']

    set_name = fields.Char(
        string = 'Set Name'
    )
    attribute_ids = fields.Many2many(
        'product.attribute',
        string='Attribute(s)',
    )


    @api.model
    def default_get(self,fields):
        res=super(MagentoAttributesSet,self).default_get(fields)
        if self._context.get('wk_channel_id'):
            res['channel_id']=self._context.get('wk_channel_id')
        return res




class Feed(models.Model):
    _inherit = ['wk.feed']
    @api.model
    def get_extra_categ_ids(self, store_categ_ids,channel_id):
        if channel_id.channel=='magento1x' and channel_id.magento1x_default_store_id:
            channel_id = channel_id.magento1x_default_store_id
        return super(Feed,self).get_extra_categ_ids(store_categ_ids,channel_id)

    @api.model
    def get_order_partner_id(self, store_partner_id,channel_id):
        if channel_id.channel=='magento1x' and channel_id.magento1x_default_store_id:
            channel_id = channel_id.magento1x_default_store_id
        return super(Feed,self).get_order_partner_id(store_partner_id,channel_id)


class MultiChannelSale(models.Model):
    _inherit = "multi.channel.sale"

    @api.model
    def match_category_mappings(self, store_category_id=None, odoo_category_id=None, domain=None, limit=1):
        if self.channel=='magento1x' and self.magento1x_default_store_id:
            self = self.magento1x_default_store_id
        return super(MultiChannelSale,self).match_category_mappings(store_category_id=store_category_id,odoo_category_id=odoo_category_id,domain=domain,limit=limit)

    @api.model
    def match_partner_mappings(self, store_id = None, _type='contact',domain=None, limit=1):
        if self.channel=='magento1x' and self.magento1x_default_store_id:
            self = self.magento1x_default_store_id
        return super(MultiChannelSale,self).match_partner_mappings(store_id=store_id,_type=_type,domain=domain,limit=limit)

    @api.model
    def get_magento1x_default_product_categ_id(self):
        domain = [('ecom_store', '=', 'magento1x')]
        if self._context.get('wk_channel_id'):
            domain += [('channel_id', '=', self._context.get('wk_channel_id'))]
        return self.env['channel.category.mappings'].search(domain,limit = 1)

    @api.model
    def magento1x_get_default_product_set_id(self):
        domain =[('ecom_store','=','magento1x')]
        wk_channel_id = self._context.get('wk_channel_id') or self._context.get('channel_id')
        if wk_channel_id:
            domain += [('channel_id','=',wk_channel_id)]
        return self.env['magento.attributes.set'].search(domain,limit=1)



    @api.model
    def get_magento_category_mappings(self, limit = 0):
        domain = [('ecom_store', '=', 'magento1x')]
        if self._context.get('wk_channel_id'):
            domain += [('channel_id', '=', self._context.get('wk_channel_id'))]
        return self.env['channel.category.mappings'].search(domain,limit)

    @api.model
    def get_magento_category_mappings_domain(self):
        mappings = self.get_magento_category_mappings().ids
        return [('id', 'in', mappings)]

    @api.model
    def get_magento_odoo_category_domain(self):
        category_ids = self.get_magento_category_mappings().mapped('odoo_category_id')
        return [('id', 'not in', category_ids)]

    @api.model
    def get_magento1x_store_id(self):
        return eval(self.magento1x_store_config).get('store_id')

    @api.model
    def get_magento1x_client(self):
        data_uri ='{base_uri}/index.php/api/xmlrpc/'.format(base_uri = self.magento1x_base_uri)
        client = xmlrpc.client.ServerProxy(data_uri)
        return client

    @api.model
    def get_magento1x_session(self):
        message = ''
        session = None
        client = None
        try:
            client = self.get_magento1x_client()
            session = client.login(
                self.magento1x_api_username,
                self.magento1x_api_key
            )
        except Error as e:
            e = str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            session = session,
            client = client,
            message = message,
        )

    @api.model
    def get_channel(self):
        result = super(MultiChannelSale, self).get_channel()
        result.append(("magento1x", "Magento v1.9"))
        return result

    @api.model
    def get_info_urls(self):
        urls = super(MultiChannelSale,self).get_info_urls()
        urls.update(
            magento1x = {
                'blog' : 'https://webkul.com/blog/multi-channel-magento-1-x-odoo-bridgemulti-channel-mob',
                'store': 'https://store.webkul.com/Multi-Channel-Magento-1-x-Odoo-Bridge-Multi-Channel-MOB.html',
            },
        )
        return urls


    def test_magento1x_connection(self):
        for obj in self:
            state = 'error'
            message = ''
            res = obj.get_magento1x_session()
            session = res.get('session')
            if not session:
                message += '<br/>%s'%(res.get('message'))
            else:
                session = res.get('session')
                client = res.get('client')
                store_list=client.call(session, 'store.list')
                store_code = obj.magento1x_store_code
                res_store = [store for store in store_list if int(store.get('store_id')) and store.get('code')==store_code ]
                # _logger.info("==%r=="%(res_store))
                if len(res_store):
                    state = 'validate'
                    message += '<br/> Credentials successfully validated.'
                    obj.magento1x_store_config = res_store[0]
                else:
                    store_list = [store.get('code') for store in store_list  if int(store.get('store_id'))]
                    message += '<br/> Store <b>%s</b> not match in these stores %r.'%(store_code,store_list)
            obj.state = state
            if state != 'validate':
                message += '<br/> Error While Credentials  validation.'
        return self.display_message(message)

    magento1x_base_uri = fields.Char(
        string = 'Base URI'
    )
    magento1x_api_username = fields.Char(
        string = 'API User'
    )
    magento1x_api_key = fields.Char(
        string = 'API Key'
    )

    magento1x_store_code = fields.Char(
        string='Store ID',
        default='default',
    )
    magento1x_store_config = fields.Text(
        string='Store Config'
    )
    magento1x_is_child_store = fields.Boolean(
        string = 'Is Child Store'
    )
    magento1x_default_store_id =fields.Many2one(
        comodel_name = 'multi.channel.sale',
        string='Parent Store',
        help = DefaultStore,
    )
    magento1x_default_product_categ_id = fields.Many2one(
        comodel_name = 'channel.category.mappings',
        string = 'Magento Categories',
        domain = lambda self:self.env['multi.channel.sale'].get_magento_category_mappings_domain(),
        default = lambda self:self.get_magento1x_default_product_categ_id()
    )

    magento1x_default_tax_type = fields.Selection(
        selection = TaxType,
        string = 'Tax Type',
        default = 'exclude',
        required = 1
    )

    magento1x_default_product_set_id = fields.Many2one(
        comodel_name='magento.attributes.set',
        string='Default Attribute Set',
        help='ID of the product attribute set',
        default=lambda self:self.magento1x_get_default_product_set_id()
    )

    magento1x_export_order_shipment = fields.Boolean(
        string = 'Export Shipment',
        default = '1',
    )
    magento1x_export_order_invoice = fields.Boolean(
        string = 'Export Invoice',
        default = '1',
    )

    magento1x_imp_products_cron = fields.Boolean(
        string = 'Import Products'
    )
    magento1x_imp_orders_cron = fields.Boolean(
        string = 'Import Orders'
    )
    magento1x_imp_orders_status_cron = fields.Boolean(
        string='Import Orders Status',
        help = """Import orders status of draft order
                    and  change state on odoo as per state mapping"""
    )
    magento1x_imp_categories_cron = fields.Boolean(
        string = 'Import Categories'
    )
    magento1x_imp_partners_cron = fields.Boolean(
        string = 'Import Partners'
    )

    @api.onchange('magento1x_imp_products_cron')
    def magento1x_set_importproducts_cron(self):
        try:
            product_cron= self.env.ref('magento1x_odoo_bridge.cron_import_products_from_magento1x',False)
            if product_cron:
                product_cron.sudo().write(dict(active=self.magento1x_imp_products_cron))
        except Exception as e:
            raise Warning(e)

    @api.onchange('magento1x_imp_orders_cron')
    def magento1x_set_import_order_cron(self):
        self.set_channel_cron(
            ref_name = 'magento1x_odoo_bridge.cron_import_orders_from_magento1x',
            active = self.magento1x_imp_orders_cron
        )

    @api.onchange('magento1x_imp_orders_status_cron')
    def set_import_order_status_cron(self):
        self.set_channel_cron(
            ref_name = 'magento1x_odoo_bridge.cron_import_orders_status_from_magento1x',
            active = self.magento1x_imp_orders_status_cron
        )

    @api.onchange('magento1x_imp_categories_cron')
    def magento1x_set_import_categories_cron(self):
        self.set_channel_cron(
            ref_name = 'magento1x_odoo_bridge.cron_import_categories_from_magento1x',
            active = self.magento1x_imp_categories_cron
        )

    @api.onchange('magento1x_imp_partners_cron')
    def magento1x_set_import_partners_cron(self):
        self.set_channel_cron(
            ref_name = 'magento1x_odoo_bridge.cron_import_partners_from_magento1x',
            active = self.magento1x_imp_partners_cron
        )

    @api.model
    def create(self, vals):
        base_uri = vals.get('magento1x_base_uri')
        if base_uri:
            vals['magento1x_base_uri'] = re.sub('/index.php', '', base_uri.strip(' ').strip('/'))
        return super(MultiChannelSale,self).create(vals)

    def write(self, vals):
        base_uri = vals.get('magento1x_base_uri')
        if base_uri:
            vals['magento1x_base_uri'] = re.sub('/index.php', '', base_uri.strip(' ').strip('/'))
        return super(MultiChannelSale,self).write(vals)

    @staticmethod
    def get_magento1x_address_hash(itemvals):
        templ_add = {
        "city":itemvals.get("city"),
        "region_code":itemvals.get("region_code"),
        "firstname":itemvals.get("firstname"),
        "lastname":itemvals.get("lastname"),
        "region":itemvals.get("region"),
        "country_id":itemvals.get("country_id"),
        "telephone":itemvals.get("telephone"),
        "street":itemvals.get("street"),
        "postcode":itemvals.get("postcode"),
        # "customer_address_id":itemvals.get("customer_address_id") or itemvals.get('customer_id')
        }
        return get_hash_dict(templ_add)
    @api.model
    def magento1x_post_do_transfer(self,picking_id,mapping_ids,result):
        debug = self.debug=='enable'
        if self.magento1x_export_order_shipment:
            sync_vals = dict(
                status ='error',
                action_on ='order',
                action_type ='export',
            )
            res =self.get_magento1x_session()
            session = res.get('session')
            client = res.get('client')
            if debug:
                _logger.info("do_transfer #1 %r===%r="%(res,mapping_ids))
            if session:
                for mapping_id in mapping_ids:
                    message=''
                    comment,data='',None
                    sync_vals['ecomstore_refrence'] ='%s(%s)'%(mapping_id.store_order_id,mapping_id.store_id)

                    sync_vals['odoo_id'] = mapping_id.odoo_order_id
                    try:
                        comment = 'Create For Odoo Order %s , Picking %s'%( mapping_id.order_name.name,picking_id.name)
                        data=client.call(session, 'order_shipment.create',[mapping_id.store_order_id,[],comment])
                        sync_vals['status'] = 'success'

                        message   += 'Delivery created successfully '
                    except Error as e:
                        e =str(e).strip('<').strip('>')
                        message += '<br/>Error For  Order  %s  Shipment <br/>%s'%(mapping_id.store_order_id,str(e))
                    except Exception as e:
                        message += '<br/>Error For  Order  %s  Shipment <br/>%s'%(mapping_id.store_order_id,str(e))
                    sync_vals['summary'] = message
                    if debug:
                        _logger.info("=do_transfer #2==%r=====%r==%r="%(comment,data,sync_vals))
                    mapping_id.channel_id._create_sync(sync_vals)

    @api.model
    def magento1x_post_confirm_paid(self,invoice_id,mapping_ids,result):
        debug = self.debug=='enable'
        if self.magento1x_export_order_invoice:
            sync_vals = dict(
                status ='error',
                action_on ='order',
                action_type ='export',
            )
            res =self.get_magento1x_session()
            session = res.get('session')
            client = res.get('client')
            if debug:
                _logger.info("confirm_paid #1 %r===%r="%(res,mapping_ids))
            if session:
                for mapping_id in mapping_ids:
                    comment,data='',None
                    sync_vals['ecomstore_refrence'] ='%s(%s)'%(mapping_id.store_order_id,mapping_id.store_id)
                    sync_vals['odoo_id'] = mapping_id.odoo_order_id
                    message=''
                    try:
                        comment = 'Create For Odoo Order %s  Invoice %s'%( mapping_id.order_name.name,invoice_id.number)
                        data=client.call(session, 'order_invoice.create',[mapping_id.store_order_id,[],comment])
                        sync_vals['status'] = 'success'
                        message += 'Invoice created successfully '
                    except Error as e:
                        e =str(e).strip('<').strip('>')
                        message += '<br/>Error For  Order  %s  Invoice <br/>%s'%(mapping_id.store_order_id,str(e))
                    except Exception as e:
                        message += '<br/>Error For  Order  %s  Invoice <br/>%s'%(mapping_id.store_order_id,str(e))
                    sync_vals['summary'] = message
                    if debug:
                        _logger.info("=do_transfer #2==%r=====%r==%r="%(comment,data,sync_vals))
                    mapping_id.channel_id._create_sync(sync_vals)

    def import_magento1x_products(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
            source='all',
            operation= 'import',
        )
        obj=self.env['import.magento1x.products'].create(vals)
        return obj.import_now()

    def import_magento1x_categories(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
            source='all',
            operation= 'import',
        )
        obj=self.env['import.magento1x.categories'].create(vals)
        return obj.import_now()

    def import_magento1x_attributes_sets(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
            # source='all',
            # operation= 'import',
        )
        obj=self.env['import.magento1x.attributes.sets'].create(vals)
        return obj.import_now()


    def import_magento1x_partners(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
            source='all',
            operation= 'import',
        )
        obj=self.env['import.magento1x.partners'].create(vals)
        return obj.import_now()

    def import_magento1x_orders(self):
        self.ensure_one()
        vals =dict(
            channel_id=self.id,
            source='all',
            operation= 'import',
        )
        obj=self.env['import.magento1x.orders'].create(vals)
        return obj.import_now()

    def _fetch_magento1x_product_attributes(self,session, client, set_id=None,attribute_id=None):
        message=''
        data= None
        args = []
        if set_id:args+=[set_id]
        elif attribute_id:args+=[attribute_id]
        try:
            if set_id:
                data=  client.call(session, 'product_attribute.list',args)
            elif attribute_id:
                data=  client.call(session, 'product_attribute.info',args)
        except Error as e:
            e =str(e).strip('<').strip('>')
            message+='<br/>%s'%(e)
        except Exception as e:
            message+='<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )


    def _fetch_magento1x_product_attributes_sets(self,session, client):
        message=''
        data= None
        args = []
        try:
            data=  client.call(session, 'product_attribute_set.list',args)
        except Error as e:
            e =str(e).strip('<').strip('>')
            message+='<br/>%s'%(e)
        except Exception as e:
            message+='<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )
    @staticmethod
    def _fetch_magento1x_orders(client,session,**kwargs):
        result = dict(
            data=None,
            message=''
        )
        message=''
        data= None
        args = {}
        channel_id = kwargs.get('channel_id')
        if channel_id:
            if channel_id.magento1x_is_child_store:
                pass
                # channel_id = channel_id.magento1x_default_store_id
            args['store_id'] = channel_id.get_magento1x_store_id()
        if kwargs.get('order_ids'):
            args['increment_id'] ={kwargs.get('condition_type'):kwargs.get('order_ids')}
        if kwargs.get('from_date') or kwargs.get('to_date')  :
            args['created_at'] = dict()
            if kwargs.get('from_date') and kwargs.get('to_date'):
                fromDate = kwargs.get('from_date').strftime(MageDateTimeFomat)
                toDate = kwargs.get('to_date').strftime(MageDateTimeFomat)
                args['created_at'].update(
                {'from':fromDate, 'to':toDate})
            else:
                if kwargs.get('from_date'):
                    fromDate = kwargs.get('from_date').strftime(MageDateTimeFomat)
                    args['created_at'].update(dict(gt=fromDate))
                if kwargs.get('to_date'):
                    toDate = kwargs.get('to_date').strftime(MageDateTimeFomat)
                    args['created_at'].update({'lt':toDate})
        try:
            data=  client.call(session, 'order.list',[args])

        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)

        return dict(
            data=data,
            message=message
        )
    @staticmethod
    def _fetch_magento1x_order_data(client,session,increment_id,**kwargs):
        message=''
        data= None
        try:
            data=  client.call(
                session,
                'order.info',
                [increment_id]
            )
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )
    @staticmethod
    def _fetch_magento1x_partners(client,session,source='all',**kwargs):
        result = dict(
            data=None,
            message=''
        )
        message=''
        data= None
        args = {}
        if not  source=='all':
                partner_ids = list(set(kwargs.get('partner_ids','').split(',')))
                args['customer_id'] ={'in':list(partner_ids)}
        else:
            channel_id = kwargs.get('channel_id')
            if channel_id:
                if channel_id.magento1x_is_child_store:
                    pass
                    # channel_id = channel_id.magento1x_default_store_id
                # args['store_id'] = channel_id.get_magento1x_store_id()
        if kwargs.get('from_date') or kwargs.get('to_date')  :
            args['created_at'] = dict()
            if kwargs.get('from_date') and kwargs.get('to_date'):
                fromDate = kwargs.get('from_date').strftime(MageDateTimeFomat)
                toDate = kwargs.get('to_date').strftime(MageDateTimeFomat)
                args['created_at'].update(
                {'from':fromDate, 'to':toDate})
            else:
                if kwargs.get('from_date'):
                    fromDate = kwargs.get('from_date').strftime(MageDateTimeFomat)
                    args['created_at'].update(dict(gt=fromDate))
                if kwargs.get('to_date'):
                    toDate = kwargs.get('to_date').strftime(MageDateTimeFomat)
                    args['created_at'].update({'lt':toDate})

        try:
            data=  client.call(session, 'customer.list',[args])
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )
    @staticmethod
    def _fetch_magento1x_customer_address(client,session,customer_id,**kwargs):
        message=''
        data= None
        try:
            data=  client.call(
                session,
                'customer_address.list',
                [customer_id]
            )
        except Error as e:
            e =str(e).strip('<').strip('>')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )

    @staticmethod
    def _fetch_magento1x_products(client,session,**kwargs):
        result = dict(
            data=None,
            message=''
        )
        message=''
        data= None
        args = {}
        if kwargs.get('product_tmpl_ids'):
                product_ids  = list(set(kwargs.get('product_tmpl_ids').split(',')))
                args['product_id'] ={kwargs.get('condition_type'):list(product_ids)}
        args['type'] ={'neq':'configurable'}
        channel_id = kwargs.get('channel_id')
        store_code = channel_id.magento1x_store_code
        if kwargs.get('from_date') or kwargs.get('to_date')  :
            args['created_at'] = dict()
            if kwargs.get('from_date') and kwargs.get('to_date'):
                fromDate = kwargs.get('from_date') - timedelta(hours=4)
                fromDate = fromDate.strftime(MageDateTimeFomat)
                toDate = kwargs.get('to_date') + timedelta(hours=5)
                toDate = toDate.strftime(MageDateTimeFomat)
                args['created_at'].update(
                {'from':fromDate, 'to':toDate})
            else:
                if kwargs.get('from_date'):
                    fromDate = kwargs.get('from_date') - timedelta(hours=4)
                    fromDate = fromDate.strftime(MageDateTimeFomat)
                    args['created_at'].update(dict(gt=fromDate))
                if kwargs.get('to_date'):
                    toDate = kwargs.get('to_date') + timedelta(hours=5)
                    toDate = toDate.strftime(MageDateTimeFomat)
                    args['created_at'].update({'lt':toDate})

        try:
            data=  client.call(session, 'product.list',[args,store_code])
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        result['data'] = data
        _logger.info("===%r===="%(args))
        result['message'] = message
        return result

    @staticmethod
    def _fetch_magento1x_product_media(client,session,product_id,**kwargs):
        message=''
        data= dict()
        try:
            data['media']=client.call(session, 'product_media.list',[product_id])
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )

    @classmethod
    def _fetch_magento1x_product_data(cls,client,session,product_id,channel_id,**kwargs):
        message=''
        data= dict()
        store_code = channel_id.magento1x_store_code
        try:
            data=  client.call(
                session,
                'product.info',
                [product_id ,store_code, InfoFields]
            )
            media_res = cls._fetch_magento1x_product_media(client=client,session=session,product_id=product_id)
            media = media_res.get('data')
            if media:
                data['media']=media#client.call(session, 'product_media.list',[product_id])
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        return dict(
            data=data,
            message=message
        )

    def _fetch_magento1x_categories(self,session, client,source='all',store_category_id=None):
        message=''
        data= None
        args = []
        if source=='all' and store_category_id:
            args+=[store_category_id]
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

    @staticmethod
    def _fetch_magento1x_qty_data(client,session,product_ids,**kwargs):
        message=''
        data_list= []
        try:
            data_list=  client.call(
                session,
                'product_stock.list',
                [product_ids]
            )
        except Error as e:
            e =str(e).strip('>').strip('<')
            message += '<br/>%s'%(e)
        except Exception as e:
            message += '<br/>%s'%(e)
        data=dict(map(lambda item:(item.get('product_id'),item.get('qty')),data_list))

        return data

    @classmethod
    def _magento1x_get_product_images_vals(cls,media):
        vals = dict()
        for data in media.get('media'):
            image_url = data.get('url')
            if image_url:
                vals['image'] =cls.read_website_image_url(image_url)
                vals['image_url'] = image_url
            break
        return vals

    @staticmethod
    def magento1x_upload_image(session,client,product_id,image,image_name,operation):
        file = dict(
            content=image,
            mime='image/jpeg',
            name= image_name
        )
        media_data = dict(
            file=file,
            types=['image','thumbnail','small_image'],
            label='label'
        )
        post_data =[JL(product_id),media_data]
        if operation=='update':
            post_data = [JL(product_id),image_name,media_data]

        return client.call(session,'product_media.%s'%(operation),post_data
        )

    @classmethod
    def magento1x_create_category(cls,session,client,data,**kwargs):
        message=''
        obj_id= None
        parent_id = data.pop('parent_id',2)
        try:

            obj_id=  client.call(session, 'catalog_category.create',[parent_id,data])
        except Error as e:
            e =str(e).strip('<').strip('>')
            message += '<br/>For Categories %s<br/>%s'%(data.get('name'),e)
        except Exception as e:
            message += '<br/>For Categories %s<br/>%s'%(data.get('name'),e)
        return dict(
            obj_id=obj_id,
            message=message
        )

    @classmethod
    def magento1x_update_category(cls,session,client,data,**kwargs):
        message=''
        obj_id= None
        store_id = data.pop('store_id')
        try:

            obj_id=  client.call(session, 'catalog_category.update',[store_id,data])
        except Error as e:
            e =str(e).strip('<').strip('>')
            message += '<br/>For Categories %s<br/>%s'%(data.get('name'),e)
        except Exception as e:
            message += '<br/>For Categories %s<br/>%s'%(data.get('name'),e)
        return dict(
            obj_id=obj_id,
            message=message
        )

    @classmethod
    def magento1x_create_product(cls,session,client,data,channel_id,**kwargs):
        message=''
        debug = channel_id.debug=='enable'
        obj_id= None
        _type = data.pop('_type','simple')
        set_id = data.pop('set_id','4')
        sku = data.pop('sku','None')
        image = data.pop('image','None')
        store_code = channel_id.magento1x_store_code

        try:

            obj_id=  client.call(session, 'catalog_product.create',[_type,set_id,sku,data,store_code])
            if image:
                image_name = 'image_%s'%(sku)
                cls.magento1x_upload_image(session,client,obj_id,image,image_name,'create')
        except Error as e:
            e =str(e).strip('<').strip('>')
            message += '<br/>For Product %s<br/>%s'%(data.get('name'),e)
        except Exception as e:
            message += '<br/>For Product %s<br/>%s'%(data.get('name'),e)
        if debug:
            _logger.info("%r===%r==="%(data,message))
        return dict(
            obj_id=obj_id,
            message=message
        )

    @classmethod
    def magento1x_update_product(cls,session,client,product_id,data,channel_id,**kwargs):
        message=''
        status= False
        _type = data.pop('_type','simple')
        set_id = data.pop('set_id','4')
        sku = data.pop('sku','None')
        image = data.pop('image','None')
        store_code = channel_id.magento1x_store_code
        try:
            status=  client.call(session, 'catalog_product.update',[JL(product_id),data,store_code])
            if image:
                media_res = channel_id._fetch_magento1x_product_media(client=client,session=session,
                product_id=JL(product_id))
                message += media_res.get('message','')
                media = media_res.get('data',{}).get('media')
                if len(media):
                    image_name = EL(media).get('file')

                    cls.magento1x_upload_image(session,client,product_id,image,image_name,'update')
                else:
                    image_name = 'image_%s'%(sku)
                    cls.magento1x_upload_image(session,client,product_id,image,image_name,'create')
        except Error as e:
            e =str(e).strip('<').strip('>')
            message += '<br/>For Product %s<br/>%s'%(data.get('name'),e)
        except Exception as e:
            message += '<br/>For Product %s<br/>%s'%(data.get('name'),e)
        return dict(
            status=status,
            message=message
        )
