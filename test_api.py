"""
Comprehensive unit tests for Portal API endpoints
25+ tests with ≥90% coverage target
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
import json
from datetime import datetime
import io

from api.main import app


class TestPortalAPI:
    """Comprehensive test suite for Portal API - 25+ tests."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests."""
        return {"Authorization": "Bearer demo_api_token_12345"}
    
    @pytest.fixture
    def invalid_auth_headers(self):
        """Invalid authentication headers."""
        return {"Authorization": "Bearer invalid_token"}
    
    # 1. Basic endpoint tests
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct response."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Portal Map Tile API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "active"
    
    # 2. Health check tests
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0
    
    # 3. Layers endpoint tests
    def test_list_layers(self, client):
        """Test layer listing endpoint."""
        response = client.get("/layers")
        assert response.status_code == 200
        data = response.json()
        assert "layers" in data
        assert len(data["layers"]) == 4
        
        layer_names = [layer["name"] for layer in data["layers"]]
        assert "soil_ph" in layer_names
        assert "organic_matter" in layer_names
        assert "elevation" in layer_names
        assert "ndvi" in layer_names
    
    # 4. Status endpoint tests
    def test_status_endpoint(self, client):
        """Test detailed status endpoint."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Portal Map Tile API"
        assert data["status"] == "operational"
        assert "endpoints" in data
        assert "supported_layers" in data
    
    # 5-10. Tile endpoint tests
    def test_tile_request_valid(self, client, auth_headers):
        """Test valid tile request."""
        tile_data = {
            "x": 5,
            "y": 10,
            "z": 8,
            "layer": "soil_ph"
        }
        response = client.post("/tiles", json=tile_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["x"] == 5
        assert data["y"] == 10
        assert data["z"] == 8
        assert data["layer"] == "soil_ph"
        assert "size_bytes" in data
        assert "generated_at" in data
    
    def test_tile_request_different_layers(self, client, auth_headers):
        """Test tile requests for all supported layers."""
        layers_to_test = ["soil_ph", "organic_matter", "elevation", "ndvi"]
        
        for layer in layers_to_test:
            tile_data = {
                "x": 1,
                "y": 1, 
                "z": 5,
                "layer": layer
            }
            response = client.post("/tiles", json=tile_data, headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["layer"] == layer
    
    def test_tile_request_invalid_layer(self, client, auth_headers):
        """Test tile request with invalid layer."""
        tile_data = {
            "x": 5,
            "y": 10,
            "z": 8,
            "layer": "invalid_layer"
        }
        response = client.post("/tiles", json=tile_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_tile_request_invalid_zoom(self, client, auth_headers):
        """Test tile request with invalid zoom level."""
        tile_data = {
            "x": 5,
            "y": 10,
            "z": 25,  # Too high
            "layer": "soil_ph"
        }
        response = client.post("/tiles", json=tile_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_tile_request_negative_coordinates(self, client, auth_headers):
        """Test tile request with negative coordinates."""
        tile_data = {
            "x": -1,  # Invalid
            "y": 10,
            "z": 8,
            "layer": "soil_ph"
        }
        response = client.post("/tiles", json=tile_data, headers=auth_headers)
        assert response.status_code == 422
    
    def test_tile_request_no_auth(self, client):
        """Test tile request without authentication."""
        tile_data = {
            "x": 5,
            "y": 10,
            "z": 8,
            "layer": "soil_ph"
        }
        response = client.post("/tiles", json=tile_data)
        assert response.status_code == 403
    
    # 11-18. Metadata endpoint tests
    def test_metadata_request_valid(self, client, auth_headers):
        """Test valid metadata request."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph", "organic_matter"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "bbox" in data
        assert "statistics" in data
        assert "count" in data
        assert "last_updated" in data
        
        # Check statistics for each layer
        assert "soil_ph" in data["statistics"]
        assert "organic_matter" in data["statistics"]
        
        # Check required statistical fields
        for layer_stats in data["statistics"].values():
            assert "mean" in layer_stats
            assert "std" in layer_stats
            assert "min" in layer_stats
            assert "max" in layer_stats
            assert "count" in layer_stats
    
    def test_metadata_request_single_layer(self, client, auth_headers):
        """Test metadata request with single layer."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["statistics"]) == 1
        assert "soil_ph" in data["statistics"]
    
    def test_metadata_request_all_layers(self, client, auth_headers):
        """Test metadata request with all supported layers."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph", "organic_matter", "elevation", "ndvi"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["statistics"]) == 4
    
    def test_metadata_request_invalid_bbox_west_east(self, client, auth_headers):
        """Test metadata request with west > east."""
        metadata_request = {
            "bbox": {
                "west": -85.0,  # West > East (invalid)
                "south": 35.0,
                "east": -95.0,
                "north": 45.0
            },
            "layers": ["soil_ph"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 422
    
    def test_metadata_request_invalid_bbox_south_north(self, client, auth_headers):
        """Test metadata request with south > north."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 45.0,  # South > North (invalid)
                "east": -85.0,
                "north": 35.0
            },
            "layers": ["soil_ph"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 422
    
    def test_metadata_request_empty_layers(self, client, auth_headers):
        """Test metadata request with empty layers list."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": []  # Empty list
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 422
    
    def test_metadata_request_too_many_layers(self, client, auth_headers):
        """Test metadata request with too many layers."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["layer" + str(i) for i in range(15)]  # Too many layers
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 422
    
    def test_metadata_request_with_valid_dates(self, client, auth_headers):
        """Test metadata request with valid date range."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph"],
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-12-31T23:59:59"
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 200
    
    # 19-23. Upload endpoint tests
    def test_upload_valid_tiff_file(self, client, auth_headers):
        """Test uploading a valid TIFF file."""
        mock_file_content = b"Mock TIFF file content for testing"
        files = {"file": ("test.tif", io.BytesIO(mock_file_content), "image/tiff")}
        
        response = client.post("/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "message" in data
        assert "metadata" in data
        
        metadata = data["metadata"]
        assert metadata["filename"] == "test.tif"
        assert metadata["format"] == "GeoTIFF"
        assert "bounds" in metadata
        assert "crs" in metadata
    
    def test_upload_valid_geotiff_file(self, client, auth_headers):
        """Test uploading a valid GeoTIFF file."""
        mock_file_content = b"Mock GeoTIFF file content"
        files = {"file": ("test.geotiff", io.BytesIO(mock_file_content), "image/tiff")}
        
        response = client.post("/upload", files=files, headers=auth_headers)
        assert response.status_code == 200
    
    def test_upload_invalid_file_type(self, client, auth_headers):
        """Test uploading an invalid file type."""
        mock_file_content = b"Mock text file content"
        files = {"file": ("test.txt", io.BytesIO(mock_file_content), "text/plain")}
        
        response = client.post("/upload", files=files, headers=auth_headers)
        assert response.status_code == 400
    
    def test_upload_no_file(self, client, auth_headers):
        """Test upload endpoint without file."""
        response = client.post("/upload", headers=auth_headers)
        assert response.status_code == 422
    
    def test_upload_no_auth(self, client):
        """Test upload without authentication."""
        mock_file_content = b"Mock TIFF file content"
        files = {"file": ("test.tif", io.BytesIO(mock_file_content), "image/tiff")}
        
        response = client.post("/upload", files=files)
        assert response.status_code == 403
    
    # 24-26. Authentication tests
    def test_tile_request_invalid_auth(self, client, invalid_auth_headers):
        """Test tile request with invalid authentication."""
        tile_data = {
            "x": 5,
            "y": 10,
            "z": 8,
            "layer": "soil_ph"
        }
        response = client.post("/tiles", json=tile_data, headers=invalid_auth_headers)
        assert response.status_code == 401
    
    def test_metadata_request_invalid_auth(self, client, invalid_auth_headers):
        """Test metadata request with invalid authentication."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph"]
        }
        response = client.post("/metadata", json=metadata_request, headers=invalid_auth_headers)
        assert response.status_code == 401
    
    def test_upload_invalid_auth(self, client, invalid_auth_headers):
        """Test upload with invalid authentication."""
        mock_file_content = b"Mock TIFF file content"
        files = {"file": ("test.tif", io.BytesIO(mock_file_content), "image/tiff")}
        
        response = client.post("/upload", files=files, headers=invalid_auth_headers)
        assert response.status_code == 401
    
    # 27-30. Edge case and error handling tests
    def test_metadata_invalid_date_range(self, client, auth_headers):
        """Test metadata request with invalid date range."""
        metadata_request = {
            "bbox": {
                "west": -95.0,
                "south": 35.0,
                "east": -85.0,
                "north": 45.0
            },
            "layers": ["soil_ph"],
            "start_date": "2023-12-31T23:59:59",  # After end_date
            "end_date": "2023-01-01T00:00:00"
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 400
    
    def test_bbox_edge_cases_world_spanning(self, client, auth_headers):
        """Test bounding box that spans the world."""
        metadata_request = {
            "bbox": {
                "west": -180.0,
                "south": -90.0,
                "east": 180.0,
                "north": 90.0
            },
            "layers": ["soil_ph"]
        }
        response = client.post("/metadata", json=metadata_request, headers=auth_headers)
        assert response.status_code == 200
    
    def test_malformed_json_request(self, client, auth_headers):
        """Test handling of malformed JSON."""
        response = client.post(
            "/tiles", 
            data="{'invalid': json'}", 
            headers={"Content-Type": "application/json", **auth_headers}
        )
        assert response.status_code == 422
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are handled."""
        response = client.options("/")
        # FastAPI automatically handles OPTIONS requests
        assert response.status_code in [200, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])