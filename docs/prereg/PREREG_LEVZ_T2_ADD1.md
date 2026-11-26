# PREREG_LEVZ_T2_ADD1 - lam ro sau moc DEV 1 (chi co thong ke ve sinh: ti le khop + do tre; chua co loi suat nao)
Chot boi MASTER 2026-11-27 06:50. Prereg goc b0515b3c.
M1. EB / EO: dieu kien kiem tai moc gio T_{k+j}; vao lenh tai close nen 1 phut ngay sau moc (tre 1 phut nhu E0 cua B1), truot 0,1 %.
    "Close gio" = close1m tai phut cuoi cua gio.
M2. Dua vao port.py (lam viec theo gio): gio vao = floor(phut vao / 60) - lam tron XUONG (bao thu: khong dung cho giai phong sau moc gio;
    cooldown lech < 1 h). Time-stop / SL / trailing / funding tinh dung tu phut vao that.
M3. Placebo thoi diem: phut ngau nhien deu trong 1..2880 trong so phut co nen that. Luot placebo thieu nam cham duoc ma kieu vao that cham
    duoc => tinh la KHONG >= that; kieu vao that khong cham duoc nam nao => p = NaN, U-c truot. Placebo "hoan vi do tre" (mo ta): 20 luot.
M4. Khong loc cac truong hop gia vao / p0 rat thap (coin giam manh trong cua so cho) - giu nguyen, bao phan phoi gia vao / p0.
M5. Thong ke ve sinh da thay (khong phai ket qua): ti le khop EL_1 89 %, EL_2 80 %, EL_3 71 %, EB 29 %, EO_3 96 %, EO_5 88 %; do tre
    trung vi 1,1 h / 3,2 h / 5,6 h / 11 h / 8 h / 12 h. EB chi khop 29 % => nhieu kha nang truot U-d (so lenh); khong sua.
M6. Placebo nang (~55 gio CPU) => chay tren Kaggle qua levz_kg, chia shard.
