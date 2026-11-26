# CHOICES_B1 - lua chon cai dat LEVZ B1 (PREREG_LEVZ_B1 @54f40792) - ghi TRUOC khi chay luoi
Nguyen tac: prereg khong noi ro => chon cach BAT LOI hon (neu xac dinh duoc), khong thi giu quy uoc B0 (CHOICES2) + ghi lai.
Cho nao la doi luat => "CAN MASTER QUYET" (cuoi file): da cai mac dinh, MASTER chot truoc khi chay luoi.

## Du lieu / duong gia
1. Luu tru: MOT memmap theo coin work/close1m.npy (float32, 631 x 2 148 480 phut, 5,42 GB) thay vi file rieng moi (ung vien, gio);
   duong gia cua (c, k) = view close1m[c, 60k : 60k + 43 201]. Tuong duong ve noi dung, gon hon, va phuc vu ca ung vien ngau nhien (rand).
2. Phut j <-> nen 1m open_time H0 + j phut; gia = close nen do. Nen co close khong huu han / <= 0 => coi nhu thieu (dem: 0). Trung (sym, ts): giu
   dong cuoi (dem: 0). Sym ngoai danh sach B0 (sig_meta) bi bo. Reader: chi file 2021-12..2025-12, filter + assert ts < 2026-01-01.
3. Phut thieu: ffill gia cuoi (truoc nen dau tien: NaN). Gap = chuoi phut thieu SAU nen dau tien (gom ca doan sau khi huy niem yet).
4. Gia vao: close cua nen open_time = T_k (dung prereg). Ung vien can nen do TON TAI (has1m) => dung lai B0 candidates() voi pxok = has1m
   (B0 dung pxok = co nen store gio). Hau qua: tap ung vien B1 khac B0 chut it (xem x12.json cand_sets).
5. Funding: dung lai ma tran FR cua B0 (work/inputs.npz, da audit: tong rate cac ky lam tron ve moc gio).

## Engine thoat (exits.py)
6. Danh gia o phut i = 1..43 200 (phut 0 = phut vao). Time-stop: i = 60 H (nen open T_k + H gio). Thu tu trong phut: SL -> trailing -> time
   -> miss (phut thieu: gia ffill khong doi nen khong the kich SL/trailing moi).
7. SL: close >= p0 (1 + SL) (">=") -> close x 1,003. Trailing: kich hoat khi close <= p0 (1 - arm) ("<="); day = min close tu phut kich hoat
   (gom phut do); thoat o phut i > i_kich_hoat khi close >= day(i-1) x (1 + gap) -> close x 1,001. Time/miss/eod: close, khong truot.
8. Thieu lien tuc > 24 h (> 1 440 phut, tinh sau khi vao) => thoat o phut thieu thu 1 441 tai close cuoi ('miss', co flag). Time-stop roi vao
   phut thieu => thoat tai close cuoi, flag = 1 (tuong tu 'time_sub' B0).
9. Duong gia cat tai 2025-12-31 23:59: su kien sau do khong ton tai; khong co su kien => 'eod' o phut cuoi (danh muc luon dong cuong buc
   cuoi fold truoc moc nay).
10. Funding: ky tai moc T_{k+h} (h >= 1) duoc tinh neu 60 h - 1 <= j (nen thoat dong luc >= moc; quy uoc B0 CHOICES2 #12 "thoat tai close =>
   nhan"); notional = qty x close nen ket thuc dung moc (path[60h-1]). Khong nhan ky tai T_k (vao sau moc 1 phut).
11. mx = max close phut 0..j / p0 (cho "lenh te nhat so voi SL"); mxh = max close trong cua so gio chua phut thoat, toi phut thoat.

## Tang danh muc (port.py) - logic B0 giu nguyen, chi them nhung diem sau
12. Thoat o phut j thuoc cua so gio (T_{kx-1}, T_kx], kx = ke + ceil(j/60). Cho trong dung duoc tu quyet dinh gio kx (thoat giua gio => gio
   ke tiep; thoat dung moc j = 60h => cung gio, nhu B0 "thoat truoc vao").
13. Equity de tinh size tai gio k = MTM theo close nen open T_k (cung phut voi lenh vao), funding den T_k, truoc phi cua lenh vao gio k.
14. Equity MTM moi gio theo mk = path[60h]; "xau nhat" = tru sum N (hm - mk) cua vi the mo qua moc VA tru N max(0, mxh - xr) cua vi the thoat
   trong cua so (B0 bo qua vi the thoat giua nen) => BAT LOI hon B0.
15. Cuoi fold kl = end - 1 h: khong vao lenh; vi the con mo dong tai mk(kl), 'eod', khong truot. Fold doc lap tu 10 000, cooldown reset (B0).
16. Phi: vao N x 0,07 %; ra N x xr x 0,07 % (notional luc ra, nhu B0 qty x px x FEE).
17. Thuoc do: B0 sim.metrics (import) + x_miss; bo x_time_sub, x_gap cua B0.

## Chon / bao cao (select_b1.py)
18. In-sample (i): dung luat B0 (hop le: >= 30 lenh moi fold, lai ca 3 fold, maxDD xau nhat DEV <= 30 %); diem maximin; cao nguyen >= 60 %.
   Kiem: ap tren grid B0 tai lap cau hinh 759, 69 hop le (test).
19. WFO (ii): luat CHI thay cot cua cac fold duoc phep (restrict + assert; test bay). Hop le = >= 30 lenh moi fold dung, lai moi fold dung,
   max(maxDD xau nhat cac fold dung) <= 30 %; cao nguyen = hang xom lai o moi fold dung. Ap tren grid B0: top-1 654 (F1) / 758 (F1+F2) khop
   A1, nhung so hop le 744 / 162 (A1 ghi 761 / 178 - A1 khong ghi ro dinh nghia DD cua minh).
20. (iii) Spearman cua diem fold (ret / maxDD xau nhat) giua cac cau hinh; ti le lai moi fold. (iv) breakdown() chay lai MOT cau hinh tren DEV.
   EW alt = TB loi suat ngay (moc 00:00, close 1m) cac coin trong universe dau ngay.

## Doi chung ngau nhien (rand_b1.py)
21. So DOT moi thang = B0 rand.episode_starts tren ung vien B1 cua lop (ADDENDUM2 G1); pool = (coin, gio) trong universe VA co nen 1m tai T_k;
   rut khong hoan lai (B0 rand.draw); s ~ U(0,1); cung tap cho DEV + 3 fold. Seed 20261127, luot r cua lop ci: default_rng([seed, ci, r]).
22. Thong ke moi luot = max diem maximin qua 585 cau hinh (195 thoat x 3 K) cua lop + so cau hinh hop le; p_max tinh RIENG tung lop.
   Lop E1: pool doi universe tai gio vao (E1 that khong doi) - nhu B0.

## CAN MASTER QUYET
A. Hang xom cua tham so trailing cho cao nguyen: cai = arm theo thu tu (3, 5, 7, 10, tat) giu gap; gap (2, 3, 5) giu arm; "tat" ke (10 %, g)
   voi MOI g (3 hang xom). Phuong an khac: tat ke (3 %, g) hoac coi trailing la 1 tham so 13 nac.
B. "Top-20 theo luat chon" o WFO: cai CHINH = 20 cau hinh dau tien qua TRON luat (hop le + cao nguyen) theo diem; bao them ban 20 cau hinh
   hop le dau tien (khong xet cao nguyen). Can chot ban nao la so dua vao tieu chi "DI TIEP B2".
C. Pham vi giam cua doi chung khi khong kip: prereg ghi "(W7, E0) va (W14, E0)" khong noi z_min. Cai 'reduced' = 6 lop (W7/W14, E0, ca 3 z_min).
   Phuong an khac: chi z_min cua cau hinh chon / WFO top-1. Va: p_max dung lop nao de so voi nguong 0,05 (lop cua WFO top-1? max qua lop?).
D. In-sample "maxDD xau nhat <= 30 %": cai = DEV (nhu B0); phuong an khac = max qua 3 fold.
E. Uoc thoi gian doi chung (DEV_B1.md): neu ca ban reduced 100 luot van > 3 h thi can MASTER chot so luot / so lop (prereg: >= 100 luot).
