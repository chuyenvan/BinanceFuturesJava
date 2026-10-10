#!/usr/bin/env python3
"""HO3b cong 5 (§4c, 27fa291b): so output exporter Java (kernel Aerospike rieng) tren lat H1 2026-03-01..03-08 voi HO26.
(a) gate 33 V3FULL; (b) Tool1 2 bien the (luoi 15') + p0 net015; (c) nhan nBars_72h. Chi dem/ty le.
Usage: ho3b_slice_cmp.py <kernel_out_dir> <out.json>"""
import glob, json, logging, os, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, "/home/ubuntu/sel1m_code")
import g015_net_train as G  # noqa: E402
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_sc")
TZ = "Asia/Ho_Chi_Minh"
A0 = pd.Timestamp("2026-03-01", tz=TZ).value // 10**6
A1 = pd.Timestamp("2026-03-08", tz=TZ).value // 10**6
T0, T1 = A0 + 7 * 3600000, A1 + 7 * 3600000
OUTK = sys.argv[1]


def cmp_cells(a, b, tol):
    ok = (np.abs(a - b) <= tol) | (np.isnan(a) & np.isnan(b))
    return ok


def gate():
    use = ["timestamp"] + GA.V3FULL
    ref = pd.read_csv(GA.STORE, usecols=use)
    ref = ref[(ref.timestamp >= A0) & (ref.timestamp < A1)]
    new = pd.read_csv(glob.glob(OUTK + "/out/gate/*.csv*")[0], usecols=use)
    new = new[(new.timestamp >= A0) & (new.timestamp < A1)]
    M = ref.merge(new, on="timestamp", how="outer", suffixes=("_r", "_n"), indicator=True)
    both = M[M._merge == "both"]
    per, bad = {}, int((M._merge != "both").sum()) * len(GA.V3FULL)
    for c in GA.V3FULL:
        a, b = both[c + "_n"].to_numpy(np.float64), both[c + "_r"].to_numpy(np.float64)
        k = int((~cmp_cells(a, b, 1e-6 * np.maximum(1.0, np.abs(b)))).sum())
        per[c] = k; bad += k
    cells = len(M) * len(GA.V3FULL)
    r = dict(rows_ref=int(len(ref)), rows_new=int(len(new)), rows_one_side=int((M._merge != "both").sum()),
             cells=cells, bad=bad, ok_frac=1 - bad / max(cells, 1), bad_by_col={k: v for k, v in per.items() if v})
    r["pass"] = r["ok_frac"] >= 0.999
    return r


def t1(pattern, lo, hi):
    x = G.read_tool1(pattern, grid_ms=G.GRID_MS)
    t = x["ts"].astype(np.int64)
    x = x[(t >= lo) & (t < hi)]
    k = x["ts"].astype(np.int64) * 10000 + x["sym"].astype(np.int64)
    o = np.argsort(k, kind="stable")
    return k[o], np.asarray(x["f"], dtype=np.float64)[o]


def tool1():
    kr, fr = t1(os.path.join(G.T1_DIR, "features_20260101_to_20260401*"), T0, T1)
    q75, q25 = np.nanpercentile(fr, 75, axis=0), np.nanpercentile(fr, 25, axis=0)
    iqr = q75 - q25
    out = dict(rows_ho26=int(len(kr)))
    for v in ("t1u", "t1d"):
        fs = glob.glob(OUTK + "/out/%s/*.t1c*" % v)
        if not fs:
            out[v] = dict(missing=True); continue
        kn, fn = t1(fs[0], T0, T1)
        com, ir, inn = np.intersect1d(kr, kn, return_indices=True)
        r = dict(rows_new=int(len(kn)), both=int(len(com)), keys_equal=bool(len(kn) == len(kr) and len(com) == len(kr)))
        tol = np.where(iqr > 0, 1e-2 * iqr, 0)
        okc = np.zeros(fr.shape[1])
        bad = 0
        for j in range(fr.shape[1]):
            a, b = fn[inn, j], fr[ir, j]
            tj = tol[j] if tol[j] > 0 else 1e-6 * np.maximum(1.0, np.abs(b))
            ok = cmp_cells(a, b, tj)
            okc[j] = ok.mean() if len(ok) else 0
            bad += int((~ok).sum())
        cells = (len(kr) + len(kn) - len(com)) * fr.shape[1]
        bad += (len(kr) + len(kn) - 2 * len(com)) * fr.shape[1]
        r.update(cells=int(cells), bad=int(bad), ok_frac=1 - bad / max(cells, 1),
                 worst_cols={int(j): round(float(okc[j]), 6) for j in np.argsort(okc)[:5]})
        r["pass"] = bool(r["keys_equal"] and r["ok_frac"] >= 0.999)
        out[v] = r
    return out


def labels():
    from funding_label_pb import read_label
    cols = ["tEpochMs", "symbol", "nBars_72h"]
    ref = read_label("/home/ubuntu/ds_label15m/funding_label_20260101_to_20260401.pb", usecols=cols)
    ref = ref[(ref.tEpochMs >= T0) & (ref.tEpochMs < T1) & (ref.tEpochMs % 900000 == 0)]
    fs = sorted(glob.glob(OUTK + "/out/lab/*.pb"))
    if not fs:
        return dict(missing=True, files=os.listdir(OUTK + "/out/lab") if os.path.isdir(OUTK + "/out/lab") else [])
    new = pd.concat([read_label(f, usecols=cols) for f in fs])
    new = new[(new.tEpochMs >= T0) & (new.tEpochMs < T1) & (new.tEpochMs % 900000 == 0)]
    M = ref.merge(new, on=["tEpochMs", "symbol"], how="left", suffixes=("_r", "_n"))
    eq = (M.nBars_72h_r == M.nBars_72h_n)
    r = dict(rows_ho26=int(len(ref)), rows_new=int(len(new)), ho26_keys_found=int(M.nBars_72h_n.notna().sum()),
             eq_frac_vs_ho26=float(eq.mean()) if len(M) else 0.0, files=[os.path.basename(f) for f in fs])
    r["pass"] = r["eq_frac_vs_ho26"] >= 0.999
    return r


def main():
    res = dict(prereg="ADDENDUM-4 §4c 27fa291b", window=[int(A0), int(A1)])
    for nm, fn in (("gate", gate), ("tool1", tool1), ("labels", labels)):
        try:
            res[nm] = fn()
        except Exception as e:  # noqa: BLE001
            res[nm] = dict(error=repr(e)[:400])
        log.info("%s %s", nm, json.dumps(res[nm], default=str))
        json.dump(res, open(sys.argv[2], "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
