"""
Drone survey routes.
Handles survey CRUD, image upload with EXIF extraction, and ODM processing.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime

from app.database import get_db
from app.models.geospatial import User, DroneSurvey, DroneImage
from app.services.drone_service import DroneSurveyService
from app.services.auth_service import auth_service

router = APIRouter()
drone_service = DroneSurveyService()


@router.post("/surveys")
async def create_survey(
    name: str = Form(...),
    description: str = Form(""),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    survey_info = drone_service.create_survey(name, description, user_id=str(user.id))

    survey = DroneSurvey(
        id=uuid.UUID(survey_info["survey_id"]),
        user_id=user.id,
        name=name,
        description=description,
        status="uploaded",
        orthomosaic_path="",
        dsm_path="",
        dtm_path="",
        point_cloud_path="",
        tile_path="",
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    return {
        "survey_id": survey_info["survey_id"],
        "name": survey.name,
        "description": survey.description,
        "status": survey.status,
        "message": "Survey created. Upload images next.",
    }


@router.post("/surveys/{survey_id}/upload")
async def upload_images(
    survey_id: str,
    files: List[UploadFile] = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        survey_uuid = uuid.UUID(survey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid survey ID format")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == survey_uuid,
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found. Create it first.")

    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if not os.path.exists(survey_dir):
        os.makedirs(survey_dir, exist_ok=True)

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

            image = DroneImage(
                id=uuid.uuid4(),
                survey_id=survey.id,
                file_name=file.filename,
                file_path=meta.get("file_path", ""),
                file_size=meta.get("file_size", 0),
                latitude=meta.get("latitude"),
                longitude=meta.get("longitude"),
                altitude=meta.get("altitude"),
                focal_length=meta.get("focal_length"),
                sensor_width=meta.get("sensor_width"),
                sensor_height=meta.get("sensor_height"),
                image_width=meta.get("image_width"),
                image_height=meta.get("image_height"),
                gimbal_pitch=meta.get("gimbal_pitch"),
                gimbal_yaw=meta.get("gimbal_yaw"),
                gimbal_roll=meta.get("gimbal_roll"),
            )
            db.add(image)
            results.append(meta)
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})

    survey.image_count = (survey.image_count or 0) + len(results)
    db.commit()

    return {
        "survey_id": survey_id,
        "uploaded": len(results),
        "errors": len(errors),
        "images": results,
        "error_details": errors,
    }


@router.post("/surveys/{survey_id}/finalize")
async def finalize_survey(
    survey_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        survey_uuid = uuid.UUID(survey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid survey ID format")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == survey_uuid,
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    stats = drone_service.finalize_upload(survey_id)
    if "error" in stats:
        raise HTTPException(status_code=400, detail=stats["error"])

    survey.bounds = stats.get("bounds")
    survey.area_hectares = stats.get("area_hectares")
    survey.status = "ready"
    db.commit()
    db.refresh(survey)

    return {
        "survey_id": survey_id,
        **stats,
        "message": "Survey finalized. Ready for processing.",
    }


@router.get("/surveys")
async def list_surveys(
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    surveys = db.query(DroneSurvey).filter(
        DroneSurvey.user_id == user.id
    ).order_by(DroneSurvey.created_at.desc()).all()

    return {
        "surveys": [
            {
                "survey_id": str(s.id),
                "name": s.name,
                "description": s.description,
                "status": s.status,
                "image_count": s.image_count or 0,
                "bounds": s.bounds,
                "area_hectares": s.area_hectares,
                "camera_model": s.camera_model,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in surveys
        ],
        "total": len(surveys),
    }


@router.get("/surveys/{survey_id}")
async def get_survey(
    survey_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        survey_uuid = uuid.UUID(survey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid survey ID format")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == survey_uuid,
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    images = drone_service.get_survey_images(survey_id)
    stats = drone_service.finalize_upload(survey_id)
    if "error" in stats:
        stats = {}

    return {
        "survey_id": survey_id,
        "name": survey.name,
        "description": survey.description,
        "status": survey.status,
        "image_count": survey.image_count or len(images),
        "bounds": survey.bounds or stats.get("bounds"),
        "area_hectares": survey.area_hectares or stats.get("area_hectares"),
        "camera_model": survey.camera_model,
        "progress": survey.progress,
        "progress_message": survey.progress_message,
        "error_message": survey.error_message,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
        "processing_started_at": survey.processing_started_at.isoformat() if survey.processing_started_at else None,
        "processing_completed_at": survey.processing_completed_at.isoformat() if survey.processing_completed_at else None,
        "images": images,
        **stats,
    }


@router.get("/surveys/{survey_id}/images/{image_name}")
async def get_image_metadata(
    survey_id: str,
    image_name: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == uuid.UUID(survey_id),
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    image_path = os.path.join(drone_service.upload_dir, survey_id, "images", image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    meta = drone_service.extractor.extract(image_path)
    return {"file_name": image_name, **meta}


@router.delete("/surveys/{survey_id}")
async def delete_survey(
    survey_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        survey_uuid = uuid.UUID(survey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid survey ID format")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == survey_uuid,
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    db.delete(survey)
    db.commit()

    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    if os.path.exists(survey_dir):
        import shutil
        shutil.rmtree(survey_dir, ignore_errors=True)

    return {"survey_id": survey_id, "message": "Survey deleted"}


@router.post("/surveys/{survey_id}/process")
async def process_survey(
    survey_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        survey_uuid = uuid.UUID(survey_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid survey ID format")

    survey = db.query(DroneSurvey).filter(
        DroneSurvey.id == survey_uuid,
        DroneSurvey.user_id == user.id,
    ).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    survey_dir = os.path.join(drone_service.upload_dir, survey_id)
    images_dir = os.path.join(survey_dir, "images")
    output_dir = os.path.join(survey_dir, "output")

    if not os.path.exists(images_dir) or not os.listdir(images_dir):
        raise HTTPException(status_code=400, detail="No images in survey")

    survey.status = "processing"
    survey.processing_started_at = datetime.utcnow()
    db.commit()

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
    except Exception:
        from app.services.odm_service import ODMService
        from app.config import settings

        odm = ODMService(
            odm_path=settings.ODM_PATH or "run.py",
            use_docker=settings.ODM_DOCKER,
        )

        if not odm.is_available():
            survey.status = "failed"
            survey.error_message = "OpenDroneMap is not installed and Celery is unavailable."
            db.commit()
            raise HTTPException(
                status_code=503,
                detail="OpenDroneMap is not installed and Celery is unavailable. "
                       "Install ODM or start Redis + Celery worker."
            )

        result = odm.process_survey(images_dir, output_dir)
        survey.status = "completed" if result.get("success") else "failed"
        survey.processing_completed_at = datetime.utcnow()
        survey.progress = 1.0 if result.get("success") else 0.0
        survey.progress_message = "Processing complete" if result.get("success") else result.get("error")
        survey.error_message = result.get("error")
        survey.orthomosaic_path = result.get("files", {}).get("orthophoto", "")
        survey.dsm_path = result.get("files", {}).get("dsm", "")
        survey.dtm_path = result.get("files", {}).get("dtm", "")
        survey.point_cloud_path = result.get("files", {}).get("point_cloud", "")
        survey.tile_path = result.get("files", {}).get("tiles", "")
        db.commit()

        return {"survey_id": survey_id, "result": result}
