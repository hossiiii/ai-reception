"""
運用監視・アラートシステム

Phase 3の監視機能:
1. 包括的なメトリクス収集
2. リアルタイム監視ダッシュボード
3. 自動アラート機能
4. パフォーマンスレポート生成
"""

import asyncio
import time
import json
import psutil
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import sqlite3
import aiosqlite
from datetime import datetime, timedelta


class MetricType(Enum):
    """メトリクスタイプ"""
    SYSTEM = "system"
    APPLICATION = "application"
    BUSINESS = "business"
    SECURITY = "security"


class AlertSeverity(Enum):
    """アラート重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MonitoringStatus(Enum):
    """監視状態"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class SystemMetric:
    """システムメトリクス"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    active_connections: int
    response_time_ms: float
    error_rate: float


@dataclass
class ApplicationMetric:
    """アプリケーションメトリクス"""
    timestamp: float
    session_count: int
    realtime_sessions: int
    legacy_sessions: int
    avg_session_duration: float
    successful_requests: int
    failed_requests: int
    audio_processing_time_ms: float
    function_call_count: int


@dataclass
class BusinessMetric:
    """ビジネスメトリクス"""
    timestamp: float
    total_visitors: int
    appointment_visitors: int
    sales_visitors: int
    delivery_visitors: int
    other_visitors: int
    customer_satisfaction_score: float
    conversion_rate: float


@dataclass
class SecurityMetric:
    """セキュリティメトリクス"""
    timestamp: float
    failed_auth_attempts: int
    rate_limit_violations: int
    suspicious_activities: int
    blocked_ips: int
    security_events: List[Dict[str, Any]]


@dataclass
class AlertRule:
    """アラートルール"""
    rule_id: str
    name: str
    metric_type: MetricType
    condition: str  # 例: "cpu_percent > 80"
    severity: AlertSeverity
    enabled: bool = True
    cooldown_seconds: int = 300
    notification_channels: List[str] = field(default_factory=list)
    last_triggered: Optional[float] = None


@dataclass
class Alert:
    """アラート"""
    alert_id: str
    rule_id: str
    timestamp: float
    severity: AlertSeverity
    metric_type: MetricType
    message: str
    current_value: Any
    threshold_value: Any
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[float] = None


class MetricsCollectorEnhanced:
    """強化されたメトリクス収集"""
    
    def __init__(self):
        self.collection_interval = 30  # 30秒間隔
        self.retention_hours = 168  # 7日間
        self.running = False
        
        # メトリクス履歴
        self.system_metrics = deque(maxlen=1000)
        self.application_metrics = deque(maxlen=1000)
        self.business_metrics = deque(maxlen=1000)
        self.security_metrics = deque(maxlen=1000)
        
        # パフォーマンス追跡
        self.response_times = deque(maxlen=100)
        self.error_counts = deque(maxlen=100)
        
    async def collect_system_metrics(self) -> SystemMetric:
        """システムメトリクス収集"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # ネットワークI/O
            network_io = psutil.net_io_counters()._asdict()
            
            # アクティブ接続数（概算）- エラーハンドリング付き
            try:
                active_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, OSError, PermissionError) as e:
                # 権限不足やその他のエラーの場合はデフォルト値を使用
                active_connections = 0
                print(f"⚠️ Unable to get network connections (using default): {e}")
            
            # レスポンス時間（最近の平均）
            avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            # エラー率計算
            total_requests = sum(self.error_counts) if self.error_counts else 1
            error_count = sum(1 for error in self.error_counts if error > 0) if self.error_counts else 0
            error_rate = (error_count / total_requests) * 100 if total_requests > 0 else 0
            
            metric = SystemMetric(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                active_connections=active_connections,
                response_time_ms=avg_response_time,
                error_rate=error_rate
            )
            
            self.system_metrics.append(metric)
            return metric
            
        except Exception as e:
            print(f"❌ System metrics collection error: {e}")
            return None
    
    async def collect_application_metrics(self, session_manager) -> ApplicationMetric:
        """アプリケーションメトリクス収集"""
        try:
            # セッション統計
            active_sessions = len(getattr(session_manager, 'active_sessions', {}))
            realtime_sessions = len([s for s in getattr(session_manager, 'active_sessions', {}).values() 
                                   if getattr(s, 'mode', '') == 'realtime'])
            legacy_sessions = active_sessions - realtime_sessions
            
            # セッション継続時間（仮の値）
            avg_session_duration = 180.0  # 3分平均と仮定
            
            # リクエスト統計
            successful_requests = 100  # 実際の値は別途収集
            failed_requests = 5
            
            # 音声処理時間
            avg_audio_processing = sum(self.response_times) / len(self.response_times) if self.response_times else 0
            
            # Function Call統計
            function_call_count = 0  # 実際の値は別途収集
            
            metric = ApplicationMetric(
                timestamp=time.time(),
                session_count=active_sessions,
                realtime_sessions=realtime_sessions,
                legacy_sessions=legacy_sessions,
                avg_session_duration=avg_session_duration,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                audio_processing_time_ms=avg_audio_processing,
                function_call_count=function_call_count
            )
            
            self.application_metrics.append(metric)
            return metric
            
        except Exception as e:
            print(f"❌ Application metrics collection error: {e}")
            return None
    
    async def collect_business_metrics(self) -> BusinessMetric:
        """ビジネスメトリクス収集"""
        try:
            # ビジネスメトリクスは実際のデータベースから収集
            # ここでは仮の値を使用
            
            metric = BusinessMetric(
                timestamp=time.time(),
                total_visitors=50,
                appointment_visitors=30,
                sales_visitors=10,
                delivery_visitors=8,
                other_visitors=2,
                customer_satisfaction_score=4.2,
                conversion_rate=0.85
            )
            
            self.business_metrics.append(metric)
            return metric
            
        except Exception as e:
            print(f"❌ Business metrics collection error: {e}")
            return None
    
    async def collect_security_metrics(self) -> SecurityMetric:
        """セキュリティメトリクス収集"""
        try:
            # セキュリティメトリクスは実際のログから収集
            # ここでは仮の値を使用
            
            metric = SecurityMetric(
                timestamp=time.time(),
                failed_auth_attempts=2,
                rate_limit_violations=0,
                suspicious_activities=0,
                blocked_ips=3,
                security_events=[]
            )
            
            self.security_metrics.append(metric)
            return metric
            
        except Exception as e:
            print(f"❌ Security metrics collection error: {e}")
            return None
    
    def record_response_time(self, response_time_ms: float):
        """レスポンス時間記録"""
        self.response_times.append(response_time_ms)
    
    def record_error(self, error_code: int = 1):
        """エラー記録"""
        self.error_counts.append(error_code)
    
    async def start_collection(self, session_manager=None):
        """メトリクス収集開始"""
        self.running = True
        print("📊 Enhanced metrics collection started")
        
        while self.running:
            try:
                # 各種メトリクス収集
                await self.collect_system_metrics()
                await self.collect_application_metrics(session_manager)
                await self.collect_business_metrics()
                await self.collect_security_metrics()
                
                # 収集間隔待機
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                print(f"❌ Metrics collection error: {e}")
                await asyncio.sleep(5)  # エラー時は短い間隔で再試行
    
    async def stop_collection(self):
        """メトリクス収集停止"""
        self.running = False
        print("📊 Metrics collection stopped")


class AlertManager:
    """アラート管理システム"""
    
    def __init__(self, db_path: str = "data/monitoring.db"):
        self.db_path = db_path
        self.alert_rules = {}
        self.active_alerts = {}
        self.notification_handlers = {}
        
        # デフォルトアラートルール
        self._setup_default_rules()
        
        self._initialized = False
        self._lock = asyncio.Lock()
    
    def _setup_default_rules(self):
        """デフォルトアラートルール設定"""
        default_rules = [
            AlertRule(
                rule_id="high_cpu",
                name="High CPU Usage",
                metric_type=MetricType.SYSTEM,
                condition="cpu_percent > 80",
                severity=AlertSeverity.HIGH,
                cooldown_seconds=300
            ),
            AlertRule(
                rule_id="high_memory",
                name="High Memory Usage",
                metric_type=MetricType.SYSTEM,
                condition="memory_percent > 85",
                severity=AlertSeverity.HIGH,
                cooldown_seconds=300
            ),
            AlertRule(
                rule_id="high_response_time",
                name="High Response Time",
                metric_type=MetricType.SYSTEM,
                condition="response_time_ms > 2000",
                severity=AlertSeverity.MEDIUM,
                cooldown_seconds=180
            ),
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                metric_type=MetricType.SYSTEM,
                condition="error_rate > 5",
                severity=AlertSeverity.CRITICAL,
                cooldown_seconds=120
            ),
            AlertRule(
                rule_id="security_breach",
                name="Security Breach Detected",
                metric_type=MetricType.SECURITY,
                condition="failed_auth_attempts > 10",
                severity=AlertSeverity.CRITICAL,
                cooldown_seconds=60
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
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
        """監視テーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            # アラートルールテーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    condition_expr TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    cooldown_seconds INTEGER DEFAULT 300,
                    notification_channels TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            
            # アラート履歴テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    alert_id TEXT PRIMARY KEY,
                    rule_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    severity TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_value TEXT,
                    threshold_value TEXT,
                    acknowledged BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    resolved_at REAL,
                    FOREIGN KEY (rule_id) REFERENCES alert_rules (rule_id)
                )
            """)
            
            # システムメトリクステーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    network_io TEXT,
                    active_connections INTEGER,
                    response_time_ms REAL,
                    error_rate REAL
                )
            """)
            
            # アプリケーションメトリクステーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS application_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    session_count INTEGER,
                    realtime_sessions INTEGER,
                    legacy_sessions INTEGER,
                    avg_session_duration REAL,
                    successful_requests INTEGER,
                    failed_requests INTEGER,
                    audio_processing_time_ms REAL,
                    function_call_count INTEGER
                )
            """)
            
            await db.commit()
    
    async def evaluate_metrics(self, metrics: Dict[MetricType, Any]):
        """メトリクス評価とアラート生成"""
        await self._ensure_initialized()
        
        triggered_alerts = []
        
        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # クールダウン期間チェック
            if rule.last_triggered and time.time() - rule.last_triggered < rule.cooldown_seconds:
                continue
            
            # メトリクスタイプに対応するデータ取得
            metric_data = metrics.get(rule.metric_type)
            if not metric_data:
                continue
            
            # 条件評価
            try:
                alert_triggered = self._evaluate_condition(rule.condition, metric_data)
                
                if alert_triggered:
                    alert = await self._create_alert(rule, metric_data)
                    triggered_alerts.append(alert)
                    rule.last_triggered = time.time()
                    
            except Exception as e:
                print(f"❌ Alert rule evaluation error [{rule_id}]: {e}")
        
        # アラート通知送信
        for alert in triggered_alerts:
            await self._send_alert_notification(alert)
        
        return triggered_alerts
    
    def _evaluate_condition(self, condition: str, metric_data: Any) -> bool:
        """条件評価"""
        try:
            # メトリクスデータを辞書に変換
            if hasattr(metric_data, '__dict__'):
                metric_dict = metric_data.__dict__
            else:
                metric_dict = metric_data
            
            # 安全な評価のために制限された名前空間を使用
            safe_namespace = {
                **metric_dict,
                'abs': abs,
                'min': min,
                'max': max,
                'len': len
            }
            
            return eval(condition, {"__builtins__": {}}, safe_namespace)
            
        except Exception as e:
            print(f"❌ Condition evaluation error: {e}")
            return False
    
    async def _create_alert(self, rule: AlertRule, metric_data: Any) -> Alert:
        """アラート作成"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"
        
        # 現在値と閾値を抽出（簡単な実装）
        current_value = "N/A"
        threshold_value = "N/A"
        
        if hasattr(metric_data, '__dict__'):
            # 条件から閾値を抽出（簡単な例）
            if ">" in rule.condition:
                parts = rule.condition.split(">")
                if len(parts) == 2:
                    metric_name = parts[0].strip()
                    threshold_value = parts[1].strip()
                    current_value = getattr(metric_data, metric_name, "N/A")
        
        message = f"{rule.name}: {rule.condition} (Current: {current_value})"
        
        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            timestamp=time.time(),
            severity=rule.severity,
            metric_type=rule.metric_type,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value
        )
        
        # データベースに保存
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO alert_history 
                    (alert_id, rule_id, timestamp, severity, metric_type, 
                     message, current_value, threshold_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert_id, rule.rule_id, alert.timestamp, rule.severity.value,
                    rule.metric_type.value, message, str(current_value), str(threshold_value)
                ))
                await db.commit()
        except Exception as e:
            print(f"❌ Alert storage error: {e}")
        
        self.active_alerts[alert_id] = alert
        print(f"🚨 Alert triggered: {message}")
        
        return alert
    
    async def _send_alert_notification(self, alert: Alert):
        """アラート通知送信"""
        try:
            # 通知チャネル（Slack、メール等）への送信
            # ここでは基本的なログ出力
            print(f"📢 Alert notification: [{alert.severity.value.upper()}] {alert.message}")
            
            # 実際の通知送信は各チャネルのハンドラで実装
            for channel, handler in self.notification_handlers.items():
                try:
                    await handler(alert)
                except Exception as e:
                    print(f"❌ Notification error [{channel}]: {e}")
                    
        except Exception as e:
            print(f"❌ Alert notification error: {e}")
    
    def register_notification_handler(self, channel: str, handler: Callable):
        """通知ハンドラ登録"""
        self.notification_handlers[channel] = handler
        print(f"📨 Notification handler registered: {channel}")
    
    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """アラート確認"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("""
                        UPDATE alert_history 
                        SET acknowledged = 1 
                        WHERE alert_id = ?
                    """, (alert_id,))
                    await db.commit()
                
                print(f"✅ Alert acknowledged: {alert_id} by {user}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Alert acknowledgment error: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, user: str) -> bool:
        """アラート解決"""
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                alert.resolved_at = time.time()
                
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("""
                        UPDATE alert_history 
                        SET resolved = 1, resolved_at = ? 
                        WHERE alert_id = ?
                    """, (alert.resolved_at, alert_id))
                    await db.commit()
                
                del self.active_alerts[alert_id]
                print(f"✅ Alert resolved: {alert_id} by {user}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Alert resolution error: {e}")
            return False


class MonitoringDashboard:
    """監視ダッシュボード"""
    
    def __init__(self, metrics_collector: MetricsCollectorEnhanced, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
    
    async def get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        try:
            # 最新のメトリクス
            latest_system = self.metrics_collector.system_metrics[-1] if self.metrics_collector.system_metrics else None
            latest_app = self.metrics_collector.application_metrics[-1] if self.metrics_collector.application_metrics else None
            
            # アクティブアラート
            active_alerts = list(self.alert_manager.active_alerts.values())
            
            # システム状態判定
            status = MonitoringStatus.HEALTHY
            if any(alert.severity == AlertSeverity.CRITICAL for alert in active_alerts):
                status = MonitoringStatus.CRITICAL
            elif any(alert.severity == AlertSeverity.HIGH for alert in active_alerts):
                status = MonitoringStatus.WARNING
            
            return {
                "status": status.value,
                "timestamp": time.time(),
                "system_metrics": {
                    "cpu_percent": latest_system.cpu_percent if latest_system else 0,
                    "memory_percent": latest_system.memory_percent if latest_system else 0,
                    "disk_percent": latest_system.disk_percent if latest_system else 0,
                    "response_time_ms": latest_system.response_time_ms if latest_system else 0,
                    "error_rate": latest_system.error_rate if latest_system else 0
                },
                "application_metrics": {
                    "session_count": latest_app.session_count if latest_app else 0,
                    "realtime_sessions": latest_app.realtime_sessions if latest_app else 0,
                    "legacy_sessions": latest_app.legacy_sessions if latest_app else 0,
                    "success_rate": (latest_app.successful_requests / 
                                   (latest_app.successful_requests + latest_app.failed_requests) * 100) 
                                   if latest_app and (latest_app.successful_requests + latest_app.failed_requests) > 0 else 100
                },
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "uptime_hours": self._calculate_uptime(),
                "health_score": self._calculate_health_score(latest_system, latest_app, active_alerts)
            }
            
        except Exception as e:
            print(f"❌ System status error: {e}")
            return {"error": str(e)}
    
    def _calculate_uptime(self) -> float:
        """稼働時間計算（仮実装）"""
        return 72.5  # 72.5時間稼働中と仮定
    
    def _calculate_health_score(self, system_metric, app_metric, alerts) -> float:
        """ヘルススコア計算"""
        try:
            score = 100.0
            
            # システムメトリクスによる減点
            if system_metric:
                if system_metric.cpu_percent > 80:
                    score -= 20
                elif system_metric.cpu_percent > 60:
                    score -= 10
                
                if system_metric.memory_percent > 85:
                    score -= 20
                elif system_metric.memory_percent > 70:
                    score -= 10
                
                if system_metric.error_rate > 5:
                    score -= 25
                elif system_metric.error_rate > 1:
                    score -= 10
            
            # アラートによる減点
            for alert in alerts:
                if alert.severity == AlertSeverity.CRITICAL:
                    score -= 30
                elif alert.severity == AlertSeverity.HIGH:
                    score -= 15
                elif alert.severity == AlertSeverity.MEDIUM:
                    score -= 5
            
            return max(0.0, min(100.0, score))
            
        except Exception:
            return 50.0  # デフォルト値
    
    async def get_metrics_history(self, hours: int = 6) -> Dict[str, Any]:
        """メトリクス履歴取得"""
        try:
            current_time = time.time()
            start_time = current_time - (hours * 3600)
            
            # システムメトリクス履歴
            system_history = [
                {
                    "timestamp": m.timestamp,
                    "cpu_percent": m.cpu_percent,
                    "memory_percent": m.memory_percent,
                    "response_time_ms": m.response_time_ms,
                    "error_rate": m.error_rate
                }
                for m in self.metrics_collector.system_metrics
                if m.timestamp > start_time
            ]
            
            # アプリケーションメトリクス履歴
            app_history = [
                {
                    "timestamp": m.timestamp,
                    "session_count": m.session_count,
                    "realtime_sessions": m.realtime_sessions,
                    "legacy_sessions": m.legacy_sessions,
                    "audio_processing_time_ms": m.audio_processing_time_ms
                }
                for m in self.metrics_collector.application_metrics
                if m.timestamp > start_time
            ]
            
            return {
                "time_range_hours": hours,
                "system_metrics": system_history,
                "application_metrics": app_history,
                "data_points": {
                    "system": len(system_history),
                    "application": len(app_history)
                }
            }
            
        except Exception as e:
            print(f"❌ Metrics history error: {e}")
            return {"error": str(e)}


class MonitoringSystem:
    """統合監視システム"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollectorEnhanced()
        self.alert_manager = AlertManager()
        self.dashboard = MonitoringDashboard(self.metrics_collector, self.alert_manager)
        
        self.monitoring_task = None
        self.running = False
        
        print("✅ MonitoringSystem initialized")
    
    async def start_monitoring(self, session_manager=None):
        """監視開始"""
        if self.running:
            print("⚠️ Monitoring already running")
            return
        
        self.running = True
        
        # メトリクス収集開始
        asyncio.create_task(self.metrics_collector.start_collection(session_manager))
        
        # アラート評価ループ開始
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        print("🔍 Monitoring system started")
    
    async def stop_monitoring(self):
        """監視停止"""
        self.running = False
        
        # メトリクス収集停止
        await self.metrics_collector.stop_collection()
        
        # 監視タスク停止
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        print("🔍 Monitoring system stopped")
    
    async def _monitoring_loop(self):
        """監視メインループ"""
        while self.running:
            try:
                # 最新メトリクス取得
                metrics = {}
                
                if self.metrics_collector.system_metrics:
                    metrics[MetricType.SYSTEM] = self.metrics_collector.system_metrics[-1]
                
                if self.metrics_collector.application_metrics:
                    metrics[MetricType.APPLICATION] = self.metrics_collector.application_metrics[-1]
                
                if self.metrics_collector.business_metrics:
                    metrics[MetricType.BUSINESS] = self.metrics_collector.business_metrics[-1]
                
                if self.metrics_collector.security_metrics:
                    metrics[MetricType.SECURITY] = self.metrics_collector.security_metrics[-1]
                
                # アラート評価
                if metrics:
                    await self.alert_manager.evaluate_metrics(metrics)
                
                # 評価間隔待機
                await asyncio.sleep(60)  # 1分間隔
                
            except Exception as e:
                print(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(10)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボードデータ取得"""
        try:
            system_status = await self.dashboard.get_system_status()
            metrics_history = await self.dashboard.get_metrics_history()
            
            return {
                "system_status": system_status,
                "metrics_history": metrics_history,
                "alert_rules": {rule_id: {
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "severity": rule.severity.value,
                    "condition": rule.condition
                } for rule_id, rule in self.alert_manager.alert_rules.items()},
                "active_alerts": [{
                    "alert_id": alert.alert_id,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "timestamp": alert.timestamp,
                    "acknowledged": alert.acknowledged
                } for alert in self.alert_manager.active_alerts.values()]
            }
            
        except Exception as e:
            print(f"❌ Dashboard data error: {e}")
            return {"error": str(e)}
    
    def record_performance_metric(self, response_time_ms: float, success: bool = True):
        """パフォーマンスメトリクス記録"""
        self.metrics_collector.record_response_time(response_time_ms)
        if not success:
            self.metrics_collector.record_error(1)


# グローバルインスタンス
monitoring_system = MonitoringSystem()


async def get_monitoring_system() -> MonitoringSystem:
    """監視システム取得"""
    return monitoring_system