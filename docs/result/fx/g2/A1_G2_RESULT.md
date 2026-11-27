# A1_G2_RESULT - audit ket qua FX G2 (chay that, cutoff 2019-12-31) - 2026-11-27
sha kiem khop: 4 code g2 + 3 g1 = ban audit; EVAL_G2.md 43768470...dd73; EVAL_G2.json 16595629...c04.
Phuong phap: tin hieu + loc + trong so + so sach DOC LAP cua A1 (tu parse csv); Sharpe x sqrt(dong/nam), CAGR nam = ngay/365,25 (nhu report).

## KET LUAN: XAC NHAN. "KHONG DAT" la DUNG (D1-D6 deu False).

## 1. Tinh lai vs report - ca 12 cau hinh khop toi 3 chu so (TRAIN, 75-89, 90-05, WFO, 06-08, 09-12, 13-19)
| cau hinh | TRAIN Sharpe [in-sample] A1 / report | WFO Sharpe A1 / report | WFO CAGR | WFO maxDD |
|---|---|---|---|---|
| L12-V10 (chon) | 0,556 / 0,556 | -0,391 / -0,391 | -3,03 % / -3,03 % | 43,42 % / 43,42 % |
| L12-F0 | 0,491 / 0,491 | -0,341 / -0,341 | -2,51 % / -2,51 % | 37,71 % / 37,71 % |
| L3-V10 | 0,368 / 0,368 | 0,040 / 0,040 | 0,04 % / 0,04 % | 26,71 % / 26,71 % |
Chuoi ngay L12-F0 cua A1 vs sim: lech toi da 1e-15 tren 11 739 ngay. Luat chon: Sharpe TRAIN cao nhat = L12-V10 (0,556; ke tiep C-V10 0,523): DUNG.
D1 -0,391 F; D2 p 0,48 F; D3 43,4 % F; D4 1/12 cau hinh CAGR WFO > 0 (L3-V10) F; D5 bo 9/168 thang -54,84 % F; D6 x2 Sharpe -0,543, CAGR -4,08 % F.
Hop le: chuoi ket thuc 2019-12-31; WFO 2006-01-02..2019-12-31.

## 2. Tay 2008-10, L12-F0
So tai cuoi thang khop 2008-10-01 (tin hieu 30/9): long JPY 0,123, CHF 0,117; short EUR 0,124, GBP 0,124, CAD 0,132, AUD 0,082, NZD 0,093, NOK 0,093,
SEK 0,111 (sum|w| = 1). Ty gia 30/9 -> 31/10: AUD -16,8 %, NZD -13,1 %, CAD -12,8 %, NOK -12,2 %, SEK -10,7 %, EUR -9,9 %, GBP -9,2 %, CHF -4,1 %, JPY +7,8 %.
MTM: CAD +1,70, AUD +1,45, SEK +1,29, EUR +1,20, NZD +1,20, NOK +1,15, GBP +1,14, JPY +0,96, CHF -0,48 = +9,62 %; swap (gom margin) -0,26 %; phi -0,01 %.
Tong +9,35 % = sim +9,3455 % (khop).

## 3. p dich vong
A1 300 luot, seed 777: real (chay rieng WFO) -0,3816 (= report); n_ge 139, p = 140/301 = 0,465 (report 0,4835). Ben vung, xa 0,05.
Luu y: trung vi dich vong -0,40 va iid -0,33 - margin 1 %/nam tren gross 1 + phi tu no keo Sharpe ~ -0,25..-0,3; chien luoc that ~ ngang ngau nhien.

## 4. Mo ta cho MASTER (ngoai tieu chi)
- maxDD 43,4 %: dinh 2008-12-05 -> day 2014-10-16. Lo DEU nhieu dong tien (% equity tai dinh): CHF -8,7, EUR -8,6, NOK -7,8, SEK -6,0, GBP -5,5,
  CAD -4,7, AUD -2,4, NZD -1,9, JPY +2,4. Khong phai loi so sach / don bay an: gross WFO trung binh 1,001, toi da 1,16 (troi trong thang giu so don vi);
  chuoi khop sim tung ngay. Nguyen nhan: 9 dong tien deu la "USD vs phan con lai" (mot nhan to), trend 12 thang dao chieu lien tuc 2009-2012.
- Theo nam L12-V10: 2006 -9,0 %; 2007 +5,8; 2008 +9,0; 2009 -14,7; 2010 -14,3; 2011 -7,7; 2012 -2,8; 2013 -3,8; 2014 +1,5; 2015 +7,1; 2016-2019 am nhe.
  => lo tap trung 2009-2012 (-34,4 %, Sharpe -1,16), nhung 2013-2019 cung am (Sharpe -0,13): khong chi do mot giai doan.
- Suy giam: Sharpe L12-V10 1975-89 0,758 -> 1990-2005 0,384 -> WFO -0,391 [hai so dau in-sample]; khop Neely-Weller-Ulrich (trend FX mat dan tu 1990s).
- Loc REER: o L12 lam TE hon (V10 -0,391 vs F0 -0,341); nhieu cau hinh khac cai thien nhe nhung deu quanh 0.

## 5. Duoc noi / khong duoc noi voi owner
DUOC: "KHONG DAT" tat ca D1-D6; WFO Sharpe -0,39, CAGR -3 %/nam, maxDD 43 %; chi 1/12 cau hinh duong WFO; p 0,48 (khong khac ngau nhien);
suy giam trend FX qua cac thap nien (mo ta, so TRAIN kem [in-sample]); HOLDOUT khong mo.
KHONG DUOC: trich Sharpe TRAIN 0,56 / 0,76 (1975-89) nhu ky vong; neu L3-V10 / C-V20 (WFO 0,04 / 0,03) la "cau hinh tot" - chon sau khi thay so,
va van ~0; "loc gia tri co ich"; de nghi doi lookback / nguong roi thu lai tren cung du lieu.

## CHUA kiem
Doi chung iid / mua-giu (chi doc so); bang % loc.
