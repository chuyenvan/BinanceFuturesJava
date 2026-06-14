# TASK-027: Sửa P2 entry correctness (audit Cao #6/#7/#8) [ƯU TIÊN CAO NHẤT]

- **status:** REVIEW — code DONE, BUILD SUCCESS (mvn -o compile); chờ user soát + gộp deploy. Nguồn: `docs/PRODUCTION_AUDIT.md` §3.
- **owner:** CCD-audit · **updated:** 2026-06-14

## ⚠️ AN TOÀN
- Live (242 / P2 trade). Test riêng, **KHÔNG tự deploy**; gộp vào đợt deploy có soát. SLF4J. KHÔNG sửa mù (xem #6 cần đối chiếu trước).

## #6 — Model Return15M V3/V4 (`OnnxInferenceManager.java:50-55`) — ĐÃ SOI: KHÔNG LỖI (chỉ dọn dead)
- Desktop soi `OnnxInferenceManager` + `DetectEntry`: `p15M.predict(featuresV3)` (33 feat) khớp `Model_Regressor_Return15M`. Nếu model là V4(30) thì scaler ONNX throw shape → catch → (0,0) → predReturn15M=0 MỌI entry → bot bất thường. **User xác nhận LIVE chạy bình thường → model cũ V3 khớp, KHÔNG trade rác.**
- **Việc (nhẹ, không gấp):** xóa `extractFeaturesV4Sideway` dead + sửa comment "V4 Sideway" (chính nó làm audit nghi oan). KHÔNG đụng logic, KHÔNG chặn deploy. (Model mới → viết inference mới sau.)

## #7 — Entry/quantity tính trên nến ĐÓNG, không dùng price_realtime tươi (`DetectEntry:494`)
- `priceEntry = ticker.priceClose` (nến 1m đóng, trễ ~1-2′). `getPriceRealtime`/`getPriceRealtimeTs` (242) đã có nhưng không gọi trong path entry → size/budget sai khi coin biến động mạnh trong phút.
- Sửa: lúc tính quantity, đọc `getPriceRealtime(symbol)` + check tuổi qua `getPriceRealtimeTs` (nếu quá cũ → fallback có cảnh báo). Giữ logic quyết định gate trên nến đóng nếu cần, nhưng SIZE theo giá tươi.

## #8 — aiBrain load fail → bot NGỪNG vào lệnh, KHÔNG alert (`DetectEntry initData:604` + `:412`)
- initData catch nuốt (LOG.error, không rethrow); `aiBrain==null` → mọi `createOrderBuyRequest` return ở :412 chỉ log info per-coin → bot chạy câm không vào lệnh, không ai biết.
- Sửa: aiBrain==null sau init → **Telegram alert + fail-fast** (hoặc cờ trạng thái rõ), đừng chạy câm.

## Acceptance
- [x] #6: Desktop+user đã chốt model live = V3 (33 feat) chạy bình thường → chỉ DỌN dead, KHÔNG đụng logic. predReturn15M không đổi (vẫn `p15M.predict(featuresV3)`).
- [x] #7: entry size dùng price_realtime tươi + check tuổi (`PRICE_REALTIME_MAX_AGE_MS`), fallback có cảnh báo.
- [x] #8: aiBrain==null → Telegram alert + ném IllegalStateException (fail-fast), không chạy câm.
- [x] Test riêng (BUILD SUCCESS mvn -o compile), không tự deploy.

## (Code điền)
- **#6 dọn dead V4 (`OnnxInferenceManager.java`):** xoá hẳn method `extractFeaturesV4Sideway` (30-feat) + dòng comment-out `featuresV4`; sửa comment field/log "V4 Sideway/Experimental"→"V3 Full". `predictAll` GIỮ NGUYÊN `p15M.predict(featuresV3)` & `pRisk4H.predict(featuresV3)` — KHÔNG đổi quyết định. Tác động SIM/PRODUCT: 0 (chỉ xoá code chết + comment).
- **#7 price_realtime vào sizing (`DetectEntry:createOrderBuyRequest` ~494 + `Configs.PRICE_REALTIME_MAX_AGE_MS=30s`):** thêm `priceForSizing` = `getPriceRealtime(symbol)` (242) nếu có & tuổi (`getPriceRealtimeTs`) ≤30s, ngược lại fallback `priceClose` + LOG.warn. CHỈ `Utils.calQuantity` dùng giá tươi; `priceEntry`/`priceTP`/record order giữ `ticker.priceClose`. Đặt SAU mọi early-return → 1 GET Aerospike/lệnh thật. Tác động: chỉ PRODUCT (live); SIM không gọi hàm này → KHÔNG cần bump CONFIG_VERSION.
- **#8 aiBrain fail alert (`DetectEntry:initData` cuối):** sau try-catch init, nếu `aiBrain==null` → LOG.error + `Utils.sendSms2Telegram` + `throw IllegalStateException` (start() chết → daemon restart, người biết ngay). Tác động: chỉ PRODUCT.
- **Bonus NPE BTC (`DetectEntry:checkMarketLevelChange2Trade` ~123):** `btcTickers==null/empty` → LOG.error + return (trước đây NPE rơi catch in stacktrace im lặng). Chỉ PRODUCT.
- **File đụng:** `OnnxInferenceManager.java`, `DetectEntrySignal2TradeNormal.java`, `Configs.java`. KHÔNG đụng file của TASK-028 (FundingIngestor/HttpRequest/BinanceDataIngestor).
