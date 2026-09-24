# TASK B2 Bước 4 — Regime-adaptive gate up/down theo MA200, up-gate CHẶT HƠN (ý Uni) — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni (đề xuất trực tiếp: "sizing theo MA200 BTC — dưới MA200 dùng T170/T140, trên MA200 dùng T100/T120/T80").
Tiền đề: B2 Bước 2 (`RESULT_REGIME_GATE.md` `54d9cdb`) đã test up→1.0/down→1.70 theo MA200: cứu bear 2022, vỡ UW-2025. Chẩn đoán 2025 (`DIAG_UW2025_SOURCE.md`): nguồn 2025 = bull-nhiễu, và gate đều ~1.18 (R0) cứu được UW-2025. Bước 3 (drawdown-throttle) NULL — nhưng đó là cơ chế REACTIVE; bước này PROACTIVE (đặt mức theo regime trước), khác bản chất.

## Ý tưởng cốt lõi (vì sao đáng thử dù 3 bước trước NULL)
Bước 2 dùng up→1.0 (quá lỏng cho bull-nhiễu 2025 → vỡ). Fix của Uni: up-gate CHẶT HƠN (T120≈1.2). Giả thuyết: **up→1.2 / down→1.7** đủ chặt để cả bull-nhiễu 2025 (up-regime) không vỡ UW, mà vẫn lỏng hơn T170 ở up-regime để lấy breadth. down→1.7 giữ phòng thủ bear 2022. Đây là proactive (mức cố định theo regime), KHÔNG giảm-khi-dưới-nước ⇒ không dính bài học "phục hồi chậm" đã giết Bước 1/2-pacing/3.

## 0. LUẬT — như B2 (không nới)
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (`free -g`≥12G, `pgrep java` rỗng → **dừng shadow-c3 trước sim, bật ngay sau, ghi mốc**); PREREG trước; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; **cổng OFF byte-identical**; `x1_rates.py --appetite current --k`; logging chuẩn.

## 1. CHỐNG OVERFIT (bắt buộc — điểm review MASTER)
- **1 cặp QUYẾT ĐỊNH khoá trước theo lý lẽ**: up=1.2 (căn cứ: chẩn đoán 2025 cho gate~1.18 cứu bull-nhiễu; lý lẽ độc lập: up-regime vẫn cần phòng thủ vừa vì bull có drawdown), down=1.7 (=T170, đã chứng minh sống bear 2022). Đây là biến thể phán quyết duy nhất.
- **Sweep MÔ TẢ (KHÔNG dùng chọn winner)**: up ∈ {1.0, 1.2, 1.4} × down=1.7 (up=1.0 = R Bước 2, dùng lại; chạy thêm 1.2, 1.4). Mục đích: vẽ đường cong breadth(n_eff)–vs–UW theo up-gate để HIỂU trade-off, báo cả 3. TUYỆT ĐỐI không đổi cặp quyết định sang mức khác sau khi thấy số (luật cấm mở biến thể quanh winner — B4_RESULT/power_wall).
- Chấm PER-YEAR 2021-2025 + toàn kỳ. down-gate giữ 1.7 cố định (không quét down — bear 2022 đã biết T170 sống, không tinh chỉnh).

## 2. CƠ CHẾ (0-diff Java, chỉ profile — hạ tầng có sẵn)
Dùng `GATE_REGIME_ADAPTIVE` + `RegimeSchedule` (CSV regime MA200-trailing causal đã sinh ở Bước 2, `regime_build_ma200.py`). `REGIME_SCALE_UP` / `REGIME_SCALE_NOTUP` đặt trong profile. `not_up` = BTC daily close < MA200 trailing (causal, y Bước 2). 0 dòng Java mới (xác nhận), chỉ profile mới cho từng cặp. Nếu vì lý do kỹ thuật phải sửa code để nhận SCALE_UP≠1.0 → ghi rõ + giữ OFF byte-identical.

## 3. BIẾN THỂ
Baseline (không tính k): T170, gate-1.0, và R (up1.0/down1.7 = Bước 2, dùng lại số).
- **RA12 (QUYẾT ĐỊNH)**: up=1.2, down=1.7.
- Sweep mô tả: **RA14** (up=1.4, down=1.7). (RA10=R Bước 2 đã có.)
k cho phán quyết = 1 (chỉ RA12 quyết định); sweep mô tả không vào phán quyết nên không thổi k. (Nếu MASTER/Uni muốn coi RA12 là 1 trong 3 lựa chọn cân nhắc thì k=3, `x1_rates.py --k 3` — agent báo cả hai cách chấm để minh bạch.)

## 4. TIÊU CHÍ (khoá trước, cho RA12; UW là chính)
- u1 breadth: n_eff_total(RA12) ≥ 1.5× T170.
- u2 khẩu vị: PASS hiện hành, **UW ≤ 200 toàn kỳ VÀ mọi năm** + CAGR ≥ CI-floor T170.
- u3 vs incumbent: maxDD ≤ −14.8% VÀ UW ≤ 115.
- u4 hiệu lực up-gate: UW(RA12) < UW(R up1.0) ở 2025 (up-gate chặt hơn thật sự cứu 2025) VÀ giữ được 2022 (≈ T170).
- u5 không phá uptrend tốt: CAGR 2023&2024 của RA12 ≥ 90% của gate-1.0 (up1.2 không cắt breadth quá tay ở up-regime tốt).
- THẮNG = RA12 đạt u1-u5. NULL = u2 vỡ (UW vẫn >200) hoặc breadth mất (u1 fail). HỖN HỢP = còn lại.

## 5. ĐO — metric tổng hợp/phân phối (KHÔNG khoá sym,start). Cùng cửa sổ 2021-07-01..2025-12-31, Oracle ARM64, per-year.

## 6. QUY TRÌNH
PREREG `docs/prereg/PREREG_REGIME_UPDOWN.md` (cặp RA12 khoá + sweep mô tả + u1-u5 + phán quyết + chống-overfit §1) commit TRƯỚC → tạo profile (RA12, RA14; regime CSV dùng lại Bước 2) → cổng OFF byte-identical T170 md5 → dừng shadow-c3 → sim tuần tự (T170 verify, RA12, RA14; R up1.0 dùng lại) → bật shadow-c3 verify → tính u1-u5 (`bigdown_struct.py`+`x1_rates.py`) per-year + đường cong up-gate {1.0,1.2,1.4} → `docs/result/RESULT_REGIME_UPDOWN.md` verdict → commit branch `module` (KHÔNG push) → dọn wfo_ds tạm, giữ printDone/sim.out.

## 7. Ý NGHĨA
- THẮNG (RA12 đạt u1-u5) ⇒ breadth CÓ giải được bằng regime-gate up/down đúng mức ⇒ shadow paper song song ≥1 tháng trước khi bàn đổi incumbent; và đây là tin lớn (ý Uni đúng).
- NULL ⇒ up-gate chặt để cứu 2025 thì mất breadth, hoặc vẫn vỡ ⇒ cùng với 3 bước reactive trước ⇒ ĐÓNG breadth long-only dứt khoát, ghi `power_wall.md`, chuyển TASK D.

## 8. Sau khi xong: cập nhật project memory (`round_2026-09-20...md` + `MEMORY.md`), báo MASTER: bảng T170/gate-1.0/R(up1.0)/RA12/RA14 (n_eff, ICC, maxDD, UW, CAGR+CI, per-year), đường cong up-gate, u1-u5 ✅/❌ cho RA12, verdict, cổng OFF PASS, mốc shadow, diff (kỳ vọng 0 Java).
