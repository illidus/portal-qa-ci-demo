"""
Unit tests for Portal QA/CI Demo FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app, UserProfile
import json

client = TestClient(app)

class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns expected response."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Portal QA/CI Demo API"
        assert data["status"] == "healthy"
    
    def test_health_check_endpoint(self):
        """Test detailed health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "portal-qa-ci-demo"
        assert data["version"] == "1.0.0"

class TestUserProfileValidation:
    """Test UserProfile Pydantic model validation."""
    
    def test_valid_user_profile_creation(self):
        """Test creating a valid user profile."""
        valid_data = {
            "user_id": 12345,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "age": 28,
            "is_active": True,
            "tags": ["developer", "python"],
            "metadata": {"location": "NYC", "timezone": "EST"}
        }
        
        user = UserProfile(**valid_data)
        assert user.user_id == 12345
        assert user.username == "john_doe"
        assert user.email == "john.doe@example.com"
        assert user.age == 28
        assert user.is_active is True
        assert user.tags == ["developer", "python"]
        assert user.metadata == {"location": "NYC", "timezone": "EST"}
    
    def test_invalid_user_id(self):
        """Test validation fails for invalid user_id."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=0,  # Invalid: must be > 0
                username="john_doe",
                email="john.doe@example.com",
                age=28
            )
    
    def test_invalid_username_length(self):
        """Test validation fails for invalid username length."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="jo",  # Invalid: too short
                email="john.doe@example.com",
                age=28
            )
    
    def test_invalid_username_pattern(self):
        """Test validation fails for invalid username pattern."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="john doe!",  # Invalid: contains space and special char
                email="john.doe@example.com",
                age=28
            )
    
    def test_invalid_email_format(self):
        """Test validation fails for invalid email format."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="john_doe",
                email="invalid-email",  # Invalid: not an email
                age=28
            )
    
    def test_invalid_age_range(self):
        """Test validation fails for invalid age."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="john_doe",
                email="john.doe@example.com",
                age=12  # Invalid: too young
            )
        
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="john_doe",
                email="john.doe@example.com",
                age=121  # Invalid: too old
            )
    
    def test_too_many_tags(self):
        """Test validation fails for too many tags."""
        with pytest.raises(ValueError):
            UserProfile(
                user_id=123,
                username="john_doe",
                email="john.doe@example.com",
                age=28,
                tags=["tag" + str(i) for i in range(11)]  # Invalid: too many tags
            )

class TestCreateUserEndpoint:
    """Test /users POST endpoint."""
    
    def test_create_user_success(self):
        """Test successful user creation."""
        user_data = {
            "user_id": 12345,
            "username": "john_doe",
            "email": "john.doe@example.com",
            "age": 28,
            "is_active": True,
            "tags": ["developer", "python"],
            "metadata": {"location": "NYC"}
        }
        
        response = client.post("/users", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "User john_doe created successfully"
        assert data["user_id"] == 12345
        assert "validation_score" in data
        assert 0.0 <= data["validation_score"] <= 1.0
    
    def test_create_user_minimal_data(self):
        """Test user creation with minimal required data."""
        user_data = {
            "user_id": 678,
            "username": "jane_doe",
            "email": "jane@example.com",
            "age": 25
        }
        
        response = client.post("/users", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["user_id"] == 678
    
    def test_create_user_invalid_data(self):
        """Test user creation fails with invalid data."""
        invalid_data = {
            "user_id": -1,  # Invalid
            "username": "a",  # Invalid: too short
            "email": "invalid-email",  # Invalid
            "age": 10  # Invalid: too young
        }
        
        response = client.post("/users", json=invalid_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_create_user_missing_required_fields(self):
        """Test user creation fails with missing required fields."""
        incomplete_data = {
            "username": "john_doe",
            "email": "john@example.com"
            # Missing user_id and age
        }
        
        response = client.post("/users", json=incomplete_data)
        assert response.status_code == 422
    
    def test_create_user_validation_score_calculation(self):
        """Test validation score calculation."""
        # Full data should get high score
        full_data = {
            "user_id": 123,
            "username": "excellent_user",
            "email": "user@example.com",
            "age": 30,
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"}
        }
        
        response = client.post("/users", json=full_data)
        assert response.status_code == 200
        data = response.json()
        full_score = data["validation_score"]
        
        # Minimal data should get lower score
        minimal_data = {
            "user_id": 456,
            "username": "min",
            "email": "min@test.co",
            "age": 20
        }
        
        response = client.post("/users", json=minimal_data)
        assert response.status_code == 200
        data = response.json()
        minimal_score = data["validation_score"]
        
        assert full_score > minimal_score

class TestValidateUserEndpoint:
    """Test /users/validate POST endpoint."""
    
    def test_validate_user_success(self):
        """Test successful user validation."""
        user_data = {
            "user_id": 789,
            "username": "test_user",
            "email": "test@example.com",
            "age": 35,
            "tags": ["testing"]
        }
        
        response = client.post("/users/validate", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is True
        assert "validation_score" in data
        assert "details" in data
        assert "user_data" in data
        assert data["user_data"]["username"] == "test_user"
    
    def test_validate_user_failure(self):
        """Test user validation with invalid data."""
        invalid_data = {
            "user_id": 0,  # Invalid
            "username": "",  # Invalid
            "email": "not-an-email",  # Invalid
            "age": 5  # Invalid
        }
        
        response = client.post("/users/validate", json=invalid_data)
        assert response.status_code == 200  # Still returns 200 but with validation results
        
        data = response.json()
        assert data["valid"] is False
        assert "errors" in data
        assert data["validation_score"] == 0.0
    
    def test_validate_user_details(self):
        """Test validation details are comprehensive."""
        user_data = {
            "user_id": 999,
            "username": "detail_user",
            "email": "detail@example.com",
            "age": 40,
            "tags": ["tag1", "tag2", "tag3"],
            "metadata": {"field1": "value1", "field2": "value2"}
        }
        
        response = client.post("/users/validate", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        details = data["details"]
        
        assert "user_id" in details
        assert "username" in details
        assert "email" in details
        assert "age" in details
        assert "tags" in details
        assert "metadata" in details
        
        assert details["tags"] == "Valid (3 tags)"
        assert details["metadata"] == "Valid (2 fields)"

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload."""
        response = client.post(
            "/users",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_empty_payload(self):
        """Test handling of empty payload."""
        response = client.post("/users", json={})
        assert response.status_code == 422
    
    def test_extra_fields_ignored(self):
        """Test that extra fields are handled gracefully."""
        user_data = {
            "user_id": 555,
            "username": "extra_user",
            "email": "extra@example.com",
            "age": 25,
            "extra_field": "should be ignored"
        }
        
        response = client.post("/users", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True

class TestApiResponseFormat:
    """Test API response format consistency."""
    
    def test_create_user_response_format(self):
        """Test create user response has expected format."""
        user_data = {
            "user_id": 111,
            "username": "format_test",
            "email": "format@example.com",
            "age": 30
        }
        
        response = client.post("/users", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["success", "message", "user_id", "validation_score"]
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)
        assert isinstance(data["user_id"], int)
        assert isinstance(data["validation_score"], float)
    
    def test_validation_response_format(self):
        """Test validation response has expected format."""
        user_data = {
            "user_id": 222,
            "username": "validation_test",
            "email": "validation@example.com",
            "age": 25
        }
        
        response = client.post("/users/validate", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        required_fields = ["valid", "validation_score", "details", "user_data"]
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["valid"], bool)
        assert isinstance(data["validation_score"], float)
        assert isinstance(data["details"], dict)
        assert isinstance(data["user_data"], dict)