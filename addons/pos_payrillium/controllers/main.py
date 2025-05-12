import json
import base64
import hashlib
import requests
from datetime import datetime

from ..config import PAYMENT_METHOD_NAME
from ..config import PAYMENT_METHOD_COLOR
from ..config import PAYMENT_METHOD_ICON
from ..config import IMAGE_BASE_URL
from odoo import http, fields
from odoo.http import request

API_BASE_URL = "http://app-node.mirillium.io/insecure-vpc/"


def build_url(terminal_id, path_type, action):
    return f"{API_BASE_URL}{terminal_id}/{path_type}/{action}"


def _get_current_terminal():
    user = request.env.user
    session = request.env['pos.session'].sudo().search([
        ('user_id', '=', user.id),
        ('state', '=', 'opened')
    ], limit=1)
    print(session, "session")

    if session and session.config_id.payrillium_terminal_id:
        return session.config_id.payrillium_terminal_id
    return None


def log_payrillium_event(execution_id, step_name, kind, payload=None, success=True, error_message=None):
    try:
        log_values = {
            'timestamp': fields.Datetime.now(),
            'execution_id': execution_id or 'missing',
            'endpoint': step_name,
            'log_type': kind,
            'success': success,
            'error_message': error_message or "",
        }

        if kind == "request":
            log_values['request_payload'] = json.dumps(payload or {})
        else:
            log_values['response_payload'] = json.dumps(payload or {})

        record = request.env['payrillium.log'].sudo().create(log_values)
        print(
            f"✅ Log saved: ID={record.id}, type={kind}, endpoint={step_name}")
    except Exception as e:
        print(f"⚠️ Error logging Payrillium event: {e}")


def generate_encryption_key():
    device_token = "6193354076942470"
    timestamp = int(datetime.utcnow().timestamp())
    time_key = datetime.utcfromtimestamp(timestamp).strftime("%Y:%m:%d:%H:%M")
    base = f"{device_token}{time_key}".ljust(32, '0')
    key = hashlib.sha256(base.encode()).hexdigest()
    key_encoded = base64.b64encode(f"{key}{timestamp}".encode()).decode()
    return key_encoded, timestamp, time_key


def sign_payload(payload):

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_encoded = base64.b64encode(payload_json.encode()).decode()
    auth_hash = hashlib.sha512(payload_encoded.encode()).hexdigest()

    return payload_json, payload_encoded, auth_hash


class PayrilliumWizardController(http.Controller):

    # @http.route('/payrillium/validate_token', type='json', auth='user')
    # def validate_token(self, token):
    #     print(f"🔑 Validating token...")
    #     try:
    #         if token == "valid_token":
    #             result = {
    #                 "success": True,
    #                 "terminals": [
    #                     {"id": "T-001", "name": "Terminal A"},
    #                     {"id": "T-002", "name": "Terminal B"},
    #                 ]
    #             }
    #             print(
    #                 f"✅ Token validation successful: {json.dumps(result, indent=2)}")

    #             request.env['payrillium.log'].sudo().create({
    #                 'timestamp': fields.Datetime.now(),
    #                 'endpoint': 'validate_token',
    #                 'request_payload': json.dumps({"token": token}),
    #                 'response_payload': json.dumps(result),
    #                 'success': True,
    #             })

    #             return result
    #         else:
    #             error = {
    #                 "success": False,
    #                 "error": "Invalid token. Could not fetch terminals."
    #             }
    #             print(
    #                 f"❌ Token validation failed: {json.dumps(error, indent=2)}")

    #             request.env['payrillium.log'].sudo().create({
    #                 'timestamp': fields.Datetime.now(),
    #                 'endpoint': 'validate_token',
    #                 'request_payload': json.dumps({"token": token}),
    #                 'response_payload': json.dumps(error),
    #                 'success': False,
    #                 'error_message': "Invalid token provided",
    #             })

    #             return error
    #     except Exception as e:
    #         error_msg = str(e)
    #         print(f"❌ Error in validate_token: {error_msg}")

    #         request.env['payrillium.log'].sudo().create({
    #             'timestamp': fields.Datetime.now(),
    #             'endpoint': 'validate_token',
    #             'request_payload': json.dumps({"token": token}),
    #             'response_payload': "",
    #             'success': False,
    #             'error_message': error_msg,
    #         })

    #         return {"status": "error", "message": error_msg}

    @http.route('/payrillium/payment_method_name', type='json', auth='public')
    def get_payment_method_name(self):
        print("🏷️ Getting payment method name...")
        try:
            result = {"payment_method_name": PAYMENT_METHOD_NAME}
            print(
                f"✅ Payment method name retrieved: {json.dumps(result, indent=2)}")

            return result
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error getting payment method name: {error_msg}")
            return {"status": "error", "message": error_msg}

    @http.route('/payrillium/payment_method_color', type='json', auth='user')
    def payment_method_color(self):
        print("🎨 Getting payment method color...")
        try:
            result = {"color": PAYMENT_METHOD_COLOR}
            print(
                f"✅ Payment method color retrieved: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error getting payment method color: {error_msg}")
            return {"status": "error", "message": error_msg}

    @http.route('/payrillium/payment_method_icon', type='json', auth='user')
    def payment_method_icon(self):
        print("🖼️ Getting payment method icon...")
        try:
            result = {"icon": PAYMENT_METHOD_ICON}
            print(
                f"✅ Payment method icon retrieved: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error getting payment method icon: {error_msg}")
            return {"status": "error", "message": error_msg}

    @http.route('/payrillium/proxy/<string:action>', type='json', auth='user')
    def proxy_to_terminal(self, action , **kwargs):
        if "kwargs" in kwargs:
            kwargs = kwargs["kwargs"]
        print(f"🛬 Incoming proxy request to endpoint: {action}")
        execution_id = kwargs.pop("executionId", "missing")
        print(execution_id, "execution_id")

        

        terminal = _get_current_terminal()
        terminal_id = terminal.serial
        key_encoded, timestamp, time_key = generate_encryption_key()

        if action == "card":
            payload = {
                "data": "",
            }
        else:
            payload = {
                "data": {
                    "data": {**kwargs},
                },
                "key": key_encoded,
            }

        payload_json, payload_encoded, auth_hash = sign_payload(payload)

        log_payrillium_event(execution_id, action, "request", payload)
        url = build_url(terminal_id, "local", action)
        headers = {
            "Content-Type": "application/json",
            # "Authorization": f"Basic {auth_hash}",
            # "timestamp": str(timestamp),
        }

        try:
            print(f"🌐 Calling endpoint: {action}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, json=payload)

            response.raise_for_status()
            data = response.json()
            print(f"✅ Successful response: {json.dumps(data, indent=2)}")
            log_payrillium_event(execution_id, action,
                                 "response", data, success=True)
            return data

        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error in call: {error_msg}")
            log_payrillium_event(
                execution_id, action, "response", None, success=False, error_message=error_msg)
            return {"status": "error", "message": error_msg}

    @http.route('/payrillium/payment/<string:action>', type='json', auth='user')
    def payrillium_payment_router(self, action, **kwargs):
        print(f"🛬 Incoming dynamic payment request to: {action}")
        if "kwargs" in kwargs:
            kwargs = kwargs["kwargs"]
        execution_id = kwargs.pop("executionId", "missing")
        print(execution_id, "execution_id")
        terminal = _get_current_terminal()
        terminal_id = terminal.serial
        key_encoded, timestamp, time_key = generate_encryption_key()
     

        payload = {
            "data": {**kwargs},
            "key": key_encoded,
        }

        payload_json, payload_encoded, auth_hash = sign_payload(payload)

        url = build_url(terminal_id, "payment", action)
        headers = {
            "Content-Type": "application/json",
        }

        log_payrillium_event(
            execution_id, f"payment/{action}", "request", payload)

        try:
            print(f"📡 Calling {url}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            print(f"✅ Response: {json.dumps(data, indent=2)}")
            log_payrillium_event(
                execution_id, f"payment/{action}", "response", data, success=True)
            return data
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            log_payrillium_event(
                execution_id, f"payment/{action}", "response", None, success=False, error_message=error_msg)
            return {"status": "error", "message": error_msg}

    @http.route('/payrillium/image/<int:product_id>', type='http', auth='public')
    def get_image(self, product_id):
        product = request.env['product.product'].sudo().browse(product_id)
        if product.image_128:
            return request.make_response(
                base64.b64decode(product.image_128),
                headers=[('Content-Type', 'image/png')]
            )
        return http.Response(status=404)

    @http.route('/payrillium/image_base_url', type='json', auth='user')
    def get_image_base_url(self):
        url = IMAGE_BASE_URL
        return {"image_base_url": url or "http://localhost:8069"}

    @http.route('/payrillium/session/terminal', type='json', auth='user')
    def get_terminal_from_session(self):
        user = request.env.user
        session = request.env['pos.session'].sudo().search([
            ('user_id', '=', user.id),
            ('state', '=', 'opened')
        ], limit=1)
        if not session:
            return {"success": False, "message": "No session found"}
        terminal = session.config_id.payrillium_terminal_id
        if not terminal:
            return {"success": False, "message": "No terminal configured"}
        return {"success": True, "terminal": {"id": terminal.id, "name": terminal.name, "serial": terminal.serial}}

    @http.route('/payrillium/check_terminal_backend', type='json', auth='public')
    def check_terminal_backend(self):
        try:
            params = request.get_json_data().get('params', {})
            terminal_id = params.get('terminal_id')

            if not terminal_id:
                return {
                    "status": "error",
                    "message": "No terminal ID provided",
                    "debug": {"received": params, "context": request.context}
                }

            terminal = request.env['payrillium.terminal'].sudo().search([
                ('serial', '=', terminal_id)
            ], limit=1)

            if not terminal:
                return {"status": "error", "message": f"Terminal with serial '{terminal_id}' not found"}

            key_encoded, timestamp, time_key = generate_encryption_key()

            payload = {"data": "", "key": key_encoded}
            url = build_url(terminal_id, "local", "test")
            headers = {"Content-Type": "application/json"}
            log_payrillium_event(
                "missing", "check_terminal", "request", payload)

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            log_payrillium_event("missing", "check_terminal",
                                 "response", data, success=True)

            return {"status": "success", "data": data}

        except Exception as e:
            log_payrillium_event("missing", "check_terminal",
                                 "response", None, success=False, error_message=str(e))
            return {"status": "error", "message": str(e)}

    @http.route('/payrillium/reset_terminal_backend', type='json', auth='public')
    def reset_terminal_backend(self):
        try:
            params = request.get_json_data().get('params', {})
            terminal_id = params.get('terminal_id')

            if not terminal_id:
                return {
                    "status": "error",
                    "message": "No terminal ID provided",
                    "debug": {"received": params, "context": request.context}
                }

            terminal = request.env['payrillium.terminal'].sudo().search([
                ('serial', '=', terminal_id)
            ], limit=1)

            if not terminal:
                return {"status": "error", "message": f"Terminal with serial '{terminal_id}' not found"}

            key_encoded, timestamp, time_key = generate_encryption_key()

            payload = {"data": "", "key": key_encoded}
            url = build_url(terminal_id, "payment", "abort")
            headers = {"Content-Type": "application/json"}
            log_payrillium_event(
                "missing", "reset_terminal", "request", payload)

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            log_payrillium_event(
                "missing", "reset_terminal", "response", data, success=True)

            return {"status": "success", "data": data}

        except Exception as e:
            log_payrillium_event(
                "missing", "reset_terminal", "response", None, success=False, error_message=str(e))
            return {"status": "error", "message": str(e)}

    @http.route('/payrillium/payment_method_data', type='json', auth='public')
    def get_payment_method_data(self):
        payment_method = request.env['pos.payment.method'].search([
            ('use_payment_terminal', '=', 'payrillium')
        ], limit=1)

        return {
            'id': payment_method.id,
            'name': payment_method.name,
            'payment_provider_id': payment_method.payment_provider_id.id if payment_method.payment_provider_id else None,
            'receivable_account_id': payment_method.receivable_account_id.id if payment_method.receivable_account_id else None,
            'outstanding_account_id': payment_method.outstanding_account_id.id if payment_method.outstanding_account_id else None,
        }
