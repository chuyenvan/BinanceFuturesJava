# PROMPT KHỞI ĐỘNG SESSION MỚI (soạn 2026-07-30 tối) — copy nguyên đoạn dưới vào tin đầu tiên

Đọc theo thứ tự, ĐỪNG điều tra lại (đã đo xong toàn bộ, đây là facts đã chốt):

1. `docs/reports/ENTRY_ALPHA_STATE_AND_PLAYBOOK.md` — ĐỌC HẾT, đặc biệt §0.-1 (cập nhật
   2026-07-30, nối lên trên §0 gốc 07-29).
2. `docs/reports/HANDOFF_20260730_exit_min_ratchet.md` — chi tiết nhánh exit-formula + lý do
   N=13 confirm đang bị chặn.
3. `docs/reports/EXIT_MACHINE_20260730_stop_schedule.md` — algebra exit đầy đủ (PHẦN 1-3).
4. `docs/reports/AUDIT_20260730_wfo_constraint_harness.md` — audit constraint (bước 1 gốc),
   L1-L6 + P0-P6.
5. `docs/SESSION_START.md` §0.-1 và §0.0 (banner, đã trỏ đúng các file trên).
6. `docs/INFRA_FACTS.md` (Oracle ce / Kaggle / gotchas / fire-and-forget / TICKER_SOURCE env
   là no-op).

Tóm tắt để bắt nhịp (đã đo xong, đừng lặp lại):
- Verdict M (07-29): entry-alpha KHÔNG đóng. Selector rank-skill THẬT + TRẢI RỘNG (không chỉ
  w15). Bottleneck = WFO/HPO harness tự loại window đang lãi, KHÔNG phải gate/selector/regime.
- Audit harness (07-30 sáng, bước 1 của NEXT gốc — XONG): xác nhận + định lượng L1 (ordering
  bug: TOO_FEW_TRADES reject cao hơn CAPITAL_LOCK) + L2 (fitness cưỡng chế đánh lướt khi
  CAPITAL_LOCK bind) + exit machine vỡ 2 chỗ (dead zone arm→ratchet, giveback đảo dấu min/max).
- Uni đọc audit rồi RẼ HƯỚNG sang exit-formula (bước 2-3 gốc — fix fitness mismatch, bỏ HPO
  argmax — TẠM DỪNG, chưa làm). 3 việc exit đã xong + commit:
  `3e66898` min-rate SL 0.01032→0.03 (khớp sweep TASK-139 đo từ 07-07, chưa từng áp dụng),
  `ccc05dc` đồng bộ 2 gene range cũ (WFORunner/SensitivityTool),
  `b203a78` ratchet decoupling env-gated (`TS_RATCHET_DECOUPLED`, mặc định OFF, chưa bật thử).
- CHẶN: N=13 window confirm cho min-rate 0.03 — jar sẵn (`binance-exit003-20260730.jar`, md5
  verify OK) nhưng job store Aerospike fanout (`103.157.218.226:3222`) đang FAILED 9/16 window,
  chưa rõ nguồn gốc, chưa an toàn để bắn lại. Đã hỏi Uni cách xử lý — **kiểm tra xem đã có câu
  trả lời chưa trước khi làm gì tiếp** (nếu chưa, hỏi lại, đừng tự quyết).

NEXT — 2 nhánh đang mở, Uni chọn nhánh nào làm trước (hoặc tuần tự cả hai — KHÔNG chạy 2 job
nặng cùng lúc trên Oracle, 1 box, disk 89%):

**NHÁNH A (harness — bước 2-3 gốc, CHƯA làm):**
2. Fix fitness mismatch: HPO chọn genome bằng Calmar nhưng chấm bằng raw-PnL-WFE → align.
3. (chỉ nếu 2 chưa đủ) bỏ per-window HPO argmax → genome regularized.
4. N=30 full 13-window confirm sau MỖI bước (số hiện tại N=1, chưa production-ready).

**NHÁNH B (exit-formula — tiếp việc tối 07-30):**
1. Giải quyết chặn N=13 confirm — kiểm tra lại `wfo_status` trước; nếu job store sạch, dùng
   `wfo_run` (Oracle-only, 1 window, đúng mục đích debug/verify) thăm dò trước khi bắn
   `wfo_fanout` 6-node (2 Oracle + 5 Kaggle) thật.
2. Sau N=13 confirm chạy xong với min-rate 0.03: so với verdict M gốc, ghi vào
   `EXIT_MACHINE_20260730_stop_schedule.md` (thêm PHẦN 4).
3. Bật thử `TS_RATCHET_DECOUPLED=true`, chạy 1 confirm RIÊNG — đừng gộp 2 biến (min-rate +
   ratchet) vào 1 lần đo, dễ confound.
4. Sửa `gap = min(peak×giveback, TS_MAX_GAP)` → `max(peak×giveback, minGap)` (P6, giveback đảo
   dấu cắt đuôi lãi lớn) — chưa làm, việc cuối của nhánh exit.

Quy tắc vận hành (không đổi từ đầu chiến dịch): job dài = fire-and-forget (launch detached,
verify bước đầu, thoát, KHÔNG poll tới xong — đốt token). KHÔNG chạy 2 WFO nặng cùng lúc trên
Oracle. Compute nặng ưu tiên Kaggle fleet. Trả lời tiếng Việt, giữ thuật ngữ English.
Verdict/PnL/commit thuộc Uni — không tự quyết PASS/FAIL hay đổi ngưỡng sau khi đã thấy số
(pre-register). Code nhánh exit (3 việc trên) ĐÃ COMMIT — không cần hỏi lại trước khi đọc/build,
nhưng bất kỳ THAY ĐỔI HÀNH VI MỚI (bật `TS_RATCHET_DECOUPLED`, đổi default nào khác) vẫn phải có
xác nhận của Uni trước khi coi là final/production.

Bắt đầu bằng: xác nhận đã đọc xong bằng cách nói lại (a) trạng thái 2 nhánh A/B hiện tại,
(b) lý do N=13 confirm đang bị chặn, (c) Uni muốn làm nhánh nào trước — rồi mới hành động.
