#!/usr/bin/env python3
"""FUNDING_FACTOR stats — T1/T2 (decile cross-section tai moc funding) + T3 (overlay MOM15).

Doc $FF_OUT/pools.npz. Thuan Python. Pre-reg: docs/PREREG_FUNDING_FACTOR.md (commit 17d600a).
K=3 test khoa o DEV/24h/phi 0,10%: T1 spread(D10-D1) net < 0; T2 net(D1) > 0;
T3 diff(G_lo f_entry<=0  -  G_hi f_entry>0) > 0 (pool P-COIN MOM15).
Cac bang 4h/72h, ALL, grid B (8h-aligned), decile, IC, H3b = DESCRIPTIVE.
"""
import os
import logging
from datetime import datetime, timezone

import numpy as np

OUT = os.environ.get("FF_OUT", "/tmp/funding_factor")
SEED = 20260905
NREP = 2000
NREP_MDE_OUTER = 2000
NREP_MDE_INNER = 200
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
K_TESTS = 3
ALPHA = 0.05
BONF_P = ALPHA / K_TESTS
BONF_PCT = [100 * BONF_P / 2, 100 * (1 - BONF_P / 2)]
MDE_GRID = [0.0002, 0.0005, 0.0010, 0.0020, 0.0025, 0.0050, 0.0100, 0.0200, 0.0400]
MDE_N_GRID = [200, 500, 1000, 5000, 20000, 100000]
MIN_SYM = 50
DEC = 10
FEE_MAIN = 0.0010
UTC = timezone.utc
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/stats.log")])
log = logging.getLogger("ffstats")
rep = []


def say(s=""):
    rep.append(s)
    log.info(s)


def nb(x):
    return f"{int(x):,}".replace(",", " ")


# ---------------------------------------------------------------- stat helpers
class Chain:
    def __init__(self, net, blk):
        self.blk, self.inv = np.unique(blk, return_inverse=True)
        self.nb = len(self.blk)
        self.sums = np.bincount(self.inv, weights=net, minlength=self.nb)
        self.cnts = np.bincount(self.inv, minlength=self.nb)
        self.net = net

    def boot_means(self, nrep=NREP, seed=SEED):
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, self.nb, size=(nrep, self.nb))
        return self.sums[idx].sum(axis=1) / self.cnts[idx].sum(axis=1)


def summ(net, blk, seed=SEED):
    c = Chain(net, blk)
    means = c.boot_means(seed=seed)
    obs = float(net.mean())
    lo, hi = np.percentile(means, [2.5, 97.5])
    half = (hi - lo) / 2.0 * CI_INFLATE
    blo, bhi = np.percentile(means, BONF_PCT)
    return {"n": len(net), "nblk": c.nb, "obs": obs, "lo": float(lo), "hi": float(hi),
            "ci_lo": obs - half, "ci_hi": obs + half, "half": float(half),
            "p_gt0": float((means > 0).mean()), "b_lo": float(blo), "b_hi": float(bhi),
            "means": means}


def group_stats(net, blk, sign, fee=0.0, seed=SEED):
    """sign=+1: kiem dinh mean>0; sign=-1: mean<0. p-value tinh truc tiep tren phan phoi bootstrap."""
    s = summ(net, blk, seed=seed)
    means = s["means"] - fee
    s["p"] = float((means <= 0).mean()) if sign > 0 else float((means >= 0).mean())
    if sign > 0:
        s["pass_x121"] = (s["obs"] - fee) - s["half"] > 0
        s["pass_bonf"] = s["b_lo"] - fee > 0
    else:
        s["pass_x121"] = (s["obs"] - fee) + s["half"] < 0
        s["pass_bonf"] = s["b_hi"] - fee < 0
    return s


def group_stats2(net_a, blk_a, net_b, blk_b, seed=SEED):
    """2 mau: diff = mean_a - mean_b; bootstrap khoi 72h resample CHUNG; null = hoan vi nhan trong block."""
    ba_, ia = np.unique(blk_a, return_inverse=True)
    bb_, ib = np.unique(blk_b, return_inverse=True)
    blocks = np.union1d(ba_, bb_)
    ka = np.searchsorted(blocks, ba_)[ia]
    kb = np.searchsorted(blocks, bb_)[ib]
    nbk = len(blocks)
    sa = np.zeros(nbk); ca = np.zeros(nbk); sb = np.zeros(nbk); cb = np.zeros(nbk)
    np.add.at(sa, ka, net_a); np.add.at(ca, ka, 1.0)
    np.add.at(sb, kb, net_b); np.add.at(cb, kb, 1.0)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nbk, size=(NREP, nbk))
    SA = sa[idx].sum(1); CA = ca[idx].sum(1); SB = sb[idx].sum(1); CB = cb[idx].sum(1)
    good = (CA > 0) & (CB > 0)
    diff = np.full(NREP, np.nan)
    diff[good] = SA[good] / CA[good] - SB[good] / CB[good]
    obs = float(net_a.mean() - net_b.mean())
    lo, hi = np.nanpercentile(diff, [2.5, 97.5])
    half = (hi - lo) / 2.0 * CI_INFLATE
    blo, bhi = np.nanpercentile(diff, BONF_PCT)
    pick = rng.integers(0, 2, size=(NREP, nbk)).astype(bool)
    A = np.where(pick, sb[None, :], sa[None, :]); B = np.where(pick, sa[None, :], sb[None, :])
    CA2 = np.where(pick, cb[None, :], ca[None, :]); CB2 = np.where(pick, ca[None, :], cb[None, :])
    SA2 = A.sum(1); SB2 = B.sum(1); CAs = CA2.sum(1); CBs = CB2.sum(1)
    g2 = (CAs > 0) & (CBs > 0)
    null = np.full(NREP, np.nan)
    null[g2] = SA2[g2] / CAs[g2] - SB2[g2] / CBs[g2]
    return {"n_a": len(net_a), "n_b": len(net_b), "obs": obs, "lo": float(lo), "hi": float(hi),
            "ci_lo": obs - half, "ci_hi": obs + half, "half": float(half),
            "p_gt0": float(np.nanmean(diff > 0)), "b_lo": float(blo), "b_hi": float(bhi),
            "p": float(np.nanmean(null >= obs)), "null_mean": float(np.nanmean(null)),
            "null_sd": float(np.nanstd(null)), "blocks": nbk,
            "pass_x121": (obs - half) > 0, "pass_bonf": float(blo) > 0}


def block_signflip(net, blk, seed=SEED):
    bc, bi = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(NREP, len(bc)))
    bs = np.bincount(bi, weights=net)
    null = (signs @ bs) / len(net)
    return float(net.mean()), float(null.mean()), float(null.std()), float((null >= net.mean()).mean())


def icc(net, gid):
    gid, inv = np.unique(gid, return_inverse=True)
    a = len(gid); ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    cnt = np.bincount(inv, minlength=a).astype(np.float64)
    sums = np.bincount(inv, weights=net, minlength=a)
    mi = sums / cnt
    gm = net.mean()
    msb = (cnt * (mi - gm) ** 2).sum() / (a - 1)
    msw = ((net - mi[inv]) ** 2).sum() / (ni - a)
    k0 = (ni - (cnt ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def mde_of(net, blk, seed=SEED, nouter=NREP_MDE_OUTER, ninner=NREP_MDE_INNER):
    net = net - net.mean()
    c = Chain(net, blk)
    rng = np.random.default_rng(seed)
    hs = np.empty(nouter)
    for r in range(nouter):
        idx = rng.integers(0, c.nb, c.nb)
        IDX = idx[rng.integers(0, c.nb, size=(ninner, c.nb))]
        m = c.sums[IDX].sum(axis=1) / c.cnts[IDX].sum(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs[r] = (hi - lo) / 2.0 * CI_INFLATE
    power = {X: float((hs < X).mean()) for X in MDE_GRID}
    mde80 = next((X for X in MDE_GRID if power[X] >= 0.80), None)
    return {"p50": float(np.percentile(hs, 50)), "p80": float(np.percentile(hs, 80)),
            "p95": float(np.percentile(hs, 95)), "power": power, "mde80": mde80}


def mde_of2(net_a, blk_a, net_b, blk_b, seed=SEED, nouter=NREP_MDE_OUTER, ninner=NREP_MDE_INNER):
    ba, ia = np.unique(blk_a, return_inverse=True)
    bb, ib = np.unique(blk_b, return_inverse=True)
    blocks = np.union1d(ba, bb)
    ka = np.searchsorted(blocks, ba)[ia]; kb = np.searchsorted(blocks, bb)[ib]
    nbk = len(blocks)
    sa = np.zeros(nbk); na = np.zeros(nbk); sb = np.zeros(nbk); nbb = np.zeros(nbk)
    np.add.at(sa, ka, net_a - net_a.mean()); np.add.at(na, ka, 1.0)
    np.add.at(sb, kb, net_b - net_b.mean()); np.add.at(nbb, kb, 1.0)
    rng = np.random.default_rng(seed)
    hs = np.empty(nouter)
    for r in range(nouter):
        idx = rng.integers(0, nbk, nbk)
        IDX = idx[rng.integers(0, nbk, size=(ninner, nbk))]
        SA = sa[IDX].sum(1); NA = na[IDX].sum(1)
        SB = sb[IDX].sum(1); NB = nbb[IDX].sum(1)
        g = (NA > 0) & (NB > 0)
        m = SA[g] / NA[g] - SB[g] / NB[g]
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs[r] = (hi - lo) / 2.0 * CI_INFLATE
    power = {X: float((hs < X).mean()) for X in MDE_GRID}
    mde80 = next((X for X in MDE_GRID if power[X] >= 0.80), None)
    return {"p50": float(np.percentile(hs, 50)), "p80": float(np.percentile(hs, 80)),
            "p95": float(np.percentile(hs, 95)), "power": power, "mde80": mde80}


def fmt_pct(x):
    return "%.4f%%" % (100 * x) if np.isfinite(x) else "nan"


def fmt_ci(s, fee=0.0):
    return "[%s, %s]" % (fmt_pct(s["ci_lo"] - fee), fmt_pct(s["ci_hi"] - fee))


def yearly(minute, val):
    yr = np.array([datetime.utcfromtimestamp(int(x) * 60 + 420 * 60).year for x in minute])
    return [(int(y), int((yr == y).sum()), float(val[yr == y].mean())) for y in sorted(set(yr.tolist()))]


def group_rank(vals, gid_sorted):
    """rank trong tung nhom (theo vals tang dan), gid_sorted = group ordinal cho tung dong (da sort theo nhom)."""
    o = np.lexsort((vals, gid_sorted))
    gg = gid_sorted[o]
    first = np.r_[True, gg[1:] != gg[:-1]]
    gstart = np.flatnonzero(first)
    gord = np.cumsum(first) - 1
    rank = np.arange(len(o)) - gstart[gord]
    out = np.empty(len(vals), dtype=np.float64)
    out[o] = rank
    return out


def main():
    z = np.load(OUT + "/pools.npz")
    holds = [int(x) for x in z["holds"]]
    fee_grid = [float(x) for x in z["fee_grid"]]
    BASE = int(z["base"])
    a_min, a_sym, a_f = z["a_min"], z["a_sym"], z["a_f"].astype(np.float64)
    a_raw, a_slip = z["a_raw"], z["a_slip"].astype(np.float64)
    a_fund, a_valid, a_sd = z["a_fund"], z["a_valid"], z["a_sd"]
    p_min, p_sym, p_f = z["p_min"], z["p_sym"], z["p_f"].astype(np.float64)
    p_raw, p_slip = z["p_raw"], z["p_slip"].astype(np.float64)
    p_fund, p_valid, p_sd = z["p_fund"], z["p_valid"], z["p_sd"]
    m_min, m_sym, m_f = z["m_min"], z["m_sym"], z["m_f"].astype(np.float64)
    m_raw, m_slip = z["m_raw"], z["m_slip"].astype(np.float64)
    m_fund, m_valid, m_sd = z["m_fund"], z["m_valid"], z["m_sd"]
    total_rows = int(z["total_rows"]); n_fire8 = int(z["n_fire8"]); n_sym = int(z["n_sym"])
    j24 = holds.index(1440)
    j4 = holds.index(240)
    j72 = holds.index(4320)
    neta = [a_raw[j].astype(np.float64) - a_slip - a_fund[j].astype(np.float64) for j in range(len(holds))]
    netp = [p_raw[j].astype(np.float64) - p_slip - p_fund[j].astype(np.float64) for j in range(len(holds))]
    net_m = [m_raw[j].astype(np.float64) - m_slip - m_fund[j].astype(np.float64) for j in range(len(holds))]
    deva = (a_min >= DEV_START) & (a_min < DEV_END)
    devp = (p_min >= DEV_START) & (p_min < DEV_END)
    devm = (m_min >= DEV_START) & (m_min < DEV_END)

    say("=== FUNDING_FACTOR — funding như factor cross-section + thành phần chi phí (long-only perp) ===")
    say("Pre-reg `docs/PREREG_FUNDING_FACTOR.md` (commit **17d600a**, chốt TRƯỚC khi chạy). Harness nguyên:")
    say("HOLD {4h,24h,72h} × phí {0.05,0.10,0.15}%, slip 0.5×range + funding Aerospike (cộng event trong")
    say("(m_e, m_x]); CI block-72h 2000 rep seed 20260905 ×1.21; null block sign-flip / block-swap;")
    say("DEV = 2022-01-01..2025-12-31 (CHÍNH), ALL = 2021-01..2025-12 (PHỤ). K=3 test khoá (Bonferroni 0,0167).")
    say("`net = raw − phí exchange − slip − f_cum`; `f_entry` = rate event cuối ≤ m_e (predictor, KHÔNG nằm trong `f_cum`).")

    # ---------------- 0. tai tao ----------------
    say("")
    say("## 0. Kiểm chứng tái tạo (PHẢI khớp, nếu không ⇒ VOID)")
    say("")
    say("| Kiểm chứng | Vòng này | Tham chiếu đã công bố | Khớp |")
    say("|---|---|---|---|")
    checks = [
        ("total_rows cross-section d15", total_rows, 619073711),
        ("Phút MOM15 (rd15 < −0,028, cnt ≥ 50)", n_fire8, 13150),
        ("M-LEVEL MOM15 k=1 (ALL)", int(len(m_min)), 11367),
        ("M-LEVEL MOM15 k=1 (DEV)", int(devm.sum()), 7128),
        ("symbol raw", n_sym, 627),
    ]
    for name, got, want in checks:
        say("| %s | **%s** | %s | %s |" % (name, nb(got), nb(want), "✔" if got == want else "**LỆCH**"))
    say("")
    say("| MOM15 (M-LEVEL k=1, DEV, 24h) | net | CI72h×1.21 | N | N_blk |")
    say("|---|---|---|---|---|")
    for fee in fee_grid:
        sel = devm & (((m_valid >> j24) & 1) == 1) & np.isfinite(net_m[j24])
        s = summ(net_m[j24][sel], (m_min[sel] // BLOCK_MIN).astype(np.int64))
        tag = " ← số neo (kỳ vọng +1,5931%)" if abs(fee - FEE_MAIN) < 1e-12 else ""
        say("| phí %.2f%% | **%s** | %s | %d | %d |%s" % (100 * fee, fmt_pct(s["obs"] - fee), fmt_ci(s, fee),
                                                          s["n"], s["nblk"], tag))

    # ---------------- grid A decile ----------------
    say("")
    say("## 1. Grid A — decile cross-section tại mốc funding (mẫu = (symbol, event funding của chính nó))")
    say("")
    order = np.lexsort((a_f, a_min))
    smin = a_min[order]
    first = np.r_[True, smin[1:] != smin[:-1]]
    gstart = np.flatnonzero(first)
    gord = np.cumsum(first) - 1
    gsize = np.bincount(gord)
    rank = np.arange(len(order)) - gstart[gord]
    dec_order = np.minimum(rank * DEC // np.maximum(gsize[gord], 1), DEC - 1)
    umin = smin[first]
    nmin_uniq = len(umin)
    vmin = gsize >= MIN_SYM
    dec_r = np.empty(len(a_min), dtype=np.int8); dec_r[order] = dec_order
    gid_r = np.empty(len(a_min), dtype=np.int64); gid_r[order] = gord
    n_fund_minutes = int(vmin.sum())
    say("- Mẫu grid A: **N = %s**; phút funding duy nhất: **%d**; phút đủ ≥%d symbol: **%d**."
        % (nb(len(a_min)), nmin_uniq, MIN_SYM, n_fund_minutes))
    nf = np.isfinite(a_f)
    say("- `f_entry`: %s hữu hạn; mean=%.6f (%.4f%%/kỳ) median=%.6f; %%>0 = **%.1f%%**."
        % (nb(nf.sum()), a_f[nf].mean(), 100 * a_f[nf].mean(), np.median(a_f[nf]), 100 * (a_f[nf] > 0).mean()))
    say("- Số symbol/phút (median) = %d; số symbol raw = %d." % (int(np.median(gsize[vmin])), n_sym))

    # ---------------- 1.1 bang decile ----------------
    say("")
    say("### 1.1 Bảng decile (DESCRIPTIVE) — mean theo dòng; DEV; net CHƯA trừ phí")
    for j, hd in enumerate(holds):
        sel = deva
        say("")
        say("**HOLD = %dh** (N=%s dòng DEV) — spread D10−D1 = (raw) − (slip) − (f_cum)" % (hd // 60, nb(sel.sum())))
        say("")
        say("| decile | N | f_entry mean (%) | raw | slip | f_cum | net | net @0,10% |")
        say("|---|---|---|---|---|---|---|---|")
        row = {}
        for dd in range(DEC):
            m_ = sel & (dec_r == dd)
            if m_.sum() < 5:
                continue
            row[dd] = (float(np.nanmean(a_raw[j][m_])), float(np.nanmean(a_slip[m_])),
                       float(np.nanmean(a_fund[j][m_])), float(np.nanmean(neta[j][m_])),
                       float(np.nanmean(a_f[m_])))
            say("| D%d | %s | %.5f | %s | %s | %s | **%s** | %s |" % (
                dd + 1, nb(m_.sum()), 100 * row[dd][4], fmt_pct(row[dd][0]), fmt_pct(row[dd][1]),
                fmt_pct(row[dd][2]), fmt_pct(row[dd][3]), fmt_pct(row[dd][3] - FEE_MAIN)))
        if 9 in row and 0 in row:
            say("")
            say("  **spread D10−D1**: raw %s | slip %s | f_cum %s | **net %s** (@0,10%%: %s)" % (
                fmt_pct(row[9][0] - row[0][0]), fmt_pct(row[9][1] - row[0][1]),
                fmt_pct(row[9][2] - row[0][2]), fmt_pct(row[9][3] - row[0][3]),
                fmt_pct(row[9][3] - row[0][3])))
        rr = np.corrcoef(np.argsort(np.argsort(a_f[nf & sel])), np.argsort(np.argsort(neta[j][nf & sel])))[0, 1]
        rc_ = np.corrcoef(np.argsort(np.argsort(a_f[nf & sel])), np.argsort(np.argsort(a_fund[j][nf & sel])))[0, 1]
        say("  Spearman(f_entry, net) = %.4f ; Spearman(f_entry, f_cum) = **%.4f** ; mean f_cum toàn bộ = %s" % (
            rr, rc_, fmt_pct(np.nanmean(a_fund[j][sel]))))

    # ---------------- portfolio series ----------------
    def port_series(j, use_gridB=False):
        net = neta[j]
        okrow = (((a_valid >> j) & 1) == 1) & np.isfinite(net)
        if use_gridB:
            mod = a_min % 1440
            okrow &= (mod == 0) | (mod == 480) | (mod == 960)
        keep = okrow & vmin[np.clip(gid_r, 0, nmin_uniq - 1)]
        comp = np.where(keep, gid_r * DEC + dec_r, -1)[keep]
        w = net[keep]
        S = np.bincount(comp, weights=w, minlength=nmin_uniq * DEC).reshape(nmin_uniq, DEC)
        C = np.bincount(comp, minlength=nmin_uniq * DEC).reshape(nmin_uniq, DEC).astype(np.float64)
        with np.errstate(invalid="ignore", divide="ignore"):
            M = np.where(C > 0, S / C, np.nan)
            allm = np.where(C.sum(1) > 0, np.nansum(np.where(C > 0, S, np.nan), axis=1) / np.maximum(C.sum(1), 1), np.nan)
        return M[vmin], allm[vmin], umin[vmin]

    say("")
    say("### 1.2 Chuỗi portfolio theo phút (equal-weight trong decile) — CI / null / K=3")
    say("")
    say("| test | HOLD | phí | N_phút | N_blk | net | CI72h×1.21 | p | Bonf3 lo | Bonf3 hi | x1.21 | Bonf3 |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|")
    res = {}
    for j, hd in enumerate(holds):
        M, allm, mins = port_series(j)
        for tag, series, sign in (("T1 spread D10−D1", M[:, 9] - M[:, 0], -1),
                                  ("T2 long-only D1", M[:, 0], +1)):
            g = np.isfinite(series)
            mm = mins[g]; sv = series[g]
            sd_ = (mm >= DEV_START) & (mm < DEV_END)
            blk = (mm[sd_] // BLOCK_MIN).astype(np.int64)
            s = group_stats(sv[sd_], blk, sign, fee=FEE_MAIN)
            res[(tag, hd)] = (s, sv[sd_], blk, mm[sd_])
            for fee in fee_grid:
                s2 = group_stats(sv[sd_], blk, sign, fee=fee)
                say("| %s | %s | %.2f%% | %d | %d | **%s** | [%s, %s] | %.4f | %s | %s | %s | %s |" % (
                    tag if fee == fee_grid[0] else "", ("%dh" % (hd // 60)) if fee == fee_grid[0] else "",
                    100 * fee, s2["n"], s2["nblk"], fmt_pct(s2["obs"] - fee),
                    fmt_pct(s2["ci_lo"] - fee), fmt_pct(s2["ci_hi"] - fee), s2["p"],
                    fmt_pct(s2["b_lo"] - fee), fmt_pct(s2["b_hi"] - fee),
                    "CÓ" if s2["pass_x121"] else "-", "**CÓ**" if s2["pass_bonf"] else "-"))
    say("")
    say("Null (block sign-flip 72h, 2000 rep) + ICC — HOLD 24h, phí 0,10%:")
    for tag in ("T1 spread D10−D1", "T2 long-only D1"):
        s, sv, blk, mm = res[(tag, 1440)]
        _, nm, nsd, npv = block_signflip(sv - FEE_MAIN, blk)
        say("  %s: p(≥obs)=%.5f | N_phút=%d N_blk=%d | ICC(ngày GMT+7)=%.4f ICC(72h)=%.4f" % (
            tag, npv, s["n"], s["nblk"], icc(sv, (mm + 420) // 1440), icc(sv, blk)))

    # ---------------- T3 ----------------
    say("")
    say("## 2. T3 — tại phút MOM15 fire: funding tại entry có tách được thắng/thua? (pool P-COIN MOM15)")
    fv = np.isfinite(p_f)
    say("")
    say("- P-COIN MOM15: N ALL = %s ; N DEV = %s ; symbol DEV = %d"
        % (nb(len(p_min)), nb(devp.sum()), len(set(p_sym[devp].tolist()))))
    say("- `f_entry` hữu hạn %s (%.1f%%); **%%>0 = %.1f%%** (tại phút MOM15 fire = phút dump)"
        % (nb(fv.sum()), 100 * fv.mean(), 100 * (p_f[fv] > 0).mean()))
    say("")
    say("| HOLD | phí | N(≤0) | N(>0) | net(≤0) | net(>0) | diff | CI72h×1.21 | p | Bonf3 lo | Bonf3 hi | x1.21 | Bonf3 |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    t3 = {}
    for j, hd in enumerate(holds):
        sel = devp & fv & (((p_valid >> j) & 1) == 1)
        lo = sel & (p_f <= 0); hi = sel & (p_f > 0)
        s = group_stats2(netp[j][lo], (p_min[lo] // BLOCK_MIN).astype(np.int64),
                         netp[j][hi], (p_min[hi] // BLOCK_MIN).astype(np.int64))
        t3[hd] = s
        for fee in fee_grid:
            say("| %s | %.2f%% | %d | %d | %s | %s | **%s** | [%s, %s] | %.4f | %s | %s | %s | %s |" % (
                ("%dh" % (hd // 60)) if fee == fee_grid[0] else "", 100 * fee, s["n_a"], s["n_b"],
                fmt_pct(netp[j][lo].mean() - fee), fmt_pct(netp[j][hi].mean() - fee),
                fmt_pct(s["obs"] - fee), fmt_pct(s["ci_lo"] - fee), fmt_pct(s["ci_hi"] - fee), s["p"],
                fmt_pct(s["b_lo"] - fee), fmt_pct(s["b_hi"] - fee),
                "CÓ" if s["ci_lo"] - fee > 0 else "-", "**CÓ**" if s["b_lo"] - fee > 0 else "-"))
    s3 = t3[1440]
    say("")
    say("  null (block swap 72h) T3 @24h: null mean=%s sd=%s ⇒ p(≥obs)=%.4f ; N_blk=%d" % (
        fmt_pct(s3["null_mean"]), fmt_pct(s3["null_sd"]), s3["p"], s3["blocks"]))

    # ---------------- H3b ----------------
    say("")
    say("### 2b. H3b (DESCRIPTIVE, THIẾU LỰC) — M-LEVEL MOM15 k=1 (đúng live)")
    selm = devm & (((m_valid >> j24) & 1) == 1) & np.isfinite(net_m[j24])
    selmf = selm & np.isfinite(m_f)
    lo = selmf & (m_f <= 0); hi = selmf & (m_f > 0)
    s = group_stats2(net_m[j24][lo], (m_min[lo] // BLOCK_MIN).astype(np.int64),
                     net_m[j24][hi], (m_min[hi] // BLOCK_MIN).astype(np.int64))
    sall = summ(net_m[j24][selm], (m_min[selm] // BLOCK_MIN).astype(np.int64))
    keeplo = selmf & (m_f <= 0)
    sk = summ(net_m[j24][keeplo], (m_min[keeplo] // BLOCK_MIN).astype(np.int64))
    say("")
    say("| subset | N | N_blk | meanNet @0,10% | CI72h×1.21 |")
    say("|---|---|---|---|---|")
    for nm_, m_ in (("f_entry ≤ 0", lo), ("f_entry > 0", hi)):
        ss = summ(net_m[j24][m_], (m_min[m_] // BLOCK_MIN).astype(np.int64))
        say("| %s | %d | %d | **%s** | %s |" % (nm_, ss["n"], ss["nblk"], fmt_pct(ss["obs"] - FEE_MAIN),
                                               fmt_ci(ss, FEE_MAIN)))
    say("| MOM15 gốc (mọi f_entry) | %d | %d | **%s** | %s |" % (sall["n"], sall["nblk"],
                                                                 fmt_pct(sall["obs"] - FEE_MAIN), fmt_ci(sall, FEE_MAIN)))
    say("| MOM15 sau LỌC BỎ f_entry>0 | %d | %d | **%s** | %s |" % (sk["n"], sk["nblk"],
                                                                   fmt_pct(sk["obs"] - FEE_MAIN), fmt_ci(sk, FEE_MAIN)))
    say("| diff (≤0 − >0) | %d/%d | %d | %s | [%s, %s] p=%.4f |" % (
        s["n_a"], s["n_b"], s["blocks"], fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"]), s["p"]))
    say("")
    mdeb = mde_of(net_m[j24][selm], (m_min[selm] // BLOCK_MIN).astype(np.int64))
    say("  MDE(80%%) MOM15 k=1 DEV: h_r p80=%s ⇒ **MDE=%s** ⇒ H3b KHÔNG đủ lực cho hiệu ứng ≲2%%/lệnh"
        % (fmt_pct(mdeb["p80"]), ("%.2f%%" % (100 * mdeb["mde80"])) if mdeb["mde80"] else ">4%"))

    # ---------------- IC ----------------
    say("")
    say("## 3. IC cross-section (DESCRIPTIVE) — Spearman(f_entry, net) TỪNG PHÚT, HOLD 24h")
    okrow = (((a_valid >> j24) & 1) == 1) & np.isfinite(neta[j24]) & np.isfinite(a_f)
    keep = np.flatnonzero(okrow & vmin[np.clip(gid_r, 0, nmin_uniq - 1)])
    gk = gid_r[keep]
    o_ = np.argsort(gk, kind="stable")
    gid_sorted = gk[o_]
    rf = group_rank(a_f[keep][o_], gid_sorted)
    rn = group_rank(neta[j24][keep][o_], gid_sorted)
    ic_min = []
    gg = gid_sorted
    firsts = np.r_[0, np.flatnonzero(gg[1:] != gg[:-1]) + 1]
    ends = np.r_[firsts[1:], len(gg)]
    for a0, b0 in zip(firsts, ends):
        if b0 - a0 < MIN_SYM:
            continue
        a = rf[a0:b0] - rf[a0:b0].mean(); b = rn[a0:b0] - rn[a0:b0].mean()
        den = np.sqrt((a * a).sum() * (b * b).sum())
        if den > 0:
            ic_min.append((umin[gg[a0]], (a * b).sum() / den))
    icm = np.array([x[1] for x in ic_min]); icmm = np.array([x[0] for x in ic_min])
    devic = (icmm >= DEV_START) & (icmm < DEV_END)
    sic = summ(icm[devic], (icmm[devic] // BLOCK_MIN).astype(np.int64))
    say("")
    say("- DEV: mean IC = **%.4f**, CI72h×1.21 [%.4f, %.4f], p(>0)=%.4f (N_phút=%d, N_blk=%d)" % (
        sic["obs"], sic["ci_lo"], sic["ci_hi"], sic["p_gt0"], sic["n"], sic["nblk"]))
    say("- ALL: mean IC = %.4f (N_phút=%d); phân vị IC DEV: p10=%.4f p50=%.4f p90=%.4f" % (
        icm.mean(), len(icm), np.percentile(icm[devic], 10), np.percentile(icm[devic], 50),
        np.percentile(icm[devic], 90)))

    # ---------------- MDE ----------------
    say("")
    say("## 4. MDE (80%) cho 3 test chính — DEV, HOLD 24h")
    say("")
    say("| test | N | N_blk | h_r p50 | h_r p80 | h_r p95 | power@0,1% | @0,5% | @1% | @2% | MDE(80%) |")
    say("|---|---|---|---|---|---|---|---|---|---|---|")
    mde_res = {}
    for tag in ("T1 spread D10−D1", "T2 long-only D1"):
        s, sv, blk, mm = res[(tag, 1440)]
        r = mde_of(sv, blk)
        mde_res[tag] = r
        say("| %s | %d | %d | %s | %s | %s | %.2f | %.2f | %.2f | %.2f | **%s** |" % (
            tag, s["n"], s["nblk"], fmt_pct(r["p50"]), fmt_pct(r["p80"]), fmt_pct(r["p95"]),
            r["power"][0.001], r["power"][0.005], r["power"][0.010], r["power"][0.020],
            ("%.2f%%" % (100 * r["mde80"])) if r["mde80"] else ">4%"))
    sel = devp & fv & (((p_valid >> j24) & 1) == 1)
    lo = sel & (p_f <= 0); hi = sel & (p_f > 0)
    r3 = mde_of2(netp[j24][lo], (p_min[lo] // BLOCK_MIN).astype(np.int64),
                 netp[j24][hi], (p_min[hi] // BLOCK_MIN).astype(np.int64))
    mde_res["T3"] = r3
    say("| T3 diff (≤0 − >0) | %d/%d | %d | %s | %s | %s | %.2f | %.2f | %.2f | %.2f | **%s** |" % (
        int(lo.sum()), int(hi.sum()), s3["blocks"], fmt_pct(r3["p50"]), fmt_pct(r3["p80"]), fmt_pct(r3["p95"]),
        r3["power"][0.001], r3["power"][0.005], r3["power"][0.010], r3["power"][0.020],
        ("%.2f%%" % (100 * r3["mde80"])) if r3["mde80"] else ">4%"))
    say("")
    say("### 4b. Đường MDE theo N (mẫu con không lặp, 200 rep/N, DEV, chuỗi T1/T2 24h)")
    say("")
    say("| test | " + " | ".join("N=%d" % n for n in MDE_N_GRID) + " |")
    say("|---|" + "---|" * len(MDE_N_GRID))
    for tag in ("T1 spread D10−D1", "T2 long-only D1"):
        _, sv, blk, _ = res[(tag, 1440)]
        cells = []
        for n in MDE_N_GRID:
            if n > len(sv):
                cells.append("n/a"); continue
            rng = np.random.default_rng(SEED)
            hs = []
            for r in range(200):
                idx = rng.choice(len(sv), size=n, replace=False)
                c = Chain(sv[idx] - sv[idx].mean(), blk[idx])
                m = c.boot_means(nrep=200, seed=SEED + r)
                lo_, hi_ = np.percentile(m, [2.5, 97.5])
                hs.append((hi_ - lo_) / 2 * CI_INFLATE)
            hp80 = float(np.percentile(hs, 80))
            mde = next((X for X in MDE_GRID if hp80 <= X), None)
            cells.append("h80=%.4f%%→%s" % (100 * hp80, ("%.2f%%" % (100 * mde)) if mde else ">4%"))
        say("| %s | " % tag + " | ".join(cells) + " |")

    # ---------------- theo nam + %coin+ ----------------
    say("")
    say("## 5. Theo năm (GMT+7) + %coin+ (DESCRIPTIVE)")
    M24, all24, mins24 = port_series(j24)
    for tag, series in (("T1 spread D10−D1", M24[:, 9] - M24[:, 0]), ("T2 long-only D1", M24[:, 0]),
                        ("universe (mọi decile)", all24)):
        g = np.isfinite(series)
        say("")
        say("**%s** — mỗi năm:" % tag)
        say("  " + " | ".join("Y%d: %d phút, %s" % (y, n_, fmt_pct(v - FEE_MAIN))
                              for y, n_, v in yearly(mins24[g], series[g])))
    selp = devp & fv & (((p_valid >> j24) & 1) == 1)
    for nm_, m_ in (("G_lo (f_entry ≤ 0)", selp & (p_f <= 0)), ("G_hi (f_entry > 0)", selp & (p_f > 0))):
        say("")
        say("**T3 pool %s** (N=%d, N_blk=%d): meanNet=%s" % (
            nm_, int(m_.sum()), len(np.unique(p_min[m_] // BLOCK_MIN)), fmt_pct(netp[j24][m_].mean() - FEE_MAIN)))
        say("  " + " | ".join("Y%d: %d mẫu, %s" % (y, n_, fmt_pct(v - FEE_MAIN))
                              for y, n_, v in yearly(p_min[m_], netp[j24][m_])))
        for mt in (1, 5, 10):
            us, inv = np.unique(p_sym[m_], return_inverse=True)
            cnt = np.bincount(inv)
            cm = np.bincount(inv, weights=netp[j24][m_]) / cnt
            okk = cnt >= mt
            if okk.any():
                say("  %%coin+ (≥%d trade): nsym=%d **%.1f%%**" % (mt, int(okk.sum()),
                                                                  100 * (cm[okk] - FEE_MAIN > 0).mean()))
    for dd in (0, 9):
        m_ = deva & (dec_r == dd) & (((a_valid >> j24) & 1) == 1) & np.isfinite(neta[j24])
        us, inv = np.unique(a_sym[m_], return_inverse=True)
        cnt = np.bincount(inv); cm = np.bincount(inv, weights=neta[j24][m_]) / cnt
        say("")
        say("**Grid A D%d** (N=%d, nsym=%d): meanNet@0,10%%=%s" % (dd + 1, int(m_.sum()), len(us),
                                                                 fmt_pct(neta[j24][m_].mean() - FEE_MAIN)))
        for mt in (1, 5, 10):
            okk = cnt >= mt
            if okk.any():
                say("  %%coin+ (≥%d trade): nsym=%d %.1f%%" % (mt, int(okk.sum()), 100 * (cm[okk] - FEE_MAIN > 0).mean()))
        say("  " + " | ".join("Y%d: %d mẫu, %s" % (y, n_, fmt_pct(v - FEE_MAIN))
                              for y, n_, v in yearly(a_min[m_], neta[j24][m_])))

    # ---------------- robustness ----------------
    say("")
    say("## 6. Robustness (DESCRIPTIVE): grid B (chỉ mốc 8h-aligned 00/08/16 UTC) + ALL — HOLD 24h, phí 0,10%")
    for useB in (True, False):
        M, allm, mins = port_series(j24, use_gridB=useB)
        for tag, series, sign in (("T1 spread D10−D1", M[:, 9] - M[:, 0], -1),
                                  ("T2 long-only D1", M[:, 0], +1)):
            g = np.isfinite(series)
            mm = mins[g]; sv = series[g]
            for wname, wsel in (("DEV", (mm >= DEV_START) & (mm < DEV_END)), ("ALL", np.ones(len(mm), bool))):
                if wsel.sum() < 5:
                    continue
                blk = (mm[wsel] // BLOCK_MIN).astype(np.int64)
                s = group_stats(sv[wsel], blk, sign, fee=FEE_MAIN)
                say("- %s | %s | %s: N_phút=%d N_blk=%d net=%s CI72h×1.21=[%s, %s] p=%.4f (x1.21 %s)" % (
                    "grid B (8h-aligned)" if useB else "grid A (mọi cadence)", tag, wname, s["n"], s["nblk"],
                    fmt_pct(s["obs"] - FEE_MAIN), fmt_pct(s["ci_lo"] - FEE_MAIN), fmt_pct(s["ci_hi"] - FEE_MAIN),
                    s["p"], "CÓ" if s["pass_x121"] else "-"))
    selA = fv & (((p_valid >> j24) & 1) == 1)
    loA = selA & (p_f <= 0); hiA = selA & (p_f > 0)
    sA = group_stats2(netp[j24][loA], (p_min[loA] // BLOCK_MIN).astype(np.int64),
                      netp[j24][hiA], (p_min[hiA] // BLOCK_MIN).astype(np.int64))
    say("- T3 | ALL: N=%d/%d diff=%s CI72h×1.21=[%s, %s] p=%.4f (x1.21 %s)" % (
        sA["n_a"], sA["n_b"], fmt_pct(sA["obs"]), fmt_pct(sA["ci_lo"]), fmt_pct(sA["ci_hi"]),
        sA["p"], "CÓ" if sA["pass_x121"] else "-"))
    say("- T1/T2 ALL: xem dòng ALL trong bảng trên (loop useB=False).")

    # ---------------- ket luan ----------------
    say("")
    say("## 7. Bảng quyết định (cổng §6 PREREG: x1.21 ∧ Bonf3 ∧ |effect| ≥ MDE ∧ dấu 4h/72h ∧ ≥60% phút đúng dấu)")
    say("")
    say("| test | HOLD | phí | net | CI72h×1.21 | p | x1.21 | Bonf3 | MDE | 4h / 72h | %phút đúng dấu | ⇒ |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|")
    verdict = {}
    for tag, sign in (("T1 spread D10−D1", -1), ("T2 long-only D1", +1)):
        s, sv, blk, mm = res[(tag, 1440)]
        r = mde_res[tag]
        mde = r["mde80"]
        signfrac = float((sv - FEE_MAIN < 0).mean()) if sign < 0 else float((sv - FEE_MAIN > 0).mean())
        signs = []
        for hd2 in (240, 4320):
            M2, _, mins2 = port_series(holds.index(hd2))
            ser2 = (M2[:, 9] - M2[:, 0]) if tag.startswith("T1") else M2[:, 0]
            g = np.isfinite(ser2); m2 = mins2[g]
            w = (m2 >= DEV_START) & (m2 < DEV_END)
            signs.append(float(ser2[g][w].mean() - FEE_MAIN))
        go = s["pass_x121"] and s["pass_bonf"] and (mde is not None and abs(s["obs"] - FEE_MAIN) >= mde) \
            and signfrac >= 0.60 and all((x < 0) if sign < 0 else (x > 0) for x in signs)
        verdict[tag] = go
        say("| %s | 24h | 0,10%% | %s | [%s, %s] | %.4f | %s | %s | %s | %s / %s | %.3f | %s |" % (
            tag, fmt_pct(s["obs"] - FEE_MAIN), fmt_pct(s["ci_lo"] - FEE_MAIN), fmt_pct(s["ci_hi"] - FEE_MAIN),
            s["p"], "CÓ" if s["pass_x121"] else "-", "**CÓ**" if s["pass_bonf"] else "-",
            ("%.2f%%" % (100 * mde)) if mde else ">4%", fmt_pct(signs[0]), fmt_pct(signs[1]), signfrac,
            "**GO**" if go else "**NO-GO**"))
    signs3 = []
    for hd2 in (240, 4320):
        jj = holds.index(hd2)
        sel2 = devp & fv & (((p_valid >> jj) & 1) == 1)
        signs3.append(float(netp[jj][sel2 & (p_f <= 0)].mean() - netp[jj][sel2 & (p_f > 0)].mean()))
    mde3 = mde_res["T3"]["mde80"]
    go3 = s3["pass_x121"] and s3["pass_bonf"] and (mde3 is not None and s3["obs"] >= mde3) \
        and all(x > 0 for x in signs3)
    verdict["T3"] = go3
    say("| T3 diff (≤0 − >0) | 24h | 0,10%% | %s | [%s, %s] | %.4f | %s | %s | %s | %s / %s | — | %s |" % (
        fmt_pct(s3["obs"]), fmt_pct(s3["ci_lo"]), fmt_pct(s3["ci_hi"]), s3["p"],
        "CÓ" if s3["pass_x121"] else "-", "**CÓ**" if s3["pass_bonf"] else "-",
        ("%.2f%%" % (100 * mde3)) if mde3 else ">4%", fmt_pct(signs3[0]), fmt_pct(signs3[1]),
        "**GO**" if go3 else "**NO-GO**"))
    say("")
    say("Kết luận tự động: **T1 %s | T2 %s | T3 %s**" % (
        "GO" if verdict["T1 spread D10−D1"] else "NO-GO",
        "GO" if verdict["T2 long-only D1"] else "NO-GO", "GO" if verdict["T3"] else "NO-GO"))
    say("")
    say("Bảng thô để viết kết luận — giá trị chính @24h/0,10%% DEV:")
    say("  T1: obs=%s CI=[%s, %s] p=%.4f | Bonf3 [%s, %s] | MDE=%s | %%phút<0=%.3f" % (
        fmt_pct(res[("T1 spread D10−D1", 1440)][0]["obs"] - FEE_MAIN),
        fmt_pct(res[("T1 spread D10−D1", 1440)][0]["ci_lo"] - FEE_MAIN),
        fmt_pct(res[("T1 spread D10−D1", 1440)][0]["ci_hi"] - FEE_MAIN),
        res[("T1 spread D10−D1", 1440)][0]["p"],
        fmt_pct(res[("T1 spread D10−D1", 1440)][0]["b_lo"] - FEE_MAIN),
        fmt_pct(res[("T1 spread D10−D1", 1440)][0]["b_hi"] - FEE_MAIN),
        ("%.2f%%" % (100 * mde_res["T1 spread D10−D1"]["mde80"])) if mde_res["T1 spread D10−D1"]["mde80"] else ">4%",
        float((res[("T1 spread D10−D1", 1440)][1] - FEE_MAIN < 0).mean())))
    say("  T2: obs=%s CI=[%s, %s] p=%.4f | Bonf3 [%s, %s] | MDE=%s" % (
        fmt_pct(res[("T2 long-only D1", 1440)][0]["obs"] - FEE_MAIN),
        fmt_pct(res[("T2 long-only D1", 1440)][0]["ci_lo"] - FEE_MAIN),
        fmt_pct(res[("T2 long-only D1", 1440)][0]["ci_hi"] - FEE_MAIN),
        res[("T2 long-only D1", 1440)][0]["p"],
        fmt_pct(res[("T2 long-only D1", 1440)][0]["b_lo"] - FEE_MAIN),
        fmt_pct(res[("T2 long-only D1", 1440)][0]["b_hi"] - FEE_MAIN),
        ("%.2f%%" % (100 * mde_res["T2 long-only D1"]["mde80"])) if mde_res["T2 long-only D1"]["mde80"] else ">4%"))
    say("  T3: obs=%s CI=[%s, %s] p=%.4f | Bonf3 [%s, %s] | MDE=%s" % (
        fmt_pct(s3["obs"]), fmt_pct(s3["ci_lo"]), fmt_pct(s3["ci_hi"]), s3["p"],
        fmt_pct(s3["b_lo"]), fmt_pct(s3["b_hi"]),
        ("%.2f%%" % (100 * mde3)) if mde3 else ">4%"))

    txt = "\n".join(rep)
    open(OUT + "/report.txt", "w").write(txt + "\n")
    log.info("wrote %s/report.txt", OUT)
    return verdict


if __name__ == "__main__":
    main()
