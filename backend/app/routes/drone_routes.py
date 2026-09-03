"""
Drone survey routes.
Handles image upload, EXIF extraction, and survey management.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from app.database import get_db
from app.models.geospatial import DroneSurvey, DroneImage, User
from app.services.drone_service import DroneSurveyService

router = APIRouter()
drone_service = DroneSurveyService()


@router.post("/surveys")
async def create_survey(
    name: str = Form(...),
    description: str = Form(""),
):
    """Create a new drone survey (empty container for images)."""
    survey_info = drone_service.create_survey(name, description)

    return {
        "survey_id": survey_info["survey_id"],
        "name": name,
        "description": description,
        "status": "uploaded",
        "message": "Survey created. Upload images next.",
    }


@router.post("/surveys/{survey_id}/upload")
async def upload_images(
    survey_id: str,
    files: List[UploadFile] = File(...),
):
    """
    Upload one or more drone images to a survey.
    Extracts EXIF GPS + camera metadata from each image.
    """
    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        raise HTTPException(status_code=404, detail="Survey not found. Create it first.")

    results = []
    errors = []

    for file in files:
        if not file.filename:
            errors.append({"file": "unknown", "error": "No filename"})
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.tif', '.tiff', '.png'):
            errors.append({"file": file.filename, "error": f"Unsupported format: {ext}"})
            continue

        try:
            content = await file.read()
            meta = drone_service.add_image(survey_dir, file.filename, content)
            results.append(meta)
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    return {
        "survey_id": survey_id,
        "uploaded": len(results),
        "errors": len(errors),
        "images": results,
        "error_details": errors,
    }


@router.post("/surveys/{survey_id}/finalize")
async def finalize_survey(survey_id: str):
    """
    Finalize upload — computes survey bounds, area, and image count.
    Call after all images are uploaded.
    """
    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        raise HTTPException(status_code=404, detail="Survey not found")

    stats = drone_service.finalize_upload(survey_id)

    if "error" in stats:
        raise HTTPException(status_code=400, detail=stats["error"])

    return {
        "survey_id": survey_id,
        **stats,
        "message": "Survey finalized. Ready for processing.",
    }


@router.get("/surveys/{survey_id}")
async def get_survey(survey_id: str):
    """Get survey details and image list."""
    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        raise HTTPException(status_code=404, detail="Survey not found")

    images = drone_service.get_survey_images(survey_id)
    stats = drone_service.finalize_upload(survey_id)

    return {
        "survey_id": survey_id,
        "images": images,
        **stats,
    }


@router.get("/surveys/{survey_id}/images/{image_name}")
async def get_image_metadata(survey_id: str, image_name: str):
    """Get EXIF metadata for a single image."""
    import os
    image_path = os.path.join(drone_service.upload_dir, survey_id, "images", image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    meta = drone_service.extractor.extract(image_path)
    return {"file_name": image_name, **meta}


@router.get("/surveys")
async def list_surveys():
    """List all drone surveys."""
    surveys = []
    if os.path.exists(drone_service.upload_dir):
        for d in os.listdir(drone_service.upload_dir):
            survey_dir = os.path.join(drone_service.upload_dir, d)
            if os.path.isdir(survey_dir):
                images_dir = os.path.join(survey_dir, "images")
                image_count = 0
                if os.path.exists(images_dir):
                    image_count = len([
                        f for f in os.listdir(images_dir)
                        if f.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png'))
                    ])
                surveys.append({
                    "survey_id": d,
                    "image_count": image_count,
                })

    return {"surveys": surveys, "total": len(surveys)}


@router.delete("/surveys/{survey_id}")
async def delete_survey(survey_id: str):
    """Delete a survey and all its images."""
    import shutil
    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        raise HTTPException(status_code=404, detail="Survey not found")

    shutil.rmtree(survey_dir)
    return {"survey_id": survey_id, "message": "Survey deleted"}


@router.post("/surveys/{survey_id}/process")
async def process_survey(survey_id: str):
    """
    Launch ODM processing for a survey via Celery.
    Returns a task_id for polling progress.
    """
    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        raise HTTPException(status_code=404, detail="Survey not found")

    images_dir = os.path.join(survey_dir, "images")
    output_dir = os.path.join(survey_dir, "output")

    if not os.path.exists(images_dir) or not os.listdir(images_dir):
        raise HTTPException(status_code=400, detail="No images in survey")

    # Dispatch to Celery
    try:
        from app.workers.celery_worker import celery_app
        task = celery_app.send_task(
            'process_drone_survey',
            args=[survey_id, images_dir, output_dir],
        )
        return {
            "survey_id": survey_id,
            "task_id": task.id,
            "status": "PENDING",
            "message": "Processing started. Poll GET /api/v1/tasks/{task_id} for progress.",
        }
    except Exception as e:
        # Celery/Redis not available — run synchronously as fallback
        from app.services.odm_service import ODMService
        from app.config import settings

        odm = ODMService(
            odm_path=settings.ODM_PATH or "run.py",
            use_docker=settings.ODM_DOCKER,
        )

        if not odm.is_available():
            raise HTTPException(
                status_code=503,
                detail="OpenDroneMap is not installed and Celery is unavailable. "
                       "Install ODM or start Redis + Celery worker."
            )

        result = odm.process_survey(images_dir, output_dir)
        return {"survey_id": survey_id, "result": result}
