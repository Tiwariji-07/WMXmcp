"""Tests for the API client."""
import pytest
import httpx
import respx
from wavemaker_wmx_mcp.api_client import APIClient

@pytest.fixture
def mock_api():
    """Fixture for mocking API responses."""
    with respx.mock as mock:
        yield mock

@pytest.mark.asyncio
async def test_api_client_get(mock_api):
    """Test GET request with API client."""
    test_url = "https://api.example.com/test"
    mock_api.get(test_url).mock(return_value=httpx.Response(200, json={"status": "ok"}))
    
    async with APIClient("https://api.example.com") as client:
        response = await client.request("GET", "/test")
        
    assert response == {"status": "ok"}

@pytest.mark.asyncio
async def test_api_client_with_auth(mock_api):
    """Test API client with authentication."""
    test_url = "https://api.example.com/secure"
    mock_api.get(test_url).mock(return_value=httpx.Response(200, json={"authenticated": True}))
    
    async with APIClient("https://api.example.com", "test-token") as client:
        response = await client.request("GET", "/secure")
        
    assert response == {"authenticated": True}
