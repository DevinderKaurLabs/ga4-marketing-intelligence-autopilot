"""Build the GA4 analytics layer in BigQuery: runs sql/02_models/*.sql in order."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mia.bq import ensure_dataset, get_client, render_sql, settings  # noqa: E402


def main() -> None:
    cfg = settings()
    client = get_client(cfg)
    ensure_dataset(client, cfg)
    total_gb = 0.0
    for path in sorted((ROOT / "sql" / "02_models").glob("*.sql")):
        started = time.time()
        job = client.query(render_sql(path.read_text(), cfg))
        job.result()
        gb = (job.total_bytes_processed or 0) / 1e9
        total_gb += gb
        print(f"OK  {path.name:34s} {time.time() - started:6.1f}s {gb:7.2f} GB scanned")
    print(f"\nDone. {total_gb:.2f} GB scanned in total (free tier: 1 TB/month).")
    print(f"Tables are in {cfg['project']}.{cfg['dataset']}")


if __name__ == "__main__":
    main()
