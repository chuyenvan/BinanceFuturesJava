---
id: 200
status: TODO
depends_on: []
touches_live_process: false
writes_242_data: false
resource: local
checkpoint: false
max_retry: 2
report: docs/reports/200.md
require_review: true
---

# TASK-200 [WS0] — Nền Preflight Gate: skeleton + compile + hook stub

## Mục tiêu (1 câu)
Có bộ khung `ai_ml/validation/preflight` compile được để WS1 fan-out cắm 19 validator vào.

## Scope
**Trong:** 7 class skeleton đã dựng (`Severity, CheckId, ValidationResult, DataValidator, PreflightContext, ExpectedRanges, ValidationReport, PreflightGate`); `mvn compile`; chạy `PreflightGate.main` rỗng.
**Ngoài:** implement validator con (WS1); cắm hook vào `WfoCoordinator` (task 206); đụng pom test (task 210).

## Bối cảnh
- Spec: `docs/DATA_VALIDATION_FRAMEWORK.md` §2-3. Roadmap: `docs/VALIDATION_TEST_ROADMAP.md` §1.
- Skeleton viết ở phiên Cowork 2026-07-11 (chưa machine-compile — sandbox thiếu javac).

## Acceptance (kiểm-được-bằng-máy)
- [ ] `mvn -q -o compile` PASS (không lỗi package preflight).
- [ ] `java ... PreflightGate docs/reports/preflight_smoke.md` exit 0, ghi report VERDICT PASS (0 validator).
- [ ] Không `System.out`; log SLF4J; Java 11.

## (Code điền) Kết quả / Phát hiện / Quyết định
