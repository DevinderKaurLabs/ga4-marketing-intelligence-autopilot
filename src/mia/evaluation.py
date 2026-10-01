"""Score each model's briefs on what matters to a marketing director: trust first."""
import json

import pandas as pd

PLACEHOLDERS = ("<other>", "(data deleted)", "(not set)")


def _has_tracking_flag(payload: dict) -> bool:
    items = payload["anomalies"]["risks"] + payload["anomalies"]["opportunities"] + \
        payload["products"].get("high_interest_low_conversion", [])
    return any(i.get("check_tracking") for i in items)


def score(result: dict, payload: dict) -> dict:
    brief = result["brief"]
    text = json.dumps(brief).lower()
    first = result["attempts"][0] if result["attempts"] else {}
    events = [e.split(": ", 1)[-1].lower() for e in payload["calendar_events"]["this_week"]]
    tracking = None
    if _has_tracking_flag(payload):
        tracking = any(a["owner"] == "Analytics & tracking" for a in brief["actions"]) or \
            any("track" in c.lower() for c in brief.get("data_caveats", []))
    return {
        "week_start": payload["run"]["week_start"], "model": result["model"], "status": result["status"],
        "attempts": len(result["attempts"]),
        "first_try_pass": bool(first.get("ok_json") and not first.get("invalid")),
        "invented_numbers_first_try": len(first.get("invalid", [])) if first.get("ok_json") else None,
        "format_failures": sum(1 for a in result["attempts"] if not a.get("ok_json")),
        "tracking_flag_respected": tracking,
        "action_on_placeholder": any(p in json.dumps(brief["actions"]).lower() for p in PLACEHOLDERS),
        "calendar_used": (any(e.split()[0] in text for e in events) if events else None),
        "latency_s": result["latency_s"], "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
    }


def summarise(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    g = df.groupby("model")
    out = pd.DataFrame({
        "weeks": g.size(),
        "validated_%": g.apply(lambda x: (x["status"] == "validated").mean() * 100),
        "first_try_pass_%": g["first_try_pass"].mean() * 100,
        "invented_numbers_first_try_avg": g["invented_numbers_first_try"].mean(),
        "fallbacks": g.apply(lambda x: (x["status"] == "fallback").sum()),
        "format_failures": g["format_failures"].sum(),
        "tracking_flags_respected_%": g["tracking_flag_respected"].apply(
            lambda s: s.dropna().astype(float).mean() * 100 if s.notna().any() else None),
        "actions_on_placeholders": g["action_on_placeholder"].sum(),
        "calendar_used_%": g["calendar_used"].apply(
            lambda s: s.dropna().astype(float).mean() * 100 if s.notna().any() else None),
        "avg_latency_s": g["latency_s"].mean(),
        "avg_prompt_tokens": g["prompt_tokens"].mean(),
        "avg_completion_tokens": g["completion_tokens"].mean(),
    })
    return out.round(1).reset_index()


def to_markdown(summary: pd.DataFrame) -> str:
    cols = list(summary.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in summary.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return f"""# Model evaluation: weekly marketing brief

Same payloads, same prompt, same validator for every model. Numbers are computed in SQL/Python;
models only write the analysis.

{chr(10).join(lines)}

**How to read this**
- *validated_%*: briefs that passed the number validator (within 3 attempts). Anything else fell back
  to the deterministic brief, so no invented number can reach a reader.
- *first_try_pass_%* and *invented_numbers_first_try_avg*: how often the model tried to invent numbers
  before being corrected. This is the honest measure of hallucination.
- *tracking_flags_respected_%*: when the data carried a "check tracking" flag, did the brief treat it as
  a data question rather than a demand story?
- *actions_on_placeholders*: actions recommended on obfuscated values like `<Other>` (should be 0).
- *calendar_used_%*: in holiday weeks, did the brief use the retail calendar to explain seasonality?
"""
