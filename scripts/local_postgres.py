"""Manage a dedicated PostgreSQL cluster inside .runtime; never touch system databases."""

import argparse
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
DATA = RUNTIME / "postgres"


def command(name):
    found = shutil.which(name)
    if found:
        return found
    matches = sorted(Path("C:/Program Files/PostgreSQL").glob(f"*/bin/{name}.exe"), reverse=True)
    if matches:
        return str(matches[0])
    raise SystemExit("Install PostgreSQL and put its bin directory on PATH.")


def run(name, *args, **kwargs):
    return subprocess.run([command(name), *map(str, args)], check=True, **kwargs)


def start():
    RUNTIME.mkdir(exist_ok=True)
    env_path = ROOT / ".env"
    if not DATA.exists():
        if env_path.exists():
            raise SystemExit(
                "An .env already exists. Configure your existing database or move .env before local setup."
            )
        password = secrets.token_urlsafe(24)
        password_file = RUNTIME / "pg-init-password"
        password_file.write_text(password, encoding="utf-8")
        try:
            run(
                "initdb",
                "-D",
                DATA,
                "-U",
                "converter",
                "--pwfile",
                password_file,
                "--auth=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            )
        finally:
            password_file.unlink(missing_ok=True)
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        env = env.replace(
            "postgresql+psycopg://converter:CHANGE_ME@localhost:5432/file_converter",
            f"postgresql+psycopg://converter:{password}@127.0.0.1:55432/file_converter",
        )
        env = env.replace(
            "REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS",
            secrets.token_urlsafe(48),
        )
        user_password, admin_password = (
            "Student-" + secrets.token_hex(5) + "A1",
            "Admin-" + secrets.token_hex(5) + "A1",
        )
        env = env.replace("DEMO_USER_PASSWORD=", "DEMO_USER_PASSWORD=" + user_password)
        env = env.replace("DEMO_ADMIN_PASSWORD=", "DEMO_ADMIN_PASSWORD=" + admin_password)
        env_path.write_text(env, encoding="utf-8")
        (RUNTIME / "demo-credentials.txt").write_text(
            f"DEMO ONLY\nstudent@example.com : {user_password}\nadmin@example.com : {admin_password}\n",
            encoding="utf-8",
        )
    status = subprocess.run([command("pg_ctl"), "-D", str(DATA), "status"], capture_output=True)
    if status.returncode:
        run(
            "pg_ctl",
            "-D",
            DATA,
            "-l",
            RUNTIME / "postgres.log",
            "-o",
            "-h 127.0.0.1 -p 55432",
            "-w",
            "start",
        )
    import psycopg
    from dotenv import dotenv_values

    url = dotenv_values(env_path)["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url.rsplit("/", 1)[0] + "/postgres", autocommit=True) as db:
        for name in ["file_converter", "file_converter_test"]:
            if not db.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
                db.execute(
                    psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(name))
                )
    print(
        "Project PostgreSQL ready on 127.0.0.1:55432. Demo credentials: .runtime/demo-credentials.txt"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop"], default="start", nargs="?")
    if parser.parse_args().action == "start":
        start()
    else:
        run("pg_ctl", "-D", DATA, "-m", "fast", "-w", "stop")
