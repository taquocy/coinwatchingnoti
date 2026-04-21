from __future__ import annotations

import logging
import smtplib
from html import unescape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from app.config import Settings

logger = logging.getLogger(__name__)


def _raise_telegram_error(response: requests.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        payload = {"description": response.text}
    description = payload.get("description", response.text)
    raise requests.HTTPError(
        f"{response.status_code} Telegram API error: {description}",
        response=response,
    )


def _strip_html_for_caption(message_html: str, limit: int = 900) -> str:
    text = (
        message_html.replace("<b>", "")
        .replace("</b>", "")
        .replace("<code>", "")
        .replace("</code>", "")
        .replace("<br>", "\n")
    )
    text = unescape(text)
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def send_telegram(settings: Settings, message_html: str) -> None:
    if not settings.telegram_enabled:
        logger.info("Telegram is disabled because TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=20)
    if not response.ok:
        _raise_telegram_error(response)
    logger.info("Telegram message sent successfully.")


def send_telegram_photo(settings: Settings, caption_html: str, image_bytes: bytes) -> None:
    if not settings.telegram_enabled:
        logger.info("Telegram is disabled because TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendPhoto"
    data = {
        "chat_id": settings.telegram_chat_id,
        "caption": _strip_html_for_caption(caption_html),
    }
    files = {
        "photo": ("coingecko_highlights.png", image_bytes, "image/png"),
    }
    response = requests.post(url, data=data, files=files, timeout=60)
    if not response.ok:
        _raise_telegram_error(response)
    logger.info("Telegram photo sent successfully.")


def send_email(settings: Settings, message_text: str, message_html: str) -> None:
    if not settings.email_enabled:
        logger.info("Email sending is disabled by EMAIL_ENABLED=false.")
        return

    required_fields = [
        settings.email_host,
        str(settings.email_port),
        settings.email_username,
        settings.email_password,
        settings.email_from,
    ]
    if not all(required_fields) or not settings.email_to:
        logger.warning("Email config is incomplete. Skipping email delivery.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = settings.email_subject
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(settings.email_to)

    msg.attach(MIMEText(message_text, "plain", "utf-8"))
    msg.attach(MIMEText(message_html, "html", "utf-8"))

    if settings.email_use_ssl:
        with smtplib.SMTP_SSL(settings.email_host, settings.email_port) as server:
            server.login(settings.email_username, settings.email_password)
            server.sendmail(settings.email_from, settings.email_to, msg.as_string())
    else:
        with smtplib.SMTP(settings.email_host, settings.email_port) as server:
            server.starttls()
            server.login(settings.email_username, settings.email_password)
            server.sendmail(settings.email_from, settings.email_to, msg.as_string())

    logger.info("Email sent successfully.")
