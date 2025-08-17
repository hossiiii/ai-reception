"""
Phase 3統合テスト

Phase 3の最適化・本格運用機能の包括的テスト:
1. パフォーマンス最適化機能テスト
2. コスト管理システムテスト
3. 監視・アラートシステムテスト
4. 信頼性管理機能テスト
5. セキュリティ機能テスト
6. 負荷テスト・パフォーマンステスト
"""

import asyncio
import time
import random
import statistics
import json
from typing import Dict, Any, List
import aiohttp
import pytest
from concurrent.futures import ThreadPoolExecutor

# Phase 3 サービスのインポート
from app.services.performance_optimizer import PerformanceOptimizer
from app.services.cost_optimizer import CostOptimizer
from app.services.monitoring_system import MonitoringSystem
from app.services.reliability_manager import ReliabilityManager, CircuitBreakerConfig
from app.services.security_manager import SecurityManager


class Phase3IntegrationTester:
    """Phase 3統合テスト実行"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = {}
        self.performance_metrics = []
        self.error_count = 0
        self.total_requests = 0
        
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """包括的テスト実行"""
        print("🧪 Starting Phase 3 Comprehensive Integration Test")
        print("=" * 60)
        
        test_results = {}
        
        # 1. 基本機能テスト
        print("1️⃣ Testing Basic Functionality...")
        test_results["basic_functionality"] = await self._test_basic_functionality()
        
        # 2. パフォーマンス最適化テスト
        print("2️⃣ Testing Performance Optimization...")
        test_results["performance_optimization"] = await self._test_performance_optimization()
        
        # 3. コスト管理テスト
        print("3️⃣ Testing Cost Management...")
        test_results["cost_management"] = await self._test_cost_management()
        
        # 4. 監視・アラートテスト
        print("4️⃣ Testing Monitoring & Alerting...")
        test_results["monitoring_alerting"] = await self._test_monitoring_alerting()
        
        # 5. 信頼性管理テスト
        print("5️⃣ Testing Reliability Management...")
        test_results["reliability_management"] = await self._test_reliability_management()
        
        # 6. セキュリティテスト
        print("6️⃣ Testing Security Features...")
        test_results["security"] = await self._test_security_features()
        
        # 7. 負荷テスト
        print("7️⃣ Running Load Tests...")
        test_results["load_testing"] = await self._run_load_tests()
        
        # 8. パフォーマンステスト
        print("8️⃣ Running Performance Tests...")
        test_results["performance_testing"] = await self._run_performance_tests()
        
        # 9. 統合シナリオテスト
        print("9️⃣ Running Integration Scenarios...")
        test_results["integration_scenarios"] = await self._run_integration_scenarios()
        
        # 10. 本格運用準備テスト
        print("🔟 Testing Production Readiness...")
        test_results["production_readiness"] = await self._test_production_readiness()
        
        # 最終結果サマリー
        test_results["summary"] = self._generate_test_summary(test_results)
        
        print("=" * 60)
        print("✅ Phase 3 Comprehensive Integration Test Completed")
        
        return test_results
    
    async def _test_basic_functionality(self) -> Dict[str, Any]:
        """基本機能テスト"""
        results = {}
        
        try:
            # ヘルスチェック
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health/") as response:
                    health_basic = await response.json()
                    results["health_basic"] = {
                        "status": response.status == 200,
                        "response_time_ms": 0,  # 実装省略
                        "data": health_basic
                    }
                
                async with session.get(f"{self.base_url}/health/detailed") as response:
                    health_detailed = await response.json()
                    results["health_detailed"] = {
                        "status": response.status == 200,
                        "system_healthy": health_detailed.get("status") == "healthy",
                        "data": health_detailed
                    }
                
                # Phase 3 管理API
                async with session.get(f"{self.base_url}/api/v3/management/overview") as response:
                    overview = await response.json()
                    results["phase3_overview"] = {
                        "status": response.status == 200,
                        "health_level": overview.get("overall_health", {}).get("level"),
                        "data": overview
                    }
            
            results["overall_success"] = all(
                test.get("status", False) for test in results.values() 
                if isinstance(test, dict)
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_performance_optimization(self) -> Dict[str, Any]:
        """パフォーマンス最適化テスト"""
        results = {}
        
        try:
            performance_optimizer = PerformanceOptimizer()
            
            # 最適化レベルテスト
            for level in ["aggressive", "balanced", "conservative"]:
                result = await performance_optimizer.adjust_optimization_level(level)
                results[f"optimization_level_{level}"] = {
                    "success": result.get("success", False),
                    "settings": result.get("settings", {})
                }
            
            # 音声処理最適化テスト
            test_audio_data = b"test_audio_data" * 1000  # 1KB のテストデータ
            optimization_result = await performance_optimizer.optimize_audio_processing(
                test_audio_data, "test_session"
            )
            
            results["audio_optimization"] = {
                "success": optimization_result.get("success", False),
                "processing_time_ms": optimization_result.get("processing_time_ms", 0),
                "optimization_level": optimization_result.get("optimization_level")
            }
            
            # パフォーマンスサマリー
            performance_summary = await performance_optimizer.get_performance_summary()
            results["performance_summary"] = {
                "available": performance_summary is not None,
                "cpu_under_pressure": performance_summary.get("performance", {}).get("cpu_under_pressure", False)
            }
            
            results["overall_success"] = all(
                test.get("success", True) for test in results.values() 
                if isinstance(test, dict)
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_cost_management(self) -> Dict[str, Any]:
        """コスト管理テスト"""
        results = {}
        
        try:
            cost_optimizer = CostOptimizer()
            
            # コスト記録テスト
            cost_record_result = await cost_optimizer.record_cost_usage(
                session_id="test_session",
                processing_mode="realtime",
                audio_duration_seconds=30.0,
                tokens_input=100,
                tokens_output=150,
                function_calls=2
            )
            
            results["cost_recording"] = {
                "success": cost_record_result.get("success", False),
                "total_cost": cost_record_result.get("total_cost", 0)
            }
            
            # コストサマリーテスト
            cost_summary = await cost_optimizer.get_cost_summary(24)
            results["cost_summary"] = {
                "available": cost_summary is not None,
                "total_cost": cost_summary.get("total_cost", 0)
            }
            
            # コスト予測テスト
            cost_prediction = await cost_optimizer.predict_cost_trend(24)
            results["cost_prediction"] = {
                "available": cost_prediction is not None,
                "predicted_cost": cost_prediction.get("predicted_total_cost", 0)
            }
            
            # コスト制限テスト
            limit_update_result = await cost_optimizer.update_cost_limits({
                "hourly_limit": 100.0,
                "daily_limit": 1000.0
            })
            results["cost_limits"] = {
                "success": limit_update_result.get("success", False)
            }
            
            results["overall_success"] = all(
                test.get("success", True) for test in results.values() 
                if isinstance(test, dict)
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_monitoring_alerting(self) -> Dict[str, Any]:
        """監視・アラートテスト"""
        results = {}
        
        try:
            monitoring_system = MonitoringSystem()
            
            # 監視開始テスト
            await monitoring_system.start_monitoring()
            results["monitoring_start"] = {"success": True}
            
            # ダッシュボードデータテスト
            dashboard_data = await monitoring_system.get_dashboard_data()
            results["dashboard_data"] = {
                "available": dashboard_data is not None,
                "has_system_status": "system_status" in dashboard_data
            }
            
            # パフォーマンスメトリクス記録テスト
            monitoring_system.record_performance_metric(250.0, True)
            monitoring_system.record_performance_metric(180.0, True)
            monitoring_system.record_performance_metric(320.0, False)
            
            results["metrics_recording"] = {"success": True}
            
            # アラート管理テスト
            test_alert_id = "test_alert_001"
            acknowledge_result = await monitoring_system.alert_manager.acknowledge_alert(
                test_alert_id, "test_user"
            )
            results["alert_management"] = {
                "acknowledge_attempted": True,
                "result": acknowledge_result
            }
            
            results["overall_success"] = True
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_reliability_management(self) -> Dict[str, Any]:
        """信頼性管理テスト"""
        results = {}
        
        try:
            reliability_manager = ReliabilityManager()
            
            # サーキットブレーカー作成テスト
            test_config = CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=30.0
            )
            
            circuit_breaker = reliability_manager.create_circuit_breaker("test_cb", test_config)
            results["circuit_breaker_creation"] = {
                "success": circuit_breaker is not None,
                "name": "test_cb"
            }
            
            # サーキットブレーカー機能テスト
            async def test_function():
                return "success"
            
            try:
                result = await circuit_breaker.call(test_function)
                results["circuit_breaker_function"] = {
                    "success": result == "success",
                    "state": circuit_breaker.state.value
                }
            except Exception:
                results["circuit_breaker_function"] = {
                    "success": False,
                    "state": circuit_breaker.state.value
                }
            
            # 信頼性監視開始テスト
            await reliability_manager.start_reliability_monitoring()
            results["reliability_monitoring"] = {"success": True}
            
            # 信頼性状態取得テスト
            reliability_status = await reliability_manager.get_reliability_status()
            results["reliability_status"] = {
                "available": reliability_status is not None,
                "overall_health": reliability_status.get("overall_health")
            }
            
            results["overall_success"] = all(
                test.get("success", True) for test in results.values() 
                if isinstance(test, dict)
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_security_features(self) -> Dict[str, Any]:
        """セキュリティ機能テスト"""
        results = {}
        
        try:
            security_manager = SecurityManager()
            
            # API キー生成テスト
            api_key = security_manager.api_key_manager.generate_api_key(
                "test_user", ["api_access"], 365
            )
            results["api_key_generation"] = {
                "success": api_key is not None,
                "key_format_valid": api_key.startswith("ai-rec-") if api_key else False
            }
            
            # API キー検証テスト
            if api_key:
                key_data = security_manager.api_key_manager.validate_api_key(api_key)
                results["api_key_validation"] = {
                    "success": key_data is not None,
                    "user_id": key_data.get("user_id") if key_data else None
                }
            
            # IP フィルタリングテスト
            test_ip = "192.168.1.100"
            security_manager.ip_filter.add_to_blacklist(test_ip, "test")
            ip_check = security_manager.ip_filter.check_ip_access(test_ip)
            results["ip_filtering"] = {
                "success": not ip_check["allowed"],
                "reason": ip_check["reason"]
            }
            
            # レート制限テスト
            rate_limit_result = await security_manager.rate_limiter.check_rate_limit(
                "test_identifier", "general_api"
            )
            results["rate_limiting"] = {
                "success": rate_limit_result.get("allowed", False),
                "remaining": rate_limit_result.get("remaining_minute", 0)
            }
            
            # セキュリティダッシュボードテスト
            security_dashboard = await security_manager.get_security_dashboard()
            results["security_dashboard"] = {
                "available": security_dashboard is not None,
                "has_security_summary": "security_summary" in security_dashboard
            }
            
            results["overall_success"] = all(
                test.get("success", True) for test in results.values() 
                if isinstance(test, dict)
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _run_load_tests(self) -> Dict[str, Any]:
        """負荷テスト実行"""
        results = {}
        
        try:
            print("   🔄 Running concurrent request test...")
            
            # 並行リクエストテスト
            concurrent_results = await self._test_concurrent_requests(50, 10)
            results["concurrent_requests"] = concurrent_results
            
            print("   🔄 Running sustained load test...")
            
            # 持続負荷テスト
            sustained_results = await self._test_sustained_load(100, 60)
            results["sustained_load"] = sustained_results
            
            print("   🔄 Running burst load test...")
            
            # バースト負荷テスト
            burst_results = await self._test_burst_load(200, 5)
            results["burst_load"] = burst_results
            
            results["overall_success"] = all(
                test.get("success", False) for test in results.values()
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_concurrent_requests(self, num_requests: int, concurrency: int) -> Dict[str, Any]:
        """並行リクエストテスト"""
        semaphore = asyncio.Semaphore(concurrency)
        response_times = []
        success_count = 0
        error_count = 0
        
        async def make_request():
            async with semaphore:
                start_time = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}/health/") as response:
                            await response.json()
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                            return response.status == 200
                except Exception:
                    return False
        
        # 並行実行
        tasks = [make_request() for _ in range(num_requests)]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results_list:
            if isinstance(result, Exception):
                error_count += 1
            elif result:
                success_count += 1
            else:
                error_count += 1
        
        return {
            "success": success_count > num_requests * 0.95,  # 95%成功率
            "total_requests": num_requests,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": (success_count / num_requests) * 100,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0,
            "min_response_time_ms": min(response_times) if response_times else 0
        }
    
    async def _test_sustained_load(self, rps: int, duration_seconds: int) -> Dict[str, Any]:
        """持続負荷テスト"""
        interval = 1.0 / rps
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        response_times = []
        success_count = 0
        error_count = 0
        
        async def make_sustained_request():
            nonlocal success_count, error_count
            request_start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/health/") as response:
                        await response.json()
                        response_time = (time.time() - request_start) * 1000
                        response_times.append(response_time)
                        if response.status == 200:
                            success_count += 1
                        else:
                            error_count += 1
            except Exception:
                error_count += 1
        
        # 持続的リクエスト送信
        while time.time() < end_time:
            asyncio.create_task(make_sustained_request())
            await asyncio.sleep(interval)
        
        # 残りのレスポンス待機
        await asyncio.sleep(2)
        
        total_requests = success_count + error_count
        
        return {
            "success": success_count > total_requests * 0.95 if total_requests > 0 else False,
            "duration_seconds": duration_seconds,
            "target_rps": rps,
            "actual_rps": total_requests / duration_seconds if duration_seconds > 0 else 0,
            "total_requests": total_requests,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": (success_count / total_requests) * 100 if total_requests > 0 else 0,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0
        }
    
    async def _test_burst_load(self, burst_size: int, burst_duration_seconds: int) -> Dict[str, Any]:
        """バースト負荷テスト"""
        response_times = []
        success_count = 0
        error_count = 0
        
        async def burst_request():
            nonlocal success_count, error_count
            start_time = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/health/") as response:
                        await response.json()
                        response_time = (time.time() - start_time) * 1000
                        response_times.append(response_time)
                        if response.status == 200:
                            success_count += 1
                        else:
                            error_count += 1
            except Exception:
                error_count += 1
        
        # バーストリクエスト実行
        start_time = time.time()
        tasks = [burst_request() for _ in range(burst_size)]
        await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        return {
            "success": success_count > burst_size * 0.9,  # 90%成功率
            "burst_size": burst_size,
            "actual_duration_seconds": total_time,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": (success_count / burst_size) * 100,
            "requests_per_second": burst_size / total_time if total_time > 0 else 0,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0
        }
    
    async def _run_performance_tests(self) -> Dict[str, Any]:
        """パフォーマンステスト実行"""
        results = {}
        
        try:
            # レスポンス時間テスト
            response_time_results = await self._test_response_times()
            results["response_times"] = response_time_results
            
            # スループットテスト
            throughput_results = await self._test_throughput()
            results["throughput"] = throughput_results
            
            # リソース使用量テスト
            resource_usage_results = await self._test_resource_usage()
            results["resource_usage"] = resource_usage_results
            
            results["overall_success"] = all(
                test.get("success", False) for test in results.values()
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_response_times(self) -> Dict[str, Any]:
        """レスポンス時間テスト"""
        endpoints = [
            "/health/",
            "/health/detailed",
            "/health/performance",
            "/api/v3/management/overview"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            endpoint_times = []
            success_count = 0
            
            for _ in range(10):  # 各エンドポイントを10回テスト
                start_time = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            await response.json()
                            response_time = (time.time() - start_time) * 1000
                            endpoint_times.append(response_time)
                            if response.status == 200:
                                success_count += 1
                except Exception:
                    pass
            
            results[endpoint] = {
                "success": success_count >= 9,  # 90%成功率
                "avg_response_time_ms": statistics.mean(endpoint_times) if endpoint_times else 0,
                "max_response_time_ms": max(endpoint_times) if endpoint_times else 0,
                "success_rate": (success_count / 10) * 100
            }
        
        # 全体評価
        overall_avg = statistics.mean([
            r.get("avg_response_time_ms", 0) for r in results.values()
        ])
        
        results["overall"] = {
            "success": overall_avg < 1000,  # 1秒以内
            "avg_response_time_ms": overall_avg
        }
        
        return results
    
    async def _test_throughput(self) -> Dict[str, Any]:
        """スループットテスト"""
        duration_seconds = 30
        max_concurrent = 50
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        success_count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def throughput_request():
            nonlocal request_count, success_count
            async with semaphore:
                request_count += 1
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}/health/") as response:
                            await response.json()
                            if response.status == 200:
                                success_count += 1
                except Exception:
                    pass
        
        # スループットテスト実行
        tasks = []
        while time.time() < end_time:
            task = asyncio.create_task(throughput_request())
            tasks.append(task)
            await asyncio.sleep(0.01)  # 10ms間隔
        
        # 残りのタスク完了待機
        await asyncio.gather(*tasks, return_exceptions=True)
        
        actual_duration = time.time() - start_time
        throughput = success_count / actual_duration
        
        return {
            "success": throughput >= 20,  # 最低20 RPS
            "duration_seconds": actual_duration,
            "total_requests": request_count,
            "successful_requests": success_count,
            "throughput_rps": throughput,
            "success_rate": (success_count / request_count) * 100 if request_count > 0 else 0
        }
    
    async def _test_resource_usage(self) -> Dict[str, Any]:
        """リソース使用量テスト"""
        try:
            import psutil
            
            # テスト開始前のリソース状況
            initial_cpu = psutil.cpu_percent(interval=1)
            initial_memory = psutil.virtual_memory().percent
            
            # 負荷をかけながらリソース監視
            resource_measurements = []
            
            async def monitor_resources():
                for _ in range(10):  # 10秒間監視
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory_percent = psutil.virtual_memory().percent
                    resource_measurements.append({
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory_percent
                    })
                    await asyncio.sleep(1)
            
            # 負荷生成
            async def generate_load():
                tasks = []
                for _ in range(20):  # 20並行リクエスト
                    async def load_request():
                        async with aiohttp.ClientSession() as session:
                            async with session.get(f"{self.base_url}/health/detailed") as response:
                                await response.json()
                    
                    tasks.append(asyncio.create_task(load_request()))
                    await asyncio.sleep(0.1)
                
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 監視と負荷を並行実行
            await asyncio.gather(
                monitor_resources(),
                generate_load(),
                return_exceptions=True
            )
            
            # 結果分析
            if resource_measurements:
                avg_cpu = statistics.mean([m["cpu_percent"] for m in resource_measurements])
                max_cpu = max([m["cpu_percent"] for m in resource_measurements])
                avg_memory = statistics.mean([m["memory_percent"] for m in resource_measurements])
                max_memory = max([m["memory_percent"] for m in resource_measurements])
                
                return {
                    "success": avg_cpu < 80 and avg_memory < 85,  # リソース使用率制限
                    "initial_cpu_percent": initial_cpu,
                    "initial_memory_percent": initial_memory,
                    "avg_cpu_percent": avg_cpu,
                    "max_cpu_percent": max_cpu,
                    "avg_memory_percent": avg_memory,
                    "max_memory_percent": max_memory,
                    "cpu_increase": avg_cpu - initial_cpu,
                    "memory_increase": avg_memory - initial_memory
                }
            else:
                return {"success": False, "error": "No measurements collected"}
                
        except ImportError:
            return {"success": False, "error": "psutil not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _run_integration_scenarios(self) -> Dict[str, Any]:
        """統合シナリオテスト"""
        results = {}
        
        try:
            # シナリオ1: 通常運用シミュレーション
            normal_operation = await self._test_normal_operation_scenario()
            results["normal_operation"] = normal_operation
            
            # シナリオ2: 高負荷運用シミュレーション
            high_load_operation = await self._test_high_load_scenario()
            results["high_load_operation"] = high_load_operation
            
            # シナリオ3: 障害復旧シミュレーション
            failure_recovery = await self._test_failure_recovery_scenario()
            results["failure_recovery"] = failure_recovery
            
            results["overall_success"] = all(
                test.get("success", False) for test in results.values()
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_normal_operation_scenario(self) -> Dict[str, Any]:
        """通常運用シナリオテスト"""
        # 通常レベルの負荷で全機能をテスト
        tasks = []
        
        # ヘルスチェック
        tasks.append(self._make_request("/health/"))
        tasks.append(self._make_request("/health/detailed"))
        
        # Phase 3 管理機能
        tasks.append(self._make_request("/api/v3/management/overview"))
        tasks.append(self._make_request("/health/performance"))
        tasks.append(self._make_request("/health/cost"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.get("success", False))
        
        return {
            "success": success_count >= len(tasks) * 0.9,  # 90%成功率
            "total_tests": len(tasks),
            "successful_tests": success_count,
            "success_rate": (success_count / len(tasks)) * 100
        }
    
    async def _test_high_load_scenario(self) -> Dict[str, Any]:
        """高負荷シナリオテスト"""
        # 高負荷状況での安定性テスト
        concurrent_requests = 100
        duration_seconds = 30
        
        semaphore = asyncio.Semaphore(concurrent_requests)
        success_count = 0
        total_count = 0
        
        async def high_load_request():
            nonlocal success_count, total_count
            async with semaphore:
                total_count += 1
                try:
                    result = await self._make_request("/health/detailed")
                    if result.get("success", False):
                        success_count += 1
                except Exception:
                    pass
        
        # 高負荷リクエスト実行
        start_time = time.time()
        tasks = []
        
        while time.time() - start_time < duration_seconds:
            task = asyncio.create_task(high_load_request())
            tasks.append(task)
            await asyncio.sleep(0.05)  # 50ms間隔
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "success": success_count >= total_count * 0.85,  # 85%成功率
            "duration_seconds": duration_seconds,
            "total_requests": total_count,
            "successful_requests": success_count,
            "success_rate": (success_count / total_count) * 100 if total_count > 0 else 0,
            "requests_per_second": total_count / duration_seconds
        }
    
    async def _test_failure_recovery_scenario(self) -> Dict[str, Any]:
        """障害復旧シナリオテスト"""
        # 意図的にエラーを発生させて復旧をテスト
        results = {}
        
        try:
            # 正常状態確認
            normal_result = await self._make_request("/health/")
            results["initial_state"] = {"healthy": normal_result.get("success", False)}
            
            # 無効なエンドポイントでエラー発生
            error_requests = []
            for _ in range(5):
                try:
                    await self._make_request("/invalid/endpoint")
                except:
                    pass
                error_requests.append(True)
            
            results["error_generation"] = {"errors_generated": len(error_requests)}
            
            # 復旧確認
            await asyncio.sleep(2)  # 復旧待機
            recovery_result = await self._make_request("/health/")
            results["recovery_state"] = {"recovered": recovery_result.get("success", False)}
            
            results["overall_success"] = (
                results["initial_state"]["healthy"] and 
                results["recovery_state"]["recovered"]
            )
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _test_production_readiness(self) -> Dict[str, Any]:
        """本格運用準備テスト"""
        results = {}
        
        try:
            # Kubernetes準備状況
            k8s_health = await self._make_request("/health/k8s/healthz")
            results["k8s_healthz"] = k8s_health.get("success", False)
            
            k8s_ready = await self._make_request("/health/k8s/readyz")
            results["k8s_readyz"] = k8s_ready.get("success", False)
            
            # 依存サービス状況
            dependencies = await self._make_request("/health/dependencies")
            results["dependencies"] = {
                "available": dependencies.get("success", False),
                "status": dependencies.get("data", {}).get("overall_status")
            }
            
            # 運用メトリクス
            metrics = await self._make_request("/health/metrics")
            results["metrics"] = {
                "available": metrics.get("success", False)
            }
            
            # Phase 3統合状況
            overview = await self._make_request("/api/v3/management/overview")
            results["phase3_integration"] = {
                "available": overview.get("success", False),
                "health_level": overview.get("data", {}).get("overall_health", {}).get("level")
            }
            
            results["overall_success"] = all([
                results.get("k8s_healthz", False),
                results.get("k8s_readyz", False),
                results.get("dependencies", {}).get("available", False),
                results.get("metrics", {}).get("available", False),
                results.get("phase3_integration", {}).get("available", False)
            ])
            
        except Exception as e:
            results["error"] = str(e)
            results["overall_success"] = False
        
        return results
    
    async def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """HTTPリクエスト実行"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    data = await response.json()
                    return {
                        "success": response.status == 200,
                        "status_code": response.status,
                        "data": data
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """テスト結果サマリー生成"""
        summary = {
            "total_test_categories": len(test_results) - 1,  # summaryを除く
            "passed_categories": 0,
            "failed_categories": 0,
            "overall_success": True,
            "performance_score": 0,
            "recommendations": []
        }
        
        for category, result in test_results.items():
            if category == "summary":
                continue
            
            if isinstance(result, dict) and result.get("overall_success", False):
                summary["passed_categories"] += 1
            else:
                summary["failed_categories"] += 1
                summary["overall_success"] = False
        
        # パフォーマンススコア計算
        success_rate = summary["passed_categories"] / summary["total_test_categories"] * 100
        summary["performance_score"] = success_rate
        
        # 推奨事項生成
        if summary["performance_score"] < 100:
            summary["recommendations"].append("Some test categories failed - review failed tests")
        
        if test_results.get("load_testing", {}).get("overall_success", True) == False:
            summary["recommendations"].append("Load testing failed - optimize for higher throughput")
        
        if test_results.get("performance_testing", {}).get("overall_success", True) == False:
            summary["recommendations"].append("Performance testing failed - optimize response times")
        
        if not summary["recommendations"]:
            summary["recommendations"].append("All tests passed - system ready for production")
        
        return summary


# テスト実行関数
async def run_phase3_tests():
    """Phase 3統合テスト実行"""
    tester = Phase3IntegrationTester()
    
    print("🚀 Starting Phase 3 Integration Tests")
    print("This may take several minutes...")
    print()
    
    try:
        results = await tester.run_comprehensive_test()
        
        # 結果出力
        print("\n" + "="*80)
        print("📊 PHASE 3 INTEGRATION TEST RESULTS")
        print("="*80)
        
        summary = results.get("summary", {})
        print(f"Overall Success: {'✅ PASS' if summary.get('overall_success') else '❌ FAIL'}")
        print(f"Performance Score: {summary.get('performance_score', 0):.1f}%")
        print(f"Test Categories: {summary.get('passed_categories', 0)}/{summary.get('total_test_categories', 0)} passed")
        print()
        
        # カテゴリ別結果
        for category, result in results.items():
            if category == "summary":
                continue
            
            status = "✅ PASS" if result.get("overall_success", False) else "❌ FAIL"
            print(f"{category.replace('_', ' ').title()}: {status}")
        
        print()
        print("Recommendations:")
        for rec in summary.get("recommendations", []):
            print(f"  • {rec}")
        
        # 詳細結果をファイルに保存
        import json
        with open("phase3_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: phase3_test_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # テスト実行
    asyncio.run(run_phase3_tests())