from odoo import models, fields, api
from odoo.exceptions import UserError

class XRecepcionFacturas(models.Model):
    _name = 'account.move'
    _description = 'Recepción de Facturas'

    name = fields.Char(string='Nombre de la Factura')

    def check_attachments(self):
        # Este método debería contener la lógica de comprobación de adjuntos
        attachments = self.env['mail.attachment'].search([
            ('res_model', '=', 'x_recepcion_facturas'),
            ('res_id', '=', self.id)
        ])
        if not attachments:
            raise UserError('No se encontraron adjuntos en los mensajes internos.')
