"""Tests for the FastAPI server."""
import pytest
from fastapi.testclient import TestClient
from wavemaker_wmx_mcp.server import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

# Add more test cases as needed
