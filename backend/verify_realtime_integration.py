#!/usr/bin/env python3
"""
OpenAI Realtime API統合Phase 1の動作確認スクリプト

基盤構築の完了確認とエラーハンドリング検証
"""

import asyncio
import os
import sys
import traceback
from typing import Dict, Any, List

# プロジェクトのルートパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_section(title: str):
    """セクションタイトルを表示"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def print_result(test_name: str, success: bool, message: str = ""):
    """テスト結果を表示"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

class RealtimeIntegrationVerifier:
    """Realtime API統合の検証クラス"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.session_id = "verification_test_001"
    
    def record_test(self, test_name: str, success: bool, message: str = ""):
        """テスト結果を記録"""
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "message": message
        })
        print_result(test_name, success, message)
    
    async def verify_imports(self):
        """インポートの確認"""
        print_section("1. インポート確認")
        
        try:
            from app.services.realtime.hybrid_voice_manager import HybridVoiceManager
            self.record_test("HybridVoiceManager インポート", True)
        except ImportError as e:
            self.record_test("HybridVoiceManager インポート", False, str(e))
        
        try:
            from app.services.realtime.realtime_audio_processor import RealtimeAudioProcessor
            self.record_test("RealtimeAudioProcessor インポート", True)
        except ImportError as e:
            self.record_test("RealtimeAudioProcessor インポート", False, str(e))
        
        try:
            from app.services.realtime.langgraph_bridge import LangGraphBridge
            self.record_test("LangGraphBridge インポート", True)
        except ImportError as e:
            self.record_test("LangGraphBridge インポート", False, str(e))
        
        try:
            from app.services.session_store import SessionStore
            self.record_test("SessionStore インポート", True)
        except ImportError as e:
            self.record_test("SessionStore インポート", False, str(e))
        
        try:
            from app.services.metrics_collector import MetricsCollector
            self.record_test("MetricsCollector インポート", True)
        except ImportError as e:
            self.record_test("MetricsCollector インポート", False, str(e))
        
        try:
            from app.services.fallback_manager import FallbackManager
            self.record_test("FallbackManager インポート", True)
        except ImportError as e:
            self.record_test("FallbackManager インポート", False, str(e))
        
        try:
            from app.config.feature_flags import FeatureFlagManager
            self.record_test("FeatureFlagManager インポート", True)
        except ImportError as e:
            self.record_test("FeatureFlagManager インポート", False, str(e))
        
        try:
            from app.config.realtime_settings import RealtimeSettings
            self.record_test("RealtimeSettings インポート", True)
        except ImportError as e:
            self.record_test("RealtimeSettings インポート", False, str(e))
    
    async def verify_configuration(self):
        """設定の確認"""
        print_section("2. 設定確認")
        
        try:
            from app.config.realtime_settings import RealtimeSettings, validate_realtime_config
            
            # 設定読み込み
            settings = RealtimeSettings()
            self.record_test("Realtime設定読み込み", True)
            
            # 設定検証
            validation = validate_realtime_config()
            if validation["valid"]:
                self.record_test("Realtime設定検証", True)
            else:
                self.record_test("Realtime設定検証", False, f"エラー: {validation['errors']}")
            
            # 警告がある場合は表示
            if validation["warnings"]:
                print(f"    ⚠️ 警告: {validation['warnings']}")
                
        except Exception as e:
            self.record_test("Realtime設定確認", False, str(e))
        
        try:
            from app.config.feature_flags import FeatureFlagManager
            
            flag_manager = FeatureFlagManager()
            flags = flag_manager.get_all_flags()
            
            self.record_test("フィーチャーフラグ読み込み", True)
            
            # デフォルト状態の確認
            realtime_enabled = flag_manager.is_enabled("realtime_mode_enabled")
            fallback_enabled = flag_manager.is_enabled("realtime_fallback_enabled")
            
            if not realtime_enabled and fallback_enabled:
                self.record_test("Phase 1デフォルト設定", True, "Realtime無効、フォールバック有効")
            else:
                self.record_test("Phase 1デフォルト設定", False, f"Realtime: {realtime_enabled}, Fallback: {fallback_enabled}")
                
        except Exception as e:
            self.record_test("フィーチャーフラグ確認", False, str(e))
    
    async def verify_database_operations(self):
        """データベース操作の確認"""
        print_section("3. データベース操作確認")
        
        try:
            from app.services.session_store import SessionStore
            
            session_store = SessionStore(db_path=":memory:")
            
            # セッション作成
            result = await session_store.create_session(self.session_id, {
                "mode": "legacy",
                "preferences": {"test": True}
            })
            self.record_test("セッション作成", result)
            
            # セッション取得
            session_info = await session_store.get_session(self.session_id)
            if session_info and session_info.session_id == self.session_id:
                self.record_test("セッション取得", True)
            else:
                self.record_test("セッション取得", False, "セッション情報が見つからない")
            
            # セッション更新
            update_result = await session_store.update_session(self.session_id, {
                "conversation_step": "greeting"
            })
            self.record_test("セッション更新", update_result)
            
            # セッション削除
            delete_result = await session_store.delete_session(self.session_id)
            self.record_test("セッション削除", delete_result)
            
        except Exception as e:
            self.record_test("SessionStore動作確認", False, str(e))
        
        try:
            from app.services.metrics_collector import MetricsCollector
            
            metrics = MetricsCollector(db_path=":memory:")
            
            # セッション開始記録
            await metrics.record_session_start(self.session_id, "legacy")
            self.record_test("メトリクス - セッション開始記録", True)
            
            # メッセージ処理記録
            await metrics.record_message_processed(
                session_id=self.session_id,
                processing_time=0.5,
                cost=0.02,
                processing_mode="legacy",
                success=True
            )
            self.record_test("メトリクス - メッセージ処理記録", True)
            
            # 統計取得
            stats = await metrics.get_current_statistics()
            if "overall" in stats and "by_mode" in stats:
                self.record_test("メトリクス - 統計取得", True)
            else:
                self.record_test("メトリクス - 統計取得", False, "統計形式が不正")
                
        except Exception as e:
            self.record_test("MetricsCollector動作確認", False, str(e))
    
    async def verify_fallback_manager(self):
        """フォールバック管理の確認"""
        print_section("4. フォールバック管理確認")
        
        try:
            from app.services.fallback_manager import FallbackManager, FallbackReason
            
            fallback_manager = FallbackManager()
            
            # エラー記録
            await fallback_manager.record_error(self.session_id, {
                "message": "テストエラー",
                "code": "TEST_ERROR"
            })
            self.record_test("フォールバック - エラー記録", True)
            
            # フォールバック判定
            metrics = {"latency_ms": 1000, "hourly_cost": 10.0}
            should_fallback, reason = await fallback_manager.should_trigger_fallback(self.session_id, metrics)
            self.record_test("フォールバック - 判定実行", True, f"結果: {should_fallback}")
            
            # 状態取得
            status = await fallback_manager.get_fallback_status()
            if "global_fallback_active" in status:
                self.record_test("フォールバック - 状態取得", True)
            else:
                self.record_test("フォールバック - 状態取得", False, "状態形式が不正")
                
        except Exception as e:
            self.record_test("FallbackManager動作確認", False, str(e))
    
    async def verify_hybrid_voice_manager(self):
        """ハイブリッド音声管理の確認"""
        print_section("5. ハイブリッド音声管理確認")
        
        try:
            # モックを使用してRealtime APIへの実際の接続を回避
            from unittest.mock import AsyncMock, patch
            
            # 依存関係をモック化
            with patch('app.services.audio_service.AudioService') as mock_audio:
                with patch('app.agents.reception_graph.ReceptionGraphManager') as mock_graph:
                    with patch('app.services.realtime.realtime_audio_processor.RealtimeAudioProcessor.health_check', return_value=False):
                        
                        # モックの設定
                        mock_audio_instance = AsyncMock()
                        mock_audio.return_value = mock_audio_instance
                        
                        mock_graph_instance = AsyncMock()
                        mock_graph.return_value = mock_graph_instance
                        
                        from app.services.realtime.hybrid_voice_manager import HybridVoiceManager
                        
                        # HybridVoiceManager初期化
                        manager = HybridVoiceManager()
                        self.record_test("HybridVoiceManager初期化", True)
                        
                        # セッション開始（Realtimeが無効なのでレガシーモードで開始されるはず）
                        session_result = await manager.start_session(self.session_id)
                        
                        if session_result["success"]:
                            self.record_test("セッション開始", True, f"モード: {session_result['processing_mode']}")
                        else:
                            self.record_test("セッション開始", False, session_result.get("error", "不明なエラー"))
                        
                        # セッション状態取得
                        status = await manager.get_session_status(self.session_id)
                        if status["success"]:
                            self.record_test("セッション状態取得", True)
                        else:
                            self.record_test("セッション状態取得", False, status.get("error", "不明なエラー"))
                        
                        # セッション終了
                        end_result = await manager.end_session(self.session_id)
                        if end_result["success"]:
                            self.record_test("セッション終了", True)
                        else:
                            self.record_test("セッション終了", False, end_result.get("error", "不明なエラー"))
                        
        except Exception as e:
            self.record_test("HybridVoiceManager動作確認", False, str(e))
    
    async def verify_langgraph_bridge(self):
        """LangGraphブリッジの確認"""
        print_section("6. LangGraphブリッジ確認")
        
        try:
            from unittest.mock import AsyncMock, patch
            
            # 依存関係をモック化
            with patch('app.agents.reception_graph.ReceptionGraphManager') as mock_graph:
                with patch('app.services.calendar_service.CalendarService') as mock_calendar:
                    with patch('app.services.slack_service.SlackService') as mock_slack:
                        
                        # モックの設定
                        mock_graph_instance = AsyncMock()
                        mock_graph.return_value = mock_graph_instance
                        
                        mock_calendar_instance = AsyncMock()
                        mock_calendar.return_value = mock_calendar_instance
                        
                        mock_slack_instance = AsyncMock()
                        mock_slack.return_value = mock_slack_instance
                        
                        from app.services.realtime.langgraph_bridge import LangGraphBridge
                        
                        # LangGraphBridge初期化
                        bridge = LangGraphBridge()
                        self.record_test("LangGraphBridge初期化", True)
                        
                        # Function Call実行履歴取得
                        history = await bridge.get_function_execution_history(self.session_id)
                        if isinstance(history, list):
                            self.record_test("実行履歴取得", True, f"履歴数: {len(history)}")
                        else:
                            self.record_test("実行履歴取得", False, "履歴形式が不正")
                        
                        # セッションクリーンアップ
                        await bridge.cleanup_session(self.session_id)
                        self.record_test("セッションクリーンアップ", True)
                        
        except Exception as e:
            self.record_test("LangGraphBridge動作確認", False, str(e))
    
    async def verify_websocket_integration(self):
        """WebSocket統合の確認"""
        print_section("7. WebSocket統合確認")
        
        try:
            from app.api.websocket import VoiceWebSocketManager
            
            # WebSocketマネージャー初期化
            ws_manager = VoiceWebSocketManager()
            self.record_test("VoiceWebSocketManager初期化", True)
            
            # アクティブコネクション確認
            if hasattr(ws_manager, 'active_connections'):
                self.record_test("アクティブコネクション管理", True)
            else:
                self.record_test("アクティブコネクション管理", False, "active_connections属性がない")
            
            # HybridVoiceManager統合確認
            if hasattr(ws_manager, 'hybrid_manager'):
                self.record_test("HybridVoiceManager統合", True)
            else:
                self.record_test("HybridVoiceManager統合", False, "hybrid_manager属性がない")
                
        except Exception as e:
            self.record_test("WebSocket統合確認", False, str(e))
    
    async def verify_file_structure(self):
        """ファイル構造の確認"""
        print_section("8. ファイル構造確認")
        
        required_files = [
            "app/services/realtime/__init__.py",
            "app/services/realtime/hybrid_voice_manager.py",
            "app/services/realtime/realtime_audio_processor.py",
            "app/services/realtime/langgraph_bridge.py",
            "app/services/session_store.py",
            "app/services/metrics_collector.py",
            "app/services/fallback_manager.py",
            "app/config/__init__.py",
            "app/config/feature_flags.py",
            "app/config/realtime_settings.py",
            "migrations/add_realtime_support.sql",
            "../.env.realtime.template"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            if os.path.exists(full_path):
                self.record_test(f"ファイル存在: {file_path}", True)
            else:
                self.record_test(f"ファイル存在: {file_path}", False, "ファイルが見つからない")
    
    def print_summary(self):
        """検証結果のサマリーを表示"""
        print_section("検証結果サマリー")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"総テスト数: {total_tests}")
        print(f"成功: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"成功率: {(passed_tests / total_tests * 100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ 失敗したテスト:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['message']}")
        
        print(f"\n{'='*50}")
        if failed_tests == 0:
            print("🎉 Phase 1基盤構築が完了しました！")
        else:
            print("⚠️ いくつかの問題が見つかりました。上記の失敗項目を確認してください。")
        print(f"{'='*50}")


async def main():
    """メイン実行関数"""
    print("OpenAI Realtime API統合Phase 1 動作確認")
    print("=" * 50)
    
    verifier = RealtimeIntegrationVerifier()
    
    try:
        # 各検証を順次実行
        await verifier.verify_imports()
        await verifier.verify_configuration()
        await verifier.verify_database_operations()
        await verifier.verify_fallback_manager()
        await verifier.verify_hybrid_voice_manager()
        await verifier.verify_langgraph_bridge()
        await verifier.verify_websocket_integration()
        await verifier.verify_file_structure()
        
    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        traceback.print_exc()
    
    finally:
        # 結果サマリー表示
        verifier.print_summary()


if __name__ == "__main__":
    asyncio.run(main())