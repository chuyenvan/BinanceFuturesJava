"""VZ E1 - T9 (MASTER 10-14): spread net tren chan EXEC 2024 + chan troi dai 4h/24h.

PRE-REG: `research/vz/e1/configs/t9_config.json` (commit TRUOC khi tinh outcome).
(a) 6 709 chan EXEC 2024 (ledger ll_h2) khop su kien E1 theo CUM 30'; feature cua
    su kien khop; net do tren chinh CHAN: 60', 240', hold-to-exit (thoi diem thoat
    that e_ms tu ll_h2/legs.pkl, gia thoat = Vision kline1m close tai e_ms).
(b) Su kien crash E1: net 240' (co san) va 1 440' (tinh moi, cung cong thuc e1_core).
(c) H-E listing drift: bao them median / CI95 / ti le duong (khong tinh phep thu moi).

Chi doc du lieu 2024. Khong goi GO. 0 Java / 0 sim.
"""
import argparse
import csv
import gzip
import json
import os
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import e1_data
from e1_common import (CRASH_BAR_RET, MERGE_GAP_MS, MIN_QUOTE_VOLUME, OUT, REPORT,
                       block_bootstrap, bucket_of, setup_logging, write_json)
from e1_stats import day_level_boot, monotonicity, spread_ci

log = setup_logging("e1_t9", "e1_t9.log")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "configs", "t9_config.json")
LEDGER_CSV = os.path.expanduser("~/claude_master/1013/ll_h2/leadlag_h2_legs.csv.gz")
LEGS_PKL = os.path.expanduser("~/claude_master/1013/ll_h2/legs.pkl")
EVENTS = os.path.join(OUT, "e1_events_2024.parquet")
DIAG = os.path.join(OUT, "e1_exec_legs_2024_diag.parquet")
LEGS_OUT = os.path.join(OUT, "e1_t9_legs_2024.parquet")
NET_OUT = os.path.join(OUT, "e1_t9_events_net1440.parquet")
MONTHS = ["2024-%02d" % m for m in range(1, 13)]
H60, H240, H1440 = 60 * 60_000, 240 * 60_000, 1440 * 60_000
DATE = "2026-10-14"


# ------------------------------------------------------------------ legs meta
def legs_meta():
    """1 dong / chan EXEC 2024: (seed,row) tu ledger csv -> sym,s_ms,e_ms tu legs.pkl."""
    keys = []
    with gzip.open(LEDGER_CSV, "rt") as f:
        for r in csv.DictReader(f):
            if r["year07"] == "2024":
                keys.append((str(r["seed"]), str(r["row"])))
    k = pd.DataFrame(keys, columns=["seed", "row"])
    L = pd.read_pickle(LEGS_PKL)["L"][["seed", "row", "sym", "s_ms", "e_ms", "level"]].copy()
    L["seed"] = L["seed"].astype(str)
    L["row"] = L["row"].astype(str)
    m = k.merge(L, on=["seed", "row"], how="left")
    m["s_ms"] = m.s_ms.astype(np.int64)
    m["e_ms"] = m.e_ms.astype(np.int64)
    m["sym"] = m.sym.astype(str) + "USDT"
    m["s_day"] = (m.s_ms // 86_400_000).astype(np.int64)
    m["s_month"] = pd.to_datetime(m.s_ms, unit="ms", utc=True).dt.strftime("%Y-%m")
    log.info("legs 2024 = %d (rows with e_ms=%d)", len(m), int(m.e_ms.notna().sum()))
    return m


# ------------------------------------------------------------------ month IO
def frame_for(path, syms):
    t = pq.read_table(path, columns=["ts", "sym", "open", "close", "quote_volume", "active"])
    col = t.column("sym").combine_chunks()
    if isinstance(col, pa.DictionaryArray):
        d = np.array(col.dictionary.to_pylist(), dtype=object)
        codes = col.indices.to_numpy()
        have = d[codes]
    else:
        have = col.to_pandas().to_numpy()
    mask = pd.Series(have).isin(set(syms)).to_numpy()
    t = t.filter(pa.array(mask))
    df = t.to_pandas()
    df["sym"] = df.sym.astype(str)
    return df


def cluster_map(df):
    """(sym,ts)->rep_ts cho moi phut ung vien crash: cum = day lien tiep cach < 30'."""
    c = df[df.active.fillna(False).astype(bool) & (df.quote_volume >= MIN_QUOTE_VOLUME)]
    br = (c.close.astype(np.float32) - c.open.astype(np.float32)) / c.open.astype(np.float32)
    c = c[br <= np.float32(CRASH_BAR_RET)].sort_values(["sym", "ts"], kind="stable")
    out = {}
    ps, pt, rep = None, None, None
    for sym, ts in zip(c.sym.to_numpy(), c.ts.to_numpy(np.int64)):
        if sym != ps or (ts - pt) >= MERGE_GAP_MS:
            rep = int(ts)
        out[(sym, int(ts))] = rep
        ps, pt = sym, int(ts)
    return out


def asof_exact(ts_arr, t):
    j = int(np.searchsorted(ts_arr, t))
    return j if j < len(ts_arr) and ts_arr[j] == t else -1


# ------------------------------------------------------------------ measure
def measure():
    cfg = json.load(open(CONFIG))
    ensure = [OUT]
    for d in ensure:
        os.makedirs(d, exist_ok=True)
    ev = pq.read_table(EVENTS).to_pandas()
    ev["tss_reversal"] = ev.taker_sell_share - ev.tss_5
    ev["ts"] = ev.ts.astype(np.int64)
    legs = legs_meta()
    diag = pq.read_table(DIAG, columns=["sym", "s_ms", "cM"]).to_pandas()
    diag["s_ms"] = diag.s_ms.astype(np.int64)
    diagmap = {(s, int(t)): float(c) for s, t, c in
               zip(diag.sym.astype(str), diag.s_ms, diag.cM)}

    leg_rows = []
    net_rows = []
    t0 = time.time()
    prev_key = None
    for m in MONTHS:
        mi = MONTHS.index(m)
        nxt = MONTHS[mi + 1] if mi + 1 < len(MONTHS) else None
        ev_m = ev[ev.month == m]
        leg_m = legs[legs.s_month == m]
        syms = set(ev_m.sym.astype(str)) | set(leg_m.sym.astype(str))
        cur = frame_for(e1_data.kline_month(m), syms)
        nx = frame_for(e1_data.kline_month(nxt), syms) if nxt else None
        # clusters (chi thang m; chan trong thang m)
        cmap = cluster_map(cur)
        # per-sym arrays (cur + next, san theo ts)
        allf = cur if nx is None else pd.concat([cur, nx], ignore_index=True)
        allf = allf.sort_values(["sym", "ts"], kind="stable")
        look = {}
        for s, g in allf.groupby("sym", sort=False):
            look[s] = (g.ts.to_numpy(np.int64), g.open.to_numpy(np.float64),
                       g.close.to_numpy(np.float64))
        # ---- (b) net 1440 cho su kien thang m
        for s, ts, b in zip(ev_m.sym.astype(str), ev_m.ts, ev_m.bucket):
            rec = look.get(s)
            g1440 = np.nan
            if rec is not None:
                ta, oa, ca = rec
                j0 = asof_exact(ta, ts)
                j1 = asof_exact(ta, ts + H1440)
                if j0 >= 0 and j1 > j0 and ca[j0] > 0 and ca[j1] > 0:
                    g1440 = float(np.log(ca[j1] / ca[j0]))
            net_rows.append((s, int(ts), b, g1440))
        # ---- (a) chan EXEC thang m: entry/exit + bucket tren chinh phut s_ms
        for r in leg_m.itertuples(index=False):
            rec = look.get(r.sym)
            ent = c60 = c240 = cex = np.nan
            b = 0
            if rec is not None:
                ta, oa, ca = rec
                j0 = asof_exact(ta, r.s_ms)
                if j0 >= 0:
                    ent, c60, cex = ca[j0], np.nan, np.nan
                    j60 = asof_exact(ta, r.s_ms + H60)
                    j240 = asof_exact(ta, r.s_ms + H240)
                    je = asof_exact(ta, r.e_ms)
                    if j60 >= 0 and ca[j60] > 0:
                        c60 = ca[j60]
                    if j240 >= 0 and ca[j240] > 0:
                        c240 = ca[j240]
                    if je >= 0 and ca[je] > 0:
                        cex = ca[je]
                    b = bucket_of(ca[j0], oa[j0])
            rep = cmap.get((r.sym, int(r.s_ms)), -1)
            leg_rows.append((r.sym, int(r.s_ms), int(r.s_day), int(r.e_ms), int(rep),
                             int(b), ent, c60, c240, cex,
                             diagmap.get((r.sym, int(r.s_ms)), np.nan)))
        # free the month we no longer need as "next"
        if prev_key is not None:
            p = os.path.join(os.path.expanduser("~/vz_e1/raw"), "kline1m-%s.parquet" % prev_key)
            if os.path.exists(p):
                os.remove(p)
                log.info("released %s (elapsed %.0fs)", p, time.time() - t0)
        prev_key = m
        log.info("month %s legs=%d events=%d elapsed=%.0fs", m, len(leg_m), len(ev_m),
                 time.time() - t0)

    lg = pd.DataFrame(leg_rows, columns=["sym", "s_ms", "day", "e_ms", "rep_ts", "bucket",
                                         "p_ent", "p_60", "p_240", "p_exit", "cM"])
    lg["matched"] = lg.rep_ts > 0
    # feature cua su kien khop
    evk = ev[["sym", "ts", "doi_60", "doi_15", "prem_z7", "tss_reversal",
              "taker_sell_share", "tss_5"]].copy()
    evk["ts"] = evk.ts.astype(np.int64)
    evk = evk.rename(columns={"ts": "rep_ts", "sym": "sym"})
    lg = lg.merge(evk, on=["sym", "rep_ts"], how="left")
    # net theo cong thuc e1_core: log(P_exit/P_ent) - cost(bucket)
    from e1_common import cost_of
    cb = np.array([cost_of(b) for b in lg.bucket])
    cs = np.array([cost_of(b, True) for b in lg.bucket])
    for tag, pe in (("60", "p_60"), ("240", "p_240"), ("exit", "p_exit")):
        g = np.full(len(lg), np.nan)
        ok = np.isfinite(lg[pe]) & np.isfinite(lg.p_ent) & (lg.p_ent > 0) & (lg[pe] > 0)
        g[ok.to_numpy()] = np.log(lg[pe][ok].to_numpy() / lg.p_ent[ok].to_numpy())
        lg["gross_%s" % tag] = g
        lg["net_%s" % tag] = g - cb
        lg["net_stress_%s" % tag] = g - cs
    lg.to_parquet(LEGS_OUT, index=False)
    nr = pd.DataFrame(net_rows, columns=["sym", "ts", "bucket", "gross_1440"])
    nrc = np.array([cost_of(b) for b in nr.bucket])
    nrs = np.array([cost_of(b, True) for b in nr.bucket])
    nr["net_1440"] = nr.gross_1440 - nrc
    nr["net_stress_1440"] = nr.gross_1440 - nrs
    nr["day"] = (nr.ts // 86_400_000).astype(np.int64)
    nr.to_parquet(NET_OUT, index=False)
    # kiem chung: entry price Vision == cM cua diag
    okc = np.isfinite(lg.cM) & np.isfinite(lg.p_ent) & (lg.cM > 0)
    rel = np.abs(lg.p_ent[okc].to_numpy() / lg.cM[okc].to_numpy() - 1.0)
    val = {"n_legs": int(len(lg)), "n_matched_cluster": int(lg.matched.sum()),
           "n_entry_ok": int((np.isfinite(lg.p_ent)).sum()),
           "entry_vs_cM_match_1e-6": float((rel <= 1e-6).mean()) if okc.sum() else None,
           "n_net60": int(np.isfinite(lg.net_60).sum()),
           "n_net240": int(np.isfinite(lg.net_240).sum()),
           "n_netexit": int(np.isfinite(lg.net_exit).sum()),
           "exit_median_hours": float(np.median((lg.e_ms - lg.s_ms) / 3_600_000.0)),
           "n_events_net1440": int(np.isfinite(nr.net_1440).sum())}
    write_json(os.path.join(REPORT, "e1_t9_measure.json"), val)
    log.info("measure %s", val)
    return lg, nr, val


# ------------------------------------------------------------------ stats
def levels_quint(vals, edges):
    lv = np.zeros(len(vals), dtype=np.int64)
    ok = np.isfinite(vals)
    lv[ok] = np.searchsorted(np.asarray(edges, dtype=np.float64), vals[ok], side="right") + 1
    return lv


def levels_combo(df, cfg, a, b):
    ea = np.array(cfg["features"][a]["tercile_edges"], dtype=np.float64)
    eb = np.array(cfg["features"][b]["tercile_edges"], dtype=np.float64)
    va = df[a].to_numpy(np.float64)
    vb = df[b].to_numpy(np.float64)
    ok = np.isfinite(va) & np.isfinite(vb)
    la = np.searchsorted(ea, va, side="right") + 1
    lb = np.searchsorted(eb, vb, side="right") + 1
    lv = np.zeros(len(df), dtype=np.int64)
    lv[ok] = la[ok] * 10 + lb[ok]
    return lv


def levels_for(df, cfg, feat):
    if feat.startswith("combo("):
        return levels_combo(df, cfg, "prem_z7", "doi_15")
    return levels_quint(df[feat].to_numpy(np.float64), cfg["features"][feat]["edges"])


def eval_block(df, lv, hi, lo, horizons, daycol):
    out = {}
    for h in horizons:
        st = h.replace("net", "net_stress", 1)
        for tag, col in (("net", h), ("stress", st)):
            v = df[col].to_numpy(np.float64)
            boot, lvs = day_level_boot(v, df[daycol].to_numpy(np.int64), lv)
            levels = [int(x) for x in lvs if x > 0]
            rec = {"n_finite": int(np.isfinite(v).sum()),
                   "mono": monotonicity([boot[x]["mean"] for x in levels]),
                   "levels": {str(x): {k: vv for k, vv in boot[x].items() if k != "reps_mean"}
                              for x in levels}}
            if hi in boot and lo in boot:
                rec["spread_extreme"] = spread_ci(boot, lo, hi)
            out["%s|%s" % (tag, h)] = rec
    return out


def stats():
    cfg = json.load(open(CONFIG))
    lg = pd.read_parquet(LEGS_OUT)
    nr = pd.read_parquet(NET_OUT)
    ev = pq.read_table(EVENTS, columns=["sym", "ts", "day", "bucket", "doi_60",
                                        "doi_15", "prem_z7", "taker_sell_share",
                                        "tss_5", "net_240", "net_stress_240"]).to_pandas()
    ev["tss_reversal"] = ev.taker_sell_share - ev.tss_5
    ev["ts"] = ev.ts.astype(np.int64)
    ev1440 = ev.merge(nr[["sym", "ts", "net_1440", "net_stress_1440"]], on=["sym", "ts"], how="left")

    res = {"task": "T9", "date": DATE, "config": cfg, "variants": {}}
    for v in cfg["variants"]:
        df = lg if v["group"] == "a" else ev1440
        daycol = "day"
        lv = levels_for(df, cfg, v["feature"])
        rec = {"id": v["id"], "group": v["group"], "feature": v["feature"],
               "n_rows": int((lv > 0).sum()),
               "levels_present": sorted(int(x) for x in np.unique(lv) if x > 0),
               "metrics": eval_block(df, lv, v["hi"], v["lo"], v["horizons"], daycol)}
        res["variants"][v["id"]] = rec
        log.info("T9 %s n=%d", v["id"], rec["n_rows"])

    # (c) H-E extras (khong tinh phep thu moi)
    dr = pq.read_table(os.path.join(OUT, "e1_listing_drift.parquet")).to_pandas()
    dr["day0"] = (dr.t0 // 86_400_000).astype(np.int64)
    c = {}
    for h in (1, 3, 7, 30):
        s = dr[dr.h_days == h]
        b = block_bootstrap(s.ret.to_numpy(np.float64), s.day0.to_numpy(np.int64))
        c["%dd" % h] = {"n": b["n"], "mean": b["mean"], "median": b["median"],
                        "ci95_mean": b["ci95_mean"], "ci95_median": b["ci95_median"],
                        "frac_pos": float((s.ret > 0).mean()),
                        "ci95_frac_pos": b["ci95_hit"]}
    res["c_listing_drift"] = c
    write_json(os.path.join(REPORT, "e1_t9.json"), res)
    log.info("T9 stats written")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    if a.measure:
        measure()
    if a.stats:
        stats()
    if not (a.measure or a.stats):
        print("use --measure / --stats")
