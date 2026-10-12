from datetime import timedelta

from sqlalchemy import delete, select

from .cloud_storage import CloudFile, remove_orphans
from .config import settings
from .models import ActionToken, Conversion, Session, Upload, now


def file_path(key, suffix):
    if settings().storage_backend == "supabase":
        return CloudFile(f"{key}.{suffix}")
    root = settings().storage_dir
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{key}.{suffix}"


def atomic_write(path, content):
    if isinstance(path, CloudFile):
        path.write_bytes(content)
        return
    partial = path.with_suffix(path.suffix + ".partial")
    try:
        partial.write_bytes(content)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def remove_user_files(db, user_id):
    for upload in db.scalars(select(Upload).where(Upload.user_id == user_id)):
        file_path(upload.id, "input").unlink(missing_ok=True)
    for conversion in db.scalars(select(Conversion).where(Conversion.user_id == user_id)):
        file_path(conversion.id, conversion.target_format).unlink(missing_ok=True)


def cleanup(db):
    for upload in db.scalars(select(Upload).where(Upload.expires_at <= now())):
        file_path(upload.id, "input").unlink(missing_ok=True)
        db.delete(upload)
    for item in db.scalars(
        select(Conversion).where(Conversion.expires_at <= now(), Conversion.status != "expired")
    ):
        file_path(item.id, item.target_format).unlink(missing_ok=True)
        item.status = "expired"
    db.execute(delete(ActionToken).where(ActionToken.expires_at < now()))
    db.execute(
        delete(Session).where(Session.last_seen < now() - timedelta(hours=settings().session_hours))
    )
    db.commit()
    root = settings().storage_dir
    if settings().storage_backend == "supabase":
        valid_ids = set(db.scalars(select(Upload.id))) | set(db.scalars(select(Conversion.id)))
        remove_orphans(valid_ids, now())
    if root.exists():
        valid_ids = set(db.scalars(select(Upload.id))) | set(db.scalars(select(Conversion.id)))
        for path in root.iterdir():
            # Leave in-flight writes alone; reap abandoned files after one minute.
            if (
                path.is_file()
                and path.name.split(".")[0] not in valid_ids
                and now().timestamp() - path.stat().st_mtime > 60
            ):
                path.unlink(missing_ok=True)
    outbox = settings().storage_dir.parent / "outbox"
    if outbox.exists():
        for path in outbox.glob("*.eml"):
            if now().timestamp() - path.stat().st_mtime > 3600:
                path.unlink(missing_ok=True)
