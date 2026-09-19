# PREREG_GATE_CALIB — hieu chuan gate: do 2 diem scale quanh T170 (1.30 / 2.10) tren wfo_ds_x1_2021

Chot: 2026-09-20, commit TRUOC khi chay. Baseline = **T170** (`profiles/x1_gs_t170.properties`, dataset
`wfo_ds_x1_2021`, `TIME_RUN=20210701`, cua so 2021-07..2025-12). md5 printDone
`efb793e2468ca3a7318da0f0ad23d4fc`, n=1089 lenh, equity 111,070. `[GATE] scale=1.7 base=0.008
n_cand=17925650 n_pass=841`. KHONG cham 2026/HOLDOUT, KHONG cham 242, KHONG push.

## 0. Cau hoi + vi sao KHONG phai open-search

Docs `DESIGN_GATE_TARGET_ALIGNMENT.md` (+ dinh chinh `0a10389`) + `RESULT_GATE_H72.md` +
`RESULT_GATE_TOPK_LABEL.md` ket luan: trong kien truc `map_s1a2`, **thu tu xep hang cua gate BI BO**
(`c4_build_map.py` chi lay multiset `p` cua gate theo hang S1). Gate chi con la **kenh LOC/HIEU CHUAN**
(dau vao duy nhat con lai = nguong dong `EntryGate`). => bien the **hieu chuan** (do doc/do chat cua
nguong gate) la thu DUY NHAT kenh gate con dieu khong duoc, va chua ai do **tren baseline T170 hiện hành**.

`RESULT_GATESCALE.md` da do L80/T130/T170 nhung **tren `wfo_ds_x1` (X1_C3_FULL, scale baseline 1.0, cua so
2022-01..2025-12)** — khong phai `wfo_ds_x1_2021` (T170, scale 1.70, 2021-07..2025-12) dang deploy. Vong
nay do **quanh diem 1.70 dang chay** de hoi: do doc hien tai co toi uu khong, hay long hon (1.30) / chat
hon (2.10) tot hon?

**KHONG open-search**: chi 2 diem co dinh doi xung quanh 1.70, chot TRUOC, khong them sau khi thay so.
**Ky vong ghi truoc: NULL** (khuon B4/GATESCALE: DEV khong phan biet duoc delta gate ~3pp; T170 da chon vi
rui ro tot hon, khong phai vi CAGR). Neu 1 trong 2 diem thang ro => bat ngo.

## 1. Co che — chot cung (byte-identical khi scale=1.70)

`SIM_GATE_DYN_SCALE` (float, doc 1 lan o `Configs` static-init, key trong PROFILE). `EntryGate.threshold`:
```
thr = MIN_MOMENTUM_15M * max(DYN_MIN, symbolPred/SCORE_BASE * DYN_MULT) * GATE_DYN_SCALE
PASS  <=>  !(predReturn15M < thr)
```
`DYN_MIN=0.26787f`, `SCORE_BASE=0.15f`, `DYN_MULT=1.28760f` (hang so `EntryGate`).
`GATE_DYN_SCALE > 1` = **CHAT hon** (nguong cao hon => it lenh); `< 1` = **LONG hon** (nhieu lenh).
Ap o nhanh dyn (`symbolPred != null`); nhanh nguong CO SO (BIG_DOWN/DCA_LEVEL1/leg market-signal) KHONG bi scale.
`scale=1.70` = T170 hien hanh. Chi nhan 1 he so vao `dyn_thr` da tinh — khong dung lai floor/MULT (IEEE-exact).

## 2. Bien the — DUNG 2, KHOA (khac nhau CHI o SIM_GATE_DYN_SCALE)

| tag | profile | scale | y nghia (vs T170=1.70) |
|---|---|---|---|
| `X1_GS_T130_2021` | `profiles/x1_gs_t130.properties` (clone x1_gs_t170) | 1.30 | gate LONG hon 0.40 (nhieu lenh hon) |
| `X1_GS_T210_2021` | `profiles/x1_gs_t210.properties` (clone x1_gs_t170) | 2.10 | gate CHAT hon 0.40 (it lenh hon) |

Moi key khac y `x1_gs_t170.properties`. `scale=1.70` = baseline (KHONG chay lai, lay md5 `efb793e2`).
Khong them bien the, khong doi 1.30/2.10 sau khi thay so. `x1_gs_t130.properties` da co san; tao
`x1_gs_t210.properties` bang clone duy nhat 1 dong `SIM_GATE_DYN_SCALE=1.30 -> 2.10`.

## 3. Cong parity (bat buoc TRUOC)

Chay `x1_gs_t170.properties` nguyen ban tren Kaggle (cung jar/data) => printDone phai **byte-identical**
md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089. FAIL => DUNG, khong chay bien the.

## 4. Cham

- `research/analysis/x1_rates.py <baseline> <tag>` — 5 rate + CI (bootstrap block-72h, 2000 rep, seed
  20260905; he so inflate theo `x1_rates.py --k <so_round>` = `sqrt(2 ln k)`, KHONG hardcode x1.21 —
  xem `RISK_APPETITE.md` §1 ghi chu 2026-09-19).
- Rang buoc cung `RISK_APPETITE.md`: maxDD<=30%/nam, UW<=200, khong nam am, quy>=-15%, tap trung 1
  coin<=15% equity. Doc TUONG DOI theo baseline (khong them vi pham nang hon incumbent).
- Bao cao rieng: so lenh, so lenh/nam, PnL (equity/CAGR), maxDD/UW, tap trung.

## 5. QUY TAC QUYET DINH (chot)

- **PASS** <=> `>=2` trong 5 rate chat luong ngoai CI theo huong TOT + qua het rang buoc cung tung nam.
- 0-1 rate ngoai CI hoac deu XAU => **NULL / XAU hon** — GIU T170. d CAGR am ro (CI tren < 0) => THUA.
- Day la **chinh nguong gate tren DEV** => duong cung CHI la ung vien (khong ap dung), phai pre-reg +
  forward. Neu NULL thi noi ro NULL.

## 6. Thu tu — bat buoc

1. Commit file nay. 2. Tao profile `x1_gs_t210` + clone `x1_gs_t130`. 3. Cong parity (byte-identical
efb793e2). 4. 2 run bien the. 5. Cham. 6. `docs/RESULT_GATE_CALIB.md` + ghi chi phi Kaggle. Commit SAU.
Khong push.

## 7. Khong lam

Khong mo lai bins/selector/exit/trailing. Khong doi scale sau khi thay so. Khong cham 242 / holdout 2026.
Khong git push. Khong tune 1.30/2.10.
