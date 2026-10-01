"""Read-only access to everything the pipeline produced. Used by the app and the assistant.
The app never queries BigQuery: it reads these files, so it is fast, free and safe to host."""
import json
import os
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


class Store:
    def __init__(self, artifacts: Path = None):
        self.art = Path(artifacts or os.getenv("MIA_ARTIFACTS") or ROOT / "artifacts")
        self.payloads = {}
        for f in sorted((self.art / "payloads").glob("week_*.json")):
            p = json.loads(f.read_text())
            self.payloads[p["run"]["week_start"]] = p
        self.weeks = sorted(self.payloads)
        self.runs = self._sql("SELECT * FROM runs ORDER BY week_start")
        self.anomalies = self._sql("SELECT * FROM anomalies")
        self.snapshots = self._sql("SELECT * FROM metric_snapshots")
        self.insights = self._sql("SELECT * FROM insights")
        self.primary_model = self._primary()

    def _sql(self, query: str) -> pd.DataFrame:
        db = self.art / "intelligence.db"
        if not db.exists():
            return pd.DataFrame()
        con = sqlite3.connect(db)
        try:
            return pd.read_sql(query, con)
        except Exception:
            return pd.DataFrame()
        finally:
            con.close()

    def _primary(self):
        f = self.art / "PRIMARY_MODEL.txt"
        if f.exists() and f.read_text().strip():
            return f.read_text().strip()
        briefs = self.art / "briefs"
        dirs = sorted(d.name for d in briefs.iterdir()) if briefs.exists() else []
        if not self.insights.empty:
            return self.insights["model"].iloc[0]
        return dirs[0] if dirs else None

    def brief(self, week: str, model: str = None):
        model = model or self.primary_model
        if not model:
            return None
        f = self.art / "briefs" / slug(model) / f"week_{week}.json"
        return json.loads(f.read_text()) if f.exists() else None

    def brief_html(self, week: str, model: str = None):
        model = model or self.primary_model
        if not model:
            return None, None
        folder = self.art / "reports" / slug(model)
        html, pdf = folder / f"brief_{week}.html", folder / f"brief_{week}.pdf"
        return (html if html.exists() else None), (pdf if pdf.exists() else None)

    def eval_runs(self) -> pd.DataFrame:
        f = self.art / "eval" / "model_eval_runs.csv"
        return pd.read_csv(f) if f.exists() else pd.DataFrame()

    def nearest_week(self, text) -> str:
        """Map any date-ish input to the Monday of a week we have."""
        if not self.weeks:
            return None
        if text in self.payloads:
            return text
        try:
            d = pd.Timestamp(str(text)[:10])
            earlier = [w for w in self.weeks if pd.Timestamp(w) <= d]
            return earlier[-1] if earlier else self.weeks[0]
        except Exception:
            return self.weeks[-1]
