# MASTER_NOTE FOREX G2 + G4 (nghien cuu tren giay) - 2026-11-27 11:06 +0700
Prereg PREREG_FX_G2 / G4 (915d7a1a) + ERRATA4 (3426fc3a). HOLDOUT 2020-2026 KHONG mo. Ca hai da chay that + A1 XAC NHAN ket qua.
G2 - trend theo chuoi thoi gian + loc gia tri REER: KHONG DAT. Cau hinh chon bang TRAIN (L12 + loc 10 %; Sharpe TRAIN 0,56 [in-sample];
 1975-89: 0,76; 1990-2005: 0,38): WFO 2006-2019 Sharpe -0,39; CAGR -3,0 % / nam; maxDD 43 %. 12 cau hinh WFO Sharpe tu -0,39 den +0,04,
 trung vi -0,09. Doi chung dich vong p = 0,48. D1..D6 deu khong dat. Trend suy giam dan: 0,76 -> 0,38 -> am.
G4 - mua sau cu sap / ban sau cu vot tren nen 1 phut (4 cap, du lieu Kaggle CC0, 2005-2019): KHONG DAT. Cau hinh chon: ban sau cu vot 60
 phut / 4 sigma / time-stop 4 h: WFO 2013-2019 -3,2 % / nam; Sharpe thang -2,9; 2 163 lenh; -4,2 bp / lenh sau phi; -1,2 bp / lenh TRUOC phi.
 Ca 12 cau hinh am ca truoc phi (-0,6 den -1,4 bp / lenh). p dich vong 0,92.
 Giai phau (A1, mo ta): chi giu 60 / 240 phut sau su kien (khong SL / trailing): phia mua sau sap WFO -1,0 / -1,8 bp; tuc KHONG co hoi phuc
 o muc gop, gia con hoi di tiep theo cu sap. Chi phi khu hoi 0,7 bp (EURUSD) den 3-3,8 bp (cap khac) => can hieu ung +1..+5 bp moi hoa von.
He qua: phuong phap loi cua he crypto (mua sau cu sap) KHONG chuyen sang forex G10 trong ngay duoc: bien dong nho so voi phi va khong co
hoi phuc. Bon nghien cuu forex (carry + gate, COT, trend + REER, mua sau sap) deu khong dat tren WFO. Khong mo holdout.
