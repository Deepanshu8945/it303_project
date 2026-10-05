import argparse
import os
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from .app.config import settings
from .app.database import Base, SessionLocal, engine
from .app.models import Conversion, Event, SystemConfig, User, now, uid
from .app.security import hash_password
from .app.storage import atomic_write, cleanup, file_path


def init():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
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

            for filename in ["students.csv", "weather.arff"]:
                content = Path("samples", filename).read_text(encoding="utf-8")
                source = filename.split(".")[-1]
                options = ParsingOptions(relation=filename.split(".")[0])
                data = parse(content, source, options, 20)
                output, _ = convert(data, source, options)
                target = "arff" if source == "csv" else "csv"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init-db", "seed", "cleanup"])
    command = parser.parse_args().command
    if command == "init-db":
        init()
    elif command == "seed":
        seed()
    else:
        with SessionLocal() as db:
            cleanup(db)
