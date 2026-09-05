# PREREG_X3 — trailing cap theo RANK selector (viec A) + pre-arm SL tai −50% (viec B)

Viet va commit **TRUOC** khi chay mot run nao. Khong sua sau khi thay ket qua.
Nen: `X1_C3` (48 thang, 2022-01-01 -> 2025-12-31), profile goc `profiles/x1_c3.properties`,
bins `predwf_map_s1a2_x1` (sha `b8776231...`), `SIM_END_DATE=20251231`, `TICKER_SOURCE=file`.
Bao cao se o `docs/X3_RANKCAP_SL50.md`.

---

## 0. Hai viec, mot jar, 5 run

| tag | `TS_CAP_STRONG_RANK` | `SIM_PRE_ARM_SL` | vai tro |
|---|---|---|---|
| `X3_PARITY` | 0 | 0 | **cong hoi quy**: phai byte-identical `X1_C3` |
| `X3_R2` | 2 | 0 | viec A, 2/8 = 25% lenh duoc cap STRONG |
| `X3_R4` | 4 | 0 | viec A, 4/8 = 50% |
| `X3_R6` | 6 | 0 | viec A, 6/8 = 75% (gan ti le STRONG hien tai 71.5%) |
| `X3_S50` | 0 | −0.50 | viec B |

Quota **5 run, dung het 5**. Khong them muc, khong chay lai sau khi thay so.

---

## 1. VIEC A — hien trang la gi va tai sao no SAI

### 1.1 Do thuc hien trang (khong doan)

`OrderTargetInfoTest.trailRate()` -> `TradeUtils.calRateLossDynamicBuyPNoPump()`:

```
maxGap = (pNoPump != null && pNoPump > TS_PNOPUMP_WEAK_THR) ? TS_MAX_GAP_WEAK(0.03) : TS_MAX_GAP(0.08)
gap    = min(maxProfit * TS_GIVEBACK_RATIO(0.5), maxGap)
rate   = round((maxProfit - gap) / 0.005) * 0.005
```

`pNoPump` = `order.symbolPred` = gia tri thang do **G015x26**. `research/pipeline/build_map.py`
**giu nguyen multiset P(win) cua G015x26 trong tung tick**, chi gan lai xem coin nao nhan gia tri
nao theo thu hang cua S1. Nghia la:

- **thu hang** trong tick den tu S1;
- **gia tri tuyet doi** van la cua G015x26 va no **dich theo regime cua tick**.

Ban le `TS_PNOPUMP_WEAK_THR = 0.29` la **tuyet doi, nam NGOAI tick**. Hau qua co hoc: tick "nong"
(G015 lac quan, ca 8 gia tri <= 0.29) thi **ca 8 coin deu STRONG**; tick "lanh" thi **ca 8 deu WEAK**.
Do thuc tren `C3`: **71.5% lenh di nhanh STRONG**.

=> Cai dang chay **KHONG phai "trailing theo selector"**. No la "trailing theo muc lac quan cua
G015x26 tai tick do". `AGENT_RUNBOOK` muc 3 mo ta cho nay chua dung; se sua trong bao cao.

⚠️ Truoc fix B1 (`docs/C3_BASELINE.md`) nhanh STRONG **chua bao gio chay** — 100% WEAK. Toan bo
lich su DEV truoc `af6181e` khong noi gi ve nhanh nay.

### 1.2 Thay doi engine

Key moi **`TS_CAP_STRONG_RANK`** (0 = TAT = mac dinh = hanh vi hien tai). Khi = N > 0:

```
strong = (selRank != null && selRank <= N)
maxGap = strong ? TS_MAX_GAP(0.08) : TS_MAX_GAP_WEAK(0.03)
```

va **ban le 0.29 bi bo qua hoan toan**. `selRank == null` (leg `DCA_LEVEL1` / `BIG_DOWN`, khong di
qua selector) -> WEAK, dung quy uoc bao thu cua nhanh `pNoPump == null`.

### 1.3 RANK LAY TU DAU — **co san tai diem chon, KHONG suy lai**

Da doc code truoc khi viet (`SimulatorMarketLevelTicker1MStopLoss` vong chon top-K):

```java
int nSel = Math.min(Configs.SELECTOR_RANK_TOPK, symbol2Pred.length);
for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[i]);   // symbol2Pred DA sort TANG theo pNoPump
...
for (long encodedData : chosenCands) { ... }
```

`chosenCands` la **K phan tu dau cua mang da sort tang** => **vi tri trong vong lap CHINH LA rank**.
Da co san bien `_tlRank` cho `TickDecisionLog` chay tren dung vong nay. => X3 dem `selRank` 1-based
tren **toan pool da chon** (ke ca coin dang giu se bi `isSymbolRunning` skip ben duoi) — dung quy uoc
**"cap-then-skip"** ma duong LIVE `DetectEntrySignal2TradeNormal:322-327` dang dung.

**Khong dung phuong an du phong** (suy rank tu thu tu `symbolPred` trong tick): khong can, vi rank ton
tai that o diem chon. Ghi lai o day de nguoi sau khong phai doc lai code.

`selRank` duoc set tren object **LEG** o `createOrder`, roi chep sang object **CUM** o `mergeOrder`
qua `clusterSelRank()` — **dung buoc ma bug B1 da quen doi voi `symbolPred`**. Lay leg KHONG-NULL
DAU TIEN theo thoi gian (leg DCA co rank null, khong duoc xoa rank cua cum).

### 1.4 Ghi nhan rank de cham diem

Rank **KHONG** duoc them vao `printDone.csv` (se pha cong hoi quy byte-identical). Thay vao do mot dong
SLF4J moi lenh vao — dung tinh than dong `PREARM_SL` cua X2:

```
SELRANK sym=<symbol> tOpen=<yyyyMMdd HH:mm> tMs=<ms> rank=<1..K> pred=<symbolPred>
```

`tOpen` in dung dinh dang cot `start` cua `printDone.csv` => ghep `(sym, start)` truc tiep. Voi profile
nay `DCA_GRID_WEIGHTS=1,0,0,0` nen moi cum chi co 1 leg => khoa ghep la duy nhat.

### 1.5 Cong ky thuat (da chay TRUOC khi commit pre-reg nay)

| cong | ket qua |
|---|---|
| `tools/check_cfg_gateway.sh` | OK |
| `mvn -o test` | **60/60 PASS** (8 test moi `RankCapTrailTest`; truoc X3 la 52) |
| `mvn -o -DskipTests package` | BUILD SUCCESS, jar md5 `01ca3461fb98f5c78e0a98055c5fe948` |

`RankCapTrailTest` kiem dung hai manh ghep: (a) rank song sot qua cum, (b) `trailRate()` chon cap theo
rank VA **bo qua ban le 0.29** (rank 2 voi `pred=0.90` -> STRONG; rank 6 voi `pred=0.01` -> WEAK).

---

## 2. VIEC B — pre-arm SL tai −50%

### 2.1 Co che DA CO TU X2, khong viet them dong engine nao

`SIM_PRE_ARM_SL` (`tradecore/PreArmSlUtils.java`, 5 unit test, commit `c633861`): nguong do tren
`firstEntryPrice` (bat bien qua DCA), chi khi `priceSL == null`, gia dong `min(stopLevel, min(open, close))`.
X3 chi dat mot gia tri moi. **Khong sua engine cho viec B.**

### 2.2 🔴 KHAI BAO POST-HOC — bat buoc doc

Run nay **la post-hoc so voi X2**. X2 da dong truc S voi **2 muc** (−0.20, −0.30) va ket luan NULL.
Them muc thu ba sau khi da thay ket qua hai muc kia la **tune-after-the-fact** neu dong co den tu ket qua X2.

**Dong co cua X3 KHONG den tu outcome X2.** No den tu mot **phep do doc lap**: `docs/HOLD_TO_DIE.md`
(counterfactual "neu khong cat ma giu tiep" tren `CLOSES_1H.bin`, 306 lenh time-stop cua `X1_C3`),
**duong hoi phuc theo do sau luc cat**:

| bin | n | be30 | be90 | arm90 | mdd90 | delist |
|---|---|---|---|---|---|---|
| `<-50` | **26** | 4.2 | **8.3** | **4.2** | **−79.6** | **11.5** |
| `-50..-30` | 42 | 16.7 | 23.8 | 21.4 | −65.2 | 2.4 |
| `-30..-20` | 64 | 31.2 | **51.6** | 42.2 | −58.5 | 3.1 |
| `-20..-10` | 93 | 53.8 | 66.7 | 50.5 | −46.8 | 6.5 |

Doc: nhom `< −50` gan nhu **khong hoi** (8.3% ve BE, 4.2% cham arm trong 90 ngay), con **tiep tuc sut
−79.6%**, va **11.5% delist**. Trong khi band `−30..−20` **con hoi 51.6%**. X2 cat o −20/−30 la cat **vao
band con hoi** — do la ly do co hoc lam `medloser` bi keo xuong dung muc cat va `mP|SL` cua `S30` **xau
hon parity**. Nguong −50% la **muc dau tien nam HOAN TOAN duoi vung con hoi**.

Duong hoi phuc theo do sau la mot phep do tren **du lieu gia** (hourly close), khong dung mot con so nao
cua 6 run X2. Neu X2 chua bao gio chay thi phep do nay van cho ra dung nguong −50%.

**Quota: 1 run.** Khong quet, khong them muc thu hai cua truc S trong dot nay.

### 2.3 Ky vong that — ghi TRUOC

Chi **26 lenh** nam trong nhom `< −50` cua `HOLD_TO_DIE` (tren 2,058 lenh = 1.3%). Se co them mot so cum
cham −50% roi hoi trong cua so 168h ma phep do counterfactual khong dem. Du vay **hieu ung ky vong la
NHO va co the khong vuot CI**. Gia tri chinh cua run nay la **cat duoi cung** (`minloser` −94.64), khong
phai cai thien trung binh. Ghi ro tu bay gio de cuoi dot khong doc nguoc.

---

## 3. THIET KE RUN

- Nen `profiles/x1_c3.properties`; moi profile X3 = ban sao + **dung 2 dong** (`TS_CAP_STRONG_RANK`,
  `SIM_PRE_ARM_SL`), khai bao ca hai o **ca 5 profile** (ke ca khi = 0) de nguoi doc thay ro hai cong tac.
- Dataset WFO 48 thang build **1 lan** (X2 da xoa `/home/ubuntu/wfo_ds_x1`; dia ~11G, dataset ~4G).
- **5 kernel Kaggle song song = dung 5 slot** la duong uu tien. No doi hai viec da ghi lam no o
  `X2_EXIT48` muc 10: `tools/kaggle_sim.py` thieu `wfo-ticker-2024h2/2025h1/2025h2` trong `TICKER_DS`
  va guard `len(tk) < 912` phai thanh **1,461**. **Da sua truoc khi commit pre-reg nay.**
- **Quy tac thoat**: neu duong Kaggle con vuong **qua 1 gio** (upload bundle 48 thang / mount / slot),
  **chuyen sang chay TUAN TU tren Oracle va ghi ly do vao bao cao muc "sai lech so voi de bai"**.
  Khong kep o do. Ket qua khong doi: Kaggle+`file` == Oracle+`file` byte-for-byte (`docs/KAGGLE_SIM.md` muc 1).

### 3.1 Cong hoi quy — chay TRUOC, FAIL thi DUNG

`X3_PARITY` (ca hai key = 0) phai ra **dung**: `printDone.csv` md5 `d39da2940dfd815f60772f70517750bf`,
**2,058 lenh** (2,059 dong ke header), `b:98523`. Runner tu `exit 9` neu lech; **khong chay 4 arm con lai**.

---

## 4. TIEU CHI PRIMARY (rate + CI khoi-72h x1.21, toan 48 thang VA theo nam)

Equity **KHONG** phai tieu chi (`AGENT_RUNBOOK` muc 0.3). CI: block bootstrap 72h, luoi khoi CHUNG neo
2022-01-01, 2000 rep, seed 20260905, nhan 1.21 — y het may cua `X2`.

### 4.1 Viec A

| ma | do luong |
|---|---|
| A1 | phan bo `profit \| STOP_MARKET_DONE`: **p10 / p25 / med / p75 / p90 / mean** |
| A2 | `win%` |
| A3 | `TSloss%` — **khong nen doi**; trailing chi tac dong SAU arm, ma dieu kien arm (`RATE_PROFIT_STOP_MARKET=0.07`) khong phu thuoc cap. **Neu `TSloss%` doi nhieu la co gi sai**, phai truy truoc khi doc tiep |
| A4 | **bang 8 hang** rank -> `n`, `%STRONG` (theo ban le 0.29 cua PARITY), `mean(profit\|SM)` |

**Cau hoi co hoc cua viec A:** *winner o rank NONG co dang duoc nha 8% hon winner o rank SAU khong?*
Bang A4 do tren **PARITY** tra loi cau do, va **do chinh la du doan** cho ba muc N.

### 4.2 Viec B

`mP|SL`, **p10 loser**, **min loser**, `win%`, so cum bi cat tai −50 (dem hai duong doc lap: dong log
`PREARM_SL` va `time_order < 168`), va trong so do **bao nhieu cum ma o PARITY ket thuc
`STOP_MARKET_DONE`** (= da tung arm +7% roi chot lai) — ghep `(sym, start)` nhu `X2_EXIT48` muc 6.
Ty le ghep **< 80% => con so KHONG do duoc dang tin cay**, phai ghi trong ngoac.

---

## 5. RANG BUOC CUNG (theo TUNG NAM)

- **R1** `maxDD <= 15%` moi nam
- **R2** khong nam am
- **R3** khong quy < −5%
- **R4** `UW` tung nam <= **1.2 x UW cua PARITY cung nam** (nguong tuyet doi 120 ngay khong con dat duoc
  tren 48 thang — `X1_EXTEND` muc 7; giu dinh nghia tuong doi cua `X2` de so sanh duoc)

R4 van la **rang buoc user CHUA duyet** (`X2_EXIT48` muc 12.1). Giu nguyen, khong tu ha.

---

## 6. QUY TAC QUYET DINH — chot TRUOC khi chay

**Viec A CO TIN HIEU khi va chi khi cả ba:**
1. `p90(profit|SM)` **HOAC** `mean(profit|SM)` **tang don dieu theo N** (N = 2 -> 4 -> 6), tren toan cua so;
2. `win%` **khong giam ngoai CI** o bat ky muc nao;
3. **it nhat mot muc** PASS toan bo R1-R4.

**Viec B CO TIN HIEU khi va chi khi cả ba:**
1. `p10 loser` **cai thien ngoai CI** (toan cua so);
2. `win%` **trong CI**;
3. PASS toan bo R1-R4.

**Khong de cu baseline moi trong dot nay**, ke ca khi mot muc co tin hieu. Equity/CAGR bao **rieng**,
dan nhan "khong phai tieu chi": N=5 => `E[max nhieu] = 2.57 x sqrt(2 ln 5) = 4.6pp`.

---

## 7. DU DOAN GHI TRUOC — khong sua sau khi thay so

### 7.1 So hoc cua cap (nen cua moi du doan duoi)

`exit = peak - min(peak*0.5, cap)`. Voi `peak` trong **6%..16%**, STRONG (cap 0.08) chot **THAP hon**
WEAK (cap 0.03) dung 5pp; chi khi `peak` chay tiep rat xa thi cap rong moi tra cong. => **STRONG = doi
median lay duoi phai**, dung nhu `C3_BASELINE` do khi bat B1 (med 6.00 -> 5.00, p90 11.00 -> 12.06).
=> **N tang (nhieu STRONG hon) => med(profit|SM) GIAM, p90 TANG.**

### 7.2 Bang A4 tren PARITY (du doan)

- `%STRONG` **khong tang theo rank** — gan nhu **tat dinh**: trong mot tick `pNoPump` sap TANG theo rank,
  ma STRONG = `pNoPump <= 0.29`. Du doan rank 1 = **95-100%** STRONG, rank 8 = **35-55%**, tong 71.5% ± 3.
  => rank ~6 la cho ban le hien tai cat qua. **Day chinh la ly do chon N = 6 lam muc "gan ti le hien tai".**
- `n` theo rank: **giam nhe** theo rank (rank sau hay bi het budget trong tick). Du doan rank 1 nhieu hon
  rank 8 khong qua 25%.
- `mean(profit|SM)` theo rank: **giam yeu** theo rank (S1 co edge: `edge5` +8.5% nam 2022 -> +19.3% nam 2025).
  Du doan gradient rank1 -> rank8 khoang **0.2 - 1.0pp**, va **KHONG don dieu** tren ca 8 hang (nhieu).
  Xac suat `mean(rank 1-2) > mean(rank 7-8)`: **65%**.

### 7.3 Viec A theo N (du doan so)

Neo PARITY (`X2_EXIT48` muc 2): `n` 2,058 · `win%` 85.33 · `TSloss%` 14.87 · `mP|SM` **7.178**.

| do | PARITY | `R2` (25% STRONG) | `R4` (50%) | `R6` (75%) |
|---|---|---|---|---|
| `med(profit\|SM)` | (chua do) | **cao nhat** | giua | thap nhat |
| `p90(profit\|SM)` | ~12 ± 2 | ~10.5 ± 2 | ~11.3 ± 2 | ~12.0 ± 2 |
| `mean(profit\|SM)` | 7.178 | 7.0 - 7.3 | 7.0 - 7.3 | 7.1 - 7.3 |
| `win%` | 85.33 | ±0.8pp | ±0.8pp | ±0.8pp |
| `TSloss%` | 14.87 | ±0.8pp | ±0.8pp | ±0.8pp |

- **`p90` tang don dieu theo N: du doan CO** (co hoc, muc 7.1). Xac suat don dieu chat tren 3 diem: **70%**.
- **`mean(profit|SM)` KHONG doi ngoai CI o ca 3 muc: du doan CO** (~75%) — B1 da cho thay cap doi
  **hinh dang** phan bo winner chu khong doi trung binh.
- **`win%` va `TSloss%` gan nhu khong doi.** Neu `TSloss%` lech > 1.5pp thi **co bug**, khong phai ket qua.
- `R6` se **gan PARITY nhat** tren moi rate; khac biet that giua hai cai la ban le nam **TRONG tick**
  (dung N coin STRONG moi tick) thay vi **NGOAI tick** (ca tick STRONG hoac ca tick WEAK).
- **>= 1 muc PASS R1-R4: 55%** (hieu ung nho hon X2 nhieu, nhung UW la thu de vo).
- **Xac suat viec A co tin hieu: 30%.** (0.70 x 0.75 x 0.55 ~ 0.29)

### 7.4 Viec B (du doan so)

Neo PARITY: `mP|SL` −21.848 · `p10loser` **−46.89** · `medloser` −18.11 · `minloser` −94.64 · `win%` 85.33.

- **`minloser`: cai thien manh**, −94.64 -> **−57 ± 8**. Day la cai chac chan nhat va la gia tri that cua run.
- 🔴 **`p10 loser`: du doan KHONG cai thien, co the XAU DI nhe** -> **−50 ± 3**.
  Ly do co hoc, ghi ro de doi chieu: parity `p10loser = −46.89` **nam TREN muc cat −50**. Cat lam hai
  viec nguoc chieu nhau len phan vi nay: (a) keo duoi dai (−94 -> −50) **len**, (b) **them** khoi luong
  moi tai −50 tu nhung cum le ra ket thuc nong hon. Hai luc dan `p10loser` **hoi tu ve ≈ −50 tu ca hai
  phia**, ma −50 **xau hon** −46.89. => **du doan viec B TRUOT dieu kien 1**.
- `mP|SL`: **−20.5 ± 1.5** (cai thien nhe, **trong CI**). Khac `S30` cua X2 (xau hon parity) vi −50%
  nam duoi vung con hoi nen it "cat oan" hon.
- `win%`: giam **0.3 - 1.0pp**, **trong CI** (~60%). `S30` mat 1.77pp voi 231 cum bi cat; −50% cat it hon nhieu.
- `n` cum bi cat tai −50: **70 - 120** (nhom `< −50` cua `HOLD_TO_DIE` co 26, cong nhung cum cham −50 roi
  hoi trong 168h). Trong so do **cum ma PARITY ket thuc `STOP_MARKET_DONE`**: **5 - 12%**.
- Theo nam: cai thien `p10loser` **chi o 2022 va 2025** (parity −51.27 / −54.73, ca hai **duoi** −50);
  **2023 (−29.11) va 2024 (−29.59) gan nhu khong doi hoac xau di nhe**.
- PASS R1-R4: **50%**.
- **Xac suat viec B co tin hieu: 20%.**

### 7.5 Ket cuc tong

Ca hai null: **55%** · chi A: **25%** · chi B: **15%** · ca hai: **5%**.

---

## 8. SAI LECH SO VOI DE BAI — ghi TRUOC

De bai yeu cau **5 kernel Kaggle song song**. `tools/kaggle_sim.py` da duoc sua (muc 3) nhung con hai
rui ro chua do duoc: (i) `sim-c2b-bundle` phai `dataset_create_version` lai voi **jar moi + dataset WFO
48 thang (~4G)**, upload tu Oracle qua Kaggle chua tung do bao gio o kich thuoc nay; (ii) `/home/ubuntu`
con **11G** trong khi dataset chiem ~4G. Neu qua **1 gio** ma chua co 5 kernel `RUNNING`, chuyen Oracle
tuan tu (~13 phut/run x 5 = ~65 phut) va ghi ly do. Quyet dinh nay da chot **truoc** khi chay.
