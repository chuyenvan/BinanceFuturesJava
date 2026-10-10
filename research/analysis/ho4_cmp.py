#!/usr/bin/env python3
"""HO4-P3 cong G / T / L (ADDENDUM-5 §5.3, 31e3c9e7): output exporter Java goc (kernel ho4-dev-x, du lieu Vision) vs DEV.
G: store gate 33 V3FULL, hop dong trong S, rel 1e-6. T: Tool1 40 cot luoi 15', hop khoa, rel 1e-6 (+ mo ta dung sai 1e-2*IQR).
L: nhan (tEpochMs, symbol) + nBars_72h, tick <= 2025-12-28 23:45 UTC. Chi dem/ty le. Usage: ho4_cmp.py <kernel_out_dir> <out.json>"""
import glob, json, logging, os, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, "/home/ubuntu/sel1m_code")
import g015_net_train as G  # noqa: E402
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4cmp")
S_LO, S_HI = 1751302800000, 1767200400000
U_LO = 1751328000000                 # 2025-07-01 00:00 UTC: mep file Tool1/nhan DEV (quy UTC)
L_MAX = 1766965500000                # 2025-12-28 23:45 UTC
OUTK = sys.argv[1]


def okc(a, b, tolrel=1e-6):
    return (np.abs(a - b) <= tolrel * np.maximum(1.0, np.abs(b))) | (np.isnan(a) & np.isnan(b))


def gate():
    use = ["timestamp"] + GA.V3FULL
    ref = pd.read_csv(GA.STORE, usecols=use)
    ref = ref[(ref.timestamp >= S_LO) & (ref.timestamp < S_HI)]
    new = pd.read_csv(glob.glob(OUTK + "/out/gate/*.csv*")[0], usecols=use)
    new = new[(new.timestamp >= S_LO) & (new.timestamp < S_HI)]
    M = ref.merge(new, on="timestamp", how="outer", suffixes=("_r", "_n"), indicator=True)
    both = M[M._merge == "both"]
    one = int((M._merge != "both").sum())
    per, bad = {}, one * len(GA.V3FULL)
    badrow = np.zeros(len(both), bool)
    for c in GA.V3FULL:
        ok = okc(both[c + "_n"].to_numpy(np.float64), both[c + "_r"].to_numpy(np.float64))
        per[c] = int((~ok).sum()); bad += per[c]; badrow |= ~ok
    cells = len(M) * len(GA.V3FULL)
    mon = pd.to_datetime(both.timestamp[badrow], unit="ms").dt.tz_localize("UTC").dt.tz_convert("Asia/Ho_Chi_Minh").dt.strftime("%Y-%m").value_counts().to_dict()
    r = dict(rows_ref=int(len(ref)), rows_new=int(len(new)), ref_only=int((M._merge == "left_only").sum()),
             new_only=int((M._merge == "right_only").sum()), cells=int(cells), bad=int(bad), ok_frac=1 - bad / max(cells, 1),
             bad_by_col={k: v for k, v in per.items() if v}, bad_rows_by_month=mon)
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
    out = {}
    tot_cells = tot_bad = 0
    for v, ref_pat in (("t1a", "features_20250701_to_20251001*"), ("t1b", "features_20251001_to_20260101*")):
        kr, fr = t1(os.path.join(G.T1_DIR, ref_pat), U_LO, S_HI)
        fs = glob.glob(OUTK + "/out/%s/*.t1c*" % v)
        if not fs:
            out[v] = dict(missing=True); continue
        kn, fn = t1(fs[0], U_LO, S_HI)
        com, ir, inn = np.intersect1d(kr, kn, return_indices=True)
        iqr = np.nanpercentile(fr, 75, axis=0) - np.nanpercentile(fr, 25, axis=0)
        bad, bad_iqr, colok = 0, 0, {}
        for j in range(fr.shape[1]):
            a, b = fn[inn, j], fr[ir, j]
            ok = okc(a, b)
            bad += int((~ok).sum()); colok[j] = float(ok.mean()) if len(ok) else 0.0
            tj = 1e-2 * iqr[j] if iqr[j] > 0 else 0.0
            bad_iqr += int((~((np.abs(a - b) <= tj) | ok)).sum())
        one = (len(kr) + len(kn) - 2 * len(com)) * fr.shape[1]
        cells = (len(kr) + len(kn) - len(com)) * fr.shape[1]
        r = dict(rows_ref=int(len(kr)), rows_new=int(len(kn)), both=int(len(com)), cells=int(cells), bad=int(bad + one),
                 ok_frac=1 - (bad + one) / max(cells, 1), ok_frac_iqr_desc=1 - (bad_iqr + one) / max(cells, 1),
                 worst_cols={int(j): round(colok[j], 6) for j in sorted(colok, key=colok.get)[:6]}, file=os.path.basename(fs[0]))
        out[v] = r; tot_cells += cells; tot_bad += bad + one
    out["ok_frac"] = 1 - tot_bad / max(tot_cells, 1)
    out["pass"] = tot_cells > 0 and out["ok_frac"] >= 0.999
    return out


def labels():
    from funding_label_pb import read_label
    cols = ["tEpochMs", "symbol", "nBars_72h"]
    out = {}
    refs, news = [], []
    for v, f in (("laba", "funding_label_20250701_to_20251001.pb"), ("labb", "funding_label_20251001_to_20260101.pb")):
        refs.append(read_label("/home/ubuntu/ds_label15m/" + f, usecols=cols))
        fs = sorted(glob.glob(OUTK + "/out/%s/*.pb" % v))
        out[v + "_files"] = [os.path.basename(x) for x in fs]
        news += [read_label(x, usecols=cols) for x in fs]
    ref, new = pd.concat(refs), pd.concat(news)
    sel = lambda d: d[(d.tEpochMs >= U_LO) & (d.tEpochMs <= L_MAX) & (d.tEpochMs % 900000 == 0)]
    ref, new = sel(ref), sel(new)
    M = ref.merge(new, on=["tEpochMs", "symbol"], how="outer", suffixes=("_r", "_n"), indicator=True)
    dev = M[M._merge != "right_only"]
    eq = (dev.nBars_72h_r == dev.nBars_72h_n)
    out.update(rows_ref=int(len(ref)), rows_new=int(len(new)), ref_found=int((dev._merge == "both").sum()),
               new_only=int((M._merge == "right_only").sum()), eq_frac_vs_dev=float(eq.mean()) if len(dev) else 0.0)
    out["pass"] = out["eq_frac_vs_dev"] >= 0.999
    return out


def main():
    res = json.load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else {}
    res.update(prereg="ADDENDUM-5 31e3c9e7", S=[S_LO, S_HI], tool1_label_lo_utc=U_LO, label_max=L_MAX)
    want = sys.argv[3].split(",") if len(sys.argv) > 3 else ["G", "T", "L"]
    for nm, fn in (("G_gate", gate), ("T_tool1", tool1), ("L_labels", labels)):
        if nm[0] not in want:
            continue
        try:
            res[nm] = fn()
        except Exception as e:  # noqa: BLE001
            res[nm] = dict(error=repr(e)[:400])
        log.info("%s %s", nm, json.dumps(res[nm], default=str)[:1500])
        json.dump(res, open(sys.argv[2], "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
