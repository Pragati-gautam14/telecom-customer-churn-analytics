"""Raw CSV -> DuckDB SQL models -> outputs/tables + powerbi/.  Run: python src/run_pipeline.py"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "telco_customer_churn.csv"
DB = ROOT / "data" / "churn.duckdb"
OUT = ROOT / "outputs" / "tables"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    con.execute(f"CREATE OR REPLACE TABLE raw_churn AS SELECT * FROM read_csv_auto('{RAW.as_posix()}', all_varchar=false)")
    for f in sorted((ROOT / "sql").glob("*.sql")):
        print("running", f.name)
        con.execute(f.read_text(encoding="utf-8"))
    for t in ["data_quality_log", "headline_kpis", "churn_by_dimension", "risk_matrix", "top_risk_segments"]:
        con.table(t).df().to_csv(OUT / f"{t}.csv", index=False)
    con.table("customers").df().to_csv(ROOT / "powerbi" / "customers_clean.csv", index=False)
    con.close()


if __name__ == "__main__":
    main()
