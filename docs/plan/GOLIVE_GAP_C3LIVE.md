# GOLIVE_GAP_C3LIVE — c3_shadow → c3_live: những gì CHƯA có để chạy tiền thật cùng logic quyết định

Ngày 2026-10-21. Đọc code nhánh `v1.1/ops-v11d` @ `2f82b6a4` (worktree `~/claude_master/v11d/wt`), chỉ đọc, không chạy gì trên 242.
Bối cảnh: pilot 10 000 USDT, DD 40 % (A40), kill-switch owner duyệt A40 + C1–C6 (`vz_e1_wt/docs/result/KILLSW_MENU.md` §4),
44 vị thế LEGACY do `BinanceOrderTradingManager` quản lý (owner tự cắt lúc go-live, KHÔNG đổi đường LEGACY).

## 0. Kết luận

1. `LIVE_PROFILE=c3_live` **đã có cổng đẩy lệnh** (`LiveProfileC3.forceNoPush`: cần `SHADOW_NO_PUSH=false` + `LIVE_ENTRY_ENABLED=true`
   + không có file `run/KILL_SWITCH`). Nhưng nếu mở cổng hôm nay, lệnh thật đi qua **đường LEGACY** (Redis queue →
   `processOrderNewMarketNew` → `OrderHelper.newOrderMarket` → `BudgetManager.symbol2Pos` → `initSLFirst`/`processDynamicTP_SL`).
   Đường này **không cùng logic C3** với sổ giấy, và có 3 lỗi chặn (G1): sizing đọc sổ giấy rỗng, vị thế C3 thật bị phân loại
   LEGACY sau ≤ 60 s, DCA grid C3 không bao giờ nhồi vị thế thật.
2. **Không được mở cổng push trước khi đóng hết các gap P0** (G1–G7, G9). Ước lượng công P0 ≈ 14–19 ngày dev, toàn bộ ≈ 22–29 ngày.
3. Quyết định owner cần trước khi code (mục 3): **tài khoản con riêng cho c3_live** (khuyến nghị mạnh — xoá gần hết G6 và một nửa G1),
   kiểu thoát (SL trên sàn hay nội bộ), cross/isolated + leverage, nguồn equity cho sizing và DD.
4. Đo chi phí thực thi trên shadow (exec-probe, mục 4) chạy được NGAY (chỉ log) và trả lời "size pilot có an toàn không"
   trước khi tiền thật vào.

## 1. Bảng gap (ưu tiên · rủi ro · công · owner)

P0 = chặn go-live; P1 = trước khi tăng size / trong tuần pilot đầu; P2 = cải thiện. Công = ngày dev (1 người), chưa tính review.

| # | gap | hiện trạng trong code (file:hàm) | rủi ro nếu bỏ qua | ưu tiên | công | owner quyết? |
|---|---|---|---|---|---|---|
| G1 | **Sổ LIVE C3 / nguồn trạng thái** | push path KHÔNG gọi `ShadowBookC3.openPos` (chỉ `shadowHandleOrder` gọi). Khi `LiveProfileC3.on()`: sizing dùng `book.marginRunning()/equityNow()` của **sổ giấy** (`DetectEntrySignal2TradeNormal.createOrderBuyRequest` ~:1150); `LegacySymbols.reconcile(real, paper)` = real \ paper ⇒ vị thế C3 thật thành LEGACY (arm 0.05, dead-zone ×5.21847, không time-stop); `LiveDcaGridC3.candidates` đọc sổ giấy ⇒ không DCA thật; guard trùng coin `book.isHolding` không thấy vị thế thật | over-size (U/U_MAX vô hiệu), luật thoát sai C3, mất DCA, có thể mua trùng coin trong cửa sổ ≤ 60 s | P0 | 3–5 | có (equity nguồn nào) |
| G2 | **Thoát thật: arm/ratchet/time-stop** | sổ giấy: nhịp 10 s, `px <= SL` ⇒ chốt ở đúng SL. Đường thật: `initSLFirst`/`processDynamicTP_SL` (2 s) đặt `STOP_MARKET` algo reduce-only (`OrderHelper.stopLoss`, cancel/replace `createSL`), ratchet từ `markPrice` Aerospike; **time-stop 168h chỉ log `would-CLOSE`, không đóng**; TS_MKT_EXT X14 chỉ có ở sổ giấy | lệch sim ở chân thoát (SL trên sàn trượt theo trigger CONTRACT_PRICE, không phải SL đúng); vị thế chưa arm giữ vô hạn | P0 | 2–3 | có (SL trên sàn vs nội bộ) |
| G3 | **Idempotency / retry / clientOrderId** | `OrderHelper.newOrderMarket` không đặt `newClientOrderId`; exception ⇒ `rpush` lại queue nếu < 5′ (`processOrderNewMarketNew` catch) ⇒ **lệnh trùng** khi lỗi xảy ra SAU khi sàn đã nhận (timeout); khoá `symbol2Processing` 2′ trong RAM, mất khi restart | mua gấp đôi/gấp ba một leg | P0 | 1–2 | không |
| G4 | **Làm tròn size / filter sàn** | `Utils.calQuantity` → `ClientSingleton.normalizeQuantity` dùng `minQty` của filter đầu tiên làm bước (không phải `stepSize`, bỏ `MARKET_LOT_SIZE`); `symbol2Notional` (MIN_NOTIONAL) nạp nhưng **không dùng**; qty = 0 ⇒ nới budget +1..+9 USDT rồi `getMinQuantity` (có thể vượt budget nhiều lần với coin giá cao; BTC ép 0.002); exchangeInfo đọc file local (cũ với coin mới list) | lệnh bị từ chối (-1111/-4164), hoặc size lệch budget; coin mới không có filter | P0 | 1 | không |
| G5 | **Leverage / margin mode / position mode** | code KHÔNG gọi change leverage / margin type / kiểm dual-side; qty tính theo `Configs.LEVERAGE_ORDER`; không truyền `positionSide` (giả định one-way) | leverage sàn ≠ cấu hình ⇒ margin thật lệch sổ; tài khoản hedge-mode ⇒ -4061 mọi lệnh; cross ⇒ dùng chung margin với LEGACY | P0 | 1 | **có** (cross/isolated, leverage) |
| G6 | **Tách khỏi LEGACY cùng tài khoản** | cùng ví, cùng margin cross, cùng Redis `REDIS_KEY_SYMBOL_2_ORDER_INFO`, cùng `BudgetManager.symbol2Pos`, cùng `is50PercentOrderLossProd`, cùng `DcaProcessor.getDCAProduction` duyệt mọi `symbol2Pos`; one-way ⇒ C3 mở trên coin LEGACY sẽ GỘP vị thế | DD LEGACY ăn margin C3 (và ngược lại), thanh lý chéo; DD 40 % đo sai gốc; gộp vị thế phá cả hai sổ | P0 | 2 (0,5 nếu tài khoản con) | **có** (khuyến nghị tài khoản con) |
| G7 | **Kill-switch act** | `KillSwitchEngine.ACT_IMPLEMENTED=false` (v11d chỉ log); file `run/KILL_SWITCH` chỉ chặn lệnh MỚI ở cổng push; C2 `onFill` chưa nối; C3 chỉ đếm lỗi `positionRisk`, không đếm lỗi đặt lệnh; C6/A40 đo trên equity GIẤY | không có bảo vệ tự động: DD 40 % không tự đóng; trượt > 2,5 % không chặn | P0 | 2–3 | có (xác nhận C2 2,5 % vs luật pilot 1,7 %; reset latch thủ công) |
| G8 | **Fill một phần / kế toán fill** | response MARKET (`NewOrderRespType.RESULT`) bị bỏ qua: `symbol2Pos` tạo từ qty YÊU CẦU + `priceEntry`=close nến; giá/qty thật chỉ có sau `updatePositionInfo` (giây 10 mỗi phút); không ghi phí, không orderId | sổ live lệch sàn tới 60 s; không đo được trượt thật (C2), không đối soát | P1 | 1–2 | không |
| G9 | **Đồng bộ sau restart (nguồn sự thật = sàn)** | restart 12h (v11d có cờ tắt) + Reporter reset; trạng thái thoát thật nằm ở Redis (`priceSL`, `timeStart`) chung LEGACY; sổ giấy nạp `open_positions.csv`; không có pha reconcile "persisted vs `positionRisk` vs openAlgoOrders" | sau restart: SL mồ côi/thiếu SL, mất `tsFirstLeg` (time-stop), legCount (DCA), peak | P0 | 2 | không |
| G10 | **Funding** | sổ giấy không tính funding; equity/DD không trừ funding thật | equity C3 lệch dần, DD 40 % trễ | P1 | 0,5 | không |
| G11 | **Giới hạn rate API (signed)** | `BinanceRestGuard` chỉ bọc REST public; mỗi lần dời SL = `getOpenAlgoOrders` + cancel + `getPositionInfo` + `postAlgoOrder` (~4 call), xét mỗi 2 s/vị thế; đợt 24 lệnh + 80 vị thế có thể chạm 1 200 order/phút hoặc weight 2 400/phút | ban IP (chung IP với ingest 242 ⇒ mất dữ liệu cho cả LEGACY) | P1 | 1–2 | không |
| G12 | **Đối soát sổ live vs sổ giấy** | không có; `tools/shadow_vs_sim.py` chỉ ghép giấy↔sim | không biết lệch đến từ đâu (trượt, lệnh bị từ chối, trễ, funding) | P1 | 1–2 | không |
| G13 | **Logging / audit** | log tự do (`Create order market…`), không orderId/clientOrderId/latency; `e.printStackTrace()` ở đường lệnh | không truy vết được sự cố tiền thật | P1 | 1 | không |
| G14 | **Trễ quyết định → khớp** | sim khớp ở close nến M; live gửi lệnh sau 6–10 s (qua Redis queue + executor) | chi phí ẩn (drift) — đo bằng exec-probe | P1 | đo: 0,5 (xong) | không |
| G15 | **Thử nghiệm không tiền** | quy tắc cấm testnet ⇒ cần adapter "dry" (đi hết đường size/round/clientOrderId/kill-switch nhưng không gửi) + mock sàn cho e2e | lỗi adapter chỉ lộ khi tiền thật | P0 | 1–2 | không |
| G16 | Delist / reduce-only / -4411 | có xử lý khoá symbol (`OrderHelper`), chưa có xử lý vị thế bị sàn đóng cưỡng bức trong sổ live | sổ live giữ "vị thế ma" | P2 | 0,5 | không |

Tổng P0 (G1–G7, G9, G15) ≈ 14–19 ngày; P1 (G8, G10–G14) ≈ 5–8 ngày; P2 ≈ 0,5 ngày.

## 2. Thiết kế đề xuất cho các gap P0 (tóm tắt — chưa code)

- **G1/G6 – `LiveBookC3`** (lớp mới, ngang `ShadowBookC3`): cụm theo symbol từ **fill thật** (qty/avgPrice từ response + user-data
  stream `ORDER_TRADE_UPDATE`), giữ `tsFirstLeg/legCount/firstEntryPrice/peak/priceSL`, persist file + đối soát `positionRisk`.
  Sizing c3_live đọc `LiveBookC3` (equity = `PILOT_EQUITY` 10 000 + realized C3 + MTM C3 − funding C3 − phí). `LegacySymbols`
  = real \ (paper ∪ **tập symbol do c3_live sở hữu, persist**). Sổ giấy vẫn chạy song song làm "twin" (G12).
- **G2 – thoát**: khuyến nghị **SL `STOP_MARKET` reduce-only trên sàn** (bảo vệ khi JVM chết) với tham số C3 (arm 0.07, ratchet liên tục,
  cùng `TradeUtils.calRateLossDynamicBuyPNoPump`), chỉ dời khi SL mới cao hơn ≥ 1 tick và ≥ 0,1 % (G11); time-stop 168h đóng
  market reduce-only; X14 dùng chung `TsMktExt`. Phương án nội bộ (như sổ giấy) khớp sim hơn nhưng không bảo vệ khi chết — owner chọn.
- **G3**: `newClientOrderId = c3-<sym>-<barStartMin>-<legIdx>` (≤ 36 ký tự), trước mọi retry `GET order?origClientOrderId`;
  -2011/-2013 ⇒ chưa có ⇒ mới gửi lại; không bao giờ `rpush` mù.
- **G4**: bước = `LOT_SIZE.stepSize` (MARKET: `MARKET_LOT_SIZE`), kiểm `minNotional`, `maxQty`; qty không đạt ⇒ BỎ leg + log (không nới budget);
  exchangeInfo nạp lúc start + mỗi 6h (REST public qua `BinanceRestGuard`).
- **G5**: lúc start, đọc (read-only) `positionSide/dual`, `leverageBracket`; trước leg đầu mỗi symbol: đặt leverage = cấu hình,
  margin type theo owner; sai ⇒ không vào lệnh.
- **G7 act**: C1–C5 ⇒ latch "NO_NEW_ENTRY" (chặn tại `createOrderBuyRequest` trước push VÀ tại `processOrderNewMarketNew`), vẫn quản lý
  vị thế; C6/A40 ⇒ đóng hết vị thế C3 (market reduce-only, chia lô, idempotent theo G3) + dừng + Telegram; latch persist file, chỉ owner
  xoá. C2 nối `onFill(avgPrice, close_M)`; C3 đếm lỗi đặt lệnh (-1xxx/-2xxx/timeout).
- **G9**: pha khởi động "reconcile trước khi trade": `positionRisk` + `openAlgoOrders` + `LiveBookC3` persisted ⇒ sàn thắng về qty/giá;
  thiếu SL ⇒ tạo; SL mồ côi ⇒ huỷ; lệch ⇒ WARN + Telegram, chặn entry tới khi khớp.
- **G15**: `LIVE_ADAPTER=dry` ⇒ đi hết adapter, ghi `[LIVE-DRY]` request đầy đủ, không gửi. Chạy ≥ 3 ngày trên 242 (song song shadow)
  trước khi mở push.

## 3. Owner cần quyết

1. **Tài khoản con riêng cho c3_live** (khuyến nghị): tách ví/margin/rate limit khỏi LEGACY; G6 gần như hết; DD 40 % đo đúng gốc.
2. Kiểu thoát: SL trên sàn (khuyến nghị) hay nội bộ như sổ giấy.
3. Margin **isolated** (khuyến nghị cho pilot, giới hạn thua mỗi coin) hay cross; leverage (= `Configs.LEVERAGE_ORDER` hiện tại).
4. Equity cho sizing/DD: ảo `PILOT_EQUITY=10000` + PnL C3 (khuyến nghị) hay số dư ví.
5. Ngưỡng C2: 2,5 % (menu kill-switch) — luật pilot cũ dừng ở 1,7 %/2,5 %; exec-probe pre-reg dùng 1,7 % (p90) làm cảnh báo.

## 4. Đo chi phí thực thi trên shadow — exec-probe (đã code, nhánh `v1.1/exec-probe`)

Chi tiết: `docs/prereg/PREREG_EXEC_PROBE.md`, runbook `docs/runbooks/DEPLOY_EXEC_PROBE_242.md`. Cờ `LIVE_EXEC_PROBE` (mặc định 0).
- Hook (chỉ khi `ExecProbe.on()`): `DetectEntrySignal2TradeNormal.createOrderBuyRequest` ngay sau `shadowHandleOrder` (leg vào/DCA đã ghi
  sổ giấy) và `ShadowBookC3.tick` ngay trước `closeAt` (trailing, time-stop). Hook chỉ xếp hàng số nguyên thuỷ, không I/O trên luồng giao dịch.
- Thread `ExecProbe` gom lô (500 ms), mở **một** websocket public `<sym>@depth20@100ms` (≤ 20 stream, ≤ 30 kết nối/5′), lấy message đầu,
  đóng; ghi `[EXEC-PROBE]` 1 dòng/sự kiện: mid, bid/ask, spread, notional L1, độ sâu phía khớp, VWAP walk-the-book cho đúng qty
  (và ×0,25, ×4), trượt so với giá sim (close nến M / SL), drift (mid vs giá sim) và impact (VWAP vs mid), trễ quyết định
  (`t_dec − close nến`) và trễ chụp. Không REST, không API key, không ghi Aerospike/Redis.
- Tải đo: parse depth20 + walk + format ≈ **45–48 µs/sự kiện**; RAM: hàng đợi ≤ 512 sự kiện (~100 KB) + 1 kết nối TLS ngắn/lô;
  +1 thread daemon (+ thread okhttp tạm). Dòng `[EXEC-PROBE-STAT]` mỗi giờ: CPU thread, heap, số kết nối, bỏ, no_book.
