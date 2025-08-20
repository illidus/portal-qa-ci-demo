"""
Pydantic schemas for Portal QA/CI Demo
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
import re


class UserRole(str, Enum):
    """User role enumeration."""
    admin = "admin"
    user = "user"
    guest = "guest"


class GeospatialData(BaseModel):
    """Geospatial data validation schema."""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    elevation: Optional[float] = Field(None, ge=-500, le=9000, description="Elevation in meters")
    accuracy: Optional[float] = Field(None, gt=0, le=100, description="GPS accuracy in meters")
    
    @field_validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        """Ensure coordinates are not exactly zero (likely invalid)."""
        if v == 0.0:
            raise ValueError('Coordinates cannot be exactly zero')
        return v


class ProcessingRequest(BaseModel):
    """Processing request schema with complex validation."""
    
    request_id: str = Field(..., pattern=r'^[a-zA-Z0-9-_]{8,64}$')
    data_type: str = Field(..., min_length=3, max_length=20)
    priority: int = Field(..., ge=1, le=5, description="Priority level 1-5")
    parameters: Dict[str, Any] = Field(..., min_length=1, max_length=20)
    location: GeospatialData
    tags: Optional[List[str]] = Field(None, max_length=10)
    
    @field_validator('data_type')
    def validate_data_type(cls, v):
        """Validate allowed data types."""
        allowed_types = ['raster', 'vector', 'timeseries', 'point_cloud', 'metadata']
        if v not in allowed_types:
            raise ValueError(f'data_type must be one of: {allowed_types}')
        return v
    
    @field_validator('parameters')
    def validate_parameters(cls, v):
        """Validate parameter structure."""
        required_keys = {'format', 'resolution'}
        if not required_keys.issubset(v.keys()):
            raise ValueError(f'parameters must include: {required_keys}')
        return v


class ProcessingResponse(BaseModel):
    """Processing response schema."""
    
    request_id: str
    status: str = Field(..., pattern=r'^(pending|processing|completed|failed)$')
    message: str
    progress: Optional[float] = Field(None, ge=0, le=100)
    estimated_completion: Optional[str] = None
    output_files: Optional[List[str]] = None


class ValidationSummary(BaseModel):
    """Validation summary for data quality assessment."""
    
    total_checks: int = Field(..., ge=0)
    passed_checks: int = Field(..., ge=0)
    failed_checks: int = Field(..., ge=0)
    warnings: int = Field(..., ge=0)
    score: float = Field(..., ge=0, le=1)
    details: Dict[str, str]
    
    @field_validator('passed_checks', 'failed_checks')
    def validate_check_counts(cls, v, info):
        """Ensure check counts are consistent."""
        if info.data and 'total_checks' in info.data and v > info.data['total_checks']:
            raise ValueError('Check count cannot exceed total checks')
        return v