"""Offline test: runs the full engine on synthetic data shaped like the BigQuery tables.

  python tests/test_engine.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def synthetic_tables(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2020-10-26", "2021-01-25", freq="W-MON")
    segments = [("total", "All traffic", 1.0)] + \
        [("channel", v, s) for v, s in [("google / organic", .4), ("(direct) / (none)", .3), ("google / cpc", .2)]] + \
        [("device", v, s) for v, s in [("desktop", .6), ("mobile", .38)]] + \
        [("country", v, s) for v, s in [("United States", .45), ("India", .1)]] + \
        [("campaign", v, s) for v, s in [("(organic)", .4), ("<Other>", .2)]]
    rows = []
    for i, w in enumerate(weeks):
        season = 1.0 + (0.8 if w == pd.Timestamp("2020-11-23") else 0) - (0.45 if w == pd.Timestamp("2020-12-28") else 0)
        for dim, val, share in segments:
            sessions = int(27000 * share * season * rng.uniform(.92, 1.08))
            viewed = int(sessions * .22)
            cart = int(viewed * .2 * (0.6 if (val == "mobile" and w == pd.Timestamp("2021-01-11")) else 1))
            checkout = int(cart * .65)
            conv = int(checkout * .15)
            rows.append(dict(week_start=w, dimension=dim, dimension_value=val,
                             days_in_data=1 if i == 0 else 7, users=int(sessions * .8),
                             new_users=int(sessions * .6), sessions=sessions,
                             engaged_sessions=int(sessions * .55), sessions_with_product_view=viewed,
                             sessions_with_add_to_cart=cart, sessions_with_checkout=checkout,
                             converting_sessions=conv, transactions=conv,
                             revenue=round(conv * rng.uniform(58, 70), 2)))
    weekly = pd.DataFrame(rows)

    days = pd.date_range("2020-11-01", "2021-01-31")
    items = [(f"Product {i}", "Apparel" if i % 2 else "Bags") for i in range(30)]
    products = pd.DataFrame([dict(date=d, item_id=str(i), item_name=n, item_category=c,
                                  views=int(rng.integers(20, 120)), adds_to_cart=int(rng.integers(2, 20)),
                                  purchase_lines=int(rng.integers(0, 5)), units=int(rng.integers(0, 6)),
                                  item_revenue=float(rng.integers(0, 150)))
                             for d in days for i, (n, c) in enumerate(items)])

    users = [f"u{i}" for i in range(1500)]
    tx = pd.DataFrame({"transaction_date": rng.choice(days, 4000),
                       "user_pseudo_id": rng.choice(users, 4000),
                       "transaction_id": [f"t{i}" for i in range(4000)],
                       "revenue": rng.uniform(10, 250, 4000).round(2),
                       "device": "desktop", "country": "United States"})
    dq = pd.DataFrame([dict(table_name="sessions", field="campaign", rows_checked=100, unusable_rows=40, unusable_pct=40.0),
                       dict(table_name="sessions", field="session_level_source", rows_checked=100, unusable_rows=62, unusable_pct=62.0),
                       dict(table_name="sessions", field="device", rows_checked=100, unusable_rows=0, unusable_pct=0.0)])
    return {"weekly": weekly, "products": products, "transactions": tx, "dq": dq}


def test_replay():
    from mia import history
    history.ARTIFACTS = ROOT / "tests" / "_artifacts"
    history.DB_PATH = history.ARTIFACTS / "intelligence.db"
    if history.DB_PATH.exists():
        history.DB_PATH.unlink()
    import run_intelligence as ri
    from mia.metrics import complete_weeks

    tables = synthetic_tables()
    weeks = complete_weeks(tables["weekly"])
    assert len(weeks) == 13, len(weeks)
    df = ri.run(tables, weeks[1:], "replay", "synthetic")
    assert len(df) == 12
    bf = df[df["week_start"] == "2020-11-23"].iloc[0]
    assert bf["revenue_change_pct"] > 50, bf
    after = df[df["week_start"] == "2020-11-30"].iloc[0]
    assert after["critical"] == 0 and "returning to normal" in after["headline"], after
    ny = df[df["week_start"] == "2020-12-28"].iloc[0]
    assert ny["critical"] >= 1 and "CRITICAL RISK" in ny["headline"], ny
    payload = json.loads((history.ARTIFACTS / "payloads" / "week_2021-01-11.json").read_text())
    risks = payload["anomalies"]["risks"]
    assert any(r["dimension_value"] == "mobile" for r in risks), risks
    # Holiday drop: segments that simply moved with the business must not flood the list
    ny_payload = json.loads((history.ARTIFACTS / "payloads" / "week_2020-12-28.json").read_text())
    assert sum(ny_payload["anomalies"]["counts"]["risks"].values()) <= 12, ny_payload["anomalies"]["counts"]
    assert payload["data_quality"]["notes"], "data quality notes missing"
    assert history.load_runs().shape[0] == 12
    print(df[["week_start", "revenue_change_pct", "critical", "warning", "watch", "headline"]].to_string(index=False))
    print("\nAll checks passed.")


if __name__ == "__main__":
    test_replay()
