from datetime import timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from ..conversion.engine import (
    ParsingOptions,
    convert,
    detect,
    override,
    parse,
    summary,
)
from ..conversion.types import ConversionError
from ..database import get_db
from ..models import Conversion, Event, SystemConfig, Upload, now, uid
from ..security import current_user
from ..storage import atomic_write, file_path

router = APIRouter(tags=["Conversion workspace"])


def limits(db):
    return db.get(SystemConfig, 1)


def validation_error(db, user, error):
    db.add(
        Event(
            user_id=user.id,
            kind="validation",
            message=str(error),
            details={"errors": error.errors},
        )
    )
    db.commit()
    raise HTTPException(
        400,
        {
            "message": "Conversion stopped. Correct the following error.",
            "errors": error.errors,
        },
    )


def owned(db, model, key, user):
    record = db.get(model, key)
    if not record or record.user_id != user.id:
        raise HTTPException(404, "Record not found.")
    return record


@router.get("/limits")
def get_limits(user=Depends(current_user), db=Depends(get_db)):
    config = limits(db)
    return {
        k: getattr(config, k) for k in ["max_upload_mb", "nominal_threshold", "retention_hours"]
    }


@router.post("/uploads", status_code=201)
def upload(
    file: UploadFile = File(...),
    options: str = Form("{}"),
    user=Depends(current_user),
    db=Depends(get_db),
):
    config = limits(db)
    if file.content_type and file.content_type not in {
        "text/csv",
        "text/plain",
        "text/arff",
        "application/x-arff",
        "application/octet-stream",
        "application/vnd.ms-excel",
    }:
        raise HTTPException(400, "Upload a plain-text CSV or ARFF file.")
    content = file.file.read(config.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > config.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds the {config.max_upload_mb} MB limit.")
    filename = Path((file.filename or "dataset").replace("\\", "/")).name[:255]
    try:
        parsing = ParsingOptions.model_validate_json(options)
        parsing.relation = parsing.relation or Path(filename).stem
        source, text = detect(filename, content)
        dataset = parse(text, source, parsing, config.nominal_threshold)
    except ValidationError:
        raise HTTPException(
            400, "Invalid parsing options. Check delimiter, quote, and relation name."
        )
    except ConversionError as error:
        validation_error(db, user, error)
    record = Upload(
        id=uid(),
        user_id=user.id,
        filename=filename,
        source_format=source,
        size=len(content),
        options=parsing.model_dump(),
        expires_at=now() + timedelta(hours=config.retention_hours),
    )
    path = file_path(record.id, "input")
    atomic_write(path, content)
    try:
        db.add(record)
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {
        "upload_id": record.id,
        "source_format": source,
        "target_format": "arff" if source == "csv" else "csv",
        "filename": filename,
        "expires_at": record.expires_at,
        **summary(dataset),
    }


class AttributeInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["numeric", "nominal", "date", "string"]
    values: list[str] = Field(default_factory=list, max_length=100000)
    date_format: str | None = None


class ConvertRequest(BaseModel):
    upload_id: str = Field(max_length=36)
    attributes: list[AttributeInput] = Field(min_length=1, max_length=10000)
    relation: str = Field(min_length=1, max_length=200)


@router.post("/conversions", status_code=201)
def create_conversion(body: ConvertRequest, user=Depends(current_user), db=Depends(get_db)):
    record = owned(db, Upload, body.upload_id, user)
    path = file_path(record.id, "input")
    if record.expires_at <= now() or not path.exists():
        raise HTTPException(410, "Upload expired. Upload the dataset again.")
    try:
        options = ParsingOptions(**{**record.options, "relation": body.relation})
        dataset = parse(
            path.read_bytes().decode("utf-8-sig"),
            record.source_format,
            options,
            limits(db).nominal_threshold,
        )
        dataset.relation = body.relation
        dataset = override(dataset, [a.model_dump() for a in body.attributes])
        output, preview = convert(dataset, record.source_format, options)
    except ValidationError:
        raise HTTPException(400, "Invalid relation name.")
    except ConversionError as error:
        validation_error(db, user, error)
    target = "arff" if record.source_format == "csv" else "csv"
    item = Conversion(
        id=uid(),
        user_id=user.id,
        filename=record.filename,
        source_format=record.source_format,
        target_format=target,
        size=record.size,
        instance_count=len(dataset.rows),
        attribute_count=len(dataset.attributes),
        expires_at=now() + timedelta(hours=limits(db).retention_hours),
    )
    output_path = file_path(item.id, target)
    atomic_write(output_path, output.encode("utf-8"))
    try:
        db.add(item)
        db.commit()
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return {
        "id": item.id,
        "preview": preview,
        "target_format": target,
        "download_name": Path(record.filename).stem + "." + target,
        **summary(dataset),
    }


@router.get("/conversions/{key}/download")
def download(key: str, user=Depends(current_user), db=Depends(get_db)):
    item = owned(db, Conversion, key, user)
    path = file_path(item.id, item.target_format)
    if item.expires_at <= now() or not path.exists():
        raise HTTPException(410, "This download has expired. Convert the original file again.")
    return FileResponse(
        path,
        filename=Path(item.filename).stem + "." + item.target_format,
        media_type="text/csv" if item.target_format == "csv" else "text/plain",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def history_view(item):
    return {
        **{
            k: getattr(item, k)
            for k in [
                "id",
                "filename",
                "source_format",
                "target_format",
                "size",
                "instance_count",
                "attribute_count",
                "status",
                "created_at",
                "expires_at",
            ]
        },
        "download_available": item.expires_at > now()
        and file_path(item.id, item.target_format).exists(),
    }


@router.get("/history")
def history(q: str = "", source: str = "", user=Depends(current_user), db=Depends(get_db)):
    query = select(Conversion).where(Conversion.user_id == user.id)
    if q:
        query = query.where(
            Conversion.filename.ilike(
                "%" + q.replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"
            )
        )
    if source:
        query = query.where(Conversion.source_format == source)
    return [
        history_view(item)
        for item in db.scalars(query.order_by(Conversion.created_at.desc()).limit(500))
    ]


@router.delete("/history/{key}")
def delete_history(key: str, user=Depends(current_user), db=Depends(get_db)):
    item = owned(db, Conversion, key, user)
    file_path(item.id, item.target_format).unlink(missing_ok=True)
    db.delete(item)
    db.commit()
    return {"message": "History entry and its output deleted."}


@router.get("/dashboard")
def dashboard(user=Depends(current_user), db=Depends(get_db)):
    from sqlalchemy import func

    condition = Conversion.user_id == user.id
    total = db.scalar(select(func.count()).select_from(Conversion).where(condition))
    rows = db.scalar(select(func.coalesce(func.sum(Conversion.instance_count), 0)).where(condition))
    active = db.scalar(
        select(func.count()).select_from(Conversion).where(condition, Conversion.expires_at > now())
    )
    recent = db.scalars(
        select(Conversion).where(condition).order_by(Conversion.created_at.desc()).limit(5)
    )
    return {
        "total": total,
        "instances": rows,
        "available": active,
        "recent": [history_view(x) for x in recent],
    }
