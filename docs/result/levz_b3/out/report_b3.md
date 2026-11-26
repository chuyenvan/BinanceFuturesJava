# REPORT_B3 (real) - PREREG_LEVZ_B3 30a8c413 + ERRATA1 308cd1fc

**Ket luan theo ERRATA1 E2: B3 KHONG DAT**

- P1..P8 (2 nam) cua prereg goc: KHONG THE DAT (C0 2024 khong dat, ERRATA1 E1) - khong cham.
- Y = 2023: khong lam (khong du mau, exit_2023 khong tinh duoc dung luat).
- So phep thu: 9 bien the x 2 model + 3 doi chung = 21 (+ 10 model mot-seed, + CV C1..C3).

## Ung vien, dot, C0, exit_Y (prereg muc 2, 3, 9)

| nam | ung vien | dot cham nam | dot bat dau trong nam |
|---|---|---|---|
| 2021 | 16 | 1 | 1 |
| 2022 | 200 | 25 | 25 |
| 2023 | 6686 | 644 | 644 |
| 2024 | 18431 | 1632 | 1632 |
| 2025 | 3531 | 429 | 428 |
- tong: 28864 ung vien, 2730 dot
- C0 Y=2023: H=720, dot train=25 (can >= 600), dot nam 2022=25 (can >= 300) => KHONG DAT exit_2023 khong tinh duoc dung luat; C0 tinh voi H = 720 (purge lon nhat) chi de tham khao
- C0 Y=2024: H=336, dot train=500 (can >= 600), dot nam 2023=475 (can >= 300) => KHONG DAT 
- C0 Y=2025: H=24, dot train=2297 (can >= 600), dot nam 2024=1628 (can >= 300) => DAT 
- exit_2024: xi=170 SL=0.5 H=336 arm=0.03 gap=0.02 diem=0.2419 (cot ['F1_ret'], sum, W==7 & E==E0 (1755); hoa 2)
- exit_2025: xi=72 SL=0.3 H=24 arm=0.07 gap=0.02 diem=0.2737 (cot ['F1_ret', 'F2_ret'], sum, W==7 & E==E0 (1755); hoa 1)
- exit_2023: khong tinh duoc exit_2023 dung luat: grid_b1 khong co fold rieng < 2023 (chi DEV/F1/F2/F3); de MASTER quyet

## (A) WFO 2025 - CHINH THUC (khong nhin truoc)

| tieu chi | dat |
|---|---|
| Q1 | False |
| Q2 | False |
| Q3 | False |
| Q4 | True |
| Q5 | False |
| Q6 | False |
| Q7 | False |
| Q8 | False |

### WFO 2025  (exit H = 24, train n = 25294, test n = 3531, C0 = {'n_train_dots': 2297, 'n_lastyear_dots': 1628, 'C0': True})
| bien the | ret | n lenh | maxDD xau nhat | n chon | nhan |
|---|---|---|---|---|---|
| M1_T20_K3 | -0.5240 | 210 | 0.5640 | 1306 |  |
| M1_T20_K5 | -0.3256 | 220 | 0.3615 | 1306 |  |
| M1_T20_K10 | -0.1562 | 228 | 0.1797 | 1306 |  |
| M1_T10_K3 | -0.2488 | 122 | 0.3503 | 599 |  |
| M1_T10_K5 | -0.0551 | 129 | 0.1658 | 599 |  |
| M1_T10_K10 | -0.0154 | 133 | 0.0782 | 599 |  |
| M1_T0_K3 | -0.5309 | 342 | 0.6230 | 3221 |  |
| M1_T0_K5 | -0.3024 | 361 | 0.4058 | 3221 |  |
| M1_T0_K10 | -0.1179 | 376 | 0.1881 | 3221 |  |
| M2_T20_K3 | -0.5231 | 226 | 0.6313 | 1388 |  |
| M2_T20_K5 | -0.3207 | 231 | 0.4185 | 1388 |  |
| M2_T20_K10 | -0.1687 | 231 | 0.2311 | 1388 |  |
| M2_T10_K3 | -0.5277 | 184 | 0.6132 | 946 |  |
| M2_T10_K5 | -0.2950 | 186 | 0.4027 | 946 |  |
| M2_T10_K10 | -0.1536 | 186 | 0.2211 | 946 |  |
| M2_T0_K3 | -0.4305 | 346 | 0.5739 | 3246 |  |
| M2_T0_K5 | -0.2094 | 363 | 0.3505 | 3246 |  |
| M2_T0_K10 | -0.0547 | 379 | 0.1456 | 3246 |  |
| BL_S20 | -0.0507 | 185 | 0.2420 | 1081 |  |
| BL_Z30 | 0.2049 | 87 | 0.0924 | 450 |  |
- GroupKFold OOF (5 phan theo quy): n=9193 q=[216], n=6299 q=[219], n=4530 q=[215], n=2678 q=[217], n=2594 q=[208, 209, 210, 211, 212, 213, 214, 218]
- RAND 500 luot: p = 0.9700, trung vi ret = -0.1205 
- mot-seed (T20 K5): ret = -0.3111, -0.3670, -0.3063, -0.3239, -0.2607, -0.3966, -0.4463, -0.2493, -0.4975, -0.3934 
- CHINH: tong net = -3256.03, bo 11 lenh loi nhat => -4889.68 
- M1 IC test = -0.0708 (CI95 theo dot [-0.14323987103208202, -0.0012536897161848283]) ; IC OOF train = -0.0457 [in-sample]; IC train = 0.5177 [in-sample]
- M2 IC test = 0.0419 (CI95 theo dot [-0.025568111651674327, 0.11672198637229572]) ; IC OOF train = -0.0682 [in-sample]; IC train = 0.1865 [in-sample]
- IC cua s (doi chung) = 0.0495 
- 10 nhom diem M1 (n / TB nhan / TB nhan co trong so): 0: 354 / 0.0277 / 0.0473; 1: 353 / 0.0131 / 0.0156; 2: 353 / 0.0091 / 0.0158; 3: 353 / 0.0080 / 0.0197; 4: 353 / 0.0029 / 0.0076; 5: 353 / -0.0099 / -0.0183; 6: 353 / -0.0098 / 0.0049; 7: 353 / -0.0169 / 0.0065; 8: 353 / -0.0057 / 0.0088; 9: 353 / 0.0022 / 0.0168 
- M1 gain top10: btc20=4.213, btcvol7=3.924, ew3=2.734, ew14=2.462, btc7=2.359, ew7=2.194, f=1.645, frac_pool=1.111, rv168=0.9772, lr4=0.939
- 10 nhom diem M2 (n / TB nhan / TB nhan co trong so): 0: 354 / 0.0161 / 0.0195; 1: 353 / 0.0073 / 0.0090; 2: 353 / 0.0029 / 0.0145; 3: 353 / 0.0154 / 0.0319; 4: 353 / 0.0108 / 0.0163; 5: 353 / 0.0004 / 0.0026; 6: 353 / 0.0074 / 0.0085; 7: 353 / -0.0080 / 0.0059; 8: 353 / -0.0109 / 0.0032; 9: 353 / -0.0207 / 0.0131 
- M2 |he so| top10: btc20=0.02934, ew14=0.02498, dlo168=0.02172, btcvol7=0.0198, lr72=0.01618, f=0.01504, lr4=0.01463, dhi168=0.0142, rv24=0.01171, liqrank=0.01041
- 8 bien the lan can M1: M1_T20_K3=-0.5240, M1_T20_K10=-0.1562, M1_T10_K3=-0.2488, M1_T10_K5=-0.0551, M1_T10_K10=-0.0154, M1_T0_K3=-0.5309, M1_T0_K5=-0.3024, M1_T0_K10=-0.1179 
- hoan vi tren nam kiem (giam IC) top10: frac_pool=0.0269, lr24=0.0246, f=0.0091, dlo168=0.0076, liqrank=0.0053, ncand_hour=0.0023, z_r=0.0021, ew14=0.0015, lr1=0.0014, qvratio=0.0012 
- theo thang (CHINH): 2025-01:71, 2025-02:-589, 2025-03:-110, 2025-04:-90, 2025-05:-222, 2025-06:274, 2025-07:-546, 2025-08:-647, 2025-09:-736, 2025-10:-539, 2025-11:-304, 2025-12:182 
- lenh te nhat (net): -418.0, -385.7, -373.5, -337.3, -332.8, -327.3, -322.5, -321.8, -310.1, -310.0 
- trung coin: {'n_coins': 96, 'max_trades_one_coin': 15, 'n_coins_ge2': 45} 

## (B) CV theo quy [CV - co nhin truoc]

| quy | n val | n train | IC (nhan exit_2025) |
|---|---|---|---|
| 2023Q1 | 1238 | 27610 | 0.0472 [CV - co nhin truoc] |
| 2023Q2 | 869 | 27979 | 0.3087 [CV - co nhin truoc] |
| 2023Q3 | 49 | 28799 | -0.6301 [CV - co nhin truoc] |
| 2023Q4 | 4530 | 24114 | -0.1529 [CV - co nhin truoc] |
| 2024Q1 | 9193 | 19452 | 0.0100 [CV - co nhin truoc] |
| 2024Q2 | 2678 | 25148 | -0.2003 [CV - co nhin truoc] |
| 2024Q3 | 238 | 28610 | 0.1547 [CV - co nhin truoc] |
| 2024Q4 | 6322 | 22495 | 0.1367 [CV - co nhin truoc] |
| 2025Q1 | 631 | 28189 | -0.1492 [CV - co nhin truoc] |
| 2025Q2 | 508 | 28337 | 0.0394 [CV - co nhin truoc] |
| 2025Q3 | 1255 | 27568 | 0.1208 [CV - co nhin truoc] |
| 2025Q4 | 1137 | 27699 | -0.1408 [CV - co nhin truoc] |
- C1 (IC > 0 o >= 9/12 quy): False (7/12) [CV - co nhin truoc]
- C2: pnl 2023/2024/2025 = -1350.5, 608.8, -2449.7; ret = -0.3191 vs BL_S20 0.3357 => False [CV - co nhin truoc]
- C3 (nhan exit_2024): ret 3 nam = 0.0972 => True [CV - co nhin truoc]

## WFO 2024 [DUOI NGUONG MAU - CHI MO TA]

### WFO 2024 - DUOI NGUONG MAU - CHI MO TA [DUOI NGUONG MAU - CHI MO TA] (exit H = 336, train n = 4968, test n = 18430, C0 = {'n_train_dots': 500, 'n_lastyear_dots': 475, 'C0': False})
| bien the | ret | n lenh | maxDD xau nhat | n chon | nhan |
|---|---|---|---|---|---|
| M1_T20_K3 | -0.5620 | 80 | 0.5670 | 1000 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T20_K5 | -0.5079 | 130 | 0.5284 | 1000 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T20_K10 | -0.2894 | 193 | 0.3681 | 1000 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T10_K3 | -0.3989 | 62 | 0.4479 | 345 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T10_K5 | -0.4587 | 84 | 0.4619 | 345 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T10_K10 | -0.3222 | 128 | 0.3231 | 345 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T0_K3 | -0.0654 | 199 | 0.3382 | 12816 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T0_K5 | -0.1433 | 294 | 0.4066 | 12816 | [DUOI NGUONG MAU - CHI MO TA] |
| M1_T0_K10 | -0.2688 | 466 | 0.4440 | 12816 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T20_K3 | -0.4968 | 124 | 0.5806 | 3375 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T20_K5 | -0.4267 | 194 | 0.5306 | 3375 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T20_K10 | -0.2038 | 319 | 0.3855 | 3375 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T10_K3 | -0.4822 | 97 | 0.5443 | 1392 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T10_K5 | -0.3590 | 144 | 0.4690 | 1392 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T10_K10 | -0.1519 | 259 | 0.3411 | 1392 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T0_K3 | -0.1493 | 196 | 0.3962 | 17827 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T0_K5 | -0.1233 | 292 | 0.3950 | 17827 | [DUOI NGUONG MAU - CHI MO TA] |
| M2_T0_K10 | -0.0808 | 476 | 0.3577 | 17827 | [DUOI NGUONG MAU - CHI MO TA] |
| BL_S20 | -0.4168 | 192 | 0.4959 | 3194 | [DUOI NGUONG MAU - CHI MO TA] |
| BL_Z30 | -0.2708 | 156 | 0.3679 | 1055 | [DUOI NGUONG MAU - CHI MO TA] |
- GroupKFold OOF (5 phan theo quy): n=2612 q=[215], n=1238 q=[212], n=869 q=[213], n=122 q=[210, 211], n=127 q=[208, 209, 214]
- RAND 500 luot: p = 0.9980, trung vi ret = -0.0671 [DUOI NGUONG MAU - CHI MO TA]
- mot-seed (T20 K5): ret = -0.3434, -0.3420, -0.3410, -0.4062, -0.4159, -0.4357, -0.3972, -0.4123, -0.5630, -0.3743 [DUOI NGUONG MAU - CHI MO TA]
- CHINH: tong net = -5078.72, bo 7 lenh loi nhat => -5536.22 [DUOI NGUONG MAU - CHI MO TA]
- M1 IC test = -0.0805 (CI95 theo dot [-0.11883261469246569, -0.04598584893231017]) [DUOI NGUONG MAU - CHI MO TA]; IC OOF train = -0.0525 [in-sample]; IC train = 0.4457 [in-sample]
- M2 IC test = -0.0533 (CI95 theo dot [-0.09045542070036534, -0.01727632496312215]) [DUOI NGUONG MAU - CHI MO TA]; IC OOF train = -0.1074 [in-sample]; IC train = 0.1200 [in-sample]
- IC cua s (doi chung) = -0.0566 [DUOI NGUONG MAU - CHI MO TA]
- 10 nhom diem M1 (n / TB nhan / TB nhan co trong so): 0: 1843 / 0.0269 / 0.0366; 1: 1843 / 0.0154 / 0.0238; 2: 1843 / 0.0195 / 0.0223; 3: 1843 / 0.0175 / 0.0194; 4: 1843 / 0.0118 / 0.0184; 5: 1843 / 0.0101 / 0.0148; 6: 1843 / 0.0029 / 0.0116; 7: 1843 / -0.0083 / 0.0063; 8: 1843 / -0.0162 / -0.0081; 9: 1843 / -0.0247 / -0.0090 [DUOI NGUONG MAU - CHI MO TA]
- M1 gain top10: rv168=1.346, btcvol7=1.153, rv24=1.09, liqrank=1.04, btc20=0.9742, btc7=0.9046, lr72=0.6845, lr168=0.5982, f=0.5837, lqv24=0.5287
- 10 nhom diem M2 (n / TB nhan / TB nhan co trong so): 0: 1843 / 0.0102 / 0.0234; 1: 1843 / 0.0046 / 0.0202; 2: 1843 / 0.0079 / 0.0187; 3: 1843 / 0.0089 / 0.0128; 4: 1843 / 0.0010 / 0.0014; 5: 1843 / 0.0039 / 0.0084; 6: 1843 / 0.0107 / 0.0170; 7: 1843 / 0.0021 / 0.0037; 8: 1843 / 0.0040 / 0.0099; 9: 1843 / 0.0014 / 0.0086 [DUOI NGUONG MAU - CHI MO TA]
- M2 |he so| top10: btc20=0.02043, btc7=0.01886, lr72=0.01796, lr24=0.01354, rv168=0.01256, dlo168=0.01204, levrun=0.01168, ew7=0.01136, ew14=0.01061, doi24=0.0092
- 8 bien the lan can M1: M1_T20_K3=-0.5620, M1_T20_K10=-0.2894, M1_T10_K3=-0.3989, M1_T10_K5=-0.4587, M1_T10_K10=-0.3222, M1_T0_K3=-0.0654, M1_T0_K5=-0.1433, M1_T0_K10=-0.2688 [DUOI NGUONG MAU - CHI MO TA]
- hoan vi tren nam kiem (giam IC) top10: btc7=0.0097, ew3=0.0094, lr72=0.0075, qvratio=0.0041, lr4=0.0036, z_r=0.0032, lr1=0.0031, doi72=0.0025, zdiff=0.0022, rv24=0.0017 [DUOI NGUONG MAU - CHI MO TA]
- theo thang (CHINH): 2024-01:14, 2024-02:-2921, 2024-03:-108, 2024-04:128, 2024-05:522, 2024-06:192, 2024-08:14, 2024-09:28, 2024-10:15, 2024-11:-1950, 2024-12:-1012 [DUOI NGUONG MAU - CHI MO TA]
- lenh te nhat (net): -593.3, -561.4, -517.4, -512.8, -470.3, -465.1, -459.7, -459.5, -451.5, -442.1 [DUOI NGUONG MAU - CHI MO TA]
- trung coin: {'n_coins': 97, 'max_trades_one_coin': 4, 'n_coins_ge2': 24} [DUOI NGUONG MAU - CHI MO TA]
