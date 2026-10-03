# LIVE sizing (E2) + DCA grid sổ giấy C3 (E5) + profile `c3_live` — 2026-10-03

Branch `feat/live-sizing-c3live` (gốc `module` d673b204). **Chưa merge** — chờ MASTER review.
Bối cảnh: `docs/audit/PARITY_LIVE_VS_SIM_20261003.md` (E2, E5), `DEPLOY242_G2FLAT3_READINESS_20261002.md` §6/§8.
Phạm vi đã duyệt: code 3 việc trên đường LIVE + deploy SHADOW Oracle (paper). **Không đụng 242** (chỉ đọc 242 qua `parity_check.py --fetch`).

## 1. Tóm tắt

| Việc | Commit | Key (mặc định) | Shadow sau deploy |
|---|---|---|---|
| E2 sizing live = managerBudget × `gridLegWeightRatio(legIdx)` | `fix(live-sizing)` 257dcc89 | `LIVE_APPLY_GRID_RATIO` (false) | true, `SIM_F_BASE` 0.09 → **0.015**; parity E2 **PASS** 787.50 |
| E5 DCA grid leg 1–3 cho sổ giấy C3 | `feat(live-dca-grid)` 737d4390 | `LIVE_DCA_GRID_ENABLED` (false) | true; E5 = MISSING (chưa có cụm nào rơi −50%) |
| profile `c3_live` (cổng push + kill-switch) | `feat(c3_live)` 6ef07289 | `LIVE_PROFILE=c3_live`, `LIVE_ENTRY_ENABLED`, `LIVE_KILL_SWITCH_FILE` (run/KILL_SWITCH) | **không bật** (shadow giữ `c3_shadow` + `SHADOW_NO_PUSH=true`) |

Mọi key mặc định = hành vi HEAD. Class diff base→final: chỉ 4 class live + 3 class mới (§5).

## 2. Thiết kế

### 2.1 E2 — `LiveGridSizing` (tradecore/selector)
- `DetectEntrySignal2TradeNormal.createOrderBuyRequest`: ngay sau `TradeUtils.managerBudget(...)`, nếu `LIVE_APPLY_GRID_RATIO=true` ⇒ `budget = managerBudget × DcaUtils.gridLegWeightRatio(legIdx)` — đúng phép nhân sim `SimulatorMarketLevelTicker1MStopLoss:1439-1444`.
- Đặt **trước** trần 4.5% equity C3 (trần áp lên leg thật, không bị vô hiệu) và trước `tierMultiplier` (giao hoán; shadow `TIER_FLAT=1`).
- `legIdx`: 0 = leg mở cụm (selector/BIG_DOWN/market); leg DCA-grid sổ giấy = `legCount` cụm (= `gridLegCount` sim khi `DCA_SIGNAL_GATE` tắt); leg DCA của vị thế THẬT legacy (`getDCAProduction`) = −1 ⇒ **không** nhân ratio (không biết bậc) + WARN 1 lần.
- Kiểm double-scale: không chỗ nào khác trên đường live (`trading/`, `tradecore/selector/`, `BudgetManager`) nhân `DCA_GRID_SCALE`/`gridLegWeightRatio`; chỉ sim (`DcaProcessor.capByDrop`, `BudgetManagerSimple`, Simulator). Workaround `SIM_F_BASE=0.09` phải bỏ khi bật (đã bỏ trên shadow) — nếu giữ 0.09 + bật cờ ⇒ ×6 lần nữa.
- Log INFO 1 lần lúc khởi động (`BinanceOrderTradingManager.main` nạp lớp sớm).

### 2.2 E5 — `LiveDcaGridC3` + `ShadowBookC3`
- Ứng viên = `DcaUtils.shouldDcaGrid(firstEntryPrice, priceClose nến 1', legCount)` trên các cụm `ShadowBookC3` — cùng hàm `DcaProcessor.getDCA` nhánh `DCA_GRID_ENABLED`, cùng **2 điểm gọi** của sim (trong nhánh `levelChange != null` và nhánh `isDcaAlt`).
- Leg đi qua **đúng** `createOrderBuyRequest(DCA_LEVEL1, symbolPred=null)` như sim `createOrderBUY(..., null)`: `prediction==null` chặn, `entryGate`, TIER_3 chặn DCA, `managerBudget` (U/U_MAX trên sổ giấy, `null` ⇒ dừng), ratio(legIdx) qua 2.1, trần 4.5%, `CONC_CAP_PERCOIN` trên `perCoinMargin`. Guard `isHolding`: leg DCA giấy chỉ nhồi cụm đang giữ; leg khác giữ guard cũ.
- Ghi: `ShadowBookC3.openPos(..., level)` → `addLeg` (VWAP/legCount như sim `mergeOrder`) + `legs.csv` (`sym,ts,leg_idx,entry,qty,leg_margin,level,first_entry,avg_entry`) **chỉ khi cờ bật**; `ledger.csv` không đổi format. `open_positions.csv` đã lưu `leg_count/first_entry` ⇒ sống qua restart 4h/12h.
- Không áp cho legacy/lệnh thật (`getDCAProduction` giữ nguyên).
- Khác sim còn lại (biết trước): `CONC_CAP_AGG_DCA` live dùng `symbol2Pos`/`liveEquitySnapshot` thật (fail-open với sổ giấy) — B0 không bật key này nên không ảnh hưởng; `DCA_ROUND_CAP`/`DCA_SIGNAL_GATE` B0 tắt, live không port.

### 2.3 `c3_live` — `LiveProfileC3`
- `LIVE_PROFILE=c3_live` ⇒ `on()=true` (toàn bộ C3: selector S1, arm 0.07/FLAT3, ratchet liên tục, time-stop 168h, legacy isolation, sizing sổ giấy, gate rolling…), `isLive()=true`.
- `forceNoPush()` = `NOT(SHADOW_NO_PUSH=="false" AND LIVE_ENTRY_ENABLED=="true") OR exists(LIVE_KILL_SWITCH_FILE)`; thiếu env ⇒ no-push; lỗi FS ⇒ coi như có kill (fail-closed). `c3_shadow` ⇒ luôn true (không đổi); tắt ⇒ false (đường cũ đọc `SHADOW_NO_PUSH`).
- Kill-switch đọc lại **mỗi lần gọi**: lúc định tuyến lệnh, ngay trước `OrderHelper.newOrderMarket` (`processOrderNewMarketNew`), và mỗi 10 s (`processManagerPosition`) — đổi trạng thái ⇒ log WARN. Log startup: profile + `PUSH ON/OFF` + giá trị env + đường dẫn kill-switch.
- Định tuyến: C3 + `forceNoPush` ⇒ sổ giấy trực tiếp (y hệt HEAD); `c3_live` + push mở ⇒ Redis queue → `processOrderNewMarketNew` → kiểm lần 2 → sàn.
- Không bị classifier chặn bước nào.

## 3. Key

| Key | Mặc định | Đọc qua | Ghi chú |
|---|---|---|---|
| `LIVE_APPLY_GRID_RATIO` | false | `Cfg.get` (1 lần, static) | đi cùng `SIM_F_BASE` = giá trị sim |
| `LIVE_DCA_GRID_ENABLED` | false | `Cfg.get` (static) | chỉ tác dụng khi profile C3 bật; nên bật cùng key trên |
| `LIVE_PROFILE=c3_live` | — | `Cfg.get` | profile mới |
| `LIVE_ENTRY_ENABLED` | — | `Cfg.get` mỗi lần | cần `true` + `SHADOW_NO_PUSH=false` mới push. Lưu ý: tiền tố `LIVE_` = tham số giao dịch trong `Cfg` ⇒ nếu dùng `TRADING_PROFILE` phải khai báo trong profile (env sẽ fail-fast) — chưa thêm vào `INFRA_KEYS` để không đụng `Cfg` (lớp dùng chung sim) |
| `LIVE_KILL_SWITCH_FILE` | `run/KILL_SWITCH` | `Cfg.getOr` (static) | tương đối WorkingDirectory |

## 4. Test

- Mới: `LiveGridSizingTest` (6): OFF ⇒ trả đúng tham chiếu managerBudget; OFF leg0 = **131.25**; ON leg0 = **787.5** (±0.01, và trùng bit với `managerBudget *= gridLegWeightRatio(0)` của sim); leg 1–3 = 787.5, leg 4 (hết bậc) = 0; legIdx<0 / null không đổi; throttle U=0.3 ⇒ 393.75.
- Mới: `LiveDcaGridC3Test` (5): chuỗi giá 100→…→2 ⇒ live sinh **3 leg** tại 49 / 24 / 9.5 (bậc 1/2/3), size trùng **bit** với chuỗi "sim" (`shouldDcaGrid` + `managerBudget(U tăng dần) × gridLegWeightRatio(gridLegCount)`); size leg1 theo throttle; U≥U_MAX ⇒ null; OFF ⇒ 0 leg; giá thiếu ⇒ bỏ.
- Mới: `LiveProfileC3LiveTest` (5): (1) c3_shadow luôn no-push kể cả env mở; (2) c3_live thiếu/thiếu-một/giá trị rác ⇒ no-push; (3) đủ `SHADOW_NO_PUSH=false`+`LIVE_ENTRY_ENABLED=true` ⇒ push; (4) đủ env + file kill-switch (temp file thật) ⇒ no-push; + profile tắt: `forceNoPush()=false`, `isLive()=false`.
- Hồi quy cũ giữ PASS: `LiveProfileC3Test`, `LegacyIsolationTest` (forceNoPush==on()==false khi tắt), `ShadowBookC3Test`.
- Toàn bộ `mvn -o test`: **226 test, 0 fail** (trên code commit 3); build cuối (`mvn -o package`, chạy test) EXIT 0.

## 5. Byte-identical khi OFF

- **Class diff** (`target/classes` module d673b204 vs HEAD, `diff -rq`): khác đúng 5 file + 3 file mới, đều đường live:
  `LiveProfileC3`, `ShadowBookC3`, `BinanceOrderTradingManager`, `DetectEntrySignal2TradeNormal` (+`$TickGate` chỉ do LineNumberTable dịch dòng); mới `LiveGridSizing`, `LiveDcaGridC3`, `LiveDcaGridC3$GridState`. **Không** class sim/tradecore dùng chung nào đổi (`Configs`, `Cfg`, `DcaUtils`, `TradeUtils`, `DcaProcessor`, Simulator… byte-identical).
- Lớp duy nhất trong closure của sim là `LiveProfileC3` (gọi từ `TradeUtils.calRateMin…ForTradingStop` → `armRate/armRateFor`): khi `LIVE_PROFILE` không đặt (sim/B0) ⇒ `ON=false`, `LIVE=false` ⇒ cùng nhánh trả `def` như HEAD.
- Đường live khi OFF: `LIVE_APPLY_GRID_RATIO` tắt ⇒ khối `if (LiveGridSizing.on())` không chạy; `LIVE_DCA_GRID_ENABLED` tắt ⇒ `active()=false` ⇒ không gọi `paperDcaGrid`, guard `isHolding` đi nhánh `else` y cũ, không tạo `legs.csv`; `c3_shadow` ⇒ `forceNoPush()` luôn true ⇒ định tuyến y cũ. Probe `L` trên env B0/242 (flag tắt) = 131.25 = managerBudget.
- **Kaggle P0** (1 kernel, `tools/kaggle_sim.py` HEAD, recipe `research/analysis/selector_ablation_b0ref.py`: profile `r4_kg0_k16_f015_g155` md5 0e0caef0 + B0OV, bundle `sim-x1-2021-bundle`, jar dataset `sim-jar-c3live` = jar FINAL): md5 printDone **ff3ce513edf2316088a4b5ac464f76dc** vs ff3ce513 ⇒ **PASS**; jar sha256 fe239c645c2b86e1; n_trades 2517; equity 131908.
  (Lần 1 `c3live-p0` lỗi hạ tầng: jar dataset thiếu file profile → kernel dừng ở bước nạp profile, chưa chạy sim; lần 2 `c3live-p0b` bổ sung profile.)

## 6. Parity + deploy shadow

**Trước** (jar 8f3ee52c, `SIM_F_BASE=0.09` workaround, restart 21:51): parity E2 shadow PASS nhờ bù env; E5 FAIL (không có grid).

**Deploy** (2026-10-03, shadow Oracle, `sudo systemctl restart shadow-c3`):
- Backup: `~/shadow_c3/app.bak_20261003_225901/` (target/jar 8f3ee52c + conf + run + bin + config.properties/logback/redis.config; không log).
- Jar: sha256 `fe239c645c2b86e1fa73a592e6beb8f41a358637efb4d681f10fe13e29b78883` (HEAD commit 3; restart cuối 23:04:05). Lần restart 22:59:43 dùng jar 6ba0a0b6 (trước khi thêm log khởi động) — chỉ khác `BinanceOrderTradingManager.class`.
- `conf/env.sh`: `SIM_F_BASE=0.09` → `0.015` (ghi chú lý do + rollback ngay trên dòng); thêm `LIVE_APPLY_GRID_RATIO=true`, `LIVE_DCA_GRID_ENABLED=true`, `LIVE_IS_SHADOW_HOST=true` (jar có `Live242WriteGuard` ⇒ shadow ngừng ghi `ai_pred_1m` vào 242 — được phép, giảm ghi 242; **không** bật gate rolling, việc 10-07 17:15 giữ nguyên). GIỮ `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`.

**Sau** (log `full.log` + journal):
- Khởi động: `[LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true … ratio(leg0)=6.0 F_BASE=0.015`, `[LIVE-DCA-GRID] … levels=[-0.5,-0.75,-0.9] legs=3 weights=[1,1,1,1] scale=6.0 applyRatio=true`, `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true`, `[NO-WRITE-242] GHI Aerospike 242 BI TAT`.
- `/proc/<pid>/environ` có `JAVA_TOOL_OPTIONS=-Xms3g -Xmx3g…`; `jcmd VM.flags`: Initial/MaxHeapSize = 3221225472.
- 15': `[GATE]` 14/14 phút, n_pass=0 (gate chưa arm — đúng kỳ vọng tới 10-07), 0 Exception/OOM/ERROR trong full.log, NRestarts 0; journal chỉ còn nhiễu có sẵn (stub key `-2015` mỗi phút, NPE `BudgetManager.updateBudget` lúc khởi động — đã có ở restart 21:51 trước deploy).
- 60': xem khối dưới.
- Parity `PARITY_WORK=<bản sao> python3 research/parity/parity_check.py live --fetch --probe` (fetch 242 chỉ-đọc): **E2 shadow PASS 787.50 USDT (live/sim 1.0000)** với `F_BASE=0.015` (probe `L 35000 0 0` = 787.5 bit 1145364480 = managerBudget 131.25 × ratio 6); 242 FAIL 131.25 (chưa áp). A1/A1b/A1c/A2/A5 PASS (F_BASE shadow = B0, không còn "lệch giải thích được"). E4 PASS. **E5 shadow MISSING** (code + cờ có; 0 leg grid vì sổ giấy 0 cụm mở, n_pass=0) — PASS khi `legs.csv` có `leg_idx>=1`. Các mục còn lại không đổi so với audit 10-03.
- Checker sửa có chủ đích (commit doc): `FormulaProbe` thêm lệnh `L eq m legIdx` = `LiveGridSizing.legBudget` (reflection; jar cũ ⇒ managerBudget); E2 dùng `L` cho live; E5 đọc env + `legs.csv`.

```
Sun Oct  4 00:05:00 +07 2026
2549553    01:00:55 3876844
lines=1521 GATE=60 GATE_minutes=60
Exception=0 OOM=0 ERROR=0 WARN=19
      6  WARN  [pool-1-thread-1] c.b.c.a.f.e.e.LiveFeatureDump: 🟠 [LIVE_FEAT_DUMP] mo file feat_dump/sel_dump_N_N.csv.gz (selector cung tick).
      6  WARN  [pool-1-thread-1] c.b.c.a.f.e.e.LiveFeatureDump: 🟠 [LIVE_FEAT_DUMP] mo file feat_dump/feat_dump_N_N.csv.gz (33 feature + ts/symbol/p15_out + 4 market).
      5  WARN  [pool-1-thread-1] c.b.c.a.f.e.e.LiveFeatureDump: 🟠 [LIVE_FEAT_DUMP] XOAY file theo 10 phut -> dong feat_dump_N_N.csv.gz + sel_dump_N_N.csv.gz
      1  WARN  [pool-1-thread-1] c.b.c.a.f.e.e.LiveFeatureDump: 🟠 [LIVE_FEAT_DUMP] BAT — se ghi toi da N tick vao feat_dump/*.csv.gz (tran N MB, xoay=10 phut). Chi ghi, khong doi logic.
      1  WARN  [main] c.b.c.a.o.e.OnnxInferenceManager: ⚠️ Scaler missing: ../storage/ai_ml_data/ai_models_reg_v3/Scaler_Return15M.onnx
NO-WRITE-242=2 LIVE-DCA-GRID due=0 SHADOW open/add-leg=0 would-BUY=0
04/10/2026 00:03:06.455 INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: [GATE] scale=1.5500 topk=16 base=0.00800 thr=[0.03088..0.04112] n_cand=16 n_rej=16 n_pass=0
04/10/2026 00:04:06.446 INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: [GATE] scale=1.5500 topk=16 base=0.00800 thr=[0.03117..0.04114] n_cand=16 n_rej=16 n_pass=0
  75 /home/ubuntu/shadow_c3/ledger.csv
   2 /home/ubuntu/shadow_c3/open_positions.csv
  77 total
ls: cannot access '/home/ubuntu/shadow_c3/legs.csv': No such file or directory
-- journal 23:04..00:05 (ngay ro rang):
journal lines=2294 exc_total=65 exc_2015=63 NPE=2 OOM=0
      2 java.lang.NullPointerException
(NPE = BudgetManager.updateBudget stub-key: luc khoi dong + hang gio, co san truoc deploy: 3 lan trong 21:51-22:59)
```

## 7. Bị chặn / rủi ro còn lại

**Bị chặn:** không bước nào bị classifier chặn. Không đụng 242 (chỉ đọc qua `--fetch`).

**Rủi ro / chưa xong:**
1. **`c3_live` push CHƯA AN TOÀN để bật** (code chỉ là cổng + kill-switch như yêu cầu). Khi push mở, lệnh đi đường thật nhưng: (a) sizing/U vẫn lấy `ShadowBookC3` (equity giấy `PAPER_EQUITY`+PnL giấy, margin giấy) — fill thật không ghi vào sổ ⇒ U≈0, throttle không hãm; (b) guard `isHolding` C3 xem sổ giấy ⇒ dựa vào `symbol2Pos`/`symbolLocked` của đường thật để chống mua trùng (selector/BIG_DOWN có, `processOrderNewMarketNew` không); (c) exit vị thế thật đi `processDynamicTP_SL` (arm 0.07/ratchet 1.0 qua `armRateFor`) nhưng **time-stop 168h chỉ có trong sổ giấy**; (d) DCA grid (E5) chỉ cho sổ giấy, vị thế thật vẫn DCA phản xạ cũ và **không** nhân ratio (legIdx=-1); (e) `BudgetManager.addMarginRunning` bị bỏ khi `on()`. ⇒ Cần một vòng "real-book adapter" trước khi `LIVE_ENTRY_ENABLED=true` ở bất kỳ đâu.
2. `LIVE_ENTRY_ENABLED`/`LIVE_KILL_SWITCH_FILE` mang tiền tố `LIVE_` ⇒ nếu host dùng `TRADING_PROFILE` thì phải khai trong profile (env ⇒ fail-fast). Không thêm vào `Cfg.INFRA_KEYS` để không đụng lớp dùng chung sim. Kill-switch mặc định là đường dẫn tương đối `run/KILL_SWITCH` theo WorkingDirectory.
3. E5 chưa quan sát được trên live (0 cụm mở, gate n_pass=0 tới 10-07). Leg grid đầu tiên phải được kiểm tay: `legs.csv` leg_idx, margin ≈ 787.5×throttle, đúng ngưỡng −50% từ `first_entry`.
4. Thứ tự float: live nhân ratio trước `tierMultiplier`, sim sau — trùng bit khi tier=1 (`TIER_FLAT=1` trên shadow/B0); tier≠1 có thể lệch ≤1 ulp.
5. `LIVE_IS_SHADOW_HOST=true` bật sớm hơn kế hoạch 10-07: shadow không còn ghi `ai_pred_1m` vào 242 (mục B8 audit sẽ phản ánh nguồn 242 thuần). Gate rolling vẫn tắt trên shadow.
6. Kaggle P0: xem §5 (nếu chưa xong lúc báo cáo thì byte-identical sim chỉ dựa class diff — class sim không đổi).

## 8. Việc còn cho 242 (chỉ khi owner gật)

Cùng gói, **chỉ khi owner gật**, theo thứ tự: (1) jar branch này (sau review/merge); (2) `conf/env.sh` 242: `LIVE_APPLY_GRID_RATIO=true` + giữ `SIM_F_BASE=0.015` (KHÔNG dùng workaround 0.09 cùng lúc); `LIVE_DCA_GRID_ENABLED=true` (chỉ sổ giấy 242); 242 **không** đặt `LIVE_IS_SHADOW_HOST`; (3) kiểm parity E2 242 PASS (787.5) + E5; (4) `c3_live` trên 242 **chỉ** sau vòng real-book adapter (§7.1) và owner gật riêng — mặc định vẫn `c3_shadow` + `SHADOW_NO_PUSH=true`; khi bật thì tạo sẵn `run/KILL_SWITCH` trước restart, gỡ file là bước cuối có chủ đích. Việc 10-07 17:15 (gate rolling + jar no-write + LIVE_IS_SHADOW_HOST) giữ lịch.

## 9. Rollback shadow

```
B=~/shadow_c3/app.bak_20261003_225901
cp $B/target/binance-java-sdk-1.2.4.jar ~/shadow_c3/app/target/
cp $B/conf/env.sh ~/shadow_c3/app/conf/env.sh      # SIM_F_BASE=0.09, khong co 3 key moi
sudo systemctl restart shadow-c3
```
`legs.csv` (nếu đã sinh) để nguyên — không xoá dữ liệu.
