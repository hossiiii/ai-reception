"""
セキュリティ管理サービス

Phase 3のセキュリティ強化機能:
1. API キー管理の強化
2. 通信暗号化の強化
3. アクセス制御とレート制限
4. セキュリティ監査ログ
5. 脅威検出と対策
"""

import asyncio
import time
import hashlib
import secrets
import jwt
import bcrypt
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import ipaddress
import re
import aiosqlite
from datetime import datetime, timedelta


class SecurityEventType(Enum):
    """セキュリティイベントタイプ"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    API_ACCESS_DENIED = "api_access_denied"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    MALFORMED_REQUEST = "malformed_request"
    IP_BLOCKED = "ip_blocked"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"


class SecurityLevel(Enum):
    """セキュリティレベル"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(Enum):
    """アクセスレベル"""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    AUTHORIZED = "authorized"
    ADMIN = "admin"


@dataclass
class SecurityEvent:
    """セキュリティイベント"""
    event_id: str
    timestamp: float
    event_type: SecurityEventType
    severity: SecurityLevel
    source_ip: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    action_taken: Optional[str] = None


@dataclass
class RateLimitRule:
    """レート制限ルール"""
    name: str
    requests_per_minute: int
    requests_per_hour: int
    burst_limit: int
    enabled: bool = True


@dataclass
class AccessControlRule:
    """アクセス制御ルール"""
    rule_id: str
    path_pattern: str
    required_access_level: AccessLevel
    allowed_methods: List[str]
    ip_whitelist: Optional[List[str]] = None
    ip_blacklist: Optional[List[str]] = None
    enabled: bool = True


class APIKeyManager:
    """API キー管理"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.key_usage: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
    def generate_api_key(self, user_id: str, permissions: List[str], expires_in_days: int = 365) -> str:
        """API キー生成"""
        key_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": time.time(),
            "expires_at": time.time() + (expires_in_days * 86400),
            "active": True,
            "usage_count": 0
        }
        
        # セキュアなキー生成
        api_key = f"ai-rec-{secrets.token_urlsafe(32)}"
        self.api_keys[api_key] = key_data
        
        print(f"🔑 API key generated for user {user_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """API キー検証"""
        if api_key not in self.api_keys:
            return None
        
        key_data = self.api_keys[api_key]
        
        # 有効期限チェック
        if time.time() > key_data["expires_at"]:
            key_data["active"] = False
            return None
        
        # アクティブ状態チェック
        if not key_data["active"]:
            return None
        
        # 使用回数更新
        key_data["usage_count"] += 1
        self.key_usage[api_key].append(time.time())
        
        return key_data
    
    def revoke_api_key(self, api_key: str, reason: str = "manual_revocation"):
        """API キー無効化"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            self.api_keys[api_key]["revoked_at"] = time.time()
            self.api_keys[api_key]["revocation_reason"] = reason
            print(f"🔑 API key revoked: {reason}")
    
    def get_key_usage_stats(self, api_key: str, hours: int = 24) -> Dict[str, Any]:
        """API キー使用統計"""
        if api_key not in self.api_keys:
            return {"error": "API key not found"}
        
        usage_times = list(self.key_usage[api_key])
        cutoff_time = time.time() - (hours * 3600)
        recent_usage = [t for t in usage_times if t > cutoff_time]
        
        return {
            "api_key": api_key[:16] + "...",  # マスク表示
            "total_usage": len(usage_times),
            "recent_usage": len(recent_usage),
            "usage_rate_per_hour": len(recent_usage) / hours if hours > 0 else 0,
            "key_info": {
                "created_at": self.api_keys[api_key]["created_at"],
                "expires_at": self.api_keys[api_key]["expires_at"],
                "active": self.api_keys[api_key]["active"]
            }
        }


class RateLimiter:
    """レート制限"""
    
    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.request_counts: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque()))
        
        # デフォルトルール
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """デフォルトレート制限ルール設定"""
        default_rules = [
            RateLimitRule("general_api", 60, 1000, 10),
            RateLimitRule("realtime_api", 30, 300, 5),
            RateLimitRule("auth_endpoints", 10, 100, 3),
            RateLimitRule("admin_endpoints", 20, 200, 2)
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
    
    def add_rule(self, rule: RateLimitRule):
        """レート制限ルール追加"""
        self.rules[rule.name] = rule
        print(f"📊 Rate limit rule added: {rule.name}")
    
    async def check_rate_limit(self, identifier: str, rule_name: str = "general_api") -> Dict[str, Any]:
        """レート制限チェック"""
        if rule_name not in self.rules:
            return {"allowed": True, "reason": "no_rule"}
        
        rule = self.rules[rule_name]
        if not rule.enabled:
            return {"allowed": True, "reason": "rule_disabled"}
        
        current_time = time.time()
        
        # 分間制限チェック
        minute_key = int(current_time / 60)
        minute_requests = self.request_counts[identifier][f"minute_{minute_key}"]
        
        # 時間制限チェック
        hour_key = int(current_time / 3600)
        hour_requests = self.request_counts[identifier][f"hour_{hour_key}"]
        
        # バースト制限チェック（直近10秒）
        burst_cutoff = current_time - 10
        all_requests = []
        for key, requests in self.request_counts[identifier].items():
            all_requests.extend([t for t in requests if t > burst_cutoff])
        
        # 制限チェック
        if len(minute_requests) >= rule.requests_per_minute:
            return {
                "allowed": False,
                "reason": "minute_limit_exceeded",
                "reset_time": (minute_key + 1) * 60,
                "current_count": len(minute_requests),
                "limit": rule.requests_per_minute
            }
        
        if len(hour_requests) >= rule.requests_per_hour:
            return {
                "allowed": False,
                "reason": "hour_limit_exceeded",
                "reset_time": (hour_key + 1) * 3600,
                "current_count": len(hour_requests),
                "limit": rule.requests_per_hour
            }
        
        if len(all_requests) >= rule.burst_limit:
            return {
                "allowed": False,
                "reason": "burst_limit_exceeded",
                "reset_time": current_time + 10,
                "current_count": len(all_requests),
                "limit": rule.burst_limit
            }
        
        # リクエスト記録
        minute_requests.append(current_time)
        hour_requests.append(current_time)
        
        # 古いデータクリーンアップ
        self._cleanup_old_requests(identifier, current_time)
        
        return {
            "allowed": True,
            "remaining_minute": rule.requests_per_minute - len(minute_requests),
            "remaining_hour": rule.requests_per_hour - len(hour_requests)
        }
    
    def _cleanup_old_requests(self, identifier: str, current_time: float):
        """古いリクエスト記録クリーンアップ"""
        # 1時間以上古いデータを削除
        cutoff_time = current_time - 3600
        
        for key in list(self.request_counts[identifier].keys()):
            requests = self.request_counts[identifier][key]
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            if not requests:
                del self.request_counts[identifier][key]


class IPFilter:
    """IP フィルタリング"""
    
    def __init__(self):
        self.blacklisted_ips: Set[str] = set()
        self.whitelisted_ips: Set[str] = set()
        self.suspicious_ips: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 自動ブロック設定
        self.auto_block_enabled = True
        self.max_failed_attempts = 10
        self.failed_attempts_window = 300  # 5分
        self.auto_block_duration = 3600  # 1時間
    
    def add_to_blacklist(self, ip: str, reason: str = "manual"):
        """IP をブラックリストに追加"""
        self.blacklisted_ips.add(ip)
        self.suspicious_ips[ip] = {
            "blocked_at": time.time(),
            "reason": reason,
            "auto_block": reason == "auto_block"
        }
        print(f"🚫 IP blocked: {ip} ({reason})")
    
    def add_to_whitelist(self, ip: str):
        """IP をホワイトリストに追加"""
        self.whitelisted_ips.add(ip)
        # ブラックリストから削除
        self.blacklisted_ips.discard(ip)
        self.suspicious_ips.pop(ip, None)
        print(f"✅ IP whitelisted: {ip}")
    
    def remove_from_blacklist(self, ip: str):
        """IP をブラックリストから削除"""
        self.blacklisted_ips.discard(ip)
        self.suspicious_ips.pop(ip, None)
        print(f"🔓 IP unblocked: {ip}")
    
    def check_ip_access(self, ip: str) -> Dict[str, Any]:
        """IP アクセスチェック"""
        # ホワイトリストチェック
        if ip in self.whitelisted_ips:
            return {"allowed": True, "reason": "whitelisted"}
        
        # ブラックリストチェック
        if ip in self.blacklisted_ips:
            return {
                "allowed": False,
                "reason": "blacklisted",
                "details": self.suspicious_ips.get(ip, {})
            }
        
        # 自動ブロック期間チェック
        if ip in self.suspicious_ips:
            block_info = self.suspicious_ips[ip]
            if block_info.get("auto_block", False):
                if time.time() - block_info["blocked_at"] < self.auto_block_duration:
                    return {
                        "allowed": False,
                        "reason": "auto_blocked",
                        "unblock_time": block_info["blocked_at"] + self.auto_block_duration
                    }
                else:
                    # ブロック期間終了
                    self.remove_from_blacklist(ip)
        
        return {"allowed": True, "reason": "not_blocked"}
    
    def record_failed_attempt(self, ip: str, attempt_type: str = "general"):
        """失敗試行記録"""
        current_time = time.time()
        self.failed_attempts[ip].append({
            "timestamp": current_time,
            "type": attempt_type
        })
        
        # 自動ブロック判定
        if self.auto_block_enabled:
            self._check_auto_block(ip)
    
    def _check_auto_block(self, ip: str):
        """自動ブロック判定"""
        if ip in self.whitelisted_ips:
            return  # ホワイトリストIPは自動ブロックしない
        
        current_time = time.time()
        cutoff_time = current_time - self.failed_attempts_window
        
        recent_failures = [
            attempt for attempt in self.failed_attempts[ip]
            if attempt["timestamp"] > cutoff_time
        ]
        
        if len(recent_failures) >= self.max_failed_attempts:
            self.add_to_blacklist(ip, "auto_block")


class SecurityAuditor:
    """セキュリティ監査"""
    
    def __init__(self, db_path: str = "data/security_audit.db"):
        self.db_path = db_path
        self.security_events: deque = deque(maxlen=10000)
        self.threat_patterns = self._load_threat_patterns()
        
        self._initialized = False
        self._lock = asyncio.Lock()
    
    def _load_threat_patterns(self) -> Dict[str, List[str]]:
        """脅威パターンロード"""
        return {
            "sql_injection": [
                r"union\s+select", r"drop\s+table", r"insert\s+into",
                r"delete\s+from", r"update\s+.*set", r"exec\s*\("
            ],
            "xss": [
                r"<script", r"javascript:", r"onerror\s*=",
                r"onload\s*=", r"eval\s*\(", r"alert\s*\("
            ],
            "path_traversal": [
                r"\.\.\/", r"\.\.\\", r"%2e%2e%2f", r"%2e%2e%5c"
            ],
            "command_injection": [
                r";\s*cat\s", r";\s*ls\s", r";\s*rm\s",
                r"&\s*dir\s", r"\|\s*type\s"
            ]
        }
    
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
        """セキュリティ監査テーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    details TEXT,
                    action_taken TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS threat_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    threat_type TEXT NOT NULL,
                    source_ip TEXT NOT NULL,
                    request_data TEXT,
                    severity TEXT NOT NULL,
                    blocked BOOLEAN DEFAULT 0
                )
            """)
            
            await db.commit()
    
    async def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityLevel,
        source_ip: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        action_taken: Optional[str] = None
    ) -> str:
        """セキュリティイベントログ"""
        await self._ensure_initialized()
        
        event_id = f"sec_{int(time.time())}_{secrets.token_hex(8)}"
        
        event = SecurityEvent(
            event_id=event_id,
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            session_id=session_id,
            details=details or {},
            action_taken=action_taken
        )
        
        self.security_events.append(event)
        
        # データベースに記録
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO security_events 
                    (event_id, timestamp, event_type, severity, source_ip, 
                     user_id, session_id, details, action_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, event.timestamp, event_type.value, severity.value,
                    source_ip, user_id, session_id, 
                    str(details) if details else None, action_taken
                ))
                await db.commit()
        except Exception as e:
            print(f"❌ Security event logging error: {e}")
        
        # 重要度に応じた通知
        if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
            print(f"🚨 Security event: {event_type.value} from {source_ip} (severity: {severity.value})")
        
        return event_id
    
    def detect_threats(self, request_data: str, source_ip: str) -> List[Dict[str, Any]]:
        """脅威検出"""
        threats = []
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if re.search(pattern, request_data, re.IGNORECASE):
                    threat = {
                        "threat_type": threat_type,
                        "pattern": pattern,
                        "severity": self._get_threat_severity(threat_type),
                        "source_ip": source_ip,
                        "detected_at": time.time()
                    }
                    threats.append(threat)
                    
                    # データベースに記録
                    asyncio.create_task(self._log_threat_detection(threat, request_data))
        
        return threats
    
    def _get_threat_severity(self, threat_type: str) -> SecurityLevel:
        """脅威重要度判定"""
        severity_mapping = {
            "sql_injection": SecurityLevel.CRITICAL,
            "command_injection": SecurityLevel.CRITICAL,
            "xss": SecurityLevel.HIGH,
            "path_traversal": SecurityLevel.HIGH
        }
        return severity_mapping.get(threat_type, SecurityLevel.MEDIUM)
    
    async def _log_threat_detection(self, threat: Dict[str, Any], request_data: str):
        """脅威検出ログ"""
        await self._ensure_initialized()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO threat_detections 
                    (timestamp, threat_type, source_ip, request_data, severity, blocked)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    threat["detected_at"], threat["threat_type"], threat["source_ip"],
                    request_data[:1000], threat["severity"].value, False
                ))
                await db.commit()
        except Exception as e:
            print(f"❌ Threat detection logging error: {e}")
    
    async def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """セキュリティサマリー取得"""
        await self._ensure_initialized()
        
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            # 最近のイベント
            recent_events = [
                event for event in self.security_events
                if event.timestamp > start_time
            ]
            
            # 重要度別集計
            severity_counts = defaultdict(int)
            event_type_counts = defaultdict(int)
            ip_counts = defaultdict(int)
            
            for event in recent_events:
                severity_counts[event.severity.value] += 1
                event_type_counts[event.event_type.value] += 1
                ip_counts[event.source_ip] += 1
            
            # データベースから脅威検出情報
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT threat_type, COUNT(*) as count
                    FROM threat_detections 
                    WHERE timestamp > ?
                    GROUP BY threat_type
                """, (start_time,)) as cursor:
                    threat_stats = await cursor.fetchall()
            
            return {
                "time_range_hours": hours,
                "total_events": len(recent_events),
                "severity_breakdown": dict(severity_counts),
                "event_type_breakdown": dict(event_type_counts),
                "top_source_ips": dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "threat_detections": {threat[0]: threat[1] for threat in threat_stats},
                "security_score": self._calculate_security_score(recent_events)
            }
            
        except Exception as e:
            print(f"❌ Security summary error: {e}")
            return {"error": str(e)}
    
    def _calculate_security_score(self, events: List[SecurityEvent]) -> float:
        """セキュリティスコア計算"""
        if not events:
            return 100.0
        
        score = 100.0
        
        for event in events:
            if event.severity == SecurityLevel.CRITICAL:
                score -= 10
            elif event.severity == SecurityLevel.HIGH:
                score -= 5
            elif event.severity == SecurityLevel.MEDIUM:
                score -= 2
            elif event.severity == SecurityLevel.LOW:
                score -= 1
        
        return max(0.0, score)


class SecurityManager:
    """統合セキュリティ管理サービス"""
    
    def __init__(self, db_path: str = "data/security.db"):
        self.api_key_manager = APIKeyManager()
        self.rate_limiter = RateLimiter()
        self.ip_filter = IPFilter()
        self.auditor = SecurityAuditor(db_path)
        self.access_rules: List[AccessControlRule] = []
        
        # JWT設定
        self.jwt_secret = secrets.token_urlsafe(32)
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_hours = 24
        
        # セキュリティ設定
        self.enable_threat_detection = True
        self.enable_auto_blocking = True
        self.enable_audit_logging = True
        
        self._setup_default_access_rules()
        
        print("✅ SecurityManager initialized")
    
    def _setup_default_access_rules(self):
        """デフォルトアクセス制御ルール設定"""
        default_rules = [
            AccessControlRule(
                rule_id="public_endpoints",
                path_pattern=r"^/(health|docs|openapi\.json).*",
                required_access_level=AccessLevel.PUBLIC,
                allowed_methods=["GET"]
            ),
            AccessControlRule(
                rule_id="api_endpoints",
                path_pattern=r"^/api/.*",
                required_access_level=AccessLevel.AUTHENTICATED,
                allowed_methods=["GET", "POST", "PUT", "DELETE"]
            ),
            AccessControlRule(
                rule_id="admin_endpoints",
                path_pattern=r"^/admin/.*",
                required_access_level=AccessLevel.ADMIN,
                allowed_methods=["GET", "POST", "PUT", "DELETE"]
            )
        ]
        
        self.access_rules.extend(default_rules)
    
    async def authenticate_request(
        self,
        request_path: str,
        request_method: str,
        source_ip: str,
        headers: Dict[str, str],
        request_data: str = ""
    ) -> Dict[str, Any]:
        """リクエスト認証"""
        # IP フィルタリング
        ip_check = self.ip_filter.check_ip_access(source_ip)
        if not ip_check["allowed"]:
            await self.auditor.log_security_event(
                SecurityEventType.IP_BLOCKED,
                SecurityLevel.MEDIUM,
                source_ip,
                details=ip_check
            )
            return {
                "allowed": False,
                "reason": "ip_blocked",
                "details": ip_check
            }
        
        # 脅威検出
        if self.enable_threat_detection and request_data:
            threats = self.auditor.detect_threats(request_data, source_ip)
            if threats:
                # 重要な脅威の場合はIPをブロック
                critical_threats = [t for t in threats if t["severity"] == SecurityLevel.CRITICAL]
                if critical_threats and self.enable_auto_blocking:
                    self.ip_filter.add_to_blacklist(source_ip, "threat_detected")
                
                await self.auditor.log_security_event(
                    SecurityEventType.SUSPICIOUS_ACTIVITY,
                    SecurityLevel.HIGH,
                    source_ip,
                    details={"threats": threats}
                )
                
                return {
                    "allowed": False,
                    "reason": "threat_detected",
                    "threats": threats
                }
        
        # アクセス制御チェック
        access_rule = self._find_matching_access_rule(request_path)
        if access_rule:
            # メソッドチェック
            if request_method not in access_rule.allowed_methods:
                await self.auditor.log_security_event(
                    SecurityEventType.API_ACCESS_DENIED,
                    SecurityLevel.MEDIUM,
                    source_ip,
                    details={"path": request_path, "method": request_method}
                )
                return {
                    "allowed": False,
                    "reason": "method_not_allowed",
                    "allowed_methods": access_rule.allowed_methods
                }
            
            # IP ホワイト/ブラックリストチェック
            if access_rule.ip_blacklist and source_ip in access_rule.ip_blacklist:
                return {"allowed": False, "reason": "ip_blacklisted_for_endpoint"}
            
            if access_rule.ip_whitelist and source_ip not in access_rule.ip_whitelist:
                return {"allowed": False, "reason": "ip_not_whitelisted_for_endpoint"}
            
            # 認証レベルチェック
            auth_result = await self._check_authentication_level(
                access_rule.required_access_level, headers, source_ip
            )
            
            if not auth_result["allowed"]:
                return auth_result
        
        # レート制限チェック
        rate_limit_key = f"{source_ip}:{request_path}"
        rate_limit_result = await self.rate_limiter.check_rate_limit(rate_limit_key)
        
        if not rate_limit_result["allowed"]:
            await self.auditor.log_security_event(
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityLevel.LOW,
                source_ip,
                details=rate_limit_result
            )
            
            # 連続的なレート制限違反は疑わしい活動として記録
            self.ip_filter.record_failed_attempt(source_ip, "rate_limit")
            
            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "details": rate_limit_result
            }
        
        # 認証成功
        return {"allowed": True, "rate_limit": rate_limit_result}
    
    def _find_matching_access_rule(self, request_path: str) -> Optional[AccessControlRule]:
        """マッチするアクセス制御ルール検索"""
        for rule in self.access_rules:
            if rule.enabled and re.match(rule.path_pattern, request_path):
                return rule
        return None
    
    async def _check_authentication_level(
        self,
        required_level: AccessLevel,
        headers: Dict[str, str],
        source_ip: str
    ) -> Dict[str, Any]:
        """認証レベルチェック"""
        if required_level == AccessLevel.PUBLIC:
            return {"allowed": True, "auth_level": "public"}
        
        # API キー認証
        api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("Bearer ", "")
        
        if api_key:
            key_data = self.api_key_manager.validate_api_key(api_key)
            if key_data:
                user_permissions = key_data.get("permissions", [])
                
                # 権限レベルチェック
                if required_level == AccessLevel.AUTHENTICATED:
                    return {"allowed": True, "auth_level": "authenticated", "user_id": key_data["user_id"]}
                elif required_level == AccessLevel.AUTHORIZED and "api_access" in user_permissions:
                    return {"allowed": True, "auth_level": "authorized", "user_id": key_data["user_id"]}
                elif required_level == AccessLevel.ADMIN and "admin" in user_permissions:
                    return {"allowed": True, "auth_level": "admin", "user_id": key_data["user_id"]}
            else:
                # 無効なAPIキー
                await self.auditor.log_security_event(
                    SecurityEventType.LOGIN_FAILURE,
                    SecurityLevel.MEDIUM,
                    source_ip,
                    details={"reason": "invalid_api_key"}
                )
                
                self.ip_filter.record_failed_attempt(source_ip, "invalid_api_key")
        
        # JWT 認証（追加実装可能）
        jwt_token = headers.get("Authorization", "").replace("Bearer ", "") if not api_key else None
        if jwt_token:
            try:
                payload = jwt.decode(jwt_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
                # JWT から権限レベル確認
                user_role = payload.get("role", "user")
                
                if required_level == AccessLevel.AUTHENTICATED:
                    return {"allowed": True, "auth_level": "authenticated", "user_id": payload.get("user_id")}
                elif required_level == AccessLevel.ADMIN and user_role == "admin":
                    return {"allowed": True, "auth_level": "admin", "user_id": payload.get("user_id")}
                    
            except jwt.InvalidTokenError:
                await self.auditor.log_security_event(
                    SecurityEventType.LOGIN_FAILURE,
                    SecurityLevel.MEDIUM,
                    source_ip,
                    details={"reason": "invalid_jwt"}
                )
        
        return {
            "allowed": False,
            "reason": "insufficient_authentication",
            "required_level": required_level.value
        }
    
    def generate_jwt_token(self, user_id: str, role: str = "user", custom_claims: Dict[str, Any] = None) -> str:
        """JWT トークン生成"""
        payload = {
            "user_id": user_id,
            "role": role,
            "iat": time.time(),
            "exp": time.time() + (self.jwt_expiry_hours * 3600)
        }
        
        if custom_claims:
            payload.update(custom_claims)
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    async def get_security_dashboard(self) -> Dict[str, Any]:
        """セキュリティダッシュボードデータ取得"""
        try:
            # セキュリティサマリー
            security_summary = await self.auditor.get_security_summary()
            
            # IP フィルター状態
            ip_filter_status = {
                "blacklisted_ips": len(self.ip_filter.blacklisted_ips),
                "whitelisted_ips": len(self.ip_filter.whitelisted_ips),
                "auto_block_enabled": self.ip_filter.auto_block_enabled
            }
            
            # API キー統計
            active_api_keys = len([k for k in self.api_key_manager.api_keys.values() if k["active"]])
            
            # レート制限統計
            rate_limit_rules = len(self.rate_limiter.rules)
            
            return {
                "timestamp": time.time(),
                "security_summary": security_summary,
                "ip_filtering": ip_filter_status,
                "api_keys": {
                    "total_active": active_api_keys,
                    "total_keys": len(self.api_key_manager.api_keys)
                },
                "rate_limiting": {
                    "active_rules": rate_limit_rules,
                    "enabled": True
                },
                "access_control": {
                    "total_rules": len(self.access_rules),
                    "enabled_rules": len([r for r in self.access_rules if r.enabled])
                },
                "threat_detection": {
                    "enabled": self.enable_threat_detection,
                    "patterns_loaded": len(self.auditor.threat_patterns)
                }
            }
            
        except Exception as e:
            print(f"❌ Security dashboard error: {e}")
            return {"error": str(e)}


# グローバルインスタンス
security_manager = SecurityManager()


async def get_security_manager() -> SecurityManager:
    """セキュリティ管理サービス取得"""
    return security_manager