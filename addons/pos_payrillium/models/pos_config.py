# models/pos_config.py

from odoo import models, fields

class POSConfig(models.Model):
    _inherit = 'pos.config'

    payrillium_terminal_id = fields.Many2one(
        'payrillium.terminal',
        string='Assigned Payrillium Terminal'
        
    )
