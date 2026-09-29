"""BigQuery helpers shared by every script. One place to change the data source."""
import os

from google.cloud import bigquery

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional (e.g. in Colab)
    pass

PUBLIC_SAMPLE = "bigquery-public-data.ga4_obfuscated_sample_ecommerce"


def settings() -> dict:
    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        raise SystemExit("Set GCP_PROJECT_ID (in .env or os.environ) before running.")
    return {
        "project": project,
        "dataset": os.getenv("BQ_DATASET", "mia"),
        "location": os.getenv("BQ_LOCATION", "US"),
        "source": os.getenv("GA4_SOURCE", PUBLIC_SAMPLE),
        "start": os.getenv("START_DATE", "20201101"),
        "end": os.getenv("END_DATE", "20210131"),
    }


def get_client(cfg: dict) -> bigquery.Client:
    return bigquery.Client(project=cfg["project"])


def ensure_dataset(client: bigquery.Client, cfg: dict) -> None:
    # Must match the source location (the public sample lives in US)
    ds = bigquery.Dataset(f"{cfg['project']}.{cfg['dataset']}")
    ds.location = cfg["location"]
    client.create_dataset(ds, exists_ok=True)


def render_sql(sql: str, cfg: dict) -> str:
    for key in ("project", "dataset", "source", "start", "end"):
        sql = sql.replace("{" + key + "}", cfg[key])
    return sql


def query_df(client: bigquery.Client, sql: str):
    return client.query(sql).to_dataframe()
