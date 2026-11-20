import json
from pathlib import Path

import duckdb
import pandas as pd

from estat_multivariada.pipeline import (
    load_config, normalize, profile, run_pipeline, slugify, validate_contract
)


def test_slugify():
    assert slugify("Euroemp.csv") == "euroemp_csv"


def test_profile():
    result = profile(pd.DataFrame({"x": [1, 1, None], "group": ["a", "a", "b"]}))
    assert result["rows"] == 3
    assert result["duplicate_rows"] == 1
    assert result["missing_cells"] == 1


def test_normalize_strips_headers_and_values():
    result = normalize(pd.DataFrame({" feature one ": [" x ", None]}))
    assert list(result.columns) == ["feature_one"]
    assert result.iloc[0, 0] == "x"


def test_contract_detects_missing_required_and_nulls():
    frame = pd.DataFrame({"id": [1, None]})
    issues = validate_contract(frame, {"required_columns": ["id", "target"], "not_null": ["id"]})
    assert {issue["rule"] for issue in issues} == {"required_column", "not_null"}


def test_contract_detects_duplicate_key_and_domain():
    frame = pd.DataFrame({"id": [1, 1], "status": ["ok", "bad"]})
    issues = validate_contract(frame, {"unique": ["id"], "accepted_values": {"status": ["ok"]}})
    assert {issue["rule"] for issue in issues} == {"unique", "accepted_values"}


def test_config_has_no_implicit_model_targets():
    config = load_config(Path("config/datasets.yml"))
    assert len(config["datasets"]) >= 1
    assert all(not item.get("model", {}).get("target") for item in config["datasets"])


def test_end_to_end_builds_parquet_and_dimensional_warehouse(tmp_path):
    source = tmp_path / "raw"
    output = tmp_path / "data"
    docs = tmp_path / "docs"
    source.mkdir()
    pd.DataFrame({"measure_a": [1, 2, 3, 4], "measure_b": [4, 3, 2, 1],
                  "group": ["a", "a", "b", "b"]}).to_csv(source / "sample.csv", index=False)
    config = tmp_path / "datasets.yml"
    config.write_text("version: 1\ndatasets:\n  - file: sample.csv\n    contract: {fail_on_error: true}\n",
                      encoding="utf-8")

    summary = run_pipeline(source, output, docs, config)

    assert summary["dataset_count"] == 1
    assert (output / "silver" / "sample.parquet").exists()
    assert json.loads((docs / "bi_summary.json").read_text())["run_id"] == summary["run_id"]
    with duckdb.connect(str(output / "gold" / "analytics.duckdb"), read_only=True) as connection:
        assert connection.sql("SELECT count(*) FROM silver_sample").fetchone()[0] == 4
        assert connection.sql("SELECT count(*) FROM dim_dataset").fetchone()[0] == 1
        assert connection.sql("SELECT count(*) FROM fact_data_quality").fetchone()[0] == 1
        assert connection.sql("SELECT count(*) FROM bi_dataset_quality").fetchone()[0] == 1
