---
id: 155
status: DOING
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/155.md
require_review: true
---

# TASK-155 [BASELINE MODEL] — Train selector trên label CHIẾN LƯỢC: maxFav_H ≥ 3% (chạm +3%)

## Mục tiêu (1 câu)
Train model tầng 1 (entry) trên đúng label chiến lược Uni ("chạm +3% trong H giờ" = success, arm SL+1%),
tạo baseline model + predict_wf để Java xác nhận, đo precision vs random baseline.

## Bối cảnh (chốt 2026-07-11)
- Mô hình 3 trạng thái: chạm +3% → arm SL+1% (success, dù ăn non +1% hay nuôi lãi). Không chạm +3% → DCA.
- **Ranh giới success/fail tầng 1 = `maxFav_H ≥ 0.03`** (định nghĩa A đúng — SL arm SAU +3% nên nhịp rớt
  trước đó không giết lệnh; định nghĩa B của task 153 là mô hình SAI, đã bỏ).
- 153 đo: selector (cũ, label 6%) đã có edge THẬT ở A: 4h +28đ% (60% vs 32%), 24h +17đ%, 72h +10đ% (bão hòa).
- **Horizon chọn: 4h** (baseline random thấp nhất 32% + edge dày nhất) — 72h bão hòa (76%, model vô dụng).
- Featset: base+oi+pump (pump = oi×taker, ls-skew... — thắng ở sweep 140).

## Scope
**Trong scope:**
1. Train WF leak-free (label `maxFav_H ≥ 0.03`, cả 4 horizon một lần) trên Kaggle → 17 fold predict_wf.
   Kernel `chuyendinh/baseline-maxfav3` (đã push, RUNNING).
2. Trong kernel: log base-rate + precision top-5 mỗi fold để so ngay với 153.
3. Khi xong: pull predict_wf → build `wfo_dataset_v6` → Java sim horizon 4h (WFO_SEL_HORIZON_IDX=0)
   + ladder + so v4(ret2)/v5(candidate). Cũng thử idx=2 (24h) cùng predict_wf.

**Ngoài scope:** KHÔNG đổi cơ chế exit/DCA (tầng 2/3). Chỉ train + xác nhận entry model.

## Pre-register
- Baseline model "thắng" nếu: precision top-5 (maxFav_4h≥3%) > 60% (vượt model cũ ở 153) VÀ khi vào Java
  cho nhiều quý-có-trade hơn v4 với CAGR ≥ v4.
- Nếu precision ≈ model cũ (60%) → label mới không thêm giá trị so 6% → ghi nhận, cân nhắc horizon khác.

## Acceptance criteria
- [ ] predict_wf 17 fold, leak-free, label maxFav≥3%.
- [ ] Bảng precision vs random per horizon (so 153).
- [ ] wfo_dataset_v6 + Java sim 4h: ladder năm/6th/quý + CAGR + số quý-trade vs v4/v5.
- [ ] Verdict pre-register.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
