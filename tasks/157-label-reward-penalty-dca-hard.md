---
id: 157
status: REVIEW
owner: CCD-157
updated: 2026-07-16 23:25 +07
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: true
max_retry: 2
report: docs/reports/157.md
require_review: true
---

# TASK-157 [LABEL DCA-CỨNG] — Selector label reward–penalty: thưởng chạm +3%/4h, phạt theo độ âm tại mốc 4h

## Bối cảnh (Uni chỉ hướng 2026-07-16)
Đang cân nhắc BỎ DCA martingale → chuyển "DCA cứng" (nhồi đúng 1 lần tại mốc 4h nếu chưa chạm TP).
Nếu bỏ DCA thì có thể bỏ luôn gate (gate đang chặn làm nhiều quý ít trade — giá trị gate chủ yếu bảo vệ DCA).
Hệ quả: label selector phải đổi — không chỉ hỏi "có chạm +3% không" (binary, task 155) mà phải PHẠT
những kèo hụt TP và đang âm sâu tại mốc 4h (chỗ DCA cứng sẽ đổ thêm vốn).

## Label mới (utility U, đơn vị return; ghép từ cột CÓ SẴN trong funding_label.csv — đúng nguyên tắc
H1 xuất thô / H2 áp ngưỡng, KHÔNG cần export Java mới)
```
hit = (maxFav_4h >= 0.03) và (nBars_4h >= 16)
U   = x                        nếu hit
U   = y × min(retEnd_4h, 0)    nếu không hit  (hụt TP nhưng về hòa/dương → 0, không phạt)
```
- **x = 0.02** (+2%): chạm +3% → arm SL+1% (cơ chế 3 trạng thái Uni) → thực nhận kỳ vọng nằm giữa
  +1% và +3%+, trừ phí+slippage 2 chân ≈ +2%. (x chỉ dịch/scale nhánh thưởng — ranking ít nhạy với x,
  nhạy với TỈ LỆ x/y; nên cố định x, quét y.)
- **y ∈ {1.0, 1.5, 2.0}**: DCA cứng tại mốc 4h = nhân đôi exposure vào lệnh đang âm → tổn thất tại đó
  đáng phạt hơn 1×. y=1 trung tính, **y=1.5 mặc định**, y=2 phạt nặng.

## Mục tiêu (1 câu)
Train thử selector regression trên U (3 biến thể y) + baseline binary maxFav3 CÙNG data/fold, đo edge
trên TEST 12 tháng OOS theo methodology top-5/kỳ-4h (task 153) → verdict label mới có đáng đi tiếp không.

## Scope
**Trong:**
1. Kernel Kaggle 1 script tự-chứa (`ml/funding_selector/kaggle_dca_hard/train.py`), dataset có sẵn:
   `funding-tool1-features` + `funding-oi-percoin` + `funding-label-full` (45 feat, lưới 15m — y hệt 108/155).
2. Time-split chuẩn train_funding_selector (train / val 6m / test 12m, purge 4h, không shuffle).
   4 model: binary(maxFav3) + reg(U, y=1/1.5/2). XGBoost hist CPU, params chuẩn selector.
3. Đo trên TEST, mỗi kỳ = block 4h KHÔNG chồng lấn, top-5 theo score (như 153):
   precision(maxFav≥3%), mean U_eval, mean độ-âm retEnd_4h của pick FAIL, so random 5 coin/kỳ (seed 42, 20 lặp).
   U_eval CỐ ĐỊNH (x=0.02, y=1.5) cho MỌI model — tách label train khỏi thước đo.
**Ngoài:** KHÔNG WF full 17 fold (chỉ khi PASS mới đáng tốn); KHÔNG đổi Java/sim; KHÔNG đụng gate
(coverage 2021-2022 là task 156, CCD khác đang làm); KHÔNG kết luận bỏ/giữ DCA (đó là pipeline
dca_ablation/edge_dca_hard — cần diff Java, chờ master).

## Pre-register (ghi TRƯỚC khi nhìn số)
Label mới **ĐÁNG ĐI TIẾP** (mở WF full + wfo_dataset v7) nếu trên TEST, tồn tại ≥1 biến thể y sao cho
model reg so với binary baseline (cùng kernel, cùng data):
1. mean U_eval top-5 **cao hơn** binary ≥ +0.10đ% tuyệt đối (mỗi pick), VÀ
2. độ-âm trung bình tại mốc 4h của pick FAIL **nông hơn** binary ≥ 10% tương đối, VÀ
3. precision(maxFav≥3%) không tụt quá 5đ% so binary, VÀ
4. cả hai model >> random (edge precision ≥ +10đ% như ngưỡng 153).
Nếu reg ≈ binary mọi mặt → ranking vốn đã tự tránh kèo âm sâu → label mới không thêm giá trị, giữ binary.
Nếu reg tệ hơn rõ → regression trên utility nhiễu hơn classification → ghi nhận, thử meta-labeling sau.

## HÀNG RÀO
- Đọc KAGGLE_RULES trước khi push (đã đọc); kiểm slot ≤5; log/output về D:\claudedata\t157\.
- Kernel enable_internet=false (chỉ đọc dataset), is_private=true, CPU.
- KHÔNG train lại label 6% cũ, không đụng predict_wf/wfo_dataset đang dùng.

## Job đang chạy (bàn giao)
- Kernel: `chuyendinh/dca-hard-label-157` (script `ml/funding_selector/kaggle_dca_hard/train.py`).
- Check: `kaggle kernels status chuyendinh/dca-hard-label-157`; output JSON `task157_result.json` +
  log tải về `D:\claudedata\t157\out\`.
- Bước còn lại nếu CCD này chết: chờ COMPLETE → tải output → điền bảng vào docs/reports/157.md →
  chấm verdict THEO PRE-REGISTER ở trên (không hậu chỉnh) → status REVIEW.

## Acceptance criteria
- [ ] Bảng TEST: 4 model × {precision top-5, U_eval, mean-loss-fail-4h} + random baseline.
- [ ] Phân rã theo quý trên TEST (ổn định regime).
- [ ] Verdict pre-register chấm bằng code trong kernel (in thẳng ra log/JSON).
- [ ] Đề xuất bước tiếp (WF full v7 / giữ binary / thử meta-label) dựa đúng verdict.

---
## (Code điền) Kết quả
Kernel v1 COMPLETE (~11 phút). **Verdict pre-register: FAIL cả 3 biến thể y** — c1 (utility hơn binary)
+ c2 (fail nông hơn ≥10%) PASS cả 3, nhưng c3 FAIL cả 3 (precision 78.3% → 59.2/42.7/32.0%); y≥1.5 thua
random về precision. `DANG_DI_TIEP=false` → KHÔNG mở WF full. Số đầy đủ: `docs/reports/157.md`.

## (Code điền) Phát hiện ngoài scope
**Binary maxFav3 (label v6 hiện tại) có utility ÂM (−1.30%/pick) và THUA RANDOM (−1.22%) dưới kế toán
DCA-cứng (x=2%, y=1.5), âm cả 5 quý TEST** — fail của nó âm TB −8.83% tại mốc 4h, sâu 3.6× random.
Điểm gãy: hòa vốn cần lãi thực/kèo thắng ≥3.67% (y=1.5) hoặc hệ-số-phạt-thật y ≤0.82 (x=2%).
→ "y thật" đo bằng task 154 Phần B (recovery path 1m) là số QUYẾT ĐỊNH cho bỏ/giữ DCA.

## (Code điền) Quyết định phát sinh
- x=0.02 cố định, quét y (ranking nhạy tỉ lệ x/y); U_eval cố định (0.02, 1.5) chấm chung mọi model.
- Đề xuất bước tiếp: 2-model meta (P(hit) + E[loss|fail]) — 1 kernel ~11 phút — chờ Uni duyệt.
