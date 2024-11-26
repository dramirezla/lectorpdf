from odoo import models, fields, api
import zipfile
import os

class XRecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _description = 'Recepción de Facturas'

    x_name = fields.Char(string='Descripcion')
    message_ids = fields.One2many('mail.message', 'res_id', string='Messages', domain=[('model', '=', 'x_recepcion_facturas')])

    @api.model
    def create(self, values):
        record = super(XRecepcionFacturas, self).create(values)
        record.check_zip_attachment()
        return record

    def write(self, values):
        res = super(XRecepcionFacturas, self).write(values)
        # Solo ejecutar la comprobación si se está modificando el campo x_name
        if 'x_name' in values:
            self.check_zip_attachment()
        return res

    def check_zip_attachment(self):
        # Comprobamos si hay adjuntos en el registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'x_recepcion_facturas'),
            ('res_id', '=', self.id),
            ('mimetype', '=', 'application/zip')
        ])

        if attachments:
            # Si encontramos un archivo ZIP, lo registramos en el log
            _logger = self.env['ir.logging'].create({
                'name': 'Zip Attachment Found',
                'type': 'server',
                'dbname': self._cr.dbname,
                'message': f'ZIP file found in the attachments of {self.x_name}',
                'level': 'INFO'
            })
