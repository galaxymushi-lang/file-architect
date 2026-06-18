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
    version = "1.0.0"
    author = "FileArchitect"
    icon = "email"

    PROVIDERS = {
        "gmail": {"host": "smtp.gmail.com", "port": 587, "tls": True},
        "outlook": {"host": "smtp-mail.outlook.com", "port": 587, "tls": True},
        "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587, "tls": True},
        "custom": {"host": "", "port": 587, "tls": True}
    }

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.provider = self.get_config("provider", "gmail")
        self.email = self.get_config("email", "")
        self.password = self.get_config("password", "")

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
            if not self.email or not self.password:
                return jsonify({"error": "Email not configured. Go to Extensions > Email > Settings"}), 400

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
            provider_config = self.PROVIDERS.get(self.provider, self.PROVIDERS["gmail"])

            msg = MIMEMultipart("alternative")
            msg["From"] = self.email
            msg["To"] = to
            msg["Subject"] = subject

            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))

            with smtplib.SMTP(provider_config["host"], provider_config["port"]) as server:
                if provider_config.get("tls"):
                    server.starttls()
                server.login(self.email, self.password)
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
                    "value": "gmail"
                },
                {
                    "name": "email",
                    "type": "text",
                    "label": "Email Address",
                    "placeholder": "your@email.com"
                },
                {
                    "name": "password",
                    "type": "password",
                    "label": "Password / App Password",
                    "placeholder": "For Gmail, use App Password"
                }
            ]
        }
