# RESULT_GRIDV2_S3 - ket qua chay that giai doan S3 WICK (12 o x 2 mo hinh khop)

(ASCII khong dau tren may chu; bao cao tieng Viet co dau do agent tra ve cho MASTER.)

## 1. Tuan thu
- Prereg: PREREG_GRIDV2_S3.md commit 1c748473 (doc toan bo, ke ca muc 19). C0: dong TRIALS_GRID.csv da them truoc khi chay (24 trial, luy ke 98).
- Code ghim: sha256(EXPECTED_SHA.txt) = 2891b42d456cb5099ff784137ecb5064fc594cce654d9d644aec6d2db9fc399a (khop); sha256sum -c 5/5 OK ca o s3/ (thu muc merge) lan vz_e1_wt/research/gridv2_s3.
  klite3 09bb18eb..., kref3 6b02dea6..., stats 975f3a42..., stats3_extra a9f9857f..., runner3_kaggle 7cb71c9b...
- C2 layout (muc 19c): 7 dataset allowlist liet ke bang kaggle datasets files (s3run/dataset_files.txt): tat ca parquet o PHANG ngay duoi dataset, khong thu muc con, khong ten file chua 2026.
  Non-parquet: README.md (5 dataset kline) + anomalies.csv (vz-kline1m-2023); runner allowlist chi parquet -> bo qua, khong abort. kline 2021-2025 = 12 thang moi nam; funding-2021..2025; lifecycle.parquet 1 file.
- Kernel: 5 kernel private gridv2-s3-shard0..4 (chuyendinh/), mount DUNG 7 dataset, internet tat, GPU tat; wrapper chi ghi code base64 + kiem sha + goi runner3_kaggle.py run voi GRIDV3_SHARD=i/5 (build_kernels_s3.py). Khong env khac.
  Push shard0 ~21:40Z (gio Oracle 2026-11-20), shard1-4 ~21:42Z, tat ca complete <= 22:04Z. Thoi gian chay runner (manifest.seconds): 1287 / 1256 / 1322 / 1216 / 1334 s. Tong ~6 415 s runner (~1,8 kernel-gio).
- So lan chay lai: 0 (khong loi ky thuat, khong sua wrapper/metadata).
- Output tai ve d0..d4 (1,7-1,9 MB / shard): reduced/, validate.json, manifest.json, run.log. Disk Oracle 18 GB trong (92%) truoc va sau.
- manifest: prereg_constants True ca 5; sha code == EXPECTED ca 5; test_overrides {}; cond B ratio 1.5, MKT z 1.0 win 60; mkt_sym BTCUSDT; n_sym 128/118/120/123/141 (tong 630).
- Quy tac su co: M/PnL chi doc SAU khi 5 shard V0-V6 ALL PASS.

### V0-V6 tung shard (ALL PASS 5/5; all_pass True)
shard | V0a | V0b | V1 | V2 (max_bad_frac) | V3 long_gaps / excl_gap / noend / feat_mismatch_days / skip_px | V4 (n_checks, skipped) | V5 (n_checked, fallback, uncovered, covered, fb_unused_bad) | V6
0 | PASS | PASS | PASS | PASS (0.0) | 194 / 2056 / 4 / 0 / 1152 | PASS (2, -) | PASS (12, 0, 0, 12/12, 0) | PASS
1 | PASS | PASS | PASS | PASS (0.0) | 180 / 1804 / 2 / 0 / 32 | PASS (2, -) | PASS (12, 0, 0, 12/12, 0) | PASS
2 | PASS | PASS | PASS | PASS (0.0) | 179 / 1898 / 0 / 0 / 0 | PASS (2, -) | PASS (12, 0, 0, 12/12, 0) | PASS
3 | PASS | PASS | PASS | PASS (0.0) | 184 / 1854 / 0 / 0 / 1104 | PASS (2, -) | PASS (12, 0, 0, 12/12, 0) | PASS
4 | PASS | PASS | PASS | PASS (0.0) | 208 / 1962 / 0 / 0 / 0 | PASS (2, v4_skipped 1000BTTCUSDT span 75.2 ngay < 90) | PASS (12, 0, 0, 12/12, 0) | PASS
- V0b files_skipped (ca 5 shard giong nhau): kline1m-2021-01 (3 645 000 dong), -02 (3 561 270), -03 (4 386 539) = dung tap prereg.
- V1: ts_min 1617235200000 (2021-04-01) .. ts_max 1767225540000 (2025-12-31 23:59) ca 5 shard; khong dong >= 2026.
- V5: v5_fallback rong, uncovered rong, 12/12 (c,T,ben) phu o MOI shard; checks_fallback_unused 0.
### (H1)(H1')(H2)
(H1) sha256sum EXPECTED_SHA.txt = 2891b42d456cb5099ff784137ecb5064fc594cce654d9d644aec6d2db9fc399a
(H1') trong ~/claude_master/w3/gridv2/s3: klite3.py: OK / kref3.py: OK / stats.py: OK / stats3_extra.py: OK / runner3_kaggle.py: OK
(H2) manifest.inputs giong het 5 shard (script xac nhan): lifecycle 1f21f7df47dd7f6c8965267a0d95979c9f66e20282fe6800ad331ed31a9159d2; funding-2021 51386684..., 2022 d1c4edcc..., 2023 5498ebd6..., 2024 93642c59..., 2025 ff69f933...
Merge: flock + nice, khong abort, log rong (merge.log 0 dong); merge tu kiem sha code OK.

## 2. Luat
rule (runner, ALPHA_FWER 0,04) = W-B ; rule_core = W-B
PASS runner: OPT=[] PESS=[]
PASS CHINH THUC (runner PASS va p_RW nua B <= 0,03, muc 19a): K_OPT3=[] K_PESS=[]
W-A tay (12 o K_OPT3 nua B khong INSUFFICIENT va can tren dong thoi 95% huu han < 4): False ; o khong thoa: BUY_c1.0_T240(ins=False,upper=86.9), BUY_c1.0_T1440(ins=False,upper=142.6), BUY_c1.5_T240(ins=False,upper=236.2), BUY_c1.5_T1440(ins=False,upper=293.2), BUY_c2.5_T240(ins=False,upper=490.6), BUY_c2.5_T1440(ins=False,upper=550.7), SELL_c1.0_T240(ins=False,upper=9.3), SELL_c1.0_T1440(ins=False,upper=14.4), SELL_c1.5_T240(ins=False,upper=49.1), SELL_c1.5_T1440(ins=False,upper=75.9), SELL_c2.5_T240(ins=False,upper=140.7), SELL_c2.5_T1440(ins=False,upper=178.7)
LUAT CHINH THUC (tinh tay, thu tu W-D > W-C > W-A > W-B) = W-B ; runner = W-B ; TRUNG
W_A_condition_OPT_B (runner) = False ; W_A_blocked_by_insufficient_OPT = []
SELL_PASS_note: {'OPT': [], 'PESS': []}

## 3. Bang 12 o x 2 mo hinh x 2 nua
Cot: n_dat (n_place) / n_khop (n_units); P(khop)=fill_rate; M; M_neth (tru beta BTC); SE; t; p (A: p_marg, B: p_RW); up95 = can tren dong thoi 95% (upper_sim95); M_adj (C4); M-top3coin; M-3sk; M-khoi(e') + ngay; M-cuaso(e'') + ngay; M_stress_x5 (K_PESS); INSUFF.

### K_PESS nua A (D=914, 46 khoi, seed 2026112150)
cell | n_dat | n_khop | P(khop)% | M | M_neth | SE | t | p | up95 | ci95_hi | M_adj | M-top3 | M-3sk | M-khoi(e') | khoi_start | M-cuaso(e'') | cuaso_start | stress5 | INSUFF
BUY_c1.0_T240 | 3271852 | 24380 | 0.745 | 29.2 | 31.8 | 16.5 | 1.52 | 0.1035 | 73.2 | 59.9 | 26.9 | 27.8 | 31.7 | 25.1 | 2023-10-19 | 25.1 | 2023-10-19 | 16.6 | no
BUY_c1.0_T1440 | 3271852 | 24374 | 0.745 | 30.9 | 49.7 | 21.8 | 1.24 | 0.1695 | 88.9 | 71.0 | 28.4 | 29.0 | 49.4 | 25.3 | 2023-10-19 | 24.0 | 2023-10-24 | 24.0 | no
BUY_c1.5_T240 | 3271852 | 8407 | 0.257 | 84.3 | 77.2 | 31.3 | 2.56 | 0.0275 | 167.7 | 140.8 | 82.1 | 82.0 | 84.2 | 74.6 | 2022-04-27 | 74.6 | 2022-04-27 | 70.6 | no
BUY_c1.5_T1440 | 3271852 | 8406 | 0.257 | 81.3 | 102.3 | 37.0 | 2.09 | 0.0700 | 179.8 | 151.1 | 79.0 | 78.8 | 104.8 | 74.3 | 2023-11-08 | 72.9 | 2023-10-24 | 72.3 | no
BUY_c2.5_T240 | 3271836 | 2649 | 0.081 | 253.3 | 216.7 | 69.7 | 3.58 | 0.0060 | 439.1 | 397.6 | 251.3 | 248.9 | 224.9 | 225.4 | 2022-04-27 | 225.4 | 2022-04-24 | 238.9 | no
BUY_c2.5_T1440 | 3271836 | 2649 | 0.081 | 274.9 | 261.7 | 62.2 | 4.36 | 0.0010 | 440.7 | 419.0 | 272.7 | 272.5 | 264.2 | 247.8 | 2022-04-27 | 247.8 | 2022-04-24 | 265.1 | no
SELL_c1.0_T240 | 3271852 | 20651 | 0.631 | -7.2 | -10.9 | 7.8 | -1.43 | 0.9210 | 13.7 | 8.6 | -9.6 | -9.2 | -13.4 | -10.3 | 2022-04-27 | -11.7 | 2022-04-23 | -19.4 | no
SELL_c1.0_T1440 | 3271852 | 20650 | 0.631 | 8.4 | 1.7 | 11.3 | 0.39 | 0.3270 | 38.6 | 33.0 | 5.8 | 5.8 | -1.2 | 2.6 | 2022-04-27 | 1.4 | 2022-04-23 | 1.9 | no
SELL_c1.5_T240 | 3271852 | 6922 | 0.212 | -3.9 | -5.3 | 16.4 | -0.48 | 0.6895 | 39.7 | 24.4 | -6.4 | -8.9 | -15.9 | -10.7 | 2022-04-27 | -11.0 | 2022-05-08 | -17.7 | no
SELL_c1.5_T1440 | 3271852 | 6922 | 0.212 | 31.1 | 23.2 | 20.4 | 1.33 | 0.0835 | 85.6 | 76.7 | 28.4 | 25.4 | 14.8 | 18.1 | 2022-04-27 | 17.1 | 2022-04-22 | 23.2 | no
SELL_c2.5_T240 | 3271852 | 1734 | 0.053 | -1.8 | -9.2 | 51.2 | -0.11 | 0.5570 | 134.6 | 81.5 | -4.4 | -19.4 | -37.2 | -29.0 | 2022-04-27 | -34.9 | 2022-04-23 | -18.0 | no
SELL_c2.5_T1440 | 3271852 | 1734 | 0.053 | 117.3 | 101.5 | 59.8 | 1.90 | 0.0170 | 276.6 | 268.3 | 114.4 | 99.5 | 66.6 | 71.8 | 2022-04-27 | 64.3 | 2022-04-23 | 107.8 | no
crit_rw=3.4315 c_upper=2.6650 min_blocks_with_units=16

### K_PESS nua B (D=731, 37 khoi, seed 2026112151)
cell | n_dat | n_khop | P(khop)% | M | M_neth | SE | t | p | up95 | ci95_hi | M_adj | M-top3 | M-3sk | M-khoi(e') | khoi_start | M-cuaso(e'') | cuaso_start | stress5 | INSUFF
BUY_c1.0_T240 | 5947542 | 35566 | 0.598 | -6.9 | -19.9 | 33.9 | -0.32 | 0.9410 | 77.9 | 49.9 | -9.8 | -7.9 | 23.1 | -16.3 | 2024-03-01 | -18.6 | 2024-02-26 | -21.5 | no
BUY_c1.0_T1440 | 5937309 | 35500 | 0.598 | 15.9 | -20.5 | 48.6 | 0.24 | 0.8570 | 137.4 | 91.4 | 12.7 | 14.6 | 62.8 | 4.8 | 2024-03-01 | 0.7 | 2024-02-26 | 8.1 | no
BUY_c1.5_T240 | 5947557 | 12539 | 0.211 | 57.8 | 17.1 | 70.1 | 0.77 | 0.6640 | 233.1 | 175.6 | 54.8 | 56.0 | 130.9 | 47.0 | 2024-03-01 | 43.6 | 2024-02-26 | 43.9 | no
BUY_c1.5_T1440 | 5937324 | 12526 | 0.211 | 83.1 | 38.2 | 84.3 | 0.94 | 0.6145 | 294.0 | 224.2 | 79.8 | 80.5 | 169.6 | 61.9 | 2025-01-15 | 61.8 | 2024-02-26 | 75.3 | no
BUY_c2.5_T240 | 5946435 | 4333 | 0.073 | 241.8 | 152.8 | 99.5 | 2.39 | 0.3965 | 490.6 | 454.8 | 239.1 | 238.1 | 346.8 | 207.8 | 2024-04-10 | 218.2 | 2024-02-18 | 228.6 | no
BUY_c2.5_T1440 | 5936202 | 4331 | 0.073 | 269.1 | 193.5 | 113.7 | 2.33 | 0.4015 | 553.4 | 518.3 | 266.3 | 265.4 | 390.6 | 236.9 | 2025-01-15 | 238.5 | 2024-02-18 | 261.3 | no
SELL_c1.0_T240 | 5947542 | 34637 | 0.582 | -30.2 | -14.1 | 11.4 | -3.00 | 0.9990 | -1.7 | -9.3 | -33.5 | -31.7 | -32.4 | -34.6 | 2025-11-11 | -35.7 | 2025-11-07 | -45.4 | no
SELL_c1.0_T1440 | 5937309 | 34558 | 0.582 | -39.7 | -31.1 | 18.2 | -2.40 | 0.9990 | 5.9 | -5.0 | -43.3 | -41.8 | -44.2 | -48.4 | 2025-10-02 | -48.4 | 2025-10-02 | -48.8 | no
SELL_c1.5_T240 | 5947557 | 11769 | 0.198 | 0.6 | 11.3 | 15.2 | -0.22 | 0.9410 | 38.5 | 31.7 | -2.9 | -2.9 | -5.6 | -6.2 | 2025-10-02 | -10.7 | 2025-09-22 | -14.6 | no
SELL_c1.5_T1440 | 5937324 | 11730 | 0.198 | 4.7 | 7.1 | 24.8 | 0.03 | 0.8905 | 66.8 | 55.4 | 0.9 | 0.2 | -5.1 | -10.0 | 2025-10-02 | -10.3 | 2025-10-06 | -4.7 | no
SELL_c2.5_T240 | 5947563 | 3262 | 0.055 | 62.0 | 62.3 | 27.2 | 2.13 | 0.4285 | 129.9 | 124.9 | 58.4 | 51.1 | 46.2 | 47.7 | 2025-10-02 | 36.5 | 2025-09-27 | 44.6 | no
SELL_c2.5_T1440 | 5937330 | 3254 | 0.055 | 58.4 | 53.3 | 44.8 | 1.22 | 0.5830 | 170.4 | 143.0 | 54.4 | 47.7 | 45.7 | 36.3 | 2025-10-02 | 35.3 | 2025-09-22 | 47.5 | no
crit_rw=7.2084 c_upper=2.5012 min_blocks_with_units=13

### K_OPT3 nua A (D=914, 46 khoi, seed 2026112140)
cell | n_dat | n_khop | P(khop)% | M | M_neth | SE | t | p | up95 | ci95_hi | M_adj | M-top3 | M-3sk | M-khoi(e') | khoi_start | M-cuaso(e'') | cuaso_start | stress5 | INSUFF
BUY_c1.0_T240 | 3271852 | 25034 | 0.765 | 41.5 | 43.9 | 15.8 | 2.37 | 0.0320 | 83.4 | 70.4 | 39.1 | 40.3 | 43.4 | 37.5 | 2023-10-19 | 37.5 | 2023-10-19 | - | no
BUY_c1.0_T1440 | 3271852 | 25028 | 0.765 | 42.4 | 60.0 | 20.6 | 1.86 | 0.0855 | 96.7 | 80.2 | 39.7 | 40.6 | 59.1 | 36.9 | 2023-10-19 | 35.5 | 2023-10-24 | - | no
BUY_c1.5_T240 | 3271852 | 8542 | 0.261 | 94.8 | 88.1 | 30.6 | 2.97 | 0.0180 | 175.7 | 148.8 | 92.6 | 92.9 | 94.8 | 85.5 | 2022-04-27 | 85.5 | 2022-04-27 | - | no
BUY_c1.5_T1440 | 3271852 | 8541 | 0.261 | 91.1 | 111.8 | 36.1 | 2.41 | 0.0610 | 186.6 | 157.7 | 88.6 | 88.6 | 114.1 | 84.3 | 2023-11-08 | 83.0 | 2023-10-24 | - | no
BUY_c2.5_T240 | 3271836 | 2676 | 0.082 | 262.7 | 226.7 | 68.9 | 3.75 | 0.0045 | 445.0 | 399.1 | 260.6 | 258.4 | 235.2 | 235.3 | 2022-04-27 | 235.3 | 2022-04-24 | - | no
BUY_c2.5_T1440 | 3271836 | 2676 | 0.082 | 283.4 | 269.9 | 61.3 | 4.56 | 0.0005 | 445.6 | 413.7 | 281.1 | 281.8 | 273.3 | 256.8 | 2022-04-27 | 256.8 | 2022-04-24 | - | no
SELL_c1.0_T240 | 3271852 | 21154 | 0.647 | 5.1 | 1.3 | 7.7 | 0.15 | 0.4485 | 25.4 | 19.4 | 2.6 | 3.2 | -1.0 | 2.1 | 2022-04-27 | 0.8 | 2022-04-23 | - | no
SELL_c1.0_T1440 | 3271852 | 21153 | 0.647 | 19.6 | 12.8 | 11.0 | 1.42 | 0.0840 | 48.7 | 42.4 | 16.8 | 17.0 | 10.2 | 14.1 | 2022-04-27 | 12.9 | 2022-04-23 | - | no
SELL_c1.5_T240 | 3271852 | 7043 | 0.215 | 8.6 | 7.2 | 16.1 | 0.28 | 0.4250 | 51.1 | 37.1 | 6.0 | 3.4 | -3.1 | 2.0 | 2022-04-27 | 1.7 | 2022-05-08 | - | no
SELL_c1.5_T1440 | 3271852 | 7043 | 0.215 | 40.9 | 33.1 | 20.0 | 1.85 | 0.0345 | 93.7 | 84.4 | 38.0 | 35.3 | 24.6 | 28.2 | 2022-04-27 | 27.3 | 2022-04-22 | - | no
SELL_c2.5_T240 | 3271852 | 1749 | 0.053 | 11.3 | 4.1 | 50.7 | 0.14 | 0.4820 | 145.5 | 97.5 | 8.7 | -6.1 | -23.8 | -15.9 | 2022-04-27 | -21.6 | 2022-04-23 | - | no
SELL_c2.5_T1440 | 3271852 | 1749 | 0.053 | 127.1 | 111.0 | 59.5 | 2.07 | 0.0175 | 284.4 | 287.7 | 124.2 | 109.7 | 76.7 | 81.8 | 2022-04-27 | 74.4 | 2022-04-23 | - | no
crit_rw=3.4225 c_upper=2.6441 min_blocks_with_units=16

### K_OPT3 nua B (D=731, 37 khoi, seed 2026112141)
cell | n_dat | n_khop | P(khop)% | M | M_neth | SE | t | p | up95 | ci95_hi | M_adj | M-top3 | M-3sk | M-khoi(e') | khoi_start | M-cuaso(e'') | cuaso_start | stress5 | INSUFF
BUY_c1.0_T240 | 5947542 | 36285 | 0.610 | 6.6 | -6.2 | 33.2 | 0.08 | 0.8300 | 86.9 | 60.6 | 3.5 | 5.6 | 35.9 | -2.2 | 2024-03-01 | -4.4 | 2024-02-26 | - | no
BUY_c1.0_T1440 | 5937309 | 36215 | 0.610 | 28.1 | -7.6 | 47.3 | 0.51 | 0.7540 | 142.6 | 98.7 | 24.7 | 27.0 | 73.8 | 17.7 | 2024-03-01 | 13.8 | 2024-02-26 | - | no
BUY_c1.5_T240 | 5947557 | 12697 | 0.213 | 69.3 | 29.1 | 68.8 | 0.95 | 0.6285 | 236.2 | 180.1 | 66.2 | 67.6 | 141.1 | 58.9 | 2024-03-01 | 55.7 | 2024-02-26 | - | no
BUY_c1.5_T1440 | 5937324 | 12684 | 0.214 | 92.4 | 48.1 | 82.9 | 1.07 | 0.5965 | 293.2 | 227.6 | 89.0 | 90.0 | 177.4 | 71.8 | 2025-01-15 | 71.8 | 2024-02-26 | - | no
BUY_c2.5_T240 | 5946435 | 4363 | 0.073 | 254.4 | 166.4 | 97.5 | 2.57 | 0.4060 | 490.6 | 463.1 | 251.6 | 250.8 | 357.3 | 221.2 | 2024-04-10 | 231.6 | 2024-02-18 | - | no
BUY_c2.5_T1440 | 5936202 | 4361 | 0.073 | 281.5 | 206.8 | 111.1 | 2.50 | 0.4115 | 550.7 | 519.4 | 278.5 | 278.2 | 400.3 | 249.8 | 2025-01-15 | 252.1 | 2024-02-18 | - | no
SELL_c1.0_T240 | 5947542 | 35265 | 0.593 | -17.5 | -1.3 | 11.0 | -1.94 | 0.9885 | 9.3 | 3.4 | -21.0 | -19.0 | -19.8 | -21.8 | 2025-11-11 | -22.9 | 2025-11-07 | - | no
SELL_c1.0_T1440 | 5937309 | 35185 | 0.593 | -28.6 | -19.4 | 17.7 | -1.84 | 0.9885 | 14.4 | 3.4 | -32.4 | -30.5 | -33.1 | -37.2 | 2025-10-02 | -37.2 | 2025-10-02 | - | no
SELL_c1.5_T240 | 5947557 | 11906 | 0.200 | 12.3 | 23.1 | 15.2 | 0.55 | 0.7540 | 49.1 | 42.7 | 8.7 | 8.7 | 6.2 | 5.5 | 2025-10-02 | 1.3 | 2025-09-22 | - | no
SELL_c1.5_T1440 | 5937324 | 11867 | 0.200 | 16.2 | 18.7 | 24.6 | 0.49 | 0.7540 | 75.9 | 67.2 | 12.2 | 11.7 | 6.5 | 1.6 | 2025-10-02 | 1.2 | 2025-10-06 | - | no
SELL_c2.5_T240 | 5947563 | 3295 | 0.055 | 76.6 | 77.2 | 26.4 | 2.75 | 0.3960 | 140.7 | 138.1 | 72.8 | 65.9 | 61.3 | 62.7 | 2025-10-02 | 51.7 | 2025-09-27 | - | no
SELL_c2.5_T1440 | 5937330 | 3287 | 0.055 | 71.4 | 66.8 | 44.3 | 1.52 | 0.5310 | 178.7 | 154.7 | 67.3 | 60.8 | 58.9 | 49.6 | 2025-10-02 | 48.7 | 2025-09-22 | - | no
crit_rw=7.2205 c_upper=2.4236 min_blocks_with_units=13

### Dieu kien PASS tung o (a_rw_B, b_half_A, c_Madj_B, d_top3_B, e_events_AB, e2_topblock_AB, e3_topwindow_AB) ; P=PASS runner; O=PASS chinh thuc
# K_PESS
BUY_c1.0_T240 | ni=True a=False b=False c=False d=False e=True e'=False e''=False | P=False O=False
BUY_c1.0_T1440 | ni=True a=False b=False c=True d=True e=True e'=True e''=False | P=False O=False
BUY_c1.5_T240 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c1.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c2.5_T240 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c2.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
SELL_c1.0_T240 | ni=True a=False b=False c=False d=False e=False e'=False e''=False | P=False O=False
SELL_c1.0_T1440 | ni=True a=False b=False c=False d=False e=False e'=False e''=False | P=False O=False
SELL_c1.5_T240 | ni=True a=False b=False c=False d=False e=False e'=False e''=False | P=False O=False
SELL_c1.5_T1440 | ni=True a=False b=True c=True d=False e=False e'=False e''=False | P=False O=False
SELL_c2.5_T240 | ni=True a=False b=False c=True d=True e=False e'=False e''=False | P=False O=False
SELL_c2.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
# K_OPT3
BUY_c1.0_T240 | ni=True a=False b=True c=True d=True e=True e'=False e''=False | P=False O=False
BUY_c1.0_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c1.5_T240 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c1.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c2.5_T240 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
BUY_c2.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False
SELL_c1.0_T240 | ni=True a=False b=False c=False d=False e=False e'=False e''=False | P=False O=False
SELL_c1.0_T1440 | ni=True a=False b=True c=False d=False e=False e'=False e''=False | P=False O=False
SELL_c1.5_T240 | ni=True a=False b=False c=True d=True e=False e'=False e''=False | P=False O=False
SELL_c1.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=False e''=False | P=False O=False
SELL_c2.5_T240 | ni=True a=False b=False c=True d=True e=False e'=False e''=False | P=False O=False
SELL_c2.5_T1440 | ni=True a=False b=True c=True d=True e=True e'=True e''=True | P=False O=False

## 4. MDE that (mde_above_floor tu SE that, stats.py) + INSUFFICIENT
K_PESS A: INSUFFICIENT=[] ; MDE(bps vuot san 4): BUY_c1.0_T240=70.6, BUY_c1.0_T1440=93.0, BUY_c1.5_T240=133.9, BUY_c1.5_T1440=157.9, BUY_c2.5_T240=297.9, BUY_c2.5_T1440=265.8, SELL_c1.0_T240=33.5, SELL_c1.0_T1440=48.4, SELL_c1.5_T240=70.1, SELL_c1.5_T1440=87.3, SELL_c2.5_T240=218.6, SELL_c2.5_T1440=255.4
K_PESS B: INSUFFICIENT=[] ; MDE(bps vuot san 4): BUY_c1.0_T240=273.1, BUY_c1.0_T1440=391.2, BUY_c1.5_T240=564.1, BUY_c1.5_T1440=678.8, BUY_c2.5_T240=800.9, BUY_c2.5_T1440=915.1, SELL_c1.0_T240=91.7, SELL_c1.0_T1440=146.7, SELL_c1.5_T240=122.1, SELL_c1.5_T1440=199.7, SELL_c2.5_T240=218.7, SELL_c2.5_T1440=360.4
K_OPT3 A: INSUFFICIENT=[] ; MDE(bps vuot san 4): BUY_c1.0_T240=67.5, BUY_c1.0_T1440=87.7, BUY_c1.5_T240=130.4, BUY_c1.5_T1440=154.1, BUY_c2.5_T240=294.0, BUY_c2.5_T1440=261.5, SELL_c1.0_T240=32.7, SELL_c1.0_T1440=46.9, SELL_c1.5_T240=68.6, SELL_c1.5_T1440=85.2, SELL_c2.5_T240=216.4, SELL_c2.5_T1440=253.7
K_OPT3 B: INSUFFICIENT=[] ; MDE(bps vuot san 4): BUY_c1.0_T240=267.3, BUY_c1.0_T1440=381.0, BUY_c1.5_T240=554.9, BUY_c1.5_T1440=668.0, BUY_c2.5_T240=785.8, BUY_c2.5_T1440=895.6, SELL_c1.0_T240=89.1, SELL_c1.0_T1440=143.0, SELL_c1.5_T240=122.5, SELL_c1.5_T1440=198.7, SELL_c2.5_T240=213.1, SELL_c2.5_T1440=357.0

## 5. Chan doan (KHONG phai bang chung)
### 5a. M_by_year (A: 2021-2023; B: 2024-2025), thu tu cell nhu bang
K_PESS A 2021: 45 86 169 196 510 511 -13 -0 -7 -7 -44 120
K_PESS A 2022: 16 -31 72 -21 326 278 15 33 13 56 41 187
K_PESS A 2023: 33 54 73 99 158 206 -19 -4 -13 27 -19 72
K_PESS B 2024: 42 58 165 187 446 464 -43 -57 -29 -19 -4 96
K_PESS B 2025: -53 -24 -48 -20 29 65 -22 -27 17 19 91 42
K_OPT3 A 2021: 53 93 176 202 516 516 -5 6 0 -1 -27 133
K_OPT3 A 2022: 30 -16 84 -9 334 285 26 43 25 67 51 196
K_OPT3 A 2023: 45 64 84 109 170 217 -5 10 2 37 -4 82
K_OPT3 B 2024: 53 67 174 194 455 472 -31 -47 -18 -10 11 109
K_OPT3 B 2025: -37 -9 -34 -8 47 83 -8 -16 29 31 106 55
### 5b. chenh M K_OPT3 - K_PESS
A: 12.4 11.4 10.6 9.8 9.5 8.5 12.4 11.2 12.5 9.8 13.1 9.8
B: 13.5 12.2 11.5 9.3 12.6 12.4 12.7 11.1 11.7 11.4 14.6 13.0
### 5c. tong hop theo o x mo hinh x nua: P(thoat limit), thoi gian giu, phan vi unit, lo lon nhat, skew, SD, gross, phi, truot, funding, cap, excl_gap_rate, M_bo_2025-10-10..13
# K_PESS A
BUY_c1.0_T240 | plim=0.614 hold=117.1 | q01=-1202.5 q05=-612.5 q50=127.5 q95=327.5 worst=-7251.1 | skew=-3.88 sd=337.7 | gross=40.2 fee=8.4 slip=3.1 fund=0.5 cap=2.3 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=29.2 | top_block share=0.204 n=1784
BUY_c1.0_T1440 | plim=0.779 hold=426.6 | q01=-1977.5 q05=-807.5 q50=152.5 q95=337.5 worst=-9917.3 | skew=-5.84 sd=482.4 | gross=39.7 fee=8.2 slip=1.7 fund=1.1 cap=2.5 | excl_gap=0.0000 n_excl=107 | Mdrop_oct25=30.9 | top_block share=0.241 n=1784
BUY_c1.5_T240 | plim=0.583 hold=119.3 | q01=-1227.5 q05=-637.5 q50=187.5 q95=492.5 worst=-7026.0 | skew=-3.74 sd=404.8 | gross=95.2 fee=8.4 slip=3.4 fund=0.9 cap=2.2 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=84.3 | top_block share=0.146 n=292
BUY_c1.5_T1440 | plim=0.719 hold=486.2 | q01=-1972.5 q05=-852.5 q50=222.5 q95=502.5 worst=-9619.2 | skew=-4.72 sd=535.3 | gross=90.1 fee=8.3 slip=2.2 fund=1.8 cap=2.4 | excl_gap=0.0000 n_excl=102 | Mdrop_oct25=81.3 | top_block share=0.146 n=544
BUY_c2.5_T240 | plim=0.582 hold=115.6 | q01=-1032.5 q05=-527.5 q50=332.5 q95=857.5 worst=-6936.2 | skew=-3.31 sd=491.7 | gross=264.0 fee=8.5 slip=3.6 fund=1.3 cap=2.0 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=253.3 | top_block share=0.151 n=122
BUY_c2.5_T1440 | plim=0.710 hold=484.8 | q01=-1612.5 q05=-557.5 q50=377.5 q95=867.5 worst=-7692.7 | skew=-4.49 sd=569.4 | gross=283.4 fee=8.4 slip=2.4 fund=2.3 cap=2.2 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=274.9 | top_block share=0.140 n=122
SELL_c1.0_T240 | plim=0.630 hold=116.9 | q01=-1972.5 q05=-807.5 q50=142.5 q95=367.5 worst=-81815.0 | skew=-60.20 sd=770.3 | gross=5.5 fee=8.4 slip=3.0 fund=-1.3 cap=2.4 | excl_gap=0.0000 n_excl=102 | Mdrop_oct25=-7.2 | top_block share=-0.379 n=738
SELL_c1.0_T1440 | plim=0.809 hold=400.0 | q01=-3142.5 q05=-1032.5 q50=177.5 q95=392.5 worst=-16833.4 | skew=-7.40 sd=741.0 | gross=22.5 fee=8.2 slip=1.7 fund=-4.2 cap=2.7 | excl_gap=0.0000 n_excl=103 | Mdrop_oct25=8.4 | top_block share=0.701 n=738
SELL_c1.5_T240 | plim=0.593 hold=124.0 | q01=-2647.5 q05=-1117.5 q50=202.5 q95=527.5 worst=-76801.1 | skew=-42.80 sd=1171.5 | gross=10.8 fee=8.4 slip=3.4 fund=-2.9 cap=2.5 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=-3.9 | top_block share=-1.609 n=249
SELL_c1.5_T1440 | plim=0.774 hold=451.1 | q01=-3977.5 q05=-1467.5 q50=252.5 q95=572.5 worst=-14030.7 | skew=-5.96 sd=940.4 | gross=51.2 fee=8.2 slip=2.0 fund=-9.8 cap=2.7 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=31.1 | top_block share=0.438 n=249
SELL_c2.5_T240 | plim=0.548 hold=136.3 | q01=-3622.5 q05=-1717.5 q50=322.5 q95=902.5 worst=-66806.1 | skew=-24.73 sd=1936.1 | gross=16.8 fee=8.5 slip=4.1 fund=-6.0 cap=2.6 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=-1.8 | top_block share=-14.477 n=105
SELL_c2.5_T1440 | plim=0.743 hold=509.3 | q01=-5107.5 q05=-2027.5 q50=402.5 q95=942.5 worst=-11063.7 | skew=-3.95 sd=1181.8 | gross=148.8 fee=8.2 slip=2.5 fund=-20.8 cap=2.9 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=117.3 | top_block share=0.425 n=105
# K_PESS B
BUY_c1.0_T240 | plim=0.601 hold=116.0 | q01=-2152.5 q05=-902.5 q50=162.5 q95=397.5 worst=-8968.2 | skew=-4.00 sd=517.9 | gross=4.2 fee=8.4 slip=3.6 fund=0.9 cap=2.9 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=23.1 | top_block share=-1.171 n=2704
BUY_c1.0_T1440 | plim=0.776 hold=431.7 | q01=-2632.5 q05=-1262.5 q50=202.5 q95=417.5 worst=-9125.8 | skew=-3.90 sd=628.7 | gross=23.8 fee=8.2 slip=2.0 fund=2.2 cap=3.2 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=62.8 | top_block share=0.720 n=2704
BUY_c1.5_T240 | plim=0.620 hold=104.0 | q01=-2527.5 q05=-1332.5 q50=262.5 q95=592.5 worst=-8331.9 | skew=-3.47 sd=673.7 | gross=68.2 fee=8.4 slip=3.5 fund=1.5 cap=3.0 | excl_gap=0.0000 n_excl=298 | Mdrop_oct25=130.9 | top_block share=0.248 n=952
BUY_c1.5_T1440 | plim=0.776 hold=398.3 | q01=-2907.5 q05=-1672.5 q50=307.5 q95=617.5 worst=-9090.1 | skew=-3.47 sd=778.8 | gross=89.6 fee=8.2 slip=2.0 fund=3.6 cap=3.3 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=169.6 | top_block share=0.304 n=837
BUY_c2.5_T240 | plim=0.646 hold=92.8 | q01=-2877.5 q05=-1502.5 q50=457.5 q95=902.5 worst=-8371.6 | skew=-3.33 sd=833.2 | gross=252.4 fee=8.4 slip=3.3 fund=1.1 cap=2.6 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=346.8 | top_block share=0.210 n=348
BUY_c2.5_T1440 | plim=0.780 hold=335.0 | q01=-3112.5 q05=-1657.5 q50=502.5 q95=922.5 worst=-9013.3 | skew=-3.37 sd=898.2 | gross=276.0 fee=8.3 slip=2.0 fund=3.4 cap=2.8 | excl_gap=0.0001 n_excl=297 | Mdrop_oct25=390.6 | top_block share=0.181 n=303
SELL_c1.0_T240 | plim=0.609 hold=116.4 | q01=-2737.5 q05=-1042.5 q50=177.5 q95=447.5 worst=-39220.4 | skew=-11.08 sd=741.4 | gross=-14.0 fee=8.4 slip=3.8 fund=-4.0 cap=3.3 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=-32.4 | top_block share=-0.094 n=1572
SELL_c1.0_T1440 | plim=0.776 hold=423.8 | q01=-4157.5 q05=-1282.5 q50=212.5 q95=467.5 worst=-85425.3 | skew=-21.10 sd=1312.7 | gross=-15.7 fee=8.3 slip=2.3 fund=-13.4 cap=3.6 | excl_gap=0.0001 n_excl=299 | Mdrop_oct25=-44.2 | top_block share=-0.150 n=1967
SELL_c1.5_T240 | plim=0.620 hold=112.0 | q01=-3662.5 q05=-1427.5 q50=262.5 q95=672.5 worst=-36539.6 | skew=-9.47 sd=985.1 | gross=20.7 fee=8.4 slip=3.8 fund=-7.9 cap=3.5 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=-5.6 | top_block share=10.556 n=919
SELL_c1.5_T1440 | plim=0.775 hold=414.7 | q01=-5577.5 q05=-1667.5 q50=312.5 q95=702.5 worst=-52454.7 | skew=-12.83 sd=1536.0 | gross=41.6 fee=8.2 slip=2.4 fund=-26.2 cap=3.8 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=-5.1 | top_block share=2.952 n=919
SELL_c2.5_T240 | plim=0.580 hold=119.3 | q01=-4752.5 q05=-2017.5 q50=407.5 q95=1082.5 worst=-33059.0 | skew=-7.58 sd=1333.5 | gross=88.9 fee=8.4 slip=4.4 fund=-14.1 cap=3.6 | excl_gap=0.0000 n_excl=296 | Mdrop_oct25=46.2 | top_block share=0.310 n=338
SELL_c2.5_T1440 | plim=0.753 hold=448.3 | q01=-7567.5 q05=-2392.5 q50=492.5 q95=1142.5 worst=-49442.7 | skew=-11.13 sd=2236.9 | gross=121.4 fee=8.2 slip=2.9 fund=-51.8 cap=4.0 | excl_gap=0.0000 n_excl=296 | Mdrop_oct25=45.7 | top_block share=0.443 n=338
# K_OPT3 A
BUY_c1.0_T240 | plim=0.644 hold=112.9 | q01=-1172.5 q05=-582.5 q50=132.5 q95=332.5 worst=-7235.2 | skew=-4.02 sd=330.2 | gross=45.1 fee=4.0 slip=0.0 fund=0.5 cap=2.4 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=41.5 | top_block share=0.167 n=1894
BUY_c1.0_T1440 | plim=0.802 hold=409.7 | q01=-1897.5 q05=-772.5 q50=157.5 q95=342.5 worst=-9915.1 | skew=-6.03 sd=470.7 | gross=45.3 fee=4.0 slip=0.0 fund=1.1 cap=2.7 | excl_gap=0.0000 n_excl=107 | Mdrop_oct25=42.4 | top_block share=0.194 n=1894
BUY_c1.5_T240 | plim=0.610 hold=116.5 | q01=-1212.5 q05=-622.5 q50=197.5 q95=497.5 worst=-7021.6 | skew=-3.82 sd=399.9 | gross=98.0 fee=4.0 slip=0.0 fund=0.9 cap=2.3 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=94.8 | top_block share=0.130 n=293
BUY_c1.5_T1440 | plim=0.743 hold=473.7 | q01=-1962.5 q05=-837.5 q50=227.5 q95=502.5 worst=-9617.1 | skew=-4.81 sd=529.5 | gross=93.4 fee=4.0 slip=0.0 fund=1.8 cap=2.5 | excl_gap=0.0000 n_excl=102 | Mdrop_oct25=91.1 | top_block share=0.134 n=549
BUY_c2.5_T240 | plim=0.604 hold=114.3 | q01=-1022.5 q05=-512.5 q50=342.5 q95=862.5 worst=-6931.8 | skew=-3.38 sd=487.1 | gross=265.4 fee=4.1 slip=0.0 fund=1.3 cap=2.1 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=262.7 | top_block share=0.145 n=122
BUY_c2.5_T1440 | plim=0.731 hold=477.6 | q01=-1602.5 q05=-542.5 q50=382.5 q95=867.5 worst=-7688.9 | skew=-4.56 sd=564.1 | gross=285.2 fee=4.1 slip=0.0 fund=2.3 cap=2.3 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=283.4 | top_block share=0.135 n=122
SELL_c1.0_T240 | plim=0.652 hold=114.1 | q01=-1937.5 q05=-777.5 q50=147.5 q95=372.5 worst=-81739.6 | skew=-61.34 sd=758.7 | gross=10.4 fee=4.0 slip=0.0 fund=-1.3 cap=2.6 | excl_gap=0.0000 n_excl=102 | Mdrop_oct25=5.1 | top_block share=0.604 n=745
SELL_c1.0_T1440 | plim=0.827 hold=388.7 | q01=-3067.5 q05=-987.5 q50=182.5 q95=397.5 worst=-16698.0 | skew=-7.56 sd=727.4 | gross=27.7 fee=4.0 slip=0.0 fund=-4.1 cap=2.8 | excl_gap=0.0000 n_excl=103 | Mdrop_oct25=19.6 | top_block share=0.307 n=745
SELL_c1.5_T240 | plim=0.617 hold=121.9 | q01=-2627.5 q05=-1092.5 q50=207.5 q95=527.5 worst=-76729.8 | skew=-43.31 sd=1159.3 | gross=15.4 fee=4.0 slip=0.0 fund=-2.9 cap=2.6 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=8.6 | top_block share=0.775 n=250
SELL_c1.5_T1440 | plim=0.793 hold=442.9 | q01=-3912.5 q05=-1427.5 q50=257.5 q95=577.5 worst=-13997.5 | skew=-6.03 sd=928.8 | gross=54.6 fee=4.0 slip=0.0 fund=-9.7 cap=2.9 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=40.9 | top_block share=0.334 n=250
SELL_c2.5_T240 | plim=0.566 hold=135.2 | q01=-3602.5 q05=-1697.5 q50=327.5 q95=902.5 worst=-66742.7 | skew=-24.88 sd=1925.2 | gross=21.1 fee=4.0 slip=0.0 fund=-5.8 cap=2.6 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=11.3 | top_block share=2.320 n=106
SELL_c2.5_T1440 | plim=0.760 hold=505.0 | q01=-5087.5 q05=-1967.5 q50=407.5 q95=947.5 worst=-11034.7 | skew=-3.97 sd=1173.4 | gross=151.6 fee=4.0 slip=0.0 fund=-20.5 cap=2.9 | excl_gap=0.0000 n_excl=101 | Mdrop_oct25=127.1 | top_block share=0.396 n=106
# K_OPT3 B
BUY_c1.0_T240 | plim=0.630 hold=113.4 | q01=-2112.5 q05=-877.5 q50=172.5 q95=402.5 worst=-8964.9 | skew=-4.02 sd=508.7 | gross=9.7 fee=4.0 slip=0.0 fund=0.9 cap=3.0 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=35.9 | top_block share=1.312 n=2740
BUY_c1.0_T1440 | plim=0.801 hold=420.3 | q01=-2607.5 q05=-1227.5 q50=207.5 q95=422.5 worst=-9122.7 | skew=-3.94 sd=616.6 | gross=29.9 fee=4.0 slip=0.0 fund=2.2 cap=3.3 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=73.8 | top_block share=0.419 n=2740
BUY_c1.5_T240 | plim=0.655 hold=102.5 | q01=-2517.5 q05=-1302.5 q50=267.5 q95=592.5 worst=-8327.7 | skew=-3.52 sd=667.5 | gross=71.9 fee=4.0 slip=0.0 fund=1.4 cap=3.2 | excl_gap=0.0000 n_excl=298 | Mdrop_oct25=141.1 | top_block share=0.214 n=963
BUY_c1.5_T1440 | plim=0.808 hold=392.1 | q01=-2872.5 q05=-1652.5 q50=312.5 q95=622.5 worst=-9086.9 | skew=-3.52 sd=772.8 | gross=92.9 fee=4.0 slip=0.0 fund=3.5 cap=3.4 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=177.4 | top_block share=0.275 n=845
BUY_c2.5_T240 | plim=0.699 hold=91.2 | q01=-2817.5 q05=-1482.5 q50=467.5 q95=907.5 worst=-8367.5 | skew=-3.38 sd=827.0 | gross=257.3 fee=4.1 slip=0.0 fund=1.1 cap=2.8 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=357.3 | top_block share=0.200 n=348
BUY_c2.5_T1440 | plim=0.833 hold=327.8 | q01=-3097.5 q05=-1637.5 q50=507.5 q95=927.5 worst=-9010.1 | skew=-3.42 sd=891.1 | gross=282.2 fee=4.1 slip=0.0 fund=3.4 cap=3.0 | excl_gap=0.0001 n_excl=297 | Mdrop_oct25=400.3 | top_block share=0.175 n=306
SELL_c1.0_T240 | plim=0.637 hold=114.7 | q01=-2707.5 q05=-1007.5 q50=182.5 q95=452.5 worst=-39154.2 | skew=-11.27 sd=731.4 | gross=-9.6 fee=4.0 slip=0.0 fund=-3.9 cap=3.5 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=-19.8 | top_block share=-0.191 n=1600
SELL_c1.0_T1440 | plim=0.802 hold=417.2 | q01=-4102.5 q05=-1247.5 q50=217.5 q95=472.5 worst=-84905.3 | skew=-21.26 sd=1296.8 | gross=-11.5 fee=4.0 slip=0.0 fund=-13.1 cap=3.8 | excl_gap=0.0001 n_excl=299 | Mdrop_oct25=-33.1 | top_block share=-0.227 n=1995
SELL_c1.5_T240 | plim=0.650 hold=110.8 | q01=-3607.5 q05=-1397.5 q50=267.5 q95=677.5 worst=-36476.9 | skew=-9.56 sd=976.7 | gross=24.0 fee=4.0 slip=0.0 fund=-7.8 cap=3.6 | excl_gap=0.0000 n_excl=297 | Mdrop_oct25=6.2 | top_block share=0.587 n=925
SELL_c1.5_T1440 | plim=0.804 hold=410.7 | q01=-5532.5 q05=-1637.5 q50=317.5 q95=707.5 worst=-52386.4 | skew=-12.96 sd=1522.4 | gross=46.1 fee=4.0 slip=0.0 fund=-26.0 cap=3.9 | excl_gap=0.0001 n_excl=298 | Mdrop_oct25=6.5 | top_block share=0.910 n=925
SELL_c2.5_T240 | plim=0.617 hold=118.3 | q01=-4727.5 q05=-2002.5 q50=417.5 q95=1087.5 worst=-33000.8 | skew=-7.64 sd=1323.9 | gross=94.6 fee=4.0 slip=0.0 fund=-14.0 cap=3.8 | excl_gap=0.0000 n_excl=296 | Mdrop_oct25=61.3 | top_block share=0.266 n=341
SELL_c2.5_T1440 | plim=0.787 hold=442.8 | q01=-7547.5 q05=-2342.5 q50=497.5 q95=1147.5 worst=-49377.7 | skew=-11.21 sd=2221.5 | gross=126.6 fee=4.0 slip=0.0 fund=-51.3 cap=4.1 | excl_gap=0.0000 n_excl=296 | Mdrop_oct25=58.9 | top_block share=0.377 n=341
### 5d. ti le thang M>0 / trung vi M thang (monthly)
BUY_c1.0_T240 K_OPT3 A: frac_pos=0.633 median=61.3 n=30
BUY_c1.0_T240 K_OPT3 B: frac_pos=0.708 median=50.6 n=24
BUY_c1.0_T240 K_PESS A: frac_pos=0.633 median=50.2 n=30
BUY_c1.0_T240 K_PESS B: frac_pos=0.708 median=32.6 n=24
BUY_c1.0_T1440 K_OPT3 A: frac_pos=0.733 median=66.9 n=30
BUY_c1.0_T1440 K_OPT3 B: frac_pos=0.917 median=82.7 n=24
BUY_c1.0_T1440 K_PESS A: frac_pos=0.700 median=56.1 n=30
BUY_c1.0_T1440 K_PESS B: frac_pos=0.875 median=67.7 n=24
BUY_c1.5_T240 K_OPT3 A: frac_pos=0.767 median=129.3 n=30
BUY_c1.5_T240 K_OPT3 B: frac_pos=0.792 median=132.2 n=24
BUY_c1.5_T240 K_PESS A: frac_pos=0.767 median=118.0 n=30
BUY_c1.5_T240 K_PESS B: frac_pos=0.750 median=122.7 n=24
BUY_c1.5_T1440 K_OPT3 A: frac_pos=0.767 median=163.6 n=30
BUY_c1.5_T1440 K_OPT3 B: frac_pos=0.875 median=133.0 n=24
BUY_c1.5_T1440 K_PESS A: frac_pos=0.767 median=155.0 n=30
BUY_c1.5_T1440 K_PESS B: frac_pos=0.792 median=121.1 n=24
BUY_c2.5_T240 K_OPT3 A: frac_pos=0.897 median=351.9 n=29
BUY_c2.5_T240 K_OPT3 B: frac_pos=0.792 median=293.2 n=24
BUY_c2.5_T240 K_PESS A: frac_pos=0.897 median=338.9 n=29
BUY_c2.5_T240 K_PESS B: frac_pos=0.750 median=281.0 n=24
BUY_c2.5_T1440 K_OPT3 A: frac_pos=0.931 median=400.6 n=29
BUY_c2.5_T1440 K_OPT3 B: frac_pos=0.750 median=275.8 n=24
BUY_c2.5_T1440 K_PESS A: frac_pos=0.931 median=385.0 n=29
BUY_c2.5_T1440 K_PESS B: frac_pos=0.750 median=266.6 n=24
SELL_c1.0_T240 K_OPT3 A: frac_pos=0.533 median=16.2 n=30
SELL_c1.0_T240 K_OPT3 B: frac_pos=0.417 median=-14.2 n=24
SELL_c1.0_T240 K_PESS A: frac_pos=0.500 median=1.7 n=30
SELL_c1.0_T240 K_PESS B: frac_pos=0.333 median=-24.2 n=24
SELL_c1.0_T1440 K_OPT3 A: frac_pos=0.667 median=24.9 n=30
SELL_c1.0_T1440 K_OPT3 B: frac_pos=0.417 median=-14.1 n=24
SELL_c1.0_T1440 K_PESS A: frac_pos=0.567 median=13.2 n=30
SELL_c1.0_T1440 K_PESS B: frac_pos=0.417 median=-23.0 n=24
SELL_c1.5_T240 K_OPT3 A: frac_pos=0.633 median=22.6 n=30
SELL_c1.5_T240 K_OPT3 B: frac_pos=0.500 median=-0.9 n=24
SELL_c1.5_T240 K_PESS A: frac_pos=0.533 median=13.3 n=30
SELL_c1.5_T240 K_PESS B: frac_pos=0.458 median=-9.6 n=24
SELL_c1.5_T1440 K_OPT3 A: frac_pos=0.733 median=54.3 n=30
SELL_c1.5_T1440 K_OPT3 B: frac_pos=0.583 median=19.8 n=24
SELL_c1.5_T1440 K_PESS A: frac_pos=0.733 median=44.0 n=30
SELL_c1.5_T1440 K_PESS B: frac_pos=0.542 median=12.3 n=24
SELL_c2.5_T240 K_OPT3 A: frac_pos=0.633 median=72.7 n=30
SELL_c2.5_T240 K_OPT3 B: frac_pos=0.542 median=42.9 n=24
SELL_c2.5_T240 K_PESS A: frac_pos=0.600 median=50.4 n=30
SELL_c2.5_T240 K_PESS B: frac_pos=0.542 median=24.4 n=24
SELL_c2.5_T1440 K_OPT3 A: frac_pos=0.900 median=143.0 n=30
SELL_c2.5_T1440 K_OPT3 B: frac_pos=0.667 median=108.0 n=24
SELL_c2.5_T1440 K_PESS A: frac_pos=0.867 median=133.7 n=30
SELL_c2.5_T1440 K_PESS B: frac_pos=0.667 median=92.2 n=24
### 5e. diag theo dim (tier, year, condB, mkt, qvratio, wick1m, hour): cell model half dim level | n_place n_fill p_fill% M M_neth gross p_lim hold
BUY_c1.0_T240 K_OPT3 A condB no | 2988434 19811 0.663 44.4 51.7 48.0 0.636 115.5
BUY_c1.0_T240 K_OPT3 A condB yes | 283418 5223 1.843 30.7 14.3 34.0 0.675 103.3
BUY_c1.0_T240 K_OPT3 A hour h0 | 136608 1149 0.842 112.1 67.6 116.1 0.700 110.0
BUY_c1.0_T240 K_OPT3 A hour h1 | 136358 911 0.668 22.0 41.2 26.0 0.541 132.1
BUY_c1.0_T240 K_OPT3 A hour h10 | 136344 697 0.511 170.9 130.7 174.9 0.912 52.5
BUY_c1.0_T240 K_OPT3 A hour h11 | 136231 626 0.460 151.6 132.8 155.7 0.871 63.2
BUY_c1.0_T240 K_OPT3 A hour h12 | 136350 1002 0.735 103.3 88.5 106.8 0.697 106.0
BUY_c1.0_T240 K_OPT3 A hour h13 | 136358 1322 0.970 129.3 83.1 133.1 0.835 85.7
BUY_c1.0_T240 K_OPT3 A hour h14 | 136480 1188 0.870 114.8 79.8 116.9 0.813 70.9
BUY_c1.0_T240 K_OPT3 A hour h15 | 136465 1910 1.400 20.9 57.0 24.5 0.647 106.8
BUY_c1.0_T240 K_OPT3 A hour h16 | 136566 1205 0.882 14.6 14.7 18.2 0.682 94.6
BUY_c1.0_T240 K_OPT3 A hour h17 | 136256 1207 0.886 -60.8 -18.7 -56.8 0.606 127.9
BUY_c1.0_T240 K_OPT3 A hour h18 | 136353 1215 0.891 89.8 67.9 93.5 0.766 84.8
BUY_c1.0_T240 K_OPT3 A hour h19 | 136234 1504 1.104 2.0 3.6 5.7 0.436 153.9
BUY_c1.0_T240 K_OPT3 A hour h2 | 136422 936 0.686 7.8 -24.3 11.8 0.578 125.4
BUY_c1.0_T240 K_OPT3 A hour h20 | 136351 1374 1.008 111.4 91.1 114.9 0.693 97.8
BUY_c1.0_T240 K_OPT3 A hour h21 | 136217 1362 1.000 -17.3 83.0 -14.5 0.552 137.1
BUY_c1.0_T240 K_OPT3 A hour h22 | 136111 1195 0.878 47.0 39.0 50.7 0.680 105.6
BUY_c1.0_T240 K_OPT3 A hour h23 | 136059 747 0.549 62.0 43.0 64.7 0.726 87.2
BUY_c1.0_T240 K_OPT3 A hour h3 | 136252 600 0.440 -88.4 -37.3 -84.6 0.420 163.5
BUY_c1.0_T240 K_OPT3 A hour h4 | 136260 798 0.586 -222.1 -115.2 -219.3 0.429 156.5
BUY_c1.0_T240 K_OPT3 A hour h5 | 136127 695 0.511 58.0 43.1 61.0 0.695 105.5
BUY_c1.0_T240 K_OPT3 A hour h6 | 136266 430 0.316 88.3 -0.3 90.1 0.519 147.3
BUY_c1.0_T240 K_OPT3 A hour h7 | 136230 765 0.562 76.1 42.3 79.3 0.776 87.6
BUY_c1.0_T240 K_OPT3 A hour h8 | 136565 981 0.718 -25.7 27.8 -21.7 0.423 163.2
BUY_c1.0_T240 K_OPT3 A hour h9 | 136389 1215 0.891 41.0 44.9 45.0 0.486 146.0
BUY_c1.0_T240 K_OPT3 A mkt idio | 0 5022 NA 24.6 27.8 27.1 0.669 109.5
BUY_c1.0_T240 K_OPT3 A mkt market | 0 20012 NA 45.8 47.9 49.6 0.638 113.8
BUY_c1.0_T240 K_OPT3 A qvratio 1_10 | 0 3984 NA 47.9 26.6 51.3 0.661 116.7
BUY_c1.0_T240 K_OPT3 A qvratio gt10 | 0 20994 NA 40.4 47.3 44.0 0.640 112.2
BUY_c1.0_T240 K_OPT3 A qvratio lt1 | 0 56 NA 9.0 -6.4 12.7 0.714 112.6
BUY_c1.0_T240 K_OPT3 A tier T1 | 219092 1215 0.555 65.5 68.1 68.7 0.649 108.4
BUY_c1.0_T240 K_OPT3 A tier T2 | 1095287 6906 0.631 54.0 55.3 57.1 0.647 110.9
BUY_c1.0_T240 K_OPT3 A tier T3 | 1957473 16913 0.864 34.7 37.5 38.4 0.642 114.1
BUY_c1.0_T240 K_OPT3 A wick1m iso | 0 1029 NA 117.8 107.8 121.8 0.792 67.7
BUY_c1.0_T240 K_OPT3 A wick1m na | 0 4 NA 46.5 9.4 50.8 0.500 148.2
BUY_c1.0_T240 K_OPT3 A wick1m not | 0 24001 NA 38.3 41.2 41.8 0.638 114.9
BUY_c1.0_T240 K_OPT3 A year y2021 | 533832 2775 0.520 53.4 95.3 56.2 0.659 105.3
BUY_c1.0_T240 K_OPT3 A year y2022 | 1190474 7841 0.659 30.4 24.9 33.9 0.620 118.4
BUY_c1.0_T240 K_OPT3 A year y2023 | 1547546 14418 0.932 45.3 44.3 49.0 0.654 111.5
BUY_c1.0_T240 K_OPT3 B condB no | 5274788 27288 0.517 8.1 3.3 11.1 0.622 116.2
BUY_c1.0_T240 K_OPT3 B condB yes | 672754 8997 1.337 2.0 -34.9 5.5 0.655 104.7
BUY_c1.0_T240 K_OPT3 B hour h0 | 248476 2802 1.128 -95.5 -42.8 -92.0 0.486 144.2
BUY_c1.0_T240 K_OPT3 B hour h1 | 248133 2086 0.841 -23.0 -19.3 -19.4 0.503 141.7
BUY_c1.0_T240 K_OPT3 B hour h10 | 247734 813 0.328 93.1 17.3 96.1 0.786 80.0
BUY_c1.0_T240 K_OPT3 B hour h11 | 247515 952 0.385 -34.1 -28.2 -31.4 0.571 132.2
BUY_c1.0_T240 K_OPT3 B hour h12 | 247856 1567 0.632 34.5 12.3 37.6 0.639 107.0
BUY_c1.0_T240 K_OPT3 B hour h13 | 248119 1454 0.586 71.4 78.4 74.7 0.711 98.5
BUY_c1.0_T240 K_OPT3 B hour h14 | 248377 1668 0.672 5.5 -3.3 8.4 0.580 126.6
BUY_c1.0_T240 K_OPT3 B hour h15 | 248617 2690 1.082 87.4 79.3 90.6 0.646 107.8
BUY_c1.0_T240 K_OPT3 B hour h16 | 248702 1837 0.739 78.9 86.5 82.1 0.696 96.7
BUY_c1.0_T240 K_OPT3 B hour h17 | 248455 2674 1.076 17.4 -19.1 21.3 0.619 114.4
BUY_c1.0_T240 K_OPT3 B hour h18 | 247632 1495 0.604 13.6 -22.1 17.1 0.613 115.9
BUY_c1.0_T240 K_OPT3 B hour h19 | 247437 1396 0.564 5.7 -6.2 9.0 0.464 151.2
BUY_c1.0_T240 K_OPT3 B hour h2 | 248008 1416 0.571 110.7 74.2 113.8 0.624 115.1
BUY_c1.0_T240 K_OPT3 B hour h20 | 247711 1696 0.685 -312.2 -309.1 -309.6 0.594 123.2
BUY_c1.0_T240 K_OPT3 B hour h21 | 247307 1742 0.704 -261.1 -211.6 -258.2 0.570 127.4
BUY_c1.0_T240 K_OPT3 B hour h22 | 247189 2293 0.928 173.8 122.8 177.2 0.881 51.2
BUY_c1.0_T240 K_OPT3 B hour h23 | 246684 677 0.274 -40.2 -97.4 -38.0 0.542 134.8
BUY_c1.0_T240 K_OPT3 B hour h3 | 247701 577 0.233 26.6 8.0 29.0 0.700 93.0
BUY_c1.0_T240 K_OPT3 B hour h4 | 247650 563 0.227 18.2 -7.6 21.1 0.691 100.5
BUY_c1.0_T240 K_OPT3 B hour h5 | 247405 1064 0.430 89.6 46.0 92.2 0.665 115.9
BUY_c1.0_T240 K_OPT3 B hour h6 | 247448 1450 0.586 134.9 9.1 137.4 0.811 77.0
BUY_c1.0_T240 K_OPT3 B hour h7 | 247509 1235 0.499 45.9 31.5 48.5 0.645 108.8
BUY_c1.0_T240 K_OPT3 B hour h8 | 248095 1088 0.439 17.4 27.9 20.1 0.537 138.8
BUY_c1.0_T240 K_OPT3 B hour h9 | 247782 1050 0.424 -44.6 -17.2 -42.1 0.658 104.8
BUY_c1.0_T240 K_OPT3 B mkt idio | 0 10046 NA 4.1 -0.3 5.5 0.653 111.0
BUY_c1.0_T240 K_OPT3 B mkt market | 0 26239 NA 7.5 -8.4 11.3 0.621 114.3
BUY_c1.0_T240 K_OPT3 B qvratio 1_10 | 0 4445 NA 20.5 19.6 24.0 0.596 133.9
BUY_c1.0_T240 K_OPT3 B qvratio gt10 | 0 31799 NA 4.7 -9.7 7.8 0.634 110.5
BUY_c1.0_T240 K_OPT3 B qvratio lt1 | 0 41 NA -51.7 -42.7 -47.9 0.683 126.0
BUY_c1.0_T240 K_OPT3 B tier T1 | 175370 914 0.521 72.0 51.1 75.2 0.674 103.0
BUY_c1.0_T240 K_OPT3 B tier T2 | 875827 3972 0.454 39.1 15.3 41.8 0.640 110.2
BUY_c1.0_T240 K_OPT3 B tier T3 | 4896345 31399 0.641 0.6 -10.6 3.7 0.627 114.1
BUY_c1.0_T240 K_OPT3 B wick1m iso | 0 1966 NA 35.8 36.1 39.6 0.741 71.6
BUY_c1.0_T240 K_OPT3 B wick1m na | 0 6 NA 129.5 113.6 133.6 0.667 80.2
BUY_c1.0_T240 K_OPT3 B wick1m not | 0 34313 NA 4.9 -8.6 8.0 0.623 115.8
BUY_c1.0_T240 K_OPT3 B year y2024 | 2304866 17631 0.765 52.8 40.3 56.8 0.653 109.1
BUY_c1.0_T240 K_OPT3 B year y2025 | 3642676 18654 0.512 -37.1 -50.1 -34.8 0.608 117.4
BUY_c1.0_T240 K_PESS A condB no | 2988434 19269 0.645 32.7 40.1 43.9 0.606 119.8
BUY_c1.0_T240 K_PESS A condB yes | 283418 5111 1.803 16.0 0.3 26.5 0.644 107.0
BUY_c1.0_T240 K_PESS A hour h0 | 136608 1109 0.812 104.6 57.9 115.9 0.672 114.2
BUY_c1.0_T240 K_PESS A hour h1 | 136358 884 0.648 5.7 25.1 18.1 0.506 138.0
BUY_c1.0_T240 K_PESS A hour h10 | 136344 680 0.499 163.2 121.8 172.7 0.859 54.8
BUY_c1.0_T240 K_PESS A hour h11 | 136231 611 0.449 145.2 125.1 154.6 0.864 65.3
BUY_c1.0_T240 K_PESS A hour h12 | 136350 979 0.718 91.9 77.2 102.5 0.674 109.1
BUY_c1.0_T240 K_PESS A hour h13 | 136358 1275 0.935 122.7 74.5 132.4 0.794 90.7
BUY_c1.0_T240 K_PESS A hour h14 | 136480 1158 0.848 107.3 70.4 115.2 0.784 73.8
BUY_c1.0_T240 K_PESS A hour h15 | 136465 1841 1.349 5.4 43.8 16.5 0.613 112.2
BUY_c1.0_T240 K_PESS A hour h16 | 136566 1168 0.855 3.3 2.5 14.0 0.651 96.6
BUY_c1.0_T240 K_PESS A hour h17 | 136256 1178 0.865 -80.5 -33.4 -68.6 0.563 131.5
BUY_c1.0_T240 K_PESS A hour h18 | 136353 1183 0.868 76.8 55.4 87.0 0.722 89.5
BUY_c1.0_T240 K_PESS A hour h19 | 136234 1485 1.090 -10.8 -9.8 2.2 0.413 158.1
BUY_c1.0_T240 K_PESS A hour h2 | 136422 911 0.668 -6.7 -39.8 5.6 0.544 131.5
BUY_c1.0_T240 K_PESS A hour h20 | 136351 1342 0.984 100.3 80.5 111.0 0.660 102.7
BUY_c1.0_T240 K_PESS A hour h21 | 136217 1342 0.985 -30.7 71.0 -19.6 0.525 141.2
BUY_c1.0_T240 K_PESS A hour h22 | 136111 1173 0.862 35.9 27.4 46.6 0.657 109.5
BUY_c1.0_T240 K_PESS A hour h23 | 136059 729 0.536 53.7 33.4 62.8 0.705 90.5
BUY_c1.0_T240 K_PESS A hour h3 | 136252 575 0.422 -107.4 -53.8 -94.1 0.391 168.4
BUY_c1.0_T240 K_PESS A hour h4 | 136260 786 0.577 -240.0 -131.0 -228.1 0.407 160.0
BUY_c1.0_T240 K_PESS A hour h5 | 136127 679 0.499 43.0 29.6 52.9 0.667 110.2
BUY_c1.0_T240 K_PESS A hour h6 | 136266 412 0.302 78.5 -15.4 88.7 0.507 148.5
BUY_c1.0_T240 K_PESS A hour h7 | 136230 736 0.540 65.5 31.5 75.4 0.747 93.8
BUY_c1.0_T240 K_PESS A hour h8 | 136565 963 0.705 -36.4 17.4 -23.3 0.411 165.8
BUY_c1.0_T240 K_PESS A hour h9 | 136389 1181 0.866 28.2 32.0 41.3 0.453 150.9
BUY_c1.0_T240 K_PESS A mkt idio | 0 4820 NA 10.7 14.6 20.6 0.636 113.4
BUY_c1.0_T240 K_PESS A mkt market | 0 19560 NA 33.7 36.0 45.0 0.608 118.1
BUY_c1.0_T240 K_PESS A qvratio 1_10 | 0 3812 NA 31.5 11.1 42.2 0.643 120.9
BUY_c1.0_T240 K_PESS A qvratio gt10 | 0 20510 NA 28.7 35.7 39.8 0.608 116.5
BUY_c1.0_T240 K_PESS A qvratio lt1 | 0 58 NA 28.9 -12.7 39.6 0.741 109.0
BUY_c1.0_T240 K_PESS A tier T1 | 219092 1209 0.552 59.3 62.1 67.6 0.625 109.8
BUY_c1.0_T240 K_PESS A tier T2 | 1095287 6773 0.618 43.5 45.2 52.9 0.618 114.2
BUY_c1.0_T240 K_PESS A tier T3 | 1957473 16398 0.838 21.0 23.9 32.9 0.611 118.9
BUY_c1.0_T240 K_PESS A wick1m iso | 0 1031 NA 107.0 95.9 118.5 0.611 72.0
BUY_c1.0_T240 K_PESS A wick1m na | 0 3 NA 54.5 57.3 70.2 0.333 162.3
BUY_c1.0_T240 K_PESS A wick1m not | 0 23346 NA 25.7 28.9 36.7 0.614 119.1
BUY_c1.0_T240 K_PESS A year y2021 | 533832 2759 0.517 45.1 87.3 55.0 0.640 106.2
BUY_c1.0_T240 K_PESS A year y2022 | 1190474 7646 0.642 16.0 11.3 27.0 0.598 122.2
BUY_c1.0_T240 K_PESS A year y2023 | 1547546 13975 0.903 33.3 32.0 44.5 0.617 116.5
BUY_c1.0_T240 K_PESS B condB no | 5274788 26695 0.506 -5.6 -10.7 5.4 0.592 118.9
BUY_c1.0_T240 K_PESS B condB yes | 672754 8871 1.319 -10.8 -47.3 0.4 0.628 107.0
BUY_c1.0_T240 K_PESS B hour h0 | 248476 2751 1.107 -111.4 -56.8 -98.6 0.473 146.2
BUY_c1.0_T240 K_PESS B hour h1 | 248133 2051 0.827 -37.5 -33.4 -24.8 0.478 144.7
BUY_c1.0_T240 K_PESS B hour h10 | 247734 800 0.323 85.0 8.2 94.4 0.760 82.1
BUY_c1.0_T240 K_PESS B hour h11 | 247515 929 0.375 -44.8 -39.0 -33.7 0.548 134.2
BUY_c1.0_T240 K_PESS B hour h12 | 247856 1538 0.621 19.9 -1.7 30.9 0.607 110.6
BUY_c1.0_T240 K_PESS B hour h13 | 248119 1402 0.565 57.0 65.5 67.6 0.687 102.7
BUY_c1.0_T240 K_PESS B hour h14 | 248377 1603 0.645 -4.6 -15.6 6.6 0.561 128.9
BUY_c1.0_T240 K_PESS B hour h15 | 248617 2629 1.057 72.7 64.3 83.8 0.622 111.4
BUY_c1.0_T240 K_PESS B hour h16 | 248702 1794 0.721 68.2 75.5 78.8 0.675 98.8
BUY_c1.0_T240 K_PESS B hour h17 | 248455 2632 1.059 3.4 -33.1 15.4 0.591 117.8
BUY_c1.0_T240 K_PESS B hour h18 | 247632 1469 0.593 -0.2 -37.7 11.5 0.583 117.6
BUY_c1.0_T240 K_PESS B hour h19 | 247437 1359 0.549 -9.1 -20.3 4.1 0.442 154.4
BUY_c1.0_T240 K_PESS B hour h2 | 248008 1401 0.565 99.9 63.4 111.1 0.605 117.4
BUY_c1.0_T240 K_PESS B hour h20 | 247711 1678 0.678 -330.9 -328.3 -320.0 0.524 125.3
BUY_c1.0_T240 K_PESS B hour h21 | 247307 1713 0.693 -278.6 -228.0 -267.4 0.532 130.2
BUY_c1.0_T240 K_PESS B hour h22 | 247189 2260 0.914 167.6 116.3 176.6 0.844 52.1
BUY_c1.0_T240 K_PESS B hour h23 | 246684 658 0.267 -50.9 -111.6 -39.7 0.505 137.5
BUY_c1.0_T240 K_PESS B hour h3 | 247701 572 0.231 17.8 -1.5 27.7 0.656 94.0
BUY_c1.0_T240 K_PESS B hour h4 | 247650 540 0.218 -3.7 -27.3 6.8 0.648 105.1
BUY_c1.0_T240 K_PESS B hour h5 | 247405 1036 0.419 79.1 34.8 89.4 0.640 118.3
BUY_c1.0_T240 K_PESS B hour h6 | 247448 1435 0.580 125.8 -3.7 134.6 0.783 79.1
BUY_c1.0_T240 K_PESS B hour h7 | 247509 1217 0.492 32.2 19.2 42.9 0.617 111.4
BUY_c1.0_T240 K_PESS B hour h8 | 248095 1074 0.433 2.4 13.0 14.3 0.510 141.6
BUY_c1.0_T240 K_PESS B hour h9 | 247782 1025 0.414 -66.0 -38.5 -55.7 0.619 108.6
BUY_c1.0_T240 K_PESS B mkt idio | 0 9856 NA -10.7 -15.3 -1.4 0.613 113.4
BUY_c1.0_T240 K_PESS B mkt market | 0 25710 NA -5.5 -21.6 6.3 0.596 117.0
BUY_c1.0_T240 K_PESS B qvratio 1_10 | 0 4273 NA 9.8 7.8 21.4 0.585 136.4
BUY_c1.0_T240 K_PESS B qvratio gt10 | 0 31252 NA -9.1 -23.5 1.9 0.603 113.1
BUY_c1.0_T240 K_PESS B qvratio lt1 | 0 41 NA -83.7 -93.2 -72.0 0.610 138.9
BUY_c1.0_T240 K_PESS B tier T1 | 175370 912 0.520 67.1 46.0 75.3 0.666 103.0
BUY_c1.0_T240 K_PESS B tier T2 | 875827 3930 0.449 31.4 7.1 40.4 0.618 111.3
BUY_c1.0_T240 K_PESS B tier T3 | 4896345 30724 0.628 -14.0 -25.3 -2.6 0.597 116.9
BUY_c1.0_T240 K_PESS B wick1m iso | 0 1972 NA 22.3 23.3 35.2 0.519 74.9
BUY_c1.0_T240 K_PESS B wick1m na | 0 5 NA 117.1 111.9 134.1 0.200 48.8
BUY_c1.0_T240 K_PESS B wick1m not | 0 33589 NA -8.7 -22.4 2.3 0.606 118.4
BUY_c1.0_T240 K_PESS B year y2024 | 2304866 17293 0.750 42.2 29.4 53.9 0.630 111.4
BUY_c1.0_T240 K_PESS B year y2025 | 3642676 18273 0.502 -53.4 -66.5 -42.9 0.573 120.3
BUY_c1.0_T1440 K_OPT3 A condB no | 2988434 19805 0.663 53.7 68.6 56.9 0.795 422.2
BUY_c1.0_T1440 K_OPT3 A condB yes | 283418 5223 1.843 -0.8 27.5 1.1 0.827 362.1
BUY_c1.0_T1440 K_OPT3 A hour h0 | 136608 1149 0.842 102.7 67.7 106.4 0.889 301.0
BUY_c1.0_T1440 K_OPT3 A hour h1 | 136358 911 0.668 -39.7 27.2 -36.0 0.655 587.8
BUY_c1.0_T1440 K_OPT3 A hour h10 | 136344 697 0.511 169.8 131.6 173.9 0.951 122.7
BUY_c1.0_T1440 K_OPT3 A hour h11 | 136231 626 0.460 168.7 155.8 172.3 0.963 141.0
BUY_c1.0_T1440 K_OPT3 A hour h12 | 136350 1002 0.735 64.0 96.9 67.0 0.790 389.9
BUY_c1.0_T1440 K_OPT3 A hour h13 | 136358 1321 0.969 131.8 86.3 135.3 0.924 207.0
BUY_c1.0_T1440 K_OPT3 A hour h14 | 136480 1188 0.870 119.0 93.5 121.2 0.901 228.9
BUY_c1.0_T1440 K_OPT3 A hour h15 | 136465 1909 1.399 49.2 56.8 51.9 0.790 422.7
BUY_c1.0_T1440 K_OPT3 A hour h16 | 136566 1201 0.879 79.8 54.9 82.6 0.882 302.0
BUY_c1.0_T1440 K_OPT3 A hour h17 | 136256 1207 0.886 -117.3 12.7 -115.1 0.716 517.0
BUY_c1.0_T1440 K_OPT3 A hour h18 | 136353 1215 0.891 42.7 66.8 45.3 0.895 239.0
BUY_c1.0_T1440 K_OPT3 A hour h19 | 136234 1504 1.104 3.8 -9.6 6.9 0.724 576.7
BUY_c1.0_T1440 K_OPT3 A hour h2 | 136422 936 0.686 -23.4 -28.7 -19.9 0.737 505.4
BUY_c1.0_T1440 K_OPT3 A hour h20 | 136351 1374 1.008 144.6 125.5 148.0 0.883 328.9
BUY_c1.0_T1440 K_OPT3 A hour h21 | 136217 1362 1.000 -108.8 118.1 -106.4 0.685 573.9
BUY_c1.0_T1440 K_OPT3 A hour h22 | 136111 1195 0.878 98.6 71.6 102.1 0.861 342.1
BUY_c1.0_T1440 K_OPT3 A hour h23 | 136059 747 0.549 48.2 137.9 50.3 0.839 313.8
BUY_c1.0_T1440 K_OPT3 A hour h3 | 136252 600 0.440 73.1 4.1 76.3 0.842 522.1
BUY_c1.0_T1440 K_OPT3 A hour h4 | 136260 798 0.586 -116.1 -45.7 -114.4 0.612 696.5
BUY_c1.0_T1440 K_OPT3 A hour h5 | 136127 695 0.511 137.0 91.6 137.7 0.853 336.7
BUY_c1.0_T1440 K_OPT3 A hour h6 | 136266 430 0.316 27.4 54.1 28.0 0.714 557.1
BUY_c1.0_T1440 K_OPT3 A hour h7 | 136230 765 0.562 102.4 64.5 105.2 0.906 251.7
BUY_c1.0_T1440 K_OPT3 A hour h8 | 136565 981 0.718 -95.1 4.2 -91.8 0.597 708.4
BUY_c1.0_T1440 K_OPT3 A hour h9 | 136389 1215 0.891 35.5 24.7 39.3 0.683 601.5
BUY_c1.0_T1440 K_OPT3 A mkt idio | 0 5021 NA 24.7 27.6 25.8 0.816 380.9
BUY_c1.0_T1440 K_OPT3 A mkt market | 0 20007 NA 46.8 68.1 50.2 0.798 416.9
BUY_c1.0_T1440 K_OPT3 A qvratio 1_10 | 0 3984 NA 39.2 34.8 41.1 0.845 372.5
BUY_c1.0_T1440 K_OPT3 A qvratio gt10 | 0 20988 NA 43.2 65.3 46.4 0.794 417.0
BUY_c1.0_T1440 K_OPT3 A qvratio lt1 | 0 56 NA -61.1 -138.9 -61.0 0.857 310.8
BUY_c1.0_T1440 K_OPT3 A tier T1 | 219092 1215 0.555 48.4 61.2 49.2 0.798 410.8
BUY_c1.0_T1440 K_OPT3 A tier T2 | 1095287 6903 0.630 57.5 74.7 59.5 0.797 412.2
BUY_c1.0_T1440 K_OPT3 A tier T3 | 1957473 16910 0.864 35.7 53.9 39.2 0.804 408.6
BUY_c1.0_T1440 K_OPT3 A wick1m iso | 0 1029 NA 114.6 109.2 118.5 0.886 235.9
BUY_c1.0_T1440 K_OPT3 A wick1m na | 0 4 NA 90.3 59.2 94.5 0.750 461.2
BUY_c1.0_T1440 K_OPT3 A wick1m not | 0 23995 NA 39.3 57.9 42.1 0.798 417.1
BUY_c1.0_T1440 K_OPT3 A year y2021 | 533832 2775 0.520 93.4 120.6 96.0 0.810 396.9
BUY_c1.0_T1440 K_OPT3 A year y2022 | 1190474 7835 0.658 -15.5 37.9 -13.7 0.782 443.5
BUY_c1.0_T1440 K_OPT3 A year y2023 | 1547546 14418 0.932 64.0 60.4 67.6 0.811 393.7
BUY_c1.0_T1440 K_OPT3 B condB no | 5264555 27218 0.517 4.1 -13.7 5.5 0.780 445.0
BUY_c1.0_T1440 K_OPT3 B condB yes | 672754 8997 1.337 100.7 11.1 103.7 0.865 345.8
BUY_c1.0_T1440 K_OPT3 B hour h0 | 247962 2798 1.128 78.6 -4.1 80.4 0.716 631.5
BUY_c1.0_T1440 K_OPT3 B hour h1 | 247620 2085 0.842 98.4 7.4 101.2 0.813 522.7
BUY_c1.0_T1440 K_OPT3 B hour h10 | 247219 812 0.328 106.5 20.6 106.3 0.878 261.9
BUY_c1.0_T1440 K_OPT3 B hour h11 | 247000 952 0.385 -76.9 -79.8 -75.2 0.638 594.1
BUY_c1.0_T1440 K_OPT3 B hour h12 | 247337 1565 0.633 60.5 14.4 61.9 0.726 481.7
BUY_c1.0_T1440 K_OPT3 B hour h13 | 247602 1453 0.587 105.0 103.3 107.5 0.884 305.5
BUY_c1.0_T1440 K_OPT3 B hour h14 | 247864 1667 0.673 0.1 7.7 1.6 0.735 502.6
BUY_c1.0_T1440 K_OPT3 B hour h15 | 248107 2688 1.083 -61.3 -14.1 -59.4 0.789 410.3
BUY_c1.0_T1440 K_OPT3 B hour h16 | 248182 1802 0.726 75.7 72.7 77.4 0.848 322.9
BUY_c1.0_T1440 K_OPT3 B hour h17 | 247936 2672 1.078 30.6 -46.1 34.5 0.848 392.8
BUY_c1.0_T1440 K_OPT3 B hour h18 | 247632 1495 0.604 -81.8 -121.5 -78.8 0.718 498.4
BUY_c1.0_T1440 K_OPT3 B hour h19 | 247437 1396 0.564 141.0 101.8 143.6 0.869 435.9
BUY_c1.0_T1440 K_OPT3 B hour h2 | 247494 1416 0.572 136.8 66.4 140.2 0.811 410.9
BUY_c1.0_T1440 K_OPT3 B hour h20 | 247711 1696 0.685 -430.8 -323.9 -429.8 0.644 568.0
BUY_c1.0_T1440 K_OPT3 B hour h21 | 247307 1742 0.704 -167.5 -190.7 -166.0 0.759 484.2
BUY_c1.0_T1440 K_OPT3 B hour h22 | 246673 2292 0.929 201.4 164.7 204.5 0.953 149.5
BUY_c1.0_T1440 K_OPT3 B hour h23 | 246180 677 0.275 43.0 -57.5 43.7 0.687 559.1
BUY_c1.0_T1440 K_OPT3 B hour h3 | 247202 575 0.233 43.7 14.8 44.5 0.831 345.8
BUY_c1.0_T1440 K_OPT3 B hour h4 | 247143 559 0.226 4.2 -18.3 4.0 0.810 367.0
BUY_c1.0_T1440 K_OPT3 B hour h5 | 246893 1060 0.429 127.7 67.5 128.5 0.894 288.3
BUY_c1.0_T1440 K_OPT3 B hour h6 | 246945 1447 0.586 138.3 6.8 138.4 0.877 247.5
BUY_c1.0_T1440 K_OPT3 B hour h7 | 247003 1234 0.500 104.2 39.3 105.0 0.845 353.0
BUY_c1.0_T1440 K_OPT3 B hour h8 | 247590 1083 0.437 97.6 53.0 97.8 0.861 367.0
BUY_c1.0_T1440 K_OPT3 B hour h9 | 247270 1049 0.424 -53.5 -67.9 -53.9 0.770 431.3
BUY_c1.0_T1440 K_OPT3 B mkt idio | 0 10013 NA 17.9 8.2 15.6 0.802 404.8
BUY_c1.0_T1440 K_OPT3 B mkt market | 0 26202 NA 32.0 -13.6 35.4 0.800 426.3
BUY_c1.0_T1440 K_OPT3 B qvratio 1_10 | 0 4441 NA 93.2 41.0 95.5 0.849 396.7
BUY_c1.0_T1440 K_OPT3 B qvratio gt10 | 0 31733 NA 19.1 -14.3 20.8 0.794 423.7
BUY_c1.0_T1440 K_OPT3 B qvratio lt1 | 0 41 NA -40.4 -46.2 -36.5 0.829 386.4
BUY_c1.0_T1440 K_OPT3 B tier T1 | 175170 913 0.521 89.8 41.4 91.2 0.835 367.8
BUY_c1.0_T1440 K_OPT3 B tier T2 | 874828 3968 0.454 56.1 2.9 55.7 0.806 409.0
BUY_c1.0_T1440 K_OPT3 B tier T3 | 4887311 31334 0.641 22.7 -10.3 24.9 0.799 423.3
BUY_c1.0_T1440 K_OPT3 B wick1m iso | 0 1957 NA 48.3 39.3 51.5 0.840 302.1
BUY_c1.0_T1440 K_OPT3 B wick1m na | 0 5 NA 237.1 210.9 241.5 1.000 229.2
BUY_c1.0_T1440 K_OPT3 B wick1m not | 0 34253 NA 26.9 -10.3 28.6 0.799 427.1
BUY_c1.0_T1440 K_OPT3 B year y2024 | 2304866 17630 0.765 67.3 33.0 71.1 0.823 383.8
BUY_c1.0_T1440 K_OPT3 B year y2025 | 3632443 18585 0.512 -9.1 -46.1 -9.2 0.780 454.9
BUY_c1.0_T1440 K_PESS A condB no | 2988434 19263 0.645 43.8 59.0 53.0 0.773 439.4
BUY_c1.0_T1440 K_PESS A condB yes | 283418 5111 1.803 -17.5 14.6 -10.1 0.801 378.6
BUY_c1.0_T1440 K_PESS A hour h0 | 136608 1109 0.812 96.6 60.6 105.5 0.875 314.4
BUY_c1.0_T1440 K_PESS A hour h1 | 136358 884 0.648 -59.2 10.5 -48.2 0.624 615.9
BUY_c1.0_T1440 K_PESS A hour h10 | 136344 680 0.499 162.0 121.0 171.1 0.903 132.2
BUY_c1.0_T1440 K_PESS A hour h11 | 136231 611 0.449 163.8 149.6 171.7 0.959 147.6
BUY_c1.0_T1440 K_PESS A hour h12 | 136350 979 0.718 50.3 85.4 59.3 0.769 404.2
BUY_c1.0_T1440 K_PESS A hour h13 | 136358 1274 0.934 127.4 78.5 135.9 0.893 219.9
BUY_c1.0_T1440 K_PESS A hour h14 | 136480 1158 0.848 112.8 85.6 119.9 0.879 238.0
BUY_c1.0_T1440 K_PESS A hour h15 | 136465 1840 1.348 38.7 47.5 47.4 0.765 442.6
BUY_c1.0_T1440 K_PESS A hour h16 | 136566 1164 0.852 70.7 44.1 78.6 0.852 311.7
BUY_c1.0_T1440 K_PESS A hour h17 | 136256 1178 0.865 -144.0 -1.7 -135.1 0.672 539.6
BUY_c1.0_T1440 K_PESS A hour h18 | 136353 1183 0.868 24.1 53.4 31.9 0.856 257.8
BUY_c1.0_T1440 K_PESS A hour h19 | 136234 1485 1.090 -7.6 -22.4 2.0 0.711 592.9
BUY_c1.0_T1440 K_PESS A hour h2 | 136422 911 0.668 -35.5 -43.2 -25.3 0.718 531.4
BUY_c1.0_T1440 K_PESS A hour h20 | 136351 1342 0.984 138.0 119.1 146.7 0.865 347.0
BUY_c1.0_T1440 K_PESS A hour h21 | 136217 1342 0.985 -121.3 109.3 -112.1 0.668 591.1
BUY_c1.0_T1440 K_PESS A hour h22 | 136111 1173 0.862 92.0 64.0 100.8 0.848 353.7
BUY_c1.0_T1440 K_PESS A hour h23 | 136059 729 0.536 41.3 131.5 48.7 0.823 324.3
BUY_c1.0_T1440 K_PESS A hour h3 | 136252 575 0.422 60.5 -9.3 69.1 0.830 544.4
BUY_c1.0_T1440 K_PESS A hour h4 | 136260 786 0.577 -129.5 -58.6 -120.3 0.597 709.1
BUY_c1.0_T1440 K_PESS A hour h5 | 136127 679 0.499 129.4 83.1 135.5 0.834 353.0
BUY_c1.0_T1440 K_PESS A hour h6 | 136266 412 0.302 4.2 39.6 11.2 0.699 562.3
BUY_c1.0_T1440 K_PESS A hour h7 | 136230 736 0.540 94.8 56.7 102.9 0.894 269.5
BUY_c1.0_T1440 K_PESS A hour h8 | 136565 963 0.705 -104.6 -3.7 -93.9 0.588 720.8
BUY_c1.0_T1440 K_PESS A hour h9 | 136389 1181 0.866 21.9 11.3 32.8 0.652 632.6
BUY_c1.0_T1440 K_PESS A mkt idio | 0 4819 NA 12.5 16.0 19.4 0.789 397.8
BUY_c1.0_T1440 K_PESS A mkt market | 0 19555 NA 35.5 58.0 44.8 0.777 433.7
BUY_c1.0_T1440 K_PESS A qvratio 1_10 | 0 3812 NA 21.4 20.5 28.6 0.836 388.2
BUY_c1.0_T1440 K_PESS A qvratio gt10 | 0 20504 NA 32.7 55.5 41.9 0.768 434.2
BUY_c1.0_T1440 K_PESS A qvratio lt1 | 0 58 NA 17.1 -103.5 22.3 0.879 278.8
BUY_c1.0_T1440 K_PESS A tier T1 | 219092 1209 0.552 43.2 55.8 48.7 0.779 415.0
BUY_c1.0_T1440 K_PESS A tier T2 | 1095287 6770 0.618 48.3 66.0 55.6 0.775 425.2
BUY_c1.0_T1440 K_PESS A tier T3 | 1957473 16395 0.838 22.9 42.5 32.6 0.781 428.1
BUY_c1.0_T1440 K_PESS A wick1m iso | 0 1031 NA 105.2 98.4 115.7 0.709 251.0
BUY_c1.0_T1440 K_PESS A wick1m na | 0 3 NA 54.8 63.8 67.1 0.667 598.7
BUY_c1.0_T1440 K_PESS A wick1m not | 0 23340 NA 27.6 47.5 36.4 0.782 434.4
BUY_c1.0_T1440 K_PESS A year y2021 | 533832 2759 0.517 86.1 113.8 94.4 0.793 401.3
BUY_c1.0_T1440 K_PESS A year y2022 | 1190474 7640 0.642 -30.9 26.2 -23.3 0.768 461.0
BUY_c1.0_T1440 K_PESS A year y2023 | 1547546 13975 0.903 53.8 49.8 63.4 0.783 412.8
BUY_c1.0_T1440 K_PESS B condB no | 5264555 26629 0.506 -9.4 -27.6 -1.6 0.754 457.1
BUY_c1.0_T1440 K_PESS B condB yes | 672754 8871 1.319 91.6 0.9 100.2 0.842 355.7
BUY_c1.0_T1440 K_PESS B hour h0 | 247962 2747 1.108 70.2 -14.8 79.0 0.708 641.3
BUY_c1.0_T1440 K_PESS B hour h1 | 247620 2050 0.828 88.3 -4.9 97.0 0.794 536.8
BUY_c1.0_T1440 K_PESS B hour h10 | 247219 799 0.323 101.2 14.0 106.4 0.855 266.2
BUY_c1.0_T1440 K_PESS B hour h11 | 247000 929 0.376 -87.6 -91.2 -78.3 0.617 605.2
BUY_c1.0_T1440 K_PESS B hour h12 | 247337 1537 0.621 46.9 0.1 55.3 0.693 503.3
BUY_c1.0_T1440 K_PESS B hour h13 | 247602 1401 0.566 90.6 91.9 98.4 0.866 322.3
BUY_c1.0_T1440 K_PESS B hour h14 | 247864 1602 0.646 -9.1 -6.2 -1.0 0.723 507.8
BUY_c1.0_T1440 K_PESS B hour h15 | 248107 2627 1.059 -79.5 -30.4 -71.5 0.772 425.2
BUY_c1.0_T1440 K_PESS B hour h16 | 248182 1760 0.709 64.5 61.4 71.7 0.832 332.9
BUY_c1.0_T1440 K_PESS B hour h17 | 247936 2630 1.061 20.2 -58.5 29.6 0.830 407.5
BUY_c1.0_T1440 K_PESS B hour h18 | 247632 1469 0.593 -99.7 -140.0 -89.8 0.685 507.1
BUY_c1.0_T1440 K_PESS B hour h19 | 247437 1359 0.549 134.3 94.5 142.3 0.859 446.7
BUY_c1.0_T1440 K_PESS B hour h2 | 247494 1401 0.566 128.0 58.3 137.5 0.795 423.0
BUY_c1.0_T1440 K_PESS B hour h20 | 247711 1678 0.678 -450.5 -342.6 -441.9 0.574 578.4
BUY_c1.0_T1440 K_PESS B hour h21 | 247307 1713 0.693 -184.7 -205.2 -176.8 0.723 497.4
BUY_c1.0_T1440 K_PESS B hour h22 | 246673 2259 0.916 194.1 158.0 202.1 0.915 152.9
BUY_c1.0_T1440 K_PESS B hour h23 | 246180 658 0.267 33.2 -71.2 41.4 0.649 571.8
BUY_c1.0_T1440 K_PESS B hour h3 | 247202 570 0.231 35.0 4.8 41.9 0.788 350.5
BUY_c1.0_T1440 K_PESS B hour h4 | 247143 536 0.217 -18.4 -39.2 -12.7 0.776 388.5
BUY_c1.0_T1440 K_PESS B hour h5 | 246893 1033 0.418 118.5 56.5 124.4 0.874 297.1
BUY_c1.0_T1440 K_PESS B hour h6 | 246945 1432 0.580 129.4 -5.4 135.1 0.851 255.7
BUY_c1.0_T1440 K_PESS B hour h7 | 247003 1216 0.492 92.1 25.9 98.7 0.818 366.6
BUY_c1.0_T1440 K_PESS B hour h8 | 247590 1070 0.432 85.5 41.0 91.2 0.839 377.4
BUY_c1.0_T1440 K_PESS B hour h9 | 247270 1024 0.414 -75.3 -90.5 -69.2 0.741 446.4
BUY_c1.0_T1440 K_PESS B mkt idio | 0 9826 NA 3.9 -5.9 7.8 0.766 414.6
BUY_c1.0_T1440 K_PESS B mkt market | 0 25674 NA 20.4 -26.1 29.9 0.780 438.3
BUY_c1.0_T1440 K_PESS B qvratio 1_10 | 0 4269 NA 84.2 30.9 92.1 0.842 405.5
BUY_c1.0_T1440 K_PESS B qvratio gt10 | 0 31190 NA 6.5 -27.5 14.5 0.767 435.4
BUY_c1.0_T1440 K_PESS B qvratio lt1 | 0 41 NA -1.1 -55.1 7.8 0.878 374.7
BUY_c1.0_T1440 K_PESS B tier T1 | 175170 911 0.520 85.6 36.7 91.5 0.827 367.2
BUY_c1.0_T1440 K_PESS B tier T2 | 874828 3926 0.449 49.3 -4.6 54.1 0.787 414.3
BUY_c1.0_T1440 K_PESS B tier T3 | 4887311 30663 0.627 9.5 -24.2 17.9 0.774 435.9
BUY_c1.0_T1440 K_PESS B wick1m iso | 0 1964 NA 36.6 26.5 47.8 0.626 314.5
BUY_c1.0_T1440 K_PESS B wick1m na | 0 4 NA 219.5 212.1 236.5 0.250 203.8
BUY_c1.0_T1440 K_PESS B wick1m not | 0 33532 NA 14.6 -23.3 22.4 0.785 438.6
BUY_c1.0_T1440 K_PESS B year y2024 | 2304866 17292 0.750 57.9 22.5 67.6 0.805 393.0
BUY_c1.0_T1440 K_PESS B year y2025 | 3632443 18208 0.501 -24.0 -61.3 -17.8 0.749 468.5
BUY_c1.5_T240 K_OPT3 A condB no | 2988434 6257 0.209 95.3 95.8 98.4 0.612 114.9
BUY_c1.5_T240 K_OPT3 A condB yes | 283418 2285 0.806 93.5 66.9 96.8 0.604 120.9
BUY_c1.5_T240 K_OPT3 A hour h0 | 136608 254 0.186 198.1 146.2 202.2 0.839 85.6
BUY_c1.5_T240 K_OPT3 A hour h1 | 136358 334 0.245 102.9 83.8 106.9 0.263 194.5
BUY_c1.5_T240 K_OPT3 A hour h10 | 136344 156 0.114 283.9 252.5 288.0 0.904 41.9
BUY_c1.5_T240 K_OPT3 A hour h11 | 136231 172 0.126 282.7 282.3 286.8 0.919 39.1
BUY_c1.5_T240 K_OPT3 A hour h12 | 136350 376 0.276 291.7 250.6 294.6 0.766 82.4
BUY_c1.5_T240 K_OPT3 A hour h13 | 136358 338 0.248 271.2 163.1 275.2 0.941 72.1
BUY_c1.5_T240 K_OPT3 A hour h14 | 136480 295 0.216 21.1 172.2 17.1 0.634 101.1
BUY_c1.5_T240 K_OPT3 A hour h15 | 136465 703 0.515 40.5 70.6 43.9 0.560 122.9
BUY_c1.5_T240 K_OPT3 A hour h16 | 136566 478 0.350 13.3 2.1 17.2 0.615 103.2
BUY_c1.5_T240 K_OPT3 A hour h17 | 136256 521 0.382 -14.6 37.0 -10.6 0.614 113.0
BUY_c1.5_T240 K_OPT3 A hour h18 | 136353 470 0.345 138.5 89.9 142.6 0.828 62.8
BUY_c1.5_T240 K_OPT3 A hour h19 | 136234 653 0.479 109.5 30.5 113.5 0.473 146.7
BUY_c1.5_T240 K_OPT3 A hour h2 | 136422 296 0.217 124.9 -66.2 129.0 0.436 153.0
BUY_c1.5_T240 K_OPT3 A hour h20 | 136351 355 0.260 179.2 154.1 181.2 0.704 98.8
BUY_c1.5_T240 K_OPT3 A hour h21 | 136217 691 0.507 105.4 169.0 108.0 0.580 132.3
BUY_c1.5_T240 K_OPT3 A hour h22 | 136111 378 0.278 -8.5 -3.0 -5.5 0.537 133.2
BUY_c1.5_T240 K_OPT3 A hour h23 | 136059 194 0.143 106.0 113.9 107.7 0.670 97.4
BUY_c1.5_T240 K_OPT3 A hour h3 | 136252 67 0.049 -129.1 -120.2 -125.3 0.269 190.5
BUY_c1.5_T240 K_OPT3 A hour h4 | 136260 416 0.305 -293.4 -142.2 -291.1 0.377 159.6
BUY_c1.5_T240 K_OPT3 A hour h5 | 136127 186 0.137 293.0 272.7 294.3 0.796 77.5
BUY_c1.5_T240 K_OPT3 A hour h6 | 136266 128 0.094 145.6 7.5 146.3 0.562 133.1
BUY_c1.5_T240 K_OPT3 A hour h7 | 136230 128 0.094 161.6 136.4 162.9 0.828 63.9
BUY_c1.5_T240 K_OPT3 A hour h8 | 136565 511 0.374 102.7 139.0 106.7 0.468 143.8
BUY_c1.5_T240 K_OPT3 A hour h9 | 136389 442 0.324 124.0 48.7 128.0 0.577 128.9
BUY_c1.5_T240 K_OPT3 A mkt idio | 0 1138 NA 80.2 81.0 81.8 0.701 97.0
BUY_c1.5_T240 K_OPT3 A mkt market | 0 7404 NA 97.1 89.2 100.4 0.595 119.5
BUY_c1.5_T240 K_OPT3 A qvratio 1_10 | 0 548 NA 184.9 99.6 186.7 0.717 111.6
BUY_c1.5_T240 K_OPT3 A qvratio gt10 | 0 7989 NA 88.8 87.3 92.0 0.602 116.8
BUY_c1.5_T240 K_OPT3 A qvratio lt1 | 0 5 NA -117.6 172.8 -113.6 0.600 141.4
BUY_c1.5_T240 K_OPT3 A tier T1 | 219092 411 0.188 169.9 156.3 172.6 0.669 104.7
BUY_c1.5_T240 K_OPT3 A tier T2 | 1095287 2344 0.214 124.1 119.2 126.6 0.611 114.3
BUY_c1.5_T240 K_OPT3 A tier T3 | 1957473 5787 0.296 77.7 70.6 81.1 0.605 118.3
BUY_c1.5_T240 K_OPT3 A wick1m iso | 0 385 NA 199.8 187.5 203.8 0.818 58.3
BUY_c1.5_T240 K_OPT3 A wick1m na | 0 1 NA 132.7 132.7 136.8 1.000 0.0
BUY_c1.5_T240 K_OPT3 A wick1m not | 0 8156 NA 89.9 83.4 93.0 0.600 119.3
BUY_c1.5_T240 K_OPT3 A year y2021 | 533832 1020 0.191 176.4 240.3 177.3 0.679 93.1
BUY_c1.5_T240 K_OPT3 A year y2022 | 1190474 2073 0.174 83.5 53.0 86.5 0.590 122.1
BUY_c1.5_T240 K_OPT3 A year y2023 | 1547546 5449 0.352 83.9 73.0 87.4 0.604 118.8
BUY_c1.5_T240 K_OPT3 B condB no | 5274803 8155 0.155 55.8 35.8 58.0 0.647 105.7
BUY_c1.5_T240 K_OPT3 B condB yes | 672754 4542 0.675 93.7 17.0 97.0 0.668 96.7
BUY_c1.5_T240 K_OPT3 B hour h0 | 248476 595 0.239 17.5 58.2 20.9 0.519 127.6
BUY_c1.5_T240 K_OPT3 B hour h1 | 248133 979 0.395 51.7 -8.2 55.3 0.407 160.6
BUY_c1.5_T240 K_OPT3 B hour h10 | 247734 277 0.112 90.4 16.1 92.1 0.780 67.8
BUY_c1.5_T240 K_OPT3 B hour h11 | 247516 207 0.084 -81.2 -78.1 -81.5 0.527 133.7
BUY_c1.5_T240 K_OPT3 B hour h12 | 247857 698 0.282 168.8 90.3 172.0 0.698 87.5
BUY_c1.5_T240 K_OPT3 B hour h13 | 248120 278 0.112 96.2 72.8 98.8 0.662 106.7
BUY_c1.5_T240 K_OPT3 B hour h14 | 248378 274 0.110 -42.6 -41.7 -46.3 0.515 141.7
BUY_c1.5_T240 K_OPT3 B hour h15 | 248618 602 0.242 179.3 169.6 181.5 0.761 72.8
BUY_c1.5_T240 K_OPT3 B hour h16 | 248703 424 0.170 138.8 137.5 140.9 0.762 74.0
BUY_c1.5_T240 K_OPT3 B hour h17 | 248456 929 0.374 61.0 26.5 64.9 0.618 108.4
BUY_c1.5_T240 K_OPT3 B hour h18 | 247633 767 0.310 128.8 88.5 132.4 0.598 115.7
BUY_c1.5_T240 K_OPT3 B hour h19 | 247438 581 0.235 95.6 69.7 98.4 0.375 185.4
BUY_c1.5_T240 K_OPT3 B hour h2 | 248008 661 0.267 292.7 242.9 295.9 0.732 88.3
BUY_c1.5_T240 K_OPT3 B hour h20 | 247713 865 0.350 -457.4 -415.6 -455.4 0.519 135.7
BUY_c1.5_T240 K_OPT3 B hour h21 | 247309 939 0.380 -201.4 -221.7 -199.5 0.637 101.0
BUY_c1.5_T240 K_OPT3 B hour h22 | 247190 822 0.333 297.3 238.1 300.9 0.921 31.4
BUY_c1.5_T240 K_OPT3 B hour h23 | 246685 349 0.141 208.0 53.8 210.3 0.656 131.5
BUY_c1.5_T240 K_OPT3 B hour h3 | 247701 152 0.061 -68.5 -87.8 -65.4 0.658 105.1
BUY_c1.5_T240 K_OPT3 B hour h4 | 247650 150 0.061 12.0 1.9 12.4 0.607 121.2
BUY_c1.5_T240 K_OPT3 B hour h5 | 247405 178 0.072 67.5 44.6 64.7 0.674 109.4
BUY_c1.5_T240 K_OPT3 B hour h6 | 247448 801 0.324 249.5 61.8 252.3 0.900 43.3
BUY_c1.5_T240 K_OPT3 B hour h7 | 247509 695 0.281 256.2 208.2 259.4 0.858 49.8
BUY_c1.5_T240 K_OPT3 B hour h8 | 248095 258 0.104 -7.3 -12.6 -5.0 0.578 122.0
BUY_c1.5_T240 K_OPT3 B hour h9 | 247782 216 0.087 -20.9 -18.2 -20.1 0.662 106.6
BUY_c1.5_T240 K_OPT3 B mkt idio | 0 3113 NA 2.0 -4.3 1.6 0.631 111.2
BUY_c1.5_T240 K_OPT3 B mkt market | 0 9584 NA 91.2 40.0 94.8 0.662 99.7
BUY_c1.5_T240 K_OPT3 B qvratio 1_10 | 0 404 NA 134.5 92.4 135.8 0.626 124.6
BUY_c1.5_T240 K_OPT3 B qvratio gt10 | 0 12289 NA 67.2 27.0 69.9 0.656 101.7
BUY_c1.5_T240 K_OPT3 B qvratio lt1 | 0 4 NA -20.5 -0.8 -16.5 0.500 177.0
BUY_c1.5_T240 K_OPT3 B tier T1 | 175370 300 0.171 199.2 131.4 201.4 0.763 82.0
BUY_c1.5_T240 K_OPT3 B tier T2 | 875827 1404 0.160 141.8 77.2 143.2 0.680 97.9
BUY_c1.5_T240 K_OPT3 B tier T3 | 4896360 10993 0.225 56.6 20.2 59.3 0.649 103.6
BUY_c1.5_T240 K_OPT3 B wick1m iso | 0 1005 NA 183.2 163.3 187.1 0.815 54.2
BUY_c1.5_T240 K_OPT3 B wick1m na | 0 5 NA 261.7 256.2 265.8 0.800 48.0
BUY_c1.5_T240 K_OPT3 B wick1m not | 0 11687 NA 59.5 17.5 62.0 0.641 106.7
BUY_c1.5_T240 K_OPT3 B year y2024 | 2304866 6316 0.274 174.0 130.3 177.9 0.667 103.1
BUY_c1.5_T240 K_OPT3 B year y2025 | 3642691 6381 0.175 -34.3 -71.1 -32.9 0.643 101.9
BUY_c1.5_T240 K_PESS A condB no | 2988434 6137 0.205 84.6 85.2 95.5 0.582 117.9
BUY_c1.5_T240 K_PESS A condB yes | 283418 2270 0.801 83.4 55.7 94.4 0.584 123.1
BUY_c1.5_T240 K_PESS A hour h0 | 136608 245 0.179 192.2 139.3 202.0 0.824 89.2
BUY_c1.5_T240 K_PESS A hour h1 | 136358 329 0.241 90.3 71.6 105.7 0.234 197.6
BUY_c1.5_T240 K_PESS A hour h10 | 136344 155 0.114 279.0 246.7 288.3 0.884 42.2
BUY_c1.5_T240 K_PESS A hour h11 | 136231 170 0.125 276.3 275.6 285.4 0.912 40.1
BUY_c1.5_T240 K_PESS A hour h12 | 136350 373 0.274 284.3 241.6 293.6 0.743 83.3
BUY_c1.5_T240 K_PESS A hour h13 | 136358 332 0.243 266.5 155.9 275.7 0.877 75.7
BUY_c1.5_T240 K_PESS A hour h14 | 136480 288 0.211 9.5 164.2 12.5 0.608 103.6
BUY_c1.5_T240 K_PESS A hour h15 | 136465 694 0.509 29.1 62.6 40.8 0.530 125.0
BUY_c1.5_T240 K_PESS A hour h16 | 136566 470 0.344 1.3 -10.8 13.2 0.589 105.9
BUY_c1.5_T240 K_PESS A hour h17 | 136256 513 0.376 -22.2 27.5 -10.5 0.593 113.7
BUY_c1.5_T240 K_PESS A hour h18 | 136353 464 0.340 127.6 75.2 137.5 0.795 67.2
BUY_c1.5_T240 K_PESS A hour h19 | 136234 642 0.471 96.3 16.3 109.6 0.447 150.7
BUY_c1.5_T240 K_PESS A hour h2 | 136422 291 0.213 114.0 -79.7 128.0 0.409 155.2
BUY_c1.5_T240 K_PESS A hour h20 | 136351 341 0.250 171.5 147.3 180.3 0.669 102.1
BUY_c1.5_T240 K_PESS A hour h21 | 136217 687 0.504 95.8 156.3 106.3 0.559 133.7
BUY_c1.5_T240 K_PESS A hour h22 | 136111 367 0.270 -28.8 -22.0 -17.5 0.499 140.5
BUY_c1.5_T240 K_PESS A hour h23 | 136059 188 0.138 95.5 104.0 104.4 0.649 100.6
BUY_c1.5_T240 K_PESS A hour h3 | 136252 65 0.048 -143.6 -137.5 -129.4 0.277 189.0
BUY_c1.5_T240 K_PESS A hour h4 | 136260 413 0.303 -307.4 -155.1 -295.5 0.366 161.3
BUY_c1.5_T240 K_PESS A hour h5 | 136127 186 0.137 287.1 266.4 294.3 0.790 77.5
BUY_c1.5_T240 K_PESS A hour h6 | 136266 127 0.093 132.6 1.2 141.4 0.528 138.5
BUY_c1.5_T240 K_PESS A hour h7 | 136230 124 0.091 152.9 127.0 160.3 0.790 68.2
BUY_c1.5_T240 K_PESS A hour h8 | 136565 507 0.371 92.0 128.4 104.9 0.460 145.7
BUY_c1.5_T240 K_PESS A hour h9 | 136389 436 0.320 112.8 36.1 125.3 0.525 133.5
BUY_c1.5_T240 K_PESS A mkt idio | 0 1113 NA 69.7 70.7 78.3 0.659 99.4
BUY_c1.5_T240 K_PESS A mkt market | 0 7294 NA 86.5 78.2 97.8 0.571 122.3
BUY_c1.5_T240 K_PESS A qvratio 1_10 | 0 549 NA 175.3 89.9 183.6 0.701 113.3
BUY_c1.5_T240 K_PESS A qvratio gt10 | 0 7854 NA 78.1 76.3 89.2 0.574 119.7
BUY_c1.5_T240 K_PESS A qvratio lt1 | 0 4 NA -299.6 67.8 -275.9 0.500 174.8
BUY_c1.5_T240 K_PESS A tier T1 | 219092 410 0.187 163.5 152.2 171.4 0.644 105.8
BUY_c1.5_T240 K_PESS A tier T2 | 1095287 2315 0.211 115.6 110.2 124.6 0.588 116.3
BUY_c1.5_T240 K_PESS A tier T3 | 1957473 5682 0.290 65.8 58.4 77.7 0.576 121.5
BUY_c1.5_T240 K_PESS A wick1m iso | 0 385 NA 191.7 178.0 203.3 0.613 60.1
BUY_c1.5_T240 K_PESS A wick1m na | 0 1 NA 117.6 117.6 136.8 0.000 1.0
BUY_c1.5_T240 K_PESS A wick1m not | 0 8021 NA 79.1 72.4 90.0 0.581 122.1
BUY_c1.5_T240 K_PESS A year y2021 | 533832 1020 0.191 169.4 235.2 177.3 0.660 93.2
BUY_c1.5_T240 K_PESS A year y2022 | 1190474 2037 0.171 71.9 39.9 82.6 0.572 124.9
BUY_c1.5_T240 K_PESS A year y2023 | 1547546 5350 0.346 72.7 61.3 84.3 0.572 122.1
BUY_c1.5_T240 K_PESS B condB no | 5274803 8029 0.152 43.9 23.6 54.0 0.608 107.1
BUY_c1.5_T240 K_PESS B condB yes | 672754 4510 0.670 82.6 5.6 93.6 0.641 98.4
BUY_c1.5_T240 K_PESS B hour h0 | 248476 573 0.231 1.2 45.1 13.5 0.497 130.5
BUY_c1.5_T240 K_PESS B hour h1 | 248133 976 0.393 37.0 -22.9 51.0 0.378 162.5
BUY_c1.5_T240 K_PESS B hour h10 | 247734 273 0.110 80.9 5.3 89.1 0.762 68.4
BUY_c1.5_T240 K_PESS B hour h11 | 247516 202 0.082 -93.2 -90.5 -84.2 0.485 135.9
BUY_c1.5_T240 K_PESS B hour h12 | 247857 692 0.279 159.0 81.2 169.7 0.658 90.0
BUY_c1.5_T240 K_PESS B hour h13 | 248120 274 0.110 85.6 62.0 96.0 0.620 107.9
BUY_c1.5_T240 K_PESS B hour h14 | 248378 268 0.108 -53.6 -53.7 -48.1 0.489 142.0
BUY_c1.5_T240 K_PESS B hour h15 | 248618 585 0.235 169.1 160.0 178.0 0.735 73.2
BUY_c1.5_T240 K_PESS B hour h16 | 248703 416 0.167 130.4 129.5 139.4 0.714 75.0
BUY_c1.5_T240 K_PESS B hour h17 | 248456 911 0.367 48.6 13.8 60.5 0.595 111.1
BUY_c1.5_T240 K_PESS B hour h18 | 247633 763 0.308 118.4 77.7 130.5 0.554 116.8
BUY_c1.5_T240 K_PESS B hour h19 | 247438 577 0.233 83.0 56.7 96.7 0.359 186.3
BUY_c1.5_T240 K_PESS B hour h2 | 248008 656 0.265 285.2 235.1 295.4 0.716 89.1
BUY_c1.5_T240 K_PESS B hour h20 | 247713 858 0.347 -477.4 -435.1 -466.6 0.456 136.8
BUY_c1.5_T240 K_PESS B hour h21 | 247309 932 0.377 -213.3 -234.7 -203.5 0.578 101.8
BUY_c1.5_T240 K_PESS B hour h22 | 247190 817 0.331 290.6 232.1 299.5 0.884 32.5
BUY_c1.5_T240 K_PESS B hour h23 | 246685 346 0.140 199.5 43.8 209.7 0.633 134.2
BUY_c1.5_T240 K_PESS B hour h3 | 247701 152 0.061 -76.5 -96.7 -65.4 0.612 105.8
BUY_c1.5_T240 K_PESS B hour h4 | 247650 147 0.059 -15.2 -25.2 -5.6 0.544 126.7
BUY_c1.5_T240 K_PESS B hour h5 | 247405 171 0.069 52.9 31.3 57.6 0.620 109.8
BUY_c1.5_T240 K_PESS B hour h6 | 247448 793 0.320 241.6 50.5 249.6 0.883 44.9
BUY_c1.5_T240 K_PESS B hour h7 | 247509 691 0.279 248.4 199.1 257.6 0.835 51.3
BUY_c1.5_T240 K_PESS B hour h8 | 248095 253 0.102 -26.0 -31.2 -14.5 0.530 124.3
BUY_c1.5_T240 K_PESS B hour h9 | 247782 213 0.086 -32.9 -31.5 -23.7 0.587 107.6
BUY_c1.5_T240 K_PESS B mkt idio | 0 3069 NA -10.2 -16.8 -2.2 0.579 112.3
BUY_c1.5_T240 K_PESS B mkt market | 0 9470 NA 79.8 28.1 91.0 0.633 101.3
BUY_c1.5_T240 K_PESS B qvratio 1_10 | 0 390 NA 124.7 84.9 133.9 0.618 125.8
BUY_c1.5_T240 K_PESS B qvratio gt10 | 0 12146 NA 55.7 14.9 66.1 0.620 103.3
BUY_c1.5_T240 K_PESS B qvratio lt1 | 0 3 NA 77.5 66.9 89.1 0.667 156.0
BUY_c1.5_T240 K_PESS B tier T1 | 175370 298 0.170 193.4 125.1 200.4 0.752 82.6
BUY_c1.5_T240 K_PESS B tier T2 | 875827 1391 0.159 133.3 68.4 140.7 0.649 98.7
BUY_c1.5_T240 K_PESS B tier T3 | 4896360 10850 0.222 44.4 7.6 55.3 0.612 105.2
BUY_c1.5_T240 K_PESS B wick1m iso | 0 1005 NA 173.4 151.4 185.7 0.593 55.4
BUY_c1.5_T240 K_PESS B wick1m na | 0 5 NA 246.3 241.2 265.8 0.000 48.8
BUY_c1.5_T240 K_PESS B wick1m not | 0 11529 NA 47.7 5.3 57.9 0.622 108.2
BUY_c1.5_T240 K_PESS B year y2024 | 2304866 6236 0.271 165.0 120.5 176.5 0.638 104.4
BUY_c1.5_T240 K_PESS B year y2025 | 3642691 6303 0.173 -48.2 -85.2 -38.9 0.601 103.6
BUY_c1.5_T1440 K_OPT3 A condB no | 2988434 6256 0.209 105.7 115.8 108.3 0.726 495.3
BUY_c1.5_T1440 K_OPT3 A condB yes | 283418 2285 0.806 51.0 100.8 52.5 0.792 414.6
BUY_c1.5_T1440 K_OPT3 A hour h0 | 136608 254 0.186 199.0 148.8 203.4 0.949 184.2
BUY_c1.5_T1440 K_OPT3 A hour h1 | 136358 334 0.245 2.3 55.2 6.6 0.464 946.3
BUY_c1.5_T1440 K_OPT3 A hour h10 | 136344 156 0.114 292.0 271.2 296.0 0.949 128.1
BUY_c1.5_T1440 K_OPT3 A hour h11 | 136231 172 0.126 323.6 323.0 327.2 0.977 94.2
BUY_c1.5_T1440 K_OPT3 A hour h12 | 136350 376 0.276 232.7 245.5 234.5 0.801 340.1
BUY_c1.5_T1440 K_OPT3 A hour h13 | 136358 338 0.248 282.7 171.2 286.7 0.967 125.3
BUY_c1.5_T1440 K_OPT3 A hour h14 | 136480 295 0.216 -58.2 182.8 -61.7 0.681 512.7
BUY_c1.5_T1440 K_OPT3 A hour h15 | 136465 703 0.515 70.4 60.9 72.7 0.653 583.4
BUY_c1.5_T1440 K_OPT3 A hour h16 | 136566 477 0.349 148.7 107.9 152.2 0.891 308.1
BUY_c1.5_T1440 K_OPT3 A hour h17 | 136256 521 0.382 -125.4 73.6 -124.3 0.681 532.9
BUY_c1.5_T1440 K_OPT3 A hour h18 | 136353 470 0.345 51.6 89.5 53.7 0.887 213.6
BUY_c1.5_T1440 K_OPT3 A hour h19 | 136234 653 0.479 57.4 -21.5 60.9 0.741 497.2
BUY_c1.5_T1440 K_OPT3 A hour h2 | 136422 296 0.217 130.4 -50.4 134.4 0.568 731.4
BUY_c1.5_T1440 K_OPT3 A hour h20 | 136351 355 0.260 203.8 180.0 205.2 0.893 299.0
BUY_c1.5_T1440 K_OPT3 A hour h21 | 136217 691 0.507 60.0 230.0 61.9 0.670 560.9
BUY_c1.5_T1440 K_OPT3 A hour h22 | 136111 378 0.278 74.0 56.5 76.4 0.717 552.2
BUY_c1.5_T1440 K_OPT3 A hour h23 | 136059 194 0.143 86.5 246.5 87.5 0.773 407.4
BUY_c1.5_T1440 K_OPT3 A hour h3 | 136252 67 0.049 46.8 -69.5 47.2 0.791 675.2
BUY_c1.5_T1440 K_OPT3 A hour h4 | 136260 416 0.305 -141.9 -38.0 -141.1 0.481 831.4
BUY_c1.5_T1440 K_OPT3 A hour h5 | 136127 186 0.137 355.4 315.1 350.1 0.935 208.3
BUY_c1.5_T1440 K_OPT3 A hour h6 | 136266 128 0.094 83.8 52.5 83.2 0.773 465.3
BUY_c1.5_T1440 K_OPT3 A hour h7 | 136230 128 0.094 209.2 177.7 209.6 0.938 184.5
BUY_c1.5_T1440 K_OPT3 A hour h8 | 136565 511 0.374 99.5 154.4 103.6 0.620 671.6
BUY_c1.5_T1440 K_OPT3 A hour h9 | 136389 442 0.324 106.6 27.7 110.6 0.760 478.9
BUY_c1.5_T1440 K_OPT3 A mkt idio | 0 1138 NA 79.3 78.6 78.4 0.797 375.9
BUY_c1.5_T1440 K_OPT3 A mkt market | 0 7403 NA 92.9 116.9 95.7 0.735 488.8
BUY_c1.5_T1440 K_OPT3 A qvratio 1_10 | 0 548 NA 85.6 96.7 83.4 0.827 355.2
BUY_c1.5_T1440 K_OPT3 A qvratio gt10 | 0 7988 NA 92.1 113.5 94.6 0.738 481.9
BUY_c1.5_T1440 K_OPT3 A qvratio lt1 | 0 5 NA -834.6 -1003.7 -869.0 0.800 390.2
BUY_c1.5_T1440 K_OPT3 A tier T1 | 219092 411 0.188 153.1 176.7 152.9 0.774 417.1
BUY_c1.5_T1440 K_OPT3 A tier T2 | 1095287 2344 0.214 121.5 140.6 122.4 0.754 462.4
BUY_c1.5_T1440 K_OPT3 A tier T3 | 1957473 5786 0.296 74.4 95.5 77.3 0.737 482.3
BUY_c1.5_T1440 K_OPT3 A wick1m iso | 0 385 NA 205.0 194.6 208.9 0.886 221.3
BUY_c1.5_T1440 K_OPT3 A wick1m na | 0 1 NA 132.7 132.7 136.8 1.000 0.0
BUY_c1.5_T1440 K_OPT3 A wick1m not | 0 8155 NA 85.7 107.9 87.9 0.737 485.7
BUY_c1.5_T1440 K_OPT3 A year y2021 | 533832 1020 0.191 202.4 266.0 203.6 0.785 400.9
BUY_c1.5_T1440 K_OPT3 A year y2022 | 1190474 2072 0.174 -9.5 72.0 -9.3 0.717 508.6
BUY_c1.5_T1440 K_OPT3 A year y2023 | 1547546 5449 0.352 108.5 98.0 111.7 0.745 474.1
BUY_c1.5_T1440 K_OPT3 B condB no | 5264570 8142 0.155 37.0 29.2 36.2 0.767 436.4
BUY_c1.5_T1440 K_OPT3 B condB yes | 672754 4542 0.675 191.7 82.1 194.5 0.883 312.6
BUY_c1.5_T1440 K_OPT3 B hour h0 | 247962 594 0.240 173.8 118.5 174.5 0.726 577.4
BUY_c1.5_T1440 K_OPT3 B hour h1 | 247620 978 0.395 325.7 143.1 329.3 0.871 518.1
BUY_c1.5_T1440 K_OPT3 B hour h10 | 247219 276 0.112 107.6 18.8 104.4 0.859 255.8
BUY_c1.5_T1440 K_OPT3 B hour h11 | 247001 207 0.084 -107.2 -110.7 -114.2 0.599 640.5
BUY_c1.5_T1440 K_OPT3 B hour h12 | 247338 697 0.282 186.6 100.1 188.2 0.783 387.1
BUY_c1.5_T1440 K_OPT3 B hour h13 | 247603 277 0.112 126.7 103.9 126.3 0.841 365.6
BUY_c1.5_T1440 K_OPT3 B hour h14 | 247865 274 0.111 -26.2 -37.9 -36.4 0.719 566.1
BUY_c1.5_T1440 K_OPT3 B hour h15 | 248108 602 0.243 97.5 113.7 98.5 0.857 272.7
BUY_c1.5_T1440 K_OPT3 B hour h16 | 248183 420 0.169 152.8 146.0 148.9 0.867 277.7
BUY_c1.5_T1440 K_OPT3 B hour h17 | 247937 929 0.375 47.8 -14.6 51.1 0.836 370.0
BUY_c1.5_T1440 K_OPT3 B hour h18 | 247633 767 0.310 -18.6 -58.1 -15.6 0.670 538.7
BUY_c1.5_T1440 K_OPT3 B hour h19 | 247438 581 0.235 295.5 242.5 297.9 0.897 490.4
BUY_c1.5_T1440 K_OPT3 B hour h2 | 247494 661 0.267 345.5 257.4 349.1 0.920 240.5
BUY_c1.5_T1440 K_OPT3 B hour h20 | 247713 865 0.350 -585.0 -391.2 -585.2 0.549 690.5
BUY_c1.5_T1440 K_OPT3 B hour h21 | 247309 939 0.380 -215.5 -159.6 -216.2 0.696 492.3
BUY_c1.5_T1440 K_OPT3 B hour h22 | 246674 822 0.333 317.9 278.6 321.1 0.976 90.3
BUY_c1.5_T1440 K_OPT3 B hour h23 | 246181 349 0.142 237.8 66.2 239.6 0.825 383.1
BUY_c1.5_T1440 K_OPT3 B hour h3 | 247202 152 0.061 -73.0 -88.3 -73.6 0.757 439.9
BUY_c1.5_T1440 K_OPT3 B hour h4 | 247143 149 0.060 -19.9 -13.9 -22.7 0.765 455.8
BUY_c1.5_T1440 K_OPT3 B hour h5 | 246893 178 0.072 54.2 29.1 41.4 0.803 388.7
BUY_c1.5_T1440 K_OPT3 B hour h6 | 246945 799 0.324 249.4 54.6 249.4 0.926 144.9
BUY_c1.5_T1440 K_OPT3 B hour h7 | 247003 694 0.281 277.6 219.1 279.4 0.921 165.3
BUY_c1.5_T1440 K_OPT3 B hour h8 | 247590 258 0.104 37.1 6.8 32.7 0.756 461.6
BUY_c1.5_T1440 K_OPT3 B hour h9 | 247270 216 0.087 -6.2 -17.2 -13.7 0.778 423.2
BUY_c1.5_T1440 K_OPT3 B mkt idio | 0 3104 NA 19.0 7.3 12.0 0.770 441.2
BUY_c1.5_T1440 K_OPT3 B mkt market | 0 9580 NA 116.2 61.4 119.1 0.821 376.2
BUY_c1.5_T1440 K_OPT3 B qvratio 1_10 | 0 404 NA 157.2 87.5 152.5 0.829 411.7
BUY_c1.5_T1440 K_OPT3 B qvratio gt10 | 0 12276 NA 90.2 46.8 90.9 0.808 391.5
BUY_c1.5_T1440 K_OPT3 B qvratio lt1 | 0 4 NA 213.4 197.9 218.1 1.000 239.0
BUY_c1.5_T1440 K_OPT3 B tier T1 | 175170 300 0.171 232.6 144.8 231.0 0.870 284.7
BUY_c1.5_T1440 K_OPT3 B tier T2 | 874828 1404 0.160 154.9 76.8 151.5 0.829 359.7
BUY_c1.5_T1440 K_OPT3 B tier T3 | 4887326 10980 0.225 80.6 41.8 81.6 0.804 399.2
BUY_c1.5_T1440 K_OPT3 B wick1m iso | 0 1002 NA 190.5 161.4 193.6 0.884 226.4
BUY_c1.5_T1440 K_OPT3 B wick1m na | 0 4 NA 350.3 347.8 354.6 1.000 113.8
BUY_c1.5_T1440 K_OPT3 B wick1m not | 0 11678 NA 83.9 38.3 84.1 0.802 406.4
BUY_c1.5_T1440 K_OPT3 B year y2024 | 2304866 6316 0.274 194.0 128.3 197.5 0.846 359.0
BUY_c1.5_T1440 K_OPT3 B year y2025 | 3632458 6368 0.175 -8.4 -31.4 -10.9 0.771 424.9
BUY_c1.5_T1440 K_PESS A condB no | 2988434 6136 0.205 96.2 106.4 105.5 0.698 509.4
BUY_c1.5_T1440 K_PESS A condB yes | 283418 2270 0.801 41.2 91.5 48.6 0.776 423.6
BUY_c1.5_T1440 K_PESS A hour h0 | 136608 245 0.179 194.5 143.2 203.5 0.939 191.9
BUY_c1.5_T1440 K_PESS A hour h1 | 136358 329 0.241 -11.6 43.5 1.9 0.435 965.3
BUY_c1.5_T1440 K_PESS A hour h10 | 136344 155 0.114 287.6 266.0 296.3 0.929 129.0
BUY_c1.5_T1440 K_PESS A hour h11 | 136231 170 0.125 318.3 317.1 326.3 0.971 96.0
BUY_c1.5_T1440 K_PESS A hour h12 | 136350 373 0.274 226.1 237.8 233.9 0.777 343.2
BUY_c1.5_T1440 K_PESS A hour h13 | 136358 332 0.243 278.5 164.5 287.5 0.907 134.5
BUY_c1.5_T1440 K_PESS A hour h14 | 136480 288 0.211 -71.2 175.5 -68.2 0.656 525.2
BUY_c1.5_T1440 K_PESS A hour h15 | 136465 694 0.509 59.3 51.7 68.9 0.622 594.6
BUY_c1.5_T1440 K_PESS A hour h16 | 136566 469 0.343 141.4 99.2 150.1 0.870 319.4
BUY_c1.5_T1440 K_PESS A hour h17 | 136256 513 0.376 -132.5 65.7 -124.6 0.663 533.2
BUY_c1.5_T1440 K_PESS A hour h18 | 136353 464 0.340 35.1 77.7 42.3 0.856 229.9
BUY_c1.5_T1440 K_PESS A hour h19 | 136234 642 0.471 44.4 -36.1 54.4 0.717 517.7
BUY_c1.5_T1440 K_PESS A hour h2 | 136422 291 0.213 121.0 -61.8 133.5 0.543 745.6
BUY_c1.5_T1440 K_PESS A hour h20 | 136351 341 0.250 197.9 176.2 204.4 0.862 304.5
BUY_c1.5_T1440 K_PESS A hour h21 | 136217 687 0.504 50.1 216.7 59.1 0.654 568.2
BUY_c1.5_T1440 K_PESS A hour h22 | 136111 367 0.270 59.8 42.3 68.8 0.692 579.8
BUY_c1.5_T1440 K_PESS A hour h23 | 136059 188 0.138 76.2 241.8 83.4 0.755 420.5
BUY_c1.5_T1440 K_PESS A hour h3 | 136252 65 0.048 33.6 -83.6 40.2 0.785 681.0
BUY_c1.5_T1440 K_PESS A hour h4 | 136260 413 0.303 -154.7 -50.0 -145.1 0.470 844.4
BUY_c1.5_T1440 K_PESS A hour h5 | 136127 186 0.137 350.6 309.8 350.1 0.930 208.6
BUY_c1.5_T1440 K_PESS A hour h6 | 136266 127 0.093 75.0 54.2 80.2 0.756 487.6
BUY_c1.5_T1440 K_PESS A hour h7 | 136230 124 0.091 202.5 169.8 207.8 0.895 208.5
BUY_c1.5_T1440 K_PESS A hour h8 | 136565 507 0.371 93.2 146.8 104.8 0.617 680.4
BUY_c1.5_T1440 K_PESS A hour h9 | 136389 436 0.320 96.3 15.9 106.8 0.713 503.6
BUY_c1.5_T1440 K_PESS A mkt idio | 0 1113 NA 70.3 69.7 75.5 0.759 385.9
BUY_c1.5_T1440 K_PESS A mkt market | 0 7293 NA 83.0 107.3 92.3 0.713 501.5
BUY_c1.5_T1440 K_PESS A qvratio 1_10 | 0 549 NA 81.4 90.0 84.7 0.818 363.8
BUY_c1.5_T1440 K_PESS A qvratio gt10 | 0 7853 NA 82.0 104.0 91.1 0.712 494.8
BUY_c1.5_T1440 K_PESS A qvratio lt1 | 0 4 NA -1181.0 -1401.1 -1220.2 0.750 486.0
BUY_c1.5_T1440 K_PESS A tier T1 | 219092 410 0.187 147.4 173.7 151.9 0.749 422.1
BUY_c1.5_T1440 K_PESS A tier T2 | 1095287 2315 0.211 114.2 133.2 120.7 0.732 472.3
BUY_c1.5_T1440 K_PESS A tier T3 | 1957473 5681 0.290 63.2 84.6 73.2 0.712 496.5
BUY_c1.5_T1440 K_PESS A wick1m iso | 0 385 NA 196.4 184.7 207.4 0.678 229.9
BUY_c1.5_T1440 K_PESS A wick1m na | 0 1 NA 117.6 117.6 136.8 0.000 1.0
BUY_c1.5_T1440 K_PESS A wick1m not | 0 8020 NA 75.8 98.4 84.5 0.721 498.6
BUY_c1.5_T1440 K_PESS A year y2021 | 533832 1020 0.191 196.3 261.9 203.6 0.766 401.1
BUY_c1.5_T1440 K_PESS A year y2022 | 1190474 2036 0.171 -21.4 61.9 -14.9 0.705 520.1
BUY_c1.5_T1440 K_PESS A year y2023 | 1547546 5350 0.346 98.5 87.3 108.4 0.716 489.5
BUY_c1.5_T1440 K_PESS B condB no | 5264570 8016 0.152 26.1 18.4 31.8 0.729 442.8
BUY_c1.5_T1440 K_PESS B condB yes | 672754 4510 0.670 184.3 73.3 192.5 0.859 319.2
BUY_c1.5_T1440 K_PESS B hour h0 | 247962 572 0.231 162.1 107.9 169.6 0.712 586.7
BUY_c1.5_T1440 K_PESS B hour h1 | 247620 975 0.394 318.4 133.5 327.6 0.844 528.0
BUY_c1.5_T1440 K_PESS B hour h10 | 247219 272 0.110 98.7 8.6 101.1 0.838 259.0
BUY_c1.5_T1440 K_PESS B hour h11 | 247001 202 0.082 -118.9 -122.8 -117.9 0.559 649.5
BUY_c1.5_T1440 K_PESS B hour h12 | 247338 691 0.279 179.0 92.3 187.1 0.744 401.1
BUY_c1.5_T1440 K_PESS B hour h13 | 247603 273 0.110 116.0 93.4 121.5 0.799 370.8
BUY_c1.5_T1440 K_PESS B hour h14 | 247865 268 0.108 -33.1 -47.2 -36.7 0.698 567.5
BUY_c1.5_T1440 K_PESS B hour h15 | 248108 585 0.236 89.7 107.2 96.1 0.831 274.9
BUY_c1.5_T1440 K_PESS B hour h16 | 248183 412 0.166 148.9 142.6 150.5 0.828 279.9
BUY_c1.5_T1440 K_PESS B hour h17 | 247937 911 0.367 38.7 -25.0 47.6 0.821 379.1
BUY_c1.5_T1440 K_PESS B hour h18 | 247633 763 0.308 -30.6 -70.7 -20.0 0.626 545.9
BUY_c1.5_T1440 K_PESS B hour h19 | 247438 577 0.233 289.9 235.5 297.5 0.882 493.7
BUY_c1.5_T1440 K_PESS B hour h2 | 247494 656 0.265 340.0 251.1 348.5 0.904 242.5
BUY_c1.5_T1440 K_PESS B hour h20 | 247713 858 0.347 -602.5 -406.8 -594.3 0.486 694.7
BUY_c1.5_T1440 K_PESS B hour h21 | 247309 932 0.377 -228.9 -170.7 -222.3 0.638 497.4
BUY_c1.5_T1440 K_PESS B hour h22 | 246674 817 0.331 311.3 272.6 319.1 0.939 95.2
BUY_c1.5_T1440 K_PESS B hour h23 | 246181 346 0.141 232.0 57.9 239.7 0.809 390.7
BUY_c1.5_T1440 K_PESS B hour h3 | 247202 152 0.061 -79.8 -96.0 -73.6 0.711 440.6
BUY_c1.5_T1440 K_PESS B hour h4 | 247143 146 0.059 -44.5 -35.8 -41.5 0.719 483.1
BUY_c1.5_T1440 K_PESS B hour h5 | 246893 171 0.069 39.8 16.3 32.7 0.749 400.3
BUY_c1.5_T1440 K_PESS B hour h6 | 246945 791 0.320 241.9 43.4 246.8 0.912 149.4
BUY_c1.5_T1440 K_PESS B hour h7 | 247003 690 0.279 271.9 210.8 278.7 0.903 168.5
BUY_c1.5_T1440 K_PESS B hour h8 | 247590 253 0.102 16.5 -17.0 19.5 0.704 474.7
BUY_c1.5_T1440 K_PESS B hour h9 | 247270 213 0.086 -17.3 -29.7 -17.8 0.704 429.5
BUY_c1.5_T1440 K_PESS B mkt idio | 0 3060 NA 7.8 -3.8 7.4 0.718 446.8
BUY_c1.5_T1440 K_PESS B mkt market | 0 9466 NA 107.4 51.8 116.2 0.794 382.6
BUY_c1.5_T1440 K_PESS B qvratio 1_10 | 0 390 NA 151.7 82.5 152.3 0.821 421.4
BUY_c1.5_T1440 K_PESS B qvratio gt10 | 0 12133 NA 80.8 36.7 87.6 0.774 397.6
BUY_c1.5_T1440 K_PESS B qvratio lt1 | 0 3 NA 223.1 184.4 231.1 1.000 178.0
BUY_c1.5_T1440 K_PESS B tier T1 | 175170 298 0.170 227.3 139.1 230.2 0.859 286.6
BUY_c1.5_T1440 K_PESS B tier T2 | 874828 1391 0.159 147.1 68.7 148.7 0.799 364.6
BUY_c1.5_T1440 K_PESS B tier T3 | 4887326 10837 0.222 70.9 31.5 78.2 0.770 405.7
BUY_c1.5_T1440 K_PESS B wick1m iso | 0 1002 NA 181.9 150.0 192.6 0.665 230.5
BUY_c1.5_T1440 K_PESS B wick1m na | 0 4 NA 337.6 333.9 354.6 0.250 114.5
BUY_c1.5_T1440 K_PESS B wick1m not | 0 11520 NA 74.4 28.3 80.6 0.786 413.0
BUY_c1.5_T1440 K_PESS B year y2024 | 2304866 6236 0.271 187.2 120.2 196.4 0.819 364.0
BUY_c1.5_T1440 K_PESS B year y2025 | 3632458 6290 0.173 -20.2 -43.2 -16.2 0.733 432.3
BUY_c2.5_T240 K_OPT3 A condB no | 2988434 1567 0.052 199.5 210.8 201.6 0.554 123.2
BUY_c2.5_T240 K_OPT3 A condB yes | 283402 1109 0.391 352.1 249.2 355.7 0.675 101.7
BUY_c2.5_T240 K_OPT3 A hour h0 | 136607 11 0.008 320.4 300.8 324.5 0.818 52.4
BUY_c2.5_T240 K_OPT3 A hour h1 | 136357 88 0.065 342.1 306.2 346.2 0.477 156.3
BUY_c2.5_T240 K_OPT3 A hour h10 | 136343 15 0.011 503.7 575.6 507.8 0.867 52.3
BUY_c2.5_T240 K_OPT3 A hour h11 | 136230 26 0.019 494.6 516.0 498.7 1.000 5.9
BUY_c2.5_T240 K_OPT3 A hour h12 | 136349 120 0.088 814.5 616.8 818.6 0.975 29.6
BUY_c2.5_T240 K_OPT3 A hour h13 | 136357 30 0.022 396.7 336.8 398.4 0.900 45.4
BUY_c2.5_T240 K_OPT3 A hour h14 | 136479 106 0.078 335.4 577.9 321.5 0.575 134.4
BUY_c2.5_T240 K_OPT3 A hour h15 | 136464 276 0.202 204.4 167.9 208.2 0.471 133.6
BUY_c2.5_T240 K_OPT3 A hour h16 | 136566 219 0.160 168.7 151.0 172.8 0.521 127.4
BUY_c2.5_T240 K_OPT3 A hour h17 | 136256 65 0.048 111.5 168.2 115.6 0.754 62.3
BUY_c2.5_T240 K_OPT3 A hour h18 | 136353 82 0.060 152.7 91.3 156.7 0.805 52.4
BUY_c2.5_T240 K_OPT3 A hour h19 | 136234 317 0.233 302.7 100.0 306.8 0.685 99.3
BUY_c2.5_T240 K_OPT3 A hour h2 | 136421 172 0.126 445.1 230.2 449.2 0.744 88.1
BUY_c2.5_T240 K_OPT3 A hour h20 | 136351 27 0.020 209.0 188.7 209.8 0.852 57.3
BUY_c2.5_T240 K_OPT3 A hour h21 | 136217 278 0.204 172.2 264.8 175.1 0.457 152.8
BUY_c2.5_T240 K_OPT3 A hour h22 | 136111 90 0.066 -78.9 -54.5 -76.6 0.300 178.0
BUY_c2.5_T240 K_OPT3 A hour h23 | 136059 26 0.019 216.9 252.3 212.4 0.769 73.7
BUY_c2.5_T240 K_OPT3 A hour h3 | 136251 8 0.006 207.8 193.8 211.8 0.625 114.9
BUY_c2.5_T240 K_OPT3 A hour h4 | 136259 206 0.151 -276.2 -102.2 -274.1 0.199 196.5
BUY_c2.5_T240 K_OPT3 A hour h5 | 136126 121 0.089 661.9 513.9 664.9 0.860 65.5
BUY_c2.5_T240 K_OPT3 A hour h6 | 136265 15 0.011 237.9 148.6 232.0 0.600 116.9
BUY_c2.5_T240 K_OPT3 A hour h7 | 136229 6 0.004 192.5 162.6 179.0 0.667 127.7
BUY_c2.5_T240 K_OPT3 A hour h8 | 136564 216 0.158 385.9 357.7 390.0 0.602 111.1
BUY_c2.5_T240 K_OPT3 A hour h9 | 136388 156 0.114 340.9 233.4 345.0 0.821 89.3
BUY_c2.5_T240 K_OPT3 A mkt idio | 0 160 NA 100.4 129.1 99.0 0.662 104.6
BUY_c2.5_T240 K_OPT3 A mkt market | 0 2516 NA 273.0 232.9 276.0 0.601 114.9
BUY_c2.5_T240 K_OPT3 A qvratio 1_10 | 0 158 NA 738.2 491.0 741.0 0.930 45.7
BUY_c2.5_T240 K_OPT3 A qvratio gt10 | 0 2518 NA 232.9 210.1 235.6 0.584 118.6
BUY_c2.5_T240 K_OPT3 A tier T1 | 219076 123 0.056 396.7 339.9 399.0 0.780 76.3
BUY_c2.5_T240 K_OPT3 A tier T2 | 1095287 731 0.067 321.4 274.9 323.5 0.659 101.0
BUY_c2.5_T240 K_OPT3 A tier T3 | 1957473 1822 0.093 230.1 199.8 233.1 0.570 122.2
BUY_c2.5_T240 K_OPT3 A wick1m iso | 0 82 NA 367.3 338.4 371.4 0.902 36.2
BUY_c2.5_T240 K_OPT3 A wick1m not | 0 2594 NA 259.4 223.2 262.1 0.595 116.8
BUY_c2.5_T240 K_OPT3 A year y2021 | 533832 477 0.089 515.8 479.6 515.7 0.797 67.9
BUY_c2.5_T240 K_OPT3 A year y2022 | 1190458 509 0.043 334.1 178.2 337.0 0.719 87.1
BUY_c2.5_T240 K_OPT3 A year y2023 | 1547546 1690 0.109 169.8 170.0 173.3 0.515 135.6
BUY_c2.5_T240 K_OPT3 B condB no | 5273840 2186 0.041 215.2 183.5 217.7 0.735 83.3
BUY_c2.5_T240 K_OPT3 B condB yes | 672595 2177 0.324 293.7 149.2 297.1 0.663 99.1
BUY_c2.5_T240 K_OPT3 B hour h0 | 248429 26 0.010 -18.0 -27.8 -15.0 0.462 138.7
BUY_c2.5_T240 K_OPT3 B hour h1 | 248086 597 0.241 460.4 234.4 464.3 0.642 117.9
BUY_c2.5_T240 K_OPT3 B hour h10 | 247687 37 0.015 -271.3 -276.8 -270.5 0.568 111.7
BUY_c2.5_T240 K_OPT3 B hour h11 | 247469 28 0.011 242.3 230.8 240.8 0.750 72.1
BUY_c2.5_T240 K_OPT3 B hour h12 | 247810 282 0.114 371.6 145.2 375.6 0.596 115.8
BUY_c2.5_T240 K_OPT3 B hour h13 | 248073 41 0.017 -98.5 -67.7 -98.2 0.610 115.4
BUY_c2.5_T240 K_OPT3 B hour h14 | 248332 42 0.017 -53.4 -18.6 -50.9 0.524 138.5
BUY_c2.5_T240 K_OPT3 B hour h15 | 248572 75 0.030 70.5 66.2 71.5 0.693 88.2
BUY_c2.5_T240 K_OPT3 B hour h16 | 248657 51 0.021 -28.2 -34.1 -29.7 0.706 92.4
BUY_c2.5_T240 K_OPT3 B hour h17 | 248409 301 0.121 296.7 228.2 300.8 0.645 103.3
BUY_c2.5_T240 K_OPT3 B hour h18 | 247587 478 0.193 450.6 369.7 454.5 0.730 92.9
BUY_c2.5_T240 K_OPT3 B hour h19 | 247391 283 0.114 372.4 296.0 376.4 0.604 142.4
BUY_c2.5_T240 K_OPT3 B hour h2 | 247961 96 0.039 488.9 454.4 493.0 0.854 47.1
BUY_c2.5_T240 K_OPT3 B hour h20 | 247666 287 0.116 -395.6 -293.4 -393.9 0.557 112.4
BUY_c2.5_T240 K_OPT3 B hour h21 | 247263 706 0.286 113.1 15.2 115.0 0.667 90.5
BUY_c2.5_T240 K_OPT3 B hour h22 | 247143 289 0.117 443.8 363.5 447.8 0.952 18.7
BUY_c2.5_T240 K_OPT3 B hour h23 | 246639 97 0.039 334.3 208.7 337.9 0.856 71.2
BUY_c2.5_T240 K_OPT3 B hour h3 | 247654 27 0.011 -749.8 -757.4 -748.4 0.333 168.2
BUY_c2.5_T240 K_OPT3 B hour h4 | 247603 30 0.012 -132.1 -147.9 -140.8 0.600 110.9
BUY_c2.5_T240 K_OPT3 B hour h5 | 247358 27 0.011 405.9 407.1 401.2 0.778 69.6
BUY_c2.5_T240 K_OPT3 B hour h6 | 247401 201 0.081 326.9 220.9 330.3 0.900 30.7
BUY_c2.5_T240 K_OPT3 B hour h7 | 247462 272 0.110 412.9 394.1 415.6 0.923 25.6
BUY_c2.5_T240 K_OPT3 B hour h8 | 248048 56 0.023 -82.3 -80.5 -83.3 0.500 128.4
BUY_c2.5_T240 K_OPT3 B hour h9 | 247735 34 0.014 -232.3 -235.0 -228.3 0.529 125.7
BUY_c2.5_T240 K_OPT3 B mkt idio | 0 709 NA -60.6 -63.1 -60.3 0.622 106.4
BUY_c2.5_T240 K_OPT3 B mkt market | 0 3654 NA 315.5 210.9 318.9 0.714 88.2
BUY_c2.5_T240 K_OPT3 B qvratio 1_10 | 0 43 NA 283.2 191.4 286.6 0.605 89.6
BUY_c2.5_T240 K_OPT3 B qvratio gt10 | 0 4320 NA 254.1 166.1 257.0 0.700 91.2
BUY_c2.5_T240 K_OPT3 B tier T1 | 175106 74 0.042 434.2 292.7 438.5 0.797 70.3
BUY_c2.5_T240 K_OPT3 B tier T2 | 874963 456 0.052 393.1 260.2 395.3 0.759 85.9
BUY_c2.5_T240 K_OPT3 B tier T3 | 4896366 3833 0.078 234.4 152.8 237.4 0.690 92.2
BUY_c2.5_T240 K_OPT3 B wick1m iso | 0 273 NA 391.2 377.8 395.3 0.912 25.7
BUY_c2.5_T240 K_OPT3 B wick1m na | 0 1 NA 328.8 328.8 332.9 1.000 0.0
BUY_c2.5_T240 K_OPT3 B wick1m not | 0 4089 NA 245.2 152.2 248.1 0.685 95.6
BUY_c2.5_T240 K_OPT3 B year y2024 | 2304866 2222 0.096 454.6 346.1 458.5 0.763 82.6
BUY_c2.5_T240 K_OPT3 B year y2025 | 3641569 2141 0.059 46.5 -20.2 48.5 0.633 100.1
BUY_c2.5_T240 K_PESS A condB no | 2988434 1546 0.052 188.4 199.6 199.1 0.523 125.0
BUY_c2.5_T240 K_PESS A condB yes | 283402 1103 0.389 344.1 240.7 355.0 0.664 102.4
BUY_c2.5_T240 K_PESS A hour h0 | 136607 10 0.007 311.9 291.8 324.5 0.600 52.4
BUY_c2.5_T240 K_PESS A hour h1 | 136357 83 0.061 327.8 291.5 341.7 0.434 163.7
BUY_c2.5_T240 K_PESS A hour h10 | 136343 15 0.011 498.2 571.0 507.8 0.867 53.5
BUY_c2.5_T240 K_PESS A hour h11 | 136230 26 0.019 490.5 511.9 498.7 1.000 5.9
BUY_c2.5_T240 K_PESS A hour h12 | 136349 120 0.088 810.0 612.8 818.6 0.967 29.7
BUY_c2.5_T240 K_PESS A hour h13 | 136357 30 0.022 391.6 328.7 398.4 0.900 45.6
BUY_c2.5_T240 K_PESS A hour h14 | 136479 106 0.078 327.5 569.5 321.5 0.566 134.4
BUY_c2.5_T240 K_PESS A hour h15 | 136464 270 0.198 196.7 154.5 209.9 0.452 133.9
BUY_c2.5_T240 K_PESS A hour h16 | 136566 218 0.160 156.5 140.0 169.6 0.500 129.7
BUY_c2.5_T240 K_PESS A hour h17 | 136256 62 0.046 85.7 147.9 96.5 0.645 65.1
BUY_c2.5_T240 K_PESS A hour h18 | 136353 80 0.059 140.4 77.6 151.0 0.738 53.7
BUY_c2.5_T240 K_PESS A hour h19 | 136234 313 0.230 294.8 91.3 306.0 0.681 99.2
BUY_c2.5_T240 K_PESS A hour h2 | 136421 171 0.125 436.1 220.1 447.3 0.719 89.9
BUY_c2.5_T240 K_PESS A hour h20 | 136351 27 0.020 203.7 184.1 209.8 0.815 57.3
BUY_c2.5_T240 K_PESS A hour h21 | 136217 276 0.203 158.6 252.9 170.8 0.442 156.3
BUY_c2.5_T240 K_PESS A hour h22 | 136111 90 0.066 -88.9 -65.1 -76.0 0.289 178.1
BUY_c2.5_T240 K_PESS A hour h23 | 136059 26 0.019 210.5 246.0 212.4 0.731 74.0
BUY_c2.5_T240 K_PESS A hour h3 | 136251 8 0.006 200.3 186.3 211.8 0.625 114.9
BUY_c2.5_T240 K_PESS A hour h4 | 136259 206 0.151 -287.5 -113.5 -274.1 0.199 196.5
BUY_c2.5_T240 K_PESS A hour h5 | 136126 121 0.089 656.3 507.4 664.8 0.851 65.5
BUY_c2.5_T240 K_PESS A hour h6 | 136265 15 0.011 230.1 140.9 232.0 0.600 116.9
BUY_c2.5_T240 K_PESS A hour h7 | 136229 6 0.004 184.9 154.3 179.0 0.667 127.8
BUY_c2.5_T240 K_PESS A hour h8 | 136564 216 0.158 377.8 349.5 390.0 0.588 111.5
BUY_c2.5_T240 K_PESS A hour h9 | 136388 154 0.113 333.7 222.3 344.3 0.734 92.4
BUY_c2.5_T240 K_PESS A mkt idio | 0 159 NA 90.6 119.9 96.6 0.623 106.6
BUY_c2.5_T240 K_PESS A mkt market | 0 2490 NA 263.7 222.9 274.7 0.579 116.2
BUY_c2.5_T240 K_PESS A qvratio 1_10 | 0 157 NA 740.4 478.8 748.2 0.924 45.2
BUY_c2.5_T240 K_PESS A qvratio gt10 | 0 2492 NA 222.6 200.2 233.5 0.560 120.1
BUY_c2.5_T240 K_PESS A tier T1 | 219076 123 0.056 389.3 331.7 396.5 0.756 78.5
BUY_c2.5_T240 K_PESS A tier T2 | 1095287 726 0.066 316.0 267.8 324.3 0.640 101.8
BUY_c2.5_T240 K_PESS A tier T3 | 1957473 1800 0.092 218.7 188.3 230.6 0.546 123.7
BUY_c2.5_T240 K_PESS A wick1m iso | 0 83 NA 357.1 324.1 369.9 0.554 39.4
BUY_c2.5_T240 K_PESS A wick1m not | 0 2566 NA 249.9 213.3 260.6 0.583 118.1
BUY_c2.5_T240 K_PESS A year y2021 | 533832 477 0.089 509.6 471.4 515.7 0.780 67.9
BUY_c2.5_T240 K_PESS A year y2022 | 1190458 506 0.043 326.2 169.0 335.7 0.709 88.4
BUY_c2.5_T240 K_PESS A year y2023 | 1547546 1666 0.108 157.7 158.3 170.2 0.486 137.5
BUY_c2.5_T240 K_PESS B condB no | 5273840 2171 0.041 207.0 174.5 216.9 0.681 84.3
BUY_c2.5_T240 K_PESS B condB yes | 672595 2162 0.321 276.6 130.9 288.1 0.611 101.3
BUY_c2.5_T240 K_PESS B hour h0 | 248429 26 0.010 -28.4 -40.3 -15.0 0.385 138.7
BUY_c2.5_T240 K_PESS B hour h1 | 248086 595 0.240 449.3 221.7 461.2 0.632 120.1
BUY_c2.5_T240 K_PESS B hour h10 | 247687 36 0.015 -304.7 -309.6 -294.6 0.472 114.7
BUY_c2.5_T240 K_PESS B hour h11 | 247469 28 0.011 234.2 222.0 240.8 0.643 72.5
BUY_c2.5_T240 K_PESS B hour h12 | 247810 281 0.113 359.6 129.9 372.5 0.537 118.2
BUY_c2.5_T240 K_PESS B hour h13 | 248073 41 0.017 -107.3 -76.7 -98.2 0.512 115.6
BUY_c2.5_T240 K_PESS B hour h14 | 248332 42 0.017 -63.8 -29.5 -50.9 0.452 139.0
BUY_c2.5_T240 K_PESS B hour h15 | 248572 75 0.030 62.1 58.7 71.3 0.600 88.6
BUY_c2.5_T240 K_PESS B hour h16 | 248657 51 0.021 -36.4 -41.4 -29.7 0.588 92.5
BUY_c2.5_T240 K_PESS B hour h17 | 248409 300 0.121 284.8 216.0 297.1 0.600 103.8
BUY_c2.5_T240 K_PESS B hour h18 | 247587 478 0.193 440.8 360.2 452.2 0.682 94.3
BUY_c2.5_T240 K_PESS B hour h19 | 247391 283 0.114 363.9 287.1 376.3 0.597 143.2
BUY_c2.5_T240 K_PESS B hour h2 | 247961 93 0.038 475.7 427.5 487.1 0.688 49.4
BUY_c2.5_T240 K_PESS B hour h20 | 247666 281 0.114 -404.9 -302.0 -395.0 0.520 113.2
BUY_c2.5_T240 K_PESS B hour h21 | 247263 706 0.286 88.7 -6.6 98.5 0.599 92.6
BUY_c2.5_T240 K_PESS B hour h22 | 247143 286 0.116 437.0 355.5 446.2 0.895 19.0
BUY_c2.5_T240 K_PESS B hour h23 | 246639 94 0.038 321.4 191.1 330.7 0.840 74.7
BUY_c2.5_T240 K_PESS B hour h3 | 247654 27 0.011 -760.0 -767.7 -748.4 0.333 168.2
BUY_c2.5_T240 K_PESS B hour h4 | 247603 29 0.012 -187.9 -208.4 -187.9 0.483 122.9
BUY_c2.5_T240 K_PESS B hour h5 | 247358 25 0.010 368.8 368.4 371.7 0.600 74.7
BUY_c2.5_T240 K_PESS B hour h6 | 247401 197 0.080 318.0 212.7 327.1 0.838 32.4
BUY_c2.5_T240 K_PESS B hour h7 | 247462 270 0.109 404.4 381.6 413.1 0.841 25.7
BUY_c2.5_T240 K_PESS B hour h8 | 248048 55 0.022 -102.8 -101.7 -92.7 0.436 131.3
BUY_c2.5_T240 K_PESS B hour h9 | 247735 34 0.014 -241.5 -243.7 -226.5 0.441 125.8
BUY_c2.5_T240 K_PESS B mkt idio | 0 701 NA -78.7 -81.6 -69.2 0.515 107.9
BUY_c2.5_T240 K_PESS B mkt market | 0 3632 NA 303.6 198.0 314.5 0.671 89.9
BUY_c2.5_T240 K_PESS B qvratio 1_10 | 0 41 NA 325.1 252.7 339.1 0.610 82.3
BUY_c2.5_T240 K_PESS B qvratio gt10 | 0 4292 NA 241.0 151.8 251.6 0.646 92.9
BUY_c2.5_T240 K_PESS B tier T1 | 175106 74 0.042 429.4 287.5 438.5 0.770 70.4
BUY_c2.5_T240 K_PESS B tier T2 | 874963 454 0.052 391.3 256.9 399.1 0.731 85.8
BUY_c2.5_T240 K_PESS B tier T3 | 4896366 3805 0.078 220.3 137.7 231.3 0.633 94.1
BUY_c2.5_T240 K_PESS B wick1m iso | 0 273 NA 380.0 362.8 393.2 0.542 27.0
BUY_c2.5_T240 K_PESS B wick1m na | 0 1 NA 313.4 313.4 332.9 0.000 1.0
BUY_c2.5_T240 K_PESS B wick1m not | 0 4059 NA 232.4 138.6 242.9 0.653 97.3
BUY_c2.5_T240 K_PESS B year y2024 | 2304866 2213 0.096 445.9 337.0 456.6 0.739 84.0
BUY_c2.5_T240 K_PESS B year y2025 | 3641569 2120 0.058 28.7 -39.6 39.2 0.549 102.0
BUY_c2.5_T1440 K_OPT3 A condB no | 2988434 1567 0.052 212.6 227.3 214.1 0.644 590.6
BUY_c2.5_T1440 K_OPT3 A condB yes | 283402 1109 0.391 383.4 330.1 385.6 0.855 318.0
BUY_c2.5_T1440 K_OPT3 A hour h0 | 136607 11 0.008 340.6 317.3 344.8 0.909 180.0
BUY_c2.5_T1440 K_OPT3 A hour h1 | 136357 88 0.065 279.5 277.3 282.9 0.716 593.1
BUY_c2.5_T1440 K_OPT3 A hour h10 | 136343 15 0.011 583.6 653.8 586.5 1.000 63.1
BUY_c2.5_T1440 K_OPT3 A hour h11 | 136230 26 0.019 494.6 516.0 498.7 1.000 5.9
BUY_c2.5_T1440 K_OPT3 A hour h12 | 136349 120 0.088 816.9 621.6 821.0 0.992 51.4
BUY_c2.5_T1440 K_OPT3 A hour h13 | 136357 30 0.022 406.3 352.9 404.9 0.933 127.3
BUY_c2.5_T1440 K_OPT3 A hour h14 | 136479 106 0.078 212.6 568.5 199.2 0.613 620.5
BUY_c2.5_T1440 K_OPT3 A hour h15 | 136464 276 0.202 218.3 141.6 220.4 0.536 731.6
BUY_c2.5_T1440 K_OPT3 A hour h16 | 136566 219 0.160 351.2 303.0 355.2 0.950 291.2
BUY_c2.5_T1440 K_OPT3 A hour h17 | 136256 65 0.048 5.6 180.1 4.6 0.831 294.9
BUY_c2.5_T1440 K_OPT3 A hour h18 | 136353 82 0.060 -43.3 34.0 -44.9 0.841 248.4
BUY_c2.5_T1440 K_OPT3 A hour h19 | 136234 317 0.233 221.6 42.8 224.1 0.823 318.9
BUY_c2.5_T1440 K_OPT3 A hour h2 | 136421 172 0.126 483.7 276.2 488.0 0.820 334.6
BUY_c2.5_T1440 K_OPT3 A hour h20 | 136351 27 0.020 224.3 198.0 223.9 0.889 198.1
BUY_c2.5_T1440 K_OPT3 A hour h21 | 136217 278 0.204 220.0 454.5 222.9 0.579 709.7
BUY_c2.5_T1440 K_OPT3 A hour h22 | 136111 90 0.066 37.6 29.9 38.9 0.422 916.1
BUY_c2.5_T1440 K_OPT3 A hour h23 | 136059 26 0.019 245.3 340.0 240.0 0.885 252.0
BUY_c2.5_T1440 K_OPT3 A hour h3 | 136251 8 0.006 392.0 250.8 386.6 0.875 353.2
BUY_c2.5_T1440 K_OPT3 A hour h4 | 136259 206 0.151 -95.0 56.3 -95.1 0.301 1088.9
BUY_c2.5_T1440 K_OPT3 A hour h5 | 136126 121 0.089 716.9 546.1 719.8 0.992 130.1
BUY_c2.5_T1440 K_OPT3 A hour h6 | 136265 15 0.011 119.4 99.4 112.6 0.733 481.6
BUY_c2.5_T1440 K_OPT3 A hour h7 | 136229 6 0.004 360.0 257.1 338.4 0.833 365.5
BUY_c2.5_T1440 K_OPT3 A hour h8 | 136564 216 0.158 389.3 384.7 394.1 0.708 505.1
BUY_c2.5_T1440 K_OPT3 A hour h9 | 136388 156 0.114 339.6 228.5 342.9 0.936 193.3
BUY_c2.5_T1440 K_OPT3 A mkt idio | 0 160 NA 116.2 151.9 110.2 0.787 410.4
BUY_c2.5_T1440 K_OPT3 A mkt market | 0 2516 NA 294.1 277.4 296.3 0.728 481.9
BUY_c2.5_T1440 K_OPT3 A qvratio 1_10 | 0 158 NA 751.0 521.6 749.8 0.968 96.4
BUY_c2.5_T1440 K_OPT3 A qvratio gt10 | 0 2518 NA 254.1 254.1 256.0 0.716 501.5
BUY_c2.5_T1440 K_OPT3 A tier T1 | 219076 123 0.056 370.9 355.6 366.8 0.846 287.0
BUY_c2.5_T1440 K_OPT3 A tier T2 | 1095287 731 0.067 340.7 309.3 341.5 0.774 411.7
BUY_c2.5_T1440 K_OPT3 A tier T3 | 1957473 1822 0.093 254.5 248.3 257.1 0.706 516.9
BUY_c2.5_T1440 K_OPT3 A wick1m iso | 0 82 NA 382.1 350.0 386.2 0.963 115.0
BUY_c2.5_T1440 K_OPT3 A wick1m not | 0 2594 NA 280.3 267.4 282.0 0.724 489.1
BUY_c2.5_T1440 K_OPT3 A year y2021 | 533832 477 0.089 516.4 493.6 516.6 0.860 264.8
BUY_c2.5_T1440 K_OPT3 A year y2022 | 1190458 509 0.043 285.1 185.6 284.1 0.809 339.6
BUY_c2.5_T1440 K_OPT3 A year y2023 | 1547546 1690 0.109 217.2 232.1 220.2 0.672 579.3
BUY_c2.5_T1440 K_OPT3 B condB no | 5263607 2184 0.041 216.4 204.3 215.3 0.807 339.9
BUY_c2.5_T1440 K_OPT3 B condB yes | 672595 2177 0.324 346.8 209.3 349.2 0.859 315.6
BUY_c2.5_T1440 K_OPT3 B hour h0 | 247915 26 0.010 364.8 359.0 359.6 0.692 598.4
BUY_c2.5_T1440 K_OPT3 B hour h1 | 247573 597 0.241 587.4 323.8 591.2 0.955 234.3
BUY_c2.5_T1440 K_OPT3 B hour h10 | 247172 37 0.015 -267.6 -288.4 -287.7 0.649 546.5
BUY_c2.5_T1440 K_OPT3 B hour h11 | 246954 28 0.011 232.8 214.5 221.6 0.786 346.1
BUY_c2.5_T1440 K_OPT3 B hour h12 | 247291 281 0.114 385.4 170.4 389.2 0.744 497.2
BUY_c2.5_T1440 K_OPT3 B hour h13 | 247556 41 0.017 -71.1 -6.3 -77.5 0.707 505.3
BUY_c2.5_T1440 K_OPT3 B hour h14 | 247819 42 0.017 -45.4 -18.2 -47.8 0.714 536.5
BUY_c2.5_T1440 K_OPT3 B hour h15 | 248062 75 0.030 52.5 36.1 52.1 0.787 390.3
BUY_c2.5_T1440 K_OPT3 B hour h16 | 248137 51 0.021 63.5 49.9 46.9 0.784 395.5
BUY_c2.5_T1440 K_OPT3 B hour h17 | 247890 301 0.121 359.3 260.4 362.3 0.937 230.6
BUY_c2.5_T1440 K_OPT3 B hour h18 | 247587 478 0.193 397.7 317.3 400.4 0.831 326.4
BUY_c2.5_T1440 K_OPT3 B hour h19 | 247391 283 0.114 465.6 382.2 469.7 0.951 299.6
BUY_c2.5_T1440 K_OPT3 B hour h2 | 247447 96 0.039 542.6 489.1 546.7 0.969 115.0
BUY_c2.5_T1440 K_OPT3 B hour h20 | 247666 287 0.116 -476.0 -231.4 -477.7 0.568 635.1
BUY_c2.5_T1440 K_OPT3 B hour h21 | 247263 706 0.286 104.0 87.6 103.5 0.711 456.9
BUY_c2.5_T1440 K_OPT3 B hour h22 | 246627 289 0.117 461.3 376.4 464.4 0.983 53.7
BUY_c2.5_T1440 K_OPT3 B hour h23 | 246135 97 0.039 443.2 309.6 447.3 0.938 184.3
BUY_c2.5_T1440 K_OPT3 B hour h3 | 247155 27 0.011 -812.2 -802.6 -824.2 0.444 875.5
BUY_c2.5_T1440 K_OPT3 B hour h4 | 247096 30 0.012 -277.6 -351.8 -302.4 0.667 532.8
BUY_c2.5_T1440 K_OPT3 B hour h5 | 246846 27 0.011 309.9 314.4 305.0 0.815 309.3
BUY_c2.5_T1440 K_OPT3 B hour h6 | 246898 200 0.081 351.4 245.1 352.3 0.925 126.8
BUY_c2.5_T1440 K_OPT3 B hour h7 | 246956 272 0.110 437.7 415.1 438.8 0.930 107.5
BUY_c2.5_T1440 K_OPT3 B hour h8 | 247543 56 0.023 -45.2 -94.5 -63.9 0.607 562.7
BUY_c2.5_T1440 K_OPT3 B hour h9 | 247223 34 0.014 0.2 -17.1 -12.1 0.706 531.3
BUY_c2.5_T1440 K_OPT3 B mkt idio | 0 707 NA -6.5 -13.8 -16.1 0.716 473.4
BUY_c2.5_T1440 K_OPT3 B mkt market | 0 3654 NA 337.2 249.5 339.9 0.856 299.6
BUY_c2.5_T1440 K_OPT3 B qvratio 1_10 | 0 43 NA 538.3 443.1 541.7 0.837 250.8
BUY_c2.5_T1440 K_OPT3 B qvratio gt10 | 0 4318 NA 278.9 204.4 279.6 0.833 328.5
BUY_c2.5_T1440 K_OPT3 B tier T1 | 174906 74 0.042 484.0 329.1 488.3 0.905 224.1
BUY_c2.5_T1440 K_OPT3 B tier T2 | 873964 456 0.052 407.7 281.0 407.0 0.879 265.1
BUY_c2.5_T1440 K_OPT3 B tier T3 | 4887332 3831 0.078 262.6 195.6 263.3 0.826 337.2
BUY_c2.5_T1440 K_OPT3 B wick1m iso | 0 273 NA 400.1 385.5 404.0 0.934 110.3
BUY_c2.5_T1440 K_OPT3 B wick1m na | 0 1 NA 328.8 328.8 332.9 1.000 0.0
BUY_c2.5_T1440 K_OPT3 B wick1m not | 0 4087 NA 273.5 194.8 274.0 0.826 342.4
BUY_c2.5_T1440 K_OPT3 B year y2024 | 2304866 2222 0.096 472.1 355.3 475.6 0.905 239.8
BUY_c2.5_T1440 K_OPT3 B year y2025 | 3631336 2139 0.059 83.5 52.5 81.2 0.757 419.1
BUY_c2.5_T1440 K_PESS A condB no | 2988434 1546 0.052 201.7 217.1 210.9 0.615 600.8
BUY_c2.5_T1440 K_PESS A condB yes | 283402 1103 0.389 377.5 324.2 385.1 0.844 322.1
BUY_c2.5_T1440 K_PESS A hour h0 | 136607 10 0.007 335.3 310.0 346.9 0.700 195.9
BUY_c2.5_T1440 K_PESS A hour h1 | 136357 83 0.061 262.2 260.2 272.8 0.675 647.2
BUY_c2.5_T1440 K_PESS A hour h10 | 136343 15 0.011 579.5 650.6 586.5 1.000 64.4
BUY_c2.5_T1440 K_PESS A hour h11 | 136230 26 0.019 490.5 511.9 498.7 1.000 5.9
BUY_c2.5_T1440 K_PESS A hour h12 | 136349 120 0.088 812.6 617.8 821.0 0.983 51.5
BUY_c2.5_T1440 K_PESS A hour h13 | 136357 30 0.022 401.5 345.1 404.9 0.933 127.5
BUY_c2.5_T1440 K_PESS A hour h14 | 136479 106 0.078 205.2 560.6 199.2 0.604 620.5
BUY_c2.5_T1440 K_PESS A hour h15 | 136464 270 0.198 209.2 128.8 219.9 0.519 730.6
BUY_c2.5_T1440 K_PESS A hour h16 | 136566 218 0.160 345.3 297.0 354.0 0.936 300.0
BUY_c2.5_T1440 K_PESS A hour h17 | 136256 62 0.046 -24.4 161.4 -19.9 0.726 309.0
BUY_c2.5_T1440 K_PESS A hour h18 | 136353 80 0.059 -59.9 19.5 -55.9 0.775 254.7
BUY_c2.5_T1440 K_PESS A hour h19 | 136234 313 0.230 213.2 35.8 221.5 0.815 323.5
BUY_c2.5_T1440 K_PESS A hour h2 | 136421 171 0.125 476.3 267.9 486.8 0.801 345.8
BUY_c2.5_T1440 K_PESS A hour h20 | 136351 27 0.020 219.2 193.6 223.9 0.852 198.1
BUY_c2.5_T1440 K_PESS A hour h21 | 136217 276 0.203 205.6 445.1 216.6 0.572 728.1
BUY_c2.5_T1440 K_PESS A hour h22 | 136111 90 0.066 28.5 20.2 39.5 0.411 916.3
BUY_c2.5_T1440 K_PESS A hour h23 | 136059 26 0.019 240.0 334.8 240.0 0.846 252.3
BUY_c2.5_T1440 K_PESS A hour h3 | 136251 8 0.006 386.6 245.4 386.6 0.875 353.2
BUY_c2.5_T1440 K_PESS A hour h4 | 136259 206 0.151 -106.6 45.3 -96.1 0.296 1092.1
BUY_c2.5_T1440 K_PESS A hour h5 | 136126 121 0.089 712.6 541.0 719.8 0.983 130.1
BUY_c2.5_T1440 K_PESS A hour h6 | 136265 15 0.011 113.3 93.4 112.6 0.733 481.6
BUY_c2.5_T1440 K_PESS A hour h7 | 136229 6 0.004 354.1 250.6 338.4 0.833 365.7
BUY_c2.5_T1440 K_PESS A hour h8 | 136564 216 0.158 382.2 377.6 394.1 0.694 510.2
BUY_c2.5_T1440 K_PESS A hour h9 | 136388 154 0.113 334.5 218.7 343.3 0.857 198.2
BUY_c2.5_T1440 K_PESS A mkt idio | 0 159 NA 102.6 139.4 102.6 0.748 422.0
BUY_c2.5_T1440 K_PESS A mkt market | 0 2490 NA 285.9 269.5 295.0 0.708 488.8
BUY_c2.5_T1440 K_PESS A qvratio 1_10 | 0 157 NA 763.5 513.5 766.8 0.962 88.6
BUY_c2.5_T1440 K_PESS A qvratio gt10 | 0 2492 NA 244.1 245.9 253.0 0.695 509.7
BUY_c2.5_T1440 K_PESS A tier T1 | 219076 123 0.056 357.2 341.8 357.8 0.821 299.3
BUY_c2.5_T1440 K_PESS A tier T2 | 1095287 726 0.066 335.4 303.5 341.6 0.758 413.7
BUY_c2.5_T1440 K_PESS A tier T3 | 1957473 1800 0.092 244.9 239.4 254.9 0.684 526.1
BUY_c2.5_T1440 K_PESS A wick1m iso | 0 83 NA 373.3 334.6 385.4 0.627 117.7
BUY_c2.5_T1440 K_PESS A wick1m not | 0 2566 NA 271.7 259.4 280.1 0.713 496.7
BUY_c2.5_T1440 K_PESS A year y2021 | 533832 477 0.089 510.9 486.0 516.6 0.843 267.0
BUY_c2.5_T1440 K_PESS A year y2022 | 1190458 506 0.043 278.0 178.4 282.7 0.802 343.7
BUY_c2.5_T1440 K_PESS A year y2023 | 1547546 1666 0.108 206.4 222.8 216.9 0.645 590.0
BUY_c2.5_T1440 K_PESS B condB no | 5263607 2169 0.041 207.1 194.2 212.5 0.751 344.7
BUY_c2.5_T1440 K_PESS B condB yes | 672595 2162 0.321 331.2 192.8 339.6 0.809 325.2
BUY_c2.5_T1440 K_PESS B hour h0 | 247915 26 0.010 357.0 349.2 359.6 0.615 598.5
BUY_c2.5_T1440 K_PESS B hour h1 | 247573 595 0.240 581.9 315.2 590.3 0.951 239.5
BUY_c2.5_T1440 K_PESS B hour h10 | 247172 36 0.015 -300.0 -320.6 -312.3 0.556 561.6
BUY_c2.5_T1440 K_PESS B hour h11 | 246954 28 0.011 228.5 209.6 221.6 0.679 346.7
BUY_c2.5_T1440 K_PESS B hour h12 | 247291 280 0.113 373.2 155.4 384.3 0.682 509.5
BUY_c2.5_T1440 K_PESS B hour h13 | 247556 41 0.017 -78.7 -14.2 -77.5 0.610 505.4
BUY_c2.5_T1440 K_PESS B hour h14 | 247819 42 0.017 -53.5 -27.4 -47.8 0.643 538.4
BUY_c2.5_T1440 K_PESS B hour h15 | 248062 75 0.030 45.4 29.9 52.1 0.693 390.6
BUY_c2.5_T1440 K_PESS B hour h16 | 248137 51 0.021 56.4 43.7 46.9 0.667 395.6
BUY_c2.5_T1440 K_PESS B hour h17 | 247890 300 0.121 350.8 250.7 358.8 0.897 232.2
BUY_c2.5_T1440 K_PESS B hour h18 | 247587 478 0.193 385.2 305.1 394.2 0.782 333.7
BUY_c2.5_T1440 K_PESS B hour h19 | 247391 283 0.114 457.2 372.9 466.0 0.940 301.9
BUY_c2.5_T1440 K_PESS B hour h2 | 247447 93 0.038 532.5 464.9 542.9 0.806 119.6
BUY_c2.5_T1440 K_PESS B hour h20 | 247666 281 0.114 -489.0 -242.7 -482.7 0.527 642.4
BUY_c2.5_T1440 K_PESS B hour h21 | 247263 706 0.286 78.4 66.4 85.2 0.643 469.2
BUY_c2.5_T1440 K_PESS B hour h22 | 246627 286 0.116 453.2 368.0 461.2 0.923 56.5
BUY_c2.5_T1440 K_PESS B hour h23 | 246135 94 0.038 434.5 295.9 443.6 0.926 191.6
BUY_c2.5_T1440 K_PESS B hour h3 | 247155 27 0.011 -861.1 -852.6 -864.2 0.407 896.4
BUY_c2.5_T1440 K_PESS B hour h4 | 247096 29 0.012 -368.0 -445.9 -385.2 0.517 629.7
BUY_c2.5_T1440 K_PESS B hour h5 | 246846 25 0.010 265.6 268.9 267.9 0.640 333.6
BUY_c2.5_T1440 K_PESS B hour h6 | 246898 196 0.079 344.0 238.4 350.3 0.867 130.8
BUY_c2.5_T1440 K_PESS B hour h7 | 246956 270 0.109 429.5 402.8 436.5 0.848 108.1
BUY_c2.5_T1440 K_PESS B hour h8 | 247543 55 0.022 -63.8 -114.7 -72.9 0.545 575.0
BUY_c2.5_T1440 K_PESS B hour h9 | 247223 34 0.014 -8.0 -25.6 -10.9 0.618 539.0
BUY_c2.5_T1440 K_PESS B mkt idio | 0 699 NA -24.5 -32.3 -26.2 0.608 481.8
BUY_c2.5_T1440 K_PESS B mkt market | 0 3632 NA 325.6 236.9 334.1 0.813 306.7
BUY_c2.5_T1440 K_PESS B qvratio 1_10 | 0 41 NA 568.0 490.4 579.4 0.829 213.8
BUY_c2.5_T1440 K_PESS B qvratio gt10 | 0 4290 NA 266.2 190.6 273.0 0.780 336.1
BUY_c2.5_T1440 K_PESS B tier T1 | 174906 74 0.042 479.6 324.1 488.3 0.878 224.1
BUY_c2.5_T1440 K_PESS B tier T2 | 873964 454 0.052 407.8 278.9 412.0 0.852 263.2
BUY_c2.5_T1440 K_PESS B tier T3 | 4887332 3803 0.078 248.4 180.7 255.6 0.770 345.7
BUY_c2.5_T1440 K_PESS B wick1m iso | 0 273 NA 387.4 368.9 400.1 0.564 116.0
BUY_c2.5_T1440 K_PESS B wick1m na | 0 1 NA 313.4 313.4 332.9 0.000 1.0
BUY_c2.5_T1440 K_PESS B wick1m not | 0 4057 NA 261.1 181.6 267.6 0.795 349.8
BUY_c2.5_T1440 K_PESS B year y2024 | 2304866 2213 0.096 464.2 346.6 473.0 0.882 245.0
BUY_c2.5_T1440 K_PESS B year y2025 | 3631336 2118 0.058 65.2 33.5 70.1 0.674 428.9
SELL_c1.0_T240 K_OPT3 A condB no | 2988434 16711 0.559 -6.4 -0.6 -1.0 0.643 116.2
SELL_c1.0_T240 K_OPT3 A condB yes | 283418 4443 1.568 48.5 8.4 53.6 0.682 106.0
SELL_c1.0_T240 K_OPT3 A hour h0 | 136608 1670 1.223 23.2 19.7 27.2 0.640 115.4
SELL_c1.0_T240 K_OPT3 A hour h1 | 136358 890 0.653 42.2 29.1 46.2 0.624 120.5
SELL_c1.0_T240 K_OPT3 A hour h10 | 136344 806 0.591 24.1 -2.7 28.4 0.694 111.2
SELL_c1.0_T240 K_OPT3 A hour h11 | 136231 634 0.465 14.1 12.3 18.1 0.715 101.7
SELL_c1.0_T240 K_OPT3 A hour h12 | 136350 1034 0.758 -19.8 -21.4 -13.4 0.629 118.5
SELL_c1.0_T240 K_OPT3 A hour h13 | 136358 1331 0.976 34.1 -3.7 40.1 0.671 107.3
SELL_c1.0_T240 K_OPT3 A hour h14 | 136480 1434 1.051 -36.8 7.5 -30.5 0.582 132.1
SELL_c1.0_T240 K_OPT3 A hour h15 | 136465 1136 0.832 -8.5 5.8 -0.7 0.634 113.1
SELL_c1.0_T240 K_OPT3 A hour h16 | 136566 1345 0.985 60.2 28.2 64.4 0.727 100.4
SELL_c1.0_T240 K_OPT3 A hour h17 | 136256 932 0.684 50.6 33.4 54.6 0.729 94.9
SELL_c1.0_T240 K_OPT3 A hour h18 | 136353 981 0.719 24.1 33.1 28.5 0.667 104.5
SELL_c1.0_T240 K_OPT3 A hour h19 | 136234 737 0.541 -122.6 -102.4 -118.5 0.617 114.5
SELL_c1.0_T240 K_OPT3 A hour h2 | 136422 682 0.500 -75.8 -66.1 -71.8 0.592 128.0
SELL_c1.0_T240 K_OPT3 A hour h20 | 136351 635 0.466 -11.8 4.5 -6.9 0.633 116.2
SELL_c1.0_T240 K_OPT3 A hour h21 | 136217 608 0.446 52.4 61.1 57.6 0.638 116.9
SELL_c1.0_T240 K_OPT3 A hour h22 | 136111 859 0.631 -18.8 -44.2 -13.4 0.582 127.5
SELL_c1.0_T240 K_OPT3 A hour h23 | 136059 595 0.437 37.3 34.6 44.2 0.741 88.5
SELL_c1.0_T240 K_OPT3 A hour h3 | 136252 603 0.443 -47.0 -49.6 -42.3 0.615 127.1
SELL_c1.0_T240 K_OPT3 A hour h4 | 136260 519 0.381 -25.7 -11.1 -17.5 0.595 126.0
SELL_c1.0_T240 K_OPT3 A hour h5 | 136127 632 0.464 45.1 17.5 51.7 0.682 116.3
SELL_c1.0_T240 K_OPT3 A hour h6 | 136266 722 0.530 8.8 -5.9 15.3 0.666 113.9
SELL_c1.0_T240 K_OPT3 A hour h7 | 136230 793 0.582 -21.0 -34.5 -13.5 0.677 108.6
SELL_c1.0_T240 K_OPT3 A hour h8 | 136565 850 0.622 23.2 25.4 27.2 0.649 119.2
SELL_c1.0_T240 K_OPT3 A hour h9 | 136389 726 0.532 7.5 6.2 12.5 0.645 118.8
SELL_c1.0_T240 K_OPT3 A mkt idio | 0 14218 NA 9.2 9.4 14.9 0.680 107.5
SELL_c1.0_T240 K_OPT3 A mkt market | 0 6936 NA -3.2 -15.2 1.3 0.593 127.5
SELL_c1.0_T240 K_OPT3 A qvratio 1_10 | 0 3815 NA 25.6 -1.8 30.8 0.604 131.4
SELL_c1.0_T240 K_OPT3 A qvratio gt10 | 0 17288 NA 0.7 2.2 6.0 0.662 110.2
SELL_c1.0_T240 K_OPT3 A qvratio lt1 | 0 51 NA -7.0 -58.0 -2.8 0.471 151.2
SELL_c1.0_T240 K_OPT3 A tier T1 | 219092 1094 0.499 36.9 31.5 41.9 0.592 130.8
SELL_c1.0_T240 K_OPT3 A tier T2 | 1095287 6584 0.601 1.0 -0.7 6.2 0.613 124.6
SELL_c1.0_T240 K_OPT3 A tier T3 | 1957473 13476 0.688 4.6 -0.1 10.0 0.675 107.6
SELL_c1.0_T240 K_OPT3 A wick1m iso | 0 641 NA 52.0 56.8 58.6 0.824 55.2
SELL_c1.0_T240 K_OPT3 A wick1m na | 0 2 NA 187.3 187.3 191.2 1.000 0.0
SELL_c1.0_T240 K_OPT3 A wick1m not | 0 20511 NA 3.7 -0.4 8.9 0.646 115.9
SELL_c1.0_T240 K_OPT3 A year y2021 | 533832 3260 0.611 -4.7 -3.5 -0.4 0.605 127.5
SELL_c1.0_T240 K_OPT3 A year y2022 | 1190474 6765 0.568 26.3 1.8 32.1 0.653 114.4
SELL_c1.0_T240 K_OPT3 A year y2023 | 1547546 11129 0.719 -4.9 2.4 0.4 0.664 110.0
SELL_c1.0_T240 K_OPT3 B condB no | 5274788 27360 0.519 -11.1 1.7 -2.7 0.653 111.0
SELL_c1.0_T240 K_OPT3 B condB yes | 672754 7905 1.175 -39.6 -11.6 -33.2 0.580 127.6
SELL_c1.0_T240 K_OPT3 B hour h0 | 248476 2349 0.945 11.0 15.0 19.3 0.614 115.8
SELL_c1.0_T240 K_OPT3 B hour h1 | 248133 1217 0.490 -21.2 -19.6 -13.7 0.626 119.8
SELL_c1.0_T240 K_OPT3 B hour h10 | 247734 1067 0.431 11.4 15.9 22.4 0.734 97.4
SELL_c1.0_T240 K_OPT3 B hour h11 | 247515 1118 0.452 52.4 44.9 62.5 0.777 90.4
SELL_c1.0_T240 K_OPT3 B hour h12 | 247856 1838 0.742 -71.6 -23.1 -64.1 0.570 127.8
SELL_c1.0_T240 K_OPT3 B hour h13 | 248119 1814 0.731 -106.2 -26.3 -98.3 0.619 116.1
SELL_c1.0_T240 K_OPT3 B hour h14 | 248377 2398 0.965 -45.8 -24.8 -39.1 0.606 117.7
SELL_c1.0_T240 K_OPT3 B hour h15 | 248617 2022 0.813 -50.0 5.2 -42.4 0.608 118.3
SELL_c1.0_T240 K_OPT3 B hour h16 | 248702 2170 0.873 -4.9 37.5 0.3 0.632 113.5
SELL_c1.0_T240 K_OPT3 B hour h17 | 248455 1629 0.656 -49.5 14.4 -43.0 0.524 135.0
SELL_c1.0_T240 K_OPT3 B hour h18 | 247632 1338 0.540 31.3 17.3 37.7 0.673 107.0
SELL_c1.0_T240 K_OPT3 B hour h19 | 247437 1109 0.448 -46.9 -19.4 -39.8 0.614 118.5
SELL_c1.0_T240 K_OPT3 B hour h2 | 248008 1173 0.473 -12.2 -5.1 -4.3 0.617 121.1
SELL_c1.0_T240 K_OPT3 B hour h20 | 247711 993 0.401 -6.0 3.1 1.6 0.697 98.9
SELL_c1.0_T240 K_OPT3 B hour h21 | 247307 1314 0.531 -36.0 -37.2 -28.9 0.632 114.5
SELL_c1.0_T240 K_OPT3 B hour h22 | 247189 1282 0.519 37.8 12.0 46.1 0.684 107.1
SELL_c1.0_T240 K_OPT3 B hour h23 | 246684 1154 0.468 29.7 -3.3 37.8 0.745 87.8
SELL_c1.0_T240 K_OPT3 B hour h3 | 247701 1220 0.493 -16.3 -21.8 -9.4 0.623 121.7
SELL_c1.0_T240 K_OPT3 B hour h4 | 247650 1034 0.418 -111.2 -101.1 -102.1 0.633 117.4
SELL_c1.0_T240 K_OPT3 B hour h5 | 247405 1168 0.472 -61.3 -29.5 -52.0 0.603 123.0
SELL_c1.0_T240 K_OPT3 B hour h6 | 247448 1473 0.595 15.9 18.5 24.5 0.587 126.8
SELL_c1.0_T240 K_OPT3 B hour h7 | 247509 1501 0.606 54.8 37.5 67.6 0.768 96.9
SELL_c1.0_T240 K_OPT3 B hour h8 | 248095 1680 0.677 -3.9 -1.0 4.3 0.560 132.9
SELL_c1.0_T240 K_OPT3 B hour h9 | 247782 1204 0.486 34.4 27.2 41.9 0.736 95.5
SELL_c1.0_T240 K_OPT3 B mkt idio | 0 23943 NA 4.8 4.5 14.0 0.713 97.6
SELL_c1.0_T240 K_OPT3 B mkt market | 0 11322 NA -64.5 -13.5 -59.3 0.476 150.8
SELL_c1.0_T240 K_OPT3 B qvratio 1_10 | 0 6228 NA -44.9 -15.4 -38.8 0.486 154.1
SELL_c1.0_T240 K_OPT3 B qvratio gt10 | 0 28834 NA -11.2 2.2 -2.8 0.672 105.6
SELL_c1.0_T240 K_OPT3 B qvratio lt1 | 0 203 NA -75.1 -61.4 -70.7 0.305 191.7
SELL_c1.0_T240 K_OPT3 B tier T1 | 175370 748 0.427 -40.4 9.4 -36.7 0.483 152.4
SELL_c1.0_T240 K_OPT3 B tier T2 | 875827 3820 0.436 -39.9 -16.3 -33.7 0.526 143.3
SELL_c1.0_T240 K_OPT3 B tier T3 | 4896345 30697 0.627 -14.1 0.3 -5.9 0.654 110.2
SELL_c1.0_T240 K_OPT3 B wick1m iso | 0 1310 NA 129.0 129.1 136.7 0.867 41.6
SELL_c1.0_T240 K_OPT3 B wick1m na | 0 3 NA 137.2 144.0 140.8 0.667 80.3
SELL_c1.0_T240 K_OPT3 B wick1m not | 0 33952 NA -23.1 -6.3 -15.2 0.628 117.5
SELL_c1.0_T240 K_OPT3 B year y2024 | 2304866 14394 0.625 -31.2 -13.5 -26.4 0.594 127.4
SELL_c1.0_T240 K_OPT3 B year y2025 | 3642676 20871 0.573 -8.0 7.2 2.0 0.667 105.9
SELL_c1.0_T240 K_PESS A condB no | 2988434 16316 0.546 -18.7 -12.8 -5.8 0.622 119.0
SELL_c1.0_T240 K_PESS A condB yes | 283418 4335 1.530 36.1 -3.8 48.4 0.660 109.2
SELL_c1.0_T240 K_PESS A hour h0 | 136608 1625 1.190 9.3 6.4 20.8 0.611 119.9
SELL_c1.0_T240 K_PESS A hour h1 | 136358 868 0.637 31.1 17.7 42.7 0.608 122.8
SELL_c1.0_T240 K_PESS A hour h10 | 136344 788 0.578 11.4 -16.3 22.8 0.678 113.9
SELL_c1.0_T240 K_PESS A hour h11 | 136231 619 0.454 5.4 3.5 16.3 0.698 103.8
SELL_c1.0_T240 K_PESS A hour h12 | 136350 1014 0.744 -30.4 -31.6 -16.4 0.614 120.1
SELL_c1.0_T240 K_PESS A hour h13 | 136358 1308 0.959 24.2 -14.4 37.4 0.654 109.5
SELL_c1.0_T240 K_PESS A hour h14 | 136480 1405 1.029 -48.8 -4.8 -34.4 0.565 133.8
SELL_c1.0_T240 K_PESS A hour h15 | 136465 1117 0.819 -19.3 -4.9 -4.0 0.608 115.3
SELL_c1.0_T240 K_PESS A hour h16 | 136566 1317 0.964 49.2 16.1 60.2 0.699 103.0
SELL_c1.0_T240 K_PESS A hour h17 | 136256 900 0.661 35.5 17.9 46.3 0.698 99.7
SELL_c1.0_T240 K_PESS A hour h18 | 136353 956 0.701 8.2 19.9 19.9 0.633 109.1
SELL_c1.0_T240 K_PESS A hour h19 | 136234 722 0.530 -134.3 -115.0 -122.4 0.609 115.1
SELL_c1.0_T240 K_PESS A hour h2 | 136422 667 0.489 -88.0 -78.4 -75.8 0.574 130.3
SELL_c1.0_T240 K_PESS A hour h20 | 136351 619 0.454 -22.5 -6.6 -10.1 0.609 118.8
SELL_c1.0_T240 K_PESS A hour h21 | 136217 594 0.436 39.2 49.9 51.9 0.609 118.4
SELL_c1.0_T240 K_PESS A hour h22 | 136111 834 0.613 -37.1 -60.3 -23.5 0.550 132.6
SELL_c1.0_T240 K_PESS A hour h23 | 136059 575 0.423 23.8 20.0 37.3 0.711 92.5
SELL_c1.0_T240 K_PESS A hour h3 | 136252 582 0.427 -59.0 -61.6 -46.3 0.586 130.8
SELL_c1.0_T240 K_PESS A hour h4 | 136260 504 0.370 -42.0 -27.8 -26.0 0.579 128.3
SELL_c1.0_T240 K_PESS A hour h5 | 136127 611 0.449 28.0 2.0 41.7 0.661 119.7
SELL_c1.0_T240 K_PESS A hour h6 | 136266 710 0.521 0.5 -14.7 14.4 0.655 116.2
SELL_c1.0_T240 K_PESS A hour h7 | 136230 775 0.569 -33.9 -46.7 -19.2 0.653 113.1
SELL_c1.0_T240 K_PESS A hour h8 | 136565 830 0.608 13.9 15.8 25.2 0.636 121.4
SELL_c1.0_T240 K_PESS A hour h9 | 136389 711 0.521 -3.3 -4.5 9.1 0.629 120.2
SELL_c1.0_T240 K_PESS A mkt idio | 0 13942 NA -2.8 -2.6 10.1 0.657 110.3
SELL_c1.0_T240 K_PESS A mkt market | 0 6709 NA -16.3 -28.1 -4.0 0.574 130.7
SELL_c1.0_T240 K_PESS A qvratio 1_10 | 0 3658 NA 12.0 -15.7 25.1 0.589 134.4
SELL_c1.0_T240 K_PESS A qvratio gt10 | 0 16947 NA -11.4 -9.8 1.2 0.639 113.1
SELL_c1.0_T240 K_PESS A qvratio lt1 | 0 46 NA 20.5 -35.9 35.7 0.543 136.7
SELL_c1.0_T240 K_PESS A tier T1 | 219092 1087 0.496 30.6 25.3 41.1 0.582 131.6
SELL_c1.0_T240 K_PESS A tier T2 | 1095287 6461 0.590 -9.2 -11.0 2.5 0.597 127.1
SELL_c1.0_T240 K_PESS A tier T3 | 1957473 13103 0.669 -9.4 -13.9 4.1 0.650 110.7
SELL_c1.0_T240 K_PESS A wick1m iso | 0 641 NA 38.4 43.5 53.5 0.532 57.9
SELL_c1.0_T240 K_PESS A wick1m na | 0 3 NA 139.8 134.7 171.6 0.000 80.3
SELL_c1.0_T240 K_PESS A wick1m not | 0 20007 NA -8.7 -12.7 4.0 0.633 118.8
SELL_c1.0_T240 K_PESS A year y2021 | 533832 3248 0.608 -13.2 -12.1 -1.2 0.595 127.9
SELL_c1.0_T240 K_PESS A year y2022 | 1190474 6604 0.555 15.2 -9.5 28.2 0.636 116.5
SELL_c1.0_T240 K_PESS A year y2023 | 1547546 10799 0.698 -19.1 -11.5 -6.3 0.637 113.9
SELL_c1.0_T240 K_PESS B condB no | 5274788 26890 0.510 -23.7 -10.7 -7.2 0.628 112.6
SELL_c1.0_T240 K_PESS B condB yes | 672754 7747 1.152 -52.9 -25.8 -37.5 0.543 129.3
SELL_c1.0_T240 K_PESS B hour h0 | 248476 2308 0.929 -1.4 2.3 15.5 0.588 117.5
SELL_c1.0_T240 K_PESS B hour h1 | 248133 1193 0.481 -33.5 -31.3 -17.8 0.616 120.9
SELL_c1.0_T240 K_PESS B hour h10 | 247734 1048 0.423 -0.4 3.9 17.9 0.712 99.5
SELL_c1.0_T240 K_PESS B hour h11 | 247515 1099 0.444 40.9 33.1 57.9 0.754 91.6
SELL_c1.0_T240 K_PESS B hour h12 | 247856 1813 0.731 -84.3 -36.0 -67.9 0.550 129.2
SELL_c1.0_T240 K_PESS B hour h13 | 248119 1791 0.722 -119.0 -38.5 -102.9 0.594 117.7
SELL_c1.0_T240 K_PESS B hour h14 | 248377 2339 0.942 -62.1 -39.5 -47.0 0.585 120.3
SELL_c1.0_T240 K_PESS B hour h15 | 248617 1981 0.797 -64.6 -7.2 -48.5 0.588 120.3
SELL_c1.0_T240 K_PESS B hour h16 | 248702 2139 0.860 -17.3 25.8 -3.8 0.598 114.8
SELL_c1.0_T240 K_PESS B hour h17 | 248455 1603 0.645 -63.1 0.7 -47.2 0.502 136.8
SELL_c1.0_T240 K_PESS B hour h18 | 247632 1315 0.531 20.3 6.1 34.6 0.643 108.9
SELL_c1.0_T240 K_PESS B hour h19 | 247437 1086 0.439 -59.3 -31.6 -43.5 0.583 119.8
SELL_c1.0_T240 K_PESS B hour h2 | 248008 1151 0.464 -23.7 -17.5 -7.1 0.593 122.5
SELL_c1.0_T240 K_PESS B hour h20 | 247711 969 0.392 -14.7 -7.5 0.6 0.672 99.3
SELL_c1.0_T240 K_PESS B hour h21 | 247307 1286 0.520 -47.9 -50.6 -32.5 0.576 116.0
SELL_c1.0_T240 K_PESS B hour h22 | 247189 1260 0.510 23.7 -3.9 40.0 0.610 109.6
SELL_c1.0_T240 K_PESS B hour h23 | 246684 1140 0.462 17.0 -18.6 32.8 0.691 90.0
SELL_c1.0_T240 K_PESS B hour h3 | 247701 1187 0.479 -27.9 -34.4 -12.7 0.602 122.1
SELL_c1.0_T240 K_PESS B hour h4 | 247650 1014 0.409 -126.6 -115.7 -109.0 0.608 119.5
SELL_c1.0_T240 K_PESS B hour h5 | 247405 1140 0.461 -75.9 -44.5 -57.7 0.579 124.4
SELL_c1.0_T240 K_PESS B hour h6 | 247448 1458 0.589 3.2 4.9 20.5 0.564 128.3
SELL_c1.0_T240 K_PESS B hour h7 | 247509 1479 0.598 45.8 28.1 65.7 0.739 99.1
SELL_c1.0_T240 K_PESS B hour h8 | 248095 1652 0.666 -15.9 -13.1 1.4 0.539 134.4
SELL_c1.0_T240 K_PESS B hour h9 | 247782 1186 0.479 20.0 12.8 34.9 0.705 98.0
SELL_c1.0_T240 K_PESS B mkt idio | 0 23558 NA -6.6 -7.2 10.2 0.682 99.3
SELL_c1.0_T240 K_PESS B mkt market | 0 11079 NA -80.3 -28.8 -65.4 0.454 152.6
SELL_c1.0_T240 K_PESS B qvratio 1_10 | 0 6066 NA -58.3 -29.2 -42.8 0.476 155.9
SELL_c1.0_T240 K_PESS B qvratio gt10 | 0 28374 NA -23.7 -10.4 -7.4 0.639 107.4
SELL_c1.0_T240 K_PESS B qvratio lt1 | 0 197 NA -93.5 -73.0 -77.6 0.284 195.1
SELL_c1.0_T240 K_PESS B tier T1 | 175370 745 0.425 -46.8 2.8 -37.4 0.474 152.9
SELL_c1.0_T240 K_PESS B tier T2 | 875827 3784 0.432 -50.0 -25.6 -36.6 0.510 144.3
SELL_c1.0_T240 K_PESS B tier T3 | 4896345 30108 0.615 -27.3 -13.0 -10.6 0.625 111.9
SELL_c1.0_T240 K_PESS B wick1m iso | 0 1301 NA 117.3 114.0 135.1 0.445 42.9
SELL_c1.0_T240 K_PESS B wick1m na | 0 3 NA 125.9 133.7 140.8 0.333 80.7
SELL_c1.0_T240 K_PESS B wick1m not | 0 33333 NA -36.0 -19.1 -19.8 0.615 119.2
SELL_c1.0_T240 K_PESS B year y2024 | 2304866 14161 0.614 -42.6 -24.8 -29.4 0.579 129.0
SELL_c1.0_T240 K_PESS B year y2025 | 3642676 20476 0.562 -21.6 -6.6 -3.3 0.630 107.6
SELL_c1.0_T1440 K_OPT3 A condB no | 2988434 16711 0.559 2.7 10.7 11.2 0.816 403.4
SELL_c1.0_T1440 K_OPT3 A condB yes | 283418 4442 1.567 83.3 20.7 89.5 0.866 333.4
SELL_c1.0_T1440 K_OPT3 A hour h0 | 136608 1670 1.223 58.4 48.5 65.6 0.845 382.3
SELL_c1.0_T1440 K_OPT3 A hour h1 | 136358 890 0.653 68.3 44.4 75.9 0.873 366.0
SELL_c1.0_T1440 K_OPT3 A hour h10 | 136344 806 0.591 27.1 8.5 34.8 0.847 341.7
SELL_c1.0_T1440 K_OPT3 A hour h11 | 136231 633 0.465 35.9 32.9 45.5 0.855 324.2
SELL_c1.0_T1440 K_OPT3 A hour h12 | 136350 1034 0.758 7.2 -35.2 15.9 0.813 407.9
SELL_c1.0_T1440 K_OPT3 A hour h13 | 136358 1331 0.976 94.3 36.0 101.8 0.842 352.4
SELL_c1.0_T1440 K_OPT3 A hour h14 | 136480 1434 1.051 -3.5 34.5 5.0 0.755 492.2
SELL_c1.0_T1440 K_OPT3 A hour h15 | 136465 1136 0.832 -21.5 -15.1 -11.9 0.777 441.3
SELL_c1.0_T1440 K_OPT3 A hour h16 | 136566 1345 0.985 55.2 29.2 62.2 0.868 317.5
SELL_c1.0_T1440 K_OPT3 A hour h17 | 136256 932 0.684 72.6 72.4 78.0 0.872 307.2
SELL_c1.0_T1440 K_OPT3 A hour h18 | 136353 981 0.719 -6.7 38.3 -0.0 0.807 408.8
SELL_c1.0_T1440 K_OPT3 A hour h19 | 136234 737 0.541 -83.4 -47.2 -77.6 0.731 492.1
SELL_c1.0_T1440 K_OPT3 A hour h2 | 136422 682 0.500 -75.5 -82.1 -66.5 0.779 471.1
SELL_c1.0_T1440 K_OPT3 A hour h20 | 136351 635 0.466 41.8 70.3 47.4 0.822 421.3
SELL_c1.0_T1440 K_OPT3 A hour h21 | 136217 608 0.446 135.0 117.9 140.4 0.878 329.7
SELL_c1.0_T1440 K_OPT3 A hour h22 | 136111 859 0.631 9.6 -31.5 15.5 0.786 479.1
SELL_c1.0_T1440 K_OPT3 A hour h23 | 136059 595 0.437 91.5 105.0 99.3 0.887 277.3
SELL_c1.0_T1440 K_OPT3 A hour h3 | 136252 603 0.443 -94.9 -99.5 -82.8 0.813 424.2
SELL_c1.0_T1440 K_OPT3 A hour h4 | 136260 519 0.381 -55.8 -58.8 -42.6 0.819 448.5
SELL_c1.0_T1440 K_OPT3 A hour h5 | 136127 632 0.464 43.0 19.2 53.2 0.866 334.9
SELL_c1.0_T1440 K_OPT3 A hour h6 | 136266 722 0.530 8.8 -5.6 17.9 0.838 362.6
SELL_c1.0_T1440 K_OPT3 A hour h7 | 136230 793 0.582 -62.5 -59.3 -50.1 0.828 362.1
SELL_c1.0_T1440 K_OPT3 A hour h8 | 136565 850 0.622 34.0 25.5 40.2 0.841 366.8
SELL_c1.0_T1440 K_OPT3 A hour h9 | 136389 726 0.532 -16.8 -24.6 -6.6 0.831 379.7
SELL_c1.0_T1440 K_OPT3 A mkt idio | 0 14217 NA 24.9 23.6 34.4 0.848 352.1
SELL_c1.0_T1440 K_OPT3 A mkt market | 0 6936 NA 8.6 -9.3 13.8 0.782 463.8
SELL_c1.0_T1440 K_OPT3 A qvratio 1_10 | 0 3815 NA 34.0 -3.6 39.7 0.831 411.4
SELL_c1.0_T1440 K_OPT3 A qvratio gt10 | 0 17287 NA 16.7 16.7 25.3 0.826 383.2
SELL_c1.0_T1440 K_OPT3 A qvratio lt1 | 0 51 NA -86.4 -61.1 -82.6 0.745 543.9
SELL_c1.0_T1440 K_OPT3 A tier T1 | 219092 1094 0.499 25.3 33.8 30.7 0.779 464.3
SELL_c1.0_T1440 K_OPT3 A tier T2 | 1095287 6584 0.601 16.3 12.3 22.9 0.807 430.8
SELL_c1.0_T1440 K_OPT3 A tier T3 | 1957473 13475 0.688 20.7 11.4 29.8 0.840 362.0
SELL_c1.0_T1440 K_OPT3 A wick1m iso | 0 641 NA 53.8 60.5 65.4 0.895 213.2
SELL_c1.0_T1440 K_OPT3 A wick1m na | 0 2 NA 187.3 187.3 191.2 1.000 0.0
SELL_c1.0_T1440 K_OPT3 A wick1m not | 0 20510 NA 18.5 11.3 26.5 0.824 394.2
SELL_c1.0_T1440 K_OPT3 A year y2021 | 533832 3260 0.611 5.7 2.8 9.7 0.810 440.0
SELL_c1.0_T1440 K_OPT3 A year y2022 | 1190474 6764 0.568 42.9 17.5 52.1 0.837 371.7
SELL_c1.0_T1440 K_OPT3 A year y2023 | 1547546 11129 0.719 9.5 13.0 18.1 0.825 384.0
SELL_c1.0_T1440 K_OPT3 B condB no | 5264555 27280 0.518 -12.0 -13.5 6.4 0.822 392.9
SELL_c1.0_T1440 K_OPT3 B condB yes | 672754 7905 1.175 -86.0 -39.8 -73.1 0.735 501.2
SELL_c1.0_T1440 K_OPT3 B hour h0 | 247962 2342 0.944 19.2 22.9 41.1 0.801 429.4
SELL_c1.0_T1440 K_OPT3 B hour h1 | 247620 1214 0.490 -54.2 -16.9 -37.0 0.809 421.5
SELL_c1.0_T1440 K_OPT3 B hour h10 | 247219 1066 0.431 -64.2 -48.4 -31.8 0.860 308.8
SELL_c1.0_T1440 K_OPT3 B hour h11 | 247000 1109 0.449 -75.0 -79.8 -61.7 0.866 288.7
SELL_c1.0_T1440 K_OPT3 B hour h12 | 247337 1828 0.739 -108.0 -50.6 -95.2 0.730 500.8
SELL_c1.0_T1440 K_OPT3 B hour h13 | 247602 1810 0.731 -187.1 -97.4 -175.8 0.708 503.3
SELL_c1.0_T1440 K_OPT3 B hour h14 | 247864 2392 0.965 -57.2 -77.1 -44.7 0.735 477.5
SELL_c1.0_T1440 K_OPT3 B hour h15 | 248107 2019 0.814 -21.1 -3.5 -4.6 0.805 447.6
SELL_c1.0_T1440 K_OPT3 B hour h16 | 248182 2164 0.872 55.8 62.3 63.3 0.850 406.5
SELL_c1.0_T1440 K_OPT3 B hour h17 | 247936 1626 0.656 10.5 2.5 21.5 0.803 545.4
SELL_c1.0_T1440 K_OPT3 B hour h18 | 247632 1338 0.540 40.8 27.5 52.7 0.844 361.4
SELL_c1.0_T1440 K_OPT3 B hour h19 | 247437 1109 0.448 -28.5 -26.7 -14.2 0.770 451.9
SELL_c1.0_T1440 K_OPT3 B hour h2 | 247494 1171 0.473 -59.4 -70.4 -25.7 0.814 424.8
SELL_c1.0_T1440 K_OPT3 B hour h20 | 247711 993 0.401 16.2 24.1 27.3 0.862 334.5
SELL_c1.0_T1440 K_OPT3 B hour h21 | 247307 1314 0.531 -94.3 -86.4 -83.2 0.763 440.6
SELL_c1.0_T1440 K_OPT3 B hour h22 | 246673 1279 0.519 -7.2 -33.0 8.6 0.825 379.6
SELL_c1.0_T1440 K_OPT3 B hour h23 | 246180 1153 0.468 32.4 -10.6 47.7 0.846 327.7
SELL_c1.0_T1440 K_OPT3 B hour h3 | 247202 1215 0.492 -82.3 -68.3 -53.5 0.762 462.1
SELL_c1.0_T1440 K_OPT3 B hour h4 | 247143 1033 0.418 -69.5 -63.0 -43.4 0.807 412.2
SELL_c1.0_T1440 K_OPT3 B hour h5 | 246893 1166 0.472 -112.3 -11.0 -88.5 0.750 467.6
SELL_c1.0_T1440 K_OPT3 B hour h6 | 246945 1471 0.596 96.3 50.0 114.2 0.876 340.0
SELL_c1.0_T1440 K_OPT3 B hour h7 | 247003 1497 0.606 18.5 14.1 46.1 0.874 280.9
SELL_c1.0_T1440 K_OPT3 B hour h8 | 247590 1675 0.677 -46.2 -26.2 -28.8 0.742 482.6
SELL_c1.0_T1440 K_OPT3 B hour h9 | 247270 1201 0.486 67.3 62.8 82.2 0.869 296.6
SELL_c1.0_T1440 K_OPT3 B mkt idio | 0 23868 NA -7.8 -7.1 13.4 0.854 328.0
SELL_c1.0_T1440 K_OPT3 B mkt market | 0 11317 NA -72.6 -45.3 -64.1 0.694 605.5
SELL_c1.0_T1440 K_OPT3 B qvratio 1_10 | 0 6226 NA -77.3 -43.7 -66.5 0.718 573.6
SELL_c1.0_T1440 K_OPT3 B qvratio gt10 | 0 28756 NA -16.9 -13.2 1.7 0.822 380.4
SELL_c1.0_T1440 K_OPT3 B qvratio lt1 | 0 203 NA -192.7 -155.1 -189.4 0.532 835.3
SELL_c1.0_T1440 K_OPT3 B tier T1 | 175170 748 0.427 -54.5 -8.4 -52.3 0.686 619.2
SELL_c1.0_T1440 K_OPT3 B tier T2 | 874828 3817 0.436 -102.8 -84.3 -93.2 0.739 540.0
SELL_c1.0_T1440 K_OPT3 B tier T3 | 4887311 30620 0.627 -18.7 -11.6 -0.3 0.813 397.0
SELL_c1.0_T1440 K_OPT3 B wick1m iso | 0 1308 NA 137.4 134.1 158.4 0.924 152.6
SELL_c1.0_T1440 K_OPT3 B wick1m na | 0 3 NA 87.4 140.4 90.4 0.667 480.3
SELL_c1.0_T1440 K_OPT3 B wick1m not | 0 33874 NA -35.0 -25.3 -18.1 0.797 427.4
SELL_c1.0_T1440 K_OPT3 B year y2024 | 2304866 14392 0.624 -47.5 -21.5 -41.2 0.768 465.9
SELL_c1.0_T1440 K_OPT3 B year y2025 | 3632443 20793 0.572 -15.5 -17.9 9.1 0.826 383.5
SELL_c1.0_T1440 K_PESS A condB no | 2988434 16316 0.546 -8.7 -0.4 6.0 0.799 414.6
SELL_c1.0_T1440 K_PESS A condB yes | 283418 4334 1.529 72.9 9.6 84.6 0.849 344.7
SELL_c1.0_T1440 K_PESS A hour h0 | 136608 1625 1.190 48.6 39.1 61.5 0.829 397.8
SELL_c1.0_T1440 K_PESS A hour h1 | 136358 868 0.637 59.4 35.1 72.4 0.858 375.1
SELL_c1.0_T1440 K_PESS A hour h10 | 136344 788 0.578 11.5 -7.5 25.2 0.836 355.7
SELL_c1.0_T1440 K_PESS A hour h11 | 136231 618 0.454 32.7 29.6 48.1 0.841 330.0
SELL_c1.0_T1440 K_PESS A hour h12 | 136350 1014 0.744 -3.3 -44.3 11.7 0.797 416.0
SELL_c1.0_T1440 K_PESS A hour h13 | 136358 1308 0.959 86.5 27.1 99.7 0.829 362.2
SELL_c1.0_T1440 K_PESS A hour h14 | 136480 1405 1.029 -14.1 23.1 1.0 0.740 502.1
SELL_c1.0_T1440 K_PESS A hour h15 | 136465 1117 0.819 -32.9 -26.9 -17.1 0.755 447.9
SELL_c1.0_T1440 K_PESS A hour h16 | 136566 1317 0.964 45.2 17.9 58.1 0.846 327.5
SELL_c1.0_T1440 K_PESS A hour h17 | 136256 900 0.661 61.6 60.0 72.4 0.851 325.0
SELL_c1.0_T1440 K_PESS A hour h18 | 136353 956 0.701 -26.8 21.7 -14.0 0.780 430.3
SELL_c1.0_T1440 K_PESS A hour h19 | 136234 722 0.530 -92.3 -56.6 -79.6 0.722 495.2
SELL_c1.0_T1440 K_PESS A hour h2 | 136422 667 0.489 -91.4 -98.1 -75.3 0.760 483.2
SELL_c1.0_T1440 K_PESS A hour h20 | 136351 619 0.454 35.0 62.6 46.3 0.805 428.9
SELL_c1.0_T1440 K_PESS A hour h21 | 136217 594 0.436 129.3 111.3 140.0 0.850 334.5
SELL_c1.0_T1440 K_PESS A hour h22 | 136111 834 0.613 -10.6 -49.1 1.7 0.764 502.9
SELL_c1.0_T1440 K_PESS A hour h23 | 136059 575 0.423 83.2 95.6 96.4 0.868 290.2
SELL_c1.0_T1440 K_PESS A hour h3 | 136252 582 0.427 -109.7 -113.6 -90.9 0.794 439.9
SELL_c1.0_T1440 K_PESS A hour h4 | 136260 504 0.370 -70.4 -73.9 -51.2 0.804 456.4
SELL_c1.0_T1440 K_PESS A hour h5 | 136127 611 0.449 27.0 6.9 42.8 0.849 351.7
SELL_c1.0_T1440 K_PESS A hour h6 | 136266 710 0.521 -1.1 -15.6 14.2 0.832 367.1
SELL_c1.0_T1440 K_PESS A hour h7 | 136230 775 0.569 -73.3 -69.8 -54.7 0.814 373.6
SELL_c1.0_T1440 K_PESS A hour h8 | 136565 830 0.608 26.0 17.2 37.9 0.831 371.1
SELL_c1.0_T1440 K_PESS A hour h9 | 136389 711 0.521 -27.5 -35.3 -11.3 0.814 389.8
SELL_c1.0_T1440 K_PESS A mkt idio | 0 13941 NA 14.4 13.0 29.8 0.830 362.0
SELL_c1.0_T1440 K_PESS A mkt market | 0 6709 NA -4.1 -21.8 7.3 0.767 478.9
SELL_c1.0_T1440 K_PESS A qvratio 1_10 | 0 3658 NA 20.7 -17.9 32.3 0.822 424.5
SELL_c1.0_T1440 K_PESS A qvratio gt10 | 0 16946 NA 6.2 6.1 20.8 0.807 394.5
SELL_c1.0_T1440 K_PESS A qvratio lt1 | 0 46 NA -136.6 -82.9 -123.5 0.761 477.0
SELL_c1.0_T1440 K_PESS A tier T1 | 219092 1087 0.496 20.0 27.2 30.2 0.769 467.2
SELL_c1.0_T1440 K_PESS A tier T2 | 1095287 6461 0.590 7.1 2.6 19.1 0.795 439.7
SELL_c1.0_T1440 K_PESS A tier T3 | 1957473 13102 0.669 8.1 -0.9 23.5 0.820 374.8
SELL_c1.0_T1440 K_PESS A wick1m iso | 0 641 NA 43.6 50.9 63.1 0.607 224.7
SELL_c1.0_T1440 K_PESS A wick1m na | 0 3 NA 92.9 101.4 123.7 0.000 480.3
SELL_c1.0_T1440 K_PESS A wick1m not | 0 20006 NA 7.3 0.1 21.2 0.816 405.6
SELL_c1.0_T1440 K_PESS A year y2021 | 533832 3248 0.608 -0.0 -2.9 9.9 0.802 440.9
SELL_c1.0_T1440 K_PESS A year y2022 | 1190474 6603 0.555 33.3 7.6 48.2 0.823 380.3
SELL_c1.0_T1440 K_PESS A year y2023 | 1547546 10799 0.698 -4.2 -0.5 10.6 0.804 399.7
SELL_c1.0_T1440 K_PESS B condB no | 5264555 26811 0.509 -22.9 -24.8 2.1 0.798 399.5
SELL_c1.0_T1440 K_PESS B condB yes | 672754 7747 1.152 -97.9 -52.6 -77.4 0.701 507.8
SELL_c1.0_T1440 K_PESS B hour h0 | 247962 2301 0.928 7.9 11.8 36.8 0.776 438.1
SELL_c1.0_T1440 K_PESS B hour h1 | 247620 1190 0.481 -62.3 -27.5 -38.2 0.801 421.6
SELL_c1.0_T1440 K_PESS B hour h10 | 247219 1047 0.424 -77.1 -61.1 -38.4 0.842 317.2
SELL_c1.0_T1440 K_PESS B hour h11 | 247000 1090 0.441 -87.7 -93.2 -67.3 0.845 293.7
SELL_c1.0_T1440 K_PESS B hour h12 | 247337 1803 0.729 -118.5 -62.1 -98.3 0.713 505.4
SELL_c1.0_T1440 K_PESS B hour h13 | 247602 1787 0.722 -199.7 -109.7 -180.8 0.685 510.2
SELL_c1.0_T1440 K_PESS B hour h14 | 247864 2333 0.941 -72.0 -90.0 -52.1 0.718 490.6
SELL_c1.0_T1440 K_PESS B hour h15 | 248107 1978 0.797 -35.6 -16.5 -12.4 0.784 458.9
SELL_c1.0_T1440 K_PESS B hour h16 | 248182 2133 0.859 46.3 53.2 60.0 0.817 413.0
SELL_c1.0_T1440 K_PESS B hour h17 | 247936 1600 0.645 0.7 -8.1 18.3 0.783 552.4
SELL_c1.0_T1440 K_PESS B hour h18 | 247632 1315 0.531 32.5 18.3 50.6 0.817 366.9
SELL_c1.0_T1440 K_PESS B hour h19 | 247437 1086 0.439 -42.8 -41.4 -21.3 0.738 457.1
SELL_c1.0_T1440 K_PESS B hour h2 | 247494 1149 0.464 -69.4 -81.7 -28.6 0.794 430.4
SELL_c1.0_T1440 K_PESS B hour h20 | 247711 969 0.392 12.8 16.6 29.8 0.841 334.1
SELL_c1.0_T1440 K_PESS B hour h21 | 247307 1286 0.520 -104.3 -98.2 -86.0 0.709 446.0
SELL_c1.0_T1440 K_PESS B hour h22 | 246673 1257 0.510 -20.0 -48.0 2.7 0.753 387.9
SELL_c1.0_T1440 K_PESS B hour h23 | 246180 1139 0.463 21.3 -26.3 43.3 0.795 336.8
SELL_c1.0_T1440 K_PESS B hour h3 | 247202 1182 0.478 -92.8 -80.1 -56.3 0.745 461.6
SELL_c1.0_T1440 K_PESS B hour h4 | 247143 1013 0.410 -80.2 -73.5 -47.2 0.787 420.2
SELL_c1.0_T1440 K_PESS B hour h5 | 246893 1139 0.461 -122.0 -21.6 -90.3 0.728 472.0
SELL_c1.0_T1440 K_PESS B hour h6 | 246945 1456 0.590 86.6 38.6 110.4 0.857 345.7
SELL_c1.0_T1440 K_PESS B hour h7 | 247003 1475 0.597 10.1 5.8 43.9 0.851 285.9
SELL_c1.0_T1440 K_PESS B hour h8 | 247590 1647 0.665 -58.0 -37.9 -33.3 0.721 489.9
SELL_c1.0_T1440 K_PESS B hour h9 | 247270 1183 0.478 50.5 45.7 71.9 0.843 305.2
SELL_c1.0_T1440 K_PESS B mkt idio | 0 23484 NA -16.5 -16.3 11.1 0.825 333.5
SELL_c1.0_T1440 K_PESS B mkt market | 0 11074 NA -88.9 -62.4 -72.7 0.673 615.3
SELL_c1.0_T1440 K_PESS B qvratio 1_10 | 0 6064 NA -93.2 -60.2 -75.0 0.711 582.9
SELL_c1.0_T1440 K_PESS B qvratio gt10 | 0 28297 NA -27.2 -23.9 -1.9 0.792 386.7
SELL_c1.0_T1440 K_PESS B qvratio lt1 | 0 197 NA -196.1 -158.5 -183.9 0.528 852.4
SELL_c1.0_T1440 K_PESS B tier T1 | 175170 745 0.425 -60.7 -14.7 -53.3 0.678 620.8
SELL_c1.0_T1440 K_PESS B tier T2 | 874828 3781 0.432 -113.0 -94.1 -97.1 0.726 544.1
SELL_c1.0_T1440 K_PESS B tier T3 | 4887311 30032 0.615 -30.0 -23.5 -4.6 0.785 403.8
SELL_c1.0_T1440 K_PESS B wick1m iso | 0 1299 NA 125.9 119.2 156.5 0.502 155.8
SELL_c1.0_T1440 K_PESS B wick1m na | 0 3 NA 76.2 130.1 90.4 0.333 480.7
SELL_c1.0_T1440 K_PESS B wick1m not | 0 33256 NA -46.2 -37.0 -22.5 0.787 434.3
SELL_c1.0_T1440 K_PESS B year y2024 | 2304866 14159 0.614 -57.4 -31.6 -44.4 0.755 472.2
SELL_c1.0_T1440 K_PESS B year y2025 | 3632443 20399 0.562 -27.4 -30.7 4.2 0.791 390.2
SELL_c1.5_T240 K_OPT3 A condB no | 2988434 5625 0.188 -15.4 -8.1 -8.6 0.601 124.3
SELL_c1.5_T240 K_OPT3 A condB yes | 283418 1418 0.500 103.5 67.9 110.9 0.681 112.6
SELL_c1.5_T240 K_OPT3 A hour h0 | 136608 554 0.406 23.9 19.9 28.1 0.549 137.5
SELL_c1.5_T240 K_OPT3 A hour h1 | 136358 243 0.178 11.7 10.9 16.0 0.527 138.5
SELL_c1.5_T240 K_OPT3 A hour h10 | 136344 250 0.183 31.7 17.7 36.1 0.644 120.7
SELL_c1.5_T240 K_OPT3 A hour h11 | 136231 217 0.159 -2.3 0.3 1.6 0.631 116.7
SELL_c1.5_T240 K_OPT3 A hour h12 | 136350 309 0.227 -7.7 -14.2 1.7 0.660 114.9
SELL_c1.5_T240 K_OPT3 A hour h13 | 136358 533 0.391 61.1 47.9 69.9 0.679 120.2
SELL_c1.5_T240 K_OPT3 A hour h14 | 136480 502 0.368 -85.7 -4.4 -78.4 0.476 146.7
SELL_c1.5_T240 K_OPT3 A hour h15 | 136465 405 0.297 -10.5 -14.2 2.0 0.644 113.5
SELL_c1.5_T240 K_OPT3 A hour h16 | 136566 513 0.376 100.7 57.7 105.5 0.708 105.2
SELL_c1.5_T240 K_OPT3 A hour h17 | 136256 296 0.217 57.7 38.7 63.4 0.676 106.8
SELL_c1.5_T240 K_OPT3 A hour h18 | 136353 314 0.230 102.0 94.5 107.8 0.685 97.6
SELL_c1.5_T240 K_OPT3 A hour h19 | 136234 248 0.182 -258.4 -223.7 -254.3 0.613 116.1
SELL_c1.5_T240 K_OPT3 A hour h2 | 136422 228 0.167 -46.2 -43.7 -42.1 0.553 131.6
SELL_c1.5_T240 K_OPT3 A hour h20 | 136351 195 0.143 3.5 36.4 10.6 0.641 121.5
SELL_c1.5_T240 K_OPT3 A hour h21 | 136217 170 0.125 199.6 211.3 204.6 0.694 100.0
SELL_c1.5_T240 K_OPT3 A hour h22 | 136111 312 0.229 11.5 -48.2 20.1 0.561 127.8
SELL_c1.5_T240 K_OPT3 A hour h23 | 136059 172 0.126 -8.4 27.0 2.4 0.640 108.6
SELL_c1.5_T240 K_OPT3 A hour h3 | 136252 183 0.134 -92.9 -97.7 -86.7 0.519 138.5
SELL_c1.5_T240 K_OPT3 A hour h4 | 136260 195 0.143 23.0 25.5 35.0 0.590 129.1
SELL_c1.5_T240 K_OPT3 A hour h5 | 136127 217 0.159 47.6 33.5 55.2 0.650 122.5
SELL_c1.5_T240 K_OPT3 A hour h6 | 136266 246 0.181 17.8 -2.9 27.5 0.606 129.1
SELL_c1.5_T240 K_OPT3 A hour h7 | 136230 255 0.187 -86.9 -92.0 -77.6 0.620 122.9
SELL_c1.5_T240 K_OPT3 A hour h8 | 136565 271 0.198 22.4 19.4 26.5 0.638 121.3
SELL_c1.5_T240 K_OPT3 A hour h9 | 136389 215 0.158 22.0 27.3 27.3 0.623 124.5
SELL_c1.5_T240 K_OPT3 A mkt idio | 0 5099 NA -0.2 2.6 7.3 0.633 118.6
SELL_c1.5_T240 K_OPT3 A mkt market | 0 1944 NA 31.4 19.2 36.6 0.575 130.6
SELL_c1.5_T240 K_OPT3 A qvratio 1_10 | 0 584 NA 112.1 90.3 120.2 0.661 126.8
SELL_c1.5_T240 K_OPT3 A qvratio gt10 | 0 6456 NA -0.8 -0.3 5.9 0.613 121.5
SELL_c1.5_T240 K_OPT3 A qvratio lt1 | 0 3 NA 35.9 -7.5 41.3 0.667 19.0
SELL_c1.5_T240 K_OPT3 A tier T1 | 219092 330 0.151 -9.9 -12.6 -2.4 0.530 141.0
SELL_c1.5_T240 K_OPT3 A tier T2 | 1095287 2008 0.183 30.8 27.6 36.8 0.575 132.5
SELL_c1.5_T240 K_OPT3 A tier T3 | 1957473 4705 0.240 0.4 -0.1 7.6 0.641 116.0
SELL_c1.5_T240 K_OPT3 A wick1m iso | 0 264 NA 172.5 173.5 180.8 0.799 58.1
SELL_c1.5_T240 K_OPT3 A wick1m not | 0 6779 NA 2.2 0.7 9.0 0.610 124.4
SELL_c1.5_T240 K_OPT3 A year y2021 | 533832 1036 0.194 0.3 -6.6 5.8 0.551 138.7
SELL_c1.5_T240 K_OPT3 A year y2022 | 1190474 2175 0.183 24.9 11.2 32.4 0.643 117.7
SELL_c1.5_T240 K_OPT3 A year y2023 | 1547546 3832 0.248 1.5 8.6 8.4 0.620 119.8
SELL_c1.5_T240 K_OPT3 B condB no | 5274803 9435 0.179 10.5 19.2 22.9 0.651 111.0
SELL_c1.5_T240 K_OPT3 B condB yes | 672754 2471 0.367 19.0 38.2 28.3 0.648 110.4
SELL_c1.5_T240 K_OPT3 B hour h0 | 248476 775 0.312 35.4 30.2 48.0 0.596 124.7
SELL_c1.5_T240 K_OPT3 B hour h1 | 248133 362 0.146 -24.4 -20.6 -14.9 0.624 117.9
SELL_c1.5_T240 K_OPT3 B hour h10 | 247734 401 0.162 32.9 39.5 48.3 0.671 108.7
SELL_c1.5_T240 K_OPT3 B hour h11 | 247516 400 0.162 69.8 66.5 83.7 0.723 101.6
SELL_c1.5_T240 K_OPT3 B hour h12 | 247857 512 0.207 19.3 12.1 34.5 0.680 107.1
SELL_c1.5_T240 K_OPT3 B hour h13 | 248120 699 0.282 -106.8 5.8 -96.3 0.579 126.6
SELL_c1.5_T240 K_OPT3 B hour h14 | 248378 633 0.255 -20.9 5.1 -9.1 0.610 115.3
SELL_c1.5_T240 K_OPT3 B hour h15 | 248618 665 0.267 -40.5 -5.1 -29.0 0.645 107.9
SELL_c1.5_T240 K_OPT3 B hour h16 | 248703 793 0.319 18.9 58.2 24.6 0.607 117.8
SELL_c1.5_T240 K_OPT3 B hour h17 | 248456 595 0.239 32.2 77.4 41.9 0.553 127.0
SELL_c1.5_T240 K_OPT3 B hour h18 | 247633 445 0.180 66.4 62.7 75.2 0.667 103.0
SELL_c1.5_T240 K_OPT3 B hour h19 | 247438 387 0.156 -8.7 15.7 1.1 0.641 109.5
SELL_c1.5_T240 K_OPT3 B hour h2 | 248008 358 0.144 -18.1 -16.3 -7.4 0.603 125.4
SELL_c1.5_T240 K_OPT3 B hour h20 | 247713 326 0.132 43.9 49.3 57.4 0.718 93.8
SELL_c1.5_T240 K_OPT3 B hour h21 | 247309 479 0.194 16.8 11.5 26.1 0.656 109.6
SELL_c1.5_T240 K_OPT3 B hour h22 | 247190 440 0.178 97.6 85.5 109.2 0.723 87.5
SELL_c1.5_T240 K_OPT3 B hour h23 | 246685 575 0.233 127.2 73.1 137.3 0.755 84.8
SELL_c1.5_T240 K_OPT3 B hour h3 | 247701 385 0.155 8.5 4.1 17.6 0.652 113.6
SELL_c1.5_T240 K_OPT3 B hour h4 | 247650 349 0.141 -199.0 -193.2 -183.3 0.585 126.1
SELL_c1.5_T240 K_OPT3 B hour h5 | 247405 403 0.163 0.7 9.8 12.7 0.645 115.6
SELL_c1.5_T240 K_OPT3 B hour h6 | 247448 443 0.179 26.6 21.7 42.2 0.664 109.3
SELL_c1.5_T240 K_OPT3 B hour h7 | 247509 524 0.212 26.2 9.4 49.8 0.737 100.4
SELL_c1.5_T240 K_OPT3 B hour h8 | 248095 510 0.206 45.0 37.2 56.8 0.653 113.8
SELL_c1.5_T240 K_OPT3 B hour h9 | 247782 447 0.180 37.2 31.0 46.6 0.736 94.4
SELL_c1.5_T240 K_OPT3 B mkt idio | 0 8924 NA 35.8 33.9 49.2 0.692 101.5
SELL_c1.5_T240 K_OPT3 B mkt market | 0 2982 NA -58.2 -9.1 -51.2 0.524 138.8
SELL_c1.5_T240 K_OPT3 B qvratio 1_10 | 0 782 NA -64.8 -31.1 -57.1 0.458 159.2
SELL_c1.5_T240 K_OPT3 B qvratio gt10 | 0 11115 NA 17.6 26.9 29.6 0.664 107.4
SELL_c1.5_T240 K_OPT3 B qvratio lt1 | 0 9 NA 141.3 100.7 168.4 0.444 172.8
SELL_c1.5_T240 K_OPT3 B tier T1 | 175370 176 0.100 -31.1 67.7 -27.4 0.426 159.1
SELL_c1.5_T240 K_OPT3 B tier T2 | 875827 949 0.108 -32.6 1.9 -26.4 0.489 150.4
SELL_c1.5_T240 K_OPT3 B tier T3 | 4896360 10781 0.220 16.9 24.3 29.3 0.668 106.6
SELL_c1.5_T240 K_OPT3 B wick1m iso | 0 556 NA 229.3 230.5 237.8 0.879 37.4
SELL_c1.5_T240 K_OPT3 B wick1m na | 0 1 NA 305.7 305.7 309.6 1.000 0.0
SELL_c1.5_T240 K_OPT3 B wick1m not | 0 11349 NA 1.6 13.0 13.5 0.639 114.4
SELL_c1.5_T240 K_OPT3 B year y2024 | 2304866 4337 0.188 -17.6 1.9 -11.4 0.601 125.9
SELL_c1.5_T240 K_OPT3 B year y2025 | 3642691 7569 0.208 29.4 35.3 44.4 0.678 102.2
SELL_c1.5_T240 K_PESS A condB no | 2988434 5531 0.185 -28.4 -21.4 -13.6 0.578 126.3
SELL_c1.5_T240 K_PESS A condB yes | 283418 1391 0.491 93.5 58.8 107.9 0.653 115.1
SELL_c1.5_T240 K_PESS A hour h0 | 136608 545 0.399 9.5 5.3 22.3 0.521 140.8
SELL_c1.5_T240 K_PESS A hour h1 | 136358 240 0.176 -0.8 -3.2 12.1 0.492 140.7
SELL_c1.5_T240 K_PESS A hour h10 | 136344 244 0.179 20.8 6.2 32.3 0.635 121.1
SELL_c1.5_T240 K_PESS A hour h11 | 136231 216 0.159 -11.8 -9.2 -0.0 0.625 117.8
SELL_c1.5_T240 K_PESS A hour h12 | 136350 305 0.224 -17.7 -24.5 -0.6 0.633 116.6
SELL_c1.5_T240 K_PESS A hour h13 | 136358 522 0.383 51.7 38.0 67.7 0.667 121.4
SELL_c1.5_T240 K_PESS A hour h14 | 136480 488 0.358 -105.5 -24.9 -88.7 0.449 149.6
SELL_c1.5_T240 K_PESS A hour h15 | 136465 401 0.294 -17.0 -21.6 3.1 0.618 113.7
SELL_c1.5_T240 K_PESS A hour h16 | 136566 502 0.368 88.8 43.2 100.6 0.675 107.6
SELL_c1.5_T240 K_PESS A hour h17 | 136256 291 0.214 48.1 30.2 61.2 0.667 107.5
SELL_c1.5_T240 K_PESS A hour h18 | 136353 312 0.229 86.8 78.6 99.9 0.644 100.7
SELL_c1.5_T240 K_PESS A hour h19 | 136234 244 0.179 -275.6 -241.5 -263.4 0.598 120.1
SELL_c1.5_T240 K_PESS A hour h2 | 136422 223 0.163 -63.2 -60.8 -50.5 0.525 136.3
SELL_c1.5_T240 K_PESS A hour h20 | 136351 192 0.141 -7.2 23.1 7.6 0.604 123.9
SELL_c1.5_T240 K_PESS A hour h21 | 136217 170 0.125 192.9 204.4 204.6 0.694 101.1
SELL_c1.5_T240 K_PESS A hour h22 | 136111 300 0.220 -5.6 -57.5 11.2 0.527 132.0
SELL_c1.5_T240 K_PESS A hour h23 | 136059 170 0.125 -18.1 18.7 0.6 0.576 110.0
SELL_c1.5_T240 K_PESS A hour h3 | 136252 181 0.133 -104.9 -109.6 -89.5 0.497 140.2
SELL_c1.5_T240 K_PESS A hour h4 | 136260 193 0.142 18.8 21.9 39.1 0.565 129.1
SELL_c1.5_T240 K_PESS A hour h5 | 136127 214 0.157 36.4 22.6 51.4 0.640 123.1
SELL_c1.5_T240 K_PESS A hour h6 | 136266 239 0.175 -5.5 -27.2 12.3 0.569 134.6
SELL_c1.5_T240 K_PESS A hour h7 | 136230 251 0.184 -101.3 -104.2 -84.2 0.610 125.1
SELL_c1.5_T240 K_PESS A hour h8 | 136565 267 0.196 9.9 8.1 21.7 0.622 123.2
SELL_c1.5_T240 K_PESS A hour h9 | 136389 212 0.155 12.3 17.2 25.1 0.613 125.2
SELL_c1.5_T240 K_PESS A mkt idio | 0 5021 NA -12.6 -9.7 2.8 0.610 120.6
SELL_c1.5_T240 K_PESS A mkt market | 0 1901 NA 18.9 6.3 32.1 0.550 133.0
SELL_c1.5_T240 K_PESS A qvratio 1_10 | 0 579 NA 104.4 81.3 119.6 0.660 127.2
SELL_c1.5_T240 K_PESS A qvratio gt10 | 0 6340 NA -13.8 -13.2 0.9 0.587 123.8
SELL_c1.5_T240 K_PESS A qvratio lt1 | 0 3 NA 8.7 -34.7 41.3 0.667 19.0
SELL_c1.5_T240 K_PESS A tier T1 | 219092 328 0.150 -14.4 -17.7 -1.2 0.509 141.9
SELL_c1.5_T240 K_PESS A tier T2 | 1095287 1978 0.181 20.4 17.0 33.3 0.556 134.1
SELL_c1.5_T240 K_PESS A tier T3 | 1957473 4616 0.236 -13.6 -14.0 2.0 0.616 118.4
SELL_c1.5_T240 K_PESS A wick1m iso | 0 263 NA 161.7 164.9 178.7 0.475 60.1
SELL_c1.5_T240 K_PESS A wick1m not | 0 6659 NA -10.5 -12.0 4.2 0.598 126.5
SELL_c1.5_T240 K_PESS A year y2021 | 533832 1033 0.194 -7.1 -13.9 6.8 0.539 138.7
SELL_c1.5_T240 K_PESS A year y2022 | 1190474 2141 0.180 13.2 -0.9 28.4 0.620 119.3
SELL_c1.5_T240 K_PESS A year y2023 | 1547546 3748 0.242 -12.9 -5.5 1.9 0.593 122.6
SELL_c1.5_T240 K_PESS B condB no | 5274803 9337 0.177 -1.1 7.5 19.6 0.626 112.1
SELL_c1.5_T240 K_PESS B condB yes | 672754 2432 0.361 7.1 25.7 25.0 0.599 111.3
SELL_c1.5_T240 K_PESS B hour h0 | 248476 765 0.308 24.1 18.4 45.6 0.575 126.2
SELL_c1.5_T240 K_PESS B hour h1 | 248133 354 0.143 -37.8 -33.1 -19.9 0.605 118.8
SELL_c1.5_T240 K_PESS B hour h10 | 247734 400 0.161 20.9 28.6 44.7 0.635 111.3
SELL_c1.5_T240 K_PESS B hour h11 | 247516 396 0.160 65.8 63.0 87.0 0.712 102.7
SELL_c1.5_T240 K_PESS B hour h12 | 247857 506 0.204 7.6 0.7 30.6 0.660 107.4
SELL_c1.5_T240 K_PESS B hour h13 | 248120 694 0.280 -116.2 -5.3 -96.8 0.565 127.2
SELL_c1.5_T240 K_PESS B hour h14 | 248378 626 0.252 -31.3 -5.3 -11.2 0.588 115.3
SELL_c1.5_T240 K_PESS B hour h15 | 248618 658 0.265 -53.2 -17.3 -33.4 0.625 109.4
SELL_c1.5_T240 K_PESS B hour h16 | 248703 781 0.314 6.9 45.7 21.1 0.583 118.9
SELL_c1.5_T240 K_PESS B hour h17 | 248456 585 0.235 18.8 63.4 37.6 0.525 127.7
SELL_c1.5_T240 K_PESS B hour h18 | 247633 444 0.179 54.8 51.2 71.8 0.635 104.2
SELL_c1.5_T240 K_PESS B hour h19 | 247438 382 0.154 -21.9 2.5 -3.9 0.613 111.2
SELL_c1.5_T240 K_PESS B hour h2 | 248008 354 0.143 -30.9 -28.6 -11.3 0.579 125.9
SELL_c1.5_T240 K_PESS B hour h20 | 247713 320 0.129 39.2 44.5 60.1 0.678 93.4
SELL_c1.5_T240 K_PESS B hour h21 | 247309 475 0.192 1.5 -2.9 20.1 0.571 111.1
SELL_c1.5_T240 K_PESS B hour h22 | 247190 435 0.176 82.5 69.4 102.7 0.614 89.4
SELL_c1.5_T240 K_PESS B hour h23 | 246685 570 0.231 120.9 64.6 137.9 0.723 86.4
SELL_c1.5_T240 K_PESS B hour h3 | 247701 382 0.154 -2.4 -7.7 14.8 0.628 114.6
SELL_c1.5_T240 K_PESS B hour h4 | 247650 345 0.139 -220.5 -213.9 -195.7 0.571 128.5
SELL_c1.5_T240 K_PESS B hour h5 | 247405 399 0.161 -12.3 -3.4 8.3 0.622 116.8
SELL_c1.5_T240 K_PESS B hour h6 | 247448 439 0.177 16.8 12.0 40.5 0.640 109.7
SELL_c1.5_T240 K_PESS B hour h7 | 247509 519 0.210 15.3 -1.5 46.6 0.703 101.8
SELL_c1.5_T240 K_PESS B hour h8 | 248095 499 0.201 29.9 21.9 49.9 0.631 115.5
SELL_c1.5_T240 K_PESS B hour h9 | 247782 441 0.178 25.4 19.3 42.3 0.705 95.6
SELL_c1.5_T240 K_PESS B mkt idio | 0 8830 NA 23.5 21.9 44.8 0.660 102.9
SELL_c1.5_T240 K_PESS B mkt market | 0 2939 NA -68.3 -20.6 -51.9 0.502 139.1
SELL_c1.5_T240 K_PESS B qvratio 1_10 | 0 770 NA -74.3 -39.8 -56.6 0.455 159.3
SELL_c1.5_T240 K_PESS B qvratio gt10 | 0 10993 NA 5.8 14.8 26.0 0.632 108.6
SELL_c1.5_T240 K_PESS B qvratio lt1 | 0 6 NA 141.2 92.2 154.5 0.500 166.8
SELL_c1.5_T240 K_PESS B tier T1 | 175370 175 0.100 -37.1 62.3 -27.4 0.417 159.5
SELL_c1.5_T240 K_PESS B tier T2 | 875827 944 0.108 -42.1 -7.2 -28.4 0.468 150.7
SELL_c1.5_T240 K_PESS B tier T3 | 4896360 10650 0.218 5.0 12.1 25.8 0.637 107.8
SELL_c1.5_T240 K_PESS B wick1m iso | 0 554 NA 216.7 216.3 235.0 0.468 38.4
SELL_c1.5_T240 K_PESS B wick1m na | 0 1 NA 291.1 300.2 309.6 0.000 1.0
SELL_c1.5_T240 K_PESS B wick1m not | 0 11214 NA -10.1 1.1 10.1 0.628 115.6
SELL_c1.5_T240 K_PESS B year y2024 | 2304866 4286 0.186 -28.7 -9.3 -14.0 0.585 126.9
SELL_c1.5_T240 K_PESS B year y2025 | 3642691 7483 0.205 17.4 23.1 40.6 0.641 103.4
SELL_c1.5_T1440 K_OPT3 A condB no | 2988434 5625 0.188 13.2 17.5 27.4 0.777 467.1
SELL_c1.5_T1440 K_OPT3 A condB yes | 283418 1418 0.500 150.6 95.2 162.3 0.853 347.0
SELL_c1.5_T1440 K_OPT3 A hour h0 | 136608 554 0.406 51.1 45.1 64.1 0.796 487.6
SELL_c1.5_T1440 K_OPT3 A hour h1 | 136358 243 0.178 47.4 29.9 60.9 0.827 470.3
SELL_c1.5_T1440 K_OPT3 A hour h10 | 136344 250 0.183 84.4 75.4 97.4 0.800 415.3
SELL_c1.5_T1440 K_OPT3 A hour h11 | 136231 217 0.159 3.0 14.9 20.4 0.760 445.5
SELL_c1.5_T1440 K_OPT3 A hour h12 | 136350 309 0.227 -6.7 -33.9 7.4 0.806 401.3
SELL_c1.5_T1440 K_OPT3 A hour h13 | 136358 533 0.391 220.7 177.6 233.6 0.856 342.9
SELL_c1.5_T1440 K_OPT3 A hour h14 | 136480 502 0.368 5.0 15.8 15.9 0.633 679.0
SELL_c1.5_T1440 K_OPT3 A hour h15 | 136465 405 0.297 -1.8 -14.1 15.5 0.778 452.8
SELL_c1.5_T1440 K_OPT3 A hour h16 | 136566 513 0.376 81.3 48.3 91.5 0.838 351.6
SELL_c1.5_T1440 K_OPT3 A hour h17 | 136256 296 0.217 95.4 82.6 105.0 0.848 356.5
SELL_c1.5_T1440 K_OPT3 A hour h18 | 136353 314 0.230 103.3 123.8 112.5 0.831 382.0
SELL_c1.5_T1440 K_OPT3 A hour h19 | 136234 248 0.182 2.4 60.6 12.2 0.750 482.3
SELL_c1.5_T1440 K_OPT3 A hour h2 | 136422 228 0.167 -12.4 -34.5 2.7 0.763 514.4
SELL_c1.5_T1440 K_OPT3 A hour h20 | 136351 195 0.143 91.2 120.4 101.0 0.785 436.8
SELL_c1.5_T1440 K_OPT3 A hour h21 | 136217 170 0.125 297.6 277.0 303.1 0.882 307.6
SELL_c1.5_T1440 K_OPT3 A hour h22 | 136111 312 0.229 33.9 -47.2 51.6 0.760 503.4
SELL_c1.5_T1440 K_OPT3 A hour h23 | 136059 172 0.126 110.1 179.3 126.5 0.837 390.0
SELL_c1.5_T1440 K_OPT3 A hour h3 | 136252 183 0.134 -224.3 -224.6 -204.5 0.738 537.8
SELL_c1.5_T1440 K_OPT3 A hour h4 | 136260 195 0.143 -180.7 -165.6 -155.2 0.790 475.2
SELL_c1.5_T1440 K_OPT3 A hour h5 | 136127 217 0.159 34.8 28.1 48.4 0.816 401.6
SELL_c1.5_T1440 K_OPT3 A hour h6 | 136266 246 0.181 21.4 13.9 34.1 0.785 439.2
SELL_c1.5_T1440 K_OPT3 A hour h7 | 136230 255 0.187 -157.2 -133.0 -135.7 0.780 439.1
SELL_c1.5_T1440 K_OPT3 A hour h8 | 136565 271 0.198 69.0 53.2 78.2 0.827 392.2
SELL_c1.5_T1440 K_OPT3 A hour h9 | 136389 215 0.158 -18.7 -28.0 1.5 0.786 439.1
SELL_c1.5_T1440 K_OPT3 A mkt idio | 0 5099 NA 42.5 42.8 58.4 0.815 412.4
SELL_c1.5_T1440 K_OPT3 A mkt market | 0 1944 NA 36.8 7.6 44.4 0.735 522.9
SELL_c1.5_T1440 K_OPT3 A qvratio 1_10 | 0 584 NA 174.9 131.2 187.4 0.848 365.4
SELL_c1.5_T1440 K_OPT3 A qvratio gt10 | 0 6456 NA 28.8 24.3 42.6 0.788 450.1
SELL_c1.5_T1440 K_OPT3 A qvratio lt1 | 0 3 NA 35.9 -7.5 41.3 0.667 19.0
SELL_c1.5_T1440 K_OPT3 A tier T1 | 219092 330 0.151 50.8 55.0 65.3 0.748 527.7
SELL_c1.5_T1440 K_OPT3 A tier T2 | 1095287 2008 0.183 62.5 53.3 70.9 0.764 491.4
SELL_c1.5_T1440 K_OPT3 A tier T3 | 1957473 4705 0.240 31.0 23.0 46.8 0.808 416.2
SELL_c1.5_T1440 K_OPT3 A wick1m iso | 0 264 NA 198.0 195.9 215.6 0.871 246.4
SELL_c1.5_T1440 K_OPT3 A wick1m not | 0 6779 NA 34.8 26.8 48.3 0.789 450.5
SELL_c1.5_T1440 K_OPT3 A year y2021 | 533832 1036 0.194 -1.4 -9.1 4.8 0.771 508.7
SELL_c1.5_T1440 K_OPT3 A year y2022 | 1190474 2175 0.183 67.3 50.1 83.1 0.814 407.0
SELL_c1.5_T1440 K_OPT3 A year y2023 | 1547546 3832 0.248 37.3 34.9 51.8 0.786 445.5
SELL_c1.5_T1440 K_OPT3 B condB no | 5264570 9396 0.178 20.0 15.8 50.9 0.813 404.1
SELL_c1.5_T1440 K_OPT3 B condB yes | 672754 2471 0.367 1.6 29.8 27.7 0.772 435.8
SELL_c1.5_T1440 K_OPT3 B hour h0 | 247962 769 0.310 102.0 94.7 140.4 0.800 446.1
SELL_c1.5_T1440 K_OPT3 B hour h1 | 247620 361 0.146 -68.4 -62.2 -42.6 0.806 411.1
SELL_c1.5_T1440 K_OPT3 B hour h10 | 247219 400 0.162 -23.5 -3.0 19.1 0.833 352.5
SELL_c1.5_T1440 K_OPT3 B hour h11 | 247001 396 0.160 -9.0 -3.9 24.6 0.826 355.9
SELL_c1.5_T1440 K_OPT3 B hour h12 | 247338 508 0.205 -36.6 -51.3 -4.5 0.831 374.6
SELL_c1.5_T1440 K_OPT3 B hour h13 | 247603 697 0.282 -177.0 -62.3 -152.4 0.671 556.1
SELL_c1.5_T1440 K_OPT3 B hour h14 | 247865 630 0.254 -57.4 -69.0 -32.8 0.721 501.3
SELL_c1.5_T1440 K_OPT3 B hour h15 | 248108 665 0.268 -13.3 0.8 9.6 0.782 439.4
SELL_c1.5_T1440 K_OPT3 B hour h16 | 248183 789 0.318 74.9 83.8 83.7 0.812 447.0
SELL_c1.5_T1440 K_OPT3 B hour h17 | 247937 593 0.239 122.0 96.2 141.6 0.821 499.4
SELL_c1.5_T1440 K_OPT3 B hour h18 | 247633 445 0.180 118.2 111.1 135.0 0.843 375.0
SELL_c1.5_T1440 K_OPT3 B hour h19 | 247438 387 0.156 37.7 49.6 50.8 0.775 426.3
SELL_c1.5_T1440 K_OPT3 B hour h2 | 247494 358 0.145 -118.5 -110.1 -50.2 0.796 448.0
SELL_c1.5_T1440 K_OPT3 B hour h20 | 247713 326 0.132 73.9 81.7 98.2 0.865 311.9
SELL_c1.5_T1440 K_OPT3 B hour h21 | 247309 479 0.194 -47.4 -43.2 -31.2 0.787 402.5
SELL_c1.5_T1440 K_OPT3 B hour h22 | 246674 439 0.178 100.2 69.4 118.0 0.829 351.4
SELL_c1.5_T1440 K_OPT3 B hour h23 | 246181 574 0.233 121.1 58.0 136.3 0.855 317.0
SELL_c1.5_T1440 K_OPT3 B hour h3 | 247202 381 0.154 -59.4 -67.7 2.6 0.816 404.2
SELL_c1.5_T1440 K_OPT3 B hour h4 | 247143 349 0.141 -76.3 -76.5 -21.8 0.791 455.4
SELL_c1.5_T1440 K_OPT3 B hour h5 | 246893 403 0.163 27.7 62.7 69.3 0.782 425.1
SELL_c1.5_T1440 K_OPT3 B hour h6 | 246945 442 0.179 85.0 78.5 124.4 0.833 361.4
SELL_c1.5_T1440 K_OPT3 B hour h7 | 247003 521 0.211 -10.0 -28.5 51.4 0.881 291.8
SELL_c1.5_T1440 K_OPT3 B hour h8 | 247590 509 0.206 42.6 47.5 74.5 0.788 407.6
SELL_c1.5_T1440 K_OPT3 B hour h9 | 247270 446 0.180 113.7 107.9 134.6 0.852 313.2
SELL_c1.5_T1440 K_OPT3 B mkt idio | 0 8886 NA 38.6 36.3 72.9 0.837 354.8
SELL_c1.5_T1440 K_OPT3 B mkt market | 0 2981 NA -50.8 -33.5 -33.8 0.705 577.4
SELL_c1.5_T1440 K_OPT3 B qvratio 1_10 | 0 782 NA -84.0 -78.7 -74.4 0.683 647.8
SELL_c1.5_T1440 K_OPT3 B qvratio gt10 | 0 11076 NA 23.0 25.5 54.4 0.812 394.0
SELL_c1.5_T1440 K_OPT3 B qvratio lt1 | 0 9 NA 231.8 142.5 266.8 1.000 358.3
SELL_c1.5_T1440 K_OPT3 B tier T1 | 175170 176 0.100 -10.3 45.5 -8.1 0.619 715.0
SELL_c1.5_T1440 K_OPT3 B tier T2 | 874828 948 0.108 -39.8 -24.0 -31.5 0.722 588.0
SELL_c1.5_T1440 K_OPT3 B tier T3 | 4887326 10743 0.220 21.5 22.1 53.8 0.814 390.1
SELL_c1.5_T1440 K_OPT3 B wick1m iso | 0 554 NA 243.9 240.6 276.5 0.931 141.3
SELL_c1.5_T1440 K_OPT3 B wick1m na | 0 1 NA 305.7 305.7 309.6 1.000 0.0
SELL_c1.5_T1440 K_OPT3 B wick1m not | 0 11312 NA 5.0 7.8 34.8 0.798 424.0
SELL_c1.5_T1440 K_OPT3 B year y2024 | 2304866 4336 0.188 -9.7 18.6 1.5 0.767 469.2
SELL_c1.5_T1440 K_OPT3 B year y2025 | 3632458 7531 0.207 31.0 18.8 71.8 0.826 377.1
SELL_c1.5_T1440 K_PESS A condB no | 2988434 5531 0.185 3.1 7.0 23.8 0.760 475.2
SELL_c1.5_T1440 K_PESS A condB yes | 283418 1391 0.491 142.6 87.4 160.1 0.832 355.3
SELL_c1.5_T1440 K_PESS A hour h0 | 136608 545 0.399 37.4 32.2 56.9 0.776 503.3
SELL_c1.5_T1440 K_PESS A hour h1 | 136358 240 0.176 33.1 14.1 52.9 0.792 480.3
SELL_c1.5_T1440 K_PESS A hour h10 | 136344 244 0.179 85.2 75.6 102.0 0.795 418.1
SELL_c1.5_T1440 K_PESS A hour h11 | 136231 216 0.159 -4.8 7.3 19.3 0.755 448.6
SELL_c1.5_T1440 K_PESS A hour h12 | 136350 305 0.224 -15.9 -44.6 4.6 0.780 407.4
SELL_c1.5_T1440 K_PESS A hour h13 | 136358 522 0.383 213.4 168.3 231.9 0.847 347.6
SELL_c1.5_T1440 K_PESS A hour h14 | 136480 488 0.358 -9.7 -0.7 9.4 0.611 692.9
SELL_c1.5_T1440 K_PESS A hour h15 | 136465 401 0.294 -5.3 -17.9 18.5 0.753 450.9
SELL_c1.5_T1440 K_PESS A hour h16 | 136566 502 0.368 72.3 36.4 88.8 0.815 360.0
SELL_c1.5_T1440 K_PESS A hour h17 | 136256 291 0.214 87.0 74.7 102.2 0.838 360.2
SELL_c1.5_T1440 K_PESS A hour h18 | 136353 312 0.229 89.8 109.9 107.2 0.795 394.3
SELL_c1.5_T1440 K_PESS A hour h19 | 136234 244 0.179 -4.6 51.8 11.9 0.750 499.7
SELL_c1.5_T1440 K_PESS A hour h2 | 136422 223 0.163 -25.5 -48.6 -3.5 0.744 529.1
SELL_c1.5_T1440 K_PESS A hour h20 | 136351 192 0.141 86.4 112.2 102.5 0.760 441.9
SELL_c1.5_T1440 K_PESS A hour h21 | 136217 170 0.125 286.0 269.3 296.4 0.876 315.2
SELL_c1.5_T1440 K_PESS A hour h22 | 136111 300 0.220 21.5 -53.5 46.2 0.743 525.4
SELL_c1.5_T1440 K_PESS A hour h23 | 136059 170 0.125 103.2 174.1 126.0 0.776 394.8
SELL_c1.5_T1440 K_PESS A hour h3 | 136252 181 0.133 -236.2 -236.2 -209.0 0.718 543.9
SELL_c1.5_T1440 K_PESS A hour h4 | 136260 193 0.142 -191.2 -178.1 -158.9 0.772 477.5
SELL_c1.5_T1440 K_PESS A hour h5 | 136127 214 0.157 25.5 21.9 45.3 0.804 403.3
SELL_c1.5_T1440 K_PESS A hour h6 | 136266 239 0.175 7.6 -2.7 26.7 0.762 456.5
SELL_c1.5_T1440 K_PESS A hour h7 | 136230 251 0.184 -171.6 -145.0 -143.5 0.773 447.4
SELL_c1.5_T1440 K_PESS A hour h8 | 136565 267 0.196 58.8 43.9 73.9 0.813 398.2
SELL_c1.5_T1440 K_PESS A hour h9 | 136389 212 0.155 -20.9 -30.5 3.6 0.778 438.6
SELL_c1.5_T1440 K_PESS A mkt idio | 0 5021 NA 34.1 34.4 56.3 0.796 419.5
SELL_c1.5_T1440 K_PESS A mkt market | 0 1901 NA 23.3 -6.4 37.7 0.716 534.6
SELL_c1.5_T1440 K_PESS A qvratio 1_10 | 0 579 NA 169.5 124.9 187.6 0.846 364.2
SELL_c1.5_T1440 K_PESS A qvratio gt10 | 0 6340 NA 18.5 13.9 38.8 0.768 459.2
SELL_c1.5_T1440 K_PESS A qvratio lt1 | 0 3 NA 8.7 -34.7 41.3 0.667 19.0
SELL_c1.5_T1440 K_PESS A tier T1 | 219092 328 0.150 48.6 52.2 68.1 0.732 527.5
SELL_c1.5_T1440 K_PESS A tier T2 | 1095287 1978 0.181 57.6 48.2 71.7 0.750 496.9
SELL_c1.5_T1440 K_PESS A tier T3 | 1957473 4616 0.236 18.5 10.4 41.2 0.788 426.0
SELL_c1.5_T1440 K_PESS A wick1m iso | 0 263 NA 185.0 185.5 210.8 0.548 253.7
SELL_c1.5_T1440 K_PESS A wick1m not | 0 6659 NA 25.1 16.8 44.9 0.783 458.9
SELL_c1.5_T1440 K_PESS A year y2021 | 533832 1033 0.194 -6.9 -14.8 5.8 0.760 507.6
SELL_c1.5_T1440 K_PESS A year y2022 | 1190474 2141 0.180 56.3 38.5 78.3 0.795 414.5
SELL_c1.5_T1440 K_PESS A year y2023 | 1547546 3748 0.242 27.3 24.9 48.3 0.766 456.4
SELL_c1.5_T1440 K_PESS B condB no | 5264570 9298 0.177 8.1 4.0 45.8 0.788 408.4
SELL_c1.5_T1440 K_PESS B condB yes | 672754 2432 0.361 -8.4 18.7 25.3 0.725 438.8
SELL_c1.5_T1440 K_PESS B hour h0 | 247962 759 0.306 91.8 83.3 137.2 0.780 451.4
SELL_c1.5_T1440 K_PESS B hour h1 | 247620 353 0.143 -80.1 -73.2 -46.9 0.788 415.8
SELL_c1.5_T1440 K_PESS B hour h10 | 247219 399 0.161 -34.6 -13.1 14.8 0.802 361.3
SELL_c1.5_T1440 K_PESS B hour h11 | 247001 392 0.159 -13.0 -7.9 25.7 0.814 357.3
SELL_c1.5_T1440 K_PESS B hour h12 | 247338 502 0.203 -45.5 -60.1 -6.8 0.813 375.8
SELL_c1.5_T1440 K_PESS B hour h13 | 247603 692 0.279 -184.4 -71.5 -151.8 0.659 556.5
SELL_c1.5_T1440 K_PESS B hour h14 | 247865 623 0.251 -66.4 -80.0 -34.3 0.698 499.5
SELL_c1.5_T1440 K_PESS B hour h15 | 248108 658 0.265 -26.0 -11.4 3.9 0.761 445.2
SELL_c1.5_T1440 K_PESS B hour h16 | 248183 777 0.313 63.9 71.4 79.2 0.789 453.2
SELL_c1.5_T1440 K_PESS B hour h17 | 247937 583 0.235 104.1 79.6 130.3 0.791 501.3
SELL_c1.5_T1440 K_PESS B hour h18 | 247633 444 0.179 113.5 105.8 136.6 0.815 376.8
SELL_c1.5_T1440 K_PESS B hour h19 | 247438 382 0.154 25.2 37.1 45.2 0.749 429.2
SELL_c1.5_T1440 K_PESS B hour h2 | 247494 354 0.143 -130.6 -121.9 -54.7 0.774 452.1
SELL_c1.5_T1440 K_PESS B hour h20 | 247713 320 0.129 69.0 77.6 97.5 0.822 307.1
SELL_c1.5_T1440 K_PESS B hour h21 | 247309 475 0.192 -59.9 -54.8 -35.6 0.705 408.6
SELL_c1.5_T1440 K_PESS B hour h22 | 246674 434 0.176 80.0 48.0 105.8 0.721 362.0
SELL_c1.5_T1440 K_PESS B hour h23 | 246181 569 0.231 113.0 47.9 134.1 0.826 321.7
SELL_c1.5_T1440 K_PESS B hour h3 | 247202 378 0.153 -73.7 -82.1 -4.5 0.791 410.7
SELL_c1.5_T1440 K_PESS B hour h4 | 247143 345 0.140 -93.8 -94.5 -32.1 0.783 462.0
SELL_c1.5_T1440 K_PESS B hour h5 | 246893 399 0.162 16.4 51.2 65.4 0.759 429.7
SELL_c1.5_T1440 K_PESS B hour h6 | 246945 438 0.177 76.0 71.1 121.9 0.806 363.2
SELL_c1.5_T1440 K_PESS B hour h7 | 247003 516 0.209 -27.5 -45.9 40.7 0.849 297.6
SELL_c1.5_T1440 K_PESS B hour h8 | 247590 498 0.201 28.2 33.2 67.4 0.767 415.6
SELL_c1.5_T1440 K_PESS B hour h9 | 247270 440 0.178 103.6 98.0 130.8 0.820 317.0
SELL_c1.5_T1440 K_PESS B mkt idio | 0 8792 NA 26.4 24.3 67.3 0.806 360.6
SELL_c1.5_T1440 K_PESS B mkt market | 0 2938 NA -60.0 -44.6 -35.4 0.681 576.9
SELL_c1.5_T1440 K_PESS B qvratio 1_10 | 0 770 NA -92.2 -83.4 -74.5 0.675 645.9
SELL_c1.5_T1440 K_PESS B qvratio gt10 | 0 10954 NA 11.4 13.3 49.6 0.782 398.5
SELL_c1.5_T1440 K_PESS B qvratio lt1 | 0 6 NA 237.7 139.7 245.1 1.000 345.0
SELL_c1.5_T1440 K_PESS B tier T1 | 175170 175 0.100 -13.1 38.6 -5.6 0.611 711.7
SELL_c1.5_T1440 K_PESS B tier T2 | 874828 943 0.108 -48.6 -32.3 -33.9 0.701 591.6
SELL_c1.5_T1440 K_PESS B tier T3 | 4887326 10612 0.217 9.8 10.0 49.1 0.784 394.1
SELL_c1.5_T1440 K_PESS B wick1m iso | 0 552 NA 230.3 223.3 272.4 0.520 144.9
SELL_c1.5_T1440 K_PESS B wick1m na | 0 1 NA 291.1 300.2 309.6 0.000 1.0
SELL_c1.5_T1440 K_PESS B wick1m not | 0 11177 NA -6.4 -3.6 30.2 0.788 428.1
SELL_c1.5_T1440 K_PESS B year y2024 | 2304866 4285 0.186 -19.5 8.6 -1.5 0.751 473.3
SELL_c1.5_T1440 K_PESS B year y2025 | 3632458 7445 0.205 18.7 6.1 66.3 0.789 381.0
SELL_c2.5_T240 K_OPT3 A condB no | 2988434 1403 0.047 -30.4 -24.3 -20.7 0.551 135.1
SELL_c2.5_T240 K_OPT3 A condB yes | 283418 346 0.122 180.4 119.0 190.8 0.627 135.5
SELL_c2.5_T240 K_OPT3 A hour h0 | 136608 138 0.101 32.3 28.8 36.8 0.457 148.4
SELL_c2.5_T240 K_OPT3 A hour h1 | 136358 54 0.040 -51.7 -56.5 -46.5 0.444 150.0
SELL_c2.5_T240 K_OPT3 A hour h10 | 136344 53 0.039 23.4 2.8 27.3 0.585 141.9
SELL_c2.5_T240 K_OPT3 A hour h11 | 136231 56 0.041 -108.3 -106.4 -104.2 0.518 142.4
SELL_c2.5_T240 K_OPT3 A hour h12 | 136350 75 0.055 -14.3 -13.9 4.4 0.613 116.5
SELL_c2.5_T240 K_OPT3 A hour h13 | 136358 167 0.122 201.4 68.8 216.0 0.671 153.1
SELL_c2.5_T240 K_OPT3 A hour h14 | 136480 127 0.093 -4.3 51.4 6.5 0.441 156.5
SELL_c2.5_T240 K_OPT3 A hour h15 | 136465 105 0.077 -83.7 -68.3 -65.1 0.571 130.0
SELL_c2.5_T240 K_OPT3 A hour h16 | 136566 116 0.085 156.8 156.2 164.4 0.638 120.6
SELL_c2.5_T240 K_OPT3 A hour h17 | 136256 91 0.067 110.7 109.3 119.1 0.593 125.6
SELL_c2.5_T240 K_OPT3 A hour h18 | 136353 59 0.043 217.6 213.0 224.9 0.661 106.7
SELL_c2.5_T240 K_OPT3 A hour h19 | 136234 62 0.046 -930.7 -890.6 -926.5 0.500 139.0
SELL_c2.5_T240 K_OPT3 A hour h2 | 136422 59 0.043 -221.4 -221.8 -217.3 0.441 149.0
SELL_c2.5_T240 K_OPT3 A hour h20 | 136351 49 0.036 -71.7 -23.8 -59.5 0.633 132.7
SELL_c2.5_T240 K_OPT3 A hour h21 | 136217 44 0.032 500.4 538.9 504.8 0.682 95.3
SELL_c2.5_T240 K_OPT3 A hour h22 | 136111 56 0.041 116.9 87.7 126.9 0.554 123.6
SELL_c2.5_T240 K_OPT3 A hour h23 | 136059 36 0.026 -77.6 -47.0 -58.4 0.694 95.7
SELL_c2.5_T240 K_OPT3 A hour h3 | 136252 54 0.040 -56.9 -75.0 -52.9 0.500 138.7
SELL_c2.5_T240 K_OPT3 A hour h4 | 136260 55 0.040 207.6 198.0 225.8 0.636 117.2
SELL_c2.5_T240 K_OPT3 A hour h5 | 136127 57 0.042 75.5 79.0 87.2 0.544 143.3
SELL_c2.5_T240 K_OPT3 A hour h6 | 136266 57 0.042 10.4 -19.3 23.1 0.509 158.0
SELL_c2.5_T240 K_OPT3 A hour h7 | 136230 70 0.051 -162.7 -165.6 -148.2 0.586 135.6
SELL_c2.5_T240 K_OPT3 A hour h8 | 136565 62 0.045 73.4 66.6 77.4 0.645 113.7
SELL_c2.5_T240 K_OPT3 A hour h9 | 136389 47 0.034 15.6 27.4 20.0 0.532 141.6
SELL_c2.5_T240 K_OPT3 A mkt idio | 0 1324 NA -49.0 -44.3 -37.9 0.561 133.4
SELL_c2.5_T240 K_OPT3 A mkt market | 0 425 NA 199.2 154.8 205.1 0.581 140.7
SELL_c2.5_T240 K_OPT3 A qvratio 1_10 | 0 92 NA 319.7 110.1 332.5 0.717 165.7
SELL_c2.5_T240 K_OPT3 A qvratio gt10 | 0 1655 NA -8.7 -4.6 1.0 0.558 133.5
SELL_c2.5_T240 K_OPT3 A qvratio lt1 | 0 2 NA 2366.7 2268.7 2372.1 0.500 98.0
SELL_c2.5_T240 K_OPT3 A tier T1 | 219092 79 0.036 -63.9 -72.7 -55.5 0.557 139.2
SELL_c2.5_T240 K_OPT3 A tier T2 | 1095287 425 0.039 14.4 -4.1 22.3 0.558 140.7
SELL_c2.5_T240 K_OPT3 A tier T3 | 1957473 1245 0.064 15.0 11.7 25.6 0.569 133.0
SELL_c2.5_T240 K_OPT3 A wick1m iso | 0 69 NA 280.9 266.2 294.8 0.739 70.4
SELL_c2.5_T240 K_OPT3 A wick1m not | 0 1680 NA 0.2 -6.7 9.9 0.559 137.8
SELL_c2.5_T240 K_OPT3 A year y2021 | 533832 227 0.043 -27.4 -35.0 -20.0 0.511 147.8
SELL_c2.5_T240 K_OPT3 A year y2022 | 1190474 589 0.049 51.2 13.4 61.0 0.615 132.8
SELL_c2.5_T240 K_OPT3 A year y2023 | 1547546 933 0.060 -4.4 7.6 6.0 0.549 133.6
SELL_c2.5_T240 K_OPT3 B condB no | 5274809 2636 0.050 61.5 66.3 79.8 0.604 121.8
SELL_c2.5_T240 K_OPT3 B condB yes | 672754 659 0.098 137.3 121.2 153.9 0.669 104.5
SELL_c2.5_T240 K_OPT3 B hour h0 | 248476 219 0.088 54.2 46.4 74.6 0.447 152.6
SELL_c2.5_T240 K_OPT3 B hour h1 | 248133 99 0.040 -11.8 6.4 1.3 0.495 142.3
SELL_c2.5_T240 K_OPT3 B hour h10 | 247734 135 0.054 142.6 149.4 163.1 0.630 127.0
SELL_c2.5_T240 K_OPT3 B hour h11 | 247516 125 0.051 238.8 228.8 254.3 0.696 115.0
SELL_c2.5_T240 K_OPT3 B hour h12 | 247857 133 0.054 -19.1 -43.0 9.5 0.692 103.9
SELL_c2.5_T240 K_OPT3 B hour h13 | 248120 163 0.066 188.5 197.1 211.1 0.693 103.9
SELL_c2.5_T240 K_OPT3 B hour h14 | 248379 142 0.057 -105.4 -104.0 -84.9 0.634 111.0
SELL_c2.5_T240 K_OPT3 B hour h15 | 248619 176 0.071 -134.7 -108.1 -118.9 0.528 129.7
SELL_c2.5_T240 K_OPT3 B hour h16 | 248704 232 0.093 115.3 160.6 122.1 0.608 122.6
SELL_c2.5_T240 K_OPT3 B hour h17 | 248456 153 0.062 247.2 256.8 256.6 0.614 114.2
SELL_c2.5_T240 K_OPT3 B hour h18 | 247634 135 0.055 181.6 188.3 196.1 0.637 111.3
SELL_c2.5_T240 K_OPT3 B hour h19 | 247438 109 0.044 156.6 173.9 172.1 0.624 111.5
SELL_c2.5_T240 K_OPT3 B hour h2 | 248008 103 0.042 95.4 96.4 112.7 0.563 134.1
SELL_c2.5_T240 K_OPT3 B hour h20 | 247713 81 0.033 248.3 270.7 270.4 0.704 100.5
SELL_c2.5_T240 K_OPT3 B hour h21 | 247310 144 0.058 210.2 210.2 218.6 0.729 93.6
SELL_c2.5_T240 K_OPT3 B hour h22 | 247190 124 0.050 124.4 120.7 144.5 0.677 92.1
SELL_c2.5_T240 K_OPT3 B hour h23 | 246686 183 0.074 279.6 195.5 291.0 0.749 92.6
SELL_c2.5_T240 K_OPT3 B hour h3 | 247701 104 0.042 -20.6 -29.1 -13.7 0.567 129.3
SELL_c2.5_T240 K_OPT3 B hour h4 | 247650 106 0.043 -392.7 -387.3 -365.5 0.509 146.5
SELL_c2.5_T240 K_OPT3 B hour h5 | 247405 110 0.044 127.7 127.6 137.0 0.536 130.3
SELL_c2.5_T240 K_OPT3 B hour h6 | 247448 132 0.053 58.9 56.3 85.6 0.621 117.1
SELL_c2.5_T240 K_OPT3 B hour h7 | 247509 161 0.065 57.1 57.5 94.0 0.646 113.1
SELL_c2.5_T240 K_OPT3 B hour h8 | 248095 125 0.050 -92.3 -105.2 -65.1 0.632 120.4
SELL_c2.5_T240 K_OPT3 B hour h9 | 247782 101 0.041 -54.6 -49.1 -34.2 0.584 124.6
SELL_c2.5_T240 K_OPT3 B mkt idio | 0 2677 NA 78.9 80.0 98.5 0.622 117.6
SELL_c2.5_T240 K_OPT3 B mkt market | 0 618 NA 66.9 65.3 77.8 0.594 121.4
SELL_c2.5_T240 K_OPT3 B qvratio 1_10 | 0 54 NA 154.9 113.3 174.7 0.407 159.9
SELL_c2.5_T240 K_OPT3 B qvratio gt10 | 0 3241 NA 75.3 76.6 93.3 0.620 117.6
SELL_c2.5_T240 K_OPT3 B tier T1 | 175370 23 0.013 -79.3 141.6 -76.9 0.217 205.7
SELL_c2.5_T240 K_OPT3 B tier T2 | 875827 169 0.019 32.2 61.4 29.6 0.485 149.7
SELL_c2.5_T240 K_OPT3 B tier T3 | 4896366 3103 0.063 80.2 77.6 99.4 0.627 116.0
SELL_c2.5_T240 K_OPT3 B wick1m iso | 0 167 NA 412.3 420.5 422.3 0.862 39.1
SELL_c2.5_T240 K_OPT3 B wick1m not | 0 3128 NA 58.7 58.9 77.1 0.604 122.5
SELL_c2.5_T240 K_OPT3 B year y2024 | 2304866 1013 0.044 11.1 14.9 20.4 0.543 137.0
SELL_c2.5_T240 K_OPT3 B year y2025 | 3642697 2282 0.063 105.7 104.9 127.6 0.650 110.0
SELL_c2.5_T240 K_PESS A condB no | 2988434 1391 0.047 -44.1 -38.4 -25.4 0.533 136.3
SELL_c2.5_T240 K_PESS A condB yes | 283418 343 0.121 169.7 109.1 188.2 0.609 136.4
SELL_c2.5_T240 K_PESS A hour h0 | 136608 138 0.101 22.7 19.1 37.0 0.435 148.6
SELL_c2.5_T240 K_PESS A hour h1 | 136358 54 0.040 -78.3 -83.2 -62.6 0.370 156.6
SELL_c2.5_T240 K_PESS A hour h10 | 136344 53 0.039 15.2 -5.6 27.3 0.585 141.9
SELL_c2.5_T240 K_PESS A hour h11 | 136231 56 0.041 -117.7 -115.0 -104.2 0.518 142.7
SELL_c2.5_T240 K_PESS A hour h12 | 136350 74 0.054 -29.5 -30.0 -2.3 0.595 118.3
SELL_c2.5_T240 K_PESS A hour h13 | 136358 166 0.122 190.2 58.9 211.8 0.669 153.9
SELL_c2.5_T240 K_PESS A hour h14 | 136480 125 0.092 -19.9 33.9 0.3 0.440 156.6
SELL_c2.5_T240 K_PESS A hour h15 | 136465 104 0.076 -99.8 -84.7 -72.6 0.567 131.6
SELL_c2.5_T240 K_PESS A hour h16 | 136566 116 0.085 149.2 149.0 164.7 0.612 120.6
SELL_c2.5_T240 K_PESS A hour h17 | 136256 91 0.067 102.6 101.2 119.1 0.582 125.6
SELL_c2.5_T240 K_PESS A hour h18 | 136353 57 0.042 202.7 199.4 220.3 0.614 112.8
SELL_c2.5_T240 K_PESS A hour h19 | 136234 62 0.046 -940.9 -902.0 -927.1 0.500 139.0
SELL_c2.5_T240 K_PESS A hour h2 | 136422 58 0.043 -264.5 -264.3 -248.7 0.414 154.2
SELL_c2.5_T240 K_PESS A hour h20 | 136351 49 0.036 -78.8 -31.7 -58.6 0.633 132.7
SELL_c2.5_T240 K_PESS A hour h21 | 136217 43 0.032 497.3 537.2 508.7 0.651 97.7
SELL_c2.5_T240 K_PESS A hour h22 | 136111 52 0.038 106.9 78.2 124.9 0.538 122.7
SELL_c2.5_T240 K_PESS A hour h23 | 136059 36 0.026 -86.6 -56.5 -58.4 0.556 95.8
SELL_c2.5_T240 K_PESS A hour h3 | 136252 53 0.039 -73.2 -91.5 -59.1 0.491 141.4
SELL_c2.5_T240 K_PESS A hour h4 | 136260 55 0.040 199.9 186.6 225.8 0.636 118.1
SELL_c2.5_T240 K_PESS A hour h5 | 136127 57 0.042 67.0 70.7 87.2 0.526 143.4
SELL_c2.5_T240 K_PESS A hour h6 | 136266 57 0.042 1.6 -28.2 23.1 0.509 158.0
SELL_c2.5_T240 K_PESS A hour h7 | 136230 69 0.051 -181.1 -184.0 -158.1 0.565 137.5
SELL_c2.5_T240 K_PESS A hour h8 | 136565 62 0.045 65.2 56.1 77.4 0.597 113.7
SELL_c2.5_T240 K_PESS A hour h9 | 136389 47 0.034 5.4 17.3 18.8 0.511 141.8
SELL_c2.5_T240 K_PESS A mkt idio | 0 1317 NA -62.1 -57.2 -42.0 0.542 134.7
SELL_c2.5_T240 K_PESS A mkt market | 0 417 NA 188.7 142.4 202.5 0.566 141.4
SELL_c2.5_T240 K_PESS A qvratio 1_10 | 0 91 NA 306.1 93.0 326.3 0.714 166.9
SELL_c2.5_T240 K_PESS A qvratio gt10 | 0 1641 NA -21.7 -17.6 -3.2 0.539 134.7
SELL_c2.5_T240 K_PESS A qvratio lt1 | 0 2 NA 2334.5 2236.4 2372.1 0.500 98.0
SELL_c2.5_T240 K_PESS A tier T1 | 219092 79 0.036 -69.8 -78.7 -55.5 0.532 139.1
SELL_c2.5_T240 K_PESS A tier T2 | 1095287 424 0.039 4.9 -14.0 20.1 0.542 140.9
SELL_c2.5_T240 K_PESS A tier T3 | 1957473 1231 0.063 0.3 -3.1 20.3 0.551 134.6
SELL_c2.5_T240 K_PESS A wick1m iso | 0 69 NA 272.1 259.6 294.8 0.507 70.8
SELL_c2.5_T240 K_PESS A wick1m not | 0 1665 NA -13.1 -20.4 5.3 0.550 139.0
SELL_c2.5_T240 K_PESS A year y2021 | 533832 225 0.042 -43.7 -51.6 -27.0 0.507 149.0
SELL_c2.5_T240 K_PESS A year y2022 | 1190474 587 0.049 41.1 3.4 59.2 0.595 133.4
SELL_c2.5_T240 K_PESS A year y2023 | 1547546 922 0.060 -18.8 -6.9 0.5 0.528 135.1
SELL_c2.5_T240 K_PESS B condB no | 5274809 2605 0.049 45.5 50.3 72.9 0.575 122.9
SELL_c2.5_T240 K_PESS B condB yes | 672754 657 0.098 127.6 109.8 152.7 0.601 105.3
SELL_c2.5_T240 K_PESS B hour h0 | 248476 219 0.088 43.0 35.2 74.1 0.434 152.7
SELL_c2.5_T240 K_PESS B hour h1 | 248133 98 0.039 -29.3 -10.7 -6.1 0.480 141.4
SELL_c2.5_T240 K_PESS B hour h10 | 247734 132 0.053 121.3 128.9 150.6 0.598 128.9
SELL_c2.5_T240 K_PESS B hour h11 | 247516 124 0.050 230.8 220.8 253.8 0.694 116.0
SELL_c2.5_T240 K_PESS B hour h12 | 247857 131 0.053 -42.1 -66.5 -5.0 0.656 106.0
SELL_c2.5_T240 K_PESS B hour h13 | 248120 158 0.064 175.3 187.2 206.3 0.658 105.6
SELL_c2.5_T240 K_PESS B hour h14 | 248379 142 0.057 -114.2 -114.0 -84.9 0.599 111.1
SELL_c2.5_T240 K_PESS B hour h15 | 248619 175 0.070 -147.2 -119.9 -121.6 0.509 130.7
SELL_c2.5_T240 K_PESS B hour h16 | 248704 229 0.092 101.6 146.9 116.9 0.590 124.7
SELL_c2.5_T240 K_PESS B hour h17 | 248456 151 0.061 231.3 241.6 249.2 0.589 115.4
SELL_c2.5_T240 K_PESS B hour h18 | 247634 134 0.054 171.6 176.9 194.8 0.597 112.3
SELL_c2.5_T240 K_PESS B hour h19 | 247438 107 0.043 139.1 157.5 163.5 0.579 114.2
SELL_c2.5_T240 K_PESS B hour h2 | 248008 102 0.041 81.7 82.5 108.2 0.549 135.4
SELL_c2.5_T240 K_PESS B hour h20 | 247713 78 0.032 237.1 255.5 267.5 0.692 98.1
SELL_c2.5_T240 K_PESS B hour h21 | 247310 144 0.058 201.2 196.5 218.1 0.590 94.1
SELL_c2.5_T240 K_PESS B hour h22 | 247190 124 0.050 115.3 110.0 144.5 0.540 92.2
SELL_c2.5_T240 K_PESS B hour h23 | 246686 182 0.074 270.2 185.9 288.6 0.725 93.8
SELL_c2.5_T240 K_PESS B hour h3 | 247701 103 0.042 -35.4 -43.8 -18.9 0.515 130.0
SELL_c2.5_T240 K_PESS B hour h4 | 247650 106 0.043 -408.0 -402.0 -370.6 0.481 147.3
SELL_c2.5_T240 K_PESS B hour h5 | 247405 107 0.043 85.2 85.1 105.5 0.467 135.4
SELL_c2.5_T240 K_PESS B hour h6 | 247448 132 0.053 46.9 44.1 82.3 0.591 118.1
SELL_c2.5_T240 K_PESS B hour h7 | 247509 160 0.065 44.1 43.9 89.9 0.619 113.0
SELL_c2.5_T240 K_PESS B hour h8 | 248095 124 0.050 -105.8 -120.0 -69.3 0.613 119.5
SELL_c2.5_T240 K_PESS B hour h9 | 247782 100 0.040 -68.6 -63.4 -38.8 0.540 125.7
SELL_c2.5_T240 K_PESS B mkt idio | 0 2646 NA 64.1 64.7 92.7 0.586 118.7
SELL_c2.5_T240 K_PESS B mkt market | 0 616 NA 52.9 51.7 72.7 0.555 122.1
SELL_c2.5_T240 K_PESS B qvratio 1_10 | 0 54 NA 123.2 85.9 154.3 0.389 160.0
SELL_c2.5_T240 K_PESS B qvratio gt10 | 0 3208 NA 61.0 61.9 87.8 0.583 118.6
SELL_c2.5_T240 K_PESS B tier T1 | 175370 23 0.013 -85.8 135.0 -76.9 0.217 205.7
SELL_c2.5_T240 K_PESS B tier T2 | 875827 169 0.019 24.2 52.8 29.5 0.456 149.8
SELL_c2.5_T240 K_PESS B tier T3 | 4896366 3070 0.063 65.2 62.3 93.5 0.590 117.0
SELL_c2.5_T240 K_PESS B wick1m iso | 0 167 NA 393.3 392.1 413.8 0.389 41.1
SELL_c2.5_T240 K_PESS B wick1m not | 0 3095 NA 44.1 44.5 71.4 0.590 123.5
SELL_c2.5_T240 K_PESS B year y2024 | 2304866 1003 0.044 -4.0 -0.2 14.7 0.517 138.1
SELL_c2.5_T240 K_PESS B year y2025 | 3642697 2259 0.062 91.3 90.0 121.9 0.608 111.0
SELL_c2.5_T1440 K_OPT3 A condB no | 2988434 1403 0.047 72.1 73.4 98.2 0.741 529.9
SELL_c2.5_T1440 K_OPT3 A condB yes | 283418 346 0.122 350.1 263.5 367.8 0.838 404.2
SELL_c2.5_T1440 K_OPT3 A hour h0 | 136608 138 0.101 130.2 127.5 151.6 0.725 584.8
SELL_c2.5_T1440 K_OPT3 A hour h1 | 136358 54 0.040 111.5 60.8 149.8 0.704 607.1
SELL_c2.5_T1440 K_OPT3 A hour h10 | 136344 53 0.039 152.5 131.0 180.9 0.698 541.6
SELL_c2.5_T1440 K_OPT3 A hour h11 | 136231 56 0.041 -111.4 -84.3 -68.1 0.679 605.8
SELL_c2.5_T1440 K_OPT3 A hour h12 | 136350 75 0.055 57.0 78.4 88.4 0.733 505.2
SELL_c2.5_T1440 K_OPT3 A hour h13 | 136358 167 0.122 571.9 394.8 590.6 0.886 356.6
SELL_c2.5_T1440 K_OPT3 A hour h14 | 136480 127 0.093 74.6 59.8 93.9 0.654 698.6
SELL_c2.5_T1440 K_OPT3 A hour h15 | 136465 105 0.077 -55.6 -39.6 -27.3 0.724 543.8
SELL_c2.5_T1440 K_OPT3 A hour h16 | 136566 116 0.085 143.9 139.4 176.3 0.836 409.2
SELL_c2.5_T1440 K_OPT3 A hour h17 | 136256 91 0.067 82.8 82.2 109.3 0.780 461.8
SELL_c2.5_T1440 K_OPT3 A hour h18 | 136353 59 0.043 318.0 320.6 326.2 0.831 395.9
SELL_c2.5_T1440 K_OPT3 A hour h19 | 136234 62 0.046 55.0 106.1 72.7 0.694 588.7
SELL_c2.5_T1440 K_OPT3 A hour h2 | 136422 59 0.043 -92.9 -101.8 -77.4 0.712 562.3
SELL_c2.5_T1440 K_OPT3 A hour h20 | 136351 49 0.036 185.3 214.4 202.5 0.714 524.9
SELL_c2.5_T1440 K_OPT3 A hour h21 | 136217 44 0.032 596.5 599.0 602.0 0.909 284.4
SELL_c2.5_T1440 K_OPT3 A hour h22 | 136111 56 0.041 210.5 172.8 224.0 0.750 562.1
SELL_c2.5_T1440 K_OPT3 A hour h23 | 136059 36 0.026 172.8 263.7 216.3 0.833 398.2
SELL_c2.5_T1440 K_OPT3 A hour h3 | 136252 54 0.040 -184.1 -205.3 -149.7 0.667 598.6
SELL_c2.5_T1440 K_OPT3 A hour h4 | 136260 55 0.040 -171.0 -176.4 -129.4 0.836 387.0
SELL_c2.5_T1440 K_OPT3 A hour h5 | 136127 57 0.042 102.7 121.3 125.2 0.754 537.4
SELL_c2.5_T1440 K_OPT3 A hour h6 | 136266 57 0.042 61.3 20.6 78.2 0.754 536.9
SELL_c2.5_T1440 K_OPT3 A hour h7 | 136230 70 0.051 85.2 86.8 110.9 0.757 479.8
SELL_c2.5_T1440 K_OPT3 A hour h8 | 136565 62 0.045 168.9 176.0 179.3 0.823 393.8
SELL_c2.5_T1440 K_OPT3 A hour h9 | 136389 47 0.034 -162.1 -162.4 -119.8 0.723 521.1
SELL_c2.5_T1440 K_OPT3 A mkt idio | 0 1324 NA 84.7 85.5 114.4 0.758 501.4
SELL_c2.5_T1440 K_OPT3 A mkt market | 0 425 NA 259.2 190.4 267.4 0.769 516.3
SELL_c2.5_T1440 K_OPT3 A qvratio 1_10 | 0 92 NA 765.9 487.7 779.6 0.946 264.9
SELL_c2.5_T1440 K_OPT3 A qvratio gt10 | 0 1655 NA 88.9 87.5 114.0 0.750 518.9
SELL_c2.5_T1440 K_OPT3 A qvratio lt1 | 0 2 NA 2366.7 2268.7 2372.1 0.500 98.0
SELL_c2.5_T1440 K_OPT3 A tier T1 | 219092 79 0.036 241.1 184.9 249.8 0.709 553.9
SELL_c2.5_T1440 K_OPT3 A tier T2 | 1095287 425 0.039 173.2 130.7 183.1 0.751 520.1
SELL_c2.5_T1440 K_OPT3 A tier T3 | 1957473 1245 0.064 104.2 99.6 134.6 0.767 496.8
SELL_c2.5_T1440 K_OPT3 A wick1m iso | 0 69 NA 324.2 301.3 355.0 0.826 322.0
SELL_c2.5_T1440 K_OPT3 A wick1m not | 0 1680 NA 119.0 103.2 143.2 0.758 512.5
SELL_c2.5_T1440 K_OPT3 A year y2021 | 533832 227 0.043 133.0 114.8 141.6 0.718 572.5
SELL_c2.5_T1440 K_OPT3 A year y2022 | 1190474 589 0.049 195.5 145.8 220.0 0.801 442.3
SELL_c2.5_T1440 K_OPT3 A year y2023 | 1547546 933 0.060 82.5 88.1 110.8 0.745 528.2
SELL_c2.5_T1440 K_OPT3 B condB no | 5264576 2628 0.050 78.8 75.6 130.6 0.787 450.8
SELL_c2.5_T1440 K_OPT3 B condB yes | 672754 659 0.098 41.9 31.7 110.7 0.791 410.9
SELL_c2.5_T1440 K_OPT3 B hour h0 | 247962 217 0.088 172.1 166.4 244.2 0.714 594.4
SELL_c2.5_T1440 K_OPT3 B hour h1 | 247620 99 0.040 -136.2 -95.9 -97.5 0.727 561.4
SELL_c2.5_T1440 K_OPT3 B hour h10 | 247219 135 0.055 -32.2 -13.3 49.4 0.822 396.8
SELL_c2.5_T1440 K_OPT3 B hour h11 | 247001 124 0.050 137.6 134.1 167.3 0.847 368.0
SELL_c2.5_T1440 K_OPT3 B hour h12 | 247338 132 0.053 -230.4 -291.0 -148.5 0.833 386.3
SELL_c2.5_T1440 K_OPT3 B hour h13 | 247603 163 0.066 139.3 147.5 188.8 0.822 359.8
SELL_c2.5_T1440 K_OPT3 B hour h14 | 247866 142 0.057 -75.5 -74.1 -45.5 0.754 457.3
SELL_c2.5_T1440 K_OPT3 B hour h15 | 248109 176 0.071 -101.9 -84.6 -62.2 0.670 601.6
SELL_c2.5_T1440 K_OPT3 B hour h16 | 248184 231 0.093 148.7 168.1 169.0 0.771 481.6
SELL_c2.5_T1440 K_OPT3 B hour h17 | 247937 153 0.062 288.6 265.7 312.3 0.810 440.1
SELL_c2.5_T1440 K_OPT3 B hour h18 | 247634 135 0.055 219.2 227.1 256.4 0.822 406.0
SELL_c2.5_T1440 K_OPT3 B hour h19 | 247438 109 0.044 371.0 381.4 400.5 0.798 402.7
SELL_c2.5_T1440 K_OPT3 B hour h2 | 247494 103 0.042 -110.9 -105.3 38.8 0.786 457.9
SELL_c2.5_T1440 K_OPT3 B hour h20 | 247713 81 0.033 297.1 342.8 342.3 0.889 310.4
SELL_c2.5_T1440 K_OPT3 B hour h21 | 247310 144 0.058 188.9 207.6 206.6 0.833 319.6
SELL_c2.5_T1440 K_OPT3 B hour h22 | 246674 124 0.050 96.2 47.3 129.0 0.815 392.7
SELL_c2.5_T1440 K_OPT3 B hour h23 | 246182 183 0.074 114.6 18.3 133.4 0.831 344.2
SELL_c2.5_T1440 K_OPT3 B hour h3 | 247202 103 0.042 -448.5 -458.2 -284.7 0.738 499.5
SELL_c2.5_T1440 K_OPT3 B hour h4 | 247143 106 0.043 -160.6 -150.0 -44.4 0.745 542.1
SELL_c2.5_T1440 K_OPT3 B hour h5 | 246893 110 0.045 220.8 240.1 248.6 0.736 512.7
SELL_c2.5_T1440 K_OPT3 B hour h6 | 246945 132 0.053 227.3 202.4 302.6 0.803 437.1
SELL_c2.5_T1440 K_OPT3 B hour h7 | 247003 160 0.065 -25.5 -27.7 64.9 0.819 398.5
SELL_c2.5_T1440 K_OPT3 B hour h8 | 247590 125 0.050 131.8 118.9 210.6 0.784 432.9
SELL_c2.5_T1440 K_OPT3 B hour h9 | 247270 100 0.040 96.5 97.7 147.6 0.790 430.4
SELL_c2.5_T1440 K_OPT3 B mkt idio | 0 2669 NA 77.6 80.3 137.1 0.793 432.9
SELL_c2.5_T1440 K_OPT3 B mkt market | 0 618 NA 44.4 8.8 81.2 0.762 485.3
SELL_c2.5_T1440 K_OPT3 B qvratio 1_10 | 0 54 NA 195.5 91.6 241.0 0.611 707.9
SELL_c2.5_T1440 K_OPT3 B qvratio gt10 | 0 3233 NA 69.3 66.4 124.7 0.790 438.4
SELL_c2.5_T1440 K_OPT3 B tier T1 | 175170 23 0.013 180.7 218.1 179.8 0.652 887.7
SELL_c2.5_T1440 K_OPT3 B tier T2 | 874828 168 0.019 11.7 9.2 -5.6 0.714 577.4
SELL_c2.5_T1440 K_OPT3 B tier T3 | 4887332 3096 0.063 73.8 68.8 133.4 0.792 432.2
SELL_c2.5_T1440 K_OPT3 B wick1m iso | 0 166 NA 412.0 404.4 464.3 0.952 143.7
SELL_c2.5_T1440 K_OPT3 B wick1m not | 0 3121 NA 53.3 48.9 108.7 0.779 458.7
SELL_c2.5_T1440 K_OPT3 B year y2024 | 2304866 1013 0.044 109.2 117.7 131.1 0.766 503.0
SELL_c2.5_T1440 K_OPT3 B year y2025 | 3632464 2274 0.063 54.5 44.2 124.6 0.797 416.0
SELL_c2.5_T1440 K_PESS A condB no | 2988434 1391 0.047 61.6 62.9 95.0 0.724 534.7
SELL_c2.5_T1440 K_PESS A condB yes | 283418 343 0.121 343.2 258.1 367.0 0.819 406.0
SELL_c2.5_T1440 K_PESS A hour h0 | 136608 138 0.101 122.8 119.6 151.3 0.703 586.7
SELL_c2.5_T1440 K_PESS A hour h1 | 136358 54 0.040 103.9 52.5 149.8 0.667 619.5
SELL_c2.5_T1440 K_PESS A hour h10 | 136344 53 0.039 145.5 123.8 180.9 0.698 541.6
SELL_c2.5_T1440 K_PESS A hour h11 | 136231 56 0.041 -119.3 -91.4 -68.1 0.679 606.0
SELL_c2.5_T1440 K_PESS A hour h12 | 136350 74 0.054 43.9 64.8 82.7 0.716 512.9
SELL_c2.5_T1440 K_PESS A hour h13 | 136358 166 0.122 564.9 388.7 588.7 0.886 359.6
SELL_c2.5_T1440 K_PESS A hour h14 | 136480 125 0.092 60.0 44.7 86.9 0.656 699.8
SELL_c2.5_T1440 K_PESS A hour h15 | 136465 104 0.076 -70.9 -55.1 -35.3 0.712 550.7
SELL_c2.5_T1440 K_PESS A hour h16 | 136566 116 0.085 134.8 134.0 173.3 0.802 418.2
SELL_c2.5_T1440 K_PESS A hour h17 | 136256 91 0.067 76.6 76.2 109.4 0.769 461.9
SELL_c2.5_T1440 K_PESS A hour h18 | 136353 57 0.042 308.4 312.6 325.2 0.789 412.1
SELL_c2.5_T1440 K_PESS A hour h19 | 136234 62 0.046 47.9 97.9 72.7 0.694 588.7
SELL_c2.5_T1440 K_PESS A hour h2 | 136422 58 0.043 -116.4 -125.7 -90.6 0.707 581.1
SELL_c2.5_T1440 K_PESS A hour h20 | 136351 49 0.036 179.2 207.4 203.4 0.714 525.0
SELL_c2.5_T1440 K_PESS A hour h21 | 136217 43 0.032 597.7 600.7 608.1 0.884 291.2
SELL_c2.5_T1440 K_PESS A hour h22 | 136111 52 0.038 204.1 173.7 224.6 0.712 562.9
SELL_c2.5_T1440 K_PESS A hour h23 | 136059 36 0.026 165.5 256.0 216.3 0.694 398.4
SELL_c2.5_T1440 K_PESS A hour h3 | 136252 53 0.039 -203.7 -224.9 -160.1 0.642 611.1
SELL_c2.5_T1440 K_PESS A hour h4 | 136260 55 0.040 -177.3 -186.3 -129.4 0.836 387.9
SELL_c2.5_T1440 K_PESS A hour h5 | 136127 57 0.042 96.1 115.0 125.2 0.737 537.6
SELL_c2.5_T1440 K_PESS A hour h6 | 136266 57 0.042 54.8 14.0 78.2 0.754 536.9
SELL_c2.5_T1440 K_PESS A hour h7 | 136230 69 0.051 72.2 73.9 104.8 0.739 486.8
SELL_c2.5_T1440 K_PESS A hour h8 | 136565 62 0.045 162.6 166.5 179.3 0.774 394.4
SELL_c2.5_T1440 K_PESS A hour h9 | 136389 47 0.034 -167.9 -168.4 -118.6 0.702 521.4
SELL_c2.5_T1440 K_PESS A mkt idio | 0 1317 NA 75.3 76.3 112.1 0.740 506.3
SELL_c2.5_T1440 K_PESS A mkt market | 0 417 NA 250.1 180.9 264.6 0.751 518.5
SELL_c2.5_T1440 K_PESS A qvratio 1_10 | 0 91 NA 759.2 476.4 778.3 0.945 267.2
SELL_c2.5_T1440 K_PESS A qvratio gt10 | 0 1641 NA 79.0 78.1 111.2 0.732 523.2
SELL_c2.5_T1440 K_PESS A qvratio lt1 | 0 2 NA 2334.5 2236.4 2372.1 0.500 98.0
SELL_c2.5_T1440 K_PESS A tier T1 | 219092 79 0.036 235.9 179.4 249.8 0.684 553.8
SELL_c2.5_T1440 K_PESS A tier T2 | 1095287 424 0.039 167.0 124.0 183.2 0.736 520.6
SELL_c2.5_T1440 K_PESS A tier T3 | 1957473 1231 0.063 92.6 88.7 130.4 0.749 502.5
SELL_c2.5_T1440 K_PESS A wick1m iso | 0 69 NA 316.1 295.4 355.0 0.594 323.0
SELL_c2.5_T1440 K_PESS A wick1m not | 0 1665 NA 109.1 93.5 140.2 0.749 517.0
SELL_c2.5_T1440 K_PESS A year y2021 | 533832 225 0.042 120.4 101.7 136.1 0.716 577.4
SELL_c2.5_T1440 K_PESS A year y2022 | 1190474 587 0.049 187.4 137.6 218.5 0.780 444.7
SELL_c2.5_T1440 K_PESS A year y2023 | 1547546 922 0.060 71.9 78.5 107.5 0.726 533.7
SELL_c2.5_T1440 K_PESS B condB no | 5264576 2597 0.049 64.6 61.4 124.2 0.760 457.1
SELL_c2.5_T1440 K_PESS B condB yes | 672754 657 0.098 33.8 21.3 110.2 0.726 413.2
SELL_c2.5_T1440 K_PESS B hour h0 | 247962 217 0.088 163.7 157.2 243.6 0.705 599.2
SELL_c2.5_T1440 K_PESS B hour h1 | 247620 98 0.040 -155.3 -114.2 -107.1 0.714 564.8
SELL_c2.5_T1440 K_PESS B hour h10 | 247219 132 0.053 -55.7 -38.6 34.4 0.803 417.6
SELL_c2.5_T1440 K_PESS B hour h11 | 247001 123 0.050 130.0 126.4 165.9 0.846 371.0
SELL_c2.5_T1440 K_PESS B hour h12 | 247338 130 0.053 -255.5 -314.9 -165.7 0.800 395.0
SELL_c2.5_T1440 K_PESS B hour h13 | 247603 158 0.064 129.3 139.9 186.6 0.791 361.9
SELL_c2.5_T1440 K_PESS B hour h14 | 247866 142 0.057 -83.0 -82.9 -45.5 0.718 457.4
SELL_c2.5_T1440 K_PESS B hour h15 | 248109 175 0.071 -112.7 -94.9 -64.6 0.651 605.4
SELL_c2.5_T1440 K_PESS B hour h16 | 248184 228 0.092 137.0 156.1 164.3 0.754 488.8
SELL_c2.5_T1440 K_PESS B hour h17 | 247937 151 0.061 275.6 252.1 305.9 0.788 446.0
SELL_c2.5_T1440 K_PESS B hour h18 | 247634 134 0.054 211.5 218.0 255.6 0.784 409.3
SELL_c2.5_T1440 K_PESS B hour h19 | 247438 107 0.043 361.7 372.0 398.1 0.766 413.0
SELL_c2.5_T1440 K_PESS B hour h2 | 247494 102 0.041 -125.1 -119.6 33.0 0.775 462.4
SELL_c2.5_T1440 K_PESS B hour h20 | 247713 78 0.032 294.8 333.6 347.5 0.872 289.0
SELL_c2.5_T1440 K_PESS B hour h21 | 247310 144 0.058 181.2 195.7 206.6 0.694 320.3
SELL_c2.5_T1440 K_PESS B hour h22 | 246674 124 0.050 88.4 38.0 129.0 0.677 393.0
SELL_c2.5_T1440 K_PESS B hour h23 | 246182 182 0.074 103.7 6.7 129.0 0.813 347.2
SELL_c2.5_T1440 K_PESS B hour h3 | 247202 102 0.041 -466.9 -476.6 -292.6 0.696 503.8
SELL_c2.5_T1440 K_PESS B hour h4 | 247143 106 0.043 -179.9 -168.9 -56.1 0.717 554.3
SELL_c2.5_T1440 K_PESS B hour h5 | 246893 107 0.043 195.6 215.9 232.6 0.682 529.1
SELL_c2.5_T1440 K_PESS B hour h6 | 246945 132 0.053 209.3 187.2 291.2 0.765 456.2
SELL_c2.5_T1440 K_PESS B hour h7 | 247003 159 0.064 -36.9 -39.7 61.0 0.792 401.0
SELL_c2.5_T1440 K_PESS B hour h8 | 247590 124 0.050 120.1 106.0 206.9 0.758 433.1
SELL_c2.5_T1440 K_PESS B hour h9 | 247270 99 0.040 85.9 87.1 144.5 0.747 434.8
SELL_c2.5_T1440 K_PESS B mkt idio | 0 2638 NA 64.2 65.9 131.5 0.759 439.0
SELL_c2.5_T1440 K_PESS B mkt market | 0 616 NA 33.8 -0.4 78.0 0.726 487.9
SELL_c2.5_T1440 K_PESS B qvratio 1_10 | 0 54 NA 168.4 93.8 222.7 0.574 711.3
SELL_c2.5_T1440 K_PESS B qvratio gt10 | 0 3200 NA 56.6 52.7 119.6 0.756 443.8
SELL_c2.5_T1440 K_PESS B tier T1 | 175170 23 0.013 175.6 213.0 179.8 0.652 887.7
SELL_c2.5_T1440 K_PESS B tier T2 | 874828 168 0.019 -3.2 -3.7 -12.5 0.679 584.5
SELL_c2.5_T1440 K_PESS B tier T3 | 4887332 3063 0.063 60.9 55.3 128.3 0.758 437.5
SELL_c2.5_T1440 K_PESS B wick1m iso | 0 166 NA 402.6 385.9 464.3 0.488 146.1
SELL_c2.5_T1440 K_PESS B wick1m not | 0 3088 NA 39.9 35.5 102.9 0.767 464.5
SELL_c2.5_T1440 K_PESS B year y2024 | 2304866 1003 0.044 96.1 104.6 125.1 0.743 511.5
SELL_c2.5_T1440 K_PESS B year y2025 | 3632464 2251 0.062 41.6 30.5 119.7 0.757 420.1

## 6. skip_px_by_cell (don vi khong dat vi muc gia <= 0, merge): {'BUY_c2.5_T240': 1144, 'BUY_c2.5_T1440': 1144}

## 7. Bat thuong du lieu / nghi van ve tinh dung dan
- Khong V FAIL, khong abort, khong chay lai. V4 shard4 bo 1 symbol (1000BTTCUSDT span 75,2 ngay < 90) theo luat prereg, van du 2 check.
- Don vi bi loc vi muc gia <= 0 (L-S3-1): chi o BUY c2,5 (1 144 don vi moi o T; V3 shard: 1152 + 32 + 1104 = 2288 = 2 x 1144); n_dat BUY c2,5 = 3 271 836 / 5 946 435 so voi 3 271 852 / 5 947 542 cac o khac.
- n_dat nua B khac nhau theo T (T240 5 947 542 vs T1440 5 937 309): don vi T1440 cuoi nua B bi cat (khong du T), khong bat thuong.
- Nhieu (symbol, thang) co ti le thang thieu > 1% (V3 sym_month_missing) - chi so V3, khong vuot nguong abort.
- Truong M_stress_slip_x5 chi co nghia o K_PESS; o K_OPT3 gia tri bang M (khong dung).
- up95 (upper_sim95) co the nho hon ci95_hi mot so o (vd K_OPT3 A SELL_c2.5_T1440): hai dinh nghia khac nhau (simultaneous vs marginal); khong dung cho PASS.
- Dong ho Oracle hien 2026-11-20 UTC; ghi TRIALS_GRID dung ngay 2026-11-21 theo yeu cau.
