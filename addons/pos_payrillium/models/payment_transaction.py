# models/payment_transaction.py
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PaymentTransactionPayrillium(models.Model):
    _inherit = 'payment.transaction'

    payrillium_terminal_id = fields.Many2one(
        'payrillium.terminal',
        string="Payrillium Terminal Used",
        help="Terminal used to process this Payrillium transaction."
    )
    card_type = fields.Char(
        string="Card Type",
        help="The card type used in this transaction (CREDIT or DEBIT)"
    )

    def _payrillium_form_get_tx_from_data(self, data):
        """Find a transaction based on the 'reference' from Payrillium data."""
        reference = data.get('reference')
        return self.search([('reference', '=', reference)], limit=1)

    def _payrillium_form_validate(self, data):
        """Mark the transaction as completed successfully."""
        self.ensure_one()
        self.write({
            'acquirer_reference': data.get('transaction_id'),
            'state': 'done',  # Or 'pending' if you use a delayed capture flow
        })
        return True

    @api.model
    def create_from_pos_payrillium(self, values):
        """Create a Payment Transaction record for a Payrillium payment."""
        _logger.info(
            "🚀 [create_from_pos_payrillium] Values received: %s", values)

        provider = self.env['payment.provider'].search(
            [('code', '=', 'payrillium')], limit=1)

        if not provider:
            _logger.error("❌ No Payrillium payment provider found.")
            raise ValueError("No Payrillium payment provider configured.")

        terminal_id = values.get('terminal_id') or False
        transaction = self.create({
            'reference': values.get('reference'),
            'provider_reference': values.get('acquirer_reference'),
            'payment_method_id': values.get('payment_method_id'),
            'amount': values.get('amount'),
            'currency_id': self.env.company.currency_id.id,
            'partner_id': self.env.user.partner_id.id,
            'state': 'done',
            'provider_id': provider.id,
            'payrillium_terminal_id': terminal_id,
            'card_type': values.get('card_type'),
        })

        pos_order = self.env['pos.order'].search(
            [('pos_reference', '=', values.get('order_pos_reference'))], limit=1)
        if pos_order:
            pos_payment = self.env['pos.payment'].search([
                ('pos_order_id', '=', pos_order.id),
                ('transaction_id', '=', False),
                ('amount', '=', values.get('amount')),
            ], limit=1)
            if pos_payment:
                pos_payment.write(
                    {'transaction_id': values.get('acquirer_reference')})
                _logger.info("🔗 pos.payment updated with transaction_id")

            _logger.info(
                "✅ Payment transaction created successfully: ID %s", transaction.id)

        return transaction.id

    def _send_payment_request_to_terminal(self):
        self.ensure_one()
        self.write({
            'state': 'done',
            'provider_reference': self.reference or 'Manual',
        })
