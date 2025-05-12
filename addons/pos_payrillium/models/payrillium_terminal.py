import requests
import json
import logging
from odoo import models, fields, api
from odoo.http import request
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class PayrilliumTerminal(models.Model):
    _name = 'payrillium.terminal'
    _description = 'Payrillium Terminal'
    name = fields.Char(string="Name", required=True)
    serial = fields.Char(string="Serial Number")
    last_session_id = fields.Many2one(
        'pos.session', string="Last Session", compute='_compute_last_session', store=True)

    pos_config_name = fields.Char(
        string="POS Config", compute='_compute_last_session', store=True)
    pos_config_id = fields.Many2one(
        'pos.config',
        string='POS Config'
    )

    def _compute_last_session(self):
        _logger.info("🔎 Starting _compute_last_session for all terminals...")
        for terminal in self:
            _logger.info(f"➡️ Terminal: {terminal.name} (ID: {terminal.id})")

            terminal.last_session_id = False
            terminal.pos_config_name = False

            pos_config = self.env['pos.config'].search([
                ('payrillium_terminal_id', '=', terminal.id)
            ], limit=1)

            if pos_config:
                _logger.info(
                    f"✅ POS Config found: {pos_config.name} (ID: {pos_config.id})")

                session = self.env['pos.session'].search([
                    ('config_id', '=', pos_config.id),
                    ('state', 'in', ['opened', 'opening_control', 'closed'])
                ], order='id desc', limit=1)

                if session:
                    _logger.info(
                        f"✅ Session found: {session.name} (State: {session.state})")
                    terminal.last_session_id = session.id
                    terminal.pos_config_name = pos_config.name
                else:
                    _logger.warning(
                        f"⚠️ No session found for POS Config {pos_config.name}")
            else:
                _logger.warning(
                    f"⚠️ No POS Config found for terminal {terminal.name}")

        _logger.info("🔁 Finished _compute_last_session.")

    def action_check_terminal(self):
        if len(self) != 1:
            raise UserError(
                "Please select exactly one terminal to perform this action.")
        for terminal in self:
            _logger.info("🔍 Checking terminal: %s (Serial: %s)",
                         terminal.name, terminal.serial)
            try:
                base_url = request.httprequest.host_url.rstrip('/')
                url = f"{base_url}/payrillium/check_terminal_backend"
                _logger.info("🌐 Making request to: %s", url)

                payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "terminal_id": terminal.serial
                    },
                    "id": 1
                }
                _logger.info("📦 Request payload: %s", json.dumps(payload))

                session = request.session
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Openerp-Session-Id': session.sid if session else None
                }

                response = requests.post(url, json=payload, headers=headers)
                _logger.info("📡 Response status code: %s",
                             response.status_code)

                response.raise_for_status()
                result = response.json()
                _logger.info("✅ Response data: %s",
                             json.dumps(result, indent=2))

                result = result.get('result', {})

                if result.get("status") == "success":
                    _logger.info("✨ Terminal check successful")
                    success_message = f"""
Terminal Status Check:
----------------------
Name: {terminal.name}
Serial: {terminal.serial}
Status: Online ✅
Connection: Successfully established"""

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Terminal Connected Successfully',
                            'message': success_message,
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    _logger.error("❌ Terminal check failed: %s", error_msg)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Connection Error',
                            'message': f"Unable to connect to terminal: {error_msg}",
                            'type': 'danger',
                            'sticky': True,
                        }
                    }

            except requests.exceptions.ConnectionError as e:
                _logger.error("🔌 Connection error: %s", str(e))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Error',
                        'message': f"Could not connect to terminal: {str(e)}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }

            except requests.exceptions.RequestException as e:
                _logger.error("🚫 Request error: %s", str(e))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Request Error',
                        'message': f"Request failed: {str(e)}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }

            except Exception as e:
                _logger.error("💥 Unexpected error: %s", str(e), exc_info=True)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'System Error',
                        'message': f"An unexpected error occurred: {str(e)}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }

    def action_unlink_terminal(self):
        if len(self) != 1:
            raise UserError(
                "Please select exactly one terminal to perform this action.")
        for terminal in self:
            _logger.info(
                f"🔗 Unlinking terminal: {terminal.name} (ID: {terminal.id})")

            if terminal.pos_config_id:
                _logger.info(
                    f"🧹 Removing terminal {terminal.name} from POS Config {terminal.pos_config_id.name}")

                pos_config = terminal.pos_config_id
                pos_config.payrillium_terminal_id = False

                terminal.write({
                    'pos_config_id': False,
                    'pos_config_name': False,
                    'last_session_id': False,
                })

                _logger.info(
                    f"✅ Terminal {terminal.name} unlinked successfully.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Terminal Unlinked',
                        'message': 'The terminal was successfully unlinked.',
                        'type': 'success',
                        'sticky': False,
                        'next': {
                            'type': 'ir.actions.client',
                            'tag': 'reload',

                        }
                    }
                }
            else:
                _logger.warning(
                    f"⚠️ Terminal {terminal.name} is not linked to any POS Config.")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Not Linked',
                        'message': 'The terminal is not linked to any POS Config.',
                        'type': 'warning',
                        'sticky': True,
                    }
                }

    def action_delete_terminal(self):
        if len(self) != 1:
            raise UserError(
                "Please select exactly one terminal to perform this action.")
        for terminal in self:
            _logger.info(
                f"🗑️ DELETE Terminal requested: {terminal.name} (Serial: {terminal.serial})")

    def action_abort_terminal(self):
        if len(self) != 1:
            raise UserError(
                "Please select exactly one terminal to perform this action.")

        for terminal in self:
            _logger.info("🔍 Resetting terminal: %s (Serial: %s)",
                         terminal.name, terminal.serial)
            try:
                base_url = request.httprequest.host_url.rstrip('/')
                url = f"{base_url}/payrillium/reset_terminal_backend"
                _logger.info("🌐 Making request to: %s", url)

                payload = {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "terminal_id": terminal.serial
                    },
                    "id": 1
                }
                _logger.info("📦 Request payload: %s", json.dumps(payload))

                session = request.session
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Openerp-Session-Id': session.sid if session else None
                }

                response = requests.post(url, json=payload, headers=headers)
                _logger.info("📡 Response status code: %s",
                             response.status_code)
                response.raise_for_status()

                result = response.json().get('result', {})
                _logger.info("✅ Response data: %s",
                             json.dumps(result, indent=2))

                top_success = result.get("success")
                data = result.get("data", {})
                data_success = data.get("success")

                if top_success and data_success:
                    message = f"Terminal {terminal.name} ({terminal.serial}) was reset successfully ✅"
                    msg_type = "success"
                elif top_success and not data_success:
                    reason = data.get("reason", "No reason provided")
                    message = f"No operation to abort on terminal {terminal.name} ({terminal.serial}) ⚠️\nReason: {reason}"
                    msg_type = "warning"
                else:
                    error_msg = result.get("message", "Unknown error")
                    raise UserError(f"Unable to reset terminal: {error_msg}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Terminal Reset Result',
                        'message': message,
                        'type': msg_type,
                        'sticky': False,
                    }
                }

            except Exception as e:
                _logger.error("Terminal reset failed: %s", str(e))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': f"Failed to reset terminal: {str(e)}",
                        'type': 'danger',
                        'sticky': True,
                    }
                }
