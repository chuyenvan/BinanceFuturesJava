# RESULT — HIEU CHUAN LAI GATE (nguong theo PHAN VI CUON p15) + DO LAI NHIP 15 PHUT

Pre-reg chot TRUOC: `docs/prereg/PREREG_GATE_RECAL.md` (commit `2e41190`). Nguon chan doan:
`docs/audit/DIAG_GATE_FROZEN_20260926.md`. Runner `research/analysis/gate_recal_run.py`,
scorer `research/analysis/gate_recal_score.py`, JSON
`docs/result/RESULT_GATE_RECAL.json`.

- Nen = **PRODUCTION FLATGRID KEEPLEG0** = `prof_x1_gs_t170` + dung 2 dong `DCA_GRID_WEIGHTS=1,1,1,1`
  / `DCA_GRID_SCALE=6.0` (bundle `sim-x1-2021-bundle`, `wfo_ds_x1_2021`), cua so **DEV
  2021-07-01..2025-12-31** (1.645 ngay lich; 1.644 ngay co equity). **KHONG cham 2026/holdout/242/shadow_c3.**
- Sim chay **Kaggle CPU kernel** (`docs/runbooks/KAGGLE_SIM.md`), **KHONG** chay Java/sim tren Oracle. Chi phi **0**.
- Jar: dataset rieng `chuyendinh/sim-jar-gate-recal`, `sha256 0ef84514acbfd6fc5011b0ae130ba10ca93579a6adb4125a1e8846f8216f5994`
  (build tu commit code `fec652e`, `mvn -o package`). Kernel log `JAR_SHA256` khop o **ca 6 chan**.
- 1 sim = JVM **1138-1324 s** (19,0-22,1 phut) => ngan sach du cho 6 chan; da chay **6/6**
  (2 parity + 3 Q + 1 nhip-15m), khong phai cat bot arm nao.

---

## 0. VIEC 2 — CONG PARITY "TAT = Y NGUYEN": **PASS CA HAI** (chay TRUOC moi so khac)

| chan | doi tuong | md5 `printDone.csv` | n | equity | ket qua |
|---|---|---|---|---|---|
| `gr-par-t170` | `x1_gs_t170` (khong override) | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1.089 | 111.070 | **KHOP** (va `diff` = **0 dong** voi `kaggle_sim/out/t170-x1-2021`) |
| `gr-par-kg0` | KEEPLEG0 (TAT gate moi) | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1.085 | 103.083 | **KHOP** (moc `PREREG_GATESCALE_KEEPLEG0` §1 / `pgk0-g170`) |

⚠️ **Sai lech voi pre-reg §3.3 (da bao):** pre-reg ghi cong nghiem thu TAT la md5 `efb793e2…` (T170).
Task yeu cau doi chieu **KEEPLEG0** (`99e42b75…`). Da chay **CA HAI** — ca hai byte-identical. Vi
**baseline so sanh duoc chon la KEEPLEG0** (nen production dang chay), khac voi pre-reg §2 (profile
`X1_GR_Q*` dung tren nen T170); xem §7 "muc bo / sai lech".

## 1. VIEC 1 — CODE: 2 key, CHI duong SIM, mac dinh TAT = byte-identical

Commit `fec652e` (3 file, +172 dong, **khong** cham ONNX / `NUM_FEATURES` / `extractFeatures45` / duong LIVE):

- `SIM_GATE_P15_Q` (float, doc 1 lan o `Configs`). Khong khai / `<=0` / `>=1` => `P15_Q=0` => **TAT** => duong cu chay nguyen ven.
  `PASS <=> !(predReturn15M < thr)`; `thr = max(MIN_MOMENTUM_15M, quantile_W(p15_past, Q))`;
  `quantile_W` = phan vi **Q** tren cua so truot **W = 30 ngay** (hang so, khong fit) cua **chinh chuoi p15
  cua nguon sim** (`predictionMap`, 2.500.260 mau/phut) — **CAUSAL**: cua so `[t-W, t)`, khong nhin tuong lai,
  khong forward-fill nguoc; ky phap **nearest-rank** (`ceil(Q*n)`). Nhanh `symbolPred != null`:
  `thr_final = max(rolling_thr, EntryGate.threshold(sp))` => **chi SIET, khong bao gio noi long**. Dung 1 moc xay 1 lan
  luc khoi dong (6,1-9,9 s cho 2,5M mau); log `[GATE-RECAL] built …` + `[GATE-RECAL] W/Q/sampleMin`.
- `SIM_ENTRY_SAMPLE_MIN` (int, mac dinh 1) = nhip lay mau **entry-leg** (VIEC 4). Can key thu 2 nay de do nhip
  (pre-reg §3.6 yeu cau 1 run nhip 15 phut); khong khai / `<=1` => **byte-identical**.
- Nguong cuon tinh tu `predictionMap` => **cung mot nguon p15** o ca sim; tren LIVE key khong duoc khai nen
  `P15_Q=0` => **duong live khong doi mot bit**.

## 2. VIEC 3+5 — BANG CHINH (baseline = KEEPLEG0 TAT, `gr-par-kg0`)

| chan | Q | n | entry/ngay | entry/thang | equity | CAGR% | maxDD% | UW | qmin% | conc% | meanP/lenh | `n_pass`/`n_cand` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `gr-par-t170` (phu) | — | 1.089 | 0,662 | 20,2 | 111.070 | +29,27 | −11,84 | 92 | −0,92 | 9,77 | 69,85 | 841/17,93M |
| **`gr-par-kg0` (TAT)** | — | **1.085** | **0,660** | **20,1** | **103.083** | **+27,14** | **−11,21** | **147** | −1,08 | 7,12 | 62,75 | 837/17,92M |
| `gr-kg0-q995` | 0,995 | 1.021 | 0,621 | 18,9 | 99.531 | +26,15 | −11,20 | 147 | −1,97 | 7,12 | 63,20 | 773/17,95M |
| `gr-kg0-q998` | 0,998 | 954 | 0,580 | 17,7 | 97.674 | +25,63 | −10,82 | 147 | −2,13 | 7,14 | 65,70 | 706/17,98M |
| `gr-kg0-q999` | 0,999 | 868 | 0,528 | 16,1 | 90.698 | +23,57 | −10,07 | 164 | −1,85 | 7,37 | 64,17 | 620/18,01M |
| `gr-kg0-q998-15m` | 0,998 + nhip 15' | **420** | **0,255** | **7,8** | 56.148 | +11,08 | −5,93 | 278 | −1,03 | 6,93 | 50,35 | 406/1,21M |

- **Co che DUNG chieu:** `n` va `n_pass` **GIAM DON DIEU** theo Q (1.085 > 1.021 > 954 > 868;
  837 > 773 > 706 > 620) => nguong cuon **co bind** (Q995 −64 lenh, Q998 −131, Q999 −217) nhung
  **chi o phia SIET** (dung nhu pre-reg §1: `max(...)`, khong noi long). `maxDD`/`UW` khong xau hon.
- **Ty le entry/thang** cua ca 4 arm nam trong `[5, 30]` (pre-reg §4-iii dieu kien 3).
- Chi tiet theo nam: **moi chan, moi nam deu ret > 0**; khong nam nao vi pham rao cung (R-MOI:
  maxDD ≤ 40 / UW ≤ 250 / qmin ≥ −20 / conc ≤ 15). UW toan ky cao nhat = 278 (`q998-15m`).
- **CI 5 rate** (block-72h, 2000 rep, seed 20260905) vs `gr-par-kg0`: **0/5 rate ngoai CI** o MOI arm,
  o **CA HAI** do rong (`x1.21` legacy **VA** `inflate(3)=1.4823`). Vi du Q999: `win%` +0,277 [−1,96; +2,60],
  `TSloss%` −0,300 [−2,33; +1,56], `mP|SM` +0,207 [−0,33; +0,78], `mP|SL` +0,803 [−1,91; +4,41],
  `meanP` +0,348 [−0,36; +1,13].
- **CI hieu CAGR** (paired block-bootstrap ngay, block 21/10/42, 2000 rep, seed 20260903, nguong `1.4823*sd_boot`):

| chan | dCAGR (pp) | lo95_21 | hi95_21 | sd_21 | P(d>0) | nguong | DAT? |
|---|---|---|---|---|---|---|---|
| `gr-kg0-q995` | −0,986 | −4,178 | +1,754 | 1,528 | 0,254 | +2,266 | khong |
| `gr-kg0-q998` | −1,512 | −5,465 | +2,204 | 2,001 | 0,228 | +2,966 | khong |
| `gr-kg0-q999` | −3,561 | −8,729 | +1,235 | 2,617 | 0,077 | +3,879 | khong |
| `gr-kg0-q998-15m` | **−16,038** | **−28,612** | **−5,477** | 5,840 | **0,000** | +8,657 | khong (am RO) |

=> Q cang chat thi CAGR cang tut (nhung CI cua 3 arm Q **van chua tach khoi 0**); rieng nhip 15'
**tut ro ret (CI tren < 0)** so voi baseline 1 phut — dung vi no cat mat phan lon co hoi vao lenh.

## 3. VIEC 4 — NHIP: 1 PHUT vs 15 PHUT ("ty le entry chuyen doi duoc")

| nhip | chan | n | entry/ngay | entry/thang | equity | CAGR% |
|---|---|---|---|---|---|---|
| **1 phut (1.440 co hoi/ngay)** | `gr-par-kg0` (TAT) | 1.085 | **0,660** | **20,1** | 103.083 | +27,14 |
| 1 phut, cung nguong | `gr-kg0-q998` | 954 | 0,580 | 17,7 | 97.674 | +25,63 |
| **15 phut (96 co hoi/ngay, khop live)** | `gr-kg0-q998-15m` | **420** | **0,255** | **7,8** | 56.148 | +11,08 |

- **Ty le chuyen doi do duoc: 15'/1' = 420/954 = 0,440** (do cung nguong Q998) — **duoi nguong 0,60** ma
  pre-reg §4-iii dat ra => nhip 15 phut **KHONG "chuyen doi duoc"** theo dung luat da chot.
  So voi chinh baseline TAT: 420/1.085 = 0,387.
- **SANITY (cong cu chay dung):** `n_cand` 17,98M -> 1,21M = **dung 15,0x** => nhip lay mau 96/ngay khop chinh xac.
- **⚠️ SUA LAI GIA DINH 15x CUA CHAN DOAN 26/09 (day la phat hien chinh cua VIEC 4):** chan doan noi
  "sim danh gia entry 1.440 lan/ngay vs live 96 => ty le entry sim bi thoi len 15x". Do thuc **BAC BO**:
  khi giam **15x so co hoi vao lenh**, so lenh chi giam **2,27x** (954 -> 420), `n_pass` giam **1,74x** (706 -> 406).
  Entry la **BIEN CO** (mot lan vuot nguong lai bi giu vi tri hang gio), khong phai **MAU** theo nhip; nen
  nhip chi giai thich duoc ~**2,3x**, **khong phai 15x**. Phan chenh con lai sim<->live (DEV 0,255/ngay
  vs live ky vong 0,086/ngay) **den tu NGUON/THANG DO p15**, khong phai tu nhip.
- **Khong** the lay so nhip-15' (7,8 entry/thang) lam du doan live cho cau hinh HIEN HANH: nguong live
  `max(rolling_live≈1,9%, dyn 2,9-3,8%) = dyn` **van > p100 cua p15 live 2026 (2,30%)** => live van 0 lenh;
  cung co ket luan cua `DIAG_...`: cau hinh hien hanh **khong duoc go-live** (~2,6 entry/thang, cay mong).

## 4. VIEC 5 — PHAN QUYET THEO KY VONG DA CHOT TRUOC

Luat chot (pre-reg §4): PASS <=> (i) `dCAGR > 1.4823*sd_boot` **VA** (ii) qua het rao cung tung nam
**VA** (iii) entry/thang ∈ `[5, 30]` **VA** ty le nhip-15' ≥ 60% nhip-1'.

| chan | (i) dCAGR | (ii) rao cung | (iii) entry/thang | (iii) nhip ≥0,60 | **PASS** |
|---|---|---|---|---|---|
| `gr-kg0-q995` | khong | DAT | DAT | DAT | **KHONG** |
| `gr-kg0-q998` | khong | DAT | DAT | DAT | **KHONG** |
| `gr-kg0-q999` | khong | DAT | DAT | DAT | **KHONG** |
| `gr-kg0-q998-15m` | khong | DAT | DAT | **KHONG** (0,440) | **KHONG** |

**VERDICT: 0/4 PASS => NULL — DUNG Y KY VONG GHI TRUOC** ("NULL hoac tuong duong nhung entry-rate doi duoc
va on dinh hon"). Ket qua cu the: nguong theo phan vi cuon **chi SIET duoc** (n giam don dieu, equity tut don dieu),
dCAGR **am** (chua tach khoi 0 o 3 arm Q, tach am o nhip 15'), 0/5 rate ngoai CI => **KHONG co bang chung
nao de thay gate hien hanh**.

Theo pre-reg §4 "cach doc": **0 PASS ma khong vi pham => "khong phan biet duoc / do doc incumbent la hop ly"
=> DONG, GIU gate hien tai** — nhung **van phai ghi muc "kenh live ky vong ~2,6 entry/thang"** vao quyet dinh
go-live (va bo sung: con so nay la ky vong cua cau hinh hien hanh, khong phai mot khuyen nghi go-live).

## 5. CAN OWNER DUYET GI DE DEPLOY

**Khong co gi de deploy.** Khong co cau hinh nao trong bai nay duoc de xuat ap dung:
- Duong **SIM** da co them 2 key, **mac dinh TAT** (`P15_Q=0`, `ENTRY_SAMPLE_MIN=1`) => hanh vi production
  **khong doi** (chung minh bang 2 cong parity byte-identical). Code da nam tren branch `module` (`fec652e`), **chua push**.
- Neu owner muon **bat** bat cu thu gi (khai `SIM_GATE_P15_Q` trong profile/env, hay restart/deploy), do la
  **quyet dinh rieng** — ket qua nay **khong ung ho** (0 PASS, dCAGR am).
- Hai de xuat ha tang (KHONG thuoc bai nay, giu nguyen tu `DIAG_...` §4.3): (a) do lai **nguon/thang do p15**
  giua model live 2026 va bo pred DEV (day moi la nut that su cua dong bang); (b) them watchdog `gatePassCuoi`
  vao `bin/health.sh`. Ca hai can **owner duyet rieng**.

## 6. MUC BO / SAI LECH / GIOI HAN (khai ro)

- **Bo:** khong chay arm T170 (pre-reg §2 profile `X1_GR_Q*` dung nen T170) — **doi sang nen KEEPLEG0**
  (production) cho ca 4 arm, theo y task ("1 arm baseline (TAT) + 3 arm Q", parity = KEEPLEG0). Chan
  `gr-par-t170` van chay de thoa pre-reg §3.3. **Khong** them diem Q nao khac (`0.995/0.998/0.999` dung chot).
- **Bo:** nhip 15' chi doi **entry-leg** (moi lenh MO moi qua `createOrder`), **giu nhip 1 phut cho cap nhat/thoat
  lenh dang mo** — khac live o cho live cap nhat vi tri theo nhip rieng. Day la xap xi co chu dich, ghi ro.
- **Bo:** `W` la hang so 30 ngay trong code (khong thanh key) theo dung yeu cau "them **1** key".
  `SIM_ENTRY_SAMPLE_MIN` la key thu 2, chi de do nhip (VIEC 4 bat buoc), mac dinh TAT.
- **Gioi han:** 3 arm Q **chi siet duoc** vi `max(rolling, dyn)` — thiet ke nay khong the **noi long**
  nguong khi dyn dang qua cao (chinh la benh cua live). Neu muon tra loi "co the dua nguong live ve trong
  tam p15 live khong", phai **pre-reg KHAC** (vd `thr = rolling` thay vi `max(rolling, dyn)`), **khong tu lam o day**.
- **Gioi han:** so sanh sim<->live van con 1 buoc: `p15` live (242, p50 0,910%, max 2,30%) khac `p15` DEV
  (p50 0,545%, max 12,26%) — bai nay **khong** cham 2026/holdout, nen **khong** khang dinh duoc gi ve 2026.
- **Khong lam:** khong push git; khong restart/sua env/profile tren host live; khong dong `242`; khong chay
  Java/sim tren Oracle (chi `mvn -o package`); khong cham ONNX/`NUM_FEATURES`/`extractFeatures45`/duong LIVE.

## 7. BANG CHUNG THO / TAI LAP

```bash
# parity (2 cong) — chay TRUOC moi so khac
md5sum /home/ubuntu/kaggle_sim/out/gr-par-t170/storage/printDone.csv   # efb793e2468ca3a7318da0f0ad23d4fc
md5sum /home/ubuntu/kaggle_sim/out/gr-par-kg0/storage/printDone.csv    # 99e42b75cf1a2142f9cd14dc72e371ba
# dong [GATE] / [GATE-RECAL] trong sim.out cua tung chan (n_cand/n_pass, W/Q/sampleMin)
grep -h "GATE-RECAL\]\|\[GATE\] " /home/ubuntu/kaggle_sim/out/gr-kg0-q998-15m/logs/sim.out
# cham lai (5 rate CI khoi-72h + equity bootstrap block-21)
python3 research/analysis/gate_recal_score.py --k 3 --json docs/result/RESULT_GATE_RECAL.json
```

Kernel: `chuyendinh/sim-gr-par-t170` · `sim-gr-par-kg0` · `sim-gr-kg0-q995` · `sim-gr-kg0-q998` ·
`sim-gr-kg0-q999` · `sim-gr-kg0-q998-15m` (private; Kaggle CPU, chi phi 0). Jar `chuyendinh/sim-jar-gate-recal`.
