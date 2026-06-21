"""
Webhook System Extension
Send/receive webhooks for automation and integrations.
"""

import json
import time
import hashlib
import hmac
import urllib.request
from extensions.base import BaseExtension


class WebhookExtension(BaseExtension):
    """Webhook system for event-driven automation."""

    name = "webhooks"
    display_name = "Webhook System"
    description = "Send and receive webhooks for automation and integrations"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "webhook"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.webhooks = []
        self.outgoing = self.get_config("outgoing", [])
        self.secret = self.get_config("secret", "")

    def get_routes(self):
        from flask import request, jsonify

        def list_webhooks():
            return jsonify({"webhooks": self.outgoing})

        def add_webhook():
            data = request.get_json()
            url = data.get("url", "")
            name = data.get("name", "Unnamed")
            events = data.get("events", ["all"])
            if not url:
                return jsonify({"error": "URL required"}), 400
            webhook = {
                "name": name,
                "url": url,
                "events": events,
                "active": True,
                "created": time.time()
            }
            self.outgoing.append(webhook)
            self._save_config()
            return jsonify({"success": True, "webhook": webhook})

        def remove_webhook():
            data = request.get_json()
            url = data.get("url", "")
            self.outgoing = [w for w in self.outgoing if w["url"] != url]
            self._save_config()
            return jsonify({"success": True})

        def test_webhook():
            data = request.get_json()
            url = data.get("url", "")
            result = self._send_webhook(url, {"event": "test", "data": "Test webhook from GALACTOS"})
            return jsonify(result)

        return {
            "/api/extensions/webhooks/list": {
                "method": "GET",
                "handler": list_webhooks,
                "login_required": True,
            },
            "/api/extensions/webhooks/add": {
                "method": "POST",
                "handler": add_webhook,
                "login_required": True,
            },
            "/api/extensions/webhooks/remove": {
                "method": "POST",
                "handler": remove_webhook,
                "login_required": True,
            },
            "/api/extensions/webhooks/test": {
                "method": "POST",
                "handler": test_webhook,
                "login_required": True,
            }
        }

    def on_chat_message(self, message, context):
        """Trigger webhooks on new chat messages."""
        self._fire_event("chat_message", {"message": message[:500]})
        return None

    def on_ai_response(self, message, context):
        """Trigger webhooks on AI responses."""
        self._fire_event("ai_response", {"message": message[:500]})
        return None

    def _fire_event(self, event_name, data):
        """Send webhook to all registered URLs for this event."""
        for wh in self.outgoing:
            if wh.get("active") and (event_name in wh.get("events", []) or "all" in wh.get("events", [])):
                self._send_webhook(wh["url"], {"event": event_name, "data": data, "timestamp": time.time()})

    def _send_webhook(self, url, payload):
        """Send a webhook POST request."""
        try:
            body = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.secret:
                sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = sig
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"success": True, "status": resp.status, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    def _save_config(self):
        self.set_config("outgoing", self.outgoing)
        if self.app and hasattr(self.app, 'extensions'):
            from extensions import registry
            registry._save_config()
        else:
            import json, os
            config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extensions.json")
            try:
                existing = {}
                if os.path.exists(config_file):
                    with open(config_file, "r") as f:
                        existing = json.load(f)
                if self.name not in existing:
                    existing[self.name] = {}
                existing[self.name]["config"] = self.config
                with open(config_file, "w") as f:
                    json.dump(existing, f, indent=2)
            except Exception:
                pass

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "secret",
                    "type": "password",
                    "label": "Webhook Secret (for signature verification)",
                    "placeholder": "Optional signing secret"
                }
            ]
        }
