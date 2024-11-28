from odoo import models, fields, api
from odoo.exceptions import UserError

class XRecepcionFacturas(models.Model):
    _name  = 'x_recepcion_facturas'
    def check_attachments(self):
        # Este método debería contener la lógica de comprobación de adjuntos
        attachments = self.env['mail.attachment'].search([
            ('res_model', '=', 'x_recepcion_facturas'),
            ('res_id', '=', self.id)
        ])
        if not attachments:
            raise UserError('No se encontraron adjuntos en los mensajes internos.')
