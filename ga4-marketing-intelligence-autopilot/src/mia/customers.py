"""Customer intelligence: weekly purchaser mix and rule-based RFM segments."""
import numpy as np
import pandas as pd

SEGMENTS = [
    ("champions", "Champions: repeat buyers, recent, high spend"),
    ("loyal", "Loyal: repeat buyers, active in last 60 days"),
    ("at_risk_high_value", "At-risk high value: high spend, no purchase for 45+ days"),
    ("new_high_value", "New high value: first order in last 30 days, high spend"),
    ("new", "New: first order in last 30 days"),
    ("dormant", "Dormant: no purchase for 60+ days"),
    ("one_time_lapsing", "One-time, lapsing: single order 31-60 days ago"),
]


def weekly_customers(tx: pd.DataFrame, week_start) -> dict:
    week_end = week_start + pd.Timedelta(days=6)
    first = tx.groupby("user_pseudo_id")["transaction_date"].min()
    wk = tx[(tx["transaction_date"] >= week_start) & (tx["transaction_date"] <= week_end)].copy()
    wk["is_new"] = wk["user_pseudo_id"].map(first) >= week_start
    revenue = float(wk["revenue"].sum())
    ret_rev = float(wk.loc[~wk["is_new"], "revenue"].sum())
    return {
        "purchasers": int(wk["user_pseudo_id"].nunique()),
        "orders": int(len(wk)),
        "revenue": revenue,
        "new_purchasers": int(wk.loc[wk["is_new"], "user_pseudo_id"].nunique()),
        "returning_purchasers": int(wk.loc[~wk["is_new"], "user_pseudo_id"].nunique()),
        "revenue_from_new": revenue - ret_rev,
        "revenue_from_returning": ret_rev,
        "returning_revenue_share_pct": (ret_rev / revenue * 100) if revenue else None,
    }


def rfm_segments(tx: pd.DataFrame, as_of) -> tuple:
    hist = tx[tx["transaction_date"] <= as_of]
    if hist.empty:
        return pd.DataFrame(), None
    g = hist.groupby("user_pseudo_id").agg(last=("transaction_date", "max"),
                                           frequency=("transaction_date", "size"),
                                           monetary=("revenue", "sum"))
    g["recency_days"] = (as_of - g["last"]).dt.days
    high = g["monetary"].quantile(0.75)
    rec, freq, mon = g["recency_days"], g["frequency"], g["monetary"]
    conditions = [
        (freq >= 2) & (rec <= 30) & (mon >= high),
        (freq >= 2) & (rec <= 60),
        (mon >= high) & (rec > 45),
        (freq == 1) & (rec <= 30) & (mon >= high),
        (freq == 1) & (rec <= 30),
        rec > 60,
    ]
    names = [s for s, _ in SEGMENTS]
    g["segment"] = np.select(conditions, names[:-1], default=names[-1])
    summary = (g.groupby("segment")
                 .agg(customers=("monetary", "size"), revenue=("monetary", "sum"),
                      avg_recency_days=("recency_days", "mean"), avg_orders=("frequency", "mean"),
                      avg_spend=("monetary", "mean"))
                 .reindex(names).fillna(0).reset_index())
    summary["description"] = summary["segment"].map(dict(SEGMENTS))
    return summary, float(high)
