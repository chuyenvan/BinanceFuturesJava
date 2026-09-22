#!/usr/bin/env python3
"""FUNDING_FACTOR extra (DESCRIPTIVE, post-hoc) — khong phai test khoa.

(a) Spearman(f_entry, d15) tai phut MOM15 fire (T3 co phai proxy do sau dump?).
(b) T3 phan tang: trong (phut fire x decile-d15) — diff net(f_entry<=0) - net(f_entry>0).
(c) Ky luat dau theo BLOCK-72h cho T1 (spread D10-D1) va T3 — bo sung cho cong '%phut dung dau'.
Doc $FF_OUT/{pools.npz,d15.npz}. Thuan Python, chi doc.
"""
import os
import logging
from datetime import datetime, timezone

import numpy as np

OUT = os.environ.get("FF_OUT", "/tmp/funding_factor")
SEED = 20260905
NREP = 2000
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
MIN_SYM = 50
DEC = 10
FEE = 0.0010
UTC = timezone.utc
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/extra.log")])
log = logging.getLogger("ffextra")
rep = []


def say(s=""):
    rep.append(s)
    log.info(s)


def fmt(x):
    return "%.4f%%" % (100 * x) if np.isfinite(x) else "nan"


def summ(net, blk, seed=SEED):
    b, inv = np.unique(blk, return_inverse=True)
    sums = np.bincount(inv, weights=net, minlength=len(b))
    cnts = np.bincount(inv, minlength=len(b))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(b), size=(NREP, len(b)))
    m = sums[idx].sum(1) / cnts[idx].sum(1)
    lo, hi = np.percentile(m, [2.5, 97.5])
    half = (hi - lo) / 2 * CI_INFLATE
    obs = float(net.mean())
    return obs, obs - half, obs + half, float((m > 0).mean()), len(b)


def main():
    z = np.load(OUT + "/pools.npz")
    dz = np.load(OUT + "/d15.npz")
    holds = [int(x) for x in z["holds"]]
    j24 = holds.index(1440)
    a_min, a_f, a_raw, a_slip, a_fund, a_valid = z["a_min"], z["a_f"].astype(np.float64), z["a_raw"], z["a_slip"].astype(np.float64), z["a_fund"], z["a_valid"]
    p_min, p_sym, p_f = z["p_min"], z["p_sym"], z["p_f"].astype(np.float64)
    p_raw, p_slip, p_fund, p_valid = z["p_raw"], z["p_slip"].astype(np.float64), z["p_fund"], z["p_valid"]
    m_min, m_f, m_raw, m_slip, m_fund, m_valid = z["m_min"], z["m_f"].astype(np.float64), z["m_raw"], z["m_slip"].astype(np.float64), z["m_fund"], z["m_valid"]
    p_d15, m_d15 = dz["p_d15"].astype(np.float64), dz["m_d15"].astype(np.float64)
    netp = p_raw[j24].astype(np.float64) - p_slip - p_fund[j24].astype(np.float64)
    neta = a_raw[j24].astype(np.float64) - a_slip - a_fund[j24].astype(np.float64)
    deva = (a_min >= DEV_START) & (a_min < DEV_END)
    devp = (p_min >= DEV_START) & (p_min < DEV_END)
    devm = (m_min >= DEV_START) & (m_min < DEV_END)

    say("=== FUNDING_FACTOR extra (DESCRIPTIVE, POST-HOC — không phải test khoá) ===")

    # (a) Spearman(f_entry, d15) tai phut fire
    fv = np.isfinite(p_f) & np.isfinite(p_d15)
    o = np.argsort(p_min[fv], kind="stable")
    mn = p_min[fv][o]; ff = p_f[fv][o]; dd = p_d15[fv][o]
    first = np.r_[True, mn[1:] != mn[:-1]]
    gid = np.cumsum(first) - 1
    ic = []
    for g in range(len(np.unique(gid))):
        pass
    starts = np.flatnonzero(first)
    ends = np.r_[starts[1:], len(mn)]
    for a0, b0 in zip(starts, ends):
        if b0 - a0 < MIN_SYM:
            continue
        x = ff[a0:b0]; y = dd[a0:b0]
        rx = np.argsort(np.argsort(x)).astype(np.float64)
        ry = np.argsort(np.argsort(y)).astype(np.float64)
        rx -= rx.mean(); ry -= ry.mean()
        den = np.sqrt((rx * rx).sum() * (ry * ry).sum())
        if den > 0:
            ic.append((mn[a0], (rx * ry).sum() / den))
    icv = np.array([x[1] for x in ic]); icm = np.array([x[0] for x in ic])
    d = (icm >= DEV_START) & (icm < DEV_END)
    say("")
    say("## (a) Spearman(f_entry, d15) tại phút MOM15 fire — DEV")
    say("  mean=%+.4f (SD %.4f) | CI72h×1.21=[%+.4f, %+.4f] | N_phút=%d" % (
        icv[d].mean(), icv[d].std(), *(lambda t: (t[1], t[2]))(summ(icv[d], (icm[d] // BLOCK_MIN).astype(np.int64)))[:2], int(d.sum())))
    say("  (âm ⇒ funding thấp đi cùng coin dump sâu hơn ⇒ T3 có thể chỉ là proxy độ sâu dump)")

    # (b) T3 phan tang theo decile d15 trong tung phut fire
    say("")
    say("## (b) T3 phân tầng: trong (phút fire × decile-d15) — diff net(f_entry≤0) − net(f_entry>0), HOLD 24h, DEV")
    sel = devp & fv & (((p_valid >> j24) & 1) == 1)
    m2 = p_min[sel]; f2 = p_f[sel]; d2 = p_d15[sel]; n2 = netp[sel]
    o2 = np.lexsort((d2, m2))
    m2s, f2s, d2s, n2s = m2[o2], f2[o2], d2[o2], n2[o2]
    first = np.r_[True, m2s[1:] != m2s[:-1]]
    gstart = np.flatnonzero(first)
    gid = np.cumsum(first) - 1
    rank = np.arange(len(m2s)) - gstart[gid]
    gsize = np.bincount(gid)
    ddec = np.minimum(rank * DEC // np.maximum(gsize[gid], 1), DEC - 1)
    low_ok = (gsize[gid] >= MIN_SYM)
    comp = gid * DEC + ddec
    ncell = (gid.max() + 1) * DEC
    tot = np.bincount(comp[low_ok], weights=n2s[low_ok], minlength=ncell)
    lo_c = np.bincount(comp[low_ok & (f2s <= 0)], weights=n2s[low_ok & (f2s <= 0)], minlength=ncell)
    n_lo = np.bincount(comp[low_ok & (f2s <= 0)], minlength=ncell)
    n_hi = np.bincount(comp[low_ok & (f2s > 0)], minlength=ncell)
    hi_c = tot - lo_c
    okc = (n_lo >= 5) & (n_hi >= 5)
    say("  cell (phút×decile-d15) đủ điều kiện ≥5 coin/nhóm: %d / %d" % (int(okc.sum()), ncell))
    if okc.any():
        diff_cell = lo_c[okc] / n_lo[okc] - hi_c[okc] / n_hi[okc]
        blk = (np.repeat(np.unique(gid), DEC).reshape(-1, DEC)[okc.reshape(-1, DEC)] // 1)
        cell_gid = np.repeat(np.arange(gid.max() + 1), DEC)[okc]
        blk = (cell_gid // 1)
        # block = block-72h cua phut fire: lay phut cua cell
        cells_min = np.repeat(np.unique(m2s), DEC)[okc]
        blkc = (cells_min // BLOCK_MIN).astype(np.int64)
        s = summ(diff_cell, blkc)
        say("  weighted diff (cell-mean) = %s | CI72h×1.21=[%s, %s] | p(>0)=%.4f | N_cell=%d N_blk=%d" % (
            fmt(s[0]), fmt(s[1]), fmt(s[2]), s[3], len(diff_cell), s[4]))
        # weighted by cell size
        w = (n_lo[okc] + n_hi[okc]).astype(np.float64)
        say("  (trọng số theo cell-size) diff = %s ; số cell dương = %.1f%%" % (
            fmt(float((diff_cell * w).sum() / w.sum())), 100 * float((diff_cell > 0).mean())))
        # theo decile
        say("")
        say("  | decile-d15 | N_cell | diff | %cell>0 |")
        say("  |---|---|---|---|")
        ddec_cell = np.repeat(np.arange(DEC), 1) if False else np.tile(np.arange(DEC), gid.max() + 1)[okc]
        for dd_ in range(DEC):
            ww = ddec_cell == dd_
            if ww.sum():
                say("  | %d | %d | %s | %.1f%% |" % (dd_ + 1, int(ww.sum()), fmt(float(diff_cell[ww].mean())),
                                                     100 * float((diff_cell[ww] > 0).mean())))

    # (c) ky luat dau theo block 72h
    say("")
    say("## (c) Kỷ luật dấu theo BLOCK-72h (bổ sung cho cổng '%phút đúng dấu')")
    # T1: minute-level spread D10-D1
    a_net = neta
    ok = (((a_valid >> j24) & 1) == 1) & np.isfinite(a_net) & np.isfinite(a_f)
    order3 = np.lexsort((a_f, a_min))
    smin = a_min[order3]
    first = np.r_[True, smin[1:] != smin[:-1]]
    gs = np.flatnonzero(first)
    gid3 = np.cumsum(first) - 1
    gsize = np.bincount(gid3)
    rank3 = np.arange(len(order3)) - gs[gid3]
    dec3_o = np.minimum(rank3 * DEC // np.maximum(gsize[gid3], 1), DEC - 1)
    umin = smin[first]
    vmin = gsize >= MIN_SYM
    dec3 = np.empty(len(a_min), dtype=np.int8); dec3[order3] = dec3_o
    gidr = np.empty(len(a_min), dtype=np.int64); gidr[order3] = gid3
    keep = ok & vmin[np.clip(gidr, 0, len(umin) - 1)]
    comp = np.where(keep, gidr * DEC + dec3, -1)[keep]
    w = a_net[keep]
    ncell = len(umin) * DEC
    S = np.bincount(comp, weights=w, minlength=ncell).reshape(len(umin), DEC)
    C = np.bincount(comp, minlength=ncell).reshape(len(umin), DEC).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        M = np.where(C > 0, S / C, np.nan)
    Mv = M[vmin]
    series = Mv[:, 9] - Mv[:, 0]
    mm = umin[vmin]
    g = np.isfinite(series)
    series, mm = series[g], mm[g]
    for wname, wsel in (("DEV", (mm >= DEV_START) & (mm < DEV_END)), ("ALL", np.ones(len(mm), bool))):
        sv, mv = series[wsel] - FEE, mm[wsel]
        log.info("dbg %s len(sv)=%d", wname, len(sv))
        blk = (mv // BLOCK_MIN).astype(np.int64)
        ublk = np.unique(blk)
        bmean = np.bincount(np.searchsorted(ublk, blk), weights=sv, minlength=len(ublk)) / np.bincount(np.searchsorted(ublk, blk), minlength=len(ublk))
        uday = np.unique((mv + 420) // 1440)
        dm = np.bincount(np.searchsorted(uday, (mv + 420) // 1440), weights=sv, minlength=len(uday)) / \
            np.bincount(np.searchsorted(uday, (mv + 420) // 1440), minlength=len(uday))
        say("  T1 spread D10−D1 | %s: %%phút<0=%.3f | %%block<0=%.3f (N_blk=%d) | %%ngày(GMT+7)<0=%.3f (N_ngày=%d)" % (
            wname, float((sv < 0).mean()), float((bmean < 0).mean()), len(ublk),
            float((dm < 0).mean()), len(uday)))
    # T3 block-level
    selT = fv & (((p_valid >> j24) & 1) == 1) & np.isfinite(p_f)
    for wname, wsel in (("DEV", devp), ("ALL", np.ones(len(p_min), bool))):
        s2 = selT & wsel
        lo = s2 & (p_f <= 0); hi = s2 & (p_f > 0)
        blo = (p_min[lo] // BLOCK_MIN); bhi = (p_min[hi] // BLOCK_MIN)
        ub = np.union1d(blo, bhi)
        sa = np.bincount(np.searchsorted(ub, blo), weights=netp[lo], minlength=len(ub))
        na = np.bincount(np.searchsorted(ub, blo), minlength=len(ub))
        sb = np.bincount(np.searchsorted(ub, bhi), weights=netp[hi], minlength=len(ub))
        nb = np.bincount(np.searchsorted(ub, bhi), minlength=len(ub))
        g2 = (na >= 5) & (nb >= 5)
        dblk = sa[g2] / na[g2] - sb[g2] / nb[g2] - FEE
        say("  T3 (≤0−>0) | %s: %%block>0=%.3f (N_blk đủ 2 nhóm=%d) | mean block diff=%s" % (
            wname, float((dblk > 0).mean()), int(g2.sum()), fmt(float(dblk.mean()))))
    say("")
    say("(a/b/c đều DESCRIPTIVE, không dùng để tuyên bố GO/NO-GO.)")
    open(OUT + "/report_extra.txt", "w").write("\n".join(rep) + "\n")
    log.info("wrote report_extra.txt")


if __name__ == "__main__":
    main()
