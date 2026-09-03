"""
HEC-RAS API routes.
Provides standalone hydrological analysis without requiring HEC-RAS installation.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Optional
import uuid
import os
import io
import json
import tempfile
import numpy as np

from app.services.hecras_service import hecras_service
from app.database import get_db
from app.models.geospatial import User, HECRASAnalysis, WatershedAnalysis
from app.services.auth_service import auth_service

router = APIRouter()


def _get_or_create_default_watershed(db: Session, user_id) -> Optional[WatershedAnalysis]:
    return db.query(WatershedAnalysis).filter(WatershedAnalysis.user_id == user_id).first()


@router.post("/create")
async def create_model(
    payload: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Create a standalone hydraulic model.
    Expected payload:
    {
      "name": "River Reach Analysis",
      "watershed_id": "<uuid>",           # optional
      "geometry": {
        "cross_sections": [
          {
            "station": 0,
            "elevations": [100.0, 99.5, 99.0, 98.5],
            "distances": [0, 20, 40, 60],
            "mannings_n": 0.035
          }
        ],
        "reach_length_m": 1000,
        "slope": 0.001
      },
      "flow": {
        "discharge_m3s": 50.0,
        "type": "steady"
      }
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    name = payload.get("name") or f"HEC-RAS Analysis {uuid.uuid4().hex[:6]}"
    geometry = payload.get("geometry") or {}
    flow = payload.get("flow") or {}
    watershed_id = payload.get("watershed_id")
    watershed = None
    if watershed_id:
        try:
            watershed = db.query(WatershedAnalysis).filter(
                WatershedAnalysis.id == uuid.UUID(watershed_id),
                WatershedAnalysis.user_id == user.id,
            ).first()
        except ValueError:
            watershed = None
    if watershed is None:
        watershed = _get_or_create_default_watershed(db, user.id)

    output_dir = os.path.join("data", "hecras")
    os.makedirs(output_dir, exist_ok=True)

    model = hecras_service.create_steady_flow_model(geometry, flow, output_dir)

    analysis = HECRASAnalysis(
        id=uuid.uuid4(),
        user_id=user.id,
        watershed_id=watershed.id if watershed else None,
        name=name,
        analysis_type=flow.get("type", "steady"),
        geometry_file=model.get("geometry_file", ""),
        plan_file=model.get("plan_file", ""),
        results_file=model.get("results_file", ""),
        parameters={
            "geometry": geometry,
            "flow": flow,
        },
        results=model.get("results", {}),
        status="completed" if model.get("success") else "failed",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "success": True,
        "model_id": str(analysis.id),
        "name": analysis.name,
        "status": analysis.status,
        "project_dir": model.get("project_dir"),
        "note": model.get("note"),
    }


@router.post("/run/{model_id}")
async def run_simulation(
    model_id: str,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        analysis_uuid = uuid.UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model ID format")

    analysis = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.id == analysis_uuid,
        HECRASAnalysis.user_id == user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Model not found")

    geometry = analysis.parameters.get("geometry", {}) if analysis.parameters else {}
    flow = analysis.parameters.get("flow", {}) if analysis.parameters else {}
    output_dir = os.path.join("data", "hecras")
    os.makedirs(output_dir, exist_ok=True)

    result = hecras_service.run_steady_flow_analysis(
        analysis.geometry_file or analysis.results_file or "",
        analysis.plan_file or "",
    )
    if not result.get("success") and "note" not in result:
        result = hecras_service.run_standalone_analysis(geometry, flow, output_dir)

    analysis.status = "completed" if result.get("success") else "failed"
    analysis.results = result.get("results", analysis.results)
    analysis.completed_at = result.get("completed_at")
    db.commit()
    db.refresh(analysis)

    return {
        "success": result.get("success", False),
        "model_id": str(analysis.id),
        "status": analysis.status,
        "results": analysis.results,
        "note": result.get("note"),
    }


@router.get("/results/{simulation_id}")
async def get_results(
    simulation_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        analysis_uuid = uuid.UUID(simulation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid simulation ID format")

    analysis = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.id == analysis_uuid,
        HECRASAnalysis.user_id == user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {
        "success": True,
        "simulation_id": str(analysis.id),
        "status": analysis.status,
        "results": analysis.results or {},
        "parameters": analysis.parameters or {},
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
    }


@router.post("/inundation")
async def calculate_inundation(
    payload: Dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    terrain_file = payload.get("terrain_file")
    wse_data = payload.get("wse_data") or {}
    if not terrain_file and not wse_data:
        raise HTTPException(status_code=400, detail="terrain_file or wse_data is required")

    result = hecras_service.calculate_flood_inundation(terrain_file, wse_data)
    return result


@router.get("/analyses")
async def list_analyses(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    analyses = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.user_id == user.id
    ).order_by(HECRASAnalysis.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "analyses": [
            {
                "id": str(a.id),
                "name": a.name,
                "analysis_type": a.analysis_type,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in analyses
        ],
        "total": db.query(HECRASAnalysis).filter(HECRASAnalysis.user_id == user.id).count(),
    }


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.id == analysis_uuid,
        HECRASAnalysis.user_id == user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    db.delete(analysis)
    db.commit()
    return {"success": True, "message": "Analysis deleted successfully"}


@router.post("/stormwater")
async def stormwater_analysis(
    payload: Dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Run standalone stormwater/hydrological analysis.
    Payload example:
    {
      "method": "rational",       # or "scs"
      "catchment_area_km2": 1.2,
      "rainfall_mm_per_hr": 75,
      "runoff_coefficient": 0.6,
      "slope": 0.02,
      "land_use": "urban"
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = hecras_service.run_stormwater_analysis(payload)
    return result


@router.post("/{analysis_id}/cross-section")
async def generate_cross_section_plot(
    analysis_id: str,
    payload: Dict,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.id == analysis_uuid,
        HECRASAnalysis.user_id == user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    cross_section_index = payload.get("cross_section_index", 0)
    img_bytes = hecras_service.generate_cross_section_plot(analysis.parameters or {}, cross_section_index)
    if img_bytes is None:
        raise HTTPException(status_code=400, detail="No cross-section data available")

    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=cross_section_{analysis_id}.png"},
    )


@router.get("/{analysis_id}/long-profile")
async def generate_long_profile_plot(
    analysis_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    analysis = db.query(HECRASAnalysis).filter(
        HECRASAnalysis.id == analysis_uuid,
        HECRASAnalysis.user_id == user.id,
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    img_bytes = hecras_service.generate_long_profile_plot(analysis.parameters or {}, analysis.results or {})
    if img_bytes is None:
        raise HTTPException(status_code=400, detail="No profile data available")

    return StreamingResponse(
        io.BytesIO(img_bytes),
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=long_profile_{analysis_id}.png"},
    )
