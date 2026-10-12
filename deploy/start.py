"""Render/Docker entrypoint. Provision once, then replace this process with uvicorn."""

import os
import subprocess
import sys

from backend.app.cloud_storage import validate_bucket
from backend.app.config import settings
from backend.app.validation_helpers import validate_admin_credentials


def main():
    config = settings()
    if config.environment == "production":
        validate_admin_credentials(config)
    if config.storage_backend == "supabase":
        validate_bucket()
    if not config.weka_jar.is_file():
        raise RuntimeError("WEKA JAR is missing from the deployment image.")
    if not config.frontend_dist or not (config.frontend_dist / "index.html").is_file():
        raise RuntimeError("Built frontend is missing from the deployment image.")
    subprocess.run([sys.executable, "-m", "backend.manage", "init-db"], check=True)
    if config.bootstrap_admin_email:
        subprocess.run([sys.executable, "-m", "backend.manage", "bootstrap-admin"], check=True)
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            os.environ.get("PORT", "8000"),
            "--workers",
            "1",
            "--proxy-headers",
            "--forwarded-allow-ips",
            "*",
        ],
    )


if __name__ == "__main__":
    main()
