# PREREG_RETRAIN_PILOT_ADD5 - sau audit doc lap, TRUOC khi cham Lane N - 2026-11-21 ~13:40 +07
Bo sung PREREG_RETRAIN_PILOT.md (c796c7b3) + ADD1..ADD4. Audit: v12/A1_RETRAIN_T1.md - PASS-WITH-MINOR: khong ro ri du lieu o ca 3 model
(p15 T1 va S1 T1 duoc auditor train lai doc lap -> TRUNG BYTE; net015 theo log kernel + NET-EQ); day noi Lane N dung (pred / bins kiem
byte; thu tu bins 0701 la cua S1 T1); script cham dung dinh nghia muc 7 + ADD4 (selftest + thu pha). Trang thai luc viet: 8/8 sim Lane N
COMPLETE va qua kiem chung KHONG lo PnL (rt_nchk 8/8); CHUA ai doc so PnL / equity / ROI cua Lane N.
A5-1 [F1 - BAT BUOC truoc khi cham] rt_score_n.py them assert (sua ha tang, khong doi dinh nghia): (i) check_n.json PASS 8/8 va check_l5.json
     PASS 8/8; (ii) dong Update dung lam E_start co ngay == 20260701 o CA hai lane, moi seed; thieu -> DUNG, khong lay ngay ke tiep.
     Chay lai selftest L-vs-L (d = 0) + thu pha "xoa dong Update 0701" (phai DUNG) truoc khi cham Lane N; ghi sha256 moi.
A5-2 [F2] Assert "so dong train >= model truoc" cua muc 3 khong duoc cai trong wrapper. Do tay: S1 12 787 169 >= 6 911 775 (dat); net015
     48 429 620 >= 39 354 754 (dat); p15 T1 2 889 607 < 2 889 623 cua b68563fe - thieu 16 dong DO mep +07 (15 dong roi vao purge + 1 dong
     ts = S3) theo D3. MASTER ghi nhan: khong phai loi du lieu, khong train lai; voi p15 nguong nay tinh theo mep +07.
A5-3 [F5c - khai bao TRUOC] Bang MO TA bo sung (khong vao luat): tach Q3 thanh 2026-07-01..07-09 va 2026-07-10..09-30 (truoc / sau khi du
     lieu gate Vision Q3 dinh loi mapper 8 id) cho ca hai lane: so lenh, SigmaPnL, so phut gate PASS. Cung voi bang theo thang cua muc 16(d).
A5-4 [F3, F4] Ghi nhan: md5 score_l5.py trong prereg la ban .bak1 (diff chi o check()); run.py Lane N khac Lane L o CFG gom tag, dataset,
     pred26_md5, bins26_sha 0701, unseal_ref (U2) - chap nhan.
A5-5 [F5 a, b, d - gioi han dien giai, ghi vao bao cao ket qua] Lane N khac Lane L ngoai 3 model o: gate rolling tron ti so model cu / moi
     trong 90 ngay (khong reseed, P10); S1 T1 hoc 45,1 % dong tren feature Vision (cung nguon voi luc suy luan Q3) con S1 live chi hoc DEV;
     8 seed ~ 1 mau (ROI D5 Lane L 3,1214-3,1217 %). H-NI vi vay la so sanh DIEM, khong phai kiem dinh thong ke.
A5-6 [F9 - an toan] Truoc khi lam bat ky kernel sim nao tiep theo: chay jar_sec_check tren ban local cua jar sim cc0f9d11 va ghi ket qua;
     neu jar co key that -> DUNG moi kernel, bao MASTER ngay (xu ly bao mat truoc).
A5-7 Sau A5-1: duoc cham Lane N theo DUNG muc 7 (H-E0, H-NI theo D5, H-DD) va DUNG tai STOP-3.
