-- OpenAI Realtime API統合のためのデータベース拡張
-- 実行日: $(date)

-- セッション管理テーブルの拡張
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'initializing',
    processing_mode TEXT NOT NULL DEFAULT 'legacy',
    created_at REAL NOT NULL,
    last_activity REAL NOT NULL,
    visitor_info TEXT,
    conversation_step TEXT,
    metadata TEXT,
    cost_usd REAL DEFAULT 0.0,
    message_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0
);

-- セッション管理インデックス
CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state);
CREATE INDEX IF NOT EXISTS idx_sessions_mode ON sessions(processing_mode);
CREATE INDEX IF NOT EXISTS idx_sessions_activity ON sessions(last_activity);

-- メトリクス収集テーブル
CREATE TABLE IF NOT EXISTS session_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    processing_mode TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    cost_usd REAL NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON session_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_mode ON session_metrics(processing_mode);
CREATE INDEX IF NOT EXISTS idx_metrics_session ON session_metrics(session_id);

-- システムメトリクステーブル
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    active_sessions INTEGER NOT NULL,
    total_cost_usd REAL NOT NULL,
    avg_latency_ms REAL NOT NULL,
    success_rate REAL NOT NULL,
    realtime_sessions INTEGER NOT NULL,
    legacy_sessions INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp);

-- フォールバックイベントテーブル
CREATE TABLE IF NOT EXISTS fallback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    reason TEXT NOT NULL,
    details TEXT,
    recovery_time REAL
);

CREATE INDEX IF NOT EXISTS idx_fallback_timestamp ON fallback_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_fallback_session ON fallback_events(session_id);

-- Function Call実行ログテーブル
CREATE TABLE IF NOT EXISTS function_call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    function_name TEXT NOT NULL,
    parameters TEXT,
    result TEXT,
    execution_time REAL,
    success BOOLEAN NOT NULL,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_function_timestamp ON function_call_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_function_session ON function_call_logs(session_id);

-- 設定管理テーブル
CREATE TABLE IF NOT EXISTS feature_flags (
    flag_name TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at REAL NOT NULL,
    updated_by TEXT,
    description TEXT
);

-- 初期フィーチャーフラグ設定
INSERT OR REPLACE INTO feature_flags (flag_name, enabled, updated_at, description) VALUES
('realtime_mode_enabled', FALSE, strftime('%s', 'now'), 'OpenAI Realtime API統合の有効化'),
('realtime_fallback_enabled', TRUE, strftime('%s', 'now'), 'フォールバック機能の有効化'),
('cost_monitoring_enabled', TRUE, strftime('%s', 'now'), 'コスト監視機能の有効化'),
('performance_monitoring_enabled', TRUE, strftime('%s', 'now'), 'パフォーマンス監視機能の有効化');

-- コスト管理ビュー
CREATE VIEW IF NOT EXISTS hourly_cost_summary AS
SELECT 
    datetime(CAST(timestamp / 3600 AS INTEGER) * 3600, 'unixepoch') as hour,
    processing_mode,
    SUM(cost_usd) as total_cost,
    COUNT(*) as message_count,
    AVG(latency_ms) as avg_latency
FROM session_metrics 
WHERE timestamp > strftime('%s', 'now') - 86400  -- 過去24時間
GROUP BY CAST(timestamp / 3600 AS INTEGER), processing_mode
ORDER BY hour DESC;

-- パフォーマンスサマリービュー
CREATE VIEW IF NOT EXISTS performance_summary AS
SELECT 
    processing_mode,
    COUNT(DISTINCT session_id) as unique_sessions,
    COUNT(*) as total_messages,
    SUM(cost_usd) as total_cost,
    AVG(latency_ms) as avg_latency,
    MIN(latency_ms) as min_latency,
    MAX(latency_ms) as max_latency,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
FROM session_metrics 
WHERE timestamp > strftime('%s', 'now') - 86400  -- 過去24時間
GROUP BY processing_mode;

-- Phase 1では複雑なトリガーは無効化
-- 後のフェーズで有効化予定

-- Basic monitoring setup completed