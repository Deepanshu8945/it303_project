import html
import logging
import smtplib
from email.message import EmailMessage

from .config import settings
from .database import SessionLocal
from .models import Event, uid


def send_link(user_id, email, purpose, token):
    config = settings()
    link = f"{config.frontend_origin}/{purpose}?token={token}"
    message = EmailMessage()
    message["From"], message["To"] = config.mail_from, email
    message["Subject"] = "File Converter — " + (
        "verify your email" if purpose == "verify" else "reset your password"
    )
    message.set_content(
        f"Open this link to {purpose} your account: {link}\nThis link expires in one hour."
    )
    message.add_alternative(
        f'<h2>File Converter System</h2><p><a href="{html.escape(link)}">{purpose.title()} your account</a></p><p>This link expires in one hour. Ignore this email if you did not request it.</p>',
        subtype="html",
    )
    try:
        if config.mail_mode == "local":
            outbox = config.storage_dir.parent / "outbox"
            outbox.mkdir(parents=True, exist_ok=True)
            eml_file = outbox / f"{uid()}.eml"
            eml_file.write_bytes(message.as_bytes())
            status = "saved locally (development delivery)"
            print(f"\n========================================================")
            print(f"[LOCAL EMAIL] To: {email}")
            print(f"Action: {purpose.title()} account")
            print(f"Link: {link}")
            print(f"Saved locally to: {eml_file}")
            print(f"========================================================\n", flush=True)
        else:
            smtp_cls = smtplib.SMTP_SSL if config.smtp_port == 465 else smtplib.SMTP
            with smtp_cls(config.smtp_host, config.smtp_port, timeout=10) as smtp:
                if config.smtp_starttls and smtp_cls is smtplib.SMTP:
                    smtp.starttls()
                if config.smtp_username:
                    smtp.login(config.smtp_username, config.smtp_password)
                refused = smtp.send_message(message)
                if refused:
                    raise RuntimeError("Recipient rejected")
            status = "accepted by SMTP server"
            print(f"[SMTP EMAIL DISPATCHED] To: {email} | Status: {status}", flush=True)
    except Exception as exc:
        logging.exception("Email delivery failed")
        print(f"[SMTP EMAIL FAILED] To: {email} | Error: {exc}", flush=True)
        status = "delivery failed; user can request a new link"
    with SessionLocal() as db:
        db.add(Event(user_id=user_id, kind="email", message=f"{purpose}: {status}"))
        db.commit()
