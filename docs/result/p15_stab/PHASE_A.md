# PHASE_A - PREREG_P15_STAB (dea45002, sha256 56cf84b0d38edf2d) - agent RUN, 2026-11-24
Code: code/stab_train.py (sha256 prefix 4e8b19a50563ccf9; recipe train_gate_fold.py b41c9159 nhung base64, md5 kiem luc chay, chay qua runpy).
Kernel copy = stab_train.py voi 1 dong KAGGLE_FOLDS thay doi (k/p15-stab-aN/stab_train.py).
Oracle heavy lock: giu 15:01 -> nha 15:06 (run_checks.sh, flock -w 600 oracle_heavy.lock nice -n 10). Khong co run_rlive.

## k1 - DAT
PROD seed 42 cut 20260701 (nhanh k1 rieng, loc+assert ts < 2026-07-01, khong luu pred) -> booster sha256
71e825723e494fe05e4bad62e281782a81103f86c1c9d11dbb81a2d0b958f582 == T1. train_rows 2889607, train_ts_max 1782837840000 (khop T1).
=> duong vao (doc chunk + loc + patch read_csv + patch fit random_state + stub ONNX) tai lap byte tren Oracle (xgboost 3.2.0, pandas 2.3.3, numpy 2.2.6).

## k2 - DAT
Fold 20251001 (OOS 2025Q4, n=132480), 8 booster PROD E8 nhom 1 (seed 42,7,123,13,2024,21,777,99), edge 0.
Gop: noi 1200 cay, la (split_conditions + base_weights o nut la) chia 8, base_score = trung binh (ca 8 = 0.0058394973), iteration_indptr 0..1200.
max|pred_gop - mean(8)| = 1.34e-07 (<= 1e-6) ; |pred| max 0.112.
ONNX (onnxmltools san co tren Oracle, khong cai moi) cua booster gop: max|d| vs mean 2.42e-08, vs booster gop 1.34e-07. File:
out/f20251001/E8g1_f20251001_merged.booster.json (sha b21383f3...), E8g1_f20251001_merged.onnx (sha b0af2930...).

## smoke + chi phi
Oracle 4 CPU: 1 lan train (recipe day du, gom in-sample IC) = 16-17 s o 2.36-2.50 M dong (fold 2025Q3/Q4); ~0.9 s / quy du lieu.
Doc CSV + loc: ~12 s. Ma tran: 17 fold x 46 job = 782 lan train ; tong ~ sum(3..19 quy)=187 x 46 x 0.9 s ~ 2.1 h CPU Oracle.
Kaggle 4 kernel x (46-49 don vi quy) ~ 33 ph toc do Oracle ; Kaggle CPU thuong cham 1.5-2.5x => du kien 50-80 ph/kernel => xong ~16:00-16:30 (+07).
DET kiem: subsample/colsample_* = 1.0 trong params thuc te; booster DET khac PROD (sha dacea9ed vs d8af0ea2 fold 20250701).

## SEED_PLAN (out/SEED_PLAN.json)
SEEDS32 = 42,7,123,13,2024,21,777,99,1001..1024. C0 = 8 seed dau. E4 nhom i = SEEDS32[4i:4i+4] (8 nhom roi). E8 nhom i = SEEDS32[8i:8i+8] (4 nhom roi;
nhom 1 = 42,7,123,13,2024,21,777,99). Job/fold (46, da khu trung): PROD x 32 seed x e0 ; PROD 42 x e1,e2,e3 ; DET(seed 42) x e0..e3 ; PROD E8g1 x e2 (42 trung).
Fold = cut 20211001..20251001 (17; 2021Q4 lam bo dem 90 ngay cho 2022Q1).

## Kernel (private, CPU, internet on de pip xgboost==3.2.0, dataset chuyendinh/gate-dataset-full; chi upload stab_train.py)
| slug | folds | trang thai luc roi |
| chuyendinh/p15-stab-a1 | 20211001,20220101,20231001,20240101,20251001 | running (push 15:03) |
| chuyendinh/p15-stab-a2 | 20220401,20230701,20240401,20250701 | running |
| chuyendinh/p15-stab-a3 | 20220701,20230401,20240701,20250401 | running |
| chuyendinh/p15-stab-a4 | 20221001,20230101,20241001,20250101 | running |
Kernel: md5 dataset assert a1c78e2f ; loc + assert ts < 2026-01-01 ; log xgboost version (WARNING neu != 3.2.0).

## Pha B lay output
~/.local/bin/kaggle kernels status chuyendinh/p15-stab-aN ; khi complete:
~/.local/bin/kaggle kernels output chuyendinh/p15-stab-aN -p ~/claude_master/w3/p15_stab/kout/aN
Dinh dang: out/f<cut>/ts_f<cut>.npy (int64 ms UTC, sorted, dedup keep last, OOS = [cut 00:00 +07, nextcut 00:00 +07)) ;
out/f<cut>/p15_f<cut>_<PROD|DET>_s<seed>_e<edge>.npy (float32, cung thu tu ts) ; out/jobs.jsonl (1 dong/job: train_rows, train_ts_max,
booster_sha256, secs, params thuc te, xgb version) ; out/stab_matrix.log ; f20251001/*.booster.json chi cho E8g1 e0 (k2).
Uoc dung luong ~ 0.53 MB/pred x 782 ~ 420 MB (< 1 GB) - pha B nen tai tung kernel, kiem du 46 file/fold.
Chuoi WFO cua 1 lan lap = ghep ts/pred cac fold 20211001..20251001 theo thu tu.

## Kiem parity Kaggle vs Oracle (pha B lam)
Oracle da co (out/f20250701, out/f20251001): PROD s42 e0, s7 e0, DET e0, PROD s42 e1 (20250701) ; 8 seed E8g1 e0 (20251001).
So pred cung ten tu kernel a2 (20250701) va a1 (20251001): pearson >= 0.9999 (k1 cho Kaggle) ; neu xgb Kaggle = 3.2.0 ky vong booster_sha256 trung (so jobs.jsonl).

## Sai lech so voi prereg / brief
1. Moi model KHONG xuat ONNX (stub onnxmltools trong runpy); booster va pred khong doi (k1 chung minh). ONNX chi xuat cho booster gop k2.
2. Pred tinh tu booster.predict(DMatrix float32) tren dong OOS dedup ts; khong luu 90 ngay rieng - bo dem lay tu quy truoc trong chuoi (fold 2021Q4).
3. DET chi chay seed 42 (khong ngau nhien con lai => seed vo nghia); DET cung patch random_state.
4. EDGE: bo dong ts trong [tr_cut - e ngay, tr_cut) bang cach loc DataFrame dua vao recipe (recipe nguyen byte).
5. Kernel cai xgboost==3.2.0 qua pip (khop Oracle) - phien ban thuc te xem log kernel.
6. 46 job/fold (brief noi ~47; seed 42 e2 trung giua ho EDGE C0 va E8g1).

## Viec con do cho pha B
- Theo doi 4 kernel ; neu error: doc log (kaggle kernels output), sua, push lai CHI fold thieu (script skip file da co chi trong cung thu muc).
- Du phong Oracle (duoi lock, ngoai gio R-LIVE): cd ~/claude_master/w3/p15_stab && flock -w 600 ~/claude_master/locks/oracle_heavy.lock nice -n 10
  python3 code/stab_train.py --mode matrix --folds <cut,...>   (~2.1 h cho ca 17 fold ; skip job da co).
- Kiem parity (tren), kiem du 782 file, roi tang S1 (chua lam).
