"""
Extension Registry
Manages loading, enabling, and configuring extensions.
"""

import os
import json
import importlib
import importlib.util
import traceback

EXTENSIONS_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(os.path.dirname(EXTENSIONS_DIR), "extensions.json")


class ExtensionRegistry:
    """Manages all extensions."""

    def __init__(self, app=None):
        self.app = app
        self.extensions = {}
        self.config = {}
        self._hooks = {
            "on_chat_message": [],
            "on_ai_response": [],
            "on_file_upload": [],
        }

    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        self._load_config()
        self._discover_extensions()
        self._register_routes()

    def _load_config(self):
        """Load extension configs from extensions.json."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.config = {}
        else:
            self.config = {}

    def _save_config(self):
        """Save extension configs to extensions.json."""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def _discover_extensions(self):
        """Auto-discover and load extensions from builtin/ and plugins/."""
        for source_dir in ["builtin", "plugins"]:
            dir_path = os.path.join(EXTENSIONS_DIR, source_dir)
            if not os.path.isdir(dir_path):
                continue

            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if item.startswith("_") or item.startswith("."):
                    continue

                # Handle .py files
                if item.endswith(".py"):
                    module_name = item[:-3]
                    self._load_module(source_dir, module_name, item_path)

                # Handle directories with __init__.py
                elif os.path.isdir(item_path):
                    init_file = os.path.join(item_path, "__init__.py")
                    if os.path.exists(init_file):
                        self._load_module(f"{source_dir}.{item}", "__init__", init_file)

    def _load_module(self, package, module_name, file_path):
        """Load a single extension module."""
        try:
            if package == "builtin":
                full_module = f"extensions.builtin.{module_name}"
            elif package == "plugins":
                full_module = f"extensions.plugins.{module_name}"
            else:
                full_module = f"extensions.{package}.{module_name}"

            spec = importlib.util.spec_from_file_location(full_module, file_path)
            if spec is None or spec.loader is None:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find extension class (subclass of BaseExtension)
            from extensions.base import BaseExtension
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, BaseExtension)
                        and attr is not BaseExtension):
                    self._register_extension(attr, package)
                    break

        except Exception as e:
            print(f"[EXTENSION ERROR] Failed to load {package}/{module_name}: {e}")
            traceback.print_exc()

    def _register_extension(self, ext_class, source="builtin"):
        """Register an extension class."""
        ext = ext_class(self.app, self.config.get(ext_class.name, {}).get("config", {}))
        ext.enabled = self.config.get(ext_class.name, {}).get("enabled", True)
        self.extensions[ext.name] = ext

        # Register hooks
        if ext.enabled:
            self._setup_hooks(ext)

        print(f"[EXTENSION] Loaded: {ext.display_name} v{ext.version} ({source})")

    def _setup_hooks(self, ext):
        """Setup hooks for an enabled extension."""
        for hook_name in ["on_chat_message", "on_ai_response", "on_file_upload"]:
            handler = getattr(ext, hook_name, None)
            if handler and callable(handler):
                # Check if it's actually overridden (not the base class default)
                if handler.__func__ is not getattr(
                    type(ext).__mro__[1], hook_name, None
                ):
                    self._hooks[hook_name].append((ext.name, handler))

    def _register_routes(self):
        """Register extension routes with Flask."""
        for ext_name, ext in self.extensions.items():
            if not ext.enabled:
                continue
            routes = ext.get_routes()
            for route_path, route_info in routes.items():
                methods = route_info.get("method", "GET").split(",")
                handler = route_info.get("handler")
                login_required = route_info.get("login_required", False)

                if handler is None:
                    continue

                endpoint = f"ext_{ext_name}_{route_path.replace('/', '_').strip('_')}"

                # Wrap with login_required if needed
                if login_required:
                    from functools import wraps
                    from flask import session, redirect, url_for, jsonify

                    def make_wrapped_handler(h):
                        @wraps(h)
                        def wrapped(*args, **kwargs):
                            if "user" not in session:
                                return jsonify({"error": "Not authenticated"}), 401
                            return h(*args, **kwargs)
                        return wrapped

                    handler = make_wrapped_handler(handler)

                self.app.add_url_rule(
                    route_path,
                    endpoint=endpoint,
                    view_func=handler,
                    methods=methods,
                )

    def trigger_hook(self, hook_name, *args, **kwargs):
        """Trigger a hook across all enabled extensions."""
        results = []
        for ext_name, handler in self._hooks.get(hook_name, []):
            try:
                result = handler(*args, **kwargs)
                if result is not None:
                    results.append((ext_name, result))
            except Exception as e:
                print(f"[EXTENSION ERROR] Hook {hook_name} in {ext_name}: {e}")
        return results

    # ===== Public API =====

    def get_all(self):
        """Return info for all extensions."""
        return [ext.get_info() for ext in self.extensions.values()]

    def get_enabled(self):
        """Return enabled extensions."""
        return [ext.get_info() for ext in self.extensions.values() if ext.enabled]

    def get(self, name):
        """Get extension by name."""
        return self.extensions.get(name)

    def enable(self, name):
        """Enable an extension."""
        ext = self.extensions.get(name)
        if ext:
            ext.enabled = True
            self.config[name] = self.config.get(name, {})
            self.config[name]["enabled"] = True
            self._save_config()
            self._setup_hooks(ext)
            return True
        return False

    def disable(self, name):
        """Disable an extension."""
        ext = self.extensions.get(name)
        if ext:
            ext.enabled = False
            self.config[name] = self.config.get(name, {})
            self.config[name]["enabled"] = False
            self._save_config()
            # Remove hooks
            for hook_name in self._hooks:
                self._hooks[hook_name] = [
                    (n, h) for n, h in self._hooks[hook_name] if n != name
                ]
            return True
        return False

    def update_config(self, name, config):
        """Update extension configuration and re-init the extension."""
        ext = self.extensions.get(name)
        if ext:
            ext.config = config
            self.config[name] = self.config.get(name, {})
            self.config[name]["config"] = config
            self._save_config()
            # Re-init extension so it reads new config values
            if hasattr(ext, '_refresh_config'):
                ext._refresh_config()
            return True
        return False

    def get_chat_tools(self):
        """Get all chat tools from enabled extensions."""
        tools = []
        for ext_name, ext in self.extensions.items():
            if not ext.enabled:
                continue
            for tool in ext.get_chat_tools():
                tool["extension"] = ext_name
                tools.append(tool)
        return tools

    def execute_tool(self, tool_name, parameters):
        """Execute a chat tool by name."""
        for ext_name, ext in self.extensions.items():
            if not ext.enabled:
                continue
            tools = ext.get_chat_tools()
            for tool in tools:
                if tool["name"] == tool_name:
                    return ext.execute_tool(tool_name, parameters)
        return {"error": f"Tool {tool_name} not found"}

    def reload(self):
        """Reload extension configs and re-init. Routes stay registered."""
        self._load_config()
        for name, ext in self.extensions.items():
            ext_config = self.config.get(name, {}).get("config", {})
            ext.config = ext_config
            if hasattr(ext, '_refresh_config'):
                ext._refresh_config()
        # Re-setup hooks
        self._hooks = {
            "on_chat_message": [],
            "on_ai_response": [],
            "on_file_upload": [],
        }
        for name, ext in self.extensions.items():
            if ext.enabled:
                self._setup_hooks(ext)


# Global registry instance
registry = ExtensionRegistry()
