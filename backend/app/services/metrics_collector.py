"""
メトリクス収集サービス

Realtime APIとLegacyモードの使用状況、パフォーマンス、コストを追跡
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import sqlite3
import aiosqlite


@dataclass
class SessionMetric:
    """セッションメトリクス"""
    session_id: str
    timestamp: float
    processing_mode: str
    latency_ms: float
    cost_usd: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class SystemMetric:
    """システムメトリクス"""
    timestamp: float
    active_sessions: int
    total_cost_usd: float
    avg_latency_ms: float
    success_rate: float
    realtime_sessions: int
    legacy_sessions: int


class MetricsCollector:
    """メトリクス収集・管理サービス"""

    def __init__(self, db_path: str = ":memory:", retention_hours: int = 24):
        self.db_path = db_path
        self.retention_hours = retention_hours
        
        # インメモリ統計（高速アクセス用）
        self.hourly_costs = deque(maxlen=retention_hours)
        self.session_stats = defaultdict(lambda: {
            "count": 0, "total_cost": 0.0, "total_latency": 0.0, "errors": 0
        })
        
        self._initialized = False
        self._lock = asyncio.Lock()
        
        print("✅ MetricsCollector initialized")

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
        """メトリクステーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            # セッションメトリクステーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    processing_mode TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    cost_usd REAL NOT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT
                )
            """)
            
            # システムメトリクステーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    active_sessions INTEGER NOT NULL,
                    total_cost_usd REAL NOT NULL,
                    avg_latency_ms REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    realtime_sessions INTEGER NOT NULL,
                    legacy_sessions INTEGER NOT NULL
                )
            """)
            
            # インデックス作成
            await db.execute("CREATE INDEX IF NOT EXISTS idx_session_timestamp ON session_metrics(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)")
            
            await db.commit()

    async def record_session_start(self, session_id: str, processing_mode: str):
        """セッション開始記録"""
        current_time = time.time()
        
        # インメモリ統計更新
        self.session_stats[processing_mode]["count"] += 1
        
        print(f"📊 Session started: {session_id} (mode: {processing_mode})")

    async def record_message_processed(
        self, 
        session_id: str, 
        processing_time: float, 
        cost: float, 
        processing_mode: str,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """メッセージ処理記録"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            latency_ms = processing_time * 1000
            
            # データベースに記録
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO session_metrics 
                    (session_id, timestamp, processing_mode, latency_ms, cost_usd, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, current_time, processing_mode, latency_ms, cost, success, error_message))
                await db.commit()
            
            # インメモリ統計更新
            stats = self.session_stats[processing_mode]
            stats["total_cost"] += cost
            stats["total_latency"] += latency_ms
            if not success:
                stats["errors"] += 1
            
            print(f"📊 Message processed: {session_id} ({latency_ms:.0f}ms, ${cost:.4f})")
            
        except Exception as e:
            print(f"❌ Metrics recording error: {e}")

    async def record_error(self, session_id: str, error_message: str):
        """エラー記録"""
        print(f"📊 Error recorded: {session_id} - {error_message}")
        
        # エラーカウント更新
        for mode_stats in self.session_stats.values():
            mode_stats["errors"] += 1

    async def record_fallback(self, session_id: str, reason: str):
        """フォールバック記録"""
        print(f"📊 Fallback recorded: {session_id} - {reason}")

    async def record_session_end(
        self, 
        session_id: str, 
        duration: float, 
        total_cost: float, 
        fallback_triggered: bool
    ):
        """セッション終了記録"""
        print(f"📊 Session ended: {session_id} (${total_cost:.4f}, fallback: {fallback_triggered})")

    async def get_hourly_cost(self) -> float:
        """過去1時間のコスト取得"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            hour_ago = current_time - 3600
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT SUM(cost_usd) FROM session_metrics 
                    WHERE timestamp > ?
                """, (hour_ago,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] or 0.0
                    
        except Exception as e:
            print(f"❌ Hourly cost calculation error: {e}")
            return 0.0

    async def get_current_statistics(self) -> Dict[str, Any]:
        """現在の統計情報取得"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            hour_ago = current_time - 3600
            
            async with aiosqlite.connect(self.db_path) as db:
                # 過去1時間の統計
                async with db.execute("""
                    SELECT 
                        processing_mode,
                        COUNT(*) as message_count,
                        AVG(latency_ms) as avg_latency,
                        SUM(cost_usd) as total_cost,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                    FROM session_metrics 
                    WHERE timestamp > ?
                    GROUP BY processing_mode
                """, (hour_ago,)) as cursor:
                    mode_stats = await cursor.fetchall()
                
                # 全体統計
                async with db.execute("""
                    SELECT 
                        COUNT(DISTINCT session_id) as unique_sessions,
                        AVG(latency_ms) as overall_avg_latency,
                        SUM(cost_usd) as overall_total_cost
                    FROM session_metrics 
                    WHERE timestamp > ?
                """, (hour_ago,)) as cursor:
                    overall_stats = await cursor.fetchone()
                
                statistics = {
                    "timestamp": current_time,
                    "time_range_hours": 1,
                    "overall": {
                        "unique_sessions": overall_stats[0] or 0,
                        "avg_latency_ms": overall_stats[1] or 0.0,
                        "total_cost_usd": overall_stats[2] or 0.0
                    },
                    "by_mode": {}
                }
                
                for mode_stat in mode_stats:
                    statistics["by_mode"][mode_stat[0]] = {
                        "message_count": mode_stat[1],
                        "avg_latency_ms": mode_stat[2] or 0.0,
                        "total_cost_usd": mode_stat[3] or 0.0,
                        "success_rate": mode_stat[4] or 0.0
                    }
                
                return statistics
                
        except Exception as e:
            print(f"❌ Statistics calculation error: {e}")
            return {"error": str(e)}

    async def get_performance_trends(self, hours: int = 6) -> Dict[str, Any]:
        """パフォーマンストレンド取得"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 時間別統計
                async with db.execute("""
                    SELECT 
                        CAST(timestamp / 3600 AS INTEGER) * 3600 as hour_bucket,
                        processing_mode,
                        COUNT(*) as message_count,
                        AVG(latency_ms) as avg_latency,
                        SUM(cost_usd) as total_cost
                    FROM session_metrics 
                    WHERE timestamp > ?
                    GROUP BY hour_bucket, processing_mode
                    ORDER BY hour_bucket
                """, (start_time,)) as cursor:
                    hourly_data = await cursor.fetchall()
                
                trends = {
                    "time_range_hours": hours,
                    "hourly_data": [],
                    "summary": {
                        "total_messages": 0,
                        "total_cost": 0.0,
                        "peak_latency": 0.0
                    }
                }
                
                for row in hourly_data:
                    hour_data = {
                        "timestamp": row[0],
                        "processing_mode": row[1],
                        "message_count": row[2],
                        "avg_latency_ms": row[3],
                        "total_cost_usd": row[4]
                    }
                    trends["hourly_data"].append(hour_data)
                    
                    # サマリー更新
                    trends["summary"]["total_messages"] += row[2]
                    trends["summary"]["total_cost"] += row[4]
                    trends["summary"]["peak_latency"] = max(
                        trends["summary"]["peak_latency"], row[3]
                    )
                
                return trends
                
        except Exception as e:
            print(f"❌ Trends calculation error: {e}")
            return {"error": str(e)}

    async def cleanup_old_metrics(self):
        """古いメトリクスのクリーンアップ"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.retention_hours * 3600)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 古いセッションメトリクス削除
                cursor = await db.execute(
                    "DELETE FROM session_metrics WHERE timestamp < ?", 
                    (cutoff_time,)
                )
                session_deleted = cursor.rowcount
                
                # 古いシステムメトリクス削除
                cursor = await db.execute(
                    "DELETE FROM system_metrics WHERE timestamp < ?", 
                    (cutoff_time,)
                )
                system_deleted = cursor.rowcount
                
                await db.commit()
                
                if session_deleted > 0 or system_deleted > 0:
                    print(f"🧹 Cleaned up {session_deleted} session metrics and {system_deleted} system metrics")
                
        except Exception as e:
            print(f"❌ Metrics cleanup error: {e}")

    async def export_metrics(self, format: str = "json") -> str:
        """メトリクスエクスポート"""
        try:
            current_stats = await self.get_current_statistics()
            trends = await self.get_performance_trends()
            
            export_data = {
                "export_timestamp": time.time(),
                "current_statistics": current_stats,
                "performance_trends": trends,
                "retention_hours": self.retention_hours
            }
            
            if format == "json":
                return json.dumps(export_data, indent=2)
            else:
                return str(export_data)
                
        except Exception as e:
            print(f"❌ Metrics export error: {e}")
            return json.dumps({"error": str(e)})