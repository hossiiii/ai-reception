"""
フィーチャーフラグ管理システム

段階的リリースとA/Bテストのためのフィーチャーフラグ
"""

import os
import json
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings


class FeatureFlags(BaseSettings):
    """フィーチャーフラグ設定"""
    
    # Realtime API関連
    realtime_mode_enabled: bool = False
    realtime_fallback_enabled: bool = True
    realtime_function_calls_enabled: bool = True
    
    # 段階的ロールアウト
    realtime_rollout_percentage: int = 0  # 0-100%
    realtime_allowlist_sessions: str = ""  # カンマ区切りのセッションIDリスト
    
    # 開発・テスト用
    force_realtime_mode: bool = False  # 開発時の強制有効化
    enable_debug_logging: bool = False
    enable_performance_monitoring: bool = True
    
    # コスト管理フラグ
    enable_cost_monitoring: bool = True
    enable_cost_alerts: bool = True
    auto_fallback_on_cost_limit: bool = True
    
    # セキュリティフラグ
    enable_audio_logging: bool = False
    enable_request_validation: bool = True
    
    class Config:
        env_file = ".env.realtime"
        env_file_encoding = "utf-8"
        env_prefix = "REALTIME_"
        extra = "ignore"  # 余分なフィールドを無視


class FeatureFlagManager:
    """動的フィーチャーフラグ管理"""
    
    def __init__(self):
        self.flags = FeatureFlags()
        self._runtime_overrides: Dict[str, Any] = {}
        
    def is_enabled(self, flag_name: str, session_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """フィーチャーフラグの有効性チェック"""
        
        # ランタイムオーバーライドチェック
        if flag_name in self._runtime_overrides:
            return self._runtime_overrides[flag_name]
        
        # 基本フラグチェック
        base_value = getattr(self.flags, flag_name, False)
        
        # 特別なロジック適用
        if flag_name == "realtime_mode_enabled":
            return self._check_realtime_eligibility(session_id, user_id)
        
        return base_value
    
    def _check_realtime_eligibility(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """Realtimeモードの適用可否判定"""
        
        # 強制モードチェック
        if self.flags.force_realtime_mode:
            return True
        
        # 基本フラグが無効の場合
        if not self.flags.realtime_mode_enabled:
            return False
        
        # 許可リストチェック
        if session_id and self.flags.realtime_allowlist_sessions:
            allowlist = [s.strip() for s in self.flags.realtime_allowlist_sessions.split(",")]
            if session_id in allowlist:
                return True
        
        # ロールアウト比率チェック
        if self.flags.realtime_rollout_percentage > 0:
            # セッションIDベースのハッシュで一貫した判定
            if session_id:
                hash_value = hash(session_id) % 100
                return hash_value < self.flags.realtime_rollout_percentage
        
        return False
    
    def set_runtime_override(self, flag_name: str, value: bool):
        """ランタイムでのフラグオーバーライド"""
        self._runtime_overrides[flag_name] = value
    
    def clear_runtime_override(self, flag_name: str):
        """ランタイムオーバーライドのクリア"""
        if flag_name in self._runtime_overrides:
            del self._runtime_overrides[flag_name]
    
    def get_all_flags(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """すべてのフラグ状態取得"""
        return {
            "realtime_mode_enabled": self.is_enabled("realtime_mode_enabled", session_id),
            "realtime_fallback_enabled": self.is_enabled("realtime_fallback_enabled", session_id),
            "realtime_function_calls_enabled": self.is_enabled("realtime_function_calls_enabled", session_id),
            "enable_cost_monitoring": self.is_enabled("enable_cost_monitoring", session_id),
            "enable_performance_monitoring": self.is_enabled("enable_performance_monitoring", session_id),
            "enable_debug_logging": self.is_enabled("enable_debug_logging", session_id),
        }
    
    def export_config(self) -> Dict[str, Any]:
        """設定のエクスポート（デバッグ用）"""
        return {
            "base_flags": {
                "realtime_mode_enabled": self.flags.realtime_mode_enabled,
                "realtime_rollout_percentage": self.flags.realtime_rollout_percentage,
                "force_realtime_mode": self.flags.force_realtime_mode,
                "enable_cost_monitoring": self.flags.enable_cost_monitoring
            },
            "runtime_overrides": self._runtime_overrides
        }


# グローバルインスタンス
feature_flag_manager = FeatureFlagManager()


def get_feature_flags() -> FeatureFlagManager:
    """フィーチャーフラグマネージャー取得"""
    return feature_flag_manager


# 便利な関数
def is_realtime_enabled(session_id: Optional[str] = None) -> bool:
    """Realtimeモードが有効かチェック"""
    return feature_flag_manager.is_enabled("realtime_mode_enabled", session_id)


def is_fallback_enabled() -> bool:
    """フォールバックが有効かチェック"""
    return feature_flag_manager.is_enabled("realtime_fallback_enabled")


def is_cost_monitoring_enabled() -> bool:
    """コスト監視が有効かチェック"""
    return feature_flag_manager.is_enabled("enable_cost_monitoring")