"""
Telegram Extension
Send and receive messages via Telegram Bot API.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from extensions.base import BaseExtension


class TelegramExtension(BaseExtension):
    """Telegram Bot integration."""

    name = "telegram"
    display_name = "Telegram"
    description = "Send and receive messages via Telegram Bot"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "telegram"

    API_BASE = "https://api.telegram.org"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        self.bot_token = self.get_config("bot_token", "")
        self.chat_id = self.get_config("chat_id", "")

    def get_routes(self):
        from flask import request, jsonify

        def send():
            data = request.get_json()
            chat_id = data.get("chat_id", self.chat_id)
            message = data.get("message", "")
            if not all([chat_id, message]):
                return jsonify({"error": "chat_id and message required"}), 400
            if not self.bot_token:
                return jsonify({"error": "Telegram not configured. Click Settings on Telegram extension."}), 400
            result = self._send_message(chat_id, message)
            return jsonify(result)

        def webhook():
            data = request.get_json()
            try:
                msg = data.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                if text and chat_id:
                    self._handle_incoming(chat_id, text, msg.get("from", {}))
            except Exception:
                pass
            return jsonify({"status": "ok"})

        def set_webhook():
            data = request.get_json()
            url = data.get("url", "")
            if not url:
                return jsonify({"error": "URL required"}), 400
            result = self._set_webhook(url)
            return jsonify(result)

        def get_updates():
            result = self._get_updates()
            return jsonify(result)

        return {
            "/api/extensions/telegram/send": {
                "method": "POST",
                "handler": send,
                "login_required": True,
            },
            "/api/extensions/telegram/webhook": {
                "method": "POST",
                "handler": webhook,
                "login_required": False,
            },
            "/api/extensions/telegram/set_webhook": {
                "method": "POST",
                "handler": set_webhook,
                "login_required": True,
            },
            "/api/extensions/telegram/updates": {
                "method": "GET",
                "handler": get_updates,
                "login_required": True,
            }
        }

    def _send_message(self, chat_id, message):
        try:
            url = f"{self.API_BASE}/bot{self.bot_token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return {"success": True, "message_id": result.get("result", {}).get("message_id", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _set_webhook(self, url):
        try:
            webhook_url = f"{url}/api/extensions/telegram/webhook"
            api_url = f"{self.API_BASE}/bot{self.bot_token}/setWebhook"
            data = urllib.parse.urlencode({"url": webhook_url}).encode()
            req = urllib.request.Request(api_url, data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return {"success": result.get("ok", False), "description": result.get("description", "")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_updates(self):
        try:
            url = f"{self.API_BASE}/bot{self.bot_token}/getUpdates?limit=50"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                updates = []
                for update in result.get("result", []):
                    msg = update.get("message", {})
                    updates.append({
                        "update_id": update.get("update_id"),
                        "chat_id": msg.get("chat", {}).get("id"),
                        "from": msg.get("from", {}).get("first_name", ""),
                        "text": msg.get("text", ""),
                        "date": msg.get("date", 0)
                    })
                return {"success": True, "updates": updates}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_incoming(self, chat_id, text, from_user):
        """Handle incoming Telegram messages."""
        pass

    def get_chat_tools(self):
        return [
            {
                "name": "telegram_send",
                "description": "Send a Telegram message to a chat",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "Chat ID or username"},
                        "message": {"type": "string", "description": "Message to send"}
                    },
                    "required": ["chat_id", "message"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "telegram_send":
            return self._send_message(parameters.get("chat_id", ""), parameters.get("message", ""))
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "bot_token",
                    "type": "password",
                    "label": "Telegram Bot Token",
                    "placeholder": "From @BotFather",
                    "value": self.get_config("bot_token", "")
                },
                {
                    "name": "chat_id",
                    "type": "text",
                    "label": "Default Chat ID",
                    "placeholder": "Your chat ID or @username",
                    "value": self.get_config("chat_id", "")
                }
            ]
        }
