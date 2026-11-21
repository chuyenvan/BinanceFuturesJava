# OWNER_DECISION_PILOT_1121 - quyet dinh cua owner sau khi RETRAIN T1 FAIL (2026-11-21 ~15:40 +07, trong chat voi MASTER)
Boi canh: docs/result/retrain_pilot_t1/RESULT_RETRAIN_T1.md (932770e5): 3 model train lai (cut 2026-07-01) lo tren 2026Q3 (ROI -6,44 % vs
model live +3,12 %) => theo PREREG_RETRAIN_PILOT muc 7: PILOT bi chan, khong tune. MASTER trinh 3 lua chon A / B / C va khuyen nghi A.
Owner tra loi (nguyen van, bo dau): "tam thoi pilot model cu. retrain can lam tung model nhu p/a A ban noi nhung neu lam tung model thi
lam sao de tinh chinh duoc tham so theo model nhi".
## Dien giai (MASTER ghi; owner co the sua)
Q1 PILOT voi 3 model DANG LIVE (p15 fold_20 8ec99757, S1 s1a2x1_cut20251231, net015 g015x26_f15_cut20251231) - TAM THOI. Day la quyet dinh
   khau vi rui ro cua owner, GO dieu kien "phai train lai truoc pilot" (luat 3 PREREG_DIAG_NOTRADE_1117; R1 PREREG_HO5 "van phai train lai";
   bang quyet dinh muc 7 PREREG_RETRAIN_PILOT). Ky vong dung cho pilot = HO5 Lane L OOS: ROI 10,95 % / 183 ngay (~23 %/nam), CI rong.
   Rui ro da noi ro: model gia dan (p15 train toi 2026-03-31; S1 / net015 toi 2025-12-31), chua co cach lam moi model da duoc chung minh.
   Moi dieu kien KY THUAT khac truoc pilot (jar, ops, gate, kiem toan script, owner tu chay) GIU NGUYEN.
Q2 RETRAIN theo phuong an A (chan doan tung model). Mo rong pham vi dung du lieu 2026 (bo sung HOLDOUT_UNSEAL_2026_1121):
   U4a 2026Q3: chay lai Lane voi TUNG model moi thay rieng (va bien the hieu chuan lai bo dem gate) - CHAN DOAN, khong chon cau hinh theo PnL Q3.
   U4b 2026-10-01 -> ngay cuoi du lieu: kiem MOT lan cho MOT cong thuc ung vien duy nhat (prereg rieng truoc khi chay).
Q3 Cau hoi cua owner "tinh chinh tham so theo model": MASTER tra loi trong chat 21/11 - khong tune tham so chien luoc theo model tren quy
   kiem chung; tham so phu thuoc thang diem model = HIEU CHUAN LAI theo cong thuc co dinh tu diem truoc moc train; neu can quy tac chon tham
   so theo model thi quy tac do la mot phan cua cong thuc train va phai duoc kiem tren nhieu quy qua khu truoc.
