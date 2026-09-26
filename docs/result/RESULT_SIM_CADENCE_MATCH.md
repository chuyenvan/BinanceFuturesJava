# RESULT — SIM THE HIEN DUNG NHIP THIET KE: **selector 15' + BIG_DOWN/DCA 1'**

Pre-reg: `docs/prereg/PREREG_GATE_RECAL.md` — **AMENDMENT §7** (commit **`30e5f4d`**, chot **TRUOC** khi code/chay).
Code: commit **`3b6c6e9`** (fix pham vi `SIM_ENTRY_SAMPLE_MIN` = **chi selector-entry**). Jar
`sha256 43888ebd14250a476fd2c4a0221e77040345883b230a9bd9a13592e903ad518d` (dataset moi
`chuyendinh/sim-jar-cadence`; khop o **ca 5 chan** trong log kernel `JAR_SHA256=`). JSON:
`docs/result/RESULT_SIM_CADENCE_MATCH.json`. Runner `research/analysis/cadence_run.py`, scorer
`research/analysis/cadence_score.py`.

- Nen = **PRODUCTION FLATGRID KEEPLEG0** (`prof_x1_gs_t170` + `DCA_GRID_WEIGHTS=1,1,1,1` /
  `DCA_GRID_SCALE=6.0`, bundle `sim-x1-2021-bundle`), cua so **DEV 2021-07-01..2025-12-31** (1.644 ngay).
  **KHONG cham 2026 / holdout / 242 / shadow_c3. KHONG push git.**
- 5 chan Kaggle CPU (**chi phi 0**, **KHONG** chay Java/sim tren Oracle), chay **song song**, JVM 696-1.303 s
  (11,6-21,7 phut), tat ca **COMPLETE**, `ok=true`, `symbol_mapper=863`.

---

## 0. VIEC 1 — CONG "TAT = Y NGUYEN": **PASS CA HAI** (chay TRUOC moi so khac)

| chan | profile + override | md5 `printDone.csv` | n | equity | ket qua |
|---|---|---|---|---|---|
| `cd-par-kg0` | KEEPLEG0 (khong khai key) | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1.085 | 103.083 | **KHOP** |
| `cd-par-t170` | `x1_gs_t170` (khong override) | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1.089 | 111.070 | **KHOP** |

=> Key khong khai / `<=1` => cong moi **khong lam gi** => **byte-identical** voi truoc khi sua. Code fix
**an toan** voi production (duong live khong khai key nen khong doi mot bit).

## 1. VIEC 0+1 — AMENDMENT + CODE (diff nho nhat)

- **VIEC 0:** `PREREG_GATE_RECAL.md` **§7 AMENDMENT** (commit `30e5f4d`, **khong xoa** muc cu): chot lai
  **PHAM VI** `SIM_ENTRY_SAMPLE_MIN` = **chi leg selector** (`PREDICT_SYMBOL_TRADE`); `BIG_DOWN` va
  `DCA_LEVEL1` **khong bi lay mau** (giu nhip 1'). Ghi ro day la sua **pham vi ap dung**, khong doi
  thuat toan/tham so nao.
- **VIEC 1:** sua tai cho trong `createOrder` — them **2 dieu kien loai tru** `BIG_DOWN` / `DCA_LEVEL1`
  (`SimulatorMarketLevelTicker1MStopLoss.java` ~:1280; javadoc `Configs.ENTRY_SAMPLE_MIN`). **Khong them
  key moi** (scope co dinh = selector-only, dung "cach don gian nhat" cua pre-reg §7.2). Diff: 2 file,
  +17/-6 dong. **Khong** cham `EntryGate` / `SIM_GATE_P15_Q` / ONNX / `NUM_FEATURES` /
  `extractFeatures45` / duong LIVE.

## 2. TRA LOI (1) — **SIM HIEN TAI (truoc fix) = 1 PHUT CHO TAT CA** (tick 1m)

Bang chung code:
- Vong lap sim duyet **tung tick 1 phut** trong ngay (`time2Tickers` phai `>= 1440` tick/ngay;
  `EntryGate.setCurrentTime(time)` moi tick) => **1.440 co hoi vao lenh/ngay**, cho **moi loai leg**.
- Cong `SIM_ENTRY_SAMPLE_MIN` dat o **DAU ham `createOrder(...)`** — ham nay la diem dung chung cua ca 3
  nguon leg (selector ~:436, `BIG_DOWN` ~:371, `DCA_LEVEL1` ~:379/:397) => khi bat `=15` no chan **ca 3**.
- Trong profile/env dang chay: **khong** khai `SIM_ENTRY_SAMPLE_MIN` => mac dinh `1` => **1' cho tat ca**.

**Ket luan: SIM HIEN TAI = 1 PHUT CHO TAT CA (tick 1m) — day chinh la cho lech.** Bang chung dinh luong:
chan cu `gr-kg0-q998-15m` (chan TAT CA o 15') bop `BIG_DOWN` 248 -> **14** va `DCA_LEVEL1` 20 -> **2**.

## 3. BANG 3 CAU HINH (cung moi thu khac; DEV 2021-07-01..2025-12-31)

| cau hinh | n | entry/ngay | entry/thang | equity | CAGR% | maxDD% | UW | qmin% | conc% | meanP/lenh |
|---|---|---|---|---|---|---|---|---|---|---|
| **`all-1'`** = `cd-par-kg0` (baseline, moi thu 1') | 1.085 | **0,660** | **20,09** | 103.083 | **+27,14** | −11,21 | 147 | −1,08 | 7,12 | 62,75 |
| **`all-15'`** = `gr-kg0-q998-15m` (chan TAT CA o 15', kem Q=0,998 — doi chieu cu) | **420** | 0,256 | 7,78 | 56.148 | +11,08 | −5,93 | 278 | −1,03 | 6,93 | 50,35 |
| **`sel15`** = **`cd-sel15`** (selector 15' + BIG_DOWN/DCA 1', gate TAT) | **744** | **0,453** | **13,77** | 71.718 | **+17,29** | −6,27 | 166 | −3,36 | 6,77 | 49,35 |
| `sel15-q998` = `cd-sel15-q998` | 608 | 0,370 | 11,26 | 65.756 | +15,05 | −6,01 | 278 | −3,43 | 6,89 | 50,59 |
| `sel15-q999` = `cd-sel15-q999` | 563 | 0,343 | 10,42 | 63.187 | +14,03 | −6,10 | 166 | −3,54 | 6,89 | 50,07 |

**So leg theo cot `level` (chung minh lay mau CHI anh huong selector):**

| chan | selector | BIG_DOWN | DCA_LEVEL1 | other | tong |
|---|---|---|---|---|---|
| `cd-par-kg0` (all-1') | 817 | **248** | **20** | 0 | 1.085 |
| `gr-kg0-q998-15m` (all-15') | 404 | **14** | **2** | 0 | 420 |
| **`cd-sel15`** (sel15) | 483 | **248** | **13** | 0 | 744 |
| `cd-sel15-q998` | 351 | **248** | **9** | 0 | 608 |
| `cd-sel15-q999` | 306 | **248** | **9** | 0 | 563 |

- **`BIG_DOWN` giu NGUYEN 248/248** o ca 3 arm `sel15*` (truoc fix: 14/248) => cong lay mau nay **da thuc su
  chi cham selector**. `DCA_LEVEL1` 20 -> 13/9: **khong** do bi lay mau ma do **giao duc dan** (it leg
  selector mo hon => it cum dang lo => it dip nhoi) — khong phai he qua truc tiep cua cong.
- `other = 0` moi chan => nhanh FOMO/market-signal khong mo lenh nao trong cua so nay (nen "loai tru
  BIG_DOWN/DCA" == "chi selector" ve mat so lieu).
- **SANITY nhip:** `n_cand` 17,92M -> 1,20M = **15,0x** (dung 96 co hoi/ngay); `n_pass` 837 -> 496 =
  **1,69x** (entry la **BIEN CO** khong phai **MAU**) — lap lai phat hien cua `RESULT_GATE_RECAL` §3.

### 3.1 CI 5 rate (block-72h, 2000 rep, seed 20260905) vs `all-1'` — **0/5 rate ngoai CI o CA 2 do rong** (x1,21 legacy VA inflate(3)=1,4823)

| chan | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---|---|---|---|---|
| `sel15` | +0,51 [−2,28; +3,55] | −0,51 [−3,80; +2,55] | −0,26 [−1,89; +0,94] | +2,67 [−1,67; +7,81] | +0,17 [−1,53; +1,67] |
| `sel15-q998` | +1,11 [−3,27; +5,79] | −0,95 [−5,04; +2,91] | −0,25 [−2,11; +1,28] | +3,57 [−1,80; +9,61] | +0,37 [−1,47; +1,90] |
| `sel15-q999` | +1,14 [−3,80; +6,37] | −1,09 [−5,56; +3,13] | −0,29 [−2,32; +1,48] | +4,06 [−1,59; +10,54] | +0,41 [−1,54; +2,09] |

Chat luong lenh (5 rate) **khong khac biet duoc** — khac biet nam o **SO LUONG** lenh.

### 3.2 CI hieu CAGR (paired block-bootstrap ngay, block 21/10/42, 2000 rep, seed 20260903, nguong 1,4823·sd_boot)

| chan | dCAGR (pp) | lo95_21 | hi95_21 | sd_21 | P(d>0) | nguong | DAT? |
|---|---|---|---|---|---|---|---|
| `all-15'` (doi chieu cu) | **−16,04** | −28,61 | −5,48 | 5,84 | 0,000 | +8,66 | khong (am RO) |
| **`sel15`** | **−9,84** | **−20,76** | **−0,49** | 5,17 | 0,019 | +7,66 | khong (am RO, CI tren < 0) |
| `sel15-q998` | −12,07 | −23,51 | −2,14 | 5,44 | 0,005 | +8,07 | khong (am RO) |
| `sel15-q999` | −13,09 | −24,98 | −2,61 | 5,66 | 0,005 | +8,39 | khong (am RO) |

- Rao cung theo nam: **PASS ca 5 chan** (maxDD ≤ 40 / UW ≤ 250 / qmin ≥ −20 / khong nam am / conc ≤ 15).

## 4. TRA LOI (2) — `sel15` khac `all-1'` bao nhieu? Mat hieu nang o DAU?

| so sanh | dn | dn% | dCAGR | d maxDD | d UW | d entry/ngay |
|---|---|---|---|---|---|---|
| `sel15` vs `all-1'` | **−341** | **−31,4%** | **−9,84 pp** | **+4,94** (tot hon) | +19 | −0,207 (0,453 vs 0,660) |
| `sel15-q998` vs `all-15'` (cung Q998) | **+188** | +44,8% | **+3,97 pp** | −0,08 | 0 | +0,114 |

**(a) Nhip selector 15' CO lam mat hieu nang that** (dCAGR −9,84 pp; CI tren −0,49 < 0 => am RO, khong
phai nhieu). Nhung **(b) phan lon "tut" trong bao cao cu la do em chan OAN `DCA`/`BIG_DOWN`:**
- Doi chieu cung Q998: `all-15'` (chan tat ca) −16,04 pp / 420 lenh vs `sel15-q998` (chi chan selector)
  −12,07 pp / 608 lenh => sua pham vi **hoi lai +3,97 pp CAGR va +188 lenh** (giam 24,8% mat mat).
  **≈ 3/4 mat mat la do nhip selector 15' that; ≈ 1/4 la do chan oan.**
- Y nghia rong hon: **ty le entry chuyen doi duoc** cua nhip 15' — dat ra o pre-reg §4(iii) la **>= 0,60** —
  cu rớt (0,387 voi `all-15'`) nay **DAT**: `sel15/all-1' = 744/1.085 = **0,686**`; rieng selector
  483/817 = **0,591**. Cong cu "nhip 15' khong chuyen doi duoc" trong `RESULT_GATE_RECAL` §3 bi **BAC BO**
  mot phan: no la **he qua cua viec chan oan**, khong phai ban chat cua nhip 15'.
- `BIG_DOWN` **248/248 = 1,000** va `entry/thang = 13,77` ∈ `[5, 30]` => ty le entry van trong dai
  chuyen doi duoc.

## 5. TRA LOI (3) — cau hinh nao go-live duoc, co can chinh live khong?

**(a) Sim da khop thiet ke.** Cau hinh **`sel15`** = *selector 15' + BIG_DOWN/DCA 1'*, gate incumbent
(`SIM_GATE_DYN_SCALE=1.70`, khong khai `SIM_GATE_P15_Q`):
- so: **744 lenh / 4,50 nam** = **0,453 entry/ngay = 13,77 entry/thang**; equity 71.718 tren 35.000
  (**CAGR +17,29%**); **maxDD −6,27%**; **UW 166** (< rao 250); qmin −3,36% (> −20); conc 6,77% (< 15);
  rao cung tung nam PASS.
- So voi baseline: **−9,84 pp CAGR** doi lay **maxDD tot hon +4,94 pp** va **UW chi +19**.
- 3 arm Q (`SIM_GATE_P15_Q` 0,998/0,999) **chi siet them** (n 608/563, CAGR +15,05/+14,03, 0/5 rate ngoai
  CI, dCAGR am sau hon) => **khong nen bat** — giu gate incumbent.

**(b) CO, live can chinh — va day la ly do bai nay ton tai.** Neu live dang danh gia entry **96 lan/ngay
(moi 15') cho TAT CA leg** (nhu chan doan 26/09: sim 1.440/ngay vs live 96/ngay), thi live phai duoc chinh
thanh **selector 15' nhung `BIG_DOWN` + `DCA` 1'** — neu khong, live se **bo mat ~1/4 co hoi** va lech sim.
Sim sau fix la **chuan de bam**; "live lech thi chinh live" (y owner 26/09 23:02). Luu y: bai nay
**KHONG** sua gi tren host live/242; doi kieu live la **viec rieng, can owner duyet**.

**(c) Chua du de go-live ngay — 1 nut rieng van con:** cau hinh sim nay chua giai quyet **nguon/thang do
p15** sim<->live (p15 live 2026: p50 0,910%, max 2,30% vs DEV p50 0,545%, max 12,26%) va nguong live
`max(rolling_live≈1,9%, dyn 2,9-3,8%)` **van > p100 cua p15 live 2026** => kenh live van ~0 lenh. Bai nay
**khong cham 2026/holdout**, nen **khong khang dinh** duoc gi ve 2026. Can **pre-reg KHAC** cho viec dua
nguong live ve trong tam p15 live (khong tu lam o day).

## 6. MUC BO / SAI LECH / GIOI HAN (khai ro)

- **Bo:** khong chay them arm "all-15' gate TAT" (chan tat ca o 15', khong Q) — doi chieu `all-15'` dung lai
  la chan cu `gr-kg0-q998-15m` (kem Q=0,998). Vi vay moi so sanh "sua pham vi hoi lai bao nhieu" duoc
  **ghep cap cung Q998** (§4b) cho cong bang; ket luan "nhip 15' that" dua tren cap TAT (`sel15` vs `all-1'`).
- **Khong chay arm q999** o ke hoach cu? — **CO chay**: ca 5 chan (2 parity + 3 arm) deu xong trong 1 luot
  5 slot song song; khong phai cat arm nao.
- **Gioi han:** nhip 15' chi ap cho **entry-leg** (mo lenh moi); cap nhat/thoat lenh dang mo van 1' — khac
  live o cho live cap nhat vi tri theo nhip rieng. Xap xi co chu dich, ghi ro (nhu `RESULT_GATE_RECAL` §6).
- **Gioi han:** `DCA_LEVEL1` giam 20 -> 13/9 la **giao duc dan**, khong do cong lay mau. Khong the tach
  hoan toan 2 hieu ung trong 1 chan; da khai ro.
- **Gioi han:** ket luan "1/4 / 3/4" la **uoc luong tu 1 cap cung Q998** (block-21 CI rong ~±20 pp o cap
  TAT), khong phai dinh luong chinh xac.
- **Khong lam:** khong push git; khong restart/sua env/profile host live; khong cham 242/shadow_c3; khong
  chay Java/sim tren Oracle (chi `mvn -o package`); khong cham ONNX/`NUM_FEATURES`/`extractFeatures45`.

## 7. BANG CHUNG THO / TAI LAP

```bash
md5sum /home/ubuntu/kaggle_sim/out/cd-par-kg0/storage/printDone.csv    # 99e42b75cf1a2142f9cd14dc72e371ba (n1085 eq103083)
md5sum /home/ubuntu/kaggle_sim/out/cd-par-t170/storage/printDone.csv   # efb793e2468ca3a7318da0f0ad23d4fc (n1089 eq111070)
grep -h "JAR_SHA256\|\[GATE\] " /home/ubuntu/kaggle_sim/out/cd-sel15/logs/sim.out
python3 research/analysis/cadence_score.py --k 3 --json /home/ubuntu/kaggle_sim/out/cadence_score.json
```

Kernel: `chuyendinh/sim-cd-par-kg0` · `sim-cd-par-t170` · `sim-cd-sel15` · `sim-cd-sel15-q998` ·
`sim-cd-sel15-q999` (private; Kaggle CPU, chi phi 0). Jar `chuyendinh/sim-jar-cadence` (`43888ebd…`).
