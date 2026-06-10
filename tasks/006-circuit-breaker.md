# TASK-006: Chạy circuit breaker 4 mode trên FULL — DCA có phải thủ phạm ruin không

- **status:** todo
- **Milestone:** ROADMAP bước 3 (ruin). Vấn đề TRỌNG TÂM (FINDINGS §1/§5: entry có edge nhưng DCA-không-giới-hạn phá hết qua chu kỳ).
- **Thực thi bởi:** Claude Code (**Java**). Tool ĐÃ CÓ: `ai_ml/validation/ablation/market/RunBreakerBacktest.java`. Chạy FULL 2021→2026 (đọc cluster 242). ~4× thời lượng FULL.
- **Quyết định nền:** ADR-0006 (golden/đo) · FINDINGS §5 (3 nguồn đuôi) · §8 (câu hỏi breaker).

## Mục tiêu (1 câu)
Chạy 4 mode OFF/MARGIN/DCA/BOTH → trả lời: breaker có **lật PnL 5 năm âm→dương** + giảm maxDD không, và **MARGIN hay DCA** gánh chính.

## Cơ chế breaker (đã code)
- `BREAKER_MARGIN_HALT` (FINDINGS: 0.70) — chặn MỞ MỚI khi margin/vốn ≥ ngưỡng (nguồn 1: mật độ 325 cụm).
- `BREAKER_CLUSTER_DD_MAX` (FINDINGS: −0.30) — ngừng NHỒI cụm khi tụt ≥ ngưỡng (nguồn 2: DCA khuếch đại).
- KHÔNG force-close (giữ long-only). Phanh chỉ DỪNG MỞ / DỪNG NHỒI.

## Luồng (tuần tự, tự cập nhật trạng thái; fail thì retry đúng bước)
- [ ] **B1 — Dọn + sync:** dọn job java cũ của mình (CLAUDE.md), `git pull`.
- [ ] **B2 — Commit sạch:** `git add -A && commit` (docs/tasks đang uncommitted). `git status` sạch.
- [ ] **B3 — Chạy `RunBreakerBacktest`** (4 mode, 1 lần). Pre-flight PHẢI pass (lookahead_block + slippage_apply + fee>0); nếu tool tự DỪNG vì cấu hình ảo → sửa rồi chạy lại. Dọn job trước khi chạy.
- [ ] **B4 — Ghi bảng vào (Code điền):** mỗi mode: totalPnl, PnL/năm (2021–2026), maxDD cũ + THẬT (+ /năm), halt count, dcaCap count, maxMarginRatio. + xác nhận **gate liêm chính**: totalPnl mode OFF khớp lần chạy nền trước (field đo mới không được đổi PnL).

## Câu hỏi quyết định (đọc bảng)
1. **OFF ra âm hay dương?** ⚠️ Data đang THIẾU coin chết (backfill hoãn, ADR-0007) + funding fee TẮT → PnL tuyệt đối **lạc quan**. Nếu OFF đã dương, rất có thể do survivorship, KHÔNG phải hệ tốt. Chỉ đọc **tương đối giữa các mode**.
2. **MARGIN/DCA/BOTH có lật PnL hay chỉ giảm maxDD?** MARGIN vs DCA — cơ chế nào gánh chính?
3. Kết luận theo FINDINGS §8:
   - Lật âm→dương → **DCA-không-giới-hạn đúng là thủ phạm, breaker sửa được** (bước ngoặt).
   - Giảm maxDD mà PnL ~giữ → đáng áp (an toàn hơn).
   - Giảm maxDD mà PnL xấu đi → **vấn đề sâu hơn DCA**, phải xem lại chiến lược (không cứu bằng phanh).

## Acceptance criteria
- [ ] 4 mode chạy cùng commit sạch (dirty=false), cùng data/tham số, chỉ khác `BREAKER_MODE`.
- [ ] Bảng đầy đủ PnL/năm + maxDD (cũ+thật) + counts; gate liêm chính OFF khớp.
- [ ] Kết luận rõ vào 1 trong 3 nhánh câu hỏi 3, có ghi lưu ý survivorship/funding-fee.
- [ ] Java, SLF4J, KHÔNG System.out.

---
## (Code điền) Kết quả

## (Code điền) Phát hiện ngoài scope

## (Code điền) Quyết định phát sinh
