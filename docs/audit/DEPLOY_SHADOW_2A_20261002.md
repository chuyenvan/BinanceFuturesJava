# DEPLOY_SHADOW_2A_20261002 — BẬC 2a: shadow_c3 (Oracle, PAPER) = bản tương đương 242 (G2+FLAT3)

- **Ngày:** 2026-10-02 (GMT+7). **Vai:** release engineer. **Runbook:** `docs/audit/DEPLOY242_G2FLAT3_READINESS_20261002.md` §9.1 (commit `1ede93a4`). Owner đã gật 2a.
- **Phạm vi:** chỉ shadow_c3 trên Oracle (`/home/ubuntu/shadow_c3/app`, service `shadow-c3`). 242: CHỈ đọc (`cat`/`sha256sum`/`grep` log, đọc Aerospike `get`). 0 sửa `.java`, 0 build. `SHADOW_NO_PUSH=true`, `LIVE_PROFILE=c3_shadow` giữ nguyên (kiểm bằng grep sau mỗi lần sửa env).
- **Model gate: GIỮ fold_20** (`d19fc8cd…` = 242) để cô lập biến. Selector S1/net015 = `cut20251231` (sha khớp 242).
- **KẾT QUẢ 15':** **PASS có điều kiện** — chạy ổn, heap 3 g có hiệu lực, `[GATE]` mỗi phút topk=16 scale=1,55; **NHƯNG lệch runbook 1 điểm bắt buộc:** `LIVE_GATE_ROLLING_*` phải TẮT tới khi buffer 242 đủ 7 ngày (≥ 2026-10-07 17:01) — lý do §3. Hành vi gate trong khoảng này **trùng 242** (cả hai dùng base 0,008). Bước bật lại: §7.
- **KẾT QUẢ 67':** 0 OOM, 0 ERROR mới, `[GATE]` 67/67 phút, RSS chững 3,88 GB, heap 3 G giữ; 0 lệnh giấy (đúng kỳ vọng warm-up). **Tiêu chí (7) so 242 cùng phút: xu hướng FAIL** (\|Δp50\| 0,046 pp > 0,02; thr ±1 % chỉ 29,9 %) — lệch dữ liệu đầu vào Oracle↔242, §5. **Phát hiện phụ:** shadow GHI `ai_pred_1m` vào Aerospike 242 (có sẵn, §4).
- Script (Oracle `~/claude_master/1002/deploy242/`): `s2a_pre*.sh` (tiền kiểm), `s2a_diff.sh` (so env), `s2a_apply.sh` (backup + áp), `s2a_restart.sh`, `s2a_fix.sh` (tắt ratio pre-arm), `s2a_grr.py` (đọc GRR1 strict), `s2a_aq.py` (đọc Aerospike 242), `s2a_mon.py` / `s2a_cmp*.{sh,py}` / `s2a_sel.sh` / `s2a_loop.sh` (theo dõi). Log: `s2a/mon_loop.log`.

## 1. TRẠNG THÁI TRƯỚC (17:40)

| mục | giá trị |
|---|---|
| máy | RAM 23 GB (used 7, available 15), 4 vCPU, swap 0, `/` 83 % (35 G trống), load 0,05 |
| service | `shadow-c3` active từ 15:09:47 (systemd `Restart=always`; `Utils.reset` 4 h ⇒ systemd dựng lại qua `run_foreground.sh`) |
| JVM | `java -server -Xms1g -Xmx4g …` (heap từ `bin/start.sh`), RSS 2,97 GB, heap used 1,67 G / 2,24 G |
| jar | `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15` ✓ |
| env (key chính) | `TS_GIVEBACK_RATIO=0.5`, `SIM_GATE_DYN_SCALE=1.70`, `SELECTOR_RANK_TOPK=16`, `S1_MODEL_ONNX=…cut20251001`, **không** `LIVE_GATE_ROLLING_*` (gate fixed), không `SIM_TS_MAX_GAP*`/`SIM_F_BASE`/`NET015_MODEL_ONNX`/`SELECTOR_TIER1_NET015`/`TRAIL_HINGE_NET015`/`LIVE_FEAT_DUMP_ROTATE_MIN`; có `DCA_GRID_ENABLED=true`, `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK` (242 không có) |
| gate model | `../storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx` sha256 `d19fc8cd…` (= 242) |
| run/ | chỉ pid file (không có `gate_ratio_live.bin`) |
| hành vi | log mỗi tick `[MAP] chua co thang gia tri net015 … KHONG mo entry giay` ⇒ sổ giấy cũ **không thể mở entry** (thiếu net015) |

Chênh env 242 \ shadow (lọc key/secret): 16 key thiếu ở shadow, 4 giá trị lệch (`S1_MODEL_ONNX`, `SHADOW_C3_DIR`, `SIM_GATE_DYN_SCALE`, `TS_GIVEBACK_RATIO`), 6 key chỉ shadow có.

## 2. BACKUP + ÁP (17:43)

**Backup** `/home/ubuntu/shadow_c3/app.bak_20261002_1743/` (96 MB, không log; `SHA256SUMS` trong thư mục):

| file | sha256 |
|---|---|
| `target/binance-java-sdk-1.2.4.jar` | `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15` |
| `conf/env.sh` | `386c0896300d9d2e3b8e5ea6efc35378f979f53a5cb220830b160784735084c8` |
| `bin/start.sh` | `4d5520573bb8ccb3d96eb265d1c521e4d4b50fb5153ddbcd5c9558712cc195f0` |
| `bin/run_foreground.sh` / `bin/daemon.sh` | `ce92a2a9…` / `517422b1…` (không đổi) |
| `config.properties` / `logback.xml` | `d8d5e87a…` / `a080a977…` (không đổi) |
| `models/Model_Regressor_Return15M.onnx` (gate, không đổi) | `d19fc8cddd9fb11778653e4b108bb52da92ea168117efac4a407c18c0f260474` |
| `models/s1a2x1_cut20251001.onnx` (S1 cũ, không xoá) | `6067a0a2…` |
| `run/…pid` | — |

**Áp** (`s2a_apply.sh`, `set -euo pipefail`, mỗi bước kiểm sha):
1. Jar ← `~/claude_master/1002/deploy242/live242/jar242.jar` (kéo READ-ONLY từ 242 ở bậc 1) — sha256 **`8f3ee52ce4ceac8c742950cd585ba5968abd318ae5dfb1fa2748831cf9f4fcf0`** ✓ (ghi `.new` rồi `mv -f`).
2. Model: net015 `g015x26_f15_cut20251231.onnx` ← `cat` từ 242 vào `/home/ubuntu/g3x26/` — sha `41a07109…` = 242 ✓; S1 `s1a2x1_cut20251231.onnx` đã có ở `/home/ubuntu/s1_model/` — sha `8b1dcf00…` = 242 ✓; gate fold_20 `d19fc8cd…` = 242 ✓ (giữ).
3. Env (sed theo tên key + append khối `[2a 2026-10-02]`): `TS_GIVEBACK_RATIO=1.0`, `SIM_GATE_DYN_SCALE=1.55`, `S1_MODEL_ONNX→cut20251231`; comment `DCA_GRID_ENABLED`, `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK` (242 unset; live không đọc — §7 readiness); thêm `NET015_MODEL_ONNX`, `SELECTOR_TIER1_NET015=true`, `TRAIL_HINGE_NET015=true`, `TS_PRED_GAP=1`, `SIM_TS_PROFIT_MULTIPLIER=3.0`, `LIVE_GATE_ROLLING_MODE=ratio/PCT=0.999950829/DAYS=90`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`, `SIM_F_BASE=0.015`, `SIM_RATE_FEE=0.000982`, `SIM_SLIPPAGE_RATE=0.000067`, `LIVE_FEAT_DUMP_ROTATE_MIN=10`, `JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh"`.
4. `bin/start.sh`: bỏ `-Xms1g -Xmx4g` khỏi `JAVA_OPTS` ⇒ `JAVA_TOOL_OPTIONS` là **nguồn heap duy nhất** (nếu giữ, cờ dòng lệnh đè `JAVA_TOOL_OPTIONS` ⇒ heap 4 g, không kiểm được fix). sha mới `0c2b38c8…`.
5. **Kiểm env sau áp** (lọc key/secret): key chỉ 242 = `APP_HEAPSIZE`, `APP_OPTS` (không dùng — start.sh 242 không đọc); key chỉ shadow = `AEROSPIKE_BATCH_*` ×2, `EXCHANGE_INFO_PATH`, `JAVA_TOOL_OPTIONS` (hạ tầng Oracle); giá trị lệch = chỉ đường dẫn `NET015_MODEL_ONNX`, `S1_MODEL_ONNX`, `SHADOW_C3_DIR`. `config.properties` 2 bên cùng `AEROSPIKE_READ_CLUSTER=242`, `CAPITAL_START=35000`, `FILE_AI_PREDICTIONS` như nhau.

**Chọn heap 3 g, không phải 5 g:** 2a là nơi đo trước giá trị sẽ áp cho 242 ở 2b (readiness §6/§9.2 đề xuất 3 g vì 242 chỉ 7,8 GB RAM). Oracle dư RAM (avail 15 G) nên 5 g cũng được, nhưng sẽ không kiểm được cấu hình 2b. Tham chiếu: 242 hiện chạy heap mặc định ≈ 1,95 GB, 0 OOM.

## 3. SỰ CỐ KHI RESTART LẦN 1 (17:44) → LỆCH RUNBOOK BẮT BUỘC: tắt ratio tới khi buffer 242 ≥ 7 ngày

**Restart 1 (17:44:37)** với buffer 242 copy vào `run/gate_ratio_live.bin` (kéo `cat` 17:44:34; sha256 `338e3c0d5b9442b65b74f80565eaeff296e6dcc8eb9beec7c8362fe3cf5054da`; `s2a_grr.py` strict: 9 chunk CRC OK, **46 224 rec / 2 889 tick**, 2026-09-30 17:01 → 10-02 17:10, r p50 0,002074 / p99 0,006856 / max 0,014007 — trùng bậc 1; mtime file trên 242 = 17:11, tức 242 flush theo giờ).
- `Picked up JAVA_TOOL_OPTIONS: -Xms3g -Xmx3g …` ✓, nhưng **sau 3 phút không có tick nào**: `jcmd Thread.print` ⇒ `main` kẹt trong `LiveGateRollingRatio.init → loadPersistedAndSeed → seedHistory → DataManagerAerospikeFloatSim.getAiPredictionAtTime → AerospikeClient.get` (`LiveGateRollingRatio.java:174-199, 218-262`).
- **Cơ chế:** persist có `firstTs` (09-30 17:01) > now − 7d ⇒ code seed khoảng `[now − 90d, 09-30 17:01)` = ~126 700 phút (grid 1'), **mỗi phút 1 `get` đồng bộ** tới Aerospike 242 (`getClient242()` hardcode) qua WAN **RTT 62 ms** (`ss -ti`) ⇒ đo **~16 get/s** ⇒ **~2,2 h kẹt main thread mỗi lần khởi động** (0 `[GATE]`, 0 tick), lặp lại ở mỗi auto-restart 12 h cho tới khi buffer đủ 7 ngày (~10-07 17:01). Trên 242 (Aerospike local) cùng vòng này chỉ mất vài giây ⇒ bậc 1 không thấy.
- **Tệ hơn — sai tương đương:** `ai_pred_1m` **không có TTL** (namespace `default-ttl=0`, record ttl = 4294967295; key 07-01, 08-15, 09-29, 09-30 16:00 FOUND; 09-01/09-20/09-25 notfound — `s2a_aq.py`, chỉ `get`/`info`), và shadow có `storage/data/predictionSymbol` riêng từ 2026-09-18 ⇒ seed sẽ **tổng hợp r từ p15(242) + sp(shadow)** cho 09-18…09-30, `firstTs` ≈ 09-18 ⇒ **shadow ARM NGAY** (242 còn warm-up tới 10-07) và `writeFresh` ghi đè file buffer ⇒ gate shadow ≠ 242. Đã kiểm lúc 17:53: file chưa bị ghi đè (`cmp` = bản copy).

**Xử lý (17:53:08, `s2a_fix.sh`):** comment 3 key `LIVE_GATE_ROLLING_MODE/PCT/DAYS` (tag `#[2a-prearm…]`), `mv run/gate_ratio_live.bin → run/gate_ratio_live.bin.242copy_20261002_174434.unused` (không xoá; bản gốc ở `s2a/gate_ratio_live_242_20261002_174434.bin`), restart.
**Vì sao vẫn tương đương 242 về quyết định:** `AIRejectFilter.java:74-82` — ratio tắt ⇒ `thrBase = Configs.MIN_MOMENTUM_15M` (0,008); ratio bật nhưng buffer < 7 ngày ⇒ `LiveGateRollingRatio.threshold` trả **fallback base `MIN_MOMENTUM_15M`** (log 242 `[GATE-RATIO] q_t=0.008000`). Cùng `EntryGate.threshold(0.008, sp)` ⇒ cùng luật cho tới khi 242 arm. Mất: buffer tự tích luỹ của shadow + log `[GATE-RATIO]` theo giờ (không tham gia quyết định trước arm). Bật lại ở §7 — khi đó persist ≥ 7 ngày ⇒ **không seed**.
Downtime do sự cố: 17:44:37 → 17:53:08 (0 tick shadow).

## 4. PHÁT HIỆN PHỤ (có sẵn trước 2a, không do 2a gây ra) — shadow GHI vào Aerospike 242

`DetectEntrySignal2TradeNormal.java:303-308` → `saveAiPrediction1M` → `getClient242().put(ai_pred_1m, yyyyMMdd-HHmm)` (code từ `f78a5e7a`, 2026-01-24) ⇒ **mọi instance, kể cả shadow Oracle, ghi p15 mỗi phút vào Aerospike 242**. Bằng chứng (`s2a_aq.py`, chỉ đọc `gen`): key 17:40/17:43 `gen=2`; **17:46–17:52 `gen=1`** (đúng cửa sổ shadow không tick); 17:55/18:00/18:05 `gen=2`; 09-29/09-30 cũng `gen=2` ⇒ 2 writer từ trước 2a, last-writer-wins.
- Ảnh hưởng tiền thật 242: **0** — 2 chỗ 242 đọc `ai_pred_1m` cho SL (`BinanceOrderTradingManager.java:337, 524`) đi qua `calRateMinWithPredReturn15MForTradingStop`, hàm này **bỏ qua** `predReturn15M` từ FROZEN v1 2026-08-24 (`TradeUtils.java:107-123`).
- Ảnh hưởng dữ liệu: `ai_pred_1m` trên 242 là hỗn hợp p15 242/shadow (|Δ| cùng phút: trung vị 0,011 pp, max 0,17 pp) ⇒ phân tích nào coi đó là "p15 LIVE 242" bị nhiễm; `seedHistory` của 242 (khi restart lúc buffer < 7 d) đọc nguồn này.
- 2a **không** gây ra và rollback cũng **không** chặn được (jar cũ cùng code). Cần sửa `.java` vòng sau (vd bỏ ghi khi `LIVE_PROFILE=c3_shadow` trên box ≠ 242, hoặc ghi vào cluster 226). Ghi nhận cho owner.

## 5. TRẠNG THÁI SAU + THEO DÕI 67' (T0 = restart 2 lúc 17:53:08; `s2a_loop.sh` poll 10', chỉ đọc)

**Sau áp (17:53):** jar `8f3ee52c…` · env sha `0c3b1063…` · `start.sh` `0c2b38c8…` · PID 2382825 · journal `Picked up JAVA_TOOL_OPTIONS: -Xms3g -Xmx3g -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh` · `jcmd VM.flags`: `InitialHeapSize=MaxHeapSize=3221225472` ⇒ **heap flag có hiệu lực** (G1). `[LIVE_PROFILE=c3_shadow] BAT — arm=0.07 timeStop=168h ratchet=LIEN TUC … SHADOW_NO_PUSH=true (hardcode)`; `[SELECTOR_TIER1_NET015=true]`; `[OI-LIVE] inplace cold-load 649 coin`; sổ giấy nạp lại `open=0 realized=980,20` (ledger cũ nối tiếp — mốc 2a = 17:53:08). `[MAP] chua co thang gia tri net015` **hết** (net015 đã có).

| poll (phút từ T0) | RSS | heap used / 3 G | `[GATE]` phút / phút chạy | selector pass p50 / p90 (ms) | n_pass | OOM / ERROR full.log | p15 sh−242 \|Δ\| trung vị (pp) | thr_min trùng ±1 % |
|---|---|---|---|---|---|---|---|---|
| 18:00 (7') | 1,96 GB | 1,16 G | 7 / 7 | 1 227 / 30 777 (tick đầu) | 0 | 0 / 0 | 0,014 | 28,6 % |
| 18:10 (17') | 2,82 GB | 2,09 G | 17 / 17 | 604 / 2 485 | 0 | 0 / 0 | 0,011 | 17,6 % |
| 18:20 (27') | 3,31 GB | 2,30 G | 27 / 27 | 484 / 1 872 | 0 | 0 / 0 | 0,011 | 18,5 % |
| 18:30 (37') | 3,66 GB | 1,20 G | 37 / 37 | 472 / 1 768 | 0 | 0 / 0 | 0,012 | 29,7 % |
| 18:40 (47') | 3,66 GB | 2,29 G | 47 / 47 | 470 / 1 227 | 0 | 0 / 0 | 0,012 | 29,8 % |
| 18:50 (57') | 3,87 GB | 2,26 G | 57 / 57 | 463 / 844 | 0 | 0 / 0 | 0,014 | 29,8 % |
| 19:00 (67') | **3,88 GB** | 2,02 G | **67 / 67 (100 %)** | **463 / 834** | **0** | **0 / 0** | 0,019 | **29,9 %** |

- Mọi `[GATE]`: `scale=1.5500 topk=16 base=0.00800`, `n_cand=16`, thr_min 2,87–3,59 % (p15 ~0,8 % ⇒ n_pass 0 là đúng kỳ vọng warm-up/base; 242 cùng phút cũng 0/67).
- Cadence: `[PASS-TIMING] selector tick` p50 **463 ms** (242: 178 ms, bậc 1) — chậm hơn do đọc Aerospike 242 qua WAN; vẫn ≪ 60 s. Tick đầu 30,8 s (cold).
- RSS: 1,96 → 3,88 GB, **chững từ 37'** (3,66 → 3,88); heap cố định 3 G ⇒ phần native ~0,9 GB. Box: used 8,2 GB / 23,9 GB, available 15,5 GB; `/` 83 %.
- `[OI-LIVE] inplace refresh 732 coin … (stale=true) size=732 evicted=0` 18:13 (242 cùng giờ: y hệt `stale=true … evicted=0`).
- feat_dump/sel_dump xoay ~10–11' (`175300 → 180300/180400 → … → 184700/184800 → 185800/185900`) ✓.
- Exception journal từ T0: `BinanceClientException -2015` ×73 + `NullPointerException` (`Reporter.calReportRunning`) ×4 — **nhiễu có sẵn** của stub key (bản cũ cùng cửa sổ 15:10–17:44: 161 lần -2015); OOM 0; `error.log` 0 dòng mới.
- Lệnh giấy: **0** (không `[SHADOW] would-BUY/arm/closed`; chỉ dòng khởi tạo sổ). `systemctl NRestarts=0`.

**So với 242 cùng phút (criterion 7, sơ bộ — FAIL xu hướng, ghi rõ):**
- p15 (`Predict return15M`, 67 phút): sh−242 có dấu p10 **−0,173** / p50 **+0,0006** / p90 +0,033 pp, mean −0,033 pp; \|Δp50\| hai phân bố 0,046 pp > ngưỡng 0,02 pp. Trung vị khớp nhưng ~10 % phút shadow thấp hơn rõ (nghi đọc ticker phút cuối qua WAN trễ hơn 242 ghi) — chưa kết luận, cần 48 h.
- `thr=[..]` trùng ±1 % chỉ **29,9 %** phút (trung vị lệch 2,5 %, max 22,9 %). Top-16 selector (sel_dump) gần như trùng (15–16/16 coin chung, n_cand 0 lệch), nhưng `gateValue` (net015 qua map) của coin chung lệch tới 5–24 % ⇒ thr lệch theo. Không phải do legacy (0 coin chỉ-shadow nằm trong 71 legacy của 242).
- Hệ quả: tiêu chí (7) như chốt ở readiness **nhiều khả năng FAIL** do khác biệt dữ liệu đầu vào Oracle↔242 (đọc từ xa), không phải do cấu hình. Không nới tiêu chí; báo owner.

## 6. TIÊU CHÍ 48 h CÒN LẠI (chốt trước — giữ nguyên §9.1 readiness, không nới sau khi thấy số)

| # | tiêu chí | cách đo | tình trạng 60' |
|---|---|---|---|
| 1 | `OutOfMemoryError` = 0 (full.log + error.log + journal) | `s2a_mon.py` | 0 ✓ |
| 2 | ERROR mới = 0 — **ngoại trừ nhiễu có sẵn** của stub key: `BinanceClientException -2015` (positionRisk/accountInformation mỗi phút, journal) + `NullPointerException` ở `Reporter.calReportRunning` (bản cũ: 161 / 99 lần từ 10-01) | journal + full.log | 0 mới ✓ (73× -2015, 4× NPE Reporter = nhiễu cũ) |
| 3 | `[GATE]` ≥ 95 % số phút mỗi cửa sổ 6 h (sau 12 h đầu phải phủ ≥ 1 auto-restart 12 h — reset kế tiếp ≈ 05:53 & 17:53) | distinct phút | 67/67 = 100 % ✓ (chưa qua auto-restart nào) |
| 4 | RSS max ≤ heap + 1,5 GB = **4,5 GB**; sau MỖI restart journal có `Picked up JAVA_TOOL_OPTIONS: -Xms3g -Xmx3g` và `jcmd VM.flags` MaxHeapSize = 3221225472 | ps/jcmd/journal | RSS max 3,88 GB ✓; heap 3 G ✓ (mới 1 lần khởi động) |
| 5 | `[OI-LIVE] inplace refresh … evicted=0` mỗi giờ | full.log | 18:13 evicted=0 ✓ |
| 6 | ORT(fold_20)(feat_dump shadow) ↔ `p15_out` max\|Δ\| ≤ 1e-6 | offline (chưa chạy) | chưa đo |
| 7 | p15 shadow vs 242 cùng phút \|Δp50\| ≤ 0,02 pp **và** `thr=[..]` trùng ±1 % | `s2a_cmp2.py` | **FAIL xu hướng**: \|Δp50\| 0,046 pp; thr ±1 % chỉ 29,9 % phút (§5) |
| 8–11 | (2a-gate, từ khi arm ≈ 10-07 17:01 + ≥ 48 h) q_t ≠ 0,008; n_pass > 0 trong 72 h sau arm; PREDICT pass/ngày ∈ [0,34; 3,8]; `[SHADOW] would-BUY` không trên coin legacy, SL arm khớp FLAT3 ≥ 90 % | log + offline | chưa tới |
| (task) | phân bố p15 shadow ~ 242; tần suất entry giấy ≈ 1,5/ngày sau arm (≈ 1,13 PREDICT danh nghĩa + BIG_DOWN/DCA) | feat_dump, ledger | chưa tới |

## 7. BƯỚC BẮT BUỘC TIẾP THEO — "2a-arm" (≥ 2026-10-07 17:15 GMT+7, sau khi buffer 242 đủ 7 ngày và đã flush)

```bash
A=/home/ubuntu/shadow_c3/app; D=/home/ubuntu/claude_master/1002/deploy242; W=$D/s2a; TS=$(date +%Y%m%d_%H%M%S)
S242="ssh -p 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
$S242 'cat /home/chuyennd/java/v_t_m/run/gate_ratio_live.bin' > $W/gate_ratio_live_242_$TS.bin
python3 $D/s2a_grr.py $W/gate_ratio_live_242_$TS.bin        # PHAI: OK, ts dau <= now-7d (09-30 17:01), ts cuoi trong 1 h gan nhat
cp -a $A/conf/env.sh $W/env.sh.pre_arm_$TS
cp $W/gate_ratio_live_242_$TS.bin $A/run/gate_ratio_live.bin
sed -i -e 's/^#\[2a-prearm[^]]*\] export LIVE_GATE_ROLLING_/export LIVE_GATE_ROLLING_/' $A/conf/env.sh
grep -n '^export LIVE_GATE_ROLLING_' $A/conf/env.sh            # 3 dong: ratio / 0.999950829 / 90
grep -q '^export SHADOW_NO_PUSH=true$' $A/conf/env.sh && grep -q '^export LIVE_PROFILE=c3_shadow$' $A/conf/env.sh
sudo systemctl restart shadow-c3; sleep 90
grep -a -E 'GATE-RATIO\] (LIVE nạp buffer|seed)' $A/logs/full.log | tail -2   # PHAI: "nạp buffer: size=… (warm-up=armed)", KHONG co "seed lịch sử"
```
Kiểm thêm: `[GATE] base=` của shadow = q_t 242 cùng giờ (log `[GATE-RATIO] q_t=` 242) ±1 %. Nếu thấy dòng `seed lịch sử` hoặc main kẹt > 2 phút ⇒ làm lại §3 (comment 3 key, mv buffer) và báo.

## 8. ROLLBACK (về trạng thái trước 2a, < 2 phút)

```bash
A=/home/ubuntu/shadow_c3/app; B=/home/ubuntu/shadow_c3/app.bak_20261002_1743
cp -f $B/target/binance-java-sdk-1.2.4.jar $A/target/ && cp -f $B/conf/env.sh $A/conf/env.sh && cp -f $B/bin/start.sh $A/bin/start.sh && cp -f $B/config.properties $A/
[ -f $A/run/gate_ratio_live.bin ] && mv $A/run/gate_ratio_live.bin $A/run/gate_ratio_live.bin.rollback_$(date +%Y%m%d_%H%M)   # truoc 2a khong co buffer
sudo systemctl restart shadow-c3
sha256sum $A/target/binance-java-sdk-1.2.4.jar $A/conf/env.sh $A/bin/start.sh   # c389b4be… / 386c0896… / 4d552057…
journalctl -u shadow-c3 -n 3 --no-pager; ps -o rss,args -p $(systemctl show -p MainPID --value shadow-c3) | cut -c1-120   # -Xms1g -Xmx4g
```
(Model `g015x26_f15_cut20251231.onnx` ở `/home/ubuntu/g3x26/` và S1 cut20251231 để lại — env cũ không trỏ tới, vô hại.)

## 9. LỆNH ĐÃ CHẠY (theo thứ tự; script đầy đủ ở Oracle `~/claude_master/1002/deploy242/`)

| giờ | lệnh | tác động |
|---|---|---|
| 17:40 | `s2a_pre.sh`, `s2a_pre2.sh` (df/free/systemctl/ps/sha/env lọc/journal) | chỉ đọc |
| 17:41 | `s2a_diff.sh` — `ssh 242 grep ^export env.sh \| grep -viE key\|secret…`, `sha256sum` model 242 | chỉ đọc 242 |
| 17:43 | `s2a_apply.sh` — backup `app.bak_20261002_1743`, jar, `cat` net015 từ 242, sed env, sửa `start.sh` | ghi trong `~/shadow_c3/app` + `/home/ubuntu/g3x26/` |
| 17:44 | `s2a_restart.sh` — `cat` buffer 242, `s2a_grr.py`, `cp → run/`, `sudo systemctl restart shadow-c3` | restart 1 |
| 17:48 | `jcmd Thread.print`, `ss -tin`, `s2a_aq.py` (Aerospike 242 `get`/`info`) | chỉ đọc |
| 17:53 | `s2a_fix.sh` — comment 3 key `LIVE_GATE_ROLLING_*`, `mv` buffer → `.unused`, `sudo systemctl restart shadow-c3` | restart 2 (trạng thái hiện tại) |
| 17:53→19:00 | `s2a_mon.py`, `s2a_cmp.sh` (`grep` log 242), `s2a_cmp2.py`, `s2a_sel.sh` (`zcat` sel_dump 242), `s2a_loop.sh` (nohup, 8 poll × 10') | chỉ đọc |

Không có lệnh nào ghi/restart trên 242. Không `rm` dữ liệu (chỉ `mv` file buffer do 2a tạo).

## 10. ARTIFACT

Oracle `~/claude_master/1002/deploy242/s2a/`: `env242.txt`, `envsh_before.txt`, `envsh_after.txt` (đã lọc key/secret), `env.sh.after_apply_ratioON`, `gate_ratio_live_242_20261002_174434.bin` + `buf_check_*.txt` + `buf242_ls_*.txt`, `BACKUP_PATH`, `T_RESTART`, `mon.log`, `mon_loop.log`, `gate242.txt`, `sel242.csv`/`selsh.csv`, `legacy242.txt`. Backup: `/home/ubuntu/shadow_c3/app.bak_20261002_1743/` (+`SHA256SUMS`).
