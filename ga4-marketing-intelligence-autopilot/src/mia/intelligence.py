"""Assemble one weekly run into a structured payload.

The payload is the ONLY thing the LLM will see (Wednesday). Every number in it is
computed here, rounded, and later used by the validator to catch invented numbers.
"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from mia.anomalies import detect
from mia.customers import rfm_segments, weekly_customers
from mia.metrics import FUNNEL_STEPS, KPI_FIELDS, pct_change
from mia.products import product_insights

# Static retail calendar so the AI can explain seasonality without guessing.
RETAIL_CALENDAR = {
    "2020-11-26": "US Thanksgiving",
    "2020-11-27": "Black Friday",
    "2020-11-30": "Cyber Monday",
    "2020-12-24": "Christmas Eve",
    "2020-12-25": "Christmas Day",
    "2020-12-26": "Boxing Day",
    "2020-12-31": "New Year's Eve",
    "2021-01-01": "New Year's Day",
}
MONEY = {"revenue", "aov", "revenue_per_session", "revenue_from_new", "revenue_from_returning"}


def rnd(value, metric: str = ""):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if float(value).is_integer() and metric not in MONEY and "pct" not in metric \
                and "rate" not in metric and "share" not in metric:
            return int(value)
        return round(float(value), 2)
    return value


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime("%Y-%m-%d")
    return rnd(obj)


def compare(cur: dict, prev: dict, fields) -> dict:
    out = {}
    for f in fields:
        c, p = cur.get(f), prev.get(f)
        chg = pct_change(c, p)
        out[f] = {"current": rnd(c, f), "previous": rnd(p, f),
                  "change_pct": None if chg is None else round(chg, 1)}
        if ("rate" in f or "share" in f) and c is not None and p is not None \
                and not pd.isna(c) and not pd.isna(p):
            out[f]["change_points"] = round(c - p, 2)
    return out


def segment_table(rated, dim, week, prev_week, top_n, sort_by="revenue"):
    cur = rated[(rated["dimension"] == dim) & (rated["week_start"] == week)].set_index("dimension_value")
    prev = rated[(rated["dimension"] == dim) & (rated["week_start"] == prev_week)].set_index("dimension_value")
    rows = []
    for val, r in cur.sort_values(sort_by, ascending=False).head(top_n).iterrows():
        p = prev.loc[val] if val in prev.index else None
        row = {"name": val}
        for f in ["revenue", "sessions", "transactions", "conversion_rate"]:
            row[f] = rnd(r[f], f)
            row[f + "_change_pct"] = None if p is None else (
                None if pct_change(r[f], p[f]) is None else round(pct_change(r[f], p[f]), 1))
        rows.append(row)
    return rows


def anomaly_records(anoms: pd.DataFrame, direction: str, limit: int) -> list:
    if anoms.empty:
        return []
    sub = anoms[anoms["direction"] == direction].head(limit)
    keep = ["severity", "rule", "dimension", "dimension_value", "metric", "metric_label",
            "current_value", "previous_value", "change_pct", "change_abs", "z_score",
            "segment_revenue_delta", "sessions_change_pct"]
    recs = []
    for r in sub.to_dict("records"):
        rec = {k: r.get(k) for k in keep if k in r}
        rec["change_pct"] = round(rec["change_pct"], 1)
        if rec.get("z_score") is not None and not pd.isna(rec["z_score"]):
            rec["z_score"] = round(rec["z_score"], 2)
        if pd.isna(rec.get("sessions_change_pct", np.nan)):
            rec.pop("sessions_change_pct", None)
        else:
            rec["sessions_change_pct"] = round(rec["sessions_change_pct"], 1)
        recs.append(rec)
    return recs


def data_quality(dq: pd.DataFrame) -> dict:
    fields = dq.to_dict("records")
    notes = []
    for r in fields:
        if r["field"] == "session_level_source":
            notes.append(f"Session-level source is available for {100 - r['unusable_pct']:.1f}% of sessions; "
                         f"the rest use the user's first-touch source.")
        elif r["unusable_pct"] >= 20:
            notes.append(f"Treat {r['field']} breakdowns with caution: {r['unusable_pct']:.1f}% of "
                         f"{r['table_name']} rows are unknown or obfuscated.")
    return {"fields": fields, "notes": notes}


def build_payload(tables: dict, rated: pd.DataFrame, weeks: list, week, wp: pd.DataFrame,
                  source: str) -> tuple:
    idx = weeks.index(week)
    prev_week = weeks[idx - 1]
    week_end = week + pd.Timedelta(days=6)
    total = rated[rated["dimension"] == "total"].set_index("week_start")
    cur, prev = total.loc[week].to_dict(), total.loc[prev_week].to_dict()

    anoms = detect(rated, weeks, week)
    funnel = compare(cur, prev, list(FUNNEL_STEPS))
    leaks = [(k, v["change_pct"]) for k, v in funnel.items() if v["change_pct"] is not None]
    worst = min(leaks, key=lambda x: x[1]) if leaks else None

    tx = tables["transactions"]
    cust_cur, cust_prev = weekly_customers(tx, week), weekly_customers(tx, prev_week)
    rfm_cur, high_value = rfm_segments(tx, week_end)
    rfm_prev, _ = rfm_segments(tx, prev_week + pd.Timedelta(days=6))
    rfm_rows = []
    if not rfm_cur.empty:
        prev_counts = rfm_prev.set_index("segment")["customers"] if not rfm_prev.empty else {}
        for r in rfm_cur.to_dict("records"):
            p = prev_counts.get(r["segment"], 0) if len(prev_counts) else 0
            rfm_rows.append({"segment": r["segment"], "description": r["description"],
                             "customers": int(r["customers"]), "customers_previous_week": int(p),
                             "customers_change": int(r["customers"] - p),
                             "revenue_to_date": round(r["revenue"], 2),
                             "avg_spend": round(r["avg_spend"], 2),
                             "avg_recency_days": round(r["avg_recency_days"], 1)})

    events = [f"{d}: {n}" for d, n in RETAIL_CALENDAR.items()
              if week <= pd.Timestamp(d) <= week_end]
    prev_events = [f"{d}: {n}" for d, n in RETAIL_CALENDAR.items()
                   if prev_week <= pd.Timestamp(d) <= prev_week + pd.Timedelta(days=6)]

    payload = {
        "run": {"week_start": week, "week_end": week_end, "previous_week_start": prev_week,
                "data_source": source, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "note": "Public obfuscated GA4 sample (Google Merchandise Store). Architecture demonstration."},
        "calendar_events": {"this_week": events, "previous_week": prev_events},
        "kpis": compare(cur, prev, KPI_FIELDS),
        "funnel": {"steps": {FUNNEL_STEPS[k]: v for k, v in funnel.items()},
                   "biggest_leak": None if worst is None or worst[1] >= 0 else
                   {"step": FUNNEL_STEPS[worst[0]], "change_pct": worst[1]}},
        "anomalies": {"counts": {d: (anoms.loc[anoms["direction"] == ("down" if d == "risks" else "up"),
                                                "severity"].value_counts().to_dict() if not anoms.empty else {})
                                 for d in ("risks", "opportunities")},
                      "risks": anomaly_records(anoms, "down", 8),
                      "opportunities": anomaly_records(anoms, "up", 5)},
        "channels": segment_table(rated, "channel", week, prev_week, 8),
        "devices": segment_table(rated, "device", week, prev_week, 5),
        "countries": segment_table(rated, "country", week, prev_week, 8, sort_by="sessions"),
        "campaigns": segment_table(rated, "campaign", week, prev_week, 6, sort_by="sessions"),
        "customers": {"this_week": compare(cust_cur, cust_prev, list(cust_cur)),
                      "rfm_high_value_threshold": None if high_value is None else round(high_value, 2),
                      "rfm_segments": rfm_rows},
        "products": product_insights(wp, week, prev_week),
        "data_quality": data_quality(tables["dq"]),
    }
    return clean(payload), anoms
