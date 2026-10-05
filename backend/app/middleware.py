from starlette.exceptions import HTTPException


class BodyLimitMiddleware:
    def __init__(self, app, maximum=52 * 1024 * 1024):
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > self.maximum:
                raise HTTPException(413, "Request exceeds the upload limit.")
            return message

        await self.app(scope, bounded_receive, send)
