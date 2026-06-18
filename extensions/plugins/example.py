"""
Example Plugin Template
Copy this file and rename it to create your own extension.
"""

from extensions.base import BaseExtension


class ExamplePlugin(BaseExtension):
    """Example plugin demonstrating the extension API."""

    name = "example"
    display_name = "Example Plugin"
    description = "A template for creating custom extensions"
    version = "1.0.0"
    author = "Your Name"
    icon = "puzzle"

    def __init__(self, app, config=None):
        super().__init__(app, config)

    def get_routes(self):
        """Example: add a custom API route."""
        from flask import jsonify

        def example_handler():
            return jsonify({"message": "Hello from Example Plugin!"})

        return {
            "/api/extensions/example/hello": {
                "method": "GET",
                "handler": example_handler,
                "login_required": True,
            }
        }

    def get_chat_tools(self):
        """Example: add a tool the AI can use."""
        return [
            {
                "name": "example_tool",
                "description": "An example tool that does something",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input text"}
                    },
                    "required": ["input"],
                },
            }
        ]

    def execute_tool(self, tool_name, parameters):
        """Example: handle tool execution."""
        if tool_name == "example_tool":
            return {"result": f"Processed: {parameters.get('input', '')}"}
        return {"error": f"Unknown tool: {tool_name}"}

    def on_chat_message(self, message, context):
        """Example: process chat messages before AI sees them."""
        # Add context or modify message here
        return None  # Return None to use original message

    def get_settings_schema(self):
        """Example: define settings UI."""
        return {
            "fields": [
                {
                    "name": "api_key",
                    "type": "password",
                    "label": "API Key",
                    "placeholder": "Enter your API key",
                },
                {
                    "name": "enabled_feature",
                    "type": "boolean",
                    "label": "Enable Special Feature",
                },
            ]
        }
