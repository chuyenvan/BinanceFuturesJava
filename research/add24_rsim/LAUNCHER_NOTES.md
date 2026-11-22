# LAUNCHER_NOTES - Add24RsimMain (DEV-B, R-SIM) - moi diem can thiep vao jar / harness (cho A1 soi)
Ma nguon: ~/claude_master/w3/add24/b/jsrc (javac -> add24/b/classes, classpath = STUB cf0f4792 : test-classes DEV-A add24_wt : add24/b/classes).
Nguyen tac: KHONG sua byte nao cua jar, KHONG sua file DEV-A; chi (a) dung API production / test cua jar va harness, (b) thay DUNG cac tham so
ma harness E2E da tu dat khac production cho bai toan 11-05, de rig chay CUNG duong production o cac diem R-SIM can.

| # | Diem can thiep | Cach | Vi sao | Vi sao KHONG lam jar chay khac duong production |
|---|---|---|---|---|
| L1 | Opts.legacy (final Set) cua CrashDayRig | reflection Field.set -> FollowSet (AbstractSet: iterator rong, size 0, contains(s) = !(s la lenh sim o phut b hoac rig dang giu s); b = floor(t/1')-1') | "theo vet sim" (EB3): moi ung vien van qua gate jar + nap r; chi vao lenh o (phut,symbol) cua sim | Duong production LEGACY (GatePreFilter.runSelector GATE_NO_ENTRY, createOrderBuyRequest0 SKIP_LEGACY_AFTER_GATE, C3LiveRuntime.buildEntry legacy) - jar quyet gate / size / DCA nhu that; chi tap symbol LEGACY la dau vao |
| L2 | LiveGateRollingRatio buffer | goi LiveGateRollingRatio.init() (that, env) TRUOC harness roi GateRatioBuffer.bulkAdd(ts,r) qua reflection (Add24BufWrite.initAndBulkAdd) | init() loc persist theo System.currentTimeMillis() (11/2026) => moi ban ghi 2026 bi bo (EB12); bulkAdd = CHINH ham loadPersistedAndSeed dung khi restart | r tinh bang bieu thuc threshold() voi hang so EntryGate cua jar; sau do moi truy van/ nap la code jar; startProduction cua harness thanh no-op (inited) |
| L3 | TrailingStopManager.defer | thread cho r.mgr != null roi reflection dat defer = Proxy -> TsMktExt.deferTimeStop (ham jar) | harness E2E hard-code .defer((s,t0,n)->false) (X14 tat cho 11-05) (EB10) | = mac dinh production: TrailingStopManager(b.defer == null) => TsMktExt::deferTimeStop. Swap xay ra truoc moi time-stop (>=168h); ghi add24_meta.txt |
| L4 | TsMktExt instance | Add24TsxInject (cung package): new TsMktExt(reader rong, file, 0, 0) + setFlagForTest ON cac ngay SIM_LOSER_TS_EXT_DAYS 2026, OFF moi ngay khac [START-2d, END+40d] + setInstanceForTest | X14 can co ngay UTC; rig khong co store ALT_EW; sim dung danh sach ngay co dinh (EB4) | decide()/deferTimeStop()/legacyCheck cua jar giu nguyen; chi nguon co (flags) la dau vao (nhu ts_ext_daily do scheduler ghi o live). OFF tuong minh tranh PENDING/grace |
| L5 | Opts.followPx | o.followPx.put(cid c3-SYM-<phut>-0, gia vao sim) (co che L0-FOLLOW-lite cua DEV-A) | ERRATA1 EB11 buoc 1: leg0 khop tai gia vao sim | Chi doi gia khop cua san gia lap FakeExchange1m cho LENH MUA leg0; qty/budget do jar tinh truoc lenh |
| L6 | Opts.a1 = false | gan truong | sim khong loc A1 (K11, EB4) | UniverseA1 cua jar (env) van chay o C3LiveEntry; chi bo loc A1 cua tang selector harness |
| L7 | fixture | exinfo SETTLING->TRADING (ban sao, EB7); BTCUSDT 1m (KS C1, EB9); sel top-24 + warm (EB3) | du lieu | khong phai code |
Khong co diem nao khac: khong doi env ngoai override khai trong run_rsim.sh (OVR); khong goi main() jar; java trong bwrap --unshare-net.

## LUOT 3 (ERRATA2 bb91e639) - diem moi
| # | Diem | Cach | Vi sao | Vi sao khong doi duong production |
|---|---|---|---|---|
| L8 | Duong gia trong nen (ERRATA2 2a/2b) | Launcher doi cho chuoi ReplayData.Bar.s[1]/s[2] (H/L): lane sim (O->L->H->C) doi o nen GIAM; lane sens (O->H->L->C) doi o nen TANG. CrashDayRig.applyPrices (DEV-A, khong sua) doc moc qua bd(i)=s[i]: giam -> O,s1,s2,C; tang -> O,s2,s1,C | CrashDayRig final, khong ke thua duoc; quy uoc thu tu trong nen la gia dinh mo phong | Chi doi THU TU moc gia dau vao; float h/l (kline() cho KillSwitch) giu nguyen; jar chi thay chuoi gia |
| L9 | Gia khop stop (ERRATA2 2a) | Ap o SCORER (score_rsim.py): thoat TRAIL -> gia = SL dang dat (su kien TRAIL_STOP_PLACED cuoi truoc khop) neu open nen khop > SL, nguoc lai open. Gia khop tho cua FakeExchange luu cot rig_fill_raw | FakeExchange1m final (khong sua); vi the da dong nen gia khop khong anh huong quyet dinh jar ve sau tren cum do | Phut khop / SL / ly do = quyet dinh jar; chi quy uoc gia khop (dau ra) |
| L10 | Bo loc san (ERRATA2 2c) | build_fx --pin: exinfo fixture = 20261027 + tickSize / LOT_SIZE & MARKET_LOT_SIZE (stepSize=minQty=minQty pin) cua exchange_info_pin.json sim (md5 5a815948 = file trong dataset sim-x1-2021-bundle, tai bang kaggle datasets download -f) | sim lam tron gia/qty theo pin | Du lieu (fixture), khong phai code; danh sach symbol khac ghi fx_check.json pin_diff |
| L11 | S-G2 ca quy | conv --hi = het quy (sel + follow moi lenh sim trong quy); cham lenh chi trong cua so; dem PASS/seen tu trace_dec | ERRATA2 1 | Khong can thiep jar |
| P1 | Add24DcaProbe (3b) | Goi ham jar MarketBigChangeDetector.getMarketStatus1M / isDcaAlt, DcaUtils.shouldDcaGrid, AIRejectFilter.entryGate(sp=null) tren market.bin SIM / market.csv rig | phan xu FIGHT | Chi doc ham jar, khong rig |
| P2 | Add24TierProbe (B5) | doc ticker sim tk26 (ObjectInputStream, class KlineObjectSimple cua jar) + tai lap CoinRankManager.updateRanking moi gio | phan xu tier | chi doc du lieu, khong rig |

## LUOT 5-6 (ERRATA3 050912ca, ERRATA4 03bb65e0) - diem moi. DANH SACH DAY DU diem can thiep vao rig = L1..L13 (khong co diem nao khac)
| # | Diem | Cach | Vi sao | Vi sao khong doi duong production |
|---|---|---|---|---|
| L12 | Tier3 cua C3LiveEntry (ERRATA4 1a) | Add24RsimMain (12): thread doi r.entry != null (truoc moi leg; meta ghi rig_t lap dat = START) roi reflection tren CHINH instance C3LiveEntry (final, khong ke thua): (a) truong private final `reconAllows` (Predicate<String>, decide() goi ngay TRUOC nhanh DCA) -> boc: ghi symbol dang xet roi goi ham goc; (b) truong private final `gridDue` (interface C3LiveEntry$GridDue) -> Proxy: goi ham GOC, neu GOC true VA symbol la T3 theo tier LUOI sim tai phut b = floor(t/1')-1' => tra false. Tier luoi = ADD24_SIMTIER (simtier_code.csv: Add24SimTierCode = CoinRankManager/HistoryManager/SimpleSymbolMapper bien dich tu git a8690d46, mapper ov_idtostr.tsv HO5, nuoi ticker sim, chi cap nhat o moc sim 2026-01-19 07:00 / 02-06 04:00); symbol khong co trong xep hang = T3 (UNKNOWN). Phut truoc moc dau = khong chan (NO_STATE_ALLOW, dem). Moi lan goi ghi sim_tier3_block.csv (ALLOW / SIM_TIER3_BLOCK / NO_STATE_ALLOW) + dem trong add24_meta.txt | CrashDayRig:922 (DEV-A) hard-code LegInput(tierMul=1, tier3=false). ERRATA4 1a: rig theo vet TRANG THAI tier cua sim | Trong decide() (76134a52) sau gridDue chi co `legIdx = ...; if (in.tier3) return TIER3_DCA` => tra false o gridDue cho CUNG ket qua "khong vao leg DCA", khong tac dung phu; khac duy nhat: outcome ghi DCA_NOT_DUE thay TIER3_DCA (scorer doc sim_tier3_block.csv). reconAllows goc van duoc goi y nguyen. tierMultiplier van = 1 (TIER_FLAT=1 hai phia) |
| L13 | N10 = dang giu (ERRATA3 B3) | n10_held.py (fixture, khong phai code): luot 1 xac dinh N10 (legs.csv NOT_BUYABLE + detail dung phut+symbol entry sim) -> FX_n10 = ban sao FX, xoa nen klines.csv.gz cua symbol N10 trong [start+1', end) cua CHINH cum sim do => ticker null => harness SKIP (khong nap gate), nhu sim giu | sim giu vi the jar tu choi (guard production DELIVERY_SOON) | Du lieu dau vao; quyet dinh jar khong doi. DEV: 4 237 nen xoa = dung so dong cascade |
| L2' | Bien moi truong ADD24_SIMTIER (run_rsim.sh ghi vao env_used.sh) | chi doc boi Add24RsimMain | L12 | jar khong doc bien nay |
Ngoai rig (chi doc du lieu / ham jar, khong anh huong rig): P3 Add24TierAll (tier theo gio, EB24 chan ts > 09-30 23:59:59 +07), P4 Add24DcaAll
(dieu kien DCA moi phut: ham jar), P5 Add24SimTierCode (classpath simcls/ = code a8690d46 TRUOC jar stub; CHI dung cho probe, KHONG co tren
classpath cua rig), P6 Add24TkPeek (khoa phut file ticker). Scorer: V-TIER (vtier.py -> score_rsim.py --vtier: cum TIER_DIV loai khoi
S-X/S-SZ/S-D, S-G/S-G2 giu nguyen), verdict_e3.py (B1/B2/B4-N11), summarize_official.py (RESULT_E4.json).
Kiem L12: DEV-2 (DEV2T) S-D 2/2 (FIGHT 02-06 04:01 leg 1, SPACE 02-06 04:19 leg 1), 83 lan chan FIGHT 02-01..02-06; DEV7 (Q2) = DEV6 tung byte
(legs, fills, trace_dec) vi gridDue duoc goi 0 lan (fixture Q2 khong co thi truong toan san -> rig khong co nhanh DCA).
Port tier (Add24TierAll) == code a8690d46 (Add24SimTierCode) o ca 2 moc: 541 / 547 symbol, 0 khac tier.

## LUOT 7 - KHONG co diem can thiep MOI vao jar / harness (L1..L13 giu nguyen). Thay doi chi o FIXTURE va SCORER:
| # | Diem | Cach | Vi sao | Vi sao khong doi duong production |
|---|---|---|---|---|
| F1 | mkt.csv.gz toan san (EB25) | run_official: mkt_days_ow1.py + run_pricedue.sh (Add24PriceDue = DcaUtils.shouldDcaGrid jar tren gia SIM closes.csv.gz cua cum leg0 trong [07-01,10-01)) -> ngay UTC co gia cham bac + ngay truoc; dl_mkt_days.py (Vision daily, EB24: tu choi ngay UTC >= 09-30, loc ts > 09-30 23:59:59 +07 tung dong); mkt_filter.py giu PHUT cham bac + 16' truoc; build_fx --mkt (manifest mkt.from = phut dau) | rig chi vao dcaPass khi co thi truong (level/dcaAlt) + gia cham bac + gate; ngoai cac phut do gridDue khong bao gio duoc goi | Du lieu dau vao; harness tu tinh thi truong (MarketReplay) nhu truoc. Bo nho ReplayData.loadMkt = n_sym x 5 x (END - mkt.from) float => mkt.from phai sat (thu DEV7M5: 16 ngay chay Xmx3g) |
| S1 | ssz_inputs_l7.py (EB28/EB29) | thay ssz_inputs.py trong run_official (file cu giu nguyen) | xem ERRATA_PROPOSED_B LUOT 7 | chi dau vao S-SZ (E_sim, M_run, thu tu leg) - khong vao rig |
| S2 | score_rsim.py S-D | them rig_extra (leg DCA rig SUBMITTED ma sim khong co trong cum leg0 trong cua so, tru cum V-TIER) va trang thai PASS_ZERO (sim 0 = rig 0) | ERRATA4 / MASTER LUOT7 muc 3 | chi doc legs.csv |
Thu F1 tren Q2 (DEV7M4, END rut 06-13, mkt 06-04..06-12 UTC): gridDue goi 17 lan (SLX 8, OPN 9) = DUNG 17 phut TIER_DIV cua V-TIER; ca 17
bi L12 chan (tier luoi T3) => rig 0 leg DCA = sim 0 (S-D PASS_ZERO). Ngoai gio thi truong khong du dieu kien -> khong goi.

## LUOT 8 (ERRATA5 0740e790) - khong diem can thiep moi; bo sung quy tac + cong
- L9 MO RONG (ERRATA5 A, ghi nhan quy tac scorer score_rsim.py:155-162): thoat TRAIL -> gia khop = SL dang dat (TRAIL_STOP_PLACED cuoi truoc
  khop). Neu SL duoc DAT ngay TRONG nen khop (ms >= dau nen) => gia khop = SL (khong ap min(SL, open)); neu SL co tu truoc nen va open > SL
  => SL; nguoc lai (open <= SL, gap) => open. Gia khop tho FakeExchange giu o cot rig_fill_raw. Hop ly voi duong O->L->H->C (lane sim):
  H nang SL roi C/L cat SL trong cung nen.
- CONG LAP DAT (m1, verdict_rsim.py INSTALL): add24_meta.txt dong "x14=swapped rig_t=<ms>" (L3) va "simtier=installed rig_t=<ms>" (L12)
  phai co VA rig_t <= START (manifest fixture); khong dat => RESULT = HUY. Thread lap dat doi r.mgr / r.entry != null (tao trong khoi dung
  rig, truoc vong phut) - DEV7/DEV8/DEV2T: rig_t = START.
