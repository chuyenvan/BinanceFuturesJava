---
id: 156
status: NEEDS_HUMAN
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
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
