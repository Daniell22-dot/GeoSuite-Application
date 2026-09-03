"""
Marine chart processing routes.
Handles nautical chart files, soundings extraction, and chart merging.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import tempfile
import os
import uuid
import io

from app.services.marine_service import MarineChartService
from app.utils.gdal_wrapper import GDALWrapper
from app.database import get_db
from app.models.geospatial import User, MarineChart
from app.services.auth_service import auth_service

router = APIRouter()
marine_service = MarineChartService()
gdal_wrapper = GDALWrapper()

@router.post("/upload")
async def upload_marine_chart(
    file: UploadFile = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Upload a marine chart file.
    
    Supported formats:
    - KAP/BSB (.kap, .bsb): Nautical chart formats
    - CAD (.dwg, .dxf): AutoCAD formats
    - GeoTIFF (.tif, .tiff): Georeferenced charts
    - PNG/JPG with world file (.png, .jpg, .jpeg)
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    supported_extensions = ['.kap', '.bsb', '.dwg', '.dxf', '.tif', '.tiff', '.png', '.jpg', '.jpeg']
    
    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported chart format. Supported: {', '.join(supported_extensions)}"
        )
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Process chart file
        if file_ext in ['.kap', '.bsb']:
            result = marine_service.process_kap_file(temp_path, chart_id=str(chart_id))
        elif file_ext in ['.dwg', '.dxf']:
            result = marine_service.process_cad_file(temp_path)
        else:
            result = gdal_wrapper.process_raster_file(temp_path)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to process chart file'))
        
        # Generate unique filename
        chart_id = uuid.uuid4()
        chart_filename = f"chart_{chart_id}{file_ext}"
        chart_path = os.path.join("data", "marine", chart_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(chart_path), exist_ok=True)
        
        # Move file to permanent location
        os.rename(temp_path, chart_path)
        
        # Create database record
        chart = MarineChart(
            id=chart_id,
            user_id=user.id,
            name=file.filename,
            chart_number=result.get('metadata', {}).get('chart_number'),
            scale=result.get('metadata', {}).get('scale'),
            projection=result.get('metadata', {}).get('projection'),
            bounds=result.get('bounds'),
            file_path=chart_path,
            file_type=file_ext[1:].upper(),
            metadata=result.get('metadata', {}),
        )
        
        db.add(chart)
        db.commit()
        db.refresh(chart)
        
        # Generate thumbnail
        thumbnail_data = marine_service.generate_thumbnail(chart_path)
        if thumbnail_data:
            chart.thumbnail = thumbnail_data
            db.commit()
        
        return {
            "success": True,
            "message": "Marine chart uploaded successfully",
            "chart_id": str(chart.id),
            "data": result
        }
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing chart file: {str(e)}")

@router.post("/process-kap")
async def process_kap_file(
    file: UploadFile = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Process KAP/BSB nautical chart file.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ('.kap', '.bsb'):
        raise HTTPException(status_code=400, detail="Expected KAP/BSB file")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        result = marine_service.process_kap_file(temp_path)
        os.unlink(temp_path)
        return result
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"KAP processing failed: {str(e)}")

@router.post("/process-cad")
async def process_cad_file(
    file: UploadFile = File(...),
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Process CAD file (DWG/DXF) for marine features.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ('.dwg', '.dxf'):
        raise HTTPException(status_code=400, detail="Expected DWG/DXF file")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        result = marine_service.process_cad_file(temp_path)
        os.unlink(temp_path)
        return result
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"CAD processing failed: {str(e)}")

@router.post("/merge")
async def merge_charts(
    chart_paths: List[str],
    output_format: str = "geotiff",
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Merge multiple marine charts into a single mosaic.
    
    Args:
        chart_paths: List of chart file paths
        output_format: Output format (geotiff, png, jpg)
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if len(chart_paths) < 2:
        raise HTTPException(status_code=400, detail="At least 2 charts required for merging")
    
    # Check if files exist
    for path in chart_paths:
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
    
    try:
        result = marine_service.merge_charts(chart_paths, output_format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart merging failed: {str(e)}")

@router.post("/extract-soundings")
async def extract_soundings(
    chart_data: dict,
    depth_range: List[float] = None,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Extract depth soundings from marine chart data.
    
    Args:
        chart_data: Chart data containing soundings
        depth_range: [min_depth, max_depth] filter range
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = marine_service.extract_soundings(chart_data, depth_range)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Soundings extraction failed: {str(e)}")

@router.get("/tiles/{chart_id}/{z}/{x}/{y}")
async def get_chart_tile(
    chart_id: str,
    z: int,
    x: int,
    y: int,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get chart tile for web mapping (XYZ tile scheme).
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        chart_uuid = uuid.UUID(chart_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chart ID format")
    
    # Get chart
    chart = db.query(MarineChart).filter(
        MarineChart.id == chart_uuid,
        MarineChart.user_id == user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    try:
        # Generate tile
        tile_data = marine_service.generate_tile(chart.file_path, z, x, y)
        
        if not tile_data:
            raise HTTPException(status_code=404, detail="Tile not available")
        
        return StreamingResponse(
            io.BytesIO(tile_data),
            media_type="image/png"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tile generation failed: {str(e)}")

@router.get("/charts")
async def get_marine_charts(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get user's marine charts.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    charts = db.query(MarineChart).filter(
        MarineChart.user_id == user.id
    ).order_by(
        MarineChart.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "charts": [
            {
                "id": str(chart.id),
                "name": chart.name,
                "chart_number": chart.chart_number,
                "scale": chart.scale,
                "projection": chart.projection,
                "file_type": chart.file_type,
                "bounds": chart.bounds,
                "created_at": chart.created_at.isoformat() if chart.created_at else None,
                "updated_at": chart.updated_at.isoformat() if chart.updated_at else None,
                "has_thumbnail": chart.thumbnail is not None
            }
            for chart in charts
        ],
        "total": db.query(MarineChart).filter(MarineChart.user_id == user.id).count()
    }

@router.get("/charts/{chart_id}")
async def get_chart_details(
    chart_id: str,
    include_soundings: bool = False,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a marine chart.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        chart_uuid = uuid.UUID(chart_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chart ID format")
    
    chart = db.query(MarineChart).filter(
        MarineChart.id == chart_uuid,
        MarineChart.user_id == user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    result = {
        "chart": {
            "id": str(chart.id),
            "name": chart.name,
            "chart_number": chart.chart_number,
            "scale": chart.scale,
            "projection": chart.projection,
            "file_path": chart.file_path,
            "file_type": chart.file_type,
            "bounds": chart.bounds,
            "metadata": chart.metadata,
            "created_at": chart.created_at.isoformat() if chart.created_at else None,
            "updated_at": chart.updated_at.isoformat() if chart.updated_at else None
        }
    }
    
    # Include soundings if requested
    if include_soundings and chart.soundings:
        result["soundings"] = [
            {
                "latitude": s.latitude,
                "longitude": s.longitude,
                "depth": s.depth,
                "unit": s.unit,
                "quality": s.quality,
                "feature_type": s.feature_type
            }
            for s in chart.soundings
        ]
    
    # Include contours if available
    if chart.contours:
        result["contours"] = [
            {
                "depth": c.depth,
                "unit": c.unit,
                "contour_type": c.contour_type,
                "points_count": len(c.points) if c.points else 0
            }
            for c in chart.contours
        ]
    
    return result

@router.get("/charts/{chart_id}/thumbnail")
async def get_chart_thumbnail(
    chart_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get chart thumbnail image.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        chart_uuid = uuid.UUID(chart_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chart ID format")
    
    chart = db.query(MarineChart).filter(
        MarineChart.id == chart_uuid,
        MarineChart.user_id == user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    if not chart.thumbnail:
        # Generate thumbnail if not exists
        if os.path.exists(chart.file_path):
            thumbnail_data = marine_service.generate_thumbnail(chart.file_path)
            if thumbnail_data:
                chart.thumbnail = thumbnail_data
                db.commit()
            else:
                raise HTTPException(status_code=404, detail="Thumbnail not available")
        else:
            raise HTTPException(status_code=404, detail="Chart file not found")
    
    return StreamingResponse(
        io.BytesIO(chart.thumbnail),
        media_type="image/png"
    )

@router.delete("/charts/{chart_id}")
async def delete_chart(
    chart_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Delete a marine chart.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        chart_uuid = uuid.UUID(chart_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chart ID format")
    
    chart = db.query(MarineChart).filter(
        MarineChart.id == chart_uuid,
        MarineChart.user_id == user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    # Delete file if it exists
    if os.path.exists(chart.file_path):
        try:
            os.remove(chart.file_path)
        except Exception as e:
            print(f"Warning: Could not delete chart file: {e}")
    
    db.delete(chart)
    db.commit()
    
    return {"success": True, "message": "Chart deleted successfully"}

@router.post("/georeference")
async def georeference_chart(
    chart_path: str,
    control_points: List[dict],
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Georeference a chart using control points.
    
    control_points: List of {pixel_x, pixel_y, map_x, map_y}
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if file exists
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if len(control_points) < 3:
        raise HTTPException(status_code=400, detail="At least 3 control points required")
    
    try:
        result = marine_service.georeference_chart(chart_path, control_points)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Georeferencing failed: {str(e)}")

@router.post("/depth-analysis")
async def analyze_depth_data(
    chart_id: str,
    analysis_type: str = "basic",
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Analyze depth data from marine chart.
    
    analysis_type options:
    - basic: Basic depth statistics
    - contours: Generate depth contours
    - safety: Safety depth analysis
    - navigation: Navigation channel analysis
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        chart_uuid = uuid.UUID(chart_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chart ID format")
    
    # Get chart
    chart = db.query(MarineChart).filter(
        MarineChart.id == chart_uuid,
        MarineChart.user_id == user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    
    try:
        # Get chart data
        chart_data = {
            "file_path": chart.file_path,
            "bounds": chart.bounds,
            "metadata": chart.metadata,
            "soundings": [
                {
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "depth": s.depth,
                    "unit": s.unit
                }
                for s in chart.soundings
            ] if chart.soundings else []
        }
        
        # Perform analysis
        result = marine_service.analyze_depth_data(chart_data, analysis_type)
        
        # Save contours to database if generated
        if analysis_type == "contours" and result.get('contours'):
            # Clear existing contours
            chart.contours = []
            
            # Add new contours
            for contour_data in result['contours']:
                from app.models.geospatial import DepthContour
                contour = DepthContour(
                    id=uuid.uuid4(),
                    chart_id=chart.id,
                    depth=contour_data.get('depth'),
                    unit=contour_data.get('unit', 'meters'),
                    contour_type=contour_data.get('type', 'depth'),
                    points=contour_data.get('points', [])
                )
                chart.contours.append(contour)
            
            db.commit()
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Depth analysis failed: {str(e)}")