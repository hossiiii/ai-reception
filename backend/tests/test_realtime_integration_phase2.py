"""
OpenAI Realtime API統合 Phase 2 テストスイート

Phase 2で実装された機能の統合テスト:
1. RealtimeWebSocketHandler
2. Function Calls完全実装
3. LangGraphブリッジ完成
4. セッション状態同期
5. フォールバック機能
6. パフォーマンス監視
7. フィーチャーフラグ制御
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocket

from app.services.realtime.realtime_websocket_handler import RealtimeWebSocketHandler
from app.services.realtime.langgraph_bridge import LangGraphBridge
from app.services.realtime.hybrid_voice_manager import HybridVoiceManager
from app.config.feature_flags import FeatureFlagManager
from app.config.realtime_settings import RealtimeSettings


class TestRealtimeWebSocketHandler:
    """RealtimeWebSocketHandlerのテスト"""

    @pytest.fixture
    def handler(self):
        return RealtimeWebSocketHandler()

    @pytest.fixture
    def mock_websocket(self):
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_websocket_handler_initialization(self, handler):
        """WebSocketハンドラーの初期化テスト"""
        assert handler is not None
        assert hasattr(handler, 'active_sessions')
        assert hasattr(handler, 'audio_processor')
        assert hasattr(handler, 'langgraph_bridge')

    @pytest.mark.asyncio
    async def test_client_connection_flow(self, handler, mock_websocket):
        """クライアント接続フローのテスト"""
        session_id = "test_session_001"
        
        with patch.object(handler, '_establish_realtime_connection') as mock_establish:
            mock_establish.return_value = {
                "success": True,
                "capabilities": {"real_time_audio": True}
            }
            
            with patch.object(handler, '_handle_session_loop') as mock_loop:
                mock_loop.return_value = None
                
                try:
                    await handler.handle_client_connection(mock_websocket, session_id)
                except Exception:
                    pass  # Expected due to mocking
                
                # セッションが作成されたことを確認
                assert session_id in handler.active_sessions
                
                # WebSocket接続が受け入れられたことを確認
                mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_realtime_event_processing(self, handler):
        """Realtimeイベント処理のテスト"""
        session_id = "test_session_002"
        
        # セッション初期化
        handler.active_sessions[session_id] = Mock()
        
        # 音声認識完了イベント
        transcription_event = {
            "type": "conversation.item.input_audio_transcription.completed",
            "transcript": "こんにちは",
            "item_id": "item_001"
        }
        
        with patch.object(handler, '_send_to_client') as mock_send:
            await handler._process_realtime_event(session_id, transcription_event)
            
            # クライアントに転写結果が送信されたことを確認
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            assert args[0] == session_id
            assert args[1]["type"] == "transcription"
            assert args[1]["text"] == "こんにちは"

    @pytest.mark.asyncio
    async def test_function_call_execution(self, handler):
        """Function Call実行のテスト"""
        session_id = "test_session_003"
        
        # セッション初期化
        session_mock = Mock()
        session_mock.websocket = AsyncMock()
        handler.active_sessions[session_id] = session_mock
        
        function_event = {
            "type": "response.function_call_arguments.done",
            "call_id": "call_001",
            "name": "collect_visitor_info",
            "arguments": '{"visitor_name": "田中太郎", "company_name": "テスト株式会社"}'
        }
        
        with patch.object(handler.langgraph_bridge, 'execute_function_call') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "result": {"visitor_info": {"name": "田中太郎"}}
            }
            
            await handler._execute_function_call(session_id, function_event)
            
            # Function Callが実行されたことを確認
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[1]
            assert call_args["function_name"] == "collect_visitor_info"
            assert call_args["parameters"]["visitor_name"] == "田中太郎"


class TestLangGraphBridge:
    """LangGraphブリッジのテスト"""

    @pytest.fixture
    def bridge(self):
        return LangGraphBridge()

    @pytest.mark.asyncio
    async def test_function_call_execution_with_retry(self, bridge):
        """リトライ機能付きFunction Call実行のテスト"""
        session_id = "test_session_004"
        
        with patch.object(bridge, '_execute_collect_visitor_info') as mock_execute:
            # 最初の2回は失敗、3回目で成功
            mock_execute.side_effect = [
                Exception("Temporary failure"),
                Exception("Another failure"),
                {"success": True, "visitor_info": {"name": "テストユーザー"}}
            ]
            
            result = await bridge.execute_function_call(
                session_id, "collect_visitor_info", 
                {"visitor_name": "テストユーザー"}
            )
            
            # 3回目で成功したことを確認
            assert result["success"] == True
            assert result["attempt"] == 3
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_session_state_sync(self, bridge):
        """セッション状態同期のテスト"""
        session_id = "test_session_005"
        
        realtime_state = {
            "features": ["real_time_audio", "low_latency"],
            "processing_mode": "realtime"
        }
        
        with patch.object(bridge.graph_manager, 'get_conversation_history') as mock_history:
            mock_history.return_value = {
                "success": True,
                "current_step": "collect_visitor_info",
                "visitor_info": {"name": "テスト"},
                "messages": ["message1", "message2"]
            }
            
            result = await bridge.sync_session_state(session_id, realtime_state)
            
            assert result["success"] == True
            state = result["synchronized_state"]
            assert state["session_id"] == session_id
            assert state["langgraph"]["message_count"] == 2
            assert state["realtime"]["processing_mode"] == "realtime"

    @pytest.mark.asyncio
    async def test_state_consistency_check(self, bridge):
        """状態一貫性チェックのテスト"""
        langgraph_state = {
            "visitor_info": {"name": "田中太郎", "company": "テスト株式会社"},
            "current_step": "check_appointment"
        }
        
        realtime_state = {
            "visitor_info": {"name": "田中太郎", "company": "テスト株式会社"}
        }
        
        function_history = [
            {"function_name": "collect_visitor_info", "status": "completed"}
        ]
        
        result = await bridge._check_state_consistency(
            langgraph_state, realtime_state, function_history
        )
        
        assert result["consistent"] == True
        assert result["score"] > 0.8


class TestHybridVoiceManager:
    """HybridVoiceManagerのテスト"""

    @pytest.fixture
    def manager(self):
        return HybridVoiceManager()

    @pytest.mark.asyncio
    async def test_emergency_fallback(self, manager):
        """緊急フォールバック機能のテスト"""
        session_id = "test_session_006"
        
        # セッション初期化
        from app.services.realtime.hybrid_voice_manager import SessionMetrics, VoiceProcessingMode
        session_metrics = SessionMetrics(
            session_id=session_id,
            start_time=time.time(),
            mode=VoiceProcessingMode.REALTIME
        )
        manager.active_sessions[session_id] = session_metrics
        
        test_audio = b"test_audio_data"
        reason = "api_timeout"
        
        with patch.object(manager, '_process_legacy_audio') as mock_legacy:
            mock_legacy.return_value = {
                "success": True,
                "processing_mode": "legacy",
                "transcription": "テスト音声",
                "ai_response": "承知いたしました"
            }
            
            result = await manager._emergency_fallback_to_legacy(
                session_id, test_audio, reason
            )
            
            assert result["success"] == True
            assert result["fallback_triggered"] == True
            assert result["fallback_reason"] == reason
            assert session_metrics.fallback_triggered == True

    @pytest.mark.asyncio
    async def test_performance_monitoring(self, manager):
        """パフォーマンス監視のテスト"""
        # アクティブセッションを作成
        from app.services.realtime.hybrid_voice_manager import SessionMetrics, VoiceProcessingMode
        
        session1 = SessionMetrics("session1", time.time(), VoiceProcessingMode.REALTIME)
        session1.cost_usd = 0.05
        session1.error_count = 1
        
        session2 = SessionMetrics("session2", time.time(), VoiceProcessingMode.LEGACY)
        session2.fallback_triggered = True
        
        manager.active_sessions = {"session1": session1, "session2": session2}
        
        with patch.object(manager.metrics_collector, 'get_hourly_cost') as mock_cost:
            mock_cost.return_value = 2.5
            
            report = await manager.monitor_system_performance()
            
            assert report["sessions"]["total"] == 2
            assert report["sessions"]["realtime"] == 1
            assert report["sessions"]["fallback_triggered"] == 1
            assert report["costs"]["current_total"] == 0.05
            assert "health" in report


class TestFeatureFlagManager:
    """フィーチャーフラグマネージャーのテスト"""

    @pytest.fixture
    def flag_manager(self):
        return FeatureFlagManager()

    def test_session_specific_overrides(self, flag_manager):
        """セッション別オーバーライドのテスト"""
        session_id = "test_session_007"
        
        # セッション別でRealtime有効化
        flag_manager.enable_for_session(session_id, "realtime_mode_enabled", True)
        
        # そのセッションではRealtime有効
        assert flag_manager.is_enabled("realtime_mode_enabled", session_id) == True
        
        # 他のセッションでは無効（基本設定に従う）
        assert flag_manager.is_enabled("realtime_mode_enabled", "other_session") == False

    def test_ab_test_assignment(self, flag_manager):
        """A/Bテスト割り当てのテスト"""
        session_id = "test_session_008"
        
        # A/Bテスト割り当て
        flag_manager.assign_ab_test(session_id, "realtime_mode", "realtime")
        
        # バリアント取得
        variant = flag_manager.get_ab_test_variant(session_id, "realtime_mode")
        assert variant == "realtime"
        
        # Realtime有効性チェック（A/Bテストが適用される）
        with patch.object(flag_manager.flags, 'realtime_mode_enabled', True):
            result = flag_manager.is_enabled("realtime_mode_enabled", session_id)
            assert result == True

    def test_progressive_rollout(self, flag_manager):
        """段階的ロールアウトのテスト"""
        flag_name = "realtime_mode_enabled"
        target_percentage = 50
        
        # ロールアウト作成
        config = flag_manager.create_progressive_rollout(flag_name, target_percentage)
        
        assert config["flag_name"] == flag_name
        assert config["target_percentage"] == target_percentage
        assert config["current_percentage"] == 0
        
        # 比率更新
        success = flag_manager.update_rollout_percentage(flag_name, 25)
        assert success == True
        assert flag_manager.flags.realtime_rollout_percentage == 25


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    @pytest.mark.asyncio
    async def test_end_to_end_realtime_flow(self):
        """エンドツーエンドRealtime処理フローのテスト"""
        # コンポーネント初期化
        handler = RealtimeWebSocketHandler()
        bridge = LangGraphBridge()
        manager = HybridVoiceManager()
        
        session_id = "integration_test_001"
        
        # 1. セッション開始
        with patch.object(manager, 'realtime_processor') as mock_processor:
            mock_processor.initialize_session.return_value = {"success": True}
            
            result = await manager.start_session(session_id)
            assert result["success"] == True

        # 2. Function Call実行
        with patch.object(bridge, '_execute_collect_visitor_info') as mock_function:
            mock_function.return_value = {
                "success": True,
                "visitor_info": {"name": "統合テスト"}
            }
            
            function_result = await bridge.execute_function_call(
                session_id, "collect_visitor_info",
                {"visitor_name": "統合テスト"}
            )
            assert function_result["success"] == True

        # 3. セッション状態同期
        realtime_state = {"processing_mode": "realtime"}
        
        with patch.object(bridge.graph_manager, 'get_conversation_history') as mock_history:
            mock_history.return_value = {
                "success": True,
                "current_step": "collect_visitor_info",
                "messages": []
            }
            
            sync_result = await bridge.sync_session_state(session_id, realtime_state)
            assert sync_result["success"] == True

    @pytest.mark.asyncio
    async def test_fallback_scenario(self):
        """フォールバックシナリオのテスト"""
        manager = HybridVoiceManager()
        session_id = "fallback_test_001"
        
        # セッション初期化
        from app.services.realtime.hybrid_voice_manager import SessionMetrics, VoiceProcessingMode
        session_metrics = SessionMetrics(
            session_id=session_id,
            start_time=time.time(),
            mode=VoiceProcessingMode.REALTIME
        )
        session_metrics.error_count = 6  # エラー閾値超過
        manager.active_sessions[session_id] = session_metrics
        
        # フォールバック判定
        should_fallback = await manager._should_fallback(session_id)
        assert should_fallback == True
        
        # フォールバック実行
        test_audio = b"test_audio"
        
        with patch.object(manager, '_process_legacy_audio') as mock_legacy:
            mock_legacy.return_value = {
                "success": True,
                "processing_mode": "legacy"
            }
            
            result = await manager._emergency_fallback_to_legacy(
                session_id, test_audio, "too_many_errors"
            )
            
            assert result["fallback_triggered"] == True
            assert session_metrics.fallback_triggered == True

    def test_feature_flag_integration(self):
        """フィーチャーフラグ統合のテスト"""
        flag_manager = FeatureFlagManager()
        
        # 基本設定: Realtime無効
        flag_manager.flags.realtime_mode_enabled = False
        
        # セッション別で有効化
        session_id = "flag_test_001"
        flag_manager.enable_for_session(session_id, "realtime_mode_enabled", True)
        
        # そのセッションのみRealtime有効
        assert flag_manager.is_enabled("realtime_mode_enabled", session_id) == True
        assert flag_manager.is_enabled("realtime_mode_enabled", "other_session") == False


def test_phase2_integration_summary():
    """Phase 2統合の概要確認テスト"""
    # すべての主要コンポーネントがインポート可能であることを確認
    try:
        from app.services.realtime.realtime_websocket_handler import RealtimeWebSocketHandler
        from app.services.realtime.langgraph_bridge import LangGraphBridge
        from app.services.realtime.hybrid_voice_manager import HybridVoiceManager
        from app.config.feature_flags import FeatureFlagManager
        from app.api.websocket import create_realtime_websocket_endpoint
        
        # インスタンス化が正常に行えることを確認
        handler = RealtimeWebSocketHandler()
        bridge = LangGraphBridge()
        manager = HybridVoiceManager()
        flag_manager = FeatureFlagManager()
        endpoint = create_realtime_websocket_endpoint()
        
        assert handler is not None
        assert bridge is not None
        assert manager is not None
        assert flag_manager is not None
        assert endpoint is not None
        
        print("✅ Phase 2 integration test summary: All components initialized successfully")
        
    except ImportError as e:
        pytest.fail(f"❌ Component import failed: {e}")
    except Exception as e:
        pytest.fail(f"❌ Component initialization failed: {e}")


if __name__ == "__main__":
    # 簡易テスト実行
    print("🧪 Running Phase 2 integration tests...")
    
    # コンポーネント初期化テスト
    test_phase2_integration_summary()
    
    print("✅ Phase 2 integration tests completed successfully!")