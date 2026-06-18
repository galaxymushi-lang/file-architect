"""
Base Extension Class
All extensions must inherit from this class.
"""


class BaseExtension:
    """Base class for all FileArchitect extensions."""

    # Extension metadata (override in subclass)
    name = "base"
    display_name = "Base Extension"
    description = "Base extension class"
    version = "1.0.0"
    author = "FileArchitect"
    icon = "extension"  # Material icon name or SVG string

    def __init__(self, app, config=None):
        """
        Initialize extension.

        Args:
            app: Flask application instance
            config: Extension configuration dict (from extensions.json)
        """
        self.app = app
        self.config = config or {}
        self._enabled = True

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    def get_routes(self):
        """
        Return additional Flask routes for this extension.

        Returns:
            dict: {route_path: {"method": "POST", "handler": callable, "login_required": True}}
        """
        return {}

    def get_chat_tools(self):
        """
        Return tools available for AI function calling.

        Returns:
            list of dicts describing tools the AI can use
            Each dict: {"name": str, "description": str, "parameters": dict}
        """
        return []

    def execute_tool(self, tool_name, parameters):
        """
        Execute a chat tool by name.

        Args:
            tool_name: Name of the tool to execute
            parameters: Dict of parameters from the AI

        Returns:
            dict with "result" or "error" key
        """
        return {"error": f"Tool {tool_name} not implemented"}

    def on_chat_message(self, message, context):
        """
        Hook: called when user sends a chat message.
        Can modify message or add context before AI processing.

        Args:
            message: User's message string
            context: Dict with chat context (history, file, model, etc.)

        Returns:
            Modified message string, or None to use original
        """
        return None

    def on_ai_response(self, response, context):
        """
        Hook: called after AI generates a response.

        Args:
            response: AI's response string
            context: Dict with chat context

        Returns:
            Modified response string, or None to use original
        """
        return None

    def on_file_upload(self, file_info):
        """
        Hook: called when a file is uploaded.

        Args:
            file_info: Dict with file metadata (filename, type, path, etc.)
        """
        pass

    def get_settings_schema(self):
        """
        Return settings UI schema for this extension.

        Returns:
            dict describing settings fields:
            {
                "fields": [
                    {"name": "api_key", "type": "password", "label": "API Key", "placeholder": "sk-..."},
                    {"name": "enabled", "type": "boolean", "label": "Enable Feature"},
                ]
            }
        """
        return {"fields": []}

    def get_config(self, key, default=None):
        """Get a config value."""
        return self.config.get(key, default)

    def set_config(self, key, value):
        """Set a config value."""
        self.config[key] = value

    def get_info(self):
        """Return extension info for the UI."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "icon": self.icon,
            "enabled": self.enabled,
            "has_settings": bool(self.get_settings_schema().get("fields")),
            "has_routes": bool(self.get_routes()),
            "has_tools": bool(self.get_chat_tools()),
        }
