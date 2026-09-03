"""
Export routes for downloading files in various formats.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import io
import json

from app.services.export_service import ExportService
from app.services.auth_service import auth_service
from app.database import get_db
from app.models.geospatial import User

router = APIRouter()
export_service = ExportService()

@router.post("/gps")
async def export_gps_data(
    export_request: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Export GPS data to various formats.
    
    Request body:
    {
        "gps_data": {...},  // GPS data to export
        "format": "gpx",    // gpx, kml, geojson, csv, shp
        "include_metadata": true,
        "filename": "custom_name"  // optional
    }
    """
    # Verify user authentication
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        gps_data = export_request.get("gps_data")
        format = export_request.get("format", "gpx")
        include_metadata = export_request.get("include_metadata", True)
        
        if not gps_data:
            raise HTTPException(status_code=400, detail="GPS data is required")
        
        # Export data
        result = export_service.export_gps_data(
            gps_data=gps_data,
            format=format,
            include_metadata=include_metadata
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail="Export failed")
        
        # Create streaming response
        file_content = result['file_content']
        filename = export_request.get('filename') or result['filename']
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=result['mime_type'],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/watershed")
async def export_watershed_data(
    export_request: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Export watershed analysis results.
    
    Request body:
    {
        "watershed_data": {...},  // Watershed analysis results
        "format": "geojson",      // geojson, shp, pdf, png
        "filename": "custom_name" // optional
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        watershed_data = export_request.get("watershed_data")
        format = export_request.get("format", "geojson")
        
        if not watershed_data:
            raise HTTPException(status_code=400, detail="Watershed data is required")
        
        result = export_service.export_watershed_data(
            watershed_data=watershed_data,
            format=format
        )
        
        filename = export_request.get('filename') or result['filename']
        
        return StreamingResponse(
            io.BytesIO(result['file_content']),
            media_type=result['mime_type'],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/marine")
async def export_marine_data(
    export_request: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Export marine chart data.
    
    Request body:
    {
        "marine_data": {...},  // Marine chart data
        "format": "geotiff",   // geotiff, png, jpg, pdf
        "filename": "custom_name" // optional
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        marine_data = export_request.get("marine_data")
        format = export_request.get("format", "geotiff")
        
        if not marine_data:
            raise HTTPException(status_code=400, detail="Marine data is required")
        
        result = export_service.export_marine_data(
            marine_data=marine_data,
            format=format
        )
        
        filename = export_request.get('filename') or result['filename']
        
        return StreamingResponse(
            io.BytesIO(result['file_content']),
            media_type=result['mime_type'],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/hecras")
async def export_hecras_data(
    export_request: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Export HEC-RAS analysis results.
    
    Request body:
    {
        "hecras_data": {...},  // HEC-RAS results
        "format": "geojson",   // geojson, csv, pdf, xlsx
        "filename": "custom_name" // optional
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        hecras_data = export_request.get("hecras_data")
        format = export_request.get("format", "geojson")
        
        if not hecras_data:
            raise HTTPException(status_code=400, detail="HEC-RAS data is required")
        
        result = export_service.export_hecras_results(
            results=hecras_data,
            format=format
        )
        
        filename = export_request.get('filename') or result['filename']
        
        return StreamingResponse(
            io.BytesIO(result['file_content']),
            media_type=result['mime_type'],
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.post("/package")
async def create_export_package(
    export_request: Dict,
    background_tasks: BackgroundTasks,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Create a ZIP package of multiple exports.
    
    Request body:
    {
        "exports": [
            {
                "type": "gps",
                "data": {...},
                "format": "gpx"
            },
            {
                "type": "watershed",
                "data": {...},
                "format": "geojson"
            }
        ],
        "package_name": "project_export"
    }
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        exports = export_request.get("exports", [])
        package_name = export_request.get("package_name")
        
        if not exports:
            raise HTTPException(status_code=400, detail="No exports specified")
        
        # Process each export
        export_results = []
        for export in exports:
            export_type = export.get("type")
            data = export.get("data")
            format = export.get("format")
            
            if not all([export_type, data, format]):
                continue
            
            try:
                if export_type == "gps":
                    result = export_service.export_gps_data(data, format)
                elif export_type == "watershed":
                    result = export_service.export_watershed_data(data, format)
                elif export_type == "marine":
                    result = export_service.export_marine_data(data, format)
                elif export_type == "hecras":
                    result = export_service.export_hecras_results(data, format)
                else:
                    continue
                
                export_results.append(result)
                
            except Exception as e:
                # Log error but continue with other exports
                print(f"Error processing {export_type} export: {e}")
                continue
        
        if not export_results:
            raise HTTPException(status_code=500, detail="No exports could be processed")
        
        # Create package
        package_result = export_service.create_export_package(
            exports=export_results,
            package_name=package_name
        )
        
        return StreamingResponse(
            io.BytesIO(package_result['file_content']),
            media_type=package_result['mime_type'],
            headers={
                "Content-Disposition": f"attachment; filename={package_result['filename']}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Package creation error: {str(e)}")

@router.get("/formats/{data_type}")
async def get_export_formats(
    data_type: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get supported export formats for a data type.
    
    data_type: gps, watershed, marine, hecras
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    formats = {
        "gps": [
            {"format": "gpx", "name": "GPX", "description": "GPS Exchange Format"},
            {"format": "kml", "name": "KML", "description": "Keyhole Markup Language"},
            {"format": "geojson", "name": "GeoJSON", "description": "Geographic JSON"},
            {"format": "csv", "name": "CSV", "description": "Comma Separated Values"},
            {"format": "shp", "name": "Shapefile", "description": "ESRI Shapefile (ZIP)"}
        ],
        "watershed": [
            {"format": "geojson", "name": "GeoJSON", "description": "Geographic JSON"},
            {"format": "shp", "name": "Shapefile", "description": "ESRI Shapefile (ZIP)"},
            {"format": "pdf", "name": "PDF Report", "description": "Portable Document Format"},
            {"format": "png", "name": "PNG Image", "description": "Portable Network Graphics"}
        ],
        "marine": [
            {"format": "geotiff", "name": "GeoTIFF", "description": "Georeferenced TIFF"},
            {"format": "png", "name": "PNG Image", "description": "Portable Network Graphics"},
            {"format": "jpg", "name": "JPG Image", "description": "JPEG Image"},
            {"format": "pdf", "name": "PDF Report", "description": "Portable Document Format"}
        ],
        "hecras": [
            {"format": "geojson", "name": "GeoJSON", "description": "Geographic JSON"},
            {"format": "csv", "name": "CSV", "description": "Comma Separated Values"},
            {"format": "pdf", "name": "PDF Report", "description": "Portable Document Format"},
            {"format": "xlsx", "name": "Excel", "description": "Microsoft Excel"}
        ]
    }
    
    if data_type not in formats:
        raise HTTPException(status_code=400, detail=f"Unknown data type: {data_type}")
    
    return {"data_type": data_type, "formats": formats[data_type]}

@router.get("/history")
async def get_export_history(
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get user's export history.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # In production, you would query a database table for export history
    # For now, return mock data
    return {
        "user_id": str(user.id),
        "total_exports": 0,
        "exports": []
    }

@router.delete("/history/{export_id}")
async def delete_export_history(
    export_id: str,
    token: str = Depends(auth_service.oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Delete an export from history.
    """
    user = auth_service.get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # In production, you would delete from database
    return {"success": True, "message": "Export deleted"}