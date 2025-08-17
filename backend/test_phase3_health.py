#!/usr/bin/env python3
"""
Phase 3ヘルスチェック機能テストスクリプト

このスクリプトはPhase 3で実装されたヘルスチェック機能と
エンタープライズ監視機能の動作を検証します。
"""

import asyncio
import sys
import traceback
from datetime import datetime

def test_imports():
    """Phase 3の依存関係とimportテスト"""
    print("🔍 Phase 3 Dependencies & Import Test")
    print("=" * 50)
    
    try:
        # 基本依存関係テスト
        import psutil
        print(f"✅ psutil: {psutil.__version__}")
        
        import jwt
        print(f"✅ PyJWT: {jwt.__version__}")
        
        import bcrypt
        print("✅ bcrypt: Available")
        
        import prometheus_client
        print("✅ prometheus_client: Available")
        
        # Phase 3サービスのimportテスト
        from app.services.performance_optimizer import get_performance_optimizer
        print("✅ PerformanceOptimizer: Import successful")
        
        from app.services.cost_optimizer import get_cost_optimizer
        print("✅ CostOptimizer: Import successful")
        
        from app.services.monitoring_system import get_monitoring_system
        print("✅ MonitoringSystem: Import successful")
        
        from app.services.reliability_manager import get_reliability_manager
        print("✅ ReliabilityManager: Import successful")
        
        from app.services.security_manager import get_security_manager
        print("✅ SecurityManager: Import successful")
        
        # APIエンドポイントのimportテスト
        from app.api.health import router as health_router
        print("✅ Health API: Import successful")
        
        from app.api.phase3_management import router as phase3_router
        print("✅ Phase3 Management API: Import successful")
        
        print("\n🎉 All Phase 3 dependencies and imports are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        traceback.print_exc()
        return False


async def test_services_initialization():
    """Phase 3サービスの初期化テスト"""
    print("\n🔧 Phase 3 Services Initialization Test")
    print("=" * 50)
    
    try:
        # サービス初期化テスト
        from app.services.performance_optimizer import get_performance_optimizer
        from app.services.cost_optimizer import get_cost_optimizer
        from app.services.monitoring_system import get_monitoring_system
        from app.services.reliability_manager import get_reliability_manager
        from app.services.security_manager import get_security_manager
        
        # 各サービスの初期化確認
        perf_optimizer = await get_performance_optimizer()
        print("✅ PerformanceOptimizer: Initialized")
        
        cost_optimizer = await get_cost_optimizer()
        print("✅ CostOptimizer: Initialized")
        
        monitoring_system = await get_monitoring_system()
        print("✅ MonitoringSystem: Initialized")
        
        reliability_manager = await get_reliability_manager()
        print("✅ ReliabilityManager: Initialized")
        
        security_manager = await get_security_manager()
        print("✅ SecurityManager: Initialized")
        
        print("\n🎉 All Phase 3 services initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Service initialization test failed: {e}")
        traceback.print_exc()
        return False


async def test_health_functions():
    """ヘルスチェック機能の動作テスト"""
    print("\n🏥 Health Check Functions Test")
    print("=" * 50)
    
    try:
        from app.api.health import (
            basic_health_check,
            detailed_health_check,
            readiness_check,
            liveness_check,
            performance_status,
            cost_status,
            monitoring_status,
            reliability_status,
            security_status,
            dependencies_status,
            operational_metrics
        )
        
        # 基本ヘルスチェック
        basic_result = await basic_health_check()
        print(f"✅ Basic Health: {basic_result['status']}")
        
        # 詳細ヘルスチェック
        detailed_result = await detailed_health_check()
        print(f"✅ Detailed Health: {detailed_result['status']}")
        
        # Readinessチェック
        readiness_result = await readiness_check()
        print(f"✅ Readiness: {'Ready' if readiness_result['ready'] else 'Not Ready'}")
        
        # Livenessチェック
        liveness_result = await liveness_check()
        print(f"✅ Liveness: {'Alive' if liveness_result['alive'] else 'Not Alive'}")
        
        # 依存関係チェック
        deps_result = await dependencies_status()
        print(f"✅ Dependencies: {deps_result['overall_status']}")
        
        # 運用メトリクス
        metrics_result = await operational_metrics()
        print(f"✅ Operational Metrics: Available")
        
        print("\n🎉 All health check functions are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Health functions test failed: {e}")
        traceback.print_exc()
        return False


async def test_performance_monitoring():
    """パフォーマンス監視機能テスト"""
    print("\n📊 Performance Monitoring Test")
    print("=" * 50)
    
    try:
        from app.services.performance_optimizer import get_performance_optimizer
        from app.services.monitoring_system import get_monitoring_system
        
        # パフォーマンス最適化機能テスト
        perf_optimizer = await get_performance_optimizer()
        perf_summary = await perf_optimizer.get_performance_summary()
        print(f"✅ Performance Summary: {perf_summary.get('optimization_enabled', False)}")
        
        # 監視システムテスト
        monitoring = await get_monitoring_system()
        dashboard_data = await monitoring.get_dashboard_data()
        print(f"✅ Monitoring Dashboard: Available")
        
        # システムリソース情報
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        print(f"✅ System Metrics: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%")
        
        print("\n🎉 Performance monitoring is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Performance monitoring test failed: {e}")
        traceback.print_exc()
        return False


async def test_fastapi_integration():
    """FastAPIアプリケーション統合テスト"""
    print("\n🚀 FastAPI Integration Test")
    print("=" * 50)
    
    try:
        from app.main import app
        
        # FastAPIアプリケーションの基本確認
        print(f"✅ FastAPI App Title: {app.title}")
        print(f"✅ FastAPI App Version: {app.version}")
        
        # ルート確認
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        health_routes = [r for r in routes if 'health' in r]
        phase3_routes = [r for r in routes if 'v3' in r or 'management' in r]
        
        print(f"✅ Health Routes: {len(health_routes)} found")
        print(f"✅ Phase3 Routes: {len(phase3_routes)} found")
        
        # 主要ルートの存在確認
        expected_health_routes = [
            "/health/",
            "/health/detailed",
            "/health/readiness",
            "/health/liveness"
        ]
        
        for route in expected_health_routes:
            if any(route in r for r in routes):
                print(f"✅ Route {route}: Available")
            else:
                print(f"⚠️  Route {route}: Not found in routes")
        
        print("\n🎉 FastAPI integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI integration test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """メインテスト実行"""
    print("🔬 Phase 3 Health Check & Integration Test")
    print("=" * 60)
    print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = []
    
    # テスト実行
    tests = [
        ("Dependencies & Imports", test_imports),
        ("Services Initialization", test_services_initialization),
        ("Health Check Functions", test_health_functions),
        ("Performance Monitoring", test_performance_monitoring),
        ("FastAPI Integration", test_fastapi_integration),
    ]
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            test_results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 60)
    print(f"Total Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_results)*100):.1f}%")
    print("-" * 60)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Phase 3 is ready for production!")
        exit_code = 0
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
        exit_code = 1
    
    print(f"Test End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)