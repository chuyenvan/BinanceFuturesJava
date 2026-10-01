#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PARITY HARNESS — shadow/242 (PAPER) <-> BACKTEST (export DEV).  (AUDIT-ONLY, deterministic)

Pre-reg: docs/prereg/PREREG_PARITY_HARNESS.md  (chot TRUOC khi chay, 2026-10-01).

Subcommands: config | features | gate | selector | entry | exit | all | selftest | fetch
- Moi tang: validate INPUT chat -> so LIVE vs BACKTEST -> validate OUTPUT -> ghi report.
- LUON in PASS/FAIL/MISSING + ly do + exit code (0 PASS / 2 FAIL / 3 MISSING).
- Python thuan, chi DOC artifact local. KHONG cham 242 (chi `fetch` READ-ONLY non-secret), KHONG ONNX, KHONG Java.
- 2026 = HOLDOUT: chi do/doi chieu, KHONG chon tham so.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import zlib

try:
    import numpy as np
except Exception:                                    # pragma: no cover
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HOME = os.path.expanduser("~")

# ------------------------------------------------------------------ inputs (chot trong pre-reg)
BASELINE_PROFILE = os.path.join(REPO, "profiles", "g2_flat3.properties")
DATA_DIR = os.path.join(HERE, "data")
LIVE_CFG_SNAP = os.path.join(DATA_DIR, "live_242_config.snapshot")
LIVE_LOG_JSON = os.path.join(DATA_DIR, "live_242_log_summary.json")

LIVE_FEAT_GLOBS = [
    HOME + "/claudedata/devexport_202609/live_242/feat_dump_*.csv.gz",
    HOME + "/shadow_c3/app/feat_dump/feat_dump_20260928_*.csv.gz",
]
DEV_EXPORT = HOME + "/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz"

JSON_OUT = os.path.join(REPO, "docs", "result", "parity_report.json")
MD_OUT = os.path.join(REPO, "docs", "result", "parity_report.md")

SSH = ["ssh", "-p", "2222", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=12",
       "-i", HOME + "/.ssh/id_rsa_chuyennd", "root@103.157.218.242"]
REMOTE_APP = "/home/chuyennd/java/v_t_m"

FEATS = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
# export thieu nguon (dev=0) => can tai tao inline (RESULT_FEATDIFF_PASS2 §2.1); ghi chu, KHONG mien tru.
SRC_GAP_FEATS = {"momentum1M", "momentum15M", "momentumAcceleration"}

# STEER owner 2026-10-01 10:45: audit tham so MARKET rateDown15MAvg (+3 field market).
# Mapping (ComprehensiveMarketFeatureExtractor.extractMomentumFeatures:93-94):
#   momentum1M  = rateDownAvg ; momentum15M = rateDown15MAvg
# Dung 4 noi (file:line): MarketBigChangeDetector.getMarketStatus1M (BIG_DOWN), isDcaAlt (DCA),
#   TickWeakBlock:135 (DROP15M), BdSizeAdapt:90 (thr=MS_DOWN_BIG_AVG).
MKT_FIELDS = [("rateDownAvg", "momentum1M"), ("rateDown15MAvg", "momentum15M")]
MKT_UNAVAIL = ["rateUpAvg", "rateUp15MAvg"]        # khong co trong CSV (chi trong MarketDataObject)
MKT_THRESH_KEYS = ["MS_DOWN_BIG_AVG", "MS_DOWN_BIG_AVG_DCA", "MS_UP_BIG_THRES"]
MKT_THRESH_ALIAS = {"MS_DOWN_BIG_AVG": ["SIM_MS_DOWN_BIG_AVG"],
                    "MS_DOWN_BIG_AVG_DCA": ["SIM_MS_DOWN_BIG_AVG_DCA"],
                    "MS_UP_BIG_THRES": ["SIM_MS_UP_BIG_THRES"]}
MKT_DEFAULTS = {"MS_DOWN_BIG_AVG": -0.03157, "MS_DOWN_BIG_AVG_DCA": -0.03157,
                "MS_UP_BIG_THRES": 0.02046}

FEAT_TOL = 1e-8   # "khop may": max|delta| tuyet doi tren cung ts

CHECKS = [
    # key,          live aliases,                                   default Java (audited), note
    ("SELECTOR_RANK_TOPK", ["SELECTOR_RANK_TOPK"], None, "selector top-K"),
    ("SELECTOR_ONLY_ENTRY", ["SELECTOR_ONLY_ENTRY"], None, "sleeve gate/market"),
    ("SIM_MIN_MOMENTUM_15M", ["SIM_MIN_MOMENTUM_15M"], None, "gate base"),
    ("SIM_GATE_ROLLING_MODE", ["SIM_GATE_ROLLING_MODE", "LIVE_GATE_ROLLING_MODE"], None, "G2 gate rolling"),
    ("SIM_GATE_ROLLING_DAYS", ["SIM_GATE_ROLLING_DAYS", "LIVE_GATE_ROLLING_DAYS"], None, "G2 gate rolling"),
    ("SIM_GATE_ROLLING_PCT", ["SIM_GATE_ROLLING_PCT", "LIVE_GATE_ROLLING_PCT"], None, "G2 gate rolling"),
    ("SIM_GATE_DYN_SCALE", ["SIM_GATE_DYN_SCALE"], None, "gate scale"),
    ("SIM_RATE_PROFIT_STOP_MARKET", ["SIM_RATE_PROFIT_STOP_MARKET"], None, "exit TP arm"),
    ("TS_GIVEBACK_RATIO", ["TS_GIVEBACK_RATIO"], 0.5, "FLAT3=1.0"),
    ("SIM_TS_MAX_GAP", ["SIM_TS_MAX_GAP"], 0.08, "FLAT3=0.03"),
    ("SIM_TS_MAX_GAP_WEAK", ["SIM_TS_MAX_GAP_WEAK"], 0.03, "FLAT3=0.03"),
    ("SIM_TS_GIVEBACK", ["SIM_TS_GIVEBACK"], None, "exit arm on"),
    ("SIM_LOSER_TIME_STOP_HOURS", ["SIM_LOSER_TIME_STOP_HOURS"], None, "exit time stop"),
    ("DCA_GRID_SCALE", ["DCA_GRID_SCALE"], None, "sizing"),
    ("DCA_GRID_WEIGHTS", ["DCA_GRID_WEIGHTS"], None, "KEEPLEG0 1,1,1,1"),
    ("TIER_FLAT", ["TIER_FLAT"], None, "sizing"),
    ("SIM_F_BASE", ["SIM_F_BASE"], 0.03, "size x0.5 khi=0.015"),
    ("CAPITAL_START", ["CAPITAL_START", "PAPER_EQUITY"], None, "budget goc"),
    ("SIM_RATE_FEE", ["SIM_RATE_FEE"], 0.002, "phi base"),
    ("SIM_SLIPPAGE_RATE", ["SIM_SLIPPAGE_RATE"], 0.003, "phi base"),
    ("SIM_FIX_B1", ["SIM_FIX_B1"], None, "bugfix"),
    ("SIM_FIX_B2", ["SIM_FIX_B2"], None, "bugfix"),
    ("SIM_FIX_B3", ["SIM_FIX_B3"], None, "bugfix"),
    ("SIM_BREAKER_MODE", ["SIM_BREAKER_MODE"], None, "breaker"),
    ("CONC_CAP_PERCOIN_ENABLED", ["CONC_CAP_PERCOIN_ENABLED"], False, "risk cap"),
    ("CONC_CAP_PERCOIN_PCT", ["CONC_CAP_PERCOIN_PCT"], None, "risk cap"),
    ("SIM_ENTRY_SAMPLE_MIN", ["SIM_ENTRY_SAMPLE_MIN", "LIVE_ENTRY_GRID_MIN"], None, "nhip vao"),
]


# ------------------------------------------------------------------ helpers
def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_gz_partial(path):
    """Doc gz ke ca khi file bi cat cut (thieu end-of-stream). Tra (header, rows, truncated)."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = b""
    truncated = False
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            try:
                out += d.decompress(chunk)
            except zlib.error:
                truncated = True
                break
    try:
        out += d.flush()
    except Exception:
        truncated = True
    if not getattr(d, "eof", True):          # gz thieu end-of-stream (file dang ghi / copy do dang)
        truncated = True
    txt = out.decode("utf-8", "ignore").splitlines()
    if not txt:
        return [], [], truncated
    hdr = txt[0].split(",")
    rows = [dict(zip(hdr, ln.split(","))) for ln in txt[1:] if len(ln.split(",")) == len(hdr)]
    return hdr, rows, truncated


def read_gz_full(path):
    """Doc gz day du (export)."""
    with gzip.open(path, "rt") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = list(rd)
    return hdr, rows, False


def parse_props(path):
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, "r", errors="ignore") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def tms(v):
    x = int(float(v))
    if x > 10 ** 14:
        x //= 1000
    elif x < 10 ** 11:
        x *= 1000
    return x // 60000 * 60000


def cmp_val(a, b):
    """So sanh gia tri config (numeric uu tien)."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        return abs(float(a) - float(b)) <= 1e-12
    except Exception:
        return str(a).strip().lower() == str(b).strip().lower()


def combine(statuses):
    if "FAIL" in statuses:
        return "FAIL"
    if "MISSING" in statuses:
        return "MISSING"
    if "PASS" in statuses:
        return "PASS"
    return "MISSING"


def mkcheck(cid, status, detail, **kw):
    d = {"id": cid, "status": status, "detail": detail}
    d.update(kw)
    return d


def load_live_feat():
    """Tra (rows_by_min, files, truncated, symbols, missing_files). Dung file 242 + shadow 2026-09-28."""
    import glob
    files = []
    for g in LIVE_FEAT_GLOBS:
        files.extend(sorted(glob.glob(g)))
    rows = {}
    trunc = []
    syms = set()
    for f in files:
        try:
            hdr, rr, tr = read_gz_partial(f)
        except Exception as e:
            return None, files, trunc, syms, "khong doc duoc %s: %s" % (os.path.basename(f), str(e)[:80])
        if not hdr:
            continue
        if tr:
            trunc.append(os.path.basename(f))
        for r in rr:
            syms.add(r.get("symbol", ""))
            if r.get("symbol") != "BTCUSDT":
                continue
            try:
                rows[tms(r["ts"])] = r
            except Exception:
                continue
    return rows, files, trunc, syms, None


def load_export():
    try:
        hdr, rr, _ = read_gz_full(DEV_EXPORT)
    except Exception as e:
        return None, None, "khong doc duoc export: %s" % str(e)[:100]
    by_ts = {}
    for r in rr:
        try:
            by_ts[tms(r["ts"])] = r
        except Exception:
            continue
    return hdr, by_ts, None


# ------------------------------------------------------------------ subcommands
def layer_config():
    checks, table = [], []
    prof = parse_props(BASELINE_PROFILE)
    live = parse_props(LIVE_CFG_SNAP)
    if not prof:
        checks.append(mkcheck("input.baseline", "FAIL", "khong doc duoc profile %s" % BASELINE_PROFILE))
        return layer("config", checks, {}, table, "thieu baseline profile")
    if not live:
        checks.append(mkcheck("input.live", "FAIL",
                              "khong doc duoc snapshot config 242 %s (chay `fetch`)" % LIVE_CFG_SNAP))
        return layer("config", checks, {}, table, "thieu config LIVE")
    checks.append(mkcheck("input.baseline", "PASS", "profile %d key" % len(prof)))
    checks.append(mkcheck("input.live", "PASS", "snapshot 242 %d key non-secret" % len(live)))

    n_match = n_lech = n_missing = 0
    for key, aliases, dflt, note in CHECKS:
        exp = prof.get(key)
        found_key, got = None, None
        for a in aliases:
            if a in live:
                found_key, got = a, live[a]
                break
        if exp is None:
            verdict = "SKIP"
        elif got is not None and cmp_val(got, exp):
            verdict = "MATCH"; n_match += 1
        elif got is not None:
            verdict = "LECH"; n_lech += 1
        elif dflt is not None and cmp_val(dflt, exp):
            verdict = "MATCH-DEFAULT"; n_match += 1
        else:
            verdict = "MISSING"; n_missing += 1
        table.append({
            "key": key, "profile": exp, "live_key": found_key or "-",
            "live": got if got is not None else ("(unset; default=%s)" % dflt if dflt is not None else "(unset)"),
            "verdict": verdict, "note": note,
        })

    bad = [t for t in table if t["verdict"] in ("LECH", "MISSING")]
    st = "FAIL" if bad else "PASS"
    checks.append(mkcheck(
        "config.key_parity", st,
        "MATCH=%d LECH=%d MISSING=%d (khong tinh SKIP)" % (n_match, n_lech, n_missing),
        mismatches=[{"key": t["key"], "profile": t["profile"], "live": t["live"], "verdict": t["verdict"]}
                    for t in bad]))
    metrics = {"match": n_match, "lech": n_lech, "missing": n_missing}
    reason = "242 KHONG khop baseline: %d LECH + %d MISSING key" % (n_lech, n_missing) if bad else "khop"
    return layer("config", checks, metrics, table, reason)


def _features_core(export_by_ts, live_rows, mutate_feature=None, drop_col=None, tol=FEAT_TOL):
    """Tra (validate_checks, table, pairs, err)."""
    checks, table = [], []
    if np is None:
        return [mkcheck("input.numpy", "FAIL", "thieu numpy")], [], [], "thieu numpy"
    if live_rows is None:
        return [mkcheck("input.live", "FAIL", "khong doc duoc feat_dump LIVE")], [], [], "thieu LIVE"
    if export_by_ts is None:
        return [mkcheck("input.backtest", "FAIL", "khong doc duoc export DEV")], [], [], "thieu BACKTEST"
    if not live_rows:
        return [mkcheck("input.live.rows", "FAIL", "0 dong LIVE (file cut cut?)")], [], [], "0 dong LIVE"

    hdr = None
    if export_by_ts:
        hdr = list(next(iter(export_by_ts.values())).keys())
    miss_cols = [c for c in FEATS if (drop_col == c) or (hdr is not None and c not in hdr)]
    if drop_col:
        miss_cols = [drop_col]
    if miss_cols:
        return [mkcheck("input.schema", "FAIL",
                        "thieu cot trong export: %s" % ",".join(miss_cols))], [], [], "thieu cot"

    common = sorted(set(live_rows.keys()) & set(export_by_ts.keys()))
    if len(common) == 0:
        return [mkcheck("input.pair", "FAIL",
                        "0 cap (ts) giao giua LIVE(n=%d) va BACKTEST(n=%d)" % (len(live_rows), len(export_by_ts)))], [], [], "0 cap"
    checks.append(mkcheck("input.pair", "PASS", "%d cap (ts) giao" % len(common)))

    nan_live = 0
    n_fail = 0
    for fn in FEATS:
        try:
            a = np.array([float(live_rows[t][fn]) for t in common], dtype=float)
            b = np.array([float(export_by_ts[t][fn]) for t in common], dtype=float)
        except Exception as e:
            table.append({"feature": fn, "n": len(common), "maxabs": None, "meanabs": None,
                          "corr": None, "status": "FAIL", "note": "parse: %s" % str(e)[:40]})
            n_fail += 1
            continue
        if mutate_feature == fn:
            b = b + 1.0                                  # TU KIEM (a): tiem lech
        nl = int(np.sum(~np.isfinite(a)))
        nan_live += nl
        d = np.abs(a - b)
        mx = float(np.nanmax(d)) if d.size else float("nan")
        mn = float(np.nanmean(d)) if d.size else float("nan")
        try:
            if a.std() > 0 and b.std() > 0:
                cr = float(np.corrcoef(a, b)[0, 1])
            else:
                cr = float("nan")
        except Exception:
            cr = float("nan")
        st = "PASS" if (mx <= tol and nl == 0) else "FAIL"
        if st == "FAIL":
            n_fail += 1
        note = "export thieu nguon (dev=0) — can tai tao inline" if fn in SRC_GAP_FEATS else ""
        table.append({"feature": fn, "n": len(common), "maxabs": mx, "meanabs": mn,
                      "corr": cr, "nan_live": nl, "status": st, "note": note})
    checks.append(mkcheck("output.nan", "PASS" if nan_live == 0 else "FAIL",
                          "NaN LIVE bất thường=%d" % nan_live))
    checks.append(mkcheck("output.feature_parity", "FAIL" if n_fail else "PASS",
                          "%d/%d feature vuot nguong max|delta|<=%.0e" % (n_fail, len(FEATS), tol)))
    return checks, table, common, None


def layer_features(mutate_feature=None, drop_col=None, quiet=False):
    live_rows, files, trunc, syms, err = load_live_feat()
    export_by_ts, eerr = None, None
    hdr_e, export_by_ts, eerr = load_export()
    if err:
        return layer("features", [mkcheck("input.live", "FAIL", err)], {}, [], err)
    checks, table, common, cerr = _features_core(export_by_ts, live_rows, mutate_feature, drop_col)
    if cerr and cerr != "0 cap":
        return layer("features", checks, {}, table, cerr)
    if not mutate_feature and not drop_col:
        checks.insert(0, mkcheck("input.integrity", "PASS" if live_rows else "FAIL",
                                 "LIVE files=%d (cut cut=%d, da phuc hoi partial), pairs=%d" % (
                                     len(files), len(trunc), len(common or []))))
    if drop_col:
        # TU KIEM (c): phai FAIL, khong crash
        return layer("features", checks, {}, table, checks[0]["detail"] if checks else "drop")
    n_fail = sum(1 for t in table if t["status"] == "FAIL")
    metrics = {"pairs": len(common), "files": len(files), "truncated_files": len(trunc),
               "symbols": sorted(syms), "feat_fail": n_fail, "tol": FEAT_TOL}
    st = "FAIL" if (n_fail or any(c["status"] == "FAIL" for c in checks)) else "PASS"
    reason = ("%d/%d feature lech (max|delta|>%.0e)" % (n_fail, len(FEATS), FEAT_TOL)) if n_fail \
        else "33/33 feature khop"
    return layer("features", checks, metrics, table, reason)


def layer_gate():
    checks = []
    live_rows, files, trunc, syms, err = load_live_feat()
    live = parse_props(LIVE_CFG_SNAP)
    prof = parse_props(BASELINE_PROFILE)
    logsum = {}
    if os.path.exists(LIVE_LOG_JSON):
        try:
            logsum = json.load(open(LIVE_LOG_JSON))
        except Exception:
            logsum = {}
    if not live_rows:
        return layer("gate", [mkcheck("input.live", "FAIL", err or "0 dong LIVE")], {}, [], err or "0 dong")
    p15 = np.array([float(r.get("p15_out", "nan")) for r in live_rows.values()], dtype=float)
    p15 = p15[np.isfinite(p15)]
    p15_max = float(p15.max()) if p15.size else float("nan")
    p15_p100 = p15_max
    thr_min = logsum.get("last_gate_thr_min")
    thr_max = logsum.get("last_gate_thr_max")
    obs_npass = logsum.get("gate_npass_total", None)
    checks.append(mkcheck("input.live", "PASS",
                          "LIVE p15 n=%d max=%.5f" % (p15.size, p15_max)))
    if thr_min is None:
        checks.append(mkcheck("gate.repro", "MISSING",
                              "khong co thr tu log 242 (chay `fetch`) => khong tai lap duoc quyet dinh cong"))
    else:
        repro_zero = (obs_npass == 0)
        consistent = repro_zero and (p15_max < float(thr_min))
        checks.append(mkcheck("gate.repro", "PASS" if consistent else "FAIL",
                              "n_pass log=%s; p15_max=%.5f %s thr_min=%.5f => %s" % (
                                  obs_npass, p15_max, "<" if p15_max < float(thr_min) else ">=",
                                  float(thr_min), "dong nhat (0 pass)" if consistent else "KHONG dong nhat")))
    live_mode = "ratio" if ("SIM_GATE_ROLLING_MODE" in live or "LIVE_GATE_ROLLING_MODE" in live) else "fixed"
    base_mode = "ratio" if str(prof.get("SIM_GATE_ROLLING_MODE", "")).lower() == "ratio" else "fixed"
    checks.append(mkcheck("gate.mode_parity", "PASS" if live_mode == base_mode else "FAIL",
                          "LIVE gate mode=%s vs BASELINE=%s" % (live_mode, base_mode)))
    checks.append(mkcheck("gate.p15_dev_parity", "MISSING",
                          "p15 phia BACKTEST can ONNX inference (bi cam) => khong do duoc; de xuat: dump p15/dev CSV"))
    metrics = {"p15_live_max": p15_max, "thr_applied_min": thr_min, "thr_applied_max": thr_max,
               "gate_npass_total": obs_npass, "live_mode": live_mode, "baseline_mode": base_mode}
    st = combine([c["status"] for c in checks])
    reason = "242 gate=%s, thr %.4f > p15_max %.4f => n_pass=%s (baseline=ratio)" % (
        live_mode, (thr_min or float("nan")), p15_max, obs_npass)
    return layer("gate", checks, metrics, [], reason)


def layer_marketparams():
    checks, table = [], []
    if np is None:
        return layer("marketparams", [mkcheck("input.numpy", "FAIL", "thieu numpy")], {}, [], "thieu numpy")
    live_rows, files, trunc, syms, err = load_live_feat()
    _, export_by_ts, eerr = load_export()
    live_cfg = parse_props(LIVE_CFG_SNAP)
    prof = parse_props(BASELINE_PROFILE)
    if not live_rows or not export_by_ts:
        return layer("marketparams", [mkcheck("input.live", "FAIL", err or eerr or "thieu du lieu")], {}, [], "thieu du lieu")
    common = sorted(set(live_rows) & set(export_by_ts))
    if not common:
        return layer("marketparams", [mkcheck("input.pair", "FAIL", "0 cap (ts)")], {}, [], "0 cap")

    # --- 1. 4 field market cung phut ---
    live_dec = {}
    bt_dec = {}
    for fn, col in MKT_FIELDS:
        a = np.array([float(live_rows[t][col]) for t in common])
        b = np.array([float(export_by_ts[t][col]) for t in common])
        d = np.abs(a - b)
        mx, mn = float(d.max()), float(d.mean())
        try:
            cr = float(np.corrcoef(a, b)[0, 1]) if (a.std() > 0 and b.std() > 0) else float("nan")
        except Exception:
            cr = float("nan")
        st = "PASS" if mx <= FEAT_TOL else "FAIL"
        # luu gia tri de do tac dong quyet dinh
        live_dec[fn] = a
        bt_dec[fn] = b
        table.append({"field": fn, "col": col, "n": len(common), "maxabs": mx, "meanabs": mn,
                      "corr": cr, "status": st})
    for fn in MKT_UNAVAIL:
        table.append({"field": fn, "col": "(n/a)", "n": 0, "maxabs": None, "meanabs": None,
                      "corr": None, "status": "MISSING"})
    nf = sum(1 for t in table if t["status"] == "FAIL")
    checks.append(mkcheck("mkt.field_parity", "FAIL" if nf else "PASS",
                          "%d/%d field co nguon bi lech max|delta|>%.0e; %d field MISSING (khong co trong CSV)"
                          % (nf, len(MKT_FIELDS), FEAT_TOL, len(MKT_UNAVAIL))))

    # --- 2. nguong ---
    th_rows = []
    n_th_lech = 0
    for k in MKT_THRESH_KEYS:
        exp = prof.get(k)
        got = None
        used = None
        for al in [k] + MKT_THRESH_ALIAS[k]:
            if al in live_cfg:
                got, used = live_cfg[al], al
                break
        dflt = MKT_DEFAULTS[k]
        if got is not None and exp is not None and cmp_val(got, exp):
            v = "MATCH"
        elif got is None and exp is None:
            v = "MATCH-DEFAULT"            # ca 2 ben unset => cung an default Java
        elif exp is None and got is None:
            v = "MATCH-DEFAULT"
        elif got is not None and exp is not None:
            v = "MATCH" if cmp_val(got, exp) else "LECH"
        elif got is None and exp is not None:
            v = "MATCH-DEFAULT" if cmp_val(dflt, exp) else "MISSING"
        else:
            v = "LECH"
        if v in ("LECH", "MISSING"):
            n_th_lech += 1
        th_rows.append({"key": k, "profile": exp if exp is not None else "(unset)",
                        "live": ("%s (%s)" % (got, used)) if got is not None else "(unset)",
                        "default": dflt, "verdict": v})
    checks.append(mkcheck("mkt.threshold_parity", "FAIL" if n_th_lech else "PASS",
                          "%d/%d nguong lech; ca 2 ben unset => dung default Java (MS_DOWN_BIG_AVG=%.5f, DCA=%.5f)"
                          % (n_th_lech, len(MKT_THRESH_KEYS), MKT_DEFAULTS["MS_DOWN_BIG_AVG"],
                             MKT_DEFAULTS["MS_DOWN_BIG_AVG_DCA"])))

    # --- 3. tac dong len quyet dinh BIG_DOWN / DCA ---
    thr_bd = MKT_DEFAULTS["MS_DOWN_BIG_AVG"]
    thr_dca = MKT_DEFAULTS["MS_DOWN_BIG_AVG_DCA"]
    def dec(a_down, a_15):
        return (a_down < thr_bd), (a_15 < thr_dca) | (a_down < thr_dca / 3.0)
    live_bd, live_dca = dec(live_dec["rateDownAvg"], live_dec["rateDown15MAvg"])
    bt_bd, bt_dca = dec(bt_dec["rateDownAvg"], bt_dec["rateDown15MAvg"])
    flip_bd = int(np.sum(live_bd != bt_bd))
    flip_dca = int(np.sum(live_dca != bt_dca))
    dead_bt = int(np.sum((bt_dec["rateDownAvg"] == 0) & (bt_dec["rateDown15MAvg"] == 0)))
    checks.append(mkcheck("mkt.impact_bigdown_dca",
                          "FAIL" if (flip_bd or flip_dca or dead_bt) else "PASS",
                          "BIG_DOWN flip=%d, DCA flip=%d; BACKTEST field=0 (chet) %d/%d phut (%.0f%%) "
                          "=> BIG_DOWN/DCA khong the kich hoat tu field nay o cac phut do"
                          % (flip_bd, flip_dca, dead_bt, len(common), 100.0 * dead_bt / len(common))))
    metrics = {"pairs": len(common), "field_fail": nf, "thresh_fail": n_th_lech,
               "bigdown_flip": flip_bd, "dca_flip": flip_dca, "backtest_dead_minutes": dead_bt,
               "live_bigdown_minutes": int(live_bd.sum()), "live_dca_minutes": int(live_dca.sum()),
               "thresholds": th_rows}
    reason = ("market: %d/%d field lech (rateDown15MAvg max|delta|=%.4f), BACKTEST field=0 %.0f%% phut; "
              "nguong khop (default)" % (nf, len(MKT_FIELDS), table[1]["maxabs"] or 0, 100.0 * dead_bt / len(common)))
    return layer("marketparams", checks, metrics, table, reason)


def layer_selector():
    checks = [mkcheck("input.live", "MISSING",
                      "artifact selector LIVE la Java-serialized HashMap<String,Float> "
                      "(storage/data/predictionSymbol/*), khong co score CSV doc duoc; "
                      "khong co artifact selector BACKTEST cung tick."),
              mkcheck("output.compare", "MISSING",
                      "khong so duoc score/rank tung tick. De xuat: them cot selectorScore+rank vao feat_dump CSV "
                      "(hoac dump CSV rieng) cho CA live lan export.")]
    return layer("selector", checks, {}, [], "MISSING: thieu nguon selector doi ung")


def layer_entry():
    checks = []
    logsum = {}
    if os.path.exists(LIVE_LOG_JSON):
        try:
            logsum = json.load(open(LIVE_LOG_JSON))
        except Exception:
            logsum = {}
    live_rows, _, _, _, err = load_live_feat()
    p15 = np.array([float(r.get("p15_out", "nan")) for r in (live_rows or {}).values()], dtype=float)
    p15 = p15[np.isfinite(p15)]

    live_entries = int(logsum.get("ledger_trades_since_1209", logsum.get("ledger_rows", 0)))
    gate_lines = int(logsum.get("gate_lines", 0))
    npass_zero = bool(logsum.get("gate_all_zero", False))
    thr_min = logsum.get("last_gate_thr_min")
    if not logsum:
        checks.append(mkcheck("input.live", "FAIL", "khong co log summary 242 (chay `fetch`)"))
        return layer("entry", checks, {}, [], "thieu log LIVE")
    checks.append(mkcheck("input.live", "PASS",
                          "%d dong [GATE], all n_pass=0=%s, ledger trades=0? next" % (gate_lines, npass_zero)))
    live_count = live_entries
    if gate_lines and npass_zero and thr_min is not None and p15.size:
        consistent = p15.max() < float(thr_min)
        checks.append(mkcheck("entry.live_consistency", "PASS" if consistent else "FAIL",
                              "n_pass=0 nhat quan voi p15_max=%.5f < thr=%.5f" % (p15.max(), float(thr_min))))
    else:
        checks.append(mkcheck("entry.live_consistency", "MISSING", "thieu du lieu de kiem nhat quan"))
    # BACKTEST: G2 la bat bien thang do (pass <=> r >= q_t, q_t = phan vi rolling < max) => tren cua so
    # co >=1 ung vien, so pass ky vong >= 1. Day la he qua TOAN HOC cua dinh nghia G2 trong profile.
    baseline_min = 1
    checks.append(mkcheck("entry.window_parity", "PASS" if live_count == baseline_min else "FAIL",
                          "LIVE entries=%d vs BACKTEST(G2) expected>=%d" % (live_count, baseline_min)))
    metrics = {"live_entries": live_count, "backtest_entries_min": baseline_min,
               "gate_lines": gate_lines, "gate_all_zero": npass_zero,
               "window_candidates": int(p15.size)}
    st = combine([c["status"] for c in checks])
    reason = "entry lech: LIVE=%d vs BACKTEST(G2)>=%d" % (live_count, baseline_min)
    return layer("entry", checks, metrics, [], reason)


def layer_exit():
    logsum = {}
    if os.path.exists(LIVE_LOG_JSON):
        try:
            logsum = json.load(open(LIVE_LOG_JSON))
        except Exception:
            logsum = {}
    closed = int(logsum.get("ledger_closed_since_1209", logsum.get("ledger_rows_since_1209", 0)))
    checks = [mkcheck("input.live", "MISSING" if closed == 0 else "PASS",
                      "ledger 242: %d lenh dong tu 12/09 (gate dong => khong co lenh)" % closed),
              mkcheck("output.compare", "MISSING",
                      "khong co lenh dong de doi chieu exit (FLAT3 vs T0). "
                      "De xuat: sau khi gate mo, so TS_GIVEBACK_RATIO/SIM_TS_MAX_GAP tren ledger that + printDone.")]
    return layer("exit", checks, {}, [], "MISSING: khong co lenh dong (gate chan truoc)")


def layer(name, checks, metrics, table, reason):
    st = combine([c["status"] for c in checks]) if checks else "MISSING"
    return {"name": name, "status": st, "reason": reason, "checks": checks,
            "metrics": metrics, "table": table}


# ------------------------------------------------------------------ selftests
def selftests():
    out = []
    # (b) deterministic: tinh 2 lan
    try:
        live_rows, _, _, _, _ = load_live_feat()
        _, export_by_ts, _ = load_export()
        c1, t1, pr1, _ = _features_core(export_by_ts, live_rows)
        c2, t2, pr2, _ = _features_core(export_by_ts, live_rows)
        same = (json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True))
        out.append({"id": "deterministic", "status": "PASS" if same else "FAIL",
                    "detail": "2 lan tinh features => %s (%d cap)" % ("byte-identical" if same else "KHAC", len(pr1))})
    except Exception as e:
        out.append({"id": "deterministic", "status": "FAIL", "detail": "loi: %s" % str(e)[:120]})
    # (a) injected shift => FAIL dung cho
    try:
        live_rows, _, _, _, _ = load_live_feat()
        _, export_by_ts, _ = load_export()
        c, table, pr, _ = _features_core(export_by_ts, live_rows, mutate_feature="hourOfDay")
        row = next((t for t in table if t["feature"] == "hourOfDay"), None)
        ok = row is not None and row["status"] == "FAIL"
        base = layer_features()
        base_fail = [t["feature"] for t in base["table"] if t["status"] == "FAIL"]
        only_extra = sorted(set([t["feature"] for t in table if t["status"] == "FAIL"]) - set(base_fail))
        out.append({"id": "injected_shift_fails_right", "status": "PASS" if (ok and only_extra == ["hourOfDay"]) else "FAIL",
                    "detail": "tai hourOfDay status=%s; FAIL them moi=%s (mong doi [hourOfDay]; truoc= %s)" % (
                        row["status"] if row else "?", only_extra,
                        "PASS" if "hourOfDay" not in base_fail else "FAIL")})
    except Exception as e:
        out.append({"id": "injected_shift_fails_right", "status": "FAIL", "detail": "loi: %s" % str(e)[:120]})
    # (c) drop required column => FAIL kem ly do, khong crash
    try:
        live_rows, _, _, _, _ = load_live_feat()
        _, export_by_ts, _ = load_export()
        c, table, pr, err = _features_core(export_by_ts, live_rows, drop_col="momentum5M")
        bad = any(x["status"] == "FAIL" for x in c)
        detail = c[0]["detail"] if c else ""
        ok = bad and err == "thieu cot" and "momentum5M" in detail
        out.append({"id": "missing_column_fails_with_reason", "status": "PASS" if ok else "FAIL",
                    "detail": "FAIL=%s err=%s detail=%s" % (bad, err, detail[:80])})
    except Exception as e:
        out.append({"id": "missing_column_fails_with_reason", "status": "FAIL",
                    "detail": "CRASH (khong duoc phep): %s" % str(e)[:120]})
    return out


# ------------------------------------------------------------------ fetch (READ-ONLY 242)
def fetch_live():
    os.makedirs(DATA_DIR, exist_ok=True)
    remote = r'''
cd %s
echo "@@ENV@@"
grep -E "^export |^[A-Z_]+=" conf/env.sh 2>/dev/null | sed "s/^export //" | grep -viE "SECRET|API_KEY|APIKEY|_KEY=|PASSW|TOKEN|PRIVATE"
echo "@@CONF@@"
grep -E "^[A-Z_]+=" config.properties 2>/dev/null | grep -viE "SECRET|API_KEY|APIKEY|_KEY=|PASSW|TOKEN|PRIVATE"
echo "@@GATE@@"
echo "total=$(grep -ac '\[GATE\]' logs/full.log 2>/dev/null)"
echo "npass_zero=$(grep -a '\[GATE\]' logs/full.log 2>/dev/null | grep -c 'n_pass=0')"
grep -a '\[GATE\]' logs/full.log 2>/dev/null | tail -1
echo "@@PASS@@"
echo "aipass=$(grep -ac 'AI PASS' logs/full.log 2>/dev/null)"
echo "@@LEDGER@@"
d="${SHADOW_C3_DIR:-/home/chuyennd/java/shadow_c3}"
wc -l "$d/ledger.csv" 2>/dev/null
head -1 "$d/ledger.csv" 2>/dev/null
head -1 "$d/open_positions.csv" 2>/dev/null
echo "@@LASTGATE_1209@@"
grep -a '\[GATE\]' logs/full.log 2>/dev/null | awk '/12\/09\/2026 08:15/{f=1} f' | head -1
''' % REMOTE_APP
    p = subprocess.run(SSH + [remote], capture_output=True, text=True, timeout=90)
    txt = p.stdout
    if "@@ENV@@" not in txt:
        return {"ok": False, "err": p.stderr[:200] or "ssh rc=%d" % p.returncode}

    def sect(tag):
        i = txt.find("@@%s@@" % tag)
        if i < 0:
            return ""
        j = txt.find("@@", i + len(tag) + 4)
        return txt[i + len(tag) + 4:j if j > 0 else len(txt)]

    env = parse_props_str(sect("ENV"))
    conf = parse_props_str(sect("CONF"))
    merged = dict(conf)
    merged.update(env)
    with open(LIVE_CFG_SNAP, "w") as fh:
        fh.write("# snapshot config 242 (NON-SECRET, READ-ONLY) — sinh boi parity_check.py fetch\n")
        for k in sorted(merged):
            fh.write("%s=%s\n" % (k, merged[k]))

    gate = sect("GATE")
    npass_zero = int(_grab(gate, "npass_zero") or 0)
    total = int(_grab(gate, "total") or 0)
    last = [l for l in gate.splitlines() if "[GATE]" in l]
    thr_min = thr_max = None
    if last:
        m = re.search(r"thr=\[([\d.]+)\.\.([\d.]+)\]", last[-1])
        if m:
            thr_min, thr_max = float(m.group(1)), float(m.group(2))
    ledger = sect("LEDGER").splitlines()
    led_rows = led_closed = 0
    if ledger:
        try:
            led_rows = max(0, int(ledger[0].split()[-1]) - 1)
        except Exception:
            led_rows = 0
    summary = {
        "gate_lines": total,
        "gate_npass_zero_lines": npass_zero,
        "gate_all_zero": (total > 0 and npass_zero == total),
        "gate_npass_total": 0 if (total > 0 and npass_zero == total) else None,
        "last_gate_thr_min": thr_min,
        "last_gate_thr_max": thr_max,
        "ai_pass_lines": int(_grab(sect("PASS"), "aipass") or 0),
        "ledger_rows": led_rows,
        "ledger_closed_since_1209": led_rows,
        "ledger_trades_since_1209": led_rows,
        "note": "READ-ONLY; ledger tren 242 gan nhat rong (gate dong tu 12/09)",
    }
    with open(LIVE_LOG_JSON, "w") as fh:
        json.dump(summary, fh, indent=1, sort_keys=True)
    return {"ok": True, "cfg_keys": len(merged), "log": summary}


def parse_props_str(s):
    out = {}
    for ln in s.splitlines():
        ln = ln.strip()
        if not ln or "=" not in ln or ln.startswith("#"):
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _grab(s, key):
    m = re.search(r"^%s=(.*)$" % re.escape(key), s, re.M)
    return m.group(1).strip() if m else None


# ------------------------------------------------------------------ report
def build_report(which="all"):
    inputs = []
    for label, path in [("baseline_profile", BASELINE_PROFILE), ("live_cfg_snapshot", LIVE_CFG_SNAP),
                        ("live_log_summary", LIVE_LOG_JSON), ("dev_export", DEV_EXPORT)]:
        if os.path.exists(path):
            inputs.append({"label": label, "path": path, "md5": md5_file(path),
                           "bytes": os.path.getsize(path)})
        else:
            inputs.append({"label": label, "path": path, "md5": None, "bytes": None, "missing": True})

    layers = []
    if which in ("all", "config"):
        layers.append(layer_config())
    if which in ("all", "features"):
        layers.append(layer_features())
    if which in ("all", "gate"):
        layers.append(layer_gate())
    if which in ("all", "marketparams"):
        layers.append(layer_marketparams())
    if which in ("all", "selector"):
        layers.append(layer_selector())
    if which in ("all", "entry"):
        layers.append(layer_entry())
    if which in ("all", "exit"):
        layers.append(layer_exit())

    rep = {
        "harness": "research/parity/parity_check.py",
        "prereg": "docs/prereg/PREREG_PARITY_HARNESS.md",
        "window_note": "2026 = HOLDOUT: chi do/doi chieu (audit-only), KHONG chon tham so",
        "feat_tol": FEAT_TOL,
        "inputs": inputs,
        "layers": layers,
    }
    if which == "all":
        rep["selftests"] = selftests()
    statuses = [l["status"] for l in layers] + [t["status"] for t in rep.get("selftests", [])]
    rep["overall"] = combine(statuses) if statuses else "MISSING"
    rep["exit_code"] = 2 if rep["overall"] == "FAIL" else (3 if rep["overall"] == "MISSING" else 0)
    return rep


def render_md(rep):
    L = []
    L.append("# PARITY REPORT — shadow/242 ↔ BACKTEST\n")
    L.append("> Sinh boi `research/parity/parity_check.py` (deterministic). Pre-reg: `docs/prereg/PREREG_PARITY_HARNESS.md`.\n")
    L.append("- **Tong ket: `%s`** (exit_code=%d)\n" % (rep["overall"], rep["exit_code"]))
    L.append("- %s\n" % rep["window_note"])
    L.append("\n## Input (md5)\n")
    L.append("| label | path | md5 | bytes |\n|---|---|---|---|")
    for i in rep["inputs"]:
        L.append("| %s | `%s` | %s | %s |" % (i["label"], i["path"], i.get("md5") or "MISSING", i.get("bytes")))
    L.append("\n## Tang\n")
    L.append("| tang | trang thai | ly do |\n|---|---|---|")
    for la in rep["layers"]:
        L.append("| **%s** | %s | %s |" % (la["name"], la["status"], la["reason"]))
    for la in rep["layers"]:
        L.append("\n### %s — %s\n" % (la["name"], la["status"]))
        if la["metrics"]:
            L.append("- metrics: `%s`\n" % json.dumps(la["metrics"], sort_keys=True))
        for c in la["checks"]:
            L.append("- [%s] %s: %s" % (c["status"], c["id"], c["detail"]))
        if la["name"] == "config" and la["table"]:
            L.append("\n| key | profile | LIVE | verdict |\n|---|---|---|---|")
            for t in la["table"]:
                L.append("| `%s` | %s | %s | %s |" % (t["key"], t["profile"], t["live"], t["verdict"]))
        if la["name"] == "marketparams" and la["metrics"].get("thresholds"):
            L.append("\nnguong (242 vs baseline vs default Java):\n")
            L.append("| key | profile | LIVE | default | verdict |\n|---|---|---|---|---|")
            for t in la["metrics"]["thresholds"]:
                L.append("| `%s` | %s | %s | %s | %s |" % (t["key"], t["profile"], t["live"], t["default"], t["verdict"]))
        if la["name"] == "marketparams" and la["table"]:
            L.append("\n| field | col | n | max\\|Δ\\| | mean\\|Δ\\| | corr | status |\n|---|---|---|---|---|---|---|")
            for t in la["table"]:
                L.append("| %s | %s | %d | %s | %s | %s | %s |" % (
                    t["field"], t["col"], t["n"], _f(t["maxabs"]), _f(t["meanabs"]), _f(t["corr"], 4), t["status"]))
        if la["name"] == "features" and la["table"]:
            L.append("\n| feature | n | max\\|Δ\\| | mean\\|Δ\\| | corr | status |\n|---|---|---|---|---|---|")
            for t in la["table"]:
                L.append("| %s | %d | %s | %s | %s | %s |" % (
                    t["feature"], t["n"], _f(t["maxabs"]), _f(t["meanabs"]), _f(t["corr"], 4), t["status"]))
    if "selftests" in rep:
        L.append("\n## Tu kiem harness\n")
        L.append("| # | status | detail |\n|---|---|---|")
        for s in rep["selftests"]:
            L.append("| %s | %s | %s |" % (s["id"], s["status"], s["detail"]))
    return "\n".join(L) + "\n"


def _f(x, nd=3):
    if x is None:
        return "-"
    try:
        return ("%%.%de" % nd) % float(x) if abs(float(x)) < 1e-3 or abs(float(x)) > 1e4 else ("%%.%df" % nd) % float(x)
    except Exception:
        return str(x)


def write_report(rep):
    os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
    with open(JSON_OUT, "w") as fh:
        json.dump(rep, fh, indent=1, sort_keys=True)
    with open(MD_OUT, "w") as fh:
        fh.write(render_md(rep))
    return JSON_OUT, MD_OUT


def print_layers(rep):
    print("=== PARITY HARNESS — overall=%s (exit=%d) ===" % (rep["overall"], rep["exit_code"]))
    for la in rep["layers"]:
        print("[%s] %s — %s" % (la["status"], la["name"], la["reason"]))
        for c in la["checks"]:
            print("    - [%s] %s: %s" % (c["status"], c["id"], c["detail"]))
    for s in rep.get("selftests", []):
        print("[%s] selftest %s — %s" % (s["status"], s["id"], s["detail"]))
    print("report: %s , %s" % (JSON_OUT, MD_OUT))


def main():
    ap = argparse.ArgumentParser(description="Parity harness shadow/242 <-> backtest (audit-only)")
    ap.add_argument("cmd", choices=["config", "features", "gate", "marketparams", "selector", "entry", "exit",
                                   "all", "selftest", "fetch"])
    args = ap.parse_args()
    if args.cmd == "fetch":
        r = fetch_live()
        print(json.dumps(r, indent=1, sort_keys=True)[:1500])
        return 0 if r.get("ok") else 2
    if args.cmd == "selftest":
        res = selftests()
        print(json.dumps(res, indent=1, sort_keys=True))
        return 0 if all(s["status"] == "PASS" for s in res) else 2
    which = "all" if args.cmd == "all" else args.cmd
    rep = build_report(which)
    if args.cmd == "all":
        write_report(rep)
    print_layers(rep)
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
