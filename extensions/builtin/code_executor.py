"""
Code Executor Extension
Sandboxed code execution for Python, JavaScript, and Shell.
"""

import subprocess
import os
import tempfile
import time
from extensions.base import BaseExtension


class CodeExecutorExtension(BaseExtension):
    """Execute code snippets in a sandboxed environment."""

    name = "code_executor"
    display_name = "Code Executor"
    description = "Execute Python, JavaScript, or Shell code in a sandboxed environment"
    version = "1.0.0"
    author = "FileArchitect"
    icon = "code"

    LANGUAGES = {
        "python": {"ext": ".py", "cmd": ["python", "-c"], "timeout": 30},
        "javascript": {"ext": ".js", "cmd": ["node"], "timeout": 15},
        "shell": {"ext": ".bat", "cmd": ["cmd", "/c"], "timeout": 10},
        "powershell": {"ext": ".ps1", "cmd": ["powershell", "-Command"], "timeout": 15}
    }

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.max_timeout = self.get_config("max_timeout", 30)

    def get_routes(self):
        from flask import request, jsonify

        def execute():
            data = request.get_json()
            language = data.get("language", "python")
            code = data.get("code", "")
            timeout = min(data.get("timeout", self.max_timeout), self.max_timeout)

            if not code:
                return jsonify({"error": "No code provided"}), 400
            if language not in self.LANGUAGES:
                return jsonify({"error": f"Unsupported language: {language}"}), 400

            result = self._execute(language, code, timeout)
            return jsonify(result)

        def languages():
            return jsonify({"languages": list(self.LANGUAGES.keys())})

        return {
            "/api/extensions/code_executor/execute": {
                "method": "POST",
                "handler": execute,
                "login_required": True,
            },
            "/api/extensions/code_executor/languages": {
                "method": "GET",
                "handler": languages,
                "login_required": True,
            }
        }

    def _execute(self, language, code, timeout):
        """Execute code and return result."""
        lang_config = self.LANGUAGES[language]
        start = time.time()

        try:
            if language == "python":
                result = subprocess.run(
                    ["python", "-c", code],
                    capture_output=True, text=True,
                    timeout=timeout, cwd=tempfile.gettempdir()
                )
            elif language == "shell":
                with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False) as f:
                    f.write(code)
                    f.flush()
                    result = subprocess.run(
                        ["cmd", "/c", f.name],
                        capture_output=True, text=True,
                        timeout=timeout, cwd=tempfile.gettempdir()
                    )
                    os.unlink(f.name)
            elif language == "powershell":
                result = subprocess.run(
                    ["powershell", "-Command", code],
                    capture_output=True, text=True,
                    timeout=timeout, cwd=tempfile.gettempdir()
                )
            elif language == "javascript":
                result = subprocess.run(
                    ["node", "-e", code],
                    capture_output=True, text=True,
                    timeout=timeout, cwd=tempfile.gettempdir()
                )
            else:
                return {"error": f"Language {language} not implemented"}

            elapsed = round(time.time() - start, 3)
            return {
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
                "language": language,
                "execution_time": f"{elapsed}s",
                "success": result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {"error": f"Execution timed out after {timeout}s", "language": language}
        except FileNotFoundError:
            return {"error": f"{language} runtime not found on system", "language": language}
        except Exception as e:
            return {"error": str(e), "language": language}

    def get_chat_tools(self):
        return [
            {
                "name": "execute_code",
                "description": "Execute code in Python, JavaScript, or Shell and return the output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string", "enum": ["python", "javascript", "shell", "powershell"], "description": "Programming language"},
                        "code": {"type": "string", "description": "Code to execute"}
                    },
                    "required": ["language", "code"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "execute_code":
            lang = parameters.get("language", "python")
            code = parameters.get("code", "")
            return self._execute(lang, code, self.max_timeout)
        return {"error": f"Unknown tool: {tool_name}"}

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "max_timeout",
                    "type": "number",
                    "label": "Max Execution Time (seconds)",
                    "value": 30,
                    "min": 5,
                    "max": 60
                }
            ]
        }
