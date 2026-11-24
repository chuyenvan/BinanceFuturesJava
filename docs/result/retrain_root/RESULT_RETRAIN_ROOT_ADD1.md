# RESULT_RETRAIN_ROOT_ADD1 - muc 2 cua PREREG_RETRAIN_ROOT_ADD1 (v1-v3, E1, E2, E3)
Agent RUN, 2026-11-24 (+07). Prereg ADD1 commit 55b146c8, sha256 0cd7d7df6572b6563d4ff9f242481224d6f43b2c17cf8031cfd7bed645e2ad1a (da xac nhan).
Chi thong ke diem p15; khong PnL/ROI/so lenh/nhan/sim/kernel/242. Moi bo doc loc ts < 2026-10-01 00:00 +07 khi doc + assert. KHONG ket luan thay MASTER.

## TOM TAT HOP LE
- v1 KHONG DAT (pearson 0.98709 < 0,999). v2 KHONG DAT (pearson 0.98710 < 0,999). v3 DAT (1.1920 / 1.5087 vs 1,192 / 1,509, +-0,002).
- Theo ADD1 muc 2 ('mot kiem khong dat => phep do lien quan = INVALID'): E2 va E3 (dung m0401/m0701 suy luan tren gate Vision Q3) = **INVALID**.
  E1 dung m0401 (va m0101 cung recipe) suy luan tren gate Vision Q2 - CUNG doi tuong ma v1 kiem (model recipe G0 tren feature Vision) => RUN xep E1 = **INVALID**
  (rieng nhanh DEV cua E1 khong dung feature Vision; so lieu ghi duoi de MASTER quyet). Cac so duoi day da tinh xong theo thiet ke chot truoc, KHONG chinh cho khop;
  nhan co hoc ghi trong ngoac chi de minh bach, KHONG phai ket qua hop le.

## 0. Du lieu + model
- Gate Vision tai CHI file gate/* + MANIFEST tu output kernel (API list_kernel_session_output, dung loi goi cua `kaggle kernels output` 1.6.17 + loc file; khong chay kernel):
  ho4p1-x26-q2 gate.csv.gz md5 393fab08 sha256 998f8f95aeebe038007f1a187662365e26edabbc1e59a936ee9bc69def45f719 (md5 = MANIFEST kernel);
  ho4p1-x26-q3 (ban A) gate.csv.gz md5 f5448d82 sha256 27e7eef20e90283a128a825a8d2cfd5d975533296c220eaadf8b37c742faa9a5 (md5 = MANIFEST);
  ho4p1-dupfx gateB.csv.gz md5 e71bc77a sha256 f507beff95bf85c375984eeaf91931faa5a4956fd20115956725df3b67899b6b; gateA md5 cda89e1f sha256 c171c6fa8f7fb18cb52b2054429ad85a7c0e447b55ddd3b462e93723416b9b86.
  Tong ~80 MB trong k/. Doc gate = rt_chain.load_gate (cot theo TEN, thu tu V3FULL_TRAIN = V3FULL G0; loc [lo,hi) +07; drop_duplicates keep last; sort).
- Rows: Q3 A 132480 (2026-07-01 00:00..09-30 23:59 +07); B 119520 (CHI 2026-07-10 00:00..09-30 23:59 +07 - gateB khong co 07-01..07-09); Q2 Vision 131040; Q2 DEV 131002.
  Dong bi bo vi >= 2026-10-01 +07 khi doc: 1 dong (ts = 10-01 00:00 +07) o gate q3/gateA/gateB. Store DEV: 2 889 623 dong, max 2026-07-01 00:00 +07 (= 06-30 17:00 UTC).
  pred live 64f66a15 va T1 c1b00ba9: n 393 120, 2026-01-01 00:00..09-30 23:59 +07.
- Model recipe G0 (drv.py retrain): m0101 (ntr 2 629 425), m0401 (2 759 025), m0701 (2 889 623) seed 42; E3 them seed 7,123,13,2024,21,777,99 cho m0401/m0701. xgboost native predict.

## 1. Kiem hop le v1-v3
| kiem | dinh nghia | so | nguong | ket qua |
|---|---|---|---|---|
| v1 | pearson(m0401 tren A Q3, pred live 64f66a15 Q3) | 0.98709 (max|d| 0.0344, n 132480) | >= 0,999 | KHONG DAT |
| v2 | pearson(m0701 tren A Q3, pred T1 c1b00ba9 Q3) | 0.98710 (max|d| 0.0666) | >= 0,999 | KHONG DAT |
| v3 | q99,99 / q99,995 (T1 file)/(live file) Q3 | 1.19197 / 1.50869 (n 132480) | 1,192 / 1,509 +-0,002 | DAT |

Chan doan MO TA (khong thuoc ADD1, khong dung de doc; code/add1_diag_v12.py, out/ADD1_diag_v12.json) - chi suy luan model co san, khong train:
- ONNX fold_20 tren gate A (doc nhu tren) vs file live: pearson 1.0000000000, max|d| 1.5e-08; ONNX T1 vs file T1: 1.0000000000; booster.json T1 vs file T1: 1.0000000000.
  => cach doc gate + anh xa cot TAI LAP DUNG pred 2026 (0 NaN trong gate A). Lech nam o MODEL: m0701 (G0) vs booster T1 pearson 0.98710; m0401 (G0) vs ONNX fold_20 0.98709.
  Tuc model recipe G0 (drv.py: doc CSV float32 truc tiep, sort, loc nhan NaN) KHONG tuong duong model train_gate_fold (T1/fold_20) khi suy luan tren feature Vision 2026Q3,
  du A1 ghi 'cay trung' cho P15-A (P15-A la train_gate_fold lai, khong phai drv G0). Nguyen nhan cu the (vd parse float32 vs float64->float32): CHUA kiem.

## 2. E1 (2026Q2, LAG = m0101, WFO = m0401, cung 131002 phut 2026-04-01 00:00:00+07..2026-06-30 23:59:00+07) - INVALID (xem tren)
| nguon | R9999 | R99995 | Rmax | R9999 trong H [0,856;1,143] | R99995 trong H [0,858;1,127] |
|---|---|---|---|---|---|
| DEV | 1.1310 | 0.9742 | 0.9798 | True | True |
| Vision | 0.9916 | 0.9956 | 0.8828 | True | True |
- X_m = q(Vision)/q(DEV) cung model: m0101 q99,99 1.1720, q99,995 1.1332 ; m0401 q99,99 1.0276, q99,995 1.1582. pearson(Vision, DEV) cung model: m0101 0.5034, m0401 0.5090.
- Ti le o feature bang nhau (float32, 131002 phut x 33 cot): 0.3620 ; dong bang nhau ca 33 cot: 0.0000. Theo cot (xem JSON frac_equal_by_col).
  (DEV co 131002 phut Q2, Vision 131040; 38 phut chi co o Vision.)
- Nhan co hoc (KHONG hop le, khong dung): [S-NO]. Su kien khong phu thuoc feature Vision: R tren DEV nam TRONG H ca 2 quantile (R9999 1,1310 sat bien tren 1,143).

## 3. E2 (2026Q3, LAG = m0401, WFO = m0701) - INVALID (v1, v2)
| tap | n | R9999 | R99995 | Rmax | trong H (9999/99995) | LODO R9999 min-max | LODO R99995 min-max |
|---|---|---|---|---|---|---|---|
| A 2026-07-01..2026-09-30 | 132480 | 0.8275 | 1.0772 | 0.7579 | False/True | 0.8120-0.9132 | 0.8661-1.1034 |
| B 2026-07-10..2026-09-30 | 119520 | 0.8491 | 1.2987 | 0.7579 | False/False | 0.8070-0.8971 | 0.8609-1.2897 |
| A 0701_0709 | 12960 | 0.9272 | 0.9287 | 0.9338 | - | - | - |
| A 0710_0930 | 119520 | 0.8639 | 1.2993 | 0.7579 | - | - | - |
- B khong co 07-01..07-09 => tach 'truoc 07-10' tren B = khong co. dupfx gateA trung x26-q3 o 100 % o (119520 phut chung); B vs A cung phut: 0.6492 o bang nhau.
- Nhan co hoc (KHONG hop le, khong dung): [mapper KHONG giai thich] (A cung NGOAI H o R9999 nhung theo chieu THAP 0,827; T1/live that = 1,192/1,509 khong tai lap bang model G0).

## 4. E3 (8x8 seed, R99995 = q(m0701 seed i)/q(m0401 seed j), Q3 ban A) - INVALID (v1, v2)
- 64 cap: min 0.7989 / median 1.0785 / max 1.2434; 1,509 nam NGOAI (tren max), 0/64 cap >= 1,509. Mo ta R9999 64 cap: 0.7570 / 1.0630 / 1.5043.
- Nhan co hoc (KHONG hop le): [ngoai dai 64 cap].

## 5. Sai lech so voi ADD1 / gioi han
- Khong doi dinh nghia/nguong. Quy +07. Quantile numpy linear. H dung so lam tron cua ADD1 muc 1.
- gateB chi phu 07-10..09-30: R tren B tinh tren phan co (n 119 520), khong phai ca Q3 nhu A.
- E1 xep INVALID theo suy dien 'lien quan' cua RUN (v1 kiem dung loai suy luan E1 dung); MASTER co the doc khac.
- Errata: lan chay 1 (13:19-13:23) dung o TypeError trong ham doc pred (ghi de ten bien) TRUOC khi tinh thong ke nao; luu code/add1_run_try1.py, log/add1_try1.*; sua ten bien, chay lai.
- Luc kiem dau/cuoi file gate bang zcat|tail, man hinh hien 40 ky tu dau cua dong ts = 2026-10-01 00:00 +07 (ts + 2 gia tri feature); khong dung trong tinh toan. Bao de minh bach.
- add1.log chua ca lan 1 va lan 2 (FileHandler append); add1.nohup = lan 2.

## 6. Thoi gian job nang (flock oracle_heavy.lock + nice 10)
- Lan 1: 13:19:0x -> 13:23:55 (exit 1). Lan 2: 13:24:14 -> 13:29:07 (exit 0, wall 4:53, RSS 1,73 GB). Chan doan: nhe, khong lock (~10 s). Lock nha tu 13:29; khong thay run_rlive.

## 7. sha256
- out/ADD1_result.json 70779cb6f5059bef4954f1a4e8ffddfa9820784822ba21394bfd0d235ccfaf5e
- out/add1_preds.npz 29ef1628d168c613487515a390bef98f4d6eaccfab929bb8616eff7ccb0fc802
- out/ADD1_diag_v12.json 554ece6386027f09b6a2545b2b5cc0fe06a90b08e97a754c87ea75cb93760f84
- code/add1_run.py e7675c4deb3c741e6c4fa059378c08e865b5d8586c26740065c436810ddde256
- code/add1_run_try1.py 9e33d0965f5dd9f414ec07042dedbe7a7f102bb1d4ad563410492d7629dc199c
- code/add1_diag_v12.py 710f670915f920aa1bb2f14ee656196e18607acd36639ba69d333a61ea049819
- code/k_fetch.py 19a9f071e11e158302d03756f5239bd6c10c1246f59fc7a7e231b2502fc261a6
