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
