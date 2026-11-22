# A1_ADD24_TIER - A1 doc lap kiem phat hien DEV-B "tier sim cap nhat luoi" (R-SIM B5 / FIGHT) - 2026-11-22 ~16:55 +07
Nguon: sim a8690d46 (git ~/src/BinanceFuturesJava, archive src/main/java), jar pilot 76134a52 (~/claude_master/w3/c3_hotfix, chi doc).
Du lieu: printDone HO5 s123 (CHI cot sym / start / level), prof_run.properties. Khong chay sim / rig, khong tinh PnL.

## 1. Bang 5 khang dinh
| # | Khang dinh DEV-B | A1 | Bang chung |
|---|---|---|---|
| 1 | Sim chi cap nhat tier khi getCoinTier duoc goi dung phut %60==0, chi tu createOrder | DUNG (co bo sung) | CoinRankManager.java:129-139 checkAndUpdate: cap nhat khi (phut %60==0 va key moi) hoac symbolTiers rong; WFO_STATIC_RANK khong dat trong prof_run (chi TIER_FLAT=1) => nhanh tinh. Trong sim, caller DUY NHAT cua ham co cap nhat la SimulatorMarketLevelTicker1MStopLoss.java:1431 (getCoinTier); :1455 getBudgetMultiplier khong cap nhat; grep toan nguon: khong caller khac trong duong sim. :1431 nam SAU gate (:1371), burst-cooldown, PumpDump, GATE_COUNT_ONLY, va TRUOC budget => goi cho MOI leg (PREDICT / BIG_DOWN / DCA) da qua gate, KE CA leg sau do bi tu choi budget / TIER3 - tuc la "chi tu createOrder sau gate" dung, nhung moc cap nhat that >= so lenh :00 trong printDone (printDone la CAN DUOI). |
| 2 | UNKNOWN => TIER_3 => chan DCA trong sim | DUNG | CoinRankManager.java:91-97 (UNKNOWN -> TIER_3); Sim:1431-1436 TIER_3 + DCA_LEVEL1 => return (D_TIER3_DCA). Coin niem yet sau moc cap nhat cuoi khong co trong xep hang => UNKNOWN. |
| 3 | Production cap nhat moi gio, doc lap voi viec co lenh | DUNG | LiveFeaturePipeline.java:201-207 extractorSink.feed(minute): updateMarketHistory + getTopCoin(minute) MOI phut cua vong feature (ke ca seed khi khoi dong :265) => checkAndUpdate o moi phut :00. Them DetectEntrySignal2TradeNormal:1012 getTopCoin, :1439 getCoinTier (duong so giay). C3LiveHook:109 dung peekCoinTier (KHONG cap nhat, doc tier hien tai). |
| 4 | Production: tier3 chan DCA (va con gi?) | DUNG - chi chan DCA | C3LiveEntry.java:236-243: DCA => sau gridDue, in.tier3 => TIER3_DCA. Leg moi (PREDICT/BIG_DOWN) khong kiem tier3. Size: C3LiveEntry:268 b x tierMultiplier = getBudgetMultiplier => 1.0 khi TIER_FLAT=1 (CoinRankManager:117). TIER_FLAT=1 co trong env242_whitelist 11-16 VA prof_run sim => tier KHONG doi size o ca 2 ben. CANH BAO: banner live 06:17 KHONG in TIER_FLAT (V8 khong so duoc) - neu 242 khac 1, L-S se bat (bao thu). |
| 5 | Quy tac xep hang giong nhau | GIONG ve CODE, dau vao universe CHUA chung minh | CoinRankManager: khac duy nhat la them peekCoinTier (diff). Cua so 720 nen, tong volume (HistoryManager.getSumVolume), T1 top 20 %, T3 bottom 20 %, tie-break A-Z: giong. HistoryManager khac: MAX_COINS 1000 (sim) vs SymbolIdLimits.CAPACITY + loai symbol quarantine (jar). Tap symbol duoc nuoi (sim: ticker sim; live: snapshot feature) co the khac (A1 / died / quarantine / TradFi) => thu hang co the lech o bien 20 % / 80 %. |

## 2. Bang chung du lieu FIGHT (printDone, chi thoi gian / symbol / level)
- Lenh sim co start o phut :00 trong 2025-10 .. 2026-06: ... 2025-10-12 03:00 (XNY) -> 2026-01-19 07:00 (DUSK, FHE BIG_DOWN) ->
  2026-02-06 04:00 (BRETT, SOLV, SWARMS PREDICT). KHONG co lenh :00 nao giua 01-19 07:00 va 02-06 04:00. TRUNG DEV-B.
- FIGHT: leg 0 PREDICT 2026-01-30 08:43; DCA_LEVEL1 2026-02-06 04:01 = 1 phut sau moc :00 duy nhat => khop co che (tier FIGHT UNKNOWN->T3
  tu khi niem yet 01-23 toi 02-06 04:00).
- Gioi han: printDone chi la CAN DUOI cua moc cap nhat (leg qua gate o :00 bi tu choi budget/TIER3 khong vao printDone). DEV-B khang dinh
  da tai tao day du (319 gate pass = 319 leg; 0 ung vien DCA o :00) - A1 KHONG tai tao doc lap muc nay. Xep hang theo gio cua DEV-B
  (FIGHT hang 58/545 -> T1) hop ly ve dinh tinh (coin moi niem yet volume lon) nhung A1 KHONG chay lai.

## 3. Cach giai thich khac (da xet)
- Dieu kien thi truong / gia bac / gate / U / tran coin tai 02-01 00:10: DEV-B probe ham jar tren market.bin + ticker sim cho TRUE; A1 chi
  doc bang, khong chay lai. Neu mot dieu kien nay sai, DCA van phai den o phut dau tien cac dieu kien dung - thoi diem 04:01 dung 1 phut sau
  moc :00 duy nhat trong 18 ngay la bang chung manh cho co che tier (xac suat trung hop rat thap).
- MAX_COINS=1000 cua sim (id >= 1000 bo im lang => UNKNOWN vinh vien): bi bac bo cho FIGHT (sim co DCA sau 02-06 => FIGHT da duoc xep hang).
  Nhung la co che lech TIEM AN khac cho symbol id >= 1000 (A1 chua kiem id).
- WFO_STATIC_RANK (tier tinh theo gio tu file): khong bat trong prof_run => loai.
- Jar sim cc0f9d11 == nguon a8690d46: A1 KHONG kiem (lay theo HO5 / DEV-B). Rui ro thap.

## 4. Ket luan: (I) LOI CUA SIM - do tin cay cao (chua tuyet doi: muc 2 gioi han + jar sim = nguon chua kiem lai)
- Y do thiet ke ro: tier theo gio (number_minute_update=60, khoa interval theo gio, ExportCoinTierStatic / WFO_STATIC_RANK tinh theo gio).
  Sim (khong con vong feature moi phut vi dung bins dung san) chi kich cap nhat ngau nhien qua getCoinTier o phut :00 => tier cu toi ~230
  ngay. Jar production (vong feature goi getTopCoin moi phut) cap nhat theo gio = dung y do. Jar KHONG loi.
- He qua cho HO5 / ky vong: sim CHAN DCA nhieu hon production voi coin moi / doi hang (DEV-B: Q1 1 leg, Q2 2 leg, Q3 0; 0 chieu nguoc).
  Production se DCA nhieu hon sim => phoi nhiem / ky vong 23 %/nam cua HO5 KHONG phan anh dung nhanh DCA cua jar. Owner can biet.
- He qua cho R-SIM: tier chi chan DCA (TIER_FLAT=1 hai phia) - KHONG tac dong truc tiep gate, size, thoat, BIG_DOWN. Tac dong GIAN TIEP:
  leg DCA lam doi U / margin / gia vao trung binh cua cum => size cac leg sau + thoat cua cum do. OW1 (Q3) theo mo hinh DEV-B: 0 leg lech
  tier => phan gate / size / thoat cua R-SIM OW1 VAN DUNG DUOC, voi dieu kien cong (duoi) xac nhan 0 su kien trong OW1.

## 5. De xuat xu ly (khong ha chuan)
1. ERRATA3 B5 chi co (1) harness / (2) jar / (3) khong phan xu. Day la loai MOI: "sim (chuan so) lech y do, jar dung" - KHONG duoc tu
   quy ve PASS. MASTER ra ERRATA4 TRUOC khi mo OW1, gom:
   a. Cong MOI V-TIER (R-SIM OW1): chay mo hinh tier theo gio (ham jar, ticker sim) song song tier luoi cua sim; moi leg sim / ung vien DCA
      trong OW1 ma hai tier khac nhau o quyet dinh chan DCA = su kien TIER_DIV. TIER_DIV > 0 trong OW1 => cum lien quan loai khoi S-X / S-SZ
      / S-D va S-D = INSUFFICIENT KHONG phu (khong duoc gan nhan "giai thich duoc"); TIER_DIV = 0 => cham OW1 theo nguong goc.
   b. Ket luan ADD24 ve DCA: khong the PASS S-D bang so voi sim nay. Hoac (khuyen nghi) sua sim (goi cap nhat tier moi phut nhu production,
      hoac WFO_STATIC_RANK tu bang tier theo gio) -> chay lai HO5 s123 2026 (Kaggle, prereg rieng / errata, KHONG doi tham so khac) ->
      chi duoc khac o cac leg TIER_DIV + day chuyen; R-SIM so voi sim da sua. Hoac owner chap nhan BANG VAN BAN: DCA = INSUFFICIENT,
      kem so luong DCA lech uoc tinh 2026 va ghi chu HO5 danh gia thap nhanh DCA cua jar.
   c. MASTER bao owner ngay: (i) sim HO5 lech jar o nhanh DCA tier (so leg / quy), (ii) chieu tac dong (production DCA nhieu hon),
      (iii) ky vong 23 %/nam can danh dau "sim tier luoi".
2. Kiem them truoc OW1 (DEV-B, A1 duyet sau): symbol id >= 1000 trong sim (MAX_COINS) - co coin nao trong 2026 bi UNKNOWN vinh vien;
   tap symbol nuoi HistoryManager sim vs live (A1 / quarantine) - lech thu hang o bien T3.
3. R-LIVE (lien quan): rig CrashDayRig:921 tier3=false - production chan DCA coin T3 (xep hang moi gio). DCA live trong OW2 cua coin T3 se
   thanh lech khong nhan (FAIL gia) - xem A1_ADD24_HARNESS_R2 muc N2.
