from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import zipfile
import io
import xml.etree.ElementTree as ET

class RecepFact(models.Model):
    _name = 'recpfact'
    _description = 'Recep Fact'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Nombre")
    description = fields.Text(string="Descripción")
    recpfact_xml = fields.Binary(string="Archivo XML", attachment=True)
    recpfact_xml_name = fields.Char(string="Nombre del Archivo XML")

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
                        if file_name.endswith('.xml'):
                            # Leer y asignar el archivo XML al campo
                            xml_content = zf.read(file_name)
                            self.recpfact_xml = base64.b64encode(xml_content)
                            self.recpfact_xml_name = file_name
                            
                            # Procesar el archivo XML
                            self._process_xml(xml_content)
                            return
                raise UserError('El archivo ZIP no contiene ningún archivo XML.')

    def _process_xml(self, xml_content):
        try:
            # Parsear el contenido del XML
            root = ET.fromstring(xml_content)
            namespaces = {node[0]: node[1] for _, node in ET.iterparse(io.BytesIO(xml_content), events=['start-ns'])}

            # Depuración: Registrar namespaces y contenido inicial
            _logger = self.env['ir.logging']
            _logger.create({
                'name': 'XML Processing',
                'type': 'server',
                'level': 'info',
                'message': f"Namespaces detectados: {namespaces}",
            })

            # Extraer datos del proveedor
            supplier_name = root.findtext('.//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name', namespaces=namespaces)
            supplier_vat = root.findtext('.//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', namespaces=namespaces)

            # Depuración: Registrar valores extraídos
            _logger.create({
                'name': 'XML Processing',
                'type': 'server',
                'level': 'info',
                'message': f"Proveedor detectado: {supplier_name}, NIT: {supplier_vat}",
            })

            if not supplier_name or not supplier_vat:
                raise UserError('El archivo XML no contiene datos válidos del proveedor.')

            # Buscar o crear el proveedor
            supplier = self.env['res.partner'].search([('vat', '=', supplier_vat)], limit=1)
            if not supplier:
                supplier = self.env['res.partner'].create({
                    'name': supplier_name,
                    'vat': supplier_vat
                })

            # Extraer totales y líneas de factura
            total_amount = root.findtext('.//cac:LegalMonetaryTotal/cbc:PayableAmount', namespaces=namespaces)
            currency = root.findtext('.//cbc:DocumentCurrencyCode', namespaces=namespaces)

            # Depuración: Registrar totales
            _logger.create({
                'name': 'XML Processing',
                'type': 'server',
                'level': 'info',
                'message': f"Total detectado: {total_amount}, Moneda: {currency}",
            })

            if not total_amount or not currency:
                raise UserError('El archivo XML no contiene datos válidos del total.')

            invoice_lines = []
            for line in root.findall('.//cac:InvoiceLine', namespaces=namespaces):
                description = line.findtext('.//cac:Item/cbc:Description', namespaces=namespaces)
                quantity = line.findtext('.//cbc:InvoicedQuantity', namespaces=namespaces)
                price = line.findtext('.//cac:Price/cbc:PriceAmount', namespaces=namespaces)

                if description and quantity and price:
                    invoice_lines.append((0, 0, {
                        'name': description,
                        'quantity': float(quantity),
                        'price_unit': float(price),
                    }))

            if not invoice_lines:
                raise UserError('El archivo XML no contiene líneas de factura válidas.')

            # Crear la factura de compra
            self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': supplier.id,
                'invoice_date': fields.Date.today(),
                'currency_id': self.env['res.currency'].search([('name', '=', currency)], limit=1).id,
                'invoice_line_ids': invoice_lines,
                'amount_total': float(total_amount)
            })
        except ET.ParseError:
            raise UserError('El archivo XML no tiene un formato válido.')
        except Exception as e:
            raise UserError(f'Ocurrió un error al procesar el archivo XML: {e}')
