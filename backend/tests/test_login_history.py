from datetime import timedelta

from sqlalchemy import delete, func, select, text

from backend.app.database import SessionLocal
from backend.app.models import LoginActivity, LoginHistory, User, now
from backend.app.security import hash_password

API = "/api/v1/auth"


def test_history_retains_multiple_logins_after_logout_and_excludes_failed_attempts(client, account):
    assert client.get(API + "/login-history").status_code == 401
    for _ in range(3):
        response = client.post(
            API + "/login",
            json={"email": "researcher@example.com", "password": account["password"]},
        )
        assert response.status_code == 200
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        assert client.post(API + "/logout", headers=headers).status_code == 200
    items = client.get(API + "/login-history", headers=account["headers"]).json()["items"]
    assert len(items) == 4
    assert [item["logged_in_at"] for item in items] == sorted(
        [item["logged_in_at"] for item in items], reverse=True
    )
    assert all(item["user_agent"] == "testclient" for item in items)
    assert client.get(API + "/recent-users").json() == {"names": ["Test Researcher"]}
    client.post(API + "/login", json={"email": "researcher@example.com", "password": "incorrect"})
    assert (
        client.post(
            API + "/refresh", json={"token": account["tokens"]["refresh_token"]}
        ).status_code
        == 200
    )
    assert client.get(API + "/login-history", headers=account["headers"]).json()["items"] == items


def test_history_is_bounded_to_100_successful_logins(client, account):
    with SessionLocal() as db:
        for index in range(105):
            db.add(
                LoginHistory(
                    user_id=account["id"], logged_in_at=now() - timedelta(days=1, seconds=index)
                )
            )
        db.commit()
    response = client.post(
        API + "/login", json={"email": "researcher@example.com", "password": account["password"]}
    )
    assert response.status_code == 200
    items = client.get(API + "/login-history", headers=account["headers"]).json()["items"]
    assert len(items) == 100
    assert items[0]["user_agent"] == "testclient"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(LoginHistory)) == 100


def test_history_scoped_to_user_and_removed_with_account(client, account):
    password = "Other-History123"
    with SessionLocal() as db:
        user = User(
            name="Other History",
            email="other-history@example.com",
            verified=True,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        other_id = user.id
    response = client.post(
        API + "/login",
        json={"email": "other-history@example.com", "password": password},
        headers={"user-agent": "Other device"},
    )
    assert response.status_code == 200
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    items = client.get(
        API + "/login-history", headers=headers, params={"user_id": account["id"]}
    ).json()["items"]
    assert len(items) == 1 and items[0]["user_agent"] == "Other device"
    assert (
        client.request(
            "DELETE", "/api/v1/profile", headers=headers, json={"current_password": password}
        ).status_code
        == 200
    )
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(LoginHistory)
                .where(LoginHistory.user_id == other_id)
            )
            == 0
        )
    assert len(client.get(API + "/login-history", headers=account["headers"]).json()["items"]) == 1


def test_upgrade_backfills_available_logins_once_and_keeps_history_private(
    client, account, monkeypatch
):
    from backend import manage
    from backend.app.config import Settings

    with SessionLocal() as db:
        activity = db.get(LoginActivity, account["id"])
        activity.previous_logged_in_at = activity.logged_in_at - timedelta(days=1)
        activity.previous_ip_address = "192.0.2.2"
        activity.previous_user_agent = "Older browser"
        db.execute(delete(LoginHistory).where(LoginHistory.user_id == account["id"]))
        db.commit()
    monkeypatch.setattr(manage, "settings", lambda: Settings(environment="local"))
    manage.init()
    manage.init()
    items = client.get(API + "/login-history", headers=account["headers"]).json()["items"]
    assert len(items) == 2
    assert items[1]["user_agent"] == "Older browser"
    with SessionLocal() as db:
        assert db.scalar(text("SELECT relrowsecurity FROM pg_class WHERE relname='login_history'"))
