#!/usr/bin/env python3
"""ofi_reorient_rulers.py — PREREG_OFI_MONEY_REORIENT §5 (bao MO TA, KHONG dung quyet dinh).

Mo ta 4 thuo chuan hien hanh `wl_ratio · tf_5 · loss_mean · conc_5` + bo "rao owner"
 (`share_top1_pct` (rao a, <=15%) · bot-50% sum (rao b', >0) · q* · median/leg · tf_5/tf_10 ·
  asym = mean|lo|/mean thang · sign%) + 3 chi so martingale, cho 3 doi tuong (candidate /
baseline_fresh / noise_ofi_check), diem ENSEMBLE seed 43/44/45, top-K=8, f=0,006.

Chay cho CA 2 CHIEU (`--orient +1` = chieu CU sai, `--orient -1` = chieu SUA) tren pool `--pool p32`
=> dinh luong loi chieu. Va `--pool b2 --extra <nhan reorient>` cho duong B2 dung chieu.

CI: block-72h, NREP=2000, seed 20260905, `inflate(k=5)` cho Δ ghep cap (giong §4 pre-reg).
CHI offline, KHONG sim/Java. DEV only.

  python3 ofi_reorient_rulers.py --kdirs .../kout42,.../kout43,.../kout44,.../kout45 \
      --pool p32 --orient -1 --out /tmp/r_m1.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import model_ruler as MR                                     # noqa: E402
import c3_rates as C                                         # noqa: E402
from ofi_money_score_v2 import (KMAP, ARMS, F_DEC, FEES, infl_k, mk, mk_ratio)  # noqa: E402

LABEL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
K = 8
H = 3600000
KSENS = [2, 5, 10]
KMUL = 5          # he so multiplicity cho Δ (giong pre-reg §4)

RUL4 = ["wl_ratio", "tf_5", "loss_mean", "conc_5"]


def load_pool(pool, extra=None):
    d = pd.read_parquet(LABEL, columns=["ts", "symId", "rank", "gross", "exit_ts"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    if pool == "b2":
        assert extra, "pool b2 can --extra (nhan reorient)"
        e = pd.read_parquet(extra)
        e = e[e.ts.isin(d.ts.unique())]
        d = pd.concat([d[["ts", "symId", "gross", "exit_ts"]],
                       e[["ts", "symId", "gross", "exit_ts"]]], ignore_index=True)
        d = d.drop_duplicates(["ts", "symId"]).sort_values(["ts", "symId"], kind="stable")
        d = d.reset_index(drop=True)
    ticks = np.sort(d.ts.unique().astype(np.int64))
    return d, ticks


def score_mat(kdirs, ticks, orient, arm, ens):
    acc = None
    for s in ens:
        p = pd.read_parquet(os.path.join(kdirs[s], KMAP[arm]), columns=["ts", "sym", "score"])
        p = p[p.ts.isin(ticks)]
        p = p.assign(score=orient * p.score.to_numpy(np.float64))
        M = pd.Series(p.score.to_numpy(np.float64),
                      index=pd.MultiIndex.from_arrays([p.ts.to_numpy(np.int64), p.sym.to_numpy(np.int64)]))
        acc = M if acc is None else acc.add(M, fill_value=np.nan)
    return acc / len(ens)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kdirs", required=True)
    ap.add_argument("--ensemble", default="43,44,45")
    ap.add_argument("--pool", default="p32", choices=["p32", "b2"])
    ap.add_argument("--extra", default=None)
    ap.add_argument("--orient", type=int, default=-1, choices=[-1, 1])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    orient = float(a.orient)
    ens = [int(x) for x in a.ensemble.split(",")]
    kdirs = {int(os.path.basename(x).replace("kout", "")): x for x in a.kdirs.split(",")}

    d, ticks = load_pool(a.pool, a.extra)
    nt = len(ticks)
    tsflat = d.ts.to_numpy(np.int64)
    exflat = d.exit_ts.to_numpy(np.int64)
    symflat = d.symId.to_numpy(np.int64)
    gross = d.gross.to_numpy(np.float64)
    print("### POOL %s: %d dong, %d tick, %d sym | ORIENT=%+d" % (
        a.pool, len(d), nt, len(np.unique(symflat)), a.orient), flush=True)

    inv = np.unique((ticks // (C.BLOCK_H * H)), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(C.SEED).integers(0, nb, (C.NREP, nb))

    def cnt(x):
        return np.bincount(inv, weights=x, minlength=nb)

    key = pd.MultiIndex.from_arrays([tsflat, symflat])
    # vi tri cua tung dong pool trong tick
    tidx = np.searchsorted(ticks, tsflat)

    out = {"pool": a.pool, "orient": a.orient, "K": K, "f_dec": F_DEC, "ensemble": ens,
           "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED, "inflate_k5": round(infl_k(KMUL), 6),
           "level": {}, "delta": {}}

    legs = {}
    for arm in ARMS:
        sc = score_mat(kdirs, ticks, orient, arm, ens)
        sc = sc.reindex(key)
        assert sc.notna().all(), "%s thieu diem" % arm
        S = sc.to_numpy(np.float64)
        # top-K theo tick
        o = np.lexsort((-S, tidx))
        c = np.bincount(tidx, minlength=nt)
        starts = np.repeat(np.cumsum(c) - c, c)[o]
        rank_in = np.arange(len(o)) - starts
        fi = np.sort(o[rank_in < K])
        ti = tidx[fi]
        g = gross[fi]
        net = g - F_DEC
        sym = symflat[fi]
        ets = exflat[fi]
        # e_t
        aa = np.searchsorted(ticks, tsflat[fi], "left")
        bb = np.searchsorted(ticks, np.clip(ets, ticks[0], ticks[-1]), "left")
        ca = np.bincount(aa, minlength=nt + 1)[:nt]
        cb = np.bincount(np.clip(bb, 0, nt), minlength=nt + 1)[:nt]
        e = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
        legs[arm] = dict(ti=ti, net=net, gross=g, sym=sym, e=e, inv=inv[ti], _BI=BI, _nb=nb)
        out["level"][arm] = point(net, g, e, sym, ti, nt)

    # -------- Δ ghep cap (paired) cho 4 thuo + net_coin/net_gr1dv --------
    for (A, B) in [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check")]:
        out["delta"]["%s-%s" % (A, B)] = dlt(legs[A], legs[B], ticks, nt, cnt, BI)
    for (A, B) in [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check")]:
        for k, v in out["delta"]["%s-%s" % (A, B)].items():
            if isinstance(v, dict) and "out_k5" in v:
                print("  %-32s %-12s %+0.5f %s" % ("%s-%s" % (A, B), k, v["mean"],
                                                   "*" if v["out_k5"] else ""), flush=True)

    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("JSON -> %s (%.1f KB)" % (a.out, os.path.getsize(a.out) / 1024.0), flush=True)


def point(net, g, e, sym, ti, nt):
    n = len(net)
    tot = float(net.sum())
    o = np.sort(net)[::-1]
    k1 = max(1, int(np.ceil(0.01 * n)))

    def tail(x):
        k = max(1, int(np.ceil(x / 100.0 * n)))
        return float(o[k:].sum())

    win = net[net > 0]
    los = net[net < 0]
    dfc = pd.DataFrame({"s": sym, "n": net})
    pcs = dfc.groupby("s").n.sum()
    rec = dict(
        n_leg=n, entry_leg_mean=float(e.mean()), net_coin=float(net.mean()),
        gross_mean=float(g.mean()), net_gr1dv=float(net.sum() / e.sum()),
        share_top1_pct=float(o[:k1].sum() / tot * 100) if tot else float("nan"),
        pass_a=bool(tot > 0 and o[:k1].sum() / tot * 100 <= 15.0),
        bottom_half_sum=tail(50), pass_b50=bool(tail(50) > 0),
        median_leg=float(np.median(net)), sign_pct=float(100.0 * (net > 0).mean()),
        tf_5=float(o[max(1, int(np.ceil(0.05 * n))):].mean()),
        tf_10=float(o[max(1, int(np.ceil(0.10 * n))):].mean()),
        asym=float(los.mean() / win.mean()) if len(los) and len(win) and win.mean() != 0 else float("nan"),
        wl_ratio=float((win.mean() / -los.mean()) if len(los) and len(win) else float("nan")),
        loss_mean=float(-los.mean()) if len(los) else float("nan"),
        conc_5=float(o[:max(1, int(np.ceil(0.05 * n)))].sum() / tot) if tot else float("nan"),
        m_max_leg_loss=float(net.min()), m_conc1coin_pct=float(100.0 * pcs.max() / tot) if tot else float("nan"),
        m_ncoin_dead=int((pcs < 0).sum()), n_coin=int(len(pcs)),
    )
    for q in np.arange(0.5, 95.55, 0.5):
        if tail(q) <= 0:
            rec["q_breakeven_pct"] = float(round(q, 2))
            break
    else:
        rec["q_breakeven_pct"] = None
    return rec


def _rid(net):
    """Chi so xep hang giam dan (0 = lon nhat) — co dinh theo gia tri."""
    return np.argsort(np.argsort(net, kind="stable"), kind="stable")


def _agg4(net):
    """4 thuo chuan, diem (point estimate), tu chinh legs."""
    n = len(net)
    win, los = net > 0, net < 0
    rk = _rid(net)                     # nho => lon
    k5 = max(1, int(np.ceil(0.05 * n)))
    tot = float(net.sum())
    wm = float(net[win].mean()) if win.any() else np.nan
    lm = float(-net[los].mean()) if los.any() else np.nan
    keep = rk >= k5
    return {
        "wl_ratio": (wm / lm) if (np.isfinite(lm) and lm != 0 and np.isfinite(wm)) else np.nan,
        "tf_5": float(net[keep].mean()) if keep.any() else np.nan,
        "loss_mean": lm,
        "conc_5": float(net[rk < k5].sum() / tot) if tot else np.nan,
    }


def block_vals(L):
    """Bootstrap block-72h cua 4 thuo, tra dict {thuo: vector NREP}."""
    net = L["net"]
    inv = L["inv"]
    nb = L["_nb"]
    BI = L["_BI"]
    n = len(net)
    win, los = net > 0, net < 0
    rk = _rid(net)
    k5 = max(1, int(np.ceil(0.05 * n)))
    keep = rk >= k5
    top = rk < k5
    tot = float(net.sum())

    def bl(x):
        return np.bincount(inv, weights=x, minlength=nb)

    lsum = bl(np.where(los, -net, 0.0)); ln = bl(los.astype(float))
    wsum = bl(np.where(win, net, 0.0)); wn = bl(win.astype(float))
    r = {}
    sw, ww = wsum[BI].sum(1), wn[BI].sum(1)
    sl, ll = lsum[BI].sum(1), ln[BI].sum(1)
    r["wl_ratio"] = np.where((ll > 0) & (ww > 0), (sw / np.maximum(ww, 1e-12)) / np.maximum(sl / np.maximum(ll, 1e-12), 1e-12), np.nan)
    r["loss_mean"] = np.where(ll > 0, sl / np.maximum(ll, 1e-12), np.nan)
    fsum = bl(np.where(keep, net, 0.0)); fc = bl(keep.astype(float))
    r["tf_5"] = fsum[BI].sum(1) / np.maximum(fc[BI].sum(1), 1e-12)
    nsum = bl(net)
    r["conc_5"] = np.where(nsum[BI].sum(1) != 0,
                           bl(np.where(top, net, 0.0))[BI].sum(1) / nsum[BI].sum(1), np.nan)
    return r


def dlt(LA, LB, ticks, nt, cnt, BI):
    """Δ ghép cặp theo tick, CI block-72h cho 4 thuo + net_coin/net_gr1dv."""
    o = dict()
    # net_coin (mean) + net_gr1dv
    dnet = LA["net"] - np.nan
    # paired theo tick: dùng trung bình theo tick
    mA = pd.Series(LA["net"]).groupby(LA["ti"]).mean().reindex(range(nt)).to_numpy(np.float64)
    mB = pd.Series(LB["net"]).groupby(LB["ti"]).mean().reindex(range(nt)).to_numpy(np.float64)
    o["dnet_coin"] = mk(mA - mB, ticks)
    # net_gr1dv: ratio-of-sums bootstrap
    repsA = cnt(np.bincount(LA["ti"], weights=LA["net"], minlength=nt))[BI].sum(1)
    repsB = cnt(np.bincount(LB["ti"], weights=LB["net"], minlength=nt))[BI].sum(1)
    eA = cnt(LA["e"])[BI].sum(1)
    eB = cnt(LB["e"])[BI].sum(1)
    mu = float(LA["net"].sum() / LA["e"].sum() - LB["net"].sum() / LB["e"].sum())
    o["dnet_gr1dv"] = mk_ratio(repsA / eA - repsB / eB, mu)
    # 4 thuo: bootstrap block tren leg (pooled, khong ghep theo tick — thuo la ti so phi tuyen)
    bA = block_vals(LA)
    bB = block_vals(LB)
    pA, pB = _agg4(LA["net"]), _agg4(LB["net"])
    for ru in RUL4:
        va = bA[ru]
        vb = bB[ru]
        obs = pA[ru] - pB[ru]
        arr = va - vb
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            o[ru] = {"mean": obs, "raw": [float("nan")] * 2, "out_k5": False}
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        k5lo = c - (c - lo) * infl_k(5)
        k5hi = c + (hi - c) * infl_k(5)
        o[ru] = {"mean": float(obs), "raw": [float(lo), float(hi)],
                 "k5": [float(k5lo), float(k5hi)],
                 "out_k5": bool(lo > 0 or hi < 0), "out_raw": bool(lo > 0 or hi < 0)}
    return o


if __name__ == "__main__":
    main()
