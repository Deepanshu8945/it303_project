import asyncio
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .database import SessionLocal
from .middleware import BodyLimitMiddleware
from .routes import admin, auth, conversions, profile
from .storage import cleanup


def run_cleanup():
    with SessionLocal() as db:
        cleanup(db)


async def maintenance():
    while True:
        try:
            await asyncio.to_thread(run_cleanup)
        except Exception:
            logging.exception("Retention cleanup failed")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(maintenance())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="File Converter System", version="1.0.0", lifespan=lifespan)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings().frontend_origin],
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
requests = defaultdict(deque)


@app.middleware("http")
async def safety(request: Request, call_next):
    current = time.monotonic()
    key = (
        request.client.host if request.client else "local",
        "auth" if "/auth/" in request.url.path else "api",
    )
    queue = requests[key]
    while queue and queue[0] <= current - 60:
        queue.popleft()
    limit = 40 if key[1] == "auth" else 240
    if len(queue) >= limit:
        return JSONResponse(
            {"detail": "Too many requests. Please wait a minute."},
            429,
            headers={"Retry-After": "60"},
        )
    queue.append(current)
    if len(requests) > 10000:
        for stale in list(requests):
            if not requests[stale] or requests[stale][-1] < current - 60:
                del requests[stale]
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > 52 * 1024 * 1024):
        return JSONResponse({"detail": "Request exceeds the upload limit."}, 413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(
        {
            "detail": "Check the required fields and input formats.",
            "errors": [
                {"field": ".".join(map(str, e["loc"][1:])), "message": e["msg"]}
                for e in exc.errors()
            ],
        },
        400,
    )


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    logging.error("Request failed", exc_info=exc)
    return JSONResponse({"detail": "The request could not be completed. Please try again."}, 500)


@app.get("/api/v1/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


for router in (auth.router, profile.router, conversions.router, admin.router):
    app.include_router(router, prefix="/api/v1")
