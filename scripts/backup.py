import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
url = make_url(dotenv_values(root / ".env")["DATABASE_URL"])
directory = root / ".runtime" / "backups"
directory.mkdir(parents=True, exist_ok=True)
destination = directory / (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + ".dump")
environment = {**os.environ, "PGPASSWORD": url.password or ""}
binary = shutil.which("pg_dump")
if not binary:
    raise SystemExit("Add PostgreSQL bin to PATH.")
subprocess.run(
    [
        binary,
        "-h",
        url.host,
        "-p",
        str(url.port or 5432),
        "-U",
        url.username,
        "-d",
        url.database,
        "-Fc",
        "-f",
        str(destination),
    ],
    env=environment,
    check=True,
)
print(f"Backup created: {destination}")
