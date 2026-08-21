from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.main import create_app


def test_health_reports_foundation_components_ok() -> None:
    app = create_app(Settings(service_check_mode="stub"))
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Correlation-ID": "test-correlation"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-correlation"
    assert response.json() == {
        "status": "ok",
        "db": "ok",
        "redis": "ok",
        "s3": "ok",
        "textract": "ok",
        "version": "0.1.0",
        "aws_region": "ap-south-1",
        "deployment": "local-compose",
    }
