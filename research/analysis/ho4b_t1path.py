#!/usr/bin/env python3
"""HO4-P0b Q1: Tool1 phu thuoc diem bat dau? So t1 (start 10-01) vs t1e (start 09-15) THEO NGAY tren 10-01..10-16 UTC:
ty le o khop toan bo va mot so cot (micro #36 ret15m, funding percentile #22, btcDominance #4) -> xem co hoi tu (warm-up)
hay lech ben (trang thai tich luy). Chi ty le, cua so 2025. Usage: ho4b_t1path.py <t1x_out_dir> <out.json>"""
import glob, json, logging, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ARGV = sys.argv[:]
sys.argv = ["x", "-", "-", "-"]
import ho4b_detcmp as D  # noqa: E402  (dung chung load_t1/okc/cua so TLO..THI)
sys.argv = ARGV

log = logging.getLogger("ho4b_t1path")


def main():
    od, out = sys.argv[1], sys.argv[2]
    ka, fa = D.load_t1(glob.glob(os.path.join(od, "t1", "*.t1c.gz"))[0])
    kb, fb = D.load_t1(glob.glob(os.path.join(od, "t1e", "*.t1c.gz"))[0])
    com, ia, ib = np.intersect1d(ka, kb, return_indices=True)
    ok = np.ones((len(com), fa.shape[1]), dtype=bool)
    for j in range(fa.shape[1]):
        ok[:, j] = D.okc(fa[ia, j], fb[ib, j])
    day = (com // 10000 - D.TLO) // 86400000
    res = {"n_common": int(len(com)), "by_day": {}}
    for d in np.unique(day):
        m = day == d
        res["by_day"][int(d)] = {"cells": round(float(ok[m].mean()), 4), "c3_btcDom": round(float(ok[m, 3].mean()), 4),
                                 "c21_fundPct": round(float(ok[m, 21].mean()), 4), "c35_ret15m": round(float(ok[m, 35].mean()), 4),
                                 "c16_basketVolSpike": round(float(ok[m, 16].mean()), 4)}
        log.info("day %d %s", d, res["by_day"][int(d)])
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
