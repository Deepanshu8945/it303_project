import secrets
from datetime import datetime, timezone

from sqlalchemy import select, text

from backend.app.database import SessionLocal
from backend.app.models import LoginActivity, User
from backend.app.security import hash_password

API = "/api/v1/auth"


def test_existing_database_update_is_private_and_preserves_accounts(client, account, monkeypatch):
    from backend import manage
    from backend.app.config import Settings
    from backend.app.database import engine

    with engine.begin() as connection:
        LoginActivity.__table__.drop(connection)
    monkeypatch.setattr(manage, "settings", lambda: Settings(environment="local"))
    manage.init()
    manage.init()
    with SessionLocal() as db:
        assert db.get(User, account["id"]) is not None
        assert db.scalar(text("SELECT relrowsecurity FROM pg_class WHERE relname='login_activity'"))
    response = client.post(
        API + "/login", json={"email": "researcher@example.com", "password": account["password"]}
    )
    assert response.status_code == 200
    assert (
        client.get(API + "/login-details", headers=account["headers"]).json()["latest"] is not None
    )


def test_first_login_details_and_authentication(client, account):
    assert client.get(API + "/login-details").status_code == 401
    result = client.get(API + "/login-details", headers=account["headers"])
    assert result.status_code == 200
    body = result.json()
    assert body["previous"] is None
    assert body["latest"]["ip_address"] == "testclient"
    assert body["latest"]["user_agent"] == "testclient"
    stamp = datetime.fromisoformat(body["latest"]["logged_in_at"])
    assert stamp.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - stamp).total_seconds()) < 30


def test_successful_login_rotates_previous_but_refresh_and_failure_do_not(client, account):
    first = client.get(API + "/login-details", headers=account["headers"]).json()
    client.post(
        API + "/login",
        json={"email": "researcher@example.com", "password": "incorrect"},
    )
    refreshed = client.post(API + "/refresh", json={"token": account["tokens"]["refresh_token"]})
    assert refreshed.status_code == 200
    assert client.get(API + "/login-details", headers=account["headers"]).json() == first
    response = client.post(
        API + "/login",
        json={"email": "researcher@example.com", "password": account["password"]},
        headers={"user-agent": "Second browser", "x-forwarded-for": "203.0.113.90"},
    )
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    details = client.get(API + "/login-details", headers=headers).json()
    assert details["previous"] == first["latest"]
    assert details["latest"]["user_agent"] == "Second browser"
    assert details["latest"]["ip_address"] == "testclient"  # spoofed header is ignored
    assert details["latest"]["logged_in_at"] >= first["latest"]["logged_in_at"]
    assert client.post(API + "/logout", headers=headers).status_code == 200
    assert client.get(API + "/login-details", headers=headers).status_code == 401
    # The original session still sees persisted details after the second session logs out.
    assert client.get(API + "/login-details", headers=account["headers"]).json() == details


def test_details_are_scoped_to_authenticated_user_and_cascade_on_delete(client, account):
    password = "Other-" + secrets.token_hex(8) + "A1"
    with SessionLocal() as db:
        user = User(
            name="Other",
            email="other@example.com",
            verified=True,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        other_id = user.id
    response = client.post(
        API + "/login",
        json={"email": "other@example.com", "password": password},
        headers={"user-agent": "Other user browser"},
    )
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    details = client.get(
        API + "/login-details", headers=headers, params={"user_id": account["id"]}
    ).json()
    assert details["latest"]["user_agent"] == "Other user browser"
    assert details["previous"] is None
    assert (
        client.get(API + "/login-details", headers=account["headers"]).json()["latest"][
            "user_agent"
        ]
        == "testclient"
    )
    deleted = client.request(
        "DELETE", "/api/v1/profile", headers=headers, json={"current_password": password}
    )
    assert deleted.status_code == 200
    with SessionLocal() as db:
        assert db.get(LoginActivity, other_id) is None
        assert db.get(LoginActivity, account["id"]) is not None


def test_existing_session_without_record_returns_empty_state(client, account):
    with SessionLocal() as db:
        db.delete(db.get(LoginActivity, account["id"]))
        db.commit()
    assert client.get(API + "/login-details", headers=account["headers"]).json() == {
        "latest": None,
        "previous": None,
    }


def test_unavailable_and_long_browser_metadata(client, account):
    for agent in ["", "Browser " * 100]:
        response = client.post(
            API + "/login",
            json={"email": "researcher@example.com", "password": account["password"]},
            headers={"user-agent": agent},
        )
        assert response.status_code == 200
        details = client.get(API + "/login-details", headers=account["headers"]).json()
        assert details["latest"]["user_agent"] == (agent[:512] or None)
    with SessionLocal() as db:
        assert len(db.scalars(select(LoginActivity)).all()) == 1


def test_unverified_and_suspended_users_do_not_record_logins(client):
    password = "Blocked-Test123"
    with SessionLocal() as db:
        db.add(
            User(name="Blocked", email="blocked@example.com", password_hash=hash_password(password))
        )
        db.commit()
    for suspended in [False, True]:
        if suspended:
            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == "blocked@example.com"))
                user.verified, user.active = True, False
                db.commit()
        response = client.post(
            API + "/login", json={"email": "blocked@example.com", "password": password}
        )
        assert response.status_code == 403
        with SessionLocal() as db:
            assert list(db.scalars(select(LoginActivity))) == []
