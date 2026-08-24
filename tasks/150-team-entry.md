---
id: 150
status: NEEDS_HUMAN
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/150.md
require_review: true
---

# TASK-150 [TEAM ENTRY] — Tối ưu PHẦN 1: chọn coin + sizing ban đầu

## Mục tiêu team (1 câu)
Tăng **tần suất cơ hội** (số quý có kèo) mà giữ/nâng tỉ lệ success, để hệ hết "nằm im 60% thời gian" —
ràng buộc then chốt đã đo. Đây là phần quyết định trần của cả hệ.

## Bộ chỉ tiêu (WFO, pre-register — verdict Uni)
- PRIMARY: **số quý có ≥10 lệnh** (tần suất cơ hội) — mục tiêu tăng rõ so với ret2 (9/22 quý dương hiện tại).
- Tỉ lệ success (kèo giữ được lãi tới cuối horizon) KHÔNG tệ hơn ret2.
- CAGR full-history (giữ 2 phần kia baseline) ≥ ret2 (4.2%/năm).
- Bậc thang: năm → 6 tháng → quý (đếm kỳ dương).

## Baseline CỐ ĐỊNH 2 phần kia (KHÔNG đụng — để cô lập biến Entry)
- Phần 2 (success): `TS_GIVEBACK_RATIO=1.0`.
- Phần 3 (fail): DCA mặc định, `TIME_STOP_HOURS=0`, `HARD_STOP_LOSS_RATE=0`.

## Scope
**Trong scope:**
1. **Bước A (SẴN SÀNG):** candidate `0.01|72h|pump` — predict_wf đã sinh xong 17 fold (Kaggle
   `selector-wf-pred-cand`, tại `/home/ubuntu/claudedata/wf_pred_cand`, +fold 2026 v2). Ghép → export
   `wfo_dataset_v5` với `WFO_SEL_HORIZON_IDX=3` (72h) + `WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/wf_pred_cand`.
   Verify funding.bin phủ 2026Q1 (>0 records) trước khi sim (bài học: v3 thiếu 2026).
2. Java sim full-history v5 (baseline 2 phần kia) + TraceData2Test + ladder_analyze → bậc thang.
3. So thẳng với ret2 (v4): số quý trade, CAGR, bậc thang. Pre-register verdict.
4. **Bước B (chỉ nếu A pass):** meta-labeling (model-2 P(success|tín hiệu) → size động) hoặc nới thêm
   gate threshold. Báo Desktop trước khi làm B.

**Ngoài scope:** KHÔNG đổi giveback/DCA/SL (phần team khác). KHÔNG build jar (báo nếu jar thiếu biến).

## HÀNG RÀO
- **CÁCH LY THU MUC (bat buoc — 3 team chay song song tren cung Oracle):** worker copy simulator sang
  thu muc rieng `/home/ubuntu/team_entry/simulator/` (cp -r tru jar; symlink jar chung read-only), chay
  o do → storage/OrderTestDone.data + config.properties RIÊNG, KHÔNG đụng team khác. TUYET DOI khong ghi de
  jar chung khi team khac dang chay.
- pgrep rỗng trước jar. setsid nohup. Verify env `WFO_FUNDING_PRED_DIR`+`WFO_SEL_HORIZON_IDX` trước export
  (lỗi env rỗng → fallback set leaky câm, đã trả giá). `SIM_END_DATE=20260601`.

## Acceptance criteria
- [ ] `wfo_dataset_v5` export sạch, funding phủ 2026Q1, manifest provenance = cand-0.01-72h-pump.
- [ ] Bảng so v5 vs v4: số quý trade, CAGR, bậc thang năm/6th/quý.
- [ ] Verdict pre-register: PASS (nhiều cơ hội hơn + không tệ success) / FAIL (không hơn ret2).
- [ ] Nếu FAIL → ghi thẳng "entry kịch trần" → tín hiệu cho Desktop chuyển framework §3.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
