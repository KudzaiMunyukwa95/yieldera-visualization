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
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    baseline_type: str = Field(default='same-period')
    baseline_config: Optional[Dict[str, Any]] = None
    analysis_type: str = Field(default='anomaly', pattern=r'^(anomaly|absolute|percentage|trend|risk)$')
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
    format: str = Field(default='png', pattern=r'^(png|pdf|svg|geotiff)$')
    resolution: int = Field(default=300, ge=150, le=600)
    include_legend: bool = Field(default=True)
    paper_size: str = Field(default='A4', pattern=r'^(A4|A3|Letter|Legal)$')

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
            'region_type': request.region_type,
            'baseline_type': request.baseline_type,
            'baseline_config': request.baseline_config,
            'visualization_config': request.visualization_config or {}
        }
        
        # Start Celery task (will run synchronously if configured as eager)
        task = process_visualization_job.delay(job_id, job_data)
        
        job.celery_task_id = task.id
        job.message = 'Job queued for processing'

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
            # Convert to PDF with full job context for Executive Summary
            pdf_path = await convert_to_pdf(job, request)
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

async def convert_to_pdf(job: VisualizationJob, request: ExportRequest) -> str:
    """Convert PNG to professional PDF format with Enhanced Executive Summary and Comparative Table"""
    from PIL import Image
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    import textwrap
    
    png_path = job.map_image_path
    paper_sizes = {
        'A4': (8.27, 11.69),
        'A3': (11.69, 16.53),
        'Letter': (8.5, 11),
        'Legal': (8.5, 14)
    }
    
    pdf_path = png_path.replace('.png', '.pdf')
    stats = job.statistics or {}
    ai_commentary = stats.get('ai_commentary', "AI Commentary not available.")
    
    with Image.open(png_path) as img:
        with PdfPages(pdf_path) as pdf:
            # PAGE 1: The Map
            fig1, ax1 = plt.subplots(1, 1, figsize=paper_sizes[request.paper_size])
            ax1.imshow(img)
            ax1.axis('off')
            plt.tight_layout()
            pdf.savefig(fig1, dpi=request.resolution, bbox_inches='tight')
            plt.close(fig1)
            
            # PAGE 2: Executive Summary & Detailed Statistics
            fig2, ax2 = plt.subplots(1, 1, figsize=paper_sizes[request.paper_size], facecolor='#ffffff')
            ax2.axis('off')
            
            # 1. Header Section
            plt.text(0.5, 0.96, "AGRICULTURAL RISK ASSESSMENT REPORT", 
                     ha='center', va='top', fontsize=18, fontweight='bold', color='#0f172a')
            
            period_start = stats.get('analysis_period', {}).get('start', job.start_date)
            period_end = stats.get('analysis_period', {}).get('end', job.end_date)
            baseline_desc = stats.get('baseline_period', '2015-2024 Historical mean')

            plt.text(0.5, 0.93, f"Region: {job.region_name}", ha='center', va='top', fontsize=11, color='#475569')
            plt.text(0.5, 0.90, f"Analysis Period: {period_start} to {period_end}", ha='center', va='top', fontsize=9, color='#64748b')
            plt.text(0.5, 0.88, f"Baseline Reference: {baseline_desc}", ha='center', va='top', fontsize=9, color='#64748b')
            
            # 2. Intelligence Executive Summary (Dynamic Height)
            plt.text(0.05, 0.86, "EXECUTIVE SUMMARY", ha='left', va='top', 
                     fontsize=12, fontweight='bold', color='#1e293b')
            
            # Use wider wrap for better space utilization
            wrapped_commentary = textwrap.fill(ai_commentary, width=95)
            # Estimate height based on wraps
            lines = wrapped_commentary.count('\n') + 1
            ai_text = plt.text(0.05, 0.835, wrapped_commentary, ha='left', va='top', 
                             fontsize=9, style='italic', linespacing=1.6, color='#334155')
            
            # Calculate dynamic y offset for next section
            ai_bottom_y = 0.835 - (lines * 0.022)
            
            # 3. CORE ANALYTICS: SEASON vs HISTORICAL (The Simple Table)
            comp_y = ai_bottom_y - 0.04
            plt.text(0.05, comp_y, "COMPARISON: SEASON VS HISTORICAL", ha='left', va='top', 
                     fontsize=12, fontweight='bold', color='#1e293b')
            
            ty = comp_y - 0.03
            # Table Headers
            header_cfg = dict(fontweight='bold', fontsize=8, color='#475569')
            plt.text(0.05, ty, "Core Unit", **header_cfg)
            plt.text(0.40, ty, "Current Season", ha='center', **header_cfg)
            plt.text(0.65, ty, "Historical Ref", ha='center', **header_cfg)
            plt.text(0.85, ty, "Deviation (%)", ha='center', **header_cfg)
            plt.axhline(y=ty-0.008, xmin=0.05, xmax=0.9, color='#cbd5e1', linewidth=0.5)
            
            # Data Rows
            ry = ty - 0.03
            row_cfg = dict(fontsize=9, color='#1e293b')
            units = [
                ("Soil Moisture (m³/m³)", stats.get('current_mean', 0), stats.get('baseline_mean', 0), stats.get('percentage_change', 0), 4),
                ("Precipitation (mm)", stats.get('mean_rainfall', 0), stats.get('baseline_rainfall', 0), stats.get('rainfall_change', 0), 2),
                ("Veg Health (NDVI)", stats.get('mean_ndvi', 0), stats.get('baseline_ndvi', 0), stats.get('ndvi_change', 0), 3)
            ]
            
            for label, cur, bas, dev, prec in units:
                plt.text(0.05, ry, label, **row_cfg)
                plt.text(0.40, ry, f"{cur:.{prec}f}", ha='center', **row_cfg)
                plt.text(0.65, ry, f"{bas:.{prec}f}", ha='center', **row_cfg)
                plt.text(0.85, ry, f"{dev:+.1f}%", ha='center', fontweight='bold', color='#0f172a' if dev >= 0 else '#e11d48')
                ry -= 0.025
            
            # 4. Detailed Agricultural Impact Table
            impact_y = ry - 0.03
            plt.text(0.05, impact_y, "SECTOR-WIDE IMPACT ASSESSMENT", ha='left', va='top', 
                     fontsize=11, fontweight='bold', color='#1e293b')
            
            y_table = impact_y - 0.03
            # Table Headers - Recalculated coordinates to prevent collisions
            plt.text(0.045, y_table, "Condition Category", fontweight='bold', fontsize=7, color='#64748b')
            plt.text(0.42, y_table, "Impact (ha)", fontweight='bold', fontsize=7, ha='right', color='#64748b')
            plt.text(0.68, y_table, "This Season", fontweight='bold', fontsize=7, ha='right', color='#64748b')
            plt.text(0.90, y_table, "Hist. Baseline", fontweight='bold', fontsize=7, ha='right', color='#64748b')
            plt.axhline(y=y_table-0.008, xmin=0.04, xmax=0.9, color='#0f172a', linewidth=0.5)
            
            zonal = stats.get('zonal_impact', {})
            impact_rows = [
                ("Extreme Drought", zonal.get('extreme_drought', {}), '#8b0000'),
                ("Severe Drought", zonal.get('severe_drought', {}), '#e11d48'),
                ("Moderate Stress", zonal.get('moderate_drought', {}), '#eab308'),
                ("Normal Conditions", zonal.get('normal', {}), '#94a3b8'),
                ("Above Normal / Wet", zonal.get('wet_conditions', {}), '#10b981')
            ]
            
            ry_tab = y_table - 0.03
            for label, data, color in impact_rows:
                area_ha = data.get('area_ha', 0)
                mc = data.get('current_moisture', 0)
                mb = data.get('baseline_moisture', 0)

                plt.text(0.052, ry_tab, label, fontsize=7, color='#1e293b')
                plt.text(0.42, ry_tab, f"{area_ha:,.0f}", fontsize=7, ha='right', fontweight='bold' if area_ha > 0 else 'normal')
                plt.text(0.68, ry_tab, f"{mc:.4f}", fontsize=7, ha='right')
                plt.text(0.90, ry_tab, f"{mb:.4f}", fontsize=7, ha='right')
                
                # Category Indicator
                rect = plt.Rectangle((0.02, ry_tab-0.003), 0.015, 0.01, facecolor=color, transform=ax2.transAxes)
                ax2.add_patch(rect)
                ry_tab -= 0.022
            
            # 5. Key Risk Summary
            risk_y = ry_tab - 0.04
            plt.text(0.05, risk_y, "COMBINED HAZARD & RISK SUMMARY", ha='left', va='top', 
                     fontsize=11, fontweight='bold', color='#1e293b')
            
            kpi_y = risk_y - 0.03
            kpis = [
                f"Multi-Peril Risk Hectares: {stats.get('multi_peril_risk_hectares', 0):,.0f} ha (Moisture Deficit + Veg decay)",
                f"Global Moisture Anomaly: {stats.get('mean_anomaly', 0):+.4f} m³/m³",
                f"Average Vegetation Health: {stats.get('mean_ndvi', 0):.3f} NDVI"
            ]
            
            for kpi in kpis:
                plt.text(0.05, kpi_y, f"• {kpi}", fontsize=8, color='#334155')
                kpi_y -= 0.018
                
            # Footer
            plt.text(0.5, 0.05, f"Analysis Protocol: US-USDA Scientific Basis | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                     ha='center', va='bottom', fontsize=7, color='#94a3b8')
            
            pdf.savefig(fig2, bbox_inches='tight')
            plt.close(fig2)
    
    return pdf_path
    
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
