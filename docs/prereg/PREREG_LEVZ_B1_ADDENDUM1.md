# PREREG_LEVZ_B1_ADDENDUM1 - chot 5 diem DEV hoi (DEV_B1.md muc CAN MASTER QUYET), TRUOC khi chay luoi B1
Commit boi MASTER 2026-11-26 11:42 +0700. out/grid_b1.parquet chua ton tai; MASTER chua thay loi nhuan cua cau hinh B1 nao (DEV chi chay 2 cau
hinh doi chieu X1 / X2 va khong bao loi nhuan).
A. Hang xom cua trailing trong kiem cao nguyen: (arm a, gap g) ke voi arm ke ben cung gap va gap ke ben cung arm; "tat" ke voi moi cau hinh
   arm 10 % (moi gap) va nguoc lai. (Nhu DEV da cai.)
B. WFO: top-1 = cau hinh dau tien qua TRON luat (hop le + maximin + cao nguyen, chi tren cac fold duoc phep). Top-20 dung cho tieu chi "DI TIEP
   B2" = 20 cau hinh diem maximin cao nhat trong so cau hinh HOP LE tren cac fold duoc phep (KHONG ap cao nguyen cho top-20). Bao ca hai ban.
C. Doi chung ngau nhien ban giam = 6 lop (W in {7, 14}) x E0 x (z_min in {2,5 ; 3,0 ; 3,5}), moi lop >= 100 lan, p_max tinh RIENG tung lop.
   Tieu chi muc 5 dung p_max cua lop chua cau hinh WFO top-1 nam 2025; neu lop do la E1 thi chay them dung lop do (>= 100 lan) truoc khi ket
   luan. Bao p_max cua moi lop da chay.
D. Dieu kien DD in-sample: maxDD xau nhat toan DEV <= 30 % (nhu B0). Voi WFO: maxDD xau nhat cua TUNG fold duoc phep <= 30 %.
E. Chay ban giam (C) truoc; khong can ban 12 lop tru truong hop o C.
Ghi nhan (khong doi): engine chi thay close 1 phut (khong thay bien dong trong phut); vao tre 1 phut; "xau nhat trong gio" gom ca phan thoat
giua nen; so cau hinh hop le WFO tren luoi B0 do DEV tinh (744 / 162) khac A1 (761 / 178) do dieu kien DD theo fold (D) - top-1 trung nhau.
