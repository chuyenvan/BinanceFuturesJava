#!/usr/bin/env python3
"""HO26_LUCK_AUDIT (2026-10-10): audit chong "so may" holdout 2026H1 (K24+skipFull vs B0 K16).

Pre-reg: docs/audit/HO26_LUCK_AUDIT.md PHAN 1 (09969df9, commit TRUOC khi do). 0 sua Java, 0 build, 0 Java sim tren
Oracle, 0 cham 242/shadow. Kaggle chi o A5 (orchestrator ~/claude_master/1010/aud26/aud26_queue.py).
Binance Vision tai TRONG BO NHO (khong ghi dia).
Stage: a1 | a1x (bo sung sau A1, mo ta) | a2 | a3 | a4 | a5 | a6 | report.  Usage: python3 research/analysis/ho26_luck_audit.py <stage>
"""
import gzip
import io
import json
import logging
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("aud26")

OUT = "/home/ubuntu/kaggle_sim/out/"
WD = "/home/ubuntu/claude_master/1010/aud26"
TICK = "/home/ubuntu/kaggle_data_hpo"
BINS = "/home/ubuntu/claude_master/1009/ho26/bins2026Ax"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
RES_A = REPO + "/docs/result/ho26/HO26_RESULT_A.json"
JSON_OUT = REPO + "/docs/audit/HO26_LUCK_AUDIT.json"
VIS = "https://data.binance.vision/data/futures/um/"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
MN, H, D = 60000, 3600000, 86400000
TZ = 7 * H
T0 = 1767200400000                     # 2026-01-01 00:00 +07
ND = 181
T1 = T0 + ND * D                       # 2026-07-01 00:00 +07
NW = ND * 1440
PEN, CRASH, TOL = 0.01675, -0.01, 1e-6
COST = 0.000982 + 2 * 0.000067
RSEED, NREP, NREP4, POOL = 20261010, 5000, 1000, 4000
K24 = 24
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT"}
MONTHS = ["2026-%02d" % m for m in range(1, 7)]


def tag(cfg, s, fee="s"):
    return "ho26-%s-%s-s%d" % (cfg, fee, s)


def pmin(col):
    t = pd.to_datetime(pd.Series(col).astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    return (t.values.astype("datetime64[ms]").astype(np.int64) - TZ)


def load_pd(t):
    d = pd.read_csv(OUT + t + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "tp", "profit", "margin", "pnl", "quantity"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["entry", "margin", "pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["ts"] = pmin(d["start"])
    d["te"] = pmin(d["end"])
    d = d.sort_values(["sym", "te", "ts"], kind="mergesort").reset_index(drop=True)
    g = d.groupby(["sym", "te"], sort=False)
    d["leg0"] = g.cumcount() == 0
    d["nleg"] = g["ts"].transform("size")
    d["symt"] = d["sym"] + "USDT"
    return d.sort_values(["ts", "sym"], kind="mergesort").reset_index(drop=True)


def wsum(d):
    """Sum PnL_S cua so (end in W)."""
    return float(d.loc[(d["te"] >= T0) & (d["te"] < T1), "pnl"].sum())


def take_lock(name):
    while os.path.exists(LOCK):
        log.info("lock dang giu: %s — cho 60s", open(LOCK).read().strip()[:120])
        time.sleep(60)
    with open(LOCK, "w") as f:
        f.write("aud26 %s pid=%d %s\n" % (name, os.getpid(), time.strftime("%Y-%m-%d %H:%M:%S")))


def drop_lock():
    try:
        if os.path.exists(LOCK) and open(LOCK).read().startswith("aud26"):
            os.remove(LOCK)
    except OSError:
        pass


def tojs(o):
    if isinstance(o, dict):
        return {str(k): tojs(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tojs(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return tojs(o.tolist())
    return o


def save(name, obj):
    json.dump(tojs(obj), open(WD + "/%s.json" % name, "w"), indent=1, ensure_ascii=False)
    log.info("ghi %s/%s.json", WD, name)


def http(url, tries=3):
    """GET -> bytes; 404 -> None."""
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:  # noqa: BLE001
            err = e
        time.sleep(2 * (k + 1))
    raise RuntimeError("http fail %s: %s" % (url, err))


def kl(url):
    """Vision kline zip (trong bo nho) -> DataFrame ot,o,h,l,c,qv (ot = open_time ms) hoac None neu 404."""
    b = http(url)
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = z.read(z.namelist()[0]).decode()
    lines = [x for x in raw.splitlines() if x and x[0].isdigit()]
    if not lines:
        return pd.DataFrame(columns=["ot", "o", "h", "l", "c", "qv"])
    a = pd.read_csv(io.StringIO("\n".join(lines)), header=None)
    ot = a[0].astype(np.int64)
    if ot.iloc[0] > 10 ** 14:                         # micro giay (Vision 2025+ spot) -> ms
        ot = ot // 1000
    return pd.DataFrame(dict(ot=ot, o=a[1].astype(float), h=a[2].astype(float), l=a[3].astype(float),
                             c=a[4].astype(float), qv=a[7].astype(float)))


def vday(sym, day):
    return kl(VIS + "daily/klines/%s/1m/%s-1m-%s.zip" % (sym, sym, day))


def s3_keys(prefix):
    keys, marker = [], ""
    while True:
        b = http(S3 + "?prefix=%s&marker=%s" % (prefix, marker)).decode()
        ks = re.findall(r"<Key>([^<]+)</Key>", b)
        keys += ks
        if "<IsTruncated>true</IsTruncated>" not in b or not ks:
            return keys
        marker = ks[-1]


def crash_log(t):
    """[CRASH-PENALTY] leg sap sym=X t=YYYYMMDD HH:MM barRet=.. -> set (symt, ts ms UTC)."""
    rx = re.compile(r"leg sap sym=(\S+) t=(\d{8} \d{2}:\d{2}) barRet=(-?[0-9.eE+-]+)")
    out = {}
    with open(OUT + t + "/logs/sim.out", errors="ignore") as f:
        for ln in f:
            m = rx.search(ln)
            if m:
                out[(m.group(1), int(pmin([m.group(2)])[0]))] = float(m.group(3))
    return out


def stage_a1():
    """Kiem gia doc lap Vision cho ho26-{k24,b0}-s-s42 + kiem du lieu + delist."""
    need, L = set(), {}
    for cfg in ("k24", "b0"):
        d = load_pd(tag(cfg, 42))
        L[cfg] = d
        for col in ("ts", "te"):
            x = d.loc[(d[col] >= T0) & (d[col] < T1)]
            for s, t in zip(x["symt"], x[col]):
                for lag in (-1, 0, 1):
                    need.add((s, time.strftime("%Y-%m-%d", time.gmtime((t + lag * MN) / 1000))))
    log.info("A1: can %d file (sym, ngay)", len(need))
    need = sorted(need)
    with ThreadPoolExecutor(8) as ex:
        got = dict(zip(need, ex.map(lambda k: vday(*k), need)))
    vstat = dict(files=len(need), n404=sum(v is None for v in got.values()), rows_bad=0, zero=0, nan=0)
    K = {}
    vstat["missing_min"] = 0
    for (s, day), df in got.items():
        if df is None:
            continue
        if len(df) != 1440:
            vstat["rows_bad"] += 1
            vstat["missing_min"] += 1440 - len(df.drop_duplicates("ot"))
        v = df[["o", "h", "l", "c"]].to_numpy()
        vstat["zero"] += int((v == 0).sum())
        vstat["nan"] += int(np.isnan(v).sum())
        for r in df.itertuples(index=False):
            K[(s, int(r.ot))] = (r.o, r.h, r.l, r.c)
    res = dict(vision=vstat, cfg={})
    for cfg, d in L.items():
        cl = crash_log(tag(cfg, 42))
        E = d.loc[(d["ts"] >= T0) & (d["ts"] < T1)]
        X = d.loc[(d["te"] >= T0) & (d["te"] < T1)]
        er = {lag: dict(ok=0, bad=0, nosrc=0) for lag in (-1, 0, 1)}
        bad_e, flag = [], dict(both=0, vis_only=0, sim_only=0, none=0)
        for r in E.itertuples(index=False):
            for lag in (-1, 0, 1):
                k = K.get((r.symt, int(r.ts) + lag * MN))
                if k is None:
                    er[lag]["nosrc"] += 1
                    continue
                o, c = k[0], k[3]
                cr = (c / o - 1.0) <= CRASH if o > 0 else False
                exp = c * (1.0 + PEN) if cr else c
                ok = abs(r.entry / exp - 1.0) <= TOL if exp > 0 else False
                er[lag]["ok" if ok else "bad"] += 1
                if lag == 0:
                    sc = (r.symt, int(r.ts)) in cl
                    flag["both" if (cr and sc) else "vis_only" if cr else "sim_only" if sc else "none"] += 1
                    if not ok:
                        bad_e.append(dict(sym=r.sym, start=r.start, level=r.level, entry=r.entry, v_close=c,
                                          v_open=o, vis_crash=bool(cr), sim_crash=bool(sc),
                                          rel=float(r.entry / exp - 1.0) if exp > 0 else None,
                                          rel_close=float(r.entry / c - 1.0) if c > 0 else None))
        xr = {lag: dict(ok=0, bad=0, nosrc=0) for lag in (-1, 0, 1)}
        bad_x, tpchk = [], []
        for r in X.itertuples(index=False):
            if np.isfinite(r.tp) and np.isfinite(r.profit) and r.entry > 0:
                tpchk.append(abs(r.tp / (r.entry * (1 + r.profit / 100.0)) - 1.0))
            for lag in (-1, 0, 1):
                k = K.get((r.symt, int(r.te) + lag * MN))
                if k is None:
                    xr[lag]["nosrc"] += 1
                    continue
                lo, hi = k[2], k[1]
                ok = lo * (1 - TOL) <= r.tp <= hi * (1 + TOL)
                xr[lag]["ok" if ok else "bad"] += 1
                if lag == 0 and not ok:
                    bad_x.append(dict(sym=r.sym, end=r.end, level=r.level, tp=r.tp, v_low=lo, v_high=hi,
                                      rel_out=float(r.tp / hi - 1 if r.tp > hi else r.tp / lo - 1)))
        tpchk = np.array(tpchk)
        pct = lambda z: 100.0 * z["ok"] / max(1, z["ok"] + z["bad"])  # noqa: E731
        res["cfg"][cfg] = dict(n_entry=len(E), n_exit=len(X), entry=er, exit=xr,
                               entry_pct={lag: pct(er[lag]) for lag in er}, exit_pct={lag: pct(xr[lag]) for lag in xr},
                               crash_flag=flag, n_crash_log_W=sum(1 for k in cl if T0 <= k[1] < T1),
                               tp_consistency=dict(n=len(tpchk), max=float(tpchk.max()) if len(tpchk) else None,
                                                   n_gt_1e4=int((tpchk > 1e-4).sum())),
                               bad_entry=bad_e, bad_exit=bad_x)
        log.info("A1 %s: entry lag0 %.2f%% %s | exit lag0 %.2f%% %s | crash %s", cfg, pct(er[0]), er[0], pct(xr[0]),
                 xr[0], flag)
    syms = set()
    for cfg in ("k24", "b0"):
        for s in SEEDS:
            d = load_pd(tag(cfg, s))
            x = d.loc[(d["te"] >= T0) & (d["ts"] < T1)]
            syms |= set(x["symt"])
    syms = sorted(syms)

    def last_day(s):
        ks = s3_keys("data/futures/um/daily/klines/%s/1m/%s-1m-2026-" % (s, s))
        ds = sorted(re.findall(r"-1m-(\d{4}-\d{2}-\d{2})\.zip$", "\n".join(ks), re.M))
        return s, (ds[0] if ds else None), (ds[-1] if ds else None)
    with ThreadPoolExecutor(8) as ex:
        LD = list(ex.map(last_day, syms))
    dl = [dict(sym=s, first=a, last=b) for s, a, b in LD if b is None or b < "2026-06-30"]
    late = [dict(sym=s, first=a, last=b) for s, a, b in LD if a is not None and a > "2026-01-01"]
    res["delist"] = dict(n_syms=len(syms), delisted_in_W=dl, listed_in_W=late)
    log.info("A1 delist: %d/%d symbol het du lieu < 2026-06-30: %s", len(dl), len(syms), dl[:10])
    save("a1", res)


def a2_one(d):
    """Cac phep bo tren Sum PnL_S cua 1 run."""
    x = d.loc[(d["te"] >= T0) & (d["te"] < T1)].copy()
    tot = float(x["pnl"].sum())
    x["mon"] = pd.to_datetime(x["te"] + TZ, unit="ms").dt.strftime("%Y-%m")
    x["day"] = (x["te"] - T0) // D
    pm = x.groupby("mon")["pnl"].sum()
    out = dict(total=tot, by_month={m: float(pm.get(m, 0.0)) for m in MONTHS})
    out["drop_month"] = {m: tot - out["by_month"][m] for m in MONTHS}
    pdy = np.sort(x.groupby("day")["pnl"].sum().to_numpy())[::-1]
    out["drop_top"] = {k: tot - float(pdy[:k].sum()) for k in (1, 3, 5)}
    out["top_days"] = [float(v) for v in pdy[:5]]
    e = d.loc[(d["ts"] >= T0) & (d["ts"] < T1)]
    sd = np.unique((e["ts"].to_numpy() - T0) // D)
    if len(sd):
        brk = np.concatenate([[False], np.diff(sd) - 1 >= 3])
        epi = np.cumsum(brk)
        ep_of = dict(zip(sd.tolist(), epi.tolist()))
        xs = x.loc[(x["ts"] >= T0) & (x["ts"] < T1)]
        ep = xs.groupby(((xs["ts"] - T0) // D).map(ep_of))["pnl"].sum()
        big = int(ep.idxmax())
        out["episodes"] = int(epi[-1]) + 1
        out["drop_ep"] = tot - float(ep.max())
        out["big_ep"] = dict(id=big, pnl=float(ep.max()), d0=int(sd[epi == big][0]), d1=int(sd[epi == big][-1]))
    else:
        out["episodes"], out["drop_ep"], out["big_ep"] = 0, tot, None
    out["june_share"] = out["by_month"]["2026-06"] / tot if tot else None
    return out


def summ(v):
    v = np.asarray(v, float)
    return dict(mean=float(v.mean()), min=float(v.min()), max=float(v.max()), n_pos=int((v > 0).sum()), n=len(v))


def stage_a2():
    R = {cfg: {s: a2_one(load_pd(tag(cfg, s))) for s in SEEDS} for cfg in ("k24", "b0")}
    S = {}
    keys = [("total", None)] + [("drop_month", m) for m in MONTHS] + [("drop_top", k) for k in (1, 3, 5)] + \
        [("drop_ep", None)]
    for cfg in R:
        S[cfg] = {}
        for a, b in keys:
            nm = a if b is None else "%s_%s" % (a, b)
            S[cfg][nm] = summ([R[cfg][s][a] if b is None else R[cfg][s][a][b] for s in SEEDS])
        S[cfg]["june_share"] = summ([R[cfg][s]["june_share"] for s in SEEDS])
    S["delta"] = {nm: summ([(R["k24"][s][a] if b is None else R["k24"][s][a][b]) -
                            (R["b0"][s][a] if b is None else R["b0"][s][a][b]) for s in SEEDS])
                  for a, b in keys for nm in [a if b is None else "%s_%s" % (a, b)]}
    for cfg in ("k24", "b0"):
        log.info("A2 %s: %s", cfg, {k: (round(v["mean"]), v["n_pos"]) for k, v in S[cfg].items() if k != "june_share"})
        log.info("A2 %s june_share mean %.3f", cfg, S[cfg]["june_share"]["mean"])
    save("a2", dict(per_seed=R, summary=S))


def daily_returns():
    """r_d MTM 181 ngay cho 16 run stress, dung thuoc scorer A (cache U_ho26.npz). Tu kiem ROI vs RESULT_A."""
    import ho26_score_a as SA
    SA.W.update(dry=False, T0=SA.ms_local("2026-01-01 00:00"), T1=SA.ms_local("2026-07-01 00:00"))
    SA.W["NW"] = (SA.W["T1"] - SA.W["T0"]) // 60000
    SA.W["ND"] = SA.W["NW"] // 1440
    SA.W["D0"] = pd.Timestamp("2026-01-01 00:00").normalize()
    assert SA.W["T0"] == T0 and SA.W["ND"] == ND
    z = np.load(SA.WD + "/U_ho26.npz")
    U = z["U"]
    tags = sorted(tag(c, s, f) for c in ("b0", "k24", "m2") for f in ("s", "b") for s in SEEDS)
    assert U.shape[0] == len(tags) == 48, U.shape
    SA.W["NE"] = U.shape[1]
    RA = json.load(open(RES_A))["metrics"]
    out, chk = {}, []
    for cfg in ("k24", "b0"):
        for s in SEEDS:
            t = tag(cfg, s)
            d, _ = SA.load(t)
            rj = json.load(open(OUT + t + "/result.json"))
            eq = SA.equity(d, rj["equity_start"], U[tags.index(t)].astype(float))
            m, (e0, Ed) = SA.metr(d, eq)
            ref = RA["%s|s|%d" % (cfg, s)]["roi"]
            chk.append(abs(m["roi"] / ref - 1.0))
            r = Ed / np.concatenate([[e0], Ed[:-1]]) - 1.0
            out[(cfg, s)] = (e0, r, m["roi"], m["sum_pnl"])
    log.info("A3 tu kiem ROI vs RESULT_A: max |rel| = %.2e", max(chk))
    return out, float(max(chk))


def boot_idx(rng, n, b, nrep):
    nb = -(-n // b)
    st = rng.integers(0, n, (nrep, nb))
    return ((st[:, :, None] + np.arange(b)[None, None, :]) % n).reshape(nrep, nb * b)[:, :n]


def stage_a3():
    R, chk = daily_returns()
    rng = np.random.default_rng(RSEED)
    infl = math.sqrt(2 * math.log(2))
    res = dict(selfcheck_roi_max_rel=chk, obs={}, boot={})
    for cfg in ("k24", "b0"):
        res["obs"][cfg] = {s: dict(e0=R[(cfg, s)][0], roi=R[(cfg, s)][2], sum_pnl=R[(cfg, s)][3]) for s in SEEDS}
    for b in (5, 10):
        idx = boot_idx(rng, ND, b, NREP)
        res["boot"][b] = {}
        for cfg in ("k24", "b0"):
            M = np.stack([R[(cfg, s)][1] for s in SEEDS])                    # 8 x 181
            E0 = np.array([R[(cfg, s)][0] for s in SEEDS])
            roi = np.prod(1.0 + M[:, idx], axis=2) - 1.0                     # 8 x NREP
            rr = {}
            for i, s in enumerate(SEEDS):
                rr[s] = bsum(roi[i], E0[i], infl)
            rr["pool"] = bsum(roi.mean(axis=0), E0.mean(), infl)
            res["boot"][b][cfg] = rr
            log.info("A3 block %d %s: pool P(ROI<=0)=%.4f CI95 %s; seed P: %s", b, cfg, rr["pool"]["p_le0"],
                     [round(x, 2) for x in rr["pool"]["ci95_roi"]], [round(rr[s]["p_le0"], 3) for s in SEEDS])
    save("a3", res)


def bsum(roi, e0, infl):
    lo, med, hi = np.percentile(roi, [2.5, 50, 97.5])
    return dict(p_le0=float((roi <= 0).mean()), ci95_roi=[100 * lo, 100 * hi], med_roi=100 * med,
                ci95_roi_infl=[100 * (med - (med - lo) * infl), 100 * (med + (hi - med) * infl)],
                ci95_pnl=[e0 * lo, e0 * hi], mean_roi=100 * float(roi.mean()))


def parse_day(day):
    """ticker sim 1 ngay UTC -> (day, syms, A[nsym,4,1440] o/h/l/c float32). jbin tuple = (start,max,min,close,open,vol)."""
    p = TICK + "/ticker_%s.bin.gz" % day
    if not os.path.exists(p):
        return day, None, None
    U0 = int(pd.Timestamp(day).value // 10 ** 6)
    with gzip.open(p, "rb") as f:
        b = f.read()
    syms, R, C, V = {}, [], [], []
    for k, v in jbin.iter_minutes(b):
        mi = (k - U0) // MN
        if 0 <= mi < 1440:
            for s, t in v.items():
                R.append(mi)
                C.append(syms.setdefault(s, len(syms)))
                V.append(t)
    A = np.full((max(1, len(syms)), 4, 1440), np.nan, np.float32)
    if R:
        R, C, X = np.array(R), np.array(C), np.array(V, np.float64)
        for j, src in enumerate((4, 1, 2, 3)):
            A[C, j, R] = X[:, src]
    return day, list(syms), A


G = {}
NSMAX = 900


def load_ticker(workers=3):
    """P[si, f, m] f=o/h/l/c, m = phut tu T0 (0..NW-1); SI = {symt: si}."""
    days = [x.strftime("%Y%m%d") for x in pd.date_range(pd.Timestamp(T0, unit="ms").normalize(),
                                                         pd.Timestamp(T1 - MN, unit="ms").normalize(), freq="D")]
    SI, miss = {}, []
    t0 = time.time()
    with Pool(workers) as pool:                      # fork TRUOC khi cap phat P (khong nhan ban P vao worker)
        P = np.full((NSMAX, 4, NW), np.nan, np.float32)
        for i, (day, syms, A) in enumerate(pool.imap_unordered(parse_day, days)):
            if syms is None:
                miss.append(day)
                continue
            g0 = (int(pd.Timestamp(day).value // 10 ** 6) - T0) // MN
            a, b = max(0, g0), min(NW, g0 + 1440)
            idx = np.array([SI.setdefault(s, len(SI)) for s in syms])
            assert len(SI) <= NSMAX, len(SI)
            P[idx, :, a:b] = A[:, :, a - g0:b - g0]
            if i % 30 == 0:
                log.info("ticker %d/%d %.0fs nsym %d", i, len(days), time.time() - t0, len(SI))
    log.info("ticker xong: %d ngay, thieu %s, nsym %d", len(days), miss, len(SI))
    G["P"], G["SI"] = P, SI
    return dict(days=len(days), missing_days=miss, nsym=len(SI))


def load_top24():
    """bins S1 2026 (bundle sim-ho26a) -> T15 (ms) + TOP[nmoc, 24] = si ticker (-1 neu khong co)."""
    mp = pd.read_csv(SYMMAP)
    id2s = dict(zip(mp["symId"].astype(int), mp["symbol"].astype(str).str.strip()))
    T, S = [], []
    for f in sorted(os.listdir(BINS)):
        if not (f.startswith("predict_wf_2026") and f.endswith(".bin")):
            continue
        a = np.fromfile(os.path.join(BINS, f), dtype=REC)
        p0 = a["p0"].astype(np.float32)
        ok = ~np.isnan(p0)
        ts, sc, sy = a["ts"][ok].astype(np.int64), (np.float32(1) - p0[ok]), a["sym"][ok].astype(int)
        o = np.lexsort((sc, ts))
        ts, sy = ts[o], sy[o]
        u, st = np.unique(ts, return_index=True)
        cnt = np.diff(np.append(st, len(ts)))
        grp = np.repeat(np.arange(len(u)), cnt)
        rk = np.arange(len(ts)) - st[grp]
        k = rk < K24
        M = np.full((len(u), K24), -1, np.int64)
        M[grp[k], rk[k]] = [G["SI"].get(id2s.get(int(x), "?"), -1) for x in sy[k]]
        T.append(u)
        S.append(M)
        log.info("bins %s: rec %d moc %d", f, len(a), len(u))
    G["T15"], G["TOP"] = np.concatenate(T), np.vstack(S)
    assert np.all(np.diff(G["T15"]) > 0)


def cands(m0):
    """ung vien tai phut m0: top-24 S1 (moc <= t, t - moc <= 15') co close; khong co -> universe co close."""
    c = G["CC"].get(m0)
    if c is not None:
        return c
    t = T0 + m0 * MN
    fi = int(np.searchsorted(G["T15"], t, "right")) - 1
    P = G["P"]
    src = "top24"
    if fi >= 0 and t - G["T15"][fi] <= 15 * MN:
        x = G["TOP"][fi]
        x = x[x >= 0]
        x = x[np.isfinite(P[x, 3, m0]) & (P[x, 3, m0] > 0)] if len(x) else x
    else:
        x = np.array([], np.int64)
    if len(x) == 0:
        src = "universe"
        x = np.flatnonzero(np.isfinite(P[:len(G["SI"]), 3, m0]) & (P[:len(G["SI"]), 3, m0] > 0))
    G["CC"][m0] = x
    G["CSRC"][m0] = src
    return x


def proxy(si, m0):
    """proxy thoat qsleeve_q0.seg: vao close phut m0. Tra (ret_net, gross, crash, why) hoac None (khong close)."""
    key = (int(si), int(m0))
    r = G["RET"].get(key)
    if r is not None:
        return r
    QS = G["QS"]
    P = G["P"]
    c0, o0 = float(P[si, 3, m0]), float(P[si, 0, m0])
    if not (np.isfinite(c0) and c0 > 0):
        G["RET"][key] = None
        return None
    cr = bool(np.isfinite(o0) and o0 > 0 and c0 / o0 - 1.0 <= CRASH)
    st = QS.new_state("x", T0 + m0 * MN)
    st["E"] = c0
    a, step, last_c = m0 + 1, 10082, np.nan
    while a < NW and not st["done"]:
        b = min(NW, a + step)
        X = P[si, :, a:b].astype(np.float64)
        ok = np.all(np.isfinite(X), axis=0) & np.all(X > 0, axis=0)
        ix = np.flatnonzero(ok)
        if len(ix):
            QS.seg(st, X[1, ix], X[2, ix], X[0, ix], X[3, ix], T0 + (a + ix) * MN)
            last_c = X[3, ix[-1]]
        a, step = b, 30000
    px, why = (st["px"], st["why"]) if st["done"] else ((last_c if np.isfinite(last_c) else c0), "mark")
    g = px / c0 - 1.0
    r = (g - COST - (PEN if cr else 0.0), g, cr, why)
    G["RET"][key] = r
    return r


def tick_check():
    """A1(ii): phut-chan thieu gia / gia 0 trong ticker sim khi chan mo (16 run stress, phan trong W)."""
    P, SI = G["P"], G["SI"]
    out = dict(legs=0, legmin=0, miss=0, zero=0, nosym=0, legs_with_miss=0)
    for cfg in ("k24", "b0"):
        for s in SEEDS:
            d = load_pd(tag(cfg, s))
            x = d.loc[(d["te"] >= T0) & (d["ts"] < T1)]
            for sym, ts, te in zip(x["symt"], x["ts"], x["te"]):
                out["legs"] += 1
                si = SI.get(sym)
                if si is None:
                    out["nosym"] += 1
                    continue
                a, b = max(0, (ts - T0) // MN), min(NW, (te - T0) // MN)
                if b <= a:
                    continue
                c = P[si, 3, a:b]
                nn, zz = int(np.isnan(c).sum()), int((c == 0).sum())
                out["legmin"] += b - a
                out["miss"] += nn
                out["zero"] += zz
                out["legs_with_miss"] += int(nn + zz > 0)
    out["miss_pct"] = 100.0 * out["miss"] / max(1, out["legmin"])
    log.info("A1(ii) ticker sim: %s", out)
    return out


def a4_legs():
    """leg0 cua 8 run k24-s co start in W: m0, notional, si that, pnl that; + hieu chuan proxy non-DCA."""
    L, cal, drop = {}, [], dict(nosym=0, noprice=0)
    for s in SEEDS:
        d = load_pd(tag("k24", s))
        x = d.loc[d["leg0"] & (d["ts"] >= T0) & (d["ts"] < T1)]
        rows = []
        for r in x.itertuples(index=False):
            si = G["SI"].get(r.symt)
            m0 = int((r.ts - T0) // MN)
            if si is None:
                drop["nosym"] += 1
                continue
            pr = proxy(si, m0)
            if pr is None:
                drop["noprice"] += 1
                continue
            rows.append((m0, float(r.margin), si, pr[0]))
            if r.nleg == 1 and r.te < T1 and np.isfinite(r.profit):
                cal.append((pr[1] - (PEN if pr[2] else 0.0), r.profit / 100.0, pr[3], r.level))
        L[s] = np.array(rows, dtype=[("m0", np.int64), ("notional", float), ("si", np.int64), ("ret", float)])
    cal = pd.DataFrame(cal, columns=["proxy", "real", "why", "level"])
    cs = dict(n=len(cal), pearson=float(np.corrcoef(cal["proxy"], cal["real"])[0, 1]) if len(cal) > 2 else None,
              bias_pp=100 * float((cal["proxy"] - cal["real"]).mean()) if len(cal) else None,
              mad_pp=100 * float((cal["proxy"] - cal["real"]).abs().median()) if len(cal) else None,
              why=cal["why"].value_counts().to_dict())
    log.info("A4 legs: %s, drop %s, hieu chuan non-DCA %s", {s: len(v) for s, v in L.items()}, drop, cs)
    return L, drop, cs


def draw_pnl(rng, mins, notionals):
    """1 lan doi chung: moi leg o phut mins[i] rut coin deu tu cands (khong lap trong cung phut). Tra Sum PnL."""
    tot = 0.0
    order = np.argsort(mins, kind="mergesort")
    mins, notionals = mins[order], notionals[order]
    u, st = np.unique(mins, return_index=True)
    en = np.append(st[1:], len(mins))
    for m0, a, b in zip(u.tolist(), st.tolist(), en.tolist()):
        c = cands(m0)
        g = b - a
        for tries in range(50):
            pick = c[rng.integers(len(c))] if g == 1 else rng.choice(c, g, replace=len(c) < g)
            pick = np.atleast_1d(pick)
            rs = [proxy(int(si), m0) for si in pick]
            if all(r is not None for r in rs):
                break
        tot += sum(n * (r[0] if r is not None else 0.0) for n, r in zip(notionals[a:b], rs))
    return tot


def pval(real, ctrl):
    ctrl = np.asarray(ctrl)
    return float((1 + (ctrl >= real).sum()) / (1 + len(ctrl)))


def stage_a4():
    import qsleeve_q0 as QS
    G.update(QS=QS, RET={}, CC={}, CSRC={})
    tk = load_ticker()
    load_top24()
    tchk = tick_check()
    L, drop, cal = a4_legs()
    rng = np.random.default_rng(RSEED)
    pool = rng.integers(0, NW, POOL)
    real = {s: float((L[s]["notional"] * L[s]["ret"]).sum()) for s in SEEDS}
    S_real = sum(real.values())
    C1 = np.zeros((NREP4, len(SEEDS)))
    C2 = np.zeros((NREP4, len(SEEDS)))
    t0 = time.time()
    for k in range(NREP4):
        for j, s in enumerate(SEEDS):
            x = L[s]
            C1[k, j] = draw_pnl(rng, x["m0"].copy(), x["notional"].copy())
            C2[k, j] = draw_pnl(rng, pool[rng.integers(0, POOL, len(x))], rng.permutation(x["notional"]))
        if k % 100 == 0:
            log.info("A4 rep %d/%d %.0fs cache %d", k, NREP4, time.time() - t0, len(G["RET"]))
    c1, c2 = C1.sum(axis=1), C2.sum(axis=1)
    src = pd.Series(G["CSRC"]).value_counts().to_dict()
    sim_pnl = {s: wsum(load_pd(tag("k24", s))) for s in SEEDS}
    why = pd.Series([G["RET"][(int(a), int(b))][3] for s in SEEDS for a, b in zip(L[s]["si"], L[s]["m0"])])
    res = dict(ticker=tk, tick_check=tchk, legs={s: len(L[s]) for s in SEEDS}, drop=drop, calib=cal,
               cand_src=src, n_proxy=len(G["RET"]), real_proxy=real, S_real=S_real, sim_sum_pnl_S=sim_pnl,
               real_why=why.value_counts().to_dict(),
               C1=dict(mean=float(c1.mean()), sd=float(c1.std()), p=pval(S_real, c1),
                       q=[float(v) for v in np.percentile(c1, [5, 50, 95])],
                       p_seed={s: pval(real[s], C1[:, j]) for j, s in enumerate(SEEDS)}),
               C2=dict(mean=float(c2.mean()), sd=float(c2.std()), p=pval(S_real, c2),
                       q=[float(v) for v in np.percentile(c2, [5, 50, 95])],
                       p_seed={s: pval(real[s], C2[:, j]) for j, s in enumerate(SEEDS)}))
    res["decomp"] = dict(beta=res["C2"]["mean"], timing=res["C1"]["mean"] - res["C2"]["mean"],
                         selection=S_real - res["C1"]["mean"], total=S_real)
    log.info("A4 S_real %.0f | C1 mean %.0f p %.4f | C2 mean %.0f p %.4f | decomp %s", S_real, c1.mean(),
             res["C1"]["p"], c2.mean(), res["C2"]["p"], res["decomp"])
    np.savez(WD + "/a4_dist.npz", C1=C1, C2=C2)
    save("a4", res)


def stage_a5():
    st = {}
    tsv = WD + "/queue_status.tsv"
    if os.path.exists(tsv):
        for ln in open(tsv).read().splitlines()[1:]:
            f = ln.split("\t")
            st[f[0]] = dict(status=f[1], md5=f[2], n=f[3], parity=f[4])
    res = dict(per_seed={}, missing=[])
    for s in SEEDS:
        t = "aud26-k24-p267-s%d" % s
        q = st.get(t, {})
        if q.get("parity") != "PASS" or not os.path.exists(OUT + t + "/storage/printDone.csv"):
            res["missing"].append(t)
            continue
        rj = json.load(open(OUT + t + "/result.json"))
        row = {}
        for nm, tt in (("p267", t), ("p1675", tag("k24", s)), ("base", tag("k24", s, "b"))):
            d = load_pd(tt)
            r = json.load(open(OUT + tt + "/result.json"))
            e0 = float(r["equity_start"]) + float(d.loc[d["te"] < T0, "pnl"].sum())
            sp = wsum(d)
            row[nm] = dict(sum_pnl=sp, n=int(((d["ts"] >= T0) & (d["ts"] < T1)).sum()), e0_real=e0,
                           roi_real=100 * sp / e0)
        row["pen_ov"] = (rj.get("overrides") or {}).get("SIM_CRASH_ENTRY_PENALTY")
        res["per_seed"][s] = row
    ok = list(res["per_seed"])
    if ok:
        for nm in ("p267", "p1675", "base"):
            res[nm] = summ([res["per_seed"][s][nm]["sum_pnl"] for s in ok])
            res[nm + "_roi"] = summ([res["per_seed"][s][nm]["roi_real"] for s in ok])
        res["delta_vs_1675"] = summ([res["per_seed"][s]["p267"]["sum_pnl"] - res["per_seed"][s]["p1675"]["sum_pnl"]
                                     for s in ok])
    log.info("A5: seeds ok %s missing %s p267 %s", ok, res["missing"], res.get("p267"))
    save("a5", res)


def s3_prefixes(prefix):
    out, marker = [], ""
    while True:
        b = http(S3 + "?prefix=%s&delimiter=/&marker=%s" % (prefix, marker)).decode()
        ps = [p for p in re.findall(r"<Prefix>([^<]+)</Prefix>", b) if p != prefix]
        out += ps
        nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", b)
        if "<IsTruncated>true</IsTruncated>" not in b or not ps:
            return out
        marker = nm.group(1) if nm else ps[-1]


def ym_range(a, b):
    return [x.strftime("%Y-%m") for x in pd.period_range(a, b, freq="M")]


def risk_stats(r):
    """r: Series return gio, index = open_time ms UTC. -> thong ke theo thang (+07) va nua nam."""
    loc = pd.to_datetime(r.index.to_numpy() + TZ, unit="ms")
    df = pd.DataFrame(dict(r=r.to_numpy(), mon=loc.strftime("%Y-%m"), day=loc.strftime("%Y-%m-%d"),
                           hy=[("%dH%d" % (y, 1 if m <= 6 else 2)) for y, m in zip(loc.year, loc.month)]))
    df = df[df["mon"] <= "2026-06"]
    ch = np.flatnonzero(df["r"].to_numpy() <= -0.03)
    tms = r.index.to_numpy()[df.index.to_numpy()][ch] if len(ch) else np.array([], np.int64)
    ep_start = set()
    for i, t in enumerate(tms):
        if i == 0 or t - tms[i - 1] >= 24 * H:
            ep_start.add(int(t))
    df["ep"] = [int(t) in ep_start for t in r.index.to_numpy()[df.index.to_numpy()]]
    out = {}
    for key in ("mon", "hy"):
        out[key] = {}
        for k, g in df.groupby(key):
            lv = np.cumprod(1.0 + g["r"].to_numpy())
            dd = lv / np.maximum.accumulate(np.concatenate([[1.0], lv]))[1:] - 1.0
            dly = g.groupby("day")["r"].apply(lambda x: float(np.prod(1.0 + x) - 1.0))
            out[key][k] = dict(ret=100 * float(lv[-1] - 1), maxdd=100 * float(dd.min()), n_days=int(len(dly)),
                               days_le5=int((dly <= -0.05).sum()), crash_h=int((g["r"] <= -0.03).sum()),
                               episodes=int(g["ep"].sum()))
    return out


def stage_a6():
    pre = "data/futures/um/monthly/klines/"
    syms = [p[len(pre):].strip("/") for p in s3_prefixes(pre)]
    syms = sorted(s for s in syms if re.fullmatch(r"[A-Z0-9]+USDT", s) and s not in STABLE)
    log.info("A6: %d symbol USDT-perp (Vision monthly)", len(syms))
    rk_months = ym_range("2021-12", "2026-05")
    jobs = [(s, m) for s in syms for m in rk_months]

    def qv(job):
        s, m = job
        df = kl(VIS + "monthly/klines/%s/1d/%s-1d-%s.zip" % (s, s, m))
        return float(df["qv"].sum()) if df is not None and len(df) else np.nan
    with ThreadPoolExecutor(24) as ex:
        V = list(ex.map(qv, jobs))
    QV = pd.Series(V, index=pd.MultiIndex.from_tuples(jobs)).unstack()      # sym x month
    months = ym_range("2022-01", "2026-06")
    top = {}
    for m in months:
        prev = str(pd.Period(m, "M") - 1)
        top[m] = QV[prev].dropna().sort_values(ascending=False).index[:50].tolist()
    need = sorted({(s, m) for m in months for s in top[m]} | {(s, m) for s in ("BTCUSDT", "ETHUSDT") for m in months})
    log.info("A6: tai %d file 1h", len(need))
    with ThreadPoolExecutor(16) as ex:
        HH = dict(zip(need, ex.map(lambda k: kl(VIS + "monthly/klines/%s/1h/%s-1h-%s.zip" % (k[0], k[0], k[1])), need)))
    n404 = [k for k, v in HH.items() if v is None]
    grid = np.arange(int(pd.Timestamp("2022-01-01").value // 10 ** 6), int(pd.Timestamp("2026-07-01").value // 10 ** 6), H)
    us = sorted({s for s, _ in need})
    C = pd.DataFrame(np.nan, index=grid, columns=us)
    for (s, m), df in HH.items():
        if df is None or not len(df):
            continue
        x = df.drop_duplicates("ot").set_index("ot")["c"]
        x = x[x.index.isin(grid)]
        C.loc[x.index, s] = x.to_numpy()
    R = C / C.shift(1) - 1.0
    R[(C <= 0) | (C.shift(1) <= 0)] = np.nan
    mon_utc = pd.to_datetime(grid, unit="ms").strftime("%Y-%m")
    mask = pd.DataFrame(False, index=grid, columns=us)
    for m in months:
        rows = mon_utc == m
        mask.loc[rows, [s for s in top[m] if s in us]] = True
    ew = R.where(mask).mean(axis=1, skipna=True)
    nmem = R.where(mask).notna().sum(axis=1)
    series = {"BTC": R["BTCUSDT"], "ETH": R["ETHUSDT"], "EW50": ew}
    res = dict(n_syms=len(syms), n_1h_files=len(need), n_1h_404=len(n404), members_per_hour=summ(nmem.to_numpy()),
               top50_2026_06=top["2026-06"][:10], stats={})
    for nm, r in series.items():
        r = r.dropna()
        res["stats"][nm] = risk_stats(r)
    hys = ["%dH%d" % (y, h) for y in (2022, 2023, 2024, 2025) for h in (1, 2)]
    res["compare"] = {}
    for nm in series:
        hy = res["stats"][nm]["hy"]
        cmp_ = {}
        for f in ("ret", "maxdd", "days_le5", "crash_h", "episodes"):
            dev = [hy[h][f] for h in hys if h in hy]
            v = hy.get("2026H1", {}).get(f)
            dens = lambda h: 30.0 * hy[h][f] / hy[h]["n_days"]  # noqa: E731
            cmp_[f] = dict(h2026=v, dev_mean=float(np.mean(dev)), dev_min=float(np.min(dev)), dev_max=float(np.max(dev)),
                           rank_desc=int(1 + sum(1 for x in dev if x > v)) if v is not None else None, n_dev=len(dev),
                           per30_2026=dens("2026H1") if "2026H1" in hy and f in ("days_le5", "crash_h", "episodes") else None,
                           per30_dev=float(np.mean([dens(h) for h in hys if h in hy]))
                           if f in ("days_le5", "crash_h", "episodes") else None)
        res["compare"][nm] = cmp_
        log.info("A6 %s 2026H1: %s", nm, {f: (round(c["h2026"], 2) if c["h2026"] is not None else None,
                                               round(c["dev_mean"], 2), c["rank_desc"]) for f, c in cmp_.items()})
    save("a6", res)


def f0(x):
    return "—" if x is None else "{:,.0f}".format(x).replace(",", " ")


def f2(x, nd=2):
    return "—" if x is None else ("{:.%df}" % nd).format(x).replace(".", ",")


def tbl(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def stage_report():
    J = {k: json.load(open(WD + "/%s.json" % k)) for k in ("a1", "a1x", "a2", "a3", "a4", "a5", "a6") if
         os.path.exists(WD + "/%s.json" % k)}
    J["prereg_commit"] = "09969df9"
    json.dump(J, open(JSON_OUT, "w"), indent=1, ensure_ascii=False)
    L = ["", "## PHẦN 2 — KẾT QUẢ (sinh bởi `ho26_luck_audit.py report`)", ""]
    if "a1" in J:
        a = J["a1"]
        L += ["### A1 — kiểm giá độc lập (Vision)", ""]
        rows = []
        for cfg, c in a["cfg"].items():
            rows.append([cfg, c["n_entry"], f2(c["entry_pct"]["0"]), c["entry"]["0"]["bad"], c["entry"]["0"]["nosrc"],
                         f2(c["entry_pct"]["-1"]) + " / " + f2(c["entry_pct"]["1"]), c["n_exit"], f2(c["exit_pct"]["0"]),
                         c["exit"]["0"]["bad"], json.dumps(c["crash_flag"])])
        L += tbl(["cfg s42", "chân vào", "% khớp vào (lag0)", "lệch", "không nguồn", "lag −1/+1 %", "chân thoát",
                  "% thoát ∈ [L,H]", "lệch", "cờ sập Vision×sim"], rows)
        L += ["", "Vision: %s. Ticker sim (16 run): %s. Delist trong W: %s; list mới trong W: %d symbol." % (
            json.dumps(a["vision"]), json.dumps(J.get("a4", {}).get("tick_check")),
            [d["sym"] + ":" + str(d["last"]) for d in a["delist"]["delisted_in_W"]], len(a["delist"]["listed_in_W"])), ""]
    if "a2" in J:
        S = J["a2"]["summary"]
        L += ["### A2 — phụ thuộc vài sự kiện (ΣPnL_S, 8 seed; mean [min] · số seed > 0)", ""]
        rows = []
        for k in S["k24"]:
            if k == "june_share":
                continue
            rows.append([k] + ["%s [%s] · %d/8" % (f0(S[c][k]["mean"]), f0(S[c][k]["min"]), S[c][k]["n_pos"])
                               for c in ("k24", "b0")] + ["%s · %d/8" % (f0(S["delta"][k]["mean"]), S["delta"][k]["n_pos"])])
        L += tbl(["phép bỏ", "k24", "b0", "Δ k24−b0"], rows)
        L += ["", "Tỉ trọng tháng 6: k24 mean %s [%s..%s]; b0 mean %s." % (
            f2(S["k24"]["june_share"]["mean"]), f2(S["k24"]["june_share"]["min"]), f2(S["k24"]["june_share"]["max"]),
            f2(S["b0"]["june_share"]["mean"])), ""]
    if "a3" in J:
        B = J["a3"]["boot"]
        L += ["### A3 — block bootstrap return ngày MTM (NREP 5000, seed 20261010)", ""]
        rows = []
        for b in ("5", "10"):
            for cfg in ("k24", "b0"):
                p = B[b][cfg]["pool"]
                ps = [B[b][cfg][str(s)]["p_le0"] for s in SEEDS]
                rows.append([b, cfg, f2(p["p_le0"], 4), "%s … %s" % (f2(p["ci95_roi"][0]), f2(p["ci95_roi"][1])),
                             "%s … %s" % (f2(p["ci95_roi_infl"][0]), f2(p["ci95_roi_infl"][1])),
                             "%s … %s" % (f0(p["ci95_pnl"][0]), f0(p["ci95_pnl"][1])),
                             "%s [%s..%s]" % (f2(np.mean(ps), 3), f2(min(ps), 3), f2(max(ps), 3))])
        L += tbl(["block", "cfg", "GỘP P(ROI≤0)", "CI95 ROI %", "CI95 inflate", "CI95 ΣPnL USD", "P(ROI≤0) từng seed mean [min..max]"], rows)
        L += ["", "Tự kiểm ROI tái lập vs RESULT_A: max |rel| %.1e." % J["a3"]["selfcheck_roi_max_rel"], ""]
    if "a4" in J:
        a = J["a4"]
        L += ["### A4 — đối chứng ngẫu nhiên (proxy thoát non-DCA, 1000 lần, ΣPnL USD gộp 8 seed)", ""]
        L += tbl(["", "giá trị", "p một phía", "p5 / p50 / p95"],
                 [["S_real (coin thật, proxy)", f0(a["S_real"]), "", ""],
                  ["C1 cùng phút, coin ngẫu nhiên", f0(a["C1"]["mean"]), f2(a["C1"]["p"], 4), " / ".join(f0(v) for v in a["C1"]["q"])],
                  ["C2 phút ngẫu nhiên", f0(a["C2"]["mean"]), f2(a["C2"]["p"], 4), " / ".join(f0(v) for v in a["C2"]["q"])]])
        d = a["decomp"]
        L += ["", "Phân rã: beta (C2) %s · thời điểm (C1−C2) %s · chọn coin (thật−C1) %s. p từng seed C1 %s; C2 %s." % (
            f0(d["beta"]), f0(d["timing"]), f0(d["selection"]), [f2(v, 3) for v in a["C1"]["p_seed"].values()],
            [f2(v, 3) for v in a["C2"]["p_seed"].values()]),
            "leg0/seed %s; bỏ %s; nguồn ứng viên %s; thoát proxy coin thật %s. ΣPnL_S sim thật (có DCA) %s." % (
            list(a["legs"].values()), a["drop"], a["cand_src"], a["real_why"], [f0(v) for v in a["sim_sum_pnl_S"].values()]),
            "Hiệu chuẩn proxy 2026 (leg0 không-DCA k24-s): n %d, pearson %s, lệch TB %s pp, |lệch| p50 %s pp." % (
            a["calib"]["n"], f2(a["calib"]["pearson"], 3), f2(a["calib"]["bias_pp"]), f2(a["calib"]["mad_pp"])), ""]
    if "a5" in J and J["a5"].get("p267"):
        a = J["a5"]
        rows = [[s, f0(v["p267"]["sum_pnl"]), f0(v["p1675"]["sum_pnl"]), f0(v["base"]["sum_pnl"]), v["p267"]["n"],
                 f2(v["p267"]["roi_real"])] for s, v in a["per_seed"].items()]
        L += ["### A5 — độ nhạy phí in-sim (penalty 2,67%)", ""]
        L += tbl(["seed", "ΣPnL_S @2,67%", "@1,675%", "phí gốc", "n @2,67%", "ROI realized % @2,67%"], rows)
        L += ["", "@2,67%%: mean %s [%s..%s], %d/%d seed > 0; Δ vs 1,675%% mean %s; thiếu %s." % (
            f0(a["p267"]["mean"]), f0(a["p267"]["min"]), f0(a["p267"]["max"]), a["p267"]["n_pos"], a["p267"]["n"],
            f0(a["delta_vs_1675"]["mean"]), a["missing"]), ""]
    if "a6" in J:
        a = J["a6"]
        L += ["### A6 — bối cảnh thị trường (Vision 1h; 2026H1 vs 8 nửa năm DEV 2022H1–2025H2)", ""]
        rows = []
        for nm, c in a["compare"].items():
            for f, v in c.items():
                rows.append([nm, f, f2(v["h2026"]), "%s [%s..%s]" % (f2(v["dev_mean"]), f2(v["dev_min"]), f2(v["dev_max"])),
                             "%s/9" % v["rank_desc"], f2(v["per30_2026"]) + " vs " + f2(v["per30_dev"])
                             if v["per30_2026"] is not None else ""])
        L += tbl(["chuỗi", "chỉ số", "2026H1", "DEV mean [min..max]", "hạng (giảm dần)", "mật độ /30 ngày 2026 vs DEV"], rows)
        L += ["", "Theo tháng 2026 (EW50: ret % / maxDD % / ngày ≤−5% / đợt sập): " + "; ".join(
            "%s %s/%s/%d/%d" % (m[5:], f2(v["ret"], 1), f2(v["maxdd"], 1), v["days_le5"], v["episodes"])
            for m, v in a["stats"]["EW50"]["mon"].items() if m >= "2026-01"),
            "BTC theo tháng 2026 ret %: " + ", ".join("%s %s" % (m[5:], f2(v["ret"], 1))
                                                       for m, v in a["stats"]["BTC"]["mon"].items() if m >= "2026-01"),
            "Thành phần/giờ EW50: %s; file 1h %d (404: %d)." % (json.dumps({k: round(v, 1) for k, v in
                                                                           a["members_per_hour"].items()}),
                                                                 a["n_1h_files"], a["n_1h_404"]), ""]
    open(WD + "/part2.md", "w").write("\n".join(L) + "\n")
    log.info("ghi %s + %s/part2.md", JSON_OUT, WD)


def stage_a1x():
    """BO SUNG SAU KHI THAY A1 (KHONG pre-reg, chi mo ta, khong vao luat A7): lech gia vao vs Vision tren 16 run
    stress + tac dong PnL bac 1 (gia vao -> Vision, giu notional/gia thoat) + ticker sim vs Vision o phut lech."""
    L = {(c, s): load_pd(tag(c, s)) for c in ("k24", "b0") for s in SEEDS}
    need = set()
    for d in L.values():
        x = d.loc[(d["ts"] >= T0) & (d["ts"] < T1)]
        need |= {(s, time.strftime("%Y-%m-%d", time.gmtime(t / 1000))) for s, t in zip(x["symt"], x["ts"])}
    need = sorted(need)
    with ThreadPoolExecutor(8) as ex:
        got = dict(zip(need, ex.map(lambda k: vday(*k), need)))
    K = {}
    for (s, _), df in got.items():
        if df is not None:
            for r in df.itertuples(index=False):
                K[(s, int(r.ot))] = (r.o, r.h, r.l, r.c)
    res = dict(files=len(need), n404=sum(v is None for v in got.values()), runs={})
    uniq = {}
    for (c, s), d in L.items():
        e = d.loc[(d["ts"] >= T0) & (d["ts"] < T1)].copy()
        ev = []
        for r in e.itertuples(index=False):
            k = K.get((r.symt, int(r.ts)))
            if k is None:
                ev.append(np.nan)
                continue
            cr = k[0] > 0 and k[3] / k[0] - 1.0 <= CRASH
            ev.append(k[3] * (1 + PEN) if cr else k[3])
        e["ev"] = ev
        e["rel"] = e["entry"] / e["ev"] - 1.0
        e["bad"] = e["rel"].abs() > TOL
        for r in e.itertuples(index=False):
            uniq[(r.symt, int(r.ts))] = (bool(r.bad), float(r.rel), float(r.entry), float(r.ev), r.level)
        x = e.loc[(e["te"] >= T0) & (e["te"] < T1) & e["ev"].notna()]
        dp = (x["margin"] * x["tp"] * (1.0 / x["ev"] - 1.0 / x["entry"])).to_numpy()
        tot = wsum(d)
        b = e.loc[e["bad"]]
        res["runs"]["%s|%d" % (c, s)] = dict(n=len(e), bad=int(e["bad"].sum()), pct=100 * float(1 - e["bad"].mean()),
                                             sum_pnl=tot, dpnl_vision=float(dp.sum()), sum_pnl_vision=tot + float(dp.sum()),
                                             bad_rel_mean=float(b["rel"].mean()) if len(b) else None,
                                             bad_june=int((b["ts"] >= int(pd.Timestamp("2026-06-01").value // 10 ** 6) - TZ).sum()))
    U = pd.DataFrame([(k[0], k[1], *v) for k, v in uniq.items()], columns=["sym", "ts", "bad", "rel", "entry", "ev", "level"])
    B = U[U["bad"]].copy()
    B["min"] = pd.to_datetime(B["ts"] + TZ, unit="ms").dt.strftime("%Y-%m-%d %H:%M")
    res["uniq"] = dict(n=len(U), bad=len(B), pct=100 * float(1 - U["bad"].mean()),
                       rel_mean=float(B["rel"].mean()), rel_med=float(B["rel"].median()),
                       n_pos=int((B["rel"] > 0).sum()), n_neg=int((B["rel"] < 0).sum()),
                       by_level=B["level"].value_counts().to_dict(), top_minutes=B["min"].value_counts().head(12).to_dict(),
                       n_minutes=int(B["min"].nunique()))
    for k in ("k24", "b0"):
        rr = [res["runs"]["%s|%d" % (k, s)] for s in SEEDS]
        res[k] = dict(match=summ([r["pct"] for r in rr]), sum_pnl=summ([r["sum_pnl"] for r in rr]),
                      sum_pnl_vision=summ([r["sum_pnl_vision"] for r in rr]), dpnl=summ([r["dpnl_vision"] for r in rr]))
        log.info("A1x %s: %s", k, json.dumps(res[k]))
    log.info("A1x uniq: %s", json.dumps(res["uniq"]))
    days = sorted({time.strftime("%Y%m%d", time.gmtime(t / 1000)) for t in B["ts"]})
    syms = set(B["sym"])
    tk = dict(n_cmp=0, eq_entry=0, n_min=0, diff_min=0, by_day={})
    for day in days:
        _, ss, A = parse_day(day)
        if ss is None:
            continue
        si = {s: i for i, s in enumerate(ss)}
        U0 = int(pd.Timestamp(day).value // 10 ** 6)
        for r in B[B["ts"] // D * D == U0].itertuples(index=False):
            if r.sym in si:
                tk["n_cmp"] += 1
                c = float(A[si[r.sym], 3, (r.ts - U0) // MN])
                cr = float(A[si[r.sym], 0, (r.ts - U0) // MN])
                exp = c * (1 + PEN) if (cr > 0 and c / cr - 1 <= CRASH) else c
                tk["eq_entry"] += int(abs(r.entry / exp - 1) <= TOL)
        dd = dm = 0
        for s in syms:
            if s not in si:
                continue
            for j in range(1440):
                k = K.get((s, U0 + j * MN))
                c = A[si[s], 3, j]
                if k is None or not np.isfinite(c):
                    continue
                dm += 1
                dd += int(abs(c / k[3] - 1) > TOL)
        tk["by_day"][day] = dict(min=dm, diff=dd)
        tk["n_min"] += dm
        tk["diff_min"] += dd
    res["ticker_vs_vision"] = tk
    log.info("A1x ticker sim vs Vision: %s", json.dumps(tk))
    save("a1x", res)


def main():
    os.makedirs(WD, exist_ok=True)
    st = sys.argv[1] if len(sys.argv) > 1 else "report"
    fn = dict(a1x=stage_a1x, a1=stage_a1, a2=stage_a2, a3=stage_a3, a4=stage_a4, a5=stage_a5, a6=stage_a6, report=stage_report)[st]
    if st == "a4":
        take_lock("a4 ticker ~3.5G RAM")
        try:
            fn()
        finally:
            drop_lock()
    else:
        fn()


if __name__ == "__main__":
    main()
