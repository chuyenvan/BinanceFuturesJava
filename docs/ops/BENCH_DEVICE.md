# BENCH_DEVICE — do dut diem: train o dau duoc?

Ngay 2026-09-05. Script: `research/kaggle/bench_device/{make_bench_data.py,run.py,pred.py,analyze.py}`.
Muc tieu: tra loi "co train tren Kaggle duoc khong hay bat buoc Oracle", bang do,
khong bang phan doan. Chay 3 moi truong x 3 seed tren **cung mot file du lieu dong bang**.

## 1. Hash du lieu — buoc dau tien, phai khop truoc khi noi ve GPU

`bench_s1.parquet` dung tu `ledger/cand_dev.parquet` + `featv2/feat_v2.parquet`, giu
`ts, sym, rel5, g1lite` + 9 feature KEEP cua S1, ep **float32**, sort `[ts, sym]`.
1,220,490 dong x 9 feature, 29,415,657 byte.

| hash | gia tri | 3 moi truong |
|---|---|---|
| file sha256 | `6b407696d99bd8fa4477b9faed8e7c3c72f3b0cc9d0b6aa3edbb556b1355c994` | **KHOP** |
| X sha256 (float32 C-contig) | `567fb13314098ce52ac92be13bcf7a5cf6b2246c296c9ee0df2ce82b72b3fd8f` | **KHOP** |
| ts / rel5 / g1lite sha256 | `b652840e…` / `d4602dac…` / `88c500c9…` | **KHOP** |

=> Dau vao dong nhat tuyet doi. Moi khac biet sau day la khac biet **tinh toan**, khong phai du lieu.

## 2. Ba moi truong

| tag | arch | python | numpy | pandas | xgboost | cpu | nthread thuc | device | thoi gian 3 seed |
|---|---|---|---|---|---|---|---|---|---|
| `oracle_cpu` | aarch64 Neoverse-N1 | 3.10.12 | 2.2.6 | 2.3.3 | 3.2.0 | 4 | 4 | `cpu` | 663s |
| `kaggle_cpu` | x86_64 | 3.12.13 | 2.0.2 | 2.3.3 | 3.2.0 | 4 | 4 | `cpu` | 1334s |
| `kaggle_gpu` | x86_64 | 3.12.13 | 2.0.2 | 2.3.3 | 3.2.0 | 4 | 4 | `cuda:0` | 145s |

`OMP_NUM_THREADS` unset ca 3 noi; `n_jobs=4` ghim trong code nen `nthread` thuc bang 4 o ca 3.

## 3. Cay dau tien (`n_estimators=1`, seed 42) — bai test sach nhat

31 node o ca 3 noi. sha256 cua `trees_to_dataframe().to_csv()`:

| tag | tree1 sha256 (16 ky tu dau) |
|---|---|
| `oracle_cpu` | `a5924a0ed04e99cd` |
| `kaggle_cpu` | `a5924a0ed04e99cd` — **GIONG HET Oracle** |
| `kaggle_gpu` | `eec89081b09a56d4` — **KHAC** |

Khac o dau (GPU vs CPU, 31 node):

| cot | so node khac | lech tuyet doi lon nhat |
|---|---|---|
| `Feature` | 7/31 | — (chon feature khac han) |
| `Split` | 11/31 | 0.941 |
| `Gain` | **31/31** | 41.4 |
| `Cover` | **31/31** | 3,580 |

`Cover` lech o **moi** node nghia la tap dong duoc lay mau da khac ngay tu goc:
`subsample=0.8` / `colsample_bytree=0.8` tren GPU dung RNG khac CPU. Cong them
`Split` lech => quantile sketch cua `hist` tren GPU khac CPU. Day la hai nguyen nhan
that, khong phai bug, va khong sua duoc bang cach ghim seed.

`n_jobs=1` vs `n_jobs=4` tren Oracle: tree1 sha **giong het** (`a5924a0ed04e99cd`).

## 4. Between-environment vs between-seed

Nen so sanh: chenh giua seed 42/43/44 **do trong chinh benchmark nay**, khong dung so cu.

### 4.1 Per-tick (danh tinh du doan) — `mean|rankIC_i − rankIC_j|` tren 4,595 tick chung

| cap | tb | max |
|---|---|---|
| `oracle_cpu` vs `kaggle_cpu` | **0.00000** | **0.00000** |
| CPU vs `kaggle_gpu` | 0.02185 | 0.02395 |
| *between-seed, chi CPU (3 cap)* | *0.01824* | *0.01848* |
| *between-seed, gop 3 env (9 cap)* | *0.02051* | *0.02594* |

`CPU vs GPU / between-seed` = **x1.07** (nen gop) hoac **x1.20** (nen CPU).

### 4.2 Aggregate

| cap | \|d mean rank-IC\| tb | max | \|d edge5\| tb | max |
|---|---|---|---|---|
| `oracle_cpu` vs `kaggle_cpu` | **0.00000** | **0.00000** | **0.000pp** | **0.000pp** |
| CPU vs `kaggle_gpu` | 0.00448 | 0.00734 | 0.198pp | 0.274pp |
| *between-seed, chi CPU* | *0.00121* | *0.00181* | *0.164pp* | *0.246pp* |
| *between-seed, chi GPU* | *0.00586* | *0.00879* | *0.083pp* | *0.124pp* |
| *between-seed, gop 3 env* | *0.00276* | *0.00879* | *0.137pp* | *0.246pp* |

**Per-tick va aggregate KHONG cung ket luan cho GPU:**
- per-tick: GPU nam trong nhieu seed (x1.07 – x1.20).
- `edge5`: GPU nam trong nhieu seed (0.198pp vs nen CPU 0.164pp, x1.21).
- `mean rank-IC`: GPU **x3.7 nen CPU** (0.00448 vs 0.00121). Va GPU con **tu no on dinh kem hon**:
  chenh giua seed cua rieng GPU la 0.00586 (max 0.00879), rong gap **4.8 lan** CPU (0.00121 / max 0.00181).

### 4.3 So thuc do tung seed

| seed | `oracle_cpu` | `kaggle_cpu` | `kaggle_gpu` |
|---|---|---|---|
| 42 | 0.173164 / +6.8565% | 0.173164 / +6.8565% | 0.173052 / +7.0085% |
| 43 | 0.171599 / +6.7493% | 0.171599 / +6.7493% | 0.164258 / +6.9165% |
| 44 | 0.171354 / +6.6104% | 0.171354 / +6.6104% | 0.165371 / +6.8841% |

(mean rank-IC / edge5). `ic_sha256` cua chuoi per-tick: Oracle == Kaggle CPU **byte-identical**
o ca 3 seed; `max|d|` per-tick = **0.0** chinh xac.

## 5. Cong `spearman >= 0.999` sai o dau

Cong cu do **spearman(pred_A, pred_B)** roi doi >= 0.999. Do lai dung thong ke do,
tren 774,270 dong OOS gop 10 cutoff (`pred.py`):

| cap | spearman gop | spearman per-tick tb |
|---|---|---|
| CPU s42 vs **GPU** s42 | 0.981279 | 0.963535 |
| CPU s43 vs **GPU** s43 | 0.980005 | 0.956429 |
| **CPU s42 vs CPU s43** (cung may, cung device, chi doi seed) | **0.981651** | **0.969096** |
| GPU s42 vs GPU s43 | 0.983203 | 0.959343 |

**Doi seed tren cung mot may cho spearman 0.9817 — thap hon nguong 0.999.**
Nguong 0.999 loai bo ca viec re-seed chinh mo hinh. No khong do "moi truong co lech khong",
no do "co phai dung mot mo hinh khong" — ma S1 von la mo hinh ngau nhien (`subsample`,
`colsample_bytree`), nen no khong bao gio dat 0.999 voi bat ky thay doi nao.
So cu `0.985490` cho GPU **tot ngang hoac hon** mot lan doi seed. Cong nay khong bao gio
la bang chung chong GPU.

Tuong tu tren chuoi rank-IC: spearman Oracle-vs-Kaggle CPU = **1.000000**; CPU-vs-GPU
0.9800–0.9897; CPU seed-vs-seed **0.98998–0.99049** — cung nam duoi 0.999.

## 6. nthread

`oracle_cpu` seed 42, `n_jobs=4` vs `n_jobs=1` (812s vs 221s):

| do | gia tri |
|---|---|
| tree1 sha256 | **giong het** |
| per-tick `mean\|dIC\|` | **0.00000** |
| `d mean rank-IC` | **0.00000** |
| `d edge5` | **0.000pp** |

`nthread` **khong** anh huong ket qua (`tree_method=hist` cong don theo thu tu co dinh).
Gia thuyet "nthread giai thich lech Oracle-Kaggle" bi bac bo.

## 7. KET LUAN

1. **`kaggle_cpu` == `oracle_cpu` byte-for-byte.** Cung dau vao => cung dau ra, tren aarch64
   lan x86_64, khac ca python (3.10 vs 3.12) va numpy (2.2.6 vs 2.0.2). **Duoc train tren
   Kaggle CPU vo dieu kien.** So cu `0.17040 vs 0.1723` khong phai loi may — voi dau vao
   dong nhat may cho ket qua dong nhat, nen chenh do la khac biet **du lieu / pipeline**
   o mot trong hai phia. Khong duoc dung no lam ly do khoa vao Oracle.
2. **GPU khong tuong duong CPU** nhung ly do khac voi ly do trong lenh cam cu:
   - Khong phai vi per-tick lech (per-tick lech ngang nhieu seed).
   - Ma vi (a) `mean rank-IC` lech x3.7 nen seed cua CPU, va (b) GPU **tu no nhieu hon**:
     dai giua seed rong gap 5 lan CPU.
   - Nguyen nhan da chi ra duoc: RNG lay mau khac (`Cover` lech 31/31) + quantile sketch
     khac (`Split` lech 11/31).
3. **Luat moi:**
   - CPU: train o **bat ky dau** (Oracle hoac Kaggle). Khong can gate.
   - GPU: duoc dung cho **quet/kham pha**, voi dieu kien **ca phep so sanh nam tren cung
     GPU** va bao cao kem **CI it nhat 3 seed**. Khong duoc lay 1 seed tren GPU roi so voi
     1 seed tren CPU.
   - Con nguyen tu lenh cu: **khong ghep cap so tu hai moi truong trong mot so sanh**;
     **parity / byte-identity phai chay tren dung device sinh ra neo**; **Java sim o lai
     Oracle** vi Oracle la data host va la noi sinh neo 60390.
4. **Bo cong `spearman >= 0.999`.** Thay bang: hieu ung phai vuot **CI multi-seed do trong
   cung moi truong**. Neu chua co CI multi-seed thi chua duoc ket luan — do la cai da tao
   2 false positive, khong phai GPU.

## 8. Tai lap

```bash
python3 research/kaggle/bench_device/make_bench_data.py     # dung bench_s1.parquet
BENCH_DEVICE=cpu BENCH_TAG=oracle_cpu BENCH_SEEDS=42,43,44 BENCH_NJOBS=4 \
  BENCH_DATA=/home/ubuntu/bench_device/bench_s1.parquet \
  BENCH_OUT=/home/ubuntu/bench_device/out \
  python3 research/kaggle/bench_device/run.py
# Kaggle: dataset chuyendinh/bench-device-pool (chua bench_s1.parquet + run.py)
#         kernel chuyendinh/bench-device-cpu | bench-device-gpu | bench-device-pgpu
python3 research/kaggle/bench_device/analyze.py
```
