#!/usr/bin/env python3
"""R5 CHAN DOAN SAU (khong thuoc luat prereg 200a29a3, KHONG doi ket luan): nghi van so dot.
MAX15/MEAN240 top-K phut dồn vao it dot hon RAW => (b) so 'it dot lon nhat' voi 'nhieu dot ca nho'.
Doi chung RAW-KHOP-DOT: lay dot RAW (top-4K phut, khu cum 60') xep theo dinh p15, giu n dot = so dot (b) cua bien the; Y72 o phut dau dot."""
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/r5_quality")
import r5_score as S  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r5diag")


def eps(ts, v, sel):
    t = ts[sel]
    st = np.r_[0, np.nonzero(np.diff(t) > S.GAP)[0] + 1]
    en = np.r_[st[1:], len(sel)]
    first = sel[st]
    peak = np.array([v[sel[a:b]].max() for a, b in zip(st, en)])
    return first, peak


def main():
    meta, D = S.load()
    vidx = {v: i for i, v in enumerate(meta["vars"])}
    out = {}
    for per, (lo, hi, kk) in {"disc": (S.YB[2022], S.YB[2024], "disc"), "conf": (S.YB[2024], S.YB[2026], "conf"),
                              "2024": (S.YB[2024], S.YB[2025], "2024"), "2025": (S.YB[2025], S.YB[2026], "2025")}.items():
        for vn in ("MAX15", "MEAN240"):
            rv, rr, nn = [], [], []
            for s in S.SEEDS:
                ts, V, y72, _ = D[s]
                m = (ts >= lo) & (ts < hi)
                K = meta["K"][s][kk]
                ep_v = S.declust(ts, S.topk(V[:, vidx[vn]], m, K))
                sel4 = S.topk(V[:, 0], m, 4 * K)
                f, pk = eps(ts, V[:, 0], sel4)
                n = len(ep_v)
                fr = f[np.argsort(-pk)[:n]]
                rv.append(np.nanmean(y72[ep_v]))
                rr.append(np.nanmean(y72[fr]))
                nn.append(n)
            out["%s_%s" % (per, vn)] = dict(n_ep=float(np.mean(nn)), var_b_pp=round(100 * float(np.mean(rv)), 2),
                                            raw_matched_pp=round(100 * float(np.mean(rr)), 2),
                                            diff_pp=round(100 * float(np.mean(rv) - np.mean(rr)), 2))
            log.info("%s %s %s", per, vn, out["%s_%s" % (per, vn)])
    json.dump(out, open(S.G + "diag_epmatch.json", "w"), indent=1)


if __name__ == "__main__":
    main()
