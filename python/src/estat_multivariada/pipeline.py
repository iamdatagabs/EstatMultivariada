from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path
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
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def read_csv(path: Path) -> pd.DataFrame:
    errors = []
    for sep in (None, ",", ";", "\\t"):
        try:
            df = pd.read_csv(path, sep=sep, engine="python", encoding="utf-8-sig")
            if df.shape[1] > 1: return df
        except Exception as exc: errors.append(str(exc))
    raise ValueError(f"Unable to read {path}: {errors}")

def profile(df: pd.DataFrame) -> dict:
    return {"rows": int(len(df)), "columns": int(df.shape[1]),
            "duplicate_rows": int(df.duplicated().sum()),
            "missing_cells": int(df.isna().sum().sum()),
            "missing_pct": round(float(df.isna().mean().mean()*100), 3) if df.size else 0,
            "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
            "categorical_columns": df.select_dtypes(exclude=[np.number]).columns.tolist()}

def analyze(df: pd.DataFrame, name: str, gold: Path) -> dict:
    numeric = df.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all")
    result = {"dataset":name, **profile(df), "pca":None, "clustering":None, "classification":None}
    out = gold/name; out.mkdir(parents=True, exist_ok=True)
    df.describe(include="all").transpose().to_csv(out/"descriptive_profile.csv")
    df.isna().sum().rename("missing_count").to_csv(out/"missingness.csv")
    if numeric.shape[1] >= 2 and len(df) >= 3:
        x = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(numeric))
        ncomp = min(5, x.shape[0], x.shape[1])
        model = PCA(n_components=ncomp, random_state=42)
        scores = model.fit_transform(x)
        pd.DataFrame(scores, columns=[f"PC{i+1}" for i in range(ncomp)]).to_csv(out/"pca_scores.csv", index=False)
        pd.DataFrame(model.components_.T, index=numeric.columns, columns=[f"PC{i+1}" for i in range(ncomp)]).to_csv(out/"pca_loadings.csv")
        result["pca"]={"components":int(ncomp),"explained_variance_ratio":[round(float(v),6) for v in model.explained_variance_ratio_],"cumulative_variance":round(float(model.explained_variance_ratio_.sum()),6)}
        if len(df) >= 5:
            k=min(4,max(2,int(np.sqrt(len(df)/2))),len(df)-1)
            labels=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(x)
            pd.DataFrame({"cluster":labels}).to_csv(out/"cluster_assignments.csv",index=False)
            sil=float(silhouette_score(x,labels)) if len(set(labels))>1 and len(df)>k else None
            result["clustering"]={"algorithm":"KMeans","clusters":int(k),"silhouette":round(sil,6) if sil is not None else None}
    # Categorical target candidate: low cardinality, repeated classes, no ID-like columns.
    candidates=[]
    for col in df.select_dtypes(exclude=[np.number]).columns:
        counts=df[col].dropna().value_counts()
        if 2 <= len(counts) <= min(12,max(2,len(df)//3)) and counts.min()>=2:
            candidates.append((col,counts))
    if candidates and numeric.shape[1]>=1:
        target,counts=max(candidates,key=lambda item:(len(item[1]),item[1].min()))
        mask=df[target].notna(); features=numeric.loc[mask]; y=df.loc[mask,target].astype(str)
        folds=min(5,int(y.value_counts().min()))
        if len(y)>=8 and folds>=2 and y.nunique()>=2:
            estimator=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),RandomForestClassifier(n_estimators=200,random_state=42,class_weight="balanced"))
            cv=StratifiedKFold(n_splits=folds,shuffle=True,random_state=42)
            pred=cross_val_predict(estimator,features,y,cv=cv)
            result["classification"]={"target":target,"algorithm":"RandomForest","cv_folds":folds,"accuracy":round(float(accuracy_score(y,pred)),6),"macro_f1":round(float(f1_score(y,pred,average="macro")),6),"n":int(len(y))}
            estimator.fit(features,y)
            pd.DataFrame({"feature":features.columns,"importance":estimator[-1].feature_importances_}).sort_values("importance",ascending=False).to_csv(out/"feature_importance.csv",index=False)
    return result

def run_pipeline(input_dir: Path, output_dir: Path, docs_data: Path|None=None) -> dict:
    bronze, silver, gold=(output_dir/x for x in ("bronze","silver","gold"))
    for folder in (bronze,silver,gold): folder.mkdir(parents=True,exist_ok=True)
    manifest=[]; results=[]
    for source in sorted(input_dir.glob("*.csv")):
        df=read_csv(source); key=slugify(source.stem)
        (bronze/source.name).write_bytes(source.read_bytes())
        clean=df.copy(); clean.columns=[str(c).strip().replace(" ","_") for c in clean.columns]
        for col in clean.select_dtypes(include=["object"]).columns:
            clean[col]=clean[col].map(lambda v:v.strip() if isinstance(v,str) else v)
        clean.to_csv(silver/f"{key}.csv",index=False)
        manifest.append({"source":source.name,"sha256":file_hash(source),"rows":int(len(df)),"columns":int(df.shape[1]),"silver_file":f"{key}.csv"})
        results.append(analyze(clean,key,gold))
    summary={"project":"Estatística Multivariada","generated_at":datetime.now(timezone.utc).isoformat(),"dataset_count":len(results),"total_rows":sum(x["rows"] for x in results),"datasets":results,"manifest":manifest}
    (gold/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (gold/"bi_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    if docs_data:
        docs_data.mkdir(parents=True,exist_ok=True)
        (docs_data/"bi_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary
