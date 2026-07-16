---
id: 151
status: REVIEW
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 2
report: docs/reports/151.md
require_review: true
---

# TASK-151 [TEAM SUCCESS] — Tối ưu PHẦN 2: nuôi lãi (xử lý lệnh thắng)

## Mục tiêu team (1 câu)
Khi lệnh đi đúng, vắt tối đa lợi nhuận mà không cắt non — nâng PnL trung bình/lệnh thắng, giữ ổn định.

## Bộ chỉ tiêu (WFO, pre-register)
- PRIMARY: **PnL trung bình / lệnh thắng** + **% của đỉnh giữ được** (không cắt non).
- Không làm tăng maxDD danh mục quá baseline.
- CAGR full-history ≥ baseline giveback=1.0 hiện tại.

## Baseline CỐ ĐỊNH 2 phần kia (KHÔNG đụng)
- Phần 1 (entry): `wfo_dataset_v4` (ret2) — KHÔNG dùng v5 (đó là biến của team Entry). Cố định để cô lập.
- Phần 3 (fail): DCA mặc định, stops off.

## Scope
**Trong scope:**
1. Re-WFO `TS_GIVEBACK_RATIO` trên cấu hình hiện tại: quét {0.7, 0.85, 1.0} — xác nhận 1.0 vẫn tốt nhất
   hay horizon/label mới đổi tối ưu. (Đã đo sơ 12h; làm lại đầy đủ, ghi bậc thang.)
2. **Scale-out từng phần:** thử chốt 1 phần ở mốc lãi (vd +X%) + nuôi phần còn lại bằng trailing lỏng.
   Cần thêm cơ chế partial-close vào simulator — nếu chưa có → BÁO Desktop (cần code, không tự thêm lớn).
3. **Pyramid (anti-martingale) thăm dò:** đánh giá khả thi nhồi thêm vào lệnh ĐANG THẮNG (khác DCA vào lỗ).
   Nếu cần code lớn → chỉ ĐÁNH GIÁ + đề xuất, không tự implement.

**Ngoài scope:** KHÔNG đổi entry/DCA/SL. Cơ chế mới cần code >50 dòng → đề xuất, chờ Desktop.

## HÀNG RÀO
- **CÁCH LY THU MUC:** worker chay o `/home/ubuntu/team_success/simulator/` riêng (storage+config riêng),
  symlink jar chung read-only. KHÔNG đụng team khác, không ghi de jar chung.
- pgrep rỗng trước jar. setsid nohup. Trả config về bak2. Mỗi biến thể chạy full-history + ladder_analyze.

## Acceptance criteria
- [ ] Bảng giveback {0.7,0.85,1.0}: PnL/lệnh-thắng, %đỉnh-giữ, maxDD, CAGR, bậc thang.
- [ ] Kết luận giveback tối ưu (xác nhận hoặc bác 1.0).
- [ ] Scale-out: nếu chạy được → so với trailing thuần; nếu cần code → đề xuất rõ.
- [ ] Verdict pre-register.

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
