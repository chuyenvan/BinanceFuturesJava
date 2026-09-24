# PREREG_S1_DETERMINISM.md — Kiem gia thuyet determinism S1 baseline18 (n_jobs=1) Kaggle CPU vs Oracle CPU

> Pre-registration. Viet TRUOC khi chay O1/O2/K1. Khong sua sau khi thay ket qua
> (luat AGENT_RUNBOOK.md muc 0.2). Cau hoi: voi `n_jobs=1` va cung wheel
> xgboost 3.2.0, baseline S1 (18-fold, KEEP9, seed 42) tren Oracle CPU va Kaggle CPU
> co ra ket qua BIT-IDENTICAL khong? Day la cau hoi ha tang thuan (KHONG phai thi
> nghiem alpha) de quyet dinh: bo luat "giu 2 baseline rieng Kaggle vs Oracle"
> (`docs/runbooks/KAGGLE_PARITY.md` muc 4.1-4.2, neu bit-identical) hay giu no nhu san nhieu
> moi truong that (neu con lech, du da toi thieu hoa).

## 1. Boi canh

`docs/runbooks/KAGGLE_PARITY.md` (commit `dea92cd`) do venh Oracle vs Kaggle voi `n_jobs=4`:
rank-in-tick trung vi 0.98872 (min 0.47395), `rank_exact_match_frac` **0.05574**,
edge5 lech **+0.19664pp** (Kaggle 15.20947% vs Oracle 15.01283%). Cung-may-Oracle
2 lan (`gate_result.json`) thi `rank_exact_match_frac = 1.000000` -- khop tuyet doi.

**Gia thuyet MASTER**: venh Oracle-vs-Kaggle o `n_jobs=4` la do XGBoost `tree_method=hist`
voi da luong (`n_jobs>1`) cong don so hoc float theo THU TU phu thuoc lich trinh he
dieu hanh cho tung luong -- khong bit-deterministic cross-machine du cung code/data/seed.
Ep `n_jobs=1` (don luong, khong con phu thuoc lich trinh) tren CA HAI may co the ra
bit-identical, vi ca Oracle va Kaggle CPU image deu la x86-64 Linux va dung CUNG mot
wheel prebuilt `xgboost==3.2.0` (khong tu build tu source o ben nao).

**Du doan MASTER (ghi truoc khi chay)**: nhieu kha nang O1==O2==K1 bit-identical
(cung wheel x86-64, don luong, khong nguon ngau nhien nao khac con hoat dong).

## 2. Thiet ke — chi doi DUNG MOT thu

So voi baseline goc (`pred_baseline18.parquet`, `n_jobs=4`, sinh boi
`research/analysis/s1_hpo_bag_featgrp.py` mode baseline / logic `run_variant`+`load_D`),
CHI doi `n_jobs=4 -> n_jobs=1`. Moi thu khac giu Y HET baseline goc:

- KEEP9 feature set, `xgboost==3.2.0`, `tree_method="hist"`, `random_state=42`.
- `CUTS18` (18-fold), `PURGE=72h`, `TZ=+7h` giong het.
- Cung thu tu dong da sort theo `ts,sym` truoc train/predict (nhu `run_variant`/
  `train_baseline18_kaggle.py` da lam: `tr = D[...].sort_values("ts")`,
  `oos = D[...].sort_values("ts")`).
- Cung dtype nhu baseline goc dang dung: `load_D`/`make_reduced_dataset.py` da downcast
  `float64 -> float32` cho KEEP9 (vi Oracle chi co 23G RAM, doc du 40 cot se OOM-kill --
  xem comment dong 96-97 `s1_hpo_bag_featgrp.py`). Day KHONG phai bien can kiem trong
  thi nghiem nay (no giong het giua Oracle-goc va Kaggle-goc san co) -- O1/O2/K1 deu
  DUNG Y HET buoc downcast nay, khong doi.
- Dataset Kaggle: dung lai nguyen `chuyendinh/s1-featv2-x1-20260919` (da co san, KHONG
  tao lai) -- 100% giong file Oracle rut gon `feat_v2_x1_keep9.parquet` +
  `cand_dev_x1_lite.parquet` da dung cho ban `n_jobs=4`.
- Model + pipeline train/predict/rank: y het `train_baseline18_kaggle.py` (da xac nhan
  la copy trung logic `run_variant`/`load_D` mode baseline trong `KAGGLE_PARITY.md`).

3 lan chay:

- **O1, O2**: baseline `n_jobs=1` tren Oracle, 2 lan doc lap, cung script, cung input
  file, chi khac ten file output -- xac nhan Oracle tu no co deterministic voi
  `n_jobs=1` hay khong.
- **K1**: baseline `n_jobs=1` tren Kaggle (kernel moi, pin `pip install xgboost==3.2.0`,
  in version, CPU, `n_jobs=1`), tai pred ve Oracle.

So sanh tung cap (O1<->O2, O1<->K1) bang script dua tren
`compare_parity_kaggle.py`, do:

- (a) **bit-identical cot score** — phep do CHINH: sort ca hai theo `(ts,sym)`,
  `np.array_equal(score_1, score_2)` (so bytes tuyet doi, khong dung tolerance).
- (b) `rank_exact_match_frac`.
- (c) `max|delta_score|` (0 neu bit-identical).
- (d) chenh edge5 tong (pp).
- (e) rank-in-tick trung vi / min.

## 3. Pre-declare ket luan (viet TRUOC khi chay)

- **Neu O1==O2 bit-identical VA O1==K1 bit-identical** (`max|delta_score|=0` ca hai cap)
  => **KET LUAN: determinism dat duoc voi `n_jobs=1`, Kaggle==Oracle bit-identical.
  BO luat 2-baseline rieng cua `KAGGLE_PARITY.md` muc 4.1-4.2. Mot baseline chay o dau
  cung duoc; so cheo Kaggle<->Oracle HOP LE khi `n_jobs=1`.** Vênh 0.197pp o ban
  `n_jobs=4` la non-determinism da luong, KHONG phai gioi han ha tang co ban.
- **Neu O1==O2 bit-identical nhung O1!=K1 (`max|delta_score|>0`)** => con SAN FLOAT-CPU
  cross-machine THAT du da don luong (vd khac libc/BLAS/CPU flags dun toi lam tron khac
  nhau o muc thap hon xgboost). Bao cao chinh xac max|delta_score|, edge5 lech bao nhieu
  pp, `rank_exact_match_frac`. Day la SAN NHIEU TOI THIEU (da toi uu bang n_jobs=1),
  KHONG phai 0.197pp cu cua `n_jobs=4` -- GIU luat "so cung moi truong" cua
  `KAGGLE_PARITY.md`, ghi ro san nay la da toi thieu hoa.
- **Neu O1!=O2 (Oracle tu lech voi n_jobs=1 tren CUNG mot may)** => con nguon
  non-determinism KHAC ngoai da luong (thu tu dong doc/sort? BLAS/OpenMP noi bo van
  da luong du n_jobs=1? Nondeterministic hash cua Python set/dict o buoc nao do?).
  Dieu tra rieng, BAO CAO, CHUA ket luan ve cau hoi Kaggle-vs-Oracle (vi ngay ca
  Oracle-vs-Oracle da khong on dinh thi so cheo Oracle-vs-Kaggle vo nghia).

## 4. Rang buoc

Khong tune (khong doi hyperparam/feature/label/purge/cuts). Khong GPU. Khong
`git push` (agent commit branch `module`, user tu push). Khong ssh 242. Khong dung
toi du lieu 2026 hay `HOLDOUT_UNSEAL`. `n_jobs=1` du kien cham hon ~4x (moi lan Oracle
~40 phut uoc tinh) -- chap nhan, KHONG cat so fold de rut ngan.

## 5. File output du kien

- Oracle: `/home/ubuntu/s1hpo/pred_baseline18_n1_o1.parquet`,
  `/home/ubuntu/s1hpo/pred_baseline18_n1_o2.parquet`,
  `/home/ubuntu/s1hpo/kaggle_kernel_det/out/pred_baseline18_n1_kaggle.parquet` (tai ve).
- `/home/ubuntu/s1hpo/determinism.json` (5 chi so x 2 cap so sanh).
- Ket qua ghi vao `docs/result/RESULT_S1_DETERMINISM.md` va cap nhat dau `docs/runbooks/KAGGLE_PARITY.md`
  neu nhanh bit-identical dung.
