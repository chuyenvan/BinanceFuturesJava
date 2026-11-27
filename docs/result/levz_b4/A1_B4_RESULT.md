# A1_B4_RESULT - kiem toan KET QUA B4 (DCA short LEVZ) - 2026-11-27
Phan quyet: PASS-CO-LUU-Y. So report_b4 tai lap doc lap DUNG TUYET DOI; ket luan "KHONG HON KHONG-DCA" ca 4 kieu dung luat A6 + E1.
LUU Y LON: dong NONE (+5,5 % / +18,0 %) KHONG phai bang chung moi - la tap con hep cua luoi B1/T1 da biet truoc.

1. sha256 PASS: 7 file code = muc BO SUNG E1 cua A1_B4_CODE.md; grid 1823b814, select 66c7d96f, report.json 5d6f5801, report.md ca8c6500;
   540 dong, 540 cfg_id, 108 / kieu.
2. Tai lap (code rieng, chi doc grid_b4.parquet, rule + plateau viet lai): lech lon nhat so voi report_b4.json = 0 (frac_pos F1-F3,
   top-1, trung vi top-20, ca 5 kieu x 2 nam). So cau hinh hop le (n>=30, ret>0, ddw<=30 %) 2024/2025: NONE 90/43, D1_5 81/26,
   D1_10 54/26, D2_5 60/24, D2_10 67/40 -> top-20 luon du 20.
3. NONE: 90/108 cau hinh trung tung o voi B1 (72 trailing) + T1 STATE (18, H168), lech ret/n/ddw moi fold = 0; 18 STATE H72 khong co ban
   doi chieu. Universe B1 W7E0 day du: top-20 2024 -23,0 % / 2025 +10,2 %. CHI cat SL{15,30} x H{72,168} (468 cfg): -4,2 % / +15,4 %.
   Chon cap trailing 5/3 + 10/5 trong 78 cap co the: hang 18/78 (2024) va 19/78 (2025); trung vi 78 cap -0,9 % / +11,5 %.
   Tach: NONE trailing (72) +4,7 % / +13,6 %; NONE STATE (36) -0,5 % / +37,1 % (2025 chi 15 hop le). Top-20 NONE 2024: 13 trailing + 7 STATE;
   2025: 16 trailing + 4 STATE. Ngoai ra top-1 NONE truot V-d ca hai nam (bo 5 % lenh loi nhat: -822 / -719 USD).
   => So tot len do LUOI HEP chon sau khi da thay B1/T1 (bo SL 50 %, H 24/336/720), khong phai loi code. KHONG duoc noi "KHONG DCA voi luoi
   nay co lai ca hai nam" nhu ket qua OOS.
4. V (quy uoc report_b4.to_md: 'x' = DAT, '.' = TRUOT). Tinh lai = report. D1_5/D1_10/D2_5: chi V-e dat. D2_10: V-a,V-c,V-e dat.
   V-b truot ca 4, ca 2 nam: top-20 DCA 2024 -2,0 / -4,7 / -8,5 / +0,06 % vs NONE +5,5 %; 2025 +9,4 / +13,6 / +5,2 / +7,2 % vs +18,0 %.
   V-c: F2 30 / 49 / 31 % (D2_10 56/62/65 dat). V-d: 2024 am o ca 4 (-2120 / -3107 / -1591 / -618 USD). Nhanh E1 KHONG kich hoat (NONE cham ca 2 nam).
5. V-e don vi = % NGAN SACH CHO (min(worst MTM, ret lenh)). top-1 s: D1_5 .15/.30, D1_10 .15/.30, D2_5 .30/.30, D2_10 .30/.15; tat ca <= 1,5 s.
   NONE top-1 s=.15: -16,8 / -21,5 % (< 22,5 %). Cap doi worst_ret F2/F3: DCA KHONG te hon (trung vi chenh +0,2..+1,6 diem).
6. Cap doi 108 cap (cung z,K,SL,thoat,H): ti le DCA > NONE F1/F2/F3: D1_5 17/29/6 %, D1_10 14/43/7 %, D2_5 10/40/5 %, D2_10 26/47/7 %;
   trung vi chenh F3 -9,7 / -9,8 / -11,4 / -13,5 diem; DEV -13..-18 diem [in-sample]. DCA thua NONE gan nhu moi cap -> ket luan ben vung,
   khong phu thuoc luoi NONE.
7. Hop le PASS: 0 NaN; acct <= 1,5e-11; exits: lenh tre nhat ket thuc EOD dung phut cuoi 2025 (70 dong rt=EOD), khong du lieu >= 2026;
   F2/F3 pnl = eq_end-1e4. EOD (E2) can tren <= 0,03 % equity/fold << bien V-b (>= 4 diem) -> khong dao.
8. Duoc noi: "DCA (4 kieu) KHONG HON KHONG-DCA theo luat; cap doi DCA thua o ~93-95 % cap F3; DCA khong lam lo te nhat xau hon".
   KHONG duoc noi: NONE +5,5/+18 % la loi suat ky vong/OOS; DEV tv; "NONE co lai ca 2 nam"; "D2_10 co cai thien".
