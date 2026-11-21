# PREREG_RETRAIN_PILOT_ADD3 - quyet dinh MASTER sau bao cao STOP-2 (mot phan) - 2026-11-21 - TRUOC moi so sim / PnL cua model moi
Bo sung PREREG_RETRAIN_PILOT.md (c796c7b3) + ADD1 (c471c851) + ADD2 (a6ab4186). Bao cao: v12/RETRAIN_PILOT_RUN.md muc "BUOC 3-4".
Hien trang: p15 T1, net015 T1 (NET-EQ trung byte, 3c/3d), P-N1, P-N2, chain N da PASS. S1 T1 CHUA co. Chua co sim Lane N nao.
A3-1 G-L: sau khi ep float32 (A2-4) cot g1lite van lech 140 932 dong. Nguyen nhan da xac minh: ledger tham chieu tinh g1lite bang SO HOC
     float32 (numpy tren Oracle); kernel Kaggle tinh float64 roi moi ep. QUYET DINH: tinh lai g1lite bang so hoc float32 theo DUNG cong thuc
     x1_ledger cho TOAN BO dong cua ledger moi (ca DEV lan Q3), roi ap cong G-L: 12/12 cot trung tuyet doi voi cand_dev_x1.parquet
     (sha256 41fb8269...) tren dong ts < S0 - 72 h. Khong trung -> DUNG. Sau do chay S1-A (X1_CUT=20251001) bang ledger moi -> sha256 JSON
     == cc0924f1...; khong trung -> DUNG. Day la tai lap SO HOC cua pipeline tham chieu, khong doi cong thuc / feature / nhan.
A3-2 Lam ro nguong A2-2 cho T2: dem theo ID mapper dung chung (khong theo ten). Hien trang do duoc: 25 102 khoa trung = 50 204 dong = 0,92 %
     tap Tool1 Q3, dung 8 id 843-850 (16 ten: BNC/SOXS, SNOW/ZHIPU, PANW/SKHY, MINIMAX/VRT, APP/SHAZ, FWDI/TZA, MUU/XBI, GEV/SOFI) - dung
     nhom da du kien trong A2-2. Nguong DUNG giu: > 1 % tap Q3 HOAC > 12 id. T2 loai toan bo dong cua cac khoa trung nay.
A3-3 P14b (loc file nhan theo cut cua fold + assert train < tr_cut): NET-EQ PASS (model_f22 sha256 d91fe741... trung byte giua ban P14 va
     P14b) -> commit cung addendum nay (research/pipeline/g015_net_train.py md5 7d2b6e8a5780f5dddb8d406c8d3078b5). T2 dung ban nay.
A3-4 Trinh tu tiep: 4d / 4e / 4f -> neu MOI cong cung PASS: duoc PUSH 8 sim Lane N (buoc 5) va chuan bi script cham; NHUNG KHONG chay cham,
     KHONG doc bat ky so PnL / equity nao cua Lane N cho toi khi (i) audit doc lap ve ro ri du lieu T1 + day noi Lane N + script cham PASS va
     (ii) MASTER cho phep. Kiem chung output sim truoc khi cham chi duoc dung cac phep so sanh khong lo PnL Q3 (md5 dau vao, so ngay, dong
     printDone / Update co end < 2026-07-01 trung Lane L).
