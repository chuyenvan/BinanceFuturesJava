# A1 audit pilot_m_daily.py V4 (sau VONG 5 DEV)
A1 (Opus) 2026-11-26 ~13:50 +07. Ban: sha256 364ee37d866e5b2a1514d285fd4253ad75ce602629f38d98dbcd9370a9dd01f7 (chua commit). So voi 0ab2edded6db (A1 V3).

## VERDICT: PASS - duoc commit va dung cham chinh thuc D=2026-11-26. Khong co loi bat buoc. 2 de nghi test (khong chan).

## 1. Delta (doc tung dong, git diff 989a2531)
- B1 :1980 `a not in (None, '', '0')` - dung.
- C3d: run_state :724/:741 arm_ts/rst_ts luu (ms, seq); armed_at :1330-1332 nhan key (t, seq) dong TS/CLOS (:1411); unarmed_at :1335-1339 key = (due, FAR) (moi dong <= due ms, tuong duong ban cu). seq = thu tu doc dong (:560), events sap theo (t, seq) (:2102). arm_ts/rst_ts CHI dung trong chk_MT; I8/I9 dung first_arm / ev['armed'] - khong doi. Khong thay doi logic nao khac ngoai B1, C3d (+ README, test, mutant).
- ARM/RST cung ms: RST sau ARM => het arm (C3d DAT); RST truoc ARM => dang arm (C3e VP). ARM cung ms SAU dong TS => dong TS khong VP, dong CLOS sau do VP (C3c, 1 VP).

## 2. Test / mutant (chay TUAN TU tren 1 ban sao, sandbox <= 45 MB)
- pm_tests 417/417. DEV mutant 39/39 GIET.
- 13 mutant song cu cua A1 (dung lai theo code moi): 12/13 GIET; Y20b (arms[-1] <= r voi tuple) = TUONG DUONG (khong the trung (t, seq)).
- 6 mutant moi C3d/B1: GIET Z03 (RST chi so ms), Z05 (hoan B1). SONG: Z01 (key dong TS bo seq - ARM cung ms sau TS bi tinh), Z04 (RST cung ms TRUOC ARM van tinh reset) - lo test, ca pha C3c/C3e cua A1 giet duoc; Z02 (unarmed key (due,-1)) gan tuong duong (ARM dung ms due); Z06 (bo (c) cho khan_canh_bao) - lo test co tu truoc.
- Tong 53/58. De nghi (khong chan): them C3c (so_vi_pham=1) va C3e vao pm_tests; them ca 2 dong hop le lien tiep khan_canh_bao=1 => VP.

## 3. Ca pha: 22/22 dung (20 ca V3 + C3e + C12b khan=1 2 dong => van VP). C11, C12, C3d nay dung; C6 = VI_PHAM (gioi han da ghi README).

## 4. Hoi quy: D=24, D=25 (--max-ts "2026-11-26 07:00"): 31/31 muc trung (trang_thai, mau, so_vi_pham, so_kcd), bac XANH.

## 5. Lenh cham D=26/11 (chi code; KHONG doc du lieu D=26)
- Cu phap dung: `bash ~/claude_master/vz_e1_wt/tools/pilot_m/pilot_m_daily.sh 2026-11-26 --official --pilot-on-start "2026-11-26 12:21"` (ms_local nhan 'yyyy-mm-dd HH:MM' :86-92; --official cam --max-ts/--now/... ; tu choi truoc 27/11 07:10).
- pilot_on = 12:21:00 (<= 12:21:23 thuc te). KHONG duoc dung "12:22": banner 12:21:40 se ngoai khung [pilot_on; +60'] => K1 VP + c3_capital 5000 != 1000 gia.
- K1: banner 12:21:40 trong khung, c3_capital 5000 = exp_cap (t >= pilot_on); can dong "khoi phuc ... con 0 leg treo" (cua so [banner-60s; banner sau)) va "reconcile khoi dong XONG" sau banner. Doi chieu cac restart truoc 26/11 (16/11, 19/11 x4): moi restart dung 1 banner logger C3LiveRuntime, RECOV + XONG trong 1-2 s sau banner => khop. Khong thay VP/KCD gia chac chan.
- K2/R4: mien [12:21:00; dong TOM TAT hop le dau tien push=ON va C3_CAPITAL=5000] (<= 60'); truoc 12:21 ky vong 1000, sau dong do 5000; khoang trong (d) cat qua khung mien duoc bo qua. Khong thay gia.
- K5/R2: INCOMPLETE chi chap nhan fails trong 4 truong, moi gia tri >= 1440 - 20 x 1 = 1420; log_minutes=1440, log_max_gap_min <= 15 van bat buoc.
- M-S/R1: von lay tu banner_at (banner gan nhat truoc SUBMIT); banner 20/11 06:17 (1000) nam trong gstore (GLOBAL_FAMS doc ca dong ngoai cua so tu log cong don) => SUBMIT truoc 12:21:40 cham 1000, sau 5000 (dung prereg muc 4). Khong KCD gia.
- K3 streak ve 1 sau banner, K4 flag sau banner: da co nhanh restart. K6: 5 restart truoc (16/11, 19/11) 0 dong " ERROR " / KHAN quanh restart.
