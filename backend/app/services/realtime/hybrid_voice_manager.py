"""
OpenAI Realtime APIとLangGraphの段階的ハイブリッド統合マネージャー

このマネージャーは以下の責務を持つ:
1. Realtime APIとLegacy AudioServiceの動的切り替え
2. フォールバック機能によるシステム安定性確保
3. コスト管理とセッション制御
4. メトリクス収集と運用監視
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional, Protocol
from dataclasses import dataclass
from enum import Enum

from ..session_store import SessionStore
from ..metrics_collector import MetricsCollector
from ..fallback_manager import FallbackManager
from .realtime_audio_processor import RealtimeAudioProcessor
from .langgraph_bridge import LangGraphBridge
from ..audio_service import AudioService
from ...config.feature_flags import FeatureFlags
from ...config.realtime_settings import RealtimeSettings


class VoiceProcessingMode(Enum):
    """音声処理モード"""
    LEGACY = "legacy"                    # 既存のAudioService使用
    REALTIME = "realtime"               # OpenAI Realtime API使用  
    HYBRID_FALLBACK = "hybrid_fallback" # Realtimeからlegacyへのフォールバック


@dataclass
class SessionMetrics:
    """セッションメトリクス"""
    session_id: str
    start_time: float
    mode: VoiceProcessingMode
    cost_usd: float = 0.0
    message_count: int = 0
    error_count: int = 0
    fallback_triggered: bool = False


class VoiceProcessor(Protocol):
    """音声処理プロトコル - 既存AudioServiceとRealtimeProcessorの共通インターフェース"""
    
    async def process_audio_input(self, audio_data: bytes) -> str:
        """音声をテキストに変換"""
        ...
    
    async def generate_audio_output(self, text: str) -> bytes:
        """テキストを音声に変換"""
        ...


class HybridVoiceManager:
    """段階的ハイブリッド音声処理マネージャー"""

    def __init__(self):
        # 依存サービス初期化
        self.session_store = SessionStore()
        self.metrics_collector = MetricsCollector()
        self.fallback_manager = FallbackManager()
        self.feature_flags = FeatureFlags()
        self.settings = RealtimeSettings()
        
        # 処理エンジン初期化
        self.legacy_processor = AudioService()
        self.realtime_processor = RealtimeAudioProcessor()
        self.langgraph_bridge = LangGraphBridge()
        
        # セッション管理
        self.active_sessions: Dict[str, SessionMetrics] = {}
        
        print("✅ HybridVoiceManager initialized")

    async def start_session(self, session_id: str, user_preferences: Optional[Dict] = None) -> Dict[str, Any]:
        """
        新しい音声セッションを開始
        
        Returns:
            セッション情報と処理モード
        """
        try:
            # セッション重複チェック
            if session_id in self.active_sessions:
                await self.end_session(session_id)
            
            # 処理モード決定
            processing_mode = await self._determine_processing_mode(user_preferences)
            
            # セッションメトリクス初期化
            session_metrics = SessionMetrics(
                session_id=session_id,
                start_time=time.time(),
                mode=processing_mode
            )
            self.active_sessions[session_id] = session_metrics
            
            # セッション状態保存
            await self.session_store.create_session(session_id, {
                "mode": processing_mode.value,
                "start_time": session_metrics.start_time,
                "preferences": user_preferences or {}
            })
            
            # モード別初期化
            if processing_mode == VoiceProcessingMode.REALTIME:
                initialization_result = await self.realtime_processor.initialize_session(session_id)
                if not initialization_result["success"]:
                    # Realtime API初期化失敗時はフォールバック
                    processing_mode = VoiceProcessingMode.LEGACY
                    session_metrics.mode = processing_mode
                    session_metrics.fallback_triggered = True
                    
            # メトリクス記録
            await self.metrics_collector.record_session_start(session_id, processing_mode.value)
            
            return {
                "success": True,
                "session_id": session_id,
                "processing_mode": processing_mode.value,
                "features": {
                    "realtime_enabled": processing_mode == VoiceProcessingMode.REALTIME,
                    "low_latency": processing_mode == VoiceProcessingMode.REALTIME,
                    "cost_monitoring": True
                },
                "limits": {
                    "max_session_time": self.settings.max_session_time,
                    "cost_limit": self.settings.cost_limit_per_hour
                }
            }
            
        except Exception as e:
            print(f"❌ Session start error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "processing_mode": VoiceProcessingMode.LEGACY.value,
                "error": str(e)
            }

    async def process_audio_message(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """
        音声メッセージを処理
        
        Args:
            session_id: セッションID
            audio_data: 音声データ
            
        Returns:
            処理結果とAI応答
        """
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": "Session not found",
                "fallback_to_legacy": True
            }
        
        session_metrics = self.active_sessions[session_id]
        processor = await self._get_processor(session_metrics.mode)
        
        try:
            # セッション制限チェック
            if await self._should_fallback(session_id):
                processor = await self._initiate_fallback(session_id)
            
            # 音声処理実行
            start_time = time.time()
            
            if session_metrics.mode == VoiceProcessingMode.REALTIME:
                # Realtime API: リアルタイム双方向処理
                result = await self._process_realtime_audio(session_id, audio_data)
            else:
                # Legacy: 従来のパイプライン処理
                result = await self._process_legacy_audio(session_id, audio_data)
            
            # 処理時間とコスト記録
            processing_time = time.time() - start_time
            await self._update_session_metrics(session_id, processing_time, result.get("cost", 0))
            
            return result
            
        except Exception as e:
            # エラー時の自動フォールバック
            session_metrics.error_count += 1
            await self.metrics_collector.record_error(session_id, str(e))
            
            if session_metrics.mode == VoiceProcessingMode.REALTIME and session_metrics.error_count >= 2:
                print(f"⚠️ Triggering fallback for session {session_id} due to errors")
                processor = await self._initiate_fallback(session_id)
                return await self._process_legacy_audio(session_id, audio_data)
            
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
                "processing_mode": session_metrics.mode.value
            }

    async def _process_realtime_audio(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Realtime APIによる音声処理（強化版フォールバック付き）"""
        session_metrics = self.active_sessions[session_id]
        max_retries = 2
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Realtime APIでリアルタイム処理
                realtime_result = await asyncio.wait_for(
                    self.realtime_processor.process_audio_stream(session_id, audio_data),
                    timeout=15.0  # 15秒タイムアウト
                )
                
                if not realtime_result["success"]:
                    raise Exception(realtime_result.get("error", "Realtime processing failed"))
                
                # LangGraphとの統合: Function Callsを使用
                if realtime_result.get("requires_langgraph"):
                    function_calls = realtime_result.get("function_calls", [])
                    
                    for function_call in function_calls:
                        bridge_result = await self.langgraph_bridge.execute_function_call(
                            session_id=session_id,
                            function_name=function_call["name"],
                            parameters=function_call["parameters"],
                            call_id=function_call.get("call_id")
                        )
                        
                        # Realtime APIに結果を返送
                        await self.realtime_processor.send_function_result(session_id, bridge_result)
                
                # パフォーマンス監視
                processing_time = time.time() - start_time
                if processing_time > 10.0:  # 10秒を超える場合は警告
                    print(f"⚠️ Slow Realtime processing: {processing_time:.2f}s for session {session_id}")
                    session_metrics.error_count += 1
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "processing_mode": "realtime",
                    "transcription": realtime_result.get("transcription", ""),
                    "ai_response": realtime_result.get("ai_response", ""),
                    "audio_response": realtime_result.get("audio_data", b""),
                    "latency_ms": realtime_result.get("latency_ms", 0),
                    "cost": realtime_result.get("cost", 0),
                    "features_used": realtime_result.get("features", []),
                    "processing_time": processing_time,
                    "attempt": attempt + 1
                }
                
            except asyncio.TimeoutError:
                session_metrics.error_count += 1
                print(f"⏰ Realtime processing timeout (attempt {attempt + 1}) for session {session_id}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # タイムアウト時は強制フォールバック
                    print(f"🔄 Timeout fallback triggered for session {session_id}")
                    return await self._emergency_fallback_to_legacy(session_id, audio_data, "timeout")
                    
            except Exception as e:
                session_metrics.error_count += 1
                error_msg = str(e)
                print(f"❌ Realtime processing error (attempt {attempt + 1}): {error_msg}")
                
                # 特定のエラーは即座にフォールバック
                if any(keyword in error_msg.lower() for keyword in ["rate_limit", "quota", "api_key", "unauthorized"]):
                    print(f"🔄 Critical error fallback triggered for session {session_id}: {error_msg}")
                    return await self._emergency_fallback_to_legacy(session_id, audio_data, f"critical_error: {error_msg}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    # 最終試行失敗時もフォールバック
                    print(f"🔄 Error fallback triggered for session {session_id}")
                    return await self._emergency_fallback_to_legacy(session_id, audio_data, f"max_retries_exceeded: {error_msg}")
        
        # ここに到達することはないが、安全のため
        return await self._emergency_fallback_to_legacy(session_id, audio_data, "unexpected_path")

    async def _emergency_fallback_to_legacy(self, session_id: str, audio_data: bytes, reason: str) -> Dict[str, Any]:
        """緊急時のLegacyモードフォールバック"""
        session_metrics = self.active_sessions[session_id]
        
        try:
            print(f"🚨 Emergency fallback to legacy mode: {session_id} (reason: {reason})")
            
            # セッションモードを強制変更
            session_metrics.mode = VoiceProcessingMode.HYBRID_FALLBACK
            session_metrics.fallback_triggered = True
            
            # Realtimeセッションのクリーンアップ
            try:
                await self.realtime_processor.cleanup_session(session_id)
            except Exception as cleanup_error:
                print(f"⚠️ Cleanup error during fallback: {cleanup_error}")
            
            # Legacyモードで処理
            fallback_result = await self._process_legacy_audio(session_id, audio_data)
            
            # フォールバック情報を追加
            fallback_result.update({
                "fallback_triggered": True,
                "fallback_reason": reason,
                "original_mode": "realtime"
            })
            
            # メトリクス記録
            await self.metrics_collector.record_fallback(session_id, reason)
            
            return fallback_result
            
        except Exception as e:
            print(f"❌ Emergency fallback failed: {e}")
            
            # 最後の手段: エラーレスポンス
            return {
                "success": False,
                "session_id": session_id,
                "processing_mode": "emergency_error",
                "error": f"Both realtime and fallback processing failed: {e}",
                "fallback_triggered": True,
                "fallback_reason": reason,
                "transcription": "",
                "ai_response": "申し訳ございません。システムエラーが発生しました。しばらくお待ちいただくか、スタッフにお声がけください。",
                "audio_response": b""
            }

    async def _process_legacy_audio(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Legacy AudioServiceによる音声処理"""
        try:
            # 1. 音声認識
            transcription = await self.legacy_processor.process_audio_input(audio_data)
            
            if not transcription.strip():
                return {
                    "success": False,
                    "error": "No transcription available",
                    "session_id": session_id,
                    "processing_mode": "legacy"
                }
            
            # 2. LangGraph処理 (既存フロー)
            from ...agents.reception_graph import ReceptionGraphManager
            graph_manager = ReceptionGraphManager()
            
            ai_result = await graph_manager.send_message(session_id, transcription)
            
            if not ai_result["success"]:
                raise Exception(ai_result.get("error", "LangGraph processing failed"))
            
            # 3. 音声合成
            ai_response_text = ai_result["message"]
            audio_response = await self.legacy_processor.generate_audio_output(ai_response_text)
            
            return {
                "success": True,
                "session_id": session_id,
                "processing_mode": "legacy",
                "transcription": transcription,
                "ai_response": ai_response_text,
                "audio_response": audio_response,
                "step": ai_result.get("step"),
                "visitor_info": ai_result.get("visitor_info"),
                "completed": ai_result.get("completed", False),
                "cost": 0.02  # 概算コスト
            }
            
        except Exception as e:
            print(f"❌ Legacy processing error: {e}")
            raise

    async def _determine_processing_mode(self, user_preferences: Optional[Dict] = None) -> VoiceProcessingMode:
        """処理モードを決定"""
        
        # フィーチャーフラグチェック
        if not self.feature_flags.realtime_mode_enabled:
            return VoiceProcessingMode.LEGACY
        
        # Realtime API利用可能性チェック
        if not await self.realtime_processor.health_check():
            return VoiceProcessingMode.LEGACY
        
        # コスト制限チェック
        if await self._is_cost_limit_exceeded():
            return VoiceProcessingMode.LEGACY
        
        # ユーザー設定考慮
        if user_preferences and user_preferences.get("prefer_legacy", False):
            return VoiceProcessingMode.LEGACY
        
        return VoiceProcessingMode.REALTIME

    async def _should_fallback(self, session_id: str) -> bool:
        """フォールバックが必要かチェック（強化版）"""
        session_metrics = self.active_sessions.get(session_id)
        if not session_metrics:
            return True
        
        current_time = time.time()
        session_duration = current_time - session_metrics.start_time
        
        # 1. セッション時間制限
        if session_duration > self.settings.max_session_time:
            print(f"⚠️ Session time limit exceeded: {session_id} ({session_duration:.1f}s)")
            return True
        
        # 2. コスト制限
        if session_metrics.cost_usd > self.settings.cost_limit_per_session:
            print(f"⚠️ Session cost limit exceeded: {session_id} (${session_metrics.cost_usd:.3f})")
            return True
        
        # 3. エラー率チェック（時間考慮）
        error_rate = session_metrics.error_count / max(session_metrics.message_count, 1)
        if session_metrics.error_count > 3 and error_rate > 0.5:
            print(f"⚠️ High error rate: {session_id} ({session_metrics.error_count} errors, {error_rate:.2f} rate)")
            return True
        
        # 4. 連続エラーチェック
        if session_metrics.error_count >= 5:
            print(f"⚠️ Too many consecutive errors: {session_id} ({session_metrics.error_count} errors)")
            return True
        
        # 5. システム全体のコスト制限
        if await self._is_system_cost_limit_exceeded():
            print(f"⚠️ System-wide cost limit exceeded, triggering fallback for {session_id}")
            return True
        
        # 6. Realtime API健全性チェック
        if session_metrics.mode == VoiceProcessingMode.REALTIME:
            api_health = await self._check_realtime_api_health()
            if not api_health["healthy"]:
                print(f"⚠️ Realtime API unhealthy: {api_health['reason']}, triggering fallback for {session_id}")
                return True
        
        # 7. パフォーマンス劣化チェック
        if await self._is_performance_degraded(session_id):
            print(f"⚠️ Performance degradation detected for {session_id}")
            return True
        
        return False

    async def _is_system_cost_limit_exceeded(self) -> bool:
        """システム全体のコスト制限チェック"""
        try:
            hourly_cost = await self.metrics_collector.get_hourly_cost()
            return hourly_cost > self.settings.cost_limit_per_hour
        except Exception as e:
            print(f"⚠️ Cost check error: {e}")
            return False

    async def _check_realtime_api_health(self) -> Dict[str, Any]:
        """Realtime API健全性チェック"""
        try:
            # 簡易健全性チェック
            health_check = await asyncio.wait_for(
                self.realtime_processor.health_check(),
                timeout=5.0
            )
            
            if health_check:
                return {"healthy": True, "reason": "api_responsive"}
            else:
                return {"healthy": False, "reason": "api_not_responding"}
                
        except asyncio.TimeoutError:
            return {"healthy": False, "reason": "api_timeout"}
        except Exception as e:
            return {"healthy": False, "reason": f"api_error: {e}"}

    async def _is_performance_degraded(self, session_id: str) -> bool:
        """パフォーマンス劣化チェック"""
        try:
            session_metrics = self.active_sessions.get(session_id)
            if not session_metrics:
                return False
            
            # 最近のメッセージの平均処理時間を取得
            recent_metrics = await self.metrics_collector.get_recent_performance_metrics(session_id, minutes=5)
            
            if not recent_metrics:
                return False
            
            avg_processing_time = recent_metrics.get("avg_processing_time", 0)
            avg_latency = recent_metrics.get("avg_latency", 0)
            
            # パフォーマンス劣化の閾値
            if avg_processing_time > 8.0:  # 8秒を超える平均処理時間
                return True
            
            if avg_latency > 3000:  # 3秒を超える平均レイテンシ
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Performance check error: {e}")
            return False

    async def monitor_system_performance(self) -> Dict[str, Any]:
        """システム全体のパフォーマンス監視"""
        try:
            current_time = time.time()
            
            # アクティブセッション統計
            total_sessions = len(self.active_sessions)
            realtime_sessions = sum(1 for s in self.active_sessions.values() if s.mode == VoiceProcessingMode.REALTIME)
            fallback_sessions = sum(1 for s in self.active_sessions.values() if s.fallback_triggered)
            
            # コスト統計
            total_cost = sum(s.cost_usd for s in self.active_sessions.values())
            hourly_cost = await self.metrics_collector.get_hourly_cost()
            
            # エラー統計
            total_errors = sum(s.error_count for s in self.active_sessions.values())
            
            # システム健全性スコア計算
            health_score = await self._calculate_system_health_score()
            
            performance_report = {
                "timestamp": current_time,
                "sessions": {
                    "total": total_sessions,
                    "realtime": realtime_sessions,
                    "legacy": total_sessions - realtime_sessions,
                    "fallback_triggered": fallback_sessions
                },
                "costs": {
                    "current_total": total_cost,
                    "hourly_total": hourly_cost,
                    "limit_per_hour": self.settings.cost_limit_per_hour,
                    "utilization_percent": (hourly_cost / self.settings.cost_limit_per_hour) * 100
                },
                "errors": {
                    "total_count": total_errors,
                    "error_rate": total_errors / max(total_sessions, 1)
                },
                "health": {
                    "score": health_score,
                    "status": "healthy" if health_score > 0.8 else "degraded" if health_score > 0.5 else "critical"
                }
            }
            
            # アラート判定
            alerts = []
            if performance_report["costs"]["utilization_percent"] > 80:
                alerts.append("high_cost_utilization")
            if performance_report["errors"]["error_rate"] > 0.3:
                alerts.append("high_error_rate")
            if performance_report["health"]["score"] < 0.5:
                alerts.append("system_health_critical")
            
            performance_report["alerts"] = alerts
            
            return performance_report
            
        except Exception as e:
            print(f"❌ Performance monitoring error: {e}")
            return {
                "timestamp": time.time(),
                "error": str(e),
                "status": "monitoring_failed"
            }

    async def _calculate_system_health_score(self) -> float:
        """システム健全性スコア計算（0.0-1.0）"""
        try:
            score_factors = []
            
            # 1. API健全性 (30%)
            api_health = await self._check_realtime_api_health()
            api_score = 1.0 if api_health["healthy"] else 0.0
            score_factors.append(("api_health", api_score, 0.3))
            
            # 2. エラー率 (25%)
            total_errors = sum(s.error_count for s in self.active_sessions.values())
            total_messages = sum(s.message_count for s in self.active_sessions.values())
            error_rate = total_errors / max(total_messages, 1)
            error_score = max(0.0, 1.0 - error_rate * 2)  # エラー率50%で0点
            score_factors.append(("error_rate", error_score, 0.25))
            
            # 3. コスト効率 (20%)
            hourly_cost = await self.metrics_collector.get_hourly_cost()
            cost_utilization = hourly_cost / self.settings.cost_limit_per_hour
            cost_score = max(0.0, 1.0 - cost_utilization)  # 100%利用で0点
            score_factors.append(("cost_efficiency", cost_score, 0.2))
            
            # 4. フォールバック率 (15%)
            fallback_sessions = sum(1 for s in self.active_sessions.values() if s.fallback_triggered)
            total_sessions = len(self.active_sessions)
            fallback_rate = fallback_sessions / max(total_sessions, 1)
            fallback_score = max(0.0, 1.0 - fallback_rate * 2)  # フォールバック率50%で0点
            score_factors.append(("fallback_rate", fallback_score, 0.15))
            
            # 5. セッション持続性 (10%)
            avg_session_duration = sum(time.time() - s.start_time for s in self.active_sessions.values()) / max(total_sessions, 1)
            target_duration = 300  # 5分が理想
            duration_score = min(1.0, avg_session_duration / target_duration)
            score_factors.append(("session_duration", duration_score, 0.1))
            
            # 重み付き平均計算
            weighted_score = sum(score * weight for _, score, weight in score_factors)
            
            return round(weighted_score, 3)
            
        except Exception as e:
            print(f"⚠️ Health score calculation error: {e}")
            return 0.5  # デフォルト値

    async def _initiate_fallback(self, session_id: str) -> VoiceProcessor:
        """フォールバックを実行"""
        session_metrics = self.active_sessions[session_id]
        
        print(f"🔄 Initiating fallback for session {session_id}")
        
        # Realtimeセッション終了
        if session_metrics.mode == VoiceProcessingMode.REALTIME:
            await self.realtime_processor.cleanup_session(session_id)
        
        # Legacyモードに切り替え
        session_metrics.mode = VoiceProcessingMode.HYBRID_FALLBACK
        session_metrics.fallback_triggered = True
        
        # メトリクス記録
        await self.metrics_collector.record_fallback(session_id, "cost_limit_exceeded")
        
        return self.legacy_processor

    async def _get_processor(self, mode: VoiceProcessingMode) -> VoiceProcessor:
        """モードに応じた処理エンジンを取得"""
        if mode == VoiceProcessingMode.REALTIME:
            return self.realtime_processor
        else:
            return self.legacy_processor

    async def _update_session_metrics(self, session_id: str, processing_time: float, cost: float):
        """セッションメトリクスを更新"""
        if session_id in self.active_sessions:
            session_metrics = self.active_sessions[session_id]
            session_metrics.cost_usd += cost
            session_metrics.message_count += 1
            
            await self.metrics_collector.record_message_processed(
                session_id, processing_time, cost, session_metrics.mode.value
            )

    async def _is_cost_limit_exceeded(self) -> bool:
        """コスト制限チェック"""
        return await self.metrics_collector.get_hourly_cost() > self.settings.cost_limit_per_hour

    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """セッション終了"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session_metrics = self.active_sessions[session_id]
        
        try:
            # モード別クリーンアップ
            if session_metrics.mode == VoiceProcessingMode.REALTIME:
                await self.realtime_processor.cleanup_session(session_id)
            
            # セッション終了メトリクス記録
            session_duration = time.time() - session_metrics.start_time
            await self.metrics_collector.record_session_end(
                session_id, session_duration, session_metrics.cost_usd, session_metrics.fallback_triggered
            )
            
            # セッション削除
            del self.active_sessions[session_id]
            await self.session_store.delete_session(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "summary": {
                    "duration_seconds": session_duration,
                    "message_count": session_metrics.message_count,
                    "cost_usd": session_metrics.cost_usd,
                    "fallback_triggered": session_metrics.fallback_triggered,
                    "mode": session_metrics.mode.value
                }
            }
            
        except Exception as e:
            print(f"❌ Session cleanup error: {e}")
            return {"success": False, "error": str(e)}

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """セッション状態取得"""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session_metrics = self.active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "processing_mode": session_metrics.mode.value,
            "duration_seconds": time.time() - session_metrics.start_time,
            "message_count": session_metrics.message_count,
            "cost_usd": session_metrics.cost_usd,
            "error_count": session_metrics.error_count,
            "fallback_triggered": session_metrics.fallback_triggered
        }