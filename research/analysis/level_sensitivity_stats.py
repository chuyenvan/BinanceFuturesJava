#!/usr/bin/env python3
"""LEVEL_SENSITIVITY stats — luoi 9 o (HOLD x phi) cho BIG_UP/MEDIUM_UP/MEDIUM_DOWN (+ MOM15 ref),
tren 3 pool (M-LEVEL / P-COIN / P-COIN-DEDUP), CI block-72h x1.21 + Bonferroni K=27, null sign-flip,
ICC, va MDE cho N moi.

Doc /tmp/level_sens/pools.npz. Thuan Python. Pre-reg: docs/PREREG_LEVEL_SENSITIVITY.md.
"""
import os
import sys
from datetime import datetime, timezone

import numpy as np

OUT = os.environ.get("LVL_OUT", "/tmp/level_sens")
SEED = 20260905
NREP = 2000
NREP_MDE_OUTER = 2000
NREP_MDE_INNER = 200
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
K_TESTS = 27                      # 3 signal x 9 o (pool P-COIN, DEV) — PREREG §6
ALPHA = 0.05
BONF_P = ALPHA / K_TESTS          # 0.001852 (mot phia)
BONF_PCT = [100 * BONF_P / 2, 100 * (1 - BONF_P / 2)]   # [0.0926, 99.9074]
MDE_GRID = [0.0002, 0.0005, 0.0010, 0.0020, 0.0025, 0.0050, 0.0100, 0.0200, 0.0400]
MDE_N_GRID = [200, 500, 1000, 5000, 20000, 100000]
LEVELS = {1: "BIG_UP", 3: "MEDIUM_UP", 4: "MEDIUM_DOWN", 8: "MOM15"}
DECISION = (1, 3, 4)
UTC = timezone.utc
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)

rep = []


def say(s=""):
    rep.append(s)


class Chain:
    """Chuoi net -> (sum, count) theo block 72h; bootstrap resample block."""

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


def ci_from_means(means, inflate=CI_INFLATE):
    obs = means.mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    half = (hi - lo) / 2.0 * inflate
    return obs, lo, hi, half


def summ(net, blk, seed=SEED):
    c = Chain(net, blk)
    means = c.boot_means(seed=seed)
    obs, lo, hi, half = ci_from_means(means)
    blo, bhi = np.percentile(means, BONF_PCT)
    return {
        "n": len(net), "nblk": c.nb, "obs": obs, "lo": lo, "hi": hi,
        "ci_lo": obs - half, "ci_hi": obs + half, "half": half,
        "p_gt0": float((means > 0).mean()), "p_le0": float((means <= 0).mean()),
        "b_lo": blo, "b_hi": bhi, "means": means,
    }


def block_signflip(net, blk, seed=SEED):
    bc, bi = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(NREP, len(bc)))
    bs = np.bincount(bi, weights=net)
    null = (signs @ bs) / len(net)
    return float(net.mean()), float(null.mean()), float(null.std()), float((null >= net.mean()).mean())


def icc(net, gid):
    gid, inv = np.unique(gid, return_inverse=True)
    a = len(gid)
    ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    cnt = np.bincount(inv, minlength=a).astype(np.float64)
    sums = np.bincount(inv, weights=net, minlength=a)
    mi = sums / cnt
    gm = net.mean()
    msb = (cnt * (mi - gm) ** 2).sum() / (a - 1)
    within = net - mi[inv]
    msw = (within ** 2).sum() / (ni - a)
    k0 = (ni - (cnt ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def mde_of(net, blk, seed=SEED, nouter=NREP_MDE_OUTER, ninner=NREP_MDE_INNER):
    """PREREG §8: center chain, moi rep -> nua-do-rong h_r (bootstrap long nhau), power(X)=P(h_r<X)."""
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


def fmt_pct(x):
    return "%.4f%%" % (100 * x) if np.isfinite(x) else "nan"


def grid_table(pool_name, minute, sym, net0, lvl, valid, holds, fee_grid, window_mask, label, moc=None):
    """In luoi 9 o cho tung signal. net0 = raw - slip - fund (chua tru phi)."""
    say("")
    say("### LƯỚI 9 Ô — pool %s — %s" % (pool_name, label))
    say("(ô neo 24h/0.10% = harness 3 vòng trước; p_gt0 = tỉ lệ rep bootstrap có mean>0)")
    say("")
    say("| signal | HOLD | phí | N | N_blk | meanNet | CI72h×1.21 | p(>0) | CI-Bonf27 | sống? (x1.21 / Bonf27) |")
    say("|---|---|---|---|---|---|---|---|---|---|")
    for lv in DECISION + (8,):
        for hd in holds:
            j = holds.index(hd)
            v = (valid >> j) & 1
            sel = (lvl == lv) & (v == 1) & np.isfinite(net0[j])
            if window_mask is not None:
                sel = sel & window_mask
            if sel.sum() < 3:
                say("| %s | %dh | — | %d | — | — | — | — | — | n quá nhỏ |" % (LEVELS[lv], hd // 60, int(sel.sum())))
                continue
            net = net0[j][sel]
            blk = (minute[sel] // BLOCK_MIN).astype(np.int64)
            s = summ(net, blk)
            if moc is not None:
                moc[(lv, hd)] = s
            for fee in fee_grid:
                obs = s["obs"] - fee
                lo = s["ci_lo"] - fee
                hi = s["ci_hi"] - fee
                blo = s["b_lo"] - fee
                bhi = s["b_hi"] - fee
                p_gt0 = float((s["means"] - fee > 0).mean())
                p_le0 = 1.0 - p_gt0
                alive_b = "**CÓ**" if blo > 0 else "-"
                alive_l = "CÓ" if lo > 0 else "-"
                sig_col = LEVELS[lv] if fee == fee_grid[0] else ""
                hold_col = "%dh" % (hd // 60) if fee == fee_grid[0] else ""
                say("| %s | %s | %.2f%% | %d | %d | **%s** | [%s, %s] | %.3f (p_le0=%.5f) | [%s, %s] | x1.21:%s / Bonf27:%s |" % (
                    sig_col, hold_col, 100 * fee, s["n"], s["nblk"], fmt_pct(obs), fmt_pct(lo),
                    fmt_pct(hi), p_gt0, p_le0, fmt_pct(blo), fmt_pct(bhi), alive_l, alive_b))


def main():
    z = np.load(OUT + "/pools.npz")
    holds = [int(x) for x in z["holds"]]
    fee_grid = [float(x) for x in z["fee_grid"]]
    BASE = int(z["base"])
    pc_min = z["pc_min"]
    pc_sym = z["pc_sym"]
    pc_lvl = z["pc_lvl"]
    pc_raw = z["pc_raw"]
    pc_slip = z["pc_slip"]
    pc_fund = z["pc_fund"]
    pc_valid = z["pc_valid"]
    ml_idx = z["ml_idx"]
    ml_min = z["ml_min"]
    ml_sym = z["ml_sym"]
    ml_lvl = z["ml_lvl"]

    net0_pc = [pc_raw[j].astype(np.float64) - pc_slip.astype(np.float64) - pc_fund[j].astype(np.float64)
               for j in range(len(holds))]

    # ---- P-COIN-DEDUP: 1 event / (sym, block-72h) TRONG TUNG SIGNAL, lay phut fire som nhat ----
    blk_all = (pc_min // BLOCK_MIN).astype(np.int64)
    dd_parts = []
    for lv in DECISION + (8,):
        idx = np.flatnonzero(pc_lvl == lv)
        o = idx[np.lexsort((pc_min[idx], blk_all[idx], pc_sym[idx]))]
        b = blk_all[o]
        s = pc_sym[o]
        f = np.ones(len(o), dtype=bool)
        f[1:] = (b[1:] != b[:-1]) | (s[1:] != s[:-1])
        dd_parts.append(o[f])
    dd_idx = np.concatenate(dd_parts)

    # ---- M-LEVEL: tai su dung returns cua P-COIN qua ml_idx ----
    pools = {
        "P-COIN": (pc_min, pc_sym, pc_lvl, pc_valid, net0_pc),
        "M-LEVEL": (ml_min, ml_sym, ml_lvl, pc_valid[ml_idx],
                    [n[ml_idx] for n in net0_pc]),
        "DEDUP": (pc_min[dd_idx], pc_sym[dd_idx], pc_lvl[dd_idx], pc_valid[dd_idx],
                  [n[dd_idx] for n in net0_pc]),
    }

    dev = (pc_min >= DEV_START) & (pc_min < DEV_END)
    devs = {k: (v[0] >= DEV_START) & (v[0] < DEV_END) for k, v in pools.items()}

    say("=== LEVEL_SENSITIVITY — N (market-level vs per-coin) + lưới 9 ô (HOLD × phí) + MDE ===")
    say("pre-reg docs/PREREG_LEVEL_SENSITIVITY.md (commit b88f467, chot TRUOC khi chay). Harness nguyen:")
    say("HOLD×(4h/24h/72h) × phí(0.05/0.10/0.15%), slip 0.5×range + funding Aerospike; CI block-72h 2000 rep")
    say("seed 20260905 ×1.21; null sign-flip 72h; DEV = 2022-01-01..2025-12-31 (CHÍNH), ALL = 2021-01..2025-12 (PHỤ, gồm 2021).")
    say("")
    say("## 0. N và N_eff (block 72h)")
    say("")
    say("| pool | signal | N ALL | N_eff ALL | N DEV | N_eff DEV | N/N_eff DEV |")
    say("|---|---|---|---|---|---|---|")
    for pk, (mn, ms, ml, mv, nn) in pools.items():
        for lv in DECISION + (8,):
            w = ml == lv
            nA = int(w.sum())
            nD = int((w & devs[pk]).sum())
            bA = len(np.unique(mn[w] // BLOCK_MIN))
            bD = len(np.unique(mn[w & devs[pk]] // BLOCK_MIN))
            say("| %s | %s | %d | %d | %d | %d | %.1f |" % (
                pk, LEVELS[lv], nA, bA, nD, bD, (nD / bD if bD else float("nan"))))

    # ---- kiem chung dang thuc dich hang so (PREREG §11 / §8) ----
    say("")
    say("## 0b. Kiểm chứng đẳng thức dịch hằng số (PREREG §8): CI_lo(X=1%) == CI_lo(0) + 1%")
    maxerr = 0.0
    for lv, hd in ((1, 1440), (4, 1440), (8, 1440)):
        j = holds.index(hd)
        sel = (pools["P-COIN"][2] == lv) & (((pools["P-COIN"][3] >> j) & 1) == 1)
        net = pools["P-COIN"][4][j][sel]
        blk = (pools["P-COIN"][0][sel] // BLOCK_MIN).astype(np.int64)
        for sd in (SEED, SEED + 7, SEED + 99):
            for shift in (0.0, 0.01):
                c = Chain(net - net.mean() + shift, blk)
                m = c.boot_means(nrep=200, seed=sd)
                lo = np.percentile(m, 2.5)
                if shift == 0.0:
                    lo0 = lo
                else:
                    maxerr = max(maxerr, abs(lo - (lo0 + 0.01)))
    say("  sai khớp max = %.3e (yêu cầu < 1e-9) ⇒ %s" % (maxerr, "ĐẠT" if maxerr < 1e-9 else "**VOID**"))

    # ---- luoi 9 o: P-COIN (HEADLINE) ----
    for win_name, wmask, key in (("DEV (CHÍNH)", dev, "dev"), ("ALL (PHỤ, gồm 2021)", None, "all")):
        mn, ms, ml, mv, nn = pools["P-COIN"]
        wm = dev if wmask is not None else None
        say("")
        say("## 1%s. P-COIN — lưới 9 ô (%s)" % ("" if key == "dev" else "b", win_name))
        grid_table("P-COIN", mn, ms, nn, ml, mv, holds, fee_grid, wm, win_name)

    # ---- luoi cho M-LEVEL va DEDUP (DEV + ALL gon) ----
    for pk in ("M-LEVEL", "DEDUP"):
        mn, ms, ml, mv, nn = pools[pk]
        say("")
        say("## 2. %s — lưới 9 ô" % pk)
        grid_table(pk, mn, ms, nn, ml, mv, holds, fee_grid, devs[pk], "DEV (CHÍNH)")

    # ---- null / ICC / %coin+ / theo nam (P-COIN, o neo 24h/0.10%) ----
    say("")
    say("## 3. Null test (block sign-flip 72h) + ICC + %coin+ + theo năm — P-COIN, ô neo 24h/0.10%, DEV")
    j = holds.index(1440)
    mn, ms, ml, mv, nn = pools["P-COIN"]
    for lv in DECISION + (8,):
        sel = (ml == lv) & (((mv >> j) & 1) == 1) & np.isfinite(nn[j]) & dev
        if sel.sum() < 3:
            continue
        net = nn[j][sel] - 0.0010
        mm = mn[sel]
        blk = (mm // BLOCK_MIN).astype(np.int64)
        day = (mm + 420) // 1440
        o, nm, ns, pv = block_signflip(net, blk)
        say("")
        say("**%s** (N=%d, N_blk=%d): meanNet=%.4f%% | null(mean=%.5f%%, sd=%.5f%%) p(>=obs)=%.4f | ICC(day)=%.4f ICC(72h)=%.4f" % (
            LEVELS[lv], int(sel.sum()), len(np.unique(blk)), net.mean() * 100, nm * 100, ns * 100, pv,
            icc(net, day), icc(net, blk)))
        uniq, inv = np.unique(ms[sel], return_inverse=True)
        cnt = np.bincount(inv)
        sm = np.bincount(inv, weights=net)
        cmean = sm / cnt
        for mt in (1, 5, 10):
            ok = cnt >= mt
            if ok.any():
                say("  %%coin+ (>=%d trade): nsym=%d %.1f%%" % (mt, int(ok.sum()), 100 * (cmean[ok] > 0).mean()))
        yr = np.array([datetime.utcfromtimestamp(int(x) * 86400).year for x in (mm + 420) // 1440])
        for y in sorted(set(yr.tolist())):
            w = yr == y
            say("  Y%d: N=%d meanNet=%.4f%%" % (y, int(w.sum()), net[w].mean() * 100))

    # ---- selection contribution (descriptive) ----
    say("")
    say("## 4. Selection contribution (descriptive): mean(net) M-LEVEL − mean(net) P-COIN, cùng phút fire")
    say("(tầng phút: mỗi phút fire lấy mean(net) của 2 coin được chọn − mean(net) của toàn pool)")
    for lv in DECISION:
        sel_pc = (ml == lv) & (((mv >> j) & 1) == 1) & dev
        sel_ml = (pools["M-LEVEL"][2] == lv) & (((pools["M-LEVEL"][3] >> j) & 1) == 1) & devs["M-LEVEL"]
        if sel_pc.sum() < 5 or sel_ml.sum() < 5:
            continue
        mins_pc = mn[sel_pc]
        net_pc = nn[j][sel_pc] - 0.0010
        mins_ml = pools["M-LEVEL"][0][sel_ml]
        net_ml = pools["M-LEVEL"][4][j][sel_ml] - 0.0010
        g = {}
        for m_, v_ in zip(mins_pc.tolist(), net_pc.tolist()):
            g.setdefault(m_, []).append(v_)
        pm = {k: float(np.mean(v)) for k, v in g.items()}
        h = {}
        for m_, v_ in zip(mins_ml.tolist(), net_ml.tolist()):
            h.setdefault(m_, []).append(v_)
        common = [m_ for m_ in h if m_ in pm]
        if not common:
            continue
        d = np.array([np.mean(h[m_]) - pm[m_] for m_ in common])
        blk_c = (np.array(common) // BLOCK_MIN).astype(np.int64)
        s = summ(d, blk_c)
        say("  %s: n_min=%d diff=%s CI72h×1.21=[%s, %s] p(>0)=%.3f  (M-LEVEL sel=%.4f%% vs P-COIN pool=%.4f%%)" % (
            LEVELS[lv], len(common), fmt_pct(s["obs"]), fmt_pct(s["ci_lo"]), fmt_pct(s["ci_hi"]),
            s["p_gt0"], np.mean([np.mean(h[m_]) for m_ in common]) * 100,
            np.mean([pm[m_] for m_ in common]) * 100))

    # ---- C. MDE ----
    say("")
    say("## 5. C. MDE cho N mới (DEV, ô HOLD tương ứng) — %/lệnh")
    say("MDE(80%) = X nhỏ nhất trong lưới {0.02,0.05,0.1,0.2,0.25,0.5,1,2,4}% có power>=80%.")
    say("Đẳng thức: phát hiện ⟺ X > h_r (h_r = nửa-độ-rộng CI72h×1.21 của chuỗi center).")
    say("LƯU Ý: MDE bất biến theo phí (phí = dịch hằng số) ⇒ cùng giá trị cho cả 3 ô phí.")
    say("")
    say("| pool | signal | HOLD | N | N_blk | h_r p50 | h_r p80 | h_r p95 | power@0.1% | @0.25% | @0.5% | @1% | MDE(80%) |")
    say("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for pk in ("P-COIN", "M-LEVEL", "DEDUP"):
        mn_, ms_, ml_, mv_, nn_ = pools[pk]
        for lv in DECISION + (8,):
            for hd in holds:
                jj = holds.index(hd)
                sel = (ml_ == lv) & (((mv_ >> jj) & 1) == 1) & np.isfinite(nn_[jj]) & devs[pk]
                if sel.sum() < 5:
                    continue
                net = nn_[jj][sel]
                blk = (mn_[sel] // BLOCK_MIN).astype(np.int64)
                r = mde_of(net, blk)
                say("| %s | %s | %dh | %d | %d | %s | %s | %s | %.2f | %.2f | %.2f | %.2f | **%s** |" % (
                    pk, LEVELS[lv], hd // 60, int(sel.sum()), len(np.unique(blk)),
                    fmt_pct(r["p50"]), fmt_pct(r["p80"]), fmt_pct(r["p95"]),
                    r["power"][0.0010], r["power"][0.0025], r["power"][0.0050], r["power"][0.0100],
                    ("%.2f%%" % (100 * r["mde80"])) if r["mde80"] else ">4%"))

    say("")
    say("### 5b. Đường MDE theo N (lấy mẫu con không lặp, 200 rep/N, DEV, chuỗi P-COIN 24h)")
    say("")
    say("| signal | " + " | ".join("N=%d" % n for n in MDE_N_GRID) + " |")
    say("|---|" + "---|" * len(MDE_N_GRID))
    mn_, ms_, ml_, mv_, nn_ = pools["P-COIN"]
    jj = holds.index(1440)
    for lv in DECISION + (8,):
        sel = (ml_ == lv) & (((mv_ >> jj) & 1) == 1) & devs["P-COIN"]
        net = nn_[jj][sel]
        blk = (mn_[sel] // BLOCK_MIN).astype(np.int64)
        if len(net) < 50:
            continue
        cells = []
        for n in MDE_N_GRID:
            if n > len(net):
                cells.append("n/a")
                continue
            rng = np.random.default_rng(SEED)
            hs = []
            for r in range(200):
                idx = rng.choice(len(net), size=n, replace=False)
                c = Chain(net[idx] - net[idx].mean(), blk[idx])
                m = c.boot_means(nrep=200, seed=SEED + r)
                lo, hi = np.percentile(m, [2.5, 97.5])
                hs.append((hi - lo) / 2 * CI_INFLATE)
            hp80 = float(np.percentile(hs, 80))
            mde = next((X for X in MDE_GRID if 100 * hp80 <= 100 * X), None)
            cells.append("h80=%.3f%%→%s" % (100 * hp80, ("%.2f%%" % (100 * mde)) if mde else ">4%"))
        say("| %s | " % LEVELS[lv] + " | ".join(cells) + " |")

    say("")
    say("### 5c. MDE của cửa sổ DEV cũ (2022-01..2024-06) trên chính chuỗi này (so số đã công bố)")
    say("")
    say("| signal | N(DEV cũ) | h_r p80 | MDE(80%) |")
    say("|---|---|---|---|")
    dev_old_end = int(datetime(2024, 7, 1, tzinfo=UTC).timestamp() // 60)
    for pk in ("M-LEVEL", "P-COIN"):
        mn_, ms_, ml_, mv_, nn_ = pools[pk]
        for lv in DECISION:
            sel = (ml_ == lv) & (((mv_ >> jj) & 1) == 1) & (mn_ >= DEV_START) & (mn_ < dev_old_end)
            if sel.sum() < 5:
                continue
            net = nn_[jj][sel]
            blk = (mn_[sel] // BLOCK_MIN).astype(np.int64)
            r = mde_of(net, blk, nouter=500)
            say("| %s | %s | %d | %s | **%s** |" % (pk, LEVELS[lv], int(sel.sum()), fmt_pct(r["p80"]),
                                                    ("%.2f%%" % (100 * r["mde80"])) if r["mde80"] else ">4%"))

    txt = "\n".join(rep)
    os.makedirs(OUT, exist_ok=True)
    open(OUT + "/report.txt", "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
