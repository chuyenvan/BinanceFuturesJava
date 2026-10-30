# PREREG_GATE_STAB — ổn định ngưỡng gate GATE_QUOTA sau burst (2026-10-30)

Trạng thái: PRE-REG, viết và commit TRƯỚC khi đo §2 (M) và trước mọi sim biến thể §3. Chỉ được sửa bằng ADDENDUM có hash.
Người viết: agent Opus (giao bởi MASTER). Nhánh `research/vz-e1`. Không push.

## 0. Bối cảnh và kết quả Pha 1 (đã xác minh, KHÔNG phải kết quả đo của prereg này)
- Cơ chế (jar live dcae2e2b = `v1.1/exec-probe` 16de49a6; sim cùng lớp lõi): `GateRatioBuffer.computeQ` (dòng 72–82) — q_h = phần tử thứ k=floor(pct·(m−1)) của mọi r có ts ∈ [h−90d, h), tính MỘT lần ở truy vấn đầu mỗi giờ; pct 0,999950829 ⇒ số phần tử trên q = (1−pct)(m−1). Sim `GateRollingRatio.threshold` và live `LiveGateRollingRatio.threshold` gọi CÙNG `buffer.addAndQuery` (cùng công thức/cửa sổ).
- Dòng log `[GATE-RATIO] q_t` lúc HH:01 in q của giờ TRƯỚC (`logHour` gọi trong `noteCandidate` trước `threshold`) ⇒ cú nhảy log 05:01 thực có hiệu lực từ 04:00.
- Tính lại tay từ `run/gate_ratio_live.bin` 242 (md5 4e29c20c, 982 968 record, 0 chunk hỏng): q giờ 03 = 0,00725548249, giờ 04–07 = 0,00950214919, giờ 08–15 = 0,00955525972 — khớp log 9 chữ số. Replay `sel_dump` tái lập đúng pass=93 (giờ 03) và pass=1 (giờ 07).
- 07:27 n_pass=1 = INTWUSDT (rank 1, sp 0,1749, r 0,00980 ≥ q 0,009502) nhưng đã mở 07:19 qua nhánh BIG_DOWN ⇒ không mở lại.
- **LIVE ≠ SIM (lỗi parity):** live chỉ loại `BudgetManager.symbol2Pos` (vị thế THẬT) trước gate (`DetectEntrySignal2TradeNormal.java:531`, v1.2 d035a086 dòng 560); vị thế GIẤY (ShadowBookC3) vẫn đi qua gate và NẠP r vào buffer. Sim loại coin đang giữ TRƯỚC gate (`isSymbolRunning`, SimulatorMarketLevelTicker1MStopLoss:460). Burst 10-30: 93 pass = 26 lệnh mới + 67 lượt coin đã giữ. Bỏ 67 lượt đó (quy ước sim): q giờ 04 = 0,007564 (+4,3 %) thay vì 0,009502 (+31 %); đợt 2 sẽ có 29 pass, 8 lệnh mới (CAP, CT, DOS, IDOL, IRYS, NIL, PARTI, Q). Ngoài ra buffer live mới 30 ngày (m≈0,96M, 48 phần tử trên q) so với sim ổn định (m≈3,1M, ~150 trên q; jmax offline 149) ⇒ live hiện nhạy với burst gấp ~3 lần backtest tới khi đủ 90 ngày (~2026-12-30).
- Kiểm công cụ (chạy TRƯỚC prereg, chỉ hiệu chuẩn, không đo outcome): `gate_offline` trên printDone `nt-x14-s*`: |pass off−sim| DEV ≤ 2,23 %/seed; recall lệnh PREDICT DEV: A1 0,9865, S99 0,990, S777 0,9936; S7 0,935, S13 0,940, S21 0,921, S123 0,932, S2024 0,948 (thấp đi cùng skipFull 147–942 lượt, offline không mô hình sổ đầy).

## 1. Câu hỏi
Q1 (đo): trong backtest A1 không TradFi (X14 + K24 + skipFull, `nt-x14-s*`), q tăng sau burst có chặn "đợt sập thứ hai" thường xuyên không, bao nhiêu tín hiệu mới bị chặn?
Q2 (sim, chỉ chạy nếu §2.6 đạt và MASTER duyệt): cơ chế ổn định q có tăng PnL/giảm DD mà không chen lệnh nền?

## 2. Đo M (offline, Oracle, chỉ đếm — không PnL mới)
2.1 Gate offline = `gate_offline.build/run_g2` (days 90, pct 0,999950829, K24, J 1024), held từ printDone của chính run; DEV = 2022-01-01..2025-12-31 (+07). Burst hour (BH) = giờ UTC có ≥ 10 ô PASS.
2.2 q_cf(h) = q tính trên cùng buffer nhưng BỎ record thuộc BH nằm trong [h−24h, h). Ô bị chặn = ô hợp lệ (không giữ) có q_cf(h) ≤ r < q(h), h trong (BH, BH+24h].
2.3 Đợt (episode) = chuỗi BH cách nhau ≤ 3 h. "Đợt kép bị chặn" = đợt có ≥ 1 ô bị chặn ở giờ ≥ (giờ BH cuối + 1). "Đợt kép đã vào" = đợt có BH khác trong (cuối, cuối+24h]. Lệnh mới bị chặn = ô bị chặn đầu tiên mỗi (symbol, đợt).
2.4 Báo theo seed và tổng: #BH, #đợt, #kép bị chặn, #kép đã vào, #ô bị chặn, #lệnh mới bị chặn, theo năm; tỉ số q(BH cuối+1)/q(BH đầu).
2.5 Mô tả (từ printDone, không suy diễn nhân quả): PnL/leg lệnh PREDICT vào trong (BH, BH+24h] (đã qua q cao) so với lệnh khác.
Seed chính: A1, S99, S777 (qua cổng công cụ recall ≥ 0,97, |Δpass| ≤ 3 %). 5 seed còn lại là phụ (xấp xỉ).
2.6 Cổng lực: nếu lệnh mới bị chặn < 20/seed DEV (median seed chính) HOẶC #kép bị chặn < 10 ⇒ KẾT LUẬN "không đủ sức thống kê", KHÔNG chạy §3, đóng hướng (chỉ giữ sửa parity §5).

## 3. Biến thể (tham số CỐ ĐỊNH, không lưới; chỉ chạy khi §2.6 đạt + MASTER duyệt)
- V0 = `nt-x14` (profile r4_kg0_k16_f015_g155 + overrides của result.json), 8 seed 42/7/13/21/99/123/777/2024.
- V1 BX24: giờ có ≥ 10 pass (đếm như `notePass`, sau skipFull) đánh dấu burst; computeQ(h) bỏ record của giờ burst trong [h−24h, h); sau 24h nạp lại. Key mới `SIM_GATE_BURST_DEFER_H=24`, `SIM_GATE_BURST_N=10`.
- V2 CAP5: q_eff(h) = min(q_raw(h), q_eff(h−1)·1,05); giảm không giới hạn; warm-up giữ nguyên. Key `SIM_GATE_Q_STEP_CAP=1.05`.
- V3 W180: `SIM_GATE_ROLLING_DAYS=180` (key có sẵn, pct giữ nguyên).
Key OFF ⇒ byte-identical V0 (bắt buộc test). Jar STUB + `research/nup3/jar_sec_check.py`.

## 4. Tiêu chí GO (mỗi biến thể vs V0, ghép cặp seed; α hiệu chỉnh 0,05/3 ⇒ CI 98,33 %)
- MTM bằng `~/claude_master/gvz/gvz_mtm.py`, kiểm missing = 0 (cấm `run_mtm` trơn); DD quý theo pipeline golive_quarterly có bù.
- G1: ΔCAGR22 DEV (2022–2025) mean > 0 với CI t ghép cặp không chứa 0, HOẶC ΔCalmar mean > 0 với CI không chứa 0.
- G2: maxDD MTM: median không sâu hơn V0 quá 2,0 pp; seed tệ nhất không sâu hơn quá 3,0 pp.
- G3: ≥ 7/8 seed cùng dấu dương ở chỉ số đạt G1.
- G4 HO 2026 (W9, cùng run): mean ΔROI ≥ 0 và không seed nào DD sâu hơn > 2 pp (HO chỉ 1 đợt sập ⇒ chỉ chặn, không chứng minh).
- G5 chen lấn: ghép leg V0↔Vk theo (sym, phút vào). ΣPnL leg chung Vk ≥ 0,98 × V0 (median seed) VÀ PnL/leg leg "mới" ≥ 0,75 × PnL/leg nền V0; báo n và PnL/leg leg "mất". Trượt G5 ⇒ NO-GO dù G1 đạt.
- Nhiều GO ⇒ chọn ΔCalmar mean lớn nhất (KHÔNG theo CAGR — bài học ISO_RISK).
- MDE: sd Δ ghép cặp tham chiếu GQSF 2,42 pp CAGR22 ⇒ MDE80 ≈ (t_0,9917;7 3,0 + 0,9)·sd/√8 ≈ 1,38·sd ≈ 3,3 pp; nếu sd biến thể ~1 pp ⇒ ~1,4 pp. Hiệu ứng kỳ vọng ước từ §2: (#lệnh mới bị chặn/năm × PnL/leg nền) / vốn — nếu < MDE ⇒ ghi trước là "không chứng minh được", không chạy.

## 5. Ngoài biến thể: sửa parity (không cần GO nghiên cứu)
Live/dry phải loại coin đang giữ trong sổ c3/shadow TRƯỚC gate như sim. v1.2 LIVE thật: `symbol2Pos` lấy từ positionRisk tài khoản chính ⇒ có thể đã đúng — CHƯA XÁC MINH; v1.2 DRY (giấy) chắc chắn lệch như shadow v1.1. Phải sửa trước cửa sổ parity v1.2 dry; nghiệm thu bằng replay 10-30 (q giờ 04 kỳ vọng 0,007564).

## 6. Cấm
Không đổi BURST_N/CF_H/EP_GAP/hệ số 1,05/180d sau khi thấy §2 hoặc §3. Không thêm biến thể. Không chọn seed. Mọi ngoại lệ ⇒ ADDENDUM có hash trước khi chạy lại.

## 7. Tài nguyên
§2: Oracle, flock `oracle_heavy.lock`, RSS ~3,3 GB, ~10 s/seed. §3: code Java V1/V2 (+test) ~1 phiên Opus; build Oracle `mvn -o`; Kaggle 3×8 run full 2021-07→2026-09 × ~44 phút / 2 slot ≈ 9 h; MTM cần kline1m Vision (không còn ở Oracle `~/vz_e1/raw`) ⇒ kernel Kaggle hoặc tải tạm từng tháng rồi xoá (≤1 GB/lần).
