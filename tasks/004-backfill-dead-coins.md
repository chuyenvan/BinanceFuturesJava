# TASK-004: Backfill coin chết vào dataset + backtest đối chứng survivorship

- **status:** todo
- **Milestone:** Đóng survivorship chain (002 → 001 → **004**). Nền quyết định: [ADR-0007](../docs/decisions/0007-survivorship-material.md).
- **Thực thi bởi:** Claude Code (ingest Aerospike + backtest — chạy trên 226/242).

## Mục tiêu (1 câu)
Đưa các coin chết (TASK-001) vào Aerospike ticker đúng format, rồi chạy backtest đối chứng (có/không) để định lượng survivorship làm lệch PnL/DD bao nhiêu — chốt có cần xem lại mọi kết luận backtest/HPO không.

## Scope
**Trong scope:**
- Tải klines monthly 1m của các coin thiếu (danh sách + chỉ số: `outputs/survivorship_missing_symbols.csv`).
- Convert sang format ticker float-packed của repo + ingest vào ticker set (`kline_1m_opt`), key theo phút, index `symbolId`.
- Cấp `symbolId` cho coin mới (qua `SimpleSymbolMapper.getId`, ghi `symbol_mapper`).
- Re-sync 226 (CopyTicker242To226) nếu ingest vào 242.
- Chạy backtest **A (dataset cũ)** vs **B (có coin chết)** cùng tham số; so PnL/maxDD(thật)/worstSingleLoss theo NĂM + tổng.

**Ngoài scope (KHÔNG động):**
- KHÔNG đổi engine logic / model / genome / `CONFIG_VERSION` (trừ khi có lý do riêng, hỏi trước).
- KHÔNG xoá/đè data của symbol ĐANG CÓ — chỉ THÊM coin thiếu.
- Loại `我踏马来了USDT`, `龙虾USDT` (rác), `LENDUSDT` (không có monthly klines).

## Bối cảnh cần biết
- ADR-0007: vì sao survivorship material (LUNA/FTT/… chết về 0, chiến lược DCA-nhồi-loser không SL).
- Coverage hiện tại để verify "chỉ thêm, không đè": chạy lại `AerospikeCoverageMap` so trước/sau.
- ⚠️ Ingest path repo: **<CẦN XÁC NHẬN: tool/hàm ghi ticker float-packed — `BinanceDataIngestor` chỉ stream live; cần xác định hàm ingest-từ-file/backfill hoặc `DataManagerAerospikeFloatSim.saveTicker*` + encoder proto>**. Đừng bịa — đọc code xác minh trước khi ghi.
- maxDD phải dùng nguồn THẬT per-tick (`trueUnrealizedMin`) — xem ADR-0001.
- Ingest = GHI Aerospike → cực cẩn trọng; cân nhắc ghi vào set TẠM trước, verify, rồi mới merge.

## Acceptance criteria (Code tự kiểm trước khi báo done)
- [ ] CHỈ thêm coin thiếu; coverage map của các symbol cũ KHÔNG đổi (verify trước/sau).
- [ ] Coin chết hiện diện trong ticker (AerospikeCoverageMap nhìn thấy + đúng khoảng tháng).
- [ ] Backtest A vs B: bảng ΔPnL / ΔmaxDD(thật) / worstSingleLoss theo năm + tổng.
- [ ] Kết luận bằng SỐ: survivorship làm PnL lạc quan / DD nông đi bao nhiêu %.
- [ ] Code Java: SLF4J, KHÔNG System.out/printStackTrace; backtest đi qua `BacktestIntegrityGuard` (luật 1–3 CLAUDE.md).
- [ ] Cấu trúc/đường dẫn khác giả định → BÁO LẠI, KHÔNG bịa.

---
## (Code điền) Kết quả

## (Code điền) Phát hiện ngoài scope

## (Code điền) Quyết định phát sinh
