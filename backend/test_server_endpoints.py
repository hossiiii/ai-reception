#!/usr/bin/env python3
"""
Phase 3サーバーエンドポイントテスト

実際にサーバーを起動してHTTPエンドポイントのテストを実行します。
"""

import asyncio
import json
import time
import subprocess
import requests
import signal
import os
from datetime import datetime


def start_server():
    """FastAPIサーバーを起動"""
    print("🚀 Starting FastAPI server...")
    
    # サーバープロセスを起動
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # サーバーが起動するまで待機
    for i in range(30):  # 30秒まで待機
        try:
            response = requests.get("http://localhost:8000/health/", timeout=2)
            if response.status_code == 200:
                print("✅ Server started successfully!")
                return process
        except:
            pass
        
        print(f"⏳ Waiting for server startup... ({i+1}/30)")
        time.sleep(1)
    
    print("❌ Server failed to start within 30 seconds")
    process.terminate()
    return None


def stop_server(process):
    """サーバーを停止"""
    if process:
        print("🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Server stopped")


def test_endpoint(url, description):
    """エンドポイントをテスト"""
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {description}: HTTP {response.status_code}")
            return True, data
        else:
            print(f"❌ {description}: HTTP {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ {description}: Error - {e}")
        return False, None


def main():
    """メインテスト実行"""
    print("🔬 Phase 3 Server Endpoint Test")
    print("=" * 60)
    print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    server_process = None
    test_results = []
    
    try:
        # サーバー起動
        server_process = start_server()
        if not server_process:
            print("❌ Server startup failed - aborting tests")
            return 1
        
        # テストエンドポイント一覧
        endpoints = [
            ("http://localhost:8000/health/", "Basic Health Check"),
            ("http://localhost:8000/health/detailed", "Detailed Health Check"),
            ("http://localhost:8000/health/readiness", "Readiness Check"),
            ("http://localhost:8000/health/liveness", "Liveness Check"),
            ("http://localhost:8000/health/performance", "Performance Status"),
            ("http://localhost:8000/health/cost", "Cost Status"),
            ("http://localhost:8000/health/monitoring", "Monitoring Status"),
            ("http://localhost:8000/health/reliability", "Reliability Status"),
            ("http://localhost:8000/health/security", "Security Status"),
            ("http://localhost:8000/health/dependencies", "Dependencies Status"),
            ("http://localhost:8000/health/metrics", "Operational Metrics"),
            ("http://localhost:8000/health/k8s/healthz", "Kubernetes Health"),
            ("http://localhost:8000/health/k8s/readyz", "Kubernetes Ready"),
            ("http://localhost:8000/health/k8s/livez", "Kubernetes Live"),
            ("http://localhost:8000/api/v3/management/performance/status", "Performance Management"),
            ("http://localhost:8000/api/v3/management/cost/summary", "Cost Management"),
            ("http://localhost:8000/api/v3/management/monitoring/dashboard", "Monitoring Dashboard"),
            ("http://localhost:8000/api/v3/management/reliability/status", "Reliability Management"),
            ("http://localhost:8000/api/v3/management/security/dashboard", "Security Dashboard"),
            ("http://localhost:8000/api/v3/management/overview", "Phase3 Overview"),
        ]
        
        print(f"\n🧪 Testing {len(endpoints)} endpoints...")
        print("-" * 60)
        
        # 各エンドポイントをテスト
        for url, description in endpoints:
            success, data = test_endpoint(url, description)
            test_results.append((description, success, url))
            
            # 一部の重要な結果を表示
            if success and data and description in ["Basic Health Check", "Detailed Health Check", "Phase3 Overview"]:
                if "status" in data:
                    print(f"   Status: {data['status']}")
                if "overall_health" in data:
                    health = data["overall_health"]
                    print(f"   Overall Health: {health.get('level', 'unknown')} (Score: {health.get('score', 0):.1f})")
            
            time.sleep(0.5)  # レート制限を避けるため少し待機
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📋 ENDPOINT TEST RESULTS")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for description, success, url in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {description}")
            
            if success:
                passed += 1
            else:
                failed += 1
        
        print("-" * 60)
        print(f"Total Endpoints: {len(test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(test_results)*100):.1f}%")
        print("-" * 60)
        
        if failed == 0:
            print("🎉 ALL ENDPOINT TESTS PASSED!")
            print("🚀 Phase 3 is ready for production deployment!")
            exit_code = 0
        else:
            print("⚠️  Some endpoint tests failed.")
            exit_code = 1
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        exit_code = 130
        
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit_code = 1
        
    finally:
        # サーバー停止
        if server_process:
            stop_server(server_process)
    
    print(f"Test End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    import sys
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)