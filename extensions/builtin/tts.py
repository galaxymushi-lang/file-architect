"""
Text-to-Speech Extension
Uses browser Web Speech API (client-side) + optional gTTS backend.
"""

import io
import os
from extensions.base import BaseExtension


class TextToSpeechExtension(BaseExtension):
    """Text-to-speech using browser API or gTTS."""

    name = "tts"
    display_name = "Text-to-Speech"
    description = "Convert text to speech using browser Web Speech API or Google TTS"
    version = "1.0.0"
    author = "GALACTOS"
    icon = "tts"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.backend = self.get_config("backend", "browser")

    def get_routes(self):
        from flask import request, jsonify, send_file

        def speak():
            data = request.get_json()
            text = data.get("text", "")
            if not text:
                return jsonify({"error": "No text provided"}), 400
            if self.backend == "gtts":
                return self._gtts_speak(text)
            return jsonify({"method": "browser", "text": text})

        return {
            "/api/extensions/tts/speak": {
                "method": "POST",
                "handler": speak,
                "login_required": True,
            }
        }

    def _gtts_speak(self, text):
        """Generate audio using gTTS."""
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en')
            audio = io.BytesIO()
            tts.write_to_fp(audio)
            audio.seek(0)
            return send_file(audio, mimetype="audio/mpeg", download_name="speech.mp3")
        except ImportError:
            return jsonify({"error": "gTTS not installed. Run: pip install gTTS", "fallback": "browser"}), 500
        except Exception as e:
            return jsonify({"error": str(e), "fallback": "browser"}), 500

    def get_chat_tools(self):
        return [
            {
                "name": "text_to_speech",
                "description": "Convert text to spoken audio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to speak"}
                    },
                    "required": ["text"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "text_to_speech":
            text = parameters.get("text", "")
            return {"method": "browser", "text": text, "message": "Audio will play in browser"}
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "backend",
                    "type": "select",
                    "label": "TTS Backend",
                    "options": [
                        {"value": "browser", "label": "Browser (Web Speech API)"},
                        {"value": "gtts", "label": "Google TTS (requires internet)"}
                    ],
                    "value": "browser"
                }
            ]
        }
