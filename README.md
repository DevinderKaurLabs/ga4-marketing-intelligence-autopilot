# GA4 Marketing Intelligence Autopilot

Turns raw GA4 event data into performance analysis, change detection, executive reports
and a manager-facing AI assistant.

**Core rule: SQL/Python calculates the truth. AI interprets the truth.**

> Architecture demonstration on Google's public GA4 sample
> (`bigquery-public-data.ga4_obfuscated_sample_ecommerce`, Google Merchandise Store,
> Nov 2020 - Jan 2021, obfuscated). It is not live or client data. The same pipeline runs
> on any GA4 BigQuery export (`project.analytics_<property_id>`) by changing `GA4_SOURCE`.

## Architecture

```
GA4 events_* (BigQuery)
  -> SQL analytics layer      stg_sessions, fct_transactions, dim_users,
                              mart_daily_metrics, mart_product_daily, dq_field_completeness
  -> Intelligence (Python)    KPIs, funnel, acquisition, products, customers/RFM,
                              change + anomaly detection, replay mode
  -> AI layer                 Mistral / Qwen via OpenAI-compatible API (or local Ollama)
                              + number validator: AI output may not contain unseen numbers
  -> Outputs                  Streamlit dashboard, weekly executive brief (HTML/PDF),
                              email, run history, manager AI assistant (tool calling)
```

## Quickstart (Google Colab, zero local disk)

1. Create a Google Cloud project and open BigQuery (Sandbox mode, no billing needed).
2. In Colab:

```python
!git clone https://github.com/<you>/ga4-marketing-intelligence-autopilot.git
%cd ga4-marketing-intelligence-autopilot
!pip install -q -r requirements.txt

from google.colab import auth
auth.authenticate_user()

import os
os.environ["GCP_PROJECT_ID"] = "your-gcp-project-id"

!python scripts/build_data_dictionary.py   # -> docs/GA4_DATA_DICTIONARY.md
!python scripts/build_models.py            # -> analytics tables in BigQuery
!python scripts/run_intelligence.py --replay   # -> 12 weekly runs, payloads + history
```

## Intelligence engine

`run_intelligence.py --replay` runs the engine as if it were every Monday from Nov 2020 to Jan 2021.
Each run produces:

- `artifacts/payloads/week_YYYY-MM-DD.json`: the structured payload the AI layer reads
  (KPIs, funnel, anomalies, channels, devices, countries, campaigns, customers/RFM, products,
  data quality, retail calendar)
- a row in `artifacts/intelligence.db` (`runs`, `anomalies`, `metric_snapshots`): marketing memory
- `artifacts/replay_summary.csv`: one line per week with a deterministic headline

**Anomaly logic.** Week vs previous week, confirmed against a 4-week rolling baseline (z-score).
Severity: critical (25%+ and z >= 2), warning (15%+ and z >= 1.5), watch (10%+).
Changes that only reverse an unusual prior week are capped at *watch* and labelled
"returning to normal", so the system does not raise false alarms after Black Friday.
Noise controls: obfuscated values (`<Other>`, `(data deleted)`) are excluded; a segment must hold
at least 5% of revenue or sessions; a segment is only flagged when its change differs from the
whole business by 15+ points (so a holiday drop is one story, not 60 alerts); at most two signals
per segment. Business-wide rate or order-value moves of 50%+ are marked "check tracking before acting".

Offline test (no BigQuery needed): `python tests/test_engine.py`

## Analytics layer

| Table | Grain | Purpose |
|---|---|---|
| `stg_sessions` | session | Flattened events, session source, funnel flags, revenue |
| `fct_transactions` | purchase event | Orders |
| `dim_users` | user | Customer base for new/returning, RFM, CLV |
| `mart_daily_metrics` | day x source x medium x campaign x device x country | Canonical KPI table |
| `mart_product_daily` | day x product | Product funnel and revenue |
| `dq_field_completeness` | field | Data quality notes for every report |

## Roadmap

- [x] Mon: BigQuery layer + data dictionary
- [x] Tue: intelligence engine + anomalies + replay mode + run history
- [ ] Wed: AI layer + validator + Mistral vs Qwen eval + executive brief + email
- [ ] Thu: Streamlit dashboard + manager AI assistant + deploy
