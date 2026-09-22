#!/usr/bin/env python3
"""FUNDING_TOPK_ROTATE stats — luat quay vong 8h LONG top-K funding nho nhat.

Pre-reg: docs/PREREG_FUNDING_TOPK_ROTATE.md (commit 55b8280, chot TRUOC khi chay; KHONG sua thiet ke).

Doc $TKR_OUT/mark_grid.npz (grid moc 8h) + $TKR_OUT/anchor_mom15.npz (neo MOM15).
Moi chu ky = 1 moc 8h: basket = K symbol co f_entry nho nhat (tang dan, dong hang theo sym index),
long equal-weight, HOLD 480', cost = fee_rt/2 + slip 0.5xrange MOI CHIEU tren phan book quay vong
(n_in/K + n_out/K) + funding thuc tra f_cum (r, r+480].
CI block-72h x1.21 2000 rep seed 20260905; Bonferroni K_test=3; null K coin ngau nhien >=200 rep;
MDE luoi rieng khung 8h; DEV 2022-2025 chinh, ALL 2021-2025 phu.
"""
import os
import logging
from datetime import datetime, timezone

import numpy as np

OUT = os.environ.get("TKR_OUT", "/tmp/funding_topk")
SEED = 20260905
NREP = 2000
NREP_MDE_OUTER = 2000
NREP_MDE_INNER = 200
NULL_REPS = 300
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
K_TESTS = 3
ALPHA = 0.05
BONF_P = ALPHA / K_TESTS
BONF_PCT = [100 * BONF_P / 2, 100 * (1 - BONF_P / 2)]
MDE_GRID = [0.0001, 0.0002, 0.0005, 0.0010, 0.0020, 0.0050]   # %/chu ky (khung 8h)
K_LIST = (5, 10, 20)
FEE_GRID = (0.0005, 0.0010, 0.0015)
FEE_MAIN = 0.0010
SLIP_HALF = 0.5
MIN_SYM_MAIN = 50
MIN_SYM_ALT = 100
UTC = timezone.utc
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
YEAR_B = [(y, int(datetime(y, 1, 1, tzinfo=UTC).timestamp() // 60) - 420) for y in range(2021, 2027)]

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/stats.log")])
log = logging.getLogger("tkrstats")
rep = []


def say(s=""):
    rep.append(s)
    log.info(s)


def nb(x):
    return f"{int(x):,}".replace(",", " ")


def fmt_pct(x, nd=4):
    return ("%." + str(nd) + "f%%") % (100 * x) if np.isfinite(x) else "nan"


def signif(x, nd=4):
    return "%.4f" % x if np.isfinite(x) else "nan"


# ---------------------------------------------------------------- stat helpers
def block_ids(mark, base):
    return ((base + mark) // BLOCK_MIN).astype(np.int64)


def summ(net, blk, seed=SEED):
    b = np.unique(blk, return_inverse=True)[1]
    nbk = b.max() + 1
    sums = np.bincount(b, weights=net, minlength=nbk)
    cnts = np.bincount(b, minlength=nbk)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nbk, size=(NREP, nbk))
    means = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    obs = float(net.mean())
    lo, hi = np.percentile(means, [2.5, 97.5])
    half = (hi - lo) / 2.0 * CI_INFLATE
    blo, bhi = np.percentile(means, BONF_PCT)
    return {"n": len(net), "nblk": int(nbk), "obs": obs, "half": float(half),
            "ci_lo": obs - half, "ci_hi": obs + half, "p_gt0": float((means > 0).mean()),
            "b_lo": float(blo), "b_hi": float(bhi), "means": means}


def mde_of(net, blk, seed=SEED, nouter=NREP_MDE_OUTER, ninner=NREP_MDE_INNER):
    net = net - net.mean()
    b = np.unique(blk, return_inverse=True)[1]
    nbk = b.max() + 1
    sums = np.bincount(b, weights=net, minlength=nbk)
    cnts = np.bincount(b, minlength=nbk)
    rng = np.random.default_rng(seed)
    hs = np.empty(nouter)
    for r in range(nouter):
        idx = rng.integers(0, nbk, nbk)
        IDX = idx[rng.integers(0, nbk, size=(ninner, nbk))]
        m = sums[IDX].sum(axis=1) / cnts[IDX].sum(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs[r] = (hi - lo) / 2.0 * CI_INFLATE
    power = {X: float((hs < X).mean()) for X in MDE_GRID}
    mde80 = next((X for X in MDE_GRID if power[X] >= 0.80), None)
    return {"p50": float(np.percentile(hs, 50)), "p80": float(np.percentile(hs, 80)),
            "p95": float(np.percentile(hs, 95)), "mde80": mde80}


def icc(net, gid):
    g, inv = np.unique(gid, return_inverse=True)
    a = len(g)
    ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    cnt = np.bincount(inv, minlength=a).astype(np.float64)
    mi = np.bincount(inv, weights=net, minlength=a) / cnt
    gm = net.mean()
    msb = (cnt * (mi - gm) ** 2).sum() / (a - 1)
    msw = ((net - mi[inv]) ** 2).sum() / (ni - a)
    k0 = (ni - (cnt ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def year_idx(mark, base):
    adj = base + mark + 420
    bnd = np.array([b for _, b in YEAR_B], dtype=np.int64)
    return np.searchsorted(bnd, adj, side="right") - 1


# ---------------------------------------------------------------- cost model
def turnover_cost(sel_slots, sel_sym, SLIP, K, fee_rt):
    """(n,) cost tung chu ky: (n_in/K)*(fee_side+slip_in) + (n_out/K)*(fee_side+slip_out)."""
    n = sel_slots.shape[0]
    prev_sym = np.empty_like(sel_sym)
    prev_sym[0] = -1
    prev_sym[1:] = sel_sym[:-1]
    prev_slots = np.empty_like(sel_slots)
    prev_slots[0] = sel_slots[0]
    prev_slots[1:] = sel_slots[:-1]
    carried_new = (sel_sym[:, :, None] == prev_sym[:, None, :]).any(axis=2)     # (n,K)
    carried_prev = (prev_sym[:, :, None] == sel_sym[:, None, :]).any(axis=2)    # (n,K)
    n_in = K - carried_new.sum(axis=1)
    n_out = K - carried_prev.sum(axis=1)
    n_in[0] = K
    n_out[0] = 0
    slip_new = SLIP[sel_slots]
    slip_prev = SLIP[prev_slots]
    slip_in = (slip_new * (~carried_new)).sum(axis=1) / np.maximum(n_in, 1)
    slip_out = (slip_prev * (~carried_prev)).sum(axis=1) / np.maximum(n_out, 1)
    fee_side = fee_rt / 2.0
    cost = (n_in / K) * (fee_side + slip_in) + (n_out / K) * (fee_side + slip_out)
    return cost, n_in, n_out


# ---------------------------------------------------------------- prepare grid
def prepare(rows_mask=None):
    z = np.load(OUT + "/mark_grid.npz")
    base = int(z["base"])
    g_mark, g_sym = z["g_mark"], z["g_sym"]
    g_f, g_raw, g_slip, g_fund, g_sd = z["g_f"], z["g_raw"], z["g_slip"], z["g_fund"], z["g_sd"]
    cadence = z["cadence"]
    if rows_mask is not None:
        g_mark, g_sym = g_mark[rows_mask], g_sym[rows_mask]
        g_f, g_raw, g_slip, g_fund, g_sd = g_f[rows_mask], g_raw[rows_mask], g_slip[rows_mask], g_fund[rows_mask], g_sd[rows_mask]
    o = np.lexsort((g_sym, g_f, g_mark))     # primary mark, then f_entry asc (NaN last), then sym
    mk = g_mark[o]
    F = g_f[o].astype(np.float64)
    fin = np.isfinite(F)
    uniq, starts = np.unique(mk, return_index=True)
    ends = np.r_[starts[1:], len(mk)]
    E = np.r_[0, np.cumsum(fin.astype(np.int64))]
    cnt_elig = E[ends] - E[starts]
    V = {k: v[o].astype(np.float64) for k, v in (("raw", g_raw), ("fund", g_fund), ("slip", g_slip))}
    return {"base": base, "mark": uniq, "starts": starts, "ends": ends, "cnt": cnt_elig,
            "sym": g_sym[o], "F": F, "slip": g_slip[o].astype(np.float64),
            "sd": g_sd[o], "V": V, "cadence": cadence, "n_all": len(mk)}


def exec_marks(prep, min_sym):
    return np.flatnonzero(prep["cnt"] >= min_sym)


def basket_series(prep, ex, K):
    st = prep["starts"][ex]
    sel_slots = st[:, None] + np.arange(K)[None, :]
    sel_sym = prep["sym"][sel_slots]
    out = {}
    for k in ("raw", "fund", "slip"):
        flat = prep["V"][k][sel_slots]
        out[k + "_mean"] = flat.mean(axis=1)
    out["sel_slots"] = sel_slots
    out["sel_sym"] = sel_sym
    out["f_mean"] = prep["F"][sel_slots].mean(axis=1)
    out["f_med"] = np.median(prep["F"][sel_slots], axis=1)
    out["f_min"] = prep["F"][sel_slots].min(axis=1)
    out["f_max"] = prep["F"][sel_slots].max(axis=1)
    out["f_le0"] = (prep["F"][sel_slots] <= 0).mean()
    out["f_eq0"] = (prep["F"][sel_slots] == 0).mean()
    out["sd_rate"] = prep["sd"][sel_slots].mean()
    return out


def universe_series(prep, ex):
    st = prep["starts"][ex]
    cnt = prep["cnt"][ex]
    n = len(ex)
    raws = np.empty(n); fund = np.empty(n); slipin = np.empty(n); slipout = np.empty(n)
    nin = np.empty(n); nout = np.empty(n)
    prev_syms = None
    prev_slip = None
    for t in range(n):
        s, c = int(st[t]), int(cnt[t])
        idx = np.arange(s, s + c)
        raws[t] = prep["V"]["raw"][idx].mean()
        fund[t] = prep["V"]["fund"][idx].mean()
        slipin[t] = prep["slip"][idx].mean()
        syms = prep["sym"][idx]
        slips = prep["slip"][idx]
        if prev_syms is None:
            nin[t], nout[t], slipout[t] = c, 0, 0.0
        else:
            still = np.isin(syms, prev_syms)
            nin[t] = int((~still).sum())
            gone = ~np.isin(prev_syms, syms)
            nout[t] = int(gone.sum())
            slipout[t] = float(prev_slip[gone].mean()) if gone.any() else 0.0
        prev_syms, prev_slip = syms, slips
    return {"raw_mean": raws, "fund_mean": fund, "slip_in": slipin, "slip_out": slipout,
            "n_in": nin.astype(np.float64), "n_out": nout.astype(np.float64), "cnt": cnt.astype(np.float64)}


def uni_cost(u, fee_rt):
    fee_side = fee_rt / 2.0
    return (u["n_in"] / u["cnt"]) * (fee_side + u["slip_in"]) + (u["n_out"] / u["cnt"]) * (fee_side + u["slip_out"])


def win_mask(mark, base, tag):
    if tag == "DEV":
        return (mark >= DEV_START - base) & (mark < DEV_END - base)
    return (mark >= 0) & (mark < DEV_END - base)


def sub(arr, w):
    return arr[w]


def table_row(name, net, blk, w, base, mark, extra=""):
    n = sub(net, w)
    b = sub(blk, w)
    s = summ(n, b)
    pos = float((n > 0).mean())
    return {"name": name, "obs": s["obs"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "half": s["half"],
            "p": s["p_gt0"], "b_lo": s["b_lo"], "b_hi": s["b_hi"], "n": s["n"], "nblk": s["nblk"],
            "pos": pos, "extra": extra, "net": n, "blk": b}


def main():
    prep = prepare()
    base = prep["base"]
    mark = prep["mark"] + base            # phut epoch
    blk = block_ids(prep["mark"], base)
    yidx = year_idx(prep["mark"], base)
    cadence = prep["cadence"]
    n_sym = len(cadence)

    say("=== FUNDING_TOPK_ROTATE — luat quay vong 8h: LONG top-K funding nho nhat ===")
    say("Pre-reg `docs/PREREG_FUNDING_TOPK_ROTATE.md` (commit **55b8280**, chot TRUOC khi chay).")
    say("Moc 8h 00/08/16 UTC (r %% 480 == 0, BASE=%d, NMIN=%d, tong moc=%d). Entry close(r), exit" % (base, int(np.load(OUT + "/mark_grid.npz")["nmin"]), len(prep["mark"])))
    say("close(r+480); `f_entry` = rate event cuoi <= r (causal); xep hang TANG DAN => top-K nho nhat;")
    say("dong hang theo sym index. Long equal-weight, HOLD 480'. `net = mean(raw) - mean(f_cum) - cost`,")
    say("cost = (n_in/K)(fee/2+slip_in) + (n_out/K)(fee/2+slip_out) (slip 0.5xrange tai nen moc).")
    say("CI block-72h 2000 rep seed 20260905 x1.21; Bonferroni K_test=3 (p<%.6f); DEV=2022-2025 CHINH, ALL phu." % BONF_P)
    say("")

    # ---------------- 0. neo MOM15 ----------------
    az = np.load(OUT + "/anchor_mom15.npz")
    z0 = np.load(OUT + "/mark_grid.npz")
    ref_total = int(z0["ref_total_rows"]); ref_fire8 = int(z0["ref_fire8"])
    m_min, m_sym = az["m_min"], az["m_sym"]
    m_min_rel = (m_min.astype(np.int64) - base)
    holds = [int(x) for x in az["holds"]]
    j24 = holds.index(1440)
    m_raw = az["m_raw"].astype(np.float64); m_slip = az["m_slip"].astype(np.float64)
    m_fund = az["m_fund"].astype(np.float64); m_valid = az["m_valid"]
    net_m = m_raw[j24] - m_slip - m_fund[j24]
    devm = (m_min_rel >= DEV_START - base) & (m_min_rel < DEV_END - base)
    sel = devm & (((m_valid >> j24) & 1) == 1) & np.isfinite(net_m)
    s_ne = summ(net_m[sel], ((base + m_min_rel[sel]) // BLOCK_MIN).astype(np.int64))
    selA = (((m_valid >> j24) & 1) == 1) & np.isfinite(net_m)
    s_neA = summ(net_m[selA], ((base + m_min_rel[selA]) // BLOCK_MIN).astype(np.int64))
    devm15 = (m_min_rel >= DEV_START - base) & (m_min_rel < DEV_END - base)

    say("## 0. Neo MOM15 — harness con luc? (PHAI khop, neu khong => VOID)")
    say("")
    say("| Kiem chung | Vong nay | Tham chieu | Khop |")
    say("|---|---|---|---|")
    checks = [("total_rows (cache2, vong truoc)", ref_total, 619073711),
              ("Phut MOM15 (rd15<-0,028, cnt>=50)", ref_fire8, 13150),
              ("M-LEVEL MOM15 k=1 rows (ALL)", int(len(m_min)), 11367),
              ("M-LEVEL MOM15 k=1 rows (DEV)", int(devm15.sum()), 7128)]
    for nm, g, w in checks:
        say("| %s | **%s** | %s | %s |" % (nm, nb(g), nb(w), "OK" if g == w else "**LECH**"))
    say("| MOM15 k=1 DEV 24h net @0,10%% | **%s** | +1,6690%% (vong truoc) / +1,6431%% (ref cu) | %s |"
        % (fmt_pct(s_ne["obs"] - FEE_MAIN), "OK" if abs(s_ne["obs"] - FEE_MAIN - 0.016690) < 0.0005 else "**LECH**"))
    say("| MOM15 k=1 ALL 24h net @0,10%% | **%s** | +2,2622%% (ref \"+2,26%%\") | %s |"
        % (fmt_pct(s_neA["obs"] - FEE_MAIN), "OK" if abs(s_neA["obs"] - FEE_MAIN - 0.022622) < 0.0005 else "**LECH**"))
    say("| N_blk MOM15 DEV | %d | 301 | %s |" % (s_ne["nblk"], "OK" if s_ne["nblk"] == 301 else "**LECH**"))
    anchor_ok = abs(s_ne["obs"] - FEE_MAIN - 0.016690) < 0.0005 and ref_total == 619073711 and int(len(m_min)) == 11367
    say("")
    say("=> Neo MOM15: **%s**." % ("TAI TAO DUNG (bo do con luc)" if anchor_ok else "SAI KHOP => VOID"))
    say("")

    # ---------------- 1. grid coverage ----------------
    say("## 1. Coverage grid moc 8h")
    say("")
    cnt = prep["cnt"]
    ex = exec_marks(prep, MIN_SYM_MAIN)
    n_mark = len(prep["mark"])
    say("- Moc 8h co du lieu: **%s**; trong do **%s** moc co `n_elig >= %d` (dung chinh), bo **%d** moc."
        % (nb(n_mark), nb(len(ex)), MIN_SYM_MAIN, n_mark - len(ex)))
    say("- `n_elig`: min **%d**, median **%d**, max **%d**; tong dong grid **%s**."
        % (int(cnt.min()), int(np.median(cnt)), int(cnt.max()), nb(prep["n_all"])))
    cad8 = int((cadence == 8).sum()); cad4 = int((cadence == 4).sum()); cado = int((cadence == 99).sum())
    say("- Cadence funding (median khoang cach event): **%d** symbol 4h, **%d** symbol 8h, **%d** khac; universe raw = **%d**."
        % (cad4, cad8, cado, n_sym))
    say("- Trung binh `n_elig` tren cac moc dung: **%.1f**." % cnt[ex].mean())
    say("")

    # ---------------- 2. bang chinh theo K ----------------
    res = {}
    for K in K_LIST:
        b = basket_series(prep, ex, K)
        res[K] = b

    say("## 2. KET QUA CHINH — net/chu ky theo K (DEV = CHINH, phi 0,10%%)")
    say("")
    say("| K | net/chu ky (DEV) | CI72h x1.21 | p(>0) | CI-Bonf3 | %%chu ky duong | N | N_blk | MDE80 |")
    say("|---|---|---|---|---|---|---|---|---|")
    main_rows = {}
    for K in K_LIST:
        b = res[K]
        cost, n_in, n_out = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(prep["mark"][ex], base, "DEV")
        r = table_row("K%d" % K, net, blk[ex], w, base, prep["mark"][ex])
        mde = mde_of(r["net"], r["blk"])
        r["mde80"] = mde["mde80"]; r["cost"] = cost; r["n_in"] = n_in; r["n_out"] = n_out
        r["raw_mean"] = b["raw_mean"]; r["fund_mean"] = b["fund_mean"]; r["b"] = b
        main_rows[K] = r
        say("| **%d** | **%s** | [%s, %s] | %.3f | [%s, %s] | **%.1f%%** | %d | %d | %s |"
            % (K, fmt_pct(r["obs"]), fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"]), r["p"],
               fmt_pct(r["b_lo"]), fmt_pct(r["b_hi"]), 100 * r["pos"], r["n"], r["nblk"],
               fmt_pct(mde["mde80"]) if mde["mde80"] else ">0,50%"))
    say("")

    # ---------------- 3. turnover + cost drag ----------------
    say("## 3. TURNOVER + COST DRAG (phan quyet dinh) — DEV, phi 0,10%%")
    say("")
    say("| K | turnover/chu ky (1 chieu) | giao dich/chu ky | gross raw | funding f_cum | phi | slip | cost tong | net | cost/gross |")
    say("|---|---|---|---|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        w = win_mask(prep["mark"][ex], base, "DEV")
        sl = prep["slip"][r["b"]["sel_slots"]]
        n_in, n_out = r["n_in"], r["n_out"]
        fee = (n_in + n_out) / (2.0 * K) * FEE_MAIN
        slipc = r["cost"] - (n_in + n_out) / (2.0 * K) * FEE_MAIN
        turn = float((n_in / K)[w].mean())
        gross = r["raw_mean"][w] - r["fund_mean"][w]
        costw = r["cost"][w]
        drag = float(costw.mean() / gross.mean()) if gross.mean() > 0 else float("nan")
        say("| **%d** | **%.1f%%** (med %.1f%%, p90 %.1f%%) | %.2f book/chu ky | %s | %s | %s | %s | **%s** | **%s** | **%.1f%%** |"
            % (K, 100 * turn, 100 * np.median((n_in / K)[w]), 100 * np.percentile((n_in / K)[w], 90),
               2 * turn, fmt_pct(float(r["raw_mean"][w].mean())), fmt_pct(float(r["fund_mean"][w].mean())),
               fmt_pct(float(fee[w].mean())), fmt_pct(float(slipc[w].mean())), fmt_pct(float(costw.mean())),
               fmt_pct(r["obs"]), 100 * drag))
    say("")

    # ---------------- 4. do nhay phi + full-churn ----------------
    say("## 4. Do nhay phi (round-trip 0,05/0,10/0,15%%) + bien the full-churn — DEV")
    say("")
    say("| K | 0,05%% | 0,10%% | 0,15%% | full-churn @0,10%% (can tren) |")
    say("|---|---|---|---|---|")
    for K in K_LIST:
        b = res[K]
        cells = []
        for fee in FEE_GRID:
            cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, fee)
            net = b["raw_mean"] - b["fund_mean"] - cost
            w = win_mask(prep["mark"][ex], base, "DEV")
            s = summ(net[w], blk[ex][w])
            cells.append("%s [%s, %s]" % (fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"])))
        slipK = prep["slip"][b["sel_slots"]].mean(axis=1)
        costf = FEE_MAIN + 2 * slipK
        net = b["raw_mean"] - b["fund_mean"] - costf
        w = win_mask(prep["mark"][ex], base, "DEV")
        s = summ(net[w], blk[ex][w])
        say("| **%d** | %s | %s | %s | %s [%s, %s] |" % (K, cells[0], cells[1], cells[2], fmt_pct(s["obs"]),
                                                          fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"])))
    say("")

    # ---------------- 5. ALL (phu) ----------------
    say("## 5. ALL (2021-2025, PHU — dan nhan ro) — phi 0,10%%")
    say("")
    say("| K | net/chu ky (ALL) | CI72h x1.21 | p(>0) | %%chu ky duong | N | N_blk |")
    say("|---|---|---|---|---|---|---|")
    allrows = {}
    for K in K_LIST:
        b = res[K]
        cost, n_in, n_out = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(prep["mark"][ex], base, "ALL")
        r = table_row("K%d" % K, net, blk[ex], w, base, prep["mark"][ex])
        allrows[K] = r
        say("| **%d** | **%s** | [%s, %s] | %.3f | **%.1f%%** | %d | %d |"
            % (K, fmt_pct(r["obs"]), fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"]), r["p"], 100 * r["pos"], r["n"], r["nblk"]))
    say("")

    # ---------------- 6. theo nam ----------------
    say("## 6. Net/chu ky theo NAM (GMT+7), DEV+2021 hien thi — phi 0,10%%")
    say("")
    hdr = "| K | " + " | ".join("%d" % y for y, _ in YEAR_B if y <= 2025) + " |"
    say(hdr)
    say("|" + "---|" * (len([y for y, _ in YEAR_B if y <= 2025]) + 1))
    for K in K_LIST:
        b = res[K]
        cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        yi = yidx[ex]
        cells = []
        for y, _ in YEAR_B:
            if y > 2025:
                continue
            m = yi == (y - 2021)
            cells.append("%s (n=%d, %.0f%%+)" % (fmt_pct(net[m].mean(), 3), int(m.sum()), 100 * float((net[m] > 0).mean())) if m.any() else "—")
        say("| **%d** | %s |" % (K, " | ".join(cells)))
    say("")

    # ---------------- 7. doi chung ----------------
    say("## 7. Doi chung")
    say("")
    u = universe_series(prep, ex)
    ucost = uni_cost(u, FEE_MAIN)
    unet = u["raw_mean"] - u["fund_mean"] - ucost
    say("### 7a. Trung binh universe cung ky (long TOAN BO eligible, equal-weight, cung mo hinh chi phi)")
    say("")
    say("| | net/chu ky DEV | CI72h x1.21 | %%chu ky duong | turnover | funding |")
    say("|---|---|---|---|---|---|")
    wd = win_mask(prep["mark"][ex], base, "DEV")
    su = summ(unet[wd], blk[ex][wd])
    say("| universe (%d ten/moc trung binh) | **%s** | [%s, %s] | %.1f%% | %.2f%% | %s |"
        % (int(u["cnt"].mean()), fmt_pct(su["obs"]), fmt_pct(su["ci_lo"]), fmt_pct(su["ci_hi"]),
           100 * float((unet[wd] > 0).mean()), 100 * float((u["n_in"] / u["cnt"])[wd].mean()),
           fmt_pct(float(u["fund_mean"][wd].mean()))))
    for K in K_LIST:
        r = main_rows[K]
        say("- K=%d vs universe: **%s** vs %s (chenh %s/chu ky)." % (K, fmt_pct(r["obs"]), fmt_pct(su["obs"]),
                                                                     fmt_pct(r["obs"] - su["obs"])))
    say("")

    say("### 7b. Neo MOM15 (xem §0; tom tat)")
    say("- MOM15 k=1 DEV 24h net @0,10%% = **%s** (CI72h x1.21 [%s, %s], N=%d, N_blk=%d) — neo con luc."
        % (fmt_pct(s_ne["obs"] - FEE_MAIN), fmt_pct(s_ne["ci_lo"] - FEE_MAIN), fmt_pct(s_ne["ci_hi"] - FEE_MAIN),
           s_ne["n"], s_ne["nblk"]))
    say("")

    say("### 7c. Dan chieu H2 vong truoc (funding thap => long)")
    say("- `docs/RESULT_FUNDING_FACTOR.md` (commit 5b548e4): D1 (decile funding thap nhat) net 24h = **-0,1913%%**,")
    say("  CI chua 0, IC cross-section **+0,0009**; H3 NULL. Tien le xa: `SURVEY_OLDCODE_SIGNALS` FUNDING_FEE_BUY ->")
    say("  ML funding_selector -> **FAIL (WFE med 0,098)**.")
    for K in K_LIST:
        r = main_rows[K]
        say("- So sanh K=%d (khung 8h, quay vong): **%s** [%s, %s] vs D1 tinh 24h -0,1913%%." %
            (K, fmt_pct(r["obs"]), fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"])))
    say("")

    # ---------------- 8. null test ----------------
    say("## 8. Null test — long K coin NGAU NHIEN (cung so luong, cung mo hinh chi phi)")
    say("")
    say("| K | null mean/chu ky (DEV) | null sd | p(null >= obs) | obs | rep |")
    say("|---|---|---|---|---|---|")
    rng_base = np.random.default_rng(SEED)
    maxc = int(cnt[ex].max())
    for K in K_LIST:
        rng = np.random.default_rng(SEED + K)
        st = prep["starts"][ex]
        cne = prep["cnt"][ex]
        w = win_mask(prep["mark"][ex], base, "DEV")
        stats = np.empty(NULL_REPS)
        allstats = np.empty(NULL_REPS)
        for rp in range(NULL_REPS):
            R = rng.random((len(ex), maxc), dtype=np.float32)
            bad = np.arange(maxc)[None, :] >= cne[:, None]
            R[bad] = np.inf
            pick = np.argpartition(R, K - 1, axis=1)[:, :K]
            sel_slots = st[:, None] + pick
            sel_sym = prep["sym"][sel_slots]
            rawm = prep["V"]["raw"][sel_slots].mean(axis=1)
            fundm = prep["V"]["fund"][sel_slots].mean(axis=1)
            cost, _, _ = turnover_cost(sel_slots, sel_sym, prep["slip"], K, FEE_MAIN)
            net = rawm - fundm - cost
            stats[rp] = net[w].mean()
            allstats[rp] = net.mean()
        obs = main_rows[K]["obs"]
        # ALL window obs
        cost_o, _, _ = turnover_cost(res[K]["sel_slots"], res[K]["sel_sym"], prep["slip"], K, FEE_MAIN)
        net_o = res[K]["raw_mean"] - res[K]["fund_mean"] - cost_o
        wa = win_mask(prep["mark"][ex], base, "ALL")
        obsA = float(net_o[wa].mean())
        main_rows[K]["null_dev"] = (float(stats.mean()), float(stats.std()), float((stats >= obs).mean()))
        main_rows[K]["null_all"] = (float(allstats.mean()), float(allstats.std()), float((allstats >= obsA).mean()))
        say("| **%d** | %s | %s | **%.3f** | %s | %d |" % (K, fmt_pct(float(stats.mean())), fmt_pct(float(stats.std())),
                                                          float((stats >= obs).mean()), fmt_pct(obs), NULL_REPS))
    say("")
    say("(null ALL: " + "; ".join("K=%d mean %s p=%.3f" % (K, fmt_pct(main_rows[K]["null_all"][0]), main_rows[K]["null_all"][2]) for K in K_LIST) + ")")
    say("")

    # ---------------- 9. ICC ----------------
    say("## 9. ICC + N_eff (net/chu ky, DEV)")
    say("")
    say("| K | ICC(ngay) | ICC(block-72h) | N | N_blk |")
    say("|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        w = win_mask(prep["mark"][ex], base, "DEV")
        net = r["net"]
        day = ((base + prep["mark"][ex]) // 1440)[w]
        say("| **%d** | %.4f | %.4f | %d | %d |" % (K, icc(net, day), icc(net, r["blk"]), r["n"], r["nblk"]))
    say("")

    # ---------------- 10. basket characteristics ----------------
    say("## 10. Dac trung basket chon (DEV, phi 0,10%%): f_entry + delist")
    say("")
    say("| K | f_entry mean (%%/ky) | f_entry median | f_entry min | f_entry max | %%ten f<=0 | %%ten f=0 | ty le dong short_delist |")
    say("|---|---|---|---|---|---|---|---|")
    for K in K_LIST:
        b = res[K]
        w = win_mask(prep["mark"][ex], base, "DEV")
        say("| **%d** | %.5f%% | %.5f%% | %.5f%% | %.5f%% | %.1f%% | %.1f%% | %.4f |"
            % (K, 100 * float(b["f_mean"][w].mean()), 100 * float(np.median(b["f_med"][w])),
               100 * float(b["f_min"][w].min()), 100 * float(b["f_max"][w].max()),
               100 * b["f_le0"], 100 * b["f_eq0"], float(b["sd_rate"])))
    say("")

    # ---------------- 11. cach phu (B): universe cadence 8h ----------------
    say("## 11. CACH PHU (B) — universe CHI symbol cadence 8h (khong dung de tuyen bo)")
    say("")
    # rebuild with 8h-only rows: reload raw grid and filter by cadence
    z = np.load(OUT + "/mark_grid.npz")
    g_sym_all = z["g_sym"]
    rows8 = (z["cadence"] == 8)[g_sym_all]
    p8 = prepare(rows8)
    ex8 = exec_marks(p8, MIN_SYM_MAIN)
    base8 = p8["base"]
    blk8 = block_ids(p8["mark"], base8)
    say("- Symbol cadence 8h trong universe: **%d/%d**; moc dung duoc: **%d**; `n_elig` median **%d**."
        % (int((z["cadence"] == 8).sum()), len(z["cadence"]), len(ex8), int(np.median(p8["cnt"][ex8]))))
    say("")
    say("| K | net/chu ky (DEV) | CI72h x1.21 | %%chu ky duong | N | N_blk | turnover |")
    say("|---|---|---|---|---|---|---|")
    for K in K_LIST:
        b = basket_series(p8, ex8, K)
        cost, n_in, _ = turnover_cost(b["sel_slots"], b["sel_sym"], p8["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(p8["mark"][ex8], base8, "DEV")
        s = summ(net[w], blk8[ex8][w])
        say("| **%d** | **%s** | [%s, %s] | %.1f%% | %d | %d | %.1f%% |"
            % (K, fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"]),
               100 * float((net[w] > 0).mean()), s["n"], s["nblk"], 100 * float((n_in / K)[w].mean())))
    say("")

    # ---------------- 12. do nhay MIN_SYM ----------------
    say("## 12. Do nhay MIN_SYM (descriptive)")
    say("")
    say("| MIN_SYM | so moc dung | K=5 | K=10 | K=20 |")
    say("|---|---|---|---|---|")
    for ms in (MIN_SYM_MAIN, MIN_SYM_ALT):
        exx = exec_marks(prep, ms)
        cells = []
        for K in K_LIST:
            b = basket_series(prep, exx, K)
            cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
            net = b["raw_mean"] - b["fund_mean"] - cost
            w = win_mask(prep["mark"][exx], base, "DEV")
            s = summ(net[w], blk[exx][w])
            cells.append("%s [%s, %s]" % (fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"])))
        say("| %d | %d | %s | %s | %s |" % (ms, len(exx), cells[0], cells[1], cells[2]))
    say("")

    # ---------------- 13. MDE ----------------
    say("## 13. MDE80 (%/chu ky, luoi {0,01;0,02;0,05;0,10;0,20;0,50}%) + power")
    say("")
    say("| K | MDE80 | p50 half-width | p80 | p95 | N | N_blk |")
    say("|---|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        mde = mde_of(r["net"], r["blk"])
        say("| **%d** | **%s** | %s | %s | %s | %d | %d |"
            % (K, fmt_pct(mde["mde80"]) if mde["mde80"] else ">0,50%", fmt_pct(mde["p50"]),
               fmt_pct(mde["p80"]), fmt_pct(mde["p95"]), r["n"], r["nblk"]))
    say("")

    # ---------------- 14. GATE ----------------
    say("## 14. CONG KET LUAN (K_test=3, Bonferroni p<%.6f)" % BONF_P)
    say("")
    say("| K | (1) net>0 | (2) CI x1.21 ngoai 0 | (3) CI-Bonf3 ngoai 0 | (4) >=60%% chu ky duong | (5) |net|>=MDE | (6) khong doi dau ALL | (7) khong doi dau phi 0,15%% | GO? |")
    say("|---|---|---|---|---|---|---|---|---|")
    go_flags = {}
    for K in K_LIST:
        r = main_rows[K]
        b = res[K]
        cost15, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, 0.0015)
        net15 = b["raw_mean"] - b["fund_mean"] - cost15
        w = win_mask(prep["mark"][ex], base, "DEV")
        o15 = float(net15[w].mean())
        mde = mde_of(r["net"], r["blk"])
        c1 = r["obs"] > 0
        c2 = r["ci_lo"] > 0
        c3 = r["b_lo"] > 0
        c4 = r["pos"] >= 0.60
        c5 = (mde["mde80"] is not None) and abs(r["obs"]) >= mde["mde80"]
        c6 = allrows[K]["obs"] > 0
        c7 = o15 > 0
        g = c1 and c2 and c3 and c4 and c5 and c6 and c7
        go_flags[K] = g
        say("| **%d** | %s | %s | %s | %s (%.1f%%) | %s | %s | %s (%s) | **%s** |"
            % (K, yn(c1), yn(c2), yn(c3), yn(c4), 100 * r["pos"], yn(c5), yn(c6), yn(c7), fmt_pct(o15),
               "GO" if g else "NO-GO"))
    say("")
    ngo = sum(1 for K in K_LIST if go_flags[K])
    if ngo == 3:
        verdict = "GO ca 3 K"
    elif ngo == 0:
        verdict = "NO-GO ca 3 K"
    else:
        verdict = "UNCONFIRMED (post-hoc) — %d/3 K dat, KHONG ap dung" % ngo
    say("**KET LUAN SO BO: %s**" % verdict)
    say("")
    say("### Tom tat so quyet dinh (DEV, phi 0,10%%)")
    say("")
    say("| K | gross (raw - funding) | cost/chu ky | net/chu ky | CI72h x1.21 | turnover |")
    say("|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        w = win_mask(prep["mark"][ex], base, "DEV")
        b = res[K]
        gross = float((b["raw_mean"] - b["fund_mean"])[w].mean())
        say("| **%d** | %s | %s | **%s** | [%s, %s] | %.1f%% |"
            % (K, fmt_pct(gross), fmt_pct(float(r["cost"][w].mean())), fmt_pct(r["obs"]),
               fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"]), 100 * float((r["n_in"] / K)[w].mean())))
    say("")
    open(OUT + "/report.txt", "w").write("\n".join(rep).replace("%%", "%") + "\n")
    log.info("report written")


def yn(b):
    return "ĐẠT" if b else "KHÔNG"


if __name__ == "__main__":
    main()
