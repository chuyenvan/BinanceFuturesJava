# RESULT — "SL CUNG 7% -> 3%" tren NEN PRODUCTION (FLATGRID KEEPLEG0)

Pre-reg: `docs/prereg/PREREG_SL_7_TO_3.md` (commit `ce353df`, viet/chot **TRUOC** khi push kernel).
Runner: `research/analysis/sl3_run.py`; scorer: `research/analysis/sl3_score.py`;
MTM moc phut: `research/analysis/sl3_intraday.py` (tai dung logic da nghiem thu cua
`docs/result/RESULT_INTRADAY_DD.md`). Cua so **DEV 2021-07-01..2025-12-31** (KHONG cham
2026/holdout/242/shadow). Sim chay **Kaggle CPU kernel** (`docs/runbooks/KAGGLE_SIM.md`), khong chay
Java/sim tren Oracle, khong `claude-run`. Chi phi Kaggle **0**. 5 chan chay **SONG SONG** 1 vong.
Bang chung tho: `/home/ubuntu/sl3/run.log` · `score.txt` · `score.json` ·
`intraday/report_sl3_intraday.txt` · `intraday/intraday_dd.json` · `kaggle_sim/out/sl3-*`.

---

## 0. CONG PARITY — PASS (dieu kien doc ket qua)

| cong | doi tuong | ket qua |
|---|---|---|
| **P** | `sl3-base` (KHONG override) = `t170_flat_keepleg0` | **n = 1,085 · equity = 103,083 · md5 `99e42b75cf1a2142f9cd14dc72e371ba`** = **dung** |

⇒ Nen Kaggle tai hien **tung byte** cau hinh production dang chay. `symbol_mapper = 863` ca 5 chan.
Doi chieu co che: so dong `PREARM_SL sym=` trong `logs/sim.out`:
**base 0 · V1 0 · V2 1,862 · V3 1,914 · V4 827** ⇒ nhanh SL cung **CO BIND THAT** o V2/V3/V4,
va **khong chay** o base/V1 (dung nhu pre-reg §2).

---

## 1. SU THAT THAM SO — "7%" LA **ARM**, KHONG PHAI SL

| ten THAT | y nghia | base | V1 | V2 | V3 | V4 |
|---|---|---|---|---|---|---|
| `SIM_RATE_PROFIT_STOP_MARKET` | **nguong ARM** cua trailing (`maxPrice >= entry*(1+x)`) — **khong phai stop-loss** | 0.07 | **0.03** | 0.07 | **0.03** | 0.07 |
| `SIM_PRE_ARM_SL` | **SL CUNG truoc arm** tren `firstEntryPrice`, am = cat `-X%`, 0 = TAT | 0 | 0 | **-0.03** | **-0.03** | **-0.07** |
| `SIM_HARD_SL_PCT` | key CU, **da chet o HEAD** (khong con `Cfg.get` nao) | — | — | — | — | — |

`SIM_LOSER_TIME_STOP_HOURS=168` giu nguyen o ca 5 chan. Profile day du tung chan:
`profiles/sl3_base|v1_arm03|v2_sl3|v3_both|v4_sl7.properties` (= `x1_gs_t170` + 2 dong KEEPLEG0 +
dong thay doi; `sl3_base` chi thieu 2 dong `CONC_CAP_PERCOIN_*` so voi `t170_flat_keepleg0` —
2 dong do da chung minh **no-op byte-identical** tren nen nay, `RESULT_GATESCALE_KEEPLEG0` §1).

---

## 2. CO CHE + CHAT LUONG LENH

| chan | n | win% | **TSloss%** | mP\|SM | mP\|SL | meanP | hold_h | turnover | Σfunding/ΣPnL | PREARM_SL |
|---|---|---|---|---|---|---|---|---|---|---|
| **moc (KEEPLEG0)** | 1,085 | 88.20 | 10.32 | 7.961 | −19.300 | 5.147 | 5.0 | 0.660 | −3.46% | 0 |
| **V1 arm 3%** | 1,503 | 93.48 | **2.59** | 3.636 | −20.493 | 3.010 | **0.5** | 0.914 | −2.93% | 0 |
| **V2 SL cung −3%** | 3,021 | 38.23 | **61.64** | 7.553 | −3.918 | 0.483 | 0.2 | 1.838 | +2.34% | 1,862 |
| **V3 ca hai** | 4,219 | 53.50 | 45.37 | 3.674 | −3.910 | 0.233 | 0.1 | 2.566 | +0.76% | 1,914 |
| **V4 SL cung −7%** | 2,013 | 58.32 | 41.18 | 7.522 | −7.991 | 1.133 | 0.8 | 1.224 | −4.57% | 827 |

**Doc ra:**
- **V1 (dung nghia owner hoi):** `n` **+38%** (1,085 → 1,503), `TSloss%` **10.32 → 2.59**,
  `win%` 88.20 → 93.48, `hold` 5.0h → **0.5h**. Doi lai: `mP|SM` **7.961 → 3.636** (moi lenh
  thang an it hon vi arm som ⇒ tranh bi chot loi nhuan som), `meanP` 5.147 → 3.010.
  ⇒ **co che dung chieu nhu ky vong** ("nhieu lenh, on dinh hon, an nho hon").
- **SL cung (V2/V3/V4):** `TSloss%` **no ra** dung nhu pre-reg du kien (10.32 → 41–62%),
  `mP|SL` duoc "keo len" (−19.30 → −3.92/−7.99) **nhung do la he qua co hoc**: loser bi cat o
  −3%/−7% nen phan bo loser **don lai tai dung muc cat** (dung nhu `X2_S20/S30` da do), khong
  phai "nha cap bot lo". `hold` tut ve 0.1–0.8h, `turnover` len 1.22–2.57 ⇒ **chi phi/thoi gian
  giu tang theo**, va `n` tang 1.9–3.9x trong khi equity GIAM (muc 6).

---

## 3. 5 RATE + CI vs MOC (block-72h, 2000 rep, seed 20260905; ngoai **CA HAI** do rong)

CI hien o do rong **rong hon** = `inflate(k)`, **k = 4** (V1..V4 so voi moc) ⇒ **1.665109**.
"Huong" theo quy uoc: win% ↑ · TSloss% ↓ · mP|SM ↑ · mP|SL ↑ · meanP ↑ = **TOT**.

| chan | win% | TSloss% | mP\|SM | mP\|SL | meanP | **TOT** | **XAU** |
|---|---|---|---|---|---|---|---|
| **V1 arm3** | **+5.277** [1.420, 9.502] TOT | **−7.728** [−11.784, −4.080] TOT | **−4.325** [−5.434, −3.166] XAU | −1.194 (trong CI) | **−2.137** [−3.834, −0.348] XAU | **2/5** | **2/5** |
| **V2 SL−3** | −49.970 XAU | +51.313 XAU | −0.408 (trong) | **+15.382** TOT | −4.664 XAU | 1/5 | **3/5** |
| **V3 both** | −34.707 XAU | +35.044 XAU | −4.287 XAU | **+15.390** TOT | −4.914 XAU | 1/5 | **4/5** |
| **V4 SL−7** | −29.882 XAU | +30.860 XAU | −0.439 (trong) | **+11.309** TOT | −4.013 XAU | 1/5 | **3/5** |

(so ngoac = CI @1.665109; moi rate ghi tren deu **ngoai ca** CI @1.21 **va** CI @1.665109.)

**(V1 la chan duy nhat co tin hieu TOT, nhung KHONG sach:** 2 rate **TOT** (win%, TSloss%) **di kem
2 rate XAU** (mP|SM, meanP) ⇒ vi pham dieu kien (c) "0 rate XAU".) Doi chieu **T170**
(`x1_gs_t170`, phu — KHONG quyet dinh, do trong cung vong nay): **moc 0 TOT/0 XAU** (do rong
`inflate(4)` rong hon nen moc khong con rate nao ngoai CI) · V1 **2 TOT/2 XAU** · V2 **1/3** ·
V3 **1/4** · V4 **1/3** ⇒ cung mot ket luan.

---

## 4. maxDD + UW TREN **MTM MOC PHUT** (BAT BUOC — `RISK_APPETITE` §7.3)

Tai kiem truoc khi bao cao (`sl3_intraday.py`, dung khuon `RESULT_INTRADAY_DD`):
**V1** `CAP0+Σpnl` vs `b_final` **PASS** ca 5 chan (|diff| 0.18–0.66 USDT);
**V2/V4** `equity_mtm(00:00Z)` vs `b+unP` in ra: **max|err| 5.37 / 1.74 / 1.77 / 1.83 / 1.79 USDT**,
tuong doi **≤ 0.0129% equity** (nguong AMENDMENT-1 0.05%) ⇒ **PASS ca 5**;
**V5** maxDD(chuoi phut lay mau 00:00Z) vs maxDD(artifact NGAY) lech **≤ 0.004 pp** ⇒ **PASS ca 5**.
⚠️ **V3** (`min_chay(unP_low)` vs `unPMin` in ra) **PASS** o base (0.001%) va V1 (0.002%) nhung
**FAIL** o V2/V3/V4 (336% / 176% / 103%): khi `SIM_PRE_ARM_SL` bat, sim **dong cum tai gia stop**
(`exitPrice = min(stopLevel, min(open,close))`) nen cuc tri am ma sim ghi nhan bi **chan tren boi
muc stop** (v2: sim −186 vs recon −810), con recon danh dau leg tai `bar.low` cua nen bi cat.
⇒ **bien the `P=bar.low` KHONG dung duoc cho chan co SL cung**; **day khong phai loi cua chuoi
`P=close`** (V2/V4/V5 PASS), nen moi so maxDD/UW duoi day **dung mark `close`** — dung khau vi.

### 4.1 Toan ky (2021-07-01 .. 2025-12-30)

| chan | maxDD NGAY | UW NGAY | **maxDD PHUT** | **UW PHUT (ngay)** | ΔmaxDD (pp) | ΔUW |
|---|---|---|---|---|---|---|
| moc | −11.21% | 147 | **−19.96%** | 147.2 | −8.75 | +0.2 |
| V1 arm3 | −5.91% | 118 | **−19.51%** | 144.4 | −13.60 | +26.4 |
| V2 SL−3 | −35.35% | 1,618 | **−36.11%** | **1,618.1** | −0.76 | +0.1 |
| V3 both | −56.13% | 1,618 | **−56.57%** | **1,618.1** | −0.43 | +0.1 |
| V4 SL−7 | −14.51% | 486 | **−20.94%** | **328.4** | −6.43 | −157.6 |

### 4.2 Theo nam (maxDD% / UW-ngay) — **PHUT** (moc phut), NGAY trong ngoac

| chan | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| moc | −11.05 / 37 (−2.46/37) | −15.43 / 74 (−11.21/72) | −5.03 / 64 (−2.73/63) | −12.16 / 91 (−6.60/92) | **−19.96 / 129** (−4.23/52) |
| V1 | −10.60 / 39 | −13.96 / 75 | −3.14 / 79 | −10.22 / 117 | **−19.51 / 127** |
| V2 | −15.62 / 158 | −28.69 / 344 | −2.61 / 89 | −16.49 / 273 | −21.98 / 165 |
| V3 | −20.02 / 158 | **−36.17 / 343** | −2.02 / 113 | −20.85 / 363 | −27.03 / 330 |
| V4 | −9.59 / 107 | −16.20 / 234 | −2.65 / 79 | −18.24 / 274 | −20.94 / 165 |

**Van de nhu cu:** chuoi NGAY **che mat 0.4–13.6 pp** maxDD (lon nhat o **2025** va o **V1**);
nam xau nhat theo phut la **2025** (khong phai 2022). Rieng V2/V3 UW = **1,618 ngay**
(≈ ca cua so 1,644 ngay) ⇒ **duoi dinh gan nhu TOAN KY**, khong phai "lo tam thoi ngan".

---

## 5. RAO CUNG `RISK_APPETITE` §7 — theo **nam** VA **toan ky** (maxDD/UW = moc phut)

| chan | maxDD_ky | UW_ky | qmin_ky | conc | nam am | **R-MOI 40/250/−20/ko nam am/conc15** | R-CU 30/200/−15 |
|---|---|---|---|---|---|---|---|
| moc | −19.96% | 147.2 | −1.08% | 7.12% | khong | **PASS** | PASS |
| **V1 arm3** | −19.51% | 144.4 | −1.32% | 7.65% | khong | **PASS** | PASS |
| V2 SL−3 | −36.11% | **1,618** | −16.95% | 5.37% | **4/5 nam** | **FAIL** (UW_ky; nam am 2021/2022/2024/2025; 2022 UW 344 · 2024 UW 273) | FAIL |
| V3 both | **−56.57%** | **1,618** | **−23.49%** | 5.64% | **4/5 nam** | **FAIL** (maxDD_ky, UW_ky, qmin_ky; 2022 UW343 · 2024 UW363 · 2025 UW330) | FAIL |
| V4 SL−7 | −20.94% | **328** | −8.62% | 5.09% | **2/5 nam** | **FAIL** (UW_ky 328; nam am 2021/2022; 2024 UW 274) | FAIL |

⇒ **Chi moc va V1 qua het rao.** Ba chan SL cung (V2/V3/V4) **FAIL nang** — dac biet UW (dai
underwater) va "nam am", dung loai rui ro ma `RISK_APPETITE` §7 duoc viet ra de chan.

---

## 6. BANG PnL CHI TIET THEO NAM (n · PnL · ret% · maxDD% **phut** · UW **phut** · qmin% · equity)

**moc KEEPLEG0** (toan ky: equity 103,083 · PnL +68,083 · maxDD phut −19.96% · UW 147.2)

| nam | n | PnL | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|
| 2021 | 149 | +4,273 | +12.21 | −11.05 | 37.0 | +4.44 | 39,272 |
| 2022 | 196 | +4,943 | +12.59 | −15.43 | 74.0 | −1.08 | 44,215 |
| 2023 | 126 | +15,376 | +34.96 | −5.03 | 64.4 | −0.37 | 59,673 |
| 2024 | 281 | +19,210 | +32.13 | −12.16 | 91.5 | −0.92 | 78,801 |
| 2025 | 333 | +24,282 | +30.81 | −19.96 | 129.0 | +1.27 | 103,083 |

**V1 arm 3%** (equity 79,773 · PnL +44,773 · maxDD phut −19.51% · UW 144.4) — *nhieu lenh nhat trong
so chan CON QUA RAO, nhung PnL/equity thap hon moc*

| nam | n | PnL | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|
| 2021 | 204 | +1,762 | +5.03 | −10.60 | 39.0 | +1.14 | 36,761 |
| 2022 | 344 | +6,257 | +17.02 | −13.96 | 74.6 | +1.66 | 43,019 |
| 2023 | 141 | +10,654 | +24.77 | −3.14 | 78.6 | −1.32 | 53,673 |
| 2024 | 347 | +10,468 | +19.50 | −10.22 | 116.5 | −0.69 | 64,141 |
| 2025 | 467 | +15,632 | +24.37 | −19.51 | 127.0 | +0.72 | 79,773 |

**V2 SL cung −3%** (equity 25,144 · PnL −9,856 · maxDD phut −36.11% · UW 1,618.1)

| nam | n | PnL | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|
| 2021 | 440 | −4,179 | −11.94 | −15.62 | 158.1 | −7.60 | 30,821 |
| 2022 | 1,051 | −7,750 | −25.15 | −28.69 | 344.0 | −15.25 | 23,070 |
| 2023 | 166 | +5,651 | +24.50 | −2.61 | 88.6 | +0.06 | 28,721 |
| 2024 | 576 | −699 | −2.43 | −16.49 | 272.7 | −7.64 | 28,022 |
| 2025 | 788 | −2,878 | −10.27 | −21.98 | 164.9 | −16.95 | 25,144 |

**V3 arm 3% + SL cung −3%** (equity 15,573 · PnL −19,427 · maxDD phut −56.57% · UW 1,618.1)

| nam | n | PnL | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|
| 2021 | 596 | −6,340 | −18.11 | −20.02 | 158.1 | −10.42 | 28,660 |
| 2022 | 1,595 | −9,796 | −34.18 | −36.17 | 343.3 | −19.90 | 18,864 |
| 2023 | 181 | +3,817 | +20.23 | −2.02 | 113.1 | −0.14 | 22,681 |
| 2024 | 760 | −2,789 | −12.30 | −20.85 | 363.5 | −8.43 | 19,892 |
| 2025 | 1,087 | −4,319 | −21.71 | −27.03 | 330.3 | −23.49 | 15,573 |

**V4 SL cung −7%** (equity 43,869 · PnL +8,869 · maxDD phut −20.94% · UW 328.4)

| nam | n | PnL | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|
| 2021 | 276 | −652 | −1.86 | −9.59 | 107.0 | −1.80 | 34,348 |
| 2022 | 615 | −2,748 | −8.00 | −16.20 | 234.4 | −7.89 | 31,600 |
| 2023 | 138 | +9,698 | +30.69 | −2.65 | 78.6 | −0.00 | 41,297 |
| 2024 | 427 | +973 | +2.36 | −18.24 | 273.9 | −8.62 | 42,270 |
| 2025 | 557 | +1,599 | +3.78 | −20.94 | 164.9 | −6.88 | 43,869 |

*(PnL/equity **bao rieng, KHONG dung de chon** — ghi o day chi de owner thay cai gia phai tra.)*

---

## 7. KET LUAN — **CA 4 BIEN THE: NULL** (vong thu **9** tren truc EXIT)

| chan | TOT ngoai CI | XAU ngoai CI | rao MOI | **E-PASS** | ket qua |
|---|---|---|---|---|---|
| V1 arm 3% | 2/5 | 2/5 | PASS | FAIL (**vi pham "0 rate XAU"**) | **NULL** |
| V2 SL cung −3% | 1/5 | 3/5 | FAIL | FAIL | **NULL** |
| V3 arm3+SL−3 | 1/5 | 4/5 | FAIL | FAIL | **NULL** |
| V4 SL cung −7% | 1/5 | 3/5 | FAIL | FAIL | **NULL** |

- **Tra dung cau hoi owner** ("SL cung 7% -> 3%"): trong baseline **khong ton tai SL cung 7%** —
  7% la **nguong ARM** cua trailing. Do **ca hai nghia**:
  - **arm 7%→3% (V1)**: **khong hon** theo luat (2 rate TOT nhung **2 rate XAU** ngoai CI; rao qua
    nhung "0 rate XAU" khong dat). **Co tin hieu do luong ro** (n +38%, TSloss% 10.32→2.59,
    hold 5.0h→0.5h, maxDD/UW phut hoi tot hon) **nhung cai mat la `mP|SM` 7.96→3.64 va `meanP`
    5.15→3.01** ⇒ "nhieu lenh, on dinh hon, an nho hon". **KHONG tu tich hop.**
  - **SL cung (V2/V3/V4)**: **hai ro rang** — FAIL rao nang (UW 328–1,618 ngay, 2–4/5 nam am,
    maxDD phut toi **−56.57%** o V3). Tai lap dung ket luan cu cua truc SL cung
    (`X2_S20/S30`, `X3_B`, `SL_ADAPT_HARDSL`): cat lo som **khong** lam bot lo, no **doi cho** lo
    (tu "giu lo am tham" sang "loss realized lien tuc") va **keo dai underwater**.
- **Danh so vong:** day la **vong 9** tren truc **exit** (8 vong truoc deu NULL: hinge · ladder ·
  peak-close · 17 policy · 20 policy · cap 10/30 · GD92xexit · high-N x exit). Ket qua vong nay
  **NULL**, dong thoi **lan dau do duoc `UW` tren MTM moc phut cho cac chan SL cung** (truoc day
  chua ai do) — va no cho thay ly do co hoc tai sao SL cung **luon** that bai o khau vi rao cung.
- **De xuat buoc tiep (KHONG tu lam, cho owner chot):** neu owner van muon "arm som de on dinh",
  huong duy nhat con hop le ve ky luat la do **arm trung gian 4–5%** (thay vi 3%) va/hoac **arm
  theo bien dong** — nhung phai pre-reg vong moi; **khong** chinh tham so cua V1 sau khi da thay so.
- Khong co ket quan nao bi doi huong boi cach do maxDD (moc phut vs ngay) trong vong nay:
  **V1 PASS rao o ca hai cach do**, V2/V4 cung FAIL o ca hai (V4: ngay UW 486 → phut 328).

---

## 8. Bang chung / commit

- Kaggle: `chuyendinh/sim-sl3-base|sl3-v1-arm03|sl3-v2-sl3|sl3-v3-both|sl3-v4-sl7` (private) ·
  output `kaggle_sim/out/<tag>/` (co `prof_run.properties` = bang chung override).
- Script: `research/analysis/sl3_run.py`, `sl3_score.py`, `sl3_intraday.py`.
- Profile: `profiles/sl3_*.properties` (5 file).
- Khong push. Khong cham 2026. Khong chay Java/sim tren Oracle.
