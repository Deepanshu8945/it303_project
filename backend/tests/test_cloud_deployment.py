import json
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app import cloud_storage
from backend.app.config import Settings, settings
from backend.app.database import SessionLocal
from backend.app.frontend import serve_frontend
from backend.app.models import Conversion, Event, now
from backend.app.storage import cleanup, file_path


@pytest.fixture
def cloud(monkeypatch):
    config = settings()
    monkeypatch.setattr(config, "storage_backend", "supabase")
    monkeypatch.setattr(config, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(config, "supabase_service_role_key", "server-only-test-key")
    objects = {}

    def handler(request):
        assert request.headers["authorization"] == "Bearer server-only-test-key"
        assert request.headers["apikey"] == "server-only-test-key"
        path = request.url.path.removeprefix("/storage/v1/")
        bucket = "converter-files"
        if path == "bucket/" + bucket:
            return httpx.Response(200, json={"public": False})
        if path == "object/list/" + bucket:
            options = json.loads(request.content)
            items = [{"name": name, "created_at": now().isoformat()} for name in sorted(objects)]
            return httpx.Response(
                200, json=items[options["offset"] : options["offset"] + options["limit"]]
            )
        if path == "object/" + bucket and request.method == "DELETE":
            for name in json.loads(request.content)["prefixes"]:
                objects.pop(name, None)
            return httpx.Response(200, json=[])
        name = path.removeprefix("object/" + bucket + "/")
        if request.method == "POST":
            objects[name] = request.content
            return httpx.Response(200, json={"Key": name})
        if name not in objects:
            return httpx.Response(404)
        return httpx.Response(200, content=objects[name] if request.method == "GET" else b"")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "request", client.request)
    yield objects
    client.close()


def test_cloud_conversion_survives_local_file_loss(client, account, cloud):
    headers = account["headers"]
    cloud_storage.validate_bucket()
    data = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("students.csv", b"name,n\nMira,93\n", "text/csv")},
    ).json()
    assert data["upload_id"] + ".input" in cloud
    result = client.post(
        "/api/v1/conversions",
        headers=headers,
        json={
            "upload_id": data["upload_id"],
            "relation": data["relation"],
            "attributes": data["attributes"],
        },
    )
    assert result.status_code == 201, result.text
    result = result.json()
    assert result["verification"]["status"] == "passed"
    assert result["id"] + ".arff" in cloud
    # No local upload/output cache: a new CloudFile instance retrieves remote bytes.
    assert file_path(result["id"], "arff").read_bytes() == cloud[result["id"] + ".arff"]
    output = client.get(f"/api/v1/conversions/{result['id']}/download", headers=headers)
    assert output.status_code == 200 and "@relation" in output.text
    assert "attachment" in output.headers["content-disposition"]
    assert "server-only-test-key" not in output.text
    assert client.get("/api/v1/history", headers=headers).json()[0]["download_available"]
    assert client.get(f"/api/v1/conversions/{result['id']}/download").status_code == 401
    client.delete("/api/v1/history/" + result["id"], headers=headers)
    assert result["id"] + ".arff" not in cloud


def test_cloud_csv_and_expiry(client, account, cloud):
    headers = account["headers"]
    data = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={
            "file": (
                "dataset.arff",
                b"@relation r\n@attribute x string\n@data\n'a,b'\n",
                "text/plain",
            ),
        },
    ).json()
    result = client.post(
        "/api/v1/conversions",
        headers=headers,
        json={
            "upload_id": data["upload_id"],
            "relation": data["relation"],
            "attributes": data["attributes"],
        },
    ).json()
    assert result["verification"]["tool"] == "Python CSV reader"
    response = client.get(f"/api/v1/conversions/{result['id']}/download", headers=headers)
    assert response.content == b'x\r\n"a,b"\r\n'
    with SessionLocal() as db:
        item = db.get(Conversion, result["id"])
        item.expires_at = now() - timedelta(seconds=1)
        db.commit()
        cleanup(db)
        assert item.status == "expired"
    assert result["id"] + ".csv" not in cloud
    assert (
        client.get(f"/api/v1/conversions/{result['id']}/download", headers=headers).status_code
        == 410
    )


def test_storage_errors_are_not_missing_objects(cloud, monkeypatch):
    def denied(*args, **kwargs):
        return httpx.Response(403, request=httpx.Request("HEAD", "https://example.supabase.co"))

    monkeypatch.setattr(httpx, "request", denied)
    with pytest.raises(httpx.HTTPStatusError):
        cloud_storage.CloudFile("file.input").exists()


def test_public_bucket_rejected(cloud, monkeypatch):
    monkeypatch.setattr(
        httpx,
        "request",
        lambda *a, **k: httpx.Response(
            200, json={"public": True}, request=httpx.Request("GET", "https://example.supabase.co")
        ),
    )
    with pytest.raises(RuntimeError, match="private"):
        cloud_storage.validate_bucket()


def test_cloud_orphan_pagination(monkeypatch):
    removed, offsets = [], []

    def request(method, path, **kwargs):
        payload = kwargs["json"]
        if method == "DELETE":
            removed.extend(payload["prefixes"])
            return SimpleNamespace(raise_for_status=lambda: None)
        offsets.append(payload["offset"])
        names = [f"orphan-{i}.input" for i in range(105)] + ["retained.input"]
        items = [
            {"name": n, "created_at": (now() - timedelta(minutes=2)).isoformat()} for n in names
        ]
        page = items[payload["offset"] : payload["offset"] + payload["limit"]]
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: page)

    monkeypatch.setattr(cloud_storage, "request", request)
    cloud_storage.remove_orphans({"retained"}, now())
    assert offsets == [0, 100] and len(removed) == 105
    assert "retained.input" not in removed


def test_brevo_delivery(client, account, monkeypatch):
    from backend.app.mail import send_link

    monkeypatch.setattr(settings(), "mail_mode", "brevo")
    monkeypatch.setattr(settings(), "brevo_api_key", "mail-test-key")
    captured = []

    def post(url, **kwargs):
        captured.append(kwargs)
        return httpx.Response(201, json={"messageId": "1"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    send_link(account["id"], "researcher@example.com", "verify", "token")
    assert captured[0]["headers"]["api-key"] == "mail-test-key"
    assert "/verify?token=token" in captured[0]["json"]["htmlContent"]
    with SessionLocal() as db:
        from sqlalchemy import select

        assert "accepted by Brevo" in db.scalar(select(Event).where(Event.kind == "email")).message


def test_frontend_routes_and_traversal(tmp_path):
    (tmp_path / "index.html").write_text("<html>converter</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app.js").write_text("console.log('ok')")
    (tmp_path / ".env").write_text("private")
    app = FastAPI()

    @app.get("/{path:path}")
    def frontend(path: str):
        return serve_frontend(tmp_path, path)

    with TestClient(app) as client:
        assert client.get("/register").text == "<html>converter</html>"
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/api/v1/missing").status_code == 404
        assert client.get("/.env").status_code == 404
    with pytest.raises(HTTPException):
        serve_frontend(tmp_path, "../.env")


def test_deployment_settings_validation():
    base = {
        "_env_file": None,
        "database_url": "postgresql+psycopg://localhost/test",
        "jwt_secret": "x" * 40,
    }
    assert Settings(**base, frontend_dist="").frontend_dist is None
    with pytest.raises(ValidationError):
        Settings(**base, storage_backend="supabase")
    with pytest.raises(ValidationError):
        Settings(**base, environment="production")
    with pytest.raises(ValidationError):
        Settings(**base, mail_mode="brevo")


def test_hosted_admin_and_table_privacy(client, monkeypatch):
    from sqlalchemy import select, text

    from backend import manage
    from backend.app.database import Base
    from backend.app.models import User
    from backend.app.security import check_password

    config = settings()
    monkeypatch.setattr(config, "environment", "production")
    monkeypatch.setattr(config, "bootstrap_admin_email", "private-admin@example.com")
    monkeypatch.setattr(config, "bootstrap_admin_password", "Private-password-123")
    manage.init()
    manage.bootstrap_admin()
    monkeypatch.setattr(config, "bootstrap_admin_password", "Changed-password-456")
    manage.bootstrap_admin()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "private-admin@example.com"))
        assert user.role == "admin" and user.verified
        assert check_password("Private-password-123", user.password_hash)
        for table in Base.metadata.sorted_tables:
            assert db.execute(
                text("SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:table)"),
                {"table": table.name},
            ).scalar()


def test_deploy_entrypoint(tmp_path, monkeypatch):
    import deploy.start as entry

    jar = tmp_path / "weka.jar"
    jar.write_bytes(b"test")
    (tmp_path / "index.html").write_text("test")
    config = SimpleNamespace(
        environment="local",
        storage_backend="local",
        weka_jar=jar,
        frontend_dist=tmp_path,
        bootstrap_admin_email="",
    )
    monkeypatch.setattr(entry, "settings", lambda: config)
    calls = []
    monkeypatch.setattr(entry.subprocess, "run", lambda args, **kw: calls.append(args))
    monkeypatch.setenv("PORT", "10000")

    class Started(Exception):
        pass

    def start(executable, args):
        calls.append(args)
        raise Started

    monkeypatch.setattr(entry.os, "execv", start)
    with pytest.raises(Started):
        entry.main()
    assert calls[0][-1] == "init-db"
    assert "10000" in calls[-1] and "0.0.0.0" in calls[-1]
    assert not any("seed" in call for call in calls)
