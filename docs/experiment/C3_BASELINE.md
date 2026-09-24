# C3_BASELINE — sua 3 bug B1/B2/B3, do lai baseline

Pre-reg `5a001e5` (`docs/prereg/PREREG_C3.md`), commit TRUOC khi chay. 5 arm chay SONG SONG tren
Kaggle CPU (5/5 slot cung `RUNNING` — lan dau do duoc tran 5 that su).
Jar `5a001e5`, md5 `710f6c7f457607a7d36f3764d36a9612`. `tools/check_cfg_gateway.sh` OK.
`mvn test` **17/17 PASS**, `mvn -DskipTests package` BUILD SUCCESS.

---

## 0. RUI RO / CANH BAO — doc TRUOC

1. 🔴 **`C2b` = 60390 tu day chi con la SO LICH SU.** Baseline moi la `C3` = **68,278**.
   Khong ghep cap so cu (E1/W1/T1/T2/T2b) voi so moi trong cung mot so sanh.
2. 🔴 **`C3_mom006` VI PHAM 3/4 rang buoc cung** (maxDD −20.75, UW 133, quy 2024Q2 −8.3).
   Khong phai ung vien. Chi dung de tra loi cau gate.
3. ⚠️ **Du doan ghi truoc cua toi SAI mot nua.** Toi doan `TSloss%` va `win%` se la 2 rate
   vuot CI. Thuc te ca hai **KHONG** vuot CI; hai rate vuot lai la `n` va `mean(margin)` —
   deu la bien **KIEM SOAT/co hoc**, khong phai bang chung chat luong. Ghi nguyen van muc 6.
4. ⚠️ **`maxDD` in trong log sim (`unProfitMin/35000`) MAT Y NGHIA duoi compound.** Moi so
   maxDD/UW trong doc nay lay tu **chuoi equity** (`(s/s.cummax()-1)`, `s = b+unP` cuoi ngay).
   Kiem chung: cach tinh nay cho `C3_REGRESS` = **−13.12% / 93 ngay**, **trung khop tuyet doi**
   so C2b lich su => thang do dung.
5. ⚠️ **B1 lam GIAM equity khi dung mot minh** (60,395 -> 59,722). Toan bo phan tang cua `C3`
   den tu **B3 (compound)**. Neu ai doc luot va quy cong cho B1 thi doc nguoc.
6. ⚠️ Equity/CAGR **khong phai tieu chi** (`sd(dCAGR)` = 2.57pp).

---

## 1. CONG HOI QUY — **PASS TUYET DOI**

Arm `C3_regress` = jar MOI + 16 key `c2b_min` nguyen ven + 3 co `false`:

| do | ky vong | thuc te | ket qua |
|---|---|---|---|
| equity | 60395 | **60395** | ✅ |
| so lenh | 970 | **970** | ✅ |
| md5 `printDone.csv` | `910f1aa6f76b5e6797d97a31a7ea5f5a` | **`910f1aa6f76b5e6797d97a31a7ea5f5a`** | ✅ **byte-identical** |
| maxDD / UW | −13.12% / 93 | **−13.12% / 93** | ✅ |

=> **Ba sua khong cham vao mot nhanh nao ngoai y dinh.** Day la dieu kien tien quyet de moi
so con lai trong doc nay co nghia. `PROFILE_HASH` Kaggle `1b50c3aacb79c259` khac `c2b_min`
(them 3 key) — **binh thuong**, khong dung lam bang chung parity (bay #11).

---

## 2. BA SUA — tom tat diff

| bug | file | thay doi | co |
|---|---|---|---|
| **B1** | `SimulatorMarketLevelTicker1MStopLoss.mergeOrder()` | them `orderResult.symbolPred = clusterSymbolPred(time2Order.values())`; them helper `clusterSymbolPred()` = leg co pred **KHONG-NULL DAU TIEN theo thoi gian**; `private` -> package-private de test | `SIM_FIX_B1` |
| **B2** | `DcaUtils.gridLegWeightRatio()` | `return w * SCALE` thay `return (w/total) * SCALE` — **bo lan chia thu hai**, GIU lan chia trong `managerBudget` | `SIM_FIX_B2` |
| **B3** | `BudgetManagerSimple.equityNow()` (moi) + `Simulator.createOrder` | goc sizing = `balanceCurrent + unProfit` thay hang so `capitalStart()` | `SIM_FIX_B3` |

**Vi sao B1 lay "leg dau CO pred" chu khong phai "leg dau"/"leg cuoi":** chi leg
`PREDICT_SYMBOL_TRADE` mang `symbolPred`; leg `BIG_DOWN` (call-site 275) va `DCA_LEVEL1`
(283/299) mang `null` vi **bo qua gate AI**. Lay leg cuoi => moi cum co DCA lai ve `null` =>
rot dung lai bug cu. Do thuc o arm `C3_FULL`: **120 leg no-pred** = dung 120 leg `BIG_DOWN`
ma `T2`/`T2b` da dem — luat chon nay giu duoc pred cho 917/1037 cum, thay vi mat het.

**Vi sao B2 sua o `DcaUtils` chu khong o `managerBudget`:** duong **LIVE**
`DetectEntrySignal2TradeNormal:556` goi `managerBudget` nhung **khong bao gio** goi
`gridLegWeightRatio`, ma `DCA_GRID_WEIGHTS` mac dinh khi thieu key la `1,1,3,8` (total=13).
Sua o `managerBudget` se **phong to lenh LIVE 13 lan**. Sua o `DcaUtils` => **LIVE khong doi
mot bit**.

**Cap cua B3:** `1575` **chua bao gio la hang so trong code** — no la
`equity x F_BASE x DCA_GRID_SCALE = 35000 x 0.03 x 1.5`. Thay `35000` bang equity thi cap
**tu dong** thanh **4.5% equity hien tai**; khong sua them dong nao. Unit test khoa
(`at70k/70000 == 0.045`).

### Unit test (17/17 PASS)
- `FixB1SymbolPredTest` (4): leg DCA/BIG_DOWN khong xoa pred; leg som nhat thang; all-null ->
  null (= hanh vi cu); **hau qua len `trailRate`**: `pred=null` va `pred=0.50` -> WEAK chot
  `0.27`, `pred=0.12` -> **STRONG chot `0.22`** (arm 30%).
- `FixB2LadderDivisionTest` (3): `1,0,0,0` FIX on/off **ra cung mot so** (1575);
  `1,1,3,8` leg-1 = **1/13** mot-leg sau sua vs **1/169** truoc sua, ty so **13.000**;
  day ladder = `equity x F_BASE x SCALE`.
- `FixB3EquityCompoundTest` (5): `equityNow` = realized+unrealized; guard equity <= 0;
  size tuyen tinh theo equity (x2 khi equity x2); cap luon 4.5%; `U_MAX` do tren cung goc.
- `DcaGridScalarTest` (5): test cu `weightRatioSumsToScale` **da thay** bang
  `clusterExposureIsBudgetTimesScale` — khang dinh cu (`sum(ratio)==SCALE`) chinh la
  **bat bien cua cai bug**; do o muc TICH (ratio x budget) moi dung.

---

## 3. NAM ARM — bang chinh

`equity`/`CAGR` **KHONG phai tieu chi**, de o cot cuoi.

| arm | co bat | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `C3_REGRESS` | — (cong) | 970 | 85.26 | 15.15 | 7.476 | −18.896 | 3.479 | 971 | −13.12 | 93 | 60,395 | 24.48 |
| `C3_B1ONLY` | B1 | 961 | 85.12 | 15.30 | 7.452 | −18.827 | 3.432 | 973 | −13.60 | 95 | 59,722 | 23.92 |
| **`C3` (`C3_BASE`)** | **B1+B2+B3** | **961** | **85.12** | **15.30** | **7.452** | **−18.827** | **3.432** | **1,397** | **−13.31** | **96** | **68,278** | **30.76** |
| `C3_FULL` | +big_down+DCA | 1,059 | 84.89 | 15.77 | 7.190 | −16.236 | 3.496 | 1,410 | −12.46 | 81 | 72,699 | 34.10 |
| `C3_MOM006` | gate 0.006 | 1,592 | 82.54 | 18.28 | 7.258 | −18.476 | 2.554 | 1,210 | −20.75 | 133 | 67,147 | 29.89 |

**Doc bang nay dung cach — 3 quan sat cau truc:**

1. **`C3_BASE` va `C3_B1ONLY` co RATE GIONG HET NHAU** (n, win%, TSloss%, mP|SM, mP|SL, meanP,
   ca phan bo winner). Chi `mMargin` doi (973 -> 1,397). => **B3 khong doi MOT quyet dinh vao/ra
   nao**, no chi doi THANG DO. Day la xac nhan sach nhat co the cho rang B3 duoc cai dung cho:
   compound tac dong qua size, khong ro ri sang logic.
   (`u = marginRunning/equity` giu throttle gan nhu bat bien nen tap lenh khong doi.)
2. **B1 mot minh gan nhu KHONG doi rate** (n 970->961, win 85.26->85.12, TSloss 15.15->15.30)
   nhung **doi HINH DANG phan bo winner** (muc 4). Equity **giam** 60,395 -> 59,722.
3. `C3_FULL` co `mean(profit|SL)` **−16.236** vs −18.827 (**+2.59pp**) — manh sach nhat cua DCA,
   dung mach `W1` truc F va `T2b` da thay, **lan nay o cung muc size** (leg-1 margin lech +2.2%).

---

## 4. PHAN BO PROFIT CUA WINNER — truoc/sau B1

Day la thu B1 that su doi. Doc theo cap **`C3_REGRESS` (truoc) -> `C3_B1ONLY` (sau)**:
hai chan chi khac DUNG MOT co, cung sizing, cung gate.

| arm | n_win | p10 | p25 | **med** | p75 | **p90** | max |
|---|---|---|---|---|---|---|---|
| `C3_REGRESS` (100% WEAK, cap 3%) | 827 | **4.459** | **4.993** | **5.999** | **8.107** | 11.000 | 207.00 |
| `C3_B1ONLY` (71.5% STRONG, cap 8%) | 818 | **3.500** | **4.000** | **5.000** | **7.496** | **12.064** | 207.00 |
| `C3` (= B1ONLY + size) | 818 | 3.500 | 4.000 | 5.000 | 7.496 | 12.064 | 207.00 |
| `C3_FULL` | 899 | 3.500 | 4.000 | 5.490 | 7.499 | 12.482 | 207.00 |
| `C3_MOM006` | 1,314 | 3.988 | 4.368 | 5.487 | 7.498 | 11.762 | 207.00 |

**Hinh dang doi dung nhu co che, khong phai dich len/xuong dong deu:**

- **Phan than TUT**: p10 −0.96pp, p25 −0.99pp, med −1.00pp, p75 −0.61pp.
- **Duoi phai DAY LEN**: p90 **+1.06pp** (11.000 -> 12.064).
- `max` khong doi (207.00) — cung mot lenh cuc dai.

**Co che (khong phai suy dien, la so hoc cua cong thuc exit):**
`exit = peak − min(peak x 0.5, cap)`.
- Voi `peak < 2 x cap` thi nhanh `peak x 0.5` chay va **STRONG = WEAK**.
  Nguong: WEAK `2 x 0.03 = 6%`, STRONG `2 x 0.08 = 16%`.
- Voi `peak` trong khoang **6% .. 16%**: WEAK chot `peak − 3%`, STRONG chot `peak − 8%`
  => **STRONG chot THAP hon dung 5pp**. Do la toan bo phan than tut.
- Doi lai, cap rong hon **khong stop-out som** o cac nhip hoi giua duong => mot phan lenh
  song sot toi `peak` cao hon => **duoi phai day len**.

**=> Ban le STRONG/WEAK la mot danh doi MEDIAN doi DUOI, khong phai mot cai tien.**
Tren DEV no gan nhu trung hoa o muc rate (win% −0.14pp, TSloss% +0.15pp, mP|SM −0.024pp) va
**hoi am o equity** (−673, tuc −1.1%, nam gon trong nhieu 2.57pp).
Dieu quan trong hon con so: **truc `SIM_TS_MAX_GAP` / `SIM_TS_PNOPUMP_WEAK_THR` bay gio DA SONG**
(truoc la key chet) — `W1` truc A va C co the quet lai, hien van la vung trang.

### Nhanh trailing thuc su chay

| arm | STRONG (pred <= 0.29) | WEAK | no-pred | STRONG% |
|---|---|---|---|---|
| `C3_REGRESS` | (695) | (275) | 0 | **0% THUC TE** — engine bo qua cot nay, 100% WEAK |
| `C3_B1ONLY` / `C3` | **687** | 274 | 0 | **71.5%** |
| `C3_FULL` | 672 | 245 | **120** (leg BIG_DOWN) | 64.8% |
| `C3_MOM006` | 1,044 | 548 | 0 | 65.6% |

⚠️ Dong `C3_REGRESS` de trong ngoac co chu dich: cot `symbolPred` trong `printDone.csv` van co
so THAT ke ca truoc khi sua (`closeOrder()` ghi tu object LEG), nen bang phan loai van tinh ra
695/275 — **nhung engine chua bao gio doc no**. Day dung la cai bay da lam `W1` mat 5 run:
**nhin CSV se tuong trailing da dung `symbolPred`.**

---

## 5. `mean(margin)` THEO NAM — phep kiem B3

| arm | 2022 | 2023 | 2024 | leg-1 | n_leg1 | n_DCA |
|---|---|---|---|---|---|---|
| `C3_REGRESS` (khong compound) | 892.0 | 1,120.3 | **924.5** | 971.05 | 970 | 0 |
| `C3_B1ONLY` (khong compound) | 895.1 | 1,120.5 | **926.1** | 973.15 | 961 | 0 |
| **`C3` (compound)** | **891.8** | **1,609.2** | **1,785.2** | 1,397.41 | 961 | 0 |
| `C3_FULL` | 855.9 | 1,688.3 | 1,812.5 | **1,428.01** | 1,037 | 22 |
| `C3_MOM006` | 737.9 | 1,444.9 | 1,546.9 | 1,209.52 | 1,592 | 0 |

**B3 XAC NHAN.** Hai chan khong compound co margin **quay dau** o 2024 (1,120 -> 924/926) vi
mau so co dinh 35,000 va throttle dao theo muc su dung von. Chan compound **tang don dieu**
892 -> 1,609 -> 1,785 (**x2.00 tu 2022 den 2024**), bam sat duong equity (35,000 -> 68,278,
x1.95). Do la dung hanh vi phai co, va **truoc dot nay he chua bao gio co no**.

Ghi chu doc so: `mean(margin)` 2022 gan nhu **giong het** o ca 3 chan (891.8 / 892.0 / 895.1) —
dung nhu ky vong: dau ky equity chua kip khac 35,000 nen compound chua co gi de compound.

### Cong hieu chuan `C3_FULL` — **PASS lan dau, KHONG dung quyen sua**

Cong chot truoc (`PREREG_C3` muc 3.1): leg-1 `mean(margin)` cua `C3_FULL` phai trong **±20%**
cua `mean(margin)` arm `C3`.

| | gia tri |
|---|---|
| muc tieu (`C3` mMargin) | **1,397.41** |
| cong ±20% | [1,117.93 , 1,676.89] |
| do duoc (`C3_FULL` leg-1) | **1,428.01** |
| lech | **+2.19%** | 
| ket qua | ✅ **TRONG CONG** — quyen sua 1-lan con nguyen |

**`DCA_GRID_SCALE = 19.5`** (= `1.5 x 13`) la con so DUNG sau khi sua B2. So **253.5** cua
`T2B_FULLFLOW` (= `1.5 x 169`) **bu cho chinh cai bug**; dung no sau B2 se phong to size 13 lan.
=> **`W1_SWEEP muc 10` (de xuat 19.5) hoa ra DUNG**, va `T2B_FULLFLOW muc 1.4` (253.5) dung
**cho engine cu**. Ca hai deu khong sai — chung noi ve hai engine khac nhau.

---

## 6. RANG BUOC CUNG — `C3` co duoc nhan lam baseline khong?

| arm | maxDD ≤15% | UW ≤120d | khong nam am | khong quy < −5% | KET QUA |
|---|---|---|---|---|---|
| `C3_REGRESS` | −13.12 ✅ | 93 ✅ | ✅ | −3.7 ✅ | PASS |
| `C3_B1ONLY` | −13.60 ✅ | 95 ✅ | ✅ | −4.0 ✅ | PASS |
| **`C3`** | **−13.31 ✅** | **96 ✅** | **✅ (9.5/64.3/8.4)** | **−4.8 ✅** | ✅ **PASS 4/4** |
| `C3_FULL` | −12.46 ✅ | 81 ✅ | ✅ (17.3/60.4/10.4) | −4.6 ✅ | PASS 4/4 |
| `C3_MOM006` | **−20.75 ❌** | **133 ❌** | ✅ (1.2/72.3/10.0) | **−8.3 ❌** | **FAIL 3/4** |

### ✅ `C3` DAT HET RANG BUOC CUNG => **duoc nhan lam baseline moi.**

**Nhung phai bao 2 dieu, khong duoc lam tron:**

1. 🔴 **`C3` sat bien o rang buoc quy: −4.8% vs tran −5.0%** (2024Q2). Bien an toan **0.2pp**.
   `C2b` cu o −3.7%. Compound **da an gan het bien do**. Mot chan tuong tu chi can xau hon
   chut la vuot. **Day khong phai "PASS thoai mai".**
2. ⚠️ **Compound day DD len dung nhu canh bao ghi truoc, nhung it hon du kien**: maxDD
   −13.12 -> −13.31 (**+0.19pp**), UW 93 -> 96 (**+3 ngay**). Ly do no khong te hon: throttle
   `1 − u/U_MAX` tu dieu tiet — equity to hon thi `u` nho hon thi size to hon, vong lap tu can
   bang. **`U_MAX` dang lam dung viec cua no.**
   maxDD theo nam: 2022 −13.3 / 2023 −2.6 / 2024 **−11.1** (chan khong compound: −6.4).
   => phan DD tang ro nhat nam o **2024**, dung nam von da lon nhat. Do la chu ky ma compound
   se tiep tuc khuech dai neu DEV keo dai them.

**KHONG TUNE.** Khong ha `F_BASE`, khong ha `U_MAX`, khong doi `DCA_GRID_SCALE`.
`C3` PASS nen khong co gi de bao cao cho user quyet — nhung neu user muon bien an toan lon hon
o rang buoc quy thi **do la nut risk preference cua user**, khong phai bai toan toi uu
(`RUNBOOK muc 4`, `QUEUE Q5`).

---

## 7. CAU GATE — `C3_mom006` vs `C3`

Block-72h bootstrap, 2000 rep, CI x1.21, seed 20260905, luoi khoi CHUNG (paired).

| rate | hieu (mom006 − C3) | CI lo | CI hi | ngoai CI? |
|---|---|---|---|---|
| `n` | **+631.0** | +475.8 | +778.3 | ✅ **CO** |
| `mean(margin)` | **−187.9** | −295.7 | −75.7 | ✅ **CO** |
| `win%` | −2.582 | −5.711 | +0.642 | — |
| `TSloss%` | +2.982 | −0.324 | +6.284 | — |
| `mean(profit\|SM)` | −0.194 | −0.869 | +0.367 | — |
| `mean(profit\|SL)` | +0.351 | −3.011 | +3.454 | — |
| `meanP` | −0.878 | −1.990 | +0.239 | — |

**Phan quyet theo luat da chot (>= 2 rate ngoai CI): KHAC.**

**Nhung phai doc ky, va day la phan quan trong hon phan quyet:**
**hai rate vuot CI (`n`, `mean(margin)`) la HAI MAT CUA CUNG MOT SU KIEN CO HOC** — noi gate
=> nhieu lenh hon => `marginRunning` cao hon => `throttle` thap hon => margin/lenh nho hon.
Chung **khong phai bang chung ve CHAT LUONG lenh**. Toan bo 5 rate chat luong (`win%`,
`TSloss%`, `mP|SM`, `mP|SL`, `meanP`) deu co CI **chua 0**. Day dung la canh bao ma
`T2B_FULLFLOW` da ghi ("`mean(margin)` la bien KIEM SOAT").

**Duong doc lap va dut khoat hon: `C3_mom006` FAIL 3/4 rang buoc cung** (maxDD −20.75%,
UW 133 ngay, 2024Q2 −8.3%) => **loai truc tiep, khong can den CI.** Trung khop voi so cu tren
jar hong (maxDD −21.1%) => ket luan nay **khong phu thuoc vao 3 bug**.

### DU DOAN GHI TRUOC — **SAI MOT NUA, ghi nguyen van**

> Du doan (`PREREG_C3` muc 6): "KHAC, huong XAU HON... `TSloss%` **TANG** va `win%` **GIAM**
> (>= 2 rate cung huong xau)."

- ✅ **Dung ve DAU**: `TSloss%` +2.98 (tang), `win%` −2.58 (giam) — ca hai dung huong xau.
- ❌ **SAI ve DO LON / ve rate nao vuot CI**: **ca hai KHONG vuot CI**. Toi da danh gia qua cao
  power cua hai rate do. Hai rate vuot CI lai la `n` va `margin`, ma toi **khong** du doan.
- ✅ Dung du doan phu: `n` tang (961 -> 1,592), maxDD xau di (−13.31 -> −20.75).

**Bai hoc ghi lai:** voi `n` thay doi 65% thi rate quality bi pha loang manh va CI no ra
(`win%` CI rong 6.35pp) — **CI cua rate quality khong co power khi mau so doi manh**.
Cac dot sau doi truc lam doi `n` nhieu nen do them mot dai luong **khong phu thuoc `n`**.

**Ket luan cho cau hoi goc ("gate co bo khong" tren jar DA SUA): gate 0.008 KHONG bo qua chat.**
Noi ra 0.006 mua them 631 lenh nhung **khong** mua duoc cai thien chat luong nao do duoc, va
**tra bang** maxDD −20.75% + UW 133 ngay. `B1` khong doi cau tra loi nay, dung nhu co che da
ghi truoc: nhom lenh bien chet bang **time-stop 168h**, ma B1 chi tac dong **sau khi arm +7%**.

---

## 8. RETURN THEO QUY (%)

| arm | 22Q1 | 22Q2 | 22Q3 | 22Q4 | 23Q1 | 23Q2 | 23Q3 | 23Q4 | 24Q1 | 24Q2 |
|---|---|---|---|---|---|---|---|---|---|---|
| `C3_REGRESS` | 0.7 | 4.4 | 10.2 | −3.7 | 7.4 | 15.4 | 8.1 | 8.6 | 7.8 | −1.4 |
| `C3_B1ONLY` | 0.9 | 2.2 | 11.7 | −4.0 | 7.3 | 15.6 | 9.3 | 7.8 | 8.0 | −2.3 |
| **`C3`** | **0.6** | **1.5** | **12.6** | **−4.8** | **8.3** | **19.1** | **13.4** | **12.3** | **13.6** | **−4.6** |
| `C3_FULL` | 0.6 | 2.4 | 11.9 | **1.8** | 7.8 | 18.1 | 11.3 | 13.2 | 15.8 | −4.6 |
| `C3_MOM006` | −1.1 | −1.1 | 10.7 | −6.6 | 16.0 | 13.8 | 13.2 | 15.3 | 20.0 | −8.3 |

Quy >= +5%: **6/10** o ca 5 chan (khong doi). 2 quy lien tiep >= +5%: **4** o ca 5 chan.
Nam >= +30%: chi **2023** o ca 5 chan. Nam am: **khong chan nao**.

**Hinh dang KHONG doi, chi bien do gian ra** — dung dac trung cua mot thay doi thang do:
`C3` giu nguyen dau cua ca 10 quy so `C3_REGRESS`, chi khuech dai (2023Q2 15.4 -> 19.1,
2024Q1 7.8 -> 13.6, va 2022Q4 −3.7 -> −4.8 / 2024Q2 −1.4 -> −4.6). **Compound khuech dai CA
HAI CHIEU** — do chinh la ly do bien an toan o rang buoc quy bi an mon (muc 6).

---

## 9. KET LUAN

1. ✅ **Cong hoi quy PASS byte-identical** => 3 sua khong ro ri sang nhanh khac.
2. ✅ **`C3` = baseline moi: 68,278 / CAGR 30.76% / maxDD −13.31% / UW 96d / n=961**,
   `profiles/c3_min.properties`, md5 `printDone` `38be0cb3195984e1000e61d9cdef54da`.
   PASS 4/4 rang buoc cung, **nhung sat bien o quy (−4.8 vs −5.0)**.
3. **Toan bo phan tang la B3 (compound), khong phai B1.** B1 mot minh: −673 equity.
   B3 khong doi mot rate nao, chi doi thang do — xac nhan sach.
4. **B1 doi HINH DANG phan bo winner**: than tut ~1pp (p10/p25/med), duoi phai len +1.06pp
   (p90). Danh doi median-doi-duoi, khong phai cai tien. **Truc A/C cua `W1` gio DA SONG.**
5. **Cau gate: KHAC theo luat, nhung 2 rate vuot CI deu la bien co hoc.** `C3_mom006`
   **FAIL 3/4 rang buoc cung** => loai. Gate 0.008 khong bo qua chat.
6. `C3_FULL` (big_down + DCA, size da bu dung 19.5) PASS 4/4 va co `mean(profit|SL)`
   **−16.24 vs −18.83** — manh sach nhat cua DCA tu truoc toi nay, **o cung muc size**.
   **KHONG de cu lam baseline** (pre-reg muc 7 cam) — nhung day la the mo manh nhat con lai.

### The mo sau dot nay
- **Quet lai `W1` truc A (`SIM_TS_MAX_GAP`) va C (`SIM_TS_PNOPUMP_WEAK_THR`)** — vua song,
  hien la vung trang. Ban le 0.29 nam giua dai van hanh (71.5% STRONG / 28.5% WEAK).
- **`C3_FULL` xung dang mot pre-reg rieng**: 4/4 rang buoc, UW 81 (tot nhat trong 5 chan),
  `mean(profit|SL)` +2.59pp. Can kiem xem phan cai thien den tu DCA hay tu 120 leg BIG_DOWN.
- Do lai `E1` (time-stop horizon) tren engine da sua — ket luan cu sinh tu engine 100% WEAK.

### Do lai tren engine moi (no ky thuat)
Moi ket luan cua `E1`/`W1`/`T1`/`T2`/`T2b` deu sinh tu engine co 3 bug. Phan lien quan den
**trailing** (E1, W1 A/B/C, T2b DCA) can do lai; phan lien quan den **selector/gate/label**
(T1, T2, F1-F4, G1) it kha nang doi vi chung khong di qua `trailRate` hay sizing — nhung
**chua kiem chung**, khong duoc coi la da xac nhan.

---

## 10. PHU LUC — CI cho ba phep so bo tro

Cung phuong phap muc 7 (block 72h, 2000 rep, x1.21, seed 20260905, luoi khoi chung).

### (a) Hieu ung THUAN cua B1 — `C3_B1ONLY` − `C3_REGRESS`

| rate | hieu | lo | hi | ngoai CI? |
|---|---|---|---|---|
| `win%` | −0.138 | −0.329 | +0.047 | — |
| `TSloss%` | +0.142 | −0.049 | +0.336 | — |
| `mean(profit\|SM)` | −0.024 | −0.388 | +0.417 | — |
| `mean(profit\|SL)` | +0.069 | −0.020 | +0.211 | — |
| `meanP` | −0.047 | −0.351 | +0.333 | — |
| `mean(margin)` | +2.103 | −3.503 | +7.281 | — |

**0/7 rate ngoai CI => B1 KHONG PHAN BIET DUOC tren rate.**
Nhung phan bo winner **CO** doi (muc 4) — do la dai luong PHAN BO, khong nam trong danh sach
rate. **Bai hoc: "null tren rate" khong dong nghia "khong doi gi"** — dung mach ma `T1` da ghi
("null o rank-IC KHONG dong nghia vo hai").
Y nghia thuc: sua B1 **an toan** (khong lam xau rate nao) va **mo lai 2 truc quet da chet**.

### (b) Hieu ung THUAN cua B3 — `C3` − `C3_B1ONLY`

| rate | hieu | lo | hi | ngoai CI? |
|---|---|---|---|---|
| `n`, `win%`, `TSloss%`, `mP\|SM`, `mP\|SL`, `meanP` | **0.000 (tat ca)** | 0.000 | 0.000 | — |
| `mean(margin)` | **+424.256** | +287.347 | +561.992 | ✅ CO |

🔴 **Hieu bang KHONG TUYET DOI o moi rate muc lenh, chi `mean(margin)` doi.**
Day la xac nhan manh nhat co the co cho rang **B3 duoc cai dung cho**: compound di qua
DUNG MOT kenh (thang do), **khong ro ri sang mot quyet dinh vao/ra nao**. Ky thuat: `throttle`
= `1 − marginRunning/(equity x U_MAX)`; ca tu va mau cung nhan len theo equity nen throttle
bat bien => cung tap tick, cung tap lenh, cung thoi diem thoat.

### (c) `C3_FULL` − `C3` (big_down + DCA, size da bu)

| rate | hieu | lo | hi | ngoai CI? |
|---|---|---|---|---|
| `n` | +98.0 | +41.0 | +168.0 | ✅ CO |
| `mean(profit\|SL)` | **+2.591** | **+0.035** | +5.841 | ✅ CO |
| `win%` | −0.228 | −1.211 | +0.849 | — |
| `TSloss%` | +0.473 | −1.329 | +2.015 | — |
| `mean(profit\|SM)` | −0.262 | −0.758 | +0.165 | — |
| `meanP` | +0.063 | −0.314 | +0.439 | — |
| `mean(margin)` | +12.2 | −35.5 | +64.9 | — |

**2/7 ngoai CI => KHAC.** Lan dau tien `mean(profit|STOP_LOSS_DONE)` cua nhanh DCA vuot CI
(**+2.59pp**, CI `[+0.035, +5.841]`) — o **cung muc size** (`mean(margin)` +12.2, CI chua 0,
tuc bien kiem soat DA duoc khoa). Truoc day (`W1` truc F, `T2b`) manh nay luon **trong CI**
hoac bi confound sizing.
⚠️ Nhung CI **cham 0** (`lo = +0.035`) => bang chung **yeu**, va `n` cung doi (+98) nen mau so
khong on. **KHONG de cu baseline** (pre-reg muc 7). Day la ung vien pre-reg tiep theo,
phai tach rieng **DCA** voi **120 leg BIG_DOWN**.
