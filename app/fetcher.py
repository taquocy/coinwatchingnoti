from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.coingecko.com"
API_BASE_URL = "https://api.coingecko.com/api/v3"

SECTION_ALIASES = {
    "trending": ["tien ao thinh hanh", "trending", "trending coins"],
    "top_gainers": ["tang manh nhat", "top gainers"],
    "top_losers": ["giam manh nhat", "top losers"],
    "new_cryptos": ["tien ao moi", "new cryptocurrencies", "recently added"],
    "most_visited": ["duoc xem nhieu nhat", "most visited"],
    "top_volume": ["khoi luong cao nhat", "highest volume", "top volume"],
}

STOP_TITLES = {
    "tien ao thinh hanh",
    "trending",
    "top gainers",
    "tang manh nhat",
    "top losers",
    "giam manh nhat",
    "tien ao moi",
    "new cryptocurrencies",
    "recently added",
    "mo khoa token sap toi",
    "upcoming token unlocks",
    "duoc xem nhieu nhat",
    "most visited",
    "khoi luong cao nhat",
    "highest volume",
    "top volume",
    "thay doi gia tu muc cao nhat tung duoc ghi nhan (%)",
    "price changes since all time high (%)",
    "tien ao duoc binh chon nhieu nhat",
    "most voted",
}

SKIP_LINES = {
    "them",
    "tien ao",
    "gia",
    "24g",
    "24h",
    "khoi luong",
    "ngay mo khoa tiep theo",
    "tu thoi diem ath (%)",
    "coin",
    "price",
    "volume",
}

PRICE_RE = re.compile(r"\$\s*[\d\.,\s]+")
PERCENT_RE = re.compile(r"([+-]?\d[\d\.,]*)%")


@dataclass(frozen=True)
class CoinEntry:
    name: str
    price_text: str
    percent_value: float
    percent_text: str
    logo_url: str | None = None
    coin_url: str | None = None
    coin_id: str | None = None
    sparkline_points: List[float] | None = None

    @property
    def is_positive(self) -> bool:
        return self.percent_value >= 0


@dataclass(frozen=True)
class HighlightSnapshot:
    fetched_at: datetime
    source_url: str
    sections: Dict[str, List[CoinEntry]]


def _normalize(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split()).strip()


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_only.lower().split()).strip()


def _extract_lines(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    texts = [_normalize(part) for part in soup.get_text("\n", strip=True).split("\n")]
    return [text for text in texts if text]


def _is_section_heading(slug: str) -> bool:
    return slug in STOP_TITLES


def _matches_alias(slug: str, aliases: List[str]) -> bool:
    return any(alias == slug or alias in slug for alias in aliases)


def _looks_like_name(text: str) -> bool:
    slug = _slugify(text)
    if not slug or slug in SKIP_LINES or _is_section_heading(slug):
        return False
    if "$" in text or "%" in text:
        return False
    if re.fullmatch(r"\d+\s*[dhms](?:\s+\d+\s*[dhms])*", slug):
        return False
    return any(ch.isalpha() for ch in text)


def _extract_percent(text: str) -> str | None:
    match = PERCENT_RE.search(text.replace(" ", ""))
    if not match:
        return None
    return f"{match.group(1)}%"


def _normalize_percent(percent_text: str, section_key: str) -> tuple[float, str]:
    raw = percent_text.replace("%", "").replace(",", ".").replace(" ", "")
    if section_key == "top_losers" and not raw.startswith("-"):
        raw = f"-{raw.lstrip('+')}"
    elif section_key == "top_gainers" and not raw.startswith(("+", "-")):
        raw = f"+{raw}"

    value = float(raw.replace("+", ""))
    display = f"{raw}%"
    return value, display


def _extract_logo_url(anchor) -> str | None:
    img = anchor.find("img")
    if not img:
        return None

    candidates = [
        img.get("src"),
        img.get("data-src"),
        img.get("data-lazy-src"),
    ]

    srcset = img.get("srcset") or img.get("data-srcset")
    if srcset:
        candidates.append(srcset.split(",")[0].strip().split(" ")[0])

    for candidate in candidates:
        if not candidate:
            continue
        if candidate.startswith("//"):
            return f"https:{candidate}"
        if candidate.startswith("http"):
            return candidate
        if candidate.startswith("/"):
            return urljoin(BASE_URL, candidate)
    return None


def _extract_coin_id(coin_url: str | None) -> str | None:
    if not coin_url:
        return None
    path = coin_url.rstrip("/").split("/")
    if not path:
        return None
    coin_id = path[-1].strip()
    return coin_id or None


def _extract_anchor_metadata(html: str) -> Dict[str, Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    metadata_map: Dict[str, Dict[str, str]] = {}

    for anchor in soup.find_all("a", href=True):
        text = _normalize(anchor.get_text(" ", strip=True))
        if "$" not in text or "%" not in text:
            continue

        price_match = PRICE_RE.search(text)
        if not price_match:
            continue

        name = text[:price_match.start()].strip()
        if not name:
            continue

        href = anchor.get("href", "").strip()
        coin_url = urljoin(BASE_URL, href) if href else None
        logo_url = _extract_logo_url(anchor)
        metadata = metadata_map.setdefault(name, {})
        if coin_url:
            metadata["coin_url"] = coin_url
            coin_id = _extract_coin_id(coin_url)
            if coin_id:
                metadata["coin_id"] = coin_id
        if logo_url:
            metadata["logo_url"] = logo_url

    return metadata_map


def _fetch_coin_logo(session: requests.Session, coin_url: str, timeout: int) -> str | None:
    response = session.get(
        coin_url,
        timeout=timeout,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    for attrs in [
        {"property": "og:image"},
        {"name": "twitter:image"},
    ]:
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return urljoin(BASE_URL, tag["content"].strip())

    first_img = soup.find("img", src=True)
    if first_img:
        return urljoin(BASE_URL, first_img["src"].strip())
    return None


def _normalize_price(price_text: str | None) -> str:
    if not price_text:
        return "N/A"
    return _normalize(price_text)


def _format_numeric_price(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    if value >= 1000:
        return f"${value:,.2f}"
    if value >= 1:
        return f"${value:,.4f}".rstrip("0").rstrip(".")
    if value >= 0.01:
        return f"${value:,.6f}".rstrip("0").rstrip(".")
    return f"${value:,.10f}".rstrip("0").rstrip(".")


def _build_entry(
    name: str,
    price_text: str | None,
    percent_text: str,
    section_key: str,
    metadata_map: Dict[str, Dict[str, str]],
) -> CoinEntry:
    percent_value, normalized_percent = _normalize_percent(percent_text, section_key)
    metadata = metadata_map.get(name, {})
    return CoinEntry(
        name=name,
        price_text=_normalize_price(price_text),
        percent_value=percent_value,
        percent_text=normalized_percent,
        logo_url=metadata.get("logo_url"),
        coin_url=metadata.get("coin_url"),
        coin_id=metadata.get("coin_id"),
    )


def _find_section_items(
    lines: List[str],
    section_key: str,
    section_titles: List[str],
    metadata_map: Dict[str, Dict[str, str]],
    limit: int = 8,
) -> List[CoinEntry]:
    start_idx = None
    for idx, line in enumerate(lines):
        if _matches_alias(_slugify(line), section_titles):
            start_idx = idx + 1
            break

    if start_idx is None:
        return []

    items: List[CoinEntry] = []
    seen = set()
    pending_name: str | None = None
    pending_price: str | None = None

    for line in lines[start_idx:]:
        normalized = _normalize(line)
        slug = _slugify(normalized)

        if _is_section_heading(slug):
            break
        if slug in SKIP_LINES or not normalized:
            continue
        if re.fullmatch(r"\d+\s*[DHMS](?:\s+\d+\s*[DHMS])*", normalized):
            continue

        price_match = PRICE_RE.search(normalized)
        if price_match and not _extract_percent(normalized):
            pending_price = _normalize(price_match.group(0))
            if pending_name is None:
                possible_name = normalized[:price_match.start()].strip()
                if possible_name:
                    pending_name = possible_name
            continue

        percent = _extract_percent(normalized)
        if not percent:
            if _looks_like_name(normalized):
                pending_name = normalized
                # Keep any pending price if the page lists name first and price on the next line.
            continue

        if price_match:
            name = normalized[:price_match.start()].strip()
            if name:
                pending_name = name
            pending_price = _normalize(price_match.group(0))

        if pending_name:
            entry = _build_entry(pending_name, pending_price, percent, section_key, metadata_map)
            unique_key = (entry.name, entry.price_text, entry.percent_text)
            if unique_key not in seen:
                items.append(entry)
                seen.add(unique_key)
            pending_name = None
            pending_price = None
            if len(items) >= limit:
                break

    return items


def _resolve_missing_logos(
    sections: Dict[str, List[CoinEntry]],
    timeout: int,
) -> Dict[str, List[CoinEntry]]:
    resolved_sections: Dict[str, List[CoinEntry]] = {}
    logo_cache: Dict[str, str | None] = {}

    with requests.Session() as session:
        for section_key, entries in sections.items():
            resolved_entries: List[CoinEntry] = []
            for entry in entries:
                logo_url = entry.logo_url
                if not logo_url and entry.coin_url:
                    if entry.coin_url not in logo_cache:
                        try:
                            logo_cache[entry.coin_url] = _fetch_coin_logo(session, entry.coin_url, timeout)
                        except requests.RequestException:
                            logo_cache[entry.coin_url] = None
                    logo_url = logo_cache.get(entry.coin_url)

                resolved_entries.append(
                    CoinEntry(
                        name=entry.name,
                        price_text=entry.price_text,
                        percent_value=entry.percent_value,
                        percent_text=entry.percent_text,
                        logo_url=logo_url,
                        coin_url=entry.coin_url,
                        coin_id=entry.coin_id,
                        sparkline_points=entry.sparkline_points,
                    )
                )
            resolved_sections[section_key] = resolved_entries

    return resolved_sections


def _fetch_market_data(session: requests.Session, coin_ids: List[str], timeout: int) -> Dict[str, Dict]:
    market_data: Dict[str, Dict] = {}
    batch_size = 80

    for offset in range(0, len(coin_ids), batch_size):
        batch = coin_ids[offset : offset + batch_size]
        response = session.get(
            f"{API_BASE_URL}/coins/markets",
            timeout=timeout,
            params={
                "vs_currency": "usd",
                "ids": ",".join(batch),
                "sparkline": "true",
            },
            headers={
                "Accept": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
        )
        response.raise_for_status()
        for item in response.json():
            market_data[item.get("id")] = item

    return market_data


def _request_json(session: requests.Session, path: str, timeout: int, params: Dict | None = None):
    response = session.get(
        f"{API_BASE_URL}{path}",
        timeout=timeout,
        params=params or {},
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    response.raise_for_status()
    return response.json()


def _entry_from_market_item(item: Dict, section_key: str) -> CoinEntry | None:
    coin_id = item.get("id")
    name = item.get("name")
    if not coin_id or not name:
        return None

    price_change = item.get("price_change_percentage_24h")
    if price_change is None:
        return None

    raw_percent = f"{float(price_change):+.1f}%"
    percent_value, percent_text = _normalize_percent(raw_percent, section_key)

    sparkline = item.get("sparkline_in_7d", {}).get("price")
    sparkline_points = None
    if isinstance(sparkline, list) and sparkline:
        sparkline_points = [float(point) for point in sparkline if isinstance(point, (int, float))]

    return CoinEntry(
        name=name,
        price_text=_format_numeric_price(item.get("current_price")),
        percent_value=percent_value,
        percent_text=percent_text,
        logo_url=item.get("image"),
        coin_url=f"{BASE_URL}/en/coins/{coin_id}",
        coin_id=coin_id,
        sparkline_points=sparkline_points,
    )


def _fetch_highlights_via_api(timeout: int) -> HighlightSnapshot:
    with requests.Session() as session:
        market_items = _request_json(
            session,
            "/coins/markets",
            timeout,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1,
                "sparkline": "true",
                "price_change_percentage": "24h",
                "locale": "vi",
            },
        )

        all_entries = [
            entry
            for item in market_items
            if (entry := _entry_from_market_item(item, "top_gainers")) is not None
        ]

        top_gainers = sorted(all_entries, key=lambda entry: entry.percent_value, reverse=True)[:8]
        top_losers = sorted(
            (
                CoinEntry(
                    name=entry.name,
                    price_text=entry.price_text,
                    percent_value=entry.percent_value,
                    percent_text=entry.percent_text,
                    logo_url=entry.logo_url,
                    coin_url=entry.coin_url,
                    coin_id=entry.coin_id,
                    sparkline_points=entry.sparkline_points,
                )
                for entry in all_entries
            ),
            key=lambda entry: entry.percent_value,
        )[:8]
        top_volume = sorted(all_entries, key=lambda entry: abs(entry.percent_value), reverse=True)[:8]

        trending_entries: List[CoinEntry] = []
        try:
            trending_payload = _request_json(session, "/search/trending", timeout)
            trending_ids = []
            id_to_meta: Dict[str, Dict] = {}
            for coin in trending_payload.get("coins", []):
                item = coin.get("item", {})
                coin_id = item.get("id")
                if not coin_id:
                    continue
                trending_ids.append(coin_id)
                id_to_meta[coin_id] = item

            if trending_ids:
                trending_market = _request_json(
                    session,
                    "/coins/markets",
                    timeout,
                    params={
                        "vs_currency": "usd",
                        "ids": ",".join(trending_ids[:15]),
                        "sparkline": "true",
                        "price_change_percentage": "24h",
                        "locale": "vi",
                    },
                )
                for item in trending_market[:8]:
                    entry = _entry_from_market_item(item, "trending")
                    if entry is None:
                        continue
                    meta = id_to_meta.get(entry.coin_id or "", {})
                    trending_entries.append(
                        CoinEntry(
                            name=entry.name,
                            price_text=entry.price_text,
                            percent_value=entry.percent_value,
                            percent_text=entry.percent_text,
                            logo_url=meta.get("large") or meta.get("small") or entry.logo_url,
                            coin_url=entry.coin_url,
                            coin_id=entry.coin_id,
                            sparkline_points=entry.sparkline_points,
                        )
                    )
        except requests.RequestException:
            trending_entries = top_gainers[:8]

        top_volume_entries = []
        for item in sorted(market_items, key=lambda current: float(current.get("total_volume") or 0), reverse=True)[:8]:
            entry = _entry_from_market_item(item, "top_volume")
            if entry:
                top_volume_entries.append(entry)

        sections = {
            "trending": trending_entries,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "new_cryptos": [],
            "most_visited": trending_entries,
            "top_volume": top_volume_entries,
        }

        return HighlightSnapshot(
            fetched_at=datetime.now(),
            source_url=f"{API_BASE_URL} fallback",
            sections=sections,
        )


def _enrich_entries_with_market_data(
    sections: Dict[str, List[CoinEntry]],
    timeout: int,
) -> Dict[str, List[CoinEntry]]:
    coin_ids = sorted(
        {
            entry.coin_id
            for entries in sections.values()
            for entry in entries
            if entry.coin_id
        }
    )
    if not coin_ids:
        return sections

    try:
        with requests.Session() as session:
            market_data = _fetch_market_data(session, coin_ids, timeout)
    except requests.RequestException:
        return sections

    enriched_sections: Dict[str, List[CoinEntry]] = {}
    for section_key, entries in sections.items():
        enriched_entries: List[CoinEntry] = []
        for entry in entries:
            market_item = market_data.get(entry.coin_id or "")
            price_text = entry.price_text
            sparkline_points = entry.sparkline_points
            if market_item:
                if price_text == "N/A":
                    price_text = _format_numeric_price(market_item.get("current_price"))
                sparkline = market_item.get("sparkline_in_7d", {}).get("price")
                if isinstance(sparkline, list) and sparkline:
                    sparkline_points = [float(point) for point in sparkline if isinstance(point, (int, float))]

            enriched_entries.append(
                CoinEntry(
                    name=entry.name,
                    price_text=price_text,
                    percent_value=entry.percent_value,
                    percent_text=entry.percent_text,
                    logo_url=entry.logo_url,
                    coin_url=entry.coin_url,
                    coin_id=entry.coin_id,
                    sparkline_points=sparkline_points,
                )
            )
        enriched_sections[section_key] = enriched_entries

    return enriched_sections


def fetch_highlights(url: str, timeout: int = 20) -> HighlightSnapshot:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
                "Referer": BASE_URL,
            },
        )
        response.raise_for_status()

        html = response.text
        lines = _extract_lines(html)
        metadata_map = _extract_anchor_metadata(html)
        sections = {
            key: _find_section_items(lines, key, aliases, metadata_map)
            for key, aliases in SECTION_ALIASES.items()
        }
        sections = _enrich_entries_with_market_data(sections, timeout)
        sections = _resolve_missing_logos(sections, timeout)

        return HighlightSnapshot(
            fetched_at=datetime.now(),
            source_url=url,
            sections=sections,
        )
    except requests.RequestException:
        return _fetch_highlights_via_api(timeout)
