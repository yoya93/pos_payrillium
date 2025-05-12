import logging
from odoo import models, fields, api
from ..config import PAYMENT_METHOD_NAME

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dummy_terminal_label = fields.Char(
        default="Select Terminal", readonly=True)
    payment_method_name_label = fields.Char(string="Method Label")
    enable_payrillium_terminal = fields.Boolean(string="Woodforest")
    module_pos_payrillium = fields.Boolean(
        string="Install Payrillium Module", default=False)
    pos_config_id = fields.Many2one(
        'pos.config',
        default=lambda self: self.env['pos.config'].search(
            [('company_id', '=', self.env.company.id)], limit=1),
        string="POS Config"
    )
    terminal_id = fields.Many2one(
        'payrillium.terminal',
        string='Available Terminals',
        related='pos_config_id.payrillium_terminal_id',
        readonly=False,
        store=True,
    )

    has_custom_payment = fields.Boolean(string='Has Payment Method')

    @api.model
    def get_values(self):
        res = super().get_values()
        _logger.info("🔧 get_values() called in ResConfigSettings")

        has_payment = False
        pos_config = self.env['pos.config'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if pos_config:
            _logger.info(f"✅ Found POS Config: {pos_config.display_name}")
            payment_method = self.env['pos.payment.method'].search([
                ('name', '=', PAYMENT_METHOD_NAME),
                ('id', 'in', pos_config.payment_method_ids.ids)
            ], limit=1)
            has_payment = bool(payment_method)
            _logger.info(
                f"🔍 Payment method {'found' if has_payment else 'not found'} for POS config")
        else:
            _logger.warning("⚠️ No POS Config found for current company")
            has_payment = False

        active_sessions = self.env['pos.session'].search(
            [('state', '=', 'opened')])
        
        
        terminal_ids_in_use = []
        for session in active_sessions:
            for pm in session.payment_method_ids:
                if hasattr(pm, 'terminal_id') and pm.terminal_id:
                    terminal_ids_in_use.append(pm.terminal_id.id)
        _logger.info(f"📦 Terminals currently in use: {terminal_ids_in_use}")

        available_terminals = self.env['payrillium.terminal'].search([
            ('id', 'not in', terminal_ids_in_use)
        ])

        _logger.info("🧩 Available terminals: %s",
                     available_terminals.mapped('name'))
        _logger.info(f"💡 Setting has_custom_payment to: {has_payment}")

        res.update({
            'has_custom_payment': has_payment,
            'terminal_id': pos_config.payrillium_terminal_id.id if pos_config else False,
            'payment_method_name_label': PAYMENT_METHOD_NAME,
            'enable_payrillium_terminal': has_payment
        })

        _logger.info("🔁 get_values() completed with update")
        return res

    def set_values(self):
        if self.enable_payrillium_terminal and not self.terminal_id:
            _logger.error(
                f"❌ Terminal must be selected for {PAYMENT_METHOD_NAME}")
            raise models.ValidationError(
                f"Please select a terminal to use with the {PAYMENT_METHOD_NAME} payment method before saving."
            )

        super().set_values()
        _logger.info("💾 set_values() called in ResConfigSettings")

        if not self.terminal_id:
            _logger.warning("⚠️ No terminal selected, skipping updates")
            return True

        existing_terminal = self.env['payrillium.terminal'].search([
            ('id', '=', self.terminal_id.id),
            ('pos_config_id', '!=', False),
            ('pos_config_id', '!=', self.pos_config_id.id),
        ], limit=1)

        if existing_terminal:
            pos_name = existing_terminal.pos_config_id.name or "Unknown POS Config"
            raise models.ValidationError(
                f"The terminal '{self.terminal_id.name}' is already assigned to the POS '{pos_name}'."
            )

        pos_config = self.pos_config_id
        if not pos_config:
            _logger.warning("🚫 No POS Config selected.")
            return True

        _logger.info(
            f"💾 Assigning terminal {self.terminal_id.name} to POS Config {pos_config.name}")

        session = self.env['pos.session'].search([
            ('config_id', '=', pos_config.id),
            ('state', 'in', ['opened', 'opening_control', 'closed'])
        ], order='id desc', limit=1)

        _logger.info(
            f"🔎 Session found: {session.display_name if session else 'No session'}")

        self.terminal_id.write({
            'pos_config_id': pos_config.id,
            'pos_config_name': pos_config.name,
            'last_session_id': session.id if session else False,
        })

        pos_config.payrillium_terminal_id = self.terminal_id

        _logger.info(
            f"✅ Terminal {self.terminal_id.name} updated with POS Config {pos_config.name}")
        return True
    @api.depends('payment_method_name_label')
    def _compute_payment_method_title(self):
        for rec in self:
            rec.payment_method_title = (
                f"To use these terminals, you must add the "
                f"{rec.payment_method_name_label or ''} payment method to your POS session."
            )





    #         def set_values(self):
    # if self.enable_payrillium_terminal and not self.terminal_id:
    #     _logger.error(
    #         f"❌ Terminal must be selected for {PAYMENT_METHOD_NAME}")
    #     raise models.ValidationError(
    #         f"Please select a terminal to use with the {PAYMENT_METHOD_NAME} payment method before saving."
    #     )

    # super().set_values()
    # _logger.info("💾 set_values() called in ResConfigSettings")

    # if not self.terminal_id:
    #     _logger.warning("⚠️ No terminal selected, skipping updates")
    #     return True

    # # Buscar si el terminal ya está asignado a otra configuración
    # existing_config = self.env['pos.config'].search([
    #     ('payrillium_terminal_id', '=', self.terminal_id.id),
    #     ('id', '!=', self.pos_config_id.id),
    # ], limit=1)

    # if existing_config:
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'payrillium.terminal.reassign.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_terminal_id': self.terminal_id.id,
    #             'default_old_config_id': existing_config.id,
    #             'default_new_config_id': self.pos_config_id.id,
    #         }
    #     }

    # pos_config = self.pos_config_id
    # if not pos_config:
    #     _logger.warning("🚫 No POS Config selected.")
    #     return True

    # _logger.info(
    #     f"💾 Assigning terminal {self.terminal_id.name} to POS Config {pos_config.name}")

    # self.terminal_id.write({
    #     'pos_config_id': pos_config.id,
    #     'pos_config_name': pos_config.name,
    # })

    # pos_config.payrillium_terminal_id = self.terminal_id

    # _logger.info(
    #     f"✅ Terminal {self.terminal_id.name} updated with POS Config {pos_config.name}")
    # return True