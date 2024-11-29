from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import re
from PyPDF2 import PdfReader
import fitz

class RecepFact(models.Model):
    _name = 'recpfact'
    _description = 'Recep Fact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Nombre")
    description = fields.Text(string="Descripción")
    recpfact_xml = fields.Binary(string="Archivo PDF", attachment=True)
    pdf_file = fields.Binary(string='Archivo PDF', attachment=True)
    recpfact_pdf_name = fields.Char(string="Nombre del Archivo PDF")
    

    def check_attachments(self):
        # Buscar adjuntos relacionados con este registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'recpfact'),
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
                            self.recpfact_xml = base64.b64encode(pdf_content)
                            self.pdf_file = base64.b64encode(pdf_content)
                            self.recpfact_pdf_name = file_name
                            
                            # Procesar el archivo PDF
                            self._process_pdf()
                            #self.create_supplier_invoice()
                            return
                raise UserError('El archivo ZIP no contiene ningún archivo PDF.')

    #def _process_pdf(self, pdf_content):
    
    def extract_text_from_pdf(self, pdf_binary):
        """Extrae texto de un archivo PDF."""
        pdf_text = ""
        pdf_document = fitz.open(stream=pdf_binary, filetype="pdf")
        for page in pdf_document:
            pdf_text += page.get_text()
        pdf_document.close()
        return pdf_text

    def parse_invoice_data(self, pdf_text):
        """Parsea datos relevantes de la factura desde el texto."""
        data = {}

        # Datos del proveedor
        data['supplier_name'] = self.extract_field(pdf_text, 'Nombre Comercial:', '\n')
        data['supplier_nit'] = self.extract_field(pdf_text, 'NIT:', '\n')

        # Datos de la factura
        data['invoice_number'] = self.extract_field(pdf_text, 'FACTURA ELECTR\u00d3NICA DE VENTA', '\n')
        data['invoice_date'] = self.extract_field(pdf_text, 'Emisi\u00f3n:', '\n').split()[0]
        data['due_date'] = self.extract_field(pdf_text, 'Vencimiento:', '\n')

        
        try:
            # Extraer y procesar el campo 'Total Neto'
            total_text = self.extract_field(pdf_text, 'Total Neto:', '\n')
            if total_text:  # Validar si el texto no está vacío
                total_cleaned = total_text.replace('$', '').replace(',', '').strip()
                data['amount_total'] = float(total_cleaned) if total_cleaned else 0.0
            else:
                data['amount_total'] = 0.0  # Valor por defecto si no se encuentra
        except ValueError as e:
            raise UserError(f"Error al procesar el campo 'Total Neto': {str(e)}")

        
        
        # Cliente (si aplica en factura de proveedor)
        data['client_name'] = self.extract_field(pdf_text, 'Cliente:', '\n')
        data['client_nit'] = self.extract_field(pdf_text, 'NIT:', '\n', start_offset=1)

        return data

    def extract_field(self, text, start_key, end_key, start_offset=0):
        """Extrae un campo delimitado por claves de inicio y fin."""
        start_index = text.find(start_key) + len(start_key) + start_offset
        end_index = text.find(end_key, start_index)
        return text[start_index:end_index].strip()

    def _process_pdf(self):
        """Procesa el archivo PDF y crea una factura de proveedor."""
        for record in self:
            if not record.pdf_file:
                raise UserError('No hay un archivo PDF cargado para procesar.')
    
            # Decodificar el archivo PDF desde base64
            pdf_binary = base64.b64decode(record.pdf_file)
            pdf_text = self.extract_text_from_pdf(pdf_binary)
    
            # Parsear los datos de la factura
            invoice_data = self.parse_invoice_data(pdf_text)
    
            # Crear factura de proveedor en Odoo
            self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.find_or_create_partner(
                    invoice_data['supplier_name'],
                    invoice_data['supplier_nit']
                ).id,
                'invoice_date': invoice_data['invoice_date'],
                'invoice_date_due': invoice_data['due_date'],
                'invoice_line_ids': [(0, 0, {
                    'name': 'Cargos Facturados',
                    'quantity': 1,
                    'price_unit': invoice_data['amount_total'],
                })]
            })
    def find_or_create_partner(self, name, vat):
        """Busca o crea un partner basado en el nombre y NIT."""
        partner = self.env['res.partner'].search([('name', '=', name), ('vat', '=', vat)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'vat': vat,
                
            })
        return partner   
