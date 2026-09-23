#!/usr/bin/env python3
"""OI_STUDY_POSTHOC2 — KIEM TRA NHIEU (POST-HOC / KHAI PHA), KHONG nam trong pre-reg.

Cau hoi: ket qua H3 (tercile ΔOI THAP cua MOM15 tot hon) co phai chi la proxy cho DO SAU CU RO
(chinh bien ma MOM15 dung de chon coin: d15 = C/max(H,15)-1)? Neu co, "thong tin OI" khong doc lap.

Do: (a) spearman(d24, d15) tai entry; (b) bang 3x3 [d15 tercile x ΔOI tercile] net 24h;
(c) trong TUNG tercile d15, ΔOI con tach duoc khong.

Thuan Python, khong Java, khong cham 2026. m_d15 lay tu /tmp/funding_factor/d15.npz (d15 tai entry).
"""
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")
COLS = ("n", "mean", "ci_lo", "ci_hi", "mean_oos")
UTC = timezone.utc


def ter3(v):
    return np.minimum((np.argsort(np.argsort(v, kind="stable")) * 3) // len(v), 2)


def stats(net, ts):
    """mean + CI block-72h x1.21 (doc lap) + OOS."""
    import pandas as pd
    blk = (ts // (72 * 60)).astype(np.int64)
    g = pd.DataFrame({"b": blk, "x": net}).groupby("b")["x"]
    s, c = g.sum().values, g.count().values.astype(np.float64)
    rng = np.random.default_rng(20260905)
    idx = rng.integers(0, len(s), (2000, len(s)))
    m = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    obs = net.mean()
    half = (hi - lo) / 2 * 1.21
    oos = ts >= int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()) // 60
    return dict(n=len(net), mean=obs, ci_lo=obs - half, ci_hi=obs + half,
                mean_oos=net[oos].mean() if oos.any() else float("nan"))


def show(lab, d):
    print("  %-34s N=%6d mean=%+.4f%% CI72h_x1.21=[%+.4f%%,%+.4f%%] OOS=%+.4f%%" % (
        lab, d["n"], 100 * d["mean"], 100 * d["ci_lo"], 100 * d["ci_hi"], 100 * d["mean_oos"]))


h = np.load("/tmp/oi_study/h3_events.npz")
mm, net, d24v, oizv, rk = h["mm"], h["net"], h["d24"], h["oiz"], h["rk"]
z = np.load("/tmp/funding_factor/pools.npz")
m_min = z["m_min"].astype(np.int64); m_valid = z["m_valid"]; m_raw = z["m_raw"]
m_slip = z["m_slip"]; m_fund = z["m_fund"]
d15all = np.load("/tmp/funding_factor/d15.npz")["m_d15"].astype(np.float64)
base24 = m_raw[1].astype(np.float64) - m_slip.astype(np.float64) - m_fund[1].astype(np.float64)
DEV0 = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60
DEV1 = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
sel = (m_min >= DEV0) & (m_min < DEV1) & (((m_valid >> 1) & 1) == 1) & np.isfinite(base24)
d15 = d15all[sel]
print("=== POST-HOC: nhieu d15 (do sau cu ro) vs ΔOI trong MOM15 (n=%d) ===" % len(d15))
ok = np.isfinite(d24v) & np.isfinite(d15)
print("  spearman(d24_entry, d15_entry) = %.4f  (n=%d)" % (
    np.corrcoef(np.argsort(np.argsort(d24v[ok])), np.argsort(np.argsort(d15[ok])))[0, 1], ok.sum()))
t_d15 = ter3(d15[ok])
t_oi = ter3(d24v[ok])
nn = net[ok]; tt = mm[ok]
print("")
print("  bang net 24h  [hang = tercile d15 (0=cu ro NONG nhat -> 2=nhe nhat), cot = tercile ΔOI thap->cao]:")
for a in range(3):
    row = []
    for b in range(3):
        m = (t_d15 == a) & (t_oi == b)
        row.append("%+8.4f (N=%4d)" % (100 * nn[m].mean(), m.sum()) if m.any() else "     n/a     ")
    print("    d15_ter%d: " % a + "  ".join(row))
print("")
print("  TRONG TUNG tercile d15, ΔOI con tach duoc khong (ter2 - ter0):")
for a in range(3):
    m2 = (t_d15 == a) & (t_oi == 2); m0 = (t_d15 == a) & (t_oi == 0)
    if m2.sum() < 50 or m0.sum() < 50:
        continue
    print("    d15_ter%d: ter2=%+.4f%% (N=%d) vs ter0=%+.4f%% (N=%d) -> chenh %+.4f%%" % (
        a, 100 * nn[m2].mean(), m2.sum(), 100 * nn[m0].mean(), m0.sum(),
        100 * (nn[m2].mean() - nn[m0].mean())))
print("")
print("  Trong tung tercile ΔOI, d15 con tach duoc khong (d15_ter0 - d15_ter2):")
for b in range(3):
    m0 = (t_oi == b) & (t_d15 == 0); m2 = (t_oi == b) & (t_d15 == 2)
    if m0.sum() < 50 or m2.sum() < 50:
        continue
    print("    ΔOI_ter%d: d15ter0=%+.4f%% (N=%d) vs d15ter2=%+.4f%% (N=%d) -> chenh %+.4f%%" % (
        b, 100 * nn[m0].mean(), m0.sum(), 100 * nn[m2].mean(), m2.sum(),
        100 * (nn[m0].mean() - nn[m2].mean())))
print("")
print("  mean d15 theo tercile ΔOI: " + "  ".join(
    "ΔOI_ter%d=%.2f%%" % (b, 100 * d15[ok][t_oi == b].mean()) for b in range(3)))
print("  mean ΔOI theo tercile d15: " + "  ".join(
    "d15_ter%d=%.4f" % (a, np.nanmean(d24v[ok][t_d15 == a])) for a in range(3)))
print("")
print("  (doi chieu) net 24h theo tercile d15 (khong dung OI):")
for a in range(3):
    m = t_d15 == a
    show("d15_ter%d" % a, stats(nn[m], tt[m]))
