# CHOICES_T2 - lua chon cua DEV khi prereg mo ho (PREREG_LEVZ_T2 @b0515b3c). DANG VIET (checkpoint 1).
## Diem vao (entry_t2.py)
1. Chi so phut j <-> nen 1m open_time H0 + j phut (close1m B1, ffill). Phut THAT = co nen that (>= nen dau, ngoai gap cua gaps.npz).
2. p0 = close1m[60 k] (= gia vao E0 cua B1). Ung vien = hop W7_E0 z 2,5/3,0/3,5 cua cand_b1 (4 792 (k, c); lop 2,5 chua hai lop kia).
3. Cua so 48 h: moi quyet dinh phai xay ra tai thoi diem <= T_k + 48 h.
   EL: lenh limit dat sau khi nen 60 k dong; xet nen i = 1..2879 (nen dong <= T_k + 48 h); chi khop o nen THAT; gia = dung muc.
   EB / EO: xet tai moc T_{k+j}, j = 1..48; vao tai close nen 60 (k + j) (tre 1 phut nhu E0 cua B1) x (1 - 0,001).
4. EB: "close gio" = close cua nen 1m cuoi gio (close1m[60 h - 1]); L = min close cua 24 nen gio dong tai T_{k-23}..T_k (nanmin).
5. EO: OI = exp(x) cua levz/work/oi_*.parquet theo dung vong lap levz.Data.X (ban ghi ts <= h - 10 phut, assert); max OI tinh tren
   cac hang k..k+j (bo NaN); hang hien tai NaN => khong kich hoat.
6. EB / EO kich hoat nhung nen vao (60 (k + j)) khong co that => khong vao gio do, xet lai o gio sau.
7. Khong khop trong cua so (ke ca cua so bi cat boi 2025-12-31 23:59) => bo ung vien cho kieu vao do.
## Bang thoat (exits_t2.py - DA VIET; ADD1 M1-M4 chap nhan 1-7, 8-10)
8. Phut vao m = 60 kb + r (0 <= r <= 59). Engine B1 (exits.exits_core) va T1 (exits_t1.Cur / bracket / part) goi NGUYEN BAN tren duong gia
   CANH THEO PHUT VAO (p[0] = gia vao that, p[i] = close1m[m + i]) => j, ly do, xr, mx, flag, j1, xr1 dung "tu phut vao that"
   (time-stop = 60 H phut sau m). STATE: hang tin hieu kb + h (h >= 1) => state_m = 60 h - r.
9. Port B1 lam viec theo GIO: gio vao cua port = kb = floor(m / 60) (quyet dinh slot / size / cooldown tai T_kb; khong nhin truoc vi
   equity tai T_kb co truoc khi khop; slot giai phong trong (T_kb, m] KHONG duoc dung - bao thu). j' = j + r (phut tinh tu T_kb) =>
   kx = kb + ceil(j' / 60) dung quy uoc port. Mang gio (mk, hm, fh, fc) tinh tren duong canh T_kb voi tien to phut 0..r = gia vao
   (mk[0] = 1, chua co lai lo truoc khi khop); do rong 722 (r > 0 va H = 720 => gio thoat toi kb + 721). fund, mxh tinh lai tren
   khung kb (cung cong thuc B1 / T1). Funding moc T_{kb+h} chi nhan khi nen vao dong TRUOC moc (60 h - 1 > r).
   Voi E0 (r = 0) moi thu trung B1 / T1 (test a).
10. Cooldown 72 h cua port tinh theo gio kb (lam tron xuong gio cua phut vao that; lech < 1 h).
11. grid_t2: ung vien cua port = (kb, c, s goc cua tin hieu, cid = hang bang thoat cua kieu vao); fold theo kb. Task sap theo (kieu vao,
    bo thoat) de moi tien trinh dung lai view (PartView lon). --shard i/n: chi so task % n == i tren thu tu nay.
12. select_t2: hang xom = 1 tham so 1 nac TRONG ho thoat (B1: zmin, K, SL, H + trailing dung logic select_b1 voi W / E co dinh;
    PART: zmin, K, s, H; STATE: zmin, K, zo, s, H); key chuan hoa NaN = 'na'; kiem: 1 899 key duy nhat, 16 008 hang xom deu ton tai.
13. placebo_t2: thong ke = tong trung vi top-20 (valid20) cac nam cham duoc; p = (1 + #>=) / (1 + nrep) (ADD1 M3). 'perm': phut
    vao = 60 k + d hoan vi trong nam; neu phut do khong co nen that => phut that ke tiep <= 60 k + 2880, khong co => bo (dem n_dropped).
    Placebo chi cho 6 kieu vao moi (E0 khong co placebo). --out DIR de chay Kaggle (runner chua symlink levz_t2/out).
14. Du lieu gia (fake_t2): test g voi 3 luot placebo thi p >= 1/4 => U-c KHONG the dat; test g se dung 19 luot cho kieu vao cay san
    (p min = 0,05) - ghi ro la lech so voi "3 luot" cua giao viec.
15. U-f: kieu vao phai cham duoc ca hai nam va trung vi top-20 > cua E0; nam E0 khong cham duoc (khong co cau hinh hop le) tinh la
    kieu vao hon E0 o nam do. U-e: thieu top-1 (khong cau hinh nao qua tron luat) o mot nam => U-e truot.
16. fake_t2 cay san: +2,5 % trong 2 h, giu 2 h, roi -5 % (vinh vien). Ban dau -20 % lam equity gia no qua ~1e10 => check_acct cua B0
    (sai so tuyet doi 1e-6) truot do lam tron float, khong phai loi ke toan; giam xuong -5 %.
## Sau A1 (PASS-WITH-MINOR, N1-N4)
17. N1: U-c chi dat khi placebo time du 100 luot VA p <= 0,05; chua du => U-c False, report ghi "placebo chua du luot". (Test g dung
    19 luot va coi la du - CHOICES 14, chi cho du lieu gia.)
18. N2 (thay CHOICES 15 ve U-f): nam E0 khong cham duoc => U-f khong danh gia duoc => U-f False (bao thu), report ghi ro.
19. N3 han che: cac lenh khop trong CUNG gio kb duoc port xep theo s (diem tin hieu), khong theo phut khop that trong gio.
20. N4 han che: lenh co r = 59 (nen vao dong dung moc T_{kb+1}) khong nhan funding cua moc T_{kb+1}.
