# RESULT_RETRAIN_ROOT_T1 - Tang 1 (M1 + M3=F_k, M5, M2) cua PREREG_RETRAIN_ROOT
Agent RUN, 2026-11-24 (+07). Prereg: ~/claude_master/vz_e1_wt/docs/prereg/PREREG_RETRAIN_ROOT.md commit 899f2fc8, sha256 6ae0720e4ddfaefbf3bf8aa2b8662556e7e42f6884d3bdd2e612c1e7a9a3c34e (da xac nhan).
Chi du lieu DEV ts < 2026-01-01 00:00 UTC (loc + assert khi doc). Khong sim, khong Kaggle, khong mvn/java, khong 242, khong PnL moi. KHONG ket luan CASE A/B/C (MASTER sau audit).

## 0. Recipe + du lieu
- Recipe G0 = ~/claude_master/1004/gabl/drv.py `retrain G0` (= gate_ablation_driver.py, ham retrain giong het): V3FULL 33 feat, label_oldbasket, purge 15', seed 42,
  XGBRegressor(reg:squarederror, max_depth 4, n_estimators 150, lr 0.05, subsample 0.8, colsample_bytree 0.8, min_child_weight 10, n_jobs 4);
  train ts < cut_UTC - 15' (expanding tu 2021-01-01); OOS fold k = [cut_k, cut_k+3M) theo +07 (WFOGateRunner = mep cua pred.bin A1). xgboost 3.2.0 (xgb-env).
- File: ~/claude_master/gvz/store/gate_dataset_full.csv md5 a1c78e2f, sha256 4094424d4d981c13... G0 goc doc ~/claudedata/gate_dataset_full.csv.gz md5 4bde28cd (DA MAT).
  Tai lap: 19/19 fold pearson(WFO, pred.bin A1) TRUNG TUNG CHU SO voi retrain_G0.json (min 0,99191 fold 5; vd fold 18 0,99204) => cung du lieu + cung recipe.
- Nap: store doc 2 889 623 dong theo chunk, bo 260 183 dong ts >= 2026-01-01 UTC ngay khi doc; nap 2 629 440 dong, min ts 2021-01-01 00:00 UTC, max ts 2025-12-31 23:59 UTC (assert < 2026-01-01 UTC dat).
  pred.bin A1 2 500 260 dong, max 2025-12-31 23:59 UTC (0 dong >= 2026 UTC).
- QUY UOC QUY: Q_k = [cut_k, cut_{k+1}) theo +07 (Asia/Ho_Chi_Minh), dung mep OOS cua pred.bin A1/G0; Q_18 = [2025-10-01, 2026-01-01) +07. WFO_k va LAG_k tinh tren CUNG
  tap dong (cac phut cua pred.bin trong Q_k, 0 dong thieu feature). 7h cuoi 2025-12-31 UTC (= 2026-01-01 +07) nap vao nhung khong thuoc quy nao => khong dung.
  Ghi chu: cut train theo UTC con OOS theo +07 => fold k da thay ~6h45' dau Q_k khi train (y nguyen G0/pred.bin). Do nhay MO TA (khong thuoc prereg, khong dung de doc):
  bo 7h dau moi quy -> R9999 [0,8570; 1,1424], R99995 [0,8579; 1,1267], dau +7/-11 (khong doi ket luan). code/m1_sens_7h.py, log/m1_sens_7h.log.

## 1. M1 (+ M3 = F_k) - p15 WFO vs LAG theo quy, KHONG PnL
Hop le: pearson(WFO_k, pred.bin A1) >= 0,99 o 18/18 quy (min 0,99191 2022Q3) -> 0 quy bi loai, M1 HOP LE, N = 18. (fold 0 / 2021Q2, chi dung lam LAG_1: 0,99454.)

| k | quy | n | pearson | R9999 | R99995 | Rmax | dp50 | F_k | frac>=.008 WFO | LAG |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2021Q3 | 132480 | 0.99414 | 0.8562 | 0.9089 | 0.9660 | -0.000990 | 0.4233 | 0.0541 | 0.1277 |
| 2 | 2021Q4 | 132480 | 0.99701 | 1.1044 | 0.8577 | 0.8751 | +0.000374 | 1.1650 | 0.0503 | 0.0431 |
| 3 | 2022Q1 | 129600 | 0.99520 | 0.9610 | 0.9153 | 1.0559 | +0.000173 | 1.2257 | 0.1066 | 0.0870 |
| 4 | 2022Q2 | 131040 | 0.99710 | 1.1187 | 1.1268 | 1.3103 | -0.000883 | 0.8124 | 0.1499 | 0.1845 |
| 5 | 2022Q3 | 132480 | 0.99191 | 1.1429 | 0.9910 | 1.0042 | +0.000056 | 1.1140 | 0.0247 | 0.0222 |
| 6 | 2022Q4 | 132480 | 0.99494 | 0.9676 | 0.9611 | 0.9674 | -0.000708 | 0.8746 | 0.0477 | 0.0545 |
| 7 | 2023Q1 | 129600 | 0.99710 | 1.0156 | 0.9194 | 0.9482 | -0.000043 | 0.9811 | 0.0257 | 0.0262 |
| 8 | 2023Q2 | 131040 | 0.99752 | 0.9738 | 1.0473 | 0.8546 | -0.000001 | 1.1429 | 0.0085 | 0.0075 |
| 9 | 2023Q3 | 132480 | 0.99807 | 1.1021 | 0.9240 | 0.8645 | -0.000039 | 0.9414 | 0.0047 | 0.0050 |
| 10 | 2023Q4 | 132480 | 0.99864 | 0.9708 | 0.9634 | 1.1700 | -0.000037 | 0.9806 | 0.0156 | 0.0159 |
| 11 | 2024Q1 | 131040 | 0.99658 | 1.0002 | 1.0061 | 0.8999 | +0.000122 | 1.0162 | 0.0879 | 0.0865 |
| 12 | 2024Q2 | 131040 | 0.99763 | 1.0465 | 1.0743 | 1.0313 | +0.000009 | 1.0637 | 0.0372 | 0.0350 |
| 13 | 2024Q3 | 132480 | 0.99869 | 0.9792 | 0.9518 | 0.9461 | +0.000004 | 1.0528 | 0.0317 | 0.0302 |
| 14 | 2024Q4 | 132480 | 0.99818 | 0.9458 | 0.9766 | 0.9342 | -0.000024 | 0.9699 | 0.0866 | 0.0893 |
| 15 | 2025Q1 | 129600 | 0.99596 | 0.9687 | 1.0102 | 0.9853 | +0.000211 | 1.1705 | 0.1249 | 0.1067 |
| 16 | 2025Q2 | 131040 | 0.99673 | 0.9628 | 0.9668 | 0.8041 | +0.000360 | 1.5022 | 0.1624 | 0.1081 |
| 17 | 2025Q3 | 132480 | 0.99778 | 0.9360 | 0.9740 | 0.9755 | +0.000127 | 1.4094 | 0.2261 | 0.1604 |
| 18 | 2025Q4 | 132480 | 0.99204 | 0.9139 | 0.9290 | 1.0256 | +0.000617 | 1.2523 | 0.7642 | 0.6102 |

Tom tat (N=18): R9999 min/median/max 0.8562 / 0.9723 / 1.1429 ; R99995 0.8577 / 0.9651 / 1.1268 ; Rmax 0.8041 / 0.9667 / 1.3103 ; dp50 -0.000990 / 0.000006 / 0.000617.
Cach doc ghi truoc:
- 1,192 trong [0.8562; 1.1429] cua R9999? KHONG. 1,509 trong [0.8577; 1.1268] cua R99995? KHONG. => nhan: **ANOMALOUS** (CA HAI chi so nam NGOAI, tren max: R9999 va R99995).
- Sign test log R9999: 7 quy > 0, 11 quy < 0 (max cung dau 11/18 < 14) => **khong co huong** (p hai phia nhi thuc 0.481, chi tham khao).
- F_k (M3, mo ta): min 0.4233 (2021Q3) / median 1.0582 / max 1.5022 (2025Q2); so quy |log F_k| > log 1,5: 2 (2021Q3 0,4233; 2025Q2 1,5022).

## 2. M5 - nhieu doi-seed p15 tren PnL DEV da co (8 seed r1-a3), khong sim moi
- Cong thuc D5 ap NGUYEN VEN: ROI_D5 = sum_pnl(lenh end trong quy) / E_start (dong 'Update <ngay dau quy> 07:00' b+unP), qua ham rows/updates/metr IMPORT tu
  ~/claude_master/w3/ho5/l5/score_l5.py (sha256 da34f318...) nhu rt_score_n.lane(); kiem A5-1 d_start == ngay dau quy: dat 18/18 quy x 8 seed. Quy lich +07 (2021Q3..2025Q4).
  Loc printDone (start, end < 2026-01-01) + Update < 20260101, assert dat (khong co dong nao bi loc: DEV ket thuc 2025-12-30, lenh cuoi end 2025-11-28).
- Phan phoi rong: |ROI_i - ROI_j| (pp), 28 cap x 18 quy = 504 gia tri: p50 0.990, p90 2.866, **p95 3.8948**, p99 11.085, max 13.408.
- Doc ghi truoc: |d_P| = 3,508 <= p95 3.8948 => **"lane P khong phan biet duoc voi nhieu doi-seed p15"** (hang phan vi 93.8 %; sat bien).
- d_N = 9,564 pp (CHI MO TA): hang phan vi 98.6 % cua phan phoi rong (> p95).
- Theo quy (pp): khoang ROI 8 seed / p95 cap:
  2021Q3: [12.19; 14.08] range 1.90, p95 cap 1.59
  2021Q4: [3.92; 5.48] range 1.57, p95 cap 1.08
  2022Q1: [5.22; 7.56] range 2.34, p95 cap 1.62
  2022Q2: [-6.74; 6.67] range 13.41, p95 cap 12.10
  2022Q3: [6.03; 8.73] range 2.70, p95 cap 2.59
  2022Q4: [-3.76; -1.00] range 2.76, p95 cap 2.48
  2023Q1: [10.77; 14.03] range 3.27, p95 cap 2.96
  2023Q2: [16.58; 22.18] range 5.60, p95 cap 5.07
  2023Q3: [8.53; 11.15] range 2.62, p95 cap 2.38
  2023Q4: [16.53; 19.17] range 2.63, p95 cap 2.34
  2024Q1: [10.75; 16.40] range 5.65, p95 cap 4.90
  2024Q2: [1.25; 3.43] range 2.17, p95 cap 1.74
  2024Q3: [4.09; 7.76] range 3.67, p95 cap 3.43
  2024Q4: [16.49; 20.40] range 3.91, p95 cap 3.55
  2025Q1: [9.31; 14.33] range 5.02, p95 cap 4.21
  2025Q2: [3.09; 5.24] range 2.15, p95 cap 1.86
  2025Q3: [-1.55; 1.29] range 2.84, p95 cap 2.45
  2025Q4: [10.98; 13.94] range 2.96, p95 cap 2.55
  Luu y mo ta: phan phoi rong bi keo boi 2022Q2 (range 13,41 pp); bo qua quy nay thi p95 se thap hon - KHONG ap dung (prereg gop moi quy).

## 3. M2 - replay gate offline (khong PnL)
- Cong cu: research/analysis/gate_offline.py (sha256 f0c6a0a6...) + gate_skipfull_offline.full_mask (9f926e07...), trung byte voi ~/src, KHONG sua.
  Chi tro: bins = 18 file cua r1-a3 (16 A3, sha concat 0d6e3781 == result.json r1_a3.bins_sha256; + 2 file 2021 ~/kaggle_sim/s3moc21), printDone/sim.out/full.log = r1-a3-a1,
  pred = pred.bin A1, GATE_QUOTA_SKIP_WHEN_FULL=true -> full_mask (U >= 0,60). Thiet ke chot va ghi RUN.progress TRUOC khi chay.
  Errata cong cu: lan chay 1 dung o assert sha bins (sap xep file theo duong dan day du) TRUOC khi tinh bat ky so nao; sua key=basename, khong doi logic.
- Kiem hop le (vs GATE-RATIO r1-a3-a1, +-10 %): dat 16/18 quy, 14/16 tu 2022Q1 => **HOP LE**. Tong replay 3312 vs log 3311. full_mask = 0 phut (sim log skipFull=58).

| quy | replay | log | ti so | ok |
|---|---|---|---|---|
| 2021Q3 | 383 | 383 | 1.000 | ok |
| 2021Q4 | 197 | 182 | 1.082 | ok |
| 2022Q1 | 89 | 103 | 0.864 | LECH |
| 2022Q2 | 257 | 249 | 1.032 | ok |
| 2022Q3 | 47 | 53 | 0.887 | LECH |
| 2022Q4 | 100 | 100 | 1.000 | ok |
| 2023Q1 | 166 | 166 | 1.000 | ok |
| 2023Q2 | 170 | 173 | 0.983 | ok |
| 2023Q3 | 97 | 96 | 1.010 | ok |
| 2023Q4 | 259 | 259 | 1.000 | ok |
| 2024Q1 | 291 | 291 | 1.000 | ok |
| 2024Q2 | 162 | 162 | 1.000 | ok |
| 2024Q3 | 116 | 116 | 1.000 | ok |
| 2024Q4 | 259 | 259 | 1.000 | ok |
| 2025Q1 | 296 | 296 | 1.000 | ok |
| 2025Q2 | 68 | 68 | 1.000 | ok |
| 2025Q3 | 80 | 80 | 1.000 | ok |
| 2025Q4 | 275 | 275 | 1.000 | ok |

- PI_k = pass(WFO_k)/pass(LAG_k) tren Q_k; chuoi p15 = WFO cua M1 truoc ranh gioi (bo dem), LAG_k (M1) trong Q_k; lock/full lay tu run a1 (khong phan hoi duong di);
  mien con [lo_k - 92 ngay, hi_k). 30-ngay: [0,30), [30,60), [60, het quy).

| quy | pass WFO | pass LAG | PI_k | WFO 30d | LAG 30d | vuot LAG-WFO 30d |
|---|---|---|---|---|---|---|
| 2021Q3 | 336 | 369 | 0.9106 | [76, 60, 200] | [64, 71, 234] | [-12, 11, 34] |
| 2021Q4 | 230 | 296 | 0.7770 | [50, 110, 70] | [40, 193, 63] | [-10, 83, -7] |
| 2022Q1 | 94 | 144 | 0.6528 | [70, 24, 0] | [141, 3, 0] | [71, -21, 0] |
| 2022Q2 | 274 | 301 | 0.9103 | [0, 220, 54] | [2, 240, 59] | [2, 20, 5] |
| 2022Q3 | 45 | 46 | 0.9783 | [25, 20, 0] | [25, 20, 1] | [0, 0, 1] |
| 2022Q4 | 175 | 304 | 0.5757 | [0, 175, 0] | [0, 304, 0] | [0, 129, 0] |
| 2023Q1 | 128 | 119 | 1.0756 | [24, 50, 54] | [33, 52, 34] | [9, 2, -20] |
| 2023Q2 | 208 | 262 | 0.7939 | [82, 14, 112] | [110, 33, 119] | [28, 19, 7] |
| 2023Q3 | 95 | 55 | 1.7273 | [42, 29, 24] | [8, 23, 24] | [-34, -6, 0] |
| 2023Q4 | 269 | 297 | 0.9057 | [94, 68, 107] | [120, 74, 103] | [26, 6, -4] |
| 2024Q1 | 271 | 284 | 0.9542 | [62, 47, 162] | [40, 69, 175] | [-22, 22, 13] |
| 2024Q2 | 157 | 178 | 0.8820 | [128, 0, 29] | [135, 0, 43] | [7, 0, 14] |
| 2024Q3 | 114 | 98 | 1.1633 | [45, 45, 24] | [24, 51, 23] | [-21, 6, -1] |
| 2024Q4 | 279 | 326 | 0.8558 | [22, 111, 146] | [20, 97, 209] | [-2, -14, 63] |
| 2025Q1 | 315 | 301 | 1.0465 | [97, 123, 95] | [74, 116, 111] | [-23, -7, 16] |
| 2025Q2 | 64 | 59 | 1.0847 | [30, 6, 28] | [12, 39, 8] | [-18, 33, -20] |
| 2025Q3 | 77 | 81 | 0.9506 | [3, 29, 45] | [1, 29, 51] | [-2, 0, 6] |
| 2025Q4 | 259 | 254 | 1.0197 | [210, 49, 0] | [207, 47, 0] | [-3, -2, 0] |

- PI_k min / median / max = 0.5757 / 0.9306 / 1.7273 (N=18). Doc ghi truoc: 1,35 trong [min, max] => **TYPICAL ve gate**.
  Mo ta: median < 1 (LAG thuong pass NHIEU hon WFO); 1,35 chi bi vuot o 1 quy (2023Q3 1,727). pass WFO(M1) khac pass replay A1 (vd 2021Q3 336 vs 383) vi WFO M1 != A1 bit-exact.

## 4. Sai lech so voi prereg / gioi han
- Khong co sai lech dinh nghia/nguong. Quyet dinh thuc thi (ghi ro): (a) quy theo +07 (mep pred.bin/G0), cung tap dong cho WFO/LAG; (b) quantile = numpy linear;
  (c) M2 dung full_mask U-xap-xi (cho ra 0 phut full; sim co skipFull=58) va lock/duong di cua run a1 cho ca WFO lan LAG; (d) M2 dung WFO/LAG cua M1 (khong phai A1) cho PI.
- File G0 goc (.csv.gz 4bde28cd) mat; dung csv a1c78e2f - tai lap pearson trung G0 tung fold nen coi la cung noi dung (chua so byte).
- 2 file bins 2021 (s3moc21) khong co sha doi chieu trong result.json (chi 16 file A3 co); 2021Q3 replay khop log 383/383.
- M5: seed DEV chi doi p15 => phan phoi rong la nhieu doi-seed p15 + duong di, khong gom nhieu net015/S1 hay khac biet du lieu/tuoi model.

## 5. Thoi gian job nang (flock oracle_heavy.lock + nice 10, khong long)
- M1: 12:47:29 -> 12:50:16 (+07), exit 0, wall 2:37, RSS 1,66 GB. M2 lan 1: ~12:54:30, dung sau 1 s (assert). M2 lan 2: 12:55:3x -> 12:56:14, exit 0, RSS 2,89 GB.
- M5 + do nhay 7h: nhe (khong lock). Lock da nha tu 12:56; khong thay run_rlive. Ghi dia ~111 MB.

## 6. sha256 file ket qua
- out/M1_result.json b1a1f5163105ebdbabaae02263738d0c55d7bee93cd0abbe00e331547690aa60
- out/M1_table.tsv 01e195dc8b9e5d611db79fc390bf8210f52f4aab0126fb8d0100a61b58585607
- out/m1_wfo.npy a3035caa259312801be30c4f6381d1dd50afbefec426c5955ab19d6281ab51fb
- out/m1_lag.npy 36852185700b04e0de4104c6e2b4753caa9708490d673ecd5a562935f6fd1eae
- out/m1_ts.npy 6a686be59f3f83e4692a8c860eda29f68af7f5f0a52c1e0ed7e0a81243991261
- out/M5_result.json 3bd22fbda21a55e2943e862a6247facdbffaec0ac60e6a28ef0771990697fc64
- out/M2_result.json 56261f99dece10355cda2121258988f855078b6e0513e23f50b1be3add0b7192
- code/m1_train_pred.py 42322732dbcb44c02d7f20506827d17616d5f872d0a0300299b7658158127e4d
- code/m5_seed_noise.py 7bed89847e0c709fe50bac14a070961896e0c6ce5d31cdf4bbc35a80d1c8406c
- code/m2_gate_replay.py 11886878491ed371d97afdbdcffb15419670b93f43109ffb96f63fae33ee8ffa
- code/m1_sens_7h.py 86850fde462f47e3cb2db27ed18780e751c092cc6ffcad08bb597581af5d5be0
