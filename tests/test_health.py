"""冒烟测试：应用可启动，健康检查可用。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "open-agent"
    assert "version" in body
