# A1_LLV - kiem toan doc lap LLV (PREREG_X3_1127 phan C) - 2026-11-27
Phan quyet: PASS-CO-LUU-Y (code/so lieu dung; H2 "CO MANH MOI" chi dat sat nguong, mong, tap trung 2024).
Code tam (da xoa): a1.py/a2.py, rng 4242/777, 4000 luot perm.

1. Prereg: cum, ret=sum pnl/sum margin, k (T_k<ts), LEV24, nguong H1-H4, ngu phan vi (run,year), NHAT QUAN, mot phia, 5000 luot: KHOP.
   Nhom H1-H4 tai tao 100 % trung. Log 1 lan chay (FileHandler append, 6 dong), code mtime 12:36:42 < chay 12:36:49; khong thay bien the/doi nguong.
   Lech: hoan vi nhan DOC LAP tung seed trong thang -> pha cau truc trung lap giua seed -> p qua nho (xem 4a).
2. Nhan qua: 100 cum ngau nhien: gia vao leg dau khop close1m (<0,2 %) 99/100 voi UTC=start-7h (lech +7h: 6, -7h: 1, +-1h: 11/1).
   k tinh lai = agent 100/100; z_oi = sig_W7(sym,T_k) 100/100; tre 1..60 phut; OI raw tai T_k co tsr<=T_k-10min 100/100;
   roll_z_inputs dung shift(1) (trailing). Toan bo 12 745 cum: T_k<ts va ts-T_k<=1h. PASS.
3. H2 tai lap: n=1470 (21,8 %), chenh +0,971 pp; bang nam x seed khop (2024 +2,4..+3,1; 2023 sai dau 3/4; c0s7 2/4).
   p kieu agent (doc lap tung seed) 0,0002 (agent 0,0008). p hoan vi CHUNG (cung (sym,k) cung nhan o moi seed) = 0,0117 (nguong 0,0125; SE MC ~0,0017).
4a. Trung lap: ~91 % cum hop le cua 1 seed co cung (sym,k) o seed khac, ~60 % o ca 4 seed; 6 746 dong = 2 472 (sym,k) duy nhat.
   p tung seed: c0s42 0,030; c0s7 0,137; c0s123 0,059; c0s13 0,026 -> KHONG seed nao <=0,0125. Dedup theo (sym,k): +1,21 pp, p 0,002.
   NHAT QUAN dat nho c0s123 2022 = +0,03 pp (sat 0).
4b. Bo 2024: +0,15 pp, p chung 0,15. Theo nam gop: 2022 +0,54 / 2023 -0,27 / 2024 +2,69 / 2025 +0,56.
4c. Trung vi: +0,14 pp. Cat 1 % cuc tri: +0,57 pp. Muc thang: 24/39 thang duong, t=1,52. 5 ngay (2024-04-13, 2024-08-05, 2025-10-10, 2023-04-04, 2023-01-14) = 32 % tong ret nhom.
4d. Bi loai (ngoai universe) ret TB 3,7-4,3 % vs giu 3,5-3,9 %, trung vi ~ngang; chiem 44-47 % PnL DEV. Chieu thien lech voi H2 khong biet (khong co z_oi).
5. H1 -0,31 pp p 0,11 (chung 0,26) 0/4 seed; H3 +0,62 pp p 0,0002 (chung 0,0097), 2022-23 dung 8/8, 2024-25 sai 8/8 -> khong nhat quan dung luat;
   H4 +0,78 pp p 0,025 (chung 0,14). Ket luan KHONG CO MANH MOI dung.
6. Tong PnL cum = ledger = equity delta (4/4, < 1 USD); 3146/3228/3245/3126 cum, DEV 2580/2662/2678/2550; max te 2025-11-28. PASS.
7. Uoc tho: H2 giu nhom tot -40,5/-42,5/-41,0/-39,9 %; bo LEV24 -2,4/-2,3/-1,3/-1,0 %: dung so hoc.
   De xuat "tang size z_oi<=-1": bang chung chua du manh cho sim Java ngay; hieu ung nam o mean (trung vi +0,14 pp), dua vao vai ngay crash 2024.
