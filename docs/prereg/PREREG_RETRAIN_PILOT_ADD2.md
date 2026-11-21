# PREREG_RETRAIN_PILOT_ADD2 - quyet dinh MASTER ve cac cong ghep du lieu (K) va ledger (G-L) - 2026-11-21 ~11:50 +07
Bo sung PREREG_RETRAIN_PILOT.md (c796c7b3) + ADD1 (c471c851). Viet TRUOC khi co bat ky so PnL / sim nao cua model moi (moi chi co:
p15 T1 da train + parity; P-N1, P-N2 PASS; net015 T1 dang train; CHUA co S1 T1, CHUA co chain N, CHUA co sim).
## 1. Hien trang (v12/RETRAIN_PILOT_RUN.progress dong 39, 47)
- K (rt-splice): feat_v2 K1/K2/K4 PASS. Tool1: file DEV Q2 ket thuc 2026-06-30 23:45 UTC (bien UTC), Vision Q3 bat dau 2026-07-01 00:00 UTC
  -> lien tuc, khong chong, khong ho; nhung tieu chi viet trong prereg "DEV max < S3" (S3 = 07-01 00:00 +07) FAIL theo chu. Vision Q3 Tool1
  co 25 102 khoa (ts, sym) TRUNG -> K1 FAIL. Nhan: DEV Q2 ket thuc 06-30 16:45 UTC (bien +07), Vision Q3 bat dau 07-01 00:00 UTC -> HO 7 h 15'
  (29 moc 15') -> K2 FAIL.
- G-L (ledger DEV dung lai): 6 928 308 = 6 928 308 dong; 11/12 cot trung tuyet doi; cot g1lite lech 1 289 373 dong, max 7,6e-8 (ban cu
  float32, ban moi float64); nhan S1 rel5 trung 100 %.
## 2. Quyet dinh
A2-1 Diem noi Tool1 = moc dau tien cua file Vision (2026-07-01 00:00 UTC), KHONG phai S3. Tieu chi K sua thanh: max ts DEV < min ts Vision
     (khong chong) VA khong ho tren luoi 15'. Hien trang: PASS. Ly do: bien file DEV theo UTC la dac tinh cua nguon; viec chong lan thoi gian
     voi OOS duoc chan boi assert train (max train_ts < cut - purge) chu khong boi diem noi.
A2-2 Khoa (ts, sym) trung trong Tool1 Vision Q3 (25 102): (i) T1 KHONG train tren file nay (train chi DEV < S3 - 72 h) -> khong anh huong model
     T1; (ii) chain N du doan Q3 dung DUNG duong du lieu cua Lane L (P-N1 da PASS trung byte) -> giu nguyen de so sanh cap; (iii) T2 (train co
     Q3 Vision): LOAI TOAN BO cac dong co khoa (ts, sym) trung (ca hai ban) khoi tap train Tool1 / nhan / ledger, ghi so dong loai + danh sach
     symbol vao manifest; sau khi loai K1 phai PASS. Bao cao: cac khoa trung thuoc symbol nao (ky vong: nhom 8 id dung chung cua mapper tu
     2026-07-09). Neu ti le dong bi loai > 1 % tap Q3 hoac symbol bi loai > 12 -> DUNG, bao MASTER.
A2-3 Lo nhan 7 h 15' (2026-06-30 17:00 -> 23:45 UTC): CHAP NHAN, khong noi suy, khong lay nguon thu ba. T1 khong bi anh huong (nhan train
     < S3 - 72 h tu DEV). T2: 29 moc x so symbol thieu nhan o dau Q3 - ghi so dong thieu vao manifest. OOS noi bo cua S1 T1 (chi mo ta) thieu
     7 h dau Q3 - ghi chu.
A2-4 G-L: ep kieu cot g1lite ve float32 (dung kieu cua ledger tham chieu cand_dev_x1.parquet) cho TOAN BO ledger moi, roi so lai: yeu cau 12/12
     cot trung tuyet doi tren cac dong ts < S0 - 72 h. Khong trung -> DUNG. Kiem dau-cuoi bo sung (bat buoc): chay lai S1-A (X1_CUT=20251001)
     bang ledger MOI (phan DEV, sau ep kieu) -> sha256 JSON phai == cc0924f1...; khong trung -> DUNG.
A2-5 Sau A2-1..A2-4: tiep tuc 4d / 4e / 4f va cac buoc con lai toi STOP-2. Moi thu khac giu nguyen prereg + ADD1.
