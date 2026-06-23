# rules/task-workflow — Luật khi nhận & chạy task (nhiều CCD)

> Đọc cùng [CORE](../CORE.md). Cơ chế điều phối đầy đủ: [AGENT_WORKFLOW](../AGENT_WORKFLOW.md). Bản đồ CCD đang làm gì: [AGENTS](../AGENTS.md).

## Ai claim / đóng task — KHÁC nhau theo cách chạy
- **QUA supervisor (headless):** supervisor claim atomic (`os.mkdir locks/<id>`) + set `status: DOING/DONE/...` + sở hữu `runtime_state.json`. **Worker KHÔNG ghi `AGENTS.md`, KHÔNG tự set `status`** (AGENT_WORKFLOW §6 — giảm race). Worker chỉ: làm task + ghi report + block RESULT.
- **Chạy TAY (CCD/CDK thủ công):** tự claim — ghi `owner` + `status: DOING` + `updated` vào header `tasks/<id>.md` (CDK cập nhật `AGENTS.md`) RỒI mới làm. Task đã có owner KHÁC + DOING + `updated` còn mới → KHÔNG đụng, báo user. Heartbeat: cập nhật `updated` mỗi commit/đổi bước; DOING mà `updated` quá cũ (≳2h) + nghi reset → STALE, reclaim được. Đóng: `DONE` + commit hash; cần soát → `REVIEW`. Một task = một owner.

## Tròn việc hoặc thành Task — chống job nửa chừng / chờ mù (đọc cùng [CORE](../CORE.md))
Pain thực tế: job nền không biết xong chưa → hỏi "chạy tới đâu" nhiều lần, chờ vô dụng, mất time; hoặc bỏ dở giữa chừng khi đổi hướng → process mồ côi. Luật chặn:

**Hai trạng thái kết thúc hợp lệ — không có trạng thái thứ 3:**
1. **TRÒN ngay trong phiên:** việc đủ ngắn để chạy xong + **VERIFY bằng số** (đo dữ liệu, không phải "lệnh chạy xong"). Vd: re-export 1 tháng → đếm NaN/records ngay.
2. **THÀNH TASK:** việc dài/không chắc xong → tạo `tasks/<id>.md` front-matter đủ (`id/status/depends_on/checkpoint/max_retry/report`) + mục "Job đang chạy" (bàn giao) + acceptance (verify gì, ngưỡng PASS pre-register). Đưa vào supervisor/queue để theo dõi.

**BẮT BUỘC thành task (không được ad-hoc nền) khi:** việc > ~vài phút, HOẶC distributed (Kaggle/queue), HOẶC ghi data thật (Aerospike/242/bộ file lớn), HOẶC không chắc xong trong phiên.

**Trước khi spawn job nền — checklist 3 điểm (thiếu 1 → KHÔNG chạy, chuyển thành task):**
- [ ] **Đo tiến độ:** có cách biết đang tới đâu (queue status / done-count / log mốc-bước có timestamp, ghi nơi bền). KHÔNG dựa "đoán đang chạy".
- [ ] **Kết thúc:** điều kiện dừng rõ + ước lượng thời gian + (Kaggle) checkpoint-resume.
- [ ] **Verify:** định trước đo gì để biết ĐÚNG khi xong (pre-register acceptance, tránh hợp-lý-hóa hậu kỳ).

**Đổi hướng giữa chừng:** việc đang dở phải DỪNG sạch — kill đúng PID mình spawn ([run-226](run-226.md)) + ghi trạng thái lại (task/report) — hoặc chốt thành task resume được. CẤM để process mồ côi chạy nền không ai theo dõi (ăn tài nguyên + nhiễu + sau này không biết tin output hay không).

**"Done" = bằng chứng đo**, không phải "đã chạy xong lệnh" (validate dữ liệu là cổng).

## BÀN GIAO job nền (BẮT BUỘC — mọi cách chạy, ngay khi spawn job lâu)
Ghi vào `tasks/<id>.md` mục "Job đang chạy" đủ để CCD KHÁC tiếp quản nếu mình chết:
- **kernel slug (Kaggle)** hoặc **PID + host (226)**; lệnh + jar + args + dataset/env; **output path**; cách check trạng thái; **các bước còn lại** (lấy output → verify gì → bước tiếp).
- Mục tiêu: CCD khác đọc task là làm tiếp được, KHÔNG chạy lại từ 0. Cập nhật mỗi mốc (launch / checkpoint / xong).

## CHECKPOINT-RESUME job dài (đặc biệt Kaggle ~12h)
Kaggle cắt kernel ~12h → job lâu hơn mà không checkpoint = bị giết rồi chạy lại từ 0 (lặp vô hạn, không bao giờ xong). Job đọc nhiều năm / khối lớn PHẢI: (a) ghi tiến độ nơi BỀN (set Aerospike checkpoint / output partial / file 226) theo đơn vị (tháng/ngày/batch symbol); (b) chạy lại = resume-skip-done; (c) output tăng dần (append/partial). Ước job >~10h → CHIA NHỎ trước khi chạy.

## System.exit + dọn tài nguyên (chi tiết: CORE · run-226 · KAGGLE_RULES)
- Tool batch: `System.exit(0)` cuối main (xem [CORE](../CORE.md)) — thiếu → kernel treo tới 12h, mất output.
- Xong việc dọn NGAY: Kaggle stop kernel đã xong + kernel treo (zombie ăn quota + chiếm slot); 226 kill ĐÚNG PID mình spawn ([run-226](run-226.md)); python đóng process/temp.

## Output contract (worker kết thúc report bằng block này — AGENT_WORKFLOW §4)
```
=== RESULT ===
STATUS: DONE | REVIEW | NEEDS_HUMAN | FAILED
COMMIT: <hash | ->
ARTIFACTS: <path | ->
VERIFY: <số đối chiếu acceptance | ->
DECISIONS: <quyết-định reversible đã tự ra | ->
QUESTIONS: <gom 1 lần, chỉ câu thật cần người | ->
=== END ===
```
Thiếu/sai format → `NEEDS_HUMAN` (không đoán). Cấm hỏi giữa chừng — gom cuối.
