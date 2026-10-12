# Runbook — deploy LIVE 1011 (LIVEFIX2): 1 jar gộp + sửa mapper 242 + buffer gate mới

Agent LIVEFIX2 2026-10-11. Người thực thi: **MASTER**. Branch `fix/live-1011` (KHÔNG merge `module` trước khi deploy PASS).
Script dựng sẵn (CHƯA chạy bước ghi nào): Oracle `~/claude_master/1011/livefix/deploy/` (biến chung `dep_env.sh`, log `deploy/logs/`).
Giữ nguyên `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` (không script nào đụng env.sh).

## 0. Tóm tắt (rủi ro trước)
- **Jar:** `~/claude_master/1011/livefix/jar/binance-java-sdk-1.2.4.jar`, sha256 `db181d41bd6837752638a63de99a2023cee7ad4b897d6e64924ac3d6c8f21577`,
  commit `d44202d6` = `origin/module` f9b41b28 (race fix 0594986e) + `fix/live-ticker-reread` 871f5593 (⊃ `fix/kline-ingest` 3c61f807)
  + `fix/symbol-mapper` d5c48dd9 + trần id 4096 (d61f2b70) + tool `restore` (d44202d6). Một artifact cho cả trading (`v_t_m`) và ingest (`collectData`).
  Đang chạy trên 242 + 2 shadow: `b0f23b7d…` (= kreread 871f5593).
- **Fail-fast có chủ đích:** jar mới + mapper 242 hiện tại (8 id dùng chung 843–850) ⇒ `SimpleSymbolMapper.init` ném `IllegalStateException`
  ⇒ app KHÔNG khởi động. Vì vậy thứ tự BẮT BUỘC: dừng app → sửa mapper → thay jar → start. Không bao giờ thay jar trước khi sửa mapper.
  Cửa thoát khẩn (không khuyến nghị): `export SYMBOL_MAPPER_DUP_POLICY=WARN`.
- **Thời gian dừng 242 (trading + ingest):** ước lượng 2–4 phút (stop ≤ 60 s song song, tool 3 lần ×~5 s, chép 2 jar ~2 s, start + full reload
  1000′ ~30 s). Trong lúc dừng: **46–47 vị thế LEGACY không được quản lý** (dòng `[LEGACY] managed 46` lúc 21:47), không có nến 1m mới
  (ingest tự lấp bằng pass settle startup limit=30 ⇒ dừng phải < 30′), `price_realtime` không cập nhật.
- **Rollback jar không cần rollback mapper:** jar cũ `b0f23b7d` chạy đúng với mapper đã sửa (counter = max = 949, không kiểm trùng).
  Khôi phục mapper về trạng thái trùng chỉ khi MASTER muốn (tool `restore`, mục 8).
- Kế hoạch sửa (chạy tool thật, chỉ đọc 242, 21:38): `check` rc=3 `n=933 maxId=933 gen=1284 idTrung=8`;
  `plan` 16 symbol → 934..949: MUU 934, XBI 935, BNC 936, SOXS 937, FWDI 938, TZA 939, MINIMAX 940, VRT 941, SNOW 942, ZHIPU 943, APP 944,
  SHAZ 945, GEV 946, SOFI 947, PANW 948, SKHY 949 (mỗi symbol của id trùng nhận id mới; 843–850 bỏ hẳn vì lịch sử theo id đó đã trộn).
  Nếu có niêm yết mới trước giờ deploy, plan dời lên (max+1…) — w2 dừng nếu plan ≠ 16 symbol.
- Mô phỏng trên bản sao mapper thật (JUnit `SymbolMapperSnapshotRepairTest`, snapshot 242 21:30, không ghi 242):
  jar mới + mapper hiện tại ⇒ FAIL-FAST; mapper sau plan ⇒ init PASS, 917 id cũ giữ nguyên, id mới kế tiếp 950, mọi id < 4096.

## 1. Thứ tự tổng
| # | Bước | Script (Oracle) | Ghi gì | Dừng app | Điều kiện đi tiếp |
|---|---|---|---|---|---|
| 1 | Điều kiện | `d1_precheck.sh` | không | 0 | `== PRECHECK DAT` |
| 2 | Dựng buffer gate (KLINE_FIX §C) | `d2_build_buffer.sh` (nohup, 1–2 h) | Oracle `~/kfix_gate` | 0 | `== BUOC 2 PASS` |
| 3a | Stage jar + buffer lên 242 | `d3_stage_242.sh` | file mới `*.livefix_new` | 0 | `== STAGE OK` |
| 3b–6a | Cửa sổ dừng 242 | `d4_window_242.sh` (= w1→w2→w3→w4) | mapper, jar, buffer | 2–4′ | `CUA SO XONG` |
| 6b | Kiểm 242 | `run242.sh w5_verify_242.sh` (+5′, +15′) | không | 0 | `== W5 PASS` |
| 7 | Shadow #1, #2 | `d7_shadow_swap.sh` | jar + buffer shadow | ~3′/shadow | `== shadow-c3(b) PASS` |
| 8 | Rollback | `r_rollback_242.sh`, `r_rollback_shadow.sh` | | | |
Cửa sổ cấm 12:50–13:20 và 00:50–01:20 (+07) (d1 kiểm). Tránh ±10′ quanh auto-restart 12 h (242 trading gần nhất 21:02, ingest 20:59 ⇒ ~09:00/21:00).
Mọi lệnh 242 chạy từ Oracle: `bash ~/claude_master/1011/livefix/deploy/run242.sh <script>` (ssh `bash -s`, log tee).

## Bước 1 — Điều kiện (`d1_precheck.sh`, chỉ đọc)
```bash
bash ~/claude_master/1011/livefix/deploy/d1_precheck.sh
```
Kiểm: (a) backfill KLINE_FIX §B xong: `BF DRV DONE` trong `~/claude_master/1010/kfixm_bf_drv.log`, không còn tiến trình
`kfixm_bf_drv.sh`, `kfixm_bf/verify_dry.json` `total.diff == 0` (**0 ô đổi**; `ulp_only` cho phép); (b) ngoài cửa sổ cấm; (c) sha jar;
(d) `SymbolMapperRepairTool check` trên 242 (chỉ đọc) rc=3 `idTrung=8` + in `plan`; (e) đủ `~/kfix_gate/{live,s1,s2}_new.{bin,json}`;
(f) liệt kê JVM trên Oracle (chỉ được có 2 shadow + kernel/tool đã biết — JVM nào khác đọc `config.properties` có
`AEROSPIKE_HOST=103.157.218.242` mà không `LIVE_IS_SHADOW_HOST=true` có thể GHI mapper bằng thuật toán cũ ⇒ dừng nó trước);
(g) trạng thái 242 (`w0_state_242.sh`: unit active, jar `b0f23b7d`, chưa có staged, buffer, LEGACY, JVM, đĩa).
Không đạt ⇒ dừng, không làm gì thêm. (Lúc viết runbook 21:47: backfill đang ở tháng 05 ⇒ CHƯA đạt.)

## Bước 2 — Buffer gate mới: dựng TRƯỚC cửa sổ, chép TRONG cửa sổ (sau sửa mapper, trước start)
```bash
cd ~/claude_master/1011/livefix/deploy && setsid nohup bash d2_build_buffer.sh > logs/d2.out 2>&1 &
tail -f logs/d2.out      # kết thúc bằng sha256 3 file + "== BUOC 2 PASS"; python3 d2_pass.py ~/kfix_gate/{live,s1,s2}_new.json
```
= KLINE_FIX_242 §C nguyên văn (C1 feat từ kline 242 đã backfill; C2 sp cache shadow local + live kéo `storage/data` 242 từng ngày
10-01→hôm nay; C3 build K16/K16/K24 + so file đang chạy). Model net015 `/home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx` (md5 e65e683b).
PASS: `ticks_matched/ticks_live ≥ 0,99`, `align_chosen_off_min` như nhau 3 đích, `analyse.armed=true`, `first_ts` 2026-10-01 13:00,
`q_ratio_new_over_ref_30d_6h.p50 ∈ [0,9; 1,1]`. FAIL ⇒ không deploy buffer (giữ buffer cũ; có thể deploy jar+mapper riêng, bỏ dòng buffer ở w3).
Đĩa Oracle ~0,6–1,1 G: script dừng nếu < 400–600 MB (mỗi ngày storage live tạm ≤ 500 MB, xoá ngay sau extract).

**Trước hay sau repair? — phân tích.** Live tính p15 từ feature lịch sử lấy qua `HistoryManager` theo **id** (ring `historyRing[id]`,
`FundingFeatureExtractorV2` → `getRsi14/getReturn/getVolatility…`; `DetectEntrySignal2TradeNormal:856` `EntrySignalFilter.selectCoins(…,
HistoryManager)`). Với id trùng, ring của id chỉ giữ nến của symbol duyệt sau ⇒ trước repair, p15 live của ~8 symbol "nạn nhân" = feature
của symbol song sinh. Buffer dựng lại ở §C **không đi qua Java/HistoryManager/mapper**: `kline_gate_buffer_rebuild.py feat` tính 33 feature
gate từ `kline_1m_opt` 242 theo **tên symbol** (grep: không dùng mapper/symId) ⇒ p15 trong buffer mới = ngữ nghĩa SAU repair (mỗi symbol
lịch sử riêng), bất kể dựng lúc nào. Vì vậy:
- Dựng **trước** cửa sổ (chỉ Oracle, không ghi 242) — nội dung không đổi nếu dựng sau repair (khác duy nhất: thêm tick mới).
- Chép buffer **trong cùng cửa sổ dừng với repair** (w3: sau w2, trước w4). Nếu dựng/chép SAU khi live đã chạy lại, phải dừng live lần 2
  (buffer chỉ chép khi app dừng — shutdown hook `GateRatioPersistFlush` append vào file lúc dừng) ⇒ thêm một lần 46–47 vị thế LEGACY không
  quản lý. Không được giữ buffer cũ: r của nó tính từ p15 trên nến chưa settle (KLINE_FIX) + feature song sinh.
- Sai khác còn lại (khai rõ): sp_k (pwin net015 của tick live, bậc 2) vẫn từ storage live — trước 10-11 tính bằng nến cũ và feature song
  sinh cho 8 symbol; tick trong khoảng [NOW của d2, lúc dừng] không có r (live nạp tiếp sau start). Giữ khoảng này ngắn: chạy C3 (hoặc cả d2)
  sát giờ cửa sổ.

## Bước 3a — Stage lên 242 (`d3_stage_242.sh`, chỉ thêm file mới)
```bash
bash ~/claude_master/1011/livefix/deploy/d3_stage_242.sh
```
Chép jar → `v_t_m/target/…jar.livefix_new`, `collectData/target/…jar.livefix_new`; `live_new.bin` → `v_t_m/run/gate_ratio_live.bin.livefix_new`;
kiểm sha trên 242 (`== STAGE OK`). App vẫn chạy jar cũ. Rollback: `rm` 3 file `*.livefix_new` trên 242.

## Bước 3b → 6a — Cửa sổ dừng 242 (`d4_window_242.sh` = w1 → w2 → w3 → w4, dừng ở lỗi đầu tiên)
```bash
bash ~/claude_master/1011/livefix/deploy/d4_window_242.sh      # hoặc từng bước: bash run242.sh w1_stop_242.sh … w4_start_242.sh
```
| Bước | Script 242 | Làm gì | Kiểm (script tự dừng nếu sai) | Rollback tại bước |
|---|---|---|---|---|
| 3b dừng | `w1_stop_242.sh` | kiểm staged (sha), ghi `/root/livefix_1011.ts`; `systemctl stop h242-trading & h242-ingest` song song | 0 JVM `BinanceOrderTradingManager` / `BinanceDataIngestor` (≤ 90 s) | `systemctl start h242-ingest; systemctl start h242-trading` (jar cũ) |
| 4 sửa mapper | `w2_repair_242.sh` | từ `v_t_m` (config = Aerospike 242, Live242WriteGuard cho ghi): `check` → `plan` → `MAPPER_REPAIR_CONFIRM=YES … apply /root/mapper_backup_livefix_<TS>.json` → `check` | 2 app phải dừng (JVM cũ giữ counter=933 sẽ cấp 934+ trùng id vừa sửa); `check` trước rc=3 (rc=0 ⇒ bỏ qua apply); plan đúng 16 symbol; dòng `[MAPPER-REPAIR] OK … 0 id trung`; `check` sau rc=0. Apply = 1 lệnh CAS (generation) — xung đột ⇒ không ghi gì | mapper chưa đổi nếu không có dòng OK ⇒ start jar cũ. Đã đổi ⇒ jar cũ vẫn chạy được (mục 8) |
| 5 thay | `w3_swap_242.sh` | backup `…jar.bak_livefix_<TS>` (2 app) + `gate_ratio_live.bin.bak_livefix_<TS>`; `cp` staged → jar (giữ staged cho tool restore) + buffer | sha jar = db181d41…; `cmp` buffer | `r_rollback_242.sh` |
| 6a start | `w4_start_242.sh` | ghi số dòng log hiện tại; start ingest, 3 s, start trading | 2 JVM chạy; in downtime | `r_rollback_242.sh` |
Log tool trên 242: `/root/livefix_mapper_<TS>_{check0,plan,apply,check1}.log`; backup map: `/root/mapper_backup_livefix_<TS>.json`
(map + generation, giữ vĩnh viễn để pháp y).

## Bước 6b — Kiểm 242 (`run242.sh w5_verify_242.sh`, chỉ đọc; chạy ~5′ và ~15′ sau start)
Chỉ đọc phần log MỚI sau w4. PASS khi:
- jar 2 app sha `db181d41…`;
- trading + ingest: `SimpleSymbolMapper initialized. Total: 933, Next ID: 950`; không `[MAPPER-DUP]`, không `[ID-CAP]`/`[MAPPER-CAP]`;
- ingest: `Started! [KLINE-INGEST] mode=ws_settle`, dòng `Chốt nến phút` mỗi phút;
- trading: `[TICKER-CACHE] full reload window=1000`, `[GATE-RATIO] LIVE nạp buffer: size=… firstTs=… (warm-up=false)` (= armed, không
  `seed lịch sử`), `[GATE-RATIO] q_t=…`; `[LIVE-KLINE] … correct=…` (dòng đầu ~10′ sau start, kỳ vọng ≥ 99%);
- env của PID trading: `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` (đọc `/proc/<pid>/environ`, chỉ 2 khoá này);
- `[LEGACY] managed 46|47` trở lại. Sau 24 h: `check` rc=0; niêm yết mới log `[MAPPER] cap id moi` (CAS), không `[ID-CAP]`.
Bổ sung (tay): `python3 research/parity/gate_arm_check.py <buffer đang chạy> --log logs/full.log` ⇒ PASS (q_t log = q tính lại ±1 ULP).
FAIL ⇒ mục 8.

## Bước 7 — Shadow #1/#2 (Oracle; `d7_shadow_swap.sh [c3|c3b|all]`)
```bash
bash ~/claude_master/1011/livefix/deploy/d7_shadow_swap.sh all      # tuần tự c3 rồi c3b; dừng nếu c3 FAIL
```
- **Shadow đọc mapper TRỰC TIẾP từ 242**: `AerospikeSymbolMapperStore.loadForInit` → `DataManagerAerospikeFloatSim.loadSymbolMapper` →
  `getReadClient()`; shadow `AEROSPIKE_READ_CLUSTER=242`, `AEROSPIKE_HOST=103.157.218.242`. Aerospike Oracle local (ns `ticker`) KHÔNG có
  record `symbol_mapper` (đọc 21:30: RECORD_NOT_FOUND) ⇒ **không có bản sao mapper nào cho shadow cần làm tươi**. Bản sao ns `test`/pickle 863
  chỉ dùng cho sim Kaggle (không đổi trong deploy — đổi = biến thể sim mới).
- Chỉ chạy SAU W5 PASS (script tự `check` mapper 242 rc=0, nếu không ⇒ ABORT vì jar mới fail-fast).
- Mỗi shadow: `sudo systemctl stop` → backup jar/buffer `.bak_livefix_<TS>` (TS ở `run/livefix_1011.ts`) → chép jar + `s1_new.bin` (c3, K16) /
  `s2_new.bin` (c3b, K24) → start → 150 s → kiểm `Total: 933, Next ID: 950`, `[NO-WRITE-242]`, `[GATE-RATIO] … warm-up=false`, active.
- Shadow giữ `LIVE_IS_SHADOW_HOST=true` ⇒ không ghi mapper; symbol mới chỉ nhận id CỤC BỘ trong JVM (log WARN) — đúng thiết kế.
- Rollback: `bash r_rollback_shadow.sh c3` / `c3b`.

## Bước 8 — Rollback toàn phần (ngược thứ tự)
| Đích | Lệnh (Oracle) | Kết quả | Dừng |
|---|---|---|---|
| Shadow #2, #1 | `bash r_rollback_shadow.sh c3b; bash r_rollback_shadow.sh c3` | jar `b0f23b7d` + buffer cũ | ~1′/shadow |
| 242 jar + buffer (giữ mapper đã sửa — **khuyến nghị**) | `bash run242.sh r_rollback_242.sh` | jar `.bak_livefix_<TS>` (b0f23b7d) cả 2 app, buffer `.bak_livefix_<TS>`; jar cũ init `Total: 933, Next ID: 950` | 2–3′ |
| 242 + mapper về nguyên trạng (8 id trùng) | `bash run242.sh r_rollback_242.sh "MAPPER_RESTORE=YES"` | như trên + `SymbolMapperRepairTool restore /root/mapper_backup_livefix_<TS>.json /root/mapper_prerestore_livefix_<TS>.json` (jar mới, CAS): chỉ trả id cũ cho symbol có trong backup mà id khác; symbol niêm yết sau repair giữ nguyên; từ chối nếu gây trùng với symbol mới. Sau đó CHỈ chạy jar cũ (hoặc `SYMBOL_MAPPER_DUP_POLICY=WARN`) | 2–3′ |
| Stage | `ssh … rm /home/chuyennd/java/{v_t_m,collectData}/target/binance-java-sdk-1.2.4.jar.livefix_new /home/chuyennd/java/v_t_m/run/gate_ratio_live.bin.livefix_new` | | 0 |
| Buffer Oracle | không ghi 242 ⇒ không cần | | 0 |
Lưu ý: r live append sau start vào buffer mới sẽ mất khi rollback buffer (chấp nhận, như KLINE_FIX §F). Không khôi phục mapper "cho chắc":
mapper trùng = ring/feature song sinh cho 16 symbol trên mọi jar.

## L2 — Trần id 1000 → `SymbolIdLimits.CAPACITY = 4096` (commit d61f2b70)
Max id 242 = 933 (sau repair 949), tăng ~1,06 id/ngày ⇒ trần 1000 chạm khoảng cuối 11/2026; 4096 ≈ 8 năm.
| Chỗ (file:dòng mới) | Trước | Sau |
|---|---|---|
| `ai_ml/features/export/HistoryManager.java:16` | `MAX_COINS = 1000`, `:63` id ≥ 1000 ⇒ `continue` IM LẶNG | `MAX_COINS = CAPACITY`; `:65-79` `acceptKline` id ≥ trần ⇒ `SymbolIdLimits.recordOverCap` = log ERROR `[ID-CAP]` (lần đầu mỗi symbol + mỗi 1000 lần) + đếm `overCapCount()` |
| `aerospike/DataManagerAerospikeFloatSim.java:1246,1251` | `klineArray[1000]`, `klineArray[id]=` (AIOOBE nếu ≥ 1000) | `[CAPACITY]` + `requireInRange` (IllegalStateException rõ ràng) |
| `ai_ml/hpo/kaggle/KaggleDataLoader.java:111,118` | như trên | như trên |
| `ai_ml/data/HPOSmartCache.java:216,220` | như trên | như trên |
| `ai_ml/data/CompactFileDay.java:54` | `arrLen` mặc định 1000 | `CAPACITY` (shape dựng lại = shape loader) |
| `tradecore/TickWeakBlock.java:173` | `excluded = boolean[max(n,1000)]` | `max(n, CAPACITY)` |
| `tradecore/PumpDumpFilter.java:61` | `MAX_SYMBOL = 1000` | `CAPACITY` |
| `research/SimulatorMarketLevelTicker1MStopLoss.java:122-123` | `symbol2OrdersEntry/symbol2OrderRunning[1000]` | `[CAPACITY]` (`activeRunningIds[1000]` đánh theo SỐ lệnh, không theo id ⇒ giữ) |
| `research/SimulatorForcedSeller.java:90-111` | 10 mảng `[1000]` theo id | `[CAPACITY]` |
| `ai_ml/data/SimpleSymbolMapper.java:37` | `ID_SOFT_CAP = 1000` | `CAPACITY` (log `[MAPPER-CAP]` khi cấp id ≥ trần) |
Không đổi (đã đủ/động): `CoinRankManager` mảng 5000; `AerospikeCoverageMap`/`SymbolLifecycleBuilder` `maxId+1`; `LiveOiFeatProvider.MAX_COINS=1500`
là số coin (map), không phải id. Script Python/numpy theo id ngoài phạm vi (không grep thấy mảng 1000 trong đường live).
**Chứng minh hành vi y hệt với id < 1000 (đọc code):** mọi thay đổi chỉ làm mảng DÀI thêm; ô 1000..4095 = null/0/false và không bao giờ
được ghi khi mọi id < 1000. Các vòng duyệt theo id vẫn tăng dần từ 0 và bỏ ô rỗng: `HistoryManager.cleanupZombieCoins` (`historyHead>0`),
`findPotentialLosersShort` (`count==0 ⇒ continue`), `updateHistoryArray` (`kline != null`), `TickWeakBlock.breadth` (`t == null ⇒ continue`),
`CompactFileDay.compress` (`k == null ⇒ continue`); `TickWeakBlock.buildExcluded` gọi thêm `getSymbol(1000..4095)` = `UNKNOWN-id` (không
trong `diedSymbol`, không side-effect). Không phép tính nào dùng `length` của mảng làm giá trị. Thay đổi hành vi duy nhất: id ≥ 1000
(trước: live bỏ im lặng / sim AIOOBE; nay: chạy đúng tới 4095, ≥ 4096 ERROR+đếm / IllegalStateException).
Bộ nhớ: ring `HistoryManager` 4096×2048 tham chiếu ≈ 33 MB (trước 8 MB) — heap shadow 3 G, live tương tự; sim: mảng phút 16 KB (trước 4 KB),
sim nạp 1 ngày/lần ⇒ ~24 MB/ngày.
**Chỗ sim cần kiểm parity md5:** đường sim đi qua `readDataFromAerospike1M_ShortKey` / `KaggleDataLoader.loadDailyTickersShort` /
`HPOSmartCache.getDataShort(FromFile)` (+ `CompactFileDay`), `HistoryManager` (updateHistoryArray, findPotentialLosersShort, cleanup),
`SimulatorMarketLevelTicker1MStopLoss.symbol2Order*`, `TickWeakBlock` (nếu bật), `PumpDumpFilter` (nếu bật) ⇒ kernel L5 bên dưới.
JUnit: `HistoryManagerIdCapTest` (999/1000/1500/4095 lưu + đọc; 4096/5000 đếm, không ném; ghi đè cùng startTime giữ nguyên),
`CompactFileDayIdCapTest`, `SymbolMapperSnapshotRepairTest`, `SymbolMapperRepairToolTest`. `mvn -o -q test`: trước gộp L2 291 test / 48 lớp
PASS (sau merge L1) → 303 / 52 PASS.

## L5 — Parity sim jar mới vs `gqsf-a1` (md5 printDone `ad26fd55f0bb5db32038ec8b357cf8e7`) — CHỜ LƯỢT
Trạng thái 21:42: orchestrator HO4 (PID 3114301) mới xong 4/32 kernel, chiếm 2 slot tới ~07:45 12-10 ⇒ CHƯA push. Script sẵn:
`~/claude_master/1011/livefix/l5/lf2_parity.py` (`gate` | `jards` | `push` | `check`).
```bash
cd ~/claude_master/1011/livefix/l5
python3 lf2_parity.py gate        # "GATE ho4-* xong=32/32 dang_chay=<2" mới đi tiếp
python3 lf2_parity.py jards       # dataset Kaggle sim-jar-livefix2 (sim.jar = hardlink jar db181d41, + profile của sim-jar-nsel)
python3 lf2_parity.py push        # tự từ chối nếu gate chưa đạt; kernel lf2-c2-s42
python3 lf2_parity.py check       # sau COMPLETE: fetch, kiểm ok/jar/mapper/ov/pred/tk/fund + md5 == ad26fd55 ⇒ l5/lf2_parity_result.json
```
Cấu hình = `ho4p1-c2` (đã cho md5 == gqsf-a1 với jar b7c89f09): K24 + `GATE_QUOTA_SKIP_WHEN_FULL=true`, seed 42, phí gốc, SIM_END 20251231,
bundle `sim-ho26a-bundle`, artefact HO4-P1 (chain/tk/pred/fund). Khác DUY NHẤT: jar dataset + `extra_env SYMBOL_MAPPER_DUP_POLICY=WARN`.
**Vì sao WARN (không dùng mapper đã sửa):** mapper Kaggle = bản sao 863 (8 id trùng) đọc qua `getReadClient` ⇒ jar mới mặc định FAIL-FAST.
Sửa bản sao = đổi artefact dùng chung của mọi sim HO (biến thể mới) — không làm. Với WARN, khác biệt so với jar cũ chỉ là `getSymbol(id trùng)`
trả tên nhỏ nhất (thay vì tên nạp sau). Trong cửa sổ gqsf-a1 (≤ 2025-12-31) 16 symbol chưa niêm yết (kline từ 2026-07-16) ⇒ không ô
`klineArray[843..850]` nào khác null ⇒ `getSymbol` cho id đó chỉ được gọi ở `TickWeakBlock.buildExcluded` (so `diedSymbol` — không chứa
16 symbol nào) ⇒ không đổi kết quả. Cấp id cho symbol lạ: kernel không ghi được mapper (NOWRITE) ⇒ id cục bộ = max+1… như thuật toán cũ.
PASS = md5 trùng. FAIL ⇒ không deploy jar cho đến khi giải thích (diff printDone theo lệnh; nghi vấn đầu: thay đổi trong module sau
b7c89f09, không phải L2).

## Rủi ro còn lại
1. Cửa sổ dừng 2–4′: 46–47 vị thế LEGACY không quản lý; giảm bằng chạy `d4_window_242.sh` một mạch (không chạy tay từng bước).
2. Writer mapper ngoài danh sách (JVM khác trên Oracle/242 với config 242, jar cũ) có thể cấp id trùng SAU repair — d1 liệt kê JVM; sau deploy
   mọi JVM jar mới dùng CAS, jar cũ thì không ⇒ không chạy tool/exporter jar cũ với `AEROSPIKE_HOST=242` không cờ shadow.
3. Rollback mapper (`restore`) tái tạo id trùng; chỉ làm khi có lý do pháp y.
4. Parity sim (L5) chưa chạy: chấp nhận deploy trước L5 là quyết định của MASTER (đường sim đổi chỉ do L2; đường live chỉ đổi ở
   `HistoryManager` — trần + log — còn 3 loader `klineArray` là đường sim/tool).
5. `HistoryManager` là RAM ⇒ sau restart MỌI ring đều rỗng và nạp lại như nhau; 16 symbol với id mới không khác symbol khác. Dữ liệu
   lưu đĩa theo id (nếu có artefact nào khoá bằng id 843–850, vd export cũ trên Oracle) sẽ không còn map — đúng ý (đã trộn 2 symbol).
6. Đĩa Oracle 0,6 G (21:45) — d2 kéo storage live từng ngày; backfill vẫn đang ghi log/backup.
