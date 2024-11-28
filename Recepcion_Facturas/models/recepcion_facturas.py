from odoo import models, fields, api
from odoo.exceptions import UserError

class XRecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Factura')
    x_studio_validar = fields.Boolean(string="Validar", track_visibility='onchange')


    def check_attachments(self):
        """ Verifica si hay archivos adjuntos en los mensajes internos del registro """
        attachments = self.env['mail.attachment'].search([
            ('res_model', '=', 'x_recepcion_facturas'),
            ('res_id', '=', self.id)
        ])

        if not attachments:
            raise UserError('No se encontraron adjuntos en los mensajes internos.')

        for attachment in attachments:
            if attachment.mimetype == 'application/zip':
                self._process_zip_attachment(attachment)

    def _process_zip_attachment(self, attachment):
        """ Procesar archivo zip adjunto """
        # Aquí puedes agregar la lógica para descomprimir el archivo zip
        # y extraer un archivo XML, por ejemplo:
        pass
