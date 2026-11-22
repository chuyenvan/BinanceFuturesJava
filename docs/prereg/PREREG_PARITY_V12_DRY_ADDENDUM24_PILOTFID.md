# PREREG ADD24 (BAN NHAP, cho MASTER duyet) - do trung thuc jar PILOT <-> sim / replay truoc PILOT (T11)
Trang thai: BAN NHAP 2026-11-22 ~09:30 +07, agent thiet ke (Opus), CHI DOC. Chua commit, chua chay gi. Ten de xuat khi chot:
vz_e1_wt/docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM24_PILOTFID.md (noi chuoi ADD22 -> ADD23). Moi so trong ban nay CHOT khi MASTER commit;
sau commit KHONG doi tieu chi / dung sai / cua so / nhan lech; sua chi bang ERRATA commit TRUOC luot chinh thuc (nhu PREREG_E2E_REPLAY_V12 s2).
Nguoi viet KHONG doc log SUBMIT / fill / exit cua bot sau 2026-11-19 va KHONG doc dong du lieu printDone HO5 (chi header) => nguong ben duoi
khong bi anh huong boi ket qua se cham.

## 0. Yeu cau goc (trich nguyen van, bo dau)
- ADD23 s3.3 (85a48263, 11-17): "KHONG ap dung cho PILOT. Truoc PILOT bat buoc: so replay voi sim engine tren du lieu 2026 ("phuong an A"
  cua prereg replay s0) va mot phep thu do trung thuc cua rig khong can ngoai le (vi du nap gia theo giay tu nguon doc lap), co prereg rieng."
- ADD23 s3.1: "Doi jar => ngoai le het hieu luc, phai chay lai phep thu." (jar pilot 01cfbb43 != jar 64180356 cua luot 11-17).
- PREREG_E2E_REPLAY_V12 s0: "Truoc PILOT ("phuong an A", prereg rieng): dung sim A3 tren cua so 2026 va so replay <-> sim engine.
  Chua co A => khong bat pilot."
- GATE_LIMITS_MICRO A1: "So voi sim tren du lieu 2026 la dieu kien truoc PILOT."
- PILOT_READINESS_1121 T11: "ADD24 (ten de xuat): prereg rieng + chay "replay <-> sim engine tren du lieu 2026" + "phep thu do trung thuc
  rig KHONG can ngoai le E2" TREN DUNG jar se pilot; A1. HO5 (sim A3 2026) da co ha tang sim, CHUA so voi replay jar" | BB | phu thuoc
  "chot jar (Q3)" | cong "prereg 2 (MASTER) + chay 8-12 (Opus) + A1 3". Lo trinh (a) buoc 5: "MASTER viet prereg ADD24 (T11) -> Opus chay
  replay<->sim 2026 + fidelity tren jar 01cfbb43 -> A1 (~1-1,5 ngay)". "Rui ro neu ADD24 TRUOT => dung, khong pilot (khong tune)."
- PILOT_READINESS T12: gate PILOT phai ghi "ADD24 ket qua". OWNER_DECISION_PILOT_1121_ADD1 s2: "... -> T9 / T11 (ADD24) -> du 7 ngay micro
  ... -> gate PILOT". Jar da chot: hotfix md5 01cfbb4324fb4a10b615dc3c976ddc73 (ADD1 Q2).
- Lien quan (KHONG phai ADD24): T9 sizing_iv = golive_first_trade_check (dung sai 2 %, file first_trade/SIZING_IV_<ts>.md); g_exec / g_exit
  = Q4_OWNER (ADD1 Q3). ADD24 KHONG thay T9 va KHONG cham truot gia (g_exec) - chi do jar co lam DUNG nhu sim / dac ta khong.

## 1. Da kiem roi - ADD24 KHONG lam lai (chi dung lai / doi chieu)
| Da co | Phu gi | Gioi han con lai (ADD24 phu) |
|---|---|---|
| E2E replay 11-17 (harness def1f034, fx1105, jar 64180356): C1,E1,S1,D1 S-DCA,X1,F1,K1 PASS so REF numpy; E2 FAIL (ADD23) | logic jar = dac ta A3 tren 9 ngay 11-05 | jar khac (01cfbb43); khong so sim engine; E2 can ngoai le |
| Parity hang ngay G-MICRO (P1/S1V, parity_v11 / parity_v12_gmicro) | feature / p15 / S1 live = backtest | khong so sizing / DCA / exit voi sim (GATE_LIMITS D2) |
| T2a / T2c (R1_S1_ABLATION, class nhanh dev) | exit 2 741 symbol-ngay 0 lech; sizing 5 885 leg trung bit | KHONG tren jar live; KHONG du lieu 2026 |
| HO5 Lane L (RESULT_HO5_A3_2026): sim A3 2026-01..09-30, 3 model LIVE (fold_20 8ec99757, S1 af706dc6~511add62, net015 e65e683b) | ky vong 23 %/nam | chua bao gio so voi jar |
| first_trade_check (T9) | budget +-2 % cong thuc, stop c3s- sau arm | dung sai rong; khong so DCA/exit/thu tu |
| HOTFIX_KS_DEV: 01cfbb43 = 64180356 + DUNG 1 entry KillSwitchEngine.class (8410 entry md5 giong) | tuong duong byte duong quyet dinh | phai chung minh lai tren stub (C0) |

## 2. Muc tieu + gia thuyet
H0 (can bac bo de PASS = gia thuyet "jar co the lech"): voi CUNG dau vao, jar pilot (01cfbb43, ban stub) ra quyet dinh khac sim A3 / dac ta.
Gia thuyet ADD24 chung minh (neu PASS):
- G1 (R-SIM, du lieu 2026 Q3, da mo): nap cho jar cung chuoi p15 thi truong + cung danh sach lenh vao cua sim HO5 Lane L s123, jar
  (a) mo gate o MOI phut sim vao lenh, (b) size leg theo cung ham sim dung (chuan hoa theo von), (c) DCA dung bac, (d) arm / trailing /
  time-stop 168 h / X14 336 h / thoat cung ly do, cung phut (+-dung sai B1), gia thoat trong dung sai. => So HO5 (~23 %/nam) la uoc luong
  cho DUNG logic lenh ma jar se chay (khong phai cho mot engine khac).
- G2 (R-LIVE, du lieu van hanh micro 2026-11-19 09:31 -> T_cut): tren chinh dau vao live da ghi (sel_dump, buffer gate, exchangeInfo,
  MINUTE-INCOMPLETE), rig chay jar stub ra CUNG tap (phut, coin, level, legIdx, thu tu) nhu lenh that; moi cum budget that nam trong bao
  co che (cache equity 60 s, gia realtime) - KHONG can ngoai le; DCA / arm / dat stop / thoat cua lenh that trung rig trong dung sai.
ADD24 KHONG chung minh: (i) alpha / ky vong loi nhuan dung trong tuong lai (model gia dan - owner chap nhan); (ii) truot gia / chat luong khop
(g_exec, g_exit = Q4_OWNER); (iii) feature / p15 / S1 live = sim (parity G-MICRO phu); (iv) selector chon coin tu toan universe = sim (chi
neu S-SEL stretch chay); (v) nguon ALT_EW live cho X14 (owner MIEN, kiem log hang ngay - ADD2); (vi) kill-switch C6/A40 o 10 000, A-02 ha
von, B-09 reboot (T5/T20); (vii) hanh vi o von 10 000 tren san that (micro la 1 000; R-LIVE-10K chi bao cao); (viii) PnL bat ky.

## 3. Doi tuong: jar STUB tuong duong byte (khong key)
- Nguon: v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2_hotfixks (md5 01cfbb43..., mode 600). KHONG giai nen / KHONG doc noi dung 8 entry co
  the chua key, xac dinh bang TEN (HOTFIX_KS_DEV): PrivateConfig, BinanceApiInternalFactory, ClientSingleton, BinanceFuturesClientSingleton,
  C3LiveClient, C3LiveCanary (+ inner) - danh sach day du (ten entry) DEV ghi vao manifest stub TRUOC khi tao.
- Tao stub (cach v12/hfx_jar/patch_jar.py): chep nguyen byte nen moi entry khac; 8 entry tren THAY bang class bien dich tu stub PrivateConfig
  (khong key) o worktree c3_hotfix 76134a52. File stub o /dev/shm/add24/jar (tmpfs, xoa khi xong), chmod 600.
- Cong C0 (truot => HUY luot, khong cham): (a) danh sach + thu tu entry stub == 01cfbb43; (b) md5 tung entry == 01cfbb43 ngoai dung danh
  sach 8 ten; (c) KillSwitchEngine.class md5 d560bd8d1e55bcd4d82e6156e45b8f04; (d) 10 class quyet dinh (C3LiveEntry, C3LiveRuntime,
  LiveGridSizing, LiveDcaGridC3, DcaUtils, EntryGate, AIRejectFilter, GatePreFilter, TrailingStopManager, LiveGateRollingRatio) +
  C3MainEquity + KillSwitchEngine nap tu stub (ClassLoader.getResource); (e) java chay trong bwrap --unshare-net (khong mang) - log 0 dong
  ket noi ra ngoai; adapter Fake / dry; LIVE_IS_SHADOW_HOST=true. TUYET DOI khong chay main() cua jar that.
- C0b (tai lap, re): chay lai luot chinh thuc 11-05 (fx1105, harness def1f034, CHI doi md5 jar mong doi -> md5 stub + manifest) R0 + S-DCA
  + FIN-INJ: moi dong quyet dinh (symbol, phut, legIdx, budget, qty, stopPrice, ly do thoat) == output luot 11-17
  (~/claude_master/e2e_v12/out1105_1117_0132) - budget lech tuong doi <= 1e-9. Chung minh stub = jar live o duong quyet dinh + harness tai lap.

## 4. Thanh phan 1 - R-SIM: replay jar <-> sim engine HO5 tren 2026 Q3 (du lieu <= 2026-09-30)
- Sim chuan: HO5 Lane L seed s123 (~/claude_master/w3/ho5/out/ho5-a3-l26-s123: printDone.csv sha256 c5693122799ca9c0..., md5 b8a77a46;
  prof_run.properties; sim jar cc0f9d11). Ly do s123: luot tai lap byte (rep3/rep4) lam tren s123; lenh 2026 gan nhu trung giua 8 seed
  (ADD1 A3). Dung 1 seed (tat dinh).
- Cua so chinh thuc OW1: lenh sim co start trong [2026-07-01 00:00 ; 2026-09-16 00:00) +07 (=> du 336 h du lieu cho X14 toi 09-30).
  Warm-up buffer gate: p15 thi truong cua sim 2026-04-02 -> 2026-06-30 (90 ngay). Cua so DEV (moi go loi / can chinh harness, converter,
  REF chi lam o day): lenh start trong [2026-04-01 ; 2026-06-15), warm-up p15 2026-01-01 -> 03-31.
- Dau vao rig (giong nhau giua sim va rig, ghi md5 vao result.json): p15 thi truong 2026 (ONNX fold_20, md5 file 64f66a15..., Kaggle chain
  ho5-a3-chain26 - chi tai doan 01-01..09-30, loc truoc khi ghi dia); kline 1m Vision cua DUNG cac symbol co trong printDone cua cua so
  (tu start - 2 h toi end + 2 h, toi da 09-30), exchangeInfo A1 20261027 (nhu bins A3), co TS_EXT 2026 (~/claude_master/tsx/ho/ho_flags.json,
  4 khoang). Moi phut sim vao lenh => mot dong "sel" tong hop: cac symbol sim vao o phut do, rank theo thu tu dong printDone, gateValue/p15
  = gia tri cua sim tai phut do. Dinh dang sel_dump (gateValue theo symbol hay theo thi truong) DEV phai xac minh tren cua so DEV; neu can
  du lieu theo symbol ma HO5 khong co => S-G = INSUFFICIENT (ghi errata TRUOC luot chinh thuc, khong doi tieu chi khac).
- Che do "theo vet sim" (1A, BAT BUOC): rig KHONG tu chon coin - chi duoc cac ung vien tren; rig tu quyet gate (LiveGateRollingRatio
  nap p15 sim + buffer warm-up sim), sizing (C3_CAPITAL = 10 000, env chien luoc 242), DCA grid, trailing, time-stop, X14, thoat tren kline
  Vision 1m (FakeExchange1m). Sim BIG_DOWN: nap dong BIG_DOWN tu printDone level=BIG_DOWN (neu co) theo cung cach.
- Sizing so theo HAM, khong so so tien (sim lai kep, live von co dinh - GATE_LIMITS B3): voi moi cum sim, tinh U_sim(t_start) =
  sum margin cac cum sim dang mo tai t_start / E_sim(t_start); E_sim = dinh nghia von size cua sim engine - DEV doc code
  SimulatorMarketLevelTicker1MStopLoss (sim jar cc0f9d11 / nguon tuong ung) va GHI cong thuc vao errata TRUOC luot chinh thuc (CHUA XAC MINH:
  von size sim la balance da thuc hien hay MTM). Chi so: margin_sim(leg 0) so f_jar(E_sim, U_sim, legIdx=0) goi LiveGridSizing /
  managerBudget TU JAR STUB (khong viet lai).
- S-SEL (stretch, KHONG bat buoc, chi bao cao): neu dung duoc sel top-24 tu bins A3 2026 + p15 + net015 cua HO5 cho cua so OW1, rig chon
  coin tu do; Jaccard (phut, symbol) vs sim sau loai A1. Khong dat => chi ghi; ADD24 khong cham.
- Khong in PnL / ROI / so du cua R-SIM (HO5 da cong bo); chi so lech quyet dinh, ham size, gia thoat tuong doi.

## 5. Thanh phan 2 - R-LIVE: do trung thuc tren lenh that (micro) - KHONG can ngoai le
- Cua so OW2: 2026-11-19 09:31 +07 (bat micro) -> T_cut. T_cut CHOT = 2026-11-24 07:00 +07 (ngay pull242 2026-11-23 COMPLETE; neu pull 11-23
  INCOMPLETE => T_cut = moc 07:00 cua ngay COMPLETE gan nhat truoc do; KHONG keo dai sau khi da xem ket qua). Gom moi lenh that trong OW2
  (24 cum 21/11 + lenh den T_cut). Cum chua dong tai T_cut: chi cham entry / sizing / DCA / arm / stop toi T_cut.
- Dau vao rig = du lieu van hanh cua chinh bot (pull242/<D>/, da co tren Oracle, KHONG ket noi 242): sel_dump (1 440/ngay), feat_dump chi
  de doi chieu so dong, run/gate_ratio_live.bin.gz (buffer gate live - chi dung lam dau vao, khong in / khong thong ke noi dung),
  logs/full.log*.gz (live: SUBMIT / skip / MINUTE-INCOMPLETE / MINUTE-FIN-EXCL / C3-LIVE-FILL / C3-LIVE-TRAIL / -4130 / C3-LIVE-EQ / KS),
  exchangeInfo snapshot cua live (neu pull co; khong co => Vision/API cong khai ngay gan nhat <= 11-19, ghi md5). Gia: kline 1m + markPrice
  kline 1m Vision futures UM cho DUNG symbol live da giu / ung vien rank <= 24 cua cac phut co SUBMIT, chi trong OW2. Env chien luoc: danh
  sach trang (bang AUDIT_GOLIVE_1116_D s1) chup MOI (xem Q6), override khai truoc: LIVE_ADAPTER=dry, C3_CAPITAL=1000, LIVE_IS_SHADOW_HOST=true,
  duong dan du lieu.
- Cac luot: L0 (chinh, FakeExchange1m, von 1 000, tu do: so cua rig tu tien hoa); L0-FOLLOW (so rig DONG BO theo FILL that moi phut - dung
  de phan xu nhan CASCADE); L0-DRY (DryGateway production, cung tieu chi entry/size); REF numpy doc lap (mo rong check_ref.py cua 11-17: them
  bao size s9.3, khong import Java); bao cao kem (KHONG cham): L-10K (von 10 000, dem leg / BUDGET_SMALL), L-SIMQ (q sim thay buffer live, do B2).
- Phut thieu: pull 2026-11-19 INCOMPLETE (feat/sel 1165/1440) => phut khong co sel_dump = NO_INPUT (nhan N1); MINUTE-INCOMPLETE /
  MINUTE-FIN-EXCL cua live (vd 4 phut dem 20/11) NAP VAO rig nhu dau vao (tiem tu dong log, khop phut + symbol) => mong doi rig cung chan.

## 6. Du lieu + holdout (giam lo toi thieu)
| Thanh phan | Du lieu doc | Thuoc pham vi da mo? | Ghi ra | Che / cam |
|---|---|---|---|---|
| R-SIM DEV | 2026-01-01..06-30 (p15, kline sym cua sim, printDone) | U1 (HO5) da mo + da cong bo | lech quyet dinh | PnL |
| R-SIM OW1 | 2026-04-02..09-30 | U1 da mo; dung lai artefact HO5 | lech quyet dinh, ham size, gia thoat % | PnL / ROI / DD / win-rate |
| R-LIVE | 2026-11-19 09:31 -> T_cut: du lieu van hanh cua bot + kline/mark cua symbol bot giu / ung vien | KHONG thuoc U1-U4b (du lieu van hanh + gia thi truong >= 10-01) => Q1 | lech quyet dinh / size / gia vao-ref / gia stop / ly do thoat | PnL sim/rig, tong lai lo, thong ke hieu qua; khong doc thi truong 10-01..11-19 tru buffer gate (dau vao, chi md5) |
| (KHONG lam) sim engine qua 10-11/2026 | can kline/feature 10-01..11-24 len Kaggle + chay sim => lo PnL sim giai doan niem phong | ngoai U3 | - | MASTER KHONG tu quyet; neu muon => xin owner (Q2) |
- R-SIM khong can 10-11: warm-up dung p15 sim 90 ngay TRUOC OW1 (khong phai buffer live) => khong co trang thai nao phai dung qua 10-11.
- R-LIVE khong can sim: so live vs rig (cung jar) + REF dac ta. "Sim tren cung du lieu 21/11" = REF numpy (dac ta A3) + G1 (rig = sim
  engine tren Q3). Day la chuoi bac cau: live ~ rig (R-LIVE), rig ~ sim (R-SIM), rig ~ dac ta (REF + C0b).
- Precedent (de owner biet, khong phai ly do tu quyet): parity hang ngay va E2E 11-05 da doc du lieu van hanh + Vision >= 10-01 cho muc
  dich van hanh truoc khi co HOLDOUT_UNSEAL. R-LIVE van ghi la diem PHAI hoi owner (Q1).

## 7. Diem lech DA BIET - xu ly trong thiet ke (khong duoc dung lam ly do sau)
| # | Diem lech | Xu ly trong ADD24 | Co phai nhan "giai thich duoc"? |
|---|---|---|---|
| K1 | B2 gate live chat hon (buffer 90 ngay nhiem, q ~0,0095 vs ~0,0075; owner MIEN) | R-LIVE dung DUNG buffer live (so live voi chinh no); R-SIM dung buffer warm tu p15 sim. L-SIMQ chi bao cao so lenh chenh | KHONG - B2 khong the giai thich lech nao |
| K2 | X14 / ALT_EW live chua doi chieu (owner MIEN + kiem log hang ngay) | R-LIVE: X14 (336 h) khong the kich trong OW2 -> khong cham; R-SIM: rig nap co TS_EXT cua sim -> kiem LOGIC X14 cua jar | KHONG trong R-SIM; R-LIVE: khong ap |
| K3 | C1 so giay LEGACY-DCA / skipFull chan lenh that (owner MIEN, theo doi) | rig khong co so giay. Lenh rig co ma live khong co: giai thich DUOC chi khi log live co dong skip so giay (skipFull / liveBookFull / U_MAX tu ShadowBookC3) DUNG phut + symbol | CO (nhan N6), dem + bao cao |
| K4 | Quyet dinh o giay ~6 cua phut sau; sizingPx = price_realtime (D-03) | so theo PHUT nen quyet dinh; size cham bang BAO s9.3 (px trong [low,high] nen phut quyet dinh) | KHONG phai nhan - da nam trong dung sai |
| K5 | 4 phut MINUTE-INCOMPLETE dem 20/11 (guard bo entry) | tiem vao rig tu log nhu dau vao; mong doi rig cung chan | CO chi khi tiem khong lam duoc (nhan N2) |
| K6 | San tu choi closePosition stop thu 2 (-4130) -> stop qty + reduceOnly | khac KIEU stop chi duoc khi log co -4130 cung symbol; GIA stop van phai trong 2 tick | CO cho kieu (N7), KHONG cho gia |
| K7 | Sizing min(C3_CAPITAL, equity c3, avail + margin), cache 60 s | BAO [b_lo,b_hi] s9.3 (C_eff min/max theo mark 1m trong 3 phut truoc quyet dinh); avail + margin coi khong rang buoc khi tmb tk con >= 2 x C3_CAPITAL (so monitor c3sub_tmb_hist) | KHONG phai nhan |
| K8 | Trailing nhip 10-15 s trong nen (B1; ARM_CUNG_NEN 11-05: JCT som 4') | dung sai phut arm / thoat + nhan N8 khi duong gia nhip cua REF xac nhan | CO (N8), gioi han so luong |
| K9 | Live: rot WS / gia cu toi ~18 s (C2) | khong co trong rig (Vision sach); lech do gia cu => KHONG GIAI THICH -> bao cao rieng, xem s9 L-X | KHONG |
| K10 | Swap jar 20/11 06:17 (restart JVM) | phut JVM khong chay (log khoi dong / khoang trong) = nhan N3 | CO (N3) |
| K11 | Sim compound vs live von co dinh (B3); sim khong loc A1 (B4) | R-SIM so HAM size, khong so tien; ung vien do sim dua (S-SEL moi dung toi A1) | KHONG phai nhan |

## 8. Nhan lech (danh sach DONG - chi cac nhan nay; moi lech khac = KHONG GIAI THICH)
Moi nhan can BANG CHUNG may doc duoc (dong log live dung phut + symbol, hoac luot L0-FOLLOW), gan tu dong boi script, A1 kiem lai 100 %.
- N1 NO_INPUT: phut khong co sel_dump trong pull. SUBMIT live roi vao phut N1 => SUBMIT do = INSUFFICIENT (khong cham, khong tinh PASS).
- N2 INCOMPLETE_NOINJ: live co [MINUTE-INCOMPLETE]/[MINUTE-FIN-EXCL] dung phut (+symbol) nhung khong tiem duoc vao rig (ghi ly do).
- N3 JVM_DOWN: phut live khong co JVM (khoang trong log / dong khoi dong), vd swap jar 20/11.
- N4 EXCH_REJECT: leg live bi san tu choi / het han (dong REJECT / EXPIRED / "tu choi cid=" cung cid hoac cung symbol <= 60 s sau SUBMIT).
- N5 CASCADE: lech chi do so khac sau mot lech DA gan N1-N4/N6; dieu kien: L0-FOLLOW (so dong bo FILL that) KHONG co lech do.
- N6 C1_PAPER: live co dong skip vi so giay (skipFull / liveBookFull / U_MAX doc ShadowBookC3) dung phut + symbol.
- N7 STOP_4130: khac kieu stop (closePosition vs qty+reduceOnly) khi log co -4130 cung symbol truoc do.
- N8 B1_INTRABAR: phut arm / doi SL / thoat lech <= 2 phut va REF-nhip (noi suy nhip trong nen nhu jar) cho cung phut voi rig/live.
Gioi han: tong N6 > 3 cum hoac > 10 % SUBMIT rig => van tinh theo nhan nhung MASTER bao owner (C1 dang chan lenh that dang ke). Tong N8 > 10 %
cum => tieu chi tuong ung FAIL.

## 9. Chi so + nguong (chot truoc)
### 9.1 Bang
| ID | TP | Chi so | Nguong PASS | Mau toi thieu (duoi => INSUFFICIENT) | Bat buoc |
|---|---|---|---|---|---|
| C0 | chung | stub tuong duong byte + 12 class tu stub + khong mang + banner [LIVE-SIZING]/[LIVE-DCA-GRID]/[MINUTE-FIN]/[GATE-RATIO] =true + ten bien env thieu = rong | 100 % | - | BB (truot = HUY, khong cham) |
| C0b | chung | tai lap luot 11-05 tren stub (R0, S-DCA, FIN-INJ) | moi dong quyet dinh == 11-17; budget <= 1e-9 tuong doi | 24 leg | BB |
| S-G | R-SIM | phut sim vao PREDICT la phut gate MO cua LiveGateRollingRatio (jar) | 100 % (khong co nhan nao ap) ; bao cao ti le phut mo khong co lenh sim | >= 50 phut vao | BB |
| S-SZ | R-SIM | abs(margin_sim - f_jar(E_sim,U_sim,0)) / margin_sim, leg 0 moi cum | <= 1e-3 o >= 90 % cum VA <= 5e-3 o 100 % | >= 50 cum | BB |
| S-X | R-SIM | (a) ly do thoat cum 1 leg (TRAIL / TIME_STOP 168 h / X14 336 h) == sim; (b) phut thoat; (c) gia thoat rig vs sim tp | (a) 100 %; (b) >= 95 % cung phut, con lai <= +-1' hoac N8; (c) TB Delta(rig-sim)/sim in [-0,8 % ; 0], tung cum >= -1,5 % hoac <= 2 tick (tru N8) | >= 30 cum thoat, >= 1 time-stop, >= 1 trail; X14: >= 1 neu sim co cum tren ngay TS_EXT | BB |
| S-D | R-SIM | cum sim co DCA (level DCA / so leg > 1): rig co leg DCA dung bac, phut den han +-1, legIdx | 100 % | >= 1 su kien; 0 => INSUFFICIENT, phu boi C0b S-DCA | BB co phu |
| S-E | R-SIM | gia vao rig (Fake1m) vs sim entry | chi bao cao (TB, p90 bps) | - | khong |
| S-SEL | R-SIM | Jaccard (phut,symbol) chon coin tu do | chi bao cao (de xuat >= 0,95) | - | khong (stretch) |
| L-E | R-LIVE | tap (phut quyet dinh, symbol, level, legIdx) SUBMIT live vs L0 + thu tu trong phut | 0 lech KHONG GIAI THICH; thu tu 100 % | >= 20 SUBMIT cham duoc | BB |
| L-N | R-LIVE | phu dinh: moi phut co input ma live KHONG SUBMIT, rig cung khong (va nguoc lai) | 0 lech KHONG GIAI THICH | toan bo phut OW2 co input | BB |
| L-S | R-LIVE | budget live trong BAO s9.3 (+-1e-5 tuong doi); U_before log == sum margin leg live truoc do / C_eff (<= 1e-6); px ngam = notional/qty trong [low,high] nen 1m phut quyet dinh; qty = floor theo stepSize; legIdx dung | 100 % SUBMIT | >= 20 | BB |
| L-S2 | R-LIVE | budget L0 (rig tu do) vs live | <= 5e-4 o >= 90 % VA <= 2e-3 o 100 % (tru N4/N5) | >= 20 | BB |
| L-P | R-LIVE | gia khop vao live vs ref (close nen quyet dinh) | chi bao cao median / p90 (bps); median > 30 bps => MASTER bao owner (g_exec) | - | khong |
| L-D | R-LIVE | DCA live <-> L0: bac, phut den han +-1, legIdx; khong leg DCA nao truoc bac | 100 % | >= 1; 0 => INSUFFICIENT, phu boi C0b S-DCA + S-D | BB co phu |
| L-T | R-LIVE | arm trailing (symbol, phut) live vs L0 | >= 90 % cung phut; con lai <= 2' (N8); 0 arm thieu / thua | >= 5 arm; duoi => INSUFFICIENT, phu boi S-X + C0b X1 | BB co phu |
| L-SL | R-LIVE | gia stop sau moi lan dat / doi (live vs L0); co stop c3s- sau arm | abs <= 2 tick hoac <= 0,1 %; kieu khac chi khi N7; 100 % cum da arm co stop | >= 5 lan dat; duoi => INSUFFICIENT, phu nhu L-T | BB co phu |
| L-X | R-LIVE | thoat: ly do (cum 1 leg), phut, gia khop thoat live vs stop / L0 | ly do 100 %; phut >= 90 % cung phut, con lai <= 2' (N8); TB Delta(live-L0) in [-0,8 % ; +0,2 %], tung cum >= -1,5 % hoac <= 2 tick | >= 5 thoat; duoi => INSUFFICIENT, phu nhu L-T | BB co phu |
| L-K | R-LIVE | rig: 0 ERROR / latch / KHAN; live: moi -4130 co stop thay the <= 2 nhip | 100 % | - | BB |
Ghi chu dung sai: X1 / T2a (11-17: TB gia thoat -0,40 %, stop lech toi da 0,97 tick) va 11-05 E2 (lech budget toi da 1,35e-4 do co che) la
can cu; L-S la phep thu KHONG can ngoai le (co che nam trong bao, khong khop nguoc tu ket qua); L-S2 bat loi lon hon co che.
"KHONG XAY RA" KHONG BAO GIO tinh la PASS.

### 9.2 Dinh nghia L-N (tranh tautology)
Rig va live cung doc sel_dump live => L-E/L-N kiem tang LENH (gate rolling + C3LiveEntry + book + guard) tren cung dau vao; KHONG kiem
feature/p15/S1 (parity G-MICRO). Phut "co input" = phut co sel_dump va JVM live chay (khong N1/N3).

### 9.3 Bao size [b_lo, b_hi] (L-S)
b = min(0,045 C_eff ; 0,0225 x C_eff x (1 - U_before/0,6) x ratio(legIdx)) (ratio tu DcaUtils.gridLegWeightRatio voi weights 1,1,1,1, SCALE 6);
C_eff = min(C3_CAPITAL, E_c3) (avail+margin khong rang buoc, K7); E_c3 = C3_CAPITAL + PnL da thuc hien c3 (FILL live truoc do, gom phi) +
sum_open qty x (mark - entry). Bien: mark lay min / max cua markPrice kline 1m Vision trong [phut quyet dinh - 2 ; phut quyet dinh] (phu TTL 60 s +
do tre) => E_lo / E_hi => b_lo / b_hi. U_before lay tu log (da kiem nhat quan L-S). Leg dau tien khi so rong: b == 0,0225 x C3_CAPITAL
(bao suy bien thanh diem).

## 10. INSUFFICIENT, ket luan, he qua
- Trang thai moi chi so: PASS / FAIL / INSUFFICIENT (FAIL > INSUFFICIENT > PASS khi gop). INSUFFICIENT khong bao gio thanh PASS.
- "BB co phu": INSUFFICIENT chap nhan duoc CHI KHI muc phu (ghi trong bang) PASS. Mau R-LIVE hien biet: ~24 cum vao (21/11), thoat rat it,
  time-stop 168 h cua cum 21/11 roi sau T_cut => du kien L-X / L-T co the INSUFFICIENT -> bang chung thoat dua vao S-X (R-SIM) + C0b.
- ADD24 = PASS <=> C0, C0b, S-G, S-SZ, S-X, L-E, L-N, L-S, L-S2, L-K PASS VA moi "BB co phu" PASS hoac INSUFFICIENT-co-phu.
- ADD24 = FAIL <=> bat ky chi so BB nao FAIL (ke ca L-X / L-T FAIL du mau nho: FAIL tren lenh that khong duoc "phu").
- ADD24 = INSUFFICIENT <=> khong FAIL nhung co BB INSUFFICIENT khong phu (vd S-G khong dung duoc dau vao, L-E < 20 SUBMIT cham duoc).
- He qua: PASS => T11 dat; gate PILOT ghi "ADD24=PASS ref=<commit ket qua> jar=01cfbb43". FAIL => KHONG pilot, khong tune, khong doi tieu chi;
  viec: (1) A1 doc lap phan xu: loi jar hay loi harness (loi harness => errata + chay lai, bao CA HAI luot nhu PREREG_E2E s2; loi jar =>
  FAIL giu nguyen); (2) loi jar => DEV sua o nhanh moi -> jar moi -> ADD24 chay lai tu dau tren jar moi (L1-L8 neu doi jar khi live);
  (3) MASTER bao owner + de xuat lich moi. INSUFFICIENT => KHONG tu dong pilot; MASTER trinh owner danh sach muc thieu + rui ro; chi pilot khi
  owner chap nhan BANG VAN BAN (commit, nhu Q4_OWNER) - hoac doi them du lieu R-LIVE (T_cut moi = ERRATA truoc khi cham lai).
- Sai lech PnL ky vong: ADD24 khong cham; neu PASS van giu ky vong HO5 ~23 %/nam CI rong (owner da chap nhan).

## 11. Cach chay an toan
- Ai: agent DEV (Opus) tren Oracle - port harness, converter, REF, chay DEV; agent RUN (Opus, co the la DEV) chay luot chinh thuc 1 lan;
  A1 (Opus doc lap, khong phai DEV) duyet harness TRUOC luot chinh thuc va kiem ket qua SAU. Owner: KHONG can chay gi (tru Q6 neu chon
  chup env bang script owner). KHONG ket noi 242 (dung pull242 da co tren Oracle). Khong subagent long nhau.
- Jar: CHI stub s3 trong bwrap --unshare-net; classpath = stub + test-classes harness; harness tu choi chay neu md5 stub != manifest.
  KHONG mvn tren worktree c3_hotfix (chi doc); harness o worktree rieng (vd ~/claude_master/w3/add24_wt tu def1f034), commit WIP.
- Tai nguyen: java -Xmx3g duoi flock ~/claude_master/oracle_heavy.lock (khong long flock); fixture + stub + kline/mark tai ve o
  /dev/shm/add24 (tmpfs 12 GB, tran 6 GB, kiem truoc: MemAvailable >= 10 GB); dia ~/: CHI ket qua (result.json, bang md, log rig nen)
  tran 300 MB; truoc moi buoc: df / >= 15,3 GB trong (hien ~15,6-16 GB) else DUNG; xoa /dev/shm/add24 khi xong (sau khi luu md5 manifest).
  Kaggle chi TAI (p15 2026, kline Q3 symbol can) - KHONG chay kernel sim moi.
- Thoi gian chay uoc tinh: C0 + C0b ~20'; R-SIM DEV + OW1 (~110 cum Q3, kline loc symbol) < 30' moi luot; R-LIVE L0 / L0-FOLLOW / L0-DRY
  (5 ngay) < 15' moi luot; REF numpy < 10'.
- Cong kiem chung TRUOC khi cham (truot => khong cham, sua dau vao, khong doi tieu chi):
  V1 md5 / sha moi dau vao ghi result.json (printDone s123, p15, kline, mark, sel_dump, buffer, exchangeInfo, env whitelist, stub, harness HEAD);
  V2 kline: du phut cho moi symbol-cua so (thieu => liet ke, cum lien quan = INSUFFICIENT); khong ts trung / nguoc;
  V3 phu thoi gian: R-SIM chi ts <= 2026-09-30 23:59; R-LIVE chi ts trong OW2 (assert tu dong - vuot = HUY luot);
  V4 so dong SUBMIT live doc duoc == so dong [C3-LIVE] SUBMIT trong log (dem doc lap bang grep -c) va == first_trade state (neu co);
  V5 banner cau hinh (C0) + tap ten env thieu = rong; V6 rig: so phut xu ly == so phut input; 0 exception nuot;
  V7 REF numpy khong import Java (kiem tinh), viet tu dac ta truoc luot chinh thuc (commit).
- Audit: A1 doc lap (1) duyet harness + converter + REF + script gan nhan TRUOC luot chinh thuc (A1_ADD24_HARNESS.md);
  (2) SAU luot: tai tinh >= 5 so tu file tho (1 budget, 1 bao size, 1 phut gate, 1 gia stop, 1 ly do thoat), kiem 100 % nhan N1-N8,
  ket luan PASS/FAIL/INSUFFICIENT doc lap (A1_ADD24_RESULT.md). MASTER tu kiem >= 3 so tu log tho truoc khi bao owner.
- Chay chinh thuc 1 LAN (khoa OFFICIAL_ADD24.lock nhu 11-17). Lot ket qua roi moi phat hien loi harness => errata + chay lai, bao CA HAI.

## 12. Lich (pilot som nhat 2026-11-26 09:31 +07)
| Moc | Viec | Ai | Gio cong |
|---|---|---|---|
| 11-22 toi | MASTER duyet ban nhap, tra loi Q1-Q8 (owner: Q1, Q2, Q5), commit prereg | MASTER / owner | 1-2 |
| 11-23 | stub + C0/C0b; port harness R-LIVE (fixture builder OW2, tiem MINUTE-INCOMPLETE, L0-FOLLOW, gan nhan); REF bao size; DEV tren fx1105 + fx1030 | DEV | 6-8 |
| 11-23 // | R-SIM: tai p15 2026 + kline Q2/Q3 loc symbol; converter printDone -> sel tong hop; xac minh von size sim (errata); DEV cua so Q2 | DEV (2) | 6-8 |
| 11-24 | A1 duyet harness (truoc chinh thuc); pull 11-23 COMPLETE (~08:30) => T_cut co dinh | A1 | 3 |
| 11-24 chieu / 11-25 sang | luot chinh thuc R-SIM OW1 + R-LIVE OW2 (Vision 11-23 thuong co tu ~11-24) | RUN | 2 |
| 11-25 | A1 kiem ket qua; MASTER ket luan; ghi vao gate PILOT (T12) | A1 / MASTER | 3-4 |
Tong ~20-25 gio agent trong ~3 ngay lich: KHA THI nhung SAT - khong con dem cho 1 vong errata. Rui ro lich lon nhat: (a) converter
printDone -> sel / dinh dang gateValue (S-G); (b) cong thuc von size sim (S-SZ) chua xac minh; (c) Vision mark/kline 11-23 tre.
Ban TOI THIEU van co y nghia (neu 11-24 12:00 R-SIM chua qua DEV): C0 + C0b + R-LIVE day du (L-*) + R-SIM chi S-X (theo vet sim, khong can
gate/sel: ep vao dung cum sim) + S-SZ neu xong; S-G = INSUFFICIENT => ADD24 = INSUFFICIENT => pilot chi khi owner chap nhan van ban
(Q4) hoac lui pilot <= 2 ngay de xong S-G. KHONG duoc ha nguong de kip lich.

## 13. Cau hoi cho MASTER / owner (kem de xuat)
Q1 (OWNER) R-LIVE doc du lieu van hanh cua bot + kline/mark Vision cua symbol bot giu, 2026-11-19 -> T_cut, KHONG in PnL. Ngoai U1-U4b.
   De xuat: owner duyet bang van ban (ghi bo sung HOLDOUT_UNSEAL "U5 van hanh ADD24"); ly do: kiem van hanh, khong chon tham so, khong PnL.
Q2 (OWNER) Co chay sim engine qua 10-11/2026 de so sim <-> live tren chinh 21/11 khong? De xuat: KHONG (lo PnL sim giai doan niem phong,
   +2-3 ngay Kaggle); thay bang chuoi live~rig~sim (s6). Neu owner muon: prereg rieng, sau pilot.
Q3 (MASTER) R-SIM dung lai HO5 Q2-Q3 (U1) cho muc dich moi (van hanh) - xem la trong pham vi U1 hay can ghi chu? De xuat: ghi chu trong
   prereg + bao owner 1 dong (khong lo them: HO5 da cong bo Q3).
Q4 (OWNER) Neu ADD24 = INSUFFICIENT (vd S-G khong dung duoc dau vao, hoac L-X thieu mau khong phu): lui pilot hay chap nhan van ban?
   De xuat: lui toi da 2 ngay de xong S-G; L-X/L-T thieu mau la chap nhan duoc khi S-X + C0b PASS (da ghi s10, khong can owner).
Q5 (OWNER/MASTER) Stub bang thay 8 entry khoa (chung minh md5 tung entry) thay vi build tu nguon voi PrivateConfig stub? De xuat: thay entry
   (giu byte duong quyet dinh, C0 kiem duoc); build tu nguon chi khi A1 phan doi.
Q6 (MASTER) Env 242 cho rig: dung env242_whitelist 11-16 (md5 8956bef...) hay chup moi? De xuat: chup MOI (sau 11-16 da bat 2 co grid,
   C3_CAPITAL, KS ...) bang duong doc chi-doc da audit (script owner 1 lenh, in sha256 env + ten bien + gia tri danh sach trang) - neu khong
   kip, dung ban 11-16 + override khai truoc va ghi gioi han.
Q7 (MASTER) Nguong (s9) va nhan dong (s8) - dac biet L-S2 (5e-4 / 2e-3), S-SZ (1e-3 / 5e-3), N8 <= 10 %, T_cut = 11-24 07:00. De xuat: chot
   nhu ban nhap; moi thay doi phai truoc commit.
Q8 (MASTER) Sau PASS, co duy tri "ADD24-M" (L-E/L-S/L-SL tren lenh that moi ngay trong pilot, tu dong, bao Telegram khi lech khong giai
   thich) khong? De xuat: CO, nhu monitor; khong chan pilot.
Q9 (MASTER) Ten file / so hieu: ADDENDUM24 cua chuoi PARITY_V12_DRY (theo ADD23) hay prereg doc lap? De xuat: ADDENDUM24_PILOTFID.

## 14. Gioi han con lai (ghi vao gate PILOT, KHONG coi la da kiem)
- Vong main DetectEntrySignal2TradeNormal (feature -> p15 -> S1, createOrderBuyRequest0, so giay twin) khong chay trong rig: R-LIVE phu
  GIAN TIEP (lenh that la ket qua cua vong main; lech se lo o L-E/L-N), R-SIM khong phu.
- Selector chon coin toan universe vs sim: chi parity G-MICRO + S-SEL (neu chay).
- X14 tren live (ALT_EW) khong kiem (MIEN, ADD2). Gia cu / WS rot (C2) khong tai hien.
- Von 10 000: hanh vi tren san that chua co (micro = 1 000); L-10K chi dem leg. Kill-switch C6/A40, A-02, B-09: ngoai ADD24.
- Mau R-LIVE nho (~24 cum, 1 ngay vao lenh): PASS khong loai tru lech hiem; ADD24-M (Q8) de bat tiep.

## 15. MASTER duyet (2026-11-22 ~09:50 +07) - phan nay THANG cac muc tren khi mau thuan
Ban nhap sha256 47931452ee9c9329975bae3ef9718dced5832e797531b16edcfa8f7592266953 (agent thiet ke, chi doc) + muc 15 nay = PREREG CHOT.
MASTER chua doc log SUBMIT / fill / exit chi tiet cua tung lenh (chi dem dong va dong HOURLY tong hop trong cac vong kiem hang ngay).
- P1 (Q1 - OWNER, CHUA co tra loi): R-LIVE tren OW2 dung du lieu van hanh cua bot + kline / markPrice cua symbol lien quan >= 2026-11-19.
  => Luot CHINH THUC R-LIVE (va moi viec tai kline / mark Vision >= 2026-10-01) CHI chay sau khi owner duyet bang van ban (commit
  OWNER_DECISION_*). Truoc do DUOC lam: stub + C0 / C0b; toan bo R-SIM (du lieu <= 2026-09-30, pham vi U1); phat trien harness R-LIVE tren
  fixture DA CO (fx1105 / fx1030) va tren log pull242 chi de dung parser (KHONG cham, KHONG in thong ke lenh that).
- P2 (Q2): KHONG chay sim engine qua thang 10-11/2026.
- P3 (Q3): R-SIM dung lai artefact HO5 (U1, da cong bo) cho muc dich van hanh: trong pham vi; khong in PnL / ROI / DD. Bao owner 1 dong.
- P4 (Q4 - OWNER, CHUA co tra loi): mac dinh BAO THU cho toi khi owner noi khac: ADD24 = INSUFFICIENT-khong-phu => KHONG pilot, lui toi da
  2 ngay de hoan tat; qua 2 ngay => trinh owner.
- P5 (Q5): stub bang THAY 8 entry (khong giai nen / khong in noi dung 8 entry goc). Them cong: (i) jar_sec_check (cong cu da dung cho jar
  sim cc0f9d11) tren stub phai ok=True; (ii) stub chi nam o /dev/shm/add24/jar, chmod 600, xoa khi xong, KHONG dua len Kaggle / may khac;
  (iii) script tao stub KHONG ghi ban sao jar goc ra noi khac.
- P6 (Q6): env cho rig = ban whitelist 11-16 (md5 8956bef...) + override KHAI TRUOC (ghi vao errata truoc luot chinh thuc), VA them cong
  **V8**: moi dong banner cau hinh cua rig ([LIVE-SIZING], [LIVE-DCA-GRID], [MINUTE-FIN], [GATE-RATIO], [TS-EXT], [UNIVERSE-A1], [KILLSW] ...)
  phai TRUNG dong banner tuong ung bot live in luc khoi dong 2026-11-20 06:17 (lay tu log pull242), tru cac truong khai truoc la khac
  (adapter, duong dan, host). V8 truot => sua env rig (errata), khong cham. KHONG doc conf/env.sh that. Neu V8 khong the dat vi thieu gia tri
  => DEV neu chinh xac bien nao thieu de MASTER xin owner chay script chup env da audit.
- P7 (Q7): CHOT nguong s9, nhan s8, T_cut = 2026-11-24 07:00 +07 nhu ban nhap. Hang so trong bao size s9.3 (0,045; 0,0225; 0,6; weights;
  SCALE) phai lay tu banner live (V8) - neu banner khac so trong s9.3 thi dung so cua banner va ghi errata TRUOC luot chinh thuc.
- P8 (Q8): ADD24-M (kiem hang ngay trong pilot) - lam SAU khi ADD24 PASS, khong chan pilot, prereg / script rieng.
- P9 (Q9): ten file nay.
- P10 (sua loi ban nhap): khoa job nang = `mkdir -p ~/claude_master/locks && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 <cmd>`
  (khong long flock). Nguong dia: < 15,3 GB trong => DUNG bao MASTER (nguong cung 15 GB).
- P11 (build): duoc `mvn -o test-compile` / javac CHI trong worktree rieng ~/claude_master/w3/add24_wt voi LIVE_IS_SHADOW_HOST=true va
  PrivateConfig STUB; CAM `mvn package`, cam copy PrivateConfig that, cam chay main() cua jar that, cam dung toi worktree c3_hotfix / c3_ops*
  (chi doc).
- P12 (thu tu): A1 doc lap duyet harness + converter + REF + script gan nhan TRUOC moi luot chinh thuc; chinh thuc 1 lan co khoa; ket qua
  qua A1 roi MASTER moi ket luan va ghi vao gate PILOT.
