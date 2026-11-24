# PREREG_RETRAIN_ROOT_ADD1_ERRATA1 - sai cong cu o ADD1: dung recipe G0 thay vi recipe da dung de dung T1 / fold_20
MASTER, 2026-11-24 13:40 (+07). Theo muc 6 prereg goc: sai sot cong cu => errata + bao ca hai luot.

## 1. Su kien luot 1 (ADD1 55b146c8; RESULT_RETRAIN_ROOT_ADD1.md sha256 f10468d7...)
- v1 pearson(m0401 recipe G0 tren gate A, file live 64f66a15) = 0,98709 < 0,999 => KHONG DAT. v2 (m0701 G0, file T1 c1b00ba9) = 0,98710 => KHONG DAT.
  v3 DAT (1,1920 / 1,5087). Chan doan (mo ta): ONNX fold_20 va booster T1 chay tren gate A tai lap file pred (pearson ~ 1,0) => doc gate / anh xa cot DUNG ;
  lech nam o MODEL: recipe G0 (1004/gabl/drv.py) KHAC recipe da dung T1 (rt_p15_train.py -> train_gate_fold.py b41c9159).
- Loi cua MASTER: ADD1 chi dinh recipe G0 cho cac model 2026 dua tren cau "recipe T1 ~ G0 (cay trung)" - SAI (P15-A la T1 trung voi chinh recipe cua no).
- So luot 1 la INVALID, CHI ghi lai, KHONG dung de doc: E1 R tren DEV 1,131 / 0,974, tren Vision 0,992 / 0,996 ; E2 A ca Q3 0,827 / 1,077, A 07-10..09-30
  0,864 / 1,299, B 0,849 / 1,299 ; E3 64 cap R99995 0,799 / 1,078 / 1,243. MASTER DA THAY cac so nay truoc khi viet errata.

## 2. Sua (CHI thay cong cu; cach doc muc 2-3 cua ADD1 GIU NGUYEN, tru 2 lam ro ghi o duoi)
- Recipe PROD = train_gate_fold.py dung commit b41c9159, goi dung nhu rt_p15_train.py da goi cho T1 (mep cut, purge, dtype, thu tu dong, tham so, seed mac dinh).
  m0701 = chinh booster T1 da co ; m0401 = chinh model live fold_20 (ONNX) ; m0101 = train moi bang recipe PROD, cut 2026-01-01 theo dung quy uoc mep cua recipe.
- Kiem hop le: v1' = m0401 (ONNX fold_20) tren gate A vs file live >= 0,999 ; v2' = booster T1 tren gate A vs file T1 >= 0,999 ; v3 nhu cu ;
  v4' (moi) = recipe PROD train lai tai cut 2026-07-01 voi seed mac dinh phai tai lap booster T1: pearson pred tren gate A >= 0,9999 (chung to goi dung recipe).
  Khong dat => INVALID, dung, bao.
- E1' = E1 voi m0101 / m0401 recipe PROD (m0401 = fold_20). E2' = E2 voi m0401 = fold_20, m0701 = T1. E3' = 8 seed recipe PROD (seed mac dinh + 7, 123, 13, 2024, 21,
  777, 99) cho cut 0401 va 0701 ; neu recipe PROD khong co nguon ngau nhien nao phu thuoc seed (8 seed cho pred trung nhau) => E3' = KHONG LAM, ghi ro.
- Lam ro 1 (viet SAU khi thay so luot 1 - ghi nhan): gateB chi co tu 2026-07-10 => phep so E2' A voi B lam tren CUNG khoang 07-10..09-30 ; "mapper giai thich"
  neu R tren B (ca 2 quantile) TRONG H trong khi R tren A cung khoang NGOAI H (it nhat 1).
- Lam ro 2: E3' doc mo ta nhu ADD1 ; them: bao ty le so cap co R99995 >= 1,509.
- Pham vi du lieu, cam PnL, cam >= 2026-10-01: nhu ADD1. Ket qua: RESULT_RETRAIN_ROOT_ADD1_E1.md, bao CA HAI luot.
