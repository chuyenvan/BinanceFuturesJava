"""FS buoc 4: block-bootstrap CI cua HIEU theo PREREG_FS muc 3.3 (= PREREG_CI muc 3).
usage: fs_boot2.py <ticks.parquet> <tag>
2000 rep, seed 20260903, block 72h chinh + 24h/168h, CI percentile cua HIEU, ghep cap."""
import logging, sys, os
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)

TKP = sys.argv[1]
TAG = sys.argv[2]
H = 3600000
TZ = 7 * H
SEED = 20260903
NREP = 2000
NCAND = 16
THR = float(np.sqrt(2.0 * np.log(NCAND)))
SELECT_END = int(pd.Timestamp("2024-01-01").value // 1e6) - TZ
BLOCKS = {"72h": 72 * H, "24h": 24 * H, "168h": 168 * H}
WINDOWS = {"SELECT": (None, SELECT_END), "CONFIRM": (SELECT_END, None), "ALL": (None, None)}
BASE = "base7"

T = pd.read_parquet(TKP)
L.info("[%s] ticks %s arms=%d", TAG, T.shape, T.arm.nunique())
L.info("arms: %s", sorted(T.arm.unique()))
L.info("nguong hieu chinh so sanh boi: sqrt(2 ln %d) = %.6f", NCAND, THR)
arms = [a for a in sorted(T.arm.unique()) if a not in (BASE, "keep9_gpu", "keep9_cpu")]
rows = []
for outc in ("g1_replay", "g1lite"):
    Tb = T[(T.arm == BASE) & (T.outc == outc)][["ts", "ic"]].rename(columns={"ic": "b"})
    if len(Tb) == 0:
        L.info("thieu base cho %s", outc)
        continue
    for arm in arms:
        Ta = T[(T.arm == arm) & (T.outc == outc)][["ts", "ic"]].rename(columns={"ic": "a"})
        J = Tb.merge(Ta, on="ts", how="inner").sort_values("ts").reset_index(drop=True)
        for wn, (lo, hi) in WINDOWS.items():
            W = J
            if lo is not None:
                W = W[W.ts >= lo]
            if hi is not None:
                W = W[W.ts < hi]
            if len(W) < 50:
                continue
            d0 = float(W.a.mean() - W.b.mean())
            rec = {"arm": arm, "outcome": outc, "window": wn, "n_tick": len(W),
                   "rankic_base": float(W.b.mean()), "rankic_arm": float(W.a.mean()),
                   "delta": d0}
            tmin = int(W.ts.min())
            av, bv = W.a.to_numpy(), W.b.to_numpy()
            for bn, Lb in BLOCKS.items():
                bid = ((W.ts.to_numpy() - tmin) // Lb).astype(np.int64)
                ub = np.unique(bid)
                idx = [np.where(bid == u)[0] for u in ub]
                rng = np.random.default_rng(SEED)
                nb = len(ub)
                ds = np.empty(NREP)
                for r in range(NREP):
                    ii = np.concatenate([idx[p] for p in rng.integers(0, nb, nb)])
                    ds[r] = av[ii].mean() - bv[ii].mean()
                rec[f"sd_{bn}"] = float(ds.std(ddof=1))
                rec[f"lo_{bn}"] = float(np.percentile(ds, 2.5))
                rec[f"hi_{bn}"] = float(np.percentile(ds, 97.5))
                rec[f"pgt0_{bn}"] = float((ds > 0).mean())
                rec[f"neff_{bn}"] = int(nb)
            for bn in BLOCKS:
                rec[f"excl0_{bn}"] = bool(rec[f"lo_{bn}"] > 0 or rec[f"hi_{bn}"] < 0)
            rec["excl0_all3"] = bool(all(rec[f"excl0_{b}"] for b in BLOCKS))
            rec["thr"] = THR * rec["sd_72h"]
            rec["over_thr"] = bool(abs(d0) >= rec["thr"])
            rows.append(rec)
            L.info("%-24s %-10s %-8s d=%+.5f sd72=%.5f CI72[%+.5f,%+.5f] thr=%.5f "
                   "over=%-5s excl3=%-5s neff=%d", arm, outc, wn, d0, rec["sd_72h"],
                   rec["lo_72h"], rec["hi_72h"], rec["thr"], rec["over_thr"],
                   rec["excl0_all3"], rec["neff_72h"])

R = pd.DataFrame(rows)
R.to_csv(f"/home/ubuntu/fs/fs_boot_{TAG}.csv", index=False)
L.info("\n===== LUAT QUYET DINH PREREG_FS 3.4 / 4 (%s) =====", TAG)


def g(arm, outc, wn):
    s = R[(R.arm == arm) & (R.outcome == outc) & (R.window == wn)]
    return s.iloc[0] if len(s) else None


verd = []
for arm in arms:
    s = g(arm, "g1_replay", "SELECT")
    if s is None:
        continue
    passed = bool(s.delta > 0 and s.over_thr and s.excl0_all3)
    c = g(arm, "g1_replay", "CONFIRM")
    conf = bool(passed and c is not None and np.sign(c.delta) == np.sign(s.delta)
                and c.excl0_72h)
    gl = g(arm, "g1lite", "SELECT")
    glp = bool(gl is not None and gl.delta > 0 and gl.over_thr and gl.excl0_all3)
    verd.append({"arm": arm, "T1": bool(s.delta > 0), "T2": bool(s.over_thr),
                 "T3": bool(s.excl0_all3), "PASS_replay": passed, "CONFIRMED": conf,
                 "PASS_g1lite": glp,
                 "d_rep_sel": float(s.delta), "sd72_rep_sel": float(s.sd_72h),
                 "thr_rep_sel": float(s.thr),
                 "d_rep_conf": float(c.delta) if c is not None else np.nan,
                 "d_rep_all": float(g(arm, "g1_replay", "ALL").delta),
                 "d_gl_sel": float(gl.delta) if gl is not None else np.nan,
                 "d_gl_all": float(g(arm, "g1lite", "ALL").delta)
                 if g(arm, "g1lite", "ALL") is not None else np.nan})
V = pd.DataFrame(verd).sort_values("d_rep_sel", ascending=False)
pd.set_option("display.width", 300)
L.info("\n%s", V.round(5).to_string(index=False))
V.to_csv(f"/home/ubuntu/fs/fs_verdict_{TAG}.csv", index=False)
n = V[V.arm == "cand_fs_noise"]
if len(n):
    L.info("\nDOI CHUNG AM fs_noise: PASS_replay=%s PASS_g1lite=%s => pipeline %s",
           n.PASS_replay.iloc[0], n.PASS_g1lite.iloc[0],
           "SAI (DUNG NGAY)" if n.PASS_replay.iloc[0] else "OK")
for cs in ("ctrl_seed1", "ctrl_seed7"):
    s = g(cs, "g1_replay", "SELECT")
    if s is not None:
        L.info("SAN NHIEU SEED %s: d=%+.5f sd72=%.5f thr=%.5f over_thr=%s",
               cs, s.delta, s.sd_72h, s.thr, s.over_thr)
L.info("BOOT_DONE %s", TAG)
