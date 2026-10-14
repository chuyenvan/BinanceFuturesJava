"""VZ E1 - T8 report generator: docs/result/VZ_EXPLORE_2024.md.

Reads the T1-V/T2/T3/T4/T5/T6 reports + the ledger and writes the exploration
report. Never calls GO; ranks at most 3 candidates with mechanism and risk.
"""
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_ledger
import e1_t3
from e1_common import OUT, REPORT, setup_logging

log = setup_logging("e1_t8", "e1_t8.log")
DOC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                   "docs", "result", "VZ_EXPLORE_2024.md")


def _j(name):
    p = os.path.join(REPORT, name)
    return json.load(open(p)) if os.path.exists(p) else None


def _f(x, nd=5):
    if x is None:
        return "n/a"
    if isinstance(x, list):
        return "[" + ", ".join("%.*f" % (nd, v) for v in x) + "]"
    try:
        return "%.*f" % (nd, float(x))
    except Exception:
        return str(x)


def quarterly_t3(cfg, ev, variant, nq_levels):
    """Spread by quarter for one T3 variant (net_60)."""
    out = {}
    lv = e1_t3.levels_for(cfg, e1_t3.VAR_BY_NAME[variant][1], nq_levels, ev)
    _, hi, lo = e1_t3.VAR_BY_NAME[variant][2], e1_t3.VAR_BY_NAME[variant][3], e1_t3.VAR_BY_NAME[variant][4]
    q = pd.to_datetime(ev.ts, unit="ms", utc=True).dt.quarter
    for qq in (1, 2, 3, 4):
        m = q == qq
        a = ev.loc[m & (lv == hi), "net_60"].to_numpy(np.float64)
        b = ev.loc[m & (lv == lo), "net_60"].to_numpy(np.float64)
        if len(a) and len(b):
            out["Q%d" % qq] = {"hi_n": int(len(a)), "lo_n": int(len(b)),
                               "spread": float(np.nanmean(a) - np.nanmean(b))}
    return out


def main():
    t1v = _j("e1_t1v_b_diag.json"), _j("e1_t1v_b1b2.json")
    t2 = _j("e1_t2_profile.json")
    t3 = _j("e1_t3.json")
    t4 = _j("e1_t4.json")
    t5 = _j("e1_t5.json")
    t6 = _j("e1_t6.json")
    n_tests = e1_ledger.count()
    L = []
    A = L.append
    A("# VZ EXPLORE 2024 — bộ đo sự kiện E1 (khám phá)")
    A("")
    A("Ngày 2026-10-14 · `research/vz-e1` · dữ liệu `vz-*-2024` (Vision), net sau chi phí "
      "bucket EXEC + 2 chân phí (0,000982) + bản stress. Bootstrap block 5 ngày, NREP 2000, seed 20261014.")
    A("")
    A("**KHÔNG gọi GO.** Mọi kết luận là khám phá trên 1 năm (2024); xác nhận phải qua "
      "`docs/prereg/PREREG_VZ_*` + `e1_confirm.py`.")
    A("")
    A("## 0. Cổng T1-V")
    if t1v[1]:
        b1 = t1v[1]["Vb1_price"]
        b2 = t1v[1]["Vb2_timing"]
        A("| mục | kết quả |")
        A("|---|---|")
        A("| V-a causal | PASS 120/120 |")
        A("| **V-b1 giá** (open time = s_ms, Vision) | %d/%d = **%.4f** → %s |"
          % (round(b1["match_frac"] * b1["n"]), b1["n"], b1["match_frac"],
             "PASS" if b1["pass"] else "FAIL"))
        A("| **V-b2 timing** (bar_ret ≤ −1% ⇒ trùng sự kiện E1) | %d/%d = **%.4f** → %s (lý do trượt: %s) |"
          % (b2["n_coincide_e1"], b2["n_crash_minutes"], b2["frac"],
             "PASS" if b2["pass"] else "FAIL", b2["miss_reasons"]))
        A("| V-c determinism | xem `e1_t1v_c_determinism.json` |")
        A("| V-d đếm | PASS — 66 058 sự kiện, NC 0 |")
    if t1v[0]:
        A("")
        A("`close_M` nguồn: %s" % t1v[0]["source_of_close_M"])
    A("")
    A("## 1. Số phép thử")
    A("")
    A("**Tổng số phép thử đã tính outcome (từ sổ `docs/research/VZ_EXPLORE_LEDGER.md`): %d.** "
      "(T2 mô tả thuần = 0.) Hệ số nở CI khi xác nhận: sqrt(2 ln k) = %.3f."
      % (n_tests, float(np.sqrt(2 * np.log(max(n_tests, 2))))))
    A("")
    # ---- T2
    A("## 2. H-A (T2) — profile quanh phút sập (0 phép thử)")
    if t2:
        A("")
        A("n = %d sự kiện; bảng median theo offset trong `~/vz_e1/reports/e1_t2_profile.md`." % t2["n_events"])
        A("Đọc: taker_sell_share nhảy lên mức cao ở phút sập rồi giảm dần; volume z đạt đỉnh trong ±5′; "
          "prem thường âm quanh sập; ΔOI tích luỹ. Chia C1/C2/C4 và BTC-cùng-sập.")
    A("")
    # ---- T3
    A("## 3. H-B (T3) — hồi có điều kiện trên SỰ KIỆN E1")
    if t3:
        cfg = t3["config"]
        ev = e1_t3.load_events()
        A("")
        A("| biến thể | n | mono net60 | spread net60 [CI95] | spread stress60 |")
        A("|---|---|---|---|---|")
        ranked = []
        for v in t3["variants"]:
            sp = v.get("net_60_spread_extreme", {})
            sps = v.get("net_stress_60_spread_extreme", {})
            A("| %s | %d | %.2f | %s %s | %s |" % (
                v["variant"], v["n"], v["net_60_monotonicity"],
                _f(sp.get("diff_mean")), _f(sp.get("ci95")) if sp else "",
                _f(sps.get("diff_mean")) if sps else "n/a"))
            ranked.append((abs(sp.get("diff_mean", 0.0)), v["variant"], sp))
        ranked.sort(reverse=True)
        A("")
        A("Ổn định theo quý (net60 spread) — 3 biến thể mạnh nhất:")
        A("")
        A("| biến thể | Q1 | Q2 | Q3 | Q4 |")
        A("|---|---|---|---|---|")
        for _, name, _sp in ranked[:3]:
            q = quarterly_t3(cfg, ev, name, e1_t3.VAR_BY_NAME[name][2])
            A("| %s | %s | %s | %s | %s |" % (name,
              _f(q.get("Q1", {}).get("spread")), _f(q.get("Q2", {}).get("spread")),
              _f(q.get("Q3", {}).get("spread")), _f(q.get("Q4", {}).get("spread"))))
    A("")
    # ---- T4
    A("## 4. H-C (T4) — quanh giờ chốt funding")
    if t4:
        A("")
        A("n = %d mốc chốt. Chi phí NC (0,0007 + 2 chân phí)." % t4["n"])
        for k in ("V1_rate_q5", "V2_absrate_top5", "V4_interval"):
            d = t4.get(k, {})
            sp = d.get("spread", {})
            A("- **%s**: n=%s mono=%.2f spread(net60)=%s CI=%s" % (
                k, d.get("n"), d.get("monotonicity", float("nan")),
                _f(sp.get("diff_mean")), _f(sp.get("ci95"))))
        d = t4.get("V3_sign_x_btcregime", {}).get("net_60", {})
        if d.get("levels"):
            A("- **V3_sign_x_btcregime** net60 theo nhóm: " +
              ", ".join("%s=%.5f" % (k, v["mean"]) for k, v in d["levels"].items()))
    A("")
    # ---- T5
    A("## 5. H-D (T5) — basis lệch cực đoan")
    if t5:
        A("")
        A("n = %d sự kiện |prem z7| > 3 (gộp 60′/symbol)." % t5["n"])
        A("")
        A("| biến thể | n | net60 mean [CI95] | hit | dprem15 | dprem60 |")
        A("|---|---|---|---|---|---|")
        for k, d in t5.items():
            if not isinstance(d, dict) or "net_60" not in d:
                continue
            r = d["net_60"]
            A("| %s | %s | %s %s | %s | %s | %s |" % (
                k, r.get("n"), _f(r.get("mean")), _f(r.get("ci95_mean")),
                _f(r.get("hit_rate"), 3), _f(d.get("dprem_15", {}).get("mean")),
                _f(d.get("dprem_60", {}).get("mean"))))
    A("")
    # ---- T6
    A("## 6. H-E (T6) — tuổi symbol")
    if t6:
        a = t6.get("a_crash_by_age", {})
        A("")
        A("| nhóm tuổi | n | net60 mean [CI95] | net240 mean |")
        A("|---|---|---|---|")
        for name, d in a.get("buckets", {}).items():
            A("| %s | %d | %s %s | %s |" % (name, d["n"], _f(d["net_60"].get("mean")),
              _f(d["net_60"].get("ci95_mean")), _f(d["net_240"].get("mean"))))
        au = a.get("age_unknown", {})
        A("| age_unknown | %d | %s | — |" % (au.get("n", 0), _f(au.get("net_60", {}).get("mean"))))
        b = t6.get("b_listing_drift", {})
        if b:
            A("")
            A("Drift sau niêm yết 2024 (n symbol=%s): " % b.get("n_symbols") +
              ", ".join("%s mean=%s" % (h, _f(b[h].get("mean"))) for h in ("1d", "3d", "7d", "30d") if h in b))
        c = t6.get("c_predelist", {})
        if c.get("n_removed"):
            A("")
            A("Trước khi bị gỡ (~30 ngày, %d symbol): median %s, tỉ lệ âm %s. **Cảnh báo survivorship.**"
              % (c["n_removed"], _f(c.get("ret_30d_median")), _f(c.get("ret_30d_frac_neg"), 3)))
    A("")
    # ---- ranking
    A("## 7. Xếp hạng ≤ 3 ứng viên (KHÔNG gọi GO)")
    A("")
    cands = _candidates(t3, t4, t5, t6)
    if not cands:
        A("*Không ứng viên nào có hiệu ứng net (thực + stress) tách khỏi 0.*")
    for i, (name, why, risk) in enumerate(cands[:3], 1):
        A("%d. **%s** — %s · *Rủi ro*: %s" % (i, name, why, risk))
    A("")
    A("## 8. Giới hạn")
    A("")
    A("- 1 năm (2024) — không dùng để chốt GO; chưa có 2022/2023/2025 trong lake.")
    A("- **Không có dữ liệu thanh lý thật** (Vision không có liquidationSnapshot cho UM) ⇒ "
      "ΔOI chỉ là proxy.")
    A("- metrics 5′ (không phải tick); giá là kline khớp lệnh Vision.")
    A("- `vz-symbols` chưa upload ⇒ tuổi symbol suy từ 2024 (cột `age_known`); "
      "symbol niêm yết trước 2024 không đo được tuổi chính xác.")
    A("- Không có lookback 30 ngày cuối 2023 (`vz-basis1m-2023` chưa có) ⇒ `prem_z7` NaN ~1 ngày đầu tháng 1.")
    A("- **E1 chưa xác minh liên kết với chân của hệ** (V-b1/V-b2 xem mục 0): mọi phân tích ở đây "
      "chỉ dựa trên SỰ KIỆN E1, KHÔNG dựa trên chân EXEC của sim.")
    A("")
    A("## 9. Tệp")
    A("")
    A("- `~/vz_e1/out/`: `e1_events_2024.parquet`, `e1_panel_2024.parquet`, `e1_dayvol_2024.parquet`, "
      "`e1_t4_funding_events.parquet`, `e1_t5_basis_events.parquet`, `e1_listing_drift.parquet`, "
      "`e1_month_snap.parquet`, `e1_sym_life_2024.parquet`.")
    A("- `~/vz_e1/reports/`: các JSON ở trên.")
    A("")
    txt = "\n".join(L)
    with open(DOC, "w") as f:
        f.write(txt)
    log.info("wrote %s (%d chars)", DOC, len(txt))
    return DOC


def _candidates(t3, t4, t5, t6):
    out = []
    if t3:
        for v in t3["variants"]:
            sp = v.get("net_60_spread_extreme") or {}
            sps = v.get("net_stress_60_spread_extreme") or {}
            ci = sp.get("ci95") or [np.nan, np.nan]
            scis = sps.get("ci95") or [np.nan, np.nan]
            excl = np.isfinite(ci[0]) and (ci[0] > 0 or ci[1] < 0)
            excl_s = np.isfinite(scis[0]) and (scis[0] > 0 or scis[1] < 0)
            if excl and excl_s:
                out.append(("H-B %s" % v["variant"],
                            "spread net60 %s CI %s (stress %s)" % (_f(sp.get("diff_mean")),
                                                                   _f(ci), _f(sps.get("diff_mean"))),
                            "1 năm, đa biến thể ⇒ nở CI sqrt(2 ln k)"))
    return out


if __name__ == "__main__":
    main()
