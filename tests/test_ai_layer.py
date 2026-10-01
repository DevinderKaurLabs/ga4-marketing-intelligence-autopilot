"""Offline test of the AI layer on a real payload (Christmas week), with a fake LLM.

  python tests/test_ai_layer.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mia.evaluation import score, summarise  # noqa: E402
from mia.insight_engine import generate  # noqa: E402
from mia.report import render  # noqa: E402
from mia.validator import allowed_numbers, validate  # noqa: E402

PAYLOAD = json.loads((ROOT / "tests" / "fixtures" / "week_2020-12-21.json").read_text())

GOOD = {
    "headline": "Revenue fell 68.9% in Christmas week, a seasonal drop that hit every channel.",
    "executive_summary": [
        "Revenue was $14,716 against $47,276 the week before (-68.9%).",
        "Conversion rate fell from 1.64% to 1.06% while sessions fell 33.9%, consistent with holiday shipping cut-offs.",
        "Returning customers held up: their revenue rose 8.8% to 2,735."],
    "what_changed": [
        {"title": "Revenue down 68.9%", "detail": "Transactions fell 62.5% to 257.", "severity": "critical"},
        {"title": "Canada fell less than the total", "detail": "Revenue -52.7%, 16.2 points better than the business.", "severity": "watch"}],
    "likely_drivers": ["Christmas Eve, Christmas Day and Boxing Day fell in this week."],
    "risks": ["January could start slowly if lapsed first-time buyers are not re-engaged."],
    "actions": [
        {"action": "Verify revenue per session tracking before reporting it upward.",
         "why": "The change is large enough to be a tracking issue.", "owner": "Analytics",
         "priority": "High", "evidence": "Revenue per session 1.41 to 0.67 (-52.9%)."},
        {"action": "Send a January win-back email to at-risk high value customers.",
         "why": "This group grew from 16 to 58.", "owner": "CRM", "priority": "medium",
         "evidence": "At-risk high value customers: 58, average spend 192.93."}],
    "data_caveats": ["Session-level source covers 73.5% of sessions; check tracking before acting on the Google Eco Tee Black numbers."],
}
INVENTED = json.loads(json.dumps(GOOD))
INVENTED["executive_summary"][0] = "Revenue was $14,716, about 3.2x lower than the week before and $45,000 below plan."


def fake_chat_factory(replies):
    replies = list(replies)

    def chat(model, messages, **kwargs):
        return replies.pop(0), {"prompt_tokens": 5000, "completion_tokens": 700}, 1.5
    return chat


def test_validator():
    allowed = allowed_numbers(PAYLOAD)
    ok = validate(GOOD, allowed)
    assert ok["passed"], ok["invalid"]
    bad = validate(INVENTED, allowed)
    texts = {i["text"] for i in bad["invalid"]}
    assert not bad["passed"] and "3.2x" not in texts and any("45,000" in t for t in texts), bad
    assert any(t.startswith("3.2") for t in texts), texts
    probe = {"a": "Revenue down 69% to 14.7k on 2020-12-21, 25 December and Dec 26; three actions; 33,000 fewer."}
    assert validate(probe, allowed)["passed"], validate(probe, allowed)
    print("validator ok:", ok["numbers_checked"], "numbers checked in good brief;",
          len(bad["invalid"]), "invented numbers caught:", sorted(texts))


def test_engine_retry_and_fallback():
    r = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory([json.dumps(INVENTED), json.dumps(GOOD)]))
    assert r["status"] == "validated" and len(r["attempts"]) == 2, r["attempts"]
    assert r["brief"]["actions"][0]["owner"] == "Analytics & tracking"  # owner normalised
    fb = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory(["not json", "still not", "{}"]))
    assert fb["status"] == "fallback"
    assert validate(fb["brief"], allowed_numbers(PAYLOAD))["passed"], "fallback must be clean"
    # Formatting slips are repaired, not failed: 5 summary lines, "High" severity, <think> block
    sloppy = json.loads(json.dumps(GOOD))
    sloppy["executive_summary"] = GOOD["executive_summary"] + ["Returning customers held up.", "More text."]
    sloppy["what_changed"][0]["severity"] = "High"
    reply = "<think>Let me work out {the numbers}...</think>```json\n" + json.dumps(sloppy) + "\n```"
    ok = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory([reply]))
    assert ok["status"] == "validated" and len(ok["attempts"]) == 1, ok["attempts"]
    assert ok["brief"]["what_changed"][0]["severity"] == "critical"
    # Empty skeleton from JSON mode -> retry without JSON mode -> real answer
    skeleton = json.dumps({k: None for k in GOOD})
    rec = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory([skeleton, json.dumps(GOOD)]))
    assert rec["status"] == "validated" and len(rec["attempts"]) == 2, rec["attempts"]
    wrapped = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory([json.dumps({"brief": GOOD})]))
    assert wrapped["status"] == "validated", wrapped["attempts"]
    empty = generate(PAYLOAD, "fake/model", chat_fn=fake_chat_factory(["__EMPTY_OUT_OF_TOKENS__"] * 3))
    assert empty["status"] == "fallback" and "length budget" in empty["attempts"][0]["error"]
    print("engine ok: retry validated on attempt 2; garbage -> fallback; sloppy format repaired; empty reply explained")
    return r, fb


def test_report_and_eval(r, fb):
    out = ROOT / "tests" / "_artifacts" / "reports"
    hist = [{"week_start": w, "revenue": v} for w, v in
            [("2020-12-07", 59721), ("2020-12-14", 47276), ("2020-12-21", 14716), ("2020-12-28", 10368)]]
    paths = render(r, PAYLOAD, hist, out)
    html = paths["html"].read_text()
    assert "none invented" in html and "#2F4156" in html and "Playfair Display" in html
    render(fb, PAYLOAD, hist, out / "fallback")
    rows = [score(r, PAYLOAD), score(fb, PAYLOAD)]
    assert rows[0]["tracking_flag_respected"] is True and rows[0]["calendar_used"] is True
    assert rows[0]["first_try_pass"] is False and rows[0]["invented_numbers_first_try"] >= 2
    print(summarise(rows).to_string(index=False))
    print("report ok:", paths["html"])


if __name__ == "__main__":
    test_validator()
    r, fb = test_engine_retry_and_fallback()
    test_report_and_eval(r, fb)
    print("\nAll AI-layer checks passed.")
