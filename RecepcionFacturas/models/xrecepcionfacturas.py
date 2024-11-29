from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import re
from PyPDF2 import PdfReader

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
                            self._process_pdf(self)
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

        # Totales
        data['amount_total'] = float(self.extract_field(pdf_text, 'Total Neto:', '\n').replace('$', '').replace(',', '').strip())
        data['amount_tax'] = float(self.extract_field(pdf_text, 'Total impuestos IVA:', '\n').replace('$', '').replace(',', '').strip())

        # Cliente (si aplica en factura de proveedor)
        data['client_name'] = self.extract_field(pdf_text, 'Cliente:', '\n')
        data['client_nit'] = self.extract_field(pdf_text, 'NIT:', '\n', start_offset=1)

        return data

    def extract_field(self, text, start_key, end_key, start_offset=0):
        """Extrae un campo delimitado por claves de inicio y fin."""
        start_index = text.find(start_key) + len(start_key) + start_offset
        end_index = text.find(end_key, start_index)
        return text[start_index:end_index].strip()

    def _process_pdf(self, pdf_content):
        """Crea una factura de proveedor en Odoo basada en el PDF."""
        for record in self:
            pdf_binary = record.pdf_file.decode('base64')
            pdf_text = self.extract_text_from_pdf(pdf_binary)
            invoice_data = self.parse_invoice_data(pdf_text)

            # Crear factura de proveedor en Odoo
            self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.find_or_create_partner(invoice_data['supplier_name'], invoice_data['supplier_nit']).id,
                'invoice_date': invoice_data['invoice_date'],
                'invoice_date_due': invoice_data['due_date'],
                'amount_total': invoice_data['amount_total'],
                'amount_tax': invoice_data['amount_tax'],
                'invoice_line_ids': [(0, 0, {
                    'name': 'Cargos Facturados',
                    'quantity': 1,
                    'price_unit': invoice_data['amount_total'] - invoice_data['amount_tax'],
                })]
            })

    def find_or_create_partner(self, name, vat):
        """Busca o crea un partner basado en el nombre y NIT."""
        partner = self.env['res.partner'].search([('name', '=', name), ('vat', '=', vat)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'vat': vat,
                'supplier': True,
            })
        return partner   
