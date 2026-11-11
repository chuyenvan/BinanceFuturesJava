#!/usr/bin/env python3
"""R3b (prereg PREREG_R3B_SMOOTH_ISO 3ea5df40) §3: hieu chinh pct CHUNG 8 seed tren NAM 2022 (chi dem, gate_offline) cho MEAN15/MEAN60,
roi sang quota 2023-25 (median 8 seed arm/A0 ngoai [0,75;1,25] => LOAI). Cam mo pnl/MTM. Output r3b_iso.json."""
import json, logging, math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r3b")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
H, M1, J = 3600000, 60000, 512
Y22 = (1640970000000, 1672506000000)           # 2022-01-01..2023-01-01 (+07)
Y2325 = (1672506000000, 1767200400000)         # 2023-01-01..2026-01-01 (+07)
ARMS = {"B1_MEAN15": (15, 12), "B2_MEAN60": (60, 48)}
LO, HI, TOL, MAXIT = 0.99990, 0.999999, 0.05, 40


def smooth(C, pts, p15, W, mincov):
    cs = np.concatenate([[0.0], np.cumsum(p15.astype(np.float64))]); t = C["ts"]
    lo = np.searchsorted(pts, t - (W - 1) * M1, "left"); hi = np.searchsorted(pts, t, "right"); n = hi - lo
    return np.where(n >= mincov, ((cs[hi] - cs[lo]) / np.maximum(n, 1)).astype(np.float32), np.float32(np.nan))


class Seed:
    """giu cay top-J (khong phu thuoc pct) + o can dem (2022, 2023-25) de dem nhanh khi doi pct."""
    def __init__(self, C, p):
        ts, SP, valid = C["ts"], C["SP"], C["valid"] & np.isfinite(p)[:, None]
        fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
        r = p[:, None] / (fac * GO.GS)
        rows, cols = np.nonzero(valid)
        vals, hv = r[rows, cols], (ts // H)[rows]
        self.first = int(ts[rows[0]])
        self.ctx = GO.mk_tree(vals, hv, J)
        del vals, hv            # hourly_q dung qh trong ctx, khong can hours (tiet kiem RAM)
        # chi giu o CO THE pass o moi pct >= LO: q(pct) >= q(LO) (k tang theo pct) => can r >= 0,99*min q_LO (bien float)
        qlo, _, _ = GO.hourly_q(None, None, self.first, 90, float(np.float32(LO)), J, ctx=self.ctx)
        rmin = np.float32(0.99 * np.nanmin(qlo))
        self.win = {}
        for nm, (a, b) in (("y22", Y22), ("y2325", Y2325)):
            m = (ts >= a) & (ts < b)
            rr, cc = np.nonzero(valid & m[:, None] & (r >= rmin))
            self.win[nm] = (ts[rr] // H, p[rr], fac[rr, cc])
        self.rmin = float(rmin)

    def count(self, pct):
        q, qh, jmax = GO.hourly_q(None, None, self.first, 90, float(np.float32(pct)), J, ctx=self.ctx)
        assert jmax < J, (jmax, J)
        qq = np.where(np.isnan(q), GO.BASE, q).astype(np.float32)
        out = {}
        for nm, (hh, p, fac) in self.win.items():
            qm = qq[np.clip(np.searchsorted(qh, hh), 0, len(qh) - 1)]
            out[nm] = int((~(p < (qm * fac) * GO.GS)).sum())
        return out


B = dict(np.load(GO.CACHE + "/cand_base.npz"))
mp = pd.read_csv(GO.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
OUT = dict(prereg="3ea5df40", lo=LO, hi=HI, tol=TOL, J=J, a0={}, arms={})
base = {}
store = {a: {} for a in ARMS}
for s in SEEDS:
    C = GO.build(s, B, s2id)
    pts, p15 = GO.load_pred(GO.SEEDS[s][1])
    base[s] = Seed(C, C["p15"]).count(GO.PCT)
    for a, (W, mc) in ARMS.items():
        store[a][s] = Seed(C, smooth(C, pts, p15, W, mc))
    log.info("%s A0 %s", s, base[s])
    del C
OUT["a0"] = base
T22 = sum(v["y22"] for v in base.values())
for a in ARMS:
    lo, hi, it, res = LO, HI, 0, None
    while it < MAXIT:
        it += 1
        mid = float(np.float32((lo + hi) / 2))
        cs = {s: store[a][s].count(mid) for s in SEEDS}
        N = sum(v["y22"] for v in cs.values())
        log.info("%s it %d pct %.9f N22 %d T22 %d ratio %.4f", a, it, mid, N, T22, N / T22)
        if abs(N / T22 - 1) <= TOL:
            res = (mid, cs, N); break
        if N > T22:
            lo = mid
        else:
            hi = mid
    if res is None:
        OUT["arms"][a] = dict(converged=False, iters=it, LOAI=True); continue
    pct, cs, N = res
    q2325 = {s: cs[s]["y2325"] / base[s]["y2325"] for s in SEEDS}
    med = float(np.median(list(q2325.values())))
    OUT["arms"][a] = dict(converged=True, iters=it, pct=pct, pct_str="%.9f" % pct, N22=N, T22=T22, ratio22=round(N / T22, 4),
                          per_seed=cs, quota2325=q2325, quota2325_med=round(med, 4), LOAI=bool(not (0.75 <= med <= 1.25)))
    log.info("%s RESULT %s", a, {k: v for k, v in OUT["arms"][a].items() if k != "per_seed"})
json.dump(OUT, open(R3 + "r3b_iso.json", "w"), indent=1)
