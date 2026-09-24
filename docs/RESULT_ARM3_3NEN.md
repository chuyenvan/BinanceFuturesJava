# RESULT — ARM 7% -> 3% tren 3 NEN (6 chan) + BANG THEO NAM

Pre-reg: `docs/PREREG_ARM3_3NEN.md` (commit **`fb047e1`**, chot **TRUOC** khi push kernel).
Runner: `research/analysis/arm33_run.py` (Kaggle CPU, chi phi 0); scorer: `research/analysis/arm33_score.py`;
MTM moc phut: `research/analysis/arm33_intraday.py` (tai dung logic da nghiem thu
`docs/RESULT_INTRADAY_DD.md` / `RISK_APPETITE` §7.3).
Cua so **DEV 2021-07-01..2025-12-31** (khong cham 2026). Raw: `/home/ubuntu/arm33/`
(`score.txt` · `score.json` · `intraday/`) · `/home/ubuntu/arm33_run.log`.

**Cau hoi (nguyen van owner)**: *"toi muon giam arm 7% hien tai ve 3% do lai voi KEEPLEG0 va T100,
GD92 nua vay la 6 cai chay di roi gui full ket qua cua 6 cai theo nam co ca so lenh va total pnl"*.

⇒ **6 chan = 3 nEN (KEEPLEG0 / T100 / GD92) × 2 muc ARM (7% = moc, 3% = arm3)**.
**CHI doi DUY NHAT `SIM_RATE_PROFIT_STOP_MARKET`** (nguong **ARM cua trailing**, KHONG phai SL —
`RESULT_SL_7_TO_3.md` §1). Khong bat `SIM_PRE_ARM_SL`, khong doi key nao khac.

---

## 0. CONG PARITY — PASS (3 moc)

| cong | tag | md5 `printDone.csv` | n | equity |
|---|---|---|---|---|
| P-A | `kg0-g170` (KEEPLEG0) | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1,085 | 103,083 |
| P-B | `hn-t100` (T100) | **`dc16e4da6ff6cb7b8d41c592bc3d9c45`** | 2,559 | 121,770 |
| P-C | `hn-g92` (GD92) | **`cd913759ecd4bf50adab2b818eaf9525`** | 2,632 | 133,944 |

- `hn-g92` co `[GATE-ROLL] BAT: pct=0.92 window=90d | 39510 moc | nguong 0.456-1.265%` (1 dong) ✓.
- Mapper **863** ca 3. `kg0-g170` **byte-identical `sl3-base`** (cung batch voi A2) ⇒ cap A sach.

**Kiem "chi 1 key doi"** (`prof_run.properties`, moc vs arm3):

| cap | key khac | ngoai `SIM_RATE_PROFIT_STOP_MARKET` |
|---|---|---|
| A `kg0-g170` → `sl3-v1-arm03` | 2 | `WFO_FUNDING_PRED_DIR` (chi **duong mount** Kaggle: `/kaggle/input/...` vs `/kaggle/input/datasets/...`, cung 1 dataset `sim-x1-2021-bundle`) |
| B `hn-t100` → `hn-t100-arm3` | **1** | **0** |
| C `hn-g92` → `hn-g92-arm3` | **1** | **0** |

- B/C: **chi 1 key**, dung nhu pre-reg. A: khac them 1 **duong dan mount** (khong phai key hanh vi;
  A1 `kg0-g170` == `sl3-base` byte-identical, va A2 `sl3-v1-arm03` cung batch do) ⇒ cap A van sach.
- `jar_sha256`: A1/A2 = `2c2f8aef…` (module); B/C = `bb282f40…` (module `b50833f` + cherry-pick
  `-n 1db0613` co `GateRollingThreshold`) — **moc va arm3 cua moi cap dung CUNG jar**.
  `git checkout -- src/` da tra `module` nguyen trang; **khong merge** `gd92-recheck`.
- Sim moi: `hn-t100-arm3` (n 3,431 / eq 80,964) · `hn-g92-arm3` (n 3,451 / eq 87,035), mapper 863.

---

## 1. *** BANG 6 CHAN — n VA PnL THEO NAM (nguon PnL: realized `pnl` USDT) ***

| nEN | arm | 2021 n | 2021 PnL | 2022 n | 2022 PnL | 2023 n | 2023 PnL | 2024 n | 2024 PnL | 2025 n | 2025 PnL | **TONG n** | **TOTAL PnL** | equity cuoi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **KEEPLEG0** | 0.07 (moc) | 149 | 4,273 | 196 | 4,943 | 126 | 15,376 | 281 | 19,210 | 333 | 24,282 | **1,085** | **68,083** | 103,083 |
| **KEEPLEG0** | **0.03 (arm3)** | 204 | 1,762 | 344 | 6,257 | 141 | 10,654 | 347 | 10,468 | 467 | 15,632 | **1,503** | **44,774** | 79,773 |
| **T100** | 0.07 (moc) | 293 | 3,248 | 406 | 6,619 | 308 | 27,014 | 668 | 32,687 | 884 | 17,202 | **2,559** | **86,770** | 121,770 |
| **T100** | **0.03 (arm3)** | 377 | 2,330 | 572 | 2,638 | 372 | 13,333 | 848 | 17,949 | 1,262 | 9,714 | **3,431** | **45,964** | 80,964 |
| **GD92** | 0.07 (moc) | 277 | 1,343 | 416 | 2,637 | 509 | 29,241 | 792 | 29,714 | 638 | 36,009 | **2,632** | **98,944** | 133,944 |
| **GD92** | **0.03 (arm3)** | 352 | 2,036 | 572 | **−438** | 606 | 14,022 | 1,020 | 17,897 | 901 | 18,518 | **3,451** | **52,036** | 87,035 |

Khoa bang `equity cuoi nam`: `kg0-g170` … `hn-g92-arm3` (tung nam) trong `/home/ubuntu/arm33/score.txt` [5].
(2021 = nua nam 2021-07-01..12-31.)

### 1b. Cot phu bat buoc

| nEN | arm | n | win% | TSloss% | meanP | hold (h) | **maxDD NGAY %** | **maxDD PHUT %** | UW ngay | turnover | Σfunding/ΣPnL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KEEPLEG0 | 0.07 | 1,085 | 88.20 | 10.32 | 5.147 | 5.0 | −11.21 | **−19.96** | 147 | 0.660 | −3.46% |
| KEEPLEG0 | **0.03** | 1,503 | 93.48 | **2.59** | 3.010 | **0.5** | −5.91 | **−19.51** | 144 | 0.914 | −2.93% |
| T100 | 0.07 | 2,559 | 84.33 | 15.36 | 3.173 | 11.1 | −16.13 | **−26.26** | 248 | 1.557 | −10.73% |
| T100 | **0.03** | 3,431 | 92.42 | **5.28** | 1.783 | **1.2** | −12.60 | **−27.32** | 339 | 2.087 | −8.59% |
| GD92 | 0.07 | 2,632 | 83.66 | 16.15 | 3.315 | 12.5 | −16.55 | **−24.30** | 278 | 1.601 | −6.33% |
| GD92 | **0.03** | 3,451 | 92.73 | **5.42** | 1.883 | **1.4** | −13.63 | **−21.30** | 478 | 2.099 | −5.29% |

`mP|SM` / `mP|SL` / `meanP` + `hold` (day du) o `/home/ubuntu/arm33/score.txt` [2].

**Doc ra (giong het nhau tren CA 3 nEN):**
- `n` **+31…+39%** (1,085→1,503 · 2,559→3,431 · 2,632→3,451); `TSloss%` **giam manh**
  (10.32→2.59 · 15.36→5.28 · 16.15→5.42); `win%` **tang**; `hold` **tut manh** (5.0→0.5 · 11.1→1.2 · 12.5→1.4 h).
- Doi lai: `mP|SM` **7.96→3.64 · 7.23→3.09 · 7.23→3.12** va `meanP` **5.15→3.01 · 3.17→1.78 · 3.32→1.88**
  ⇒ **moi lenh an it hon ~2x**.
- **TOTAL PnL tut nang**: KEEPLEG0 **68,083 → 44,774 (−34.2%)** · T100 **86,770 → 45,964 (−47.0%)** ·
  GD92 **98,944 → 52,036 (−47.4%)**; **equity cuoi −22.6% / −33.5% / −35.0%**.

---

## 2. CHAM 5 RATE + CI (block-72h, 2000 rep, seed 20260905, anchor 2021-07-01)

`k=3` ⇒ `inflate(3)=1.482304`. `arm3 vs MOC CUA CHINH NEN`. **NGOAI CI** = ngoai **ca hai** do rong.

| nEN | win% | TSloss% | mP∣SM | mP∣SL | meanP | TOT | XAU |
|---|---|---|---|---|---|---|---|
| **A KEEPLEG0** | **+5.277** [1.864, 9.059] TOT | **−7.728** [−11.361, −4.503] TOT | **−4.325** [−5.309, −3.290] XAU | −1.194 (trong CI) | **−2.137** [−3.643, −0.539] XAU | 2/5 | **2/5** |
| **B T100** | **+8.092** [5.802, 10.544] TOT | **−10.082** [−12.567, −7.747] TOT | **−4.144** [−4.812, −3.495] XAU | −2.429 (trong CI) | **−1.390** [−2.380, −0.394] XAU | 2/5 | **2/5** |
| **C GD92** | **+9.064** [6.570, 11.756] TOT | **−10.729** [−13.309, −8.177] TOT | **−4.115** [−4.639, −3.549] XAU | −2.623 (ngoai @1.21, trong @1.4823) | **−1.432** [−2.312, −0.535] XAU | 2/5 | **2/5** |

⇒ **Ca 3 nEN CUNG mot kieu**: 2 rate `TOT` (win% ↑, TSloss% ↓) di kem **2 rate `XAU`** (mP|SM, meanP).
⇒ Vi pham dieu kien "**0 rate XAU**" ⇒ **E-PASS = FALSE** cho **ca A, B va C**.

---

## 3. RAO CUNG `RISK_APPETITE.md` §7 (maxDD/UW = **MTM MOC PHUT**)

Khau vi hien hanh: `maxDD` nam **≤40%** · quy xau nhat **≥−20%** · `UW` **≤250** ngay ·
tap trung 1 coin **≤15%** · khong nam am.

| nEN | arm | toan ky | theo nam |
|---|---|---|---|
| A KEEPLEG0 | 0.07 | **PASS** | 5/5 nam P |
| A KEEPLEG0 | **0.03** | **PASS** | 5/5 nam P |
| B T100 | 0.07 | FAIL (`conc_ky 27.23`) | 5/5 nam P |
| B T100 | **0.03** | **FAIL NANG HON** (`UW_ky 339`, `conc_ky 20.16`, **2025 UW 252**) | 4/5 nam P |
| C GD92 | 0.07 | FAIL (`UW_ky 278`) | 5/5 nam P |
| C GD92 | **0.03** | **FAIL NANG HON** (`UW_ky 478`, `conc_ky 18.02`, **2022 nam am −1.18%**) | 4/5 nam P |

- **A**: arm3 **khong lam xau** rao (PASS ca hai; maxDD phut −19.96% → −19.51%).
- **B, C**: arm3 **lam XAU rao ro ret** — `UW` phut **248→339** (B) va **278→478** (C); them dong
  `conc` (>=15%) va **GD92-arm3 tao ra 1 nam am 2022 (−1.18%)** (moc khong co nam am).

---

## 4. KET LUAN

> **arm 3% KHONG hon moc tren BAT KY nEN nao (KEEPLEG0 / T100 / GD92).**
> Ca 3 nEN cung mot ket cuc: `n` tang ~1/3, `win%` tang / `TSloss%` giam (2 rate `TOT` **ngoai CI**),
> NHUNG `mP|SM` va `meanP` giam (2 rate `XAU` **ngoai CI**) ⇒ vi pham "0 rate XAU" ⇒ **NULL (E-PASS FALSE)**.
> Kem theo, **TOTAL PnL giam 34-47%** va **equity cuoi giam 23-35%**; tren 2 nEN nhieu lenh (T100, GD92)
> arm3 con **lam rao cung XAU hon** (UW phut +91 / +200 ngay; GD92-arm3 phat sinh 1 nam am 2022).
> ⇒ **Giu arm 7%**. Da danh doi "nhieu lenh hon" bang PnL: **doi KHONG dang** (owner doi "nhieu lenh
> de on dinh" — nhung do on dinh per-lenh chang bu duoc PnL mat di).

- Khong push. Khong cham 2026. Khong chay Java/sim tren Oracle (Kaggle, chi phi 0). Khong `claude-run`.
