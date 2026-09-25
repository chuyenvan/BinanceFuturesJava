#!/usr/bin/env python3
"""audit_pnl_label.py — VIỆC 1 của PREREG_AUDIT_PNL: audit ĐỘC LẬP nhãn (b).

  V1a: 200 cặp (t,sym) ngẫu nhiên (SEED_A) -> chạy LẠI exit engine từ bins thô -> so nhãn đã lưu.
  V1b: 200 cặp BỊ BỎ + 200 cặp ĐƯỢC GIỮ (SEED_B1/B2) -> bỏ có làm lệch phân bố `gross` không?
  V1c: 113 dòng OPEN_AT_END xử lý thế nào (theo code) + ảnh hưởng lên mức của rổ.

Chỉ ĐỌC. Không train/sim hệ thống/push.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_pnl_lib as A                       # noqa: E402

os.makedirs(A.OUT, exist_ok=True)
T0 = time.time()
BLOCK_MS = 72 * A.HOUR
NREP, SEED_BOOT = 2000, 20260905


def block_boot_diff(v1, ts1, v2, ts2, nrep=NREP, seed=SEED_BOOT):
    """CI khối-72h của HIỆU 2 mẫu ĐỘC LẬP (bootstrap theo khối, cùng quy ước c3_rates)."""
    b1 = np.asarray(ts1, dtype=np.int64) // BLOCK_MS
    b2 = np.asarray(ts2, dtype=np.int64) // BLOCK_MS
    ids = np.unique(np.concatenate([b1, b2]))
    pos = {b: i for i, b in enumerate(ids)}
    i1 = np.array([pos[x] for x in b1]); i2 = np.array([pos[x] for x in b2])
    n = len(ids)
    s1 = np.bincount(i1, weights=np.asarray(v1, float), minlength=n)
    c1 = np.bincount(i1, minlength=n).astype(float)
    s2 = np.bincount(i2, weights=np.asarray(v2, float), minlength=n)
    c2 = np.bincount(i2, minlength=n).astype(float)
    rng = np.random.default_rng(seed)
    out = np.empty(nrep); k = 0
    while k < nrep:
        sel = rng.integers(0, n, n)
        C1, C2 = c1[sel].sum(), c2[sel].sum()
        if C1 <= 0 or C2 <= 0:
            continue
        out[k] = s1[sel].sum() / C1 - s2[sel].sum() / C2
        k += 1
    return float(out.mean()), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def ci_mean(v, ts, nrep=NREP, seed=SEED_BOOT):
    b = np.asarray(ts, np.int64) // BLOCK_MS
    _, inv = np.unique(b, return_inverse=True)
    s = np.bincount(inv, weights=np.asarray(v, float))
    c = np.bincount(inv).astype(float)
    m = c > 0
    s, c, n = s[m], c[m], int(m.sum())
    rng = np.random.default_rng(seed)
    out = np.empty(nrep)
    for i in range(nrep):
        p = rng.integers(0, len(s), len(s))
        out[i] = s[p].sum() / c[p].sum()
    return float(np.asarray(v, float).mean()), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def q5(x):
    x = np.asarray(x, float)
    return dict(mean=round(float(x.mean()), 6), med=round(float(np.median(x)), 6),
                p05=round(float(np.percentile(x, 5)), 6), p25=round(float(np.percentile(x, 25)), 6),
                p75=round(float(np.percentile(x, 75)), 6), p95=round(float(np.percentile(x, 95)), 6))


def _pair_worker(p):
    """Chạy lại 1 cặp với CỬA SỔ TĂNG DẦN (2 -> 4 -> 6 -> 8-9 ngày).
    CHÍNH XÁC: engine chỉ khác nhau ở nhánh `OPEN_AT_END` (hết mảng); mọi status khác đã CHỐT
    trong cửa sổ ngắn ⇒ mở rộng không đổi kết quả. OPEN_AT_END thật = dữ liệu coin HẾT trong ≤168h.
    """
    d0 = A.day_of(p["ts"])
    days = list(range(d0, d0 + 9))
    bars, k = {}, 2
    while True:
        new = {d: {p["sym"]} for d in days[:k] if d not in bars}
        if new:
            bars.update(A.load_days(list(new), new, workers=1))
        arr, miss = A.assemble(bars, p["sym"], days[:k])
        if arr is None:
            return dict(p, replay_ok=False, miss_days=len(miss), days_read=k)
        r = A.replay(p["sym"], arr[0], arr[1], p["ts"])
        if r is None:
            return dict(p, replay_ok=False, miss_days=len(miss), days_read=k)
        if r["status"] != "OPEN_AT_END" or k >= 9:
            return dict(p, replay_ok=True, miss_days=len(miss), days_read=k,
                        **{"replay_" + kk: v for kk, v in r.items()})
        k = min(k + 2, 9)


def run_pairs(pairs, tag):
    """pairs: list[dict(sym, ts, ...)]. Song song theo CẶP (4 lõi), cửa sổ tăng dần."""
    A.log("%s: %d cặp (cửa sổ tăng dần, 4 lõi)", tag, len(pairs))
    out = []
    with Pool(4) as pool:
        for i, r in enumerate(pool.imap_unordered(_pair_worker, pairs, chunksize=1)):
            out.append(r)
            if i % 25 == 0:
                A.log("  %s %d/%d (%.0fs)", tag, i + 1, len(pairs), time.time() - T0)
    n_none = sum(1 for r in out if not r.get("replay_ok"))
    A.log("%s: xong (no-entry=%d) %.0fs", tag, n_none, time.time() - T0)
    return out


def main():
    lab = A.load_label()
    lab = lab.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    res = {"meta": {"n_label": len(lab), "sha_label_note": "label_b_pnl.parquet 309024 dòng",
                    "seeds": {"A": A.SEED_A, "B1": A.SEED_B1, "B2": A.SEED_B2, "C": A.SEED_C},
                    "windows": "day(t)..day(t)+8", "engine": "exitfit/exit_engine.make_p0(), pred=None",
                    "block_h": 72, "nrep": NREP, "seed_boot": SEED_BOOT}}

    # ---------------- V1a ----------------
    PARTIAL = os.path.join(A.OUT, "label_partial.json")
    rng = np.random.default_rng(A.SEED_A)
    idx = rng.choice(len(lab), 200, replace=False)
    s = lab.iloc[np.sort(idx)]
    pairs = [dict(row=int(i), sym=r.sym, ts=int(r.ts), symId=int(r.symId),
                  gross_label=float(r.gross), tp_label=float(r.tp), E_label=float(r.E),
                  status_label=r.status, exit_label=int(r.exit_ts), hold_label=int(r.hold_min))
             for i, r in zip(np.sort(idx), s.itertuples())]
    if os.path.exists(PARTIAL):
        res["V1a"] = json.load(open(PARTIAL))["V1a"]
        A.log("V1a: dùng lại kết quả đã lưu (%s)", PARTIAL)
    else:
        R = run_pairs(pairs, "V1a")
        ok = [r for r in R if r.get("replay_ok")]
        dg = np.array([r["replay_gross"] - r["gross_label"] for r in ok])
        exact = np.array([abs(r["replay_tp"] - r["tp_label"]) < 1e-12
                          and r["replay_exit_ts"] == r["exit_label"] for r in ok])
        match_status = np.array([r["replay_status"] == r["status_label"] for r in ok])
        dgr = np.array([r["replay_gross"] for r in ok])
        gl = np.array([r["gross_label"] for r in ok])
        sl = np.array([r["status_label"] for r in ok])
        sub = lab.iloc[[r["row"] for r in ok]]
        year = pd.to_datetime(sub.ts.to_numpy(), unit="ms", utc=True).year.to_numpy()
        res["V1a"] = {
            "n_sample": len(R), "n_replay_ok": len(ok),
            "delta_gross": q5(dg),
            "abs_delta_gross": q5(np.abs(dg)),
            "frac_exact_tp_and_exit": float(exact.mean()),
            "frac_status_match": float(match_status.mean()),
            "frac_abs_delta_lt_1e-9": float((np.abs(dg) < 1e-9).mean()),
            "spearman": float(pd.Series(dgr).corr(pd.Series(gl), method="spearman")),
            "frac_delta_pos": float((dg > 0).mean()),
            "by_year": {int(y): dict(n=int((year == y).sum()),
                                     med=round(float(np.median(dg[year == y])), 6),
                                     mean=round(float(dg[year == y].mean()), 6))
                        for y in np.unique(year)},
            "by_status": {s_: dict(n=int((sl == s_).sum()),
                                  med=round(float(np.median(dg[sl == s_])), 6))
                          for s_ in sorted(set(sl.tolist()))},
            "verdict": ("DUNG" if abs(np.median(dg)) <= 1e-4 and exact.mean() >= 0.90 else "SAI"),
        }
        json.dump({"V1a": res["V1a"]}, open(PARTIAL, "w"), indent=1, default=str)

    # ---------------- V1b ----------------
    cand = A.candidates_frame()
    mask, n_drop, info = A.dropped_days(cand)
    lab_keys = set(zip(lab.ts.to_numpy(), lab.symId.to_numpy()))
    keep_keys = set(zip(cand.ts.to_numpy()[~mask], cand.symId.to_numpy()[~mask]))
    smap = pd.read_csv(A.MAP_CSV)[["symId", "symbol"]]
    cand = cand.merge(smap, on="symId", how="left")
    res["V1b_gate"] = {"n_cand": int(len(cand)), "n_dropped_pairs": int(n_drop),
                       "pct_dropped": round(100.0 * n_drop / len(cand), 3),
                       "keep_key_set_equals_label": bool(keep_keys == lab_keys),
                       "n_unmapped_sym": int(cand.symbol.isna().sum()),
                       "intervals": info}

    lab_gross = dict(zip(zip(lab.ts.to_numpy(), lab.symId.to_numpy()), lab.gross.to_numpy()))
    D = cand[mask].dropna(subset=["symbol"])
    K = cand[~mask].dropna(subset=["symbol"])
    rd = np.random.default_rng(A.SEED_B1).choice(len(D), 200, replace=False)
    rk = np.random.default_rng(A.SEED_B2).choice(len(K), 200, replace=False)
    Pd = [dict(sym=r.symbol, ts=int(r.ts), symId=int(r.symId)) for r in D.iloc[np.sort(rd)].itertuples()]
    Pk = [dict(sym=r.symbol, ts=int(r.ts), symId=int(r.symId),
               gross_label=lab_gross.get((int(r.ts), int(r.symId)))) for r in K.iloc[np.sort(rk)].itertuples()]
    Rd = run_pairs(Pd, "V1b-dropped")
    Rk = run_pairs(Pk, "V1b-kept")
    okd = [r for r in Rd if r.get("replay_ok")]
    okk = [r for r in Rk if r.get("replay_ok")]
    vd = np.array([r["replay_gross"] for r in okd]); td = np.array([r["ts"] for r in okd])
    vk = np.array([r["replay_gross"] for r in okk]); tk = np.array([r["ts"] for r in okk])
    vkl = np.array([r["gross_label"] for r in okk], float)
    mb, lo, hi = block_boot_diff(vd, td, vk, tk)
    md = ci_mean(vd, td); mk = ci_mean(vk, tk)
    res["V1b"] = {
        "dropped": dict(n=len(okd), gross=q5(vd), pos_rate=round(float((vd > 0).mean()), 4),
                        ci95_raw=[round(md[1], 6), round(md[2], 6)],
                        status={s_: int(sum(1 for r in okd if r["replay_status"] == s_))
                                for s_ in sorted(set(r["replay_status"] for r in okd))}),
        "kept": dict(n=len(okk), gross=q5(vk), pos_rate=round(float((vk > 0).mean()), 4),
                     ci95_raw=[round(mk[1], 6), round(mk[2], 6)],
                     status={s_: int(sum(1 for r in okk if r["replay_status"] == s_))
                             for s_ in sorted(set(r["replay_status"] for r in okk))}),
        "diff_dropped_minus_kept": dict(mean=round(mb, 6), ci95_raw=[round(lo, 6), round(hi, 6)],
                                        outside_ci=bool(lo > 0 or hi < 0)),
        "kept_replay_vs_label_median": round(float(np.median(vk - vkl)), 6) if vkl.size else None,
    }

    # ---------------- V1c ----------------
    oa = lab[lab.status == "OPEN_AT_END"]
    res["V1c"] = {
        "n": int(len(oa)), "pct_of_pool": round(100.0 * len(oa) / len(lab), 4),
        "handling": ("mark-to-market: price_tp = close(nến CUỐI mảng bars); status='OPEN_AT_END'; "
                     "KHÔNG bỏ dòng (exit_engine.simulate, nhánh exit_ts is None)"),
        "gross": q5(oa.gross.to_numpy()),
        "hold_min_mean": float(oa.hold_min.mean()),
        "gross_all_pool": round(float(lab.gross.mean()), 6),
        "gross_excl_openend": round(float(lab[lab.status != "OPEN_AT_END"].gross.mean()), 6),
    }
    json.dump(res, open(os.path.join(A.OUT, "label.json"), "w"), indent=1, default=str)
    A.log("WRITE %s/label.json  (%.0fs)", A.OUT, time.time() - T0)
    print(json.dumps({k: res[k] for k in ("V1a",) if k in res}, indent=1, default=str)[:1500])


if __name__ == "__main__":
    main()
