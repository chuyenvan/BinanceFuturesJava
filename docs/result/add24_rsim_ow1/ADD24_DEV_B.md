# ADD24 R-SIM - bao cao DEV-B (2026-11-22, ASCII) - prereg 6ee84f17 (muc 15 MASTER thang)
Trang thai: buoc 1-4 XONG tren cua so DEV; DUNG tai STOP-A24-B (KHONG chay OW1, khong mo/dem/cham output rig OW1).
Khong in PnL/ROI/DD/win-rate. Errata de xuat: ~/claude_master/w3/add24/ERRATA_PROPOSED_B.md (EB1..EB12) - MASTER commit TRUOC OW1.

## 1. Cong thuc von size sim (EB1, da xac minh)
Sim jar cc0f9d11 = code a8690d46. SimulatorMarketLevelTicker1MStopLoss.createOrder:
  balanceBasic = sizingEquity() = Configs.FIX_B3 ? BudgetManagerSimple.equityNow() : balanceBasic   (FIX_B3=true)
  budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, lvl) = E*F_BASE*clamp(1-U/U_MAX)/dcaGridTotalWeight
  budget *= tier(1) ; budget *= DcaUtils.gridLegWeightRatio(legIdx) (FIX_B2: w*SCALE=6) ; qty = calQuantityTest (floor stepSize)
BudgetManagerSimple.equityNow() = balanceCurrent + unProfit ; updateBalance() moi gio (time%60'==0, sau khoi vao lenh cua tick):
  balanceCurrent = 35000 + sum calTp(cum da dong) ; unProfit = sum cum mo qty*(lastPrice - entry), lastPrice = close nen 1m tai H.
=> E_sim = MTM tai moc gio H gan nhat truoc t ; U_sim = margin dang mo (+ leg sim truoc trong cung phut: BIG_DOWN roi PREDICT theo rank) / E_sim.
Leg0 = 0.0225*E*(1-U/0.6). Kiem 16/16 phut vao lenh DEV: |E suy nguoc / E tai lap - 1| <= 1.2e-5.

## 2. Dau vao rig + ket luan S-G
sel.csv.gz (ts,symbol,selectorScore,rank,gateValue,p15): gateValue = THEO SYMBOL (sp = 1 - p0 bins A3 2026, ffill 15'->phut, stale<=15',
sort = port quickSortByFloatPred, top-24), p15 = THEO THI TRUONG (pred_2026.bin). 97/97 lenh PREDICT DEV trung bit symbolPred/pred15m
cua printDone => S-G LAM DUOC (khong INSUFFICIENT vi dau vao). Buffer gate: warm-up = ung vien sim khong giu + co nen [W0,START):
tai lap 2026Q1 = 2 938 973 vs sim log 2 938 970 (+3). "Theo vet" = tap LEGACY dong (EB3). Launcher: add24/b/jsrc (Add24RsimMain,
Add24BufWrite, Add24TsxInject, Add24SszProbe) bien dich javac vao add24/b/classes (stub + test-classes DEV-A d6c631cd), chay bwrap
--unshare-net, LIVE_IS_SHADOW_HOST=true, LIVE_ADAPTER=dry, FAKE, C3_CAPITAL=10000, env whitelist 11-16 (md5 8956befd...) + override (EB4).

## 3. Du lieu (tmpfs /dev/shm/add24/b, 408 MB; moi ts <= 2026-09-30 23:59 +07, assert tu dong)
- Doc tai cho (khong Kaggle): w3/ho5/a3/data26/ds predict_wf_20260101.bin sha b58099f4..., _20260401 sha 78e4e437..., _20260701 sha
  9a914693... (chi OW1), pred_2026.bin md5 64f66a15 (ts_max 1790787540000 = 09-30 23:59 +07); printDone s123 md5 b8a77a46
  sha c5693122...; mapper ov_idtostr.tsv; exchangeInfo_20261027_1140.json.gz md5 115dd8e5; ho_flags.json sha ecaced06.
- Vision UM 1m (zip sha256 == .CHECKSUM, loc truoc khi ghi): kl/ 90 symbol printDone (DEV+OW1, [start-2h,end+2h]) 471 753 dong,
  ts 1779054060000..1789034460000; cand_bars DEV (ung vien khong giu, 390 symbol, 1 144 phut khong co nen/phang) ; BTCUSDT ref
  2026-04-01..06-30 129 600 dong. Chi tiet md5: add24/b/dev_results/{kl_manifest,avail_manifest,ref_manifest,manifest_conv,fx_check}.json
- fx_dev md5: sel b8a04e96, klines 3d929016, warm d0abea1d, exinfo(patched) d7061f4f, follow 62aa0588, bigdown 28391777, cand ccaa782d.

## 4. Ket qua cua so DEV (lenh sim start 04-01..06-15: 101 cum = 97 PREDICT + 4 BIG_DOWN, 14 phut PREDICT; luot DEV3)
Cong V1 V2 V3 V5 V6 = OK (108 000 phut xu ly == 108 000 phut sel; 0 exception; KS khong latch; env thieu = rong). V7: REF numpy S-SZ
khong import Java.
- S-G: jar PASS 97/97 (0 fail) ; 14 phut < 50 => INSUFFICIENT (mau DEV). Jar PASS ung vien sim KHONG vao: 25 (13 phut, 8 phut khong co lenh sim).
  (DEV2 truoc patch SETTLING: 83/97 - day chuyen buffer, EB7.)
- S-SZ (goi LiveGridSizing.legBudget(TradeUtils.managerBudget(...),0) cua stub; F_BASE 0.015 U_MAX 0.6 SCALE 6 ratio0 6): 101 cum,
  max 4.99e-3, p90 3.9e-4, 95.0 % <= 1e-3, 100 % <= 5e-3 => PASS (sat 5e-3 do floor stepSize, EB2); chi so lam tron (EB2): max 9.5e-5.
- S-X: rig vao 98/101 (3 NOT_BUYABLE DELIVERY_SOON, EB8); (a) ly do 98/98 trung (87 TRAIL, 11 TIME_STOP gom 4 X14 190.6h);
  (b) cung phut 80/98 = 81.6 % (11 cum -1', 2 cum +1', 5 cum >1': -203,-23,+17,+9,+3) => DEV KHONG DAT 95 %;
  (c) TB Delta gia thoat -0.65 % (trong [-0.8;0]); 6 cum < -1.5 % (TA -12.87, CLOU -12.52, SKYAI -3.14, US -2.89, ALLO -2.85/-2.02).
  Time-stop: 11/11 cung phut, TB +0.18 %. Trail: TB -0.75 %. Nguyen nhan: gia vao rig != sim + nhip trong nen/khop stop FakeExchange (EB11).
- S-D: 0 cum DCA sim => INSUFFICIENT (phu C0b S-DCA, DEV-A PASS). Rig khong co mkt toan thi truong (EB5).
- S-E: 98 cum, TB +0.41 bps, p90 |.| 8.9 bps. S-SEL: khong lam.

## 5. Lenh chay chinh thuc OW1 (1 lan, co khoa; CHI sau A1 duyet harness + MASTER commit errata)
  nohup ~/claude_master/w3/add24/b/run_official_rsim.sh <A1_REF> <ERRATA_COMMIT> [--patch-settling] [--allow-no-mkt] &
  (khoa ~/claude_master/w3/add24/b/OFFICIAL_ADD24_RSIM.lock + .done; tu kiem df>=15300M, MemAvailable>=10000M, md5 stub; DUNG neu OW1 co
  cum DCA ma khong --allow-no-mkt; ket qua -> add24/b/official_ow1/ (score.json, gates.json, result_noPnL.json, SHA256SUMS). Thoi gian
  uoc: conv ~2', tai availability ~15-20', build ~3', rig ~2-4', score ~1'.)

## 6. Rui ro lich
(1) EB11: S-X(b)(c) co the FAIL o OW1 vi quy uoc rig (gia vao + nhip/khop stop), khong do jar -> MASTER quyet errata truoc OW1.
(2) EB5: neu OW1 co cum DCA -> can mkt toan thi truong Q3 (~1-1,5 GB tmpfs, +~1h) hoac S-D INSUFFICIENT.
(3) EB8: guard DELIVERY_SOON cua jar (lech that) can nhan/xu ly. (4) X14 khong kich duoc trong OW1 (khong ngay TS_EXT 07-09).
(5) Harness launcher dung reflection (legacy set, defer X14, buffer bulkAdd) - A1 phai duyet; neu A1 doi DEV-A dua vao harness: +2-3h.

## 7. File (code add24/b; sha256 o duoi)
  a35cf9399913858dbf56917e02314fb14da70d3d7508123ba309769ad0c6e01b  conv_rsim.py
  da08e5d2ad99bc2ecf2cb2c0775da467453d9cfb43abc2ccbca32ec45538ed4a  check_conv.py
  89d28328f3e11912cc18d8ec6b6a48f34e451c9f9c2edcf5b4e057581ca4010d  dl_klines.py
  7eef9cf653c00723f04ed710db7bae53190b4a13b9fd56f080add5f6132ca6b6  dl_avail.py
  d376771f2b3ee59376089c3a3a1b7299fdd274bf5f596c9173b45e3c0856929d  dl_ref.py
  e793e0f9676e918d692b80386bacc64d0d56ccaddaf332f7efd776efa246600f  build_fx.py
  226d78d744c8d303d751f2e944a893118139d5beb1c94bffc727d864a4e78e06  ssz_inputs.py
  f8d1820251c464749aed6aa64635bca9f612906cf7765136ff5a60cbc6c7bb84  esim_check.py
  65d9bd2b5b256c456a6f6e9afc47e402381ca4df5bbae2f2f9587f49ae08ccca  esim_check2.py
  5265184e7f1b556015b98545b0fb801343c92a0668ca1ebe49b80b9259296f3f  esim_mtm.py
  e983aa1f26c4e6cc900a650c24c81b8b5d36ef334bd91e87a27a729f06774614  score_rsim.py
  073937676695ca8e25eae68d646ff182e0f6b0466855a43d5255fddcf61751f7  gates_rsim.py
  1f928264f8c0b2bce410e6f3405177997483975f2769a0cb942b13f18728e1b5  run_rsim.sh
  4f1b107cb2ab7ad8efdbcb0d380c8230869a01bef1e59d7fee25c19fbb020d54  run_ssz.sh
  3357c59d0a00d9fe64884613a8c88e051390c8e62339cce2d8fa998bfac1b1f6  run_official_rsim.sh
  0ecaddfbb58a850e8303a342587db93fa2f3d9779de03da35f680284fcc79c86  jsrc/com/binance/chuyennd/tradecore/selector/Add24TsxInject.java
  98f41cdd9052688b102dc01fc3732a9a47a323524693af9b702aa1eb58ff4252  jsrc/com/binance/chuyennd/ai_ml/onnx/entry/Add24BufWrite.java
  a8efb0cd3fb9e3b3de0685941f026857155b9e1499fa671cfccf73acd8745ee0  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24RsimMain.java
  2e3d2f52642cf0db3cdcbc92c619aa119b42ef258850f4e55059c90965e8c9f7  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24SszProbe.java
  7a3de363811472ee38bc11b677b7dcd80915c2474f1ee83d467f96fdb4508edf  ../ERRATA_PROPOSED_B.md

# LUOT 2 (ERRATA1 29152e39) - 2026-11-22 ~12:50 - DUNG tai STOP-A24-B (KHONG chay OW1)
Ap: entry-follow EB11 buoc 1 (o.followPx cid c3-SYM-<phut>-0 -> gia vao sim), N10 PROD_GUARD (legs.csv NOT_BUYABLE + ly do jar),
S-SZ chinh = EB2 (lam tron stepSize) + bao chi so goc, V9 (fed theo quy vs log sim), cum DCA = nhom (sym,end) > 1 dong (EB13).
Launcher: add24/b/LAUNCHER_NOTES.md (L1-L7). Classifier S-X doc lap: add24/b/classify_sx.py (REF-sim theo nen + REF-nhip 4 moc/nen).
## DEV4 (cua so DEV, 101 leg = 101 cum 1 leg): V1 V2 V3 V5 V6 V9 OK (V9 2026Q1 2938973/2938970 = 1+1.0e-6)
- S-G 97/97 PASS tai phut sim (14 phut < 50 => INSUFFICIENT mau); 25 PASS ung vien sim khong vao (13 phut).
- N10 = 3 (D, HIGH x2 DELIVERY_SOON) = 3.1 % lenh PREDICT.
- S-SZ (EB2, n 98): max 9.5e-5, 100 % <= 1e-3 => PASS ; goc: max 4.99e-3, 94.9 % <= 1e-3.
- S-E: 0 bps (follow). S-X (98 cum): (a) 98/98 ; (b) cung phut 87/98 = 88.8 % (9 cum -1', 2 cum >1': -42', -4') => < 95 % ;
  (c) TB -0.58 % ; 5 cum < -1.5 %. Phan loai 15 cum lech (b)/(c): K8_INTRABAR 10 (REF-nhip trung phut rig 10/10, REF-sim trung phut sim
  10/10; gom CLOU -42' -10.55 %), FILL_MODEL 4 (cung phut; rig khop tai moc L cua nen 2.0-12.9 % duoi SL trong khi open > SL; sim chot
  min(SL, open) = SL), TICK_SNAPSHOT 1 (VELVET -4', tick 0.0001 pin sim vs 0.00001 exInfo 1027). OTHER (lech logic that) = 0.
  REF-sim tai lap phut+gia thoat sim 86/87 cum trail (cum con lai = VELVET tick).
## DEV-2 (S-D; cum DCA FIGHT/SPACE: leg0 PREDICT 01-30 08:43, DCA 02-06 04:01/04:19; mkt toan thi truong 01-31 21:30..02-06 05:00:
847 symbol / 625 co du lieu / 4 775 476 dong, 101 s tai; buffer warm chi 29 ngay => S-G DEV-2 khong co y nghia)
- S-D: SPACE DCA dung phut 02-06 04:19 legIdx 1 (OK); FIGHT: rig DCA 02-01 00:10 (som 5 ngay) vi MarketReplay (Vision, 543 symbol)
  cho dcaAlt=1 tu 02-01 00:10 khi gia FIGHT da <= -50 % tu 01-31 22:44; sim (market.bin) DCA 02-06 04:01 => UNG VIEN LECH (nguon dieu
  kien thi truong live-vs-sim), can market.bin HO5 de phan xu => S-D DEV-2 = FAIL 1/2 (chua phan xu).
- S-SZ DEV-2: lech -2.7..-8.8 % CHI o 25 leg 02-01 00:11..01:43 (REF numpy cung lech nhu jar => cong thuc E_sim tai lap sai o doan nay,
  khong phai jar); cac phut khac <= 1.1e-3.
## Mau OW1 (dem printDone): 81 leg / 80 cum; 67 leg PREDICT trong 16 phut (S-G INSUFFICIENT chac chan theo nguong 50 phut); 12 BIG_DOWN;
  1 cum DCA (leg0 06-25 truoc cua so, 2 leg DCA 07-01/07-02) loai + dem; exit: 67 STOP_MARKET (trail) + 13 STOP_LOSS (12 >=168h).
## Lenh chinh thuc (cap nhat): nohup ~/claude_master/w3/add24/b/run_official_rsim.sh <A1_REF> 29152e39[,<ERRATA2>] &
  fe7fd8e63ffa4021509c4c909e713d9f2533dbafec59517bca08ff00e8f91b74  conv_rsim.py
  94c81ad40678cea5f58d86fd922de3dd7dd8bed5f8a581df5f387092d176a11d  build_fx.py
  86d1ffbf439281400f4767521c75a45458d3851e3cbc92a0758d0c10e22347a4  ssz_inputs.py
  a957f7f12ab2db03f0c2a155fac0bdececbde94b690a18f6af992046d95207dc  score_rsim.py
  3bcecb165fb5410a232347bddfdb788781033c481f3b55bfcd6870acfe0ed2cb  gates_rsim.py
  b0d4284d9699736c81a78ac2c4b8ef523f8f3db493d89734b73a436aa689f95e  classify_sx.py
  9636eb08b18387810b0904ba034c0a0324bc65ed7b4cd2c7d0fbc2dbd5418e3d  dl_mkt.py
  85b602c675b6840e0d16cb3750eb2c632e99adc7194fcab93fa9409c582b39ad  dl_klines.py
  7eef9cf653c00723f04ed710db7bae53190b4a13b9fd56f080add5f6132ca6b6  dl_avail.py
  d376771f2b3ee59376089c3a3a1b7299fdd274bf5f596c9173b45e3c0856929d  dl_ref.py
  1f928264f8c0b2bce410e6f3405177997483975f2769a0cb942b13f18728e1b5  run_rsim.sh
  4f1b107cb2ab7ad8efdbcb0d380c8230869a01bef1e59d7fee25c19fbb020d54  run_ssz.sh
  abc5ff5c733c67c8b1ac37f19d7f099e19b96b2f37e34ea0b59ffc2986db6b6e  run_official_rsim.sh
  0c2805476cc467665082fa170a126e20ef3b37ac0fd0212f7257058701a0ed0b  dev2_run.sh
  a23b0f7618f8f09905f328ec5846e715c0d511f90f2bfb8f8eff6aa5e9f87c26  LAUNCHER_NOTES.md
  19e80544497b4c6967fbb7fb82f2de5f431058b37f1659384d9c0abc3e47bf9c  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24RsimMain.java
  98f41cdd9052688b102dc01fc3732a9a47a323524693af9b702aa1eb58ff4252  jsrc/com/binance/chuyennd/ai_ml/onnx/entry/Add24BufWrite.java
  189f2ccde916478ad78e950b1cd4e89f8aea0bb6ccf4688a385ae856942142e9  ../ERRATA_PROPOSED_B.md

# LUOT 3 (ERRATA2 bb91e639) - 2026-11-22 ~14:45 - DUNG tai STOP-A24-B (KHONG chay OW1; ERRATA2 3b dang CHAN)
Ap: L8 duong gia trong nen 2 lane (doi chuoi Bar.s H/L trong launcher), L9 khop stop min(SL,open) (SL dat trong nen khop => SL) o scorer,
L10 bo loc pin sim (md5 5a815948 = dataset sim-x1-2021-bundle; 23 symbol khac 20261027), L11 S-G2 ca quy (sel/follow het quy), S-SZ leg0 moi cum,
--end_pad (V6). Chi tiet: add24/b/LAUNCHER_NOTES.md (L1-L11, P1), ERRATA_PROPOSED_B.md EB17-EB22.
## DEV5b (lane CHINH) - V1 V2 V3 V5 V6 V9 OK (131 040/131 040 phut; V9 Q1 1+1.0e-6)
S-G 97/97 (14 phut, 97 quyet dinh < 50 => INSUFFICIENT mau DEV) | S-G2 Q2: tho FAIL 147/122, seen +1.4e-3; loai N10-cascade PASS 122==122,
seen -1.2e-5 | N10 3 (3.1 %) | S-SZ (EB2) max 9.5e-5 PASS (goc max 4.99e-3) | S-E 0 | S-X (a) 98/98, (b) 92/98 cung phut + 6 K8/N8 (-1'),
(c) TB +0.078 %, 0 cum < -1.5 % | S-D 0 su kien.
## Lane DO NHAY: 41/98 doi phut thoat; Delta gia sens-chinh TB -0.91 %, p05 -9.09 %, min -12.18 %.
## 3b FIGHT: CHAN (EB20). 3c: chua tim ra (EB21).
## Lenh chinh thuc (CHUA chay; chi sau khi 3b duoc go): nohup ~/claude_master/w3/add24/b/run_official_rsim.sh <A1_REF> 29152e39,bb91e639 &
  Uoc tinh ~40-50 phut (tai availability Q2-Q3 ~15-20', 2 lane x ~4'), tmpfs them ~0.7 GB.
  fe7fd8e63ffa4021509c4c909e713d9f2533dbafec59517bca08ff00e8f91b74  conv_rsim.py
  a779dbff6ba14b736d079a07866598324db3d1bc22ebd4856d0494a4892cd4f6  build_fx.py
  86d1ffbf439281400f4767521c75a45458d3851e3cbc92a0758d0c10e22347a4  ssz_inputs.py
  ce30d40a09b6a4fede64a695b66810b6043e6bab6c4bc87088cc4a64deec824b  score_rsim.py
  3bcecb165fb5410a232347bddfdb788781033c481f3b55bfcd6870acfe0ed2cb  gates_rsim.py
  ac03c8687c8fcb7d90ca6d09dc18db59b180b5b24db025cb4fa90dd9c46349d4  classify_sx.py
  f04575443aa6e5ccbb8c10affb7d4bf998c9ff75c34f1973142d441b1fee8feb  lane_diff.py
  9636eb08b18387810b0904ba034c0a0324bc65ed7b4cd2c7d0fbc2dbd5418e3d  dl_mkt.py
  85b602c675b6840e0d16cb3750eb2c632e99adc7194fcab93fa9409c582b39ad  dl_klines.py
  7eef9cf653c00723f04ed710db7bae53190b4a13b9fd56f080add5f6132ca6b6  dl_avail.py
  d376771f2b3ee59376089c3a3a1b7299fdd274bf5f596c9173b45e3c0856929d  dl_ref.py
  aa16da1cc63bb56444b642f64dc00f9df1e8325a150251f1d4eb988686e7fa27  fight_tier.py
  8a2b193f201a1af43411a474df07ce69925d475a1466ab871e817f03693134b1  run_rsim.sh
  4f1b107cb2ab7ad8efdbcb0d380c8230869a01bef1e59d7fee25c19fbb020d54  run_ssz.sh
  66e3bae7036a52ab3771626e3c7b0faeba5afad1bb1f6243c805d97b53f8fe26  run_dcaprobe.sh
  8a6f97c4168920f94315abcde76549ea764f6b3d8ecc35aa77ff7ef815213508  run_official_rsim.sh
  e7e99f5ae19eeeca43bc4916e1479eac809b5d89a706d74ea37b3a2aa2364856  dev5_run.sh
  0c2805476cc467665082fa170a126e20ef3b37ac0fd0212f7257058701a0ed0b  dev2_run.sh
  a387e44ea922b4cde2c388691daef52b38230f0ab1d2076b2610c2a6d61dc5e9  LAUNCHER_NOTES.md
  099e7a87a3693b672e72a6357332b0043fd54a28ce4f133e70c214edc1005667  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24RsimMain.java
  daa50ab0a056cb47245ac3f02760156d4149540224d4fd9fc9fad8ba3916f8ab  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24DcaProbe.java
  2e3d2f52642cf0db3cdcbc92c619aa119b42ef258850f4e55059c90965e8c9f7  jsrc/com/binance/chuyennd/c3live/e2e/replay/Add24SszProbe.java
  98f41cdd9052688b102dc01fc3732a9a47a323524693af9b702aa1eb58ff4252  jsrc/com/binance/chuyennd/ai_ml/onnx/entry/Add24BufWrite.java
  0ecaddfbb58a850e8303a342587db93fa2f3d9779de03da35f680284fcc79c86  jsrc/com/binance/chuyennd/tradecore/selector/Add24TsxInject.java
  882958bfc4145013fe0ebddb8f41cee0d0ffb5c550c523e5b1ee8e0c4ac1e6e6  ../ERRATA_PROPOSED_B.md

# LUOT 4 (ERRATA3 050912ca) - 2026-11-22 ~15:00 - DUNG: B5 KET LUAN (2) (xem ERRATA_PROPOSED_B.md muc LUOT 4)
- B5: sim chan DCA FIGHT do TIER_3 "cu" (CoinRankManager cap nhat lazy chi khi createOrder goi dung phut :00; moc 01-19 07:00 -> 02-06 04:00,
  FIGHT niem yet 01-23 => UNKNOWN->TIER_3). Production cap nhat moi gio (LiveFeaturePipeline) => FIGHT T1 => DCA 02-01 00:10 nhu rig.
  Du lieu dung: market.bin sim (trich <=02-06, md5 goc 0fcc44d8), ticker sim tk26 01-23..02-06 (15 file, md5 khop), probe Add24TierProbe /
  Add24DcaProbe (ham jar stub, bwrap). Kaggle: chi TAI (API list_kernel_session_output, loc 15 file), khong push.
- DEV6 (B1-B4) CHUA chay vi B5 (2) => DUNG theo chi dan. Da chuan bi: N10-held se lam bang bo nen symbol N10 trong khoang sim giu (ticker null
  => SKIP_AFTER_RANK nhu sim giu), 2 luot (luot 1 xac dinh N10 bang quyet dinh jar). Chua code B1/B2 verdict, N11.

# LUOT 5 (MASTER: dinh luong tier cu + DEV6) - 2026-11-22 ~17:00 - DUNG, KHONG chay OW1
- Chi tiet: w3/add24/b/dev_results/TIER_IMPACT.md (bang a-e) + tier_impact.json. Script: l5_prep.py, l5_tier.py, run_tierall.sh,
  run_dcaall.sh, jsrc Add24TierAll.java / Add24DcaAll.java (ham jar stub, bwrap --unshare-net).
- (a) Moc cap nhat tier sim 2026: CHI 2 (01-19 07:00, 02-06 04:00); truoc do 2025-10-12 03:00 (cach 99,17 ngay). Day du vi 319 gate pass
  PREDICT = 319 leg; 1 phut BIG_DOWN :00; 0 ung vien DCA :00. Do cu tai leg PREDICT: TB 110,7 / trung vi 118,2 / max 229,7 ngay.
- (c) (i) sim chan / prod DCA: Q1 1 cum 1 leg ~0,7 % von (FIGHT som 123,85 h); Q2 2 cum 2 leg ~3,8 % von uoc (SLX 06-02, OPN 06-06 - sim
  khong bao gio DCA); Q3 0. (ii) = 0 moi quy. Trung: SPACE (Q1), GUA (2 leg), AIN (2 leg). Mo hinh tai tao 6/6 leg DCA sim.
- (d) tier chi chan DCA (sim 1431, jar DetectEntry 1439 + C3LiveHook 109 / C3LiveEntry 243); he so size = 1 (TIER_FLAT=1 ca 2 phia);
  khong anh huong vao / size / thoat / BIG_DOWN.
- (e) GUA (OW1): tier cu = tier dung = khong T3 tai ca 2 leg => tier KHONG quyet dinh thoi diem.
- DEV6 (B1-B4, lane sim, Q2): N10 3 (DUSDT, HIGHUSDT x2 DELIVERY_SOON) -> xoa 4 237 nen trong khoang sim giu; S-G2 THO 122/122, seen
  -1,2e-5 PASS; S-X(b) (92 + 6 N8 REF) / 98 = 100 %, N8 6,1 %, khac 0 PASS; S-X(c) TB +0,078 % PASS, cum vuot 0; S-SZ max 9,5e-5, N11 0
  PASS; S-E 0 bps; S-G 97/97 (INSUFFICIENT mau DEV); S-D INSUFFICIENT (0 su kien); V gate 7/7 ok. dev_results/DEV6_sim/.
- run_official_rsim.sh: errata bat buoc 29152e39,bb91e639,050912ca; luot 1 OW1_p1 -> n10_held.py -> 2 lane tren FX_n10 + verdict_e3.py.
- SU CO: ticker_20260930 (ngay UTC) chua 10-01 00:00-06:59 +07 - Add24TierAll da doc vao bo nho; dau ra da cat > 09-30 23:59 +07.

# LUOT 6 (ERRATA4 03bb65e0) - 2026-11-22 ~17:10 - DUNG, KHONG chay OW1
- 1a TIER LUOI vao rig: L12 (LAUNCHER_NOTES) - boc reconAllows + Proxy gridDue cua instance C3LiveEntry, ADD24_SIMTIER =
  l6_inputs/simtier_code.csv (Add24SimTierCode: code a8690d46 CoinRankManager/HistoryManager/SimpleSymbolMapper bien dich vao simcls/,
  mapper ov_idtostr.tsv, ticker sim 01-18..01-19 [tai lai 2 file, md5 ref_ok] + tk26 01-23..02-05; moc 01-19 07:00 / 02-06 04:00).
  Port LUOT5 == code: 0 khac tier (541 / 547 symbol). DEV-2 (DEV2T, lane sim): S-D 2/2 PASS (FIGHT 02-06 04:01 legIdx 1, SPACE 02-06
  04:19 legIdx 1); 83 lan chan FIGHT. (DEV-2 S-SZ van FAIL nhu DEV2W - 3c: 21 leg N11 o 2 phut 01-31 + 4 leg BIG_DOWN khong giai thich.)
- 1b V-TIER: vtier.py (l6_inputs) -> score_rsim.py --vtier. Thu: DEV Q2 TIER_DIV 17 phut / 2 cum (SLX, OPN) -> loai; DEV-2 81 / 1 (FIGHT);
  OW1 (chi du lieu sim) 0 (2 phut du dieu kien, cum GUA, tier giong nhau).
- 1d: khong symbol id >= 1000 (mapper max 900; printDone 2026 max 862; bin ung vien 2026 max 863; 8 symbol ticker 2026 ngoai mapper ->
  sim cap 901..908). Sim HistoryManager: MAX_COINS 1000 bo im lang, tap = symbol co mat trong tick (updateHistoryArray), zombie 4h/24h;
  production: SymbolIdLimits.CAPACITY + log ERROR khi vuot, bo symbol isQuarantined (id trung) - con lai giong.
- DEV7 (= DEV6 + L12): giong DEV6 tung byte (legs/fills/trace_dec), gridDue goi 0 lan (Q2 khong co mkt toan san -> rig khong DCA).
  Voi V-TIER: S-X n 96 (bo SLX/OPN), cung phut 90 + N8 6, TB +0,068 %; S-SZ n 96 PASS; S-G2 122/122.
- TAI LAP TIER_IMPACT (cho A1): `~/claude_master/w3/add24/b/repro_tier_impact.sh` (dau vao /dev/shm/add24/b/l5: tier_hourly 51d66b3f,
  closes 16fc5890, market26.npy d56cf089; ra "TIER_IMPACT tai lap TRUNG" - da chay 17:0x).
- Chinh thuc: `~/claude_master/w3/add24/b/run_official_rsim.sh <A1_REF> 29152e39,bb91e639,050912ca,03bb65e0` -> official_ow1/RESULT_E4.json.

# LUOT 7 - 2026-11-22 ~18:00 - DUNG, KHONG chay OW1
- 3c / EB27 KET LUAN (1): cong thuc tai lap S-SZ cua DEV-B sai 2 diem (EB28 vi the huy niem yet giu margin 2 ngay; EB29 thu tu BIG_DOWN =
  HashSet<Short>). Sau sua (ssz_inputs_l7.py): DEV-2 S-SZ EB2 max 7,7e-5 PASS (truoc 8,7e-2 FAIL), 0 N11, 0 leg khong giai thich;
  DEV (DEV7) ssz_in khong doi 1 dong, S-SZ PASS. Gia MTM: ticker sim (tk26) = Vision cho moi vi the mo (lech 0) - khong phai nguon.
- Phat hien phu (EB30): production duyet leg BIG_DOWN theo HashSet<String>, sim theo HashSet<Short> -> size tung leg khac khi >= 2 leg/tick.
- S-X DEV-2: 9 N8 deu K8_INTRABAR (REF-nhip = phut rig, REF-sim = phut sim, -1'), Delta +0,77..+8,82 %, 01-30..02-06 (gom sap 01-31/02-01);
  TB khong N8 +0,0034 %; 2 dong OTHER = cum DCA SPACE (ngoai S-X). Khong cum lech nao thieu co che.
- EB25 mkt: OW1 can 8 ngay UTC 09-15..09-22 (~ 8 x 1 trieu dong, ~110 MB gz, ~4 phut tai); thu Q2 9 ngay = 9,4 trieu dong 123 MB 264 s.
  OOM truoc do vi manifest mkt.from = START (bo nho = n_sym x 5 x (END - from)); sua: build_fx --mkt. DEV7M4: gridDue 17 lan = 17 TIER_DIV,
  ca 17 bi tier luoi chan -> rig 0 DCA = sim. DEV7M5: span 16 ngay (= OW1) chay Xmx3g OK.
- run_official_rsim.sh: + buoc mkt (EB25), ssz_inputs_l7.py, S-D rig_extra. Lenh: run_official_rsim.sh <A1_REF> 29152e39,bb91e639,050912ca,03bb65e0

# LUOT 8 (ERRATA5 0740e790) - 2026-11-22 ~19:40 - DUNG, KHONG chay OW1 (A1 duyet delta)
| # | Sua | file:dong | Test |
|---|---|---|---|
| R1 | S-G: mau >= 50 quyet dinh VA >= 10 phut; lenh PREDICT sim bi jar REJECT => FAIL truoc khi xet mau | score_rsim.py S-G (dong "sample_ok"/status); verdict_rsim.py S-G | tiem (a) -> FAIL |
| R2 | S-SZ: lech (> 5e-3 / ti le <= 1e-3 < 90 %) hoac leg khong stepSize => FAIL truoc mau; N11 khong che INSUFFICIENT (N11 > 2 phut => INSUFFICIENT); m2 dem no_stepsize | score_rsim.py S-SZ status; verdict_rsim.py S-SZ | tiem (c) -> FAIL |
| R3 | S-X mau >= 30 thoat, >= 1 time-stop, >= 1 trail (thieu => INSUFFICIENT chi khi 0 lech) | verdict_rsim.py S-X | DEV8 30/9/87 |
| R4 | S-X(a) ly do thoat = trang thai rieng | verdict_rsim.py a_reason | tiem (d) -> FAIL |
| R5 | MOI cum sim trong cua so co trang thai SCORED / N10 / DCA_CUM / NO_EXIT_SAU_END; con lai MISSING => FAIL | verdict_rsim.py states | tiem (e) -> FAIL; (b) phut +3' -> FAIL |
| R6 | S-D: rig_extra => FAIL; 0 su kien hai phia => INSUFFICIENT_CO_PHU (khong PASS) | score_rsim.py S-D; verdict_rsim.py S-D | tiem (f) -> FAIL |
| R7 | verdict_rsim.py: HUY > FAIL > INSUFFICIENT > PASS_CAN_OWNER; N10 > 5 % => CAN_OWNER; co SIM_TIER_STALE + BD_ORDER luon bat; test_inject.py | verdict_rsim.py, test_inject.py | (a)-(f) FAIL, (g) = goc |
| m1 | cong lap dat L3 + L12: rig_t <= START, khong => HUY | verdict_rsim.py INSTALL | DEV7/DEV8/DEV2T rig_t = START |
| m3 | L9 mo rong ghi LAUNCHER_NOTES (LUOT 8) | LAUNCHER_NOTES.md | - |
- DEV8 (fx_dev6 + mkt loc SLX/OPN 06-05..06-12, span toi END 07-01 ~25 ngay, Xmx3g OK): RESULT PASS_CAN_OWNER; S-G 97 qd / 14 phut PASS;
  S-G2 122/122 PASS; S-SZ 96 PASS; S-X 96 (90 + 6 N8) a/b/c PASS; S-D INSUFFICIENT_CO_PHU (gridDue 17 lan, 17 chan tier luoi, rig 0 DCA);
  V gates + lap dat PASS; N10 3,1 %.
- DEV-2 (DEV2T cham lai): RESULT HUY - V9 false (cua so DEV-2 khong du quy warm-up gate: buffer tu 01-01, sim co 90 ngay) => 14 lenh
  PREDICT 02-06 bi jar REJECT (r < q, nguong rolling khac) => S-G FAIL, S-X 14 MISSING (cung lenh). S-SZ PASS (79, 7,7e-5). S-D: voi V-TIER
  (FIGHT loai) SPACE 1/1 PASS; khong V-TIER 2/2. N10 7,7 % (CAN_OWNER). DEV-2 chi dung cho S-D / S-SZ.
- Lenh chinh thuc: run_official_rsim.sh <A1_REF> 29152e39,bb91e639,050912ca,03bb65e0,0740e790 -> official_ow1/RESULT_RSIM.json
