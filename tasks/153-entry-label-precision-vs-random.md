---
id: 153
status: REVIEW
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/153.md
require_review: true
---

# TASK-153 [ENTRY-LABEL] — Đo PRECISION label mới (đạt +3%) vs BASELINE RANDOM

## Mục tiêu (1 câu)
Trả lời phép đo bản lề: với label mới của Uni ("entry chọn coin đạt max +3% trong H giờ → arm SL-lãi-1%"),
selector CÓ edge thật so với chọn ngẫu nhiên không, và horizon nào cho biên edge dày nhất (baseline thấp).

## Bối cảnh (chốt với Uni 2026-07-11 — BA TRẠNG THÁI)
Một entry rẽ 3 luồng:
- **Chạm +3% trong H giờ** → arm SL cứng +1% → CHẮC CHẮN THẮNG (tệ nhất +1% nếu rẽ xuống = ăn non; tốt
  nhất nuôi lãi dài). SL +1% chỉ quyết định thắng-ít-hay-nhiều (tầng 2), KHÔNG quyết định thắng/thua.
- **Không chạm +3%** → không có SL cứng → FAIL tầng entry → vào luồng DCA (tầng 3).
- → **Ranh giới success/fail tầng 1 CHỈ LÀ: có chạm +3% hay không.** `precision(maxFav_H ≥ 3%)` CHÍNH LÀ
  tỉ lệ thắng của hệ. KHÔNG cần điều kiện maxAdv (đó là chuyện tầng 2 — nuôi được bao xa).
- Nguyên lý: baseline (random) THẤP thì mới dễ có edge dày. Horizon ngắn (4h/24h) → baseline thấp hơn 72h.
- "Chạm +3%" = có ≥1 nến 1m close ≥ +3% = `maxFav_H ≥ 0.03` trong label CSV → đo CHÍNH XÁC, không cần path.

## Scope
**Trong scope (Kaggle, dùng label CSV có sẵn, KHÔNG cần train):**
1. Với mỗi horizon H ∈ {4h, 24h, 72h}, success = **`maxFav_H ≥ 0.03`** (chạm +3% — ranh giới DUY NHẤT tầng 1).
   Thử thêm target = {+2%, +3%, +4%} để xem đường cong precision-vs-baseline theo ngưỡng.
2. Đo 3 lớp precision cho mỗi (H, định nghĩa):
   - **(1) Selector hiện tại:** với mỗi kỳ, lấy top-N coin theo score `predict_wf` (dùng pred ret2 sẵn có
     hoặc score selector), tính % đạt success.
   - **(2) Random:** chọn N coin ngẫu nhiên mỗi kỳ (seed cố định, lặp 20 lần lấy trung bình), % success.
   - **(3) Edge = (1) − (2).**
3. Bảng kết quả: H × {A,B} × {precision_selector, precision_random, edge, n_kỳ, n_coin_tb}.

**Ngoài scope:** KHÔNG train model mới (chỉ đo trên score sẵn có). KHÔNG path 1m (bước Java sau).

## Pre-register (ghi TRƯỚC khi nhìn số)
- Label "có edge đáng train" nếu: tồn tại ≥1 horizon mà **edge (1)−(2) ≥ 10 điểm %** VÀ baseline random ≤ 60%.
- Nếu mọi horizon: baseline cao (>70%) HOẶC edge < 5 điểm % → "chọn coin không thêm giá trị cho ngưỡng
  này" → báo thẳng, KHÔNG train tiếp.

## Acceptance criteria
- [ ] Bảng H×{A,B}×{sel, random, edge} đầy đủ 3 horizon.
- [ ] Chỉ rõ horizon cho baseline thấp nhất + edge dày nhất (khuyến nghị horizon để train).
- [ ] Verdict pre-register: có edge đáng train / không.
- [ ] Ghi rõ B là xấp xỉ (path thật cần 1m ticker — Java bước sau).

## Kỹ thuật
- Dùng harness kiểu `sweep_harness.py` đã có (load label CSV + score). Kernel self-contained (inline, không
  sibling import — bài học). Path resolver `/kaggle/input/**`. Score selector: dùng `predict_wf_*.bin` ret2
  đã có trên dataset, hoặc nếu không có trên Kaggle dataset thì báo cần upload.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
