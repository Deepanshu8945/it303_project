import argparse
import os
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert

from .app.config import settings
from .app.database import Base, SessionLocal, engine
from .app.models import Conversion, Event, LoginActivity, LoginHistory, SystemConfig, User, now, uid
from .app.security import hash_password
from .app.storage import atomic_write, cleanup, file_path


def init():
    Base.metadata.create_all(engine)
    # Login metadata stays private even when local development uses a hosted database.
    # The backend's database owner connection still works with RLS enabled.
    private_tables = (
        Base.metadata.sorted_tables
        if settings().environment == "production"
        else [LoginActivity.__table__, LoginHistory.__table__]
    )
    with engine.begin() as connection:
        for table in private_tables:
            connection.exec_driver_sql(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY')
    with SessionLocal() as db:
        # Preserve the two login records available from the previous version.
        # Deterministic IDs make concurrent/repeated upgrades safe.
        activities = db.scalars(
            select(LoginActivity).where(
                ~exists().where(LoginHistory.user_id == LoginActivity.user_id)
            )
        )
        for activity in activities:
            for prefix in ("previous_", ""):
                timestamp = getattr(activity, prefix + "logged_in_at")
                if timestamp is not None:
                    db.execute(
                        insert(LoginHistory)
                        .values(
                            id=str(
                                uuid5(
                                    NAMESPACE_URL,
                                    f"login:{activity.user_id}:{timestamp.isoformat()}",
                                )
                            ),
                            user_id=activity.user_id,
                            logged_in_at=timestamp,
                            ip_address=getattr(activity, prefix + "ip_address"),
                            user_agent=getattr(activity, prefix + "user_agent"),
                        )
                        .on_conflict_do_nothing(index_elements=["id"])
                    )
        if not db.get(SystemConfig, 1):
            config = settings()
            db.add(
                SystemConfig(
                    id=1,
                    max_upload_mb=config.max_upload_mb,
                    nominal_threshold=config.nominal_threshold,
                    retention_hours=config.retention_hours,
                )
            )
        db.commit()
    print("Database schema initialized.")


def seed():
    from dotenv import load_dotenv

    load_dotenv()
    passwords = [
        os.environ.get("DEMO_USER_PASSWORD"),
        os.environ.get("DEMO_ADMIN_PASSWORD"),
    ]
    if not all(passwords):
        raise SystemExit("Set DEMO_USER_PASSWORD and DEMO_ADMIN_PASSWORD in .env first.")
    with SessionLocal() as db:
        for email, name, role, password in zip(
            ["student@example.com", "admin@example.com"],
            ["Mira Desai", "Lab Administrator"],
            ["user", "admin"],
            passwords,
        ):
            if not db.scalar(select(User).where(User.email == email)):
                db.add(
                    User(
                        name=name,
                        email=email,
                        role=role,
                        password_hash=hash_password(password),
                        verified=True,
                    )
                )
        db.commit()
        user = db.scalar(select(User).where(User.email == "student@example.com"))
        if not db.scalar(select(Conversion).where(Conversion.user_id == user.id)):
            from .app.conversion.engine import ParsingOptions, convert, parse
            from .app.conversion.verification import verify_output

            for filename in ["students.csv", "weather.arff"]:
                content = Path("samples", filename).read_text(encoding="utf-8")
                source = filename.split(".")[-1]
                options = ParsingOptions(relation=filename.split(".")[0])
                data = parse(content, source, options, 20)
                output, _ = convert(data, source, options)
                target = "arff" if source == "csv" else "csv"
                config = settings()
                verify_output(
                    data,
                    output,
                    target,
                    java=config.java_executable,
                    jar=config.weka_jar,
                    timeout=config.verification_timeout_seconds,
                )
                item = Conversion(
                    id=uid(),
                    user_id=user.id,
                    filename=filename,
                    source_format=source,
                    target_format=target,
                    size=len(content.encode()),
                    instance_count=len(data.rows),
                    attribute_count=len(data.attributes),
                    expires_at=now() + timedelta(hours=24),
                )
                atomic_write(file_path(item.id, target), output.encode())
                db.add(item)
            db.add(
                Event(
                    user_id=user.id,
                    kind="validation",
                    message="Demo: inconsistent field count rejected",
                    details={
                        "errors": [
                            {
                                "line": 3,
                                "severity": "fatal",
                                "message": "Expected 3 fields, found 2.",
                            }
                        ]
                    },
                )
            )
            db.commit()
    print("Demo accounts and sample conversion history are ready.")


def bootstrap_admin():
    """Create a private hosted administrator once; never overwrite existing passwords."""
    from .app.validation_helpers import validate_admin_credentials

    config = settings()
    email, password = validate_admin_credentials(config)
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            if existing.role != "admin":
                raise RuntimeError("Bootstrap email belongs to a non-administrator account.")
            return
        db.add(
            User(
                name="Project Administrator",
                email=email,
                password_hash=hash_password(password),
                role="admin",
                verified=True,
            )
        )
        db.commit()
    print("Hosted administrator created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "seed", "cleanup", "bootstrap-admin"])
    command = parser.parse_args().command
    if command == "init-db":
        init()
    elif command == "seed":
        seed()
    elif command == "bootstrap-admin":
        bootstrap_admin()
    else:
        with SessionLocal() as db:
            cleanup(db)
