from __future__ import annotations

import base64
from html import escape
from io import BytesIO
from typing import Dict, List

from PIL import Image, ImageDraw

from app.fetcher import CoinEntry, HighlightSnapshot

SECTION_LABELS: Dict[str, str] = {
    "trending": "Tiền ảo thịnh hành",
    "top_gainers": "Tăng mạnh nhất",
    "top_losers": "Giảm mạnh nhất",
    "new_cryptos": "Tiền ảo mới",
    "most_visited": "Được xem nhiều nhất",
    "top_volume": "Khối lượng cao nhất",
}

SECTION_EMOJIS: Dict[str, str] = {
    "trending": "🔥",
    "top_gainers": "🚀",
    "top_losers": "📉",
    "new_cryptos": "✨",
    "most_visited": "👀",
    "top_volume": "💰",
}


def _to_bullet_lines(items: List[CoinEntry], empty_text: str) -> List[str]:
    if not items:
        return [empty_text]
    return [f"- {item.name} | Giá: {item.price_text} | {item.percent_text}" for item in items]


def _sparkline_data_uri(entry: CoinEntry, width: int = 120, height: int = 32) -> str | None:
    points = entry.sparkline_points or []
    if len(points) < 2:
        return None

    image = Image.new("RGBA", (width, height), (248, 250, 252, 255))
    draw = ImageDraw.Draw(image)
    color = (22, 163, 74, 255) if entry.is_positive else (220, 38, 38, 255)
    border = (226, 232, 240, 255)

    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill=(248, 250, 252, 255), outline=border)

    min_price = min(points)
    max_price = max(points)
    price_range = max_price - min_price
    if price_range == 0:
        price_range = max_price or 1

    plot_points = []
    for index, value in enumerate(points):
        x = 8 + (index / (len(points) - 1)) * (width - 16)
        normalized = (value - min_price) / price_range
        y = height - 8 - normalized * (height - 16)
        plot_points.append((x, y))

    if len(plot_points) >= 2:
        draw.line(plot_points, fill=color, width=3)
        last_x, last_y = plot_points[-1]
        draw.ellipse((last_x - 2, last_y - 2, last_x + 2, last_y + 2), fill=color)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render_text_message(snapshot: HighlightSnapshot) -> str:
    lines = [
        "COINGECKO HIGHLIGHTS",
        f"Thời gian lấy dữ liệu: {snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Nguồn: {snapshot.source_url}",
        "",
    ]

    for key, title in SECTION_LABELS.items():
        lines.append(f"{SECTION_EMOJIS.get(key, '•')} [{title}]")
        lines.extend(_to_bullet_lines(snapshot.sections.get(key, []), "- Không lấy được dữ liệu"))
        lines.append("")

    return "\n".join(lines).strip()


def render_telegram_message(snapshot: HighlightSnapshot) -> str:
    blocks = [
        "<b>CoinGecko Highlights</b>",
        f"<b>Thời gian:</b> {escape(snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S'))}",
        f"<b>Nguồn:</b> {escape(snapshot.source_url)}",
        "",
    ]

    for key, title in SECTION_LABELS.items():
        blocks.append(f"{escape(SECTION_EMOJIS.get(key, '•'))} <b>{escape(title)}</b>")
        items = snapshot.sections.get(key, [])
        if not items:
            blocks.append("- Không lấy được dữ liệu")
        else:
            for item in items:
                blocks.append(
                    f"- {escape(item.name)} | Giá: <code>{escape(item.price_text)}</code> | "
                    f"<b>{escape(item.percent_text)}</b>"
                )
        blocks.append("")

    return "\n".join(blocks).strip()


def render_email_html_message(snapshot: HighlightSnapshot) -> str:
    sections_html: List[str] = []

    for key, title in SECTION_LABELS.items():
        items = snapshot.sections.get(key, [])
        item_rows: List[str] = []

        if not items:
            item_rows.append(
                "<div style='padding:8px 0;color:#6b7280;font-size:14px;line-height:20px;'>Không lấy được dữ liệu</div>"
            )
        else:
            for item in items:
                color = "#16a34a" if item.is_positive else "#dc2626"
                logo_html = ""
                if item.logo_url:
                    logo_html = (
                        f"<img src='{escape(item.logo_url)}' alt='{escape(item.name)}' "
                        "width='22' height='22' "
                        "style='display:block;border-radius:50%;background:#ffffff;border:1px solid #e5e7eb;'>"
                    )

                chart_uri = _sparkline_data_uri(item)
                chart_html = ""
                if chart_uri:
                    chart_html = (
                        f"<img src='{chart_uri}' alt='chart {escape(item.name)}' width='120' height='32' "
                        "style='display:block;max-width:100%;height:auto;border-radius:8px;'>"
                    )

                item_rows.append(
                    "<div style='padding:12px 0;border-bottom:1px solid #f1f5f9;'>"
                    "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' "
                    "style='border-collapse:collapse;width:100%;'>"
                    "<tr>"
                    "<td style='vertical-align:top;'>"
                    "<table role='presentation' cellspacing='0' cellpadding='0' border='0' style='border-collapse:collapse;'>"
                    "<tr>"
                    f"<td style='vertical-align:middle;padding-right:10px;width:22px;'>{logo_html}</td>"
                    "<td style='vertical-align:middle;'>"
                    f"<div style='font-size:14px;line-height:20px;color:#0f172a;font-weight:700;'>{escape(item.name)}</div>"
                    f"<div style='font-size:12px;line-height:18px;color:#64748b;'>Giá: {escape(item.price_text)}</div>"
                    "</td>"
                    "</tr>"
                    "</table>"
                    "</td>"
                    "</tr>"
                    "<tr>"
                    "<td style='padding-top:10px;'>"
                    "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' "
                    "style='border-collapse:collapse;width:100%;'>"
                    "<tr>"
                    "<td style='vertical-align:middle;'>"
                    f"{chart_html or '<div style=\"height:32px;\"></div>'}"
                    "</td>"
                    f"<td style='vertical-align:middle;text-align:right;padding-left:12px;font-size:14px;line-height:20px;font-weight:700;color:{color};white-space:nowrap;'>{escape(item.percent_text)}</td>"
                    "</tr>"
                    "</table>"
                    "</td>"
                    "</tr>"
                    "</table>"
                    "</div>"
                )

        sections_html.append(
            "<div style='margin:0 0 18px 0;padding:16px 18px;background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;'>"
            f"<div style='font-size:16px;line-height:22px;font-weight:700;margin-bottom:10px;color:#0f172a;'>"
            f"{escape(SECTION_EMOJIS.get(key, '•'))} {escape(title)}</div>"
            f"{''.join(item_rows)}"
            "</div>"
        )

    return (
        "<html><body style='margin:0;padding:16px;background:#f8fafc;font-family:Arial,sans-serif;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' "
        "style='border-collapse:collapse;width:100%;background:#f8fafc;'>"
        "<tr>"
        "<td align='center'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' border='0' "
        "style='border-collapse:collapse;width:100%;max-width:820px;'>"
        "<tr>"
        "<td style='padding-bottom:18px;'>"
        "<div style='padding:20px;background:#0f172a;border-radius:16px;color:#ffffff;'>"
        "<div style='font-size:24px;line-height:30px;font-weight:800;margin-bottom:8px;'>CoinGecko Highlights</div>"
        f"<div style='font-size:13px;line-height:18px;opacity:0.9;'>Thời gian: {escape(snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
        f"<div style='font-size:13px;line-height:18px;opacity:0.9;word-break:break-all;'>Nguồn: {escape(snapshot.source_url)}</div>"
        "</div>"
        "</td>"
        "</tr>"
        "<tr>"
        f"<td>{''.join(sections_html)}</td>"
        "</tr>"
        "</table>"
        "</td>"
        "</tr>"
        "</table>"
        "</body></html>"
    )
