"""
Computer Vision API routes — all CV operations exposed as REST endpoints.
Falls back to mock results when the CV engine or model weights are unavailable.
"""
import os
import io
import json
import uuid
import numpy as np
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from PIL import Image
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.geospatial import User, SurveyPlan
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/cv", tags=["computer-vision"])


class TransformRequest(BaseModel):
    easting: float
    northing: float
    direction: str = "cassini_to_utm"
    zone: str = "zone_3"
    method: str = "geodetic"


class BulkTransformRequest(BaseModel):
    coordinates: List[List[float]]
    direction: str = "cassini_to_utm"
    zone: str = "zone_3"
    method: str = "geodetic"


class GPSMatchRequest(BaseModel):
    points: List[List[float]]
    road_network_id: Optional[str] = None
    extent: Optional[List[float]] = None


_pipeline = None
_pipeline_error = None


def get_pipeline():
    global _pipeline, _pipeline_error
    if _pipeline is not None:
        return _pipeline
    if _pipeline_error is not None:
        return None
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from app.cv_engine.pipeline import CVPipeline
        model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cv_models')
        _pipeline = CVPipeline(model_dir=model_dir if os.path.exists(model_dir) else None)
        return _pipeline
    except Exception as e:
        _pipeline_error = str(e)
        return None


def load_image_from_upload(file_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    arr = np.array(img, dtype=np.float64)
    return arr


def _mock_digitize(filename: str, coordinate_system: str, zone: str) -> dict:
    return {
        "beacons": [
            {"x": 120, "y": 80, "width": 40, "height": 40, "beacon_type": "iron_pin", "confidence": 0.92},
            {"x": 300, "y": 160, "width": 40, "height": 40, "beacon_type": "concrete", "confidence": 0.87},
            {"x": 480, "y": 240, "width": 40, "height": 40, "beacon_type": "iron_pin", "confidence": 0.91},
        ],
        "boundaries": [
            {"points": [[120, 80], [300, 160], [480, 240], [120, 80]], "confidence": 0.85}
        ],
        "labels": [
            {"text": "L.R. 20946", "bbox": [10, 10, 120, 30], "confidence": 0.95, "type": "title_reference"},
            {"text": "SCALE 1:500", "bbox": [10, 40, 110, 55], "confidence": 0.91, "type": "scale"},
        ],
        "text_regions": [
            {"bbox": [10, 10, 120, 30], "confidence": 0.95},
            {"bbox": [10, 40, 110, 55], "confidence": 0.91},
        ],
        "processing_time_ms": 0,
        "total_beacons": 3,
        "total_boundaries": 1,
        "total_labels": 2,
        "filename": filename,
        "coordinate_system": coordinate_system,
        "zone": zone,
        "note": "Mock result - CV engine unavailable",
    }


def _mock_result(base: dict, filename: str, note: str = "Mock result - CV engine unavailable") -> dict:
    base["filename"] = filename
    base.setdefault("processing_time_ms", 0)
    base.setdefault("note", note)
    return base


@router.post("/digitize")
async def digitize_survey_plan(
    file: UploadFile = File(...),
    coordinate_system: str = Form("cassini"),
    zone: str = Form("zone_3"),
    confidence_threshold: float = Form(0.7),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = _mock_digitize(file.filename, coordinate_system, zone)
    else:
        result = pipeline.digitize_survey_plan(image)
        result["filename"] = file.filename
        result.setdefault("processing_time_ms", 0)
        result.setdefault("note", "Real CV result")
        result["coordinate_system"] = coordinate_system
        result["zone"] = zone

    plan = SurveyPlan(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name=file.filename,
        file_path="",
        coordinate_system=coordinate_system,
        zone=zone,
        status="completed",
        result=result,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    result["plan_id"] = str(plan.id)
    return JSONResponse(content=result)


@router.post("/features")
async def extract_features(
    file: UploadFile = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = {"features": [], "total": 0, "note": "CV engine unavailable"}
    else:
        result = pipeline.extract_features(image)
        result["filename"] = file.filename
        result.setdefault("note", "Real CV result")
    return JSONResponse(content=result)


@router.post("/changes")
async def detect_changes(
    file_before: UploadFile = File(...),
    file_after: UploadFile = File(...),
    threshold: float = Form(0.3),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents_before = await file_before.read()
    contents_after = await file_after.read()
    try:
        img_before = load_image_from_upload(contents_before)
        img_after = load_image_from_upload(contents_after)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load images: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = {"changes": [], "total_changes": 0, "note": "CV engine unavailable"}
    else:
        result = pipeline.detect_changes(img_before, img_after)
        result["filename"] = file_before.filename
        result["filename_after"] = file_after.filename
        result.setdefault("note", "Real CV result")
    return JSONResponse(content=result)


@router.post("/gps-match")
async def match_gps_track(request: GPSMatchRequest, token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    gps_array = np.array(request.points)
    pipeline = get_pipeline()
    extent = tuple(request.extent) if request.extent else None
    if pipeline is None:
        result = {"matched_track": gps_array.tolist(), "snap_distances": [], "note": "CV engine unavailable"}
    else:
        result = pipeline.match_gps_track(gps_array, extent=extent)
    return JSONResponse(content=result)


@router.post("/symbols")
async def recognize_symbols(file: UploadFile = File(...), token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        symbols = []
    else:
        symbols = pipeline.recognize_symbols(image)
    return JSONResponse(content={"symbols": symbols, "total": len(symbols), "filename": file.filename})


@router.post("/soundings")
async def extract_soundings(file: UploadFile = File(...), token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = {"soundings": [], "total": 0, "note": "CV engine unavailable"}
    else:
        result = pipeline.extract_depth_soundings(image)
        result["filename"] = file.filename
        result.setdefault("note", "Real CV result")
    return JSONResponse(content=result)


@router.post("/land-use")
async def classify_land_use(file: UploadFile = File(...), token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = {"classes": {}, "dominant_class": "unknown", "note": "CV engine unavailable"}
    else:
        result = pipeline.classify_land_use(image)
        result["filename"] = file.filename
        result.setdefault("note", "Real CV result")
    return JSONResponse(content=result)


@router.post("/text")
async def extract_text(file: UploadFile = File(...), token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        text_regions = []
    else:
        text_regions = pipeline.extract_text(image)
    return JSONResponse(content={"text_regions": text_regions, "total": len(text_regions), "filename": file.filename})


@router.post("/fast-digitize")
async def fast_digitize(file: UploadFile = File(...), token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    contents = await file.read()
    try:
        image = load_image_from_upload(contents)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load image: {e}")

    pipeline = get_pipeline()
    if pipeline is None:
        result = {
            "beacons": [],
            "boundaries": [],
            "text_regions": [],
            "total_beacons": 0,
            "total_boundaries": 0,
            "total_text_regions": 0,
            "filename": file.filename,
            "note": "CV engine unavailable",
        }
    else:
        result = pipeline.fast_digitize(image)
        result["filename"] = file.filename
        result.setdefault("note", "Real CV result")
    return JSONResponse(content=result)


@router.get("/models")
async def get_model_info():
    pipeline = get_pipeline()
    if pipeline is None:
        return JSONResponse(content={
            "engine": "KLISS CV Engine",
            "status": "unavailable",
            "error": _pipeline_error or "CV engine not initialized",
            "models": {},
        })
    return JSONResponse(content=pipeline.get_model_info())


@router.get("/capabilities")
async def get_capabilities():
    pipeline = get_pipeline()
    engine_version = "KLISS CV Engine v0.1.0"
    if pipeline is None:
        return {
            "engine": engine_version,
            "status": "degraded",
            "note": "Running in mock mode - model weights not loaded",
            "dependencies": "NumPy only",
            "modules": {
                "digitize": {"endpoint": "/api/v1/cv/digitize", "method": "POST", "description": "Auto-extract beacons, boundaries and labels from scanned survey plans", "input": "Image file", "output": "Beacon coordinates, boundary polylines, extracted text labels"},
                "features": {"endpoint": "/api/v1/cv/features", "method": "POST", "description": "Classify pixels in drone/satellite imagery", "input": "Image file", "output": "Semantic segmentation map"},
                "changes": {"endpoint": "/api/v1/cv/changes", "method": "POST", "description": "Detect changes between two images", "input": "Two image files", "output": "Change map"},
                "gps_match": {"endpoint": "/api/v1/cv/gps-match", "method": "POST", "description": "Snap noisy GPS track to nearest road", "input": "GPS coordinate list", "output": "Matched track"},
                "symbols": {"endpoint": "/api/v1/cv/symbols", "method": "POST", "description": "Detect map symbols", "input": "Image file", "output": "Symbol locations and types"},
                "soundings": {"endpoint": "/api/v1/cv/soundings", "method": "POST", "description": "Extract depth values from nautical chart rasters", "input": "Nautical chart image", "output": "Sounding positions and depths"},
                "land_use": {"endpoint": "/api/v1/cv/land-use", "method": "POST", "description": "Classify satellite imagery into land use categories", "input": "Satellite image", "output": "Land use class probabilities"},
                "text": {"endpoint": "/api/v1/cv/text", "method": "POST", "description": "Extract text labels from map images", "input": "Map image", "output": "Text regions with bounding boxes"},
                "fast_digitize": {"endpoint": "/api/v1/cv/fast-digitize", "method": "POST", "description": "Traditional CV digitization", "input": "Survey plan image", "output": "Beacons, boundaries, text regions"},
            },
        }
    return {
        "engine": engine_version,
        "status": "ready",
        "dependencies": "NumPy only",
        "modules": pipeline.get_capabilities() if hasattr(pipeline, 'get_capabilities') else {},
    }
