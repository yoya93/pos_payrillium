# Used for post-install hook to show configuration wizard
from odoo import api, SUPERUSER_ID
from odoo.api import Environment
import logging

_logger = logging.getLogger(__name__)


def show_payrillium_wizard_once(env):
    """
    Show the configuration wizard once after installation (Odoo 17+)
    """
    config = env['payrillium.config'].search([], limit=1)
    if not config or not config.token:
        env['ir.actions.server'].create({
            'name': 'Show Payrillium Wizard',
            'model_id': env.ref('base.model_res_config_settings').id,
            'binding_model_id': env.ref('base.model_res_config_settings').id,
            'state': 'code',
            'code': "action = env.ref('pos_payrillium.action_payrillium_wizard').read()[0]",
        })
