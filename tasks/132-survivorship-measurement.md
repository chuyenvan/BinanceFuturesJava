# TASK-132: Đo survivorship bias — enumerate universe lịch sử thật + ước lượng ảnh hưởng — CCD opus

- **status:** doing (giao 2026-07-05 tối)
- **Bối cảnh:** universe backtest hiện dùng coin CÒN SỐNG hôm nay → sống sót bias (coin delisted bị loại khỏi
  lịch sử → backtest thấy "toàn winner"). docs/decisions/0007-survivorship-*.md đã có; SurvivorshipBac0.java +
  SurvivorshipFeatureCheck.java đã tồn tại. Mục "hoàn thiện đo lường trung thực" #2.

## ⛔ HÀNG RÀO
1. **PHA 1 = ĐO, KHÔNG BACKFILL.** Trả lời bằng số:
   - SurvivorshipBac0/SurvivorshipFeatureCheck hiện làm gì (đọc code + chạy nếu an toàn) — nó đã enumerate được
     universe lịch sử thật (gồm coin delisted) chưa?
   - Đếm: bao nhiêu symbol từng tồn tại trên Binance futures trong 2021–2026 vs bao nhiêu symbol CÓ trong dataset
     WFO hiện tại (market.bin). Chênh lệch = số coin delisted bị thiếu.
   - Ước lượng ảnh hưởng: các coin delisted thường là coin giảm mạnh/bị bỏ → long-only DCA vào chúng sẽ LỖ NẶNG
     (martingale không stop-loss). Thiếu chúng = backtest phồng. Ghi mức độ (định tính + con số symbol thiếu).
2. **PHA 2 (backfill dữ liệu delisted) chỉ làm nếu Uni duyệt** — nặng, đụng data pipeline, để NEEDS_HUMAN.
   PHA 1 chỉ cần cho Uni thấy "thiếu bao nhiêu coin, ảnh hưởng cỡ nào" để quyết có đáng backfill không.
3. Không đụng Oracle compute nặng. Đọc 226/Aerospike read-only để đếm symbol; crawl Binance API để lấy danh sách
   symbol lịch sử CHỈ nếu không geo-block (nếu block → ghi PENDING, dùng danh sách offline nếu có).
4. SLF4J only.

## Output: docs/reports/survivorship_audit.md (PHA 1) + marker /d/claudedata/CCD132_DONE. NEEDS_HUMAN cho PHA 2.
