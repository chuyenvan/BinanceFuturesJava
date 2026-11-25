# PREREG_LEVZ2_ADDENDUM2 - sua theo audit simulator (A1_LEVZ2_SIM), TRUOC khi chay luoi
Commit boi MASTER 2026-11-25 21:42 +0700. out/grid.parquet chua ton tai. MASTER chua thay loi nhuan cua cau hinh mo phong nao (A1 da chay 4 cau
hinh de doi chieu doc lap va KHONG bao loi nhuan; cac file a1/out/ref_* khong duoc doc de chon tham so).

G1 (muc 6, doi chung ngau nhien - A1 B1): "so ung vien that cua thang" = so DOT cua cau hinh chon trong thang do, DOT = gio dau tien cua moi
   coin sau khi gop cac gio ung vien cach nhau <= 72 h; moi luot ngau nhien rut DUNG so dot do (coin, gio) deu tu universe cua thang. Ly do: dem
   theo gio tho lam luot ngau nhien co gap 1,4-6,8 lan so dot => p_rand do "vao nhieu lenh hon", khong do tin hieu.
G2 (muc 2 (a)(b), thu tu SL / DCA trong nen - A1 B2): chua DCA va open < 1,10 x p0 <= high => DCA TRUOC (neu tran 60 % cho phep), roi kiem SL
   tren khoi luong moi; open >= muc stop => thoat tai open, khong DCA. Ly do: muc stop (>= 1,15 x p0) cao hon muc DCA nen gia di qua muc DCA
   truoc; ban cu (SL cham thi bo DCA) la lac quan.
G3 (muc 2 (b)(c) - A1 M1): trong mot nen, neu trailing da kich hoat tu truoc va high >= muc trail cua nen truoc thi thoat theo trailing va KHONG
   DCA trong nen do.
G4 (ghi nhan lech chu, giu nhu code - A1 M2, M3, M5): trailing khi gap thoat tai max(open ; muc x 1,001); cooldown: lenh moi cho cung coin chi
   duoc tu gio thu 73 sau gio vao truoc (giong tang 1); gia vao = close gio t (tre 0; tang 1 vao sau 1 phut).
G5 (A1 M6): grid.py assert bat bien ke toan cho ca DEV, F1, F2, F3.
Ghi nhan (A1 M4): voi tran 60 % va size = equity x 0,60 / K_max, DCA gan nhu luon bi tran chan khi du K vi the => o B0 chieu DCA gan nhu
khong co tac dung; khong sua (DCA lam o tang B4).
