from __future__ import annotations

from io import BytesIO
from typing import Dict, List

import requests
from PIL import Image, ImageDraw, ImageFont

from app.fetcher import CoinEntry, HighlightSnapshot

SECTION_LABELS: Dict[str, str] = {
    "trending": "🔥 Tiền ảo thịnh hành",
    "top_gainers": "🚀 Tăng mạnh nhất",
    "top_losers": "📉 Giảm mạnh nhất",
    "new_cryptos": "✨ Tiền ảo mới",
    "most_visited": "👀 Được xem nhiều nhất",
    "top_volume": "💰 Khối lượng cao nhất",
}

CARD_WIDTH = 1080
PADDING_X = 48
PADDING_Y = 36
HEADER_HEIGHT = 120
SECTION_GAP = 18
ROW_HEIGHT = 62
LOGO_SIZE = 30
CHART_WIDTH = 130
CHART_HEIGHT = 34


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _download_logo(session: requests.Session, url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")
        return image.resize((LOGO_SIZE, LOGO_SIZE))
    except Exception:
        return None


def _fallback_logo(name: str) -> Image.Image:
    image = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (241, 245, 249, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((0, 0, LOGO_SIZE - 1, LOGO_SIZE - 1), fill=(226, 232, 240, 255))
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    font = _load_font(12, bold=True)
    bbox = draw.textbbox((0, 0), initials, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text(
        ((LOGO_SIZE - width) / 2, (LOGO_SIZE - height) / 2 - 1),
        initials,
        fill=(51, 65, 85, 255),
        font=font,
    )
    return image


def _build_row_logo(session: requests.Session, entry: CoinEntry) -> Image.Image:
    logo = _download_logo(session, entry.logo_url)
    if logo:
        return logo
    return _fallback_logo(entry.name)


def _draw_sparkline(draw: ImageDraw.ImageDraw, x: int, y: int, entry: CoinEntry) -> None:
    points = entry.sparkline_points or []
    if len(points) < 2:
        return

    min_price = min(points)
    max_price = max(points)
    price_range = max_price - min_price
    if price_range == 0:
        price_range = max_price or 1

    chart_color = (22, 163, 74, 255) if entry.is_positive else (220, 38, 38, 255)
    draw.rounded_rectangle(
        (x, y, x + CHART_WIDTH, y + CHART_HEIGHT),
        radius=8,
        fill=(248, 250, 252, 255),
        outline=(226, 232, 240, 255),
    )

    plot_points = []
    for index, value in enumerate(points):
        px = x + 8 + (index / (len(points) - 1)) * (CHART_WIDTH - 16)
        normalized = (value - min_price) / price_range
        py = y + CHART_HEIGHT - 8 - normalized * (CHART_HEIGHT - 16)
        plot_points.append((px, py))

    if len(plot_points) >= 2:
        draw.line(plot_points, fill=chart_color, width=3)
        last_x, last_y = plot_points[-1]
        draw.ellipse((last_x - 3, last_y - 3, last_x + 3, last_y + 3), fill=chart_color)


def _estimate_height(snapshot: HighlightSnapshot) -> int:
    total_rows = 0
    for entries in snapshot.sections.values():
        total_rows += max(1, len(entries))
    return HEADER_HEIGHT + (len(snapshot.sections) * 42) + (total_rows * ROW_HEIGHT) + (len(snapshot.sections) * SECTION_GAP) + 80


def render_telegram_card(snapshot: HighlightSnapshot) -> bytes:
    height = _estimate_height(snapshot)
    image = Image.new("RGBA", (CARD_WIDTH, height), (248, 250, 252, 255))
    draw = ImageDraw.Draw(image)

    title_font = _load_font(34, bold=True)
    meta_font = _load_font(18)
    section_font = _load_font(24, bold=True)
    row_font = _load_font(21, bold=True)
    price_font = _load_font(16)
    percent_font = _load_font(22, bold=True)

    draw.rounded_rectangle((24, 20, CARD_WIDTH - 24, height - 20), radius=24, fill=(255, 255, 255, 255))
    draw.rounded_rectangle((24, 20, CARD_WIDTH - 24, 20 + HEADER_HEIGHT), radius=24, fill=(15, 23, 42, 255))

    draw.text((PADDING_X, 42), "CoinGecko Highlights", fill=(255, 255, 255, 255), font=title_font)
    draw.text(
        (PADDING_X, 84),
        f"Thời gian: {snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}",
        fill=(226, 232, 240, 255),
        font=meta_font,
    )

    current_y = 20 + HEADER_HEIGHT + 24
    with requests.Session() as session:
        for key, title in SECTION_LABELS.items():
            draw.text((PADDING_X, current_y), title, fill=(15, 23, 42, 255), font=section_font)
            current_y += 36

            entries = snapshot.sections.get(key, [])
            if not entries:
                draw.text((PADDING_X, current_y), "Không lấy được dữ liệu", fill=(100, 116, 139, 255), font=meta_font)
                current_y += ROW_HEIGHT
            else:
                for entry in entries:
                    logo = _build_row_logo(session, entry)
                    image.alpha_composite(logo, (PADDING_X, current_y + 6))

                    text_x = PADDING_X + LOGO_SIZE + 14
                    draw.text((text_x, current_y + 2), entry.name, fill=(15, 23, 42, 255), font=row_font)
                    draw.text((text_x, current_y + 30), f"Giá: {entry.price_text}", fill=(100, 116, 139, 255), font=price_font)

                    percent_color = (22, 163, 74, 255) if entry.is_positive else (220, 38, 38, 255)
                    percent_bbox = draw.textbbox((0, 0), entry.percent_text, font=percent_font)
                    percent_width = percent_bbox[2] - percent_bbox[0]
                    chart_x = CARD_WIDTH - PADDING_X - CHART_WIDTH - percent_width - 24
                    _draw_sparkline(draw, chart_x, current_y + 12, entry)
                    draw.text(
                        (CARD_WIDTH - PADDING_X - percent_width, current_y + 16),
                        entry.percent_text,
                        fill=percent_color,
                        font=percent_font,
                    )
                    current_y += ROW_HEIGHT

            current_y += SECTION_GAP

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
