# PREREG SHORTVOL_T0 — tầng 0: VRP BTC/ETH và proxy bán straddle 7 ngày, chồng rủi ro với X14

- Ngày: 2026-10-24. Agent vol0 (giao bởi MASTER). Commit file này TRƯỚC khi tính bất kỳ VRP/RV-so-DVOL/PnL nào.
- Đã xem trước khi viết (được phép): độ phủ DVOL, độ phủ kline1m BTC/ETH, độ phủ X14 (sim.out, printDone). Không nhìn số VRP/PnL.
- Câu hỏi: có phần bù rủi ro biến động (VRP) đủ để một hệ BÁN biến động BTC/ETH đều tay ngoài lúc sập không, và nó chồng rủi ro với crash-buy X14 tới mức nào. KHÔNG mô phỏng options thật.

## 1. Dữ liệu (đã kiểm phủ)
- DVOL Deribit public `get_volatility_index_data` (curl từ Oracle, không key), BTC và ETH, resolution 1D và 3600, 2021-12-01→2025-12-30 (1D: 1491/1491 ngày, ts đều 00:00 UTC, không trùng, không thiếu; 1h: 35785/35785). Close nến 1D ngày D−1 = close nến 1h 23:00 ngày D−1 (khớp 1491/1491) ⇒ là giá trị DVOL tại 00:00 UTC ngày D. `open[D] ≠ close[D−1]` ở 102 (BTC) / 111 (ETH) ngày ⇒ dùng close[D−1] như thiết kế ("close 00:00 UTC"), không dùng open.
- Code tải: `research/shortvol_t0/sv_fetch_dvol.py`. sha256 CSV ghi ở result.
- Giá: `~/vz_e1/raw/kline1m-YYYY-MM.parquet` (ts int64 ms), BTCUSDT, ETHUSDT, cột close. Lưới 1m 2021-12-31 00:00 → 2025-12-31 23:59 UTC: 2 105 280 phút mỗi symbol, **0 phút thiếu** (raw đủ 2 105 280 dòng), 0 dòng trùng. Các "lỗ dữ liệu đã biết" (2022-02-26/27/28 …) là lỗ của **vũ trụ symbol** (139 → 91 symbol/ngày) — BTC/ETH không thiếu. Vẫn giữ ffill (không kích hoạt) và ghi số phút n_trades = 0 hoặc active = False (BTC 308, ETH 213; nằm ở các tháng 2022-05, 2023-09, 2023-11, 2024-10, 2025-01, 2025-08 — nến phẳng kiểu bảo trì, return 0).
- X14: `~/kaggle_sim/out/tsx-x14-{a1,s123,s13,s2024,s21,s7,s777,s99}/`. Equity ngày MTM E = b + unP tại dòng `BudgetManagerSimple: Update YYYYMMDD 07:00` (07:00 +07 = 00:00 UTC), 1644 ngày/seed 2021-07-01→2025-12-30. printDone: 28 263 leg (mọi level: PREDICT_SYMBOL_TRADE, BIG_DOWN, DCA_LEVEL1), `start`/`end` giờ +07 ⇒ UTC = −7h. Code: `research/shortvol_t0/sv_prep.py`.
- Không dùng 2020/2021 (trừ phút 2021-12-31 23:59 làm giá mốc cho return đầu tiên 2022-01-01), không dùng 2026.

## 2. Định nghĩa (khoá)
- σ_t (điểm vol) = DVOL_t = close nến DVOL 1D có ts = t − 1 ngày (giá trị tại 00:00 UTC ngày t).
- Giá mốc 5′: P(m) tại mốc m = k·5 phút = close nến 1m có ts = m − 1 phút. r = ln(P(m)/P(m−5′)).
- RV_N(t) (điểm vol) = 100·√(365/N · Σ r²) với r trên các khoảng 5′ nằm trong (t, t+N ngày], t = 00:00 UTC; N = 30 (8 640 return) và N = 7 (2 016 return).
- VRP30_t = DVOL_t − RV30(t), t ∈ [2022-01-01, 2025-12-01] (1 431 ngày; cửa sổ cuối kết thúc 2025-12-31 24:00). VRP7_t = DVOL_t − RV7(t), t ∈ [2022-01-01, 2025-12-24]. **Lệch kỳ hạn:** DVOL là IV 30 ngày, VRP7 so nó với RV 7 ngày (chỉ mô tả, không vào tiêu chí).
- Tuần bán: mỗi thứ Hai t_k 08:00 UTC, t_k ∈ {2022-01-03, …, 2025-12-22} (208 tuần). S0 = close nến 1m ts = t_k 08:00; S_T = close nến 1m ts = t_k + 7 ngày 08:00. σ = DVOL tại 00:00 UTC thứ Hai đó /100.
- Phí thu P = 0,8·σ·√(7/365)·S0 (Brenner–Subrahmanyam, straddle ATM). Phí sàn mỗi chân f = min(0,00024·S0, 0,10·P/2), 2 chân. Slippage = 0,05·P. Payoff = |S_T − S0|.
- PnL_week = (P − 2f − 0,05P − |S_T − S0|) / S0 (phân số của S0, 1 đơn vị notional; báo bằng %).
- Biến thể đối chứng (duy nhất): bỏ tuần k nếu ∃ leg X14 (union 8 seed, mọi dòng printDone) có start_UTC ∈ (t_k − 7 ngày, t_k]. Tuần bị bỏ: PnL = 0 (vốn đứng yên), vẫn nằm trong chuỗi khi tính mean/Sharpe. Thống kê "chỉ tuần có bán" báo mô tả.
- X14 tuần: median seed = **s2024** (như TREND_T1, chọn theo Sharpe MTM X14 trước khi có PnL short-vol). r_X14,k = E(t_k+7 00:00 UTC)/E(t_k 00:00 UTC) − 1. Lệch 8 giờ so với tuần short-vol (equity X14 chỉ có tại 00:00 UTC).
- "Tuần X14 có leg" (để đo chồng rủi ro, KHÔNG causal, mô tả): ∃ leg union 8 seed với [start, end] giao [t_k 08:00, t_k+7 08:00).
- Danh mục gộp: r_c,k = 0,8·r_X14,k + 0,2·PnL_week,k (BTC). maxDD tính từ equity tích luỹ (1 + r) bắt đầu 1,0 trong mỗi kỳ, kỳ 2022–23 = tuần có t_k ∈ 2022–2023 (104 tuần), 2024–25 = t_k ∈ 2024–2025 (104 tuần).
- Sharpe tuần hằng năm hoá = mean/std(ddof=1)·√52. Năm của VRP theo năm của t; năm của tuần theo năm của t_k.
- CI 95 % VRP30 cả kỳ: block bootstrap theo tháng dương lịch của t (48 khối, rút có hoàn lại 48 khối, ghép, lấy mean), 10 000 lần, seed numpy 20261024, percentile 2,5/97,5.

## 3. Tiêu chí GO tầng 0 (BTC quyết định; ETH báo kèm cùng tiêu chí, không quyết định)
- **V1**: mean VRP30 > 0 ở ≥ 3/4 năm {2022, 2023, 2024, 2025} VÀ mean cả kỳ > 0 với cận dưới CI 95 % > 0.
- **V2**: mean PnL_week net > 0 ở ≥ 3/4 năm VÀ Sharpe tuần hằng năm hoá cả kỳ ≥ 0,8.
- **V3**: biến thể đối chứng (bỏ tuần X14 gần đây) vẫn đạt V2.
- **V4**: maxDD gộp 80/20 ≥ maxDD X14 một mình − 3 điểm % (DD là số âm), ở CẢ 2022–23 và 2024–25.
- GO ⇔ V1 ∧ V2 ∧ V3 ∧ V4 (BTC) ⇒ sang tầng 1 (MASTER thiết kế). Trượt bất kỳ ⇒ NO-GO, ĐÓNG short-vol.

## 4. Mô tả (không vào verdict)
- VRP30/VRP7 theo năm, DVOL TB, RV TB; phân phối PnL tuần (quantile, 10 tuần tệ nhất + ngày), tuần LUNA (t_k = 2022-05-09), FTX (2022-11-07), 2025-10-10 (t_k = 2025-10-06); tỉ lệ tuần lãi; payoff ratio = mean lãi / |mean lỗ|.
- Độ nhạy slippage 2 % / 10 % premium.
- Chồng rủi ro: corr(PnL_week, r_X14) theo tuần (cả kỳ + từng kỳ); tổng PnL short-vol tuần X14 có leg vs không; số tuần trong 10 tuần tệ nhất short-vol trùng tuần X14 có leg; V4 cho từng seed X14 (mô tả); ETH cùng bảng.

## 5. Validation
- V1v: ts int64 (assert dtype), số nến 1m = 2 105 280/symbol, số mốc 5′ và số return mỗi cửa sổ đúng (8 640 / 2 016), số tuần 208, số ngày VRP30 1 431.
- V2v: script độc lập `sv_indep.py` (không import pipeline; đọc lại raw parquet và JSON DVOL thô) tái lập mean VRP30 năm 2023 BTC và PnL proxy 10 tuần (t_k = 2023-01-02 … 2023-03-06), |Δ| < 1e-9.
- V3v: in raw cho 3 tuần (2022-05-09, 2023-06-05, 2025-10-06): S0, S_T, DVOL, P, phí, payoff, PnL; kiểm tay trong result.
- V4v: RV30 từ 5′ vs từ 1m vs từ daily (return 00:00→00:00) cùng bậc độ lớn (tỉ số trung bình trong [0,5; 2]).
- V5v: DVOL ts khớp ngày UTC, không trùng, không thiếu (ghi ngày thiếu) — đã kiểm ở §1, chạy lại trong `sv_valid.py`.

## 6. Lệch thiết kế
1. Không cần ffill: BTC/ETH không thiếu phút nào; lỗ đã biết thuộc vũ trụ symbol khác. ffill vẫn để trong code (0 phút kích hoạt).
2. DVOL CSV **không commit**: Deribit Membership Terms (hiệu lực 2026-08-13) cl. 2.10 "market data … personal use only", cấm "publish, forward … without prior written approval"; cl. 37.3 cấm copy/distribute. Repo có thể bị push ⇒ chỉ commit script tải + sha256 + thống kê. File để ở `~/claude_master/shortvol_t0_wk/dvol/` (dùng riêng).
3. Tuần X14 neo 00:00 UTC thứ Hai (equity chỉ có tại 00:00 UTC), lệch 8 giờ so với tuần short-vol 08:00.
4. VRP30 kết thúc t = 2025-12-01 và tuần cuối t_k = 2025-12-22 vì không dùng dữ liệu 2026.
5. "Leg X14" = mọi dòng printDone (cả BIG_DOWN, DCA_LEVEL1), union 8 seed — thiết kế không nói lọc level.
