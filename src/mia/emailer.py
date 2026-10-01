"""Send the brief by Gmail (app password). HTML body, PDF attached if present."""
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send(to: str, subject: str, html_path: Path, pdf_path: Path = None) -> None:
    user, password = os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD")
    if not user or not password:
        raise SystemExit("Set GMAIL_USER and GMAIL_APP_PASSWORD (a Google app password, not your login).")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content("Your weekly marketing brief is attached. Open in an HTML-capable mail client.")
    msg.add_alternative(Path(html_path).read_text(encoding="utf-8"), subtype="html")
    if pdf_path and Path(pdf_path).exists():
        msg.add_attachment(Path(pdf_path).read_bytes(), maintype="application", subtype="pdf",
                           filename=Path(pdf_path).name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
