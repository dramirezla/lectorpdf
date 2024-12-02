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


    ##no
    
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
    
        # Extraer y procesar el campo 'Total Neto'
        try:
            total_text = self.extract_field(pdf_text, 'Total Neto:', '\t')
            if total_text:  # Validar si el texto no está vacío
                # Extraer el número inicial hasta el segundo punto decimal
                match = re.search(r'\d+,\d+\.\d+', total_text)
                if match:
                    total_cleaned = match.group(0).replace(',', '')  # Eliminar la coma
                    data['amount_total'] = float(total_cleaned)  # Convertir a float
                else:
                    data['amount_total'] = 0.0  # Valor por defecto si no se encuentra
            else:
                data['amount_total'] = 0.0  # Valor por defecto si el texto está vacío
        except ValueError as e:
            raise UserError(f"Error al procesar el campo 'Total Neto': {str(e)}")


        # Extract product details
        products = self.extract_product_details(pdf_text)
        data['products'] = products
        
        # Cliente (si aplica en factura de proveedor)
        data['client_name'] = self.extract_field(pdf_text, 'Cliente:', '\n')
        data['client_nit'] = self.extract_field(pdf_text, 'NIT:', '\n', start_offset=1)
    
        return data

    def extract_product_details(self, pdf_text):
        """Extrae los detalles de los productos de la matriz."""
        product_details = []
        
        # Expresión regular para extraer las filas de productos
        # Esta regex busca el patrón de cada fila en la tabla
        product_pattern = re.compile(r'(\d+)\s+([^\d]+)\s+([A-Za-z]+)\s+(\d+)\s+\$([\d,\.]+)\s+\$([\d,\.]+)\s+\$([\d,\.]+)\s+(\w+)\s+([\d,\.]+)')
        
        matches = product_pattern.findall(pdf_text)
        
        for match in matches:
            product_code = match[0]  # Código
            description = match[1].strip()  # Descripción
            unit = match[2]  # Unidad de medida
            quantity = float(match[3])  # Cantidad
            price_unit = float(match[4].replace(',', ''))  # Precio unitario (eliminando comas)
            discount = float(match[5].replace(',', ''))  # Descuento
            charge = float(match[6].replace(',', ''))  # Cargo
            tax = match[7]  # Impuesto (en este caso IVA u otros)
            subtotal = float(match[8].replace(',', ''))  # Subtotal
            
            # Almacenamos los detalles del producto
            product_details.append({
                'product_code': product_code,
                'description': description,
                'unit': unit,
                'quantity': quantity,
                'price_unit': price_unit,
                'discount': discount,
                'charge': charge,
                'tax': tax,
                'subtotal': subtotal,
            })
        
        return product_details



    
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
            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': self.find_or_create_partner(
                    invoice_data['supplier_name'],
                    invoice_data['supplier_nit']
                ).id,
                'invoice_date': fields.Date.today(),  # Puedes usar invoice_data['invoice_date'] si es necesario
                'invoice_date_due': fields.Date.today(),  # O invoice_data['due_date']
                'amount_total': invoice_data['amount_total'],  # Asegurar que el total neto se agregue
                'invoice_line_ids': [],
            }
    
            # Agregar el total neto como el valor total de la factura
            invoice_vals['amount_total'] = invoice_data['amount_total']  # Agrega el Total Neto a la factura
    
            # Agregar las líneas de productos
            for product in invoice_data['products']:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'name': product['description'],  # Descripción del producto
                    'quantity': product['quantity'],  # Cantidad del producto
                    'price_unit': product['price_unit'],  # Precio unitario del producto
                    'tax_ids': [(6, 0, [self.env.ref('account.tax_iva').id])],  # Asume que el impuesto es IVA
                    'price_subtotal': product['subtotal'],  # Subtotal de la línea de producto
                }))
    
            # Crear la factura
            self.env['account.move'].create(invoice_vals)


    def find_or_create_partner(self, name, vat):
        """Busca o crea un partner basado en el nombre y NIT."""
        partner = self.env['res.partner'].search([('name', '=', name), ('vat', '=', vat)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'vat': vat,
                
            })
        return partner   
