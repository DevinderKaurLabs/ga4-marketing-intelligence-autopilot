"""Write the weekly brief with an LLM, validate every number, render HTML/PDF.

  python scripts/generate_briefs.py --model mistralai/mistral-small-3.2-24b-instruct --weeks all
  python scripts/generate_briefs.py --weeks latest --pdf        # uses MODEL_PRIMARY from env
"""
import argparse
import json
import os

from _common import ARTIFACTS, load_payloads, revenue_history, slug

from mia import history
from mia.insight_engine import generate
from mia.report import render


def run(model: str, weeks: str = "all", pdf: bool = False, chat_fn=None, quiet: bool = False) -> list:
    hist = revenue_history()
    out = []
    for payload in load_payloads(weeks):
        week = payload["run"]["week_start"]
        try:
            result = generate(payload, model, chat_fn=chat_fn)
        except Exception as exc:  # keep going: one provider hiccup must not kill the run
            print(f"{week}  ERROR      {exc.__class__.__name__}: {str(exc)[:160]}  (re-run this week later)")
            continue
        brief_dir = ARTIFACTS / "briefs" / slug(model)
        brief_dir.mkdir(parents=True, exist_ok=True)
        brief_path = brief_dir / f"week_{week}.json"
        brief_path.write_text(json.dumps(result, indent=2, default=str))
        paths = render(result, payload, hist, ARTIFACTS / "reports" / slug(model), pdf=pdf)
        history.record_insight(result, week, brief_path)
        first = result["attempts"][0] if result["attempts"] else {}
        json_fail = sum(1 for a in result["attempts"] if not a.get("ok_json"))
        if not quiet:
            print(f"{week}  {result['status']:9s}  attempts={len(result['attempts'])}  "
                  f"invented_first_try={len(first.get('invalid', []))}  format_failures={json_fail}  "
                  f"numbers_checked={result['numbers_checked']}  {result['latency_s']}s  "
                  f"-> {paths['html'].relative_to(ARTIFACTS.parent)}")
            if result["status"] == "fallback":
                for a in result["attempts"]:
                    why = a.get("error") or f"invented numbers: {[i['text'] for i in a.get('invalid', [])][:6]}"
                    print(f"      attempt {a['attempt']}: {why[:200]}")
                    if a.get("raw_reply"):
                        print(f"        model replied: {a['raw_reply'][:160]!r}")
        out.append((result, payload))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=os.getenv("MODEL_PRIMARY"))
    ap.add_argument("--weeks", default="all", help="all | latest | 2020-12-21[,2020-12-28]")
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()
    if not args.model:
        raise SystemExit("Pass --model or set MODEL_PRIMARY")
    run(args.model, args.weeks, args.pdf)


if __name__ == "__main__":
    main()
