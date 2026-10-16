import os

os.environ.setdefault("AUTO_CREATE_TABLES", "false")

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    """健康检查接口应返回 ok。"""
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
