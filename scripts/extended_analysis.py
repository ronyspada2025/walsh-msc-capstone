#!/usr/bin/env python3
"""extended_analysis.py - reproduces the Final Report analyses that
final_pipeline.py does not compute, and checks each result against the
value printed in the report.

Covers: RQ1 bootstrap CIs, permutation importance, repeated 5x5 CV,
seed-2026 holdout, per-capita re-tune; RQ2 zero-truncated negative
binomial with population offset (Table 15) with conventional /
state-clustered / t(26) / cluster-bootstrap intervals, ridge bootstrap
R2 CIs; RQ4 extended screening metrics (Table 19), full-frame
inferential logistic with clustered ORs (Table 18), aggregation-rule and
threshold sensitivity (Table 20), and the log-intensity OLS complement.

Usage (from the repository root):
    python3 scripts/extended_analysis.py
Optional: BOOT=199 python3 scripts/extended_analysis.py   (faster bootstrap)

Writes reports/tables/extended_results.json and prints PASS/DRIFT lines.
"""
import json, os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
np.random.seed(42)

BOOT = int(os.environ.get("BOOT", "999"))
TOL_AUC, TOL_COEF = 0.006, 0.03
DATA = "data/processed/merged_municipal_dataset.csv"
T26 = 2.056  # t critical, df=26

checks = []
def check(name, expected, actual, tol):
    if expected is None or actual is None:
        verdict = "INFO "
    else:
        verdict = "PASS " if abs(actual - expected) <= tol else "DRIFT"
    checks.append((verdict, name, expected, actual))
    print(f"{verdict} {name:55s} report={expected}  computed="
          f"{actual if actual is None else round(float(actual), 4)}")

# ---------------- load + clean (per Table 5 cleaning log) ----------------
print("== Loading and cleaning ==")
df0 = pd.read_csv(DATA, dtype=str)
key = "MUNICIP_ID" if "MUNICIP_ID" in df0.columns else df0.columns[0]
df0[key] = df0[key].str.zfill(7)
for c in df0.columns:
    if c != key:
        df0[c] = pd.to_numeric(df0[c], errors="ignore")
df0 = df0.drop_duplicates()          # removes the 193 exact duplicates
pre = df0.copy()                     # 9,914 rows: kept for SLP sensitivity

def col(*names):
    for n in names:
        if n in df0.columns: return n
    sys.exit(f"Column not found: {names}")

NR  = col("NR_STATION_CNT", "ERB_NR")
SLP = col("SLP_STATION_CNT")
P5G = col("PRIVATE_5G_LIC")
POP = col("POP_2024")

agg = {c: "first" for c in df0.columns if c != key}
agg[SLP] = "sum"; agg[P5G] = "max"
df = df0.groupby(key, as_index=False).agg(agg)
assert len(df) == 5571, f"expected 5571 municipalities, got {len(df)}"

if "FIBER_PER_100" not in df.columns:
    df["FIBER_PER_100"] = 100 * df[col("FIBER_ACCESSES")] / df[POP]
if "LTE_ACCESS_PER_100" not in df.columns:
    df["LTE_ACCESS_PER_100"] = 100 * df[col("ACC_LTE")] / df[POP]
df["NR_PER_100K_POP"] = 1e5 * df[NR] / df[POP]
df["SLP_PER_100K_POP"] = 1e5 * df[SLP] / df[POP]
REGION_MAP = {"1": "North", "2": "Northeast", "3": "Southeast",
              "4": "South", "5": "Center-West"}
df["REGION"] = df[key].str[0].map(REGION_MAP)
df["UF"] = df[key].str[:2]

STRUCT = ["GDP_PER_CAP", POP, "POP_DENSITY", "FIBER_PER_100", "LTE_ACCESS_PER_100"]
need = STRUCT + [NR, SLP, "REGION"]
m = df.dropna(subset=need).copy()
check("modeling frame n", 5564, len(m), 0.5)
thrN = m[NR].quantile(.75); thrPC = m["NR_PER_100K_POP"].quantile(.75)
thrS = m["SLP_PER_100K_POP"].quantile(.75)
check("P75 count threshold", 9, thrN, 0.5)
check("P75 per-100k threshold", 46.36, thrPC, 0.2)
check("SLP P75 threshold", 1618.34, thrS, 1.0)

def design(frame):
    X = frame[STRUCT].astype(float).copy()
    X = pd.concat([X, pd.get_dummies(frame["REGION"], prefix="REGION")
                        .drop(columns=["REGION_Center-West"])], axis=1)
    return X.astype(float)

X = design(m)
yN  = (m[NR] > thrN).astype(int)
yPC = (m["NR_PER_100K_POP"] > thrPC).astype(int)
yS  = (m["SLP_PER_100K_POP"] > thrS).astype(int)
yPres = (m[NR] > 0).astype(int)

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression, RidgeCV, LinearRegression
from sklearn.model_selection import (train_test_split, GridSearchCV,
    RepeatedStratifiedKFold, cross_validate)
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance
from sklearn.metrics import (roc_auc_score, f1_score, accuracy_score,
    average_precision_score, brier_score_loss, confusion_matrix,
    recall_score, precision_score, r2_score, mean_absolute_error)

RF_GRID = {"n_estimators": [100, 300], "max_depth": [None, 8, 16],
           "min_samples_leaf": [1, 5, 20]}

def boot_auc_ci(yte, p, n=1000, seed=42):
    rng = np.random.RandomState(seed); idx = np.arange(len(yte)); out = []
    yte = np.asarray(yte); p = np.asarray(p)
    while len(out) < n:
        s = rng.choice(idx, len(idx), replace=True)
        if yte[s].min() == yte[s].max(): continue
        out.append(roc_auc_score(yte[s], p[s]))
    return np.percentile(out, [2.5, 97.5])

res = {}
def rf_block(y, label, exp):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, stratify=y, random_state=42)
    gs = GridSearchCV(RandomForestClassifier(random_state=42, n_jobs=-1),
                      RF_GRID, cv=5, scoring="f1", n_jobs=-1).fit(Xtr, ytr)
    best = gs.best_params_
    p = gs.best_estimator_.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, p); lo, hi = boot_auc_ci(yte, p)
    check(f"{label} dev ROC-AUC", exp["auc"], auc, TOL_AUC)
    check(f"{label} dev CI low", exp["lo"], lo, 0.01)
    check(f"{label} dev CI high", exp["hi"], hi, 0.01)
    check(f"{label} dev F1", exp["f1"], f1_score(yte, gs.best_estimator_.predict(Xte)), 0.01)
    pi = permutation_importance(gs.best_estimator_, Xte, yte, n_repeats=20,
                                scoring="roc_auc", random_state=42)
    imp = dict(zip(X.columns, pi.importances_mean))
    if exp.get("pop_pi") is not None:
        check(f"{label} perm importance POP", exp["pop_pi"], imp[POP], 0.03)
    mdl = RandomForestClassifier(random_state=42, n_jobs=-1, **best)
    cv = cross_validate(mdl, X, y, scoring=["roc_auc", "f1"],
        cv=RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=42), n_jobs=-1)
    check(f"{label} repeated-CV AUC mean", exp["cvauc"], cv["test_roc_auc"].mean(), TOL_AUC)
    check(f"{label} repeated-CV AUC sd", exp["cvsd"], cv["test_roc_auc"].std(), 0.008)
    Xt2, Xe2, yt2, ye2 = train_test_split(X, y, test_size=.25, stratify=y, random_state=2026)
    p2 = mdl.fit(Xt2, yt2).predict_proba(Xe2)[:, 1]
    check(f"{label} seed-2026 AUC", exp["s2026"], roc_auc_score(ye2, p2), TOL_AUC)
    return {"best_params": best, "dev_auc": auc, "ci": [lo, hi],
            "perm_importance": imp, "cv_auc": [cv["test_roc_auc"].mean(),
            cv["test_roc_auc"].std()], "seed2026_auc": roc_auc_score(ye2, p2)}

print("\n== RQ1 count target ==")
res["rq1_count"] = rf_block(yN, "RQ1 count",
    dict(auc=.927, lo=.906, hi=.945, f1=.808, pop_pi=.212, cvauc=.920, cvsd=.009, s2026=.919))
print("\n== RQ1 per-capita target (re-tuned) ==")
res["rq1_percap"] = rf_block(yPC, "RQ1 per-capita",
    dict(auc=.817, lo=.790, hi=.845, f1=.593, pop_pi=None, cvauc=.824, cvsd=.017, s2026=.825))

# ---------------- RQ2 ----------------
print("\n== RQ2 truncated negative binomial (Table 15) ==")
import statsmodels.api as sm
try:
    from statsmodels.discrete.truncated_model import TruncatedLFNegativeBinomialP as TNB
except ImportError:
    sys.exit("statsmodels >= 0.14 required: python3 -m pip install -U statsmodels")

pres = m[m[NR] > 0].copy()
check("NR-present n", 2192, len(pres), 0.5)
sc = StandardScaler()
Zc = ["GDP_PER_CAP", "POP_DENSITY", "FIBER_PER_100", "LTE_ACCESS_PER_100"]
Ztr = pd.DataFrame(sc.fit_transform(pres[Zc]), columns=Zc, index=pres.index)
regd = pd.get_dummies(pres["REGION"], prefix="REGION").drop(columns=["REGION_Center-West"]).astype(float)
lpop = np.log(pres[POP].astype(float)); clpop = lpop - lpop.mean()
exog = sm.add_constant(pd.concat([Ztr, regd, clpop.rename("clogpop")], axis=1))
tnb = TNB(pres[NR].astype(float), exog, offset=lpop, truncation=0)
fit = tnb.fit(method="bfgs", maxiter=1000, disp=0)
cl  = tnb.fit(method="bfgs", maxiter=1000, disp=0,
              cov_type="cluster", cov_kwds={"groups": pres["UF"]})
alpha = float(fit.params[-1])
check("truncated NB alpha", 0.66, alpha, 0.05)
check("truncated NB McFadden R2", 0.017, 1 - fit.llf/tnb.fit(method="bfgs", maxiter=0, disp=0).llnull if hasattr(fit,'llnull') else fit.prsquared, 0.01) if hasattr(fit,'prsquared') else None
names = list(exog.columns)
def coef(nm): i = names.index(nm); return float(fit.params[i]), float(cl.bse[i])
g, gse = coef("clogpop")
check("gamma (clogpop)", -0.139, g, TOL_COEF)
for nm, expRR in [("POP_DENSITY", 1.25), ("FIBER_PER_100", 1.14), ("GDP_PER_CAP", 1.11)]:
    b, se = coef(nm)
    check(f"rate ratio {nm}", expRR, float(np.exp(b)), 0.04)
    lo_, hi_ = b - T26*se, b + T26*se
    print(f"      {nm}: t(26) clustered CI for coef [{lo_:.3f}, {hi_:.3f}]")
res["rq2_tnb"] = {"alpha": alpha, "params": dict(zip(names, map(float, fit.params[:-1]))),
                  "cluster_se": dict(zip(names, map(float, cl.bse[:-1])))}

print("\n== RQ2 cluster bootstrap (states, may take minutes) ==")
rng = np.random.RandomState(42); ufs = pres["UF"].unique(); bs = []
for _ in range(BOOT):
    pick = rng.choice(ufs, len(ufs), replace=True)
    bdf = pd.concat([pres[pres["UF"] == u] for u in pick])
    try:
        Zb = pd.DataFrame(sc.transform(bdf[Zc]), columns=Zc, index=bdf.index)
        rb = pd.get_dummies(bdf["REGION"], prefix="REGION").reindex(columns=regd.columns, fill_value=0).astype(float)
        lb = np.log(bdf[POP].astype(float))
        eb = sm.add_constant(pd.concat([Zb, rb, (lb - lpop.mean()).rename("clogpop")], axis=1))
        fb = TNB(bdf[NR].astype(float), eb, offset=lb, truncation=0).fit(
            method="bfgs", maxiter=500, disp=0)
        if fb.mle_retvals.get("converged", True): bs.append(fb.params[:-1])
    except Exception: pass
print(f"      converged replications: {len(bs)}/{BOOT}")
if bs:
    B = np.array(bs); qs = np.percentile(B, [2.5, 97.5], axis=0)
    i = names.index("POP_DENSITY")
    print(f"      POP_DENSITY cluster-bootstrap CI [{qs[0,i]:.3f}, {qs[1,i]:.3f}] (report [.149, .276])")

print("\n== RQ2 ridge with bootstrap R2 CI ==")
def ridge_block(ylab, y, expR2, expLo, expHi):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=.25, random_state=42)
    scl = StandardScaler().fit(Xtr)
    r = RidgeCV(alphas=np.logspace(-2, 3, 25)).fit(scl.transform(Xtr), ytr)
    p = r.predict(scl.transform(Xte)); r2 = r2_score(yte, p)
    rng = np.random.RandomState(42); idx = np.arange(len(yte)); rs = []
    for _ in range(1000):
        s = rng.choice(idx, len(idx), True)
        rs.append(r2_score(np.asarray(yte)[s], p[s]))
    lo, hi = np.percentile(rs, [2.5, 97.5])
    check(f"ridge R2 ({ylab})", expR2, r2, 0.02)
    check(f"ridge R2 CI low ({ylab})", expLo, lo, 0.04)
    check(f"ridge R2 CI high ({ylab})", expHi, hi, 0.04)
ridge_block("raw", m["NR_PER_100K_POP"].astype(float), .02, -.08, .09)
ridge_block("log1p", np.log1p(m["NR_PER_100K_POP"].astype(float)), .06, -.15, .18)

# ---------------- RQ4 ----------------
print("\n== RQ4 screening metrics (Table 19) ==")
Xtr, Xte, ytr, yte = train_test_split(X, yS, test_size=.25, stratify=yS, random_state=42)
scl = StandardScaler().fit(Xtr)
lr = LogisticRegression(class_weight="balanced", max_iter=5000).fit(scl.transform(Xtr), ytr)
p = lr.predict_proba(scl.transform(Xte))[:, 1]; yhat = (p >= .5).astype(int)
tn, fp, fn, tp = confusion_matrix(yte, yhat).ravel()
lo, hi = boot_auc_ci(yte, p)
check("RQ4 dev ROC-AUC", .810, roc_auc_score(yte, p), TOL_AUC)
check("RQ4 CI low", .786, lo, 0.01); check("RQ4 CI high", .836, hi, 0.01)
check("RQ4 PR-AUC", .623, average_precision_score(yte, p), 0.01)
check("RQ4 sensitivity", .753, recall_score(yte, yhat), 0.01)
check("RQ4 specificity", .713, tn/(tn+fp), 0.01)
check("RQ4 precision", .467, precision_score(yte, yhat), 0.01)
check("RQ4 F1", .576, f1_score(yte, yhat), 0.01)
check("RQ4 accuracy", .723, accuracy_score(yte, yhat), 0.01)
check("RQ4 Brier", .176, brier_score_loss(yte, p), 0.01)
check("RQ4 TP", 262, tp, 3); check("RQ4 FN", 86, fn, 3)
check("RQ4 FP", 299, fp, 3); check("RQ4 TN", 744, tn, 3)

print("\n== RQ4 inferential logistic, full frame (Table 18) ==")
Zall = pd.DataFrame(StandardScaler().fit_transform(X), columns=X.columns, index=X.index)
ex = sm.add_constant(Zall)
lg = sm.Logit(yS, ex).fit(disp=0)
lgc = sm.Logit(yS, ex).fit(disp=0, cov_type="cluster", cov_kwds={"groups": m["UF"]})
check("RQ4 McFadden R2", .196, lg.prsquared, 0.01)
for nm, expB, expOR in [("GDP_PER_CAP", .965, 2.62), (POP, .516, 1.68),
        ("LTE_ACCESS_PER_100", .373, 1.45), ("FIBER_PER_100", .229, 1.26),
        ("REGION_Northeast", -.548, 0.58)]:
    b = float(lg.params[nm]); se = float(lgc.bse[nm])
    check(f"RQ4 beta {nm}", expB, b, TOL_COEF)
    print(f"      OR={np.exp(b):.2f} (report {expOR}); t(26) CI "
          f"[{np.exp(b-T26*se):.2f}, {np.exp(b+T26*se):.2f}]")

print("\n== RQ4 aggregation + threshold sensitivity (Table 20) ==")
rules = {"sum": "sum", "max": "max", "mean": "mean", "first": "first"}
base_targets = None
for rname, r in rules.items():
    s = pre.groupby(key)[SLP].agg(r).reindex(m[key]).values.astype(float)
    per = 1e5 * s / m[POP].values.astype(float)
    thr = np.nanquantile(per, .75)
    yv = (per > thr).astype(int)
    if rname == "sum": base_targets = yv
    agree = (yv == base_targets).mean()
    Xt, Xe, yt, ye = train_test_split(X, yv, test_size=.25, stratify=yv, random_state=42)
    s2 = StandardScaler().fit(Xt)
    a = roc_auc_score(ye, LogisticRegression(class_weight="balanced", max_iter=5000)
                      .fit(s2.transform(Xt), yt).predict_proba(s2.transform(Xe))[:, 1])
    orgdp = float(np.exp(sm.Logit(yv, ex).fit(disp=0).params["GDP_PER_CAP"]))
    print(f"   {rname:6s} thr={thr:7.0f} agree={agree:6.1%} AUC={a:.3f} OR_GDP={orgdp:.2f}")
print("   (report Table 20: thresholds 1618/1283/903/1126; AUC .810/.777/.789/.779; OR 2.62/2.49/2.64/2.21)")

print("\n== RQ4 log-intensity OLS complement ==")
yl = np.log1p(m["SLP_PER_100K_POP"].astype(float))
ols = sm.OLS(yl, ex).fit(cov_type="cluster", cov_kwds={"groups": m["UF"]})
check("RQ4 OLS R2", .244, ols.rsquared, 0.01)

# ---------------- summary ----------------
os.makedirs("reports/tables", exist_ok=True)
res["checks"] = [{"verdict": v, "name": n, "report": e,
                  "computed": None if a is None else float(a)} for v, n, e, a in checks]
json.dump(res, open("reports/tables/extended_results.json", "w"), indent=2, default=float)
npass = sum(1 for v, *_ in checks if v == "PASS ")
ndrift = sum(1 for v, *_ in checks if v == "DRIFT")
print(f"\n===== EXTENDED ANALYSIS SUMMARY: PASS={npass} DRIFT={ndrift} "
      f"(of {len(checks)} checks) =====")
print("Wrote reports/tables/extended_results.json")
if ndrift:
    print("DRIFT lines above show where the computed value differs from the "
          "report beyond tolerance - send the full output for interpretation.")
