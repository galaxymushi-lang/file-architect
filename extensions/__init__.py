"""
FileArchitect Extensions
Auto-discovers and loads all extensions.
"""

from extensions.registry import registry, ExtensionRegistry
from extensions.base import BaseExtension

__all__ = ["registry", "BaseExtension", "ExtensionRegistry"]
