# SIGCOUNT - dem su kien dong long LEVZ (CHI DEM, khong gia / loi suat)

## Cong thuc (da cai dat)
Chung: t = gio quyet dinh (thong tin <= t). X[t] = ln OI ban ghi 5m moi nhat ts in (t-70m, t-10m] (frozen tier-1). f[t] = r8 = rate*8/interval_h
cua ky thanh toan moi nhat ts <= t-1m (con hieu luc). Wh = 24W. m,sd = mean/std(ddof1) cua X tren hang t-Wh..t-1 (>= 0.8Wh). Funding: mean_f, sd_f tren
cac ky trong [t-W, ky moi nhat) (>= 0.8 W/ih ky). U = universe tier-1 (qv30 >= 20M, >= 45 ngay, loai stable). Moi trang thai yeu cau U[t].
- D0: z_oi=(X-m)/max(sd,0.02) > z, z_f=(f-mean_f)/max(sd_f,5e-5) > z, f > 1e-4 (dung tier-1, so sanh '>' nhu sig.py).
- D1: D0 bo f > 1e-4.
- D2: san = trung vi cua sd (chinh coin) tren hang t-2160..t-1 (>= 720 gia tri hop le); z = num/max(sd, san); sd < 1e-9 (OI) / 1e-12 (funding, tinh so nguyen chinh xac) coi la 0; max(sd,san) <= nguong do hoac san chua du lich su => z = NaN.
  Ap cho ca OI (sd tu rolling) va funding (sd_f lay mau theo gio). Dieu kien z_oi2 > z, z_f2 > z.
- D3: D2 & f[t] > trung vi cua f (chuoi theo gio) tren hang t-720..t-1 (>= 576).
- D4: dev = X - m (m = trung binh W ngay truoc). dev[t] >= Q_q(dev, hang t-2160..t-1, >=720) VA f[t] >= Q_q(f, hang t-2160..t-1, >=720), quantile noi suy tuyen tinh.
  D4s = bien the chan doan, so sanh strict '>' (vi f bi dinh rat nhieu o dung 1e-4 => '>=' bat ca dai phang).
- D5: tai gio t, eligible = U & z_oi2, z_f2 huu han (z kieu D2); top p% = z >= gia tri lon thu ceil(p% * n_eligible); ca hai top p% & z_oi2 > 0 & z_f2 > 0.
Dem: vao = S[t] & !S[t-1]; dot = cac lan vao cung coin cach nhau < 24h (noi chuoi) gop; nam theo gio vao/dau dot; chi tinh tu 2022-01-01. Dot chua gio D0: trong [dau dot, cuoi run cuoi]
co >= 1 gio D0 (D0 cung W, cung z; D4/D5 doi chieu D0 z=2.5). Khoi dong: du lieu bat dau 2021-12-01 => san 90 ngay o Q1-2022 tinh tren lich su ngan hon (min 30 ngay).

## Tai lap D0 (so voi sig_W*.parquet)
- W7: {"z_oi": {"nan_mismatch": 0, "maxabs": 0.0}, "z_f": {"nan_mismatch": 0, "maxabs": 8.641133319997607e-08}, "f": {"nan_mismatch": 0, "maxabs": 0.0}, "u_mismatch": 0, "u_total_mine": 4790328, "u_total_sig": 4790328, "state_z2.0": {"sig": 11937, "mine": 11937, "mismatch": 0}, "state_z2.5": {"sig": 4792, "mine": 4792, "mismatch": 0}, "state_z3.0": {"sig": 1965, "mine": 1965, "mismatch": 0}, "episodes72_z2.5": {"mine": 757, "s1_ref": 757, "match": true}}
- W14: {"z_oi": {"nan_mismatch": 0, "maxabs": 0.0}, "z_f": {"nan_mismatch": 0, "maxabs": 9.022036628891783e-08}, "f": {"nan_mismatch": 0, "maxabs": 0.0}, "u_mismatch": 0, "u_total_mine": 4790328, "u_total_sig": 4790328, "state_z2.0": {"sig": 13514, "mine": 13514, "mismatch": 0}, "state_z2.5": {"sig": 5403, "mine": 5403, "mismatch": 0}, "state_z3.0": {"sig": 2238, "mine": 2238, "mismatch": 0}, "episodes72_z2.5": {"mine": 634, "s1_ref": 634, "match": true}}

## Kiem nhan qua: {"cuts": [1643911200000, 1650078000000, 1668020400000, 1703599200000, 1754200800000], "n_points": 100, "n_defs": 40, "point_mismatch_total": 0, "prefix_mismatch_total": 0, "trunc_vs_full_mismatch_total": 0, "pass_": true}

## W = 7 ngay

| dinh nghia | dot 2022 | 2023 | 2024 | 2025 | tong | min/max nam | %coin-h tong | coin | top5 coin % | med run h | %h f>0 | f vao med (%/8h) | %dot chua D0 | %D0 nam trong |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 z2.0 | 14 | 368 | 1002 | 270 | 1654 | 0.01 | 0.254 | 361 | 5.9 | 4 | 100.0 | 0.0498 | 100.0 | 100.0 |
| D1 z2.0 | 58 | 371 | 1008 | 285 | 1722 | 0.06 | 0.263 | 364 | 5.9 | 4 | 99.5 | 0.0487 | 96.1 | 100.0 |
| D0 z2.5 | 6 | 182 | 461 | 168 | 817 | 0.01 | 0.102 | 287 | 7.2 | 4 | 100.0 | 0.0526 | 100.0 | 100.0 |
| D1 z2.5 | 16 | 182 | 462 | 169 | 829 | 0.03 | 0.103 | 288 | 7.1 | 4 | 99.7 | 0.0521 | 98.6 | 100.0 |
| D0 z3.0 | 5 | 89 | 214 | 90 | 398 | 0.02 | 0.042 | 211 | 8.3 | 4 | 100.0 | 0.0572 | 100.0 | 100.0 |
| D1 z3.0 | 7 | 89 | 214 | 90 | 400 | 0.03 | 0.042 | 213 | 8.2 | 4 | 100.0 | 0.0571 | 99.5 | 100.0 |
| D2 z2.0 | 26 | 237 | 585 | 156 | 1004 | 0.04 | 0.157 | 299 | 7.5 | 4 | 99.7 | 0.0522 | 95.2 | 58.5 |
| D3 z2.0 | 26 | 237 | 579 | 156 | 998 | 0.04 | 0.155 | 299 | 7.5 | 4 | 99.7 | 0.0526 | 95.2 | 58.0 |
| D2 z2.5 | 3 | 105 | 241 | 87 | 436 | 0.01 | 0.057 | 219 | 8.5 | 4 | 100.0 | 0.0570 | 98.2 | 52.9 |
| D3 z2.5 | 3 | 105 | 240 | 87 | 435 | 0.01 | 0.057 | 219 | 8.5 | 4 | 100.0 | 0.0574 | 98.2 | 52.8 |
| D2 z3.0 | 2 | 53 | 107 | 46 | 208 | 0.02 | 0.022 | 139 | 10.1 | 4 | 100.0 | 0.0638 | 98.6 | 51.8 |
| D3 z3.0 | 2 | 53 | 106 | 46 | 207 | 0.02 | 0.022 | 138 | 10.1 | 4 | 100.0 | 0.0642 | 98.6 | 51.5 |
| D5 p5 | 358 | 431 | 784 | 687 | 2260 | 0.46 | 0.341 | 379 | 10.1 | 4 | 94.7 | 0.0100 | 17.9 | 50.3 |
| D5 p2 | 106 | 128 | 279 | 211 | 724 | 0.38 | 0.091 | 258 | 12.4 | 3 | 95.9 | 0.0275 | 31.2 | 28.0 |
| D4 q0.950 | 1411 | 1297 | 1142 | 1592 | 5442 | 0.72 | 1.647 | 437 | 5.6 | 4 | 99.3 | 0.0100 | 5.6 | 38.3 |
| D4s q0.950 | 31 | 383 | 615 | 200 | 1229 | 0.05 | 0.325 | 317 | 7.5 | 4 | 99.7 | 0.0427 | 24.7 | 38.3 |
| D4 q0.975 | 761 | 581 | 563 | 905 | 2810 | 0.62 | 0.724 | 371 | 7.2 | 4 | 99.4 | 0.0100 | 7.2 | 25.2 |
| D4s q0.975 | 13 | 168 | 290 | 115 | 586 | 0.04 | 0.131 | 232 | 9.4 | 5 | 99.9 | 0.0451 | 34.5 | 25.2 |
| D4 q0.990 | 384 | 252 | 263 | 497 | 1396 | 0.51 | 0.285 | 294 | 9.2 | 4 | 99.5 | 0.0100 | 9.2 | 16.0 |
| D4s q0.990 | 7 | 69 | 126 | 62 | 264 | 0.06 | 0.044 | 158 | 12.5 | 4 | 99.7 | 0.0490 | 49.2 | 16.0 |
| D5b p5 | 303 | 380 | 654 | 571 | 1908 | 0.46 | 0.281 | 352 | 11.3 | 4 | 99.8 | 0.0100 | 18.6 | 44.2 |
| D5b p2 | 127 | 137 | 257 | 215 | 736 | 0.49 | 0.091 | 255 | 14.3 | 3 | 99.8 | 0.0213 | 29.5 | 26.8 |
| D6a Q0.995 | 616 | 778 | 1012 | 810 | 3216 | 0.61 | 0.574 | 406 | 7.6 | 4 | 95.6 | 0.0270 | 25.2 | 100.0 |
| D6a Q0.998 | 265 | 434 | 474 | 385 | 1558 | 0.56 | 0.239 | 346 | 7.7 | 4 | 96.5 | 0.0346 | 46.8 | 89.5 |
| D6a Q0.999 | 158 | 269 | 287 | 230 | 944 | 0.55 | 0.127 | 296 | 7.7 | 4 | 96.4 | 0.0382 | 59.5 | 68.9 |
| D6b Q0.995 | 544 | 713 | 877 | 743 | 2877 | 0.62 | 0.558 | 370 | 9.7 | 5 | 95.8 | 0.0241 | 22.3 | 79.7 |
| D6b Q0.998 | 226 | 363 | 437 | 344 | 1370 | 0.52 | 0.236 | 324 | 10.3 | 5 | 96.2 | 0.0340 | 39.1 | 66.3 |
| D6b Q0.999 | 128 | 226 | 253 | 219 | 826 | 0.51 | 0.126 | 274 | 10.3 | 4 | 96.8 | 0.0383 | 52.3 | 53.1 |

## W = 14 ngay

| dinh nghia | dot 2022 | 2023 | 2024 | 2025 | tong | min/max nam | %coin-h tong | coin | top5 coin % | med run h | %h f>0 | f vao med (%/8h) | %dot chua D0 | %D0 nam trong |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 z2.0 | 11 | 361 | 848 | 193 | 1413 | 0.01 | 0.288 | 318 | 5.9 | 4 | 100.0 | 0.0496 | 100.0 | 100.0 |
| D1 z2.0 | 28 | 361 | 850 | 195 | 1434 | 0.03 | 0.291 | 318 | 5.9 | 4 | 99.8 | 0.0492 | 98.5 | 100.0 |
| D0 z2.5 | 4 | 174 | 427 | 109 | 714 | 0.01 | 0.115 | 274 | 7.3 | 4 | 100.0 | 0.0541 | 100.0 | 100.0 |
| D1 z2.5 | 6 | 174 | 427 | 110 | 717 | 0.01 | 0.115 | 274 | 7.3 | 4 | 100.0 | 0.0540 | 99.6 | 100.0 |
| D0 z3.0 | 3 | 84 | 195 | 69 | 351 | 0.02 | 0.048 | 193 | 8.3 | 4 | 100.0 | 0.0584 | 100.0 | 100.0 |
| D1 z3.0 | 4 | 84 | 195 | 69 | 352 | 0.02 | 0.048 | 193 | 8.2 | 4 | 100.0 | 0.0580 | 99.7 | 100.0 |
| D2 z2.0 | 9 | 212 | 487 | 116 | 824 | 0.02 | 0.169 | 268 | 6.9 | 5 | 99.9 | 0.0519 | 97.8 | 57.5 |
| D3 z2.0 | 9 | 212 | 487 | 116 | 824 | 0.02 | 0.169 | 268 | 6.9 | 5 | 99.9 | 0.0519 | 97.8 | 57.5 |
| D2 z2.5 | 2 | 93 | 221 | 62 | 378 | 0.01 | 0.063 | 190 | 9.8 | 4 | 100.0 | 0.0580 | 99.5 | 53.2 |
| D3 z2.5 | 2 | 93 | 221 | 62 | 378 | 0.01 | 0.063 | 190 | 9.8 | 4 | 100.0 | 0.0580 | 99.5 | 53.2 |
| D2 z3.0 | 2 | 39 | 96 | 41 | 178 | 0.02 | 0.024 | 123 | 11.8 | 4 | 100.0 | 0.0665 | 98.3 | 50.1 |
| D3 z3.0 | 2 | 39 | 96 | 41 | 178 | 0.02 | 0.024 | 123 | 11.8 | 4 | 100.0 | 0.0665 | 98.3 | 50.1 |
| D5 p5 | 302 | 355 | 667 | 584 | 1908 | 0.45 | 0.381 | 342 | 10.3 | 4 | 96.0 | 0.0100 | 17.0 | 44.8 |
| D5 p2 | 82 | 112 | 239 | 201 | 634 | 0.34 | 0.107 | 244 | 13.9 | 4 | 96.8 | 0.0249 | 29.3 | 26.3 |
| D4 q0.950 | 1247 | 1226 | 1071 | 1504 | 5048 | 0.71 | 1.808 | 431 | 6.3 | 5 | 99.5 | 0.0100 | 6.6 | 49.2 |
| D4s q0.950 | 32 | 371 | 615 | 210 | 1228 | 0.05 | 0.354 | 313 | 8.0 | 5 | 99.8 | 0.0417 | 27.2 | 49.2 |
| D4 q0.975 | 727 | 579 | 588 | 917 | 2811 | 0.63 | 0.825 | 380 | 6.8 | 4 | 99.5 | 0.0100 | 8.4 | 33.8 |
| D4s q0.975 | 16 | 178 | 318 | 130 | 642 | 0.05 | 0.145 | 241 | 9.3 | 4 | 99.9 | 0.0454 | 37.1 | 33.8 |
| D4 q0.990 | 402 | 244 | 282 | 529 | 1457 | 0.46 | 0.340 | 295 | 9.0 | 4 | 99.5 | 0.0100 | 11.7 | 23.5 |
| D4s q0.990 | 6 | 71 | 128 | 76 | 281 | 0.05 | 0.049 | 159 | 10.7 | 4 | 99.7 | 0.0531 | 60.5 | 23.5 |
| D5b p5 | 265 | 321 | 561 | 504 | 1651 | 0.47 | 0.313 | 324 | 11.5 | 4 | 99.7 | 0.0100 | 18.0 | 41.6 |
| D5b p2 | 101 | 127 | 217 | 206 | 651 | 0.47 | 0.105 | 245 | 14.6 | 4 | 99.8 | 0.0231 | 27.5 | 25.5 |
| D6a Q0.995 | 484 | 703 | 760 | 658 | 2605 | 0.64 | 0.584 | 361 | 8.4 | 6 | 97.4 | 0.0275 | 27.3 | 100.0 |
| D6a Q0.998 | 208 | 384 | 398 | 291 | 1281 | 0.52 | 0.245 | 304 | 8.4 | 5 | 97.5 | 0.0347 | 45.6 | 81.7 |
| D6a Q0.999 | 97 | 240 | 228 | 165 | 730 | 0.40 | 0.127 | 261 | 8.6 | 4 | 98.1 | 0.0390 | 58.5 | 59.8 |
| D6b Q0.995 | 476 | 640 | 708 | 638 | 2462 | 0.67 | 0.577 | 338 | 10.8 | 6 | 97.4 | 0.0241 | 21.5 | 74.6 |
| D6b Q0.998 | 195 | 333 | 338 | 288 | 1154 | 0.58 | 0.245 | 280 | 12.0 | 6 | 98.0 | 0.0338 | 38.2 | 62.6 |
| D6b Q0.999 | 101 | 210 | 204 | 171 | 686 | 0.48 | 0.128 | 233 | 12.0 | 5 | 98.2 | 0.0387 | 50.6 | 48.5 |

Chi tiet theo nam (coin-gio, lan vao, coin, thang dinh, top5, run, f>0, dot/thang, do trung): out/sigcount.json.

# BUOC 2 (MASTER msg 2): D5b, D6, mo ta luc vao, tap ung vien

## Dinh nghia them
- D5b: nhu D5 nhung tap xep hang = U & z2 huu han & f >= trung vi cat ngang cua f (cac coin U co f huu han) tai gio t; top p% tinh trong tap do.
- D6a / D6b: s = min(z_oi, z_f) (D6a: z kieu D1 = san sd co dinh, khong san f; D6b: z kieu D2). Nguong = phan vi Q cua toan bo s huu han cua moi coin-gio
  trong U, hang [d0-2160, d0-1], tinh lai MOI NGAY luc 00:00 UTC (d0), can >= 720 gio lich su; trang thai = U & s >= nguong & s > 0.
- Diem xep hang ung vien: D1/D6: s = min(z_oi, z_f); D5/D5b: min(hang phan vi cat ngang (rank pct, 1 = cao nhat, ties average) cua z_oi2, cua z_f2) trong tap xep hang.
- Ung vien: B0 sim.candidates() E0 (moi gio trang thai co nen 1m has1m; sap xep k tang, s giam, c tang); cooldown 72h nam o port.py, khong o danh sach ung vien.

## Nguong D6 (trung vi theo nam)
- D6a_W7_Q0.995: 2022=1.28, 2023=1.42, 2024=2.11, 2025=1.36
- D6a_W7_Q0.998: 2022=1.54, 2023=1.82, 2024=2.55, 2025=1.78
- D6a_W7_Q0.999: 2022=1.73, 2023=2.20, 2024=2.89, 2025=2.18
- D6b_W7_Q0.995: 2022=1.17, 2023=1.23, 2024=1.81, 2025=1.23
- D6b_W7_Q0.998: 2022=1.43, 2023=1.67, 2024=2.23, 2025=1.57
- D6b_W7_Q0.999: 2022=1.60, 2023=2.05, 2024=2.59, 2025=1.89
- D6a_W14_Q0.995: 2022=1.22, 2023=1.49, 2024=2.11, 2025=1.32
- D6a_W14_Q0.998: 2022=1.42, 2023=2.09, 2024=2.61, 2025=1.72
- D6a_W14_Q0.999: 2022=1.61, 2023=2.50, 2024=3.00, 2025=2.13
- D6b_W14_Q0.995: 2022=1.12, 2023=1.24, 2024=1.85, 2025=1.20
- D6b_W14_Q0.998: 2022=1.33, 2023=1.65, 2024=2.30, 2025=1.57
- D6b_W14_Q0.999: 2022=1.45, 2023=2.01, 2024=2.61, 2025=1.91

## Mo ta luc vao dot (tong 2022-25): %dot f>0,01% | %dot f > tb W ngay cua chinh no (z_f>0 that) | z_oi q10/50/90 | z_f q10/50/90

| def | dot | %f>1e-4 | %f>own mean | z_oi q10/50/90 | z_f q10/50/90 |
|---|---|---|---|---|---|
| D5_W7_p5 | 2260 | 44 | 100 | 1.6/2.2/3.6 | 0.6/1.3/3.5 |
| D5b_W7_p5 | 1908 | 45 | 100 | 1.4/2.2/3.6 | 0.6/1.3/3.6 |
| D5_W7_p2 | 724 | 56 | 100 | 2.0/2.8/4.3 | 0.8/1.6/4.7 |
| D5b_W7_p2 | 736 | 52 | 100 | 1.7/2.7/4.2 | 0.8/1.6/4.7 |
| D6a_W7_Q0.995 | 3216 | 62 | 100 | 1.4/2.1/3.3 | 1.3/2.1/4.7 |
| D6a_W7_Q0.998 | 1558 | 74 | 100 | 1.6/2.5/3.9 | 1.6/2.8/6.0 |
| D6a_W7_Q0.999 | 944 | 79 | 100 | 1.8/2.8/4.3 | 1.8/3.2/6.4 |
| D6b_W7_Q0.995 | 2877 | 56 | 100 | 1.2/1.8/3.0 | 1.2/1.8/3.9 |
| D6b_W7_Q0.998 | 1370 | 69 | 100 | 1.5/2.2/3.4 | 1.5/2.4/5.0 |
| D6b_W7_Q0.999 | 826 | 75 | 100 | 1.6/2.5/3.8 | 1.7/2.8/6.0 |
| D5_W14_p5 | 1908 | 44 | 100 | 1.5/2.3/3.6 | 0.5/1.1/3.2 |
| D5b_W14_p5 | 1651 | 46 | 100 | 1.4/2.2/3.6 | 0.5/1.2/3.3 |
| D5_W14_p2 | 634 | 54 | 100 | 2.1/2.9/4.3 | 0.7/1.4/4.4 |
| D5b_W14_p2 | 651 | 53 | 100 | 1.8/2.7/4.2 | 0.7/1.4/4.1 |
| D6a_W14_Q0.995 | 2605 | 65 | 100 | 1.3/2.0/3.4 | 1.2/2.1/4.6 |
| D6a_W14_Q0.998 | 1281 | 75 | 100 | 1.5/2.4/3.9 | 1.4/2.8/5.6 |
| D6a_W14_Q0.999 | 730 | 84 | 100 | 1.7/2.8/4.6 | 1.7/3.3/6.7 |
| D6b_W14_Q0.995 | 2462 | 57 | 100 | 1.2/1.8/3.0 | 1.1/1.6/3.6 |
| D6b_W14_Q0.998 | 1154 | 69 | 100 | 1.3/2.1/3.5 | 1.3/2.3/4.4 |
| D6b_W14_Q0.999 | 686 | 77 | 100 | 1.6/2.4/3.8 | 1.5/2.8/5.4 |

## Universe / tap xep hang (2022+): {"W7": {"U_min": 66, "U_med": 127.0, "elig_min": 0, "elig_med": 126.0, "hours_elig_lt40": 131, "hours_elig_lt20": 131, "eligb_min": 0, "eligb_med": 77.0, "hours_eligb_lt40": 1152, "by_year_elig_med": {"2022": 103.0, "2023": 112.0, "2024": 150.5, "2025": 159.0}}, "W14": {"U_min": 66, "U_med": 127.0, "elig_min": 0, "elig_med": 127.0, "hours_elig_lt40": 265, "hours_elig_lt20": 265, "eligb_min": 0, "eligb_med": 78.0, "hours_eligb_lt40": 1382, "by_year_elig_med": {"2022": 102.0, "2023": 113.0, "2024": 150.5, "2025": 158.0}}}

## Hoi quy ung vien vs cand_b1: {"W7_E0_2.5": {"n_mine": 4792, "n_ref": 4792, "identical_kc_order": true, "max_abs_s_diff": 3.843637408351697e-09}, "W7_E0_3.0": {"n_mine": 1965, "n_ref": 1965, "identical_kc_order": true, "max_abs_s_diff": 3.843637408351697e-09}, "W7_E0_3.5": {"n_mine": 838, "n_ref": 838, "identical_kc_order": true, "max_abs_s_diff": 4.220197524773539e-10}}

## LOI NGUON (errata - KHONG sua code goc)
- File: /home/ubuntu/claude_master/w3/levz/code/levz.py (md5 9f16404194de5fa510981d0ffa6d6833), ham fund_z (dong 147-172).
  Dong 158: `c = float(r8.mean())` - hang so can giua (centering) = trung binh r8 cua TOAN BO chuoi funding cua coin (ca tuong lai, toi 2025-12);
  dong 159-167: y = r8 - c, cumsum S1/S2, var = (s2 - s1^2/n)/(n-1), sd = sqrt(max(var,0)).
- Co che: gia tri dung (mean, sd cua cua so qua khu) khong phu thuoc c ve mat toan hoc, nhung SAI SO LAM TRON thi co: c doi khi du lieu tuong lai doi
  => cac so cuoi cua mean / sd tai gio t doi theo du lieu sau t (look-ahead muc lam tron). Hai he qua: (1) cua so funding hang so (vd ghim 0,01 %)
  co sd = 0 dung ra lai thanh sd ~1e-10..1e-9 duong; (2) z = (f-mean)/max(sd, san) lech nho.
- Do lon (so voi tinh lai bang so nguyen chinh xac, rate tren luoi 1e-8): xem bang 'srcbug' duoi day. Voi san co dinh 5e-5 (D0/D1, sig.py, cand_b1)
  sai lech z <= ~1e-7, KHONG doi trang thai nao (D0 tai lap 100 %, cand_b1 W7_E0 tai lap). Voi san thich nghi (D2+, san co the ~1e-9)
  sai so bi khuech dai: lan chay dau kiem nhan qua thay 167 o trang thai thay doi khi chi nhieu du lieu SAU t. Da sua trong ban dem nay (fund_parts so nguyen).
- Khuyen nghi errata: moi bien the dung san sd nho / thich nghi phai dung tinh toan chinh xac hoac c nhan qua (vd c = r8 dau tien); D0 hien tai khong bi anh huong.

srcbug: {"W7": {"max_abs_sd_diff": 8.562344941864339e-09, "n_frozen_sd_pos_exact_zero": 783338, "max_frozen_sd_when_exact_zero": 8.562344941864339e-09, "max_abs_z_diff": 3.177588041580748e-07, "n_ok_hours": 9555315}, "W14": {"max_abs_sd_diff": 3.985003931300988e-09, "n_frozen_sd_pos_exact_zero": 465678, "max_frozen_sd_when_exact_zero": 3.985003931300988e-09, "max_abs_z_diff": 1.1388510756660253e-07, "n_ok_hours": 9477825}}
