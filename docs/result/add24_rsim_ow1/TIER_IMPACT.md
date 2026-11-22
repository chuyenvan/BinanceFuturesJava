# ADD24 LUOT5 - TIER_IMPACT (DEV-B) - tac dong tier CU cua sim HO5 Lane L s123, 2026-01-01..09-30 (+07). KHONG PnL. 2026-11-22
Nguon: printDone HO5 (3941 dong), market.bin sim (md5 0fcc44d8, trich <= 09-30 23:59 +07), pred_2026.bin (p15), ticker sim ho4p1-tk26
(273 file 20260101..20260930, md5 sau giai nen khop tk_raw_md5.json 273/273, doc tuan tu roi XOA). Ham jar stub (cf0f4792) trong bwrap:
Add24TierAll (tier theo gio), Add24DcaAll (dieu kien DCA moi phut). Phan tich: l5_tier.py -> dev_results/tier_impact.json.
Co che (a8690d46): CoinRankManager.checkAndUpdate chi cap nhat khi duoc GOI o phut %60==0; trong sim chi Sim:1431 getCoinTier (createOrder,
SAU gate) goi no. Production (76134a52) goi getTopCoin moi phut (LiveFeaturePipeline:206) => cap nhat moi gio.

## (a) Moc cap nhat tier cua sim (lenh vao createOrder dung phut :00)
| moc (+07)        | cach moc truoc (ngay) | nguon |
| 2025-10-04 00:00 | -     | leg printDone |
| 2025-10-11 04:00 .. 2025-10-12 03:00 | 15 moc, cach 0,04-0,17 | leg printDone (cum BIG_DOWN 10-11) |
| 2026-01-19 07:00 | 99,17 | leg BIG_DOWN (DUSK, FHE) |
| 2026-02-06 04:00 | 17,88 | leg PREDICT |
| (khong co moc nao 02-06 04:00 -> 09-30) | >= 236 | - |
Do day du 2026: gate pass PREDICT sim (GATE-RATIO 103+122+94 = 319) = 319 leg PREDICT printDone => moi lan qua gate deu thanh lenh (khong
co lan goi getCoinTier "an"); BIG_DOWN: 16 phut thi truong < -0,03157 trong 2026, chi 1 phut :00 (01-19 07:00, co lenh); ung vien DCA o
phut :00: 0 (mo hinh 1c). => 2 moc 2026 la DAY DU (tru bo loc burst/PumpDump, chi lam GIAM).
Do cu tier sim (ngay) tai:            n    TB      trung vi  max
  moi leg PREDICT 2026               319  110,67  118,18    229,72
  moi leg DCA sim 2026                 6  124,17  145,93    226,57
  moi phut du dieu kien DCA (1c)     172   39,39   17,63    226,57

## (b) Tier dung theo gio
Add24TierAll: ring 720 totalUsdt / symbol (HistoryManager), xep hang giam dan (hoa: ten symbol), T1 < 20 %, T3 >= 80 %, UNKNOWN -> T3;
6 552 gio; n symbol 537 (01-01) -> 667 (09-30). tier_hourly.csv.gz (md5 51d66b3f) + closes.csv.gz cho 357 dong printDone +-1h (md5 16fc5890)
trong /dev/shm/add24/b/l5/. Gio dau 2026-01-01 07:00 +07 (file ticker theo ngay UTC).

## (c) So quyet dinh DCA: tier cu (sim) vs tier dung (production), moi cum sim cham 2026 (351 cum; 6 cum co phut du dieu kien)
Dieu kien phut: BIG_DOWN (getMarketStatus1M) hoac isDcaAlt tren market.bin sim; gate entryGate(sp=null) p15; shouldDcaGrid(first, close
sim, legCount); U < 0,6 (E = 35000 + da dong, noi bo); tran per-coin 15 % khong bao gio chan (LUOT4). Kiem mo hinh: tai tao 6/6 leg DCA
that cua sim dung phut (duong tier cu).
| quy    | (i) sim CHAN, prod DCA: cum / leg / sum % von | som hon (h) hoac sim khong DCA | (ii) sim DCA, prod CHAN | (iii) trung |
| 2026Q1 | 1 / 1 / ~0,7 %  | +123,85 h (FIGHT 01-30: prod 02-01 00:10, sim 02-06 04:01) | 0 | 1 cum / 1 leg (SPACE 01-30) |
| 2026Q2 | 2 / 2 / ~3,8 % (uoc: trung vi margin leg DCA/E = 1,89 %) | sim KHONG BAO GIO DCA: SLX 06-02 (prod 06-06 01:53), OPN 06-06 (prod 06-09 09:20) | 0 | 1 cum / 2 leg (GUA 06-25) |
| 2026Q3 | 0 | - | 0 | 1 cum / 2 leg (AIN 09-16) |
Phut (theo legCount sim): (i) Q1 81, Q2 17; (ii) 0; trung 6. Quy theo leg0 cua cum. SLX/OPN: tier sim chot 02-06 04:00 => symbol
niem yet / chua co mat luc do => UNKNOWN -> T3 suot quy; production thay T1/T2.

## (d) Moi cho doc tier (ngoai cac tool offline: export / hpo / wfo / validation - chi goi getTopCoin / resetCache)
| file:dong (sim a8690d46)                         | dung de                 | anh huong voi HO5 (TIER_FLAT=1, DCA_ROUND_CAP off, WFO_STATIC_RANK off) |
| SimulatorMarketLevelTicker1MStopLoss:1431-1436   | getCoinTier: T3 chan DCA_LEVEL1 | CO (chi DCA; PREDICT/BIG_DOWN di qua) + la NOI DUY NHAT cap nhat tier |
| SimulatorMarketLevelTicker1MStopLoss:1455        | getBudgetMultiplier x budget | KHONG (TIER_FLAT => 1,0) |
| DcaProcessor:147 tierMultiplierOf (capByDrop)    | tran DCA moi luot       | KHONG (DCA_ROUND_CAP off; TIER_FLAT => 1,0) |
| CoinRankManager:117 getMultiplierByTier          | he so 1,2/1,0/0,5       | KHONG (TIER_FLAT=1 ca prof_run HO5 va env 242) |
| Universe top-50 % (getTopCoin)                   | tap coin du doan        | sim: bin du doan offline (RunGeneratePredictions:81 goi getTopCoin MOI phut) - khong qua tier sim |
| file:dong (jar 76134a52)                         |                          | |
| LiveFeaturePipeline:206 getTopCoin(minute)       | nuoi rank moi phut => tier moi gio | (nguon tier "dung") |
| DetectEntrySignal2TradeNormal:1436 / 1439-1443   | tierMultiplier; getCoinTier T3 chan DCA_LEVEL1 | 1436 KHONG (=1); 1439 CO (chi DCA) |
| C3LiveHook:107 / :109 peekCoinTier               | tierMul, tier3 -> LegInput | :107 KHONG (=1); :109 CO (chi DCA) |
| C3LiveEntry:243 TIER3_DCA / :268 b*tierMultiplier | chan DCA / size        | :243 CO (chi DCA); :268 KHONG (=1) |
| DetectEntrySignal2TradeNormal:1012 getTopCoin(time) | basket                | gio hoa, khong doc tier T3 |
| CrashDayRig:911 (harness)                        | tierMul=1, tier3=false  | rig KHONG mo phong chan T3 |
=> tier KHONG anh huong lenh VAO (PREDICT / BIG_DOWN), size, thoat, BIG_DOWN voi cau hinh HO5; CHI chan leg DCA. Khong can dem (c) cho
lenh vao.

## (e) Cum DCA OW1 (GUA, leg0 06-25 20:53; DCA 07-01 08:12 va 07-02 20:37)
Ca 2 leg: tier cu (moc 02-06 04:00) = KHONG T3, tier dung theo gio = KHONG T3 => tier KHONG quyet dinh thoi diem; thoi diem do gia cham bac
+ thi truong + gate (phut du dieu kien dau tien cua moi bac = dung phut leg sim). Production tier dung cho cung 2 leg cung phut.

## Gioi han
- E chi gom phan da dong (khong MTM) khi xet U < 0,6 va % von; % von leg (i) Q2 la UOC (sim khong co leg do): trung vi margin leg DCA / E.
- Duong production gia dinh cum giu den dung phut dong cua sim (DCA them se doi gia TB / thoat - khong mo phong); DCA leg 2+ cua prod sau
  leg them khong xet cho SLX/OPN (chi 1 leg / cum du dieu kien trong khoang giu).
- PumpDumpFilter / burstCooldown / TickWeakBlock khong mo phong (chi lam GIAM ung vien).
- Xep hang dung tap symbol CO MAT trong ticker cua phut (sim: HistoryManager.getAllSymbolsShort - symbol da huy niem yet van con lich su
  cu) => bien T3 co the lech vai symbol; A1 nen kiem.
- SU CO RANG BUOC: file ticker theo ngay UTC => ticker_20260930 chua 2026-10-01 00:00..06:59 +07; Add24TierAll DA DOC 7 gio do vao bo nho
  (file tho da xoa). Dau ra da CAT bo moi dong > 09-30 23:59 +07 (4 669 dong tier) truoc moi phan tich; khong so lieu nao >= 10-01 +07 duoc dung.
