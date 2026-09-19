from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'


def test_ingest_and_chat_fallback():
    with TestClient(app) as client:
        ingested = client.post('/ingest', json={'title': 'Python', 'content': 'Python is a readable programming language.'})
        assert ingested.status_code == 200
        response = client.post('/chat', json={'message': 'What is Python?'})
        assert response.status_code == 200
        assert response.json()['sources'][0]['title'] == 'Python'
