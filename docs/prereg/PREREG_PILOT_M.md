# PREREG_PILOT_M - kiem chung HANG NGAY lenh that trong PILOT 5.000 (c3 v1.2, jar 01cfbb43) - v3
Trang thai: v3 sau A1_PILOT_M_V2 (v2 3cc4f815 tai v12/PREREG_PILOT_M_v2_draft.md; v2 sau A1_PILOT_M, FAIL ban v1 8cd03322), 2026-11-25 +07, agent soan thao (Opus), CHI DOC.
CHOT 2026-11-25 +07: MASTER duyet; A1 vong 1 FAIL (v1) -> sua B1-B9, m1-m13; A1 vong 2 FAIL sat nguong (v2) -> dan NGUYEN VAN R1-R4 + n1-n4
(A1_PILOT_M_V2: dan R1-R4 thi commit duoc, khong can vong 3); MASTER doi chieu diff v2->v3 (ban truoc dong CHOT nay: sha256 df30a902). Bao cao A1 + ghi chu nguon: docs/result/pilot_m/.
Ban v1 giu tai v12/PREREG_PILOT_M_v1_draft.md. Ten chot: vz_e1_wt/docs/prereg/PREREG_PILOT_M.md.
Moi nguong / dinh nghia CHOT khi MASTER commit; sau commit chi sua bang ERRATA commit TRUOC lan cham ke tiep (neu ly do).
Nguon tung hang so / chuoi log (file:dong): v12/PILOT_M_DRAFT_NOTES.md.
Can cu: OWNER_DECISION_PILOT_1121_ADD6 (7514d874) muc 4 (cam ket MASTER); MASTER_CONCLUSION_RLIVE_1124 (cc4a4339); PREREG ADD24 6ee84f17
+ ERRATA1-7 (ERRATA6 70d2840d, ERRATA7 fa00ccdf); A1_RLIVE_RUN3_1124 muc 4.3 (7 bat bien E1-E7); REVIEW_1124_BT_LIVE (D1-D14);
PILOT_DAY_1126; A1_PILOT_M (B1-B9, m1-m13). Code jar live = c3_hotfix commit 4fdda6f8 (REVIEW_1124 muc 0); c3_hotfix HEAD 76134a52,
4fdda6f8..HEAD chi doi ops/ (Java = 4fdda6f8).
Su co pham vi (khai bao): nguoi soan KHONG doc / dem / tinh dong log, kline, mark, output rig nao co thoi gian >= 2026-11-24 07:00 +07,
TRU MOT lan: lenh `tail -3` cron log monitor in 3 dong luc 2026-11-25 12:02 (sau T_cut) gom so cum (so_c3=7cum) va gia tri tien
(tmb, tmb0, eq, dd cua tk con) + "deadman OK". Cac dong nay KHONG duoc luu, KHONG dung cho bat ky nguong / dinh nghia nao (A1_PILOT_M muc
"Chong nhin truoc" da doi chieu tung nguong voi nguon). Khong tinh / in PnL.

## 0. Pham vi va nguyen tac
- Ngay cham D = cua so [D 07:00 ; D+1 07:00) +07 = ngay UTC D = dung cua so pull242/<D>/ (check.txt ws_ms / we_ms) = 1 ngay UTC Vision.
- Du lieu cham: (a) log live pull242/<D>/logs/full.log*.gz (Oracle; KHONG doc 242 cho viec cham); (b) pull242/<D>/dumps (sel_dump,
  feat_dump), run/gate_ratio_live.bin.gz; (c) Vision futures UM klines 1m + markPriceKlines 1m CHI cho symbol live giu / co SUBMIT / ung
  vien rank <= 24 trong ngay D; (d) ~/claude_master/deploy/golive_monitor_cron.log (dong "TOM TAT:" cua cron monitor Oracle) cho M-K.
  Ngay dau = D 2026-11-24 (du lieu tu 2026-11-24 07:00 +07, CHUA dung trong R-LIVE). Khong dung du lieu truoc moc nay de cham.
- Du lieu thi truong >= 2026-10-01 (Vision) cho PILOT-M: ngoai pham vi ADD4 (U5 chi 18-24/11) => moi phan can Vision = KCD_CAU_TRUC cho
  toi khi owner xac nhan bang van ban (muc 13 Q1).
- Nguong lay tu hang so code (4fdda6f8) / banner khoi dong live / prereg ADD24 + ERRATA; KHONG lay tu du lieu moi. Moi so co dong nguon.
- Khong doi tieu chi sau khi thay so. Doi = ERRATA commit truoc lan cham ke tiep, neu ly do; lan cham da lam giu nguyen ket qua cu.
- PILOT-M KHONG quyet dinh thay owner: sinh BAC canh bao (muc 10) + hanh dong DE XUAT. Khong dung PnL de cham dat / truot; PnL, equity
  chi o muc M-R (mo ta, chi ti le dd). Khi doc dong log co truong lai lo / tien (vd "[C3-LIVE-BOOK] dong cum ... realized= phi=",
  "[KILLSW] HOURLY ... eq= peak= acct_eq=", TOM TAT "tmb= eq= tmb0="), bo cham PHAI bo truong do truoc khi ghi bat ky file nao
  (ngoai le: eq= cua [KILLSW] HOURLY chi dung trong bo nho cho M-S (2), khong ghi ra).
- Trang thai moi muc moi ngay:
  | Trang thai | Nghia |
  | DAT | moi su kien dat |
  | VI_PHAM | >= 1 su kien khong dat |
  | KHONG_CO_SU_KIEN | mau = 0 (KHONG tinh dat) |
  | KHONG_CHAM_DUOC | thieu du lieu VAN HANH: pull242/<D> chua COMPLETE / thieu file, Vision ngay UTC D chua phat hanh (khi da co quyen), log thieu truong; ghi ly do |
  | KCD_CAU_TRUC | khong cham duoc vi CAU TRUC: chua co van ban owner cho du lieu (Q1) / chua co cong cu duoc A1 duyet (Q2, muc 12) / K7 (Q4); ghi ly do |
  Gop (nhieu tieu muc -> 1 muc): VI_PHAM > KHONG_CHAM_DUOC > KCD_CAU_TRUC > KHONG_CO_SU_KIEN > DAT.
- "Cum" = (symbol, tsFirstLeg). Thoi diem mo cum = thoi diem dong "[C3-LIVE] SUBMIT <SYM> <LEVEL> SUBMITTED cid=c3-<SYM>-<barMin>-0"
  (tsFirstLeg = nowMs luc reserve, TRUOC dong nay: LiveBookC3:539, C3LiveEntry :279 -> :295). Cum dong = dong "[C3-LIVE] cum <SYM> DA DONG
  tren san (<ly do>)". Cum mo qua nhieu ngay: trang thai doc lien tuc tu log cac ngay truoc (bat dau tu log 2026-11-21 cho 8 cum mo tai
  T_cut, chi dung dong SUBMIT / FILL / arm / stop de dung trang thai, khong tinh thong ke tren ngay < 2026-11-24).
- Tre phat hien: pull ngay D xong ~08:23 +07 ngay D+1 => vi pham som nhat bao sau toi ~26 h (Vision: them ~1 ngay). Xem muc 11.

## 1. M-E - tai lap VAO lenh (tre theo Vision D)
### 1.1 Dinh nghia (giu nguyen ADD24 sau ERRATA1-7)
- L-E: tap (phut quyet dinh dts, symbol, level, legIdx) cua moi dong SUBMIT live trong ngay D == tap cua lane L0 (rig jar stub), thu tu trong
  phut 100 %. L-N: moi phut co input (co sel_dump va JVM chay) ma live khong SUBMIT thi rig cung khong (va nguoc lai). Nhan dong N1-N12
  dung nhu ADD24 s8 + ERRATA1 (N9), ERRATA2/3 (N3 dinh nghia moi = phut co sel_dump nhung live khong co dong tick quyet dinh), ERRATA4 C1
  (ke thua), ERRATA5 D1 (N6 = [GATE] n_skipfull > 0), ERRATA5 B(i) (tiem TIER3). Lech khong nhan = KHONG GIAI THICH.
- Phan loai lech M-E (de xep bac): nhom E = "cung thong tin, quyet dinh khac" = lech L-E / L-N KHONG GIAI THICH tai phut ma V10a (ERRATA7 D)
  cua ngay do DAT (rig va live cung dau vao gate + cung tap dang giu). Lech o phut V10a khong dat / tap giu khac = nhom "trang thai khac"
  (do lech thoat lenh da biet) - ghi, khong phai nhom E.
- Chi tieu: 0 lech nhom E; thu tu 100 %.
### 1.2 Kha thi voi harness ADD24 HEAD 8d397ce2 (KHONG sua)
- KHONG chay duoc nguyen trang tren ngay moi: run_rlive.sh:29-33 co dinh START='2026-11-19 09:31', CAP=1000, TCUT phai khop
  ^2026-11-2[0-4] 07:00$ (exit 15); P1 gate chi cho OW2 (ADD4); rig khoi dong voi so RONG (A11) trong khi tu 2026-11-24 live dang giu
  8 cum. => M-E can MOT wrapper moi (nhanh rieng tu 8d397ce2, KHONG doi bo cham rlive_score / conclude / labels): tham so START = D 07:00,
  END = D+1 07:00, CAP = c3_capital trong banner "[C3-LIVE] khoi dong ... c3_capital=" cua JVM dang chay, nap trang thai dang giu dau
  ngay THEO VET live (tap cum mo + legCount + firstEntryPrice tu log; khong mo phong thoat - thoat da biet lech). Wrapper phai qua A1
  (muc 12). Chua co wrapper duoc A1 duyet (hoac chua co quyen Vision Q1) => M-E = KCD_CAU_TRUC (khong bao gio tinh dat).
- Von: CAP = 1000 cho phut truoc dong khoi dong JVM pilot 2026-11-26; CAP = 5000 sau do. Ngay 2026-11-26 tach 2 doan tai dong
  "MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager" cua lan restart pilot; phut JVM khong chay = N3; KHONG ghep 2 doan
  trong 1 lane (rig khong doi von giua luot).
- V8 (banner): so banner rig voi banner live cua CHINH JVM chay trong ngay D (khong phai banner 20/11), danh sach khac duoc phep = ERRATA3 A9
  + c3_capital.
- Khi da co quyen + wrapper: Vision ngay UTC D chua phat hanh (HTTP HEAD klines 1m BTCUSDT != 200) hoac pull242/<D>/COMPLETE chua co =>
  KHONG_CHAM_DUOC; cham lai khi co. Qua 2026-(D+3) 09:00 +07 van thieu => "thieu du lieu > 1 ngay" (muc 10 VANG).
### 1.3 M-E0 - kiem chi tu log + pull (khong rig, chay duoc ngay)
Moi dong SUBMIT live ngay D: (a) cid = c3-<SYM>-<barMin>-<legIdx> voi barMin*60 000 = dts va thoi diem dong log trong [dts+60 s ; dts+180 s];
(b) chi leg 0 level PREDICT_SYMBOL_TRADE: symbol co trong sel_dump ts=dts voi rank <= 24 (pull242/<D>/dumps/sel_dump_*.csv.gz, cot
ts,symbol,...,rank); leg 0 BIG_DOWN: co dong "Market level change: <yyyyMMdd HH:mm> level: BIG_DOWN" (DetectEntrySignal2TradeNormal :365)
hoac "Market level:<dts> BIG_DOWN <SYM>" (:1474) cung phut; (c) leg 0: truoc do khong co cum mo cung symbol; (d) moi SUBMIT co dung 1 dong
xac nhan khop ("[C3-LIVE-EXEC] FILL <SYM> <cid>" hoac "[C3-LIVE-FILL] xac nhan qua stream <SYM> <cid>") HOAC 1 dong ket thuc khong khop:
"[C3-LIVE-FILL] leg <SYM> <cid> ket thuc <X> khong khop => huy giu cho" (FillAccounting :211) hoac moi dong "[C3-LIVE-EXEC] <SYM> <cid> ...
=> huy giu cho" (C3LiveOrderExecutor :304/:321/:553/:562), trong 300 s. Chi tieu 100 %. Day KHONG thay M-E (khong kiem gate / L-N).

## 2. M-I - bat bien THOAT lenh tren log live (hang ngay)
Mau so moi bat bien = so su kien trong ngay D; mau 0 => KHONG_CO_SU_KIEN. Chi tieu moi bat bien 100 %. Dong log dung (prefix bo qua):
 ARM  = "[C3-LIVE-TRAIL] arm <SYM> entry=<e> px=<p> peak=<k> SL=<s>"
 STOP = "[C3-LIVE-TRAIL] <SYM> (ARM|MOVE) stop=<P> cid=<c3s-...> mode=(closePosition|qty+reduceOnly) (cu=<cid|null> <px>)"
 ALGO = "[C3-LIVE-FILL] ALGO_UPDATE <SYM> caid=<cid> X=<NEW|CANCELED|TRIGGERED|FINISHED|...> ai=..."
 SFIL = "[C3-LIVE-FILL] <SYM> stop khop <qty>@<px> (stop=<P> truot=<1-px/P>)"
 CLOS = "[C3-LIVE] cum <SYM> DA DONG tren san (<ly do>) qty=..." ; BOOK = "[C3-LIVE-BOOK] dong cum <SYM> ly do=<r> legs= qty= ... exitQty="
 TS   = "[C3-LIVE-TRAIL] TIME-STOP <SYM> entry= px= gio_giu=<h> => dong MARKET reduce-only"
 RST  = "[C3-LIVE-TRAIL] <SYM> khong con arm (DCA reset) => huy stop <cid>"
### 2.1 Bay bat bien da kiem hau nghiem (A1_RLIVE_RUN3 muc 4.3) - nay DANG KY TRUOC
Ky hieu: entry = truong entry= cua dong ARM (= avgEntryF cua cum); HIGH/LOW/O/C = kline 1m LAST Vision; markLOW = low markPriceKlines 1m.
Cong thuc (code TradeUtils.trailFromCap :52-58, tinh bang float32 nhu code - Math.round tren float):
 F(peak) = entry x (1 + round((peak - min(peak x GIVEBACK, GAP)) / 0,005) x 0,005), stop dat = lam tron XUONG theo tickSize (syncStop).
 GAP = 0,03, GIVEBACK = 1: KHONG in o banner (mac dinh Configs 0,08 / 0,03 / 0,5); C3TrailRate chon TS_MAX_GAP hoac TS_MAX_GAP_WEAK theo
 pNoPump (TRAIL_HINGE_NET015=true) => ca hai phai = 0,03. Gia tri hieu luc SUY tu ARM SL (A1_RLIVE_RUN3 4.1 khop 16/16; A1_PILOT_M tinh lai
 BLESS / JCT); I9(b) la phep kiem lien tuc cua gia tri nay.
- I1 (E1, can Vision kline => KCD_CAU_TRUC toi Q1): moi STOP cua cum: P <= floorTick(F(peakMax)) + 1 tick, peakMax = max HIGH tu phut khop
  leg dau (gom phut dts+1) toi phut cua dong STOP / entry - 1. Su kien = moi dong STOP. Vuot + 1 tick nhung < 0,1 % => VANG "DATA" (nguon
  price_realtime live co the khac LAST Vision), khong VI_PHAM.
- I2 (E2, can Vision kline => KCD_CAU_TRUC toi Q1): VI_PHAM chi khi co 2 phut tron LIEN TIEP (sau phut khop leg dau) deu co O > entry x 1,07
  VA C > entry x 1,07 ma dong ARM cua cum chua co toi het phut thu hai (lay mau 10 s => 1 phut le khong bao dam co mau > nguong). Arm 0,07 =
  LiveProfileC3.ARM_RATE :51, banner "arm=0.07". Su kien = moi cum-ngay dang giu chua arm dau ngay hoac arm trong ngay. Bo qua phut co dong
  "[C3-LIVE] khong doc duoc gia realtime" hoac thuoc N3.
- I3 (E3, chi log): chuoi P cua STOP trong mot pha arm (tu ARM toi CLOS hoac RST) tang nghiem: moi MOVE co P >= P_truoc + 1 tick VA
  P >= P_truoc x 1,001 (syncStop: tick + DEFAULT_MIN_MOVE_FRAC 0,001, TrailingStopManager :55). Ngoai le DUY NHAT: dong RST mo pha moi.
- I4 (E4, chi log): (a) moi ARM co dong STOP "ARM" cung symbol trong <= 61 s (C3StopProtector.DEADLINE_MS) - qua 61 s ma co
  "[C3-LIVE-TRAIL] <SYM> dat stop ... loi ... => thu lai nhip sau" thi stop cu phai van hieu luc (khong co ALGO X=CANCELED cua stop cu truoc
  khi stop moi X=NEW); (b) moi cid cua STOP co ALGO X=NEW voi thoi diem trong [t_STOP - 5 s ; t_STOP + 61 s] (ALGO NEW qua stream thuong in
  TRUOC dong STOP 14-21 ms); (c) moi cid bi thay (cu=<cid>) co ALGO X=CANCELED (hoac "huy stop ... loi => thu lai" roi CANCELED) truoc dong
  CLOS cua cum; (d) moi CLOS ly do TRAILING_STOP co ALGO X=TRIGGERED cua cid stop dang hieu luc truoc do.
- I5 (E5, can Vision mark => KCD_CAU_TRUC toi Q1): sau khi stop P hieu luc (ALGO X=NEW) va truoc phut cua CLOS, KHONG co phut tron nao co
  markLOW <= P (live da phai thoat). Phut dang thay stop (stop cu da huy, moi chua NEW) => dung P nho hon.
- I6 (E6, can Vision mark => KCD_CAU_TRUC toi Q1): phut cua SFIL/CLOS ly do TRAILING_STOP co markLOW <= P (phut do hoac phut truoc).
- I7 (E7, can rig L0-FOLLOW => KCD_CAU_TRUC toi Q2): so voi L0-FOLLOW cung ngay: live KHONG arm som hon rig va P_live <= P_rig + 2 tick khi
  rig con giu.
### 2.2 Bat bien MASTER yeu cau them
- I8 (i) Khong dat stop / dong cum truoc ARM, tru ngoai le: khong co STOP, SFIL, CLOS ly do TRAILING_STOP / TRAILING_IMMEDIATE /
  STOP_LOST_61S cua cum truoc dong ARM dau tien cua cum. CLOS truoc ARM chi duoc voi ly do thuoc {TIME_STOP_168H, FLATTEN*, EXTERNAL
  (thu cong, phai co ghi chep owner cung ngay), DELIST_SETTLE}. Chi log.
- I9 (ii) Muc trailing chi tang theo dinh da ghi: (a) = I3; (b) SL cua dong ARM == F(peak cua chinh dong ARM) tinh float32, sai <= 1e-6
  tuong doi; (c) dong ARM chi xuat hien 1 lan moi pha. Chi log. (Dong MOVE khong in peak => phan "theo dinh" giua 2 MOVE chi kiem chan tren
  I1.)
- I10 (iii) Moi cum dong co DUNG 1 dong CLOS va 1 dong BOOK cung ly do, ly do thuoc tap code: {TRAILING_STOP, TIME_STOP_168H,
  TRAILING_IMMEDIATE, STOP_LOST_61S, FLATTEN*, EXTERNAL, DELIST_SETTLE, LIQUIDATION, ADL, LOST_FOREIGN, GHOST_CLEAR_OWNER, BOT_CLOSE}
  (FillAccounting :49-54, TrailingStopManager :53-54, C3StopProtector :34, Reconciler :68/:992). DAT chi khi ly do thuoc
  {TRAILING_STOP, TIME_STOP_168H, TRAILING_IMMEDIATE, FLATTEN*, EXTERNAL-co-ghi-chep}. STOP_LOST_61S / LIQUIDATION / ADL / LOST_FOREIGN /
  GHOST_CLEAR_OWNER / BOT_CLOSE / EXTERNAL khong ghi chep = VI_PHAM. Ghi chu: "X14" KHONG phai ly do dong rieng trong jar - X14 chi HOAN
  time-stop (TsMktExt.decide :105-112); cat sau hoan van la TIME_STOP_168H.
- I11 (iv) Sau dong cum, doi chieu khop: (a) dong "[C3-LIVE-RECON] HOURLY khop: doi chieu qty c3 (<n> cum) lech max=..." KE TIEP sau CLOS
  co n == so cum mo theo log tai thoi diem do, BO cum co leg treo, cum dang dong, cum MERGED va cum flat-pending (Reconciler :813-815), va
  KHONG chua chuoi "LECH" (so khop PHAN BIET hoa thuong - dong khop co "lech max="); (b) trong 24 h sau CLOS KHONG co dong chua
  "leo thang UNKNOWN" (gom "<SYM>: cum so da chot > ... ma san VAN con vi the" :597 va "... ma account VAN con vi the" :635) va KHONG co
  "[C3-LIVE-RECON] LECH QTY c3"; (c) neu co dong lop B "<SYM>: cum so vua chot nhung positionRisk con ... (lop B)" (:588) hoac "<SYM>: cum
  so vua chot nhung con stop c3s- dang giu => CHI chan mo moi" (:291) thi phai co "<SYM>: 2 lan doc phang ... GO chan rieng symbol (lop B)"
  (:646) trong <= 2 h. Ghi chu: Reconciler hang gio KHONG in qty tung symbol da dong => "qty = 0 cho symbol" cua khung MASTER thay bang
  (a)-(c). Chi log.
- I12 (v) Khong hai lenh dong cho cung cum: (a) <= 1 CLOS moi cum; (b) BOOK exitQty <= qty (+ 1 stepSize); (c) KHONG co dong
  "[C3-LIVE] vi the AM (short)" (FillAccounting :280) o bat ky dau; (d) tong qty cac SFIL cua cum <= qty cum. Chi log.

## 3. M-T - time-stop 168 h
- Code: cum CHUA arm (priceSL NaN) va now - tsFirstLeg > 168 h (strict) tai nhip exit (EXIT_EVERY_MS 10 s, C3LiveRuntime :78; vong ops 5 s
  :75) => TsMktExt.deferTimeStop: co ngay UTC hien tai ON hoac PENDING => HOAN (log "[TS-EXT] defer-START <SYM> age_h=168 flag=..."), toi
  da 504 h; OFF => dong "TIME-STOP" + closeCluster(TIME_STOP_168H) MARKET reduce-only. Nhip khong co gia => KHONG xet time-stop nhip do.
  PENDING chi trong 00:00-00:22 UTC (07:00-07:22 +07) hoac 20 phut dau sau khoi dong JVM (START_GRACE_MS).
- Cum da arm KHONG bao gio time-stop (chi trailing) - TrailingStopManager :207-231.
- TsMktExt la singleton DUNG CHUNG so GIAY (ShadowBookC3 :407, thread [pool-3-thread-1]) va so that (TrailingStopManager :127, thread
  [C3LIVE-OPS]); truoc T_cut da co defer-START cua so giay (21/11 21:01, 22/11 03:54, [pool-3-thread-1]). TsMktExt.track log o thread goi
  (:363-371); TrailingStopManager goi defer trong nhip exit cua opsLoop (moi dong TrailingStopManager truoc T_cut co thread [C3LIVE-OPS]).
  => defer-START cua cum THAT = dong co thread [C3LIVE-OPS]; thread khac = so giay, bo qua; dong khong co truong thread => KHONG_CHAM_DUOC.
  Cua so: dong "[TS-EXT] defer-START <SYM> age_h=168" [C3LIVE-OPS] trong (due - 2 s ; due + 120 s].
- Moc: due = thoi diem dong SUBMIT leg 0 + 168 h; cua so quyet dinh = (due - 2 s ; due + 120 s] (tsFirstLeg dat TRUOC dong SUBMIT;
  120 s = 10 s nhip + 5 s vong + <= 61 s cho guard Urgent + bien); CLOS ly do TIME_STOP_168H trong <= due + 600 s (Flattener 5 lenh / 10 s,
  gui lai luot sau).
- Cac cum mo tai T_cut (xac nhan tu log TRUOC 2026-11-24 07:00; 16 cum khac da dong TRAILING_STOP truoc T_cut; 8 cum nay chua co dong TRAIL
  nao truoc T_cut):
  | Cum | SUBMIT leg0 (+07) | due = SUBMIT + 168 h (+07) |
  | MMTUSDT | 2026-11-21 10:45:07.919 | 2026-11-28 10:45:07.9 |
  | ZILUSDT | 2026-11-21 11:08:07.970 | 2026-11-28 11:08:08.0 |
  | SOPHUSDT | 2026-11-21 11:08:12.306 | 2026-11-28 11:08:12.3 |
  | CFGUSDT | 2026-11-21 11:08:15.107 | 2026-11-28 11:08:15.1 |
  | KAVAUSDT | 2026-11-21 11:08:15.909 | 2026-11-28 11:08:15.9 |
  | BREVUSDT | 2026-11-21 11:08:19.340 | 2026-11-28 11:08:19.3 |
  | ICNTUSDT | 2026-11-21 11:08:20.212 | 2026-11-28 11:08:20.2 |
  | IRYSUSDT | 2026-11-21 11:08:21.935 | 2026-11-28 11:08:21.9 |
  (Moc "10:39" trong khung MASTER = BLESSUSDT, da dong 21/11 12:47 - khong thuoc M-T.) Restart 2026-11-26 khong doi tsFirstLeg (persist
  ts_first_leg, LiveBookC3 :1070/:1170); dong "[C3-LIVE] khoi dong ... cum=<n>" sau restart phai co n = so cum mo theo log.
- Cham moi cum co due trong ngay D, CHUA arm tai due, chua dong: DAT <=> mot trong hai: (A) co dong "[TS-EXT] flag day=<ngay UTC due>
  flag=OFF" (bat ky final=true|false) hoac khong co dong co ngay do ma thoi diem ngoai cua so PENDING, VA dong TS cua cum trong
  (due - 2 s ; due + 120 s] VA CLOS (TIME_STOP_168H) <= due + 600 s; (B) co ngay UTC due = ON (hoac PENDING hop le) VA dong defer-START cua
  cum THAT ([C3LIVE-OPS]) trong (due - 2 s ; due + 120 s] VA khong co TS / CLOS truoc khi co doi OFF hoac age > 504 h (khi do ap (A) voi moc moi = phut co
  doi / 504 h). Moi truong hop khac (dong som hon due - 2 s, khong dong / khong hoan sau due + 120 s, hoan khi co OFF, dong khi co ON) =
  VI_PHAM. Chi tieu 100 %. Chi log.

## 4. M-D - DCA
- Code (4fdda6f8): leg DCA = level DCA_LEVEL1, legIdx = legCount hien tai (gom leg 0; C3LiveEntry :242), 1..3; dieu kien due: close nen
  1m quyet dinh / firstEntryPrice - 1 <= level[legCount-1], levels = [-0,5 ; -0,75 ; -0,9] (banner "[LIVE-DCA-GRID] ... levels=[-0.5,
  -0.75, -0.9] legs=3") - DcaUtils.shouldDcaGrid :32-43; firstEntryPrice = gia KHOP leg 0 (D8). DCA chi duoc quet o phut co levelChange !=
  null hoac isDcaAlt (DetectEntrySignal2TradeNormal :472-517), KHONG phai moi phut.
- Gate cua leg DCA: ca nhanh "due=" va "live-only" di qua createOrderBuyRequest0 -> aiRejectFilter.entryGate(predict, symbolPred=null, ...)
  (DetectEntrySignal2TradeNormal :1314-1316) -> sp=null => thrBase = Configs.MIN_MOMENTUM_15M (AIRejectFilter :119) -> EntryGate.threshold
  (thr, null) = thr (EntryGate :184-198) => DCA co nguong p15 TUYET DOI MIN_MOMENTUM_15M (khong rolling). Dong log: PASS =
  "AI PASS [<SYM>] Reason: PERFECT: 15M(<x>%) symbolPred: null" (DetectEntrySignal2TradeNormal :1338, ly do AIRejectFilter :202-203; dong co
  ky tu bieu tuong o dau - so khop chuoi con nay); REJECT = "SKIP ORDER [<SYM> DCA_LEVEL1] due to AI REJECT: BAD MOMENTUM: ... symbolPred: null"
  (:1333, AIRejectFilter :200) - so khop theo TIEN TO "SKIP ORDER [<SYM> DCA_LEVEL1] due to AI REJECT"; 0 dong truoc T_cut, mau chi kiem
  bang code. BIG_DOWN bo gate p15 (BigDownSelect.bypassGate, :1302-1312).
- Gia tri hieu luc MIN_MOMENTUM_15M tren live = CHUA XAC NHAN: KHONG in o banner; mac dinh code 0,02284 (Configs :437, env
  SIM_MIN_MOMENTUM_15M :843) KHONG hieu luc vi log 20/11 08:54:06 co leg DCA_LEVEL1 PASS o 15M(1.03%) => hieu luc <= 0,0103; comment code
  nhac 0,008 (DetectEntrySignal2TradeNormal :1295/:1306, GateRollingRatio :26) - khong phai bang chung. => PILOT-M KHONG dung con so nguong
  cu the; chi yeu cau co dong PASS cho leg (D1(e)) va GHI gia tri 15M cua tung leg DCA (thong ke mo ta). Dong REJECT dau tien co (x < y) se
  cho y = nguong hieu luc: ghi lai, KHONG doi tieu chi.
- Chan khac: cum con leg treo / dang dong (DCA_PENDING), TIER3_DCA (log "skip"), latch (KS_BLOCKED; C4 khong chan DCA), U >= 0,60 (U_MAX),
  budget < 5 (BUDGET_SMALL), MODE_GUARD, RECON_BLOCKED, KILL file / drain (PUSH_OFF), MINUTE-INCOMPLETE / MINUTE-FIN-EXCL (ERRATA2).
  DCA_NOT_DUE / DCA_NOT_HOLDING / DCA_OFF / LEGACY chi log DEBUG (C3LiveEntry :298-301); "[C3-LIVE] KHONG vao lenh" WARN gioi han 1 lan /
  600 s / outcome (C3LiveEntry :36, :309-316).
- D1 (chi log, 100 %): moi SUBMIT level DCA_LEVEL1 legIdx=k: (a) ref (truong ref= cua dong FILL / xac nhan stream cung cid) / avg leg 0
  (avg= dong xac nhan leg 0; neu cid leg 0 co dong PX_CORRECTED thi dung gia sau hieu chinh cuoi) - 1 <= level[k-1] + 1e-6; (b) k == so leg da xac nhan khop cua cum (gom leg 0) va 1 <= k <= 3; (c) dong
  "[LIVE-DCA-GRID] site=... due=[...]" hoac "live-only due=<SYM>" cung phut quyet dinh co SYM; (d) leg truoc cua cum da xac nhan khop;
  (e) co dong "AI PASS [<SYM>] Reason: PERFECT: 15M(<x>%) symbolPred: null" trong [dts+60 s ; t_SUBMIT]. Ghi x cua moi leg (mo ta).
- D2 (can Vision kline => KCD_CAU_TRUC toi Q1, 100 %): ref cua leg DCA == close nen 1m Vision phut dts (dts = barMin cua cid) trong 1e-6
  tuong doi hoac 1 tick; lech => VANG "DATA" (nguon ingest live khac Vision), khong VI_PHAM.
- D3 (MUC THEO DOI, can Vision kline, KHONG sinh VI_PHAM / bac): dem phut cum dang giu co close_Vision / firstEntryPrice - 1 <= level[legCount-1]
  - 0,001 ma khong co SUBMIT DCA; phan loai: co "[LIVE-DCA-GRID] site=" cung phut / co "SKIP ORDER [<SYM> DCA_LEVEL1] due to AI REJECT" /
  MINUTE-INCOMPLETE / MINUTE-FIN-EXCL / "[C3-LIVE] skip <SYM> DCA_LEVEL1" / khong co dong nao (phut khong quet DCA). VI_PHAM chieu nguoc CHI
  qua D4 (rig).
- D4 (can rig => KCD_CAU_TRUC toi Q2): L-D ADD24 (bac, phut den han +-1, legIdx).
- Luu y da biet (KHONG phai lech): cum mo tu micro (von 1.000, leg 0 ~22,5) neu den bac sau restart pilot se co leg DCA size theo von
  JVM moi (b theo muc 5, ratio moi bac = 6) => ~5 lan leg 0 cua chinh cum (C3LiveEntry .capital = equity.capital cua JVM; PILOT_DAY_1126
  muc F). M-S cham leg do theo von 5.000.

## 5. M-S - sizing
- Cong thuc code (moi leg, ca DCA; C3LiveEntry :255-277): b0 = (C_eff x 0,015 x (1 - U/0,6) / 4) x 6 = 0,0225 x C_eff x (1 - U/0,6);
  b1 = min(b0 ; 0,045 x C_eff); b1 < 5 => BUDGET_SMALL; b = b1 x tierMul (SAU tran 4,5 % va SAU kiem minBudget; tierMul in {1,2 ; 1,0 ;
  0,5} theo TIER_1/2/3, = 1 neu TIER_FLAT - CoinRankManager :122-127); qty = floor(b / sizingPx ; marketStepSize); notional = qty x sizingPx
  <= b; minNotional => SIZING skip. C_eff = min(C3_CAPITAL, equity c3, availableBalance + margin c3) (C3MainEquity :163-170). U = margin c3
  dang dung (gom pending) / C_eff; U >= 0,6 => chan. (TradeUtils.managerBudget :125-145, LiveGridSizing :69-81, DcaUtils.gridLegWeightRatio
  :47-64 FIX_B2, SymbolRules :117-157; banner [LIVE-SIZING] F_BASE=0.015 SCALE=6.0 weights [1,1,1,1]; banner LiveProfileC3 sizeCap=4.5%.)
  Day leg lien tiep cung phut: (1 - U/0,6) giam ~x0,9625 moi leg (= 1 - 0,0225/0,6). Bang chung truoc T_cut: 24/24 SUBMIT co tierMul = 1.
- Dong log: SUBMIT ".. SUBMITTED cid=.. qty=<q> budget=<b> legIdx=<k> notional=<n> U_before=<u>"; C_eff KHONG in => C_ngam = b /
  (0,0225 x (1 - u/0,6)).
- MUC THEO DOI (bao so, khong xep bac rieng): (a) L-S2 ADD24 (budget rig L0 vs live <= 5e-4 o >= 90 % VA <= 2e-3 o 100 %) - KCD_CAU_TRUC
  toi Q2; (b) L-S ADD24 (budget trong bao s9.3 +-1e-5) - KCD_CAU_TRUC toi Q1; (c) phan phoi C_ngam / C3_CAPITAL - 1.
- MUC CANH BAO CUNG (chi log + exchangeInfo, 100 %): r = C_ngam / min(C3_CAPITAL, eq_lo) (equity c3 MTM; chi dung trong bo nho);
  eq_lo = min truong eq= cua cac dong [KILLSW] HOURLY CUNG JVM voi SUBMIT (sau banner khoi dong cua JVM dang chay) bao quanh SUBMIT; chi co
  1 dong cung JVM => dung dong do; khong co dong nao cung JVM => chi xet r_cap = C_ngam / C3_CAPITAL > 1 + 1e-6, nhanh r < 0,98 =
  KHONG_CHAM_DUOC cho leg do. VI_PHAM khi bat ky:
  (1) r > 1 + 1e-6 hoac r < 0,98 (2 % = dung sai T9 golive_first_trade_check / ADD22), TRU: |r - 1,2| <= 0,02 hoac |r - 0,5| <= 0,02 =>
  VANG "TIER" (MASTER dieu tra TIER_FLAT); r < 0,98 ma co dong "[C3-LIVE-EQ] CANH BAO ky quy" (C3MainEquity :174) trong 24 h truoc =>
  VANG "AVAIL";
  (3) notional > b x (1 + 1e-9); (4) b - notional > marketStepSize x (n/q) + 1e-9 (lam tron qty KHONG giai thich duoc); (5) q khong la boi
  so marketStepSize; (6) b > 0,045 x C3_CAPITAL x 1,2 hoac b < 5 x 0,5; (7) legIdx sai (leg 0 khi dang giu / DCA k != legCount).
  C3_CAPITAL = truong c3_capital cua banner khoi dong JVM dang chay. marketStepSize lay tu run/c3live_exchangeInfo.json cung ngay (MASTER
  chep chi doc) - thieu => (4)(5) KCD_CAU_TRUC cho toi khi co quy trinh chep exchangeInfo hang ngay duoc MASTER ghi vao prereg bang
  ERRATA; sau do thieu = KHONG_CHAM_DUOC.
  Can cu nguong: L-S2 da truot o 9,48e-4 do day chuyen gia khop (owner chap nhan ADD6) => muc theo doi giu nguong ADD24; muc cung bat
  loi cong thuc / von / lam tron (> 2 %) ma co che gia khop khong tao ra duoc.

## 6. M-X - chat luong thuc thi (mo ta + nguong kill-switch)
- Truot VAO (dinh nghia code = C2 co dau, KillSwitchEngine.c2Adverse :221-225, ref = close nen 1m quyet dinh): s_in = avg / ref - 1 tu dong
  "[C3-LIVE-EXEC] FILL ... avg= ref= slip=" hoac "[C3-LIVE-FILL] xac nhan qua stream ... avg= ref=" (moi cid 1 lan); neu cid co dong
  "PX_CORRECTED -> <px>" (C3LiveOrderExecutor :439-440, :504; FillAccounting :186) thi dung gia hieu chinh cuoi. Bao: n, median, p90, max
  (bps) theo NGAY va LUY KE tu 2026-11-24; so leg s_in > 0,017; so leg s_in > 0,025; so su kien > 0,025 trong 24 h truot.
- Truot RA: trailing = truong truot= cua SFIL (= 1 - px/stop, FillAccounting :233); time-stop / FLATTEN = 1 - gia khop / px cua dong TS.
  Chi bao (median, p90, max).
- Dem: REJECT / khong khop ("[C3-LIVE-EXEC] <SYM> <cid> KHONG khop"), -4130 ("san tu choi stop closePosition thu 2 (-4130)"), -2021
  ("se kich ngay (-2021"), gui lai ("gui lai CUNG cid"), UNKNOWN ("=> UNKNOWN"), "TU CHOI", "[KILLSW] C2_WARN", "[KILLSW] LATCH".
- Nguong (code OpsConfig :130-133 / KillSwitchEngine :140-143; banner 20/11 06:17 "C2 signed=1"): canh bao 0,017; kich 0,025; >= 3 lan /
  24 h => latch NO_NEW_ENTRY. Env LIVE_KILLSW_C2_WARN/_SLIP/_COUNT/_WINDOW_H co the ghi de; banner KHONG in nguong => nguong HIEU LUC
  CHUA XAC NHAN cho toi dong "[KILLSW] C2_WARN ... warn>X slip>Y" dau tien (in nguong that). Khi do dung so trong dong log.
- Xep bac: VANG khi: >= 1 leg s_in > c2Warn trong ngay; hoac >= 2 su kien > c2Slip trong 24 h truot (con 1 truoc latch); hoac median s_in
  LUY KE (>= 10 leg; gom ca leg micro von 1.000, khong tach) > 30 bps (L-P ADD24 => bao owner g_exec); hoac >= 1 -4130 ma khong co stop thay the <= 2 nhip (20 s) (L-K ADD24 =>
  VI_PHAM M-I I4). LATCH => muc 8 K6 / muc 10.

## 7. M-G - khoang cach thoat live <-> backtest (THU DU LIEU, KHONG cham dat / truot)
- Moi cum dong trong ngay D: live (phut CLOS, ly do, gia khop thoat TB tu SFIL hoac khop dong MARKET) + rig 1 phut L0 va L0-FOLLOW cung cum
  (phut thoat, ly do, gia thoat) ghep theo ERRATA1 E-A13 / ERRATA3 A6 / ERRATA4 C2 (L-T, L-SL, L-X). KCD_CAU_TRUC toi Q1 + Q2; phan live
  van ghi hang ngay.
- Thong ke dang ky truoc (luy ke tu 2026-11-24 07:00): ti le cung ly do; phan bo delta phut thoat (live - rig) min / p10 / median / p90 /
  max; ti le live muon hon / som hon / cung phut; delta gia thoat tuong doi (live - rig)/rig median / p10 / p90; so cum moi nhom A/B/C/D
  (dinh nghia A1_RLIVE_RUN3 muc 4.4); dem cum co markLOW cham stop ma kline LOW khong (va nguoc lai). Khong PnL.
- Moc tong ket: cum dong thu 30 (tinh tu 2026-11-24 07:00) hoac 2026-12-08 07:00 +07 (14 ngay), cai nao truoc => bao cao PILOT-M-R1
  (v12/pilot_m/PILOT_M_R1.md) lam dau vao cho quyet dinh 10.000; quyet dinh do can prereg rieng. M-G khong bao gio sinh bac.

## 8. M-K - van hanh (hang ngay, tu log pull + cron monitor Oracle)
Moi muc DAT/VI_PHAM; nguon trong ngoac:
- K1 JVM: dem dong banner "c.b.c.c.r.C3LiveRuntime: [C3-LIVE] khoi dong adapter=" (moi restart in 2-3 dong co chuoi nay, chi dem dong cua
  logger C3LiveRuntime, khong dem ban C3-LIVE-ALERT) = 0 trong ngay D, tru ngay 2026-11-26 >= 1 restart trong khung owner (pilot_on). Moi dong
  do phai co "adapter=LIVE ... c3_capital=<C> ... killSwitchArmed=true X14=true" voi C = 1000.0 truoc pilot / 5000.0 sau; sau do co
  "reconcile khoi dong XONG" va "khoi phuc sau restart: con 0 leg treo". Restart ngoai khung owner => VI_PHAM. (log)
- K2 TOM TAT monitor (dong "TOM TAT:" moi luot cron trong golive_monitor_cron.log, ngay D). VI_PHAM khi: bat ky dong co adapter != live,
  C3_CAPITAL sai von, push != ON, latch != NONE, jar != 01cfbb43, khan=KHAN, deadman != OK; HOAC khan_canh_bao != 0 / khan != 0 o >= 2 dong
  LIEN TIEP cung noi dung; HOAC khoang trong giua 2 dong TOM TAT > 10 phut. Ngoai le: trong thoi gian owner da drain theo de xuat (co ghi
  chep), KILL_SWITCH = CO va push = OFF la KY VONG (khong VI_PHAM). Ngoai le 2026-11-26: cac dong TOM TAT trong khung
  [lenh pilot_on bat dau ; dong TOM TAT dau tien co push=ON VA C3_CAPITAL=5000] (toi da 60 phut, ghi gio pilot_on tu PILOT_DAY_1126 / ghi
  chep owner) KHONG xet; qua 60 phut chua ve => VI_PHAM. Bo cham KHONG chep tmb / eq / dd / tmb0. (cron log Oracle)
- K3 RECON: moi gio co dong "[C3-LIVE-RECON] HOURLY khop:" (>= 23 / ngay tru gio JVM dung; RECON_EVERY_MS 3 600 000), streak tang dung 1
  moi dong trong cung JVM (ve 1 sau restart); 0 dong "LECH QTY", "van lech qty", "CHAN vao lenh", "leo thang UNKNOWN". (log)
- K4 X14: co dong "[TS-EXT] flag day=<D UTC> flag=(ON|OFF)" (final=true|false deu hop le; dong hang ngay tinh ~07:03 +07 co final=false)
  co thoi diem < D 07:25 +07, hoac (neu JVM khoi dong trong ngay) dong do sau banner khoi dong; KHONG co "[TS-EXT] chua co co ngay"; >= 23
  dong "[TS-EXT] status" / ngay (tru gio JVM dung); ghi gia tri flag (OFF/ON) vao bao cao (dieu kien MIEN_X14 ADD2). File thuc te =
  run/ts_ext_daily.csv.a1 (banner 20/11) - KHONG doc file tren 242; bang chung = dong log. (log)
- K5 pull242/<D>/COMPLETE co, check.txt STATUS=OK, missing= / fails= / errors= rong, log_minutes=1440. Ngay 2026-11-26: chap nhan STATUS=INCOMPLETE neu
  fails CHI gom feat_minutes / sel_minutes / psym_feat_minutes / psym_pred_minutes va moi gia tri >= 1440 - 20 x (so banner khoi dong
  C3LiveRuntime trong ngay); log_minutes=1440 va log_max_gap_min <= 15 van bat buoc. (pull)
- K6 0 dong " ERROR " va 0 dong chua "KHAN" trong log ngay D (moc so sanh: 0 / 0 trong 2026-11-19..11-24 07:00); 0 dong "[KILLSW] LATCH".
  Dong "[KILLSW] LATCH them code=<C>": C in {C6, A40} (FLATTEN) => DO; ma khac (NO_NEW_ENTRY) => VANG + bao owner NGAY. (log)
- K7 oracle_seen: KCD_CAU_TRUC (script chi ghi /var/lib/c3_oracle_seen/oracle_seen.log tren 242 + Telegram; PILOT-M khong doc 242). Bang
  chung gian tiep = K2 deadman=OK.

## 9. M-R - bao cao ngay
- Tep: ~/claude_master/v12/pilot_m/D_<yyyymmdd>.md (D = ngay cham). Dong dau: "PILOT-M D=<yyyy-mm-dd> cham_luc=<+07> bac=<XANH|VANG|DO>
  prereg=<commit> cong_cu=<commit|tay>"; truong prereg=<sha commit prereg> la BAT BUOC (thieu => bao cao khong hop le). Than <= 150 tu + bang 1 dong moi muc: | Muc | Trang thai | Mau | So chinh | Ghi chu |
  cho M-E, M-E0, M-I (I1..I12 gop, ghi I vi pham va I nao KCD_CAU_TRUC), M-T, M-D (D1..D4; D3 chi so), M-S (cung / theo doi), M-X, M-G, M-K
  (K1..K7). Trang thai dung DUNG 5 gia tri muc 0. Moi o KCD_CAU_TRUC / KHONG_CHAM_DUOC ghi ly do ngan.
- Dong mo ta equity (KHONG dung cham): tu dong "[KILLSW] HOURLY" cuoi ngay D: dd= va acct_dd=, min dd trong ngay, khoang cach toi A40 = dd -
  (-0,40) (A40_DD / C6_DD = -0,40, KillSwitchEngine :99/:101); chi ti le, khong in so tien.
- Kiem cheo truoc khi bao owner: MASTER tu tinh lai >= 3 so tu log goc (vd 1 dong SUBMIT -> C_ngam; 1 chuoi STOP -> I3; 1 dong HOURLY RECON
  -> K3) va ghi "kiem_cheo: <3 so> khop" trong bao cao. Chi bao owner so da qua kiem cheo.

## 10. Bac canh bao va hanh dong DE XUAT (owner quyet)
Moi (muc, trang thai) duoc gan dung 1 bac theo bang duoi; KCD_CAU_TRUC va KHONG_CO_SU_KIEN KHONG BAO GIO sinh VANG / DO.
- DO (bat ky): M-I bat ky I1..I12 VI_PHAM (tru I1 VANG "DATA"); M-E lech nhom E (muc 1.1) >= 1; M-T VI_PHAM; M-D D1 VI_PHAM; M-S muc cung
  VI_PHAM (tru VANG "TIER" / "AVAIL"); K3 VI_PHAM (RECON lech: LECH QTY / leo thang UNKNOWN / I11); co dong "vi the AM (short)"; CLOS ly do
  LIQUIDATION / ADL / STOP_LOST_61S / LOST_FOREIGN; LATCH FLATTEN (C6 / A40).
  Hanh dong de xuat (trong <= 2 h sau khi phat hien): owner chay dung mo moi
  `MODE=drain bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_live_off.sh` (fail-open, giu quan ly vi the; LUU Y: drain chan CA leg DCA
  - PUSH_OFF); MASTER dieu tra va bao cao trong 24 h; `golive_pilot_down.sh` CHI khi so phang (script tu choi khi con vi the). Khong tu
  dong lam gi.
- VANG (khong co DO va bat ky): M-E0 VI_PHAM; M-E lech KHONG GIAI THICH ngoai nhom E; I1 / D2 VANG "DATA"; M-S VANG "TIER" / "AVAIL";
  M-X cham nguong muc 6; K1 / K2 / K4 / K5 / K6 VI_PHAM (tru LATCH FLATTEN = DO); LATCH NO_NEW_ENTRY (+ bao owner NGAY); K2 latch != NONE
  hoac KILL_SWITCH co ngoai drain da ghi => bao owner NGAY; KHONG_CHAM_DUOC (thieu du lieu VAN HANH) keo dai qua 2026-(D+3) 09:00 +07
  ("thieu du lieu > 1 ngay"). Hanh dong: theo doi, ghi, bao owner trong bao cao ngay.
- XANH: moi truong hop con lai, gom: DAT, KHONG_CO_SU_KIEN, KCD_CAU_TRUC, KHONG_CHAM_DUOC chua qua han D+3, M-D D3 (theo doi), M-S muc theo
  doi, M-G.
- Hai ngay VANG lien tiep do CUNG mot muc (khong tinh KCD_CAU_TRUC) => MASTER de xuat owner xem xet nhu DO (owner quyet).

## 11. Gioi han (PILOT-M KHONG chung minh)
PnL ky vong / alpha; on dinh model giua cac lan retrain; khac biet thoat do MARK vs LAST, lay mau 10 s vs HIGH nen (D1/D2) - chi do o M-G;
moi buoc dat stop live = cong thuc(peak mau that) (khong co chuoi price_realtime 10 s - I1 chi chan tren); hanh vi 10.000; X14 dung gia tri
ALT_EW (MIEN ADD2); C1 so giay (MIEN); K7 avail+margin; lech hiem duoi tan suat mau; thu tu leg BIG_DOWN (BD_ORDER); gia tri hieu luc
MIN_MOMENTUM_15M / TS_MAX_GAP* / C2* / TIER_FLAT (env, khong doc). Do tre: cham dua tren pull ngay D (xong ~08:23 +07 ngay D+1) => vi pham
som nhat bao sau toi ~26 h (phan can Vision: them ~1 ngay); "bao ngay" cua ADD6 hieu la ngay sau khi pull / Vision co. Canh bao tuc thoi
van do golive_monitor / deadman / kill-switch jar dam nhan.

## 12. Cong cu
- tools/pilot_m/pilot_m_daily.sh (Oracle, chi doc pull242 + cron log; khong ket noi 242; khong in PnL / tien): parse log ngay D (+ trang
  thai cum luy ke), cham M-E0, M-I (I3, I4, I8-I12), M-T, M-D (D1), M-S (muc cung 1,3,6,7; 4,5 khi co exchangeInfo), M-X, M-K (K1-K6),
  ghi D_<yyyymmdd>.md + json voi 5 trang thai muc 0.
- tools/pilot_m/pilot_m_vision.sh: tai Vision klines/markPriceKlines 1m ngay UTC D cho symbol can (CHI SAU van ban owner Q1), cham I1, I2,
  I5, I6, D2, D3, L-S; ghi manifest sha256 zip.
- tools/pilot_m/rlive_day.sh: wrapper M-E (muc 1.2) tren nhanh moi tu add24_wt 8d397ce2, chay duoi
  `mkdir -p ~/claude_master/locks && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 <cmd>`, cham L-E/L-N/V10a/I7/D4/
  L-S2/M-G (CHI SAU Q1 + A1 duyet).
- Moi script: A1 duyet TRUOC khi dung ket qua (test: tiem 1 vi pham moi bat bien => VI_PHAM; ngay rong => KHONG_CO_SU_KIEN; thieu pull =>
  KHONG_CHAM_DUOC; chua co quyen / cong cu => KCD_CAU_TRUC). Cho toi khi co script duoc duyet: MASTER cham TAY theo dung dinh nghia nay cac
  muc "chi log"; muc can Vision / rig = KCD_CAU_TRUC.

## 13. Quyet dinh MASTER 2026-11-25
Q1 Phan can Vision >= 2026-11-24 (I1, I2, I5, I6, D2, D3, L-S, M-E, M-G) = KCD_CAU_TRUC cho toi khi owner xac nhan bang van ban
   (OWNER_DECISION_*). Khi co quyen / co wrapper duoc A1 duyet => cham LAI MOI ngay tu 2026-11-24 theo dung prereg nay (khong doi tieu chi,
   khong chon ngay).
Q2 Wrapper M-E lam sau, qua A1, KHONG chan cac muc chi-log; truoc do M-E / I7 / D4 / L-S2 / M-G = KCD_CAU_TRUC.
Q3 Bac DO => de xuat `MODE=drain bash ~/claude_master/w3/c3_ops6/ops/c3live/golive_live_off.sh` TRUOC (drain chan ca leg DCA);
   `golive_pilot_down.sh` chi khi so phang.
Q4 K7 = KCD_CAU_TRUC; bang chung gian tiep = K2 deadman=OK.
Q5 Dung sai M-T 120 s / 600 s (cua so (due - 2 s ; due + 120 s]); M-S muc cung 2 % (cong thuc sau sua B6: tierMul + availableBalance).
