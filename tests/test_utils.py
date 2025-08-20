"""
Unit tests for utility functions
"""

import pytest
import math
from datetime import datetime

from app.utils import (
    generate_request_id, calculate_geospatial_distance,
    validate_coordinate_bounds, compute_data_quality_score,
    estimate_processing_time, format_file_size,
    generate_mock_output_files, create_processing_summary
)


class TestGenerateRequestId:
    """Test request ID generation."""
    
    def test_default_prefix(self):
        """Test request ID generation with default prefix."""
        request_id = generate_request_id()
        assert request_id.startswith("req_")
        parts = request_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "req"
    
    def test_custom_prefix(self):
        """Test request ID generation with custom prefix."""
        request_id = generate_request_id("custom")
        assert request_id.startswith("custom_")
        parts = request_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "custom"
    
    def test_unique_ids(self):
        """Test that generated IDs are unique."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2


class TestGeospatialDistance:
    """Test geospatial distance calculation."""
    
    def test_same_coordinates(self):
        """Test distance between identical coordinates."""
        distance = calculate_geospatial_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0.0
    
    def test_known_distance(self):
        """Test distance calculation for known coordinates."""
        # NYC to LA (approximate)
        nyc_lat, nyc_lon = 40.7128, -74.0060
        la_lat, la_lon = 34.0522, -118.2437
        
        distance = calculate_geospatial_distance(nyc_lat, nyc_lon, la_lat, la_lon)
        
        # Approximate distance is ~3944 km
        assert 3900 < distance < 4000
    
    def test_short_distance(self):
        """Test distance calculation for nearby coordinates."""
        # Two points in Manhattan
        lat1, lon1 = 40.7128, -74.0060  # Lower Manhattan
        lat2, lon2 = 40.7831, -73.9712  # Upper Manhattan
        
        distance = calculate_geospatial_distance(lat1, lon1, lat2, lon2)
        
        # Should be around 10-15 km
        assert 8 < distance < 20
    
    def test_antipodal_points(self):
        """Test distance calculation for antipodal points."""
        distance = calculate_geospatial_distance(0, 0, 0, 180)
        
        # Half the Earth's circumference
        expected = math.pi * 6371  # Earth radius
        assert abs(distance - expected) < 100


class TestValidateCoordinateBounds:
    """Test coordinate bounds validation."""
    
    def test_valid_coordinates(self):
        """Test validation of valid coordinates."""
        result = validate_coordinate_bounds(40.7128, -74.0060)
        
        assert result["latitude_valid"] is True
        assert result["longitude_valid"] is True
        assert result["in_ocean"] is True
        assert result["in_polar_region"] is False
    
    def test_invalid_latitude(self):
        """Test validation of invalid latitude."""
        result = validate_coordinate_bounds(91.0, -74.0060)
        
        assert result["latitude_valid"] is False
        assert result["longitude_valid"] is True
    
    def test_invalid_longitude(self):
        """Test validation of invalid longitude."""
        result = validate_coordinate_bounds(40.7128, 181.0)
        
        assert result["latitude_valid"] is True
        assert result["longitude_valid"] is False
    
    def test_polar_coordinates(self):
        """Test validation of polar coordinates."""
        result = validate_coordinate_bounds(80.0, 0.0)  # Arctic
        
        assert result["latitude_valid"] is True
        assert result["longitude_valid"] is True
        assert result["in_polar_region"] is True
    
    def test_boundary_coordinates(self):
        """Test validation of boundary coordinates."""
        # Test exact boundaries
        result1 = validate_coordinate_bounds(90.0, 180.0)
        assert result1["latitude_valid"] is True
        assert result1["longitude_valid"] is True
        
        result2 = validate_coordinate_bounds(-90.0, -180.0)
        assert result2["latitude_valid"] is True
        assert result2["longitude_valid"] is True


class TestComputeDataQualityScore:
    """Test data quality score computation."""
    
    def test_complete_data(self):
        """Test score for complete data."""
        data = {
            "request_id": "test_123",
            "data_type": "raster",
            "location": {"lat": 40.7, "lon": -74.0},
            "parameters": {"format": "tiff"},
            "tags": ["test"],
            "priority": 3
        }
        
        score = compute_data_quality_score(data)
        assert 0.8 <= score <= 1.0
    
    def test_minimal_data(self):
        """Test score for minimal data."""
        data = {
            "request_id": "test_123",
            "data_type": "vector",
            "location": {"lat": 40.7, "lon": -74.0}
        }
        
        score = compute_data_quality_score(data)
        assert 0.3 <= score <= 0.7
    
    def test_empty_data(self):
        """Test score for empty data."""
        data = {}
        
        score = compute_data_quality_score(data)
        assert score == 0.0
    
    def test_invalid_data_type(self):
        """Test score with invalid data type."""
        data = {
            "request_id": "test_123",
            "data_type": "invalid_type",
            "location": {"lat": 40.7, "lon": -74.0}
        }
        
        score = compute_data_quality_score(data)
        assert score < 1.0


class TestEstimateProcessingTime:
    """Test processing time estimation."""
    
    def test_different_data_types(self):
        """Test time estimation for different data types."""
        parameters = {"resolution": "10m", "format": "tiff"}
        
        raster_time = estimate_processing_time("raster", parameters)
        vector_time = estimate_processing_time("vector", parameters)
        point_cloud_time = estimate_processing_time("point_cloud", parameters)
        
        # Point cloud should take longest
        assert point_cloud_time > raster_time
        assert point_cloud_time > vector_time
    
    def test_resolution_impact(self):
        """Test that resolution affects processing time."""
        high_res = {"resolution": "0.5", "format": "tiff"}
        low_res = {"resolution": "50", "format": "tiff"}
        
        high_res_time = estimate_processing_time("raster", high_res)
        low_res_time = estimate_processing_time("raster", low_res)
        
        # High resolution should take longer
        assert high_res_time >= low_res_time
    
    def test_unknown_data_type(self):
        """Test time estimation for unknown data type."""
        parameters = {"resolution": "10m", "format": "tiff"}
        
        time_estimate = estimate_processing_time("unknown", parameters)
        assert isinstance(time_estimate, int)
        assert time_estimate > 0
    
    def test_invalid_resolution(self):
        """Test time estimation with invalid resolution."""
        parameters = {"resolution": "invalid", "format": "tiff"}
        
        time_estimate = estimate_processing_time("raster", parameters)
        assert isinstance(time_estimate, int)
        assert time_estimate > 0


class TestFormatFileSize:
    """Test file size formatting."""
    
    def test_bytes(self):
        """Test formatting of byte values."""
        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1023) == "1023.0 B"
    
    def test_kilobytes(self):
        """Test formatting of kilobyte values."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
    
    def test_megabytes(self):
        """Test formatting of megabyte values."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"
    
    def test_gigabytes(self):
        """Test formatting of gigabyte values."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
    
    def test_terabytes(self):
        """Test formatting of terabyte values."""
        huge_size = 1024 * 1024 * 1024 * 1024
        result = format_file_size(huge_size)
        assert "TB" in result


class TestGenerateMockOutputFiles:
    """Test mock output file generation."""
    
    def test_raster_files(self):
        """Test file generation for raster data."""
        files = generate_mock_output_files("test_123", "raster")
        
        assert any("result.raster" in f for f in files)
        assert any("metadata.json" in f for f in files)
        assert any("statistics.csv" in f for f in files)
        assert any("histogram.png" in f for f in files)
    
    def test_vector_files(self):
        """Test file generation for vector data."""
        files = generate_mock_output_files("test_456", "vector")
        
        assert any("result.vector" in f for f in files)
        assert any("attributes.csv" in f for f in files)
        assert any("spatial_index.qix" in f for f in files)
    
    def test_timeseries_files(self):
        """Test file generation for timeseries data."""
        files = generate_mock_output_files("test_789", "timeseries")
        
        assert any("result.timeseries" in f for f in files)
        assert any("trends.csv" in f for f in files)
        assert any("forecast.json" in f for f in files)
    
    def test_common_files(self):
        """Test that common files are always generated."""
        files = generate_mock_output_files("test_000", "metadata")
        
        assert any("metadata.json" in f for f in files)
        assert any("processing_log.txt" in f for f in files)
    
    def test_file_paths_structure(self):
        """Test that file paths have correct structure."""
        files = generate_mock_output_files("test_123", "raster")
        
        for file_path in files:
            assert file_path.startswith("/outputs/test_123/")


class TestCreateProcessingSummary:
    """Test processing summary creation."""
    
    def test_summary_structure(self):
        """Test processing summary has correct structure."""
        start_time = datetime.now()
        summary = create_processing_summary("test_123", "completed", start_time)
        
        assert summary["request_id"] == "test_123"
        assert summary["status"] == "completed"
        assert "start_time" in summary
        assert "end_time" in summary
        assert "duration_seconds" in summary
        assert "performance_metrics" in summary
    
    def test_performance_metrics(self):
        """Test performance metrics are included."""
        start_time = datetime.now()
        summary = create_processing_summary("test_456", "failed", start_time)
        
        metrics = summary["performance_metrics"]
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_io" in metrics
        
        # Values should be reasonable
        assert 0 <= metrics["cpu_usage"] <= 100
        assert 0 <= metrics["memory_usage"] <= 100
        assert 0 <= metrics["disk_io"] <= 100
    
    def test_timing_calculation(self):
        """Test that timing calculation works correctly."""
        start_time = datetime.now()
        summary = create_processing_summary("test_789", "processing", start_time)
        
        # Duration should be very small (nearly instant)
        assert summary["duration_seconds"] >= 0
        assert summary["duration_seconds"] < 1  # Should complete in less than 1 second