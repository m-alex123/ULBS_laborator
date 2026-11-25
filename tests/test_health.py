from sqlalchemy.exc import OperationalError


def test_health_returns_ok_when_database_is_reachable(client) -> None:
    test_client, _ = client
    response = test_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


def test_health_returns_503_when_database_fails(client, monkeypatch) -> None:
    test_client, _ = client
    from app.web.routers import health as health_router

    def broken_check(_db) -> bool:
        raise OperationalError("SELECT 1", {}, Exception("db down"))

    monkeypatch.setattr(health_router, "check_db_connection", broken_check)
    response = test_client.get("/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["database"] == "unreachable"
