#!/usr/bin/env python3
"""HO2026_NOTF_EPISODE — phan ra ΔROI (A1 - A0) theo thang + do mong manh.

Doc lap voi scorer: doc lai printDone.csv (realized) + gia 1m Vision de MTM, dung lai logic
~/claude_master/audit_1030/aud_mtm.py (npz mtm_all_eq.npz da co). Khong chay sim, khong tune.

Dinh nghia:
  r_t(s)  = E_t/E_{t-1} - 1 (daily close 23:59 UTC), E_{-1} = equity_start
  dROI_m  = [prod_{t in m}(1+r_t(A1)) - 1] - [prod_{t in m}(1+r_t(A0)) - 1]   (pp)
  dROI_W9 = E_end/E_0 - 1 (A1) - (A0)                                          (pp)
  dROI_ex_X = tinh lai ROI tren chuoi ngay KHONG thuoc X (noi suy qua cac ngay con lai)
Bootstrap: moving block tren chuoi ngay (block 5 va 21 ngay, circular, B=5000), KHONG resample seed.
Usage: python3 ep_blocks.py [out.json]
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/audit_1030")
import aud_mtm as M  # noqa: E402

Z = np.load("/home/ubuntu/claude_master/audit_1030/mtm_all_eq.npz")
ND = M.NW // 1440
DAY0 = np.datetime64("2026-01-01")
SEEDS = M.SEEDS


def daily(E):
    """tra ve (e0, closes[ND]) voi closes[d] = E cuoi ngay d."""
    assert len(E) == M.NW
    return float(E[0]), E[1439::1440].astype(np.float64)


def rets(E):
    e0, c = daily(E)
    prev = np.concatenate([[e0], c[:-1]])
    return c / prev - 1.0


def roi(E, mask):
    e0, c = daily(E)
    prev = np.concatenate([[e0], c[:-1]])
    r = c / prev - 1.0
    return 100 * (np.prod(1 + r[mask]) - 1)


def dseries(cfg_a, cfg_b):
    """mean qua seed cua (rA1 - rA0) theo ngay."""
    D = []
    for s in SEEDS:
        D.append(rets(Z[cfg_b % s]) - rets(Z[cfg_a % s]))
    return np.mean(D, axis=0)


def block_boot(d, L, B=5000, seed=20261030):
    rng = np.random.default_rng(seed)
    n = len(d)
    nb = int(np.ceil(n / L))
    out = np.empty(B)
    for i in range(B):
        st = rng.integers(0, n, nb)
        idx = np.concatenate([(np.arange(k, k + L) % n) for k in st])[:n]
        out[i] = 100 * d[idx].sum()
    return dict(mean=round(float(out.mean()), 3), p05=round(float(np.percentile(out, 5)), 3),
                p50=round(float(np.percentile(out, 50)), 3), p95=round(float(np.percentile(out, 95)), 3),
                p_le0=round(float((out <= 0).mean()), 3))


def main(outp):
    months = sorted({str(DAY0 + np.timedelta64(d, "D"))[:7] for d in range(ND)})
    day_month = np.array([str(DAY0 + np.timedelta64(d, "D"))[:7] for d in range(ND)])
    ep = np.array([("2026-06-02" <= str(DAY0 + np.timedelta64(d, "D")) <= "2026-06-06") for d in range(ND)])
    june = day_month == "2026-06"
    R = {"def": "xem docstring", "configs": {}}
    for name, A, B in (("k24s", M.A0["k24s"], M.A1["k24s"]), ("x14", M.A0["x14"], M.A1["x14"])):
        d = dseries(A, B)
        per = {}
        for m in months:
            mk = day_month == m
            # dROI thang = chenh lech ROI tung ben (compounding trong thang)
            ra = np.mean([roi(Z[A % s], mk) for s in SEEDS])
            rb = np.mean([roi(Z[B % s], mk) for s in SEEDS])
            per[m] = dict(droi=round(float(rb - ra), 3), contrib_pp=round(float(100 * d[mk].sum()), 3),
                          n_days=int(mk.sum()),
                          pos_seeds=int(sum((roi(Z[B % s], mk) - roi(Z[A % s], mk)) > 0 for s in SEEDS)))
        w9 = np.mean([100 * (Z[B % s][-1] / Z[B % s][0] - 1) - 100 * (Z[A % s][-1] / Z[A % s][0] - 1) for s in SEEDS])
        ex_j = np.mean([roi(Z[B % s], ~june) - roi(Z[A % s], ~june) for s in SEEDS])
        ex_ep = np.mean([roi(Z[B % s], ~ep) - roi(Z[A % s], ~ep) for s in SEEDS])
        ex_june_only = np.mean([roi(Z[B % s], june) - roi(Z[A % s], june) for s in SEEDS])
        R["configs"][name] = dict(
            w9=round(float(w9), 3), months=per,
            ex_june=round(float(ex_j), 3), ex_ep_0602_0606=round(float(ex_ep), 3),
            ex_june_arith=round(float(100 * d[~june].sum()), 3), ex_ep_arith=round(float(100 * d[~ep].sum()), 3),
            june_only=round(float(ex_june_only), 3),
            sum_daily_pp=round(float(100 * d.sum()), 3),
            boot_block5=block_boot(d, 5), boot_block21=block_boot(d, 21),
            sign_days=dict(pos=int((d > 0).sum()), neg=int((d < 0).sum()), zero=int((d == 0).sum())))
    json.dump(R, open(outp, "w"), indent=1)
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ep_blocks.json")
