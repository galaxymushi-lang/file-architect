"""
Email Sender Extension
Send emails via SMTP with configurable providers.
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from extensions.base import BaseExtension


class EmailExtension(BaseExtension):
    """Send emails via SMTP."""

    name = "email_sender"
    display_name = "Email Sender"
    description = "Send emails via SMTP (Gmail, Outlook, custom SMTP server)"
    version = "1.1.0"
    author = "GALACTOS"
    icon = "email"

    PROVIDERS = {
        "gmail": {"host": "smtp.gmail.com", "port": 587, "tls": True},
        "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "tls": True},
        "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587, "tls": True},
        "custom": {"host": "", "port": 587, "tls": True}
    }

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        """Re-read config from self.config dict."""
        self.provider = self.get_config("provider", "gmail")
        self.email_addr = self.get_config("email", "")
        self.password = self.get_config("password", "")
        self.custom_host = self.get_config("custom_host", "")
        self.custom_port = int(self.get_config("custom_port", 587))
        self.custom_tls = self.get_config("custom_tls", True)

    def get_routes(self):
        from flask import request, jsonify

        def send():
            data = request.get_json()
            to = data.get("to", "")
            subject = data.get("subject", "")
            body = data.get("body", "")
            html = data.get("html", False)

            if not all([to, subject, body]):
                return jsonify({"error": "to, subject, and body required"}), 400
            self._refresh_config()
            if not self.email_addr or not self.password:
                return jsonify({"error": "Email not configured. Click Settings on Email extension."}), 400

            result = self._send_email(to, subject, body, html)
            return jsonify(result)

        def providers():
            return jsonify({"providers": list(self.PROVIDERS.keys())})

        return {
            "/api/extensions/email/send": {
                "method": "POST",
                "handler": send,
                "login_required": True,
            },
            "/api/extensions/email/providers": {
                "method": "GET",
                "handler": providers,
                "login_required": True,
            }
        }

    def _send_email(self, to, subject, body, html=False):
        """Send email via SMTP."""
        try:
            if self.provider == "custom":
                host = self.custom_host
                port = self.custom_port
                tls = self.custom_tls
                if not host:
                    return {"success": False, "error": "Custom SMTP host is empty. Configure it in extension settings."}
            else:
                pc = self.PROVIDERS.get(self.provider, self.PROVIDERS["gmail"])
                host = pc["host"]
                port = pc["port"]
                tls = pc["tls"]

            msg = MIMEMultipart("alternative")
            msg["From"] = self.email_addr
            msg["To"] = to
            msg["Subject"] = subject

            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            with smtplib.SMTP(host, port) as server:
                if tls:
                    server.starttls()
                server.login(self.email_addr, self.password)
                server.send_message(msg)

            return {"success": True, "message": f"Email sent to {to}"}
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "error": "Authentication failed. Check email/password. For Gmail, use App Password."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_chat_tools(self):
        return [
            {
                "name": "send_email",
                "description": "Send an email to a recipient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body text"},
                        "html": {"type": "boolean", "description": "Whether body is HTML", "default": False}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "send_email":
            self._refresh_config()
            return self._send_email(
                parameters.get("to", ""),
                parameters.get("subject", ""),
                parameters.get("body", ""),
                parameters.get("html", False)
            )
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "provider",
                    "type": "select",
                    "label": "Email Provider",
                    "options": [
                        {"value": "gmail", "label": "Gmail"},
                        {"value": "outlook", "label": "Outlook/Hotmail"},
                        {"value": "yahoo", "label": "Yahoo Mail"},
                        {"value": "custom", "label": "Custom SMTP"}
                    ],
                    "value": self.get_config("provider", "gmail")
                },
                {
                    "name": "email",
                    "type": "text",
                    "label": "Email Address",
                    "placeholder": "your@email.com",
                    "value": self.get_config("email", "")
                },
                {
                    "name": "password",
                    "type": "password",
                    "label": "Password / App Password",
                    "placeholder": "For Gmail, use App Password",
                    "value": self.get_config("password", "")
                },
                {
                    "name": "custom_host",
                    "type": "text",
                    "label": "SMTP Host (Custom only)",
                    "placeholder": "smtp.example.com",
                    "value": self.get_config("custom_host", "")
                },
                {
                    "name": "custom_port",
                    "type": "number",
                    "label": "SMTP Port (Custom only)",
                    "placeholder": "587",
                    "value": self.get_config("custom_port", 587)
                },
                {
                    "name": "custom_tls",
                    "type": "boolean",
                    "label": "Enable TLS (Custom only)",
                    "value": self.get_config("custom_tls", True)
                }
            ]
        }
