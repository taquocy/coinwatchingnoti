from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import requests


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

INDEX_LABELS: Dict[str, str] = {
    "^DJI": "Dow Jones",
    "^IXIC": "Nasdaq",
    "^GSPC": "S&P 500",
    "^RUT": "Russell 2000",
    "GC=F": "Giá vàng",
    "CL=F": "Giá dầu WTI",
    "SI=F": "Giá bạc",
    "^N225": "Nikkei 225",
    "^KS11": "KOSPI",
    "000001.SS": "Shanghai Composite",
}


@dataclass(frozen=True)
class StockIndexEntry:
    symbol: str
    display_name: str
    price_text: str
    change_text: str
    percent_text: str
    market_state: str
    market_time_text: str

    @property
    def is_positive(self) -> bool:
        return self.change_text.startswith("+")


@dataclass(frozen=True)
class StockSnapshot:
    fetched_at: datetime
    source_url: str
    entries: List[StockIndexEntry]


def _format_price(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def _format_change(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+,.2f}"


def _format_percent(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _format_market_time(epoch_seconds: int | None) -> str:
    if not epoch_seconds:
        return "N/A"
    return datetime.fromtimestamp(epoch_seconds).strftime("%Y-%m-%d %H:%M:%S")


def _derive_market_state(meta: Dict) -> str:
    explicit_state = str(meta.get("marketState") or "").strip().upper()
    if explicit_state:
        return explicit_state

    market_time = meta.get("regularMarketTime")
    if not isinstance(market_time, int):
        return "N/A"

    periods = meta.get("currentTradingPeriod", {})
    regular = periods.get("regular", {})
    pre = periods.get("pre", {})
    post = periods.get("post", {})

    def in_period(period: Dict) -> bool:
        start = period.get("start")
        end = period.get("end")
        return isinstance(start, int) and isinstance(end, int) and start <= market_time <= end

    if in_period(regular):
        return "REGULAR"
    if in_period(pre):
        return "PRE"
    if in_period(post):
        return "POST"
    if regular:
        return "CLOSED"
    return "N/A"


def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://finance.yahoo.com",
        "Referer": "https://finance.yahoo.com/",
    }


def _request_chart(session: requests.Session, symbol: str, timeout: int) -> Dict:
    response = session.get(
        YAHOO_CHART_URL.format(symbol=symbol),
        timeout=timeout,
        params={
            "interval": "1d",
            "range": "5d",
            "includePrePost": "true",
            "events": "div,splits",
        },
        headers=_build_headers(),
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("chart", {}).get("result", [])
    if not result:
        error_message = payload.get("chart", {}).get("error", {}).get("description") or "No chart result returned"
        raise requests.HTTPError(f"Yahoo Finance chart error for {symbol}: {error_message}", response=response)
    return result[0]


def _latest_close_from_chart(result: Dict) -> float | None:
    quote_list = result.get("indicators", {}).get("quote", [])
    if not quote_list:
        return None
    closes = quote_list[0].get("close", [])
    valid_closes = [value for value in closes if isinstance(value, (int, float))]
    if not valid_closes:
        return None
    return float(valid_closes[-1])


def _to_entry(symbol: str, result: Dict) -> StockIndexEntry:
    meta = result.get("meta", {})
    display_name = INDEX_LABELS.get(symbol) or meta.get("shortName") or meta.get("longName") or symbol

    current_price = meta.get("regularMarketPrice")
    if current_price is None:
        current_price = _latest_close_from_chart(result)

    previous_close = meta.get("previousClose")
    if previous_close is None:
        previous_close = meta.get("chartPreviousClose")

    change_value = None
    change_percent = None
    if isinstance(current_price, (int, float)) and isinstance(previous_close, (int, float)) and previous_close != 0:
        change_value = float(current_price) - float(previous_close)
        change_percent = (change_value / float(previous_close)) * 100

    return StockIndexEntry(
        symbol=symbol,
        display_name=display_name,
        price_text=_format_price(current_price),
        change_text=_format_change(change_value),
        percent_text=_format_percent(change_percent),
        market_state=_derive_market_state(meta),
        market_time_text=_format_market_time(meta.get("regularMarketTime")),
    )


def fetch_market_snapshot(symbols: List[str], timeout: int = 20) -> StockSnapshot:
    entries: List[StockIndexEntry] = []
    with requests.Session() as session:
        for symbol in symbols:
            chart = _request_chart(session, symbol, timeout)
            entries.append(_to_entry(symbol, chart))

    return StockSnapshot(
        fetched_at=datetime.now(),
        source_url="https://query1.finance.yahoo.com/v8/finance/chart",
        entries=entries,
    )


def fetch_us_stock_snapshot(symbols: List[str], timeout: int = 20) -> StockSnapshot:
    return fetch_market_snapshot(symbols, timeout)
