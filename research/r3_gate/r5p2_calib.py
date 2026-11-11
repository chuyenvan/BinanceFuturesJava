#!/usr/bin/env python3
"""R5P2 (prereg PREREG_R5P2_MAX15_GATE f2222d05) §2: hieu chinh pct iso-count 2022 cho M1 (MAX15 + q PHUT) va M0 (p15 + q PHUT).
CHI DEM (gate_offline, khong pnl/MTM). q phut tai t = phan tu k cua r o hop le ts in [t-90d, t); warm-up 7d => 0,008.
Output r5p2_iso.json (pct + quota nam 2022..2025 vs A0 q gio)."""
import json, logging, math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r5p2")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
H, M1, D, J, TZ = 3600000, 60000, 86400000, 512, 7 * 3600000
YB = {y: (int(pd.Timestamp("%d-01-01" % y).value // 10**6) - TZ, int(pd.Timestamp("%d-01-01" % (y + 1)).value // 10**6) - TZ) for y in (2022, 2023, 2024, 2025)}
LO, HI, TOL, MAXIT, T22 = 0.99990, 0.999999, 0.05, 40, 4345


def topk_range(tree, lo, hi, k):
    parts = []
    l, r = lo + tree.size, hi + tree.size
    while l < r:
        if l & 1:
            parts.append(tree.T[l]); l += 1
        if r & 1:
            r -= 1; parts.append(tree.T[r])
        l >>= 1; r >>= 1
    return np.concatenate(parts) if parts else np.zeros(0, np.float32)


class ArmSeed:
    def __init__(self, C, p):
        ts, SP = C["ts"], C["SP"]
        valid = C["valid"] & np.isfinite(p)[:, None]
        fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
        r = p[:, None] / (fac * GO.GS)
        rows, cols = np.nonzero(valid)
        vals = r[rows, cols].astype(np.float32); cts = ts[rows]          # rows tang theo ts
        self.first = int(cts[0])
        tree, qh, h0 = GO.mk_tree(vals, cts // H, J)
        qlo, _, _ = GO.hourly_q(None, None, self.first, 90, float(np.float32(LO)), J, ctx=(tree, qh, h0))
        self.rmin = np.float32(0.9 * np.nanmin(qlo))
        cand = vals >= self.rmin
        dev = (cts >= YB[2022][0]) & (cts < YB[2025][1])
        sel = cand & dev
        cr, cc = rows[sel], cols[sel]
        self.cell_t, self.cell_p, self.cell_fac = ts[cr], p[cr], fac[cr, cc]
        mins = np.unique(self.cell_t)
        self.mins = mins
        self.m = np.zeros(len(mins), np.int64)
        self.top = np.full((len(mins), J), -np.inf, np.float32)
        for i, t in enumerate(mins.tolist()):
            a = t - 90 * D
            ia, ib = np.searchsorted(cts, a, "left"), np.searchsorted(cts, t, "left")
            self.m[i] = ib - ia
            hA = -(-a // H); hB = t // H                                  # gio day du [hA, hB)
            ha_end = np.searchsorted(cts, hA * H, "left"); hb_beg = np.searchsorted(cts, hB * H, "left")
            if hA < hB:
                full = topk_range(tree, max(hA - h0, 0), max(hB - h0, 0), J)
                x = np.concatenate([vals[ia:min(ha_end, ib)], full, vals[max(hb_beg, ia):ib]])
            else:
                x = vals[ia:ib]
            x = x[np.isfinite(x)]
            if len(x) > J:
                x = np.partition(x, len(x) - J)[len(x) - J:]
            x = np.sort(x)[::-1]
            self.top[i, :len(x)] = x
        self.idx = np.searchsorted(mins, self.cell_t)
        log.info("ArmSeed: o hop le %d, rmin %.6f, o ung vien DEV %d, phut %d", len(vals), self.rmin, len(self.cell_t), len(mins))

    def passes(self, pct):
        k = np.minimum(self.m - 1, np.maximum(0, np.floor(float(np.float32(pct)) * (self.m - 1)).astype(np.int64)))
        jj = self.m - 1 - k
        assert (jj < J).all(), int(jj.max())
        q = self.top[np.arange(len(self.mins)), jj]
        warm = (self.mins - self.first) < 7 * D
        q = np.where(warm | (self.m == 0), GO.BASE, q).astype(np.float32)
        assert (q[~warm] >= self.rmin).all(), "q phut < rmin => thieu o ung vien"
        qc = q[self.idx]
        P = ~(self.cell_p < (qc * self.cell_fac) * GO.GS)
        return {y: int(P[(self.cell_t >= a) & (self.cell_t < b)].sum()) for y, (a, b) in YB.items()}


B = dict(np.load(GO.CACHE + "/cand_base.npz"))
mp = pd.read_csv(GO.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
OUT = dict(prereg="f2222d05", lo=LO, hi=HI, tol=TOL, J=J, T22=T22, a0={}, arms={})
store = {"M1_MAX15_QMIN": {}, "M0_QMIN": {}}
for s in SEEDS:
    C = GO.build(s, B, s2id)
    G0 = GO.run_g2(C, J=256)
    dev = C["ts"]
    OUT["a0"][s] = {y: int(G0["P"][(dev >= a) & (dev < b)].sum()) for y, (a, b) in YB.items()}
    pts, p15 = GO.load_pred(GO.SEEDS[s][1])
    mx = pd.Series(p15.astype(np.float64), index=pd.to_datetime(pts, unit="ms")).rolling("15min", min_periods=12).max()
    pm = mx.reindex(pd.to_datetime(C["ts"], unit="ms")).to_numpy()
    pm = np.where(np.isfinite(pm), pm, np.nan).astype(np.float32)
    store["M1_MAX15_QMIN"][s] = ArmSeed(C, pm)
    store["M0_QMIN"][s] = ArmSeed(C, C["p15"])
    log.info("%s A0 %s", s, OUT["a0"][s])
    del C, G0
assert sum(v[2022] for v in OUT["a0"].values()) == T22, sum(v[2022] for v in OUT["a0"].values())
for a, st in store.items():
    lo, hi, it, res = LO, HI, 0, None
    while it < MAXIT:
        it += 1
        mid = float(np.float32((lo + hi) / 2))
        cs = {s: st[s].passes(mid) for s in SEEDS}
        N = sum(v[2022] for v in cs.values())
        log.info("%s it %d pct %.9f N22 %d ratio %.4f", a, it, mid, N, N / T22)
        if abs(N / T22 - 1) <= TOL:
            res = (mid, cs, N); break
        if N > T22: lo = mid
        else: hi = mid
    if res is None:
        OUT["arms"][a] = dict(converged=False, iters=it); continue
    pct, cs, N = res
    qy = {y: round(float(np.median([cs[s][y] / OUT["a0"][s][y] for s in SEEDS])), 4) for y in YB}
    OUT["arms"][a] = dict(converged=True, iters=it, pct=pct, pct_str="%.9f" % pct, N22=N, ratio22=round(N / T22, 4),
                          quota_year_median=qy, per_seed=cs)
    log.info("%s RESULT pct %s ratio22 %.4f quota_nam %s", a, "%.9f" % pct, N / T22, qy)
json.dump(OUT, open(R3 + "r5p2_iso.json", "w"), indent=1, default=str)
