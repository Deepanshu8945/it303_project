import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

config = dotenv_values(".env")
database = (
    os.environ.get("TEST_DATABASE_URL")
    or config.get("DATABASE_URL", "").rsplit("/", 1)[0] + "/file_converter_test"
)
if not make_url(database).database.endswith("_test"):
    raise RuntimeError("Tests require a dedicated database whose name ends in _test.")
os.environ["DATABASE_URL"] = database
os.environ["STORAGE_DIR"] = str(Path(".runtime/test-storage").resolve())
os.environ["MAIL_MODE"] = "local"

from fastapi.testclient import TestClient

from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app, requests
from backend.app.models import SystemConfig


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(SystemConfig(id=1, max_upload_mb=1, nominal_threshold=20, retention_hours=24))
        db.commit()
    requests.clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def account(client):
    import secrets

    from backend.app.models import User
    from backend.app.security import hash_password

    password = "Test-" + secrets.token_hex(8) + "A1"
    with SessionLocal() as db:
        user = User(
            name="Test Researcher",
            email="researcher@example.com",
            password_hash=hash_password(password),
            verified=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher@example.com", "password": password},
    )
    assert response.status_code == 200
    return {
        "id": user_id,
        "password": password,
        "tokens": response.json(),
        "headers": {"Authorization": "Bearer " + response.json()["access_token"]},
    }
