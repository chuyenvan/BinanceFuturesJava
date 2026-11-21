# RESULT_RETRAIN_T1 - holdout tang kiem chung (3 model cut20260701) Lane N vs Lane L tren 2026Q3 - 2026-11-21
Prereg: docs/prereg/PREREG_RETRAIN_PILOT.md (c796c7b3) + ADD1 (c471c851) + ADD2 (a6ab4186) + ADD3 (2d5458ad) + ADD4 (6b41632c) + ADD5 (cb5e2d07).
HOLDOUT_UNSEAL_2026_1121 (e9095a02), pham vi U2. Audit doc lap: v12/A1_RETRAIN_T1.md (PASS-WITH-MINOR). Nhat ky: v12/RETRAIN_PILOT_RUN.{md,progress}.

## Phan quyet (luat muc 7, ap nguyen van)
- H-E0: mean SigmaPnL_Q3 Lane N = -10743.4 ; so seed > 0 = 0/8 => FAIL
- H-NI: mean d = -9.5640 pp, sd = 0.000224 pp, LB = -9.5642 pp (nguong >= -1,0) => FAIL
- H-DD: mean maxDD_Q3 Lane N = -7.450 % (nguong canh bao -22,72 %) => khong canh bao
- QUYET DINH (bang muc 7): H-E0 FAIL => PILOT tiep tuc BI CHAN (R2 HO5). DUNG. Khong tune, khong doi cutoff / seed / tham so, khong chay lai. Buoc 7 (T2) KHONG bat dau.

## Tuan thu
- Cong: 3a (P15-A, S1-A, NET-A, NET-B PASS; P15-B FAIL ghi nhan khong chan - ADD1 A1-1); K (ADD2), G-L 12/12 + S1-A lai (ADD3), NET-EQ, 3c/3d 3 model, P-N1, P-N2,
  kiem chung khong-PnL 8/8 (rt_nchk), selftest scorer L-vs-L d = 0 + thu pha A5-1 (thieu Update 0701 -> DUNG). jar_sec_check jar sim cc0f9d11: ok (khong key).
- Scorer: work/score/rt_score_n.py sha256 26c86069c0c5ba3bcca29440d884fe507f1b088dff99e7c619479bcacea8b059 (dinh nghia SCORE_DEFS_L5; ROI D5 = SigmaPnL_Q3 / E_start_Q3; assert A5-1).
- Khong doi gi sau khi thay so. Q3 = 2026-07-01..2026-09-30 (+07). E_start = dong Update 2026-07-01 07:00 (ca hai lane, moi seed - assert).

## Bang 8 seed (Q3)
| seed | lane | n | SigmaPnL_Q3 | E_start | ROI D5 % | ROI MTM % | maxDD % | Sharpe | % ngay co lenh |
|---|---|---|---|---|---|---|---|---|---|
| a1 | N | 164 | -10444.0 | 162110.0 | -6.4426 | -5.5431 | -7.450 | -3.21 | 18.5 |
| a1 | L | 110 | 5060.5 | 162110.0 | 3.1217 | 4.5093 | -1.480 | 3.63 | 10.9 |
| s123 | N | 164 | -10355.8 | 160737.0 | -6.4427 | -5.5432 | -7.451 | -3.21 | 18.5 |
| s123 | L | 110 | 5017.4 | 160737.0 | 3.1215 | 4.5092 | -1.481 | 3.63 | 10.9 |
| s13 | N | 164 | -11596.3 | 179996.0 | -6.4425 | -5.5435 | -7.451 | -3.21 | 18.5 |
| s13 | L | 110 | 5618.6 | 179996.0 | 3.1215 | 4.5090 | -1.481 | 3.63 | 10.9 |
| s2024 | N | 164 | -10276.4 | 159504.0 | -6.4427 | -5.5428 | -7.450 | -3.21 | 18.5 |
| s2024 | L | 110 | 4978.9 | 159504.0 | 3.1215 | 4.5096 | -1.480 | 3.63 | 10.9 |
| s21 | N | 164 | -10493.0 | 162870.0 | -6.4425 | -5.5431 | -7.450 | -3.21 | 18.5 |
| s21 | L | 110 | 5083.8 | 162870.0 | 3.1214 | 4.5097 | -1.480 | 3.63 | 10.9 |
| s7 | N | 164 | -9904.5 | 153736.0 | -6.4426 | -5.5426 | -7.450 | -3.21 | 18.5 |
| s7 | L | 110 | 4799.0 | 153736.0 | 3.1216 | 4.5097 | -1.480 | 3.63 | 10.9 |
| s777 | N | 164 | -11342.8 | 176066.0 | -6.4424 | -5.5428 | -7.450 | -3.21 | 18.5 |
| s777 | L | 110 | 5495.8 | 176066.0 | 3.1214 | 4.5097 | -1.480 | 3.63 | 10.9 |
| s99 | N | 164 | -11534.2 | 179041.0 | -6.4422 | -5.5429 | -7.450 | -3.21 | 18.5 |
| s99 | L | 110 | 5588.6 | 179041.0 | 3.1214 | 4.5090 | -1.481 | 3.63 | 10.9 |
| TB | N | 164.0 | -10743.4 | 166757.5 | -6.4425 | -5.5430 | -7.450 | -3.21 | 18.5 |
| TB | L | 110.0 | 5205.3 | 166757.5 | 3.1215 | 4.5094 | -1.480 | 3.63 | 10.9 |

## d(s) = 100 x (ROI_N - ROI_L) (D5, pp)
| seed | a1 | s123 | s13 | s2024 | s21 | s7 | s777 | s99 |
|---|---|---|---|---|---|---|---|---|
| d | -9.5642 | -9.5642 | -9.5640 | -9.5642 | -9.5640 | -9.5641 | -9.5638 | -9.5636 |
- mean -9.5640, sd 0.000224, LB -9.5642. Mo ta MTM: mean d -10.0524 pp, LB -10.0526.

## Mo ta (khong luat)
- Bootstrap tuan (10 000, rng 20261121) tong chuoi d trung binh 8 seed (pp): CI80 [-17.589, -1.653].
- Lenh trung (sym, start) trong Q3 N vs L (moi seed nhu nhau): N 164, L 110, chung 35.
- Theo thang / tach truoc-sau 07-10 (trung binh 8 seed; n = lenh co start trong cua so; SigmaPnL = pnl dong co end trong cua so; phut gate PASS: khong co
  theo cua so (log sim chi in tong) - tong n_pass ca giai doan: N 4027.9 vs L 3972.9, chenh N-L = 55 o moi seed, phat sinh tu Q3 vi 2 lane trung toi 06-30):
| cua so | n N | n L | SigmaPnL N | SigmaPnL L |
|---|---|---|---|---|
| 07 | 11.0 | 2.0 | -5602.3 | -4783.2 |
| 08 | 76.0 | 75.0 | -5860.6 | 6908.0 |
| 09 | 77.0 | 33.0 | 719.5 | 3080.5 |
| 0701-0709 | 4.0 | 2.0 | -6009.7 | -4783.2 |
| 0710-0930 | 160.0 | 108.0 | -4733.7 | 9988.6 |
- Luu y doc bang thang: SigmaPnL theo END nen thang 07 gom ca lenh mo tu Q2 dong trong thang 07 (chung 2 lane ve diem vao, khac ve thoat do model / gate).

## Gioi han dien giai (ADD5 A5-5, chep nguyen)
A5-5 [F5 a, b, d - gioi han dien giai, ghi vao bao cao ket qua] Lane N khac Lane L ngoai 3 model o: gate rolling tron ti so model cu / moi
     trong 90 ngay (khong reseed, P10); S1 T1 hoc 45,1 % dong tren feature Vision (cung nguon voi luc suy luan Q3) con S1 live chi hoc DEV;
     8 seed ~ 1 mau (ROI D5 Lane L 3,1214-3,1217 %). H-NI vi vay la so sanh DIEM, khong phai kiem dinh thong ke.
- Them: ROI D5 Lane L tren Q3 = 3,12 % (4,51 % la ROI MTM - ADD4).

## Manifest 3 model T1
- p15 T1: ONNX sha256 c9f13fc00571266b27307a1847d459a9c776cac4ebb8464d2a3999258c5b4cf3 (md5 3f840e4b), booster 71e82572...; 2 889 607 dong (DEV gate_dataset_full a1c78e2f,
  0 % Vision); max train ts 1782837840000; CUTOFF 20260701 + GATE_PURGE_MS 26100000 (mep +07, purge 15'); seed 42; xgb-env Py 3.10.12 / xgboost 3.2.0.
- net015 T1: model_f22_4h.json sha256 d91fe74181cd2c0c9e49098c21c45e3b5b94a7b9aa00aacb0a9ccea2a0c57901; ONNX sha256 29d9a79d5ad706fe3890a52651f6e10bd15360b9588a27ade44e19c52150d926;
  48 429 620 dong (DEV, 0 % Vision); max train ts 1782578700000; g015_net_train P14 / P14b NET-EQ trung byte; CPU seed 42; Kaggle Py 3.13 / xgboost 3.2.0.
- S1 T1: s1a2x1_cut20260701.json sha256 8bb11092dc20db6b4e70aaac29d7aa6293bb272640912e9aea9f008f2316ac88; .onnx sha256 18ed11a0d15050e20b49c6bd07314edfabcebe543d229cea904e0d62cff57c63;
  12 787 169 dong; max train ts 1782440100000; 45,1 % dong ts >= S0 (feature Vision); seed 42; python3 3.10.12 / xgboost 3.2.0.
- Lane N du lieu: dataset rt-n-data26 (pred_2026 a574a2e9; bins 0101 b58099f4 / 0401 78e4e437 = L, 0701 bb64cde3); 8 kernel sim-rt-n-l26-<seed> (jar cc0f9d11 stub).

## Duong dan + sha256
- ~/claude_master/w3/retrain/out/score/score_n_laneN.json sha256 1ab0a6de6eba1d13ae911444690ef0c507e88e58bb21bb015520274bf6fa2f66
- ~/claude_master/w3/retrain/out/score/score_n_selftest_LvsL.json sha256 eb472ba2a48eff8d6e51e5a2b4eacc802d12635244aa77059b5cf24b1788bfbb
- ~/claude_master/w3/retrain/out/nsim/check_summary.txt sha256 e878d95512bbad72c2cb3893f796af9685752168ea1bb71b699dffdf09e75f68
- ~/claude_master/w3/retrain/out/jar_sec_check_cc0f9d11.json sha256 c38bfc1ab23dffa5e2f3acd875afc86f1a17489db00d1290e129f60a6e666e39
- ~/claude_master/w3/retrain/work/score/rt_score_n.v1_v2.diff sha256 4820c807e7f1a57c02cc35c7475c3937ea04befea7eb27f7bd326326ba260549
- Log cham: ~/claude_master/w3/retrain/out/score/score_laneN.log; thu pha: out/score/brk/brk.log; output sim chon loc: out/nsim/rt-n-l26-<seed>/.
