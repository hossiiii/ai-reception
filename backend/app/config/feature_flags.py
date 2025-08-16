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
    """動的フィーチャーフラグ管理（強化版）"""
    
    def __init__(self):
        self.flags = FeatureFlags()
        self._runtime_overrides: Dict[str, Any] = {}
        self._session_overrides: Dict[str, Dict[str, bool]] = {}  # セッション別オーバーライド
        self._ab_test_assignments: Dict[str, str] = {}  # A/Bテスト割り当て
        
    def is_enabled(self, flag_name: str, session_id: Optional[str] = None, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """フィーチャーフラグの有効性チェック（強化版）"""
        
        # 1. セッション別オーバーライドチェック（最優先）
        if session_id and session_id in self._session_overrides:
            if flag_name in self._session_overrides[session_id]:
                return self._session_overrides[session_id][flag_name]
        
        # 2. ランタイムオーバーライドチェック
        if flag_name in self._runtime_overrides:
            return self._runtime_overrides[flag_name]
        
        # 3. 基本フラグチェック
        base_value = getattr(self.flags, flag_name, False)
        
        # 4. 特別なロジック適用
        if flag_name == "realtime_mode_enabled":
            return self._check_realtime_eligibility(session_id, user_id, context)
        elif flag_name == "realtime_fallback_enabled":
            return self._check_fallback_eligibility(session_id, context)
        elif flag_name == "enable_performance_monitoring":
            return self._check_monitoring_eligibility(context)
        
        return base_value

    def enable_for_session(self, session_id: str, flag_name: str, enabled: bool = True) -> None:
        """特定セッションでのフラグ有効化"""
        if session_id not in self._session_overrides:
            self._session_overrides[session_id] = {}
        
        self._session_overrides[session_id][flag_name] = enabled
        print(f"🎛️ Flag '{flag_name}' {'enabled' if enabled else 'disabled'} for session {session_id}")

    def disable_for_session(self, session_id: str, flag_name: str) -> None:
        """特定セッションでのフラグ無効化"""
        self.enable_for_session(session_id, flag_name, False)

    def clear_session_overrides(self, session_id: str) -> None:
        """セッション別オーバーライドのクリア"""
        if session_id in self._session_overrides:
            del self._session_overrides[session_id]
            print(f"🧹 Session overrides cleared for {session_id}")

    def assign_ab_test(self, session_id: str, test_name: str, variant: str) -> None:
        """A/Bテスト割り当て"""
        self._ab_test_assignments[f"{session_id}:{test_name}"] = variant
        print(f"🧪 A/B test assignment: {session_id} -> {test_name}:{variant}")

    def get_ab_test_variant(self, session_id: str, test_name: str) -> Optional[str]:
        """A/Bテストバリアント取得"""
        return self._ab_test_assignments.get(f"{session_id}:{test_name}")

    def create_progressive_rollout(self, flag_name: str, target_percentage: int, duration_hours: int = 24) -> Dict[str, Any]:
        """段階的ロールアウトの作成"""
        import time
        
        rollout_config = {
            "flag_name": flag_name,
            "target_percentage": target_percentage,
            "start_time": time.time(),
            "duration_hours": duration_hours,
            "current_percentage": 0
        }
        
        # 実際の実装では永続化が必要
        print(f"📈 Progressive rollout created for '{flag_name}': 0% -> {target_percentage}% over {duration_hours}h")
        
        return rollout_config

    def update_rollout_percentage(self, flag_name: str, new_percentage: int) -> bool:
        """ロールアウト比率の更新"""
        try:
            if flag_name == "realtime_mode_enabled":
                self.flags.realtime_rollout_percentage = new_percentage
                print(f"📊 Rollout percentage updated for '{flag_name}': {new_percentage}%")
                return True
            return False
        except Exception as e:
            print(f"❌ Failed to update rollout percentage: {e}")
            return False
    
    def _check_realtime_eligibility(self, session_id: Optional[str] = None, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Realtimeモードの適用可否判定（強化版）"""
        
        # 強制モードチェック
        if self.flags.force_realtime_mode:
            return True
        
        # 基本フラグが無効の場合
        if not self.flags.realtime_mode_enabled:
            return False
        
        # A/Bテストチェック
        if session_id:
            ab_variant = self.get_ab_test_variant(session_id, "realtime_mode")
            if ab_variant == "realtime":
                return True
            elif ab_variant == "legacy":
                return False
        
        # 許可リストチェック
        if session_id and self.flags.realtime_allowlist_sessions:
            allowlist = [s.strip() for s in self.flags.realtime_allowlist_sessions.split(",")]
            if session_id in allowlist:
                return True
        
        # コンテキストベースの判定
        if context:
            # 特定条件でのRealtime有効化
            if context.get("user_preference") == "realtime":
                return True
            if context.get("device_type") == "desktop" and context.get("connection_speed") == "high":
                return True
            # システム負荷チェック
            if context.get("system_load", 0) > 0.8:
                return False  # 高負荷時はRealtime無効
        
        # ロールアウト比率チェック
        if self.flags.realtime_rollout_percentage > 0:
            # セッションIDベースのハッシュで一貫した判定
            if session_id:
                hash_value = hash(session_id) % 100
                return hash_value < self.flags.realtime_rollout_percentage
        
        return False

    def _check_fallback_eligibility(self, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """フォールバック機能の適用可否判定"""
        
        # 基本フラグチェック
        if not self.flags.realtime_fallback_enabled:
            return False
        
        # コンテキストベースの判定
        if context:
            # 特定のエラー状況では必ずフォールバック有効
            if context.get("error_count", 0) > 2:
                return True
            if context.get("api_error") in ["rate_limit", "quota_exceeded"]:
                return True
        
        return self.flags.realtime_fallback_enabled

    def _check_monitoring_eligibility(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """パフォーマンス監視の適用可否判定"""
        
        # 基本フラグチェック
        if not self.flags.enable_performance_monitoring:
            return False
        
        # リソース使用量チェック
        if context:
            cpu_usage = context.get("cpu_usage", 0)
            memory_usage = context.get("memory_usage", 0)
            
            # リソース使用量が高い場合は監視を制限
            if cpu_usage > 0.9 or memory_usage > 0.9:
                return False
        
        return True
    
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