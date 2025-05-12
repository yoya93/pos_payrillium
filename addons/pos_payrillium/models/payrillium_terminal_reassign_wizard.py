from odoo import models, fields, api, _

class PayrilliumTerminalReassignWizard(models.TransientModel):
    _name = 'payrillium.terminal.reassign.wizard'
    _description = 'Reasignar terminal Payrillium'

    terminal_id = fields.Many2one('payrillium.terminal', required=True, string="Terminal")
    old_config_id = fields.Many2one('pos.config', required=True, string="Configuración actual")
    new_config_id = fields.Many2one('pos.config', required=True, string="Nueva configuración")

    def action_confirm(self):
        # Desasignar de la anterior
        self.old_config_id.payrillium_terminal_id = False
        # Asignar a la nueva
        self.new_config_id.payrillium_terminal_id = self.terminal_id
        # Actualizar terminal
        self.terminal_id.pos_config_id = self.new_config_id.id
        self.terminal_id.pos_config_name = self.new_config_id.name
        return {'type': 'ir.actions.act_window_close'}