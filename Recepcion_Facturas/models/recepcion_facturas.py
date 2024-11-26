from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class XRecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _description = 'Recepción de Facturas'

    x_name = fields.Char(string='Nombre')

    def write(self, values):
        # Verificamos si x_name ha sido modificado
        if 'x_studio_validar' in values:
            self.check_zip_attachment()  # Ejecutamos la comprobación si x_name ha cambiado
        # Ejecutamos el método estándar de escritura
        res = super(XRecepcionFacturas, self).write(values)
        return res

    def check_zip_attachment(self):
        # Buscamos adjuntos de tipo ZIP relacionados con este registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('mimetype', '=', 'application/zip')
        ])

        # Depuración: Verifica si se están recuperando los adjuntos
        if attachments:
            for attachment in attachments:
                _logger.info(f"Attachment found: {attachment.name}, MimeType: {attachment.mimetype}")
            # Si se encuentra un archivo ZIP, mostramos un mensaje de error
            raise UserError(f"Se ha encontrado un archivo ZIP adjunto en el registro '{self.x_name}'. No se permite esta acción.")
        else:
            _logger.info("No ZIP attachments found.")

