"""
Portal API - Map tile and metadata service for client dashboards
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import rasterio
import numpy as np
import os
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uvicorn


app = FastAPI(
    title="Portal Map Tile API",
    description="High-performance map tile and metadata service for geospatial dashboards",
    version="1.0.0"
)

# CORS middleware for client dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Data models
class TileRequest(BaseModel):
    """Request model for map tile generation."""
    x: int = Field(..., ge=0, description="Tile X coordinate")
    y: int = Field(..., ge=0, description="Tile Y coordinate")
    z: int = Field(..., ge=0, le=18, description="Zoom level")
    layer: str = Field(..., description="Layer name")
    
    class Config:
        schema_extra = {
            "example": {
                "x": 1024,
                "y": 768,
                "z": 10,
                "layer": "soil_properties"
            }
        }


class TileMetadata(BaseModel):
    """Metadata for a map tile."""
    tile_id: str
    bounds: List[float] = Field(..., description="[minx, miny, maxx, maxy]")
    crs: str = Field(default="EPSG:4326")
    pixel_size: float
    creation_time: datetime
    data_source: str
    
    class Config:
        schema_extra = {
            "example": {
                "tile_id": "soil_10_1024_768",
                "bounds": [-104.5, 41.0, -104.0, 41.5],
                "crs": "EPSG:4326",
                "pixel_size": 0.0001,
                "creation_time": "2023-08-20T10:30:00Z",
                "data_source": "gamma_radiometric_survey"
            }
        }


class RasterStats(BaseModel):
    """Statistical summary of raster data."""
    band_count: int
    width: int
    height: int
    bounds: List[float]
    crs: str
    data_type: str
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    nodata_value: Optional[float] = None


class WebhookEvent(BaseModel):
    """Webhook event notification."""
    event_type: str = Field(..., description="Type of event (tile_created, analysis_complete)")
    tile_id: Optional[str] = None
    timestamp: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "tile_created",
                "tile_id": "soil_10_1024_768",
                "timestamp": "2023-08-20T10:30:00Z",
                "payload": {"processing_time": 2.3, "file_size": 1024}
            }
        }


# Mock authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token for authentication."""
    token = credentials.credentials
    
    # In production, validate against your auth system
    if token != "demo_api_token_12345":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


# In-memory storage for demo (use database in production)
tiles_db: Dict[str, TileMetadata] = {}
webhook_events: List[WebhookEvent] = []


@app.get("/", summary="API Health Check")
async def root():
    """Health check endpoint."""
    return {
        "service": "Portal Map Tile API",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/tiles/", response_model=TileMetadata, summary="Generate Map Tile")
async def create_tile(
    request: TileRequest,
    token: str = Depends(verify_token)
):
    """
    Generate a new map tile for the specified coordinates and layer.
    
    This endpoint creates map tiles for client dashboard visualization.
    Tiles are generated on-demand and cached for performance.
    """
    tile_id = f"{request.layer}_{request.z}_{request.x}_{request.y}"
    
    # Check if tile already exists
    if tile_id in tiles_db:
        return tiles_db[tile_id]
    
    # Calculate tile bounds (simplified Web Mercator projection)
    tile_size = 360.0 / (2 ** request.z)
    min_x = -180.0 + request.x * tile_size
    max_x = min_x + tile_size
    min_y = -90.0 + request.y * tile_size
    max_y = min_y + tile_size
    
    # Create metadata
    metadata = TileMetadata(
        tile_id=tile_id,
        bounds=[min_x, min_y, max_x, max_y],
        crs="EPSG:4326",
        pixel_size=tile_size / 256,  # Assuming 256x256 pixel tiles
        creation_time=datetime.now(),
        data_source=f"{request.layer}_survey_data"
    )
    
    # Store in database
    tiles_db[tile_id] = metadata
    
    # Create webhook event
    event = WebhookEvent(
        event_type="tile_created",
        tile_id=tile_id,
        timestamp=datetime.now(),
        payload={
            "layer": request.layer,
            "zoom": request.z,
            "processing_time": 1.2
        }
    )
    webhook_events.append(event)
    
    return metadata


@app.get("/tiles/{tile_id}", response_model=TileMetadata, summary="Get Tile Metadata")
async def get_tile(tile_id: str, token: str = Depends(verify_token)):
    """Retrieve metadata for a specific tile."""
    if tile_id not in tiles_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tile {tile_id} not found"
        )
    
    return tiles_db[tile_id]


@app.get("/tiles/", response_model=List[TileMetadata], summary="List All Tiles")
async def list_tiles(
    layer: Optional[str] = None,
    limit: int = Field(default=100, le=1000),
    token: str = Depends(verify_token)
):
    """List all available tiles, optionally filtered by layer."""
    tiles = list(tiles_db.values())
    
    if layer:
        tiles = [tile for tile in tiles if layer in tile.tile_id]
    
    return tiles[:limit]


@app.delete("/tiles/{tile_id}", summary="Delete Tile")
async def delete_tile(tile_id: str, token: str = Depends(verify_token)):
    """Delete a specific tile."""
    if tile_id not in tiles_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tile {tile_id} not found"
        )
    
    del tiles_db[tile_id]
    
    # Create webhook event
    event = WebhookEvent(
        event_type="tile_deleted",
        tile_id=tile_id,
        timestamp=datetime.now(),
        payload={"reason": "manual_deletion"}
    )
    webhook_events.append(event)
    
    return {"message": f"Tile {tile_id} deleted successfully"}


@app.post("/raster/analyze/", response_model=RasterStats, summary="Analyze Raster File")
async def analyze_raster(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """
    Analyze uploaded raster file and return statistical summary.
    
    Supports GeoTIFF, NetCDF, and other GDAL-compatible formats.
    """
    if not file.filename.lower().endswith(('.tif', '.tiff', '.nc', '.img')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Use GeoTIFF, NetCDF, or IMG format."
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Analyze raster using rasterio
        with rasterio.open(tmp_path) as src:
            # Read first band for statistics
            data = src.read(1, masked=True)
            
            stats = RasterStats(
                band_count=src.count,
                width=src.width,
                height=src.height,
                bounds=list(src.bounds),
                crs=str(src.crs),
                data_type=str(src.dtypes[0]),
                min_value=float(data.min()),
                max_value=float(data.max()),
                mean_value=float(data.mean()),
                std_value=float(data.std()),
                nodata_value=src.nodata
            )
            
            # Create webhook event
            event = WebhookEvent(
                event_type="raster_analyzed",
                timestamp=datetime.now(),
                payload={
                    "filename": file.filename,
                    "file_size": file.size,
                    "band_count": stats.band_count,
                    "pixel_count": stats.width * stats.height
                }
            )
            webhook_events.append(event)
            
            return stats
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to analyze raster: {str(e)}"
        )
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)


@app.get("/webhooks/events/", response_model=List[WebhookEvent], summary="Get Webhook Events")
async def get_webhook_events(
    event_type: Optional[str] = None,
    limit: int = Field(default=50, le=500),
    token: str = Depends(verify_token)
):
    """Retrieve recent webhook events for monitoring and debugging."""
    events = webhook_events.copy()
    
    if event_type:
        events = [event for event in events if event.event_type == event_type]
    
    # Return most recent events first
    events.reverse()
    return events[:limit]


@app.post("/webhooks/simulate/", summary="Simulate Webhook Event")
async def simulate_webhook(
    event: WebhookEvent,
    token: str = Depends(verify_token)
):
    """Simulate a webhook event for testing purposes."""
    webhook_events.append(event)
    return {"message": "Webhook event simulated successfully", "event_id": len(webhook_events)}


@app.get("/health/", summary="Detailed Health Check")
async def health_check():
    """Detailed health check with service metrics."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "total_tiles": len(tiles_db),
            "total_webhook_events": len(webhook_events),
            "memory_usage": "normal",
            "api_version": "1.0.0"
        },
        "dependencies": {
            "rasterio": "available",
            "numpy": "available",
            "fastapi": "available"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )