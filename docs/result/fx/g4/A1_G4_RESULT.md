# A1_G4_RESULT - audit DOC LAP ket qua G4 (agent A1, 2026-11-27)
KET LUAN: XAC NHAN. "KHONG DAT" la DUNG.
- sha256 eval_g4.md ee0accf7... va eval_g4.json 432dff0f... khop.
- Code doc lap (khong goi sim/eval cua DEV): doc parquet filter ts < 2020-01-01 (assert), sigma = std gop ddof=1 cua r1 trong 20
  phien NY(17:00) truoc, N4/N3/rollover, vao close nen ke tiep, SL 2 / arm 1 / gap 0,5 x sigma60, TS 4h, check gia mo sau gap > 5 phut,
  chi phi 0,8 pip / max(3 pip, 3 bp), truot 0,5C cho SL/TS, x3 khi thoat roi rollover / dau tuan. KHONG tinh swap (lech nho).
## So tinh lai vs report (4 cap, WFO 2013-2019)
| | A1 S-60-4-4h | DEV | A1 L-60-4-4h | DEV |
| lenh | 2163 | 2163 | 2409 | 2409 |
| bp/lenh truoc phi | -1.21 | -1.21 | -1.04 | -1.04 |
| bp/lenh sau phi | -4.16 | -4.17 | -4.12 | -4.13 |
| tong (von) | -0.2250 | -0.2256 | -0.2479 | -0.2485 |
| Sharpe thang | -2.938 | -2.943 | -2.660 | -2.664 |
| ti le thang | 0.579 | 0.577 | 0.579 | 0.579 |
| payoff | 0.435 | 0.438 | 0.444 | 0.444 |
| SL/TRAIL/TS | 32.7/58.7/8.6 | 32.7/58.7/8.6 | 32.8/60.4/6.8 | 32.8/60.4/6.8 |
So lenh theo nam khop tung nam; tong theo cap khop (vd S: EURUSD -0.0344 vs -0.0343, GBPUSD -0.0700 vs -0.0701). Lech con lai ~0.5 bp
tong / ~0.002 ti le thang = swap (A1 bo). TRAIN: S -1.686 vs -1.689, L -1.750 vs -1.750; -1.689 la max cua 12 => luat chon dung.
D1..D7 = F,F,T,F,F,F,T kiem lai tu so: dung. D2 (p 0,92) A1 CHUA tu tinh lai.
## 3 lenh tinh tay (EURUSD, S-60-4-4h, mo phong A1 = khop tong DEV)
- TRAIL: vao 2013-02-05 16:29 UTC BID 1.35872, sigma60 10.80 bp; SL gia 1.36166, arm 1.35725; day 1.35715 (peak 11.55 bp); nguong
  trail 6.15 bp -> thoat close 16:42 1.35794 (5.74 bp). Ban 1.35868, mua lai 1.35798 => +5.15 bp sau phi.
- SL: vao 2013-01-17 08:48 1.33391, sigma60 10.23 bp, SL 1.33664; close 10:41 1.33668 => gop -20.77, sau phi+truot -21.67 bp.
- TS: vao 2013-07-11 19:18 1.31002, sigma60 11.07, peak 9.39 < arm; 23:18 close 1.30955 => gop +3.59, sau phi+truot +2.67 bp.
## Hop le
Max ts doc 2019-12-31 21:00; lenh vao trong cap-nam loai = 0; khong lenh TRAIN nam 2007/2008; WFO tu 2013-01.
## Giai phau (MO TA, ngoai tieu chi)
(a) Gop WFO ca 12 cau hinh deu AM (-0.61 den -1.36 bp/lenh, json DEV; A1 xac nhan 2 cau hinh). TRAIN chi L-60-3 ~ +0.1..+0.2.
(b) Chi time-stop (giu 60' / 240' tu close nen vao, phut dau moi chuoi su kien, khong khoa vi the), gop bp (se ngay tho, cum => that rong hon):
  T=4 L: TRAIN +0.42 / +0.34; WFO -1.01(0.56) / -1.75(0.97). S: TRAIN -1.36 / -1.16; WFO -0.24 / +1.11(0.91).
  T=3 L: TRAIN +1.03 / +1.47; WFO -0.94(0.26) / -1.07(0.47). S: TRAIN -0.51 / -0.25; WFO -0.08 / +0.43.
  => KHONG co hoi phuc o muc gop (WFO phia L con hoi tiep dien). Payoff 0,44 / thang 58 % la dang hinh cua co che thoat tren buoc ngau
  nhien ~0 troi, KHONG phai nguyen nhan thua; nguyen nhan = gop ~0/am + phi.
(c) Phi khu hoi WFO: EURUSD 0.68 bp (0.07 sigma60), GBPUSD 3.00, USDJPY 3.02, AUDUSD 3.77 bp (~0.3 sigma60); them truot SL/TS =>
  phi TB ~2.95 bp/lenh. Hoa von can gop >= ~+1 bp (EURUSD) / ~+4-5 bp (cap khac); thuc te -1 bp.
