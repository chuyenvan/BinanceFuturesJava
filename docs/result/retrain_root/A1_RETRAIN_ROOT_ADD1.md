# A1_RETRAIN_ROOT_ADD1 - audit doc lap luot 2 (ERRATA1, recipe PROD) + phep do mo ta bo sung
Agent A1 (Opus), 2026-11-24 (+07). Doi tuong: RESULT_RETRAIN_ROOT_ADD1_E1.md sha256 af41edc8... (xac nhan), add1e1_preds.npz 41f98dac..., code/add1e1_run.py.
Doc ADD1 (55b146c8) + ERRATA1 (591b3382). Code/output A1: a1/a1_add1_recalc.py/.json, a1_v1check.py/.json, a1_prod_dev.py/.log/.json (prod_tmp/ = booster+onnx 25 model).
Job nang: 13:49:38-13:58 (flock + nice 10, 25 lan train, 479 s); khong thay run_rlive.

## VERDICT luot 2: PASS-WITH-MINOR. Nhan xac nhan: E1' = S-NO ; E2' = "mapper KHONG giai thich" ; E3' = "trong nhieu seed tai 2026" (1,509 hang 92,2 %, 5/64).
Cay ADD1 muc 3 ap co hoc: S-NO + mapper KHONG giai thich => nhanh "dich thang T1 la that va chua giai thich duoc => GIU live; bao owner". E3' chi mo ta.

## 1. Tai tinh (A1 vs RUN)
(a) v1' doc lap (loader rieng, ONNX fold_20 tren gate A Q3, 132 480 phut): pearson 0,99999999999994, max|d| 1,49e-8 (RUN 1,0 / 1,5e-8). v2' booster T1: max|d| 2,2e-8.
    v3 tu file pred: 1,19197 / 1,50869 (= RUN). v4': sha256 out/prod/c20260701_s42/booster.json = p15_t1/booster.json = 71e82572... (tu tinh sha256sum) => trung.
(b) Tu npz (code rieng): E1' DEV 0,9481/0,9343, Vision 1,0199/1,0128; X_m0101 1,0859/1,0773, X_m0401 1,1682/1,1679 ; E2' A 07-10..09-30 1,2106/1,5428, B 1,2134/1,4958
    (cung 119 520 phut, tsA==tsB), A ca Q3 1,1920/1,5087, A 07-01..07-09 1,0403/1,0506 ; E3' R99995 0,6441/0,9418/2,0943, hang 1,509 = 92,19 %, 5/64 cap >= 1,509 ;
    R9999 0,7409/0,9939/1,3944, hang 1,192 = 82,8 % (11/64 >= 1,192) ; pearson giua seed W 0,978-0,993, L 0,973-0,991. TAT CA TRUNG RUN.
(c) Du lieu: moi bo doc loc ts < 2026-10-01 00:00 +07 khi doc + assert (add1_run.read_csv_filtered/read_pred); store kiem n_all == n_loc truoc khi script PROD doc ca file;
    gate doc usecols timestamp+33 V3 (khong nhan); E1' DEV usecols timestamp+V3. Nhan chi doc boi chinh recipe train (dong < cut, nhu T1). Khong PnL. npz: max ts < END (A1 assert).
(d) Nhan dung luat: E1' ca DEV va Vision trong H ca 2 quantile => S-NO. E2' (Lam ro 1): B 07-10..09-30 NGOAI H (1,213 > 1,143; 1,496 > 1,127) => "mapper KHONG giai thich". Dung.
MINOR: W seed 42 = booster native, cac seed khac + L = ONNX (|d| ~1e-8, vo hai); E1' DEV parse float64->float32 vs Vision float32 truc tiep (RUN da ghi).

## 2. Soi E3'
(a) Chen seed: patch XGBRegressor.fit chi goi set_params(random_state=s) roi fit goc; khoi phuc trong finally; assert get_params()['random_state']==s. Day la thay doi DUY NHAT
    (script b41c9159 chay dung byte qua runpy). Recipe co subsample 0,8 + colsample_bytree 0,8 => seed co tac dung that (pred khac, pearson 0,97-0,99). Seed 42 cua RUN di duong
    KHONG va (if seed != 42) = v4' trung sha T1. A1 kiem them duong VA voi seed 42 (cut 20260101, du lieu DEV): booster sha 2ceeb8a7... = m0101 cua RUN => patch trung tinh. OK.
(b) L seed 42 (PROD cut 0401 mep +07, 2 758 605 dong) vs fold_20 (cut 0401 UTC, purge 0) tren Q3 A: pearson 0,9809, max|d| 0,0553, q(L42)/q(fold_20) = 1,293 (q99,99) / 1,473 (q99,995).
    => LECH LON: doi ~435 dong o mep lam doi chuoi lay mau subsample => tuong duong doi seed. fold_20 q99,995 = 0,02924 THAP HON ca 8 seed PROD-0401 (0,0298-0,0603);
    q99,99 0,0273 trong dai (0,0259-0,0419). T1 (= W42) q99,995 0,0441 o giua dai W (0,0388-0,0624). Ghep W 8 seed / fold_20: R99995 [1,328 ; 2,136], 4/8 >= 1,509; R9999 [1,137 ; 1,324].
    => 1,509 chu yeu do fold_20 co duoi cuc tri THAP bat thuong tren Q3, khong do T1.
    DINH CHINH audit Tang 1 cua A1 (muc B(i)): "d/c ~ 1 va b/a ~ 1" la SAI - moi thay doi so/thu tu dong train (mep, purge, sort) = doi seed hieu dung (luot 1: G0 vs T1 pearson 0,987).
(c) Null cong bang? UNG HO: cung recipe, cung du lieu, cung feature Vision A, cung quy; va (b) cho thay chinh "dong doi" fold_20 vs PROD-0401 da la mot lan doi seed hieu dung.
    CHONG: (1) 64 cap cheo gop nhieu ca W lan L; cau hoi "T1 co bat thuong khi live da co dinh" nen dung W_seed/fold_20 (=> [1,33;2,14], T1 o hang 4/8 - van "trong");
    (2) do tren gate Vision co loi mapper - nhieu seed o day khong dai dien DEV; (3) chi 8 x 8, khong doc lap (64 cap dung chung 16 model); (4) khong ghi truoc nguong.
    => Cong bang de noi "1,509 khong vuot nhieu seed tai 2026Q3"; KHONG du de noi "TYPICAL so voi lich su".
(d) Vi sao rong: KHONG do recipe PROD va KHONG chu yeu do ghep cheo - xem muc 3: tren DEV cung recipe PROD + cung thiet ke 64 cap: 2025Q3 [0,868;1,083], 2025Q4 [0,768;1,204]
    (~ dai RECON [0,82;1,20] G0). Nhieu cung-cut: sd(log q99,995) qua 8 seed = 0,035/0,036 (2025Q3 W/L), 0,078/0,075 (2025Q4), 0,156/0,240 (2026Q3) => 2026Q3 rong gap 2-7 lan.
    Ghep cheo chi nhan ~sqrt(2) so voi ti so-voi-ban-goc. => dac thu 2026Q3 (che do + feature Vision), khong phai recipe.

## 3. Phep do MO TA bo sung (KHONG co trong prereg; viet SAU khi thay E3'; chi mo ta, khong dung cho cay quyet dinh)
Recipe PROD that (train_gate_fold.py b41c9159 qua runpy; pd.read_csv va tra ve DEV loc ts < 2026-01-01 UTC khi doc, giu thu tu file; patch seed nhu E3', ap ca seed 42).
Kiem duong ong: seed 42 cut 20260101 tai lap sha 2ceeb8a7 (m0101 RUN). Cut 20250401/20250701/20251001 x 8 seed; quy +07; feature DEV.
| quy | n | R9999 64 cap min/med/max | R99995 64 cap min/med/max | cap >= 1,509 / >= 1,192 | cap seed42 | pearson seed W / L | sd log q99,995 W / L |
|---|---|---|---|---|---|---|---|
| 2025Q3 | 132480 | 0,905 / 0,972 / 1,016 | 0,868 / 0,980 / 1,083 | 0 / 0 | 0,970 / 1,010 | 0,994-0,996 / 0,992-0,995 | 0,035 / 0,036 |
| 2025Q4 | 132480 | 0,810 / 0,982 / 1,173 | 0,768 / 0,983 / 1,204 | 0 / 0 | 0,994 / 0,992 | 0,979-0,994 / 0,971-0,993 | 0,078 / 0,075 |
| 2026Q3 (E3', Vision A) | 132480 | 0,741 / 0,994 / 1,394 | 0,644 / 0,942 / 2,094 | 5 / 11 | 0,922 / 1,024 | 0,978-0,993 / 0,973-0,991 | 0,156 / 0,240 |
=> Dai seed rong la dac thu 2026Q3, khong phai tinh chat chung cua recipe PROD. (2025Q4 pearson giua seed tuong duong 2026Q3 nhung duoi on dinh hon nhieu.)

## 4. Y KIEN A1 (y kien, khong phai ket qua prereg)
DUNG MUC bang chung:
- Lech duoi T1/live o 2026Q3 KHONG do cong thuc T1 sai, KHONG do loi mapper (E2'), va nguon Vision khong tao dich o Q2 (E1', 1 cap seed).
- Phan lon ti so 1,51 den tu model LIVE (fold_20) co q99,995 thap hon moi seed cung recipe; T1 nam giua dai seed cua no. Tai 2026Q3, duoi cuc tri p15 cuc ky nhay voi
  seed/row-order (sd log 0,16-0,24) => q99,995 1 quy la thong ke khong on dinh; nhan ANOMALOUS (so voi H) dung luat nhung khong chi ra "retrain hong".
- He qua thiet ke: gate cuon q 0,99995 tren p15 phu thuoc ~7 phut/quy => moi lan doi model la mot lan "rut tham" thang duoi; pass +35 % (lane P) la that ve co che.
QUA TAY: "retrain an toan / T1 tuong duong live" (chua co M4; PnL lane P van kem; ti so pass gate van doi that); "nguyen nhan la nguon Vision" (chua do nhieu seed DEV vs Vision cung quy);
"nhieu seed giai thich het" (E3' mo ta, khong ghi truoc nguong; 2026Q3 van ngoai H va dai seed 2026 khac DEV); quy ket cho "che do 2026" (moi 1 quy).
NEN DO TRUOC khi thiet ke quy trinh (can prereg): (1) nhieu seed 2026Q2 tren DEV vs Vision (cung quy, ca hai nguon) - tach "che do" vs "nguon feature" cho do rong duoi;
(2) ensemble trung binh 8 seed (T1-ens / live-ens tren Q3): neu ~1 thi lech la thuan nhieu seed; dong thoi la ung vien giam phuong sai duoi; (3) M2 replay gate tren 2026Q3 theo seed
(phan phoi pass P/L) de biet 1,35 o dau trong nhieu seed; (4) LODO/phut cuc tri cua Q3 (ngay nao gay duoi, co trung 07-10+ khong); (5) M4 (Tang 2) van can cho Q-B.

## Khong kiem duoc
- Khong tu chay lai v4' bang train 2026 (chi so sha booster); khong kiem noi dung gate Vision ngoai cot V3; E1' frac o bang/cot chi doc tu RUN. Mot lan 'exit 0' thua trong
  a1_prod_dev.log (dong wrapper) - ket qua chi 1 lan chay (25 model, log tuan tu).
