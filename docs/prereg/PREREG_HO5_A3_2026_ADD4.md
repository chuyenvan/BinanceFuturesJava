# PREREG_HO5_A3_2026_ADD4 - ghi nhan HAU KIEM cac sua KY THUAT trong luot 5 (2026-11-21) - KHONG doi luat, KHONG doi cau hinh sim
Viet SAU khi co ket qua (hau kiem, khai bao ro). Mo seal: HOLDOUT_UNSEAL_2026_1121 (e9095a02), pham vi U1.
1. Tu kiem funding cua kernel (ADD2/ADD3) sai thiet ke: funding.bin DEV co 1 ban ghi dung tai SEAL (ffill 15' tu 23:45) nen khac khi co bins
   2026 -> 4 kernel v1 dung o tu kiem TRUOC sim (khong sinh so 2026). Thay bang tu kiem v2 chat hon: dung lai funding CHI tu bins DEV ->
   md5 == 50c4bc8d va 2 301 064 ban ghi truoc SEAL trung byte. Push lai cung ten kernel.
2. ho5_sim thieu nhanh pred cho seed A1 -> them A1_PRED (pred goc bundle 5dd6bb4c cho doan truoc 2026 + p15 2026).
3. Duong dan symbol map 863 cua a3_26 da mat -> tro sang ban 863 trong ho4p1-code (md5 9a3e40e9 trung manifest chain HO4).
4. score_l5 doc khoa cu (funding v1, profile_hash) -> sua cho doc khoa, khong doi tieu chi. SCORE_DEFS_L5.md (sha 03a93453) chot TRUOC khi co
   output 2026.
5. profile_hash doi (ef770e13 thay 0738cca9) CHI vi SIM_LOSER_TS_EXT_DAYS them 4 khoang TS_EXT 2026 (ho_flags.json) - dung prereg muc 1.
6. Lech quy trinh (khong anh huong so): dot push thu hai duoc push khi kernel thu moi qua tu kiem, chua COMPLETE (KAGGLE_RULES yeu cau doi).
Ket qua ap luat (nguyen van): E0 PASS (mean SigmaPnL OOS +17 195; 8/8 seed duong; 8 seed gan nhu MOT mau - lenh 2026 trung 93,6-100 %);
E0b bootstrap tuan CI80 [871 ; 34 365]; R1: ky vong PILOT = ROI OOS 10,95 % / 183 ngay (~23 %/nam), thay cho 37,72 %; R3 khong canh bao
(maxDD W -3,05 % MTM ngay). Van phai train lai truoc pilot (luat 3 PREREG_DIAG_NOTRADE_1117).
