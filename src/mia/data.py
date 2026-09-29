"""Pull the analytics tables from BigQuery once, cache them as Parquet, reuse them."""
from pathlib import Path

import pandas as pd

from mia.bq import get_client, query_df, settings

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data"

QUERIES = {
    "weekly": "SELECT * FROM `{p}.{d}.mart_weekly_dimensions`",
    "products": "SELECT * FROM `{p}.{d}.mart_product_daily`",
    "transactions": """SELECT transaction_date, user_pseudo_id, transaction_id, revenue, device, country
                       FROM `{p}.{d}.fct_transactions`""",
    "dq": "SELECT * FROM `{p}.{d}.dq_field_completeness`",
}
DATE_COLS = {"weekly": ["week_start"], "products": ["date"], "transactions": ["transaction_date"]}


def normalise(tables: dict) -> dict:
    """Make BigQuery DATE columns plain pandas datetimes."""
    for name, cols in DATE_COLS.items():
        if name in tables:
            for c in cols:
                tables[name][c] = pd.to_datetime(tables[name][c].astype(str))
    return tables


def load_tables(refresh: bool = False) -> dict:
    CACHE.mkdir(exist_ok=True)
    tables, client, cfg = {}, None, None
    for name, sql in QUERIES.items():
        path = CACHE / f"{name}.parquet"
        if path.exists() and not refresh:
            tables[name] = pd.read_parquet(path)
            continue
        if client is None:
            cfg = settings()
            client = get_client(cfg)
        df = query_df(client, sql.format(p=cfg["project"], d=cfg["dataset"]))
        for c in DATE_COLS.get(name, []):
            df[c] = pd.to_datetime(df[c].astype(str))
        df.to_parquet(path, index=False)
        tables[name] = df
        print(f"Pulled {name}: {len(df):,} rows")
    return normalise(tables)
