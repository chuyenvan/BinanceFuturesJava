#!/usr/bin/env python3
"""PARITY 1020 — phan B: S1 selectorScore + hang top-24 (4), net015 gateValue qua quantile-map (5).
Offline = tinh lai tu du lieu DA SETTLE tren Aerospike 242 (kline_1m_opt close 1h, oi_feat_delta24h/oi_feat_lsg)
dung cong thuc S1FeatureLive/S1RankerLive (ban Java live), model c3_models (md5 khop 242).
Universe tung phut mau = khoa cua predictionSymbol/<ts>.features (= aiCandidates live).
net015: P(win) tinh tren CHINH mang float[45] live (Pa1020Feat) -> do code/map + anh huong thu tu S1; KHONG do feature 45."""
import glob, gzip, io, json, os, subprocess, sys, datetime as dt
import numpy as np, pandas as pd, onnxruntime as ort, aerospike, cramjam
from importlib.machinery import SourceFileLoader
W = "/home/ubuntu/claude_master/parity_1020"
dx = SourceFileLoader("dx", W + "/devexport_1020.py").load_module()
A = {}
exec(open(W + "/par_a.py").read().split("res = {}")[0], A)
read_gz, f7, stats = A["read_gz"], A["f7"], A["stats"]
H, MIN = 3600000, 60000
T0 = 1792148400000
TZ7 = dt.timezone(dt.timedelta(hours=7))
NH = 336 + 48
MERGE_TOL = 2 * H


def mkey(ms):
    return dt.datetime.fromtimestamp(ms / 1000, TZ7).strftime("%Y%m%d-%H%M")


# ---------- 45 feature live (Java) ----------
FEATCSV = W + "/feat45_live.csv.gz"
files = sorted(glob.glob(W + "/raw242/psym/*.features"))
if not os.path.exists(FEATCSV) or os.path.getmtime(FEATCSV) < max(os.path.getmtime(f) for f in files):
    cp = "/home/ubuntu/src_wt_pxcache/target/binance-java-sdk-1.2.4.jar:" + W + "/jcls"
    r = subprocess.run(["java", "-Xmx2g", "-cp", cp, "Pa1020Feat", FEATCSV] + files, capture_output=True, text=True)
    print("JAVA", r.stdout.strip(), r.stderr.strip()[-500:])
F45 = pd.read_csv(FEATCSV, dtype={"symbol": str})
mins = sorted(F45.ts.unique().tolist())
print("feature minutes", len(mins), "rows", len(F45))

# ---------- live sel_dump ----------
S = pd.read_csv(W + "/out_sel_gate.csv.gz")
S = S[S.ts.isin(mins)].copy()
print("sel rows on sampled minutes", len(S), "minutes", S.ts.nunique())
legacy = set(l.strip() for l in open(W + "/raw242/legacy_symbols.csv") if l.strip() and not l.startswith("#"))
print("legacy", len(legacy))

# ---------- kline close 1h tu 242 ----------
c = aerospike.client({"hosts": [("103.157.218.242", 3222)], "policies": {"timeout": 8000, "max_retries": 2}}).connect()
hmin = (min(mins) // H) * H - (NH - 1) * H
hmax = (max(mins) // H) * H
hist = {}   # hour -> dict sym->close
for t in range(hmin, hmax + H, H):
    try:
        rec = c.get(("ticker", "kline_1m_opt", mkey(t - MIN)))
    except Exception:
        continue
    syms, arr = dx.parse_minute(rec[2]["data"])
    d = {}
    for i, s in enumerate(syms):
        s = s if s.endswith("USDT") else s + "USDT"
        pc = float(arr[i, 3])
        if pc > 0:
            d[s] = pc
    hist[t] = d
print("hours read", len(hist), "of", (hmax - hmin) // H + 1)

# ---------- OI tu 242 ----------
allsym = sorted(set(F45.symbol))
oi = {}
for s in allsym:
    a = []
    for st in ("oi_feat_delta24h", "oi_feat_lsg"):
        m = {}
        for mo in ("202609", "202610"):
            try:
                rec = c.get(("ticker", st, s + "_" + mo))
                js = json.loads(bytes(cramjam.snappy.decompress_raw(rec[2]["f_data"])))
                m.update({int(k): float(np.float32(v)) for k, v in js.items()})
            except Exception:
                pass
        ks = np.array(sorted(m), dtype=np.int64)
        a.append((ks, np.array([m[k] for k in ks], dtype=np.float64)))
    oi[s] = a
c.close()
print("OI loaded", len(oi))

S1 = ort.InferenceSession(W + "/raw242/models/c3_models/s1a2x1_cut20251231.onnx", providers=["CPUExecutionProvider"])
s1in = S1.get_inputs()[0].name
NET = ort.InferenceSession(W + "/raw242/models/c3_models/g015x26_f15_cut20251231.onnx", providers=["CPUExecutionProvider"])
netin = NET.get_inputs()[0].name
outs = [o.name for o in NET.get_outputs()]
pidx = [i for i, o in enumerate(outs) if "prob" in o.lower()]
pidx = pidx[0] if pidx else len(outs) - 1


def pwin(X):
    o = NET.run(None, {netin: X.astype(np.float32)})[pidx]
    if isinstance(o, list):
        return np.array([float(np.float32(d.get(1, d.get("1", np.nan)))) for d in o], dtype=np.float32)
    o = np.asarray(o)
    return o[:, -1].astype(np.float32)


def rank_pct(v):
    out = np.full(len(v), np.nan)
    m = ~np.isnan(v)
    if m.sum() == 0:
        return out
    out[m] = pd.Series(v[m]).rank(method="average").values / m.sum()
    return out


def floor_tol(ks, t, avail_max=None):
    if len(ks) == 0:
        return None
    hi = t if avail_max is None else min(t, avail_max)
    i = np.searchsorted(ks, hi, "right") - 1
    if i < 0 or (t - ks[i]) > MERGE_TOL:
        return None
    return int(ks[i])


def val_of(a, ref):
    ks, vs = a
    i = np.searchsorted(ks, ref)
    return float(vs[i]) if i < len(ks) and ks[i] == ref else np.nan


def oi_feats(s, now, H0, mode):
    a = oi.get(s)
    if a is None:
        return np.nan, np.nan
    d, l = a
    if mode == "T":   # backtest/train: chi diem moc gio, asof <= gio dong cuoi (feat_v2_build)
        def hm(x):
            k, v = x; mm = (k % H) == 0; return k[mm], v[mm]
        d2, l2 = hm(d), hm(l)
        ref = floor_tol(d2[0], H0)
        if ref is None:
            ref = floor_tol(l2[0], H0)
        if ref is None:
            return np.nan, np.nan
        return val_of(d2, ref), val_of(l2, ref)
    avail = None if mode == "S" else H0 - (25 if mode == "E25" else 35) * MIN
    lo = H0 - 24 * H
    ref = floor_tol(d[0][d[0] >= lo], now, avail)
    if ref is None:
        ref = floor_tol(l[0][l[0] >= lo], now, avail)
    if ref is None:
        return np.nan, np.nan
    return val_of(d, ref), val_of(l, ref)


SYM_ALL = sorted(set().union(*[set(d) for d in hist.values()]) | set(allsym))
SIDX = {x: i for i, x in enumerate(SYM_ALL)}
NHALL = (hmax - hmin) // H + 1
CL = np.full((len(SYM_ALL), NHALL), np.nan)
for h, d in hist.items():
    j = (h - hmin) // H
    for x, v in d.items():
        CL[SIDX[x], j] = v
HM = {x: tuple((k[(k % H) == 0], v[(k % H) == 0]) for k, v in oi[x]) for x in oi}


def oi_feats2(s, now, H0, mode):
    if s not in oi:
        return np.nan, np.nan
    if mode == "T":
        d2, l2 = HM[s]
        ref = floor_tol(d2[0], H0)
        if ref is None:
            ref = floor_tol(l2[0], H0)
        if ref is None:
            return np.nan, np.nan
        return val_of(d2, ref), val_of(l2, ref)
    d, l = oi[s]
    avail = None if mode == "S" else H0 - (25 if mode == "E25" else 35) * MIN
    lo = H0 - 24 * H
    dk = d[0][np.searchsorted(d[0], lo):]
    lk = l[0][np.searchsorted(l[0], lo):]
    ref = floor_tol(dk, now, avail)
    if ref is None:
        ref = floor_tol(lk, now, avail)
    if ref is None:
        return np.nan, np.nan
    return val_of(d, ref), val_of(l, ref)


def s1_scores(uni, now, mode):
    H0 = (now // H) * H
    j1 = (H0 - hmin) // H
    cand = sorted(x for x in uni if x in SIDX)
    Cw = CL[[SIDX[x] for x in cand], j1 - (NH - 1):j1 + 1]
    keep = ~np.all(np.isnan(Cw), axis=1)
    syms = [x for x, k in zip(cand, keep) if k]
    C = Cw[keep]
    n = NH - 1
    cn = C[:, n]
    w = C[:, n - 167:n + 1]
    nn = np.sum(~np.isnan(w), axis=1)
    with np.errstate(all="ignore"):
        mx = np.nanmax(np.where(np.isnan(w), -np.inf, w), axis=1)
        dd = np.where((nn >= 84) & ~np.isnan(cn) & (mx != 0) & np.isfinite(mx), cn / mx - 1, np.nan)
        ww = np.where(np.isnan(w), -np.inf, w)
        k = np.argmax(ww, axis=1)
        hrs = np.where(((168 - nn) <= 84) & np.isfinite(ww[np.arange(len(k)), k]), (167 - k) / 168.0, np.nan)
        rr = C[:, n - 167:n + 1] / C[:, n - 168:n] - 1
        nr = np.sum(~np.isnan(rr), axis=1)
        vol = np.where((nr >= 84) & (nr >= 2), np.nanstd(rr, axis=1, ddof=1), np.nan)
        r3 = cn / C[:, n - 72] - 1
        r14 = cn / C[:, n - 336] - 1
    oid = np.full(len(syms), np.nan); lsg = oid.copy()
    for i, x in enumerate(syms):
        oid[i], lsg[i] = oi_feats2(x, now, H0, mode)
    X = np.column_stack([vol, dd, rank_pct(dd), hrs, r3, rank_pct(r3), r14, lsg, rank_pct(oid)]).astype(np.float32)
    ready = int(np.sum(np.sum(~np.isnan(C), axis=1) >= 336))
    raw = np.asarray(S1.run(None, {s1in: X})[0]).reshape(-1)
    return dict(zip(syms, (-raw).astype(np.float32).tolist())), ready, None


def rank_first(v, asc):
    order = sorted(range(len(v)), key=lambda i: ((v[i] if asc else -v[i]), i))
    r = np.empty(len(v), dtype=int)
    for k, i in enumerate(order):
        r[i] = k + 1
    return r


res = {"modes": {}}
for mode in ("S", "E25", "E35", "T"):
    rows, mrows = [], []
    for ts in mins:
        uni = set(F45.symbol[F45.ts == ts])
        sc, ready, X = s1_scores(uni, ts, mode)
        # TreeMap<Float,String>: diem trung -> mat coin
        byv = {}
        for s in sorted(sc):
            if not np.isnan(sc[s]):
                byv.setdefault(np.float32(sc[s]), []).append(s)
        ndup = sum(len(v) - 1 for v in byv.values())
        pool = sorted(byv.items(), key=lambda x: x[0])
        pool_syms = [v[-1] for _, v in pool]          # gia dinh: ban ghi cuoi thang (khong tai lap duoc thu tu HashMap)
        nonleg = [s for s in pool_syms if s not in legacy]
        top_off = nonleg[:24]
        L = S[S.ts == ts].sort_values("rank")
        top_live = L.symbol.tolist()
        rk_off = {s: i + 1 for i, s in enumerate(nonleg)}
        # quantile-map net015 (LiveBuildMap) tren pwin cua mang 45 live
        Fm = F45[F45.ts == ts].set_index("symbol")
        uni_map = sorted(s for s in pool_syms if s in Fm.index)
        pw = pwin(Fm.loc[uni_map, ["f%d" % i for i in range(45)]].values.astype(np.float32))
        scv = np.array([sc[s] for s in uni_map], dtype=np.float32)
        rS = rank_first(scv.tolist(), True)
        pS = rank_first(pw.tolist(), False)
        byP = np.empty(len(uni_map) + 1, dtype=np.float32)
        for i in range(len(uni_map)):
            byP[pS[i]] = pw[i]
        gv_off = {s: np.float32(np.float32(1.0) - byP[rS[i]]) for i, s in enumerate(uni_map)}
        kmap = {s: int(rS[i]) for i, s in enumerate(uni_map)}
        pdesc = np.sort(pw)[::-1]
        gv_vals = (np.float32(1.0) - pdesc).astype(np.float32)
        for _, r in L.iterrows():
            s = r.symbol
            gl = np.float32(r.gateValue)
            hit = np.where(gv_vals == gl)[0]
            rows.append(dict(ts=ts, symbol=s, rank_live=int(r["rank"]), score_live=float(r.selectorScore),
                             score_off=float(sc.get(s, np.nan)), rank_off=rk_off.get(s, np.nan),
                             gv_live=float(gl), gv_off=float(gv_off.get(s, np.nan)),
                             k_implied=int(hit[0]) + 1 if len(hit) else -1, k_off=kmap.get(s, -1),
                             p15=float(r.p15), p15_off=float(r.p15_off), q=float(r.q_rep)))
        mrows.append(dict(ts=ts, n_uni=len(uni), n_scored=len(sc), ready=ready, n_dup=ndup, n_pool=len(pool_syms),
                          n_map=len(uni_map), jacc=len(set(top_live) & set(top_off)) / len(set(top_live) | set(top_off)),
                          n_common=len(set(top_live) & set(top_off)), live_not_off=[s for s in top_live if s not in top_off],
                          off_not_live=[s for s in top_off if s not in top_live]))
    R = pd.DataFrame(rows); M = pd.DataFrame(mrows)
    R.to_csv(W + "/out_s1_%s.csv.gz" % mode, index=False); M.to_json(W + "/out_s1min_%s.json" % mode, orient="records")
    sp = []
    for ts, g in R.groupby("ts"):
        g2 = g.dropna(subset=["rank_off"])
        if len(g2) > 3:
            sp.append(g2.rank_live.corr(g2.rank_off, method="spearman"))
    sd = R.dropna(subset=["score_off"])
    gvd = R.dropna(subset=["gv_off"])
    out = dict(n_minutes=int(M.shape[0]), n_rows=int(len(R)),
               score=stats(sd.score_live, sd.score_off), score_exact_f32=float((sd.score_live.astype(np.float32) == sd.score_off.astype(np.float32)).mean()),
               jaccard=dict(mean=float(M.jacc.mean()), median=float(M.jacc.median()), min=float(M.jacc.min()), frac_eq1=float((M.jacc == 1).mean())),
               n_common_mean=float(M.n_common.mean()),
               spearman_rank=dict(mean=float(np.nanmean(sp)), median=float(np.nanmedian(sp)), min=float(np.nanmin(sp))) if sp else None,
               live_rank_off_rank_exact=float((R.rank_live == R.rank_off).mean()),
               gv=stats(gvd.gv_live, gvd.gv_off), gv_exact=float((gvd.gv_live.astype(np.float32) == gvd.gv_off.astype(np.float32)).mean()),
               gv_implied_found=float((R.k_implied > 0).mean()), k_implied_eq_k_off=float((R.k_implied == R.k_off).mean()),
               dup_scores=dict(minutes_with_dup=int((M.n_dup > 0).sum()), max_dup=int(M.n_dup.max())),
               uni=dict(n_uni_med=float(M.n_uni.median()), n_pool_med=float(M.n_pool.median()), n_map_med=float(M.n_map.median())))
    # theo phut-trong-gio (bien gio :00/:02 vs con lai)
    R["mm"] = (R.ts // MIN) % 60
    out["score_exact_by_mm"] = R.assign(ex=(R.score_live.astype(np.float32) == R.score_off.astype(np.float32))).groupby("mm").ex.mean().round(4).to_dict()
    out["jacc_by_mm"] = M.assign(mm=(M.ts // MIN) % 60).groupby("mm").jacc.mean().round(4).to_dict()
    res["modes"][mode] = out
    print("MODE", mode, json.dumps(out, default=str)[:3000], flush=True)
json.dump(res, open(W + "/par_b.json", "w"), indent=1, default=str)
print("JSON ->", W + "/par_b.json")
