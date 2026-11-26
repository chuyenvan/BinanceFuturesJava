# A1_G1_RESULT - audit ket qua FX G1 (chay that, cutoff 2019-12-31) - 2026-11-27
sha kiem khop: code 4/4 = ban audit vong 2; EVAL_G1.md 59ae915e...cc1f1; EVAL_G1.json 58b20a81...85be4.
Phuong phap: code so sach + vi the + gate DOC LAP cua A1 (tu parse csv, khong goi simulate/evaluate). Quy uoc: loi suat ngay tren moi dong lich FRED (ca ngay nghi), Sharpe = mean/std(ddof 1) x sqrt(so dong/nam = 260,9) (giong report; x sqrt(252) lech <= 0,003); CAGR = gop^(1/nam), nam = (ngay cuoi - ngay dau + 1)/365,25; maxDD tren equity gop ngay trong ky.

## KET LUAN: XAC NHAN. "KHONG DAT" la DUNG.

## 1. Tinh lai vs report (ca 12 cau hinh khop toi 3 chu so / 0,01 %)
| cau hinh | TRAIN Sharpe [in-sample] | TRAIN CAGR [in-sample] | TRAIN maxDD [in-sample] | WFO Sharpe | WFO CAGR | WFO maxDD |
|---|---|---|---|---|---|---|
| k2_FXVOL_q80_N3 (chon) A1 | 0,963 | 2,74 % | 7,84 % | 0,003 | -0,07 % | 13,46 % |
| report | 0,963 | 2,74 % | 7,84 % | 0,003 | -0,07 % | 13,46 % |
| k2_OFF A1 | 0,758 | 2,73 % | 6,40 % | -0,021 | -0,33 % | 22,72 % |
| report | 0,758 | 2,73 % | 6,40 % | -0,021 | -0,33 % | 22,72 % |
10 cau hinh con lai: khop het. Luat chon: Sharpe TRAIN cao nhat = k2_FXVOL_q80_N3 (0,963; ke tiep 0,875) - DUNG.
Hai nua WFO (Calmar): chon 0,010 / -0,039; k2_OFF -0,001 / -0,053 => D5 dung.
D1 0,003 > 0,3 F; D2 p 0,076 F; D3 13,46 % <= 25 % T; D4 3/12 cau hinh CAGR WFO > 0 (can >= 7,2) F; D5 T; D6 bo 9/168 thang tot nhat => -20,08 % F; D7 x2 Sharpe -0,201, CAGR -0,92 % F. => F F T F T F F, khop report.
Tinh hop le: chuoi ket thuc 2019-12-31, khong dong nao > cutoff; WFO bat dau 2006-01-02 (ngay lam viec dau 2006).

## 2. J6 - tay thang 2008-10, k2_OFF
Vi the giu trong thang 10/2008 dat tai 2008-09-30 (lai suat 2008-08): LONG AUD (d 4,55), NZD (5,44); SHORT JPY (-1,91), CHF (-0,58). LUU Y: brief MASTER ghi "short JPY, CAD" - do la so do dat cuoi 10/2008 cho thang 11.
Ty gia 30/9 -> 31/10 (USD/1 ngoai te): AUD -16,83 %, NZD -13,08 %, JPY +7,79 %, CHF -4,11 %. MTM moi chan 0,25 x thay doi: AUD -4,21 %, NZD -3,27 %, short JPY -1,95 %, short CHF +1,03 % => -8,40 %. Carry (d - 1 % margin, 31 ngay /360, notional troi): +0,17 % (AUD +0,067, NZD +0,087, JPY +0,021, CHF -0,009). Chi phi rebalance 31/10: -0,008 %. Tong -8,24 % = A1 day-loop -8,2396 % = "WFO worst_m" k2_OFF trong report (-8,24 %). KHOP.

## 3. p ngau nhien
A1 200 luot, seed khac (424242), cung gate FXVOL q80 N3 + chi phi: n_ge 15, p = 16/201 = 0,080 (report 0,076). Ben vung trong 0,05-0,10, khong <= 0,05.
Chu y dien giai: trung vi ngau nhien -0,33 (do chi phi + margin 1 %/nam moi chan va carry ngau nhien ~0); that 0,003. p ~0,08 chu yeu do "khong lo nhu ngau nhien", KHONG phai bang chung tin hieu.

## 4. Mo ta cho MASTER (ngoai tieu chi, nhan [mo ta])
| giai doan | chon: tong / maxDD | k2_OFF: tong / maxDD |
|---|---|---|
| 2006-2008 | -2,48 % / 12,10 % | -12,56 % / 21,96 % |
| 2008 rieng | -4,21 % / 4,22 % | -17,99 % / 19,74 % |
| 2009-2012 | +3,47 % / 7,91 % | +14,15 % / 7,91 % |
| 2013-2019 | -1,91 % / 6,96 % | -4,30 % / 11,75 % |
- Gate CO cat duoc cu sap 2008 (maxDD 2008 19,7 % -> 4,2 %) nhung dong cua trong pha hoi phuc 2009-2012 (+14,2 % -> +3,5 %) => WFO ~0.
- TRAIN dep vi chinh carry G10 kiem tien 1994-2005 (k2_OFF TRAIN Sharpe 0,76 [in-sample]); sau 2008 carry khong gate tu no ~0 (WFO -0,02; 2013-2019 am). Gate chon tren TRAIN nang Sharpe TRAIN 0,76 -> 0,96 nhung khong them gia tri WFO (trung vi 12 cau hinh -0,045). Nguyen nhan chinh: carry G10 suy giam sau 2008 (lai suat G10 hoi tu gan 0 => d nho, khong du bu chi phi + margin) cong rui ro chon cau hinh.

## 5. Duoc noi / khong duoc noi voi owner
DUOC: "KHONG DAT" theo tieu chi chot truoc; WFO Sharpe 0,003, CAGR -0,07 %/nam, maxDD 13,5 %; 3/12 cau hinh duong tren WFO; x2 chi phi am; HOLDOUT chua mo va khong nen mo; gate giam sut giam 2008 nhung bo lo hoi phuc (mo ta). So TRAIN chi kem nhan [in-sample].
KHONG DUOC: "gan co y nghia / p 0,076 gan 0,05"; "gate co hieu qua" (D5 dat nhung Calmar ca hai nua deu ~0 / am); trich Sharpe TRAIN 0,96 nhu ky vong; trich ban bo ngay co H1 (Sharpe 0,119) hay cau hinh WFO tot nhat (k3_FXVOL_q90_N3 0,151) - do la chon sau khi thay so; de nghi "chinh lai gate / doi tham so roi thu lai" tren cung du lieu.

## CHUA kiem
Doi chung mua-giu, ban K5 va H1 (chi doc so report); trung vi 12 (tinh nham tu bang: khop -0,045).
