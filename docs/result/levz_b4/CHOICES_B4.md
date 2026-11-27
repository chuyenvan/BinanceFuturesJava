# CHOICES_B4 (DEV, chua audit) - cac lua chon khi prereg PREREG_X3_1127 PHAN A mo ho
1. [MASTER CHAP NHAN] Thu tu trong mot phut: (1) khop limit leg them, (2) SL theo gia von MOI, (3) trailing, (4) STATE, (5) TIME, (6) MISS. Uu tien cung
   phut SL > TRAIL > STATE > TIME > MISS (B1 + T1). Khop truoc SL = bao thu (vi the lon hon khi gia di len).
2. Leg them khop khi close 1m >= L_l (1 - 1e-12) (MASTER 2026-11-27: SUA de close BANG dung muc thi khop nhu prereg ">=";
   truoc do 100 x (1 + 0,05 x 2) = 110,00000000000001 lam close 110,0 khong khop); gia khop = dung L_l, phi 0,07 %, khong truot.
   Test d tran 3 nay dung close 110,0 dung muc. Ve sinh tren du lieu that khong doi o 4 chu so. Nhieu leg co the khop cung phut (nhay gia). Leg chi khop o phut <= phut thoat.
3. Gia von = sum N / sum (N / L) (trung binh theo khoi luong). Trailing: muc arm = gia von hien hanh x (1 - a); da arm thi giu trang
   thai arm khi leg sau khop; day / gap nhu B1 (khong phu thuoc gia von); arm va thoat khong cung phut (B1). Thuc te leg khong the khop
   sau khi arm (gia <= gio von x (1 - a) < L).
4. Funding (quy uoc B1): moc h tra cho leg khop o phut f < 60 h - 1 va vi the con mo (60 h - 1 <= j); so tien / ngan sach =
   N (p0 / L) fh[h] (fh B1 = FR x close moc / p0).
5. Dua vao port.py B1 KHONG SUA: ngan sach cho = notional cua port (giu tron ca phan chua khop => von giu tron tu dong: slot chiem
   tron N tu luc vao, khong lenh khac dung duoc). xr_eff = sum_filled N X / L + N (n_add - nf) (1 - FEE) / (1 + FEE); fund_eff nhu #4
   => net port / N = loi suat DCA tren ngan sach CHINH XAC (test b, sai so <= 1e-12). Phi vao leg them nam trong xr_eff (port tinh
   phi vao FEE x N luc vao cho ca ngan sach; phan chenh hoan qua xr_eff luc thoat).
6. Mang theo gio (moi kieu DCA, khong phu thuoc cau hinh thoat vi port chi dung h < gio thoat): mkm[i] = N (n_add - so leg da khop)
   (1 - FEE) + sum N p[i] / L => MTM port (1 - mk - FEE) = MTM that ke ca phi leg; hm = max mkm trong cua so gio; mx, mxh tu mkm.
   n_add = 0 => dung bit-for-bit mang B1 (test a).
7. 'worst' (lo te nhat mot cho, V-e) = min(1 - FEE - max mkm[0..j], ret tren ngan sach); bo qua funding giua chung lenh.
8. Test (a): n_add = 0 x trailing (8 bo: SL 15/30 x H 72/168 x TR5_3/TR10_5) so voi B1 exits.npz (xi = common_b1.xidx); STATE chi co
   H 168 trong T1 (STATE_H = 168, 720) => kiem 2 bo (SL 15/30, H 168); STATE H 72 KHONG co bo trung trong T1 (kiem gian tiep qua test b).
9. [MASTER CHAP NHAN 2026-11-27; ky vong 'DCA te hon' la cau trong de giao viec, khong phai luat prereg] (test f): voi SL tinh tu GIA VON va leg chia deu ngan sach giu tron, squeeze mot chieu toi SL cho lo tren
   ngan sach ~ bang KHONG DCA (khi da khop het leg, lo = s nhu nhau; khac biet chi do truot / buoc gia). Test f vi vay kiem "DCA KHONG
   tot hon KHONG DCA qu? 0,1 % ngan sach" thay vi "te hon chat"; DCA te hon chat o chuoi "sap khong co nhip tang" (von leg chua khop
   nam yen). Pump roi sap (tat ca leg khop): moi kieu DCA > KHONG DCA.
10. Ung vien: hop W7_E0 z 2,5 / 3,0 / 3,5 cua cand_b1 = 4 792 dong (z 3,0 / 3,5 la tap con); bang thoat theo dong ucid; NONE dung mang gio B1.
11. Lang gieng (plateau select_b1.rule) TRONG cung kieu DCA: zmin, K, SL, H mot buoc; thoat TR5_3 <-> TR10_5; STATE khong co lang
    gieng thoat (bien phan loai). top-20 = 20 cau hinh HOP LE tot nhat theo score (nhu T1 / T2); top-1 = cau hinh dau qua du luat.
12. [MASTER BAC - xem ERRATA1 E1] V-a, V-b dung trung vi top-20 (valid). Kieu DCA khong cham duoc nam Y => V-a, V-b False.
    KHONG DCA khong cham duoc nam Y => moc V-b nam Y = 0 (V-b(Y) = trung vi top-20 DCA > 0); report in ro dong do + trung vi
    loi suat nam Y cua 108 cau hinh KHONG DCA (chi mo ta). NONE cham duoc => so top-20 voi top-20 nhu cu. Test i.
    V-d: chay lai top-1 tren fold thu, bo 5 % lenh LOI NHAT (lai lon nhat) van > 0. V-e: lo te nhat mot cho = min(worst trong
    bang thoat, ret lenh) tren cac lenh cua top-1 o fold thu, so voi 1,5 x s cua cau hinh do; khong co top-1 => False.
13. STATE H 72 n_add 0 (khong co bo T1): test b chay vong for tham chieu tren 300 lenh that x 2 SL = 600 phep so.
14. Du lieu GIA (fake_b4.py): 3 coin, 1 lenh / ~400-460 h moi coin (it lenh de lai kep khong lam vo dung sai so sach 1e-6 cua
    check_acct B0); 'pump' tang 11-14 % roi sap -12 %; 'rand' buoc ngau nhien khong troi. Test h KHONG do duoc do nhay /
    bao dong gia cua tieu chi (rand gan nhu khong co cfg hop le) - chi chung minh pipeline ra duoc 'DAT' (ERRATA1 E2).
