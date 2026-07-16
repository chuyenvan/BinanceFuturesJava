---
id: 204
status: TODO
depends_on: [200, 202]
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 2
report: docs/reports/204.md
require_review: true
---

# TASK-204 [WS1-B] — Validator nhóm B: Leakage (B1-B4) [ĐẮT, sample]

## Mục tiêu (1 câu)
Chặn rò rỉ tương lai — loại lỗi ĐẢO NGƯỢC verdict (precision ảo "×2.4" từng là số leaky).

## Scope
**Trong:** `B1LabelOosValidator` (mỗi predict_wf: max(ts_train) < min(ts_oos) − embargo), `B2ShuffleTestValidator` (xáo nhãn → edge biến mất; so precision train vs OOS — có thể gọi script Python compare), `B3EmbargoValidator` (embargo ≥ max holding THỰC ĐO), `B4CrossSectionalLeakValidator` (population/basket/z-score/OI-merge chỉ tính từ dữ liệu ≤ t; không coin niêm yết tương lai trong cross-section). Random-sample phân tầng (tháng × tier), N=100/cell từ `PreflightContext.sampleSizePerCell`; B1/B4 thêm 100 mẫu quanh ±embargo mỗi biên fold.
**Ngoài:** đổi logic purge của pipeline pred (chỉ ĐO, báo nếu sai).

## Bối cảnh
- `ValidateFundingOOS`, `gen_funding_wf_predictions.py` (purge 72h). Bài học: `DATA_VALIDATION_FRAMEWORK §5.2`.

## Acceptance (kiểm-được-bằng-máy)
- [ ] B1 kiểm mọi fold, metrics gap train↔oos (phút) ≥ embargo.
- [ ] B3 so embargo khai báo vs max-holding đo từ sim.
- [ ] Sample đủ N mỗi cell (không sample mù).

## (Code điền) Kết quả / Phát hiện / Quyết định
