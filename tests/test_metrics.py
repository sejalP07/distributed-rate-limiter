from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_is_available():
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200

    body = response.text

    assert "gateway_requests_total" in body
    assert "gateway_rate_limit_rejections_total" in body
    assert "gateway_auth_failures_total" in body
    assert "gateway_dependency_errors_total" in body
    assert "gateway_request_latency_seconds" in body