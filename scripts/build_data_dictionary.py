"""Profile the GA4 export and write docs/GA4_DATA_DICTIONARY.md (a portfolio artifact)."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mia.bq import get_client, query_df, settings  # noqa: E402

# field -> (business meaning, used for)
MEANING = {
    "event_date": ("Date of the event (YYYYMMDD, property time zone)", "All time series"),
    "event_timestamp": ("Event time in microseconds (UTC)", "Session ordering"),
    "event_name": ("Action performed: page_view, add_to_cart, purchase...", "Funnel, KPIs"),
    "event_params": ("Repeated key/value context for the event", "Sessions, pages, session source"),
    "user_pseudo_id": ("Pseudonymous browser/device ID", "Users, customers, RFM"),
    "user_first_touch_timestamp": ("First time the user was seen", "New vs returning"),
    "device.category": ("desktop / mobile / tablet", "Device analysis"),
    "device.operating_system": ("Operating system", "Device analysis"),
    "device.web_info.browser": ("Browser", "QA, device analysis"),
    "geo.country": ("Country of the user", "Geographic analysis"),
    "geo.city": ("City of the user", "Geographic analysis"),
    "traffic_source.source": ("FIRST-EVER acquisition source of the user (not the session)", "Acquisition"),
    "traffic_source.medium": ("FIRST-EVER acquisition medium of the user", "Acquisition"),
    "traffic_source.name": ("FIRST-EVER acquisition campaign of the user", "Campaigns"),
    "ecommerce.transaction_id": ("Order ID", "Transactions"),
    "ecommerce.purchase_revenue": ("Order revenue", "Revenue, AOV"),
    "ecommerce.total_item_quantity": ("Units in the order", "Basket size"),
    "items": ("Repeated product lines attached to ecommerce events", "Product analysis"),
    "items.item_id": ("Product ID", "Product analysis"),
    "items.item_name": ("Product name", "Product analysis"),
    "items.item_category": ("Product category", "Category analysis"),
    "items.price": ("Unit price", "Product revenue"),
    "items.quantity": ("Units", "Product revenue"),
    "items.item_revenue": ("Line revenue", "Product revenue"),
    "platform": ("WEB / ANDROID / IOS", "Platform split"),
}


def walk(fields, prefix=""):
    for f in fields:
        path = prefix + f.name
        mode = "REPEATED " if f.mode == "REPEATED" else ""
        yield path, mode + f.field_type
        if f.field_type in ("RECORD", "STRUCT"):
            yield from walk(f.fields, path + ".")


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    cfg = settings()
    client = get_client(cfg)
    src = cfg["source"]
    sample_table = client.get_table(f"{src}.events_{cfg['end']}")
    base = (f"FROM `{src}.events_*` "
            f"WHERE _TABLE_SUFFIX BETWEEN '{cfg['start']}' AND '{cfg['end']}'")

    overview = query_df(client, f"""
        SELECT MIN(event_date) AS first_day, MAX(event_date) AS last_day,
               COUNT(*) AS events, COUNT(DISTINCT user_pseudo_id) AS users,
               COUNTIF(event_name = 'purchase') AS purchase_events,
               ROUND(SUM(IF(event_name = 'purchase',
                            IFNULL(ecommerce.purchase_revenue, 0), 0)), 2) AS revenue
        {base}""").iloc[0]
    events = query_df(client, f"""
        SELECT event_name, COUNT(*) AS events, COUNT(DISTINCT user_pseudo_id) AS users
        {base} GROUP BY 1 ORDER BY 2 DESC""")
    params = query_df(client, f"""
        SELECT ep.key AS param_key, COUNT(*) AS occurrences,
               COUNTIF(ep.value.string_value IS NOT NULL) AS as_string,
               COUNTIF(ep.value.int_value IS NOT NULL) AS as_int,
               COUNTIF(ep.value.double_value IS NOT NULL) AS as_double,
               STRING_AGG(DISTINCT e.event_name, ', ' ORDER BY e.event_name LIMIT 6) AS seen_on
        FROM `{src}.events_*` AS e, UNNEST(e.event_params) AS ep
        WHERE _TABLE_SUFFIX BETWEEN '{cfg['start']}' AND '{cfg['end']}'
        GROUP BY 1 ORDER BY 2 DESC""")

    schema_rows = [(f"`{p}`", t, *MEANING.get(p, ("", ""))) for p, t in walk(sample_table.schema)]
    param_rows = []
    for r in params.itertuples():
        kinds = {"string": r.as_string, "int": r.as_int, "double": r.as_double}
        vtype = max(kinds, key=kinds.get)
        param_rows.append((f"`{r.param_key}`", f"{r.occurrences:,}", f"value.{vtype}_value", r.seen_on))
    overview_rows = [
        ("Date range", f"{overview.first_day} to {overview.last_day}"),
        ("Events", f"{int(overview.events):,}"),
        ("Users (user_pseudo_id)", f"{int(overview.users):,}"),
        ("Purchase events", f"{int(overview.purchase_events):,}"),
        ("Purchase revenue", f"{float(overview.revenue):,.2f}"),
    ]
    event_rows = [(f"`{r.event_name}`", f"{r.events:,}", f"{r.users:,}") for r in events.itertuples()]

    doc = f"""# GA4 Data Dictionary

Source: `{src}` (Google Merchandise Store, public obfuscated GA4 export sample).
Generated automatically by `scripts/build_data_dictionary.py` on {date.today()}.

> Architecture demonstration on Google's public 2020-21 sample. Obfuscated values
> (`<Other>`, NULL, '') are expected. The same code runs on any GA4 BigQuery export
> by changing `GA4_SOURCE`.

## Overview

{md_table(["Metric", "Value"], overview_rows)}

## Event inventory

{md_table(["event_name", "Events", "Users"], event_rows)}

## Event parameter inventory

`event_params` is a repeated record, so every parameter is read with `UNNEST`.

{md_table(["Key", "Occurrences", "Stored in", "Seen on events"], param_rows)}

## Schema

{md_table(["Field", "Type", "Business meaning", "Used for"], schema_rows)}

## Modelling notes

- `traffic_source.*` is the user's **first-ever** acquisition source, not the session source.
  `stg_sessions` uses session-level `source`/`medium`/`campaign` params where present and
  falls back to first touch; `source_scope` records which one was used.
- `event_params` and `items` are repeated records and must be flattened with `UNNEST`.
- User counts are not additive across days or dimensions; recompute distinct users from
  `stg_sessions` for any total.
"""
    out = ROOT / "docs" / "GA4_DATA_DICTIONARY.md"
    out.write_text(doc)
    print(f"Wrote {out.relative_to(ROOT)}")
    print(overview.to_string())


if __name__ == "__main__":
    main()
