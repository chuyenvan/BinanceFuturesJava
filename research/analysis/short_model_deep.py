#!/usr/bin/env python3
"""short_model_deep.py — CHAM SAU cho PREREG_SHORT_DEEP (0-sim, offline, tai cho).

Doc `predict_wf_*.bin` (slot 3 = head 72h) + nhan `.pb` (nhieu horizon) + funding cache
(Aerospike scan -> npz), roi do NGUYEN cac chi so da khoa trong
`docs/prereg/PREREG_SHORT_DEEP.md` §4 (co che cat) · §5 (funding) · §6 (chi so/CI/phan ra).

KHONG train, KHONG sim, KHONG cham .java. Chi doc lai bins/nhan/funding co san.

Co che cat:
  - CUNG C in {0.20,0.30,0.40,0.50,0.70,0.90}: pnl=-C neu maxFav_72h>=C else -retEnd_72h
  - TIME-STOP T in {12h,24h} (48h KHONG co trong nhan -> bao thieu):
        pnl=-retEnd_Th (nBars_Th>=T/15); va TIME-STOP+C: pnl=-C neu maxFav_Th>=C else -retEnd_Th
  - MEM 2 tang (S,C): pnl=-C neu mfav>=C ; -(S+C)/2 neu S<=mfav<C ; -retEnd_72h neu mfav<S
  - UB lookahead P in {0.05,0.10,0.20}: pnl=+P neu maxAdv_72h>=P else -retEnd_72h  (CAN TREN, khong phai co che)

Funding (short, PERP): f_frac = sum rate(sym,tau) voi tau in (t, t+T]  (rate>0 => short NHAN)
  => pnl_co_funding = pnl + f_frac.  borrow = 0 (PERP). Liquidation KHONG mo hinh.

Chay:
  python3 short_model_deep.py --bins-root DIR --arms SHORT42:SHORT42,SHORT13:SHORT13 \
      --labels-dir /home/ubuntu/claudedata/wfo15m/label_ds_15m \
      --map-csv /home/ubuntu/claudedata/kaggle_oi_stage/symbol_map.csv \
      --fund-cache /tmp/fund_cache.npz --out /tmp/smdeep.json
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import short_model_score as SMS  # read_bins, ci_mean

H = 3600000
CUTS = (0.20, 0.30, 0.40, 0.50, 0.70, 0.90)
SOFT_S = (0.15, 0.20, 0.30)
SOFT_C = (0.30, 0.40, 0.50, 0.60)
TS_H = (12, 24)
UB_P = (0.05, 0.10, 0.20)
NEED72 = 288
DEV_CUT = 1767225600000  # 2026-01-01
FOLDS = "20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001," \
        "20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001"

COL72 = ["retEnd_72h", "maxFav_72h", "maxAdv_72h", "nBars_72h"]
COLT = {h: ["retEnd_%dh" % h, "maxFav_%dh" % h, "nBars_%dh" % h] for h in TS_H}


# ─────────────────────── nhan ───────────────────────

def load_labels_deep(lb_dir, map_csv):
    """-> key, ts, sym, + dict arr theo horizon."""
    cdir = os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code")
    if cdir not in sys.path:
        sys.path.insert(0, cdir)
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(glob.glob(lb_dir + "/funding_label_15m_*.pb"))
    fs = [f for f in fs if ".part" not in f]
    use = ["tEpochMs", "symbol"] + COL72
    for h in TS_H:
        use += COLT[h]
    out = {k: [] for k in ["ts", "sy"] + COL72}
    for h in TS_H:
        for c in COLT[h]:
            out[c] = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=use)
        d = d[(d["nBars_72h"] >= NEED72) & d["retEnd_72h"].notna() & (d.tEpochMs < DEV_CUT)]
        if not len(d):
            continue
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        if not k.any():
            continue
        sid = sid[k].to_numpy(np.int32)
        out["ts"].append(d.tEpochMs.to_numpy(np.int64)[k])
        out["sy"].append(sid)
        for c in COL72:
            out[c].append(d[c].to_numpy(np.float32)[k])
        for h in TS_H:
            for c in COLT[h]:
                out[c].append(d[c].to_numpy(np.float32)[k])
    res = {}
    for k2, v in out.items():
        res[k2] = np.concatenate(v)
    key = res["ts"] * SMS.RES + res["sy"].astype(np.int64)
    o = np.argsort(key, kind="stable")
    for k2 in res:
        res[k2] = res[k2][o]
    return res


def btc_regime(lbl):
    """dict ts -> +1/-1 theo retEnd_72h cua BTC (proxy regime)."""
    # tim symId cua BTC tu map da nan (dung ten 'BTCUSDT')
    return None  # dien o main (can symbol_map)


# ─────────────────────── funding ───────────────────────

class Fund:
    def __init__(self, npz):
        z = np.load(npz, allow_pickle=True)
        self.syms = [str(s) for s in z["syms"]]
        self.ts = z["ts"].astype(np.int64)
        self.rt = z["rt"].astype(np.float64)
        self.sid = z["sid"].astype(np.int32)
        o = np.argsort(self.sid, kind="stable")
        self.ts, self.rt, self.sid = self.ts[o], self.rt[o], self.sid[o]
        self.bounds = np.searchsorted(self.sid, np.arange(len(self.syms) + 1))
        self.cum = np.zeros(len(self.ts) + 1)
        np.cumsum(self.rt, out=self.cum[1:])
        # ban CLIP tran |rate|<=0.0075/settle (do nhay, PREREG §5)
        self.rtc = np.clip(self.rt, -0.0075, 0.0075)
        self.cumc = np.zeros(len(self.ts) + 1)
        np.cumsum(self.rtc, out=self.cumc[1:])
        self.s2i = {s: i for i, s in enumerate(self.syms)}

    def _win(self, sym_ids, t, h_ms, ts, cum):
        out = np.zeros(len(t))
        sid_of = np.array([self.s2i.get(s, -1) for s in sym_ids], dtype=np.int32)
        for sid in np.unique(sid_of):
            if sid < 0:
                continue
            m = sid_of == sid
            a, b = self.bounds[sid], self.bounds[sid + 1]
            ta, ca = ts[a:b], cum[a:b + 1]
            lo = np.searchsorted(ta, t[m], side="right")
            hi = np.searchsorted(ta, t[m] + h_ms, side="right")
            out[m] = ca[hi] - ca[lo]
        return out

    def sum_win(self, sym_ids, t, h_ms):
        """sum rate trong (t, t+h] cho tung cap (syms[i], t[i]); sym_ids = ten string."""
        return self._win(sym_ids, t, h_ms, self.ts, self.cum)

    def sum_win_clip(self, sym_ids, t, h_ms):
        return self._win(sym_ids, t, h_ms, self.ts, self.cumc)


# ─────────────────────── dung cong cu ───────────────────────

def per_tick(vals, ts):
    """gop theo tick (mean), tra ve (pt_vals, pt_ts) da sort theo ts."""
    s = pd.Series(vals).groupby(pd.Series(ts)).mean()
    return s.to_numpy(), s.index.to_numpy(np.int64)


def mech_block(S, fund, cost, T_ms, direction="short"):
    """S = DataFrame [ts,sym,ret72,mfav72,madv72,ret12,mfav12,nb12,ret24,mfav24,nb24].
    Tra ve dict cac co che: net (mean-seed chua gop) + by_year + cut_rate + tail."""
    t = S["ts"].to_numpy(np.int64)
    ret72 = S["retEnd_72h"].to_numpy(np.float64)
    mf72 = S["maxFav_72h"].to_numpy(np.float64)
    madv = S["maxAdv_72h"].to_numpy(np.float64)
    fund72 = fund.sum_win(S["sym"].tolist(), t, T_ms)          # fraction (rate units)
    fund72c = fund.sum_win_clip(S["sym"].tolist(), t, T_ms)   # ban clip |rate|<=0.0075
    out = {}

    def emit(name, gross_pnl, fund_add, extra=None):
        pt, pts = per_tick(gross_pnl, t)
        net = pt - cost
        rec = {"net": SMS.ci_mean(net, pts),
               "net_stress": SMS.ci_mean(pt - 0.0015, pts),
               "gross": SMS.ci_mean(pt, pts),
               "by_year_net": by_year(net, pts),
               "by_year_gross": by_year(pt, pts),
               "n_trade": int(len(S)), "n_tick": int(len(pts)),
               "tail_p99": round(float(np.percentile(gross_pnl, 1)), 6),
               "tail_max": round(float(gross_pnl.min()), 6)}
        if fund_add is not None:
            ptF, _ = per_tick(gross_pnl + fund_add, t)
            netF = ptF - cost
            rec["net_funded"] = SMS.ci_mean(netF, pts)
            rec["by_year_net_funded"] = by_year(netF, pts)
            rec["fund_mean_pct"] = round(float(100 * fund_add.mean()), 6)
            ptC, _ = per_tick(gross_pnl + fund72c, t)
            netC = ptC - cost
            rec["net_funded_clip"] = SMS.ci_mean(netC, pts)
            rec["by_year_net_funded_clip"] = by_year(netC, pts)
            rec["fund_clip_mean_pct"] = round(float(100 * fund72c.mean()), 6)
        if extra:
            rec.update(extra)
        out[name] = rec

    sgn = -1.0 if direction == "short" else 1.0
    g0 = sgn * ret72
    emit("none", g0, fund72 if direction == "short" else None)
    if direction != "short":
        return out
    for C in CUTS:
        stop = mf72 >= C
        g = np.where(stop, -C, -ret72)
        emit("hard_%.2f" % C, g, fund72, {"cut_rate": round(float(stop.mean()), 6)})
    for S_ in SOFT_S:
        for C in SOFT_C:
            if S_ >= C:
                continue
            g = np.where(mf72 >= C, -C, np.where(mf72 >= S_, -(S_ + C) / 2.0, -ret72))
            emit("soft_%.2f_%.2f" % (S_, C), g, fund72,
                 {"tier1_rate": round(float((mf72 >= S_).mean()), 6),
                  "tier2_rate": round(float((mf72 >= C).mean()), 6)})
    # time-stop (no cut) + time-stop+cut
    for h in TS_H:
        rt = S["retEnd_%dh" % h].to_numpy(np.float64)
        mf = S["maxFav_%dh" % h].to_numpy(np.float64)
        nb = S["nBars_%dh" % h].to_numpy(np.float64)
        ok = nb >= (h * 4)          # h*60min/15min = h*4 bars
        fh = fund.sum_win(S["sym"].tolist(), t, h * H)
        fhc = fund.sum_win_clip(S["sym"].tolist(), t, h * H)
        g = -rt
        pt, pts = per_tick(g[ok], t[ok])
        net = pt - cost
        rec = {"net": SMS.ci_mean(net, pts), "by_year_net": by_year(net, pts),
               "n_trade": int(ok.sum()), "n_tick": int(len(pts)),
               "tail_p99": round(float(np.percentile(g[ok], 1)), 6),
               "tail_max": round(float(g[ok].min()), 6)}
        ptF, _ = per_tick(g[ok] + fh[ok], t[ok])
        rec["net_funded"] = SMS.ci_mean(ptF - cost, pts)
        rec["by_year_net_funded"] = by_year(ptF - cost, pts)
        rec["net_funded_clip"] = SMS.ci_mean(per_tick(g[ok] + fhc[ok], t[ok])[0] - cost, pts)
        rec["by_year_net_funded_clip"] = by_year(per_tick(g[ok] + fhc[ok], t[ok])[0] - cost, pts)
        rec["fund_mean_pct"] = round(float(100 * fh[ok].mean()), 6)
        rec["fund_clip_mean_pct"] = round(float(100 * fhc[ok].mean()), 6)
        out["tstop_%dh" % h] = rec
        for C in (0.30, 0.50):
            g2 = np.where(mf[ok] >= C, -C, g[ok])
            pt2, pts2 = per_tick(g2, t[ok])
            net2 = pt2 - cost
            pt2F, _ = per_tick(g2 + fh[ok], t[ok])
            out["tstop_%dh_cut%.2f" % (h, C)] = {
                "net": SMS.ci_mean(net2, pts2), "by_year_net": by_year(net2, pts2),
                "net_funded": SMS.ci_mean(pt2F - cost, pts2),
                "by_year_net_funded": by_year(pt2F - cost, pts2),
                "cut_rate": round(float((mf[ok] >= C).mean()), 6),
                "n_trade": int(ok.sum()),
                "fund_mean_pct": round(float(100 * fh[ok].mean()), 6)}
    # UB lookahead (maxAdv_72h luu GIA TRI AM = muc GIAM)
    for P in UB_P:
        hitub = madv <= -P
        g = np.where(hitub, P, -ret72)
        emit("UB_lookahead_%.2f" % P, g, None,
             {"hit_rate": round(float(hitub.mean()), 6)})
    out["_funding"] = {
        "pct_trade_receive": round(float((fund72 > 0).mean()), 6),
        "pct_trade_pay": round(float((fund72 < 0).mean()), 6),
        "fund72_mean_pct": round(float(100 * fund72.mean()), 6),
        "fund72_p01_pct": round(float(100 * np.percentile(fund72, 1)), 6),
        "fund72_med_pct": round(float(100 * np.percentile(fund72, 50)), 6),
        "fund72_p99_pct": round(float(100 * np.percentile(fund72, 99)), 6),
        "fund72_clip_mean_pct": round(float(100 * fund72c.mean()), 6),
        "fund72_clip_med_pct": round(float(100 * np.percentile(fund72c, 50)), 6),
    }
    return out


def by_year(vals, ts):
    y = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Bangkok").year.to_numpy()
    o = {}
    for yr in (2022, 2023, 2024, 2025):
        m = y == yr
        o[yr] = round(float(np.asarray(vals)[m].mean()), 6) if m.sum() else None
    return o


def decompose(S, fund, T_ms, btc_ts_ret, year):
    """Phan ra nam `year`: theo quy, coin, regime, entry-type. Tra ve dict gon."""
    t = S["ts"].to_numpy(np.int64)
    y = pd.to_datetime(t, unit="ms", utc=True).tz_convert("Asia/Bangkok")
    m = y.year.to_numpy() == year
    Sx = S.loc[m]
    t = t[m]
    ret72 = Sx["retEnd_72h"].to_numpy(np.float64)
    mf72 = Sx["maxFav_72h"].to_numpy(np.float64)
    g = -ret72                                     # gross short, KHONG cat
    cost = 0.00112
    fund72 = fund.sum_win(Sx["sym"].tolist(), t, T_ms)
    q = y[m].quarter.to_numpy()
    mon = y[m].month.to_numpy()
    res = {"year": year, "n_trade": int(m.sum()),
           "gross_nocut_pct": round(float(100 * g.mean()), 5),
           "net_nocut_pct": round(float(100 * (g.mean() - cost)), 5),
           "net_nocut_funded_pct": round(float(100 * (g.mean() + fund72.mean() - cost)), 5),
           "net_hard30_pct": round(float(100 * (np.where(mf72 >= 0.30, -0.30, g).mean() - cost)), 5),
           "by_quarter_net_pct": {}, "by_month_net_pct": {},
           "neg_coins": [], "regime": {}, "mfav_bucket": {}, "cost_pp_pct": round(100 * cost, 4),
           "fund_pp_pct": round(float(100 * fund72.mean()), 5)}
    for qq in (1, 2, 3, 4):
        mm = q == qq
        if mm.sum():
            res["by_quarter_net_pct"][qq] = round(float(100 * (g[mm].mean() - cost)), 5)
    for mo in range(1, 13):
        mm = mon == mo
        if mm.sum():
            res["by_month_net_pct"][mo] = round(float(100 * (g[mm].mean() - cost)), 5)
    # coin dong gop am
    dfs = pd.DataFrame({"sym": Sx["sym"].to_numpy(), "g": g})
    agg = dfs.groupby("sym")["g"].agg(["mean", "size"]).sort_values("mean")
    res["neg_coins"] = [[str(s), round(float(r["mean"]) * 100, 3), int(r["size"])]
                        for s, r in agg.head(8).iterrows()]
    # regime BTC
    if btc_ts_ret is not None:
        bts, bret = btc_ts_ret
        idx = np.clip(np.searchsorted(bts, t), 0, len(bts) - 1)
        hit = bts[idx] == t
        up = np.where(hit, bret[idx] >= 0, np.nan)
        for nm, sel in (("up", up == True), ("down", up == False)):
            sel = np.asarray(sel) & hit
            if sel.sum():
                res["regime"][nm] = {"net_pct": round(float(100 * (g[sel].mean() - cost)), 5),
                                     "n": int(sel.sum()),
                                     "hitrate_fav30": round(float((mf72[sel] >= 0.30).mean()), 4)}
    # entry-type theo bucket maxFav_72h
    edges = [0.0, 0.05, 0.10, 0.20, 0.30, 100.0]
    lab = ["<5%", "5-10%", "10-20%", "20-30%", ">=30%"]
    for i in range(len(edges) - 1):
        selb = (mf72 >= edges[i]) & (mf72 < edges[i + 1])
        if selb.sum():
            res["mfav_bucket"][lab[i]] = {
                "net_pct": round(float(100 * (g[selb].mean() - cost)), 5),
                "n": int(selb.sum()),
                "net_hard30_pct": round(float(100 * (np.where(mf72[selb] >= 0.30, -0.30, g[selb]).mean() - cost)), 5)}
    return res


# ─────────────────────── main ───────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", required=True, help="TAG:DIR,... (tat ca SHORT)")
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--map-csv", required=True)
    ap.add_argument("--fund-cache", default="")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--cost", type=float, default=0.00112)
    ap.add_argument("--folds", default=FOLDS)
    ap.add_argument("--decomp-years", default="2023,2024")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    folds = [x.strip() for x in a.folds.split(",") if x.strip()]

    t0 = time.time()
    lbl = load_labels_deep(a.labels_dir, a.map_csv)
    print("### nhan: %d dong (%.1f phut)" % (len(lbl["ts"]), (time.time() - t0) / 60), flush=True)
    key = lbl["ts"] * SMS.RES + lbl["sy"].astype(np.int64)
    sym_series = pd.Series(lbl["sy"])

    smap = pd.read_csv(a.map_csv)
    # regime proxy: BTC KHONG co trong nhan -> dung median thi truong cua retEnd_72h theo tick
    mk = pd.Series(lbl["retEnd_72h"].astype(np.float64)).groupby(
        pd.Series(lbl["ts"])).median()
    btc_ts_ret = (mk.index.to_numpy(np.int64), mk.to_numpy(np.float64))

    fund = Fund(a.fund_cache) if a.fund_cache else None
    T_ms = 72 * H
    res = {"prereg": "docs/prereg/PREREG_SHORT_DEEP.md", "k": a.k, "cost": a.cost,
           "cuts": list(CUTS), "soft": {"S": list(SOFT_S), "C": list(SOFT_C)},
           "time_stop_h": list(TS_H), "time_stop_48h": "KHONG_CO_NHAN(4/12/24/72h)",
           "ub_lookahead": list(UB_P), "ci": {"block_h": SMS.BLOCK_H, "nrep": SMS.NREP,
           "seed": SMS.SEED, "legacy": SMS.LEG}, "arms": {}, "decomp": {}}
    for spec in a.arms.split(","):
        spec = spec.strip()
        if not spec:
            continue
        tag, d = spec.split(":")
        dirp = os.path.join(a.bins_root, d)
        files = [os.path.join(dirp, "predict_wf_%s.bin" % f) for f in folds]
        have = [f for f in files if os.path.exists(f)]
        if not have:
            print("### arm %s: KHONG co bins" % tag, flush=True)
            res["arms"][tag] = {"error": "no bins"}
            continue
        ts, sym, p = SMS.read_bins(have)
        kk = ts * SMS.RES + sym.astype(np.int64)
        ip = np.clip(np.searchsorted(key, kk), 0, len(key) - 1)
        hit = key[ip] == kk
        ts, sym, p, ip = ts[hit], sym[hit], p[hit], ip[hit]
        ret = lbl["retEnd_72h"][ip].astype(np.float64)
        ok = np.isfinite(p) & np.isfinite(ret)
        ts, sym, p, ip = ts[ok], sym[ok], p[ok], ip[ok]
        d = {"n_tick": int(pd.unique(ts).size), "n_rows": int(len(ts)), "n_files": len(have)}
        # rank-IC
        g = pd.DataFrame({"ts": ts, "p": p.astype(np.float64), "ret": ret})
        grp = g.groupby("ts", sort=False)
        g["n"] = grp["p"].transform("size")
        g["r"] = grp["p"].rank(method="first")
        g["rk"] = grp["ret"].rank(method="first")
        x = g["r"].to_numpy(); yv = g["rk"].to_numpy()
        tmp = pd.DataFrame({"ts": g["ts"].to_numpy(), "x": x, "y": yv,
                            "x2": x * x, "y2": yv * yv, "xy": x * yv})
        ag = tmp.groupby("ts", sort=False).agg(sr=("x", "sum"), sy=("y", "sum"),
              sx=("x2", "sum"), syy=("y2", "sum"), sxy=("xy", "sum"), n=("x", "size"))
        del tmp, x, yv
        num = ag.n * ag.sxy - ag.sr * ag.sy
        den = np.sqrt((ag.n * ag.sx - ag.sr ** 2) * (ag.n * ag.syy - ag.sy ** 2))
        ic_t = (-num / den.replace(0, np.nan)).dropna()
        d["ic"] = SMS.ci_mean(ic_t.to_numpy(), ic_t.index.to_numpy(np.int64))
        # K8 selection
        sel = g["r"] > (g["n"] - a.k)
        S = pd.DataFrame({"ts": ts[sel.to_numpy()], "sym": sym[sel.to_numpy()]})
        idx = np.where(sel.to_numpy())[0]
        for c in COL72:
            S[c] = lbl[c][ip[idx]]
        for h in TS_H:
            for c in COLT[h]:
                S[c] = lbl[c][ip[idx]]
        # sym name
        i2n = dict(zip(smap.symId.astype(np.int32), smap.symbol.astype(str)))
        S["sym"] = S["sym"].map(i2n)
        direction = "long" if tag.startswith("LONG") else "short"
        d["direction"] = direction
        d["mech"] = mech_block(S, fund, a.cost, T_ms, direction)
        res["arms"][tag] = d
        print("### arm %s: IC=%.5f out_both=%s | none_net=%.5f funded=%.5f"
              % (tag, d["ic"]["mean"], d["ic"]["out_both"],
                 d["mech"]["none"]["net"]["mean"],
                 d["mech"]["none"].get("net_funded", {}).get("mean", float("nan"))),
              flush=True)
        for yy in ([int(x) for x in a.decomp_years.split(",")] if direction == "short" else []):
            res["decomp"].setdefault(str(yy), {})[tag] = decompose(S, fund, T_ms, btc_ts_ret, yy)
            print("###   decomp %d: gross=%.4f%% net=%.4f%% fund=%.4f%%"
                  % (yy, res["decomp"][str(yy)][tag]["gross_nocut_pct"],
                     res["decomp"][str(yy)][tag]["net_nocut_pct"],
                     res["decomp"][str(yy)][tag]["fund_pp_pct"]), flush=True)
        del g, S
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f phut)" % (a.out, (time.time() - t0) / 60), flush=True)


if __name__ == "__main__":
    main()
