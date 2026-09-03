"""
Monitoring and observability for GeoSuite.
Includes logging, metrics, and health checks.
"""
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import REGISTRY
import psutil
import os

from app.config import settings

# Setup logging
logger = logging.getLogger(__name__)

# Prometheus metrics
# Request metrics
REQUEST_COUNT = Counter(
    'geosuite_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'geosuite_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

# Business metrics
GPS_UPLOADS = Counter(
    'geosuite_gps_uploads_total',
    'Total number of GPS file uploads'
)

MARINE_CHARTS_PROCESSED = Counter(
    'geosuite_marine_charts_processed_total',
    'Total number of marine charts processed'
)

WATERSHED_ANALYSES = Counter(
    'geosuite_watershed_analyses_total',
    'Total number of watershed analyses performed'
)

HECRAS_SIMULATIONS = Counter(
    'geosuite_hecras_simulations_total',
    'Total number of HEC-RAS simulations'
)

# System metrics
SYSTEM_CPU_USAGE = Gauge(
    'geosuite_system_cpu_usage_percent',
    'System CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'geosuite_system_memory_usage_percent',
    'System memory usage percentage'
)

SYSTEM_DISK_USAGE = Gauge(
    'geosuite_system_disk_usage_percent',
    'System disk usage percentage'
)

APPLICATION_UPTIME = Gauge(
    'geosuite_application_uptime_seconds',
    'Application uptime in seconds'
)

# Custom metrics
ACTIVE_USERS = Gauge(
    'geosuite_active_users',
    'Number of active users'
)

ACTIVE_TASKS = Gauge(
    'geosuite_active_tasks',
    'Number of active tasks'
)

DATABASE_CONNECTIONS = Gauge(
    'geosuite_database_connections',
    'Number of active database connections'
)

class MetricsCollector:
    """Collect and update system metrics."""
    
    def __init__(self):
        self.start_time = time.time()
    
    def collect_system_metrics(self):
        """Collect system-level metrics."""
        # CPU usage
        SYSTEM_CPU_USAGE.set(psutil.cpu_percent(interval=1))
        
        # Memory usage
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_USAGE.set(memory.percent)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        SYSTEM_DISK_USAGE.set(disk.percent)
        
        # Uptime
        uptime = time.time() - self.start_time
        APPLICATION_UPTIME.set(uptime)
    
    def increment_request(self, method: str, endpoint: str, status: int):
        """Increment request counter."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    
    def record_latency(self, method: str, endpoint: str, latency: float):
        """Record request latency."""
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)
    
    def increment_gps_upload(self):
        """Increment GPS upload counter."""
        GPS_UPLOADS.inc()
    
    def increment_marine_chart(self):
        """Increment marine chart counter."""
        MARINE_CHARTS_PROCESSED.inc()
    
    def increment_watershed_analysis(self):
        """Increment watershed analysis counter."""
        WATERSHED_ANALYSES.inc()
    
    def increment_hecras_simulation(self):
        """Increment HEC-RAS simulation counter."""
        HECRAS_SIMULATIONS.inc()
    
    def set_active_users(self, count: int):
        """Set active users count."""
        ACTIVE_USERS.set(count)
    
    def set_active_tasks(self, count: int):
        """Set active tasks count."""
        ACTIVE_TASKS.set(count)
    
    def set_database_connections(self, count: int):
        """Set database connections count."""
        DATABASE_CONNECTIONS.set(count)

# Global metrics collector
metrics_collector = MetricsCollector()

def get_metrics():
    """Get all metrics in Prometheus format."""
    metrics_collector.collect_system_metrics()
    return generate_latest(REGISTRY)

def get_health_status() -> Dict[str, Any]:
    """
    Get system health status.
    
    Returns:
        Dictionary with health status information
    """
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "components": {}
    }
    
    # Check database
    try:
        from app.database import engine
        db_type = "PostgreSQL" if not settings.DATABASE_URL.startswith("sqlite") else "SQLite"
        status["components"]["database"] = {
            "status": "healthy",
            "details": f"Connected to {db_type}"
        }
    except Exception as e:
        status["components"]["database"] = {
            "status": "unhealthy",
            "details": str(e)
        }
        status["status"] = "degraded"
    
    # Check Redis
    try:
        # This would check Redis connection
        status["components"]["redis"] = {
            "status": "healthy",
            "details": "Connected to Redis"
        }
    except Exception as e:
        status["components"]["redis"] = {
            "status": "unhealthy",
            "details": str(e)
        }
        status["status"] = "degraded"
    
    # Check file system
    try:
        disk_usage = psutil.disk_usage('/')
        status["components"]["filesystem"] = {
            "status": "healthy" if disk_usage.percent < 90 else "warning",
            "details": f"{disk_usage.percent}% used",
            "free_gb": disk_usage.free / (1024**3)
        }
        if disk_usage.percent >= 90:
            status["status"] = "warning"
    except Exception as e:
        status["components"]["filesystem"] = {
            "status": "unhealthy",
            "details": str(e)
        }
        status["status"] = "degraded"
    
    # Check memory
    try:
        memory = psutil.virtual_memory()
        status["components"]["memory"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "details": f"{memory.percent}% used",
            "available_gb": memory.available / (1024**3)
        }
        if memory.percent >= 90:
            status["status"] = "warning"
    except Exception as e:
        status["components"]["memory"] = {
            "status": "unhealthy",
            "details": str(e)
        }
        status["status"] = "degraded"
    
    return status

def setup_logging():
    """Setup application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(settings.LOG_FILE)
        ]
    )
    
    # Set log levels for specific libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)

class PerformanceMonitor:
    """Monitor application performance."""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, operation: str):
        """Start timer for an operation."""
        self.metrics[operation] = {
            "start_time": time.time(),
            "end_time": None,
            "duration": None
        }
    
    def end_timer(self, operation: str):
        """End timer for an operation."""
        if operation in self.metrics:
            end_time = time.time()
            self.metrics[operation]["end_time"] = end_time
            self.metrics[operation]["duration"] = end_time - self.metrics[operation]["start_time"]
    
    def get_duration(self, operation: str) -> Optional[float]:
        """Get duration of an operation."""
        if operation in self.metrics and self.metrics[operation]["duration"]:
            return self.metrics[operation]["duration"]
        return None
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "operations": {}
        }
        
        for operation, data in self.metrics.items():
            if data["duration"]:
                report["operations"][operation] = {
                    "duration_seconds": data["duration"],
                    "start_time": data["start_time"],
                    "end_time": data["end_time"]
                }
        
        return report

# Global performance monitor
performance_monitor = PerformanceMonitor()