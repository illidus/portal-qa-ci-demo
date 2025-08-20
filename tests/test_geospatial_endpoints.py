"""
Unit tests for geospatial endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestGeospatialValidateEndpoint:
    """Test /geospatial/validate endpoint."""
    
    def test_validate_complete_geospatial_data(self):
        """Test validation of complete geospatial data."""
        location_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "elevation": 10.0,
            "accuracy": 2.5
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_checks" in data
        assert "passed_checks" in data
        assert "failed_checks" in data
        assert "score" in data
        assert "details" in data
        
        assert 0.0 <= data["score"] <= 1.0
        assert data["total_checks"] == data["passed_checks"] + data["failed_checks"]
    
    def test_validate_minimal_geospatial_data(self):
        """Test validation of minimal geospatial data."""
        location_data = {
            "latitude": 51.5074,
            "longitude": -0.1278
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["score"] < 1.0  # Should be lower than complete data
        assert "elevation_check" in data["details"]
        assert "accuracy_assessment" in data["details"]
    
    def test_validate_high_accuracy_data(self):
        """Test validation of high accuracy geospatial data."""
        location_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "elevation": 52.0,
            "accuracy": 1.0  # Very high accuracy
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["details"]["accuracy_assessment"] == "good"
        assert data["score"] > 0.7  # Should have high score
    
    def test_validate_moderate_accuracy_data(self):
        """Test validation of moderate accuracy geospatial data."""
        location_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "elevation": 52.0,
            "accuracy": 15.0  # Moderate accuracy
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["details"]["accuracy_assessment"] == "moderate"
    
    def test_validate_polar_coordinates(self):
        """Test validation of polar region coordinates."""
        location_data = {
            "latitude": 85.0,  # Arctic
            "longitude": 0.0,
            "elevation": 0.0,
            "accuracy": 5.0
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["warnings"] == 1  # Should have warning for polar region
        assert data["details"]["location_type"] == "polar"
    
    def test_validate_standard_coordinates(self):
        """Test validation of standard (non-polar) coordinates."""
        location_data = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "elevation": 10.0,
            "accuracy": 3.0
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["warnings"] == 0  # No warnings for standard location
        assert data["details"]["location_type"] == "standard"
    
    def test_validate_invalid_coordinates(self):
        """Test validation fails for invalid coordinates."""
        location_data = {
            "latitude": 91.0,  # Invalid
            "longitude": -74.0060
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 422
    
    def test_validate_extreme_elevation(self):
        """Test validation of extreme elevation values."""
        # Test very high elevation
        location_data = {
            "latitude": 27.9881,  # Everest area
            "longitude": 86.9250,
            "elevation": 8848.0,  # Mount Everest
            "accuracy": 10.0
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["details"]["elevation_check"] == "passed"
    
    def test_validate_zero_coordinates_fails(self):
        """Test that zero coordinates are rejected."""
        location_data = {
            "latitude": 0.0,  # Should be rejected
            "longitude": -74.0060
        }
        
        response = client.post("/geospatial/validate", json=location_data)
        assert response.status_code == 422


class TestGeospatialDistanceEndpoint:
    """Test /geospatial/distance endpoint."""
    
    def test_distance_same_coordinates(self):
        """Test distance calculation for identical coordinates."""
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060&lat2=40.7128&lon2=-74.0060"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["distance_km"] == 0.0
        assert data["distance_miles"] == 0.0
        assert "coordinates" in data
        assert data["coordinates"]["point1"]["latitude"] == 40.7128
    
    def test_distance_known_cities(self):
        """Test distance calculation between known cities."""
        # NYC to Boston (approximate distance ~300 km)
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060&lat2=42.3601&lon2=-71.0589"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 250 < data["distance_km"] < 350  # Approximate distance
        assert 150 < data["distance_miles"] < 220  # Miles conversion
    
    def test_distance_cross_atlantic(self):
        """Test distance calculation across Atlantic."""
        # NYC to London
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060&lat2=51.5074&lon2=-0.1278"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert 5000 < data["distance_km"] < 6000  # Approximate distance
        assert data["distance_miles"] > 0
    
    def test_distance_antipodal_points(self):
        """Test distance calculation for antipodal points."""
        response = client.get(
            "/geospatial/distance?lat1=0&lon1=0&lat2=0&lon2=180"
        )
        assert response.status_code == 200
        
        data = response.json()
        # Should be approximately half Earth's circumference
        expected_distance = 3.14159 * 6371  # π * Earth radius
        assert abs(data["distance_km"] - expected_distance) < 100
    
    def test_distance_invalid_coordinates(self):
        """Test distance calculation with invalid coordinates."""
        response = client.get(
            "/geospatial/distance?lat1=91&lon1=0&lat2=0&lon2=0"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data["detail"].lower()
    
    def test_distance_missing_parameters(self):
        """Test distance calculation with missing parameters."""
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060"
            # Missing lat2 and lon2
        )
        assert response.status_code == 422
    
    def test_distance_response_format(self):
        """Test that distance response has correct format."""
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060&lat2=42.3601&lon2=-71.0589"
        )
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["distance_km", "distance_miles", "coordinates"]
        for field in required_fields:
            assert field in data
        
        # Check coordinate structure
        coords = data["coordinates"]
        assert "point1" in coords
        assert "point2" in coords
        
        point1 = coords["point1"]
        assert "latitude" in point1
        assert "longitude" in point1
        
        point2 = coords["point2"]
        assert "latitude" in point2
        assert "longitude" in point2
    
    def test_distance_precision(self):
        """Test distance calculation precision."""
        response = client.get(
            "/geospatial/distance?lat1=40.7128&lon1=-74.0060&lat2=40.7628&lon2=-73.9560"
        )
        assert response.status_code == 200
        
        data = response.json()
        # Distances should be rounded to 2 decimal places
        km_str = str(data["distance_km"])
        miles_str = str(data["distance_miles"])
        
        if "." in km_str:
            assert len(km_str.split(".")[1]) <= 2
        if "." in miles_str:
            assert len(miles_str.split(".")[1]) <= 2
    
    def test_distance_boundary_coordinates(self):
        """Test distance calculation with boundary coordinates."""
        # Test with extreme valid coordinates
        response = client.get(
            "/geospatial/distance?lat1=90&lon1=180&lat2=-90&lon2=-180"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["distance_km"] > 0
        assert data["distance_miles"] > 0
    
    def test_distance_float_precision(self):
        """Test distance calculation with high precision coordinates."""
        response = client.get(
            "/geospatial/distance?lat1=40.712812&lon1=-74.006015&lat2=40.712813&lon2=-74.006016"
        )
        assert response.status_code == 200
        
        data = response.json()
        # Very small distance should be calculated correctly
        assert data["distance_km"] < 0.1  # Should be very small
        assert data["distance_miles"] < 0.1