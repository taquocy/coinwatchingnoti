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
from app.stock_fetcher import fetch_market_snapshot, fetch_us_stock_snapshot
from app.stock_formatter import (
    render_market_email_html_message,
    render_market_telegram_message,
    render_market_text_message,
    render_us_stock_email_html_message,
    render_us_stock_telegram_message,
    render_us_stock_text_message,
)
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
    if not settings.us_stock_enabled:
        return text_message

    try:
        stock_snapshot = fetch_us_stock_snapshot(settings.us_stock_symbols, settings.request_timeout)
        stock_text_message = render_us_stock_text_message(stock_snapshot)
        return f"{text_message}\n\n{'=' * 64}\n\n{stock_text_message}"
    except Exception:
        logger.warning("US stock preview generation failed.", exc_info=True)
        return f"{text_message}\n\n{'=' * 64}\n\nKhong lay duoc du lieu chi so chung khoan My."


def preview_us_stock_job() -> str:
    settings = get_settings()
    if not settings.us_stock_enabled:
        return "US stock notifier is disabled by US_STOCK_ENABLED=false."

    stock_snapshot = fetch_us_stock_snapshot(settings.us_stock_symbols, settings.request_timeout)
    return render_us_stock_text_message(stock_snapshot)


def preview_asia_market_job() -> str:
    settings = get_settings()
    if not settings.asia_market_enabled:
        return "Asia market notifier is disabled by ASIA_MARKET_ENABLED=false."

    snapshot = fetch_market_snapshot(settings.asia_market_symbols, settings.request_timeout)
    return render_market_text_message(snapshot, "Chỉ số chứng khoán châu Á")


def run_job() -> None:
    logger.info("Starting CoinGecko highlight job.")

    settings, _snapshot, text_message, telegram_message, email_html_message, telegram_card = build_messages()

    try:
        send_telegram_photo(settings, telegram_message, telegram_card)
    except Exception:
        logger.warning("Telegram photo delivery failed. Falling back to text message.", exc_info=True)
        send_telegram(settings, telegram_message)
    send_email(settings, text_message, email_html_message)

    if settings.us_stock_enabled:
        try:
            run_us_stock_job(settings)
        except Exception:
            logger.warning("US stock delivery failed. Crypto delivery was already completed.", exc_info=True)

    if settings.asia_market_enabled:
        try:
            run_asia_market_job(settings)
        except Exception:
            logger.warning("Asia market delivery failed. Other deliveries were already completed.", exc_info=True)

    logger.info("CoinGecko highlight job finished.")


def run_us_stock_job(settings=None) -> None:
    settings = settings or get_settings()
    if not settings.us_stock_enabled:
        logger.info("US stock job skipped because US_STOCK_ENABLED=false.")
        return

    logger.info("Fetching US stock market index snapshot.")
    stock_snapshot = fetch_us_stock_snapshot(settings.us_stock_symbols, settings.request_timeout)
    stock_text_message = render_us_stock_text_message(stock_snapshot)
    stock_telegram_message = render_us_stock_telegram_message(stock_snapshot)
    stock_email_html_message = render_us_stock_email_html_message(stock_snapshot)
    send_telegram(settings, stock_telegram_message)
    send_email(
        settings,
        stock_text_message,
        stock_email_html_message,
        subject=settings.us_stock_email_subject,
    )
    logger.info("US stock market index job finished.")


def run_asia_market_job(settings=None) -> None:
    settings = settings or get_settings()
    if not settings.asia_market_enabled:
        logger.info("Asia market job skipped because ASIA_MARKET_ENABLED=false.")
        return

    logger.info("Fetching Asia market index snapshot.")
    snapshot = fetch_market_snapshot(settings.asia_market_symbols, settings.request_timeout)
    text_message = render_market_text_message(snapshot, "Chỉ số chứng khoán châu Á")
    telegram_message = render_market_telegram_message(snapshot, "Chỉ số chứng khoán châu Á")
    email_html_message = render_market_email_html_message(snapshot, "Chỉ số chứng khoán châu Á")
    send_telegram(settings, telegram_message)
    send_email(
        settings,
        text_message,
        email_html_message,
        subject=settings.asia_market_email_subject,
    )
    logger.info("Asia market index job finished.")


def run_us_stock_job_safe() -> None:
    try:
        run_us_stock_job()
    except Exception:
        logger.error("US stock market index job failed.\n%s", traceback.format_exc())
        raise


def run_asia_market_job_safe() -> None:
    try:
        run_asia_market_job()
    except Exception:
        logger.error("Asia market index job failed.\n%s", traceback.format_exc())
        raise


def _add_daily_job(scheduler: BlockingScheduler, job_func, job_id: str, hhmm: str, timezone_name: str) -> None:
    hour_text, minute_text = hhmm.split(":", maxsplit=1)
    trigger = CronTrigger(hour=int(hour_text), minute=int(minute_text), timezone=ZoneInfo(timezone_name))
    scheduler.add_job(job_func, trigger=trigger, id=job_id, replace_existing=True)
    logger.info("Scheduled %s at %s (%s).", job_id, hhmm, timezone_name)


def _add_us_stock_jobs(scheduler: BlockingScheduler, settings) -> None:
    if not settings.us_stock_enabled:
        return

    _add_daily_job(
        scheduler,
        run_us_stock_job_safe,
        "us-stock-open",
        settings.us_stock_market_open_time,
        settings.us_stock_market_timezone,
    )
    _add_daily_job(
        scheduler,
        run_us_stock_job_safe,
        "us-stock-close",
        settings.us_stock_market_close_time,
        settings.us_stock_market_timezone,
    )
    _add_daily_job(
        scheduler,
        run_us_stock_job_safe,
        "us-stock-morning",
        settings.us_stock_morning_time,
        settings.us_stock_morning_timezone,
    )


def _add_schedule_specs_jobs(scheduler: BlockingScheduler, job_func, job_id_prefix: str, specs: list[str]) -> None:
    for index, spec in enumerate(specs, start=1):
        hhmm, timezone_name = spec.split("@", maxsplit=1)
        _add_daily_job(scheduler, job_func, f"{job_id_prefix}-{index}", hhmm, timezone_name)


def _add_asia_market_jobs(scheduler: BlockingScheduler, settings) -> None:
    if not settings.asia_market_enabled:
        return
    _add_schedule_specs_jobs(scheduler, run_asia_market_job_safe, "asia-market", settings.asia_market_schedule_specs)


def run_crypto_job_only() -> None:
    logger.info("Starting CoinGecko crypto-only job.")

    settings, _snapshot, text_message, telegram_message, email_html_message, telegram_card = build_messages()

    try:
        send_telegram_photo(settings, telegram_message, telegram_card)
    except Exception:
        logger.warning("Telegram photo delivery failed. Falling back to text message.", exc_info=True)
        send_telegram(settings, telegram_message)
    send_email(settings, text_message, email_html_message)
    logger.info("CoinGecko crypto-only job finished.")


def run_crypto_job_only_safe() -> None:
    try:
        run_crypto_job_only()
    except Exception:
        logger.error("CoinGecko crypto-only job failed.\n%s", traceback.format_exc())
        raise


def _build_scheduler() -> BlockingScheduler:
    settings = get_settings()
    scheduler = BlockingScheduler(timezone=ZoneInfo(settings.timezone))

    for item in settings.schedule_times:
        _add_daily_job(scheduler, run_crypto_job_only_safe, f"crypto-{item}", item, settings.timezone)

    _add_us_stock_jobs(scheduler, settings)
    _add_asia_market_jobs(scheduler, settings)

    return scheduler


def run_job_safe() -> None:
    try:
        run_job()
    except Exception:
        logger.error("CoinGecko highlight job failed.\n%s", traceback.format_exc())
        raise


def run(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CoinGecko Highlights notifier")
    parser.add_argument("--run-once", action="store_true", help="Run immediately and exit")
    parser.add_argument("--preview", action="store_true", help="Fetch and print the current highlights without sending notifications")
    parser.add_argument("--run-stock-once", action="store_true", help="Send only the US stock market update immediately and exit")
    parser.add_argument("--preview-stock", action="store_true", help="Fetch and print only the US stock market update without sending notifications")
    parser.add_argument("--run-asia-market-once", action="store_true", help="Send only the Asia market update immediately and exit")
    parser.add_argument("--preview-asia-market", action="store_true", help="Fetch and print only the Asia market update without sending notifications")
    args = parser.parse_args(argv)

    if args.preview:
        print(preview_job())
        return

    if args.preview_stock:
        try:
            print(preview_us_stock_job())
        except Exception:
            logger.error("US stock preview failed.\n%s", traceback.format_exc())
        return

    if args.preview_asia_market:
        try:
            print(preview_asia_market_job())
        except Exception:
            logger.error("Asia market preview failed.\n%s", traceback.format_exc())
        return

    if args.run_once:
        run_job_safe()
        return

    if args.run_stock_once:
        run_us_stock_job_safe()
        return

    if args.run_asia_market_once:
        run_asia_market_job_safe()
        return

    scheduler = _build_scheduler()
    logger.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        time.sleep(0.1)
        sys.exit(0)
