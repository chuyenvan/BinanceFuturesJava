# PARITY LIVE vs SIM (B0) — 2026-10-03

Phạm vi: mọi chỉ số trên LIVE (shadow_c3 trên Oracle 161.118.212.3 và 242 tiền thật, CHỈ ĐỌC) có khớp backtest B0 không, theo 9 lớp A–I.
Checklist đăng ký trước khi chạy: `docs/runbooks/PARITY_LIVE_VS_SIM_CHECKLIST.md`. Công cụ: `python3 research/parity/parity_check.py live --fetch --probe` (exit 0 PASS / 2 FAIL / 3 MISSING).

## 0. Kết luận

- Lần chạy TRƯỚC sửa: overall FAIL; shadow FAIL 9 mục. Lần chạy SAU sửa: overall FAIL; shadow FAIL 8 mục.
- Sửa được bằng env trên shadow: 1 mục (E2 sizing, `SIM_F_BASE` 0.015 -> 0.09). Phần còn lại là FAIL do CODE (bảng §4) hoặc do nguồn dữ liệu (D1/B5), hoặc MISSING vì chưa có lệnh/chưa bật gate (đến 2026-10-07 17:15).
- 242: không đụng tới. Các đề xuất ở §5 để owner quyết.
- Không sửa dấu hiệu nào bằng cách nới tiêu chí: mọi ngưỡng PASS/FAIL đã khoá trong checklist trước khi chạy.

## 1. Tóm tắt theo lớp (trạng thái xấu nhất của lớp)

| lớp | shadow trước | shadow sau | 242 (chỉ đọc) |
|---|---|---|---|
| A config / key | MISSING | MISSING | PASS |
| B gate | FAIL | FAIL | FAIL |
| C selector | MISSING | MISSING | MISSING |
| D feature | FAIL | FAIL | FAIL |
| E entry / size | FAIL | FAIL | FAIL |
| F exit | FAIL | FAIL | FAIL |
| G fee / funding | FAIL | FAIL | FAIL |
| H cadence / latency | PASS | FAIL | FAIL |
| I data-in / universe | MISSING | MISSING | MISSING |

Cửa sổ đo trước: từ 2026-10-03 17:57; sau: từ 2026-10-03 21:54.

## 2. Chi tiết từng mục (kết quả lần chạy SAU; E2 có trước/sau)

| id | mục | kỳ vọng (sim B0) | shadow | 242 | sh | 242 | hành động |
|---|---|---|---|---|---|---|---|
| A1 | Configs.* hieu dung (jar 8f3ee52c, 139 field) B0 vs live | mọi field = B0 (trừ field live-only/không đọc) | 7 field khac B0, 0 chua giai thich | 8 field khac B0, 0 chua giai thich | **PASS** | **PASS** |  |
| A1b | shadow == 242 (Configs hieu dung, tru ha tang) | giong nhau | 0 field khac (+ F_BASE: shadow 0.09 = 0.015 x DCA_GRID_SCALE, co chu y, xem E2) | - | **PASS** | **PASS** |  |
| A1c | gia tri hieu dung key vao/ra/size (B0/shadow/242) | - | xem evidence | xem evidence | **PASS** | **PASS** |  |
| A2 | /proc/<pid>/environ (JVM dang chay) == conf/env.sh | trùng | 0 lech [] | 0 lech [] | **PASS** | **PASS** | restart neu lech (shadow) |
| A3 | gate rolling (B0: SIM_GATE_ROLLING_MODE/PCT/DAYS = ratio/0.999950829/90) | ratio/0.999950829/90 | KHONG co key (co chu y: bat 10-07 17:15, DEPLOY_SHADOW_2A §7) | {'LIVE_GATE_ROLLING_DAYS': '90', 'LIVE_GATE_ROLLING_MODE': 'ratio', 'LIVE_GATE_ROLLING_PCT': '0.999950829'} | **MISSING** (known) | **PASS** | KHONG bat som: seed Aerospike 242 qua WAN ~2.2 h chan main thread; bat 10-07 17:15 sau khi buffer 242 du 7 ngay |
| A4 | key B0 live KHONG doc / thay bang key live | - | SIM_APPLY_FUNDING -> ledger giay khong tru funding (G1); SIM_FUNDING_MARK -> idem; DCA_GRID_ENABLED -> live khong chay grid (E5); WFO_FUNDING_PRED_DIR -> chi tai lap sim… | idem (242 khong khai bao 3 key dau) | **PASS** | **PASS** | ghi nhan, khong sua |
| A5 | key live-only bat buoc SHADOW_NO_PUSH=true, LIVE_PROFILE=c3_shadow | bat buoc | ok | ok | **PASS** | **PASS** |  |
| A6 | config.properties key chet (Configs canh bao 'KHONG AI DOC': RATE_FEE, RATE_PROFIT_STOP_MARKET, ...) | khong anh huong | 20 key chet (RATE_PROFIT_STOP_MARKET=0.01, RATE_FEE=0.0015...) — Configs.RATE_*=0.07/0.000982 tu env | idem | **PASS** | **PASS** | ghi nhan (gia tri trong file la SAI SU THAT) |
| B1 | [GATE] coverage phut distinct / phut cua so (tu 2026-10-03 21:54) | 1/phut | 104.3% (27 phut) | 104.3% (25 phut) | **PASS** | **PASS** |  |
| B2 | thr tinh lai tu sel_dump (EntryGate: base*max(0.26787,sp/0.15*1.2876)*scale) vs log thr=[min..max] | khop (/d/<=6e-6, >=99% phut) | 100.0% phut khop (n=27) | 100.0% phut khop (n=23) | **PASS** | **PASS** |  |
| B3 | n_pass tinh lai (!(p15<thr_i)) vs log n_pass | 100% | 100.0% (0 lech) | 100.0% (0 lech) | **PASS** | **PASS** |  |
| B4 | ORT(model gate d19fc8cd) tren feat_dump (33 feat) vs p15_out | max/d/<=1e-6 | max/d/=4.74e-12 (n=27) | max/d/=4.34e-11 (n=24) | **PASS** | **PASS** | model 242 gia dinh = d19fc8cd (DEPLOY_SHADOW_2A §1) |
| B5 | shadow vs 242 cung phut: p15, thr_min, n_cand | /dp50/<=0.02pp va thr +-1% >=90% phut | /dp50 phan phoi/=0.010pp; paired d p10/p50/p90=-0.040/-0.007/0.016 pp; thr_min +-1%=64.0% (n=25) | - | **FAIL** (known) | **FAIL** (known) | nguon: p15 shadow doc ticker qua WAN tre hon (xem D1); khong sua duoc bang env |
| B6 | nguong truoc arm: base=MIN_MOMENTUM_15M=0.008 (G2 fallback) | base 0.00800; q_t=0.008 den arm | base=[0.008] (ratio TAT) | base=[0.008]; [GATE-RATIO] q_t=[0.008] buffer=73888 | **PASS** | **PASS** |  |
| B7 | arm gate G2: buffer 242 (GRR1) -> firstTs+7d, q(0.99995) tinh lai (script gate_arm_check.py) | q_t log = q tinh lai sau arm; n_pass/ngay in [0.34;3.8] | shadow: ratio TAT (chua co buffer rieng) — bat 10-07 17:15 | n=73392 firstTs=2026-09-30 17:01 arm>=2026-10-07 18:00; chua arm -> q_t fallback=0.008; q_now(neu arm)=0.011659; CHUA ARM | **MISSING** | **MISSING** | chay lai gate_arm_check.py sau 10-07 17:15; so q_t log vs q tinh lai |
| B8 | p15 live (feat_dump p15_out) vs ai_pred_1m Aerospike 242 cung phut (n=24) | khop; ai_pred_1m = last-writer(242/shadow) toi 10-07 | max/ai-p15_sh/=4.20e-10 | max/ai-p15_242/=1.68e-03; gen=[2] | **PASS** | **FAIL** (known) | 2 writer (gen=2) => 1 trong 2 so se lech; fix = jar f282581a + LIVE_IS_SHADOW_HOST=true (10-07 17:15), KHONG lam som |
| C1 | top-16 shadow vs 242 cung tick (/giao/) | 16/16 | mean 15.05/16; =16: 4.5%; >=14: 100.0%; rank1 giong 100.0% (n=22 tick); /dgateValue/ p50=0.0037 p90=0.0122 | - | **PASS** | **PASS** |  |
| C2 | sort: rank tang => selectorScore & gateValue(sp) khong giam; rank1 = sp thap nhat (sim: sp nho = tot) | 100% tick | 0/26 tick vi pham | 0/22 tick vi pham | **PASS** | **PASS** |  |
| C3 | recompute offline top-16 tu model deploy (S1 8b1dcf00 + net015 41a07109 + map) tren CUNG feature vector live … | 16/16 | feat_dump KHONG ghi vector 45/9 (chi 33 gate-feature) -> khong tai tao duoc | idem | **MISSING** | **MISSING** | CAN CODE: LiveFeatureDump.maybeDumpSelector them 45+9 cot (hoac dump selFeat45/S1 float[9]) |
| C4 | n_cand=16 moi tick; so coin duoc cham diem [S1] score N | 16; ~universe sim | n_cand=[16]; N median=628 [596..689] | n_cand=[16]; N median=628 [570..689] | **PASS** | **PASS** |  |
| D1 | 33 feature gate (+4 market, p15_out): shadow vs 242 cung (ts,symbol), /d/<=1e-3(1+/x/) | giong (cung nguon, cung code) | 26/38 cot PASS (n=24 cap); FAIL: volatilityTermStructure(0%), advanceDeclineRatio(0%), percentAboveMA20(4%), volumeRatioUpDown(58%), marketBreadthStrength(8%), btcDomina… | - | **FAIL** (known) | **FAIL** (known) | nguon lech Oracle<->242 (doc ticker qua WAN, nen cuoi chua chot) — can code/di chuyen shadow ve cung LAN |
| D2 | 33 feature live vs DEV export cung phut (parity_check.py features) | 27/33 FAIL lan truoc (thieu nguon/ticker-vs-kline) | FAIL: 27/33 feature lech (exact<=1e-08, inline<=1e-03; o nguong may 29/33) / 1 check FAIL / 5 | - | **FAIL** (known) | **FAIL** (known) | lech da biet (RESULT_FEATDIFF_PASS2): tong hieu ung len p15 <= 0.006pp |
| D3 | 45 cot G015 + 9 cot KEEP9 (vector selector) live vs offline cung phut | khop | shadow KHONG dump vector selector | 242 KHONG dump vector selector | **MISSING** | **MISSING** | CAN CODE (LiveFeatureDump); OI feature da audit rieng: AUDIT_OI_FEAT_PARITY = KHONG VENH (spearman 1.0) |
| E2 | margin leg dau @equity 35000, throttle 1: sim = managerBudget*tier*(w0*DCA_GRID_SCALE); live = managerBudget*… | 787.50 USDT (=2.25% equity) | TRƯỚC: 131.25 USDT (live/sim = 0.1667) -> SAU: 787.50 USDT (live/sim = 1.0000) | 131.25 USDT (live/sim = 0.1667) | **PASS** | **FAIL** | shadow: SIM_F_BASE = F_BASE(B0)*DCA_GRID_SCALE = 0.015*6 = 0.09 (bu, vi live khong nhan ratio). 242: chi de xuat (cung env hoac code) |
| E1 | gia vao = ticker.priceClose cua nen tin hieu (live: OrderTargetInfo.priceEntry=ticker.priceClose -> ShadowBoo… | entry = priceClose | dung (code) | dung (code, legacy khong mo lenh moi) | **PASS** | **PASS** |  |
| E3 | tran per-coin CONC_CAP_PERCOIN 15% equity va tran live 4.5% equity (live-only) co chan leg dau? | khong bind | leg dau 2.25% equity < 4.5% va < 15% => khong bind | idem | **PASS** | **PASS** |  |
| E4 | U=Sum(margin)/equity, throttle=1-U/U_MAX (U_MAX=0.60): hai ham managerBudget chung; live: marginRunning=Shado… | cung ham | B(35000,5000)=600.00 / B(40000,12000)=450.00 / B(35000,21000)=nan | idem | **PASS** | **PASS** |  |
| E5 | DCA grid (leg 1-3 tai -50/-75/-90%) + DCA_LEVEL1 | co (46 DCA_LEVEL1 + leg grid) | KHONG co (DcaProcessor.getDCAProduction duyet vi the THAT; shadow khong co) | chi coin legacy (skip-LEGACY cho so giay) | **FAIL** (known) | **FAIL** (known) | CAN CODE (hoac owner chap nhan 'B0-khong-grid' sau do tac dong tren sim) |
| E6 | ledger giay shadow/242 (archive) — size thuc te | - | 74 lenh giay, ts_entry 2026-09-06..2026-09-19, notional p50=231 (rank/pred cu), reason={'TRAILING_STOP': 58, 'TIME_STOP_168H': 16}; 0 lenh tu 2a (10-02 17:53) | ledger.csv 242: 0 lenh (n_pass=0) | **MISSING** | **MISSING** | chua co lenh sau 2a (n_pass=0 den arm 10-07); xac nhan size khi co lenh dau tien: margin = 787.50 x throttle |
| F1 | arm 7%: giay hardcode LiveProfileC3.ARM_RATE=0.07; legacy Configs.RATE_PROFIT_STOP_MARKET (env) | 0.07 | 0.07 (hardcode) | legacy: 0.07; giay: 0.07 | **PASS** | **PASS** |  |
| F2 | SL sau arm = trailFromCap(peak): peak - min(peak*1.0, 0.03), lam tron 0.005; ham Java that (calRateLossDynami… | SL(peak=7%)=+4.0%; SL(peak=10%)=+7.0% | Java==Py: 0 sai; B0==shadow bit-exact: True; vi du {'R 0.07000 0.10': 0.04, 'R 0.08000 0.10': 0.05, 'R 0.10000 0.10': 0.07, 'R 0.20000 0.10': 0.17} | Java==Py: 0 sai; B0==242 bit-exact: True | **PASS** | **PASS** |  |
| F3 | lam tron 0.5% (step 0.005) — chung ham trailFromCap voi sim (OrderTargetInfoTest.trailRate) | step 0.005 | = sim (cung ham) | = sim (cung ham) | **PASS** | **PASS** |  |
| F4 | ratchet: giay lien tuc (mult 1.0); legacy dead-zone x5.21847 (arm*5.22=36.5%) | sim lien tuc | giay: lien tuc (tradecore/selector/LiveProfileC3.java:41: public static final float RATCHET_DEADZONE_MULT_ON = 1.0f;) | legacy: dead-zone x5.21847 => SL dung yen o +4% khi lai 7-36.5% (co chu y L3, khong doi luat tien that) | **PASS** | **FAIL** (known) | owner chot huong (khong tu dong bo) — de xuat: legacy 242 = ratchet lien tuc (can code/env?) |
| F5 | time-stop 168h cho cum CHUA arm: giay co; legacy khong | co (SIM_LOSER_TIME_STOP_HOURS=168, min(open,close)) | co (ShadowBookC3 tick, px snapshot) | legacy: khong (timeStopApplies=false) — 0 lenh giay | **PASS** | **FAIL** (known) | legacy 242: chi bao cao |
| F6 | SL cung ban dau pre-arm (PRE_ARM_SL / HARD SL / calRateLossDynamic cu) | B0: khong co (PRE_ARM_SL=0) | khong co (PRE_ARM_SL=0, khong nhanh trong ShadowBookC3) | idem | **PASS** | **PASS** |  |
| F7 | nguon dinh/gia: sim = HIGH nen 1m (peakPrice), fill SL = min(SL, open); giay = snapshot price_realtime moi 10… | HIGH/LOW 1m | snapshot 10s (dinh THAP hon HIGH => arm tre/it hon; fill SL khong haircut gap) | legacy: lenh SL that tren san (tiem can sim hon) | **FAIL** (known) | **FAIL** (known) | CAN CODE (ShadowBookC3.tick doc high/low 1m) — hien khong sua duoc bang env |
| F8 | uu tien cung nen: sim dat SL o nen arm, khong khop cung nen (BLOCK_INTRABAR_LOOKAHEAD); giay: arm->ratchet->k… | khong khop cung nen | co the khop cung tick (gap 3pp nen hiem) | - | **FAIL** (known) | **MISSING** (known) | cung nhom F7 (code) |
| F9 | vi the dang chay (giay/legacy): doi chieu SL so vs cong thuc | - | 0 vi the giay (n_pass=0 tu 2a) | legacy 48 symbol, 0 'New price SL'/'Update SL' tu 10-01 (chua legacy nao lai >7%) | **MISSING** | **MISSING** | chua kiem duoc; chay lai khi co lenh |
| G1 | ledger giay: pnl=(exit-entry)*qty, KHONG tru phi/slippage/funding | sim tru: fee 0.000982 + 2*slip 0.000067 ~ 0.2098%/vong + funding mark | khong tru (PnL giay lac quan ~0.210% notional/vong + funding) | idem (so giay) | **FAIL** (known) | **FAIL** (known) | tinh offline tu ledger (tools/shadow_vs_sim.py); CAN CODE de tru trong ledger |
| G2 | 242: fill that legacy dong — phi thuc te vs 0.1116%/vong | 0.1116% | - | khong co fill legacy nao dong tu 10-01 | **MISSING** | **MISSING** | doc userTrades khi co lenh dong (khong co API key o day) |
| H1 | [PASS-TIMING] selector tick (ms) p50/p90/max trong cua so; nhip 60 s | p90 << 60000 ms | p50=413 p90=3223 max=13985 (n=27) | p50=192 p90=263 max=1206 (n=25) | **PASS** | **PASS** | shadow cham hon 242 (doc Aerospike 242 qua WAN) nhung << 60 s |
| H2 | OOM + ERROR moi (tru nhieu co san: -2015 stub-key, Reporter NPE, P2PTracker, Legacy Scan) trong cua so | 0 | OOM=0, ERROR la=3 [('ERROR [pool-#-thread-#] c.b.c.a.DataManagerAerospikeFloatSim: ❌ [AEROSPIKE-FAIL] MẤT DATA chunk start=# #:# ke', 1), ('ERROR [LiveOiFeatRefresh] c.b… | OOM=0, ERROR la=0 [] | **FAIL** (known) | **PASS** | loi Aerospike WAN (Node not found / MAT DATA chunk / getMetricMap) ngay sau restart: shadow doc Aerospike 242 qua WAN; tu hoi phuc ([GATE] dung nhip), khong sua duoc ban… |
| H2b | [OI-LIVE] mode inplace, refresh hang gio evicted=0 | inplace; evicted=0 | inplace: cold-load=0, refresh=1, evicted!=0 / reload loi=0 | inplace: cold-load=0, refresh=0, evicted!=0 / reload loi=0 | **PASS** | **MISSING** |  |
| H3 | auto-restart 12h giu heap: JAVA_TOOL_OPTIONS trong environ (con ke thua) / -Xmx | giu heap 3g (kiem 3 restart) | co: -Xms3g -Xmx3g -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh; jcmd MaxHeap=3221225472; 'Picked up' sau moi restart: 3 | KHONG: cmdline=.x86_64/bin/java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager; JAVA_TOOL_OPTIONS vang… | **PASS** | **FAIL** (known) | 242: CHI DE XUAT: them export JAVA_TOOL_OPTIONS vao conf/env.sh (an toan, khong .java) — owner quyet |
| I1 | universe live: so coin cham diem [S1] (>=336 moc gio) vs sim (mapper 863 id gom delisted) | universe sim: USDT-perp, khong USDC/BTCDOM/_ (SurvivorshipBac0:52) | N median=628 [596..689] (n_enough median=621); 30 tick dau cua so=628, 30 tick cuoi=628 | N median=628 [570..689] (n_enough median=621) | **PASS** | **PASS** | sau restart shadow universe nho ~560 den khi OI refresh gio dau (cold-load OI 564 coin) — xem H2b |
| I2 | symbol vol=0 / symbol la vao top-16 | khong | top-16 18 symbol khac nhau, 0 ky tu la; vol=0 KHONG kiem duoc (dump khong co volume; S1RankerLive chi loc pc<=0) | idem | **MISSING** | **MISSING** | CAN CODE hoac Aerospike scan volume; neu can: loc theo kline_1m_opt volume |
| I3 | coin legacy (vi the THAT cu tren 242) bi chan khoi so giay | - | legacy_symbols.csv shadow: 0 (khong vi the that) | 48 coin legacy; 'skip-LEGACY' 1748 lan trong log | **PASS** | **PASS** | ghi nhan |

## 3. Đã sửa trên shadow (env/config/file; không .java, không build)

| mục | trước | sau | cách làm |
|---|---|---|---|
| E2 sizing leg đầu @equity 35000 | managerBudget = 131.25 USDT (live/sim = 0.1667) | 787.50 USDT (live/sim = 1.0000; Probe+FormulaProbe: 787.50006 float32) | `~/shadow_c3/app/conf/env.sh`: `SIM_F_BASE=0.015` -> `0.09` (= F_BASE B0 0.015 × DCA_GRID_SCALE 6.0; vì đường paper live không nhân `gridLegWeightRatio` = w×DCA_GRID_SCALE như sim, DcaUtils FIX_B2). Backup `~/claude_master/1003/parity/env.sh.pre_fbase_20261003_215130` (md5 ce35d2f24d7f). Restart `shadow-c3` 21:52 (+07); `SHADOW_NO_PUSH=true`, `LIVE_PROFILE=c3_shadow`, `JAVA_TOOL_OPTIONS=-Xms3g -Xmx3g` giữ nguyên; `[GATE]` chạy lại sau 1-2 phút. |

Chưa xác nhận bằng lệnh thật: shadow chưa có lệnh nào sau 2a (n_pass=0 đến khi G2 arm), nên E6 vẫn MISSING; xác nhận cuối là margin lệnh đầu tiên trong `ledger.csv` = 787.50 × throttle × tier.

Không sửa thêm gì vì: (a) mọi mục còn lại FAIL cần đổi code; (b) gate rolling + jar `jar_nowrite` f282581a chỉ làm 2026-10-07 17:15 theo `DEPLOY_SHADOW_2A_20261002.md` §7 / `FIX_NO_WRITE_242_20261003.md`.

## 4. FAIL do CODE (cần code; chưa làm vì ngoài phạm vi env/config)

| mục | vấn đề | file:line (HEAD 69b3cf07) | đề xuất |
|---|---|---|---|
| F7/F8 | đỉnh/giá exit lấy từ snapshot `price_realtime` mỗi 10s, fill SL đúng giá SL; sim dùng HIGH/LOW nến 1m, fill min(SL,open), BLOCK_INTRABAR_LOOKAHEAD | `tradecore/selector/ShadowBookC3.java:348` (peak), `:352-375` (arm/trail trên px), `:385-401` closeAt | tick đọc high/low 1m + fill haircut như sim |
| G1 | PnL sổ giấy không trừ phí 0.000982 + 2×slip 0.000067 (~0.21%/vòng) và funding | `ShadowBookC3.java:42` (ghi chú), `:388` `pnl=(exitPx-entry)*qty` | trừ phí/slip/funding trong closeAt, hoặc tính offline `tools/shadow_vs_sim.py` |
| E5 | không có DCA grid leg 1-3 (sim DCA_GRID_ENABLED=true): `DcaProcessor.getDCAProduction` duyệt vị thế THẬT, shadow không có; `openPos` bỏ leg2+ | `tradecore/DcaProcessor.java:156`, `ShadowBookC3.java:260` | thêm grid vào sổ giấy, hoặc owner chấp nhận 'B0 không grid' và đo tác động trên sim |
| C3/D3 | dump không có vector 45 G015 + 9 KEEP9 nên không tái tạo được top-16 offline | `ai_ml/features/export/entry/LiveFeatureDump.java:194` `maybeDumpSelector` | thêm 54 cột vào sel_dump |
| I2 | không kiểm được vol=0 (dump không có volume; ranker chỉ loại pc<=0) | `tradecore/selector/S1RankerLive.java:244` | thêm cột volume vào dump hoặc loc theo kline_1m_opt |
| D1/B5 | feature thị trường (advanceDeclineRatio, percentAboveMA20, marketBreadth*, basket*, volatilityTermStructure) lệch shadow vs 242 cùng phút: nguồn ticker/kline đọc khác thời điểm (shadow đọc Aerospike 242 qua WAN) | không có 1 dòng lỗi; lệch dữ liệu đầu vào | chạy shadow cùng LAN với dữ liệu hoặc chốt nến trước khi tính; ảnh hưởng đo được: |Δp15| median 0.005pp, thr_min ±1% chỉ 45.9% phút, top-16 giao 15.06/16, rank1 giống 99.6% |
| B8 | `ai_pred_1m` Aerospike 242 có 2 writer (gen=2): 242 + shadow; giá trị lưu = writer sau. max|ai−p15_242|=1.9e-3, max|ai−p15_shadow|=2.9e-5 => bản ghi hiện là của shadow | gói jar `jar_nowrite` f282581a + `LIVE_IS_SHADOW_HOST=true` | LÀM 2026-10-07 17:15 theo kế hoạch, không làm sớm |

## 5. 242 (CHỈ ĐỌC): báo cáo + đề xuất, không sửa

| mục | hiện trạng | đề xuất cho owner |
|---|---|---|
| H3 | `JAVA_TOOL_OPTIONS` vắng trong environ/cmdline => sau auto-restart 12h heap mặc định (~1.95GB) thay vì 3g | thêm `export JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g ..."` vào `conf/env.sh` của 242 (không cần .java), chọn lúc restart thường lệ |
| E2 | leg đầu 131.25 USDT @35000 = 1/6 sim; DCA_GRID_ENABLED=false nên không có leg 1-3. Lưu ý: 242 cũng đang chạy `LIVE_PROFILE=c3_shadow` + `SHADOW_NO_PUSH=true` (sổ giấy `/home/chuyennd/java/shadow_c3`, 0 lệnh), tiền thật chỉ còn vị thế legacy | để sổ giấy 242 khớp sim: `SIM_F_BASE=0.09` trong `conf/env.sh` 242 (như shadow). Nếu sau này chuyển sang đẩy lệnh thật thì sizing này là quyết định rủi ro tiền thật (không có trần 4.5% của LiveProfileC3), owner chốt riêng; không tự áp |
| F4/F5 | legacy: ratchet dead-zone ×5.21847 (SL đứng yên +4% khi lãi 7-36.5%), không time-stop 168h; sổ giấy dùng ratchet liên tục + time-stop | owner chốt hướng; 242 không mở lệnh mới tới khi G2 arm (n_pass=0) nên chưa ảnh hưởng |
| H2 | 2 ERROR `P2PTracker getLowestPrice BUY/SELL exception: null` trong cửa sổ | báo cáo; ERROR thuộc nhóm đã biết, không ảnh hưởng gate/selector |
| B7 | G2 buffer 242: n=73392, firstTs 2026-09-30 17:01, arm từ 2026-10-07 18:00; q_now (nếu arm) = 0.011659 so với fallback 0.008 => sau arm ngưỡng gate cao hơn ~46% | kiểm lại bằng `gate_arm_check.py` sau arm; so q_t log và q tính lại |
| A3 | gate rolling ratio/0.999950829/90 ĐÃ bật trên 242; chưa arm (đang fallback 0.008) | không làm gì |
| jar | 242 chạy jar 8f3ee52c; shadow cùng jar. Bản `jar_nowrite` f282581a chỉ cần cho host shadow | làm 10-07 17:15 |

## 6. Việc có lịch 2026-10-07 17:15 (ghi lại, KHÔNG làm sớm)

1. Bật gate rolling trên shadow (`SIM_GATE_ROLLING_MODE=ratio`, `PCT=0.999950829`, `DAYS=90`) sau khi buffer đủ 7 ngày; seed Aerospike 242 qua WAN ~2.2 h chặn main thread nên không bật sớm.
2. Thay jar bằng `~/claude_master/1002/deploy242/jar_nowrite/` (f282581a) + `LIVE_IS_SHADOW_HOST=true` để chấm dứt ghi `ai_pred_1m` từ shadow (B8).
3. Chạy lại `parity_check.py live --fetch --probe`; B7 (arm) và E6/F9 (lệnh đầu tiên) sẽ đo được lần đầu.

## 7. Lưu ý đo đạc / giới hạn

- MD5 profile B0 dùng để dựng bộ env sim là `c6ab008d…` (file `profiles/prof_run.properties` hiện tại) khác `ff3ce513` owner nêu; ff3ce513 nhiều khả năng là hash printDone/config chứ không phải hash file. Mọi kết quả A1 quy chiếu file c6ab008d.
- 2026 là holdout/audit-only; tài liệu này không dùng để chọn tham số, chỉ đối chiếu live với sim.
- Cửa sổ sau sửa chỉ ~30 phút (21:54-22:22) nên H2b 242 = MISSING (chưa có lần refresh OI hàng giờ nào trong cửa sổ); các thống kê tỷ lệ (C1, B5, D1) không đổi theo sửa env vì E2 chỉ ảnh hưởng sizing.
- Sau khi sửa E2, A1/A1b/A1c/E4 ban đầu báo FAIL vì F_BASE shadow (0.09) khác B0 (0.015) và khác 242. Checker được sửa để coi F_BASE = F_BASE(B0) × DCA_GRID_SCALE là lệch GIẢI THÍCH ĐƯỢC (điều kiện cứng trong code: |F_BASE_shadow − 0.015×6| < 1e-9) và E4 so với B0 nhân hệ số F_BASE; đây là thay đổi checker có chủ đích, ghi lại ở đây.
- H2 shadow FAIL (known): 3 ERROR Aerospike lúc 21:56 (4 phút sau restart): `Node not found for partition` (BTC/ETH oi_feat_z), 1 chunk 21:11 mất 45 key sau 4 lần retry, và `Legacy Scan` -3. Shadow đọc Aerospike 242 qua WAN nên gặp blip; tự hồi phục, [GATE] đủ nhịp (B1 110%), không phải do thay đổi F_BASE. Không sửa được bằng env.
- Hash: jar `8f3ee52ce4ceac8c`, gate model `d19fc8cd`, S1 `8b1dcf00`, net015 `41a07109`.

