# PREREG_GRID_PREMISE_1120 (CHOT 2026-11-20 02:00 +07, MASTER; TRUOC khi tinh bat ky outcome nao) - dot 1: 4 phep thu TIEN DE grid, 0-sim
Nguon: nhap cua agent thiet ke (~/claude_master/v12/GRID_PROGRAM_1120.md). Owner 2026-11-20: "xem grid trade" = NGHIEN CUU grid. Khong sua sau khi thay so.
Quyet dinh cua MASTER cho 5 cau hoi mo (truoc khi chay):
  (Q1) Chap nhan chia E = 2021-07-01..2023-12-31 / C = 2024-01-01..2025-12-31 nhu duoi (kline 2021 it symbol: ghi nhan, U30 van tinh duoc).
  (Q2) T3 DUOC dung printDone c3/A3 (in-sample doi voi ENTRY - ghi ro trong ket qua; ket luan chi noi ve luat thoat). Tham so proxy trailing phai lay tu
       config.properties / result.json overrides cua luot r1-a3 (khong lay tu tri nho hay tai lieu khac); cong V6 (tai lap exit >= 90 %) khong dat => T3 = "KHONG CHAY DUOC",
       tinh la FAIL va van chiem 1 vi tri trong Holm.
  (Q3) Tieu chi dung muc phi BASE nhu muc 0; STRESS chi bao cao, khong la tieu chi.
  (Q4) Duoc upload printDone (8 seed) va lifecycle.parquet len Kaggle duoi dang dataset PRIVATE (khong co bi mat; kiem danh sach file truoc khi push).
  (Q5) Chap nhan luat "0/4 PASS => de xuat dong ho grid doc lap"; viec ghi FINDINGS do MASTER lam sau khi bao owner.
  (Q6) Thuc thi: moi T mot agent + mot kernel Kaggle rieng; tong so kernel dang chay cua tai khoan <= 5 (dung chung voi DCAGRID_A3). Holm tren 4 p_C do MASTER tinh sau khi
       ca 4 ket qua C da ghi file; agent T_k chi bao p_E, p_C, san hieu ung cua rieng minh. C chi chay 1 lan, sau khi E da ghi file ket qua (sha256) tren Oracle.


## 0. Luat chung (ap cho T1..T4)
- PASS tien de KHONG co nghia la co chien luoc - chi mo khoa buoc 2 (sim day du, prereg rieng, kha nang khop do bang aggTrades).
- Ky: KHAM PHA E = 2021-07-01 00:00 -> 2023-12-31 23:59 UTC; XAC NHAN C = 2024-01-01 -> 2025-12-31 23:59 UTC.
  T3 (can printDone c3) E = 2022-01-01 -> 2023-12-31. C chay DUNG 1 LAN, sau khi ket qua E da ghi file + commit.
  Moi nguong suy tu du lieu (tercile, cutoff) tinh TREN E, ghi file, roi DONG BANG cho C.
- 2026: CAM. Moi loader assert max(ts) < 1767225600000 (2026-01-01 UTC); khong mount dataset vz-*-2026; khong doc
  funding_snapshot Oracle tru khi thieu symbol (khi do loc ts < 2026-01-01 TRUOC khi giai ma, assert).
- Du lieu: Kaggle chuyendinh/vz-kline1m-{2021..2025} (doc theo row group = symbol), chuyendinh/vz-funding (2021-2025),
  universe PIT: ~/claude_master/symlife_wk/lifecycle.parquet (upload ban sao private, ghi sha256). Giu coin delist: vi the dong
  tai gia dong cua phut giao dich cuoi + phat truot stress; khong loai coin vi sau nay delist.
- Universe U30(t): top-30 USDT perp theo quote_volume 30 ngay TRUOC t (tinh tu kline), loai stablecoin (USDC, BUSD, TUSD, FDUSD,
  USDP, DAI), loai BTCDOM/DEFI index, loai symbol ten khong ASCII, can >= 30 ngay lich su. Tai tao dau moi thang UTC.
- Chi phi: BASE taker 0,0491 %/chieu (= 0,0982 %/vong, muc do that trong repo: VZ ledger SIM_RATE_FEE=0.000982) + truot 0,02 %/chieu
  (BTC/ETH) hoac 0,05 %/chieu (con lai). STRESS = 0,10 %/chieu phi + 0,15 %/chieu truot (= Java sim RATE_FEE 0.002 + SLIPPAGE 0.003).
  Maker 0,02 %/chieu CHI dung khi khop qua quy tac xuyen (duoi). Funding THAT tu vz-funding cho moi vi the giu qua moc settle.
- Khop: KHONG "cham la khop". Lenh kich hoat khi close 1m vuot muc -> khop TAKER tai open phut ke tiep + truot. Rieng T3 cho phep
  limit-sell maker neu high 1m >= muc*(1+0,10 %) (xuyen >= 1 tick va hon) VA volume phut do >= 3x khoi luong lenh gia dinh
  (notional 1.000 USDT); khong dat -> coi nhu chua khop.
- Multiple testing: 4 gia thuyet chinh (T1..T4), MOI phep thu dung 1 thong ke chinh. Cong E: p_E < 0,05 (1 phia) VA dung dau VA dat
  san hieu ung. Cong C: Holm-Bonferroni tren 4 p_C, alpha ho = 0,05 (p nho nhat so voi 0,0125, ...). Phep thu truot cong E thi
  van chay C (de bao cao) nhung tinh la FAIL va van chiem 1 vi tri trong Holm. Ghi +4 vao trial ledger ho grid (da co >= 3 trial
  grid doc lap truoc do: GRID_RESEARCH, SCREEN_WIDE G, GRID_T1).
- p-value thuc nghiem = (1 + #{surrogate >= thuc}) / (1 + N). N surrogate >= 500 (toi thieu 200 theo luat du an). Seed 20261120.
- CI: bootstrap theo cum (ngay UTC hoac su kien), 2000 rep.
- KHONG lam: khong 2026; khong doi tham so/luoi/nguong sau khi thay so; khong them bien the; khong doi dinh nghia su kien; neu phat
  hien bug sau khi thay so -> ADDENDUM rieng ghi truoc/sau, chay lai TOAN BO, bao ca 2.
- Kiem chung luot chay (moi T, ghi validate.json, FAIL bat ky -> khong bao cao so):
  V0 so dong kline doc duoc khop registry theo nam (2021 60.001.411; 2022 75.973.640; 2023 104.401.093; 2024 155.015.111;
     2025 256.801.320) cho phan da doc; V1 min/max ts trong [ky], max < 2026-01-01; V2 0 NaN trong cot dung; 0 gia <= 0;
  V3 phu phut: bao % phut thieu theo symbol-thang, liet ke lo > 60 phut (luu y gotcha 2022-02-26..28 o 48 symbol);
  V4 khong look-ahead: thay du lieu sau t bang rac -> moi quyet dinh tai t giu nguyen (5 thoi diem ngau nhien);
  V5 tinh tay 1 don vi (1 su kien / 1 thang / 1 entry) bang script doc lap, khop < 1e-9;
  V6 tai lap so cu (rieng tung T, ghi ben duoi).
- Chay o dau: Kaggle CPU kernel private (4 core, 31 GB; Oracle khong con kline 1m, dia 21 GB). Moi T 1 kernel; 4 kernel song song.
  Oracle chi de chuan bi printDone (T3) va luu ket qua (< 20 MB).

## T1 (H1) - Dao dong sau sap: grid co dinh sau onset BD1a hon chinh no tren duong xao khoi?
- Su kien: onset BD1a = gio UTC t0 dau tien co ret24h_BTC = close(t0)/close(t0-24h)-1 <= -0,05 (nen 1h dung tu 1m, close gio),
  cac onset cach nhau >= 72h (onset trong 72h sau onset truoc bi bo). Dinh nghia lay nguyen tu PREREG_BIGDOWN_STRUCT (BD1a).
- Don vi: (su kien e, coin i in U30(t0)), cua so W = [t0+1h, t0+73h) phut 1m. Coin delist trong W: dong tai phut cuoi.
- Luoi CO DINH duy nhat (khong toi uu): P0 = close 1m tai t0+1h. Muc mua k=1..5 tai P0*(1-0,03k) (-3,-6,-9,-12,-15 %), moi muc
  notional bang nhau 1/5. Moi lot ban tai gia mua*(1,03). Lot ban xong co the mua lai o cung muc (luoi lap). Kich hoat bang close 1m,
  khop taker tai open phut ke tiep + truot BASE. Cuoi W: lot ton MTM tai close cuoi. Funding that cho lot ton qua moc settle.
- Thong ke chinh S1 = TB tren cac (e,i) cua [PnL_grid_thuc - TB_surrogate PnL_grid] (% notional luoi), surrogate = hoan vi KHOI
  60 phut log-return trong W (khong lap lai, cung coin, cung cua so) -> giu nguyen tong loi nhuan + phan phoi bien dong, pha cau truc
  thu tu > 60 phut. 500 hoan vi/don vi; p tu phan phoi TB-tren-don-vi cua 500 bo surrogate.
- H0: S1 <= 0. H1: S1 > 0.
- San hieu ung (ca E va C): S1 >= 0,30 % notional/su kien-coin VA TB PnL_grid NET BASE thuc > 0 voi CI95 (bootstrap theo SU KIEN)
  can duoi > -0,25 %.
- Thong ke phu (mo ta, khong vao Holm): VR(60m) tren 1m trong W so voi cua so doi chung khop bien dong (cung coin, ngay khong su kien,
  cung decile realized vol 72h tinh tren E) - "event-time shuffle" 500 lan; PnL STRESS; tach theo do sau (ret24h -5..-8 / -8..-15 / < -15).
- V6: so onset BD1a gio tren DEV phai khop con so trong ket qua BIGDOWN_STRUCT (agent tra file ket qua tuong ung truoc khi chay);
  khong khop -> dung, bao MASTER.
- Rui ro biet truoc: n su kien nho (uoc vai chuc moi ky) -> cong suat thap; tuong quan cheo coin cao -> CI theo su kien la bat buoc.
- Chi phi: doc ~30 coin x so su kien x 73h 1m; 500 hoan vi x so don vi grid numpy/numba. ~30-60 phut 1 kernel.

## T2 (H5) - Phan bu tai can bang ro alt (theo thoi gian)
- Ro: moi thang UTC m, A20(m) = top-20 cua U30(dau thang) tru BTCUSDT, ETHUSDT. Coin delist trong thang: dong tai phut cuoi, tien ve
  USDT 0 lai cho het thang (ca A va B).
- A = trong so deu, tai can bang ve deu moi 00:00 UTC. B = trong so deu dau thang, giu nguyen (buy&hold) den cuoi thang.
- Thong ke chinh S2 = TB thang cua [log(1+R_A,gross) - log(1+R_B,gross)] - TB_surrogate cua cung dai luong. Surrogate = hoan vi THU
  TU NGAY trong thang, CUNG MOT hoan vi cho moi coin (giu tuong quan cung ngay, tong loi nhuan tung coin -> B bat bien). 1000 hoan vi.
- H0: S2 <= 0. H1: S2 > 0 (gia tuong doi giua alt dao chieu o thang >= 1 ngay).
- San hieu ung: S2 >= 0,30 %/thang VA TB log(1+R_A,net BASE) - log(1+R_B,net BASE) > 0 (net gom phi+truot theo turnover thuc
  va funding that ca hai ro).
- Phu (mo ta): STRESS; ket qua theo nam; bo 3 coin dong gop lon nhat (do tap trung).
- V6: tai lap 1 so tu TREND_T1/khac khong co -> thay bang kiem toan hoc: voi du lieu tong hop 2 tai san doc lap GBM sigma
  bang nhau, hoan vi phai cho S2 ~ 0 (|S2| < 2 SE tren 200 duong); voi 2 tai san dao dong nguoc pha tong hop, S2 > 0 ro.
- Chi phi: nen ngay tu 1m cho ~60-100 symbol/nam. ~30 phut.

## T3 (H7) - Ladder chot tung phan thay exit c3 tren CUNG entry
- Tap: leg0 cua cum c3/A3 trong printDone 8 seed (/home/ubuntu/kaggle_sim/out/r1-a3-*/storage/printDone.csv), cum = (sym,end) theo
  conc_grid.py; doi gio GMT+7 naive -> UTC (t_utc = t_naive - 7h). LOAI cum co leg DCA (thuoc PREREG_DCAGRID_A3). Gop trung lap
  (sym, start) giua seed -> 1 entry (trong so = so seed co entry do; bao ca 2 cach).
- Doi chung san co = exit thuc trong printDone (gia ra, thoi diem T_exit). Ladder CO DINH: ban 1/3 tai +3 %, 1/3 tai +6 %, 1/3 tai
  +10 % so voi gia vao (limit maker, khop theo quy tac xuyen + 3x volume o muc 0); phan con lai dong tai T_exit voi gia exit thuc.
  Khong stop moi, khong doi entry. Funding that tinh theo thoi gian giu tung phan.
- Thong ke chinh S3 = TB cap doi [PnL_ladder - PnL_thuc] (% notional leg0, net BASE).
- Doi chung surrogate: cung entry, duong gia [entry, T_exit) hoan vi khoi 60 phut (giu diem cuoi), ap CA ladder va 1 proxy exit
  trailing (arm +1,032 %, gap = cong thuc exit machine trong INFRA_FACTS) -> phan phoi [ladder - proxy] tren surrogate, 500 lan.
  Tren duong THUC cung tinh [ladder - proxy] (proxy kiem duoc tren cung 1m) -> so voi p95 surrogate.
- H0: S3 <= 0. PASS can: (a) p_S3 (bootstrap theo ngay entry, 1 phia) < nguong, (b) [ladder-proxy] thuc > p95 surrogate,
  (c) S3 >= 0,20 % notional/entry ca E va C.
- V6: dem cum/seed ~3488 va DCA ~48,4 cum/seed khop GRID_RESEARCH_REVIEW_1119; proxy trailing tren duong thuc phai tai lap exit
  printDone o >= 90 % entry (|dgia| < 0,1 %) - khong dat -> dung, bao MASTER (proxy sai thi (b) vo nghia).
- Rui ro: entry c3 tune tren toan 2022-25 -> C sach voi luat thoat moi, KHONG sach voi entry; ket qua chi noi ve exit.
  X2 da cho truc exit NULL -> prior thap.
- Chi phi: printDone (vai MB) upload private dataset; 1m quanh ~3-4k entry x so ngay giu. ~30-45 phut.

## T4 (H2') - Nhan regime EX-ANTE co du bao mean-reversion trong 24h toi?
- Don vi: (coin i in U30, ngay UTC d). Dac trung tai 00:00 d tu 7 ngay truoc: z_VR = z robust (Lo-MacKinlay heteroskedastic, code
  research/grid_t1/g_vr.py) cua VR(q=12) tren log-return 5m. Nhan RANGE(i,d) = z_VR <= -1,0 VA realized vol 7d khong o tercile tren
  (cutoff tercile tinh tren E, gop moi coin, dong bang cho C).
- Bien muc tieu: logVR_fwd = log VR(q=12) tren 5m trong [d, d+24h).
- Thong ke chinh S4 = TB(logVR_fwd | RANGE) - TB(logVR_fwd | khong RANGE), clustered theo ngay.
- Surrogate: dich vong chuoi nhan RANGE cua tung coin mot do lech ngau nhien >= 30 ngay (giu ty le + tu tuong quan nhan), 1000 lan.
- H0: S4 >= 0. H1: S4 < 0.
- San hieu ung: S4 <= -0,05 VA TB VR_fwd trong RANGE <= 0,92, ca E va C.
- Phu: VR_fwd vs nhan theo nam; luoi doi xung co dinh buoc 1 % 24h tren ngay RANGE (taker, BASE) chi MO TA.
- V6: chay g_vr.py tren universe + ky E cua GRID_T1 -> median VR(1h) phai = 0,913 (+-0,005) va % sig 56,9 % (+-1pp).
- Chi phi: 5m tu 1m cho U30, ~1.600 ngay. ~30-40 phut.

## Tieu chi PASS/FAIL toan dot (CHOT)
- T_k PASS neu: cong E dat (p_E<0,05 + dau + san hieu ung) VA cong C dat (Holm tren 4 p_C, alpha 0,05 + san hieu ung) VA validate.json
  sach. Moi truong hop khac = FAIL. Khong co "gan dat".
- 0 PASS -> de xuat DONG ho grid doc lap (ghi FINDINGS), chi giu thi nghiem DCAGRID_A3 dang chay.
- >= 1 PASS -> chi mo khoa buoc 2 cho ho do: sim day du, prereg rieng, khop do bang aggTrades Vision, control RW, stress phi.

## Bao cao (moi T): RESULT_GRIDP_T{k}.md: prereg sha, code sha, validate.json, bang E/C (S, p, CI, san), STRESS, phu, rui ro.
