# PREREG_C3 — sua 3 bug (B1/B2/B3) va DO LAI baseline

Commit TRUOC khi chay. Khong sua file nay sau khi thay ket qua.
Doc `docs/AGENT_RUNBOOK.md` (luat cung + 14 bay) va `docs/QUEUE.md` muc BUGS truoc.

**Day KHONG phai mot cuoc thi.** Khong co "arm thang". Muc dich duy nhat: **do lai baseline**
sau khi sua 3 bug ma user da quyet sua. `C2b` (60390) tu day chi con la **so lich su**;
khong giu jar cu lam neo song song.

---

## 0. RUI RO / CANH BAO — doc TRUOC

1. 🔴 **`C2b` khong con la neo song song.** Sau khi bat 3 co, moi so cu (`C2b`, `E1`, `W1`,
   `T1`, `T2`, `T2b`) sinh ra tu mot engine KHAC. **Khong duoc ghep cap so cu voi so moi**
   trong cung mot so sanh — dung cai bay ma `N4_a8s175` da dinh (`W1_SWEEP` truc G).
2. 🔴 **Mo ta exit trong `AGENT_RUNBOOK muc 3` va `C2B_SPEC` LA SAI cho sim truoc fix B1.**
   Ca hai ghi "cap 0.08 STRONG / 0.03 WEAK, ban le `symbolPred < 0.29`". Thuc te nhanh STRONG
   **chua bao gio chay**. Sau B1 mo ta do moi dung. `C2B_SPEC` se duoc dan banner SUPERSEDED.
3. 🔴 **Ban le nguoc voi truc giac.** Code: `pNoPump > THR(0.29)` -> **WEAK** (cap 0.03);
   `pNoPump <= 0.29` -> **STRONG** (cap 0.08). Ma **88.55% hang duoc admit co score < 0.30**
   (`QUEUE Q2`) => sau B1 **da so lenh di nhanh STRONG**, khong phai thieu so.
   Cap LON = cho nha nhieu hon = trailing LONG hon (chot THAP hon o cung dinh), **khong phai**
   "chot cao hon". Huong tac dong len `mean(profit|SM)` that su khong doan duoc truoc.
4. 🔴 **`maxDD` bao trong log sim MAT Y NGHIA khi compound.** `Simulator` in
   `unProfitMin / balanceBasic` voi `balanceBasic` con la hang so 35000. Duoi B3 mau so do
   khong con la equity => ty le in ra bi PHONG DAI theo thoi gian.
   => **Rang buoc cung dung maxDD tu CHUOI EQUITY** (`qret.py`: `(s/s.cummax()-1)`, `s` = `b+unP`
   cuoi ngay), la dai luong bat bien theo thang do. So raw cua log bao cao rieng, dan nhan.
5. ⚠️ **B3 lam DD nang len la KHA NANG THAT** — compound bom size vao dung luc equity cao,
   nen sut sau do lon hon ve tuyet doi. Neu `C3` vi phat rang buoc cung: **BAO, KHONG TUNE.**
   Ghi nguyen van "he compound that vi pham rang buoc, can user quyet `F_BASE`".
   Tuyet doi khong ha `F_BASE`/`U_MAX` sau khi thay so — do la sin (`RUNBOOK muc 0.3`).
6. ⚠️ **Equity KHONG phai tieu chi** (`sd(dCAGR)` = 2.57pp, DEV da ~125 run). Bao cao rieng.
7. ⚠️ **`n` co the doi manh** => moi rate deu doi mau so. Doc rate kem `n`, khong doc roi.

---

## 1. BA SUA — quyet dinh va LY DO (chot truoc khi chay)

### B1 — `mergeOrder()` khong chep `symbolPred`

`SimulatorMarketLevelTicker1MStopLoss.mergeOrder()` tao object CUM moi;
`OrderTargetInfoTest.trailRate()` chay tren CHINH object cum va co fallback
`pnp = (symbolPred != null) ? symbolPred : 1f`. `1f > 0.29` luon dung => **100% lenh WEAK**.

**Chon leg nao?** -> **leg co `symbolPred` KHONG-NULL DAU TIEN theo thu tu thoi gian tang dan.**

Ly do (khong phai tuy chon):
- Chi leg vao qua selector (`PREDICT_SYMBOL_TRADE`, call-site 348) mang `symbolPred`.
  Leg `BIG_DOWN` (275) va `DCA_LEVEL1` (283/299) duoc tao voi `symbolPred = null` vi chung
  **BO QUA gate AI**.
- Lay **"leg cuoi"** (nhu `symbol`/`timeStart`/`marketLevelChange` dang lam) se nhan `null`
  o **moi cum co DCA** => roi dung lai bug cu. Loai.
- Lay **"leg dau"** thuan cung hong khi leg dau la `BIG_DOWN`. Loai.
- **"Leg dau co pred"** = dac trung selector cua cum tai luc MO, **bat bien qua DCA** — dung
  nguyen tac da ap cho `firstEntryPrice` va `clusterFirstLegTime` ngay ben tren trong cung ham.
- Moi leg null -> gan `null` => y het hanh vi cu, khong sinh nhanh moi.

Trong `c2b_min` moi cum chi co **1 leg** (`DCA_GRID_WEIGHTS=1,0,0,0` + `SELECTOR_ONLY_ENTRY=1`)
nen ba lua chon trung nhau; khac biet chi hien o arm `C3_full`.

### B2 — tong trong so DCA bi chia HAI LAN

`TradeUtils.managerBudget:62` chia `/dcaGridTotalWeight()` VA `DcaUtils.gridLegWeightRatio:53`
chia tiep => `margin(leg i) ~ w[i]/total^2` (169 thay vi 13 voi luoi `1,1,3,8`).

**Chon BO lan chia o `DcaUtils.gridLegWeightRatio`, GIU lan chia trong `managerBudget`.**

Ly do (khong phai tuy chon): duong **LIVE** `DetectEntrySignal2TradeNormal:556` goi
`managerBudget` nhung **KHONG BAO GIO** goi `gridLegWeightRatio`; ma `DCA_GRID_WEIGHTS` mac dinh
khi thieu key la `"1,1,3,8"` (total=13). Sua o `managerBudget` se **phong to lenh LIVE 13 lan**.
Sua o `gridLegWeightRatio` => **LIVE khong doi mot bit nao**, chi duong sim (noi duy nhat goi ham
do) duoc sua.

**Kiem da chay (unit test `FixB2LadderDivisionTest`, PASS):**
- `1,0,0,0` (total=1): FIX on/off ra **cung mot so** (1575 @equity 35000) — day la ly do C2b
  khong bao gio thay bug.
- `1,1,3,8`: leg-1 = **1/13** cua mot-leg (truoc: 1/169); ty so `fixed/buggy` = **13.000**.
- Cham day ladder: tong exposure cum = `equity x F_BASE x SCALE` = 1575 (khong phinh).

### B3 — `balanceBasic` la hang so 35000 => khong compound

**Goc sizing doi thanh `BudgetManagerSimple.equityNow()` = `balanceCurrent + unProfit`**
(`balanceCurrent` = von + realized; `unProfit` = unrealized cum dang chay).

Ly do chon cap nay chu khong phai `balanceBasic + profit + unProfit`: **ca hai duoc ghi CUNG MOT
LUC** trong `updateBalance()` => anh chup NHAT QUAN, khong dem trung phan vua chuyen tu unrealized
sang realized (`profit` cong ngay luc dong lenh, `unProfit` chi refresh theo tick).
Cadence: `updateBalance` goi moi GIO va moi nua dem (`Simulator` 366/376) trong khi lenh mo theo
phut => gia tri tre **toi da 1 gio**, tuc **thuan qua khu, KHONG look-ahead**.

Ap cho CA HAI ve trong `managerBudget`: `budget = equity x F_BASE x throttle / ladder` VA
`u = marginRunning / equity` (tran `U_MAX` cung do tren equity — nhat quan, khong lech pha).

**Giu `F_BASE=0.03`, `U_MAX=0.6`.**
**CAP: chon 4.5% EQUITY HIEN TAI (giu nguyen ti le), khong phai 1575 tuyet doi.**
Ghi ro: **1575 chua bao gio la mot hang so trong code** — no la HE QUA cua
`equity x F_BASE x DCA_GRID_SCALE = 35000 x 0.03 x 1.5`. Thay `35000` bang equity thi cap tu dong
thanh 4.5% equity; khong can sua them dong nao. Unit test khoa dieu nay
(`at70k/70000 == 0.045`).

Duong LIVE **khong doi**: `DetectEntrySignal2TradeNormal` truyen `BudgetManager.balanceBasic`
rieng cua no, khong di qua `equityNow()`.

---

## 2. CONG HOI QUY — quan trong hon moi phep do khac

Ba co `SIM_FIX_B1` / `SIM_FIX_B2` / `SIM_FIX_B3`, **mac dinh `true`**, khai bao trong profile
(tien to `SIM_` => bat buoc qua profile, khong dat qua env — bay #2).

**Arm `C3_regress`** = `profiles/c3_regress.properties` (16 key cua `c2b_min` GIU NGUYEN TUNG
BYTE + 3 co `false`), chay tren **jar MOI**.

**Tieu chi PASS (khong co vung xam):**

| duong | equity | n | md5 `printDone.csv` |
|---|---|---|---|
| Kaggle / Oracle+`file` (neo cua duong nay) | **60395** | 970 | `910f1aa6f76b5e6797d97a31a7ea5f5a` |
| (tham chieu Oracle+`aerospike`, KHONG chay o dot nay) | 60390 | 970 | `8f7afdfb27b15f5b6d4c886700def93c` |

**FAIL => DUNG NGAY tai day.** Khong chay 4 arm con lai, khong bao so nao khac.
FAIL nghia la mot trong 3 sua da cham vao nhanh khac ngoai y dinh => phai tim ra cho do truoc.
Bao cao phai neu ro: arm nao, so nao, va `diff` dong dau tien lech.

Ghi chu: **`PROFILE_HASH` cua `c3_regress` KHAC `c2b_min`** (them 3 key) — dieu do BINH THUONG
va **khong** duoc dung lam bang chung parity (bay #11). Chi md5 `printDone.csv` moi tinh.

---

## 3. NAM ARM — chay SONG SONG tren Kaggle

Ha tang: `tools/kaggle_sim.py`, 5 kernel CPU cung luc, `TICKER_SOURCE=file`, neo 60395.
Doi jar => **bat buoc `dataset_create_version`** bundle `chuyendinh/sim-c2b-bundle` voi
`sim.jar` moi + 2 profile moi (bay #12). **Bins KHONG doi** => khong build lai dataset (bay #13:
bins khong di qua duong Kaggle; o day ta khong doi bins nen khong lien quan).

| # | tag Kaggle | devrun | profile | override | de tra loi |
|---|---|---|---|---|---|
| 1 | `c3-regress` | `C3_REGRESS` | `c3_regress` | — | **CONG.** Phai = 60395 / `910f1aa6…` |
| 2 | `c3-base` | `C3_BASE` | `c3_min` | — | **BASELINE MOI `C3`** |
| 3 | `c3-full` | `C3_FULL` | `c3_min` | `SELECTOR_ONLY_ENTRY=0`, `DCA_GRID_WEIGHTS=1,1,3,8`, `DCA_GRID_SCALE=19.5` | luong day du o size DUNG |
| 4 | `c3-mom006` | `C3_MOM006` | `c3_min` | `SIM_MIN_MOMENTUM_15M=0.006` | cau GATE |
| 5 | `c3-b1only` | `C3_B1ONLY` | `c3_regress` | `SIM_FIX_B1=true` | tach RIENG hieu ung B1 |

Arm 5 = `C3_regress` + chi B1 => hieu `arm5 - arm1` la **hieu ung thuan cua B1**;
hieu `arm2 - arm5` la hieu ung thuan cua B2+B3 (ma B2 vo hinh o `1,0,0,0`, nen thuc chat la B3).
Do la ly do co arm 5: **tach B1 khoi B3**, hai co che hoan toan khac nhau.

### 3.1 `DCA_GRID_SCALE` cua arm 3 — TINH LAI theo cong thuc MOI

Sau B2: `margin(leg i) = equity x F_BASE x throttle x SCALE x w[i] / total`.

```
arm 2 (1,0,0,0, SCALE=1.5):  equity x 0.03 x throttle  x 1.5 x 1/1
arm 3 (1,1,3,8, SCALE=S)  :  equity x 0.03 x throttle' x S   x 1/13
bang nhau  =>  S = 1.5 x 13 = 19.5
```

**`DCA_GRID_SCALE = 19.5`.** Con so **253.5** cua `T2B_FULLFLOW` la `1.5 x 169` — no bu cho
`total^2`, tuc **bu cho chinh cai bug**; sau B2 dung no se phong to size 13 lan. Khong dung.

**Cong hieu chuan (chot truoc):** `mean(margin)` cua **leg-1** o arm 3 phai nam trong **±20%**
cua `mean(margin)` arm 2. Ngoai cong => duoc **DUNG MOT LAN** quyen sua `SCALE` roi chay lai
arm 3; lan hai ma van ngoai cong thi ghi FAIL hieu chuan va KHONG dien giai arm 3.
(`throttle` la vong phan hoi nen khong the dat chinh xac bang cong thuc — day la ly do co cong
±20%, giong `PREREG_T2B muc 2`.)

---

## 4. DO GI — bao cao, KHONG phai tieu chi chon

Moi arm: `equity`, `CAGR`, `maxDD`, `UW`, `n`, `win%`, `TSloss%`,
`mean(profit|STOP_MARKET_DONE)`, `mean(profit|STOP_LOSS_DONE)`,
**phan bo profit cua winner (p10/p25/med/p75/p90/max)**, `mean(margin)` **theo nam**,
**dem lenh nhanh STRONG vs WEAK**, return theo quy.
Cong cu: `research/analysis/qret_ladder.py` + `/home/ubuntu/java/fsrun/qret.py`.

- **Phan bo winner la thu chinh phai nhin** — B1 doi HINH DANG cua no, khong chi doi trung binh.
- **STRONG/WEAK dem OFFLINE tu cot `symbolPred` cua `printDone.csv`** (rule: `<= 0.29` = STRONG).
  **KHONG them cot vao `printDone.csv`** — doi dinh dang la vo moi phep so md5 parity ve sau.
- `mean(margin)` theo nam la **phep kiem B3**: phai TANG theo equity. Neu khong tang => B3 khong
  vao duoc duong sizing, phai tim loi.
- `maxDD` / `UW` lay tu **chuoi equity** (`qret.py`). So `unProfitMin/35000` cua log bao cao rieng
  va dan nhan "mau so co dinh, khong con la % equity duoi compound".

---

## 5. RANG BUOC CUNG de `C3` duoc nhan lam baseline moi

Tat ca do tren **arm 2** (`C3_BASE`):

1. `maxDD` <= **15%**
2. `UW` (underwater dai nhat) <= **120 ngay**
3. **Khong nam nao am**
4. **Khong quy nao < −5%**

Vi pham bat ky dieu nao => **BAO CAO, KHONG TUNE**. Ghi nguyen van:
*"he compound that vi pham rang buoc cung, can user quyet `F_BASE`"*.
Khong duoc: ha `F_BASE`, ha `U_MAX`, doi `DCA_GRID_SCALE`, doi horizon time-stop, hay chon arm
khac lam baseline. Tat ca deu la tune-sau-khi-thay-so.

---

## 6. CAU GATE — `C3_mom006` vs `C3`

**Quy tac quyet dinh (chot truoc):** goi la **KHAC** khi **>= 2 rate PRIMARY nam ngoai CI cung
huong**. CI = bootstrap **khoi 72h**, nhan he so **x1.21** (chuan da dung o F4/G1/T1/T2b).
Rate PRIMARY: `TSloss%`, `win%`, `mean(profit|SM)`, `mean(profit|SL)`, `n`, `mean(margin)`.

**DU DOAN GHI TRUOC (bat buoc, de sau khong doc nguoc):**

> Du doan: **KHAC**, va theo huong **XAU HON** cho `mom006`. Cu the: `TSloss%` **TANG** va
> `win%` **GIAM** (>= 2 rate cung huong xau). Co che: noi gate 0.008 -> 0.006 ha nguong dong
> cho ung vien BIEN vao; nhom bien chet bang **time-stop 168h**, khong phai bang trailing
> (`E0_EXIT_CF`: 66.6% chua tung vuot +3%, maxFav median 1.83% dat o gio thu 4).
> **B1 KHONG cuu duoc nhom nay** — B1 chi noi cap giveback SAU khi da arm +7%, ma nhom bien
> khong bao gio arm. => sua B1 khong lam doi ban chat cau tra loi cua truc gate.
> Du doan phu: `n` tang, `equity` co the cao hon nhung `maxDD` xau di (tren jar cu: 60,953 voi
> maxDD −21.1%).
>
> Neu ket qua la **KHONG PHAN BIET DUOC** thi du doan nay SAI va phai ghi ro la sai.

---

## 7. CAM sau khi thay so

- Khong tune bat ky tham so nao.
- Khong doi tieu chi, khong doi rang buoc cung, khong doi dinh nghia "KHAC".
- Khong chay VAL. Khong push.
- Khong de cu arm 3/4/5 lam baseline — **baseline la arm 2, hoac khong co**.
- Null / vi pham rang buoc deu la ket qua hop le va PHAI duoc bao cao nguyen van.
