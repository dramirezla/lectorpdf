from odoo import models, fields, api
from odoo.exceptions import UserError

class XRecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _description = 'Recepción de Facturas'

    x_name = fields.Char(string='Nombre')
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
            # Si encontramos un archivo ZIP, mostramos una ventana emergente con error
            raise UserError(f"Se ha encontrado un archivo ZIP adjunto en el registro '{self.x_name}'. No se permite esta acción.")
