#!/usr/bin/env python3
"""Render docs/result/LOB_VERIFY.md and LOB_T1.md from the Kaggle JSON outputs."""
import json
import os

A = json.load(open(os.path.expanduser("~/claude_master/lob/out/A/verify_a.json")))
Bp = os.path.expanduser("~/claude_master/lob/out/B/t1.json")
B = json.load(open(Bp)) if os.path.exists(Bp) else None
REPO = os.path.expanduser("~/claude_master/vz_e1_wt")
PREV_ROWS = {"BNBUSDT.csv": 3851648, "BTCUSDT.csv": 6018702, "ETHUSDT.csv": 5926882,
             "SOLUSDT.csv": 4510657, "XRPUSDT.csv": 3827972}


def f(x, n=2, dash="—"):
    if x is None:
        return dash
    try:
        if x != x:
            return dash
    except Exception:
        pass
    return f"{x:,.{n}f}"


a1 = A["sections"].get("A1", {})
a2 = A["sections"].get("A2", {})
a3 = A["sections"].get("A3", {})
a4 = A["sections"].get("A4", {})
a5 = A["sections"].get("A5", {})

L = []
L.append("# LOB_VERIFY — kiểm + sàng dataset LOB Kaggle `alpha000x/crypto-lob-data`\n")
L.append("Ngày 2026-10-23. Kernel: **`chuyendinh/lob-verify-a`** (script kernel, CPU, private, "
         "internet ON chỉ để tải kline tĩnh `data.binance.vision`). Toàn bộ dữ liệu nặng chạy trên "
         "Kaggle; Oracle không tải dataset về (0 byte).\n")
L.append(f"- Thời gian kernel: **{A.get('total_sec')} s** "
         f"(A1 {A['timing_sec'].get('A1')} s, A2 {A['timing_sec'].get('A2')} s, "
         f"A3 {A['timing_sec'].get('A3')} s, A4 {A['timing_sec'].get('A4')} s)\n")

L.append("## A1. Metadata\n")
L.append("| file | GB | dòng (không kể header) | cột |")
L.append("|---|---|---|---|")
for r in a1.get("files", []):
    rows = r.get("rows_excl_header")
    note = ""
    if rows is None:
        rows = PREV_ROWS.get(r["name"])
        note = " *(đếm ở run v3, file byte-identical)*"
    L.append(f"| {r['name']} | {r['gb']:,.2f} | {rows:,}{note} | {r['n_columns']} |")
L.append(f"\nTổng **{a1.get('total_gb')} GB**, {a1.get('n_columns')} cột = 3 meta "
         f"(`event_ts_ms`, `recv_ts_ns`, `update_id`) + **{a1.get('n_levels')} level** mỗi bên "
         f"(`bid_px_i`, `bid_qty_i`, `ask_px_i`, `ask_qty_i`, i = 1..100). Không có cột thời gian "
         f"dạng ngày: thời gian chỉ có trong `event_ts_ms` (ms UTC) và `recv_ts_ns` (ns).\n")

L.append("## A2. Toàn vẹn — quét TOÀN BỘ `BNBUSDT.csv`\n")
L.append("| kiểm | giá trị |")
L.append("|---|---|")
for k, lbl in [("rows", "số dòng"), ("first_utc", "bắt đầu (UTC)"), ("last_utc", "kết thúc (UTC)"),
               ("nonmono_ts", "`event_ts` không tăng"), ("dup_ts", "`event_ts` trùng"),
               ("uid_nonmono", "`update_id` giảm"), ("uid_dup", "`update_id` trùng"),
               ("crossed", "bid1 > ask1 (crossed)"), ("locked", "bid1 = ask1 (locked)"),
               ("neg_qty", "qty âm"), ("zero_px", "px ≤ 0"),
               ("bid_mono_bad", "bid không giảm dần theo level"),
               ("ask_mono_bad", "ask không tăng dần theo level"),
               ("nan_cells_20lvl", "ô NaN trong 20 level"),
               ("elapsed_sec", "thời gian quét (s)")]:
    L.append(f"| {lbl} | {a2.get(k)} |")
sp = a2.get("spread_bps", {})
gp = a2.get("gap_ms", {})
lg = a2.get("lag_ms", {})
mn = a2.get("minutes", {})
L.append(f"\n- Spread (bps): median **{f(sp.get('p50'), 4)}**, p5 {f(sp.get('p5'), 4)}, "
         f"p95 {f(sp.get('p95'), 4)}, p99 {f(sp.get('p99'), 4)}, max {f(sp.get('max'), 3)} "
         f"→ đúng 1 tick 0,01 USDT trên giá ~750 (0,01/750 = 0,133 bps).")
L.append(f"- Nhịp update: median **{f(gp.get('p50'), 0)} ms**, p95 {f(gp.get('p95'), 0)}, "
         f"p99 {f(gp.get('p99'), 0)}, p99,9 {f(gp.get('p999'), 0)}, max {f(gp.get('max'), 0)} ms; "
         f"~{mn.get('rows_per_min_p50', 0):,.0f} dòng/phút.")
L.append(f"- Trễ `recv_ts_ns − event_ts_ms`: median **{f(lg.get('p50'), 1)} ms**, p95 {f(lg.get('p95'), 1)}, "
         f"p99 {f(lg.get('p99'), 1)}, min {f(lg.get('min'), 2)} ms, **tỉ lệ âm {f(lg.get('neg_frac'), 4)}** "
         f"(không có record nào nhận trước khi xảy ra).")
L.append(f"- Phủ phút: **{mn.get('n'):,} phút** liên tục {mn.get('first_utc')} → {mn.get('last_utc')}, "
         f"lỗ hổng > 1 phút: **{mn.get('gaps_gt1')}** (gap lớn nhất {mn.get('gap_max')} phút).")
L.append(f"- Độ sâu L1: bid median {f(a2.get('depth_b1', {}).get('p50'), 3)}, "
         f"ask median {f(a2.get('depth_a1', {}).get('p50'), 3)} (đơn vị BNB).\n")

L.append("## A3. Toàn vẹn mẫu 4 symbol còn lại (3 cửa sổ byte đầu/giữa/cuối)\n")
L.append("| file | cửa sổ | dòng | crossed | locked | nonmono_ts | dup_ts | bid_mono_bad | ask_mono_bad |")
L.append("|---|---|---|---|---|---|---|---|---|")
for r in a3.get("files", []):
    for w in r.get("windows", []):
        if w.get("rows") is None:
            L.append(f"| {r['file']} | {w['label']} | lỗi đọc mẫu | | | | | | |")
            continue
        L.append(f"| {r['file']} | {w['label']} | {w.get('rows', 0):,} | {w.get('crossed')} | "
                 f"{w.get('locked')} | {w.get('nonmono_ts')} | {w.get('dup_ts')} | "
                 f"{w.get('bid_mono_bad')} | {w.get('ask_mono_bad')} |")
L.append(f"\nMỗi cửa sổ {a3.get('window_bytes', 0)/2**20:.0f} MB (≈ 15–20 nghìn dòng) — đủ để phát hiện "
         f"lỗi cấu trúc; **không** quét toàn bộ 4 file lớn (80,6 GB) để tiết kiệm thời gian kernel.\n")

L.append("## A4. Đối chiếu mid với Binance Vision (kline 1m, file tĩnh)\n")
L.append("| thị trường | phút khớp | dev median (bps) | |dev| p50 | |dev| p95 | |dev| p99 | "
         "|dev|>1bps | demeaned |dev| p50 | corr return 1m |")
L.append("|---|---|---|---|---|---|---|---|---|")
for mkt, m in a4.get("markets", {}).items():
    d = m.get("dev_bps", {})
    L.append(f"| {mkt} | {m.get('n_matched', 0):,} | {f(d.get('median'), 3)} | {f(d.get('abs_p50'), 3)} | "
             f"{f(d.get('abs_p95'), 3)} | {f(d.get('abs_p99'), 3)} | "
             f"{f((d.get('frac_abs_gt_1bps') or 0)*100, 1)} % | {f(d.get('demeaned_abs_p50'), 4)} | "
             f"{f(d.get('ret_corr_1m'), 5)} |")
L.append("\n`dev` = (mid cuối phút − close kline 1m)/close·1e4. `demeaned` = dev trừ median (loại basis "
         "không đổi). `corr return 1m` = tương quan log-return phút của mid và của close kline — đại lượng "
         "**nhận diện thị trường** vì basis hằng số bị triệt tiêu.\n")

if a5:
    L.append("## A5. Kết luận Phase A\n")
    c = a5.get("criteria", {})
    L.append("| điều kiện chạy B | đạt |")
    L.append("|---|---|")
    names = {"no_nan_l1_5": "không NaN ở L1–L5", "crossed_plus_locked_zero": "crossed + locked = 0",
             "ts_monotonic_no_dup": "ts tăng, không trùng", "vision_match": "khớp Vision ≤ 1 bps / p95 ≤ 5 bps",
             "minute_coverage_ge_90pct": "phủ phút ≥ 90 %, không lỗ hổng"}
    for k, v in c.items():
        L.append(f"| {names.get(k, k)} | {'✅' if v else '❌'} |")
    L.append(f"\nThị trường khớp nhất: **{a5.get('best_market')}** (|dev| p50 "
             f"{f(a5.get('best_abs_p50_bps'), 3)} bps). `run_B_allowed` = **{a5.get('run_B_allowed')}**.\n")

L.append("## A6. Kết luận Phase A — dùng được cho gì\n")
L.append("**Đạt.** Dataset là **order book spot** (không phải futures) 100 level, snapshot ~100 ms, "
         "7,0 ngày (2026-10-06 → 2026-10-13), 5 symbol, 95,01 GB. Trên BNBUSDT (3,85 M dòng, 10.081 phút "
         "liên tục, 0 lỗ hổng): **0 lỗi cấu trúc** (0 crossed/locked/NaN/ts-dup/level-đảo), spread = 1 tick, "
         "và mid phút khớp kline spot Vision tới **0,067 bps tuyệt đối / 0,0027 bps sau khi trừ basis**, "
         "corr return 1m 0,9989. 4 symbol còn lại sạch trên 12 cửa sổ mẫu (≈ 0,20 M dòng).\n")
L.append("**Dùng được cho:**\n")
L.append("- Nghiên cứu microstructure spot: imbalance L1–L5, OFI, microprice, depth slope; horizon 1 s – 15 phút.")
L.append("- Sinh feature/label cho ML trên book 100 level (độ sâu đủ để tính slope tới 100 bậc).")
L.append("- So sánh 5 symbol (BNB/BTC/ETH/SOL/XRP) cùng khung thời gian, cùng định dạng.")
L.append("- Kiểm tra tính khả thi kinh tế của market-making/mean-reversion tần suất cao ở mức **sàng lọc**.\n")
L.append("**KHÔNG dùng được cho:**\n")
L.append("- Backtest chiến lược cần **book futures** (USDT-M) — book ở đây là spot; basis futures ~2,6 bps.")
L.append("- Mô phỏng **queue position / fill của maker**: chỉ có snapshot cách nhau ~100 ms, không có "
         "từng event add/cancel/trade, không có số thứ tự hàng đợi.")
L.append("- Phân tích **trade flow / adverse selection** (không có trade prints, không có aggressor side).")
L.append("- Kết luận về mùa vụ/regime dài hạn: **7 ngày** là mẫu ngắn, chỉ gồm 1 tuần tháng 10/2026.")
L.append("- Bất kỳ so sánh với dữ liệu 2020 (niêm phong) hay suy rộng sang thanh khoản 2021–2024.\n")

open(os.path.join(REPO, "docs/result/LOB_VERIFY.md"), "w").write("\n".join(L) + "\n")
print("wrote LOB_VERIFY.md")

# ---------------------------------------------------------------- LOB_T1.md
if not B:
    print("no t1.json yet")
    raise SystemExit(0)

H = []
H.append("# LOB_T1 — tín hiệu order book spot BNBUSDT: IC ngoài mẫu và chi phí\n")
H.append(f"Prereg: `docs/prereg/PREREG_LOB_T1.md` @ `{B.get('prereg_commit')}` (commit trước khi đo). "
         f"Kernel: **`chuyendinh/lob-t1-signals`**, CPU, {B.get('input_gb')} GB CSV, "
         f"{B.get('timing_sec')} s.\n")
g = B.get("grid", {})
H.append(f"- Grid 1 s: **{g.get('n_seconds'):,} giây** {g.get('first_utc')} → {g.get('last_utc')}, "
         f"tỉ lệ giây có observation {f((g.get('obs_frac') or 0)*100, 2)} %.")
H.append(f"- Chia: discovery {g.get('n_seconds_disc'):,} s (60 %) → test {g.get('n_seconds_test'):,} s (40 %), "
         f"mốc chia **{g.get('split_utc')}**.")
spd = B.get("spread_bps", {})
H.append(f"- Spread book: median **{f(spd.get('p50'), 4)} bps**, p10 {f(spd.get('p10'), 4)}, p90 {f(spd.get('p90'), 4)}.")
H.append(f"- Chi phí áp: taker {B['costs_bps_roundtrip']['taker']:.0f} bps / vòng, "
         f"maker {B['costs_bps_roundtrip']['maker']:.0f} bps / vòng (mỗi chiều 5 / 2 bps).\n")

SIG = ["imb1", "imb5", "ofi1", "micro_bps", "slope_imb", "depth_bps5"]
H.append("## 1. IC / R² / decile theo horizon (chỉ số trên TEST)\n")
H.append("| signal | h | IC disc | IC test | NW t | R² OOS | decile D10−D1 (bps) | net taker | net maker |")
H.append("|---|---|---|---|---|---|---|---|---|")
for hz in ["1s", "10s", "60s", "300s", "900s"]:
    res = B["results"].get(hz, {})
    for s in SIG:
        r = res.get(s, {})
        if "skip" in r:
            H.append(f"| {s} | {hz} | — | — | — | — | — | — | — |")
            continue
        H.append(f"| {s} | {hz} | {f(r['ic_disc'], 4)} | {f(r['ic_test'], 4)} | {f(r['nw_t'], 1)} | "
                 f"{f(r['r2_oos'], 5)} | {f(r['spread_top_minus_bottom_bps'], 3)} | "
                 f"{f(r['strat_net_taker_bps'], 2)} | {f(r['strat_net_maker_bps'], 2)} |")
H.append("")

H.append("## 2. Theo regime (h = 10 s, test)\n")
H.append("| signal | vol thấp | vol cao | phút sập |")
H.append("|---|---|---|---|")
reg = B.get("regime", {})
for s in SIG:
    lo = reg.get("vol_lo", {}).get(s, {}).get("ic")
    hi = reg.get("vol_hi", {}).get(s, {}).get("ic")
    cr = reg.get("crash", {}).get(s, {}).get("ic")
    H.append(f"| {s} | {f(lo, 4)} | {f(hi, 4)} | {f(cr, 4)} |")
H.append(f"\nNgưỡng phút sập |return 1m| ≥ {f(reg.get('crash', {}).get('threshold_abs_1m_bps'), 2)} bps "
         f"(phân vị 99,9 của discovery), chiếm {f((reg.get('crash', {}).get('frac_test') or 0)*100, 3)} % số giây test. "
         f"n giây: vol thấp {reg.get('vol_lo', {}).get('_n_seconds')}, vol cao {reg.get('vol_hi', {}).get('_n_seconds')}.\n")

H.append("## 3. Kiểm hợp lệ\n")
v = B.get("validation", {})
v1 = v.get("V1_placebo_shuffled_returns", {})
v2 = v.get("V2_random_signal", {})
H.append("| kiểm | kết quả |")
H.append("|---|---|")
H.append(f"| V1 placebo (return xáo trộn, 3 lần) | IC gốc {f(v1.get('ic_observed'), 4)}; |IC| xáo trộn max "
         f"{f(v1.get('max_abs'), 4)} |")
H.append(f"| V2 control ngẫu nhiên (10 vector) | mean {f(v2.get('mean'), 5)}, sd {f(v2.get('sd'), 5)} "
         f"(lý thuyết {f(v2.get('theoretical_sd'), 5)}), n {v2.get('n'):,} |")
H.append(f"| V3 IC theo ngày (`imb1`, 10 s) | xem bảng dưới |")
H.append(f"| V4 số học chi phí | {'PASS' if v.get('V4_cost_arithmetic', {}).get('check') else 'FAIL'} |")
v5 = v.get("V5_counts", {})
H.append(f"| V5 số mẫu | n_1s {v5.get('n_1s'):,} (kỳ vọng {v5.get('expected_1s'):,}), n_60s {v5.get('n_60s'):,} |")
v6 = v.get("V6_recompute", {})
H.append(f"| V6 parse độc lập (csv thuần vs pandas) | max|Δimb1| {f(v6.get('max_abs_diff_imb'), 10)}, "
         f"max|Δmicro| {f(v6.get('max_abs_diff_micro'), 10)} trên {v6.get('n'):,} dòng |")
v7 = v.get("V7_quarter_stability_imb1_h10", [])
if v7:
    H.append(f"| V7 ổn định 4 quý của test (`imb1`, 10 s) | " +
             ", ".join(f"Q{d['quarter']} {f(d['ic'], 3)}" for d in v7) + " |")
H.append("\n| ngày UTC | IC imb1 (10 s) | n |")
H.append("|---|---|---|")
for d in v.get("V3_daywise_ic_imb1_h10", []):
    H.append(f"| {d['day_utc']} | {f(d['ic'], 4)} | {d['n']:,} |")
H.append("")

H.append("## 4. Phân bố feature (toàn bộ grid)\n")
H.append("| signal | p1 | median | p99 | autocorr(1 s) |")
H.append("|---|---|---|---|---|")
for s, d in B.get("distribution", {}).items():
    H.append(f"| {s} | {f(d['p1'], 4)} | {f(d['p50'], 4)} | {f(d['p99'], 4)} | {f(d['autocorr_1s'], 3)} |")
H.append("")

# verdict per prereg §6
def verdict():
    hits = {}
    for hz, res in B["results"].items():
        for s, r in res.items():
            if "skip" in r:
                continue
            g1 = abs(r["ic_test"]) >= 0.02 and abs(r["nw_t"]) >= 3 and (r["ic_test"] * r["ic_disc"] > 0)
            g3days = 0
            if s == "imb1" and hz == "10s":
                g3days = sum(1 for d in v.get("V3_daywise_ic_imb1_h10", [])
                             if d["ic"] * (1 if r["ic_test"] > 0 else -1) > 0)
            if g1:
                hits.setdefault(hz, []).append((s, r["ic_test"], r["nw_t"],
                                                r["strat_net_taker_bps"], r["strat_net_maker_bps"]))
    return hits


hits = verdict()
H.append("## 5. Kết luận theo luật prereg §6\n")
H.append("**G1** (`|IC_test| ≥ 0,02`, `|NW t| ≥ 3`, cùng dấu discovery) đạt ở:")
if hits:
    for hz, lst in hits.items():
        H.append(f"- h = {hz}: " + "; ".join(f"`{s}` IC {f(ic, 4)} (t {f(t, 1)})" for s, ic, t, n, m in lst))
else:
    H.append("- **Không** feature nào đạt G1.")
H.append("")
H.append("**G2** (`net_taker > 0`): **không feature nào, ở bất kỳ horizon nào**. "
         "Net taker tốt nhất trong toàn bộ 30 ô (6 signal × 5 horizon) là "
         f"**{f(max(r['strat_net_taker_bps'] for res in B['results'].values() for r in res.values() if 'skip' not in r), 2)} bps**.")
H.append("")
H.append("**G3** (prereg: dấu IC đúng ≥ 5/7 ngày): test chỉ phủ **4 ngày** (10–13/10), nên luật 7 ngày "
         "**không áp dụng nguyên văn được** — ghi nhận `imb1` đúng dấu **4/4** ngày "
         f"(IC {', '.join(f(d['ic'], 3) for d in v.get('V3_daywise_ic_imb1_h10', []))}).")
H.append("")
best_maker = max(((hz, s, r["strat_net_maker_bps"], r["nw_t"]) for hz, res in B["results"].items()
                  for s, r in res.items() if "skip" not in r), key=lambda x: x[2])
H.append(f"**KẾT LUẬN: NO-GO.** Không cấu hình nào đạt G1+G2 ⇒ không đạt \"GO (tradeable with taker)\". "
         f"Với maker: ô có net maker cao nhất là `{best_maker[1]}` @ {best_maker[0]} = "
         f"**{f(best_maker[2], 2)} bps**, nhưng NW t = {f(best_maker[3], 1)} (không đạt G1) và đây là "
         f"hiệu ứng thanh khoản không có dấu tiên nghiệm ⇒ **không đủ cơ sở cho GO-maker-only**; "
         f"các tín hiệu literature mạnh (imb1/imb5/micro) vẫn âm sau phí maker ở mọi horizon.")
H.append("")
H.append("Tín hiệu **có thật và mạnh về thống kê** (IC 0,30 ở 10 s, t 57, placebo 0,003, 4/4 ngày đúng dấu, "
         "decile đơn điệu), nhưng gross chỉ 0,56–3,4 bps trong khi một vòng lệnh tốn 4–10 bps ⇒ "
         "**chi phí lớn hơn edge 3–18 lần**. Đây là bài toán chi phí, không phải bài toán dự báo.")
H.append("")

H.append("## 6. Vì sao IC rất cao mà vẫn không trade được\n")
H.append("| h | gross D10−D1 tốt nhất (bps) | net taker (−10 bps) | net maker (−4 bps) |")
H.append("|---|---|---|---|")
for hz in ["1s", "10s", "60s", "300s", "900s"]:
    res = B["results"].get(hz, {})
    cand = [(s, r) for s, r in res.items() if "skip" not in r and s != "depth_bps5"]
    if not cand:
        continue
    s, r = max(cand, key=lambda kv: kv[1]["strat_gross_bps"])
    H.append(f"| {hz} | `{s}` {f(r['strat_gross_bps'], 2)} | {f(r['strat_net_taker_bps'], 2)} | "
             f"{f(r['strat_net_maker_bps'], 2)} |")
H.append("")
H.append("(`depth_bps5` @900 s có gross +5,1 bps nhưng NW t = −1,6 ⇒ không đáng tin, không đưa vào bảng.)\n")
H.append("Edge **tăng theo horizon** (0,56 bps ở 1 s → ~3,4 bps ở 900 s) nhưng **chi phí là hằng số "
         "theo vòng lệnh**, nên mọi horizon đều âm sau phí taker; ngay cả sau phí maker 2 bps/chiều, mọi horizon "
         "vẫn âm (−0,6 bps ở 900 s đến −3,4 bps ở 1 s). Nói cách khác: tín hiệu **có thật** (IC 0,30 ở 10 s, decile đơn điệu, "
         "placebo ~0, IC đúng dấu ở 4/4 ngày test) nhưng **quá nhỏ so với phí** — đây là bài toán chi phí, "
         "không phải bài toán dự báo.")
H.append("")
H.append("Ghi chú quan trọng: book là **spot**, nên giả định 5 bps taker / 2 bps maker là **lạc quan** "
         "(spot Binance retail là 10 bps/side; 2 bps maker là mức futures/VIP cao). Ngoài ra mô hình decile "
         "giả định **khớp được ở giá tốt nhất**, không mô phỏng xác suất fill và adverse selection của maker "
         "⇒ net maker trong bảng là **cận trên**.")
H.append("")
H.append("## 7. Cần gì để kiểm chắc hơn (và chi phí)\n")
H.append("| thiếu gì | tại sao cần | cách lấy | chi phí ước tính |")
H.append("|---|---|---|---|")
H.append("| Event-level book (add/cancel/trade) hoặc L2 diff | mô phỏng queue position + fill maker, "
         "tính adverse selection thật | thu forward bằng WS `depth@100ms` + `trade` trên box; hoặc mua "
         "dữ liệu L2 lịch sử | tự thu: 0 phí license nhưng cần ~1–2 GB/ngày/symbol (Oracle chỉ còn ~16 GB "
         "⇒ phải dùng object storage); mua: vài chục–vài trăm USD/tháng cho 1 sàn |")
H.append("| ≥ 3 tháng dữ liệu, nhiều regime | 7 ngày không đủ để nói edge bền | mở rộng dataset (cùng nguồn) "
         "hoặc thu tiếp | dung lượng tuyến tính: ~14 GB/tuần/symbol ⇒ 3 tháng ≈ 180 GB/symbol |")
H.append("| Fee tier thật của tài khoản | quyết định taker/maker nào áp dụng | lấy từ tài khoản Binance "
         "của owner | 0 |")
H.append("| Impact model theo size | decile giả định size vô hạn ở top-of-book | dùng depth 100 level + "
         "mô hình impact (v.d. square-root) | 0 (đã có depth) |")
H.append("")
H.append("**Điều kiện tối thiểu để có thể GO:** gross D10−D1 phải ≥ 2× phí/chiều + spread + buffer "
         "adverse selection; với phí maker thực tế ≥ 2 bps/chiều thì cần gross ≥ ~6–8 bps ở horizon giữ được "
         "> 1 phút. Hiện tại mức cao nhất là 3,4 bps (900 s) ⇒ còn thiếu ~2×.")
H.append("")
H.append("## 8. Giới hạn của lần đo này\n")
H.append("- Không mô phỏng fill/queue/adverse selection ⇒ cả net taker và net maker đều là **cận trên**.")
H.append("- `R² OOS` của `ofi1` âm dù IC dương: OFI có đuôi rất dày (p1/p99 ±2,7), OLS tuyến tính không "
         "ổn định; IC (hạng) là thống kê đáng tin hơn cho OFI.")
H.append("- Regime \"phút sập\" theo prereg (|r1m| ≥ 37,5 bps) chỉ có 45 giây trong test ⇒ **không đủ mẫu, "
         "chưa kết luận**; đã thay bằng so sánh vol thấp/cao (bảng §2).")
H.append("- Grid 1 s làm mất chi tiết trong giây; horizon 1 s vì vậy là **cận trên lạc quan** về tốc độ.")
H.append("- Chỉ 1 symbol (BNB); 4 symbol còn lại chưa đo tín hiệu.")
H.append("- **Thứ tự thời gian cần ghi rõ:** số spot trong prereg (|dev| p50 0,067 bps, corr 0,9989) được "
         "kiểm cục bộ bằng 16 file kline Vision tải trong `/tmp` **trước** khi commit prereg, vì kernel A4 "
         "lúc đó trả 0 phút khớp spot (kline spot Vision đã chuyển sang timestamp micro-giây). Kernel A v4 "
         "(sửa chuẩn hoá µs) sau đó cho **đúng cùng con số** (-0,065 / 0,0667 / 0,99887) ⇒ không đổi kết luận.")
H.append("- Số cuối cùng lấy từ kernel **`chuyendinh/lob-t1-v2`**: 2 lần push vào `lob-t1-signals` trả "
         "`status=error` với log rỗng (lỗi phía Kaggle), nên chạy lại bằng kernel mới; code không đổi.")
H.append("")

open(os.path.join(REPO, "docs/result/LOB_T1.md"), "w").write("\n".join(H) + "\n")
print("wrote LOB_T1.md")
