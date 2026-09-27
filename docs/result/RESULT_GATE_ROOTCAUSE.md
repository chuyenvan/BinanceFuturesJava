# RESULT — GOC GATE: LECH NGUON/THANG DO p15 + LUAT GATE THEO DON VI NGUON LIVE (DE XUAT)

Pre-reg chot TRUOC: `docs/prereg/PREREG_GATE_ROOTCAUSE.md` (commit `371c49c`). Nguon chan doan:
`docs/audit/DIAG_GATE_FROZEN_20260926.md` (+`.json`), `docs/result/RESULT_GATE_RECAL.md`.
Script: `research/analysis/gate_rootcause_analyze.py`, `..._live_rolling.py`, `..._run.py`, `..._score.py`.
JSON: `docs/result/RESULT_GATE_ROOTCAUSE.json`.

**RANH GIOI (CUNG, khai RO):** `S_dev` = `wfo_ds_x1_2021/pred.bin` (<= 2025-12-31) la **FIT**;
`S_live` (242 `full.log`, 12/08-27/09/2026) va `S_shadow` (Oracle shadow) **CHI CHAN DOAN** — khong dung de
chon `Q`/`W`/nguong/the so nao. Cua so sim DEV = 2021-07-01..2025-12-31. Khong chay Java/sim tren Oracle.
Khong sua code. Khong deploy. Khong push git.

**KET LUAN MOT CAU:** hai phan bo p15 **KHONG** chi lech thang do ma **lech HINH DANG** (`D=11,26`; than affine
`live ~ 0,33 + 1,07 x dev` nhung **duoi bi cat** — live `max 2,30%` vs DEV `max 12,26%`) => **khong the map bang 1 thua so**
=> nguong bat buoc tinh tu chinh nguon live. Phuong an A (thay dyn bang phan vi cuon) **dung co che nhung 0/3 PASS tren DEV**
(qua rong, `UW` 568-773 > 250, 3/5 rate ngoai CI) => **DONG, giu gate hien tai**; cai can sua truoc tien la **nguon/thang do p15 cua model LIVE**, khong phai cong thuc gate.

---

## 1. VIEC 1 — DO LECH NGUON (so)

### 1.1 Bang phan bo (`%`; nearest-rank)

| nguon | n | min | p1 | p5 | p25 | p50 | p75 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| **S_dev** `pred.bin` (FIT) | 2.500.260 | 0,202 | 0,284 | 0,328 | 0,442 | **0,545** | 0,673 | 0,960 | 1,308 | **12,261** |
| **S_live** 242 2026 (chan doan) | 8.986 | 0,400 | 0,600 | 0,690 | 0,820 | **0,910** | 1,020 | 1,380 | 1,770 | **2,300** |
| S_shadow Oracle 20-26/09 | 609 | 0,530 | 0,560 | 0,660 | 0,800 | 0,930 | 1,050 | 1,250 | 1,490 | 2,300 |

### 1.2 Thuong so scale theo tung phan vi `r_p = live/dev`

| | min | p1 | p5 | p25 | p50 | p75 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|---|
| `r_p` | 1,981 | **2,113** | 2,106 | 1,856 | 1,669 | 1,515 | 1,438 | 1,353 | **0,188** |

`r*` (trung vi) = **1,669**; `D = max(r_p)/min(r_p)` = **11,26** (nguong chot truoc: 1,50).

### 1.3 **KET LUAN: KHONG phai scale — la LECH CA HINH DANG (body affine + DUOI BI CAT)**

1. `r_p` **giam don dieu** tu 2,11 (p1) -> 1,35 (p99) -> **0,19 (max)** => khong co 1 thua so nao map duoc (`D=11,26 >> 1,5`).
2. Fit affine tren **than** (p5..p95): `live ~ 0,3305 + 1,0746 x dev` (pp). Residual tai p1..p99 **<= 0,036 pp** —
   than thuc su chi la **dich +0,33 pp, doc 1,07x**. Nhung tau **duoi**: affine du doan `max = 13,5%`, thuc te **2,30%**
   (residual **+11,2 pp**). => **dich nen (level shift) + CAT DUOI (tail truncation)**.
3. Kie dinh Poisson (ky vong = ty le DEV x 8.986 mau):

| thr | frac DEV | ky vong live | **thuc do** | P(X<=obs) |
|---|---|---|---|---|
| 0,800% | 12,289% | 1.104 | **7.137** | ~0 (live **nhieu hon** — dich nen len) |
| 1,705% | 0,3903% | 35,1 | **135** | 1,0 (live nhieu hon) |
| 2,947% | 0,0899% | 8,08 | **0** | **3,1e-4** |
| 3,760% | 0,0509% | 4,58 | **0** | **1,0e-2** |

=> Khong phai "2026 yen hon": live co **nhieu muc p15 thap** hon (0,8-1,7%) => nen cao hon; nhung **duoi bi cat**:
0 mau >= 2,947% trong khi DEV ky vong 8,08. Dong thoi `max` live = 2,30% chi xuat hien 1 lan; va **dai p99->max live
chi rong 0,53 pp** (1,77->2,30) vs DEV 10,95 pp (1,308->12,261) — **dynamic range 8,9x hep hon**.

### 1.4 Tra loi VIEC 1

- **Scale hay shape?** => **SHAPE** (huong ghi truoc DUNG): body = affine (dich +0,33 pp, scale 1,07),
  **duoi bi cat/nen** (khong co mau nao vuot ~2,3% trong 45,6 ngay).
- **Map bang 1 thua so duoc khong?** => **KHONG**. He qua: **nguong gate bat buoc phai duoc tinh tu chinh nguon live**
  (khong the "hieu chuan lai" mot hang so tuyet doi tren bo pred DEV).

---

## 2. VIEC 2 — LUAT GATE MOI THEO DON VI NGUON LIVE (3 phuong an)

`roll = quantile_Q(p15 cua CHINH nguon dang chay, cua so cuon W=30 ngay, CAUSAL)`, `W`/`Q` **chot truoc**.

**Truoc het — mot su that dinh luong lam luat phan vi tren LIVE tro nen *tho*:** tren live, `p99,0=1,77` ma `max=2,30`;
`quantile` cua 30 ngay cuoi: `p99=1,41 / p99,5=1,47 / p99,8=1,50 / max=2,30`. Tuc **ca dai Q ∈ [0,995 ; 0,999] chi trai
0,21 pp (1,47% -> 1,68%)** — nguong phan vi tren live **gan nhu phang** (vi dau ra model live bi nen).

### Phuong an A — **THAY dyn bang phan vi cuon** (`thr = max(base, roll)`, moi leg)
- Cai dat KHONG sua code: `SIM_GATE_P15_Q=Q` + `SIM_GATE_DYN_SCALE=0,001` (dyn -> ~1e-6 < base => `max = roll`).
- **Do tren DEV** (§3) + **do tren chinh chuoi live** (chan doan, `gate_rootcause_live_rolling.py`):

| Q | thr cuon live (30 ngay cuoi) | pass event/ngay (live) | **entry/thang ky vong live** (= pass x ti le entry/pass cua DEV) |
|---|---|---|---|
| 0,995 | 1,47% | 0,549 | **~16** |
| 0,998 | 1,52% | 0,307 | **~9** |
| 0,999 | 1,68% | 0,154 | **~4-5** |

- Uu: **causal, khong co hang so tuyet doi** => chuyen duoc giua sim/live, **khong phai fit tren 2026**.
- Rui ro: **mat tinh chat "theo symbolPred"** cua dyn => khi 1 tick pass thi **MOI ung vien trong tick deu pass**
  (ti le entry/pass co the tang). Va vi dai Q rat hep, gate **kem phan biet** (Q doi tu 0,995->0,999 chi doi nguong 0,21 pp).

### Phuong an B — **giu dyn nhung hieu chuan lai he so** (`SIM_GATE_DYN_SCALE=c`)
- Can `c` de `thr = 0,008·max(0,26787, sp/0,15·1,2876)·c <= max live = 2,30%` voi **moi** sp:
  `c <= 2,30/3,759·1,70 = **1,04**`. Tai `c=1,0`: `thr = [1,705..2,300]%` => chi pass khi p15 >= 1,705%
  (135/8.986 mau = 1,5%).
- **Hai van de (dinh luong):** (i) chon duoc `c` **bat buoc phai nhin phan bo 2026** => **vi pham ranh gioi FIT**;
  (ii) khi da keo `thr` vao trong support live, **dai dong cua dyn chi con 1,35x** (sp live ~0,25-0,32) =>
  **thoai hoa thanh nguong PHANG** => mat dung cai "theo chat luong ung vien" ma dyn sinh ra de lam.
- Entry/thang ky vong: ~**9-16/thang** (giong A) nhung **khong suy ra duoc tu du lieu hop le**.

### Phuong an C — **tat han dyn khi nguon la model live** (`thr = base = 0,80%` phang)
- Live: `0,8%` la **p20 cua live** (79,4% mau >= 0,8%) => gan nhu tick nao cung pass => **qua rong** (chi con chan boi slot).
- Tren DEV, bo dyn (luat phang) da do: **`RESULT_FLATGATE` = -61 pp CAGR**. => **KHONG kha thi**.

### Ket luan VIEC 2: pa **A kha thi nhat**; **C loai**; **B khong dung duoc** vi phai fit tren holdout.

---

## 3. VIEC 3 — KIEM CHUNG TREN DEV (2021-07-01..2025-12-31, nhip selector 15')

Nen KEEPLEG0, bundle `sim-x1-2021-bundle`, jar `sim-jar-cadence` (sha `43888ebd…`), Kaggle CPU (chi phi 0).
**KHONG sua code** => pa A dat bang key co san (`SIM_GATE_P15_Q` + `SIM_GATE_DYN_SCALE=0,001`).

### 3.1 Cong parity (TAT = y nguyen) — **PASS CA HAI** (cung jar)

| chan | md5 `printDone.csv` | n | equity | ket qua |
|---|---|---|---|---|
| `rc-par-kg0` | **`99e42b75cf1a2142f9cd14dc72e371ba`** | 1.085 | 103.083 | **KHOP** |
| `rc-par-t170` | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1.089 | 111.070 | **KHOP** |

### 3.2 Bang chinh — **phuong an A** (`thr = max(base, roll_Q)`) vs `cd-sel15`

| chan | Q | n | entry/thang | eq | CAGR% | maxDD% | UW | qmin | conc% | meanP/lenh | `n_pass`/`n_cand` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **`cd-sel15`** (doi chieu) | — | 744 | **13,77** | 71.718 | +17,29 | **-6,27** | **166** | -3,36 | 6,77 | **49,35** | 496/1.203.200 |
| `rc-a-q995` | 0,995 | 3.256 | **60,28** | 69.195 | +16,36 | **-32,64** | **773** | **-23,29** | 9,92 | 10,50 | 3.230/1.089.731 |
| `rc-a-q998` | 0,998 | 1.875 | **34,71** | 64.225 | +14,45 | -20,60 | **568** | -14,28 | 10,43 | 15,59 | 1.628/1.148.204 |
| `rc-a-q999` | 0,999 | 1.297 | **24,01** | 52.866 | +9,60 | -18,41 | **631** | -13,01 | 8,69 | 13,78 | 1.049/1.173.130 |

Leg theo `level`: `cd-sel15` sel 483 / BIG_DOWN 248 / DCA 13; cac arm A: sel 2960/1594/1022, BIG_DOWN 248 (khong doi), DCA 48/33/27.

### 3.3 Chat luong lenh (CI 5 rate, block-72h, 2000 rep, seed 20260905, inflate k=3 = 1,4823) vs `cd-sel15`

| chan | win% | TSloss% | mP\|SM | mP\|SL | meanP | **ngoai CI** |
|---|---|---|---|---|---|---|
| `rc-a-q995` | **-9,32** [-14,16;-4,68] | **+11,47** [+6,48;+16,19] | -0,36 | -1,06 | **-3,30** [-4,90;-1,40] | **3/5** |
| `rc-a-q998` | **-7,96** [-13,07;-3,22] | **+9,60** [+4,04;+15,03] | -0,22 | -0,57 | **-2,62** [-4,53;-0,55] | **3/5** |
| `rc-a-q999` | **-8,29** [-14,30;-3,08] | **+9,54** [+3,83;+15,62] | -0,17 | +0,37 | **-2,39** [-4,44;-0,29] | **3/5** |

Equity paired block-bootstrap ngay (block 21/10/42, 2000 rep, seed 20260903, nguong `1,4823*sd`): `dCAGR` = **-0,93 / -2,84 / -7,68** pp — **khong arm nao DAT**, ca 3 CI chua tach khoi 0 theo huong duong.

### 3.4 Phan quyet (theo luat da chot o pre-reg §4)

| chan | (i) `dCAGR > 1,4823 sd` | (ii) rao cung | (iii) entry/thang ∈[5,30] | (iii) khong qua rong | (iv) 0/5 rate ngoai CI | **PASS** |
|---|---|---|---|---|---|---|
| `rc-a-q995` | khong | **VI PHAM** (UW 773; qmin -23,3) | **khong** (60,3) | **khong** | **khong** (3/5) | **KHONG** |
| `rc-a-q998` | khong | **VI PHAM** (UW 568) | **khong** (34,7) | **khong** | **khong** (3/5) | **KHONG** |
| `rc-a-q999` | khong | **VI PHAM** (UW 631) | DAT (24,0) | DAT | **khong** (3/5) | **KHONG** |

**VERDICT: 0/3 PASS cho phuong an A => DONG, GIU GATE HIEN TAI.**

- **"Qua rong" la THAT va co dinh luong:** Q995/Q998 day entry len **60,3 / 34,7 lenh/thang** (4,4x / 2,5x `cd-sel15`),
  `maxDD` tu **-6,3 -> -32,6 / -20,6**, `UW` **166 -> 773 / 568**, `qmin` **-3,4 -> -23,3 / -14,3**, `meanP/lenh` **49,4 -> 10,5 / 15,6**.
  Ba rate `win%` / `TSloss%` / `meanP` **ngoai CI theo huong XAU o ca 3 arm** => day khong phai "nhieu co hoi hon" ma la **nhieu lenh rac**.
  Ngay ca Q999 (entry/thang 24,0, trong khoang [5,30]) van **vi pham rao UW** (631 > 250) va **3/5 rate ngoai CI**.
- Phuong an A **co cuu duoc dong bang tren live khong?** Ve co che: **CO** — nguong cuon live (chan doan) cho
  `pass event/ngay = 0,55 / 0,31 / 0,15` (Q995/998/999), tuong ung **~15,9 / 8,9 / 4,5 entry/thang** (nhan ti le
  entry/pass do duoc tren DEV = **0,916 / 0,979 / 0,974**). Nhung **cai gia tren DEV la qua lon** (0/3 PASS) => khong duoc phep doi gate.
- **Nghich ly can ghi ro:** tren live, luat phan vi (A) va luat tuyet doi (incumbent) la **hai thu khac nhau**; tren
  DEV, A lai **long hon** incumbent (vi DEV co duoi dai). Mot luat **khong the vua** "dung don vi live" **vua** "giu chat luong DEV"
  => cai can sua truoc tien **khong phai la cong thuc gate ma la DON VI p15 cua NGUON LIVE** (xem §4.4).

---

## 4. VIEC 4 — TRA LOI (4 cau)

### (1) Hai phan bo p15 lech the nao (so) — scale hay shape?

**SHAPE.** `r_p` giam don dieu **2,11 -> 0,19** (`D=11,26`), than la affine `live ~ 0,33 + 1,07 x dev` (residual <= 0,036 pp
qua p1..p99) nhung **duoi bi cat**: live `max=2,30%` trong khi affine du doan 13,5% va DEV that su vuot 2,947% **2.247 mau**
(live: **0**; ky vong Poisson 8,08; P=3,1e-4). Live co **nhieu** mau o vung thap (>=0,8%: 7.137 vs ky vong 1.104) =>
**dich nen len + nen duoi**, khong phai "thi truong yen hon".

### (2) Co the map bang 1 thua so khong?

**KHONG.** Khong ton tai 1 he so `k` nao dua ca 8 diem phan vi trung nhau (`r_p` khong hang so, `D=11,26 >> 1,5`).
He qua direct: **nguong gate bat buoc phai tinh tu chinh nguon live** (khong the "hieu chuan lai" hang so tuyet doi 2,947-3,760%
thanh mot con so co nghia cho live). Con **hinh dang body** thi **co** the map affine (`0,33 + 1,07x`) nhung chi cho than, **khong** cho duoi.

### (3) 3 phuong an A/B/C — kha thi nhat? entry/thang? rui ro?

| pa | entry/thang ky vong | kha thi? | rui ro chinh |
|---|---|---|---|
| **A thay dyn bang phan vi cuon** | DEV @15': **60,3 / 34,7 / 24,0** (Q995/998/999); LIVE uoc: **~15,6 / 8,7 / 4,4** | **KHONG duoc deploy** (0/3 PASS tren DEV: qua rong, UW 568-773 > 250, 3/5 rate ngoai CI) nhung la **pa duy nhat dung co che** | qua rong => nhieu lenh rac, maxDD -6,3 -> -32,6, meanP/lenh 49,4 -> 10,5; mat tinh chat theo `symbolPred` (1 tick pass = ca 8 ung vien pass) |
| **B giu dyn + hieu chuan lai `SIM_GATE_DYN_SCALE`** | ~9-16/thang | **KHONG dung duoc** | de chon `c <= 2,30/3,76x1,7 = 1,04` **phai nhin phan bo 2026 = fit tren holdout (bi cam)**; va khi da keo vao support live thi dai dong cua dyn chi con **1,35x** => **thoai hoa thanh nguong PHANG** (mat y nghia) |
| **C tat han dyn** | rat lon (tick nao cung pass) | **KHONG** | `base=0,80%` = **p20 cua live** (79,4% mau >=) => ngap lenh; da do tren DEV: **`RESULT_FLATGATE` = -61 pp CAGR** |

**Kha thi nhat = A**, nhung **khong dat chuan deploy** o bai nay. Trong 3 diem Q, **Q=0,999** la diem duy nhat nam trong bang entry [5,30]
tren DEV (24,0/thang) — van vi pham rao `UW` va 3/5 rate. Neu phai chon mot diem de **pre-reg vong sau**, do la `Q=0,999`.

### (4) De deploy duoc thi can gi (KHONG tu deploy)

0. **Ket luan truoc:** bai nay **KHONG de xuat deploy bat cu cau hinh nao** (0/3 PASS). Khong co gi de owner bat.
1. **Sua goc o NGUON, khong o gate (uu tien 1):** lam cho p15 cua **model live** cung don vi/thang do voi bo pred WFO
   (hoac xuat them 1 artifact p15 live de gate dung chinh nguon do, va **do lai phan bo**). Viec nay thuoc duong
   model/live (ONNX/feature export) — **ngoai pham vi bai nay**, can owner + nguoi so huu model.
2. Neu khong sua duoc nguon: **pre-reg MOI** cho luat gate, vi du *phan vi cuon + san theo do tan cua chinh nguon live*
   (2 tham so, khong dung hang so tuyet doi), **van FIT <= 2025-12-31**, va **them dieu kien chat luong lenh**
   (UW <= 250, meanP/lenh khong giam ngoai CI) — pre-reg nay da chot cac nguong do.
3. **Doi chieu bat buoc truoc khi ban:** chay lai **2 cong parity** (`99e42b75…`, `efb793e2…`) tren dung jar se deploy;
   chay tren **shadow** 1 cua so >= 4 tuan (khong phai 6,9 ngay — mau qua nho); **watchdog `gatePassCuoi`** vao `bin/health.sh`.
4. **Nguoi duyet:** owner (deploy jar / doi env/profile / mo holdout). **Rollback:** giu nguyen jar + env hien tai,
   doi `SIM_GATE_P15_Q` ve khong khai / `SIM_GATE_DYN_SCALE` ve 1,7 => ve dung hanh vi cu (byte-identical da chung minh).
5. **Khong tu deploy / khong push** trong bai nay.

### Muc bo / ly do

- **Bo:** phuong an B **khong chay sim** — vi **khong the chon `c` hop le** (moi cach chon deu phai nhin 2026 = fit tren holdout).
  Da tra loi bang dinh luong (thay vi chay 1 chan vo nghia).
- **Bo:** phuong an C **khong chay sim** — da co bang chung **cung cau hinh** tu `RESULT_FLATGATE` (-61 pp CAGR) + so cua bai nay
  (base 0,80% = p20 cua live => ngap).
- **Bo:** khong chay them chan nao ngoai 5 chan da chot (2 parity + 3 pa A) — du de ket luan 0/3 PASS.
- **Bo (sai lech):** uoc entry/thang cho LIVE dung 2 thanh phan (pass rate tren chuoi live **chan doan** x ti le entry/pass
  tren DEV) — la **xap xi**, khong phai sim live; da khai ro.
- **Bo:** so `S_shadow` (609 mau) nho hon `S_live` (8.986) nen chi dung lam bang chung phu; moi ket luan dinh luong dua tren `S_live`.

---

## 5. MUC BO / SAI LECH / GIOI HAN (khai RO)

- **KHONG sua code** => khong phat sinh nhu cau rebuild jar; pa A dat bang 2 key co san; cong parity CA HAI md5
  (neu co buoc nao can sua code thi mac dinh giu nguyen — khong xay ra o bai nay).
- Uoc **entry/thang cho LIVE** dung **hai** thanh phan: ty le pass do tren **chuoi p15 live** (chan doan) x
  **ti le entry/pass** do tren **DEV sim**. Day la xap xi co chu dich (khong co sim live); khai ro.
- `S_live` la **market-level p15** trong log `[PREDICT fail]/[GATE]` (khong phai tung symbol); live gate ap cung 1 nguong
  cho ca tick (pa A) nen cach do nay dung cho pa A, **khong** dung cho pa B (dyn theo `symbolPred`).
- 2026 **chi doc de chan doan**; moi fit/threshold/Q/W deu nam tren `S_dev <= 2025-12-31`.
- Khong cham ONNX / `NUM_FEATURES` / `extractFeatures45` / duong LIVE; khong restart/sua 242/shadow; khong push git.

## 6. BANG CHUNG THO

```bash
python3 research/analysis/gate_rootcause_analyze.py        # phan bo 2 nguon + Poisson + affine
python3 research/analysis/gate_rootcause_live_rolling.py   # chan doan: luat phan vi tren chuoi live
python3 research/analysis/gate_rootcause_run.py all        # 5 chan Kaggle (2 parity + 3 pa A)
python3 research/analysis/gate_rootcause_score.py --k 3    # 5 rate CI + equity bootstrap vs cd-sel15
md5sum /home/ubuntu/kaggle_sim/out/rc-par-kg0/storage/printDone.csv   # 99e42b75cf1a2142f9cd14dc72e371ba
md5sum /home/ubuntu/kaggle_sim/out/rc-par-t170/storage/printDone.csv  # efb793e2468ca3a7318da0f0ad23d4fc
```
