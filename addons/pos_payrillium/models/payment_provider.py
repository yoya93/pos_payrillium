from odoo import models, fields


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payrillium', 'Payrillium Terminal')],
        ondelete={'payrillium': 'set default'}
    )

    def _get_default_payment_method_line_id(self):
        if self.code == 'payrillium':
            lines = self.env['account.payment.method.line'].search([
                ('journal_id.type', '=', 'bank'),
            ])
            return lines.filtered(lambda l: l.payment_type == 'inbound')[:1]
        return super()._get_default_payment_method_line_id()
