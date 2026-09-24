# RESULT_BOOKFIX — sua so giay LIVE ShadowBookC3 gop leg2+ cung coin

Ngay: 2026-09-13. Code: branch `module`. Oracle-only. KHONG cham 242, KHONG push, KHONG tune.
CHI sua so giay shadow (accounting). SIM / gate / entry / exit / legacy / duong tien that: KHONG doi.

## 1. Bug (xac nhan)
File `src/main/java/com/binance/chuyennd/tradecore/selector/ShadowBookC3.java`, ban cu dong 194-203:

    private final Map<String, Pos> open = ...;
    public void openPos(...) {
        Pos p = new Pos(...);
        if (open.putIfAbsent(symbol, p) == null) { nOpen++; saveState(); LOG... }
        // else: leg2+ cung coin bi VUT im lang
    }

`open` la `Map<String,Pos>` (1 leg / coin) + `putIfAbsent` => leg thu 2+ cua CUNG coin (DCA_LEVEL1,
BIG_DOWN) bi bo qua: khong VWAP lai, khong dem legCount, khong cong qty/margin, khong log.
Leg2+ toi qua `BinanceOrderTradingManager.shadowHandleOrder` (KHONG co guard `isHolding`); duong
selector (`DetectEntrySignal2TradeNormal`) tu early-return khi da giu. Hau qua: 2 sleeve
(`BIG_DOWN` 9884.4 + `DCA_LEVEL1` 7407.3) khong tai lap = **17291.7 / 76428.4 = 22.6% pnl** thieu
(docs/result/RESULT_SIZEPROBE.md muc 3).

## 2. Fix (Map -> Cluster, chi accounting)
- `open` doi tu `Map<String,Pos>` sang `Map<String,Cluster>`. `Cluster` gop CA leg cua 1 coin:
  `sumEntryQty (Sigma e*q)`, `qty`, `legCount`, `firstEntryPrice` (leg dau, bat bien),
  `tsFirstLeg` (neo time-stop), `tsLastLeg`, `rank`/`symbolPred` (leg KHONG-null dau), `priceSL`,
  `peakRate`. `avgEntry() = sumEntryQty/qty` = VWAP.
- `openPos`: coin CHUA giu => tao Cluster; DANG giu => `addLeg` CONG leg (cap nhat VWAP/qty/legCount,
  giu rank/pred leg KHONG-null dau, re-arm `priceSL=null`+`peakRate=0`) va LOG `add-leg`.
- Position-model KHOP sim `SimulatorMarketLevelTicker1MStopLoss.mergeOrder` (:825-864):
  VWAP `entry = Sigma(priceEntry_i*qty_i)/Sigma qty_i`; `legCount = orders.size()`;
  `firstEntryPrice` leg dau bat bien; time-stop neo `clusterFirstLegTime` (leg dau);
  rank/pred = `clusterSelRank`/`clusterSymbolPred` (leg KHONG-null dau); merge tao cum REQUEST moi
  (`minPrice=priceClose`) => shadow re-arm.
- `marginRunning`/`equityNow`/`tick`/`closeAt` cong/tinh tren VWAP+tong qty cua CUM. `closeAt` ghi
  1 dong ledger/cum: `entry=VWAP`, `qty=tong qty`, pnl `=(exit-VWAP)*tong qty`, `ts_entry=tsFirstLeg`.
- `saveState`/`loadState`: them cot `leg_count,first_entry,ts_last`. Tuong thich nguoc dong 8-truong
  cu (1 leg): legCount=1, firstEntryPrice=entry, tsLastLeg=tsFirstLeg.
- GIU nguyen: SHADOW_NO_PUSH, isolation legacy (skip LegacySymbols o call-site), `trailRate` (+hinge
  net015), ARM 0.07, ratchet lien tuc, time-stop 168h, moi chu ky public (openPos/tick/equityNow/
  marginRunning/openSymbols/isHolding/openCount/ledgerPath). 1 leg => VWAP==entry, legCount==1 =>
  ledger + accounting Y HET truoc.

## 3. Test moi
`src/test/java/.../ShadowBookC3Test.java`:
- `multiLegClusterMatchesSimModel`: leg1(100,q2,rank3,pred0.20)+leg2 DCA(60,q2,rank-1,null) =>
  VWAP=80, qty=4, legCount=2, firstEntryPrice=100, tsFirstLeg=0, rank=3, pred=0.20, DCA re-arm
  (priceSL=null, peak=0); margin=320/lev; MTM(90)=+40; dong o SL 93.6 => pnl=(93.6-80)*4=54.4.
- `clusterStateSurvivesRestart`: cum 2 leg song qua restart (VWAP/legCount/qty/margin nguyen ven).
- Thay test cu `noDuplicateOpen` (khang dinh hanh vi bug — vut leg2).

## 4. Cong
- (a) `mvn -o package`: **BUILD SUCCESS**, `Tests run: 128, Failures: 0, Errors: 0, Skipped: 0`
  (ShadowBookC3Test = 7 test, gom 2 test moi).
- (b) PARITY SIM byte-identical — chay lai baseline `X1_C3_FULL` (profile `profiles/x1_c3_full.properties`,
  dataset `/home/ubuntu/wfo_ds_x1`, `SIM_END_DATE=20251231`) voi jar da build:

  | file | md5 | ky vong | ket qua |
  |---|---|---|---|
  | printDone.csv (nguyen file) | `2478e90d4e6147bf4cc64f75967ef47d` | `2478e90d...` | KHOP |
  | printDone.csv (bo header) | `e13bc39e625b8d2ceebb7b9194f7f4f0` | `e13bc39e...` | KHOP |
  | n dong (bo header) | 2266 | 2266 | KHOP |
  | equity cuoi (b:) | 111428 | 111428 | KHOP |

  => ShadowBookC3 KHONG nam trong duong sim; sua no => sim byte-identical. Cong parity **PASS**.

## 5. Xac nhan pham vi
- Chi sua 2 file: `ShadowBookC3.java` (so giay) + `ShadowBookC3Test.java` (test) + doc nay.
- KHONG cham: sim, gate, entry, exit, sizing, legacy isolation, duong tien that, 242. KHONG push.
