---
id: 143
status: DONE
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 1
report: docs/reports/143.md
require_review: true
---

# TASK-143: Test đuôi BEAR 2022 — rủi ro DCA gồng coin không hồi

## Mục tiêu (1 câu)
Đo rủi ro đuôi thật của DCA-không-SL trong bear kéo dài: "không lỗ quý nào" của hệ một phần nhờ coin
luôn hồi trong 2021–2026 (chủ yếu uptrend) — bear 2022 + coin delist (LUNA/FTT) là chỗ chưa test.

## Scope
**Trong scope:**
- Sim RIÊNG giai đoạn bear: chạy window 2022 (nếu pred/gate thiếu 2022 thì ghi rõ giới hạn — data gap
  đã biết, KHÔNG tự vá). Nếu không có pred 2022, dùng giai đoạn bear khác có data (2025 các quý sập).
- Đo: maxDD sâu nhất, số cụm DCA kẹt > 90 ngày, có margin-call/burn không, thời gian phục hồi.
- **Thử tier-DCA thô:** phân biệt coin theo thanh khong/tier (dùng volume hoặc rank sẵn có nếu có), chỉ
  gồng sâu Tier-1, Tier-2/3 dừng DCA sớm. Nếu KHÔNG có tier mapping sẵn → ghi "cần tier mapping" là
  NEEDS_HUMAN, KHÔNG tự chế mapping bừa.

**Ngoài scope:** KHÔNG đổi kiến trúc; chỉ đo rủi ro + thử tier-stop nếu có sẵn dữ liệu tier.

## Pre-register
- Rủi ro "chấp nhận được" nếu maxDD bear ≤ 50% VÀ không burn account VÀ phục hồi < 1 năm.

## HÀNG RÀO
- 242 chỉ đọc. pgrep rỗng trước jar. setsid nohup. Data gap 2022 đã biết — ghi rõ, không vá.

## Acceptance criteria
- [ ] Report 143.md: maxDD bear, #cụm kẹt >90d, có/không burn, tier-DCA nếu khả thi.
- [ ] Nếu thiếu data/tier → ghi rõ NEEDS_HUMAN, không bịa.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
