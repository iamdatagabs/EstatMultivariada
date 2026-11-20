from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
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
    for separator in (None, ",", ";", "\\t"):
        try:
            frame = pd.read_csv(path, sep=separator, engine="python", encoding="utf-8-sig")
            if frame.shape[1] > 1:
                return frame
        except Exception as exc:  # preserve parser diagnostics for the final error
            errors.append(str(exc))
    raise ValueError(f"Unable to read {path}: {errors}")


def profile(frame: pd.DataFrame) -> dict:
    numeric = frame.select_dtypes(include=[np.number])
    missing = frame.isna().sum()
    return {
        "rows": int(len(frame)),
        "columns": int(frame.shape[1]),
        "duplicate_rows": int(frame.duplicated().sum()),
        "missing_cells": int(missing.sum()),
        "missing_pct": round(float(frame.isna().mean().mean() * 100), 3) if frame.size else 0,
        "missing_by_column": {str(k): int(v) for k, v in missing.items()},
        "numeric_columns": numeric.columns.tolist(),
        "categorical_columns": frame.select_dtypes(exclude=[np.number]).columns.tolist(),
        "constant_numeric_columns": [c for c in numeric if numeric[c].nunique(dropna=True) <= 1],
    }


def analyze(frame: pd.DataFrame, name: str, gold: Path) -> dict:
    numeric = frame.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna(axis=1, how="all")
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]
    result = {"dataset": name, **profile(frame), "pca": None, "clustering": None, "classification": None}
    output = gold / name
    output.mkdir(parents=True, exist_ok=True)
    frame.describe(include="all").transpose().to_csv(output / "descriptive_profile.csv")
    frame.isna().sum().rename("missing_count").to_csv(output / "missingness.csv")
    if numeric.shape[1] >= 2 and len(frame) >= 3:
        imputed = SimpleImputer(strategy="median").fit_transform(numeric)
        scaled = StandardScaler().fit_transform(imputed)
        n_components = min(5, scaled.shape[0], scaled.shape[1])
        model = PCA(n_components=n_components, random_state=42)
        scores = model.fit_transform(scaled)
        columns = [f"PC{i + 1}" for i in range(n_components)]
        pd.DataFrame(scores, columns=columns).to_csv(output / "pca_scores.csv", index=False)
        pd.DataFrame(model.components_.T, index=numeric.columns, columns=columns).to_csv(output / "pca_loadings.csv")
        result["pca"] = {
            "components": int(n_components),
            "explained_variance_ratio": [round(float(v), 6) for v in model.explained_variance_ratio_],
            "cumulative_variance": round(float(model.explained_variance_ratio_.sum()), 6),
        }
        if len(scaled) >= 5:
            clusters = min(4, max(2, int(np.sqrt(len(scaled) / 2))), len(scaled) - 1)
            labels = KMeans(n_clusters=clusters, random_state=42, n_init=10).fit_predict(scaled)
            pd.DataFrame({"row_index": np.arange(len(labels)), "cluster": labels}).to_csv(
                output / "cluster_assignments.csv", index=False
            )
            silhouette = float(silhouette_score(scaled, labels)) if len(set(labels)) > 1 else None
            result["clustering"] = {
                "algorithm": "KMeans",
                "clusters": int(clusters),
                "silhouette": round(silhouette, 6) if silhouette is not None else None,
            }

    # Heuristic target selection is deliberately conservative; validate target semantics before interpretation.
    candidates = []
    for column in frame.select_dtypes(exclude=[np.number]).columns:
        counts = frame[column].dropna().value_counts()
        if 2 <= len(counts) <= min(12, max(2, len(frame) // 3)) and counts.min() >= 2:
            candidates.append((column, counts))
    if candidates and numeric.shape[1] >= 1:
        target, _ = max(candidates, key=lambda item: (len(item[1]), item[1].min()))
        mask = frame[target].notna()
        features = numeric.loc[mask]
        labels = frame.loc[mask, target].astype(str)
        folds = min(5, int(labels.value_counts().min()))
        if len(labels) >= 8 and folds >= 2 and labels.nunique() >= 2:
            estimator = make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced"),
            )
            cross_validation = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
            predictions = cross_val_predict(estimator, features, labels, cv=cross_validation)
            result["classification"] = {
                "target": target,
                "algorithm": "RandomForest",
                "cv_folds": folds,
                "accuracy": round(float(accuracy_score(labels, predictions)), 6),
                "macro_f1": round(float(f1_score(labels, predictions, average="macro")), 6),
                "n": int(len(labels)),
                "baseline_accuracy": round(float(labels.value_counts(normalize=True).max()), 6),
            }
            estimator.fit(features, labels)
            pd.DataFrame({
                "feature": features.columns,
                "importance": estimator[-1].feature_importances_,
            }).sort_values("importance", ascending=False).to_csv(output / "feature_importance.csv", index=False)
    return result


def run_pipeline(input_dir: Path, output_dir: Path, docs_data: Path | None = None) -> dict:
    bronze, silver, gold = (output_dir / layer for layer in ("bronze", "silver", "gold"))
    for folder in (bronze, silver, gold):
        folder.mkdir(parents=True, exist_ok=True)
    manifest, results = [], []
    database_path = gold / "analytics.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        for source in sorted(input_dir.glob("*.csv")):
            original = read_csv(source)
            key = slugify(source.stem)
            (bronze / source.name).write_bytes(source.read_bytes())
            clean = original.copy()
            clean.columns = [str(column).strip().replace(" ", "_") for column in clean.columns]
            for column in clean.select_dtypes(include=["object"]).columns:
                clean[column] = clean[column].map(lambda value: value.strip() if isinstance(value, str) else value)
            clean = clean.replace([np.inf, -np.inf], np.nan)
            clean.to_csv(silver / f"{key}.csv", index=False)
            clean.to_parquet(silver / f"{key}.parquet", index=False)
            connection.register("incoming_frame", clean)
            connection.execute(f'CREATE OR REPLACE TABLE "{key}" AS SELECT * FROM incoming_frame')
            connection.unregister("incoming_frame")
            manifest.append({
                "source": source.name,
                "sha256": file_hash(source),
                "rows": int(len(original)),
                "columns": int(original.shape[1]),
                "silver_csv": f"{key}.csv",
                "silver_parquet": f"{key}.parquet",
            })
            results.append(analyze(clean, key, gold))
    summary = {
        "project": "Estatística Multivariada",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_count": len(results),
        "total_rows": sum(item["rows"] for item in results),
        "datasets": results,
        "manifest": manifest,
        "storage": {"format": ["CSV", "Parquet"], "query_engine": "DuckDB"},
    }
    (gold / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (gold / "bi_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if docs_data:
        docs_data.mkdir(parents=True, exist_ok=True)
        (docs_data / "bi_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return summary
