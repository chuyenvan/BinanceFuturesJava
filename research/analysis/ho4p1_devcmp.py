#!/usr/bin/env python3
"""HO4-P1 P3-DEV (ADDENDUM-6 §6.3, CHI BAO): so lat DEV dung lai tu Vision (det-a + chdet-a) voi DEV goc — chay TRONG Kaggle.
G store gate, T Tool1 (strict 1e-6 + dung sai 1 buoc luong tu T1C2), L nhan, V feat_v2, P p15 M42, N net015 Q4, B bins Q4, pool.
Them pred.bin cho sim DEV theo xap xi (a) ADDENDUM-5: p15' = p15 DEV + [M42(dong dung lai) - M42(dong DEV)] (dong co 33 feature
khac rel 1e-6). Chi ty le/dem, KHONG so 2026. Usage (trong kernel): ho4p1_devcmp.py <cfg.json>"""
import glob, gzip, hashlib, json, logging, os, struct, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("devcmp")
CFG = json.load(open(sys.argv[1]))
IN, WORK = "/kaggle/input", "/kaggle/working"
OUT = WORK + "/out"
CODE = CFG["code_dir"]
os.makedirs(OUT, exist_ok=True)
os.environ["SEL1M_CODE"] = CODE
os.environ["MAP_CSV"] = CODE + "/symbol_map_863.csv"
sys.path.insert(0, CODE)
import g015_net_train as G  # noqa: E402
from funding_label_pb import read_label  # noqa: E402
S_LO, S_HI, Q4 = 1751302800000, 1767200400000, 1759251600000
L_MAX = 1766965500000
V3 = json.load(open(CODE + "/v3full.json"))
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])
RES = dict(prereg="ADDENDUM-6 af6d6c94 P3-DEV (chi bao)")


def save():
    json.dump(RES, open(OUT + "/devcmp.json", "w"), indent=1, default=str)


def find(pat, src):
    return sorted(p for p in glob.glob(IN + "/**/" + pat, recursive=True) if ("/" + src + "/") in p and os.path.isfile(p))


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def relok(a, b, tol=1e-6):
    a = a.astype(np.float64); b = b.astype(np.float64)
    return (np.abs(a - b) <= tol * np.maximum(1.0, np.abs(b))) | (np.isnan(a) & np.isnan(b))


def store(path):
    d = pd.read_csv(path, usecols=["timestamp"] + V3, dtype={c: np.float32 for c in V3})
    d["timestamp"] = d["timestamp"].astype(np.int64)
    d = d[(d.timestamp >= S_LO) & (d.timestamp < S_HI)].drop_duplicates("timestamp", keep="last")
    return d.sort_values("timestamp").reset_index(drop=True)


def m42(X):
    import xgboost as xgb
    b = xgb.Booster(); b.load_model(CODE + "/gate_s42_cut20260101p15.json")
    return b.predict(xgb.DMatrix(X)).astype(np.float32)


def cmp_G_P():
    dev = store(find("gate_dataset_full.csv*", "bdchain-gate-store")[0])
    new = store(find("gate_dev.csv*", CFG["det_src"])[0])
    M = dev.merge(new, on="timestamp", how="outer", suffixes=("_d", "_n"), indicator=True)
    B = M[M._merge == "both"].reset_index(drop=True)
    one = int((M._merge != "both").sum())
    feq = np.ones(len(B), bool)
    per, ok = {}, 0
    for c in V3:
        k = relok(B[c + "_n"].to_numpy(), B[c + "_d"].to_numpy())
        per[c] = round(float(k.mean()), 6); ok += int(k.sum()); feq &= k
    cells = len(M) * len(V3)
    RES["G"] = dict(rows_dev=int(len(dev)), rows_new=int(len(new)), both=int(len(B)), one_side=one, ok_frac=ok / max(1, cells),
                    rows_all33_equal=int(feq.sum()), per_col=per)
    Xd = B[[c + "_d" for c in V3]].to_numpy(np.float32); Xn = B[[c + "_n" for c in V3]].to_numpy(np.float32)
    pd_, pn = m42(Xd), m42(Xn)
    d = np.abs(pd_.astype(np.float64) - pn.astype(np.float64))
    RES["P"] = dict(both=int(len(B)), one_side=one, ok_rows=int((d <= 1e-6).sum()), ok_frac=float((d <= 1e-6).sum() / max(1, len(M))),
                    max_abs=float(d.max()) if len(d) else None)
    # xap xi (a): pred.bin cho sim DEV = base ho26-pred-s42; dong ts in S co feature khac -> p15 + delta M42
    raw = open(find("pred.bin", "ho26-pred-s42")[0], "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=REC).copy()
    ts = a["ts"].astype(np.int64)
    bt = B.timestamp.to_numpy(np.int64)
    ch = ~feq
    pos = np.searchsorted(ts, bt[ch])
    hit = (pos < len(ts)) & (ts[np.clip(pos, 0, len(ts) - 1)] == bt[ch])
    delta = (pn[ch] - pd_[ch]).astype(np.float64)
    a["p15"][pos[hit]] = (a["p15"][pos[hit]].astype(np.float64) + delta[hit]).astype(np.float32).astype(">f4")
    os.makedirs(OUT + "/pred_simdev", exist_ok=True)
    with open(OUT + "/pred_simdev/pred.bin", "wb") as f:
        f.write(raw[:4]); f.write(a.tobytes())
    RES["pred_simdev"] = dict(rows_changed=int(hit.sum()), md5=md5f(OUT + "/pred_simdev/pred.bin"), base_md5=hashlib.md5(raw).hexdigest())
    log.info("G %s P %s", {k: v for k, v in RES["G"].items() if k != "per_col"}, RES["P"])
    save()


def t1_load(paths, lo, hi):
    aa = []
    for p in paths:
        x = G.read_tool1(p, grid_ms=G.GRID_MS)
        t = x["ts"].astype(np.int64)
        aa.append(x[(t >= lo) & (t < hi)].copy())
    a = np.concatenate(aa)
    k = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
    o = np.argsort(k, kind="stable")
    k, a = k[o], a[o]
    u = np.r_[True, np.diff(k) > 0]
    return k[u], a["f"][u].astype(np.float64)


def cmp_T():
    out = {}
    U3, U4, U5 = (int(pd.Timestamp(x, tz="UTC").value // 10**6) for x in ("2025-07-01", "2025-10-01", "2026-01-01"))
    for q, lo, hi, devp, newsub in (("Q3", U3, U4, "features_20250701_to_20251001*", "t1a"),
                                    ("Q4", U4, U5, "features_20251001_to_20260101*", "t1b")):
        kd, fd = t1_load(find(devp, "funding-tool1-15m")[:1], lo, hi)
        kn, fn = t1_load(find(newsub + "/*.t1c*", CFG["det_src"]), lo, hi)
        com, ia, ib = np.intersect1d(kd, kn, return_indices=True)
        a, b = fn[ib], fd[ia]
        rng = np.nanmax(fd, axis=0) - np.nanmin(fd, axis=0)
        step = 1.01 * rng / 65535.0 + 1e-6
        strict = (np.abs(a - b) <= 1e-6 * np.maximum(1.0, np.abs(b))) | (np.isnan(a) & np.isnan(b))
        quant = (np.abs(a - b) <= step[None, :]) | (np.isnan(a) & np.isnan(b))
        union = len(kd) + len(kn) - len(com)
        out[q] = dict(keys_dev=int(len(kd)), keys_new=int(len(kn)), common=int(len(com)), strict_frac=float(strict.sum() / (40 * union)),
                      quant_frac=float(quant.sum() / (40 * union)), quant_frac_common=float(quant.mean()) if len(com) else None,
                      worst_cols_quant=sorted(((round(float(quant[:, j].mean()), 4), j) for j in range(40)))[:5])
        log.info("T %s %s", q, out[q])
        del kd, fd, kn, fn, a, b
    RES["T"] = out
    save()


def cmp_L():
    U4 = int(pd.Timestamp("2025-10-01", tz="UTC").value // 10**6)
    def lab(paths, lo, hi):
        L = pd.concat([read_label(p, usecols=["tEpochMs", "symbol", "nBars_72h"]) for p in paths])
        L = L[(L.tEpochMs >= lo) & (L.tEpochMs < hi) & (L.tEpochMs <= L_MAX)]
        return L.drop_duplicates(["tEpochMs", "symbol"], keep="first")
    res = {}
    for q, lo, hi, devp, sub in (("Q3", 0, U4, "funding_label_20250701_to_20251001*", "laba"),
                                 ("Q4", U4, 1 << 62, "funding_label_20251001_to_20260101*", "labb")):
        d = lab(find(devp, "funding-label-15m")[:1], lo, hi)
        n = lab(find(sub + "/*.pb", CFG["det_src"]), lo, hi)
        M = d.merge(n, on=["tEpochMs", "symbol"], how="left", suffixes=("_d", "_n"))
        eq = int((M.nBars_72h_d == M.nBars_72h_n).sum())
        res[q] = dict(n_dev=int(len(d)), n_new=int(len(n)), found=int(M.nBars_72h_n.notna().sum()), equal=eq, frac=eq / max(1, len(d)))
    RES["L"] = res
    log.info("L %s", res)
    save()


def cmp_VNB():
    F = pd.read_parquet(find("feat_v2.parquet", CFG["chain_src"])[0])
    D = pd.read_parquet(find("feat_v2_x1_keep9.parquet", "s1-featv2-x1-20260919")[0], columns=["ts", "sym"] + KEEP)
    F = F[(F.ts >= S_LO) & (F.ts < S_HI)]; D = D[(D.ts >= S_LO) & (D.ts < S_HI)]
    F["sym"] = F.sym.astype(np.int64); D["sym"] = D.sym.astype(np.int64)
    M = D.merge(F, on=["ts", "sym"], how="outer", suffixes=("_d", "_n"), indicator=True)
    B = M[M._merge == "both"]
    ok = sum(int(relok(B[c + "_n"].to_numpy(), B[c + "_d"].to_numpy()).sum()) for c in KEEP)
    RES["V"] = dict(rows_dev=int(len(D)), rows_new=int(len(F)), both=int(len(B)), ok_frac=ok / max(1, len(M) * len(KEEP)),
                    per_col={c: round(float(relok(B[c + "_n"].to_numpy(), B[c + "_d"].to_numpy()).mean()), 4) for c in KEEP})
    key = lambda a: a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
    n = np.fromfile(find("net015/predict_wf_20251001.bin", CFG["chain_src"])[0], dtype=DT)
    o = np.fromfile(find("predict_wf_20251001.bin", "predwf-g015x26-gate")[0], dtype=DT)
    com, ia, ib = np.intersect1d(key(o), key(n), return_indices=True)
    d = np.abs(o["p0"][ia].astype(np.float64) - n["p0"][ib].astype(np.float64))
    un = len(o) + len(n) - len(com)
    from scipy.stats import spearmanr
    RES["N"] = dict(n_orig=int(len(o)), n_new=int(len(n)), common=int(len(com)), ok_frac=float((d <= 1e-3).sum() / max(1, un)),
                    spearman=float(spearmanr(o["p0"][ia], n["p0"][ib]).correlation), max_abs=float(d.max()))
    nb = np.fromfile(find("bins/predict_wf_20251001.bin", CFG["chain_src"])[0], dtype=DT)
    db = np.fromfile(find("predict_wf_20251001.bin", "sim-ho26a-bundle")[0], dtype=DT)
    com, ia, ib = np.intersect1d(key(db), key(nb), return_indices=True)
    okc = np.ones(len(com), bool)
    for c in ("p0", "p1", "p2", "p3"):
        x, y = nb[c][ib].astype(np.float64), db[c][ia].astype(np.float64)
        okc &= (np.abs(x - y) <= 1e-6) | (np.isnan(x) & np.isnan(y))
    RES["B"] = dict(n_dev=int(len(db)), n_new=int(len(nb)), common=int(len(com)),
                    ok_frac=float(okc.sum() / max(1, len(db) + len(nb) - len(com))))
    try:
        Lg = pd.read_parquet(find("cand_dev_x1_lite.parquet", "s1-featv2-x1-20260919")[0])
        S = pd.read_parquet(find("s1_ho4p1det.parquet", CFG["chain_src"])[0])
        if "g1lite" in Lg.columns:
            Lg = Lg[Lg.g1lite.notna()]
        Lg = Lg[(Lg.ts >= Q4) & (Lg.ts < S_HI)]; S = S[(S.ts >= Q4) & (S.ts < S_HI)]
        a, b = set(zip(Lg.ts.astype(np.int64), Lg.sym.astype(np.int64))), set(zip(S.ts.astype(np.int64), S.sym.astype(np.int64)))
        RES["pool_Q4"] = dict(n_dev=len(a), n_new=len(b), jaccard=len(a & b) / max(1, len(a | b)))
    except Exception as e:  # noqa: BLE001
        RES["pool_Q4"] = dict(error=repr(e)[:200])
    log.info("V %s N %s B %s pool %s", RES["V"]["ok_frac"], RES["N"], RES["B"], RES.get("pool_Q4"))
    save()


if __name__ == "__main__":
    cmp_G_P()
    cmp_VNB()
    cmp_L()
    cmp_T()
    RES["done"] = True
    save()
    log.info("DEVCMP_DONE")
