#!/usr/bin/env python3
"""R3b pha chuan bi: do CO CHE quota tang ~70 % cua MEAN15/MEAN60 (CHI DEM, khong PnL). Seed S42, S7.
D0 danh nghia: (1-pct)*so o hop le DEV.  D1 q 'cung gio' (CHAN DOAN, nhin truoc trong gio: cua so [h-90d+1h, h+1h)) —
neu lam phat bien mat => do q dong bang trong gio + tin hieu dai.  D2 tap trung: ti le pass nam trong gio co >=10 pass;
so gio co pass; pass/gio co pass.  D3 theo nam (khong dung)."""
import json, logging, math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/r3_gate")
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("qmech")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in {"S42": "a1", "S7": "s7"}.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
DEV0, DEV1, H, M1, J = 1640970000000, 1767200400000, 3600000, 60000, 256


def smooth(C, pts, p15, W, mincov):
    cs = np.concatenate([[0.0], np.cumsum(p15.astype(np.float64))]); t = C["ts"]
    lo = np.searchsorted(pts, t - (W - 1) * M1, "left"); hi = np.searchsorted(pts, t, "right"); n = hi - lo
    ps = np.where(n >= mincov, ((cs[hi] - cs[lo]) / np.maximum(n, 1)).astype(np.float32), np.float32(np.nan))
    C2 = dict(C); C2["p15"] = ps; C2["valid"] = C["valid"] & np.isfinite(ps)[:, None]
    return C2


def passes(C, lead):
    """lead=0: gate that (q_h tu [h-90d, h)); lead=1: chan doan q tu [h-90d+1h, h+1h) (gom ca gio hien tai)."""
    ts, p, SP, valid = C["ts"], C["p15"], C["SP"], C["valid"]
    fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
    r = p[:, None] / (fac * GO.GS)
    rows, cols = np.nonzero(valid)
    vals, hv = r[rows, cols], (ts // H)[rows]
    first = int(ts[rows[0]])
    tree, qh, h0 = GO.mk_tree(vals, hv, J)
    W = 90 * 24
    q = np.full(len(qh), np.nan, np.float32)
    for i, hh in enumerate(qh.tolist()):
        if hh * H - first < 7 * GO.D:
            continue
        hi = min(hh - h0 + lead, tree.size); lo = max(0, hi - W)
        m = int(tree.cum[min(hi, len(tree.cum) - 1)] - tree.cum[lo])
        if m == 0:
            continue
        k = min(m - 1, max(0, int(math.floor(float(GO.PCT) * (m - 1)))))
        q[i] = tree.kth(lo, hi, m - 1 - k)
    qq = np.where(np.isnan(q), GO.BASE, q).astype(np.float32)
    qm = qq[np.clip(np.searchsorted(qh, ts // H), 0, len(qh) - 1)]
    P = valid & ~(p[:, None] < (qm[:, None] * fac) * GO.GS)
    return P, int(valid[(ts >= DEV0) & (ts < DEV1)].sum())


def conc(C, P):
    dev = (C["ts"] >= DEV0) & (C["ts"] < DEV1)
    hrs = (C["ts"][dev] // H)
    ph = pd.Series(P[dev].sum(1)).groupby(hrs).sum()
    ph = ph[ph > 0]
    return dict(hours_with_pass=int(len(ph)), pass_per_hour_med=float(ph.median()), share_in_hours_ge10=round(float(ph[ph >= 10].sum() / ph.sum()), 4))


B = dict(np.load(GO.CACHE + "/cand_base.npz"))
mp = pd.read_csv(GO.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
OUT = {}
for arm in GO.SEEDS:
    C = GO.build(arm, B, s2id)
    pts, p15 = GO.load_pred(GO.SEEDS[arm][1])
    res = {}
    for nm, CC in (("A0", C), ("MEAN15", smooth(C, pts, p15, 15, 12)), ("MEAN60", smooth(C, pts, p15, 60, 48))):
        dev = (CC["ts"] >= DEV0) & (CC["ts"] < DEV1)
        P0, nval = passes(CC, 0)
        P1, _ = passes(CC, 1)
        res[nm] = dict(nominal=round((1 - float(GO.PCT)) * nval, 1), pass_real=int(P0[dev].sum()), pass_q_incl_hour=int(P1[dev].sum()),
                       conc=conc(CC, P0), by_year={int(y): int(P0[dev & (CC["yr"] == y)].sum()) for y in (2022, 2023, 2024, 2025)})
        log.info("%s %s %s", arm, nm, res[nm])
    OUT[arm] = res
    del C
json.dump(OUT, open(R3 + "quota_mech.json", "w"), indent=1)
