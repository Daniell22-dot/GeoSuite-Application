"""
Monitoring and health check routes.
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from app.config import settings

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
    from app.monitoring import metrics_collector
    from app.database import SessionLocal
    from app.models.geospatial import User, GPSTrack, WatershedAnalysis, DroneSurvey, MarineChart
    from sqlalchemy import func

    db = SessionLocal()
    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_tracks = db.query(func.count(GPSTrack.id)).scalar() or 0
        total_watershed = db.query(func.count(WatershedAnalysis.id)).scalar() or 0
        total_drone = db.query(func.count(DroneSurvey.id)).scalar() or 0
        total_marine = db.query(func.count(MarineChart.id)).scalar() or 0

        return {
            "system": {
                "cpu_usage": f"{metrics_collector.collect_system_metrics() if hasattr(metrics_collector, 'collect_system_metrics') else 'N/A'}",
                "app_version": settings.APP_VERSION,
                "app_name": settings.APP_NAME,
            },
            "counts": {
                "users": total_users,
                "gps_tracks": total_tracks,
                "watershed_analyses": total_watershed,
                "drone_surveys": total_drone,
                "marine_charts": total_marine,
            },
            "endpoints": {
                "gps_uploads": "Counted in metrics",
                "marine_charts": "Counted in metrics",
                "watershed_analyses": "Counted in metrics",
                "hecras_simulations": "Counted in metrics"
            }
        }
    finally:
        db.close()

@router.get("/logs")
async def get_logs(limit: int = 100):
    """
    Get recent application logs.
    
    Args:
        limit: Maximum number of log lines to return
    """
    try:
        with open(settings.LOG_FILE, "r") as f:
            lines = f.readlines()
        
        # Return last 'limit' lines
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        
        return {
            "log_file": settings.LOG_FILE,
            "total_lines": len(lines),
            "recent_lines": recent_lines
        }
    except FileNotFoundError:
        return {
            "log_file": settings.LOG_FILE,
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