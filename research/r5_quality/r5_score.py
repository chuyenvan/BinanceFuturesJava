#!/usr/bin/env python3
"""R5_SIGNAL_QUALITY cham (prereg 200a29a3 §4-§6). Usage: r5_score.py discover | confirm
discover: 2022-23, ghi selection.json (<=2 bien the (b) cao nhat VA > RAW). confirm: 2024-25 CHI cho bien the trong selection.json."""
import json
import logging
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r5score")
G = "/home/ubuntu/claude_master/res1109/r5_quality/"
RES = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/"
SEEDS = ["S42", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
M1, D, TZ, NB, RNG = 60000, 86400000, 7 * 3600000, 2000, 20261112
GAP = 60 * M1
MULTS = (0.25, 0.5, 1.0, 2.0, 4.0)


def load():
    meta = json.load(open(G + "sig_meta.json"))
    Y = pd.read_parquet(G + "out/r5q_y.parquet")[["ts", "y72", "y24"]]
    S = {}
    for s in SEEDS:
        z = np.load(G + "sig_%s.npz" % s)
        df = pd.DataFrame(dict(ts=z["ts"])).merge(Y, on="ts", how="left")
        S[s] = (z["ts"], z["V"], df.y72.to_numpy(), df.y24.to_numpy())
    return meta, S


def topk(v, m, K):
    idx = np.nonzero(m & np.isfinite(v))[0]
    if K >= len(idx):
        return np.sort(idx)
    sel = idx[np.argpartition(-v[idx], K - 1)[:K]]
    return np.sort(sel)


def declust(ts, sel):
    if len(sel) == 0:
        return sel
    t = ts[sel]
    first = np.r_[True, np.diff(t) > GAP]
    return sel[first]


def day_sums(ts, y, sel, days):
    ok = np.isfinite(y[sel])
    d = ((ts[sel][ok] + TZ) // D)
    pos = np.searchsorted(days, d)
    sy = np.bincount(pos, weights=y[sel][ok], minlength=len(days))
    n = np.bincount(pos, minlength=len(days)).astype(float)
    return sy, n


def period_stats(S, vars_, vidx, lo, hi, Kkey, meta, Wb, days, full=True):
    """tra dict bien the -> chi so (a),(b) theo seed + mau bootstrap (b) theo seed."""
    out = {}
    for vn in vars_:
        k = vidx[vn]
        A, Bm, Bb, Ab, B24, nep = [], [], [], [], [], []
        for s in SEEDS:
            ts, V, y72, y24 = S[s]
            m = (ts >= lo) & (ts < hi)
            K = meta["K"][s][Kkey]
            sel = topk(V[:, k], m, K)
            ep = declust(ts, sel)
            nep.append(len(ep))
            for arr, ss in ((A, sel), (Bm, ep)):
                yy = y72[ss]
                arr.append(float(np.nanmean(yy)) if np.isfinite(yy).any() else np.nan)
            B24.append(float(np.nanmean(y24[ep])) if np.isfinite(y24[ep]).any() else np.nan)
            if Wb is not None:
                sy, n = day_sums(ts, y72, ep, days)
                Bb.append((Wb @ sy) / np.maximum(Wb @ n, 1e-12))
                sya, na = day_sums(ts, y72, sel, days)
                Ab.append((Wb @ sya) / np.maximum(Wb @ na, 1e-12))
        out[vn] = dict(a=float(np.nanmean(A)), b=float(np.nanmean(Bm)), b24=float(np.nanmean(B24)), a_seed=A, b_seed=Bm,
                       n_ep=float(np.mean(nep)), boot_b=np.mean(Bb, axis=0) if Bb else None, boot_a=np.mean(Ab, axis=0) if Ab else None)
    return out


def extras(S, vars_, vidx, lo, hi, Kkey, meta):
    ex = {}
    for vn in vars_:
        k = vidx[vn]
        lags, cap, rs_all, rs_top, lift = [], [], [], [], {}
        for s in SEEDS:
            ts, V, y72, _ = S[s]
            m = (ts >= lo) & (ts < hi)
            K = meta["K"][s][Kkey]
            raw_ep = declust(ts, topk(V[:, 0], m, K))
            selv = topk(V[:, k], m, K)
            tv = ts[selv]
            hit, lg = 0, []
            for e in raw_ep:
                j = np.searchsorted(tv, ts[e] - 60 * M1, "left")
                if j < len(tv) and tv[j] <= ts[e] + 240 * M1:
                    hit += 1
                    lg.append((tv[j] - ts[e]) / M1)
            cap.append(hit / max(len(raw_ep), 1))
            if lg:
                lags.append(float(np.median(lg)))
            ok = m & np.isfinite(V[:, k]) & np.isfinite(y72)
            rs_all.append(spearmanr(V[ok, k], y72[ok]).correlation)
            thr = np.nanquantile(V[m, k], 0.95)
            ok5 = ok & (V[:, k] >= thr)
            rs_top.append(spearmanr(V[ok5, k], y72[ok5]).correlation)
            for mu in MULTS:
                sel = topk(V[:, k], m, max(1, int(round(mu * K))))
                ep = declust(ts, sel)
                la, lb = lift.setdefault(mu, ([], []))
                la.append(float(np.nanmean(y72[sel])))
                lb.append(float(np.nanmean(y72[ep])))
        ex[vn] = dict(lag_med=float(np.median(lags)) if lags else None, capture=float(np.mean(cap)),
                      spearman_all=float(np.median(rs_all)), spearman_top5=float(np.median(rs_top)),
                      lift={str(mu): [round(100 * float(np.nanmean(v[0])), 3), round(100 * float(np.nanmean(v[1])), 3)] for mu, v in lift.items()})
    return ex


def boot_weights(lo, hi, S):
    days = np.unique(np.concatenate([(S[s][0][(S[s][0] >= lo) & (S[s][0] < hi)] + TZ) // D for s in SEEDS]))
    rng = np.random.default_rng(RNG)
    Wb = np.stack([np.bincount(rng.integers(0, len(days), len(days)), minlength=len(days)) for _ in range(NB)]).astype(float)
    return days, Wb


def discover():
    meta, S = load()
    vars_ = meta["vars"]
    vidx = {v: i for i, v in enumerate(vars_)}
    lo, hi = YB[2022], YB[2024]
    days, Wb = boot_weights(lo, hi, S)
    st = period_stats(S, vars_, vidx, lo, hi, "disc", meta, Wb, days)
    ex = extras(S, vars_, vidx, lo, hi, "disc", meta)
    raw = st["RAW"]
    rows = {}
    for vn in vars_:
        d = st[vn]["boot_b"] - raw["boot_b"]
        rows[vn] = dict(a_pp=round(100 * st[vn]["a"], 3), b_pp=round(100 * st[vn]["b"], 3), b24_pp=round(100 * st[vn]["b24"], 3),
                        db_pp=round(100 * (st[vn]["b"] - raw["b"]), 3), db_ci90=[round(100 * float(x), 3) for x in np.percentile(d, [5, 95])],
                        da_pp=round(100 * (st[vn]["a"] - raw["a"]), 3), n_ep=st[vn]["n_ep"], **ex[vn])
    cand = sorted([v for v in vars_ if v != "RAW" and st[v]["b"] > raw["b"]], key=lambda v: -st[v]["b"])[:2]
    sel = dict(prereg="200a29a3", period="2022-01-01..2024-01-01 (+07)", selected=cand, rule="(b) cao nhat VA > RAW, toi da 2",
               b_pp={v: rows[v]["b_pp"] for v in vars_}, K={s: meta["K"][s]["disc"] for s in SEEDS})
    json.dump(sel, open(G + "selection.json", "w"), indent=1)
    json.dump(dict(rows=rows, K=sel["K"]), open(G + "discover.json", "w"), indent=1)
    L = ["# R5_SIGNAL_QUALITY — KHÁM PHÁ 2022–23 (prereg 200a29a3) — tự sinh bởi research/r5_quality/r5_score.py", "",
         "Y72 = fwd 72h ròng 0,2 %% rổ top-24 sp; top-K phút theo biến thể, K = số phút B0 pass (TB 8 seed K=%.0f). (a) không khử cụm; (b) đợt ≤60′ lấy phút đầu (CHÍNH). Δ so RAW, CI90 bootstrap ngày 2 000, seed %d. Đơn vị pp." % (np.mean(list(sel["K"].values())), RNG), "",
         "| biến thể | (a) | (b) | Δ(b) [CI90] | số đợt | trễ trung vị (′) | bắt đợt RAW | Spearman toàn/top5 % | (b) Y24 |", "|---|---|---|---|---|---|---|---|---|"]
    for vn in vars_:
        r = rows[vn]
        L.append("| %s | %+.2f | %+.2f | %+.2f [%+.2f; %+.2f] | %.0f | %s | %.2f | %.3f / %.3f | %+.2f |" % (
            vn, r["a_pp"], r["b_pp"], r["db_pp"], r["db_ci90"][0], r["db_ci90"][1], r["n_ep"],
            "-" if r["lag_med"] is None else "%.0f" % r["lag_med"], r["capture"], r["spearman_all"], r["spearman_top5"], r["b24_pp"]))
    L += ["", "**Lựa chọn (commit trước xác nhận):** %s" % (", ".join(cand) if cand else "KHÔNG có biến thể nào > RAW ⇒ ĐÓNG, không chạy xác nhận"), "",
          "Lift (a)/(b) theo K×{0,25;0,5;1;2;4}: xem discover.json."]
    open(RES + "R5_SIGNAL_QUALITY_DISCOVER.md", "w").write("\n".join(L) + "\n")
    log.info("SELECTED %s", cand)


def confirm():
    meta, S = load()
    sel = json.load(open(G + "selection.json"))["selected"]
    vars_ = meta["vars"]
    vidx = {v: i for i, v in enumerate(vars_)}
    use = ["RAW"] + sel
    lo, hi = YB[2024], YB[2026]
    days, Wb = boot_weights(lo, hi, S)
    st = period_stats(S, use, vidx, lo, hi, "conf", meta, Wb, days)
    yr = {y: period_stats(S, use, vidx, YB[y], YB[y + 1], str(y), meta, None, None) for y in (2024, 2025)}
    rows = {}
    for v in sel:
        d = st[v]["boot_b"] - st["RAW"]["boot_b"]
        ci = np.percentile(d, [5, 95])
        dy = {y: 100 * (yr[y][v]["b"] - yr[y]["RAW"]["b"]) for y in yr}
        rows[v] = dict(b_pp=round(100 * st[v]["b"], 3), raw_b_pp=round(100 * st["RAW"]["b"], 3), db_pp=round(100 * (st[v]["b"] - st["RAW"]["b"]), 3),
                       db_ci90=[round(100 * float(x), 3) for x in ci], db_year=dy, a_pp=round(100 * st[v]["a"], 3),
                       DAT=bool(ci[0] > 0 and all(x > 0 for x in dy.values())))
    json.dump(dict(prereg="200a29a3", rows=rows), open(G + "confirm.json", "w"), indent=1)
    L = ["# R5_SIGNAL_QUALITY — XÁC NHẬN 2024–25 (prereg 200a29a3)", "",
         "| biến thể | (b) | RAW (b) | Δ(b) [CI90] | Δ 2024 | Δ 2025 | KẾT |", "|---|---|---|---|---|---|---|"]
    for v, r in rows.items():
        L.append("| %s | %+.2f | %+.2f | %+.2f [%+.2f; %+.2f] | %+.2f | %+.2f | %s |" % (
            v, r["b_pp"], r["raw_b_pp"], r["db_pp"], r["db_ci90"][0], r["db_ci90"][1], r["db_year"][2024], r["db_year"][2025], "ĐẠT" if r["DAT"] else "KHÔNG ĐẠT"))
    concl = "Có biến thể ĐẠT ⇒ MASTER viết prereg Pha 2." if any(r["DAT"] for r in rows.values()) else "Không biến thể nào ĐẠT ⇒ \"p15 thô đã là cách dùng tốt nhất trong thư viện này\", ĐÓNG."
    L += ["", "**Kết luận theo luật:** " + concl]
    open(RES + "R5_SIGNAL_QUALITY_CONFIRM.md", "w").write("\n".join(L) + "\n")
    log.info("CONFIRM %s", rows)


if __name__ == "__main__":
    {"discover": discover, "confirm": confirm}[sys.argv[1]]()
