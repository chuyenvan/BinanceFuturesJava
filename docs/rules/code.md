# rules/code — Quy ước & luật code (nạp khi sửa code Java/HPO)

> Đọc cùng [CORE](../CORE.md). Phần catch-câm + SLF4J + bump CONFIG_VERSION đã ở CORE — không lặp ở đây.

## Quy ước
- **Java 11** (pom.xml pin `source/target` 11). `CONVENTIONS.md` ghi Java 21 nhưng build thật là 11 → xác nhận user TRƯỚC khi dùng cú pháp Java 21 (và bump pom nếu thật sự muốn).
- Method mới phải có **Javadoc** đầy đủ (mô tả, params, return).
- Sửa NHỎ, mỗi thay đổi một mục đích. KHÔNG refactor hàng loạt khi chưa hỏi user (codebase ~250 class, nhiều ràng buộc ngầm).

## Luật quyết định / HPO (quên = run vô nghĩa, sai âm thầm)
- **MỘT BỘ NÃO sim/product:** mọi quyết định vào/ra lệnh nằm trong hàm lõi THUẦN dùng chung. Mẫu đúng: `DcaUtils.shouldDca`, `MarketBigChangeDetector.evaluateCircuitBreakerCore`. Thấy `xxx` vs `xxxProd`/`xxxProduction` lệch về LUẬT = BUG cần gom, không phải tính năng. Còn lệch: `createOrderBUY` (sim) vs `createOrderBuyRequest` (product) — ROADMAP bước 5.
- **`taskId` HPO phải băm ĐỦ mọi gene** (`buildTaskId`). Thêm gene mà quên → cá thể khác trùng key → HPO vô nghĩa. (Đã dính 4 gene DCA.)
- **KHÔNG random-split chuỗi thời gian:** cắt theo MỐC THỜI GIAN, không `train_test_split(shuffle/stratify)`. Scaler chỉ `fit` trên TRAIN (fit toàn bộ rồi chia = leak phân phối test).
- **Tiền/giá đang `Float`** (rủi ro sai số tích lũy). Refactor sang `double`/`BigDecimal` phải đồng bộ sim+product + bump `CONFIG_VERSION`.
- **KHÔNG đổi `finalFitness` (`HPOFitnessCalculatorV3`) khi HPO đang chạy dở.** `profitFactor`/`worstSingleLoss`/`payoffRatio` là guardrail báo cáo, cố ý KHÔNG nằm trong fitness.
- **Worker HPO tuần tự 1 task/JVM** nên ghi `static Configs` an toàn. ĐỪNG song song nhiều trial trong cùng JVM với static Configs (giẫm tham số chéo).

## Runtime config (đọc từ CWD, không phải classpath)
- `config.properties` (`tradecore/Configs.java` load: hosts/ports, capital, symbol lists, paths `../storage/`; thiếu → `System.exit(0)`), `redis.config` (`redis/RedisConst.java`), `config/PrivateConfig.java` (key live — xem [security](security.md)).
- `tradecore/Configs.java` = bề mặt tinh chỉnh trung tâm (leverage/fee/budget/breaker/trailing/AI-filter/DCA — `static`, nhiều cái HPO set). Đọc comment từng section trước khi đổi magic number.
