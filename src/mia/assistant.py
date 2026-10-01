"""Manager assistant: plan -> call data tools -> answer -> validate numbers.

The model never sees the database. It picks from a small set of read-only tools, the code runs
them, and the answer must only use numbers the tools returned (same validator as the brief)."""
import json

from mia import llm
from mia.validator import allowed_numbers, validate

MAX_CALLS = 3


def _kpis(store, week):
    p = store.payloads[week]
    return {"week": week, "calendar_events": p["calendar_events"]["this_week"],
            "kpis": p["kpis"], "funnel": p["funnel"]}


def _trend(store):
    if store.runs.empty:
        return {"weeks": []}
    cols = [c for c in ("week_start", "revenue", "revenue_change_pct", "n_critical", "n_warning", "headline")
            if c in store.runs.columns]
    return {"weeks": store.runs[cols].to_dict("records")}


def _anomalies(store, week=None, severity=None, dimension=None, direction=None):
    a = store.anomalies
    if a.empty:
        return {"signals": []}
    if week:
        a = a[a["week_start"] == week]
    if severity:
        a = a[a["severity"] == severity]
    if dimension:
        a = a[a["dimension"] == dimension]
    if direction in ("up", "down"):
        a = a[a["direction"] == direction]
    cols = ["week_start", "severity", "direction", "dimension", "dimension_value", "metric_label",
            "current_value", "previous_value", "change_pct", "check_tracking"]
    a = a[[c for c in cols if c in a.columns]].head(12).copy()
    for c in ("current_value", "previous_value", "change_pct"):
        if c in a:
            a[c] = a[c].round(2)
    return {"signals": a.to_dict("records")}


def _segments(store, dimension, week):
    key = {"channel": "channels", "device": "devices", "country": "countries", "campaign": "campaigns"}.get(
        dimension, "channels")
    return {"week": week, "dimension": dimension, "rows": store.payloads[week].get(key, [])}


def _customers(store, week):
    return {"week": week, **store.payloads[week]["customers"]}


def _products(store, week):
    return {"week": week, **store.payloads[week]["products"]}


def _brief(store, week):
    b = store.brief(week)
    if not b:
        return {"week": week, "brief": None}
    br = b["brief"]
    return {"week": week, "status": b["status"], "headline": br["headline"],
            "summary": br["executive_summary"], "actions": br["actions"], "data_caveats": br["data_caveats"]}


TOOLS = {
    "get_week_kpis": ("KPIs, funnel and calendar events for one week vs the previous week. args: week", _kpis),
    "get_revenue_trend": ("Weekly revenue, change and headline for every week in the history. args: none", _trend),
    "get_anomalies": ("Detected signals. args (all optional): week, severity (critical|warning|watch), "
                      "dimension (total|channel|device|country|campaign), direction (up|down)", _anomalies),
    "get_segments": ("Performance by segment for one week. args: dimension (channel|device|country|campaign), week",
                     _segments),
    "get_customers": ("New vs returning purchasers and RFM customer segments for one week. args: week", _customers),
    "get_products": ("Product gainers, decliners, high-interest/low-conversion and categories. args: week", _products),
    "get_brief": ("The validated weekly brief: headline, summary, actions, caveats. args: week", _brief),
}


def _planner_prompt(question, week, weeks):
    tools = "\n".join(f"- {n}: {d}" for n, (d, _) in TOOLS.items())
    return [{"role": "system", "content":
             "You choose which data tools answer a marketing manager's question. "
             f"Available weeks (Mondays): {weeks[0]} to {weeks[-1]}. The currently selected week is {week}. "
             f"Tools:\n{tools}\n\nReturn ONLY JSON: {{\"calls\": [{{\"tool\": \"name\", \"args\": {{...}}}}]}} "
             f"with at most {MAX_CALLS} calls. Use week values in YYYY-MM-DD form."},
            {"role": "user", "content": question}]


ANSWER_RULES = """You are a senior e-commerce analyst answering a marketing manager.
Use ONLY the tool results provided. Do not calculate new numbers (no sums, differences, ratios).
Copy numbers exactly as they appear (rounding to fewer decimals is fine). If the data cannot answer
the question, say so plainly. Items with check_tracking true must be treated as possible tracking
issues. Phrase causes as hypotheses. The data is Google's public demo dataset.
Return ONLY JSON: {"answer": "2-4 sentences", "evidence": ["metric: numbers"], "likely_drivers": ["..."],
"recommended_action": "one specific action", "data_used": ["tool names"]}"""


def _run_calls(store, calls, week):
    results = {}
    for c in calls[:MAX_CALLS]:
        name = c.get("tool")
        if name not in TOOLS:
            continue
        args = dict(c.get("args") or {})
        fn = TOOLS[name][1]
        if name == "get_revenue_trend":
            out = fn(store)
        else:
            if "week" in args or name in ("get_week_kpis", "get_segments", "get_customers", "get_products",
                                          "get_brief"):
                args["week"] = store.nearest_week(args.get("week") or week)
            try:
                out = fn(store, **{k: v for k, v in args.items() if v not in (None, "")})
            except TypeError:
                out = fn(store, week=store.nearest_week(week)) if name != "get_anomalies" else fn(store, week=week)
        results[f"{name}({json.dumps(args, default=str)})"] = out
    return results


def ask(store, question: str, week: str, model: str, chat_fn=None) -> dict:
    chat_fn = chat_fn or llm.chat
    week = store.nearest_week(week)
    # 1. plan
    try:
        text, _, _ = chat_fn(model, _planner_prompt(question, week, store.weeks), json_mode=None)
        calls = llm.extract_json(text).get("calls", [])
    except Exception:
        calls = []
    if not calls:
        calls = [{"tool": "get_week_kpis", "args": {"week": week}},
                 {"tool": "get_anomalies", "args": {"week": week}}]
    # 2. run tools
    results = _run_calls(store, calls, week)
    allowed = allowed_numbers(results)
    messages = [{"role": "system", "content": ANSWER_RULES},
                {"role": "user", "content": f"Question: {question}\n\nTool results:\n"
                                            + json.dumps(results, default=str, separators=(",", ":"))}]
    # 3. answer + validate (one retry)
    last_error = None
    for attempt in (1, 2):
        try:
            text, _, _ = chat_fn(model, messages, json_mode=None)
            ans = llm.extract_json(text)
            ans = {k: ans.get(k) for k in ("answer", "evidence", "likely_drivers", "recommended_action", "data_used")}
            if not ans["answer"]:
                raise ValueError("empty answer")
        except Exception as exc:
            last_error = str(exc)[:200]
            continue
        check = validate(ans, allowed)
        if check["passed"]:
            return {"ok": True, "attempts": attempt, "answer": ans, "tool_results": results,
                    "numbers_checked": check["numbers_checked"]}
        last_error = "unverified numbers: " + ", ".join(i["text"] for i in check["invalid"][:6])
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": f"These numbers are not in the tool results: {last_error}. "
                                                 "Rewrite using only numbers from the tool results. JSON only."}]
    return {"ok": False, "attempts": 2, "answer": None, "tool_results": results, "error": last_error}
