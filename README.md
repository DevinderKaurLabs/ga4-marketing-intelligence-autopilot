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

## AI layer

Run it end to end in Colab with `GA4_Autopilot_AI_Brief_Run.ipynb` (free NVIDIA Build key for Mistral, Qwen and Nemotron, or a free Gemini key; no GPU needed).

```
payload.json -> prompt (rules) -> LLM (Mistral / Qwen / Nemotron via NVIDIA Build free tier; Gemini, OpenRouter, fal or local Ollama by setting)
             -> JSON schema check -> number validator -> retry with the exact invented numbers
             -> after 3 failed attempts: deterministic fallback brief (no AI text)
             -> HTML/PDF brief -> email -> audit trail in intelligence.db (insights table)
```

- **Number validator** (`src/mia/validator.py`): extracts every number the model writes and checks it
  against the payload (rounding allowed, dates ignored). Ratios like "3.2x" or invented targets are
  rejected and sent back to the model.
- **Rules the model must follow** (`src/mia/prompts.py`): no new calculations, "check tracking" items
  are data questions not demand stories, seasonality only from the retail calendar, no actions on
  obfuscated placeholders, max 3 actions each with owner, priority and evidence.
- **Model evaluation** (`scripts/evaluate_models.py`): same payloads and prompt for each model, scored
  on invented numbers, fallbacks, tracking flags respected, placeholder actions, calendar use,
  latency and tokens. Output: `artifacts/eval/model_eval.md`.

```bash
python scripts/list_models.py                                   # current Mistral/Qwen IDs + prices
python scripts/evaluate_models.py --models "$MODEL_A" "$MODEL_B"
python scripts/generate_briefs.py --model "$MODEL_PRIMARY" --weeks all --pdf
python scripts/send_brief.py --to you@example.com --week 2020-12-21
python tests/test_ai_layer.py                                   # offline, fake LLM, real payload
```

## Analytics layer

| Table | Grain | Purpose |
|---|---|---|
| `stg_sessions` | session | Flattened events, session source, funnel flags, revenue |
| `fct_transactions` | purchase event | Orders |
| `dim_users` | user | Customer base for new/returning, RFM, CLV |
| `mart_daily_metrics` | day x source x medium x campaign x device x country | Canonical KPI table |
| `mart_product_daily` | day x product | Product funnel and revenue |
| `dq_field_completeness` | field | Data quality notes for every report |

## Dashboard and manager assistant

`app/streamlit_app.py` reads the saved pipeline outputs (no BigQuery at runtime, no cloud credentials
on the server). Views: Overview, Acquisition, Customers, Products, Signals & history, Weekly brief
(with the model evaluation), and **Ask the data**: a manager assistant that plans calls to seven
read-only data tools, answers from their results, and passes the same number validator as the brief.
If it cannot produce a verifiable answer it shows the retrieved data instead.

Deploy free on Streamlit Community Cloud: main file `app/streamlit_app.py`, secrets `LLM_PROVIDER`,
`LLM_API_KEY` and optionally `APP_PASSCODE` (protects the assistant's free model credits).

```bash
streamlit run app/streamlit_app.py
python tests/test_app.py        # builds synthetic outputs, opens every view, tests the assistant
```

## Visual identity

All documents and charts share one theme (`src/mia/theme.py`, `.streamlit/config.toml`), matching
[devinder-kaur.vercel.app](https://devinder-kaur.vercel.app): navy `#2F4156`, teal `#567C8D`,
teal-ink `#44697A`, sky `#C8D9E6`, beige `#F5EFEB`, white, rule `#DCD3CC`; Playfair Display for
headings, PT Serif for body, Pinyon Script for the masthead. Charts follow one rule: the data point
that matters in navy, context in sky, comparison in teal.

## Roadmap

- [x] Mon: BigQuery layer + data dictionary
- [x] Tue: intelligence engine + anomalies + replay mode + run history
- [x] AI layer + validator + Mistral vs Qwen eval + executive brief + email
- [x] Streamlit dashboard + manager AI assistant (deploy on Streamlit Community Cloud)
