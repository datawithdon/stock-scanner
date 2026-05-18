import html as html_mod
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

from config import EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT


def _row(i: int, c: dict) -> str:
    bg = "#f0fff4" if i % 2 == 0 else "#ffffff"
    chg_color = "#2e7d32" if c["pct_change"] >= 0 else "#c62828"
    chg = f"{'+' if c['pct_change'] >= 0 else ''}{c['pct_change']}%"
    score_color = "#1b5e20" if c["score"] >= 70 else "#e65100" if c["score"] >= 50 else "#424242"
    checks = lambda v: "&#10003;" if v else "&#8212;"
    return (
        f'<tr style="background:{bg}">'
        f'<td style="font-weight:700;padding:8px 12px">{html_mod.escape(str(c["ticker"]))}</td>'
        f'<td style="padding:8px 12px">${c["price"]}</td>'
        f'<td style="padding:8px 12px;color:{chg_color}">{chg}</td>'
        f'<td style="padding:8px 12px">{c["volume_ratio"]}x</td>'
        f'<td style="padding:8px 12px">{c["rsi"]}</td>'
        f'<td style="padding:8px 12px;text-align:center">{checks(c["is_breakout"])}</td>'
        f'<td style="padding:8px 12px;text-align:center">{checks(c["above_sma50"])}</td>'
        f'<td style="padding:8px 12px;text-align:center">{checks(c["above_sma200"])}</td>'
        f'<td style="padding:8px 12px">{c["ret_3m"]}%</td>'
        f'<td style="padding:8px 12px;font-weight:700;color:{score_color}">{c["score"]}</td>'
        "</tr>"
    )


def _build_html(candidates: list[dict], scan_date: str) -> str:
    rows = "".join(_row(i, c) for i, c in enumerate(candidates))
    header_style = "background:#1a237e;color:#fff;padding:8px 12px;text-align:left"
    return f"""
<html><body style="font-family:Arial,sans-serif;max-width:960px;margin:0 auto;color:#212121">
<h2 style="color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:8px">
  Stock Breakout Scanner &mdash; {scan_date}
</h2>
<p>Found <strong>{len(candidates)}</strong> candidates meeting volume surge + price breakout criteria.</p>
<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px">
  <thead>
    <tr>
      <th style="{header_style}">Ticker</th>
      <th style="{header_style}">Price</th>
      <th style="{header_style}">Day Chg</th>
      <th style="{header_style}">Vol Ratio</th>
      <th style="{header_style}">RSI</th>
      <th style="{header_style}">Breakout</th>
      <th style="{header_style}">&gt;50d MA</th>
      <th style="{header_style}">&gt;200d MA</th>
      <th style="{header_style}">3mo Ret</th>
      <th style="{header_style}">Score /100</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#757575;font-size:11px;margin-top:24px;border-top:1px solid #eee;padding-top:12px">
  <strong>Score breakdown:</strong> Volume surge (35pts) &bull; Breakout above 20d high (25pts)
  &bull; Above 50d &amp; 200d MA (20pts) &bull; RSI 50&ndash;75 (20pts)<br>
  Not financial advice. Do your own research before trading.
</p>
</body></html>
"""


def send_alert(candidates: list, scan_date: str = None) -> None:
    if not candidates:
        print("No candidates — skipping email.")
        return

    if not EMAIL_FROM or not EMAIL_PASSWORD:
        print("Email not configured — printing results instead:")
        for c in candidates:
            print(f"  {c['ticker']}: score={c['score']} vol={c['volume_ratio']}x RSI={c['rsi']}")
        return

    scan_date = scan_date or date.today().strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Stock Breakout Scanner: {len(candidates)} candidates — {scan_date}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(_build_html(candidates, scan_date), "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

    print(f"Email sent to {EMAIL_TO}: {len(candidates)} candidates")
