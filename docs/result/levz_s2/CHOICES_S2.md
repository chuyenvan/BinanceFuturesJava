# CHOICES_S2 - cac cho prereg PREREG_LEVZ_S2 (74ec941e) mo ho / phai dien giai (DEV, chua audit). MASTER quyet.
1. P6b = D6 Q 0,998 voi z kieu D1 (prereg "nhu tren" = nhu P6a), KHONG phai D6b (z kieu D2) cua sigcount. Kiem: P6b trung 100 % sigcount D6_W7_Q0.998.
2. "So coin xep hang duoc" (nguong < 40 cho P5 VA P5b) = so coin U co z_oi2, z_f2 huu han (fin2) - dung dinh nghia cua con so 131 gio
   trong prereg; voi P5b KHONG dung kich thuoc tap sau loc f >= trung vi (trung vi 77; 1 152 gio < 40). Ket qua: ca 131 gio bi bo deu co 0 coin
   xep hang => so ung vien P5 / P5b KHONG doi (4 277 / 4 267).
3. ep72 (so luong moi nam cho doi chung ngau nhien) = B0 rand.episode_starts (noi chuoi khi khoang cach <= 72 h, nhu B1 rand); bao kem
   ep72 kieu cooldown-tu-gio-dau (L.episodes) trong out/cand_s2.json (chenh 0-12 / nam).
4. select_b1.rule dung NGUYEN VEN (khong sua) voi dd_mode='folds'; df dua vao chi co cot tham so + cot cac fold train (assert). Vi luoi S2 khong
   co W/E/zmin, them cot hang W=7, E='E0', zmin=3.0 (gia tri thuoc select_b1.STD) va BO cac lang gieng doi W/E/zmin; lang gieng con lai
   (K, SL, H, arm, gap) dung select_b1.neighbours. "Gop cac nam train" = cach select_b1 gop F1+F2: diem = min qua cac fold train, hop le = moi
   fold train (n >= 30, ret > 0) va max maxDD-worst cac fold train <= 30 %. KHONG gop ledger nhieu nam thanh mot fold.
5. [THAY theo MASTER + ERRATA2 F1] Trung vi top-20 = trung vi loi suat nam Y cua <= 20 cau hinh dau tien qua DU luat (ke ca cao nguyen)
   = select_b1 'top20_rule'. Nam khong co cau hinh qua luat => 'khong cham duoc Y', KHONG tinh 0: tong WFO that = tong tren cac nam
   CHAM DUOC (scored_years). p_wfo: moi luot ngau nhien chi cong tren DUNG scored_years cua tap THAT; luot thieu bat ky nam nao trong do
   => KHONG >= that; tap that 0 nam cham => p_wfo NaN (S-c truot). Part rand luu top20 TUNG NAM + scored de tinh lai.
6. p_max "max qua luoi tren DEV nhu B1": B1 dung maximin F1..F3 (khong co o S2). Chon: max qua 585 cau hinh cua DEV_ret / max(DEV_maxdd_worst,
   1e-9) - in-sample, chi bao kem. Co the doi sang maximin Y22..Y25 neu MASTER muon.
7. Fold nam: k0 = gio 00:00 01/01, kl = 00:00 01/01 nam sau - 1 h (giong B1 run_all) => Y24 == F2, Y25 == F3 cua B1 (test a: 0 lech / 47 385 o).
8. check_acct: tai cai dung bat bien B0 grid.check_acct (tol 1e-6) cho ten fold S2 (DEV, Y22..Y25) vi ham goc co dinh ten DEV/F1/F2/F3.
9. Funding / z dung ban so nguyen chinh xac (sigcount) - khac fund_z goc <= 3,2e-7 tren z_f; REF van lay nguyen cand_b1 W7_E0_3.0.
10. [THAY] Kiem nhan qua: test c (3 moc ngau nhien, toan bo tien to) + test c2 (MASTER): 381 moc cat co chu dich, moi dinh nghia
    >= 100 gio DANG trong trang thai va >= 100 gio NGAY TRUOC khi vao; nhieu OI hang > T va funding ts > T - 1 phut; trang thai + s
    tai <= T khong doi: PASS (0 lech). Han che (A1): moc cat <= 2022-08; bu bang doi chieu doc lap toan bo 2022-2025 cua A1.

## Quyet dinh MASTER (2026-11-26)
- #1 DUNG; #2, #3, #4, #6 CHAP NHAN (#4 ghi trong REPORT_S2.md).
- #5 THAY: khong tinh 0 im lang. select_s2: wfo_sum_top20 = tong tren cac nam CHAM DUOC (scored_years, n_scored); rand_s2: luot
  ngau nhien khong cham duoc nam nao (NaN) tinh la KHONG >= that; that NaN => p_wfo NaN (S-c truot). S-a: 3 nam cham -> >= 2/3 > 0 va
  tong > 0; 2 nam -> ca 2 > 0; < 2 nam -> TRUOT (MASTER se dua vao ERRATA).
11. (MOI, cho MASTER) S-d / S-e tinh tren cac nam cham duoc; < 2 nam cham duoc -> TRUOT (nhat quan voi S-a). Ledger S-d = gop lenh
    top-1 cua cac nam cham duoc, bo ceil(5 %) lenh LAI NHAT, tong net con lai > 0.
12. rand_s2 --shard i/n: lay cac (tap, luot) co chi so thu tu % n == i; seed chi phu thuoc (tap, luot) => ket qua giong chay 1 tien trinh.
