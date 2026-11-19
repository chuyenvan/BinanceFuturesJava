# PREREG_DCAGRID_A3 (CHOT 2026-11-19 22:15 +07, MASTER; TRUOC khi do) - DCA grid -50/-75/-90 trong A3 co dong gop that khong, va co khop duoc khong

Trang thai: CHOT boi MASTER 2026-11-19 22:15 +07 tu nhap cua agent ra soat (~/claude_master/v12/GRID_RESEARCH_REVIEW_1119.md). Khong sua sau khi thay so.
Bo sung cua MASTER (truoc khi do): (1) Ha tang Kaggle dung bo sinh kernel ~/claude_master/w3/ho5/ho5_k3.py (overlay snapshot mapper + funding_data, jar sim cc0f9d11 khong doi) vi cong Aerospike 3222 da dong;
    cong G-P0 duoc coi la DAT bang luot ho5-a3-rep3-s123 (md5 printDone a11ce5f9 trung byte voi r1-a3-s123) NEU arm N dung DUNG bo sinh do, chi them override DCA_GRID_LEVELS.
    (2) Bang chung muc 1 la so DA NHIN truoc prereg (khai ro): cau hoi Q2 vi the la kiem dinh xac nhan mot nghi ngo da co, khong phai phat hien moi.
    (3) Quyet dinh muc 6 KHONG tu dong ap vao live: micro-live giu nguyen cau hinh; moi thay doi DCA tren live can prereg rieng + owner duyet.

## 0. Cau hoi
Q1. Leg DCA grid (rows DCA_LEVEL1, leg>0) cua A3 co KHOP DUOC tren thi truong that o gia sim khong?
Q2. Bo DCA grid (giu nguyen leg0) thi CAGR22 / maxDD MTM / UW cua A3 doi bao nhieu (gom ca hieu ung duong di: throttle, U_MAX)?

## 1. Bang chung co san (da nhin - khong dung de chon tham so)
- 8 seed r1-a3-*: 1,39% cum co DCA; PnL leg DCA +8.587/seed (7,5% tong PnL); +9.906 tu 2025-10-10..13; bo su kien do -1.319/seed.
- Script chi doc: ~/claude_master/w3/gridres/dca_contrib.py, dca_event.py.

## 2. Du lieu / cua so
- DEV 2021-07-01 -> 2025-12-31 (nhu R1). KHONG dung 2026 (seal). Khong cham 242.
- Pha 0: data.binance.vision futures/um/daily/aggTrades/<SYM>/<SYM>-aggTrades-YYYY-MM-DD.zip, chi cac (sym, ngay) co leg DCA trong 8 seed (uoc <= 120 file; ghi sha256).

## 3. Pha 0 (0-sim, Oracle, Python offline, RAM < 2G, flock oracle_heavy)
Voi moi leg DCA (sym, start phut t, gia entry p, quantity q):
- V_le(t) = tong khoi luong aggTrades gia <= p trong [t, t+60s). Khop "TIN DUOC" neu V_le >= 3*q (dat hang doi 3x); "YEU" neu q <= V_le < 3q; "KHONG" neu V_le < q.
- Gia khop thay the: p_alt = max(p, VWAP phut t) (bi quan). PnL_alt = q*(exit - p_alt) - phi; exit lay tu printDone (entry*(1+profit/100) cua row).
- Bao: ti le TIN DUOC / YEU / KHONG theo su kien (2022-05, 2022-11, 2025-10-10..13, khac); tong PnL leg DCA goc vs PnL_alt (chi tinh leg TIN DUOC + YEU voi p_alt, leg KHONG = 0).
LUAT P0 (chot truoc):
- P0-FAIL neu (a) leg KHONG o 2025-10-10..13 >= 30%, HOAC (b) tong PnL_alt leg DCA/seed <= 0.
- P0-FAIL => ket luan "dong gop DCA grid chua kiem chung / khong dang tin"; Pha 1 van chay nhung chi de do RUI RO (maxDD/UW), khong ghi "DCA co dong gop".

## 4. Pha 1 (Kaggle, 8 seed cua R1: a1,s7,s13,s21,s99,s123,s777,s2024)
- Arm A3 = dung lai output r1-a3-* (md5 printDone da co; cong G-P0: chay lai 1 seed A3 phai trung md5).
- Arm N = A3 + DCA_GRID_LEVELS=-0.999,-0.999,-0.999 (giu DCA_GRID_WEIGHTS=1,1,1,1, sum=4 => leg0 khong doi). KHONG dung DCA_GRID_ENABLED=false (bat logic DCA cu, DcaProcessor:39).
- Cong G-SIZE: so 200 leg dau tien (truoc leg DCA dau tien cua A3) giua N va A3: margin/entry trung bit. Lech => VOID.
- Cong G-ZERO: N co 0 row DCA_LEVEL1 voi leg>0. Khac => VOID.
- Chi phi: ~40 phut/kernel (secs 2381 cua r1-a3-a1), 8 kernel, 5 song song => ~2 h.

## 5. Chi so va luat (chot truoc)
D = A3 - N, paired theo seed, CI95 paired-t (nhu R1). Chi so chinh: dCAGR22. Phu: dmaxDD MTM 2022-25, dUW, dPnL theo nam, dPnL bo cua so 2025-10-10..13 (cong PnL cac lenh dong ngoai cua so).
- "DCA GRID CO DONG GOP" <=> P0 PASS VA dCAGR22 > 0 voi can duoi CI95 > 0 VA >= 6/8 seed duong VA dPnL bo 10/10 > 0.
- "DONG GOP CHI TU 1 SU KIEN" <=> dCAGR22 > 0 nhung dPnL bo 10/10 <= 0.
- "KHONG PHAN BIET" <=> CI95 dCAGR22 chua 0.
- "DCA GRID HAI" <=> can tren CI95 dCAGR22 < 0.
- Rui ro: bao rieng dmaxDD, dUW, max % equity 1 coin; khong dung de doi phan quyet o tren.
Mot phep chinh (dCAGR22) => khong nhan he so da kiem dinh. Khong them arm/tham so sau khi thay so.

## 6. Quyet dinh (de xuat, owner chot)
- CO DONG GOP: giu nguyen live.
- Con lai: chuyen thanh quyet dinh khau vi rui ro (tran tap trung 1 coin, tail), KHONG goi DCA grid la alpha; can nhac N cho live neu dmaxDD/UW cua N tot hon.

## 7. Khong lam
Khong mo 2026. Khong tune levels/weights/scale. Khong sua Java. Khong cham 242. Khong push.
