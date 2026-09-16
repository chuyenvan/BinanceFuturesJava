# AUDIT — dao sau BIG_DOWN: co che end-to-end, nguon goc tham so + nghi van leak/overfit, phan ra dong gop

> **Tai lieu MO TA/AUDIT (descriptive).** KHONG pre-reg, KHONG sua mot dong `.java`, KHONG them
> flag, KHONG chay sim moi. Moi so lay tu code (branch `module`) + du lieu DA CO (printDone.csv
> baseline T170 `efb793e2468ca3a7318da0f0ad23d4fc`) + git history + cac DIAG/AUDIT da co.
> **KHONG de xuat con so/tham so moi. KHONG ket luan "nen chon cai nao".**
>
> Boi canh cua nguoi dung: *"bigdown la cai tin hieu cach day 2 nam toi build luc do chua hieu ve
> leak ve overfit nen truoc sau gi cai tien no"*. => Trong tam: **audit nguon goc tham so + nghi van
> leak/overfit**, va **phan ra gia tri that su den tu dau**.
>
> Doc kem (bat buoc): `DIAG_BIGDOWN_TRIGGER_MECHANISM.md`, `DIAG_BIGDOWN_CONCENTRATION.md`,
> `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE.md`, `DESIGN_ROLLING_BIGDOWN.md`,
> `DIAG_DCA_GUARD_COUPLING.md`, `QUEUE.md`.

---

## 0. Tom tat mot dong

BIG_DOWN la mot **cat ngang toan thi truong tren DUNG 1 nen 1 phut** (trung binh return cua 100
coin giam manh nhat thap hon hang so `-0.03157`), chon 2 coin theo **score selector pNoPump tang
dan** (khong theo do giam), **bypass hoan toan cong entry gate**, va dung **chung mot hang so
`MS_DOWN_BIG_AVG`** voi nhanh DCA (`isDcaAlt`). **Hang so nguong `-0.03157` KHONG co tai lieu nao
ghi CACH CHON** — no xuat hien lan dau trong mot commit ten chi la "optimize" (2026-02-26), thay
mot gia tri mac dinh tron `-0.032`, va sau do duoc HPO day len `-0.05514` roi "revert ve cu".
=> nghi van **chon nguong bang cach nhin DEV** la co co so; day chinh la diem can cai tien truoc.

---

## 1. CO CHE END-TO-END (kem dan chieu dong code, khong suy dien)

### 1.1 Trigger o dau va dieu kien gi

`MarketBigChangeDetector.getMarketStatus1M` (dong 174-186) chi con MOT nhanh song:

```java
public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg) {
    if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {     // dong 179, MS_DOWN_BIG_AVG = -0.03157f
        return MarketLevelChange.BIG_DOWN;
    }
    return null;
}
```

`rateUpAvg` va `rateDown15MAvg` duoc truyen vao nhung **khong dung** o nhanh nay (BIG_UP / SMALL_UP /
SMALL_DOWN_15M da bi xoa 2026-09-03). Lookback = **1 nen 1 phut**, khong EMA, khong rolling high.

### 1.2 `rateDownAvg` la gi

`calMarketData` (dong 48-95) + `calRateChangeAvg` (dong 149-167):

- dong 67: `rateChange = rateOf2Double(ticker.priceClose, ticker.priceOpen)` cho moi coin;
- dong 75: `rateDown2Symbols.put(rateChange, symbol)` (TreeMap tang dan);
- dong 86: `calRateChangeAvg(rateDown2Symbols, 100)` — duyet tu khoa NHO NHAT (am nhat), lay trung
  binh **100 phan tu dau**; neu universe nho thi `period` bi ep xuong `size*4/5` (dong 152-154).

=> **`rateDownAvg` = trung binh return cua 100 coin GIAM MANH NHAT trong DUNG nen 1 phut hien tai.**

Ba bo loc truoc khi vao thong ke (dong 63-74):

| dong | loc | muc dich |
|---|---|---|
| 63-65 | bo `Constants.diedSymbol` | coin da chet |
| 69-71 | bo coin `rateChange < -0.15` khi `rateChangeBtc > -0.004` | loai dump rieng le (delist/warning) khi BTC khong giam |
| 72-74 | bo coin `rateChange > 0.3` | loai pump bat thuong |

### 1.3 Chon coin the nao — `getTopSymbolArray` + `pNoPump`

`getTopSymbolArray` (dong 123-146) chi lam 3 viec: duyet `predict2Symbol` theo thu tu TreeMap
(**tang dan**), bo `symbolLocked`, dung khi du `period` phan tu.

Nguon `predict2Symbol`: `SimulatorMarketLevelTicker1MStopLoss.java:324` goi
`extractPredict2Symbol(time2SymbolPred.get(time))` (dong 822-830), va ham do `put(pred, symbolId)`
voi `pred` = **score selector pNoPump** (lower = "de pump nhat" theo selector).

=> **coin duoc chon = 2 coin co pNoPump THAP NHAT trong cac coin chua bi khoa, KHONG theo do giam.**

### 1.4 So coin / tick

| | |
|---|---|
| `NUMBER_ENTRY_EACH_SIGNAL = 2` | `Configs.java:106` |
| nhanh `/2` cho SMALL_UP/SMALL_DOWN_15M | `Simulator...:316-319` — hai level da CHET => thuc te luon **2 coin/tick** |
| `symbolLocked` | toan bo symbol dang co vi the (`Simulator...:311`) => BIG_DOWN chi mo vi the MOI |

Kiem chung bang so lieu: 124 phut trigger x 2 = **248 leg**, khop tuyet doi; moi phut trigger deu
mo dung 2 leg (leg BIG_DOWN bo qua `EntryGate`, xem 1.5).

### 1.5 Duong budget/sizing cho leg BIG_DOWN

`createOrder` (`Simulator...:1202`) — thu tu thuc thi (dan chieu dong, khong suy dien):

1. dong 1215: `if (!levelChange.equals(BIG_DOWN)) { entryGate(...) }` => **BIG_DOWN bypass HOAN TOAN
   cong gate** (khong chiu `GATE_DYN_SCALE`, khong chiu regime scale — `EntryGate.threshold` tra
   `thrBase` khi `symbolPred == null`).
2. dong 1281: `budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange)`
   — cong thuc (`TradeUtils.java:78-95`):
   ```
   u = marginRunning / equity ;  neu u >= U_MAX -> null (chan lenh moi)
   throttle = clamp(1 - u/U_MAX, 0, 1)
   budget = equity * F_BASE * throttle / dcaGridTotalWeight()      // F_BASE=0.03, ladder=13
   ```
3. dong 1297-1298: `budget *= tierMultiplier` (profile TIER_FLAT=1 => luon 1.00).
4. dong 1301-1314 (`DCA_GRID_ENABLED=true`): `legIdx = gridLegCount(cur)`; leg BIG_DOWN la vi the
   MOI => `legIdx = 0`; `ratio = gridLegWeightRatio(0) = w[0] * DCA_GRID_SCALE = 1 * 19.5`; `budget *= ratio`.

Hop nhat (throttle = 1): `budget = equity * 0.03 * throttle / 13 * 19.5 = equity * 4.5% * throttle`.
(Trung khit `DIAG_BIGDOWN_CONCENTRATION` muc 1: `margin(bac 0) = equity x 4.5% x throttle`.)
`BD_SIZE_ADAPT` (dong 1316-1324) mac dinh `off` => khong scale.

### 1.6 Duong EXIT ap cho leg BIG_DOWN

`startUpdateOldOrderTrading` (`Simulator...:916`) — **dung CHUNG cho moi leg, khong co nhanh rieng
cho BIG_DOWN**. Thu tu:

1. PRE-ARM HARD SL (`PRE_ARM_SL`, mac dinh 0 = OFF) — dong 926-946.
2. LOSER TIME-STOP (`LOSER_TIME_STOP_HOURS`, mac dinh 0 = OFF) — dong 946-960.
3. COND EXIT (`COND_EXIT_HOURS`, mac dinh 0 = OFF) — dong 960-976.
4. Arm trailing: `if (maxPrice >= entry*(1+RATE_PROFIT_STOP_MARKET) || priceSL != null)`
   (dong 978-984) => `updateStatusNew` + `updateTPSL` (trailing stop / ratchet / stop-market).
   `RATE_PROFIT_STOP_MARKET = 0.03` (`Configs.java:169`).

Leg BIG_DOWN duoc tao voi `symbolPred=null`, `selRank=null` => theo quy uoc X3 (comment
`Configs.java` muc TS_CAP_STRONG_RANK) no di nhanh **WEAK trailing** = `TS_MAX_GAP_WEAK = 0.03`
(`Configs.java:141`), khong phai `TS_MAX_GAP = 0.08`.

Tren T170, exit thuc te chi co HAI trang thai: `STOP_MARKET_DONE` (thang, trailing) va
`STOP_LOSS_DONE` (thua). Khong co `TAKE_PROFIT_DONE`. (So lieu muc 4.)

### 1.7 Ghep voi DCA — `isDcaAlt`

`MarketBigChangeDetector.isDcaAlt` (dong 188-191):

```java
return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG          // nguong -0.03157
        || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;     // nguong -0.01052
```

=> **`MS_DOWN_BIG_AVG` dung CHUNG cho ca BIG_DOWN lan DCA.** `isDcaAlt` la "cong mo rong thi truong"
cho phep `DcaProcessor.getDCA` chay ke ca khi khong co BIG_DOWN; guard THAT SU cua moi leg DCA la
`DcaUtils.shouldDcaGrid` (do gia per-coin cham `-0.50/-0.75/-0.90` tren `firstEntryPrice`). Chi tiet
da co o `DIAG_DCA_GUARD_COUPLING.md` muc 1-3 (khong lap lai o day).

---

## 2. AUDIT NGUON GOC THAM SO (phan chinh)

### 2.1 Bang toan bo hang so/nguong tham gia quyet dinh BIG_DOWN

Ghi theo field + gia tri + noi khai bao + **commit dua vao + ngay** + **co tai lieu ghi cach chon khong**.

#### (A) Trigger

| Field | Gia tri | Khai bao | Commit dua vao (ngay) | Tai lieu cach chon |
|---|---|---|---|---|
| `MS_DOWN_BIG_AVG` | `-0.03157f` | `Configs.java:392` (override `SIM_MS_DOWN_BIG_AVG` o dong 657) | **Xem 2.2 — day la diem nghi van chinh** | **KHONG CO** |

#### (B) Chon coin / universe

| Field | Gia tri | Khai bao | Commit (ngay) | Tai lieu cach chon |
|---|---|---|---|---|
| `NUMBER_ENTRY_EACH_SIGNAL` | `2` | `Configs.java:106` | `2cbde5f` (2026-04-21) "fixbug predict call marketdataobject" | KHONG CO (so tu nhien, gia tri nho) |
| `calRateChangeAvg(..., 100)` | `100` coin | hardcode `MarketBigChangeDetector.java:86-88` | khong truy rieng (co trong `0a96a1b` 2026-01-27 tro di) | KHONG CO |
| loc dump `-0.15` / BTC `-0.004` / pump `+0.3` | 3 nguong | hardcode `MarketBigChangeDetector.java:69-72` | khong truy rieng | KHONG CO |
| `NUMBER_TICKER_CAL_RATE_CHANGE` | `15` | `Configs.java:107` | khong truy rieng | CHI dung cho `rateDown15MAvg` (`isDcaAlt`), KHONG cho BIG_DOWN |
| tieu chi chon = `pNoPump` tang dan | — | `getTopSymbolArray` `MarketBigChangeDetector.java:123-146` | khong truy rieng | KHONG CO (selector duoc dung cho entry, KHONG thiet ke rieng cho BIG_DOWN) |

#### (C) Sizing

| Field | Gia tri | Khai bao | Commit (ngay) | Tai lieu cach chon |
|---|---|---|---|---|
| `F_BASE` | `0.03f` | `Configs.java:155` | "gene search [0.01, 0.05]" (comment, khong truy rieng) | comment ghi la gene HPO |
| `U_MAX` | `0.60f` | `Configs.java:156` | "gene search [0.40, 0.80]" (comment) | comment ghi la gene HPO |
| `LEVERAGE_ORDER` | `1` | `Configs.java:102` | khong truy rieng | KHONG CO (khong don bay) |
| `DCA_GRID_WEIGHTS` | `1,1,3,8` | `Configs.java:189` | `DIAG_BIGDOWN_CONCENTRATION` + comment muc 8 Configs: "So do tu du lieu that (171k entry, phan phoi MAE p50=-56%)" | CO ly do (MAE), ghi o comment |
| `DCA_GRID_SCALE` | `19.5` (profile, KHONG phai default 1.0) | profile `x1_gs_t170.properties` | theo `DIAG_BIGDOWN_CONCENTRATION` muc 1 | comment muc 8: "scale bu lai phan du tru khong dung" |
| `tierMultiplier` | `1.0` (`TIER_FLAT=1`) | `CoinRankManager` + profile | khong truy rieng | profile dat flat |

#### (D) Exit (dung chung moi leg)

| Field | Gia tri | Khai bao | Commit (ngay) | Tai lieu cach chon |
|---|---|---|---|---|
| `RATE_PROFIT_STOP_MARKET` | `0.03f` | `Configs.java:169` | `3e66898` (2026-07-30) "raise floor 0.01032 -> 0.03" | **CO** — comment ghi ro ly do round-trip cost (fee 0.002 + slippage 0.003 = 0.008) + TASK-139 sweep |
| `TS_MAX_GAP` | `0.08f` | `Configs.java:140` | khong truy rieng | KHONG CO |
| `TS_MAX_GAP_WEAK` | `0.03f` | `Configs.java:141` | khong truy rieng | KHONG CO |
| `TS_GIVEBACK_RATIO` | `0.5f` (default) | `Configs.java:173-175` | khong truy rieng | KHONG CO |
| `PRE_ARM_SL` / `LOSER_TIME_STOP_HOURS` / `COND_EXIT_HOURS` | `0` (tat) | `Configs.java` | mac dinh OFF | — |

#### (E) DCA coupling (di san)

| Field | Gia tri | Khai bao | Trang thai |
|---|---|---|---|
| `DCA_TIME_BIG_DOWN` | `8` | `Configs.java:397` | **CHET** khi `DCA_GRID_ENABLED=true` (chi song o nhanh `shouldDca` cu) |
| `DCA_LOSS_BIG_DOWN` | `-0.15f` | `Configs.java:398` | **CHET** (nhu tren) |
| `DCA_GRID_LEVELS` | `-0.50,-0.75,-0.90` | `Configs.java:187` | guard per-coin cua DCA |

### 2.2 Truy git history cua `MS_DOWN_BIG_AVG` (nghi van chinh)

`git log -L '/MS_DOWN_BIG_AVG/,+1'` + `git log -S` cho thay **dung chuoi**:

| Commit | Ngay | Message | Gia tri `MS_DOWN_BIG_AVG` |
|---|---|---|---|
| `0a96a1b` | 2026-01-27 | "add hpo for market" | `-0.032` (double, **default tron**) — lan dau khai bao, **la gene HPO** (kem `RunOptimizationMarketThreshold`) |
| `a391b7e` | 2026-02-26 | "optimize" | `-0.03157` (double) — **thay default tron bang 5 chu so co nghia**, khong kem giai thich |
| `2cbde5f` | 2026-04-21 | "fixbug predict call marketdataobject at production" | `-0.03157f` (float, chuyen `utils/Configs.java`) |
| `cb50841` | 2026-06-01 | "update HPO moi nhat" | `-0.05514f` (comment "Cu: -0.03157f") — **HPO tim ra gia tri khac** |
| `1fbe620` | 2026-06-04 | "Ablation filter + revert params HPO ve cu" | `-0.03157f` (comment "HPO (da revert ve cu): -0.05514f") — **revert ve -0.03157** |

Cung chuoi cho `MS_UP_BIG_THRES` (nay da chet): `0.025` -> `0.02046` (cung `a391b7e`) ->
`0.01757` (`cb50841`) -> revert `0.02046` (`1fbe620`).

### 2.3 Danh gia leak/overfit (co ly le, khong khang dinh bua)

1. **Nguong `-0.03157` khong co mot tai lieu nao ghi "cach chon".** Toan bo `docs/` khong co file
   nao truoc/trong 2026-02-26 ghi ly do chon `-0.03157`. Commit `a391b7e` chi co ten "optimize",
   khong co message, khong co PREREG, khong co bang chung holdout. => **tai lieu ghi cach chon la
   KHONG TON TAI.**

2. **Dau hieu chon nguong theo ket qua DEV — MANH.** Hai bang chung:
   - Gia tri `-0.03157` co **5 chu so co nghia**, thay mot default tron `-0.032` (2 chu so). Mot
     nguoi chon nguong "bang ly le" se khong chuyen tu `-0.032` sang `-0.03157`; do la dang thuc
     cua **gia tri HPO/sweep da toi uu hoa** (gene range `[-0.055, -0.020]` khai o `WFORunner:67`).
   - Comment hien tai `// HPO (da revert ve cu): -0.05514f` **tu thua nhan** gia tri da tung bi HPO
     day len `-0.05514` (tren DEV) roi bi "revert ve cu". Tuc **gia tri nay da tung duoc toi uu hoa
     tren chinh du lieu DEV dang dung de danh gia** — day la dinh nghia cua chon nguong bang cach
     nhin DEV.
   - `MS_UP_BIG_THRES` (cung commit, cung kieu 5 chu so) cung vay — va no da **chet** khi BIG_UP bi
     xoa (2026-09-03), tuc mot nguong duoc tune theo DEV lai khong con tac dung.

3. **Do tu do (so tham so) tren so quan sat.**
   - So tham so tham gia truc tiep quyet dinh BIG_DOWN (trigger + chon + sizing + exit): ~5-10
     scalar (`MS_DOWN_BIG_AVG`, `NUMBER_ENTRY_EACH_SIGNAL`, `F_BASE`, `U_MAX`, `DCA_GRID_SCALE`,
     `RATE_PROFIT_STOP_MARKET`, `TS_MAX_GAP_WEAK`, `TS_GIVEBACK_RATIO`, ...) — chua ke cac nguong
     loc `-0.15/-0.004/0.3`.
   - So quan sat doc lap cua su kien BIG_DOWN: **124 phut / 56 ngay / 248 leg** tren 4.5 nam
     (1645 ngay). Moi thong ke o muc ngay chi co **56** quan sat "co su kien"; moi thong ke o muc
     leg-co-thua (`STOP_LOSS_DONE`) chi co **21** quan sat (xem muc 4).
   - => ti le tham so / quan sat rat cao, dac biet voi nguong trigger (1 nguong / 56 ngay su kien).
     **Rat de overfit.** Day khong phai khang dinh "da overfit", ma la **khong co bang chung nao
     trong repo cho thay nguong nay da duoc kiem holdout doc lap.**

4. **KHONG xac dinh duoc tu repo:** (i) `-0.03157` co phai la dau ra cua mot run HPO cu the nao
   khong, tren cua so nao; (ii) co bat ky OOS/holdout nao duoc chay luc do khong. Repo **khong co
   PREREG/ket qua nao** dat truoc 2026-02-26 cho nguong nay. => **ghi RO la KHONG xac dinh duoc.**

5. **Ngoai le duy nhat co tai lieu:** `RATE_PROFIT_STOP_MARKET = 0.03` (exit, dung chung) co giai
   thich ro rang trong commit `3e66898` + comment `Configs.java:167-168` (round-trip cost +
   TASK-139 sweep). Con lai, cac nguong BIG_DOWN deu khong co provenance.

### 2.4 Doi chieu voi ket luan da co

- `DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 3-4 da do: nguong `-0.03157` nam **thap hon p0.01** cua phan
  phoi `rateDownAvg` (124/2,301,233 phut = 0.00539%), tuong duong **-22.4 sigma**; va muc 4 ghi ro
  "moi so o muc 3 deu tinh tren DEV... bat ky tham so nao chon tu day deu **da bi nhiem**". Audit
  nay **bo sung them bang chung provenance**: khong chi "da nhiem theo dinh nghia", ma **gia tri
  nguong tu no khong co giay to ghi cach chon** va **da tung bi HPO tune roi revert**.
- `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` da xac lap: BIG_DOWN bypass gate, so "ve" khong phu thuoc
  gate (248 leg giong nhau o 3 gate), va gia tri cua no den tu **sizing** (xem muc 4). Audit nay
  khong mo lai phan do, chi lam ro them **nguon goc cua trigger** ma AUDIT do khong truy.

---

## 3. PHAN RA DONG GOP (so lieu)

Nguon: `printDone.csv` T170 (md5 `efb793e2...`, n=1089), gom theo `level`. So lieu muc nay **khop
tung dong** voi `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` muc 1-2 (da kiem lai doc lap, theo nam DONG
lenh = cot `end`).

### 3.1 Theo nguon leg (T170)

| nhom | n leg | % leg | pnl (USD) | % PnL | pnl/leg |
|---|---|---|---|---|---|
| PREDICT_SYMBOL_TRADE (entry qua gate) | 821 | 75.4% | 47,115 | 61.9% | 57.4 |
| **BIG_DOWN** | **248** | **22.8%** | **16,254** | **21.4%** | **65.5** |
| DCA_LEVEL1 | 20 | 1.8% | 12,701 | 16.7% | 635.1 |
| **TONG** | **1089** | 100% | **76,070** | 100% | — |

=> BIG_DOWN chiem **22.8% so leg** nhung **21.4% PnL**. Tong phan **KHONG qua gate scale**
(BIG_DOWN + DCA_LEVEL1) = **38.1% PnL** (trung khit AUDIT).

### 3.2 BIG_DOWN theo tung nam (theo nam DONG lenh = cot `end`)

| nam | n leg | pnl BIG_DOWN | pnl TONG | % PnL BIG_DOWN |
|---|---|---|---|---|
| 2021 | 32 | +982 | +4,273 | 23.0% |
| 2022 | 20 | +1,358 | +7,688 | 17.7% |
| 2023 | 49 | +2,022 | +16,637 | 12.2% |
| 2024 | 71 | +6,172 | +20,097 | 30.7% |
| 2025 | 76 | +5,720 | +27,374 | 20.9% |

(Ghi chu: cot `start` (gio mo, GMT+7) cho 2023=50 leg / +1,716 va 2024=70 / +6,478 — lech 1 leg XVS
mo 2023-12-27, dong 2024-01-03, pnl -305.72. Bang tren dung cot `end` de khop quy uoc "theo nam dong
lenh" cua AUDIT.)

=> Dong gop cua BIG_DOWN **tap trung vao 2024 (30.7%) va 2025 (20.9%)** — cung la 2 nam co PnL tong
lon nhat va la giai doan `rateDownAvg` am sau nhat (`DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 3.4:
2024 depth -0.137, 2025 depth -0.354).

---

## 4. TRONG BIG_DOWN, GIA TRI DEN TU DAU (entry quality / sizing / exit)

Kiem lai bang so tu `printDone.csv` (da tinh lai doc lap). T170 chi co 2 trang thai exit
`STOP_MARKET_DONE` (thang) va `STOP_LOSS_DONE` (thua).

| chi so | BIG_DOWN (n=248) | PREDICT entry (n=821) |
|---|---|---|
| pnl/leg | **65.54** | 57.39 |
| win% (`STOP_MARKET_DONE`) | **91.53%** | 89.89% |
| TSloss% (`STOP_LOSS_DONE`) | **8.47%** | 10.11% |
| mP\|SM (mean loi khi thang) | **+96.57** | +110.75 |
| mP\|SL (mean lo khi thua) | **-269.86** | -417.10 |

Doc mo ta (khong suy luan qua):

1. **Entry quality — co that, nhung o phia "lo nong hon", khong phai "thang to hon".** BIG_DOWN co
   `mP|SM` **THAP hon** entry (+96.57 vs +110.75) va `win%` chi nhuom hon 1.6pp, nhung `mP|SL` **nong
   hon rat nhieu** (-269.86 vs -417.10). Nghia la: leg BIG_DOWN **khong thang to hon**, no **thua it
   hon** — dung voi ban chat "bat day": vao sau mot nhip giam lon nen khoang cach xuong SL nong hon.
   Chu y: `mP|SM` thap hon cung nhat quan voi viec chon coin theo `pNoPump` (KHONG theo do giam) —
   diem `DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 1.5 da co la "bat hop ly".

2. **Sizing — day la ket luan audit cu, va so lieu KHONG mo lai duoc.** `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE`
   muc 3 da chung minh: cung **248 leg / 124 tick / 54 ngay** o ca T100/T130/T170, nhung `pnl/leg`
   BIG_DOWN tang don dieu **46.6 -> 53.3 -> 65.5** (T170 +41% so T100), do gate chat => it lenh dong
   thoi => `throttle` cao => moi leg duoc cap budget lon hon. **Do la loi ich qua co che sizing, khong
   phai qua chon entry.** Audit nay khong chay lai 3 gate, chi xac nhan T170 = 65.54 (khop 65.5 cua AUDIT).

3. **Exit — khong phai nguon edge.** Exit dung CHUNG moi leg (cung trailing, cung `TS_MAX_GAP_WEAK`
   vi `selRank=null`). `mP|SM` cua BIG_DOWN **thap hon** entry, tuc exit **khong** sinh ra gia tri
   tang them cho BIG_DOWN. Neu co, gia tri exit nay da nam chung o ca entry lan BIG_DOWN.

=> **Ket luan trung thuc (2 tang, khong mau thuan):**
- Tang "vi sao T170 rut nhieu hon T100 tu BIG_DOWN" => **sizing** (ket luan AUDIT, dung vung).
- Tang "vi sao leg BIG_DOWN co `pnl/leg` cao hon leg entry trong cung T170" => **entry quality o
  phia giam lo** (mP|SL nong hon nhieu), khong phai sizing, khong phai exit.

---

## 5. DO NHAY / GIOI HAN THONG KE

(Toan bo so muc nay tai dung tu `DIAG_BIGDOWN_TRIGGER_MECHANISM.md` muc 3 va `DESIGN_ROLLING_BIGDOWN.md`
muc 1 — ghi ro nguon.)

| chi so | gia tri | nguon |
|---|---|---|
| So phut trigger / 4.5 nam | **124 phut** (0.00539%) | DIAG muc 3.3 |
| So ngay co >=1 trigger | **56 ngay** (3.4% so ngay) | DIAG muc 3.4 |
| So leg BIG_DOWN | **248 leg** (124 tick x 2) | DIAG muc 3.4 + da kiem lai |
| Trigger theo nam (so phut) | 2021:16, 2022:10, 2023:25, 2024:35, 2025:38 | DIAG muc 3.4 |
| Hinh dang `rateDownAvg` | skew -14.87, excess-kurtosis +2401 | DESIGN muc 1 |
| Nguong quy ra sigma | -22.4 sigma (fat-tail, khong phai 2-3 sigma) | DESIGN muc 1 |

He qua ve power:

1. **Mau su kien rat mong.** Moi thong ke o muc ngay dua tren **56** ngay co su kien; moi thong ke o
   muc leg-co-thua dua tren **21** leg `STOP_LOSS_DONE` (muc 4). Voi co mau do, `mP|SL = -269.86`
   la trung binh cua 21 quan sat => CI rat rong.
2. **Khong co "tay doi chung doc lap" cho trigger.** Ca 3 gate T100/T130/T170 cho **cung 248 leg /
   124 tick / 54-56 ngay** (`AUDIT` muc 3) => khong the dung gate lam bien doi chung doc lap de
   kiem nguong trigger. Bat ky tham so trigger moi deu **fit tren chinh 56 ngay su kien do**.
3. **Trigger hiem hon p0.01** (124/2,301,233 = 5.4e-5, trong khi p0.01 = -0.0223). Do hiem nay
   khong uoc luong duoc bang quantile rolling truc tiep (cua so 30 ngay ~43k mau => quantile 5.4e-5
   ~ 2 mau) — `DESIGN_ROLLING_BIGDOWN` muc 0-1 da chung minh. => bat ky thiet ke rolling nao cung
   phai di bang **hoi tu (conjunction)** cac marginal uoc luong duoc, khong phai mot quantile cuc doan.
4. **Do nhay tan suat rat cao theo giai doan.** `DESIGN` muc 1 ghi: `k` de tai lap mat do hien tai
   phai ~23-25 va dao **-13.5..-41.5 (3.1x)** theo giai doan. Tuc mot nguong co dinh `-0.03157` bat
   "su kien" co tan suat **khong on dinh qua thoi gian**.

---

## 6. DANH SACH HUONG CAI TIEN UNG VIEN (xep hang)

> Moi huong gom: gia thuyet, bang chung hien co, bang chung CAN de ket luan, chi phi (co can cham
> LIVE khong), rui ro. **KHONG de xuat con so, KHONG chon ho.** Xep theo tang rui ro va do manh bang
> chung (tu thap -> cao), nhat quan voi `DESIGN_ROLLING_BIGDOWN` muc 5.

### H1 — TACH `MS_DOWN_BIG_AVG` thanh 2 duong rieng (BIG_DOWN vs `isDcaAlt`) [nen lam TRUOC moi huong khac]

- **Gia thuyet:** nguong DCA va nguong BIG_DOWN nen la 2 bien doc lap, vi hien tai 1 hang so dieu
  khien ca 2 con duong co tan suat lech nhau 43x.
- **Bang chung hien co:** `DIAG_DCA_GUARD_COUPLING` muc 3 — `rateDown15MAvg` cham nguong o 0.231%,
  `rateDownAvg` chi 0.00539%; doi chung se doi DCA nhieu hon BIG_DOWN.
- **Bang chung CAN:** parity gate byte-identical sau khi tach (xac nhan khong doi hanh vi khi giu
  cung 2 gia tri).
- **Chi phi:** chi code (them 1 field + 1 nhanh doc rieng); khong can cham LIVE neu chi doi duong SIM
  truoc; nhung tach = doi hanh vi => can parity rieng.
- **Rui ro:** thap; nhung neu tach xong ma khong giu gia tri y het thi doi tan suat DCA (nhay 43x).

### H2 — SIZING theo severity (giu nguyen trigger, doi size leg BIG_DOWN) [rui ro thap]

- **Gia thuyet:** gia tri cua BIG_DOWN den tu sizing (muc 4 + AUDIT) => scale size theo do sau se
  trung dung diem tao gia tri, va co the giam rui ro tap trung (tran/giam size khi cuc doan).
- **Bang chung hien co:** `AUDIT` muc 3 (pnl/leg tang theo gate = sizing); `DIAG_BIGDOWN_CONCENTRATION`
  (13 cum bac 3 => -27,857 USD; T130/AIA -12,400 = -11.8% equity); `PREREG_BD_SIZE_ADAPT` da chay va
  ra **NULL** (khong ket luan duoc, giu T170).
- **Bang chung CAN:** mot pre-reg rieng do lai pnl/leg va tap trung 1-coin (max %equity, so cum bac>=2/3)
  — `BD_SIZE_ADAPT` da chay nhung chua cho tin hieu du.
- **Chi phi:** chi cham duong budget nhanh BIG_DOWN; khong cham trigger/live/isDcaAlt/HPO gene.
- **Rui ro:** thap nhat trong cac huong "co tac dong"; nhung scale LEN co the day margin qua U_MAX
  (da duoc ghi la "tuong minh" trong PREREG).

### H3 — SELECTION: doi/bo sung tieu chi chon 2 coin BIG_DOWN [rui ro thap-vua]

- **Gia thuyet:** chon coin theo `pNoPump` (de pump nhat) khong lien quan "con nao bi ban manh nhat";
  chon theo drop 1-phut causal (hoac mix) se "bat dung con rot sau nhat" => chat luong leg tang ma
  khong doi so leg.
- **Bang chung hien co:** `DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 1.5 (chon theo pNoPump, khong theo do
  giam); `AUDIT` muc 3 (161/166/161 coin khac nhau nhung so leg y het => co khong gian doi SELECTION);
  `PREREG_SEL_BIGDOWN` da chay va ra **NULL**.
- **Bang chung CAN:** mot pre-reg do lai pnl/leg, win%, mP|SM, mP|SL rieng BIG_DOWN tren cac mode
  drop/mix/drop_top8 (da co code, chua co ket qua du manh).
- **Chi phi:** chi cham duong chon coin (khong cham trigger, khong cham live cong thuc tinh ticker).
- **Rui ro:** chon "rot sau nhat" co the trung coin delist/thanh khoan mong (loc `diedSymbol` da co
  nhung can kiem them); khong tang so leg.

### H4 — TRIGGER: thiet ke lai thanh hoi tu (conjunction) [rui ro cao, lam sau cung]

- **Gia thuyet:** do hiem hien tai phai den tu giao cua >=2 marginal uoc luong duoc (vd depth +
  rateDown15M + xac nhan k phut), khong phai 1 quantile cuc doan cua 1 bien fat-tail.
- **Bang chung hien co:** `DESIGN_ROLLING_BIGDOWN` muc 4 (muc 4.1) — `rateDown15MAvg` co san lam D2;
  muc 1 chung minh mean-k*std va quantile truc tiep deu khong tai lap duoc do hiem.
- **Bang chung CAN:** pre-reg rieng, nhung **bat buoc** phai giai quyet truoc 5 rang buoc ky thuat
  (H1 tach nguong; sim+LIVE chung ham; cam dong `calMarketData` = duong feature model; `MS_DOWN_BIG_AVG`
  la gene HPO o 3 noi; mau su kien 56 ngay).
- **Chi phi:** cham ca sim + LIVE + gene HPO + duong feature; cao nhat.
- **Rui ro:** cao nhat — doi ban chat BIG_DOWN, va tren 56 ngay su kien thi bat ky tham so trigger
  moi deu rat de overfit (khong co tay doi chung doc lap).

### Thu tu de xuat (ghi nhan tu DESIGN, khong phai quyet dinh moi)

1. **H1 (tach nguong)** la tien de cua moi huong khac.
2. **H2 (sizing)** va/hoac **H3 (selection)** — bang chung manh nhat + blast radius nho.
3. **H4 (trigger)** chi lam sau khi H1-H3 da chay va co ly do ro.

---

## 7. GIOI HAN CUA TAI LIEU NAY

1. **Khong chay sim, khong sua code.** Moi so la doc code + doc lai `printDone.csv` T170 + git
   history + cac DIAG/AUDIT da co. Khong co so lieu holdout 2026.
2. **KHONG xac dinh duoc nguon goc chinh xac cua `-0.03157`:** repo khong co PREREG/ket qua dat
   truoc 2026-02-26. Ket luan "nghi van chon theo DEV" la **suy luan co ly le** (5 chu so co nghia +
   comment "da HPO roi revert"), KHONG phai bang chung truc tiep "da chay run HPO nao, cua so nao".
3. **Phan ra dong gop (muc 3-4) la ATTRIBUTION, khong phai COUNTERFACTUAL.** Giong gioi han da ghi o
   `AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE` muc 5.1: bo PnL BIG_DOWN ra **khong** mo phong duoc the gioi
   khong co BIG_DOWN (von/ throttle/ sizing cac leg sau khac han). Duong equity tong hop lai KHONG
   dung de cham hard-constraint (maxDD/UW) — xem muc 5.2 cua AUDIT do.
4. **So leg DCA/gio/phut va tap trung coin** lay tu `DIAG_DCA_GUARD_COUPLING` va
   `DIAG_BIGDOWN_CONCENTRATION` — khong kiem chung lai doc lap o day.
5. **Phan bo per-nam cua BIG_DOWN** tinh theo cot `end` (nam dong lenh). Dung cot `start` (gio mo,
   GMT+7) se lech 1 leg XVS (mo 2023-12-27, dong 2024-01-03) giua 2023/2024 — da ghi ro o muc 3.2.
6. **Khong de xuat con so, khong ket luan "nen chon cai nao".** Muc 6 chi liet ke cac huong ung vien
   kem bang chung CAN; viec chon la quyet dinh pre-reg cua MASTER.
