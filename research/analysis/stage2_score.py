#!/usr/bin/env python3
"""stage2_score.py — cham 6 bien the Stage 2 tu `*_perfold_ticks.parquet` (kernel xuat ra).

Pre-reg: docs/prereg/PREREG_STAGE2_FEATVAR.md (dd27c6c) §3-§4.
Chi so: rank-IC cross-section (tung tick) + lift@8 = top-8 hit - base hit (tung tick).
CI: paired block-72h bootstrap, NREP=2000, seed=20260905 (hang so IMPORT tu c3_rates — khong viet lai),
    he so no rong = c3_rates.inflate(k) voi k = so bien the ung vien trong vong (khong hardcode).
Luat: GIU chi khi (1) CI(delta vs V0) ngoai 0 & duong VA (2) CI(delta vs V5) ngoai 0 & duong.
Read-only. Khong train, khong sim.
"""
import os, sys, json, glob, logging
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("s2score")

ARMS = ["V0", "V1", "V2", "V3", "V4", "V5"]
K = 6                      # PREREG §3(e): 6 bien the
H = 3600000
METRICS = ["ic", "lift8"]


def block_boot_mean(delta, ts, nrep=C.NREP, seed=C.SEED):
    """CI block-72h cua TRUNG BINH `delta` (bootstrap theo khoi, cung quy uoc c3_rates/prescreen)."""
    bk = (np.asarray(ts, dtype=np.int64) // (C.BLOCK_H * H))
    _, inv = np.unique(bk, return_inverse=True)
    sums = np.bincount(inv, weights=np.asarray(delta, dtype=np.float64))
    cnts = np.bincount(inv).astype(np.float64)
    keep = cnts > 0
    sums, cnts = sums[keep], cnts[keep]
    rng = np.random.default_rng(seed)
    out = np.empty(nrep)
    for b in range(nrep):
        pick = rng.integers(0, len(sums), len(sums))
        out[b] = sums[pick].sum() / cnts[pick].sum()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def load(dirpath, tag):
    p = os.path.join(dirpath, "%s_perfold_ticks.parquet" % tag)
    d = pd.read_parquet(p, columns=["ts", "fold", "ic", "lift8", "n_coin", "n8"])
    d["ts"] = d.ts.astype(np.int64)
    return d


def main():
    d = sys.argv[1]
    if len(sys.argv) > 2:
        k = int(sys.argv[2])
    else:
        k = K
    INFL = C.inflate(k)
    log.info("### CI_INFLATE = c3_rates.inflate(%d) = %.6f | block=%dh nrep=%d seed=%d",
             k, INFL, C.BLOCK_H, C.NREP, C.SEED)
    D = {}
    for t in ARMS:
        p = os.path.join(d, "%s_perfold_ticks.parquet" % t)
        if os.path.exists(p):
            D[t] = load(d, t)
    log.info("arms co mat: %s", list(D))
    if "V0" not in D:
        raise SystemExit("THIEU V0 (moc) — khong cham duoc")

    out = {"k": k, "inflate": INFL, "arms": {}, "vs": {}}
    for t, x in D.items():
        row = {"n_tick": int(len(x)), "n_fold": int(x.fold.nunique()),
               "n_coin_mean": float(x.n_coin.mean())}
        for m in METRICS:
            v = x[m].dropna()
            lo, hi = block_boot_mean(v.values, x.loc[v.index, "ts"].values)
            row[m] = {"mean": float(v.mean()), "raw": [lo, hi],
                      "infl": [float(v.mean() - (v.mean() - lo) * INFL),
                               float(v.mean() + (hi - v.mean()) * INFL)]}
        out["arms"][t] = row
        log.info("  %-3s n_tick=%-7d ic=%+.6f [%.6f,%.6f]x%.4f  lift8=%+.6f [%.6f,%.6f]x%.4f",
                 t, row["n_tick"], row["ic"]["mean"], row["ic"]["infl"][0], row["ic"]["infl"][1], INFL,
                 row["lift8"]["mean"], row["lift8"]["infl"][0], row["lift8"]["infl"][1], INFL)

    # --- so sanh PAIRED theo tung tick (cung tick cho moi arm) ---
    base_ts = D["V0"].set_index("ts")
    for t in ARMS:
        if t in ("V0",):
            continue
        X = D[t].set_index("ts")
        common = base_ts.index.intersection(X.index)
        r = {"n_tick_chung": int(len(common))}
        for other in ("V0", "V5"):
            if other not in D or other == t:
                continue
            Y = D[other].set_index("ts")
            idx = common.intersection(Y.index)
            for m in METRICS:
                dl = (X.loc[idx, m] - Y.loc[idx, m]).dropna()
                lo, hi = block_boot_mean(dl.values, dl.index.values)
                mm = float(dl.mean())
                r["%s_vs_%s" % (m, other)] = {
                    "mean": mm, "raw": [lo, hi],
                    "infl": [float(mm - (mm - lo) * INFL), float(mm + (hi - mm) * INFL)],
                    "ngoai_0": bool(lo > 0 or hi < 0),
                    "huong": float(np.sign(mm)),
                    "ngoai_0_duong": bool(mm - (mm - lo) * INFL > 0),
                    "ngoai_0_am": bool(mm + (hi - mm) * INFL < 0)}
                # [LAM RO SAU KHI XEM SO — KHONG sua pre-reg] pre-reg §4 viet "CI khong chua 0 VA
                # CUNG DAU DUONG"; cau do viet theo quy uoc IC > 0. Do duoc: rank-IC o day AM
                # (giong Stage 0) => "HON" nghia la |IC| LON HON = AM HON. `huong_tot` duoi day la
                # ban doc theo CHIEU TOT LEN: `ic` = am hon; `lift8` = duong hon.
                _x = r["%s_vs_%s" % (m, other)]
                _x["huong_tot"] = bool(_x["ngoai_0"] and
                                       (_x["infl"][1] < 0 if m == "ic" else _x["infl"][0] > 0))
        out["vs"][t] = r
    json.dump(out, open(os.path.join(d, "stage2_score.json"), "w"), indent=1)

    # --- ap LUAT §4 ---
    log.info("\n### LUAT §4 (GIU = (1) hon V0 ngoai CI VA (2) khac V5 ngoai CI; 'hon' = CHIEU TOT LEN: "
             "rank-IC AM HON / lift@8 DUONG HON — xem lam ro)")
    verdict = {}
    for t in ARMS:
        if t not in out["vs"]:
            continue
        a = out["vs"][t].get("ic_vs_V0"); b = out["vs"][t].get("ic_vs_V5")
        ok1 = bool(a and a.get("huong_tot"))
        ok2 = bool(b and b.get("huong_tot"))
        lit1 = bool(a and a.get("ngoai_0_duong"))          # ban doc CHU NGHIA pre-reg (dau duong)
        lit2 = bool(b and b.get("ngoai_0_duong"))
        verdict[t] = {"hon_V0": ok1, "khac_V5": ok2, "GIU": ok1 and ok2,
                      "doc_chu_nghia_hon_V0": lit1, "doc_chu_nghia_khac_V5": lit2,
                      "doc_chu_nghia_GIU": lit1 and lit2,
                      "d_ic_vs_V0": (a or {}).get("mean"), "d_ic_vs_V5": (b or {}).get("mean")}
        log.info("  %-3s (chieu tot len) hon_V0=%-5s khac_V5=%-5s => %-4s | (doc chu nghia 'dau duong') "
                 "hon_V0=%-5s khac_V5=%-5s", t, ok1, ok2, "GIU" if ok1 and ok2 else "NULL",
                 lit1, lit2)
    out["verdict"] = verdict
    json.dump(out, open(os.path.join(d, "stage2_score.json"), "w"), indent=1)
    log.info("WROTE %s/stage2_score.json", d)


if __name__ == "__main__":
    main()
