#!/usr/bin/env python3
"""GATE_SMART Pha 0a (PREREG_GATE_SMART 6d92cdba) — CHI DO. Oracle, offline. Output ~/claude_master/gsmart/p0a.json"""
import sys, json, math, logging
import numpy as np, pandas as pd
sys.path.insert(0, '/home/ubuntu/claude_master/vz_e1_wt/research/analysis')
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("gsm")
OUT = '/home/ubuntu/claude_master/gsmart/'
H, D = GO.H, GO.D
TZ = 7 * H
PCTD = float(np.float32(0.999950829))
SEEDS = {"A1": "nt-x14-s42", "S7": "nt-x14-s7", "S13": "nt-x14-s13", "S21": "nt-x14-s21", "S99": "nt-x14-s99",
         "S123": "nt-x14-s123", "S777": "nt-x14-s777", "S2024": "nt-x14-s2024"}
DEV0, DEV1 = 1640970000000, 1767200400000

# ---- regime: RV 24h tu edge_attr index ----
Z = np.load('/home/ubuntu/claude_master/edge_attr/index.npz')
def rv_series(tk, rk):
    t = Z[tk].astype(np.int64); r = Z[rk].astype(np.float64)
    if t[0] < 10**12: t = t * 60000
    o = np.argsort(t); t, r = t[o], np.nan_to_num(r[o])
    cs = np.concatenate([[0.0], np.cumsum(r * r)])
    return t, cs
EW = rv_series('ew_ts', 'ew_r'); BT = rv_series('bt_ts', 'bt_r')
def rv_at(S, ts):
    t, cs = S
    e = np.searchsorted(t, ts, 'left'); b = np.searchsorted(t, ts - 1440 * 60000, 'left')
    n = e - b
    v = np.where(n >= 1200, np.sqrt((cs[e] - cs[b]) * 1440.0 / np.maximum(n, 1)), np.nan)
    return v
grid = np.arange(DEV0, DEV1, H)
EDGE = {nm: np.nanquantile(rv_at(S, grid), [1 / 3, 2 / 3]) for nm, S in (("ew", EW), ("bt", BT))}
COV = {nm: [int(S[0][0]), int(S[0][-1])] for nm, S in (("ew", EW), ("bt", BT))}
log.info("RV edges %s cov %s", EDGE, COV)


def seed_legs(arm, tag):
    B = dict(np.load(GO.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    C = GO.build(arm, B, s2id, tag)
    G = GO.run_g2(C, J=1024)
    x = GO.classify(C, G["P"])
    x = x[(x.s_ms >= DEV0) & (x.s_ms < DEV1)].copy()
    ts, P, r, qm, valid = C["ts"], G["P"], G["r"], G["qm"], C["valid"]
    hm = ts // H; h0 = int(hm.min())
    hp = np.bincount(hm - h0, weights=P.sum(1), minlength=int(hm.max()) - h0 + 1)
    BH = np.nonzero(hp >= 10)[0] + h0
    # episode: chuoi phut pass cach <= 3h
    pm = ts[P.any(1)]
    ep_start = np.empty(len(pm), np.int64); cur = None; last = None
    for i, t in enumerate(pm.tolist()):
        if last is None or t - last > 3 * H: cur = t
        ep_start[i] = cur; last = t
    # buffer de lay tuoi phan tu dat q
    rows, cols = np.nonzero(valid)
    vt = ts[rows]; vv = r[rows, cols].astype(np.float32)
    del rows, cols
    p = x[x.cat == "pass"].copy()
    ii = p.i.to_numpy(int); cc = p.c.to_numpy(int)
    p["r"] = r[ii, cc]; p["q"] = qm[ii]; p["rq"] = p.r / p.q; p["rank"] = cc + 1
    p["ts"] = ts[ii]
    # khoang cach toi BH truoc (gio)
    hl = p.ts.to_numpy(np.int64) // H
    j = np.searchsorted(BH, hl, 'right') - 1
    inb = np.isin(hl, BH)
    dist = np.where(j >= 0, (hl - BH[np.maximum(j, 0)]), 10**6).astype(float)
    # neu dang trong BH thi dist=0; nguoc lai so gio tu BH truoc
    p["b3"] = np.where(inb, "inBH", np.where(dist <= 24, "0-24h", np.where(dist <= 168, "24h-7d", ">7d")))
    k = np.searchsorted(pm, p.ts.to_numpy(np.int64)); k = np.clip(k, 0, len(pm) - 1)
    p["ep"] = ((ep_start[k] + TZ) // D)                         # cum = ngay (+07) bat dau dot -> chung giua seed
    p["rv_ew"] = rv_at(EW, p.ts.to_numpy(np.int64)); p["rv_bt"] = rv_at(BT, p.ts.to_numpy(np.int64))
    # tuoi ban ghi dat q (gio cua leg)
    age = {}
    for h in np.unique(hl).tolist():
        hh = h * H
        a, b = np.searchsorted(vt, hh - 90 * D, 'left'), np.searchsorted(vt, hh, 'left')
        m = b - a
        if m <= 1: continue
        jj = m - 1 - min(m - 1, int(math.floor(PCTD * (m - 1))))
        seg = vv[a:b]
        idx = np.argpartition(-seg, jj)[jj]
        age[h] = (hh - int(vt[a + idx])) / D
    p["age_d"] = [age.get(h, np.nan) for h in hl.tolist()]
    p["seed"] = arm
    log.info("%s: legs DEV %d pass %d (cat %s)", arm, len(x), len(p), x.cat.value_counts().to_dict())
    return p[["seed", "ts", "yr", "sym", "pnl", "r", "q", "rq", "rank", "b3", "ep", "rv_ew", "rv_bt", "age_d"]]


L = pd.concat([seed_legs(a, t) for a, t in SEEDS.items()], ignore_index=True)
L.to_parquet(OUT + "p0a_legs.parquet")
rng = np.random.default_rng(20261103)
eps = np.unique(L.ep.to_numpy())
gi = {e: np.nonzero(L.ep.to_numpy() == e)[0] for e in eps}
NB = 2000
BS = [np.concatenate([gi[e] for e in rng.choice(eps, len(eps), replace=True)]) for _ in range(NB)]
pnl = L.pnl.to_numpy(float)


def stat(mask):
    m = mask.to_numpy() if hasattr(mask, "to_numpy") else mask
    pt = float(np.nanmean(pnl[m])) if m.any() else float("nan")
    bs = [np.nanmean(pnl[b][m[b]]) if m[b].any() else np.nan for b in BS]
    lo, hi = np.nanpercentile(bs, [5, 95])
    return dict(n=int(m.sum()), mean=round(pt, 2), med=round(float(np.nanmedian(pnl[m])), 2) if m.any() else None, ci90=[round(lo, 2), round(hi, 2)]), np.array(bs)


def diff(ma, mb):
    a, ba = stat(ma); b, bb = stat(mb)
    d = ba - bb; lo, hi = np.nanpercentile(d, [5, 95])
    return dict(a=a, b=b, diff=round(a["mean"] - b["mean"], 2), ci90=[round(lo, 2), round(hi, 2)])


R = dict(prereg="6d92cdba", n_legs=len(L), n_eps=int(len(eps)), cluster="ngay(+07) bat dau dot, chung 8 seed", rv_edges={k: v.tolist() for k, v in EDGE.items()},
         rv_cov=COV, all=stat(np.ones(len(L), bool))[0])
rqb = pd.cut(L.rq, [1, 1.1, 1.25, 1.5, 2, np.inf], right=False)
R["B1"] = {str(k): stat(rqb == k)[0] for k in rqb.cat.categories}
s1a = R["B1"]["[1.0, 1.1)"]
s1b = diff(rqb == rqb.cat.categories[-1], rqb == rqb.cat.categories[0])
R["S1"] = dict(low_bucket=s1a, top_minus_low=s1b,
               HOLD=bool(s1a["ci90"][1] < 0 or (s1b["ci90"][0] > 0 and s1b["diff"] >= 0.5 * R["all"]["mean"])))
for nm in ("ew", "bt"):
    tv = np.digitize(L["rv_" + nm], EDGE[nm])
    R["B2_" + nm] = {str(t): stat(tv == t)[0] for t in (0, 1, 2)}
    d = diff(tv == 2, tv == 0)
    yrs = {}
    for y in (2022, 2023, 2024, 2025):
        my = (L.yr == y).to_numpy()
        a, b = pnl[(tv == 2) & my], pnl[(tv == 0) & my]
        yrs[y] = round(float(np.nanmean(a) - np.nanmean(b)), 2) if len(a) and len(b) else None
    sgn = np.sign(d["diff"])
    d["by_year"] = yrs; d["same_sign_years"] = int(sum(1 for v in yrs.values() if v is not None and np.sign(v) == sgn))
    d["HOLD"] = bool((d["ci90"][0] > 0 or d["ci90"][1] < 0) and d["same_sign_years"] >= 3)
    R["S2_" + nm] = d
R["S2"] = dict(HOLD=R["S2_ew"]["HOLD"], note="quyet dinh theo ALT_EW (bien cua V-b); BTC chi mo ta")
R["B3"] = {k: stat(L.b3 == k)[0] for k in ("inBH", "0-24h", "24h-7d", ">7d")}
R["B4"] = {k: stat(m)[0] for k, m in (("1-4", L["rank"] <= 4), ("5-12", (L["rank"] >= 5) & (L["rank"] <= 12)), ("13-24", L["rank"] >= 13))}
ab = pd.cut(L.age_d, [0, 7, 30, 60, 90.01], right=False)
R["B5"] = {str(k): stat(ab == k)[0] for k in ab.cat.categories}
s3 = diff(ab == ab.cat.categories[-1], ab == ab.cat.categories[0]); s3["HOLD"] = bool(s3["ci90"][0] > 0 or s3["ci90"][1] < 0)
R["S3"] = s3
R["B6"] = {int(y): stat(L.yr == y)[0] for y in (2022, 2023, 2024, 2025)}
R["S4"] = "Pha 0b (kernel near-miss) — chua do"
R["S5"] = dict(HOLD=False, src="GATE_STAB M 026bb92c")
json.dump(R, open(OUT + "p0a.json", "w"), indent=1, default=str)
print(json.dumps({k: R[k] for k in ("n_legs", "n_eps", "all", "S1", "S2", "S3")}, indent=1, default=str))
