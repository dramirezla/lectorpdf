from odoo import models, fields, api
from odoo.exceptions import UserError

class factPopup(models.Model):
    _name = 'recpfact'
    _description = 'Recep Fact'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(string="Nombre")
    description = fields.Text(string="Descripción")
    def check_attachments(self):
        # Este método debería contener la lógica de comprobación de adjuntos
        attachments = self.env['mail.attachment'].search([
            ('res_model', '=', 'recpfact'),
            ('res_id', '=', self.id)
        ])
        if not attachments:
            raise UserError('No se encontraron adjuntos en los mensajes internos.')
