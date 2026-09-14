#!/usr/bin/env python3
"""Compare a fresh pipeline run against the values printed in the Final Report.

Usage:
    python scripts/compare_headline_results.py [path/to/headline_results.json]

Default path: reports/tables/headline_results.json (written by final_pipeline.py).

The script walks scripts/expected_results.json, tries to find each expected
numeric value inside the actual results file (by exact key, then by
case-insensitive substring match on flattened keys), and reports:
  MATCH    |actual - expected| <= tolerance
  DRIFT    difference above tolerance  -> investigate before submission
  MISSING  expected key not found in the actual output (naming differences
           are likely; match manually and re-run with --map key=actual.path)

Exit code is 0 only if there are no DRIFT results, so it can gate CI.
"""
import json, math, sys, argparse

def flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{prefix}{k}." if not isinstance(v,(int,float)) else f"{prefix}{k}"))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[f"{prefix}{k}"] = float(v)
    elif isinstance(d, list):
        for i, v in enumerate(d):
            if isinstance(v, (int, float)):
                out[f"{prefix}{i}"] = float(v)
            else:
                out.update(flatten(v, f"{prefix}{i}."))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("actual", nargs="?", default="reports/tables/headline_results.json")
    ap.add_argument("--expected", default="scripts/expected_results.json")
    ap.add_argument("--map", action="append", default=[],
                    help="manual mapping expected_key=actual_flat_key (repeatable)")
    args = ap.parse_args()

    with open(args.expected) as f: exp = json.load(f)
    with open(args.actual) as f: act = json.load(f)

    tol_default = exp.get("_meta", {}).get("tolerance_default", 0.005)
    manual = dict(m.split("=", 1) for m in args.map)

    fexp = flatten({k: v for k, v in exp.items() if k != "_meta"})
    fact = flatten(act)
    fact_lower = {k.lower(): k for k in fact}

    match = drift = missing = 0
    rows = []
    for key, evalue in sorted(fexp.items()):
        akey = None
        if key in manual and manual[key] in fact:
            akey = manual[key]
        elif key in fact:
            akey = key
        else:
            leaf = key.split(".")[-1].lower()
            cands = [orig for low, orig in fact_lower.items() if leaf and leaf in low]
            if len(cands) == 1:
                akey = cands[0]
        if akey is None:
            missing += 1; rows.append(("MISSING", key, evalue, None)); continue
        avalue = fact[akey]
        # integers (counts) must match exactly; ratios use tolerance
        tol = 0 if float(evalue).is_integer() and abs(evalue) > 1 else tol_default
        if math.isclose(avalue, evalue, abs_tol=max(tol, 1e-12)):
            match += 1; rows.append(("MATCH", key, evalue, avalue))
        else:
            drift += 1; rows.append(("DRIFT", key, evalue, avalue))

    w = max(len(r[1]) for r in rows) + 2
    for status, key, ev, av in rows:
        if status == "MATCH": continue
        print(f"{status:8s} {key:<{w}} expected={ev} actual={av}")
    print(f"\n{match} matched, {drift} drifted, {missing} not auto-matched "
          f"(tolerance {tol_default}; integers exact).")
    if drift:
        print("DRIFT above tolerance: re-check library versions (requirements.txt), "
              "the input checksum, and seeds before updating the report.")
    if missing:
        print("MISSING keys usually mean naming differences between the report's "
              "labels and headline_results.json; map them with --map and re-run.")
    sys.exit(1 if drift else 0)

if __name__ == "__main__":
    main()
