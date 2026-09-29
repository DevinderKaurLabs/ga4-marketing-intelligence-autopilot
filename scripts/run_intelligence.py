"""Run the weekly intelligence engine.

  python scripts/run_intelligence.py --replay     # every complete week, as if run each Monday
  python scripts/run_intelligence.py --latest     # most recent complete week
  python scripts/run_intelligence.py --week 2020-12-28
  add --refresh to re-pull tables from BigQuery
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mia import history  # noqa: E402
from mia.metrics import add_rates, complete_weeks  # noqa: E402
from mia.products import weekly_products  # noqa: E402
from mia.intelligence import build_payload  # noqa: E402

LABEL = {"risks": {"critical": "CRITICAL RISK", "warning": "WARNING", "watch": "WATCH"},
         "opportunities": {"critical": "MAJOR UPSIDE", "warning": "NOTABLE UPSIDE", "watch": "UPSIDE"}}
RANK = {"critical": 0, "warning": 1, "watch": 2}


def headline(payload: dict) -> str:
    """Deterministic one-liner: the most severe signal (risks win ties), else revenue."""
    tops = [(RANK[items[0]["severity"]], i, bucket, items[0])
            for i, bucket in enumerate(("risks", "opportunities"))
            if (items := payload["anomalies"][bucket])]
    if not tops:
        rev = payload["kpis"]["revenue"]
        return f"Stable week: revenue {rev['change_pct']:+.1f}% vs previous week"
    _, _, bucket, a = min(tops, key=lambda t: (t[0], t[1]))
    where = "" if a["dimension"] == "total" else f" [{a['dimension']}: {a['dimension_value']}]"
    note = " (returning to normal after an unusual week)" if a["rule"] == "reverting_to_baseline" else ""
    if a.get("check_tracking"):
        note += " - check tracking before acting"
    return (f"{LABEL[bucket][a['severity']]}: {a['metric_label']} {a['change_pct']:+.1f}% "
            f"vs previous week{where}{note}")


def run(tables: dict, which: list, mode: str, source: str) -> pd.DataFrame:
    rated = add_rates(tables["weekly"])
    weeks = complete_weeks(tables["weekly"])
    wp = weekly_products(tables["products"])
    if mode == "replay":
        history.reset()
    summary = []
    for week in which:
        if week not in weeks or weeks.index(week) == 0:
            print(f"skip {week.date()}: needs a complete previous week")
            continue
        payload, anoms = build_payload(tables, rated, weeks, week, wp, source)
        path = history.save_payload(payload)
        line = headline(payload)
        history.record_run(payload, anoms, rated, mode, path, line)
        k = payload["kpis"]
        c = payload["anomalies"]["counts"]["risks"]
        summary.append({"week_start": payload["run"]["week_start"],
                        "revenue": k["revenue"]["current"], "revenue_change_pct": k["revenue"]["change_pct"],
                        "sessions": k["sessions"]["current"],
                        "conversion_rate": k["conversion_rate"]["current"],
                        "critical": c.get("critical", 0), "warning": c.get("warning", 0),
                        "watch": c.get("watch", 0),
                        "upside_signals": sum(payload["anomalies"]["counts"]["opportunities"].values()),
                        "events": ", ".join(payload["calendar_events"]["this_week"]), "headline": line})
    df = pd.DataFrame(summary)
    if not df.empty:
        df.to_csv(history.ARTIFACTS / "replay_summary.csv", index=False)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--replay", action="store_true")
    g.add_argument("--latest", action="store_true")
    g.add_argument("--week", help="Monday of the week, YYYY-MM-DD")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    from mia.bq import settings
    from mia.data import load_tables
    tables = load_tables(refresh=args.refresh)
    weeks = complete_weeks(tables["weekly"])
    if args.replay:
        which, mode = weeks[1:], "replay"
    elif args.latest:
        which, mode = weeks[-1:], "latest"
    else:
        which, mode = [pd.Timestamp(args.week)], "single"
    df = run(tables, which, mode, settings()["source"])
    pd.set_option("display.width", 200, "display.max_colwidth", 90)
    print(df[["week_start", "revenue", "revenue_change_pct", "critical", "warning", "watch",
              "headline"]].to_string(index=False))
    print(f"\nPayloads: artifacts/payloads/  History: artifacts/intelligence.db  "
          f"Summary: artifacts/replay_summary.csv")


if __name__ == "__main__":
    main()
