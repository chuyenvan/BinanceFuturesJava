"""VZ E1 - T7 confirmation runner (build ready; runs only when the lake has the data).

    python3 e1_confirm.py --prereg docs/prereg/PREREG_VZ_B4.md --years 2022,2023,2025

Reads the YAML block of the pre-registration (family, variant, thresholds fixed
from 2024, measure, GO rule, k tests for the CI widening sqrt(2 ln k)), and
REFUSES unless that pre-reg file is committed and clean in git.

Confirmation years (2022/2023/2025), v1 = H-B / V2_tss_reversal_q5 (B4):
- E1 events are rebuilt per year from the lake (kline1m), reusing the e1_core
  event definition (`candidates`) and feature code (`compute_features` at commit
  6b2ae088). Features use at most the last 30 days of the PREVIOUS year.
- net 60'/240'/1440' (real + stress) use the e1_core formula
  `log(close(ts+h)/close(ts)) - (bucket EXEC + 2*0.000982)`; an event is kept
  only when ts+1440' stays inside the year (the next year is never read).
- the variant is evaluated with the FROZEN 2024 edges (configs/t3_thresholds.json,
  same edges as the pre-reg YAML), never recomputed per confirmation year.
- the 3-condition GO rule is evaluated and written with the output md5 and the
  pre-reg commit hash -> reports/e1_confirm_B4.json.

Guards (each REFUSES, reads nothing, invents nothing):
- pre-reg not committed / dirty, or missing a required YAML key;
- the year's kline1m (or its lookback month) is not in the lake;
- pre-reg edges differ from the frozen 2024 config;
- a variant other than the frozen B4 variant is requested.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import yaml

import e1_core
import e1_data
import e1_t3
from e1_common import OUT, REPORT, setup_logging, write_json
from e1_stats import day_level_boot, monotonicity, spread_ci

log = setup_logging("e1_confirm", "e1_confirm.log")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FROZEN_CONFIG = os.path.join(HERE, "configs", "t3_thresholds.json")
CONFIRM_YEARS = {"2021", "2022", "2023", "2025"}
SMOKE_YEARS = {"2024"}
REQUIRED = ("name", "family", "variant", "thresholds", "measure", "go_rule", "k_tests")
B4_VARIANT = "V2_tss_reversal_q5"
HORIZONS_CONFIRM = ("net_60", "net_240", "net_1440", "net_stress_1440")
LOOKBACK_DAYS = 30


def yaml_block(path):
    text = open(path).read()
    if "```yaml" not in text:
        raise SystemExit("no ```yaml block in %s" % path)
    body = text.split("```yaml", 1)[1].split("```", 1)[0]
    return yaml.safe_load(body)


def git_state(path):
    rel = os.path.relpath(os.path.abspath(path), REPO)
    log_out = subprocess.run(["git", "log", "--oneline", "--", rel], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    return {"committed": bool(log_out), "dirty": bool(diff), "commit": commit,
            "rel": rel, "log": log_out}


def build_cfg(prereg):
    th = prereg["thresholds"]
    cfg = {"date": "prereg", "features": {}}
    for k, v in th.items():
        if isinstance(v, dict):
            cfg["features"][k] = v
    return cfg


def check_frozen(cfg):
    """The pre-reg edges must be exactly the frozen 2024 edges (no per-year refit)."""
    if "tss_reversal" not in cfg["features"]:
        raise SystemExit("REFUSE: pre-reg has no tss_reversal thresholds")
    with open(FROZEN_CONFIG) as f:
        froz = json.load(f)
    for feat, d in cfg["features"].items():
        if feat not in froz["features"]:
            raise SystemExit("REFUSE: feature %s is not in the frozen %s" % (feat, FROZEN_CONFIG))
        if [float(x) for x in d.get("edges", [])] != \
           [float(x) for x in froz["features"][feat]["edges"]]:
            raise SystemExit("REFUSE: pre-reg edges for %s differ from the frozen 2024 config"
                             % feat)


# ------------------------------------------------------------------ lake guard
def required_months(year):
    """12 months of `year` + the lookback month (last Dec of the previous year)."""
    y = int(year)
    return ["%04d-%02d" % (y, m) for m in range(1, 13)] + ["%04d-12" % (y - 1)]


def check_lake(years, fetch=False):
    """REFUSE unless every required kline1m month is available (local, or on Kaggle if fetch).

    No data is read here: only a local file existence check and (with --fetch) a
    Kaggle metadata listing. Missing months are reported, never fabricated.
    """
    missing = []
    for y in years:
        for m in required_months(y):
            if e1_data.local_month(m, "kline") is not None:
                continue
            if fetch:
                files = e1_data.kaggle_files(e1_data.kline_slug(m))
                if files and ("kline1m-%s.parquet" % m) in files:
                    continue
            missing.append(m)
    if missing:
        raise SystemExit(
            "REFUSE: kline1m lake is incomplete for %s - %d month(s) missing "
            "(e.g. %s). No data read, nothing fabricated; wait for Phase 1 to "
            "upload the year (or pass --fetch once it has)."
            % (",".join(years), len(missing), ", ".join(missing[:8])))
    log.info("lake OK for years=%s (fetch=%s)", years, fetch)


# ------------------------------------------------------------------ evaluation
def level_series(cfg, ev, variant):
    _, feat, nq, hi_lv, lo_lv = e1_t3.VAR_BY_NAME[variant]
    lv = e1_t3.levels_for(cfg, feat, nq, ev)
    return lv, hi_lv, lo_lv


def col_block(ev, lv, col, hi_lv, lo_lv, widen):
    """Spread (top - bottom) for one net column + monotonicity + widened CI."""
    boot, lvs = day_level_boot(ev[col].to_numpy(np.float64), ev["day"].to_numpy(np.int64), lv)
    levels = [int(x) for x in lvs if x > 0]
    sp = spread_ci(boot, lo_lv, hi_lv) if (hi_lv in boot and lo_lv in boot) else \
        {"diff_mean": float("nan"), "ci95": [float("nan"), float("nan")], "excl_zero": False}
    se = float("nan")
    wide_upper = float("nan")
    if hi_lv in boot and lo_lv in boot:
        d = boot[hi_lv]["reps_mean"] - boot[lo_lv]["reps_mean"]
        d = d[np.isfinite(d)]
        if d.size > 1:
            se = float(np.nanstd(d, ddof=1))
            wide_upper = float(sp["diff_mean"] + widen * se)
    return {
        "n": int(np.isfinite(ev[col].to_numpy(np.float64)).sum()),
        "levels": {str(x): {"n": int(boot[x]["n"]), "mean": float(boot[x]["mean"]),
                            "median": float(boot[x]["median"]),
                            "hit_rate": float(boot[x]["hit_rate"]),
                            "ci95_mean": [float(boot[x]["ci95_mean"][0]),
                                          float(boot[x]["ci95_mean"][1])]}
                   for x in levels},
        "monotonicity": float(monotonicity([boot[x]["mean"] for x in levels])),
        "spread_extreme": {"diff_mean": float(sp["diff_mean"]),
                           "ci95": [float(sp["ci95"][0]), float(sp["ci95"][1])],
                           "excl_zero": bool(sp["excl_zero"]),
                           "se": se,
                           "ci95_wide_sqrt2lnk": [float(sp["ci95"][0]), wide_upper]},
    }


def eval_confirm(ev, cfg, variant, widen):
    lv, hi_lv, lo_lv = level_series(cfg, ev, variant)
    out = {"n_events": int(len(ev)), "n_level_assigned": int((lv > 0).sum()),
           "levels_present": sorted(int(x) for x in np.unique(lv) if x > 0)}
    for col in HORIZONS_CONFIRM:
        out[col] = col_block(ev, lv, col, hi_lv, lo_lv, widen)
    return out


def run_confirmation(prereg_path, yrs, pre, gs, fetch=False):
    variant = pre["variant"]
    if variant != B4_VARIANT:
        raise SystemExit("REFUSE: variant %s is not the frozen B4 variant %s"
                         % (variant, B4_VARIANT))
    cfg = build_cfg(pre)
    check_frozen(cfg)
    check_lake(yrs, fetch=fetch)
    widen = float(np.sqrt(2.0 * np.log(max(int(pre["k_tests"]), 2))))

    per_year = {}
    pooled = []
    for y in yrs:
        ev = e1_core.build_year_events(int(y), lookback_days=LOOKBACK_DAYS,
                                       prior_lookback=True, fetch=fetch)
        n_all = int(len(ev))
        if n_all == 0:
            raise SystemExit("REFUSE: no %s crash events built for %s" % (variant, y))
        ev = ev[np.isfinite(ev.net_1440.to_numpy(np.float64))].copy()
        if len(ev) == 0:
            raise SystemExit("REFUSE: no %s event with ts+1440' inside %s" % (variant, y))
        r = eval_confirm(ev, cfg, variant, widen)
        r["n_events_all"] = n_all
        r["n_with_full_24h"] = int(len(ev))
        r["frac_full_24h"] = float(len(ev) / n_all)
        per_year[y] = r
        pooled.append(ev)
        log.info("year %s events=%d with24h=%d spread1440=%.5f", y, n_all, len(ev),
                 r["net_1440"]["spread_extreme"]["diff_mean"])

    pooled_res = eval_confirm(pd.concat(pooled, ignore_index=True), cfg, variant, widen)
    p = pooled_res["net_1440"]["spread_extreme"]
    ps = pooled_res["net_stress_1440"]["spread_extreme"]
    c1 = bool(p["diff_mean"] < 0 and p["ci95_wide_sqrt2lnk"][1] < 0)
    c2 = bool(all(per_year[y]["net_1440"]["spread_extreme"]["diff_mean"] < 0 for y in yrs))
    c3 = bool(ps["diff_mean"] < 0)

    res = {"prereg": pre, "prereg_commit": gs["commit"], "years": yrs, "variant": variant,
           "ci_widen_factor_sqrt2lnk": widen, "per_year": per_year, "pooled": pooled_res,
           "go_rule": {
               "cond1_pooled_net1440_lt0_and_widened_ci_upper_lt0": c1,
               "cond2_each_year_net1440_lt0": c2,
               "cond3_pooled_stress_same_direction_lt0": c3,
               "decision": "GO" if (c1 and c2 and c3) else "NO-GO"}}
    blob = json.dumps(res, sort_keys=True, default=str).encode()
    res["output_md5"] = hashlib.md5(blob).hexdigest()
    name = str(pre["name"]).replace(" ", "_")
    outpath = os.path.join(REPORT, "e1_confirm_%s.json" % name)
    write_json(outpath, res)
    log.info("confirm %s -> %s md5=%s decision=%s", name, outpath, res["output_md5"],
             res["go_rule"]["decision"])
    return res


def run(prereg_path, years, fetch=False):
    gs = git_state(prereg_path)
    if not gs["committed"]:
        raise SystemExit("REFUSE: pre-reg %s is not committed (git log empty)" % prereg_path)
    if gs["dirty"]:
        raise SystemExit("REFUSE: pre-reg %s has uncommitted changes" % prereg_path)
    pre = yaml_block(prereg_path)
    missing = [k for k in REQUIRED if k not in pre]
    if missing:
        raise SystemExit("REFUSE: pre-reg missing keys %s" % missing)
    yrs = [y.strip() for y in years.split(",") if y.strip()]
    unsupported = [y for y in yrs if y not in SMOKE_YEARS and y not in CONFIRM_YEARS]
    if unsupported:
        raise SystemExit("REFUSE: unknown years %s" % unsupported)
    if not pre["family"].lower().startswith("h-b"):
        raise SystemExit("REFUSE: family %s evaluator not implemented in this runner (v1: H-B)"
                         % pre["family"])

    if set(yrs) <= SMOKE_YEARS:
        # 2024 smoke: reproduce the frozen T3 numbers bit-exactly (no lake rebuild).
        cfg = build_cfg(pre)
        ev = e1_t3.load_events()
        out = e1_t3.evaluate_variant(pre["variant"], cfg, ev)
        widen = float(np.sqrt(2.0 * np.log(max(int(pre["k_tests"]), 2))))
        res = {"prereg": pre, "prereg_commit": gs["commit"], "years": yrs,
               "ci_widen_factor_sqrt2lnk": widen, "result": out}
        blob = json.dumps(res, sort_keys=True, default=str).encode()
        res["output_md5"] = hashlib.md5(blob).hexdigest()
        name = str(pre["name"]).replace(" ", "_")
        write_json(os.path.join(REPORT, "e1_confirm_%s.json" % name), res)
        return res

    if set(yrs) & SMOKE_YEARS:
        raise SystemExit("REFUSE: do not mix the 2024 smoke with confirmation years")

    return run_confirmation(prereg_path, yrs, pre, gs, fetch=fetch)


# ------------------------------------------------------------------ smoke tests
def smoke_check(prereg_path):
    """(a) the runner reproduces the frozen T3 numbers bit-exactly on 2024."""
    res = run(prereg_path, "2024")
    rep = json.load(open(os.path.join(REPORT, "e1_t3.json")))
    variant = res["prereg"]["variant"]
    ref = [v for v in rep["variants"] if v["variant"] == variant]
    if not ref:
        return {"pass": False, "reason": "T3 report has no variant %s" % variant}
    ref = ref[0]
    for col in ("net_60", "net_240"):
        for lv, d in res["result"][col].items():
            for stat in ("mean", "median", "hit_rate", "n"):
                a, b = d[stat], ref[col][lv][stat]
                if isinstance(a, float):
                    if not (np.isnan(a) and np.isnan(b)) and a != b:
                        return {"pass": False, "why": (col, lv, stat, a, b)}
                elif a != b:
                    return {"pass": False, "why": (col, lv, stat, a, b)}
    return {"pass": True, "variant": variant}


def smoke_engine():
    """(a) 2024 event set + net_60'/240' bit-exact vs e1_events_2024.parquet.

    (b) new net_1440 vs e1_t9_events_net1440.parquet.
    `prior_lookback=False` so nothing outside 2024 is read (2023 is off-limits).
    """
    ev_new = e1_core.build_year_events(2024, lookback_days=LOOKBACK_DAYS,
                                       prior_lookback=False, fetch=True)
    canon = e1_t3.load_events()
    out = {"n_new": int(len(ev_new)), "n_canon": int(len(canon))}

    mn = ev_new[["sym", "ts", "bucket", "net_60", "net_240", "tss_reversal"]].copy()
    mc = canon[["sym", "ts", "bucket", "net_60", "net_240", "tss_reversal"]].copy()
    m = mn.merge(mc, on=["sym", "ts"], how="outer", suffixes=("_new", "_canon"), indicator=True)
    out["event_set_identical"] = bool((m._merge == "both").all() and len(m) == len(canon) == len(ev_new))
    both = m[m._merge == "both"]
    out["n_common"] = int(len(both))
    out["bucket_mismatch"] = int((both.bucket_new != both.bucket_canon).sum())
    for col in ("net_60", "net_240"):
        a = both[col + "_new"].to_numpy(np.float64)
        b = both[col + "_canon"].to_numpy(np.float64)
        fin = np.isfinite(a) & np.isfinite(b)
        out[col + "_max_abs_diff"] = float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else None
        out[col + "_nan_mismatch"] = int((np.isfinite(a) != np.isfinite(b)).sum())
    rc = both.tss_reversal_canon.to_numpy(np.float64)
    rn = both.tss_reversal_new.to_numpy(np.float64)
    fin = np.isfinite(rc) & np.isfinite(rn)
    out["tss_reversal_max_abs_diff"] = float(np.max(np.abs(rc[fin] - rn[fin]))) if fin.any() else None
    out["tss_reversal_nan_new_only"] = int((np.isfinite(rc) & ~np.isfinite(rn)).sum())

    t9 = pd.read_parquet(os.path.join(OUT, "e1_t9_events_net1440.parquet"))[
        ["sym", "ts", "net_1440", "net_stress_1440"]]
    mm = ev_new.merge(t9, on=["sym", "ts"], how="inner", suffixes=("_new", "_t9"))
    a = mm.net_1440_new.to_numpy(np.float64)
    b = mm.net_1440_t9.to_numpy(np.float64)
    fin = np.isfinite(a) & np.isfinite(b)
    out["net1440_n_compared"] = int(fin.sum())
    out["net1440_max_abs_diff"] = float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else None
    out["net1440_nan_mismatch"] = int((np.isfinite(a) != np.isfinite(b)).sum())
    out["net1440_caveat"] = ("e1_t9 keeps every 2024 event (net=NaN when past year end); "
                             "this engine also builds the whole year, so both share the "
                             "same in-year set")

    tol = 1e-12
    ok = (out["event_set_identical"] and out["bucket_mismatch"] == 0
          and out.get("net_60_max_abs_diff", 1) <= tol and out.get("net_60_nan_mismatch", 1) == 0
          and out.get("net_240_max_abs_diff", 1) <= tol and out.get("net_240_nan_mismatch", 1) == 0
          and out.get("net1440_max_abs_diff", 1) <= tol and out["net1440_nan_mismatch"] == 0
          and out["tss_reversal_nan_new_only"] <= 101)  # only the Jan-1 00:0x rows lack lookback
    out["pass"] = bool(ok)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--years", default="2022,2023,2025")
    ap.add_argument("--fetch", action="store_true",
                    help="allow downloading missing months from the year's Kaggle dataset")
    ap.add_argument("--smoke-check", action="store_true")
    ap.add_argument("--smoke-engine", action="store_true")
    a = ap.parse_args()
    if a.smoke_check:
        print(json.dumps(smoke_check(a.prereg), default=str))
    elif a.smoke_engine:
        print(json.dumps(smoke_engine(), default=str))
    else:
        print(json.dumps(run(a.prereg, a.years, fetch=a.fetch), default=str))
