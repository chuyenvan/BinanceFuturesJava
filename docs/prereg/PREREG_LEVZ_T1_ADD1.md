# PREREG_LEVZ_T1_ADD1 - lam ro 3 diem cua ho HEDGE (tra loi cau hoi cua DEV; chot TRUOC khi co bat ky so loi nhuan nao cua T1)
Chot boi MASTER 2026-11-26. Prereg goc 186f2a5a. Tai thoi diem nay T1 moi co engine thoat + test hoi quy (a); chua chay luoi.
A1. Ba bo thoat tham chieu B1 trong HEDGE (xi 12 = thoat cua cfg 4107; xi 170 = exit_2024; xi 72 = exit_2025) chay tren CA luoi 3 z x 3 K x
    2 che do gate nhu moi bo khac (dung cau "Moi ho x 3 z x 3 K x 2 che do gate" cua prereg). Tong so cau hinh T1 = 9 468 (DEV dem).
A2. Duoi G_EW14, gate chi chan lenh SHORT MOI. Chan long phong ho luon bang h x tong notional short DANG MO (ke ca short mo truoc khi gate
    dong), can lai moi gio.
A3. Chan long: gia = close 1 phut cua BTCUSDT / ETHUSDT tai moc gio (cung kho close1m cua B1); funding that cua BTC / ETH (long tra khi
    funding duong). maxDD "xau nhat trong nen" cua danh muc co hedge = gia tri xau nhat cua phan short (nhu B1) CONG gia tri chan long tinh
    tai close 1 phut THAP NHAT cua BTC / ETH trong gio do (gia dinh hai dieu xau xay ra cung luc - bao thu). Bao kem maxDD tinh tai close gio.
