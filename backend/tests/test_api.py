import secrets
from datetime import timedelta

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import ActionToken, Conversion, Event, Session, User, now
from backend.app.security import digest, hash_password
from backend.app.storage import cleanup, file_path

API = "/api/v1"


def upload(client, headers, content=b"name,score\nMira,93\nArjun,88\n", filename="students.csv"):
    return client.post(
        API + "/uploads",
        headers=headers,
        files={"file": (filename, content, "text/csv")},
    )


def converted(client, headers):
    data = upload(client, headers).json()
    result = client.post(
        API + "/conversions",
        headers=headers,
        json={
            "upload_id": data["upload_id"],
            "relation": data["relation"],
            "attributes": data["attributes"],
        },
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_health_and_authentication(client, account):
    assert client.get(API + "/health").json()["database"] == "connected"
    assert client.get(API + "/dashboard").status_code == 401
    assert (
        client.post(
            API + "/auth/login",
            json={"email": "researcher@example.com", "password": "wrong"},
        ).status_code
        == 401
    )
    assert client.get(API + "/auth/me", headers=account["headers"]).json()["role"] == "user"
    assert client.get(API + "/admin", headers=account["headers"]).status_code == 403
    assert client.post(API + "/auth/logout", headers=account["headers"]).status_code == 200
    assert client.get(API + "/dashboard", headers=account["headers"]).status_code == 401
    assert (
        client.post(
            API + "/auth/refresh", json={"token": account["tokens"]["refresh_token"]}
        ).status_code
        == 401
    )


def test_complete_conversion_history_workflow(client, account):
    headers = account["headers"]
    result = converted(client, headers)
    assert result["instance_count"] == 2
    output = client.get(API + f"/conversions/{result['id']}/download", headers=headers)
    assert output.status_code == 200 and "@relation" in output.text
    assert client.get(API + "/dashboard", headers=headers).json()["total"] == 1
    assert len(client.get(API + "/history?q=students&source=csv", headers=headers).json()) == 1
    assert client.get(API + "/history?q=other", headers=headers).json() == []
    assert client.delete(API + "/history/" + result["id"], headers=headers).status_code == 200
    assert client.get(API + "/history", headers=headers).json() == []
    assert (
        client.get(API + f"/conversions/{result['id']}/download", headers=headers).status_code
        == 404
    )


def test_ownership_and_admin_cannot_read_dataset(client, account):
    result = converted(client, account["headers"])
    password = "Other-" + secrets.token_hex(6) + "A1"
    with SessionLocal() as db:
        db.add(
            User(
                name="Other",
                email="other@example.com",
                password_hash=hash_password(password),
                verified=True,
                role="admin",
            )
        )
        db.commit()
    login = client.post(
        API + "/auth/login", json={"email": "other@example.com", "password": password}
    ).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    assert (
        client.get(API + f"/conversions/{result['id']}/download", headers=headers).status_code
        == 404
    )
    assert client.delete(API + "/history/" + result["id"], headers=headers).status_code == 404
    assert client.get(API + "/history", headers=headers).json() == []


def test_invalid_uploads_and_schema(client, account):
    headers = account["headers"]
    for content, filename in [
        (b"a,b\n1\n", "bad.csv"),
        (b"hi", "bad.exe"),
        (b"\xff", "bad.csv"),
    ]:
        response = upload(client, headers, content, filename)
        assert response.status_code == 400
        assert response.json()["detail"]["errors"][0]["severity"] == "fatal"
    assert upload(client, headers, b"a" * (1024 * 1024 + 1)).status_code == 413
    data = upload(client, headers).json()
    data["attributes"][0]["type"] = "numeric"
    response = client.post(
        API + "/conversions",
        headers=headers,
        json={
            "upload_id": data["upload_id"],
            "relation": data["relation"],
            "attributes": data["attributes"],
        },
    )
    assert response.status_code == 400
    assert client.get(API + "/history", headers=headers).json() == []


def test_refresh_rotation_and_inactivity(client, account):
    original = account["tokens"]["refresh_token"]
    response = client.post(API + "/auth/refresh", json={"token": original})
    assert response.status_code == 200
    assert client.post(API + "/auth/refresh", json={"token": original}).status_code == 401
    with SessionLocal() as db:
        session = db.scalar(select(Session).where(Session.user_id == account["id"]))
        session.last_seen = now() - timedelta(hours=25)
        db.commit()
    assert client.get(API + "/dashboard", headers=account["headers"]).status_code == 401


def test_lockout(client, account):
    for _ in range(5):
        assert (
            client.post(
                API + "/auth/login",
                json={"email": "researcher@example.com", "password": "wrong"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            API + "/auth/login",
            json={"email": "researcher@example.com", "password": account["password"]},
        ).status_code
        == 429
    )


def test_registration_verification_reset(client):
    password = "Register-" + secrets.token_hex(6) + "A1"
    body = {"name": "New Researcher", "email": "new@example.com", "password": password}
    assert client.post(API + "/auth/register", json=body).status_code == 201
    assert client.post(API + "/auth/register", json=body).status_code == 400
    assert client.post(API + "/auth/login", json=body).status_code == 403
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == body["email"]))
        token = secrets.token_urlsafe(40)
        db.add(
            ActionToken(
                token_hash=digest(token),
                user_id=user.id,
                purpose="verify",
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
    assert client.post(API + "/auth/verify", json={"token": token}).status_code == 200
    assert client.post(API + "/auth/verify", json={"token": token}).status_code == 400
    assert client.post(API + "/auth/login", json=body).status_code == 200
    assert (
        client.post(API + "/auth/forgot-password", json={"email": body["email"]}).status_code == 200
    )
    with SessionLocal() as db:
        reset = secrets.token_urlsafe(40)
        db.add(
            ActionToken(
                token_hash=digest(reset),
                user_id=user.id,
                purpose="reset",
                expires_at=now() + timedelta(hours=1),
            )
        )
        db.commit()
        assert db.scalar(select(Event).where(Event.kind == "email"))
    new_password = "Changed-" + secrets.token_hex(6) + "A1"
    assert (
        client.post(
            API + "/auth/reset-password",
            json={"token": reset, "password": new_password},
        ).status_code
        == 200
    )
    assert client.post(API + "/auth/login", json=body).status_code == 401
    assert (
        client.post(API + "/auth/login", json={**body, "password": new_password}).status_code == 200
    )


def test_profile_change_and_delete(client, account):
    headers = account["headers"]
    converted(client, headers)
    assert (
        client.patch(
            API + "/profile",
            headers=headers,
            json={
                "name": "Updated",
                "email": "researcher@example.com",
                "current_password": account["password"],
            },
        ).status_code
        == 200
    )
    assert client.get(API + "/auth/me", headers=headers).json()["name"] == "Updated"
    assert (
        client.request(
            "DELETE",
            API + "/profile",
            headers=headers,
            json={"current_password": account["password"]},
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert db.get(User, account["id"]) is None
        assert not db.scalar(select(Conversion).where(Conversion.user_id == account["id"]))


def test_admin_config_and_suspend(client, account):
    with SessionLocal() as db:
        admin = User(
            name="Admin",
            email="admin@example.com",
            password_hash=hash_password(account["password"]),
            verified=True,
            role="admin",
        )
        db.add(admin)
        db.commit()
    login = client.post(
        API + "/auth/login",
        json={"email": "admin@example.com", "password": account["password"]},
    ).json()
    headers = {"Authorization": "Bearer " + login["access_token"]}
    assert client.get(API + "/admin", headers=headers).json()["stats"]["users"] == 2
    assert (
        client.put(
            API + "/admin/config",
            headers=headers,
            json={"max_upload_mb": 2, "nominal_threshold": 3, "retention_hours": 1},
        ).status_code
        == 200
    )
    assert (
        client.put(
            API + "/admin/config",
            headers=headers,
            json={"max_upload_mb": 999, "nominal_threshold": 3, "retention_hours": 1},
        ).status_code
        == 400
    )
    assert (
        client.patch(
            API + "/admin/users/" + account["id"],
            headers=headers,
            json={"active": False},
        ).status_code
        == 200
    )
    assert client.get(API + "/dashboard", headers=account["headers"]).status_code == 401
    assert (
        client.patch(
            API + "/admin/users/" + account["id"],
            headers=headers,
            json={"active": True},
        ).status_code
        == 200
    )
    assert client.delete(API + "/admin/users/" + account["id"], headers=headers).status_code == 200


def test_retention(client, account):
    result = converted(client, account["headers"])
    with SessionLocal() as db:
        item = db.get(Conversion, result["id"])
        item.expires_at = now() - timedelta(seconds=1)
        db.commit()
        cleanup(db)
        assert not file_path(item.id, item.target_format).exists()
    assert (
        client.get(
            API + f"/conversions/{result['id']}/download", headers=account["headers"]
        ).status_code
        == 410
    )
    assert len(client.get(API + "/history", headers=account["headers"]).json()) == 1


def test_upload_conversion_preserves_embedded_crlf(client, account):
    headers = account["headers"]
    data = upload(client, headers, b'name,notes\r\nMira,"line\r\nbreak"\r\n').json()
    result = client.post(
        API + "/conversions",
        headers=headers,
        json={
            "upload_id": data["upload_id"],
            "relation": data["relation"],
            "attributes": data["attributes"],
        },
    )
    assert result.status_code == 201
    assert result.json()["rows"][0][1] == "line\r\nbreak"


def test_oversized_body_without_content_length(client):
    response = client.post(
        API + "/auth/login",
        content=(b" " * 1024 * 1024 for _ in range(53)),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
