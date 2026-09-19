# RESULT_S1_DETERMINISM.md -- Ket qua kiem gia thuyet determinism (n_jobs=1)

> Doi chieu `docs/PREREG_S1_DETERMINISM.md` (commit `e8963c5`, viet TRUOC khi chay).
> KHONG sua pre-reg sau khi thay ket qua. Bang so du gia dinh MASTER cua pre-reg
> (ca hai may x86-64) la SAI -- xem muc 2.

## 1. Ket qua 3 lan chay

| run | may | n_jobs | edge5 all | thoi gian train 18-fold | platform |
|---|---|---|---|---|---|
| O1 | Oracle | 1 | 15.012825% | 2192.8s (~36.5 phut) | `Linux-6.8.0-1060-oracle-**aarch64**-glibc2.35` |
| O2 | Oracle | 1 | 15.012825% | 2195.7s (~36.6 phut) | `Linux-6.8.0-1060-oracle-**aarch64**-glibc2.35` |
| K1 | Kaggle | 1 | 15.209468% | 2438.6s (~40.6 phut) | `Linux-6.12.90+-**x86_64**-glibc2.35` |

xgboost **3.2.0** ca hai ben (pin dung, dung wheel prebuilt). python: Oracle 3.10.12,
Kaggle 3.12.13 (khac ban python, khong khac ban xgboost).

## 2. PHAT HIEN QUAN TRONG lam SAI mot gia dinh cua pre-reg

Pre-reg (muc 1) gia dinh "**ca Oracle va Kaggle CPU image deu la x86-64 Linux**".
**Gia dinh nay SAI**: `platform.platform()` do truc tiep trong log O1/O2/K1 cho thay
**Oracle chay tren aarch64 (ARM64)**, con **Kaggle CPU image la x86_64**. Day la
KIEN TRUC CPU KHAC NHAU, khong phai cung mot kien truc nhu pre-reg gia dinh khi dat
gia thuyet MASTER ("cung wheel prebuilt x86-64"). Phat hien nay khong lam vo hieu
pre-reg (thiet ke van dung: chi doi n_jobs, moi thu khac giu nguyen) nhung thay doi
cach doc ket qua o muc 3 -- xem giai thich.

## 3. 5 chi so moi cap (script: `research/pipeline/x1/kaggle_parity/... det_compare.py`
tren Oracle, output `/home/ubuntu/s1hpo/determinism.json`)

### O1 vs O2 (Oracle vs chinh no, n_jobs=1, 2 lan doc lap)

| chi so | gia tri |
|---|---|
| **bit_identical_score** | **True** |
| max\|delta_score\| | **0.0** |
| rank_exact_match_frac | **1.000000** |
| spearman toan cuc | 1.000000 |
| rank-in-tick median / min | 1.000000 / 0.999999999999999 |
| edge5 O1 / O2 | 15.012825% / 15.012825% (delta 0.0 pp) |

=> Oracle voi `n_jobs=1` **hoan toan deterministic noi bo** (nhu ky vong, va nhu
`gate_result.json` da xac nhan truoc do voi `n_jobs=4`).

### O1 vs K1 (Oracle vs Kaggle, ca hai `n_jobs=1`)

| chi so | gia tri (n_jobs=1, O1 vs K1) | doi chieu ban CU (n_jobs=4, `parity_result.json`) |
|---|---|---|
| **bit_identical_score** | **False** | (chua do o ban cu) |
| max\|delta_score\| | **357.0** (dieu vi score la RANK trong tick, khong phai xac suat) | -- |
| rank_exact_match_frac | **0.055740** | 0.055740 |
| spearman toan cuc | 0.992777 | 0.992777 |
| rank-in-tick median / min | 0.988716 / 0.473950 | 0.988716 / 0.473950 |
| edge5 lech (Kaggle - Oracle) | **+0.196643pp** (15.209468% vs 15.012825%) | +0.196643pp (15.209468% vs 15.012825%) |

=> **5/5 chi so GIONG HET (toi 6 chu so thap phan) giua ban n_jobs=1 va ban n_jobs=4
cu.** `n_jobs=1` KHONG lam giam mot chut nao rank_exact_match_frac, edge5 lech,
hay rank-in-tick -- san nay khong bi thu hep di chut nao.

## 4. Nhanh pre-declare nao dung, va dieu chinh cach doc

Theo pre-reg muc 3: O1==O2 bit-identical (dung) VA O1!=K1 voi max\|delta_score\|>0
(dung) => roi vao **nhanh 2**: "con SAN FLOAT-CPU cross-machine THAT du da don luong
... GIU luat 'so cung moi truong' cua KAGGLE_PARITY.md".

**Nhung so lieu manh hon dieu pre-reg du doan cho nhanh nay.** Pre-reg viet nhanh 2
voi ham y san se DUOC THU HEP boi n_jobs=1 ("da toi uu bang n_jobs=1", "khong phai
0.197pp cu"). Thuc te: **san KHONG thu hep mot chut nao** -- 5/5 chi so trung khop
tuyet doi voi ban n_jobs=4 cu. Dieu nay **BAC BO gia thuyet MASTER cua pre-reg**
("venh do XGBoost hist + n_jobs>1 cong don float da luong theo thu tu phu thuoc
lich trinh he dieu hanh"): neu da luong la nguyen nhan, giam n_jobs=4 -> 1 phai lam
giam it nhieu do lech; o day do lech khong doi mot ly nao. Ket hop voi Phat hien
muc 2 (Oracle = aarch64, Kaggle = x86_64 -- KHAC kien truc CPU), gia thuyet HOP LY
HON nhieu la: **venh Oracle-vs-Kaggle den tu KIEN TRUC CPU khac nhau (ARM64 vs x86_64)
lam xgboost `tree_method=hist` sinh ra split-point/tich luy float khac nhau o muc
intrinsic/compiler-backend cua wheel, hoan toan doc lap voi so luong luong (n_jobs)**.
Day KHONG phai thi nghiem da thiet ke de tach rieng "kien truc CPU" khoi "da luong"
(hai bien nay von di di kem nhau giua 2 may that su san co: Oracle luon la aarch64,
Kaggle luon la x86_64) -- nen day la suy luan HOP LY NHAT tu du lieu hien co, KHONG
phai ket luan da chung minh day du (can mot may x86-64 Oracle-tuong-duong hoac mot
Kaggle GPU/CPU aarch64 de tach bach that, hien khong san co).

## 5. KET LUAN

- **BAC BO gia thuyet MASTER** (da luong `n_jobs>1` la nguyen nhan venh): `n_jobs=1`
  khong lam thay doi bat ky chi so nao trong 5 chi so venh Oracle-Kaggle so voi
  `n_jobs=4`.
- **GIU NGUYEN luat "2-baseline rieng cho Kaggle vs Oracle"** cua
  `docs/KAGGLE_PARITY.md` muc 4.1-4.2 -- **KHONG bo**. Cam so Kaggle-variant voi
  Oracle-baseline va nguoc lai van dung nhu cu.
- San nhieu moi truong Oracle-vs-Kaggle o day la **~0.197pp edge5 / rank_exact_match_frac
  ~5.6% / rank-in-tick median ~0.989**, KHONG phu thuoc n_jobs (1 hay 4 deu nhu nhau).
  Day nhieu kha nang la do **kien truc CPU khac nhau (aarch64 Oracle vs x86_64
  Kaggle)**, khong phai do lich trinh luong.
- **Oracle-vs-Oracle van bit-identical tuyet doi** bat ke n_jobs (`gate_result.json`
  voi n_jobs=4, va O1 vs O2 o day voi n_jobs=1) -- so sanh Oracle-variant voi
  Oracle-baseline tren CUNG mot may van la phep so hop le va dang tin cay 100%.

## 6. File

- Script train Oracle (chi doi n_jobs so voi baseline goc, cung logic
  `run_variant`/`load_D` nhu `train_baseline18_kaggle.py`):
  `/home/ubuntu/s1hpo/det/det_train_oracle_n1.py`.
- Script kernel Kaggle (n_jobs=1): `/home/ubuntu/s1hpo/kaggle_kernel_det/train_baseline18.py`,
  kernel `chuyendinh/s1-baseline18-det-n1-20260919` (private, CPU, COMPLETE).
- Output: `/home/ubuntu/s1hpo/pred_baseline18_n1_o1.parquet`,
  `pred_baseline18_n1_o2.parquet`, `kaggle_kernel_det/out/pred_baseline18_n1_kaggle.parquet`.
- So sanh: `/home/ubuntu/s1hpo/det/det_compare.py` -> `/home/ubuntu/s1hpo/determinism.json`.
- Pre-reg: `docs/PREREG_S1_DETERMINISM.md` (commit `e8963c5`).
