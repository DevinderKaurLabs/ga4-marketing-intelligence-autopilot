"""Shared helpers for the AI-layer scripts."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ARTIFACTS = ROOT / "artifacts"


def slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def load_payloads(weeks: str = "all") -> list:
    files = sorted((ARTIFACTS / "payloads").glob("week_*.json"))
    if not files:
        raise SystemExit("No payloads found. Run: python scripts/run_intelligence.py --replay")
    payloads = [json.loads(f.read_text()) for f in files]
    if weeks == "all":
        return payloads
    if weeks == "latest":
        return payloads[-1:]
    wanted = set(weeks.split(","))
    return [p for p in payloads if p["run"]["week_start"] in wanted]


def revenue_history() -> list:
    path = ARTIFACTS / "replay_summary.csv"
    if not path.exists():
        return []
    with path.open() as fh:
        return [{"week_start": r["week_start"], "revenue": float(r["revenue"])} for r in csv.DictReader(fh)]
