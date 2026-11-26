# A1_G1_CODE - audit doc lap code FX G1 (carry G10 + gate rolling) - 2026-11-27
Auditor: A1 (khong phai DEV). Khong tinh loi suat / Sharpe tren du lieu that; khong doc du lieu >= 2020-01-01; khong sua code goc.

## KET LUAN: PASS-WITH-MINOR (khong co loi CHAN)
sha256 da kiem khop: load_g1.py c49541a2...ea74c2, sim_g1.py 1f0e411f...6096f8, eval_g1.py 42d71b7a...cc1f, test_g1.py 4a77c0c7...a2a.

## 1. Doi chieu prereg + ERRATA (doc code)
- Universe theo thang, lai suat m-1 (load_g1.py:151-160), gap > 3 ngay, EUR tu 1999 (115): DUNG.
- Tai can bang = dong cuoi thang co gia (149); xep hang d = r_i - r_USD (m-1), tie-break ma (sim_g1.py:100-103); 1/(2k), can 2k (124-145): DUNG.
- Gate: FX_VOL theo J2 (33-55), VIX lag 1 dong theo J4 (58-60), phan vi cua so [t-N nam, t) KHONG gom t (63-81), kiem moi dong, flat toi rebalance ke tiep, trigger dung ngay rebalance => khong mo (148-161), thieu lich su => OFF: DUNG.
- 12 cau hinh (19-29). Chi phi: EURUSD 0,8 pip, khac MAX(3 pip, 3 bp) khu hoi, mot chieu = 1/2, lenh do gate x2 (174-181, 280); margin 1 %/nam moi chan; x2 nhan doi spread + margin: DUNG (bao thu).
- Carry ngay lich /360 tren notional moi chan (229-231): DUNG. TRAIN/WFO/hai nua (eval_g1.py:19-22); chon bang Sharpe TRAIN, hoa -> k nho -> OFF (87-91): DUNG. Ngau nhien 500, cung k/gate/chi phi/engine (109-117). D1-D7 (133-134), D6 theo J3 (81-84), D5 ghi chu khi OFF; nhan [in-sample]; trung vi 12; doi chung a/b/c; H1 mo ta: DUNG.
- Cutoff: moi duong nap (DEX, IR3TIB, VIX, ECB) bo dong > cutoff truoc khi parse (load_g1.py:69-72, 176); G1Data assert; >2019-12-31 can token owner. Khoa --real I_HAVE_A1_PASS o sim/eval main. Khong print; out/ chi co 2 log test; test h tat dinh.

## 2. Tu kiem doc lap tren du lieu that <= 2019-12-31 (code rieng, csv tu parse)
- Lich: trung khop. Vi the (universe + xep hang + trong so + dong T): 312 thang x k{2,3} = 624 thang-cau hinh 1993-12..2019-11, 0 lech. Mau k2: 1994-01 L NOK,SEK S CAD,AUD (n6); 1999-01 L GBP,NOK S EUR,SEK (n7); 2002-05 n9 co JPY; 2008-10 L AUD,NZD S JPY,CAD; 2015-01 L AUD,NZD S CHF,SEK.
- FX_VOL tu tinh: max lech 1,3e-15, mau NaN trung. Gate trig hang ngay 2005-2012 (2086 dong): FXVOL q80 N3 371/371, FXVOL q90 N10 350/350, VIX q90 N3 326/326 (+1993-01..1994-06): 0 lech.
- Trang thai mo/flat hang ngay k2 2005-2012 (logic rieng vs gross>0 cua sim): FXVOL q80 N3 0 lech; FXVOL q90 N10 0 lech; VIX 1 lech = 2008-01-01 (trigger roi vao ngay nghi khong co gia, sim dong o ngay hop le ke tiep - dung muc 3).
- Chieu yet gia 9 ma: ten FRED + muc gia (DEXUSAL 0,79; DEXJPUS 106) khop C1; dau 2008-09-30 -> 2008-10-31: long AUD, NZD, GBP, EUR, CAD, CHF, NOK, SEK AM; long JPY DUONG (yen tang thang 10/2008) - dung thuc te, mine = sim.

## 3. So sach tinh tay (kich ban gia tong hop, 4 ccy, 2 long 2 short, 3 thang, gate dong 2000-02-15, mo lai 2000-02-29, dao vi the 2000-03-31)
Vong lap ngay doc lap tu gia RAW: equity cuoi sim = tay = 1,003887124193 (lech 4e-16); x2: 1,001248233886 (lech 9e-16). Turnover moi su kien khop (1,0 / 0,99761 / 1,0 / 1,001463). gross*equity tai T0 = 1 (gross 1 cua equity truoc phi), gross trong luc gate = 0, 4 lenh dong co co gate (x2). Max gross 1,0019 (troi trong thang do giu so don vi - C5), khong don bay an.

## 4. Mutant (20, chay tren ban copy mktemp; test goc fails=0 tren copy)
BAT (13): M01 lai suat m thay m-1 (b,e); M03 VIX cung ngay (d); M04 dao chieu CAD (a); M05 bo margin (c); M06 gate khong x2 (d); M07 1/k (c,e); M11 cutoff bo qua (f); M12 bo san 3 bp (c); M13 carry bo dau short (c); M14 gap >5 (e); M16 bo kiem gate trong thang (d); M17 bo gate tai ngay rebalance (d); M18 cua so N-1 nam (d).
LOT (6): M02 phan vi gom t (test b vo hieu: tai 2008-10-15 v_t da la max cua so nen doi v_t=1e6 khong doi q); M08 chon bang Sharpe WFO; M09 ngau nhien khong qua gate; M10 D6 bo thang te nhat; M15 kich ban x2 khong nhan; M19 nguong D2 0,10. M20 (cho EUR truoc 1999) la mutant tuong duong (DEXUSEU bat dau 1999).
=> Code DUNG cho ca 6 diem lot (doc code + tu kiem phan 2), nhung TEST khong bao ve chung.

## 5. Loi (khong CHAN)
NHO-1 test gap (test_g1.py:141-146, 434-444): them unit test (a) q_t == np.quantile(v[[t-N,t)]) truc tiep tai ngay v_t < q_t; (b) select() tren rows gia co TRAIN/WFO nguoc nhau; (c) random goi simulate voi dung gate (assert gate_close co trong lich ngau nhien); (d) drop_best_months tren chuoi tay; (e) cost_x2 khac cost_x1; (f) bang nguong D1-D7. Nen lam truoc khi chay that (re, < 30 phut), khong doi logic.
NHO-2 p khong cong 1 (eval_g1.py:117): theo nghia den prereg "ti le"; de nghi bao kem (n_ge+1)/(N+1) (mo ta).
NHO-3 C4 carry dung lai suat m-1 co dinh suot thang giu (cu 1-2 thang): dung prereg muc 6, nhung trong chu ky ha lai suat (2001, 2008-09) phong dai carry cua chan long lai cao => CO THE LAM DEP. De nghi MASTER errata: bao kem (mo ta) carry tinh bang lai suat cua chinh thang giu (ke toan, khong phai tin hieu).
NHO-4 Phi vao lenh dau tien (1993-12-31) nam ngoai lat TRAIN (eval_g1.py:28-31) - khong dang ke.
NHO-5 state[] gan cho dong nr truoc khi xu ly su kien (sim_g1.py:240) => % thoi gian gate lech 1 dong / lan; chi bao cao.
NHO-6 Khi khop tre (thieu gia tai T), carry cua vi the cu dung diff moi (sim_g1.py:252-254); 1994-2019 khong co gap > 3 nen khong dang ke.
NHO-7 Khoa --real chi o CLI; evaluate()/simulate() van goi duoc tren du lieu that (quy trinh, khong ky thuat).
NHO-8 Neu Sharpe ngau nhien NaN se khong dem vao n_ge (lech co loi) - kha nang thap; nen assert khong NaN.

## 6. CHOICES
C4: xem NHO-3. C5 (giu so don vi): chuan cho tai can bang thang, khong lam dep. C10: khop prereg (khong mo khi trigger ngay rebalance). C12 D4/D6/D7 dung CAGR / gop: khat khe hon so hoc => khong lam dep. C13: NHO-2. C6 x2 gom margin: bao thu. C8 = J4. C2/C9 ngay nghi: VIX/FX gate co the trigger ngay nghi, khop ngay hop le ke tiep - dung.

## 7. CHUA kiem
Cong thuc metrics (Sharpe/maxDD/Calmar/skew) chi doc code, chua doi chieu tay; ecb_flag_dates; doi chung mua-giu bang tay; noi dung report_md; PnL that 2008-10 (J6, de A1-results).

## Vong 2 (sau ERRATA3 K1/K5/K6, 2026-11-27)
sha256 da kiem khop: load_g1.py f466ace5...fe99c, sim_g1.py a99ff7aa...4e7, eval_g1.py 61efccfa...ded, test_g1.py 7a87c264...37b.
- Doc phan doi: duong chinh run_sim voi carry_rates="signal" (mac dinh) giu nguyen cong thuc vong 1; nhanh K5 (_holding_diff, sim_g1.py:190-198, 246-251) chi chay khi carry_rates="holding"; evaluate goi K5 SAU khi tinh D/verdict, chi ghi vao k5_carry_holding_month (eval_g1.py:164-176) - khong vao tieu chi.
- Chay lai tu kiem doc lap (code moi viet lai): vi the 624 thang-cau hinh 0 lech; trig gate 2005-2012 0 lech (FXVOL q80 N3 371, VIX q90 N3 321, FXVOL q90 N10 350); lich gate_close va co gate tai rebalance k2 khop tap hop (11/10/12 va 16/14/14, symdiff 0). Khong goi simulate tren du lieu that (da khoa).
- So sach tinh tay: equity cuoi 1,003887124193 (x2: 1,001248233886) = vong 1 (lech <= 2e-13 do lam tron 12 chu so), turnover giong; co hay khong co bang lai suat thi duong chinh khong doi; K5 cho so khac (1,003393) nhu ky vong.
- K1: p = (1 + n_ge)/(N + 1), NaN dem la >= that (eval_g1.py:100-103) - DUNG, bao thu. Nguong D1-D7 la hang so (:26-30).
- Khoa: simulate() va evaluate() tren du lieu tu load() bi PermissionError khi khong co token (da thu). Test a-i PASS (fails=0) tren ban copy. Bo qua duoc chi bang cach cu y dat data.is_real=False hoac tu dung G1Data - khoa quy trinh, chap nhan.
- Mutant (test c,d,i): BAT 8/10 - M02 phan vi gom t, M08 chon bang WFO, M09 ngau nhien khong gate, M10 D6 bo thang te nhat, M15 x2 khong nhan, M19 D2 0,10, M21 p khong +1, M24 NaN khong dem. LOT 2: M22 (evaluate dung carry K5 cho duong chinh) va M23 (run_sim mac dinh "holding") - code hien tai DUNG (doc code + so sach tren), nhung khong test nao bao ve. NHO: them test du lieu tong hop co lai suat thay doi theo thang, assert ket qua chinh va D khong doi khi bat / tat K5.
KET LUAN CUOI: PASS-WITH-MINOR (khong co loi CHAN).
