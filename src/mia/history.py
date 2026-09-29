"""Marketing memory: every run's metrics and anomalies stored in SQLite."""
import json
import sqlite3
from pathlib import Path

import pandas as pd

from mia.metrics import KPI_FIELDS, RATE_DEFS

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DB_PATH = ARTIFACTS / "intelligence.db"
SNAPSHOT_METRICS = sorted(set(KPI_FIELDS) | set(RATE_DEFS))
ANOMALY_COLS = ["run_id", "week_start", "severity", "rule", "dimension", "dimension_value", "metric",
                "metric_label", "kind", "current_value", "previous_value", "change_pct", "change_abs",
                "baseline_mean", "z_score", "sessions_change_pct", "segment_revenue_current",
                "segment_revenue_delta", "impact", "direction",
                "total_change_pct", "gap_vs_total_pts", "segment_share_pct", "check_tracking"]


def reset() -> None:
    """Start a replay from a clean memory (schema may have changed between versions)."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    for f in (ARTIFACTS / "payloads").glob("*.json") if (ARTIFACTS / "payloads").exists() else []:
        f.unlink()


def connect() -> sqlite3.Connection:
    ARTIFACTS.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY, week_start TEXT, week_end TEXT, generated_at TEXT, mode TEXT,
        revenue REAL, revenue_change_pct REAL, n_critical INTEGER, n_warning INTEGER,
        n_watch INTEGER, headline TEXT, payload_path TEXT)""")
    return con


def record_run(payload: dict, anoms: pd.DataFrame, rated: pd.DataFrame, mode: str,
               payload_path: Path, headline: str) -> str:
    week = payload["run"]["week_start"]
    run_id = f"week_{week}"
    con = connect()
    for table in ("runs", "anomalies", "metric_snapshots"):
        try:
            con.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        except sqlite3.OperationalError:
            pass  # table not created yet
    counts = payload["anomalies"]["counts"]["risks"]
    rev = payload["kpis"]["revenue"]
    con.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        run_id, week, payload["run"]["week_end"], payload["run"]["generated_at"], mode,
        rev["current"], rev["change_pct"], counts.get("critical", 0), counts.get("warning", 0),
        counts.get("watch", 0), headline, str(payload_path.relative_to(ROOT))))

    if not anoms.empty:
        a = anoms.copy()
        a["run_id"] = run_id
        a["week_start"] = week
        a = a.reindex(columns=ANOMALY_COLS)
        a.to_sql("anomalies", con, if_exists="append", index=False)

    snap = rated[(rated["week_start"] == pd.Timestamp(week)) & (rated["sessions"] >= 100)]
    snap = snap.melt(id_vars=["dimension", "dimension_value"], value_vars=SNAPSHOT_METRICS,
                     var_name="metric", value_name="value").dropna(subset=["value"])
    snap["run_id"] = run_id
    snap["week_start"] = week
    snap.to_sql("metric_snapshots", con, if_exists="append", index=False)
    con.commit()
    con.close()
    return run_id


def load_runs() -> pd.DataFrame:
    con = connect()
    df = pd.read_sql("SELECT * FROM runs ORDER BY week_start", con)
    con.close()
    return df


def save_payload(payload: dict) -> Path:
    folder = ARTIFACTS / "payloads"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"week_{payload['run']['week_start']}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path
