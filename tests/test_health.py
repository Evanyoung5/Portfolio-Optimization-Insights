def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_versioned_health_check(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["service"] == "portfolio-optimization-api"
