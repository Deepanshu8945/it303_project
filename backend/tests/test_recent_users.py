from datetime import timedelta

from backend.app.database import SessionLocal
from backend.app.models import LoginActivity, User, now
from backend.app.security import hash_password

API = "/api/v1/auth"


def test_public_recent_users_empty(client):
    response = client.get(API + "/recent-users")
    assert response.status_code == 200
    assert response.json() == {"names": []}


def test_recent_users_returns_only_names_and_does_not_duplicate_logins(client, account):
    assert client.get(API + "/recent-users").json() == {"names": ["Test Researcher"]}
    for _ in range(2):
        assert (
            client.post(
                API + "/login",
                json={"email": "researcher@example.com", "password": account["password"]},
            ).status_code
            == 200
        )
    response = client.get(API + "/recent-users")
    assert response.json() == {"names": ["Test Researcher"]}
    assert "email" not in response.text
    assert "logged_in_at" not in response.text
    assert "ip_address" not in response.text
    assert "user_agent" not in response.text


def test_recent_users_sorted_bounded_and_excludes_unavailable_accounts(client):
    stamp = now()
    password_hash = hash_password("Recent-User123")
    with SessionLocal() as db:
        for index in range(10):
            user = User(
                name=f"User {index}",
                email=f"recent{index}@example.com",
                verified=True,
                password_hash=password_hash,
            )
            db.add(user)
            db.flush()
            db.add(
                LoginActivity(
                    user_id=user.id,
                    logged_in_at=stamp + timedelta(seconds=index),
                    ip_address="192.0.2.1",
                    user_agent="Private browser",
                )
            )
        for verified, active, name in [(False, True, "Unverified"), (True, False, "Suspended")]:
            user = User(
                name=name,
                email=f"{name.lower()}@example.com",
                verified=verified,
                active=active,
                password_hash=password_hash,
            )
            db.add(user)
            db.flush()
            db.add(LoginActivity(user_id=user.id, logged_in_at=stamp + timedelta(hours=1)))
        db.add(
            User(
                name="Never signed in",
                email="never@example.com",
                verified=True,
                password_hash=password_hash,
            )
        )
        db.commit()
    assert client.get(API + "/recent-users").json() == {
        "names": ["User 9", "User 8", "User 7", "User 6", "User 5"]
    }
