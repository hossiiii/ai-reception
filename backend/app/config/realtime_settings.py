"""
OpenAI Realtime API専用設定管理

このモジュールは以下の設定を管理:
1. Realtime API接続設定
2. コスト制限とレート制限
3. セッション管理設定
4. パフォーマンス調整
"""

from pydantic_settings import BaseSettings
from typing import Optional


class RealtimeSettings(BaseSettings):
    """OpenAI Realtime API設定"""
    
    # Realtime API認証
    realtime_api_key: str = "sk-test-key-placeholder"
    realtime_api_url: str = "wss://api.openai.com/v1/realtime"
    
    # セッション管理
    max_session_time: int = 600  # 最大セッション時間（秒）
    session_cleanup_interval: int = 300  # セッションクリーンアップ間隔（秒）
    max_concurrent_sessions: int = 10  # 最大同時セッション数
    
    # コスト管理
    cost_limit_per_hour: float = 50.0  # 1時間あたりコスト制限（USD）
    cost_limit_per_session: float = 5.0  # セッションあたりコスト制限（USD）
    cost_alert_threshold: float = 0.8  # アラート閾値（制限の80%）
    
    # パフォーマンス設定
    connection_timeout: int = 10  # 接続タイムアウト（秒）
    response_timeout: int = 15  # レスポンスタイムアウト（秒）
    max_audio_chunk_size: int = 1024 * 64  # 最大音声チャンクサイズ（バイト）
    
    # 音声設定
    input_audio_format: str = "pcm16"
    output_audio_format: str = "pcm16"
    voice_model: str = "alloy"
    turn_detection_threshold: float = 0.5
    silence_duration_ms: int = 500
    
    # Function Calls設定
    enable_function_calls: bool = True
    max_function_calls_per_turn: int = 3
    function_call_timeout: int = 30  # Function Call実行タイムアウト（秒）
    
    # ログ・監視設定
    enable_detailed_logging: bool = True
    log_audio_data: bool = False  # セキュリティ上の理由でデフォルトfalse
    enable_metrics_collection: bool = True
    metrics_collection_interval: int = 60  # メトリクス収集間隔（秒）
    
    # フォールバック設定
    enable_fallback: bool = True
    fallback_error_threshold: int = 3  # エラー回数の閾値
    fallback_latency_threshold: float = 5.0  # レイテンシ閾値（秒）
    
    class Config:
        env_file = ".env.realtime"  # 専用の設定ファイルを使用
        env_file_encoding = "utf-8"
        env_prefix = "REALTIME_"
        extra = "ignore"  # 余分なフィールドを無視


# グローバル設定インスタンス
realtime_settings = RealtimeSettings()


def get_realtime_settings() -> RealtimeSettings:
    """Realtime設定取得"""
    return realtime_settings


def validate_realtime_config() -> dict:
    """Realtime設定の検証"""
    settings = get_realtime_settings()
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # API Key検証
    if not settings.realtime_api_key or not settings.realtime_api_key.startswith('sk-'):
        validation_results["valid"] = False
        validation_results["errors"].append("Invalid or missing REALTIME_API_KEY")
    
    # コスト制限検証
    if settings.cost_limit_per_hour <= 0:
        validation_results["valid"] = False
        validation_results["errors"].append("REALTIME_COST_LIMIT_PER_HOUR must be positive")
    
    if settings.cost_limit_per_session > settings.cost_limit_per_hour:
        validation_results["warnings"].append(
            "Session cost limit exceeds hourly limit"
        )
    
    # セッション設定検証
    if settings.max_session_time <= 0:
        validation_results["valid"] = False
        validation_results["errors"].append("REALTIME_MAX_SESSION_TIME must be positive")
    
    if settings.max_concurrent_sessions <= 0:
        validation_results["valid"] = False
        validation_results["errors"].append("REALTIME_MAX_CONCURRENT_SESSIONS must be positive")
    
    # タイムアウト設定検証
    if settings.connection_timeout <= 0:
        validation_results["valid"] = False
        validation_results["errors"].append("REALTIME_CONNECTION_TIMEOUT must be positive")
    
    if settings.response_timeout <= settings.connection_timeout:
        validation_results["warnings"].append(
            "Response timeout should be greater than connection timeout"
        )
    
    return validation_results