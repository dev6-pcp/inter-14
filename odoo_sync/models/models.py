# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .odoo_api import OdooApi
from odoo.exceptions import ValidationError
from datetime import datetime


class MigrateModels(models.Model):
    _name = 'migarator.models'
    src_model = fields.Char(string='Src Model', required=True)
    dest_model = fields.Char(string='Dest Model', required=True)
    src_res_id = fields.Integer(string='Src Res Id')
    dest_res_id = fields.Integer(string='Dest Res Id')
    finsihed = fields.Boolean(string='Finished')
    state = fields.Selection(string='Status',
                             selection=[('draft', 'Draft'),
                                        ('done', 'Done'), ],
                             default='draft', )

    fields_dest_not_in = fields.Text(
        string='Fields  DEST Not In',
        copy=False)

    line_ids = fields.One2many(
        comodel_name='migarator.models.lines',
        inverse_name='migarator_id',
        string='Line_ids',
        required=False)
    length = fields.Integer(
        string='Length',
        required=False)

    batch_size = fields.Integer(
        string='Batch Size',
        required=False)
    src_domain = fields.Char(
        string='SRC Domain',
        required=False, default="[]")
    dest_domain = fields.Char(
        string='DEST Domain',
        required=False, default="[]")
    data = fields.Text(string="Data", copy=True)
    active = fields.Boolean(
        string='Active',
        default=True)
    for_server = fields.Boolean(
        string='For server',
        required=False)
    fields = fields.Selection(
        string='Fields',
        selection=[('many2one', 'Many2one'),
                   ('many2many', 'Many2many'),
                   ('many2one_reference', 'Many2one_reference'),
                   ('selection', 'Selection'),
                   ('all_with_relation', 'All Without Relation'),
                   ('all', 'All'),
                   ],
        required=True, )


    def clear_data(self):
        self.data = ""

    def get_api(self):
        with_user = self.env['ir.config_parameter'].sudo()
        migarator_host_name = with_user.get_param('odoo_migrator.migarator_host_name')
        migarator_database = with_user.get_param('odoo_migrator.migarator_database')
        migarator_user_name = with_user.get_param('odoo_migrator.migarator_user_name')
        migarator_password = with_user.get_param('odoo_migrator.migarator_password')
        api = OdooApi(migarator_host_name, migarator_database, migarator_user_name, migarator_password)
        return api

    def get_data_from_api(self):
        if self.for_server:
            api = self.get_api()
            data = []
            loop = 1
            if not self.data:
                if self.length:
                    for loop in range(1, (self.length / self.batch_size) + 1):
                        if self.src_domain:
                            data +=self.env[self.src_model].sudo().search_read(domain=eval(self.src_domain),limit=self.batch_size,offset=loop,fields=self.line_ids.mapped('src_field'))
                        else:
                            data +=self.env[self.src_model].sudo().search_read(domain=[],limit=self.batch_size,offset=loop,fields=self.line_ids.mapped('src_field'))

                        if data:
                            loop = max(data, key=lambda x: x['id'])
                else:
                    if self.src_domain:
                        data += self.env[self.src_model].sudo().search_read(domain=eval(self.src_domain),
                                                                     fields=self.line_ids.mapped('src_field'))

                    else:
                        data += self.env[self.src_model].sudo().search_read(domain=[],
                                                                     fields=self.line_ids.mapped('src_field'))
                print("Ddata",data)
                self.data = data
        else:
            api = self.get_api()
            data = []
            loop = 1
            if not self.data:
                if self.length:
                    for loop in range(1, (self.length / self.batch_size) + 1):
                        if self.src_domain:
                            data += api.search6(self.src_model, eval(self.src_domain), self.line_ids.mapped('src_field'),
                                                limit=self.batch_size,
                                                offset=loop)
                        else:
                            data += api.search6(self.src_model, [[]], self.line_ids.mapped('src_field'),
                                                limit=self.batch_size,
                                                offset=loop)
                        if data:
                            loop = max(data, key=lambda x: x['id'])
                else:
                    if self.src_domain:
                        data += api.search2(self.src_model, eval(self.src_domain), self.line_ids.mapped('src_field'),
                                            )
                    else:
                        data += api.search2(self.src_model, [[]], self.line_ids.mapped('src_field'))
                self.data = data

    def create_data(self):
        self.create_syc_id_field()
        if eval(self.data):
            recods = []
            for datas in eval(self.data):
                if 1 == 1:
                    val = {}
                    for line in self.line_ids:
                        if line.src_field in datas.keys():
                            if line.is_many_2_one:
                                val.update(
                                    {
                                        line.dest_field: datas.get(line.src_field)[0] if datas.get(
                                            line.src_field) else False
                                    }
                                )
                            elif line.is_many_2_many:
                                val.update(
                                    {
                                        line.dest_field: [(6, 0, [x for x in datas.get(line.src_field)])]
                                    }
                                )
                            elif line.is_selection:
                                val.update(
                                    {
                                        line.dest_field: str(datas[line.src_field])
                                    }
                                )
                            elif line.custom_value:
                                val.update(
                                    {
                                        line.dest_field: str(line.value)
                                    }
                                )
                            else:
                                val.update(
                                    {
                                        line.dest_field: datas[line.src_field]
                                    }
                                )

                    recods.append(val)
        for recod in recods:
            self.create_record(recod)
        self.state = 'done'

    def check_fields(self):
        api = self.get_api()
        data = api.search6(self.src_model, [[]], [], limit=20)
        types = []
        if self.fields == 'many2one':
            types = ['many2one']
        if self.fields == 'many2many':
            types = ['many2many']
        if self.fields == 'many2one_reference':
            types = ['many2one_reference']
        if self.fields == 'selection':
            types = ['selection']

        if self.fields == 'all_with_relation':
            types = ['selection', 'binary', 'boolean', 'char', 'date', 'datetime', 'float', 'html', 'integer',
                     'monetary', 'reference', 'text']

        if self.fields == 'all':
            types = ['selection', 'many2one', 'many2many', 'binary', 'boolean', 'char', 'date', 'datetime', 'float',
                     'html', 'integer', 'monetary', 'reference', 'text']

        fields = []
        lines = []
        for datas in data:
            for key in datas.keys():
                if key not in fields:
                    fields.append(key)
        fields_dest_not_in = ""
        for field in fields:

            record = self.check_field_found(field)
            if record:
                if record.ttype in types and record.ttype != 'one2many' and field not in ['activity_state']:
                    lines.append((0, 0, {
                        'src_field': field,
                        'dest_field': field,
                        'is_many_2_one': True if record.ttype == 'many2one' else False,
                        'is_many_2_many': True if record.ttype == 'many2many' else False,
                        'is_selection': True if record.ttype == 'selection' else False,
                    }))
            else:
                print("D>D", field)
                fields_dest_not_in += field + "\n"
        self.fields_dest_not_in = fields_dest_not_in
        self.line_ids = [(5, 0, 0)]
        self.line_ids = lines

    def check_field_found(self, field):
        record = self.env['ir.model.fields'].search([('model_id.model', '=', self.dest_model), ('name', '=', field)])
        if record:
            return record
        else:
            return False



    def create_record(self, record):
        if self.for_server:
            api = self.get_api()
            domain = [['x_syc_id', '=', record.get('x_syc_id')]]
            if eval(self.dest_domain):
                domain += eval(self.dest_domain)
            if domain:
                print("D>D>>",domain)
                res = api.search1(self.dest_model, [domain])
                if res:
                    api.update(self.dest_model, res[0], record)
                else:
                    api.create(self.dest_model, record)
            else:
                api.create(self.dest_model, record)
        else:
            domain=[('x_syc_id','=',record.get('x_syc_id'))]
            if eval(self.dest_domain):
                domain += eval(self.dest_domain)
            if domain:
                res = self.env[self.dest_model].sudo().search(domain)
                if res:
                    res.sudo().write(record)
                else:
                    self.env[self.dest_model].sudo().create(record)
            else:
                self.env[self.dest_model].sudo().create(record)

    def reset_to_draft(self):
        self.state = 'draft'

    def create_syc_id_field(self):
        res=self.env['ir.model.fields'].sudo().search([('model_id.model', '=', self.dest_model), ('name', '=', 'x_syc_id')])
        if not res:
            model_id=self.env['ir.model'].sudo().search(
                [('model', '=', self.dest_model)],limit=1)
            res = self.env['ir.model.fields'].sudo().create({
                'name':'x_syc_id',
                'model_id':model_id.id,
                'ttype':'integer',
               })
    def create_old_serial_field(self):
        res=self.env['ir.model.fields'].sudo().search([('model_id.model', '=', self.dest_model), ('name', '=', 'x_serial')])
        if not res:
            model_id=self.env['ir.model'].sudo().search(
                [('model', '=', self.dest_model)],limit=1)
            res = self.env['ir.model.fields'].sudo().create({
                'name':'x_serial',
                'model_id':model_id.id,
                'ttype':'char',
               })
    def sync_all(self):
        for rec in self:
            rec.reset_to_draft()
            rec.clear_data()
            rec.get_data_from_api()
            rec.create_data()




class MigrateModelsLines(models.Model):
    _name = 'migarator.models.lines'
    migarator_id = fields.Many2one(
        comodel_name='migarator.models',
        string='Migarator_id',
        required=False)
    src_field = fields.Char(string='Src Field', required=True)
    dest_field = fields.Char(string='Dest Field', required=True)
    is_many_2_one = fields.Boolean(string='Is Many2one Field', required=True)
    is_many_2_many = fields.Boolean(string='Is Many2many Field', required=True)
    is_selection = fields.Boolean(string='Is Selection Field', required=True)
    custom_value = fields.Boolean(string='Is Custom Value')
    value = fields.Char(string='Custom Value')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    migarator_host_name = fields.Char(string='Host Name')
    migarator_database = fields.Char(string='Database')
    migarator_user_name = fields.Char(string='User Name')
    migarator_password = fields.Char(string='Password')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        with_user = self.env['ir.config_parameter'].sudo()
        with_user.set_param('odoo_migrator.migarator_host_name', self.migarator_host_name)
        with_user.set_param('odoo_migrator.migarator_database', self.migarator_database)
        with_user.set_param('odoo_migrator.migarator_user_name', self.migarator_user_name)
        with_user.set_param('odoo_migrator.migarator_password', self.migarator_password)

        return res

    @api.model
    def get_values(self):
        values = super(ResConfigSettings, self).get_values()
        with_user = self.env['ir.config_parameter'].sudo()
        values['migarator_host_name'] = with_user.get_param('odoo_migrator.migarator_host_name')
        values['migarator_database'] = with_user.get_param('odoo_migrator.migarator_database')
        values['migarator_user_name'] = with_user.get_param('odoo_migrator.migarator_user_name')
        values['migarator_password'] = with_user.get_param('odoo_migrator.migarator_password')

        return values







