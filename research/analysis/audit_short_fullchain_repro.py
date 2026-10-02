#!/usr/bin/env python3
"""audit_short_fullchain_repro.py — AUDIT doc lap SHORT_FULLCHAIN (b61ae757): tai lap 1 lat + funding EXACT
+ chan doan SL-uu-tien-cung-nen + 20 lenh mau entry. CHI DOC (Aerospike read-only, khong ghi dia ngoai --out).

Chay tren Oracle (noi co du lieu), vi du lat 2024 (khop by_year['2024'] trong RESULT_SHORT_FULLCHAIN.json):
  python3 research/analysis/audit_short_fullchain_repro.py --slice 2024 \
      --fund-cache /tmp/fund_cache.npz --out /tmp/audit_sfc_2024.json
Dung NGUYEN build_picks/sim/exits/agg cua short_fullchain_sim.py (khong viet lai thuat toan).
"""
import argparse, json, os, sys, time
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import short_fullchain_sim as S  # noqa
from short_v3_score import Fund  # noqa  (funding exact, quy uoc rate>0 => SHORT NHAN)

TZ7 = S.TZ7
H = S.H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="/home/ubuntu/ledger/pred_s1a2x1.parquet")
    ap.add_argument("--gate-csv", default="/home/ubuntu/src/BinanceFuturesJava/research/parity/data/p15_dev.csv")
    ap.add_argument("--map-csv", default="/home/ubuntu/claudedata/oi/symbol_map.csv")
    ap.add_argument("--aero", default="127.0.0.1:3222")
    ap.add_argument("--slice", default="2024", help="YYYY (cua so y het sim goc) hoac YYYYQn")
    ap.add_argument("--fund-cache", required=True)
    ap.add_argument("--nsample", type=int, default=20)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    y = int(a.slice[:4])
    if "Q" in a.slice:
        q = int(a.slice[-1]); m1 = 3 * (q - 1) + 1
        st = datetime(y, m1, 1, tzinfo=TZ7)
        en = (datetime(y + (m1 + 3 > 12), (m1 + 3 - 1) % 12 + 1, 1, tzinfo=TZ7) + timedelta(days=3))
    else:  # cua so y het main() goc
        st = datetime(y, 1, 1, tzinfo=TZ7)
        en = datetime(y, 12, 31, 23, 59, tzinfo=TZ7) if y == 2025 else datetime(y + 1, 1, 3, tzinfo=TZ7)
    pk = S.build_picks(a.panel)
    pk = pk[(pk["ts"] + 72 * H) <= S.DEV_END_MS]
    lo_ms = int(st.timestamp() * 1000) - 15 * 60000; hi_ms = int(en.timestamp() * 1000)
    pk = pk[(pk.ts >= lo_ms) & (pk.ts <= hi_ms)].reset_index(drop=True)   # thu union -> tiet kiem RAM
    print("slice %s picks=%d" % (a.slice, len(pk)), flush=True)
    g = pd.read_csv(a.gate_csv, usecols=["ts", "predRisk4H"]); g["min"] = g["ts"] // 60000
    gmin = g.groupby("min")["predRisk4H"].first()
    q10 = float(gmin.quantile(0.10)); q90 = float(gmin.quantile(0.90))
    smap = pd.read_csv(a.map_csv); id2name = dict(zip(smap.symId.astype(int), smap.symbol))
    rts, rsym, rg, rpnl, rheld = S.sim(pk, id2name, gmin.to_dict(), None, a.aero, [(st, en, y)])
    ts = np.asarray(rts, np.int64); sym = np.asarray(rsym, np.int64); gg = np.asarray(rg, np.float64)
    # ---- funding EXACT: sum rate trong (entry, entry+held], entry = ts+15m (close nen m0+14) ----
    F = Fund(a.fund_cache)
    fsid = np.array([F.s2i.get(id2name.get(int(s), ""), -1) for s in sym])
    entry = ts + 15 * 60000
    res = {"slice": a.slice, "n": int(len(ts)), "q10": q10, "q90": q90,
           "fund_cover": float((fsid >= 0).mean()), "variants": {}}
    br = {"A_all": np.ones(len(ts), bool), "B_CHAN_q10": ~(gg <= q10),
          "C_THUAN_q90": gg >= q90, "D_NGHICH_q10": gg <= q10}
    for c in S.COMBOS:
        if not (c[1] in (0.10, 1.00)):
            continue
        pnl = np.asarray(rpnl[c], np.float64); held = np.asarray(rheld[c], np.float64)
        fex = np.full(len(ts), np.nan)
        for s in np.unique(fsid[fsid >= 0]):
            i = np.where(fsid == s)[0]
            b0, b1 = F.bounds[s], F.bounds[s + 1]
            ta, ca = F.ts[b0:b1], F.cum[b0:b1 + 1]
            lo = np.searchsorted(ta, entry[i], side="right")
            hi = np.searchsorted(ta, entry[i] + (held[i] * 60000).astype(np.int64), side="right")
            fex[i] = ca[hi] - ca[lo]
        key = "T%d_SL%d_TS%dh" % (int(c[0] * 100), int(c[1] * 100), c[2])
        nsl = int(np.isclose(pnl, -c[1]).sum())      # so lenh thoat bang SL (= tie cung nen, xem audit)
        for vn, m in br.items():
            m = m & np.isfinite(gg) & np.isfinite(pnl)
            const = pnl[m] - S.COST_BASE - S.FUND72 * held[m] / 4320.0
            exact = pnl[m] - S.COST_BASE + np.nan_to_num(fex[m])
            yy = pd.to_datetime(ts[m], unit="ms", utc=True).tz_convert("Asia/Bangkok").year
            ag = S.agg(pnl[m] + S.FUND72 * held[m] / 4320.0 + np.nan_to_num(fex[m]), held[m], ts[m])
            res["variants"].setdefault(vn, {})[key] = {
                "n": int(m.sum()), "net_const_pickw": float(const.mean()),
                "net_const_by_year_slice": float(const[yy == y].mean()) if (yy == y).any() else None,
                "net_exact_pickw": float(exact.mean()),
                "fund_exact_mean": float(np.nan_to_num(fex[m]).mean()),
                "fund_const_mean": float(-(S.FUND72 * held[m] / 4320.0).mean()),
                "agg_exact_tickw": ag, "n_SL_exit": nsl}
    # ---- 20 lenh mau: kiem entry offset (ts = OPEN nen 15m; entry = close 1m tai m0+14) ----
    import aerospike, cramjam
    h_, p_ = a.aero.split(":"); cli = aerospike.client({"hosts": [(h_, int(p_))]}).connect()
    rng = np.random.default_rng(20261002); smp = []
    for j in rng.choice(len(ts), size=min(a.nsample, len(ts)), replace=False):
        m0 = int(ts[j]) // 60000; nm = id2name[int(sym[j])].encode(); row = {"ts": int(ts[j]), "sym": nm.decode()}
        for off in (13, 14, 15):
            k = datetime.fromtimestamp((m0 + off) * 60, TZ7).strftime("%Y%m%d-%H%M")
            try:
                _, _, bins = cli.get(("test", "kline_1m_opt", k))
                v = S.parse_needed(bytes(cramjam.snappy.decompress_raw(bins["data"])), {nm}).get(nm)
            except Exception as e:
                v = repr(e)
            row["m0+%d" % off] = {"key": k, "hlc": v}
        row["pnl_T3_SL10_TS24h"] = float(rpnl[(0.03, 0.10, 24)][j]); row["held_min"] = float(rheld[(0.03, 0.10, 24)][j])
        smp.append(row)
    res["samples"] = smp
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("JSON ->", a.out, "%.0fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
