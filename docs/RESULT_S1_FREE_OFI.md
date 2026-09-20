# RESULT_S1_FREE_OFI — order-flow-imbalance (OFI) tu Binance Vision aggTrades (mien phi), cho S1

Ket qua THAT cua ca Giai doan A (khao sat kha thi) va Giai doan B (thong ke), chay theo
dung `docs/PREREG_S1_FREE_OFI.md` (commit truoc, khong sua sau khi thay so). Ket luan
cuoi: **HARNESS_NGHI_NGO** — khong cong bo THANG/NULL/THUA cho candidate OFI trong vong
nay, ly do chi tiet o muc 4.

## 1. Giai doan A — kha thi (tom tat, chi tiet day du da nam trong PREREG muc 1)

- Nut that la PARSE CSV (`pandas.read_csv` ~257-317k dong/s), KHONG phai bang thong tai
  (~62MB/s). `duckdb.read_csv`+`GROUP BY` nhanh hon ~18x (4.6-4.7 trieu dong/giay).
- Quyet dinh pham vi (chot TRUOC khi tai du lieu that cho Giai doan B): **15 symbol**
  thanh khoan cao nhat (sau khi loai 8 memecoin niem yet muon), **giu nguyen ca so 54
  thang** 2021-07→2025-12 de khong pha vo 18-fold SELECT/CONFIRM chuan.

## 2. Giai doan B buoc 1 — build feature (SO THAT, kernel `chuyendinh/ofi-build-feat-15sym`)

Tu `ofi_build_summary.json` (dinh kem `research/pipeline/x1/kaggle_ofi/`):

| | |
|---|---|
| Tong thoi gian | **5,667.5s (≈1.57 gio)** — trong nguong an toan 3.5h da dat |
| `stopped_early` | **false** — hoan tat DAY DU 15 symbol x 54 thang, khong bi cat ngang |
| Symbol-thang thu | 810 (15 x 54) |
| Tai thanh cong (`n_ok`) | 486 |
| Bo qua 404 (`n_skip_404`) | 324 — TOAN BO la do symbol niem yet muon hon 2021-07 (vd
  AIAUSDT, ALCHUSDT, COAIUSDT, EVAAUSDT, MYXUSDT chua ton tai truoc mot moc nao do; xem
  danh sach day du trong `ofi_build_log.json`), KHONG co loi mang/HTTP nao khac |
| Loi khac (`n_err`) | **0** |
| So symbol co du lieu | 15/15 (moi symbol co it nhat vai thang du lieu) |
| Dong feature gio ra | 349,651 dong (`ts`, `sym`, `ofi_1h`, `aggr_buy_ratio_1h`) |
| Khoang thoi gian phu | 2021-07-01 → 2025-12-31 |

Dung dung uoc luong o PREREG (~1.2-2.1h) — so that 1.57h nam trong khoang do.

## 3. Giai doan B buoc 2 — train/danh gia (SO THAT, kernel `chuyendinh/ofi-train-eval-15sym`)

`ofi_coverage_frac = 0.026631` (**2.66%** dong trong pool co `ofi_1h` khong NaN) — thap
hon uoc tinh tho ban dau (15/60≈25% neu tinh theo so symbol trong universe 60, nhung pool
`feat_v2_x1_keep9.parquet` bao phu TOAN BO >600 symbol cua he thong, khong chi 60; cong
them 324/810 symbol-thang la 404 do niem yet muon) — dung nhu gioi han da disclose truoc
o PREREG muc 5.1-5.2, khong phai bat ngo.

`baseline_edge5_all_pct = 15.209468%` — **khop chinh xac** voi so da luu trong
`docs/RESULT_S1_DETERMINISM.md` (kernel `chuyendinh/s1-baseline18-det-n1-20260919`),
xac nhan file baseline duoc tai su dung dung, khong bi hong/doi.

### 3.1 Bang CI (theo dung khung `PREREG_S1_HPO_BAG_FEATGRP.md`/`PREREG_S1_NOISE_CAL.md`)

Don vi: diem phan tram tuyet doi cua edge5 (vd `+0.0295` = **+2.95 diem phan tram** so
voi baseline 15.21%), rank-IC o don vi thap phan thuong (khong nhan 100).

| Bien the | SELECT mean Δedge5 | SELECT nguong `inflate(2)*sd_boot` | SELECT vuot nguong? | CONFIRM Δedge5 (CI95×inflate(2)) | CONFIRM verdict edge5 | CONFIRM Δrank-IC (CI95×inflate(2)) | CONFIRM verdict rank-IC |
|---|---|---|---|---|---|---|---|
| **candidate** (KEEP9+ofi_1h+aggr_buy_ratio_1h) | −0.00109 (−0.109pp) | 0.00222 | KHONG | **+0.02946** [+0.00930, +0.05685] (**+2.95pp** [+0.93, +5.68]) | **THANG*** | +0.000116 [−0.00114, +0.00133] | NULL |
| **noise_ofi_check** (doi chung, k=2, cung mask NaN voi ofi_1h) | −0.00294 (−0.294pp) | 0.00194 | **CO** | **+0.01688** [+0.00041, +0.03934] (**+1.69pp** [+0.04, +3.93]) | **THANG*** | +0.000136 [−0.00116, +0.00152] | NULL |

`*` — verdict edge5 RIENG cua tung bien the theo cong thuc §4 cua PREREG (CI khong chua
0, mean>0), **NHUNG khong duoc cong bo la ket luan chinh thuc** vi bi loai bo boi luat
§4.1(b) — xem muc 4.

`n_ticks` CONFIRM = 13,914 (edge5) / 13,805 (rank-IC) cho ca hai bien the — **giong het
nhau**, xac nhan tap tick OOS trung khop tuyet doi voi baseline (sanity check muc 4.2 cua
PREREG PASS).

## 4. Ap dung luat quyet dinh §4.1 cua PREREG — vi sao HARNESS_NGHI_NGO

**`noise_ofi_check` vuot nguong CA tren SELECT (§4.1a) LAN tren CONFIRM (§4.1b)** — CI
CONFIRM cua doi chung nhieu KHONG chua 0 (`[+0.00041, +0.03934]`). Theo dung luat da
chot TRUOC khi thay so: **KHONG duoc cong bo THANG cho candidate that**, phai dung dieu
tra truoc khi ket luan. Da thuc hien dieu tra sau (dung du lieu/log da co, khong chay
them kernel moi ngoai pham vi da pre-register):

### 4.1 Sanity check bat buoc (§4.2 PREREG) — TOAN BO PASS

- Tap `ts` OOS cua candidate/noise trung tuyet doi voi baseline (`assert` trong script
  khong bao loi — kernel chay het, khong dung giua chung o assertion nao).
- `score` khong NaN/Inf (assert PASS).
- `assert tr.ts.max() < c` giu nguyen moi fold (khong bao loi purge/leak).
- => **Khong phat hien loi purge/join/leak theo nghia truyen thong** (nhiem vu, khong
  phai gia dinh).

### 4.2 Bang chung chinh: candidate va noise gan nhu GIONG HET nhau theo tung fold

Trich log kernel (`ofi-train-eval-15sym.log`), edge5 OOS THO (chua tru baseline) tung
fold, candidate vs noise:

| fold | cutoff | ticks | candidate edge5 | noise edge5 | chenh lech |
|---|---|---|---|---|---|
| 0 | 2021-07-01 | 489 | +8.182% | +8.157% | +0.025pp |
| 1 | 2021-10-01 | 445 | +6.534% | +5.989% | +0.545pp |
| 2 | 2022-01-01 | 952 | +4.691% | +4.121% | +0.570pp |
| 3 | 2022-04-01 | 1290 | +5.431% | +5.886% | −0.455pp |
| 4 | 2022-07-01 | 241 | +3.854% | +3.748% | +0.106pp |
| 5 | 2022-10-01 | 445 | +12.424% | +11.284% | +1.140pp |
| 6 | 2023-01-01 | 247 | +7.439% | +8.005% | −0.566pp |
| 7 | 2023-04-01 | 76 | +4.988% | +5.081% | −0.093pp |
| 8 | 2023-07-01 | 44 | +13.472% | +13.077% | +0.395pp |
| 9 | 2023-10-01 | 140 | +11.766% | +10.378% | +1.388pp |
| 10 | 2024-01-01 | 814 | +8.522% | +8.746% | −0.224pp |
| 11 | 2024-04-01 | 346 | +4.304% | +4.200% | +0.104pp |
| 12 | 2024-07-01 | 291 | +9.723% | +9.724% | −0.001pp |
| 13 | 2024-10-01 | 809 | +10.261% | +8.760% | +1.501pp |
| 14 | 2025-01-01 | 1167 | +15.002% | +14.774% | +0.228pp |
| 15 | 2025-04-01 | 1483 | +9.452% | +8.227% | +1.225pp |
| 16 | 2025-07-01 | 2095 | +16.954% | +17.893% | −0.939pp |
| 17 | 2025-10-01 | 6909 | +29.338% | +26.976% | +2.362pp |

Ca hai bien the bam sat nhau tren TOAN BO 18 fold (chenh lech tuyet doi tung fold nam
trong khoang [−0.94, +2.36]pp, KHONG co pattern he thong candidate > noise), trong khi
CA HAI cung deu cao hon han baseline reused (15.21% trung binh 18-fold) — dac biet ro o
cac fold gan nhat (14, 16, 17 deu >15%, fold 17 len toi ~27-29%). Day la bang chung
MANH: khoan "cai thien" +1.7 den +2.9pp do duoc tren CONFIRM **KHONG the quy cho noi
dung cua OFI/aggr_buy_ratio** — vi mot cot nhieu ngau nhien thuan tuy (`noise_ofi_check`)
tao ra hieu ung GAN NHU GIONG HET.

### 4.3 Gia thuyet nguyen nhan chinh (chua duoc xac nhan 100% — can theo doi them)

Ca `ofi_candidate` va `ofi_noise` deu duoc **train MOI trong kernel nay** (2026-09-20),
trong khi **baseline dung de so sanh la file dong bang** (`pred_baseline18_n1_kaggle.
parquet`) tu MOT kernel KHAC, chay o MOT NGAY KHAC (`s1-baseline18-det-n1-20260919`,
2026-09-19). `docs/RESULT_S1_DETERMINISM.md` da xac nhan mot khoang lech kien truc
aarch64-vs-x86_64 CO THAT (~0.197pp) NHUNG **CHUA TUNG kiem tra rieng** kha nang tai lap
(reproducibility) **giua hai lan chay KHAC NHAU tren CUNG kien truc Kaggle x86_64**
(cung code, cung seed=42, cung n_jobs=1, khac session/khac ngay — vd do image Kaggle
mac dinh cap nhat phien ban numpy/pandas/scipy KHONG duoc pin phien ban trong ca hai
script, hoac do bien dong phan cung/BLAS giua cac container khac nhau cua Kaggle).
Bien do do duoc o day (candidate va noise deu ~+1.7 den +2.9pp CONFIRM so voi baseline
dong bang, trong khi CACH NHAU giua candidate/noise chi vai phan tram diem — nho hon han)
phu hop hon voi gia thuyet "baseline dong bang tu session khac KHONG con so sanh duoc
mot cach an toan voi bien the moi train hom nay", hon la voi mot loi purge/join cu the
(vi tat ca sanity check muc 4.1 deu PASS).

**Day la mot LO HONG PHUONG PHAP luan quan trong can bao cao MASTER**: quyet dinh
"TAI SU DUNG baseline dong bang" (PREREG muc 3, dong y voi tien le HPO_BAG_FEATGRP/
NOISE_CAL) ngam dinh Kaggle-chay-lai-cung-code-la-tai-lap-duoc — GIA DINH NAY CHUA TUNG
DUOC KIEM CHUNG DOC LAP truoc vong nay, va ket qua vong nay cho thay no CO THE SAI voi
bien do lon hon nhieu (~1-3pp edge5) so voi bat ky hieu ung feature thuc te nao dang
tim kiem.

### 4.4 De xuat buoc tiep theo (KHONG thuc hien trong vong nay — ngoai pham vi pre-reg da chot)

De xac nhan/bac bo gia thuyet 4.3: chay LAI mot bien the `baseline_fresh` (KEEP9 thuan,
CUNG code/seed/n_jobs, train MOI trong CUNG kernel voi candidate/noise thay vi tai su
dung file dong bang) va so sanh 3 chieu (`baseline_fresh` vs `candidate` vs `noise`)
TRONG CUNG MOT lan chay. Neu `baseline_fresh` cung cho edge5 CONFIRM cao hon
`pred_baseline18_n1_kaggle.parquet` mot khoang tuong tu (~1-3pp), gia thuyet 4.3 duoc
xac nhan va co the danh gia lai candidate mot cach cong bang (candidate vs baseline_fresh
CUNG session). Day la mot vong do luong MOI, can MASTER duyet truoc khi chay (thay doi
thiet ke "tai su dung baseline" da pre-register).

## 5. Ket luan cuoi cung

**HARNESS_NGHI_NGO** (theo dung nhan da dinh nghia truoc trong PREREG §4.1b) —
**KHONG cong bo THANG/NULL/THUA cho gia thuyet "OFI/aggr_buy_ratio tu Binance Vision
aggTrades giup S1"** trong vong nay. Nguyen nhan nhieu kha nang nhat la lo hong phuong
phap luan o muc 4.3 (baseline dong bang tu session khac khong con dang tin cay de so
sanh voi bien the train moi), KHONG phai loi purge/join/leak truyen thong (da loai qua
sanity check muc 4.1), va CUNG khong phai bang chung phan bac gia thuyet OFI (vi hieu
ung do duoc hoan toan co the la nhieu he thong, KHONG lien quan gi den noi dung feature).

De tra loi cau hoi goc ("OFI tu Binance Vision co giup S1 khong") mot cach dang tin cay,
CAN mot vong do luong moi voi baseline train-moi-trong-cung-session (muc 4.4), duoc
MASTER duyet truoc khi chay (vi day la thay doi thiet ke so voi PREREG da chot cua vong
nay).

## 6. File/artifact lien quan

- `docs/PREREG_S1_FREE_OFI.md` — pre-reg day du (chot truoc so).
- `research/pipeline/x1/kaggle_ofi/ofi_build_feat.py` — kernel Giai doan B buoc 1
  (`chuyendinh/ofi-build-feat-15sym`, COMPLETE).
- `research/pipeline/x1/kaggle_ofi/ofi_train_eval.py` — kernel Giai doan B buoc 2
  (`chuyendinh/ofi-train-eval-15sym`, COMPLETE).
- `research/pipeline/x1/kaggle_ofi/stage_a_results.json`,
  `research/pipeline/x1/kaggle_ofi/stage_a2_results.json` — so lieu Giai doan A.
- `research/pipeline/x1/kaggle_ofi/ofi_build_summary.json`,
  `research/pipeline/x1/kaggle_ofi/ofi_build_log.json` — so that Giai doan B buoc 1.
- `research/pipeline/x1/kaggle_ofi/ofi_result.json` — so that day du Giai doan B buoc 2
  (bang muc 3.1 trich tu day).

## 7. CAP NHAT 2026-09-20 -- DIEU TRA HARNESS_NGHI_NGO DAY DU (theo yeu cau Uni/MASTER)

Da dieu tra day du theo dung trinh tu MASTER yeu cau (Giai doan 1 re truoc: kiem tra
population mismatch bang doc code + thuc nghiem row/tick-count + restricted-population
test; Giai doan 2: train baseline_fresh + candidate + noise CUNG session de kiem tra
truc tiep cross-session determinism). CA HAI gia thuyet nay (population mismatch,
cross-session non-determinism) deu bi **BAC BO bang bang chung thuc nghiem truc tiep**:

- Population: `len(BASE)==len(CAND)==len(NOISE)=6,685,957`, so tick giong het
  (18,283=18,283=18,283), 0/18,283 tick lech so dong. Han che quan the xuong dung tap
  co OFI-coverage (2.66-2.80%) lam edge5 **GIAM** (khong tang) cho ca 3 bien the --
  nguoc huong hoan toan voi gia thuyet population mismatch.
- Cross-session determinism: train lai `baseline_fresh` (KEEP9 thuan) TRONG CUNG kernel
  voi candidate/noise (kernel `chuyendinh/ofi-train-eval-v2-audit`, 2026-09-20) cho ket
  qua **GIONG HET TUYET DOI** voi `baseline_frozen` (session 2026-09-19):
  `15.209467887878418% == 15.209467887878418%`, CONFIRM delta = 0.000000 CHINH XAC.
  Kaggle tai lap 100% giua hai session cach nhau 1 ngay -- khong co drift.

**Nguyen nhan that su da xac dinh**: mot CONFOUND missingness-la-chi-bao-subset-symbol
-- vi OFI/noise chi phu 15/>600 symbol, mask NaN cua chung trung khop chinh xac voi
"co phai 1 trong 15 symbol thanh khoan cao duoc chon o Giai doan A hay khong"; XGBoost
hoc huong-mac-dinh cho NaN nhu mot chi bao nhi phan DOC LAP voi gia tri that (neu co) --
va 15 symbol nay tinh co co dac tinh edge5 CONFIRM (2024-2025) khac biet so voi phan
con lai cua universe, hoan toan KHONG lien quan gi den OFI/order-flow. Day KHONG phai
loi purge/join/leak, KHONG phai bug harness -- ma la GIOI HAN THIET KE tat yeu cua
quyet dinh thu hep pham vi 15/>600 symbol da chot o Giai doan A.

Chi tiet day du (bang so lieu, code trich dan, kiem tra tung buoc, ra soat cac vong
truoc, de xuat huong tiep theo neu muon tach OFI-content ra khoi confound) tai
`docs/AUDIT_HARNESS_OFI_2026-09-20.md`.

**Verdict cuoi cung khong doi**: HARNESS_NGHI_NGO -> khong cong bo THANG/NULL/THUA cho
gia thuyet OFI trong thiet ke hien tai -- nhung nay la mot ket luan CO NGUYEN NHAN RO
RANG (confound thiet ke), khong con la "chua ro nguyen nhan" nhu ban dau. Cac vong
truoc (`RESULT_S1_HPO_BAG_FEATGRP.md`, `PREREG_S1_NOISE_CAL.md`) KHONG dung feature
gioi han theo subset-symbol nen KHONG can ra soat lai vi ly do nay; quyet dinh "tai su
dung baseline dong bang" trong cac vong do da duoc XAC NHAN AN TOAN boi phep do cross-
session determinism o tren.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
