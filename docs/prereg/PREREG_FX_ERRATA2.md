# PREREG_FX_ERRATA2 - lam ro sau khi DEV viet code (chua co loi suat that nao duoc tinh; chua A1; chua chay)
Chot boi MASTER 2026-11-27 00:05. Ap cho PREREG_FX_G1 / G3 (058ed482) + ERRATA1 (a65fb2d0).
J1 (G1 + G3, chi phi). "3 pip khu hoi" qua re voi cap gia lon (USDNOK, USDSEK, USDJPY: 3 pip ~ 0,2-0,3 bp). Chi phi khu hoi moi cap
   (tru EURUSD giu 0,8 pip) = MAX(3 pip, 3 bp cua gia tri giao dich). Kich ban xau x2 nhu cu.
J2 (G1). FX_VOL = trung binh deu vol thuc 21 ngay cua MOI dong tien co ty gia FRED tai ngay do (EUR chi tu 1999), khong phu thuoc co lai
   suat hay khong; lich su tinh phan vi dung ty gia tu 1971 (thong tin qua khu, khong phai du lieu TRAIN bi cam).
J3 (G1). D6 "bo 5 % thang tot nhat": lay chuoi loi suat THANG cua cau hinh duoc chon tren WFO, bo ceil(5 % x so thang) thang co loi suat
   cao nhat, loi suat gop cua phan con lai phai > 0. G3: don vi la TUAN nhu prereg G3.
J4 (G1). Gate VIX dung VIX cua ngay lam viec TRUOC (gia FRED chot trua New York, truoc gio dong cua VIX) - chap nhan lua chon C8 cua DEV.
J5 (G3). Chi phi tinh cho TUNG phan (tranche) rieng, KHONG netting giua phan dong va phan mo cung ngay (bao thu). Bao kem (mo ta) ban co netting.
J6 (G1 + G3). Doi chieu tay PnL thang 2008-10 tren du lieu that do A1 KET QUA lam sau khi chay (DEV khong duoc tinh loi suat that).
J7 (G3). Chap nhan tam cac lua chon C5 (warm-up COT 1986-1992 cho cua so z), C7, C9, C12, C14, C15, C19, C21, C23, C24 cua DEV; A1 soat
   va bao muc nao co the lam dep ket qua.
