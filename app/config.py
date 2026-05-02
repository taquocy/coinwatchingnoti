from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value.strip())


def _get_csv(name: str, default: str = "") -> List[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    coingecko_url: str
    request_timeout: int
    timezone: str
    schedule_times: List[str]
    us_stock_enabled: bool
    us_stock_symbols: List[str]
    us_stock_market_timezone: str
    us_stock_market_open_time: str
    us_stock_market_close_time: str
    us_stock_morning_timezone: str
    us_stock_morning_time: str
    asia_market_enabled: bool
    asia_market_symbols: List[str]
    asia_market_schedule_specs: List[str]
    telegram_bot_token: str
    telegram_chat_id: str
    email_enabled: bool
    email_host: str
    email_port: int
    email_use_ssl: bool
    email_username: str
    email_password: str
    email_from: str
    email_to: List[str]
    email_subject: str
    us_stock_email_subject: str
    asia_market_email_subject: str

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)


def get_settings() -> Settings:
    return Settings(
        coingecko_url=os.getenv("COINGECKO_URL", "https://www.coingecko.com/vi/highlights"),
        request_timeout=_get_int("REQUEST_TIMEOUT", 20),
        timezone=os.getenv("TIMEZONE", "Asia/Bangkok"),
        schedule_times=_get_csv("SCHEDULE_TIMES", "07:00,13:00,20:00"),
        us_stock_enabled=_get_bool("US_STOCK_ENABLED", True),
        us_stock_symbols=_get_csv("US_STOCK_SYMBOLS", "^DJI,^IXIC,^GSPC,GC=F,CL=F,SI=F"),
        us_stock_market_timezone=os.getenv("US_STOCK_MARKET_TIMEZONE", "America/New_York").strip(),
        us_stock_market_open_time=os.getenv("US_STOCK_MARKET_OPEN_TIME", "09:30").strip(),
        us_stock_market_close_time=os.getenv("US_STOCK_MARKET_CLOSE_TIME", "16:00").strip(),
        us_stock_morning_timezone=os.getenv("US_STOCK_MORNING_TIMEZONE", "Asia/Bangkok").strip(),
        us_stock_morning_time=os.getenv("US_STOCK_MORNING_TIME", "07:00").strip(),
        asia_market_enabled=_get_bool("ASIA_MARKET_ENABLED", True),
        asia_market_symbols=_get_csv("ASIA_MARKET_SYMBOLS", "^N225,^KS11,000001.SS"),
        asia_market_schedule_specs=_get_csv(
            "ASIA_MARKET_SCHEDULE_SPECS",
            "08:30@Asia/Bangkok,10:00@Asia/Bangkok,13:00@Asia/Bangkok,16:30@Asia/Bangkok",
        ),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
        email_enabled=_get_bool("EMAIL_ENABLED", True),
        email_host=os.getenv("EMAIL_HOST", "").strip(),
        email_port=_get_int("EMAIL_PORT", 465),
        email_use_ssl=_get_bool("EMAIL_USE_SSL", True),
        email_username=os.getenv("EMAIL_USERNAME", "").strip(),
        email_password=os.getenv("EMAIL_PASSWORD", "").strip(),
        email_from=os.getenv("EMAIL_FROM", "").strip(),
        email_to=_get_csv("EMAIL_TO"),
        email_subject=os.getenv("EMAIL_SUBJECT", "[CoinGecko] Highlights Daily Update").strip(),
        us_stock_email_subject=os.getenv("US_STOCK_EMAIL_SUBJECT", "[US Stocks] Market Index Update").strip(),
        asia_market_email_subject=os.getenv("ASIA_MARKET_EMAIL_SUBJECT", "[Asia Markets] Index Update").strip(),
    )
