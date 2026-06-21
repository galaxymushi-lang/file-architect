"""
API Access Extension
Expose GALACTOS as an API for external apps.
Generate API keys, rate limiting, and API documentation.
"""

import os
import json
import time
import hashlib
import secrets
from extensions.base import BaseExtension


class APIAccessExtension(BaseExtension):
    """Expose GALACTOS as an API."""

    name = "api_access"
    display_name = "API Access"
    description = "Expose GALACTOS as an API for external apps. Generate API keys and manage access."
    version = "1.0.0"
    author = "GALACTOS"
    icon = "api"

    API_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "api_keys.json")

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        self.rate_limit = int(self.get_config("rate_limit", 60))
        self.api_enabled = self.get_config("api_enabled", True)

    def _load_keys(self):
        if os.path.exists(self.API_FILE):
            try:
                with open(self.API_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_keys(self, keys):
        with open(self.API_FILE, "w") as f:
            json.dump(keys, f, indent=2)

    def get_routes(self):
        from flask import request, jsonify

        def generate_key():
            data = request.get_json()
            name = data.get("name", "Unnamed")
            keys = self._load_keys()
            api_key = f"gal_{secrets.token_hex(24)}"
            keys[api_key] = {
                "name": name,
                "created": time.time(),
                "requests": 0,
                "last_used": None,
                "active": True
            }
            self._save_keys(keys)
            return jsonify({"success": True, "api_key": api_key, "name": name})

        def list_keys():
            keys = self._load_keys()
            result = []
            for key, info in keys.items():
                result.append({
                    "key_preview": key[:8] + "..." + key[-4:],
                    "name": info["name"],
                    "created": info["created"],
                    "requests": info["requests"],
                    "last_used": info["last_used"],
                    "active": info["active"]
                })
            return jsonify({"keys": result})

        def revoke_key():
            data = request.get_json()
            key = data.get("key", "")
            keys = self._load_keys()
            if key in keys:
                keys[key]["active"] = False
                self._save_keys(keys)
                return jsonify({"success": True})
            return jsonify({"error": "Key not found"}), 404

        def api_chat():
            if not self.api_enabled:
                return jsonify({"error": "API access is disabled"}), 403

            api_key = request.headers.get("X-API-Key", "")
            keys = self._load_keys()
            if api_key not in keys or not keys[api_key]["active"]:
                return jsonify({"error": "Invalid or inactive API key"}), 401

            keys[api_key]["requests"] += 1
            keys[api_key]["last_used"] = time.time()
            self._save_keys(keys)

            data = request.get_json()
            message = data.get("message", "")
            if not message:
                return jsonify({"error": "No message provided"}), 400

            from app import ollama_generate
            result = ollama_generate(message)
            return jsonify({"response": result, "model": data.get("model", "default")})

        def api_docs():
            docs = {
                "name": "GALACTOS API",
                "version": "1.0.0",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/external/chat",
                        "description": "Send a message to GALACTOS AI",
                        "headers": {"X-API-Key": "your_api_key"},
                        "body": {"message": "Your message", "model": "optional_model"},
                        "response": {"response": "AI response", "model": "model_used"}
                    },
                    {
                        "method": "GET",
                        "path": "/api/external/status",
                        "description": "Check API status"
                    }
                ]
            }
            return jsonify(docs)

        def api_status():
            return jsonify({"status": "online", "version": "1.0.0", "api_enabled": self.api_enabled})

        return {
            "/api/extensions/api_access/generate": {
                "method": "POST",
                "handler": generate_key,
                "login_required": True,
            },
            "/api/extensions/api_access/list": {
                "method": "GET",
                "handler": list_keys,
                "login_required": True,
            },
            "/api/extensions/api_access/revoke": {
                "method": "POST",
                "handler": revoke_key,
                "login_required": True,
            },
            "/api/external/chat": {
                "method": "POST",
                "handler": api_chat,
                "login_required": False,
            },
            "/api/external/status": {
                "method": "GET",
                "handler": api_status,
                "login_required": False,
            },
            "/api/external/docs": {
                "method": "GET",
                "handler": api_docs,
                "login_required": False,
            }
        }

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "api_enabled",
                    "type": "boolean",
                    "label": "Enable API Access",
                    "value": self.get_config("api_enabled", True)
                },
                {
                    "name": "rate_limit",
                    "type": "number",
                    "label": "Rate Limit (requests per minute)",
                    "value": self.get_config("rate_limit", 60)
                }
            ]
        }
