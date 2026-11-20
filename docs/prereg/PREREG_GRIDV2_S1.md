# PREREG_GRIDV2_S1_FINAL - Giai doan 1 grid ("lam min tap dau vao"): don vi luoi MOT BEN, 32 o, 2 mo hinh khop bao nhau
Ngay 2026-11-20. Tac gia: agent thiet ke+dev. Trang thai: FINAL - A1 vong 3 PASS-WITH-MINOR (v12/A1_GRIDV2_S1_R3.md); MASTER duyet va commit 2026-11-20 (muc 18). CHUA cham du lieu that.
Ban TU CHUA (thay the DRAFT3 244eb0a1...). Can cu: w3/gridv2/S1_MASTER_DECISIONS_1120.md (sha256 beb7d83f...), _R3.md (1261f873...),
_R4.md (020ad102...); audit A1 v12/A1_GRIDV2_S1.md (F1-F16) + v12/A1_GRIDV2_S1_R2.md (G1-G7); v12/GRID_PLAYBOOK_1120.md,
v12/GRID_PROTOCOL_V2_REDTEAM.md. Code + ket qua tong hop: w3/gridv2/s1/ (sha256 muc 15; EXPECTED_SHA.txt cho merge), bao cao
v12/GRIDV2_S1_DEV.md R4. Bang xu ly F1-F16 + G1-G7: muc 17.
Quy uoc: bps = 0,01 %; UTC; nua A = 2021-07-01..2023-12-31 (XAC NHAN), nua B = 2024-01-01..2025-12-31 (CHINH).
Moi dieu duoi day chot TRUOC khi cham du lieu that; khong doi sau do (doi = trial moi + exploratory).

## 0. Cau hoi va pham vi
Owner: "chon khung + coin + chieu phu hop" truoc khi xay chien luoc. S1 hoi: duoi mo hinh khop LAC QUAN nhat co the bao ve (K_OPT),
co tap (khung c,k / tier / tap coin ex-ante / chieu theo xu huong) nao ma PnL NET trung binh moi don vi luoi mot ben da khop > 4 bps,
o ca 2 nua, khong do bat spread, khong do <= 3 coin / 1 su kien, va (voi tap mot chieu) khong do beta BTC? Buoc 3-5 (chien luoc,
tinh chinh, can bang) chi lam cho tap PASS, prereg rieng.

## 1. Du lieu (chi doc sau commit prereg + sha)
- Kline 1m: Kaggle chuyendinh/vz-kline1m-2021..2025 (kline1m-YYYY-MM.parquet, 1 row group = 1 symbol; cot ts (ms open), sym, open,
  high, low, close, volume, quote_volume, active). Doc 2021-05-01..2025-12-31 (2 thang dau chi warm-up). V0: dong metadata/nam =
  {2021: 60001411, 2022: 75973640, 2023: 104401093, 2024: 155015111, 2025: 256801320}.
- Funding: CHI chuyendinh/gridp-t1-funding (funding-2021..2025.parquet: ts, sym, interval_h, rate). KHONG mount vz-funding (co 2026).
  Neu thieu cot interval_h: suy = khoang cach 2 moc lien tiep (gio, lam tron, kep [1, 8]).
- Universe: chuyendinh/gridp-lifecycle (lifecycle.parquet: symbol, first_utc, last_utc, ascii); bo dong first_utc >= 2026-01-01.
- ALLOWLIST dataset (R3-7): runner duyet MOI file duoi thu muc input; moi file phai nam trong DUNG 1 trong 7 slug vz-kline1m-2021,
  -2022, -2023, -2024, -2025, gridp-t1-funding, gridp-lifecycle; phai co du 7 slug; ten file chua "2026" -> abort; trong slug chi
  chap nhan dung ten parquet mong doi (kline1m-YYYY-MM voi YYYY = nam cua slug, funding-YYYY voi YYYY < 2026, DUY NHAT 1
  lifecycle.parquet); parquet la / trung thang -> abort. Khong glob "**" lay file dau tien. Moi ts doc vao phai < 2026-01-01 (assert).
- Phut hop le = co dong, active = True, O/H/L/C huu han > 0; con lai = lo.
- V2 (R3-6): dong active co O/H/L/C NaN hoac <= 0 -> coi la phut lo (khong khop), DEM theo nam va bao cao; abort CHI KHI ti le dong
  xau > 0,1 % so dong active cua bat ky nam nao (kiem ngay sau pass1, truoc khi mo phong).
- V6 (R3-10): truoc khi mo phong, tren TOAN file funding moi nam (moi symbol): median |rate| phai trong [1e-5, 1e-3] VA interval_h
  thuoc {1, 2, 4, 8} (cot co san: moi dong; cot suy tu khoang cach moc: >= 99 % dong); sai -> abort.

## 2. Universe + tier (point-in-time tai ngay D, chi du lieu <= cuoi D-1)
- Hop le: ten USDT, khong "_", ASCII, khong stable (USDC/BUSD/TUSD/FDUSD/USDP/DAI/USDE), khong index (BTCDOM/DEFI/FOOTBALL/BLUEBIRD),
  first_utc <= D - 30 ngay, last_utc >= D, >= 1 phut hop le o D-1.
- Tier = hang tong quote_volume D-30..D-1 (hoa: ten): T1 = 1-10, T2 = 11-60, T3 >= 61. Coin delist o lai den ngay delist.

## 3. Feature ex-ante (M3; ngay D chi dung du lieu <= cuoi D-1; hoa: ten symbol)
- Close gio = close phut hop le cuoi cua gio; close ngay = close phut hop le cuoi cua ngay.
- sigma_1d(D) = RMS (khong tru TB) 30 log-return close ngay D-30..D-1, can >= 20 return hop le.
- ER30(D) = |C_cuoi - C_dau| / tong |C_h - C_{h-1}| tren chuoi close gio hop le trong [D-30 00:00, D 00:00) (gio thieu bo qua, noi 2 gio
  hop le ke nhau); can >= 600/720; tong = 0 -> khong xac dinh (khong thuoc ER_LOW).
- Tuoi(D) = floor((D 00:00 - first_utc) / 1 ngay).
- F3(D) = TB rate x 8/interval_h cac moc funding ts trong [D - 3 ngay, D); khong co moc -> qua loc.
  Loc funding theo chieu (R10): don vi BUY bi loai neu F3 > +0,0005; SELL bi loai neu F3 < -0,0001.
- SMA20(x, d) = TB cac close ngay hop le d-19..d (can >= 18). UP(x, D) = C(D-1) > SMA20(D-1) VA SMA20(D-1) > SMA20(D-6);
  DOWN doi xung (thieu -> khong UP, khong DOWN).
- beta(D) = he so OLS co intercept, log-return ngay sym theo BTCUSDT tren cac ngay D-30..D-1 co ca hai return; >= 20 cap; kep [0, 3];
  thieu -> 1.
- ADX14(D) (chi chan doan): Wilder tren nen ngay hop le (bo ngay trong), gia tri cua ngay hop le cuoi <= D-1; can >= 28 nen.
- Phan vi cat ngang: numpy 'linear' tren cac symbol co tier > 0 ngay D va gia tri huu han. So sanh voi nguong co dung sai tuong doi
  1e-9 (chong nhieu float khi coin nam DUNG nguong).
- tick(D) = tick suy tu gia ngay D-1 (gia tri huu han gan nhat truoc D): buoc lon nhat dang {1,2,5}x10^k <= hieu nho nhat giua 2 gia
  khac nhau sao cho >= 99,9 % gia O/H/L/C la boi so; < 20 gia khac nhau -> tick ngay truoc.
- s_hat(D) (R3-5) = spread Abdi-Ranaldo tren nen 1m cua NGAY HOP LE GAN NHAT trong [D-7, D-1] (khong dung gia tri cu hon 7 ngay);
  khong co -> s_hat = 2 x san truot tier cua don vi (T1 4 / T2 10 / T3 20 bps). Khong bao gio dat s_hat = 0 do thieu du lieu.
- COND_A(t0) = |log(C[t0-1]/C[t0-61])| >= 2,5 sigma_1d/sqrt(24) VA quote volume 60' truoc t0 >= 3 x (TB quote volume ngay 30 ngay
  truoc)/24. COND_B(t0) = RV 24 gio BTCUSDT (24 log-return gio truoc t0, can >= 20) / sigma_1d(BTC, D) >= 1,5.
  Tham so COND la hang so prereg trong code (COND_PREREG); KHONG co bien moi truong nao doi duoc (R3-1).

## 4. Don vi luoi MOT BEN (M1)
- Dat tai moi dau gio t0 (24 lan/coin-ngay) voi moi (c, k); m0 = close phut t0-1 (phai hop le); d = c x sigma_1d(D).
- c {0,1; 0,2; 0,4}; T = W = round(k c^2 1440) phut, k {2; 8} (sigma_1m := sigma_1d/sqrt(1440)): 29/115/115/461/461/1843'.
- Moi (sym, t0, c, k) sinh HAI don vi DOC LAP: BUY = 1 lenh mua tai L_b = floor_tick(m0(1-d)) song W phut; SELL = 1 lenh ban tai
  L_s = ceil_tick(m0(1+d)) song W phut. Ben nay khop KHONG huy ben kia (khong OCO, khong "khop doi").
- Bo qua neu d x m0 < 4 tick, t0 + 2T + 61 vuot cuoi du lieu, hoac m0 sau delist.
- Thoat: mua tai L_b -> ban tai X = ceil_tick(L_b(1+d)); ban tai L_s -> mua tai X = floor_tick(L_s(1-d)). Het han: close phut f+T
  (f = phut khop; phut lo -> phut hop le dau tien sau do).
- PnL (phan so notional luc vao, xuat bps): gross = side x (ra - vao)/vao; net = gross + funding - phi - truot.
- net_h = net - side x beta(D) x (B[x] - B[f]) / B[f]; B[m] = close BTCUSDT phut hop le cuoi <= m; f/x = phut khop/thoat. Luat KHONG
  tru phi hedge (bao cao them muc 9 (13)). NEUTRAL = gop moi don vi BUY va SELL (trong so 1 moi don vi da khop).

## 5. Hai mo hinh khop (ap cho tung ben)
| Quy tac | K_OPT | K_PESS |
|---|---|---|
| Khop lenh mua L (ban doi xung) | low <= L (cham) | low <= L - 1 tick (xuyen) |
| Gia khop | L (ke ca phut mo da vuot muc) | L |
| Thoat limit | tu chinh phut khop (thu tu co loi O->L->H): high >= X | tu phut f+1: high >= X + 1 tick |
| Gia da vuot X luc dong phut khop | bao ham (vong tron cung phut) | thoat TAKER tai dung X o phut f+1, phi taker 0,05 % VA tru truot s = max(san tier, s_hat/2) (R3-4) |
| Het han | close phut f+T, khong spread, phi maker 0,02 % | close phut f+T, taker 0,05 % + truot max(san tier, s_hat/2) |
| Phi maker | 0,02 % | 0,04 % (stress) |
| Delist giua don vi | close phut hop le cuoi, taker 0,05 % | idem + truot 50 bps |
San truot tier: T1 2 / T2 5 / T3 10 bps. Lo <= 60 phut: khong khop trong lo, lenh van song. Don vi co chuoi lo > 60 phut giao
[t0-1, ket thuc] -> LOAI (dem V3; ti le loai bao cao muc 9 (12)). Funding: moc s tinh khi f < s <= x; tien = -side x rate x
close(phut hop le cuoi < s)/gia vao.

## 6. 32 o gia thuyet (M2) x 2 mo hinh = 64 trial; so trial ho grid 8 + 64 = 72 (R3-14: giu 72)
| Nhom | O | Tap don vi | Thong ke |
|---|---|---|---|
| G-N (18) "chon khung" | (c,k) x tier T1/T2/T3 | moi don vi BUY+SELL cua tier | net |
| G-S (8) "coin cho grid 2 chieu" | (c,k) in {(0,2;2),(0,2;8)} x {ER_LOW, IDEAL_N, COND_A, COND_B}, gop tier | xem duoi | net |
| G-D (6) "mot chieu theo xu huong" | (c,k) in {(0,2;2),(0,2;8),(0,4;8)} x {TREND_BUY, TREND_SELL}, gop tier, bo BTCUSDT | xem duoi | net_h |
- ER_LOW: ER30 <= phan vi 33,33 % cat ngang. IDEAL_N: ER_LOW VA sigma_1d trong [p10, p90] cat ngang VA tuoi >= 90 VA tier <= 2 VA qua
  loc funding theo chieu cua don vi. COND_A, COND_B: muc 3 (NEUTRAL, khong loc chieu).
- TREND_BUY: chi BUY, UP(sym) VA UP(BTCUSDT) VA tuoi >= 90 VA qua loc funding BUY. TREND_SELL: chi SELL, DOWN(sym) VA DOWN(BTC) VA tuoi
  >= 90 VA qua loc funding SELL. O G-D: moi dieu kien PASS va luat dung net_h.
- Co BETA (R4-5, chi o G-D, chi bao cao): BETA = (M net tho nua B > 4 bps) VA (M net_h nua B <= 4 bps), theo diem uoc; luon bao cao
  ca hai so (result.json BETA_detail).

## 7. Thong ke (thay M4 theo R3-1, R3-2, R3-3)
- M(o, nua, mo hinh) = tong thong ke / so don vi DA KHOP (khong loai) trong nua; don vi gan vao ngay cua t0. H0(o): M <= 4 bps.
- Khoi: circular block bootstrap 20 ngay lich (khoi cuoi cat cho du D ngay), chon lai ca mat cat coin cung ngay, B = 2000,
  seed 2026112040 (+1 nua B, +10 K_PESS).
- SE goc (khong ngau nhien): SE = sqrt(sum_b (S_b - M N_b)^2) / sum N tren cac khoi KHONG chong lan 20 ngay (S_b, N_b = tong thong ke,
  so don vi cua khoi b). t = (M - 4) / SE.
- Bootstrap-t STUDENTIZED: moi replicate r tinh M*_r va SE*_r theo CUNG cong thuc tren cac khoi da chon cua CHINH replicate do;
  t*_r = (M*_r - M) / SE*_r.
- Nua B: Romano-Wolf stepdown max-t tren t* cua cac o KHONG INSUFFICIENT (RIENG tung mo hinh khop), FWER danh nghia ALPHA_FWER = 0,04
  (hang so co dinh).
- Nua A: p 1 phia = ti le t*_r >= t (bootstrap-t studentized, cung B, seed nua A), nguong 0,10.
- INSUFFICIENT (R3-3, R4-2; tung o x nua x mo hinh khop) neu BAT KY: (i) so don vi da khop < 200; (ii) so khoi 20 ngay KHONG chong
  lan (dem tu ngay dau cua nua) co >= 1 don vi da khop < ceil(tong so khoi cua nua / 3) (nua B 731 ngay: 37 khoi -> can >= 13; nua A
  914 ngay: 46 khoi -> can >= 16); (iii) M khong huu han hoac SE goc = 0 (hoac khong huu han).
  O INSUFFICIENT: p_RW = 1, khong the PASS, duoc LIET KE, va lam L-A khong dat; t* cua no bi LOAI khoi max-t o MOI buoc RW va khoi
  can tren dong thoi (R4-1); can tren = NaN. O nua A: p = NaN -> khong qua dieu kien (b).
- Replicate co SE* = 0 (hoac khong co don vi, M* / SE* khong huu han): t* cua o do o replicate do = 0 (R4-2).
- Can tren dong thoi (R3-2): c_up = phan vi (1 - ALPHA_UPPER) = 95 % cua max_j(-t*_j) tren cac o KHONG INSUFFICIENT (cung bootstrap);
  can tren_j = M_j + c_up x SE_j. ALPHA_UPPER = 0,05 la hang so RIENG (khong phu thuoc ALPHA_FWER).
- Hang so ALPHA_FWER = 0,04, ALPHA_UPPER = 0,05, MIN_UNITS = 200, B = 2000, khoi 20 nam trong code; runner assert bang gia tri prereg;
  KHONG co bien moi truong / tham so CLI nao doi duoc (GRIDV2_ALPHA, GRIDV2_COND, GRIDV2_MARKET_SYM, GRIDV2_REGISTRY, GRIDV2_V4_SYMS
  co mat -> abort).
- Merge (R4-3): bat buoc --expected-sha EXPECTED_SHA.txt (sha256 klite.py, kref.py, stats.py, runner_kaggle.py = muc 15); abort neu:
  khong dung 5 shard 0..4/5 (thieu / trung chi so / trung thu muc), manifest prereg_constants != True, validate all_pass != True, hang
  so khac prereg, cond != COND_PREREG, mkt_sym != BTCUSDT, sha code trong manifest bat ky shard != EXPECTED_SHA.
- result.json (R4-4) ghi TEST_ONLY / allow_test o dau file; neu allow_test (chi co qua import trong test noi bo) thi "rule" =
  "TEST_ONLY:<luat>" - KHONG BAO GIO la ket qua that.
- C4: cap = s_hat/2 x so chan maker (1 + 1[thoat limit]); M_adj = M - TB cap (G-D: tren net_h).
- Bao cao bat buoc moi o x nua x mo hinh: n dat/khop/loai, P(khop), M, M_neth, M net tho, CI95 bootstrap-t, SE, p, p_RW, INSUFFICIENT,
  can tren dong thoi 95 %, gross, gross_h, phi, truot, funding, cap, M_adj, P(thoat limit), SD, skew, phan vi 1 %/5 % (histogram
  1 bps), M theo nam, M bo top-3 coin (theo tong thong ke trong o-nua), M bo 3 su kien (t0 trong [dau - 3 ngay, cuoi + 1 ngay) cua
  2022-05-09..13, 2022-11-08..10, 2025-10-10..13), gross moi phut giu, "chi giu" H (muc 9 (10)).

## 8. PASS 1 o (tung mo hinh) va luat quyet dinh
PASS = (o KHONG INSUFFICIENT o ca 2 nua) VA (a) RW bac H0 o nua B (p_RW <= 0,04); (b) M_A > 4 VA p_A <= 0,10; (c) M_adj_B > 0;
(d) M_B bo top-3 coin > 4; (e) M bo su kien > 4 o CA hai nua.
- L-A: CA 32 o duoi K_OPT KHONG INSUFFICIENT o nua B, can tren dong thoi 95 % huu han VA < 4 bps o MOI o => "DONG MANH"; FINDINGS;
  khong engine. Co o INSUFFICIENT (hoac can tren khong huu han) -> L-A KHONG dat (roi ve L-B, liet ke cac o do).
- L-B: khong o nao PASS duoi K_OPT va khong dat L-A => "DONG THEO NGAN SACH", ghi MDE that tung o + danh sach o INSUFFICIENT;
  chi mo lai voi bang chung NGOAI.
- L-C: co o PASS duoi K_OPT nhung khong duoi K_PESS => prereg rieng engine muc giao dich CHI cho cac o do.
- L-D: co o PASS duoi K_PESS => prereg rieng walk-forward (moi lua chon chi tu cua so train cua fold - sua ro ri N3).
- Thu tu ap: L-D > L-C > L-A > L-B (runner tinh "rule"; MASTER doi chieu tay). Buoc 3-5 chi cho o PASS.

## 9. Bang chan doan (CHI BAO CAO - khong la bang chung, khong PASS/FAIL)
Moi (c,k) cua G-N gop tier x mo hinh x nua: (1) BUY vs SELL; (2) tuoi < 90 / >= 90; (3) funding bi loc / khong; (4) ADX14 < 20 /
20-25 / > 25 / thieu; (5) sigma cat ngang <= p10 / giua / >= p90; (6) gio UTC; (7) nam; (8) ti le thang M > 0 + trung vi M thang (R25);
(9) nguoc xu huong (BUY trong DOWN&DOWN, SELL trong UP&UP; net va net_h); (10) o G-D: gross moi phut giu vs H = TB tren MOI don vi
da dat (khong loai) cua side x ln(close[t0+T-1]/m0)/T; ghi "khong hon giu" neu <=.
Them (R3-9): (11) moi o gop tier (G-S, G-D) x mo hinh x nua TACH theo tier T1/T2/T3: so don vi dat / khop, M, M_neth, ti le loai lo;
(12) ti le don vi bi loai do lo > 60' theo o x nua x mo hinh; (13) o G-D: M_neth va M_neth - 2 x 5 bps x beta (phi hedge taker 2 chan).
Ung vien tinh chinh buoc 4 phai qua prereg WF.

## 10. Cong suat + FWER (power.py, mo phong TONG HOP qua DUNG process_symbol, RW studentized 4 %)
Mo phong "base": 200 panel tong hop (BTC + 5 alt: T1 2, T2 2, T3 2; sigma ngay 3/3,5/5/5/6,5/6,5 %; beta 0,9-1,3; 2 alt tre; funding AR;
soc gia+khoi luong cho COND_A), 731 ngay nua B + 45 ngay warm-up, 2 buoc/phut, KHONG drift (null), chay QUA DUNG process_symbol
(32 o, mat na, net_h), CA K_OPT VA K_PESS. M that tung o (moi mo hinh) = gop 200 panel; dich ve san (H0 bien) roi chay stats.cell_stats
(RW studentized, ALPHA 0,04, B = 1000) 32 o moi panel. FWER = ti le panel co >= 1 o bi bac.
FWER do (out_synth_r4/power32.json, cai dat FINAL: INSUFFICIENT (i)-(iii) loai khoi max, t* = 0 khi SE* = 0; R = 200 panel base, B = 1000):
| mo hinh | FWER @ 4 % (luat prereg) | min_units = 0 (chi bo (i)) | tham khao 5 / 3 / 2 / 1 % | nguong max-t median |
|---|---|---|---|---|
| K_OPT | 0,035 +- 0,013 | 0,035 | 0,040 / 0,030 / 0,015 / 0,015 | 3,59 (z chuan 3,02) |
| K_PESS | 0,040 +- 0,014 | 0,040 | 0,045 / 0,030 / 0,015 / 0,010 | 3,60 |
=> FWER do <= 5 % ca 2 mo hinh: GIU ALPHA_FWER = 0,04. (A1 doc lap, cai dat R3: base 160 panel 0,031/0,031; wide 14 coin 0,037/0,037.)
Tren panel tong hop KHONG o nao INSUFFICIENT (0 % panel), nen FWER R4 = R3. So don vi khop / panel (731 ngay, 6 coin) nho nhat:
S_COND_A c0,2 k2 1 166; S_COND_A c0,2 k8 1 894; S_COND_B c0,2 k2 3 830; S_COND_B c0,2 k8 6 044; D TREND 6 244-11 250; G-N 27 866-49 299;
S_ER_LOW 29 915 / 48 576; S_IDEAL_N 11 687 / 19 113 (R4-7).
Cong suat 31 o khi co 1 o thua (R4-2 (2), L12; 31 o +3,5 sd that, o S_COND_A_c0.2_k2 o H0 bien; 200 panel, B 1000; CHI BAO CAO):
| trang thai o thua | don vi o thua (median) | INSUFFICIENT | cong suat TB 31 o K_OPT / K_PESS | o thua bi bac (sai) |
|---|---|---|---|---|
| day (du lieu goc) | 1 164 | 0 % | 0,651 / 0,656 | 0,015 / 0,015 |
| thua 13 khoi x 1 ngay (NGAY TREN nguong (ii)) | 232 | 0 % | 0,582 / 0,585 | 0,015 / 0,015 |
| thua 12 khoi x 1 ngay (duoi nguong -> loai khoi max) | 220 | 100 % | 0,667 / 0,674 | 0 / 0 |
=> O thua vua du dieu kien van keo cong suat 31 o khac xuong ~7 diem % (0,65 -> 0,58); duoi nguong thi bi loai va khong keo
(0,67). Khong tu doi nguong (R4-2); MASTER xem xet neu can.
Cong suat (MDE_B quy ve so coin that A 10/50/130, B 10/50/420; bps VUOT san 4). "chuan" = (z_(1-0,04/32) + 0,84) x SE_B;
"max-t" = (nguong max-t studentized do duoc tren panel, median + 0,84) x SE_B (bao thu hon; panel 6 coin co duoi t day hon
universe that ~420 coin).
| o (K_OPT; K_PESS chenh <= 0,1) | MDE_B chuan / max-t | o | MDE_B chuan / max-t | o | MDE_B chuan / max-t |
|---|---|---|---|---|---|
| N c0,1 k2 T1/T2/T3 | 1,0/0,9/0,6 ; 1,1/1,0/0,7 | N c0,2 k8 T1/T2/T3 | 5,3/4,9/3,6 ; 6,1/5,7/4,2 | S ER_LOW / IDEAL_N c0,2 k2 | 1,9/2,3 ; 2,2/2,7 |
| N c0,1 k8 T1/T2/T3 | 1,5/1,4/1,0 ; 1,8/1,6/1,2 | N c0,4 k2 T1/T2/T3 | 8,5/7,7/5,8 ; 9,7/8,8/6,6 | S COND_A / COND_B c0,2 k2 | 2,2/2,7 ; 2,5/3,1 |
| N c0,2 k2 T1/T2/T3 | 2,5/2,2/1,5 ; 2,8/2,5/1,8 | N c0,4 k8 T1/T2/T3 | 19,5/17,9/14,2 ; 22,3/20,5/16,3 | S ER_LOW / IDEAL_N c0,2 k8 | 4,3/5,1 ; 5,0/5,8 |
| D TREND_BUY/SELL c0,2 k2 | 1,5/1,6 ; 1,7/1,8 | D TREND_BUY/SELL c0,2 k8 | 3,8/4,1 ; 4,4/4,7 | S COND_A / COND_B c0,2 k8 | 4,2/6,4 ; 4,8/7,3 |
| D TREND_BUY/SELL c0,4 k8 | 13,1/14,2 ; 15,1/16,3 | | | | |
Ti le don vi tap / G-N gop cung (c,k) tren panel tong hop: ER_LOW 0,34; IDEAL_N 0,13; COND_A 0,013; COND_B 0,04; TREND_BUY 0,07;
TREND_SELL 0,08 (COND_A/COND_B phu thuoc tan suat soc tong hop - du lieu that co the khac nhieu; INSUFFICIENT theo muc 7).
M null tren panel (dac tinh bo sinh, xem ghi chu duoi): K_OPT -11..-46, K_PESS -17..-54 bps/don vi.
Ghi chu (R3-8): null net trung binh tren panel tong hop la DAC TINH CUA BO SINH tong hop (2 buoc/phut -> overshoot roi rac; soc
1/4000 phut), KHONG phai cua mo hinh phi/truot. Phi + truot chi giai thich ~4 bps (K_OPT) va ~9-10 bps (K_PESS). Nguong thuc te de 1 o
co loi the: gross > ~8 bps (K_OPT), > ~13-15 bps (K_PESS). Gioi han: panel 6 coin (rho, phi uoc tu 6 coin), sigma gia dinh, gia lien
tuc (khong luoi tick); SE that co the lon hon 1,5-2x (nhay gia, delist).

## 11. Kiem chung (truoc chay that; ket qua dev o GRIDV2_S1_DEV.md R3, R4)
Oracle 99/99 PASS (518 s, seed 2026112050; out_synth_r4/test_results.json; chay sau lan sua code cuoi). Test moi R4 (5):
- stats_insufficient_excluded_from_max: 31 o +3,5 sd them 1 o thua 300 don vi / 3 ngay (cuc doan, INSUFFICIENT (ii)): p_RW cua 31 o,
  nguong max-t va c_up GIONG HET khi khong co o thua (cong suat 0,968 = 0,968); o thua p_RW 1, can tren NaN.
- stats_insufficient_condition_ii_blocks: 731 ngay 12 khoi -> INSUFFICIENT "ii", 13 khoi -> du (can 13); 914 ngay 15 -> INSUFF, 16 -> du.
- stats_se_star_zero_tstar_zero: SE* = 0 / replicate khong don vi -> t* = 0; o 12 khoi gia tri a + 1 khoi b: p, c_up huu han.
- merge_shard_guards_sha_TEST_ONLY: 5 shard hop le -> chay, TEST_ONLY False, rule L-A; thieu shard, trung thu muc, trung chi so,
  khong --expected-sha, sha stats lech, cond sai, mkt_sym sai, prereg_constants False -> deu abort; allow_test -> TEST_ONLY True,
  rule "TEST_ONLY:...", khoa dau result.json = TEST_ONLY.
- merge_beta_flag_R4_5: net 30 / net_h -10 -> BETA; net 30 / net_h 30 (khong PASS do nua A) -> KHONG BETA (luat cu gan nham);
  net 2 -> khong; BETA_detail 6 o G-D.
Test R3 (16, van chay va PASS trong bo R4):
- RW studentized: SE khoi vs giai tich (TB 0,97; min 0,65 - sat nguong 0,65 cua test, ~37 khoi); FWER null 32 o @ 4 %: Gauss 0,020,
  duoi day t4 + N Poisson khong deu 0,043 (300 sim, gioi han 0,074); hieu ung cay (4/32 o +5 SE): cong suat 0,955-0,965, FWER trong
  28 o null 0,030 (200 sim).
- INSUFFICIENT + can tren: o 0 don vi / 150 don vi -> INSUFFICIENT, p_RW 1, can tren NaN, p nua A NaN; c_up 95 % (2,33) < 99 % (2,88).
- Merge/luat (bang reduced gia, ALPHA_FWER 0,04, ALPHA_UPPER 0,05): tat ca am -> L-A, can tren merge = tinh lai doc lap tu stats
  (c_up 95 % 3,23 vs 99 % 3,71); 1 o NaN nua B -> L-B (liet ke); 1 o 143 don vi -> L-B (liet ke); 1 o that su > san + 1 o lon nhung
  INSUFFICIENT -> L-D, chi o that PASS.
- Guard: env cam (5 bien x check_env + merge) -> abort; allowlist (hop le; slug la; file 2026; nam lech; thieu slug; 2 lifecycle;
  parquet la; file ngoai slug); V2 10/10 000 OK, 11/10 000 FAIL; V6 (%-units, qua nho, interval 3h FAIL; suy 99,5 % OK); s_hat ffill 7
  ngay roi 2 x san tier.
- Runner lake gia (allowlist slug that): V0-V6 PASS; khoi dong lai tu checkpoint: bo dem V3 giong het; merge tu choi shard test khi
  khong allow_test; bang chan doan (11) 48 dong, (12) 128, (13) M_neth - phi hedge < M_neth.
Giu tu R2 (chay lai tren code R3, deu PASS): E2a ke toan 0 sai; don vi mot ben vs dap an giai tich (|z| <= 1,4 RW; drift z_sell 2,81
bien, 10 seed khac TB 0,45); MC doc lap |z| <= 1,6; bracket; E2c (z -2,2); bien 8/8; klite vs kref 9 240 don vi 0 lech; feature tay +
kref; mat na 32 o runner vs kref 1 800 don vi 0 lech; net_h 0 lech; khong nhin tuong lai 0 khac; tier PIT; runner GBM 12/12 |z| <= 3;
lake beta G-D 12/12.
Doi chieu doc lap (R3-13): kref KHONG doc lap hoan toan voi klite (cung hang so dung sai 1e-7 / 0,01 tick, cung cach hieu truot
taker_beyond) -> "0 lech klite vs kref" mot phan la common-mode. Bo mo phong rieng cua A1 (audit_s1/a1_mysim.py, viet tu prereg,
8 024 don vi) la doi chieu doc lap thu ba: 0 lech ngoai 14 don vi taker_beyond lech dung bang truot (nay da ghi ro muc 5, R3-4).
Khi chay THAT: V0-V6 ALL PASS bat buoc truoc khi doc M: V0 registry + so dong doc = metadata; V1 ts < 2026 va trong thang; V2 dong
active xau <= 0,1 %/nam (dem, bao cao); V3 lo + don vi loai + doi chieu feature pass1 = pass2 (0 ngay lech; bo dem luu trong checkpoint);
V4 rac sau moc tc (gia, active, qv, funding, tier, nguong cat ngang, BTC) -> don vi ket thuc truoc tc giong het (ket qua, net_h, tap);
V5 doc lai parquet tho + kref (net, d, tick, ER30, UP/DOWN, beta, F3) 8 don vi/shard; V6 median |rate| funding / interval_h.

## 12. Holdout, an toan
- Niem phong moi du lieu >= 2026-01-01 (chi owner mo). Khoi kiem ngoai mau tuong lai tinh tu 2026-10-14 (tai lieu: SCREEN_WIDE C
  toi 2026-09-30, MM_Q1 K 2026-01..09, mm_markout DEV <= 2026-06 va HO khong chay; LOB_T1 dung spot BNBUSDT 2026-10-06..13).
- Khong doc du lieu that khi dev; chi chay that sau audit doc lap PASS va MASTER commit prereg (D6).

## 13. Chay that + chi phi
- Toc do do (Oracle, R2): ~15 s CPU / symbol-lich-day-du cho 32 o x 2 mo hinh x 2 ben. Universe ~527k sym-ngay ~ 320 symbol-lich-day-du
  => ~80 phut CPU tong + pass1 (doc ca OHLC, 15,7 GB, ~15-30 phut/shard).
- KN 5 kernel CPU song song (shard = crc32(symbol) mod 5): ~40-70 phut/kernel, TONG ~4-6 kernel-gio. /kaggle/working tam ~2 GB/shard
  (agg_sym + *.v3.json, xoa sau reduce; GRIDV2_KEEP_SYM=1 de giu checkpoint); tai ve chi reduced/ (~10-30 MB/shard) + validate.json +
  manifest.json + run.log.
- Mount: DUNG 7 dataset allowlist (muc 1). Env CHI: GRIDV2_SHARD=i/5 (+ GRIDV2_INPUT/GRIDV2_OUT/GRIDV2_KEEP_SYM van hanh). Dung neu
  bat ky V0-V6 FAIL (V2/V6 abort som).
- Gop + thong ke tren Oracle: python3 runner_kaggle.py merge OUT --expected-sha s1/EXPECTED_SHA.txt d0 d1 d2 d3 d4 -> result.json,
  diag.json (alpha, B, san co dinh trong code; guard R4-3).
  Truoc merge BAT BUOC (A1 vong 3, H1): sha256sum s1/EXPECTED_SHA.txt =
  4f764be8a1ab480b2a10af390dbf39b82979071d4d250d3f81fca2bf1831987b (muc 15); khac -> DUNG.
  Truoc merge BAT BUOC (A1 vong 3, H2): manifest.inputs (sha256 file lifecycle + funding) cua 5 shard phai GIONG HET nhau va
  V0 (so dong kline theo nam) PASS o ca 5 shard; khac -> DUNG, khong doc M.

## 14. Diem lech / cai dat cu the so voi S1_MASTER_DECISIONS (+ R3)
L1 (DRAFT2: alpha 1 % thay luoi M4) - BO, thay bang R3-1: RW studentized, ALPHA_FWER 4 % co dinh.
L2 Dung sai 1e-9 tuong doi khi so sanh voi nguong phan vi; phan vi = numpy 'linear'. (R3-14: chap nhan)
L3 F3: rate x 8/interval_h theo cot interval_h; thieu cot -> suy tu khoang cach moc. (chap nhan)
L4 net_h: B[f], B[x] = close BTC phut hop le cuoi <= phut khop/thoat; luat khong tru phi hedge. (chap nhan; bao cao (13))
L5 M5 (10) H tren don vi da dat KHONG bi loai lo; close[t0+T-1] thieu -> close hop le cuoi <= phut do. (chap nhan)
L6 FWER/cong suat: do CA K_OPT va K_PESS; van panel 6 coin, gia lien tuc, B 1000 trong mo phong (that 2000). A1 do them panel
   14 coin (wide): RWst 4 % FWER 0,037.
L7 Bang chan doan (6) gio va (7) nam tren G-N gop tier; (8) thang dung net. (chap nhan)
L8 (DRAFT3) - THAY bang R4-1: o INSUFFICIENT bi loai khoi max-t moi buoc RW va khoi can tren; replicate SE* = 0 -> t* = 0 (R4-2).
L11 (moi) Replicate KHONG co don vi nao cua o (M*, SE* khong xac dinh) cung gan t* = 0 nhu SE* = 0 (R4-2 chi noi SE* = 0; day la cach
   gan nhat, khong gan +-inf). Voi o khong INSUFFICIENT (>= ceil(nb/3) khoi co don vi) truong hop nay hiem.
L12 (moi) Nghien cuu cong suat R4-2 (2): o thua = S_COND_A_c0.2_k2 (o 20, thua nhat theo A1 G1), giu 1 ngay (nhieu don vi nhat) trong
   moi khoi cua 13 (ngay tren nguong) / 12 (duoi nguong) khoi cach deu, nhan S, N cung he so de >= 200 don vi; 31 o con lai dich
   +3,5 sd that (sd qua panel), o thua o H0 bien.
L9 (moi) Test noi bo can tham so khac prereg (COND_A vmult 0,5 de co su kien tren lake gia, symbol thi truong AAAUSDT, registry lake gia):
   truyen qua tham so ham run(test_overrides=...) - KHONG co duong vao tu CLI / env; manifest ghi prereg_constants = False va merge tu
   choi shard do (tru allow_test trong test).
L10 (moi) V6 voi interval_h SUY (thieu cot): dung sai 99 % dong thuoc {1,2,4,8} (khoang cach moc co the lech do lo du lieu funding).

## 15. sha256 code (ban dev sau lan sua cuoi, Oracle w3/gridv2/s1/)
  196f458489c5a808754d4afc39c2ad03f9149d57936de7f84c810074b8652680  klite.py
  6de0e412633658f1d548d28c7a650ff9b0e43b1a5f6cc3e64dbe93c51c928ff2  kref.py
  012092d70250810e85c053ef31412e49124e99d2bde6ef6959f9ce9ff666f555  synth.py
  975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4  stats.py
  9ddb3cef497bc578188ef164f2d98920bc2739c07b00c2926607642f2d72ef91  runner_kaggle.py
  eeb018b452652fe0cb5cbdaf9f2b0d4641d2c8cf05147cd98e40bc3fd61b8398  test_klite.py
  f95706c0a96f1b6e1af314a746a32da07f8ceecaf35c6a19410714b7e8e78a3c  power.py
  4f764be8a1ab480b2a10af390dbf39b82979071d4d250d3f81fca2bf1831987b  EXPECTED_SHA.txt
  b60d519d0afa65ee19c923e9444ea9730d13d7fea62e829cdff9089d88a30e66  out_synth_r4/test_results.json
  f3aac9b1ccc68cf049b9058a028867af075ae0d1579226b3756ba75de65fa7a1  out_synth_r4/power32.json
  4dfa0362d399f11793e9d6b9747132f49e378696bad0d70aa44201c75b5db868  out_synth_r4/power32_table.md
  294883dca06ecf5847e6588ce7ea0ec78c4367d4bbc31ab36037d3699ea3252b  out_synth_r4/hand_units.txt
  (test 99/99 va power chay voi DUNG ban code nay; khong sua code sau test. EXPECTED_SHA.txt = 4 dong dau klite/kref/stats/runner cho merge --expected-sha. Ban R3 luu w3/gridv2/_old_v3/.)

## 16. Quyet dinh da chot (R4-6) va gioi han da biet
D1 Thong ke: Romano-Wolf stepdown max-t, bootstrap-t studentized khoi 20 ngay, ALPHA_FWER = 0,04 (FWER do <= 5 % ca K_OPT, K_PESS -
   muc 10), can tren dong thoi ALPHA_UPPER = 0,05, B = 2000. Khong doi sau commit.
D2 INSUFFICIENT theo muc 7 (i)-(iii); o INSUFFICIENT khong PASS, bi loai khoi max-t/can tren, duoc liet ke va chan L-A.
D3 Phi hedge G-D: luat dung net_h KHONG tru phi hedge; bang chan doan (13) bao cao net_h - 2 x 5 bps x beta (chi mo ta).
D4 Truoc chay that: audit doc lap A1 vong 3 doc ban FINAL + chay lai test_klite.py; MASTER commit prereg + EXPECTED_SHA.txt; merge
   chi voi --expected-sha.
Gioi han da biet (chua the biet truoc khi cham du lieu, he qua da dinh san):
- Tan suat / do thua COND_A, COND_B (va cac o G-S / G-D khac) tren du lieu that: neu o nao INSUFFICIENT o nua B -> L-A khong dat
  (roi ve L-B neu khong o nao PASS), o do duoc liet ke; neu INSUFFICIENT o nua A -> o do khong the PASS.
- FWER chua do voi gia luoi tick, volatility clustering > 20 ngay va ~420 coin that; panel tong hop 6 coin.
- Layout /kaggle/input that phai dung ten 7 slug allowlist; khac -> abort (khong doc M).
- Don vi rate / interval_h funding that: V6 abort neu ngoai khoang.

## 17. Bang xu ly phat hien audit A1 (F1-F16 vong 1, G1-G7 vong 2) - dong theo ban sha muc 15
| Ma | Muc | Xu ly | File:dong |
|---|---|---|---|
| F1 | MAJOR | ALPHA_UPPER = 0,05 rieng; c_up = phan vi 95 % max(-t*) tren o du du lieu | stats.py:17, 105-108; runner_kaggle.py:46, 1145-1149 |
| F2 | MAJOR | ALPHA_FWER = 0,04 co dinh; env cam -> abort; assert hang so; merge guard | runner_kaggle.py:45-62, 113-126, 983-1034 |
| F3 | MAJOR | RW stepdown max-t STUDENTIZED (SE* tu tong khoi cua chinh replicate) | stats.py:27-130 |
| F4 | MINOR | INSUFFICIENT: khong PASS, L-A khong dat, liet ke | stats.py:76-85; runner_kaggle.py:1134, 1145-1149 |
| F5 | MINOR | Ghi ro truot taker_beyond K_PESS (giu code) | prereg muc 5 |
| F6 | MINOR | s_hat ngay hop le gan nhat trong 7 ngay; khong co -> 2 x san tier | runner_kaggle.py:56, 128-139, 480, 540 |
| F7 | MINOR | V2 dem theo nam, abort chi khi > 0,1 % | runner_kaggle.py:53, 141-146, 286-291, 878-883 |
| F8 | MINOR | Allowlist 7 slug, file 2026 -> abort, ten parquet chat, 1 lifecycle | runner_kaggle.py:57-58, 169-220; synth.py:121-125, 181 |
| F9 | MINOR | Sua cau null -11..-46 bps (dac tinh bo sinh) | prereg muc 10 |
| F10 | MINOR | p nua A = bootstrap-t studentized | stats.py:92, 127-130; runner_kaggle.py:1134-1135 |
| F11 | NOTE | Ghi nhan muc doc lap kref; mysim A1 la doi chieu thu ba | prereg muc 11 |
| F12 | NOTE | Bang (11) tach tier o G-S/G-D | runner_kaggle.py:591-598, 1172-1177 |
| F13 | NOTE | Bang (12) ti le loai lo > 60' | runner_kaggle.py:1085, 1178-1186 |
| F14 | NOTE | V6 funding -> abort | runner_kaggle.py:54-55, 148-167, 888-895 |
| F15 | NOTE | Checkpoint luu bo dem V3 | runner_kaggle.py:827-846, 907-927 |
| F16 | NOTE | Test merge/luat/guard/RW studentized | test_klite.py:512-586, 940-1229 |
| G1 | MAJOR | (a) o INSUFFICIENT loai khoi max-t moi buoc RW + can tren (R4-1); (b) them dieu kien (ii) so khoi >= ceil(nb/3) (R4-2); do cong suat 31 o co/khong o thua (muc 10) | stats.py:19, 76-108; power.py (sparsify, power31_sparse); test stats_insufficient_excluded_from_max, stats_insufficient_condition_ii_blocks |
| G2 | MINOR | Merge: bat buoc --expected-sha; dung 5 shard 0..4/5 khong trung/thieu; cond, mkt_sym, prereg_constants, all_pass, hang so; sha code manifest == EXPECTED_SHA | runner_kaggle.py:51-52, 968-1034, 1190-1199; s1/EXPECTED_SHA.txt; test merge_shard_guards_sha_TEST_ONLY |
| G3 | MINOR | result.json: TEST_ONLY / allow_test o dau file; rule = "TEST_ONLY:<luat>" khi allow_test; allow_test khong co tu CLI | runner_kaggle.py:1053, 1152-1154; test merge_shard_guards_sha_TEST_ONLY |
| G4 | NOTE | Replicate SE* = 0 (va khong don vi) -> t* = 0 | stats.py:60-65, 90; test stats_se_star_zero_tstar_zero |
| G5 | NOTE | Co BETA = net tho B > 4 VA net_h B <= 4; BETA_detail bao cao ca hai so | runner_kaggle.py:1139-1143; test merge_beta_flag_R4_5 |
| G6 | MINOR | Muc 16 viet lai thanh quyet dinh da chot + gioi han da biet | prereg muc 16 |
| G7 | MINOR | So don vi/panel dung power32.json (muc 10) | prereg muc 10 |

## 18. MASTER duyet (2026-11-20)
- Ban nay = PREREG_GRIDV2_S1_FINAL.md cua dev (sha256 09149f1738c0ea6d6941396f81eca4f22072ddbf551032c2da994de7b1212198) + 3 sua VAN BAN
  cua MASTER: dong trang thai (dau file), 2 dong 'Truoc merge BAT BUOC' o muc 13 (A1 vong 3 H1, H2), va muc 18 nay. Khong sua code.
- Audit doc lap: vong 1 FAIL (F1-F16) -> vong 2 PASS-WITH-MINOR (G1-G7) -> vong 3 PASS-WITH-MINOR (chi con H1 bat buoc = da them;
  H2 = da them dang kiem tay; H3-H5 ghi nhan). Bao cao: v12/A1_GRIDV2_S1.md, _R2.md, _R3.md.
- MASTER chap nhan cac diem lech L2-L7, L9-L12. Nguong INSUFFICIENT (ii) = ceil(so khoi / 3) GIU NGUYEN du o thua ngay tren nguong
  keo cong suat 31 o khac ~2-7 diem % (da biet truoc khi cham du lieu; khong doi sau).
- So trial ho grid: 8 (vong 1) + 64 = 72. Code ghim theo sha muc 15; ban sao code: research/gridv2_s1/ (cung commit).
- Du lieu >= 2026-01-01 van NIEM PHONG. Ket qua S1 chi quyet dinh co lam tiep buoc 3-5 cho tap nao; khong doi cau hinh live.
