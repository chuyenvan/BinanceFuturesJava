#!/usr/bin/env python3
"""IND_COMBO P0 (prereg 14ed6c00) track G buoc 1: r/q theo phut cho 1 seed, cau hinh Y HET R5 Pha 1 (r5_signal.py).
Usage: ind_g2.py S42. Output ~/claude_master/ind1114/g2_<seed>.npz: ts (phut DEV co pass hoac max r/q >= 0,70), pas, mrq.
Kiem: so phut pass theo nam KHOP sig_meta.json R5. KHONG doc Y."""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("indg2")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
OUT = "/home/ubuntu/claude_master/ind1114/"


def main(s):
    B = dict(np.load(GO.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    C = GO.build(s, B, s2id)
    del B
    ts, p, SP, valid = C["ts"], C["p15"], C["SP"], C["valid"]
    fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT).astype(np.float32)
    r = (p[:, None] / (fac * GO.GS)).astype(np.float32)
    del C["SP"], C["SY"], C["d"]
    vals = r[valid]
    hv = np.repeat(ts // GO.H, valid.sum(1))
    first = int(ts[np.nonzero(valid.any(1))[0][0]])
    q, qh, jmax = GO.hourly_q(vals, hv, first, 90, float(GO.PCT), 256)
    del vals, hv
    warm = np.isnan(q)
    qq = np.where(warm, GO.BASE, q).astype(np.float32)
    idx = np.clip(np.searchsorted(qh, ts // GO.H), 0, len(qh) - 1)
    qm = qq[idx]
    thr = (qm[:, None] * fac) * GO.GS
    would = ~np.isnan(SP) & ~(p[:, None] < thr)
    P = valid & would
    pas = P.any(1)
    rq = np.where(valid, r / qm[:, None], -np.inf)
    mrq = rq.max(1).astype(np.float32)
    log.info("%s pass cells %d jmax %d rss %.2f GB", s, int(P.sum()), jmax, GO.rss())
    meta = json.load(open("/home/ubuntu/claude_master/res1109/r5_quality/sig_meta.json"))["K"][s]
    chk = {}
    for y in (2022, 2023, 2024, 2025):
        m = (ts >= YB[y]) & (ts < YB[y + 1])
        chk[str(y)] = (int(pas[m].sum()), meta[str(y)])
    log.info("%s K pass theo nam (ta, R5) %s", s, chk)
    assert all(a == b for a, b in chk.values()), "K KHONG KHOP R5"
    # nhat quan: phut khong pass => mrq < 1
    assert not np.any((~pas) & (mrq >= 1.0) & (ts >= YB[2022]) & (ts < YB[2026])), "mrq>=1 ma khong pass"
    keep = (ts >= YB[2022]) & (ts < YB[2026]) & (pas | (mrq >= 0.70))
    np.savez(OUT + "g2_%s.npz" % s, ts=ts[keep], pas=pas[keep], mrq=mrq[keep])
    log.info("%s luu %d phut (pass %d, nm70 %d)", s, int(keep.sum()), int(pas[keep].sum()), int((keep & ~pas).sum()))


if __name__ == "__main__":
    main(sys.argv[1])
