from __future__ import annotations

import argparse
import logging
import sys
import time
import traceback
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.fetcher import fetch_highlights
from app.formatter import render_email_html_message, render_telegram_message, render_text_message
from app.notifier import send_email, send_telegram, send_telegram_photo
from app.telegram_card import render_telegram_card


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


def build_messages():
    settings = get_settings()
    snapshot = fetch_highlights(settings.coingecko_url, settings.request_timeout)
    text_message = render_text_message(snapshot)
    telegram_message = render_telegram_message(snapshot)
    email_html_message = render_email_html_message(snapshot)
    telegram_card = render_telegram_card(snapshot)
    return settings, snapshot, text_message, telegram_message, email_html_message, telegram_card


def preview_job() -> str:
    settings, snapshot, text_message, _telegram_message, _email_html_message, _telegram_card = build_messages()
    logger.info(
        "Preview generated successfully from %s with %s populated sections.",
        settings.coingecko_url,
        sum(1 for items in snapshot.sections.values() if items),
    )
    return text_message


def run_job() -> None:
    logger.info("Starting CoinGecko highlight job.")

    settings, _snapshot, text_message, telegram_message, email_html_message, telegram_card = build_messages()

    try:
        send_telegram_photo(settings, telegram_message, telegram_card)
    except Exception:
        logger.warning("Telegram photo delivery failed. Falling back to text message.", exc_info=True)
        send_telegram(settings, telegram_message)
    send_email(settings, text_message, email_html_message)
    logger.info("CoinGecko highlight job finished.")


def run_job_safe() -> None:
    try:
        run_job()
    except Exception:
        logger.error("CoinGecko highlight job failed.\n%s", traceback.format_exc())
        raise


def _build_scheduler() -> BlockingScheduler:
    settings = get_settings()
    timezone = ZoneInfo(settings.timezone)
    scheduler = BlockingScheduler(timezone=timezone)

    for item in settings.schedule_times:
        hour_text, minute_text = item.split(":", maxsplit=1)
        trigger = CronTrigger(hour=int(hour_text), minute=int(minute_text), timezone=timezone)
        scheduler.add_job(run_job_safe, trigger=trigger, id=f"job-{item}", replace_existing=True)
        logger.info("Scheduled job at %s (%s).", item, settings.timezone)

    return scheduler


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CoinGecko Highlights notifier")
    parser.add_argument("--run-once", action="store_true", help="Run immediately and exit")
    parser.add_argument("--preview", action="store_true", help="Fetch and print the current highlights without sending notifications")
    args = parser.parse_args(argv)

    if args.preview:
        print(preview_job())
        return

    if args.run_once:
        run_job_safe()
        return

    scheduler = _build_scheduler()
    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        time.sleep(0.1)
        sys.exit(0)
