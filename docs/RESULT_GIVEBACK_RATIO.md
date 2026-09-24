# RESULT_GIVEBACK_RATIO — `TS_GIVEBACK_RATIO` = 1 / 2 / 5 tren KEEPLEG0 (moc 0.5)

Pre-reg: `docs/PREREG_GIVEBACK_RATIO.md` (commit **`bca8575`**, chot **TRUOC** khi push kernel).
Runner: `research/analysis/gb_run.py` (Kaggle CPU, chi phi 0); scorer: `research/analysis/gb_score.py`;
MTM moc phut: `research/analysis/gb_intraday.py` (tai dung logic da nghiem thu `docs/RESULT_INTRADAY_DD.md`,
`RISK_APPETITE` §7.3).
Cua so **DEV 2021-07-01..2025-12-31** (khong cham 2026). Raw: `/home/ubuntu/gbr/` (`score.txt` ·
`score.json` · `intraday/`) · `/home/ubuntu/kaggle_sim/out/gb-r{1,2,5}/`.
**Vong thu 11 truc EXIT.**

**Cau hoi (nguyen van owner)**: *"`TS_GIVEBACK_RATIO 0.5` test cai nay voi 1 2 5 xem sao"*.
⇒ 4 chan, **CHI doi DUY NHAT `TS_GIVEBACK_RATIO`** (0.5 = moc / 1 / 2 / 5).

---

## 0. BUOC 0 — `TS_GIVEBACK_RATIO` co phai marker validate (`exit(2)`) khong? ⇒ **KHONG**

- `Configs.java:173-175`: doc tu **profile** (`properties.get("TS_GIVEBACK_RATIO")`), default `0.5` ⇒ key PROFILE binh thuong.
- `Configs.java:839`: nam trong **`KNOWN_PROPS`** (allowlist key code thuc su doc) ⇒ khong bi bao "dead key".
- `Configs.java:864-874`: danh sach marker THAT (`exit(2)` im lang) **chi gom `SIM_TS_GIVEBACK` va `SIM_BREAKER_MODE`**
  ⇒ `TS_GIVEBACK_RATIO` **khong** nam trong do.
- ⇒ Override qua PROFILE la dung; **khong sua Java, khong rebuild jar** (jar 3 chan moi = `2c2f8aef…`
  = **CUNG jar voi moc**), `src/` sach.

## 0b. CONG PARITY + "chi 1 key doi" — PASS

| chan | `TS_GIVEBACK_RATIO` | md5 `printDone.csv` | n | equity | jar | mapper |
|---|---|---|---|---|---|---|
| `kg0-g170` (MOC) | 0.5 | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1,085 | 103,083 | 2c2f8aef | 863 |
| `gb-r1` | 1 | `f8342d402b3c13121581e6faa3649687` | 1,071 | 97,460 | 2c2f8aef | 863 |
| `gb-r2` | 2 | `9f5eb0c5ee01abf5c933a9516a5f5919` | 1,069 | 97,801 | 2c2f8aef | 863 |
| `gb-r5` | 5 | **`9f5eb0c5ee01abf5c933a9516a5f5919`** (== r2) | 1,069 | 97,801 | 2c2f8aef | 863 |

- Moc `kg0-g170`: n / eq / md5 **dung** cong (`99e42b75` / 1,085 / 103,083) ⇒ **PASS**.
- `prof_run.properties` cua ca 3 chan moi khac moc **dung 1 key hanh vi** `TS_GIVEBACK_RATIO`;
  key con lai khac duy nhat la **duong mount** `WFO_FUNDING_PRED_DIR`
  (`/kaggle/input/sim-x1-2021-bundle` vs `/kaggle/input/datasets/chuyendinh/sim-x1-2021-bundle`,
  **cung 1 dataset**, khong phai key hanh vi) — dung nhu pre-reg §3.
- `[GATE-ROLL]`: **khong ap dung** (chi T100/GD92 moi bat; KEEPLEG0 = `kg0-g170` khong co dong nay).

---

## 1. *** BANG 4 CHAN ***

| `TS_GIVEBACK_RATIO` | n | win% | TSloss% | mP∣SM | mP∣SL | meanP | hold (h) | equity cuoi | **maxDD PHUT** | **UW PHUT (ngay)** | Σfunding/ΣPnL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **0.5 (MOC)** | 1,085 | **88.20** | **10.32** | 7.961 | −19.300 | 5.147 | **5.0** | 103,083 | −19.96% | 147.2 | −3.46% |
| **1** | 1,071 | 78.34 | 20.63 | **8.751** | **−8.744** | 5.141 | 6.8 | 97,460 | −19.95% | 144.4 | −2.69% |
| **2** | 1,069 | 79.42 | 19.55 | 8.733 | −9.578 | 5.153 | 7.0 | 97,801 | −19.96% | 144.4 | −2.68% |
| **5** | 1,069 | 79.42 | 19.55 | 8.733 | −9.578 | 5.153 | 7.0 | 97,801 | −19.96% | 144.4 | −2.68% |

(`maxDD`/`UW` = **MTM MOC PHUT**, `RISK_APPETITE` §7.3; cong nghiem thu V1/V2/V3/V5 PASS ca 4 chan,
`max|err|/equity` 0.0129–0.0154% ≤ nguong 0.05%).

**Doc ra:** `n` **giam nhe 14–16 leg**; `win%` **−8.8…−9.9 pp**; `TSloss%` **x2** (10.32 → 19.6–20.6%);
`hold` **+1.8…+2.0h** (5.0 → 6.8–7.0); nguoc lai `mP∣SL` **tot len rat manh** (−19.3 → −8.7/−9.6, tuc
lo cua lenh bi cat NONG hon) va `mP∣SM` tang nhe; **`meanP` gan nhu KHONG doi** (5.147 → 5.141/5.153).
`equity` cuoi **−5.1%…−5.4%**.

---

## 2. ⭐ SO LEG THUC SU KHAC NHAU (kiem du doan "gan nhu trung nhau")

Khoa leg day du = `(sym, start, end, status, pnl)` tu `printDone.csv`:

| cap | n_A | n_B | **leg khac** | cung `(sym,start)` ma khac `end/status/pnl` |
|---|---|---|---|---|
| 0.5 vs **1** | 1,085 | 1,071 | **2,144** | 1,022 |
| 0.5 vs **2** | 1,085 | 1,069 | **2,144** | 1,022 |
| 0.5 vs **5** | 1,085 | 1,069 | **2,144** | 1,022 |
| **1 vs 2** | 1,071 | 1,069 | **1,944** | 966 |
| **1 vs 5** | 1,071 | 1,069 | **1,944** | 966 |
| **2 vs 5** | 1,069 | 1,069 | **0** | 0 |

- **2 vs 5 = 0 leg khac** (byte-identical, cung md5) ⇒ du doan "**ratio 2 ≡ ratio 5**" **DUNG TUYET DOI**.
- **1 vs 2/5** khac **1,944 leg** — nhung da so la **dich chuyen nho**: `d_pnl` mean **+0.40 USDT**,
  sd 22.2, chi **21.9%** leg co `|d_pnl|>1 USDT` (so voi moc: mean **−4.4 USDT**, sd 84.9, **93%** leg `|d|>1`).
  ⇒ "1 gan nhu trung 2/5" dung ve **muc do**, khong dung ve **byte**.
- **0.5 vs 1/2/5: 2,144 leg khac tren tong 2,156** ⇒ **du doan "gan nhu KHONG khac moc" la SAI**.
  Nguyen nhan: `gap` doi ⇒ SL doi ⇒ **gia exit cua gan nhu MOI leg deu doi** (93% leg `|d_pnl|>1 USDT`,
  max 1,126 USDT/leg). Vi **da so lenh thuoc nhom STRONG** (selector top-8 uu tien coin de chay,
  `pNoPump` thap ⇒ `maxGap = 0.08`), khac biet `gap` khong chi o vai leg biên.

---

## 3. *** BANG PnL THEO NAM + TOTAL PnL ***

| `TS_GIVEBACK_RATIO` | 2021 n / PnL | 2022 n / PnL | 2023 n / PnL | 2024 n / PnL | 2025 n / PnL | **TONG n** | **TOTAL PnL** | equity cuoi |
|---|---|---|---|---|---|---|---|---|
| **0.5 (MOC)** | 149 / 4,273 | 196 / 4,943 | 126 / 15,376 | 281 / 19,210 | 333 / 24,282 | **1,085** | **68,083** | 103,083 |
| **1** | 150 / 3,112 | 197 / 5,601 | 125 / 14,686 | 275 / 16,672 | 324 / 22,389 | **1,071** | **62,460** | 97,460 |
| **2** | 150 / 3,162 | 197 / 5,436 | 125 / 14,604 | 275 / 17,006 | 322 / 22,593 | **1,069** | **62,802** | 97,801 |
| **5** | 150 / 3,162 | 197 / 5,436 | 125 / 14,604 | 275 / 17,006 | 322 / 22,593 | **1,069** | **62,802** | 97,801 |

(2021 = nua nam 2021-07-01..12-31. PnL = realized `pnl` USDT.)
⇒ **TOTAL PnL giam −7.8% (2/5) / −8.3% (1)**; n giam nhe; **khong nam nao am**; 2022 la nam DUY NHAT
`TS_GIVEBACK_RATIO>=1` **tot hon moc** (+658 / +493 USDT).

---

## 4. CHAM 5 RATE + CI (block-72h, 2000 rep, seed 20260905, anchor 2021-07-01)

`k=3` ⇒ `inflate(3)=1.482304`. `ratio vs MOC (0.5)`. **NGOAI CI** = ngoai **ca hai** do rong.

| chan | win% | TSloss% | mP∣SM | mP∣SL | meanP | TOT | XAU |
|---|---|---|---|---|---|---|---|
| **1** | **−9.865** [−12.741,−7.312] **XAU** | **+10.312** [+7.815,+13.107] **XAU** | **+0.790** TOT | **+10.556** TOT | −0.006 (trong CI) | 2/5 | **2/5** |
| **2** | **−8.783** [−11.503,−6.426] **XAU** | **+9.228** [+6.871,+11.892] **XAU** | **+0.772** TOT | **+9.722** TOT | +0.006 (trong CI) | 2/5 | **2/5** |
| **5** | **−8.783** [−11.503,−6.426] **XAU** | **+9.228** [+6.871,+11.892] **XAU** | **+0.772** TOT | **+9.722** TOT | +0.006 (trong CI) | 2/5 | **2/5** |

⇒ Ca 3 chan **CUNG mot kieu**: 2 rate `TOT` (`mP∣SM`, `mP∣SL`) **di kem 2 rate `XAU`** (`win%`, `TSloss%`),
`meanP` **trong CI**. Vi pham dieu kien "**0 rate XAU**" ⇒ **E-PASS = FALSE** ca 3.

---

## 5. RAO CUNG `RISK_APPETITE` §7 (maxDD/UW = **MTM MOC PHUT**)

| chan | maxDD NGAY | UW NGAY | **maxDD PHUT** | **UW PHUT** | theo nam (5/5 nam) | toan ky |
|---|---|---|---|---|---|---|
| 0.5 (MOC) | −11.21% | 147 | −19.96% | 147.2 | 5/5 P | **PASS** |
| 1 | −9.67% | 164 | −19.95% | 144.4 | 5/5 P | **PASS** |
| 2 | −9.69% | 164 | −19.96% | 144.4 | 5/5 P | **PASS** |
| 5 | −9.69% | 164 | −19.96% | 144.4 | 5/5 P | **PASS** |

- Theo nam (`maxDD phut% / UW / ret% / qmin%`, rao MOI 40/250/−20/khong nam am/conc 15):
  ca 4 chan **P** o **ca 5 nam**; `maxDD` nam xau nhat = **2025** (−19.95…−19.96%), **khong nam nao am**.
- Rao **CU** (30/200/−15) cung **PASS** ca 4 chan.
- `TS_GIVEBACK_RATIO>=1` **khong lam xau rao**: maxDD phut gan nhu khong doi (−19.96 → −19.95/−19.96),
  `UW` phut **giam nhe** 147.2 → 144.4. Cua so 2025-10-09..13: −19.57% (low −23.67%) **giong het** ca 4 chan.

---

## 6. KET LUAN (theo luat pre-reg §6)

> **`TS_GIVEBACK_RATIO` 1 / 2 / 5 = NULL tren KEEPLEG0** (vi pham "0 rate XAU": `win%` va `TSloss%`
> ngoai CI cung huong XAU; `meanP` trong CI).
>
> **Kiem du doan khoa truoc (bang so, khong bang cong thuc):**
> - ✅ "**ratio 2 ≡ ratio 5**" — **DUNG TUYET DOI**: `md5` giong, **0/1069 leg khac**, PnL nam y het.
> - ⚠️ "**1/2/5 gan nhu trung nhau**" — **GAN DUNG** ve cuong do (1 vs 2/5: 1,944 leg khac nhung
>   `d_pnl` mean +0.4 USDT, 21.9% leg `|d|>1`), **khong dung** ve byte.
> - ❌ "**gan nhu KHONG khac moc**" — **SAI**: 0.5 vs 1/2/5 khac **2,144/2,156 leg** (93% leg `|d_pnl|>1`),
>   `win%` −8.8…−9.9 pp, `TSloss%` ×2, `hold` +1.8…+2.0 h. Ly do: nhom STRONG (`maxGap=0.08`) chiem
>   **da so** leg, nen `gap = 0.5*peak` → `0.08` doi **gia exit cua gan nhu moi leg**, khong chi o vai bien.
>
> **Danh doi:** `n` −14..−16 leg, `TOTAL PnL` **−7.8% (2/5) / −8.3% (1)**, equity −5.1…−5.4%;
> doi lai `mP∣SL` **nong hon nhieu** (−19.3 → −8.7/−9.6) va rao cung **khong xau hon**.
> ⇒ Ket cuc: **giu `TS_GIVEBACK_RATIO = 0.5`**. Khong GO.

- Khong push. Khong cham 2026. Khong chay Java/sim tren Oracle (Kaggle, chi phi 0). Khong `claude-run`.
