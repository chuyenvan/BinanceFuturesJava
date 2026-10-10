#!/usr/bin/env python3
"""KDIV — lech kline 1m Aerospike 242 (`ticker.kline_1m_opt`) vs Binance Vision / REST fapi. CHI DOC 242.
Pre-reg: docs/prereg/PREREG_KLINE_242_DIV.md (b41bbf81). Bao cao: docs/audit/KLINE_242_DIVERGENCE.md.
Stage:
  syms                         -> mau symbol (top50 242 2026-03-10..16 U symbol HO26 s42)
  d1 --lo YYYYMMDD --hi YYYYMMDD  (+07, hi khong gom) -> kdiv_d1/<utcday>.json + .npz (chuoi phut)
  d2                           -> REST fapi/v1/klines vs Vision vs 242 tren mau (symbol, ngay)
  dev                          -> ticker DEV 2025 (kaggle_data_hpo) vs Vision
  gate --arm 242|vis --lo --hi -> 33 feature gate (port devexport) -> p15 ONNX fold_20
  gatecmp                      -> D4a: PASS 242 vs Vision
  report                       -> docs/audit/KLINE_242_DIVERGENCE.json
Chi doc Aerospike (operate = read + expression_read). Khong ghi gi len 242.
"""
import argparse, datetime, glob, gzip, io, json, logging, os, random, sys, time, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import devexport_202609 as dx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kdiv")
WD = "/home/ubuntu/claude_master/1003/kdiv"
REPO = "/home/ubuntu/src/BinanceFuturesJava"
OUTK = "/home/ubuntu/kaggle_sim/out/"
TDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
VIS = "https://data.binance.vision/data/futures/um/"
REST = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=1m&startTime=%d&limit=1500"
MN, H, D = 60000, 3600000, 86400000
TZ = 7 * H
TZ7 = dx.TZ7
F5 = ["open", "high", "low", "close", "quoteVolume"]
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT"}
VB = [0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, np.inf]            # bac bien dong (H-L)/O Vision
OB = [-np.inf, -30, 0, 2, 5, 10, 20, 60, 86400, np.inf]             # bac LUT - (phut+60s), giay
RB = [-np.inf, 1e-12, 0.1, 0.5, 0.9, 0.99, 1.01, np.inf]            # bac Q242/QV
HB = np.linspace(-9, 1, 1001)                                     # log10 |a/b-1|
FLAGS = ["vol0", "openeq_vollow", "inside", "close_only", "shift", "o_eq", "c_eq"]
ERR = {"http": 0, "as": 0}


def k7(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, TZ7).strftime("%Y%m%d-%H%M")


def d7(s):
    return int(datetime.datetime.strptime(s, "%Y%m%d").replace(tzinfo=TZ7).timestamp() * 1000)


def utcs(ms, f="%Y-%m-%d"):
    return datetime.datetime.utcfromtimestamp(ms / 1000).strftime(f)


def http(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log.warning("http %s %s", e.code, url)
            time.sleep(3 + 5 * i)
        except Exception as e:
            log.warning("http err %s %s", e, url)
            time.sleep(3 + 5 * i)
    ERR["http"] += 1
    log.error("http FAIL %s", url)
    return None


def vis_zip(url):
    """-> (mi ms int64, v float64 (n,7) o,h,l,c,qv,vol,trades) hoac None (404/loi)."""
    b = http(url)
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    df = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
    df = df[df[0].str.isdigit()]
    mi = df[0].astype(np.int64).to_numpy() // MN * MN
    v = df[[1, 2, 3, 4, 7, 5, 8]].astype(np.float64).to_numpy()
    o = np.argsort(mi, kind="mergesort")
    return mi[o], v[o]


def vis_month(sym, ym):
    return vis_zip(VIS + "monthly/klines/%s/1m/%s-1m-%s.zip" % (sym, sym, ym))


def vis_day(sym, day):
    return vis_zip(VIS + "daily/klines/%s/1m/%s-1m-%s.zip" % (sym, sym, day))


def vis_dense(vm, day_ms, pad=1):
    """vm=(mi,v) -> (1440+2pad, 7) NaN neu thieu; hang i <-> phut day_ms+(i-pad)*MN."""
    out = np.full((1440 + 2 * pad, 7 if vm is None else vm[1].shape[1]), np.nan)
    if vm is None:
        return out
    mi, v = vm
    lo, hi = np.searchsorted(mi, [day_ms - pad * MN, day_ms + D + pad * MN])
    idx = (mi[lo:hi] - day_ms) // MN + pad
    out[idx] = v[lo:hi]
    return out


def as_store():
    st = dx.Store("242", pool=40)
    return st


def fetch242(st, ms_list):
    """-> list (ms, data|None|'ERR', gen, lut_ns). CHI DOC: operate gom read + expression_read."""
    import aerospike
    from aerospike_helpers import expressions as exp
    from aerospike_helpers.operations import expression_operations as eo, operations as op
    ops = [op.read("data"), eo.expression_read("lut", exp.LastUpdateTime().compile())]

    def one(ms):
        key = ("ticker", "kline_1m_opt", k7(ms))
        err = None
        for i in range(3):
            try:
                _, meta, b = st.client.operate(key, ops)
                return ms, b.get("data"), int(meta.get("gen", 0)), int(b.get("lut") or 0)
            except aerospike.exception.RecordNotFound:
                return ms, None, 0, 0
            except Exception as e:
                err = e
                time.sleep(1 + i)
        ERR["as"] += 1
        log.warning("as err %s %s", k7(ms), err)
        return ms, "ERR", 0, 0
    return list(st.pool.map(one, ms_list))


def dense242(rows, day_ms, syms):
    """rows tu fetch242 cho 1 ngay UTC -> ({sym: (1440,5) f32 NaN}, gen, lut, nsym)."""
    A = {}
    gen = np.zeros(1440, np.int32)
    lut = np.zeros(1440, np.int64)
    nsym = np.zeros(1440, np.int16)
    for ms, data, g, l in rows:
        i = (ms - day_ms) // MN
        gen[i] = g
        lut[i] = l
        if data is None or isinstance(data, str):
            nsym[i] = -1 if isinstance(data, str) else 0
            continue
        s2, a2 = dx.parse_minute(data)
        nsym[i] = len(s2)
        for j, s in enumerate(s2):
            if syms is None or s in syms:
                x = A.get(s)
                if x is None:
                    x = A[s] = np.full((1440, 5), np.nan, np.float32)
                x[i] = a2[j]
    return A, gen, lut, nsym


def feq(a, b):
    """a float32, b float64 -> khop float32 (==, hoac |a-b|<=1e-8|b|)."""
    b32 = b.astype(np.float32)
    a64, b64 = a.astype(np.float64), b32.astype(np.float64)
    return (a == b32) | (np.abs(a64 - b64) <= 1e-8 * np.abs(b64))


def load_pd(tag):
    d = pd.read_csv(OUTK + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    d["sym"] = d["sym"].astype(str).str.strip()
    for c in ("start", "end"):
        t = pd.to_datetime(d[c].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
        d[c + "_ms"] = t.values.astype("datetime64[ms]").astype(np.int64) - TZ
    return d


def stage_syms():
    st = as_store()
    t0, t1 = d7("20260310"), d7("20260317")
    rows = fetch242(st, list(range(t0, t1, 10 * MN)))
    tot = {}
    for ms, data, g, l in rows:
        if data is None or isinstance(data, str):
            continue
        s2, a2 = dx.parse_minute(data)
        for j, s in enumerate(s2):
            tot[s] = tot.get(s, 0.0) + float(a2[j, 4])
    st.close()
    top = [s for s, _ in sorted(tot.items(), key=lambda x: -x[1]) if s not in STABLE][:50]
    w0, w1 = d7("20260101"), d7("20260701")
    ho = set()
    for tg in ("ho26-k24-s-s42", "ho26-b0-s-s42"):
        d = load_pd(tg)
        d = d[(d["start_ms"] >= w0) & (d["start_ms"] < w1)]
        ho |= set(s + "USDT" for s in d["sym"])
    out = dict(top50=top, ho26=sorted(ho), all=sorted(set(top) | ho), n_keys=len(rows))
    json.dump(out, open(WD + "/kdiv_syms.json", "w"), indent=1)
    log.info("syms top50=%d ho26=%d all=%d", len(top), len(ho), len(out["all"]))


def bc(x, n=7):
    return np.bincount(np.asarray(x, np.int64), minlength=n)[:n]


def cmp_day(A, VD, day_ms, legs):
    """So 242 (A) vs Vision (VD) cho 1 ngay UTC. Nua 0 = phut [0,1020) (ngay +07 = ngay UTC), nua 1 = [1020,1440)."""
    acc = {h: dict(n=0, mis=0, misf=np.zeros(5, np.int64), a_only=0, v_only=0, flags=np.zeros(len(FLAGS), np.int64),
                   vbn=np.zeros(7, np.int64), vbm=np.zeros(7, np.int64), rb=np.zeros(7, np.int64)) for h in (0, 1)}
    hist = np.zeros((5, 1000), np.int64)
    mser = np.zeros((1440, 7), np.int32)          # nboth, nmis_any, mis o,h,l,c,q
    persym, lg = {}, np.zeros(4, np.int64)        # legs: vao co o, vao lech close, thoat co o, thoat lech bat ky
    empty = np.full((1442, 7), np.nan)
    for s in sorted(set(A) | set(VD)):
        a = A.get(s)
        vv = VD.get(s, empty)
        ha = ~np.isnan(a[:, 0]) if a is not None else np.zeros(1440, bool)
        V = vv[1:1441]
        hv = ~np.isnan(V[:, 0])
        for h, c in enumerate(bc(np.nonzero(ha & ~hv)[0] >= 1020, 2)):
            acc[h]["a_only"] += int(c)
        for h, c in enumerate(bc(np.nonzero(hv & ~ha)[0] >= 1020, 2)):
            acc[h]["v_only"] += int(c)
        idx = np.nonzero(ha & hv)[0]
        if len(idx) == 0:
            continue
        X, Y = a[idx], V[idx]
        E = np.stack([feq(X[:, k], Y[:, k]) for k in range(5)], 1)
        mis = ~E.all(1)
        hf = (idx >= 1020).astype(np.int64)
        vol = (Y[:, 1] - Y[:, 2]) / np.where(Y[:, 0] > 0, Y[:, 0], np.nan)
        vb = np.clip(np.searchsorted(VB, vol, side="right") - 1, 0, 6)
        mser[idx, 0] += 1
        mser[idx[mis], 1] += 1
        for k in range(5):
            mser[idx[~E[:, k]], 2 + k] += 1
        for h in (0, 1):
            m = hf == h
            acc[h]["n"] += int(m.sum())
            acc[h]["mis"] += int((mis & m).sum())
            acc[h]["misf"] += (~E[m]).sum(0)
            acc[h]["vbn"] += bc(vb[m])
            acc[h]["vbm"] += bc(vb[m & mis])
        if mis.any():
            Xm, Ym, Em, im, hm = X[mis], Y[mis], E[mis], idx[mis], hf[mis]
            q0 = Xm[:, 4] == 0
            ovl = Em[:, 0] & (Xm[:, 4] < 0.99 * Ym[:, 4])
            ins = (Xm[:, 1] <= Ym[:, 1] * (1 + 1e-7)) & (Xm[:, 2] >= Ym[:, 2] * (1 - 1e-7))
            co = ~Em[:, 3] & Em[:, 0] & Em[:, 1] & Em[:, 2] & Em[:, 4]
            sh = np.zeros(len(im), bool)
            for W in (vv[im], vv[im + 2]):           # Vision phut t-1, t+1
                e4 = ~np.isnan(W[:, 0])
                for k in range(4):
                    e4 &= feq(Xm[:, k], np.nan_to_num(W[:, k]))
                sh |= e4
            Fm = np.stack([q0, ovl, ins, co, sh, Em[:, 0], Em[:, 3]], 1)
            ratio = Xm[:, 4] / np.where(Ym[:, 4] > 0, Ym[:, 4], np.nan)
            rbi = np.clip(np.searchsorted(RB, ratio, side="right") - 1, 0, 6)
            for h in (0, 1):
                mm = hm == h
                acc[h]["flags"] += Fm[mm].sum(0)
                acc[h]["rb"] += bc(rbi[mm])
            for k in range(5):
                bad = ~Em[:, k]
                with np.errstate(divide="ignore", invalid="ignore"):
                    r = np.abs(Xm[bad, k].astype(np.float64) - Ym[bad, k]) / np.abs(Ym[bad, k])
                lr = np.log10(np.clip(np.nan_to_num(r, nan=9.0, posinf=9.0), 1e-9, 9.0))
                hist[k] += np.histogram(lr, HB)[0]
        persym[s] = [int(len(idx)), int(mis.sum()), int((~E[:, 3]).sum())]
        for ms, kind in legs.get(s, ()):
            i = (ms - day_ms) // MN
            if not (0 <= i < 1440) or not (ha[i] and hv[i]):
                continue
            j = np.searchsorted(idx, i)
            if kind == 0:
                lg[0] += 1
                lg[1] += int(not E[j, 3])
            else:
                lg[2] += 1
                lg[3] += int(mis[j])
    out = dict(day=utcs(day_ms, "%Y%m%d"), sym=persym, legs=lg.tolist(),
               hist=[{int(i): int(c) for i, c in enumerate(hist[k]) if c} for k in range(5)],
               halves={h: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in acc[h].items()} for h in (0, 1)})
    return out, mser


def load_legs(lo_ms, hi_ms, syms):
    legs = {}
    for tg in ("ho26-k24-s-s42", "ho26-b0-s-s42"):
        d = load_pd(tg)
        for col, kind in (("start_ms", 0), ("end_ms", 1)):
            x = d[(d[col] >= lo_ms) & (d[col] < hi_ms)]
            for s, ms in zip(x["sym"], x[col]):
                if s + "USDT" in syms:
                    legs.setdefault(s + "USDT", set()).add((int(ms), kind))
    return legs


def chunk_of(day_ms):
    ym = utcs(day_ms, "%Y-%m")
    return ym if "2026-04" <= ym <= "2026-09" else utcs(day_ms)


def stage_d1(lo, hi):
    S = json.load(open(WD + "/kdiv_syms.json"))
    sl = S["all"]
    syms = set(sl)
    lo_ms, hi_ms = d7(lo), d7(hi)
    legs = load_legs(lo_ms, hi_ms, syms)
    od = WD + "/kdiv_d1"
    os.makedirs(od, exist_ok=True)
    st = as_store()
    day = lo_ms // D * D
    cur, VM = None, {}
    while day < hi_ms:
        fo = od + "/%s.json" % utcs(day, "%Y%m%d")
        if os.path.exists(fo):
            day += D
            continue
        t0 = time.time()
        ch = chunk_of(day)
        if ch != cur:
            VM = {}
            fn = vis_month if len(ch) == 7 else vis_day
            with ThreadPoolExecutor(8) as ex:
                for s, r in zip(sl, ex.map(lambda s: fn(s, ch), sl)):
                    if r is not None:
                        VM[s] = r
            cur = ch
            log.info("vision %s: %d/%d symbol", ch, len(VM), len(sl))
        rows = fetch242(st, [day + i * MN for i in range(1440)])
        t1 = time.time()
        A, gen, lut, nsym = dense242(rows, day, syms)
        VD = {s: vis_dense(VM[s], day) for s in sl if s in VM}
        R, mser = cmp_day(A, VD, day, legs)
        R["vis_missing"] = sorted(s for s in sl if s not in VM)
        R["err"] = dict(ERR)
        R["n_keys"] = int((nsym > 0).sum())
        json.dump(R, open(fo + ".tmp", "w"))
        np.savez_compressed(od + "/%s.npz" % utcs(day, "%Y%m%d"), mser=mser, gen=gen, lut=lut, nsym=nsym)
        os.replace(fo + ".tmp", fo)
        h0, h1 = R["halves"][0], R["halves"][1]
        n = h0["n"] + h1["n"]
        log.info("%s keys=%d cells=%d mis=%.3f%% as=%.0fs tot=%.0fs", R["day"], R["n_keys"], n,
                 100.0 * (h0["mis"] + h1["mis"]) / max(n, 1), t1 - t0, time.time() - t0)
        day += D
    st.close()


def rest_day(sym, day_ms):
    b = http(REST % (sym, day_ms), tries=3, timeout=30)
    out = np.full((1440, 7), np.nan)
    if b is None:
        return None
    js = json.loads(b)
    if not isinstance(js, list):
        log.warning("REST %s %s -> %s", sym, day_ms, str(js)[:200])
        return None
    for k in js:
        i = (int(k[0]) - day_ms) // MN
        if 0 <= i < 1440:
            out[i] = [float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[7]), float(k[5]), float(k[8])]
    return out


def eqcount(X, Y, nf):
    """X, Y (1440, >=nf) NaN=thieu -> dict(both, eq per field, eq_all, rb Q ratio tren o lech)."""
    both = ~np.isnan(X[:, 0]) & ~np.isnan(Y[:, 0])
    Xb, Yb = X[both], Y[both]
    E = np.stack([feq(Xb[:, k].astype(np.float32), Yb[:, k]) for k in range(nf)], 1)
    mis = ~E.all(1)
    ratio = Xb[mis, 4] / np.where(Yb[mis, 4] > 0, Yb[mis, 4], np.nan)
    return dict(both=int(both.sum()), x_only=int((~np.isnan(X[:, 0]) & np.isnan(Y[:, 0])).sum()),
                y_only=int((np.isnan(X[:, 0]) & ~np.isnan(Y[:, 0])).sum()), eqf=E.sum(0).tolist(),
                eq_all=int((~mis).sum()), rb=bc(np.clip(np.searchsorted(RB, ratio, side="right") - 1, 0, 6)).tolist())


def stage_d2():
    cand = []
    for f in sorted(glob.glob(WD + "/kdiv_d1/*.json")):
        R = json.load(open(f))
        if R["day"] < "20260425":
            continue
        for s, (n, m, mc) in R["sym"].items():
            if m > 0:
                cand.append((s, R["day"], m))
    cand.sort(key=lambda x: (-x[2], x[0], x[1]))
    pick, ns, nm = [], {}, {}
    for s, day, m in cand:
        mo = day[:6]
        if ns.get(s, 0) < 2 and nm.get(mo, 0) < 6:
            pick.append((s, day, m, "top"))
            ns[s] = ns.get(s, 0) + 1
            nm[mo] = nm.get(mo, 0) + 1
        if len(pick) >= 40:
            break
    rest = [c for c in cand if (c[0], c[1]) not in {(p[0], p[1]) for p in pick}]
    rng = random.Random(20261010)
    pick += [(s, d, m, "rand") for s, d, m in rng.sample(rest, min(20, len(rest)))]
    st = as_store()
    out = []
    for s, day, m, kind in pick:
        day_ms = int(datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        Rr = rest_day(s, day_ms)
        time.sleep(1.2)
        Vv = vis_dense(vis_day(s, utcs(day_ms)), day_ms, pad=0)
        A, _, _, _ = dense242(fetch242(st, [day_ms + i * MN for i in range(1440)]), day_ms, {s})
        A = A.get(s, np.full((1440, 5), np.nan, np.float32)).astype(np.float64)
        if Rr is None:
            out.append(dict(sym=s, day=day, kind=kind, d1_mis=m, rest=None))
            continue
        r = dict(sym=s, day=day, kind=kind, d1_mis=m,
                 rest_vs_vis=eqcount(Rr, Vv, 7), rest_vs_242=eqcount(A, Rr, 5), vis_vs_242=eqcount(A, Vv, 5))
        out.append(r)
        log.info("D2 %s %s %s d1mis=%d R~V %d/%d  R~242 %d/%d", kind, s, day, m, r["rest_vs_vis"]["eq_all"],
                 r["rest_vs_vis"]["both"], r["rest_vs_242"]["eq_all"], r["rest_vs_242"]["both"])
    st.close()
    T = {}
    for k in ("rest_vs_vis", "rest_vs_242", "vis_vs_242"):
        xs = [o[k] for o in out if o.get(k)]
        T[k] = dict(both=sum(x["both"] for x in xs), eq_all=sum(x["eq_all"] for x in xs),
                    eqf=np.sum([x["eqf"] for x in xs], 0).tolist(), rb=np.sum([x["rb"] for x in xs], 0).tolist(),
                    x_only=sum(x["x_only"] for x in xs), y_only=sum(x["y_only"] for x in xs))
        T[k]["rate"] = T[k]["eq_all"] / max(T[k]["both"], 1)
    json.dump(dict(n=len(out), totals=T, items=out, rest_fail=sum(1 for o in out if o.get("rest") is None and "rest_vs_vis" not in o)),
              open(WD + "/kdiv_d2.json", "w"), indent=1)
    log.info("D2 TOTAL %s", json.dumps({k: round(v["rate"], 6) for k, v in T.items()}))


def stage_dev():
    """D4b: ticker DEV (kaggle_data_hpo, Java-serialized) 2025 vs Vision daily, mau top50."""
    import jbin
    S = json.load(open(WD + "/kdiv_syms.json"))
    sl = S["top50"]
    res = []
    for day in ["2025%02d%02d" % (m, d) for m in (3, 6, 9, 12) for d in (1, 15)]:
        p = TDIR + "/ticker_%s.bin.gz" % day
        if not os.path.exists(p):
            res.append(dict(day=day, missing=True))
            continue
        day_ms = int(datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        A = {}
        with gzip.open(p, "rb") as f:
            b = f.read()
        for ms, mm in jbin.iter_minutes(b):
            i = (ms - day_ms) // MN
            if not (0 <= i < 1440):
                continue
            for s, v in mm.items():
                if s in sl:
                    A.setdefault(s, np.full((1440, 5), np.nan))[i] = (v[4], v[1], v[2], v[3], v[5])
        with ThreadPoolExecutor(8) as ex:
            VV = dict(zip(sl, ex.map(lambda s: vis_day(s, utcs(day_ms)), sl)))
        T = dict(day=day, both=0, eq_all=0, eqf=np.zeros(5, np.int64), x_only=0, y_only=0, nsym=0)
        for s in sl:
            if s not in A or VV.get(s) is None:
                continue
            c = eqcount(A[s], vis_dense(VV[s], day_ms, pad=0), 5)
            T["nsym"] += 1
            for k in ("both", "eq_all", "x_only", "y_only"):
                T[k] += c[k]
            T["eqf"] += np.array(c["eqf"])
        T["eqf"] = T["eqf"].tolist()
        T["rate"] = T["eq_all"] / max(T["both"], 1)
        res.append(T)
        log.info("DEV %s nsym=%d both=%d eq=%.5f%%", day, T["nsym"], T["both"], 100 * T["rate"])
    json.dump(res, open(WD + "/kdiv_dev.json", "w"), indent=1)


# ----------------------------- D4a: gate 242 vs Vision -----------------------------
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
BINS = "/home/ubuntu/claude_master/1009/ho26/bins2026Ax"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
FEATS = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
         "momentumAcceleration", "trendStrengthETH", "trendConsistency",
         "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
         "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
         "btcDominance", "rsi14", "volumeSpike", "distMA20",
         "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
         "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
         "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"]   # thu tu fold_20 (featdiff_pass2.FEATS)
DYN_MIN, SCORE_BASE, DYN_MULT = np.float32(0.26787), np.float32(0.15), np.float32(1.28760)
GS, PCT, BASE = np.float32(1.55), np.float32(0.999950829), np.float32(0.008)
K24 = 24
W0, W1 = d7("20260501"), d7("20260701")


class VisStore:
    """Store 242 nhung GIA TRI kline thay bang Vision (o co ca 2); o chi co 242 giu nguyen (cung universe)."""

    def __init__(self, orig_cls, orig_parse):
        self.st = orig_cls("242", pool=40)
        self.parse = orig_parse
        self.cache, self.cur = {}, None
        self.stat = dict(cells=0, repl=0, keep242=0)
        self.cl = {}                 # phut -> (close242 dict, closeVis dict) cho proxy hang
        self.rk = []

    def __getattr__(self, n):
        return getattr(self.st, n)

    def _load(self, ch, syms):
        if ch != self.cur:
            self.cache, self.cur = {}, ch
        need = [s for s in syms if s not in self.cache]
        if need:
            with ThreadPoolExecutor(8) as ex:
                for s, r in zip(need, ex.map(lambda s: vis_month(s, ch), need)):
                    self.cache[s] = None if r is None else (r[0], r[1][:, :5].astype(np.float32))
            log.info("VisStore %s +%d sym (tong %d, co Vision %d)", ch, len(need), len(self.cache),
                     sum(1 for v in self.cache.values() if v is not None))

    def get_kline_day(self, d, day_count=1440):
        raw = self.st.get_kline_day(d, day_count)
        parsed = {}
        for k, v in raw.items():
            ms = int(datetime.datetime.strptime(k, "%Y%m%d-%H%M").replace(tzinfo=TZ7).timestamp() * 1000)
            parsed[k] = (ms, self.parse(v))
        syms = sorted(set(s for _, (s2, _) in parsed.values() for s in s2))
        self._load(utcs(d, "%Y-%m"), syms)
        VD = {}
        for s in syms:
            vm = self.cache.get(s)
            if vm is not None:
                VD[s] = vis_dense((vm[0], vm[1].astype(np.float64)), d, pad=0)[:, :5].astype(np.float32)
        out = {}
        for k in sorted(parsed, key=lambda x: parsed[x][0]):
            ms, (s2, a2) = parsed[k]
            i = (ms - d) // MN
            a3 = a2.copy()
            for j, s in enumerate(s2):
                V = VD.get(s)
                if V is not None and 0 <= i < 1440 and not np.isnan(V[i, 0]):
                    a3[j] = V[i]
                    self.stat["repl"] += 1
                else:
                    self.stat["keep242"] += 1
            self.stat["cells"] += len(s2)
            out[k] = (s2, a3)
            self._rank(ms, s2, a2, a3)
        return out

    def _rank(self, ms, s2, a2, a3):
        """Proxy hang: Jaccard top-24 / bottom-24 theo return 60' (close 242 vs close Vision), luoi 15'."""
        if not (W0 - 2 * H <= ms < W1):
            return
        self.cl[ms] = (dict(zip(s2, a2[:, 3].tolist())), dict(zip(s2, a3[:, 3].tolist())))
        for t in [t for t in self.cl if t < ms - 61 * MN]:
            del self.cl[t]
        if ms < W0 or ms % (15 * MN) or (ms - 60 * MN) not in self.cl:
            return
        (c2, cv), (p2, pv) = self.cl[ms], self.cl[ms - 60 * MN]
        ss = [s for s in c2 if s in p2 and p2[s] > 0 and pv.get(s, 0) > 0 and s not in STABLE]
        if len(ss) < 100:
            return
        r2 = np.array([c2[s] / p2[s] - 1 for s in ss])
        rv = np.array([cv[s] / pv[s] - 1 for s in ss])
        o2, ov = np.argsort(r2, kind="mergesort"), np.argsort(rv, kind="mergesort")
        jt = len(set(o2[-K24:]) & set(ov[-K24:])) / len(set(o2[-K24:]) | set(ov[-K24:]))
        jb = len(set(o2[:K24]) & set(ov[:K24])) / len(set(o2[:K24]) | set(ov[:K24]))
        self.rk.append((int(ms), round(jt, 4), round(jb, 4), len(ss)))


def stage_gate(a):
    """33 feature gate (port devexport_202609, md INLINE, funding 242) tu kline 242 (--arm 242) hoac Vision (--arm vis)."""
    import argparse as _ap
    orig_store, orig_parse = dx.Store, dx.parse_minute
    out = WD + "/kdiv_gate_%s_%s_%s.csv.gz" % (a.arm, a.lo, a.hi)
    holder, memo = {}, {}

    def fast_parse(x):
        # run() parse cung 1 bytes 2 lan (md inline + feature) -> memo theo dinh danh; tuple (VisStore) di thang
        if isinstance(x, tuple):
            return x
        r = memo.get(id(x))
        if r is None or r[0] is not x:
            if len(memo) > 4000:
                memo.clear()
            r = memo[id(x)] = (x, orig_parse(x))
        return r[1]
    dx.parse_minute = fast_parse
    if a.arm == "vis":

        def mk(cluster, pool=40):
            holder["vs"] = VisStore(orig_store, orig_parse)
            return holder["vs"]
        dx.Store = mk
    rc = dx.run(_ap.Namespace(start=a.lo, end=a.hi, out=out + ".tmp.gz", cluster="242", md_inline=True,
                              died_config=REPO + "/config.properties"))
    if rc:
        raise SystemExit("devexport rc=%s" % rc)
    os.replace(out + ".tmp.gz", out)
    if a.arm == "vis":
        vs = holder["vs"]
        json.dump(dict(stat=vs.stat, rank=vs.rk), open(out.replace(".csv.gz", "_aux.json"), "w"))
        log.info("vis stat %s rank n=%d", vs.stat, len(vs.rk))


def load_feat(pattern, sess):
    fs = sorted(glob.glob(pattern))
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    df = df.drop_duplicates("ts", keep="first").sort_values("ts").reset_index(drop=True)
    X = df[FEATS].to_numpy(np.float32)
    p = sess.run(None, {sess.get_inputs()[0].name: X})[0].reshape(-1).astype(np.float32)
    log.info("feat %s: files=%d rows=%d", pattern, len(fs), len(df))
    return df, p


def load_bins():
    mp = pd.read_csv(SYMMAP)
    id2s = dict(zip(mp["symId"].astype(int), mp["symbol"].astype(str).str.strip()))
    T, SP = [], []
    for f in sorted(glob.glob(BINS + "/predict_wf_2026*.bin")):
        a = np.fromfile(f, dtype=REC)
        p0 = a["p0"].astype(np.float32)
        ok = ~np.isnan(p0)
        ts, sc = a["ts"][ok].astype(np.int64), (np.float32(1) - p0[ok])
        o = np.lexsort((sc, ts))
        ts, sc = ts[o], sc[o]
        u, st = np.unique(ts, return_index=True)
        grp = np.repeat(np.arange(len(u)), np.diff(np.append(st, len(ts))))
        rk = np.arange(len(ts)) - st[grp]
        k = rk < K24
        M = np.full((len(u), K24), np.nan, np.float32)
        M[grp[k], rk[k]] = sc[k]
        T.append(u)
        SP.append(M)
    return np.concatenate(T), np.vstack(SP)


def gate_eval(ts, p15, T15, SP):
    """ts sort tang (phut), p15 float32 -> (pass (n,24) bool, valid (n,24), q theo phut)."""
    import gate_offline as go
    fi = np.searchsorted(T15, ts, "right") - 1
    okm = (fi >= 0) & (ts - T15[np.maximum(fi, 0)] <= 15 * MN)
    sp = np.where(okm[:, None], SP[np.maximum(fi, 0)], np.nan).astype(np.float32)
    valid = ~np.isnan(sp)
    fac = np.maximum(DYN_MIN, (sp / SCORE_BASE * DYN_MULT).astype(np.float32)).astype(np.float32)
    r = (p15[:, None] / (fac * GS).astype(np.float32)).astype(np.float32)
    hrs_row = ts // H
    vals = r[valid]
    hours = np.repeat(hrs_row, valid.sum(1))
    q, qh, jmax = go.hourly_q(vals, hours, int(ts[valid.any(1)][0]), 90, PCT, 256)
    qmap = np.full(len(ts), np.nan, np.float32)
    pos = np.searchsorted(qh, hrs_row)
    hit = (pos < len(qh)) & (qh[np.minimum(pos, len(qh) - 1)] == hrs_row)
    qmap[hit] = q[pos[hit]]
    qq = np.where(np.isnan(qmap), BASE, qmap).astype(np.float32)
    thr = ((qq[:, None] * fac).astype(np.float32) * GS).astype(np.float32)
    P = ~(p15[:, None] < thr) & valid
    return P, valid, qmap, jmax


def stage_gatecmp():
    import onnxruntime as ort
    sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    d2, p2 = load_feat(WD + "/kdiv_gate_242_*.csv.gz", sess)
    dv, pv = load_feat(WD + "/kdiv_gate_vis_*.csv.gz", sess)
    V0 = d7("20260401")
    t2 = d2["ts"].to_numpy(np.int64)
    tv0 = dv["ts"].to_numpy(np.int64)
    kv = tv0 >= V0
    tv = np.concatenate([t2[t2 < V0], tv0[kv]])
    pvv = np.concatenate([p2[t2 < V0], pv[kv]])
    T15, SP = load_bins()
    P2, V2, q2, j2 = gate_eval(t2, p2, T15, SP)
    PV, VV, qv, jv = gate_eval(tv, pvv, T15, SP)
    w2 = np.nonzero((t2 >= W0) & (t2 < W1))[0]
    wv = np.nonzero((tv >= W0) & (tv < W1))[0]
    com, i2, iv = np.intersect1d(t2[w2], tv[wv], return_indices=True)
    a, b = w2[i2], wv[iv]
    va = V2[a] & VV[b]
    fl = (P2[a] != PV[b]) & va
    dp = np.abs(p2[a].astype(np.float64) - pvv[b].astype(np.float64))
    fd = {}
    da, db = d2.iloc[a].reset_index(drop=True), dv.set_index("ts").loc[com].reset_index()
    for f in FEATS:
        x, y = da[f].to_numpy(np.float64), db[f].to_numpy(np.float64)
        fd[f] = float(np.mean(~(np.isclose(x, y, rtol=1e-6, atol=1e-12) | (np.isnan(x) & np.isnan(y)))))
    hq = np.unique(com // H)
    qa = pd.Series(q2[a], index=com // H).groupby(level=0).first()
    qb = pd.Series(qv[b], index=com // H).groupby(level=0).first()
    qr = (qb / qa).replace([np.inf, -np.inf], np.nan).dropna()
    rk = []
    for f in sorted(glob.glob(WD + "/kdiv_gate_vis_*_aux.json")):
        rk += json.load(open(f))["rank"]
    rk = sorted({r[0]: r for r in rk if W0 <= r[0] < W1}.values())   # bo trung o ranh chunk
    rk = np.array(rk) if rk else np.zeros((0, 4))
    month = pd.to_datetime(com + TZ, unit="ms").strftime("%Y-%m").to_numpy()
    bym = {}
    for mo in sorted(set(month)):
        m = month == mo
        bym[mo] = dict(minutes=int(m.sum()), pairs=int(va[m].sum()), flips=int(fl[m].sum()),
                       flip_pct=100.0 * fl[m].sum() / max(va[m].sum(), 1),
                       min_any_flip_pct=100.0 * fl[m].any(1).mean(),
                       pass242_pct=100.0 * (P2[a][m] & va[m]).sum() / max(va[m].sum(), 1),
                       passvis_pct=100.0 * (PV[b][m] & va[m]).sum() / max(va[m].sum(), 1))
    res = dict(window=["20260501", "20260701"], minutes=int(len(com)), pairs=int(va.sum()), flips=int(fl.sum()),
               flip_pct=100.0 * fl.sum() / max(va.sum(), 1), min_any_flip_pct=100.0 * fl.any(1).mean(),
               flip_242pass_visfail=int((fl & P2[a]).sum()), flip_visPass_242fail=int((fl & PV[b]).sum()),
               pass242_pct=100.0 * (P2[a] & va).sum() / max(va.sum(), 1),
               passvis_pct=100.0 * (PV[b] & va).sum() / max(va.sum(), 1),
               p15_eq_pct=100.0 * float(np.mean(p2[a] == pvv[b])),
               dp15_pp=dict(p50=float(np.percentile(dp, 50) * 100), p90=float(np.percentile(dp, 90) * 100),
                            p99=float(np.percentile(dp, 99) * 100), max=float(dp.max() * 100)),
               p15_mean_pct=dict(a242=float(p2[a].mean() * 100), vis=float(pvv[b].mean() * 100)),
               q_ratio_vis_over_242=dict(p1=float(qr.quantile(0.01)), p50=float(qr.median()), p99=float(qr.quantile(0.99)),
                                         hours=int(len(qr)), hours_neq=int((qr != 1).sum())),
               jmax=[int(j2), int(jv)], feat_diff_frac=fd, by_month=bym,
               rank_proxy=dict(n=int(len(rk)), jac_top24_mean=float(rk[:, 1].mean()) if len(rk) else None,
                               jac_bot24_mean=float(rk[:, 2].mean()) if len(rk) else None,
                               jac_top24_lt1_pct=float(100 * np.mean(rk[:, 1] < 1)) if len(rk) else None,
                               jac_bot24_lt1_pct=float(100 * np.mean(rk[:, 2] < 1)) if len(rk) else None))
    # validate: truoc diem gay (04-03..04-24, sau warm-up chunk) 2 nhanh phai cho p15 gan nhu trung
    va0, va1 = d7("20260403"), d7("20260425")
    cm, j2_, jv_ = np.intersect1d(t2[(t2 >= va0) & (t2 < va1)], tv0[(tv0 >= va0) & (tv0 < va1)], return_indices=True)
    i2_ = np.nonzero((t2 >= va0) & (t2 < va1))[0][j2_]
    iv_ = np.nonzero((tv0 >= va0) & (tv0 < va1))[0][jv_]
    res["validate_pre_break"] = dict(minutes=int(len(cm)), p15_eq_pct=100.0 * float(np.mean(p2[i2_] == pv[iv_])),
                                     dp15_max_pp=float(np.max(np.abs(p2[i2_].astype(np.float64) - pv[iv_])) * 100) if len(cm) else None)
    json.dump(res, open(WD + "/kdiv_gatecmp.json", "w"), indent=1)
    log.info("GATECMP %s", json.dumps({k: v for k, v in res.items() if k not in ("feat_diff_frac", "by_month")}))


# ----------------------------- report -----------------------------
def hq(h, q):
    c = np.cumsum(h)
    if c[-1] == 0:
        return None
    i = int(np.searchsorted(c, q * c[-1]))
    return float(10 ** ((HB[i] + HB[i + 1]) / 2))


def stage_report():
    S = json.load(open(WD + "/kdiv_syms.json"))
    lo7, hi7 = d7("20260401"), d7("20261010")
    days, mon, sym_mj = {}, {}, {}
    legs = np.zeros(4, np.int64)
    mins = []
    for f in sorted(glob.glob(WD + "/kdiv_d1/*.json")):
        R = json.load(open(f))
        dms = int(datetime.datetime.strptime(R["day"], "%Y%m%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        z = np.load(f[:-5] + ".npz")
        ms = dms + np.arange(1440) * MN
        mins.append(np.column_stack([ms, z["mser"], z["gen"], z["lut"], z["nsym"]]))
        for h in ("0", "1"):
            d7s = utcs(dms + TZ + (0 if h == "0" else D), "%Y%m%d")
            if not (lo7 <= d7(d7s) < hi7):
                continue
            x = R["halves"][h]
            t = days.setdefault(d7s, dict(n=0, mis=0, misf=np.zeros(5), a_only=0, v_only=0, flags=np.zeros(len(FLAGS)),
                                          vbn=np.zeros(7), vbm=np.zeros(7), rb=np.zeros(7)))
            for k in t:
                t[k] = t[k] + (np.array(x[k]) if isinstance(t[k], np.ndarray) else x[k])
        mo = R["day"][:6]
        hm = mon.setdefault(mo, np.zeros((5, 1000), np.int64))
        for k in range(5):
            for i, c in R["hist"][k].items():
                hm[k, int(i)] += c
        if "20260501" <= R["day"] <= "20260630":
            legs += np.array(R["legs"])
            for s, v in R["sym"].items():
                x = sym_mj.setdefault(s, np.zeros(3, np.int64))
                x += np.array(v)
    M = np.vstack(mins)
    M = M[(M[:, 0] >= lo7) & (M[:, 0] < hi7)]
    ms, nb, nm = M[:, 0], M[:, 1], M[:, 2]
    gen, lut, nsym = M[:, 8], M[:, 9], M[:, 10]

    def agg(sel):
        t = None
        for d in sel:
            x = days[d]
            t = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in x.items()} if t is None else \
                {k: t[k] + x[k] for k in t}
        n = max(t["n"], 1)
        nmis = max(t["mis"], 1)
        return dict(days=len(sel), cells=int(t["n"]), mis_pct=100.0 * t["mis"] / n,
                    mis_field_pct={F5[k]: 100.0 * t["misf"][k] / n for k in range(5)},
                    a_only=int(t["a_only"]), v_only=int(t["v_only"]),
                    flags_pct_of_mis={FLAGS[k]: 100.0 * t["flags"][k] / nmis for k in range(len(FLAGS))},
                    qratio_pct_of_mis={"%s..%s" % (RB[k], RB[k + 1]): 100.0 * t["rb"][k] / nmis for k in range(7)},
                    vol_mis_pct={"%s..%s" % (VB[k], VB[k + 1]): [int(t["vbn"][k]), 100.0 * t["vbm"][k] / max(t["vbn"][k], 1)]
                                 for k in range(7)})

    dk = sorted(days)
    per = dict(pre_0401_0424=agg([d for d in dk if d < "20260425"]),
               post_0425_1009=agg([d for d in dk if d >= "20260425"]),
               ho26_0501_0630=agg([d for d in dk if "20260501" <= d <= "20260630"]),
               q3_0701_0930=agg([d for d in dk if "20260701" <= d <= "20260930"]))
    for mo in sorted(set(d[:6] for d in dk)):
        per["m" + mo] = agg([d for d in dk if d[:6] == mo])
        per["m" + mo]["relerr_p50_p99"] = {F5[k]: [hq(mon[mo][k], 0.5), hq(mon[mo][k], 0.99)] for k in range(5)} if mo in mon else None
    daily = {d: dict(cells=int(days[d]["n"]), mis_pct=round(100.0 * days[d]["mis"] / max(days[d]["n"], 1), 4),
                     f=[round(100.0 * days[d]["misf"][k] / max(days[d]["n"], 1), 3) for k in range(5)]) for d in dk}
    # LUT / gen / tap trung theo phut
    off = lut / 1e9 - (ms / 1000.0 + 60)
    post = ms >= d7("20260425")
    ob = np.clip(np.searchsorted(OB, off, side="right") - 1, 0, len(OB) - 2)
    ob[lut == 0] = len(OB) - 1
    lutb = {}
    for k in range(len(OB)):
        m = post & (ob == k) & (nb > 0)
        lab = ("%s..%s" % (OB[k], OB[k + 1])) if k < len(OB) - 1 else "no_lut"
        lutb[lab] = dict(minutes=int(m.sum()), cells=int(nb[m].sum()), mis_pct=100.0 * nm[m].sum() / max(nb[m].sum(), 1))
    gb = {}
    for lab, a_, b_ in (("<=20", 0, 20), ("21", 21, 21), ("22", 22, 22), ("23-30", 23, 30), ("31-100", 31, 100), (">100", 101, 1e12)):
        m = post & (gen >= a_) & (gen <= b_) & (nb > 0)
        gb[lab] = dict(minutes=int(m.sum()), cells=int(nb[m].sum()), mis_pct=100.0 * nm[m].sum() / max(nb[m].sum(), 1))

    rw = off >= 86400
    sweep = dict(minutes=int(rw.sum()))
    if rw.any():
        sweep.update(min_from=k7(int(ms[rw].min())), min_to=k7(int(ms[rw].max())),
                     lut_from=k7(int(lut[rw].min() // 10 ** 6)), lut_to=k7(int(lut[rw].max() // 10 ** 6)),
                     post_minutes=int((rw & post).sum()))
    share = nm / np.maximum(nb, 1)
    conc = {}
    for lab, a_, b_ in (("0", 0, 0), ("(0,5%]", 1e-12, 0.05), ("(5,20%]", 0.05, 0.2), ("(20,50%]", 0.2, 0.5), ("(50,100%]", 0.5, 1.01)):
        m = post & (nb > 0) & (share >= a_) & (share <= b_) if lab == "0" else post & (nb > 0) & (share > a_) & (share <= b_)
        conc[lab] = dict(minutes=int(m.sum()), mis_cells_pct=100.0 * nm[m].sum() / max(nm[post].sum(), 1))
    # diem gay
    b0, b1 = d7("20260424"), d7("20260426")
    w = (ms >= b0) & (ms < b1)
    mw, nbw, nmw = ms[w], nb[w], nm[w]
    okr = 1 - nmw / np.maximum(nbw, 1)
    first_mis = k7(int(mw[np.argmax(nmw > 0)])) if (nmw > 0).any() else None
    hr = {}
    for i in range(0, len(mw), 60):
        hr[k7(int(mw[i]))] = round(100.0 * (1 - nmw[i:i + 60].sum() / max(nbw[i:i + 60].sum(), 1)), 3)
    brk = None
    for i in range(len(mw) - 60):
        if 1 - nmw[i:i + 60].sum() / max(nbw[i:i + 60].sum(), 1) < 0.99:
            rest = [1 - nmw[j:j + 60].sum() / max(nbw[j:j + 60].sum(), 1) for j in range(i, len(mw) - 59, 60)]
            if max(rest) < 0.99:
                brk = k7(int(mw[i]))
                break
    gen_w = {k7(int(mw[i])): int(gen[w][i]) for i in range(0, len(mw), 30)}

    grp = {}
    for g in ("top50", "ho26"):
        x = np.sum([sym_mj[s] for s in S[g] if s in sym_mj], 0)
        grp[g] = dict(cells=int(x[0]), mis_pct=100.0 * x[1] / max(x[0], 1), close_mis_pct=100.0 * x[2] / max(x[0], 1))
    out = dict(prereg="b41bbf81", n_sym=len(S["all"]), syms=S, periods=per, daily=daily, lut_buckets_post=lutb,
               gen_buckets_post=gb, rewrite_sweep=sweep, minute_concentration_post=conc,
               breakpoint=dict(rule_minute=brk, first_mis_minute=first_mis, hourly_match_pct=hr, gen_30min=gen_w),
               ho26_mayjun=dict(groups=grp, legs=dict(entry_cells=int(legs[0]), entry_close_mis=int(legs[1]),
                                                      exit_cells=int(legs[2]), exit_any_mis=int(legs[3]))))
    for k, f in (("d2", "kdiv_d2.json"), ("dev2025", "kdiv_dev.json"), ("gate", "kdiv_gatecmp.json")):
        p = WD + "/" + f
        if os.path.exists(p):
            out[k] = json.load(open(p))
    if "d2" in out:
        out["d2"].pop("items_full", None)
    json.dump(out, open(REPO + "/docs/audit/KLINE_242_DIVERGENCE.json", "w"), indent=1, default=float)
    log.info("report: post mis=%.3f%% brk=%s first=%s", per["post_0425_1009"]["mis_pct"], brk, first_mis)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--lo", default="20260401")
    ap.add_argument("--hi", default="20261010")
    ap.add_argument("--arm", default="242")
    a = ap.parse_args()
    if a.stage == "syms":
        stage_syms()
    elif a.stage == "d1":
        stage_d1(a.lo, a.hi)
    elif a.stage in globals() or ("stage_" + a.stage) in globals():
        f = globals()["stage_" + a.stage]
        f(a) if a.stage in ("gate",) else f()
    else:
        raise SystemExit("stage?")


if __name__ == "__main__":
    main()
