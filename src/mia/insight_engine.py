"""Payload in, validated brief out. Retry on invented numbers; deterministic fallback."""
from mia import llm
from mia.prompts import build_messages, number_feedback, schema_feedback
from mia.schema import Brief, normalise
from mia.validator import allowed_numbers, validate

OWNER_BY_METRIC = {
    "revenue": "Performance marketing", "transactions": "Performance marketing",
    "sessions": "Performance marketing", "users": "Performance marketing",
    "conversion_rate": "E-commerce & CRO", "view_to_cart_rate": "E-commerce & CRO",
    "cart_to_checkout_rate": "E-commerce & CRO", "checkout_to_purchase_rate": "E-commerce & CRO",
    "aov": "Merchandising", "revenue_per_session": "E-commerce & CRO",
    "engagement_rate": "SEO & content", "traffic_vs_revenue": "Performance marketing",
}


def fallback_brief(payload: dict) -> dict:
    """Deterministic brief built only from payload values. Used if the AI keeps failing."""
    k = payload["kpis"]
    risks = payload["anomalies"]["risks"]
    opps = payload["anomalies"]["opportunities"]
    top = (risks or opps or [None])[0]

    def where(a):
        return "the whole business" if a["dimension"] == "total" else f"{a['dimension']} {a['dimension_value']}"

    headline = (f"{top['metric_label']} changed {top['change_pct']}% vs previous week in {where(top)}."
                if top else f"Revenue changed {k['revenue']['change_pct']}% vs previous week.")
    changes = [{"title": f"{a['metric_label']} ({where(a)})",
                "detail": f"{a['previous_value']} to {a['current_value']} ({a['change_pct']}%).",
                "severity": a["severity"] if a in risks else "positive"} for a in (risks + opps)[:4]]
    actions = [{"action": f"Investigate {a['metric_label'].lower()} in {where(a)}.",
                "why": f"Flagged {a['severity']} by the anomaly engine.",
                "owner": "Analytics & tracking" if a.get("check_tracking") else
                OWNER_BY_METRIC.get(a["metric"], "Performance marketing"),
                "priority": "high" if a["severity"] == "critical" else "medium",
                "evidence": f"{a['metric_label']} {a['previous_value']} to {a['current_value']} ({a['change_pct']}%)."}
               for a in risks[:3]] or [{"action": "No action needed beyond routine monitoring.",
                                        "why": "No material risks detected.", "owner": "Performance marketing",
                                        "priority": "low", "evidence": f"Revenue {k['revenue']['change_pct']}%."}]
    return {"headline": headline,
            "executive_summary": [f"Revenue {k['revenue']['current']} vs {k['revenue']['previous']} "
                                  f"({k['revenue']['change_pct']}%).",
                                  f"Sessions {k['sessions']['current']} ({k['sessions']['change_pct']}%), "
                                  f"conversion rate {k['conversion_rate']['current']}%."],
            "what_changed": changes or [{"title": "Stable week", "detail": "No material changes.",
                                         "severity": "watch"}],
            "likely_drivers": [], "risks": [], "actions": actions,
            "data_caveats": payload["data_quality"]["notes"][:4]}


def generate(payload: dict, model: str, max_attempts: int = 3, chat_fn=None) -> dict:
    chat_fn = chat_fn or llm.chat
    allowed = allowed_numbers(payload)
    messages = build_messages(payload)
    attempts, total_latency, tokens_in, tokens_out = [], 0.0, 0, 0
    json_mode = None  # provider default first
    for n in range(1, max_attempts + 1):
        text, usage, latency = chat_fn(model, messages, json_mode=json_mode)
        total_latency += latency
        tokens_in += usage.get("prompt_tokens") or 0
        tokens_out += usage.get("completion_tokens") or 0
        try:
            brief = Brief.model_validate(normalise(llm.extract_json(text))).model_dump()
        except Exception as exc:
            attempts.append({"attempt": n, "ok_json": False, "error": str(exc)[:300], "invalid": [],
                             "raw_reply": text[:400]})
            json_mode = False  # if JSON mode produced junk, let the model answer in plain text next time
            messages += [{"role": "assistant", "content": text}, {"role": "user", "content": schema_feedback(str(exc))}]
            continue
        check = validate(brief, allowed)
        attempts.append({"attempt": n, "ok_json": True, "numbers_checked": check["numbers_checked"],
                         "invalid": check["invalid"]})
        if check["passed"]:
            return {"status": "validated", "model": model, "brief": brief, "attempts": attempts,
                    "numbers_checked": check["numbers_checked"], "latency_s": round(total_latency, 1),
                    "prompt_tokens": tokens_in, "completion_tokens": tokens_out}
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": number_feedback(check["invalid"])}]
    brief = fallback_brief(payload)
    check = validate(brief, allowed)
    return {"status": "fallback", "model": model, "brief": brief, "attempts": attempts,
            "numbers_checked": check["numbers_checked"], "latency_s": round(total_latency, 1),
            "prompt_tokens": tokens_in, "completion_tokens": tokens_out}
