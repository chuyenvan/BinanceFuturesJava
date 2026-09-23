#!/usr/bin/env python3
"""OI_STUDY_POSTHOC — MO TA (POST-HOC / KHAI PHA), KHONG nam trong thiet ke pre-reg.

Pre-reg: docs/PREREG_OI_STUDY.md (commit 7c5f025). Script nay chi lam 3 viec MO TA, khong dung
de phan quyet:
  (1) MDE cho H3 (nua-do-rong x1.21 + p80 tren 500 chuoi null sign-flip 72h) — vi script chinh
      chi tinh MDE cho H1.
  (2) PHAN RA CHI PHI: gross (raw) vs fee vs slip vs funding cho EW va Q9 (24h) — de thay mat do
      cua "net" den tu dau (yeu cau "phi ghi ro").
  (3) MO TA thanh phan Q9/Q0: bien do 1m trung binh (rg5/c5) — chi de hieu Q9 la nhom coin nao.
Thuan Python, khong Java, khong cham 2026.
"""
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
OUT = "/tmp/oi_study"
SEED, NREP, BLOCK_H, CI_INFLATE, MIN_SYM = 20260905, 2000, 72, 1.21, 50
FEE = 0.0010
UTC = timezone.utc
say = print


def sums_of(net, blk):
    g = pd.DataFrame({"b": blk, "x": net}).groupby("b")["x"]
    return g.sum().values, g.count().values.astype(np.float64)


def half_centered(net, blk, nrep=NREP, seed=SEED):
    c = net - net.mean()
    s, cc = sums_of(c, blk)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), (nrep, len(s)))
    m = s[idx].sum(axis=1) / cc[idx].sum(axis=1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    return (hi - lo) / 2 * CI_INFLATE


def mde(net, blk, seed=SEED, nrep_null=500):
    s, c = sums_of(net, blk)
    rng = np.random.default_rng(seed)
    hs = []
    for r in range(nrep_null):
        sg = rng.choice([-1.0, 1.0], size=len(s))
        ss = sg * s
        ss = ss - ss.sum() / c.sum() * c
        idx = rng.integers(0, len(s), (NREP, len(s)))
        m = ss[idx].sum(axis=1) / c[idx].sum(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs.append((hi - lo) / 2 * CI_INFLATE)
    hs = np.array(hs)
    return float(np.percentile(hs, 80)), float(np.median(hs))


# ---------- (1) MDE cho H3 ----------
z = np.load(OUT + "/h3_events.npz")
mm, net, d24v, oizv, rk = z["mm"], z["net"], z["d24"], z["oiz"], z["rk"]
say("=== (1) MDE cho H3 (POST-HOC, chi mo ta) ===")
say("toan bo H3 DEV: N=%d" % len(net))
for nn, fv in (("all", np.ones(len(net))), ("d24 tercile0 (ΔOI thap)", d24v), ("d24 tercile2 (ΔOI cao)", d24v),
               ("rank_d24 tercile0", rk), ("rank_d24 tercile2", rk)):
    ok = np.isfinite(fv)
    if nn == "all":
        sel2 = ok
    else:
        ter = np.minimum((np.argsort(np.argsort(fv[ok], kind="stable")) * 3) // ok.sum(), 2)
        target = 0 if "0" in nn else 2
        sel2 = np.zeros(len(net), bool)
        sel2[np.flatnonzero(ok)[ter == target]] = True
    p80, p50 = mde(net[sel2], mm[sel2] // (BLOCK_H * 60))
    hc = half_centered(net[sel2], mm[sel2] // (BLOCK_H * 60))
    say("  %-26s N=%5d blk=%4d | half x1.21=%.4f%% | MDE(p80)=%.4f%%" % (
        nn, sel2.sum(), len(np.unique(mm[sel2] // (BLOCK_H * 60))), 100 * hc, 100 * p80))
# MDE cho tuong phan (hai chuoi doc lap) -> xap xi bang duong cheo: half(a)+half(b)
ok = np.isfinite(d24v)
ter = np.minimum((np.argsort(np.argsort(d24v[ok], kind="stable")) * 3) // ok.sum(), 2)
ix = np.flatnonzero(ok)
ha = half_centered(net[ix[ter == 2]], mm[ix[ter == 2]] // (BLOCK_H * 60))
hb = half_centered(net[ix[ter == 0]], mm[ix[ter == 0]] // (BLOCK_H * 60))
say("  tuong phan H3 d24 ter2-ter0: MDE(uoc luong duong cheo) = %.4f%% ; do duoc = -5.5075%%" % (
    100 * (ha + hb)))

# ---------- (2) PHAN RA CHI PHI ----------
say("")
say("=== (2) PHAN RA CHI PHI (24h, EW va Q9) — POST-HOC mo ta ===")
meta = json.load(open(OUT + "/meta.json"))
NSTEP, T0 = meta["nstep"], meta["T0"]
a0 = T0 * 1000 // 300000
i0 = (int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) * 1000 // 300000) - a0
d24 = np.load(OUT + "/d24.npy", mmap_mode="r")
c5 = np.load(OUT + "/c5.npy", mmap_mode="r")
rg5 = np.load(OUT + "/rg5.npy", mmap_mode="r")
f5 = np.load(OUT + "/f5.npy", mmap_mode="r")
hours = np.arange(i0 + ((-i0) % 12), NSTEP, 12, dtype=np.int64)
A = {g: {k: [] for k in ("raw", "fee", "slip", "fund")} for g in (9, 0, "EW")}
for i in hours:
    j = i + 288
    if j >= NSTEP:
        continue
    d, c = d24[i], c5[i]
    u = np.isfinite(d) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
    if u.sum() < MIN_SYM:
        continue
    idx = np.flatnonzero(u)
    order = np.argsort(d[idx], kind="stable")
    N = len(idx)
    dec_r = np.empty(N, dtype=np.int8)
    dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
    raw = c5[j][idx] / c[idx] - 1.0
    sl = 0.5 * rg5[i][idx] / c[idx]
    fu = f5[j][idx] - f5[i][idx]
    for g in (9, 0, "EW"):
        m = np.ones(N, bool) if g == "EW" else (dec_r == g)
        A[g]["raw"].append(raw[m]); A[g]["slip"].append(sl[m]); A[g]["fund"].append(fu[m])
say("  | nhom | N | gross(raw) | -fee | -slip | -fund | = net |")
for g in (9, 0, "EW"):
    r = np.concatenate(A[g]["raw"]); s = np.concatenate(A[g]["slip"]); f = np.concatenate(A[g]["fund"])
    net = r - FEE - s - f
    say("  | %-4s | %d | %+.4f%% | -0.1000%% | -%.4f%% | -%+.4f%% | %+.4f%% |" % (
        "Q9" if g == 9 else ("Q0" if g == 0 else "EW"), len(r), 100 * r.mean(), 100 * s.mean(),
        100 * f.mean(), 100 * net.mean()))

# ---------- (3) mo ta thanh phan Q9/Q0 ----------
say("")
say("=== (3) MO TA thanh phan decile (bien do 1m trung binh rg5/c5 @ 24h) — POST-HOC ===")
prof = {g: [] for g in range(10)}
for i in hours[::12]:
    d, c = d24[i], c5[i]
    u = np.isfinite(d) & np.isfinite(c) & (c > 0) & np.isfinite(rg5[i])
    if u.sum() < MIN_SYM:
        continue
    idx = np.flatnonzero(u)
    order = np.argsort(d[idx], kind="stable")
    N = len(idx)
    dec_r = np.empty(N, dtype=np.int8)
    dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
    rv = rg5[i][idx] / c[idx]
    for g in range(10):
        m = dec_r == g
        if m.any():
            prof[g].append(np.median(rv[m]))
say("  decile : " + "  ".join("Q%d" % g for g in range(10)))
say("  med(rg5/c5) %%: " + "  ".join("%.3f" % (100 * np.median(prof[g])) for g in range(10)))
