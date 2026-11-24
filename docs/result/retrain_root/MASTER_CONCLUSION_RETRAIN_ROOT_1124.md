# MASTER_CONCLUSION_RETRAIN_ROOT_1124 - ket luan sau Tang 1 + ADD1 (luot 2) + audit A1
MASTER, 2026-11-24 14:10 (+07). Prereg 899f2fc8, ADD1 55b146c8, ERRATA1 591b3382. Audit: A1_RETRAIN_ROOT_T1.md (PASS, 1 MAJOR dien giai),
A1_RETRAIN_ROOT_ADD1.md (PASS-WITH-MINOR). Tang 2 (M4) CHUA chay. Khong du lieu >= 2026-10-01, khong PnL 2026 moi.

## 1. Ap cay quyet dinh (co hoc)
- Tang 1: M1 = ANOMALOUS (1,192 / 1,509 ngoai [0,856;1,143] / [0,858;1,127], N = 18) => CASE B. M2 = TYPICAL ve gate (1,35 trong [0,576;1,727]).
  M5 = "lane P khong phan biet duoc voi nhieu doi-seed p15" (3,508 <= p95 3,895 ; sat bien).
- ADD1 luot 2 (recipe PROD, hop le v1'-v4'): E1' = S-NO (nguon feature DEV/Vision khong tao dich ngoai dai o 2026Q2) ; E2' = "mapper KHONG giai thich"
  (ban B 07-10..09-30: 1,213 / 1,496) ; E3' (mo ta) = 1,509 nam TRONG dai 64 cap doi-seed tai 2026Q3 (hang 92,2 %; 5/64 cap >= 1,509).
- Nhanh ap dung: "E1 = S-NO va E2 = mapper KHONG giai thich => dich thang T1 la that va chua giai thich duoc => GIU model live ; khong de xuat quy trinh ;
  bao owner". => GIU 3 MODEL LIVE. CHUA co quy trinh retrain duoc de xuat.

## 2. Phat hien (muc bang chung ghi ro)
- [da kiem] Pipeline retrain p15 dung: train lai recipe PROD cut 0701 ra booster trung sha T1.
- [da kiem, bac bo] Nguon feature Vision va loi mapper KHONG giai thich do lech duoi T1/live. (Gia thuyet MASTER neu luc 13:15 - SAI.)
- [mo ta, ngoai cach doc ghi truoc] Duoi cuc tri cua p15 phu thuoc manh vao ngau nhien luc train: chi doi seed (subsample/colsample 0,8), tren 2026Q3 ti so duoi
  q99,995 giua hai ban train dao dong 0,64 - 2,09 (pearson pred giua seed 0,973 - 0,992). sd log q99,995 giua seed: 2025Q3 0,035 ; 2025Q4 0,077 ; 2026Q3
  0,16 - 0,24. Model live fold_20 co q99,995 tren Q3 THAP hon ca 8 seed train lai tai cung cut ; T1 nam giua dai seed cua no => ti so 1,51 chu yeu do fold_20
  la mot lan "rut" duoi thap, khong phai do T1 cao bat thuong. Doi mep cut (~435 dong) da tuong duong doi seed (pearson 0,981).
- [suy ra, CHUA do truc tiep] Vi gate dung quantile 0,99995 va DCA dung nguong tuyet doi 0,008, moi lan doi model la mot lan rut ngau nhien ve so lenh / tap lenh.
  Phep thu 1 quy (T1 vs live) khong du luc de chap nhan hay bac mot ban retrain.
- KHONG duoc noi: "retrain an toan" ; "nhieu seed giai thich het" (64 cap khong doc lap, khong co nguong ghi truoc, 1 quy) ; "do che do 2026".
- Dinh chinh: (i) "live train toi cuoi 2025" SAI - fold_20 cat 2026-04-01 ; (ii) ADD1 luot 1 dung recipe G0 la loi cong cu cua MASTER (ERRATA1) ;
  (iii) audit Tang 1 cau "d/c ~ 1, b/a ~ 1" SAI (A1 tu dinh chinh).

## 3. Viec tiep (CHUA bat dau ; moi viec can prereg rieng ; khong viec nao doi jar / model live)
- R1 on dinh duoi: ensemble K seed cho p15 (trung binh diem) - do tren DEV: phuong sai ti so duoi / pass gate / ROI quy giua cac "lan retrain" giam bao nhieu ;
  doi model = doi strategy => validate DEV day du + HO + parity truoc khi nghi toi live.
- R2 replay gate theo seed tren DEV (va Q3 mo ta): doi seed doi bao nhieu % tap lenh.
- R3 M4 (Tang 2 prereg goc): model gia 1 quy vs retrain dung han tren DEV.
- R4 nghiem thu retrain: KHONG bang PnL 1 quy ; bang tai lap pipeline + thuoc xep hang + dai co che ; va shadow song song tren feature live truoc khi doi.
