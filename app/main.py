"""
Portal QA/CI Demo - FastAPI application with Pydantic validation
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import asyncio
import uuid

from .schemas import (
    UserRole, GeospatialData, ProcessingRequest, ProcessingResponse, 
    ValidationSummary
)
from .utils import (
    generate_request_id, calculate_geospatial_distance, 
    validate_coordinate_bounds, compute_data_quality_score,
    estimate_processing_time, generate_mock_output_files,
    create_processing_summary
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for demo purposes
processing_requests: Dict[str, Dict[str, Any]] = {}
user_sessions: Dict[str, Dict[str, Any]] = {}

app = FastAPI(
    title="Portal QA/CI Demo",
    description="FastAPI application demonstrating Pydantic validation and testing",
    version="1.0.0"
)

class UserProfile(BaseModel):
    """User profile data with comprehensive validation."""
    
    user_id: int = Field(..., gt=0, description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    age: int = Field(..., ge=13, le=120, description="User age between 13 and 120")
    is_active: bool = Field(default=True, description="Whether user account is active")
    tags: Optional[List[str]] = Field(default=None, max_length=10, description="User tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": 12345,
                "username": "john_doe",
                "email": "john.doe@example.com",
                "age": 28,
                "is_active": True,
                "tags": ["developer", "python"],
                "metadata": {"location": "NYC", "timezone": "EST"}
            }
        }
    }

class UserResponse(BaseModel):
    """Response model for user operations."""
    
    success: bool
    message: str
    user_id: Optional[int] = None
    validation_score: Optional[float] = None

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Portal QA/CI Demo API", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "service": "portal-qa-ci-demo",
        "version": "1.0.0"
    }

@app.post("/users", response_model=UserResponse)
async def create_user(user_profile: UserProfile):
    """
    Create a new user profile with comprehensive validation.
    
    This endpoint demonstrates:
    - Pydantic model validation
    - Custom field validation rules
    - Error handling with meaningful messages
    - JSON schema validation
    """
    try:
        # Simulate validation scoring based on completeness
        validation_score = calculate_validation_score(user_profile)
        
        # Simulate user creation logic
        logger.info(f"Creating user: {user_profile.username} (ID: {user_profile.user_id})")
        
        return UserResponse(
            success=True,
            message=f"User {user_profile.username} created successfully",
            user_id=user_profile.user_id,
            validation_score=validation_score
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/users/validate")
async def validate_user_data(request: dict):
    """
    Validate user data without creating a user.
    
    Returns detailed validation results and suggestions.
    """
    try:
        user_profile = UserProfile(**request)
        validation_score = calculate_validation_score(user_profile)
        validation_details = get_validation_details(user_profile)
        
        return {
            "valid": True,
            "validation_score": validation_score,
            "details": validation_details,
            "user_data": user_profile.model_dump()
        }
        
    except ValidationError as e:
        return {
            "valid": False,
            "errors": e.errors(),
            "validation_score": 0.0
        }

def calculate_validation_score(user_profile: UserProfile) -> float:
    """Calculate a validation score based on data completeness and quality."""
    score = 0.0
    
    # Base score for required fields
    score += 0.4
    
    # Optional fields scoring
    if user_profile.tags:
        score += 0.2
    if user_profile.metadata:
        score += 0.2
    
    # Username quality
    if len(user_profile.username) >= 6:
        score += 0.1
    
    # Email domain quality (simple check)
    if user_profile.email.endswith(('.com', '.org', '.edu')):
        score += 0.1
    
    return min(score, 1.0)

def get_validation_details(user_profile: UserProfile) -> Dict[str, str]:
    """Get detailed validation feedback."""
    details = {
        "user_id": "Valid" if user_profile.user_id > 0 else "Invalid",
        "username": "Valid" if 3 <= len(user_profile.username) <= 50 else "Invalid length",
        "email": "Valid" if "@" in user_profile.email else "Invalid format",
        "age": "Valid" if 13 <= user_profile.age <= 120 else "Invalid range"
    }
    
    if user_profile.tags:
        details["tags"] = f"Valid ({len(user_profile.tags)} tags)"
    else:
        details["tags"] = "Not provided"
        
    if user_profile.metadata:
        details["metadata"] = f"Valid ({len(user_profile.metadata)} fields)"
    else:
        details["metadata"] = "Not provided"
    
    return details

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Custom validation error handler."""
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation failed",
            "errors": exc.errors(),
            "detail": "Please check your input data and try again"
        }
    )

@app.post("/processing/submit", response_model=ProcessingResponse)
async def submit_processing_request(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a geospatial data processing request.
    
    Demonstrates:
    - Complex nested validation
    - Background task processing
    - Geospatial data validation
    - Request ID generation
    """
    try:
        # Generate unique request ID if not provided
        if not hasattr(request, 'request_id') or not request.request_id:
            request_id = generate_request_id("proc")
        else:
            request_id = request.request_id
        
        # Validate coordinate bounds
        coord_validation = validate_coordinate_bounds(
            request.location.latitude, 
            request.location.longitude
        )
        
        if not coord_validation["latitude_valid"] or not coord_validation["longitude_valid"]:
            raise HTTPException(
                status_code=422, 
                detail="Invalid coordinate bounds"
            )
        
        # Store request
        processing_requests[request_id] = {
            "request": request.model_dump(),
            "status": "pending",
            "submitted_at": datetime.now(),
            "estimated_duration": estimate_processing_time(
                request.data_type, 
                request.parameters
            )
        }
        
        # Schedule background processing
        background_tasks.add_task(simulate_processing, request_id)
        
        logger.info(f"Processing request submitted: {request_id}")
        
        return ProcessingResponse(
            request_id=request_id,
            status="pending",
            message=f"Processing request {request_id} submitted successfully",
            progress=0.0,
            estimated_completion=None
        )
        
    except ValidationError as e:
        logger.error(f"Validation error in processing request: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting processing request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/processing/status/{request_id}", response_model=ProcessingResponse)
async def get_processing_status(request_id: str):
    """Get the status of a processing request."""
    if request_id not in processing_requests:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_data = processing_requests[request_id]
    status = request_data["status"]
    
    # Calculate progress based on elapsed time
    if status == "processing":
        elapsed = (datetime.now() - request_data["submitted_at"]).total_seconds()
        estimated_duration = request_data["estimated_duration"]
        progress = min((elapsed / estimated_duration) * 100, 95.0)
    elif status == "completed":
        progress = 100.0
    elif status == "failed":
        progress = 0.0
    else:
        progress = 0.0
    
    return ProcessingResponse(
        request_id=request_id,
        status=status,
        message=f"Request {request_id} is {status}",
        progress=progress,
        output_files=request_data.get("output_files")
    )


@app.get("/processing/list")
async def list_processing_requests(
    status: Optional[str] = None,
    limit: int = 10
):
    """List processing requests with optional status filter."""
    # Validate limit parameter
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Limit must be between 1 and 100")
    
    requests = []
    
    for req_id, req_data in processing_requests.items():
        if status is None or req_data["status"] == status:
            requests.append({
                "request_id": req_id,
                "status": req_data["status"],
                "submitted_at": req_data["submitted_at"].isoformat(),
                "data_type": req_data["request"]["data_type"]
            })
    
    # Sort by submission time (newest first)
    requests.sort(key=lambda x: x["submitted_at"], reverse=True)
    
    return {
        "total": len(requests),
        "requests": requests[:limit]
    }


@app.post("/geospatial/validate")
async def validate_geospatial_data(location: GeospatialData):
    """Validate geospatial data and provide quality assessment."""
    coord_validation = validate_coordinate_bounds(
        location.latitude, 
        location.longitude
    )
    
    # Calculate quality score
    quality_factors = {
        "coordinates_valid": coord_validation["latitude_valid"] and coord_validation["longitude_valid"],
        "elevation_provided": location.elevation is not None,
        "accuracy_provided": location.accuracy is not None,
        "high_accuracy": location.accuracy is not None and location.accuracy <= 10,
        "reasonable_elevation": (location.elevation is not None and 
                               -500 <= location.elevation <= 9000) if location.elevation else True
    }
    
    score = sum(quality_factors.values()) / len(quality_factors)
    
    return ValidationSummary(
        total_checks=len(quality_factors),
        passed_checks=sum(quality_factors.values()),
        failed_checks=len(quality_factors) - sum(quality_factors.values()),
        warnings=1 if coord_validation.get("in_polar_region", False) else 0,
        score=score,
        details={
            "coordinate_validation": "passed" if quality_factors["coordinates_valid"] else "failed",
            "elevation_check": "passed" if quality_factors["reasonable_elevation"] else "failed",
            "accuracy_assessment": "good" if quality_factors["high_accuracy"] else "moderate",
            "location_type": "polar" if coord_validation.get("in_polar_region") else "standard"
        }
    )


@app.get("/geospatial/distance")
async def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
):
    """Calculate distance between two geographic coordinates."""
    try:
        distance_km = calculate_geospatial_distance(lat1, lon1, lat2, lon2)
        
        return {
            "distance_km": round(distance_km, 2),
            "distance_miles": round(distance_km * 0.621371, 2),
            "coordinates": {
                "point1": {"latitude": lat1, "longitude": lon1},
                "point2": {"latitude": lat2, "longitude": lon2}
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Error calculating distance: {str(e)}"
        )


@app.delete("/processing/{request_id}")
async def cancel_processing_request(request_id: str):
    """Cancel a processing request."""
    if request_id not in processing_requests:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_data = processing_requests[request_id]
    
    if request_data["status"] == "completed":
        raise HTTPException(
            status_code=400, 
            detail="Cannot cancel completed request"
        )
    
    request_data["status"] = "cancelled"
    logger.info(f"Processing request cancelled: {request_id}")
    
    return {"message": f"Request {request_id} cancelled successfully"}


@app.get("/schema/export")
async def export_api_schema():
    """Export OpenAPI schema for documentation and client generation."""
    return app.openapi()


async def simulate_processing(request_id: str):
    """Simulate background processing of a request."""
    await asyncio.sleep(2)  # Initial delay
    
    if request_id in processing_requests:
        # Update to processing
        processing_requests[request_id]["status"] = "processing"
        
        # Simulate processing time
        estimated_duration = processing_requests[request_id]["estimated_duration"]
        await asyncio.sleep(min(estimated_duration, 10))  # Cap at 10 seconds for demo
        
        # Complete processing
        if processing_requests[request_id]["status"] != "cancelled":
            processing_requests[request_id]["status"] = "completed"
            processing_requests[request_id]["output_files"] = generate_mock_output_files(
                request_id,
                processing_requests[request_id]["request"]["data_type"]
            )
            processing_requests[request_id]["completed_at"] = datetime.now()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)