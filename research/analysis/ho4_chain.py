#!/usr/bin/env python3
"""HO4-P3 chuoi Python ha nguon (ADDENDUM-5 §5.3, 31e3c9e7) tren lat DEV S=[2025-07-01,2026-01-01) +07:
OI ghep (ghim ts < S_LO + Vision dung lai ts >= S_LO) -> V feat_v2 KEEP9 (CLOSES Vision) -> P gate p15 (model HO1 B2 s42)
-> pool (nhan dung lai) -> S1 (Q4 model goc cut20251001; Q3 xap xi delta) -> N net015 (Q4 ONNX goc f15; Q3 delta)
-> B bins (x1_build_map) -> artefact cho sim (market.bin, pred.bin, bins). Chi dem/ty le; KHONG in gia tri/PnL.
Usage: ho4_chain.py <stage> (oi|V|P|pool|S1|N|B|mkt|all)"""
import glob, gzip, hashlib, json, logging, os, struct, subprocess, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, "/home/ubuntu/sel1m_code")
import g015_net_train as G  # noqa: E402
import gate_ablation_driver as GA  # noqa: E402
import ho1_net015_predict as HN  # noqa: E402
import ho2_net015_onnx as H2  # noqa: E402
import ho1_featv2_window as FW  # noqa: E402
import ho1_s1_2026 as S1  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4ch")
W = "/home/ubuntu/claude_master/1010/ho4"
KX = W + "/kaggle/out/ho4-dev-x/out"
KO = W + "/kaggle/out/ho4-dev-oi/out/oi_rebuilt.bin.gz"
C = W + "/chain"
os.makedirs(C, exist_ok=True)
S_LO, S_HI = 1751302800000, 1767200400000
Q4_LO = 1759251600000                      # 2025-10-01 00:00 +07
L_MAX = 1766965500000                      # 2025-12-28 23:45 UTC (nhan du 72h nhin truoc trong DEV)
H, Q = 3600000, 900000
ODT = G.OI_DT
PIN = G.OI_FILE
CLO_RB = W + "/s1/CLOSES_1H_dev.bin"
M42 = "/home/ubuntu/claude_master/1003/ho1/gate/gate_s42_cut20260101p15.json"
PRED_BASE = "/home/ubuntu/claude_master/1003/ho1/gate/pred_s42/pred.bin"   # 22f69456 (bundle sim-ho26a)
PRED_BASE_MD5 = "22f69456381d9d1abd1592382c3b0319"
ORIG = {"20251001": "/home/ubuntu/claude_master/1009/ho26/orig/predict_wf_20251001.bin",
        "20250701": W + "/orig/predict_wf_20250701.bin"}
ORIG_SHA = {"20251001": "e03f0e58ed35f86929059cc349ceb18121df8b48ba3035293d7e6c9140da283a",
            "20250701": "8e7d1154fbc72665f38a23c8f4254de3b4c28f1b736c88c3374ee1245ff176c7"}
DEV_BINS = "/home/ubuntu/predwf_map_s1a2_x1_2021"
MKT_BASE = "/home/ubuntu/claude_master/1003/ho1/ds/market.bin"            # 34e33678 (bundle sim-ho26a)
DT = HN.DT
RES = json.load(open(C + "/chain.json")) if os.path.exists(C + "/chain.json") else {}


def save():
    json.dump(RES, open(C + "/chain.json", "w"), indent=1, default=str)


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ---------------- OI ghep ----------------
_RB = None


def rebuilt():
    global _RB
    if _RB is None:
        with gzip.open(KO, "rb") as f:
            _RB = np.frombuffer(f.read(), dtype=ODT)
        log.info("OI dung lai: %d dong", len(_RB))
    return _RB


def read_pin(lo, hi, step=10_000_000):
    n = os.path.getsize(PIN) // ODT.itemsize
    parts = []
    for k in range(0, n, step):
        c = np.fromfile(PIN, dtype=ODT, count=min(step, n - k), offset=k * ODT.itemsize)
        t = c["ts"].astype(np.int64)
        parts.append(c[(t >= lo) & (t < hi)].copy())
    return np.concatenate(parts)


def read_oi_comb(lo, hi):
    a = read_pin(lo, min(hi, S_LO)) if lo < S_LO else np.zeros(0, ODT)
    r = rebuilt()
    t = r["ts"].astype(np.int64)
    b = r[(t >= max(lo, S_LO)) & (t < hi)]
    return np.concatenate([a, b]).astype(ODT)


def oi_hourly_file(path, lo, hi):
    a = read_oi_comb(lo, hi)
    a = a[a["ts"].astype(np.int64) % H == 0]
    a.astype(ODT).tofile(path)       # big-endian (bai hoc HO3b)
    log.info("OI gio ghep -> %s %d dong", path, len(a))


# ---------------- V: feat_v2 KEEP9 ----------------
def closes_rb():
    a = np.fromfile(FW.CLO, dtype=FW.DT)
    FW.DEV_UNI.update(int(x) for x in np.unique(a["sym"]))
    b = np.fromfile(CLO_RB, dtype=FW.DT)
    df = pd.DataFrame({"ts": b["ts"].astype(np.int64), "sym": b["sym"].astype(np.int32), "c": b["c"].astype(np.float64)})
    df = df[(df.ts >= FW.T_START) & (df.ts <= FW.T_END)]
    P = df.pivot(index="ts", columns="sym", values="c").sort_index()
    hours = pd.Index(np.arange(P.index.min(), P.index.max() + H, H))
    return P.reindex(hours)


def stage_V():
    FW.T_START = int(pd.Timestamp("2025-05-15").value // 10**6)
    FW.T_END = 1767225600000                       # 2026-01-01 00:00 UTC
    FW.KEEP_FROM = S_LO - 24 * H
    FW.Q4_LO = S_LO
    hp = C + "/oi_hourly.bin"
    oi_hourly_file(hp, FW.T_START - 3 * H, FW.T_END + 1)
    FW.OI = hp
    P = closes_rb()
    long = FW.features(P)
    g = FW.gate(long)
    os.remove(hp)
    long.to_parquet(C + "/feat_new.parquet", index=False)
    RES["V_featv2"] = dict(g, n_rows=int(len(long)), ok_frac=1 - g["bad_frac"])
    save()
    log.info("CONG V: %s", RES["V_featv2"])


# ---------------- P: gate p15 (model HO1 B2 seed 42) + pred.bin cho sim ----------------
def load_store(path):
    use = ["timestamp"] + GA.V3FULL
    d = pd.read_csv(path, usecols=use, dtype={c: np.float32 for c in GA.V3FULL})
    d["timestamp"] = d["timestamp"].astype(np.int64)
    d = d[(d.timestamp >= S_LO) & (d.timestamp < S_HI)].drop_duplicates("timestamp", keep="last")
    return d.sort_values("timestamp").reset_index(drop=True)


def m42(X):
    import xgboost as xgb
    b = xgb.Booster()
    b.load_model(M42)
    return b.predict(xgb.DMatrix(X)).astype(np.float32)


def stage_P():
    dev = load_store(GA.STORE)
    new = load_store(glob.glob(KX + "/gate/*.csv*")[0])
    M = dev.merge(new, on="timestamp", how="outer", suffixes=("_d", "_n"), indicator=True)
    B = M[M._merge == "both"].reset_index(drop=True)
    Xd = B[[c + "_d" for c in GA.V3FULL]].to_numpy(np.float32)
    Xn = B[[c + "_n" for c in GA.V3FULL]].to_numpy(np.float32)
    pd_, pn = m42(Xd), m42(Xn)
    d = np.abs(pd_.astype(np.float64) - pn.astype(np.float64))
    feq = np.ones(len(B), bool)
    for j in range(Xd.shape[1]):
        a, b = Xn[:, j].astype(np.float64), Xd[:, j].astype(np.float64)
        feq &= (np.abs(a - b) <= 1e-6 * np.maximum(1.0, np.abs(b))) | (np.isnan(a) & np.isnan(b))
    one = int((M._merge != "both").sum())
    ok = int((d <= 1e-6).sum())
    r = dict(rows_dev=int(len(dev)), rows_new=int(len(new)), both=int(len(B)), one_side=one, ok_rows=ok,
             ok_frac=ok / max(1, len(M)), rows_feat_equal=int(feq.sum()), max_abs=float(d.max()) if len(d) else None)
    r["pass"] = r["ok_frac"] >= 0.999
    # pred.bin cho sim: base 22f69456; ts in S: p15' = p15 base + (M42(new) - M42(dev)) neu feature khac, giu nguyen neu trung
    raw = open(PRED_BASE, "rb").read()
    assert hashlib.md5(raw).hexdigest() == PRED_BASE_MD5
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=GA_REC).copy()
    ts = a["ts"].astype(np.int64)
    bt = B.timestamp.to_numpy(np.int64)
    ch = ~feq
    pos = np.searchsorted(ts, bt[ch])
    hit = (pos < len(ts)) & (ts[np.clip(pos, 0, len(ts) - 1)] == bt[ch])
    delta = (pn[ch] - pd_[ch]).astype(np.float64)
    newv = (a["p15"][pos[hit]].astype(np.float64) + delta[hit]).astype(np.float32)
    a["p15"][pos[hit]] = newv.astype(">f4")
    out = C + "/pred.bin"
    with open(out, "wb") as f:
        f.write(raw[:4]); f.write(a.tobytes())
    r.update(pred_rows_changed=int(hit.sum()), pred_md5=md5f(out), pred_base_md5=PRED_BASE_MD5)
    RES["P_p15"] = r
    save()
    log.info("CONG P: %s", r)


GA_REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])


# ---------------- pool + S1 ----------------
def open_ticks(pred_path):
    raw = open(pred_path, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=GA_REC)
    ts = a["ts"].astype(np.int64)
    m = (ts >= S_LO) & (ts < S_HI) & (ts % Q == 0)
    return ts[m][a["p15"][m].astype(np.float32) >= np.float32(0.008)]


def stage_S1():
    DEVLAB = ["/home/ubuntu/ds_label15m/funding_label_20250701_to_20251001.pb", "/home/ubuntu/ds_label15m/funding_label_20251001_to_20260101.pb"]
    NEWLAB = sorted(glob.glob(KX + "/laba/*.pb")) + sorted(glob.glob(KX + "/labb/*.pb"))
    ot_new, ot_dev = open_ticks(C + "/pred.bin"), open_ticks(PRED_BASE)
    A_new = pd.concat([S1.avail_pool(ot_new[ot_new <= L_MAX], NEWLAB), S1.avail_pool(ot_new[ot_new > L_MAX], DEVLAB)]).drop_duplicates()
    A_dev = S1.avail_pool(ot_dev, DEVLAB)
    kn = set(zip(A_new.ts.tolist(), A_new.sym.tolist())); kd = set(zip(A_dev.ts.tolist(), A_dev.sym.tolist()))
    r = dict(open_new=int(len(ot_new)), open_dev=int(len(ot_dev)), pool_new=len(kn), pool_dev=len(kd),
             jaccard=len(kn & kd) / max(1, len(kn | kd)), new_label_files=[os.path.basename(x) for x in NEWLAB])
    Fn = pd.read_parquet(C + "/feat_new.parquet")
    Fn["sym"] = Fn.sym.astype(np.int64)
    Fd = pd.read_parquet(FW.DEVF, columns=["ts", "sym"] + S1.KEEP)
    Fd["sym"] = Fd.sym.astype(np.int64)
    Fd = Fd[Fd.ts >= S_LO - 24 * H]
    assert S1.sha256f(S1.M1001) == json.load(open("/home/ubuntu/s1_model/s1a2x1_cut20251001.manifest.json"))["sha256_json"]
    devS = pd.read_parquet(S1.PRED_DEV)
    devS = devS[(devS.ts >= S_LO) & (devS.ts < S_HI)][["ts", "sym", "score"]]
    # kiem duong ong: S1 cut20251001 tren pool DEV Q4 + feature DEV == pred_s1a2x1 Q4
    Ad4 = A_dev[A_dev.ts >= Q4_LO]
    Sd4, _ = S1.score(S1.M1001, Ad4, Fd)
    chk = Sd4[["ts", "sym", "score"]].merge(devS[devS.ts >= Q4_LO], on=["ts", "sym"], how="outer", suffixes=("_m", "_d"), indicator=True)
    r["devQ4_model_vs_pred"] = dict(both=int((chk._merge == "both").sum()), one=int((chk._merge != "both").sum()),
                                   max_abs=float((chk.score_m - chk.score_d).abs().max()))
    out = []
    for q, (lo, hi) in (("Q3", (S_LO, Q4_LO)), ("Q4", (Q4_LO, S_HI))):
        A = A_new[(A_new.ts >= lo) & (A_new.ts < hi)]
        Sn, cov = S1.score(S1.M1001, A, Fn)
        Sn = Sn[["ts", "sym", "score"]]
        if q == "Q4":
            out.append(Sn); r["Q4_rows"] = int(len(Sn)); r["Q4_feat_cov"] = cov
            continue
        Sm, _ = S1.score(S1.M1001, A, Fd)
        X = Sn.merge(Sm[["ts", "sym", "score"]], on=["ts", "sym"], suffixes=("", "_m")).merge(devS, on=["ts", "sym"], how="left", suffixes=("", "_dev"))
        off = (X.score_dev - X.score_m)
        med = off.groupby(X.ts).transform("median")
        X["s_out"] = np.where(X.score_dev.notna(), X.score_dev + (X.score - X.score_m), X.score + med.fillna(0.0))
        out.append(X[["ts", "sym"]].assign(score=X.s_out.values))
        r["Q3_rows"] = int(len(X)); r["Q3_in_dev"] = int(X.score_dev.notna().sum()); r["Q3_feat_cov"] = cov
    S = pd.concat(out).sort_values(["ts", "sym"]).reset_index(drop=True)
    S.to_parquet("/home/ubuntu/ledger/pred_ho4dev.parquet", index=False)
    r["pred_s1_sha256"] = sha256f("/home/ubuntu/ledger/pred_ho4dev.parquet")
    RES["S1_pool"] = r
    save()
    log.info("S1/pool: %s", r)


# ---------------- N: net015 ----------------
def keyof(ts, sym):
    return np.asarray(ts, np.int64) * 10000 + np.asarray(sym, np.int64)


def rows(patterns, lo, hi, comb):
    HN.read_oi = read_oi_comb if comb else _READ_OI_PIN
    X, ts, sym, info = HN.build_rows(patterns, lo, hi)
    m = (ts >= lo) & (ts < hi)
    return X[m], ts[m], sym[m]


_READ_OI_PIN = HN.read_oi


def write_like_orig(r, kr, knew, pnew, path):
    """Ghi file net015 theo DUNG thu tu dong file goc cho khoa chung (bai hoc HO2 A2); khoa chi-moi noi sau (p1..p3 NaN)."""
    o = np.argsort(knew)
    pos = np.clip(np.searchsorted(knew[o], kr), 0, len(knew) - 1)
    hit = knew[o][pos] == kr
    out = r[hit].copy()
    out["p0"] = pnew[o][pos][hit].astype(">f4")
    extra = np.setdiff1d(knew, kr)
    if len(extra):
        e = np.zeros(len(extra), dtype=DT)
        e["ts"] = extra // 10000; e["sym"] = (extra % 10000).astype(np.int16)
        ie = np.searchsorted(knew[o], extra)
        e["p0"] = pnew[o][ie].astype(">f4")
        for c in ("p1", "p2", "p3"):
            e[c] = np.float32(np.nan)
        out = np.concatenate([out, e])
    out.astype(DT).tofile(path)          # FIX: np.concatenate tra ve native-endian (bai hoc HO3b) — phat hien qua kiem khoa B
    return int(hit.sum()), int(len(extra))


def stage_N():
    nd = C + "/net015"
    os.makedirs(nd, exist_ok=True)
    res = {}
    t1a, t1b = glob.glob(KX + "/t1a/*.t1c*")[0], glob.glob(KX + "/t1b/*.t1c*")[0]
    for cut, lo, hi, pn_pat, pd_pat in (("20251001", Q4_LO, S_HI, [t1a, t1b], None),
                                        ("20250701", S_LO, Q4_LO, [t1a], [os.path.join(G.T1_DIR, "features_20250401*"), os.path.join(G.T1_DIR, "features_20250701*")])):
        assert sha256f(ORIG[cut]) == ORIG_SHA[cut], cut
        r = np.fromfile(ORIG[cut], dtype=DT)
        kr = keyof(r["ts"], r["sym"])
        Xn, tn, sn = rows(pn_pat, lo, hi, True)
        pnew = H2.predict(Xn); del Xn
        kn = keyof(tn, sn)
        if pd_pat is not None:          # Q3: xap xi delta voi f15 (model f14 goc da mat)
            Xd, td, sd = rows(pd_pat, lo, hi, False)
            pdm = H2.predict(Xd); del Xd
            kd = keyof(td, sd)
            od = np.argsort(kd)
            on = np.argsort(kn)
            # gia tri goc theo khoa moi
            orr = np.argsort(kr)
            pr = np.clip(np.searchsorted(kr[orr], kn), 0, len(kr) - 1)
            in_orig = kr[orr][pr] == kn
            pq = np.clip(np.searchsorted(kd[od], kn), 0, len(kd) - 1)
            in_dev = kd[od][pq] == kn
            both = in_orig & in_dev
            adj = pnew.astype(np.float64).copy()
            adj[both] = r["p0"][orr][pr][both].astype(np.float64) + (pnew[both].astype(np.float64) - pdm[od][pq][both].astype(np.float64))
            offs = pd.Series(np.where(both, adj - pnew, np.nan)).groupby(tn).transform("median").to_numpy()
            nb = ~both
            adj[nb] = pnew[nb] + np.nan_to_num(offs[nb])
            pnew = np.clip(adj, 0.0, 1.0).astype(np.float32)
            res[cut + "_delta"] = dict(n_new=int(len(kn)), n_both=int(both.sum()), n_new_only=int(nb.sum()))
        com, ia, ib = np.intersect1d(kr, kn, return_indices=True)
        d = np.abs(r["p0"][ia].astype(np.float64) - pnew[ib].astype(np.float64))
        union = len(kr) + len(kn) - len(com)
        rr = dict(n_orig=int(len(kr)), n_new=int(len(kn)), common=int(len(com)), keys_equal=bool(len(com) == len(kr) == len(kn)),
                  ok_cells=int((d <= 1e-3).sum()), ok_frac=float((d <= 1e-3).sum() / max(1, union)), max_abs=float(d.max()),
                  bit_equal_frac=float((d == 0).mean()))
        try:
            from scipy.stats import spearmanr
            rr["spearman"] = float(spearmanr(r["p0"][ia], pnew[ib]).correlation)
        except Exception:  # noqa: BLE001
            pass
        rr["n_written_common"], rr["n_written_extra"] = write_like_orig(r, kr, kn, pnew, nd + "/predict_wf_%s.bin" % cut)
        rr["sha256"] = sha256f(nd + "/predict_wf_%s.bin" % cut)
        if cut == "20251001":
            rr["pass"] = bool(rr["keys_equal"] and rr["ok_frac"] >= 0.99)
        res[cut] = rr
        log.info("N %s: %s", cut, rr)
    RES["N_net015"] = res
    save()


# ---------------- B: bins (x1_build_map) ----------------
def stage_B():
    bd = C + "/bins"
    os.makedirs(bd, exist_ok=True)
    env = dict(os.environ, X1_CUTS="20250701 20251001", X1_G015_DIR=C + "/net015")
    p = subprocess.run([sys.executable, "-u", "x1_build_map.py", "ho4dev", bd], cwd=R + "/research/pipeline/x1", env=env,
                       capture_output=True, text=True)
    assert p.returncode == 0 and "MAP_OK" in p.stdout, p.stdout[-500:] + p.stderr[-500:]
    res = {}
    for cut in ("20251001", "20250701"):
        n = np.fromfile(bd + "/predict_wf_%s.bin" % cut, dtype=DT)
        d = np.fromfile(DEV_BINS + "/predict_wf_%s.bin" % cut, dtype=DT)
        kn, kd = keyof(n["ts"], n["sym"]), keyof(d["ts"], d["sym"])
        com, ia, ib = np.intersect1d(kd, kn, return_indices=True)
        ok = np.ones(len(com), bool)
        for c in ("p0", "p1", "p2", "p3"):
            a, b = n[c][ib].astype(np.float64), d[c][ia].astype(np.float64)
            ok &= (np.abs(a - b) <= 1e-6) | (np.isnan(a) & np.isnan(b))
        union = len(kd) + len(kn) - len(com)
        rr = dict(n_dev=int(len(kd)), n_new=int(len(kn)), common=int(len(com)), keys_equal=bool(len(com) == len(kd) == len(kn)),
                  ok_cells=int(ok.sum()), ok_frac=float(ok.sum() / max(1, union)), md5=md5f(bd + "/predict_wf_%s.bin" % cut),
                  dev_md5=md5f(DEV_BINS + "/predict_wf_%s.bin" % cut))
        if cut == "20251001":
            rr["pass"] = bool(rr["keys_equal"] and rr["ok_frac"] >= 0.99)
        res[cut] = rr
        log.info("B %s: %s", cut, rr)
    res["map_tail"] = p.stdout.strip().splitlines()[-3:]
    RES["B_bins"] = res
    save()


# ---------------- market.bin cho sim ----------------
def stage_mkt():
    def rd(p):
        with open(p, "rb") as f:
            n = struct.unpack(">i", f.read(4))[0]
            return np.frombuffer(f.read(20 * n), dtype=np.dtype([("ts", ">i8"), ("v", "V12")]))
    assert md5f(MKT_BASE).startswith("34e33678"), "market base phai = bundle sim-ho26a"
    base, nb = rd(MKT_BASE), rd(KX + "/market_rebuilt.bin")
    tb, tn = base["ts"].astype(np.int64), nb["ts"].astype(np.int64)
    MDT = np.dtype([("ts", ">i8"), ("v", "V12")])
    out = np.concatenate([base[tb < S_LO], nb[(tn >= S_LO) & (tn < S_HI)], base[tb >= S_HI]]).astype(MDT)
    assert (np.diff(out["ts"].astype(np.int64)) > 0).all()
    assert out.dtype == MDT and out.tobytes()[:12] == base.tobytes()[:12]
    p = C + "/market.bin"
    with open(p, "wb") as f:
        f.write(struct.pack(">i", len(out))); f.write(out.tobytes())
    RES["mkt_sim"] = dict(base_md5=md5f(MKT_BASE), n_base=int(len(base)), n_out=int(len(out)),
                          n_S_base=int(((tb >= S_LO) & (tb < S_HI)).sum()), n_S_new=int(((tn >= S_LO) & (tn < S_HI)).sum()), md5=md5f(p))
    save()
    log.info("mkt: %s", RES["mkt_sim"])


if __name__ == "__main__":
    st = sys.argv[1]
    for nm, fn in (("V", stage_V), ("P", stage_P), ("S1", stage_S1), ("N", stage_N), ("B", stage_B), ("mkt", stage_mkt)):
        if st in (nm, "all"):
            fn()
    log.info("CHAIN_STAGE_DONE %s", st)
