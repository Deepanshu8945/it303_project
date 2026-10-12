"""Serve the built SPA on the same origin as the API when configured."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


def serve_frontend(root: Path, path: str):
    root = root.resolve()
    if path == "api" or path.startswith("api/"):
        raise HTTPException(404, "API route not found.")
    if any(part.startswith(".") for part in Path(path).parts):
        raise HTTPException(404, "File not found.")
    requested = (root / path).resolve()
    if not requested.is_relative_to(root):
        raise HTTPException(404, "File not found.")
    if requested.is_file():
        return FileResponse(requested)
    if path.startswith("assets/") or "." in Path(path).name:
        raise HTTPException(404, "File not found.")
    return FileResponse(root / "index.html")
