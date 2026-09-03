"""
GeoSuite — Native development launcher.
Starts the FastAPI backend without Docker.

Usage:
    python run_dev.py              # Start backend only
    python run_dev.py --all        # Start backend + Celery worker
"""
import os
import sys
import argparse
import subprocess
import time
import signal

# Ensure we're in the backend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Load .env
from dotenv import load_dotenv
load_dotenv()

from app.config import settings


def print_banner():
    db_type = "SQLite" if "sqlite" in settings.DATABASE_URL else "PostgreSQL"
    redis_ok = _check_redis()
    print(f"""
╔══════════════════════════════════════════════════╗
║              GeoSuite v{settings.APP_VERSION}                    ║
║          Geospatial Analytical Toolkit           ║
╠══════════════════════════════════════════════════╣
║  API       http://localhost:8000                 ║
║  Docs      http://localhost:8000/docs            ║
║  Health    http://localhost:8000/health           ║
║  Database  {db_type:<37} ║
║  Redis     {"Connected" if redis_ok else "Offline (tasks sync):<27} ║
╚══════════════════════════════════════════════════╝
""")


def _check_redis():
    import socket
    try:
        sock = socket.create_connection(("localhost", 6379), timeout=2)
        sock.close()
        return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


def run_backend():
    import uvicorn
    print_banner()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


def run_celery():
    """Start Celery worker (requires Redis)."""
    if not _check_redis():
        print("[!] Redis not running — Celery tasks disabled.")
        print("    Install Redis or use Docker: docker run -d -p 6379:6379 redis:7-alpine")
        return

    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.workers.celery_worker.celery_app",
        "worker", "--loglevel=info", "--concurrency=2",
    ]
    return subprocess.Popen(cmd)


def main():
    parser = argparse.ArgumentParser(description="GeoSuite Dev Launcher")
    parser.add_argument("--all", action="store_true", help="Start backend + Celery worker")
    args = parser.parse_args()

    processes = []

    if args.all:
        celery_proc = run_celery()
        if celery_proc:
            processes.append(celery_proc)

    try:
        run_backend()
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            p.terminate()
            p.wait()


if __name__ == "__main__":
    main()
