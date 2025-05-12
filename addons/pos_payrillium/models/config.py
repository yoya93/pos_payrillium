# Used to store and manage Payrillium configuration settings including API token and global parameters
from odoo import models, fields

class PayrilliumConfig(models.Model):
    _name = "payrillium.config"
    _description = "Payrillium Configuration"
    token = fields.Char(string="API Token")
    def has_token_or_not(self):
        record = self.search([('token', '!=', False)], limit=1)
        return bool(record)