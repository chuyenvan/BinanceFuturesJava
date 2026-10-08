# NSEL_P0B — AUDIT KHỚP NỐI: khả thi cơ chế "LÕI cộng dồn" (CORE_ADD)

Ngày **2026-10-08**. Repo `module` @ `0c68609c`. Phạm vi: **chỉ đọc code + số có sẵn** — 0 sửa `.java`, 0 build, 0 sim/Kaggle, 0 chạm 242/shadow.
Số K4 tính bằng `research/analysis/nsel_p0b_addleg.py` (Python offline, `nice -n 10`, RAM < 1 GB ⇒ không tạo lock) trên printDone arm D
(`gkf-l2-k32`, `gkf2-l2k32-s7`, `gkf2-l2k32-s21`) + bảng MẤT của agent data (`~/claude_master/1008/nsel/j3_mat_rows.csv.gz`, chỉ đọc) + nến 1m
`/home/ubuntu/kaggle_data_hpo`. Cache sự kiện: `~/claude_master/1008/nsel/p0b_events.csv.gz`. JSON: `docs/audit/NSEL_P0B_ADDLEG_20261008.json`.
Viết tắt: `SIM` = `research/SimulatorMarketLevelTicker1MStopLoss.java`; `OTI` = `research/OrderTargetInfoTest.java`; `LIVE` = `trading/DetectEntrySignal2TradeNormal.java`;
`BOTM` = `trading/BinanceOrderTradingManager.java`; `OH` = `helper/OrderHelper.java`; `SB` = `tradecore/selector/ShadowBookC3.java`; `ARF` = `AIRejectFilter.java`;
`DP` = `tradecore/DcaProcessor.java`; `DU` = `tradecore/DcaUtils.java`; `TU` = `tradecore/TradeUtils.java`; `CFG` = `tradecore/Configs.java`.

## 0. KẾT LUẬN
1. **K1 — Sim và live đều là 1 VỊ THẾ GỘP / symbol.** Sim: `symbol2OrdersEntry[sym]` (danh sách chân) + `symbol2OrderRunning[sym]` (object cụm gộp) (`SIM:104-105`);
   chân mới (DCA/BIG_DOWN/...) được `orders.add` rồi `mergeOrder` dựng lại object cụm: **giá vào bình quân theo qty, qty cộng** (`SIM:1176-1186`),
   `firstEntryPrice` = chân đầu (bất biến, `SIM:1193`), `clusterFirstLegTime` = chân đầu (`SIM:1212`), `symbolPred/selRank` = chân đầu có giá trị (`SIM:1231,1237`),
   object mới ⇒ **`priceSL` = null ⇒ trailing reset** (constructor `OTI:114-130` không mang SL). Arm/TS tính trên **giá bình quân** (`OTI:156-158`, `OTI:185-196`, `OTI:246-268`);
   pre-arm SL / TP cố định / DCA-grid neo `firstEntryPrice` (`SIM:999-1000`, `SIM:1056-1058`, `DP:40-43`); time-stop 168h neo chân đầu (`SIM:1025-1027`).
   Đóng: `closeOrder` đóng **mọi chân cùng phút, cùng `priceTP`**, PnL tính từng chân, funding gán chân đầu (`SIM:1103-1136`) ⇒ cụm (sym,end) đúng (0/7.3k cụm lệch tp, K4).
   Live: **one-way** (lệnh MARKET `positionSide=null` `OH:42`; không có lời gọi `changePositionSide` nào trong `com.binance.chuyennd` — hedge mode sẽ từ chối lệnh không có positionSide ⇒ suy ra one-way, là cấu hình tài khoản, code không tự đặt).
   Net 1 chiều/symbol, sàn tự bình quân giá vào. Sổ giấy C3 (`SB`) cũng 1 cụm/symbol: `addLeg` cộng qty, bình quân, **reset `priceSL`, `peakRate`** (`SB:112-121`) — cùng ngữ nghĩa sim.
2. **K2 — Khoá symbol là `continue` IM LẶNG, không counter.** Sim `SIM:433` (chỉ `TickDecisionLog.candAlreadyOpen` khi TICKLOG bật, `SIM:430-432`); live `LIVE:493` (trước `gateCand++`).
   Coin bị khoá **không vào `createOrder`** ⇒ không `noteCandidate`, không tính `bookFull`, **r không nạp buffer** (`ARF:92-117`) ⇒ không tiêu "quota", không đếm skipFull
   (skipFull chỉ đếm bookFull `ARF:98-101`). Nhưng `selRank` vẫn tăng (`SIM:426`) ⇒ coin giữ chiếm hạng. LÕI pass trên coin THÊM đang giữ ⇒ **bị bỏ im lặng**.
3. **K3 — chỉ (a) CORE_ADD có cận dương; (b) re-entry ÂM; (c) suy biến về ~0 vì size THÊM = size LÕI ở cấu hình hiện tại.** Đề xuất (a) có ràng buộc (§3.4), sim trước, live sau khi có resize SL.
4. **K4 [ĐO, xấp xỉ, in-sample]** — lúc LÕI lẽ ra vào, vị thế THÊM: lỗ chưa thực hiện trung vị **−2,8…−3,3 %** (86–88 % đang lỗ, p10 −17…−20 %), tuổi trung vị **0,42–0,57 h**
   (58–61 % < 1 h, p90 25–29 h), U trung vị **0,44** (U ≥ 0,60 chỉ 0,6–0,8 %), đã arm TS 2,4–3,6 %, đa số 1 chân (1,01–1,03). THÊM đóng **sau** lệnh nền 57–58 %, cùng phút 20 %, trước 21–23 %.
   ΣPnL_S chân CORE_ADD (3 seed S42/S7/S21): **cận 1 (đóng cùng THÊM) 74,8k / 62,9k / 60,6k; cận 2 (đóng như nền) 52,3k / 48,1k / 47,6k** với size chân nền;
   với size theo U của arm (thực tế hơn, trung vị 0,48× chân nền): **36,1k / 28,6k / 30,1k** và **23,5k / 20,1k / 22,3k**. (b): **−8,3k / −3,6k / −7,4k**.
5. **K5** — CORE_ADD không thay F1/F2 (nó chỉ thu lại chân LÕI bị mất, không chặn THÊM vào sớm trong nến sập). `lastLeg0Ts` tách 2 tầng; CORE_ADD cập nhật mốc LÕI, không bị F2 chặn. Key mặc định OFF ⇒ byte-identical.

## 1. K1 — Biểu diễn vị thế

### 1.1 Sim
- Chân thêm vào cụm đang giữ chỉ có 2 đường: DCA_LEVEL1 (`SIM:376-381`, `SIM:390-399`; ứng viên = cụm thoả `shouldDcaGrid(firstEntryPrice, lastPrice, legCount)` `DP:40-43`, `DU:32-43`, mốc −50/−75/−90 % so chân đầu `CFG:205-206`)
  và nhánh DCA_SIGNAL_GATE (`SIM:440-451`, mặc định OFF). Selector/BIG_DOWN đều loại coin đang giữ (`SIM:338`, `SIM:433`).
- Size chân: `managerBudget = equity·F_BASE·(1−U/U_MAX)/ladder` (`TU:125-143`, ladder = 4 với `DCA_GRID_WEIGHTS=1,1,1,1`) × `gridLegWeightRatio = w·DCA_GRID_SCALE = 6` (`DU:47-63`, FIX_B2)
  ⇒ mỗi chân ≈ **2,25 %·equity·throttle**; tối đa 4 chân/coin (leg0 + 3 DCA) ≈ 9 % < `CONC_CAP_PERCOIN_PCT` 15 % (`SIM:1503-1518`).
- `legCount` của cụm = `gridLegCount` (`SIM:1215`, `SIM:733-741`) — quyết định bậc DCA kế và tỉ trọng; chân DCA-signal đã có tiền lệ **không tính vào bậc grid**.
- Sau khi thêm chân: TP/TS/arm tính lại trên giá bình quân, trailing **mất trạng thái** (cụm mới `priceSL=null`, phải arm lại khi đỉnh ≥ avg·1,07); pre-arm SL, TP cố định, mốc DCA, time-stop vẫn neo chân đầu.
- `marginRunning += calMargin` từng chân (`SIM:1575`), trừ cả cụm lúc đóng (`SIM:1135`) ⇒ U tăng theo từng chân thêm.

### 1.2 Live (đường thật 242 — hiện shadow, `SHADOW_NO_PUSH`)
- DCA thật: `DP.getDCAProduction` (`LIVE:355-366`, `LIVE:376-391`) dùng **`DcaUtils.shouldDca` cũ, KHÔNG phải grid** (`DP:156-179`) — sai khác sim đã có sẵn.
- Đặt lệnh: MARKET (`BOTM:184`, `OH:34-43`), rồi **ghi đè** `REDIS_KEY_SYMBOL_2_ORDER_INFO[sym]` bằng order MỚI (`BOTM:191`) ⇒ `priceSL=null`, `timeStart` = chân mới, `marketLevel` = chân mới; `symbol2Pos` tạm = qty chân mới rồi `updatePositionInfo` đọc lại từ sàn (`BOTM:189-197`, `BOTM:398-450`).
- SL: lệnh algo `STOP_MARKET` **reduceOnly với qty CỐ ĐỊNH = positionAmt lúc tạo** (`BOTM:665`, `OH:86-107`). Ratchet chỉ chạy khi `priceSL != null` (`BOTM:560`) trên giá bình quân sàn (`BOTM:522-530`);
  arm lại qua `initSLFirst` (`BOTM:354-379`). `createSL` chỉ huỷ STOP_MARKET cũ khi **giá khác** (`BOTM:629-641`). ⇒ Sau khi cộng qty vào vị thế ĐÃ arm, STOP_MARKET cũ còn treo với qty cũ cho tới khi arm lại:
  nếu khớp trước, chỉ đóng **một phần** vị thế, phần LÕI mới không có SL; Redis đã mất `priceSL`. Đây là rủi ro live chính của mọi phương án cộng qty.
- Đường giấy C3: `createOrderBuyRequest` chặn coin đang giữ trừ DCA-grid giấy (`LIVE:1062-1068`), `shadowHandleOrder` → `SB.openPos` → `addLeg` (`BOTM:224-239`, `SB:272-289`); `SB.tick` đóng **cả cụm** trên `avgEntry` (`SB:381-426`, `SB:428-445`).
- Time-stop live C3 neo `orderInfo.timeStart` (`BOTM:553-556`) = chân **mới nhất** sau ghi đè, còn sim neo chân đầu (`SIM:1026`) — lệch parity có sẵn cho cụm nhiều chân (đường giấy `SB:399` neo `tsFirstLeg`, đúng sim).

## 2. K2 — Khoá symbol hiện nay
| chỗ | điều kiện | hành vi | log/counter | quota gate |
|---|---|---|---|---|
| selector sim `SIM:423-433` | `isSymbolRunning` (`SIM:770-775`) | `selRank++` rồi bỏ qua | không (chỉ TICKLOG `SIM:430-432`) | không `noteCandidate`, không nạp r, không skipFull |
| market-signal/BIG_DOWN sim `SIM:338`, `SIM:352-357` | `symbolLocked` = coin đang giữ | không được chọn | không | BIG_DOWN không qua gate AI |
| selector live `LIVE:493` | `symbol2Pos.containsKey` | `continue` trước `gateCand++` | không | như sim (live gọi gate 4 tham số `LIVE:1007-1008`) |
| `createOrderBuyRequest` C3 `LIVE:1067-1068` | `book.isHolding` | `return` | không | gate đã chạy (r đã nạp) — khác sim |
- Hệ quả: (i) LÕI pass trên coin THÊM giữ ⇒ **mất im lặng**, không đo được trong log; (ii) quần thể buffer LÕI loại coin đang giữ ⇒ q phụ thuộc tập giữ (NSEL_P0_DATA J4/p4: q nền trên đường D = 0,76×);
  (iii) trên đường C3 live gate chạy TRƯỚC khoá giữ (`LIVE:1007` < `LIVE:1067`) ⇒ r coin đang giữ **có** nạp buffer live, sim thì không — lệch parity quần thể buffer có sẵn.
- Không có quota bị "tiêu" cho phút đó: quota = phân vị r, coin bị khoá không đóng góp r. skipFull chỉ xét `bookFull` (`SIM:1345-1347`, `ARF:98-101`).

## 3. K3 — Phương án "LÕI cộng dồn"

### 3.1 Bảng
| | (a) CORE_ADD vào cụm THÊM | (b) đóng THÊM rồi mở LÕI mới | (c) "nâng cấp" (bù qty tới size LÕI + cờ) |
|---|---|---|---|
| sửa sim | nhánh mới cạnh `SIM:440-451` (`else if` coin giữ bởi cụm tầng THÊM chưa có chân LÕI, rank ≤ K_LÕI) → `createOrderCoreAdd` theo mẫu `createOrderBuyDcaSignal` `SIM:1268-1271`; trong `createOrder`: gate **chỉ tầng LÕI** (buffer LÕI), `legIdx=0` như `SIM:1454` nhưng **không** nhân `DCA_SIGNAL_BASE_RATIO` (`SIM:1463`); loại chân khỏi `gridLegCount` (`SIM:733-741`); cờ `order.coreAdd/nselTier` (`SIM:1549-1550`); `mergeOrder` gán tầng cụm = LÕI (`SIM:1215-1237`) | trong nhánh `SIM:433`: gate LÕI phải chạy **trước** khi đóng (entryGate có side-effect nạp buffer `ARF:116-117`) ⇒ cần cờ "đã duyệt" cho `createOrder`; `closeOrder` với lý do mới (`SIM:1103-1136`) rồi `createOrderBUY` | như (a) nhưng qty = max(0, size_LÕI − qty_THÊM); cùng chỗ sửa |
| U / budget / throttle | +1 chân ⇒ U tăng `SIM:1575`, throttle chân sau giảm; `managerBudget==null` ở U≥0,60 ⇒ không thêm (K4: 0,6–0,8 % sự kiện) | đóng THÊM giảm U trước khi mở ⇒ chân LÕI to hơn (a) | ≈0 qty ⇒ ≈0 tác động |
| trần U THÊM (F2-a) | phải tách margin theo **chân** (cụm lẫn 2 tầng); kế toán theo cụm sẽ đếm sai | sạch (1 tầng/cụm) | đổi cờ cụm THÊM→LÕI: margin chuyển tầng — cần quy ước |
| skipFull / quota | chân LÕI là PREDICT ⇒ `bookFull` áp như thường; r của coin giữ-bởi-THÊM **được nạp** buffer LÕI (gần quần thể nền hơn hiện tại, nơi coin không bị giữ) | như (a) | như (a) |
| held | sau khi thêm, cụm = LÕI ⇒ mọi ứng viên sau trên coin bị khoá như nền | cụm LÕI mới | như (a) |
| tập trung | ≤ 2 chân leg0 + 3 DCA ≈ 11,25 % eq (throttle 1) < 15 % CONC-PC; K4: sau thêm p50 1,6 %, p90 2,6 %, >15 % = 0 | 1 cụm như nền | không tăng |
| live khả thi | cộng qty one-way OK; **phải** huỷ/tạo lại STOP_MARKET theo qty mới nếu cụm đã arm (K4: 2,4–3,6 % sự kiện đã arm) và không ghi đè `priceSL/timeStart` (`BOTM:191`); C3 giấy: `SB.addLeg` dùng ngay + thêm cờ tầng vào `saveState` | 2 lệnh MARKET (bán + mua) ở nến sập: trượt giá thật ×2, huỷ SL; one-way OK | như (a) |
| parity sim↔live | lệch có sẵn ×2: DCA thật dùng `shouldDca` cũ (`DP:156-179`), time-stop neo chân mới (`BOTM:555`); thêm: SL qty, nhịp selector 15′ vs 1′ | phí/trượt chân đóng không mô phỏng đúng (sim đóng tại `close(t)` không trượt) | như (a) |
| số K4 (cận, 3 seed) | size U-arm: cận1 28,6–36,1k, cận2 20,1–23,5k | **−3,6…−8,3k** (đóng THÊM tại close(m0) mất 51,7–60,6k so với kết quả thực của THÊM) | size THÊM = size LÕI (cùng `managerBudget`) ⇒ qty bù ≈ 0 ⇒ ≈ 0 |

### 3.2 Ghi chú từng phương án
- (a) giữ nguyên cụm THÊM (THÊM thực tế hồi lại: đóng nó ở m0 tệ hơn 52–61k), thêm đúng chân LÕI bị mất. Rủi ro: nhồi vào coin vừa sập (THÊM đang lỗ p50 −3 %), chân LÕI mất trạng thái TS của cụm,
  mốc DCA/pre-arm vẫn neo giá chân THÊM (cao hơn) ⇒ DCA kích hoạt muộn hơn so với giá chân LÕI.
- (b) thực chất "cắt lỗ THÊM ở đáy": bị loại bởi số (âm cả 3 seed dù dùng size chân nền cho LÕI).
- (c) chỉ có nghĩa khi THÊM được size nhỏ hơn (α<1); khi đó (c) = (a) với qty (1−α)·N. Ở arm D (cùng sizing) nó chỉ đổi nhãn.

### 3.3 Test cần có (a)
1) OFF ⇒ md5 B0 `650c386f` + gqsf-a1 `ad26fd55`; 2) `mergeOrder` với chân CORE_ADD: avg, qty, `firstEntryPrice` không đổi, `gridLegCount` không tính, bậc DCA kế không dịch; 3) tối đa 1 CORE_ADD/cụm;
4) size = leg0 LÕI (ratio bậc 0, không base-ratio); 5) U≥U_MAX ⇒ không thêm; 6) `closeOrder` đóng mọi chân, PnL từng chân; 7) gate: chỉ rank ≤ K_LÕI, chỉ buffer LÕI, nạp r đúng 1 lần;
8) fail-fast nếu bật cùng `SIM_DCA_SIGNAL_GATE` (chung nhánh `SIM:440`) hoặc khi NSEL 2 tầng tắt; 9) live: resize STOP_MARKET (mock client), `SB` persist cờ tầng round-trip.

### 3.4 Đề xuất
**(a) có ràng buộc**: 1 CORE_ADD/cụm, chỉ khi cụm đang ở tầng THÊM và chưa có chân LÕI, gate LÕI nguyên (rank ≤ 24, buffer LÕI), size LÕI bình thường theo U hiện tại, không tính bậc grid,
**chỉ sim** ở vòng kế (đo in-sim + stress in-sim vs D và vs K24, pre-reg trước). Live chỉ port sau khi có resize SL theo qty và giữ `priceSL/timeStart` khi thêm chân. Lý do: là phương án duy nhất có cận dương ở cả 2 cách size,
không phải đóng vị thế ở đáy (b), và (c) không có giá trị ở cấu hình hiện tại. Cận K4 không phải bằng chứng GO (xem §4.3).

## 4. K4 — Số có sẵn [ĐO, in-sample, chỉ báo cáo, KHÔNG chọn ngưỡng]
Tập: chân nền MẤT với nguyên nhân `2_giu_symbol` ở arm D, entry 2022–2025: S42 1674 / S7 1696 / S21 1679 (= NSEL_P0_DATA T2). Cụm THÊM tìm thấy 100 % (miss 0, trùng 0);
1418 / 1447 / 1444 cụm THÊM khác nhau. Tự kiểm: close nến 1m phút m0 == entry nền **100 %**; 0 thiếu nến; mô hình phí `COST = RATE_FEE + 2·SLIPPAGE` tái lập pnl nền, phần dư = funding (Σ +1,5k / 5049 chân, trung vị −0,04).

### 4.1 Trạng thái vị thế THÊM lúc LÕI lẽ ra vào (p10/p25/p50/p75/p90)
| seed | lãi/lỗ chưa TH vs giá BQ % | tuổi h | U | THÊM kết thúc − nền kết thúc (h) | đỉnh từ leg0 vs BQ % | đáy từ leg0 vs BQ % |
|---|---|---|---|---|---|---|
| S42 | −19,8 / −8,9 / −3,3 / −1,1 / +0,6 | 0,03 / 0,10 / 0,57 / 5,7 / 29,4 | 0,39 / 0,42 / 0,44 / 0,50 / 0,54 | −0,7 / 0 / +0,4 / +30,4 / +131 | 0,6 / 1,1 / 2,1 / 4,1 / 6,1 | −25,8 / −13,1 / −4,7 / −1,7 / −0,7 |
| S7 | −18,7 / −8,4 / −3,2 / −1,0 / +0,4 | 0,03 / 0,10 / 0,53 / 5,8 / 28,4 | 0,37 / 0,42 / 0,44 / 0,50 / 0,54 | −1,0 / 0 / +0,3 / +29,0 / +128 | 0,6 / 1,1 / 2,1 / 4,2 / 6,1 | −25,3 / −11,9 / −4,4 / −1,5 / −0,6 |
| S21 | −17,2 / −8,1 / −2,8 / −0,9 / +0,6 | 0,03 / 0,07 / 0,42 / 5,2 / 24,9 | 0,39 / 0,42 / 0,44 / 0,49 / 0,53 | −0,6 / 0 / +0,3 / +26,2 / +129 | 0,6 / 1,0 / 2,1 / 4,0 / 5,9 | −23,7 / −11,5 / −4,3 / −1,4 / −0,6 |

| seed | % đang lỗ | % đã arm TS (đỉnh ≥ BQ·1,07) | % U ≥ 0,60 | % tuổi < 1h | THÊM đóng trước / cùng phút / sau nền | số chân THÊM ≤ m0 (TB) | % U sau thêm ≥ 0,60 |
|---|---|---|---|---|---|---|---|
| S42 | 86,4 | 3,6 | 0,8 | 57,6 | 21,3 / 20,4 / 58,2 | 1,03 | 0,8 |
| S7 | 87,6 | 3,2 | 0,8 | 58,0 | 22,8 / 20,2 / 57,0 | 1,03 | 0,8 |
| S21 | 86,4 | 2,4 | 0,6 | 61,2 | 23,0 / 20,0 / 57,0 | 1,01 | 0,6 |

### 4.2 Cận ΣPnL_S (stress 1,675 % khi nến quyết định sập; không funding)
| seed | ΣPnL_S chân MẤT (thực) | cận 1, size nền | cận 2, size nền | cận 1, size U-arm | cận 2, size U-arm | ROI_S cận1 / cận2 % | % chân cận1 < 0 | (b) tổng | ΣPnL cụm THÊM (thực) |
|---|---|---|---|---|---|---|---|---|---|
| S42 | 52 872 | 74 778 | 52 299 | 36 064 | 23 514 | 4,57 / 3,19 | 23,8 | −8 274 | −4 710 |
| S7 | 48 782 | 62 881 | 48 118 | 28 551 | 20 143 | 4,06 / 3,11 | 25,1 | −3 622 | −7 105 |
| S21 | 47 840 | 60 601 | 47 566 | 30 087 | 22 304 | 3,90 / 3,06 | 24,6 | −7 384 | −9 224 |
- Theo loại chân: PRED 1564/1588/1570 chân, cận 1 size nền 66,0k/55,3k/53,4k, cận 2 49,3k/45,9k/45,5k; BIG_DOWN ~110 chân/seed, cận 1 7,2–8,7k, cận 2 2,1–3,0k (BIG_DOWN không qua gate AI — không thuộc "LÕI gate").
- Theo năm (cận 1 / cận 2, size nền): 2022 S42 −2,6k / +0,4k, S7 −1,7k / +2,0k, S21 −0,9k / +1,6k; 2023 8,1–12,2k / 7,5–10,7k; 2024 31,3–35,5k / 22,0–24,8k; 2025 22,1–29,7k / 15,4–16,4k.
  ⇒ cận 1 **âm năm 2022 ở cả 3 seed**, phần lớn đến từ 2024–2025.
- Theo ngày (ngày có sự kiện: 106/111/108): ΣPnL_S cận 1/ngày p5 −1,07…−1,46k, p50 +0,24…+0,30k, p95 +3,3…+3,7k, min −3,6…−4,0k, max +11,0…+13,3k; ngày âm 24–29 % (cận 2: 15–21 %).
  Hiệu cận1−cận2 theo ngày: TB +121…+212, sd 1,0–1,1k, ngày âm 39–42 % ⇒ chênh giữa hai cận chủ yếu từ ít ngày lớn.
- Size U-arm = eq_arm·0,0225·max(0, 1−U/0,60), trung vị **0,48×** notional chân nền (arm đang giữ nhiều hơn ⇒ throttle thấp hơn).

### 4.3 Hạn chế (bắt buộc đọc)
1. **Không mô phỏng lại đường đi.** Thêm chân làm giá BQ thấp hơn ⇒ arm/TS kích hoạt ở mức giá khác, thoát khác `tp` thực của THÊM; cận 1 **không phải cận trên chặt**, cận 2 không phải cận dưới.
2. Không mô hình lãi kép, U tăng làm nhỏ các chân sau, thay đổi held/buffer (r coin giữ-bởi-THÊM sẽ nạp buffer LÕI ⇒ q_LÕI đổi), DCA thêm trên cụm gộp, funding.
3. In-sample, cùng dữ liệu đã dùng để phát hiện J3; đã nhìn k = 5 biến thể (2 cận × 2 size + (b)) ⇒ nếu dùng làm sàng lọc phải nới √(2 ln 5) = 1,79× half-width. Không có CI ở đây vì không có thước MTM ngày cho chân giả định.
4. Luật GO/NO-GO phải là sim in-sim + stress in-sim (NSEL_P0_CODE J5), thước chính ghép cặp theo ngày MTM vs B0×c đã chốt trước.

## 5. K5 — Tương tác với gate 2 tầng (NSEL_P0_CODE J7)
- **F1/F2 vẫn cần.** CORE_ADD chỉ thu lại chân LÕI bị mất; không ngăn THÊM vào CÙNG coin sớm 0,4–0,6 h trong nến sập (nguồn của ROI_S leg0 THÊM −1,15…−1,57 %). F1 (nến sập) trên THÊM giảm trực tiếp số va chạm này.
- **`lastLeg0Ts` tách 2 tầng**: `lastLeg0Ts_core`, `lastLeg0Ts_add`, cập nhật đúng chỗ chân thật sự mở (`SIM:1556-1575`, sau mọi `return`). CORE_ADD **không** phải leg0 nhưng là một lần vào LÕI ⇒ cập nhật `lastLeg0Ts_core`,
  **không** bị F2 chặn (F2 chỉ áp tầng THÊM). Live: khôi phục sau restart từ `SB`/sổ (đã nêu J7).
- **Kế toán U theo chân** (`marginCore`, `marginAdd`) thay vì theo cụm — cụm gộp chứa 2 tầng; trần `NSEL_ADD_U_MAX` chỉ đọc `marginAdd`.
- **Counter** (1 dòng `[NSEL]` cuối run + 1 dòng SLF4J/sự kiện, không thêm cột printDone): `core_on_held_by_add_would` (đếm cả khi OFF bằng `GRB.queryOnly`, không nạp buffer ⇒ không đổi hành vi),
  `core_add_seen`, `core_add_entered`, `core_add_rej_budget`, `core_add_rej_conc`, `core_add_rej_max1`, `core_held_by_core`; dòng `NSEL_CORE_ADD sym tOpenThem tAdd unreal U rank`.
- **Key đề xuất** (mặc định OFF ⇒ byte-identical): `SIM_NSEL_CORE_ADD` (false) · `SIM_NSEL_CORE_ADD_MAX_PER_CLUSTER` (1) · `SIM_NSEL_CORE_ADD_SIZE_RATIO` (1.0) · `SIM_NSEL_CORE_ADD_IN_GRID` (false) ·
  `LIVE_NSEL_CORE_ADD` (false; fail-fast nếu bật ở đường thật khi chưa có resize STOP_MARKET). Fail-fast: CORE_ADD bật ∧ NSEL 2 tầng tắt; CORE_ADD ∧ `SIM_DCA_SIGNAL_GATE`; CORE_ADD ∧ `GATE_BUFFER_TOPK>0`.

## 6. Tái lập
`nice -n 10 python3 research/analysis/nsel_p0b_addleg.py --workers 3` (~4 phút, RAM < 1 GB; đọc 350 file nến ngày; import `nsel_p0_data.load`). Ghi `~/claude_master/1008/nsel/p0b_events.csv.gz` và JSON.
