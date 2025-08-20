# Portal QA/CI Demo

FastAPI application with comprehensive Pydantic validation, 25+ tests, and ≥90% coverage.

## Features

- **FastAPI with Pydantic**: Comprehensive validation and error handling
- **25+ Unit Tests**: Exhaustive endpoint testing with ≥90% coverage
- **GitHub Actions CI**: Automated testing and security scanning
- **Postman Collection**: Complete API testing collection
- **Authentication**: Bearer token validation
- **CORS Support**: Cross-origin request handling

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn api.main:app --reload

# Run tests with coverage
pytest test_api.py --cov=api --cov-report=term-missing -v

# Test API startup
python -c "from api.main import app; print('✅ API loads successfully')"
```

## API Endpoints

### Public Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /status` - Detailed service status
- `GET /layers` - List available data layers

### Authenticated Endpoints (Bearer token required)
- `POST /tiles` - Generate map tiles
- `POST /metadata` - Get layer metadata for bounding box
- `POST /upload` - Upload and process GeoTIFF files

## Authentication

All protected endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer demo_api_token_12345" \
     -X POST http://localhost:8000/tiles \
     -H "Content-Type: application/json" \
     -d '{"x": 5, "y": 10, "z": 8, "layer": "soil_ph"}'
```

## Pydantic Validation

Comprehensive input validation with detailed error messages:

### TileRequest Model
- `x`, `y`: Non-negative integers
- `z`: Zoom level (0-18)
- `layer`: Must be one of: soil_ph, organic_matter, elevation, ndvi

### BoundingBox Model
- `west`, `east`: Longitude (-180 to 180), west < east
- `south`, `north`: Latitude (-90 to 90), south < north

### MetadataRequest Model
- `bbox`: Valid BoundingBox
- `layers`: 1-10 valid layer names
- `start_date`, `end_date`: Optional datetime range (start < end)

## Testing

### Test Coverage
```bash
pytest test_api.py --cov=api --cov-report=term-missing -v
```

**Coverage Target**: ≥90%
**Test Count**: 30+ comprehensive tests covering:

- All endpoint functionality
- Authentication scenarios
- Input validation edge cases
- Error handling
- CORS support
- File upload validation

### Test Categories
1. **Basic Endpoints** (4 tests): Root, health, layers, status
2. **Tile Endpoints** (6 tests): Valid requests, invalid params, auth
3. **Metadata Endpoints** (8 tests): Valid/invalid bbox, layers, dates
4. **Upload Endpoints** (5 tests): File validation, auth
5. **Authentication** (3 tests): Valid/invalid tokens
6. **Edge Cases** (4 tests): Malformed requests, CORS, boundaries

## GitHub Actions CI

Automated pipeline (`.github/workflows/ci.yml`):

### Test Job
- Multi-Python version testing (3.9, 3.10, 3.11)
- Dependency installation
- Code linting with flake8
- Test execution with coverage reporting
- API startup verification

### Security Job
- Security scanning with bandit
- Dependency vulnerability checks with safety
- Report generation and artifact upload

## Postman Collection

Import `postman_collection.json` for complete API testing:

### Collection Features
- Pre-configured authentication
- Environment variables
- All endpoint examples
- Error case scenarios
- Example request/response pairs

### Collection Sections
1. **Health & Status**: Root, health, status endpoints
2. **Layers**: Available layer listing
3. **Tiles**: Tile generation for different layers
4. **Metadata**: Single/multi-layer metadata queries
5. **Upload**: File upload examples
6. **Error Cases**: Invalid requests and auth failures

## Development

### Running Locally
```bash
# Start development server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Access interactive docs
open http://localhost:8000/docs
```

### Adding New Endpoints
1. Define Pydantic models for request/response
2. Implement endpoint with proper validation
3. Add authentication if required
4. Write comprehensive tests (≥3 per endpoint)
5. Update Postman collection
6. Verify coverage stays ≥90%

## File Structure

```
├── api/
│   ├── __init__.py           # Package initialization
│   └── main.py               # FastAPI application
├── .github/workflows/
│   └── ci.yml                # GitHub Actions CI pipeline
├── test_api.py               # Comprehensive test suite (30+ tests)
├── postman_collection.json   # Postman testing collection
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```