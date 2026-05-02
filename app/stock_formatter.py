from __future__ import annotations

from html import escape

from app.stock_fetcher import StockSnapshot


MARKET_STATE_LABELS = {
    "PRE": "Trước mở cửa",
    "REGULAR": "Đang giao dịch",
    "POST": "Sau đóng cửa",
    "CLOSED": "Đã đóng cửa",
    "N/A": "Không rõ",
}


def _market_state_label(value: str) -> str:
    return MARKET_STATE_LABELS.get(value, value)


def render_market_text_message(snapshot: StockSnapshot, title: str) -> str:
    lines = [
        title.upper(),
        f"Thời gian lấy dữ liệu: {snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    if not snapshot.entries:
        lines.append("- Không lấy được dữ liệu")
    else:
        for entry in snapshot.entries:
            lines.append(
                f"- {entry.display_name} ({entry.symbol}) | "
                f"Giá: {entry.price_text} | "
                f"Biến động: {entry.change_text} ({entry.percent_text}) | "
                f"Trạng thái: {_market_state_label(entry.market_state)} | "
                f"Mốc dữ liệu: {entry.market_time_text}"
            )

    return "\n".join(lines).strip()


def render_market_telegram_message(snapshot: StockSnapshot, title: str) -> str:
    blocks = [
        f"<b>{escape(title)}</b>",
        f"<b>Thời gian:</b> {escape(snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S'))}",
        "",
    ]

    if not snapshot.entries:
        blocks.append("- Không lấy được dữ liệu")
    else:
        for entry in snapshot.entries:
            blocks.append(
                f"📈 <b>{escape(entry.display_name)}</b> <code>{escape(entry.symbol)}</code>\n"
                f"Giá: <code>{escape(entry.price_text)}</code>\n"
                f"Biến động: <b>{escape(entry.change_text)} ({escape(entry.percent_text)})</b>\n"
                f"Trạng thái: {escape(_market_state_label(entry.market_state))}\n"
                f"Mốc dữ liệu: {escape(entry.market_time_text)}"
            )
            blocks.append("")

    return "\n".join(blocks).strip()


def render_market_email_html_message(snapshot: StockSnapshot, title: str) -> str:
    if not snapshot.entries:
        entries_html = (
            "<div style='padding:14px 0;color:#64748b;font-size:14px;line-height:20px;'>"
            "Không lấy được dữ liệu"
            "</div>"
        )
    else:
        rows = []
        for entry in snapshot.entries:
            color = "#16a34a" if entry.is_positive else "#dc2626"
            rows.append(
                "<div style='padding:14px 0;border-bottom:1px solid #e2e8f0;'>"
                f"<div style='font-size:16px;line-height:22px;font-weight:700;color:#0f172a;'>{escape(entry.display_name)} "
                f"<span style='font-size:13px;color:#64748b;'>({escape(entry.symbol)})</span></div>"
                f"<div style='font-size:14px;line-height:22px;color:#0f172a;'>Giá: {escape(entry.price_text)}</div>"
                f"<div style='font-size:14px;line-height:22px;font-weight:700;color:{color};'>"
                f"Biến động: {escape(entry.change_text)} ({escape(entry.percent_text)})</div>"
                f"<div style='font-size:13px;line-height:20px;color:#64748b;'>Trạng thái: {escape(_market_state_label(entry.market_state))}</div>"
                f"<div style='font-size:13px;line-height:20px;color:#64748b;'>Mốc dữ liệu: {escape(entry.market_time_text)}</div>"
                "</div>"
            )
        entries_html = "".join(rows)

    return (
        "<html><body style='margin:0;padding:16px;background:#f8fafc;font-family:Arial,sans-serif;'>"
        "<div style='max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;'>"
        "<div style='padding:20px 24px;background:#0f172a;color:#ffffff;'>"
        f"<div style='font-size:24px;line-height:30px;font-weight:800;'>{escape(title)}</div>"
        f"<div style='font-size:13px;line-height:18px;opacity:0.9;margin-top:8px;'>Thời gian: {escape(snapshot.fetched_at.strftime('%Y-%m-%d %H:%M:%S'))}</div>"
        "</div>"
        f"<div style='padding:0 24px 18px 24px;'>{entries_html}</div>"
        "</div>"
        "</body></html>"
    )


def render_us_stock_text_message(snapshot: StockSnapshot) -> str:
    return render_market_text_message(snapshot, "Chỉ số chứng khoán Mỹ và hàng hóa")


def render_us_stock_telegram_message(snapshot: StockSnapshot) -> str:
    return render_market_telegram_message(snapshot, "Chỉ số chứng khoán Mỹ và hàng hóa")


def render_us_stock_email_html_message(snapshot: StockSnapshot) -> str:
    return render_market_email_html_message(snapshot, "Chỉ số chứng khoán Mỹ và hàng hóa")
