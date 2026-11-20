from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def slugify(value: str) -> str:
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    errors = []
    for separator in (None, ",", ";", "\t"):
        try:
            frame = pd.read_csv(path, sep=separator, engine="python", encoding="utf-8-sig")
            if frame.shape[1] > 1:
                return frame
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError(f"Unable to read {path}: {errors}")


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Dataset configuration not found: {path}")
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config.get("datasets"), list):
        raise ValueError("Configuration must define a 'datasets' list")
    files = [item.get("file") for item in config["datasets"]]
    if any(not value for value in files) or len(files) != len(set(files)):
        raise ValueError("Every dataset must have a unique, non-empty file entry")
    return config


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.copy()
    clean.columns = [str(c).strip().replace(" ", "_") for c in clean.columns]
    if clean.columns.duplicated().any():
        duplicates = clean.columns[clean.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate column names after normalization: {duplicates}")
    for column in clean.select_dtypes(include=["object", "string"]).columns:
        clean[column] = clean[column].map(lambda value: value.strip() if isinstance(value, str) else value)
    return clean.replace([np.inf, -np.inf], np.nan)


def profile(frame: pd.DataFrame) -> dict:
    numeric = frame.select_dtypes(include=[np.number])
    missing = frame.isna().sum()
    return {
        "rows": int(len(frame)), "columns": int(frame.shape[1]),
        "duplicate_rows": int(frame.duplicated().sum()), "missing_cells": int(missing.sum()),
        "missing_pct": round(float(frame.isna().mean().mean() * 100), 3) if frame.size else 0,
        "missing_by_column": {str(key): int(value) for key, value in missing.items()},
        "numeric_columns": numeric.columns.tolist(),
        "categorical_columns": frame.select_dtypes(exclude=[np.number]).columns.tolist(),
        "constant_numeric_columns": [column for column in numeric if numeric[column].nunique(dropna=True) <= 1],
    }


def validate_contract(frame: pd.DataFrame, contract: dict) -> list[dict]:
    issues = []
    for column in contract.get("required_columns", []):
        if column not in frame:
            issues.append({"severity": "error", "rule": "required_column", "column": column,
                           "message": f"Required column '{column}' is missing"})
    for column in contract.get("not_null", []):
        if column in frame and frame[column].isna().any():
            issues.append({"severity": "error", "rule": "not_null", "column": column,
                           "count": int(frame[column].isna().sum()), "message": "Null values are not allowed"})
    for column in contract.get("unique", []):
        if column in frame and frame[column].duplicated().any():
            issues.append({"severity": "error", "rule": "unique", "column": column,
                           "count": int(frame[column].duplicated().sum()), "message": "Values must be unique"})
    for column, accepted in contract.get("accepted_values", {}).items():
        if column in frame:
            invalid = frame[column].dropna().loc[lambda values: ~values.isin(accepted)]
            if not invalid.empty:
                issues.append({"severity": "error", "rule": "accepted_values", "column": column,
                               "count": int(len(invalid)), "message": "Values outside configured domain"})
    return issues


def analyze(frame: pd.DataFrame, name: str, gold: Path, model_config: dict | None = None) -> dict:
    numeric = frame.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna(axis=1, how="all")
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]
    result = {"dataset": name, **profile(frame), "pca": None, "clustering": None, "classification": None}
    output = gold / name
    output.mkdir(parents=True, exist_ok=True)
    frame.describe(include="all").transpose().to_csv(output / "descriptive_profile.csv")
    frame.isna().sum().rename("missing_count").to_csv(output / "missingness.csv")
    if numeric.shape[1] >= 2 and len(frame) >= 3:
        scaled = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(numeric))
        components = min(5, scaled.shape[0], scaled.shape[1])
        pca = PCA(n_components=components, random_state=42)
        scores = pca.fit_transform(scaled)
        names = [f"PC{i + 1}" for i in range(components)]
        pd.DataFrame(scores, columns=names).to_csv(output / "pca_scores.csv", index=False)
        pd.DataFrame(pca.components_.T, index=numeric.columns, columns=names).to_csv(output / "pca_loadings.csv")
        result["pca"] = {"components": int(components),
                         "explained_variance_ratio": [round(float(value), 6) for value in pca.explained_variance_ratio_],
                         "cumulative_variance": round(float(pca.explained_variance_ratio_.sum()), 6)}
        if len(scaled) >= 5:
            k = min(4, max(2, int(np.sqrt(len(scaled) / 2))), len(scaled) - 1)
            labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(scaled)
            pd.DataFrame({"row_index": np.arange(len(labels)), "cluster": labels}).to_csv(
                output / "cluster_assignments.csv", index=False)
            silhouette = float(silhouette_score(scaled, labels)) if len(set(labels)) > 1 else None
            result["clustering"] = {"algorithm": "KMeans", "clusters": int(k),
                                    "silhouette": round(silhouette, 6) if silhouette is not None else None}
    target = (model_config or {}).get("target")
    if target:
        if target not in frame.columns:
            raise ValueError(f"Configured ML target '{target}' does not exist in {name}")
        excluded = set((model_config or {}).get("exclude_features", [])) | {target}
        features = frame.select_dtypes(include=[np.number]).drop(columns=list(excluded & set(frame.columns)))
        labels = frame[target]
        mask = labels.notna()
        features, labels = features.loc[mask], labels.loc[mask].astype(str)
        folds = min(5, int(labels.value_counts().min())) if len(labels) else 0
        if features.shape[1] == 0 or len(labels) < 8 or labels.nunique() < 2 or folds < 2:
            raise ValueError(f"Insufficient data for configured classification target '{target}' in {name}")
        estimator = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                  RandomForestClassifier(n_estimators=300, random_state=42,
                                                         class_weight="balanced"))
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        predictions = cross_val_predict(estimator, features, labels, cv=cv)
        metrics = {"target": target, "algorithm": "RandomForest", "cv_folds": folds,
                   "accuracy": round(float(accuracy_score(labels, predictions)), 6),
                   "macro_f1": round(float(f1_score(labels, predictions, average="macro")), 6),
                   "n": int(len(labels)), "baseline_accuracy": round(float(labels.value_counts(normalize=True).max()), 6)}
        result["classification"] = metrics
        estimator.fit(features, labels)
        importance = pd.DataFrame({"feature": features.columns, "importance": estimator[-1].feature_importances_})
        importance.sort_values("importance", ascending=False).to_csv(output / "feature_importance.csv", index=False)
        import mlflow
        mlflow.set_tracking_uri(f"file:{(gold.parent / 'mlruns').resolve()}")
        mlflow.set_experiment(f"estat-multivariada-{name}")
        with mlflow.start_run(run_name="random-forest-stratified-cv"):
            mlflow.log_params({"target": target, "algorithm": "RandomForest", "cv_folds": folds, "n": len(labels)})
            mlflow.log_metrics({key: metrics[key] for key in ("accuracy", "macro_f1", "baseline_accuracy")})
            mlflow.log_artifact(str(output / "feature_importance.csv"))
    return result


def run_pipeline(input_dir: Path, output_dir: Path, docs_data: Path | None = None,
                 config_path: Path = Path("config/datasets.yml")) -> dict:
    config = load_config(config_path)
    bronze, silver, gold = (output_dir / layer for layer in ("bronze", "silver", "gold"))
    for folder in (bronze, silver, gold):
        folder.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest, results, quality_rows, dataset_rows = [], [], [], []
    database_path = gold / "analytics.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        for item in config["datasets"]:
            source = input_dir / item["file"]
            if not source.exists():
                raise FileNotFoundError(f"Configured source not found: {source}")
            name = slugify(Path(item["file"]).stem)
            original = read_csv(source)
            clean = normalize(original)
            issues = validate_contract(clean, item.get("contract", {}))
            quality = {"run_id": run_id, "dataset_key": name, "rows": len(clean),
                       "missing_cells": int(clean.isna().sum().sum()),
                       "duplicate_rows": int(clean.duplicated().sum()),
                       "error_count": sum(issue["severity"] == "error" for issue in issues)}
            quality_rows.append(quality)
            if issues and item.get("contract", {}).get("fail_on_error", True):
                raise ValueError(f"Data contract failed for {source.name}: {json.dumps(issues, ensure_ascii=False)}")
            (bronze / source.name).write_bytes(source.read_bytes())
            clean.to_csv(silver / f"{name}.csv", index=False)
            clean.to_parquet(silver / f"{name}.parquet", index=False)
            table = f"silver_{name}"
            connection.register("incoming_frame", clean)
            connection.execute(f'CREATE OR REPLACE TABLE "{table}" AS SELECT * FROM incoming_frame')
            connection.unregister("incoming_frame")
            manifest.append({"source": source.name, "sha256": file_hash(source), "rows": len(original),
                             "columns": original.shape[1], "silver_csv": f"{name}.csv",
                             "silver_parquet": f"{name}.parquet", "duckdb_table": table,
                             "quality_issues": issues})
            dataset_rows.append({"dataset_key": name, "source_file": source.name,
                                 "row_count": len(clean), "column_count": clean.shape[1]})
            results.append(analyze(clean, name, gold, item.get("model", {})))
        connection.register("dataset_rows_df", pd.DataFrame(dataset_rows))
        connection.register("quality_rows_df", pd.DataFrame(quality_rows))
        connection.execute("CREATE OR REPLACE TABLE dim_dataset AS SELECT * FROM dataset_rows_df")
        connection.execute("CREATE OR REPLACE TABLE fact_data_quality AS SELECT * FROM quality_rows_df")
        connection.unregister("dataset_rows_df")
        connection.unregister("quality_rows_df")
        connection.execute("CREATE OR REPLACE TABLE dim_run AS SELECT ? AS run_id, ?::TIMESTAMP AS generated_at",
                           [run_id, datetime.now(timezone.utc).replace(tzinfo=None)])
        connection.execute("""CREATE OR REPLACE VIEW bi_dataset_quality AS
            SELECT d.dataset_key, d.source_file, d.row_count, d.column_count,
                   q.missing_cells, q.duplicate_rows, q.error_count, q.run_id
            FROM dim_dataset d JOIN fact_data_quality q USING(dataset_key)""")
    summary = {"project": "Estatística Multivariada", "run_id": run_id,
               "generated_at": datetime.now(timezone.utc).isoformat(), "dataset_count": len(results),
               "total_rows": sum(item["rows"] for item in results), "datasets": results,
               "manifest": manifest, "quality": quality_rows,
               "storage": {"formats": ["CSV", "Parquet"], "query_engine": "DuckDB",
                           "warehouse": str(database_path),
                           "model": ["dim_dataset", "dim_run", "fact_data_quality", "bi_dataset_quality"]}}
    (gold / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (gold / "bi_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if docs_data:
        docs_data.mkdir(parents=True, exist_ok=True)
        (docs_data / "bi_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
