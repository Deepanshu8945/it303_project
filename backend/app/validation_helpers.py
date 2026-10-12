from email_validator import validate_email


def validate_admin_credentials(config):
    email = validate_email(config.bootstrap_admin_email, check_deliverability=False).normalized
    password = config.bootstrap_admin_password
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise ValueError(
            "BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters and at most 72 UTF-8 bytes."
        )
    if not (
        any(c.isupper() for c in password)
        and any(c.islower() for c in password)
        and any(c.isdigit() for c in password)
    ):
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD needs uppercase, lowercase, and a number.")
    return email, password
