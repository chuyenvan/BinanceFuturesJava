# PREREG_FX_ERRATA3 - sau A1 audit code G1 va G3 (ca hai PASS-WITH-MINOR; A1_G1_CODE.md, A1_G3_CODE.md); chot TRUOC khi chay that
Chot boi MASTER 2026-11-27 00:50. Chua co loi suat that nao duoc tinh. Moi thay doi deu theo huong BAO THU hon hoac chi them bao cao mo ta.
K1 (G1 + G3). p cua doi chung ngau nhien = (1 + so luot >= that) / (N + 1) (thay cho so luot / N). Tieu chi D2 dung p nay.
K2 (G3). Bien broker 1 % / nam tinh tren TONG |trong so| cua tung phan (tranche), khong tinh tren vi the rong da bu tru.
K3 (G3). Moi thuoc do WFO (D1, D3, D6, D7) chi gom cac phan VAO LENH trong WFO (khong gom phan mo cuoi TRAIN tran sang); vi the con mo
   o cuoi ky bi tinh phi dong.
K4 (G3, mo ta). Bao kem p theo doi chung "dich vong khoi" (giu cau truc cum cua tin hieu) - khong vao tieu chi.
K5 (G1, mo ta). Bao kem do nhay: carry tinh bang lai suat cua chinh thang giu (thay cho thang m-1 co dinh) - chi mo ta, khong vao tieu chi
   (A1: lai suat cu 1-2 thang co the phong dai carry trong chu ky ha lai suat 2001, 2008).
K6 (G1 + G3). Bo sung unit test cho cac diem A1 thay test chua bao ve (G1: phan vi gate khong gom ngay t; chon cau hinh chi bang TRAIN;
   luot ngau nhien qua cung gate; D6 bo thang TOT nhat; x2 nhan chi phi; nguong D2. G3: nguong |z| 1,5; D9 = 150; dau swap; phi bien).
K7 (G3, ghi nhan). TFF khong co warm-up: TRAIN cua W156 thuc te chi tu ~2009-06 - diem yeu thiet ke, khong sua.
