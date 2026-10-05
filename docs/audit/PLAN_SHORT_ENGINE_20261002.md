# PLAN_SHORT_ENGINE_20261002 — kiểm kê đường SELL + kế hoạch dựng "SHORT SLEEVE gated OFF = byte-identical"

Ngày 2026-10-02 · branch `module` · HEAD lúc đọc `a6867424` · **CHỈ ĐỌC** (grep/git/sed): không sửa `.java`, không build, không chạy sim, không chạm 242/LIVE, không đọc key.
Mọi `file:line` là của HEAD `a6867424` (đã dịch ~7 dòng so với số trong đề bài; ví dụ `DetectEntrySignal2TradeNormal` 795 → 802, 1101 → 1108). Ước lượng dòng/ngày công là **ƯỚC**, không đo.

## 0. TL;DR

1. **Cổng nghiên cứu vẫn ĐÓNG.** `RESULT_SHORT_FEASIBILITY.md` (2026-09-30, commit `5241ba56`) = NO-GO (G1 net_short −102 173 USDT vs long +96 909; G2 decile âm nhất −0,0898 %/24h ≫ ngưỡng −0,2098 %, dấu lật năm). `AUDIT_SHORT_REVIEW_20261002.md` (`a6867424`) xác nhận NULL/NO-GO cho 12 vòng và đề xuất đúng 1 vòng kế: `PREREG_SHORT_BETANEUTRAL` (chưa commit). **Không nên viết Java trước khi vòng đó GO** — kế hoạch này chỉ là hồ sơ "build bao nhiêu, sửa chỗ nào, rủi ro gì" để owner quyết.
2. **Số điểm chạm: 42** (Engine/sim 30 · Live 10 · Config/tool 2). **CAO 8** (6 sim + 2 live), **TRUNG BÌNH 8**, **THẤP 26**. Chi tiết §3.
3. **Hạ tầng còn lại cho SELL rất mỏng**: `calTp()` (nhánh SELL, `OrderTargetInfoTest.java:281`), `TraceOrderDone.java:123` (dấu profit SELL), `Utils.calPriceTarget` (đối xứng sẵn), `createOrder(OrderSide side, …)` (nhận side nhưng thân hàm toàn giả định long), live `processDynamicTP_SL` (nửa-short). Mọi thứ khác (entry, exit, margin, MTM, funding, SL live) là **long-only**.
4. **Nguyên tắc giữ parity**: mọi logic short nằm trong nhánh `side == SELL` / method riêng / ledger riêng; **không tổng quát hoá** đường long. Khi `SHORT_SLEEVE_ENABLED=false` không lệnh SELL nào tồn tại ⇒ mọi nhánh short là code chết ⇒ md5 B0 `650c386f0d0dfea334af9d55ca2f21d4` (n 2517, eq 131 908) phải giữ nguyên sau TỪNG bước.
5. **Ước lượng**: sim-only ≈ **430–620 dòng Java main + 150–220 dòng test**; sim + live ≈ **590–880 + 230–320 test**. Công: **sim-only 4–6 ngày công; + live shadow 3–4; + live thật/testnet 2–3 (tổng 9–13)**. So với 647–890 dòng của Phương án B (HedgeBook BTC): cùng bậc độ lớn, xem §6.
6. **Thiếu hẳn (không thuộc việc này)**: model/pred riêng cho short, label ngược có chặn squeeze, gate/regime riêng, dữ liệu liquidation/L2/fill thật, alpha beta-neutral. Liệt kê §8.

## 1. Commit gỡ ENABLE_SHORT (2026-09-03)

Commit **`5f40a90c`** "refactor(engine): xoa 40 co-che TRO voi cau hinh dang chay" (2026-09-03 15:47, Claude Opus 5). Bản nháp SHORT được thêm 2026-07-18 bởi `8d93f939` (order-side SHORT, flag-gated) + `df542c51` (wire ENTRY short vào selector). `git log -S ENABLE_SHORT` còn các commit nhắc lại nó trong docs (`5a7aa348`, `5241ba56`...), nhưng **chỉ `5f40a90c` gỡ code**.

| Thứ bị gỡ (trong `5f40a90c`) | File (vị trí cũ trong diff) | Số dòng gỡ (xấp xỉ, đếm `^-`) |
|---|---|---|
| `Configs.ENABLE_SHORT` (final, env), `SHORT_SL_PCT` (mặc định 0.25), `SHORT_TIME_STOP_HOURS` (mặc định 24) + khối "6b. SHORT-SIDE" | `tradecore/Configs.java` | ~13 |
| `OrderTargetInfoTest.updateStatusShort(ticker)`: hard-SL cứng `entry*(1+SHORT_SL_PCT)`, fill `max(trigger, open)`; time-stop `max(open, close)`; **TODO trailing-short chưa làm** | `research/OrderTargetInfoTest.java` | ~41 |
| `createOrderSELL(...)` (wrapper `createOrder(OrderSide.SELL,…)`) | `research/SimulatorMarketLevelTicker1MStopLoss.java` | ~17 |
| Nhánh router `if (ENABLE_SHORT && side==SELL) { updateStatusShort; closeOrder; return; }` ngay sau `updatePriceByKlineSimple` | sim `startUpdateOldOrderTrading` | ~14 |
| Dispatch entry `if (ENABLE_SHORT) createOrderSELL else createOrderBUY` tại vòng selector `PREDICT_SYMBOL_TRADE` ("đảo chiều tín hiệu", gate/budget giữ nguyên) | sim | ~8 |
| 2 guard "SHORT cấm martingale": `if (!ENABLE_SHORT)` quanh DCA_LEVEL1 và `isDcaAlt` | sim | ~7 (2 chỗ) |
| 2 unit test `ShortEntryLifecycleTest` (129 dòng) + `ShortOrderMechanismTest` (101 dòng) | `src/test/.../research/` | 230 |
| **Tổng riêng cho SHORT** | | **≈ 100 dòng main + 230 dòng test** |

Cùng commit còn gỡ 39 cơ chế khác (breaker, SIZE_MULT, GateRollingThreshold...) — **không liên quan SHORT, không cần khôi phục** (nhưng `SHADOW_NO_PUSH` đã bị gỡ nhầm rồi khôi phục sau; xem comment `BinanceOrderTradingManager.java:160-173`).
Điều rút ra: bản nháp cũ **mới chỉ có hard-SL + time-stop**, chưa trailing, chưa sửa dấu funding, chưa ledger riêng, chưa live ⇒ **khôi phục `git revert` không đủ**; hơn nữa nó **đảo tín hiệu long** (chọn pNoPump thấp để SELL) — đúng loại "mirror" mà `RESEARCH_SHORT.md` đã kết luận không có edge.

## 2. Trạng thái hiện tại (đo bằng grep)

`grep -rn "OrderSide.BUY|OrderSide.SELL|createOrderBUY|createOrderSELL|ENABLE_SHORT|isShort|positionSide|SHORT" src/main/java --include=*.java | grep -v import | grep -v '^//'` = **127 dòng / 43 file**. Trong đó **67 dòng thuộc SDK `com/binance/client/**`** (POJO/REST: `RestApiRequestImpl` 19, 8 model × 5, ...) — không phải engine. **60 dòng thuộc `chuyennd/**`**, đáng kể: `Simulator…StopLoss` 11 (toàn `createOrderBUY`/`OrderSide.BUY`), `BinanceOrderTradingManager` 10, `OrderTargetInfoTest` 3, `Utils` 2, `DetectEntrySignal2TradeNormal` 2, `OrderHelper` 2, `TraceOrderDone` 2; còn lại là tool export/probe 1–3 dòng/file (`ExportFundingLabel`, `PassSpeedBenchV2/V3`, `CarryEdgeProbe`, `LunaDcaScenario`... — không nằm trên đường giao dịch).
Grep **bỏ sót** các chỗ giả định long mà không có chữ BUY/SELL (ví dụ `qty*(last-entry)`, `maxPrice >= entry*(1+arm)`), nên bảng §3 dựa trên đọc code, không chỉ grep.
`ENABLE_SHORT` còn đúng 1 dấu vết: `tradecore/Cfg.java:56` (danh sách prefix tham số giao dịch: `"ENABLE_SHORT"`, `"SHORT_"`) — nghĩa là key mới tên `SHORT_*` **đã được phân loại là tham số giao dịch** (bị fail-fast nếu đặt qua env khi có profile). Và comment mốc `Simulator…:375` ("co ENABLE_SHORT da go 2026-09-03 (long-only)").

## 3. Bảng kiểm kê điểm chạm (file:line · long giả định gì · short cần gì · rủi ro parity cho long)

Thang rủi ro (đối với **nhánh long khi sleeve OFF**): **CAO** = chạm đường dùng chung equity/margin/PnL/hot-path mọi tick (một thay đổi thứ tự phép tính float là đủ vỡ md5); **TB** = hàm dùng chung nhưng tách được bằng nhánh `side==SELL` đặt TRƯỚC code long; **THẤP** = method/nhánh riêng, gated key OFF mặc định hoặc không nằm trên đường long. Quy tắc cứng cho mọi CAO/TB: viết `if (side==SELL){…}` rồi để nguyên văn code long ở `else`/sau, **không** gộp thành helper, **không** nhân `±1f`, **không** đổi thứ tự cộng.

### 3.1 Engine / simulator (30 điểm)

| ID | file:line | Long giả định | Short cần | Rủi ro |
|---|---|---|---|---|
| E1 | `OrderTargetInfoTest.java:133-149` `updatePriceByKlineSimple` | chạy MỌI tick MỌI lệnh; `minPrice=min(low)`, `profitMin=qty*(minPrice-entry)` (đáy = bất lợi); `maeLow/maePeak` theo dõi cả hai đầu; gọi `accrueFundingMark` (:134) | nhánh SELL: bất lợi = `maxPrice`; `profitMin=qty*(entry-maxPrice)`; `minPrice` giữ vai trò tham chiếu trailing (đáy) | **CAO** |
| E2 | `:151-183` `calRateLoss/calRateLossMax/calProfit/calMargin` | `calProfit=qty*(lastPrice-entry)` → vào `unProfit` → `equityNow()`; `calMargin=qty*entry/lev` (abs, dùng được) | `calProfit` SELL = `qty*(entry-lastPrice)`; rate đảo dấu | **CAO** (qua `equityNow`) |
| E3 | `:185-244` `updateStatusNew` | arm khi `peak ≥ entry*(1+arm)`; SL=`calPriceTarget(entry,SELL,-rate)`=`entry*(1+rate)`; chạm khi `minPrice≤priceSL`; fill `min(priceSL, open)`; `STOP_MARKET_DONE` nếu `priceSL>entry` | `updateStatusShort` mới: arm khi `trough ≤ entry*(1-arm)`; SL=`calPriceTarget(entry,BUY,-rate)`=`entry*(1-rate)`; chạm khi `maxPrice≥priceSL`; fill `max(priceSL, open)`; `STOP_MARKET_DONE` nếu `priceSL<entry` | THẤP (method mới) |
| E4 | `:246-272` `updateTPSL` | ratchet SL chỉ LÊN (`priceSLChange>0 && priceSLNew>entry`) | ratchet chỉ XUỐNG (`priceSLNew<priceSL && priceSLNew<entry`) | THẤP |
| E5 | `:274-297` `calTp` | đã có nhánh SELL `qty*(entry-TP)-fee`; trừ `calFundingFee()`; slippage 2 chân | **không sửa**; chỉ thêm test dấu | THẤP |
| E6 | `:306-345` `computeFundingOnClose` (DRAFT/REVIEW-POINT dòng 328-334) | `feeTotal=Σ rate*qty*entry`; `calTp` TRỪ ⇒ **short bị trừ khi rate>0 (mô hình pessimistic)**; Binance thật: rate>0 ⇒ long TRẢ, **short NHẬN** | phải ĐẢO DẤU cho SELL (key `SHORT_FUNDING_SIGN`, mặc định REAL). Các script Python đã tính dấu ĐÚNG (`AUDIT_SHORT_REVIEW` F16: "LỖI tiềm ẩn chỉ khi build") — Java phải khớp | TB |
| E7 | `:347-366` `accrueFundingMark` (bật ở profile qua `SIM_FUNDING_MARK`) | `fundingAccrued += rate*qty*price*FUNDING_SCALE` mỗi mốc settle; chạy hot-path từ E1 | câu lệnh riêng cho SELL (đảo dấu); câu lệnh long giữ nguyên văn | TB |
| E8 | `:372-391` `trailRate` + `TradeUtils.java:40-62` `trailFromCap` | cap WEAK/STRONG theo `symbolPred`=pNoPump (S1) — **vô nghĩa với short**; `trailFromCap(maxProfitRate,maxGap)` là hàm thuần theo *profit rate* (làm tròn 0.005) | dùng lại `trailFromCap` với profit rate short=`(entry-trough)/entry`; cap theo nguồn pred short (chưa có → dùng 1 cap hằng, key riêng) | THẤP |
| E9 | `TradeUtils.java:30-32` `peakPrice`; `:107-123` `armRate` | `peakPrice = TS_PEAK_CLOSE ? close : max` | thêm `troughPrice` (close : min); arm rate short key riêng | THẤP |
| E10 | `Utils.java:281-290` `calPriceTarget` | đối xứng sẵn; `normalizePrice` làm tròn tick (exchange_info pin) | không sửa; test làm tròn SL short (không lọt về phía bất lợi quá 1 tick) | THẤP |
| S1 | `Simulator…:1262-1316` wrappers + `createOrder(OrderSide side,…)` | chữ ký nhận `side` nhưng thân (gate, sizing, cap, margin) toàn giả định long; comment "một bộ não" | **KHÔNG luồn side qua thân hàm chung**; viết `createOrderShort` riêng (~80–120 dòng, sao chép đúng các gate cần thiết) để đường long không bị đụng | THẤP (nếu tách) / CAO (nếu luồn) |
| S2 | `:1323-1345` `entryGate(predict, symbolPred, …)` → `EntryGate.java:184-214` | `pass(predReturn15M ≥ threshold(pNoPump))`: regime "market pump", ngưỡng theo pNoPump | gate short riêng: regime + pred short (chưa có); KHÔNG tái dùng `EntryGate.threshold` | THẤP |
| S3 | `:1347-1380` `PumpDumpFilter.shouldSkip`, `GATE_COUNT_ONLY`, `TIER_3` | lọc "pump-dump feature > p90" cho long; DCA_LEVEL1 bỏ tier3 | quyết định riêng cho short (filter này ngược nghĩa); bỏ | THẤP |
| S4 | `:1388-1399` sizing: `marginRunning`, `FIX_B3 ? equityNow()`, `managerBudget` (`TradeUtils.java:125`) | `budget = equity*F_BASE*throttle/ladder`; `u=marginRunning/equity ≥ U_MAX ⇒ null` | sleeve budget riêng + cap `SHORT_MAX_NOTIONAL_PCT`; chế độ ISOLATED không cho margin short vào `u` của long | **CAO** |
| S5 | `:794-840`, `:1464-1510` BOOK_CAP / CONC_CAP (AGG_DCA, PERCOIN, BD) | cộng margin MỌI leg đang mở (`symbol2OrderRunning`) | quyết định: short có tính vào cap của long không (ISOLATED: không; SHARED: có) — phải lọc theo side | TB |
| S6 | `:1517-1560` khởi tạo lệnh + `marginRunning += order.calMargin()` (:1559) | `minPrice=entry`, `maeLow=entry`, `firstEntryPrice`, `mergeOrder`, cộng margin vào counter dùng chung | `createOrderShort` tự khởi tạo; cộng vào `marginRunningShort` (ISOLATED) | **CAO** (counter dùng chung) |
| S7 | `:1174-1236` `mergeOrder`; `symbol2OrderRunning[]` (1 slot/symbol); `isSymbolRunning` :770 | `orders.get(0).side` đúng; nhưng **mỗi symbol 1 vị thế** — leg SELL trộn vào cụm BUY sẽ làm hỏng side/qty | giữ 1 vị thế/symbol (khoá cứng ở `createOrderShort`: `if (isSymbolRunning) return`); **cũng đúng với live one-way** (L10) | THẤP |
| S8 | `:983-1100` `startUpdateOldOrderTrading` | 5 cổng thoát đều hướng long: PRE_ARM_SL (:1000), LOSER_TIME_STOP min(open,close) (:1025-1033), COND_EXIT dùng `maePeak` (:1040-1046), TP-FIXED `close ≥ first*(1+TP)` (:1056-1070), ARM `peak ≥ entry*(1+arm)` (:1078) | router ngay sau `updatePriceByKlineSimple` (:989): `if (side==SELL){ startUpdateShort(...); return; }` (đúng mẫu đã bị gỡ) + bản short của 5 cổng | THẤP (router) |
| S9 | `PreArmSlUtils.java:26-41` | `stopLevel=first*(1+preArm)`, `hit: barLow ≤ stop`, `exit=min(stop,min(open,close))` | thêm `*Short`: `stop=first*(1-preArm)`, `barHigh ≥ stop`, `exit=max(stop,max(open,close))` | THẤP |
| S10 | `:1103-1138` `closeOrder` | `computeFundingOnClose`; `updatePnl`; `marginRunning -= calMargin` (:1135) | nhánh riêng cho SELL (ledger short) đặt TRƯỚC code long | **CAO** |
| S11 | `:255-270` MTM-at-low → `BudgetManagerSimple.updateTrueUnrealizedMin/updateEquityMtm` (:105,:130) | `unrealAtLow += qty*(tk.minPrice-entry)`, `notional += qty*minPrice`; MARGIN_CALL `equity ≤ MMR*notional` | short: dùng `tk.maxPrice`, dấu đảo; cộng riêng rồi gộp có chú ý (đáy long và đỉnh short KHÔNG cùng thời điểm: tổng là chặn dưới bảo thủ) | TB (metric trong result.json) |
| S12 | `:538-565` cuối kỳ | `priceTP=lastPrice`, `computeFundingOnClose`, `putOrderDone` | dùng được (calTp SELL-aware); thêm split done-map | THẤP |
| S13 | `:889-897` `updateSymbolDeListed` | đóng ở `lastPrice` (STOP_LOSS_DONE) | short trên coin delist sẽ ghi lãi ảo (giá treo thấp) ⇒ cần luật haircut (pre-reg) | THẤP |
| S14 | `:359,:391`, `:783-791` `getActiveOrderMap` → `DcaProcessor.getDCA` (`DcaProcessor.java:26-101`) | DCA/martingale dùng `calRateLoss()`/`lastPrice` dấu long | **loại lệnh SELL khỏi DCA** (squeeze p99 +20,4 %, max +602 % ⇒ martingale short = nổ vốn) | THẤP |
| S15 | `:311-314` `DCA_SIGNAL_GATE` eligibility | loss dấu long | lọc side | THẤP |
| S16 | `:410-445` vòng selector; `selectCands` :711-731; `time2SymbolPred` | `long[]` sắp TĂNG theo pNoPump (S1); top-K; `createOrderBUY(…selRank)` :436 | bảng pred short riêng + vòng gọi `createOrderShort` (**dữ liệu CHƯA CÓ**, §8) | THẤP |
| S17 | `:575` `TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone)`; `TraceOrderDone.java:91-160` | header cố định 24 cột; dấu profit SELL ĐÃ đúng (:123); `pnl=calTp` | **không thêm cột/dòng vào printDone.csv** (runbook cấm, ~6 script chấm điểm); short ghi `storage/printDone_short.csv` qua done-map riêng | THẤP |
| S18 | `research/analysis/x1_rates.py:80`, `c3_rates.py trades()`, `qret_ladder.py`, `java/fsrun/qret.py`, `beta_decomp_t170.py` | giả định 1 dòng = 1 lệnh selector long; không lọc `side` | đọc file short riêng / lọc `side`; nếu quên: **vỡ ÂM THẦM** | THẤP |
| S19 | `BudgetManagerSimple.java:40,178,189,305-348` (`marginRunning`, `equityNow`, `updatePnl: profit+=calTp`, `calUnrealizedProfit`, `calProfitLossMax`) | một ví duy nhất; `equityNow=balanceCurrent+unProfit` là GỐC sizing mọi lệnh long | ISOLATED: thêm `profitShort/marginRunningShort/unProfitShort` + `equityTotal()` chỉ để báo cáo; `updatePnl` có nhánh SELL đầu hàm; SHARED (chỉ khi cần so với live): cộng vào equity | **CAO** |
| S20 | `TickDecisionLog` (`posClose/pos/posOpenAtEnd/cand`), `shadow_vs_sim.py` | chưa đọc kỹ; chưa thấy ghi `side` | ghi side hoặc tắt log cho SELL | THẤP |

### 3.2 Live (10 điểm) — parity ở đây là *hành vi*, không có md5; rủi ro CAO = chạm đường long THẬT trên 242

| ID | file:line | Long giả định | Short cần | Rủi ro |
|---|---|---|---|---|
| L1 | `BinanceOrderTradingManager.java:156-195` `processOrderNewMarketNew`; `OrderHelper.java:34-39` | dùng `order.side` (ổn); `postOrder(positionSide=null)` ⇒ **one-way mode**; kill-switch `SHADOW_NO_PUSH` + `LiveProfileC3.forceNoPush()` chặn đẩy lệnh thật (:156-175) | dùng được cho SELL; **kill-switch giữ nguyên** + thêm kill-switch riêng `SHORT_LIVE_ENABLED` (mặc định false) | THẤP |
| L2 | `:185` `PositionHelper.createPosNew(symbol, entry, quantity)` (`PositionHelper.java:62-70`) | `positionAmt=+qty` | SELL phải là `−qty` (nếu không, `processDynamicTP_SL`/`initSLFirst` coi là long tới lần `updatePositionInfo` kế) | TB |
| L3 | `:313-376` `initSLFirst` | **`continue` cứng khi `positionAmt<0` (:326)**; `positionSide=BUY` (:324); `slBelowEntry` chỉ BUY (:348); nhánh `sideSL=BUY` cho SELL (:355-358) **không bao giờ tới** | bỏ `continue`, tổng quát hoá guard SL-sai-phía cho SELL (SL phải < entry) | **CAO (live)** |
| L4 | `:487-503` `tsGap` | `calRateLossDynamicBuyPNoPump(…, LATEST_SEL_PNOPUMP[symbol])` — pNoPump của selector long | gap short từ nguồn pred short (chưa có) hoặc cap hằng | THẤP |
| L5 | `:504-590` `processDynamicTP_SL` | **đã nửa-short**: `side2Sl=BUY` khi amt<0 (:538-540), đảo dấu `priceSLChange`; `rateLoss` đảo dấu qua `PositionHelper.calRateLoss` (:50-52). Thiếu guard `priceSLNew < entry`. **Lệch sẵn sim↔live**: live còn dead-zone ×5.21847 (`LIVE_RATCHET_DEADZONE_MULT`), sim ratchet liên tục (comment "CHỜ CHỐT HƯỚNG") | thêm guard; short thừa kế lệch này ⇒ **chốt hướng long trước** | TB |
| L6 | `:605-650` `createSL`; `OrderHelper.java:90-112` `stopLoss` | **chỉ có nhánh `positionAmt>0`, KHÔNG có else** ⇒ short không bao giờ có SL; `stopLoss` **hard-code `OrderSide.SELL`** ("Mặc định SL cho lệnh Long là Sell"), reduceOnly=true | tham số hoá side (SELL→BUY stop reduceOnly); sửa chữ ký ảnh hưởng đường long đang chạy | **CAO (live)** |
| L7 | `DetectEntrySignal2TradeNormal.java:802` (dummyOrder BUY để `fundingExtractor.extractFeatures`), `:915-1130` `createOrderBuyRequest`, `:1108` `new OrderTargetInfo(…, OrderSide.BUY, …)`, `:413-500` pool top-K, `:89/:874` `LATEST_SEL_PNOPUMP` | pool theo pNoPump TĂNG; entry luôn BUY; feature chiết xuất như long | `createOrderSellRequest` riêng, pool + map pred short riêng; kiểm feature extractor có phụ thuộc `side` không | TB |
| L8 | `BudgetManager.java:53-54` `symbolBuy/symbolSell` (điền ở `updatePositionInfo` :395-440; **không ai đọc**) | — | dùng làm khoá "1 vị thế/symbol/mọi chiều" | THẤP |
| L9 | `tradecore/selector/LiveProfileC3`, `ShadowBookC3` (sổ giấy trailing, "would-BUY", reset `minPrice`) | long-only; chưa đọc kỹ | bản short của sổ giấy cho giai đoạn shadow | TB |
| L10 | `SyncRequestClient.java:209,245` `changePositionSide/getPositionSide` (có, chưa dùng) | one-way mode: SELL trên coin đang long sẽ **giảm/đóng long**, không mở short | **KHÔNG chuyển hedge mode**; giữ one-way + khoá cứng "symbol đã có vị thế (bất kỳ chiều) ⇒ không vào short" (khớp S7) | THẤP (quyết định thiết kế) |

### 3.3 Config / công cụ (2 điểm)

| ID | file | Nội dung | Rủi ro |
|---|---|---|---|
| C1 | `tradecore/Configs.java` (+ `Cfg.java:56` đã coi `SHORT_` là prefix tham số giao dịch) | thêm key (mặc định OFF/giá trị trung tính), đọc qua `Cfg.get`; **KHÔNG thêm vào bất kỳ `profiles/*.properties` nào** (PROFILE_HASH đổi) | THẤP |
| C2 | `tools/check_cfg_gateway.sh`, `gen_config_inventory.sh`, `gen_config_field_map.py`, `tools/parity_clean.sh` | chạy lại sau khi thêm key (inventory sinh từ mã nguồn); `parity_clean.sh` so `printDone.csv` với bản nền C2b | THẤP |

**Tổng điểm chạm = 10 (E) + 20 (S) + 10 (L) + 2 (C) = 42.** CAO = E1, E2, S4, S6, S10, S19 (sim) + L3, L6 (live) = **8**. TB = E6, E7, S5, S11, L2, L5, L7, L9 = **8**. THẤP = 26.
Lưu ý quan trọng: nếu *luồn `side` qua `createOrder`* thay vì tách `createOrderShort`, S1/S2/S3/S5 đều thành CAO — đó là lý do kế hoạch chọn **tách**. Đổi lại phải có test đảm bảo các gate dùng chung (EntryGate, tier, cap) không trôi lệch giữa 2 đường.

## 4. Quyết định thiết kế cần owner chốt TRƯỚC khi viết dòng nào (đề xuất mặc định kèm theo)

| # | Câu hỏi | Đề xuất | Lý do |
|---|---|---|---|
| D1 | Dấu funding short | **REAL** (rate>0 ⇒ short nhận), key `SHORT_FUNDING_SIGN=REAL\|COST` | Binance thật; script Python đã tính đúng; mô hình DRAFT "chi phí" làm lệch nghiên cứu |
| D2 | Ví short: ISOLATED hay SHARED | **ISOLATED** cho nghiên cứu (long rows byte-identical kể cả khi sleeve ON); SHARED chỉ thêm sau, riêng để so với live | ISOLATED cho phép kiểm bất biến "long printDone không đổi khi ON" (§5, T7) — SHARED bắt buộc đổi `equityNow`/`u` của long |
| D3 | 1 vị thế/symbol/mọi chiều | **CÓ** | khớp sim `symbol2OrderRunning[]` và live one-way; tránh hedge mode |
| D4 | DCA/martingale cho short | **CẤM** | squeeze p99 +20,4 %, max +602 % (RESULT_SHORT_FEASIBILITY) |
| D5 | SL cứng bắt buộc + trần notional/lệnh + trần tổng notional short | **BẮT BUỘC**, key `SHORT_SL_PCT`, `SHORT_MAX_NOTIONAL_PCT`, `SHORT_MAX_CONCURRENT` | thua lỗ short không chặn trên (long tối đa −100 %); lev=1 nhưng cross-margin thì squeeze một coin ăn vào vốn chung |
| D6 | Fill khi gap-up | `max(trigger, open)` (mirror BOOKING-FIX TASK-118), slippage short tách key (squeeze rộng hơn 0.003 của long) | không look-ahead; tránh lạc quan |
| D7 | Delist/giá treo | haircut hoặc bỏ lệnh; ghi vào pre-reg | tránh lãi ảo ở S13 |

## 5. Kế hoạch build tối thiểu "SHORT SLEEVE gated OFF = byte-identical"

**Kỷ luật chung**: mỗi bước = 1 commit nhỏ; sau MỖI bước chạy cổng parity OFF; md5 lệch ⇒ **dừng, bisect ngay**, không làm bước kế. Không thêm key vào profile. Không thêm cột/dòng vào `printDone.csv`. Mỗi key mới có default OFF/trung tính và đọc qua `Cfg.get`.

### 5.1 Key config mới (tất cả `SHORT_*`, mặc định OFF; ví dụ — tên chốt ở pre-reg)

`SHORT_SLEEVE_ENABLED=false` (công tắc tổng; false ⇒ không tạo SELL) · `SHORT_LIVE_ENABLED=false` (kill-switch live thứ 2, bên cạnh `SHADOW_NO_PUSH`) · `SHORT_EQUITY_MODE=ISOLATED|SHARED` · `SHORT_FUNDING_SIGN=REAL|COST` · `SHORT_SL_PCT` · `SHORT_PRE_ARM_SL` · `SHORT_ARM_RATE` · `SHORT_TS_GAP_CAP` · `SHORT_LOSER_TS_HOURS` · `SHORT_TP_RATE` · `SHORT_TOPK` · `SHORT_MAX_NOTIONAL_PCT` · `SHORT_MAX_CONCURRENT` · `SHORT_SLIPPAGE_RATE` · `SHORT_PRED_DIR` (nguồn pred short; trống ⇒ bảng rỗng ⇒ không có candidate).

### 5.2 Thứ tự bước

| Bước | Việc | Chạm | Cổng bắt buộc |
|---|---|---|---|
| B0 | **Không code.** `PREREG_SHORT_BETANEUTRAL` GO + owner chốt D1–D7 (§4). Không có GO ⇒ dừng ở đây | — | GO nghiên cứu |
| B1 | Chụp "golden": build jar từ HEAD, chạy parity OFF (Kaggle sim B0 + `tools/parity_clean.sh`), lưu `md5(printDone.csv)=650c386f0d0dfea334af9d55ca2f21d4`, n 2517, eq 131 908 (`RESULT_HOLDTODIE.md:18`), cùng `result.json` (maxDD_mtm, MARGIN_CALL) | — | PASS = điểm tựa |
| B2 | Thêm key vào `Configs.java` (+ chạy `check_cfg_gateway.sh`, `gen_config_inventory.sh`). **Chưa đọc key ở đâu** | C1, C2 | parity #1 = md5 B0 |
| B3 | Nguyên liệu side-aware trong `OrderTargetInfoTest`/`TradeUtils`/`PreArmSlUtils`: `calProfit`/`calRateLoss`/`profitMin` (E1,E2), dấu funding (E6,E7), `troughPrice` (E9), `*Short` của PreArm (S9). Viết dạng `if (side==SELL){…}` đặt trước/sau code long nguyên văn | E1,E2,E6,E7,E9,S9 | unit test dấu (T1–T4) + parity #2 |
| B4 | Máy thoát short: `updateStatusShort`/`updateTPSLShort` (E3,E4,E8) + `startUpdateShort` + router `side==SELL` (S8) + bản short của LOSER_TS / COND_EXIT / TP-FIXED / ARM | E3,E4,E8,S8 | test T5–T6 + parity #3 |
| B5 | **Bước rủi ro nhất**: sổ riêng ISOLATED trong `BudgetManagerSimple` (`profitShort/marginRunningShort/unProfitShort`, `updatePnl` nhánh SELL), nhánh margin ở `closeOrder` (S10), MTM-at-high (S11), done-map riêng + `printDone_short.csv` (S12,S17), lọc side ở `getActiveOrderMap`/DCA (S14,S15) | S10,S11,S14,S15,S17,S19 | T7–T9 + parity #4 (+ so `result.json`: maxDD_mtm, MARGIN_CALL không đổi) |
| B6 | Đường vào: `createOrderShort` + vòng selector short + loader pred short (S1–S7,S16). Pred short rỗng ⇒ 0 lệnh | S1–S7,S16 | T10 (ON + bảng rỗng ⇒ md5 B0) + parity #5 |
| B7 | **Bất biến ISOLATED**: bật sleeve với short *tiêm giả* (test-only: vài lệnh SELL cố định); `printDone.csv` (long) phải **byte-identical B0**; `printDone_short.csv` khớp golden tính tay | toàn bộ | T11 |
| B8 | Chạy nghiên cứu short (pre-reg riêng, ngoài phạm vi kế hoạch này) | — | — |
| B9 | **Chỉ khi B8 GO + owner duyệt**: live trong shadow (L1–L10), kill-switch kép, testnet, **không động 242**; sửa `createSL/stopLoss/initSLFirst` bằng cách thêm overload/nhánh, giữ nguyên chữ ký đường long | L1–L10 | test hành vi + soi log `would-SELL` + đối chiếu `shadow_vs_sim.py` |

Chi phí cổng parity: 1 lần sim T170 ≈ 13 phút (DESIGN_HEDGED_BOOK §6); kernel Kaggle `flat3` ≈ 1 641 s (RESULT_TRAIL2_G2). B1–B7 ≈ 6 lần chạy ⇒ ~1,5–3 giờ chờ máy thuần (tuần tự vì Oracle 1 slot JVM), chưa tính build/debug. Lưu ý quy ước md5: `parity_clean.sh` so `printDone.csv` **bỏ dòng header**, còn `RESULT_HOLDTODIE.md` ghi `md5(printDone)` — kiểm lại cùng một quy ước trước khi so (chưa xác minh trong vòng đọc này).

### 5.3 Test bắt buộc

**Parity**: P0 = md5 B0 sau từng bước B2–B6 (OFF); P1 = ON + bảng pred rỗng ⇒ md5 B0; P2 = ON-ISOLATED + SELL tiêm giả ⇒ `printDone.csv` (long) vẫn md5 B0; P3 = `result.json` (maxDD_mtm, MARGIN_CALL, equity) không đổi khi OFF; P4 = `check_cfg_gateway.sh` PASS và PROFILE_HASH các profile hiện có không đổi.

**Unit (bảng golden tính tay, không dùng sim)**:
- T1 `calTp` SELL: entry 100, TP 90, qty 1 ⇒ lãi gộp +10 trừ fee/slippage; entry 100, TP 120 ⇒ lỗ.
- T2 funding: rate>0 ⇒ short NHẬN (phí âm), long TRẢ; rate<0 ngược lại; `SHORT_FUNDING_SIGN=COST` tái hiện DRAFT; **long không đổi 1 bit** so với bản trước (so trực tiếp `float` bằng `==`).
- T3 `calProfit`/unrealized SELL và `profitMin` (đáy bất lợi = `maxPrice`); `calMargin` abs.
- T4 `peakPrice/troughPrice`; `calPriceTarget(BUY,-r)` = `entry*(1-r)` + làm tròn tick không lọt về phía bất lợi quá 1 tick.
- T5 trailing short: arm tại −5 %; SL = `entry*(1-rate)` với `rate=trailFromCap(profitRate,cap)`; SL **luôn < entry** sau arm (tương đương bất biến "SL trên entry" của long); ratchet chỉ xuống; chạm khi `maxPrice ≥ priceSL`; gap-up `open>priceSL` ⇒ fill = open (đếm `CLAMP`).
- T6 hard-SL/pre-arm, loser time-stop (`max(open,close)`), TP-fixed (`close ≤ first*(1-TP)`), COND_EXIT (dùng `maeLow`).
- T7 sổ ISOLATED: margin/PnL/unrealized short **không** đổi `equityNow()` và `marginRunning` của long; `equityTotal` = tổng.
- T8 loại trừ: symbol đang long ⇒ `createOrderShort` return; symbol đang short ⇒ selector long bỏ qua; DCA/DCA_SIGNAL không bao giờ chọn lệnh SELL.
- T9 MTM-at-high + MARGIN_CALL cho short; delist (S13) theo luật đã chốt.
- T10/T11 như P1/P2 nhưng ở mức JUnit tích hợp (dataset nhỏ).
- Live (B9): `createSL` cho SELL đặt STOP_MARKET **BUY reduceOnly** (mock client, không gọi sàn); `initSLFirst` không còn bỏ qua amt<0; `stopLoss` overload không đổi hành vi với long (test hồi quy chữ ký).

## 6. Ước lượng dòng & công, đối chiếu tài liệu có sẵn

| Hạng mục | Dòng Java main (ước) |
|---|---|
| Config (C1) | 25–35 |
| `OrderTargetInfoTest` (E1,E2,E3,E4,E6,E7,E8 + `updateStatusShort/TPSL`) | 110–150 |
| `TradeUtils` + `PreArmSlUtils` (E9,S9) | 20–30 |
| Sim: router + `startUpdateShort` + 4 cổng thoát short (S8) | 60–90 |
| Sim: `createOrderShort` + vòng selector short + loader pred (S1–S7,S16) | 100–150 |
| Sim: closeOrder/MTM-at-high/done-map + `printDone_short` + lọc DCA (S10–S15,S17) | 60–90 |
| `BudgetManagerSimple` sổ ISOLATED (S19) | 40–60 |
| TickDecisionLog/side (S20) | 10–20 |
| **Sim-only** | **≈ 430–620** (+ test 150–220) |
| Live: `OrderHelper`/`createSL`/`initSLFirst`/`createPosNew` (L2,L3,L6) | 50–80 |
| Live: `createOrderSellRequest`, pool/map pred short, kill-switch, khoá 1 vị thế (L1,L4,L7,L8,L10) | 90–140 |
| Live: sổ giấy short (L9) + guard `processDynamicTP_SL` (L5) | 30–50 |
| **Sim + live** | **≈ 590–880** (+ test 230–320) |

**Công (người-ngày, ước)**: sim-only **4–6** (B2–B7, gồm ~6 vòng parity); live shadow **3–4**; live thật/testnet **2–3** ⇒ **9–13**. Chưa tính: huấn luyện model short, pre-reg/nghiên cứu, review song song.

**Đối chiếu**: (a) `STRATEGY_CONSOLIDATED.md §B.7` (`docs/archive/_cleanup_20260829/docs/`) là mục "Harness sẵn có" — **không có ước lượng dòng**; nó chỉ ghi `CarryEdgeProbe` "carry đã loại" (hiện cũng nhắc lại ở RESULT_SHORT_FEASIBILITY (i′)). (b) Con số **647–890 dòng** nằm ở `docs/design/DESIGN_HEDGED_BOOK.md §3` và `docs/result/RESULT_HEDGE_OVERLAY_A.md §7.1`, cho **Phương án B = HedgeBook BTC singleton song song** (HedgeBook 300–400 + HedgeBeta 90–130 + Budget 40–60 + hook 50–70 + funding SELL 15–25 + ledger 40 + test 100–150). Thiết kế ở đây **khác**: tái dùng `OrderTargetInfoTest`/exit machine thay vì sổ tách rời, thêm đường live, nên sim-only (430–620 + test ≈ 580–840) **cùng bậc** với 647–890, và tổng có live (≈ 820–1 200 gồm test) **vượt** nó. Cả hai tài liệu cùng chỉ ra đúng 3 điểm lõi gây rủi ro (`equityNow`, `marginRunning`/admission, dấu funding dùng chung) — khớp E2/S4/S19, S6/S10, E6/E7 ở trên. Điểm DESIGN_HEDGED_BOOK nêu mà kế hoạch này **không gặp**: va slot symbol BTCUSDT (không có hedge leg tách rời; thay bằng khoá 1 vị thế/symbol); điểm kế hoạch này gặp thêm: live (L1–L10) và pred short.

## 7. Rủi ro còn lại & cách giảm

1. **Parity long vỡ âm thầm** ở E1/E2/E7/S10/S19 (hot-path hoặc counter chung): giảm bằng quy tắc "nhánh SELL đặt trước, code long nguyên văn", không helper chung, parity sau từng bước, so cả `result.json`.
2. **Nhánh short chạy nhầm khi OFF**: công tắc `SHORT_SLEEVE_ENABLED` chặn ở `createOrderShort` và ở vòng selector; test P1.
3. **Số liệu nghiên cứu bị trộn** (script chấm điểm giả định 1 dòng = 1 lệnh long): ghi short ra file riêng; thêm lọc `side` vào 5 script (S18).
4. **Thua lỗ short không chặn trên + squeeze**: SL cứng bắt buộc, trần notional, cấm DCA; slippage short riêng; kiểm `max +602 %` trong test fill.
5. **Live one-way mode**: SELL trên coin đang long là *đóng long*. Khoá cứng 1 vị thế/symbol (L8/L10) và test.
6. **Live SL short không tồn tại hôm nay** (`createSL` chỉ nhánh amt>0): mở lệnh short thật khi chưa sửa L6 = **vị thế không SL**. Bắt buộc `SHORT_LIVE_ENABLED=false` mặc định và `SHADOW_NO_PUSH` còn nguyên.
7. **Lệch sim↔live có sẵn** (dead-zone ×5.21847 ở live vs ratchet liên tục ở sim; `LIVE_RATCHET_DEADZONE_MULT`): short thừa kế; chốt hướng cho long trước.
8. **Sửa chữ ký `OrderHelper.stopLoss` / `createSL` / `initSLFirst` chạm đường long đang chạy thật** (L3, L6 = CAO live): chỉ thêm overload/nhánh mới, không đổi hành vi hiện có; không deploy lên 242 trong phạm vi này.
9. **Ước lượng có thể thấp**: chưa đọc kỹ `TickDecisionLog`, `ShadowBookC3/LiveProfileC3`, `fundingExtractor` (có phụ thuộc `side`?) — đánh dấu "chưa đọc kỹ" ở S20, L7, L9.

## 8. Dữ liệu / model còn THIẾU cho short (liệt kê, không thuộc việc này)

- **Pred riêng cho short** (kiểu pNoPump/pDump): `time2SymbolPred` hiện là `long[]` sắp TĂNG theo pNoPump của selector S1 (cho long); không có bảng cho short. `LATEST_SEL_PNOPUMP` (live) cũng chỉ một map.
- **Label ngược có chặn squeeze** (forward return âm, kèm MAE/max-adverse): chưa có; 5 năm squeeze p99 +20,4 %, max +602 % (RESULT_SHORT_FEASIBILITY).
- **Gate/regime riêng cho short** (`EntryGate` hiện là regime market-pump, ngưỡng theo pNoPump).
- **Alpha beta-neutral**: chưa vòng nào đo (AUDIT_SHORT_REVIEW §10; ~90 % STATE là beta, excess +0,026 %/24h CI chứa 0).
- **Liquidation / L2 / fill thật** (kết luận FEASIBILITY: "chỉ mở lại khi có DATA MỚI"); mô hình trượt giá short khi squeeze; mark vs last cho stop; chính sách delist.
- **Chọn margin mode** (isolated/cross) và trần đòn bẩy cho sleeve short ở live (hiện `LEVERAGE_ORDER=1`).
- **Funding Aerospike** cho nguồn dấu (`FundingFeeManager`) đã có cho long; cần kiểm độ phủ cho coin short-eligible.

## 9. Tái lập bản kiểm kê

```
cd /home/ubuntu/src/BinanceFuturesJava            # branch module, HEAD a6867424
git log --all --format='%h %ad %s' --date=short -S ENABLE_SHORT | head
git show 5f40a90c --stat ; git show 5f40a90c | sed -n '2126,2268p;2870,3267p'
grep -rn "OrderSide.BUY\|OrderSide.SELL\|createOrderBUY\|createOrderSELL\|ENABLE_SHORT\|isShort\|positionSide\|SHORT" src/main/java --include=*.java | grep -v -i import | grep -v '^[^:]*:[0-9]*:[[:space:]]*//' | wc -l   # 127
sed -n '983,1100p;1174,1236p;1262,1560p' src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java
```
Không có tệp nào ngoài tài liệu này được tạo/sửa trong repo; một tệp scratch `~/claude_master/1002/_diff_5f40a90c.txt` (diff `5f40a90c`, ngoài repo, không commit) được tạo để đếm dòng.
