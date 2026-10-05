# SHADOW2_K24_SKIPFULL_PLAN — shadow #2 = K24 + GATE_QUOTA_SKIP_WHEN_FULL (paper, Oracle)

- **Ngày:** 2026-10-05. **Trạng thái:** KẾ HOẠCH — **chờ MASTER duyệt**. Chưa tạo thư mục/service, chưa build, chưa deploy. Không chạm 242, không sửa `~/shadow_c3`.
- **Quyết định owner 2026-10-05:** shadow #2 (sau 2026-10-07, sau khi shadow #1 bật gate rolling 17:15) chạy **K24 + `GATE_QUOTA_SKIP_WHEN_FULL=true`**, GEOM OFF, paper. Shadow #1 giữ B0 K16 làm đối chứng. 242 không đổi.
- **Nguồn:** code `module` HEAD `fa6ae743` (skipFull merge `95d32a56`); sim `docs/result/RESULT_GATE_QUOTA_SKIPFULL.md`, `docs/result/GATE_SKIPFULL_DETAIL_20261005.md`; kỳ vọng K24+ON 8 seed: CAGR22 37,0 (35,6–39,3), Calmar 1,65, maxDD −22,6, UW 116, ~740 lệnh/năm; K16: 32,8 / 1,74 / −18,9 / 94 / ~520.
- **Tiêu chí lên 242:** `docs/prereg/PREREG_SHADOW2_PROMOTION.md` (vận hành, không theo PnL).
- **Thay thế:** `docs/runbooks/SHADOW2_GEOM_PLAN.md` (HOÃN).

## 0. CHẶN (phải xử lý trước khi dựng)

**C1 — jar module THIẾU live-sizing.** `origin/feat/live-sizing-c3live` (`01864c76`) **CHƯA merge** vào `module` (`git merge-base --is-ancestor` = NOTMERGED). Thiếu 4 commit:
`257dcc89` LIVE_APPLY_GRID_RATIO (E2, sửa leg0 = 1/6 sim), `737d4390` LIVE_DCA_GRID_ENABLED (E5), `6ef07289` profile c3_live + kill-switch, `01864c76` docs + parity probe L.
Jar build từ `module` hiện tại ⇒ key `LIVE_APPLY_GRID_RATIO`/`LIVE_DCA_GRID_ENABLED` **không tồn tại** ⇒ env shadow #1 (`SIM_F_BASE=0.015` đi kèm ratio) cho leg0 = 131,25 thay vì 787,5 @35000 (lỗi 1/6) và không có DCA leg 1–3. Jar shadow #1 (`fe239c64…`) có live-sizing nhưng **không có skipFull**.
- Dry-merge (`git merge-tree d673b204 HEAD origin/feat/live-sizing-c3live`, git 2.34): **1 hunk xung đột** trong `DetectEntrySignal2TradeNormal.java` — hai method private mới chèn cùng chỗ (`liveBookFull` của skipFull vs `paperDcaGrid` của live-sizing). Giải: **giữ cả hai** (không giao logic). Phần còn lại (sizing trong `createOrderBuyRequest`, `ShadowBookC3`, `LiveProfileC3`, test mới) tự merge.
- Phần src khác nhau giữa base `d673b204` và `module` chỉ là skipFull (AIRejectFilter, GateRollingRatio, Configs, DetectEntrySignal2TradeNormal, Simulator, test) — key tắt = byte-identical (P0 `ff3ce513`) ⇒ jar mới với key OFF ≙ fe239c64.

**Phương án cho MASTER (agent KHÔNG tự merge):**
- **A (đề xuất):** merge `feat/live-sizing-c3live` → `module`, giải hunk trên, `mvn test` (221 + LiveGridSizingTest, LiveDcaGridC3Test, LiveProfileC3LiveTest), build jar, ghi sha256. Truy vết sạch; shadow #1 sau này có thể dùng cùng jar.
- **B:** worktree từ `module` + merge local (không push), build jar riêng. Nhanh hơn, nhưng jar không ứng với commit nào trên remote ⇒ khó audit; chỉ dùng nếu A bị chặn.
- Kiểm jar sau build: `unzip -l` có `LiveGridSizing.class`, `LiveDcaGridC3.class`; `javap -cp <jar> com.binance.chuyennd.tradecore.Configs | grep GATE_QUOTA_SKIP_WHEN_FULL`.

**C2 — không có log skipFull riêng trên live** (xem §1b). Không chặn việc chạy, nhưng chặn đo tiêu chí (iv) của prereg trừ khi dùng proxy (§5).

## 1. Kiểm đường live (đọc code `module` HEAD `fa6ae743`)

**1a. TOPK.** Key duy nhất: `SELECTOR_RANK_TOPK` — `Configs.java:375-376` (`static final`, đọc 1 lần lúc nạp class qua `Cfg.get`). Không có `LIVE_TOPK`; profile `c3_shadow` không đụng TOPK (`LiveProfileC3.java:21` chỉ ghi chú). `Cfg.get` (`Cfg.java:129-135`): không có `TRADING_PROFILE` ⇒ `System.getenv(key)`. Shadow #1 chạy env (không `TRADING_PROFILE`), `conf/env.sh: export SELECTOR_RANK_TOPK=16` ⇒ log `[GATE] … topk=16` (`DetectEntrySignal2TradeNormal.java:498-500`; đã thấy trên `~/shadow_c3/app/logs/full.log` 05/10 08:16).
Dùng live: `DetectEntrySignal2TradeNormal.java:413` (pool rank-mode), `:473` (break khi `rank >= TOPK`), `:698-699` (cap topK), `LiveGateRollingRatio.java:220` (seed buffer lấy top-K theo TOPK).
⇒ Shadow #2: `export SELECTOR_RANK_TOPK=24` trong `~/shadow_c3b/app/conf/env.sh` — biến môi trường của tiến trình riêng, không ảnh hưởng shadow #1/242. **Không** đặt `TRADING_PROFILE` (khi có profile, `Cfg.java:104-117` gặp env `SELECTOR_*`/`GATE_*`/`LIVE_*`/`SIM_*` sẽ `System.exit(2)`).

**1b. `GATE_QUOTA_SKIP_WHEN_FULL` trên live.**
- Đọc: `Configs.java:159` (mặc định false), `Configs.java:909` trong khối `static {}` (`:823`), `Cfg.get` ⇒ env. Không phụ thuộc tiền tố `LIVE_` hay `TRADING_PROFILE` (bài học LIVE_ENTRY_ENABLED chỉ áp khi chạy profile). Banner khởi động: `DetectEntrySignal2TradeNormal.java:1309-1310` WARN `*** [GATE-QUOTA] LIVE SKIP_WHEN_FULL=ON …`.
- `bookFull`: `DetectEntrySignal2TradeNormal.java:962-966` = key bật **và** `levelChange == PREDICT_SYMBOL_TRADE` **và** `liveBookFull()` (`:920-933`). `liveBookFull`: mặc định `BudgetManager.marginRunning/balanceBasic`; khi `LiveProfileC3.on()` (c3_shadow) ⇒ **ShadowBookC3**: `equityNow(pxOpen)` (giá `getAllPriceRealtimeLegacy`) + `marginRunning()` — cùng nguồn với khối sizing của `createOrderBuyRequest`. Đầy = `TradeUtils.managerBudget(null, …) == null` ⇔ `U = margin/equity ≥ U_MAX` (`TradeUtils.java:134-137`; `U_MAX` mặc định 0,60 `Configs.java:160`, override `SIM_U_MAX` `:907`, cả sim lẫn shadow đều không khai ⇒ 0,60).
- Skip: `AIRejectFilter.java:83-86` ⇒ `GateRollingRatio.noteSkipFull` + REJECT `"BOOK FULL: U>=U_MAX …"`; không gọi `LiveGateRollingRatio.threshold` ⇒ r không vào buffer live; `noteCandidate` vẫn gọi trước (`:76-81`) — giống sim (`SimulatorMarketLevelTicker1MStopLoss.java:1345-1349`, cùng điều kiện PREDICT + managerBudget null). Leg DCA (`DCA_LEVEL1`, kể cả LIVE-DCA-GRID) không bị skipFull — giống sim.
- **Log (THIẾU):** REJECT ở nhánh PREDICT chạy chế độ gom (`:977-980`) ⇒ chỉ vào `rejectCollector` ⇒ nằm lẫn trong `n_rej` của dòng `[GATE]` và dòng tổng hợp reject (`:507-513`), **không phân biệt** với reject của gate. `GateRollingRatio.stats()` (có `skipFull=`) chỉ được in bởi Simulator (`:598`). ⇒ Live không đếm được skipFull trực tiếp. Không sửa Java (ngoài phạm vi); đề xuất MASTER: (a) thêm 1 dòng log/đếm skipFull theo giờ vào nhánh `AIRejectFilter.java:83` (cần pre-reg byte-identical OFF), hoặc (b) proxy §5.
- Chi phí: khi bật, mỗi ứng viên PREDICT gọi thêm 1 lần `getAllPriceRealtimeLegacy(openSymbols)` (≤24 lần/phút) — đọc 242, chấp nhận được, theo dõi `AEROSPIKE_BATCH_*` timeout.

**1c. Key K24 phụ thuộc khác.** Sim K24 = profile `r4_kg0_k16_f015_g155` + `B0OV` + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true` (`gate_skipfull_driver.py:41`; `gate_ablation_driver.py:397-399`). `g2_flat3.properties` = cùng profile + B0OV. **Không** đổi `CONC_CAP_PERCOIN_*` (true / 0,15), `U_MAX` (không khai = 0,60), `SIM_F_BASE` (0,015), `DCA_GRID_*`, `SIM_GATE_DYN_SCALE` (1,55). ⇒ Khác biệt giao dịch với shadow #1 **đúng 2 key**. Thiếu JUnit nào? Không thấy test cho đường live `liveBookFull` + ShadowBookC3 (GateQuotaSkipFullTest chỉ test AIRejectFilter/GateRollingRatio) — chỉ báo, không thêm.

## 2. Tiên quyết

| # | Mục | Yêu cầu | Trạng thái 10-05 |
| --- | --- | --- | --- |
| T1 | Jar | module + live-sizing + skipFull (§0 C1), `mvn test` PASS, sha256 ghi vào §7 | **CHẶN** — chờ MASTER chọn A/B |
| T2 | Shadow #1 | gate rolling bật 10-07 17:15 + chạy ổn ≥24h (shadow #1 là đối chứng, phải cùng chế độ gate) | chưa đến hạn |
| T3 | Thư mục | `~/shadow_c3b/app` (chưa tồn tại), `SHADOW_C3_DIR=/home/ubuntu/shadow_c3b` (**bắt buộc** — `ShadowBookC3.java:138` ghi `ledger.csv`/state vào đó; thiếu ⇒ ghi `.`/đè sổ #1 nếu trỏ nhầm) | chưa |
| T4 | Redis riêng | cổng 7302, `~/shadow_c3b/redis/redis-shadow.conf` (copy 7301 → thay port/dir/pid/log/nodes), service `shadow-c3b-redis`; `app/redis.config: Redis.Address=127.0.0.1:7302` | 7302 trống (ss) |
| T5 | Heap | `JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g …"` (start.sh không đặt Xmx) | — |
| T6 | Buffer gate | §4 (G1 copy 242 ≥7d hoặc G2 seed K24) — file `run/gate_ratio_live.bin` của **#2** | chờ MASTER |
| T7 | Ghi 242 | `LIVE_IS_SHADOW_HOST=true` (Live242WriteGuard chặn mọi put 242: price_realtime, ai_pred_1m, kline…) | copy từ #1 |
| T8 | Kill-switch | c3_shadow: `SHADOW_NO_PUSH` hardcode true; `LIVE_KILL_SWITCH_FILE` chỉ hiệu lực với `c3_live` (`LiveProfileC3` branch :47-48, :70). Vẫn `touch ~/shadow_c3b/app/run/KILL_SWITCH` (dây lưng) | — |
| T9 | RAM/đĩa | available ≥ 8G trước khi start; đĩa trống ≥ 20G | 15G / 26G (§6) |
| T10 | Model/dữ liệu | `S1_MODEL_ONNX`, `NET015_MODEL_ONNX`, `EXCHANGE_INFO_PATH` dùng chung (chỉ đọc); `FILE_AI_PREDICTIONS=../storage/ai_ml_data/…` ⇒ cần `~/shadow_c3b/storage/ai_ml_data` (copy hoặc symlink chỉ đọc tới `~/shadow_c3/storage/ai_ml_data`) | — |

## 3. env.sh dự kiến shadow #2

Cách tạo: `cp ~/shadow_c3/app/conf/env.sh ~/shadow_c3b/app/conf/env.sh` **sau 10-07** (khi #1 đã bỏ comment 3 dòng `LIVE_GATE_ROLLING_*`), rồi sửa đúng các dòng dưới. Mọi dòng khác giữ nguyên (C3 shadow, R4-1M, FLAT3 DCA, T170 TS, NET015, CONC_CAP 0,15, SIM_F_BASE=0.015, LIVE_APPLY_GRID_RATIO=true, LIVE_DCA_GRID_ENABLED=true, LIVE_IS_SHADOW_HOST=true, heap 3g, PAPER_EQUITY=35000).

```bash
# --- [SHADOW2 K24+SKIPFULL 2026-10-05] owner duyet 10-05; plan docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md ---
export SHADOW_C3_DIR=/home/ubuntu/shadow_c3b          # INFRA: so giay rieng (#1 = /home/ubuntu/shadow_c3)
export SELECTOR_RANK_TOPK=24                          # GIAO DICH 1/2 (#1 = 16)
export GATE_QUOTA_SKIP_WHEN_FULL=true                 # GIAO DICH 2/2 (#1 khong khai = false)
# gate rolling: GIONG #1 sau 10-07 (bat, khong comment)
export LIVE_GATE_ROLLING_MODE=ratio
export LIVE_GATE_ROLLING_PCT=0.999950829
export LIVE_GATE_ROLLING_DAYS=90
# LIVE_GATE_ROLLING_FILE: de mac dinh run/gate_ratio_live.bin (tuong doi WorkingDirectory ~/shadow_c3b/app)
```
Kiểm diff: `diff <(grep '^export' ~/shadow_c3/app/conf/env.sh | sort) <(grep '^export' ~/shadow_c3b/app/conf/env.sh | sort)` ⇒ **chỉ** 3 dòng: `SHADOW_C3_DIR`, `SELECTOR_RANK_TOPK`, `GATE_QUOTA_SKIP_WHEN_FULL`. Nếu #1 chưa bật gate rolling ⇒ diff có thêm 3 dòng `LIVE_GATE_ROLLING_*` ⇒ **DỪNG**, chưa start #2.

## 4. Buffer gate rolling (T6) — cần MASTER chọn

`LiveGateRollingRatio.loadPersistedAndSeed` (`:172-203`): nạp `run/gate_ratio_live.bin` (cửa sổ 90d); nếu persist bắt đầu sau `now−7d` ⇒ `seedHistory` (topK = `SELECTOR_RANK_TOPK`) từ `ai_pred_1m` (Aerospike) + `storage/data/predictionSymbol/<ngày>/<ts>` cục bộ; buffer < 7d ⇒ fallback base (gate phẳng 0,008).
- **G1 — copy buffer của 242 (≥7d, CHỈ ĐỌC 242)**, giống cách shadow #1 làm 10-07. Ưu: #1 và #2 khởi đầu cùng buffer. **Lệch:** buffer 242 là quần thể r của **K16**; K24 thêm 8 ứng viên/tick hạng thấp (sp cao ⇒ r thấp) ⇒ q₀.₉₉₉₉₅ của buffer K24 thật **thấp hơn** ⇒ với G1, #2 khắt khe hơn sim K24 cho tới khi buffer thay hết (90 ngày > cửa sổ đánh giá 4 tuần) ⇒ tỉ lệ lệnh #2/#1 bị kéo **xuống** trong các tuần đầu.
- **G2 — seed K24:** persist rỗng + copy `storage/data/predictionSymbol` ≥90 ngày vào `~/shadow_c3b/app/storage/data/` ⇒ seed đúng quần thể K24. Shadow #1 chỉ có **18 ngày** predictionSymbol (20260918…) ⇒ phải lấy từ 242 (chỉ đọc; chưa kiểm 242 có ≥90 ngày). Hạn chế seed (`:207-213`): không loại coin đang giữ, không tái tạo skipFull.
- **Đề xuất:** G2 nếu 242 có ≥90 ngày predictionSymbol; nếu không ⇒ G1 và ghi rõ lệch trong báo cáo tuần (tiêu chí (ii) prereg đánh giá trên cửa sổ đã khai). Quyết định ghi vào §7 **trước khi start**.

## 5. Các bước dựng (sau khi T1–T10 xong, MASTER duyệt)

1. `mkdir -p ~/shadow_c3b/{app,redis,storage}`; `cp -a ~/shadow_c3/app/{bin,conf,logback.xml,config.properties,redis.config} ~/shadow_c3b/app/`; `mkdir ~/shadow_c3b/app/{target,run,logs,feat_dump}` (KHÔNG copy `run/`, `logs/`, `storage/data/order`, `feat_dump/`, ledger/open_positions). Không in nội dung config.properties (có khoá).
2. Sửa `app/redis.config` ⇒ 7302; `app/bin/run_foreground.sh` ⇒ `cd /home/ubuntu/shadow_c3b/app`. `grep -rn shadow_c3[^b] ~/shadow_c3b/app/{bin,conf}` phải = 0 dòng (trừ comment).
3. Đặt jar (T1) vào `~/shadow_c3b/app/target/binance-java-sdk-1.2.4.jar`; `sha256sum` khớp §7.
4. env.sh theo §3; chạy lệnh diff §3.
5. Buffer gate theo §4.
6. Redis: copy conf ⇒ thay `7301→7302`, `shadow_c3→shadow_c3b`; unit `shadow-c3b-redis.service` (copy `shadow-c3-redis` thay đường dẫn); `redis-cli -p 7302 ping` = PONG; cluster 1 node như #1: `redis-cli -p 7302 cluster addslots $(seq 0 16383)` rồi `redis-cli -p 7302 cluster info` = `cluster_state:ok`.
7. Unit `shadow-c3b.service` = bản sao `shadow-c3` thay `WorkingDirectory`/`ExecStart` sang `shadow_c3b`, `Requires=shadow-c3b-redis.service`. `systemctl daemon-reload && systemctl start shadow-c3b-redis shadow-c3b` (chỉ khi MASTER cho lệnh dựng). Không `enable` cho tới khi qua kiểm 60'.
8. Kiểm 60' (dưới). Ghi kết quả vào `docs/audit/DEPLOY_SHADOW2_K24_<ngày>.md`.

**Rollback:** `systemctl stop shadow-c3b shadow-c3b-redis && systemctl disable shadow-c3b shadow-c3b-redis`. Giữ nguyên `~/shadow_c3b` để audit (không xoá). Shadow #1/242 không bị chạm ở bất kỳ bước nào ⇒ không cần rollback phía đó. Kiểm lại #1: `systemctl is-active shadow-c3`, `wc -l ~/shadow_c3/ledger.csv` không đổi bất thường.

**Kiểm sau 60 phút (đều phải ĐẠT):**
- `journalctl -u shadow-c3b --since -65min | grep -c 'Exception\|OutOfMemory'` = 0; `systemctl show shadow-c3b -p NRestarts` = 0.
- Banner: `*** [GATE-QUOTA] LIVE SKIP_WHEN_FULL=ON`; `[GATE-RATIO] LIVE BAT: mode=ratio pct=0.99995083 window=90d file=run/gate_ratio_live.bin`; `LIVE nạp buffer: … (warm-up=armed)`; `[LIVE_PROFILE=c3_shadow]` + PUSH tắt; `[NO-WRITE-242] GHI Aerospike 242 BI TAT (LIVE_IS_SHADOW_HOST=true …)`.
- `grep '\[GATE\]' logs/full.log | tail` ⇒ `topk=24`, `n_cand ≤ 24`, ~1 dòng/phút (#1 vẫn `topk=16`).
- skipFull: không có log riêng (C2). Proxy: tick `[GATE]` có `n_rej = n_cand` trong lúc U ≥ 0,60 tính từ `~/shadow_c3b/ledger.csv` + `open_positions` (margin mở / equity). 60' đầu kỳ vọng U < 0,60 ⇒ skip = 0.
- Sổ: `~/shadow_c3b/ledger.csv` tồn tại; `lsof -p <pid #2> | grep shadow_c3/` = 0 (không mở file của #1).
- Parity: `SHADOW_DIR=/home/ubuntu/shadow_c3b python3 research/parity/live_vs_sim_check.py --fetch --probe --out /tmp/s2_parity.json` — khác biệt **chỉ** được phép ở TOPK (24 vs 242=16) và `GATE_QUOTA_SKIP_WHEN_FULL`; probe L (LiveGridSizing, E2/E5) chỉ có sau khi merge live-sizing (T1).
- Tài nguyên: RSS java #2 ≤ 4,3G; `free -g` available ≥ 6G; `redis-cli -p 7302 info memory` ≤ 512mb.

## 6. Tài nguyên Oracle (đo 2026-10-05 ~08:20, chỉ đọc)

- RAM 23G: used 8G, buff/cache 9G, **available 15G**, không swap. RSS: java shadow #1 **3,9G** (heap 3g), `asd` 3,0G, node openclaw 1,1G. Shadow #2 cùng heap ⇒ +~4G ⇒ available ~11G; còn đủ cho job agent ≤8G (lock `~/claude_master/1002/oracle_heavy.lock`) nhưng **không** đủ cho 2 job nặng song song. Redis #2 `maxmemory 512mb`.
- Đĩa `/`: 194G, dùng 168G, **trống 26G (87%)**. `~/shadow_c3` = 1,9G (storage/data 875M/18 ngày ≈ 50M/ngày; logs 40M; feat_dump 3,9M xoay vòng). #2 ước ~1,5G/4 tuần (+~4,5G nếu G2 copy 90 ngày predictionSymbol — cần đo trước khi copy). Ngưỡng dừng: đĩa trống < 10G ⇒ stop #2 trước.
- CPU 4 nhân; #2 thêm 1 vòng selector/phút + gọi Aerospike 242 (đọc). Theo dõi `AEROSPIKE_BATCH_TOTAL_TIMEOUT_MS=20000` timeout trong log cả hai shadow tuần đầu.

## 7. Nhật ký quyết định (điền khi dựng)

| Mục | Giá trị | Ai/ngày |
| --- | --- | --- |
| Phương án jar (A/B) | — | MASTER |
| Commit jar, sha256 | — | |
| Buffer gate (G1/G2), nguồn, số ngày | — | MASTER |
| Giờ start, giờ qua kiểm 60' | — | |
| Log skipFull: thêm Java (a) hay proxy (b) | — | MASTER |
