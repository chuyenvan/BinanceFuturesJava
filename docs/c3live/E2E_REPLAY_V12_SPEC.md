# E2E_REPLAY_V12 — Đặc tả REF + harness (phép thử (iii) "REPLAY ĐƯỜNG LỆNH")

- Prereg: `vz_e1_wt/docs/prereg/PREREG_E2E_REPLAY_V12.md` (ea6c7a5b, CHỐT 16-11). Tài liệu này là bước 2 của §8 (dev): harness + REF +
  "Đặc tả REF". Viết TRƯỚC lượt chính thức 11-05; A1 đối chiếu REF ↔ đặc tả này trước khi chạy 11-05.
- Mọi kết quả trong nhánh này (trước khi A1 duyệt) là trên **fixture PHÁT TRIỂN 10-30** (`~/claude_master/e2e1105/fx`, cửa sổ
  10-29 07:00 → 11-01 07:00 +07) — KHÔNG phải kết quả chấm.

## 1. Harness (cái gì là production thật)
- Classpath = ĐÚNG file `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2` (md5 641803565297d4065d90245e04a00f11) **đặt trước**
  `target/test-classes`; không có `target/classes`. `ReplayMain` kiểm md5 file jar chứa `C3LiveEntry`, `getResource` + `CodeSource` của 10 class
  (C3LiveEntry, C3LiveRuntime, LiveGridSizing, LiveDcaGridC3, DcaUtils, EntryGate, AIRejectFilter, GatePreFilter, TrailingStopManager,
  LiveGateRollingRatio) — sai ⇒ ghi `refused.json`, exit 3. `run_lane.sh` kiểm md5 lần nữa trước khi chạy.
- Mỗi lượt = 1 JVM riêng (class production đọc env 1 lần lúc nạp). Env JVM = `env -i` + **danh sách trắng 242** (file
  `~/claude_master/e2e_v12/env242_whitelist.raw`, lấy bằng `grep -E '^(export )?(TÊN1|…)='` với tên cụ thể, mẫu ở `.names`) + override khai trước:
  `LIVE_ADAPTER=dry, C3_CAPITAL=<lượt>, LIVE_APPLY_GRID_RATIO/LIVE_DCA_GRID_ENABLED=<true|false theo lượt>, C3_EXCLUDE_LEGACY_HELD=false,
  LIVE_IS_SHADOW_HOST=true, LIVE_GATE_ROLLING_FILE=<file tạm của lượt>` + **LỆCH (báo MASTER): `LIVE_TS_MKT_EXT=0`** (xem §5).
  `result.json.env_check` ghi tên thiếu / giá trị khác (ngoài override) — phải rỗng.
- Không gắn cứng: `C3LiveEntry` dựng y `C3LiveRuntime.buildEntry:417-427` — `.legBudgetFn(LiveGridSizing::legBudget)` (APPLY đọc env),
  `.dcaGridEnabled(LiveDcaGridC3.active())` (env), `.legacy(LegacySymbols.blocksC3 || scope.entryBlocked)`; gate ratio = `LiveGateRollingRatio.init()`
  THẬT (env MODE/PCT/DAYS/FILE; file persist ghi trước bằng các bản ghi buffer live `ts < START`); `EntryGate.GATE_DYN_SCALE`,
  `Configs.MIN_MOMENTUM_15M`, K, C3_CAPITAL đọc qua Configs/Cfg (rig cũ gán tay — đã xoá). Giá trị hiệu lực ghi ở `result.json.cfg_effective`.
- Banner C1: `[LIVE-SIZING] …=true`, `[LIVE-DCA-GRID] …=true … applyRatio=true` (static init của class trong jar), `[GATE-RATIO] LIVE BAT`
  (LiveGateRollingRatio.init trong jar), `[MINUTE-FIN] BAT` — **in bởi harness** bằng biểu thức production
  `MinuteCompletenessGuard.enabled() && finEnabled()` (banner production nằm trong `DetectEntrySignal2TradeNormal.start`, vòng main không chạy).
- Đường lệnh mỗi phút (đồng hồ giả; phút `tm`: nhịp 0 = open nến `tm` → ops (exit) → quyết định cho nến `b = tm−1` ở +6 s → nhịp 15/30/45 s):
  `GatePreFilter.runSelector` → `AIRejectFilter.entryGate` → (LEGACY sau gate) → **fin**: `MinuteCompletenessGuard.finAllows(tập fin, sym)`,
  tập fin = symbol có nến 1m chốt trong fixture ở phút `b` (lượt FIN-INJ bỏ 1 symbol) → `C3LiveEntry.onLeg` (ref = close nến `b`, giá size =
  giá nhịp hiện tại, tierMul = 1, tier3 = false). BIG_DOWN: `BigDownSelect.bypassGate` (không gate p15, như createOrderBuyRequest0 r4u).
  DCA: `book.gridStates()` × `DcaUtils.shouldDcaGrid` → `entryGate(sp=null)` → fin → onLeg(dca). Lớp thực thi y rig 11-05 (LiveBookC3,
  C3ScopedGateway, FillAccounting, C3LiveOrderExecutor, Reconciler, TrailingStopManager CLOSE_POSITION, KillSwitchEngine ACT…), sàn =
  `FakeExchange1m` (MARKET khớp tại giá nhịp, STOP kích khi giá nhịp ≤ stop, khớp tại giá nhịp) hoặc `DryGateway` production.
- Đầu ra mỗi lượt `<out>/<LƯỢT>/`: `result.json` (jar_check, env_check, cfg_effective, injections), `legs.csv` (mọi lần onLeg: outcome, budget,
  margin_before, capital, ref_px, sizing_px, leg_idx), `fills.csv` (khớp c3 sự thật sàn), `events.csv`, `outcomes.csv`, `fin_excl.csv`, `run.log`.

## 2. Đặc tả REF (`tools/e2e/ref_v12.py`, numpy/python, không Java, không đọc output replay)
Tham số: env 242 (cùng file danh sách trắng) + override của lượt + profile A3 `~/kaggle_sim/out/r1-a3-a1/prof_run.properties` (giá trị trùng env 242:
K=24, F_BASE=0,015, weights 1,1,1,1, SCALE 6,0, arm 0,07, TS_GIVEBACK_RATIO 1,0, MAX_GAP = MAX_GAP_WEAK = 0,03, time-stop 168 h, gate ratio
pct 0,999950829 / 90 ngày, DYN_SCALE 1,55, MIN_MOMENTUM_15M 0,008, skipFull bật). Hằng đặc tả không có trong env: U_MAX = 0,6; level grid
−0,50/−0,75/−0,90; trần leg 4,5 % × C; budget tối thiểu 5; EntryGate DYN_MIN 0,26787, SCORE_BASE 0,15, DYN_MULT 1,28760 (E2E_REPLAY.md / check_ref 11-05).

- **§R0 Đồng hồ** = §1 (phút `tm`, quyết định nến `b = tm−1` sau nhịp open của `tm`). Phút không có dòng sel_dump ⇒ không có leg nào (cả DCA/BIG_DOWN).
- **§R1 Chọn coin.** Hàng sel_dump phút `b` đưa vào pool khoá = selectorScore (float32; trùng khoá ⇒ hàng hạng sau đè), duyệt khoá tăng dần;
  bỏ (không đếm hạng) symbol loại A1: contractType chứa TRADIFI/TRADFI, hoặc underlyingType ∈ {EQUITY, HK_EQUITY, KR_EQUITY, CN_EQUITY, COMMODITY, FX,
  INDEX, PREMARKET}; symbol không có trong exchangeInfo ⇒ loại nếu `b > serverTime`. Đếm hạng tới K=24. Symbol đang giữ (cụm mở trong sổ REF)
  ⇒ đếm hạng, không gate. skipFull: U ≥ U_MAX ⇒ không gate, không nạp r. Gate: q(giờ h) = phần tử thứ `floor(pct·(m−1))` (partition) của các r
  có ts ∈ [h − 90 ngày, h) (buffer live ts < START + r REF tự nạp); fac = max(DYN_MIN, gv/SCORE_BASE·DYN_MULT); r = p15/(fac·GS) nạp mọi ứng viên
  được gate; PASS ⇔ p15 ≥ q·fac·GS (float32). PASS ⇒ (LEGACY: tắt vì C3_EXCLUDE_LEGACY_HELD=false) ⇒ fin (§R8) ⇒ leg PREDICT legIdx 0.
- **§R2 BIG_DOWN** (dòng bigdown fixture): không A1, không đang giữ ⇒ leg legIdx 0, không gate p15.
- **§R3 Sizing** (prereg §3): `U = marginUsed/C` (marginUsed = Σ notional các leg mở kể cả leg vừa đặt cùng phút); `U ≥ U_MAX` ⇒ U_MAX;
  `b = C·F_BASE·(1 − U/U_MAX)/Σw` (float32), cờ BẬT ⇒ `× w[legIdx]·SCALE`; `b = min(b, 0,045·C)`; `b < 5` ⇒ BUDGET_SMALL;
  `qty = floor(b/giá_size, stepSize)` (MARKET_LOT_SIZE nếu > 0, không thì LOT_SIZE); qty = 0 / < minQty / notional < MIN_NOTIONAL ⇒ SIZING.
  Giá trị tay (C = 10 000, cờ bật, 3 leg liên tiếp, bỏ làm tròn qty): 225,00 / 216,5625 / 208,4414 (prereg: 225,00 / 216,56 / 208,44).
- **§R4 Khớp:** FAKE: giá = giá nhịp lúc quyết định = open nến `tm` (× hệ số S-DCA); DRY: giá = ref = close nến `b`. Giá size = open nến `tm`.
  VWAP cụm = Σqty·giá/Σqty; "giá vào leg đầu" = giá khớp leg 0.
- **§R5 DCA grid** (cờ bật): mỗi phút, mỗi cụm mở (không mở trong phút đó, chưa thoát), `legCount = n ∈ {1,2,3}`:
  đến hạn ⇔ `close_b·f / first − 1 ≤ level[n−1]` (float32); gate DCA: `p15 ≥ MIN_MOMENTUM_15M` (NGHI VẤN N2); fin; leg legIdx = n (budget §R3).
  Tối đa 3 leg DCA (legCount 4 ⇒ hết bậc).
- **§R6 Thoát (A3, theo nến 1m `t ≥ tm` của phút khớp):** `minP = min(minP, L_t)`; P = VWAP.
  1. Chưa arm và `t − b0 > 168 h` (b0 = phút quyết định leg đầu) ⇒ TIME_STOP, giá = min(O_t, C_t).
  2. Chưa arm, `rate = (H_t − P)/P > 0,07` ⇒ arm: `SL = P·(1 + trail(rate))`, `minP = C_t`, không khớp trong nến này.
  3. Đã arm: `minP ≤ SL` ⇒ TRAIL, giá = min(SL, O_t). Không thoát ⇒ ratchet: `rate ≥ 0,07` ⇒ `SL' = P·(1+trail(rate))`; nếu SL' > SL và SL' > P ⇒
     SL = SL', `minP = C_t`.
  `trail(rate) = round((rate − min(rate·1,0, 0,03))/0,005)·0,005` (MAX_GAP = MAX_GAP_WEAK ⇒ không phụ thuộc symbolPred). X14: danh sách ngày gia hạn
  của profile A3 không có ngày 2026 ⇒ không gia hạn. Thoát "tại open" (giá = O_t) và TIME_STOP giải phóng cụm TRƯỚC quyết định của phút `t`;
  thoát khác giải phóng SAU quyết định.
- **§R7 S-DCA (lượt tổng hợp, luật khai trước, rig và REF cùng áp trên sổ của mình):** phút `tm` đầu tiên ≥ `E2E_SDCA_AT` có ≥ N=2 cụm mở,
  legCount = 1, chưa arm ⇒ chọn N cụm theo (b0, symbol). Từ nến `tm`: mọi giá O/H/L/C (và ref, close DCA) của symbol đó × f, f = 0,40 / 0,20 / 0,07
  cho các pha 10 phút liên tiếp (pha cuối giữ đến hết cửa sổ).
- **§R8 FIN-INJ:** leg PREDICT PASS đầu tiên ở phút ≥ `E2E_FIN_INJ_AT` bị bỏ khỏi tập fin ⇒ FIN_EXCL, không gửi, hạng 25 không thế chỗ.

## 3. Bộ chấm `tools/e2e/check_v12.py` (prereg §5/§6)
C1 (mọi lượt cờ bật: md5, 10/10 class từ jar, 4 banner, env_check rỗng) · E1 (R0, R0-DRY: dãy (phút, symbol) leg PREDICT ≡ REF, n ≥ 20) ·
S1 (mọi SUBMIT: |b − b_REF(U của chính lượt, legIdx)|/b ≤ 1e-5; qty = floor(b/giá_size, step) BigDecimal; 3 giá trị tay) ·
D1 (tự nhiên R0 ≡ REF hoặc KHÔNG XẢY RA; S-DCA: ≥ 2 cụm × legIdx 1,2,3, phút ≡ REF S-DCA, budget đúng, không leg 5, không leg trước bậc) ·
X1 (R0: cụm thoát khớp (symbol, b0) với REF; lý do cụm 1 leg 100 %; ≥ 98 % cùng phút, còn lại ±1; Δgiá TB ∈ [−0,8 %; 0], từng cụm ≥ −1,5 % hoặc ≤ 2 tick;
n ≥ 10, ≥ 1 TIME_STOP, ≥ 1 TRAIL, thiếu ⇒ KHÔNG ĐỦ MẪU) · F1 (FIN-INJ vs R0) · K1 (0 ERROR, 0 latch, 0 KHAN) · E2 (chỉ fixture 11-05: R-OLD ↔
`dry_submits_1105.csv` từ log dry thật, ≥ 20/23, nhãn khai trước trong `labels_1105.csv`) · §6 (đếm leg R0 hỏng ở vốn 1 000 bằng công thức §R3
cùng U; ≥ 90 % đặt được ⇒ micro = 1 000, ngược lại 4 000; kèm outcome thực của R-1000/R-4000).

## 4. NGHI VẤN (đặc tả ≠ code — KHÔNG chỉnh REF theo code; MASTER quyết)
- **N1 neo time-stop:** `LiveBookC3.reserve` đặt `tsFirstLeg = nowMs` (lúc gửi, ≈ b0 + 66 s); TrailingStopManager cắt khi `now − tsFirstLeg > 168 h`
  ⇒ trên rig cắt ở nhịp open của nến `b0 + 168 h + 2'` với giá open; sim A3 cắt ở nến `b0 + 168 h + 1'` giá min(O, C). Lệch 1 phút có hệ thống
  ⇒ nếu > 2 % cụm thoát là time-stop, X1 "≥ 98 % cùng phút" sẽ FAIL trên 11-05.
- **N2 gate DCA:** production + rig cho leg DCA qua `entryGate(sp = null)` ⇒ cần p15 thị trường ≥ 0,008 ở phút đến hạn; prereg §3 không ghi cổng
  này. REF theo comment production "sim gọi entryGate cho mọi leg trừ BIG_DOWN" — cần MASTER xác nhận đây là đặc tả A3.
- **N3 X14:** env 242 `LIVE_TS_MKT_EXT=1` nhưng replay phải đặt 0 (TsMktExt khởi chạy đọc ALT_EW Aerospike); prereg §7 đã ghi X14 không đủ dữ liệu,
  nhưng override này KHÔNG có trong danh sách override khai trước ⇒ báo MASTER.
- **N4 vốn sizing:** prereg §3 dùng `C = C3_CAPITAL` cố định cho cả U và b; code dùng `capital = C3MainEquity.capital()` =
  min(C3_CAPITAL, equity c3 (gồm lỗ chưa chốt), available + margin) cho cả U và b. Thấy trên S-DCA 10-30: capital 9 723 / 9 557 / 9 267 ⇒
  budget DCA thấp hơn công thức prereg 4,8–14,1 % (khớp 1e-5 nếu thay C bằng capital code). Bộ chấm giữ C = C3_CAPITAL (không nới);
  kết quả theo capital code chỉ ghi "báo cáo". Ở 11-05, mọi leg vào khi equity < 10 000 (sau lỗ) sẽ FAIL S1 theo prereg.
- **N5 phút thoát trailing:** A3 (`BLOCK_INTRABAR_LOOKAHEAD=true`) arm trong nến t thì KHÔNG khớp trong nến t; TrailingStopManager arm ở nhịp
  15 s rồi stop có thể kích ngay các nhịp sau CÙNG nến ⇒ thoát sớm 1 phút. 10-30: 18/22 cùng phút (82 %), 4/22 lệch −1' (SL trùng REF tới 1e-9).
  Tiêu chí X1 "≥ 98 % cùng phút" khó đạt ở 11-05 nếu tỉ lệ này lặp lại — cần MASTER quyết (không nới tiêu chí ở đây).
- E2 (11-05): bộ chấm chỉ lấy SUBMIT dry thật có phút quyết định < 11-06 07:00 +07 (prereg "23 SUBMIT 22:52–22:53"); nhãn lệch phải nằm trong
  `tools/e2e/labels_1105.csv` (symbol,label), tạo + commit TRƯỚC lượt chính thức (run_official kiểm worktree sạch + HEAD = commit A1 duyệt).
- (kết quả chạy thử 10-30: `docs/c3live/E2E_REPLAY_V12_DEV_RESULT.md`).

## 5. Giới hạn rig so với production (ngoài prereg §7)
Vòng main `DetectEntrySignal2TradeNormal` không chạy (createOrderBuyRequest0 guard, cầu dao mật độ, sổ giấy twin, `liveBookFull` đọc U sổ giấy —
rig dùng U sổ c3 thật, price_realtime D-03, tierMul/TIER_3 = 1/false); banner `[MINUTE-FIN]` do harness in; tập fin = có nến Vision
(không mô phỏng ingestor/bin fin thật); X14 tắt; `Configs` đọc `config.properties` của worktree Oracle (không phải của 242) cho key không có
trong env; Vision sạch hơn live; executor đồng bộ; Fake khớp tại giá nhịp (không sổ lệnh, không MARK).

## 6. ERRATA 1 (vòng 2, `PREREG_E2E_REPLAY_V12_ERRATA1.md` 33633d41) — đặc tả thay đổi / bổ sung
Mục này THAY các chỗ tương ứng ở §1–§5 (chỗ nào mâu thuẫn thì §6 thắng). Vẫn chỉ phát triển trên **fixture 10-30**; 11-05 chưa dựng.

- **Fixture dev mở rộng** `~/claude_master/e2e_v12/fx1030` = `e2e1105/fx` chép nguyên (sha cũ giữ trong `manifest.extended_from`) + 2 đầu vào
  THÔ mới do `prep_fixture.py --extend-from` (fixture 11-05 dựng mới cũng có): `mkt.csv.gz` = Vision 1m của MỌI symbol có file trong
  `parity_v11w/vision/klines_1m/<ngày UTC>` (752 symbol ở 10-30, cột symbol,t,o,h,l,c,qv; qv = quote_volume Vision cột 8), t ∈ [START − 60′, END);
  `ts_ext.csv` = mọi dòng log live `[TS-EXT] flag day=… flag=… final=…` trong `pull242/<ngày>/logs/full.log@*.gz`;
  `manifest.mkt.died_symbols_sim` = `DIED_SYMBOLS` của `~/kaggle_sim/out/r1-a3-a1/config.properties` (BTCDOMUSDT, USDCUSDT).
  Rig và REF đọc CÙNG `mkt.csv.gz` nhưng TỰ tính riêng (rig: hàm production trong jar; REF: numpy).

- **§R0' Thứ tự tầng quyết định** (sửa §R0/§1; = live `DetectEntrySignal2TradeNormal:433-516`, sim `SimulatorMarketLevelTicker1MStopLoss:341-410`
  rồi mới khối selector): phút `b` có dòng sel_dump ⇒ (1) BIG_DOWN (dòng bigdown) → (2) DCA grid nhánh "level" CHỈ khi phút là BIG_DOWN →
  (3) DCA grid nhánh "dcaAlt" CHỈ khi `isDcaAlt` → (4) selector PREDICT (bản `fa9b4cac` chạy selector trước, DCA mọi phút — lỗi harness/REF N6).
  Hai nhánh cùng phút được gọi lần lượt (giống live/sim), mỗi nhánh dùng legCount hiện tại.

- **§R8 Điều kiện thị trường của phút `b` (N6) — công thức SIM** (nguồn: `r3_wt` `research/ExportMarketData2File.java:84-131`,
  `tradecore/MarketBigChangeDetector.java:48-95` (calMarketData), `:149-181` (calRateChangeAvg), `:183-195` (getMarketStatus1M),
  `:197-201` (isDcaAlt); `tradecore/Configs.java:107` (NUMBER_TICKER_CAL_RATE_CHANGE = 15), `:511/:515` (MS_DOWN_BIG_AVG = MS_DOWN_BIG_AVG_DCA
  = −0,03157f; `SIM_MS_DOWN_BIG_AVG(_DCA)` không đặt ở 242 lẫn profile A3), `BD_FRACTION = 0`; `utils/Utils.java:457-460` (isTickerAvailable)):
  1. Tập symbol = có nến ở `b`, trừ died; bản REF chính `a1` trừ thêm loại A1 (§R1) — xem NGHI VẤN N7.
  2. `rate = (c − o)/o` (float32). `btc = rate(BTCUSDT)` (không có ⇒ 0). Bỏ symbol nếu `btc > −0,004 ∧ rate < −0,15` hoặc `rate > 0,3`
     (so sánh double như Java Float vs hằng double).
  3. `rateDownAvg = avg(khoá rate)`. `max15` = max HIGH của 15 nến KHẢ DỤNG gần nhất (≤ b) của symbol (KHẢ DỤNG ⇔ `h ≠ l ∨ qv ≠ 0`);
     chỉ symbol khả dụng ở `b` có `r15 = (c − max15)/max15`; `rateDown15MAvg = avg(khoá r15)`.
  4. `avg(khoá)`: tập khoá float32 DUY NHẤT (TreeMap), tăng dần; `period = 100`, nếu `period > size·4/5` (chia nguyên) thì `period = size·4/5`;
     cộng float32 tuần tự từ khoá nhỏ nhất tới khi `counter ≥ period` (period 0 ⇒ 1 phần tử); rỗng ⇒ 0; kết quả `total/counter` float32.
  5. `BIG_DOWN ⇔ rateDownAvg < MS_DOWN_BIG_AVG`; `isDcaAlt ⇔ rateDown15MAvg < MS_DOWN_BIG_AVG_DCA ∨ rateDownAvg < MS_DOWN_BIG_AVG_DCA/3` (float32).
  6. Ghi `ref_market.csv` (b, p15, dip, down/down15/big/alt cho `a1` và `all`). Bản `all` (= sim A3 không lọc A1, AUDIT_GOLIVE_1116_D #23) chỉ báo cáo.
  Rig (`MarketReplay.java`) lặp lại vòng live `DetectEntrySignal2TradeNormal:280-356` bằng HÀM PRODUCTION của jar (`Constants.diedSymbol`,
  `Utils.isTickerAvailable`, `Utils.rateOf2Double`, `MarketBigChangeDetector.calRateChangeAvg/getMarketStatus1M/isDcaAlt`,
  `Configs.NUMBER_TICKER_CAL_RATE_CHANGE`) trên universe A1 của rig; khác sim có chủ đích theo live: symbol không khả dụng bị bỏ hẳn; cửa sổ 15 =
  15 bản ghi có mặt gần nhất (không lọc khả dụng); không có BTC ở `b` ⇒ không quyết định gì ở phút đó. Bộ chấm báo cáo số phút cờ rig ≠ REF.

- **§R5' DCA grid** (thay §R5): như §R5 nhưng CHỈ trong nhánh (2)/(3) của §R0'; cổng `p15 ≥ MIN_MOMENTUM_15M` (0,008, phẳng, sp = null) cho
  mọi leg DCA ở CẢ REF lẫn rig (N2 = đặc tả, sim `createOrder:2286-2301`; rig đi qua `AIRejectFilter.entryGate(sp=null)` production —
  `CrashDayRig.dcaPass`).

- **§R9 Vốn tính size (N4):** `C_eff = min(C3_CAPITAL, E)`, thay `C` trong §R3 (cả U và b, trần 4,5 %·C_eff).
  `E(t) = C3_CAPITAL + Σ rp − Σ phí + Σ_vị thế mở q·(mark(s,t) − giá vào TB)` (= `C3MainEquity.c3Equity:122-152`, funding = 0 vì sàn giả không có
  funding) tính từ **khớp của SÀN** (`fills.csv`, sự thật sàn) có `ms ≤ t`: `rp` REF TỰ TÍNH = q·(giá bán − giá vào TB), giá vào TB = VWAP lệnh mua
  từ lúc vị thế 0, phí = cột fee của sàn; `mark(s,t)` = giá nhịp fixture tại t (nhịp k = (t − phút)/15 s: k0 O; nến giảm k1 H, k2 L; nến tăng k1 L,
  k2 H; k3 C; × hệ số S-DCA; không có nến ⇒ close nến gần nhất). REF vòng kín dùng E tại `t = tm` (lúc cache equity 60 s làm mới ở nhịp open,
  `ops()` → `ks.onPaper` → `c3Equity`). Bộ chấm dùng `E_REF(eq_at)` với `eq_at` = thời điểm cache mà jar thực dùng (rig đọc field
  `C3MainEquity.eqCached/eqAtMs` ngay sau `onLeg`, cột `eq`, `eq_at` của legs.csv) và kiểm `|E_REF − E_replay|/E ≤ 1e-6`; S1/D1: b_REF theo
  công thức §R3 với `C_eff_REF = min(C3_CAPITAL, E_REF)` và U của chính lượt, dung sai 1e-5.
  Đây là đầu vào DUY NHẤT REF đọc từ thư mục lượt replay (theo đúng câu chữ errata "từ fills + giá mark của fixture"); REF không đọc quyết định,
  sizing hay outcome nào của jar.

- **§R7b S-DCA tổng hợp điều kiện thị trường + p15 (E5):** giữ §R7 (chọn cụm, hệ số giá 0,40/0,20/0,07 mỗi 10′); thêm, với `st` = phút chọn
  cụm và `off = (b − st)/1′`: (i) `0 ≤ off < 30` ⇒ ĐẦU VÀO THỊ TRƯỜNG của phút `b` là TỔNG HỢP: mọi symbol có nến gốc ở `b` và có nến gốc ở
  `st − 1′` có nến phẳng `o = h = l = c = P_s` (P_s = close gốc nến `st − 1′`, qv = qv gốc ở `b`), mọi bản ghi lịch sử cũng phẳng P_s
  (⇒ `max15 = P_s`, rate = 0, r15 = 0 ⇒ KHÔNG có điều kiện), trừ (ii) `off ∈ {2, 3, 12, 22}` "dip": `c' = (float)(P_s·0,98)`, `l' = min(P_s, c')`
  ⇒ `rateDownAvg ≈ −2 % < −1,05 %` ⇒ isDcaAlt (không BIG_DOWN); (iii) `off = 2` ⇒ p15 thị trường := 0 cho cả phút (gate selector, buffer r, cổng DCA).
  Nến GIAO DỊCH không đổi (chỉ hệ số §R7). Ngoài cửa sổ: dữ liệu thật (× hệ số S-DCA cho 2 symbol bị ép, cả max15).
  Thiết kế (độc lập dữ liệu thị trường thật): bậc 1 đến hạn từ `st` nhưng không có điều kiện ở `st, st+1`; dip nhưng p15 = 0 ở `st+2` ⇒ GATE_REJECT;
  ⇒ leg legIdx 1 ở `st+3`; bậc 2 (đến hạn từ `st+10`) ở `st+12`; bậc 3 (từ `st+20`) ở `st+22`. Rig: `MarketReplay.synthBar`, REF: `Market.state(synth=…)`.

- **§R10 S-TS (lượt tổng hợp chỉ fixture dev, E1/N1):** cửa sổ 10-30 = 72 h < 168 h ⇒ không thể có time-stop tự nhiên. S-TS = R0 kéo tới
  `END + 168 h + 30′` với giá mọi symbol giao dịch đứng yên = close cuối trước END (O = H = L = C), không sel_dump ⇒ không vào lệnh mới; cụm còn mở
  ở END không arm ⇒ TIME_STOP 168 h. Rig: `E2E_FLAT_EXT=1 E2E_END=…` (`ReplayData.bar`), REF: `--flat-ext --end …`. Chỉ để thử bộ chấm X1
  (TIME_STOP), KHÔNG vào kết luận, KHÔNG chạy ở lượt chính thức.

- **X1 (E1/N1, E3/N5, E4, E2/N3)** — bộ chấm: cụm khớp (symbol, b0); lý do cụm 1 leg ≡ REF;
  `X14_HOAN`: cụm TIME_STOP mà ngày UTC của phút thoát REF có flag X14 thật = ON (`ts_ext.csv`, dòng `final=true` cuối của ngày, không có thì dòng
  cuối) ⇒ loại khỏi X1, báo số lượng; TIME_STOP: phút thoát ≡ REF (0 lệch), giá khớp ∈ [L, H] của nến đó (× hệ số), loại khỏi trung bình Δ;
  `ARM_CUNG_NEN` (có `TRAIL_ARM` hoặc `TRAIL_SL` của symbol trong CHÍNH phút thoát replay): được lệch đúng −1 phút (hoặc 0), báo riêng Δ;
  còn lại ≥ 98 % cùng phút, dư ≤ ±1; giá: mọi cụm thoát stop/trailing: stopPrice jar ĐẶT (sự kiện `TRAIL_STOP_PLACED` có cid = cid lệnh bán đã
  khớp) so với SL REF ≤ 2 tick; giá khớp sàn giả chỉ BÁO CÁO (TB, min); n ≥ 10, ≥ 1 TIME_STOP, ≥ 1 TRAIL sau khi loại X14_HOAN.
- **D1:** tự nhiên (R0) vào kết luận: có DCA ⇒ (phút, symbol, legIdx) ≡ REF và mỗi leg: phút có điều kiện thị trường REF (`big_a1 ∨ alt_a1`),
  p15 REF ≥ 0,008, budget ≡ công thức với C_eff_REF (1e-5), E (1e-6); không có ⇒ KHÔNG XẢY RA. S-DCA: như cũ + cùng các kiểm từng leg.
- **C1:** tập override khai báo phải ĐÚNG = {LIVE_ADAPTER, C3_CAPITAL, LIVE_APPLY_GRID_RATIO, LIVE_DCA_GRID_ENABLED, C3_EXCLUDE_LEGACY_HELD,
  LIVE_IS_SHADOW_HOST, LIVE_GATE_ROLLING_FILE (đường dẫn dữ liệu), LIVE_TS_MKT_EXT} và `LIVE_TS_MKT_EXT = 0` (E2/N3).
- **E5 config:** lượt replay KHÔNG đọc `config.properties` của worktree: `run_lane.sh` chép `tools/e2e/config_replay.properties` (mỗi key có nhãn
  nguồn) vào cwd của JVM. Configs bắt buộc có file (thiếu ⇒ `System.exit`) và các key của file KHÔNG có mặc định trong code JAR, nên: hạ tầng
  (Aerospike/đường dẫn/luồng) = giá trị GIẢ có chủ đích (replay không kết nối); `DIED_SYMBOLS = BTCDOM,USDC` (= 242 = sim, AUDIT_GOLIVE_1116_D #24);
  `SPECIAL_SYMBOLS` rỗng (không nơi nào đọc). `result.json`: `config_properties_replay` (key → [nhãn] giá trị),
  `worktree_config_keys_KHONG_doc`, `cfg_effective."Cfg.asked_khong_dat_env_(mac_dinh_JAR)"` (key code đã hỏi mà env lượt không đặt ⇒ mặc định JAR).
- **E5 khoá chạy 1 lần:** `run_official_1105.sh` ghi `~/claude_master/e2e_v12/OFFICIAL_1105.lock` (đường cố định) NGAY khi bắt đầu; đã có ⇒ từ chối,
  trừ khi `E2E_ERRATA=<tên errata mới>` chưa từng dùng trong khoá; tên errata + khoá vào `result.json` (`errata_mo_lai`, `official_lock`).
- **Thử tiêm lệch** `tools/e2e/inject_v12.py` (dev): stopPrice +3 tick; TIME_STOP +1′; DCA dời sang phút không điều kiện; REF bỏ cờ thị trường /
  p15 < 0,008 ở phút có leg; E × (1 + 2e-6) ⇒ đều phải FAIL.

### NGHI VẤN mới (vòng 2)
- **N7 universe điều kiện thị trường:** sim A3 không lọc A1 (AUDIT_GOLIVE_1116_D #23, "LỆCH đã biết"), live lọc A1 + bỏ TradFi. REF chính dùng
  universe A1 (nhất quán §R1); bản `all` báo cáo. Trên 10-30: xem `ref_summary.market.flag_a1_ne_all`.
- **N8 key config không có mặc định JAR:** errata E5 yêu cầu "dùng mặc định trong code của JAR" nhưng `DIED_SYMBOLS`, `SPECIAL_SYMBOLS` và các key hạ
  tầng không có mặc định (Configs.getString = properties.get; thiếu file ⇒ exit) ⇒ dùng file khai báo nhãn (trên). `DIED_SYMBOLS` lấy giá trị 242
  theo audit (không đọc env.sh 242).
- **N9 thứ tự tầng quyết định:** bản `fa9b4cac` (rig + REF) chạy selector trước BIG_DOWN/DCA; production và sim làm ngược lại — đã sửa theo
  production (ảnh hưởng U_before của leg PREDICT cùng phút với leg BIG_DOWN/DCA, và tập "đang giữ" của selector).
- **N11 E4 × N5 (dời SL trong chính phút thoát):** X1 giá theo E4 = stopPrice jar ĐẶT vs SL REF ≤ 2 tick cho MỌI cụm stop/trailing. Khi jar
  ratchet SL ở nhịp 15 s trong CHÍNH phút thoát (nhãn `ARM_CUNG_NEN`), stop jar cao hơn SL REF (sim chỉ ratchet ở cuối nến, sau kiểm khớp) —
  10-30: QUSDT b0 10-30 07:26 (+07): stop jar 0,054512 vs SL REF 0,0542679 = +244 tick (+0,45 %) ⇒ X1 FAIL (bộ chấm KHÔNG miễn, không nới).
  MASTER quyết: miễn 2 tick cho cụm `ARM_CUNG_NEN` (báo riêng như E3) hay giữ FAIL.
- **N10 E thời điểm cache:** equity c3 cache 60 s; trên rig cache làm mới ở nhịp open (`eq_at = tm`) — bộ chấm báo phân bố `eq_at − b` (giây).
  Ở live nhịp làm mới phụ thuộc lịch gọi thật; sai khác chỉ ảnh hưởng mức mark của UPL.

## 7. ERRATA 2 (vòng 3, `PREREG_E2E_REPLAY_V12_ERRATA2.md` 593e7f45) — REF-nhịp (E7) + xử lý tạm N7–N10 (E8)
Mục này bổ sung §6 (chỗ mâu thuẫn thì §7 thắng). Vẫn CHỈ fixture phát triển **10-30**; 11-05 chưa dựng, chưa chạy.

- **§R6n REF-nhịp (E7)** — lớp phủ ĐỘC LẬP trong `ref_v12.py` (numpy/python, không Java, không đọc output/sự kiện replay), chạy trên
  CÙNG cụm (symbol, b0, leg, VWAP theo thời gian) của REF-nến vòng kín; không đổi quyết định/sizing/U của REF (REF-nến vẫn là sổ
  vòng kín cho E1/S1/D1).
  1. **Chuỗi giá nhịp** (dựng lại từ ĐẦU VÀO fixture `klines.csv.gz`, đúng nhịp rig được cấp — `CrashDayRig.run`/`applyPrices`):
     phút `t` có 4 nhịp `k = 0..3` ở `t + 0 / 15 / 30 / 45 s`. **Quy tắc thứ tự H/L:** nến giảm (float32 `C < O`) ⇒ `O, H, L, C`;
     còn lại (tăng hoặc phẳng `C ≥ O`) ⇒ `O, L, H, C`. Giá × hệ số S-DCA của symbol ở phút `t`; S-TS sau END: nến phẳng (= rig `ReplayData.bar`).
     (Ghi chú: lời giao việc ghi "+15/30/45/60 s"; rig thật đặt O ở +0 s và C ở +45 s — REF theo rig; giá nhịp đứng yên giữa các nhịp
     nên +45 s ≡ "trước +60 s".)
  2. **Thứ tự trong 1 nhịp** (= rig: `applyPrices` → sàn giả kích STOP → `ops()` → `TrailingStopManager.step`): (a) sàn: cụm đã arm và
     giá nhịp ≤ SL ⇒ thoát TRAIL (TRAIL_LOSS nếu SL ≤ P), ghi SL tại lúc thoát; (b) trailing với giá nhịp `p`: `rate = (p − P)/P` (float32);
     chưa arm và `rate > 0,07` ⇒ arm, `SL = P·(1 + trail(rate))`; đã arm và `rate ≥ 0,07` ⇒ `SL' = P·(1+trail(rate))`, nhận nếu `SL' > SL ∧ SL' > P`.
     Stop đặt/dời ở nhịp `k` chỉ kích từ nhịp `k+1` (kể cả nhịp 0 phút sau = gap tại open). `trail()`, ngưỡng, P = VWAP: y §R6.
  3. **Time-stop không đổi** (§R6.1): nhịp 0 của nến `t`, chưa arm, `t − b0 > 168 h` ⇒ TIME_STOP, giá `min(O_t, C_t)`.
  4. **Lịch**: nhịp 0 xử lý TRƯỚC quyết định của phút (VWAP cũ); nhịp 1–3 SAU quyết định (VWAP đã gồm leg vừa khớp ở +6 s, kể cả cụm vừa
     mở). Khác REF-nến: REF-nến chỉ áp VWAP mới từ nến sau (chỉ ảnh hưởng cụm có DCA).
  5. **Nhịp live** (không mô phỏng riêng vì giá rig chỉ đổi ở 4 nhịp): live `C3LiveRuntime` ops 5 s (`:75` `OPS_PERIOD_MS`), exit 10 s
     (`:78` `EXIT_EVERY_MS` — KHÔNG phải 15 s như lời giao việc), equity/book 15 s (`:77`); rig chạy `ops()` (gồm trailing) ngay sau mỗi
     nhịp giá 15 s ⇒ mọi lịch ≤ 15 s nhìn cùng 4 giá ⇒ tương đương trên rig. Live thật: giá trong nến liên tục, thứ tự H/L thật không biết
     ⇒ REF-nhịp là QUY ƯỚC đo mức lệch live↔sim, không phải mô hình đúng của live.
  6. **Đầu ra** `ref_clusters.csv` thêm: `nhip_exit_bar, nhip_reason, nhip_exit_px, nhip_k, nhip_sl, nhip_label, nhip_ev_phut_thoat`;
     `nhip_label = 1` ⇔ REF-nhịp có ARM hoặc dời SL ở một nhịp TRONG chính phút thoát của nó (= nhãn `ARM_CUNG_NEN`, TIME_STOP luôn 0).
     `ref_summary.nhip` = số cụm thoát, danh sách nhãn, số cụm có phút thoát nhịp ≠ nến.

- **X1 (E7, thay phần ARM_CUNG_NEN của §6):** nhãn `ARM_CUNG_NEN` lấy từ `nhip_label` của REF (KHÔNG từ sự kiện replay).
  Cụm có nhãn: `|stopPrice jar ĐẶT − nhip_sl| ≤ 2 tick` VÀ phút thoát jar ≡ `nhip_exit_bar`. Cụm không nhãn: như ERRATA 1 E4 (REF-nến:
  ≥ 98 % cùng phút, dư ≤ ±1′; stopPrice vs SL REF-nến ≤ 2 tick; TIME_STOP 0 lệch + giá ∈ [L, H]). Bộ chấm vẫn tính "arm-cùng-nến của jar"
  (TRAIL_ARM/TRAIL_SL của symbol trong CHÍNH phút thoát jar, trừ TIME_STOP) CHỈ để đối chiếu: khác nhãn REF-nhịp (hai chiều) ⇒ X1 FAIL
  (`ok_nhan`, danh sách `nhan_lech`). Báo riêng `ARM_CUNG_NEN_bao_cao_rieng`: mỗi cụm có nhãn — Δphút jar↔nhịp, Δphút nhịp↔nến,
  ΔSL nhịp↔nến (tick, %), Δstop jar↔nhịp (tick).
- **Thử tiêm mới** (`inject_v12.py`, S-TS): T7 stopPrice jar +3 tick ở cụm có nhãn ⇒ FAIL; T8 bỏ nhãn REF-nhịp của cụm có nhãn ⇒ FAIL;
  T9 gắn nhãn cho 1 cụm TRAIL không nhãn ⇒ FAIL.

- **E8 (xử lý tạm, CHỜ A1):**
  - **N7:** REF chính dùng universe A1 (§R8 bản `a1`); bộ chấm báo `N7 REF universe A1 vs khong loc` = số phút cờ (BIG_DOWN, isDcaAlt)
    của `a1` ≠ `all` (`ref_summary.market.flag_a1_ne_all`).
  - **N8:** key `config.properties` không có mặc định trong JAR: liệt kê trong `result.json.config_properties_replay` (key → [nhãn] giá trị)
    và in lại ở bộ chấm (`N8 key config khong mac dinh JAR`). `DIED_SYMBOLS` KHÔNG có trong danh sách trắng env 242 (là key
    config.properties, không phải env) ⇒ giá trị 242 theo AUDIT_GOLIVE_1116_D #24 (BTCDOM,USDC; jar đọc ra {BTCDOMUSDT, USDCUSDT}); A1 xác nhận.
  - **N9:** giữ thứ tự production (§R0'); A1 đối chiếu sim.
  - **N10 cache equity 60 s — REF mô hình như đặc tả:** nguồn `C3MainEquity.java:57` (`MAX_TTL_MS = 60_000`), `:96` (ttl = min(MAX_TTL, ttl)),
    `:124` (dùng cache nếu `now − eqAtMs < ttl`), `:148-149` (làm mới `eqAtMs = now`), `:163-164` (`capital()` gọi `c3Equity()`);
    `C3LiveRuntime.java:253-254` (ttl = env `LIVE_C3_EQUITY_TTL_MS`, mặc định 60 000), `:77`/`:520-521` (live gọi `c3Equity()` mỗi 15 s);
    `C3LiveEntry.java:254` (`capital.capital()` lúc vào lệnh). REF: gọi ở mỗi nhịp ops của rig (+0/15/30/45 s) và lúc quyết định (+6 s),
    làm mới khi `now − at ≥ 60 s` ⇒ `eq_at` (cột mới `ref_legs.csv`), E = `equity_at(fills, eq_at)`. Bộ chấm báo `N10 eq_at REF vs jar`.
    **Chưa chắc là chủ đích:** ở live pha làm mới (so với phút) phụ thuộc lúc vòng ops khởi động ⇒ tuổi E lúc quyết định ∈ [0, 60) s
    (rig/REF: 6 s); không thấy tài liệu nói cache 60 s là thiết kế cho sizing ⇒ **A1 phân xử**; A1 bác ⇒ ghi "LỆCH-CHƯA-GHI", báo owner.

### NGHI VẤN mới (vòng 3)
- **N12 nhịp exit live 10 s** (`C3LiveRuntime:78`) ≠ "15 s" trong lời giao việc/ERRATA2; không ảnh hưởng rig (giá đổi mỗi 15 s) nhưng
  mức lệch live↔sim đo bằng REF-nhịp chỉ đúng dưới quy ước 4 nhịp O→H/L→C.
- **N13 VWAP sau DCA:** REF-nhịp áp VWAP mới từ nhịp 1 của phút khớp DCA, REF-nến từ nến sau; chỉ chạm cụm có DCA đã arm — 10-30 không có.

## 8. ERRATA 3 (vong 4, `PREREG_E2E_REPLAY_V12_ERRATA3.md` 409e1144) - E9/E10/E11 + ghi nhan E12 (van ban ASCII)

- **E9 R-OLD = cau hinh dry that cua NGAY fixture (A1 R2 B1).** CHI luot `R-OLD`: `C3_EXCLUDE_LEGACY_HELD=true` + danh sach LEGACY
  cua ngay fixture; moi luot khac giu `false` (prereg muc 1). Nguon (`tools/e2e/legacy_src.py`, D = ngay +07 cua START fixture):
  (1) `pull242/<D>/run/legacy_symbols.csv` neu co; (2) nguoc lai dong log `[LEGACY] managed N: ...` CUOI CUNG co thoi diem <= START
  trong `pull242/<D>/logs/full.log@*.gz` (gio log +07). Ghi ra `<luot>/wd/run/legacy_symbols.csv` (= `LegacySymbols.DEFAULT_FILE` trong
  cwd jar - DUNG duong production, jar nap 1 lan; khong goi `reconcile` vi khong co vi the that) + `<luot>/legacy_E9.json`
  (nguon, md5 nguon, so dong, ms, danh sach, md5 csv, moi lan danh sach DOI trong [START, END) kem file/dong/them/bot, log phu toi dau).
  `result.json.legacy_E9` = json nguon + tap jar THAT SU nap (`LegacySymbols.getInstance().all()`, `excludeLegacyHeld()`, md5 file).
  Khong lap duoc danh sach => luot R-OLD TU CHOI (exit 6). 11-05: `pull242/2026-11-05/run/` KHONG co `legacy_symbols.csv` (chi
  `gate_ratio_live.bin.gz`) => nguon = `pull242/2026-11-05/logs/full.log@1793928180_135437659.gz` (kiem bang `ls`; CHUA chay
  legacy_src cho 11-05). Dev 10-30 (START 10-29 07:00 => `pull242/2026-10-29`): dong 427867 (10-29 06:59:10), n = 44; trong cua so
  doi 2 lan (ZECUSDT vao 10-29 11:18, ra 11:21) - chi bao cao.
  - Nhan E2: `tools/e2e/labels_1105.csv` (commit `0c198ba9`, chi header `symbol,label,nguon`, rong; `*.csv` bi gitignore => `add -f`).
    Bo cham `labels_check`: header DUNG `symbol,label,nguon`; nhan thuoc tap khai truoc {LEGACY-11-05, JAR-R4Q-FIN2-BIGDOWN-SEL,
    JAR-R4Q-FIN2-UNIVERSE-A1, EXCHANGEINFO}; `LEGACY-11-05` bat buoc cot `nguon` (dong log chi ra danh sach doi trong ngay); symbol
    khong trung; file thieu => TU CHOI => E2 FAIL. E2 con FAIL neu R-OLD khong chay voi `excludeLegacyHeld=true` + tap LEGACY khac rong.
    Nguong E2 GIU NGUYEN. `run_official_1105.sh` tien kiem: labels da commit + hop le, nguon LEGACY 11-05 ton tai (ls).
- **E10 U va eq_at DOC LAP (A1 R2 B2).** REF (`--fills`) ghi `ref_u.csv`: `used_before_usd` cua moi cid = tong gia von vi the DANG MO
  (BUY: + qty x gia khop; SELL: - qty x VWAP vi the) tinh tu `fills.csv` theo thoi gian (on dinh trong cung ms = thu tu file) NGAY TRUOC
  dong BUY dau tien cua cid. Bo cham: `U_REF = used_REF / C_eff_REF`, `U_jar = margin_before / capital` (jar);
  budget ky vong tinh tu `used_REF` (KHONG con dung `margin_before` cua jar). Them vao S1 va D1: `|U_REF - U_jar| <= 1e-6` cho MOI SUBMIT
  (thieu U_REF => FAIL). `ref_market.csv` them cot `eq_at` = thoi diem cache equity cua REF tai quyet dinh phut b (mo hinh cache 60 s,
  doc lap jar); `E_REF = equity_at(fills, eq_at_REF)` (truoc day tinh tai eq_at do JAR bao). S1 (va D1): `|E_REF - E_jar| / E_REF <= 1e-6`
  VA `eq_at_jar == eq_at_REF` (ms) cho moi SUBMIT. Dien giai: ERRATA3 viet "eq_at (equity jar dung khi tinh size) == eq_at REF (sai so
  tuong doi <= 1e-6)" - ap 1e-6 cho GIA TRI equity va so khop thoi diem cache CHINH XAC (1e-6 tuong doi cua ms epoch = 30 phut, vo nghia);
  MASTER xac nhan (NGHI VAN N14).
- **E11 sua loi harness (khong doi tieu chi).**
  - (a) REF: cum co nhan `ARM_CUNG_NEN` (REF-nhip thoat va co ARM/doi SL trong chinh phut thoat): trang thai "dang giu" (book: held cho
    selector, U, DCA, S-DCA) GIAI PHONG tai nhip thoat REF-nhip - nhip j = 0 (truoc quyet dinh) => phut do da trong; j >= 1 => trong tu
    quyet dinh phut sau (= jar). REF-nen van chay tiep cum do (danh sach `ghosts`) CHI de dien cot `exit_*` bao cao. Cot moi
    `giai_phong_nhip` (`phut:j`) trong `ref_clusters.csv`; `ref_summary.nhip` them `giai_phong_theo_nhip(E11a)`,
    `nen_thoat_truoc_nhip_co_nhan` (chieu nguoc - REF-nen thoat TRUOC REF-nhip - khong xu ly, chi dem; ly thuyet = 0 vi REF-nhip min
    hon). X1: cum co nhan ma REF-nen con OPEN cuoi cua so => cham theo REF-nhip (A1 R2 rui ro 6). Thu: `tools/e2e/test_ref_e11a.py`
    (fixture tam tu dev 10-30: symbol vao lai top-K ngay phut sau; REF moi vao lai, REF cu 1302fd81 coi dang giu).
  - (b) Khoa chay 1 lan: `tools/e2e/official_lock.sh` (goi tu `run_official_1105.sh`): kiem + ghi trong flock rieng; khoa da co =>
    chi errata MOI duoc mo; `chmod u+w` -> ghi dong -> `chmod a-w` -> DOC LAI thay dung dong va errata xuat hien dung 1 lan, sai bat ky
    buoc nao => TU CHOI (khong chay). Thu: `tools/e2e/test_official_lock.sh` (thu muc tam, 12 ca, gom khoa da `chmod a-w`, thu muc chi
    doc, khoa la thu muc, flock khong mo duoc).
  - (c) `result.json`: `env242_file_md5` (md5 file gia tri env 242 da dung), `labels_1105_file`, `labels_1105_md5`; bo cham in lai
    md5 tu tinh (`INPUT md5 (ERRATA3 E11)`).
  - (d) NHIP: production `C3LiveRuntime` ops 5 s (`:75`), exit 10 s (`:78` `EXIT_EVERY_MS`, KHONG phai 15 s), onBook/equity 15 s (`:77`).
    Rig (`CrashDayRig.run/ops`): ops moi 5 s (+0, +5, quyet dinh +6, +10 ... +55 s), `mgr.step` (exit) khi `now - lastExit >= 10 s`
    (+0/+10/../+50 s), equity 15 s; tail sau END 36 x 5 s (= 3 phut nhu cu). **Gia DAU VAO chi co 4 moc/phut** (+0/+15/+30/+45 s = O,
    cuc 1, cuc 2, C cua nen 1m; nen giam O,H,L,C, con lai O,L,H,C) - do la DO PHAN GIAI cua du lieu dau vao, KHONG phai nhip exit; nhip
    exit doc gia moc gan nhat <= thoi diem. REF-nhip: j = 0..5 o +10j s, gia = moc `PIDX[j] = [0,0,1,2,2,3]`; nhip 0 truoc quyet dinh,
    1..5 sau; equity REF goi +0/+15/+30/+45 s + quyet dinh +6 s (khong doi). Hai nhip doc cung 1 moc khong doi trang thai trailing (kiem
    stop p <= SL sau arm luon sai; ratchet cung rate khong tang SL) => ket qua thoat chi doi THOI DIEM (ms) khop, khong doi gia/phut,
    tru khi moc C nam o +50 s thay vi +45 s. Cot `nhip_k` = chi so nhip exit 0..5 (truoc: 0..3).
- **E12 (ghi nhan phan xu A1 R2, KHONG doi tieu chi):**
  - N7: dieu kien thi truong live tinh tren universe A1, sim khong loc - khac biet co chu dich da ghi (AUDIT_GOLIVE_1116_D, D7); phan
    "ticker kha dung" (live bo han ticker khong kha dung + cua so 15 ban ghi, rig n = 512-513 vs sim/REF n = 517) la lech nho chua ghi
    => THEM vao danh sach gioi han cua gate (10-30: 0/4319 phut khac co).
  - N8: `DIED_SYMBOLS=BTCDOM,USDC` lay tu `config.properties` (Configs.getString = properties), khop repo va sim.
  - N9: thu tu BIG_DOWN -> DCA -> selector: live = sim (dung sau ERRATA 1).
  - N10: cache equity 60 s - thuoc khac biet N4 da ghi; rang buoc bang `eq_at` (E10).
  - N12, N13: cung ho N5 (xu ly theo nhip trong nen); ghi vao danh sach gioi han cua gate.

### NGHI VAN moi (vong 4)
- **N14 dien giai "eq_at ... sai so tuong doi <= 1e-6" (E10):** harness ap 1e-6 cho gia tri equity va so khop ms cua thoi diem cache
  (chat hon neu MASTER muon hieu "eq_at" la thoi diem voi dung sai). MASTER xac nhan.
- **N15 danh sach LEGACY tinh:** jar nap 1 lan luc khoi dong (nhu production khi khong co vi the that de reconcile); neu danh sach 11-05
  doi trong cua so (legacy_E9.json `doi_trong_cua_so`) thi replay KHONG theo kip => lech phai gan nhan LEGACY-11-05 kem dong log
  (dung ERRATA3 E9). Ngay START 11-05 log `pull242/2026-11-05` phu toi 11-06 08:23 => doi sau moc do khong thay duoc (khong anh huong
  23 SUBMIT 22:51-22:53).

### Phan xu MASTER N14/N15 (vong 5, 16-11) - ap vao bo cham
- **N14 (E10):** tieu chi tren GIA TRI: E_jar (cot `eq`) vs E_REF tai `eq_at` REF sai so tuong doi <= 1e-6 (GIU, FAIL neu vuot) va
  |U_REF - U_jar| <= 1e-6 (GIU). So khop MOC thoi gian `eq_at` jar == `eq_at` REF tung ms chat hon errata => CHI BAO CAO (S1:
  `E."eq_at_lech_moc(BAO CAO, N14)"` = so SUBMIT lech moc + |lech| lon nhat ms + vi du; D1: `eq_at_khop(BAO CAO, N14)`), KHONG lam FAIL.
  Moi kiem khac giu nguyen. Code: `check_v12.py` `e_check` (lech moc -> bao cao), `dca_leg_checks` (bo dieu kien moc khoi `ok`).
- **N15 (E9/E2):** danh sach LEGACY cua R-OLD nap MOT LAN luc khoi dong (`run/legacy_symbols.csv`, tu dong `[LEGACY] managed` gan nhat
  truoc START). Neu log ngay fixture cho thay danh sach DOI trong ngay (`legacy_E9.json` `doi_trong_cua_so`) thi phan lech o E2 do doi
  do phai gan nhan `LEGACY-11-05` (nhan da khai trong prereg) KEM dong log lam bang chung. Bo cham CHI chap nhan nhan nay khi cot `nguon`
  = `<duong dan log>:<so dong>` (duong dan khong rong, so dong nguyen > 0) - `check_v12.legacy_evidence_ok`; thieu/sai => TU CHOI file
  nhan (E2 FAIL). Khong doi code cham E2 nao khac.
