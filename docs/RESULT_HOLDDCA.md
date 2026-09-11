# RESULT_HOLDDCA — bo time-stop + om bag + DCA 1:1 toi da 3 leg theo nhip BIG_DOWN

Pre-reg: `docs/PREREG_HOLDDCA.md` commit `877694c` (2026-09-11 21:40 +07), chot TRUOC khi cham code
va TRUOC moi run. Nen: `devrun/X1_C3_FULL_PARITY_R` (md5 printDone `2478e90d4e6147bf4cc64f75967ef47d`,
equity 111,428, n=2,266). Cua so 2022-01-01..2025-12-31, dataset `wfo_ds_x1`, bins `predwf_map_s1a2_x1`
KHONG rebuild. Khong cham 242 / holdout 2026 / selector / gate / bins.

**KET QUA MOT DONG: 0/3 PASS. Ca ba bien the THUA ro (CI95 cua d CAGR nam hoan toan duoi 0)
va vi pham rang buoc cung o 3/4 nam. Cach doc (b) cua PREREG muc 4, kem nhan "THUA" — DONG nhanh nay.**

---

## 0. Code HIEN TAI lam gi (doc TRUOC khi sua) va toi da doi gi

### 0.1 DCA — trigger

`DcaProcessor.getDCA()` duoc goi o HAI cho trong `SimulatorMarketLevelTicker1MStopLoss`:

| # | Dieu kien tick | Tham so | Level leg sinh ra |
|---|---|---|---|
| a | `getMarketStatus1M(...) != null` — sau ban go 2026-09-03 chi con MOT nhanh song la `BIG_DOWN` (`rateDownAvg < MS_DOWN_BIG_AVG`) | `levelChange` | `DCA_LEVEL1` |
| b | `MarketBigChangeDetector.isDcaAlt(...)` = `rateDown15MAvg < MS_DOWN_BIG_AVG` HOAC `rateDownAvg < MS_DOWN_BIG_AVG/3` (long hon a) | `null` | `DCA_LEVEL1` |

Voi profile C3 (`DCA_GRID_ENABLED=true`) ca hai cho deu roi vao `DcaUtils.shouldDcaGrid(firstEntryPrice,
lastPrice, legCount)`:

- muc lo do tren **`firstEntryPrice` = gia leg DAU cua cum** (bat bien qua DCA), **KHONG phai gia von TB**;
- bac grid `DCA_GRID_LEVELS = -0.50, -0.75, -0.90` => toi da **3 leg them** (tong 4 leg/coin) — trung so
  leg voi pre-reg, nhung moc sau hon nhieu (-50% thay vi -20%);
- **khong co cooldown**, **khong xet cum da arm hay chua**, va khi `DCA_GRID_ENABLED=true` thi
  `levelChange` bi BO QUA hoan toan (nhanh `shouldDca`/`getDcaConfig` chi chay khi grid tat).

Thuc te tren nen: chi **54/2,266 leg** la leg 2+ (1.95% cum PST co DCA) — grid -50/-75/-90 gan nhu khong ban.

### 0.2 DCA — sizing (day la cho de hieu sai nhat)

Duong sizing trong `createOrderBUY`:

```
budget = BudgetManagerSimple.getBudget()                    // = balanceBasic / NUMBER_ORDER_BUDGET
budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange)
budget = budget * CoinRankManager.getBudgetMultiplier(symbolId)
budget = budget * DcaUtils.gridLegWeightRatio(legIdx)        // chi khi DCA_GRID_ENABLED
```

**`managerBudget` BO QUA tham so `budget` truyen vao** — `getBudget()` (= 35000/50 = 700) khong tham gia
sizing mot bit nao. No tra:

```
equity * F_BASE * throttle / dcaGridTotalWeight()     // F_BASE=0.03, throttle=1-u/U_MAX, ladder=13
```

Voi `FIX_B2=true`, `gridLegWeightRatio(i) = w[i] * DCA_GRID_SCALE` = `{19.5, 19.5, 58.5, 156}` cho
luoi `1,1,3,8` va `SCALE=19.5`. Ghep lai, von thuc te moi leg:

| leg | he so tren equity (throttle=1, tier=1) |
|---|---|
| 1 (entry) | `0.03 * 19.5/13` = **4.5% equity** |
| 2 | 4.5% |
| 3 | 13.5% |
| 4 | 36% |

=> luoi hien tai **KHONG phai 1:1 theo USDT**, va **tran von/coin thuc te = 58.5% equity** neu day het
4 leg (hiem: 0.34% cum). "C = getBudget()" trong pre-reg muc 1.4 la mo ta **y dinh** cua comment trong
`Configs.java`, khong phai cai code dang lam.

**Chon dinh nghia C (ghi ro de nguoi doc khong phai doan):** theo pre-reg muc 2 ("E100: entry = C *nhu nay*";
"E25: entry = C/4, 3 leg DCA => toi da C/coin = tran hien nay"), C = **von leg DAU theo cong thuc hien hanh**
= `managerBudget(...) * tierMultiplier * gridLegWeightRatio(0)` = 4.5% equity o throttle=1. Do la con so
duy nhat khop CA HAI cau tren.

### 0.3 Arm / trailing — DA tinh tren gia von trung binh, KHONG phai sua

`mergeOrder()` dung object cum voi `priceEntry = Sigma(px_i * q_i) / Sigma q_i` = **VWAP moi leg dang mo**.
`startUpdateOldOrderTrading` arm tai `ticker.maxPrice >= orderMulti.priceEntry * (1 + RATE_PROFIT_STOP_MARKET)`
va `updateStatusNew`/`updateTPSL` dat SL qua `Utils.calPriceTarget(symbol, priceEntry, ...)` — tat ca tren
object CUM. `firstEntryPrice` chi duoc dung cho `PRE_ARM_SL` (tat) va cho grid DCA cu.

=> **Pre-reg muc 1.2 da duoc thoa san. KHONG sua gi o duong arm/trailing** (dieu nay giu cong nghiem thu
byte-identical de dat duoc).

### 0.4 Time-stop

`Configs.LOSER_TIME_STOP_HOURS` doc tu `SIM_LOSER_TIME_STOP_HOURS`; nhanh chi chay khi `> 0`.
Dat `=0` trong profile la du de TAT (khong can sua code).

### 0.5 Vi the con mo cuoi ky duoc ghi o dau

Vong ket thuc cua sim duyet `activeRunningIds`, gan `priceTP = lastPrice` cho tung leg roi `putOrderDone(...)`
=> **vi the con mo VAN co trong `printDone.csv`**, MTM theo gia cuoi. NHUNG vong do **KHONG goi
`updatePnl`** => cot `b:` trong `sim.out` (realized) KHONG chua phan nay; no nam o `unP:`.
=> equity cham diem = **`b + unP`** (dung y khuon `ci_bookcap.py`). Kiem chung: `pnl` cua cac cum con mo
trong printDone khop `unP` cuoi ky (muc 4 bang 8c: -17,329 vs unP -17,725 cho E25 — chenh la funding/phi
ghi rieng).

### 0.6 Toi da doi gi (diff: 4 file Java, +87/-2 dong; 0 file selector/gate/bins/242)

| File | Thay doi |
|---|---|
| `tradecore/Configs.java` | +5 key qua `Cfg` (khong doc env): `SIM_DCA_TRIGGER` (bat khi = `BIG_DOWN`), `SIM_DCA_MIN_DROP` (0.20), `SIM_DCA_COOLDOWN_H` (24), `SIM_DCA_MAX_LEGS` (3), `SIM_ENTRY_FRACTION` (1.0). Khong khai = `HOLD_DCA_ON=false` = TAT. |
| `tradecore/DcaUtils.java` | +`shouldDcaHold(avgEntry, lastPrice, priceSL, legCount, lastLegTime, now)`: chua arm (`priceSL == null`) VA `legCount <= MAX_LEGS` VA `lastPrice/avgEntry - 1 <= -MIN_DROP` VA `now - lastLegTime >= COOLDOWN_H`. |
| `tradecore/DcaProcessor.java` | `getDCA` re sang `shouldDcaHold` khi `HOLD_DCA_ON` (truoc nhanh grid). |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | (a) TAT duong `isDcaAlt` khi `HOLD_DCA_ON` => mot co che DCA duy nhat; (b) sizing: `ratio = gridLegWeightRatio(0) * SIM_ENTRY_FRACTION` cho MOI leg (thay `gridLegWeightRatio(legIdx)`); (c) log `[DCA13]` mot dong/leg + dem; (d) mot dong tong ket `[DCA13] TONG ...`. |

**Vi sao KHONG dung `DCA_GRID_WEIGHTS=1,1,1,1`** (pre-reg muc 1.3 co goi y): `managerBudget` chia cho
`dcaGridTotalWeight()`. Doi weights `1,1,3,8` -> `1,1,1,1` lam ladder tut 13 -> 4, tuc C phinh 3.25 lan —
pha dung dieu kien "tran von/coin C giu nhu nay" cua muc 1.4. Nen giu nguyen `DCA_GRID_WEIGHTS`/`SCALE`
trong profile va ep ti trong o ma nguon: moi leg lay `gridLegWeightRatio(0)`.

Ba profile khac `x1_c3_full.properties` **dung 6 dong**: `SIM_LOSER_TIME_STOP_HOURS` 168 -> 0, cong 5 key
HOLDDCA. Ba profile khac NHAU **dung 1 dong**: `SIM_ENTRY_FRACTION` = 0.25 / 0.50 / 1.00 (kiem bang `diff`).

---

## 1. CONG NGHIEM THU (pre-reg muc 1.7) — PASS

Jar MOI (`mvn -DskipTests -o package` rc=0), profile `x1_c3_full.properties` (khong khai key moi),
dir `devrun/X1_HD_OFF`:

| kiem | ket qua |
|---|---|
| `cmp -s <(tail -n +2 X1_HD_OFF/.../printDone.csv) <(tail -n +2 X1_C3_FULL_PARITY_R/.../printDone.csv)` | **rc=0** |
| md5 ca header | `2478e90d4e6147bf4cc64f75967ef47d` hai ben |
| so dong printDone | 2,267 (2,266 lenh) hai ben |
| `b:` cuoi | 111,428 hai ben; `done:339/2266/2266` hai ben |
| so dong `[DCA13]` trong sim.out | **0** |
| `tools/check_cfg_gateway.sh` | OK |

=> khong khai key moi thi jar moi khong doi MOT BIT nao. Duoc phep chay bien the.

---

## 2. BA BIEN THE — equity, CAGR, d CAGR, 5 rate

Equity cham diem = `b + unP` (MTM), ngay cuoi cung co ban ghi = 2025-12-30 (cadence log cua sim),
n = 1,460 ngay = 4.0000 nam. Paired block-bootstrap: block 21 ngay, 2,000 rep, seed 20260903,
k=3 => nguong `1.4823 * sd_boot`.

| tag | entry_frac | eq cuoi (b+unP) | b (realized) | unP | CAGR% | d CAGR (pp) | sd_boot | CI95 | nguong 1.48*sd | ket |
|---|---|---|---|---|---|---|---|---|---|---|
| `X1_C3_FULL_PARITY_R` | — | 111,428 | 111,428 | 0 | +33.58 | — | — | — | — | nen |
| `X1_HD_E25` | 0.25 | **41,117** | 58,842 | -17,725 | +4.11 | **-29.47** | 9.72 | [-49.46, -11.32] | 14.41 | khong vuot |
| `X1_HD_E50` | 0.50 | **37,861** | 56,998 | -19,137 | +1.98 | **-31.59** | 10.23 | [-52.45, -12.66] | 15.16 | khong vuot |
| `X1_HD_E100` | 1.00 | **31,017** | 48,168 | -17,151 | -2.98 | **-36.55** | 10.30 | [-57.47, -17.31] | 15.27 | khong vuot |

`P(d>0)` = 0.001 / 0.001 / 0.000. Do ben theo block: block 10 va 42 cho cung ket luan
(hi95 lan luot -10.99/-13.36 cho E25, -11.52/-13.70 cho E50, -16.36/-18.88 cho E100) — **CI95 tren
nam hoan toan duoi 0 o ca ba do dai block**.

### 5 rate chat luong + CI khoi-72h x1.21 (toan cua so, `x1_rates.py`)

| rate | nen | E25 (hieu, CI) | E50 (hieu, CI) | E100 (hieu, CI) |
|---|---|---|---|---|
| n (leg) | 2,266 | 2,349 (+83, [-72, +243]) | 2,166 (-100, [-340, +113]) | 1,348 (**-918**, [-1385, -522]) |
| win% | 84.69 | 86.04 (+1.35, [-2.15, +4.80]) | 86.01 (+1.32, [-2.75, +5.21]) | 85.91 (+1.22, [-2.97, +5.26]) |
| TSloss% | 14.96 | 0.13 (**-14.83**, [-17.68, -12.18]) | 0.14 (**-14.82**, [-17.67, -12.17]) | 0.22 (**-14.74**, [-17.59, -12.06]) |
| mP\|SM | 7.333 | 8.099 (+0.77, [-1.05, +2.53]) | 9.117 (+1.78, [-0.17, +3.87]) | 11.249 (**+3.92**, [+0.68, +7.66]) |
| mP\|SL | -19.570 | -43.839 (-24.27, [-73.08, +20.81]) | -43.839 (nt) | -43.839 (nt) |
| meanP | 3.308 | 2.185 (-1.12, [-3.75, +1.27]) | 1.795 (-1.51, [-4.31, +1.12]) | 2.337 (-0.97, [-5.27, +3.73]) |
| mMargin | 1,945 | 173 (**-1,772**) | 168 (**-1,777**) | 178 (**-1,767**) |

So rate CHAT LUONG ngoai CI (bo `n`, `mMargin`): **1 / 1 / 2**.

**CANH BAO DOC SO (pre-reg muc 3 da ghi truoc):** `TSloss%` tut 14.96 -> 0.13 la **HE QUA CAU TRUC**
cua viec bo time-stop (chi con 3 lenh `STOP_LOSS_DONE` trong ca 48 thang, thay vi 339), KHONG phai cai
thien. Cung the, `win%` +1.3pp va `mP|SM` cao hon la vi lenh thua **khong bao gio duoc ghi nhan la thua** —
chung nam trong `unP` -17k..-19k. Doc `win%` o day la doc sai. `mMargin` tut 11 lan la vi von bi chia
nho ra nhieu cum om dong thoi, khong phai vi rui ro/lenh giam.

---

## 3. THEO NAM — return, maxDD, quy min, UW, rang buoc cung

Rang buoc cung (pre-reg muc 3, **UW BO theo quyet dinh user 11/09 — chi bao cao**):
`maxDD >= -15%`, `ret_nam >= 0`, `quy_min >= -5%`. Chuoi equity cat trong nam; quy dau tien so voi CAP0=35,000.

| tag | nam | maxDD% | ret_nam% | quy_min% | UW (chi ghi) | rang buoc |
|---|---|---|---|---|---|---|
| PARITY_R | 2022 | -12.46 | +17.30 | +0.63 | 64 | OK |
| PARITY_R | 2023 | -2.51 | +60.43 | +7.80 | 45 | OK |
| PARITY_R | 2024 | -11.36 | +45.36 | -4.64 | 121 | OK |
| PARITY_R | 2025 | -10.60 | +16.45 | -2.47 | 227 | OK |
| **E25** | 2022 | -8.71 | **-5.30** | **-3.87** | 181 | **VI PHAM** (nam am) |
| **E25** | 2023 | -9.42 | +25.89 | -1.32 | 201 | OK |
| **E25** | 2024 | **-15.42** | +15.34 | **-9.56** | 245 | **VI PHAM** |
| **E25** | 2025 | **-17.49** | **-14.38** | **-9.35** | 357 | **VI PHAM** |
| **E50** | 2022 | -14.24 | **-12.97** | **-9.88** | 326 | **VI PHAM** |
| **E50** | 2023 | -12.40 | +28.86 | -1.76 | 205 | OK |
| **E50** | 2024 | **-20.97** | +13.35 | **-14.25** | 251 | **VI PHAM** |
| **E50** | 2025 | **-17.66** | **-14.44** | **-9.43** | 357 | **VI PHAM** |
| **E100** | 2022 | **-20.60** | **-19.80** | **-15.71** | 326 | **VI PHAM** |
| **E100** | 2023 | -11.56 | +22.40 | -2.64 | 229 | OK |
| **E100** | 2024 | **-22.95** | +4.66 | **-16.30** | 279 | **VI PHAM** |
| **E100** | 2025 | **-16.70** | **-13.56** | **-9.76** | 357 | **VI PHAM** |

**Ca ba bien the vi pham 3/4 nam. Nen qua ca 4 nam** (khi UW khong la rang buoc).
maxDD toan cua so: nen -12.46, E25 -18.86, E50 -21.72, E100 -23.50 — **xau di don dieu theo entry fraction**.

maxDD theo nam so voi nen (duong = tot hon): E25 chi tot hon o 2022 (+3.75pp), xau hon 3 nam con lai
(-6.91 / -4.06 / -6.89); E50 xau hon ca 4 nam (-1.78 / -9.88 / -9.61 / -7.06); E100 xau hon ca 4 nam
(-8.14 / -9.05 / -11.59 / -6.10). **Khong co nam nao maxDD tot hon mot cach he thong.**

d CAGR theo nam (chi bao cao, bootstrap trong nam): am o **12/12** o cap (bien the x nam),
tu -22.6pp den -40.3pp; khong o dau vuot nguong.

---

## 4. CO CHE — da duoc thu THAT su chua?

### 4.1 Leg DCA + % cum PST co DCA

| tag | 2022 | 2023 | 2024 | 2025 | TONG 48 thang | usdt/leg TB (2022 -> 2025) | %cum PST co DCA |
|---|---|---|---|---|---|---|---|
| PARITY_R (grid cu) | 0 | 0 | 0 | 0 | **0 leg `[DCA13]`** (54 leg-2+ theo grid cu) | — | 1.95% |
| E25 | 40 | 42 | 121 | 128 | **331** | 212 -> 88 | 8.82% |
| E50 | 44 | 42 | 110 | 102 | **298** | 214 -> 46 | 8.06% |
| E100 | 48 | 45 | 93 | 22 | **208** | 118 -> 9 | 8.69% |

Nguong "co che tro" cua pre-reg muc 4(c) la **< 100 leg / 48 thang**: ca ba deu vuot xa (331/298/208).
Time-stop-off doi **>> 5% lenh**: `STOP_LOSS_DONE` tu 339 xuong **3** o ca ba bien the.
=> **KHONG roi vao cach doc (c). Phep thu da that su duoc chay.**

Chu y `usdt/leg TB` tut manh theo thoi gian (E100: 118 -> 9 USDT): von leg ti le voi equity x throttle,
ma equity giam va `u = margin/equity` tang => `throttle = 1 - u/U_MAX` sat 0 => leg DCA cuoi ky gan nhu
vo nghia. Day la **co che tu bop nghet**, khong phai loi cau hinh.

### 4.2 Von khoa, entries/ngay (PST starvation), vi the mo

| tag | nam | margin TB | margin max | % equity TB | entry (cum)/ngay | open TB | open cuoi nam |
|---|---|---|---|---|---|---|---|
| PARITY_R | 2022 | 1,597 | 17,378 | 4.45 | 1.06 | 1.8 | 0 |
| PARITY_R | 2025 | 10,774 | 60,201 | 10.08 | 2.34 | 3.8 | 1 |
| E25 | 2022 | 6,813 | 12,587 | 19.94 | 0.88 | 26.9 | 47 |
| E25 | 2025 | 19,803 | 24,253 | **44.16** | 2.08 | 109.6 | **195** |
| E50 | 2022 | 10,341 | 16,197 | 32.03 | 0.87 | 30.8 | 55 |
| E50 | 2025 | 22,431 | 23,846 | **55.21** | 1.80 | 134.2 | **195** |
| E100 | 2022 | 12,728 | 17,581 | 42.00 | 0.84 | 33.7 | 63 |
| E100 | 2025 | 19,904 | 21,167 | **60.76** | **0.40** | 132.8 | **128** |

**PST starvation la co that va do duoc**: entries/ngay 2025 tut 2.34 (nen) -> 2.08 / 1.80 / **0.40**.
E100 mo duoc 166 leg trong ca nam 2025 (nen: 884). Ly do co hoc: `u = marginRunning/equity` cham
`U_MAX = 0.60` => `managerBudget` tra `null` => tu choi lenh moi. Day dung la cai counterfactual
offline KHONG mo hinh duoc (pre-reg muc 0, y (a)).

So vi the mo dong thoi (leg): p90 nam 2025 = 195 (E25), 195 (E50), 140 (E100) vs **11.0** o nen;
max ca ky 205 / 204 / 145 vs 30.

### 4.3 Vi the mo cuoi ky + MTM (pre-reg muc 1.5)

| tag | moc dong cuoi | n cum con mo | margin dang khoa | pnl (MTM) cua cum con mo | b cuoi | eq cuoi = b+unP |
|---|---|---|---|---|---|---|
| PARITY_R | 2025-12-24 23:23 | 1 | 3,926 | -547 | 111,428 | 111,428 |
| E25 | 2025-12-31 06:59 | **65** | 24,013 | **-17,329** | 58,842 | **41,117** |
| E50 | 2025-12-31 06:59 | **66** | 23,014 | **-19,195** | 56,998 | **37,861** |
| E100 | 2025-12-31 06:59 | **38** | 19,267 | **-17,379** | 48,168 | **31,017** |

Cach lay MTM (kiem tra tren ma nguon, muc 0.5): vi the con mo **CO** trong `printDone.csv` voi
`priceTP = lastPrice`; `b:` KHONG chua chung; `unP:` chua. Cham diem tren `b+unP` la dung va khong
"giau" khoan lo om. Neu ai do cham tren `b:` khong thoi thi E25 se trong nhu 58,842 — **sai 30%**.

### 4.4 Concentration, collapse-day, coin het gia

| tag | n cum | pnl tong | pnl top-5% cum | % pnl tu top-5% | collapse-day (48 thang) | coin het gia (rate <= -95%) |
|---|---|---|---|---|---|---|
| PARITY_R | 2,212 | +76,428 | +64,458 | **84.3%** | 25 | 0 |
| E25 | 2,018 | +6,513 | +6,607 | **101.4%** | **0** | 2 (0.10%) |
| E50 | 1,868 | +2,803 | +7,725 | **275.6%** | **0** | 4 (0.21%) |
| E100 | 1,140 | -4,210 | +4,486 | **-106.6%** | **0** | 4 (0.35%) |

Concentration **xau di**, khong tot len: o E50 rieng 5% cum tot nhat da gap 2.76 lan tong pnl —
95% cum con lai cong lai la AM. Voi E100 tong pnl da am.

"0 collapse-day" **KHONG** la tin tot: collapse-day dinh nghia la ngay co >= 4 lenh dong
`STOP_LOSS_DONE`, ma bo time-stop thi gan nhu khong con lenh nao dong bang SL — rui ro chuyen tu
"ngay sup do do duoc" thanh "khoan lo om keo dai khong bao gio duoc ghi nhan". Ngay te nhat theo pnl
dong lenh cua ca ba bien the deu la **2025-12-31** (ngay ket so, -17.3k / -19.2k / -17.4k) — dung la
ngay he thong bi ep ghi nhan phan da om.

---

## 5. PHAN QUYET (pre-reg muc 4, doc DUNG nhu da chot)

Quy tac: **PASS <=> (i) `d CAGR > 1.4823 * sd_boot`** (paired, block 21, toan cua so) **VA
(ii) qua HET rang buoc cung o CA 4 NAM** (maxDD >= -15%, nam >= 0, quy >= -5%; UW bo).

| bien the | (i) d vs nguong | (ii) 4 nam | PHAN QUYET |
|---|---|---|---|
| `X1_HD_E25` | -29.47 vs 14.41 -> **KHONG DAT** | 3/4 nam vi pham -> **KHONG DAT** | **KHONG PASS — THUA** |
| `X1_HD_E50` | -31.59 vs 15.16 -> **KHONG DAT** | 3/4 nam vi pham -> **KHONG DAT** | **KHONG PASS — THUA** |
| `X1_HD_E100` | -36.55 vs 15.27 -> **KHONG DAT** | 3/4 nam vi pham -> **KHONG DAT** | **KHONG PASS — THUA** |

**Cach doc (pre-reg muc 4, chon DUNG mot nhanh):**

- **(a) khong ap dung** — 0/3 PASS, khong co nhanh nao mo, **khong de xuat so giay thu 2**, khong doi
  production, khong mo holdout.
- **(c) khong ap dung** — co che DA duoc thu that: 331/298/208 leg `[DCA13]` trong 48 thang (nguong tro
  la < 100), va bo time-stop doi 339 -> 3 lenh `STOP_LOSS_DONE` (>> 5%). Day KHONG phai "chua co phep thu".
- **Nhan "THUA" cua muc 4 ap dung**: `d CAGR` am ro va **CI95 tren < 0** o ca ba bien the, o ca ba do dai
  block (21/10/42). Ghi **THUA thang**, khong phai "khong phan biet duoc".
- **(b)** la khung dong: **DONG nhanh nay**. So de nguoi doc tu can khau vi da ghi day o muc 3-4:
  maxDD toan ky -18.9 / -21.7 / -23.5 (nen -12.5); 2022 am -5.3 / -13.0 / -19.8; 2025 am -14.4 / -14.4 / -13.6;
  concentration top-5% 101 / 276 / -107 %; von khoa TB nam 2025 = 44 / 55 / 61% equity.

**Ket luan huong**: ky vong ghi truoc trong pre-reg muc 0 ("entry nho => PST sleeve co lai ~ti le entry;
DCA sleeve bu khong du; 2022 vi pham rang buoc cung; tong khong phan biet duoc hoac thua") **da dung, va
con manh hon du bao** — khong phai "khong phan biet duoc" ma la thua ro rang, don dieu theo entry fraction.
Huong bien thien cung nhat quan voi co che: entry cang to thi von khoa cang som, PST sleeve
(nguon +59k / 77% pnl cua nen) cang bi boi doi, va E100 mat han sleeve nay o 2025 (0.40 entry/ngay).

---

## 6. NHUNG GI KHONG LAM / KHONG KET LUAN

- **Khong tune sau khi thay so.** 0.07 / 0.5 / 0.80 / 24h / 3 leg / 3 muc entry deu la so chot truoc
  trong `PREREG_HOLDDCA.md` `877694c`. Khong them bien the, khong them bo loc hau kiem.
- **Khong ket luan gi ve "DCA noi chung"**: bai nay do DUNG mot cau hinh (nhip BIG_DOWN 1 phut,
  -20% tren gia von TB, cooldown 24h, 1:1 theo USDT, K=3, khong time-stop). Mot luoi khac (vd giu time-stop
  ma chi them DCA, hoac moc sau hon) CHUA duoc do o day.
- **Khong ket luan `TSloss%` / `win%` / `mP|SM` cai thien** — xem canh bao o muc 2: chung la he qua co hoc
  cua viec bo time-stop, khong phai tin hieu chat luong. Pre-reg muc 3 da ghi truoc dieu nay.
- **Khong ket luan "0 collapse-day = an toan hon"** — xem muc 4.4.
- **Khong chay 2026 / holdout / 242 / `SHADOW_NO_PUSH`.** Khong sua selector, gate, bins, `SELECTOR_RANK_TOPK`,
  `TS_*`, `F_BASE`, `U_MAX`, `NUMBER_ORDER_BUDGET`. Khong rebuild bins hay dataset.
- **Khong doi duong LIVE.** `gridLegWeightRatio` va `managerBudget` giu nguyen; nhanh moi trong
  `createOrderBUY` chi ton tai o `SimulatorMarketLevelTicker1MStopLoss` (sim). Khong khai key => byte-identical
  (muc 1).
- **Khong xoa dir devrun cua nguoi khac.** Bon dir moi: `X1_HD_OFF`, `X1_HD_E25`, `X1_HD_E50`, `X1_HD_E100`.
- **Khong khang dinh nguyen nhan duy nhat**. Ba kenh cung chay mot luc (bo time-stop; DCA them von; entry
  nho lai) va thiet ke nay **khong tach duoc** dong gop tung kenh. Cai do duoc: huong tong hop la am, va
  `entry/ngay` + `%equity khoa` cho thay kenh "budget bi bag chiem" la co that. Muon tach kenh phai co
  pre-reg khac (vd chi bo time-stop, giu DCA cu).

---

## 7. TAI LAP

```bash
# 1) build
cd /home/ubuntu/src/BinanceFuturesJava
PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH mvn -DskipTests -o package
bash tools/check_cfg_gateway.sh

# 2) cong nghiem thu (phai byte-identical voi X1_C3_FULL_PARITY_R)
bash /home/ubuntu/x1log/run_hd.sh X1_HD_OFF  profiles/x1_c3_full.properties
cmp -s <(tail -n +2 /home/ubuntu/java/devrun/X1_HD_OFF/storage/printDone.csv) \
       <(tail -n +2 /home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv); echo rc=$?

# 3) ba bien the (1 slot java, tuan tu; ~13.5 phut/run)
for v in 25 50 100; do
  bash /home/ubuntu/x1log/run_hd.sh X1_HD_E$v profiles/x1_holddca_e$v.properties
done

# 4) cham
cd research/analysis
python3 ci_holddca.py X1_HD_E25 X1_HD_E50 X1_HD_E100     # -> /home/ubuntu/x1log/ci_holddca.out
for v in 25 50 100; do python3 x1_rates.py X1_C3_FULL_PARITY_R X1_HD_E$v; done
```

`run_hd.sh` = khuon `runx()` cua `research/pipeline/x1/run_x1_sim.sh` (env `WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1
WFO_SMART_CACHE=1 SIM_END_DATE=20251231 EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json
TRADING_PROFILE=<profile>`, `java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g`), them 2 dong kiem `[DCA13]`.

| artifact | duong dan |
|---|---|
| pre-reg | `docs/PREREG_HOLDDCA.md` (`877694c`) |
| profile | `profiles/x1_holddca_e25.properties`, `_e50`, `_e100` |
| script cham | `research/analysis/ci_holddca.py` (khuon `ci_bookcap.py`, them muc 5/8/9) |
| run | `/home/ubuntu/java/devrun/X1_HD_OFF`, `X1_HD_E25`, `X1_HD_E50`, `X1_HD_E100` |
| log cham | `/home/ubuntu/x1log/ci_holddca.out`, `rates_HD_E{25,50,100}.out` |
| PROFILE_HASH | E25 `1db263c983c65fef`, E50 `3ef05f2e9413ae65`, E100 `68dedd0049f6db1c`, C3 `135750e04d67c263` |
| md5 printDone | E25 `f96f2db3c7f4e2e9db2d2340b51c2d76`, E50 `e66a1c2e3fb68dc8ffb6a1425b7d1308`, E100 `2b0f7fefd75c43acc0672ebb6e73a96a` |
