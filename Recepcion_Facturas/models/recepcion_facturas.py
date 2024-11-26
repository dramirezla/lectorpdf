from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
import zipfile
import io

_logger = logging.getLogger(__name__)

class XRecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _description = 'Recepción de Facturas'

    x_name = fields.Char(string='Nombre')
    x_studio_validar = fields.Boolean(string='Validar')  # Verifica si este campo existe

    def write(self, values):
        # Verificamos si x_studio_validar ha sido modificado
        if 'x_studio_validar' in values:
            self.check_zip_attachment()  # Ejecutamos la comprobación si x_studio_validar ha cambiado
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
                
                # Intentar descomprimir el archivo ZIP y verificar el contenido
                try:
                    with zipfile.ZipFile(io.BytesIO(attachment.datas), 'r') as zip_ref:
                        zip_ref.testzip()  # Verificar si el ZIP es válido
                        _logger.info(f"ZIP file {attachment.name} is valid.")
                        # Aquí puedes agregar código para procesar el archivo XML dentro del ZIP
                except zipfile.BadZipFile:
                    _logger.error(f"Bad ZIP file: {attachment.name}")
                    raise UserError(f"El archivo adjunto '{attachment.name}' no es un archivo ZIP válido.")
                except Exception as e:
                    _logger.error(f"Error while handling ZIP file: {e}")
                    raise UserError(f"Hubo un error al procesar el archivo ZIP adjunto: {str(e)}")
            
            # Si se encuentra un archivo ZIP, mostramos un mensaje de error
            raise UserError(f"Se ha encontrado un archivo ZIP adjunto en el registro '{self.x_name}'. No se permite esta acción.")
        else:
            _logger.info("No ZIP attachments found.")
