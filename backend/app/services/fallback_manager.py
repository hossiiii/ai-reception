"""
フォールバック管理サービス

Realtime APIからLegacyモードへの自動フォールバック制御
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class FallbackReason(Enum):
    """フォールバック理由"""
    API_ERROR = "api_error"
    COST_LIMIT = "cost_limit"
    LATENCY_HIGH = "latency_high"
    ERROR_THRESHOLD = "error_threshold"
    MANUAL_TRIGGER = "manual_trigger"
    HEALTH_CHECK_FAIL = "health_check_fail"


@dataclass
class FallbackEvent:
    """フォールバックイベント"""
    session_id: str
    timestamp: float
    reason: FallbackReason
    details: Dict[str, Any]
    recovery_time: Optional[float] = None


class FallbackManager:
    """フォールバック管理サービス"""

    def __init__(self):
        # フォールバック設定
        self.error_threshold = 3  # 連続エラー閾値
        self.latency_threshold = 5.0  # レイテンシ閾値（秒）
        self.cost_threshold_per_hour = 50.0  # コスト閾値（USD/時）
        
        # フォールバック状態管理
        self.session_errors: Dict[str, int] = {}
        self.session_latencies: Dict[str, List[float]] = {}
        self.fallback_events: List[FallbackEvent] = []
        self.global_fallback_active = False
        self.global_fallback_until = 0.0
        
        print("✅ FallbackManager initialized")

    async def should_trigger_fallback(
        self, 
        session_id: str, 
        current_metrics: Dict[str, Any]
    ) -> tuple[bool, Optional[FallbackReason]]:
        """
        フォールバックをトリガーすべきかチェック
        
        Returns:
            (should_fallback, reason)
        """
        # グローバルフォールバックチェック
        if self.global_fallback_active and time.time() < self.global_fallback_until:
            return True, FallbackReason.API_ERROR
        
        # セッション固有のエラー率チェック
        error_count = self.session_errors.get(session_id, 0)
        if error_count >= self.error_threshold:
            return True, FallbackReason.ERROR_THRESHOLD
        
        # レイテンシチェック
        if self._check_latency_threshold(session_id, current_metrics.get("latency_ms", 0)):
            return True, FallbackReason.LATENCY_HIGH
        
        # コスト制限チェック
        hourly_cost = current_metrics.get("hourly_cost", 0.0)
        if hourly_cost >= self.cost_threshold_per_hour:
            return True, FallbackReason.COST_LIMIT
        
        return False, None

    async def record_error(self, session_id: str, error_details: Dict[str, Any]):
        """エラー記録とフォールバック判定"""
        # エラーカウント更新
        self.session_errors[session_id] = self.session_errors.get(session_id, 0) + 1
        
        print(f"⚠️ Error recorded for session {session_id}: {self.session_errors[session_id]} errors")
        
        # 重大なエラーの場合はグローバルフォールバック検討
        if self._is_critical_error(error_details):
            await self._trigger_global_fallback(FallbackReason.API_ERROR, error_details)

    async def record_latency(self, session_id: str, latency_ms: float):
        """レイテンシ記録"""
        if session_id not in self.session_latencies:
            self.session_latencies[session_id] = []
        
        # 直近5回のレイテンシを保持
        self.session_latencies[session_id].append(latency_ms)
        if len(self.session_latencies[session_id]) > 5:
            self.session_latencies[session_id].pop(0)

    async def trigger_fallback(
        self, 
        session_id: str, 
        reason: FallbackReason, 
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """フォールバック実行"""
        try:
            fallback_event = FallbackEvent(
                session_id=session_id,
                timestamp=time.time(),
                reason=reason,
                details=details or {}
            )
            
            self.fallback_events.append(fallback_event)
            
            print(f"🔄 Fallback triggered for session {session_id}: {reason.value}")
            
            # フォールバック理由に応じた処理
            if reason == FallbackReason.COST_LIMIT:
                # コスト制限の場合はグローバルフォールバックも検討
                await self._trigger_global_fallback(reason, details)
            
            return True
            
        except Exception as e:
            print(f"❌ Fallback trigger error: {e}")
            return False

    async def _trigger_global_fallback(
        self, 
        reason: FallbackReason, 
        details: Optional[Dict[str, Any]] = None
    ):
        """グローバルフォールバック実行"""
        self.global_fallback_active = True
        
        # フォールバック理由に応じた回復時間設定
        recovery_minutes = {
            FallbackReason.API_ERROR: 30,
            FallbackReason.COST_LIMIT: 60,
            FallbackReason.LATENCY_HIGH: 15,
            FallbackReason.HEALTH_CHECK_FAIL: 45
        }.get(reason, 30)
        
        self.global_fallback_until = time.time() + (recovery_minutes * 60)
        
        print(f"🚨 Global fallback activated: {reason.value} (recovery in {recovery_minutes} min)")

    def _check_latency_threshold(self, session_id: str, current_latency_ms: float) -> bool:
        """レイテンシ閾値チェック"""
        if session_id not in self.session_latencies:
            return False
        
        latencies = self.session_latencies[session_id]
        if len(latencies) < 3:  # 最低3回のサンプルが必要
            return False
        
        # 平均レイテンシが閾値を超えているかチェック
        avg_latency_ms = sum(latencies) / len(latencies)
        return avg_latency_ms > (self.latency_threshold * 1000)

    def _is_critical_error(self, error_details: Dict[str, Any]) -> bool:
        """重大なエラーかどうか判定"""
        error_message = error_details.get("message", "").lower()
        
        # 重大なエラーパターン
        critical_patterns = [
            "authentication",
            "rate limit",
            "quota exceeded",
            "service unavailable",
            "connection timeout"
        ]
        
        return any(pattern in error_message for pattern in critical_patterns)

    async def reset_session_state(self, session_id: str):
        """セッション状態リセット"""
        if session_id in self.session_errors:
            del self.session_errors[session_id]
        
        if session_id in self.session_latencies:
            del self.session_latencies[session_id]
        
        print(f"🔄 Session state reset: {session_id}")

    async def check_recovery_conditions(self) -> bool:
        """回復条件チェック"""
        if not self.global_fallback_active:
            return True
        
        current_time = time.time()
        
        # 回復時間チェック
        if current_time >= self.global_fallback_until:
            self.global_fallback_active = False
            print("✅ Global fallback recovered")
            return True
        
        return False

    async def get_fallback_status(self) -> Dict[str, Any]:
        """フォールバック状態取得"""
        current_time = time.time()
        
        # 最近のフォールバックイベント（過去1時間）
        recent_events = [
            event for event in self.fallback_events
            if current_time - event.timestamp <= 3600
        ]
        
        # セッション別エラー統計
        session_stats = {}
        for session_id, error_count in self.session_errors.items():
            session_stats[session_id] = {
                "error_count": error_count,
                "avg_latency_ms": (
                    sum(self.session_latencies.get(session_id, [])) / 
                    len(self.session_latencies.get(session_id, [1]))
                ) if session_id in self.session_latencies else 0.0
            }
        
        return {
            "global_fallback_active": self.global_fallback_active,
            "global_fallback_until": self.global_fallback_until,
            "recovery_seconds_remaining": max(0, self.global_fallback_until - current_time),
            "recent_fallback_events": len(recent_events),
            "session_error_counts": len(self.session_errors),
            "total_sessions_with_errors": len([e for e in self.session_errors.values() if e > 0]),
            "session_statistics": session_stats,
            "thresholds": {
                "error_threshold": self.error_threshold,
                "latency_threshold_ms": self.latency_threshold * 1000,
                "cost_threshold_per_hour": self.cost_threshold_per_hour
            }
        }

    async def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """閾値更新"""
        if "error_threshold" in new_thresholds:
            self.error_threshold = new_thresholds["error_threshold"]
        
        if "latency_threshold" in new_thresholds:
            self.latency_threshold = new_thresholds["latency_threshold"]
        
        if "cost_threshold_per_hour" in new_thresholds:
            self.cost_threshold_per_hour = new_thresholds["cost_threshold_per_hour"]
        
        print(f"📊 Fallback thresholds updated: {new_thresholds}")

    async def force_recovery(self, reason: str = "manual"):
        """強制回復"""
        self.global_fallback_active = False
        self.global_fallback_until = 0.0
        
        # セッションエラー状態もリセット
        self.session_errors.clear()
        self.session_latencies.clear()
        
        print(f"🔧 Forced fallback recovery triggered: {reason}")

    async def cleanup_old_events(self, max_age_hours: int = 24):
        """古いイベントのクリーンアップ"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        initial_count = len(self.fallback_events)
        self.fallback_events = [
            event for event in self.fallback_events
            if event.timestamp > cutoff_time
        ]
        
        cleaned_count = initial_count - len(self.fallback_events)
        if cleaned_count > 0:
            print(f"🧹 Cleaned up {cleaned_count} old fallback events")