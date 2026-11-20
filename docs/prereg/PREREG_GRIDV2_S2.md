# PREREG_GRIDV2_S2_FINAL - Giai doan 2 grid: ENGINE MUC GIAO DICH (aggTrades) cho DUY NHAT o S_COND_A_c0.2_k2
Ngay 2026-11-20. Tac gia: agent thiet ke+dev S2. Trang thai: FINAL cho audit doc lap (thay DRAFT 4c154992...; MASTER da chot
D1-D9 + R-11, muc 16). CHUA cham du lieu giao dich that
(chi HTTP HEAD 220 request lay kich thuoc file, ngay <= 2025-12-31). Ban TU CHUA. Can cu: docs/prereg/PREREG_GRIDV2_S1.md (commit
4ecc655d) + PREREG_GRIDV2_S1_ADD1.md (19608bbd); ket qua S1 v12/RESULT_GRIDV2_S1.md (246ae234; luat L-C); quyet dinh MASTER S2-1..S2-9.
Code + test tong hop: w3/gridv2/s2/ (sha256 muc 14). Bao cao dev: v12/GRIDV2_S2_DEV.md.
Quy uoc: bps = 0,01 %; UTC; nua A = 2021-07-01..2023-12-31 (XAC NHAN), nua B = 2024-01-01..2025-12-31 (CHINH); "S1" = prereg S1 + ADD1.
Moi dieu duoi day chot TRUOC khi tai bat ky aggTrades nao; khong doi sau do (doi = trial moi + exploratory).

## 0. Cau hoi va pham vi
S1 (luat L-C): DUY NHAT o S_COND_A_c0.2_k2 PASS duoi K_OPT (M nua B +19,92 bps, nua A +18,45) va KHONG duoi K_PESS (-15,79 / -10,33);
chenh 35,7 bps den tu mo hinh khop tren nen 1 phut. S2 hoi: khi khop bang CHUOI GIAO DICH THAT (thu tu theo transact_time, roi
agg_trade_id), loi the cua o nay con khong? - TL_THROUGH (chinh, bao thu: chi khop khi gia xuyen muc) va TL_TOUCH (lac quan co trinh
tu that). Pham vi: CHI o nay; moi dinh nghia don vi / su kien / universe / tier / tick / muc gia / thoat / het han / funding / loai
don vi giu NGUYEN S1 (S1 muc 2-5; COND_A z 2,5, vmult 3; c 0,2; k 2 => W = T = 115 phut; NEUTRAL BUY + SELL; gop 3 tier).
Khong them o, khong doi (c, k), khong doi nguong COND_A. So trial ho grid: 72 + 2 = 74 (THROUGH, TOUCH; THROUGH_LAT5S chi bao cao,
khong la trial).

## 1. Du lieu
- Danh sach su kien: kernel Kaggle events_kernel.py (muc 2) tren DUNG 7 dataset allowlist S1 (vz-kline1m-2021..2025, gridp-t1-funding,
  gridp-lifecycle), enable_internet = false.
- Giao dich: Binance Vision USDT-M futures aggTrades HANG NGAY
  https://data.binance.vision/data/futures/um/daily/aggTrades/<SYM>/<SYM>-aggTrades-YYYY-MM-DD.zip (+ .CHECKSUM sha256); cot
  agg_trade_id, price, quantity, first_trade_id, last_trade_id, transact_time, is_buyer_maker (co hoac khong dong tieu de; bool
  true/True). transact_time > 1e14 (micro giay) -> chia 1000 (ghi co).
- NIEM PHONG: moi du lieu >= 2026-01-01 (chi owner mo). url_of / sample / load_events / collapse_ms / parse_zip abort neu ngay hoac
  ts >= 2026-01-01. S1 da loai don vi co t0 + 2T + 61 phut vuot 2025-12-31 => khong cum nao can file 2026 (sample abort neu co).
- Tai tren Oracle (may khac khong toi Vision), theo lo, rut gon roi XOA file tho (muc 6).

## 2. Danh sach su kien (events_kernel.py, code S1 GHIM, khong sua / monkeypatch)
- Wrapper nhung base64 klite.py 196f4584, kref.py 6de0e412, stats.py 975f3a42, runner_kaggle.py 23a788cf (sha ADD1 muc 3) +
  events_kernel.py; kiem sha truoc khi chay. 5 shard, symbol chia nhu S1 (crc32(sym) mod 5).
- Moi shard goi DUNG chuoi ham cua runner_kaggle.run(): find_inputs (allowlist), pass1, V0a/V0b (registry that, bo qua 2021-01..03),
  V2, build_tiers, cross_section, load_funding + V6, market_context (BTCUSDT), roi process_symbol(..., collect_units=True) cho MOI
  symbol (y het S1; tinh ca 32 o x 2 mo hinh), trich don vi o 20 (ck (0,2; 2), memb[20] = COND_A) va xuat:
  events_s{i}.parquet (1 dong / don vi BUY hoac SELL): sym, day, date, t0_ms, t0_min, side, m0, d, sigma_1d = d / 0,2, tick, L, X,
  tier, s_hat (R3-5 S1), slip = max(san tier, s_hat/2), W, T, dl_end_ms (cuoi phut hop le cuoi neu delist, -1 neu khong), first_ms +
  ket qua S1 tung don vi K_OPT (o_*) / K_PESS (p_*): filled, excl, ok, f_ms, x_ms, kind, xpx, gross, fee, slipc, fund, net, n_maker.
  kline_win_s{i}.parquet: nen 1m LAKE (valid, O/H/L/C) moi phut trong [t0 - 61, t0 + W + T + 61] cua moi don vi (cho W2).
  funding_ev_s{i}.parquet: moc funding (sym, ts, rate) trong cua so don vi.
  validate_s{i}.json: V0a, V0b, V1, V2, V3 (feat pass1 = pass2), V6, E1a (tong theo ngay x mo hinh cua don vi trich == bang agg o 20
  cua CHINH process_symbol: place, fill, net, gross; sai so <= 1e-6); all_pass bat buoc. manifest_s{i}.json: sha code + input,
  prereg_constants (False neu dung tham so test noi bo -> run_s2 tu choi).
- E1b (precheck tren Oracle, TRUOC lay mau): tong theo (mo hinh, ngay) cua danh sach su kien == run2/d*/reduced/agg.parquet o 20 (lan
  chay S1 cong bo) - place, fill, net, gross; |lech| <= 1e-6 (+1e-6 tuong doi). Khac -> DUNG (du lieu / code khong tai lap S1).

## 3. Don vi (giu nguyen S1 muc 4)
Moi (sym, t0) COND_A (c 0,2; k 2): BUY = 1 lenh mua limit tai L = floor_tick(m0(1 - d)); SELL = 1 lenh ban tai L = ceil_tick(m0(1 + d));
m0 = close lake phut t0 - 1; d = 0,2 sigma_1d(D); song W = 115 phut; thoat limit X = ceil_tick(L(1 + d)) (BUY) / floor_tick(L(1 - d))
(SELL); het han T = 115 phut sau khop. L, X, tick, d, slip lay TU danh sach su kien (khong tinh lai) => cung lenh voi S1.

## 4. Lay mau (sample.py)
- Don vi lay mau = cum (sym, ngay UTC cua t0) co >= 1 don vi o 20. Mo phong MOI don vi cua cum duoc chon. File can: ngay D; them D+1
  neu max t0 + (W + T + 61) phut > 00:00 D+1. Khong can D-1 (DL-4).
- Tang = nam x tier (2021H2, 2022, 2023 -> nua A; 2024, 2025 -> nua B; tier = tier S1 cua (sym, D), duy nhat trong cum).
- Thu tu tat dinh: khoa = sha256("2026112150|sym|YYYY-MM-DD"); trong tang xep theo khoa; chon n_h = max(1, round(f_nua x N_h)) cum dau;
  phan con lai theo dung thu tu = DANH SACH DU PHONG (W6). Phan tang TI LE (pi_h = n_h / N_h ~ f_nua).
- f_nua (hang so: SE_TARGET 4,5 bps, F_GRID {0,05; 0,075; 0,10; 0,125; 0,15; 0,20; 0,25; 0,30; 0,35; 0,40; 0,50; 0,60; 0,80; 1,0}):
  f nho nhat trong luoi sao cho SE_pred(f) <= 4,5 cho CA K_OPT va K_PESS, voi SE_pred(f)^2 = SE_blk^2 + (1 - f)/f x sum_c u_c^2 / N^2;
  u_c = tong (net - M_nua) cac don vi ok cua cum c (ket qua S1 TUNG DON VI tu kernel - CHI phuong sai, khong ket qua TL nao);
  SE_blk = SE khoi 20 ngay S1 toan cum. (Xap xi lay mau Bernoulli cum; phan tang chi lam SE nho hon.)
- Cum audit (W4, W5): trong cac cum da chon cua moi nua, theo thu tu khoa, lay den khi >= 300 don vi VA >= 60 cum.
- Xuat sample.csv (ASCII, sap theo sym, ngay; cot sym, date, half, year, tier, stratum, key, rank, n_stratum, n_sel_stratum, selected,
  audit, files, n_units) + sample_manifest.json. sha256(sample.csv) = MOC W1: MASTER commit sha TRUOC khi tai bat ky aggTrades nao.
- Ngan sach (MASTER D2, quy tac dinh truoc): HEAD toan bo file cua mau theo luat SE (fetch_reduce --head-only) TRUOC khi tai; neu
  tong byte zip (file duy nhat; HEAD khong 200 tinh 0) > CAP = 150 GB: chon f LON NHAT trong F_GRID (f_nua' = min(f_nua, f)) sao cho
  tong <= 150 GB (lua chon long nhau: tap file cua f nho la tap con, HEAD da phu) - sample.py EVDIR SMPDIR head.json; ghi f moi va SE du
  doan vao sample_manifest.json (cap). Ca f nho nhat van vuot -> DUNG, bao MASTER. sha256 sample.csv commit SAU buoc nay.

## 5. Hai mo hinh khop muc giao dich (tl_engine.py; doi chieu doc lap tl_ref.py)
Giao dich cua symbol sap (transact_time, agg_trade_id); gom theo ms (gia dau / cuoi / min / max, min gia cua giao dich is_buyer_maker
= True (ben BAN chu dong), max gia cua giao dich is_buyer_maker = False (ben MUA chu dong)) - khong mat thong tin cho cac quy tac duoi.
So sanh gia dung sai tol = 0,01 tick (nhu TOL_TICK S1); "1 tick" = tick(D) ex-ante S1.
| Quy tac | TL_THROUGH (CHINH) | TL_TOUCH |
|---|---|---|
| Lenh vao song | giao dich co transact_time trong [t0, t0 + W phut) (t0 = 00 ms cua phut t0) | nhu THROUGH |
| BUY khop tai L | giao dich dau tien gia <= L - 1 tick | giao dich dau tien gia < L (moi ben) HOAC gia <= L voi is_buyer_maker = True |
| SELL khop tai L | gia >= L + 1 tick | gia > L (moi ben) HOAC gia >= L voi is_buyer_maker = False |
| Thoat limit X | co hieu luc tu tf + 250 ms den te = tf + T phut (gom ca te); khop khi giao dich XUYEN X >= 1 tick | tu tf + 250 ms; cham dung ben chu dong (nhu dong khop, doi ben) |
| Gia DA vuot X luc lenh thoat co hieu luc (R-11) | neu giao dich GAN NHAT truoc tf + 250 ms co gia >= X + 1 tick (BUY) / <= X - 1 tick (SELL): thoat NGAY tai tf + 250 ms, gia X, phi TAKER 0,05 %, KHONG truot (nhu taker_beyond K_PESS S1, bo truot vi X da xau hon thi truong) | khong ap (giu maker theo dong tren) |
| Het han (te) | TAKER tai gia giao dich cuoi <= te; phi taker 0,05 % + truot s = max(san tier, s_hat/2) | gia giao dich cuoi <= te; phi maker 0,02 %, khong truot |
| Delist (dl_end <= te) | gia giao dich cuoi < dl_end; taker 0,05 % + truot 50 bps | taker 0,05 %, khong truot |
| Phi maker | 0,02 % moi chan maker; net_stress voi 0,04 % (bao cao) | idem |
Khop vao bang chinh gia L; thoat limit / taker_beyond bang chinh X; n_maker = 1 voi taker_beyond. PnL (phan so notional luc vao, xuat bps): gross = side (xpx - L)/L;
fee = maker + phi_ra x xpx/L; truot = ti_le x xpx/L; funding: moc s voi tf < s <= tx: -side x rate x (gia giao dich cuoi < s)/L;
net = gross + funding - fee - truot. n_maker = 1 + 1[thoat limit] (nhu S1, cho C4). tx = thoi diem giao dich thoat / te / dl_end.
Lo du lieu (thay "phut lo > 60'" cua S1): khoang KHONG co giao dich dai > 60 phut (nghiem ngat, ms) cat [t0, ket thuc don vi]
(ket thuc = tx neu khop; min(t0 + W, dl_end) neu khong) -> LOAI (excl = 1, dem); bien du lieu da tai (00:00 ngay D, cuoi du lieu)
coi nhu giao dich ao; sau dl_end khong tinh lo.
Bao ham (kiem T1): THROUGH khop => TOUCH khop (tf_TOUCH <= tf_THROUGH); TOUCH khop => K_OPT (klite S1) tren nen dung lai tu CUNG giao
dich khop o phut <= ; K_PESS tren nen dung lai khop DUNG tap THROUGH, cung phut.
Mo hinh CHI BAO CAO (khong vao luat, khong la trial): THROUGH_LAT5S = THROUGH voi lenh vao co hieu luc tu t0 + 5 s va lenh thoat tu
tf + 5 s; quy tac R-11 ap voi moc tf + 5 s (do nhay tre ha tang; xem muc 12 G4). CACH DOC DINH TRUOC (MASTER D5): neu
TL_THROUGH PASS (L2-A) ma THROUGH_LAT5S KHONG PASS (cung dieu kien muc 8) -> nhan "L2-A-INFRA": ung vien chi kha thi khi co ha tang
dat lenh maker do tre thap (hien tre that ~7 s, gateway khong co LIMIT/GTX) - buoc ke phai gom xay ha tang truoc khi kiem ngoai mau.
Luat L2-A/B/C/INS KHONG doi (result_s2.json: rule + label).

## 6. Tai + rut gon (fetch_reduce.py)
- Doc sample.csv, kiem sha256 == sha da commit (W1) - sai -> abort. Thu tu xu ly: (sym, ngay). Lo 40 cum; tai song song 6 luong;
  moi file: .CHECKSUM + zip, kiem sha256; sai / loi mang -> thu lai toi 2 lan; 404 -> THIEU ngay.
- Cum co file thieu (404 / checksum sai sau 3 lan / loi doc) -> "missing"; thay bang cum DU PHONG dau tien chua dung cua CUNG tang
  (theo rank); du phong cung thieu -> tiep. Ghi state.json (checkpoint theo cum; khoi dong lai khong lam lai), files.jsonl (url,
  bytes, sha256, so dong, id_gaps, n_time_back, n_outside_day, us_converted, t_min, t_max).
- Moi cum: ghep giao dich D (+ D+1), gom ms, mo phong NGAY THROUGH + TOUCH + THROUGH_LAT5S cho moi don vi -> res/part_*.parquet;
  nen 1m dung lai (phut = floor(transact_time / 60000)) cho moi phut trong cua so [t0 - 61, t0 + W + T + 61] -> bars/part_*.parquet
  (zstd); cum audit: luu giao dich THO trong [min t0 - 61', max t0 + (W + T + 62)' + 60'] -> audit/<sym>_<ngay>.npz; roi XOA zip.
- Dia: abort neu dung luong trong < 15 GB (MIN_FREE_GB) hoac thu muc tam > 2 GB (MAX_TEMP_GB); checkpoint giu nguyen.

## 7. Thong ke (run_s2.py; stats.py S1 ghim)
- M(mo hinh, nua) = tong net / so don vi da khop KHONG loai (gan ngay cua t0), KHONG trong so (phan tang ti le). H0: M <= 4 bps.
- stats.cell_stats S1 voi J = 1 (ma tran ngay x 1): circular block bootstrap 20 ngay lich, bootstrap-t STUDENTIZED, B = 2000,
  seed 2026112160 (+1 nua B, +10 TOUCH, +100 ban co trong so); SE goc theo khoi khong chong lan; p 1 phia = ti le t* >= t.
- INSUFFICIENT (tung mo hinh x nua; dem TRUC TIEP, khong trong so): < 200 don vi khop, hoac < ceil(so khoi / 3) khoi 20 ngay co don vi
  (nua B 13/37, nua A 16/46), hoac M / SE khong huu han / SE = 0.
- Them: M_adj_C4 = M - TB(s_hat/2 x n_maker); M bo top-3 coin (theo tong net trong nua); M bo 3 su kien (t0 trong [dau - 3 ngay,
  cuoi + 1 ngay) cua 2022-05-09..13, 2022-11-08..10, 2025-10-10..13); M maker 0,04 %; ti le khop; P(thoat limit); gross, phi, truot,
  funding TB; M theo nam, theo tier; SD don vi; CI95; S1 K_OPT / K_PESS tren CUNG cum mau (doi chieu dai dien).
- Nhay (CHI BAO CAO): ban co trong so Hajek w_h = N_h / so cum da mo phong cua tang (weighted_rule_core); neu khac luat chinh ->
  ghi ro trong bao cao (khong doi luat).

## 8. PASS va luat quyet dinh
PASS(mo hinh) = khong INSUFFICIENT o CA 2 nua VA (a) nua B: p <= ALPHA_B = 0,04 (MASTER D1) va M_B > 4; (b) M_A > 4 VA p_A <= 0,10;
(c) M_adj_C4_B > 0 (dieu kien (c) S1 - DL-7); (d) M_B bo top-3 coin > 4; (e) M bo su kien > 4 o CA 2 nua.
Thu tu ap (ap nguyen van, runner tinh "rule"; MASTER doi chieu tay):
- L2-INS (DL-8): TL_THROUGH INSUFFICIENT o bat ky nua nao -> KHONG ket luan, bao MASTER (khong roi ve L2-C).
- L2-A: TL_THROUGH PASS -> "ung vien that": buoc ke = prereg kiem ngoai mau 2026 (owner mo niem phong) + kiem kha nang dat lenh maker;
  KHONG doi cau hinh live.
- L2-B: TL_THROUGH khong PASS, TL_TOUCH PASS -> loi the phu thuoc vi tri hang doi -> DONG (ha tang khong co uu tien hang doi); FINDINGS.
- L2-C: ca hai khong PASS -> xac nhan artifact mo hinh khop nen 1 phut -> DONG ho grid doc lap; FINDINGS.
- Nhan bo sung (khong phai luat): L2-A + THROUGH_LAT5S khong PASS -> "L2-A-INFRA" (muc 5).
So trial ho grid: 74.

## 9. Kiem chung bat buoc khi chay that (run_s2; MOI W TRUOC khi tinh M; bat ky FAIL -> result chi co khoi W, rule "W_FAIL", KHONG M)
- W0: events: du 5 shard 0..4/5, all_pass, prereg_constants True, input sha giong nhau, code sha == EXPECTED_SHA; fetch: moi file ngay
  < 2026-01-01 va t_max < 2026-01-01; su kien < 2026. (+ chan 2026 trong moi ham doc.)
- E1b (precheck): muc 2.
- W1: sha256(sample.csv) == sha da commit (run_s2 + fetch_reduce + state.json); moi cum da chon co trang thai; thay the cung tang,
  rank tang dan, khong lay cum da chon.
- W2: nen 1m dung lai tu aggTrades vs kline lake (kline_win) tren MOI phut lake hop le thuoc cua so cac cum da mo phong va nam trong
  du lieu da tai: ti le phut low VA high bang DUNG (dung sai 0) >= 99 %. Bao cao them open/close, phut lake hop le khong co giao dich,
  phut co giao dich ma lake khong hop le. (Can cu: EXEC_RESULT - lech high/low 153/115 881 phut = 0,13 %; lech open/close do gan bien
  phut ~3,5 % -> KHONG dung open/close lam tieu chi.)
- W3: klite S1 tren nen dung lai tu aggTrades (C[t0-1] := m0 lake de L, X giong het) vs ket qua S1 tung don vi (o_*, p_*): ti le dong
  y (filled, phut khop, kieu thoat, phut thoat cua don vi khong loai) >= 97 % moi mo hinh, VA |M_dung_lai - M_S1| <= 1 bps moi nua x
  mo hinh. Ly do nguong: lech high/low 0,13 % phut; quyet dinh 1 don vi phu thuoc vai phut cuc tri => ky vong < 1-2 % don vi lech;
  97 % bat duoc loi he thong (test: lech phut khop 10 % don vi da khop -> 94,6 % -> FAIL).
- W4: tren cum audit: thay giao dich sau moc tc ngau nhien (seed 2026112170) bang rac -> don vi co (ket thuc + 60') < tc giong het MOI
  cot; ket thuc < tc giong het tru cot excl (dinh nghia lo can toi 60' sau ket thuc - nhu lgc S1).
- W5: tren cum audit (>= 200 don vi): tl_ref (python thuan, vong lap giao dich THO) vs tl_engine: 0 lech; phat lai engine tren giao
  dich audit == ket qua da luu luc fetch: 0 lech.
- W6: ti le cum DA CHON thieu file <= 3 % moi nua (thay the van ap dung); vuot -> FAIL.

## 10. Cong suat, size, ngan sach
- Tu run2 (o 20): SE khoi 20 ngay nua B K_OPT 2,83 / K_PESS 2,75; SE gop theo NGAY 2,63 / 2,92; SE iid 0,70 / 1,00 (SD don vi ~248;
  phu thuoc trong ngay rat manh). Nua A: khoi 2,44 / 2,94; ngay 2,16 / 2,90; iid 0,74 / 1,19.
- SE du doan (max 2 mo hinh) theo f: bao thu (sum_c u_c^2 <= sum theo ngay) / lac quan (cum ~ iid):
| f | 0,05 | 0,075 | 0,10 | 0,15 | 0,20 | 0,25 | 0,30 | 0,35 | 0,40 | 0,50 | 0,60 | 1,0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nua B | 13,0/5,2 | 10,6/4,5 | 9,2/4,1 | 7,5/3,6 | 6,5/3,4 | 5,8/3,3 | 5,2/3,1 | 4,8/3,1 | 4,5/3,0 | 4,0/2,9 | 3,6/2,9 | 2,8 |
| nua A | 13,0/6,0 | 10,6/5,1 | 9,2/4,6 | 7,5/4,1 | 6,5/3,8 | 5,8/3,6 | 5,3/3,5 | 4,9/3,4 | 4,6/3,3 | 4,1/3,2 | 3,8/3,1 | 2,9 |
  => luat SE_TARGET 4,5 cho f trong [0,10; 0,50] (chot CHINH XAC tu danh sach su kien, muc 4). Ke hoach ngan sach theo f = 0,5 (xau nhat).
- Cong suat (1 phia, xap xi chuan; so lieu tinh voi alpha 0,05; voi ALPHA_B 0,04 cong suat giam <= 0,01, MDE 80 % SE 4,5 = 15,7): SE 4,5: P(PASS (a) | M_B that = +19,9) = 0,97; P((b) | M_A that = +18,45) = 0,97; MDE 80 % nua B
  = 4 + 2,49 SE = 15,2 bps; +19,9 va -15,8 cach nhau 7,9 SE; P(bac H0 | M = -15,8) < 1e-9. SE 5: 0,94 / 0,95, MDE 16,4.
  M that cua TL_THROUGH o giua (vd +8): P(PASS (a)) ~ 0,22 - S2 khong co cong suat cho loi the nho (gioi han G6).
- Size (T9, stats.py S1, null CUM: hieu ung ngay + cum + nhieu t3, so cum / ngay thay doi; M that = 4): nua B size 0,0625 tai alpha
  danh nghia 0,05 (800 mo phong, gioi han MC 0,065 -> PASS luat test; tai 0,04 = ALPHA_B: 0,0425; 0,03: 0,031); nua A 0,085 tai 0,10.
  Null them hieu ung CHE DO 30 ngay (phu thuoc dai hon khoi 20 ngay; chi bao cao): nua B 0,085 tai 0,05 / 0,075 tai 0,04 / 0,059 tai
  0,03 / 0,044 tai 0,02; nua A 0,135 tai 0,10 (dev_out/t9_detail.json; gioi han G7)
  => ALPHA_B danh nghia = 0,04 (MASTER D1). GIOI HAN R-3: p nua B sat nguong (vd 0,02-0,04) KHONG dang tin - size do duoc toi
  7,5 % tai 0,04 khi co phu thuoc che do 30 ngay; doc ket qua phai ghi ro (khong doi luat).
- HEAD 220 request (dev_out/head_sizes.json): ngay PROXY (sym ~ so don vi S1 theo nua, ngay ~ so don vi theo ngay; KHONG phai ngay su
  kien) nua A TB 1,51 MB (trung vi 0,82, p90 4,0), nua B TB 0,95 MB (0,34; 1,65); 3/220 = 1,4 % 404. Ngay su kien COND_A (khoi luong
  >= 3 x TB trong gio) uoc 1,5-3 x => A 2,3-4,5 MB, B 1,4-2,9 MB / file; ~1,2 file / cum.
- So cum (chua biet truoc kernel): don vi dat nua B 171 032, nua A 97 324 (= 85 516 / 48 662 su kien x 2 ben); gia dinh 3-8 don vi / cum
  => B 21-57 nghin cum, A 12-32 nghin. Tai f = 0,5: uoc 30-120 GB zip (trung tam ~60-80 GB); f = 0,2: 12-48 GB; f = 0,1: 6-24 GB.

## 11. Kiem chung dev (test_tl.py; ket qua dev_out/test_results.json; chay lai TOAN BO sau lan sua cuoi R-11)
Ket qua: 11/11 PASS (Oracle; dev_out/test_results.json).
| Test | KQ | s | Noi dung / so do |
|---|---|---|---|
| T1 bao nhau | PASS | 3.2 | 2540 don vi: THROUGH khop 834, TOUCH 847, K_OPT (klite S1 tren nen dung lai) 848, K_PESS 834; vi pham 0 |
| T2 dap an giai tich (buoc +-1 tick, 9000 duong) | PASS | 14.1 | THROUGH E[Z] = -0.199 +- 0.137 tick (z -1.45); TOUCH -0.149 +- 0.117 (z -1.27); bien the SAI z -8.8 (bi bac) |
| T3 bien (18 tinh huong, 22 kiem) | PASS | 0.0 | xuyen dung 1 tick, cham khong xuyen, sai ben, cung ms / 249 / 250 ms, thoat dung te / te+1, phi het han, nua dem, lo 60' / 60'+1 ms, delist, funding (tf, tf+1, tx, tx+1), bien cua so vao, SELL, truoc t0, TOUCH gia vuot, LAT5S, R-11 taker_beyond BUY / SELL / dung bang X (khong); ref dong y moi ca |
| T4 engine vs tl_ref | PASS | 81.6 | 5012 don vi x 3 mo hinh, 0 lech, max |dfloat| 0; khop THROUGH 1752 / TOUCH 1777; co thoat limit / het han / delist; loai lo {'THROUGH': 58, 'TOUCH': 57, 'THROUGH_LAT5S': 58} |
| T5 khong nhin tuong lai | PASS | 3.5 | ket thuc+60' < tc: 2370 don vi, 0 khac; ket thuc < tc: 2491, 0 khac (tru excl) |
| T6 lay mau (+ tran CAP) | PASS | 0.7 | same_sha, proportional, selected_are_first_ranks, rank_by_key, next_day_when_late, no_next_day_if_delisted, audit_A, audit_B, se_pred_decreasing, auto_f_smallest, block_2026, cap_not_applied_under, cap_largest_f_within, sha_guard |
| T7 fetch_reduce zip gia | PASS | 16.4 | missing_two, substituted_same_stratum, subs_done_ok, checksum_retried, w6_fail_when_17pct, tmp_empty, resume_no_rework, block_2026, disk_guard, sample_sha_guard, no_header_parsed, title_bool_parsed, run_s2_W_FAIL_no_M |
| T8 luat | PASS | 0.6 | L2-A / L2-B / L2-C / L2-INS dung; dieu kien (e) su kien chan L2-A; nhan L2-A-INFRA; ALPHA_B = 0,04 |
| T9 size 1 o | PASS | 55.8 | null cum: B 0.0625 @0,05 (gioi han MC 0.0651), A 0.0850 @0,10; null che do 30 ngay (chi bao cao): B 0.0850 @0,05, 0.0750 @0,04, 0.0587 @0,03 |
| T10 e2e (sample->fetch->run_s2) | PASS | 22.3 | W0-W6 PASS; W2 1.000 (19064 phut); W3 dong y K_OPT 1.000 K_PESS 1.000; W5 240 don vi 0 lech; kiem luc: W2/W3/W5 bat loi cai (W3 lech 10 % -> 0.946) |
| T11 events_kernel tren lake gia S1 | PASS | 166.5 | 5 shard all_pass, E1a; E1b vs runner S1 ghim cung lake: max lech 2.3e-13; 4108 don vi / 1468 cum; build 5 kernel |

## 12. Gioi han (biet truoc, he qua dinh san)
G1 CUNG su kien voi S1 (khong phai mau doc lap; o nay la tot nhat trong 32 duoi K_OPT - loi nguyen nguoi thang) => S2 kiem CO CHE KHOP;
   ke ca L2-A van can mau ngoai 2026 (owner mo niem phong).
G2 Khong co du lieu so lenh / vi tri hang doi: TL_THROUGH la CAN DUOI bao thu (gia dinh lenh nho, khong tac dong gia); TL_TOUCH lac quan
   (dung dau hang doi tai muc). Su that nam giua.
G3 Kich thuoc lenh gia dinh nho (khong tac dong gia, khong khop mot phan).
G4 Tre 250 ms la gia dinh; ha tang live do duoc tre lenh MARKET trung vi ~7 s va gateway live KHONG co LIMIT/GTX (GRIDV2_INFRA muc 1)
   -> THROUGH_LAT5S chi bao cao; "kha nang dat lenh maker" la buoc rieng (L2-A).
G5 (R-11, da xu ly) THROUGH: gia da vuot X luc lenh thoat co hieu luc -> taker tai X (khong huong gia tot hon) - bao thu; TOUCH giu
   maker tai X o giao dich cham ke tiep (lac quan, dung vai tro can tren).
G6 Mau theo cum (sym, ngay) voi f < 1 -> SE > S1; cong suat chi du phan biet +19,9 vs san 4 / -15,8; loi the nho (< ~15 bps) khong du
   cong suat.
G7 (R-3) Bootstrap khoi 20 ngay hut size khi co phu thuoc > 20 ngay (T9 che do 30 ngay: 8,5 % tai 0,05; 7,5 % tai 0,04 = ALPHA_B):
   p sat nguong khong dang tin.
G8 Engine chay luc tai (dia khong du giu giao dich tho): sua engine sau khi tai = tai lai (chi phi lap lai).
G9 is_buyer_maker cua aggTrades la ben chu dong cua giao dich gop; TL_TOUCH dua vao no.

## 13. Ke hoach chay + chi phi
THU TU COMMIT (bat buoc): (1) MASTER commit prereg + s2/EXPECTED_SHA.txt TRUOC khi chay kernel su kien; (2) sau kernel + sample.py (+ ap
tran CAP neu can): MASTER commit sha256 cua sample.csv (file chua ca danh sach du phong: selected = 0, rank) TRUOC khi tai bat ky
aggTrades nao; (3) chay fetch_reduce / engine; (4) W0-W6 ALL PASS truoc khi doc M.
1. MASTER commit prereg + w3/gridv2/s2/EXPECTED_SHA.txt (muc 14).
2. python3 events_kernel.py build OUT ~/claude_master/vz_e1_wt/research/gridv2_s1 -> 5 thu muc kernel_e0..4 (mount DUNG 7 dataset,
   khong internet); push + cho (agent chay). Uoc ~25-45 phut / kernel (S1 run2: 22-35 phut / shard + trich + s_hat + xuat), 5 song song
   ~1 gio, tong 2,5-4 kernel-gio. Tai ve events_s*, kline_win_s* (uoc 0,2-0,5 GB), funding_ev_s*, validate_s*, manifest_s*, run_s*.log.
3. Oracle: python3 run_s2.py --stage precheck ... (W0_events + E1b) -> PASS bat buoc.
4. python3 sample.py EVDIR SMPDIR -> sample.csv + manifest (f, SE du doan, so cum, so file).
5. python3 fetch_reduce.py --head-only ... -> head.json (tong GB, 404); > 150 GB -> python3 sample.py EVDIR SMPDIR head.json (f lon
   nhat trong tran, muc 4) roi moi commit sha sample.csv.
6. nohup flock ~/claude_master/locks/oracle_heavy.lock nice python3 fetch_reduce.py ... (khoi dong lai an toan). Uoc (f = 0,5, 60-120 GB):
   tai 6 luong ~15-40 MB/s -> 0,5-2 gio; doc CSV (~4-5 x zip) don luong ~100 MB/s -> 1-3 gio; tong 2-5 gio. Dia: tam <= 2 GB;
   output res + bars + audit uoc 0,5-1 GB; giu trong >= 15 GB.
7. python3 run_s2.py --stage full ... -> result_s2.json (W0-W6 truoc; luat). B = 2000: vai phut.
8. Bao cao RESULT_GRIDV2_S2 + doi chieu tay luat.

## 14. sha256 code (Oracle w3/gridv2/s2/; test chay voi DUNG ban nay, sau lan sua cuoi)
  b49241d4388b08de92ee7fd494bc291f1e1f183972c066e1d51edc54aba733bf  tl_engine.py
  71594505338cd8dd5af4cfbb36aa3d5752cb615019a6e341401af81d4bbfb8ee  tl_ref.py
  8296ec2a1db7b6343f157426db5368d7a393c9005223b7611b2172281699d980  sample.py
  05a70450c2076b22056caadbc477278810939af26f050f5ce0a7677cffd0efa2  fetch_reduce.py
  9a78fa91819dd559b35568ef876d92629a1da9cc1a39a168ede79af7e5b3f5f4  run_s2.py
  e9dce8d9a88c0e88e406550a94d356cff079dc3b334c97984ab9871b7ecaf621  events_kernel.py
  a1f698a4b416c7ef9da6cb921efc0291e91d8cabeff559f3ed35628b19b3ae53  synth_trades.py
  650043fe9788dd328107f14dced59c5026a99087297890c93f8dc1146b0cc9e7  test_tl.py
  e1438b1ba82822784c11842fbe488e40ef5ac48a320962e5b91ea6cd050db177  head_s2.py
  196f458489c5a808754d4afc39c2ad03f9149d57936de7f84c810074b8652680  klite.py
  6de0e412633658f1d548d28c7a650ff9b0e43b1a5f6cc3e64dbe93c51c928ff2  kref.py
  975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4  stats.py
  23a788cf97f69c73aec663572d0f133136e6e872eb64c8251b9641ba0dd14ccf  runner_kaggle.py
  3684023bba2b8df8e66d267caaa1c8e907bf1ca2da6d95990da7081778a99479  dev_out/test_results.json
  b8d3a462393cb25f8ba272ac6d6eb5f4cc7528e29d3ba796e3e165dc76e4439e  dev_out/head_sizes.json
  a283c5d83f1c74dccceb1a30b518aaddaca91722e22818358dd11479e0162a58  dev_out/t9_detail.json
  273c59188208aaa12e29d703edb341e749edf8244ec8fa24b89b97a9ce52e342  dev_out/power_table.json
  b15df375f48134135f0ece0d41351b4ddb2e56f8cada3a57f04d00763f020819  dev_out/power_table.py
  5aa541f4e7fd8a002bb1572db2023526a88c6919e05cb3520ab2b934fe0f4f9c  dev_out/finalize.py
  b852e84978eb60e21ea302fe385b0badb199085ec06d69065a358cc9510c88f6  EXPECTED_SHA.txt
  (4 dong S1 = ban ghim ADD1 muc 3; test 11/11 va bang muc 10-11 chay voi DUNG ban code nay; khong sua code sau test.)

## 15. Bang diem lech so voi S2-1..S2-9 (va cach cai dat cu the)
DL-1 (S2-5) TL_TOUCH khop ca khi gia VUOT muc o ben bat ky (BUY: gia < L), khong chi gia <= L voi is_buyer_maker = True. Ly do: (i) mot
     giao dich duoi gia mua dang nghi chung to gia ban da thap hon lenh -> lenh nghi da bi khop; (ii) bao dam THROUGH khop => TOUCH khop
     (bao nhau S2-5 / test (1)). Doi xung cho SELL va lenh thoat.
DL-2 (S2-5) Delist: theo S1 (K_OPT: taker, khong truot; K_PESS: taker + 50 bps) -> TOUCH / THROUGH; gia = giao dich cuoi truoc dl_end.
DL-3 (S2-5) Gia mark funding = giao dich cuoi truoc moc (S1: close phut hop le cuoi truoc moc).
DL-4 (S2-5) "Lo" muc giao dich: khoang khong giao dich > 60' (nghiem ngat) cat [t0, ket thuc]; bien du lieu da tai = giao dich ao;
     khong tai D-1 (S1 xet tu phut t0 - 1, phut nay hop le theo dinh nghia su kien S1). Phu thuoc toi 60' sau ket thuc (nhu S1).
DL-5 (S2-5) Bien thoi gian cu the: vao [t0, t0 + W) ; thoat limit [tf + 250 ms, te] (gom te); het han gia giao dich cuoi <= te, tx = te.
DL-6 (S2-5) So sanh gia dung sai 0,01 tick; "1 tick" = tick S1 ex-ante (suy tu gia ngay D-1) - neu tick that nho hon, THROUGH bao thu hon.
DL-7 (S2-6) Them dieu kien (c) M_adj_C4_B > 0 cua S1 vao PASS (S2-6 khong liet ke) - bao thu. MASTER xac nhan (D3).
DL-8 (S2-7) Them L2-INS: THROUGH INSUFFICIENT -> khong ket luan (khong roi ve L2-C "dong") - MASTER xac nhan (D4).
DL-9 (S2-6) Chinh = KHONG trong so (phan tang ti le, pi_h lech chi do lam tron / max(1, .)); ban Hajek bao cao nhay.
DL-10 (S2-4) Tang = nam x tier (nua long trong nam).
DL-11 (S2-4) N chot bang LUAT tu danh sach su kien (phuong sai S1 tung don vi), khong phai so co dinh; muc tieu SE 4,5 (bien du 5).
     Ngan sach: HEAD toan mau truoc tai, > CAP -> dung (D2). Bang du bao muc 10.
DL-12 (S2-2) Engine chay luc tai (khong luu giao dich tho tru cum audit); luu nen cua so + ket qua don vi. Ly do dia (<= 3 GB tam).
DL-13 (S2-8 W2) Kline lake do kernel su kien xuat (kline_win) cho cua so moi don vi; so low + high (khong open/close - ly do muc 9).
DL-14 (S2-8 W3) Nguong 97 % dong y + |dM| <= 1 bps; C[t0-1] := m0 lake de tach anh huong bien phut.
DL-15 (moi) THROUGH_LAT5S chi bao cao (G4).
DL-16 (S2-3) Kernel su kien chay process_symbol day du (32 o) thay vi chi o 20 - khong sua code S1; them E1a (trong kernel) + E1b.
DL-17 (S2-8 W6) Nguong thieu 3 % / nua; thay the = cum du phong ke tiep cung tang (danh sach xao san bang khoa sha256).
DL-18 (S2-6) ALPHA_B = 0,04 (MASTER D1; T9 size 4,25 % null cum, 7,5 % voi che do 30 ngay).
DL-19 (MASTER R-11) THROUGH (va THROUGH_LAT5S): gia da vuot X >= 1 tick o giao dich gan nhat TRUOC luc lenh thoat co hieu luc -> taker
     tai X, phi 0,05 %, khong truot (EX_TAKER_BEYOND = 4). "Gan nhat truoc" = giao dich cuoi (theo transact_time, agg_trade_id) co
     transact_time < tf + 250 ms (giao dich dung tai tf + 250 ms xet theo quy tac thoat limit thuong). Ap chi khi tf + 250 ms < moc delist.
DL-20 (MASTER D2) tran 150 GB: f lon nhat trong luoi (chung cho 2 nua: min(f_nua, f)) - sample.apply_cap.
DL-21 (MASTER D5) nhan "L2-A-INFRA" (result_s2.json "label"), luat khong doi.
MASTER CHAP NHAN DL-1..DL-17 (2026-11-20).

## 16. Quyet dinh da chot (MASTER 2026-11-20)
D1 ALPHA_B = 0,04 (code run_s2.ALPHA_B + prereg). Gioi han R-3 / G7 ghi ro.
D2 SE_TARGET 4,5 bps; tran tai 150 GB zip; vuot -> f LON NHAT trong luoi con trong tran, ghi SE du doan (muc 4, sample.apply_cap).
D3 Giu dieu kien (c) C4 trong PASS. D4 Giu L2-INS.
D5 THROUGH_LAT5S chi bao cao; cach doc dinh truoc "L2-A-INFRA" (muc 5, 8); luat L2-A/B/C/INS khong doi.
D6 W3: dong y >= 97 % va |dM| <= 1 bps; W6: thieu <= 3 % moi nua.
D7 Cho phep HEAD toan bo file mau + tai 30-150 GB tu Vision tren Oracle (chi ngay <= 2025-12-31).
D8 Cum audit >= 300 don vi va >= 60 cum moi nua (W5 >= 200 don vi).
D9 Ban chinh KHONG trong so (phan tang ti le); Hajek chi bao cao.
R-11 (sua code) THROUGH / THROUGH_LAT5S: taker_beyond tai X, phi taker, khong truot; TOUCH giu maker (DL-19).
Thu tu commit: muc 13. Chap nhan DL-1..DL-17.

## 17. Holdout, an toan
- Khong cham du lieu >= 2026-01-01 (moi ham doc abort). Khong may 242. Khong doi cau hinh live trong moi nhanh L2.
- Chi chay that sau audit doc lap PASS va MASTER commit prereg + EXPECTED_SHA + (sau buoc 4) sha sample.csv.

## 18. MASTER duyet + bo sung BAT BUOC sau audit doc lap (2026-11-21) - muc nay THANG khi mau thuan voi cac muc tren
Ban nay = PREREG_GRIDV2_S2_FINAL.md cua dev (sha256 e458e9475fa2d6e246051228140172d3ef25a59892ba4416e31d41acdd9e4d20) + muc 18 (chi van
ban; khong sua code; EXPECTED_SHA.txt b852e84978eb60e21ea302fe385b0badb199085ec06d69065a358cc9510c88f6). Audit doc lap
v12/A1_GRIDV2_S2.md: PASS-WITH-MINOR (F1-F13); bo mo phong rieng cua audit 5 516 don vi x 3 mo hinh: 0 lech; cay hieu ung 5/5 dung.
Trang thai: MASTER duyet va commit. CHUA cham du lieu giao dich that.
(a) [F1, F7] sha256sum s2/EXPECTED_SHA.txt == b852e849... va `sha256sum -c EXPECTED_SHA.txt` PASS: ngay truoc khi khoi dong fetch_reduce,
    sau MOI lan khoi dong lai, va ngay truoc run_s2; ghi log tung lan. Lech bat ky lan nao -> W0 FAIL.
(b) [F2] run_s2 --stage full BAT BUOC co --sample-sha = sha256 cua sample.csv da duoc MASTER commit; thieu -> ket qua khong hop le.
(c) [F3] fetch_reduce chay that KHONG dung --base-url. W0: moi url trong files.jsonl bat dau bang "https://data.binance.vision/".
(d) [F4] W0: moi dong files.jsonl co status ok phai co n_outside_day == 0; liet ke moi cum done-ok co 100 % don vi bi loai (excl);
    bat ky vi pham nao -> W0 FAIL.
(e) [F5] W1 (kiem tay bang script chi in dem / True-False): tap cum done-ok == (cum duoc chon khong thieu) hop (cum du phong trong subs);
    moi cum thay the = cum du phong CHUA DUNG DAU TIEN cung tang theo rank; moi cum missing co dong files.jsonl khong-ok tuong ung.
    Sai -> W1 FAIL.
(f) [F11] Bat ky W FAIL: KHONG tinh / KHONG doc M. Moi sua doi chi tren phan khong dung M, qua addendum prereg + audit truoc khi chay lai.
(g) [F8] Lam ro: so cum moi tang n_h = floor(f x N_h + 0,5); seed bootstrap THROUGH_LAT5S = seed TL_THROUGH; THROUGH_LAT5S INSUFFICIENT
    duoc coi la "khong PASS" khi gan nhan L2-A-INFRA.
(h) [F6, van hanh] fetch_reduce chay voi --batch <= 10; chi khoi dong / tiep tuc khi dia trong >= 15,5 GB; dung khi < 15 GB.
(i) [F13] Bao cao (khong chan): tong id_gaps va n_time_back tren files.jsonl; neu > 0,1 % so file co id_gaps > 0 thi neu o muc nghi van.
(j) MASTER chap nhan DL-1..DL-21. Gioi han da biet: F9, F10, F12 (K_PESS tren nen dung lai khop dung tap THROUGH => tien nghiem
    L2-B / L2-C cao), G7 (p sat nguong khong dang tin). So trial ho grid: 72 + 2 = 74.
