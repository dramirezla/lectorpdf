import logging
_logger = logging.getLogger(__name__)

class ListAttachmentLoader(models.Model):
    _name = "x_recepcion_facturas"
    _inherit = "x_recepcion_facturas"

    x_studio_adjunto = fields.Binary(string="Adjunto")

    @api.model
    def action_load_attachments(self):
        records = self.search([])  # Considerar aplicar filtros si es necesario
        for record in records:
            for message in record.message_ids:
                if message.attachment_ids:
                    attachment = message.attachment_ids[0]  # Asegura que solo el primer adjunto se usa
                    if attachment:
                        record.x_studio_adjunto = attachment.datas
                        _logger.info(f'Attachment loaded for record {record.id}')
                    else:
                        _logger.warning(f'No attachment found in message {message.id} for record {record.id}')
                else:
                    _logger.warning(f'No messages with attachments for record {record.id}')
