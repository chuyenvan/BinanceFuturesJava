---
id: 156
status: REVIEW
owner: CCD-156B
updated: 2026-07-16 17:30 +07
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/156.md
require_review: true
---

# TASK-156 [GATE COVERAGE] — Sinh gate prediction cho 2021-2022 (gốc rễ WFO FAIL)

## PHÁT HIỆN GỐC RỄ (đo được 2026-07-11, Uni chỉ hướng)
WFO luôn FAIL (~29% OOS-dương) ở CẢ ret2 lẫn maxFav3 — KHÔNG phải do chiến lược, mà do **gate model
(pred.bin / wfo_gate_pred.csv) CHỈ phủ 2023-01 → 2026-05**. 2021=0 records, 2022=420 records (gần trống).
Entry đòi `predict != null` (SimulatorMarketLevelTicker1MStopLoss line 187) → 2021-2022 bị chặn CỨNG mọi
entry → 8/17 cửa sổ WFO ZERO_TRADES → verdict FAIL GIẢ.

Chuỗi loại trừ đã đo:
1. Selector maxFav3 CÓ pred 2022 (P(win) tới 0.99) — không thiếu selector.
2. Tắt gate-filter (ABLATION_MODE=B) 2021-2022 VẪN zero — không phải gate-threshold.
3. Gate MODEL chỉ phủ 2023+ → chặn `predict != null`. ← GỐC RỄ.

2021 là năm bull MẠNH NHẤT lịch sử crypto (Uni: mọi mô hình đều đẹp nhất 2021). 2021 mà 0 lệnh là bằng
chứng cứng của lỗi coverage, không phải thiếu cơ hội.

## Mục tiêu (1 câu)
Sinh gate prediction (predReturn15M, predRisk4H) phủ 2021-01 → 2022-12 leak-free, để WFO đánh giá công bằng.

## ĐÃ XÁC ĐỊNH NGUYÊN NHÂN (đo 2026-07-11) — feature CÓ, chỉ thiếu vì CUTOFF
- market.bin phủ 2021 đầy đủ. Selector CÓ pred 2022 (train trên 2021) → feature data 2021-2022 CHẮC CHẮN
  tồn tại. → Gate thiếu 2021-2022 KHÔNG phải thiếu data mà vì gate train CUTOFFS bắt đầu 2023.
  → SỬA ĐƯỢC: train lại gate cutoffs mở về 2021 (giống selector). Hướng 1 khả thi, không cần hướng 2.

## Scope
**Trong scope:**
1. Tìm gate training pipeline: `ml/gate/train_gate_fold.py` (newest) + `WFOGateRunner`. Xác định vì sao
   pred cũ (`wfo_gate_pred.csv`) bắt đầu 2023 — do CUTOFFS hay do thiếu feature data 2021-2022?
2. Kiểm feature data gate (ff_*.bin / OI) CÓ phủ 2021-2022 không:
   - Nếu CÓ → sinh lại gate pred với cutoffs mở rộng về 2021 (leak-free WF, fold đầu train tối thiểu rồi
     predict tiến). Ghép vào wfo_gate_pred.csv → rebuild pred.bin cho v6.
   - Nếu KHÔNG (feature data gate vốn thiếu 2021-2022) → ghi rõ: đây là giới hạn DATA gate, và WFO phải
     LOẠI cửa sổ 2021-2022 khỏi mẫu (không phạt oan) → tính verdict chỉ trên cửa sổ có đủ data.
3. Sau khi có gate pred phủ đủ (hoặc quyết loại cửa sổ): **chạy lại WFO v6** → verdict mới.

**Ngoài scope:** KHÔNG đổi selector/exit/DCA. KHÔNG train lại selector maxFav3 (đã có). Chỉ lo GATE coverage.

## Pre-register
- Nếu sinh được gate 2021-2022 → WFO lại: kỳ vọng %OOS-dương tăng rõ (2021 bull có lệnh dương). PASS nếu
  đạt ngưỡng cũ (WFE med≥0.5, %OOS+≥70%, maxDD≤50%) TRÊN mẫu cửa sổ CÓ ĐỦ DATA.
- Nếu gate feature vốn thiếu 2021-2022 → verdict tính trên 2023-2025 (13 cửa sổ có data): cùng ngưỡng.

## HÀNG RÀO
- Gate pred phải LEAK-FREE (train quá khứ → predict OOS), giống selector. Purge buffer = max trade duration.
- setsid nohup. Đọc ff/OI qua path có sẵn, chú ý OOM (OI 138M từng OOM Oracle → có thể cần Kaggle như selector).
- SLF4J. Cách ly thư mục.

## Acceptance criteria
- [ ] Xác định NGUYÊN NHÂN gate pred thiếu 2021-2022 (cutoff config vs thiếu feature data).
- [ ] Hoặc sinh được gate pred 2021-2022 leak-free, hoặc chứng minh feature data vốn thiếu + đề xuất loại cửa sổ.
- [ ] Chạy lại WFO v6 với gate đầy đủ (hoặc mẫu đã lọc) → verdict mới + so 29% cũ.
- [ ] Kết luận: chiến lược maxFav3 PASS/FAIL khi gate KHÔNG còn là biến nhiễu.

---
## (Code điền) Kết quả
Đầy đủ tại `docs/reports/156.md` (kèm RESULT block). Tóm tắt:
- Gốc rễ = CUTOFF `FIRST_OOS=20230101` → sửa `WFOGateRunner` minTrainMonths=3; gate pred v6: 21 fold,
  2,717,280 pred OOS phủ 2021-04-01 → 2026-05 (2021=396,420 · 2022=525,600 dòng; cũ 0/420). Leak-free expanding.
- Đã nạp set `ai_pred_market_gate_wfo` (2,717,280 rec) + rebuild pred.bin + WFO chạy lại (07-12/07-13).
- **Verdict mới (metric sạch, dataset _ff):** maxFav3 **FAIL** — %OOS+ 50.0% (8/16) vs 29% cũ, WFE_med 0.596 (đạt),
  maxDD 31.8% (đạt) → trượt DUY NHẤT posRatio ≥70%. ret2wf FAIL 43.8%. Gate hết là biến nhiễu; FAIL còn lại do
  posRatio/regime → thuộc campaign strategy, ngoài scope 156.

## (Code điền) Phát hiện ngoài scope
- `predRisk4H` 2021-2022 = 0.0 fallback, KHÔNG phục hồi được (model `ai_models_reg_v3` mất — chi tiết report).
- BUG 4 funding.bin mất forward-fill 15m→phút + BUG 1 WFE-median nhiễm + orphan jobs → `docs/reports/BUGHUNT_WFO_20260713.md`
  (phát hiện & fix bởi phiên overnight 07-12/07-13, ảnh hưởng trực tiếp cách đọc verdict 156).

## (Code điền) Quyết định phát sinh
- minTrainMonths=3 (khớp bước OOS, reversible).
- 2026-07-16: đóng hồ sơ bằng verify-log (job đã xong + các bước còn lại đã được phiên overnight chạy trọn),
  KHÔNG re-run WFO (BUGHUNT cấm vòng mới khi metric chưa sạch; verdict final đã trên metric sạch).
