"""AUDIT parity gate tang 2 (dyn) SIM vs LIVE — do offline, khong chay sim.

Cau hoi: SIM (SimulatorMarketLevelTicker1MStopLoss.createOrder:964-968) LUON goi
checkSignalDynamic cho leg PREDICT_SYMBOL_TRADE; LIVE (DetectEntrySignal2TradeNormal:652-659,
tu commit 311bb29) BYPASS khi SELECTOR_RANK_TOPK>0 => chi con checkSignal (gate phang 0.008).
Script do phan slot top-8 bi CHAN boi gate dyn ma gate phang cho qua, theo nam.

Nguon so: cong thuc + tham so doc THANG tu repo qua gate_cfg (profile x1_c3_full +
Configs.java + AIRejectFilter.java, KHONG hardcode); bins selector
WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1 (p0 = P(win); symbolPred = 1 - p0,
dao dau tai WfoDataset.buildFundingFromWfFiles:248); gate p15 = claudedata/wfo_gate_pred.csv.

Luoi: bins o 15m, nhung WfoDataset.forwardFillToGrid carry-forward moc selector ra MOI phut
market (stale <= 15m) => engine xet ung vien moi PHUT voi cung top-8, p15 doi tung phut.
Bao ca hai luoi (15m = moc selector, 1m = luoi engine that).
READ-ONLY.
"""
import glob
import logging
import os
import sys

import numpy as np
import pandas as pd

os.environ.setdefault("GATE_PROFILE",
                      "/home/ubuntu/src/BinanceFuturesJava/profiles/x1_c3_full.properties")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_cfg  # noqa: E402

LOG = logging.getLogger("gate_dyn_parity")
BINS = os.environ.get("BINS_DIR", "/home/ubuntu/predwf_map_s1a2_x1")
GATE = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
GRID = 900_000
TZ = 7 * 3_600_000
K = 8
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"),
               ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])


def load_gate():
    g = pd.read_csv(GATE, usecols=["timestamp", "predReturn15M"]).rename(
        columns={"timestamp": "ts", "predReturn15M": "p15"})
    return g.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def topk_bins():
    """Moi moc selector 15m -> 8 nguong dyn cua top-8 (sort tang), + so coin trong pool."""
    ts_out, thr_out, ncoin, spmed, spmin = [], [], [], [], []
    for f in sorted(glob.glob(BINS + "/predict_wf_*.bin")):
        a = np.fromfile(f, dtype=DT)
        ts = a["ts"].astype(np.int64)
        sp = 1.0 - a["p0"].astype(np.float64)     # DAO DAU: symbolPred = 1 - P(win)
        keep = ~np.isnan(sp)
        ts, sp = ts[keep], sp[keep]
        order = np.lexsort((sp, ts))              # ts tang; trong tick symbolPred tang (thap = tot)
        ts, sp = ts[order], sp[order]
        starts = np.flatnonzero(np.r_[True, ts[1:] != ts[:-1]])
        ends = np.r_[starts[1:], len(ts)]
        for s, e in zip(starts, ends):
            top = sp[s:min(e, s + K)]
            ts_out.append(int(ts[s]))
            thr_out.append(np.sort(gate_cfg.dyn_thr(top)))
            ncoin.append(int(e - s))
            spmed.append(float(np.median(top)))
            spmin.append(float(top.min()))
        LOG.info("%s -> %d moc 15m", os.path.basename(f), len(starts))
    o = np.argsort(ts_out)
    return (np.array(ts_out)[o], [thr_out[i] for i in o],
            np.array(ncoin)[o], np.array(spmed)[o], np.array(spmin)[o])


def report(df, label):
    df = df.copy()
    df["yr"] = pd.to_datetime(df.ts + TZ, unit="ms").dt.year
    df["flat_ok"] = df.p15 >= gate_cfg.MIN_MOMENTUM_15M
    df["slot_flat"] = np.where(df.flat_ok, df.nslot, 0)
    rows = []
    for yr, x in df.groupby("yr"):
        sf, sd = int(x.slot_flat.sum()), int(x.n_dyn.sum())
        rows.append({
            "yr": yr, "tick": len(x), "tick_flat_open": int(x.flat_ok.sum()),
            "tick_dyn_open": int((x.n_dyn > 0).sum()),
            "slot_flat": sf, "slot_dyn": sd,
            "pct_slot_dyn_block": 100.0 * (1 - sd / max(sf, 1)),
            "slot_dyn_ngoai_flat": int(x.loc[~x.flat_ok, "n_dyn"].sum()),
            "sp_top8_med": round(float(x.sp_med.median()), 4),
        })
    R = pd.DataFrame(rows)
    tot_f, tot_d = R.slot_flat.sum(), R.slot_dyn.sum()
    pd.set_option("display.width", 250)
    LOG.info("[%s]\n%s", label, R.round(3).to_string(index=False))
    LOG.info("[%s] TONG slot_flat=%d slot_dyn=%d => dyn CHAN %.2f%% slot ma gate phang cho qua",
             label, tot_f, tot_d, 100.0 * (1 - tot_d / max(tot_f, 1)))
    return R


def main():
    gate_cfg.describe()
    LOG.info("dyn_thr mau: sp=0.25 -> %.5f | sp=0.30 -> %.5f | sp=0.35 -> %.5f | san -> %.5f",
             gate_cfg.dyn_thr(0.25), gate_cfg.dyn_thr(0.30), gate_cfg.dyn_thr(0.35),
             gate_cfg.dyn_thr(0.0))
    G = load_gate()
    sel_ts, sel_thr, sel_n, sel_med, sel_min = topk_bins()
    nslot = np.minimum(sel_n, K)
    thr_mat = np.full((len(sel_ts), K), np.inf)
    for i, t in enumerate(sel_thr):
        thr_mat[i, :len(t)] = t

    # --- luoi 15m: chi moc selector ---
    p15_at = pd.Series(G.p15.values, index=G.ts.values)
    m15 = pd.DataFrame({"ts": sel_ts, "nslot": nslot,
                        "sp_med": sel_med}).merge(
        p15_at.rename("p15").reset_index().rename(columns={"index": "ts"}), on="ts", how="inner")
    j = np.searchsorted(sel_ts, m15.ts.values)
    m15["n_dyn"] = (thr_mat[j] <= m15.p15.values[:, None]).sum(axis=1)
    report(m15, "LUOI 15m (moc selector)")

    # --- luoi 1m: forward-fill selector ra moi phut market (stale <= 15m) ---
    idx = np.searchsorted(sel_ts, G.ts.values, side="right") - 1
    ok = (idx >= 0) & ((G.ts.values - sel_ts[np.clip(idx, 0, None)]) <= GRID)
    idx = idx[ok]
    m1 = pd.DataFrame({"ts": G.ts.values[ok], "p15": G.p15.values[ok],
                       "nslot": nslot[idx], "sp_med": sel_med[idx]})
    m1["n_dyn"] = (thr_mat[idx] <= m1.p15.values[:, None]).sum(axis=1)
    R1 = report(m1, "LUOI 1m (forward-fill, = engine)")
    R1.to_csv("/home/ubuntu/ledger/gate_dyn_parity_year.csv", index=False)
    LOG.info("saved /home/ubuntu/ledger/gate_dyn_parity_year.csv")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
