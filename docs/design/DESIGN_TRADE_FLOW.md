# DESIGN_TRADE_FLOW — Luong trade HIEN TAI, doc TRUC TIEP tu code

> **Muc dich**: tai lieu nen de owner phan tich luong trade dang chay. **Moi khang dinh deu doc tu
> code that, kem `file:line`.** Khong suy dien, khong lay tu tri nho, khong chep lai tai lieu cu.
>
> **Pham vi do luong**
> - Code: `git rev-parse HEAD` = **`aebeb38481d9cda7be068a75bde33f79ced455e1`** (branch `module`, 2026-09-24).
> - Cau hinh baseline: **`profiles/t170_flat_keepleg0.properties`** (KEEPLEG0) + `config.properties`
>   + default hardcode trong `Configs.java`.
> - Phuong phap: chi DOC code (khong chay Java/sim tren Oracle — shadow LIVE). File nay la file duy nhat duoc tao.
>
> **Quy uoc ten file trong tai lieu**
> | Ten tat | Duong dan |
> |---|---|
> | `SML` | `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java` |
> | `OTIT` | `src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java` |
> | `TradeUtils` | `src/main/java/com/binance/chuyennd/tradecore/TradeUtils.java` |
> | `Configs` | `src/main/java/com/binance/chuyennd/tradecore/Configs.java` |
> | `EntryGate` | `src/main/java/com/binance/chuyennd/tradecore/EntryGate.java` |
> | `DcaUtils` / `DcaProcessor` | `src/main/java/com/binance/chuyennd/tradecore/DcaUtils.java` / `DcaProcessor.java` |
> | `MBDetector` | `src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java` |

---

## 0. NGUON DU LIEU

### 0.1 Bon khoi du lieu (nap 1 lan, tru ticker)

`SML.initData()` (`SML:890-945`) nap DONG THOI ca 4 khoi vao RAM truoc khi vao vong lap:

| Khoi | Bien engine | Nguon A (env `WFO_DATA_DIR`) | Nguon B (mac dinh) | Code |
|---|---|---|---|---|
| Market | `time2MarketData` | `market.bin` trong WFO dataset | Aerospike `market_data` | `SML:900-921`; `WfoDataset.java:41,306-322` |
| AI-pred | `predictionMap` | `pred.bin` | Aerospike `ai_pred_market_full_basket_v2` | `SML:901-921`; `WfoDataset.java:46` |
| Selector S1 | `time2SymbolPred` | `funding.bin` (build tu bins) | Aerospike funding-pred | `SML:902-934`; `WfoDataset.java:47` |
| Ticker 1m | `time2Tickers` (theo NGAY) | — (luon doc theo ngay) | Aerospike / `kaggle_data_hpo/ticker_*.bin` | `SML:224-241` |

### 0.2 Ticker 1m — `ticker_*.bin`

- Ten file: `"ticker_" + Utils.sdfFile.format(dayTs)` → `kaggle_data_hpo/ticker_<yyyyMMdd>.bin` hoac `.bin.gz`
  (`KaggleDataLoader.java:19,23-43,100-101`).
- Chon nguon bang `TICKER_SOURCE` (`config.properties:21` = `aerospike` trong repo; box dev Kaggle dat `file`):
  - `aerospike` → `DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(startTime)` (`SML:229-231`);
  - `file` → `KaggleDataLoader.loadDailyTickersShort(startTime)` (`SML:239`; `KaggleDataLoader.java:100-133`) —
    key `String` → convert sang `short` symbolId bang `SimpleSymbolMapper`, mang `KlineObjectSimple[1000]`.
  - Thieu/sai `TICKER_SOURCE` → `throw` (`SML:241-244`); ngay rong → `throw` FAIL-FAST (`SML:246-249`).
- **Tan suat nap: 1 NGAY / vong lap** (`SML:188` `while(true)`, cuoi vong `startTime += Utils.TIME_DAY`, `SML:531`).
  Ngay co `<1440` phut → `dayDataErrors++` va SKIP **toan bo ngay do** (khong kiem SL, khong cap nhat maxDD) (`SML:219,484-491`).
- Bar 1m `KlineObjectSimple` = `{startTime, priceOpen, maxPrice(high), minPrice(low), priceClose, totalUsdt}`;
  `Utils.isTickerAvailable()` = `minPrice != maxPrice || totalUsdt != 0` (`Utils.java:457-463`).

### 0.3 Market / funding / pred

- **Market** `MarketDataObject{rateDownAvg, rateUpAvg, rateDown15MAvg}` (`object/MarketDataObject.java:5-15`).
  Duong sim **khong tinh lai** market breadth; no duoc nap san (0.1). `SML:322` chi `.get(time)`.
- **AI-pred** `AiPredictionData.predReturn15M` (`SML:330,1039-1044`) — tra theo khoa **dung phut**
  `predictionMap.get(ticker.startTime)` (`SML:1249`), **khong forward-fill**.
- **Funding fee** (phi giu lenh): `FundingFeeManager.getFundingHistory(symbol)` — moc settle THAT
  (`OTIT:301-334`); tinh 1 luot luc dong cum, hoac tich luy theo tick khi mark-mode.

### 0.4 `WFO_FUNDING_PRED_DIR` = S1 bins (file pred)

- Khai bao bat buoc trong profile: `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1`
  (`profiles/t170_flat_keepleg0.properties:21`; thieu/tro sai → `IOException` fail cung, `WfoDataset.java:87-96`).
- Doc `predict_wf_*.bin`, ban ghi **26 byte big-endian**: `[long ts][short symId][float p4h][float p12h][float p24h][float p72h]`
  (`WfoDataset.java:212-247`).
- Chon horizon bang `WFO_SEL_HORIZON_IDX` (default **1 = 12h**) (`WfoDataset.java:101`).
- Encode vao engine: `long = (symId << 32) | Float.floatToRawIntBits(score)` voi **`score = 1.0f - pWin`**
  (`WfoDataset.java:247`) — **DAO DAU** so voi xac suat thang; engine uu tien score NHO.
  Engine goi gia tri nay la `symbolPred` / **`pNoPump`** (`TradeUtils.java:38-45`, `docs/runbooks/AGENT_RUNBOOK.md:311`).
- **Forward-fill 15m → 1m**: moi phut lay `floorEntry(ts)` cua luoi 15m, chan stale `<= 15 phut`
  (`WfoDataset.java:125-132,281-300`; tat bang `WFO_FUNDING_FILL=0`). Vi vay selector co mat ~100% so phut
  (khac `predReturn15M` — khong fill).
- Guard chong leak: ts-range cac file `predict_wf_*` phai ROI NHAU (overlap → `IOException` LEAK-SUSPECT,
  `WfoDataset.java:249-259`); span moi fold `<= 100` ngay (`WfoDataset.java:107-112`).
- **Niem phong 2026**: moi ban ghi `>= 2026-01-01` bi cat khoi ca 3 khoi (`WfoDataset.java:136-139`,
  `HoldoutSeal.trimMap`).

### 0.5 Don vi thoi gian (GMT+7 vs UTC) — DIEM DE NHAM

- Moc thoi gian trong engine la **epoch millis**. Goc chay: `startTime = sdfFile.parse(TIME_RUN).getTime() + 7 * TIME_HOUR`
  (`SML:118`) voi `sdfFile` **gan cung GMT+7** (`Utils.java:38-51`).
  `TIME_RUN=20210101` (`config.properties:29`) ⇒ `2021-01-01 00:00 GMT+7` **+ 7h** = **`2021-01-01 00:00 UTC`**.
  ⇒ **"Ngay" cua simulator = ngay UTC, bat dau 00:00 UTC (= 07:00 GMT+7)**, va `time % Utils.TIME_DAY == 0`
  (nua dem, `SML:457`) la **00:00 UTC**.
- Nhung **moi log/ten file lai format theo GMT+7**: `Utils.normalizeDateYYYYMMDDHHmm` (`Utils.java:170-174`),
  ten file ticker `sdfFile` GMT+7. ⇒ Doc log GMT+7 nhung ranh gioi ngay la UTC.
- Funding: `FundingFeeManager` dung moc settle that cua san (00:00/08:00/16:00 UTC), quet trong
  `(clusterFirstLegTime, timeUpdate]` (`OTIT:310-325`).

---

## 1. VONG LAP CHINH — thu tu tung buoc

Class chay: **`SimulatorMarketLevelTicker1MStopLoss`**, ham `simulatorWithInitEntry(startTime, endTime)`
(`SML:141`). Truoc khi vao vong lap co guard lien chinh `BacktestIntegrityGuard.assertProductionGrade()`
(`SML:146`).

Mot **tick = 1 phut** (1 entry cua `time2Tickers`). Thu tu TUYET DOI trong 1 tick:

| # | Buoc | Code |
|---|---|---|
| 1 | Dat `EntryGate.CURRENT_REGIME_SCALE = RegimeSchedule.scaleForTime(time)` (chi khi `GATE_REGIME_ADAPTIVE`; default OFF) | `SML:224` |
| 2 | `HistoryManager.updateHistoryArray(symbol2Ticker)` — **bo qua** khi `WFO_STATIC_RANK` | `SML:230-232` |
| 3 | **UPDATE TUNG VI THE DANG MO** (copy mang `activeRunningIds`) → goi `startUpdateOldOrderTrading(time, id, ticker)` cho tung symbol → **toan bo logic EXIT nam o day** | `SML:235-254`; `SML:946` |
| 4 | Do maxDD THAT: `Σ quantity*(bar.low - priceEntry)` → `updateTrueUnrealizedMin(...)`; roi `updateEquityMtm(...)` (report-only) | `SML:288-305` |
| 5 | (chi khi `DCA_SIGNAL_GATE=true`, default **false**) pre-pass tick: `dsReserved`, T1/T2 counters | `SML:307-350` |
| 6 | Lay `marketData`; `tickBlocked = TickWeakBlock.step(...)` (default OFF) | `SML:322,324` |
| 7 | **Sinh tin hieu**: `levelChange = MarketBigChangeDetector.getMarketStatus1M(...)` (chi `BIG_DOWN` hoac `null`) | `SML:330` |
| 8 | Chon `symbol2BUY` = leg market-signal (`BdSelection.select` neu ACTIVE, else `getTopSymbolArray(numberOrder, ...)`) — loai symbol dang chay (`symbolLocked`) | `SML:343-355` |
| 9 | `symbolDcaLevel = DcaProcessor.getDCA(levelChange, time, budget, activeOrderMap)`; tie-break `dsFilterGrid` | `SML:358-362` |
| 10 | **Vao lenh nhom A** (market-signal): `createOrderBUY(..., levelChange, ..., null)` cho tung symbol — **chi khi `!SELECTOR_ONLY_ENTRY`** | `SML:365-372` |
| 11 | **Vao lenh nhom B** (DCA grid): `createOrderBUY(..., DCA_LEVEL1, ..., null)` | `SML:374-381` |
| 12 | Nhanh `isDcaAlt(...)` → `getDCA(null, ...)` lan 2 → them leg `DCA_LEVEL1` | `SML:388-405` |
| 13 | **Vao lenh nhom C** (selector): `time2SymbolPred.get(time)` → `selectCands` (top-K) → bo symbol dang chay → `createOrderBUY(..., PREDICT_SYMBOL_TRADE, marketData, symbolPred, selRank)` | `SML:407-450`; `selectCands` `SML:701-720` |
| 14 | Cuoi tick: nua dem → `updateBalance(..., true)` (+`System.gc()` dau nam); moi gio → check delist `updateSymbolDeListed` + `updateBalance(..., false)` | `SML:457-476`; `SML:879-888` |
| 15 | (neu `TickDecisionLog.ON`) ghi trang thai read-only | `SML:480-485` |

Het ngay → `startTime += TIME_DAY`; ket thuc khi `startTime > endTime` (`SML:529-535`).
Cuoi run: cum con mo duoc ghi ra `allOrderDone` + `computeFundingOnClose()` cho tung cum (`SML:537-575`).

**Thu tu 3 nhom leg trong 1 tick: A (BIG_DOWN/market-signal) → B (DCA trong nhanh `levelChange`) → C (selector top-K).**
Moi buoc deu di qua CUNG mot ham `createOrder(...)` (xem muc 4) ⇒ cung gate/sizing/cap.

---

## 2. THU TU KIEM TRA EXIT TRONG 1 NEN (chinh xac theo if/else)

Ham: `SML.startUpdateOldOrderTrading(Long time, short symbolId, KlineObjectSimple ticker)` — `SML:946-1034`.
Dieu kien vao: `orderMulti != null && orderMulti.timeStart <= ticker.startTime` (`SML:948-949`).
`orderMulti` la object **CUM** (`symbol2OrderRunning[id]`), khong phai leg.

### Buoc 2.0 — cap nhat gia (luon chay truoc moi kiem tra)

`orderMulti.updatePriceByKlineSimple(ticker)` (`SML:950` → `OTIT:133-151`):
- `lastPrice = ticker.priceClose` (dung lam tham chieu trailing);
- `minPrice = min(minPrice, bar.low)` — **`minPrice` bi RESET len `lastPrice` moi lan arm/ratchet** (xem 2.4/2.5);
- `maeLow = min(maeLow, low)`, `maePeak = max(maePeak, high)` (do luong MAE/MFE, khong reset qua DCA);
- `timeUpdate = ticker.startTime`;
- neu `FUNDING_MARK_NOTIONAL` (profile: `SIM_FUNDING_MARK=true`) → `accrueFundingMark(startTime, close)` (`OTIT:135`).

### Thu tu kiem tra (dung nhu code)

```
(1) PRE-ARM HARD SL          SML:962-975      <-- hien TAT (PRE_ARM_SL=0)
(2) LOSER TIME-STOP          SML:988-994      <-- BAT (168h)
(3) CONDITIONAL EXIT         SML:1002-1011    <-- TAT (COND_EXIT_HOURS=0)
(4) ARM + TRAILING/CHOT SL   SML:1021-1031    <-- BAT (arm 7%)
```

**(1) PRE-ARM HARD SL — `SIM_PRE_ARM_SL` = 0f ⇒ TAT** (`Configs.java:437`; `PreArmSlUtils.enabledVal(v) = v < 0f`,
`PreArmSlUtils.java:21-23`). Khi bat, dieu kien: `priceSL == null && bar.low <= firstEntryPrice*(1+PRE_ARM_SL)`
(`SML:962-963`); dong ngay tai `PreArmSlUtils.exitPriceVal(...)` = gia khong bao gio tot hon muc stop
(xau hon neu nen dong duoi) (`PreArmSlUtils.java:38-45`), `status=STOP_LOSS_DONE`, `closeOrder`, `return`.
Cong `SL_ADAPT_HARDSL` (default off) doi `preArmSlEff` theo `selRank` (`SML:954-958`).

**(2) LOSER TIME-STOP — `SIM_LOSER_TIME_STOP_HOURS` = 168** (`profile:37` → `Configs.java:810`; default hardcode `0`).
- Chi ap cho cum **CHUA ARM**: `priceSL == null` — **KHONG ap cho cum da arm roi bi tut** (comment `Configs.java:420-423`).
- **Moc tinh: `anchor = clusterFirstLegTime > 0 ? clusterFirstLegTime : timeStart`** (`SML:989`) ⇒ tinh tu
  **LEG DAU cua cum**, khong phai leg vua nhoi (`clusterFirstLegTime` set trong `mergeOrder`, `SML:1155`).
- Dieu kien: `time - anchor > 168 * 3600000L` (`SML:990`).
- Gia chot: **`Math.min(ticker.priceOpen, ticker.priceClose)`** (`SML:992`) — **khong** dung `min(SL, open)`;
  khong look-ahead. `status = STOP_LOSS_DONE`, `closeOrder`, `return`.
- Cong `SL_ADAPT_TSTOP` (default off) doi gio theo `selRank` (`SML:979-983`).

**(3) CONDITIONAL EXIT — `SIM_COND_EXIT_HOURS` = 0 ⇒ TAT** (`Configs.java:429`).
Khi bat: chua arm + giu qua N gio + `(maePeak - priceEntry)/priceEntry < COND_EXIT_MIN_FAV` → dong tai
`min(open, close)` (`SML:1002-1011`).

**(4) ARM + TRAILING** (`SML:1013-1031`). Cong arm:

```java
float armRate = Configs.RATE_PROFIT_STOP_MARKET;            // = 0.07 (profile:35)
if (TradeUtils.peakPrice(ticker) >= orderMulti.priceEntry * (1 + armRate)
        || orderMulti.priceSL != null) { ... }              // SML:1021-1022
```

**So voi gia nao?** `TradeUtils.peakPrice(ticker) = Configs.TS_PEAK_CLOSE ? ticker.priceClose : ticker.maxPrice`
(`TradeUtils.java:30-32`). `TS_PEAK_MODE` khong khai trong profile ⇒ **`high` ⇒ so voi HIGH cua nen 1m hien tai**
(`Configs.java:496-498`). So sanh voi **`priceEntry` = gia vao TRUNG BINH cua cum** (khong phai leg dau).

Trong nhanh nay:

- `predReturn15M = getPredReturn15MForTradingStop(time)` — `predictionMap.get(time).predReturn15M`,
  `predict == null → 0f` (`SML:1037-1044`). Luu y: tham so nay **khong con tac dung** (muc 8 #6).
- `orderMulti.updateStatusNew(predReturn15M, ticker)` (`SML:1024` → `OTIT:185-242`).
- Sau do: neu `status ∈ {TAKE_PROFIT_DONE, STOP_LOSS_DONE, STOP_MARKET_DONE}` → **`closeOrder`** (`SML:1026-1028`);
  nguoc lai → **`orderMulti.updateTPSL(predReturn15M, ticker)`** (`SML:1030` → `OTIT:246-270`).

#### 2.4 `updateStatusNew` — dat SL LAN DAU (khi `priceSL == null`) — `OTIT:186-208`

```java
Float rateLoss = calRateLossMax(TradeUtils.peakPrice(ticker));            // OTIT:189  (peak = HIGH nen hien tai)
Float rateMin2MoveSl = TradeUtils.calRateMinWithPredReturn15MForTradingStop(predReturn15M); // OTIT:190
if (rateLoss > rateMin2MoveSl) {                                          // OTIT:191  (strict >)
    Float rateStop = trailRate(rateLoss);                                 // OTIT:192
    Float priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateStop); // OTIT:193
    minPrice = lastPrice;                                                 // OTIT:194  << RESET low-tracking
    this.priceSL = priceSLNew;                                            // OTIT:195
    if (Configs.BLOCK_INTRABAR_LOOKAHEAD) return;                         // OTIT:197  << KHONG khop ngay trong nen dat SL
    if (lastPrice <= priceSLNew) { ... }                                  // OTIT:205-207 (nhanh CU, chi khi guard tat)
}
```

`rateMin2MoveSl` = **hang so arm**, khong con phu thuoc `predReturn15M`:
`calRateMinWithPredReturn15MForTradingStop` tra `LiveProfileC3.armRate(Configs.RATE_PROFIT_STOP_MARKET)`
(`TradeUtils.java:107-113`) ⇒ **0.07** (profile:35), tru khi `LIVE_PROFILE=c3_shadow` (chi o duong LIVE).

#### 2.5 `trailRate` — cong thuc gap (TRAILING) — `OTIT:372-392` + `TradeUtils.java:52-62`

```java
float gap  = Math.min(maxProfitRate * Configs.TS_GIVEBACK_RATIO, maxGap);
float rate = maxProfitRate - gap;
rate = Math.round(rate / 0.005f) * 0.005f;      // lam tron buoc 0.5%
```

- `Configs.TS_GIVEBACK_RATIO` = **0.5** (`profile:40` → `Configs.java:173-175`).
- `maxGap` chon theo **`pNoPump` cua chinh coin** (`TradeUtils.java:40-45`, `OTIT:390`):
  ```java
  Float pnp = (this.symbolPred != null) ? this.symbolPred : 1f;   // OTIT:390 — null => coi nhu YEU
  float maxGap = (pNoPump != null && pNoPump > TS_PNOPUMP_WEAK_THR) ? TS_MAX_GAP_WEAK : TS_MAX_GAP;
  ```
  | Truong hop | `maxGap` | Nguon |
  |---|---|---|
  | `pNoPump > 0.29` (kho pump → **YEU**) | **`TS_MAX_GAP_WEAK = 0.03`** (3%) | `Configs.java:141,443` |
  | `pNoPump <= 0.29` (de chay → **MANH**) | **`TS_MAX_GAP = 0.08`** (8%) | `Configs.java:140` |
  | `pNoPump == null` (leg BIG_DOWN/DCA, chua co selector) | **0.03** (vi fallback `1f > 0.29`) | `OTIT:390` |

  ⇒ **Nguong phan biet = `TS_PNOPUMP_WEAK_THR` = 0.29** (default, `Configs.java:443-444`; override `SIM_TS_PNOPUMP_WEAK_THR`, khong khai trong profile).
  ⇒ `pNoPump` = **chinh `symbolPred` cua cum** (score S1, muc 0.4), duoc `mergeOrder` chep sang object cum
  nho `SIM_FIX_B1` (`SML:1163-1165` + `clusterSymbolPred` `SML:1108-1115`).
  Vi du: arm o +7% ⇒ SL +3.5%; +10% ⇒ SL +7% (yeu) hoac +5% (manh) — khop comment `OTIT:368-371`.
- Hai nhanh khac **dang TAT**: `TS_LADDER_ON=false` (`Configs.java:476`) va `TS_CAP_STRONG_RANK=0` (`Configs.java:456`).

#### 2.6 `updateTPSL` — RATCHET SL (cac nen sau) — `OTIT:246-270`

```java
if (priceSL != null) {
    Float rateLoss = calRateLossMax(TradeUtils.peakPrice(ticker));      // OTIT:251 (lai HIGH nen hien tai)
    Float rateMin2MoveSl = calRateMinWithPredReturn15MForTradingStop(rateChangeMax90M);  // = 0.07
    if (rateLoss >= rateMin2MoveSl) {                                   // OTIT:256 (>=)
        Float rateSL = trailRate(rateLoss);                             // OTIT:258
        Float priceSLNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, -rateSL);  // OTIT:260
        float priceSLChange = priceSLNew - priceSL;
        if (priceSLChange > 0 && priceSLNew > priceEntry) {             // OTIT:262-263
            priceSL = priceSLNew;                                       // OTIT:265
            minPrice = lastPrice;                                       // OTIT:266  << RESET low-tracking
        }
    }
}
```

**GUARD "SL LUON > ENTRY"**: chi ton tai tuong minh o day — `priceSLNew > priceEntry` (`OTIT:263`).
Nhanh dat SL lan dau (2.4) **khong co check nay**; bat bien chi duoc bao dam gian tiep
(`gap <= 0.5*maxProfit` ⇒ `rate > 0` ⇒ `priceSLNew > priceEntry`) — xem muc 8 #7.

#### 2.7 Khop SL — nen sau (nhanh `else`) — `OTIT:210-241`

```java
if (minPrice <= priceSL) {                                  // OTIT:212
    status = (priceSL > priceEntry) ? STOP_MARKET_DONE : STOP_LOSS_DONE;   // OTIT:213-216
    priceTP = Math.min(priceSL, ticker.priceOpen);          // OTIT:240  << TASK-118 clamp ve bar.open
}
```

- **Gia khop lenh thoat = `min(priceSL, bar.open)` MAC DINH** (`OTIT:240`), co log rieng khi
  `open < priceSL` (gap-down: `[EXIT-CLAMP-118]`, `OTIT:222-238`). Khong con `min(priceSL, maxPrice)`.
- **`BLOCK_INTRABAR_LOOKAHEAD = true` MAC DINH** (`Configs.java:122`) ⇒ nen vua DAT SL **khong** duoc khop
  trong chinh nen do (`OTIT:197-200`); viec khop lui lai sang nen sau qua nhanh `else`.
  Nhanh `if (lastPrice <= priceSLNew) { TAKE_PROFIT_DONE; priceTP = min(priceSL, open); }` (`OTIT:205-207`)
  la **hanh vi CU (look-ahead)** — chi chay khi tat guard.
- `minPrice` tai day = `min(close cua nen ratchet truoc, low cac nen sau)` — **khong** tinh `low` cua chinh
  nen dat SL (vi bi reset o `OTIT:194/266`).

#### 2.8 `closeOrder` — dong cum — `SML:1046-1090`

1. `orderMulti.computeFundingOnClose()` — tinh **1 luot cho ca cum** (`OTIT:301-334`); voi mark-mode
   (`FUNDING_MARK_NOTIONAL=true`, profile) thi chot `fundingAccrued` (`OTIT:336-364`).
2. Chep `status/priceTP/minPrice/maeLow/maePeak/lastPrice/timeUpdate` xuong TUNG leg; **toan bo funding cua cum
   gan vao DUY NHAT leg dau** (`fundingAssigned`, `SML:1065-1068`) de `Σ calTp` khong cong trung.
3. `putOrderDone(order)` + `BudgetManagerSimple.updatePnl(order)` cho tung leg (`SML:1070-1071`).
4. Xoa cum khoi mang: `symbol2OrdersEntry[id]=null`, `symbol2OrderRunning[id]=null`, `removeActiveRunningId(id)`,
   `marginRunning -= orderMulti.calMargin()` (`SML:1075-1080`).

#### 2.9 Delist / het ticker

`updateSymbolDeListed(symbolId, time)` — goi **moi gio** khi `!isTickerAvailable(ticker)` (`SML:466-473`):
neu `order.timeUpdate < time - 2 * TIME_DAY` → `status = STOP_LOSS_DONE`, **`priceTP = order.lastPrice`**
(`SML:879-888`) — **khong** ap clamp `min(SL, open)`.
Luu y: `Utils.isTickerAvailable` van coi bar `low == high` la "co ticker" neu `totalUsdt != 0` (`Utils.java:457-463`).

---

## 3. BUOC DCA (nhoi lenh)

### 3.1 Dieu kien nhoi — `DcaUtils.shouldDcaGrid` (`DcaUtils.java:32-45`)

```java
if (legCount < 1 || legCount > Configs.dcaGridLegs()) return false;   // het bac -> khong nhoi
float level = Configs.dcaGridLevel(legCount - 1);
if (level >= 0f) return false;
float drop = lastPrice / firstEntryPrice - 1f;                        // am khi lo
return drop <= level;
```

- Goi tu `DcaProcessor.getDCA` khi `DCA_GRID_ENABLED=true` (`DcaProcessor.java:38-40`); profile bat (`profile:50`).
- **Nguong %: so voi `firstEntryPrice` = gia vao LEG DAU cua cum** (bat bien qua DCA), khong phai gia vao trung binh.
- **Gia so sanh: `lastPrice` = close cua cum** (`SML:1145` set khi merge, `OTIT:134` cap nhat moi nen) ⇒ **theo CLOSE nen 1m**, khong phai low.
- Moc lo: `Configs.DCA_GRID_LEVELS` = **`-0.50, -0.75, -0.90`** (default, profile khong khai — `Configs.java:187-188`):
  leg 2 khi `drop <= -50%`, leg 3 khi `<= -75%`, leg 4 khi `<= -90%` (**tich luy tu leg dau**, khong phai tu leg truoc).
- **Toi da bao nhieu leg**: `dcaGridLegs() = DCA_GRID_LEVELS.length = 3` bac DCA (`Configs.java:231-233`)
  ⇒ **toi da 4 leg/cum** (1 leg dau + 3 DCA). `legCount` = so leg da khop, set trong `mergeOrder`
  (`SML:1158` = `gridLegCount(orders)`; `gridLegCount` = `orders.size()` khi `DCA_SIGNAL_GATE=false`, `SML:723-731`).
- Hai call-site/tick: `SML:358` (nhanh co `levelChange`) va `SML:390` (nhanh `isDcaAlt` → truyen `levelChange=null`).
  Khi `DCA_GRID_ENABLED=true`, tham so `levelChange` **khong duoc dung** trong filter (`DcaProcessor.java:38-44`).
- Khong co tran so leg theo tick: **moi cum dang chay cham moc** deu duoc nhoi (khong bi gioi han boi `NUMBER_ENTRY_EACH_SIGNAL`);
  cac cong chan la budget/`U_MAX`, `CONC_CAP_PERCOIN`, tier, `isTickerAvailable`.
- Cum `TIER_3_SHITCOIN` bi **chan han leg DCA** (`SML:1308-1312`) nhung leg DAU van duoc mo.

### 3.2 Cong thuc sizing — xac nhan bang code

Duong di size trong `createOrder` (`SML:1321-1391`):

```java
balanceBasic = Configs.FIX_B3 ? BudgetManagerSimple.equityNow() : balanceBasic;  // SML:1321-1323
budget = BudgetManagerSimple.getBudget();                                        // SML:1324  (700 — THAM SO CHET, muc 8 #1)
budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);// SML:1326
if (budget == null) return;                                                      // SML:1328-1330
budget *= tierMultiplier;                                                        // SML:1333
budget *= DcaUtils.gridLegWeightRatio(legIdx);                                   // SML:1371  (legIdx = gridLegCount(cur) hoac 0)
quantity = Utils.calQuantityTest(budget, leverage=1, entry=close, symbolStr);    // SML:1389
```

`TradeUtils.managerBudget` (`TradeUtils.java:126-140`):

```java
float u = marginRunning / balanceBasic;
if (u >= Configs.U_MAX) return null;                       // U_MAX = 0.60
float throttle = clamp(1f - u / Configs.U_MAX, 0f, 1f);
float ladder = Configs.dcaGridTotalWeight();               // sum(weights) = 4 voi 1,1,1,1  (Configs.java:296-299)
return balanceBasic * Configs.F_BASE * throttle / ladder;   // F_BASE = 0.03
```

`DcaUtils.gridLegWeightRatio(legIdx)` (`DcaUtils.java:47-63`):

```java
float w = Configs.dcaGridWeight(legIdx);
...
if (Configs.FIX_B2) return w * Configs.DCA_GRID_SCALE;      // DcaUtils.java:62  (KEEPLEG0: 1 * 6.0 = 6.0)
return (w / total) * Configs.DCA_GRID_SCALE;               // DcaUtils.java:63  (duong CU, co FIX_B2=false)
```

⇒ **Cong thuc hieu dung (giong de bai, xac nhan bang code):**

```
margin(leg i) ≈ equity × F_BASE × throttle × tierMult × w[i] × DCA_GRID_SCALE / Σw      (i = legIdx)
             = equity × 0.03  × throttle × 1.0      × 1   × 6.0             / 4        (KEEPLEG0)
             = 0.045 × equity × throttle
```

`w[i] * SCALE = 6.0` o **moi bac** (vi `w = 1,1,1,1` va `DCA_GRID_SCALE=6.0`, `profile:43,51`) ⇒ **cung mot size
cho ca 4 leg**; tong khi cham day = `4 × 4.5% = 18% equity` (throttle=1).
Kiem chung doc lap: voi ladder cu `1,1,3,8` + `SCALE=19.5` → tong = `0.03×19.5/13×(1+1+3+8) = 58.5%`
— **khop dung con so "tran 58.5%"** trong `deploy/shadow_c3/env.sh:8`. Cong thuc doc dung.

### 3.3 Vai tro tung tham so trong sizing

| Tham so | Gia tri KEEPLEG0 | Vai tro | Code |
|---|---|---|---|
| `F_BASE` | 0.03 | % equity moi leg goc | `Configs.java:155` (override `SIM_F_BASE`, khong khai) |
| `throttle` | `clamp(1 - u/0.60)` | giam size lien tuc khi margin/equity tien tran | `TradeUtils.java:135-137` |
| `U_MAX` | 0.60 | `u >= U_MAX` → **chan han lenh moi** (`return null`) | `Configs.java:156`; `TradeUtils.java:133` |
| `TIER_FLAT` | 1 | bo he so tier (1.2/1.0/0.5 → **1.00**) | `Configs.java:578`; `CoinRankManager.java:117` |
| `w[i]` | 1,1,1,1 | ti trong tung leg | `profile:51` → `Configs.java:189-190` |
| `DCA_GRID_SCALE` | **6.0** | nhan CA THANG (bu phan du tru hiem) | `profile:43` → `Configs.java:266-267` |
| `Σw` | 4 | chia trong `managerBudget` (`ladder`) | `Configs.java:296-299` |
| `FIX_B2` | true | bo lan chia `/Σw` thu 2 (truoc day he so danh 169 thay vi 13) | `DcaUtils.java:56-63`; `Configs.java:590` |
| `FIX_B3` | true | goc sizing = `equityNow()` thay `capitalStart()=35000` | `SML:1321-1323`; `BudgetManagerSimple.java:178-182` |
| `LEVERAGE_ORDER` | 1 | `quantity = budget*lev/price`; `margin = qty*entry/lev` | `Configs.java:102`; `OTIT:181-183` |
| `calQuantityTest` | — | lam tron xuong theo `stepSize` cua symbol | `Utils.java:311-326` |

`equityNow() = balanceCurrent (= capital + realized profit) + unProfit`, lam moi **moi gio / nua dem**
(`BudgetManagerSimple.java:178-182`; `SML:457-476`) ⇒ goc sizing **tre toi da 1 gio** (causal, khong look-ahead).

`USDT` khong dung: `getBudget()` tra `BUDGET_PER_ORDER = balanceBasic / number_order_budget = 35000/50 = 700`
(`BudgetManagerSimple.java:155,184-187`; `number_order_budget` `Configs.java:149-153`) **nhung bi `managerBudget` bo qua**.

---

## 4. DUONG VAO LENH (entry)

### 4.1 Chon ung vien

**(a) Nhom selector (chinh) — `SML:407-450`:**

1. `symbol2Pred = time2SymbolPred.get(time)` (mang `long[]` da sort TANG theo score, `preprocessFundingData` `SML:1551-1566`).
2. `selectCands(symbol2Pred)` (`SML:701-720`) voi `SELECTOR_RANK_TOPK=8` (`profile:9`)
   → **lay 8 phan tu DAU** cua mang (score nho nhat = `P(win)` cao nhat) ⇒ **rank 1 = `pNoPump` thap nhat cua tick**.
   Nhanh `TOPK<=0` (cutoff tuyet doi theo `PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX`) **khong chay**.
3. Vong `for` theo thu tu `chosenCands`: `selRank` tang dan 1..8 (`SML:426-428`).
4. `if (!isSymbolRunning(targetId))` (`SML:433`; `isSymbolRunning` duyet `activeRunningIds`, `SML:760-765`)
   → **moi symbol toi da 1 cum**, coin dang giu bi loai (tru nhanh DCA-SIGNAL, default off).
5. `createOrderBUY(targetId, ticker, PREDICT_SYMBOL_TRADE, marketData, symbolPred, selRank)` (`SML:436`).
6. `SELECTOR_ONLY_ENTRY=0` (`profile:10`) — y nghia: **`0` = KHONG tat** ⇒ nhom market-signal/BIG_DOWN
   **van chay** (`SML:365`: `if (!Configs.SELECTOR_ONLY_ENTRY) { ... }`). Dat `1` se bo han nhom (a) o muc 1 bang 8
   — tuc bo CA leg BIG_DOWN, khong chi selector.

**(b) Nhom market-signal/BIG_DOWN — `SML:330-372`:** `numberOrder = NUMBER_ENTRY_EACH_SIGNAL = 2` (`Configs.java:106`);
`getTopSymbolArray(2, symbol2Ticker, symbolLocked, predict2Symbol)` (`MBDetector.java:123-147`) lay 2 symbol
score nho nhat co ticker, bo symbol dang chay. Nhanh `numberOrder/2` cho `SMALL_*` la **code chet** (muc 8 #2).
Neu `BdSelection.ACTIVE` (default off) thi doi cach chon (`SML:346-350`).

**(c) Nhom DCA — `SML:374-381` + `SML:388-405`:** xem muc 3.

### 4.2 Gate — `createOrder` (`SML:1240-1272`)

```java
AiPredictionData predict = predictionMap.get(ticker.startTime);   // SML:1249
if (predict == null) return;                                      // SML:1249-1252  (parity LIVE, khong vao lenh "mu")
if (!levelChange.equals(BIG_DOWN)) {                              // SML:1256  << BIG_DOWN BO QUA GATE
    FilterResult fr = aiRejectFilter.entryGate(predict, symbolPred,
            levelChange == PREDICT_SYMBOL_TRADE);                  // SML:1257-1258
    if (fr.decision == REJECT) return;                             // SML:1265-1267
}
```

`AIRejectFilter.entryGate` (`ai_ml/onnx/entry/AIRejectFilter.java:61-64`): `sp = predictSymbolTrade ? symbolPred : null`
⇒ **chi leg selector (`PREDICT_SYMBOL_TRADE`) moi co nguong DONG**; leg BIG_DOWN / DCA_LEVEL1 (va cac leg `symbolPred=null`)
dung nguong CO SO.

`EntryGate.threshold` (`EntryGate.java:92-99`) — **cong thuc hieu dung**:

```
dyn_thr(score) = SIM_MIN_MOMENTUM_15M × max(DYN_MIN, (score / 0.15) × DYN_MULT) × GATE_DYN_SCALE
PASS  <=>  !(predReturn15M < dyn_thr)
```

| Hang so | Gia tri | Nguon |
|---|---|---|
| `SIM_MIN_MOMENTUM_15M` | **0.008** | `profile:32` → `Configs.java:759` (default hardcode 0.02284, `Configs.java:407`) |
| `DYN_MIN` (can duoi) | 0.26787 | **hang so trong code** `EntryGate.java:43` |
| `SCORE_BASE` | 0.15 | `EntryGate.java:45` |
| `DYN_MULT` | 1.28760 | `EntryGate.java:47` |
| `SIM_GATE_DYN_SCALE` | **1.70** | `profile:73` → `Configs.java:763-766`; nhan VAO KET QUA (`EntryGate.java:97`) |

- **`SIM_GATE_DYN_SCALE=1.70` "nhan vao dau"?** Nhan vao **ket qua cuoi cung** cua `dyn_thr` (he so ngoai cung),
  va **chi ap cho nhanh `symbolPred != null`** (`EntryGate.java:88-97`).
- Gia tri nguong thuc te: `score=0` → `0.008 × 0.26787 × 1.70` = **0.364%**; `score=0.3212` →
  `0.008 × (0.3212/0.15 × 1.2876) × 1.70` = **3.75%** (`predReturn15M` cung don vi phan tram 15m).
- Khong co can tren: nhanh `Math.min(..., AI_DYNAMIC_MAX)` da bi xoa khoi `EntryGate` (comment `profile:26`).
- Cong `GATE_REGIME_ADAPTIVE` (default off, `EntryGate.java:55`) thay `GATE_DYN_SCALE` bang `CURRENT_REGIME_SCALE`
  (`SML:224` dat moi tick).

Sau gate: `PumpDumpFilter.shouldSkip(...)` (default OFF, `SML:1271`); `GATE_COUNT_ONLY` (default off → khong dung),
dem `entryBigDown/entryPredictSymbol/...` (`SML:1296-1300`).

### 4.3 Sizing → khoa symbol → budget → `CONC_CAP_PERCOIN` → gia vao lenh

| # | Buoc | Code | Ghi chu |
|---|---|---|---|
| 1 | `entry = ticker.priceClose`, `leverage = LEVERAGE_ORDER = 1` | `SML:1303-1304` | **gia vao lenh = CLOSE cua nen 1m** (market order), khong slip gia |
| 2 | Tier check: `TIER_3_SHITCOIN` + `DCA_LEVEL1` → bo | `SML:1307-1312` | leg dau cua shitcoin van vao |
| 3 | `balanceBasic` (equityNow khi FIX_B3) + `managerBudget` (U_MAX/throttle) | `SML:1321-1331` | `null` → bo lenh |
| 4 | `× tierMultiplier` (TIER_FLAT=1 → 1.0) | `SML:1333` | `CoinRankManager.java:117` |
| 5 | `× gridLegWeightRatio(legIdx)` (legIdx=0 cho leg dau) | `SML:1360-1371` | `ratio<=0` → het bac, bo |
| 6 | `quantity = calQuantityTest(...)` (floor stepSize) | `SML:1389` | margin that `<=` budget |
| 7 | `CONC_CAP_AGG_DCA_ENABLED` (default **false**) → bo qua | `SML:1398-1411` | cap 0.45 tai san DCA-grid |
| 8 | **`CONC_CAP_PERCOIN_ENABLED` (profile true, pct 0.15)** → ap cho **MOI leg** (ke ca leg dau): bo neu `(coinNow + legNew)/equity > 0.15` | `SML:1414-1433`; `concPerCoinMargin` `SML:819-830` | `profile:79-80`; `legNew = qty*entry/lev` |
| 9 | `CONC_CAP_BD_RATE_ENABLED` (default false) | `SML:1430-1436` | gioi han 75 leg BIG_DOWN/gio neu bat (`CONC_CAP_BD_PER_HOUR`, `Configs.java:635-636`) |
| 10 | Tao order tai `entry`, gan `firstEntryPrice`, `symbolPred`, `selRank`, `dcaSignalLeg` | `SML:1440-1470` | `firstEntryPrice` = gia vao leg dau (bat bien) |
| 11 | `mergeOrder(...)` → object CUM (avg entry, `clusterFirstLegTime`, `legCount`, carry `symbolPred`) | `SML:1482`; `SML:1117-1185` | |
| 12 | `addActiveRunningId`, `updateMaxOrderRunning`, `marginRunning += order.calMargin()` | `SML:1483-1489` | `calMargin = qty*entry/lev` (`OTIT:181-183`) |

**Phi / slip / funding** (`OTIT.calTp`, `OTIT:274-292`):
- phi: `- quantity × priceEntry × RATE_FEE`, `RATE_FEE = 0.002` (`Configs.java:103`) — tru **1 lan** cho ca vong
  (comment "da sua thanh 2 chan");
- slippage: `- quantity × priceEntry × SLIPPAGE_RATE × 2f`, `SLIPPAGE_RATE = 0.003`, `APPLY_SLIPPAGE = true`
  (`OTIT:288-291`; `Configs.java:117,125`) ⇒ **0.6%**;
- funding: `- calFundingFee()` (`OTIT:292`), bat qua `SIM_APPLY_FUNDING=true` (`profile:54` → `Configs.java:818`;
  default hardcode `APPLY_FUNDING_FEE = false`, `Configs.java:132`);
- ⇒ chi phi khu vong ≈ **0.8% notional** (+ funding), ap dung tai thoi diem **dong lenh** (khong tru luc mo).

---

## 5. CO CHE BAT/TAT HIEN TAI

### 5.1 `SIM_BREAKER_MODE=OFF` (`profile:58`)

- Trong engine **KHONG TON TAI co che breaker nao** (grep `BREAKER_MODE` trong `SML` = 0 ket qua).
  Key chi duoc **validate**: khac `OFF` → `System.exit(2)` (`Configs.java:868-876`).
- Bo limiter mat do (`BURST_BASE=40`, `DENSITY_SUSTAIN=10`, `CIRCUIT_DANGER_RATIO=0.7`,
  `MBDetector.java:196-215`) **chi chay o duong LIVE**, khong duoc goi trong simulator.

### 5.2 BIG_DOWN co chay khong? — **CO, va la nhanh duy nhat**

- `MBDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, rateDown15MAvg)` (`MBDetector.java:174-183`):
  ```java
  if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) return MarketLevelChange.BIG_DOWN;   // MS_DOWN_BIG_AVG = -0.03157
  return null;                                                                     // (BIG_UP/SMALL_* da xoa)
  ```
  (`Configs.java:409`; override `SIM_MS_DOWN_BIG_AVG`, khong khai trong profile).
- Khi co tin hieu: mo **2 leg** (`NUMBER_ENTRY_EACH_SIGNAL=2`) cho 2 coin score nho nhat, **bo qua gate AI**
  (`SML:1256`), `symbolPred = null` ⇒ **(a) trailing cap = WEAK 0.03** va **(b) leg BIG_DOWN an size bang
  leg thuong** (khong co `VolTargetSizing`/`BdSizeAdapt`/`PacingSizing` — deu default off).
- Nhanh `DCA_LEVEL1` thu hai (`isDcaAlt`, `MBDetector.java:188-192`) chay **doc lap** voi BIG_DOWN,
  dung `MS_DOWN_BIG_AVG_DCA = -0.03157` (`Configs.java:413`).

### 5.3 Ba co sua bug `SIM_FIX_B1/B2/B3 = true` (`profile:66-68`)

| Co | Sua GI (1 dong) | Code |
|---|---|---|
| **B1** | `mergeOrder` **chep `symbolPred`** tu leg dau co pred sang object CUM: truoc day field null ⇒ `trailRate` roi vao fallback `1f > 0.29` ⇒ **100% lenh di nhanh WEAK cap 0.03**, nhanh STRONG (cap 0.08) chua bao gio chay | `SML:1163-1165` (`orderResult.symbolPred = clusterSymbolPred(...)`), helper `SML:1108-1115` |
| **B2** | `gridLegWeightRatio` tra `w * SCALE` thay vi `(w / Σw) * SCALE`: truoc day `managerBudget` da chia `/Σw` mot lan, chia them ⇒ margin `~ w[i]/Σw²` (ladder 1,1,3,8 → he so **169** thay vi 13); bug vo hinh voi ladder `1,0,0,0` (Σw=1) | `DcaUtils.java:62` vs `:63`, comment `DcaUtils.java:56-61`; `Configs.java:590` |
| **B3** | Goc sizing = **equity hien tai** `equityNow()` (compounded) thay hang so `capitalStart()=35000`: ap cho CA `budget = equity*F_BASE*throttle/ladder` VA `u = marginRunning/equity` (tran `U_MAX` cung doc tren equity — nhat quan) | `SML:1321-1323`; `BudgetManagerSimple.java:178-182`; `Configs.java:591` |

Ca 3 co default **true** (`Configs.java:589-591`: `!"false".equalsIgnoreCase(Cfg.getOr("SIM_FIX_Bn","true"))`).

### 5.4 Cac co khac dang ON/OFF (baseline KEEPLEG0)

| Co | Trang thai | Gia tri/nguon |
|---|---|---|
| `BLOCK_INTRABAR_LOOKAHEAD` | **ON** | `Configs.java:122` |
| `APPLY_SLIPPAGE` | ON | `Configs.java:125` |
| `APPLY_FUNDING_FEE` (qua `SIM_APPLY_FUNDING`) | ON | `profile:54` → `Configs.java:818` |
| `FUNDING_MARK_NOTIONAL` (qua `SIM_FUNDING_MARK`) | ON | `profile:55` → `Configs.java:819` |
| `PRE_ARM_SL` | OFF (0) | `Configs.java:437` |
| `COND_EXIT_HOURS` | OFF (0) | `Configs.java:429` |
| `TS_LADDER` | OFF | `Configs.java:476` |
| `TS_CAP_STRONG_RANK` | 0 (OFF) | `Configs.java:456-457` |
| `TS_PEAK_MODE` | `high` | `Configs.java:496-498` |
| `DCA_SIGNAL_GATE` | OFF | `Configs.java:601-602` |
| `DCA_ROUND_CAP_ENABLED` | OFF | `Configs.java:199` |
| `CONC_CAP_PERCOIN_*` | **ON** (0.15) | `profile:79-80` → `Configs.java:646-651` |
| `CONC_CAP_AGG_DCA_*` / `CONC_CAP_BD_RATE_*` | OFF | `Configs.java:625-636` |
| `GATE_REGIME_ADAPTIVE` | OFF | `EntryGate.java:55` (key `SIM_GATE_REGIME_ADAPTIVE`) |
| `VolTargetSizing` / `PacingSizing` | OFF | `Configs.java:673,683` (`OFF`) → `VolTargetSizing.java:54`, `PacingSizing.java:60` |
| `BdSizeAdapt` / `BdSelection` | OFF | `Configs.java:661` / `:693` (`off`) → `BdSizeAdapt.java:35`, `BdSelection.java:39` |
| `PumpDumpFilter` (`SIM_FILTER_D3D4`) | OFF | `Configs.java:406` (null) → `PumpDumpFilter.java:92`; call `SML:1271` |
| `TickWeakBlock` (`SIM_TICK_BLOCK_IND`) | OFF (rong) | `TickWeakBlock.java:47-48`; call `SML:324` |
| `TickDecisionLog` | OFF | call sites `SML:175-177,480-485` |
| `WRITE_SIM_STORAGE` | OFF (default) | `SML:590`; `Configs.java` (TASK-112) |

---

## 6. BANG TOM TAT THAM SO — BASELINE KEEPLEG0 (`file:line`)

| Tham so | Gia tri hieu dung | Khai bao (nguon) | Doc tai |
|---|---|---|---|
| `SELECTOR_RANK_TOPK` | 8 | `profiles/t170_flat_keepleg0.properties:9` | `Configs.java:362-363`; `SML:701-706` |
| `SELECTOR_ONLY_ENTRY` | 0 (nhom market-signal VAN chay) | `...:10` | `SML:365` |
| `WFO_FUNDING_PRED_DIR` | `/home/ubuntu/predwf_map_s1a2_x1` | `...:21` | `WfoDataset.java:74-96` |
| `SIM_MIN_MOMENTUM_15M` | 0.008 | `...:32` | `Configs.java:759` → `EntryGate.java:95` |
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 (nguong ARM) | `...:35` | `Configs.java:806` → `SML:1016`,`OTIT:190` |
| `SIM_TS_GIVEBACK` | 1 (**chi validate**, khong phai knob) | `...:36` | `Configs.java:864-869` |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | `...:37` | `Configs.java:810` → `SML:979,990` |
| `TS_GIVEBACK_RATIO` | 0.5 | `...:40` | `Configs.java:173-175` → `TradeUtils.java:53` |
| `DCA_GRID_SCALE` | 6.0 | `...:43` | `Configs.java:266-267` → `DcaUtils.java:62` |
| `TIER_FLAT` | 1 | `...:44` | `Configs.java:578` → `CoinRankManager.java:117` |
| `CAPITAL_START` | 35000 | `...:47` | `Configs.java:730-733` |
| `DCA_GRID_ENABLED` | true | `...:50` | `Configs.java:186` |
| `DCA_GRID_WEIGHTS` | 1,1,1,1 (Σw=4) | `...:51` | `Configs.java:189-190` |
| `SIM_APPLY_FUNDING` | true | `...:54` | `Configs.java:818` |
| `SIM_FUNDING_MARK` | true | `...:55` | `Configs.java:819` |
| `SIM_BREAKER_MODE` | OFF | `...:58` | `Configs.java:870-876` |
| `SIM_FIX_B1/B2/B3` | true/true/true | `...:66-68` | `Configs.java:589-591` |
| `SIM_GATE_DYN_SCALE` | 1.70 | `...:73` | `Configs.java:763-766` → `EntryGate.java:97` |
| `CONC_CAP_PERCOIN_ENABLED` | true | `...:79` | `Configs.java:646-648`; `SML:1414` |
| `CONC_CAP_PERCOIN_PCT` | 0.15 | `...:80` | `Configs.java:650-651`; `SML:1421-1422` |
| `F_BASE` | 0.03 | default (khong khai) | `Configs.java:155` (env `SIM_F_BASE` `Configs.java:803`) |
| `U_MAX` | 0.60 | default | `Configs.java:156` (env `SIM_U_MAX` `:804`) |
| `TS_MAX_GAP` / `TS_MAX_GAP_WEAK` | 0.08 / 0.03 | default | `Configs.java:140-141` (`:801-802`) |
| `TS_PNOPUMP_WEAK_THR` | 0.29 | default | `Configs.java:443-444` (`:798`) |
| `TS_PEAK_MODE` | high | default | `Configs.java:496-498` → `TradeUtils.java:30-32` |
| `BLOCK_INTRABAR_LOOKAHEAD` | true | default | `Configs.java:122` |
| `NUMBER_ENTRY_EACH_SIGNAL` | 2 | default | `Configs.java:106`; `SML:332` |
| `MS_DOWN_BIG_AVG` / `_DCA` | -0.03157 / -0.03157 | default | `Configs.java:409,413` (`:807,809`) |
| `DCA_GRID_LEVELS` | -0.50,-0.75,-0.90 | default | `Configs.java:187-188`; `DcaUtils.java:42` |
| `LEVERAGE_ORDER` | 1 | default | `Configs.java:102`; `SML:1304` |
| `RATE_FEE` / `SLIPPAGE_RATE` / `APPLY_SLIPPAGE` | 0.002 / 0.003 / true | default | `Configs.java:103,117,125`; `OTIT:277-291` |
| `number_order_budget` | 50 (→ `BUDGET_PER_ORDER=700`, **khong dung de tinh size**) | default | `Configs.java:149-153`; `BudgetManagerSimple.java:155` |
| `PRE_ARM_SL` / `COND_EXIT_HOURS` / `TS_CAP_STRONG_RANK` / `TS_LADDER` | 0 / 0 / 0 / OFF | default | `Configs.java:437,429,456,476` |
| `TICKER_SOURCE` | `aerospike` (repo) | `config.properties:21` | `Configs.java:70`; `SML:229-244` |
| `USE_SMART_CACHE` | false | `config.properties` (khong khai) | `Configs.java:76`; `SML:229-239` |

---

## 7. SO DO LUONG (text)

```
[NAP DU LIEU - 1 lan]  SML.initData():890
  WFO_DATA_DIR? --> market.bin / pred.bin / funding.bin (md5 + HoldoutSeal 2026-01-01)
       |  (else Aerospike)
       +--> time2MarketData, predictionMap, time2SymbolPred (selector S1, forward-fill 15m->1m)
  (moi ngay) --> ticker_<yyyyMMdd>.bin  hoac Aerospike 1M  --> time2Tickers[1440]
          |
          v
+---------------- VONG LAP: for NGAY (UTC) { for PHUT { -------------------+
|  (1) [EXIT] for moi vi the dang mo: startUpdateOldOrderTrading  SML:946 |
|        updatePriceByKlineSimple (close/high/low)                SML:950 |
|        (1) PRE-ARM SL      [TAT]                                SML:962 |
|        (2) LOSER 168h tu leg DAU, close=min(open,close)         SML:988 |
|        (3) COND EXIT       [TAT]                                SML:1002|
|        (4) ARM: HIGH >= avgEntry*(1+0.07)                       SML:1021|
|              -> updateStatusNew: gap=min(peak*0.5, maxGap)      OTIT:185|
|                 maxGap = 0.03 neu pNoPump>0.29 else 0.08        OTIT:390|
|                 dat priceSL; BLOCK_INTRABAR -> khong khop noi nen OTIT:197|
|              -> updateTPSL: ratchet neu priceSLNew>priceSL VA >entry OTIT:262|
|              -> khop: minPrice<=priceSL -> priceTP=min(priceSL,bar.open) OTIT:240|
|              -> closeOrder (funding 1 luot, day lenh vao allOrderDone)   |
|  (2) [DO maxDD] Σ qty*(bar.low - entry)                          SML:288|
|  (3) [TIN HIEU] levelChange = BIG_DOWN neu rateDownAvg < -0.03157 SML:330|
|  (4) [NHOM A] BIG_DOWN/market-signal: 2 coin score nho nhat      SML:343|
|              + NHOM B/C: DCA grid (drop <= -50/-75/-90% tu leg dau) SML:358|
|  (5) [NHOM C] SELECTOR: top-8 score nho nhat (rank1..8)          SML:407|
|              -- moi leg --> createOrder                        SML:1240|
|                 predict==null -> BO                            SML:1249|
|                 BIG_DOWN? -> BO QUA GATE                        SML:1256|
|                 entryGate: dyn_thr=0.008*max(0.26787,(sp/0.15)*1.2876)*1.70 |
|                 balanceBasic=equityNow (FIX_B3)                 SML:1321|
|                 u=marginRunning/equity >= 0.60? -> BO            TradeUtils:133|
|                 budget = eq*0.03*throttle/4 * 1(tier) * 6.0(grid ratio)   |
|                 quantity = floor(budget*1/close)                 SML:1389|
|                 (coinNow+legNew)/equity > 0.15? -> BO            SML:1422|
|                 ENTRY TAI PRICE = CLOSE nen 1m                   SML:1303|
|  (6) [CUOI TICK] nua dem -> updateBalance(true); moi gio -> delist(>2 ngay)  |
+-------------------------------------------------------------------------+
[KET THUC] cum con mo -> allOrderDone + funding; bao cao GATE/CLAMP/...   SML:537
```

---

## 8. ⭐ DIEM MAU THUAN / PHAT HIEN MOI (code vs tai lieu cu / gia dinh pho bien)

**#1 — `budget` trong chuoi size la THAM SO CHET; con so "700 USDT/lenh" khong co tac dung.**
`profiles/...:45` ghi *"BASE_BUDGET = CAPITAL_START / NUMBER_ORDER_BUDGET = 35000/50 = 700 USDT / lenh"*.
Nhung `TradeUtils.managerBudget(Float budget, ...)` (`TradeUtils.java:126-140`) **khong doc tham so `budget`** —
no tra `balanceBasic * F_BASE * throttle / ladder`. `SML:1324-1326` truyen `getBudget()` (=700) vao roi bi bo qua.
⇒ Doi `NUMBER_ORDER_BUDGET`/`CAPITAL_START` **khong doi size**. (`docs/experiment/T2B_FULLFLOW.md:31-33` cung da ghi
"THAM SO CHET" — tai lieu profile thi chua sua.)

**#2 — Hai nhanh `SMALL_UP` / `SMALL_DOWN_15M` trong vong lap chinh la CODE CHET.**
`SML:338-339`: `if (levelChange == SMALL_UP || SMALL_DOWN_15M) numberOrder = numberOrder / 2;`
nhung `getMarketStatus1M` (`MBDetector.java:174-183`) **chi tra `BIG_DOWN` hoac `null`** (BIG_UP/SMALL_* da xoa
2026-09-03, xem comment `MBDetector.java:177-178`). ⇒ Nhanh chia doi khong bao gio chay; `numberOrder` luon = 2.

**#3 — Comment GATE trong chinh profile dang SAI hai diem (so nguong + ten key da xoa).**
`profiles/...:25` ghi `dyn_thr = SIM_MIN_MOMENTUM_15M * max(SIM_AI_DYNAMIC_MIN, score/0.15*SIM_AI_DYNAMIC_MULTIPLIER)`
va `:27-28` ghi *"0.214 phan tram o san den 2.206 phan tram o score 0.3212"*.
- Hai key `SIM_AI_DYNAMIC_MIN` / `SIM_AI_DYNAMIC_MULTIPLIER` **DA BI XOA** (`Configs.java:792-796`); gia tri that la
  **hang so** `EntryGate.DYN_MIN=0.26787`, `DYN_MULT=1.28760` (`EntryGate.java:43-47`).
- **Thieu he so cua chinh profile nay**: `SIM_GATE_DYN_SCALE=1.70` (`profile:73`) nhan vao ket qua
  (`EntryGate.java:97`). Nguong THAT = san **0.364%** va dinh **3.75%** tai score 0.3212 — khong phai 0.214% / 2.206%.
  (Comment o khoi GATE_DYN_SCALE noi dung, nhung khoi GATE phia tren de nguoi doc hieu sai.)

**#4 — Gene HPO `AI_DYNAMIC_MIN` / `AI_DYNAMIC_MULTIPLIER` van duoc dang ky nhung KHONG con anh huong gate.**
`ai_ml/wfo/WFORunner.java:64-65`, `ai_ml/wfo/framework/tasks/StrategyWfoTask.java:71-72`,
`ai_ml/hpo/SensitivityTool.java:64-65` deu khai 2 gene nay; chung chi set field `Configs.AI_DYNAMIC_MIN/MULTIPLIER`
(`Configs.java:328-329`) — nhung **khong file nao trong duong gate doc 2 field do** (grep: ngoai `Configs` chi con
cac file dang ky gene + comment trong `EntryGate`). ⇒ HPO/WFO se bao 2 gene nay "vo nghia" (hoac ton eval vo ich).
Rieng `SIM_AI_DYNAMIC_MAX` **con song** nhung chi tac dong nhanh `SELECTOR_RANK_TOPK<=0` (`SML:708`), ma KEEPLEG0 co TOPK=8.

**#5 — `docs/experiment/T2B_FULLFLOW.md` mo ta cong thuc size cua BAN TRUOC FIX_B2, va so dong da lech.**
`docs/experiment/T2B_FULLFLOW.md:57-58` ghi `gridLegWeightRatio = (w[legIdx] / total) * DCA_GRID_SCALE`.
Code hien tai voi `FIX_B2=true` (default, `Configs.java:590`) tra **`w * DCA_GRID_SCALE`** (`DcaUtils.java:62`).
Ngoai ra tai lieu do trich `SimulatorMarketLevelTicker1MStopLoss.java` **dong 875-903**; trong code hien tai chuoi
size nam o **dong 1321-1389**.

**#6 — `predReturn15M` truyen vao arm/trailing la tham so KHONG CON TAC DUNG.**
`calRateMinWithPredReturn15MForTradingStop(predReturn15M)` bo qua tham so (FROZEN v1 2026-08-24) va tra
`RATE_PROFIT_STOP_MARKET` (`TradeUtils.java:107-113`); nguong dich SL cung khong dung no.
⇒ `getPredReturn15MForTradingStop` (`SML:1037-1044`) chi con vai tro "chay dung chu ky ham".

**#7 — Guard "SL luon > entry" KHONG duoc check o lan dat SL dau.**
Check tuong minh chi co o ratchet: `priceSLChange > 0 && priceSLNew > priceEntry` (`OTIT:262-263`).
Nhanh dat SL lan dau (`OTIT:191-196`) chi dua vao bat bien gian tiep: `gap <= maxProfit*0.5` ⇒ `rate >= maxProfit/2 > 0`
(`TradeUtils.java:53-54`) — dung **voi dieu kien arm hien tai (7%)**, nhung **khong** duoc bao ve bang code neu
`TS_MAX_GAP`/`RATE_PROFIT_STOP_MARKET` bi doi (vd arm 2% thi `rate >= 1%` van >0, nhung neu ai sua `trailFromCap`
hoac bat `TS_LADDER` thi bat bien nay phu thuoc `trailFromLadder`'s `cap = peak*0.9`, `TradeUtils.java:87-89`).

**#8 — "Dinh trailing" KHONG phai mot dinh tich luy; no la HIGH cua nen dang xet, va `minPrice` bi RESET moi lan ratchet.**
`OTIT:189` / `OTIT:251` tinh `rateLoss` tu `TradeUtils.peakPrice(ticker)` = **HIGH nen hien tai**, khong phai
`maePeak`/peak tich luy (khac `maePeak`, `OTIT:143-147`). Dinh chi duoc "nho" gian tiep nho `priceSL` chi di len.
Dong thoi `minPrice = lastPrice` (`OTIT:194`, `OTIT:266`) **xoa vung low cu** ⇒ SL khong the khop bang `low` cua
chinh nen dat/ratchet SL; khop SL dung `min(close cua nen truoc, low cac nen sau)` (`OTIT:212`, `OTIT:134-136`).
Khong tai lieu nao trong `docs/` mo ta chi tiet nay.

**#9 — Gia thoat cua 3 duong KHONG cung mot cong thuc.**
| Duong thoat | Gia chot | Code |
|---|---|---|
| SL trailing (nhanh chinh) | `min(priceSL, bar.open)` (clamp TASK-118) | `OTIT:240` |
| LOSER TIME-STOP 168h | `min(bar.open, bar.close)` | `SML:992` |
| COND EXIT | `min(bar.open, bar.close)` | `SML:1009` |
| PRE-ARM SL | `PreArmSlUtils.exitPriceVal` (khong tot hon muc stop) | `SML:966-967`; `PreArmSlUtils.java:38-45` |
| Delist (>2 ngay khong co ticker) | **`order.lastPrice`** (close cuoi cung) | `SML:884-886` |
⇒ Chung minh sau chi ap `min(priceSL,bar.open)` la **thieu**; va delist khong ap clamp nao.

**#10 — `SIM_TS_GIVEBACK=1` la co **marker**, khong phai tham so.**
Gia tri cua no **khong bao gio duoc doc**; chi co 1 static block `if (gb != null && !"1".equals(gb.trim())) exit(2)`
(`Configs.java:864-869`). ⇒ Sweep `SIM_TS_GIVEBACK` (vd `=0`) se **DUNG CHUONG TRINH**, khong "tat giveback".
Knob that la `TS_GIVEBACK_RATIO` (`profile:40`). Tuong tu `SIM_BREAKER_MODE` (`Configs.java:870-876`).

**#11 — Trong CUNG 1 tick, `createOrder` duoc goi theo 3 nhom (A/B/C) va **khong co tran theo tick**;
thu tu B truoc C co the an budget cua C.**
`SML:365-405` (A, B) chay TRUOC `SML:407-450` (C). Vi `managerBudget` chan khi `u >= U_MAX` va
`CONC_CAP_PERCOIN` chan theo equity, **thu tu nhom quyet dinh ai duoc vao truoc** (nhat la trong ngay BIG_DOWN
khi A mo 2 leg roi B nhoi toan bo cac cum dang lo). Khong co tai lieu nao ghi thu tu uu tien nay.

**#12 — `NUMBER_ENTRY_EACH_SIGNAL=2` chi ap cho nhom A; nhom B (DCA) khong bi gioi han so leg/tick.**
`SML:332` (halving `SMALL_*` la code chet — #2) va `SML:374-405` (moi cum cham moc deu duoc nhoi).
⇒ Kich thuoc "1 tin hieu = 2 lenh" trong `Configs.java:106` chi dung cho BIG_DOWN.

**#13 — Chieu thoi gian "ngay" la UTC nhung toan bo format la GMT+7.**
`SML:118` (`+7h` voi `sdfFile` GMT+7, `Utils.java:38-51`) ⇒ ngay chay = **00:00 UTC → 00:00 UTC**;
`time % TIME_DAY == 0` = nua dem UTC (`SML:457`). Log/ten file ticker lai GMT+7 (`Utils.java:170-174`;
`KaggleDataLoader.java:92`). Bat ky phan tich nao ghep log GMT+7 voi "ngay" deu lech 7 gio.

**#14 — Ten `time2SymbolPred` / "funding" la DI SAN: khoi nay la **S1 selector bins**, khong phai funding rate.**
`SML:902-934` (`time2SymbolPred`), `WfoDataset.java:47` `SET_FUNDING = "funding_selector_pred_1m_v2"`,
`WfoDataset.java:41` `F_FUNDING = "funding.bin"`, `preprocessFundingData` (`SML:1551-1566`).
Key cau hinh de pin no la `WFO_FUNDING_PRED_DIR`. Funding fee that la mot khoi KHAC (`FundingFeeManager`).
De nham lan khi doc code/log — nhat la `SIM_APPLY_FUNDING` (fee) vs `funding.bin` (selector).

**#15 — `DCA_GRID_WEIGHTS=1,1,1,1` (4 phan tu) di kem `DCA_GRID_LEVELS` chi 3 phan tu ⇒ `w[3]` chi dung cho leg cuoi,
va co che "het bac" chan o `legCount > dcaGridLegs()=3` (`Configs.java:250-256` = `dcaGridWeight`).**
`Configs.java:187-190,231-233`; `DcaUtils.java:41`. Khong sai, nhung de gay hieu nham rang ladder co 4 bac DCA
(thuc te la **3 bac DCA / 4 leg**).

**#16 — `CONC_CAP_PERCOIN` ap cho CA leg DAU tien va dung `equity` (khong phai notional), nen no khong chi la
"tran DCA".** `SML:1414-1433` — `concPerCoinMargin` cong MOI leg dang mo cua coin (`SML:819-830`).
Comment profile (`:76-78`) chi noi "tren KEEPLEG0 la NO-OP trong mau" — dung voi mau, nhung o kenh 1x/mat that
no se chan ca lenh mo moi khi coin da chiem >15% equity.

---

## 9. Muc KHONG doc duoc / gioi han cua lan doc nay

- **Khong chay sim** (rang buoc: box Oracle dang shadow LIVE) ⇒ moi ket luan la **doc code tinh**, khong co
  so do lai tu run. Cac con so suy ra tu cong thuc (vd 4.5%/leg, 18%/cum, nguong gate 0.364%-3.75%) chua duoc
  doi chieu bang 1 lan chay.
- **`ClientSingleton.normalizeQuantityTest`** (lam tron `quantity` theo `stepSize` cua symbol) va `getMinQuantity`
  nam ngoai pham vi da doc (`Utils.java:311-326` goi ra); anh huong cua no len size that chua duoc luong hoa o day.
- **`FundingFeeManager`** (nguon moc settle, cache) chua duoc doc chi tiet — chi xac nhan duoc diem goi va cong thuc.
- **`BdSelection` / `BdSizeAdapt` / `VolTargetSizing` / `PacingSizing` / `TickWeakBlock` / `PumpDumpFilter` /
  `RegimeSchedule` / `DcaProcessor.capByDrop`** chi duoc xac nhan la **default OFF** (nhanh khong chay o baseline),
  khong mo ta chi tiet logic ben trong.
- **Duong LIVE** (`DetectEntrySignal2TradeNormal`, `BinanceOrderTradingManager`, `LiveProfileC3`,
  `deploy/shadow_c3/env.sh`) chi duoc doi chieu o muc tham chieu (vd `armRate` 0.05/0.07), **khong phai doi tuong
  cua tai lieu nay**.
- **HPO/WFO wrapper** (`StrategyWfoTask`, `WFORunner`) chi duoc doc de xac nhan gene — khong xac minh bang chay.
