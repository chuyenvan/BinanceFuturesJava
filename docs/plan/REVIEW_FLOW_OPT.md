# REVIEW_FLOW_OPT — RÀ SOÁT END-TO-END LUỒNG `G2 + FLAT3`: hướng TỐI ƯU **CHƯA THỬ**

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Loại:** CHỈ ĐỌC + THIẾT KẾ (**0 sim / 0 train / 0 build**).
**Baseline:** `profiles/g2_flat3.properties` = `r4_kg0_k16_f015_g155` + GDV2 rolling gate
(`SIM_GATE_ROLLING_MODE=ratio`, `PCT=0.999950829`, `DAYS=90`) + FLAT3 exit (`TS_GIVEBACK_RATIO=1.0`,
`SIM_TS_MAX_GAP(_WEAK)=0.03`).
**Số chuẩn:** `@base` B0 n **2517** · eq **131 908** (md5 `650c386f…`); `@stress` n **2509** · CAGR **33,79 %** ·
ddPhút **−18,00 %** · UW **128,9** · q\* 23,7 · top-1 17,59 % · conc **4,09 %** · Calmar_MTM **1,877** · **PASS 4 tầng**
(`RESULT_GDV2_P3`). **Luật:** `docs/runbooks/RISK_APPETITE.md` §9 (T4: `n` là mục tiêu chính).
**Ràng buộc:** không chạm 242/ONNX/LIVE/`NUM_FEATURES`/`extractFeatures45` · DEV ≤ 2025-12-31 · không push file dữ liệu.

---

## 0. TRẢ LỜI THẲNG (đọc trước)

> **Gần như KHÔNG còn lever CONFIG nào > NULL.** Nút cổ **duy nhất** là **CỔNG AI** (96 %+ ứng viên chết ở đó;
> `RESULT_CAPACITY_DIAG` `aedf535`), **không** phải slot/vốn/size/exit. Mọi cách mở gate bằng config **đã đo đều vỡ T1/T3**
> (10/11 lever đã chặn — `SUGGEST_DOUBLE_ENTRIES` §1).
> **Còn ĐÚNG 1 hướng cơ học có thể thêm SỰ KIỆN thật**: **nguồn sự kiện thứ 2 ĐỘC LẬP** — và ứng viên duy nhất đã thử
> (OFI V3, từ aggTrades miễn phí) vừa **NO-GO** vì nó *là S1 + 2 cột* (tương quan 0,87–0,93; `RESULT_OFI_V3_EVENT2`).
> ⇒ Hướng còn lại **PHẢI cần DỮ LIỆU MỚI** (L2 order-book depth mua, hoặc liquidation thu forward) — không thể làm bằng
> config/feature trên dữ liệu hiện có.
> **Các tầng còn lại (FEATURE/SELECTOR/ENTRY/SIZING/EXIT/RISK):** những ô *thật sự* chưa chạy đều **kỳ vọng thấp hoặc ≈ 0**,
> vì cơ chế của chúng không chạm được nút cổ (xem §2).

---

## 1. VIỆC 1 — BẢNG LUỒNG END-TO-END (`tầng · file:line · key điều khiển`)

| # | tầng | điểm vào (file:line) | key điều khiển |
|---|---|---|---|
| 1a | **DATA — ticker 1m** | `aerospike/DataManagerAerospikeFloatSim.java:1474` `scanAll(sp,"ticker","kline_1m_opt")` | `TICKER_SOURCE`, (Aerospike 242 ns `ticker`) |
| 1b | **DATA — OI** | `ai_ml/onnx/funding/LiveOiFeatProvider.java:59` · `research/oibackfill/ComputeOiFeat2Live242.java` | `OI_LIVE_REFRESH_MODE=inplace` (deploy 242 `388ffc37`) |
| 1c | **DATA — funding** | `research/OrderTargetInfoTest.java:317,353` `FundingFeeManager.getFundingHistory` | `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK`, `SIM_FUNDING_SCALE` |
| 2a | **FEATURE — gate 33** | `ai_ml/onnx/entry/OnnxInferenceManager.java:51` gọi `extractFeaturesV3Full:67` | ONNX (KHÔNG đụng) |
| 2b | **FEATURE — selector 45** | `ai_ml/onnx/funding/SelectorOnnxInferenceManager.java:56` `extractFeatures45` | bins `WFO_FUNDING_PRED_DIR`; scaler = red herring (`RESULT_P15_SOURCE`) |
| 3a | **GATE — 1 cổng entry (market)** | `ai_ml/onnx/entry/AIRejectFilter.java:61` `entryGate` → `tradecore/EntryGate.java:184` `threshold` | `SIM_MIN_MOMENTUM_15M=0.008` |
| 3b | **GATE — dyn scale** | `EntryGate.java:44-58` (`DYN_MIN/SCORE_BASE/DYN_MULT/GATE_DYN_SCALE`) | `SIM_GATE_DYN_SCALE=1.55` |
| 3c | **GATE — rolling ratio W90** | `ai_ml/onnx/entry/GateRollingRatio.java:28-76` + `GateRatioBuffer.java` | `SIM_GATE_ROLLING_MODE=ratio`, `…PCT=0.999950829`, `…DAYS=90` |
| 3d | **GATE — quantile cuộn p15 (OFF)** | `EntryGate.java:83,111,158` `P15_Q/rollingThrAt`; set-time `Simulator…:227` | `SIM_GATE_P15_Q` (0=OFF) |
| 4a | **SELECTOR — top-K** | `research/SimulatorMarketLevelTicker1MStopLoss.java:711` `selectCands` · gọi `:410` | `SELECTOR_RANK_TOPK=16`, `SELECTOR_ONLY_ENTRY=0`, `SELECTOR_LEG_CUT` |
| 4b | **SELECTOR — nhịp** | `Simulator…:1305-1313` (sim `SIM_ENTRY_SAMPLE_MIN=1`) · live `trading/DetectEntrySignal2TradeNormal.java:1184` | `SIM_ENTRY_SAMPLE_MIN=1`, `LIVE_ENTRY_GRID_MIN=15` |
| 4c | **SELECTOR — cascade** | `DetectEntrySignal2TradeNormal.java:688` | `ENTRY_CASCADE=0` (code sẵn, CHƯA deploy) |
| 5 | **ENTRY** | `Simulator…createOrder:1281`; gate-bypass BIG_DOWN `:1326`; BIG_DOWN nguồn `:332/348/371`; DCA_LEVEL1 `:379/390`; PREDICT `:436`; DCA-signal `:448` | `BD_SIZE_ADAPT`, `DCA_SIGNAL_GATE`, `BD_SEL_TOPK` |
| 6 | **SIZING/ALLOCATION** | `tradecore/TradeUtils.java:125` `managerBudget` → `:138-142` (`eq×F_BASE×throttle/ladder`); DCA-grid ratio `Simulator…:~1418`; tier `CoinRankManager.java:74`; trần `Simulator…:1471/1490/1505` | `SIM_F_BASE=0.015`, `SIM_U_MAX=0.60`, `DCA_GRID_*`, `CONC_CAP_PERCOIN_PCT=0.15` |
| 7 | **EXIT** | `Simulator…startUpdateOldOrderTrading:983`; PRE_ARM_SL `:1004`; LOSER_TS `:1026`; COND_EXIT `:1045`; TP `:1064`; arm `:1080` → `OrderTargetInfoTest.java:214 updateStatusNew` / `:246 updateTPSL` / `:376 trailRate` | `RATE_PROFIT_STOP_MARKET=0.07`, `LOSER_TIME_STOP_HOURS=168`, `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP(_WEAK)=0.03` |
| 8 | **RISK** | `tradecore/TickWeakBlock.java:90 step` (gọi `Simulator…:326`, summary `:619`); trần `TradeUtils.managerBudget:137` | `SIM_U_MAX`, `SIM_BREAKER_MODE=OFF` |
| 9a | **LIVE↔SIM — nhịp** | sim 1′ (`Simulator…:1310` `SIM_ENTRY_SAMPLE_MIN`) vs live `LIVE_ENTRY_GRID_MIN=15` (`Detect:1184`) | gap: `RESULT_SIM_CADENCE_MATCH` (sel15 ≈ 17,3 % vs 1′ ≈ 27 %) |
| 9b | **LIVE↔SIM — latency/fill** | `RESULT_LATENCY_FILL` (D6) — **không bias**, chỉ lệch mốc đo | — |
| 9c | **LIVE↔SIM — chi phí** | `RESULT_COST_TRUTH` (`d059cc3`): sim vào ở CLOSE nến 1′ ⇒ đúng = `fee + spread`, KHÔNG slip | `SIM_RATE_FEE`, `SIM_SLIPPAGE_RATE` |

---

## 2. VIỆC 2 — TỪNG TẦNG: **ĐÃ CÀN** vs **CHƯA THỬ (có cơ sở)**

⚠️ Cột "đã càn" **KHÔNG đề xuất lại** (theo yêu cầu). Chỉ ghi để đối chiếu.

### 2.1 DATA — **càn một phần, 1 ô cần DỮ LIỆU MỚI**
- Đã càn: liquidity **lọc universe** (`RESULT_COST_LIQUIDITY`: decile kém thanh khoản **lãi nhất** ⇒ cắt mất lãi);
  OFI từ aggTrades miễn phí (`RESULT_OFI_MONEY_REORIENT` + `RESULT_OFI_V3_EVENT2` = **NO-GO**).
- **CHƯA THỬ (cần data mới):** **L2 order-book depth** (bulk Vision chỉ có `bookDepth` %, không phải L2 thật) ·
  **liquidation stream** (`forceOrder`, không có bulk lịch sử ⇒ chỉ thu forward) · on-chain.
  (`docs/plan/PROPOSAL_MICROSTRUCTURE_DATA.md` — licences/rủi ro đã khảo.)

### 2.2 FEATURE (gate 33 / selector 45) — **CÀN**
- `RESULT_FEAT_ADD_V1` (thêm 5 feature): **FAIL T1** trên đúng nền G2+FLAT3 (UW 353 > 250; 2022 âm).
- `RESULT_FEAT_CUT_RVOL15M`: **dừng ở tầng model**, KHÔNG sim.
- `REVIEW_GATE_FEATLABEL` §2: **không** feature/label nào mở được gate mà giữ T3; 1 ô chưa chạy
  (`PREREG_GATE_FEATLABEL`, đo dưới gate ratio) — **ưu tiên THẤP, kỳ vọng NULL**.

### 2.3 GATE — **CÀN (11 vòng)**
- `RESULT_GATESCALE`/`GATE_CALIB`/`GATEDYN`/`GATEDYN2`/`FLATGATE`/`GATE_RECAL`/`GATE_ROOTCAUSE`/`GD92_R4`/`GDV2_EVEN`/`DOUBLE_ENTRIES`/`OFI_V3_EVENT2`.
- Quy luật bất biến: **mở gate ⇒ n↑ ⇒ T1/T3 vỡ** (D2 `pct 0,92`+scale 1,00 = n 4287 **FAIL 4/4**; W30 **FAIL 4/4**).
- ⚠️ **Nuance (ghi nhận, KHÔNG đề xuất lại):** `RESULT_REGIME_GATE` (regime MA200) PASS CAGR 32,95 nhưng **FAIL chỉ vì UW
  2025 = 223 > 200** — ngưỡng nay đã nới **250** (§7). Trục này vẫn nằm trong "đã càn" (5 vòng breadth/regime);
  việc "chấm lại dưới ngưỡng mới" là quyết định của owner, không phải hướng mới.

### 2.4 SELECTOR (S1) — **CÀN**
- K×size: `RESULT_DOUBLE_ENTRIES` (+`_QY`) — trần **1,83×**, arm đó vỡ T3; K24 **trượt T4** (⟹ `DECISION 0013`).
- `RESULT_SELECTOR_LEG_CUT` NULL · cadence `RESULT_R4_CADENCE` (1′ đã ở trần) · `RESULT_K_DENSITY` (K chỉ dày **trong tuần gate mở**).
- Dư địa duy nhất: **size phi-tuyến theo rank/edge trong top-K** — xem §3 H3 (**chưa có key nào**).

### 2.5 ENTRY — **CÀN (trừ 1 path market-signal)**
- DCA-signal `RESULT_DCA_SIGNAL_GATE(_V2)` · DCA grid `RESULT_DCA_MORELEGS_V4` (NULL 8/8) · `DCA_ROUND_CAP` (PRIMARY PASS→FAIL).
- BIG_DOWN: `RESULT_SEL_BIGDOWN` NULL · `RESULT_BD_THRESHOLD_FRAGILITY` (**ngưỡng brittle**: PnL BIG_DOWN dao **2×** giữa 4 điểm quét;
  hiện tại là local max) · `RESULT_BIGUP_MEDIUPDOWN`/`BD_SIZE_ADAPT` đã đo.
- Chưa thử: xem §3 H4 — dùng **path BIG_DOWN/DCA (bypass gate)** như nguồn sự kiện mở **tuần gate ĐÓNG**.

### 2.6 SIZING / ALLOCATION — **gần CÀN, 2 ô trống**
- `SIM_F_BASE` = lever **không-thêm-lệnh** (`RESULT_SIZE_COUNT`: ×0,5 ⇒ n **y hệt**); throttle `U_MAX` không bind (max U 0,47).
- Vol-target COIN **NULL** (`RESULT_VOLTARGET_G2` — chỉ là cắt leverage); vol-target **PORTFOLIO BLOCKED** (hằng số
  `PORTFOLIO_TARGET_ANNUAL_VOL=0.25` **hard-code**, đổi cần **build jar**) ⇒ **ô chưa thử thật**.
- Trần per-coin 15 % (`RESULT_CONC_CAP_HIGHN`): bind nhưng **chỉ hạ conc, n↓ nhẹ**; trần aggregate DCA + BD/giờ: có key, đa số non-binding.
- **Ô trống #1:** size phi-tuyến theo rank/edge (H3). **Ô trống #2:** vol-target PORTFOLIO (cần build; kỳ vọng ≈ NULL như bản COIN).

### 2.7 EXIT — **CÀN (4 vòng + 6 chân)**
- `RESULT_EXIT_HIGH_N` (**6/6 chân 0 TỐT/0 XẤU ngoài CI** trên nền 2 559/2 632 leg) · `RESULT_TRAIL_G2`/`TRAIL2_G2` (FLAT3 = đơn giản nhất, không kém) ·
  `RESULT_EXIT_FIT` NULL · `RESULT_HOLDTODIE` (bỏ TS 168h ⇒ **n −203, vỡ tail**) · `RESULT_EXIT_STRUCT` (A2/A3 kém) ·
  `RESULT_SHAPE1_EARLY_CUT` (3 giá trị cắt lỗ sớm chưa thử ⇒ **0/4 PASS**) · `SL_ADAPTIVE_SWEEP`/`FAMILY2_TP_SL`.
- ⇒ **KHÔNG** còn chân exit nào đáng đầu tư (`RESULT_CAPACITY_DIAG` §4). Cơ chế "chốt một phần" (partial scale-out) chưa có,
  nhưng exit đã 4 vòng NULL ⇒ **kỳ vọng ≈ 0**.

### 2.8 RISK — **CÀN**
- `RESULT_TICK_BLOCK` (chặn cả lượt) NO-GO · `RESULT_DD_THROTTLE` NULL · trần gross 70 % **không bind** (`RESULT_GROSS_ASYMMAP`: gross thật 48,8 % max).
- Chưa thử: **trần exposure TƯƠNG QUAN (cross-coin / theo cụm crash)** — nhưng `RESULT_TAIL_LEVER`: đuôi là **hệ thống**, mọi cap **cắt 82–114 % PnL** ⇒ **kỳ vọng ≈ 0**.

### 2.9 LIVE↔SIM — **lệch THẬT, chưa đóng**
- Nhịp: live `LIVE_ENTRY_GRID_MIN=15` ⇒ CAGR thiết-kế ≈ **17,3 %** vs sim 1′ ≈ 27 % (`RESULT_SIM_CADENCE_MATCH`).
- Cascade (`ENTRY_CASCADE`) **code xong, đã chứng minh OFF byte-identical**, **CHƯA deploy** — đây là **hướng H2** (§3).
- Latency/chi phí: đã đo, **không bias** (`RESULT_LATENCY_FILL`, `RESULT_COST_TRUTH`).

---

## 3. VIỆC 3 — XẾP HẠNG ≤ 5 HƯỚNG **CHƯA THỬ**

### H1 — Nguồn sự kiện thứ 2 **ĐỘC LẬP** (L2 order-book depth / liquidation cascade) ⟶ **CẦN DỮ LIỆU MỚI**
- **Vì sao chưa thử:** OFI V3 (ứng viên duy nhất, từ aggTrades free) **KHÔNG độc lập** với S1 (spearman 0,87–0,93;
  top-8 ngoài pool 0,054 %) ⇒ NO-GO. Nguồn **thật sự** độc lập (micro-structure) **chưa có dữ liệu**.
- **Cơ học:** chỉ kênh này mở được **56 % số tuần gate ĐÓNG** (132/234 tuần; khe dài 70–129 ngày giống nhau ở mọi K ⇒
  không K nào lấp được). Là lever **SỐ SỰ KIỆN**, không phải leg/tuần.
- **Kỳ vọng `n`/chất lượng:** **chưa biết** (không có cơ sở số); trần OFI cho thấy ứng viên không-độc-lập chỉ +12 % và **net âm**.
- **Test RẺ NHẤT (0-sim, offline):** lặp lại đúng phương pháp `RESULT_OFI_V3_EVENT2` — đo **(a)** % tick nguồn mới nằm NGOÀI pool S1,
  **(b)** số entry thật & `net_coin` (CI block-72h) của tập mới — **cổng DỪNG: <200 event/4 năm hoặc `net ≤ 0` ⇒ bỏ.** (~1–2 h CPU.)
- **Chi phí:** **cao** — mua L2 (Tardis/Kaiko; licence/survivorship rủi ro, `PROPOSAL_MICROSTRUCTURE_DATA`) hoặc **thu liquidation forward**.
- **Rủi ro:** **cao** (mọi alt-data tới nay NULL; chi phí chìm nếu NO-GO).

### H2 — Đóng gap **LIVE↔SIM**: nhịp 1′ + `ENTRY_CASCADE` (KHÔNG phải alpha mới)
- **Vì sao chưa thử:** code sẵn + đã chứng minh OFF byte-identical (`RESULT_CADENCE_V2_PARITY` PASS 3 chân), **chưa deploy**;
  đụng đường LIVE ⇒ **cần owner duyệt**. Nhịp 1′ trên LIVE bất khả thi vì lượt ~228 s ⇒ cần cascade lọc rẻ trước.
- **Kỳ vọng:** sim `n` **KHÔNG đổi** (OFF = byte-identical); LIVE tiến gần sim **CAGR 17,3 % → ~27/34 %** (mục tiêu THẬT, không phải nghiên cứu).
- **Test rẻ nhất:** **0-sim** — shadow prove cascade (latency/fill) rồi so `LIVE_ENTRY_GRID_MIN 15→1`; cổng parity đã có.
- **Chi phí:** 0 tiền; **cần owner + deploy** (42/shadow).
- **Rủi ro:** trung bình (đã từng deploy 27/09 rồi rollback vì hàng đợi phình — cascade sinh ra để sửa đúng lỗi đó).

### H3 — **SIZING PHI-TUYẾN theo RANK/EDGE** trong top-K (thay vì chia đều)
- **Vì sao chưa thử:** **không có key nào** trong `Configs`; mọi vòng size (F_BASE, tier, vol-target, BD-size) đều **đều nhau / scale ngoài rank**.
- **Kỳ vọng `n`/chất lượng:** `n ≈ 0` (admission KHÔNG đổi) — chỉ **chất lượng (Calmar/T2)** có thể ↑ nhẹ bằng dồn vốn vào rank tốt.
- **Test rẻ nhất (sim Kaggle 0 tiền):** **1 arm** = G2+FLAT3 + `SIZE_BY_RANK` (w[i] ∝ 1/rank, chuẩn hoá Σw = K) — so Calmar_MTM/T2/T3.
- **Chi phí:** **thêm 1 key + revert-able** (~1 buổi code) + 1 chân Kaggle.
- **Rủi ro:** thấp; nhưng **xác suất thắng thấp** (`RESULT_SELECTOR_LEG_CUT` NULL; tier multiplier đã ~đều ⇒ dư địa nhỏ).

### H4 — **Path market-signal (BIG_DOWN / DCA-level) như nguồn sự kiện mở TUẦN GATE ĐÓNG**
- **Vì sao chưa thử:** BIG_DOWN **bypass gate** (`Simulator…:1326` điều kiện `!BIG_DOWN`) nên nó **có thể** nổ ở tuần gate đóng,
  nhưng chưa ai **đếm event BIG_DOWN/DCA trong tuần gate đóng** và chấm `net` của riêng chúng; `BD_THRESHOLD_FRAGILITY` chỉ **mô tả** độ nhạy, **không chọn ngưỡng**.
- **Kỳ vọng:** thêm được **một ít** sự kiện (BIG_DOWN hiện 248 leg / 4 năm) ở đúng tuần gate đóng; nhưng **edge mong manh** (PnL dao 2× theo ngưỡng).
- **Test RẺ NHẤT (0-sim, miễn phí, chạy được ngay):** đếm `n_event` BIG_DOWN/DCA **trong 132 tuần gate đóng** + phân phối `net/leg` (bootstrap) từ artifact
  sẵn có; **cổng DỪNG: <100 event hoặc net ≤ 0 ⇒ bỏ.**
- **Chi phí:** **0** (thuần đọc artifact/offline). Nếu qua cổng: + vài arm sim.
- **Rủi ro:** trung bình-cao (ngưỡng brittle).

### H5 — **GATE rolling WINDOW dài hơn (W180 / W365)** — chỉ W30/W90 đã chạy
- **Vì sao chưa thử:** `RESULT_GDV2_EVEN` chỉ quét **W30 (FAIL 4/4)** và **W90 (PASS = baseline)**; `pct` giữ `1−ρ`.
- **Kỳ vọng:** cửa sổ dài ⇒ sát ρ hơn (W90 1,24× vs W30 1,58×) ⇒ **thường n↓ hoặc ~0**; rủi ro thấp. **Không hứa mở gate.**
- **Test rẻ nhất:** 1–2 arm sim Kaggle (0 tiền) — so n/T3 vs G2.
- **Chi phí:** thấp. **Rủi ro:** thấp, **giá trị kỳ vọng ≈ 0**.

---

## 4. MỤC **BỎ** + LÝ DO (không đề xuất lại)

| mục bỏ | lý do (bằng chứng) |
|---|---|
| K×size, mở gate (scale/pct/label/feature) | 10/11 lever đã chặn; mở gate **luôn** vỡ T1/T3 (`D2`, `G1`, `B3/B4`, W30) |
| OFI V3 làm nguồn sự kiện #2 | `RESULT_OFI_V3_EVENT2` **NO-GO** (99,95 % pick nằm trong S1; net tuần đóng **âm**) |
| Regime/breadth gate (5 vòng) | đã càn; lần gần nhất FAIL chỉ vì UW 223 > 200 (nuance §2.3, **không** đề xuất lại) |
| Exit (TP/trailing/giveback/TS/pre-arm/SL-adapt) | **4 vòng + 6 chân NULL**; `EXIT_HIGH_N`: hiệu ứng **KHÔNG** tăng theo n |
| Giảm size để tăng `n` | `RESULT_SIZE_COUNT`: ×0,5 ⇒ `n` **y hệt** |
| Rút TS để giải phóng slot | `RESULT_CAPACITY_DIAG`: **không kẹt slot** (0/1644 ngày chạm trần) |
| Cắt universe để tăng chất lượng | `RESULT_COST_LIQUIDITY`: decile **kém thanh khoản lãi nhất** |
| Cross-coin/gross cap để cắt đuôi | `RESULT_TAIL_LEVER`: cap cắt **82–114 % PnL**; trần gross 70 % **không bind** |
| Track B · pump/dump detect · money-ranker · reversal/squeeze · `(a)/(b′)` | đã càn/NULL (`RESULT_TRACKB_REDFLAGS`, `PUMPDUMP_*`, `MONEY_RANKER`, `REVERSAL_*`; `(a)/(b′)` bất khả thi toán học) |

---

## 5. CẦN **DỮ LIỆU MỚI** (đánh dấu rõ)

| dữ liệu | dùng cho | nguồn / chi phí | ghi chú |
|---|---|---|---|
| **L2 order-book depth** | H1 (nguồn sự kiện #2) | Tardis/Kaiko/Amberdata — **mua** | bulk Vision **KHÔNG** có L2 thật; licences/survivorship rủi ro |
| **Liquidation (`forceOrder`)** | H1 | WS free, **không có bulk lịch sử** | chỉ thu **forward** từ nay |
| **On-chain** | H1 (dài hạn) | — | chưa khảo sát |

---

## 6. TUÂN THỦ
- **0 sim / 0 train / 0 build** (chỉ đọc doc + code). · **0 GPU.** · **KHÔNG** chạm 242/ONNX/LIVE/`NUM_FEATURES`/`extractFeatures45`.
- **KHÔNG** push file dữ liệu. · DEV **≤ 2025-12-31** (không đọc 2026/HOLDOUT).
- Pre-reg kèm: `docs/prereg/PREREG_EVENT_SOURCE_2.md` (H1 + H4 — cổng DỪNG 0-sim, viết TRƯỚC khi đo).
