"""
信頼性管理サービス

Phase 3の信頼性強化機能:
1. サーキットブレーカーパターン
2. 自動復旧機能
3. 冗長化とロードバランシング
4. 障害時の自動切り替え
5. ヘルスチェック機能
"""

import asyncio
import time
import random
import statistics
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import aiohttp
import sqlite3
import aiosqlite


class CircuitState(Enum):
    """サーキットブレーカー状態"""
    CLOSED = "closed"      # 正常状態
    OPEN = "open"          # 障害状態（リクエスト遮断）
    HALF_OPEN = "half_open"  # 回復試行状態


class ServiceStatus(Enum):
    """サービス状態"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"


class FailureType(Enum):
    """障害タイプ"""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    SERVICE_ERROR = "service_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN = "unknown"


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカー設定"""
    failure_threshold: int = 5  # 障害閾値
    success_threshold: int = 3  # 成功閾値（半開状態での回復判定）
    timeout_seconds: float = 60.0  # 開状態の持続時間
    monitoring_window_seconds: int = 300  # 監視ウィンドウ（5分）
    slow_call_duration_ms: float = 2000.0  # 遅延コール閾値


@dataclass
class HealthCheckConfig:
    """ヘルスチェック設定"""
    endpoint: str
    interval_seconds: int = 30
    timeout_seconds: float = 5.0
    expected_status: int = 200
    max_retries: int = 3
    enabled: bool = True


@dataclass
class ServiceInstance:
    """サービスインスタンス"""
    instance_id: str
    endpoint: str
    weight: int = 1
    status: ServiceStatus = ServiceStatus.HEALTHY
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def get_avg_response_time(self) -> float:
        """平均レスポンス時間取得"""
        return statistics.mean(self.response_times) if self.response_times else 0.0


class CircuitBreaker:
    """サーキットブレーカー実装"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.next_attempt_time = 0.0
        
        # 実行履歴
        self.call_history = deque(maxlen=1000)
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_opens": 0
        }
        
        print(f"🔌 CircuitBreaker '{name}' initialized")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """サーキットブレーカーを通じた関数実行"""
        self.metrics["total_calls"] += 1
        
        # 状態チェック
        if self.state == CircuitState.OPEN:
            if time.time() < self.next_attempt_time:
                raise Exception(f"Circuit breaker '{self.name}' is OPEN")
            else:
                # 半開状態に移行
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                print(f"🔌 Circuit breaker '{self.name}' moved to HALF_OPEN")
        
        start_time = time.time()
        
        try:
            # 関数実行
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # 成功時の処理
            execution_time = (time.time() - start_time) * 1000
            await self._on_success(execution_time)
            
            return result
            
        except Exception as e:
            # 失敗時の処理
            execution_time = (time.time() - start_time) * 1000
            await self._on_failure(e, execution_time)
            raise
    
    async def _on_success(self, execution_time_ms: float):
        """成功時の処理"""
        self.call_history.append({
            "timestamp": time.time(),
            "success": True,
            "execution_time_ms": execution_time_ms
        })
        
        self.metrics["successful_calls"] += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                # 回復成功
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                print(f"✅ Circuit breaker '{self.name}' recovered to CLOSED")
        else:
            # 閉状態での成功
            self.failure_count = max(0, self.failure_count - 1)
    
    async def _on_failure(self, error: Exception, execution_time_ms: float):
        """失敗時の処理"""
        self.call_history.append({
            "timestamp": time.time(),
            "success": False,
            "execution_time_ms": execution_time_ms,
            "error": str(error)
        })
        
        self.metrics["failed_calls"] += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        # 遅延コールも失敗として扱う
        if execution_time_ms > self.config.slow_call_duration_ms:
            self.failure_count += 1
        
        # 状態変更判定
        if self.state == CircuitState.HALF_OPEN:
            # 半開状態での失敗 -> 開状態に戻る
            self.state = CircuitState.OPEN
            self.next_attempt_time = time.time() + self.config.timeout_seconds
            self.metrics["circuit_opens"] += 1
            print(f"🚫 Circuit breaker '{self.name}' reopened due to failure in HALF_OPEN")
            
        elif self.state == CircuitState.CLOSED:
            # 閉状態での失敗数チェック
            recent_failures = self._get_recent_failure_count()
            if recent_failures >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.next_attempt_time = time.time() + self.config.timeout_seconds
                self.metrics["circuit_opens"] += 1
                print(f"🚫 Circuit breaker '{self.name}' opened due to {recent_failures} failures")
    
    def _get_recent_failure_count(self) -> int:
        """最近の失敗回数を取得"""
        current_time = time.time()
        window_start = current_time - self.config.monitoring_window_seconds
        
        recent_calls = [
            call for call in self.call_history
            if call["timestamp"] > window_start
        ]
        
        return len([call for call in recent_calls if not call["success"]])
    
    def get_metrics(self) -> Dict[str, Any]:
        """メトリクス取得"""
        recent_calls = list(self.call_history)[-100:]  # 最新100件
        
        if recent_calls:
            success_rate = len([c for c in recent_calls if c["success"]]) / len(recent_calls) * 100
            avg_response_time = statistics.mean([c["execution_time_ms"] for c in recent_calls])
        else:
            success_rate = 0.0
            avg_response_time = 0.0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "next_attempt_time": self.next_attempt_time,
            "metrics": self.metrics,
            "recent_success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds
            }
        }


class LoadBalancer:
    """ロードバランサー"""
    
    def __init__(self, name: str):
        self.name = name
        self.instances: List[ServiceInstance] = []
        self.current_index = 0  # ラウンドロビン用
        
    def add_instance(self, instance: ServiceInstance):
        """サービスインスタンス追加"""
        self.instances.append(instance)
        print(f"⚖️ Instance added to load balancer '{self.name}': {instance.instance_id}")
    
    def remove_instance(self, instance_id: str):
        """サービスインスタンス削除"""
        self.instances = [i for i in self.instances if i.instance_id != instance_id]
        print(f"⚖️ Instance removed from load balancer '{self.name}': {instance_id}")
    
    def get_healthy_instances(self) -> List[ServiceInstance]:
        """健全なインスタンス取得"""
        return [i for i in self.instances if i.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]]
    
    def select_instance(self, strategy: str = "weighted_round_robin") -> Optional[ServiceInstance]:
        """インスタンス選択"""
        healthy_instances = self.get_healthy_instances()
        
        if not healthy_instances:
            return None
        
        if strategy == "round_robin":
            # ラウンドロビン
            instance = healthy_instances[self.current_index % len(healthy_instances)]
            self.current_index += 1
            return instance
            
        elif strategy == "weighted_round_robin":
            # 重み付きラウンドロビン
            total_weight = sum(i.weight for i in healthy_instances)
            if total_weight == 0:
                return healthy_instances[0]
            
            # 重みに基づく選択
            weights = [i.weight / total_weight for i in healthy_instances]
            selected_instance = random.choices(healthy_instances, weights=weights)[0]
            return selected_instance
            
        elif strategy == "least_response_time":
            # 最小レスポンス時間
            return min(healthy_instances, key=lambda i: i.get_avg_response_time())
            
        else:
            # デフォルトは最初の健全なインスタンス
            return healthy_instances[0]
    
    def update_instance_status(self, instance_id: str, status: ServiceStatus, response_time_ms: float = 0):
        """インスタンス状態更新"""
        for instance in self.instances:
            if instance.instance_id == instance_id:
                instance.status = status
                instance.last_health_check = time.time()
                
                if response_time_ms > 0:
                    instance.response_times.append(response_time_ms)
                
                if status != ServiceStatus.HEALTHY:
                    instance.consecutive_failures += 1
                else:
                    instance.consecutive_failures = 0
                
                break
    
    def get_status(self) -> Dict[str, Any]:
        """ロードバランサー状態取得"""
        healthy_count = len([i for i in self.instances if i.status == ServiceStatus.HEALTHY])
        degraded_count = len([i for i in self.instances if i.status == ServiceStatus.DEGRADED])
        unhealthy_count = len([i for i in self.instances if i.status in [ServiceStatus.UNHEALTHY, ServiceStatus.DOWN]])
        
        return {
            "name": self.name,
            "total_instances": len(self.instances),
            "healthy_instances": healthy_count,
            "degraded_instances": degraded_count,
            "unhealthy_instances": unhealthy_count,
            "instances": [
                {
                    "instance_id": i.instance_id,
                    "endpoint": i.endpoint,
                    "status": i.status.value,
                    "weight": i.weight,
                    "consecutive_failures": i.consecutive_failures,
                    "avg_response_time_ms": i.get_avg_response_time()
                }
                for i in self.instances
            ]
        }


class HealthChecker:
    """ヘルスチェック機能"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheckConfig] = {}
        self.check_results: Dict[str, deque] = {}
        self.running = False
        
    def register_health_check(self, service_name: str, config: HealthCheckConfig):
        """ヘルスチェック登録"""
        self.health_checks[service_name] = config
        self.check_results[service_name] = deque(maxlen=100)
        print(f"🏥 Health check registered for service: {service_name}")
    
    async def perform_health_check(self, service_name: str) -> Dict[str, Any]:
        """ヘルスチェック実行"""
        if service_name not in self.health_checks:
            return {"error": f"Health check not configured for {service_name}"}
        
        config = self.health_checks[service_name]
        
        if not config.enabled:
            return {"status": "disabled"}
        
        start_time = time.time()
        
        for attempt in range(config.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(config.endpoint) as response:
                        response_time_ms = (time.time() - start_time) * 1000
                        
                        result = {
                            "service_name": service_name,
                            "timestamp": time.time(),
                            "status_code": response.status,
                            "response_time_ms": response_time_ms,
                            "attempt": attempt + 1,
                            "healthy": response.status == config.expected_status,
                            "endpoint": config.endpoint
                        }
                        
                        self.check_results[service_name].append(result)
                        
                        if response.status == config.expected_status:
                            return result
                        
            except asyncio.TimeoutError:
                result = {
                    "service_name": service_name,
                    "timestamp": time.time(),
                    "error": "timeout",
                    "response_time_ms": config.timeout_seconds * 1000,
                    "attempt": attempt + 1,
                    "healthy": False,
                    "endpoint": config.endpoint
                }
                
            except Exception as e:
                result = {
                    "service_name": service_name,
                    "timestamp": time.time(),
                    "error": str(e),
                    "attempt": attempt + 1,
                    "healthy": False,
                    "endpoint": config.endpoint
                }
            
            # リトライ前の待機
            if attempt < config.max_retries - 1:
                await asyncio.sleep(1)
        
        # 全試行失敗
        self.check_results[service_name].append(result)
        return result
    
    async def start_monitoring(self):
        """ヘルスチェック監視開始"""
        if self.running:
            return
        
        self.running = True
        print("🏥 Health check monitoring started")
        
        while self.running:
            try:
                # 全サービスのヘルスチェック実行
                tasks = []
                for service_name in self.health_checks.keys():
                    task = asyncio.create_task(self.perform_health_check(service_name))
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # 最短間隔まで待機
                min_interval = min((config.interval_seconds for config in self.health_checks.values()), default=30)
                await asyncio.sleep(min_interval)
                
            except Exception as e:
                print(f"❌ Health check monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def stop_monitoring(self):
        """ヘルスチェック監視停止"""
        self.running = False
        print("🏥 Health check monitoring stopped")
    
    def get_service_health(self, service_name: str) -> Dict[str, Any]:
        """サービスヘルス状態取得"""
        if service_name not in self.check_results:
            return {"error": f"No health check data for {service_name}"}
        
        results = list(self.check_results[service_name])
        
        if not results:
            return {"error": f"No health check results for {service_name}"}
        
        # 最新結果
        latest = results[-1]
        
        # 成功率計算（過去10回）
        recent_results = results[-10:]
        success_count = len([r for r in recent_results if r.get("healthy", False)])
        success_rate = (success_count / len(recent_results)) * 100 if recent_results else 0
        
        # 平均レスポンス時間
        response_times = [r.get("response_time_ms", 0) for r in recent_results if "response_time_ms" in r]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        return {
            "service_name": service_name,
            "latest_check": latest,
            "success_rate_percent": success_rate,
            "avg_response_time_ms": avg_response_time,
            "total_checks": len(results),
            "recent_checks": len(recent_results)
        }


class ReliabilityManager:
    """統合信頼性管理サービス"""
    
    def __init__(self, db_path: str = "data/reliability.db"):
        self.db_path = db_path
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.health_checker = HealthChecker()
        
        # 自動復旧設定
        self.auto_recovery_enabled = True
        self.recovery_check_interval = 60  # 1分間隔
        
        self._initialized = False
        self._lock = asyncio.Lock()
        
        print("✅ ReliabilityManager initialized")
    
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
        """信頼性管理テーブル作成"""
        async with aiosqlite.connect(self.db_path) as db:
            # サーキットブレーカー履歴
            await db.execute("""
                CREATE TABLE IF NOT EXISTS circuit_breaker_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    breaker_name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    previous_state TEXT,
                    new_state TEXT,
                    failure_count INTEGER,
                    details TEXT
                )
            """)
            
            # ヘルスチェック履歴
            await db.execute("""
                CREATE TABLE IF NOT EXISTS health_check_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    healthy BOOLEAN NOT NULL,
                    response_time_ms REAL,
                    status_code INTEGER,
                    error_message TEXT,
                    endpoint TEXT
                )
            """)
            
            await db.commit()
    
    def create_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """サーキットブレーカー作成"""
        circuit_breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """サーキットブレーカー取得"""
        return self.circuit_breakers.get(name)
    
    def create_load_balancer(self, name: str) -> LoadBalancer:
        """ロードバランサー作成"""
        load_balancer = LoadBalancer(name)
        self.load_balancers[name] = load_balancer
        return load_balancer
    
    def get_load_balancer(self, name: str) -> Optional[LoadBalancer]:
        """ロードバランサー取得"""
        return self.load_balancers.get(name)
    
    async def execute_with_reliability(
        self,
        func: Callable,
        circuit_breaker_name: str,
        load_balancer_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """信頼性機能を使った関数実行"""
        try:
            # ロードバランサーでインスタンス選択
            if load_balancer_name:
                load_balancer = self.get_load_balancer(load_balancer_name)
                if load_balancer:
                    instance = load_balancer.select_instance()
                    if not instance:
                        raise Exception(f"No healthy instances available in load balancer {load_balancer_name}")
                    
                    # インスタンス情報を引数に追加
                    kwargs["selected_instance"] = instance
            
            # サーキットブレーカーで実行
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
            if circuit_breaker:
                return await circuit_breaker.call(func, *args, **kwargs)
            else:
                # サーキットブレーカーがない場合は直接実行
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
        except Exception as e:
            # エラー時のインスタンス状態更新
            if load_balancer_name and "selected_instance" in kwargs:
                load_balancer = self.get_load_balancer(load_balancer_name)
                if load_balancer:
                    instance = kwargs["selected_instance"]
                    load_balancer.update_instance_status(
                        instance.instance_id,
                        ServiceStatus.UNHEALTHY
                    )
            
            raise
    
    async def start_reliability_monitoring(self):
        """信頼性監視開始"""
        # ヘルスチェック開始
        await self.health_checker.start_monitoring()
        
        # 自動復旧監視開始
        if self.auto_recovery_enabled:
            asyncio.create_task(self._auto_recovery_loop())
        
        print("🔄 Reliability monitoring started")
    
    async def stop_reliability_monitoring(self):
        """信頼性監視停止"""
        await self.health_checker.stop_monitoring()
        print("🔄 Reliability monitoring stopped")
    
    async def _auto_recovery_loop(self):
        """自動復旧ループ"""
        while self.auto_recovery_enabled:
            try:
                await self._check_recovery_conditions()
                await asyncio.sleep(self.recovery_check_interval)
                
            except Exception as e:
                print(f"❌ Auto recovery loop error: {e}")
                await asyncio.sleep(10)
    
    async def _check_recovery_conditions(self):
        """復旧条件チェック"""
        current_time = time.time()
        
        # サーキットブレーカーの自動復旧チェック
        for name, cb in self.circuit_breakers.items():
            if cb.state == CircuitState.OPEN and current_time >= cb.next_attempt_time:
                print(f"🔄 Attempting auto-recovery for circuit breaker: {name}")
                # 半開状態に移行（次回呼び出し時）
        
        # ロードバランサーインスタンスの復旧チェック
        for name, lb in self.load_balancers.items():
            for instance in lb.instances:
                if instance.status == ServiceStatus.UNHEALTHY:
                    # ヘルスチェック実行
                    if instance.instance_id in self.health_checker.health_checks:
                        health_result = await self.health_checker.perform_health_check(instance.instance_id)
                        if health_result.get("healthy", False):
                            lb.update_instance_status(instance.instance_id, ServiceStatus.HEALTHY)
                            print(f"✅ Instance recovered: {instance.instance_id}")
    
    async def get_reliability_status(self) -> Dict[str, Any]:
        """信頼性状態取得"""
        await self._ensure_initialized()
        
        try:
            # サーキットブレーカー状態
            circuit_breaker_status = {}
            for name, cb in self.circuit_breakers.items():
                circuit_breaker_status[name] = cb.get_metrics()
            
            # ロードバランサー状態
            load_balancer_status = {}
            for name, lb in self.load_balancers.items():
                load_balancer_status[name] = lb.get_status()
            
            # ヘルスチェック状態
            health_check_status = {}
            for service_name in self.health_checker.health_checks.keys():
                health_check_status[service_name] = self.health_checker.get_service_health(service_name)
            
            # 全体サマリー
            total_circuit_breakers = len(self.circuit_breakers)
            open_circuit_breakers = len([cb for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN])
            
            total_instances = sum(len(lb.instances) for lb in self.load_balancers.values())
            healthy_instances = sum(
                len([i for i in lb.instances if i.status == ServiceStatus.HEALTHY])
                for lb in self.load_balancers.values()
            )
            
            return {
                "timestamp": time.time(),
                "overall_health": "healthy" if open_circuit_breakers == 0 and healthy_instances == total_instances else "degraded",
                "summary": {
                    "circuit_breakers": {
                        "total": total_circuit_breakers,
                        "open": open_circuit_breakers,
                        "closed": total_circuit_breakers - open_circuit_breakers
                    },
                    "service_instances": {
                        "total": total_instances,
                        "healthy": healthy_instances,
                        "unhealthy": total_instances - healthy_instances
                    },
                    "auto_recovery_enabled": self.auto_recovery_enabled
                },
                "circuit_breakers": circuit_breaker_status,
                "load_balancers": load_balancer_status,
                "health_checks": health_check_status
            }
            
        except Exception as e:
            print(f"❌ Reliability status error: {e}")
            return {"error": str(e)}


# グローバルインスタンス
reliability_manager = ReliabilityManager()


async def get_reliability_manager() -> ReliabilityManager:
    """信頼性管理サービス取得"""
    return reliability_manager


# 使用例とデフォルト設定
async def setup_default_reliability():
    """デフォルト信頼性設定"""
    rm = await get_reliability_manager()
    
    # OpenAI Realtime API用サーキットブレーカー
    realtime_config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=30.0,
        monitoring_window_seconds=300
    )
    rm.create_circuit_breaker("openai_realtime", realtime_config)
    
    # レガシーAPI用サーキットブレーカー
    legacy_config = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout_seconds=60.0
    )
    rm.create_circuit_breaker("legacy_api", legacy_config)
    
    # Slack通知用サーキットブレーカー
    slack_config = CircuitBreakerConfig(
        failure_threshold=2,
        success_threshold=1,
        timeout_seconds=15.0
    )
    rm.create_circuit_breaker("slack_notifications", slack_config)
    
    print("🔧 Default reliability configuration applied")