from odoo import models, fields, api

class ListAttachmentLoader(models.Model):
    _name = "x_recepcion_facturas"
    _inherit = "x_recepcion_facturas"

    x_studio_adjunto = fields.Binary(string="Adjunto")

    @api.model
    def action_load_attachments(self):
        records = self.search([])
        for record in records:
            for message in record.message_ids:
                attachment = message.attachment_ids[:1]
                if attachment:
                    record.x_studio_adjunto = attachment.datas
