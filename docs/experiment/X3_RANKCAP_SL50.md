# X3_RANKCAP_SL50 — trailing cap theo RANK selector + pre-arm SL tai −50% (48 thang)

Pre-reg: `docs/prereg/PREREG_X3.md` (commit `e622926`), viet va commit **TRUOC** khi chay.
Engine: cung commit. Nen `X1_C3`, cua so 2022-01-01 -> 2025-12-31, `SIM_END_DATE=20251231`,
bins `predwf_map_s1a2_x1` (sha `b8776231...`), Oracle + `TICKER_SOURCE=file`.
5 run, quota dung het 5/5, 00:58 -> 02:08 (12.9 phut/run).

---

## 0. KET QUA MOT DONG — **CA HAI VIEC: KHONG CO TIN HIEU**

Ca viec A (`TS_CAP_STRONG_RANK` 2/4/6) lan viec B (`SIM_PRE_ARM_SL=-0.50`) deu truot quy tac
`PREREG_X3` muc 6. Chi tiet muc 8.

🔴 **Bon rui ro phai doc truoc:**

1. **Ban le trailing hien tai gan nhu KHONG lien quan den rank** — do duoc, khong con la suy luan.
   Bang rank x %STRONG cua PARITY: rank 1 = **87.7%** STRONG, rank 8 = **83.3%**, toan dai 8 rank chi
   trai tu **80.9% den 87.7%** (spread **6.8pp**). Neu ban le 0.29 that su phan biet theo rank thi
   spread phai gan 100pp. => `AGENT_RUNBOOK` muc 3 mo ta SAI cho nay; da sua trong dot nay.
2. **Winner o rank NONG KHONG tot hon winner o rank SAU** — cau hoi co hoc cua viec A co cau tra loi
   **KHONG**. `mean(profit|SM)` cua rank 1-2 = **6.801**, cua rank 7-8 = **7.065**. Nghia la nha cap
   rong 8% cho rank nong la **dat cuoc vao mot gradient khong ton tai**. Do la ly do SAU CUNG cua ca
   ba muc N, khong phai chuyen nhieu.
3. 🔴 **`X3_R6` giong `X3_PARITY` o MOI rate muc lenh (0/8 rate ngoai CI, `n` = 2,058 y het,
   `win%` = 85.33 y het) nhung `UW 2022` nhay 64 -> 159 ngay.** Mot thay doi vo hinh o muc trade lai
   lam vo rang buoc R4. => **R4 (underwater) o do phan giai nay bi chi phoi boi nhieu single-realization,
   khong con phan biet duoc gi.** Day la bang chung manh nhat tu truoc den nay cho `X2_EXIT48` muc 12.1.
4. **Pre-arm SL −50% lam `p10 loser` XAU DI** (−46.89 -> **−50.07**), dung nhu du doan ghi truoc
   (muc 9). Cai no lam duoc that su la cat duoi cung: `minloser` −94.64 -> **−71.44**.

---

## 1. CODE — RANK LAY TU DAU + CONG HOI QUY

### 1.1 Rank co san tai diem chon, **khong phai suy lai**

`SimulatorMarketLevelTicker1MStopLoss`, vong chon top-K:

```java
int nSel = Math.min(Configs.SELECTOR_RANK_TOPK, symbol2Pred.length);
for (int i = 0; i < nSel; i++) chosenCands.add(symbol2Pred[i]);  // symbol2Pred DA sort TANG theo pNoPump
```

`chosenCands` la K phan tu dau cua mang **da sort tang** => **vi tri trong vong lap CHINH LA rank**.
Da co san `_tlRank` cho `TickDecisionLog` chay tren dung vong nay. X3 dem `selRank` **1-based tren
toan pool da chon** (ke ca coin dang giu se bi `isSymbolRunning` skip) — dung quy uoc **"cap-then-skip"**
cua duong LIVE (`DetectEntrySignal2TradeNormal:322-327`).

=> **KHONG dung phuong an du phong** (suy rank tu thu tu `symbolPred` trong tick). Khong can.

### 1.2 Cac cho da sua

| file | noi dung |
|---|---|
| `tradecore/Configs.java` | `TS_CAP_STRONG_RANK` (0 = tat), doc qua `Cfg.get("TS_CAP_STRONG_RANK")` |
| `tradecore/TradeUtils.java` | tach loi chung `trailFromCap(maxProfit, maxGap)` (KHONG doi mot phep tinh nao) + `calRateLossDynamicBuyRank(...)` |
| `research/OrderTargetInfoTest.java` | field `Integer selRank`; `trailRate()` re nhanh khi `TS_CAP_STRONG_RANK > 0` |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | dem rank o vong chon; `createOrderBUY/createOrder` them tham so `selRank` (overload giu chu ky cu); **`mergeOrder` chep rank qua `clusterSelRank()`**; dong log `SELRANK` |
| `test/.../RankCapTrailTest.java` (MOI) | 8 test |

🔴 **KHONG lap bug B1**: `selRank` duoc chep sang object CUM trong `mergeOrder` bang
`clusterSelRank()` — lay leg KHONG-NULL DAU TIEN theo thoi gian, doi xung `clusterSymbolPred()`.
Gan **vo dieu kien** (khong sau co `FIX_B1`, khong sau co `TS_CAP_STRONG_RANK`): day la field moi,
khong duong nao doc no khi key = 0, nen van byte-identical ma khong sinh nhanh trang thai thu hai.

Test then chot (`capRankIgnoresPnoPumpHinge`): `rank 2` voi `pred=0.90` -> **STRONG**; `rank 6` voi
`pred=0.01` -> **WEAK**. Tuc ban le 0.29 that su bi bo qua.

Rank **khong** vao `printDone.csv` (se pha cong byte-identical) — ghi bang dong SLF4J
`SELRANK sym=... tOpen=... tMs=... rank=... pred=...`, ghep lai theo `(sym, start)` khi cham diem.
`printDone` ghi `sym` **khong co duoi quote** (`ANT`) con log ghi day du (`ANTUSDT`) => cat duoi o
CUOI chuoi. **Ty le ghep 100.0%** tren ca 5 run.

### 1.3 Cong ky thuat + CONG HOI QUY — **PASS**

| cong | ket qua |
|---|---|
| `tools/check_cfg_gateway.sh` | OK |
| `mvn -o test` | **60/60 PASS** (8 test moi; truoc X3 la 52) |
| `mvn -o -DskipTests package` | BUILD SUCCESS, jar md5 `01ca3461fb98f5c78e0a98055c5fe948` |
| dataset WFO build lai | `binsSha256=b87762312620f31769a8ef0160ec8132a5482c8f235d86e3364b59cce022a862`, `foldCount=16`, `marketCount=2,554,812` `predCount=2,500,260` `fundingCount=2,043,446` — **trung tuyet doi manifest X1/X2** |
| **`X3_PARITY` = jar MOI + ca hai key TAT** | md5 `d39da2940dfd815f60772f70517750bf` = `X1_C3`, **2,058 lenh**, `b:98523` |

=> ✅ **BYTE-IDENTICAL.** `n_SELRANK = 2,058` va `n_PREARM_SL = 0` o PARITY (dung thiet ke:
log khong tham gia quyet dinh). Runner tu `exit 9` neu cong FAIL; 4 arm chay sau khi cong PASS.

---

## 2. BANG CHINH 48 THANG

`equity`/`CAGR` **KHONG phai tieu chi** (muc 10).

| tag | N | n | win% | TSloss% | mean\|SM | mP\|SL | p10loser | minloser | meanP | md5 printDone |
|---|---|---|---|---|---|---|---|---|---|---|
| `X3_PARITY` | 0 | 2,058 | 85.33 | 14.87 | 7.178 | −21.848 | −46.89 | −94.64 | 2.863 | `d39da294…` |
| `X3_R2` | 2 | 2,077 | 85.46 | 14.73 | 7.081 | −21.867 | −46.89 | −94.64 | 2.816 | `00565595…` |
| `X3_R4` | 4 | 2,065 | 85.38 | 14.82 | 7.091 | −21.849 | −46.89 | −94.64 | 2.802 | `83dc4309…` |
| `X3_R6` | 6 | 2,058 | 85.33 | 14.87 | 7.167 | −21.849 | −46.89 | −94.64 | 2.853 | `2e83104c…` |
| `X3_S50` | — | 2,197 | 85.03 | 14.93 | 7.194 | **−23.146** | **−50.07** | **−71.44** | 2.664 | `a866bc4a…` |

**Kiem chung co hoc `TSloss%` (tieu chi A3 cua pre-reg): PASS.** So lenh `STOP_LOSS_DONE` cua ca ba
arm A = **306**, y het PARITY (`done:306/...` trong log sim cua ca 4 run). Dung nhu du doan: trailing
chi tac dong SAU arm, ma dieu kien arm (`RATE_PROFIT_STOP_MARKET=0.07`) khong phu thuoc cap. Ba cot
`mP|SL` / `p10loser` / `minloser` cua ba arm A **giong PARITY den 2 chu so** — lenh thua khong bi cham.

---

## 3. A4 — BANG RANK x %STRONG x PROFIT (tren `X3_PARITY`)

Day la phep do tra loi cau hoi co hoc cua viec A. `%STRONG` tinh theo **ban le 0.29 dang chay**.

| rank | n | %STRONG | mean(profit\|SM) | med(profit\|SM) | n_SM |
|---|---|---|---|---|---|
| 1 | 302 | **87.7%** | 6.809 | 4.996 | 261 |
| 2 | 270 | 86.7% | 6.793 | 5.000 | 237 |
| 3 | 245 | 82.9% | 7.350 | 5.000 | 208 |
| 4 | 241 | 84.2% | 6.850 | 4.996 | 205 |
| 5 | 245 | 81.2% | **8.221** | 5.000 | 207 |
| 6 | 225 | **80.9%** | 7.466 | 5.489 | 188 |
| 7 | 254 | 81.9% | 7.282 | 5.000 | 207 |
| 8 | 276 | 83.3% | 6.877 | 4.999 | 239 |
| **ALL** | **2,058** | **83.8%** | **7.178** | **5.000** | **1,752** |

**Ba doc quan trong:**

1. **`%STRONG` gan nhu PHANG theo rank** (80.9% .. 87.7%, spread 6.8pp). Trong mot tick cac gia tri
   `pNoPump` bam rat sat nhau (vi du cung mot tick: rank 1 = 0.3547, rank 2 = 0.3586, rank 3 = 0.3613),
   nen ban le 0.29 cat **giua cac tick**, khong cat **giua cac rank trong tick**. => xac nhan bang do
   thuc cai ma muc 1.1 cua pre-reg mo ta bang code: **cai dang chay khong phai "trailing theo selector"**.
2. **`mean(profit|SM)` KHONG giam theo rank.** Trong so theo `n_SM`: rank 1-2 = **6.801**,
   rank 7-8 = **7.065**. Rank sau **hoi tot hon** rank nong. Rank tot nhat la **rank 5** (8.221).
   => **Cau tra loi cho "winner o rank nong co dang duoc nha 8% hon khong": KHONG.**
3. `med(profit|SM)` = **5.000 o ca 8 rank** — khong co gradient nao ca.

**Do la du doan cho ba muc N, va no du doan NULL.** Neu khong co gradient chat luong theo rank thi
doi ai duoc cap rong theo rank chi la **hoan vi**, khong phai cai tien.

`%STRONG` **hieu dung** cua tung arm (theo luat rank, khong theo 0.29):
`R2` = 573/2,077 = **27.6%** · `R4` = 1,056/2,065 = **51.1%** · `R6` = 1,523/2,058 = **74.0%**
(so voi `PARITY` theo luat gia tri = **83.8%**).

---

## 4. VIEC A — PHAN BO WINNER THEO N

| tag | N | n_SM | p10 | p25 | med | p75 | **p90** | mean |
|---|---|---|---|---|---|---|---|---|
| `X3_PARITY` | 0 | 1,752 | 3.500 | 4.000 | 5.000 | 7.466 | **12.495** | 7.178 |
| `X3_R2` | 2 | 1,771 | **3.998** | **4.499** | **5.500** | **7.994** | 11.222 | 7.081 |
| `X3_R4` | 4 | 1,759 | 3.989 | 4.493 | 5.498 | 7.500 | 11.500 | 7.091 |
| `X3_R6` | 6 | 1,752 | 3.500 | 4.000 | 5.000 | 7.495 | 12.481 | 7.167 |

**So hoc lam ra bang nay** (`exit = peak − min(peak·0.5, cap)`): voi `peak` trong 6%..16%, STRONG
(cap 0.08) chot **THAP hon** WEAK (cap 0.03) dung 5pp; cap rong chi tra cong khi `peak` chay rat xa.
=> **it STRONG hon => than phan bo LEN, duoi phai XUONG.** Do dung la cai `R2` lam: p10/p25/med
**+0.5pp** va p90 **−1.27pp**.

CI khoi-72h x1.21, hieu `arm − PARITY`, toan cua so:

| arm | win% | TSloss% | mean\|SM | med\|SM | **p90\|SM** | p10loser | #rate CL ngoai CI |
|---|---|---|---|---|---|---|---|
| `R2` | **+0.134** [+0.04,+0.24] ✅ | −0.136 ✅ | −0.097 [−0.36,+0.13] — | **+0.500** [+0.45,+1.05] ✅ | **−1.273** [−2.16,−0.34] ✅ | 0.000 — | 4 |
| `R4` | +0.050 — | −0.050 — | −0.088 — | +0.499 [+0.49,+0.50] ✅ | −0.995 [−1.66,+0.15] — | 0.000 — | 1 |
| `R6` | **0.000** — | **0.000** — | −0.011 — | 0.000 — | −0.014 — | 0.000 — | **0** |

- **`win%` KHONG giam ngoai CI o muc nao** — dieu kien 2 cua quy tac quyet dinh **DAT**. (Day la khac
  biet lon so voi `X2`, noi dieu kien 2 giet ca hai truc.)
- **`R6` la con so 0 tuyet doi**: `n` giong het PARITY (2,058), `win%` giong het, `TSloss%` giong het,
  **0/8 rate chat luong ngoai CI**. Doi 83.8% STRONG "theo gia tri" thanh 74.0% STRONG "theo rank"
  cho ket qua muc lenh **khong phan biet duoc**.
- **`p90` KHONG tang don dieu theo N**: 12.495 -> 11.222 -> 11.500 -> 12.481. Cai cao nhat la
  **PARITY**. `mean|SM` cung khong: 7.178 -> 7.081 -> 7.091 -> 7.167.
  => **dieu kien 1 TRUOT.**

---

## 5. VIEC B — PRE-ARM SL TAI −50%

**61 cum bi cat** boi pre-arm SL (log `PREARM_SL`), doi chieu doc lap `time_order < 168h` = **62**
(lech 1 cum = hai cum dong tai bien `SIM_END_DATE`, xuat hien y het o ca 4 run co `PREARM_SL = 0`).
=> co che ghi nhan **dung**. `n_SL` 306 -> 328 (`n_timestop` 304 -> 266).

| do | PARITY | `S50` | doi |
|---|---|---|---|
| `minloser` | −94.64 | **−71.44** | ✅ cat duoi that |
| `p10loser` | −46.89 | **−50.07** | 🔴 **XAU DI** (hieu −3.187, CI [−13.59, +6.29] — **trong CI**) |
| `mP\|SL` | −21.848 | **−23.146** | xau di (hieu −1.298, CI [−3.43, +0.49] — trong CI) |
| `win%` | 85.33 | 85.03 | −0.301, **trong CI** |
| `n` | 2,058 | 2,197 | +139, trong CI |

**Tai sao `p10 loser` xau di — co hoc, da ghi TRUOC khi chay (muc 9):** `p10loser` cua PARITY la
**−46.89**, tuc **nam TREN muc cat −50**. Cat lam hai viec nguoc chieu: (a) keo duoi dai (−94 -> −50)
**len**, (b) **them khoi luong moi tai −50** tu nhung cum le ra ket thuc nong hon. Hai luc dan phan vi
nay **hoi tu ve ≈ −50 tu ca hai phia**, ma −50 xau hon −46.89. Do dung la ban rat gon cua hieu ung
"**dun phan bo lenh thua thanh mot cot tai muc cat**" ma `X2_EXIT48` muc 2 do o −20/−30.

**Theo nam** — cho duy nhat truc S lam dung viec no hua:

| nam | p10loser PARITY | p10loser `S50` | mP\|SL PARITY | mP\|SL `S50` |
|---|---|---|---|---|
| 2022 | −51.27 | **−50.58** | −22.859 | −25.875 |
| 2023 | −29.11 | −29.11 (khong doi) | −13.228 | −13.777 |
| 2024 | −29.59 | −29.59 (khong doi) | −15.520 | −15.417 |
| 2025 | **−54.73** | **−50.23** | −28.941 | −29.920 |

Dung nhu du doan: **chi 2022 va 2025 doi** (hai nam duy nhat co `p10loser` **duoi** −50);
2023/2024 **khong doi mot chu so** vi lenh thua cua hai nam do khong sau toi −50%.

### 5.1 Chi phi cat oan — **re nhat trong moi muc SL da do**

| arm | n_SL | ghep% | cat oan | %_cua_SL | pnl parity thu duoc | profit% TB |
|---|---|---|---|---|---|---|
| `X3_S50` | 328 | **94.8%** | **6** | **1.8%** | +644.3 | +4.004 |
| (`X2_S30`) | 401 | 86.0% | 40 | 10.0% | +5,147 | +5.96 |
| (`X2_T72`) | 419 | 95.7% | 96 | 22.9% | +10,263 | +6.65 |

**1.8%** — nguong −50% gan nhu khong cat nham lenh nao le ra thang, dung nhu `HOLD_TO_DIE` du bao
(nhom `< −50` chi 4.2% cham arm trong 90 ngay). Ty le ghep 94.8% >= 80% nen con so nay **do duoc
dang tin cay**. Nhung "khong cat oan" **khong dong nghia voi "co loi"**: 61 cum bi cat van bi ep
xuong −50% thay vi ket thuc nong hon o gio thu 168.

---

## 6. RANG BUOC CUNG THEO NAM — **4/4 arm FAIL, PARITY PASS**

R1 maxDD <= 15%/nam; R2 khong nam am; R3 khong quy < −5%; R4 UW <= 1.2 x UW parity cung nam.
Tran UW: 2022 **76.8** / 2023 **68.4** / 2024 **145.2** / 2025 **362.4**.

| arm | nam FAIL | vi pham |
|---|---|---|
| `X3_R2` | 2022 | UW **114** > 76.8 |
| `X3_R4` | 2022 | UW **119** > 76.8 |
| `X3_R6` | 2022 | UW **159** > 76.8 |
| `X3_S50` | 2022 | maxDD **−16.86** (> 15) ; UW **77** > 76.8 |
| `X3_PARITY` | — | PASS 4/4 nam |

UW theo nam:

| arm | UW 2022 | UW 2023 | UW 2024 | UW 2025 |
|---|---|---|---|---|
| `X3_PARITY` | **64** | 57 | 121 | 302 |
| `X3_R2` | **114** | 57 | 121 | 302 |
| `X3_R4` | **119** | 58 | 121 | 302 |
| `X3_R6` | **159** | 57 | 122 | 302 |
| `X3_S50` | **77** | 57 | 121 | 302 |

### 6.1 🔴 PHAT HIEN QUAN TRONG NHAT CUA DOT NAY — R4 khong con phan biet duoc gi

`X3_R6` co: `n` = 2,058 (**y het** PARITY), `win%` = 85.33 (y het), `TSloss%` = 14.87 (y het),
`mean|SM` lech **−0.011**, **0/8 rate chat luong ngoai CI**, equity lech **−0.45%**.
Tuc o moi thang do muc-lenh no **khong phan biet duoc voi PARITY**.

**Nhung `UW 2022` cua no la 159 ngay so voi 64 cua PARITY** — gap 2.5 lan, va vo tran R4.

Mot dai luong ma **nhieu vo hinh o muc trade** lam **nhay 95 ngay** thi no khong do chat luong; no do
**mot duong gia duy nhat**. `X2_EXIT48` muc 12.1 da ghi "R4 chua bao gio duoc user duyet"; X3 them
bang chung **dinh luong** rang R4 o do phan giai nay chu yeu la nhieu. **Van giu R4 trong dot nay**
(pre-reg da chot, khong duoc sua sau khi thay so) nhung day la thu phai dua len user.

Tuong tu: `X3_S50` co maxDD 2022 **−16.86%** trong khi ca nam 2022 van duong (+5.48%) — cung mot
duong gia, cung mot nam.

---

## 7. RATE THEO NAM (trich)

| tag | nam | n | win% | TSloss% | mean\|SM | p90\|SM |
|---|---|---|---|---|---|---|
| `PARITY` | 2022 | 360 | 83.33 | 16.39 | 6.552 | 10.000 |
| `PARITY` | 2023 | 290 | 88.62 | 12.07 | 8.887 | 12.696 |
| `PARITY` | 2024 | 624 | 85.74 | 15.06 | 7.266 | 14.047 |
| `PARITY` | 2025 | 784 | 84.69 | 15.05 | 6.738 | 11.997 |
| `R2` | 2022 | 364 | 83.52 | 16.21 | 6.330 | 9.402 |
| `R2` | 2025 | 791 | 84.83 | 14.92 | 6.872 | 11.498 |
| `R6` | 2024 | 625 | 85.76 | 15.04 | 7.227 | 13.495 |
| `R6` | 2025 | 784 | 84.69 | 15.05 | 6.789 | 11.741 |
| `S50` | 2022 | 429 | 83.68 | 16.08 | 6.547 | 10.042 |
| `S50` | 2025 | 853 | 84.06 | 15.12 | 6.873 | 12.473 |

Khong nam nao co `win%` hay `TSloss%` doi qua 0.7pp o bat ky arm nao.

---

## 8. PHAN QUYET TUNG VIEC — theo dung quy tac `PREREG_X3` muc 6

| viec | (1) | (2) | (3) | **PHAN QUYET** |
|---|---|---|---|---|
| **A** (`TS_CAP_STRONG_RANK` 2/4/6) | ❌ p90 theo N = 12.495 → 11.222 → 11.500 → 12.481 **khong don dieu**; `mean\|SM` 7.178 → 7.081 → 7.091 → 7.167 cung khong | ✅ `win%` khong giam ngoai CI o muc nao (con **tang** nhe o `R2`) | ❌ **0/3 muc** PASS (ca ba FAIL UW 2022) | 🔴 **KHONG CO TIN HIEU** |
| **B** (`SIM_PRE_ARM_SL=-0.50`) | ❌ `p10loser` **xau di** −3.187, CI [−13.59,+6.29] | ✅ `win%` −0.301 **trong CI** | ❌ FAIL (maxDD 2022 −16.86, UW 2022 77) | 🔴 **KHONG CO TIN HIEU** |

### => **CA HAI VIEC: NULL.** Khong de cu baseline moi (pre-reg muc 6 cam tuyet doi).

**Null nay CO THONG TIN — phan phai doc ky:**

- **Viec A truot vi mot ly do CO HOC, khong phai vi nhieu.** Bang A4 cho thay **khong ton tai gradient
  chat luong theo rank** (`mean(profit|SM)` rank 1-2 = 6.801 < rank 7-8 = 7.065). Doi cap rong tu
  "coin trong tick lac quan" sang "coin rank nong" la **hoan vi tren mot truc khong mang thong tin**.
  Ket qua dung nhu vay: `R6` = PARITY den muc khong phan biet duoc; `R2` chi doi **hinh dang** phan bo
  winner (than +0.5pp, duoi phai −1.27pp) — dung phep doi median-doi-duoi ma `C3_BASELINE` da mo ta khi
  bat B1, chi lan nay di **nguoc chieu**.
- **Cai HOC duoc va phai giu**: `S1` xep hang coin **de VAO lenh** (`edge5` +8.5% -> +19.3%), nhung thu
  hang do **KHONG dong thoi noi lenh nao dang duoc nuoi lau hon sau khi da arm +7%**. Hai cau hoi khac
  nhau. Muon dieu khien trailing theo trang thai thi phai co mot **tin hieu rieng cho pha sau-arm**
  (vd do bien dong realized cua chinh cum, hoac `maePeak` toi gio H), khong phai tai dung diem selector.
- **Viec B truot o dieu kien 1 dung theo huong da du doan.** Mot **nguong SL tinh** van la cong cu SAI —
  X2 chung minh o −20/−30, X3 chung minh o −50: chi khac la o −50 gia phai tra doi thanh
  **`p10 loser` va `mP|SL`** thay vi **`medloser`**. Cai −50% mua duoc that su la **`minloser`
  −94.64 -> −71.44** va **chi phi cat oan 1.8%** (re nhat da do). Neu lan sau ai muon "cat duoi cung"
  thuan tuy thi day la so de doc lai — nhung no **khong** cai thien duoc mot rate PRIMARY nao.
- **Khong duoc doc nguoc:** khong arm nao co equity vuot PARITY qua nhieu (`R2` 99,189 = +0.7%), va
  ca 4 arm **deu FAIL rang buoc cung**. Khong co gi de chon.

---

## 9. DU DOAN GHI TRUOC — doi chieu (`PREREG_X3` muc 7), **KHONG sua**

### 9.1 Bang A4 (muc 7.2)

| du doan | thuc te | dung? |
|---|---|---|
| `%STRONG` **khong tang** theo rank | 87.7 → 86.7 → 82.9 → 84.2 → 81.2 → 80.9 → 81.9 → 83.3 | ✅ ve HUONG chung |
| rank 1 = **95-100%**, rank 8 = **35-55%**, tong 71.5% ± 3 | rank 1 = **87.7%**, rank 8 = **83.3%**, tong **83.8%** | ❌ **SAI ca ba** |
| `n` rank 1 hon rank 8 khong qua 25% | 302 vs 276 = **+9.4%** | ✅ |
| `mean(rank 1-2) > mean(rank 7-8)` — xac suat 65% | **6.801 vs 7.065** — NGUOC lai | ❌ |

🔴 **Cai sai dang gia nhat cua toi la du doan `%STRONG` doc theo rank tu 95% xuong 40%.** Toi cho rang
`pNoPump` trong mot tick trai rong qua ban le 0.29. Thuc te **cac gia tri trong mot tick bam rat sat
nhau**, nen ban le gan nhu **hoan toan truc giao voi rank** (spread chi 6.8pp). Nghia la hien trang
con **xa "trailing theo selector"** hon ca cai toi viet trong pre-reg — ket luan dinh tinh cua muc 1.1
DUNG, nhung do lon thi toi da **danh gia THAP**.

### 9.2 Viec A (muc 7.3)

| du doan | thuc te | dung? |
|---|---|---|
| N tang => med giam, p90 tang (so hoc muc 7.1) | `R2` (25% STRONG) med **5.500** > PARITY 5.000, p90 **11.222** < 12.495 | ✅ **DUNG chinh xac** |
| `p90` **tang don dieu** theo N (70%) | 12.495 → 11.222 → 11.500 → 12.481 — **khong** | ❌ |
| `mean\|SM` **khong** ngoai CI o ca 3 muc (75%) | 3/3 trong CI (−0.097 / −0.088 / −0.011) | ✅ |
| `win%`, `TSloss%` gan nhu khong doi (±0.8pp) | thuc te **±0.15pp** | ✅ (chat hon du doan) |
| "neu `TSloss%` lech > 1.5pp thi CO BUG" | lech toi da 0.14pp; so lenh SL = **306 o ca 4 run** | ✅ khong co bug |
| `R6` gan PARITY nhat tren moi rate | **0/8 rate ngoai CI**, `n` giong het | ✅ **DUNG**, va manh hon du doan |
| >= 1 muc PASS R1-R4 (55%) | **0/3** | ❌ |
| viec A co tin hieu: **30%** | NULL | — |

### 9.3 Viec B (muc 7.4)

| du doan | thuc te | dung? |
|---|---|---|
| 🔴 `p10loser` **khong cai thien, co the xau di** -> **−50 ± 3** | **−50.07** | ✅ **trung tam** |
| `minloser` −94.64 -> **−57 ± 8** | **−71.44** | ❌ (dung huong, sai do lon) |
| `mP\|SL` **−20.5 ± 1.5** (cai thien nhe, trong CI) | **−23.146** — **xau di**, trong CI | ❌ ve huong, ✅ ve "trong CI" |
| `win%` giam 0.3-1.0pp, **trong CI** | **−0.301**, trong CI | ✅ |
| `n` cum bi cat: **70-120** | **61** | ❌ (thap hon) |
| trong so do PARITY thang: **5-12%** | **1.8%** | ❌ (thap hon nhieu) |
| chi 2022 va 2025 doi; 2023/2024 gan nhu khong doi | 2023/2024 **khong doi mot chu so** | ✅ **DUNG chinh xac** |
| PASS R1-R4 (50%) | FAIL | ❌ |
| viec B co tin hieu: **20%** | NULL | — |

### 9.4 Ket cuc tong

Du doan: ca hai null **55%** · chi A 25% · chi B 15% · ca hai 5%.
**Ket cuc: ca hai null** — roi vao nhanh xac suat cao nhat.

---

## 10. EQUITY / CAGR — **KHONG PHAI TIEU CHI**

N=5 => `E[max nhieu] = 2.57 x sqrt(2 ln 5) = 4.6pp`. Bao rieng, dan nhan.

| tag | equity | CAGR% | maxDD% (48t) | UW (48t) |
|---|---|---|---|---|
| `X3_PARITY` | 98,523 | 29.58 | −13.31 | 302 |
| `X3_R2` | 99,189 | 29.79 | −12.93 | 302 |
| `X3_R4` | 95,875 | 28.69 | −12.96 | 302 |
| `X3_R6` | 98,075 | 29.43 | −13.21 | 302 |
| `X3_S50` | 96,549 | 28.92 | **−16.86** | 302 |

Bien do **−2.7% .. +0.7%** quanh parity — **nam gon trong 4.6pp**, tuc khong phan biet duoc voi nhieu.
Khong dung de chon, va cung khong co gi de chon (4/4 FAIL rang buoc cung).

---

## 11. SAI LECH SO VOI DE BAI — Kaggle, va con so lam co so quyet dinh

De bai yeu cau **5 kernel Kaggle song song**. **Da chay TUAN TU tren Oracle.** Ly do **do duoc**,
khong doan — theo dung quy tac thoat da chot o `PREREG_X3` muc 3 va muc 8:

1. **`tools/kaggle_sim.py` DA duoc sua** (tra no `X2_EXIT48` muc 10, commit **truoc** khi chay):
   `TICKER_DS` them `wfo-ticker-2024h2` / `-2025h1` / `-2025h2`; guard `len(tk) < 912` -> **1,461**.
   🔴 Con mot bay nua da phat hien va sua: `TICKER_MIN_DAYS` la hang so **module**, KHONG ton tai trong
   namespace cua `KERNEL_TEMPLATE` (template chi duoc thay dung mot cho `__CFG_JSON__`) => de nguyen
   se `NameError` tren kernel. Nay day qua `CFG["ticker_min_days"]` + tham so `submit(..., ticker_min_days=)`.
2. **Do thuc throughput upload Oracle -> Kaggle: 3.23 MB/s** (dataset thu 95MB het **29.4s**).
3. **Bundle X3 can upload: 5.32 GB** = dataset WFO 48 thang **4.289 GB** (`funding.bin` 4.198 GB) +
   bins X1 **0.931 GB** + jar 0.095 GB.
4. => **upload thuan = 1,647 s = 27.5 phut**, chua ke Kaggle xu ly dataset 5.3GB, do tre mount, va
   rui ro dut giua chung. So voi **52 phut** cho 4 arm tuan tu tren Oracle (12.9 phut/run) thi duong
   Kaggle **khong nhanh hon** ma **them rui ro**.

**Ket luan: duong Kaggle 48 thang gio da THONG ve code, nhung nut that la BANG THONG, khong phai code.**
Ai muon dung no phai upload 5.3GB mot lan (sau do doi profile/jar thi chi phai upload lai jar 95MB —
luc do Kaggle moi thang). Ghi vao `QUEUE`.

Dataset thu `chuyendinh/x3-speed-probe` (private, 95MB) con tren Kaggle — xoa duoc tuy y, khong ai doc.

---

## 12. ARTIFACT / TAI LAP

| artifact | duong dan |
|---|---|
| jar | `target/binance-java-sdk-1.2.4.jar`, md5 `01ca3461fb98f5c78e0a98055c5fe948` |
| profiles | `profiles/x3_{parity,r2,r4,r6,s50}.properties` — moi cai khac `x1_c3` dung **2 dong** |
| runner Oracle | `research/pipeline/x3/run_x3_sim.sh` (cong hoi quy tu dong, `exit 9` neu FAIL) |
| runner Kaggle | `research/pipeline/x3/run_x3_kaggle.py` (**chua chay** — xem muc 11) |
| cham diem | `research/analysis/x3_rates.py` |
| run | `/home/ubuntu/java/devrun/X3_{PARITY,R2,R4,R6,S50}` |
| log | `/home/ubuntu/x3log/build_ds.out`, `/home/ubuntu/x3_{parity,arms,score}.out` |
| dataset WFO | `/home/ubuntu/wfo_ds_x1` (4.0G) — **XOA sau khi cham diem**; tai tao bang runner |

```bash
R=/home/ubuntu/src/BinanceFuturesJava
bash $R/research/pipeline/x3/run_x3_sim.sh
python3 $R/research/analysis/x3_rates.py
rm -rf /home/ubuntu/wfo_ds_x1
```

---

## 13. THE MO SAU DOT NAY (khong lam trong dot nay, khong duoc tu chay)

1. 🔴 **R4 (underwater) phai dua len user.** X3 cho bang chung dinh luong: `R6` khong phan biet duoc
   voi PARITY o **moi** rate muc lenh (0/8 ngoai CI, `n` va `win%` giong het) nhung `UW 2022` 64 -> 159.
   Mot rang buoc bi nhieu single-realization lam nhay 95 ngay thi khong con la rang buoc chat luong.
   **Khong duoc tu ha hoac tu bo** — day la nut RISK PREFERENCE cua user.
2. **Truc "trailing theo trang thai" van chua ai cham.** X3 chi chung minh **rank selector KHONG phai**
   tin hieu cho pha sau-arm. Tin hieu cho pha do phai do chinh pha do sinh ra (vd bien dong realized cua
   cum, hoac `maePeak`/thoi gian tu luc arm). Phai co pre-reg rieng.
3. **`TS_MAX_GAP` / `TS_MAX_GAP_WEAK` (0.08 / 0.03) van chua bao gio duoc quet tren 48 thang.**
   X3 chi doi **AI duoc cap nao**, khong doi **cap la bao nhieu**. `W1` truc A/C van la vung trang.
4. **Duong Kaggle 48 thang: nut that la bang thong (5.32GB @ 3.23 MB/s), khong phai code** (muc 11).
5. **KHONG duoc them muc thu tu cho truc S.** X2 (2 muc) + X3 (1 muc) da dong truc nay o ba do sau
   khac nhau va ca ba deu NULL vi **cung mot co che**: nguong tinh dun phan bo lenh thua thanh cot.
