class ListAttachmentLoader(models.Model):
    _name = "x_recepcion_facturas"
    _inherit = "x_recepcion_facturas"

    x_studio_adjunto = fields.Binary(string="Adjunto")

    @api.model
    def action_load_attachments(self):
        records = self.search([])
        for record in records:
            # Buscar mensajes relacionados al registro
            for message in record.message_ids:
                if message.attachment_ids:
                    # Asignar el primer archivo adjunto a x_studio_adjunto
                    attachment = message.attachment_ids[0]
                    if attachment:
                        record.x_studio_adjunto = attachment.datas
                        break  # Salir después de asignar el primer archivo


