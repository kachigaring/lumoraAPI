"""
Email the generated CSVs after each run.

Uses plain SMTP. Settings come from engine/.env:

    REPORT_TO=you@example.com
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=you@gmail.com
    SMTP_PASSWORD=your-16-char-gmail-app-password   (NOT your normal password)

If REPORT_TO is blank the step is skipped and the files just stay in output/.
An email failure never stops the run - the files are already written.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

from .log import get_logger

log = get_logger()
load_dotenv()


def is_configured() -> bool:
    return bool(os.getenv("REPORT_TO") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def send_report(subject: str, body: str, attachments: list[Path]) -> bool:
    if not is_configured():
        log.info("Email not set up (no REPORT_TO / SMTP_USER / SMTP_PASSWORD in .env) - "
                 "files are in the output folder. See EMAIL_SETUP.md to switch email on.")
        return False

    to_addr = os.getenv("REPORT_TO")
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.set_content(body)

    for path in attachments:
        p = Path(path)
        if not p.exists():
            continue
        msg.add_attachment(
            p.read_bytes(), maintype="text", subtype="csv", filename=p.name
        )

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, password)
            s.send_message(msg)
        log.info(f"Emailed {len(attachments)} file(s) to {to_addr}.")
        return True
    except Exception as e:  # noqa: BLE001 - report and carry on
        log.error(
            f"Could not send the email: {e}\n"
            f"  -> The files are still saved in the output folder.\n"
            f"  -> If this is Gmail, check SMTP_PASSWORD is a 16-character App Password "
            f"(myaccount.google.com > Security > App passwords), not your login password."
        )
        return False
