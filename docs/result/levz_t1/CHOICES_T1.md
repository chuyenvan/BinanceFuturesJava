# CHOICES_T1 - lua chon cai dat LEVZ T1 (PREREG_LEVZ_T1 @186f2a5a + ADD1 45f45a5b) - muc 1-9 MASTER da chap nhan (ADD1 tra loi)
Nguyen tac: prereg khong noi ro => chon cach BAT LOI hon neu xac dinh duoc, khong thi giu quy uoc B1 (CHOICES_B1) + ghi lai.

## Engine (exits_t1.py)
1. Tai dung B1 exits.path_of / hourly_core / Store (import, khong sua): cung duong gia 1m, ffill, gap > 24 h => 'miss', cat 2025-12-31, eod.
2. Thu tu trong mot phut: SL > TP > STATE > TIME > MISS. SL va TP khong the cung phut (close khong the vua >= p0(1+sl) vua <= p0(1-tp)).
3. TP: close 1m <= p0 (1 - tp) => khop DUNG muc p0 (1 - tp), xr = 1 - tp, khong truot, phi 0,07 % tren notional luc ra (nhu port B1).
4. Ma ly do: port.py chi biet RNAMES B1 (sl, trail, time, miss, eod). T1 giu ma rieng rt (sl, trail, time, miss, eod, tp, state, be) trong
   bang thoat va MAP sang ma port: tp -> 'trail', state -> 'time', be -> 'sl'. => trong parquet luoi T1, cot x_trail = ti le TP (BRK/VOL/PART),
   x_time gom ca thoat STATE (ho STATE), x_sl gom ca stop hoa von PART. Khong monkeypatch port/common_b1.
5. VOL: u = sd (ddof 1) loi suat log gio tren 168 h KET THUC tai T_k (close cac nen gio CL[k-168..k] cua inputs.npz B0; nen dong tai T_k
   co truoc lenh vao T_k + 1 phut) x can(24). Bo loi suat NaN. Neu < 24 loi suat hop le => SL = tran 50 % (bat loi). R x SL >= 100 % => TP
   khong bao gio cham (tu nhien).
6. STATE: dieu kien xet tai hang tin hieu k + h, h >= 1 (hang k + h = gio da chot tai T_{k+h}); thoat tai path phut 60 h (close nen 1m mo
   tai T_{k+h}, tre 1 phut - cung quy uoc vao lenh va time-stop B1). Khong xet h = 0 (gio vao). NaN => khong kich (giu lenh; SL / H van bat).
   f so voi 0,0001 (f tang 1 da quy ve 8 h). Neu STATE va TIME cung phut: ghi 'state' (gia nhu nhau).
7. PART: dong 50 % o phut dau tien close <= p0 (1 - s), khop dung p0 (1 - s), CHI khi phut do < phut SL va <= phut TIME / MISS. Phan con
   lai: stop hoa von = close >= p0 -> thoat close x 1,003 (truot SL, bat loi), TP tai p0 (1 - 3 s), TIME, MISS; BE / TP chi xet tu phut SAU
   phut chot mot nua (lenh TP 3 s coi nhu dat sau khi khop nua dau - bat loi); TIME / MISS trung phut chot mot nua => dong phan con lai
   cung phut.
8. PART vao port.py (khong sua) nhu MOT lenh: xr = 0,5 xr1 + 0,5 xr2 (=> gross va phi ra dung tuyet doi), funding = du ky truoc phut chot
   nua (quy tac 60 h - 1 <= j1) + 0,5 cac ky sau; mang gio hieu dung (PartView): mk = 0,5 xr1 + 0,5 mk sau phut chot nua; fh x 0,5 sau
   chot nua; hm / mxh = ban bat loi (max cua ban day va ban nua) cho cua so gio chua phut chot nua. Lech duy nhat so voi so sach that:
   phi ra cua nua dau (0,5 x xr1 x 0,07 %) ghi nhan luc dong lenh thay vi luc chot nua (equity dung de chia size thoi diem giua cao hon
   <= 0,035 % notional); tong cuoi dung tuyet doi.
9. Phut thieu (ffill) khong kich SL / TP moi (gia khong doi) - nhu B1.
   (MASTER: report PART phai in ly do thoat THAT rt tu bang thoat T1, khong in ma da map.)

## HEDGE (hedge_t1.py; ADD1 A1-A3)
10. Phan short = vong port.run B1 chep lai, chi doi size = eq x 0,60 / ((1 + h) K); so cai / thuoc do dung lai port._ledger + sim.metrics
    (khong sua). Lenh thoat short chi xu ly tai gio co ung vien (dung nhu port.run, cung thu tu cong 'realized') - test (c) h = 0 trung
    tuyet doi B1 (trades, equity, moi cot metrics).
11. "Notional short dang mo" = N x mk (gia tri hien tai theo close 1m moc gio) cua moi short con mo SAU quyet dinh gio k (gom lenh vua vao,
    bo lenh da thoat trong cua so (T_{k-1}, T_k]). Can lai moi gio tai P_k = close nen 1m mo tai T_k (cung phut voi gia vao / mark short).
12. BTCETH: 2 chan doc lap, moi chan muc tieu 0,5 x L_k. Phi 0,07 % tren |luong can lai| moi chan.
13. Funding chan long: ky tai moc T_k (FR[k] cua B0) tinh tren so units giu tu gio k-1, notional = units x close nen 1m KET THUC tai T_k
    (nhu B1 path[60h-1]); long TRA khi rate > 0.
14. Equity dung chia size tai gio k = equity short B1 + (tien mat hedge + units x P_k) TRUOC can lai gio k.
15. eq_worst (A3) = eq_worst short B1 + equity hedge - units_{k-1} x (P_k - min close 1m trong (T_{k-1}, T_k]). maxdd (cot B0) = tai close
    gio (bao kem theo A3). Cuoi fold (kl): dong het chan long tai P_kl (phi tinh).
16. acct_err = bat bien so cai phan short (B1); them hedge_acct_err (tien mat hedge = tong dong tien mua/ban - phi - funding),
    hedge_pnl, hedge_fees, hedge_funding, hedge_val_mean. Gate G_EW14 chi chan short moi (A2); chan long theo short dang mo.

## Chon / bao cao (select_t1.py, report_t1.py)
17. WFO = select_b1.rule KHONG sua (dd_mode 'folds'), chay rieng tung (ho, gate). Hang xom cao nguyen = doi 1 tham so 1 nac trong ho:
    zmin, K + BRK (s, R, H) | VOL (a, R theo thu tu 1, 2, 3, khong TP; H) | PART (s, H) | STATE (z_out, SL, H) | HEDGE (inst, h + neu
    bo goc la BRK: s, R, H cua bo goc). 3 bo goc B1 cua HEDGE khong co hang xom theo bo goc. Top-1 = qua tron luat; top-20 = 20 cau hinh
    HOP LE diem cao nhat (B1 ADD1 B). Khong cau hinh hop le => 'khong cham duoc <Y>'.
18. T-b dung ti le cau hinh co lai trong ho (gate NONE) o F1, F2, F3. T-d: trung vi qua cau hinh cua ho cua (F2_n + F3_n) >= 100.
19. T-e: chay lai top-1 WFO tren fold kiem; "bo 5 % lenh loi nhat" = bo ceil(5 % x so lenh) lenh co net CAO nhat (nhu PROGRAM R6);
    tong net con lai (+ hedge_pnl voi HEDGE, vi chan long khong phai 'lenh') phai > 0.
20. Ly do thoat trong report = rt THAT cua bang thoat T1 (tp / be / state ...); lenh bi dong cuoi fold = 'eod'. Bo goc B1 cua HEDGE: ten B1.
## Doi chung ngau nhien (rand_t1.py)
21. Lop W7 E0 z 3,0; rut nhu rand_b1 (B0 build_pools / draw tren dot that cua lop); seed rieng 20261128, luot r: default_rng([seed, r]);
    CUNG mot tap ngau nhien cho moi ho va ca hai gate (G_EW14 loc theo gio vao nhu ung vien that). Thong ke = max diem maximin (B0
    score_of) qua toan bo bo thoat x K cua ho; p = ti le luot >= max that (cung ho / gate / z 3,0). 100 luot, moi ho, moi gate, khong
    gate truoc. Resumable, 1 file part / (ho, gate, luot).
## Ghi nhan 'miss' (MASTER hoi)
22. Bang thoat B1 that (work/exits.npz, 8 524 ung vien union x 195 bo) co 0 lan 'miss' va longgap = 0 => 124 gap > 24 h cua B1 khong
    nam trong duong 30 ngay sau gio vao cua ung vien nao (vi tri tung gap CHUA kiem). T1 cung 0 'miss' => KHOP B1,
    khong phai do map ma (miss -> miss) hay dem sai. Vi test (a) khong phu nhanh nay, them test (h) tren du lieu GIA co gap 2 000 phut.
