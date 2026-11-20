"""runner_kaggle.py - khung chay Giai doan 1 v2 (PREREG_GRIDV2_S1_DRAFT3) tren lake vz-kline1m (row group = 1 symbol).
CHI da viet + test tren parquet GIA cung schema. KHONG push, KHONG chay tren du lieu that trong pha dev.

Che do:
  python runner_kaggle.py run    -> doc lake (GRIDV2_INPUT), mo phong shard (GRIDV2_SHARD="i/K"), ghi reduced/ + validate.json
  python runner_kaggle.py merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 d1 d2 d3 d4 -> gop + thong ke -> result.json, diag.json
Bien moi truong (CHI van hanh, khong doi thong ke): GRIDV2_INPUT (/kaggle/input), GRIDV2_OUT (/kaggle/working),
  GRIDV2_SHARD (0/1), GRIDV2_KEEP_SYM (1 = giu checkpoint tung symbol).
R3-1: KHONG co bien moi truong nao doi duoc alpha / dieu kien COND / symbol thi truong / registry / so symbol V4: neu dat
  (GRIDV2_ALPHA, GRIDV2_COND, GRIDV2_MARKET_SYM, GRIDV2_REGISTRY, GRIDV2_V4_SYMS) -> abort. Hang so = prereg (assert).
  Test noi bo dung tham so ham test_overrides (manifest ghi prereg_constants=False; merge tu choi shard do tru khi allow_test).
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
import klite  # noqa: E402
import kref   # noqa: E402
import stats  # noqa: E402

log = logging.getLogger("gridv2_s1")
MIN = 60000
DAY = 86400000
SEAL = 1767225600000                      # 2026-01-01 UTC: khong doc gi >= moc nay
DATA_START = 1619827200000                # 2021-05-01 (warm-up 2 thang)
STUDY_START = 1625097600000               # 2021-07-01
HALF_B = 1704067200000                    # 2024-01-01
CK_ALL = [(0.1, 2), (0.1, 8), (0.2, 2), (0.2, 8), (0.4, 2), (0.4, 8)]
S_CK = [(0.2, 2), (0.2, 8)]
D_CK = [(0.2, 2), (0.2, 8), (0.4, 8)]
S_SETS = ["ER_LOW", "IDEAL_N", "COND_A", "COND_B"]
D_SETS = [("TREND_BUY", 1), ("TREND_SELL", -1)]
FLOOR_BPS = 4.0
ALPHA_FWER = 0.04                         # R3-1: RW studentized, FWER danh nghia co dinh
ALPHA_UPPER = 0.05                        # R3-2: can tren dong thoi 95 % (L-A)
MIN_UNITS = 200                           # R3-3: < 200 don vi khop trong nua -> INSUFFICIENT
COND_PREREG = {"A": dict(z=2.5, vmult=3.0), "B": dict(ratio=1.5)}
MARKET_SYM = "BTCUSDT"
V4_SYMS = 2
N_SHARDS = 5                              # R4-3: merge doi DUNG 5 shard 0..4/5
SHA_FILES = ("klite.py", "kref.py", "stats.py", "runner_kaggle.py")   # R4-3: sha kiem trong manifest == EXPECTED_SHA.txt
V2_MAX_BAD_FRAC = 0.001                   # R3-6: dong active xau (NaN / <= 0) > 0,1 % cua mot nam -> abort
V6_RATE_RANGE = (1e-5, 1e-3)              # R3-10: median |rate| moi nam
V6_INTERVALS = (1, 2, 4, 8)
SHAT_FFILL_DAYS = 7                       # R3-5: s_hat thieu ngay D-1 -> ngay hop le gan nhat trong 7 ngay truoc
ALLOWED_SLUGS = ("vz-kline1m-2021", "vz-kline1m-2022", "vz-kline1m-2023", "vz-kline1m-2024", "vz-kline1m-2025",
                 "gridp-t1-funding", "gridp-lifecycle")
FORBIDDEN_ENV = ("GRIDV2_ALPHA", "GRIDV2_COND", "GRIDV2_MARKET_SYM", "GRIDV2_REGISTRY", "GRIDV2_V4_SYMS")
assert ALPHA_FWER == 0.04 and ALPHA_UPPER == 0.05 and MIN_UNITS == 200, "hang so thong ke khac prereg"
assert stats.ALPHA_FWER == ALPHA_FWER and stats.ALPHA_UPPER == ALPHA_UPPER and stats.MIN_UNITS == MIN_UNITS
assert stats.BLOCK == 20 and stats.NBOOT == 2000
F3_BUY_MAX = 0.0005
F3_SELL_MIN = -0.0001
AGE_MIN = 90
XTOL = 1e-9
REGISTRY_REAL = {2021: 60001411, 2022: 75973640, 2023: 104401093, 2024: 155015111, 2025: 256801320}
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "USDEUSDT"}
INDEXES = {"BTCDOMUSDT", "DEFIUSDT", "FOOTBALLUSDT", "BLUEBIRDUSDT"}
EVENTS = [("2022-05-09", "2022-05-13"), ("2022-11-08", "2022-11-10"), ("2025-10-10", "2025-10-13")]
SEED_BOOT = 2026112040
SEED_V = 2026112041
HIST_LO, HIST_HI = -3000, 3000
SUM_COLS = ["place", "excl", "excl_gap", "fill", "net", "neth", "gross", "grossh", "fee", "slip", "fund", "cap",
            "net2", "net3", "neth2", "neth3", "lim", "holdmin", "hb_sum", "hb_n", "hcost"]
TABLES = ("agg", "shalf", "hist", "diag", "mon", "tdiag")
TKEYS = {"agg": ["cell", "model", "day"], "shalf": ["sym", "cell", "model", "half"], "hist": ["cell", "model", "half", "bin"],
         "diag": ["ck", "model", "half", "dim", "level"], "mon": ["ck", "model", "month"],
         "tdiag": ["cell", "model", "half", "tier"]}


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cells():
    """32 o: 18 G-N (c,k,tier) + 8 G-S ((c,k) x 4 tap) + 6 G-D ((c,k) x 2 tap). stat = cot thong ke chinh."""
    out = []
    for c, k in CK_ALL:
        for tr in (1, 2, 3):
            out.append(dict(id=len(out), grp="N", c=c, k=k, tier=tr, set=None, side=0, stat="net",
                            name="N_c%.1f_k%d_T%d" % (c, k, tr)))
    for c, k in S_CK:
        for st in S_SETS:
            out.append(dict(id=len(out), grp="S", c=c, k=k, tier=0, set=st, side=0, stat="net",
                            name="S_%s_c%.1f_k%d" % (st, c, k)))
    for c, k in D_CK:
        for st, sd in D_SETS:
            out.append(dict(id=len(out), grp="D", c=c, k=k, tier=0, set=st, side=sd, stat="neth",
                            name="D_%s_c%.1f_k%d" % (st, c, k)))
    assert len(out) == 32
    return out


def cond_params(override=None):
    """Dieu kien COND_A / COND_B = prereg. override CHI dung trong test noi bo (khong co duong vao tu CLI / env)."""
    dflt = json.loads(json.dumps(COND_PREREG))
    for k, v in (override or {}).items():
        dflt[k].update(v)
    return dflt


def check_env():
    """R3-1: cam moi bien moi truong ghi de tham so thong ke / validation."""
    bad = [k for k in FORBIDDEN_ENV if k in os.environ]
    if bad:
        raise RuntimeError("bien moi truong bi cam (R3-1, khong ghi de tham so prereg): %s" % bad)


def shat_exante(spread_daily):
    """R3-5: s_hat cho ngay D = Abdi-Ranaldo ngay hop le gan nhat trong [D-7, D-1]; khong co -> NaN (thay bang 2 x san tier
    o shat_fill). Khong bao gio dung gia tri cu hon 7 ngay."""
    return pd.Series(np.asarray(spread_daily, np.float64)).ffill(limit=SHAT_FFILL_DAYS - 1).shift(1).to_numpy()


def shat_fill(shat, tierv):
    """s_hat NaN -> 2 x san truot tier (T1 4 / T2 10 / T3 20 bps); khong bao gio 0 do thieu du lieu."""
    fl = np.array([klite.SLIP_TIER_FLOOR.get(int(t), klite.SLIP_TIER_FLOOR[3]) for t in np.asarray(tierv).ravel()])
    sh = np.asarray(shat, np.float64)
    return np.where(np.isfinite(sh), sh, 2.0 * fl)


def v2_eval(by_year):
    """R3-6: by_year {nam: [so dong active xau, so dong active]} -> (ok, ti le max). Dong xau da la phut lo (khong khop)."""
    fr = {int(y): (b / a if a > 0 else 0.0) for y, (b, a) in by_year.items()}
    mx = max(fr.values()) if fr else 0.0
    return bool(mx <= V2_MAX_BAD_FRAC), mx, fr


def v6_eval(frames):
    """R3-10: frames {nam: DataFrame(rate, interval_h[, inferred])}: median |rate| moi nam trong [1e-5, 1e-3] va interval_h
    thuoc {1,2,4,8} (cot co san: moi dong; cot suy tu khoang cach moc: >= 99 % dong)."""
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


# ------------------------------------------------------------------ kiem ke file
def _slug_of(rel):
    parts = rel.split(os.sep)
    hit = [p for p in parts[:-1] if p in ALLOWED_SLUGS]
    return hit[0] if len(hit) == 1 else None


def find_inputs(inp):
    """R3-7: allowlist dataset. Moi file duoi thu muc input phai nam trong DUNG 1 slug cho phep; du 7 slug; ten file chua
    '2026' -> abort; trong slug chi chap nhan dung ten parquet mong doi (kline1m-YYYY-MM nam = slug, funding-YYYY,
    lifecycle.parquet duy nhat). Khong glob '**' lay file dau tien."""
    kl, fu, lp, seen = {}, {}, [], set()
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
                      V3=dict(long_gaps=0, units_excl_gap=0, units_excl_noend=0, sym_month_missing=[], feat_mismatch_days=0),
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


# ------------------------------------------------------------------ pass 1: qv ngay, close gio (moi symbol), V0-V2
def pass1(kl, VS, nday):
    qv, act, hc, rows = {}, {}, {}, {}
    for (y, mo), p in sorted(kl.items()):
        if ms("%04d-%02d-01" % (y, mo)) < DATA_START - 31 * DAY:
            continue
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
            by[0] += int((a & ~good).sum())          # dong active xau -> phut lo (khong khop), dem (R3-6)
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


def cross_section(tiers, hc, nday):
    """Nguong cat ngang theo ngay tren universe hop le (tier > 0): ER30 p33,33; sigma p10, p90."""
    er, sg, el = {}, {}, {}
    for s in tiers:
        dc = daily_close_from_hourly(hc[s], nday)
        er[s] = klite.er30(hc[s], nday)
        sg[s] = klite.sigma_exante(dc)
        el[s] = tiers[s] > 0
    thr = dict(er_p33=klite.xs_percentile(er, el, 100.0 / 3.0), sig_p10=klite.xs_percentile(sg, el, 10.0),
               sig_p90=klite.xs_percentile(sg, el, 90.0))
    return thr, er, sg


# ------------------------------------------------------------------ pass 2: 1 symbol
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
        if v6frames is not None:                     # V6 tren TOAN file (moi symbol), khong chi shard
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
    """Boi canh symbol thi truong (BTC): luoi phut, close ngay, UP/DOWN, ti le RV24/sigma theo gio (COND_B)."""
    G = klite.prepare_grid(*arrays[:4], arrays[5], dl)
    hc = klite.hourly_close(G, nday)
    dc = daily_close_from_hourly(hc, nday)
    sig = klite.sigma_exante(dc)
    up, dn = klite.up_down(dc)
    hcs = np.r_[np.nan, hc[:-1]]                # hcs[h] = close cuoi gio h-1 (truoc dau gio h)
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
    return dict(C=G["C"], lv=G["lv"], dc=dc, up=up, dn=dn, ratio=ratio)


def process_symbol(s, arrays, ctx, collect_units=False):
    """Mo phong 32 o cho 1 symbol. ctx: nday, tier, qvd, fund (ts, rate, ih) | None, dl, first_ms, mkt (dict) | None,
    mkt_sym, thr (er_p33, sig_p10, sig_p90), CP, er_p1, sig_p1 (pass1, doi chieu; None = bo qua)."""
    nday = ctx["nday"]
    O, H, L, C, QV, valid = arrays
    dl = ctx["dl"]
    G = klite.prepare_grid(O, H, L, C, valid, dl)
    feat = klite.daily_features(G, nday)
    sig = klite.sigma_exante(feat["close"])
    hc = klite.hourly_close(G, nday)
    er = klite.er30(hc, nday)
    mism = 0
    if ctx.get("sig_p1") is not None:
        for a1, a2 in ((ctx["sig_p1"], sig), (ctx["er_p1"], er)):
            mism += int(np.sum(~((np.isnan(a1) & np.isnan(a2)) | (np.abs(np.nan_to_num(a1) - np.nan_to_num(a2)) < 1e-12))))
    do, dh, dlo, dcl = klite.daily_ohlc(G, nday)
    adx = klite.adx14(do, dh, dlo, dcl)
    up, dn = klite.up_down(feat["close"])
    mkt = ctx["mkt"]
    beta = klite.beta_btc(feat["close"], mkt["dc"]) if mkt is not None else np.ones(nday)
    fu = ctx.get("fund")
    f3 = klite.f3_funding(fu[0], fu[1], fu[2], nday, DATA_START) if fu is not None else np.full(nday, np.nan)
    age = (np.floor((DATA_START + np.arange(nday) * DAY - ctx["first_ms"]) / DAY) if ctx["first_ms"] is not None
           else np.zeros(nday))
    thr = ctx["thr"]
    tick_c = pd.Series(feat["tick"]).ffill().shift(1).to_numpy()
    spr_c = shat_exante(feat["spread"])
    qv30 = np.r_[0.0, np.cumsum(ctx["qvd"])]
    cqv = np.r_[0.0, np.cumsum(QV)]
    n = G["n"]
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
    j61 = t0_all - 61
    ok61 = (j61 >= 0) & G["valid"][np.clip(j61, 0, None)]
    with np.errstate(all="ignore"):
        r60 = np.where(base_ok & ok61, np.log(G["C"][t0_all - 1] / G["C"][np.clip(j61, 0, None)]), 0.0)
    s1h = sig[D_all] / np.sqrt(24.0)
    q60 = cqv[t0_all] - cqv[np.clip(t0_all - 60, 0, None)]
    qref = (qv30[D_all] - qv30[np.clip(D_all - 30, 0, None)]) / 30.0 / 24.0
    condA = base_ok & ok61 & (np.abs(r60) >= CP["A"]["z"] * s1h) & (q60 >= CP["A"]["vmult"] * qref) & (qref > 0)
    if mkt is not None:
        hh = D_all * 24 + h_all
        condB = base_ok & np.isfinite(mkt["ratio"][hh]) & (mkt["ratio"][hh] >= CP["B"]["ratio"])
        upB, dnB = mkt["up"][D_all], mkt["dn"][D_all]
    else:
        condB = np.zeros_like(base_ok)
        upB = dnB = np.zeros_like(base_ok)
    with np.errstate(invalid="ignore"):          # so sanh nguong co dung sai tuong doi 1e-9 (chong nhieu float khi hoa)
        p33, p10, p90 = thr["er_p33"][D_all], thr["sig_p10"][D_all], thr["sig_p90"][D_all]
        erlow = np.isfinite(er[D_all]) & np.isfinite(p33) & (er[D_all] <= p33 + XTOL * np.abs(p33))
        sigmid = (sig[D_all] >= p10 - XTOL * np.abs(p10)) & (sig[D_all] <= p90 + XTOL * np.abs(p90))
        siglo = sig[D_all] <= p10 + XTOL * np.abs(p10)
        sighi = sig[D_all] >= p90 - XTOL * np.abs(p90)
    age_all, f3_all, up_all, dn_all, adx_all = age[D_all], f3[D_all], up[D_all], dn[D_all], adx[D_all]
    is_mkt = s == ctx["mkt_sym"]
    CL = cells()
    ag_rows, sh_rows, hist, diag, mon, units, tdg = [], [], {}, {}, {}, {}, {}
    half_d = np.where(DATA_START + np.arange(nday) * DAY >= HALF_B, 1, 0)
    month_d = pd.to_datetime(DATA_START + np.arange(nday) * DAY, unit="ms").strftime("%Y-%m").to_numpy()
    for ci, (c, k) in enumerate(CK_ALL):
        T = klite.unit_T(c, k)
        d = c * sig[D_all]
        tick = tick_c[D_all]
        with np.errstate(invalid="ignore"):
            sel = base_ok & (d * m0_all >= klite.MIN_D_TICKS * tick) & (t0_all + 2 * T + klite.LONG_GAP_MIN + 1 <= n)
        ii = np.nonzero(sel)[0]
        if ii.size == 0:
            continue
        pi = np.r_[ii, ii]
        side = np.r_[np.ones(ii.size, np.int8), -np.ones(ii.size, np.int8)]
        sidef = side.astype(float)
        tierv = tier_all[pi]
        shat = shat_fill(spr_c[D_all[pi]], tierv)
        slip = np.maximum(np.array([klite.SLIP_TIER_FLOOR[int(t)] for t in tierv]), shat / 2.0)
        Du = D_all[pi]
        fpass = np.where(side == 1, ~(f3_all[pi] > F3_BUY_MAX), ~(f3_all[pi] < F3_SELL_MIN))
        memb = [(ci * 3 + tr_ - 1, tierv == tr_) for tr_ in (1, 2, 3)]
        if (c, k) in S_CK:
            si = S_CK.index((c, k))
            ideal = erlow[pi] & sigmid[pi] & (age_all[pi] >= AGE_MIN) & (tierv <= 2) & fpass
            for j, m_ in enumerate((erlow[pi], ideal, condA[pi], condB[pi])):
                memb.append((18 + si * 4 + j, m_))
        if (c, k) in D_CK and not is_mkt:
            di = D_CK.index((c, k))
            memb.append((26 + di * 2, (side == 1) & up_all[pi] & upB[pi] & (age_all[pi] >= AGE_MIN) & fpass))
            memb.append((26 + di * 2 + 1, (side == -1) & dn_all[pi] & dnB[pi] & (age_all[pi] >= AGE_MIN) & fpass))
        tend = t0_all[pi] + T - 1
        lvt = G["lv"][tend]
        with np.errstate(all="ignore"):
            hb_unit = sidef * np.log(np.where(lvt >= 0, G["C"][np.clip(lvt, 0, None)], np.nan) / m0_all[pi]) / T * 1e4
        for model in ctx.get("models", ("OPT", "PESS")):
            R = klite.run_units(G, t0_all[pi], d[pi], T, T, tick[pi], slip, model, side, fs, fr)
            ok = R["filled"] & (R["excl"] == 0)
            okp = R["excl"] == 0
            hedge = np.zeros(pi.size)
            if mkt is not None:
                fb = mkt["lv"][np.clip(R["f"], 0, None)]
                xb = mkt["lv"][np.clip(R["x"], 0, None)]
                with np.errstate(all="ignore"):
                    Bf = np.where(fb >= 0, mkt["C"][np.clip(fb, 0, None)], np.nan)
                    Bx = np.where(xb >= 0, mkt["C"][np.clip(xb, 0, None)], np.nan)
                    hedge = np.nan_to_num(np.where(ok, sidef * beta[Du] * (Bx - Bf) / Bf * 1e4, 0.0))
            net = np.where(ok, R["net"], 0.0)
            neth = np.where(ok, R["net"] - hedge, 0.0)
            gross = np.where(ok, R["gross"], 0.0)
            colz = dict(place=np.ones(pi.size), excl=(R["excl"] != 0).astype(float), excl_gap=(R["excl"] == 1).astype(float),
                        fill=ok.astype(float), net=net, neth=neth, gross=gross, grossh=gross - hedge,
                        fee=np.where(ok, R["fee"], 0.0), slip=np.where(ok, R["slip"], 0.0), fund=np.where(ok, R["fund"], 0.0),
                        cap=np.where(ok, shat / 2.0 * R["n_maker"] * 1e4, 0.0), net2=net ** 2, net3=net ** 3,
                        neth2=neth ** 2, neth3=neth ** 3, lim=(ok & (R["kind"] == klite.EX_LIMIT)).astype(float),
                        holdmin=np.where(ok, R["x"] - R["f"], 0).astype(float),
                        hb_sum=np.where(okp & np.isfinite(hb_unit), hb_unit, 0.0),
                        hb_n=(okp & np.isfinite(hb_unit)).astype(float),
                        hcost=np.where(ok, 2.0 * 5.0 * beta[Du], 0.0))
            for cid, m_ in memb:
                if not m_.any():
                    continue
                sm = {kk: np.bincount(Du[m_], weights=v[m_], minlength=nday) for kk, v in colz.items()}
                dd = np.nonzero(sm["place"])[0]
                df = pd.DataFrame({kk: v[dd] for kk, v in sm.items()})
                df["day"], df["cell"], df["model"] = dd, cid, model
                ag_rows.append(df)
                stat = neth if CL[cid]["stat"] == "neth" else net
                if cid >= 18:                              # chan doan (11): tach tier cho o gop tier (G-S, G-D)
                    for tr_ in (1, 2, 3):
                        for hv in (0, 1):
                            mt = m_ & (tierv == tr_) & (half_d[Du] == hv)
                            if mt.any():
                                a_ = tdg.setdefault((cid, model, hv, tr_), np.zeros(5))
                                a_ += [mt.sum(), (mt & ok).sum(), net[mt].sum(), neth[mt].sum(), (R["excl"][mt] == 1).sum()]
                for hv in (0, 1):
                    mm = m_ & ok & (half_d[Du] == hv)
                    if mm.any():
                        sh_rows.append(dict(sym=s, cell=cid, model=model, half=hv, net=net[mm].sum(), neth=neth[mm].sum(),
                                            fill=float(mm.sum())))
                        nb = np.clip(np.round(stat[mm]).astype(np.int64), HIST_LO - 1, HIST_HI + 1)
                        u_, cnt = np.unique(nb, return_counts=True)
                        hd = hist.setdefault((cid, model, hv), {})
                        for b_, c_ in zip(u_.tolist(), cnt.tolist()):
                            hd[b_] = hd.get(b_, 0) + c_
            # ---- chan doan M5 (G-N gop tier cua (c,k))
            hv_u = half_d[Du]
            dims = {
                "side": np.where(side == 1, "BUY", "SELL"),
                "age": np.where(age_all[pi] >= AGE_MIN, "ge90", "lt90"),
                "fundfilt": np.where(fpass, "pass", "filtered"),
                "adx": np.where(~np.isfinite(adx_all[pi]), "na",
                                np.where(adx_all[pi] < 20, "lt20", np.where(adx_all[pi] <= 25, "20_25", "gt25"))),
                "sigxs": np.where(siglo[pi], "le_p10", np.where(sighi[pi], "ge_p90", "mid")),
                "hour": np.char.add("h", h_all[pi].astype(str)),
                "countertrend": np.where(((side == 1) & dn_all[pi] & dnB[pi]) | ((side == -1) & up_all[pi] & upB[pi]),
                                         "ct", "other"),
            }
            for dim, lab in dims.items():
                for lv in np.unique(lab[ok]):
                    for hv in (0, 1):
                        mm = ok & (lab == lv) & (hv_u == hv)
                        if mm.any():
                            a_ = diag.setdefault((ci, model, hv, dim, str(lv)), np.zeros(4))
                            a_ += [mm.sum(), net[mm].sum(), neth[mm].sum(), gross[mm].sum()]
            mo_u = month_d[Du]
            for mo_ in np.unique(mo_u[ok]):
                mm = ok & (mo_u == mo_)
                a_ = mon.setdefault((ci, model, str(mo_)), np.zeros(3))
                a_ += [mm.sum(), net[mm].sum(), neth[mm].sum()]
            if collect_units:
                units[(ci, model)] = dict(R=R, t0=t0_all[pi], side=side, d=d[pi], T=T, tick=tick[pi], slip=slip, D=Du,
                                          memb={cid: m_ for cid, m_ in memb}, neth=np.where(ok, R["net"] - hedge, np.nan),
                                          beta=beta[Du], ok=ok)
    agg = pd.concat(ag_rows, ignore_index=True) if ag_rows else pd.DataFrame(columns=SUM_COLS + ["day", "cell", "model"])
    agg["sym"] = s
    shalf = pd.DataFrame(sh_rows, columns=["sym", "cell", "model", "half", "net", "neth", "fill"])
    hrows = [dict(cell=k[0], model=k[1], half=k[2], bin=b, count=c) for k, hd in hist.items() for b, c in hd.items()]
    drows = [dict(ck=k[0], model=k[1], half=k[2], dim=k[3], level=k[4], fill=v[0], net=v[1], neth=v[2], gross=v[3])
             for k, v in diag.items()]
    mrows = [dict(ck=k[0], model=k[1], month=k[2], fill=v[0], net=v[1], neth=v[2]) for k, v in mon.items()]
    trows = [dict(cell=k[0], model=k[1], half=k[2], tier=k[3], place=v[0], fill=v[1], net=v[2], neth=v[3], excl_gap=v[4])
             for k, v in tdg.items()]
    return dict(agg=agg, shalf=shalf, hist=pd.DataFrame(hrows, columns=TKEYS["hist"] + ["count"]),
                diag=pd.DataFrame(drows, columns=TKEYS["diag"] + ["fill", "net", "neth", "gross"]),
                mon=pd.DataFrame(mrows, columns=TKEYS["mon"] + ["fill", "net", "neth"]),
                tdiag=pd.DataFrame(trows, columns=TKEYS["tdiag"] + ["place", "fill", "net", "neth", "excl_gap"]),
                units=units, aux=dict(G=G, sig=sig, er=er, beta=beta, f3=f3, up=up, dn=dn, adx=adx, age=age, tick=tick_c,
                                      feat_mismatch=mism, condA=condA, condB=condB, t0_all=t0_all, base_ok=base_ok))


# ------------------------------------------------------------------ V4: khong nhin tuong lai
def v4_check(s, arrays, ctx, rng):
    nday = ctx["nday"]
    d0 = (STUDY_START - DATA_START) // DAY
    tc_day = int(rng.integers(d0 + 60, nday - 30))
    tc = tc_day * 1440 + int(rng.integers(0, 1440))
    a1 = process_symbol(s, arrays, ctx, collect_units=True)
    O, H, L, C, QV, valid = [x.copy() for x in arrays]
    nn = O.size - tc
    junk = np.exp(rng.normal(0, 3, nn))
    O[tc:], C[tc:] = junk, junk[::-1]
    H[tc:], L[tc:] = np.maximum(O[tc:], C[tc:]) * 1.5, np.minimum(O[tc:], C[tc:]) * 0.5
    QV[tc:] = rng.random(nn) * 1e12
    valid[tc:] = rng.random(nn) < 0.5
    c2 = dict(ctx)
    c2["sig_p1"] = None
    c2["qvd"] = ctx["qvd"].copy()
    c2["qvd"][tc_day:] = rng.random(nday - tc_day) * 1e12
    c2["tier"] = ctx["tier"].copy()
    c2["tier"][tc_day + 1:] = rng.integers(0, 4, nday - tc_day - 1)
    c2["thr"] = {k: v.copy() for k, v in ctx["thr"].items()}
    for k in c2["thr"]:
        c2["thr"][k][tc_day + 1:] = rng.random(nday - tc_day - 1)
    if ctx.get("fund") is not None:
        fsm, frr, fih = ctx["fund"]
        c2["fund"] = (fsm, np.where(fsm >= DATA_START + tc * MIN, rng.normal(0, 0.01, frr.size), frr), fih)
    if ctx["mkt"] is not None:
        mk = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in ctx["mkt"].items()}
        mk["C"][tc:] = np.exp(rng.normal(5, 1, mk["C"].size - tc))
        mk["ratio"][tc // 60 + 1:] = rng.random(mk["ratio"].size - tc // 60 - 1) * 3
        mk["dc"][tc_day:] = np.exp(rng.normal(5, 1, nday - tc_day))
        mk["up"][tc_day + 1:] = rng.random(nday - tc_day - 1) < 0.5
        mk["dn"][tc_day + 1:] = rng.random(nday - tc_day - 1) < 0.5
        c2["mkt"] = mk
    a2 = process_symbol(s, (O, H, L, C, QV, valid), c2, collect_units=True)
    nchk, nbad = 0, 0
    for key, u1 in a1["units"].items():
        R1 = u1["R"]
        end1 = np.where(R1["filled"], R1["x"], u1["t0"] + u1["T"] - 1)
        keep = (end1 < tc - 2) & (u1["t0"] < tc)
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
                    (not u1["ok"][i] or (R1["net"][i] == R2["net"][j] and R1["x"][i] == R2["x"][j]
                                         and u1["neth"][i] == u2["neth"][j])))
            for cid, m1 in u1["memb"].items():
                m2 = u2["memb"].get(cid)
                same = same and bool(m1[i]) == (bool(m2[j]) if m2 is not None else False)
            nbad += 0 if same else 1
    return dict(sym=s, tc_min=int(tc), n_checked=nchk, n_diff=nbad, ok=(nchk > 0 and nbad == 0))


# ------------------------------------------------------------------ V5: doc lai tho + cai dat doc lap (kref)
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


def v5_check(s, kl, fu_paths, life, res, ctx, rng, nmax=4):
    out = []
    mkt_sym = ctx["mkt_sym"]
    aux = res["aux"]
    for key in sorted(res["units"]):
        u = res["units"][key]
        R = u["R"]
        cand = np.nonzero(u["ok"])[0]
        if cand.size == 0:
            continue
        i = int(rng.choice(cand))
        t0 = int(u["t0"][i])
        D = t0 // 1440
        base = DATA_START + (D - 32) * DAY
        hi_ms = DATA_START + (int(R["x"][i]) + 5) * MIN
        Ol, Hl, Ll, Cl = _raw_bars(kl, s, base, hi_ms)
        Cb = _raw_bars(kl, mkt_sym, base, hi_ms)[3]
        nmin = len(Cl)
        dclose, dcb = _dclose(Cl, 32), _dclose(Cb, 32)
        sg = kref.ref_sigma(dclose, 32)
        prev = []
        for v in (Ol, Hl, Ll, Cl):
            prev += [x for x in v[31 * 1440:32 * 1440] if x is not None]
        tk = kref.ref_tick(prev)
        hourly = [kref.ref_hourly_close(Cl, h) for h in range(32 * 24)]
        er_r = kref.ref_er30(hourly, 32)
        up_r, dn_r = kref.ref_updown(dclose, 32)
        beta_r = kref.ref_beta(dclose, dcb, 32)
        fl, ev = [], []
        for y, p in sorted(fu_paths.items()):
            f = pd.read_parquet(p)
            f = f[(f.sym.astype(str) == s)]
            ih = f["interval_h"] if "interval_h" in f.columns else pd.Series(8.0, index=f.index)
            for t_, rt, i_ in zip(f.ts, f.rate, ih):
                if base - 3 * DAY <= t_ <= hi_ms:
                    ev.append((int(t_), float(rt), float(i_)))
                if base <= t_ <= hi_ms:
                    fl.append((int((t_ - base) // MIN), float(rt)))
        fl.sort()
        f3_r = kref.ref_f3(ev, DATA_START + D * DAY)
        dl = -1
        l_ = life.get(s, {}).get("last")
        if l_ is not None and l_ < SEAL - DAY:
            vi = [k for k in range(nmin) if Cl[k] is not None and base + k * MIN <= l_]
            dl = vi[-1] if vi and (base + (nmin - 1) * MIN) > l_ else -1
        c = CK_ALL[key[0]][0]
        sd = int(u["side"][i])
        rr = kref.simulate_unit(Ol, Hl, Ll, Cl, t0 - (D - 32) * 1440, c * sg, int(u["T"]), int(u["T"]), tk, float(u["slip"][i]),
                                key[1], sd, fl, dl)
        okv = (rr["filled"] and abs(rr["net"] - R["net"][i]) < 1e-9 and abs(c * sg - u["d"][i]) < 1e-12 and tk == u["tick"][i]
               and ((np.isnan(er_r) and np.isnan(aux["er"][D])) or abs(er_r - aux["er"][D]) < 1e-12)
               and up_r == bool(aux["up"][D]) and dn_r == bool(aux["dn"][D]) and abs(beta_r - aux["beta"][D]) < 1e-9
               and ((np.isnan(f3_r) and np.isnan(aux["f3"][D])) or abs(f3_r - aux["f3"][D]) < 1e-15))
        out.append(dict(ck=key[0], model=key[1], side=sd, t0=t0, net_main=float(R["net"][i]), net_ref=rr.get("net"),
                        er=[float(aux["er"][D]), er_r], beta=[float(aux["beta"][D]), beta_r], f3=[float(aux["f3"][D]), f3_r],
                        updown=[bool(aux["up"][D]), up_r, bool(aux["dn"][D]), dn_r], ok=bool(okv)))
        if len(out) >= nmax:
            break
    return out


def save_tables(res, base):
    for t in TABLES:
        res[t].to_parquet("%s.%s.parquet" % (base, t), index=False)


def reduce_tables(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for t, kk in TKEYS.items():
        parts = [pd.read_parquet(p) for p in sorted(glob.glob(os.path.join(src_dir, "*.%s.parquet" % t)))]
        parts = [p for p in parts if len(p)]
        if not parts:
            continue
        df = pd.concat(parts, ignore_index=True)
        if "sym" in df.columns and "sym" not in kk:
            df = df.drop(columns=["sym"])
        df.groupby(kk, as_index=False).sum(numeric_only=True).to_parquet(os.path.join(dst_dir, "%s.parquet" % t), index=False)


# ------------------------------------------------------------------ run
def _v3_sym(res, arr, nday, s):
    """Bo dem V3 cua 1 symbol (luu vao checkpoint - R3-11)."""
    G = res["aux"]["G"]
    lg = np.diff(np.r_[0, G["lgc"]])
    out = dict(long_gaps=int(np.sum(np.diff(np.r_[0, (lg > 0).astype(np.int8)]) == 1)),
               feat_mismatch_days=int(res["aux"]["feat_mismatch"]), units_excl_gap=0, units_excl_noend=0, sym_month_missing=[])
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
    """Chay 1 shard. test_overrides (CHI test noi bo): dict registry / mkt_sym / cond / v4_syms."""
    check_env()
    tov = dict(test_overrides or {})
    inp = os.environ.get("GRIDV2_INPUT", "/kaggle/input")
    out = os.environ.get("GRIDV2_OUT", "/kaggle/working")
    os.makedirs(os.path.join(out, "agg_sym"), exist_ok=True)
    fh = logging.FileHandler(os.path.join(out, "run.log"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=[logging.StreamHandler(sys.stdout), fh],
                        force=True)
    si, sk = [int(x) for x in os.environ.get("GRIDV2_SHARD", "0/1").split("/")]
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
    meta = {}
    for (y, mo), p in kl.items():
        meta[y] = meta.get(y, 0) + pq.ParquetFile(p).metadata.num_rows
    VS.v["V0"].update(meta_rows=meta, registry=registry,
                      ok_registry=(registry is None) or all(meta.get(y) == registry[y] for y in registry))
    life = load_life(lpath)
    qv, act, hc, rows = pass1(kl, VS, nday)
    VS.v["V0"]["rows_read_pass1"] = rows
    VS.v["V0"]["ok_read_eq_meta"] = all(rows.get(y, 0) == meta[y] for y in meta)
    ok2, mx2, fr2 = v2_eval(VS.v["V2"]["by_year"])
    VS.v["V2"].update(ok=ok2, max_bad_frac=mx2, bad_frac_by_year=fr2)
    if not ok2:
        json.dump(VS.v, open(os.path.join(out, "validate.json"), "w"), indent=1, default=str)
        raise RuntimeError("V2 FAIL: ti le dong active xau %.5f > %.4f - DUNG" % (mx2, V2_MAX_BAD_FRAC))
    tiers = build_tiers(qv, act, life, nday)
    thr, er_p1, sg_p1 = cross_section(tiers, hc, nday)
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
    v4, v5 = [], []
    for k_ in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days"):
        VS.v["V3"][k_] = 0
    VS.v["V3"]["n_sym_from_checkpoint"] = 0
    for n_i, s in enumerate(mine):
        base = os.path.join(out, "agg_sym", s)
        if all(os.path.exists("%s.%s.parquet" % (base, t)) for t in TABLES) and os.path.exists(base + ".v3.json") and n_i > nv4:
            v3s = json.load(open(base + ".v3.json"))            # checkpoint: lay lai bo dem V3 (R3-11)
            VS.v["V3"]["n_sym_from_checkpoint"] += 1
        else:
            arr = load_symbol(kl, s, nday)
            dl = delist_index(s, life, arr[5])
            ctx = dict(nday=nday, tier=tiers[s], qvd=qv[s], fund=fund.get(s), dl=dl, first_ms=life[s]["first"], mkt=mkt,
                       mkt_sym=mkt_sym, thr=thr, CP=CP, er_p1=er_p1[s], sig_p1=sg_p1[s])
            res = process_symbol(s, arr, ctx, collect_units=(n_i <= nv4))
            v3s = _v3_sym(res, arr, nday, s)
            if n_i < nv4:
                v4.append(v4_check(s, arr, ctx, rng))
                log.info("V4 %s", v4[-1])
            if res["units"] and len(v5) < 8:
                v5 += v5_check(s, kl, fu, life, res, ctx, rng)
            save_tables(res, base)
            json.dump(v3s, open(base + ".v3.json", "w"))
            log.info("sym %s (%d/%d) dl=%d rows=%d %.0fs", s, n_i + 1, len(mine), dl, len(res["agg"]), time.time() - t_start)
        for k_ in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days"):
            VS.v["V3"][k_] += int(v3s[k_])
        VS.v["V3"]["sym_month_missing"] += v3s["sym_month_missing"]
    reduce_tables(os.path.join(out, "agg_sym"), os.path.join(out, "reduced"))
    if os.environ.get("GRIDV2_KEEP_SYM", "0") != "1":
        for p in glob.glob(os.path.join(out, "agg_sym", "*.parquet")) + glob.glob(os.path.join(out, "agg_sym", "*.v3.json")):
            os.remove(p)
    VS.v["V4"] = dict(checks=v4, ok=bool(v4) and all(x["ok"] for x in v4))
    VS.v["V5"] = dict(checks=v5, ok=bool(v5) and all(x["ok"] for x in v5))
    v = VS.v
    v["V1"]["ok"] = (not v["V1"]["bad"]) and v["V1"]["ts_max"] is not None and v["V1"]["ts_max"] < SEAL
    v["V3"]["ok"] = v["V3"]["feat_mismatch_days"] == 0
    v["all_pass"] = bool(v["V0"]["ok_registry"] and v["V0"]["ok_read_eq_meta"] and v["V1"]["ok"] and v["V2"]["ok"]
                         and v["V3"]["ok"] and v["V4"]["ok"] and v["V5"]["ok"] and v["V6"]["ok"])
    man = dict(shard="%d/%d" % (si, sk), n_sym=len(mine), cond=CP, mkt_sym=mkt_sym, prereg_constants=prereg_constants,
               test_overrides=tov, alpha_fwer=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS,
               inputs={os.path.basename(p): sha256_file(p) for p in [lpath] + list(fu.values())},
               code={f: sha256_file(os.path.join(HERE, f)) for f in ("klite.py", "kref.py", "runner_kaggle.py", "stats.py")},
               seconds=round(time.time() - t_start, 1))
    json.dump(v, open(os.path.join(out, "validate.json"), "w"), indent=1, default=str)
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1, default=str)
    log.info("XONG all_pass=%s %.0fs", v["all_pass"], time.time() - t_start)
    return v, man


# ------------------------------------------------------------------ merge + thong ke
def load_reduced(dirs):
    out = {}
    for t, kk in TKEYS.items():
        parts = [pd.read_parquet(os.path.join(d, "reduced", "%s.parquet" % t)) for d in dirs
                 if os.path.exists(os.path.join(d, "reduced", "%s.parquet" % t))]
        out[t] = pd.concat(parts, ignore_index=True).groupby(kk, as_index=False).sum(numeric_only=True) if parts else pd.DataFrame()
    return out


def day_matrix(A, lo, hi, col, J):
    M = np.zeros((hi - lo, J))
    sub = A[(A.day >= lo) & (A.day < hi)]
    if len(sub):
        np.add.at(M, (sub.day.to_numpy().astype(int) - lo, sub.cell.to_numpy().astype(int)), sub[col].to_numpy())
    return M


def load_expected_sha(path):
    """EXPECTED_SHA.txt dang sha256sum: '<sha>  <ten file>' -> {ten: sha}; phai du SHA_FILES."""
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
    """R4-3: du DUNG 5 shard 0..4/5, khong trung (ca thu muc lan chi so), prereg_constants, V0-V6 all_pass, hang so, cond ==
    COND_PREREG, mkt_sym == BTCUSDT, sha code trong manifest == expected_sha. Sai -> RuntimeError."""
    errs, seen_dir, seen_idx = [], set(), set()
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
        if man.get("cond") != COND_PREREG:
            errs.append("cond != COND_PREREG: %s" % d)
        if man.get("mkt_sym") != MARKET_SYM:
            errs.append("mkt_sym != %s: %s" % (MARKET_SYM, d))
        code = man.get("code") or {}
        for f in SHA_FILES:
            if code.get(f) != expected_sha.get(f):
                errs.append("sha %s lech: %s" % (f, d))
    if seen_idx != set(range(N_SHARDS)):
        errs.append("thieu shard: %s" % sorted(set(range(N_SHARDS)) - seen_idx))
    if errs:
        raise RuntimeError("merge tu choi (R4-3): " + "; ".join(errs))


def merge(outdir, shard_dirs, floor=FLOOR_BPS, nboot=stats.NBOOT, allow_test=False, expected_sha=None):
    """Gop shard + thong ke. Hang so ALPHA_FWER / ALPHA_UPPER / MIN_UNITS = prereg (khong tham so, khong env).
    Chay that: expected_sha = duong dan EXPECTED_SHA.txt (bat buoc); check_shards (R4-3).
    allow_test CHI cho test noi bo (khong co tu CLI): bo qua check_shards, cho nboot != 2000; result.json danh dau TEST_ONLY (R4-4)."""
    check_env()
    if not allow_test:
        if floor != FLOOR_BPS or nboot != stats.NBOOT:
            raise RuntimeError("merge: san / so bootstrap khac prereg")
        if expected_sha is None:
            raise RuntimeError("merge: can --expected-sha (R4-3)")
        check_shards(shard_dirs, load_expected_sha(expected_sha) if isinstance(expected_sha, str) else expected_sha)
    shard_info = []
    for d in shard_dirs:
        mf, vf = os.path.join(d, "manifest.json"), os.path.join(d, "validate.json")
        man = json.load(open(mf)) if os.path.exists(mf) else {}
        val = json.load(open(vf)) if os.path.exists(vf) else {}
        info = dict(dir=d, prereg_constants=bool(man.get("prereg_constants", False)), all_pass=bool(val.get("all_pass", False)),
                    alpha_fwer=man.get("alpha_fwer"), alpha_upper=man.get("alpha_upper"), min_units=man.get("min_units"))
        shard_info.append(info)
    os.makedirs(outdir, exist_ok=True)
    T_ = load_reduced(shard_dirs)
    A, SH, HS = T_["agg"], T_["shalf"], T_["hist"]
    nday = (SEAL - DATA_START) // DAY
    d0 = (STUDY_START - DATA_START) // DAY
    dB = (HALF_B - DATA_START) // DAY
    halves = {"A": (d0, dB), "B": (dB, nday)}
    cl = cells()
    J = len(cl)
    statcol = np.array([c["stat"] for c in cl])
    res = dict(TEST_ONLY=bool(allow_test), allow_test=bool(allow_test), floor=floor, alpha_fwer=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS, nboot=nboot,
               method="studentized_block_bootstrap_RW_maxt", cells=[c["name"] for c in cl], stat=statcol.tolist(),
               shards=shard_info, models={})
    ev_days = [((ms(a) - 3 * DAY - DATA_START) // DAY, (ms(b) + DAY - DATA_START) // DAY) for a, b in EVENTS]

    def pick(Mnet, Mneth):
        return np.where(statcol[None, :] == "neth", Mneth, Mnet)

    for model in ("OPT", "PESS"):
        Am = A[A.model == model]
        R = {}
        for h, (lo, hi) in halves.items():
            Sn, Sh, N = day_matrix(Am, lo, hi, "net", J), day_matrix(Am, lo, hi, "neth", J), day_matrix(Am, lo, hi, "fill", J)
            S = pick(Sn, Sh)
            st = stats.cell_stats(S, N, floor, SEED_BOOT + (0 if h == "A" else 1) + (0 if model == "OPT" else 10), B=nboot,
                                  alpha=ALPHA_FWER, alpha_upper=ALPHA_UPPER, min_units=MIN_UNITS)
            ex = {c: day_matrix(Am, lo, hi, c, J).sum(0) for c in ("gross", "grossh", "fee", "slip", "fund", "cap", "lim",
                                                                     "place", "excl", "excl_gap", "holdmin", "hb_sum", "hb_n",
                                                                     "hcost")}
            Nt = np.maximum(N.sum(0), 1)
            st["M_raw_net"] = Sn.sum(0) / Nt
            st["M_neth"] = Sh.sum(0) / Nt
            st["gross_mean"] = ex["gross"] / Nt
            st["grossh_mean"] = ex["grossh"] / Nt
            st["cap_mean"] = ex["cap"] / Nt
            st["M_adj_C4"] = st["M"] - st["cap_mean"]
            st["fill_rate"] = N.sum(0) / np.maximum(ex["place"] - ex["excl"], 1)
            for c in ("fee", "slip", "fund"):
                st[c + "_mean"] = ex[c] / Nt
            st["p_lim_exit"] = ex["lim"] / Nt
            st["gross_per_min_held"] = ex["gross"] / np.maximum(ex["holdmin"], 1)
            st["hold_bench_per_min"] = ex["hb_sum"] / np.maximum(ex["hb_n"], 1)
            st["excl_gap_rate"] = ex["excl_gap"] / np.maximum(ex["place"], 1)            # chan doan (12)
            st["M_neth_minus_hedge_fee"] = (Sh.sum(0) - ex["hcost"]) / Nt                # chan doan (13): - 2 x 5 bps x beta
            hv = 0 if h == "A" else 1
            top3 = []
            for c in range(J):
                sc = SH[(SH.model == model) & (SH.half == hv) & (SH.cell == c)] if len(SH) else SH
                if len(sc) == 0:
                    top3.append(np.nan)
                    continue
                col = cl[c]["stat"]
                gs = sc.groupby("sym")[[col, "fill"]].sum().sort_values(col, ascending=False)
                rest = gs.iloc[3:]
                top3.append(rest[col].sum() / max(rest.fill.sum(), 1))
            st["M_drop_top3"] = np.array(top3)
            keep = np.ones(hi - lo, bool)
            for (elo, ehi) in ev_days:
                a_, b_ = max(elo, lo) - lo, min(ehi, hi) - lo
                if b_ > a_:
                    keep[a_:b_] = False
            st["M_drop_events"] = S[keep].sum(0) / np.maximum(N[keep].sum(0), 1)
            yrs = {}
            for y in range(2021, 2026):
                ylo = max(lo, (ms("%d-01-01" % y) - DATA_START) // DAY)
                yhi = min(hi, (ms("%d-01-01" % (y + 1)) - DATA_START) // DAY)
                if yhi > ylo:
                    yrs[y] = (S[ylo - lo:yhi - lo].sum(0) / np.maximum(N[ylo - lo:yhi - lo].sum(0), 1)).tolist()
            st["M_by_year"] = yrs
            n2 = pick(day_matrix(Am, lo, hi, "net2", J), day_matrix(Am, lo, hi, "neth2", J)).sum(0)
            n3 = pick(day_matrix(Am, lo, hi, "net3", J), day_matrix(Am, lo, hi, "neth3", J)).sum(0)
            mu = S.sum(0) / Nt
            var = n2 / Nt - mu ** 2
            with np.errstate(invalid="ignore", divide="ignore"):
                st["skew"] = (n3 / Nt - 3 * mu * n2 / Nt + 2 * mu ** 3) / var ** 1.5
                st["sd_unit"] = np.sqrt(var)
            q1, q5 = [], []
            for c in range(J):
                hh = HS[(HS.cell == c) & (HS.model == model) & (HS.half == hv)].sort_values("bin") if len(HS) else HS
                if len(hh) == 0:
                    q1.append(np.nan); q5.append(np.nan)
                    continue
                cc = np.cumsum(hh["count"].to_numpy()) / hh["count"].sum()
                b = hh["bin"].to_numpy()
                q1.append(float(b[np.searchsorted(cc, 0.01)]))
                q5.append(float(b[np.searchsorted(cc, 0.05)]))
            st["q01_unit"], st["q05_unit"] = np.array(q1), np.array(q5)
            R[h] = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in st.items()}
        pas, beta_flag = [], []
        for c in range(J):
            b, a = R["B"], R["A"]
            ok = (bool(b["rw_reject"][c]) and not b["insufficient"][c] and not a["insufficient"][c]
                  and np.isfinite(a["M"][c]) and a["M"][c] > floor and np.isfinite(a["p_marg"][c]) and a["p_marg"][c] <= 0.10
                  and b["M_adj_C4"][c] > 0 and b["M_drop_top3"][c] > floor and b["M_drop_events"][c] > floor
                  and a["M_drop_events"][c] > floor)
            pas.append(bool(ok))
            # R4-5: co BETA = net tho nua B > 4 VA net_h nua B <= 4 (diem uoc), chi o G-D; luon bao cao ca hai so
            beta_flag.append(bool(cl[c]["stat"] == "neth" and b["M_raw_net"][c] > floor and b["M_neth"][c] <= floor))
        R["PASS"], R["BETA_flag"] = pas, beta_flag
        R["BETA_detail"] = [dict(cell=cl[c]["name"], M_raw_net_B=R["B"]["M_raw_net"][c], M_neth_B=R["B"]["M_neth"][c],
                                 BETA=beta_flag[c]) for c in range(J) if cl[c]["stat"] == "neth"]
        up = np.array(R["B"]["upper_sim95"], dtype=float)
        ins = np.array(R["B"]["insufficient"], dtype=bool)
        R["INSUFFICIENT_B"] = [cl[c]["name"] for c in range(J) if ins[c]]
        R["INSUFFICIENT_A"] = [cl[c]["name"] for c in range(J) if R["A"]["insufficient"][c]]
        # L-A (R3-2, R3-3): CA 32 o du du lieu, can tren huu han va < san
        R["strong_close_all_upper_lt_floor_B"] = bool((not ins.any()) and np.all(np.isfinite(up)) and np.all(up < floor))
        res["models"][model] = R
    opt, pes = res["models"]["OPT"]["PASS"], res["models"]["PESS"]["PASS"]
    res["rule_core"] = "L-D" if any(pes) else ("L-C" if any(opt) else
                                               ("L-A" if res["models"]["OPT"]["strong_close_all_upper_lt_floor_B"] else "L-B"))
    res["rule"] = ("TEST_ONLY:" if allow_test else "") + res["rule_core"]          # R4-4
    res["L_A_blocked_by_insufficient_OPT"] = res["models"]["OPT"]["INSUFFICIENT_B"]
    json.dump(res, open(os.path.join(outdir, "result.json"), "w"), indent=1,
              default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    D_ = T_["diag"]
    diag = []
    for r in (D_.itertuples() if len(D_) else []):
        diag.append(dict(ck="c%.1f_k%d" % CK_ALL[int(r.ck)], model=r.model, half="AB"[int(r.half)], dim=r.dim, level=r.level,
                         n=int(r.fill), M=r.net / max(r.fill, 1), M_neth=r.neth / max(r.fill, 1), gross=r.gross / max(r.fill, 1)))
    MO = T_["mon"]
    monthly = []
    if len(MO):
        for (ck, model), g in MO.groupby(["ck", "model"]):
            for h, (a, b) in (("A", ("2021-07", "2023-12")), ("B", ("2024-01", "2025-12"))):
                gg = g[(g.month >= a) & (g.month <= b)]
                m_ = gg.net / gg.fill.clip(lower=1)
                monthly.append(dict(ck="c%.1f_k%d" % CK_ALL[int(ck)], model=model, half=h, frac_month_pos=float((m_ > 0).mean()),
                                    median_month_M=float(m_.median()), n_month=int(len(gg))))
    TD = T_["tdiag"]
    tier_split = []                                    # (11) tach tier cho o G-S / G-D
    for r in (TD.itertuples() if len(TD) else []):
        tier_split.append(dict(cell=cl[int(r.cell)]["name"], model=r.model, half="AB"[int(r.half)], tier=int(r.tier),
                               n_place=int(r.place), n_fill=int(r.fill), M=r.net / max(r.fill, 1), M_neth=r.neth / max(r.fill, 1),
                               excl_gap_rate=r.excl_gap / max(r.place, 1)))
    excl_rate, hedge_fee = [], []                      # (12) ti le loai lo > 60' ; (13) net_h - 2 x 5 bps x beta (G-D)
    for model in ("OPT", "PESS"):
        for h in ("A", "B"):
            Rm = res["models"][model][h]
            for c in range(J):
                excl_rate.append(dict(cell=cl[c]["name"], model=model, half=h, excl_gap_rate=Rm["excl_gap_rate"][c]))
                if cl[c]["grp"] == "D":
                    hedge_fee.append(dict(cell=cl[c]["name"], model=model, half=h, M_neth=Rm["M_neth"][c],
                                          M_neth_minus_hedge_fee=Rm["M_neth_minus_hedge_fee"][c]))
    json.dump(dict(diag=diag, monthly=monthly, tier_split=tier_split, excl_rate=excl_rate, hedge_fee=hedge_fee),
              open(os.path.join(outdir, "diag.json"), "w"), indent=1, default=float)
    return res, T_


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "merge":
        # python3 runner_kaggle.py merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 d1 d2 d3 d4
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
        a = sys.argv[2:]
        if len(a) < 3 or a[1] != "--expected-sha":
            raise SystemExit("dung: merge OUT_DIR --expected-sha EXPECTED_SHA.txt d0 .. d4")
        merge(a[0], a[3:], expected_sha=a[2])
    else:
        run()
