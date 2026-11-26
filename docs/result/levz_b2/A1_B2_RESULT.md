# A1_B2_RESULT - audit KET QUA LEVZ B2 (A1, 2026-11-26 07:18-07:42 UTC)
Nguon: out/grid_b2_<O>.parquet (12 x 7 020), levz_b1/out/grid_b1.parquet, report_b2.json. Code A1: a1/code/{res_recalc,anatomy,pl_run,pl_fair}.py;
so: a1/out/{res_recalc,anatomy,fair_G_EW14,fair_G_EW7}.json, a1/out/pl/placebo_b2_G_EW{14,7}_FORCE.json. SHA code/test khop; chi out/check_none.json doi
(sec_mean do pipeline chay lai, identical 300/300) - vo hai.

## 1. Tinh lai doc lap (code rieng tu parquet)
- 12 phuong an x 4 fold x {trung vi ret, frac lai, trung vi chenh, frac cai thien, lenh con lai, trung vi maxDDw}: 0 sai lech voi report_b2 (tol 1e-12).
  Ke toan acct_err ~0 moi dong. Tieu chi (a)-(d) cham lai bang code rieng (valid20 tu viet: n>=30, ret>0, DDw<=0,30 tren fold chon): trung DEV o 12/12.
  Doc (c) dung chu prereg (trung vi n_O/n_goc, F1-F3) cho CUNG ket qua voi cach doc min cua DEV o ca 12 => lua chon cach doc khong doi ket luan.
- 2 cau hinh duoi G_EW14 (cfg 939, 902), ung vien A1 tu loc -> port.run_all: 108/108 cot trung parquet. Ledger DEV A1 cho 7 020 cau hinh: so lenh
  trung DEV_n 7 020/7 020 (G_EW14 va G_EW7).
- KHONG phuong an nao dat (a)-(d). G_EW7, G_EW14: dat (a), truot (b), (c), (d) (WFO 2024 va 2025: 0 cau hinh hop le).
- So MASTER doc: DUNG het (goc, G_EW14, G_EW7, G_BTC20, F_LIQ50). Bo sung can noi: "F1 +0,3 % / 60 %" cua G_EW14 dua tren TRUNG VI 1 LENH / 2 nam
  (p5-p95: 0-3) => vo nghia thong ke; "lenh con 12 %" la cach doc min (trung vi ti le = 12,9 %).

## 2. Giai phau G_EW14 / G_EW7
Gate mo (% gio): EW14 2022 60 / 2023 36 / 2024 46 / 2025 61; EW7 56 / 39 / 45 / 55. 2024 theo thang (EW14): T1 68, T2 11, T3 25, T4 72, T5 35, T6 77,
T7 52, T8 60, T9 36, T10 47, T11 20, T12 49 (EW7 tuong tu).
So lenh / cau hinh (trung vi [p5-p95]) 2022 / 2023 / 2024 / 2025:
- GOC: 2 [0-6] / 57 [30-126] / 99 [52-258] / 65 [35-152].
- G_EW14: 0 [0-1] / 0 [0-2] / 12 [2-39] / 31 [14-87]; theo z 2,5/3,0/3,5 nam 2024: 22 / 11 / 4,5; theo K gan nhu khong doi (11-12,5).
- G_EW7: 0 [0-1] / 1 [0-4] / 11 [3-22] / 24 [13-69].
Lenh phan biet (gop 7 020 cau hinh, (coin, gio vao)): G_EW14 2022-23: 7 lenh (4 dot coin); 2024: 230 (97 dot); 2025: 216 (102 dot). G_EW7 2024: 61 (40 dot).
=> "92,9 % cau hinh co lai DEV" la 7 020 bien the tren CUNG ~450 lenh / ~200 dot coin, gan nhu toan bo 2024-2025, dong cum theo vai thang gate mo;
   khong phai 7 020 bang chung doc lap. F1 (2022-23) gan nhu rong.
Phan vi ret qua 7 020 cau hinh (5/25/50/75/95 %): G_EW14 F2 -3,6/+0,5/+2,1/+5,7/+16,4; F3 -1,4/+4,3/+9,8/+19,4/+45,2; G_EW7 F2 -8,8/-1,7/+1,1/+3,9/+11,4;
  F3 -11,0/0,0/+6,6/+14,4/+33,8.
3 cau hinh dai dien G_EW14 (trung vi DEV_ret trong lop): 
- W7 E0 z2,5 K10 (cfg 4061): 141 lenh (2024: 51, 2025: 87); top 5 % lenh (8) = 65 % PnL; thang tot nhat 2024-04, 2025-11; SL 5 %; lenh te nhat -55 %.
- W7 E0 z3,0 K3 (cfg 4196): 64 lenh; top 4 lenh = 73 % PnL; 2025-11 mot thang = 93 % PnL tong; SL 16 %.
- W14 E0 z2,5 K10 (cfg 432): 71 lenh; top 4 lenh = 166 % PnL (phan con lai lo); 2025 lo; SL 18 %.
=> Loi nhuan DON vao vai lenh / vai thang (2024-04, 2025-11).
Gate CHON hay chi GIAM? (lenh cua ban GOC, gop moi cau hinh, chia theo gate mo/dong tai gio vao):
- 2024 EW14: mo 253 lenh pb, TB +2,6 %/lenh, thang 78 %, SL 7,7 % | dong 2 319 lenh pb, TB -1,4 %, thang 66 %, SL 16 %. EW7: mo +0,8 % / SL 11,7 % vs dong -1,1 % / 15,4 %.
- 2025 EW14: mo +2,4 % / SL 13,3 % vs dong +1,9 % / 13,4 % (gan nhu khong khac); EW7: mo +1,9 % vs dong +2,3 % (nguoc).
- 2023: gate mo chi 4-8 lenh pb - khong do duoc.
=> Hieu ung CHON chi ro o 2024 (nam sinh ra gia thuyet); o 2025 khong co, va ve danh muc gate lam giam ret trung vi F3 (-5,3 / -9,1 pp).

## 3. Tinh manh bang chung
- Hau kiem: gia thuyet sinh SAU khi thay 2024 hong; 3 bien the EW + 2 BTC tren cung y tuong; 12 phuong an; nguong 0 / cua so 7-14 chon sau => do tu do lon.
- Placebo prereg (dich vong, 500, NGOAI quy trinh, chi mo ta): G_EW14 that 0,843 vs placebo trung vi 0,25 [5-95 %: 0,08-0,60], p = 0/500;
  G_EW7 0,647 vs 0,26 [0,07-0,56], p = 0,020 (> 0,05/12). Nhac MINOR: placebo giu 49-51 % ung vien vs gate that 11-14 % => lan hieu ung so lenh.
- Placebo cong bang (A1, 200 luot, giu ngau nhien DUNG so ung vien gate that giu moi lop x nam): G_EW14 F2 0,843 vs 0,39 [0,26-0,52] p = 0; DEV 0,93 vs
  0,73 [0,64-0,81] p = 0. G_EW7 F2 0,647 vs 0,38 [0,24-0,54] p = 0; DEV 0,823 vs 0,76 [0,66-0,86] p = 0,165.
  Han che: chon ngau nhien theo dong ung vien khong giu cum thoi gian; placebo dich vong giu cum nhung khong giu so lenh - khong cai nao giu ca hai.
- Doc: trong 2024, gate EW14 tach lenh tot / xau ro hon ngau nhien - nhung 2024 la du lieu sinh ra gia thuyet (in-sample ve chon gia thuyet), placebo
  KHONG sua duoc loi hau kiem / da phep thu. Bang chung ngoai nam goc (2025, va 2022-23 rong) khong ung ho.

## 4. Ket luan theo prereg muc 5 (chu)
Khong phuong an nao dat (a)-(d) => "B2 KHONG CUU DUOC": MASTER bao owner so thuc; khuyen nghi DUNG chuong trinh short (khong B3 ML); owner quyet;
KHONG thu to hop / nguong khac de vot. Placebo prereg khong ap dung (chi cho phuong an dat (a)-(d)).
MASTER DUOC noi: "Gate EW14 truot tieu chi prereg (b), (c), (d); B2 khong cuu duoc. Mo ta: trong 2024 - chinh nam lam nay ra y tuong - chan khi alt tang
14 ngay bo ~88 % lenh va lenh con lai tot hon; 2022-23 gan nhu khong co lenh; 2025 gate lam giam loi nhuan so ban goc; khong cau hinh nao hop le theo
luat chon cua B1; ket qua la hau kiem, khong phai ky vong."
KHONG DUOC noi: "93 % cau hinh co lai" nhu bang chung; "placebo p ~ 0 => edge that"; bat ky muc loi nhuan ky vong; de nghi trien khai / HO 2026 cho
G_EW14 (can prereg moi + owner quyet, va trai muc 5).
