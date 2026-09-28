#!/usr/bin/env python3
"""entry_rulers.py — PREREG_ENTRY_RULERS (commit c24c908).

BỘ THƯỚC **TẦNG ENTRY (vi mô)** — đo CHẤT LƯỢNG XẾP HẠNG cross-section trong pool P32 tại mỗi
quyết định vào lệnh, thay cho tầng TIỀN/CAGR (thiếu power: N_eff ~76 tuần, edge dồn ~9 đợt).
Mẫu DÀY: 9657 tick (15') x 32 coin = 309.024 leg.

Read-only: KHÔNG train, KHÔNG sim, KHÔNG chạm 242/ONNX/LIVE. DEV only (<= 2025-12-31).
CI: block-72h, 2000 rep, seed 20260905, PAIRED. inflate(k_ruler=6)/inflate(k_obj=10).

Thước chính (pre-reg §4):
  rank_ic · top_decile_lift · winrate (cua so CO DINH) · pnl_vol_norm
Thước phụ: edge5 · med_lift
Bo co ly do: turnover-adjusted (hang so o tang pool).

Usage: python3 entry_rulers.py [--pool p32] [--out docs/result/entry_rulers.json]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c3_rates as C                                       # noqa: E402

POOL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
SCORES = "/tmp/trr/scores_pool_p32.npz"                    # xuat boi tail_robust_rulers.py (4660529)
MONEY = "docs/result/tail_robust_rulers.json"
TMP = "/tmp/er"
F = 0.006
BLOCK_H = 72
NREP = 2000
SEED = 20260905
K_RULER = 6
K_OBJ = 10
DEC_FRAC = 0.10
RULERS_MAIN = ["rank_ic", "top_decile_lift", "winrate", "pnl_vol_norm"]
RULERS_SUB = ["edge5", "med_lift"]
RULERS = RULERS_MAIN + RULERS_SUB
ALL_OBJS = ["45deploy", "A44", "A45", "V1", "V5", "MRA4", "S1",
            "ofi_candidate", "ofi_baseline_fresh", "ofi_noise"]
ORIENT = {o: -1 for o in ("S1", "ofi_candidate", "ofi_baseline_fresh", "ofi_noise")}
H = 3600000


def log(*a):
    print(*a, flush=True)


def load_pool():
    d = pd.read_parquet(POOL, columns=["ts", "symId", "gross", "exit_ts", "rank"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    ts = d.ts.to_numpy(np.int64)
    ticks = np.unique(ts)
    tick = np.searchsorted(ticks, ts)
    return dict(ts=ts, sym=d.symId.to_numpy(np.int64), gross=d.gross.to_numpy(np.float64),
                exit_ts=d.exit_ts.to_numpy(np.int64), tick=tick, ticks=ticks)


def load_scores(P, objs):
    z = np.load(SCORES)
    out = {}
    for o in objs:
        s = np.asarray(z[o], np.float64) * ORIENT.get(o, 1)
        out[o] = s
    return out


def common_ticks(P, SC, objs):
    nt = len(P["ticks"])
    m = np.ones(nt, bool)
    for o in objs:
        m &= np.isfinite(SC[o].reshape(nt, -1)).all(1)
    log("  ### tick dung chung: %d / %d (bo %d)" % (m.sum(), nt, nt - m.sum()))
    return P["ticks"][m]


def subset(P, ticks):
    m = np.isin(P["ts"], ticks)
    ts = P["ts"][m]
    t2 = np.unique(ts)
    return dict(ts=ts, sym=P["sym"][m], gross=P["gross"][m], exit_ts=P["exit_ts"][m],
                tick=np.searchsorted(t2, ts), ticks=t2)


def row_rank(M):
    """Rank trung binh theo hang (tick) — cho Spearman (xu ly dong hang)."""
    return pd.DataFrame(M).rank(axis=1, method="average").to_numpy(np.float64)


def rank_ic_series(SM, GM):
    rs = row_rank(SM)
    ry = row_rank(GM)
    a = rs - rs.mean(1, keepdims=True)
    b = ry - ry.mean(1, keepdims=True)
    num = (a * b).sum(1)
    den = np.sqrt((a * a).sum(1) * (b * b).sum(1))
    return np.where(den > 0, num / den, np.nan)


def lift_series(SM, GM, k):
    order = np.argsort(-SM, axis=1, kind="stable")
    top = np.take_along_axis(GM, order[:, :k], axis=1)
    return top.mean(1) - GM.mean(1)


def medlift_series(SM, GM, k):
    order = np.argsort(-SM, axis=1, kind="stable")
    top = np.take_along_axis(GM, order[:, :k], axis=1)
    return np.median(top, axis=1) - np.median(GM, axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/result/entry_rulers.json")
    a = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)
    t0 = time.time()
    P = load_pool()
    nt = len(P["ticks"])
    log("### pool rows=%d tick=%d sym=%d" % (len(P["gross"]), nt, len(np.unique(P["sym"]))))
    SC = load_scores(P, ALL_OBJS)
    tk = common_ticks(P, SC, ALL_OBJS)
    if len(tk) < nt:
        m = np.isin(P["ts"], tk)
        SC = {o: SC[o][m] for o in ALL_OBJS}
        P = subset(P, tk)
    nt = len(P["ticks"])
    log("  ### after filter rows=%d tick=%d" % (len(P["gross"]), nt))
    GM = P["gross"].reshape(nt, 32)
    net = P["gross"] - F
    kdec = int(np.ceil(DEC_FRAC * 32))                     # =4
    kedge = 5
    # sigma_sym: proxy vol moi coin (std gross tren toan mau)
    df = pd.DataFrame({"s": P["sym"], "g": P["gross"]})
    sd = df.groupby("s")["g"].std().to_dict()
    sig = np.array([sd.get(s, np.nan) for s in P["sym"]], np.float64)
    sig = np.where(np.isfinite(sig) & (sig > 1e-9), sig, np.nan)
    log("  ### sigma_sym: finite=%.1f%% median=%.4f" % (100 * np.isfinite(sig).mean(), np.nanmedian(sig)))
    BI = None
    inv = P["ticks"] // (BLOCK_H * H)
    _, inv = np.unique(inv, return_inverse=True)
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(SEED).integers(0, nb, (NREP, nb))
    log("  ### blocks(72h)=%d reps=%d seed=%d" % (nb, NREP, SEED))

    # per-tick arrays -> per-block sums
    # rank_ic/top_decile_lift/edge5/med_lift: tren TOAN pool (32 coin) — do chat luong XEP HANG
    # winrate/pnl_vol_norm: tren tap CHON CO DINH top-K (K=8, van hanh) — khong phu thuoc duoi
    K = 8
    pl = {}
    for o in ALL_OBJS:
        SM = SC[o].reshape(nt, 32)
        order = np.argsort(-SM, axis=1, kind="stable")[:, :K]
        sel_net = np.take_along_axis(net.reshape(nt, 32), order, axis=1)
        sel_sig = np.take_along_axis(sig.reshape(nt, 32), order, axis=1)
        pos_t = (sel_net > 0).sum(1).astype(np.float64)
        pvn_t = np.nansum(np.where(np.isfinite(sel_sig), sel_net / sel_sig, 0.0), axis=1)
        pl[o] = {"rank_ic": rank_ic_series(SM, GM),
                 "top_decile_lift": lift_series(SM, GM, kdec),
                 "edge5": lift_series(SM, GM, kedge),
                 "med_lift": medlift_series(SM, GM, kdec),
                 "pos": pos_t,
                 "pvn": pvn_t}
        del SM, order, sel_net, sel_sig
        log("  ### series %s %.0fs" % (o, time.time() - t0))

    def blk(arr):
        return np.bincount(inv, weights=np.nan_to_num(arr), minlength=nb)

    def blkcnt(arr):
        return np.bincount(inv, weights=np.isfinite(arr).astype(np.float64), minlength=nb)

    # block arrays cho moi doi tuong x 6 thước
    BLK = {}
    for o in ALL_OBJS:
        d = {}
        for r in ("rank_ic", "top_decile_lift", "edge5", "med_lift"):
            d[r] = (blk(pl[o][r]), blkcnt(pl[o][r]))
        d["winrate"] = (np.bincount(inv, weights=pl[o]["pos"], minlength=nb),
                         K * np.bincount(inv, minlength=nb).astype(np.float64))
        d["pnl_vol_norm"] = (np.bincount(inv, weights=pl[o]["pvn"], minlength=nb),
                             K * np.bincount(inv, minlength=nb).astype(np.float64))
        BLK[o] = d

    def pt(o, r):
        num, cnt = BLK[o][r]
        return float(num.sum() / cnt.sum())

    def reps(o, r):
        num, cnt = BLK[o][r]
        return num[BI].sum(1) / cnt[BI].sum(1)

    def ci_sum(v, point):
        lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
        infl = C.inflate(K_RULER)
        ilo, ihi = point - (point - lo) * infl, point + (hi - point) * infl
        orw, oi = bool(lo > 0 or hi < 0), bool(ilo > 0 or ihi < 0)
        wid = hi - lo
        wr = wid / abs(point) if abs(point) > 1e-12 else float("inf")
        return {"point": round(point, 8), "raw": [round(float(lo), 8), round(float(hi), 8)],
                "infl": [round(float(ilo), 8), round(float(ihi), 8)],
                "out_raw": orw, "out_infl": oi, "out": bool(orw and oi),
                "width": round(float(wid), 8), "width_rel": round(float(wr), 4),
                "dir": int(np.sign(point))}

    infl_r = C.inflate(K_RULER)
    infl_o = C.inflate(K_OBJ)
    res = {"prereg": "PREREG_ENTRY_RULERS.md", "f": F, "K_ruler": K_RULER, "K_obj": K_OBJ,
           "inflate_k6": infl_r, "inflate_k10": infl_o, "block_h": BLOCK_H, "nrep": NREP,
           "seed": SEED, "n_tick": nt, "n_leg": len(P["gross"]), "objs": ALL_OBJS,
           "k_decile": kdec, "k_edge5": kedge, "level": {}, "delta": {}, "rule": {},
           "rank": {}, "redundancy": {}, "money": {}}
    REP = {}
    for o in ALL_OBJS:
        res["level"][o] = {}
        for r in RULERS:
            REP[(o, r)] = reps(o, r)
            res["level"][o][r] = ci_sum(REP[(o, r)], pt(o, r))
    # delta vs 2 doi chung
    for o in ALL_OBJS:
        if o in ("45deploy", "V1"):
            continue
        for r in RULERS:
            for ctl in ("45deploy", "V1"):
                key = "%s-%s" % (o, ctl)
                d = REP[(o, r)] - REP[(ctl, r)]
                ptd = pt(o, r) - pt(ctl, r)
                res["delta"].setdefault(key, {})[r] = ci_sum(d, ptd)
    # hieu chuan thước: cap retrain/nhieu
    for pair in (("A45", "45deploy"), ("V5", "V1")):
        key = "%s-%s" % pair
        for r in RULERS:
            d = REP[(pair[0], r)] - REP[(pair[1], r)]
            ptd = pt(pair[0], r) - pt(pair[1], r)
            res["delta"].setdefault(key, {})[r] = ci_sum(d, ptd)
    # D1: thang ca 2 doi chung, >=2 thuoc CHINH, cung dau, out
    D1 = {}
    for o in ALL_OBJS:
        if o in ("45deploy", "V1"):
            continue
        ok = []
        for r in RULERS_MAIN:
            da = res["delta"]["%s-45deploy" % o][r]
            db = res["delta"]["%s-V1" % o][r]
            if da["out"] and db["out"] and da["dir"] == db["dir"] and da["dir"] == 1:
                ok.append(r)
        D1[o] = {"thuoc_thang": ok, "n": len(ok), "WIN": len(ok) >= 2}
    res["D1"] = D1
    # D2: thước phan giai duoc (khong keo cap hieu chuan ra ngoai CI)
    D2 = {}
    for r in RULERS:
        hits = [k for k in ("A45-45deploy", "V5-V1") if res["delta"][k][r]["out"]]
        D2[r] = {"doi_chung_ngoai_CI": hits, "phan_giai_duoc": len(hits) == 0,
                 "width_rel_main": None}
    res["D2"] = D2
    # bang xep hang theo tung thước + so voi tang TIEN
    pts = {o: {r: pt(o, r) for r in RULERS} for o in ALL_OBJS}
    for r in RULERS:
        order = sorted(ALL_OBJS, key=lambda o: -pts[o][r])
        res["rank"][r] = order
    # tang TIEN (doc lai tu tail_robust_rulers.json)
    if os.path.exists(MONEY):
        j = json.load(open(MONEY))
        mny = j["runs"]["p32"]["money"]
        mn = {}
        for o in ALL_OBJS:
            if o in mny:
                f6 = mny[o]["fees"]["0.006"]
                mn[o] = {"net_tick": f6["net_tick"]["point"], "sized_A_mean": f6["sized_A_mean"]["point"]}
        res["money"] = mn
        for key in ("net_tick", "sized_A_mean"):
            if len(mn) == len(ALL_OBJS):
                res["rank"]["money_" + key] = sorted(ALL_OBJS, key=lambda o: -mn[o][key])

    def spearman(a, b, keys):
        ra = pd.Series(a).rank(); rb = pd.Series(b).rank()
        return float(np.corrcoef(ra, rb)[0, 1])

    # so thứ hạng entry vs tien
    if res["money"]:
        cmp_ = {}
        order_m = res["rank"].get("money_net_tick")
        for r in RULERS:
            o_r = res["rank"][r]
            rho = spearman([o_r.index(o) for o in ALL_OBJS], [order_m.index(o) for o in ALL_OBJS],
                           ALL_OBJS)
            moved = [(o, order_m.index(o) - o_r.index(o)) for o in ALL_OBJS
                     if order_m.index(o) != o_r.index(o)]
            cmp_[r] = {"spearman_vs_money_net_tick": round(rho, 4),
                       "top1": o_r[0], "money_top1": order_m[0],
                       "moved": sorted(moved, key=lambda x: -abs(x[1]))[:4]}
        res["rank_compare"] = cmp_
    # trung lap giua cac thước (tren 10 doi tuong)
    M = pd.DataFrame({r: [pts[o][r] for o in ALL_OBJS] for r in RULERS}, index=ALL_OBJS)
    res["redundancy"] = {"pearson": json.loads(M.corr(method="pearson").round(3).to_json()),
                         "spearman": json.loads(M.corr(method="spearman").round(3).to_json())}
    with open(a.out, "w") as fh:
        json.dump(res, fh, separators=(",", ":"), default=str)
    log("### JSON -> %s (%.1f KB) | %.0fs" % (a.out, os.path.getsize(a.out) / 1e3, time.time() - t0))
    # tom tat nhanh ra stdout
    log("\n=== POINT (10 doi tuong x 6 thuoc) ===")
    log("%-20s %s" % ("obj", " ".join("%11s" % r for r in RULERS)))
    for o in ALL_OBJS:
        log("%-20s %s" % (o, " ".join("%+11.5f" % pts[o][r] for r in RULERS)))
    log("\n=== D1 WIN ===")
    for o, v in D1.items():
        log("  %-20s n=%d WIN=%s %s" % (o, v["n"], v["WIN"], v["thuoc_thang"]))
    log("=== D2 (thuoc) ===")
    for r in RULERS:
        log("  %-16s phan_giai=%s hits=%s" % (r, D2[r]["phan_giai_duoc"], D2[r]["doi_chung_ngoai_CI"]))
    log("=== RANK vs MONEY ===")
    for r, v in res.get("rank_compare", {}).items():
        log("  %-16s rho=%+.3f top1=%s money_top1=%s" % (r, v["spearman_vs_money_net_tick"],
                                                           v["top1"], v["money_top1"]))


if __name__ == "__main__":
    main()
