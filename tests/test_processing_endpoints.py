"""
Unit tests for processing endpoints
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app, processing_requests

client = TestClient(app)


class TestProcessingSubmitEndpoint:
    """Test /processing/submit endpoint."""
    
    def test_submit_valid_processing_request(self):
        """Test submitting a valid processing request."""
        request_data = {
            "request_id": "test_submit_001",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
                "accuracy": 5.0
            },
            "tags": ["test", "automated"]
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["request_id"] == "test_submit_001"
        assert data["status"] == "pending"
        assert data["progress"] == 0.0
        assert "message" in data
    
    def test_submit_minimal_processing_request(self):
        """Test submitting a minimal processing request."""
        request_data = {
            "request_id": "test_submit_002",
            "data_type": "vector",
            "priority": 1,
            "parameters": {
                "format": "shp",
                "resolution": "1m"
            },
            "location": {
                "latitude": 51.5074,
                "longitude": -0.1278
            }
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "pending"
    
    def test_submit_invalid_coordinates(self):
        """Test submitting request with invalid coordinates."""
        request_data = {
            "request_id": "test_submit_003",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 91.0,  # Invalid latitude
                "longitude": -74.0060
            }
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 422
    
    def test_submit_invalid_data_type(self):
        """Test submitting request with invalid data type."""
        request_data = {
            "request_id": "test_submit_004",
            "data_type": "invalid_type",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 422
    
    def test_submit_missing_required_parameters(self):
        """Test submitting request with missing required parameters."""
        request_data = {
            "request_id": "test_submit_005",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff"  # Missing 'resolution'
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 422
    
    def test_submit_zero_coordinates(self):
        """Test submitting request with zero coordinates (should fail)."""
        request_data = {
            "request_id": "test_submit_006",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 0.0,  # Should be rejected
                "longitude": -74.0060
            }
        }
        
        response = client.post("/processing/submit", json=request_data)
        assert response.status_code == 422


class TestProcessingStatusEndpoint:
    """Test /processing/status/{request_id} endpoint."""
    
    def setup_method(self):
        """Set up test data before each test."""
        # Clear any existing requests
        processing_requests.clear()
    
    def test_get_status_existing_request(self):
        """Test getting status of existing request."""
        # First submit a request
        request_data = {
            "request_id": "test_status_001",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        
        submit_response = client.post("/processing/submit", json=request_data)
        assert submit_response.status_code == 200
        
        # Then get status
        status_response = client.get("/processing/status/test_status_001")
        assert status_response.status_code == 200
        
        data = status_response.json()
        assert data["request_id"] == "test_status_001"
        assert data["status"] in ["pending", "processing", "completed"]
        assert "progress" in data
        assert "message" in data
    
    def test_get_status_nonexistent_request(self):
        """Test getting status of non-existent request."""
        response = client.get("/processing/status/nonexistent_request")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_status_progress_calculation(self):
        """Test that progress is calculated correctly."""
        # Submit request and immediately check status
        request_data = {
            "request_id": "test_status_002",
            "data_type": "metadata",  # Quick processing
            "priority": 5,
            "parameters": {
                "format": "json",
                "resolution": "1m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        
        client.post("/processing/submit", json=request_data)
        
        # Check status multiple times
        response1 = client.get("/processing/status/test_status_002")
        assert response1.status_code == 200
        
        progress1 = response1.json()["progress"]
        assert 0.0 <= progress1 <= 100.0


class TestProcessingListEndpoint:
    """Test /processing/list endpoint."""
    
    def setup_method(self):
        """Set up test data before each test."""
        processing_requests.clear()
    
    def test_list_empty_requests(self):
        """Test listing when no requests exist."""
        response = client.get("/processing/list")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 0
        assert data["requests"] == []
    
    def test_list_with_requests(self):
        """Test listing with existing requests."""
        # Submit multiple requests
        for i in range(3):
            request_data = {
                "request_id": f"test_list_{i:03d}",
                "data_type": "raster",
                "priority": i + 1,
                "parameters": {
                    "format": "tiff",
                    "resolution": "10m"
                },
                "location": {
                    "latitude": 40.7128 + i,
                    "longitude": -74.0060
                }
            }
            client.post("/processing/submit", json=request_data)
        
        # List all requests
        response = client.get("/processing/list")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 3
        assert len(data["requests"]) == 3
        
        # Check structure of returned requests
        for req in data["requests"]:
            assert "request_id" in req
            assert "status" in req
            assert "submitted_at" in req
            assert "data_type" in req
    
    def test_list_with_status_filter(self):
        """Test listing with status filter."""
        # Submit a request
        request_data = {
            "request_id": "test_list_filter_001",
            "data_type": "raster",
            "priority": 3,
            "parameters": {
                "format": "tiff",
                "resolution": "10m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        client.post("/processing/submit", json=request_data)
        
        # Test filtering by status
        response = client.get("/processing/list?status=pending")
        assert response.status_code == 200
        
        data = response.json()
        for req in data["requests"]:
            assert req["status"] == "pending"
    
    def test_list_with_limit(self):
        """Test listing with limit parameter."""
        # Submit multiple requests
        for i in range(5):
            request_data = {
                "request_id": f"test_list_limit_{i:03d}",
                "data_type": "vector",
                "priority": 2,
                "parameters": {
                    "format": "shp",
                    "resolution": "1m"
                },
                "location": {
                    "latitude": 40.7128 + i * 0.1,
                    "longitude": -74.0060
                }
            }
            client.post("/processing/submit", json=request_data)
        
        # Test with limit
        response = client.get("/processing/list?limit=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5  # Total should still be 5
        assert len(data["requests"]) == 3  # But only 3 returned
    
    def test_list_invalid_limit(self):
        """Test listing with invalid limit parameter."""
        response = client.get("/processing/list?limit=0")
        assert response.status_code == 422
        
        response = client.get("/processing/list?limit=101")
        assert response.status_code == 422


class TestProcessingCancelEndpoint:
    """Test /processing/{request_id} DELETE endpoint."""
    
    def setup_method(self):
        """Set up test data before each test."""
        processing_requests.clear()
    
    def test_cancel_existing_request(self):
        """Test cancelling an existing request."""
        # Submit a request
        request_data = {
            "request_id": "test_cancel_001",
            "data_type": "point_cloud",  # Long processing time
            "priority": 3,
            "parameters": {
                "format": "las",
                "resolution": "0.1m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        client.post("/processing/submit", json=request_data)
        
        # Cancel the request
        response = client.delete("/processing/test_cancel_001")
        assert response.status_code == 200
        
        data = response.json()
        assert "cancelled successfully" in data["message"]
        
        # Verify status is updated
        status_response = client.get("/processing/status/test_cancel_001")
        status_data = status_response.json()
        assert status_data["status"] == "cancelled"
    
    def test_cancel_nonexistent_request(self):
        """Test cancelling a non-existent request."""
        response = client.delete("/processing/nonexistent_request")
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_cancel_completed_request(self):
        """Test cancelling a completed request should fail."""
        # Submit and manually mark as completed
        request_data = {
            "request_id": "test_cancel_002",
            "data_type": "metadata",
            "priority": 3,
            "parameters": {
                "format": "json",
                "resolution": "1m"
            },
            "location": {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }
        client.post("/processing/submit", json=request_data)
        
        # Manually mark as completed for testing
        processing_requests["test_cancel_002"]["status"] = "completed"
        
        # Try to cancel
        response = client.delete("/processing/test_cancel_002")
        assert response.status_code == 400
        
        data = response.json()
        assert "cannot cancel completed" in data["detail"].lower()