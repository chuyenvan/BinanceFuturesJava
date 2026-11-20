# PREREG_GRIDV2_S3_FINAL2 - Giai doan S3 "WICK": lenh limit SAU dat san (mot ben), 12 o, 2 mo hinh khop bao nhau
Ngay 2026-11-21. Tac gia: agent thiet ke+dev S3. Trang thai: FINAL2 (ban R3: FINAL 57d89db4... + audit doc lap A1
(v12/A1_GRIDV2_S3.md, F1-F11) + quyet dinh MASTER R3-1..R3-9, muc 16, 18). CHUA cham du lieu that. Chua MASTER commit.
Ban TU CHUA (khong viet "nhu S1"): moi dinh nghia can thiet duoc chep lai duoi day.
Can cu: w3/gridv2/S3_MASTER_DECISIONS_1120.md (sha256 a89bd9ad1f996bf0f9a57634a06ceeb65eeb5092f5e032fa82ede16a6273f70f);
prereg S1 docs/prereg/PREREG_GRIDV2_S1.md (commit 4ecc655d) + PREREG_GRIDV2_S1_ADD1.md (commit 19608bbd); code S1 ghim
(w3/gridv2/s1 = research/gridv2_s1); audit S1 v12/A1_GRIDV2_S1{,_R2,_R3,_R4}.md; ket qua S1 v12/RESULT_GRIDV2_S1.md.
Code + ket qua tong hop: w3/gridv2/s3/ (sha256 muc 15); bao cao dev v12/GRIDV2_S3_DEV.md.
Quy uoc: bps = 0,01 %; UTC; nua A = 2021-07-01..2023-12-31 (XAC NHAN, 914 ngay), nua B = 2024-01-01..2025-12-31 (CHINH, 731 ngay).
Moi dieu duoi day chot TRUOC khi cham du lieu that; doi sau do = trial moi + exploratory.

## 0. Cau hoi, pham vi, boi canh
Chi dao owner 20/11: thu "vai tro khac" cua grid = lop thuc thi cho loi the crash-buy (c3). Kiem ke (v12/EXEC_GRID_INVENTORY_1120.md)
cho thay da DONG: vao lenh bang limit / bac thang thap hon gia tin hieu (EXEC_RESULT 10-12 P1-P4 NO-GO), DCA nong/sau theo %
(DCA_SIGNAL_GATE V1-V4, ROUND_CAP, NUP2 B2/B3), bac thang chot loi (GRIDP_T3 FAIL), luoi co dinh sau cu sap BTC (GRIDP_T1 FAIL).
CHUA thu: lenh limit SAU dat SAN tren so (khop chac chan khi gia XUYEN qua, khong phu thuoc hang doi), bat phan "rau" trong phut
ma lenh MARKET cua c3 (vao sau khi nen dong + ~7 s) khong bat duoc.
Cau hoi S3: KINH TE DON VI cua 1 lenh sau mot ben (dat dau moi gio, song 60 phut, muc d = c x sigma_1d, thoat limit khi hoi nua
quang duong, het han T phut) - net trung binh / don vi DA KHOP co > 4 bps, o ca 2 nua, duoi mo hinh khop BI QUAN (K_PESS), khong do
<= 3 coin, khong do 3 su kien da biet, khong do MOT khoi 20 ngay? S3 CHUA mo hinh von / margin / chong lan voi c3 (buoc sau, chi
neu PASS).
BOI CANH BAT BUOC GHI (S3-10): MASTER DA BIET ket qua DCAGRID_A3 (leg DCA -50/-75/-90 lai gan nhu chi o su kien 2025-10-10..13)
=> gia thuyet S3 duoc hinh thanh SAU khi thay du lieu goi y; vi vay co dieu kien (e) bo 3 su kien VA (e') bo khoi 20 ngay lai nhat.
So trial ho grid: 74 (sau S2) + 24 (12 o x 2 mo hinh) = 98.

## 1. Du lieu (chi doc sau commit prereg + sha) - GIONG S1 + ADD1
- Kline 1m: Kaggle chuyendinh/vz-kline1m-2021..2025 (kline1m-YYYY-MM.parquet, 1 row group = 1 symbol; cot ts (ms open), sym, open,
  high, low, close, volume, quote_volume, active). Doc 2021-05-01..2025-12-31 (2 thang dau chi warm-up). Registry dong metadata/nam:
  {2021: 60001411, 2022: 75973640, 2023: 104401093, 2024: 155015111, 2025: 256801320}.
- Funding: CHI chuyendinh/gridp-t1-funding (funding-2021..2025.parquet: ts, sym, interval_h, rate); KHONG mount vz-funding (co 2026).
  Thieu cot interval_h -> suy = khoang cach 2 moc lien tiep (gio, lam tron, kep [1, 8]).
- Universe: chuyendinh/gridp-lifecycle (lifecycle.parquet: symbol, first_utc, last_utc, ascii); bo dong first_utc >= 2026-01-01.
- ALLOWLIST: runner duyet MOI file duoi input; moi file phai nam trong DUNG 1 trong 7 slug vz-kline1m-2021..-2025, gridp-t1-funding,
  gridp-lifecycle; du 7 slug; ten file chua "2026" -> abort; trong slug chi chap nhan dung ten parquet mong doi (kline1m-YYYY-MM voi
  YYYY = nam slug, funding-YYYY voi YYYY < 2026, DUY NHAT 1 lifecycle.parquet); parquet la / trung thang -> abort. Moi ts < 2026 (assert).
  R3-6 (A1 F7): slug hop le phai la thu muc NGAY TREN file va la thanh phan slug DUY NHAT cua duong dan; 7 slug phai o CUNG cap
  thu muc (cung tien to); thu muc la long slug hop le / slug o cap khac / thu muc con trong slug -> abort.
- Phut hop le = co dong, active = True, O/H/L/C huu han > 0; con lai = lo.
- Kiem V (TAT CA PASS truoc khi doc bat ky M nao; ghi validate.json moi shard):
  V0a: tong dong metadata MOI file cua nam == registry. V0b: so dong pass1 doc cua nam == tong metadata cac file DA MO; tap file bo
  qua == tap theo quy tac "thang BAT DAU truoc 2021-05-01 - 31 ngay" == {kline1m-2021-01, -02, -03}; registry - dong doc == tong
  metadata file bo qua (chinh xac). V1: moi ts trong dung thang cua file va < 2026. V2: dong active co O/H/L/C NaN hoac <= 0 -> phut lo,
  dem theo nam; abort neu > 0,1 % dong active cua bat ky nam nao. V3: dem lo > 60', don vi loai, (sym, thang) thieu > 1 %, so don vi
  bi loc vi muc gia <= 0 (L-S3-1); feature pass1 (sigma_1d, ER30 tu close gio) == pass2 (0 ngay lech). V4 (khong nhin tuong lai): 2
  symbol HOP LE dau tien theo ten trong shard (span >= 90 ngay); tc ngau nhien deu (seed co dinh) trong [max(dau + 45 ngay,
  2021-07-01 + 45 ngay), cuoi - 15 ngay]; lam rac moi du lieu sau tc (gia, active, quote volume, tier, funding, BTC: gia, sigma, ti le
  COND_B, close ngay) -> moi don vi ket thuc truoc tc phai GIONG HET (khop, thoat, loai, ket qua, net_h, co "toan thi truong")
  VA (R3-4, A1 F5) mang feature theo ngay sigma_1d, tick, s_hat, beta, tier, sigma_1d(BTC) GIONG HET cho moi ngay <= ngay cua tc;
  n_checked = 0 hoac n_diff > 0 hoac feature lech -> FAIL. V5 (doc lai tho + cai dat doc lap kref3): DUNG 12 vi tri = 6 cap (c,T) x 2 ben, mo hinh xen ke
  (cap chan: BUY-K_OPT3 / SELL-K_PESS; cap le: BUY-K_PESS / SELL-K_OPT3) => moi cap co CA 2 mo hinh, moi to hop (mo hinh, ben) co 3 vi
  tri (sua J1 audit S1); moi vi tri 1 don vi DA KHOP chon tat dinh (rng co dinh theo shard) tu symbol dau tien co ung vien; doc lai
  parquet tho + tinh lai sigma, tick, beta, delist, funding va mo phong bang kref3: khop f, thoat x, loai thoat, net (1e-9 bps), d,
  tick, beta phai trung. DU PHONG (MASTER P2, chot truoc): neu sau khi duyet HET symbol cua shard, vi tri (c, T, ben, mo hinh) khong
  co don vi DA KHOP nao -> thay bang mo hinh con lai cho cung (c, T, ben) (don vi du phong da chon tat dinh luc duyet), ghi vao
  validate.json V5.v5_fallback; neu ca 2 mo hinh deu khong co don vi khop cho (c, T, ben) -> ghi V5.uncovered. V5 shard PASS khi MOI
  don vi da so khop kref3 VA so (c, T, ben) uncovered <= 2 / 12; lech -> FAIL. R3-5 (A1 F6): MOI don vi da doi chieu, KE CA don vi du
  phong da chay kref3 nhung khong dung (vi tri chinh duoc lap o symbol sau), phai khop kref3 (ghi checks_fallback_unused); lech -> FAIL. Merge: moi (c, T, ben) (12) phai duoc phu boi >= 1 shard
  (V5.covered_ctside), neu khong -> abort. V6: tren TOAN file funding moi nam: median |rate| trong [1e-5, 1e-3] VA interval_h
  thuoc {1,2,4,8} (cot co san: moi dong; suy: >= 99 %); sai -> abort.

## 2. Universe + tier (point-in-time tai ngay D, chi du lieu <= cuoi D-1) - GIONG S1
- Hop le: ten USDT, khong "_", ASCII, khong stable (USDC/BUSD/TUSD/FDUSD/USDP/DAI/USDE), khong index (BTCDOM/DEFI/FOOTBALL/BLUEBIRD),
  first_utc <= D - 30 ngay, last_utc >= D, >= 1 phut hop le o D-1.
- Tier = hang tong quote_volume D-30..D-1 (hoa: ten): T1 = 1-10, T2 = 11-60, T3 >= 61. Coin delist o lai den ngay delist. 12 o GOP 3 tier.

## 3. Feature ex-ante (ngay D chi dung du lieu <= cuoi D-1)
- close ngay = close phut hop le cuoi cua ngay. sigma_1d(D) = RMS (khong tru TB) 30 log-return close ngay D-30..D-1, can >= 20.
- tick(D) = tick suy tu gia ngay D-1 (gia tri huu han gan nhat truoc D): buoc lon nhat dang {1,2,5}x10^k <= hieu nho nhat giua 2 gia
  khac nhau sao cho >= 99,9 % gia O/H/L/C la boi so; < 20 gia khac nhau -> tick ngay truoc.
- s_hat(D) = spread Abdi-Ranaldo tren nen 1m cua NGAY HOP LE GAN NHAT trong [D-7, D-1]; khong co -> 2 x san truot tier (T1 4 / T2 10 /
  T3 20 bps). Khong bao gio 0 do thieu du lieu.
- beta(D) (CHI cho net_h bao cao) = OLS co intercept log-return ngay sym theo BTCUSDT tren D-30..D-1, >= 20 cap, kep [0, 3], thieu -> 1.
- COND_B(t0) (CHI chan doan) = RV 24 gio BTCUSDT (24 log-return gio truoc t0, can >= 20) / sigma_1d(BTC, D) >= 1,5.
- Co "toan thi truong" (CHI chan doan, tinh tai phut khop f): r = ln(B[f] / B[f-60]), B[m] = close BTCUSDT phut hop le cuoi <= m;
  BUY: r <= -1 x sigma_1d(BTC, D)/sqrt(24) -> "market", nguoc lai "idio"; SELL doi dau (r >= +1 x ...). D = ngay cua t0.
- Hang so (COND_PREREG = {B: ratio 1,5; MKT: z 1,0, win 60}) nam trong code; KHONG bien moi truong nao doi duoc.

## 4. Don vi lenh sau MOT BEN (S3-2)
- Dat tai moi dau gio t0 (24 lan / coin-ngay) cho moi (c, T); m0 = close phut t0-1 (phai hop le, khong sau delist); d = c x sigma_1d(D),
  c in {1,0; 1,5; 2,5}; T in {240, 1440} phut.
- BUY: 1 lenh mua tai L = floor_tick(m0(1-d)) song W = 60 phut (phut t0..t0+59). SELL: 1 lenh ban tai L = ceil_tick(m0(1+d)) song 60
  phut. BUY va SELL DOC LAP (khong OCO).
- Khop tai phut f -> lenh thoat limit X: BUY X = ceil_tick(L(1 + 0,5 d)); SELL X = floor_tick(L(1 - 0,5 d)) (hoi NUA quang duong).
- Het han: close phut f+T (phut lo -> phut hop le dau tien sau do) theo quy tac het han cua tung mo hinh (muc 5).
- Bo qua (khong dat) neu: d x m0 < 4 tick; t0 + 60 + T + 61 vuot cuoi luoi du lieu; m0 khong hop le / sau delist; (L-S3-1) BUY co
  L <= 0 hoac X <= L, SELL co X <= 0 hoac X >= L (chi xay ra khi d >= 1 (BUY) / d >= 2 (SELL); dem va bao cao theo o).
- floor_tick(p) = floor(p/tick + 1e-7) x tick; ceil_tick(p) = ceil(p/tick - 1e-7) x tick; so sanh gia dung sai 0,01 tick.
- PnL (phan so notional luc vao, xuat bps): gross = side x (gia ra - L)/L; net = gross + funding - phi - truot.
  net_h (CHI bao cao) = net - side x beta(D) x (B[x] - B[f]) / B[f].
- Funding: moc s tinh khi f < s <= x; tien = -side x rate x close(phut hop le cuoi < s) / L.

## 5. Hai mo hinh khop (S3-3; R3-1: mo hinh lac quan DOI thanh K_OPT3, K_PESS giu nguyen quy tac S1)
| Quy tac | K_OPT3 (khoa code "OPT") | K_PESS |
|---|---|---|
| Khop lenh mua L (ban doi xung) | low <= L (cham) trong W | low <= L - 1 tick (xuyen) |
| Gia khop | L (ke ca phut mo da vuot muc) | L |
| Thoat CUNG phut khop | CHI KHI close phut khop da vuot X ve phia co loi (BUY close >= X; SELL close <= X): thoat tai X, maker | khong |
| Thoat limit (cac phut sau) | tu phut f+1: CHAM (BUY high >= X; SELL low <= X), tai X, maker | tu phut f+1: high >= X + 1 tick |
| Gia da vuot X luc dong phut khop | thoat cung phut (dong tren) | thoat TAKER tai dung X o phut f+1, phi taker 0,05 % VA truot s |
| Het han | close phut f+T, phi maker 0,02 %, khong truot | close phut f+T, taker 0,05 % + truot s |
| Phi maker (vao + thoat limit) | 0,02 % | 0,04 % (stress) |
| Delist giua don vi | close phut hop le cuoi, taker 0,05 % | idem + truot 50 bps |
Ly do R3-1 (A1 F1): K_OPT cua S1 cho "vong tron cung phut theo thu tu co loi O->L->H" (thoat neu high phut khop >= X). O phut gia roi
manh, open la high nen quy tac cu ghi lai ao +0,5 d ke ca khi gia KHONG hoi: tren null nhay vinh vien giua phut (A1), K_OPT cu ghi
+476..+800 bps / don vi trong khi K_PESS -210..-921 -> nhanh W-C / W-A vo nghia. K_OPT3 chi cho thoat cung phut khi close da vuot X (duong
gia tu muc khop toi close chac chan qua X). S1 dung K_OPT CU: o S_COND_A cua S1 (PASS duoi K_OPT, khong duoi K_PESS) co the chiu cung
hien vat nay - dang duoc kiem bang S2.
s = max(san tier, s_hat/2); san truot tier T1 2 / T2 5 / T3 10 bps. Phi thoat tinh tren notional ra (x gia ra / L).
Lo <= 60 phut: khong khop trong lo, lenh van song. Don vi co chuoi lo > 60 phut giao [t0-1, ket thuc] -> LOAI (dem V3, bao cao).
Lenh vao het song khi qua phut t0+59 hoac qua phut hop le cuoi truoc delist.
K_PESS la mo hinh CHINH cua luat. Bao cao them (KHONG vao luat): K_PESS voi truot thoat taker x5 (timeout + taker_beyond; L-S3-5).
Tinh chat: tap don vi khop duoi K_PESS la con cua K_OPT3 (cung t0, ben) va f_OPT <= f_PESS (kiem tren tong hop, muc 11).

## 6. 12 o gia thuyet (S3-4) x 2 mo hinh = 24 trial; ho grid 74 + 24 = 98
O = ben {BUY, SELL} x c {1,0; 1,5; 2,5} x T {240, 1440}, gop 3 tier, MOI don vi da khop cua ben/c/T (khong loc funding, tuoi, xu huong).
Ten: BUY_c1.0_T240, BUY_c1.0_T1440, BUY_c1.5_T240, BUY_c1.5_T1440, BUY_c2.5_T240, BUY_c2.5_T1440, SELL_... (cung thu tu; id 0..11).
Thong ke: M = net trung binh / don vi DA KHOP (khong loai) (bps), KHONG tru beta (net_h bao cao them).

## 7. Thong ke (S3-5; GIONG S1, stats.py S1 KHONG doi byte)
- M(o, nua, mo hinh) = tong net / so don vi da khop trong nua; don vi gan vao ngay cua t0. H0(o): M <= 4 bps.
- Circular block bootstrap 20 ngay lich (khoi cuoi cat cho du D), chon lai ca mat cat coin cung ngay, B = 2000; seed 2026112140
  (+1 nua B, +10 K_PESS).
- SE goc: SE = sqrt(sum_b (S_b - M N_b)^2) / sum N tren cac khoi KHONG chong lan 20 ngay tu ngay dau cua nua (S_b, N_b = tong net,
  so don vi cua khoi b). t = (M - 4)/SE. Bootstrap-t STUDENTIZED: moi replicate tinh M*, SE* cung cong thuc tren khoi cua chinh no;
  t* = (M* - M)/SE*; SE* = 0 / khong don vi -> t* = 0.
- Nua B: Romano-Wolf stepdown max-t tren t* cua cac o KHONG INSUFFICIENT, RIENG tung mo hinh, ALPHA_FWER = 0,04 (co dinh).
- Nua A: p 1 phia = ti le t*_r >= t (cung B, seed nua A), nguong 0,10.
- INSUFFICIENT (o x nua x mo hinh) neu BAT KY: (i) < 200 don vi da khop; (ii) so khoi 20 ngay khong chong lan co >= 1 don vi khop
  < ceil(so khoi / 3) (nua B 37 khoi -> can >= 13; nua A 46 -> >= 16); (iii) M khong huu han hoac SE goc = 0 / khong huu han.
  O INSUFFICIENT: p_RW = 1, khong the PASS, LIET KE, bi LOAI khoi max-t moi buoc RW va khoi can tren dong thoi; nua A p = NaN.
- Can tren dong thoi: c_up = phan vi 95 % (ALPHA_UPPER = 0,05) cua max_j(-t*_j) tren o khong INSUFFICIENT; can tren_j = M_j + c_up SE_j.
- C4: cap = s_hat/2 x so chan maker (1 + 1[thoat limit]); M_adj = M - TB cap.
- Hang so ALPHA_FWER 0,04, ALPHA_UPPER 0,05, MIN_UNITS 200, B 2000, khoi 20, san 4 bps, p nua A 0,10, W 60, ti le thoat 0,5,
  c {1; 1,5; 2,5}, T {240; 1440}, phi / truot nam trong code; runner assert; KHONG env / CLI doi duoc (moi bien GRIDV3_* / GRIDV2_*
  ngoai 4 bien van hanh GRIDV3_INPUT/OUT/SHARD/KEEP_SYM, va 5 bien cam S1 -> abort).
- Merge: bat buoc --expected-sha EXPECTED_SHA.txt (sha256 klite3.py, kref3.py, stats.py, stats3_extra.py, runner3_kaggle.py);
  abort neu: khong dung 5 shard 0..4/5 (thieu / trung chi so / trung thu muc), prereg_constants != True, validate all_pass != True,
  hang so khac, s3_const != prereg, cond != COND_PREREG, mkt_sym != BTCUSDT, sha code manifest != EXPECTED_SHA, manifest.inputs (sha
  lifecycle + funding) KHONG giong het 5 shard (H2 audit S1, nay trong code), co (c, T, ben) khong duoc shard nao phu o V5 (MASTER P2).
  R3-3 (A1 F3): merge TU KIEM sha256 cac file code trong thu muc cua CHINH no (klite3, kref3, stats, stats3_extra, runner3) ==
  --expected-sha; lech -> abort.
  result.json: khoa dau = TEST_ONLY; allow_test (chi qua
  import trong test) -> rule = "TEST_ONLY:<luat>".

## 8. PASS va luat (S3-6, S3-7)
PASS 1 o (tung mo hinh) = khong INSUFFICIENT o CA 2 nua VA
 (a) RW bac H0 o nua B (p_RW <= 0,04);
 (b) M_A > 4 VA p_A <= 0,10;
 (c) M_adj_B > 0 (C4);
 (d) M_B bo top-3 coin (theo tong net cua coin trong o-nua) > 4;
 (e) M bo 3 su kien (t0 trong [dau - 3 ngay, cuoi + 1 ngay) cua 2022-05-09..13, 2022-11-08..10, 2025-10-10..13) > 4 o CA hai nua;
 (e') M sau khi bo KHOI 20 ngay khong chong lan (phan hoach tu ngay dau cua nua, khoi cuoi cat - cung phan hoach SE goc) co TONG NET
      LON NHAT cua o do > 4 o CA hai nua; khong con don vi ngoai khoi do -> khong dat;
 (e'') (MASTER P1) M sau khi bo CUA SO TRUOT 20 ngay lien tiep (trong nua) co TONG NET LON NHAT cua o do (hoa: cua so som nhat) > 4
      o CA hai nua; khong con don vi -> khong dat. Giu ca (e') va (e''): (e'') bat cum su kien vat qua ranh gioi 2 khoi phan hoach.
PASS = (a), (b), (c), (d), (e), (e'), (e'') deu dat (result.json PASS_conditions ghi tung dieu kien: a_rw_B, b_half_A, c_Madj_B,
d_top3_B, e_events_AB, e2_topblock_AB, e3_topwindow_AB).
Luat (ap nguyen van, thu tu W-D > W-C > W-A > W-B; runner tinh "rule", MASTER doi chieu tay):
 W-D: co o PASS duoi K_PESS => buoc ke = prereg rieng gom (i) kiem khop muc giao dich tren mau lan khop (kieu S2 TL_THROUGH),
      (ii) mo phong danh muc co rang buoc von / margin lenh cho va chong lan voi lenh c3, (iii) (R3-9) kiem kha thi dat lenh that
      theo tung symbol (bo loc gia / buoc gia / khoi luong toi thieu cua san). KHONG doi cau hinh live.
 W-C: co o PASS duoi K_OPT3 nhung khong duoi K_PESS => chi kiem khop muc giao dich cho cac o do.
 W-A: CA 12 o duoi K_OPT3 KHONG INSUFFICIENT o nua B VA can tren dong thoi 95 % huu han VA < 4 bps o MOI o => DONG MANH.
 W-B: con lai => DONG THEO NGAN SACH (ghi MDE that + o INSUFFICIENT).
 W-C va W-A doc theo K_OPT3 (R3-9). W-A xet INSUFFICIENT o nua B duoi K_OPT3; vi o c2,5 nhieu kha nang INSUFFICIENT (D4), S3 thuc te co
 the KHONG BAO GIO dat W-A ("dong manh") ma ket thuc o W-B (A1 F11) - da biet truoc.
 O SELL PASS: ghi rieng "SELL (he thong hien long-only)" (result.json SELL_PASS_note); cung luat.

## 9. Bang chan doan S3-8 (CHI bao cao, khong PASS/FAIL)
Moi o x mo hinh x nua: theo tier (T1/T2/T3); theo nam; theo gio UTC cua t0; COND_B co / khong / na; cu roi "rieng coin" vs
"toan thi truong" (muc 3); P(khop) = khop/(dat - loai); P(thoat limit); thoi gian giu TB (phut); phan vi 1/5/50/95 % net don vi
(histogram 5 bps, tam bin); lo lon nhat 1 don vi; ti le thang M > 0 + trung vi M thang; M bo rieng 2025-10-10..13; chenh M K_OPT3 -
K_PESS; M_neth; M stress truot x5 (K_PESS); khoi top va cua so truot top (ngay bat dau); khoi top (ngay bat dau, ti trong net, so don vi);
gross, phi, truot, funding, cap TB; SD, skew; M theo nam; ti le loai lo; so don vi bi loc vi muc gia <= 0.
R3-7 (A1 R2, HAU NGHIEM - chi chan doan): M tach theo ti le quote_volume PHUT KHOP / trung vi quote_volume phut hop le cua ngay D-1
(nhom lt1 / 1_10 / gt10 / na) va theo "rau 1 phut co lap" (BUY: low phut khop < min(low f-1, low f+1) x (1 - 0,5 d); SELL: high phut khop >
max(high f-1, high f+1) x (1 + 0,5 d); iso / not / na). Co "toan thi truong" dung close phut khop = hau nghiem (A1 F8).

## 10. Cong suat + FWER (power3.py R3; mo phong TONG HOP qua DUNG runner3.process_symbol; KHONG du lieu that)
Panel: BTC + 7 alt (tier 1/1/2/2/3/3/3/3; sigma ngay 3/3,5/5/5/6,5/6,5/8/8 %; beta 0,8-1,3), 731 ngay (nua B) + 45 warm-up, 2 buoc/phut.
NULL (R3-8) = GBM martingale + nhay VINH VIEN doi xung dat o buoc con GIUA phut (open phut nhay = gia truoc nhay): nhay rieng coin
Poisson LAM_I / coin / ngay, |log| = U(1, 4) x sigma_1d; nhay toan thi truong Poisson LAM_M / ngay cung dau, |log| = U(1, 4) x sigma(BTC) x
beta. TAN SUAT NHAY LA THAM SO GIA DINH; 3 kich ban low (0,03; 0,005), base (0,10; 0,02), high (0,30; 0,05). Seed 2026112180.
FWER (base, 200 panel, RW studentized B 1000; M that moi o = gop panel, dich ve san 4 bps; out_power_r3/power3.json):
| mo hinh | FWER @ 4 % (luat) | tham khao 5 / 3 / 2 / 1 % | nguong max-t median |
|---|---|---|---|
| K_OPT3 | 0,045 +- 0,015 | 0,050 / 0,040 / 0,020 / 0,015 | 2,8 |
| K_PESS | 0,040 +- 0,014 | 0,050 / 0,040 / 0,020 / 0,010 | 2,8 |
Ti le panel o INSUFFICIENT (K_PESS): BUY_c1.0_T240 0,000; BUY_c1.0_T1440 0,000; BUY_c1.5_T240 0,180; BUY_c1.5_T1440 0,180; BUY_c2.5_T240 1,000; BUY_c2.5_T1440 1,000; SELL_c1.0_T240 0,000; SELL_c1.0_T1440 0,000; SELL_c1.5_T240 0,010; SELL_c1.5_T1440 0,010; SELL_c2.5_T240 1,000; SELL_c2.5_T1440 1,000.
So do DOC LAP cua A1 (bo sinh rieng, 9 coin, B 2000; A1 F2): null MONG (~200-340 don vi/o) K_OPT 0,055 +- 0,016 / K_PESS 0,060 +- 0,017;
null DAY (370-860 don vi/o) 0,020 / 0,020; gop 300 panel 0,043 / 0,047. => FWER vuot nhe danh nghia khi o mong, dat khi day.
MASTER: neu FWER do > 5 % o mo hinh nao -> DUNG, bao MASTER (khong tu doi alpha). Ket qua R3: K_OPT3 0,045, K_PESS 0,040.

M null (base, bps / don vi khop, gop 200 panel) va M null tren lake runner nhay giua phut (out_synth_r3, nua B / nua A):
| o | M null power K_OPT3 / K_PESS | lake null_mid M_B K_OPT3 / K_PESS (n) | lake M_A K_OPT3 / K_PESS |
|---|---|---|---|
| BUY_c1.0_T240 | -660,8 / -671,5 | -446,2 / -453,0 (509) | -439,7 / -446,4 |
| BUY_c1.0_T1440 | -675,9 / -685,4 | -515,6 / -521,9 (509) | -483,9 / -490,2 |
| BUY_c1.5_T240 | -501,5 / -512,4 | -218,2 / -225,0 (267) | -212,7 / -219,5 |
| BUY_c1.5_T1440 | -517,1 / -527,0 | -307,2 / -313,5 (267) | -269,7 / -276,0 |
| BUY_c2.5_T240 | -246,1 / -257,0 | -227,0 / -233,8 (5) | 36,4 / 29,9 |
| BUY_c2.5_T1440 | -264,7 / -274,7 | -345,8 / -352,6 (5) | -127,4 / -133,5 |
| SELL_c1.0_T240 | -771,6 / -784,0 | -540,8 / -548,0 (499) | -530,7 / -538,0 |
| SELL_c1.0_T1440 | -797,9 / -809,2 | -594,6 / -601,5 (498) | -624,7 / -631,6 |
| SELL_c1.5_T240 | -609,1 / -621,4 | -253,5 / -260,6 (382) | -250,9 / -258,0 |
| SELL_c1.5_T1440 | -635,9 / -647,3 | -313,5 / -320,2 (381) | -354,4 / -361,1 |
| SELL_c2.5_T240 | -353,7 / -366,0 | -227,8 / -234,8 (28) | -80,2 / -87,2 |
| SELL_c2.5_T1440 | -377,7 / -389,5 | -338,9 / -345,5 (28) | 13,4 / 6,9 |

MDE (bps VUOT san 4) quy ve universe that (B: 10 T1 / 50 T2 / 420 T3, 37 khoi; A: 10/50/130, 46 khoi) bang phan ra phuong sai
tong khoi 20 ngay (rieng coin + hiep phuong sai cheo coin); max-t = (nguong max-t median + 0,84) x SE.
| o (K_PESS) | khop/coin-ngay low / base / high | MDE_B max-t low / base / high | MDE_A max-t base | MDE_B K_OPT3 base | khop that B base (uoc) |
|---|---|---|---|---|---|
| BUY_c1.0_T240 | 0,017 / 0,051 / 0,119 | 153,9 / 96,4 / 72,1 | 71,1 | 95,5 | 17327 |
| BUY_c1.0_T1440 | 0,017 / 0,051 / 0,119 | 201,0 / 112,4 / 97,4 | 89,7 | 111,6 | 17327 |
| BUY_c1.5_T240 | 0,013 / 0,036 / 0,064 | 78,2 / 72,1 / 54,1 | 51,5 | 70,8 | 12134 |
| BUY_c1.5_T1440 | 0,013 / 0,036 / 0,064 | 89,6 / 98,7 / 100,6 | 79,9 | 97,8 | 12134 |
| BUY_c2.5_T240 | 0,006 / 0,011 / 0,004 | 99,3 / 39,9 / 40,0 | 38,0 | 38,5 | 3331 |
| BUY_c2.5_T1440 | 0,006 / 0,011 / 0,004 | 129,4 / 99,9 / suy bien | 90,7 | 99,1 | 3331 |
| SELL_c1.0_T240 | 0,018 / 0,053 / 0,131 | 167,3 / 128,8 / 92,3 | 90,0 | 127,3 | 18115 |
| SELL_c1.0_T1440 | 0,018 / 0,053 / 0,131 | 229,1 / 155,6 / 119,4 | 117,0 | 154,2 | 18115 |
| SELL_c1.5_T240 | 0,014 / 0,041 / 0,085 | 112,4 / 102,7 / 72,4 | 72,6 | 101,2 | 14033 |
| SELL_c1.5_T1440 | 0,014 / 0,041 / 0,085 | 172,9 / 136,1 / 101,5 | 104,4 | 134,8 | 14033 |
| SELL_c2.5_T240 | 0,008 / 0,019 / 0,019 | 87,1 / 59,9 / 39,0 | 47,3 | 58,6 | 7010 |
| SELL_c2.5_T1440 | 0,008 / 0,019 / 0,019 | 161,2 / 99,7 / suy bien | 86,9 | 98,6 | 7010 |
Doc bang: MDE lon (vai chuc - vai tram bps) vi don vi khop chu yeu den tu nhay va nhay toan thi truong lam don vi khop dong thoi;
o c2,5 / SELL co the INSUFFICIENT (D4). 'suy bien' = phuong sai uoc tu panel <= 0 (qua it khop o kich ban do; c2,5 T1440 high).
Gioi han: panel 8 coin; null nhay vinh vien; khong volatility clustering dai han; B 1000 (that 2000).

## 11. Kiem chung tong hop (truoc chay that) - test_klite3.py (ban R3)
Oracle, chay lai TOAN BO sau lan sua cuoi: 45/45 PASS, 202 s (seed 2026112150; out_synth_r3/test_results.json; code KHONG sua sau test).
Danh sach: acct_identity_fee_slip_gross, analytic_martingale_OPT_T240, analytic_martingale_PESS_T240, analytic_martingale_OPT_T1440, analytic_martingale_PESS_T1440, analytic_drift_wald_OPT_T240, analytic_drift_wald_PESS_T240, analytic_drift_wald_OPT_T1440, analytic_drift_wald_PESS_T1440, indepMC_bounce_h2_OPT, indepMC_bounce_h2_PESS, indepMC_ar1_m0.3_OPT, indepMC_ar1_m0.3_PESS, indepMC_drift_bounce1_OPT, indepMC_drift_bounce1_PESS, bracket_lat_tpm10_OPT3_exact, bracket_lat_tpm10_PESS, bracket_gbm_tpm10_OPT3_exact, bracket_gbm_tpm10_PESS, edges_S3_klite3_and_kref3, ref3_vs_klite3_all_units, pess_fill_subset_of_opt, no_lookahead_kernel_and_features, stats_rw12_fwer_null_gauss, stats_rw12_fwer_null_heavy, stats_rw12_planted_effect, stats_insufficient_i_ii_iii, eprime_drop_top_block, e2prime_sliding_window_straddle, merge_rules_WD_WC_WA_WB, merge_guards_shards_sha_inputs_TEST_ONLY, guard_forbidden_env_aborts, guard_dataset_allowlist, guard_V0a_V0b_pure, guard_V2_threshold_0p1pct, guard_V6_funding_units, guard_shat_ffill7_then_2x_floor, V5_select_eval_12_slots_4_combos, universe_mktflag_skip_diag_V4, tiers_point_in_time, runner3_checkpoint_keeps_V3_counters, runner3_diag_S3_8_tables, runner3_V0_V6_on_lakes, runner3_wick_lake_BUY_large_positive_both_models, runner3_null_mid_minute_lake_no_pass_WB.
Diem chinh (R3):
- K_OPT3: bracket_{lat,gbm}_tpm10_OPT3_exact = TRUNG TUNG DON VI (0,0 bps, cung tap khop) voi dap an muc giao dich DOC LAP
  synth3.trade_engine_path3(mode 'opt3'); indepMC_*_OPT (duong moi |z| <= 3, cung duong 0,0); analytic_martingale / drift_wald (luoi
  tick, tpm 1: K_OPT3 TB gross = 0 / Wald); edges E3 (close < X -> thoat phut f+1), E14 (open/high > X, close < X, gia khong hoi ->
  KHONG thoat cung phut, het han; close >= X -> thoat cung phut); ref3_vs_klite3_all_units 0 lech; pess_fill_subset_of_opt 0 vi pham.
- runner3_null_mid_minute_lake_no_pass_WB (R3-2): lake nhay vinh vien GIUA phut qua runner + merge -> 0 o PASS ca K_OPT3 va K_PESS,
  rule TEST_ONLY:W-B (M o muc 10). runner3_wick_lake_BUY_large_positive_both_models: lake rau -> W-D, 6 o BUY PASS ca 2 mo hinh.
- merge_guards: R3_self_sha_copy_ok (ban sao nguyen -> merge chay, B 2000), R3_self_sha_copy_modified (sua 1 dong runner3 -> abort
  'sha256 file code cua CHINH merge'); + moi guard R2.
- universe_mktflag_skip_diag_V4: R3_V4_leaky_sigma_fail (sigma_1d dung ca return ngay D -> V4 FAIL qua so sanh feature ngay); V4 sach
  feat_diff = 0; rac 3 ngay truoc tc -> FAIL; diag du 7 chieu (tier, year, hour, condB, mkt, qvratio, wick1m).
- V5_select_eval: R3_unused_fallback_mismatch_fail (don vi du phong khong dung lech kref3 -> FAIL), R3_unused_fallback_ok_pass.
- guard_dataset_allowlist: R3_nested_foreign_slug, R3_subdir_inside_slug, R3_slug_at_other_level -> abort.
- Giu tu R1/R2: ke toan, bien E1-E13, (e') / (e''), RW 12 o null / cay / INSUFFICIENT, luat W-D/W-C/W-A/W-B + SELL, env, V0b/V2/V6,
  tier PIT, checkpoint, bang chan doan.
Phat trien: code soan + chay thu trong sandbox rieng cua agent (khong du lieu that); ket qua chinh thuc tren Oracle.

## 12. Holdout, an toan
- Niem phong moi du lieu >= 2026-01-01 (chi owner mo). Khong doc du lieu that khi dev; chi chay that sau audit doc lap PASS va MASTER
  commit prereg + EXPECTED_SHA.txt.

## 13. Chay that + chi phi
- Toc do do (Oracle, lake tong hop full lich 2021-05..2025-12, tpm 4): ~8,5 s / symbol-lich-day-du (12 o x 2 mo hinh x 2 ben, gom
  feature + V5). Universe that ~630 symbol, TB ~840 ngay / symbol -> ~125 symbol / shard x ~4-5 s ~ 10 phut + pass1 (doc 15,7 GB,
  ~15-30 phut / shard, giong S1).
- 5 kernel Kaggle CPU song song (shard = crc32(symbol) mod 5), uoc 25-45 phut / kernel (S1 thuc te 1 297-2 115 s voi 32 o; S3 nhe
  hon o pha vao (W = 60 thay W = T toi 1 843) nhung bang chan doan nang hon), TONG ~2-4 kernel-gio. /kaggle/working tam ~1-2 GB / shard
  (xoa sau reduce); tai ve reduced/ (6 bang, ~5-20 MB / shard) + validate.json + manifest.json + run.log.
- Mount DUNG 7 dataset allowlist (muc 1). Env CHI GRIDV3_SHARD=i/5 (+ GRIDV3_INPUT / GRIDV3_OUT / GRIDV3_KEEP_SYM van hanh). Lenh kernel:
  python3 runner3_kaggle.py run. Dung neu bat ky V0-V6 FAIL.
- Truoc merge BAT BUOC: (H1) sha256sum s3/EXPECTED_SHA.txt == gia tri muc 15 (sau khi MASTER commit); (H1') (R3-9) NGAY truoc merge,
  trong thu muc code dung de merge: sha256sum -c EXPECTED_SHA.txt, DAN output vao RESULT (merge cung tu kiem, R3-3); (H2) da tu dong trong merge
  (manifest.inputs giong het 5 shard) + V0 PASS 5/5. Gop tren Oracle:
  python3 runner3_kaggle.py merge OUT --expected-sha s3/EXPECTED_SHA.txt d0 d1 d2 d3 d4 -> result.json, diag.json.
- QUY TAC (MASTER P8, chot truoc): BAT KY V-check FAIL / abort (run hoac merge) -> KHONG doc M / PnL nao. Chi sua PHAN KIEM CHUNG
  qua addendum prereg + audit doc lap, roi chay lai TOAN BO 5 shard (khong trial moi neu chua doc M; nhu ADD1 cua S1).

## 14. Diem lech / cai dat cu the so voi S3-1..S3-10
L-S3-1 (them, S3-2 khong noi) Loc muc gia <= 0: BUY co L <= 0 hoac X <= L, SELL co X <= 0 hoac X >= L -> KHONG dat (chi xay ra khi
   d = c x sigma_1d >= 1 cho BUY / >= 2 cho SELL, vd coin moi sigma_1d >= 40 % voi c = 2,5). Ly do: lenh gia <= 0 khong ton tai; dat
   no se lam phinh mau so P(khop). Dem theo o (validate V3.skip_px_by_cell, result.json skip_px_by_cell), CHI bao cao. Gay bat doi
   xung BUY/SELL o c lon (BUY bi loc nhieu hon) - ghi nhan.
L-S3-2 (sua J1 audit S1) V5 = 12 vi tri co dinh (6 cap (c,T) x 2 ben, mo hinh xen ke) thay cach can bang 2 bo dem cua S1 -> moi cap
   co ca 2 mo hinh, ca 4 to hop (mo hinh, ben) duoc kiem tren du lieu that. Hau qua: shard khong co don vi khop nao cho 1 vi tri (vd
   SELL c2,5 T240 K_OPT3) -> V5 FAIL -> dung (huong an toan, giong J4 S1). V5 khong con kiem ER30/UP/DOWN/F3 (S3 khong dung).
L-S3-3 (them, H2 audit S1) merge tu choi neu manifest.inputs (sha lifecycle + funding) khac nhau giua 5 shard; manifest them s3_const
   (W, ti le thoat, c, T, phi, truot, san...) va merge doi == prereg.
L-S3-4 Bien moi truong: ten van hanh doi sang GRIDV3_INPUT/OUT/SHARD/KEEP_SYM; MOI bien GRIDV3_* / GRIDV2_* khac (va 5 bien cam S1)
   -> abort (rong hon S1). CLI: "python3 runner3_kaggle.py run" (S1 chay khi khong co tham so) | "merge ...".
L-S3-5 Stress "truot het han x5" (S3-3): ap cho MOI lenh thoat taker do thi truong cua K_PESS = het han (timeout) VA taker_beyond
   (thoat tai X o f+1 khi dong phut khop da vuot X); KHONG ap cho delist (da 50 bps). Ly do: ca hai deu la lenh taker giua bien dong
   manh; S3-3 chi noi "het han". Chi bao cao (M_stress_slip_x5).
L-S3-6 Co "toan thi truong" (S3-8): r = ln(B[f]/B[f-60]) tinh den CHINH phut khop f (S3-8 viet "60 phut truoc phut khop" - chon gom
   phut f de bat cu sap dong thoi); nguong 1 x sigma_1d(BTC, D cua t0)/sqrt(24). Chi bao cao.
L-S3-7 (e') phan hoach khoi tu ngay dau cua nua (giong SE goc, khoi cuoi cat); khoi top = argmax tong net (hoa: khoi dau); khong con
   don vi -> NaN -> khong dat. Them chan doan "bo cua so TRUOT 20 ngay lon nhat" (khong vao luat). Kiem: 3 su kien da biet deu nam tron
   trong 1 khoi phan hoach (2022-05-09..13: ngay 312-316 nua A, khoi 300-319; 2022-11-08..10: 495-497, khoi 480-499; 2025-10-10..13:
   ngay 648-651 nua B, khoi 640-659).
L-S3-8 Seed bootstrap rieng S3: 2026112140 (+1 nua B, +10 K_PESS); seed V-check 2026112141 + chi so shard.
L-S3-9 Phan vi net don vi tu histogram bin 5 bps (S1: 1 bps) kep +-50 000 bps (net S3 lon hon S1 ~2 bac); sai so <= 2,5 bps.
   Lo lon nhat 1 don vi lay chinh xac (bang umin gop bang MIN).
L-S3-10 COND_PREREG cua S3 = {B: 1,5; MKT: z 1,0, win 60} (COND_A khong dung o S3); merge doi dung dict nay.
L-S3-11 Diem lam ro (khong lech): W = 60 tinh tu phut t0 (t0..t0+59); T tinh tu PHUT KHOP (thoat co the sau khi W het); bo qua neu
   t0 + 60 + T + 61 > so phut luoi (= S3-2); lenh vao bi huy o delist; M_adj, top-3, su kien, INSUFFICIENT, can tren, RW: nguyen S1.
L-S3-12 (MASTER P1, R2) them dieu kien PASS (e'') cua so truot 20 ngay; stats3_extra.drop_top_window (truoc la chan doan).
L-S3-13 (MASTER P2, R2) V5 du phong: mo hinh con lai cho vi tri thieu (v5_fallback), uncovered <= 2 / 12 moi shard; merge doi moi
   (c,T,ben) duoc >= 1 shard phu. Bo dieu kien "du 4 to hop mo hinh x ben" o V5 shard (du phong co the lam mat 1 to hop; ghi combos).
L-S3-14 (MASTER R3-1) mo hinh lac quan doi thanh K_OPT3 (thay S3-3 phan K_OPT); K_PESS giu nguyen.
L-S3-15 (MASTER R3-3..R3-7) merge tu kiem sha; V4 so feature ngay; V5 moi don vi da doi chieu; allowlist chat cap thu muc; 2 chieu
   chan doan hau nghiem (qvratio, wick1m).
MASTER chap nhan L-S3-1..L-S3-13 (2026-11-21). Thay doi R1 -> R2 CHI gom P1, P2 (code + test) va P8 (van ban); khong thay doi nao khac.

## 15. sha256 code (Oracle w3/gridv2/s3/, ban R3 sau lan sua cuoi)
  09bb18ebea6c0e2367a48f2a29508bfcfa6b8865ee64584d3572db73a7883946  klite3.py
  6b02dea6ef61bc2413e1f02b29da00d42833a68c3e8cde4e36060b53cc5a1b2b  kref3.py
  975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4  stats.py  (== s1/stats.py TUNG BYTE)
  a9f9857f3888048b413cda3023400579674a5f2e6dae729d2808e35765755edb  stats3_extra.py
  7cb71c9bd75d6086afc2e0f8a4a98cd39e489aad24f32c1fc8e96ff1a69cac33  runner3_kaggle.py
  0cb2de520214b87a6b0d22de0526083b3d2866b19bffe3acbcd8d1ca2a3d1147  synth3.py
  aa25a6ae078eafd9902d81565a7492a417af8818cc54a53fecb9fa131bda8b27  test_klite3.py
  20c0d60596f3007ce6e700083ba9b170c6f6ae366a2aeaa1aa308b88f6b1225b  power3.py
  2891b42d456cb5099ff784137ecb5064fc594cce654d9d644aec6d2db9fc399a  EXPECTED_SHA.txt  (5 dong: klite3, kref3, stats, stats3_extra, runner3)
  36276d183494e61ca4ab989179c6bbb66560c9299f0beda68b6fe416dd812ad6  out_synth_r3/test_results.json
  be64514344ffd850508c79515dabc7a6f8f3c0edd345d9ed613216a931e71d12  out_synth_r3/hand_units.txt
  8b4f1a50df7afefbdbf9be6cfa28197575e4f79ab4eca90363919365e70a92e0  out_synth_r3/runner_lake_summary.json
  6a62136d296fab53ebc3a4f19d598f1163f2d8fcf514a954820d42c2ac650261  out_power_r3/power3.json
  5eec5efe674f2e3c489f4d7f83ecdcc759f3131bbc7210b86f61676f21ddedfc  out_power_r3/power3_table.md
  (test 45/45 va power R3 chay voi DUNG ban code nay; khong sua code sau test. Ban R1: s3/_r1_backup/, R2: s3/_r2_backup/.)

## 16. Quyet dinh da chot (MASTER 2026-11-21)
D1 (P1) PASS = (a), (b), (c), (d), (e), (e'), (e''); (e'') = bo cua so truot 20 ngay lon nhat > 4 o ca 2 nua (muc 8).
D2 (P2) V5 giu 12 vi tri bat buoc + du phong chot truoc (muc 1); shard PASS khi moi don vi khop kref3 va uncovered <= 2; merge abort neu
   (c,T,ben) nao khong duoc shard nao phu.
D3 (P3) Stress truot x5 cho timeout + taker_beyond cua K_PESS, chi bao cao.
D4 (P4) Chap nhan o c 2,5 (va SELL) co the INSUFFICIENT; khong ha nguong (i)-(iii).
D5 (P5) Giu loc muc gia <= 0 (L-S3-1).
D6 (P6, R3-9) Bo loc gia: MASTER da tra tai lieu Binance (USDS-M futures common-definition, 2026-11-21): PERCENT_PRICE chi rang buoc
   BUY price <= markPrice x multiplierUp va SELL price >= markPrice x multiplierDown => lenh mua SAU duoi gia (va ban SAU tren gia) khong
   bi bo loc nay chan. Ket qua D6 CHI la ghi chu: KHONG doi o / nguong / luat; W-D them buoc (iii) kiem kha thi dat lenh that tung symbol.
D7 (P7) Giu 98 trial, ALPHA_FWER 0,04, ALPHA_UPPER 0,05, B 2000, p nua A 0,10. FWER do R3 (null giua phut, muc 10): K_OPT3 0,045 +- 0,015,
   K_PESS 0,040 +- 0,014; luat W-D dua tren K_PESS. (R1, K_OPT cu, null dau phut: 0,050 / 0,040.)
D8 (P8) Bat ky V FAIL / abort -> khong doc M; chi sua kiem chung qua addendum + audit; chay lai TOAN BO 5 shard (muc 13).
D9 Chap nhan diem lech L-S3-1..L-S3-13.
D10 (R3-1) Mo hinh lac quan = K_OPT3 (muc 5); tap khop K_PESS con cua K_OPT3.
D11 (R3-2) Null kiem chung = nhay vinh vien GIUA phut; bat buoc 0 o PASS ca 2 mo hinh, luat W-B (muc 11).
D12 (R3-3) merge tu kiem sha file code cua chinh no; (H1') sha256sum -c ngay truoc merge, dan vao RESULT.
D13 (R3-4, R3-5, R3-6) V4 so feature ngay; V5 moi don vi da doi chieu; allowlist chat cap thu muc.
D14 (R3-7) Chan doan qvratio, wick1m (chi bao cao, hau nghiem).
D15 (R3-8) FWER do lai tren null giua phut (muc 10) + ghi so doc lap A1; > 5 % -> dung, bao MASTER.
D16 (R3-9) W-C / W-A theo K_OPT3; S1 dung K_OPT cu (S_COND_A S1 co the chiu hien vat - kiem bang S2); W-D buoc (iii).

## 17. Gioi han da biet (S3-10 + dev) va rui ro lam ket qua vo nghia
Ghi bat buoc (S3-10):
- Su kien cuc doan co the co su co san (API, ADL, huy lenh hang loat, ngung giao dich) - KHONG mo hinh; kline 1m (gia giao dich cuoi)
  co the chua rau do lenh thanh ly / thanh khoan mong ma lenh that cua ta co the khong duoc khop (vi tri hang doi o muc L khong mo
  hinh duoc; K_PESS chi doi xuyen 1 tick).
- Lenh cho tren nhieu coin chiem margin; lenh khop dong loat trong cu sap toan thi truong -> rui ro tap trung / thanh ly - KHONG mo
  hinh (S3 chi kinh te don vi). Don vi BUY khop roi gia roi tiep (T toi 1440 phut) co the lo hang nghin bps (bao cao lo lon nhat).
- s_hat ex-ante (Abdi-Ranaldo ngay truoc) thap hon spread luc sap: truot taker K_PESS co the bi danh gia thap -> bao cao stress x5.
- MASTER da biet ket qua DCAGRID_A3 (loi o su kien 2025-10-10..13) truoc khi thiet ke S3 -> gia thuyet hau nghiem; (e), (e') giam
  nhung KHONG loai bo thien lech nay. Ket qua PASS phai doc kem bang khoi top va M bo 2025-10.
Gioi han dev / rui ro lam ket qua vo nghia:
- Tan suat cu roi >= c sigma_1d trong 1 gio la THAM SO GIA DINH trong power3 (khong lay tu du lieu that) -> MDE muc 10 chi la khoang
  (3 kich ban); so don vi khop that co the thap hon nhieu (o c 2,5: INSUFFICIENT).
- Cum su kien toan thi truong: don vi khop tap trung vao it ngay; khoi 20 ngay + RW studentized giu FWER tren panel tong hop (muc 10)
  nhung so khoi hieu dung nho -> SE kem chinh xac; (ii) INSUFFICIENT chan o qua thua.
- sigma_1d ex-ante bao gom ca nhay -> sau mot cu sap, d tu dong noi rong (lenh xa hon) trong ~30 ngay - la mot phan cua dinh nghia.
- net trung binh / don vi KHOP khong phai loi nhuan danh muc: P(khop) rat thap (~0,04-0,2 % / don vi dat tren panel tong hop), tan suat co hoi thap; W-D chi mo prereg
  tiep theo (von / margin / chong lan c3).
- Kline la gia cuoi (last), khong phai mark price: lenh limit khop theo last; thanh ly theo mark - khong mo hinh.
- Bo loc gia cua san: theo tai lieu Binance MASTER da tra (D6) PERCENT_PRICE khong chan lenh mua sau / ban sau; cac rang buoc khac
  (price band dong, gioi han so lenh, khoi luong toi thieu, thay doi quy tac theo thoi gian) chua mo hinh -> W-D buoc (iii).
- (A1 R2) rau gia GIA / in sai trong kline chinh la thu S3 do loi; chi bao cao qvratio / wick1m (muc 9) - khong loc.
- (A1 F2) FWER vuot nhe danh nghia khi o mong (it don vi, duoi day).
- Panel power 8 coin, gia lam tron luoi tuong doi 1e-8 (gan lien tuc), khong volatility clustering dai han.
- kref3 khong doc lap hoan toan voi klite3 (cung quy uoc +-1e-7 / 0,01 tick); doi chieu doc lap them: engine muc giao dich synth3
  (khop tung don vi o tpm 1, bracket o tpm 10).

## 18. Bang xu ly audit doc lap A1 (v12/A1_GRIDV2_S3.md, F1-F11)
| Ma | Muc | Xu ly (R3) | Vi tri |
|---|---|---|---|
| F1 | MAJOR | K_OPT3 thay K_OPT (R3-1) o klite3 + kref3; dap an doc lap trade_engine_path3 'opt3'; null giua phut 0 PASS, W-B (R3-2) | klite3.run_units; kref3.simulate_unit; synth3; muc 5, 11 |
| F2 | MINOR | FWER do lai tren null giua phut (R3-8) + ghi so A1; khong doi alpha | muc 10, D15 |
| F3 | MINOR | merge tu kiem sha file code cua chinh no (R3-3) + (H1') | runner3.merge; muc 7, 13 |
| F4 | MINOR | D6 ghi ket qua tai lieu san, CHI ghi chu; W-D (iii) | muc 8, 16, 17 |
| F5 | MINOR | V4 so mang feature ngay (R3-4); test sigma ro ri -> FAIL | runner3.v4_check, process_symbol aux |
| F6 | MINOR | V5 moi don vi da doi chieu ke ca du phong khong dung (R3-5) | runner3.v5_eval / run |
| F7 | NOTE | allowlist chat cap thu muc (R3-6) | runner3._slug_of / find_inputs |
| F8 | NOTE | ghi co 'toan thi truong' la hau nghiem | muc 9 |
| F9 | NOTE | giu (dung chu prereg) | - |
| F10 | NOTE | giu: V5 o c1,0 phu du 4 to hop; merge khong doi hop combos | L-S3-13 |
| F11 | NOTE | ghi ro S3 co the ket thuc W-B, khong bao gio W-A | muc 8 |
A1 R2 (gia in sai) -> R3-7 chan doan qvratio / wick1m. A1 R3 (price band) -> D6. A1 R4, R5 -> muc 17 (giu).

## 19. MASTER duyet + bo sung BAT BUOC sau audit vong 2 (2026-11-21) - muc nay THANG khi mau thuan voi cac muc tren
Ban nay = PREREG_GRIDV2_S3_FINAL2.md cua dev (sha256 50c4fbeba84501ec69ce6129d37a868b1b1ce4460315cd7e49fe64659a5f14b4) + muc 19 (chi van
ban; KHONG sua code; EXPECTED_SHA.txt 2891b42d456cb5099ff784137ecb5064fc594cce654d9d644aec6d2db9fc399a). Audit doc lap: vong 1
v12/A1_GRIDV2_S3.md (F1 MAJOR: K_OPT cu thoi phong -> doi sang K_OPT3), vong 2 v12/A1_GRIDV2_S3_R2.md (PASS-WITH-MINOR cho code + luat;
bo mo phong rieng 72 940 don vi 0 lech; 4 lake cay hieu ung dung ky vong). CHUA cham du lieu that.
(a) [G1, R3-8] FWER Romano-Wolf 12 o o danh nghia 4 % da do: dev (200 panel) K_OPT3 0,045 / K_PESS 0,040; A1 vong 2 null mong (200 panel)
    0,050 / 0,050, null day (100 panel) 0,060 +- 0,024 / 0,060 +- 0,024; gop moi lan do cua A1: K_PESS 30/600 = 0,050, K_OPT3 16/300 =
    0,053. Tieu chi dung R3-8 ("FWER do > 5 % -> dung, bao MASTER") DA KICH HOAT boi null day. QUYET DINH MASTER (truoc khi cham du lieu
    that): dieu kien PASS (a) CHINH THUC dung nguong p_RW <= 0,03 thay cho 0,04 (FWER do o 3 %: mong 0,035 / 0,035; day 0,030 / 0,050).
    Code KHONG doi (ALPHA_FWER = 0,04 trong runner3 / stats.py; stats.py van trung byte S1). Cach ap: tap o PASS CHINH THUC = cac o
    runner bao PASS (o 0,04) VA co p_RW (nua B, trong result.json) <= 0,03; tinh tay va ghi vao RESULT. Luat W-D / W-C ap tren tap PASS
    CHINH THUC; W-A dung can tren dong thoi (ALPHA_UPPER 0,05) nhu code; W-B la phan con lai. Truong "rule" cua runner (o 0,04) bao cao
    kem de doi chieu; neu khac luat chinh thuc thi luat CHINH THUC thang.
(b) [G2] Sua doc so FWER o muc 10: "A1 vong 1 (K_OPT CU, nhay dau phut): mong 0,055 / 0,060; day 0,020 / 0,020. A1 vong 2 (K_OPT3,
    nhay giua phut): mong 0,050 / 0,050; day 0,060 / 0,060."
(c) [G3] TRUOC khi tao kernel: liet ke TEN FILE cua 7 dataset allowlist (chi ten / duong dan, khong doc noi dung). Neu bat ky parquet can
    dung nam trong thu muc con cua slug (allowlist R3-6 se abort) -> DUNG, khong push kernel, bao MASTER; sua qua addendum + audit.
    Abort do layout input / loi ky thuat truoc khi doc M KHONG tinh la trial.
(d) [G6] D9: MASTER chap nhan L-S3-1..L-S3-15. Thay doi R2 -> R3 chi gom R3-1..R3-9.
(e) [D6] Tai lieu Binance USDS-M futures "Public Endpoints Info / common definition" (tra 2026-11-21): PERCENT_PRICE: BUY price <=
    markPrice x multiplierUp; SELL price >= markPrice x multiplierDown => lenh mua sau DUOI gia / ban sau TREN gia khong bi bo loc nay
    chan. Chi la ghi chu; khong doi o / nguong / luat; W-D (iii) van yeu cau thu dat lenh that theo tung symbol.
(f) Boi canh: S2 (commit ket qua 766b4424) ra L2-C - o COND_A cua S1 duoi K_OPT cu la hien vat thu tu trong nen 1 phut (cung mau: K_OPT
    +18,3 / +19,8 bps nhung TL_TOUCH that +5,9 / -1,2 va TL_THROUGH -2,4 / -9,1). S3 dung K_OPT3 de tranh hien vat do.
(g) So trial ho grid: 74 + 24 = 98. Du lieu >= 2026-01-01 NIEM PHONG. Ket qua S3 khong doi cau hinh live.
