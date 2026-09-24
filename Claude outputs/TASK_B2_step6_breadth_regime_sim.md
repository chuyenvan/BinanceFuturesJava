# TASK B2 Bước 6 — SIM regime-gate bằng MARKET-BREADTH (ý Uni, regime đầu tiên qua cổng phủ) — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni.
Tiền đề: `DIAG_BREADTH_REGIME.md` (`3536a2a`/`4f4801c`/`dee1672`) — market-breadth (% top-50 trên MA200 < 50%) là regime DUY NHẤT trong 7 hướng phủ được CẢ UW-2022 (92.7%) LẪN UW-2025 (70.9%), cả hai ≥60%. B (BTC+ETH hướng-giá) và C (BTC-đơn) đều mù 2025. Quét: 6/6 tổ hợp MA200 pass 2025 (robust).

## Cảnh báo khoá TRƯỚC (dự báo MASTER — chống giải-thích-xuôi)
Phủ thời-gian UW ≠ đánh dấu đúng lệnh xấu. Edge độc lập (DIAG): khi breadth-notup, ROI sổ T100 vẫn +1.99%, loss-rate/phi KHÔNG cao hơn lúc breadth-up (phi thấp hơn: 1.91 vs 2.18); forward BTC return notup còn > up. VÀ breadth<50% xảy ra >55% ngày mỗi năm (trạng thái thường, không hiếm). ⇒ MASTER dự báo 2 rủi ro: (i) notup quá thường xuyên → gate chặt phần lớn thời gian → hệ về gần T170 → **n_eff không đạt ×1.5 (u1 fail)**; (ii) chặt lúc breadth thấp cắt cả lệnh tốt → **CAGR giảm (u5 fail)**. Có thể NULL. Điểm mới đáng theo dõi: **UW-2025 có thể lần đầu về ≤200** (regime này chặt nhiều ở 2025: notup 72.9% vs MA200 26.8%). Sim phân giải.

## 0. LUẬT — như B2 (không nới)
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (`free -g`≥12G, `pgrep java` rỗng → dừng shadow-c3 trước sim, bật ngay sau, ghi mốc); PREREG trước; cổng tái lập T170 md5 `efb793e2`; cổng OFF byte-identical; `x1_rates.py --appetite current --k`; per-year; logging chuẩn.

## 1. CƠ CHẾ (0-diff Java kỳ vọng — dùng hạ tầng có sẵn)
Regime CSV mới `regime_daily_breadth.csv` sinh từ `breadth_regime.py` (đã có): `not_up(D) = breadth_top50_MA200(D) < 50%`, causal (dùng dữ liệu ≤ D-1). Đưa vào `GATE_REGIME_ADAPTIVE`+`RegimeSchedule`+`SIM_REGIME_SCALE_UP` (hạ tầng Bước 2/4, 0-diff Java, chỉ đổi CSV `SIM_REGIME_FILE`+profile). Xác nhận OFF byte-identical.

## 2. BIẾN THỂ (khoá PREREG)
Baseline (không tính k): T170, gate-1.0. 
- **BR (chính, khoá)**: regime=breadth, up→1.0 / not_up→1.7. (up-gate 1.0 vì breadth đã notup nhiều ở 2025 — không cần siết up thêm; giữ đơn giản như R Bước 2.)
- **BR0 (đối chứng)**: gate cố định đều khớp tổng số lệnh ≈ BR (tách "nhắm breadth-regime" khỏi "giảm chung"). Nội suy log-tuyến tính như Bước 2/4.
Nếu Bước 6 cho n_eff BR quá thấp (u1 fail vì notup thường xuyên) → đó là kết quả, KHÔNG mở biến thể up1.2/ngưỡng khác trong round này (chống dredging); ghi nhận cho round PREREG riêng nếu muốn.

## 3. TIÊU CHÍ (khoá trước; UW-2025 là điểm mới, breadth là ràng buộc)
- u1 breadth: n_eff_total(BR) ≥ 1.5× T170 (=909).
- u2 khẩu vị: PASS hiện hành, **UW ≤ 200 mọi năm** (đặc biệt 2025 — cái mọi regime trước vỡ) + CAGR ≥ CI-floor T170.
- u3 vs incumbent: maxDD ≤ −14.8% VÀ UW ≤ 115.
- u4 nhắm đúng (BR vs BR0): UW(BR) < UW(BR0) toàn kỳ VÀ đặc biệt UW-2025(BR) < UW-2025(BR0) — bằng chứng breadth-regime cắt đúng, không phải giảm chung.
- u5 giữ uptrend: CAGR 2023&2024 BR ≥ 90% gate-1.0 (không cắt nhầm lệnh tốt lúc breadth thấp trong năm tốt).
- THẮNG = BR đạt u1-u5 (đặc biệt là regime ĐẦU TIÊN đạt u2 với UW-2025≤200). NULL = u1 fail (mất breadth) hoặc u2 vỡ (UW vẫn >200) hoặc BR0 ngang BR (u4). HỖN HỢP = còn lại.

## 4. ĐO — metric tổng hợp/phân phối (KHÔNG khoá sym,start). Cùng cửa sổ 2021-07-01..2025-12-31, per-year.

## 5. QUY TRÌNH
PREREG `docs/prereg/PREREG_BREADTH_GATE_SIM.md` (cơ chế + biến thể + u1-u5 + **dự báo cảnh báo §trên** + phán quyết) commit TRƯỚC → sinh CSV regime breadth + profile BR/BR0 (dùng `SIM_REGIME_SCALE_UP`; nếu buộc sửa .java thì tối thiểu + OFF byte-identical) → cổng OFF T170 md5 `efb793e2` → dừng shadow-c3 → sim tuần tự (T170 verify, BR, BR0) → bật shadow-c3 verify → tính u1-u5 (`bigdown_struct.py`+`x1_rates.py`) per-year → `docs/result/RESULT_BREADTH_GATE_SIM.md` verdict + đối chiếu dự báo → commit branch `module` (KHÔNG push) → dọn wfo_ds tạm, giữ printDone/sim.out.
OFF không byte-identical → DỪNG, báo MASTER.

## 6. Ý nghĩa
THẮNG (đặc biệt UW-2025 lần đầu ≤200 mà giữ breadth+CAGR) ⇒ ý Uni (market-breadth) giải được cái 7 hướng trước không ⇒ shadow forward ≥1 tháng trước khi bàn đổi incumbent; kết quả dương đầu tiên của breadth. NULL ⇒ breadth-regime phủ đúng thời gian nhưng không cắt đúng lệnh (như dự báo) ⇒ đóng breadth vĩnh viễn, TASK D là hướng chính.

## 7. Sau khi xong: cập nhật project memory (`round_2026-09-20...md`+`MEMORY.md`), báo MASTER: bảng T170/gate-1.0/BR/BR0 (n_eff, ICC, maxDD, UW, CAGR+CI, per-year), u1-u5 ✅/❌, verdict, đối chiếu dự báo (n_eff có tụt không, CAGR uptrend có mất không, UW-2025 có về ≤200 không), cổng OFF PASS, mốc shadow, diff Java.
