import pandas as pd
from estat_multivariada.pipeline import profile, slugify, run_pipeline


def test_slugify():
    assert slugify("Euroemp.csv") == "euroemp_csv"


def test_profile():
    result = profile(pd.DataFrame({"x": [1, 1, None], "group": ["a", "a", "b"]}))
    assert result["rows"] == 3
    assert result["duplicate_rows"] == 1
    assert result["missing_cells"] == 1


def test_pipeline_writes_bronze_silver_gold_and_duckdb(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    pd.DataFrame({
        "segment": ["a", "a", "b", "b", "c", "c"],
        "x": [1, 2, 8, 9, 4, 5],
        "y": [2, 1, 9, 8, 4, 6],
    }).to_csv(source / "sample.csv", index=False)
    output = tmp_path / "warehouse"
    docs = tmp_path / "docs" / "data"
    result = run_pipeline(source, output, docs)
    assert result["dataset_count"] == 1
    assert (output / "bronze" / "sample.csv").exists()
    assert (output / "silver" / "sample.parquet").exists()
    assert (output / "gold" / "analytics.duckdb").exists()
    assert (docs / "bi_summary.json").exists()
