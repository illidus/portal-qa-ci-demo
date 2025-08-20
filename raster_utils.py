"""
Raster processing utilities for map tile generation
"""

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import Window
from typing import Tuple, Optional, List, Dict, Any
import tempfile
import os


class RasterProcessor:
    """Utility class for raster data processing and tile generation."""
    
    def __init__(self, tile_size: int = 256):
        self.tile_size = tile_size
    
    def validate_raster(self, file_path: str) -> Dict[str, Any]:
        """
        Validate raster file and return metadata.
        
        Args:
            file_path: Path to raster file
            
        Returns:
            Dictionary with validation results and metadata
        """
        try:
            with rasterio.open(file_path) as src:
                # Basic validation checks
                validation = {
                    "is_valid": True,
                    "errors": [],
                    "warnings": [],
                    "metadata": {
                        "width": src.width,
                        "height": src.height,
                        "band_count": src.count,
                        "crs": str(src.crs),
                        "bounds": list(src.bounds),
                        "dtype": str(src.dtypes[0]),
                        "nodata": src.nodata
                    }
                }
                
                # Check for common issues
                if src.crs is None:
                    validation["warnings"].append("Missing coordinate reference system (CRS)")
                
                if src.width == 0 or src.height == 0:
                    validation["errors"].append("Invalid raster dimensions")
                    validation["is_valid"] = False
                
                if src.count == 0:
                    validation["errors"].append("No data bands found")
                    validation["is_valid"] = False
                
                # Check data range
                try:
                    sample_data = src.read(1, window=Window(0, 0, min(100, src.width), min(100, src.height)))
                    if np.all(np.isnan(sample_data)) or np.all(sample_data == src.nodata):
                        validation["warnings"].append("Sample data appears to be all NoData")
                except Exception as e:
                    validation["warnings"].append(f"Could not read sample data: {str(e)}")
                
                return validation
                
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Failed to open raster file: {str(e)}"],
                "warnings": [],
                "metadata": {}
            }
    
    def reproject_raster(self, src_path: str, dst_crs: str = "EPSG:4326") -> str:
        """
        Reproject raster to target CRS.
        
        Args:
            src_path: Source raster file path
            dst_crs: Target coordinate reference system
            
        Returns:
            Path to reprojected raster file
        """
        with rasterio.open(src_path) as src:
            # Calculate transform and dimensions for target CRS
            transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            
            # Create output profile
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            # Create temporary output file
            dst_fd, dst_path = tempfile.mkstemp(suffix='.tif')
            os.close(dst_fd)
            
            with rasterio.open(dst_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=dst_crs,
                        resampling=Resampling.bilinear
                    )
            
            return dst_path
    
    def generate_tile(self, src_path: str, x: int, y: int, z: int) -> Optional[np.ndarray]:
        """
        Generate a map tile from raster data.
        
        Args:
            src_path: Source raster file path
            x: Tile X coordinate
            y: Tile Y coordinate  
            z: Zoom level
            
        Returns:
            Numpy array representing the tile, or None if no data
        """
        with rasterio.open(src_path) as src:
            # Calculate tile bounds in Web Mercator
            tile_bounds = self._tile_to_bounds(x, y, z)
            
            # Transform bounds to source CRS
            if src.crs != "EPSG:4326":
                # For simplicity, assume source is already in appropriate CRS
                # In production, properly transform coordinates
                pass
            
            # Calculate window in source raster
            window = rasterio.windows.from_bounds(*tile_bounds, src.transform)
            
            # Read data
            try:
                data = src.read(1, window=window, out_shape=(self.tile_size, self.tile_size))
                
                # Handle NoData
                if src.nodata is not None:
                    data = np.ma.masked_equal(data, src.nodata)
                
                return data
                
            except Exception:
                # Return empty tile if read fails
                return np.zeros((self.tile_size, self.tile_size), dtype=np.float32)
    
    def _tile_to_bounds(self, x: int, y: int, z: int) -> Tuple[float, float, float, float]:
        """Convert tile coordinates to geographic bounds."""
        n = 2.0 ** z
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = np.arctan(np.sinh(np.pi * (1 - 2 * y / n)))
        lat_deg = np.degrees(lat_rad)
        
        # Tile bounds
        tile_size = 360.0 / n
        return (lon_deg, lat_deg, lon_deg + tile_size, lat_deg + tile_size)
    
    def calculate_statistics(self, file_path: str, band: int = 1) -> Dict[str, float]:
        """
        Calculate comprehensive statistics for a raster band.
        
        Args:
            file_path: Path to raster file
            band: Band number (1-indexed)
            
        Returns:
            Dictionary with statistical measures
        """
        with rasterio.open(file_path) as src:
            data = src.read(band, masked=True)
            
            if data.size == 0:
                return {"error": "No data in specified band"}
            
            stats = {
                "count": int(data.count()),
                "min": float(data.min()),
                "max": float(data.max()),
                "mean": float(data.mean()),
                "median": float(np.median(data.compressed())),
                "std": float(data.std()),
                "variance": float(data.var()),
                "sum": float(data.sum()),
                "valid_pixels": int(np.sum(~data.mask)),
                "nodata_pixels": int(np.sum(data.mask)),
                "total_pixels": int(data.size)
            }
            
            # Calculate percentiles
            compressed_data = data.compressed()
            if len(compressed_data) > 0:
                percentiles = [1, 5, 10, 25, 75, 90, 95, 99]
                for p in percentiles:
                    stats[f"percentile_{p}"] = float(np.percentile(compressed_data, p))
            
            return stats
    
    def create_overview(self, file_path: str, overview_levels: List[int] = None) -> bool:
        """
        Create overview pyramids for faster tile serving.
        
        Args:
            file_path: Path to raster file
            overview_levels: List of overview levels (e.g., [2, 4, 8, 16])
            
        Returns:
            True if successful, False otherwise
        """
        if overview_levels is None:
            overview_levels = [2, 4, 8, 16]
        
        try:
            with rasterio.open(file_path, 'r+') as src:
                src.build_overviews(overview_levels, Resampling.average)
                src.update_tags(ns='rio_overview', resampling='average')
            return True
        except Exception:
            return False
    
    def clip_raster(self, src_path: str, bounds: Tuple[float, float, float, float]) -> str:
        """
        Clip raster to specified bounds.
        
        Args:
            src_path: Source raster file path
            bounds: Clipping bounds (minx, miny, maxx, maxy)
            
        Returns:
            Path to clipped raster file
        """
        with rasterio.open(src_path) as src:
            # Calculate window from bounds
            window = rasterio.windows.from_bounds(*bounds, src.transform)
            
            # Read clipped data
            clipped_data = src.read(window=window)
            
            # Update transform for clipped area
            clipped_transform = rasterio.windows.transform(window, src.transform)
            
            # Create output profile
            profile = src.profile.copy()
            profile.update({
                'height': clipped_data.shape[1],
                'width': clipped_data.shape[2],
                'transform': clipped_transform
            })
            
            # Create temporary output file
            dst_fd, dst_path = tempfile.mkstemp(suffix='.tif')
            os.close(dst_fd)
            
            with rasterio.open(dst_path, 'w', **profile) as dst:
                dst.write(clipped_data)
            
            return dst_path


def create_sample_raster(output_path: str, width: int = 512, height: int = 512) -> str:
    """
    Create a sample raster file for testing purposes.
    
    Args:
        output_path: Output file path
        width: Raster width in pixels
        height: Raster height in pixels
        
    Returns:
        Path to created raster file
    """
    # Generate sample data
    x = np.linspace(-2, 2, width)
    y = np.linspace(-2, 2, height)
    X, Y = np.meshgrid(x, y)
    
    # Create synthetic elevation data
    Z = np.sin(X) * np.cos(Y) * np.exp(-(X**2 + Y**2)/4) + np.random.normal(0, 0.1, (height, width))
    Z = ((Z - Z.min()) / (Z.max() - Z.min()) * 1000).astype(np.float32)  # Scale to 0-1000m
    
    # Define raster properties
    transform = rasterio.transform.from_bounds(-104.5, 41.0, -104.0, 41.5, width, height)
    
    profile = {
        'driver': 'GTiff',
        'dtype': 'float32',
        'nodata': -9999.0,
        'width': width,
        'height': height,
        'count': 1,
        'crs': 'EPSG:4326',
        'transform': transform,
        'compress': 'lzw'
    }
    
    # Write raster
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(Z, 1)
    
    return output_path