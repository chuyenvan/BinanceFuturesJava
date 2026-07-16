---
id: 206
status: TODO
depends_on: [201, 202, 203, 204, 205]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 2
report: docs/reports/206.md
require_review: true
---

# TASK-206 [WS1] — Cắm 21 validator + cổng 2-tầng + hook WfoCoordinator

## Mục tiêu (1 câu)
Gate chạy đủ 21 check theo 2 tầng (FAST inline + SLOW stamp), THẬT SỰ chặn WFO/HPO khi data hỏng/chưa validate.

## Scope
**Trong:** đăng ký 21 validator trong `PreflightGate`; gọi `assertReadyForWfo(ctx, fingerprint, env, stampPath, reportPath)` ở đầu `WfoCoordinator.init()/reset()` (trước `buildJobs`); `runFullAndStamp` chạy ngoài theo trigger; fingerprint = md5 manifest WFO dataset; nạp `ExpectedRanges` từ `validate_criteria.md`; test chặn bằng data giả hỏng + test thiếu stamp.
**Ngoài:** đổi logic WFO khác.

## Acceptance (kiểm-được-bằng-máy)
- [ ] `PreflightGate.run(ctx, ALL)` trả 21 kết quả trên data thật; report markdown đầy đủ bảng.
- [ ] FAST có BLOCK-fail → `WfoCoordinator reset` THROW + exit 1 (KHÔNG buildJobs).
- [ ] Không stamp SLOW / md5 đổi / đổi env → `assertReadyForWfo` THROW (bắt chạy full ngoài).
- [ ] `runFullAndStamp` PASS → ghi stamp; WFO sau khớp stamp → chạy tiếp không lặp SLOW.
- [ ] `CONFIG_VERSION` bump nếu hành vi backtest đổi.

## (Code điền) Kết quả / Phát hiện / Quyết định
