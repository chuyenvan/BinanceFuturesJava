#!/usr/bin/env python3
"""short_betaneutral_score.py — CHẤM 0-sim cho PREREG_SHORT_BETANEUTRAL (pre-reg 6610b587).

Danh mục beta-neutral mỗi tick t: SHORT top-K8 (score bins OLD_ndown_S42, SAU lọc N1b r1>=0, cắt +30 %)
+ LONG EW toàn universe nhãn cùng tick, cùng notional, giữ 72h.
  spread(t) = mean_K8(pnl_s + f_s) + R_EW(t) - F_EW(t) - 2*0,112 %
Funding: rate > 0 => long TRẢ / SHORT NHẬN; f = Σ rate trong (t, t+72h] (exact, Aerospike cache).
Sanity: tái lập V3 base_k8_T72_C30 net_pre +0,409 % / fund_mean -0,580 % (±0,03 pp) — lệch => VOID.

KHÔNG train, KHÔNG sim, KHÔNG chạm .java. Cửa sổ chính t+72h <= 2026-01-01 (không dùng dữ liệu 2026).
"""
import argparse
import gc
import glob
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import short_model_score as SMS  # read_bins, ci_mean (block-72h, NREP 2000, seed 20260905, x1.21)

H = 3600000
T0 = 1640995200000          # 2022-01-01 UTC
DEV_CUT = 1767225600000     # 2026-01-01 UTC
MAIN_END = DEV_CUT - 72 * H  # t + 72h <= DEV_CUT
COST = 0.00112
COST_STRESS = 0.00150
K = 8
CUT = 0.30
NEED = 288
RES = 1024
FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]
SANITY = {"net_pre": 0.00409, "fund_mean": -0.00580, "tol": 0.0003}
YEARS = (2022, 2023, 2024, 2025)
log = logging.getLogger("betaneutral")


# ───────────────────────── funding (lean, float32) ─────────────────────────

class Fund:
    def __init__(self, npz):
        z = np.load(npz, allow_pickle=True)
        self.syms = [str(s) for s in z["syms"]]
        ts = z["ts"].astype(np.int64); rt = z["rt"].astype(np.float64); sid = z["sid"].astype(np.int32)
        o = np.argsort(sid, kind="stable")
        self.ts, self.rt, self.sid = ts[o], rt[o], sid[o]
        self.bounds = np.searchsorted(self.sid, np.arange(len(self.syms) + 1))
        self.cum = np.zeros(len(self.ts) + 1)
        np.cumsum(self.rt, out=self.cum[1:])
        self.s2i = {s: i for i, s in enumerate(self.syms)}

    def compute(self, fsid, t, tend):
        """f = Σ rate trong (t, tend]; r1 = rate settle kế tiếp sau t. Không có dữ liệu => NaN."""
        n = len(t)
        f = np.full(n, np.nan, np.float32)
        r1 = np.full(n, np.nan, np.float32)
        o = np.argsort(fsid, kind="stable")
        fs = fsid[o]
        b = np.searchsorted(fs, np.arange(len(self.syms) + 1))
        for s in range(len(self.syms)):
            i0, i1 = b[s], b[s + 1]
            if i1 == i0:
                continue
            a, bb = self.bounds[s], self.bounds[s + 1]
            if bb <= a:
                continue
            idx = o[i0:i1]
            tt = t[idx]; te = tend[idx]
            ta, ca, ra = self.ts[a:bb], self.cum[a:bb + 1], self.rt[a:bb]
            lo = np.searchsorted(ta, tt, side="right")
            hi = np.searchsorted(ta, te, side="right")
            f[idx] = (ca[hi] - ca[lo]).astype(np.float32)
            ok = lo < len(ta)
            v = r1[idx]; v[ok] = ra[lo[ok]].astype(np.float32); r1[idx] = v
        del o, fs
        return f, r1


# ───────────────────────── nhãn (panel lean) ─────────────────────────

def load_labels(lb_dir, map_csv):
    sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    i2s = dict(zip(smap.symId.astype(np.int32), smap.symbol))
    fs = sorted(f for f in glob.glob(lb_dir + "/funding_label_*.pb") if ".part" not in f)
    cols = ["tEpochMs", "symbol", "retEnd_72h", "maxFav_72h", "nBars_72h", "tHitFav_72h"]
    acc = {k: [] for k in ("ts", "sym", "ret", "mfav", "thit")}
    for fp in fs:
        d = FLPB.read_label(fp, usecols=cols)
        d = d[(d["nBars_72h"] >= NEED) & d["retEnd_72h"].notna()
              & (d.tEpochMs >= T0) & (d.tEpochMs < DEV_CUT)]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        if k.any():
            acc["ts"].append(d.tEpochMs.to_numpy(np.int64)[k])
            acc["sym"].append(sid[k].to_numpy(np.int32))
            acc["ret"].append(d["retEnd_72h"].to_numpy(np.float32)[k])
            acc["mfav"].append(d["maxFav_72h"].to_numpy(np.float32)[k])
            acc["thit"].append(d["tHitFav_72h"].to_numpy(np.int32)[k])
        del d
    out = {k: np.concatenate(v) for k, v in acc.items()}
    key = out["ts"] * RES + out["sym"].astype(np.int64)
    o = np.argsort(key, kind="stable")
    for k in list(out):
        out[k] = out[k][o]
    out["key"] = key[o]
    out["i2s"] = i2s
    return out


# ───────────────────────── tiện ích ─────────────────────────

def rank_in_tick(ts, v):
    """Hạng tăng dần 1..n của v trong từng tick (như V3: lexsort((v, ts)), ổn định) + kích thước tick."""
    o2 = np.lexsort((v, ts))
    ts_s = ts[o2]
    r = np.empty(len(ts)); nn = np.empty(len(ts), np.int64)
    if not len(ts):
        return r, nn
    new = np.empty(len(ts_s), dtype=bool); new[0] = True
    np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
    gid = np.cumsum(new) - 1
    firsts = np.flatnonzero(new)
    sizes = np.diff(np.append(firsts, len(ts_s)))
    r[o2] = (np.arange(len(ts_s)) - firsts[gid] + 1).astype(np.float64)
    nn[o2] = sizes[gid]
    return r, nn


def per_tick(v, ts):
    """Trung bình theo tick (bỏ NaN): trả (giá trị, tick)."""
    v = np.asarray(v, np.float64)
    u, inv = np.unique(ts, return_inverse=True)
    m = np.isfinite(v)
    s = np.bincount(inv, weights=np.where(m, v, 0.0), minlength=len(u))
    c = np.bincount(inv, weights=m.astype(np.float64), minlength=len(u))
    with np.errstate(invalid="ignore", divide="ignore"):
        return s / c, u


def year_of(ts):
    return pd.to_datetime(pd.Series(ts), unit="ms", utc=True).dt.year.to_numpy()


def by_year(v, ts):
    yr = year_of(ts); v = np.asarray(v, np.float64)
    return {str(y): (round(float(np.nanmean(v[yr == y])), 6) if (yr == y).any() else None) for y in YEARS}


def ci(v, ts):
    c = SMS.ci_mean(v, ts)
    return {"mean": round(c["mean"], 6), "raw": [round(c["raw"][0], 6), round(c["raw"][1], 6)],
            "infl": [round(c["infl"][0], 6), round(c["infl"][1], 6)], "n_tick": int(c["n"]),
            "out_raw": bool(c["out_raw"]), "out_legacy": bool(c["out_legacy"])}


def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    vx = np.var(x)
    return round(float(np.mean((x - x.mean()) * (y - y.mean())) / vx), 4) if vx > 0 else None


def spearman_ticks(ts, p, ret):
    """rank-IC per tick = Spearman(score, -ret) (không ties) — trả (ic per tick, tick)."""
    rp, n = rank_in_tick(ts, p)
    rr, _ = rank_in_tick(ts, -ret.astype(np.float64))
    d2 = (rp - rr) ** 2
    u, inv = np.unique(ts, return_inverse=True)
    sd2 = np.bincount(inv, weights=d2, minlength=len(u))
    nt = np.bincount(inv, minlength=len(u)).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        ic = 1.0 - 6.0 * sd2 / (nt * (nt * nt - 1.0))
    ic[nt < 3] = np.nan
    return ic, u


def topk_mask(ts, p, k):
    r, n = rank_in_tick(ts, p)
    return r > (n - k)


def cut_pnl(ret, mfav):
    return np.where(mfav >= CUT, -CUT, -ret.astype(np.float64))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-dir", default=os.path.expanduser("~/sm_pathexit/sm/OLD_ndown_S42"))
    ap.add_argument("--labels-dir", default="/home/ubuntu/ds_label15m")
    ap.add_argument("--map-csv", default="/home/ubuntu/claudedata/oi/symbol_map.csv")
    ap.add_argument("--fund-cache", default="/tmp/fund_cache.npz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    res = {"prereg": "docs/prereg/PREREG_SHORT_BETANEUTRAL.md@6610b587", "bins": a.bins_dir,
           "cost_leg": COST, "cost_leg_stress": COST_STRESS, "K": K, "cut": CUT, "T_h": 72}

    files = [os.path.join(a.bins_dir, "predict_wf_%s.bin" % f) for f in FOLDS]
    miss = [f for f in files if not os.path.exists(f)]
    if miss:
        res["VERDICT"] = "BLOCKED"; res["reason"] = "thieu bins: %s" % miss
        json.dump(res, open(a.out, "w"), indent=1); log.error("BLOCKED %s", miss); return

    L = load_labels(a.labels_dir, a.map_csv)
    log.info("nhan %d dong (%.1f phut)", len(L["key"]), (time.time() - t0) / 60)
    fund = Fund(a.fund_cache)
    fmap = np.full(RES, -1, np.int32)
    for sid, nm in L["i2s"].items():
        if nm in fund.s2i:
            fmap[int(sid) % RES] = fund.s2i[nm]
    L["fsid"] = fmap[L["sym"].astype(np.int64)]
    L["f72"], L["r1"] = fund.compute(L["fsid"], L["ts"], L["ts"] + 72 * H)
    log.info("funding panel xong; f72 huu han %.4f (%.1f phut)", float(np.isfinite(L["f72"]).mean()),
             (time.time() - t0) / 60)

    # ── bins ∩ nhãn (như V3: join key, score hữu hạn, sort ts ổn định) ──
    bts, bsym, bp = SMS.read_bins(files)
    key = bts * RES + bsym.astype(np.int64)
    ip = np.clip(np.searchsorted(L["key"], key), 0, len(L["key"]) - 1)
    hit = (L["key"][ip] == key) & np.isfinite(bp)
    bts, bp, ip = bts[hit], bp[hit], ip[hit]
    del bsym, key, hit; gc.collect()
    o = np.argsort(bts, kind="stable")
    bts, bp, ip = bts[o], bp[o], ip[o]
    del o; gc.collect()
    res["n_join"] = int(len(bts))
    log.info("bins join %d dong, %d tick (%.1f phut)", len(bts), len(np.unique(bts)), (time.time() - t0) / 60)

    # ── SANITY: V3 base_k8_T72_C30 (không lọc, cửa sổ V3 t < DEV_CUT) ──
    sel = topk_mask(bts, bp, K)
    si = ip[sel]; sts = bts[sel]
    pnl = cut_pnl(L["ret"][si], L["mfav"][si]); f = L["f72"][si].astype(np.float64)
    m = np.isfinite(pnl) & np.isfinite(f)
    pt, _ = per_tick(pnl[m], sts[m])
    s_net_pre = float(np.mean(pt - COST)); s_fund = float(np.mean(f[m]))
    ok1 = abs(s_net_pre - SANITY["net_pre"]) <= SANITY["tol"]
    ok2 = abs(s_fund - SANITY["fund_mean"]) <= SANITY["tol"]
    res["sanity"] = {"n_kept": int(m.sum()), "net_pre": round(s_net_pre, 6), "fund_mean": round(s_fund, 6),
                     "target": SANITY, "ref_v3_short42_arm": {"n_kept": 1114016, "net_pre": 0.003857,
                                                              "fund_mean": -0.00581},
                     "PASS": bool(ok1 and ok2)}
    log.info("SANITY n=%d net_pre=%+.5f (muc tieu %+.5f) fund_mean=%+.5f (muc tieu %+.5f) => %s",
             m.sum(), s_net_pre, SANITY["net_pre"], s_fund, SANITY["fund_mean"],
             "PASS" if (ok1 and ok2) else "VOID")
    del sel, si, sts, pnl, f, m, pt; gc.collect()
    if not (ok1 and ok2):
        res["VERDICT"] = "VOID"; res["reason"] = "sanity lech > 0,03 pp so V3"
        json.dump(res, open(a.out, "w"), indent=1); return

    # ── cửa sổ chính: t + 72h <= 2026-01-01 ──
    w = bts <= MAIN_END
    bts, bp, ip = bts[w], bp[w], ip[w]
    del w; gc.collect()

    # IC theo năm: toàn bộ bins ∩ nhãn (không lọc N1b)
    ic, ic_u = spearman_ticks(bts, bp, L["ret"][ip])
    ic_yr = by_year(ic, ic_u)
    res["ic"] = {"all": round(float(np.nanmean(ic)), 5), "by_year": ic_yr, "n_tick": int(np.isfinite(ic).sum())}
    log.info("IC all=%+.4f by_year=%s", res["ic"]["all"], ic_yr)
    del ic, ic_u; gc.collect()

    # Chân SHORT: lọc N1b (r1>=0, f hữu hạn) RỒI top-K8 theo score
    r1 = L["r1"][ip]; fb = L["f72"][ip]
    el = np.isfinite(r1) & (r1 >= 0) & np.isfinite(fb)
    res["n1b_elig_frac"] = round(float(el.mean()), 4)
    ets, ep, eip = bts[el], bp[el], ip[el]
    del r1, fb, el, bts, bp, ip; gc.collect()
    sel = topk_mask(ets, ep, K)
    kts, kip = ets[sel], eip[sel]
    del ets, ep, eip, sel; gc.collect()
    kret = L["ret"][kip].astype(np.float64); kmf = L["mfav"][kip]
    kf = L["f72"][kip].astype(np.float64)
    kpnl = cut_pnl(kret, kmf)
    s_pf, u = per_tick(kpnl + kf, kts)
    s_ret, _ = per_tick(kret, kts)
    s_f, _ = per_tick(kf, kts)
    res["n_picks"] = int(len(kts)); res["n_tick"] = int(len(u))
    res["picks_per_tick"] = round(len(kts) / max(len(u), 1), 3)
    res["cut_rate"] = round(float((kmf >= CUT).mean()), 4)
    res["fund_mean_short_row"] = round(float(kf.mean()), 6)
    log.info("picks=%d tick=%d picks/tick=%.2f cut_rate=%.4f fund_short=%+.5f", len(kts), len(u),
             res["picks_per_tick"], res["cut_rate"], res["fund_mean_short_row"])

    # Chân LONG EW: toàn universe nhãn cùng tick (không lọc), funding = mean f72 hữu hạn
    lw = L["ts"] <= MAIN_END
    lts = L["ts"][lw]
    ul, inv = np.unique(lts, return_inverse=True)
    cnt = np.bincount(inv, minlength=len(ul)).astype(np.float64)
    REW = np.bincount(inv, weights=L["ret"][lw].astype(np.float64), minlength=len(ul)) / cnt
    lf = L["f72"][lw].astype(np.float64); fm = np.isfinite(lf)
    FEW = (np.bincount(inv, weights=np.where(fm, lf, 0.0), minlength=len(ul))
           / np.bincount(inv, weights=fm.astype(np.float64), minlength=len(ul)))
    del lts, inv, lf, fm, lw; gc.collect()
    j = np.searchsorted(ul, u)
    assert np.all(ul[j] == u), "tick pick khong co trong universe nhan"
    R, F, NEW = REW[j], FEW[j], cnt[j]
    res["ew_universe_mean_n"] = round(float(NEW.mean()), 2)
    res["ew_ret_mean"] = round(float(R.mean()), 6); res["ew_fund_mean"] = round(float(np.nanmean(F)), 6)

    # Spread beta-neutral
    spread = s_pf + R - F - 2 * COST
    spread_stress = s_pf + R - F - 2 * COST_STRESS
    res["spread"] = ci(spread, u)
    res["spread_by_year"] = by_year(spread, u)
    res["spread_stress"] = ci(spread_stress, u)
    res["spread_stress_by_year"] = by_year(spread_stress, u)
    res["spread_gross_pre_fund"] = round(float(np.mean(per_tick(kpnl, kts)[0] + R)), 6)
    res["fund_net_2legs"] = round(float(np.nanmean(s_f - F)), 6)
    res["beta_short_leg"] = slope(R, s_ret)
    res["beta_spread"] = slope(R, spread)
    res["corr_short_leg_ew"] = round(float(np.corrcoef(R, s_ret)[0, 1]), 4)
    log.info("SPREAD mean=%+.5f raw=%s infl=%s by_year=%s", res["spread"]["mean"], res["spread"]["raw"],
             res["spread"]["infl"], res["spread_by_year"])
    log.info("stress mean=%+.5f beta_short=%s beta_spread=%s", res["spread_stress"]["mean"],
             res["beta_short_leg"], res["beta_spread"])

    # Directional đối chiếu (cùng tập K8 sau N1b, không hedge)
    dirn = s_pf - COST
    res["directional"] = ci(dirn, u)
    res["directional_by_year"] = by_year(dirn, u)
    res["ew_leg_net_fund"] = ci(R - F, u)

    # F3-bound (phụ): lệnh bị cắt chỉ tính funding tới tHitFav_72h
    cutm = kmf >= CUT
    f3 = kf.copy()
    if cutm.any():
        ci_ = np.flatnonzero(cutm)
        tt = kts[ci_]
        te = tt + L["thit"][kip[ci_]].astype(np.int64) * 60000
        fc, _ = fund.compute(L["fsid"][kip[ci_]], tt, te)
        f3[ci_] = fc.astype(np.float64)
    s_pf3, _ = per_tick(kpnl + f3, kts)
    sp3 = s_pf3 + R - F - 2 * COST
    res["f3_bound"] = {"spread": ci(sp3, u), "by_year": by_year(sp3, u),
                       "fund_short_row_cut_only_full": round(float(kf[cutm].mean()), 6) if cutm.any() else None,
                       "fund_short_row_cut_only_tohit": round(float(f3[cutm].mean()), 6) if cutm.any() else None}

    # Luật GO (5 điều kiện, cơ học)
    sp = res["spread"]
    yrs = sum(1 for v in res["spread_by_year"].values() if v is not None and v > 0)
    icp = sum(1 for v in res["ic"]["by_year"].values() if v is not None and v > 0)
    cond = {"1_sanity": bool(res["sanity"]["PASS"]),
            "2_spread_ci": bool(sp["mean"] > 0 and sp["raw"][0] > 0 and sp["infl"][0] > 0),
            "3_years_pos_ge3": bool(yrs >= 3), "4_ic_pos_4y": bool(icp == 4),
            "5_stress_pos": bool(res["spread_stress"]["mean"] > 0)}
    res["years_pos"] = yrs; res["ic_years_pos"] = icp
    res["conditions"] = cond
    res["VERDICT"] = "GO-nghien-cuu" if all(cond.values()) else "NO-GO"
    log.info("DIRECTIONAL mean=%+.5f raw=%s by_year=%s", res["directional"]["mean"], res["directional"]["raw"],
             res["directional_by_year"])
    log.info("F3 spread=%+.5f; dieu kien=%s => %s (%.1f phut)", res["f3_bound"]["spread"]["mean"], cond,
             res["VERDICT"], (time.time() - t0) / 60)
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
