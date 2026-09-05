# X2_EXIT48 — danh vao DUOI cua lenh thua tren 48 thang: pre-arm hard SL vs time-stop

Pre-reg: `docs/PREREG_X2.md` (commit `b4ddc35`), viet va commit **TRUOC** khi chay. Engine:
commit `c633861` (viet lai pre-arm SL). Nen `C3`/`X1_C3`, cua so 2022-01-01 -> 2025-12-31,
`SIM_END_DATE=20251231`, bins `predwf_map_s1a2_x1` (sha `b8776231...`), Oracle + `TICKER_SOURCE=file`.
6 run, quota dung het 6/6, 22:19 -> 23:39 (13.0 phut/run).

---

## 0. KET QUA MOT DONG — **CA HAI TRUC: KHONG CO TIN HIEU** theo luat da chot

Ca `T` (time-stop) lan `S` (pre-arm SL) deu **truot** quy tac `PREREG_X2` muc 7. Chi tiet muc 7.
Cai do duoc va dang giu lai la **co che**, khong phai mot tham so de dat.

🔴 **Ba rui ro phai doc truoc:**

1. **Khong muc nao trong 5 muc PASS rang buoc cung.** 5/5 arm FAIL, va **deu FAIL o 2022/2023**
   chu khong phai 2025. Cat lo som **doi cho** underwater tu 2025 sang 2022: `X2_T72` UW 2025
   **302 -> 189** nhung UW 2022 **64 -> 159**. `X2_S30` UW 2022 **64 -> 224** va maxDD 2022
   **−13.31 -> −17.23** (vuot tran 15%). Day dung la co che `E1` muc 5.3 da canh bao, chi khac
   la lan nay do duoc **theo nam** nen thay ro no dich di dau.
2. **Pre-arm SL cat duoc DUOI nhung lam DAY xau di.** `X2_S30`: `p10 loser` −46.89 -> −30.94
   (tot), nhung `median loser` **−18.11 -> −30.00** (xau gap doi) va `mP|SL` **−21.85 -> −22.78**
   (**xau hon parity**, CI chua 0). Muc −30% bien phan bo lenh thua thanh mot **cot dung tai
   dung muc cat**: `medloser` cua `S30` = −30.00 va cua `S20` = −20.00 — bang **chinh xac** muc SL.
   => "cat duoi" va "bot am trung binh" **KHONG di cung nhau**.
3. **`win%` giam ngoai CI o CA 5 muc**, khong ngoai le. Day la dieu kien 2 cua quy tac quyet dinh
   va no la thu lam ca hai truc truot ngay ca truoc khi xet rang buoc cung.

---

## 1. PRE-ARM SL CO PHAI VIET LAI KHONG — **CO**, va cong hoi quy PASS

### 1.1 Do thuc hien trang: key cu da chet that

`grep -rn "HARD_SL" src/main` => **khong con mot `Cfg.get("SIM_HARD_SL_PCT")` nao**. Con lai
chi la di vat: field `OrderTargetInfoTest.firstEntryPrice` (van duoc set dung) va dong in
`DumpConfig.derived.pre_arm_stop`. `C2B_SPEC` muc 5.1 ghi dung.
=> X2 la **thay doi ENGINE**, khong phai quet tham so.

### 1.2 Cai da viet (commit `c633861`)

| file | noi dung |
|---|---|
| `tradecore/PreArmSlUtils.java` (MOI) | logic thuan: `stopLevel = firstEntryPrice*(1+pct)`; `hit(first, bar.minPrice)`; `exitPrice = min(stopLevel, min(open,close))` |
| `tradecore/Configs.java` | `PRE_ARM_SL = 0f` + `Cfg.get("SIM_PRE_ARM_SL")` |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | cong chen o `startUpdateOldOrderTrading`, **TRUOC** `LOSER_TIME_STOP`, guard `priceSL == null` |
| `tradecore/DumpConfig.java` | `derived.pre_arm_stop` in noi dung THAT |
| `test/.../PreArmSlTest.java` (MOI) | 5 test |

Bon quyet dinh thiet ke (da chot o pre-reg muc 2.2, khong doi sau khi thay so):

- **Do tren `firstEntryPrice`** (bat bien qua DCA), khong phai `priceEntry` (binh quan, dich moi lan nhoi).
- **Chi khi `priceSL == null`** — da arm thi trailing lam chu.
- **Phat hien bang `bar.minPrice`** — doi xung voi cong arm da dung `bar.maxPrice`.
- **Gia dong = `min(stopLevel, min(open, close))`** — khong bao gio TOT hon muc stop (chan
  look-ahead khi nen thung xuong roi bat len), xau hon khi nen dong duoi stop (chiu gap).

**Ly do thoat KHONG duoc them vao `printDone.csv`** (se pha cong byte-identical) — ghi bang mot
dong SLF4J `PREARM_SL sym=... first=... stop=... exit=... tOpen=... tNow=...`.

### 1.3 Cong ky thuat + CONG HOI QUY — **PASS**

| cong | ket qua |
|---|---|
| `tools/check_cfg_gateway.sh` | OK |
| `mvn test` | **52/52 PASS** (5 test moi `PreArmSlTest`) |
| `mvn -DskipTests package` | BUILD SUCCESS, jar md5 `34bf6b46032e03b6fd7ae38c8c54581e` |
| dataset WFO build lai | `binsSha256=b87762312620f31769a8ef0160ec8132a5482c8f235d86e3364b59cce022a862`, `foldCount=16`, `marketCount=2,554,812` `predCount=2,500,260` `fundingCount=2,043,446` — **trung tuyet doi manifest cua X1** |
| **`X2_PARITY` = jar MOI + key TAT** | **md5 `d39da2940dfd815f60772f70517750bf` = `X1_C3`**, **2,059 dong**, `b:98523` |

=> ✅ **BYTE-IDENTICAL.** Cong nay chay TRUOC 5 arm con lai; runner tu `exit 9` neu FAIL.
`n_PREARM_SL = 0` o `X2_PARITY` va o ca 3 arm truc T (dung nhu thiet ke).

## 2. SAU RUN — bang chinh 48 thang

`equity`/`CAGR` **KHONG phai tieu chi** (muc 8). `p10loser`/`medloser`/`minloser` = phan vi cua
phan bo `profit` cua **lenh THUA** (`profit < 0`).

| tag | n | win% | TSloss% | mP\|SM | **mP\|SL** | **p10loser** | medloser | minloser | meanP | md5 printDone |
|---|---|---|---|---|---|---|---|---|---|---|
| `X2_PARITY` | 2,058 | 85.33 | 14.87 | 7.178 | −21.848 | −46.89 | −18.11 | −94.64 | 2.863 | `d39da294…` |
| `X2_T120` | 2,080 | 83.75 | 16.73 | 7.218 | −18.701 | −39.20 | −15.65 | −91.65 | 2.882 | `2ddbdd23…` |
| `X2_T96` | 2,108 | 82.92 | 18.03 | 7.191 | −16.729 | −36.52 | −13.84 | −91.00 | 2.879 | `d67f4600…` |
| `X2_T72` | 2,123 | 81.25 | 19.74 | 7.221 | **−14.577** | −30.86 | −12.38 | −90.09 | 2.919 | `6cc6e4f0…` |
| `X2_S20` | **2,717** | **79.28** | 20.61 | 7.260 | −18.932 | **−21.55** | **−20.00** | **−65.32** | **1.861** | `a57cc61e…` |
| `X2_S30` | 2,457 | 83.56 | 16.32 | 7.247 | **−22.784** | −30.94 | **−30.00** | −59.88 | 2.345 | `1880526b…` |

**Ba quan sat cau truc — quan trong hon con so:**

1. **Truc S lam dung viec no hua o DUOI va chi o duoi.** `minloser` −94.64 -> −65.32 (`S20`) /
   −59.88 (`S30`); `p10loser` −46.89 -> −21.55 / −30.94. Nhung `medloser` **−18.11 -> −20.00 /
   −30.00** — bang **dung muc cat**. Pre-arm SL khong "cuu" lenh nao, no **dun toan bo phan
   thua lai thanh mot cot o muc cat**: cai duoi dai bi keo len, cai than bi keo XUONG.
2. Vi vay `mP|SL` cua `S30` **xau hon parity** (−22.78 vs −21.85, CI [−3.954, +2.412] chua 0) —
   cat o −30% khong bu duoc phan lenh dang lo 10-18% bi ep xuong −30%. Chi o −20% (`S20`) trung
   binh moi bot am (−18.93), va gia cua no la `win%` **−6.05pp** va `meanP` **−1.00pp**.
3. **Truc T cai thien ca hai dai luong don dieu** va **khong dung toi `mP|SM`** (7.178 -> 7.221,
   phang) — dung ket luan `E1` muc 5.2 tren engine cu, nay tai lap tren engine DA SUA va tren 48
   thang. Nhung no mua bang `win%` (85.33 -> 81.25) va `TSloss%` (14.87 -> 19.74).

## 3. THEO NAM — 2025 la cho dang xem

`p10 loser` (muc tieu that) va `mP|SL`:

| nam | do | PARITY | T120 | T96 | T72 | S30 | S20 |
|---|---|---|---|---|---|---|---|
| **2025** | **p10loser** | **−54.73** | −49.74 | −46.96 | −39.19 | **−31.55** | **−22.18** |
| **2025** | **mP\|SL** | **−28.94** | −24.38 | −22.18 | −18.89 | −26.03 | −20.17 |
| **2025** | win% | 84.69 | 83.17 | 82.02 | 81.09 | 81.85 | **76.36** |
| **2025** | n | 784 | 796 | 801 | 809 | 942 | **1,032** |
| **2025** | minloser | −94.64 | −91.65 | −91.00 | −90.09 | −59.88 | **−65.32** |
| 2024 | p10loser | −29.59 | −28.34 | −27.13 | −23.25 | −30.17 | −21.15 |
| 2023 | p10loser | −29.11 | −21.26 | −19.41 | −15.37 | −30.00 | −20.57 |
| 2022 | p10loser | −51.27 | −34.51 | −28.81 | −26.55 | −31.19 | −21.67 |

**Doc bang nay:**

- **Truc S thang tuyet doi o `p10 loser` 2025**: `+32.5pp` (`S20`) va `+23.2pp` (`S30`) so
  `+15.5pp` cua `T72`. Do dung la co che: SL la phep **cat cut** phan phoi, time-stop chi rut
  ngan thoi gian phoi nhiem. **Du doan ghi truoc cua toi DUNG** — xem muc 8.
- Nhung `mP|SL` 2025 cua `S30` (−26.03) van **thua** `T96` (−22.18) va `T72` (−18.89), du `S30`
  cat duoi manh hon nhieu. Lai la hieu ung "dun thanh cot" o muc 2.
- **`S20` lam 2025 THANH NAM AM**: `ret_nam = −1.91%` (muc 5). Do la lan duy nhat trong toan bo
  DEV mot chan co nam am.
- 2023 la nam **it lenh thua sau nhat** (parity p10loser −29.11): o day pre-arm SL **chi gay hai**
  (`S30` p10loser −30.00 = xau hon parity). Mot nguong tinh khong the dung cho moi regime.

## 4. CI KHOI-72H x1.21 (paired, luoi khoi CHUNG neo 2022-01-01, 2000 rep, seed 20260905)

Hieu `arm − X2_PARITY`. Bo `n`/`mMargin` khoi dem (bien co hoc). `mP|SM` va `meanP` khong muc
nao ngoai CI o toan cua so tru `S20`.

| arm | pham vi | win% | TSloss% | mP\|SL | p10loser | #rate CL ngoai CI |
|---|---|---|---|---|---|---|
| `T120` | 48t | **−1.576** [−2.41,−0.81] ✅ | +1.862 ✅ | +3.147 [+0.89,+5.62] ✅ | +7.685 [+0.15,+15.89] ✅ | 4 |
| `T120` | 2025 | **−1.528** ✅ | +1.658 ✅ | +4.564 [+1.00,+7.95] ✅ | +4.992 [−2.41,+27.56] — | 4 |
| `T96` | 48t | **−2.403** ✅ | +3.158 ✅ | +5.119 [+2.51,+7.94] ✅ | +10.362 [+2.32,+19.63] ✅ | 4 |
| `T96` | 2025 | **−2.671** ✅ | +3.051 ✅ | +6.765 ✅ | +7.768 [+0.22,+31.79] ✅ | 5 |
| `T72` | 48t | **−4.073** ✅ | +4.867 ✅ | +7.271 [+4.34,+10.58] ✅ | +16.022 [+6.76,+25.03] ✅ | 4 |
| `T72` | 2025 | **−3.606** ✅ | +4.356 ✅ | +10.055 [+7.12,+13.19] ✅ | +15.534 [+6.28,+39.07] ✅ | 4 |
| `S20` | 48t | **−6.047** [−7.96,−3.88] ✅ | +5.742 ✅ | +2.916 [−0.53,+6.75] — | **+25.337** [+14.20,+35.50] ✅ | 4 |
| `S20` | 2025 | **−8.337** [−11.00,−4.71] ✅ | +8.108 ✅ | +8.769 [+3.39,+15.64] ✅ | **+32.544** [+19.01,+62.51] ✅ | 4 |
| `S30` | 48t | **−1.768** [−3.02,−0.45] ✅ | +1.452 ✅ | **−0.936** [−3.95,+2.41] — | +15.942 [+5.14,+25.59] ✅ | 3 |
| `S30` | 2025 | **−2.847** ✅ | +2.465 ✅ | +2.915 [−1.49,+8.58] — | +23.175 [+11.31,+51.86] ✅ | 3 |

🔴 **`win%` giam VA ngoai CI o 10/10 dong.** Khong co muc nao "mien phi".

## 5. RANG BUOC CUNG THEO NAM — **5/5 arm FAIL**

R1 maxDD <= 15%/nam; R2 khong nam am; R3 khong quy < −5%; **R4 UW <= 1.2 x UW parity cung nam**
(tuong doi, theo `X1_EXTEND` muc 7 — nguong tuyet doi 120 khong con dat duoc).
Tran UW: 2022 **76.8** / 2023 **68.4** / 2024 **145.2** / 2025 **362.4**.

| arm | nam FAIL | vi pham |
|---|---|---|
| `X2_T120` | 2022, 2023 | UW **99** > 76.8 ; UW **85** > 68.4 |
| `X2_T96` | 2022, 2024 | UW **123** > 76.8 ; UW **224** > 145.2 va quy **−6.72** |
| `X2_T72` | 2022 | UW **159** > 76.8 |
| `X2_S20` | 2022, **2025** | quy **−5.17** ; **ret_nam −1.91% (NAM AM)** va quy **−7.90** |
| `X2_S30` | 2022, 2024 | maxDD **−17.23** (> 15) va UW **224** ; UW **140**, quy **−6.03** |
| `X2_PARITY` | — | PASS 4/4 nam (theo dinh nghia R4 tuong doi) |

**Phat hien cau truc quan trong nhat cua dot nay:** cat lo som **KHONG lam giam** underwater,
no **DOI CHO** underwater. Doi chieu UW theo nam:

| arm | UW 2022 | UW 2023 | UW 2024 | UW 2025 |
|---|---|---|---|---|
| `X2_PARITY` | 64 | 57 | **121** | **302** |
| `X2_T120` | **99** | **85** | 95 | **137** |
| `X2_T96` | **123** | 68 | **224** | 264 |
| `X2_T72` | **159** | 68 | 98 | **189** |
| `X2_S30` | **224** | 61 | 140 | 164 |
| `X2_S20` | 69 | 53 | 78 | **302** |

`T72` doi 113 ngay UW cua 2025 lay 95 ngay UW cua 2022. Do la **danh doi**, khong phai cai tien —
va `E1` muc 5.3 (UW 93 -> 156 tren 30 thang) da thay dung cai nay ma khong tach duoc theo nam.

## 6. CHI PHI THAT CUA SL — lenh bi cat OAN (tieu chi P5)

Ghep `(sym, start)` cua leg-1 giua arm va `X2_PARITY`. **CAT OAN** = cum bi dong bang
`STOP_LOSS_DONE` o arm ma o parity ket thuc `STOP_MARKET_DONE` (tuc **da arm +7%** roi chot lai).

| arm | n_SL | ghep% | **cat oan** | %_cua_SL | pnl parity thu duoc tu chinh nhung cum do | profit% TB |
|---|---|---|---|---|---|---|
| `X2_T120` | 348 | 97.7% | **35** | 10.1% | **+3,047** | +5.64 |
| `X2_T96` | 380 | 96.8% | **63** | 16.6% | **+6,648** | +6.78 |
| `X2_T72` | 419 | 95.7% | **96** | 22.9% | **+10,263** | +6.65 |
| `X2_S30` | 401 | 86.0% | **40** | 10.0% | **+5,147** | +5.96 |
| `X2_S20` | 560 | **77.1%** | (127) | (22.7%) | (+15,182) | (+6.50) |

🔴 **`X2_S20`: ty le ghep 77.1% < 80% => theo pre-reg muc 5, con so nay KHONG do duoc dang tin cay.**
Ghi trong ngoac, khong duoc dung de ket luan. Ly do ghep thap: `S20` co 2,717 lenh vs 2,058 cua
parity — hai chan phan ky manh theo thoi gian vi cat som giai phong margin lien tuc.

**Doc bang nay:** chi phi tang **don dieu** theo do cat ngan tren truc T (10.1% -> 16.6% -> 22.9%
so lenh SL la lenh le ra da thang). O truc S, `S30` cat oan **10.0%** — thap nhat trong 5 arm o ty
le — vi nguong −30% chi cham nhung cum da roi rat sau, ma so do it khi quay lai +7%.
=> **`S30` la muc "re" nhat ve chi phi cat oan**, nhung cung la muc **khong cai thien duoc `mP|SL`**.

### 6.1 Tach ly do thoat (kiem cheo hai duong doc lap)

| arm | n_SL | dong log `PREARM_SL` | n co hold < TS_H | n time-stop dung han |
|---|---|---|---|---|
| `X2_T120` / `T96` / `T72` | 348 / 380 / 419 | **0** / 0 / 0 | 2 / 2 / 2 | 346 / 378 / 417 |
| `X2_S20` | 560 | **482** | 483 | 77 |
| `X2_S30` | 401 | **231** | 232 | 169 |

Hai duong do doc lap (log SLF4J vs `time_order < TS_H` trong `printDone.csv`) **lech dung 1 lenh**
o ca hai arm S — chenh la 2 cum dong tai bien `SIM_END_DATE` (cung xuat hien o ca 3 arm T, noi
`PREARM_SL = 0`). => co che ghi nhan **dung**, khong co lenh nao bi gan nham ly do.

## 7. PHAN QUYET TUNG TRUC — theo dung quy tac `PREREG_X2` muc 7

Truc CO TIN HIEU khi va chi khi: (1) `mP|SL` VA `p10loser` cai thien **don dieu** doc truc, tren
**toan cua so VA rieng 2025**; (2) `win%` **khong giam ngoai CI** o bat ky muc nao; (3) **it nhat
mot muc** PASS toan bo R1-R4.

| truc | (1) don dieu | (2) win% trong CI | (3) >=1 muc PASS | **PHAN QUYET** |
|---|---|---|---|---|
| **T** (168/120/96/72) | ✅ **CO** — `mP\|SL` −21.85→−18.70→−16.73→−14.58 va `p10loser` −46.89→−39.20→−36.52→−30.86; 2025 cung don dieu | ❌ **KHONG** — −1.58 / −2.40 / −4.07, **ca ba ngoai CI** | ❌ **KHONG** — 0/3 muc | 🔴 **KHONG CO TIN HIEU** |
| **S** (off/−0.30/−0.20) | ❌ **KHONG** — `mP\|SL` toan cua so −21.85 → **−22.78** → −18.93 (khong don dieu; `S30` xau hon parity) | ❌ **KHONG** — −1.77 / −6.05, **ca hai ngoai CI** | ❌ **KHONG** — 0/2 muc | 🔴 **KHONG CO TIN HIEU** |

### => **CA HAI TRUC: NULL.** Khong de cu baseline moi (pre-reg muc 7 cam tuyet doi).

**Nhung null nay CO THONG TIN, va day la phan phai doc ky:**

- Truc T **truot o dieu kien 2 va 3, KHONG truot o dieu kien 1**. Co che ma `E1` mo ta la **that**
  va **tai lap duoc tren engine da sua va tren 48 thang**: `mP|SL` va `p10loser` cai thien don
  dieu, `mP|SM` khong doi. Cai giet no la **gia**: `win%` giam ngoai CI o ca ba muc, va UW **doi
  cho** sang 2022 lam vo rang buoc cung.
- Truc S truot o **ca ba** dieu kien. Cai dang gia nhat hoc duoc: mot **hard SL tinh, mot nguong,
  bat bien theo thoi gian** la cong cu SAI cho bai nay. No dun phan bo lenh thua thanh mot cot
  tai muc cat (`medloser` = dung muc cat) nen doi mot cai duoi dai lay mot cai than sau hon.
- **Khong duoc doc nguoc:** `X2_T72` co equity 116,318 (+18% so parity) va CAGR 35.07%. Do
  **khong phai tieu chi** (muc 8) va no **FAIL rang buoc cung**. Neu lan sau ai nhac `T72` vi so
  equity, day la cho de doc lai.

## 8. EQUITY / CAGR — **KHONG PHAI TIEU CHI**

N=6 => `E[max nhieu] = 2.57 x sqrt(2 ln 6) = 4.9pp`. Bao rieng, dan nhan.

| tag | equity | CAGR% | maxDD% (48t) | UW (48t) |
|---|---|---|---|---|
| `X2_PARITY` | 98,523 | 29.58 | −13.31 | 302 |
| `X2_T120` | 105,459 | 31.80 | −13.48 | 137 |
| `X2_T96` | 108,207 | 32.65 | −12.55 | 264 |
| `X2_T72` | **116,318** | 35.07 | −12.66 | 189 |
| `X2_S20` | **78,742** | 22.51 | −15.00 | 302 |
| `X2_S30` | 92,224 | 27.45 | −17.23 | 224 |

Bien do +18% / −20% quanh parity **vuot xa** 4.9pp, nhung equity van khong duoc dung de chon:
ca 5 arm deu FAIL rang buoc cung, nen khong co gi de chon.

## 9. DU DOAN GHI TRUOC — doi chieu (`PREREG_X2` muc 8), **KHONG sua**

> **Du doan chinh: TRUC S cai thien `p10 loser` 2025 NHIEU HON HAN truc T.**

✅ **DUNG.** `+32.5pp` (`S20`) / `+23.2pp` (`S30`) vs `+15.5pp` (`T72`).

So cu the du doan vs thuc te (`p10 loser` 2025):

| arm | du doan | thuc te | trong bang? |
|---|---|---|---|
| `S20` | −22 ± 4 | **−22.18** | ✅ (gan nhu trung tam) |
| `S30` | −33 ± 5 | **−31.55** | ✅ |
| `T72` | −45 ± 7 | **−39.19** | ❌ — T tot hon toi tuong |
| `T96` | −48 ± 7 | **−46.96** | ✅ |
| `T120` | −51 ± 6 | **−49.74** | ✅ |

4/5 trong bang. Sai lech duy nhat la **toi danh gia THAP truc T** o muc cat ngan nhat.

Ba du doan phu:

- (a) "Truc S lam `win%` giam nhieu hon truc T; `S20` mat 2-5pp, `S30` mat 1-3pp; kha nang cao
  truc S truot dieu kien 2 o muc −0.20." — ✅ **dung ve huong va ve `S30`** (2025: −2.85pp), ❌ **sai
  ve do lon cua `S20`**: −8.34pp o 2025, gap doi can tren du doan. Va ❌ **sai o cho quan trong hon**:
  toi tuong dieu kien 2 chi giet truc S — thuc te no giet **CA HAI** truc, ke ca `T120`.
- (b) "Ca hai truc lam UW dai ra; >= 3/6 run vi pham R4." — ✅ **dung ve so** (5/5 arm FAIL rang
  buoc cung, 4/5 co vi pham UW), nhung ❌ **sai ve cho**: toi tuong UW dai ra o 2025 (nam da xau
  nhat). Thuc te UW 2025 **NGAN LAI** manh (302 -> 137 o `T120`) va cai vo la **2022**.
- (c) "`n` tang; `T72` >= 2,200; `S20` >= 2,150." — ❌ **sai** ve `T72` (2,123), ✅ **dung** ve `S20`
  (2,717) nhung thap hon thuc te rat nhieu.

Xac suat toi dat truoc: S co tin hieu 35% / T 30% / ca hai null 40%. **Ket cuc: ca hai null.**

## 10. SAI LECH SO VOI DE BAI — da ghi TRUOC khi chay (`PREREG_X2` muc 9)

Chay **tuan tu tren Oracle**, khong phai 6 kernel Kaggle song song. Ly do (do duoc, khong doan):
cong hoi quy phai tai lap md5 `d39da294...` sinh ra tren **Oracle + `file`**; chay cong do tren
dung may sinh ra neo la duong zero-risk. Duong Kaggle con doi hoi (i) upload ~5G (jar moi +
dataset 48 thang + bins X1) voi dia con 11G, (ii) **sua `tools/kaggle_sim.py`** (`TICKER_DS`
thieu 3 dataset 2024h2/2025h1/2025h2 — chung **DA co** tren Kaggle; va guard `len(tk) < 912`
phai thanh 1,461). Gia thuc te: **78 phut wall-clock** (13.0 phut/run x 6). `X1_EXTEND` muc 1.3(b)
chon y het vi cung ly do.

⚠️ **No ky thuat de lai:** `tools/kaggle_sim.py` **van chua chay duoc cua so 48 thang**. Ai muon
duong Kaggle cho job sau phai sua 2 cho tren truoc. Ghi vao `QUEUE`.

## 11. ARTIFACT / TAI LAP

| artifact | duong dan |
|---|---|
| jar | `target/binance-java-sdk-1.2.4.jar`, md5 `34bf6b46032e03b6fd7ae38c8c54581e` (commit `c633861`) |
| profiles | `profiles/x2_{parity,t120,t96,t72,s20,s30}.properties` — moi cai khac `x1_c3` **dung 1 dong** |
| runner | `research/pipeline/x2/run_x2_sim.sh` (co cong hoi quy tu dong, `exit 9` neu FAIL) |
| cham diem | `research/analysis/x2_rates.py` |
| run | `/home/ubuntu/java/devrun/X2_{PARITY,T120,T96,T72,S20,S30}` |
| log | `/home/ubuntu/x2log/{build.out,build_ds.out,sim.out,score.out}` |
| dataset WFO | `/home/ubuntu/wfo_ds_x1` (4.0G) — **DA XOA sau khi cham diem** (dia 95%); tai tao bang `run_x2_sim.sh` |

```bash
R=/home/ubuntu/src/BinanceFuturesJava
bash $R/research/pipeline/x2/run_x2_sim.sh
python3 $R/research/analysis/x2_rates.py
rm -rf /home/ubuntu/wfo_ds_x1
```

## 12. THE MO SAU DOT NAY (khong lam trong dot nay, khong duoc tu chay)

1. 🔴 **Rang buoc UW can user quyet lai.** X2 dung R4 **tuong doi** (1.2x parity theo nam) vi
   `X1_EXTEND` muc 7 da chung minh nguong 120 tuyet doi khong dat duoc. Voi R4 tuong doi thi
   **parity PASS con moi arm FAIL** — tuc rang buoc nay dang lam dung viec cua no, nhung no
   **chua bao gio duoc user duyet**. Neu user muon danh doi "UW 2025 ngan hon, UW 2022 dai hon"
   thi `T120` la ung vien (UW 2025 302 -> 137, maxDD 2025 −12.17 -> −9.65) — **nhung do la nut
   RISK PREFERENCE cua user**, khong phai bai toan toi uu.
2. Cai da hoc ve co che: **hard SL mot nguong tinh la cong cu sai**. Neu con quay lai bai "duoi
   2025" thi huong con lai la **SL PHU THUOC TRANG THAI** (vd chi cat khi cum chua tung vuot
   +x%, hoac nguong theo do bien dong cua coin) — chinh la ho `SIM_COND_EXIT_HOURS` /
   `SIM_COND_EXIT_MIN_FAV` da co san trong engine tu F2 va **chua bao gio duoc quet tren 48 thang**.
   Phai co pre-reg rieng; **KHONG duoc chay tiep trong dot nay** (tune-after-the-fact).
3. `tools/kaggle_sim.py` chua ho tro cua so 48 thang (muc 10).
