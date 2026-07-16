---
id: 144
status: BLOCKED
depends_on: [140]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/144.md
require_review: true
---

# TASK-144: Feature mới "pump-giữ-thanh-khoản" — re-export Java ff (CHỜ 140)

## Mục tiêu (1 câu)
Nếu task 140 cho thấy feature-set `pump` (phái sinh từ OI/orderflow) thắng → thử thêm feature THÔ mới mà
hiện chưa có (volume spike, spread thu hẹp, funding phase shift), cần re-export `ff_*.bin` từ Java.

## Điều kiện kích hoạt (Desktop mở BLOCKED→READY khi):
- Task 140 kết luận `pump` featset vượt `base`/`oi` rõ rệt → tín hiệu bơm-thanh-khoản CÓ giá trị →
  đáng đầu tư thêm feature thô. Nếu 140 cho thấy `pump` KHÔNG hơn → task này HỦY (không đáng công).

## Scope (khi mở)
**Trong scope:**
- Thêm feature vào `ExportFeaturesForPythonTool` (Java, nguồn sự thật): volume z-score, spread proxy,
  funding trend/phase, OI acceleration. Re-export `ff_*.bin` → dataset Kaggle mới.
- Chạy lại sweep 140 với feature-set mở rộng, so PnL-lite với featset cũ.

**Ngoài scope:** KHÔNG đổi label/engine. KHÔNG re-export nếu 140 chưa xác nhận pump có giá trị.

## HÀNG RÀO
- Heavy export → Oracle, không 226. Verify không OOM (OI merge 138M từng OOM câm). setsid nohup.
- Java là nguồn data; giữ provenance (ff mới phải track commit Java sinh ra nó).

## Acceptance criteria (khi mở)
- [ ] ff mới export sạch, manifest track provenance.
- [ ] Sweep lại: report so PnL-lite featset-mới vs cũ, pre-register ngưỡng cải thiện.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
