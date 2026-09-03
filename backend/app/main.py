import os
import sys

# R integration — only set if R_HOME not already configured
if 'R_HOME' not in os.environ:
    r_home_candidates = []
    if settings.R_HOME:
        r_home_candidates.append(settings.R_HOME)
    r_home_candidates.extend([
        '/usr/lib/R',
        '/usr/local/lib/R',
        '/opt/R',
    ])
    for candidate in r_home_candidates:
        if os.path.exists(candidate):
            os.environ['R_HOME'] = candidate
            r_bin = os.path.join(candidate, 'bin', 'x64' if os.name == 'nt' else '')
            if os.path.exists(r_bin):
                os.environ['PATH'] = r_bin + os.pathsep + os.environ.get('PATH', '')
                if hasattr(os, 'add_dll_directory'):
                    try:
                        os.add_dll_directory(r_bin)
                    except Exception:
                        pass
            break

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.routes import gps_routes, marine_routes, watershed_routes, file_routes, terminal_routes, weather_routes
from app.routes import auth_routes, export_routes, monitoring_routes, task_routes, drone_routes, transform_routes
from app.routes import cv_routes, annotate_routes, config_routes
from app.config import settings
from app.models.geospatial import init_db

load_dotenv()

if os.name == 'nt':
    conda_bin = os.path.join(os.environ.get('CONDA_PREFIX', ''), 'Library', 'bin')
    if os.path.exists(conda_bin):
        os.add_dll_directory(conda_bin)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print(" Starting GeoSuite Backend...")
    init_db()
    print(" Database initialized")
    
    # Create necessary directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("data/temp", exist_ok=True)
    os.makedirs("data/output", exist_ok=True)
    os.makedirs("data/dem", exist_ok=True)
    os.makedirs("data/drone_surveys", exist_ok=True)
    
    yield
    
    # Shutdown
    print(" Shutting down GeoSuite Backend...")

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Complete Geospatial Processing Platform with GPS, Marine Charts, and Watershed Modeling",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

ORIGINS = [o.strip() for o in settings.BACKEND_CORS_ORIGINS if o.strip()]
# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files for public OUTPUTS ONLY (DEM terrain & generated outputs).
# Raw user uploads (uploads/, drone_surveys/, temp/) are intentionally NOT
# served statically — they must only be reachable through authenticated API routes.
# Override the list via PUBLIC_DATA_DIRS (comma-separated) if you need more.
public_dirs = [d.strip() for d in os.getenv("PUBLIC_DATA_DIRS", "dem,output").split(",") if d.strip()]
for _d in public_dirs:
    _path = os.path.join("data", _d)
    if os.path.isdir(_path):
        app.mount(f"/data/{_d}", StaticFiles(directory=_path), name=f"data_{_d}")

# Include routes
app.include_router(gps_routes.router, prefix="/api/v1/gps", tags=["GPS"])
app.include_router(marine_routes.router, prefix="/api/v1/marine", tags=["Marine"])
app.include_router(watershed_routes.router, prefix="/api/v1/watershed", tags=["Watershed"])
app.include_router(file_routes.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(terminal_routes.router, prefix="/api/v1/terminal", tags=["Terminal"])
app.include_router(weather_routes.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(export_routes.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(monitoring_routes.router, prefix="/api/v1/monitoring", tags=["Monitoring"])
app.include_router(task_routes.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(drone_routes.router, prefix="/api/v1/drone", tags=["Drone"])
app.include_router(transform_routes.router, prefix="/api/v1/transform", tags=["Coordinate Transform"])
app.include_router(cv_routes.router, tags=["Computer Vision"])
app.include_router(annotate_routes.router, tags=["Annotation"])
app.include_router(config_routes.router, prefix="/api/v1/config", tags=["Config"])

@app.get("/")
async def root():
    return {
        "message": f" {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "endpoints": {
            "gps": "/api/v1/gps",
            "marine": "/api/v1/marine",
            "watershed": "/api/v1/watershed",
            "files": "/api/v1/files",
            "auth": "/api/v1/auth",
            "export": "/api/v1/export",
            "weather": "/api/v1/weather",
            "monitoring": "/api/v1/monitoring",
            "tasks": "/api/v1/tasks",
            "drone": "/api/v1/drone",
            "transform": "/api/v1/transform",
            "config": "/api/v1/config",
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME.lower().replace(" ", "-")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )