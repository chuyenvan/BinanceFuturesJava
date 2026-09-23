# PREREG_TRAIL_LADDER — gap trailing BAC THANG theo dinh (thay "tran phang")

Viet **TRUOC** khi chay bat ky bien the nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Nguon: brief cua Uni 2026-09-23 + `docs/RESULT_TRAIL_HINGE.md` (tien le: doi **tran PHANG** `SIM_TS_MAX_GAP`
0.08→0.05 / 0.12 va ban le `SIM_TS_PNOPUMP_WEAK_THR` 0.29→0.17 ⇒ **ca 3 NULL**).

## 0. Cau hoi + y tuong (nguyen van Uni)

> *"buoc sl dau 0.07 ok, buoc 2 tam tam, nhung sau do chi 3-8% — hoi be, de truot song 2x/3x. Thay cai dich
> LEN LIEN TUC bang dich theo BAC NHAY cang lon cang dai."*

Co che hien tai (`research/OrderTargetInfoTest.trailRate`, `TradeUtils.trailFromCap`):
arm tai **+7%** (`SIM_RATE_PROFIT_STOP_MARKET=0.07`), roi
`SL_rate = maxProfit − min(maxProfit × TS_GIVEBACK_RATIO(0.5), maxGap)`, trong do `maxGap` la **tran PHANG**
= `TS_MAX_GAP_WEAK=0.03` (yeu, `pNoPump > TS_PNOPUMP_WEAK_THR=0.29`) hoac `TS_MAX_GAP=0.08`; ratchet LIEN TUC.

=> Vong nay doi **HINH DANG ham gap** (bac thang tang dan theo dinh), **khong** phai doi mot con so
(tien le da cho thay doi con so ⇒ NULL).

## 1. Co che trong code (kiem TRUOC, ghi ro file:dong)

| # | cho | noi dung |
|---|---|---|
| 1 | `Configs.java:140-141` | `TS_MAX_GAP = 0.08f`, `TS_MAX_GAP_WEAK = 0.03f` (tran PHANG, hai cap) |
| 2 | `Configs.java:705,708,709,713` | override tu profile: `SIM_TS_PNOPUMP_WEAK_THR`, `SIM_TS_MAX_GAP`, `SIM_TS_MAX_GAP_WEAK`, `SIM_RATE_PROFIT_STOP_MARKET` |
| 3 | `TradeUtils.java:40-46` | `trailFromCap(peak, maxGap)`: `gap = min(peak*0.5, maxGap)`, `rate = peak − gap`, lam tron buoc **0.005** |
| 4 | `OrderTargetInfoTest.java:370-379` | `trailRate(peak)`: `TS_CAP_STRONG_RANK>0` → nhanh RANK (T170 **khong** dat ⇒ khong chay); nguoc lai `calRateLossDynamicBuyPNoPump(peak, symbolPred, thr)` |
| 5 | `Simulator…StopLoss.java:249-262` | `updateTPSL`: ratchet SL khi `rateLoss >= arm(0.07)`; chi nang SL khi `priceSLNew > priceEntry` (BAT BIEN khong am) |
| 6 | `OrderTargetInfoTest.java:216-222` | nhanh khop SL: `minPrice <= priceSL` → `STOP_MARKET_DONE` neu `priceSL > priceEntry`, nguoc lai `STOP_LOSS_DONE`; gia chot `priceTP = min(priceSL, bar.open)` |
| 7 | `OrderTargetInfoTest.java:145-146` | `maePeak` = dinh GIA THAT cua cum tu leg dau (chi di LEN, khong tham gia quyet dinh khi `COND_EXIT_HOURS=0` — T170 khong dat) |

**Ket luan §1:** duong trailing cua T170 la (1)+(3)+(4) o tren; `TS_CAP_STRONG_RANK` khong bat. Khong co co
nao khac vo hieu. Bien the vi vay phai la **bien the CODE/PROFILE** (khong phai bins — dung y `KAGGLE_SIM.md`
§6, va khong dung `TICKER_SOURCE`).

## 2. Cong chan BUOC 0 (bat buoc, lam TRUOC)

1. **Key bind**: flag MOI `TS_LADDER` default **OFF** ⇒ `trailRate()` di **nguyen duong cu** ⇒ `printDone.csv`
   phai **byte-identical** md5 `efb793e2468ca3a7318da0f0ad23d4fc` (n=1089, equity 111070) — nhu tien le
   `RESULT_TRAIL_HINGE`/`RESULT_SELECTOR_LEG_CUT`. Khac bat ky byte nao ⇒ **DUNG, bao RO**.
2. **Parity tren Kaggle** (khong chay Java sim tren Oracle): bundle `sim-x1-2021-bundle` + jar MOI
   (dataset `sim-jar-trailladder`) + `profile x1_gs_t170` + `SIM_END_DATE=20251231`, `TICKER_SOURCE=file`.
   Tien le da xac nhan Kaggle == Oracle byte-identical cho profile/cua so nay (`docs/KAGGLE_SIM_48M.md`).
3. Neu (1) hoac (2) FAIL ⇒ DUNG, khong chay bien the, bao RO.

## 3. Co che moi — GAP BAC THANG (chot TRUOC)

Them 2 key PROFILE (doc qua `Cfg`):

| key | y nghia |
|---|---|
| `TS_LADDER` | cong tac, `1` = bat. **Default OFF** (khong khai bao) ⇒ byte-identical |
| `TS_LADDER_LO` | can duoi (tang dan) cua tung bac, theo **RATE DINH** (`0.10` = +10%) |
| `TS_LADDER_GAPS` | gap tuong ung, cung do dai, tat ca `> 0` |

Cong thuc (moi, trong `TradeUtils`):

```
peak = maxProfitRate (calRateLossMax(ticker.maxPrice))
gap  = GAPS[i]  voi i = chi so CUOI cung ma peak >= LO[i]
peak < LO[0]  =>  quay ve CONG THUC CU: gap = min(peak*0.5, maxGap)   (maxGap = STRONG/WEAK theo pNoPump)
gap  = min(gap, peak*0.9)         <-- BAT BIEN: SL LUON TREN ENTRY
SL   = round((peak - gap)/0.005)*0.005
```

- **BAT BIEN "SL luon tren entry" giu nguyen**: `gap <= peak*0.9` ⇒ `SL >= peak*0.1 > 0`; va `updateTPSL`
  van chi nang SL khi `priceSLNew > priceEntry` (dong 6 o §1). Khong doi dong nao khac cua ratchet.
- **KHONG lam no thanh gene HPO (chu y, khong phai so sot):** `StrategyWfoTask` ap gene bang **REFLECTION**
  len **FIELD SCALAR** cua `Configs` (`Field.setFloat/setInt`). `TS_LADDER_LO` / `TS_LADDER_GAPS` la
  **`float[]`** ⇒ reflection **khong cham toi duoc** ⇒ **mang KHONG duoc HPO dieu khien**, va do la **chu y**
  (cung tien le `DCA_GRID_LEVELS`/`DCA_GRID_WEIGHTS`, `Configs.java:208`). `TS_LADDER` chi la cong tac
  `boolean`. Vong nay **khong chay HPO**, khong tune sau khi thay so.
- Validate bang tay: mang phai **cung do dai**, `LO` **tang dan nghiem ngat**, `GAPS` **> 0**; sai ⇒
  `System.exit(2)` (fail-fast, khong am tham roi ve default).

### 3.1 Ba bien the (k = 3, CHOT TRUOC — dung nguyen so brief giao)

| tag | ten | `TS_LADDER_LO` | `TS_LADDER_GAPS` | doc |
|---|---|---|---|---|
| `L1` | thang nhe | `0.00,0.10,0.25,0.50,1.00` | `0.04,0.08,0.15,0.25,0.35` | <10%→4%; 10-25%→8%; 25-50%→15%; 50-100%→25%; >100%→35% |
| `L2` | thang doc | `0.00,0.10,0.25,0.50,1.00` | `0.04,0.10,0.20,0.35,0.50` | <10%→4%; 10-25%→10%; 25-50%→20%; 50-100%→35%; >100%→50% |
| `L3` | chi noi o vung lai lon | `0.50,1.00` | `0.25,0.40` | peak<50% → **cong thuc CU**; 50-100%→25%; >100%→40% |

Doi chung: **parity T170** (khong bien the nao khac). `k = 3` (3 ung vien; baseline KHONG tinh).

### 3.2 Do LUONG "bat song lon" (muc DICH cua thay doi) — bat buoc

Them 1 co **do-luong-only** `SIM_TRAIL_TRACE` (default OFF) ghi file **RIENG** `storage/trailTrace.csv`
(printDone + cot `peak` = `maePeak` cua cum). **KHONG them cot vao `printDone.csv`** (se pha cong hoi quy
byte-identical — dung tien le `PREARM_SL`/`SELRANK` cua X2/X3: ghi log/file rieng). Cong cu chi DOC, khong
tham gia quyet dinh vao/ra.

Voi cac lenh **tung dat `peak >= +20%` / `+50%` / `+100%`** (`peakPct = (maePeak−entry)/entry`):
so lenh, **% bi cat som** (exit xay ra khi con cach dinh bao xa: `gap_thuc = peakPct − exitPct`, % lenh thoat
vi trailing `STOP_MARKET_DONE`), **capture ratio = `(exit−entry)/(peak−entry)`**, va **phan bo exit reason**.

## 4. Cham diem (chot TRUOC)

### 4.1 5 rate chat luong (theo LEG, toan bo, tu `printDone.csv`) vs `PARITY`
`n`, `win%`, `TSloss%`, `mP|SM` (mean profit lenh `STOP_MARKET_DONE`), `mP|SL` (lenh `STOP_LOSS_DONE`),
`meanP`. "Tot" = `win%`/`mP|SM`/`mP|SL`/`meanP` **TANG**, `TSloss%` **GIAM** (`docs/RISK_APPETITE.md`).

### 4.2 CI (chot TRUOC, bao CA HAI do rong)
Bootstrap **block-72h** paired, **2000 rep**, **seed `20260905`**; moc neo block **co dinh 2021-07-01**
(2 arm phai dung CHUNG luoi khoi, neu khong ghep cap "paired" sai).

1. `x1.21` — he so **cu**, la muc **brief yeu cau** (rong hon `inflate(3)`);
2. `inflate(3) = sqrt(2 ln 3) = 1.482304` — he so chuan hoa theo `docs/AUDIT_CI_INFLATE_STANDARDIZATION.md`
   (k=3 ung vien; **trung tien le `PREREG_TRAIL_HINGE`** ⇒ **chat hon**).

`rate ngoai CI` chi duoc tinh khi ngoai CI o **CA HAI** do rong (khong chon do rong theo ket qua).

### 4.3 Rang buoc CUNG (`docs/RISK_APPETITE.md`, do tu `sim.out` + `printDone.csv`)
maxDD theo NAM **<= 30%** · UW **<= 200 ngay** · quy xau nhat **>= −15%** · **khong nam am** ·
tap trung 1 coin **<= 15%** equity (`conc_max`). PASS het moi nam moi bien the = PASS rang buoc cung.

### 4.4 Bao cao RIENG (KHONG dung de chon)
PnL/equity cuoi, CAGR, maxDD/UW, phan bo theo nam, `pnl/leg`. **Khong chon bien the theo equity**
(bai hoc `RESULT_SEL_BIGDOWN`: `DROP` +28% end-equity nhung 0/3 rate ngoai CI ⇒ NULL).

## 5. Ky luat ket luan (chot TRUOC)

**GO** chi khi **ca ba**:
1. **>= 2** trong 5 rate (§4.1) **ngoai CI** o **CA HAI** do rong (§4.2) va **CUNG huong TOT**;
2. **het rang buoc cung** (§4.3);
3. **khong rate nao XAU ngoai CI**.

- Neu chi "bat duoc song lon hon ma rate khong doi" ⇒ ghi ro **CHUA DU KET LUAN** (khong phai GO), **kem so
  capture ratio** (§3.2).
- Neu chi **mot bien the** dat ⇒ ghi **UNCONFIRMED**, khong ap dung.
- Khong dat (0/5 rate ngoai CI huong tot) ⇒ **NULL / NO-GO**.

## 6. Du doan ghi truoc (chot truoc khi chay)

> **MASTER (tu soan, vong nay khong co du doan san cua Uni):** ky vong **NULL** cho ca 3 tren 5 rate
> (`TSloss%`/`meanP` dich chuyen nho, nhieu kha nang trong CI). Khac biet CO THE thay duoc la o
> **capture ratio / so lan bi cat som** cua nhom `peak >= 50%` (gap lon hon ⇒ it bi "truot song" hon —
> `RESULT_TRAIL_HINGE` V2 gap 0.12 co `meanP` +0.070, mP|SM +0.023, van trong CI). Neu capture ratio nhom lon
> **KHONG** doi ro ret ⇒ co che "gap bac thang" khong co tac dung do duoc ⇒ NULL chac.

## 7. Quy trinh + tai nguyen

1. Viet + commit pre-reg nay **TRUOC** khi chay.
2. Them code (`Configs` + `TradeUtils` + `OrderTargetInfoTest` + trace) + 3 profile + 2 script; build jar
   bang `mvn -o package` **tren Oracle (chi BUILD, KHONG chay sim, KHONG chay Java sim tren Oracle)`;
   day jar len Kaggle dataset rieng `chuyendinh/sim-jar-trailladder` (`jar_ds` — khong tao lai bundle 5.3GB).
3. Chay **tuan tu/tung dot** tren Kaggle (5 slot/account, 12h kill/kernel, **chi phi 0**). Ghi ro so kernel +
   wall-clock da dung.
4. Cham theo §4; ghi `docs/RESULT_TRAIL_LADDER.md`; commit (**KHONG push**); don file tam.

## 8. Pham vi + cam ket

DEV 2021-07-01..2025-12-31 (`wfo_ds_x1_2021`, `leakFreeFrom=2021-07-01`). **KHONG** dung 2026 (seal).
**KHONG** `claude-run`/Claude Code. **KHONG** chay sim Java tren Oracle (`shadow-c3` dang chay — chi build jar).
**KHONG** git push, KHONG ssh 242. Khong tune sau khi thay so. Khong sua trigger/gate/entry/DCA/sizing/bins
cua T170 — **chi** doi HINH DANG ham gap trailing khi co `TS_LADDER=1`.
