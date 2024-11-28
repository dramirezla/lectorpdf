from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import re
from PyPDF2 import PdfReader

class RecepFact(models.Model):
    _name = 'recpfact_xml'
    _description = 'Recep Fact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Nombre")
    description = fields.Text(string="Descripción")
    recpfact_xml_pdf = fields.Binary(string="Archivo PDF", attachment=True)
    recpfact_xml_pdf_name = fields.Char(string="Nombre del Archivo PDF")

    def check_attachments(self):
        # Buscar adjuntos relacionados con este registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'recpfact_xml'),
            ('res_id', '=', self.id)
        ])
        
        if not attachments:
            raise UserError('No se encontraron adjuntos en los mensajes internos.')

        # Procesar los adjuntos
        for attachment in attachments:
            if attachment.mimetype == 'application/zip':
                # Descomprimir el archivo ZIP
                zip_data = base64.b64decode(attachment.datas)
                with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zf:
                    for file_name in zf.namelist():
                        if file_name.endswith('.pdf'):
                            # Leer y asignar el archivo PDF al campo
                            pdf_content = zf.read(file_name)
                            self.recpfact_xml_pdf = base64.b64encode(pdf_content)
                            self.recpfact_xml_pdf_name = file_name
                            
                            # Procesar el archivo PDF
                            self._process_pdf(pdf_content)
                            return
                raise UserError('El archivo ZIP no contiene ningún archivo PDF.')

    def _process_pdf(self, pdf_content):
        try:
            # Leer el PDF
            reader = PdfReader(io.BytesIO(pdf_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text()

            if not text:
                raise UserError('No se pudo extraer texto del archivo PDF.')

            # Extraer el NIT y el precio con expresiones regulares
            nit = re.search(r'(?<=NIT:)\s*(\d+)', text)
            precio = re.search(r'(?<=Precio:)\s*\$?(\d+,\d+|\d+)', text)

            if not nit or not precio:
                raise UserError('No se encontraron los datos requeridos en el PDF.')

            # Validar si el precio tiene formato correcto
            total_amount = precio.group(1).replace(',', '')  # Eliminar comas si hay
            try:
                total_amount = float(total_amount)
            except ValueError:
                raise UserError('El precio en el PDF no tiene un formato válido.')

            # Guardar los valores extraídos en campos de la factura o hacer lo que necesites
            self.name = f'Factura {nit.group(1)}'
            self.description = f'NIT: {nit.group(1)} | Total: {total_amount}'
            # Si tienes un campo de factura relacionado, lo puedes usar aquí para crear la factura

        except Exception as e:
            raise UserError(f'Ocurrió un error inesperado al procesar el archivo PDF: {e}')
