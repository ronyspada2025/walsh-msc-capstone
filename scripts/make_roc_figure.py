#!/usr/bin/env python3
"""Generate the recommended ROC-curve figure (Figure 12: Visual Evidence).

Plots held-out ROC curves for the three reported classifiers on the seed-42
development split used throughout the Final Report:
  - RQ1 random forest, count target (reported AUC .927)
  - RQ1 random forest, per-capita target, re-tuned (reported AUC .817)
  - RQ4 balanced logistic, HIGH_SLP target (reported AUC .810)

IMPORTANT: this script rebuilds targets/features from the committed merged
dataset following the report's documented definitions. Before inserting the
figure into the report, CONFIRM that the AUCs it prints match the reported
values above (within ~.005). If they do not, your local pipeline differs from
the report configuration - reconcile with final_pipeline.py first (which is
the authoritative implementation) or adapt this script to import from it.

Usage: python scripts/make_roc_figure.py
Output: reports/figures/figure12_roc_curves.png
"""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, roc_auc_score

SEED = 42
DATA = "data/processed/merged_municipal_dataset.csv"  # committed input
REGION_MAP = {"1": "North", "2": "Northeast", "3": "Southeast", "4": "South", "5": "Center-West"}

def load_frame():
    df = pd.read_csv(DATA, dtype={"MUNICIP_ID": str})
    # Collapse to one row per municipality following the report's cleaning log:
    df = df.drop_duplicates()
    agg = {c: "first" for c in df.columns if c != "MUNICIP_ID"}
    if "SLP_STATION_CNT" in agg: agg["SLP_STATION_CNT"] = "sum"
    if "PRIVATE_5G_LIC" in agg: agg["PRIVATE_5G_LIC"] = "max"
    df = df.groupby("MUNICIP_ID", as_index=False).agg(agg)
    # Feature engineering per the data dictionary:
    if "ERB_NR" in df.columns and "NR_STATION_CNT" not in df.columns:
        df = df.rename(columns={"ERB_NR": "NR_STATION_CNT"})
    df["NR_PER_100K_POP"] = 1e5 * df["NR_STATION_CNT"] / df["POP_2024"]
    df["SLP_PER_100K_POP"] = 1e5 * df["SLP_STATION_CNT"] / df["POP_2024"]
    df["REGION"] = df["MUNICIP_ID"].str[0].map(REGION_MAP)
    return df

def structural_X(df):
    X = df[["GDP_PER_CAP", "POP_2024", "POP_DENSITY", "FIBER_PER_100", "LTE_ACCESS_PER_100"]].copy()
    X = pd.concat([X, pd.get_dummies(df["REGION"], prefix="REGION", drop_first=True)], axis=1)
    return X

RF_GRID = {"n_estimators": [200, 400], "max_depth": [None, 8, 16], "min_samples_leaf": [1, 5, 20]}

def rf_curve(X, y, label):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
    gs = GridSearchCV(RandomForestClassifier(random_state=SEED, n_jobs=-1),
                      RF_GRID, cv=5, scoring="f1", n_jobs=-1).fit(Xtr, ytr)
    p = gs.best_estimator_.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, p)
    fpr, tpr, _ = roc_curve(yte, p)
    print(f"{label}: held-out AUC = {auc:.3f}  (best params: {gs.best_params_})")
    return fpr, tpr, auc

def logit_curve(X, y, label):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
    sc = StandardScaler().fit(Xtr)
    m = LogisticRegression(class_weight="balanced", max_iter=5000).fit(sc.transform(Xtr), ytr)
    p = m.predict_proba(sc.transform(Xte))[:, 1]
    auc = roc_auc_score(yte, p)
    fpr, tpr, _ = roc_curve(yte, p)
    print(f"{label}: held-out AUC = {auc:.3f}")
    return fpr, tpr, auc

def main():
    df = load_frame().dropna(subset=["GDP_PER_CAP", "POP_2024", "POP_DENSITY",
                                     "FIBER_PER_100", "LTE_ACCESS_PER_100",
                                     "NR_STATION_CNT", "SLP_STATION_CNT"])
    X = structural_X(df)
    curves = []
    y1 = (df["NR_STATION_CNT"] > df["NR_STATION_CNT"].quantile(.75)).astype(int)
    curves.append((*rf_curve(X, y1, "RQ1 count target (report: .927)"), "RQ1 random forest, count target"))
    y2 = (df["NR_PER_100K_POP"] > df["NR_PER_100K_POP"].quantile(.75)).astype(int)
    curves.append((*rf_curve(X, y2, "RQ1 per-capita target (report: .817)"), "RQ1 random forest, per-capita target"))
    y3 = (df["SLP_PER_100K_POP"] > df["SLP_PER_100K_POP"].quantile(.75)).astype(int)
    curves.append((*logit_curve(X, y3, "RQ4 HIGH_SLP (report: .810)"), "RQ4 balanced logistic (exploratory)"))

    fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=200)
    for fpr, tpr, auc, name in curves:
        ax.plot(fpr, tpr, lw=2, label=f"{name} (AUC = {auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, label="Chance (AUC = .500)")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("Held-Out ROC Curves for the Reported Classifiers (Seed-42 Development Split)")
    ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout()
    out = "reports/figures/figure12_roc_curves.png"
    fig.savefig(out)
    print(f"\nSaved {out}")
    print("Insert as Figure 12 in the Visual Evidence subsection ONLY if the "
          "printed AUCs match the report within ~.005.")

if __name__ == "__main__":
    main()
