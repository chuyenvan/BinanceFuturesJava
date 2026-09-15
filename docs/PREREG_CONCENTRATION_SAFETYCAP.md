# PRE-REG — CONCENTRATION SAFETY-CAP (safety-net circuit breaker, khong binding tren lich su)

> **Trang thai:** pre-reg DA CHOT boi MASTER truoc khi viet mot dong code nao. Commit nay di
> TRUOC commit code. Khong phai de xuat de chon — la spec de trien khai dung.
>
> Tai lieu nen bat buoc doc truoc: `docs/DIAG_DCA_CONCURRENCY.md` (commit `f03a4f1`) va
> `docs/DIAG_BIGDOWN_CONCENTRATION.md`.

---

## 0. Boi canh — vi sao lam, va vi sao KHONG cat giam gi

`DIAG_DCA_CONCURRENCY.md` da do tren 3 baseline (T170 / T130 / T100, dataset `wfo_ds_x1_2021`,
2021-07 -> 2025-12) va ket luan:

1. **DCA-grid pile-in gan nhu khong xay ra that.** Dinh AGGREGATE margin nam trong cac leg
   DCA-grid bac>=1 (cong dong toan so) chi dat **29.25% equity (T170)**, **40.40% (T130)**,
   **41.20% (T100)**. **Chua bao gio cham 50%.** So episode co aggregate >= 50% equity = **0**
   o ca 3 baseline.
2. Cum "vao o at" THAT SU di qua duong **BIG_DOWN** (mo vi the MOI), khong phai duong DCA:
   dinh **54 leg BIG_DOWN trong 1 gio**, dung 1 moc `2025-10-11 04:13`, **giong het nhau o ca 3
   gate** (leg BIG_DOWN co `symbolPred=null` nen bypass hoan toan `GATE_DYN_SCALE`).
3. Nhung **dung cum BIG_DOWN do lai la co che cuu T170 trong dot underwater te nhat** — da co
   audit rieng xac nhan BIG_DOWN la NECESSARY, khong phai nhieu.

=> **Quyet dinh cua MASTER: KHONG cat giam BIG_DOWN/DCA trong vung da quan sat.** Khong danh doi
CAGR. Thay vao do lap **safety-net circuit breaker dat nguong CAO HON dinh lich su** — bao ve
truoc kich ban TE HON bat ky dieu gi da thay trong 4.5 nam, ma **khong duoc doi mot so lieu
backtest nao dang co**.

**Day KHONG phai mot lever toi uu hoa.** Day la BAO HIEM. Neu round nay lam doi bat ky ket qua
baseline nao, no da THAT BAI theo dinh nghia.

---

## 1. Xac minh co che (Buoc 0 — da lam truoc khi code, khong suy doan)

Doc lai `DcaUtils.java`, `DcaProcessor.java`, `SimulatorMarketLevelTicker1MStopLoss.java`,
`EntryGate.java`, `Configs.java`, `Cfg.java`. Ranh gioi hai co che:

| | **BIG_DOWN** | **DCA-grid** |
|---|---|---|
| Ban chat | **MO VI THE MOI** (leg DAU cua mot cum) | **CONG THEM leg** vao cum DA MO |
| Kich hoat | `MarketBigChangeDetector.getMarketStatus1M(...)` tra ve `BIG_DOWN` (gia thi truong sap) | `DcaUtils.shouldDcaGrid(firstEntryPrice, lastPrice, legCount)`: `drop <= -50/-75/-90%` do tren `firstEntryPrice` |
| Chon symbol | `getTopSymbolArray(numberOrder, ..., symbolLocked, ...)` — `symbolLocked` = TOAN BO symbol dang chay => **chi coin CHUA co vi the** | `DcaProcessor.getDCA(...)` stream tren **vi the DANG MO** => **chi coin DA co vi the** |
| Tran moi tick | `NUMBER_ENTRY_EACH_SIGNAL=2` (SMALL_UP / SMALL_DOWN_15M thi /2) | **KHONG co tran** — vong lap khong `break`/`limit` |
| Diem goi | `SimulatorMarketLevelTicker1MStopLoss:336` `createOrderBUY(symbolId, ticker, levelChange, ...)` voi `levelChange == BIG_DOWN` | `:344` (nhanh market-level) va `:362` (nhanh `isDcaAlt`), ca hai voi `MarketLevelChange.DCA_LEVEL1` |
| Gate | `createOrder:1122` — `if (!levelChange.equals(BIG_DOWN))` => **BIG_DOWN BO QUA EntryGate** | di qua `EntryGate` nhung `symbolPred == null` => an nguong CO SO, **khong an `GATE_DYN_SCALE`** |

**Hai co che TACH BIET hoan toan** — dung nhu gia dinh cua MASTER. Mot leg khong the vua la
BIG_DOWN vua la DCA-grid: tap symbol cua hai duong la BU NHAU (`symbolLocked`).

### 1.1 Diem chen check — MOT phieu duy nhat

Ca 4 call-site (`:336`, `:344`, `:362`, `:398`) deu do vao **mot ham loi duy nhat**:

```
createOrderBUY(...) -> createOrder(side, symbolId, ticker, levelChange, marketData, symbolPred, selRank, dcaSignal)
```

Trong `createOrder`, thu tu cong da co: `predict==null` -> `EntryGate` -> `GATE_COUNT_ONLY` ->
loc `TIER_3_SHITCOIN` cho DCA -> `TradeUtils.managerBudget` (`U_MAX`, tra `null` = chan) ->
`tierMultiplier` -> `DCA_GRID` ratio (`ratio<=0` -> `return`) -> `calQuantityTest` -> **tao
`OrderTargetInfoTest`**. Sau diem tao order **khong con bat ky duong return som nao**.

=> **Diem chen ca 2 guard: NGAY TRUOC khi construct `OrderTargetInfoTest`, sau khi `quantity` da
tinh xong.** Ly do chon dung cho do:
- `budget` da nhan het (`throttle`, `tierMultiplier`, `gridLegWeightRatio`) => margin du kien la
  **so THAT**, khong phai uoc luong.
- Dung sau moi cong hien co => guard la **lop cuoi cung**, khong bao gio tranh chap voi cong khac.
- Phan biet loai leg bang `levelChange` (`BIG_DOWN` / `DCA_LEVEL1`) — chinh xac, khong suy doan.

### 1.2 Cach nhan dien mot leg DCA-grid bac>=1 dang mo

Mot leg dang mo la DCA-grid bac>=1 **khi va chi khi** `leg.marketLevelChange == DCA_LEVEL1` va
`!leg.dcaSignalLeg`. Ly do du: `DcaProcessor.getDCA` chi duyet cac symbol DANG CO vi the, nen moi
leg `DCA_LEVEL1` tat yeu la leg thu >= 2 cua cum (bac>=1). `dcaSignalLeg` loai tru leg-2 cua co
che DCA-SIGNAL (`DCA_SIGNAL_GATE`, mac dinh `false` o ca 3 baseline) — hai co che doc lap.

Tap "dang mo" duyet theo `activeRunningIds[0..activeRunningCount)` + `symbol2OrdersEntry[id]`:
`closeOrder` xoa cum khoi `symbol2OrdersEntry` nen day dung la tap con mo (cung quy uoc
`counterOrderRunning()` dang dung).

---

## 2. Guard 1 — `CONC_CAP_AGG_DCA_ENABLED`

| Key | Default | Y nghia |
|---|---|---|
| `CONC_CAP_AGG_DCA_ENABLED` | **`false`** | bat/tat guard 1 |
| `CONC_CAP_AGG_DCA_PCT` | **`0.45`** | tran ti le aggregate margin DCA-grid / equity |

**Quy tac:** tai thoi diem dinh mo **1 leg DCA-grid moi (bac>=1)** cho **bat ky coin nao**:

```
aggNow  = tong margin dang nam trong TAT CA leg DCA-grid bac>=1 dang mo (cong dong TOAN BO coin)
legNew  = margin du kien cua leg sap mo = quantity * entry / leverage
equity  = balanceBasic dang dung trong createOrder (FIX_B3 => equityNow(); cung mau so voi U_MAX)

if ((aggNow + legNew) / equity > CONC_CAP_AGG_DCA_PCT)  ->  KHONG mo leg do
```

- **Chan HAN, khong throttle giam size.** Style giong `TradeUtils.managerBudget` tra `null` khi
  `u >= U_MAX`: `return` khoi `createOrder`, khong tao order.
- Co log lai (mot dong, chi khi guard bat va thuc su chan).
- So sanh la **`>`** (vuot nguong), khong phai `>=`.

---

## 3. Guard 2 — `CONC_CAP_BD_RATE_ENABLED`

| Key | Default | Y nghia |
|---|---|---|
| `CONC_CAP_BD_RATE_ENABLED` | **`false`** | bat/tat guard 2 |
| `CONC_CAP_BD_PER_HOUR` | **`75`** | so leg BIG_DOWN toi da trong 60 phut |

**Quy tac:** tai thoi diem dinh mo **1 leg BIG_DOWN moi**:

```
nBD = so leg BIG_DOWN DA MO trong cua so 60 phut gan nhat, tinh den thoi diem hien tai cua sim
      (rolling window: giu cac timestamp t thoa  t > now - 60 phut)

if (nBD >= CONC_CAP_BD_PER_HOUR)  ->  KHONG mo leg BIG_DOWN do
```

- Dem theo leg **THUC SU DA MO** (ghi timestamp sau khi order duoc tao), khong dem ung vien bi
  cac cong khac loai.
- `now` = `ticker.startTime` (thoi gian sim), khong dung dong ho thuc.
- So sanh la **`>=`** (da du 75 thi chan leg thu 76).
- Trang thai rolling window reset trong `initDataReady` (moi sample WFO bat dau sach).

---

## 4. Cong PARITY — dieu kien BAT BUOC

Ca 2 flag **default `false`**. Khi ca hai `false`, hanh vi phai **byte-identical 100%** voi
baseline hien tai. Khong mot nhanh nao duoc doc gia tri nguong, khong mot cau truc du lieu nao
duoc cap phat, khi flag tat.

---

## 5. Vi sao nguong 0.45 va 75 — "bao hiem KHONG binding", KHONG phai lever

| | dinh LICH SU da do (4.5 nam, 3 baseline) | nguong pre-reg | bien do du |
|---|---|---|---|
| aggregate margin DCA-grid / equity | **0.4120** (T100; T130 0.4040; T170 0.2925) | **0.45** | +9.2% tuong doi so voi dinh |
| leg BIG_DOWN / gio | **54** (giong nhau o ca 3 gate, 2025-10-11 04:13) | **75** | +38.9% so voi dinh |

Hai nguong nay duoc chon **CO CHU DICH CAO HON dinh lich su** de:

- **Khong binding tren lich su** => bat len KHONG lam thay doi mot so lieu backtest nao
  (CAGR / maxDD / UW / n leg / equity deu giu nguyen).
- Chi kich hoat trong kich ban **te hon bat ky dieu gi da thay trong 4.5 nam** — do la toan bo
  muc dich ton tai cua no.

**Ghi ro de tranh hieu nham ve sau:** day **KHONG phai** tham so de tune. Khong duoc dua 0.45 /
75 vao bat ky vong HPO/WFO/grid-search nao. Hai so nay la BIEN AN TOAN, khong phai gene.

---

## 6. Tieu chi PASS cua round nay

Tieu chi **KHONG phai** win-rate / CI bootstrap nhu cac round truoc. Day la verify **tinh dung
dan cua safety-net**:

1. **Parity OFF:** chay lai 3 baseline voi ca 2 guard `false` tren build MOI => md5
   `storage/printDone.csv` phai **KHOP CHINH XAC** baseline da biet.
2. **Parity ON:** chay lai 3 baseline voi ca 2 guard `true` (nguong 0.45 / 75) => md5 phai
   **VAN KHOP CHINH XAC** dung baseline do.

| baseline | profile | md5 baseline | n leg |
|---|---|---|---|
| **T170** | `profiles/x1_gs_t170.properties` | `efb793e2468ca3a7318da0f0ad23d4fc` | 1089 |
| **T130** | `profiles/x1_gs_t130.properties` | `68510567e9b17430b3453b08abe03e9b` | 1580 |
| **T100** | `profiles/x1_c3_full.properties` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` | 2559 |

Harness: `/home/ubuntu/k_runarm.sh <TAG> <PROFILE>` (dataset `/home/ubuntu/wfo_ds_x1_2021`,
`configs/sim_dev_file_2021.properties`, `SIM_END_DATE=20251231`) — y het moi round truoc.

PASS = **ca 6 run deu ra dung md5 baseline tuong ung.**

---

## 7. QUY TRINH KHI LECH — DUNG, KHONG TU NOI NGUONG

Neu **bat ky** baseline nao ra ket qua KHAC khi bat guard, nghia la guard da **binding o dau do
ngoai du doan cua MASTER**. Hai kha nang da luong truoc:

- (a) cach MASTER dinh nghia "aggregate margin" khong khop cach code tu track (vi du mau so
  equity, hoac tap leg duoc tinh la "DCA-grid bac>=1");
- (b) phat hien MOT diem concurrency khac chua thay trong diagnostic.

**Khi do BAT BUOC:**

1. **DUNG NGAY.** Khong chay tiep cac baseline con lai nhu the khong co gi.
2. **KHONG TU Y NOI NGUONG.** Khong sua 0.45 -> 0.50, khong sua 75 -> 100. Khong "tinh chinh"
   dinh nghia aggregate cho khop ket qua.
3. Bao cao chi tiet cho MASTER: **baseline nao**, **thoi diem (timestamp sim) nao**, **guard nao
   bind**, **gia tri do duoc vs nguong**, **chenh lech ket qua bao nhieu** (md5, n leg, equity).
4. MASTER quyet dinh nguong moi qua **MOT PRE-REG RIENG**. Round nay ket thuc o trang thai FAIL.

---

## 8. Pham vi thay doi code (khai bao truoc)

- `Configs.java`: **4 field moi**, doc qua `Cfg.get`/`Cfg.getOr` dung convention cac field
  `DCA_GRID_*` / `DCA_SIGNAL_*` hien co.
- `Cfg.java`: them tien to `CONC_CAP_` vao `TRADING_PREFIXES` (de key moi chiu dung ky luat
  fail-fast "da co profile thi khong duoc dat qua env" nhu moi tham so giao dich khac).
- `SimulatorMarketLevelTicker1MStopLoss.java`: 2 khoi check trong `createOrder` + 1 helper cong
  margin + 1 rolling window BIG_DOWN (reset trong `initDataReady`).
- **KHONG dong** vao `DcaUtils`, `DcaProcessor`, `EntryGate`, `TradeUtils`, va **khong dong vao
  duong LIVE** (`DetectEntrySignal2TradeNormal`) — guard chi nam o duong sim.
