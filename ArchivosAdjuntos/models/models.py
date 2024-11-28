from odoo import models, fields, api

class ListAttachmentLoader(models.Model):
    _name = "x_recepcion_facturas"
    _inherit = "x_recepcion_facturas"

    x_studio_adjunto = fields.Binary(string="Adjunto", attachment=True)

    @api.model
    def action_load_attachments(self):
        records = self.search([])
        for record in records:
            # Buscar archivos adjuntos en los mensajes relacionados
            for message in record.message_ids:
                if message.attachment_ids:
                    # Tomar el primer archivo adjunto encontrado y asignarlo al campo
                    attachment = message.attachment_ids[0]
                    record.x_studio_adjunto = attachment.datas
                    break  # Se detiene después de asignar el primer archivo encontrado

