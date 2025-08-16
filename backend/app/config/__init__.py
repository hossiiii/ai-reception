"""
設定管理モジュール
"""

# Import the main settings object from config.py to maintain backward compatibility
import importlib.util
import os

# Load settings from the config.py file directly
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
spec = importlib.util.spec_from_file_location("app.config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
settings = config_module.settings

from .realtime_settings import RealtimeSettings, get_realtime_settings, validate_realtime_config
from .feature_flags import FeatureFlags, FeatureFlagManager, get_feature_flags, is_realtime_enabled

__all__ = [
    "settings",  # Export settings for backward compatibility
    "RealtimeSettings",
    "get_realtime_settings", 
    "validate_realtime_config",
    "FeatureFlags",
    "FeatureFlagManager",
    "get_feature_flags",
    "is_realtime_enabled"
]