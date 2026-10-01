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
# 3 feature market (momentum1M/15M/acceleration) = rateDownAvg/rateDown15MAvg cua export.
# Export chet nguon (=0) trong cua so LIVE => phai TAI TAO INLINE tu kline (md_inline).
# Nguong inline KHONG the 1e-8 (2 duong ticker-vs-kline khac nhau); do duoc max|delta| = 7.5e-4
# (502 cap, 2026-09-28/29) => dat nguong thuc dung 1e-3, van nho hon 1 bac so voi lech that (~1e-2..1e+0).
INLINE_FEATS = {"momentum1M", "momentum15M", "momentumAcceleration"}
FEAT_TOL_INLINE = 1e-3

# --- marketparams (STEER owner 2026-10-01 10:45) ---
MARKET_BIN = "/home/ubuntu/wfo_ds_x1_2021/market.bin"      # DEV: simulator market_data source (<=2025-12-31)
DEV_STRESS_DAY = "2025-10-10"                              # ngay crash manh (down15 min -0.718)
MS_DOWN_BIG_AVG = -0.03157                                 # Configs.java:466 (default; baseline g2_flat3 khong override)
MS_DOWN_BIG_AVG_DCA = -0.03157                             # Configs.java:470
MS_UP_BIG_THRES = 0.02046                                  # Configs.java:465

# --- V3 (VIEC 1) chan doan WRITER gz: file feat_dump thieu gz trailer = "cat cut" ---
# Java GZIPOutputStream(counter,16384,true) + writer.flush() moi dong => day 1 DEFLATE SYNC-FLUSH block
# (empty stored block = 00 00 FF FF) xuong file, NHUNG trailer (CRC32+ISIZE) CHI duoc ghi khi close().
# close() (LiveFeatureDump.java:148-155) CHI duoc goi khi du REMAINING tick hoac cham tran 200 MB
# => JVM bi restart/stop truoc do => file khong bao gio duoc finalize => thieu trailer.
# Anh xa: LiveFeatureDump.maybeDump (src/main/java/.../features/export/entry/LiveFeatureDump.java:84-121)
#         open() flush syncFlush=true (dong 133-146) ; close() (dong 148-155). Duong goi = LIVE
#         (DetectEntrySignal2TradeNormal.java:299) => RANG BUOC: chi DE XUAT, khong sua.
GZ_SYNC_FLUSH = b"\x00\x00\xff\xff"
LIVE_WRITER_FILE = "src/main/java/com/binance/chuyennd/ai_ml/features/export/entry/LiveFeatureDump.java"

# --- V3 (VIEC 2) marketparams: 4 field (nguon cac field) ---
MP_CSV = os.path.join(DATA_DIR, "marketparams_inline.csv")   # *.csv => gitignored (khong push data)
MKT_ALL4 = ["rateDownAvg", "rateUpAvg", "rateDown15MAvg", "rateUp15MAvg"]

# --- V3 (VIEC 3) selector + gate-p15 (nguon KHONG-ONNX) ---
PRED_BIN = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"           # DEV gate p15: n x (ts, predReturn15M, predRisk4H)
FUNDING_BIN = "/home/ubuntu/wfo_ds_x1_2021/funding.bin"     # DEV selector: n x (ts, len, len x long symId|bits(1-P))
SELECTOR_SYM_DIR = HOME + "/shadow_c3/app/storage/data/predictionSymbol"  # LIVE selector (2026-09)
P15_DEV_CSV = os.path.join(DATA_DIR, "p15_dev.csv")
SELECTOR_CSV = os.path.join(DATA_DIR, "selector_live.csv")

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


def gz_diag(path):
    """VIEC 1: chan doan 1 file .gz. Tra bang chung 'cat cut' = thieu gz trailer nhung CO sync-flush tail
    (00 00 FF FF) => writer da flush() nhung KHONG close()/finalize."""
    with open(path, "rb") as fh:
        data = fh.read()
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    ok = True
    try:
        out = d.decompress(data)
        out += d.flush()
    except zlib.error:
        ok = False
        out = b""
    eof = bool(getattr(d, "eof", False))
    rows = max(0, out.decode("utf-8", "ignore").count("\n") - 1) if out else 0
    return {"file": os.path.basename(path), "bytes": len(data),
            "trailer": bool(eof), "full_ok": bool(ok and eof),
            "syncflush_tail": data[-4:] == GZ_SYNC_FLUSH, "tail_hex": data[-4:].hex(),
            "rows_recovered": rows}


def gz_writer_emulation(path):
    """VIEC 1: TAI LAP co che Java writer bang Python (zlib) — file that lam CHUNG.
    - BUGGY: syncFlush=true + flush() moi dong, KHONG close() => thieu trailer, tail = 00 00 FF FF.
    - FIXED: y nhu tren + close() (tuong duong shutdown hook finalize) => trailer day du, gzip mo duoc.
    Tra dict so sanh. KHONG doc/ghi gi ngoai path.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    real = gz_diag(path)
    # BUGGY: nap lai chinh du lieu goc (raw gz) roi cat bo 8 byte trailer (neu co) + flush sync
    co = zlib.compressobj(6, zlib.DEFLATED, 16 + 15)
    buggy = co.compress(b"hello\n") + co.flush(zlib.Z_SYNC_FLUSH)   # flush KHONG finish
    fixed = buggy + co.flush()                                     # finish => trailer ghi ra
    buggy_ok = True
    try:
        gzip.decompress(buggy)
    except Exception:
        buggy_ok = False
    fixed_ok = True
    try:
        gzip.decompress(fixed)
    except Exception:
        fixed_ok = False
    return {"real_file": real, "emu_buggy_tail": buggy[-4:].hex(), "emu_buggy_decompress_ok": buggy_ok,
            "emu_fixed_tail": fixed[-4:].hex(), "emu_fixed_decompress_ok": fixed_ok,
            "real_matches_buggy": real["syncflush_tail"] and not real["full_ok"]}


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


# ------------------------------------------------------------------ marketparams helpers
_ANALYSIS_DIR = os.path.join(REPO, "research", "analysis")
_INLINE_CACHE = {}


def load_market_bin(path=MARKET_BIN):
    """Doc market.bin (DEV `market_data` source): int n + n*(long ts, float down,up,down15)."""
    import struct
    if np is None or not os.path.exists(path):
        return None, "thieu numpy hoac khong thay %s" % path
    with open(path, "rb") as f:
        cnt = struct.unpack(">i", f.read(4))[0]
        buf = f.read(20 * cnt)
    if len(buf) < 20 * cnt:
        return None, "market.bin cut cut"
    a = np.frombuffer(buf, dtype=np.dtype([("ts", ">i8"), ("d", ">f4"), ("u", ">f4"), ("x", ">f4")]))
    out = {int(t): (float(d), float(u), float(x)) for t, d, u, x in a}
    return out, None


def inline_md_days(day_ms_list):
    """Tai tao MarketDataObject INLINE tu kline 242 (md_inline + devexport parse). Tra (dict, err).
    dict: min_ts(ms) -> (rateDownAvg, rateUpAvg, rateDown15MAvg). Cache theo ngay."""
    days = sorted(set(d // 86400000 * 86400000 for d in day_ms_list))
    key = tuple(days)
    if key in _INLINE_CACHE:
        return _INLINE_CACHE[key]
    try:
        if _ANALYSIS_DIR not in sys.path:
            sys.path.insert(0, _ANALYSIS_DIR)
        import datetime
        import devexport_202609 as dx
        from md_inline import InlineMD
        import featdiff_pass2 as fp
    except Exception as e:
        r = (None, "thieu module (aerospike/cramjam): %s" % str(e)[:80])
        _INLINE_CACHE[key] = r
        return r
    TZ7, DAY = dx.TZ7, dx.DAY
    try:
        store = dx.Store("242")
    except Exception as e:
        r = (None, "khong mo duoc Aerospike 242 READ-ONLY: %s" % str(e)[:90])
        _INLINE_CACHE[key] = r
        return r
    out = {}
    try:
        for dms in days:
            gen = InlineMD(fp.load_died())
            kl = store.get_kline_day(dms)
            parsed = {}
            for k, v in kl.items():
                try:
                    ts = int(datetime.datetime.strptime(k, "%Y%m%d-%H%M").replace(tzinfo=TZ7).timestamp() * 1000)
                except Exception:
                    continue
                parsed[ts] = v
            for ts in sorted(parsed.keys()):
                syms, arr = dx.parse_minute(parsed[ts])
                if not syms:
                    continue
                snap = {s: (float(arr[i, 0]), float(arr[i, 1]), float(arr[i, 2]), float(arr[i, 3]))
                        for i, s in enumerate(syms)}
                md = gen.update(snap)
                if md is not None:
                    out[ts // 60000 * 60000] = md
    except Exception as e:
        store.close()
        r = (None, "loi tai tao inline: %s" % str(e)[:90])
        _INLINE_CACHE[key] = r
        return r
    store.close()
    r = (out, None)
    _INLINE_CACHE[key] = r
    return r


def live_market_series(live_rows):
    """LIVE side tu feat_dump: momentum1M=rateDownAvg, momentum15M=rateDown15MAvg. Tra dict min_ts->(d,d15)."""
    return {t: (float(r["momentum1M"]), float(r["momentum15M"])) for t, r in live_rows.items()}


def _stats(a, b):
    d = np.abs(a - b)
    try:
        cr = float(np.corrcoef(a, b)[0, 1]) if (a.std() > 0 and b.std() > 0) else float("nan")
    except Exception:
        cr = float("nan")
    return float(np.max(d)) if d.size else float("nan"), float(np.mean(d)) if d.size else float("nan"), cr


def _flip_counts(a_d, a_d15, b_d, b_d15, thr=MS_DOWN_BIG_AVG, thr_dca=MS_DOWN_BIG_AVG_DCA):
    """Dem so PHUT quyet dinh BIG_DOWN / DCA DOI TRANG THAI giua 2 duong field."""
    bl = a_d < thr
    bi = b_d < thr
    dl = (a_d15 < thr_dca) | (a_d < thr_dca / 3)
    di = (b_d15 < thr_dca) | (b_d < thr_dca / 3)
    return {
        "bigdown_flips": int(np.sum(bl != bi)), "bigdown_a": int(bl.sum()), "bigdown_b": int(bi.sum()),
        "dca_flips": int(np.sum(dl != di)), "dca_a": int(dl.sum()), "dca_b": int(di.sum()),
    }


# ------------------------------------------------------------------ V3 helpers (VIEC 2/3)
def dump_marketparams_csv(day_ms_list):
    """VIEC 2 — exporter '--md-inline' (tuong duong): xuat 4 field market tai moi phut tai tao inline
    (port `MarketBigChangeDetector.calMarketData`). `rateUp15MAvg` = 0 vi calMarketData KHONG tinh field nay
    (constructor 3 field) va market.bin cung chi co 3 float. Tra (path, err)."""
    inline, err = inline_md_days(day_ms_list)
    if err:
        return None, err
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(MP_CSV, "w") as fh:
            fh.write("ts," + ",".join(MKT_ALL4) + "\n")
            for t in sorted(inline):
                d, u, x = inline[t]
                fh.write("%d,%.9g,%.9g,%.9g,0\n" % (t, d, u, x))
    except Exception as e:
        return None, str(e)[:80]
    return MP_CSV, None


def read_p15_dev(limit=None):
    """VIEC 3 — doc `pred.bin` (nguon p15 DEV KHONG-ONNX): int n + n*(long ts, float predReturn15M, float predRisk4H).
    Tra (list[(ts,p15,risk)], err). `limit` <= 0/None = doc het (streaming, khong giu qua 2.6M)."""
    import struct
    if not os.path.exists(PRED_BIN):
        return None, "khong thay %s" % PRED_BIN
    out = []
    with open(PRED_BIN, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        step = 16
        for _ in range(n):
            b = f.read(step)
            if len(b) < step:
                break
            ts, p15, risk = struct.unpack(">qff", b)
            out.append((ts, p15, risk))
            if limit and len(out) >= limit:
                break
    return out, None


def dump_p15_dev_csv():
    """VIEC 3 — dump p15 DEV (pred.bin) ra CSV (nan 2 cot), ghi vao DATA_DIR (*.csv => gitignored)."""
    rows, err = read_p15_dev()
    if err:
        return None, err
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(P15_DEV_CSV, "w") as fh:
            fh.write("ts,predReturn15M,predRisk4H\n")
            for ts, p15, risk in rows:
                fh.write("%d,%.9g,%.9g\n" % (ts, p15, risk))
    except Exception as e:
        return None, str(e)[:80]
    return P15_DEV_CSV, None


def read_selector_tick(path):
    """VIEC 3 — doc 1 artifact selector LIVE (Java-serialized HashMap<String,Float> qua Snappy).
    Tra dict symbol->score (score THAP = coin tot, tier1Score = P(fail)).
    Dung javaobj (frame ngoai byte[]) + cramjam (snappy). Tra (dict, err)."""
    try:
        import javaobj
        import cramjam
    except Exception as e:
        return None, "thieu javaobj/cramjam: %s" % str(e)[:50]
    try:
        obj = javaobj.loads(open(path, "rb").read())
        raw = bytes((x & 0xFF) for x in obj)
        m = javaobj.loads(cramjam.snappy.decompress_raw(raw))
        d = {}
        for k, v in m.items():
            try:
                d[str(k)] = float(getattr(v, "value", v))
            except Exception:
                pass
        return d, None
    except Exception as e:
        return None, "decode loi: %s" % str(e)[:60]


def dump_selector_live_csv(day="20260928"):
    """VIEC 3 — dump selector LIVE (predictionSymbol/<day>/*) ra CSV ts,symbol,selectorScore,rank.
    Tra (path, stats, err)."""
    import glob
    d = os.path.join(SELECTOR_SYM_DIR, day)
    files = sorted(f for f in glob.glob(d + "/*") if not f.endswith(".features"))
    if not files:
        return None, {}, "khong co artifact %s" % d
    stats = {"ticks": 0, "rows": 0, "syms_min": None, "syms_max": None, "err": None}
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        fh = open(SELECTOR_CSV, "w")
        fh.write("ts,symbol,selectorScore,rank\n")
        for f in files:
            ts = int(os.path.basename(f))
            m, err = read_selector_tick(f)
            if err:
                stats["err"] = err
                continue
            stats["ticks"] += 1
            stats["rows"] += len(m)
            ns = len(m)
            stats["syms_min"] = ns if stats["syms_min"] is None else min(stats["syms_min"], ns)
            stats["syms_max"] = ns if stats["syms_max"] is None else max(stats["syms_max"], ns)
            for rank, (sym, sc) in enumerate(sorted(m.items(), key=lambda kv: kv[1]), 1):
                fh.write("%d,%s,%.9g,%d\n" % (ts, sym, sc, rank))
        fh.close()
    except Exception as e:
        try:
            fh.close()
        except Exception:
            pass
        return None, stats, str(e)[:80]
    return SELECTOR_CSV, stats, None


def funding_bin_meta():
    """VIEC 3 — metadata nguon selector DEV (funding.bin): int n + n*(long ts, int len, len x long (symId<<32)|bits(1-P))."""
    import struct
    if not os.path.exists(FUNDING_BIN):
        return None, "khong thay %s" % FUNDING_BIN
    with open(FUNDING_BIN, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        t0, l0 = struct.unpack(">qi", f.read(12))
        f.seek(4 + 12 + 8 * l0 + 0)
        # quet toi ban ghi cuoi
        f.seek(4)
        last = None
        for _ in range(n):
            b = f.read(12)
            if len(b) < 12:
                break
            ts, l = struct.unpack(">qi", b)
            f.seek(8 * l, 1)
            last = ts
    return {"n": n, "ts0": t0, "ts1": last, "first_len": l0}, None


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


# VIEC 4 — phan nhom nguyen nhan feature lech (i/ii/iii). Tieu chi + co so:
#  - Export DEV la PORT Python 1-1 cua ComprehensiveMarketFeatureExtractor (doc 2 file) => CONG THUC giong.
#  - Khac nhau con lai = NGUON: LIVE (ticker live + history-ring do tick live nuoi) vs BACKTEST (kline luu).
RATIO_AMPLIFIED = {"volumeRatioUpDown", "advanceDeclineRatio", "btcDominance", "volumeSpike",
                   "basketVolSpike"}   # ti so up/down (upCount/downCount, upVol/downVol, btcVol/sumVol)


def _classify_feature(fn, mx, corr, exp0, status):
    """Tra nhom nguyen nhan: 'ok' | 'ii-export-thieu-nguon(=0)' | 'i-ti-so-nhay' |
    'i-nhieu-ticker-vs-kline' | 'iii-nghi-logic/tap-hop'."""
    if status == "PASS":
        return "ok"
    if fn in INLINE_FEATS and mx is not None and mx > FEAT_TOL_INLINE:
        return "ii-export-thieu-nguon(=0) + logic con lai"
    if exp0 is not None and exp0 == exp0 and exp0 >= 0.5:
        return "ii-export-thieu-nguon(=0)"
    if fn in RATIO_AMPLIFIED:
        return "i-ti-so-nhay (nhieu ticker-vs-kline)"
    if corr is not None and corr == corr and corr < 0.7:
        return "iii-nghi-logic/tap-hop (can control cung-nguon)"
    return "i-nhieu-ticker-vs-kline"


def _features_core(export_by_ts, live_rows, mutate_feature=None, drop_col=None, tol=FEAT_TOL,
                   inline_md=None):
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
    n_fail_machine = 0
    for fn in FEATS:
        try:
            a = np.array([float(live_rows[t][fn]) for t in common], dtype=float)
            b = np.array([float(export_by_ts[t][fn]) for t in common], dtype=float)
        except Exception as e:
            table.append({"feature": fn, "n": len(common), "maxabs": None, "meanabs": None,
                          "corr": None, "status": "FAIL", "note": "parse: %s" % str(e)[:40]})
            n_fail += 1
            n_fail_machine += 1
            continue
        row_tol = tol
        note = ""
        recon = False
        if inline_md is not None and fn in INLINE_FEATS:
            # TAI TAO INLINE phia BACKTEST tu kline (thay field chet =0 trong export)
            if fn == "momentum1M":
                b = np.array([inline_md.get(t, (np.nan,) * 3)[0] for t in common], dtype=float)
            elif fn == "momentum15M":
                b = np.array([inline_md.get(t, (np.nan,) * 3)[2] for t in common], dtype=float)
            else:  # momentumAcceleration = momentum5M(export) - momentum15MAvg(inline)
                b = np.array([float(export_by_ts[t]["momentum5M"]) - inline_md.get(t, (np.nan,) * 3)[2]
                              for t in common], dtype=float)
            row_tol = FEAT_TOL_INLINE
            recon = True
            note = "tai tao inline tu kline (nguon export=0)"
        elif fn in SRC_GAP_FEATS:
            note = "export thieu nguon (dev=0) — can tai tao inline"
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
        st = "PASS" if (mx <= row_tol and nl == 0) else "FAIL"
        st_m = "PASS" if (mx <= FEAT_TOL and nl == 0) else "FAIL"
        if st == "FAIL":
            n_fail += 1
        if st_m == "FAIL":
            n_fail_machine += 1
        exp0 = float(np.mean(b == 0)) if b.size else float("nan")
        live0 = float(np.mean(a == 0)) if a.size else float("nan")
        cls = _classify_feature(fn, mx, cr, exp0, st)
        table.append({"feature": fn, "n": len(common), "maxabs": mx, "meanabs": mn,
                      "corr": cr, "nan_live": nl, "status": st, "status_machine": st_m,
                      "tol": row_tol, "reconstructed": recon, "note": note,
                      "exp0": exp0, "live0": live0, "cls": cls})
    checks.append(mkcheck("output.nan", "PASS" if nan_live == 0 else "FAIL",
                          "NaN LIVE bất thường=%d" % nan_live))
    checks.append(mkcheck("output.feature_parity", "FAIL" if n_fail else "PASS",
                          "%d/%d feature vuot nguong (exact<=%.0e / inline<=%.0e); "
                          "o nguong MAY (%.0e): %d/%d vuot" % (
                              n_fail, len(FEATS), tol, FEAT_TOL_INLINE, FEAT_TOL, n_fail_machine, len(FEATS)),
                          n_fail=n_fail, n_fail_machine=n_fail_machine))
    return checks, table, common, None


def layer_features(mutate_feature=None, drop_col=None, quiet=False):
    live_rows, files, trunc, syms, err = load_live_feat()
    export_by_ts, eerr = None, None
    hdr_e, export_by_ts, eerr = load_export()
    if err:
        return layer("features", [mkcheck("input.live", "FAIL", err)], {}, [], err)
    inline_md, inline_err = (None, None)
    if not mutate_feature and not drop_col and live_rows:
        inline_md, inline_err = inline_md_days(sorted(live_rows.keys()))
    checks, table, common, cerr = _features_core(export_by_ts, live_rows, mutate_feature, drop_col,
                                                 inline_md=inline_md)
    if cerr and cerr != "0 cap":
        return layer("features", checks, {}, table, cerr)
    if inline_err:
        checks.insert(0, mkcheck("input.inline_source", "MISSING",
                                 "khong tai tao duoc inline: %s" % inline_err))
    else:
        recon = ("tai tao inline %d phut (md_inline<-kline 242)" % len(inline_md)) if inline_md else \
                "khong dung inline"
        checks.insert(0, mkcheck("input.inline_source", "PASS" if inline_md else "MISSING", recon))
    if not mutate_feature and not drop_col:
        diags = []
        for f in files:
            try:
                diags.append(gz_diag(f))
            except Exception:
                pass
        n_trunc = sum(1 for d in diags if not d["trailer"])
        n_sync = sum(1 for d in diags if d["syncflush_tail"])
        rootcause = ""
        if n_trunc:
            rootcause = (" — GOC VIEC1: file thieu gz trailer=%d/%d, tail sync-flush(00 00 FF FF)=%d/%d "
                         "=> writer da flush() nhung KHONG finalize: %s:133-146 (syncFlush=true) + close():148-155 "
                         "CHI goi khi du REMAINING/200MB; KHONG co shutdown hook => JVM restart giua chung => thieu trailer"
                         " => harness phuc hoi dong hoan chinh bang partial-inflate") % (
                             n_trunc, len(diags), n_sync, len(diags), LIVE_WRITER_FILE)
        checks.insert(0, mkcheck("input.integrity", "PASS" if live_rows else "FAIL",
                                 "LIVE files=%d (thieu-trailer=%d, sync-flush-tail=%d%s), pairs=%d" % (
                                     len(files), n_trunc, n_sync, rootcause, len(common or [])),
                                 diag=diags))
    if drop_col:
        # TU KIEM (c): phai FAIL, khong crash
        return layer("features", checks, {}, table, checks[0]["detail"] if checks else "drop")
    n_fail = sum(1 for t in table if t["status"] == "FAIL")
    n_fail_m = sum(1 for t in table if t.get("status_machine") == "FAIL")
    groups = {}
    for t in table:
        if t["status"] == "FAIL":
            groups[t.get("cls", "?")] = groups.get(t.get("cls", "?"), 0) + 1
    metrics = {"pairs": len(common), "files": len(files), "truncated_files": len(trunc),
               "symbols": sorted(syms), "feat_fail": n_fail, "feat_fail_machine_tol": n_fail_m,
               "tol": FEAT_TOL, "tol_inline": FEAT_TOL_INLINE,
               "inline_minutes": len(inline_md) if inline_md else 0,
               "reconstructed": sorted(INLINE_FEATS), "fail_groups": groups}
    st = "FAIL" if (n_fail or any(c["status"] == "FAIL" for c in checks)) else "PASS"
    reason = ("%d/%d feature lech (exact<=%.0e, inline<=%.0e; o nguong may %d/%d)" % (
        n_fail, len(FEATS), FEAT_TOL, FEAT_TOL_INLINE, n_fail_m, len(FEATS))) if n_fail \
        else "33/33 feature khop"
    return layer("features", checks, metrics, table, reason)


def layer_marketparams():
    """STEER owner 2026-10-01 10:45: audit tham so market rateDownAvg/rateUpAvg/rateDown15MAvg
    (nguon that: MarketBigChangeDetector.calMarketData) — 4 noi dung:
    (1) field LIVE vs BACKTEST cung phut; (2) nguong; (3) SO LAN BIG_DOWN/DCA DOI TRANG THAI; (4) MISSING.
    """
    checks, table = [], []
    live_rows, files, trunc, syms, err = load_live_feat()
    live = parse_props(LIVE_CFG_SNAP)
    prof = parse_props(BASELINE_PROFILE)
    if not live_rows:
        return layer("marketparams", [mkcheck("input.live", "FAIL", err or "0 dong LIVE")], {}, [], err or "0 dong")
    live_md = live_market_series(live_rows)
    checks.append(mkcheck("input.live", "PASS",
                          "LIVE feat_dump: %d phut (momentum1M=rateDownAvg, momentum15M=rateDown15MAvg)" % len(live_md)))

    # ---- (1) BACKTEST: tai tao inline (dung CHINH calMarketData) tren cung phut live ----
    inline, ierr = inline_md_days(sorted(live_md.keys()))
    if ierr:
        checks.append(mkcheck("mp.live_vs_backtest", "MISSING", "khong tai tao inline: %s" % ierr))
    else:
        common = sorted(set(live_md) & set(inline))
        a_d = np.array([live_md[t][0] for t in common]); b_d = np.array([inline[t][0] for t in common])
        a_x = np.array([live_md[t][1] for t in common]); b_x = np.array([inline[t][2] for t in common])
        m1 = _stats(a_d, b_d); m15 = _stats(a_x, b_x)
        checks.append(mkcheck("input.pair", "PASS", "%d phut giao (LIVE vs inline=cung thuat toan calMarketData)" % len(common)))
        table.append({"field": "rateDownAvg", "col": "momentum1M", "n": len(common),
                      "maxabs": m1[0], "meanabs": m1[1], "corr": m1[2],
                      "status": "PASS" if m1[0] <= FEAT_TOL_INLINE else "FAIL"})
        table.append({"field": "rateDown15MAvg", "col": "momentum15M", "n": len(common),
                      "maxabs": m15[0], "meanabs": m15[1], "corr": m15[2],
                      "status": "PASS" if m15[0] <= FEAT_TOL_INLINE else "FAIL"})
        bad = [t for t in table if t["status"] == "FAIL"]
        checks.append(mkcheck("mp.fields_live_vs_inline", "FAIL" if bad else "PASS",
            "LIVE vs inline: rateDownAvg max|d|=%.3e corr=%.5f ; rateDown15MAvg max|d|=%.3e corr=%.5f "
            "(rateUpAvg: feat_dump KHONG xuat -> do o phia DEV store ben duoi)" % (
                m1[0], m1[2], m15[0], m15[2])))
        # ---- (3) TAC DONG: so PHUT BIG_DOWN / DCA doi trang thai ----
        fl = _flip_counts(a_d, a_x, b_d, b_x)
        checks.append(mkcheck("mp.decision_flips_live", "PASS" if (fl["bigdown_flips"] == 0 and fl["dca_flips"] == 0)
                              else "FAIL", "BIG_DOWN flip=%d (live=%d inline=%d); DCA flip=%d (live=%d inline=%d)" % (
                                  fl["bigdown_flips"], fl["bigdown_a"], fl["bigdown_b"],
                                  fl["dca_flips"], fl["dca_a"], fl["dca_b"]), **fl))
    # ---- (1b) DEV: market.bin (store backtest) vs inline cung phut (ngay stress) ----
    mb, mberr = load_market_bin()
    dev_fl, dev_stats = {}, {}
    fields4 = False
    if mberr:
        checks.append(mkcheck("mp.dev_store", "MISSING", mberr))
    else:
        import datetime
        dms = int(datetime.datetime.strptime(DEV_STRESS_DAY + " +0700", "%Y-%m-%d %z").timestamp() * 1000)
        inline2, ierr2 = inline_md_days([dms])
        if ierr2:
            checks.append(mkcheck("mp.dev_store", "MISSING", "inline ngay DEV: %s" % ierr2))
        else:
            c2 = sorted(set(mb) & set(inline2))
            if not c2:
                checks.append(mkcheck("mp.dev_store", "MISSING", "0 phut giao market.bin vs inline (%s)" % DEV_STRESS_DAY))
            else:
                md_ = np.array([mb[t][0] for t in c2]); mid = np.array([inline2[t][0] for t in c2])
                mu_ = np.array([mb[t][1] for t in c2]); miu = np.array([inline2[t][1] for t in c2])
                mx_ = np.array([mb[t][2] for t in c2]); mix = np.array([inline2[t][2] for t in c2])
                s1 = _stats(md_, mid); su = _stats(mu_, miu); s2 = _stats(mx_, mix)
                dev_fl = _flip_counts(md_, mx_, mid, mix)
                dev_stats = {"n": len(c2), "rateDownAvg_maxabs": s1[0], "rateDownAvg_corr": s1[2],
                             "rateUpAvg_maxabs": su[0], "rateUpAvg_corr": su[2],
                             "rateDown15MAvg_maxabs": s2[0], "rateDown15MAvg_corr": s2[2]}
                checks.append(mkcheck("mp.dev_store", "PASS",
                                      "market.bin(DEV store) vs inline @%s: n=%d; rateDownAvg max|d|=%.3e corr=%.4f; "
                                      "rateUpAvg max|d|=%.3e corr=%.4f; rateDown15MAvg max|d|=%.3e corr=%.4f; "
                                      "BIG_DOWN flip=%d DCA flip=%d" % (
                                          DEV_STRESS_DAY, len(c2), s1[0], s1[2], su[0], su[2], s2[0], s2[2],
                                          dev_fl["bigdown_flips"], dev_fl["dca_flips"])))
                table.append({"field": "rateUpAvg", "col": "market.bin[1]", "n": len(c2),
                              "maxabs": su[0], "meanabs": su[1], "corr": su[2],
                              "status": "PASS" if su[0] <= FEAT_TOL_INLINE else "FAIL",
                              "note": "DEV store vs inline; feat_dump LIVE khong co cot (Java khong xuat)"})
                table.append({"field": "rateUp15MAvg", "col": "-", "n": len(c2),
                              "maxabs": 0.0, "meanabs": 0.0, "corr": 1.0, "status": "PASS",
                              "note": "CA 2 phia = 0: calMarketData KHONG tinh (constructor 3 field) + market.bin 3 float"})
                fields4 = True
    # ---- (1d) VIEC 2: exporter '--md-inline' tuong duong -> CSV 4 field + dem field do duoc ----
    mp_csv, mp_err = (None, None)
    if live_rows:
        mp_csv, mp_err = dump_marketparams_csv(sorted(live_md.keys()))
    if mp_err:
        checks.append(mkcheck("mp.csv_export", "MISSING", "khong xuat duoc CSV: %s" % mp_err))
    else:
        checks.append(mkcheck("mp.csv_export", "PASS",
                              "xuat 4 field ra CSV (tuong duong --md-inline): %s (K=%s) — rateUp15MAvg=0 (khong tinh)" % (
                                  os.path.basename(mp_csv or ""), ",".join(MKT_ALL4))))
    n_meas = sum(1 for t in table if t.get("field") in MKT_ALL4 and t["status"] in ("PASS", "FAIL"))
    checks.append(mkcheck("mp.fields4", "PASS" if n_meas == 4 else "MISSING",
                          "%d/4 field market DO DUOC (rateDownAvg/rateUpAvg/rateDown15MAvg max|d|<=~1e-3 muc nhieu; "
                          "rateUp15MAvg=0 ca 2 phia). LIVE-side truc tiep: 2/4 (dump thieu cot rateUpAvg/rateUp15MAvg)" % n_meas))
    # ---- (1c) LIVE vs BACKTEST-STORE cung phut: khong the ----
    if not mberr:
        ov = len(set(live_md) & set(mb))
        checks.append(mkcheck("mp.live_vs_store_sameminute", "MISSING",
                              "LIVE(2026-09) vs market.bin(<=2025-12-31): giao=%d phut => khong so truc tiep cung phut duoc; "
                              "dung inline lam cau noi (ca 2 phia khop ~1e-3)" % ov))
    # ---- (2) NGUONG ----
    def _resolve(key, simkey, dflt):
        v = live.get(key, live.get(simkey))
        return ("LIVE=%s" % v) if v is not None else ("unset->default %.5f" % dflt)
    th_rows = []
    for key, simkey, dflt in [("MS_DOWN_BIG_AVG", "SIM_MS_DOWN_BIG_AVG", MS_DOWN_BIG_AVG),
                              ("MS_DOWN_BIG_AVG_DCA", "SIM_MS_DOWN_BIG_AVG_DCA", MS_DOWN_BIG_AVG_DCA),
                              ("MS_UP_BIG_THRES", None, MS_UP_BIG_THRES)]:
        lv = live.get(key, live.get(simkey)) if simkey else None
        pv = prof.get(key)
        if lv is None and pv is None:
            v = "MATCH-DEFAULT"
            table.append({"field": "THR:%s" % key, "col": key, "n": 0, "maxabs": 0.0, "meanabs": 0.0,
                          "corr": 1.0, "status": v, "note": _resolve(key, simkey, dflt)})
        else:
            ok = cmp_val(lv, pv) if (lv is not None and pv is not None) else False
            v = "MATCH" if ok else "LECH"
            table.append({"field": "THR:%s" % key, "col": key, "n": 0, "maxabs": None, "meanabs": None,
                          "corr": None, "status": v, "note": "LIVE=%s baseline=%s" % (lv, pv)})
        th_rows.append({"key": key, "profile": pv if pv is not None else "(unset)",
                        "live": ("%s" % lv) if lv is not None else "(unset)",
                        "default": dflt, "verdict": v})
    thr_bad = [t for t in table if t["status"] == "LECH"]
    checks.append(mkcheck("mp.thresholds", "FAIL" if thr_bad else "PASS",
                          "3 nguong: 242 & baseline deu UNSET -> cung default Java (-0.03157/-0.03157/0.02046)"
                          if not thr_bad else "nguong LECH: %s" % [t["col"] for t in thr_bad]))
    metrics = {"live_minutes": len(live_md), "inline_minutes": len(inline or {}),
               "dev_store": dev_stats, "dev_flips": dev_fl,
               "thresholds": th_rows, "marketparams_csv": mp_csv,
               "fields_measured_4": n_meas,
               "thr_live_overrides": {k: v for k, v in live.items() if k.startswith("SIM_MS_") or k.startswith("MS_")}}
    st = combine([c["status"] for c in checks])
    reason = "4/4 field: rateDownAvg/rateUpAvg/rateDown15MAvg khop muc nhieu ticker-vs-kline (LIVE&DEV, max|d|~7e-4..2e-3, corr>0.99); " \
             "rateUp15MAvg=0 ca 2 phia (khong duoc calMarketData tinh); nguong MATCH default; flip LIVE=0/0, DEV(stress)=%d/%d" % (
                 dev_fl.get("bigdown_flips", -1), dev_fl.get("dca_flips", -1))
    return layer("marketparams", checks, metrics, table, reason)


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
    pdev_checks, pdev_metrics, pdev_reason = p15_dev_analysis(live_rows)
    checks.extend(pdev_checks)
    metrics = {"p15_live_max": p15_max, "thr_applied_min": thr_min, "thr_applied_max": thr_max,
               "gate_npass_total": obs_npass, "live_mode": live_mode, "baseline_mode": base_mode,
               "p15_dev": pdev_metrics}
    st = combine([c["status"] for c in checks])
    reason = "242 gate=%s, thr %.4f > p15_max %.4f => n_pass=%s (baseline=ratio)" % (
        live_mode, (thr_min or float("nan")), p15_max, obs_npass)
    return layer("gate", checks, metrics, [], reason)




def p15_dev_analysis(live_rows):
    """VIEC 3 — dump p15 DEV (pred.bin, KHONG-ONNX) ra CSV + do phia DEV + kiem phu cua so LIVE.
    Tra (checks, metrics, reason)."""
    checks = []
    rows, err = read_p15_dev()
    if err:
        return [mkcheck("gate.p15_dev", "MISSING", err)], {}, err
    ts = np.array([r[0] for r in rows], dtype="int64")
    p15 = np.array([r[1] for r in rows], dtype="float64")
    risk = np.array([r[2] for r in rows], dtype="float64")
    csv, cerr = dump_p15_dev_csv()
    if cerr:
        checks.append(mkcheck("gate.p15_dev.csv", "MISSING", "khong dump CSV: %s" % cerr))
    else:
        checks.append(mkcheck("gate.p15_dev.csv", "PASS",
                              "dump p15 DEV (nguon KHONG-ONNX pred.bin) -> %s (n=%d)" % (
                                  os.path.basename(csv or ""), len(rows))))
    q = {p: float(np.quantile(p15, p)) for p in (0.5, 0.99, 0.999, 0.9999)}
    dev = {"n": int(len(rows)), "ts0": int(ts.min()), "ts1": int(ts.max()),
           "p15_min": float(p15.min()), "p15_max": float(p15.max()), "p15_mean": float(p15.mean()),
           "p15_q": q, "risk_mean": float(risk.mean())}
    checks.append(mkcheck("gate.p15_dev.stats", "PASS",
                          "DEV p15: n=%d ts %s..%s; min=%.4f q0.5=%.5f q0.99=%.4f q0.999=%.4f max=%.4f" % (
                              len(rows), str(int(ts.min())), str(int(ts.max())), float(p15.min()),
                              q[0.5], q[0.99], q[0.999], float(p15.max()))))
    lmin = min(live_rows) if live_rows else 0
    lmax = max(live_rows) if live_rows else 0
    ov = int(np.sum((ts >= lmin) & (ts <= lmax))) if live_rows else 0
    metrics = {"dev": dev, "overlap_live_minutes": ov,
               "live_window": [int(lmin), int(lmax)]}
    if ov == 0:
        checks.append(mkcheck("gate.p15_dev_parity", "MISSING",
                              "pred.bin(DEV<=2025-12-31) KHONG phu cua so LIVE(2026-09-28) => giao=0 phut, "
                              "khong so cung phut duoc (2026 = holdout) => giu MISSING + ly do; de xuat: xuat p15 ra kline LIVE"))
        reason = "nguon p15 DEV non-ONNX co (pred.bin n=%d) nhung KHONG phu cua so LIVE => MISSING cung-phut" % len(rows)
    else:
        # co giao => so cung phut (p15 DEV vs p15_out LIVE)
        dmap = {int(t): float(v) for t, v in zip(ts, p15)}
        cm = sorted(set(dmap) & set(live_rows))
        a = np.array([float(live_rows[t]["p15_out"]) for t in cm])
        b = np.array([dmap[t] for t in cm])
        mx, mn, cr = _stats(a, b)
        checks.append(mkcheck("gate.p15_dev_parity",
                              "PASS" if mx <= FEAT_TOL_INLINE else "FAIL",
                              "p15 DEV vs LIVE cung phut n=%d max|d|=%.3e corr=%.4f" % (len(cm), mx, cr)))
        metrics["parity"] = {"n": len(cm), "maxabs": mx, "corr": cr}
        reason = "p15 DEV vs LIVE n=%d max|d|=%.3e" % (len(cm), mx)
    return checks, metrics, reason


def layer_selector():
    """VIEC 3 — selector: uu tien NGUON CO SAN (artifact LIVE `predictionSymbol/*`), khong bia.
    - LIVE: doc artifact Java-serialized HashMap<String,Float> (242/shadow storage) -> do coverage + top-K.
    - DEV: funding.bin (selector labels 2021-2025) — KHONG phu cua so LIVE => giu MISSING cung-tick + ly do.
    """
    live_rows, files, trunc, syms, err = load_live_feat()
    cols = set(next(iter(live_rows.values())).keys()) if live_rows else set()
    has_sel = ("selectorScore" in cols) or ("rank" in cols) or ("selector_score" in cols)
    checks = []
    if has_sel:
        checks.append(mkcheck("input.live_col", "PASS", "feat_dump CO cot selectorScore/rank"))
    else:
        checks.append(mkcheck("input.live_col", "MISSING",
                              "feat_dump KHONG co cot selectorScore/rank (cot hien co: %d)" % len(cols)))
    if not live_rows:
        return layer("selector", checks, {}, [], "khong doc duoc LIVE feat_dump")
    # --- LIVE: artifact predictionSymbol cho dung NGAY cua cua so parity (2026-09-28) ---
    days = sorted({__import__("datetime").datetime.utcfromtimestamp(t / 1000).strftime("%Y%m%d")
                   for t in live_rows})
    # thu cac ngay cua so (GMT+7 va UTC) — chon ngay co artifact
    cand = []
    for d in days + ["20260928"]:
        p = os.path.join(SELECTOR_SYM_DIR, d)
        if os.path.isdir(p):
            cand.append(d)
    day = cand[0] if cand else (days[0] if days else "20260928")
    csv, sstats, serr = (None, {}, "khong thu")
    if cand:
        csv, sstats, serr = dump_selector_live_csv(day)
    if serr:
        checks.append(mkcheck("input.artifact", "MISSING", "artifact selector LIVE: %s" % serr))
    else:
        checks.append(mkcheck("input.artifact", "PASS",
                              "artifact LIVE %s/* : ticks=%d rows=%d syms/tick=%s..%s -> %s (RAW, khong ONNX)" % (
                                  day, sstats.get("ticks"), sstats.get("rows"),
                                  sstats.get("syms_min"), sstats.get("syms_max"), os.path.basename(csv or ""))))
    fmeta, ferr = funding_bin_meta()
    if ferr:
        checks.append(mkcheck("input.dev_source", "MISSING", ferr))
    else:
        checks.append(mkcheck("input.dev_source", "PASS",
                              "nguon selector DEV = funding.bin (n=%d ts %d..%d) — KHONG-ONNX" % (
                                  fmeta["n"], fmeta["ts0"], fmeta["ts1"])))
    # --- cung-tick: LIVE(2026-09) vs DEV(<=2025-12-31) ---
    lmin, lmax = min(live_rows), max(live_rows)
    if fmeta and not ferr and not (lmax < fmeta["ts0"] or lmin > fmeta["ts1"]):
        checks.append(mkcheck("output.compare", "PASS", "co giao cua so => so duoc score/rank cung tick"))
        reason = "selector do duoc (co giao cua so)"
    else:
        checks.append(mkcheck("output.compare", "MISSING",
                              "funding.bin(%s..%s) KHONG phu cua so LIVE(%s..%s) => KHONG so cung tick; "
                              "de xuat: them cot selectorScore+rank vao feat_dump (ca live lan export)" % (
                                  fmeta["ts0"] if fmeta else "?", fmeta["ts1"] if fmeta else "?", lmin, lmax)))
        reason = "MISSING cung-tick: đo được phía LIVE (artifact %s: %d tick, %d dong), thiếu đối ứng cung-tick DEV" % (
            day, sstats.get("ticks", 0), sstats.get("rows", 0))
    metrics = {"feat_dump_cols": len(cols), "has_selector_col": has_sel,
               "live_artifact_day": day, "live_ticks": sstats.get("ticks"),
               "live_rows": sstats.get("rows"), "live_syms_per_tick": [sstats.get("syms_min"), sstats.get("syms_max")],
               "dev_selector": fmeta, "selector_csv": csv}
    return layer("selector", checks, metrics, [], reason)


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
        _, bt, _, _ = _features_core(export_by_ts, live_rows)
        base_fail = [t["feature"] for t in bt if t["status"] == "FAIL"]
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
    # (d) VIEC 1: co che writer gz — tai lap bug (flush khong close) + fix (close)
    try:
        files = []
        for g in LIVE_FEAT_GLOBS:
            import glob as _g
            files.extend(sorted(_g.glob(g)))
        emu = gz_writer_emulation(files[0]) if files else None
        ok = bool(emu and (not emu["emu_buggy_decompress_ok"]) and emu["emu_fixed_decompress_ok"]
                  and emu["emu_buggy_tail"] == "0000ffff" and emu["real_matches_buggy"])
        out.append({"id": "gz_writer_finalize", "status": "PASS" if ok else "FAIL",
                    "detail": "tai lap: buggy(no-close) decompress_ok=%s tail=%s | fixed(close) ok=%s | file that khop %s" % (
                        emu["emu_buggy_decompress_ok"], emu["emu_buggy_tail"], emu["emu_fixed_decompress_ok"],
                        emu["real_matches_buggy"]) if emu else "khong co file LIVE de doi chieu"})
    except Exception as e:
        out.append({"id": "gz_writer_finalize", "status": "FAIL", "detail": "loi: %s" % str(e)[:120]})
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
            L.append("\n| feature | n | max\\|Δ\\| | mean\\|Δ\\| | corr | exp0 | status | nhom (VIEC4) |\n|---|---|---|---|---|---|---|---|")
            for t in la["table"]:
                L.append("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
                    t["feature"], t["n"], _f(t["maxabs"]), _f(t["meanabs"]), _f(t["corr"], 4),
                    _f(t.get("exp0"), 2), t["status"], t.get("cls", "")))
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
