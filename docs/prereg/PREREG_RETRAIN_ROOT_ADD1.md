# PREREG_RETRAIN_ROOT_ADD1 - CASE B: tach nguon feature suy luan (DEV vs Vision vs loi mapper) khoi "them 1 quy du lieu"
MASTER, 2026-11-24 (+07). Viet TRUOC khi chay. Bo sung cho PREREG_RETRAIN_ROOT (899f2fc8).

## 0. Can cu (Tang 1 da chay + audit)
- ~/claude_master/w3/retrain_root/RESULT_RETRAIN_ROOT_T1.md sha256 adf12bf8... ; audit A1_RETRAIN_ROOT_T1.md sha256 16aa3d52... (so khop; M1 PASS tinh toan).
- M1: R9999 [0,856 ; 1,143], R99995 [0,858 ; 1,127] (N = 18, feature DEV) ; 2026Q3 T1/live = 1,192 / 1,509 => ANOMALOUS theo luat (CASE B).
  M2: PI [0,576 ; 1,727], 1,35 => TYPICAL ve gate. M5: p95 = 3,895 pp, |d_P| = 3,508 => "khong phan biet" (sat bien).
- Audit (MAJOR ve dien giai): cap 2026Q3 suy luan tren gate Vision ho4p1-x26-q3 (ban A, loi mapper 8 id: 16/41 cot, 99,2 % phut tu 2026-07-10 -
  HO4_P1 ADD7), M1 suy luan tren feature DEV => null cua M1 KHONG doi chung nguon feature. Recipe T1 ~ G0 (cay trung), fold_20 ~ G0 cut 0401
  (lech max 6,75e-5) => khac biet cong thuc gan nhu bang 0. Leave-one-day-out (mo ta): dai R9999 toi 1,234, R99995 toi 1,477.
- He qua: CASE B khong dieu tra "cong thuc T1" nua ma dieu tra NGUON FEATURE SUY LUAN + che do 2026.

## 1. Pham vi du lieu (noi rong CO GIOI HAN so voi muc 2 cua prereg goc)
- Cho phep tinh THONG KE DIEM p15 (khong PnL, khong sim, khong nhan) tren 2026-01-01 .. 2026-09-30, da duoc mo niem phong (HOLDOUT_UNSEAL_2026_1121).
- KHONG doc gi >= 2026-10-01. KHONG tinh PnL / ROI / so lenh moi. KHONG train model nao khac ngoai p15 recipe G0 tai cac cut neu duoi.
- Dai tham chieu H (co dinh, lay tu M1): R9999 trong [0,856 ; 1,143], R99995 trong [0,858 ; 1,127]. Dai LODO chi de MO TA.

## 2. Phep do
Model (recipe G0, gate_dataset_full.csv, seed G0): m0101 = cut 2026-01-01 UTC ; m0401 = cut 2026-04-01 UTC ; m0701 = cut 2026-07-01 (dong < 2026-07-01).
Kiem hop le: (v1) pred cua m0401 tren gate Vision Q3 ban A so voi pred live fold_20 (pred_2026.bin md5 64f66a15, doan Q3): pearson >= 0,999 ;
(v2) pred cua m0701 tren ban A so voi pred T1 (c1b00ba9, doan Q3): pearson >= 0,999 ; (v3) ti so q99,99 / q99,995 cua (T1 file)/(live file) tren Q3
tinh lai phai ra 1,192 / 1,509 (+-0,002). Mot kiem khong dat => phep do lien quan = INVALID, bao MASTER, khong sua cho khop.

E1 (nguon feature, 2026Q2 - quy co CA HAI nguon): cap LAG = m0101, WFO = m0401 du doan 2026Q2 (+07, cung tap phut) tren
  (i) feature DEV (gate_dataset_full.csv) va (ii) feature Vision (kernel ho4p1-x26-q2, gate.csv*).
  Thong ke: R9999, R99995 = q(WFO)/q(LAG) cho tung nguon ; va X_m = q(Vision)/q(DEV) cua CUNG model (m0101, m0401) o hai quantile ; ti le o feature
  bang nhau giua hai nguon (mo ta).
  Doc (ghi truoc):
  - S-REGIME: R tren DEV nam NGOAI H (it nhat 1 quantile) => che do 2026 tu no cho dich lon hon lich su 2021-2025 ; dai H khong ap duoc cho 2026.
  - S-YES: R tren DEV nam TRONG H (ca 2) VA R tren Vision NGOAI H (it nhat 1) => nguon feature Vision du de tao dich ngoai dai giua hai model.
  - S-NO: ca hai nguon TRONG H => nguon feature khong tao dich o Q2.
E2 (loi mapper, 2026Q3): cap LAG = m0401, WFO = m0701 du doan 2026Q3 tren gate ban A (ho4p1-x26-q3) va ban B (ho4p1-dupfx gateB, da sua mapper).
  Thong ke: R9999, R99995 tren A, tren B ; tach 07-01..07-09 va 07-10..09-30 (mo ta) ; leave-one-day-out cua R tren A va B (mo ta: min / max).
  Doc: R tren B TRONG H (ca 2) trong khi tren A NGOAI => "loi mapper giai thich dich ngoai dai" ; R tren B van NGOAI => mapper KHONG giai thich.
E3 (nhieu seed tai 2026, mo ta): 8 seed (G0, 7, 123, 13, 2024, 21, 777, 99) cho m0401 va m0701 ; phan phoi R99995 cua 64 cap (WFO seed i / LAG seed j)
  tren Q3 ban A ; bao min / median / max va vi tri cua 1,509.

## 3. Cay doc (co hoc)
- E1 = S-YES hoac E2 = "mapper giai thich" => KET LUAN: do lech thang diem T1/live o 2026Q3 duoc giai thich (it nhat mot phan) boi NGUON FEATURE SUY LUAN cua
  ban thu 2026 (Vision / mapper), khong phai boi cach train => phep thu T1 tren Q3 KHONG du hop le de bac retrain ; quy trinh nghiem thu retrain phai cham
  tren feature cung nguon voi train / live. Buoc tiep (prereg rieng): dung ban thu cung nguon ; M4 (Tang 2) van can de tra loi Q-B.
- E1 = S-REGIME => dai lich su khong ap cho 2026 ; ANOMALOUS mat can cu ; ve "KHONG KET LUAN" cho Q-A ; M4 la buoc tiep.
- E1 = S-NO va E2 = "mapper KHONG giai thich" => dich thang T1 la that va chua giai thich duoc => GIU model live ; khong de xuat quy trinh ; bao owner.
- E3 chi mo ta (neu 1,509 nam trong dai 64 cap => ghi "trong nhieu seed tai 2026").
- Khong nhanh nao cho phep dung PnL 2026 hay du lieu >= 2026-10-01.

## 4. Quy trinh
Agent RUN chay ; agent A1 kiem doc lap. Tai gate Vision Q2 / Q3 A / gateB tu output kernel Kaggle ve ~/claude_master/w3/retrain_root/k/ (chi tai, khong chay
kernel) ; ghi sha256. Job nang Oracle duoi flock oracle_heavy.lock, xong truoc 15:40 +07 ngay 24/11 hoac doi sau R-LIVE. Ket qua: RESULT_RETRAIN_ROOT_ADD1.md.
