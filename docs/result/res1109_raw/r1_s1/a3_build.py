"""R1 A3 S1FULL (+loc A1 = B0'): dung bins tu net015 RAW (G015x26) + S1 cham MOI (tick, coin) bang model fold WFO.
Cong G-NET0 (nguon net015), G-FULL (do phu + khop pred_s1a2x1 tren pool cu), G-SAN (multiset tung tick).
Gan gia tri: trong tick, coin co diem S1 va KHONG thuoc A1-loai xep theo score tang (1 = tot), nhan P(win) lon dan;
coin bi ha (score NaN hoac A1-loai) nhan phan P(win) nho nhat con lai (giu thu tu p0 goc giam dan).
Chi doi p0 (nhu build_map); p1..p3, tap (ts,sym), thu tu record giu nguyen. Chi doc nguon; ghi OUT."""
import glob
import gzip
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a3")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
H = 3600000
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global",
        "rk_oi_delta24h"]
RAW = os.path.expanduser("~/claude_master/res1109/r1_s1/g015x26")
MAP = "/home/ubuntu/predwf_map_s1a2_x1"
MOD = "/home/ubuntu/s1_model_allfold"
FEAT = "/home/ubuntu/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet"
PRED = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
EXI = os.path.expanduser("~/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz")
SMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
OUT = os.path.expanduser("~/claude_master/res1109/r1_s1/a3_bins")
TRADFI_UT = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX"}


def a1_excluded_ids():
    """UniverseA1Classifier: TRADFI (contractType chua TRADIFI/TRADFI hoac underlyingType TradFi), INDEX, PREMARKET."""
    ei = json.load(gzip.open(EXI))
    bad = set()
    for s in ei["symbols"]:
        ct = (s.get("contractType") or "").upper()
        ut = (s.get("underlyingType") or "").strip().upper()
        if "TRADIFI" in ct or "TRADFI" in ct or ut in TRADFI_UT or ut in ("INDEX", "PREMARKET"):
            bad.add(s["symbol"])
    sm = pd.read_csv(SMAP)
    ids = set(int(i) for i, s in zip(sm.symId, sm.symbol) if s in bad)
    log.info("A1-loai: %d symbol exchangeInfo, %d co symId trong symbol_map: %s", len(bad), len(ids),
             sorted(s for s in sm.symbol if s in bad)[:40])
    return ids


def main():
    os.makedirs(OUT, exist_ok=True)
    a1 = a1_excluded_ids()
    F = pd.read_parquet(FEAT)
    F["sym"] = F["sym"].astype("int64")
    F = F.rename(columns={"ts": "ts_h"}).set_index(["ts_h", "sym"])
    P = pd.read_parquet(PRED, columns=["ts", "sym", "score"])
    P["sym"] = P["sym"].astype("int64")
    pool_ts = set(P.ts.unique().tolist())
    rep = {"folds": [], "a1_ids": sorted(a1)}
    files = sorted(glob.glob(RAW + "/predict_wf_*.bin"))
    assert len(files) == 16, len(files)
    for fn in files:
        b = os.path.basename(fn)
        fold = b[11:19]
        raw = np.fromfile(fn, dtype=REC)
        mp = np.fromfile(os.path.join(MAP, b), dtype=REC)
        # ---- G-NET0
        assert len(raw) == len(mp) and np.array_equal(raw["ts"], mp["ts"]) and np.array_equal(raw["sym"], mp["sym"]), \
            "G-NET0: (ts,sym)/thu tu khac " + b
        D = pd.DataFrame({"i": np.arange(len(raw)), "ts": raw["ts"].astype("i8"), "sym": raw["sym"].astype("i8"),
                          "p": raw["p0"].astype("f8"), "pm": mp["p0"].astype("f8")})
        fin = np.isfinite(D.p.values)
        assert np.array_equal(fin, np.isfinite(D.pm.values)), "G-NET0: NaN khac " + b
        V = D[fin]
        sa = V.sort_values(["ts", "p"]).p.values
        sb = V.sort_values(["ts", "pm"]).pm.values
        ms = float(np.mean(np.abs(sa - sb) <= 1e-6))
        nonpool = ~V.ts.isin(pool_ts)
        cell_np = float(np.mean(np.abs(V.p.values[nonpool.values] - V.pm.values[nonpool.values]) <= 1e-6)) \
            if nonpool.any() else float("nan")
        assert ms == 1.0, "G-NET0 multiset %s %.6f" % (b, ms)
        assert np.isnan(cell_np) or cell_np == 1.0, "G-NET0 cell ngoai pool %s %.6f" % (b, cell_np)
        # ---- S1 cham MOI dong
        V = V.copy()
        V["ts_h"] = (V.ts // H) * H
        X = F.reindex(pd.MultiIndex.from_arrays([V.ts_h.values, V.sym.values])).to_numpy(dtype=np.float32)
        bst = xgb.Booster()
        bst.load_model(os.path.join(MOD, "s1a2x1_cut%s.json" % fold))
        allnan = np.isnan(X).all(axis=1)
        sc = -bst.predict(xgb.DMatrix(X, feature_names=KEEP))
        sc[allnan] = np.nan
        V["score"] = sc
        # ---- G-FULL: khop pred_s1a2x1 tren pool cu
        M = V.merge(P, on=["ts", "sym"], how="inner", suffixes=("", "_ref"))
        maxd = float(np.nanmax(np.abs(M.score.values - M.score_ref.values))) if len(M) else float("nan")
        Pr = P[(P.ts >= V.ts.min()) & (P.ts <= V.ts.max())][["ts", "sym"]]
        n_ref = int(len(Pr))
        n_absent = int((Pr.merge(D[["ts", "sym"]], on=["ts", "sym"], how="left", indicator=True)._merge
                        == "left_only").sum())
        demote = V.score.isna() | V.sym.isin(a1)
        cov = float((~V.score.isna()).mean())
        # ---- gan gia tri
        V["dem"] = demote.values
        V["k1"] = np.where(V.dem, 1, 0)
        V["k2"] = np.where(V.dem, -V.p, V.score)       # ha: giu thu tu p goc giam dan
        V = V.sort_values(["ts", "k1", "k2", "sym"])
        V["r"] = V.groupby("ts").cumcount()
        Ps = V[["ts", "p"]].sort_values(["ts", "p"], ascending=[True, False])
        Ps["r"] = Ps.groupby("ts").cumcount()
        V = V.merge(Ps[["ts", "r", "p"]].rename(columns={"p": "p_new"}), on=["ts", "r"], how="left")
        new = raw.copy()
        p0 = new["p0"].astype("f8")
        p0[V.i.values] = V.p_new.values
        new["p0"] = p0.astype(">f4")
        # ---- G-SAN: multiset tung tick giu nguyen
        chk = pd.DataFrame({"ts": raw["ts"][fin].astype("i8"), "a": raw["p0"][fin].astype("f8"),
                            "b": new["p0"][fin].astype("f8")})
        s1v = chk.sort_values(["ts", "a"]).a.values
        s2v = chk.sort_values(["ts", "b"]).b.values
        assert np.array_equal(s1v, s2v), "G-SAN multiset " + b
        assert np.array_equal(np.isnan(raw["p0"]), np.isnan(new["p0"])), "G-SAN NaN " + b
        new.tofile(os.path.join(OUT, b))
        r = dict(fold=fold, rows=int(fin.sum()), multiset_eq=ms, cell_eq_nonpool=cell_np, coverage_score=cov,
                 demoted_frac=float(demote.mean()), a1_rows=int(V.sym.isin(a1).sum()), pool_matched=int(len(M)),
                 pool_ref=n_ref, pool_absent_in_bin=n_absent, pool_maxd=maxd, changed_frac=float(np.mean(np.abs(raw["p0"][fin] - new["p0"][fin]) > 0)))
        rep["folds"].append(r)
        log.info("%s", r)
    h = hashlib.sha256()
    for fn in sorted(glob.glob(OUT + "/predict_wf_*.bin")):
        with open(fn, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
    rep["a3_bins_sha256_concat"] = h.hexdigest()
    rep["G_FULL_ADD1_raw"] = all(f["coverage_score"] >= 0.99 and f["pool_matched"] >= 0.999 * f["pool_ref"]
                                 and f["pool_maxd"] <= 1e-6 for f in rep["folds"])
    ok_full = all(f["coverage_score"] >= 0.99
                  and f["pool_matched"] >= 0.999 * (f["pool_ref"] - f["pool_absent_in_bin"])
                  and f["pool_maxd"] <= 1e-6 for f in rep["folds"])
    rep["G_NET0"] = True
    rep["G_FULL"] = ok_full
    rep["G_SAN"] = True
    json.dump(rep, open(OUT + "/a3_report.json", "w"), indent=1)
    log.info("DONE sha=%s G_FULL=%s", rep["a3_bins_sha256_concat"], ok_full)


if __name__ == "__main__":
    main()
