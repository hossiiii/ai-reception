"""
コスト最適化システム

Phase 3のコスト管理機能:
1. リアルタイムコスト監視とアラート
2. 自動コスト制限とセッション終了
3. 使用量予測とバジェット管理
4. コスト効率の自動最適化
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import sqlite3
import aiosqlite
from datetime import datetime, timedelta


class CostLimitType(Enum):
    """コスト制限タイプ"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SESSION = "session"


class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CostLimits:
    """コスト制限設定"""
    hourly_limit: float = 50.0
    daily_limit: float = 500.0
    weekly_limit: float = 2000.0
    monthly_limit: float = 8000.0
    session_limit: float = 10.0
    
    # アラート閾値（制限の何%でアラート）
    warning_threshold: float = 0.7  # 70%
    critical_threshold: float = 0.9  # 90%
    emergency_threshold: float = 0.95  # 95%


@dataclass
class CostUsage:
    """コスト使用量"""
    session_id: str
    timestamp: float
    processing_mode: str
    audio_duration_seconds: float
    tokens_input: int
    tokens_output: int
    function_calls: int
    cost_breakdown: Dict[str, float]
    total_cost: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "processing_mode": self.processing_mode,
            "audio_duration_seconds": self.audio_duration_seconds,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "function_calls": self.function_calls,
            "cost_breakdown": self.cost_breakdown,
            "total_cost": self.total_cost
        }


@dataclass
class CostAlert:
    """コストアラート"""
    alert_id: str
    timestamp: float
    level: AlertLevel
    limit_type: CostLimitType
    current_usage: float
    limit_value: float
    threshold_percent: float
    message: str
    auto_action_taken: Optional[str] = None


class RealtimeCostCalculator:
    """リアルタイムコスト計算エンジン"""
    
    def __init__(self):
        # OpenAI Realtime API 料金設定（2024年11月時点）
        self.realtime_pricing = {
            "audio_input_per_minute": 0.06,
            "audio_output_per_minute": 0.24,
            "text_input_per_1k_tokens": 0.005,
            "text_output_per_1k_tokens": 0.02,
            "function_call_base": 0.001
        }
        
        # Legacy API 料金設定
        self.legacy_pricing = {
            "whisper_per_minute": 0.006,
            "tts_per_1k_chars": 0.015,
            "gpt4_input_per_1k_tokens": 0.03,
            "gpt4_output_per_1k_tokens": 0.06
        }
    
    def calculate_realtime_cost(
        self,
        audio_input_seconds: float = 0,
        audio_output_seconds: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        function_calls: int = 0
    ) -> Tuple[Dict[str, float], float]:
        """Realtime APIコスト計算"""
        
        cost_breakdown = {}
        
        # 音声入力コスト
        if audio_input_seconds > 0:
            audio_input_cost = (audio_input_seconds / 60) * self.realtime_pricing["audio_input_per_minute"]
            cost_breakdown["audio_input"] = audio_input_cost
        
        # 音声出力コスト
        if audio_output_seconds > 0:
            audio_output_cost = (audio_output_seconds / 60) * self.realtime_pricing["audio_output_per_minute"]
            cost_breakdown["audio_output"] = audio_output_cost
        
        # テキスト入力コスト
        if input_tokens > 0:
            text_input_cost = (input_tokens / 1000) * self.realtime_pricing["text_input_per_1k_tokens"]
            cost_breakdown["text_input"] = text_input_cost
        
        # テキスト出力コスト
        if output_tokens > 0:
            text_output_cost = (output_tokens / 1000) * self.realtime_pricing["text_output_per_1k_tokens"]
            cost_breakdown["text_output"] = text_output_cost
        
        # Function Callコスト
        if function_calls > 0:
            function_cost = function_calls * self.realtime_pricing["function_call_base"]
            cost_breakdown["function_calls"] = function_cost
        
        total_cost = sum(cost_breakdown.values())
        
        return cost_breakdown, total_cost
    
    def calculate_legacy_cost(
        self,
        audio_seconds: float = 0,
        tts_characters: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> Tuple[Dict[str, float], float]:
        """Legacy APIコスト計算"""
        
        cost_breakdown = {}
        
        # Whisperコスト
        if audio_seconds > 0:
            whisper_cost = (audio_seconds / 60) * self.legacy_pricing["whisper_per_minute"]
            cost_breakdown["whisper"] = whisper_cost
        
        # TTSコスト
        if tts_characters > 0:
            tts_cost = (tts_characters / 1000) * self.legacy_pricing["tts_per_1k_chars"]
            cost_breakdown["tts"] = tts_cost
        
        # GPT-4入力コスト
        if input_tokens > 0:
            gpt4_input_cost = (input_tokens / 1000) * self.legacy_pricing["gpt4_input_per_1k_tokens"]
            cost_breakdown["gpt4_input"] = gpt4_input_cost
        
        # GPT-4出力コスト
        if output_tokens > 0:
            gpt4_output_cost = (output_tokens / 1000) * self.legacy_pricing["gpt4_output_per_1k_tokens"]
            cost_breakdown["gpt4_output"] = gpt4_output_cost
        
        total_cost = sum(cost_breakdown.values())
        
        return cost_breakdown, total_cost
    
    def estimate_session_cost(self, session_duration_minutes: float, mode: str = "realtime") -> float:
        """セッションコスト予測"""
        if mode == "realtime":
            # 平均的なRealtime セッションのコスト予測
            avg_audio_ratio = 0.8  # 80%が音声
            avg_tokens_per_minute = 150
            avg_function_calls_per_minute = 0.5
            
            estimated_audio_input = session_duration_minutes * avg_audio_ratio
            estimated_audio_output = session_duration_minutes * avg_audio_ratio * 0.6
            estimated_tokens = int(session_duration_minutes * avg_tokens_per_minute)
            estimated_functions = int(session_duration_minutes * avg_function_calls_per_minute)
            
            _, total_cost = self.calculate_realtime_cost(
                audio_input_seconds=estimated_audio_input * 60,
                audio_output_seconds=estimated_audio_output * 60,
                input_tokens=estimated_tokens,
                output_tokens=estimated_tokens,
                function_calls=estimated_functions
            )
            
        else:  # legacy
            avg_tokens_per_minute = 200
            estimated_tokens = int(session_duration_minutes * avg_tokens_per_minute)
            estimated_audio = session_duration_minutes * 0.8
            estimated_tts_chars = estimated_tokens * 4  # 平均4文字/トークン
            
            _, total_cost = self.calculate_legacy_cost(
                audio_seconds=estimated_audio * 60,
                tts_characters=estimated_tts_chars,
                input_tokens=estimated_tokens,
                output_tokens=estimated_tokens
            )
        
        return total_cost


class CostLimitManager:
    """コスト制限管理"""
    
    def __init__(self, limits: CostLimits):
        self.limits = limits
        self.active_limits = {
            CostLimitType.HOURLY: True,
            CostLimitType.DAILY: True,
            CostLimitType.WEEKLY: True,
            CostLimitType.MONTHLY: True,
            CostLimitType.SESSION: True
        }
        
    def check_limit_exceeded(self, current_usage: float, limit_type: CostLimitType) -> Tuple[bool, float]:
        """制限超過チェック"""
        if not self.active_limits.get(limit_type, False):
            return False, 0.0
        
        limit_value = getattr(self.limits, f"{limit_type.value}_limit")
        exceeded = current_usage >= limit_value
        
        return exceeded, limit_value
    
    def get_alert_level(self, current_usage: float, limit_type: CostLimitType) -> Optional[AlertLevel]:
        """アラートレベル判定"""
        if not self.active_limits.get(limit_type, False):
            return None
        
        limit_value = getattr(self.limits, f"{limit_type.value}_limit")
        usage_ratio = current_usage / limit_value
        
        if usage_ratio >= self.limits.emergency_threshold:
            return AlertLevel.EMERGENCY
        elif usage_ratio >= self.limits.critical_threshold:
            return AlertLevel.CRITICAL
        elif usage_ratio >= self.limits.warning_threshold:
            return AlertLevel.WARNING
        
        return None
    
    def calculate_remaining_budget(self, current_usage: float, limit_type: CostLimitType) -> float:
        """残予算計算"""
        limit_value = getattr(self.limits, f"{limit_type.value}_limit")
        return max(0.0, limit_value - current_usage)


class CostOptimizer:
    """統合コスト最適化システム"""
    
    def __init__(self, db_path: str = "data/cost_management.db"):
        self.db_path = db_path
        self.calculator = RealtimeCostCalculator()
        self.limits = CostLimits()
        self.limit_manager = CostLimitManager(self.limits)
        
        # 使用量追跡
        self.usage_history = deque(maxlen=10000)
        self.session_costs = {}
        self.recent_alerts = deque(maxlen=100)
        
        # 自動アクション設定
        self.auto_actions_enabled = True
        self.emergency_shutdown_enabled = True
        
        self._initialized = False
        self._lock = asyncio.Lock()
        
        print("✅ CostOptimizer initialized")
    
    async def _ensure_initialized(self):
        """データベース初期化確認"""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
            
            await self._create_tables()
            self._initialized = True
    
    async def _create_tables(self):
        """コスト管理テーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            # コスト使用履歴テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cost_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    processing_mode TEXT NOT NULL,
                    audio_duration_seconds REAL,
                    tokens_input INTEGER,
                    tokens_output INTEGER,
                    function_calls INTEGER,
                    cost_breakdown TEXT,
                    total_cost REAL NOT NULL
                )
            """)
            
            # アラート履歴テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cost_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    level TEXT NOT NULL,
                    limit_type TEXT NOT NULL,
                    current_usage REAL NOT NULL,
                    limit_value REAL NOT NULL,
                    threshold_percent REAL NOT NULL,
                    message TEXT NOT NULL,
                    auto_action_taken TEXT
                )
            """)
            
            # 予算制限テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS budget_limits (
                    id INTEGER PRIMARY KEY,
                    hourly_limit REAL,
                    daily_limit REAL,
                    weekly_limit REAL,
                    monthly_limit REAL,
                    session_limit REAL,
                    warning_threshold REAL,
                    critical_threshold REAL,
                    emergency_threshold REAL,
                    updated_at REAL
                )
            """)
            
            # インデックス作成
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_usage(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alert_timestamp ON cost_alerts(timestamp)")
            
            await db.commit()
    
    async def record_cost_usage(
        self,
        session_id: str,
        processing_mode: str,
        audio_duration_seconds: float = 0,
        tokens_input: int = 0,
        tokens_output: int = 0,
        function_calls: int = 0
    ) -> Dict[str, Any]:
        """コスト使用量記録"""
        await self._ensure_initialized()
        
        try:
            # コスト計算
            if processing_mode == "realtime":
                cost_breakdown, total_cost = self.calculator.calculate_realtime_cost(
                    audio_input_seconds=audio_duration_seconds,
                    audio_output_seconds=audio_duration_seconds * 0.6,  # 60%が出力音声と仮定
                    input_tokens=tokens_input,
                    output_tokens=tokens_output,
                    function_calls=function_calls
                )
            else:  # legacy
                tts_chars = tokens_output * 4  # 平均4文字/トークン
                cost_breakdown, total_cost = self.calculator.calculate_legacy_cost(
                    audio_seconds=audio_duration_seconds,
                    tts_characters=tts_chars,
                    input_tokens=tokens_input,
                    output_tokens=tokens_output
                )
            
            # 使用量オブジェクト作成
            usage = CostUsage(
                session_id=session_id,
                timestamp=time.time(),
                processing_mode=processing_mode,
                audio_duration_seconds=audio_duration_seconds,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                function_calls=function_calls,
                cost_breakdown=cost_breakdown,
                total_cost=total_cost
            )
            
            # データベースに記録
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO cost_usage 
                    (session_id, timestamp, processing_mode, audio_duration_seconds, 
                     tokens_input, tokens_output, function_calls, cost_breakdown, total_cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, usage.timestamp, processing_mode, audio_duration_seconds,
                    tokens_input, tokens_output, function_calls, 
                    json.dumps(cost_breakdown), total_cost
                ))
                await db.commit()
            
            # インメモリ履歴更新
            self.usage_history.append(usage)
            
            # セッション別コスト累計
            if session_id not in self.session_costs:
                self.session_costs[session_id] = 0.0
            self.session_costs[session_id] += total_cost
            
            # コスト制限チェック
            limit_checks = await self._check_all_limits(session_id, total_cost)
            
            print(f"💰 Cost recorded: {session_id} (${total_cost:.4f}, mode: {processing_mode})")
            
            return {
                "success": True,
                "session_id": session_id,
                "total_cost": total_cost,
                "cost_breakdown": cost_breakdown,
                "session_total": self.session_costs[session_id],
                "limit_checks": limit_checks
            }
            
        except Exception as e:
            print(f"❌ Cost recording error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _check_all_limits(self, session_id: str, new_cost: float) -> Dict[str, Any]:
        """全コスト制限チェック"""
        limit_checks = {}
        alerts_triggered = []
        
        current_time = time.time()
        
        # 時間範囲別使用量取得
        usage_by_period = await self._get_usage_by_periods(current_time)
        
        # 各制限タイプをチェック
        for limit_type in CostLimitType:
            if limit_type == CostLimitType.SESSION:
                current_usage = self.session_costs.get(session_id, 0.0)
            else:
                current_usage = usage_by_period.get(limit_type.value, 0.0)
            
            # 制限超過チェック
            exceeded, limit_value = self.limit_manager.check_limit_exceeded(current_usage, limit_type)
            
            # アラートレベル判定
            alert_level = self.limit_manager.get_alert_level(current_usage, limit_type)
            
            limit_checks[limit_type.value] = {
                "current_usage": current_usage,
                "limit_value": limit_value,
                "exceeded": exceeded,
                "alert_level": alert_level.value if alert_level else None,
                "remaining_budget": self.limit_manager.calculate_remaining_budget(current_usage, limit_type)
            }
            
            # アラート生成
            if alert_level:
                alert = await self._create_alert(
                    limit_type, alert_level, current_usage, limit_value, session_id
                )
                alerts_triggered.append(alert)
        
        # 自動アクション実行
        if alerts_triggered and self.auto_actions_enabled:
            await self._execute_auto_actions(alerts_triggered, session_id)
        
        return {
            "limit_checks": limit_checks,
            "alerts_triggered": [alert.message for alert in alerts_triggered],
            "auto_actions_executed": len(alerts_triggered) > 0 and self.auto_actions_enabled
        }
    
    async def _get_usage_by_periods(self, current_time: float) -> Dict[str, float]:
        """期間別使用量取得"""
        try:
            periods = {
                "hourly": current_time - 3600,
                "daily": current_time - 86400,
                "weekly": current_time - 604800,
                "monthly": current_time - 2592000
            }
            
            usage_by_period = {}
            
            async with aiosqlite.connect(self.db_path) as db:
                for period_name, start_time in periods.items():
                    async with db.execute("""
                        SELECT SUM(total_cost) FROM cost_usage 
                        WHERE timestamp > ?
                    """, (start_time,)) as cursor:
                        result = await cursor.fetchone()
                        usage_by_period[period_name] = result[0] or 0.0
            
            return usage_by_period
            
        except Exception as e:
            print(f"❌ Usage calculation error: {e}")
            return {}
    
    async def _create_alert(
        self,
        limit_type: CostLimitType,
        alert_level: AlertLevel,
        current_usage: float,
        limit_value: float,
        session_id: str
    ) -> CostAlert:
        """アラート生成"""
        alert_id = f"{limit_type.value}_{alert_level.value}_{int(time.time())}"
        threshold_percent = current_usage / limit_value * 100
        
        message = f"{alert_level.value.upper()}: {limit_type.value} cost limit at {threshold_percent:.1f}% (${current_usage:.2f}/${limit_value:.2f})"
        
        alert = CostAlert(
            alert_id=alert_id,
            timestamp=time.time(),
            level=alert_level,
            limit_type=limit_type,
            current_usage=current_usage,
            limit_value=limit_value,
            threshold_percent=threshold_percent,
            message=message
        )
        
        # データベースに記録
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO cost_alerts 
                    (alert_id, timestamp, level, limit_type, current_usage, 
                     limit_value, threshold_percent, message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert_id, alert.timestamp, alert_level.value, limit_type.value,
                    current_usage, limit_value, threshold_percent, message
                ))
                await db.commit()
        except Exception as e:
            print(f"❌ Alert recording error: {e}")
        
        self.recent_alerts.append(alert)
        print(f"🚨 {message}")
        
        return alert
    
    async def _execute_auto_actions(self, alerts: List[CostAlert], session_id: str):
        """自動アクション実行"""
        for alert in alerts:
            action_taken = None
            
            if alert.level == AlertLevel.EMERGENCY and self.emergency_shutdown_enabled:
                # 緊急時はセッション強制終了
                action_taken = "emergency_session_termination"
                await self._terminate_session(session_id, "Emergency cost limit exceeded")
                
            elif alert.level == AlertLevel.CRITICAL:
                # 重要アラートでは新規セッション制限
                action_taken = "new_session_restriction"
                await self._restrict_new_sessions(alert.limit_type)
                
            elif alert.level == AlertLevel.WARNING:
                # 警告では通知のみ
                action_taken = "notification_sent"
                await self._send_cost_notification(alert)
            
            if action_taken:
                alert.auto_action_taken = action_taken
                print(f"🤖 Auto action executed: {action_taken} for {alert.alert_id}")
    
    async def _terminate_session(self, session_id: str, reason: str):
        """セッション強制終了"""
        print(f"🛑 Terminating session {session_id}: {reason}")
        # 実際のセッション終了処理は呼び出し元で実装
    
    async def _restrict_new_sessions(self, limit_type: CostLimitType):
        """新規セッション制限"""
        print(f"🚫 Restricting new sessions due to {limit_type.value} limit")
        # セッション制限の実装
    
    async def _send_cost_notification(self, alert: CostAlert):
        """コスト通知送信"""
        print(f"📧 Sending cost notification: {alert.message}")
        # 通知送信の実装
    
    async def get_cost_summary(self, hours: int = 24) -> Dict[str, Any]:
        """コストサマリー取得"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 期間内の使用量統計
                async with db.execute("""
                    SELECT 
                        processing_mode,
                        COUNT(*) as usage_count,
                        SUM(total_cost) as total_cost,
                        AVG(total_cost) as avg_cost,
                        SUM(audio_duration_seconds) as total_audio_seconds,
                        SUM(tokens_input + tokens_output) as total_tokens,
                        SUM(function_calls) as total_function_calls
                    FROM cost_usage 
                    WHERE timestamp > ?
                    GROUP BY processing_mode
                """, (start_time,)) as cursor:
                    mode_stats = await cursor.fetchall()
                
                # 時間別統計
                async with db.execute("""
                    SELECT 
                        CAST(timestamp / 3600 AS INTEGER) * 3600 as hour_bucket,
                        SUM(total_cost) as hourly_cost
                    FROM cost_usage 
                    WHERE timestamp > ?
                    GROUP BY hour_bucket
                    ORDER BY hour_bucket
                """, (start_time,)) as cursor:
                    hourly_stats = await cursor.fetchall()
            
            # 現在の制限状況
            usage_by_period = await self._get_usage_by_periods(current_time)
            
            summary = {
                "time_range_hours": hours,
                "timestamp": current_time,
                "by_mode": {},
                "hourly_breakdown": [],
                "current_limits": {},
                "total_cost": 0.0,
                "cost_efficiency": {}
            }
            
            # モード別統計
            total_cost = 0.0
            for mode_stat in mode_stats:
                mode_name = mode_stat[0]
                mode_data = {
                    "usage_count": mode_stat[1],
                    "total_cost": mode_stat[2],
                    "avg_cost": mode_stat[3],
                    "total_audio_seconds": mode_stat[4] or 0,
                    "total_tokens": mode_stat[5] or 0,
                    "total_function_calls": mode_stat[6] or 0
                }
                summary["by_mode"][mode_name] = mode_data
                total_cost += mode_stat[2]
            
            summary["total_cost"] = total_cost
            
            # 時間別統計
            for hour_stat in hourly_stats:
                summary["hourly_breakdown"].append({
                    "timestamp": hour_stat[0],
                    "cost": hour_stat[1]
                })
            
            # 制限状況
            for limit_type in CostLimitType:
                if limit_type == CostLimitType.SESSION:
                    continue  # セッション制限は個別管理
                
                current_usage = usage_by_period.get(limit_type.value, 0.0)
                limit_value = getattr(self.limits, f"{limit_type.value}_limit")
                
                summary["current_limits"][limit_type.value] = {
                    "current_usage": current_usage,
                    "limit_value": limit_value,
                    "usage_percent": (current_usage / limit_value * 100) if limit_value > 0 else 0,
                    "remaining_budget": max(0, limit_value - current_usage)
                }
            
            return summary
            
        except Exception as e:
            print(f"❌ Cost summary error: {e}")
            return {"error": str(e)}
    
    async def predict_cost_trend(self, prediction_hours: int = 24) -> Dict[str, Any]:
        """コストトレンド予測"""
        try:
            # 過去24時間のデータから予測
            recent_usage = list(self.usage_history)[-100:]  # 最新100件
            
            if len(recent_usage) < 10:
                return {"error": "Insufficient data for prediction"}
            
            # 時間あたりの平均コスト計算
            total_cost = sum(usage.total_cost for usage in recent_usage)
            time_span_hours = (recent_usage[-1].timestamp - recent_usage[0].timestamp) / 3600
            
            if time_span_hours <= 0:
                return {"error": "Invalid time span for prediction"}
            
            hourly_avg_cost = total_cost / time_span_hours
            
            # 予測計算
            predicted_cost = hourly_avg_cost * prediction_hours
            
            # モード別予測
            mode_predictions = {}
            for mode in ["realtime", "legacy"]:
                mode_usage = [u for u in recent_usage if u.processing_mode == mode]
                if mode_usage:
                    mode_cost = sum(u.total_cost for u in mode_usage)
                    mode_hourly = mode_cost / time_span_hours
                    mode_predictions[mode] = {
                        "predicted_cost": mode_hourly * prediction_hours,
                        "hourly_rate": mode_hourly
                    }
            
            return {
                "prediction_hours": prediction_hours,
                "predicted_total_cost": predicted_cost,
                "hourly_average_cost": hourly_avg_cost,
                "by_mode": mode_predictions,
                "data_points": len(recent_usage),
                "confidence": "high" if len(recent_usage) >= 50 else "medium"
            }
            
        except Exception as e:
            print(f"❌ Cost prediction error: {e}")
            return {"error": str(e)}
    
    async def update_cost_limits(self, new_limits: Dict[str, float]) -> Dict[str, Any]:
        """コスト制限更新"""
        try:
            # 制限値更新
            for limit_name, limit_value in new_limits.items():
                if hasattr(self.limits, limit_name):
                    setattr(self.limits, limit_name, limit_value)
            
            # データベースに保存
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO budget_limits 
                    (id, hourly_limit, daily_limit, weekly_limit, monthly_limit, 
                     session_limit, warning_threshold, critical_threshold, 
                     emergency_threshold, updated_at)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.limits.hourly_limit,
                    self.limits.daily_limit,
                    self.limits.weekly_limit,
                    self.limits.monthly_limit,
                    self.limits.session_limit,
                    self.limits.warning_threshold,
                    self.limits.critical_threshold,
                    self.limits.emergency_threshold,
                    time.time()
                ))
                await db.commit()
            
            print(f"💰 Cost limits updated: {new_limits}")
            
            return {
                "success": True,
                "updated_limits": new_limits,
                "current_limits": {
                    "hourly_limit": self.limits.hourly_limit,
                    "daily_limit": self.limits.daily_limit,
                    "weekly_limit": self.limits.weekly_limit,
                    "monthly_limit": self.limits.monthly_limit,
                    "session_limit": self.limits.session_limit
                }
            }
            
        except Exception as e:
            print(f"❌ Limit update error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_recent_alerts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """最近のアラート取得"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM cost_alerts 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,)) as cursor:
                    alerts = await cursor.fetchall()
            
            return [
                {
                    "alert_id": alert[1],
                    "timestamp": alert[2],
                    "level": alert[3],
                    "limit_type": alert[4],
                    "current_usage": alert[5],
                    "limit_value": alert[6],
                    "threshold_percent": alert[7],
                    "message": alert[8],
                    "auto_action_taken": alert[9]
                }
                for alert in alerts
            ]
            
        except Exception as e:
            print(f"❌ Alert retrieval error: {e}")
            return []


# グローバルインスタンス
cost_optimizer = CostOptimizer()


async def get_cost_optimizer() -> CostOptimizer:
    """コスト最適化サービス取得"""
    return cost_optimizer