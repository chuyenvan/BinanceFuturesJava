# CHOICES_B3 - lua chon cai dat ma PREREG_LEVZ_B3 (30a8c413) khong noi ro (DEV, 2026-11-26) - cho A1 / MASTER soat
1. Pool: B0 sim.candidates (E0, W7) voi pxok = has1m cua B1 (work/hourly.npz) - giong het paths.cand() cua B1, chi doi z_min = 1,5.
   E0 = MOI gio o trang thai LEV (khong cooldown trong bo sinh; cooldown 72 h nam o port.py). Hoi quy z>=2,5/3,0/3,5: TRUNG 100 % (k, c, s).
2. Dot: lien ket don theo coin (ung vien ke tiep cung coin cach < 24 h => cung dot; >= 24 h => dot moi). Trong so = 1 / kich thuoc dot
   tinh tren TOAN pool (truoc purge). Dot "thuoc nam" = nam cua ung vien dau tien (bao cao); C0 dem so dot DISTINCT co >= 1 ung vien
   trong tap train sau purge / trong nam train gan nhat sau purge.
3. exit_Y, Y = 2025: "loi nhuan cac fold < Y" = F1_ret + F2_ret (tong, moi fold doc lap tu 10 000). Ban kep lai (1+F1)(1+F2)-1 cho CUNG
   exit (da kiem, ghi trong out/exitsel_b3.json). Y = 2024: chi F1_ret (F1 = 2022-01-01..2024-01-01).
4. exit_2024 co 2 bo hoa diem (SL 0,5 / arm 3 % / gap 2 %, H = 336 va H = 720) => luat hoa chon H ngan hon = 336.
5. exit_2023: KHONG tinh duoc dung luat (grid_b1 khong co fold rieng 2022). Khong tu che. C0_2023 chi tinh tham khao voi H = 720.
6. Tap train bat dau 2022-01-01 (nhu fold F1 cua B1); ung vien 2021-12 (16 ung vien / 1 dot) khong vao train.
7. Purge: bo ung vien train co k > k0(Y) - H(exit_Y) - 24 (k = gio vao, don vi gio) - dung muc 3.
## Sau ERRATA1 (308cd1fc)
8. Bang thoat chi luu 2 bo: exit_2024 (xi 170, H 336) va exit_2025 (xi 72, H 24); engine B1 van tinh du 195 bo ben trong. Mang gio
   (mk, hm, fh, fc) cat con 337 cot (= H max + 1; port.py khong doc qua gio H). work/labels_b3.npz 315 MB. Kiem trung tuyet doi voi
   exits.npz cua B1 tren 7 936 ung vien trung + tinh lai 300 ung vien ngau nhien.
9. Nhan = (1 - xr) - 0,07 % - xr x 0,07 % + funding (= port._net / N), khong cat, khong bien doi. 20 / 8 ung vien cuoi 2025 thoat 'eod'.
10. Dac trung px (lr, rv, rng, dhi/dlo, qv) lay tu px_1h dong k = nen gio KET THUC tai T_k (test: 500/500 khop close 1m phut T_k - 1).
    Cua so truot (std, tong qv, max/min) can >= 80 % gio co du lieu, khong thi NaN. rv = std (ddof 1) loi suat log gio.
11. liqrank = phan vi (hang trung binh, (r) / (n - 1)) cua tong qv 168 h giua cac coin trong U tai k co du >= 80 % gio.
12. "Trang thai LEV" cho levrun / frac_lev = U & z_oi >= 2,5 & z_f >= 2,5 & f > 0,01 % (dinh nghia LEV7 cua B2). levrun = so gio lien tuc
    toi va gom k (0 neu k khong LEV). frac_pool = U & z >= 1,5 & f > 0,01 % (khong doi has1m) / #U. ncand_hour = so ung vien pool tai k
    (gom chinh no). ncand7d = so ung vien pool cung coin trong [k - 168, k - 1].
13. Tuoi niem yet = AGE cua B2 mkt.npz (so ngay tu dong d1 dau tien; d1 bat dau 2021-01-01 => can duoi cho 2022), tran 720; -1 => NaN.
14. doi24 / doi72 = chenh ln OI (X tier-1, doc tai tsr <= h - 10 phut). df24 = f(k) - f(k - 24) (f r8 cua B0).
15. EW3/7/14, BTC7/20 tinh lai bang ham B2 mkt.ewr / btcdev tren CC (hr clast) - trung 100 % mkt.npz. btcvol7 = std loi suat log gio
    BTC (px) 168 h. Khong bo dac trung nao (34 dac trung, NaN <= 3,3 %).
16. M2: hang phan vi theo phan phoi train (trung binh searchsorted trai/phai) ; NaN -> 0,5. Ridge co trong so dot.
17. LightGBM: deterministic=True, force_row_wise, n_jobs=4 (de tat dinh); cac tham so khac dung muc 5.
18. Nguong T20/T10 = phan vi KHONG trong so cua diem OOF (trung binh 10 seed) tren tap train; T0 = diem > 0 (T20/T10 dung >=).
19. OOF GroupKFold: khong purge giua cac quy trong OOF (prereg khong yeu cau) - ghi de A1 soat.
20. Mot-seed (P6/Q6): moi seed tu OOF rieng -> nguong rieng -> model cuoi rieng; bien the T20 K5.
21. BL_S20: nguong = phan vi 80 % cua s tren tap train (da purge); BL_Z30 = pool & s >= 3,0 (= cand_b1 W7_E0_3.0); ca hai K5.
22. RAND: giu moi ung vien nam Y voi xac suat p (Bernoulli), diem ngau nhien U(0,1); rng = default_rng([20261126, Y, r]); p_value =
    ti le luot co ret >= ret CHINH (ERRATA1 Q3: chi nam 2025).
23. Q5/P5: bo ceil(5 %) lenh co net ($) lon nhat cua CHINH, tong net con lai > 0.
24. IC co trong so: hang trung binh thuong, roi Pearson co trong so dot. CI95 = bootstrap 1 000 lan theo dot. Hoan vi = giam IC (M1 du
    10 seed) khi xao 1 cot tren nam kiem.
25. WFO 2024 (mo ta): tap train = 2022-01-01 .. purge (2022 + 2023), exit_2024.
26. CV (ERRATA1 B): dai purge 2 dau [dau quy - H - 24 h, cuoi quy + H + 24 h], cuoi quy = gio cuoi cung cua quy; train = 2022-01-01 ..
    2025-12-31 ngoai quy va ngoai dai. C2: nguong = phan vi 80 % OOF tren ung vien 2023-01-01 .. 2025-12-31 22:00 (vao lenh duoc);
    BL_S20 cua C2 = phan vi 80 % cua s tren cung khoang; danh muc lien tuc mot lan tu 10 000; pnl nam = metrics pnl_Y cua B0.
27. Chay that bi chan: wfo_b3 / cv_b3 chi chay voi `--real I_HAVE_A1_PASS`.
## Sau A1_B3_CODE (PASS-WITH-MINOR)
28. GroupKFold(5) theo quy (sklearn, khong xao) - GIU NGUYEN thuat toan (prereg chi noi "GroupKFold 5 phan theo QUY"); kich thuoc phan
    RAT LECH (chi la so ung vien, khong co nhan):
    Y=2025: 9 193 (2024Q1) | 6 299 (2024Q4) | 4 530 (2023Q4) | 2 678 (2024Q2) | 2 594 (2022Q1-Q4, 2023Q1-Q3, 2024Q3).
    Y=2024 (mo ta): 2 612 (2023Q4) | 1 238 (2023Q1) | 869 (2023Q2) | 122 (2022Q3-Q4) | 127 (2022Q1-Q2, 2023Q3).
    wfo_b3 ghi kich thuoc phan vao json (oof_folds), report_b3 in ra.
29. Tuoi niem yet bi chan duoi cho coin co tu truoc 2021-01-01 (chi anh huong 2022) - giu nguyen (A1 NHO-5).
