# DEV_B3 - LEVZ B3 (PREREG_LEVZ_B3 30a8c413 + ERRATA1 308cd1fc) - CODE + TEST, CHUA TRAIN / CHAM TREN DU LIEU THAT (cho A1 audit)
2026-11-26. Khong co so loi nhuan / tuong quan nhan-dac trung that nao trong file nay.

## Chay tung buoc (tu ~/claude_master/w3/levz_b3; viec nang qua code/heavy.sh = kiem RAM >= 4000 MB, dia >= 12 GB, flock + nice)
1. pool:      python3 code/cand_b3.py build           -> work/pool_b3.npz, out/cand_b3.json
2. exit_Y:    python3 code/exitsel_b3.py               -> out/exitsel_b3.json
3. C0:        python3 code/cand_b3.py c0               -> out/cand_b3.json (muc C0)
4. nhan:      bash code/heavy.sh code/labels_b3.py build   -> work/labels_b3.npz (315 MB), out/labels_b3.json (~90 s)
5. dac trung: bash code/heavy.sh code/feat_b3.py build     -> work/feat_b3.parquet, out/feat_b3.json (~15 s)
6. test:      bash code/heavy.sh code/test_b3.py           -> out/test_report.json (~5 phut)
7. (SAU A1)   bash code/heavy.sh code/wfo_b3.py --real <co do MASTER cap sau khi A1 PASS> -> out/wfo_b3.json, out/wfo_b3_ledger.parquet
8. (SAU A1)   bash code/heavy.sh code/cv_b3.py --real <co do MASTER cap sau khi A1 PASS>  -> out/cv_b3.json
9. (SAU A1)   python3 code/report_b3.py                                -> out/report_b3.md / .json
Buoc 1-6 da chay. Buoc 7-9 CHUA chay tren du lieu that (chi chay tren du lieu gia trong test f, g).

## So dem
- Pool W7 E0 z >= 1,5: 28 864 ung vien, 2 730 dot. Ung vien / dot: 2021-12 16 / 1; 2022 200 / 25; 2023 6 686 / 644; 2024 18 431 / 1 632;
  2025 3 531 / 429. Hoi quy z >= 2,5 / 3,0 / 3,5 == cand_b1 (4 792 / 1 965 / 838 dong) TRUNG 100 %.
- exit_2024 = xi 170 (SL 0,50, H 336, arm 3 %, gap 2 %; hoa voi H 720 -> H ngan); exit_2025 = xi 72 (SL 0,30, H 24, arm 7 %, gap 2 %).
  exit_2023 khong tinh duoc dung luat.
- C0: 2024 train 500 dot (nam 2023: 475) KHONG DAT; 2025 2 297 (1 628) DAT; 2023 25 KHONG DAT.
- Nhan (ve sinh): 28 864 dong, NaN 0 / 0; ly do thoat exit_2024: sl 1 100, trail 26 890, time 854, eod 20; exit_2025: sl 603,
  trail 7 911, time 20 342, eod 8; flag 0; longgap 0. Trung exits.npz B1 tren 7 936 dong (moi mang, tuyet doi).
- Dac trung: 34 (25 coin + 9 thi truong), KHONG bo cai nao; NaN <= 0,5 % (df24 3,3 %). Danh sach: out/feat_b3.json.

## Test (out/test_report.json) - xem file; ban moi nhat sau sua A1: 11 test
- a_causal / a_px_timing / b_regression / c_purge / d_dots / e_groupkfold / f_fake_pipeline / g_determinism: nhu ban truoc.
  b_regression: nhan so voi B1 port._net(p) / N tinh doc lap tung dong (khong dung label_of).
- h_weights: w = 1 / kich thuoc dot (vi du tay); LightGBM va Ridge tren dac trung hang -> du doan = TB CO TRONG SO (-0,990, khong
  phai +0,636); spy: wfo_year truyen dung 1 / kich thuoc dot + nhom = quy lich; cv_oof truyen dung trong so cho moi fold.
- i_wfo_formulas: nguong 80,2 / 90,1 / 0 tren 1..100; T0 nghiem (> 0), T20 bao gom (>=); BL_S20 = q80 s train; BL_Z30 = s >= 3,0;
  p_keep = 12 / 40; p = ti le >= ; Q5 bo ceil(5 %) lenh LON nhat (dap an tay 2 lenh, con -2); tap test/train doc lap va khong giao;
  noi day trong wfo_year (nguong, so chon, BL, p_keep, p, Q5) so voi tinh doc lap.
- j_cv_formulas: nguong C2 tren toan khoang = 24,2 (khong theo nam); C1 dem IC > 0 nghiem; C2 can ca 3 nam > 0 VA > BL_S20; C3 ret > 0.
- Mutant tu kiem (ban copy trong mktemp, khong ghi out/): logs/mut.log.

## A1 can soi
- feat_b3.features (dac biet liqrank, levrun, ncand7d, cua so px), cv_b3.cv_masks, wfo_b3.wfo_year (train/test mask, RAND, Q5),
  model_b3 (OOF / nguong / mot-seed), CHOICES_B3 #8-#27.
- Khong lam: Y = 2023 (ERRATA1). P1..P8 khong cham (ERRATA1 E1).
