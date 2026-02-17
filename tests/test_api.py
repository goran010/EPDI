import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.api.main import app
from src.database.database import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Setup test database"""
    init_db()
    yield
    # Cleanup after tests


def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "FIDIT AI Assistant API" in response.json()["message"]


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data


def test_get_statistics():
    """Test statistics endpoint"""
    response = client.get("/api/statistics")
    assert response.status_code == 200
    data = response.json()
    assert "total_natjecaji" in data
    assert "active_natjecaji" in data
    assert "total_izdavatelji" in data


def test_get_natjecaji():
    """Test get all natjecaji endpoint"""
    response = client.get("/api/natjecaji")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_natjecaji_with_pagination():
    """Test natjecaji with pagination"""
    response = client.get("/api/natjecaji?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5


def test_get_active_natjecaji():
    """Test get active natjecaji only"""
    response = client.get("/api/natjecaji?active_only=true")
    assert response.status_code == 200
    data = response.json()
    for natjecaj in data:
        assert natjecaj["status"] == "active"


def test_search_natjecaji():
    """Test search functionality"""
    response = client.get("/api/search?q=inovacije")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_expiring_soon():
    """Test expiring soon endpoint"""
    response = client.get("/api/natjecaji/expiring/soon?days=30")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_natjecaj_not_found():
    """Test get natjecaj with invalid ID"""
    response = client.get("/api/natjecaji/99999")
    assert response.status_code == 404


def test_get_izdavatelji():
    """Test get all izdavatelji"""
    response = client.get("/api/izdavatelji")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# Run tests with: pytest tests/test_api.py -v
