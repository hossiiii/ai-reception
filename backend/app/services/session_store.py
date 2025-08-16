"""
拡張セッション状態管理

RealtimeとLegacyモード両方に対応したセッション管理
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import aiosqlite


class SessionState(Enum):
    """セッション状態"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class SessionInfo:
    """セッション情報"""
    session_id: str
    state: SessionState
    processing_mode: str  # "legacy" or "realtime"
    created_at: float
    last_activity: float
    visitor_info: Optional[Dict[str, Any]] = None
    conversation_step: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    cost_usd: float = 0.0
    message_count: int = 0
    error_count: int = 0


class SessionStore:
    """セッション状態管理ストア"""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._initialized = False
        self._lock = asyncio.Lock()
        
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
        """テーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    processing_mode TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_activity REAL NOT NULL,
                    visitor_info TEXT,
                    conversation_step TEXT,
                    metadata TEXT,
                    cost_usd REAL DEFAULT 0.0,
                    message_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_state 
                ON sessions(state)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_last_activity 
                ON sessions(last_activity)
            """)
            
            await db.commit()

    async def create_session(self, session_id: str, initial_data: Dict[str, Any]) -> bool:
        """新しいセッション作成"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            
            session_info = SessionInfo(
                session_id=session_id,
                state=SessionState.INITIALIZING,
                processing_mode=initial_data.get("mode", "legacy"),
                created_at=current_time,
                last_activity=current_time,
                visitor_info=initial_data.get("visitor_info"),
                conversation_step=initial_data.get("step"),
                metadata=initial_data.get("preferences", {})
            )
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO sessions (
                        session_id, state, processing_mode, created_at, last_activity,
                        visitor_info, conversation_step, metadata, cost_usd, message_count, error_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_info.session_id,
                    session_info.state.value,
                    session_info.processing_mode,
                    session_info.created_at,
                    session_info.last_activity,
                    json.dumps(session_info.visitor_info) if session_info.visitor_info else None,
                    session_info.conversation_step,
                    json.dumps(session_info.metadata) if session_info.metadata else None,
                    session_info.cost_usd,
                    session_info.message_count,
                    session_info.error_count
                ))
                await db.commit()
            
            print(f"✅ Session created: {session_id} (mode: {session_info.processing_mode})")
            return True
            
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """セッション情報取得"""
        await self._ensure_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM sessions WHERE session_id = ?
                """, (session_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return SessionInfo(
                            session_id=row[0],
                            state=SessionState(row[1]),
                            processing_mode=row[2],
                            created_at=row[3],
                            last_activity=row[4],
                            visitor_info=json.loads(row[5]) if row[5] else None,
                            conversation_step=row[6],
                            metadata=json.loads(row[7]) if row[7] else None,
                            cost_usd=row[8],
                            message_count=row[9],
                            error_count=row[10]
                        )
            
            return None
            
        except Exception as e:
            print(f"❌ Session retrieval error: {e}")
            return None

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """セッション情報更新"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            
            # 更新可能フィールドの処理
            set_clauses = ["last_activity = ?"]
            values = [current_time]
            
            if "state" in updates:
                set_clauses.append("state = ?")
                values.append(updates["state"].value if isinstance(updates["state"], SessionState) else updates["state"])
            
            if "visitor_info" in updates:
                set_clauses.append("visitor_info = ?")
                values.append(json.dumps(updates["visitor_info"]) if updates["visitor_info"] else None)
            
            if "conversation_step" in updates:
                set_clauses.append("conversation_step = ?")
                values.append(updates["conversation_step"])
            
            if "metadata" in updates:
                set_clauses.append("metadata = ?")
                values.append(json.dumps(updates["metadata"]) if updates["metadata"] else None)
            
            if "cost_usd" in updates:
                set_clauses.append("cost_usd = ?")
                values.append(updates["cost_usd"])
            
            if "message_count" in updates:
                set_clauses.append("message_count = ?")
                values.append(updates["message_count"])
            
            if "error_count" in updates:
                set_clauses.append("error_count = ?")
                values.append(updates["error_count"])
            
            values.append(session_id)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(f"""
                    UPDATE sessions 
                    SET {', '.join(set_clauses)}
                    WHERE session_id = ?
                """, values)
                await db.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Session update error: {e}")
            return False

    async def increment_counters(self, session_id: str, message_count: int = 0, cost_usd: float = 0.0, error_count: int = 0) -> bool:
        """カウンターの増分更新"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE sessions 
                    SET 
                        last_activity = ?,
                        message_count = message_count + ?,
                        cost_usd = cost_usd + ?,
                        error_count = error_count + ?
                    WHERE session_id = ?
                """, (current_time, message_count, cost_usd, error_count, session_id))
                await db.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ Counter increment error: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """セッション削除"""
        await self._ensure_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                await db.commit()
            
            print(f"🗑️ Session deleted: {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Session deletion error: {e}")
            return False

    async def list_active_sessions(self) -> List[SessionInfo]:
        """アクティブなセッション一覧"""
        await self._ensure_initialized()
        
        try:
            active_states = [SessionState.ACTIVE, SessionState.PROCESSING, SessionState.WAITING]
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM sessions 
                    WHERE state IN ({})
                    ORDER BY last_activity DESC
                """.format(','.join(['?' for _ in active_states])), 
                [state.value for state in active_states]) as cursor:
                    rows = await cursor.fetchall()
                    
                    sessions = []
                    for row in rows:
                        sessions.append(SessionInfo(
                            session_id=row[0],
                            state=SessionState(row[1]),
                            processing_mode=row[2],
                            created_at=row[3],
                            last_activity=row[4],
                            visitor_info=json.loads(row[5]) if row[5] else None,
                            conversation_step=row[6],
                            metadata=json.loads(row[7]) if row[7] else None,
                            cost_usd=row[8],
                            message_count=row[9],
                            error_count=row[10]
                        ))
                    
                    return sessions
                    
        except Exception as e:
            print(f"❌ Active sessions retrieval error: {e}")
            return []

    async def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """期限切れセッションのクリーンアップ"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            cutoff_time = current_time - max_age_seconds
            
            async with aiosqlite.connect(self.db_path) as db:
                # 期限切れセッションを特定
                async with db.execute("""
                    SELECT session_id FROM sessions 
                    WHERE last_activity < ? OR state = ?
                """, (cutoff_time, SessionState.EXPIRED.value)) as cursor:
                    expired_sessions = await cursor.fetchall()
                
                # 期限切れセッションを削除
                await db.execute("""
                    DELETE FROM sessions 
                    WHERE last_activity < ? OR state = ?
                """, (cutoff_time, SessionState.EXPIRED.value))
                
                await db.commit()
                
                cleanup_count = len(expired_sessions)
                if cleanup_count > 0:
                    print(f"🧹 Cleaned up {cleanup_count} expired sessions")
                
                return cleanup_count
                
        except Exception as e:
            print(f"❌ Session cleanup error: {e}")
            return 0

    async def get_session_statistics(self) -> Dict[str, Any]:
        """セッション統計情報"""
        await self._ensure_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 基本統計
                async with db.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active_sessions,
                        SUM(CASE WHEN processing_mode = 'realtime' THEN 1 ELSE 0 END) as realtime_sessions,
                        SUM(CASE WHEN processing_mode = 'legacy' THEN 1 ELSE 0 END) as legacy_sessions,
                        SUM(cost_usd) as total_cost,
                        SUM(message_count) as total_messages,
                        AVG(cost_usd) as avg_cost_per_session
                    FROM sessions
                """) as cursor:
                    row = await cursor.fetchone()
                    
                    return {
                        "total_sessions": row[0],
                        "active_sessions": row[1],
                        "realtime_sessions": row[2],
                        "legacy_sessions": row[3],
                        "total_cost_usd": row[4] or 0.0,
                        "total_messages": row[5] or 0,
                        "avg_cost_per_session": row[6] or 0.0
                    }
                    
        except Exception as e:
            print(f"❌ Statistics retrieval error: {e}")
            return {}