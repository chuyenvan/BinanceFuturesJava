# OWNER_DECISION_PILOT_1121_ADD7 - mo rong pham vi du lieu Vision cho PILOT-M
Ghi luc: 2026-11-25 13:59 +0700 (MASTER ghi lai quyet dinh owner trong phien lam viec 2026-11-25).

## 1. Cau hoi MASTER (2026-11-25 ~12:45 +07)
"Cho phep dung du lieu Binance Vision tu 24/11 tro di de cham pilot khong? Du lieu sau 01/10 dang niem phong cho nghien cuu, va ngoai
le cu chi cap cho R-LIVE. Neu dong y: chi tai nen 1 phut va mark price cua cac symbol bot dang giu hoac la ung vien, chi de cham
pilot, khong tinh PnL."

## 2. Tra loi owner (nguyen van, bo dau)
"ok dung du lieu vision de cham pilot nhe"

## 3. Pham vi duoc mo (MASTER dien giai HEP, dung theo cau hoi)
- Du lieu: Binance Vision futures UM klines 1m va markPriceKlines 1m, ngay UTC >= 2026-11-24, CHI cho symbol live giu / co SUBMIT /
  ung vien rank <= 24 trong ngay cham, va du lieu dau vao ma rig ADD24 can de tai lap quyet dinh cua chinh cac ngay do.
- Muc dich DUY NHAT: cham PREREG_PILOT_M (commit 2a21fe35) - cac muc I1, I2, I5, I6, D2, D3, L-S, va M-E / I7 / D4 / L-S2 / M-G khi co
  wrapper duoc A1 duyet. Khong tinh / in PnL. Khong dung cho nghien cuu, chon tham so, train, hay danh gia chien luoc.
- Ngoai pham vi tren, du lieu thi truong >= 2026-10-01 VAN NIEM PHONG cho nghien cuu.
- He qua theo PREREG_PILOT_M muc 13 Q1: cac muc can Vision het trang thai KCD_CAU_TRUC do "chua co quyen" (van KCD_CAU_TRUC cho toi khi
  cong cu tuong ung duoc A1 duyet); khi co cong cu => cham LAI moi ngay tu 2026-11-24, khong doi tieu chi.
