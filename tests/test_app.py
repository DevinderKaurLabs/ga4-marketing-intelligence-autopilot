"""Build a full set of pipeline outputs from synthetic data, then open every app view
and ask the assistant a question with a fake model.  python tests/test_app.py"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
ART = ROOT / "tests" / "_app_artifacts"


def build_artifacts():
    shutil.rmtree(ART, ignore_errors=True)
    from mia import history
    history.ARTIFACTS, history.DB_PATH = ART, ART / "intelligence.db"
    import _common
    _common.ARTIFACTS = ART
    import run_intelligence as ri
    import test_engine
    from mia.metrics import complete_weeks
    tables = test_engine.synthetic_tables()
    ri.run(tables, complete_weeks(tables["weekly"])[1:], "replay", "synthetic")

    import generate_briefs
    generate_briefs.ARTIFACTS = ART
    from test_ai_layer import GOOD

    def fake_chat(model, messages, **kw):  # returns a brief built from the payload's own numbers
        payload = json.loads(messages[-1]["content"].split("PAYLOAD:\n", 1)[1])
        k = payload["kpis"]["revenue"]
        brief = json.loads(json.dumps(GOOD))
        brief["headline"] = f"Revenue {k['change_pct']}% vs the previous week."
        brief["executive_summary"] = [f"Revenue was {k['current']} vs {k['previous']}.", "Signals below."]
        brief["what_changed"] = [{"title": "Revenue", "detail": f"{k['change_pct']}%", "severity": "watch"}]
        brief["actions"] = [{"action": "Review revenue.", "why": "Weekly check.", "owner": "Performance marketing",
                             "priority": "medium", "evidence": f"Revenue {k['current']}."}]
        brief["likely_drivers"], brief["risks"], brief["data_caveats"] = [], [], []
        return json.dumps(brief), {"prompt_tokens": 1, "completion_tokens": 1}, 0.1

    results = generate_briefs.run("fake/model-a", "all", chat_fn=fake_chat, quiet=True)
    from mia.evaluation import score
    import pandas as pd
    (ART / "eval").mkdir(exist_ok=True)
    pd.DataFrame([score(r, p) for r, p in results]).to_csv(ART / "eval" / "model_eval_runs.csv", index=False)
    (ART / "PRIMARY_MODEL.txt").write_text("fake/model-a")


def test_views():
    from streamlit.testing.v1 import AppTest
    os.environ["MIA_ARTIFACTS"] = str(ART)
    os.environ.pop("LLM_API_KEY", None)
    views = ["Overview", "Acquisition", "Customers", "Products", "Signals & history", "Weekly brief", "Ask the data"]
    for view in views:
        at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60)
        at.run()
        at.sidebar.radio[0].set_value(view).run()
        assert not at.exception, (view, at.exception)
        print(f"view ok: {view:18s} markdown blocks={len(at.markdown)} charts/tables rendered")
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=60)
    at.run()
    at.sidebar.selectbox[0].set_value("2020-12-28").run()
    assert not at.exception
    print("week switch ok")


def test_assistant():
    from mia.assistant import ask
    from mia.store import Store
    store = Store(ART)
    week = "2020-12-28"
    rev = store.payloads[week]["kpis"]["revenue"]
    calls = []

    def fake(model, messages, **kw):
        calls.append(messages[0]["content"][:30])
        if "choose which data tools" in messages[0]["content"]:
            return json.dumps({"calls": [{"tool": "get_week_kpis", "args": {"week": "2020-12-30"}},
                                         {"tool": "get_anomalies", "args": {"week": week, "severity": "critical"}}]}), {}, 0.1
        if len(calls) == 2:  # first answer invents a number
            return json.dumps({"answer": f"Revenue fell {rev['change_pct']}%, about 2.4x worse than plan.",
                               "evidence": [], "likely_drivers": [], "recommended_action": "x",
                               "data_used": []}), {}, 0.1
        return json.dumps({"answer": f"Revenue changed {rev['change_pct']}% to {rev['current']}.",
                           "evidence": [f"Revenue {rev['previous']} to {rev['current']}"],
                           "likely_drivers": ["New Year week."], "recommended_action": "Check the critical signals.",
                           "data_used": ["get_week_kpis"]}), {}, 0.1

    res = ask(store, "Why did revenue fall?", week, "fake", chat_fn=fake)
    assert res["ok"] and res["attempts"] == 2, res
    assert "get_week_kpis" in list(res["tool_results"])[0]
    print("assistant ok: planned 2 tools, caught an invented number, answered on attempt 2")

    def garbage(model, messages, **kw):
        return "sorry", {}, 0.1
    res2 = ask(store, "anything", week, "fake", chat_fn=garbage)
    assert not res2["ok"] and res2["tool_results"], res2
    print("assistant ok: unusable model output -> shows data instead of an unverified answer")


if __name__ == "__main__":
    build_artifacts()
    test_views()
    test_assistant()
    shutil.rmtree(ART, ignore_errors=True)
    print("\nAll app checks passed.")
