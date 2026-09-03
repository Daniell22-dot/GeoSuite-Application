"""
Task management routes.
Dispatch Celery tasks and poll their status/results.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.workers.celery_worker import celery_app

router = APIRouter()


class TaskDispatchRequest(BaseModel):
    task_name: str
    args: list = []
    kwargs: Dict[str, Any] = {}


class WatershedTaskRequest(BaseModel):
    dem_path: str
    pour_point: Dict[str, float]


class MarineTaskRequest(BaseModel):
    chart_path: str


class BatchGpxRequest(BaseModel):
    gpx_files: list
    correct_elevation: bool = True


class ElevationProfileRequest(BaseModel):
    coordinates: list
    dem_source: str = "srtm"


class MergeChartsRequest(BaseModel):
    chart_paths: list
    output_format: str = "geotiff"


TASK_MAP = {
    'process_watershed_analysis': 'process_watershed_analysis',
    'process_marine_chart': 'process_marine_chart',
    'batch_process_gpx': 'batch_process_gpx',
    'generate_elevation_profile': 'generate_elevation_profile',
    'merge_marine_charts': 'merge_marine_charts',
}


@router.post("/dispatch")
async def dispatch_task(request: TaskDispatchRequest):
    """Dispatch a named Celery task with arbitrary args/kwargs."""
    task_name = TASK_MAP.get(request.task_name)
    if not task_name:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task: {request.task_name}. "
                   f"Available: {list(TASK_MAP.keys())}"
        )

    task = celery_app.send_task(task_name, args=request.args, kwargs=request.kwargs)
    return {"task_id": task.id, "status": "PENDING", "task_name": request.task_name}


@router.post("/dispatch/watershed")
async def dispatch_watershed(request: WatershedTaskRequest):
    task = celery_app.send_task(
        'process_watershed_analysis',
        args=[request.dem_path, request.pour_point],
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/dispatch/marine")
async def dispatch_marine(request: MarineTaskRequest):
    task = celery_app.send_task(
        'process_marine_chart',
        args=[request.chart_path],
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/dispatch/batch-gpx")
async def dispatch_batch_gpx(request: BatchGpxRequest):
    task = celery_app.send_task(
        'batch_process_gpx',
        args=[request.gpx_files, request.correct_elevation],
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/dispatch/elevation-profile")
async def dispatch_elevation_profile(request: ElevationProfileRequest):
    task = celery_app.send_task(
        'generate_elevation_profile',
        args=[request.coordinates, request.dem_source],
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.post("/dispatch/merge-charts")
async def dispatch_merge_charts(request: MergeChartsRequest):
    task = celery_app.send_task(
        'merge_marine_charts',
        args=[request.chart_paths, request.output_format],
    )
    return {"task_id": task.id, "status": "PENDING"}


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """Poll task status, progress, and result."""
    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }

    if result.status == 'PROGRESS':
        info = result.info or {}
        response["progress"] = info.get('progress', 0)
        response["status_message"] = info.get('status', '')

    elif result.status == 'SUCCESS':
        response["result"] = result.result

    elif result.status == 'FAILURE':
        response["error"] = str(result.info)

    return response


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """Revoke a running task."""
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "status": "REVOKED"}
