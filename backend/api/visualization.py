"""
Visualization API endpoints for job management
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import uuid
import json
import os
from datetime import datetime
import tempfile
import io
import base64

from ..database import get_db
from ..models import VisualizationJob, AnalysisPreset, get_job_by_id, get_jobs_by_user
from ..celery_app import process_visualization_job, get_task_status, cancel_task

from ..config import settings
from ..services.region_service import get_all_regions, get_region_by_id

router = APIRouter(prefix="/visualization", tags=["visualization"])

# =====================================
# PYDANTIC MODELS
# =====================================

class VisualizationRequest(BaseModel):
    region_name: str = Field(..., min_length=1, max_length=255)
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON geometry")
    region_id: Optional[str] = Field(None, description="Predefined region ID")
    region_type: Optional[str] = None
    start_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(..., regex=r'^\d{4}-\d{2}-\d{2}$')
    baseline_type: str = Field(default='same-period')
    baseline_config: Optional[Dict[str, Any]] = None
    analysis_type: str = Field(default='anomaly', regex=r'^(anomaly|absolute|percentage|trend|risk)$')
    visualization_config: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    created_at: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    created_at: str
    statistics: Optional[Dict[str, Any]] = None
    map_preview_available: bool = False

class ExportRequest(BaseModel):
    job_id: str = Field(..., description="Job ID to export")
    format: str = Field(default='png', regex=r'^(png|pdf|svg|geotiff)$')
    resolution: int = Field(default=300, ge=150, le=600)
    include_legend: bool = Field(default=True)
    paper_size: str = Field(default='A4', regex=r'^(A4|A3|Letter|Legal)$')

# =====================================
# JOB MANAGEMENT ENDPOINTS
# =====================================

@router.post("/generate", response_model=JobResponse)
async def generate_visualization(
    request: VisualizationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = "default_user"  # In production, get from authentication
):
    """
    Start a new visualization generation job
    """
    
    try:
        # Validate date range
        start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(request.end_date, '%Y-%m-%d')
        
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if (end_date - start_date).days > 366:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 366 days")
        
        # Resolve geometry
        geometry = request.geometry
        if not geometry and request.region_id:
            region = get_region_by_id(request.region_id)
            if not region:
                raise HTTPException(status_code=404, detail="Region ID not found")
            geometry = region['geometry']
            # If region name not provided or generic, use official name
            if not request.region_name or request.region_name == "Region":
                 request.region_name = region['name']

        if not geometry or 'type' not in geometry:
            raise HTTPException(status_code=400, detail="Invalid geometry or missing region ID")
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job record
        job = VisualizationJob(
            id=job_id,
            user_id=user_id,
            region_name=request.region_name,

            geometry=geometry,
            start_date=request.start_date,
            end_date=request.end_date,
            analysis_type=request.analysis_type,
            region_id=request.region_id,
            region_type=request.region_type,
            baseline_type=request.baseline_type,
            baseline_config=request.baseline_config,
            visualization_config=request.visualization_config,
            status='pending',
            message='Job queued for processing'
        )
        
        db.add(job)
        db.commit()
        
        # Prepare job data for Celery
        job_data = {
            'region_name': request.region_name,
            'geometry': geometry,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'analysis_type': request.analysis_type,
            'visualization_config': request.visualization_config or {}
        }
        
        # Start Celery task
        task = process_visualization_job.delay(job_id, job_data)
        
        # Update job with Celery task ID
        job.celery_task_id = task.id
        db.commit()
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message="Visualization job queued for processing",
            created_at=job.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start visualization job: {str(e)}")

@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get the current status of a visualization job
    """
    
    try:
        # Get job from database
        job = get_job_by_id(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if map preview is available
        map_preview_available = bool(job.map_image_path and os.path.exists(job.map_image_path))
        
        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            message=job.message,
            created_at=job.created_at.isoformat(),
            statistics=job.statistics,
            map_preview_available=map_preview_available
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str, db: Session = Depends(get_db)):
    """
    Get full job details including parameters and results
    """
    
    try:
        job = get_job_by_id(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job details: {str(e)}")

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """
    Cancel a running visualization job
    """
    
    try:
        job = get_job_by_id(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in ['pending', 'running']:
            raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job.status}")
        
        # Cancel Celery task
        if job.celery_task_id:
            cancel_success = cancel_task(job.celery_task_id)
            if not cancel_success:
                raise HTTPException(status_code=500, detail="Failed to cancel background task")
        
        # Update job status
        job.status = 'cancelled'
        job.message = 'Job cancelled by user'
        job.completed_at = datetime.utcnow()
        db.commit()
        
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")

@router.get("/jobs")
async def list_user_jobs(
    user_id: str = "default_user",  # In production, get from authentication
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List jobs for a specific user
    """
    
    try:
        query = db.query(VisualizationJob).filter(VisualizationJob.user_id == user_id)
        
        if status_filter:
            query = query.filter(VisualizationJob.status == status_filter)
        
        jobs = query.order_by(VisualizationJob.created_at.desc()).limit(limit).all()
        
        return [job.to_dict() for job in jobs]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

# =====================================
# EXPORT ENDPOINTS
# =====================================

@router.post("/export")
async def export_visualization(request: ExportRequest, db: Session = Depends(get_db)):
    """
    Export visualization in specified format
    """
    
    try:
        job = get_job_by_id(db, request.job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != 'completed':
            raise HTTPException(status_code=400, detail="Job is not completed yet")
        
        if not job.map_image_path or not os.path.exists(job.map_image_path):
            raise HTTPException(status_code=404, detail="Visualization file not found")
        
        # Handle different export formats
        if request.format == 'png':
            return FileResponse(
                path=job.map_image_path,
                media_type='image/png',
                filename=f"{job.region_name}_{request.job_id}.png"
            )
        
        elif request.format == 'pdf':
            # Convert to PDF
            pdf_path = await convert_to_pdf(job.map_image_path, request)
            return FileResponse(
                path=pdf_path,
                media_type='application/pdf',
                filename=f"{job.region_name}_{request.job_id}.pdf"
            )
        
        elif request.format == 'svg':
            # Convert to SVG
            svg_path = await convert_to_svg(job.map_image_path, request)
            return FileResponse(
                path=svg_path,
                media_type='image/svg+xml',
                filename=f"{job.region_name}_{request.job_id}.svg"
            )
        
        elif request.format == 'geotiff':
            # Generate GeoTIFF (re-process with spatial reference)
            geotiff_path = await generate_geotiff(job, request)
            return FileResponse(
                path=geotiff_path,
                media_type='application/octet-stream',
                filename=f"{job.region_name}_{request.job_id}.tiff"
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {request.format}")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/jobs/{job_id}/preview")
async def get_map_preview(job_id: str, db: Session = Depends(get_db)):
    """
    Get base64 encoded preview of the generated map
    """
    
    try:
        job = get_job_by_id(db, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != 'completed':
            raise HTTPException(status_code=400, detail="Job is not completed yet")
        
        if not job.map_image_path or not os.path.exists(job.map_image_path):
            raise HTTPException(status_code=404, detail="Map image not found")
        
        # Read and encode image
        with open(job.map_image_path, 'rb') as img_file:
            img_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        return {
            'job_id': job_id,
            'image_data': img_data,
            'format': 'png',
            'statistics': job.statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preview: {str(e)}")

# =====================================
# PRESET MANAGEMENT
# =====================================

@router.get("/presets")
async def get_analysis_presets(db: Session = Depends(get_db)):
    """
    Get available analysis presets
    """
    
    try:
        presets = db.query(AnalysisPreset)\
                   .filter(AnalysisPreset.is_public == True)\
                   .order_by(AnalysisPreset.usage_count.desc())\
                   .all()
        
        return [preset.to_dict() for preset in presets]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get presets: {str(e)}")

@router.post("/presets")
async def create_analysis_preset(
    preset_data: dict,
    db: Session = Depends(get_db),
    user_id: str = "default_user"
):
    """
    Create a new analysis preset
    """
    
    try:
        preset = AnalysisPreset(
            name=preset_data['name'],
            description=preset_data.get('description', ''),
            geometry=preset_data['geometry'],
            default_start_date=preset_data.get('default_start_date'),
            default_end_date=preset_data.get('default_end_date'),
            default_analysis_type=preset_data.get('default_analysis_type', 'anomaly'),
            created_by=user_id,
            is_public=preset_data.get('is_public', False)
        )
        
        db.add(preset)
        db.commit()
        
        return preset.to_dict()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create preset: {str(e)}")

# =====================================
# REGION MANAGEMENT
# =====================================

@router.get("/regions")
async def list_regions():
    """
    List available predefined regions for analysis
    """
    try:
        return get_all_regions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list regions: {str(e)}")

# =====================================
# UTILITY FUNCTIONS
# =====================================

async def convert_to_pdf(png_path: str, request: ExportRequest) -> str:
    """Convert PNG to PDF format"""
    from PIL import Image
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    
    # Paper sizes in inches
    paper_sizes = {
        'A4': (8.27, 11.69),
        'A3': (11.69, 16.53),
        'Letter': (8.5, 11),
        'Legal': (8.5, 14)
    }
    
    pdf_path = png_path.replace('.png', '.pdf')
    
    with Image.open(png_path) as img:
        with PdfPages(pdf_path) as pdf:
            fig, ax = plt.subplots(1, 1, figsize=paper_sizes[request.paper_size])
            ax.imshow(img)
            ax.axis('off')
            
            plt.tight_layout()
            pdf.savefig(fig, dpi=request.resolution, bbox_inches='tight')
            plt.close(fig)
    
    return pdf_path

async def convert_to_svg(png_path: str, request: ExportRequest) -> str:
    """Convert PNG to SVG format (embedded)"""
    import base64
    
    svg_path = png_path.replace('.png', '.svg')
    
    with open(png_path, 'rb') as img_file:
        img_data = base64.b64encode(img_file.read()).decode()
    
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1000">
    <title>Yieldera Agricultural Analysis</title>
    <image href="data:image/png;base64,{img_data}" width="1200" height="1000"/>
</svg>'''
    
    with open(svg_path, 'w') as svg_file:
        svg_file.write(svg_content)
    
    return svg_path

async def generate_geotiff(job: VisualizationJob, request: ExportRequest) -> str:
    """Generate GeoTIFF with spatial reference"""
    # This would require re-running the GEE analysis to get georeferenced data
    # For now, return a placeholder - in production, implement full GEE export
    
    geotiff_path = job.map_image_path.replace('.png', '.tiff')
    
    # Placeholder implementation
    # In production, use the job parameters to re-run GEE analysis
    # and export as proper GeoTIFF with spatial reference
    
    import shutil
    shutil.copy(job.map_image_path, geotiff_path)
    
    return geotiff_path
