from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import re
from PyPDF2 import PdfReader
import fitz


class RecepFact(models.Model):
    _name = 'recpfact2'
    _description = 'Recep Fact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    #Definicion de campos
    name = fields.Char(string="Nombre")
    description = fields.Text(string="Descripción")
    recpfact_xml = fields.Binary(string="Archivo PDF", attachment=True)
    pdf_file = fields.Binary(string='Archivo PDF', attachment=True)
    recpfact_pdf_name = fields.Char(string="Nombre del Archivo PDF")

    
    def check_attachments(self):
        # Buscar adjuntos relacionados con este registro
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'recpfact2'),
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

    # Definir el método parse_products_matrix
    def parse_products_matrix(self, products_matrix):
        # Dividir el string en líneas
        lines = products_matrix.strip().split("\n")
        
        # Consolidar líneas mal separadas
        consolidated_lines = []
        buffer = ""
    
        for line in lines:
            if line[0].isdigit() and (buffer and not buffer[0].isdigit()):  # Nueva fila detectada
                consolidated_lines.append(buffer.strip())
                buffer = line
            else:
                buffer += f" {line.strip()}"
        if buffer:
            consolidated_lines.append(buffer.strip())
    
        # Procesar las líneas
        parsed_products = []
        for line in consolidated_lines:
            columns = line.split()  # Dividir la línea en columnas
    
            # Validar que haya suficientes columnas para procesar
            if len(columns) < 7:
                raise ValueError(f"Línea con formato incorrecto: {line}")
    
            # Mapear únicamente las columnas necesarias
            parsed_products.append({
                '#': columns[0],
                'CÓDIGO': columns[1],
                'DESCRIPCIÓN': " ".join(columns[2:-5]),  # Descripción hasta antes de las últimas 5 columnas
                'CANTIDAD': columns[-5],
                'PRECIO UNITARIO': columns[-4],
                'IMPUESTOS': " ".join(columns[-3:-1]),  # Impuestos agrupados
                'SUBTOTAL': columns[-1],
            })
        raise UserError(f"{parsed_products}")
        return parsed_products



    def parse_invoice_data(self, pdf_text):
        """Parsea datos relevantes de la factura desde el texto."""
        data = {
            'supplier_name': self.extract_field(pdf_text, 'Nombre Comercial:', '\n'),
            'supplier_nit': self.extract_field(pdf_text, 'NIT:', '\n'),
            'product_lines': [],
        }
        products_matrix = self.extract_field(pdf_text, 'acuerdo', 'CUFE')
        
        # Llamada correcta a la función parse_products_matrix usando self
        parsed_products = self.parse_products_matrix(products_matrix)
        
        for product in parsed_products:
            data['product_lines'].append({
                'description': product['DESCRIPCIÓN'],
                'quantity': float(product['MEDIDA'].replace(',', '')),
                'unit_price': float(product['PRECIO'].replace('$', '').replace(',', '')),
                'discount': float(product['DESCUENTO'].replace('$', '').replace(',', '')),
                'charge': float(product['UNITARIO'].replace('$', '').replace(',', '')),
                'taxes': product['IMPUESTOS'],
                'subtotal': float(product['SUBTOTAL'].replace('$', '').replace(',', '')),
            })
        
        return data


    #def _process_pdf(self, pdf_content):
    
    def extract_text_from_pdf(self, pdf_binary):
        """Extrae texto de un archivo PDF."""
        pdf_text = ""
        pdf_document = fitz.open(stream=pdf_binary, filetype="pdf")
        for page in pdf_document:
            pdf_text += page.get_text()
        pdf_document.close()
        return pdf_text


        
        for match in matches:
            description = match[2].strip().replace('\n', ' ')  # Unimos líneas de descripción
            quantity = float(match[3].replace(',', ''))
            unit_price = float(match[4].replace(',', ''))
            discount = float(match[5].replace(',', ''))
            charge = float(match[6].replace(',', ''))
            taxes = match[7] or '0%'  # Si no hay IVA, usamos '0%'
            subtotal = float(match[8].replace(',', ''))
    
            data['product_lines'].append({
                'description': description,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount': discount,
                'charge': charge,
                'taxes': taxes,
                'subtotal': subtotal,
            })
    
        
        return data



    def get_tax_id_from_string(self, tax_string):
        """Convierte un texto de impuesto en un registro de impuesto de Odoo."""
        tax_percentage = float(re.search(r'\d+\.\d+', tax_string).group())
        tax = self.env['account.tax'].search([('amount', '=', tax_percentage)], limit=1)
        if not tax:
            raise UserError(f"No se encontró el impuesto con el porcentaje {tax_percentage}%.")
        return [(4, tax.id)]  # Formato para Many2many


    
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
            product_lines = invoice_data.get('product_lines', [])
    
            # Crear factura de proveedor en Odoo
            invoice = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.find_or_create_partner(
                    invoice_data['supplier_name'],
                    invoice_data['supplier_nit']
                ).id,
                'invoice_date': fields.Date.today(),  # Puedes ajustar según los datos de la factura
                'invoice_date_due': fields.Date.today(),  # Puedes ajustar según los datos de la factura
            })
    
            # Agregar líneas de factura
            for line in product_lines:
                self.env['account.move.line'].create({
                    'move_id': invoice.id,
                    'name': line['description'],  # Descripción del producto
                    'quantity': line['quantity'],  # Cantidad
                    'price_unit': line['unit_price'],  # Precio unitario
                    'tax_ids': line['tax_ids'],  # Impuestos
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
