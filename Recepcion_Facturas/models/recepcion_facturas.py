import base64
import zipfile
import io
from odoo import models, fields, api
from xml.etree import ElementTree as ET
import logging

_logger = logging.getLogger(__name__)

class RecepcionFacturas(models.Model):
    _name = 'x_recepcion_facturas'
    _inherit = ['mail.thread']
    _description = 'Recepción de Facturas'

    x_name = fields.Char(string="Nombre", required=True, track_visibility='onchange')
    message_attachment_ids = fields.One2many('ir.attachment', 'res_id', string="Archivos Adjuntos", domain=[('res_model', '=', 'x_recepcion_facturas')])

    @api.model
    def _procesar_adjuntos(self, record):
        # Verificar si el registro tiene adjuntos
        attachments = record.message_attachment_ids
        if not attachments:
            _logger.warning("No se encontraron adjuntos para el registro %s", record.id)
            return

        for attachment in attachments:
            # Verificar que el adjunto es un archivo ZIP
            if attachment.mimetype == 'application/zip':
                _logger.info("Procesando archivo ZIP: %s", attachment.name)
                zip_content = base64.b64decode(attachment.datas)
                try:
                    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                        # Verificar que el archivo ZIP contiene archivos
                        file_names = z.namelist()
                        if not file_names:
                            _logger.warning("El archivo ZIP no contiene archivos: %s", attachment.name)
                            continue
                        
                        for file_name in file_names:
                            # Verificar que el archivo es un XML
                            if file_name.endswith('.xml'):
                                _logger.info("Procesando archivo XML: %s", file_name)
                                with z.open(file_name) as xml_file:
                                    xml_content = xml_file.read()
                                    self._guardar_xml_como_adjunto(record, file_name, xml_content)
                                    self._crear_factura_desde_xml(xml_content)
                except zipfile.BadZipFile:
                    _logger.error("El archivo adjunto no es un ZIP válido: %s", attachment.name)
                except Exception as e:
                    _logger.error("Error al procesar archivo ZIP: %s", e)

    def _guardar_xml_como_adjunto(self, record, file_name, xml_content):
        """Guardar el XML como archivo adjunto."""
        attachment_vals = {
            'name': file_name,  # Nombre del archivo adjunto
            'type': 'binary',   # Tipo de archivo adjunto
            'datas': base64.b64encode(xml_content),  # Codificar el contenido XML en base64
            'mimetype': 'application/xml',  # Tipo MIME
            'res_model': 'x_recepcion_facturas',  # Relacionar el adjunto con el modelo actual
            'res_id': record.id,  # Relacionar el adjunto con el registro específico
        }
        self.env['ir.attachment'].create(attachment_vals)

    def _crear_factura_desde_xml(self, xml_content):
        tree = ET.fromstring(xml_content)
        datos_factura = self._leer_datos_xml(tree)
        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': datos_factura['partner_id'],
            'invoice_date': datos_factura['invoice_date'],
            'invoice_line_ids': datos_factura['invoice_line_ids'],
        })

    def _leer_datos_xml(self, tree):
        namespaces = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }
        # Proveedor
        supplier_vat = tree.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', namespaces).text
        supplier_name = tree.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name', namespaces).text

        # Cliente
        customer_vat = tree.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID', namespaces).text
        customer_name = tree.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name', namespaces).text

        # Factura
        invoice_number = tree.find('.//cbc:ID', namespaces).text
        invoice_date = tree.find('.//cbc:IssueDate', namespaces).text
        total_amount = tree.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', namespaces).text

        # Líneas de factura
        invoice_lines = []
        for line in tree.findall('.//cac:InvoiceLine', namespaces):
            description = line.find('.//cac:Item/cbc:Description', namespaces).text
            quantity = float(line.find('.//cbc:InvoicedQuantity', namespaces).text)
            price_unit = float(line.find('.//cac:Price/cbc:PriceAmount', namespaces).text)
            invoice_lines.append((0, 0, {
                'name': description,
                'quantity': quantity,
                'price_unit': price_unit,
            }))

        # Buscar partner por NIT
        partner = self.env['res.partner'].search([('vat', '=', supplier_vat)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': supplier_name,
                'vat': supplier_vat,
                'supplier_rank': 1,
            })

        return {
            'partner_id': partner.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': invoice_lines,
        }

    @api.model
    def create(self, vals):
        record = super().create(vals)
        self._procesar_adjuntos(record)
        return record

    def write(self, vals):
        result = super().write(vals)
        if 'x_name' in vals:  # Corregido para verificar el campo 'x_name'
            self._procesar_adjuntos(self)  # Llamar al proceso de adjuntos
        return result
