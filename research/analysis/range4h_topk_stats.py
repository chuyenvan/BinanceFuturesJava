#!/usr/bin/env python3
"""RANGE4H_TOPK stats — luat quay vong 4h LONG top-K coin co NEN 4h BIEN DO RONG NHAT.

Pre-reg: docs/PREREG_RANGE4H_TOPK.md (commit 62e01bf, chot TRUOC khi chay; KHONG sua thiet ke).

Doc $R4H_OUT/mark_grid4h.npz (grid moc 4h) + $R4H_OUT/anchor_mom15.npz (neo MOM15).
Moi chu ky = 1 moc 4h: basket = K symbol co range4h LON NHAT (giam dan, dong hang theo sym index),
long equal-weight, HOLD 240', cost = fee_rt/2 + slip 0.5xrange MOI CHIEU tren phan book quay vong
(n_in/K + n_out/K) + funding thuc tra f_cum (r, r+240].
CI block-72h x1.21 2000 rep seed 20260905; Bonferroni K_test=4; null K coin ngau nhien >=200 rep;
MDE luoi rieng khung 4h; DEV 2022-2025 chinh, ALL 2021-2025 phu; PHU HOLD 24h.
"""
import os
import json
import logging
from datetime import datetime, timezone

import numpy as np

OUT = os.environ.get("R4H_OUT", "/tmp/range4h_topk")
SEED = 20260905
NREP = 2000
NREP_MDE_OUTER = 2000
NREP_MDE_INNER = 200
NULL_REPS = 300
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
K_TESTS = 4
ALPHA = 0.05
BONF_P = ALPHA / K_TESTS
BONF_PCT = [100 * BONF_P / 2, 100 * (1 - BONF_P / 2)]
MDE_GRID = [0.0001, 0.0002, 0.0005, 0.0010, 0.0020, 0.0050]   # %/chu ky (khung 4h)
K_LIST = (1, 3, 5, 10)
FEE_GRID = (0.0005, 0.0010, 0.0015)
FEE_MAIN = 0.0010
MIN_SYM_MAIN = 50
MIN_SYM_ALT = 100
LEVEL_MIN = 240
HOLD_AUX = 1440
UTC = timezone.utc
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
YEAR_B = [(y, int(datetime(y, 1, 1, tzinfo=UTC).timestamp() // 60) - 420) for y in range(2021, 2027)]

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/stats4h.log")])
log = logging.getLogger("r4hstats")
rep = []
NUM = {}


def say(s=""):
    rep.append(s)
    log.info(s)


def nb(x):
    return f"{int(x):,}".replace(",", " ")


def fmt_pct(x, nd=4):
    return ("%." + str(nd) + "f%%") % (100 * x) if np.isfinite(x) else "nan"


def yn(b):
    return "ĐẠT" if b else "KHÔNG"


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
            "b_lo": float(blo), "b_hi": float(bhi)}


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
            "p95": float(np.percentile(hs, 95)), "mde80": mde80,
            "power": {("%.2f%%" % (100 * k)): v for k, v in power.items()}}


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
    prev_sym = np.empty_like(sel_sym)
    prev_sym[0] = -1
    prev_sym[1:] = sel_sym[:-1]
    prev_slots = np.empty_like(sel_slots)
    prev_slots[0] = sel_slots[0]
    prev_slots[1:] = sel_slots[:-1]
    carried_new = (sel_sym[:, :, None] == prev_sym[:, None, :]).any(axis=2)
    carried_prev = (prev_sym[:, :, None] == sel_sym[:, None, :]).any(axis=2)
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
def prepare(mark_key="g_mark", raw_key="g_raw240", fund_key="g_fund240", rows_mask=None):
    z = np.load(OUT + "/mark_grid4h.npz")
    base = int(z["base"])
    g_mark, g_sym = z[mark_key], z["g_sym"]
    g_rng, g_slip = z["g_rng"], z["g_slip"]
    g_raw, g_fund = z[raw_key], z[fund_key]
    if rows_mask is not None:
        g_mark, g_sym = g_mark[rows_mask], g_sym[rows_mask]
        g_rng, g_slip, g_raw, g_fund = g_rng[rows_mask], g_slip[rows_mask], g_raw[rows_mask], g_fund[rows_mask]
    key = -g_rng.astype(np.float64)          # giam dan theo bien do  => tang dan theo -range
    o = np.lexsort((g_sym, key, g_mark))     # primary mark, then range DESC, then sym asc
    mk = g_mark[o]
    uniq, starts = np.unique(mk, return_index=True)
    ends = np.r_[starts[1:], len(mk)]
    return {"base": base, "mark": uniq, "starts": starts, "ends": ends,
            "cnt": (ends - starts),
            "sym": g_sym[o], "RNG": g_rng[o].astype(np.float64),
            "slip": g_slip[o].astype(np.float64),
            "V": {"raw": g_raw[o].astype(np.float64), "fund": g_fund[o].astype(np.float64)},
            "n_all": len(mk)}


def exec_marks(prep, min_sym):
    return np.flatnonzero(prep["cnt"] >= min_sym)


def basket_series(prep, ex, K):
    st = prep["starts"][ex]
    cnt = prep["cnt"][ex]
    sel_slots = st[:, None] + np.arange(K)[None, :]
    sel_sym = prep["sym"][sel_slots]
    out = {"sel_slots": sel_slots, "sel_sym": sel_sym, "cnt": cnt}
    for k in ("raw", "fund"):
        out[k + "_mean"] = prep["V"][k][sel_slots].mean(axis=1)
    out["slip_mean"] = prep["slip"][sel_slots].mean(axis=1)
    RG = prep["RNG"][sel_slots]
    out["rng_mean"] = RG.mean(axis=1)
    # phan vi cua basket trong pool cua moc (0..1, 1 = rong nhat)
    jm = (K - 1) / 2.0
    out["pct_med"] = 1.0 - (jm + 0.5) / cnt.astype(np.float64)
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


def main():
    z = np.load(OUT + "/mark_grid4h.npz")
    base = int(z["base"])
    prep = prepare()
    mark = prep["mark"] + base
    blk = block_ids(prep["mark"], base)
    yidx = year_idx(prep["mark"], base)

    say("=== RANGE4H_TOPK — luat quay vong 4h: LONG top-K NEN 4h BIEN DO RONG NHAT ===")
    say("Pre-reg `docs/PREREG_RANGE4H_TOPK.md` (commit **62e01bf**, chot TRUOC khi chay).")
    say("Moc 4h 00/04/08/12/16/20 UTC (r %% 240 == 0, BASE=%d, NMIN=%d)." % (base, int(z["nmin"])))
    say("range4h = (max high - min low)/open tren [r-240, r-1] (nen 4h DA DONG, >=200/240 phut).")
    say("Xep hang GIAM DAN => top-K LON NHAT; dong hang theo sym index. Entry close(r), exit close(r+240).")
    say("net = mean(raw) - mean(f_cum) - cost; cost = (n_in/K)(fee/2+slip_in) + (n_out/K)(fee/2+slip_out).")
    say("CI block-72h 2000 rep seed %d x1.21; Bonferroni K_test=%d (p<%.6f); DEV=2022-2025 CHINH, ALL phu."
        % (SEED, K_TESTS, BONF_P))
    say("")

    # ---------------- 0. neo MOM15 ----------------
    az = np.load(OUT + "/anchor_mom15.npz")
    ref_total = int(z["ref_total_rows"]); ref_fire8 = int(z["ref_fire8"])
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
    d_dev = s_ne["obs"] - FEE_MAIN
    d_all = s_neA["obs"] - FEE_MAIN
    checks = [("total_rows (cache2, vong truoc)", ref_total, 619073711),
              ("Phut MOM15 (rd15<-0,028, cnt>=50)", ref_fire8, 13150),
              ("M-LEVEL MOM15 k=1 rows (ALL)", int(len(m_min)), 11367),
              ("M-LEVEL MOM15 k=1 rows (DEV)", int(devm15.sum()), 7128)]
    for nm, g, w in checks:
        say("| %s | **%s** | %s | %s |" % (nm, nb(g), nb(w), "OK" if g == w else "**LECH**"))
    say("| MOM15 k=1 DEV 24h net @0,10%% | **%s** | +1,6690%% (vong truoc) / +1,6431%% (ref cu) | %s |"
        % (fmt_pct(d_dev), "OK" if abs(d_dev - 0.016690) < 0.0005 else "**LECH**"))
    say("| MOM15 k=1 ALL 24h net @0,10%% | **%s** | +2,2622%% (ref \"+2,26%%\") | %s |"
        % (fmt_pct(d_all), "OK" if abs(d_all - 0.022622) < 0.0005 else "**LECH**"))
    say("| N_blk MOM15 DEV | %d | 301 | %s |" % (s_ne["nblk"], "OK" if s_ne["nblk"] == 301 else "**LECH**"))
    anchor_ok = (abs(d_dev - 0.016690) < 0.0005 and abs(d_all - 0.022622) < 0.0005
                 and ref_total == 619073711 and int(len(m_min)) == 11367 and s_ne["nblk"] == 301)
    say("")
    say("=> Neo MOM15: **%s**." % ("TAI TAO DUNG (bo do con luc)" if anchor_ok else "SAI KHOP => VOID"))
    say("")
    NUM["anchor"] = {"dev24": d_dev, "all24": d_all, "nblk": s_ne["nblk"], "n_dev": s_ne["n"],
                     "ci_dev": [s_ne["ci_lo"] - FEE_MAIN, s_ne["ci_hi"] - FEE_MAIN], "ok": bool(anchor_ok)}

    # ---------------- 1. coverage ----------------
    cnt = prep["cnt"]
    ex = exec_marks(prep, MIN_SYM_MAIN)
    n_mark = len(prep["mark"])
    say("## 1. Coverage grid moc 4h")
    say("")
    say("- Moc 4h co du lieu: **%s**; trong do **%s** moc co `n_elig >= %d` (dung chinh), bo **%d** moc."
        % (nb(n_mark), nb(len(ex)), MIN_SYM_MAIN, n_mark - len(ex)))
    say("- `n_elig`: min **%d**, median **%d**, max **%d**; tong dong grid **%s**."
        % (int(cnt.min()), int(np.median(cnt)), int(cnt.max()), nb(prep["n_all"])))
    say("- Trung binh `n_elig` tren cac moc dung: **%.1f**." % cnt[ex].mean())
    st = z["stat_n_mark_rows"]
    say("- Chan doan sinh grid (tren toan universe symbol-moc): khong co nen tai moc **%s**; cua so nen"
        " khuyet (`<200/240` phut hoac thieu nen open) **%s**; tong dong raw **%s**;"
        " dong **eligible (HOLD 240 + f_cum huu han) = %s**."
        % (nb(z["stat_n_bar_miss"]), nb(z["stat_n_win_short"]), nb(z["stat_n_mark_rows"]), nb(z["stat_n_elig"])))
    say("- `short_delist` (exit som) ti le dong: **%.5f**; so symbol co funding record: **%d/%d**."
        % (float(z["stat_n_delist"]) / max(int(z["stat_n_elig"]), 1), int(z["stat_n_fund_ok"]), int(z["n_sym"])))
    say("- So dong bi loai vi khong co funding: **%s**." % nb(z["stat_n_nofund_rows"]))
    say("")
    NUM["coverage"] = {"marks_data": int(n_mark), "marks_used": int(len(ex)),
                       "n_elig_min": int(cnt.min()), "n_elig_med": int(np.median(cnt)),
                       "n_elig_max": int(cnt.max()), "rows_grid": int(prep["n_all"]),
                       "rows_generated": int(z["stat_n_mark_rows"]), "delist_rate": float(z["stat_n_delist"]) / max(int(z["stat_n_elig"]), 1)}

    # ---------------- 2. bang chinh theo K ----------------
    res = {K: basket_series(prep, ex, K) for K in K_LIST}
    say("## 2. KET QUA CHINH — net/chu ky theo K (DEV = CHINH, phi 0,10%%)")
    say("")
    say("| K | net/chu ky (DEV) | CI72h x1.21 | p(>0) | CI-Bonf4 | %%chu ky duong | N | N_blk |")
    say("|---|---|---|---|---|---|---|---|")
    main_rows = {}
    for K in K_LIST:
        b = res[K]
        cost, n_in, n_out = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(prep["mark"][ex], base, "DEV")
        r = {"K": K, "net": net[w], "blk": blk[ex][w], "cost": cost, "n_in": n_in, "n_out": n_out,
             "b": b, "w": w}
        s = summ(net[w], blk[ex][w])
        r.update({"obs": s["obs"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "p": s["p_gt0"],
                  "b_lo": s["b_lo"], "b_hi": s["b_hi"], "n": s["n"], "nblk": s["nblk"],
                  "pos": float((net[w] > 0).mean())})
        main_rows[K] = r
        say("| **%d** | **%s** | [%s, %s] | %.3f | [%s, %s] | **%.1f%%** | %d | %d |"
            % (K, fmt_pct(r["obs"]), fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"]), r["p"],
               fmt_pct(r["b_lo"]), fmt_pct(r["b_hi"]), 100 * r["pos"], r["n"], r["nblk"]))
        # checkpoint trung gian ngay sau moi K
        json.dump({k: (float(v) if isinstance(v, (int, float, np.floating, np.integer)) else None)
                   for k, v in r.items() if k not in ("net", "blk", "cost", "n_in", "n_out", "b", "w")},
                  open(OUT + "/checkpoint_K%d.json" % K, "w"), indent=1)
        NUM["K%d_DEV" % K] = {"net": r["obs"], "ci": [r["ci_lo"], r["ci_hi"]], "p": r["p"],
                              "pos_frac": r["pos"], "n": r["n"], "nblk": r["nblk"]}
    say("")

    # ---------------- 3. turnover + cost drag ----------------
    say("## 3. TURNOVER + COST DRAG (phan quyet dinh) — DEV, phi 0,10%%")
    say("")
    say("| K | turnover/chu ky (1 chieu) | giao dich/chu ky | raw | f_cum | phi | slip | cost tong | net | cost/gross |")
    say("|---|---|---|---|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        w = r["w"]
        n_in, n_out = r["n_in"], r["n_out"]
        feec = (n_in + n_out) / (2.0 * K) * FEE_MAIN
        slipc = r["cost"] - (n_in + n_out) / (2.0 * K) * FEE_MAIN
        turn = float((n_in / K)[w].mean())
        gross = r["b"]["raw_mean"][w] - r["b"]["fund_mean"][w]
        drag = float(r["cost"][w].mean() / gross.mean()) if gross.mean() > 0 else float("nan")
        say("| **%d** | **%.1f%%** (med %.1f%%, p90 %.1f%%) | %.2f book/chu ky | %s | %s | %s | %s | **%s** | **%s** | **%.1f%%** |"
            % (K, 100 * turn, 100 * np.median((n_in / K)[w]), 100 * np.percentile((n_in / K)[w], 90),
               2 * turn, fmt_pct(float(r["b"]["raw_mean"][w].mean())), fmt_pct(float(r["b"]["fund_mean"][w].mean())),
               fmt_pct(float(feec[w].mean())), fmt_pct(float(slipc[w].mean())), fmt_pct(float(r["cost"][w].mean())),
               fmt_pct(r["obs"]), 100 * drag))
        NUM["K%d_cost" % K] = {"turnover": turn, "turnover_med": float(np.median((n_in / K)[w])),
                               "turnover_p90": float(np.percentile((n_in / K)[w], 90)),
                               "raw": float(r["b"]["raw_mean"][w].mean()),
                               "fund": float(r["b"]["fund_mean"][w].mean()),
                               "gross": float(gross.mean()), "fee": float(feec[w].mean()),
                               "slip": float(slipc[w].mean()), "cost": float(r["cost"][w].mean()),
                               "cost_over_gross": drag,
                               "slip_side_basket": float(r["b"]["slip_mean"][w].mean())}
    say("")
    # slip basket vs universe (descriptive)
    u = universe_series(prep, ex)
    wd = win_mask(prep["mark"][ex], base, "DEV")
    say("- **slip/chieu** (nua bien do nen 1m moc): basket K=1 **%s**, K=5 **%s**, K=10 **%s**;"
        " **universe %s** (moc trung binh)."
        % (fmt_pct(float(res[1]["slip_mean"][wd].mean())), fmt_pct(float(res[5]["slip_mean"][wd].mean())),
           fmt_pct(float(res[10]["slip_mean"][wd].mean())), fmt_pct(float(u["slip_in"][wd].mean()))))
    NUM["slip_universe"] = float(u["slip_in"][wd].mean())
    say("")

    # ---------------- 4. do nhay phi + full-churn ----------------
    say("## 4. Do nhay phi (round-trip 0,05/0,10/0,15%%) + bien the full-churn — DEV")
    say("")
    say("| K | 0,05%% | 0,10%% | 0,15%% | full-churn @0,10%% (can tren) |")
    say("|---|---|---|---|---|")
    for K in K_LIST:
        b = res[K]
        cells = []
        feeobs = {}
        for fee in FEE_GRID:
            cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, fee)
            net = b["raw_mean"] - b["fund_mean"] - cost
            w = win_mask(prep["mark"][ex], base, "DEV")
            s = summ(net[w], blk[ex][w])
            cells.append("%s [%s, %s]" % (fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"])))
            feeobs["%.2f%%" % (100 * fee)] = s["obs"]
            if fee == 0.0015:
                main_rows[K]["obs15"] = s["obs"]
        slipK = prep["slip"][b["sel_slots"]].mean(axis=1)
        costf = FEE_MAIN + 2 * slipK
        net = b["raw_mean"] - b["fund_mean"] - costf
        w = win_mask(prep["mark"][ex], base, "DEV")
        s = summ(net[w], blk[ex][w])
        say("| **%d** | %s | %s | %s | %s [%s, %s] |" % (K, cells[0], cells[1], cells[2], fmt_pct(s["obs"]),
                                                          fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"])))
        NUM["K%d_fee" % K] = {"obs_by_fee": feeobs, "f15": main_rows[K]["obs15"],
                              "fullchurn": s["obs"], "cells": cells}
    say("")

    # ---------------- 5. ALL (phu) ----------------
    say("## 5. ALL (2021-2025, PHU — dan nhan ro) — phi 0,10%%")
    say("")
    say("| K | net/chu ky (ALL) | CI72h x1.21 | p(>0) | %%chu ky duong | N | N_blk |")
    say("|---|---|---|---|---|---|---|")
    allrows = {}
    for K in K_LIST:
        b = res[K]
        cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(prep["mark"][ex], base, "ALL")
        s = summ(net[w], blk[ex][w])
        allrows[K] = {"obs": s["obs"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "p": s["p_gt0"],
                      "pos": float((net[w] > 0).mean()), "n": s["n"], "nblk": s["nblk"]}
        say("| **%d** | **%s** | [%s, %s] | %.3f | **%.1f%%** | %d | %d |"
            % (K, fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"]), s["p_gt0"],
               100 * float((net[w] > 0).mean()), s["n"], s["nblk"]))
        NUM["K%d_ALL" % K] = allrows[K]
    say("")

    # ---------------- 6. theo nam ----------------
    say("## 6. Net/chu ky theo NAM (GMT+7) — phi 0,10%%")
    say("")
    yrs = [y for y, _ in YEAR_B if y <= 2025]
    say("| K | " + " | ".join("%d" % y for y in yrs) + " |")
    say("|" + "---|" * (len(yrs) + 1))
    yi = yidx[ex]
    for K in K_LIST:
        b = res[K]
        cost, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        cells = []
        for y, _ in YEAR_B:
            if y > 2025:
                continue
            m = yi == (y - 2021)
            cells.append("%s (n=%d, %.0f%%+)" % (fmt_pct(float(net[m].mean()), 3), int(m.sum()),
                                                 100 * float((net[m] > 0).mean())) if m.any() else "—")
        say("| **%d** | %s |" % (K, " | ".join(cells)))
    say("")

    # ---------------- 7. doi chung ----------------
    say("## 7. Doi chung")
    say("")
    say("### 7a. Trung binh universe cung ky (long TOAN BO eligible, equal-weight, cung mo hinh chi phi)")
    say("")
    say("| | net/chu ky DEV | CI72h x1.21 | %%chu ky duong | turnover | funding |")
    say("|---|---|---|---|---|---|")
    ucost = uni_cost(u, FEE_MAIN)
    unet = u["raw_mean"] - u["fund_mean"] - ucost
    su = summ(unet[wd], blk[ex][wd])
    say("| universe (%d ten/moc trung binh) | **%s** | [%s, %s] | %.1f%% | %.2f%% | %s |"
        % (int(u["cnt"].mean()), fmt_pct(su["obs"]), fmt_pct(su["ci_lo"]), fmt_pct(su["ci_hi"]),
           100 * float((unet[wd] > 0).mean()), 100 * float((u["n_in"] / u["cnt"])[wd].mean()),
           fmt_pct(float(u["fund_mean"][wd].mean()))))
    for K in K_LIST:
        r = main_rows[K]
        say("- K=%d vs universe: **%s** vs %s (chenh %s/chu ky)." % (K, fmt_pct(r["obs"]), fmt_pct(su["obs"]),
                                                                     fmt_pct(r["obs"] - su["obs"])))
    NUM["universe"] = {"net": su["obs"], "ci": [su["ci_lo"], su["ci_hi"]], "pos_frac": float((unet[wd] > 0).mean()),
                       "turnover": float((u["n_in"] / u["cnt"])[wd].mean()), "fund": float(u["fund_mean"][wd].mean()),
                       "raw": float(u["raw_mean"][wd].mean()), "n_elig_mean": float(u["cnt"].mean())}
    say("")
    say("### 7b. Neo MOM15 (xem §0)")
    say("- MOM15 k=1 DEV 24h net @0,10%% = **%s** (CI72h x1.21 [%s, %s], N=%d, N_blk=%d); ALL = **%s**."
        % (fmt_pct(d_dev), fmt_pct(s_ne["ci_lo"] - FEE_MAIN), fmt_pct(s_ne["ci_hi"] - FEE_MAIN),
           s_ne["n"], s_ne["nblk"], fmt_pct(d_all)))
    say("")
    say("### 7c. Dan chieu vong funding-topk (commit fdf61d7) + funding-factor")
    say("- `RESULT_FUNDING_TOPK_ROTATE.md`: top-K funding NHO NHAT khung 8h — net DEV **-0,2223%% (K=5)**,"
        " cost/gross **351%%**, slip/chieu basket **0,334%%** vs universe **0,139%%**; universe equal-weight"
        " (8h) **-0,0129%%**; ket luan **NO-GO ca 3 K**.")
    say("- `RESULT_FUNDING_FACTOR.md` D1 (funding thap nhat) net 24h -0,1913%%, CI chua 0. Tien le xa:"
        " `SURVEY_OLDCODE_SIGNALS` FUNDING_FEE_BUY -> FAIL (WFE med 0,098).")
    say("")

    # ---------------- 8. null test ----------------
    say("## 8. Null test — long K coin NGAU NHIEN (cung so luong, cung mo hinh chi phi)")
    say("")
    say("| K | null mean/chu ky (DEV) | null sd | p(null >= obs) | obs | rep |")
    say("|---|---|---|---|---|---|")
    maxc = int(cnt[ex].max())
    for K in K_LIST:
        rng = np.random.default_rng(SEED + K)
        stx = prep["starts"][ex]
        cne = prep["cnt"][ex]
        w = win_mask(prep["mark"][ex], base, "DEV")
        stats = np.empty(NULL_REPS)
        allstats = np.empty(NULL_REPS)
        for rp in range(NULL_REPS):
            R = rng.random((len(ex), maxc), dtype=np.float32)
            bad = np.arange(maxc)[None, :] >= cne[:, None]
            R[bad] = np.inf
            pick = np.argpartition(R, K - 1, axis=1)[:, :K]
            sel_slots = stx[:, None] + pick
            sel_sym = prep["sym"][sel_slots]
            rawm = prep["V"]["raw"][sel_slots].mean(axis=1)
            fundm = prep["V"]["fund"][sel_slots].mean(axis=1)
            cost, _, _ = turnover_cost(sel_slots, sel_sym, prep["slip"], K, FEE_MAIN)
            net = rawm - fundm - cost
            stats[rp] = net[w].mean()
            allstats[rp] = net.mean()
        obs = main_rows[K]["obs"]
        b = res[K]
        cost_o, _, _ = turnover_cost(b["sel_slots"], b["sel_sym"], prep["slip"], K, FEE_MAIN)
        net_o = b["raw_mean"] - b["fund_mean"] - cost_o
        wa = win_mask(prep["mark"][ex], base, "ALL")
        obsA = float(net_o[wa].mean())
        main_rows[K]["null_dev"] = (float(stats.mean()), float(stats.std()), float((stats >= obs).mean()))
        main_rows[K]["null_all"] = (float(allstats.mean()), float(allstats.std()), float((allstats >= obsA).mean()))
        say("| **%d** | %s | %s | **%.3f** | %s | %d |" % (K, fmt_pct(float(stats.mean())),
                                                          fmt_pct(float(stats.std())),
                                                          float((stats >= obs).mean()), fmt_pct(obs), NULL_REPS))
        NUM["K%d_null" % K] = {"mean": float(stats.mean()), "sd": float(stats.std()),
                               "p": float((stats >= obs).mean()), "obs": obs,
                               "all_mean": float(allstats.mean()), "all_p": float((allstats >= obsA).mean())}
    say("")
    say("(null ALL: " + "; ".join("K=%d mean %s p=%.3f" % (K, fmt_pct(main_rows[K]["null_all"][0]),
                                                          main_rows[K]["null_all"][2]) for K in K_LIST) + ")")
    say("")

    # ---------------- 9. ICC ----------------
    say("## 9. ICC + N_eff (net/chu ky, DEV)")
    say("")
    say("| K | ICC(ngay) | ICC(block-72h) | N | N_blk |")
    say("|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        day = ((base + prep["mark"][ex]) // 1440)[r["w"]]
        say("| **%d** | %.4f | %.4f | %d | %d |" % (K, icc(r["net"], day), icc(r["net"], r["blk"]), r["n"], r["nblk"]))
    say("")

    # ---------------- 10. dac trung basket ----------------
    say("## 10. Dac trung basket chon (DEV): range4h + phan vi trong pool")
    say("")
    say("| K | range mean | range median | range min | range max | phan vi trung binh trong pool |")
    say("|---|---|---|---|---|---|")
    for K in K_LIST:
        b = res[K]
        w = wd
        say("| **%d** | %.4f%% | %.4f%% | %.4f%% | %.4f%% | %.4f |"
            % (K, 100 * float(b["rng_mean"][w].mean()), 100 * float(np.median(b["rng_mean"][w])),
               100 * float(np.nanmin(b["rng_mean"][w])), 100 * float(np.nanmax(b["rng_mean"][w])),
               float(b["pct_med"][w].mean())))
        NUM["K%d_rng" % K] = {"mean": float(b["rng_mean"][w].mean()), "pct_med": float(b["pct_med"][w].mean())}
    say("- Universe pool: range trung binh (moc trung binh) = **%.4f%%** (trung binh cua trung binh tung moc)."
        % (100 * float(np.mean([prep["RNG"][s:e].mean() for s, e in zip(prep["starts"][ex], prep["ends"][ex])]))))
    say("")

    # ---------------- 11. PHU: HOLD 24h ----------------
    say("## 11. PHU — HOLD 24h (moc 00 UTC, `r %% 1440 == 0`; dan nhan, KHONG dung de tuyen bo)")
    say("")
    zz = np.load(OUT + "/mark_grid4h.npz")
    rows24 = ((zz["g_mark"] % 1440) == 0)
    p24 = prepare(raw_key="g_raw1440", fund_key="g_fund1440", rows_mask=rows24)
    ex24 = exec_marks(p24, MIN_SYM_MAIN)
    blk24 = block_ids(p24["mark"], base)
    say("- So moc 00 UTC dung duoc: **%d** (tu %d); `n_elig` median **%d**." %
        (len(ex24), int(rows24.sum()), int(np.median(p24["cnt"][ex24]))))
    say("")
    say("| K | net/24h (DEV) | CI72h x1.21 | %%chu ky duong | N | N_blk | turnover/24h | cost/24h |")
    say("|---|---|---|---|---|---|---|---|")
    for K in K_LIST:
        b = basket_series(p24, ex24, K)
        cost, n_in, _ = turnover_cost(b["sel_slots"], b["sel_sym"], p24["slip"], K, FEE_MAIN)
        net = b["raw_mean"] - b["fund_mean"] - cost
        w = win_mask(p24["mark"][ex24], base, "DEV")
        s = summ(net[w], blk24[ex24][w])
        say("| **%d** | **%s** | [%s, %s] | %.1f%% | %d | %d | %.1f%% | %s |"
            % (K, fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"]),
               100 * float((net[w] > 0).mean()), s["n"], s["nblk"],
               100 * float((n_in / K)[w].mean()), fmt_pct(float(cost[w].mean()))))
        NUM["K%d_HOLD24h" % K] = {"net": s["obs"], "ci": [s["ci_lo"], s["ci_hi"]],
                                  "pos_frac": float((net[w] > 0).mean()), "n": s["n"],
                                  "turnover": float((n_in / K)[w].mean()), "cost": float(cost[w].mean()),
                                  "raw": float(b["raw_mean"][w].mean()), "fund": float(b["fund_mean"][w].mean())}
    say("")

    # ---------------- 12. do nhay MIN_SYM ----------------
    say("## 12. Do nhay MIN_SYM (descriptive)")
    say("")
    say("| MIN_SYM | so moc dung | K=1 | K=3 | K=5 | K=10 |")
    say("|---|---|---|---|---|---|")
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
        say("| %d | %d | %s | %s | %s | %s |" % (ms, len(exx), cells[0], cells[1], cells[2], cells[3]))
    say("")

    # ---------------- 13. MDE ----------------
    say("## 13. MDE80 (%/chu ky 4h, luoi {0,01;0,02;0,05;0,10;0,20;0,50}%) + half-width")
    say("")
    say("| K | MDE80 | p50 half-width | p80 | p95 | N | N_blk |")
    say("|---|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        mde = mde_of(r["net"], r["blk"])
        r["mde80"] = mde["mde80"]
        say("| **%d** | **%s** | %s | %s | %s | %d | %d |"
            % (K, fmt_pct(mde["mde80"]) if mde["mde80"] else ">0,50%", fmt_pct(mde["p50"]),
               fmt_pct(mde["p80"]), fmt_pct(mde["p95"]), r["n"], r["nblk"]))
        NUM["K%d_mde" % K] = {k: v for k, v in mde.items() if k != "power"}
        NUM["K%d_mde" % K]["power"] = mde["power"]
    say("")

    # ---------------- 14. GATE ----------------
    say("## 14. CONG KET LUAN (K_test=%d, Bonferroni p<%.6f)" % (K_TESTS, BONF_P))
    say("")
    say("| K | (1) net>0 | (2) CI x1.21 ngoai 0 | (3) CI-Bonf4 ngoai 0 | (4) >=60%% chu ky duong | (5) |net|>=MDE | (6) khong doi dau ALL | (7) khong doi dau phi 0,15%% | GO? |")
    say("|---|---|---|---|---|---|---|---|---|")
    go_flags = {}
    for K in K_LIST:
        r = main_rows[K]
        mde = r["mde80"]
        c1 = r["obs"] > 0
        c2 = r["ci_lo"] > 0
        c3 = r["b_lo"] > 0
        c4 = r["pos"] >= 0.60
        c5 = (mde is not None) and abs(r["obs"]) >= mde
        c6 = allrows[K]["obs"] > 0
        c7 = r["obs15"] > 0
        g = c1 and c2 and c3 and c4 and c5 and c6 and c7
        go_flags[K] = bool(g)
        say("| **%d** | %s | %s | %s | %s (%.1f%%) | %s | %s | %s (%s) | **%s** |"
            % (K, yn(c1), yn(c2), yn(c3), yn(c4), 100 * r["pos"], yn(c5), yn(c6), yn(c7),
               fmt_pct(r["obs15"]), "GO" if g else "NO-GO"))
        NUM["K%d_gate" % K] = {"c1": bool(c1), "c2": bool(c2), "c3": bool(c3), "c4": bool(c4),
                               "c5": bool(c5), "c6": bool(c6), "c7": bool(c7), "go": bool(g)}
    say("")
    ngo = sum(1 for K in K_LIST if go_flags[K])
    if ngo == len(K_LIST):
        verdict = "GO ca 4 K"
    elif ngo == 0:
        verdict = "NO-GO ca 4 K"
    else:
        verdict = "UNCONFIRMED (post-hoc) — %d/4 K dat, KHONG ap dung" % ngo
    say("**KET LUAN SO BO: %s**" % verdict)
    NUM["verdict_auto"] = verdict
    say("")
    say("### Tom tat so quyet dinh (DEV, phi 0,10%%)")
    say("")
    say("| K | gross (raw - funding) | cost/chu ky | net/chu ky | CI72h x1.21 | turnover |")
    say("|---|---|---|---|---|---|")
    for K in K_LIST:
        r = main_rows[K]
        w = r["w"]
        gross = float((r["b"]["raw_mean"] - r["b"]["fund_mean"])[w].mean())
        say("| **%d** | %s | %s | **%s** | [%s, %s] | %.1f%% |"
            % (K, fmt_pct(gross), fmt_pct(float(r["cost"][w].mean())), fmt_pct(r["obs"]),
               fmt_pct(r["ci_lo"]), fmt_pct(r["ci_hi"]), 100 * float((r["n_in"] / K)[w].mean())))
    say("")
    open(OUT + "/report4h.txt", "w").write("\n".join(rep).replace("%%", "%") + "\n")
    json.dump(NUM, open(OUT + "/numbers4h.json", "w"), indent=1, default=float)
    log.info("report written")


if __name__ == "__main__":
    main()
