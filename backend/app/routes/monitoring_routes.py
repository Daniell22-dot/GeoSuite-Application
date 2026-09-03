"""
Monitoring and health check routes.
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.monitoring import get_metrics, get_health_status, metrics_collector

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """
    Get Prometheus metrics.
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain")

@router.get("/health")
async def health():
    """
    Get system health status.
    """
    health_status = get_health_status()
    return health_status

@router.get("/health/live")
async def liveness_probe():
    """
    Liveness probe for Kubernetes.
    """
    health_status = get_health_status()
    if health_status["status"] in ["healthy", "warning"]:
        return {"status": "alive"}
    else:
        return Response(
            content="unhealthy",
            status_code=503,
            media_type="text/plain"
        )

@router.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe for Kubernetes.
    """
    health_status = get_health_status()
    if health_status["status"] == "healthy":
        return {"status": "ready"}
    else:
        return Response(
            content="not ready",
            status_code=503,
            media_type="text/plain"
        )

@router.get("/stats")
async def get_statistics():
    """
    Get application statistics.
    """
    # This would query database for statistics
    # For now, return basic metrics
    
    stats = {
        "requests_total": "See /metrics for detailed counters",
        "system": {
            "cpu_usage": "See /metrics",
            "memory_usage": "See /metrics",
            "disk_usage": "See /metrics"
        },
        "endpoints": {
            "gps_uploads": "Counted in metrics",
            "marine_charts": "Counted in metrics",
            "watershed_analyses": "Counted in metrics",
            "hecras_simulations": "Counted in metrics"
        }
    }
    
    return stats

@router.get("/logs")
async def get_logs(limit: int = 100):
    """
    Get recent application logs.
    
    Args:
        limit: Maximum number of log lines to return
    """
    try:
        with open("geosuite.log", "r") as f:
            lines = f.readlines()
        
        # Return last 'limit' lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "log_file": "geosuite.log",
            "total_lines": len(lines),
            "recent_lines": recent_lines
        }
    except FileNotFoundError:
        return {
            "log_file": "geosuite.log",
            "error": "Log file not found",
            "recent_lines": []
        }

@router.get("/performance")
async def get_performance_report():
    """
    Get performance report.
    """
    from app.monitoring import performance_monitor
    return performance_monitor.get_performance_report()