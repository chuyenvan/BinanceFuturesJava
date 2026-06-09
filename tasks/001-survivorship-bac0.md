# TASK-001: Bậc-0 — ước lượng độ nặng survivorship bias

- **status:** done — survivorship ĐÁNG KỂ (tập thiếu chứa LUNA/FTT/RAY/SRM/WAVES… chết về ~0). Đề xuất mở task backfill + ADR.
- **Milestone:** Tiền đề dữ liệu — đo mức thiên lệch survivorship TRƯỚC khi tin kết quả backtest (cross-cutting, ảnh hưởng độ tin cậy của Bước 1–4 trong ROADMAP).
- **Thực thi bởi:** Claude Code (**Java**, chạy trên 226 — đọc coverage CSV cùng máy; chỉ tải Binance nếu tập thiếu đáng kể).

## Mục tiêu (1 câu)
Chốt bằng số: có coin USDT-perp nào TỪNG tồn tại mà dataset THIẾU HOÀN TOÀN không, và nếu có thì chúng sập cỡ nào — để quyết có đáng full backfill (TASK-003/004) hay không.

## Bối cảnh (đã biết từ Bước trước)
- **Universe data.vision** (USDT-perp, đã parse): **732** symbol. Endpoint S3 XML đúng:
  `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/futures/um/monthly/klines/`
- **Coverage thật** (TASK-002): `aerospike_coverage.csv` trên **226** (`/home/chuyennd/java/simulator/outputs/`), **750** symbol USDT-perp có data, cột `symbol,firstMonth,lastMonth,monthsCovered,gapMonths`.
- Tín hiệu sơ bộ: coverage (750) > universe (732) ⇒ tập thiếu hoàn toàn nhiều khả năng RẤT NHỎ.

## RÀNG BUỘC SYMBOL (lọc ở phía tiêu thụ — KHÔNG re-run 002)
Chỉ USDT perpetual. LOẠI khỏi cả universe lẫn coverage: nhóm chứa `USDC` (vd `USDCUSDT`, `1000BONKUSDCUSDT`), `BTCDOMUSDT` (dominance index), mọi symbol có `_` / COIN-M / USDC-margined.

## Các bước
1. Đọc `aerospike_coverage.csv` (226) → tập `coverage` (symbol có data), áp RÀNG BUỘC SYMBOL.
2. Universe data.vision USDT-perp (parse listing hoặc dùng kết quả đã có), áp RÀNG BUỘC SYMBOL.
3. **Tập thiếu hoàn toàn** = `universe − coverage`. In số lượng + danh sách đầy đủ.
4. **CỔNG QUYẾT:**
   - Tập thiếu rỗng hoặc nhỏ & không coin nào từng có thanh khoản đáng kể → KẾT LUẬN: survivorship-do-thiếu-symbol nhẹ, **KHÔNG cần full backfill**. Ghi kết luận + đánh `done`. Đóng chuỗi (bỏ 003/004).
   - Tập thiếu đáng kể → mới tải klines Binance từng symbol thiếu (monthly 1m, 404 bỏ qua), tính `firstOpen, maxClose, minClose, lastClose, drawdownToBottom=minClose/firstOpen−1, diedNearZero=(lastClose/maxClose)<0.1, avgQuoteVolume`; xuất `outputs/survivorship_missing_symbols.csv` + summary (số diedNearZero, drawdown TB, 10 coin sập nặng nhất). Khi đó 003/004 mới có nghĩa.

## Acceptance criteria
- [ ] Phép trừ tính trên tập đã lọc RÀNG BUỘC SYMBOL (universe + coverage).
- [ ] In rõ số lượng + danh sách tập thiếu hoàn toàn.
- [ ] Ghi rõ KẾT LUẬN ở Cổng quyết (cần backfill hay không) + lý do bằng số.
- [ ] Nếu chạy nhánh tải Binance: CSV đúng cột + summary đủ mục.
- [ ] Java, log SLF4J/Log4j2, KHÔNG System.out/printStackTrace.
- [ ] Cấu trúc khác giả định → BÁO LẠI, KHÔNG bịa.

---
## (Code điền) Kết quả

- Tool: `src/main/java/com/binance/chuyennd/ai_ml/validation/data/SurvivorshipBac0.java` (Java thuần java.net+zip, KHÔNG Aerospike/engine/backtest; SLF4J). Chạy trên **226**.
- Sau lọc (USDT-perp, bỏ `USDC`/`BTCDOMUSDT`/`_`): coverage = **711**, universe data.vision = **730**.
- **TẬP THIẾU HOÀN TOÀN = 39 symbol** (universe − coverage). 38/39 có klines (LENDUSDT không có monthly klines). 12 diedNearZero. drawdown TB = **−60.9%**.
- 10 coin thiếu sập nặng nhất: LUNAUSDT(−99.7%, avgQV 609k), ANCUSDT(−99.7%), DODOUSDT(−98.1%), RAYUSDT(−97.6%), FTTUSDT(−97.1%), AUDIOUSDT(−96.2%), DGBUSDT(−95.7%), GALUSDT(−94.8%), SRMUSDT(−89.7%), ANTUSDT(−88.5%).
- CSV: `226:/home/chuyennd/java/simulator/outputs/survivorship_missing_symbols.csv` (39 dòng + header). *(Trên 226, chưa kéo local.)*
- **CỔNG QUYẾT → survivorship ĐÁNG KỂ:** dataset THIẾU đúng các cú sập-về-0 lịch sử (LUNA, FTT, RAY, SRM, WAVES, DODO, AUDIO, ANC…). Với chiến lược long-only DCA-nhồi-loser, đây là rủi ro ĐUÔI nặng nhất — backtest hiện đang giấu nó ⇒ **NÊN backfill** trước khi tin kết quả backtest/HPO.

## (Code điền) Phát hiện ngoài scope

- **`avgQuoteVolume` (TB toàn đời) HẠ THẤP thanh khoản đỉnh** của coin sống-rồi-chết-lê-thê: FTT avgQV=8.9k, RAY=6.5k, SRM=29k… (đuôi gần-0 dài kéo trung bình xuống) ⇒ cổng `LIQUID_QV=50k` chỉ đếm "6 liquid" là **ĐÁNH GIÁ THẤP**. Thực chất FTT/RAY/SRM/DODO/AUDIO đều TỪNG rất thanh khoản rồi chết → tập "đáng kể" lớn hơn 6. Nếu cần chốt chặt: đo QV ĐỈNH (rolling max) hoặc QV ở thời kỳ sống, KHÔNG dùng mean toàn đời.
- **2 symbol "rác" lọt universe:** `我踏马来了USDT`, `龙虾USDT` (tên meme tiếng Trung, listing 2026 trên data.vision) — đuôi USDT nên qua lọc; nhiễu nhỏ, không phải coin nghiêm túc.
- `LENDUSDT` thiếu hoàn toàn nhưng KHÔNG có monthly klines (delist trước khi có monthly) → không đo được.
- coverage-only (có trong dataset, không trong universe-monthly) = 20 — symbol đổi tên/ngoài um-monthly; không ảnh hưởng kết luận.

## (Code điền) Quyết định phát sinh

- **Đề xuất ADR + task backfill:** survivorship material → backfill 38 coin chết (ưu tiên LUNA/FTT/RAY/SRM/WAVES/DODO/AUDIO/ANC) vào Aerospike ticker rồi chạy lại backtest đối chứng (có/không các coin này) để định lượng PnL/DD chênh. Đây là quyết định lớn (đổi nền dữ liệu) → cần ADR ghi WHY. **Chưa tự tạo** (chờ user duyệt hướng + đánh số task).
