import pandas as pd
import pytest

from estat_multivariada.pipeline import (
    normalize, profile, slugify, validate_contract, load_config
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
    issues = validate_contract(frame, {"required_columns": ["id", "target"],
                                       "not_null": ["id"]})
    assert {issue["rule"] for issue in issues} == {"required_column", "not_null"}


def test_contract_detects_duplicate_key_and_domain():
    frame = pd.DataFrame({"id": [1, 1], "status": ["ok", "bad"]})
    issues = validate_contract(frame, {"unique": ["id"],
                                       "accepted_values": {"status": ["ok"]}})
    assert {issue["rule"] for issue in issues} == {"unique", "accepted_values"}


def test_config_is_explicit_and_disables_implicit_targets():
    config = load_config(__import__("pathlib").Path("config/datasets.yml"))
    assert len(config["datasets"]) >= 1
    assert all("model" not in item or not item["model"].get("target") for item in config["datasets"])
