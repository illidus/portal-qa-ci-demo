"""
Unit tests for Portal API endpoints
"""

import pytest
import tempfile
import os
from httpx import AsyncClient
from fastapi.testclient import TestClient
import json
from datetime import datetime

from api.main import app
from raster_utils import create_sample_raster, RasterProcessor


class TestAPI:
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API requests."""
        return {"Authorization": "Bearer demo_api_token_12345"}
    
    @pytest.fixture
    def sample_raster_file(self):
        """Create a sample raster file for testing."""
        fd, path = tempfile.mkstemp(suffix='.tif')
        os.close(fd)
        create_sample_raster(path, 256, 256)
        yield path
        os.unlink(path)
    
    def test_health_check(self, client):
        """Test API health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Portal Map Tile API"
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = client.get("/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "metrics" in data
        assert "dependencies" in data
        assert data["dependencies"]["rasterio"] == "available"
    
    def test_create_tile_without_auth(self, client):
        """Test tile creation without authentication."""
        tile_request = {
            "x": 1024,
            "y": 768,
            "z": 10,
            "layer": "soil_properties"
        }
        
        response = client.post("/tiles/", json=tile_request)
        assert response.status_code == 403  # Forbidden
    
    def test_create_tile_with_invalid_auth(self, client):
        """Test tile creation with invalid authentication."""
        tile_request = {
            "x": 1024,
            "y": 768,
            "z": 10,
            "layer": "soil_properties"
        }
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/tiles/", json=tile_request, headers=headers)
        assert response.status_code == 401  # Unauthorized
    
    def test_create_tile_valid(self, client, auth_headers):
        """Test successful tile creation."""
        tile_request = {
            "x": 1024,
            "y": 768,
            "z": 10,
            "layer": "soil_properties"
        }
        
        response = client.post("/tiles/", json=tile_request, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["tile_id"] == "soil_properties_10_1024_768"
        assert len(data["bounds"]) == 4
        assert data["crs"] == "EPSG:4326"
        assert "creation_time" in data
    
    def test_create_tile_duplicate(self, client, auth_headers):
        """Test creating duplicate tile returns existing metadata."""
        tile_request = {
            "x": 2048,
            "y": 1536,
            "z": 11,
            "layer": "elevation"
        }
        
        # Create tile first time
        response1 = client.post("/tiles/", json=tile_request, headers=auth_headers)
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Create same tile again
        response2 = client.post("/tiles/", json=tile_request, headers=auth_headers)
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data1["tile_id"] == data2["tile_id"]
        assert data1["creation_time"] == data2["creation_time"]
    
    def test_tile_request_validation(self, client, auth_headers):
        """Test tile request input validation."""
        # Invalid zoom level
        invalid_request = {
            "x": 1024,
            "y": 768,
            "z": 25,  # Too high
            "layer": "soil_properties"
        }
        
        response = client.post("/tiles/", json=invalid_request, headers=auth_headers)
        assert response.status_code == 422  # Validation error
        
        # Negative coordinates
        invalid_request = {
            "x": -1,
            "y": 768,
            "z": 10,
            "layer": "soil_properties"
        }
        
        response = client.post("/tiles/", json=invalid_request, headers=auth_headers)
        assert response.status_code == 422
    
    def test_get_tile_metadata(self, client, auth_headers):
        """Test retrieving tile metadata."""
        # First create a tile
        tile_request = {
            "x": 512,
            "y": 384,
            "z": 9,
            "layer": "temperature"
        }
        
        create_response = client.post("/tiles/", json=tile_request, headers=auth_headers)
        assert create_response.status_code == 200
        tile_id = create_response.json()["tile_id"]
        
        # Get tile metadata
        response = client.get(f"/tiles/{tile_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["tile_id"] == tile_id
        assert "bounds" in data
        assert "creation_time" in data
    
    def test_get_nonexistent_tile(self, client, auth_headers):
        """Test retrieving metadata for non-existent tile."""
        response = client.get("/tiles/nonexistent_tile", headers=auth_headers)
        assert response.status_code == 404
        
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_list_tiles(self, client, auth_headers):
        """Test listing all tiles."""
        # Create a few tiles
        tiles_to_create = [
            {"x": 100, "y": 200, "z": 8, "layer": "vegetation"},
            {"x": 101, "y": 200, "z": 8, "layer": "vegetation"},
            {"x": 100, "y": 201, "z": 8, "layer": "soil"}
        ]
        
        for tile_request in tiles_to_create:
            client.post("/tiles/", json=tile_request, headers=auth_headers)
        
        # List all tiles
        response = client.get("/tiles/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(tiles_to_create)
    
    def test_list_tiles_with_filter(self, client, auth_headers):
        """Test listing tiles with layer filter."""
        # Create tiles with different layers
        client.post("/tiles/", json={"x": 300, "y": 400, "z": 7, "layer": "filter_test_1"}, headers=auth_headers)
        client.post("/tiles/", json={"x": 301, "y": 400, "z": 7, "layer": "filter_test_2"}, headers=auth_headers)
        
        # Filter by layer
        response = client.get("/tiles/?layer=filter_test_1", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        filtered_tiles = [tile for tile in data if "filter_test_1" in tile["tile_id"]]
        assert len(filtered_tiles) >= 1
    
    def test_delete_tile(self, client, auth_headers):
        """Test tile deletion."""
        # Create a tile
        tile_request = {"x": 999, "y": 888, "z": 12, "layer": "delete_test"}
        create_response = client.post("/tiles/", json=tile_request, headers=auth_headers)
        tile_id = create_response.json()["tile_id"]
        
        # Delete the tile
        response = client.delete(f"/tiles/{tile_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify tile is gone
        get_response = client.get(f"/tiles/{tile_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_tile(self, client, auth_headers):
        """Test deleting non-existent tile."""
        response = client.delete("/tiles/nonexistent_tile", headers=auth_headers)
        assert response.status_code == 404
    
    def test_analyze_raster_file(self, client, auth_headers, sample_raster_file):
        """Test raster file analysis."""
        with open(sample_raster_file, 'rb') as f:
            files = {"file": ("test.tif", f, "image/tiff")}
            response = client.post("/raster/analyze/", files=files, headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["band_count"] == 1
        assert data["width"] == 256
        assert data["height"] == 256
        assert data["crs"] == "EPSG:4326"
        assert len(data["bounds"]) == 4
        assert "min_value" in data
        assert "max_value" in data
        assert "mean_value" in data
    
    def test_analyze_invalid_file_format(self, client, auth_headers):
        """Test raster analysis with invalid file format."""
        # Create a text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a raster file")
            txt_file = f.name
        
        try:
            with open(txt_file, 'rb') as f:
                files = {"file": ("test.txt", f, "text/plain")}
                response = client.post("/raster/analyze/", files=files, headers=auth_headers)
            
            assert response.status_code == 400
            assert "Unsupported file format" in response.json()["detail"]
        finally:
            os.unlink(txt_file)
    
    def test_webhook_events(self, client, auth_headers):
        """Test webhook event functionality."""
        # Create a tile to generate events
        tile_request = {"x": 777, "y": 666, "z": 13, "layer": "webhook_test"}
        client.post("/tiles/", json=tile_request, headers=auth_headers)
        
        # Get webhook events
        response = client.get("/webhooks/events/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should have at least one event from tile creation
        tile_events = [event for event in data if event["event_type"] == "tile_created"]
        assert len(tile_events) >= 1
    
    def test_simulate_webhook_event(self, client, auth_headers):
        """Test webhook event simulation."""
        test_event = {
            "event_type": "test_event",
            "tile_id": "test_tile_123",
            "timestamp": datetime.now().isoformat(),
            "payload": {"test": "data"}
        }
        
        response = client.post("/webhooks/simulate/", json=test_event, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "simulated successfully" in data["message"]
        assert "event_id" in data
    
    def test_webhook_event_filtering(self, client, auth_headers):
        """Test filtering webhook events by type."""
        # Simulate a custom event
        test_event = {
            "event_type": "custom_test_event",
            "timestamp": datetime.now().isoformat(),
            "payload": {"filter": "test"}
        }
        client.post("/webhooks/simulate/", json=test_event, headers=auth_headers)
        
        # Filter events by type
        response = client.get("/webhooks/events/?event_type=custom_test_event", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        filtered_events = [event for event in data if event["event_type"] == "custom_test_event"]
        assert len(filtered_events) >= 1


class TestRasterUtils:
    @pytest.fixture
    def sample_raster(self):
        """Create a sample raster file for testing."""
        fd, path = tempfile.mkstemp(suffix='.tif')
        os.close(fd)
        create_sample_raster(path, 128, 128)
        yield path
        os.unlink(path)
    
    @pytest.fixture
    def processor(self):
        """Create RasterProcessor instance."""
        return RasterProcessor(tile_size=256)
    
    def test_validate_raster_valid_file(self, processor, sample_raster):
        """Test raster validation with valid file."""
        result = processor.validate_raster(sample_raster)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert "metadata" in result
        assert result["metadata"]["width"] == 128
        assert result["metadata"]["height"] == 128
        assert result["metadata"]["band_count"] == 1
    
    def test_validate_raster_invalid_file(self, processor):
        """Test raster validation with invalid file."""
        result = processor.validate_raster("nonexistent_file.tif")
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "Failed to open raster file" in result["errors"][0]
    
    def test_calculate_statistics(self, processor, sample_raster):
        """Test raster statistics calculation."""
        stats = processor.calculate_statistics(sample_raster)
        
        assert "count" in stats
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert "std" in stats
        assert "valid_pixels" in stats
        
        # Check that min <= mean <= max
        assert stats["min"] <= stats["mean"] <= stats["max"]
        assert stats["std"] >= 0
    
    def test_generate_tile(self, processor, sample_raster):
        """Test tile generation."""
        tile_data = processor.generate_tile(sample_raster, x=0, y=0, z=1)
        
        assert tile_data is not None
        assert tile_data.shape == (256, 256)  # Default tile size
        assert isinstance(tile_data, np.ndarray)
    
    def test_create_overview(self, processor, sample_raster):
        """Test overview creation."""
        result = processor.create_overview(sample_raster, [2, 4])
        
        # Should succeed for valid raster
        assert result is True
    
    def test_create_sample_raster(self):
        """Test sample raster creation."""
        fd, path = tempfile.mkstemp(suffix='.tif')
        os.close(fd)
        
        try:
            result_path = create_sample_raster(path, 64, 64)
            assert result_path == path
            assert os.path.exists(path)
            
            # Verify raster properties
            import rasterio
            with rasterio.open(path) as src:
                assert src.width == 64
                assert src.height == 64
                assert src.count == 1
                assert str(src.crs) == "EPSG:4326"
        finally:
            os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__])