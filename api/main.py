"""
Portal API - Map tile and metadata service for client dashboards
FastAPI application with comprehensive Pydantic validation
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
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

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token."""
    if credentials.credentials != "demo_api_token_12345":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token"
        )
    return credentials.credentials

# Pydantic models with comprehensive validation
class TileRequest(BaseModel):
    """Request model for map tile generation."""
    x: int = Field(..., ge=0, description="Tile X coordinate")
    y: int = Field(..., ge=0, description="Tile Y coordinate") 
    z: int = Field(..., ge=0, le=18, description="Zoom level")
    layer: str = Field(..., description="Layer name")
    
    @field_validator('layer')
    @classmethod
    def validate_layer(cls, v):
        allowed_layers = ['soil_ph', 'organic_matter', 'elevation', 'ndvi']
        if v not in allowed_layers:
            raise ValueError(f'Layer must be one of: {allowed_layers}')
        return v

class BoundingBox(BaseModel):
    """Bounding box model with comprehensive validation."""
    west: float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)
    
    @field_validator('east')
    @classmethod
    def validate_east(cls, v, info):
        if 'west' in info.data and v <= info.data['west']:
            raise ValueError('East must be greater than west')
        return v
    
    @field_validator('north')
    @classmethod
    def validate_north(cls, v, info):
        if 'south' in info.data and v <= info.data['south']:
            raise ValueError('North must be greater than south')
        return v

class MetadataRequest(BaseModel):
    """Request model for metadata queries."""
    bbox: BoundingBox
    layers: List[str] = Field(..., min_length=1, max_length=10)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @field_validator('layers')
    @classmethod
    def validate_layers(cls, v):
        allowed_layers = ['soil_ph', 'organic_matter', 'elevation', 'ndvi']
        for layer in v:
            if layer not in allowed_layers:
                raise ValueError(f'Invalid layer: {layer}. Must be one of: {allowed_layers}')
        return v

class MetadataResponse(BaseModel):
    """Response model for metadata."""
    bbox: BoundingBox
    statistics: Dict[str, Dict[str, float]]
    count: int
    last_updated: datetime

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    timestamp: datetime

# Mock data storage and utilities
SERVICE_START_TIME = datetime.now()

def generate_mock_tile_data(x: int, y: int, z: int, layer: str) -> bytes:
    """Generate mock tile data."""
    seed_val = abs(x + y + z + hash(layer)) % (2**32 - 1)
    np.random.seed(seed_val)
    data = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    return data.tobytes()

def calculate_mock_statistics(bbox: BoundingBox, layer: str) -> Dict[str, float]:
    """Calculate mock statistics for a layer."""
    seed_val = abs(hash(f"{bbox.west}{bbox.south}{bbox.east}{bbox.north}{layer}")) % (2**32 - 1)
    np.random.seed(seed_val)
    
    if layer == 'soil_ph':
        mean_val = np.random.uniform(5.5, 7.5)
        std_val = np.random.uniform(0.3, 0.8)
    elif layer == 'organic_matter':
        mean_val = np.random.uniform(2.0, 6.0)
        std_val = np.random.uniform(0.5, 1.2)
    elif layer == 'elevation':
        mean_val = np.random.uniform(100, 800)
        std_val = np.random.uniform(50, 200)
    elif layer == 'ndvi':
        mean_val = np.random.uniform(0.3, 0.8)
        std_val = np.random.uniform(0.1, 0.3)
    else:
        mean_val = np.random.uniform(0, 100)
        std_val = np.random.uniform(5, 25)
    
    return {
        'mean': float(mean_val),
        'std': float(std_val),
        'min': float(mean_val - 2 * std_val),
        'max': float(mean_val + 2 * std_val),
        'count': int(np.random.uniform(1000, 50000))
    }

# API Routes
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "Portal Map Tile API", 
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = (datetime.now() - SERVICE_START_TIME).total_seconds()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        uptime_seconds=uptime
    )

@app.post("/tiles", dependencies=[Depends(verify_token)])
async def get_tile(request: TileRequest):
    """Generate a map tile."""
    tile_data = generate_mock_tile_data(request.x, request.y, request.z, request.layer)
    
    return {
        "x": request.x,
        "y": request.y,
        "z": request.z,
        "layer": request.layer,
        "size_bytes": len(tile_data),
        "generated_at": datetime.now(),
        "format": "PNG"
    }

@app.post("/metadata", response_model=MetadataResponse, dependencies=[Depends(verify_token)])
async def get_metadata(request: MetadataRequest):
    """Get metadata for specified layers and bounding box."""
    
    # Validate date range
    if request.start_date and request.end_date:
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
    
    # Calculate statistics for each layer
    statistics = {}
    total_count = 0
    
    for layer in request.layers:
        stats = calculate_mock_statistics(request.bbox, layer)
        statistics[layer] = stats
        total_count += stats['count']
    
    return MetadataResponse(
        bbox=request.bbox,
        statistics=statistics,
        count=total_count,
        last_updated=datetime.now()
    )

@app.post("/upload", dependencies=[Depends(verify_token)])
async def upload_raster(file: UploadFile = File(...)):
    """Upload and process a raster file."""
    
    # Validate file type
    if not file.filename.lower().endswith(('.tif', '.tiff', '.geotiff')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only TIFF/GeoTIFF files are supported"
        )
    
    # Process file in temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Mock processing
        file_size = len(content)
        
        metadata = {
            "filename": file.filename,
            "size_bytes": file_size,
            "format": "GeoTIFF",
            "processed_at": datetime.now(),
            "bounds": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "crs": "EPSG:4326",
            "resolution": [30.0, 30.0],
            "dimensions": [1024, 1024]
        }
        
        return {
            "status": "success",
            "message": f"Processed {file.filename}",
            "metadata": metadata
        }
        
    finally:
        os.unlink(tmp_file_path)

@app.get("/layers")
async def list_layers():
    """List available data layers."""
    return {
        "layers": [
            {
                "name": "soil_ph",
                "description": "Soil pH levels",
                "unit": "pH units",
                "range": [4.0, 9.0]
            },
            {
                "name": "organic_matter", 
                "description": "Soil organic matter content",
                "unit": "percentage",
                "range": [0.0, 10.0]
            },
            {
                "name": "elevation",
                "description": "Digital elevation model",
                "unit": "meters",
                "range": [0.0, 3000.0]
            },
            {
                "name": "ndvi",
                "description": "Normalized Difference Vegetation Index",
                "unit": "index",
                "range": [-1.0, 1.0]
            }
        ]
    }

@app.get("/status")
async def get_status():
    """Get detailed service status."""
    return {
        "service": "Portal Map Tile API",
        "version": "1.0.0",
        "status": "operational",
        "uptime_seconds": (datetime.now() - SERVICE_START_TIME).total_seconds(),
        "endpoints": ["/", "/health", "/tiles", "/metadata", "/upload", "/layers", "/status"],
        "supported_layers": ["soil_ph", "organic_matter", "elevation", "ndvi"]
    }

# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": str(exc),
            "detail": "Validation error",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)