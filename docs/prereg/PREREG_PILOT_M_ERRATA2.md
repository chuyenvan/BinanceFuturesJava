# PREREG_PILOT_M_ERRATA2 - lam ro 3 diem cua ERRATA1 truoc lan cham chinh thuc dau tien
Commit boi MASTER 2026-11-25 14:56 +0700. Ap cho PREREG_PILOT_M 2a21fe35 + ERRATA1 c0f35f3c, moi ngay cham tu D = 2026-11-24.
Trang thai: CHUA co lan cham chinh thuc nao (v12/pilot_m/ chua ton tai). Nguon: 3 de nghi cua DEV cong cu vong 2 (v12/PILOT_M_TOOL_DEV.md,
muc VONG 2), phat sinh khi cai ERRATA1 va chay thu ngay 2026-11-21/22/23; khong ai doc / dem du lieu >= 2026-11-24 07:00 +07.
Bao cao ngay ghi 'prereg=2a21fe35+E1+E2'.

F1 (ERRATA1 E2 (d), lam ro cau "thoi diem cuoi cua cron log da doc"): doan cuoi ngay tinh toi min(D+1 07:00 ; thoi diem CHAM). Thoi diem
   cham = luc chay bo cham (khong phai thoi diem dong cuoi trong file). Ly do: neu lay dong cuoi trong file thi monitor chet khong bao
   gio sinh khoang trong. Lan cham chinh thuc chi chay SAU D+1 07:10 +07.
F2 (ERRATA1 E1 (S1), sua): co che: budget leg nhan tierMultiplier trong {1,2 ; 1 ; 0,5} (C3LiveEntry :268) va log KHONG in tier => C_ngam
   cua leg tier 1,2 co the toi 1,2 x C_eff.
   (S1) r_cap = C_ngam / C3_CAPITAL > 1,2 x (1 + 1e-6) => VI_PHAM (DO).
   (S1b) 1 + 1e-6 < r_cap <= 1,2 x (1 + 1e-6) => VANG "TIER" (khong phan biet duoc leg tier 1,2 hop le voi loi vuot von tu log; ghi so leg).
   (S2)(S3) va ngoai le TIER / AVAIL cua ERRATA1 giu nguyen.
F3 (ERRATA1 E13, lam ro pham vi): E13 (flag NA = OFF) CHI ap cho M-T. K4 GIU NGUYEN: ngay co dong co "flag=NA(->OFF)" (khong co gia tri
   ALT_EW cho ngay do) => K4 VI_PHAM (VANG). Ly do: MIEN_X14 (ADD2) kem dieu kien MASTER kiem X14 hang ngay; co NA la X14 mat du lieu dau
   vao, can bao owner du time-stop van chay dung theo OFF.
