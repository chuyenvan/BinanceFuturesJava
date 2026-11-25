# PREREG_LEVZ2_ADDENDUM1 - chot 4 diem cai dat + doi vai tro luoi thanh tang B0 cua PROGRAM_SHORT_LEVZ
Commit boi MASTER 2026-11-25 21:24 +0700, TRUOC khi chay luoi (out/grid.parquet chua ton tai). Da thay cho toi luc nay: chi so LENH cua 1 cau hinh smoke
(584 lenh, 2,9 % dinh SL, doi chieu gross voi tang 1); CHUA thay loi nhuan cua bat ky cau hinh mo phong nao.

## 1. Quyet dinh 4 diem DEV hoi (DEV_LEVZ2.md muc CAN MASTER QUYET) - giu nhu DEV da cai
A. E1: moc = gio LEV gan nhat trong 24 h truoc; vao tai gio dau tien co z_r <= -2 ke tu moc do. CHAP NHAN.
B. Tran 60 %: size = equity x 0,60 / K_max nen K_max vi the ~ 60 %; chi kiem tran khi DCA. CHAP NHAN.
C. Cuoi fold: dong cuong buc moi vi the tai close cuoi fold. CHAP NHAN.
D. Diem muc 5 va Calmar muc 7 dung maxDD "xau nhat trong gio". CHAP NHAN (bao thu).

## 2. Doi vai tro (theo chi dao owner 2026-11-25, xem PROGRAM_SHORT_LEVZ muc 0)
- Luoi 1 296 cau hinh cua PREREG_LEVZ2 = tang B0 "ban do tho". Muc 5 (luat chon) va muc 6 (doi chung ngau nhien) VAN chay va bao cao day du.
- Muc 7 cua PREREG_LEVZ2 ("DU DIEU KIEN DI HO" / "KHONG DI HO - dong ho") HET HIEU LUC: B0 tu no KHONG dua gi di HO va KHONG dong ho.
  Quyet dinh HO chi theo PROGRAM_SHORT_LEVZ muc 4 cho he da dong bang o B5; luat dung som theo muc 5 cua chuong trinh.
- Gioi han da biet cua B0: simulator nen gio => trailing (10 % / 5 %) va thu tu trong nen chi mang tinh chi dan; trailing min (arm 3 %) lam
  o B1 bang engine nen 1 phut. Ket qua B0 la IN-SAMPLE tren toan DEV - khong dung lam ky vong loi nhuan.
