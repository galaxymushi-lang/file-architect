"""
Calendar Extension
Manage events and schedules using Google Calendar API.
"""

import os
import json
import time
import urllib.request
import urllib.parse
from extensions.base import BaseExtension


class CalendarExtension(BaseExtension):
    """Google Calendar integration."""

    name = "calendar"
    display_name = "Calendar"
    description = "Manage events and schedules using Google Calendar"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "calendar"

    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://www.googleapis.com/calendar/v3"
    SCOPES = "https://www.googleapis.com/auth/calendar"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self._refresh_config()

    def _refresh_config(self):
        self.client_id = self.get_config("client_id", "")
        self.client_secret = self.get_config("client_secret", "")
        self.access_token = self.get_config("access_token", "")
        self.refresh_token = self.get_config("refresh_token", "")
        self.calendar_id = self.get_config("calendar_id", "primary")

    def get_routes(self):
        from flask import request, jsonify, redirect

        def auth_url():
            if not self.client_id:
                return jsonify({"error": "Client ID not configured"}), 400
            params = urllib.parse.urlencode({
                "client_id": self.client_id,
                "redirect_uri": request.host_url + "api/extensions/calendar/callback",
                "scope": self.SCOPES,
                "response_type": "code",
                "access_type": "offline"
            })
            return jsonify({"url": f"{self.AUTH_URL}?{params}"})

        def callback():
            code = request.args.get("code")
            if not code:
                return jsonify({"error": "No auth code"}), 400
            result = self._exchange_code(code, request.host_url)
            if result.get("success"):
                return redirect("/?calendar=connected")
            return jsonify(result), 400

        def list_events():
            data = request.get_json() or {}
            days = data.get("days", 7)
            result = self._list_events(days)
            return jsonify(result)

        def create_event():
            data = request.get_json()
            summary = data.get("summary", "")
            start = data.get("start", "")
            end = data.get("end", "")
            description = data.get("description", "")
            if not all([summary, start, end]):
                return jsonify({"error": "summary, start, and end required"}), 400
            result = self._create_event(summary, start, end, description)
            return jsonify(result)

        def delete_event():
            data = request.get_json()
            event_id = data.get("event_id", "")
            if not event_id:
                return jsonify({"error": "event_id required"}), 400
            result = self._delete_event(event_id)
            return jsonify(result)

        return {
            "/api/extensions/calendar/auth": {
                "method": "GET",
                "handler": auth_url,
                "login_required": True,
            },
            "/api/extensions/calendar/callback": {
                "method": "GET",
                "handler": callback,
                "login_required": False,
            },
            "/api/extensions/calendar/list": {
                "method": "POST",
                "handler": list_events,
                "login_required": True,
            },
            "/api/extensions/calendar/create": {
                "method": "POST",
                "handler": create_event,
                "login_required": True,
            },
            "/api/extensions/calendar/delete": {
                "method": "POST",
                "handler": delete_event,
                "login_required": True,
            }
        }

    def _api_request(self, url, method="GET", data=None):
        if not self.access_token:
            self._refresh_access_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def _refresh_access_token(self):
        if not self.refresh_token:
            return False
        try:
            data = urllib.parse.urlencode({
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }).encode()
            req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                tokens = json.loads(resp.read())
                self.access_token = tokens.get("access_token", "")
                self.set_config("access_token", self.access_token)
                return True
        except:
            return False

    def _exchange_code(self, code, host):
        try:
            data = urllib.parse.urlencode({
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": f"{host}api/extensions/calendar/callback",
                "grant_type": "authorization_code"
            }).encode()
            req = urllib.request.Request(self.TOKEN_URL, data=data, method="POST")
            with urllib.request.urlopen(req) as resp:
                tokens = json.loads(resp.read())
                self.access_token = tokens.get("access_token", "")
                self.refresh_token = tokens.get("refresh_token", self.refresh_token)
                self.set_config("access_token", self.access_token)
                self.set_config("refresh_token", self.refresh_token)
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _list_events(self, days=7):
        try:
            import datetime
            now = datetime.datetime.utcnow()
            end = now + datetime.timedelta(days=days)
            params = urllib.parse.urlencode({
                "timeMin": now.isoformat() + "Z",
                "timeMax": end.isoformat() + "Z",
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 50
            })
            result = self._api_request(f"{self.API_BASE}/calendars/{self.calendar_id}/events?{params}")
            events = []
            for item in result.get("items", []):
                start = item.get("start", {}).get("dateTime", item.get("start", {}).get("date", ""))
                end = item.get("end", {}).get("dateTime", item.get("end", {}).get("date", ""))
                events.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "No title"),
                    "start": start,
                    "end": end,
                    "description": item.get("description", "")
                })
            return {"success": True, "events": events}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_event(self, summary, start, end, description=""):
        try:
            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start, "timeZone": "UTC"},
                "end": {"dateTime": end, "timeZone": "UTC"}
            }
            result = self._api_request(
                f"{self.API_BASE}/calendars/{self.calendar_id}/events",
                method="POST",
                data=event
            )
            return {"success": True, "event_id": result.get("id")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _delete_event(self, event_id):
        try:
            url = f"{self.API_BASE}/calendars/{self.calendar_id}/events/{event_id}"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.access_token}"}, method="DELETE")
            urllib.request.urlopen(req)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_chat_tools(self):
        return [
            {
                "name": "calendar_list",
                "description": "List upcoming calendar events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Number of days to look ahead (default 7)"}
                    }
                }
            },
            {
                "name": "calendar_create",
                "description": "Create a new calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "start": {"type": "string", "description": "Start time (ISO format)"},
                        "end": {"type": "string", "description": "End time (ISO format)"},
                        "description": {"type": "string", "description": "Event description"}
                    },
                    "required": ["summary", "start", "end"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "calendar_list":
            return self._list_events(parameters.get("days", 7))
        elif tool_name == "calendar_create":
            return self._create_event(
                parameters.get("summary", ""),
                parameters.get("start", ""),
                parameters.get("end", ""),
                parameters.get("description", "")
            )
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "client_id",
                    "type": "text",
                    "label": "Google Client ID",
                    "placeholder": "From Google Cloud Console",
                    "value": self.get_config("client_id", "")
                },
                {
                    "name": "client_secret",
                    "type": "password",
                    "label": "Google Client Secret",
                    "placeholder": "From Google Cloud Console",
                    "value": self.get_config("client_secret", "")
                },
                {
                    "name": "calendar_id",
                    "type": "text",
                    "label": "Calendar ID",
                    "placeholder": "primary",
                    "value": self.get_config("calendar_id", "primary")
                }
            ]
        }
