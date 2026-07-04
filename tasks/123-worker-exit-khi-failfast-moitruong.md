# TASK-123: WfoWorker exit sớm khi FAIL-FAST lỗi môi trường (chống máy-xay-job) — STUB

- **status:** todo (phát hiện 2026-07-04: kernel-3 xay 15 job thành FAILED trong 4 phút,
  mỗi job 3s vì FAIL-FAST "khong co ticker ngay X" — lỗi MÔI TRƯỜNG lặp lại y hệt mọi job)
- Đề xuất: WfoWorker đếm FAIL liên tiếp cùng loại exception môi trường (FAIL-FAST ticker/config);
  ≥2 lần liên tiếp → log ERROR + exit(1) thay vì claim tiếp — job giữ nguyên FAILED có thể reset chạy node khác.
  Phân biệt với FAIL nội tại 1 job (OOM window nặng) — loại đó claim tiếp là đúng.
- Kèm: WfoCoordinator thêm lệnh `reset-failed` (chỉ FAILED→PENDING, giữ DONE) — hôm nay phải reset full mất 7 DONE.
## Kết quả
<.>
