# T2B_FULLFLOW — luong DAY DU voi SIZE DUOC BU: selector C2b vs selector cu

Tiep noi `docs/experiment/T2_FULLFLOW.md`. T2 do duoc phep so selector trong luong day du **o mot diem
van hanh gan nhu vo hieu** (`mean(margin)` 971 -> 9.21, CAGR 0.36%) nen ket qua "khong phan
biet duoc" cua no khong tra loi duoc cau hoi. T2b chay lai voi `DCA_GRID_SCALE` **duoc bu**.

Pre-reg `docs/prereg/PREREG_T2B.md` commit `0058c35` **TRUOC khi chay**. DEV 2022-01-01..2024-06-30.
Khong chay VAL. jar `binance-java-sdk-1.2.4.jar` sha256 `09417d3e…`, code `6a9fdad`.
Oracle + `TICKER_SOURCE=aerospike` cho ca 4 chan (khong ghep moi truong — `RUNBOOK bay #7`).

---

## 0. RUI RO / DOC SO CHO DUNG — truoc moi thu

1. **`DCA_GRID_SCALE=253.5` chua tung ai chay.** Mien da tham truoc day la 1.5 / 2.0.
   Moi ket luan o day gan voi dung gia tri nay.
2. **`T2b_full_old` khac `T2b_full_c2b` o HAI bien** (bins `G015_v2` + gate calib 0.014052),
   da ghi truoc (`PREREG_T2B muc 0.4`). Nen doc "selector cu" o day la **goi bins + hieu chuan
   gate cua no**, khong phai chi bins. Chenh lech tan suat (2,666 vs 1,068 lenh) la **mot phan
   cua goi do**, khong phai loi do luong.
3. **Sizing van khong do duoc tren DEV** (`RUNBOOK muc 4`). Khac T2 o cho: bay gio hai chan
   duoc do **o cung mot muc tieu kiem soat** (`mean(margin)` leg 1 ~ 971), nen so sanh giua
   chung khong con bi confound sizing — nhung so tuyet doi cua tung chan van la ham cua size.
4. `E[max nhieu]` equity N=4 = **4.28pp CAGR**. Equity bao rieng, khong phai tieu chi.
5. **Khong de cu ung vien baseline moi** (pre-reg muc 0.7).

---

## 1. CONG THUC SIZE — he so 105x den tu dau

### 1.1 Duong di cua mot leg

`SimulatorMarketLevelTicker1MStopLoss.createOrder` (dong 875-903):

```java
Float budget = BudgetManagerSimple.getInstance().getBudget();          // (1) THAM SO CHET
budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);
budget *= tierMultiplier;                                              // TIER_FLAT=1 -> 1.0
if (Configs.DCA_GRID_ENABLED) budget *= DcaUtils.gridLegWeightRatio(legIdx);
quantity = Utils.calQuantityTest(budget, leverage, entry, symbolStr);  // LEVERAGE_ORDER=1
```

(1) `getBudget()` tra `BUDGET_PER_ORDER = balanceBasic/50 = 700`, **nhung `managerBudget`
khong doc tham so `budget`** — no la tham so chet. Con so `BASE_BUDGET = 35000/50 = 700`
ghi trong comment cua `c2b_min.properties` **khong con anh huong gi den size**.

`TradeUtils.managerBudget` (FROZEN v1 2026-08-24, `TradeUtils.java:53-64`):
```java
float u = marginRunning / balanceBasic;
if (u >= Configs.U_MAX) return null;                        // U_MAX = 0.60 (hardcode)
float throttle = clamp(1f - u/U_MAX, 0, 1);
float ladder = Configs.dcaGridTotalWeight();                // <<< CHIA TONG TRONG SO, LAN 1
return balanceBasic * Configs.F_BASE * throttle / ladder;   // F_BASE = 0.03 (hardcode)
```

`DcaUtils.gridLegWeightRatio` (`DcaUtils.java:47-54`):
```java
return (w[legIdx] / Configs.dcaGridTotalWeight()) * Configs.DCA_GRID_SCALE;  // <<< LAN 2
```

### 1.2 Ghep lai — tong trong so bi chia **HAI LAN**

```
margin(leg i) = balanceBasic x F_BASE x throttle x DCA_GRID_SCALE x w[i] / total^2
              = 35000 x 0.03 x throttle x SCALE x w[i] / total^2
```

`balanceBasic` **la hang so** `Configs.capitalStart()` = 35000 — khong doan nao trong duong
sim ghi lai no (`grep 'balanceBasic *='` chi ra HPO + checker) => **size KHONG compound**.

| | `1,0,0,0` (`c2b_min`) | `1,1,3,8` (T2/T2b) |
|---|---|---|
| `total` | 1 | 13 |
| `total^2` | 1 | **169** |
| he so leg 1 | `1050 x throttle x SCALE` | `1050 x throttle x SCALE / 169` |

**He so danh mac dinh la 169 = 13^2, KHONG phai 13.** Truc giac "tong weight 13 nen leg dau
con 1/13 suat budget" (dung trong `T2_FULLFLOW muc 5` va trong the mo cua `W1_SWEEP muc 10`,
de xuat `scale ~ 1.5 x 13 = 19.5`) **bo sot lan chia thu nhat** trong `managerBudget`.
Comment trong code goi lan chia do la "chua cho du ladder DCA" — nhung `gridLegWeightRatio`
da chia roi, nen thanh chia doi. **Dinh chinh `W1_SWEEP muc 10` va `T2_FULLFLOW muc 5`:
scale bu dung la 253.5, khong phai 19.5.**

### 1.3 Vi sao DO duoc 106 chu khong phai 169 — `throttle` noi lai 1.59x

`throttle` la vong phan hoi: size nho => `marginRunning` nho => `u` nho => `throttle` -> 1.

| | `T2_c2b_ref` | `T2_full_c2b` |
|---|---|---|
| `mean(margin)` **leg 1** do duoc | **971.0515** | **9.1440** |
| he so cong thuc (SCALE=1.5) | 1575 | 9.31953 |
| => `throttle` ngu y | **0.61654** | **0.98116** |
| => `u = U_MAX(1-throttle)` | 0.23008 (`marginRunning` ~ 8,053) | 0.01130 (~ 395) |

```
169 / (0.98116 / 0.61654) = 169 / 1.59137 = 106.19
do truc tiep:  971.0515 / 9.1440           = 106.19    <- khop tuyet doi
```
(Con so **105.45** cua `T2_FULLFLOW` la `mean(margin)` TOAN BO — thap hon 106.19 vi leg 2+
mang trong so 1/3/8 nen nang hon leg 1.)

**=> 105x = 169x (binh phuong tong trong so) chia 1.59x (throttle noi lai vi gan nhu khong
dung von). Khong con he so an nao khac.**

### 1.4 Scale can de dua leg 1 ve ~971

O cung `throttle`: `1050 x SCALE / 169 = 1050 x 1.5 / 1` => **`SCALE = 1.5 x 169 = 253.5`**.

---

## 2. HIEU CHUAN — **PASS lan dau, KHONG dung quyen sua**

Cong da chot truoc (`PREREG_T2B muc 2`): `mean(margin)` leg 1 cua `T2b_full_c2b` phai nam
trong ±20% cua 971.05, tuc **[776.84 , 1165.26]**.

| lan | `DCA_GRID_SCALE` | `mean(margin)` leg 1 do duoc | lech vs 971.05 | ket qua |
|---|---|---|---|---|
| **1** | **253.5** | **947.0018** | **-2.48%** | **TRONG CONG — dung lai** |
| 2 | *khong dung* | — | — | quyen sua 1-lan **con nguyen** |

`throttle` thuc te tut ve 0.60127 (tu 0.98116) dung nhu du bao ghi truoc o pre-reg muc 1.3,
va rot sat gia tri cua chan ref (0.61654) — chenh 2.5% la do 120 leg BIG_DOWN + 21 leg DCA
2+ (trong so 1/3/8) an them margin.

**Scale 253.5 duoc ap Y HET cho ca 3 chan** (`full_c2b`, `full_old`, `dca_c2b`) — khong hieu
chuan rieng tung chan. Kiem chung: `mean(margin)` leg 1 = 947.00 / 750.65 / 960.62. Chan
`full_old` thap hon 21% **khong phai vi duoc hieu chuan khac**, ma vi no mo 2.5 lan so lenh
=> `marginRunning` cao hon => `throttle` thap hon. Do chinh la vong phan hoi o muc 1.3, va la
mot **he qua co hoc cua selector+gate cu**, khong phai mot bien tu do.

---

## 3. PARITY

| tag | md5 `printDone.csv` | b | n |
|---|---|---|---|
| neo `C2b` (`RUNBOOK muc 3`) | `8f7afdfb27b15f5b6d4c886700def93c` | 60390 | 970 |
| **`T2b_c2b_ref` (= tai dung `T2_c2b_ref`)** | **`8f7afdfb27b15f5b6d4c886700def93c`** | **60390** | **970** |

**PARITY OK — byte-identical.** Tai dung hop le: jar sha256 `09417d3e…` khong doi,
`find src -newer <jar> -name '*.java'` **rong**, git tree sach truoc khi chay
=> khong ton mot run cho parity.

md5 cac chan T2b: `T2b_full_c2b` `fe4d686ab2c4d616a737d8a14404ef82` ·
`T2b_full_old` `5acd7997c317f5a965b628e6f88d27d8` · `T2b_dca_c2b` `902698545c90cf0d85a49cf9403bdf1e`.

Dataset: `wfo_ds_clean` (`fundingPredDir=/home/ubuntu/predwf_map_s1a2`) cho `full_c2b`+`dca_c2b`;
`wfo_ds_t2old` build rieng (`fundingPredDir=/home/ubuntu/predwf_G015_v2`,
`md5(funding.bin)=f6f088f02e360964783d66e32b488399` — **trung y het** dataset ma T2 da build
cho `T2_full_old`, xac nhan duong build deterministic), **da `rm -rf` sau khi chay** (dia 14G free).

**Runs da dung: 3/4** (parity tai dung). Quyen hieu chuan: **0/1**.

---

## 4. BANG RATE PRIMARY

| | `T2b_c2b_ref` | **`T2b_full_c2b`** | **`T2b_full_old`** | `T2b_dca_c2b` |
|---|---|---|---|---|
| big_down | tat | **bat** | **bat** | tat |
| DCA `1,1,3,8` | tat | **bat** | **bat** | **bat** |
| `DCA_GRID_SCALE` | 1.5 | **253.5** | **253.5** | **253.5** |
| selector | S1 `map_s1a2` | S1 `map_s1a2` | **`G015_v2` + gate 0.014052** | S1 `map_s1a2` |
| **n lenh** | 970 | 1068 | **2666** | 1015 |
| **TSloss%** | 15.155 | 15.356 | **20.143** | 15.370 |
| **win%** | 85.258 | 85.112 | **80.645** | 84.631 |
| **mean(profit\|STOP_MARKET_DONE)** | 7.476 | 7.375 | 7.078 | 7.358 |
| **mean(profit\|STOP_LOSS_DONE)** | -18.896 | **-15.947** | **-20.800** | -16.371 |
| mean(profit) toan bo | 3.479 | **3.793** | **1.452** | 3.711 |
| median(profit) | 5.50 | 5.50 | 5.50 | 5.50 |
| **mean(margin) leg 1** | 971.05 | **947.00** | **750.65** | 960.62 |
| mean(margin) toan bo | 971.05 | 938.93 | 746.74 | 952.42 |
| **total margin deployed** | 941,920 | **1,002,773** | **1,990,801** | 966,703 |

### 4.1 Phan bo status (day du)

| tag | `STOP_MARKET_DONE` | `STOP_LOSS_DONE` (time-stop 168h) | khac |
|---|---|---|---|
| `T2b_c2b_ref` | 823 (84.85%) | 147 (15.15%) | — |
| `T2b_full_c2b` | 904 (84.64%) | 164 (15.36%) | — |
| `T2b_full_old` | 2128 (79.82%) | 537 (20.14%) | **`REQUEST` 1 (0.04%)** |
| `T2b_dca_c2b` | 859 (84.63%) | 156 (15.37%) | — |

Khong sinh status exit moi. `REQUEST` 1/2666 = lenh chua dong toi `SIM_END_DATE` (giong T2).

### 4.2 Nguon leg entry + so leg DCA thuc thi theo level

| tag | `PREDICT_SYMBOL_TRADE` | `BIG_DOWN` | `DCA_LEVEL1` | leg 1 | leg 2 | leg 3 | leg 4 |
|---|---|---|---|---|---|---|---|
| `T2b_c2b_ref` | 970 | 0 | 0 | 970 | 0 | 0 | 0 |
| `T2b_full_c2b` | 927 | **120** | 21 | 1047 | **17** | **4** | 0 |
| `T2b_full_old` | 2501 | **120** | 45 | 2621 | **34** | **7** | **4** |
| `T2b_dca_c2b` | 994 | 0 | 21 | 994 | **17** | **4** | 0 |

`BIG_DOWN` = **dung 120 leg o ca 3 chan bat no**, y het T2 — tin hieu sinh tu
`marketData.rateDownAvg` (toan thi truong), khong phu thuoc selector.

**DCA hau nhu khong bao gio cham**: 21 leg / 1068 (1.97%) o C2b, 45 / 2666 (1.69%) o G015_v2.
Bac -50% cham 17-34 lan, -75% cham 4-7 lan, -90% cham 0-4 lan trong 2.5 nam. Bu size **khong**
lam DCA cham nhieu hon (21 leg o T2 = 21 leg o T2b) — luoi `-50/-75/-90%` moi la cai chan.

### 4.3 **PnL TACH THEO LEG LEVEL** — DCA kiem tien hay do them vao lenh thua?

| tag | n leg 1 | `sum(pnl)` leg 1 | n leg 2+ | **`sum(pnl)` leg 2+** | `mean(profit%)` leg 1 | `mean(profit%)` leg 2+ |
|---|---|---|---|---|---|---|
| `T2b_c2b_ref` | 970 | 25,391 | 0 | — | 3.479 | — |
| **`T2b_full_c2b`** | 1047 | 26,411 | 21 | **+3,398** | 3.511 | **+17.898** |
| **`T2b_full_old`** | 2621 | 11,879 | 45 | **-4,239** | 1.534 | **-3.317** |
| `T2b_dca_c2b` | 994 | 25,619 | 21 | **+3,177** | 3.436 | **+16.715** |

**Dau cua PnL leg 2+ DAO CHIEU theo selector.** Tren bins C2b, 21 leg DCA lai **+3,398 USD**
(11.4% tong PnL cua chan, tren 2.0% so leg) voi `mean(profit%)` **+17.9** — cao gap 5 lan leg 1;
dung nhu thiet ke ("ha gia von cua cum dang thua roi thoat khi hoi"). Tren bins cu, 45 leg DCA
**mat -4,239 USD** — chinh la kieu "do them vao lenh thua". Tai lap leg index: gom `(sym, end)`,
kiem chung so dong `leg>=1` = so dong `level=DCA_LEVEL1` **khop 100%** o ca 4 chan (21/21,
45/45, 21/21, 0/0).

⚠️ n = 21 va 45. **Khong du de ket luan gi ve DCA tu rieng cot nay** — day la mo ta, khong
phai bang chung. No chi duoc dung lam **dieu kien can** cua cau phu (muc 6.2).

---

## 5. CI 95% block-bootstrap 72h x1.21 (4000 rep, seed 7, hai mau doc lap)

### 5.1 CAU CHINH — `T2b_full_c2b` - `T2b_full_old`

| rate | `full_c2b` | `full_old` | hieu | CI | ket qua |
|---|---|---|---|---|---|
| `TSloss%` | 15.356 | 20.143 | -4.787 | [-9.807, +0.148] | trong CI (cham bien) |
| `win%` | 85.112 | 80.645 | +4.467 | [-0.450, +9.552] | trong CI (cham bien) |
| `mean(profit\|SM)` | 7.375 | 7.078 | +0.296 | [-0.921, +1.642] | trong CI |
| `mean(profit\|SL)` | -15.947 | -20.800 | +4.853 | [-1.377, +10.585] | trong CI |
| **`mean(profit)`** | 3.793 | 1.452 | **+2.341** | **[+0.302, +4.388]** | **KHAC** |
| **`mean(margin)`** | 938.93 | 746.74 | **+192.19** | **[+57.10, +320.39]** | **KHAC** |

**2/6 rate ngoai CI, ca hai cung dau (+, tuc nghieng ve C2b)** => theo luat da dang ky
(`>= 2 rate cung huong ngoai CI`) => **KHAC NHAU**.

⚠️ **Doc cho dung ca hai:** `mean(margin)` la **bien kiem soat**, khong phai bien chat luong.
No lech vi `full_old` mo 2.5 lan so lenh => `marginRunning` cao hon => `throttle` thap hon
(muc 1.3), **KHONG** phai vi no duoc hieu chuan khac (cung `SCALE=253.5`). Vay bang chung
**chat luong** thuc su chi la `mean(profit)` (+2.34pp). Bon rate con lai deu nghieng ve C2b
va hai trong so do (`TSloss%` -4.79, `win%` +4.47) **cham bien CI** — nhat quan voi T2 nhung
van chua qua nguong rieng le.

### 5.2 CAU PHU — `T2b_dca_c2b` - `T2b_c2b_ref` (bat rieng DCA, big_down van tat)

| rate | `dca_c2b` | `c2b_ref` | hieu | CI | ket qua |
|---|---|---|---|---|---|
| `TSloss%` | 15.369 | 15.155 | +0.215 | [-5.802, +6.180] | trong CI |
| `win%` | 84.631 | 85.258 | -0.627 | [-6.729, +5.675] | trong CI |
| `mean(profit\|SM)` | 7.358 | 7.476 | -0.118 | [-1.985, +1.665] | trong CI |
| `mean(profit\|SL)` | -16.371 | -18.896 | +2.526 | [-5.531, +10.601] | trong CI |
| `mean(profit)` | 3.711 | 3.479 | +0.231 | [-2.470, +2.958] | trong CI |
| `mean(margin)` | 952.42 | 971.05 | -18.64 | [-139.09, +100.65] | trong CI |

**0/6 rate ngoai CI.**

### 5.3 Doi chieu — `T2b_full_c2b` - `T2b_c2b_ref` (bat CA HAI co che, vs ref)

| rate | `full_c2b` | `c2b_ref` | hieu | CI | ket qua |
|---|---|---|---|---|---|
| `TSloss%` | 15.356 | 15.155 | +0.201 | [-5.691, +6.074] | trong CI |
| `win%` | 85.112 | 85.258 | -0.145 | [-6.018, +5.814] | trong CI |
| `mean(profit\|SM)` | 7.375 | 7.476 | -0.101 | [-1.785, +1.574] | trong CI |
| `mean(profit\|SL)` | -15.947 | -18.896 | +2.949 | [-4.652, +10.871] | trong CI |
| `mean(profit)` | 3.793 | 3.479 | +0.314 | [-2.161, +2.885] | trong CI |
| `mean(margin)` | 938.93 | 971.05 | -32.13 | [-149.69, +88.32] | trong CI |

**0/6 rate ngoai CI.** Bat ca big_down lan DCA (o size da bu) **khong phan biet duoc voi
`c2b_min` tren rate** — nhat quan voi tung co che bat rieng (muc 5.2 va `T2_full_c2b_noDCA`).
Bang nay **khong** nam trong quy tac quyet dinh da dang ky; ghi de doi chieu.

---

## 6. RANG BUOC CUNG (maxDD <= 15% · UW <= 120 ngay · khong nam am · khong quy < -5% · n >= 600)

| tag | maxDD% | UW (ngay) | nam am | quy min | n | ket qua |
|---|---|---|---|---|---|---|
| `T2b_c2b_ref` | -13.1 | 93 | khong | -3.7 (2022Q4) | 970 | **PASS** |
| **`T2b_full_c2b`** | **-11.5** | **81** | khong | **-1.4** (2024Q2) | 1068 | **PASS** |
| **`T2b_full_old`** | **-41.6** | **390** | **-29.7% (2022)** | **-27.3** (2022Q2) | 2666 | **FAIL 4/4** |
| `T2b_dca_c2b` | -11.6 | 81 | khong | -1.6 (2024Q2) | 1015 | **PASS** |

Loi nhuan theo nam: `c2b_ref` 11.6 / 45.4 / 6.3 · `full_c2b` **22.5 / 41.5 / 6.8** ·
`full_old` **-29.7 / 65.5 / 4.8** · `dca_c2b` 21.9 / 41.6 / 5.6.

`T2b_full_old` **FAIL ca bon rang buoc**, khong phai mot. Do la ket qua **rat khac T2**, noi
ca hai chan cung "PASS mot cach rong" vi khong giao dich bang tien (maxDD -0.1 / -0.4).
Voi size that, chan bins cu **vo 2022Q2 -27.3%** va mat 390 ngay duoi dinh.

---

## 7. PHAN QUYET

### 7.1 CAU CHINH — `T2b_full_c2b` vs `T2b_full_old`: **KHAC. Selector C2b THANG.**

Hai duong doc lap cung tra ve mot ket qua:
1. **Rate**: 2/6 rate PRIMARY ngoai CI cung huong (`mean(profit)` +2.34pp,
   `mean(margin)` +192) => vuot nguong `>= 2` da dang ky.
2. **Rang buoc cung**: `T2b_full_old` **FAIL 4/4** (maxDD -41.6, UW 390 ngay, nam 2022
   -29.7%, quy 2022Q2 -27.3%) => bi loai truc tiep, bat ke rate (`PREREG_T2B muc 6`).

**Dieu da doi so voi T2 la DUY NHAT mot thu: size.** Cung jar, cung code, cung bins, cung
gate, cung dataset, cung cong CI. T2 ket luan "khong phan biet duoc" (1/6) vi ca hai chan
chay o ~1% von — o do moi hieu ung bi nen xuong duoi nguong do duoc. Bu `DCA_GRID_SCALE`
tra lai bien do that va **phep so tro nen co nghia**. Do la bai hoc phuong phap chinh cua T2b:
**mot phep so o diem van hanh sai co the tra ve null ma khong phai vi hai vat giong nhau.**

**Gioi han cua ket luan nay** (ghi dam, khong duoc bo khi trich):
- "Selector cu" o day la **goi `predwf_G015_v2` + gate 0.014052**, hai bien. Khong tach duoc
  phan nao la bins, phan nao la hieu chuan gate. Muon tach phai co chan thu ba.
- `predwf_G015x26` (ban goc that su cua "selector cu") **khong tai lap duoc**; `G015_v2` la
  ban dung lai. Ket luan gan voi `G015_v2`.
- Chi mot `DCA_GRID_SCALE` (253.5), mot realization DEV. maxDD/UW/nam la single-realization,
  `n_eff` nho (`RUNBOOK muc 4`) — nhung o day chung khong quyet dinh mot minh, rate cung chi
  cung huong.
- 2022 lam gan het viec: bo 2022 ra thi hai chan gan bang nhau o 2023-2024 (41.5+6.8 vs
  65.5+4.8, ban cu con **cao hon**). Day **dung la** hinh dang ma `SELECTOR_LADDER_Q` da canh
  bao ("78% uu the C2b nam trong 2022"). => **Uu the cua C2b trong luong day du van la mot
  hien tuong 2022.** Khong duoc doc no nhu "C2b tot hon o moi regime".

### 7.2 CAU PHU — DCA co dang bat khong? **KHONG ĐANG** (theo luat da dang ky)

`T2b_dca_c2b` vs `T2b_c2b_ref`: **0/6 rate ngoai CI** => khong dat dieu kien `>= 2 rate`.
Dieu kien thu hai (`sum(pnl)` leg 2+ duong) **DAT** (+3,177 USD). Thieu mot trong hai
=> **khong dang bat**. Ket luan la **KHONG PHAN BIET DUOC tren rate**, khong phai "co hai".

**Bon quan sat de lai (mo ta, khong phai phan quyet):**
- `mean(profit|STOP_LOSS_DONE)` -18.90 -> **-16.37** (bot lo 2.53pp). Day la lan **thu hai**
  hieu ung nay xuat hien — `W1_SWEEP muc F` da thay -18.90 -> -18.09 -> -17.37 don dieu theo
  ti trong DCA. Lan nay o **cung muc size** (960.6 vs 971.1, lech 1.1%) nen **khong con giai
  thich duoc bang sizing**. Van trong CI ([-5.53, +10.60]) — chua phai bang chung.
- maxDD -13.1 -> **-11.6** va UW 93 -> **81 ngay** o `total margin deployed` **cao hon** 2.6%.
  Khac T2/W1 (o do maxDD giam chi vi lenh nho di), lan nay khong phai artifact sizing.
  Nhung maxDD/UW la single-realization => khong du de doi baseline.
- **DCA chi no trong quy sap, khong no luc nao khac.** Phan bo 21 leg 2+ cua `dca_c2b`:
  **2022Q2 13 leg (+947 USD) · 2022Q4 6 leg (+2,339) · 2024Q2 2 leg (-109)** — 0 leg trong
  suot 2023. Quy 2022Q4 di tu **-3.7% -> +3.7%** (ref -1,513 USD -> dca +1,534, chenh +3,047)
  va rieng PnL leg 2+ quy do la **+2,339** = ~77% cua chenh lech. Nhung do la **mot quy,
  6 leg** — `n_eff` = 1, khong phai bang chung.
  Doi chieu `full_old`: 45 leg cung don ve 2022Q2 (23 leg, **-3,573**) va 2022Q4 (7 leg,
  **-1,478**) => **cung co che, dau nguoc**, tuy selector.
- **Ghep voi chan big_down-mot-minh cua T2** (`T2_full_c2b_noDCA`, 0/6 rate ngoai CI): **ca
  hai co che, bat rieng le, deu KHONG phan biet duoc voi `c2b_min` tren rate.** Bat CA HAI
  (`T2b_full_c2b`) cung cho **0/6** so voi ref (do that, muc 5.3).

### 7.3 Khong de cu ung vien baseline moi

Dung `PREREG_T2B muc 0.7`. `T2b_full_c2b` co equity cao hon ref nhung nam trong mien nhieu
(muc 8) va khong phan biet duoc voi ref tren rate.

---

## 8. EQUITY — **KHONG PHAI TIEU CHI**

`E[max nhieu]` N=4 = `2.57 x sqrt(2 ln 4)` = **4.28pp CAGR**. So CAGR/Sharpe lay tu
`/home/ubuntu/java/fsrun/ev.sh` (2.49 nam).

| tag | equity cuoi | CAGR | Sharpe(quy) | quy duong | vs `c2b_ref` | trong nhieu 4.28pp? |
|---|---|---|---|---|---|---|
| **`T2b_full_c2b`** | **64,809** | **28.05%** | **1.28** | 9/10 | +3.57pp | **CO — khong ket luan duoc** |
| `T2b_dca_c2b` | 63,796 | 27.25% | 1.24 | 9/10 | +2.77pp | **CO** |
| `T2b_c2b_ref` | 60,390 | 24.48% | 0.95 | 8/10 | 0 | — |
| `T2b_full_old` | 42,687 | **8.30%** | **0.15** | 7/10 | **-16.18pp** | KHONG — da bi loai o muc 6 |

Equity cuoi nam: `full_c2b` 42,891 / 60,694 / 64,809 · `dca_c2b` 42,649 / 60,406 / 63,796 ·
`c2b_ref` 39,073 / 56,830 / 60,390 · **`full_old` 24,622 / 40,746 / 42,687**.

`T2b_full_old` mat **-9,912 USD trong 2022Q2** va cham day maxDD **-41.57% ngay 2022-11-10**
(dot FTX). `open-end 1 MTM -197$` = dong `REQUEST`; log sim ghi `b:42836`, `ev.sh`/`qret.py`
doc 42,687 tu `printDone.csv`. Ca hai cho cung phan quyet.

## 9. SAI LECH SO VOI PRE-REG (ghi de minh bach)

- Dung **3/4 run** da dang ky (`T2b_c2b_ref` tai dung `T2_c2b_ref` sau khi kiem jar sha256 +
  `find src -newer` rong, dung nhu pre-reg muc 3 cho phep). Khong them chan nao sau khi thay so.
- **Quyen hieu chuan 1-lan KHONG duoc dung** — lan chay dau da trong cong (947.00 / 971.05,
  lech -2.48%, cong ±20%).
- `T2b_full_old` khac `T2b_full_c2b` o **2 bien** — ghi truoc o pre-reg muc 0.4.
- CI: block-bootstrap 72h, **hai mau doc lap** (so lenh khac nhau 1068 vs 2666 nen khong ghep
  cap), 4000 rep, noi rong nua-do-rong x1.21, seed 7. Script `research/analysis/t2b_cmp.py`,
  metric `research/analysis/t2b_legs.py`.
- Moi run tren Oracle + `TICKER_SOURCE=aerospike`. **Khong day chan nao len Kaggle** — chan
  `full_old` phai build dataset o Oracle (bay #13) va `RUNBOOK bay #7` cam ghep hai moi truong
  trong mot phep so, nen de 3 chan cung mot noi. (Pre-reg cho phep Kaggle lam probe hieu chuan;
  khong can dung vi lan chay dau da PASS.)
- Khong chay VAL. Khong push. `wfo_ds_t2old` da `rm -rf`, dia 14G free.
