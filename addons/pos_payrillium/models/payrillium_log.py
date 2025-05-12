from odoo import models, fields, api

from odoo.tools import format_datetime


class PayrilliumLog(models.Model):
    _name = "payrillium.log"
    _description = "Payrillium Log"

    timestamp = fields.Datetime(string="Timestamp", required=True, index=True)
    display_time = fields.Char(
        string="Display Time", compute="_compute_display_time", store=True)

    execution_id = fields.Char(string="Execution ID", index=True)
    log_type = fields.Selection(
        [("request", "Request"), ("response", "Response")], string="Log Type")
    endpoint = fields.Char(string="Endpoint")
    request_payload = fields.Text(string="Request")
    response_payload = fields.Text(string="Response")
    success = fields.Boolean(string="Success")
    error_message = fields.Text(string="Error")

    @api.depends("timestamp")
    def _compute_display_time(self):
        for record in self:
            if record.timestamp:
                record.display_time = format_datetime(
                    self.env, record.timestamp, dt_format="short", tz="local")
            else:
                record.display_time = ""
