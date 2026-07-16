---
id: 152
status: NEEDS_HUMAN
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/152.md
require_review: true
---

# TASK-152 [TEAM FAIL] — Tối ưu PHẦN 3: xử lý lệnh thua (DCA/SL) — MỎ CHƯA KHAI THÁC

## Mục tiêu team (1 câu)
Khi lệnh đi sai, cứu (DCA) hay cắt (SL) sao cho tối ưu tổng danh mục + thanh khoản ≤1 năm. Đây là phần
CHƯA TỪNG tối ưu riêng (mới thử SL/time-stop thô cắt-ngang → net âm). Tối ưu ĐÚNG = theo tier + ATR + thesis.

## Bộ chỉ tiêu (WFO, pre-register)
- PRIMARY: **max-holding ≤ 1 năm** (thanh khoản) + **maxDD mỗi cụm** giảm + **tỉ lệ-cứu** (lỗ→hồi) cao.
- Vốn kẹt trung bình giảm.
- CAGR tổng KHÔNG giảm quá 15% so baseline (đánh đổi chấp nhận được cho thanh khoản/an toàn).

## Baseline CỐ ĐỊNH 2 phần kia (KHÔNG đụng)
- Phần 1 (entry): `wfo_dataset_v4` (ret2). Phần 2 (success): `TS_GIVEBACK_RATIO=1.0`.

## Scope
**Trong scope (đo từ rẻ→mạnh):**
1. **Đo hiện trạng fail:** phân bố holding-time, độ sâu DCA mỗi cụm, cụm nào kẹt >90/180/270 ngày, cụm nào
   không bao giờ hồi (candidate delist). Đây là baseline để biết mỏ ở đâu.
2. **Thang DCA theo ATR spacing** (thay % cứng): khoảng cách nhồi DCA theo biến động coin, không cố định.
3. **Tier-based DCA/SL:** nếu có sẵn tier/rank coin (CoinRank static) → Tier-1 gồng sâu, Tier-2/3 dừng DCA
   sớm / SL. Nếu KHÔNG có tier mapping → ghi NEEDS_HUMAN, KHÔNG tự chế tier bừa.
4. **Thesis-invalidation stop:** thoát khi cấu trúc lý-do-vào gãy (không theo % cứng — % cứng đã net âm).
   Cần định nghĩa "thesis gãy" đo được → đề xuất trước, chờ Desktop nếu cần code lớn.
5. **Liên kết entry-size ↔ DCA-room** (thăm dò): đề xuất, phối hợp team Entry sau (Desktop điều phối).

**Ngoài scope:** KHÔNG đổi entry/giveback. KHÔNG dùng lại SL/time-stop THÔ cắt-ngang (đã loại). Code >50
dòng → đề xuất, chờ Desktop.

## HÀNG RÀO
- **CÁCH LY THU MUC:** worker chay o `/home/ubuntu/team_fail/simulator/` riêng (storage+config riêng),
  symlink jar chung read-only. KHÔNG đụng team khác, không ghi de jar chung.
- pgrep rỗng trước jar. setsid nohup. Data gap 2022 (gate/pred thiếu) đã biết — ghi rõ, không vá.
- Mỗi biến thể full-history + ladder_analyze + đo holding-distribution.

## Acceptance criteria
- [ ] Report holding/DCA-depth distribution hiện trạng (biết mỏ ở đâu).
- [ ] ≥1 kỹ thuật (ATR-DCA hoặc tier) chạy được → so baseline: max-holding, maxDD-cụm, tỉ lệ-cứu, CAGR.
- [ ] Verdict pre-register + đề xuất kỹ thuật cần code (nếu có), không tự implement lớn.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
