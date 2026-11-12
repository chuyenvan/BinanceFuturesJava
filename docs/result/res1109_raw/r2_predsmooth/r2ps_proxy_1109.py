#!/usr/bin/env python3
"""R2 PHA0 proxy (chi do, market-level, KHONG phai gate that): so phut cuc tri p15 diem vs cac dang lam muot causal.
Gate that = r = p15/factor(sp) so voi q_t (pct 0.99995 tren buffer ung vien) -> day chi la xap xi thoi diem."""
import logging
import struct
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("r2px")


def load(p):
    with open(p, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        a = np.frombuffer(f.read(16 * n), dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r4h", ">f4")]))
    return a["ts"].astype(np.int64), a["p15"].astype(np.float64)


def causal_mean(v, w):
    s = np.cumsum(np.concatenate([[0.0], v]))
    out = np.full_like(v, np.nan)
    out[w - 1:] = (s[w:] - s[:-w]) / w
    return out


def ewma(v, hl):
    a = 1 - 0.5 ** (1.0 / hl)
    out = np.empty_like(v)
    m = v[0]
    for i, x in enumerate(v):
        m = a * x + (1 - a) * m
        out[i] = m
    return out


def causal_max(v, w):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full_like(v, np.nan)
    out[w - 1:] = sliding_window_view(v, w).max(axis=1)
    return out


def episodes(idx, gap):
    if len(idx) == 0:
        return []
    starts = [idx[0]]
    for a, b in zip(idx[:-1], idx[1:]):
        if b - a > gap:
            starts.append(b)
    return starts


def main(p, frac):
    ts, v = load(p)
    arms = {"P1": v, "mean15": causal_mean(v, 15), "mean60": causal_mean(v, 60),
            "mean240": causal_mean(v, 240), "ewma_hl15": ewma(v, 15), "max15": causal_max(v, 15)}
    k = int(round(frac * len(v)))
    base_idx = np.sort(np.argsort(-v)[:k])
    base_ep = episodes(base_idx, 60)
    LOG.info("file=%s n=%d top_frac=%g k=%d base_episodes(gap60)=%d", p, len(v), frac, k, len(base_ep))
    bset = set(base_idx.tolist())
    for name, x in arms.items():
        xx = np.where(np.isnan(x), -np.inf, x)
        idx = np.sort(np.argsort(-xx)[:k])
        ep = episodes(idx, 60)
        jac = len(bset & set(idx.tolist())) / len(bset | set(idx.tolist()))
        # do tre: moi dot base, phut dau tien arm vao top trong [t-60, t+240]
        delays = []
        miss = 0
        for s in base_ep:
            j = np.searchsorted(idx, s - 60)
            if j < len(idx) and idx[j] <= s + 240:
                delays.append(idx[j] - s)
            else:
                miss += 1
        d = np.array(delays) if delays else np.array([np.nan])
        ok = ~np.isnan(x)
        r = np.corrcoef(v[ok], x[ok])[0, 1]
        LOG.info("%-9s corr=%.3f episodes=%4d jaccard_phut=%.3f base_ep_hit=%d miss=%d delay_min med=%.0f p25=%.0f p75=%.0f",
                 name, r, len(ep), jac, len(delays), miss, np.nanmedian(d), np.nanpercentile(d, 25), np.nanpercentile(d, 75))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
