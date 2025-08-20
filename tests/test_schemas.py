"""
Unit tests for Pydantic schemas
"""

import pytest
from pydantic import ValidationError

from app.schemas import (
    GeospatialData, ProcessingRequest, ProcessingResponse,
    ValidationSummary, UserRole
)


class TestGeospatialData:
    """Test GeospatialData schema validation."""
    
    def test_valid_geospatial_data(self):
        """Test valid geospatial data creation."""
        data = GeospatialData(
            latitude=40.7128,
            longitude=-74.0060,
            elevation=10.5,
            accuracy=2.0
        )
        
        assert data.latitude == 40.7128
        assert data.longitude == -74.0060
        assert data.elevation == 10.5
        assert data.accuracy == 2.0
    
    def test_minimal_geospatial_data(self):
        """Test geospatial data with only required fields."""
        data = GeospatialData(
            latitude=51.5074,
            longitude=-0.1278
        )
        
        assert data.latitude == 51.5074
        assert data.longitude == -0.1278
        assert data.elevation is None
        assert data.accuracy is None
    
    def test_invalid_latitude_range(self):
        """Test validation fails for invalid latitude."""
        with pytest.raises(ValidationError):
            GeospatialData(latitude=91.0, longitude=0.0)
        
        with pytest.raises(ValidationError):
            GeospatialData(latitude=-91.0, longitude=0.0)
    
    def test_invalid_longitude_range(self):
        """Test validation fails for invalid longitude."""
        with pytest.raises(ValidationError):
            GeospatialData(latitude=0.0, longitude=181.0)
        
        with pytest.raises(ValidationError):
            GeospatialData(latitude=0.0, longitude=-181.0)
    
    def test_zero_coordinates_validation(self):
        """Test that exactly zero coordinates are rejected."""
        with pytest.raises(ValidationError, match="Coordinates cannot be exactly zero"):
            GeospatialData(latitude=0.0, longitude=-74.0060)
        
        with pytest.raises(ValidationError, match="Coordinates cannot be exactly zero"):
            GeospatialData(latitude=40.7128, longitude=0.0)
    
    def test_invalid_elevation_range(self):
        """Test validation fails for invalid elevation."""
        with pytest.raises(ValidationError):
            GeospatialData(
                latitude=40.7128,
                longitude=-74.0060,
                elevation=-501.0  # Below minimum
            )
        
        with pytest.raises(ValidationError):
            GeospatialData(
                latitude=40.7128,
                longitude=-74.0060,
                elevation=9001.0  # Above maximum
            )
    
    def test_invalid_accuracy_range(self):
        """Test validation fails for invalid accuracy."""
        with pytest.raises(ValidationError):
            GeospatialData(
                latitude=40.7128,
                longitude=-74.0060,
                accuracy=0.0  # Must be > 0
            )
        
        with pytest.raises(ValidationError):
            GeospatialData(
                latitude=40.7128,
                longitude=-74.0060,
                accuracy=101.0  # Above maximum
            )


class TestProcessingRequest:
    """Test ProcessingRequest schema validation."""
    
    def test_valid_processing_request(self):
        """Test valid processing request creation."""
        request = ProcessingRequest(
            request_id="test_req_12345",
            data_type="raster",
            priority=3,
            parameters={
                "format": "tiff",
                "resolution": "10m"
            },
            location=GeospatialData(
                latitude=40.7128,
                longitude=-74.0060
            ),
            tags=["urgent", "test"]
        )
        
        assert request.request_id == "test_req_12345"
        assert request.data_type == "raster"
        assert request.priority == 3
        assert request.parameters["format"] == "tiff"
        assert request.location.latitude == 40.7128
        assert request.tags == ["urgent", "test"]
    
    def test_invalid_request_id_pattern(self):
        """Test validation fails for invalid request ID pattern."""
        with pytest.raises(ValidationError):
            ProcessingRequest(
                request_id="invalid id!",  # Contains space and special char
                data_type="raster",
                priority=3,
                parameters={"format": "tiff", "resolution": "10m"},
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )
    
    def test_invalid_data_type(self):
        """Test validation fails for invalid data type."""
        with pytest.raises(ValidationError, match="data_type must be one of"):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="invalid_type",
                priority=3,
                parameters={"format": "tiff", "resolution": "10m"},
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )
    
    def test_invalid_priority_range(self):
        """Test validation fails for invalid priority."""
        with pytest.raises(ValidationError):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="raster",
                priority=0,  # Below minimum
                parameters={"format": "tiff", "resolution": "10m"},
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )
        
        with pytest.raises(ValidationError):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="raster",
                priority=6,  # Above maximum
                parameters={"format": "tiff", "resolution": "10m"},
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )
    
    def test_missing_required_parameters(self):
        """Test validation fails for missing required parameters."""
        with pytest.raises(ValidationError, match="parameters must include"):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="raster",
                priority=3,
                parameters={"format": "tiff"},  # Missing 'resolution'
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )
    
    def test_too_many_tags(self):
        """Test validation fails for too many tags."""
        with pytest.raises(ValidationError):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="raster",
                priority=3,
                parameters={"format": "tiff", "resolution": "10m"},
                location=GeospatialData(latitude=40.7128, longitude=-74.0060),
                tags=["tag" + str(i) for i in range(11)]  # Too many tags
            )
    
    def test_empty_parameters(self):
        """Test validation fails for empty parameters."""
        with pytest.raises(ValidationError):
            ProcessingRequest(
                request_id="test_req_12345",
                data_type="raster",
                priority=3,
                parameters={},  # Empty parameters
                location=GeospatialData(latitude=40.7128, longitude=-74.0060)
            )


class TestProcessingResponse:
    """Test ProcessingResponse schema validation."""
    
    def test_valid_processing_response(self):
        """Test valid processing response creation."""
        response = ProcessingResponse(
            request_id="test_req_12345",
            status="processing",
            message="Request is being processed",
            progress=45.5,
            estimated_completion="2024-01-01T12:00:00",
            output_files=["file1.tiff", "file2.json"]
        )
        
        assert response.request_id == "test_req_12345"
        assert response.status == "processing"
        assert response.progress == 45.5
        assert len(response.output_files) == 2
    
    def test_invalid_status_pattern(self):
        """Test validation fails for invalid status."""
        with pytest.raises(ValidationError):
            ProcessingResponse(
                request_id="test_req_12345",
                status="invalid_status",
                message="Test message"
            )
    
    def test_invalid_progress_range(self):
        """Test validation fails for invalid progress values."""
        with pytest.raises(ValidationError):
            ProcessingResponse(
                request_id="test_req_12345",
                status="processing",
                message="Test message",
                progress=-1.0  # Below minimum
            )
        
        with pytest.raises(ValidationError):
            ProcessingResponse(
                request_id="test_req_12345",
                status="processing",
                message="Test message",
                progress=101.0  # Above maximum
            )


class TestValidationSummary:
    """Test ValidationSummary schema validation."""
    
    def test_valid_validation_summary(self):
        """Test valid validation summary creation."""
        summary = ValidationSummary(
            total_checks=10,
            passed_checks=8,
            failed_checks=2,
            warnings=1,
            score=0.8,
            details={"check1": "passed", "check2": "failed"}
        )
        
        assert summary.total_checks == 10
        assert summary.passed_checks == 8
        assert summary.failed_checks == 2
        assert summary.score == 0.8
        assert len(summary.details) == 2
    
    def test_check_count_validation(self):
        """Test validation fails when check counts exceed total."""
        with pytest.raises(ValidationError):
            ValidationSummary(
                total_checks=10,
                passed_checks=12,  # Exceeds total
                failed_checks=2,
                warnings=0,
                score=0.8,
                details={}
            )
    
    def test_invalid_score_range(self):
        """Test validation fails for invalid score range."""
        with pytest.raises(ValidationError):
            ValidationSummary(
                total_checks=10,
                passed_checks=8,
                failed_checks=2,
                warnings=0,
                score=1.5,  # Above maximum
                details={}
            )


class TestUserRole:
    """Test UserRole enumeration."""
    
    def test_valid_user_roles(self):
        """Test valid user role values."""
        assert UserRole.admin == "admin"
        assert UserRole.user == "user"
        assert UserRole.guest == "guest"
    
    def test_user_role_in_validation(self):
        """Test user role can be used in validation contexts."""
        from pydantic import BaseModel, Field
        from typing import Optional
        
        class TestModel(BaseModel):
            role: UserRole = Field(default=UserRole.user)
        
        model = TestModel(role=UserRole.admin)
        assert model.role == UserRole.admin
        
        # Test with string value
        model2 = TestModel(role="guest")
        assert model2.role == UserRole.guest