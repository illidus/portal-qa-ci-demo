"""
Utility functions for Portal QA/CI Demo
"""

import hashlib
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta


def generate_request_id(prefix: str = "req") -> str:
    """Generate a unique request ID."""
    timestamp = str(int(time.time()))
    random_suffix = str(random.randint(1000, 9999))
    return f"{prefix}_{timestamp}_{random_suffix}"


def calculate_geospatial_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate approximate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    import math
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in kilometers
    r = 6371
    return c * r


def validate_coordinate_bounds(lat: float, lon: float) -> Dict[str, bool]:
    """Validate if coordinates are within reasonable geographic bounds."""
    return {
        "latitude_valid": -90 <= lat <= 90,
        "longitude_valid": -180 <= lon <= 180,
        "in_ocean": abs(lat) < 60 and abs(lon) < 180,  # Simplified ocean check
        "in_polar_region": abs(lat) > 66.5
    }


def compute_data_quality_score(data: Dict[str, Any]) -> float:
    """Compute a data quality score based on completeness and validity."""
    score = 0.0
    total_possible = 0
    
    # Check for required fields
    required_fields = ['request_id', 'data_type', 'location']
    for field in required_fields:
        total_possible += 1
        if field in data and data[field] is not None:
            score += 1
    
    # Check for optional fields that improve quality
    optional_fields = ['parameters', 'tags', 'priority']
    for field in optional_fields:
        total_possible += 0.5
        if field in data and data[field] is not None:
            score += 0.5
    
    # Bonus for data type validity
    if data.get('data_type') in ['raster', 'vector', 'timeseries', 'point_cloud']:
        score += 0.5
        total_possible += 0.5
    
    return min(score / total_possible, 1.0) if total_possible > 0 else 0.0


def estimate_processing_time(data_type: str, parameters: Dict[str, Any]) -> int:
    """Estimate processing time in seconds based on data type and parameters."""
    base_times = {
        'raster': 30,
        'vector': 15,
        'timeseries': 45,
        'point_cloud': 120,
        'metadata': 5
    }
    
    base_time = base_times.get(data_type, 60)
    
    # Adjust based on resolution
    if 'resolution' in parameters:
        try:
            resolution = float(parameters['resolution'])
            if resolution < 1:  # High resolution
                base_time *= 2
            elif resolution > 10:  # Low resolution
                base_time *= 0.5
        except (ValueError, TypeError):
            pass
    
    # Add random variation
    variation = random.uniform(0.8, 1.2)
    return int(base_time * variation)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def generate_mock_output_files(request_id: str, data_type: str) -> List[str]:
    """Generate mock output file paths."""
    base_path = f"/outputs/{request_id}"
    
    files = [f"{base_path}/result.{data_type}"]
    
    # Add common auxiliary files
    files.extend([
        f"{base_path}/metadata.json",
        f"{base_path}/processing_log.txt"
    ])
    
    # Add type-specific files
    if data_type == 'raster':
        files.extend([
            f"{base_path}/statistics.csv",
            f"{base_path}/histogram.png"
        ])
    elif data_type == 'vector':
        files.extend([
            f"{base_path}/attributes.csv",
            f"{base_path}/spatial_index.qix"
        ])
    elif data_type == 'timeseries':
        files.extend([
            f"{base_path}/trends.csv",
            f"{base_path}/forecast.json"
        ])
    
    return files


def create_processing_summary(request_id: str, status: str, start_time: datetime) -> Dict[str, Any]:
    """Create a processing summary with timing information."""
    now = datetime.now()
    duration = (now - start_time).total_seconds()
    
    return {
        "request_id": request_id,
        "status": status,
        "start_time": start_time.isoformat(),
        "end_time": now.isoformat(),
        "duration_seconds": duration,
        "performance_metrics": {
            "cpu_usage": random.uniform(10, 80),
            "memory_usage": random.uniform(20, 60),
            "disk_io": random.uniform(5, 100)
        }
    }