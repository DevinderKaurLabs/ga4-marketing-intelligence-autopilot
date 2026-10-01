"""Change and anomaly detection: week vs previous week, plus a rolling baseline z-score."""
import numpy as np
import pandas as pd

from mia.metrics import pct_change

# Every metric is "higher is better". denom + min_denom stop tiny segments from firing.
METRICS = {
    "revenue": {"label": "Revenue", "kind": "money", "denom": "transactions", "min_denom": 20},
    "transactions": {"label": "Transactions", "kind": "count", "denom": "transactions", "min_denom": 20},
    "sessions": {"label": "Sessions", "kind": "count", "denom": "sessions", "min_denom": 1000},
    "users": {"label": "Users", "kind": "count", "denom": "sessions", "min_denom": 1000},
    "conversion_rate": {"label": "Conversion rate", "kind": "rate", "denom": "sessions", "min_denom": 1000},
    "engagement_rate": {"label": "Engagement rate", "kind": "rate", "denom": "sessions", "min_denom": 1000},
    "aov": {"label": "Average order value", "kind": "money", "denom": "transactions", "min_denom": 30},
    "revenue_per_session": {"label": "Revenue per session", "kind": "money", "denom": "sessions", "min_denom": 1000},
    "view_to_cart_rate": {"label": "Product view to cart rate", "kind": "rate",
                          "denom": "sessions_with_product_view", "min_denom": 300},
    "cart_to_checkout_rate": {"label": "Cart to checkout rate", "kind": "rate",
                              "denom": "sessions_with_add_to_cart", "min_denom": 150},
    "checkout_to_purchase_rate": {"label": "Checkout to purchase rate", "kind": "rate",
                                  "denom": "sessions_with_checkout", "min_denom": 100},
}
SEVERITY_RANK = {"critical": 0, "warning": 1, "watch": 2}

# Noise controls (tuned on the real GA4 sample)
UNUSABLE_VALUES = {"", "<Other>", "(not set)", "(data deleted)", "(none) / (none)", "<Other> / <Other>"}
MIN_SEGMENT_SHARE = 5.0      # segment must hold >= 5% of total revenue or sessions
MIN_GAP_VS_TOTAL = 15.0      # segment change must differ from the total's change by 15+ points
MAX_SIGNALS_PER_SEGMENT = 2  # keep the two strongest signals per segment
TRACKING_SUSPECT_PCT = 50.0  # business-wide rate/value moves this large: check tracking first
REVENUE_METRICS = {"revenue", "transactions", "aov"}


def severity(change_pct: float, z: float, z_prev: float = np.nan):
    """Magnitude of the weekly change, confirmed by the baseline z-score when available."""
    mag = abs(change_pct)
    has_z = z is not None and not pd.isna(z)
    prev_was_unusual = not pd.isna(z_prev) and abs(z_prev) >= 2 and np.sign(z_prev) != np.sign(change_pct)
    if prev_was_unusual or (has_z and np.sign(z) != np.sign(change_pct)):
        # Change vs last week, but the week is not unusual vs baseline:
        # usually a return to normal after a spike. Never escalate these.
        return ("watch", "reverting_to_baseline") if mag >= 10 else (None, None)
    zabs = abs(z) if has_z else None
    if mag >= 25 and (zabs is None or zabs >= 2):
        return "critical", "large_change"
    if mag >= 15 and (zabs is None or zabs >= 1.5):
        return "warning", "notable_change"
    if mag >= 10:
        return "watch", "moderate_change"
    return None, None


def detect(rated: pd.DataFrame, weeks: list, week, baseline_n: int = 4) -> pd.DataFrame:
    idx = weeks.index(week)
    if idx == 0:
        return pd.DataFrame()
    prev_week = weeks[idx - 1]
    base_weeks = weeks[max(0, idx - baseline_n):idx]
    prev_base_weeks = weeks[max(0, idx - 1 - baseline_n):idx - 1]
    data = rated[rated["week_start"].isin(base_weeks + [week])]
    vals = data["dimension_value"].fillna("")
    data = data[~vals.isin(UNUSABLE_VALUES) & ~vals.str.contains("<Other>|\\(data deleted\\)", regex=True)]
    total = rated[rated["dimension"] == "total"].set_index("week_start")
    tot_cur, tot_prev = total.loc[week], total.loc[prev_week]
    rows = []
    for (dim, val), g in data.groupby(["dimension", "dimension_value"]):
        g = g.set_index("week_start")
        if week not in g.index or prev_week not in g.index:
            continue
        is_total = dim == "total"
        if not is_total:
            rev_share = max(g.loc[week, "revenue"] / max(tot_cur["revenue"], 1),
                            g.loc[prev_week, "revenue"] / max(tot_prev["revenue"], 1)) * 100
            ses_share = max(g.loc[week, "sessions"] / max(tot_cur["sessions"], 1),
                            g.loc[prev_week, "sessions"] / max(tot_prev["sessions"], 1)) * 100
        else:
            rev_share = ses_share = 100.0
        cur, prev = g.loc[week], g.loc[prev_week]
        seg_rev_delta = float(cur["revenue"] - prev["revenue"])
        base = dict(dimension=dim, dimension_value=val, segment_revenue_delta=round(seg_rev_delta, 2),
                    segment_revenue_current=round(float(cur["revenue"]), 2))
        for metric, spec in METRICS.items():
            if min(cur[spec["denom"]], prev[spec["denom"]]) < spec["min_denom"]:
                continue
            share = rev_share if metric in REVENUE_METRICS else ses_share
            if share < MIN_SEGMENT_SHARE:
                continue
            c, p = float(cur[metric]), float(prev[metric])
            chg = pct_change(c, p)
            if chg is None:
                continue
            total_chg = pct_change(float(tot_cur[metric]), float(tot_prev[metric]))
            gap = None if total_chg is None else chg - total_chg
            if not is_total and gap is not None and abs(gap) < MIN_GAP_VS_TOTAL:
                continue  # this segment just moved with the business
            hist = g.loc[[w for w in base_weeks if w in g.index], metric].dropna().astype(float)
            z = np.nan
            if len(hist) >= 3 and hist.std(ddof=1) > 0:
                z = (c - hist.mean()) / hist.std(ddof=1)
            prev_hist = g.loc[[w for w in prev_base_weeks if w in g.index], metric].dropna().astype(float)
            z_prev = np.nan
            if len(prev_hist) >= 3 and prev_hist.std(ddof=1) > 0:
                z_prev = (p - prev_hist.mean()) / prev_hist.std(ddof=1)
            sev, rule = severity(chg, z, z_prev)
            if sev is None:
                continue
            tracking = bool(is_total and spec["kind"] in ("rate", "money") and metric != "revenue"
                            and abs(chg) >= TRACKING_SUSPECT_PCT)
            rows.append({**base, "metric": metric, "metric_label": spec["label"], "kind": spec["kind"],
                         "current_value": c, "previous_value": p, "change_pct": chg,
                         "change_abs": c - p, "baseline_mean": hist.mean() if len(hist) else np.nan,
                         "z_score": z, "severity": sev, "rule": rule,
                         "direction": "up" if chg > 0 else "down",
                         "total_change_pct": total_chg, "gap_vs_total_pts": None if is_total else gap,
                         "segment_share_pct": round(share, 1), "check_tracking": tracking})
        # Traffic grew but revenue did not follow
        if min(cur["sessions"], prev["sessions"]) >= 1000 and prev["revenue"] > 0 \
                and ses_share >= MIN_SEGMENT_SHARE:
            s_chg = pct_change(float(cur["sessions"]), float(prev["sessions"]))
            r_chg = pct_change(float(cur["revenue"]), float(prev["revenue"]))
            if s_chg is not None and r_chg is not None and s_chg >= 20 and r_chg <= 2:
                rows.append({**base, "metric": "traffic_vs_revenue",
                             "metric_label": "Traffic up, revenue not following", "kind": "divergence",
                             "current_value": float(cur["revenue"]), "previous_value": float(prev["revenue"]),
                             "change_pct": r_chg, "change_abs": float(cur["revenue"] - prev["revenue"]),
                             "baseline_mean": np.nan, "z_score": np.nan,
                             "severity": "warning" if r_chg <= -5 else "watch", "rule": "divergence",
                             "direction": "down", "sessions_change_pct": s_chg,
                             "segment_share_pct": round(ses_share, 1), "check_tracking": False})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["week_start"] = week
    out["severity_rank"] = out["severity"].map(SEVERITY_RANK)
    out["is_total"] = (out["dimension"] == "total").astype(int)
    # Rank: severity first, total business first, then biggest revenue swing
    out["impact"] = out["segment_revenue_delta"].abs()
    out["abs_change"] = out["change_pct"].abs()
    out = out.sort_values(["severity_rank", "is_total", "impact", "abs_change"],
                          ascending=[True, False, False, False])
    # Keep only the strongest signals per segment (total business keeps up to 6)
    out["n_in_segment"] = out.groupby(["dimension", "dimension_value"]).cumcount()
    limit = np.where(out["dimension"] == "total", 6, MAX_SIGNALS_PER_SEGMENT)
    out = out[out["n_in_segment"] < limit]
    return out.drop(columns=["is_total", "n_in_segment", "abs_change"]).reset_index(drop=True)
