"""
Phase 3 統合管理 API エンドポイント

Phase 3の本格運用機能統合管理:
1. パフォーマンス最適化制御
2. コスト管理とアラート設定
3. 監視・アラート管理
4. 信頼性設定管理
5. セキュリティ管理
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, Any, Optional, List
import time
from pydantic import BaseModel

from ..services.performance_optimizer import get_performance_optimizer
from ..services.cost_optimizer import get_cost_optimizer, CostLimits
from ..services.monitoring_system import get_monitoring_system
from ..services.reliability_manager import get_reliability_manager, CircuitBreakerConfig
from ..services.security_manager import get_security_manager


router = APIRouter(prefix="/api/v3/management", tags=["Phase 3 Management"])


# Pydantic models
class OptimizationLevelRequest(BaseModel):
    level: str  # "aggressive", "balanced", "conservative"


class CostLimitsRequest(BaseModel):
    hourly_limit: Optional[float] = None
    daily_limit: Optional[float] = None
    weekly_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    session_limit: Optional[float] = None


class AlertRuleRequest(BaseModel):
    rule_id: str
    name: str
    metric_type: str
    condition: str
    severity: str
    enabled: bool = True
    cooldown_seconds: int = 300


class CircuitBreakerRequest(BaseModel):
    name: str
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 60.0
    monitoring_window_seconds: int = 300


class SecurityRuleRequest(BaseModel):
    rule_id: str
    path_pattern: str
    required_access_level: str
    allowed_methods: List[str]
    enabled: bool = True


# パフォーマンス最適化エンドポイント
@router.get("/performance/status", summary="パフォーマンス状態取得")
async def get_performance_status(
    performance_optimizer = Depends(get_performance_optimizer)
) -> Dict[str, Any]:
    """パフォーマンス最適化の現在状態を取得"""
    try:
        return await performance_optimizer.get_performance_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/optimize-level", summary="最適化レベル調整")
async def adjust_optimization_level(
    request: OptimizationLevelRequest,
    performance_optimizer = Depends(get_performance_optimizer)
) -> Dict[str, Any]:
    """パフォーマンス最適化レベルを調整"""
    try:
        if request.level not in ["aggressive", "balanced", "conservative"]:
            raise HTTPException(status_code=400, detail="Invalid optimization level")
        
        result = await performance_optimizer.adjust_optimization_level(request.level)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/cleanup", summary="リソースクリーンアップ")
async def trigger_resource_cleanup(
    performance_optimizer = Depends(get_performance_optimizer)
) -> Dict[str, Any]:
    """パフォーマンス最適化のリソースクリーンアップを実行"""
    try:
        result = await performance_optimizer.cleanup_resources()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# コスト管理エンドポイント
@router.get("/cost/summary", summary="コストサマリー取得")
async def get_cost_summary(
    hours: int = Query(24, description="集計期間（時間）"),
    cost_optimizer = Depends(get_cost_optimizer)
) -> Dict[str, Any]:
    """コスト使用状況のサマリーを取得"""
    try:
        return await cost_optimizer.get_cost_summary(hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/prediction", summary="コスト予測")
async def get_cost_prediction(
    prediction_hours: int = Query(24, description="予測期間（時間）"),
    cost_optimizer = Depends(get_cost_optimizer)
) -> Dict[str, Any]:
    """コストトレンド予測を取得"""
    try:
        return await cost_optimizer.predict_cost_trend(prediction_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/limits", summary="コスト制限更新")
async def update_cost_limits(
    request: CostLimitsRequest,
    cost_optimizer = Depends(get_cost_optimizer)
) -> Dict[str, Any]:
    """コスト制限値を更新"""
    try:
        # None以外の値のみを更新
        limits_update = {k: v for k, v in request.dict().items() if v is not None}
        
        if not limits_update:
            raise HTTPException(status_code=400, detail="No limits to update")
        
        result = await cost_optimizer.update_cost_limits(limits_update)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/alerts", summary="コストアラート履歴")
async def get_cost_alerts(
    limit: int = Query(20, description="取得件数"),
    cost_optimizer = Depends(get_cost_optimizer)
) -> List[Dict[str, Any]]:
    """最近のコストアラートを取得"""
    try:
        return await cost_optimizer.get_recent_alerts(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 監視・アラート管理エンドポイント
@router.get("/monitoring/dashboard", summary="監視ダッシュボード")
async def get_monitoring_dashboard(
    monitoring_system = Depends(get_monitoring_system)
) -> Dict[str, Any]:
    """監視ダッシュボードデータを取得"""
    try:
        return await monitoring_system.get_dashboard_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start", summary="監視開始")
async def start_monitoring(
    monitoring_system = Depends(get_monitoring_system)
) -> Dict[str, Any]:
    """監視システムを開始"""
    try:
        await monitoring_system.start_monitoring()
        return {"status": "monitoring_started", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop", summary="監視停止")
async def stop_monitoring(
    monitoring_system = Depends(get_monitoring_system)
) -> Dict[str, Any]:
    """監視システムを停止"""
    try:
        await monitoring_system.stop_monitoring()
        return {"status": "monitoring_stopped", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/alerts/{alert_id}/acknowledge", summary="アラート確認")
async def acknowledge_alert(
    alert_id: str,
    user: str = Query(..., description="確認ユーザー"),
    monitoring_system = Depends(get_monitoring_system)
) -> Dict[str, Any]:
    """アラートを確認済みにマーク"""
    try:
        success = await monitoring_system.alert_manager.acknowledge_alert(alert_id, user)
        if success:
            return {"status": "acknowledged", "alert_id": alert_id, "user": user}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/alerts/{alert_id}/resolve", summary="アラート解決")
async def resolve_alert(
    alert_id: str,
    user: str = Query(..., description="解決ユーザー"),
    monitoring_system = Depends(get_monitoring_system)
) -> Dict[str, Any]:
    """アラートを解決済みにマーク"""
    try:
        success = await monitoring_system.alert_manager.resolve_alert(alert_id, user)
        if success:
            return {"status": "resolved", "alert_id": alert_id, "user": user}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 信頼性管理エンドポイント
@router.get("/reliability/status", summary="信頼性状態取得")
async def get_reliability_status(
    reliability_manager = Depends(get_reliability_manager)
) -> Dict[str, Any]:
    """信頼性管理の現在状態を取得"""
    try:
        return await reliability_manager.get_reliability_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reliability/circuit-breaker", summary="サーキットブレーカー作成")
async def create_circuit_breaker(
    request: CircuitBreakerRequest,
    reliability_manager = Depends(get_reliability_manager)
) -> Dict[str, Any]:
    """新しいサーキットブレーカーを作成"""
    try:
        config = CircuitBreakerConfig(
            failure_threshold=request.failure_threshold,
            success_threshold=request.success_threshold,
            timeout_seconds=request.timeout_seconds,
            monitoring_window_seconds=request.monitoring_window_seconds
        )
        
        circuit_breaker = reliability_manager.create_circuit_breaker(request.name, config)
        
        return {
            "status": "created",
            "name": request.name,
            "config": config.__dict__
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reliability/monitoring/start", summary="信頼性監視開始")
async def start_reliability_monitoring(
    reliability_manager = Depends(get_reliability_manager)
) -> Dict[str, Any]:
    """信頼性監視を開始"""
    try:
        await reliability_manager.start_reliability_monitoring()
        return {"status": "reliability_monitoring_started", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reliability/monitoring/stop", summary="信頼性監視停止")
async def stop_reliability_monitoring(
    reliability_manager = Depends(get_reliability_manager)
) -> Dict[str, Any]:
    """信頼性監視を停止"""
    try:
        await reliability_manager.stop_reliability_monitoring()
        return {"status": "reliability_monitoring_stopped", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# セキュリティ管理エンドポイント
@router.get("/security/dashboard", summary="セキュリティダッシュボード")
async def get_security_dashboard(
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """セキュリティダッシュボードデータを取得"""
    try:
        return await security_manager.get_security_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/api-key", summary="API キー生成")
async def generate_api_key(
    user_id: str = Query(..., description="ユーザーID"),
    permissions: List[str] = Query(..., description="権限リスト"),
    expires_in_days: int = Query(365, description="有効期限（日数）"),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """新しいAPI キーを生成"""
    try:
        api_key = security_manager.api_key_manager.generate_api_key(
            user_id, permissions, expires_in_days
        )
        
        return {
            "status": "generated",
            "api_key": api_key,
            "user_id": user_id,
            "permissions": permissions,
            "expires_in_days": expires_in_days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/security/api-key/{api_key}", summary="API キー無効化")
async def revoke_api_key(
    api_key: str,
    reason: str = Query("manual_revocation", description="無効化理由"),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """API キーを無効化"""
    try:
        security_manager.api_key_manager.revoke_api_key(api_key, reason)
        return {
            "status": "revoked",
            "api_key": api_key[:16] + "...",
            "reason": reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security/api-key/{api_key}/usage", summary="API キー使用統計")
async def get_api_key_usage(
    api_key: str,
    hours: int = Query(24, description="統計期間（時間）"),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """API キーの使用統計を取得"""
    try:
        return security_manager.api_key_manager.get_key_usage_stats(api_key, hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/ip/blacklist", summary="IP ブラックリスト追加")
async def add_ip_to_blacklist(
    ip: str = Query(..., description="ブロックするIP"),
    reason: str = Query("manual", description="ブロック理由"),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """IP をブラックリストに追加"""
    try:
        security_manager.ip_filter.add_to_blacklist(ip, reason)
        return {
            "status": "blacklisted",
            "ip": ip,
            "reason": reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/security/ip/blacklist/{ip}", summary="IP ブラックリスト削除")
async def remove_ip_from_blacklist(
    ip: str,
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """IP をブラックリストから削除"""
    try:
        security_manager.ip_filter.remove_from_blacklist(ip)
        return {
            "status": "unblocked",
            "ip": ip
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/ip/whitelist", summary="IP ホワイトリスト追加")
async def add_ip_to_whitelist(
    ip: str = Query(..., description="許可するIP"),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """IP をホワイトリストに追加"""
    try:
        security_manager.ip_filter.add_to_whitelist(ip)
        return {
            "status": "whitelisted",
            "ip": ip
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 統合管理エンドポイント
@router.get("/overview", summary="Phase 3 全体概要")
async def get_phase3_overview(
    performance_optimizer = Depends(get_performance_optimizer),
    cost_optimizer = Depends(get_cost_optimizer),
    monitoring_system = Depends(get_monitoring_system),
    reliability_manager = Depends(get_reliability_manager),
    security_manager = Depends(get_security_manager)
) -> Dict[str, Any]:
    """Phase 3 全機能の統合概要を取得"""
    try:
        # 並行して各サービスの状態を取得
        performance_task = performance_optimizer.get_performance_summary()
        cost_task = cost_optimizer.get_cost_summary(24)
        monitoring_task = monitoring_system.get_dashboard_data()
        reliability_task = reliability_manager.get_reliability_status()
        security_task = security_manager.get_security_dashboard()
        
        # 結果を待機
        performance_data = await performance_task
        cost_data = await cost_task
        monitoring_data = await monitoring_task
        reliability_data = await reliability_task
        security_data = await security_task
        
        # 全体健康度スコア計算
        health_scores = []
        
        # パフォーマンススコア
        perf_score = 100
        if performance_data.get("performance", {}).get("cpu_under_pressure", False):
            perf_score -= 20
        health_scores.append(perf_score)
        
        # コストスコア
        cost_score = 100
        if cost_data.get("total_cost", 0) > 50:  # 24時間で$50超過
            cost_score -= 30
        health_scores.append(cost_score)
        
        # 監視スコア
        monitoring_score = 100
        system_status = monitoring_data.get("system_status", {})
        if system_status.get("critical_alerts", 0) > 0:
            monitoring_score -= 40
        health_scores.append(monitoring_score)
        
        # 信頼性スコア
        reliability_score = 100
        if reliability_data.get("overall_health") != "healthy":
            reliability_score -= 30
        health_scores.append(reliability_score)
        
        # セキュリティスコア
        security_score = security_data.get("security_summary", {}).get("security_score", 100)
        health_scores.append(security_score)
        
        overall_health_score = sum(health_scores) / len(health_scores)
        
        # 健康レベル判定
        if overall_health_score >= 90:
            health_level = "excellent"
        elif overall_health_score >= 80:
            health_level = "good"
        elif overall_health_score >= 70:
            health_level = "warning"
        else:
            health_level = "critical"
        
        return {
            "timestamp": time.time(),
            "phase3_version": "1.0.0",
            "overall_health": {
                "level": health_level,
                "score": overall_health_score,
                "component_scores": {
                    "performance": perf_score,
                    "cost": cost_score,
                    "monitoring": monitoring_score,
                    "reliability": reliability_score,
                    "security": security_score
                }
            },
            "performance": {
                "optimization_enabled": performance_data.get("optimization_enabled", False),
                "cpu_under_pressure": performance_data.get("performance", {}).get("cpu_under_pressure", False),
                "avg_latency_ms": performance_data.get("performance", {}).get("avg_audio_latency_ms", 0)
            },
            "cost": {
                "total_24h_usd": cost_data.get("total_cost", 0),
                "hourly_limit_usd": 50.0,
                "efficiency": "optimal" if cost_data.get("total_cost", 0) < 25 else "moderate"
            },
            "monitoring": {
                "active_alerts": system_status.get("active_alerts", 0),
                "critical_alerts": system_status.get("critical_alerts", 0),
                "uptime_hours": system_status.get("uptime_hours", 0)
            },
            "reliability": {
                "overall_health": reliability_data.get("overall_health", "unknown"),
                "circuit_breakers_open": reliability_data.get("summary", {}).get("circuit_breakers", {}).get("open", 0),
                "healthy_instances": reliability_data.get("summary", {}).get("service_instances", {}).get("healthy", 0)
            },
            "security": {
                "security_level": "excellent" if security_score >= 90 else "good",
                "blocked_ips": len(security_data.get("ip_filtering", {}).get("blacklisted_ips", 0)),
                "active_api_keys": security_data.get("api_keys", {}).get("total_active", 0)
            },
            "recommendations": _generate_recommendations(
                performance_data, cost_data, monitoring_data, reliability_data, security_data
            )
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generate_recommendations(perf_data, cost_data, monitoring_data, reliability_data, security_data) -> List[str]:
    """改善推奨事項生成"""
    recommendations = []
    
    # パフォーマンス推奨
    if perf_data.get("performance", {}).get("cpu_under_pressure", False):
        recommendations.append("Consider scaling up resources or optimizing CPU-intensive operations")
    
    # コスト推奨
    if cost_data.get("total_cost", 0) > 50:
        recommendations.append("Review cost optimization settings and consider usage patterns")
    
    # 監視推奨
    active_alerts = monitoring_data.get("system_status", {}).get("active_alerts", 0)
    if active_alerts > 5:
        recommendations.append("Address active alerts to improve system stability")
    
    # 信頼性推奨
    if reliability_data.get("overall_health") != "healthy":
        recommendations.append("Check circuit breaker states and service health")
    
    # セキュリティ推奨
    security_score = security_data.get("security_summary", {}).get("security_score", 100)
    if security_score < 90:
        recommendations.append("Review security events and strengthen access controls")
    
    if not recommendations:
        recommendations.append("System is operating optimally")
    
    return recommendations