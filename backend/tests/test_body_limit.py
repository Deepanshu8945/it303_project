import pytest
from starlette.exceptions import HTTPException

from backend.app.middleware import BodyLimitMiddleware


def test_streaming_body_limit():
    import asyncio

    async def application(scope, receive, send):
        await receive()
        await receive()

    async def receive():
        return {"type": "http.request", "body": b"123456", "more_body": True}

    async def send(message):
        pass

    with pytest.raises(HTTPException) as error:
        asyncio.run(BodyLimitMiddleware(application, maximum=10)({"type": "http"}, receive, send))
    assert error.value.status_code == 413
