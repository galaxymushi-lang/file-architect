"""
WhatsApp Extension
Send and receive messages via WhatsApp Business API.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from extensions.base import BaseExtension


class WhatsAppExtension(BaseExtension):
    """WhatsApp Business API integration."""

    name = "whatsapp"
    display_name = "WhatsApp"
    description = "Send and receive messages via WhatsApp Business API"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "whatsapp"

    API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        self.access_token = self.get_config("access_token", "")
        self.phone_number_id = self.get_config("phone_number_id", "")
        self.business_account_id = self.get_config("business_account_id", "")
        self.verify_token = self.get_config("verify_token", "galactos_verify")

    def get_routes(self):
        from flask import request, jsonify

        def send():
            data = request.get_json()
            to = data.get("to", "")
            message = data.get("message", "")
            if not all([to, message]):
                return jsonify({"error": "to and message required"}), 400
            if not self.access_token or not self.phone_number_id:
                return jsonify({"error": "WhatsApp not configured. Click Settings on WhatsApp extension."}), 400
            result = self._send_message(to, message)
            return jsonify(result)

        def webhook_verify():
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")
            if mode == "subscribe" and token == self.verify_token:
                return challenge
            return "Forbidden", 403

        def webhook_receive():
            data = request.get_json()
            try:
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        for msg in messages:
                            self._handle_incoming(msg)
            except Exception:
                pass
            return jsonify({"status": "ok"})

        def list_messages():
            data = request.get_json() or {}
            phone = data.get("phone", "")
            result = self._list_messages(phone)
            return jsonify(result)

        return {
            "/api/extensions/whatsapp/send": {
                "method": "POST",
                "handler": send,
                "login_required": True,
            },
            "/api/extensions/whatsapp/webhook": {
                "method": "GET",
                "handler": webhook_verify,
                "login_required": False,
            },
            "/api/extensions/whatsapp/webhook": {
                "method": "POST",
                "handler": webhook_receive,
                "login_required": False,
            },
            "/api/extensions/whatsapp/messages": {
                "method": "POST",
                "handler": list_messages,
                "login_required": True,
            }
        }

    def _send_message(self, to, message):
        try:
            url = f"{self.API_BASE}/{self.phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Authorization", f"Bearer {self.access_token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return {"success": True, "message_id": result.get("messages", [{}])[0].get("id", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_messages(self, phone):
        try:
            params = urllib.parse.urlencode({"phone_number_id": self.phone_number_id, "limit": 50})
            url = f"{self.API_BASE}/{self.phone_number_id}/messages?{params}"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {self.access_token}")
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return {"success": True, "messages": result.get("data", [])}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_incoming(self, msg):
        """Handle incoming WhatsApp messages."""
        pass

    def get_chat_tools(self):
        return [
            {
                "name": "whatsapp_send",
                "description": "Send a WhatsApp message to a phone number",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Phone number with country code (e.g., +1234567890)"},
                        "message": {"type": "string", "description": "Message to send"}
                    },
                    "required": ["to", "message"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "whatsapp_send":
            return self._send_message(parameters.get("to", ""), parameters.get("message", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "access_token",
                    "type": "password",
                    "label": "WhatsApp Business Access Token",
                    "placeholder": "From Meta Developer Console",
                    "value": self.get_config("access_token", "")
                },
                {
                    "name": "phone_number_id",
                    "type": "text",
                    "label": "Phone Number ID",
                    "placeholder": "From WhatsApp Business settings",
                    "value": self.get_config("phone_number_id", "")
                },
                {
                    "name": "business_account_id",
                    "type": "text",
                    "label": "Business Account ID",
                    "placeholder": "From Meta Business Suite",
                    "value": self.get_config("business_account_id", "")
                },
                {
                    "name": "verify_token",
                    "type": "text",
                    "label": "Webhook Verify Token",
                    "placeholder": "Custom token for webhook verification",
                    "value": self.get_config("verify_token", "galactos_verify")
                }
            ]
        }
