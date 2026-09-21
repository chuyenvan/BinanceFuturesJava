"""BREADTH_ROBUST (round moi giao boi Uni/MASTER 2026-09-21, VALIDATE_BREADTH_ROBUST) - kiem tra
tinh ROBUST cua ket luan breadth-regime (dinh nghia A, TASK B2 Buoc 5.2/5.3/6) khi doi universe
(top-30/50/100 theo symId thu tu niem yet, PROXY, VA all-coin-song - toan bo coin co close tai t)
va tham so (MA in {100,200}, nguong "yeu" in {40%,50%,60%}). HOAN TOAN 0-sim: KHONG chay Java,
KHONG xgboost, KHONG build, KHONG sua .java. Day la VALIDATE ROBUSTNESS, KHONG phai chon cau hinh
dep nhat - bao TAT CA to hop, KHONG nhat winner.

Tai dung NGUYEN VAN (khong sua):
  - research/analysis/trend_rank_ic.load_closes() (CLOSES_1H.bin, loc ts<2026-01-01 = HOLDOUT)
  - research/analysis/breadth_regime.py: day_id, build_daily_close_by_sym, up_matrix,
    breadth_from_up_matrix, pct_notup_by_year, window_pct_notup, gate_verdict, cac hang so
    SIM0/SIM1/UW2022/UW2025/MIN_PERIODS_FLOOR/GATE_THRESHOLD_PCT/SYM_BTC/SYM_ETH/DAY_MS

Phan 1: sweep top-30/50/100/all-coin x MA{100,200} x nguong{40,50,60}% - bang day du %notup/nam
  (2021-2025) + %phu UW-2022/UW-2025 cho CA 24 to hop.
Phan 2: chuoi breadth_score(t) lien tuc (causal) cho 2 cau hinh chinh: all-coin/MA200 va
  top50/MA200. Xuat CSV. Minh hoa anh xa score->gate (gate_up=1.0/gate_down=1.7/thr=50%,
  cong thuc MASTER de nghi trong nhiem vu) cho vai ngay mau + thong ke UW2022/UW2025/2023/2024.
Phan 3: ket luan proxy co du tot khong dua tren do robust cua Phan 1.

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/breadth_robust.py
Ghi: research/analysis/out/breadth_robust.json, research/analysis/out/breadth_score_series.csv
"""
import csv
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa: E402
import breadth_regime as BR  # noqa: E402  (tai dung day_id/up_matrix/... , KHONG sua file nay)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("breadth_robust")

OUT_JSON = os.path.join(HERE, "out", "breadth_robust.json")
OUT_CSV = os.path.join(HERE, "out", "breadth_score_series.csv")

SWEEP_MA = (100, 200)
SWEEP_THR = (40.0, 50.0, 60.0)

# minh hoa gate lien tuc (Phan 2) - cong thuc MASTER de nghi trong nhiem vu, KHONG phai sim that
GATE_UP = 1.0     # gate khi breadth_score >= thr (long, giong dinh nghia A/BR truoc)
GATE_DOWN = 1.7   # gate khi breadth_score -> 0 (chat nhat, giong dinh nghia A/BR truoc)
GATE_THR_SCORE = 0.5  # = THRESHOLD_MAIN/100 cua dinh nghia A


def continuous_gate(score, gate_up=GATE_UP, gate_down=GATE_DOWN, thr=GATE_THR_SCORE):
    if score is None or not np.isfinite(score):
        return None
    x = np.clip((thr - score) / thr, 0.0, 1.0)
    return float(gate_up + (gate_down - gate_up) * x)


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== BREADTH_ROBUST: nap CLOSES_1H.bin (toan bo symId) ===")
    df = T.load_closes()
    all_symids_present = sorted(int(s) for s in df["sym"].unique())
    log.info("Tong so symId co du lieu (ts<2026-01-01): %d (min=%d max=%d)",
             len(all_symids_present), min(all_symids_present), max(all_symids_present))

    daily_by_sym = BR.build_daily_close_by_sym(df, all_symids_present)

    day0, day1 = BR.day_id(BR.SIM0), BR.day_id(BR.SIM1)
    day_range = np.arange(day0, day1 + 1)
    log.info("SIM range %s..%s = %d ngay", BR.SIM0, BR.SIM1, len(day_range))

    universes = {
        "top30": [s for s in all_symids_present if s <= 30],
        "top50": [s for s in all_symids_present if s <= 50],
        "top100": [s for s in all_symids_present if s <= 100],
        "all": all_symids_present,
    }
    for lbl, syms in universes.items():
        log.info("universe %s: %d symId", lbl, len(syms))

    result = {"meta": dict(sim0=BR.SIM0, sim1=BR.SIM1, uw2022=list(BR.UW2022), uw2025=list(BR.UW2025),
                            gate_threshold_pct=BR.GATE_THRESHOLD_PCT,
                            n_symid_total=len(all_symids_present),
                            sweep_universe=list(universes.keys()), sweep_ma=list(SWEEP_MA),
                            sweep_thr=list(SWEEP_THR),
                            note="all=all-coin-song (toan bo symId co close tai t, khong gioi han "
                                 "topN); top30/50/100 = symId 1..N theo thu tu niem yet (PROXY, "
                                 "giong Buoc 5.2/6)")}

    # ---------------- so coin song / ngay theo universe (kiem ty le phu doi theo nam) ----------------
    alive_count_by_universe_year = {}
    alive_mat_cache = {}
    for lbl, syms in universes.items():
        up_mat200, alive_mat = BR.up_matrix(daily_by_sym, syms, day_range, 200)
        alive_mat_cache[(lbl, 200)] = (up_mat200, alive_mat)
        n_alive = alive_mat.sum(axis=1)
        dates_tmp = pd.to_datetime(day_range.astype(np.int64) * BR.DAY_MS, unit="ms")
        s = pd.Series(n_alive, index=dates_tmp)
        by_year = {str(y): dict(min=int(g.min()), median=float(g.median()), max=int(g.max()))
                   for y, g in s.groupby(s.index.year)}
        alive_count_by_universe_year[lbl] = by_year
        log.info("so coin song/ngay (universe=%s, MA200 alive_mat): %s", lbl, by_year)
    result["alive_count_by_universe_year"] = alive_count_by_universe_year

    # ---------------- Phan 1: sweep day du ----------------
    sweep_rows = []
    robust_count = 0
    per_universe_pass = {lbl: 0 for lbl in universes}
    for lbl, syms in universes.items():
        for ma_w in SWEEP_MA:
            if (lbl, ma_w) in alive_mat_cache:
                up_mat, _ = alive_mat_cache[(lbl, ma_w)]
            else:
                up_mat, _ = BR.up_matrix(daily_by_sym, syms, day_range, ma_w)
            breadth, n_valid = BR.breadth_from_up_matrix(up_mat)
            for thr in SWEEP_THR:
                notup = breadth < thr
                by_year = BR.pct_notup_by_year(notup, day_range)
                c22 = BR.window_pct_notup(notup, day_range, *BR.UW2022)
                c25 = BR.window_pct_notup(notup, day_range, *BR.UW2025)
                gv = BR.gate_verdict("%s/MA%d/thr%.0f" % (lbl, ma_w, thr), c22, c25)
                if gv["go"]:
                    robust_count += 1
                    per_universe_pass[lbl] += 1
                row = dict(universe=lbl, n_symid=len(syms), ma_window=ma_w, threshold_pct=thr,
                           pct_notup_by_year={y: by_year[y]["pct_notup"] for y in sorted(by_year)},
                           pct_notup_uw2022=c22["pct_notup"], pct_notup_uw2025=c25["pct_notup"],
                           go=gv["go"])
                sweep_rows.append(row)
                log.info("universe=%-6s MA=%3d thr=%4.0f%%  UW2022=%6s  UW2025=%6s  GO=%s  notup/nam=%s",
                          lbl, ma_w, thr,
                          "None" if c22["pct_notup"] is None else "%.1f" % c22["pct_notup"],
                          "None" if c25["pct_notup"] is None else "%.1f" % c25["pct_notup"],
                          gv["go"], row["pct_notup_by_year"])
    result["sweep_full"] = sweep_rows
    result["robust_summary"] = dict(n_combo_total=len(sweep_rows), n_combo_go=robust_count,
                                     per_universe_pass=per_universe_pass,
                                     per_universe_total=len(SWEEP_MA) * len(SWEEP_THR))
    log.info("=== ROBUST SUMMARY: %d/%d to hop GO (>=60%% ca UW2022 lan UW2025); theo universe: %s ===",
              robust_count, len(sweep_rows), per_universe_pass)

    # ---------------- Phan 2: chuoi breadth-score lien tuc (2 cau hinh chinh) ----------------
    log.info("=== Phan 2: chuoi breadth_score(t) causal, 2 cau hinh chinh (all-coin/MA200, top50/MA200) ===")
    up_all, _ = alive_mat_cache[("all", 200)]
    breadth_all, nvalid_all = BR.breadth_from_up_matrix(up_all)
    up_t50, _ = alive_mat_cache[("top50", 200)]
    breadth_t50, nvalid_t50 = BR.breadth_from_up_matrix(up_t50)

    score_all = breadth_all / 100.0
    score_t50 = breadth_t50 / 100.0
    dates = pd.to_datetime(day_range.astype(np.int64) * BR.DAY_MS, unit="ms")

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "day_id", "breadth_score_allcoin", "n_valid_allcoin",
                    "breadth_score_top50", "n_valid_top50",
                    "gate_allcoin_ma200", "gate_top50_ma200"])
        for i, d in enumerate(day_range):
            sa = score_all[i] if np.isfinite(score_all[i]) else None
            st = score_t50[i] if np.isfinite(score_t50[i]) else None
            w.writerow([dates[i].strftime("%Y-%m-%d"), int(d),
                        "" if sa is None else "%.6f" % sa, int(nvalid_all[i]),
                        "" if st is None else "%.6f" % st, int(nvalid_t50[i]),
                        "" if sa is None else "%.4f" % continuous_gate(sa),
                        "" if st is None else "%.4f" % continuous_gate(st)])
    log.info("Da ghi chuoi breadth-score -> %s (%d dong)", OUT_CSV, len(day_range))

    def window_score_stats(score_arr, start, end):
        d0, d1 = BR.day_id(start), BR.day_id(end)
        m = (day_range >= d0) & (day_range <= d1)
        v = score_arr[m]
        v = v[np.isfinite(v)]
        if len(v) == 0:
            return None
        gates = np.array([continuous_gate(x) for x in v])
        return dict(n=int(len(v)), score_mean=float(v.mean()), score_median=float(np.median(v)),
                    gate_mean=float(gates.mean()), gate_median=float(np.median(gates)))

    def year_score_stats(score_arr, year):
        m = (dates.year == year)
        v = score_arr[m]
        v = v[np.isfinite(v)]
        if len(v) == 0:
            return None
        gates = np.array([continuous_gate(x) for x in v])
        return dict(n=int(len(v)), score_mean=float(v.mean()), score_median=float(np.median(v)),
                    gate_mean=float(gates.mean()), gate_median=float(np.median(gates)))

    windows_stats = {}
    for cfg_lbl, arr in (("all_ma200", score_all), ("top50_ma200", score_t50)):
        windows_stats[cfg_lbl] = dict(
            uw2022=window_score_stats(arr, *BR.UW2022),
            uw2025=window_score_stats(arr, *BR.UW2025),
            y2023=year_score_stats(arr, 2023),
            y2024=year_score_stats(arr, 2024),
        )
        log.info("gate-mapping stats [%s]: UW2022=%s UW2025=%s 2023=%s 2024=%s", cfg_lbl,
                  windows_stats[cfg_lbl]["uw2022"], windows_stats[cfg_lbl]["uw2025"],
                  windows_stats[cfg_lbl]["y2023"], windows_stats[cfg_lbl]["y2024"])
    result["gate_mapping_window_stats"] = windows_stats

    # vai ngay mau (2022 sau, 2025 chop, 2023/24 khoe) - chon thu cong theo boi canh biet truoc,
    # bao dung so tinh duoc, khong chinh sua de dep
    sample_dates = ["2022-06-18", "2022-11-09", "2025-04-07", "2025-06-15", "2025-08-05",
                     "2023-08-15", "2023-11-15", "2024-03-01", "2024-07-15"]
    day_to_pos = {int(d): i for i, d in enumerate(day_range)}
    sample_rows = []
    for ds in sample_dates:
        pos = day_to_pos.get(BR.day_id(ds))
        if pos is None:
            continue
        sa = score_all[pos] if np.isfinite(score_all[pos]) else None
        st = score_t50[pos] if np.isfinite(score_t50[pos]) else None
        sample_rows.append(dict(date=ds,
                                 breadth_score_allcoin=sa,
                                 gate_allcoin=None if sa is None else continuous_gate(sa),
                                 breadth_score_top50=st,
                                 gate_top50=None if st is None else continuous_gate(st)))
        log.info("ngay mau %s: score_all=%s gate_all=%s | score_top50=%s gate_top50=%s", ds,
                  sa, None if sa is None else continuous_gate(sa), st,
                  None if st is None else continuous_gate(st))
    result["sample_days_gate_mapping"] = sample_rows
    result["gate_formula"] = dict(formula="gate(t)=gate_up+(gate_down-gate_up)*clip((thr-score(t))/thr,0,1)",
                                   gate_up=GATE_UP, gate_down=GATE_DOWN, thr_score=GATE_THR_SCORE,
                                   note="MASTER de xuat trong nhiem vu, minh hoa CHUA sim; "
                                        "thr=50% giong dinh nghia A")

    # ---------------- Phan 3: ket luan proxy ----------------
    ma200_rows = [r for r in sweep_rows if r["ma_window"] == 200]
    ma200_go = sum(1 for r in ma200_rows if r["go"])
    all_ma200_rows = [r for r in ma200_rows if r["universe"] == "all"]
    all_ma200_go = sum(1 for r in all_ma200_rows if r["go"])
    result["proxy_verdict"] = dict(
        ma200_all_combo_go="%d/%d" % (ma200_go, len(ma200_rows)),
        all_coin_ma200_go="%d/%d" % (all_ma200_go, len(all_ma200_rows)),
        note="xem docs/VALIDATE_BREADTH_ROBUST.md Phan 3 cho ket luan chi tiet")
    log.info("=== PHAN 3 proxy: MA200 (moi universe) GO %d/%d to hop; rieng all-coin/MA200 GO %d/%d ===",
              ma200_go, len(ma200_rows), all_ma200_go, len(all_ma200_rows))

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s , %s", OUT_JSON, OUT_CSV)


if __name__ == "__main__":
    main()
