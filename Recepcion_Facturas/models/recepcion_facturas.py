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
        # Log para verificar si se ejecuta el método write
        _logger.info(f"Executing write with values: {values}")
        
        # Verificamos si x_studio_validar ha sido modificado
        if 'x_studio_validar' in values:
            _logger.info(f"Detected change in 'x_studio_validar', checking for ZIP attachments.")
            self.check_zip_attachment()  # Ejecutamos la comprobación si x_studio_validar ha cambiado
        
        # Ejecutamos el método estándar de escritura
        res = super(XRecepcionFacturas, self).write(values)
        return res

    def check_zip_attachment(self):
        # Log para indicar que estamos comprobando los adjuntos
        _logger.info(f"Checking ZIP attachment for record '{self.x_name}' (ID: {self.id})")
        
        # Buscamos adjuntos de tipo ZIP relacionados con este registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('mimetype', '=', 'application/zip')
        ])

        # Si no se encuentran archivos ZIP, lo indicamos en los logs
        if not attachments:
            _logger.info("No ZIP attachments found.")
        else:
            # Si se encuentra un archivo ZIP, procesamos cada adjunto
            for attachment in attachments:
                _logger.info(f"Found ZIP attachment: {attachment.name}, MimeType: {attachment.mimetype}")
                
                try:
                    # Intentamos abrir y verificar si el archivo ZIP es válido
                    with zipfile.ZipFile(io.BytesIO(attachment.datas), 'r') as zip_ref:
                        zip_ref.testzip()  # Verificar si el ZIP es válido
                        _logger.info(f"ZIP file '{attachment.name}' is valid.")
                        
                        # Aquí puedes agregar código adicional para procesar el archivo XML dentro del ZIP
                        
                except zipfile.BadZipFile:
                    # Si el archivo no es un ZIP válido, lanzamos un error
                    _logger.error(f"Bad ZIP file: {attachment.name}")
                    raise UserError(f"El archivo adjunto '{attachment.name}' no es un archivo ZIP válido.")
                except Exception as e:
                    # Si ocurre otro error, lo registramos y lanzamos un error
                    _logger.error(f"Error processing ZIP file '{attachment.name}': {str(e)}")
                    raise UserError(f"Hubo un error al procesar el archivo ZIP adjunto '{attachment.name}': {str(e)}")
            
            # Si se ha encontrado un archivo ZIP, mostramos un mensaje de error
            raise UserError(f"Se ha encontrado un archivo ZIP adjunto en el registro '{self.x_name}'. No se permite esta acción.")
