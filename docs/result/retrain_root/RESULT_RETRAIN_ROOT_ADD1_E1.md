# RESULT_RETRAIN_ROOT_ADD1_E1 - ADD1 (55b146c8) + ERRATA1 (591b3382): ca hai luot
Agent RUN, 2026-11-24 (+07). ERRATA1 sha256 562db2cbb48a31982a28568afddd12632d6a25b40cd5dd570f18bb07577246f5 (da xac nhan). Chi thong ke diem p15 <= 2026-09-30;
khong PnL/sim/kernel/242/nhan. Moi bo doc loc ts < 2026-10-01 00:00 +07 KHI DOC (dong 10-01 00:00 bi cat o buoc doc, khong in). KHONG ket luan thay MASTER.

## LUOT 1 (recipe G0) - INVALID, chi ghi lai (RESULT_RETRAIN_ROOT_ADD1.md sha256 f10468d7...)
- v1 0.98709 KHONG DAT ; v2 0.98710 KHONG DAT ; v3 1.1920 / 1.5087 DAT.
- So (INVALID, khong doc): E1 DEV 1.1310 / 0.9742, Vision 0.9916 / 0.9956 ; E2 A ca Q3 0.8275 / 1.0772, A 07-10..09-30 0.8639 / 1.2993, B 0.8491 / 1.2987 ; E3 R99995 64 cap 0.7989 / 1.0785 / 1.2434.

## LUOT 2 (recipe PROD) - HOP LE (v1' v2' v3 v4')
- Recipe PROD = vz_e1_wt/ml/gate/train_gate_fold.py md5 b41c9159 chay DUNG byte qua runpy nhu rt_p15_train.py: DATA gate_dataset_full.csv (a1c78e2f), CUTOFF, GATE_PURGE_MS=26100000
  (mep 00:00 +07 - 15'), random_state 42 hard-code. m0701 = booster T1 (sha256 71e82572), m0401 = ONNX fold_20 (md5 8ec99757), m0101 = PROD cut 20260101 (train 2629005 dong, max 2025-12-31 23:44:00+07).
- Store kiem truoc khi recipe doc ca file: 2 889 623 dong, 0 dong >= 2026-10-01 +07, max 2026-07-01 00:00 +07.

### Kiem hop le
| kiem | so | nguong | ket qua |
|---|---|---|---|
| v1' ONNX fold_20 tren gate A vs file live | pearson 1.0000000000, max|d| 1.5e-08 | >= 0,999 | DAT |
| v2' booster T1 tren gate A vs file T1 | pearson 1.0000000000, max|d| 2.2e-08 | >= 0,999 | DAT |
| v3 (T1 file)/(live file) Q3 | 1.19197 / 1.50869 | 1,192 / 1,509 +-0,002 | DAT |
| v4' PROD cut 0701 seed mac dinh vs booster T1 tren A | pearson 1.0000000000, max|d| 0.0e+00; booster sha256 TRUNG T1 (True); 2889607 dong, max 2026-06-30 23:44:00+07 | >= 0,9999 | DAT |

### E1' (2026Q2, LAG = m0101 PROD, WFO = m0401 fold_20; cung 131002 phut 2026-04-01 00:00:00+07..2026-06-30 23:59:00+07)
| nguon | R9999 | R99995 | Rmax | R9999 trong H [0,856;1,143] | R99995 trong H [0,858;1,127] |
|---|---|---|---|---|---|
| DEV | 0.9481 | 0.9343 | 1.0032 | True | True |
| Vision | 1.0199 | 1.0128 | 0.8598 | True | True |
- X_m = q(Vision)/q(DEV): m0101 q99,99 1.0859, q99,995 1.0773 ; m0401 q99,99 1.1682, q99,995 1.1679. pearson(Vision, DEV) cung model: m0101 0.5015, m0401 0.5048.
- O feature bang nhau (float32): 0.3620; dong bang ca 33 cot: 0.0000 (theo cot: JSON). DEV 131002 phut Q2, Vision 131040.
- Nhan (cach doc ADD1, ap co hoc): **S-NO**.

### E2' (2026Q3, LAG = m0401 fold_20, WFO = m0701 T1)
| tap | n | R9999 | R99995 | Rmax | trong H (9999/99995) | LODO R9999 min-max | LODO R99995 min-max |
|---|---|---|---|---|---|---|---|
| A_0710_0930 | 119520 | 1.2106 | 1.5428 | 1.5756 | False/False | 1.1402-1.2293 | 1.1293-1.5465 |
| B_0710_0930 | 119520 | 1.2134 | 1.4958 | 1.5756 | False/False | 1.1311-1.2285 | 1.1304-1.5051 |
| A_Q3_full | 132480 | 1.1920 | 1.5087 | 1.5756 | False/False | 1.1056-1.1990 | 1.1118-1.5125 |
| A_0701_0709 | 12960 | 1.0403 | 1.0506 | 1.0689 | True/True | 1.0140-1.0403 | 1.0527-1.0698 |
- So sanh chinh (Lam ro 1): A va B tren CUNG 119 520 phut 07-10..09-30. B NGOAI H ca 2 quantile => nhan (ap co hoc): **mapper KHONG giai thich**.
- A ca Q3 va A 07-01..07-09 chi mo ta. A ca Q3 tai lap 1,1920 / 1,5087 (= v3).

### E3' (8 seed recipe PROD cho cut 0401 va 0701, Q3 ban A) - LAM
- Seed: script khong co tham so seed (random_state=42 hard-code) => chen seed bang patch XGBRegressor.fit (set_params(random_state) ngay truoc fit), moi thu khac y nguyen
  (kiem get_params random_state == seed). 8 seed cho pred KHAC nhau (pearson voi seed 42: 0701 0,980-0,992 ; 0401 0,973-0,986) => LAM.
  W seed 42 = booster T1 (v4'); L seed 42 = PROD cut 0401 (mep +07) - KHONG phai fold_20 (fold_20 = WFOGateRunner cut UTC, purge 0).
- 64 cap R99995: min 0.6441 / median 0.9418 / max 2.0943 ; 1,509 TRONG dai (hang phan vi 92.2 %); ti le cap R99995 >= 1,509: 0.0781 (5/64).
- 64 cap R9999: min 0.7409 / median 0.9939 / max 1.3944 ; 1,192 TRONG dai (hang phan vi 82.8 %).
- Doc mo ta (ADD1): "trong nhieu seed tai 2026".

## Sai lech / gioi han
- E3' seed qua patch fit (script khong co tham so seed) - dien giai cua RUN cho '8 seed recipe PROD'; MASTER co the khong chap nhan.
- E1' DEV doc nhu recipe PROD (float64 -> float32), Vision doc nhu rt_chain (float32 truc tiep); ti le o bang nhau phan anh ca khac biet parse (neu co).
- E1' m0401 = fold_20 (cut 0401 UTC, purge 0) trong khi m0101 PROD dung mep +07 - 15' (theo ERRATA1).
- add1e1.log + add1e1.nohup la luot 2; khong in duoi file gate.

## Job nang (flock oracle_heavy.lock + nice 10)
- Luot 2: 13:35:05 -> 13:44:50 (+07), exit 0, wall 9:45, RSS 3,98 GB, 17 lan train PROD (~31 s/lan). Lock nha 13:44:50; khong thay run_rlive.

## sha256
- out/ADD1E1_result.json 90fbec257a22f326b909811180b4a7a5aa1d20cd66bb7ec6a34e23769ac9a0cc
- out/add1e1_preds.npz 41f98dac647db19cdd378ecad82f297409ebd2e8c3ed3680d831e458203dadd1
- out/ADD1_result.json 70779cb6f5059bef4954f1a4e8ffddfa9820784822ba21394bfd0d235ccfaf5e
- code/add1e1_run.py 1698afb5971f86cd02bd7731ceb0da5546083232740c119f3b8447c849826736
- RESULT_RETRAIN_ROOT_ADD1.md f10468d764c6b54c73202543e36d4d8a164c266f031bfac646bca0a573f1f013
