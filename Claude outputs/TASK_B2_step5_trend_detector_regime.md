# TASK B2 Bước 5 — Regime bằng TrendDetector production (SMA7/100 1D+4H OR) thay MA200 — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni (đề xuất: lấy lại `TrendDetector.isBtc/EthTrendBuyProduction` từ `157cf4d`, dùng làm regime, thử tham số).
Tiền đề: recon code (agent trước) — detector thật = `SMA_SHORT=7` vs `SMA_LONG=100`, khung 1D VÀ 4H, OR; up = (SMA7−SMA100>0 trên 1D) OR (trên 4H). KHÔNG phải MA60/M10/SMA200 (tên hàm cũ gây nhầm). File đã xoá ở HEAD nhưng lấy lại từ `157cf4d` nguyên vẹn. Chưa có bằng chứng edge; trend-crossover ensemble MA50/100/200 đã CHẾT holdout (trend-holdout-verdict) — nên đây là giả thuyết, không phải chắc thắng.

## Vì sao đáng thử (nhắm đúng lỗ hổng còn lại)
Bước 4 (RA14) dùng regime = BTC<MA200: cứu 2022, nhưng MA200 gọi 2025 là uptrend nên miss UW-2025 (RA12 vỡ, RA14 phải siết tới mất breadth). **Detector SMA7/100 NHANH HƠN** (SMA100<MA200; thêm khung 4H): trong bull-nhiễu 2025 (chop mạnh), SMA7 cắt xuống SMA100 nhiều lần → đánh dấu not-up → gate chặt → có thể cứu 2025 mà MA200 miss, đồng thời vẫn bắt bear 2022. **Điểm mạnh chống overfit**: cấu hình SMA7/100/1D+4H là production gốc 1 năm trước, KHÔNG chọn sau khi biết 2022/2025 → ít curve-fit hơn MA200.

## 0. LUẬT — như B2 (không nới)
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (`free -g`≥12G, `pgrep java` rỗng → dừng shadow-c3 trước sim, bật ngay sau, ghi mốc); PREREG trước; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; cổng OFF byte-identical; `x1_rates.py --appetite current --k`; logging chuẩn; KHÔNG `git checkout` (dùng `git show 157cf4d:<path>` để lấy code cũ, không đổi working tree).

## BƯỚC 1 — ĐO DETECTOR NHƯ REGIME FILTER (0-sim, làm TRƯỚC, độc lập UW sim)
Mục tiêu: biết detector có đánh dấu ĐÚNG cả 2022 (bear) lẫn 2025 (bull-nhiễu) là "not-up" không — TRƯỚC khi tốn sim. Nếu nó cũng miss 2025 như MA200 → NO-GO.

### 1.1 Tái hiện detector bằng Python (causal, từ dữ liệu offline)
- Resample `CLOSES_1H.bin` (BTC symId, ETH symId; map `/home/ubuntu/selector_pred_out/symbol_map.csv`) → chuỗi close 1D (mỗi 24h, boundary UTC-epoch giống `Utils.getDate`) và 4H (mỗi 4h, `Utils.get4Hour`). Ghi rõ giới hạn: resample từ 1h ≈ native Binance 1D/4H kline (close tại boundary trùng, nhưng SMA của close-resample có thể lệch nhẹ native — nêu trong doc, chấp nhận cho nghiên cứu).
- SMA7, SMA100 trên mỗi khung (close, đúng `SimpleMovingAverage.calculate`: trung bình N close gần nhất). up_1d = SMA7_1d − SMA100_1d > 0; up_4h tương tự. **detector_up(t) = up_1d(t) OR up_4h(t)**, causal (chỉ dùng nến đã đóng ≤ t).
- Cấu hình CHÍNH (khoá theo production gốc, KHÔNG nhặt từ sweep): SMA_SHORT=7, SMA_LONG=100, khung {1D,4H}, OR, ngưỡng 0.

### 1.2 Đo (commit `docs/PREREG_TREND_REGIME_DIAG.md` khoá metric trước)
- **Chuỗi regime**: % ngày detector=up mỗi năm 2021-2025. So MA200 (Bước 4: 2021 UP64.7%, 2022 UP0%, 2023 UP80.3%, 2024 UP80.1%, 2025 UP73.4%). **Câu chính: detector gọi 2025 UP bao nhiêu %?** Kỳ vọng < 73% (thấp hơn MA200 = bắt bull-nhiễu tốt hơn).
- **Phủ chuỗi UW dài**: lấy 2 chuỗi UW dài của gate-1.0/T100 (2022: 2021-11-16→2022-07-21; 2025: 2025-03-04→2025-10-16, từ `RESULT_REGIME_UPDOWN.md`/uw_source). Tính % ngày trong MỖI chuỗi mà detector=not-up. **Cổng: detector phải phủ tốt CẢ HAI** (không chỉ 2022 như MA200).
- **Edge độc lập (không qua sim)**: forward return BTC 1D/7D khi detector=up vs not-up (detector có tách được up/down thật không, hay nhiễu). ROI/đồng-thua của sổ T100 gán theo detector-regime (lệnh mở khi detector=not-up có tệ hơn không).
- **Sweep MÔ TẢ** (KHÔNG chọn winner): {SMA_SHORT∈[7], SMA_LONG∈[50,100,150,200], khung {1D-only, 4H-only, 1D+4H-OR}} — vẽ đường "% 2025 gọi not-up" theo tham số, để HIỂU độ nhạy. Cấu hình gốc (7/100/1D+4H) là cái duy nhất dùng cho phán quyết Bước 2; các mức khác chỉ mô tả.

### 1.3 Cổng GO/NO-GO cho Bước 2 (khoá trước)
- GO nếu: detector=not-up phủ ≥60% số ngày trong chuỗi UW-2025 VÀ ≥60% chuỗi UW-2022 (bắt được cả hai — điều MA200 không làm được với 2025). Tức detector "thấy" giai đoạn xấu 2025.
- NO-GO nếu: detector gọi 2025-UW-window phần lớn là up (giống MA200, miss 2025) → detector không hơn MA200, dừng, ghi power_wall.
- Ngưỡng 60% theo lý lẽ (đủ phủ để gate-chặt cắt phần lớn phơi nhiễm xấu); khoá trước.

Output `docs/DIAG_TREND_REGIME.md` + `research/analysis/trend_regime.py` + json, commit. Trả MASTER: %up mỗi năm (detector vs MA200), %phủ 2 chuỗi UW, edge độc lập, GO/NO-GO.

## BƯỚC 2 — SIM regime-gate dùng detector (chỉ khi Bước 1 GO)
Như Bước 4 nhưng regime = detector (thay MA200). Cắm: sinh CSV regime từ detector (giống `regime_build_ma200.py` → `regime_daily_trenddet.csv`), dùng `GATE_REGIME_ADAPTIVE`+`RegimeSchedule`+`SIM_REGIME_SCALE_UP` (hạ tầng đã có từ Bước 2/4, 0-diff Java nếu chỉ đổi CSV+profile). Biến thể QUYẾT ĐỊNH: up→1.0/down→1.7 (nền, giống R nhưng regime=detector); nếu Bước 1 cho thấy cần up chặt hơn thì up→1.2 — chốt 1 cặp trong PREREG theo kết quả Bước 1, KHÔNG quét-chọn-winner. Đối chứng R0 (giảm đều khớp n). Tiêu chí u1-u5 y Bước 4 (u1 n_eff≥1.5×T170; u2 UW≤200 mọi năm+CAGR floor; u3 maxDD/UW vs T170; u4 cứu 2025 + giữ 2022; u5 giữ uptrend 2023/2024). Cổng OFF byte-identical + tái lập T170. Dừng/bật shadow, sim tuần tự, per-year.

## 3. Ý nghĩa
THẮNG (detector-regime đạt u1-u5, đặc biệt cứu được 2025 mà MA200 không) ⇒ đây là kết quả dương đầu tiên của breadth ⇒ shadow forward ≥1 tháng trước khi bàn đổi incumbent; và xác nhận ý Uni đúng.
NO-GO Bước 1 hoặc NULL Bước 2 ⇒ detector không hơn MA200 ⇒ đóng breadth (5 round), ghi power_wall, chuyển TASK D. RA14 vẫn là ứng viên chờ (shadow/holdout) nếu muốn một biến thể MA200 khiêm tốn.

## 4. Sau mỗi bước: cập nhật project memory (`round_2026-09-20...md` + `MEMORY.md`), báo MASTER số + GO/NO-GO (Bước 1) hoặc verdict+u1-u5 (Bước 2).
