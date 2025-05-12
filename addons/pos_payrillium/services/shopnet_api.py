# Used to communicate with Shopnet API from the Odoo backend
import requests
import logging

_logger = logging.getLogger(__name__)

SHOPNET_API_URL = "https://sn.mirillium.io/api/v1/get_terminals_by_customer"


def get_terminals_from_token(full_token):
    """
    Real call to Shopnet API unless token starts with TEST.
    """
    _logger.info("📡 Preparing Shopnet API call with raw token: %s", full_token)

    if not full_token or len(full_token) < 5:
        return {
            "success": False,
            "message": "Token format is invalid. Minimum 5 characters required.",
            "terminals": [],
        }

    code = full_token[:4]
    token = full_token[4:]

    try:
        params = {
            "token": token,
            "code": code,
        }

        _logger.info("🌐 Calling Shopnet API with params: %s", params)
        response = requests.get(SHOPNET_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Check for valid structure
        terminals_raw = data.get("data")
        if data.get("success") and isinstance(terminals_raw, list):
            # Extract only desired fields
            terminals = [
                {
                    "name": t.get("model", {}).get("name", "Unknown"),
                    "serial": t.get("serial", "N/A"),
                    # "status": t.get("status") if t.get("status") in ("online", "offline") else "offline",

                }
                for t in terminals_raw
            ]

            _logger.info("✅ Parsed terminals: %s", terminals)
            return {
                "success": True,
                "message": "Terminals fetched successfully",
                "terminals": terminals,
            }

        error_msg = data.get("message", "Unexpected response from Shopnet")
        _logger.warning("⚠️ Unexpected response: %s", data)
        return {
            "success": False,
            "message": error_msg,
            "terminals": [],
        }

    except requests.RequestException as e:
        _logger.error("❌ Connection error with Shopnet: %s", str(e))
        return {
            "success": False,
            "message": "Failed to connect to Shopnet API",
            "terminals": [],
        }
