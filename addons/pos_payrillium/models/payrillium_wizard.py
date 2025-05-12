# Used to handle configuration wizard functionality
from ..config import PAYMENT_METHOD_NAME, PAYMENT_METHOD_COLOR, PAYMENT_METHOD_ICON
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from ..services.shopnet_api import get_terminals_from_token

_logger = logging.getLogger(__name__)


class PayrilliumWizard(models.TransientModel):
    _name = 'payrillium.wizard'
    _description = 'Wizard to configure Payrillium'

    token = fields.Char(string="Token", required=True)
    account_id = fields.Many2one(
        'account.account',
        string="Payment Account",
        required=True,
        domain=[
            ('account_type', 'in', ['asset_cash', 'bank']),
            ('deprecated', '=', False)
        ],
        help="This account will be used as the 'Outstanding Payments/Receipts' account. It must be of type 'Cash' or 'Bank' and be reconciliable."
    )
    receivable_account_id = fields.Many2one(
        'account.account',
        string="Receivable Account",
        required=True,
        domain=[
            ('account_type', '=', 'asset_receivable'),
            ('reconcile', '=', True),
            ('deprecated', '=', False)
        ],
        help="Account used for POS counterpart. Must be type 'Receivable'."
    )

    @api.model
    def check_and_open_wizard(self, *args, **kwargs):
        _logger.info(
            "🔵 Executing check_and_open_wizard with args: %s, kwargs: %s", args, kwargs)
        config = self.env['payrillium.config'].search([], limit=1)
        if not config or not config.token:
            _logger.info("🔵 No configuration found, opening wizard")
            action = self.env.ref(
                'pos_payrillium.action_payrillium_wizard').read()[0]
            return action
        _logger.info("🔵 Configuration already exists with token")
        return False

    def submit_token(self):
        _logger.info("🔐 Token received in wizard")

        token = self.token.strip()
        _logger.info("🔐 Token received in wizard: %s", token)

        if not token or token == "INVALID":
            _logger.warning("❌ Invalid token entered: %s", token)
            raise UserError("❌ Invalid Token")

        response = get_terminals_from_token(token)
        if not response["success"]:
            raise UserError("❌ " + response["message"])

        terminals = response["terminals"]

        # Step 0: Delete previous terminals
        old_terminals = self.env['payrillium.terminal'].sudo().search([])
        _logger.info("🧹 Deleting %d previous terminals", len(old_terminals))
        old_terminals.unlink()

        for terminal in terminals:
            _logger.info("💾 Creating terminal: %s", terminal)
            self.env['payrillium.terminal'].sudo().create({
                "name": terminal["name"],
                "serial": terminal["serial"]
            })

        # Step 1: Create or get bridge account
        account = self.env['account.account'].search([
            ('code', '=', '101401'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not account:
            _logger.info("🟡 No account found, creating new account 101401.")
            account = self.env['account.account'].create({
                'name': 'Payrillium Bridge Account',
                'code': '101401',
                'account_type': 'asset_cash',
                'reconcile': True,
                'company_id': self.env.company.id,
            })
            _logger.info(
                f"✅ Account created: {account.display_name} (ID: {account.id})")
        else:
            _logger.info(
                f"✅ Account found: {account.display_name} (ID: {account.id})")

        # Step 2: Create or get journal
        journal = self.env['account.journal'].search([
            ('code', '=', 'PAYR'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            _logger.info("🟡 No journal found, creating new journal PAYR.")
            journal = self.env['account.journal'].create({
                'name': 'Payrillium Journal',
                'type': 'bank',
                'code': 'PAYR',
                'company_id': self.env.company.id,
                'default_account_id': account.id,
            })
            _logger.info(
                f"✅ Journal created: {journal.display_name} (ID: {journal.id})")
        else:
            if journal.default_account_id != self.account_id:
                journal.write({'default_account_id': self.account_id.id})
                _logger.info(
                    f"🔁 Updated journal default account to: {self.account_id.code}")
            else:
                _logger.info(
                    f"✅ Journal already has correct default account: {journal.default_account_id.code}")

        # Step 3: Ensure payment provider
        self.ensure_payrillium_acquirer()

        # Step 4: Payment method line (manual inbound)
        payment_method = self.env['account.payment.method'].search([
            ('payment_type', '=', 'inbound'),
            ('name', 'ilike', 'Manual')
        ], limit=1)

        if not payment_method:
            raise UserError("❌ No 'Manual' inbound payment method found")

        existing_lines = self.env['account.payment.method.line'].search([
            ('journal_id', '=', journal.id),
            ('payment_method_id', '=', payment_method.id)
        ])
        if existing_lines:
            _logger.warning(
                f"🧹 Deleting {len(existing_lines)} existing method lines for PAYR + Manual inbound")
            existing_lines.unlink()

        self.env['account.payment.method.line'].create({
            'name': 'Payrillium Manual In',
            'journal_id': journal.id,
            'payment_method_id': payment_method.id,
            'payment_provider_id': self.env['payment.provider'].search([('code', '=', 'payrillium')], limit=1).id,
            'payment_account_id': self.account_id.id,
            'sequence': 10,
        })
        _logger.info(
            f"✅ Created clean method line with account '{self.account_id.name}'")

        # Step 5: POS payment method
        existing = self.env['pos.payment.method'].search([
            ('name', '=', PAYMENT_METHOD_NAME)
        ], limit=1)

        if not existing:
            _logger.info("🟡 No POS payment method found, creating new one.")
            pos_method = self.env['pos.payment.method'].create({
                'name': PAYMENT_METHOD_NAME,
                'journal_id': journal.id,
                'receivable_account_id': self.receivable_account_id.id,
                'outstanding_account_id': self.account_id.id,
                'use_payment_terminal': 'payrillium',
                'payrillium_color': PAYMENT_METHOD_COLOR,
                'payrillium_icon': PAYMENT_METHOD_ICON,
                'payment_provider_id': self.env['payment.provider'].search([('code', '=', 'payrillium')], limit=1).id,
            })
            _logger.info(
                "ℹ️ Reusing method line already created for journal + payment method.")
            _logger.info(
                f"✅ POS payment method created: {pos_method.display_name} (ID: {pos_method.id})")
        else:
            updates = {}
            if existing.receivable_account_id.id != self.receivable_account_id.id:
                updates['receivable_account_id'] = self.receivable_account_id.id
            if not existing.outstanding_account_id or existing.outstanding_account_id.id != self.account_id.id:
                updates['outstanding_account_id'] = self.account_id.id
            if updates:
                existing.write(updates)

                _logger.info(
                    f"🔁 Updated accounts on POS payment method to: {self.account_id.code}")
            _logger.info(
                f"✅ POS payment method found: {existing.display_name} (ID: {existing.id})")

        _logger.info(
            "✅ Terminals successfully saved in payrillium.terminal model")

        terminal_names = "\n".join([t["name"] for t in terminals])
        _logger.info("💾 Terminals added to payrillium.terminal model")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "✅ Terminals Added",
                "message": f"{terminal_names}",
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    @api.model
    def ensure_payrillium_acquirer(self):
        """Ensure a Payrillium payment provider exists, create if not."""
        _logger.info("🔍 Checking if Payrillium payment provider exists...")
        Provider = self.env['payment.provider']
        if not Provider.search([('code', '=', 'payrillium')], limit=1):
            _logger.info("🔍 Creating Payrillium payment provider")
            Provider.create({
                'name': 'Payrillium Terminal',
                'code': 'payrillium',
                'state': 'enabled',
                'company_id': self.env.company.id,
            })
            _logger.info("✅ Payrillium payment provider successfully created.")
        else:
            _logger.info("🔍 Payrillium payment provider already exists")
