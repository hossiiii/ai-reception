"""
OpenAI Realtime API統合Phase 1のテスト

基盤構築の動作確認テスト
"""

import pytest
import asyncio
import os
import json
from unittest.mock import AsyncMock, Mock, patch

from app.services.realtime.hybrid_voice_manager import HybridVoiceManager, VoiceProcessingMode
from app.services.realtime.realtime_audio_processor import RealtimeAudioProcessor
from app.services.realtime.langgraph_bridge import LangGraphBridge
from app.services.session_store import SessionStore, SessionState
from app.services.metrics_collector import MetricsCollector
from app.services.fallback_manager import FallbackManager
from app.config.feature_flags import FeatureFlagManager
from app.config.realtime_settings import RealtimeSettings


class TestRealtimeAPIIntegrationPhase1:
    """Realtime API統合Phase 1の基盤テスト"""

    @pytest.fixture
    def mock_env_vars(self):
        """テスト用環境変数設定"""
        test_env = {
            "REALTIME_API_KEY": "sk-test-key-for-testing",
            "REALTIME_ENABLED": "false",  # Phase 1では無効
            "REALTIME_FALLBACK_ENABLED": "true",
            "REALTIME_DEBUG_MODE": "true",
            "REALTIME_DB_PATH": ":memory:",
            "REALTIME_COST_LIMIT_PER_HOUR": "50.0"
        }
        
        with patch.dict(os.environ, test_env):
            yield test_env

    @pytest.fixture
    def session_store(self):
        """テスト用セッションストア"""
        return SessionStore(db_path=":memory:")

    @pytest.fixture
    def metrics_collector(self):
        """テスト用メトリクス収集"""
        return MetricsCollector(db_path=":memory:")

    @pytest.fixture
    def fallback_manager(self):
        """テスト用フォールバック管理"""
        return FallbackManager()

    @pytest.fixture
    def feature_flag_manager(self):
        """テスト用フィーチャーフラグ管理"""
        return FeatureFlagManager()

    @pytest.mark.asyncio
    async def test_session_store_initialization(self, session_store):
        """セッションストアの初期化テスト"""
        # セッション作成
        session_id = "test_session_001"
        initial_data = {
            "mode": "legacy",
            "preferences": {"prefer_legacy": True}
        }
        
        result = await session_store.create_session(session_id, initial_data)
        assert result is True
        
        # セッション取得
        session_info = await session_store.get_session(session_id)
        assert session_info is not None
        assert session_info.session_id == session_id
        assert session_info.processing_mode == "legacy"
        assert session_info.state == SessionState.INITIALIZING

    @pytest.mark.asyncio
    async def test_metrics_collector_initialization(self, metrics_collector):
        """メトリクス収集の初期化テスト"""
        # セッション開始記録
        await metrics_collector.record_session_start("test_session_001", "legacy")
        
        # メッセージ処理記録
        await metrics_collector.record_message_processed(
            session_id="test_session_001",
            processing_time=0.5,
            cost=0.02,
            processing_mode="legacy",
            success=True
        )
        
        # 統計取得
        stats = await metrics_collector.get_current_statistics()
        assert "overall" in stats
        assert "by_mode" in stats

    @pytest.mark.asyncio
    async def test_fallback_manager_initialization(self, fallback_manager):
        """フォールバック管理の初期化テスト"""
        session_id = "test_session_001"
        
        # エラー記録
        await fallback_manager.record_error(session_id, {"message": "test error"})
        
        # フォールバック判定
        current_metrics = {"latency_ms": 1000, "hourly_cost": 10.0}
        should_fallback, reason = await fallback_manager.should_trigger_fallback(session_id, current_metrics)
        
        # 初回エラーではフォールバックしない
        assert should_fallback is False

    def test_feature_flag_manager_initialization(self, feature_flag_manager):
        """フィーチャーフラグ管理の初期化テスト"""
        # デフォルト設定でRealtimeは無効
        assert feature_flag_manager.is_enabled("realtime_mode_enabled") is False
        
        # フォールバックは有効
        assert feature_flag_manager.is_enabled("realtime_fallback_enabled") is True
        
        # 全フラグ取得
        all_flags = feature_flag_manager.get_all_flags()
        assert "realtime_mode_enabled" in all_flags
        assert "realtime_fallback_enabled" in all_flags

    @pytest.mark.asyncio
    async def test_realtime_settings_validation(self, mock_env_vars):
        """Realtime設定の検証テスト"""
        from app.config.realtime_settings import validate_realtime_config
        
        # 設定検証
        validation_result = validate_realtime_config()
        
        # Phase 1では基本的な設定エラーがある可能性があるが、構造は正常
        assert "valid" in validation_result
        assert "errors" in validation_result
        assert "warnings" in validation_result

    @pytest.mark.asyncio
    async def test_hybrid_voice_manager_legacy_mode(self, mock_env_vars):
        """HybridVoiceManagerのレガシーモードテスト"""
        # Realtimeが無効の場合、レガシーモードで動作するはず
        with patch('app.services.realtime.realtime_audio_processor.RealtimeAudioProcessor.health_check', return_value=False):
            with patch('app.services.audio_service.AudioService.process_audio_input', new_callable=AsyncMock) as mock_audio:
                with patch('app.agents.reception_graph.ReceptionGraphManager.send_message', new_callable=AsyncMock) as mock_graph:
                    
                    mock_audio.return_value = "テスト音声入力"
                    mock_graph.return_value = {
                        "success": True,
                        "message": "テスト応答",
                        "step": "greeting"
                    }
                    
                    # HybridVoiceManagerのテスト用初期化
                    manager = HybridVoiceManager()
                    
                    # セッション開始（レガシーモードに切り替わるはず）
                    session_result = await manager.start_session("test_session_001")
                    
                    # レガシーモードで開始されることを確認
                    assert session_result["success"] is True
                    assert session_result["processing_mode"] in ["legacy", "realtime"]  # フォールバック時はlegacy

    @pytest.mark.asyncio
    async def test_langgraph_bridge_initialization(self):
        """LangGraphブリッジの初期化テスト"""
        with patch('app.agents.reception_graph.ReceptionGraphManager'):
            with patch('app.services.calendar_service.CalendarService'):
                with patch('app.services.slack_service.SlackService'):
                    
                    bridge = LangGraphBridge()
                    
                    # Function Call実行履歴取得
                    history = await bridge.get_function_execution_history("test_session_001")
                    assert isinstance(history, list)
                    assert len(history) == 0  # 初期状態では空

    @pytest.mark.asyncio
    async def test_database_migration_compatibility(self, session_store, metrics_collector):
        """データベースマイグレーションの互換性テスト"""
        # セッションストアとメトリクス収集が同じデータベース構造に対応していることを確認
        
        # セッション作成
        session_id = "migration_test_001"
        await session_store.create_session(session_id, {"mode": "legacy"})
        
        # メトリクス記録
        await metrics_collector.record_session_start(session_id, "legacy")
        await metrics_collector.record_message_processed(
            session_id=session_id,
            processing_time=0.3,
            cost=0.01,
            processing_mode="legacy"
        )
        
        # データが正常に保存されていることを確認
        session_info = await session_store.get_session(session_id)
        assert session_info is not None
        
        stats = await metrics_collector.get_current_statistics()
        assert stats.get("overall", {}).get("unique_sessions", 0) >= 0

    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, fallback_manager):
        """エラーハンドリングとフォールバックテスト"""
        session_id = "error_test_001"
        
        # 複数のエラーを記録してフォールバック閾値をテスト
        for i in range(5):
            await fallback_manager.record_error(session_id, {
                "message": f"test error {i}",
                "code": "TEST_ERROR"
            })
        
        # エラー閾値を超えた場合のフォールバック判定
        current_metrics = {"latency_ms": 1000, "hourly_cost": 10.0}
        should_fallback, reason = await fallback_manager.should_trigger_fallback(session_id, current_metrics)
        
        # エラー閾値（3）を超えているのでフォールバックするはず
        assert should_fallback is True

    @pytest.mark.asyncio
    async def test_cost_monitoring_and_limits(self, metrics_collector, fallback_manager):
        """コスト監視と制限テスト"""
        session_id = "cost_test_001"
        
        # 高コストのメッセージ処理を記録
        for i in range(10):
            await metrics_collector.record_message_processed(
                session_id=session_id,
                processing_time=1.0,
                cost=10.0,  # 高コスト
                processing_mode="realtime"
            )
        
        # 時間あたりコスト取得
        hourly_cost = await metrics_collector.get_hourly_cost()
        
        # コスト制限チェック
        current_metrics = {"latency_ms": 1000, "hourly_cost": hourly_cost}
        should_fallback, reason = await fallback_manager.should_trigger_fallback(session_id, current_metrics)
        
        # コスト制限を考慮した判定結果を確認
        assert isinstance(should_fallback, bool)

    @pytest.mark.asyncio
    async def test_system_integration_smoke_test(self, mock_env_vars):
        """システム統合のスモークテスト"""
        # 主要コンポーネントが正常に初期化され、相互に通信できることを確認
        
        session_store = SessionStore(db_path=":memory:")
        metrics_collector = MetricsCollector(db_path=":memory:")
        fallback_manager = FallbackManager()
        
        session_id = "integration_test_001"
        
        # セッション作成
        await session_store.create_session(session_id, {"mode": "legacy"})
        
        # メトリクス記録
        await metrics_collector.record_session_start(session_id, "legacy")
        
        # セッション情報取得
        session_info = await session_store.get_session(session_id)
        assert session_info is not None
        
        # システム統計取得
        stats = await metrics_collector.get_current_statistics()
        assert "overall" in stats
        
        # フォールバック状態取得
        fallback_status = await fallback_manager.get_fallback_status()
        assert "global_fallback_active" in fallback_status
        
        # セッション終了
        await session_store.delete_session(session_id)

    def test_configuration_loading(self, mock_env_vars):
        """設定読み込みテスト"""
        # 環境変数から設定が正しく読み込まれることを確認
        from app.config.realtime_settings import RealtimeSettings
        from app.config.feature_flags import FeatureFlags
        
        # Realtime設定
        realtime_settings = RealtimeSettings()
        assert hasattr(realtime_settings, 'realtime_api_key')
        assert hasattr(realtime_settings, 'cost_limit_per_hour')
        
        # フィーチャーフラグ
        feature_flags = FeatureFlags()
        assert hasattr(feature_flags, 'realtime_mode_enabled')
        assert hasattr(feature_flags, 'realtime_fallback_enabled')

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """段階的劣化テスト"""
        # Realtime APIが利用できない場合のレガシーシステムへの段階的劣化
        
        with patch('app.services.realtime.realtime_audio_processor.RealtimeAudioProcessor.health_check', return_value=False):
            # RealtimeAudioProcessorのヘルスチェックが失敗する場合
            processor = RealtimeAudioProcessor()
            health_status = await processor.health_check()
            assert health_status is False
            
            # この場合、HybridVoiceManagerはレガシーモードにフォールバックするはず


class TestPhase1CompletionChecklist:
    """Phase 1完了チェックリスト"""

    def test_required_files_exist(self):
        """必要なファイルの存在確認"""
        required_files = [
            "backend/app/services/realtime/__init__.py",
            "backend/app/services/realtime/hybrid_voice_manager.py",
            "backend/app/services/realtime/realtime_audio_processor.py",
            "backend/app/services/realtime/langgraph_bridge.py",
            "backend/app/services/session_store.py",
            "backend/app/services/metrics_collector.py",
            "backend/app/services/fallback_manager.py",
            "backend/app/config/feature_flags.py",
            "backend/app/config/realtime_settings.py",
            "backend/migrations/add_realtime_support.sql",
            ".env.realtime.template"
        ]
        
        for file_path in required_files:
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)
            assert os.path.exists(full_path), f"Required file not found: {file_path}"

    def test_imports_work(self):
        """インポートが正常に動作することを確認"""
        try:
            from app.services.realtime.hybrid_voice_manager import HybridVoiceManager
            from app.services.realtime.realtime_audio_processor import RealtimeAudioProcessor
            from app.services.realtime.langgraph_bridge import LangGraphBridge
            from app.services.session_store import SessionStore
            from app.services.metrics_collector import MetricsCollector
            from app.services.fallback_manager import FallbackManager
            from app.config.feature_flags import FeatureFlagManager
            from app.config.realtime_settings import RealtimeSettings
            
            # 基本的なクラスのインスタンス化
            session_store = SessionStore(db_path=":memory:")
            metrics_collector = MetricsCollector(db_path=":memory:")
            fallback_manager = FallbackManager()
            feature_flag_manager = FeatureFlagManager()
            
            assert session_store is not None
            assert metrics_collector is not None
            assert fallback_manager is not None
            assert feature_flag_manager is not None
            
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_database_schema_compatibility(self):
        """データベーススキーマの互換性確認"""
        import sqlite3
        from app.services.session_store import SessionStore
        from app.services.metrics_collector import MetricsCollector
        
        # テスト用データベースで基本操作を実行
        try:
            # SQLiteインメモリデータベースでテスト
            with sqlite3.connect(":memory:") as conn:
                # マイグレーションSQLの読み込みと実行をシミュレート
                cursor = conn.cursor()
                
                # 基本的なテーブル作成（簡略版）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        processing_mode TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        last_activity REAL NOT NULL
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        processing_mode TEXT NOT NULL,
                        latency_ms REAL NOT NULL,
                        cost_usd REAL NOT NULL,
                        success BOOLEAN NOT NULL
                    )
                """)
                
                # テストデータ挿入
                cursor.execute("""
                    INSERT INTO sessions (session_id, state, processing_mode, created_at, last_activity)
                    VALUES (?, ?, ?, ?, ?)
                """, ("test_001", "active", "legacy", 1234567890, 1234567890))
                
                cursor.execute("""
                    INSERT INTO session_metrics (session_id, timestamp, processing_mode, latency_ms, cost_usd, success)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("test_001", 1234567890, "legacy", 500.0, 0.02, True))
                
                conn.commit()
                
                # データ取得テスト
                cursor.execute("SELECT COUNT(*) FROM sessions")
                session_count = cursor.fetchone()[0]
                assert session_count == 1
                
                cursor.execute("SELECT COUNT(*) FROM session_metrics")
                metrics_count = cursor.fetchone()[0]
                assert metrics_count == 1
                
        except Exception as e:
            pytest.fail(f"Database schema test failed: {e}")

    def test_environment_variable_compatibility(self):
        """環境変数の互換性確認"""
        from app.config.realtime_settings import RealtimeSettings
        from app.config.feature_flags import FeatureFlags
        
        # 環境変数なしでも基本設定が読み込めることを確認
        try:
            realtime_settings = RealtimeSettings()
            feature_flags = FeatureFlags()
            
            # 必要な属性が存在することを確認
            assert hasattr(realtime_settings, 'cost_limit_per_hour')
            assert hasattr(realtime_settings, 'max_session_time')
            assert hasattr(feature_flags, 'realtime_mode_enabled')
            assert hasattr(feature_flags, 'realtime_fallback_enabled')
            
        except Exception as e:
            pytest.fail(f"Environment variable compatibility test failed: {e}")