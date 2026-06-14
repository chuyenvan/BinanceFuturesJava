# TASK-020: Audit luồng PRODUCTION (2 process) — rà lỗi logic/data ẩn

- **status:** REVIEW (audit DONE — `docs/PRODUCTION_AUDIT.md`; chờ Desktop/user mở task sửa các finding Cao). Giao CCD rảnh — **ưu tiên người CHƯA viết code live này** (góc nhìn mới rà khách quan hơn; tránh CCD#1 đang ngập 016/019).
- **owner:** CCD-audit · **updated:** 2026-06-14
- **Tính chất:** RÀ + LIỆT KÊ, **KHÔNG sửa code**. Mỗi phát hiện nặng → mở task sửa riêng sau (user/Desktop quyết).

## ⚠️ AN TOÀN
- CHỈ ĐỌC code + đọc Aerospike (242 qua 226) để verify data tươi. **KHÔNG sửa, KHÔNG restart, KHÔNG đụng `BinanceOrderTradingManager`/`BinanceDataIngestor` đang chạy.** SLF4J nếu có tool đọc.

## Bối cảnh — vì sao audit
4 lượt gần đây liên tục lộ bug live "im lặng": FundingFeeManager cache không refresh (isProductionMode dead) · FundingIngestor flush sai nhịp · TickerFuturesHelper -1130 (limit invalid) · startHistoryCrawl thừa · ban/rate guard thiếu. Toàn loại chạy-không-crash-nhưng-sai. → rà hệ thống tìm các pattern tương tự CÒN LẠI.

## Phạm vi: 2 process live
- **P1 `BinanceDataIngestor`** (ingest → Aerospike 242): ticker/kline, funding, OI, price_realtime, repair.
- **P2 `BinanceOrderTradingManager`** (trade live): entry (model pred + market level), DCA, exit/trailing, lock, budget, reporter.

## Phương pháp
Với MỖI process: liệt kê mọi thread/loop từ `main` (start gì) → soi từng cái theo CHECKLIST. Bằng chứng cụ thể (file:dòng + log/đọc Aerospike), không phán chung chung.

## CHECKLIST (pattern bug đã thấy → tìm cái tương tự)
1. **Nhịp loop:** sleep đúng đơn vị? tần suất thực khớp ý định? (đối chiếu log/ts Aerospike) — như FundingIngestor flush.
2. **Data tươi vs cache tĩnh:** manager/cache nào load 1 lần lúc start mà KHÔNG refresh trong live? (như FundingFeeManager). Soi mọi cache: model pred (time2SymbolPred precompute?), symbol mapper, funding, price, lifecycle.
3. **Flag dead:** biến cờ set mà không ai đọc (như isProductionMode)?
4. **Exception nuốt:** loop có try-catch nuốt → chết im / hụt nhịp mà không ai biết?
5. **Ghi/đọc đúng nơi:** live ghi 242? đọc 242 (private, qua 226)? có chỗ nào lỡ đọc 226 (backtest) trong live?
6. **Ban/rate guard:** mọi REST call qua `BinanceRestGuard` + throttle? còn caller nào gọi thẳng `HttpRequest`?
7. **Param hợp lệ:** limit/startTime/range tính có ra giá trị invalid (0/âm/>max) ở edge? (như -1130).
8. **DIED_SYMBOLS:** dùng nhất quán ingest + trade? skip đúng coin? (đối chiếu config 129 prod).
9. **Edge symbol:** coin mới list / delist / data thiếu → xử an toàn (không crash, không lệnh sai, không 0 giả)?
10. **Sim/live parity:** trade live đi đúng code path như sim (một-bộ-não)? có nhánh chỉ-live khác sim không?
11. **Train/serve parity:** feature/pred lúc trade live = đúng công thức + data như lúc train? (nối FundingFeeManager — funding live tươi chưa).
12. **Quyết định trên data cũ/trễ:** entry/exit dùng price_realtime/funding/pred — các nguồn này có tươi tại thời điểm quyết không (hay stale như funding)?

## Trọng tâm P2 (trade) — dễ sai mà hậu quả nặng
- Model pred nạp thế nào ở live: `time2SymbolPred` precompute lúc start (→ STALE như funding?) hay tính realtime? Nếu precompute → coin/thời điểm mới không có pred.
- price_realtime đọc 242 có tươi? funding qua FundingFeeManager (đang lỗi 019).
- DCA/trailing/exit: ngưỡng, lock symbol, budget — logic biên (chia 0, symbol mất data giữa chừng).

## Output
- 1 file **`docs/PRODUCTION_AUDIT.md`**: bảng `[Vị trí (file:dòng) | Phát hiện | Mức độ (Cao/TB/Thấp) | Bằng chứng | Đề xuất]`. Nhóm theo P1/P2 + cross-cutting.
- KHÔNG sửa. Phát hiện Cao → Desktop/user mở task sửa.

## Acceptance
- [x] Liệt kê đủ thread/loop của P1 + P2 (từ main). → `docs/PRODUCTION_AUDIT.md` §1
- [x] Mỗi mục checklist soi qua, có kết luận (sạch / nghi / lỗi) + bằng chứng. → §2-4 + §6 (đã-tốt)
- [x] File `docs/PRODUCTION_AUDIT.md` với bảng phát hiện phân mức. → 12 Cao + nhiều TB/Thấp
- [x] KHÔNG sửa code/không đụng live. → chỉ đọc source (+ verify) ; KHÔNG chạy job/đụng 242.

## (Code điền) — KQ trong `docs/PRODUCTION_AUDIT.md`
- **P1 thread/loop + phát hiện:** 9 loop từ main (funding poll/flush, price 3s, kline phút, repair, OI history/forward); watchdog DEAD. Cao: funding REST bỏ guard (FundingIngestor:49) · watchdog dead+counter hỏng (Ingestor:22) · HttpRequest nuốt câm · race writeMinuteBatch · ForkJoinPool per-batch.
- **P2 thread/loop + phát hiện:** T1 entry, T2 queue, T3 manager (trailing/markPrice), T4 restart 4h, T5 budget 1h, T6 funding refresh 30'. Cao: model Return15M nhầm feature V3/V4 (OnnxInferenceManager:50-55) · entry dùng nến đóng không price_realtime (DetectEntry:494) · aiBrain fail → ngừng vào lệnh câm · updatePositionInfo clear-then-fill + lock không nhả.
- **Cross-cutting (parity, guard, cache):** gate AI lệch pred==null sim≠live (một-bộ-não) · DIED_SYMBOLS repo 30 vs 129 (008) · getReadClient có thể lỡ đọc 226 nếu IS_KAGGLE_MODE bật + 2 hàm hardcode 226 · vài TickerFuturesHelper REST bỏ guard.
- **Đã-tốt (loại nghi):** pred KHÔNG precompute stale (infer realtime) · ghi/đọc 242 nhất quán · funding refresh (019) đã vá · DIED_SYMBOLS dùng nhất quán ingest+trade.
- **Trạng thái:** audit DONE; finding Cao → Desktop/user mở task sửa riêng (KHÔNG sửa từ task này).
