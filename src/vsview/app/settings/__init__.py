"""Settings submodule for vsview."""

from .action import ActionID
from .manager import SettingsManager
from .secrets import SecretsError, SecretsManager
from .shortcuts import ShortcutManager

__all__ = ["ActionID", "SecretsError", "SecretsManager", "SettingsManager", "ShortcutManager"]
