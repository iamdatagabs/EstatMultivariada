import pandas as pd
import duckdb

from estat_multivariada.pipeline import (
    normalize, profile, slugify, validate_contract, load_config, run_pipeline
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


def test_config_lists_all_repository_datasets():
    config = load_config(__import__("pathlib").Path("config/datasets.yml"))
    assert len(config["datasets"]) == 8
    assert {item["file"] for item in config["datasets"]} >= {"Road_distances_NZ.csv", "Voting_NJ_Congressmen.csv"}


def test_pipeline_builds_warehouse_and_bi_artifacts(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({
        "segment": ["a", "a", "a", "b", "b", "b", "c", "c", "c"],
        "x": [1, 2, 3, 8, 9, 10, 4, 5, 6],
        "y": [2, 1, 3, 9, 8, 10, 5, 4, 6],
    }).to_csv(raw / "sample.csv", index=False)
    config = tmp_path / "datasets.yml"
    config.write_text(
        "version: 1\ndatasets:\n  - file: sample.csv\n    contract:\n      fail_on_error: true\n",
        encoding="utf-8",
    )
    output, docs = tmp_path / "warehouse", tmp_path / "docs" / "data"
    result = run_pipeline(raw, output, docs, config)
    assert result["dataset_count"] == 1
    assert (output / "bronze" / "sample.csv").exists()
    assert (output / "silver" / "sample.parquet").exists()
    assert (output / "gold" / "bi_summary.json").exists()
    assert (docs / "bi_summary.json").exists()
    with duckdb.connect(str(output / "gold" / "analytics.duckdb"), read_only=True) as con:
        assert con.execute("select count(*) from silver_sample").fetchone()[0] == 9
        assert con.execute("select count(*) from bi_dataset_quality").fetchone()[0] == 1
