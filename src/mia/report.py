"""Render a validated brief to HTML (and PDF if WeasyPrint is installed)."""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from mia import theme

TEMPLATES = Path(__file__).parent / "templates"
KPI_ROWS = [("revenue", "Revenue", "money0"), ("transactions", "Transactions", "int"),
            ("sessions", "Sessions", "int"), ("conversion_rate", "Conversion rate", "pct"),
            ("aov", "Average order value", "money2"), ("revenue_per_session", "Revenue per session", "money2"),
            ("engagement_rate", "Engagement rate", "pct")]


def fmt(value, kind):
    if value is None:
        return "n/a"
    if kind == "money0":
        return f"${value:,.0f}"
    if kind == "money2":
        return f"${value:,.2f}"
    if kind == "pct":
        return f"{value:.2f}%"
    return f"{value:,.0f}"


def kpi_rows(payload):
    rows = []
    for key, label, kind in KPI_ROWS:
        k = payload["kpis"].get(key)
        if not k:
            continue
        chg = k.get("change_pct")
        rows.append({"label": label, "current": fmt(k["current"], kind), "previous": fmt(k["previous"], kind),
                     "change": "n/a" if chg is None else f"{chg:+.1f}%",
                     "dir": "" if chg is None else ("down" if chg < 0 else "up")})
    return rows


def revenue_bars(history, week, width=620, height=70):
    if not history:
        return [], width
    peak = max(h["revenue"] for h in history) or 1
    gap = 6
    w = (width - gap * (len(history) - 1)) / len(history)
    bars = []
    for i, h in enumerate(history):
        bh = max(2, h["revenue"] / peak * height)
        bars.append({"x": round(i * (w + gap), 1), "y": round(74 - bh, 1), "w": round(w, 1), "h": round(bh, 1),
                     "current": h["week_start"] == week})
    return bars, width


def render(result: dict, payload: dict, history: list, out_dir: Path, pdf: bool = False) -> dict:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    week = payload["run"]["week_start"]
    bars, chart_w = revenue_bars(history, week)
    caveats = list(dict.fromkeys(result["brief"].get("data_caveats", []) + payload["data_quality"]["notes"]))[:5]
    html = env.get_template("brief.html").render(
        c=theme.COLORS, fonts_url=theme.GOOGLE_FONTS_URL, stack_heading=theme.STACK_HEADING,
        stack_body=theme.STACK_BODY, stack_script=theme.STACK_SCRIPT,
        run=payload["run"], brief=result["brief"], kpi_rows=kpi_rows(payload), bars=bars, chart_w=chart_w,
        calendar=", ".join(e.split(": ", 1)[-1] for e in payload["calendar_events"]["this_week"]),
        caveats=caveats, status=result["status"], model=result["model"],
        numbers_checked=result["numbers_checked"], attempts=len(result["attempts"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"brief_{week}.html"
    html_path.write_text(html, encoding="utf-8")
    paths = {"html": html_path}
    if pdf:
        try:
            from weasyprint import HTML

            pdf_path = out_dir / f"brief_{week}.pdf"
            HTML(string=html, base_url=str(out_dir)).write_pdf(pdf_path)
            paths["pdf"] = pdf_path
        except Exception as exc:  # PDF is a nice-to-have; HTML is the deliverable
            print(f"PDF skipped ({exc.__class__.__name__}): pip install weasyprint to enable")
    return paths
