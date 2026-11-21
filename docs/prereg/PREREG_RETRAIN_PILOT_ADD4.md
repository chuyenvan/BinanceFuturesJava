# PREREG_RETRAIN_PILOT_ADD4 - DINH CHINH con so tham chieu o muc 16(b) - 2026-11-21 ~13:00 +07 - TRUOC khi co bat ky so Lane N nao
Phat hien khi tu kiem script cham tren Lane L vs Lane L (rt_score_n.py selftest, v12/RETRAIN_PILOT_RUN.progress 12:48:50):
- Muc 7 + D5 dinh nghia ROI_Q3(s) = SigmaPnL_Q3(s) / E_start_Q3(s) (PnL cac lenh DONG trong Q3 chia equity dau Q3).
- Con so "ROI_Q3 Lane L = 4,51 %" ma MASTER ghi o muc 16(b) la ROI MTM (E_end / E_start - 1) lay tu bang HO5, KHONG phai dinh nghia D5.
  Theo dung dinh nghia D5, Lane L Q3 = 5 205 / 166 758 = 3,12 % (trung binh 8 seed; script cham tai lap).
DINH CHINH: cau "mean ROI_Q3 Lane N phai >= ~3,51 %" o muc 16(b) la SAI so tham chieu; theo cong thuc (KHONG doi) nguong tuong ung la
  mean ROI_Q3,N (dinh nghia D5) >= ~2,12 % khi sd(d) ~ 0. Cong thuc H-NI o muc 7 GIU NGUYEN nhu da commit (c796c7b3); khong doi luat,
  khong doi dinh nghia. ROI MTM cua hai lane van duoc bao cao trong bang mo ta (muc 7 "Mo ta").
Thoi diem: sim Lane N dau tien (s123) vua duoc push 12:56, chua co output; chua ai doc so Lane N.
