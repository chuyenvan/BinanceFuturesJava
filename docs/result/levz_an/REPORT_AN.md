# REPORT_AN - Giai phau he SHORT LEVZ (B1) + kha thi tang xep hang + ghep voi he LONG c3
2026-11-26. Phan tich MO TA tren ket qua da co (khong toi uu, khong tham so moi). Du lieu thi truong < 2026-01-01 UTC (moi reader assert).
Tat ca so tai lap tu `code/` + `out/`. "Da do" = so in trong bang/out; "suy doan" ghi ro.
CANH BAO CHUNG: cfg 4107 / 5204 / ho 50 deu duoc chon SAU KHI nhin DEV (in-sample). Ho 50 = 50 cau hinh `valid` diem cao nhat
(valid doi hoi lai ca 3 fold) => nam nao ho cung duong LA DO CACH CHON, khong phai bang chung.

## 0. Cach lam + kiem tra
- Short: `code/a_run.py` chay lai `levz_b1/code/port.run` DEV lien mach 2022-01-01..2025-12-31 cho 4107, 5204, 3550 + top-50 valid
  (52 cau hinh, 5204 nam trong ho). Tai lap grid_b1 DEV_ret/DEV_n CHINH XAC (max|dret| = 0, |acct_err| <= 2.7e-12) -> `out/a_check.json`.
  Dac trung luc vao (nhan qua): z_oi, z_f, f (bang sig W cua cau hinh), dOI24 (oi tier-1, tsr <= T_k-10m), r24 = CLH[k]/CLH[k-24]-1
  (gia den close nen 1m vao lenh), qv30 (nen 1h dong truoc T_k), tuoi niem yet (tu bar 1m dau tien; bi cat trai tai 2021-12-01),
  gio UTC, btc7 / ew7 (7 ngay den close vao lenh; ew = TB deu coin universe tru BTC).
- Toan luoi: `code/a_grid2024.py` chay lai port DEV cho CA 7 020 cau hinh co san (khong tham so moi) -> loi nhuan thang MTM.
  ret 2024 lien mach vs F2_ret cua grid: tuong quan 0,996; ti le am 80,0 % vs 80,4 %.
- Long: `code/c_long.py`. printDone.csv: moi dong 1 leg BUY; margin = entry x quantity (= notional vao, sai so < 1e-5);
  pnl = USD rong; sum(pnl) = equity_final - equity_start DUNG cho 4/4 lan lap (35 000 -> 138 932 / 143 350 / 157 908 / 153 884);
  so dong = n_trades. Thoi gian UTC+7 -> UTC (-7 h): KIEM BANG GIA (`code/c_tzcheck.py`, 400 leg): sau khi tru 7 h, 99,25 % entry
  khop close 1m (+-1 phut) trong 0,2 %; neu khong tru chi 5 %. Equity ngay dung MTM (tu close1m cua B1, leg mo dinh gia tai moc 00:00 UTC;
  2-3 leg/lan lap khong co gia: FOOTBALL, BLUEBIRD -> 0 unrealized); MTM bo qua phi/funding cua leg dang mo. Co ca chuoi realized de so.
- Ghep: `code/c_combo.py`. r_ghep = r_long + m x r_short (moi sleeve tinh tren cung von, can bang lai hang ngay - xap xi), m = 0,5/1,0/1,5.

## A. Giai phau he short
### A1. Ba cau hinh tham chieu (DEV lien mach, von 10 000)
| | 4107 (W7 E0 z3,0 K3 SL15 H24 t10/5) | 5204 (W7 E0 z3,5 K10 SL50 H24 t5/2) | 3550 (W7 E0 z2,5 K3 SL15 H336 t3/2) |
|---|---|---|---|
| Lai nam 2022/23/24/25 | +6,2 / +15,3 / +27,4 / +10,3 % | +0,4 / +4,7 / +6,7 / +10,9 % | +3,0 / +36,5 / -35,9 / -22,6 % |
| So lenh (theo nam thoat) | 5 / 71 / 130 / 87 (293) | 3 / 44 / 97 / 55 (199) | 6 / 82 / 195 / 153 (436) |
| maxDD trong nam (MTM gio) | 1 / 16 / 15 / 22 % | 0,4 / 2 / 4 / 3 % | 1 / 7 / 45 / 34 % |
| Ti le gio KHONG co vi the | 89,6 % | 94,7 % | 83,0 % |
| Ly do thoat (n; PnL USD) | SL 37: -18 221; time 192: +6 269; trail 64: +19 143 | SL 2: -707; time 68: -1 307; trail 129: +4 465 | SL 83: -26 751; time 2: -168; trail 351: +23 887 |
| Win / TB thang / TB thua | 62,5 % / +6,3 % / -7,8 % | 77,4 % / +4,7 % / -8,0 % | 80,0 % / +3,5 % / -15,5 % |
| MAE (close 1m) trung vi / p95 | 4,3 % / 15,7 % | 3,5 % / 24,5 % | 2,9 % / 15,7 % |
| Giu (h) trung vi | 24 | 12,3 | 7,5 |
| Funding nhan / phi | +774 / -1 165 | +98 / -181 | +804 / -1 227 |
| Top-5 coin / tong | +4 415 / +7 192 | +648 / +2 451 | +2 485 / -3 032 |
| Bo top-10 coin | -257 | +1 437 | -7 259 |
| Bo top 5 % lenh (15 / 10 / 22 lenh) | -910 | +1 566 | -7 757 |
Nguon: `out/a_summary.json`, `out/a_monthly.parquet`, `out/a_coin.parquet`.

### A2. Nam 2024 hong o dau (toan luoi 7 020 cau hinh, `out/a_grid_*.parquet`)
| Thang 2024 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| % cau hinh am | 11 | 89 | 75 | 12 | 72 | 13 | 46 | 12 | 2 | 18 | 86 | 79 |
| Trung vi loi nhuan thang | +1,8 | -7,2 | -3,8 | +4,2 | -1,4 | +3,3 | 0,0 | +0,5 | 0,0 | +1,4 | -6,7 | -3,6 |
| BTC thang (%) | +1 | +44 | +16 | -15 | +11 | -7 | +3 | -9 | +8 | +11 | +37 | -3 |
| Alt EW thang (%) | -11 | +41 | +27 | -35 | +18 | -27 | -9 | -18 | +27 | -8 | +60 | -20 |
- Ti le cau hinh am theo nam: 2022 8,5 %; 2023 43 %; 2024 80 %; 2025 16,5 %.
- Trong 5 618 cau hinh lo 2024: trung vi PnL lenh SL = -4 926 USD, lenh khong-SL = +3 124; 92 % co phan khong-SL duong.
- Theo tham so (ti le am 2024): E1 98 % vs E0 62 %; H24 64 %, H72 74 %, H>=168 87 %; z2,5 88 % / z3,0 77 % / z3,5 75 %; W14 85 % vs W7 75 %.
- Coin (dong gop ret x 0,6/K cong qua cau hinh): xau nhat 1000PEPE, HBAR, NEIRO, 1000FLOKI, BCH, HIGH, WLD, NTRN, XMR, SEI;
  10 coin nay = 46 % tong dong gop am => lo kha phan tan, khong 1-2 coin.
- 3550 (WFO-2024 top-1): 2024 = 195 lenh, 42 SL (-15 067 USD) vs trail 152 (+9 969). Thang: 02 -1 844 (8 SL), 03 -2 337 (10 SL),
  11 -1 449 (10 SL), 05 -538, 12 -408; 04 +1 095. SL KHONG tuc thi: thoi gian tu vao den SL trung vi 23,4 h (p10 3,4 h; p90 87 h);
  chi 2/42 SL trong 1 h dau, 8/42 trong 6 h. Chuoi SL lien tiep (theo thu tu thoat) toi da 2 - SL don cum theo THANG, khong theo chuoi.
- 4107 trong 2024 van +27 % (chon in-sample): Nov -983 (4 SL), May -434; Feb +831, Mar +2 063.

### A3. Ho 50 cau hinh
49/50 W7, 50/50 E0, z3,5 38 / z3,0 12, H24 35, trailing bat 49/50. Lai nam trung vi +0,9 / +7,6 / +6,8 / +13,1 % (min 2024 +2,5 % - do
luat valid). Ti le gio nhan roi trung vi 93,9 %; so lenh/nam trung vi 3 / 44 / 97 / 55. Top-5 coin chiem trung vi 43 % loi nhuan;
50/50 van duong khi bo top-5 coin; 47/50 duong khi bo top 5 % lenh. Thoat: trail 65 %, time 30 %, SL 4,7 %.
50 cau hinh chi dung 708 lenh vao (sym, gio) khac nhau => ho KHONG phai 50 bang chung doc lap.

### A4. Dac trung lenh thang/thua (pool ung vien doc lap W7 E0 z>=2,5, moi dot 1 lan, thoat SL15 H24 t10/5; n = 6/174/419/158)
Spearman(dac trung, ret) theo nam 2023 / 2024 / 2025 (SE ~ 0,08 / 0,05 / 0,08):
| s=min(z) | z_oi | z_f | f | dOI24 | r24 | qv30 | ew7 | btc7 | tuoi | gio |
|---|---|---|---|---|---|---|---|---|---|---|
| +0,15/+0,10/+0,04 | +0,11/+0,08/+0,04 | +0,12/+0,10/+0,01 | +0,04/+0,14/-0,12 | +0,13/+0,16/-0,12 | +0,19/+0,09/-0,16 | -0,12/-0,02/+0,07 | +0,18/+0,03/0,00 | -0,07/+0,05/-0,10 | +0,06/-0,03/0,00 | +0,03/+0,05/+0,06 |
Bang ngu phan vi (canh chung toan ky, theo nam): `out/b_feat_quint.parquet` (o moi nam 7-125 dot; sai so TB ~1-2 %/o).
Lenh cua 4107: ew7 luc vao trung vi 2024 thang 15,0 % vs thua 12,5 %; 2025 thang 2,2 % vs thua 6,0 % (dao dau).

## B. Kha thi tang xep hang (ML)
### B1. So dot ung vien/nam (E0, f > 0,01 %/8h, co nen 1m, cooldown 72 h tu dau dot) - `out/b_counts.parquet`
| W | z_min | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| 7 | 1,0 | 42 | 917 | 2 276 | 597 |
| 7 | 1,5 | 25 | 577 | 1 440 | 391 |
| 7 | 2,0 | 14 | 331 | 845 | 248 |
| 7 | 2,5 | 6 | 174 | 419 | 158 |
| 14 | 1,0 | 38 | 820 | 1 884 | 511 |
| 14 | 1,5 | 21 | 512 | 1 168 | 317 |
| 14 | 2,0 | 11 | 302 | 671 | 174 |
| 14 | 2,5 | 4 | 161 | 365 | 104 |
Bang sig_W7/W14 CO chua z < 2,5 (giu moi hang universe; z_oi huu han 99,4-99,8 % moi nam, ke ca 2022) => dem truc tiep, khong can dung lai tang 1.
2022 gan nhu khong co tin hieu do dieu kien f > 0,01 %/8h (thi truong giam) - khong phai thieu du lieu.
### B2. Ket qua tung dot doc lap z>=2,5 (khong qua danh muc; `out/b_outcomes.parquet`), W7, 2023 / 2024 / 2025
| Thoat | win % | TB ret % (SE) |
|---|---|---|
| SL15 H24 t10/5 | 60 / 58 / 56 | +0,65 (0,50) / +0,10 (0,39) / +0,02 (0,91) |
| SL30 H72 t10/5 | 52 / 59 / 68 | -0,44 (0,74) / +0,47 (0,57) / +0,64 (1,32) |
| SL50 H24 khong trail | 59 / 54 / 58 | +0,42 (0,57) / -0,78 (0,45) / +0,32 (1,60) |
W14 tuong tu (|TB| <= 0,7 %, deu < 2 SE). Gio khong-dau-dot (tu tuong quan, SE bi danh gia thap): 2024 TB -0,4..-0,9 %, 2025 +1,3..+3,4 %.
Ti le SL (SL15) tang 7 % (2023) -> 11 % (2024) -> 21 % (2025).
### B3. Ket luan dem
Nguong >= 300 ung vien/nam: KHONG nam nao 2022 dat (toi da 42). 2023-2025 chi dat o z_min <= 1,5 (W7: 577/1 440/391; W14: 512/1 168/317);
z2,0 dat 2023-2024 nhung truot 2025 (248/174). Pool z>=2,5 hien co: 174/419/158 (W7). Nhan (ket qua) cho z < 2,5 CHUA co: exits.npz
chi phu union z>=2,5 (8 524 cid). Uoc cong: dung lai cand cho z 1,0-2,0 (ham B0 candidates() voi zmin moi) + exits_core B1 (~2,7 ms/ung vien
cho 195 bo thoat; W7+W14 z>=1,0 ~ 129 k gio-ung-vien => ~6 phut CPU, ~2,5 GB RAM bang day du; hoac chi dau dot ~7 k => < 1 phut)
+ test khop + prereg pool moi: ~0,5 ngay cong (suy doan). Phai ghi o thu muc moi, khong vao levz_b1.

## C. Ghep voi he LONG (c0s42 / c0s7 / c0s123 / c0s13)
Long 2022-2025 (MTM): CAGR 35,0-39,8 %, maxDD 12,7-17,7 % (May 2022), Sharpe ngay 1,93-2,11; co >= 1 leg 41-42 % so gio; phoi nhiem TB ~5 %,
toi da 48 %; funding long tra -2 437..-2 751 USD trong DEV.
### C1. Cap long x short (khoang qua 4 lan lap; ho = trung vi 50 cau hinh x 4)
| | 4107 | 5204 | 3550 | ho 50 (trung vi) |
|---|---|---|---|---|
| Tuong quan ngay MTM 2022-25 | 0,012..0,023 | 0,012..0,027 | -0,001..0,007 | 0,032 (p10-p90 0,006-0,052) |
| (realized, de so) | 0,07..0,09 | 0,05..0,09 | 0,04 | 0,09 |
| Tuong quan tuan / thang (48 diem) | -0,02..-0,01 / -0,14..-0,04 | 0,04..0,08 / 0,01..0,05 | 0,00..0,02 / -0,11..-0,07 | 0,05 / 0,03 |
| % gio CA HAI co vi the | 3,2-3,8 | 1,7-1,9 | 5,4-6,2 | 1,8 |
| Gross (long+short) max / p99 | 0,92-0,97 / 0,61 | 0,48-0,56 / 0,39-0,41 | 0,95-1,02 / 0,66 | 0,69 / 0,42 |
| Lenh short trung coin dang long | 15-17/293, 59-76 h | 8-10/199, 8-17 h | 10-11/436, 23-33 h | 4,5 % lenh (1,8-13,2 %) |
Tuong quan thang theo TUNG nam chi 12 diem (vd 4107: 2024 +0,40..+0,47; 2025 -0,49..-0,61) => nhieu, khong doc.
10 ngay te nhat cua long (2022-05-11 -11,2 %, 2022-11-09 -9,6 %, 2024-04-13 -4,9 %, ...; tong -46..-47 %): short 4107 / 5204 / ho KHONG co
vi the ca 10 ngay (r = 0); 3550 co vi the 1-2 ngay (+0..+2 %). 10 ngay te nhat cua short: long khong co vi the 6-7/10 ngay, duong 2-3,
tong long +0,2..+3,4 %. Xung dot trung coin nam chu yeu o 2024.
### C2. Danh muc ghep cung von (IN-SAMPLE cua short - chi de hieu cau truc)
| | m | CAGR | maxDD | Calmar | Sharpe | dung von TB / dinh gio |
|---|---|---|---|---|---|---|
| Long rieng | - | 35,0-39,8 % | 12,7-17,7 % | 1,99-3,14 | 1,93-2,11 | ~5 % / 0,48 |
| + 4107 | 0,5 / 1,0 / 1,5 | 45-50 / 55-60 / 64-69 % | 13-18 / 17-18 / 25-26 % | 2,6-3,9 / 3,1-3,5 / 2,5-2,7 | 2,1-2,3 / 2,0-2,1 / 1,8-1,9 | 7 / 8,5 / 10 % ; 0,63-0,68 / 0,92-0,97 / 1,22-1,28 |
| + 5204 | 0,5 / 1,0 / 1,5 | 39-44 / 43-48 / 46-52 % | = long | 2,2-3,4 / 2,4-3,8 / 2,6-4,1 | 2,1-2,3 / 2,2-2,4 / 2,3-2,5 | 5,5-6 % ; 0,48-0,67 |
| + ho 50 (trung vi) | 0,5 / 1,0 / 1,5 | 40-45 / 45-50 / 50-55 % | = long | 2,3-3,5 / 2,5-3,9 / 2,7-4,1 | 2,1-2,3 / 2,2-2,3 / 2,2-2,3 | 6-7 % ; 0,48-1,0 |
| + 3550 | 0,5 / 1,0 / 1,5 | 30-34 / 23-28 / 16-21 % | 14-18 / 28-31 / 53-56 % | 1,7-2,4 / 0,8-0,9 / 0,3-0,4 | 1,5-1,6 / 1,0-1,1 / 0,6-0,7 | 8 / 11 / 14 % ; 0,64-0,69 / 0,95-1,02 / 1,28-1,35 |
Ho 50: Calmar ghep > long o 100 % cap (m 0,5 & 1,0), 98,5 % (m 1,5). Theo nam (4107, m=1, trung vi lap): 2022 +13,6 % (long +7,0),
2023 +102 % (+75), 2024 +80 % (+42), 2025 +47 % (+34). 3550 m=1: 2024 -8,9 % (long +41,7 %). Nguon `out/c_combo.parquet`.
### C3. Van de van hanh khi ghep 1 tai khoan (chi liet ke tu du lieu)
1. One-way mode: 4,5 % (trung vi ho; 4107 5-6 %) lenh short trung coin dang co long - one-way se bu tru/dong vi the long; can hedge mode
   hoac luat xu ly xung dot. 2. Margin chung CROSS 1x: gross dinh 0,92-0,97 (4107 m1), 1,22-1,35 (m1,5) => vuot 1x o m 1,5;
   long rieng dinh 0,48. 3. Kill-switch/DD chung: DD trong nam cua short (4107 22 % nam 2025; 3550 45 % nam 2024) lon hon DD cua long
   tung nam (4-17 %) => DD chung se bi short chi phoi o nam xau; long dung moc equity khac (sim tu 2021-07, 35 000). 4. Funding hai chieu:
   short NHAN funding (+774 tren 10 000 voi 4107), long TRA (-2,4..-2,8 k tren ~42-150 k); cung coin cung luc => bu tru. 5. Moc thoi gian:
   sim long ghi UTC+7, short UTC. 6. Co so tinh size khac nhau (short: MTM equity x 0,6/K; long: equity sim) - can 1 dinh nghia equity chung.

## QUAN SAT (danh so; do chac chan)
1. Lai cua short den tu SO IT lenh thang lon qua trailing; SL an mat phan lon (4107: trail +19 143, time +6 269, SL -18 221; bo 15 lenh tot
   nhat (5 %) thi -910). Chac: cao (da do), nhung 1 cau hinh in-sample.
2. 2024 hong o 5 thang alt tang manh/tiep dien: Feb (89 % cau hinh am), Mar (75 %), Nov (86 %), Dec (79 %), May (72 %); thang alt giam
   (Apr -35 %, Jun -27 %) 87-88 % cau hinh duong. n = 7 020 cau hinh nhung cung 1 chuoi thi truong => thuc chat ~5 su kien. Chac: trung binh.
3. Lo 2024 = lo SL: 92 % cau hinh lo 2024 co phan khong-SL duong; trung vi SL -4 926 vs con lai +3 124 USD. Chac: cao (da do).
4. Squeeze den CHAM: 3550/2024 SL sau trung vi 23 h (p10 3,4 h), chi 2/42 trong 1 h - SL la xu huong keo dai, khong phai wick. n=42. Chac: TB.
5. H dai (>=168 h) va E1 te hon ro trong 2024 (87 % / 98 % am vs H24 64 %, E0 62 %). Chac: TB (khong doc lap giua cau hinh).
6. Tap trung coin cao: ho 50 top-5 coin = 43 % loi nhuan (trung vi), nhung 50/50 van duong khi bo top-5; 4107 thi am khi bo top-10 coin.
7. He short nhan roi ~90-95 % thoi gian; 2022 chi 3-6 lenh (tin hieu hiem do f > 0,01 %). Chac: cao.
8. Dac trung: chi s = min(z), z_oi, z_f giu dau duong 2023-2025 nhung yeu dan (+0,15 -> +0,04); dOI24, r24, f, qv30 DAO DAU nam 2025.
   n 158-419/nam, SE 0,05-0,08 => vai he so vuot ~2 SE (2023: r24, ew7; 2024: f, dOI24; 2025: r24 am) nhung khong bien nao ngoai
   s/z_oi/z_f giu dau qua 3 nam. Chac: thap.
9. Moi dot doc lap z>=2,5: TB ret ~0 (|TB| <= 0,8 %, deu < 2 SE) duoi ca 3 bo thoat co dinh => loi nhuan danh muc phu thuoc lua chon/
   tuong tac thoat, khong thay tin hieu tho manh. Chac: TB.
10. Pool cho ML: >= 300 dot/nam chi khi z_min <= 1,5 (2023-25); 2022 khong bao gio dat (<= 42). Chac: cao (dem).
11. Tuong quan ngay long-short ~0 (MTM 0,01-0,03; realized 0,05-0,09 la do lech thoi diem ghi nhan); cung co vi the chi 2-4 % so gio;
    short KHONG co vi the trong ca 10 ngay te nhat cua long. Chac: cao cho do do; y nghia tuong lai: thap.
12. Ghep sleeve nho (5204 / ho) khong tang maxDD cua long (DD cua long thong tri) va tang Calmar o 100 % cap; sleeve lon/kem (3550 m>=1)
    lam DD ghep 28-56 %. Chac: TB (in-sample).
13. Xung dot cung coin: 4,5 % lenh short (trung vi ho), 4107 15-17 lenh / 59-76 h trong 4 nam. Chac: cao.

## KHONG ket luan duoc
- Co "edge" hay khong: moi cau hinh duoc chon in-sample; 80 % luoi lo 2024; tung dot doc lap TB ~0.
- Dac trung nao on dinh: so mau/o nho, dao dau, 2022 gan nhu khong co mau.
- Tuong quan thang theo tung nam (12 diem); hanh vi trong thi truong tuong lai (2026 holdout chua doc).
- MTM long bo qua phi/funding leg dang mo; equity long la sim nghien cuu (4 lan lap), khong phai live. Short chi thay close 1m (khong wick).
- Ghep r_long + m x r_short gia dinh can bang lai hang ngay tren cung von - khong mo phong rang buoc margin/thu tu lenh that.

## GOI Y GIA THUYET cho tang sau (HAU KIEM - sinh ra sau khi nhin du lieu, can prereg truoc khi thu)
- G1 (hau kiem): cong che do theo xu huong alt EW (thang Feb/Mar/Nov 2024 alt +27..+60 %) - NHUNG o muc lenh, ew7 luc vao khong tach thang/thua
  (2024 thang co ew7 CAO hon) => neu thu phai la bien xu huong dai hon / nhan qua, dang ky truoc.
- G2 (hau kiem): gioi han H ngan (24 h) + E0 la vung it ton thuong 2024; can kiem ngoai mau.
- G3 (hau kiem): xep hang theo s=min(z) la ung vien duy nhat cung dau 3 nam; ML can pool z_min <= 1,5 va loai 2022 (qua it mau).
- G4 (hau kiem): gia tri cua sleeve short cho he ghep nam o tinh doc lap thoi gian (nhan roi khi long sap), khong o lai; sleeve nho (m<=1, K10)
  khong lam tang DD - can kiem tren 2026 holdout theo prereg.
- G5: can luat xung dot cung coin (hedge mode hoac bo qua) truoc khi ghep that.

## Diem A1 can soi
- `a_run.py`: tai lap grid (a_check.json); t_exit = T_ke + (j+1) phut; eod; dac trung nhan qua (dOI24 dung oi tsr; qv30 bar dong truoc T_k;
  r24/btc7/ew7 dung CLH[k] = gia vao lenh - khong dung gia sau vao).
- `c_long.py`: chuyen UTC+7 (c_tzcheck.json), MTM tai moc ngay = close bar 1m ket thuc tai moc; leg mo khong co gia -> 0; expo = margin/equity realized.
- `c_combo.py`: canh ngay short (eq 00:00 -> 00:00; ngay cuoi den 23:00 2025-12-31), cong thuc ghep cong tuyen tinh, merge interval long theo usym.
- `b_pool.py`: dem dot (cooldown 72 h tu dau dot, >= z, f > 1e-4, has1m); outcome ret = (1-xr) - 0,0007(1+xr) + fund; bo 'eod'.
- `a_grid2024.py`: thang = equity MTM cuoi thang (gio cuoi thang); dong gop coin = sum ret x 0,6/K.
