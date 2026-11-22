# ERRATA de xuat (DEV-B, R-SIM) cho PREREG_PARITY_V12_DRY_ADDENDUM24_PILOTFID (6ee84f17) - CHO MASTER commit TRUOC luot chinh thuc
Nguoi viet: DEV-B 2026-11-22. Chi dung du lieu cua so DEV (lenh sim start 2026-04-01..06-15, du lieu <= 06-30) + header/danh sach
symbol OW1. KHONG doc / dem / cham output rig tren OW1. Khong in PnL.

## EB1 - Cong thuc von size sim (thay "CHUA XAC MINH" muc 4) - DA XAC MINH
Nguon: jar sim cc0f9d11 build tu a8690d46 (RESULT_DCAGRID_A3: "jar sim cc0f9d11, build tu code a8690d46").
- SimulatorMarketLevelTicker1MStopLoss.createOrder: balanceBasic = sizingEquity() = (FIX_B3=true) BudgetManagerSimple.equityNow();
  marginRunning = BudgetManagerSimple.marginRunning; budget = TradeUtils.managerBudget(budget, marginRunning, equity, level)
  = equity*F_BASE*clamp(1-U/U_MAX)/dcaGridTotalWeight; budget *= tier(=1, TIER_FLAT) ; budget *= DcaUtils.gridLegWeightRatio(legIdx)
  (FIX_B2: w*SCALE = 6) ; qty = Utils.calQuantityTest(budget, 1, close) (floor theo LOT stepSize).
  => leg0 = 0.0225 * E * (1 - U/0.6) (F_BASE 0.015, weights 1,1,1,1, SCALE 6, U_MAX 0.6).
- BudgetManagerSimple.equityNow() = balanceCurrent + unProfit, CA HAI chi cap nhat trong updateBalance() goi MOI GIO
  (time % 60' == 0) va nua dem, SAU khoi vao lenh cua tick do:
    balanceCurrent = CAPITAL_START (35000) + profit ; profit = sum calTp() cac cum DA DONG (calTp = qty*(tp-entry) - phi 0.000982*
    notional - truot 2 chan - funding) ;  unProfit = sum cum DANG MO qty*(lastPrice - entryAvg), lastPrice = close nen 1m cua phut H.
  => E_sim = MTM (KHONG phai balance da thuc hien), chup tai H = moc gio gan nhat < t (t dung moc gio => H = t - 1h).
- U_sim(leg k trong phut t) = [sum margin (qty*entry, don bay 1) cac cum mo truoc t + margin cac leg sim da mo TRUOC trong cung phut]
  / E_sim ; thu tu trong phut = BIG_DOWN truoc, roi PREDICT theo selRank (rank top-24).
- Kiem: tai 16/16 phut vao lenh DEV, E suy nguoc tu margin leg0 vs E tai lap tu printDone (pnl cot = calTp) + close Vision tai H:
  |lech tuong doi| <= 1.2e-5 (3 phut khong cum mo: <= 7.3e-6). Script: w3/add24/b/esim_mtm.py, ssz_inputs.py.

## EB2 - S-SZ: margin_sim gom lam tron qty (floor stepSize) - CAN MASTER QUYET
margin_sim = floor(budget/entry, step)*entry <= f(E,U) ; lech toi da ~ step*entry/margin. REF numpy tren DEV (101 cum): rel max 4.99e-3
(LABUSDT step 1.0), p90 3.9e-4, 95.0 % <= 1e-3, 100 % <= 5e-3 -> sat nguong 5e-3 do lam tron, KHONG do ham size.
De xuat: S-SZ so f_jar SAU cung phep lam tron: qty_jar = floor(f_jar/entry, stepSize) (stepSize exchangeInfo A1 20261027, kiem
trung qty_sim) -> chi so = |qty_jar*entry - margin_sim|/margin_sim (ky vong ~1e-6) ; HOAC giu chi so goc + ghi chu. Nguong giu nguyen.
- Cum DCA (entry != lastentry): printDone chi co margin GOP cac leg, start = leg CUOI -> margin leg0 KHONG tach duoc => loai khoi S-SZ
  (ghi so cum loai). DEV: 0 cum DCA.

## EB3 - S-G: dinh dang dau vao + buffer gate (sua muc 4 "mot dong sel tong hop")
- gateValue cua sel = THEO SYMBOL (sp = 1 - p0 bins A3, sort tang = selector), p15 = THEO THI TRUONG (pred_2026.bin). HO5 CO DU:
  97/97 lenh PREDICT DEV: score tai lap == symbolPred printDone va p15 == pred15m (float32 trung bit). => S-G KHONG INSUFFICIENT.
- Nhung buffer gate jar (LiveGateRollingRatio) phai nap r cua MOI ung vien moi phut nhu sim (sim nap top-24 khong giu, co nen:
  2026Q1 sim log "[GATE-RATIO] 2026Q1 seen=2 938 970"; tai lap 2 938 973, lech +3 = 1e-6). Neu sel chi chua cac symbol sim vao lenh
  (chu nghia muc 4) => buffer trong cua so thieu ~99,99 % ban ghi -> q sai -> S-G vo nghia.
  De xuat: sel = top-24 ung vien sim MOI phut (forward-fill 15' nhu s3_funding/WfoDataset, sort = port quickSortByFloatPred);
  "theo vet" = tap LEGACY dong (symbol khong phai lenh sim o phut quyet dinh va khong dang giu => duong production GATE_NO_ENTRY /
  SKIP_LEGACY_AFTER_GATE: van qua gate jar + nap r, KHONG vao lenh). S-G = jar PASS tai moi (phut, symbol) PREDICT cua sim; bao cao
  them so (phut, symbol) jar PASS ma sim khong vao.
- Buffer warm-up = ung vien sim [W0, START) r tinh bang bieu thuc + hang so EntryGate cua jar; nap bang GateRatioBuffer.bulkAdd cua jar
  SAU LiveGateRollingRatio.init() (init loc persist theo System.currentTimeMillis() = 11/2026 => moi ban ghi 2026Q1-Q3 bi bo neu
  nap qua file persist). Them cong V9 (de xuat): so ban ghi warm-up tai lap / sim log quy == 1 +- 1e-4.

## EB4 - Cau hinh rig R-SIM (override khai truoc, ngoai danh sach 11-16)
LIVE_TS_MKT_EXT=1 + co TS_EXT ngay UTC = SIM_LOSER_TS_EXT_DAYS 2026 (ho_flags.json: 20260205-14, 0216-17, 0224-25, 0611) nap vao TsMktExt
cua jar (ON cac ngay do, OFF MOI ngay khac - tranh PENDING/grace => DEFER sai) ; o.a1=false (sim khong loc A1, K11) ; C3_CAPITAL=10000 ;
LIVE_ADAPTER=dry ; FAKE ; LIVE_APPLY_GRID_RATIO=true ; LIVE_DCA_GRID_ENABLED=true ; C3_EXCLUDE_LEGACY_HELD=false.
Luu y OW1: KHONG co ngay TS_EXT nao trong 07-01..09-30 => X14 khong the kich trong OW1 (dieu kien mau X14 cua S-X khong ap).

## EB5 - S-D / mkt.csv.gz
Rig can mkt.csv.gz (nen 1m MOI symbol) cho dieu kien thi truong DCA (ERRATA1 N6). Fixture R-SIM DEV dung mkt RONG => rig KHONG the DCA.
DEV: 0 cum DCA o sim (2026-01..06-15) => S-D = INSUFFICIENT (phu boi C0b S-DCA). OW1: CHUA xem (khong mo). Script chinh thuc tu dem
cum DCA trong OW1 (entry != lastentry) va DUNG neu > 0 ma chua co mkt OW1 (can MASTER quyet: tai mkt toan thi truong Q3 ~1-1,5 GB tmpfs,
+~1 h; hoac S-D INSUFFICIENT + loai cum DCA khoi S-X).

## EB6 - Dinh nghia giu (held) tu printDone
PREDICT: giu tu start+1' ; BIG_DOWN: tu start (nhanh BIG_DOWN chay truoc selector trong tick) ; den end (khong gom). Cum DCA: start =
leg cuoi => thoi diem leg dau khong biet (canh bao; DEV 0).

## EB7 - exchangeInfo A1 20261027: 10/101 cum DEV co symbol status=SETTLING (huy niem yet sau Q2). Neu jar tu choi vao lenh SETTLING
=> lech do snapshot, khong do logic: can nhan rieng hoac patch status=TRADING trong ban fixture (MASTER quyet). (cap nhat sau luot DEV)

## Cap nhat sau luot DEV (DEV1..DEV3, 2026-11-22 ~10:15)
EB7 (xac nhan): DEV2 dung exInfo 20261027 nguyen ban: 6 lenh sim NOT_BUYABLE/NOT_TRADING (STG, EPIC x3, VIC, D: status SETTLING o 10/2026)
 => rig KHONG giu cac symbol nay -> chung tiep tuc la ung vien va nap r cao vao buffer -> q jar tang -> day chuyen 14/97 S-G REJECT
 (r < q sat nut, vd 06-04 08:22 INUSDT r=0.0060961 q=0.0061027). DEV3 patch status SETTLING->TRADING (PERPETUAL USDT) trong BAN SAO
 fixture: S-G 97/97 PASS. De xuat: R-SIM dung --patch-settling (khai truoc, ghi danh sach symbol patch vao fx_check.json).
EB8 (MOI - lech THAT jar vs sim, KHONG phai harness): jar chan mua symbol sap huy niem yet (NOT_BUYABLE DELIVERY_SOON, deliveryDate
 2026-06-11 16:00 +07): DEV3 3 lenh sim (DUSDT 06-05 21:01, HIGHUSDT 06-05 21:01 va 06-06 11:31) rig khong vao. Prereg khong co nhan cho
 truong hop "sim vao, jar chan theo guard production". De xuat MASTER: bao cao rieng (dem), khong tinh vao S-X; S-G van tinh (gate PASS).
EB9 (harness): KillSwitch C1 can nen BTCUSDT moi phut (ref) - fixture R-SIM sparse => latch NO_NEW_ENTRY tu 04-01 00:05 (DEV1, 0 lenh).
 Sua: them BTCUSDT 1m Vision cho [START, END) vao klines (dl_ref.py). Khong doi tieu chi.
EB10 (harness): CrashDayRig dung .defer((s,t0,n)->false) (E2E tat X14). R-SIM: launcher (add24/b, KHONG sua code DEV-A) thay defer cua
 TrailingStopManager bang TsMktExt::deferTimeStop CUA JAR (= mac dinh production khi builder khong truyen defer) ngay khi mgr tao (truoc
 moi time-stop). DEV2 (khong swap): 3 cum 06-04 08:22 (US, MYX, SWARMS) cat 168h, sim hoan toi 190.6h (ngay UTC 06-11 ON) -> lech -1357'.
 DEV3 (swap): 11/11 time-stop dung phut, 4 cum X14 hoan 190.6h trung sim. De xuat DEV-A them co env (vd E2E_X14=jar) trong harness de A1
 duyet 1 duong duy nhat thay vi reflection.
EB11 (CAN MASTER QUYET TRUOC OW1 - rui ro S-X FAIL do quy uoc rig, khong do logic jar):
 (a) Phut thoat: DEV3 80/98 cum cung phut (81.6 % < 95 %); 13 cum lech +-1' (11 cum -1': rig nang SL trong nen theo duong gia noi suy
     10-15 s roi cham low cung nen; sim nang SL tu high nen t chi ap tu nen t+1 = K8/B1); 5 cum lech > 1': CLOU -203', EPIC -23',
     VIC +17', MAGMA +9', OPN +3'.
 (b) Gia thoat: TB Delta(rig-sim)/sim = -0.65 % (trong [-0.8 %; 0]); 6 cum < -1.5 %: TA -12.87 % (cung phut, nen gap: sim chot
     min(SL, open) theo TASK-118, rig khop stop theo mo hinh FakeExchange1m), CLOU -12.52 % (rig ARM o peak 7.04 % theo gia vao rig
     0.18106, sim gia vao = close 0.18114 -> peak 6.99 % < 0.07 chua arm -> sim giu tiep), SKYAI -3.14, US -2.89, ALLO -2.85/-2.02.
 Nguyen nhan chung = (i) gia vao rig != gia vao sim (S-E TB +0.41 bps, p90 8.9 bps) lam lech nguong arm 7 % sat bien; (ii) mo hinh khop
 stop / nhip trong nen cua FakeExchange1m khac booking sim. Lua chon (KHONG doi nguong): giu nguyen va chap nhan S-X co the FAIL vi quy
 uoc; HOAC errata "theo vet" gom ca GIA VAO = sim entry (Fake fill leg0 tai close nen sim) + nhan N8 dung REF-nhip (A1 kiem). MASTER quyet.
EB12 (harness gate init): LiveGateRollingRatio.init() nap persist voi now=System.currentTimeMillis() (11/2026) -> buffer 2026 bi bo het,
 seed Aerospike rong -> fallback base 0.008 (DEV1). Sua: launcher goi init() roi GateRatioBuffer.bulkAdd (ham jar) voi 2 938 973 ban ghi
 warm-up truoc harness; startProduction sau do no-op (inited).

## LUOT 2 (sau ERRATA1 29152e39) - de xuat cho ERRATA2 (MASTER quyet)
EB13 (SUA nhan dinh EB2/EB5/EB6 cua DEV-B): printDone.csv ghi 1 DONG / LEG (khong phai 1 dong/cum). Cum = nhom (sym, end); cum DCA = nhom
 > 1 dong (leg0 + leg DCA_LEVEL1); cot entry/margin/quantity/start la cua TUNG leg. => margin leg0 cua cum DCA TACH DUOC (dong leg0);
 start leg dau = start dong leg0 (khong can suy). Toan bo 2021-2026: 53 cum nhieu leg (2026: 4). Script da sua: cum DCA = nhom > 1 dong.
 Tac dong: (a) S-SZ: co the cham leg0 cua cum DCA (ERRATA1 dang loai - giu loai hay cham? MASTER); (b) E_sim/U_sim/held da tinh theo
 dong nen KHONG doi (DEV 101 dong = 101 cum 1 leg).
EB14 (MAU OW1, dem tu printDone, khong chay rig): OW1 81 leg / 80 cum (68 cum leg0 PREDICT, 12 BIG_DOWN), 67 leg PREDICT trong **16 phut**,
 21 phut vao lenh (moi level). S-G nguong mau ">= 50 phut vao" => S-G OW1 = INSUFFICIENT chac chan (16 < 50), ke ca DEV + OW1 (14+16=30).
 S-SZ: ~79-80 leg0 (>= 50 OK). S-X: 79 cum 1 leg co the cham (>= 30 OK), time-stop 12 (>= 1), trail 67 (>= 1). 1 cum DCA (leg0 PREDICT
 2026-06-25 20:53 TRUOC cua so, leg DCA 07-01 08:12 va 07-02 20:37) => loai khoi S-X/S-SZ/follow, dem; S-D OW1 = 0 su kien.
 => Neu khong co ERRATA2 cho dinh nghia mau S-G (vd dem lenh PREDICT 67 thay vi phut 16), ADD24 = INSUFFICIENT (P4: khong pilot).
EB15 (V9 OW1): warm-up buffer tu 04-02 (prereg) nhung sim log dem theo quy 2026Q2 tu 04-01 => script dem ung vien tu 04-01 (cung bins/
 held/availability) de so V9 voi 3 011 221, buffer van chi nap tu 04-02 (ban ghi 04-01 nam ngoai cua so 90 ngay tai 07-01 nen khong anh huong q).
EB16 (exchange_info_pin sim != exInfo 20261027): sim kernel dung exchange_info_pin.json (tickSize VELVET 0.0001; rig 0.00001) => SL sim
 lam tron theo tick cu: DEV4 VELVET 06-05 13:22 lech -4' (low 0.14042 > SL sim 0.1404, <= SL rig ~0.14045). Nhan de xuat: TICK_SNAPSHOT
 (bang chung: tick 2 ban exchangeInfo + SL 2 ben). Co the khu: dung tickSize/minQty cua pin sim cho rig R-SIM (pin md5 5a815948 o
 1009/ho26/kaggle/sim-ho26a-bundle - CAN xac minh la cung file voi bundle HO5 sim-x1-2021-bundle).

## LUOT 3 (sau ERRATA2 bb91e639) - de xuat ERRATA3 (MASTER quyet)
EB17 (S-G2, DEV 2026Q2): tho: jar PASS 147 vs sim 122, seen 3 015 422 vs 3 011 221 (+1.4e-3) => FAIL theo chu. Nguyen nhan duy nhat may doc
 duoc: N10-cascade - DUSDT/HIGHUSDT (jar chan DELIVERY_SOON, sim GIU tu 06-05 21:01) khong duoc rig giu nen van la ung vien: 4 237 dong
 gate + 25 PASS (toan bo 25 PASS "thua" la 2 symbol nay, 06-05 22:45..06-06 11:38). Loai cac dong (symbol N10, phut trong khoang sim giu):
 PASS 122 == 122 (bang tuyet doi), seen 3 011 185 (-1.2e-5 <= 1e-4); 122/122 lenh sim jar PASS. De xuat: S-G2 dem sau khi loai N10-cascade
 (nhan may: symbol co N10 + phut trong [start(+1'), end) cua cum sim) - hoac rig coi symbol N10 la "dang giu" trong khoang sim giu.
EB18 (S-X lane CHINH DEV5, O-L-H-C, khop min(SL,open)): (a) 98/98 ; (b) cung phut 92/98 = 93.9 % (< 95 %), 6 cum -1' (DEXE, VELVET, BTW,
 GUA, PLAY, LAB) - CA 6 la K8 (REF-nhip cung phut rig, REF-sim cung phut sim): moc H nang SL roi moc C <= SL cung nen; sim chi ap SL moi
 tu nen sau => N8 hop le 6/98 = 6.1 % (< 10 %). (c) TB +0.078 % (rig CAO hon sim, NGOAI [-0.8 %; 0] theo chu), cum thap nhat 0.000 %,
 0 cum < -1.5 %; bo 6 cum N8: TB +0.022 %. => Can MASTER chot: (b) 95 % tinh truoc hay sau nhan N8; (c) can tren 0 co ap khi rig >= sim.
 Sua mo hinh khop (score): SL dat TRONG nen khop (nang tai H cung nen) => khop = SL (khong ap min(SL,open) vi SL chua ton tai luc open).
EB19 (lane DO NHAY O-H-L-C, chi bao cao): 41/98 cum doi phut thoat so lane chinh; Delta gia thoat sens-vs-chinh: TB -0.91 %, p05 -9.09 %,
 trung vi 0, min -12.18 %, max 0. (So voi sim: cung phut 52/98, 16 cum < -1.5 %, TB -0.84 %.)
EB20 (3b FIGHT - CHAN): Add24DcaProbe (ham jar getMarketStatus1M / isDcaAlt / shouldDcaGrid / AIRejectFilter.entryGate sp=null) voi CHINH
 market.bin cua sim (kernel ho4p1-chain-y26 md5 0fcc44d8 = HO5, trich 2026-01-01..02-06 23:59): jar DCA FIGHT 02-01 00:10 (TRUNG rig Vision);
 82 phut truoc 02-06 du dieu kien thi truong + gia + gate ma sim KHONG DCA; SPACE 02-06 04:19 khop ca 2 nguon. => KHONG phai nguon thi truong
 => theo ERRATA2 3b(2): LECH DCA (jar-trong-rig vs sim). Ung vien co che: sim chan DCA_LEVEL1 cho TIER_3 (Sim:1431-1436); production jar CUNG
 chan (C3LiveHook.onLeg tier3 = CoinRankManager.peekCoinTier) nhung CrashDayRig truyen tier3=false ("gioi han", dong 911) => co the la
 thieu harness, KHONG chac logic jar. Xep hang xap xi tu Vision (tong quote vol 720') cho FIGHT top 3-28 % (khong TIER_3) => chua giai thich
 duoc; can du lieu ticker cua sim (ho4p1-tk26, 273 file/ngay, dung luong lon) hoac log TickDecisionLog de phan xu. KHONG mo OW1 (ERRATA2).
EB21 (3c S-SZ DEV-2): o phut 02-01 00:12 (H = 02-01 00:00) E suy nguoc tu 18 leg NHAT QUAN (lech nhau <= 1e-4) va thap hon E tai lap 2.11 %;
 01:43 (H 01:00) tuong tu; 00:11 BIG_DOWN 2 leg khong nhat quan (-5.4 % / +1.0 %). REF numpy = jar => sai o E_sim tai lap (khong phai jar).
 Cac phut khac DEV-2 / DEV: <= 1.2e-5. Nghi: gia MTM cua sim tai H (ticker sim tu 242/Aerospike) khac Vision cho 6 cum dang mo (FIGHT -50 %,
 SPACE -26 % ...) hoac sizing BIG_DOWN rieng. CHUA tim ra (can ticker sim ngay 01-31/02-01). Theo ERRATA2 3c: OW1 cham theo nguong, leg lech
 phai co giai thich may doc, khong thi FAIL.
EB22 (V6 off-by-one): rig quyet dinh nen b o phut b+1 => phut cuoi cua sel khong duoc xu ly neu END = het du lieu. Sua: manifest END = END_DATA
 + 1' (build_fx --end_pad), klines van < END_DATA. DEV5b: 131 040 = 131 040.

## LUOT 4 - B5 (FIGHT) PHAN XU: KET LUAN (2) - DIEU KIEN TIER CUA SIM KHAC PRODUCTION (bao MASTER ngay)
Bang dieu kien 1 leg DCA (FIGHT leg0 PREDICT 01-30 08:43 gia 0.016396; t1 = 02-01 00:10, t2 = 02-06 04:01):
| Dieu kien | Sim a8690d46 | Jar production 76134a52 | Rig harness | FIGHT t1 | FIGHT t2 |
| thi truong | Sim:353-385 getMarketStatus1M BIG_DOWN / Sim:396-397 isDcaAlt (market.bin) | DetectEntrySignal2TradeNormal + C3LiveHook.dcaDue (MarketBigChangeDetector cung ham) | MarketReplay (Vision) | alt=TRUE (down -0.01251 < -0.01052) | alt=TRUE (down -0.01161) |
| gia bac grid | DcaProcessor.getDCA -> DcaUtils.shouldDcaGrid(first,lastPrice,legCount) L1=-0.50 | C3LiveEntry:238 gridDue.due (cung DcaUtils) | cung | c sim 0.008196 => -0.50012 <= -0.5 TRUE | -0.6105 TRUE |
| ticker co mat | Sim:403 isTickerAvailable | nen live | nen Vision | co (ticker sim h!=l) | co |
| gate | Sim:1374 entryGate sp=null => p15 >= MIN_MOMENTUM_15M 0.008 (EntryGate:195) | AIRejectFilter cung nhanh | cung | p15 0.01506 PASS | 0.02822 PASS |
| so / U | managerBudget null neu U>=0.6 | C3LiveEntry managerBudget | cung | U ~0.075 | U ~0.39 |
| tran per-coin | Sim CONC_PC 15 % (log SUMMARY blocked=0 ca run) | CONC_PC live | - | ~4.5 % | ~4.5 % |
| TIER_3 chan DCA | Sim:1431-1436 getCoinTier(symbolId,t) -> CoinRankManager.checkAndUpdate: CHI cap nhat khi duoc GOI dung phut %60==0 (chi goi tu createOrder sau gate) | C3LiveEntry:243 in.tier3 = C3LiveHook:109 peekCoinTier; xep hang cap nhat MOI GIO vi LiveFeaturePipeline nuoi HistoryManager + getTopCoin(time) moi phut | CrashDayRig:911 tier3=false (thieu) | SIM: UNKNOWN->TIER_3 (cap nhat cuoi 01-19 07:00, FIGHT niem yet 01-23) => CHAN ; PRODUCTION (xep hang moi gio tu ticker sim): FIGHT hang 58/545 = TIER_1 => KHONG chan | sim cap nhat 02-06 04:00 (lenh sim 04:00) => FIGHT hang 22/547 T1 => DCA 04:01 |
Bang chung: (a) lenh sim o phut :00 trong 2025-12..2026-06 chi co 01-19 07:00 (BIG_DOWN) va 02-06 04:00 (PREDICT) => moc cap nhat tier;
 (b) DCA FIGHT 02-06 04:01 = 1 phut sau lenh 04:00; SPACE 04:19 cung sau moc nay; (c) xep hang tai lap bang code CoinRankManager/HistoryManager
 a8690d46 tren CHINH ticker sim (ho4p1-tk26 ticker_20260123..0206, md5 khop tk_raw_md5.json): FIGHT T1/T2 suot 01-30..02-06;
 (d) Add24DcaProbe: moi dieu kien khac (thi truong market.bin sim, gia ticker sim, gate) cho DCA 02-01 00:10.
=> Sim chan DCA FIGHT 5 ngay vi tier CU (lazy update) - production jar voi xep hang moi gio se DCA 02-01 00:10 (nhu rig). Quy tac giong,
 TRANG THAI tier khac do nhip cap nhat => hanh vi DCA jar production KHAC sim (moi symbol niem yet / doi hang sau moc cap nhat cuoi
 cua sim). Sua harness (tier3 that) KHONG lam khop: rig se van DCA 00:10. Theo ERRATA3 B5: (2) => KHONG mo OW1, MASTER bao owner.
Tac dong rong (de MASTER danh gia): tier sim co the cu nhieu tuan (chi cap nhat khi co lenh/gate-pass dung phut :00) => DCA (va moi
 nhanh dung tier) cua HO5 / A3 sim phu thuoc moc cap nhat ngau nhien; OW1: 1 cum DCA (leg0 06-25) co 2 leg DCA 07-01/07-02 - chua kiem.
3c: chua giai thich bang co che tier (TIER_FLAT=1 => tier khong doi size). Van mo, N11 xu ly.

## LUOT 5 (de xuat, cho MASTER)
- EB23: tier cu cua sim => 3 leg DCA "sim chan / production DCA" trong 2026Q1-Q3 (FIGHT som 123,85 h; SLX, OPN sim khong DCA); 0 nguoc
  lai. Tier chi chan DCA (TIER_FLAT=1). Chi tiet dev_results/TIER_IMPACT.md.
- EB24: file ticker tk26 theo ngay UTC => tai lieu <= 2026-09-30 23:59 +07 thi KHONG tai ticker_20260930 nguyen ngay (hoac cat khi doc).

## LUOT 6 (de xuat, cho MASTER)
- EB25: S-D tren OW1 = INSUFFICIENT theo cau truc (OW1 khong co cum DCA leg0 trong cua so - EB5, va fixture khong co mkt toan san nen rig
  khong co nhanh DCA); V-TIER OW1 chi dem tren du lieu sim (0).
- EB26: N11 - "vuot nguong" = sai so EB2 (lam tron qty) > 1e-3; cum E suy nguoc trong 1e-4 quanh chinh leg do, can >= 3 leg.
- EB27: DEV-2 S-SZ: 4 leg BIG_DOWN 01-31 khong N11 (E suy nguoc khac cac leg PREDICT cung phut) - neu OW1 co phut tuong tu se FAIL; can
  MASTER quyet co dieu tra size BIG_DOWN truoc OW1 khong.

## LUOT 7 (de xuat, cho MASTER)
- EB28 (S-SZ dau vao, KET LUAN (1) - loi cong thuc tai lap cua DEV-B): vi the HUY NIEM YET trong sim (a8690d46 Simulator:474-480 +
  updateSymbolDeListed:907-913): khi ticker bien mat, sim chi dong vi the o moc gio dau tien time > timeUpdate + 2 ngay (va khong o nhanh
  nua dem UTC), priceTP = lastPrice; printDone ghi end = timeUpdate (gio ticker cuoi). Trong 2 ngay do marginRunning VAN gom margin vi the.
  ssz_inputs cu giai phong margin luc end => U thap hon that => 21 leg PREDICT N11 o 02-01 00:12 / 01:43 (COMMON 1 866,5, delivery 01-30 16:00).
  Sua: ssz_inputs_l7.py giu margin + MTM q*(tp - e) toi luc dong that. Kiem: lech E con -1,1e-4 / -1,3e-4 (truoc +2,16 %).
- EB29 (S-SZ dau vao, (1)): thu tu leg BIG_DOWN trong 1 phut cua sim = thu tu duyet HashSet<Short> symbol2BUY (Simulator:350-376; bucket = id &
  (cap-1), id mapper HO5), KHONG theo hang. ssz_inputs cu xep theo hang => U cua leg BIG_DOWN sau sai (RIVER 02-01 00:11 / 01:43).
- EB30 (bao MASTER, khong cham): production jar (DetectEntrySignal2TradeNormal:444-466) duyet symbol2BUY = HashSet<String> (thu tu theo
  String.hashCode) - KHAC thu tu sim (HashSet<Short> theo id). Khi >= 2 leg BIG_DOWN cung tick, leg sau co U lon hon => size nho hon; doi thu
  tu thi doi size tung leg (vd 02-01 01:43: BULLA / RIVER moi leg ~ +-3,7 %), tong margin tick gan nhu khong doi. Rig theo bigdown.csv (A-Z).
  S-SZ (ham size voi dau vao sim) khong do dieu nay. OW1 co 12 cum BIG_DOWN: MASTER quyet co can chi so rieng.
- EB31 (EB25 thuc thi): mkt toan san chi cho ngay co gia sim cham bac (OW1: 09-15..09-22 UTC, chi cum AIN leg0 09-16 01:45 - ngoai cua so
  cham S-D); trong cua so cham [07-01, 09-16) KHONG cum nao co gia cham bac 1 => S-D OW1 = PASS_ZERO neu rig 0 leg DCA.

## LUOT 8 (de xuat, cho MASTER)
- EB32: S-SZ "lech" (R2) = leg EB2 > 5e-3 HOAC ti le <= 1e-3 < 90 % (sau N11); leg > 1e-3 chi N11 khi >= 3 leg cung phut, E suy nguoc trung 1e-4.
- EB33: S-X trang thai cum: NO_EXIT_SAU_END (sim thoat sau END fixture) khong la lech; cum DCA cham o S-D.
- EB34: DEV-2 khong dung cho S-G (V9 false: buffer gate chi tu 01-01) - ket qua HUY la dung thiet ke; OW1 warm-up 04-02..06-30 du quy.
