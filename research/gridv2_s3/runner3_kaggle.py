"""runner3_kaggle.py - khung chay Giai doan S3 "WICK" (PREREG_GRIDV2_S3) tren lake vz-kline1m (row group = 1 symbol).
Copy tu runner_kaggle.py S1 ban ADD1 (sha 23a788cf...) roi doi PHAN MO PHONG / O / MERGE cho S3; GIU NGUYEN rao chan:
allowlist 7 slug, chan 2026, cam bien moi truong, assert hang so prereg, V0a/V0b/V1-V6 (V5 sua J1: phu 4 to hop model x side),
checkpoint, --expected-sha, du 5 shard, TEST_ONLY. Them (H2 audit S1): merge doi manifest.inputs GIONG HET 5 shard.
CHI viet + test tren parquet TONG HOP. KHONG push, KHONG chay tren du lieu that trong pha dev.

Che do:
  python3 runner3_kaggle.py run    -> doc lake (GRIDV3_INPUT), mo phong shard (GRIDV3_SHARD="i/K"), ghi reduced/ + validate.json
  python3 runner3_kaggle.py merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 d1 d2 d3 d4 -> result.json, diag.json
Bien moi truong van hanh (KHONG doi thong ke): GRIDV3_INPUT (/kaggle/input), GRIDV3_OUT (/kaggle/working), GRIDV3_SHARD (0/1),
  GRIDV3_KEEP_SYM (1 = giu checkpoint). MOI bien GRIDV3_* / GRIDV2_* khac (va 5 bien cam cua S1) -> abort.
"""
import os
import sys
import re
import glob
import json
import time
import hashlib
import logging
import zlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import klite3  # noqa: E402
import kref3   # noqa: E402
import stats   # noqa: E402
import stats3_extra  # noqa: E402

log = logging.getLogger("gridv2_s3")
MIN = 60000
DAY = 86400000
SEAL = 1767225600000                      # 2026-01-01 UTC: khong doc gi >= moc nay
DATA_START = 1619827200000                # 2021-05-01 (warm-up 2 thang)
STUDY_START = 1625097600000               # 2021-07-01
HALF_B = 1704067200000                    # 2024-01-01
# ---- hang so S3 (S3-2..S3-5)
W_ENTRY = 60
EXIT_FRAC = 0.5
C_LIST = (1.0, 1.5, 2.5)
T_LIST = (240, 1440)
CT_ALL = [(c, T) for c in C_LIST for T in T_LIST]          # 6 cap (c, T)
SIDES = ((1, "BUY"), (-1, "SELL"))
STRESS_SLIP_MULT = 5                      # S3-3: K_PESS truot het han x5 (chi bao cao)
FLOOR_BPS = 4.0
ALPHA_FWER = 0.04
ALPHA_UPPER = 0.05
MIN_UNITS = 200
P_HALF_A = 0.10
COND_PREREG = {"B": dict(ratio=1.5), "MKT": dict(z=1.0, win=60)}   # COND_B (chan doan) + "toan thi truong" (S3-8)
S3_CONST = dict(W_ENTRY=W_ENTRY, EXIT_FRAC=EXIT_FRAC, C_LIST=list(C_LIST), T_LIST=list(T_LIST), STRESS_SLIP_MULT=STRESS_SLIP_MULT,
                MIN_D_TICKS=klite3.MIN_D_TICKS, FEE_MAKER=dict(klite3.FEE_MAKER), FEE_TAKER=klite3.FEE_TAKER,
                DELIST_SLIP_PESS=klite3.DELIST_SLIP_PESS, SLIP_TIER_FLOOR={str(k): v for k, v in klite3.SLIP_TIER_FLOOR.items()},
                LONG_GAP_MIN=klite3.LONG_GAP_MIN, FLOOR_BPS=FLOOR_BPS, P_HALF_A=P_HALF_A)
MARKET_SYM = "BTCUSDT"
V4_SYMS = 2
N_SHARDS = 5
SHA_FILES = ("klite3.py", "kref3.py", "stats.py", "stats3_extra.py", "runner3_kaggle.py")
V2_MAX_BAD_FRAC = 0.001
V6_RATE_RANGE = (1e-5, 1e-3)
V6_INTERVALS = (1, 2, 4, 8)
SHAT_FFILL_DAYS = 7
ALLOWED_SLUGS = ("vz-kline1m-2021", "vz-kline1m-2022", "vz-kline1m-2023", "vz-kline1m-2024", "vz-kline1m-2025",
                 "gridp-t1-funding", "gridp-lifecycle")
ENV_OPS = ("GRIDV3_INPUT", "GRIDV3_OUT", "GRIDV3_SHARD", "GRIDV3_KEEP_SYM")
FORBIDDEN_ENV = ("GRIDV2_ALPHA", "GRIDV2_COND", "GRIDV2_MARKET_SYM", "GRIDV2_REGISTRY", "GRIDV2_V4_SYMS")
assert klite3.W_ENTRY == W_ENTRY and klite3.EXIT_FRAC == EXIT_FRAC and tuple(klite3.C_LIST) == C_LIST
assert tuple(klite3.T_LIST) == T_LIST and len(CT_ALL) == 6
assert klite3.FEE_MAKER == {"OPT": 2e-4, "PESS": 4e-4} and klite3.FEE_TAKER == 5e-4 and klite3.DELIST_SLIP_PESS == 50e-4
assert klite3.SLIP_TIER_FLOOR == {1: 2e-4, 2: 5e-4, 3: 10e-4} and klite3.MIN_D_TICKS == 4 and klite3.LONG_GAP_MIN == 60
assert ALPHA_FWER == 0.04 and ALPHA_UPPER == 0.05 and MIN_UNITS == 200 and FLOOR_BPS == 4.0, "hang so thong ke khac prereg"
assert stats.ALPHA_FWER == ALPHA_FWER and stats.ALPHA_UPPER == ALPHA_UPPER and stats.MIN_UNITS == MIN_UNITS
assert stats.BLOCK == 20 and stats.NBOOT == 2000 and stats3_extra.BLOCK == 20
REGISTRY_REAL = {2021: 60001411, 2022: 75973640, 2023: 104401093, 2024: 155015111, 2025: 256801320}
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "USDEUSDT"}
INDEXES = {"BTCDOMUSDT", "DEFIUSDT", "FOOTBALLUSDT", "BLUEBIRDUSDT"}
EVENTS = [("2022-05-09", "2022-05-13"), ("2022-11-08", "2022-11-10"), ("2025-10-10", "2025-10-13")]
EVENT_OCT25 = ("2025-10-10", "2025-10-13")
SEED_BOOT = 2026112140
SEED_V = 2026112141
HIST_W = 5.0                              # bps / bin (net don vi S3 lon: hang tram - hang nghin bps)
HIST_LIM = 10000                          # bin kep [-10000, 10000] = +-50 000 bps
SUM_COLS = ["place", "excl", "excl_gap", "fill", "net", "neth", "gross", "fee", "slip", "fund", "cap", "lim", "holdmin",
            "sx5", "net2", "net3"]
DIAG_COLS = ["place", "excl", "fill", "net", "neth", "gross", "lim", "holdmin"]
TABLES = ("agg", "shalf", "hist", "umin", "diag", "mon")
TKEYS = {"agg": ["cell", "model", "day"], "shalf": ["sym", "cell", "model", "half"], "hist": ["cell", "model", "half", "bin"],
         "umin": ["cell", "model", "half"], "diag": ["cell", "model", "half", "dim", "level"], "mon": ["cell", "model", "month"]}
TMIN = ("umin",)                          # bang gop bang MIN (con lai: SUM)


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cells():
    """12 o (S3-4): ben {BUY, SELL} x c {1,0; 1,5; 2,5} x T {240, 1440}, gop 3 tier. id = sidx*6 + ct."""
    out = []
    for sidx, (sd, sn) in enumerate(SIDES):
        for ci, (c, T) in enumerate(CT_ALL):
            out.append(dict(id=sidx * 6 + ci, side=sd, side_name=sn, ct=ci, c=c, T=T, stat="net",
                            name="%s_c%.1f_T%d" % (sn, c, T)))
    assert len(out) == 12 and [x["id"] for x in out] == list(range(12))
    return out


def cond_params(override=None):
    dflt = json.loads(json.dumps(COND_PREREG))
    for k, v in (override or {}).items():
        dflt[k].update(v)
    return dflt


def check_env():
    """Cam moi bien moi truong co the ghi de tham so: 5 bien S1 + MOI GRIDV2_* / GRIDV3_* ngoai 4 bien van hanh."""
    bad = [k for k in os.environ if k in FORBIDDEN_ENV or ((k.startswith("GRIDV3_") or k.startswith("GRIDV2_"))
                                                           and k not in ENV_OPS)]
    if bad:
        raise RuntimeError("bien moi truong bi cam (khong ghi de tham so prereg): %s" % sorted(bad))


def shat_exante(spread_daily):
    """s_hat cho ngay D = Abdi-Ranaldo ngay hop le gan nhat trong [D-7, D-1]; khong co -> NaN (shat_fill)."""
    return pd.Series(np.asarray(spread_daily, np.float64)).ffill(limit=SHAT_FFILL_DAYS - 1).shift(1).to_numpy()


def shat_fill(shat, tierv):
    fl = np.array([klite3.SLIP_TIER_FLOOR.get(int(t), klite3.SLIP_TIER_FLOOR[3]) for t in np.asarray(tierv).ravel()])
    sh = np.asarray(shat, np.float64)
    return np.where(np.isfinite(sh), sh, 2.0 * fl)


def v2_eval(by_year):
    fr = {int(y): (b / a if a > 0 else 0.0) for y, (b, a) in by_year.items()}
    mx = max(fr.values()) if fr else 0.0
    return bool(mx <= V2_MAX_BAD_FRAC), mx, fr


def v6_eval(frames):
    out, ok = {}, True
    for y, f in sorted(frames.items()):
        if len(f) == 0:
            out[int(y)] = dict(n=0)
            continue
        med = float(np.median(np.abs(f["rate"].to_numpy(np.float64))))
        ih = f["interval_h"].to_numpy(np.float64)
        inset = np.isin(np.round(ih, 6), V6_INTERVALS)
        inferred = bool(f.attrs.get("inferred", False))
        ok_i = bool(inset.mean() >= 0.99) if inferred else bool(inset.all())
        ok_r = V6_RATE_RANGE[0] <= med <= V6_RATE_RANGE[1]
        out[int(y)] = dict(n=int(len(f)), median_abs_rate=med, frac_interval_ok=float(inset.mean()), inferred=inferred,
                           ok=bool(ok_r and ok_i))
        ok = ok and ok_r and ok_i
    return bool(ok), out


# ------------------------------------------------------------------ kiem ke file (allowlist - giong S1)
def _slug_of(rel):
    """R3-6 (A1 F7): slug hop le phai la thu muc NGAY TREN file; khong thanh phan nao khac la slug hop le."""
    parts = rel.split(os.sep)
    hit = [p for p in parts[:-1] if p in ALLOWED_SLUGS]
    if len(hit) != 1 or len(parts) < 2 or parts[-2] != hit[0]:
        return None
    return hit[0]


def find_inputs(inp):
    kl, fu, lp, seen, prefixes = {}, {}, [], set(), set()
    for dp, dn, fn in os.walk(inp):
        dn.sort()
        for f in sorted(fn):
            rel = os.path.relpath(os.path.join(dp, f), inp)
            if "2026" in f:
                raise RuntimeError("file ten chua 2026 trong input - DUNG: %s" % rel)
            slug = _slug_of(rel)
            if slug is None:
                raise RuntimeError("file ngoai allowlist dataset - DUNG: %s" % rel)
            seen.add(slug)
            prefixes.add(os.sep.join(rel.split(os.sep)[:-2]))        # R3-6: moi slug phai o CUNG cap thu muc
            if not f.endswith(".parquet"):
                continue
            p = os.path.join(dp, f)
            if slug.startswith("vz-kline1m-"):
                m = re.fullmatch(r"kline1m-(\d{4})-(\d{2})\.parquet", f)
                if not m or m.group(1) != slug[-4:]:
                    raise RuntimeError("parquet la trong %s: %s" % (slug, rel))
                key = (int(m.group(1)), int(m.group(2)))
                if key in kl:
                    raise RuntimeError("kline trung thang: %s" % rel)
                kl[key] = p
            elif slug == "gridp-t1-funding":
                m = re.fullmatch(r"funding-(\d{4})\.parquet", f)
                if not m:
                    raise RuntimeError("parquet la trong %s: %s" % (slug, rel))
                y = int(m.group(1))
                if y >= 2026 or y in fu:
                    raise RuntimeError("funding nam %d khong hop le / trung: %s" % (y, rel))
                fu[y] = p
            else:
                if f != "lifecycle.parquet":
                    raise RuntimeError("parquet la trong %s: %s" % (slug, rel))
                lp.append(p)
    miss = sorted(set(ALLOWED_SLUGS) - seen)
    if miss:
        raise RuntimeError("thieu dataset trong allowlist: %s" % miss)
    if len(prefixes) != 1:
        raise RuntimeError("slug khong cung cap thu muc (thu muc la long slug?) - DUNG: %s" % sorted(prefixes))
    if len(lp) != 1:
        raise RuntimeError("can dung 1 lifecycle.parquet, thay %d" % len(lp))
    if any(y >= 2026 for y, _ in kl):
        raise RuntimeError("kline 2026 - DUNG")
    return kl, fu, lp[0]


_RG = {}


def rg_map(p):
    if p in _RG:
        return _RG[p]
    pf = pq.ParquetFile(p)
    m = {}
    for i in range(pf.num_row_groups):
        col = pf.read_row_group(i, columns=["sym"]).column("sym").combine_chunks()
        if hasattr(col, "dictionary"):
            u = col.dictionary.take(np.unique(np.asarray(col.indices))).to_pylist()
        else:
            u = list(set(col.to_pylist()))
        if len(u) != 1:
            raise RuntimeError("row group %d cua %s khong phai 1 symbol" % (i, p))
        m[str(u[0])] = i
    _RG[p] = (pf, m)
    return pf, m


class V:
    def __init__(self):
        self.v = dict(V0=dict(), V1=dict(bad=[], ts_min=None, ts_max=None), V2=dict(nan=0, nonpos=0, hl_bad=0, rows_active=0, by_year={}),
                      V3=dict(long_gaps=0, units_excl_gap=0, units_excl_noend=0, sym_month_missing=[], feat_mismatch_days=0,
                              units_skip_px=0, skip_px_by_cell={}),
                      V4=dict(), V5=dict(), V6=dict())

    def ts(self, t, y, mo, where):
        if t.size == 0:
            return
        a, b = int(t.min()), int(t.max())
        assert b < SEAL, "ts >= 2026 xuat hien"
        lo = ms("%04d-%02d-01" % (y, mo))
        hi = ms("%04d-%02d-01" % (y + (mo == 12), mo % 12 + 1))
        if a < lo or b >= hi:
            self.v["V1"]["bad"].append([where, a, b])
        v1 = self.v["V1"]
        v1["ts_min"] = a if v1["ts_min"] is None else min(v1["ts_min"], a)
        v1["ts_max"] = b if v1["ts_max"] is None else max(v1["ts_max"], b)


def valid_rows(t):
    a = t.column("active").to_numpy(zero_copy_only=False).astype(bool)
    cols = [t.column(c).to_numpy(zero_copy_only=False).astype(np.float64) for c in ("open", "high", "low", "close")]
    good = a & np.all([np.isfinite(c) & (c > 0) for c in cols], 0)
    return a, cols, good


# ------------------------------------------------------------------ V0a/V0b (ADD1 - giong S1)
V0_SKIP_EXPECTED_REAL = [[2021, 1], [2021, 2], [2021, 3]]


def v0_rule_skipped(y, mo):
    return ms("%04d-%02d-01" % (y, mo)) < DATA_START - 31 * DAY


def v0_eval(meta_file, opened, rows_read, registry, expect_skip=None):
    opened = {(int(a), int(b)) for a, b in opened}
    years = sorted({y for y, _ in meta_file})
    meta_y = {y: sum(n for (yy, _), n in meta_file.items() if yy == y) for y in years}
    skipped = sorted(k for k in meta_file if k not in opened)
    rule = sorted(k for k in meta_file if v0_rule_skipped(*k))
    ok_a = (registry is None) or all(meta_y.get(int(y)) == int(n) for y, n in registry.items())
    ok_b = skipped == rule and (expect_skip is None or [list(k) for k in skipped] == [list(k) for k in expect_skip])
    det = {}
    for y in years:
        mo_open = sum(n for k, n in meta_file.items() if k[0] == y and k in opened)
        mo_skip = sum(n for k, n in meta_file.items() if k[0] == y and k not in opened)
        rd = int(rows_read.get(y, 0))
        ok_y = rd == mo_open
        if registry is not None and int(y) in {int(k) for k in registry}:
            ok_y = ok_y and (int(registry[y]) - rd == mo_skip)
        det[int(y)] = dict(rows_read=rd, meta_opened=mo_open, meta_skipped=mo_skip, ok=bool(ok_y))
        ok_b = ok_b and ok_y
    files_skipped = [dict(file="kline1m-%04d-%02d.parquet" % k, meta_rows=int(meta_file[k])) for k in skipped]
    return bool(ok_a), bool(ok_b), dict(by_year=det, files_skipped=files_skipped, rule_skipped=[list(k) for k in rule])


# ------------------------------------------------------------------ pass 1 (giong S1)
def pass1(kl, VS, nday):
    qv, act, hc, rows = {}, {}, {}, {}
    for (y, mo), p in sorted(kl.items()):
        if ms("%04d-%02d-01" % (y, mo)) < DATA_START - 31 * DAY:
            continue
        VS.v["V0"].setdefault("files_opened", []).append([y, mo])
        pf, m = rg_map(p)
        for s, i in m.items():
            t = pf.read_row_group(i, columns=["ts", "open", "high", "low", "close", "quote_volume", "active"])
            ts = t.column("ts").to_numpy().astype(np.int64)
            VS.ts(ts, y, mo, "%s/%s" % (os.path.basename(p), s))
            rows[y] = rows.get(y, 0) + t.num_rows
            a, cols, good = valid_rows(t)
            o_, h_, l_, c_ = [c[a] for c in cols]
            fin = np.all([np.isfinite(c[a]) for c in cols], 0)
            VS.v["V2"]["rows_active"] += int(a.sum())
            VS.v["V2"]["nan"] += int((~fin).sum())
            VS.v["V2"]["nonpos"] += int(sum(((c[a] <= 0) & np.isfinite(c[a])).sum() for c in cols))
            by = VS.v["V2"]["by_year"].setdefault(y, [0, 0])
            by[0] += int((a & ~good).sum())
            by[1] += int(a.sum())
            with np.errstate(invalid="ignore"):
                VS.v["V2"]["hl_bad"] += int(((h_ < np.maximum(o_, c_) - 1e-12) | (l_ > np.minimum(o_, c_) + 1e-12)).sum())
            q = t.column("quote_volume").to_numpy(zero_copy_only=False).astype(np.float64)
            day = (ts - DATA_START) // DAY
            ok = good & (day >= 0) & (day < nday) & np.isfinite(q)
            if s not in qv:
                qv[s] = np.zeros(nday)
                act[s] = np.zeros(nday, np.int64)
                hc[s] = np.full(nday * 24, np.nan)
            qv[s] += np.bincount(day[ok], weights=q[ok], minlength=nday)
            act[s] += np.bincount(day[ok], minlength=nday)
            g2 = good & (day >= 0) & (day < nday)
            if g2.any():
                tt, cc = ts[g2], cols[3][g2]
                o = np.argsort(tt, kind="stable")
                tt, cc = tt[o], cc[o]
                hh = (tt - DATA_START) // 3600000
                last = np.r_[hh[1:] != hh[:-1], True]
                hc[s][hh[last]] = cc[last]
        log.info("pass1 %04d-%02d nsym=%d", y, mo, len(m))
    return qv, act, hc, rows


def load_life(path):
    d = pd.read_parquet(path)
    life = {}
    for r in d.itertuples():
        f = None if pd.isna(r.first_utc) else int(pd.Timestamp(r.first_utc).value // 10**6)
        if f is not None and f >= SEAL:
            continue
        l_ = None if pd.isna(r.last_utc) else int(pd.Timestamp(r.last_utc).value // 10**6)
        life[str(r.symbol)] = dict(first=f, last=l_, ascii=bool(getattr(r, "ascii", True)))
    return life


def eligible(s, life):
    return (s.endswith("USDT") and "_" not in s and s.isascii() and s not in STABLE and s not in INDEXES
            and s in life and life[s]["first"] is not None and life[s]["ascii"])


def build_tiers(qv, act, life, nday):
    syms = sorted(s for s in qv if eligible(s, life))
    Q = np.stack([qv[s] for s in syms]) if syms else np.zeros((0, nday))
    A = np.stack([act[s] for s in syms]) if syms else np.zeros((0, nday))
    cq = np.concatenate([np.zeros((len(syms), 1)), np.cumsum(Q, 1)], 1)
    tiers = {s: np.zeros(nday, np.int8) for s in syms}
    first = np.array([life[s]["first"] for s in syms], np.int64)
    last = np.array([life[s]["last"] if life[s]["last"] is not None else SEAL for s in syms], np.int64)
    d0 = (STUDY_START - DATA_START) // DAY
    names = np.array(syms)
    for D in range(d0, nday):
        tD = DATA_START + D * DAY
        ok = (first <= tD - 30 * DAY) & (last >= tD) & (A[:, D - 1] > 0)
        sc = cq[:, D] - cq[:, D - 30]
        ii = np.nonzero(ok)[0]
        order = ii[np.lexsort((names[ii], -sc[ii]))]
        for r, j in enumerate(order):
            tiers[syms[j]][D] = 1 if r < 10 else (2 if r < 60 else 3)
    return tiers


def daily_close_from_hourly(hcs, nday):
    a = hcs.reshape(nday, 24)
    fin = np.isfinite(a)
    la = 23 - np.argmax(fin[:, ::-1], 1)
    return np.where(fin.any(1), a[np.arange(nday), la], np.nan)


def pass1_features(tiers, hc, nday):
    """ER30, sigma_1d tu close gio pass1 (chi de doi chieu pass1 = pass2 o V3; S3 khong dung nguong cat ngang)."""
    er, sg = {}, {}
    for s in tiers:
        dc = daily_close_from_hourly(hc[s], nday)
        er[s] = klite3.er30(hc[s], nday)
        sg[s] = klite3.sigma_exante(dc)
    return er, sg


def load_symbol(kl, s, nday):
    n = nday * 1440
    O = np.full(n, np.nan); H = O.copy(); L = O.copy(); C = O.copy(); QV = np.zeros(n)
    valid = np.zeros(n, bool)
    for (y, mo), p in sorted(kl.items()):
        pf, m = rg_map(p)
        if s not in m:
            continue
        t = pf.read_row_group(m[s], columns=["ts", "open", "high", "low", "close", "quote_volume", "active"])
        ts = t.column("ts").to_numpy().astype(np.int64)
        assert ts.size == 0 or int(ts.max()) < SEAL
        idx = (ts - DATA_START) // MIN
        a, cols, good = valid_rows(t)
        q = t.column("quote_volume").to_numpy(zero_copy_only=False).astype(np.float64)
        k = good & (idx >= 0) & (idx < n)
        ii = idx[k]
        O[ii], H[ii], L[ii], C[ii] = cols[0][k], cols[1][k], cols[2][k], cols[3][k]
        QV[ii] = np.nan_to_num(q[k])
        valid[ii] = True
    return O, H, L, C, QV, valid


def load_funding(fu, syms, v6frames=None):
    out = {}
    for y, p in sorted(fu.items()):
        f = pd.read_parquet(p)
        assert f.empty or int(f.ts.max()) < SEAL, "funding >= 2026"
        f["sym"] = f["sym"].astype(str)
        inferred = "interval_h" not in f.columns
        if inferred:
            f = f.sort_values(["sym", "ts"])
            f["interval_h"] = (f.groupby("sym").ts.diff() / 3600000.0).round().fillna(8).clip(1, 8)
        if v6frames is not None:
            g6 = f[["rate", "interval_h"]].copy()
            g6.attrs["inferred"] = inferred
            v6frames[y] = g6
        f = f[f.sym.isin(syms)]
        for s, g in f.groupby("sym"):
            out.setdefault(s, []).append(g[["ts", "rate", "interval_h"]].to_numpy(np.float64))
    res = {}
    for s, parts in out.items():
        a = np.concatenate(parts)
        a = a[np.argsort(a[:, 0], kind="stable")]
        ts = a[:, 0].astype(np.int64)
        keep = np.r_[True, np.diff(ts) > 0]
        res[s] = (ts[keep], a[keep, 1], a[keep, 2])
    return res


def delist_index(s, life, valid):
    l_ = life.get(s, {}).get("last")
    if l_ is None or l_ >= SEAL - DAY:
        return -1
    lim = (l_ - DATA_START) // MIN
    v = np.nonzero(valid[: lim + 1])[0]
    return int(v[-1]) if v.size else -1


def market_context(arrays, dl, nday):
    """Boi canh BTC: luoi phut (C, lv), close ngay, sigma_1d ex-ante, ti le RV24/sigma theo gio (COND_B)."""
    G = klite3.prepare_grid(*arrays[:4], arrays[5], dl)
    hc = klite3.hourly_close(G, nday)
    dc = daily_close_from_hourly(hc, nday)
    sig = klite3.sigma_exante(dc)
    hcs = np.r_[np.nan, hc[:-1]]
    lr = np.r_[np.nan, np.diff(np.log(hcs))]
    sq = np.where(np.isfinite(lr), lr * lr, 0.0)
    okc = np.isfinite(lr).astype(np.int64)
    cs, cn = np.r_[0.0, np.cumsum(sq)], np.r_[0, np.cumsum(okc)]
    Hh = np.arange(nday * 24)
    a = np.clip(Hh - 23, 0, None)
    rv = np.sqrt(cs[Hh + 1] - cs[a])
    cnt = cn[Hh + 1] - cn[a]
    sd = sig[Hh // 24]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.where((cnt >= 20) & np.isfinite(sd) & (sd > 0), rv / sd, np.nan)
    return dict(C=G["C"], lv=G["lv"], dc=dc, sig=sig, ratio=ratio)


# ------------------------------------------------------------------ pass 2: 1 symbol, 12 o x 2 mo hinh
def _diag_add(diag, key, mask, cols):
    if not mask.any():
        return
    a_ = diag.setdefault(key, np.zeros(len(DIAG_COLS)))
    a_ += [cols[c][mask].sum() for c in DIAG_COLS]


def process_symbol(s, arrays, ctx, collect_units=False):
    """Mo phong 12 o S3 cho 1 symbol. ctx: nday, tier, fund (ts, rate, ih) | None, dl, mkt (dict) | None, mkt_sym, CP,
    er_p1, sig_p1 (pass1, doi chieu V3; None = bo qua), models (tuy chon)."""
    nday = ctx["nday"]
    O, H, L, C, QV, valid = arrays
    dl = ctx["dl"]
    G = klite3.prepare_grid(O, H, L, C, valid, dl)
    feat = klite3.daily_features(G, nday)
    sig = klite3.sigma_exante(feat["close"])
    hc = klite3.hourly_close(G, nday)
    er = klite3.er30(hc, nday)
    mism = 0
    if ctx.get("sig_p1") is not None:
        for a1, a2 in ((ctx["sig_p1"], sig), (ctx["er_p1"], er)):
            mism += int(np.sum(~((np.isnan(a1) & np.isnan(a2)) | (np.abs(np.nan_to_num(a1) - np.nan_to_num(a2)) < 1e-12))))
    mkt = ctx["mkt"]
    beta = klite3.beta_btc(feat["close"], mkt["dc"]) if mkt is not None else np.ones(nday)
    fu = ctx.get("fund")
    tick_c = pd.Series(feat["tick"]).ffill().shift(1).to_numpy()
    spr_c = shat_exante(feat["spread"])
    n = G["n"]
    # R3-7 (chi chan doan): trung vi quote_volume / phut hop le cua NGAY D-1
    qvm = np.where(G["valid"][: nday * 1440], np.asarray(QV, np.float64)[: nday * 1440], np.nan).reshape(nday, 1440)
    with np.errstate(all="ignore"):
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            qv_med = np.r_[np.nan, np.nanmedian(qvm, 1)[:-1]]
    fs = fr = None
    if fu is not None:
        fs = (fu[0] - DATA_START) // MIN
        k = (fs >= 1) & (fs < n)
        fs, fr = fs[k], fu[1][k]
    d0 = (STUDY_START - DATA_START) // DAY
    days = np.arange(d0, nday)
    D_all = np.repeat(days, 24)
    h_all = np.tile(np.arange(24), days.size)
    t0_all = D_all * 1440 + h_all * 60
    tier_all = np.repeat(ctx["tier"][days], 24)
    base_ok = (tier_all > 0) & np.isfinite(sig[D_all]) & np.isfinite(tick_c[D_all]) & G["valid"][t0_all - 1]
    if dl >= 0:
        base_ok &= t0_all - 1 <= dl
    m0_all = np.where(base_ok, G["C"][t0_all - 1], np.nan)
    CP = ctx["CP"]
    if mkt is not None:
        hh = D_all * 24 + h_all
        rb = mkt["ratio"][hh]
        condB = np.where(np.isfinite(rb), np.where(rb >= CP["B"]["ratio"], "yes", "no"), "na")
    else:
        condB = np.full(D_all.size, "na")
    half_d = np.where(DATA_START + np.arange(nday) * DAY >= HALF_B, 1, 0)
    dts = pd.to_datetime(DATA_START + np.arange(nday) * DAY, unit="ms")
    month_d = dts.strftime("%Y-%m").to_numpy()
    year_d = np.char.add("y", dts.strftime("%Y").to_numpy().astype(str))
    ag_rows, sh_rows, hist, umin, diag, mon, units = [], [], {}, {}, {}, {}, {}
    skip_px = {}
    for ci, (c, T) in enumerate(CT_ALL):
        d = c * sig[D_all]
        tick = tick_c[D_all]
        with np.errstate(invalid="ignore"):
            sel = base_ok & (d * m0_all >= klite3.MIN_D_TICKS * tick) & (t0_all + W_ENTRY + T + klite3.LONG_GAP_MIN + 1 <= n)
        ii = np.nonzero(sel)[0]
        if ii.size == 0:
            continue
        pi = np.r_[ii, ii]
        side = np.r_[np.ones(ii.size, np.int8), -np.ones(ii.size, np.int8)]
        Lb, Xb, Ls, Xs = klite3.levels(m0_all[pi], d[pi], tick[pi])
        posok = np.where(side == 1, (Lb > 0) & (Xb > Lb), (Xs > 0) & (Xs < Ls))   # muc gia <= 0 -> khong dat (L-S3-3)
        for sidx, (sd, _) in enumerate(SIDES):
            nbad = int(((side == sd) & ~posok).sum())
            if nbad:
                skip_px[sidx * 6 + ci] = skip_px.get(sidx * 6 + ci, 0) + nbad
        pi, side = pi[posok], side[posok]
        if pi.size == 0:
            continue
        sidef = side.astype(float)
        tierv = tier_all[pi]
        shat = shat_fill(spr_c[D_all[pi]], tierv)
        slip = np.maximum(np.array([klite3.SLIP_TIER_FLOOR[int(t)] for t in tierv]), shat / 2.0)
        Du = D_all[pi]
        hv_u = half_d[Du]
        for model in ctx.get("models", ("OPT", "PESS")):
            R = klite3.run_units(G, t0_all[pi], d[pi], W_ENTRY, T, tick[pi], slip, model, side, fs, fr)
            ok = R["filled"] & (R["excl"] == 0)
            hedge = np.zeros(pi.size)
            mflag = np.full(pi.size, "na", dtype=object)
            if mkt is not None:
                fb = mkt["lv"][np.clip(R["f"], 0, None)]
                xb = mkt["lv"][np.clip(R["x"], 0, None)]
                f60 = mkt["lv"][np.clip(R["f"] - CP["MKT"]["win"], 0, None)]
                with np.errstate(all="ignore"):
                    Bf = np.where(fb >= 0, mkt["C"][np.clip(fb, 0, None)], np.nan)
                    Bx = np.where(xb >= 0, mkt["C"][np.clip(xb, 0, None)], np.nan)
                    B60 = np.where((f60 >= 0) & (R["f"] - CP["MKT"]["win"] >= 0), mkt["C"][np.clip(f60, 0, None)], np.nan)
                    hedge = np.nan_to_num(np.where(ok, sidef * beta[Du] * (Bx - Bf) / Bf * 1e4, 0.0))
                    rbt = np.log(Bf / B60)
                    thr = CP["MKT"]["z"] * mkt["sig"][Du] / np.sqrt(24.0)
                    fin = np.isfinite(rbt) & np.isfinite(thr)
                    mw = np.where(side == 1, rbt <= -thr, rbt >= thr)
                mflag = np.where(ok & fin, np.where(mw, "market", "idio"), "na")
            # R3-7 (chi chan doan, HAU NGHIEM): qv phut khop / trung vi qv phut ngay D-1; rau 1 phut co lap
            fi_ = np.clip(R["f"], 1, n - 2)
            with np.errstate(all="ignore"):
                qr = np.asarray(QV, np.float64)[fi_] / qv_med[Du]
                qvl = np.where(ok & np.isfinite(qr) & (qv_med[Du] > 0),
                               np.where(qr < 1, "lt1", np.where(qr <= 10, "1_10", "gt10")), "na")
                lo_f, lo_a, lo_b = G["L"][fi_], G["L"][fi_ - 1], G["L"][fi_ + 1]
                hi_f, hi_a, hi_b = G["H"][fi_], G["H"][fi_ - 1], G["H"][fi_ + 1]
                fin3 = np.where(side == 1, np.isfinite(lo_f) & np.isfinite(lo_a) & np.isfinite(lo_b),
                                np.isfinite(hi_f) & np.isfinite(hi_a) & np.isfinite(hi_b))
                iso = np.where(side == 1, lo_f < np.minimum(lo_a, lo_b) * (1 - 0.5 * d[pi]),
                               hi_f > np.maximum(hi_a, hi_b) * (1 + 0.5 * d[pi]))
            wkl = np.where(ok & fin3, np.where(iso, "iso", "not"), "na")
            net = np.where(ok, R["net"], 0.0)
            neth = np.where(ok, R["net"] - hedge, 0.0)
            stress = ok & ((R["kind"] == klite3.EX_TIMEOUT) | (R["kind"] == klite3.EX_TAKER_BEYOND))
            sx5 = np.where(stress & (model == "PESS"), (STRESS_SLIP_MULT - 1) * np.nan_to_num(R["slip"]), 0.0)
            colz = dict(place=np.ones(pi.size), excl=(R["excl"] != 0).astype(float), excl_gap=(R["excl"] == 1).astype(float),
                        fill=ok.astype(float), net=net, neth=neth, gross=np.where(ok, R["gross"], 0.0),
                        fee=np.where(ok, R["fee"], 0.0), slip=np.where(ok, R["slip"], 0.0), fund=np.where(ok, R["fund"], 0.0),
                        cap=np.where(ok, shat / 2.0 * R["n_maker"] * 1e4, 0.0), lim=(ok & (R["kind"] == klite3.EX_LIMIT)).astype(float),
                        holdmin=np.where(ok, R["x"] - R["f"], 0).astype(float), sx5=sx5, net2=net ** 2, net3=net ** 3)
            dcols = dict(colz)
            for sidx, (sd, _) in enumerate(SIDES):
                cid = sidx * 6 + ci
                m_ = side == sd
                if not m_.any():
                    continue
                sm = {kk: np.bincount(Du[m_], weights=v[m_], minlength=nday) for kk, v in colz.items()}
                dd = np.nonzero(sm["place"])[0]
                df = pd.DataFrame({kk: v[dd] for kk, v in sm.items()})
                df["day"], df["cell"], df["model"] = dd, cid, model
                ag_rows.append(df)
                for hv in (0, 1):
                    mh = m_ & (hv_u == hv)
                    mm = mh & ok
                    if mm.any():
                        sh_rows.append(dict(sym=s, cell=cid, model=model, half=hv, net=net[mm].sum(), neth=neth[mm].sum(),
                                            fill=float(mm.sum())))
                        nb = np.clip(np.floor(net[mm] / HIST_W).astype(np.int64), -HIST_LIM, HIST_LIM)
                        u_, cnt = np.unique(nb, return_counts=True)
                        hd = hist.setdefault((cid, model, hv), {})
                        for b_, c_ in zip(u_.tolist(), cnt.tolist()):
                            hd[b_] = hd.get(b_, 0) + c_
                        k_ = (cid, model, hv)
                        umin[k_] = min(umin.get(k_, np.inf), float(net[mm].min()))
                    if not mh.any():
                        continue
                    # ---- chan doan S3-8 (chi bao cao)
                    for dim, lab in (("tier", np.char.add("T", tierv.astype(str))), ("year", year_d[Du]),
                                     ("hour", np.char.add("h", h_all[pi].astype(str))), ("condB", condB[pi])):
                        for lv in np.unique(lab[mh]):
                            _diag_add(diag, (cid, model, hv, dim, str(lv)), mh & (lab == lv), dcols)
                    z = dict(dcols, place=np.zeros(pi.size), excl=np.zeros(pi.size))
                    for dim, lab in (("mkt", mflag), ("qvratio", qvl), ("wick1m", wkl)):
                        for lv in np.unique(lab[mh & ok]):
                            _diag_add(diag, (cid, model, hv, dim, str(lv)), mh & ok & (lab == lv), z)
                mo_u = month_d[Du]
                for mo_ in np.unique(mo_u[m_ & ok]):
                    mm = m_ & ok & (mo_u == mo_)
                    a_ = mon.setdefault((cid, model, str(mo_)), np.zeros(2))
                    a_ += [mm.sum(), net[mm].sum()]
            if collect_units:
                units[(ci, model)] = dict(R=R, t0=t0_all[pi], side=side, d=d[pi], T=T, tick=tick[pi], slip=slip, D=Du,
                                          neth=np.where(ok, R["net"] - hedge, np.nan), beta=beta[Du], ok=ok, mflag=mflag)
    agg = pd.concat(ag_rows, ignore_index=True) if ag_rows else pd.DataFrame(columns=SUM_COLS + ["day", "cell", "model"])
    agg["sym"] = s
    shalf = pd.DataFrame(sh_rows, columns=["sym", "cell", "model", "half", "net", "neth", "fill"])
    hrows = [dict(cell=k[0], model=k[1], half=k[2], bin=b, count=c) for k, hd in hist.items() for b, c in hd.items()]
    urows = [dict(cell=k[0], model=k[1], half=k[2], net_min=v) for k, v in umin.items()]
    drows = [dict(cell=k[0], model=k[1], half=k[2], dim=k[3], level=k[4], **{c: v[i] for i, c in enumerate(DIAG_COLS)})
             for k, v in diag.items()]
    mrows = [dict(cell=k[0], model=k[1], month=k[2], fill=v[0], net=v[1]) for k, v in mon.items()]
    return dict(agg=agg, shalf=shalf, hist=pd.DataFrame(hrows, columns=TKEYS["hist"] + ["count"]),
                umin=pd.DataFrame(urows, columns=TKEYS["umin"] + ["net_min"]),
                diag=pd.DataFrame(drows, columns=TKEYS["diag"] + DIAG_COLS),
                mon=pd.DataFrame(mrows, columns=TKEYS["mon"] + ["fill", "net"]),
                units=units, skip_px=skip_px,
                aux=dict(G=G, sig=sig, er=er, beta=beta, tick=tick_c, shat=spr_c, tier=np.asarray(ctx["tier"]).copy(),
                         mkt_sig=(mkt["sig"].copy() if mkt is not None else None), feat_mismatch=mism, t0_all=t0_all,
                         base_ok=base_ok))


# ------------------------------------------------------------------ V4: khong nhin tuong lai (ADD1 R5-2, giong S1)
V4_MIN_SPAN_DAYS = 90
V4_LEAD_DAYS, V4_TAIL_DAYS = 45, 15


def v4_pick(valid):
    ii = np.nonzero(valid)[0]
    if ii.size == 0:
        return False, None, None, "khong co phut hop le"
    a, b = int(ii[0]), int(ii[-1])
    if b - a < V4_MIN_SPAN_DAYS * 1440:
        return False, a, b, "span %.1f ngay < %d" % ((b - a) / 1440.0, V4_MIN_SPAN_DAYS)
    lo = max(a + V4_LEAD_DAYS * 1440, (STUDY_START - DATA_START) // MIN + V4_LEAD_DAYS * 1440)
    hi = b - V4_TAIL_DAYS * 1440
    if lo > hi:
        return False, lo, hi, "khoang tc rong (du lieu ket thuc truoc STUDY_START + 60 ngay)"
    return True, lo, hi, ""


def v4_check(s, arrays, ctx, rng, tc_range=None, junk_lead_min=0):
    """Rac sau moc tc (gia, active, qv, tier, funding, BTC: gia, sigma, ratio, close ngay) -> moi don vi ket thuc truoc tc phai
    giong het (khop, thoat, ket qua, net_h, co 'toan thi truong'). junk_lead_min CHI cho test (rac bat dau som -> phai FAIL)."""
    nday = ctx["nday"]
    d0 = (STUDY_START - DATA_START) // DAY
    if tc_range is None:
        tc_day = int(rng.integers(d0 + 60, nday - 30))
        tc = tc_day * 1440 + int(rng.integers(0, 1440))
    else:
        tc = int(rng.integers(tc_range[0], tc_range[1] + 1))
        tc_day = tc // 1440
    a1 = process_symbol(s, arrays, ctx, collect_units=True)
    O, H, L, C, QV, valid = [x.copy() for x in arrays]
    tj = tc - int(junk_lead_min)
    tc, tc_true = tj, tc
    tc_day = tc // 1440
    nn = O.size - tc
    junk = np.exp(rng.normal(0, 3, nn))
    O[tc:], C[tc:] = junk, junk[::-1]
    H[tc:], L[tc:] = np.maximum(O[tc:], C[tc:]) * 1.5, np.minimum(O[tc:], C[tc:]) * 0.5
    QV[tc:] = rng.random(nn) * 1e12
    valid[tc:] = rng.random(nn) < 0.5
    c2 = dict(ctx)
    c2["sig_p1"] = None
    c2["tier"] = ctx["tier"].copy()
    c2["tier"][tc_day + 1:] = rng.integers(0, 4, nday - tc_day - 1)
    if ctx.get("fund") is not None:
        fsm, frr, fih = ctx["fund"]
        c2["fund"] = (fsm, np.where(fsm >= DATA_START + tc * MIN, rng.normal(0, 0.01, frr.size), frr), fih)
    if ctx["mkt"] is not None:
        mk = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in ctx["mkt"].items()}
        mk["C"][tc:] = np.exp(rng.normal(5, 1, mk["C"].size - tc))
        mk["ratio"][tc // 60 + 1:] = rng.random(mk["ratio"].size - tc // 60 - 1) * 3
        mk["dc"][tc_day:] = np.exp(rng.normal(5, 1, nday - tc_day))
        mk["sig"][tc_day + 1:] = rng.random(nday - tc_day - 1)
        c2["mkt"] = mk
    a2 = process_symbol(s, (O, H, L, C, QV, valid), c2, collect_units=True)
    nchk, nbad = 0, 0
    for key, u1 in a1["units"].items():
        R1 = u1["R"]
        end1 = np.where(R1["filled"], R1["x"], u1["t0"] + W_ENTRY - 1)
        keep = (end1 < tc_true - 2) & (u1["t0"] < tc_true)
        u2 = a2["units"].get(key)
        if u2 is None:
            nbad += int(keep.sum())
            continue
        pos2 = {(int(t), int(sd)): i for i, (t, sd) in enumerate(zip(u2["t0"], u2["side"]))}
        R2 = u2["R"]
        for i in np.nonzero(keep)[0]:
            nchk += 1
            j = pos2.get((int(u1["t0"][i]), int(u1["side"][i])))
            if j is None:
                nbad += 1
                continue
            same = (R1["filled"][i] == R2["filled"][j] and R1["excl"][i] == R2["excl"][j] and
                    (not u1["ok"][i] or (R1["net"][i] == R2["net"][j] and R1["x"][i] == R2["x"][j] and R1["kind"][i] == R2["kind"][j]
                                         and u1["neth"][i] == u2["neth"][j] and u1["mflag"][i] == u2["mflag"][j])))
            nbad += 0 if same else 1
    # R3-4 (A1 F5): mang feature theo ngay (sigma_1d, tick, s_hat, beta, tier, sigma BTC) giong het cho moi ngay <= ngay cua tc
    dtc = tc_true // 1440
    feat_diff = {}
    for k_ in ("sig", "tick", "shat", "beta", "tier", "mkt_sig"):
        x1, x2 = a1["aux"][k_], a2["aux"][k_]
        if x1 is None and x2 is None:
            continue
        x1, x2 = np.asarray(x1, float)[: dtc + 1], np.asarray(x2, float)[: dtc + 1]
        same_ = (np.isnan(x1) & np.isnan(x2)) | (x1 == x2)
        feat_diff[k_] = int((~same_).sum())
    nfd = int(sum(feat_diff.values()))
    return dict(sym=s, tc_min=int(tc_true), tc_range=(None if tc_range is None else [int(tc_range[0]), int(tc_range[1])]),
                n_checked=nchk, n_diff=nbad, feat_days_checked=int(dtc + 1), feat_diff=feat_diff,
                ok=(nchk > 0 and nbad == 0 and nfd == 0))


# ------------------------------------------------------------------ V5: doc lai tho + kref3 (sua J1: 12 o-vi tri co dinh)
def _raw_bars(kl, s, lo_ms, hi_ms):
    rows = []
    for (y, mo), p in sorted(kl.items()):
        a = ms("%04d-%02d-01" % (y, mo))
        b = ms("%04d-%02d-01" % (y + (mo == 12), mo % 12 + 1))
        if b <= lo_ms or a > hi_ms:
            continue
        rows.append(pq.read_table(p, columns=["ts", "sym", "open", "high", "low", "close", "active"],
                                  filters=[("sym", "=", s)]).to_pandas())
    nmin = int((hi_ms - lo_ms) // MIN) + 1
    Ol, Hl, Ll, Cl = [None] * nmin, [None] * nmin, [None] * nmin, [None] * nmin
    if not rows:
        return Ol, Hl, Ll, Cl
    df = pd.concat(rows)
    df = df[(df.ts >= lo_ms) & (df.ts <= hi_ms) & df.active.astype(bool)]
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    for r in df.itertuples():
        k = int((r.ts - lo_ms) // MIN)
        Ol[k], Hl[k], Ll[k], Cl[k] = float(r.open), float(r.high), float(r.low), float(r.close)
    return Ol, Hl, Ll, Cl


def _dclose(Cl, nd):
    out = []
    for dd in range(nd):
        seg = [v for v in Cl[dd * 1440:(dd + 1) * 1440] if v is not None]
        out.append(seg[-1] if seg else None)
    return out


# 12 vi tri V5 = 6 cap (c,T) x 2 ben; mo hinh xen ke de moi cap co CA 2 mo hinh va moi to hop (mo hinh, ben) co 3 vi tri (sua J1)
V5_SLOTS = [(ci, sd, ("OPT" if (ci % 2 == 0) == (sd == 1) else "PESS")) for ci in range(len(CT_ALL)) for sd in (1, -1)]
V5_N = len(V5_SLOTS)


def _other(model):
    return "PESS" if model == "OPT" else "OPT"


def v5_select(res, need, rng):
    """Chon tat dinh (rng co dinh theo shard) 1 don vi DA KHOP cho moi vi tri con thieu (ci, ben, mo hinh). Tra [(slot, key, i)]."""
    picks = []
    for slot in sorted(need, key=lambda s_: (s_[0], -s_[1], s_[2])):
        ci, sd, model = slot
        u = res["units"].get((ci, model))
        if u is None:
            continue
        cand = np.nonzero(u["ok"] & (u["side"] == sd))[0]
        if cand.size:
            picks.append((slot, (ci, model), int(rng.choice(cand))))
    return picks


V5_MAX_UNCOVERED = 2                      # R2 (MASTER P2): toi da 2 / 12 (c,T,ben) khong phu trong 1 shard


def v5_finalize(v5, need, fb):
    """R2 (MASTER P2) sau khi duyet HET symbol: vi tri con thieu -> dung don vi du phong (mo hinh con lai, cung (c,T,ben)) neu co
    (ghi v5_fallback); khong co -> (c,T,ben) 'uncovered'. Tra (v5 day du, fallback, uncovered)."""
    out = list(v5)
    fallback, uncovered = [], []
    for slot in sorted(need, key=V5_SLOTS.index):
        if slot in fb:
            x = dict(fb[slot], fallback=True, slot=list(slot))
            out.append(x)
            fallback.append(dict(slot=list(slot), used_model=x["model"], sym=x["sym"], t0=x["t0"], ok=x["ok"]))
        else:
            uncovered.append([slot[0], slot[1]])
    return out, fallback, uncovered


def v5_eval(v5, fallback=(), uncovered=(), extra_checked=()):
    """V5 PASS (R2, MASTER P2) = moi don vi da so khop kref3 VA so (c,T,ben) KHONG duoc phu (boi vi tri chinh hoac du phong)
    <= 2 / 12. covered_ctside dung cho merge (moi (c,T,ben) phai duoc phu boi >= 1 shard)."""
    covered = sorted({(x["ct"], x["side"]) for x in v5}, key=lambda k: (k[0], -k[1]))
    allcs = [(ci, sd) for ci in range(len(CT_ALL)) for sd in (1, -1)]
    unc = [list(k) for k in allcs if k not in covered]
    combos = sorted({(x["model"], x["side"]) for x in v5})
    extra = list(extra_checked)                   # R3-5 (A1 F6): don vi du phong DA doi chieu nhung khong dung - van phai khop kref3
    ok = len(v5) >= 1 and all(x["ok"] for x in v5) and all(x["ok"] for x in extra) and len(unc) <= V5_MAX_UNCOVERED
    return dict(checks=v5, checks_fallback_unused=extra, n_fallback_unused_bad=int(sum(not x["ok"] for x in extra)),
                covered_ctside=[list(k) for k in covered], uncovered=unc, v5_fallback=list(fallback),
                combos=[list(c) for c in combos], n_checked=len(v5),
                checked=[[x["sym"], x["t0"], x["c"], x["T"], x["side"], x["model"]] for x in v5], ok=bool(ok))


def v5_check(s, kl, fu_paths, life, res, ctx, picks):
    out = []
    mkt_sym = ctx["mkt_sym"]
    aux = res["aux"]
    for slot, key, i in picks:
        u = res["units"][key]
        R = u["R"]
        t0 = int(u["t0"][i])
        D = t0 // 1440
        base = DATA_START + (D - 32) * DAY
        hi_ms = DATA_START + (int(R["x"][i]) + 5) * MIN
        Ol, Hl, Ll, Cl = _raw_bars(kl, s, base, hi_ms)
        Cb = _raw_bars(kl, mkt_sym, base, hi_ms)[3]
        nmin = len(Cl)
        dclose, dcb = _dclose(Cl, 32), _dclose(Cb, 32)
        sg = kref3.ref_sigma(dclose, 32)
        prev = []
        for v in (Ol, Hl, Ll, Cl):
            prev += [x for x in v[31 * 1440:32 * 1440] if x is not None]
        tk = kref3.ref_tick(prev)
        beta_r = kref3.ref_beta(dclose, dcb, 32)
        fl = []
        for y, p in sorted(fu_paths.items()):
            f = pd.read_parquet(p)
            f = f[(f.sym.astype(str) == s)]
            for t_, rt in zip(f.ts, f.rate):
                if base <= t_ <= hi_ms:
                    fl.append((int((t_ - base) // MIN), float(rt)))
        fl.sort()
        dl = -1
        l_ = life.get(s, {}).get("last")
        if l_ is not None and l_ < SEAL - DAY:
            vi = [k for k in range(nmin) if Cl[k] is not None and base + k * MIN <= l_]
            dl = vi[-1] if vi and (base + (nmin - 1) * MIN) > l_ else -1
        c, T = CT_ALL[key[0]]
        sd = int(u["side"][i])
        off = (D - 32) * 1440
        rr = kref3.simulate_unit(Ol, Hl, Ll, Cl, t0 - off, c * sg, W_ENTRY, int(T), tk, float(u["slip"][i]), key[1], sd, fl, dl,
                                 xfrac=EXIT_FRAC)
        okv = (rr["filled"] and rr["excl"] == 0 and rr["f"] + off == int(R["f"][i]) and rr["x"] + off == int(R["x"][i])
               and rr["kind"] == klite3.EXIT_NAMES[int(R["kind"][i])] and abs(rr["net"] - R["net"][i]) < 1e-9
               and abs(c * sg - u["d"][i]) < 1e-12 and tk == u["tick"][i] and abs(beta_r - aux["beta"][D]) < 1e-9)
        out.append(dict(sym=s, ct=key[0], c=c, T=int(T), model=key[1], side=sd, t0=t0, kind=rr.get("kind"),
                        net_main=float(R["net"][i]), net_ref=rr.get("net"), beta=[float(aux["beta"][D]), beta_r], ok=bool(okv)))
    return out


def save_tables(res, base):
    for t in TABLES:
        res[t].to_parquet("%s.%s.parquet" % (base, t), index=False)


def _reduce(df, t):
    kk = TKEYS[t]
    if "sym" in df.columns and "sym" not in kk:
        df = df.drop(columns=["sym"])
    g = df.groupby(kk, as_index=False)
    return g.min(numeric_only=True) if t in TMIN else g.sum(numeric_only=True)


def reduce_tables(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for t in TABLES:
        parts = [pd.read_parquet(p) for p in sorted(glob.glob(os.path.join(src_dir, "*.%s.parquet" % t)))]
        parts = [p for p in parts if len(p)]
        if not parts:
            continue
        _reduce(pd.concat(parts, ignore_index=True), t).to_parquet(os.path.join(dst_dir, "%s.parquet" % t), index=False)


# ------------------------------------------------------------------ run
def _v3_sym(res, arr, nday, s):
    G = res["aux"]["G"]
    lg = np.diff(np.r_[0, G["lgc"]])
    out = dict(long_gaps=int(np.sum(np.diff(np.r_[0, (lg > 0).astype(np.int8)]) == 1)),
               feat_mismatch_days=int(res["aux"]["feat_mismatch"]), units_excl_gap=0, units_excl_noend=0, sym_month_missing=[],
               units_skip_px=int(sum(res["skip_px"].values())), skip_px_by_cell={str(k): int(v) for k, v in res["skip_px"].items()})
    ag = res["agg"]
    if len(ag):
        out["units_excl_gap"] = int(ag.excl_gap.sum())
        out["units_excl_noend"] = int((ag.excl - ag.excl_gap).sum())
    vv = arr[5].reshape(nday, 1440).sum(1)
    for mo_start in range(0, nday, 30):
        seg = vv[mo_start:mo_start + 30]
        live = seg[seg > 0]
        if live.size:
            miss = 100.0 * (1 - live.sum() / (live.size * 1440.0))
            if miss > 1.0:
                out["sym_month_missing"].append([s, int(mo_start), round(float(miss), 3)])
    return out


def run(test_overrides=None):
    """Chay 1 shard. test_overrides (CHI test noi bo, khong co duong vao tu CLI / env): dict registry / mkt_sym / cond / v4_syms."""
    check_env()
    tov = dict(test_overrides or {})
    inp = os.environ.get("GRIDV3_INPUT", "/kaggle/input")
    out = os.environ.get("GRIDV3_OUT", "/kaggle/working")
    os.makedirs(os.path.join(out, "agg_sym"), exist_ok=True)
    fh = logging.FileHandler(os.path.join(out, "run.log"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=[logging.StreamHandler(sys.stdout), fh],
                        force=True)
    si, sk = [int(x) for x in os.environ.get("GRIDV3_SHARD", "0/1").split("/")]
    registry = tov.get("registry", REGISTRY_REAL)
    if registry is not None:
        registry = {int(k): v for k, v in registry.items()}
    mkt_sym = tov.get("mkt_sym", MARKET_SYM)
    CP = cond_params(tov.get("cond"))
    nv4 = int(tov.get("v4_syms", V4_SYMS))
    prereg_constants = not tov
    t_start = time.time()
    VS = V()
    kl, fu, lpath = find_inputs(inp)
    nday = (SEAL - DATA_START) // DAY
    meta, meta_file = {}, {}
    for (y, mo), p in kl.items():
        meta_file[(y, mo)] = pq.ParquetFile(p).metadata.num_rows
        meta[y] = meta.get(y, 0) + meta_file[(y, mo)]
    VS.v["V0"].update(meta_rows=meta, registry=registry,
                      ok_registry=(registry is None) or all(meta.get(y) == registry[y] for y in registry))
    life = load_life(lpath)
    qv, act, hc, rows = pass1(kl, VS, nday)
    VS.v["V0"]["rows_read_pass1"] = rows
    ok0a, ok0b, d0b = v0_eval(meta_file, VS.v["V0"].get("files_opened", []), rows, registry,
                              V0_SKIP_EXPECTED_REAL if registry == REGISTRY_REAL else None)
    VS.v["V0"].update(ok_V0a=ok0a, ok_V0b=ok0b, V0b=d0b)
    VS.v["V0"]["ok_registry"] = bool(VS.v["V0"]["ok_registry"] and ok0a)
    VS.v["V0"]["ok_read_eq_meta"] = ok0b
    ok2, mx2, fr2 = v2_eval(VS.v["V2"]["by_year"])
    VS.v["V2"].update(ok=ok2, max_bad_frac=mx2, bad_frac_by_year=fr2)
    if not ok2:
        json.dump(VS.v, open(os.path.join(out, "validate.json"), "w"), indent=1, default=str)
        raise RuntimeError("V2 FAIL: ti le dong active xau %.5f > %.4f - DUNG" % (mx2, V2_MAX_BAD_FRAC))
    tiers = build_tiers(qv, act, life, nday)
    er_p1, sg_p1 = pass1_features(tiers, hc, nday)
    syms = sorted(tiers)
    mine = [s for s in syms if zlib.crc32(s.encode()) % sk == si]
    log.info("universe %d sym, shard %d/%d -> %d sym", len(syms), si, sk, len(mine))
    v6frames = {}
    fund = load_funding(fu, set(mine) | {mkt_sym}, v6frames)
    ok6, d6 = v6_eval(v6frames)
    VS.v["V6"] = dict(ok=ok6, by_year=d6)
    if not ok6:
        json.dump(VS.v, open(os.path.join(out, "validate.json"), "w"), indent=1, default=str)
        raise RuntimeError("V6 FAIL (don vi rate / interval_h funding) - DUNG: %s" % d6)
    mkt = None
    if mkt_sym in qv:
        arr = load_symbol(kl, mkt_sym, nday)
        mkt = market_context(arr, delist_index(mkt_sym, life, arr[5]), nday)
    rng = np.random.default_rng(SEED_V + si)
    v4, v5, v4_skipped = [], [], []
    v5_need = set(V5_SLOTS)
    v5_fb = {}                                                   # R2: du phong (mo hinh con lai) cho vi tri con thieu
    v5_fb_all = []                                               # R3-5: MOI don vi du phong da doi chieu
    for k_ in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days", "units_skip_px"):
        VS.v["V3"][k_] = 0
    VS.v["V3"]["n_sym_from_checkpoint"] = 0
    for n_i, s in enumerate(mine):
        base = os.path.join(out, "agg_sym", s)
        if (all(os.path.exists("%s.%s.parquet" % (base, t)) for t in TABLES) and os.path.exists(base + ".v3.json") and n_i > nv4
                and len(v4) >= nv4 and not v5_need):
            v3s = json.load(open(base + ".v3.json"))
            VS.v["V3"]["n_sym_from_checkpoint"] += 1
        else:
            arr = load_symbol(kl, s, nday)
            dl = delist_index(s, life, arr[5])
            ctx = dict(nday=nday, tier=tiers[s], fund=fund.get(s), dl=dl, mkt=mkt, mkt_sym=mkt_sym, CP=CP,
                       er_p1=er_p1[s], sig_p1=sg_p1[s])
            res = process_symbol(s, arr, ctx, collect_units=(n_i <= nv4 or bool(v5_need)))
            v3s = _v3_sym(res, arr, nday, s)
            if len(v4) < nv4:
                okp, lo4, hi4, why = v4_pick(arr[5])
                if okp:
                    v4.append(v4_check(s, arr, ctx, rng, tc_range=(lo4, hi4)))
                    log.info("V4 %s", v4[-1])
                else:
                    v4_skipped.append(dict(sym=s, reason=why))
            if res["units"] and v5_need:
                pk = v5_select(res, v5_need, rng)
                chk = v5_check(s, kl, fu, life, res, ctx, pk)
                for x, p_ in zip(chk, pk):
                    x["slot"], x["fallback"] = list(p_[0]), False
                v5 += chk
                v5_need -= {tuple(p_[0]) for p_ in pk}
                alt = {(ci, sd, _other(m)) for (ci, sd, m) in v5_need if (ci, sd, m) not in v5_fb}
                if alt:
                    pkf = v5_select(res, alt, rng)
                    for x, p_ in zip(v5_check(s, kl, fu, life, res, ctx, pkf), pkf):
                        ci, sd, m = p_[0]
                        v5_fb[(ci, sd, _other(m))] = x
                        v5_fb_all.append(x)
            save_tables(res, base)
            json.dump(v3s, open(base + ".v3.json", "w"))
            log.info("sym %s (%d/%d) dl=%d rows=%d %.0fs", s, n_i + 1, len(mine), dl, len(res["agg"]), time.time() - t_start)
        for k_ in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days", "units_skip_px"):
            VS.v["V3"][k_] += int(v3s[k_])
        for kc, vc in v3s["skip_px_by_cell"].items():
            VS.v["V3"]["skip_px_by_cell"][kc] = VS.v["V3"]["skip_px_by_cell"].get(kc, 0) + int(vc)
        VS.v["V3"]["sym_month_missing"] += v3s["sym_month_missing"]
    reduce_tables(os.path.join(out, "agg_sym"), os.path.join(out, "reduced"))
    if os.environ.get("GRIDV3_KEEP_SYM", "0") != "1":
        for p in glob.glob(os.path.join(out, "agg_sym", "*.parquet")) + glob.glob(os.path.join(out, "agg_sym", "*.v3.json")):
            os.remove(p)
    VS.v["V4"] = dict(checks=v4, v4_skipped=v4_skipped, n_required=nv4,
                      ok=nv4 > 0 and len(v4) == nv4 and all(x["ok"] for x in v4))
    v5_all, v5_fbk, v5_unc = v5_finalize(v5, v5_need, v5_fb)
    used = {id(v5_fb[s_]) for s_ in v5_need if s_ in v5_fb}
    VS.v["V5"] = v5_eval(v5_all, v5_fbk, v5_unc, [x for x in v5_fb_all if id(x) not in used])
    v = VS.v
    v["V1"]["ok"] = (not v["V1"]["bad"]) and v["V1"]["ts_max"] is not None and v["V1"]["ts_max"] < SEAL
    v["V3"]["ok"] = v["V3"]["feat_mismatch_days"] == 0
    v["all_pass"] = bool(v["V0"]["ok_registry"] and v["V0"]["ok_read_eq_meta"] and v["V1"]["ok"] and v["V2"]["ok"]
                         and v["V3"]["ok"] and v["V4"]["ok"] and v["V5"]["ok"] and v["V6"]["ok"])
    man = dict(shard="%d/%d" % (si, sk), n_sym=len(mine), cond=CP, mkt_sym=mkt_sym, prereg_constants=prereg_constants,
               test_overrides=tov, alpha_fwer=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS, s3_const=S3_CONST,
               inputs={os.path.basename(p): sha256_file(p) for p in [lpath] + list(fu.values())},
               code={f: sha256_file(os.path.join(HERE, f)) for f in SHA_FILES},
               seconds=round(time.time() - t_start, 1))
    json.dump(v, open(os.path.join(out, "validate.json"), "w"), indent=1, default=str)
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1, default=str)
    log.info("XONG all_pass=%s %.0fs", v["all_pass"], time.time() - t_start)
    return v, man


# ------------------------------------------------------------------ merge + thong ke + luat
def load_reduced(dirs):
    out = {}
    for t in TABLES:
        parts = [pd.read_parquet(os.path.join(d, "reduced", "%s.parquet" % t)) for d in dirs
                 if os.path.exists(os.path.join(d, "reduced", "%s.parquet" % t))]
        out[t] = _reduce(pd.concat(parts, ignore_index=True), t) if parts else pd.DataFrame()
    return out


def day_matrix(A, lo, hi, col, J):
    M = np.zeros((hi - lo, J))
    sub = A[(A.day >= lo) & (A.day < hi)] if len(A) else A
    if len(sub):
        np.add.at(M, (sub.day.to_numpy().astype(int) - lo, sub.cell.to_numpy().astype(int)), sub[col].to_numpy())
    return M


def load_expected_sha(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        h, f = line.split()[:2]
        out[os.path.basename(f.lstrip("*"))] = h.lower()
    miss = [f for f in SHA_FILES if f not in out]
    if miss:
        raise RuntimeError("EXPECTED_SHA thieu: %s" % miss)
    return out


def check_shards(shard_dirs, expected_sha):
    """Du DUNG 5 shard 0..4/5, khong trung (thu muc / chi so), prereg_constants, V0-V6 all_pass, hang so, s3_const == S3_CONST,
    cond == COND_PREREG, mkt_sym == BTCUSDT, sha code == expected_sha, manifest.inputs GIONG HET 5 shard (H2)."""
    errs, seen_dir, seen_idx, inputs, covered = [], set(), set(), [], set()
    if len(shard_dirs) != N_SHARDS:
        errs.append("so shard %d != %d" % (len(shard_dirs), N_SHARDS))
    for d in shard_dirs:
        rd = os.path.realpath(d)
        if rd in seen_dir:
            errs.append("thu muc trung: %s" % d)
        seen_dir.add(rd)
        mf, vf = os.path.join(d, "manifest.json"), os.path.join(d, "validate.json")
        if not (os.path.exists(mf) and os.path.exists(vf)):
            errs.append("thieu manifest/validate: %s" % d)
            continue
        man, val = json.load(open(mf)), json.load(open(vf))
        sh = str(man.get("shard", ""))
        m = re.fullmatch(r"(\d+)/(\d+)", sh)
        if not m or int(m.group(2)) != N_SHARDS or not 0 <= int(m.group(1)) < N_SHARDS:
            errs.append("shard la: %s (%s)" % (sh, d))
        elif int(m.group(1)) in seen_idx:
            errs.append("chi so shard trung: %s (%s)" % (sh, d))
        else:
            seen_idx.add(int(m.group(1)))
        if not (man.get("prereg_constants") is True and val.get("all_pass") is True and man.get("alpha_fwer") == ALPHA_FWER
                and man.get("alpha_upper") == ALPHA_UPPER and man.get("min_units") == MIN_UNITS):
            errs.append("prereg_constants / all_pass / hang so sai: %s" % d)
        if json.loads(json.dumps(man.get("s3_const"))) != json.loads(json.dumps(S3_CONST)):
            errs.append("s3_const khac prereg: %s" % d)
        if man.get("cond") != COND_PREREG:
            errs.append("cond != COND_PREREG: %s" % d)
        if man.get("mkt_sym") != MARKET_SYM:
            errs.append("mkt_sym != %s: %s" % (MARKET_SYM, d))
        code = man.get("code") or {}
        for f in SHA_FILES:
            if code.get(f) != expected_sha.get(f):
                errs.append("sha %s lech: %s" % (f, d))
        inputs.append(json.dumps(man.get("inputs"), sort_keys=True))
        for k in ((val.get("V5") or {}).get("covered_ctside") or []):
            covered.add((int(k[0]), int(k[1])))
    miss_cs = [(ci, sd) for ci in range(len(CT_ALL)) for sd in (1, -1) if (ci, sd) not in covered]
    if miss_cs:
        errs.append("V5: (c,T,ben) khong duoc shard nao phu: %s" % miss_cs)
    if len(set(inputs)) > 1:
        errs.append("manifest.inputs khac nhau giua cac shard (H2)")
    if seen_idx != set(range(N_SHARDS)):
        errs.append("thieu shard: %s" % sorted(set(range(N_SHARDS)) - seen_idx))
    if errs:
        raise RuntimeError("merge tu choi: " + "; ".join(errs))


def pass_cell(A, B, c, floor=FLOOR_BPS):
    """PASS 1 o (S3-6 + R2): (a)-(e), (e') khoi phan hoach, (e'') cua so truot 20 ngay. Tra (pass, dict dieu kien)."""
    fin = lambda v: v is not None and np.isfinite(v)        # noqa: E731
    cond = dict(
        not_insufficient=(not B["insufficient"][c]) and (not A["insufficient"][c]),
        a_rw_B=bool(B["rw_reject"][c]),
        b_half_A=fin(A["M"][c]) and A["M"][c] > floor and fin(A["p_marg"][c]) and A["p_marg"][c] <= P_HALF_A,
        c_Madj_B=fin(B["M_adj_C4"][c]) and B["M_adj_C4"][c] > 0,
        d_top3_B=fin(B["M_drop_top3"][c]) and B["M_drop_top3"][c] > floor,
        e_events_AB=fin(B["M_drop_events"][c]) and B["M_drop_events"][c] > floor and fin(A["M_drop_events"][c])
        and A["M_drop_events"][c] > floor,
        e2_topblock_AB=fin(B["M_drop_top_block"][c]) and B["M_drop_top_block"][c] > floor and fin(A["M_drop_top_block"][c])
        and A["M_drop_top_block"][c] > floor,
        e3_topwindow_AB=fin(B["M_drop_top_window"][c]) and B["M_drop_top_window"][c] > floor and fin(A["M_drop_top_window"][c])
        and A["M_drop_top_window"][c] > floor)
    cond = {k: bool(v) for k, v in cond.items()}
    return all(cond.values()), cond


def decide_rule(models, floor=FLOOR_BPS):
    """S3-7: W-D > W-C > W-A > W-B. models[m]['PASS'] (12 bool), models['OPT']['B'] (upper_sim95, insufficient)."""
    opt, pes = models["OPT"]["PASS"], models["PESS"]["PASS"]
    up = np.array(models["OPT"]["B"]["upper_sim95"], dtype=float)
    ins = np.array(models["OPT"]["B"]["insufficient"], dtype=bool)
    wa = bool((not ins.any()) and np.all(np.isfinite(up)) and np.all(up < floor))
    if any(pes):
        return "W-D", wa
    if any(opt):
        return "W-C", wa
    return ("W-A" if wa else "W-B"), wa


def _quant_hist(HS, c, model, hv, qs):
    hh = HS[(HS.cell == c) & (HS.model == model) & (HS.half == hv)].sort_values("bin") if len(HS) else HS
    if len(hh) == 0:
        return [np.nan] * len(qs)
    cc = np.cumsum(hh["count"].to_numpy()) / hh["count"].sum()
    b = hh["bin"].to_numpy()
    return [float((b[min(np.searchsorted(cc, q), b.size - 1)] + 0.5) * HIST_W) for q in qs]


def merge(outdir, shard_dirs, floor=FLOOR_BPS, nboot=stats.NBOOT, allow_test=False, expected_sha=None):
    """Gop shard + thong ke + luat S3. Chay that: expected_sha (bat buoc) + check_shards. allow_test CHI cho test noi bo (khong co
    tu CLI): bo qua check_shards, cho nboot != 2000; result.json danh dau TEST_ONLY va rule = 'TEST_ONLY:<luat>'."""
    check_env()
    if not allow_test:
        if floor != FLOOR_BPS or nboot != stats.NBOOT:
            raise RuntimeError("merge: san / so bootstrap khac prereg")
        if expected_sha is None:
            raise RuntimeError("merge: can --expected-sha")
        exp = load_expected_sha(expected_sha) if isinstance(expected_sha, str) else expected_sha
        bad = [f for f in SHA_FILES if sha256_file(os.path.join(HERE, f)) != exp.get(f)]   # R3-3 (A1 F3): code dang chay merge
        if bad:
            raise RuntimeError("merge: sha256 file code cua CHINH merge khac --expected-sha: %s" % bad)
        check_shards(shard_dirs, exp)
    shard_info, skip_px = [], {}
    for d in shard_dirs:
        mf, vf = os.path.join(d, "manifest.json"), os.path.join(d, "validate.json")
        man = json.load(open(mf)) if os.path.exists(mf) else {}
        val = json.load(open(vf)) if os.path.exists(vf) else {}
        shard_info.append(dict(dir=d, prereg_constants=bool(man.get("prereg_constants", False)),
                               all_pass=bool(val.get("all_pass", False)), inputs=man.get("inputs")))
        for kc, vc in ((val.get("V3") or {}).get("skip_px_by_cell") or {}).items():
            skip_px[int(kc)] = skip_px.get(int(kc), 0) + int(vc)
    os.makedirs(outdir, exist_ok=True)
    T_ = load_reduced(shard_dirs)
    A, SH, HS, UM = T_["agg"], T_["shalf"], T_["hist"], T_["umin"]
    nday = (SEAL - DATA_START) // DAY
    d0 = (STUDY_START - DATA_START) // DAY
    dB = (HALF_B - DATA_START) // DAY
    halves = {"A": (d0, dB), "B": (dB, nday)}
    cl = cells()
    J = len(cl)
    res = dict(TEST_ONLY=bool(allow_test), allow_test=bool(allow_test), floor=floor, alpha_fwer=ALPHA_FWER,
               alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS, nboot=nboot, p_half_A=P_HALF_A, s3_const=S3_CONST,
               method="studentized_block_bootstrap_RW_maxt", cells=[c["name"] for c in cl], shards=shard_info,
               skip_px_by_cell={cl[k]["name"]: v for k, v in sorted(skip_px.items())}, models={})
    ev_days = [((ms(a) - 3 * DAY - DATA_START) // DAY, (ms(b) + DAY - DATA_START) // DAY) for a, b in EVENTS]
    oct_days = [((ms(EVENT_OCT25[0]) - 3 * DAY - DATA_START) // DAY, (ms(EVENT_OCT25[1]) + DAY - DATA_START) // DAY)]

    def keep_mask(lo, hi, evs):
        keep = np.ones(hi - lo, bool)
        for (elo, ehi) in evs:
            a_, b_ = max(elo, lo) - lo, min(ehi, hi) - lo
            if b_ > a_:
                keep[a_:b_] = False
        return keep

    for model in ("OPT", "PESS"):
        Am = A[A.model == model] if len(A) else A
        R = {}
        for h, (lo, hi) in halves.items():
            S, N = day_matrix(Am, lo, hi, "net", J), day_matrix(Am, lo, hi, "fill", J)
            st = stats.cell_stats(S, N, floor, SEED_BOOT + (0 if h == "A" else 1) + (0 if model == "OPT" else 10), B=nboot,
                                  alpha=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS)
            ex = {c: day_matrix(Am, lo, hi, c, J).sum(0) for c in ("neth", "gross", "fee", "slip", "fund", "cap", "lim", "place",
                                                                     "excl", "excl_gap", "holdmin", "sx5")}
            Nt = np.maximum(N.sum(0), 1)
            st["M_neth"] = ex["neth"] / Nt
            st["gross_mean"] = ex["gross"] / Nt
            for c in ("fee", "slip", "fund", "cap"):
                st[c + "_mean"] = ex[c] / Nt
            st["M_adj_C4"] = st["M"] - st["cap_mean"]
            st["M_stress_slip_x5"] = (S.sum(0) - ex["sx5"]) / Nt
            st["n_place"], st["n_excl"] = ex["place"], ex["excl"]
            st["fill_rate"] = N.sum(0) / np.maximum(ex["place"] - ex["excl"], 1)
            st["p_lim_exit"] = ex["lim"] / Nt
            st["hold_mean_min"] = ex["holdmin"] / Nt
            st["excl_gap_rate"] = ex["excl_gap"] / np.maximum(ex["place"], 1)
            hv = 0 if h == "A" else 1
            top3 = []
            for c in range(J):
                sc = SH[(SH.model == model) & (SH.half == hv) & (SH.cell == c)] if len(SH) else SH
                if len(sc) == 0:
                    top3.append(np.nan)
                    continue
                gs = sc.groupby("sym")[["net", "fill"]].sum().sort_values("net", ascending=False)
                rest = gs.iloc[3:]
                top3.append(rest["net"].sum() / max(rest.fill.sum(), 1))
            st["M_drop_top3"] = np.array(top3)
            st["M_drop_events"] = stats3_extra.mean_excluding_days(S, N, keep_mask(lo, hi, ev_days))
            st["M_drop_oct2025"] = stats3_extra.mean_excluding_days(S, N, keep_mask(lo, hi, oct_days))
            tb = stats3_extra.drop_top_block(S, N)
            st["M_drop_top_block"] = tb["M_drop"]
            st["top_block_start"] = [str(pd.Timestamp(DATA_START + (lo + int(x)) * DAY, unit="ms").date()) for x in tb["top_lo"]]
            st["top_block_share_net"] = tb["top_share"]
            st["top_block_n"] = tb["top_N"]
            tw = stats3_extra.drop_top_window(S, N)                                   # R2 (MASTER P1): dieu kien (e'')
            st["M_drop_top_window"] = tw["M_drop"]
            st["top_window_start"] = [str(pd.Timestamp(DATA_START + (lo + int(x)) * DAY, unit="ms").date()) for x in tw["start"]]
            yrs = {}
            for y in range(2021, 2026):
                ylo = max(lo, (ms("%d-01-01" % y) - DATA_START) // DAY)
                yhi = min(hi, (ms("%d-01-01" % (y + 1)) - DATA_START) // DAY)
                if yhi > ylo:
                    yrs[y] = (S[ylo - lo:yhi - lo].sum(0) / np.maximum(N[ylo - lo:yhi - lo].sum(0), 1)).tolist()
            st["M_by_year"] = yrs
            n2 = day_matrix(Am, lo, hi, "net2", J).sum(0)
            n3 = day_matrix(Am, lo, hi, "net3", J).sum(0)
            mu = S.sum(0) / Nt
            var = n2 / Nt - mu ** 2
            with np.errstate(invalid="ignore", divide="ignore"):
                st["skew"] = (n3 / Nt - 3 * mu * n2 / Nt + 2 * mu ** 3) / var ** 1.5
                st["sd_unit"] = np.sqrt(var)
            qq = [_quant_hist(HS, c, model, hv, (0.01, 0.05, 0.50, 0.95)) for c in range(J)]
            for k_, nm in enumerate(("q01_unit", "q05_unit", "q50_unit", "q95_unit")):
                st[nm] = np.array([q[k_] for q in qq])
            um = []
            for c in range(J):
                u_ = UM[(UM.cell == c) & (UM.model == model) & (UM.half == hv)] if len(UM) else UM
                um.append(float(u_.net_min.min()) if len(u_) else np.nan)
            st["worst_unit_net"] = np.array(um)
            R[h] = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in st.items()}
        pas, conds = [], []
        for c in range(J):
            p_, cd = pass_cell(R["A"], R["B"], c, floor)
            pas.append(bool(p_))
            conds.append(dict(cell=cl[c]["name"], **cd))
        R["PASS"], R["PASS_conditions"] = pas, conds
        R["INSUFFICIENT_B"] = [cl[c]["name"] for c in range(J) if R["B"]["insufficient"][c]]
        R["INSUFFICIENT_A"] = [cl[c]["name"] for c in range(J) if R["A"]["insufficient"][c]]
        R["SELL_PASS_long_only_note"] = ["SELL (he thong hien long-only): %s" % cl[c]["name"] for c in range(J)
                                         if pas[c] and cl[c]["side"] == -1]
        res["models"][model] = R
    rule, wa = decide_rule(res["models"], floor)
    res["rule_core"] = rule
    res["rule"] = ("TEST_ONLY:" if allow_test else "") + rule
    res["W_A_condition_OPT_B"] = wa
    res["W_A_blocked_by_insufficient_OPT"] = res["models"]["OPT"]["INSUFFICIENT_B"]
    res["PASS_cells"] = {m: [cl[c]["name"] for c in range(J) if res["models"][m]["PASS"][c]] for m in ("OPT", "PESS")}
    res["SELL_PASS_note"] = {m: res["models"][m]["SELL_PASS_long_only_note"] for m in ("OPT", "PESS")}
    res["diff_M_OPT_minus_PESS"] = {h: (np.array(res["models"]["OPT"][h]["M"], float)
                                        - np.array(res["models"]["PESS"][h]["M"], float)).tolist() for h in ("A", "B")}
    json.dump(res, open(os.path.join(outdir, "result.json"), "w"), indent=1,
              default=lambda o: o.tolist() if hasattr(o, "tolist") else (o.item() if hasattr(o, "item") else str(o)))
    # ---- chan doan S3-8 (chi bao cao)
    D_ = T_["diag"]
    diag = []
    for r in (D_.itertuples() if len(D_) else []):
        f_ = max(r.fill, 1)
        diag.append(dict(cell=cl[int(r.cell)]["name"], model=r.model, half="AB"[int(r.half)], dim=r.dim, level=r.level,
                         n_place=int(r.place), n_fill=int(r.fill),
                         p_fill=(r.fill / (r.place - r.excl) if r.place - r.excl > 0 else None),
                         M=r.net / f_, M_neth=r.neth / f_, gross=r.gross / f_, p_lim=r.lim / f_, hold_min=r.holdmin / f_))
    MO = T_["mon"]
    monthly = []
    if len(MO):
        for (cc, model), g in MO.groupby(["cell", "model"]):
            for h, (a, b) in (("A", ("2021-07", "2023-12")), ("B", ("2024-01", "2025-12"))):
                gg = g[(g.month >= a) & (g.month <= b)]
                m_ = gg.net / gg.fill.clip(lower=1)
                monthly.append(dict(cell=cl[int(cc)]["name"], model=model, half=h, frac_month_pos=float((m_ > 0).mean()) if len(gg) else None,
                                    median_month_M=float(m_.median()) if len(gg) else None, n_month=int(len(gg))))
    json.dump(dict(diag=diag, monthly=monthly), open(os.path.join(outdir, "diag.json"), "w"), indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    return res, T_


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        # python3 runner3_kaggle.py merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 d1 d2 d3 d4
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
        a = sys.argv[2:]
        if len(a) < 3 or a[1] != "--expected-sha":
            raise SystemExit("dung: merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 .. d4")
        merge(a[0], a[3:], expected_sha=a[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "run":
        run()
    else:
        raise SystemExit("dung: runner3_kaggle.py run | merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 .. d4")
