# HO4 — định nghĩa scorer B (commit TRƯỚC khi đọc printDone/equity 2026 của ho4-*)

Scorer B độc lập (không import/đọc ho26_score_a/b, nsel_score_a, ho4_score_a, HO4_RESULT_A). Script `research/analysis/ho4_score_b.py` (`fetch` rồi `score`). Luật: `docs/prereg/PREREG_HOLDOUT2026H1.md` §1 + ADDENDUM-5/6/7 (không đổi). Trạng thái lúc commit: scorer B CHƯA đọc printDone/equity/result.json/log 2026 của ho4-* (chỉ đọc header cột printDone + định dạng log/printDone của run DEV `gqsf-a1`).

## Dữ liệu vào
- 32 run `~/kaggle_sim/out/ho4-<cfg>-<b|s>-s<seed>`, cfg ∈ {b0, k24}, seed ∈ {42,7,13,21,99,123,777,2024}. Trước khi đọc: md5 `storage/printDone.csv` phải == dòng cuối có parity PASS của slug trong `~/claude_master/1011/ho4p1/q/queue_status.tsv`; lệch ⇒ dừng.
- printDone: `start`/`end` = chuỗi `YYYYmmdd HH:MM` giờ +07; `pnl` = PnL đã trừ phí/slippage/funding (bản `-s-`: penalty 1,675% nằm trong `entry`), ghi nhận tại phút `end`. `quantity` = khối lượng (kiểm == margin/entry). side BUY = long (SELL nếu có: dấu ngược).
- Giá MTM: Vision `futures/um` klines 1m (`data.binance.vision`, monthly; tháng chưa có monthly ⇒ daily), symbol = `sym` + `USDT`, close của nến có open_time = phút m (ms UTC). Tải cho mọi (symbol, tháng) giao với khoảng mở của chân có end ≥ 2025-12-31 00:00 +07 trong 32 run. Cache `~/claude_master/1012/ho4sb/vision` (cache tự tạo, xoá được). Ép float32 như ticker sim.
- Lưới phút G = [2025-12-31 00:00, 2026-10-03 00:00) +07.

## Equity MTM phút
- E(m) = 35000 + Σ pnl(end ≤ m) + Σ_{chân start ≤ m < end} q·(close(sym,m) − entry) (BUY). Thiếu giá: ffill theo symbol; trước giá đầu tiên trong lưới dùng entry. Đếm phút-chân thiếu giá.
- Cửa sổ (giờ +07): **W9** 2026-01-01 00:00 → 09-30 23:59; **H1** 01-01 00:00 → 06-30 23:59; **Q3** 07-01 00:00 → 09-30 23:59.
- E_start = E(phút ngay trước mốc đầu cửa sổ) (MTM của chính run); E_end = E(23:59 ngày cuối).
- **n** = số dòng có start ∈ cửa sổ. **ΣPnL** = Σ pnl dòng có end ∈ cửa sổ. **ROI** = E_end/E_start − 1. **maxDD** = min_m E(m)/peak(m) − 1 trên [E_start, E(đầu)…E(cuối)], peak = max chạy từ E_start (đặt lại đầu mỗi cửa sổ).
- Theo tháng (+07): n, ΣPnL, ROI MTM tháng (E cuối tháng / E cuối tháng trước − 1).
- Ngày (+07): E_d = E(23:59 ngày d), E_0 = E_start; r_d = E_d/E_{d−1} − 1. **Sharpe** = mean(r)/std(r, ddof 1)·√365; **Sortino** = mean(r)/√mean(min(r,0)²)·√365; **CAGR** = (E_end/E_start)^(365/số ngày) − 1. Tỉ lệ so DEV baseline stress: Sharpe/1,80; CAGR/27,6%; maxDD/(−22,9%).
- **% ngày có lệnh** = số ngày có ≥ 1 start / số ngày cửa sổ.

## Luật (bản stress `-s-`, từng cửa sổ W9/H1/Q3; ghép cặp theo seed)
- **E0**: mean_seed ΣPnL_S(k24) > 0 VÀ #seed ΣPnL_S(k24) > 0 ≥ 6/8.
- **H-A**: Δ = k24 − b0 cùng seed; mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5pp (maxDD âm; Δ tính theo điểm %).
- Bản phí gốc `-b-`: cùng số, chỉ báo.

## Báo kèm (ngoài luật)
- **Bootstrap MTM block-10d**: dP_d = E_d − E_{d−1} (USD) theo ngày, mỗi seed; khối 10 ngày liên tiếp vòng tròn, cùng chỉ số khối cho 8 seed và cho cả k24 lẫn b0; thống kê = mean_seed Σ dP*; NREP 5000, `numpy.random.default_rng(20261012)` sinh lần lượt cho W9, H1, Q3 (một ma trận chỉ số/cửa sổ dùng chung cho k24 và Δ). Báo: quan sát, P(≤0), CI95 phân vị 2,5/97,5, CI95 inflate k=3 = obs + 1,482·(phân vị − obs).
- **Độ tập trung** (k24-s, mỗi cửa sổ): ΣPnL theo ngày end; tỉ trọng top-1/3/5 ngày lãi = Σ k ngày lớn nhất / ΣPnL cửa sổ (chỉ khi ΣPnL > 0); leave-one-month-out: bỏ ΣPnL 1 tháng ⇒ #seed còn > 0 và mean còn > 0, báo tháng tệ nhất.
- **Độ nhạy dữ liệu H1**: ho4 vs `ho26-<cfg>-s-s<seed>` (b0, k24) cùng seed, thước H1 y hệt (n theo start, ΣPnL theo end): ΔΣPnL = HO4 − HO26, Δn, trùng lệnh = ghép 1-1 (sym bằng, |Δstart| ≤ 1 phút) — số cặp, % n HO4, % n HO26.

## Tự kiểm
1. md5 printDone == queue_status (32/32). 2. n printDone == `result.json.n_trades`. 3. Equity cuối: `equity_final` so (a) b+unP dòng log `Update D 07:00` cuối, (b) E MTM tại phút đó (và phút trước; lấy lệch nhỏ hơn) — ngưỡng 0,01% áp cho (b); báo thêm 35000+Σpnl. Mọi dòng `Update` có ngày ≥ 20260101: median/max |E − (b+unP)|/(b+unP). 4. Phần trước 2026: `ho4-k24-s-s42` vs `ho26-k24-s-s42` — dòng printDone end ≤ 2025-12-31 23:59 +07 so nguyên dòng (trùng/chỉ-HO4/chỉ-HO26), dòng start < 2026-01-01 00:00, dòng log `Update` ngày ≤ 20251231 (b, unP); báo lệch đầu tiên. 5. TZ: median |entry/close(start) − 1| trên bản `-b-` (giả định +07 vs UTC). 6. |quantity − margin/entry|/quantity max.

Python logging, không print. RAM ước < 3 GB.
