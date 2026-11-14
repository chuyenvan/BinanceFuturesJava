# IND_COMBO Pha 0 — kế hoạch vận hành (đi kèm PREREG_IND_COMBO, khoá CÙNG commit, TRƯỚC khi đọc bất kỳ Y nào)

Tác giả: agent thực thi (Opus) cho MASTER · 2026-11-14. Tài liệu này CHỈ cụ thể hoá chỗ prereg chưa ghi chi tiết; mâu thuẫn ⇒ prereg thắng.

## A. Kiểm kho (đã làm, chỉ đọc schema/đếm dòng — không đọc giá trị Y)
- Leg B0: `~/kaggle_sim/out/nt-x14-s{42,7,13,21,99,123,777,2024}/storage/printDone.csv` (8 seed; có sym, start (+07), end, level, margin, pnl, symbolPred = điểm S1). Chỉ dùng level `PREDICT_SYMBOL_TRADE` (BIG_DOWN, DCA_LEVEL1 là sleeve riêng, không phải leg selector).
- Hạng S1 trong phút: từ `~/claude_master/1004/gqd/cand_base.npz` (top-24 sp theo phút, như GATE_SMART P0a): rank = vị trí sym trong top-24 (1 = điểm S1 cao nhất). Không có trong top-24 ⇒ rank NaN, leg bị loại khỏi phân tích track S (ghi số lượng).
- Y72 (track G): `~/claude_master/res1109/r5_quality/out/r5q_y.parquet` (cột y72 theo phút DEV, đúng kernel R5 Pha 1, prereg 200a29a3). r/q theo phút: tính lại bằng `gate_offline` với cấu hình R5 (pred `res1109/r3_gate/pred/pred_s*.bin`, sổ khoá `nup4_fix/results/n4f-b0-*`), J = 256; kiểm số phút pass mỗi seed/năm KHỚP `sig_meta.json` R5 (bằng tuyệt đối) trước khi dùng.
- Nến: 1h OHLCV `~/java/fsrun/OHLCV_1H_v2.bin` (md5 86f1061c…, nguồn Aerospike kline_1m_opt, 2021-01-01→2025-12-31, 626 symbol, ts = giờ ĐÓNG). 4h/1d gộp từ 1h (UTC, 4h mốc 00/04/…; 1d 00:00 UTC). Lợi suất 1m (chỉ cho C18): close Vision `~/claude_master/res1109/r1_s1/kl/kline1m-YYYY-MM.parquet` (2021-12→2025-12), gộp theo giờ (Σr, Σr², n). ALT_EW theo phút: `~/claude_master/edge_attr/index.npz` (2021-07→2025-12).
- HO 2026 (chỉ mô tả): nến 2026-01..06 phải dựng từ Kaggle `vz-kline1m-2026` (1 kernel, enable_internet=false). Y72 2026 không có ⇒ track G không có HO. Không có cand_base 2026 ⇒ HO track S khử theo điểm S1 + không có hạng.

## B. Định nghĩa
- Thời gian: năm theo +07 (như R5/sim): EXPLORE ts ∈ [2022-01-01, 2024-01-01) +07; CONFIRM [2024-01-01, 2026-01-01); HO [2026-01-01, 2026-07-01).
- Y_leg (%) = 100 × pnl / margin của dòng PREDICT (pnl ròng phí sim, đã gồm DCA trong leg + exit). Tổng PnL nhóm (tiêu chí veto) = Σ pnl USD.
- Phút vào M = start(+07) − 7 h (UTC ms). Nến dùng được ⇔ giờ đóng ≤ M (nến đang chạy KHÔNG dùng). 4h/1d: chỉ nến 4h/1d ĐÃ đóng ≤ M.
- Cụm (track S): đợt = chuỗi phút vào leg (hợp 8 seed) cách nhau ≤ 60′; id cụm chung mọi seed.
- Indicator (tham số chuẩn; Wilder cho RSI/ATR/ADX): C1–3 RSI14 1h/4h/1d; C4–5 Stoch %K14 = 100(C−LL14)/(HH14−LL14) 1h/4h; C6–7 %b(20,2) σ ddof=0 1h/4h; C8 BBW1d = 4σ/SMA20, phân vị (0–1) của giá trị hiện tại trong 180 nến 1d gần nhất của chính coin (cần ≥ 90); C9–10 MACD hist(12,26,9)/ATR14 1h/4h; C11–12 ADX14 4h/1d; C13 (+DI − −DI)14 1d; C14 (C − max H 20 nến 1d)/ATR14 1d; C15 close 1h cuối / max close 1h 720 giờ − 1; C16–17 C/SMA50 − 1, C/SMA200 − 1 (1d; thiếu đủ nến ⇒ NaN); C18 std(r1m giờ đóng cuối)/std(r1m 24 giờ đóng cuối) (cần ≥ 45 và ≥ 1080 phút); C19 (qv giờ cuối − mean qv 168 giờ trước đó)/sd; C20 số nến 4h đỏ (C<O) liên tiếp kết thúc ở nến 4h đóng cuối. Warm-up tối thiểu = đủ chu kỳ của indicator (EMA/Wilder cần ≥ 3× chu kỳ nến), thiếu ⇒ NaN.
- Market: M1 BTC RSI14 4h; M2 BTC RSI14 1d; M3 BTC C/SMA200 − 1 (1d); M4 breadth = % coin có nến 1d ngày đó và ≥ 50 nến 1d với C > SMA50; M5 ALT_EW drawdown 30 ngày = exp(I − max I trong 30 ngày) − 1, I = Σ r ALT_EW tới giờ đóng cuối; M6 std r ALT_EW 1m 24 h / 30 ngày (tới giờ đóng cuối).
- Khử trùng: Spearman trên X của leg EXPLORE (gộp seed), theo thứ tự C1..C20, M1..M6; bỏ indicator có |ρ| > 0,80 với indicator đứng trước CÒN GIỮ. Bảng 45 feature S1 KHÔNG có trong dump ⇒ không khử theo S1 (điều kiện "nếu có" của prereg không thoả).
- Partial Spearman IC: trong mẫu kỳ, rank X (bỏ NaN) và rank Y; hồi quy OLS mỗi bên trên [1, rank(hạng S1), rank(điểm S1), dummy năm]; IC = corr(residual). Bootstrap cụm 2 000, seed 20261114 (numpy default_rng), rank tính một lần trên mẫu kỳ, residual + corr tính lại mỗi lần. CI90 = phân vị 5/95. p hai phía = 2Φ(−|IC|/se_boot); một phía (CONFIRM) = Φ(−s·IC/se_boot), s = dấu EXPLORE.
- Tổ hợp: phân vị của X theo ECDF EXPLORE (gộp leg EXPLORE); điểm có dấu = s × (phân vị − 0,5). C_ALL = nanmean mọi indicator COIN-level còn giữ; C_TOP5 = 5 coin-level |IC EXPLORE| lớn nhất. ML: xgboost (hist) depth 3, 200 cây, lr 0,05, subsample 0,8, seed 20261114, nthread 4; mục tiêu = residual rank(Y_leg) trên [rank(hạng S1), dummy năm] trong EXPLORE; feature = toàn bộ indicator còn giữ (C+M) + hạng S1 + điểm S1; NaN để xgboost xử lý.
- MDE80 (trước khi đọc Y CONFIRM): se_C = median_i(se_boot,E,i) × √(n_cụm_E / n_cụm_C); MDE80 = (z_0,90 + z_0,80) × se_C (một phía α 0,10 không chỉnh) và bản Holm m ứng viên (α/m). > 0,08 ⇒ cảnh báo.
- Veto (CONFIRM): ngũ phân vị xấu = 20 % giá trị bất lợi theo s và cutpoint EXPLORE (s > 0: X ≤ q20_E; s < 0: X ≥ q80_E). Đạt (3) ⇔ mean Y bị loại − mean Y giữ < 0 với CI90 cụm < 0 VÀ Σ pnl USD nhóm bị loại ≤ 0 ở cả 2024 và 2025.
- Seed 42 báo riêng (mô tả): IC, dấu.

## C. Track G
- Đơn vị = (seed, phút DEV). Phút pass B0 = G2 pass bất kỳ ô; near-miss band b = không pass VÀ max_ô hợp lệ r/q ∈ [b, 1), b ∈ {0,85; 0,70}. Khử cụm như R5: theo từng seed × nhóm, giữ phút ĐẦU của mỗi chuỗi cách ≤ 60′. Cụm bootstrap = đợt trên hợp mọi phút pass ∪ near-miss 0,70 của 8 seed (≤ 60′).
- Dấu s_M (EXPLORE) = dấu Spearman(M, Y72) trên phút (pass ∪ near-miss 0,70) đã khử cụm EXPLORE. Thuận = top 20 % của s·M, nghịch = bottom 20 % (cutpoint EXPLORE trên cùng tập). C_ALL_M = nanmean s × (phân vị ECDF − 0,5) của M còn giữ.
- G-relax(M,b): Δ = mean Y72(nm_b ∩ thuận) − mean Y72(pass). G-veto(M): Δ = mean Y72(pass ∩ nghịch) − mean Y72(pass còn lại). (Y72 tính bằng pp.)
- Chọn EXPLORE (≤ 2 ứng viên, ghi SELECTION): ứng viên relax nếu ở CẢ 2 band Δ_E ≥ 0, CI90 dưới > −1 pp và Y72(nm∩thuận) > 0; ứng viên veto nếu Δ_E < 0 với CI90 < 0. Xếp theo |Δ_E| (relax: min 2 band), lấy tối đa 2.
- CONFIRM: tiêu chí prereg + Holm một phía α 0,10 trên m = 14 (7 chỉ báo × 2 band); p relax = P_norm(Δ ≤ −1 pp), p veto = P_norm(Δ ≥ 0) theo se bootstrap.

## D. Validate trước khi báo
Số leg/cụm mỗi năm; tỉ lệ NaN mỗi indicator (< 20 % trừ C17/C8 có ghi chú); kiểm causal 20 leg ngẫu nhiên (seed 20261114) tính tay RSI14 1h, C/SMA50 1d, Stoch 4h từ chuỗi 1h thô và xác nhận nến cuối dùng có giờ đóng ≤ M; seed 42 cùng chiều gộp; chạy bootstrap 2 lần ra cùng số.
