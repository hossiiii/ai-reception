#!/usr/bin/env python3
"""
Phase 3 Startup Test

アプリケーションのstartupイベントをテストします。
"""

import asyncio
import traceback
from datetime import datetime


async def test_startup_sequence():
    """スタートアップシーケンステスト"""
    print("🚀 Testing Application Startup Sequence")
    print("=" * 50)
    
    try:
        # Phase 3 サービスの初期化
        from app.services.performance_optimizer import get_performance_optimizer
        from app.services.cost_optimizer import get_cost_optimizer
        from app.services.monitoring_system import get_monitoring_system
        from app.services.reliability_manager import get_reliability_manager, setup_default_reliability
        from app.services.security_manager import get_security_manager
        
        print("📊 Initializing Performance Optimizer...")
        performance_optimizer = await get_performance_optimizer()
        # パフォーマンス最適化レベルを設定
        await performance_optimizer.adjust_optimization_level("balanced")
        print("✅ Performance Optimizer: Ready")
        
        print("💰 Initializing Cost Optimizer...")
        cost_optimizer = await get_cost_optimizer()
        # コスト状況を確認
        cost_summary = await cost_optimizer.get_cost_summary()
        print("✅ Cost Optimizer: Ready")
        
        print("🔍 Initializing Monitoring System...")
        monitoring_system = await get_monitoring_system()
        # 監視システムを開始（軽量モード）
        print("✅ Monitoring System: Ready")
        
        print("🛡️ Initializing Reliability Manager...")
        reliability_manager = await get_reliability_manager()
        # デフォルト信頼性設定
        await setup_default_reliability()
        print("✅ Reliability Manager: Ready")
        
        print("🔐 Initializing Security Manager...")
        security_manager = await get_security_manager()
        print("✅ Security Manager: Ready")
        
        print("\n🎯 Phase 3 services successfully initialized!")
        return True
        
    except Exception as e:
        print(f"❌ Startup sequence failed: {e}")
        traceback.print_exc()
        return False


async def test_basic_functionality():
    """基本機能テスト"""
    print("\n🧪 Testing Basic Functionality")
    print("=" * 50)
    
    try:
        # ヘルスチェック機能のテスト
        from app.api.health import basic_health_check, detailed_health_check
        
        print("🏥 Testing Health Check Functions...")
        
        # 基本ヘルスチェック
        basic_result = await basic_health_check()
        print(f"✅ Basic Health Check: {basic_result['status']}")
        
        # 詳細ヘルスチェック
        detailed_result = await detailed_health_check()
        print(f"✅ Detailed Health Check: {detailed_result['status']}")
        
        # システムメトリクス確認
        system_resources = detailed_result.get('system_resources', {})
        cpu_percent = system_resources.get('cpu_percent', 0)
        memory_percent = system_resources.get('memory_percent', 0)
        print(f"✅ System Resources: CPU {cpu_percent:.1f}%, Memory {memory_percent:.1f}%")
        
        print("\n🎉 Basic functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False


async def test_phase3_management():
    """Phase 3管理機能テスト"""
    print("\n⚙️ Testing Phase 3 Management Functions")
    print("=" * 50)
    
    try:
        from app.services.performance_optimizer import get_performance_optimizer
        from app.services.cost_optimizer import get_cost_optimizer
        from app.services.monitoring_system import get_monitoring_system
        
        # パフォーマンス最適化状態取得
        perf_optimizer = await get_performance_optimizer()
        perf_summary = await perf_optimizer.get_performance_summary()
        print(f"✅ Performance Summary: Available (Optimization: {perf_summary.get('optimization_enabled', False)})")
        
        # コスト状況取得
        cost_optimizer = await get_cost_optimizer()
        cost_summary = await cost_optimizer.get_cost_summary()
        print(f"✅ Cost Summary: Available (Total: ${cost_summary.get('total_cost', 0):.2f})")
        
        # 監視システム状態取得
        monitoring = await get_monitoring_system()
        dashboard_data = await monitoring.get_dashboard_data()
        print("✅ Monitoring Dashboard: Available")
        
        print("\n🎉 Phase 3 management functions test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Phase 3 management test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """メインテスト実行"""
    print("🔬 Phase 3 Application Startup Test")
    print("=" * 60)
    print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    test_results = []
    
    # テスト実行
    tests = [
        ("Startup Sequence", test_startup_sequence),
        ("Basic Functionality", test_basic_functionality),
        ("Phase3 Management", test_phase3_management),
    ]
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            test_results.append((test_name, False))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 STARTUP TEST RESULTS")
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
        print("🎉 ALL STARTUP TESTS PASSED!")
        print("🚀 Phase 3 application startup is working correctly!")
        exit_code = 0
    else:
        print("⚠️  Some startup tests failed.")
        exit_code = 1
    
    print(f"Test End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    import sys
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