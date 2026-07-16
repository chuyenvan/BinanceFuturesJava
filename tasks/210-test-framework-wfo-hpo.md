---
id: 210
status: TODO
depends_on: [200]
touches_live_process: false
writes_242_data: false
resource: local
checkpoint: false
max_retry: 2
report: docs/reports/210.md
require_review: true
---

# TASK-210 [WS2] — Unit-test framework WFO/HPO (chạy LOCAL, không Aerospike)

## Mục tiêu (1 câu)
Test tự động cho logic lõi WFO/HPO đọc file bin — bắt lỗi parse/cửa-sổ/horizon TRƯỚC khi chạy thật.

## Scope
**Trong:** thêm JUnit vào pom + tạo `src/test/java`; test: (a) `WfoDataset` parse `market.bin/pred.bin/funding.bin` (count, md5 verify fail-fast), (b) số cửa sổ WFO = 17 + biên train/OOS/embargo đúng, (c) `buildFundingFromWfFiles` decode horizon (score = 1−P(win), đảo dấu đúng `decodeSelectorMapToPrimitiveArray`), (d) fold count. Dùng fixture bin nhỏ tự sinh.
**Ngoài:** test cần Aerospike/226 (đó là integration, không phải unit).

## Bối cảnh
- Repo CHƯA có `src/test`; JUnit chưa khai pom → task này thêm (bump nhẹ, review). Nếu Uni không muốn đụng pom → fallback `mainX()` assert tay.
- Nguồn: `WFO_DATAFLOW §4-6`, `WfoDataset.java`, `WfoCoordinator.java`.

## Acceptance (kiểm-được-bằng-máy)
- [ ] `mvn test` xanh; ≥4 test nêu trên PASS.
- [ ] Test md5-mismatch → fail-fast đúng (assert throw).
- [ ] Không `System.out` trong test util.

## (Code điền) Kết quả / Phát hiện / Quyết định
