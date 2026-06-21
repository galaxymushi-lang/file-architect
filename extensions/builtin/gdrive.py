"""
Google Drive Extension
Upload/download files to Google Drive via OAuth2.
"""

import json
import os
import urllib.request
import urllib.parse
import base64
from extensions.base import BaseExtension


class GoogleDriveExtension(BaseExtension):
    """Google Drive integration for file storage."""

    name = "gdrive"
    display_name = "Google Drive"
    description = "Upload and download files from Google Drive"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "drive"

    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

    SCOPES = "https://www.googleapis.com/auth/drive.file"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.client_id = self.get_config("client_id", "")
        self.client_secret = self.get_config("client_secret", "")
        self.access_token = self.get_config("access_token", "")
        self.refresh_token = self.get_config("refresh_token", "")

    def get_routes(self):
        from flask import request, jsonify, redirect

        def auth_url():
            if not self.client_id:
                return jsonify({"error": "Client ID not configured"}), 400
            params = urllib.parse.urlencode({
                "client_id": self.client_id,
                "redirect_uri": request.host_url + "api/extensions/gdrive/callback",
                "scope": self.SCOPES,
                "response_type": "code",
                "access_type": "offline"
            })
            return jsonify({"url": f"{self.AUTH_URL}?{params}"})

        def callback():
            code = request.args.get("code")
            if not code:
                return jsonify({"error": "No auth code"}), 400
            result = self._exchange_code(code)
            if result.get("success"):
                return redirect("/?gdrive=connected")
            return jsonify(result), 400

        def list_files():
            data = request.get_json() or {}
            query = data.get("query", "")
            result = self._list_files(query)
            return jsonify(result)

        def upload():
            from flask import request as req
            if 'file' not in req.files:
                return jsonify({"error": "No file"}), 400
            file = req.files['file']
            result = self._upload_file(file.filename, file.read())
            return jsonify(result)

        def download():
            data = request.get_json()
            file_id = data.get("file_id", "")
            result = self._get_download_url(file_id)
            return jsonify(result)

        return {
            "/api/extensions/gdrive/auth": {
                "method": "GET",
                "handler": auth_url,
                "login_required": True,
            },
            "/api/extensions/gdrive/callback": {
                "method": "GET",
                "handler": callback,
                "login_required": False,
            },
            "/api/extensions/gdrive/list": {
                "method": "POST",
                "handler": list_files,
                "login_required": True,
            },
            "/api/extensions/gdrive/upload": {
                "method": "POST",
                "handler": upload,
                "login_required": True,
            },
            "/api/extensions/gdrive/download": {
                "method": "POST",
                "handler": download,
                "login_required": True,
            }
        }

    def _exchange_code(self, code):
        """Exchange authorization code for tokens."""
        try:
            data = urllib.parse.urlencode({
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": "http://localhost:5000/api/extensions/gdrive/callback",
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

    def _refresh_access_token(self):
        """Refresh the access token."""
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

    def _api_request(self, url, method="GET", data=None):
        """Make authenticated API request."""
        if not self.access_token:
            self._refresh_access_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def _list_files(self, query="", max_results=20):
        """List files in Google Drive."""
        try:
            q = f"name contains '{query}'" if query else ""
            params = urllib.parse.urlencode({"q": q, "pageSize": max_results, "fields": "files(id,name,mimeType,size,modifiedTime)"})
            result = self._api_request(f"{self.API_BASE}/files?{params}")
            return {"files": result.get("files", [])}
        except Exception as e:
            return {"error": str(e)}

    def _upload_file(self, filename, content):
        """Upload file to Google Drive."""
        try:
            import io
            metadata = {"name": filename}
            boundary = "----GALACTOSBoundary"
            body = f"--{boundary}\r\nContent-Type: application/json\r\n\r\n{json.dumps(metadata)}\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n".encode()
            body += content
            body += f"\r\n--{boundary}--\r\n".encode()

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}"
            }
            req = urllib.request.Request(
                f"{self.UPLOAD_URL}?uploadType=multipart",
                data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                return {"success": True, "file_id": result.get("id"), "name": filename}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_download_url(self, file_id):
        """Get download URL for a file."""
        return {"url": f"{self.API_BASE}/files/{file_id}?alt=media", "auth_required": True}

    def get_chat_tools(self):
        return [
            {
                "name": "gdrive_list",
                "description": "List files in Google Drive",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (filename contains)"}
                    }
                }
            },
            {
                "name": "gdrive_upload",
                "description": "Upload a file to Google Drive (provide base64 content)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Filename"},
                        "content_base64": {"type": "string", "description": "File content as base64"}
                    },
                    "required": ["filename", "content_base64"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "gdrive_list":
            return self._list_files(parameters.get("query", ""))
        elif tool_name == "gdrive_upload":
            content = base64.b64decode(parameters.get("content_base64", ""))
            return self._upload_file(parameters.get("filename", "file"), content)
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "client_id",
                    "type": "text",
                    "label": "Google Client ID",
                    "placeholder": "From Google Cloud Console"
                },
                {
                    "name": "client_secret",
                    "type": "password",
                    "label": "Google Client Secret",
                    "placeholder": "From Google Cloud Console"
                }
            ]
        }
