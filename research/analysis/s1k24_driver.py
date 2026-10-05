#!/usr/bin/env python3
"""S1_K24 — driver: step0 (rank-band) | g1 (MAP_PARITY + map arm) | edge (G2 offline) | upload | submit | status |
fetch | parity | score. Pre-reg docs/prereg/PREREG_S1_K24.md (commit 15ec9e18, chot TRUOC do).
Arm (k=3): ARM-A GEOM@K24 (G42=n700-a3 + G7), ARM-B OBJ24 (B42,B7), ARM-C OBJ24+GEOM (C42,C7); nen CTRL4@K24 (K42,S7,S13,S21).
Sim: Kaggle, tools/kaggle_sim.py HEAD (NOWRITE242, md5 8b60b00a), template label_firsthit_sim (duong s1rn/geom/n700-A3),
B0OV + SELECTOR_RANK_TOPK=24. Thuoc: MTM ngay paired block-10d NREP 2000 seed 20260905, inflate sqrt(2 ln 3).
THUAN PYTHON; 0 Java tren Oracle; 0 cham 242/shadow; DEV <= 2025.
"""
import argparse
import glob
import hashlib
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import selector_ablation_driver as SAD  # noqa: E402
import selector_ablation_scores as SAS  # noqa: E402
import s1_retrain_noise_sim as RN  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("s1k24")
W = "/home/ubuntu/claude_master/1004/s1k24"
PRED = W + "/pred"
PREREG_COMMIT = "15ec9e18"
K_INFL = 3
INFL = math.sqrt(2.0 * math.log(K_INFL))      # 1.4823
SAD.INFL, SAD.K_INFL = INFL, K_INFL
NREP, SEED, BLOCK_D = 2000, 20260905, 10
OV = dict(SAD.B0OV)
OV["SELECTOR_RANK_TOPK"] = 24
CTRL = ["K42", "S7", "S13", "S21"]
ARMS = {"CTRL4": CTRL, "ARM-A": ["G42", "G7"], "ARM-B": ["B42", "B7"], "ARM-C": ["C42", "C7"]}
GO_ARMS = ["ARM-A", "ARM-B", "ARM-C"]
NEWRUNS = CTRL + ["G7", "B42", "B7", "C42", "C7"]
TAG = {r: "s1k24-" + r.lower() for r in NEWRUNS}
TAG.update({"G42": "n700-a3", "A1": "n700-a1"})
DSN = {r: "s1rn-bins-" + r.lower() for r in CTRL}
DSN.update({"G7": "geom-bins-g7", "G42": "geom-bins-g42"})
DSN.update({r: "s1k24-bins-" + r.lower() for r in ("B42", "B7", "C42", "C7")})
SHA_RN = json.load(open("/home/ubuntu/claude_master/1003/s1rn/sim_sha256.json"))
SHA_GEOM = json.load(open("/home/ubuntu/claude_master/1003/geom/sim_sha256.json"))
SHA_JSON = W + "/sim_sha256.json"
MTM_CACHE = W + "/mtm.json"
JSON_OUT = os.path.join(REPO, "docs/result/s1k24.json")
STEP0_JSON = os.path.join(REPO, "docs/audit/RANKBAND_K24_20261004.json")
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
W0 = pd.Timestamp("2021-12-31")
YEARS = [2022, 2023, 2024, 2025]
DEPLOY = RN.F0MAP
MOC21 = RN.MOC21
REC = SAS.REC
TZ_MS = 7 * 3600000


def want_sha(r):
    if r in CTRL:
        return SHA_RN[r]
    if r in ("G42", "G7"):
        return SHA_GEOM[r]
    return json.load(open(SHA_JSON))[r]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ G1: map
def pred_src(r):
    if r in CTRL:
        return "/home/ubuntu/claude_master/1003/s1rn/kout/pred_%s.parquet" % r
    if r in ("G42", "G7"):
        return "/home/ubuntu/claude_master/1003/geom/kout/pred_%s.parquet" % r
    return PRED + "/pred_%s.parquet" % r


def map_arm(r):
    """pred -> sanity (= RN.prep) -> pred tam int64/float32 -> x1_build_map s1a2x1 (G015 = bins deploy) -> map_<r>."""
    P, O = pd.read_parquet(pred_src(r), columns=["ts", "sym", "score"]), RN.load_pred("ORIG")
    assert np.isfinite(P.score).all() and not P.duplicated(["ts", "sym"]).any()
    J = O[["ts", "sym"]].merge(P[["ts", "sym"]], on=["ts", "sym"], how="inner")
    fo, fp = np.bincount(RN.fold_of(O.ts), minlength=16), np.bincount(RN.fold_of(P.ts), minlength=16)
    ok = len(P) == len(O) == len(J) and (fo == fp).all() and RN.fold_of(P.ts).min() >= 0
    log.info("PREP %s rows %d orig %d join %d -> %s", r, len(P), len(O), len(J), "OK" if ok else "*** FAIL ***")
    assert ok
    os.makedirs(W + "/mpred", exist_ok=True)
    name = "s1a2x1k24" + r
    dst = W + "/mpred/pred_%s.parquet" % name
    P.astype({"ts": "int64", "sym": "int64", "score": "float32"}).to_parquet(dst, index=False)
    lk = "/home/ubuntu/ledger/pred_%s.parquet" % name
    if not os.path.lexists(lk):
        os.symlink(dst, lk)
    out = W + "/map_" + r
    RN.build_map(name, out)
    assert len(RN.md5dir(out)) == 16
    return SAS.sha256_concat(SAS.src_files([out, MOC21]))


def co_score(outfile):
    return {ln.split()[1]: float(ln.split()[6]) for ln in open(outfile) if " co score " in ln}


def check_map(r):
    """G1-c: tung file cung so dong + (ts,sym) cung thu tu voi deploy, p1..p3 y het, multiset p0 theo tick y het,
    ty le 'co score' == ban kiem ORIG."""
    out, res = W + "/map_" + r, {}
    ref = co_score(W + "/map_ORIGchk.out")
    cs = co_score(out + ".out")
    for f in sorted(glob.glob(DEPLOY + "/predict_wf_*.bin")):
        b = os.path.basename(f)
        a, d = SAS.read_rec(out + "/" + b), SAS.read_rec(f)
        ok = len(a) == len(d) and np.array_equal(a["ts"], d["ts"]) and np.array_equal(a["sym"], d["sym"])
        ok = ok and all(np.array_equal(a[c], d[c], equal_nan=True) for c in ("p1", "p2", "p3"))
        if ok:
            ts = a["ts"].astype(np.int64)
            oa, od = np.lexsort((a["p0"], ts)), np.lexsort((d["p0"], ts))
            ok = np.array_equal(a["p0"][oa], d["p0"][od])
        res[b] = dict(ok=bool(ok), co_score=cs.get(b), co_score_ref=ref.get(b),
                      changed=float((a["p0"] != d["p0"]).mean()) if len(a) == len(d) else None)
        res[b]["ok"] = res[b]["ok"] and cs.get(b) == ref.get(b)
    allok = len(res) == 16 and all(v["ok"] for v in res.values())
    log.info("CHECK_MAP %s %s", r, "PASS" if allok else "*** FAIL ***")
    return allok, res


def g1(runs):
    sh = json.load(open(SHA_JSON)) if os.path.exists(SHA_JSON) else {}
    rep = json.load(open(W + "/g1.json")) if os.path.exists(W + "/g1.json") else {}
    if "a_mapparity" not in rep:
        assert RN.sha256f(RN.ORIG_PRED) == RN.ORIG_SHA
        RN.build_map("s1a2x1", W + "/map_ORIGchk")
        a, b = RN.md5dir(W + "/map_ORIGchk"), RN.md5dir(DEPLOY)
        rep["a_mapparity"] = dict(ok=len(a) == 16 and a == b, n_eq=sum(a.get(k) == v for k, v in b.items()))
        log.info("G1a MAP_PARITY %s", rep["a_mapparity"])
    for r in runs:
        s = map_arm(r)
        sh[r] = s
        if r in ("G42", "G7"):
            rep["b_regen_" + r] = dict(ok=s == SHA_GEOM[r], sha=s, want=SHA_GEOM[r])
            log.info("G1b %s %s", r, rep["b_regen_" + r])
        ok, det = check_map(r)
        rep["c_" + r] = dict(ok=ok, sha=s, files=det)
    json.dump(sh, open(SHA_JSON, "w"), indent=1)
    json.dump(rep, open(W + "/g1.json", "w"), indent=1)
    return all(v["ok"] for v in rep.values())


# ------------------------------------------------------------------ STEP 0: rank-band
BANDS = [(0, 8, "1-8"), (8, 16, "9-16"), (16, 24, "17-24"), (24, 10 ** 9, ">24")]


def bins_index(dirs):
    """Gom 18 file bins -> (key = ts*4096+sym sap xep, rank 0.. theo R50 rank_in_ts, sc = f32(1)-p0, ticks duy nhat)."""
    import selector_ablation_topm as SAT
    K, Rk, Sc = [], [], []
    for f in SAS.src_files(dirs):
        a = SAS.read_rec(f)
        r = SAT.rank_in_ts(a)
        K.append(a["ts"].astype(np.int64) * 4096 + a["sym"].astype(np.int64))
        Rk.append(r.astype(np.int32))
        Sc.append((np.float32(1.0) - a["p0"].astype(np.float32)))
    K, Rk, Sc = np.concatenate(K), np.concatenate(Rk), np.concatenate(Sc)
    o = np.argsort(K, kind="stable")
    K, Rk, Sc = K[o], Rk[o], Sc[o]
    assert (np.diff(K) > 0).all(), "trung (ts,sym) giua cac file"
    return K, Rk, Sc, np.unique(K // 4096)


def load_pd(tag):
    d = pd.read_csv(OUT % tag + "storage/printDone.csv")
    d.columns = [c.strip() for c in d.columns]
    d = d[d.side == "BUY"].copy()
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["ms"] = ((d["t0"] - pd.Timedelta(hours=7)).astype("datetime64[ns]").astype("int64") // 10 ** 6).astype(np.int64)
    d["yr"] = d["t0"].dt.year
    d["win"] = (d["profit"] > 0).astype(int)
    d["sl"] = (d["status"].astype(str) == "STOP_LOSS_DONE").astype(int)
    k = d["sym"].astype(str) + "|" + d["start"].astype(str) + "|" + d["level"].astype(str)
    d["key"] = k + "#" + d.groupby(k).cumcount().astype(str)
    return d


def join_rank(d, IDX, symmap):
    """Tick bins 15' lon nhat <= entry (lag 0) va tick truoc do (lag 1); chon lag theo ti le khop symbolPred."""
    K, Rk, Sc, T = IDX
    sid = d["sym"].astype(str).add("USDT").map(symmap)
    d["symId"] = sid
    i0 = np.searchsorted(T, d["ms"].to_numpy(), side="right") - 1
    best = None
    for lag in (0, 1):
        ii = np.clip(i0 - lag, 0, len(T) - 1)
        key = T[ii] * 4096 + np.nan_to_num(sid.to_numpy(float), nan=0).astype(np.int64)
        j = np.clip(np.searchsorted(K, key), 0, len(K) - 1)
        hit = (K[j] == key) & sid.notna().to_numpy()
        sc = np.where(hit, Sc[j], np.nan)
        m = hit & (np.abs(sc - d["symbolPred"].to_numpy(float)) < 1e-6)
        if best is None or m.mean() > best[0]:
            best = (m.mean(), lag, np.where(hit, Rk[j], -1), m, hit)
    rate, lag, rk, m, hit = best
    d["rank"] = rk
    d["sp_match"] = m
    d["band"] = "NA"
    for lo, hi, nm in BANDS:
        d.loc[hit & (rk >= lo) & (rk < hi), "band"] = nm
    return d, dict(lag=int(lag), match_symbolPred=float(rate), hit=float(hit.mean()), sym_unmapped=int(sid.isna().sum()))


def band_stats(d, by=None):
    def f(g):
        return dict(n=int(len(g)), sum_pnl=float(g.pnl.sum()), pnl_leg=float(g.pnl.mean()) if len(g) else None,
                    roi_leg=float(g.profit.mean()) if len(g) else None, win=float(100 * g.win.mean()) if len(g) else None,
                    sl=float(100 * g.sl.mean()) if len(g) else None)
    out = {}
    keys = ["band"] + ([by] if by else [])
    for k, g in d.groupby(keys):
        out["|".join(str(x) for x in (k if isinstance(k, tuple) else (k,)))] = f(g)
    return out


def step0():
    symmap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv").set_index("symbol")["symId"]
    runs = {"A1_B0K24": ("n700-a1", "deploy"), "A3_G42K24": ("n700-a3", "G42"),
            "B0_K16": ("n700-b0ref", "deploy"), "G42_K16": ("geom-g42", "G42")}
    idx = {"deploy": bins_index([DEPLOY, MOC21]), "G42": bins_index([W + "/map_G42", MOC21])}
    res, D = {"runs": {}}, {}
    for nm, (tag, bk) in runs.items():
        d = load_pd(tag)
        d, jm = join_rank(d, idx[bk], symmap)
        D[nm] = d
        pr = d[d.level == "PREDICT_SYMBOL_TRADE"]
        res["runs"][nm] = dict(tag=tag, bins=bk, md5=md5f(OUT % tag + "storage/printDone.csv"), n=int(len(d)),
                               join=jm, rank_q=d.loc[d["rank"] >= 0, "rank"].describe().to_dict(),
                               all=band_stats(d), predict=band_stats(pr), predict_year=band_stats(pr, "yr"),
                               level=band_stats(d, "level"), all_year=band_stats(d, "yr"),
                               join_by_level={lv: dict(n=int(len(g)), match_symbolPred=float(g.sp_match.mean()),
                                                       rank_max=int(g["rank"].max()))
                                              for lv, g in d.groupby("level")})
        log.info("STEP0 %s join %s", nm, jm)
        for b, v in res["runs"][nm]["predict"].items():
            log.info("   %-6s n %4d SumPnL %9.0f pnl/leg %7.1f roi %5.2f win %5.1f sl %5.1f", b, v["n"], v["sum_pnl"],
                     v["pnl_leg"], v["roi_leg"], v["win"], v["sl"])
    # tap lenh moi o K24 (co o K24, khong co o K16) — theo khoa sym|start|level#cumcount
    for k24, k16 in (("A1_B0K24", "B0_K16"), ("A3_G42K24", "G42_K16")):
        a, b = D[k24], D[k16]
        new = a[~a.key.isin(set(b.key))]
        com = a[a.key.isin(set(b.key))]
        gone = b[~b.key.isin(set(a.key))]
        res["new_" + k24] = dict(n=int(len(new)), sum_pnl=float(new.pnl.sum()), roi_leg=float(new.profit.mean()),
                                 win=float(100 * new.win.mean()), sl=float(100 * new.sl.mean()),
                                 by_year={int(y): dict(n=int(len(g)), sum_pnl=float(g.pnl.sum()),
                                                       roi_leg=float(g.profit.mean())) for y, g in new.groupby("yr")},
                                 band=band_stats(new), band_year=band_stats(new, "yr"),
                                 by_level=band_stats(new, "level"),
                                 predict=band_stats(new[new.level == "PREDICT_SYMBOL_TRADE"]),
                                 predict_year=band_stats(new[new.level == "PREDICT_SYMBOL_TRADE"], "yr"),
                                 common_predict=band_stats(com[com.level == "PREDICT_SYMBOL_TRADE"]),
                                 gone_predict=band_stats(gone[gone.level == "PREDICT_SYMBOL_TRADE"]),
                                 common=dict(n=int(len(com)), sum_pnl=float(com.pnl.sum()), roi_leg=float(com.profit.mean())),
                                 gone_from_k16=dict(n=int(len(gone)), sum_pnl=float(gone.pnl.sum()),
                                                    roi_leg=float(gone.profit.mean())))
        log.info("NEW %s vs %s: n %d SumPnL %.0f roi %.2f | common n %d | gone n %d SumPnL %.0f", k24, k16, len(new),
                 new.pnl.sum(), new.profit.mean(), len(com), len(gone), gone.pnl.sum())
    # A3 vs A1 tung dai
    A1, A3 = res["runs"]["A1_B0K24"]["predict"], res["runs"]["A3_G42K24"]["predict"]
    res["A3_minus_A1_band"] = {b: dict(d_n=A3[b]["n"] - A1.get(b, {}).get("n", 0),
                                       d_sum_pnl=A3[b]["sum_pnl"] - A1.get(b, {}).get("sum_pnl", 0.0),
                                       d_roi_leg=(A3[b]["roi_leg"] - A1[b]["roi_leg"]) if b in A1 else None)
                               for b in A3}
    G1, G3 = res["runs"]["G42_K16"]["predict"], res["runs"]["B0_K16"]["predict"]
    res["G42K16_minus_B0K16_band"] = {b: dict(d_n=G1[b]["n"] - G3.get(b, {}).get("n", 0),
                                              d_sum_pnl=G1[b]["sum_pnl"] - G3.get(b, {}).get("sum_pnl", 0.0))
                                      for b in G1}
    json.dump(res, open(STEP0_JSON, "w"), indent=1, default=str)
    log.info("A3-A1 band %s", {b: round(v["d_sum_pnl"]) for b, v in res["A3_minus_A1_band"].items()})
    log.info("JSON -> %s", STEP0_JSON)


# ------------------------------------------------------------------ G2: edge offline
EDGE_RUNS = ["ORIG", "G0K42", "K42", "S7", "S13", "S21", "G42", "G7", "B42", "B7", "C42", "C7"]
EDGE_PAIRS = [("B42", "K42"), ("B7", "S7"), ("C42", "K42"), ("C7", "S7"), ("C42", "G42"), ("C7", "G7"),
              ("B42", "ORIG"), ("G42", "K42"), ("G7", "S7")]


def edge():
    L = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts", "sym", "g1lite"])
    L = L[L.g1lite.notna()]
    M = None
    for r in EDGE_RUNS:
        p = RN.ORIG_PRED if r == "ORIG" else pred_src(r)
        if not os.path.exists(p):
            continue
        P = pd.read_parquet(p, columns=["ts", "sym", "score"]).rename(columns={"score": r})
        M = P if M is None else M.merge(P, on=["ts", "sym"], how="inner")
    runs = [c for c in M.columns if c not in ("ts", "sym")]
    M = M.merge(L, on=["ts", "sym"], how="left")
    assert M.g1lite.notna().all()
    g = M.groupby("ts")
    M["n"] = g.ts.transform("size")
    M = M[M.n >= 25].copy()
    g = M.groupby("ts")
    mu = g.g1lite.transform("mean").to_numpy()
    tick = M.ts.to_numpy()
    E = {}
    for r in runs:
        rk = g[r].rank(method="first").to_numpy()
        for nm, lo, hi in (("e5", 1, 5), ("e8", 1, 8), ("e16", 1, 16), ("e24", 1, 24), ("b17_24", 17, 24)):
            v = np.where((rk >= lo) & (rk <= hi), M.g1lite.to_numpy() - mu, np.nan)
            E[(r, nm)] = 100 * pd.Series(v).groupby(tick).mean()
    yr = pd.to_datetime(E[(runs[0], "e24")].index.to_numpy(), unit="ms").year
    out = {"n_ticks": int(len(E[(runs[0], "e24")])), "rows": int(len(M)), "runs": {}, "pairs": {}}
    for r in runs:
        out["runs"][r] = {nm: dict(all=float(E[(r, nm)].mean()),
                                   year={int(y): float(E[(r, nm)][yr == y].mean()) for y in sorted(set(yr))})
                          for nm in ("e5", "e8", "e16", "e24", "b17_24")}
        log.info("EDGE %-6s e5 %+.3f e8 %+.3f e16 %+.3f e24 %+.3f b17-24 %+.3f", r,
                 *[out["runs"][r][nm]["all"] for nm in ("e5", "e8", "e16", "e24", "b17_24")])
    blk = (E[(runs[0], "e24")].index.to_numpy() // (72 * 3600000))
    ub, inv = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(SEED)
    picks = [rng.integers(0, len(ub), size=len(ub)) for _ in range(NREP)]
    for x, y in EDGE_PAIRS:
        if x not in runs or y not in runs:
            continue
        res = {}
        for nm in ("e24", "b17_24", "e8"):
            dd = (E[(x, nm)] - E[(y, nm)]).to_numpy()
            s = np.bincount(inv, weights=dd, minlength=len(ub))
            c = np.bincount(inv, minlength=len(ub)).astype(float)
            bs = np.array([s[p].sum() / c[p].sum() for p in picks])
            res[nm] = dict(d=float(np.mean(dd)), ci_raw=[float(v) for v in np.percentile(bs, [2.5, 97.5])],
                           year={int(yy): float(dd[yr == yy].mean()) for yy in sorted(set(yr))})
        out["pairs"][x + "-" + y] = res
        log.info("dEDGE %-9s e24 %+.3f %s b17-24 %+.3f", x + "-" + y, res["e24"]["d"],
                 [round(v, 3) for v in res["e24"]["ci_raw"]], res["b17_24"]["d"])
    g2 = {}
    for arm, pr in (("ARM-B", [("B42", "K42"), ("B7", "S7")]), ("ARM-C", [("C42", "K42"), ("C7", "S7")])):
        ds = [out["pairs"][x + "-" + y]["e24"]["d"] for x, y in pr if x + "-" + y in out["pairs"]]
        g2[arm] = dict(mean_d_e24=float(np.mean(ds)) if ds else None, n=len(ds), ok=bool(ds and np.mean(ds) > 0))
    out["G2"] = g2
    log.info("G2 %s", g2)
    json.dump(out, open(W + "/edge.json", "w"), indent=1)


# ------------------------------------------------------------------ Kaggle
def ks_mod():
    from tools import kaggle_sim as ks
    md5 = md5f(os.path.join(REPO, "tools/kaggle_sim.py"))
    assert md5 == SAD.KS_MD5_WANT, ("tools/kaggle_sim.py khong phai HEAD NOWRITE242", md5)
    assert "NOWRITE_HOST" in ks.KERNEL_TEMPLATE and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in ks.KERNEL_TEMPLATE
    return ks


def upload(r):
    ks = ks_mod()
    fol = W + "/ds_sim_" + r
    os.makedirs(fol, exist_ok=True)
    fs = sorted(glob.glob(W + "/map_" + r + "/predict_wf_*.bin"))
    assert len(fs) == 16, len(fs)
    for f in fs:
        dst = os.path.join(fol, os.path.basename(f))
        if not os.path.exists(dst):
            os.link(f, dst)
    json.dump({"title": DSN[r], "id": ks.USER + "/" + DSN[r], "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(fol, "dataset-metadata.json"), "w"))
    res = ks._api().dataset_create_new(fol, public=False, quiet=False, dir_mode="skip")
    log.info("upload %s -> %s", r, getattr(res, "url", res))


def submit(r, code_sha):
    import label_firsthit_sim as LFS
    ks = ks_mod()
    assert r in NEWRUNS
    sha = want_sha(r)
    tag = TAG[r]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": SAD.PROFILE, "overrides": dict(OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": code_sha, "bins_ds": "", "jar_ds": SAD.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": "P0", "fh_arm": r, "fh_ds": DSN[r], "want_bins_sha": sha, "src_bins_sha": sha,
           "moc21_ds": SAD.MOC21_DS, "liq_ds": SAD.LIQ_DS, "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = LFS.template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + SAD.BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + SAD.JAR_DS, ks.USER + "/" + SAD.MOC21_DS, ks.USER + "/" + DSN[r]],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    res = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s sha %s ov %s", r, getattr(res, "url", res), sha[:8], json.dumps(OV))


def result_json(tag):
    p = OUT % tag + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def prof_run(tag):
    p, out = OUT % tag + "prof_run.properties", {}
    if os.path.exists(p):
        for ln in open(p):
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.rstrip("\n").split("=", 1)
                out[k.strip()] = v.strip()
    return out


def parity_run(r):
    import reset_rule_score as R
    tag = TAG[r]
    if not os.path.exists(OUT % tag + "storage/printDone.csv"):
        return dict(ok=False, why="chua co printDone")
    rj, pr = result_json(tag), prof_run(tag)
    sel = rj.get("sel") or {}
    chk = dict(jar=rj.get("jar_sha256") == SAD.JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
               topk24=pr.get("SELECTOR_RANK_TOPK") == "24")
    if r != "A1":
        chk["bins_ok"] = sel.get("bins_ok") is True and sel.get("bins_sha256") == want_sha(r)
    out = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=int(len(R.load_legs(tag))),
               eq=float(R.load_daily(tag)["equity"].iloc[-1]))
    log.info("PARITY %-4s %-12s %s n=%d eq=%.0f md5=%s %s", r, tag, "PASS" if out["ok"] else "*** VOID ***", out["n"],
             out["eq"], out["md5"][:8], chk)
    return out


# ------------------------------------------------------------------ score
def gmean(vals):
    v = [x for x in vals if x is not None and np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def pnl_days(L, days):
    s = L.groupby(L["te"].dt.normalize())["pnl"].sum()
    return s.reindex(days).fillna(0.0).to_numpy()


def group_pnl_boot(legs, idx, groups, pairs):
    days = idx[1:]
    P = {g: np.mean([pnl_days(legs[r], days) for r in mem], axis=0) for g, mem in groups.items() if mem}
    T = len(days)
    nb = int(math.ceil(T / BLOCK_D))
    rng = np.random.default_rng(SEED)
    picks = []
    for _ in range(NREP):
        st = rng.integers(0, T - BLOCK_D + 1, size=nb)
        picks.append((st[:, None] + np.arange(BLOCK_D)[None, :]).ravel()[:T])
    out = {}
    for x, y in pairs:
        if x in P and y in P:
            d = P[x] - P[y]
            bs = np.array([d[p].sum() for p in picks])
            lo, hi = np.percentile(bs, [2.5, 97.5])
            obs = float(d.sum())
            out[x + "-" + y] = dict(d=obs, ci_raw=[float(lo), float(hi)],
                                    ci_infl=[float(obs - (obs - lo) * INFL), float(obs + (hi - obs) * INFL)])
    return out


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    import n700_driver as N7
    R.MTM_COSTS = {"legacy": R.LEGACY}
    runs = [r for a in ARMS.values() for r in a] + ["A1"]
    par = {r: parity_run(r) for r in runs}
    keys = [r for r in runs if par[r]["ok"]]
    groups = {a: [r for r in mem if r in keys] for a, mem in ARMS.items()}
    for r in keys:
        groups[r] = [r]
    legs = {r: R.load_legs(TAG[r]) for r in keys}
    daily = {r: R.load_daily(TAG[r]) for r in keys}
    md5 = {r: par[r]["md5"] for r in keys}
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    miss = {r: legs[r] for r in keys if r not in raw or raw[r].get("md5") != md5[r]}
    log.info("MTM can tinh %s", sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for r, vv in new.items():
            vv["md5"] = md5[r]
            raw[r] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    N7.TAG.update({r: TAG[r] for r in keys})
    N7.DESC.update({r: r for r in keys})
    M = {r: N7.arm_metrics(R, F3, r, legs[r], daily[r], raw[r]["legacy"]) for r in keys}
    for r in keys:
        M[r]["md5"] = md5[r]
    eqs = {r: daily[r]["equity"][daily[r]["equity"].index >= W0] for r in keys}
    idx = eqs["A1"].index
    for r in keys:
        assert len(eqs[r]) == len(idx) and (eqs[r].index == idx).all(), ("lech chi so ngay", r)
    eqs["P0"] = eqs["A1"]
    obs, bs = SAD.daily_boot(eqs)
    mets = ("cagr", "mdd", "calmar", "sharpe")
    gobs = {g: {m: gmean([obs[r][m] for r in mem]) for m in mets} for g, mem in groups.items() if mem}
    gbs = {g: {m: np.mean([bs[r][m] for r in mem], axis=0) for m in mets} for g, mem in groups.items() if mem}
    pairs = [(a, "CTRL4") for a in GO_ARMS] + [("B42", "A1"), ("ARM-A", "A1"), ("A1", "CTRL4"), ("ARM-C", "ARM-B"),
                                               ("ARM-C", "ARM-A")] + [(r, "CTRL4") for r in keys if r != "A1"]
    pairs = [(x, y) for x, y in pairs if x in gobs and y in gobs]
    con = {x + "-" + y: {m: SAD.ci_of(gobs[x][m] - gobs[y][m], gbs[x][m] - gbs[y][m]) for m in mets} for x, y in pairs}
    dp = group_pnl_boot(legs, idx, groups, pairs)
    for x, y in pairs:
        con[x + "-" + y]["pnl"] = dp[x + "-" + y]
    finish(M, groups, gobs, con, par, legs)


def gtab(M, mem):
    """Bang nhom = TB cac seed (n/nam, CAGR22, maxDD MTM (min qua seed + TB), Calmar22, UW, win/SL 2022+, nam, quy)."""
    x = {q: gmean([M[r][q] for r in mem]) for q in ("n_per_year", "cagr22", "cagr", "dd_mtm", "dd_mtm22", "calmar22",
                                                  "uw_mtm", "win22", "sl22", "roi_lenh", "sum_pnl_2022_25")}
    x["dd_mtm_worst"] = float(min(M[r]["dd_mtm"] for r in mem))
    x["dd_mtm22_worst"] = float(min(M[r]["dd_mtm22"] for r in mem))
    x["roi_year"] = {y: gmean([M[r]["roi_year"].get(y) for r in mem]) for y in YEARS}
    x["per_year"] = {y: {q: gmean([M[r]["per_year"].get(y, {}).get(q) for r in mem])
                         for q in ("n", "sum_pnl", "dd_mtm_year", "win", "sl")} for y in YEARS}
    x["cum_2022_24"] = gmean([100 * (np.prod([1 + M[r]["roi_year"].get(y, np.nan) / 100 for y in (2022, 2023, 2024)]) - 1)
                              for r in mem])
    return x


def quarters(legs, mem):
    out = {}
    for r in mem:
        L = legs[r][(legs[r]["te"] >= "2022-01-01") & (legs[r]["te"] < "2026-01-01")]
        for q, v in L.groupby(L["te"].dt.to_period("Q"))["pnl"].sum().items():
            out.setdefault(str(q), []).append(float(v))
    return {q: float(np.mean(v)) for q, v in sorted(out.items())}


def finish(M, groups, gobs, con, par, legs):
    G = {g: gtab(M, mem) for g, mem in groups.items() if mem}
    Q = {g: quarters(legs, mem) for g, mem in groups.items() if mem and g in ARMS}
    c = G["CTRL4"]
    rule = {}
    for a in GO_ARMS:
        if a not in G:
            continue
        x, k = G[a], con[a + "-CTRL4"]
        dy = {y: x["roi_year"][y] - c["roi_year"][y] for y in YEARS}
        r = {"C1_dCAGR22_CIinfl>0": dict(ok=bool(k["cagr"]["d"] > 0 and k["cagr"]["ci_infl"][0] > 0), **k["cagr"]),
             "C2_maxDD_MTM>=-40_moi_seed": dict(ok=bool(x["dd_mtm_worst"] >= -40 and x["dd_mtm22_worst"] >= -40),
                                               worst=x["dd_mtm_worst"], worst22=x["dd_mtm22_worst"]),
             "C3_Calmar22>=0.90xCTRL4": dict(ok=bool(x["calmar22"] >= 0.90 * c["calmar22"]), arm=x["calmar22"],
                                             ctrl=c["calmar22"], ratio=x["calmar22"] / c["calmar22"]),
             "C4_>=3/4_nam_dROI>=0": dict(ok=bool(sum(v >= 0 for v in dy.values()) >= 3), dROI=dy,
                                          n_ok=int(sum(v >= 0 for v in dy.values())))}
        r["C5_bao_cao_cum2022_24>=0"] = dict(ok=bool(x["cum_2022_24"] - c["cum_2022_24"] >= 0),
                                             d=x["cum_2022_24"] - c["cum_2022_24"])
        r["dPnL"] = k["pnl"]
        r["n_seed"] = len(groups[a])
        r["GO"] = bool(all(v["ok"] for kk, v in r.items() if kk[:2] in ("C1", "C2", "C3", "C4")) and len(groups[a]) == 2)
        rule[a] = r
    log.info("%-6s %6s %6s %7s %7s %6s %5s %5s %5s", "nhom", "n/nam", "CAGR22", "ddMTM", "ddWorst", "Cal22", "UW", "win", "SL")
    for g, x in G.items():
        log.info("%-6s %6.0f %6.2f %7.2f %7.2f %6.3f %5.0f %5.1f %5.1f | ROI %s", g, x["n_per_year"], x["cagr22"],
                 x["dd_mtm"], x["dd_mtm_worst"], x["calmar22"], x["uw_mtm"], x["win22"], x["sl22"],
                 {y: round(v, 1) for y, v in x["roi_year"].items()})
    for cc, d in con.items():
        log.info("CON %-14s dCAGR %+.2f raw %s infl %s | dPnL %+.0f raw %s infl %s", cc, d["cagr"]["d"],
                 [round(v, 2) for v in d["cagr"]["ci_raw"]], [round(v, 2) for v in d["cagr"]["ci_infl"]], d["pnl"]["d"],
                 [round(v) for v in d["pnl"]["ci_raw"]], [round(v) for v in d["pnl"]["ci_infl"]])
    for a, r in rule.items():
        log.info("RULE %s GO=%s %s", a, r["GO"], {kk: v["ok"] for kk, v in r.items() if kk[:1] == "C"})
    js = dict(prereg="docs/prereg/PREREG_S1_K24.md", prereg_commit=PREREG_COMMIT, k_infl=K_INFL, inflate=INFL,
              nrep=NREP, seed=SEED, block_days=BLOCK_D, overrides=OV, tags=TAG, datasets=DSN,
              window="2022-01-01..2025-12-30 (equity rebase 2021-12-31)", jar_sha256=SAD.JAR_SHA,
              kaggle_sim_md5=SAD.KS_MD5_WANT, parity=par, groups=groups, group_table=G, quarters=Q,
              boot_obs_group=gobs, contrasts=con, rule=rule, metrics=M,
              g1=json.load(open(W + "/g1.json")) if os.path.exists(W + "/g1.json") else None,
              edge=json.load(open(W + "/edge.json")) if os.path.exists(W + "/edge.json") else None,
              sim_sha256=json.load(open(SHA_JSON)) if os.path.exists(SHA_JSON) else None)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["step0", "g1", "edge", "upload", "submit", "status", "fetch", "parity", "score"])
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--code-sha", default=PREREG_COMMIT)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.cmd == "step0":
        step0()
    elif a.cmd == "g1":
        sys.exit(0 if g1(a.runs) else 3)
    elif a.cmd == "edge":
        edge()
    elif a.cmd == "upload":
        for r in a.runs:
            upload(r)
    elif a.cmd == "submit":
        ks = ks_mod()
        log.info("free_slots=%d", ks.free_slots())
        for r in a.runs:
            submit(r, a.code_sha)
    elif a.cmd == "status":
        ks = ks_mod()
        for r in a.runs or NEWRUNS:
            try:
                log.info("STATUS %-4s %s", r, ks._status(ks.kernel_ref(TAG[r])))
            except Exception as e:  # noqa: BLE001
                log.info("STATUS %-4s loi %s", r, str(e)[:120])
    elif a.cmd == "fetch":
        ks = ks_mod()
        for r in a.runs:
            o = ks.fetch(TAG[r])
            log.info("FETCH %s %s", r, json.dumps(o.get("result"), default=str)[:400])
    elif a.cmd == "parity":
        for r in a.runs:
            parity_run(r)
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
