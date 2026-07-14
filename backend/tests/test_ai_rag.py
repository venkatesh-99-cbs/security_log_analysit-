import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


client = app.test_client()


def test_add_custom_knowledge():
    response = client.post(
        "/api/v1/ai/rag/add",
        json={
            "title": "Test Knowledge",
            "content": "This is a test snippet for the RAG knowledge base.",
            "source": "Unit Test",
            "category": "testing",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ingested"] == 1
    assert data["total"] >= 1


def test_upload_custom_knowledge_file():
    data = {
        "file": (BytesIO(b"This is a file-based knowledge snippet for testing."), "knowledge.txt"),
        "title": "File Knowledge",
        "source": "Unit Test",
        "category": "testing",
    }

    response = client.post(
        "/api/v1/ai/rag/upload",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["ingested"] == 1
    assert body["total"] >= 1
