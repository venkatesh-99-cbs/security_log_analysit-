from app.main import app

client = app.test_client()

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Security Log Analysis Assistant API"}

def test_health_check():
    response = client.get("/api/v1/health/status")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"
