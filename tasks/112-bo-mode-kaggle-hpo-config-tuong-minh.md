# TASK-112: Bỏ IS_KAGGLE_MODE / IS_HPO_MODE — nguồn dữ liệu tường minh per-box + fail-fast

- **status:** todo
- **Milestone:** hạ tầng backtest/WFO — [docs/insights/WFO_ROADMAP.md](../docs/insights/WFO_ROADMAP.md)
- **Ưu tiên:** cao — 2 flag này đã gây hỏng 2 lần chạy; lần gần nhất làm VÔ HIỆU cả full WFO 17 window (2026-07-02).
- **require_review:** true
- **touches_live_process:** code-only. **CẤM deploy/restart bất cứ gì trên 242** trong task này.

## ⛔ RÀNG BUỘC MÔI TRƯỜNG (đọc TRƯỚC khi làm bất cứ gì)

1. **Trên Oracle (ubuntu@161.118.212.3) đang có run WFO verdict thật:** 2 process `WfoWorker` + jobstore Aerospike taskId `strategy_window` (17 job). `TYPE="strategy_window"` là hardcode (StrategyWfoTask.java:37) — **mọi lệnh `WfoCoordinator reset strategy_window` sẽ ĐÈ jobstore và PHÁ run đang chạy.**
   → CẤM: reset/init jobstore, kill java, đè file `~/java/simulator/binance-futures-wfo-lf.jar` trên Oracle **khi run chưa xong**. Kiểm trước bằng: `pgrep -f WfoWorker` (phải rỗng) VÀ `WfoCoordinator status strategy_window` (DONE=17). Nếu run chưa xong → làm phần code/compile/local trước, phần GATE trên Oracle chờ.
2. Phát triển code trên repo local Windows (`E:\educa\source\github\20260415\BinanceFuturesJava`, branch `module`). Build: `JAVA_HOME=/c/Users/pc/.jdks/corretto-17.0.9 /c/Users/pc/bin/mvn -q -DskipTests package`. Deploy lên Oracle = jar TÊN MỚI `binance-futures-task112.jar` (KHÔNG đè jar đang chạy), md5 verify.
3. KHÔNG `git add .` — add từng file. Trailer commit: `Co-Authored-By: ...` như quy ước. `luna_csv/ scripts/ scripts_tmp/` không bao giờ commit.

## Mục tiêu (1 câu)

Xóa 2 flag runtime `Configs.IS_KAGGLE_MODE` / `Configs.IS_HPO_MODE` (~25 tool tự set tay ở `main()`, trộn 3 quyết định độc lập), thay bằng config **tường minh per-box** trong `config.properties` + **fail-fast tại điểm dùng**, để không bao giờ còn "quên set mode → âm thầm đọc sai nguồn → kết quả rác".

## Bối cảnh (2 sự cố — bằng chứng)

1. **2026-07-02:** `WfoWorker` chạy với `WFO_KAGGLE=1` nhưng thiếu `WFO_SMART_CACHE=1` → sim rơi nhánh `IS_KAGGLE_MODE` đọc ticker từ FILE `kaggle_data_hpo/` (chỉ có 2021-01→2022-06) → **13/17 window ZERO_TRADES âm thầm** (sim log "File data error" rồi CHẠY TIẾP, fitness −100000) → full verdict vô hiệu. Aerospike Oracle-local thực ra CÓ kline đầy đủ 2021→2026 (đã sample 5 mốc xác nhận).
2. Trước đó 1 lần lỗi tương tự do set nhầm/quên mode.

**Bản chất:** 2 flag boolean trộn 3 quyết định độc lập — (a) đọc Aerospike cluster nào, (b) ticker từ nguồn nào, (c) tinh chỉnh log/storage — và không có fail-fast.

## Bảng rà đầy đủ điểm rẽ nhánh (đã đo 2026-07-02 — số dòng có thể xê dịch, dùng grep)

| # | Vị trí | Hành vi hiện tại | Việc phải làm |
|---|---|---|---|
| 1 | `DataManagerAerospikeFloatSim.getReadClient()` (~2445) | mode→`getClient226()`, else→`getClient242()` (LIVE) | đọc `AEROSPIKE_READ_CLUSTER`; thiếu config → throw ngay tại đây (lazy fail-fast) |
| 2 | `SymbolLifecycleManager` (~57) | if riêng y hệt #1 | thay bằng gọi `getReadClient()` (gom 1 chỗ) |
| 3 | `SimulatorMarketLevelTicker1MStopLoss` ~92-99 (đọc ticker) | 3 nhánh: SMART_CACHE→Aerospike-cache; elif KAGGLE→FILE; else→Aerospike | logic MỚI (pseudo-code §Thiết-kế) theo `TICKER_SOURCE` + fail-fast data |
| 4 | Sim ~240 (`IS_HPO_MODE`) | chỉ đổi `isPrintBalance` (log) + System.gc — đã xác nhận signature `BudgetManagerSimple.updateBalance(..., boolean isPrintBalance)`, KHÔNG đổi PnL | hợp nhất về nhánh else hiện tại (log mỗi nửa đêm); xóa if |
| 5 | Sim ~315 (`!IS_KAGGLE_MODE`) | ghi `storage/*.data` + printDone.csv | config `WRITE_SIM_STORAGE` default `false` (⚠️ đổi default cho người chạy local — trước đây local mặc định GHI; ghi vào migration note) |
| 6 | `Configs.assertLiveRuntime()` (~97, guard #12/TASK-030) | fail nếu mode bật trên live | fail nếu `AEROSPIKE_READ_CLUSTER` thiếu HOẶC != `242` (live gọi hàm này lúc startup → thiếu config nổ ngay tại live, đúng ý) |
| 7 | `GoldenBacktest` ~342 | metadata `"226"/"242"` từ flag | đọc từ config mới (cosmetic) |
| 8 | ~25 tool `main()` set tay flag (WfoWorker/Coordinator/ExportWfoDataset, Ablation*, Run*, Export*, SensitivityTool, ExportHpoDataKaggle, ExportTool1*, MetricDistributionTool, WFORunner...) | nguồn lỗi "quên set" | xóa toàn bộ dòng set; env `WFO_KAGGLE`/`SENS_KAGGLE` chết theo (xóa cả đoạn đọc env) |
| 9 | **`Aggregate15m4hBtcEth` (~64): `IS_KAGGLE_MODE = !read242`** | ⚠️ CASE ĐẶC BIỆT — chọn cluster ĐỘNG theo arg runtime, không phải per-box | KHÔNG đi qua `getReadClient()`: tool tự gọi thẳng `getClient226()` / `getClient242()` theo arg `read242` (tool đã biết rõ nó muốn đọc đâu) |
| 10 | `Configs.java:78-79` (2 field; IS_KAGGLE_MODE còn đọc từ properties) | — | xóa 2 field; các box còn dòng `IS_KAGGLE_MODE=...` trong config.properties → dòng chết, ghi migration "xóa dòng cũ" |
| 11 | Kaggle-thật: `RunWorkerKaggle`, `RunHpoPhase1_MarketThresholds`, `BenchmarkSpeedTest` đọc file core+ticker | lý do tồn tại gốc của mode (Kaggle không có Aerospike) | GIỮ đường file; chạy bằng `TICKER_SOURCE=file` trong config của Kaggle dataset |

## Thiết kế chốt (Uni duyệt 2026-07-02; các điểm lazy/GATE do Claude bổ sung sau khi đo code)

### 1. Hai config mới trong `config.properties` — KHÔNG set trong code, KHÔNG default ngầm
- `AEROSPIKE_READ_CLUSTER=226|242`
- `TICKER_SOURCE=aerospike|file`
- **Fail-fast LAZY tại điểm dùng** (KHÔNG check trong static-init của Configs): `getReadClient()` throw `IllegalStateException` message rõ ("Thieu AEROSPIKE_READ_CLUSTER trong config.properties — them dong: AEROSPIKE_READ_CLUSTER=226 (box backtest) hoac =242 (live)") nếu thiếu/giá trị lạ; tương tự `TICKER_SOURCE` check tại điểm sim đọc ticker. *Lý do lazy: box Kaggle chạy thuần file không có/không cần `AEROSPIKE_READ_CLUSTER`; tool không chạy sim không cần `TICKER_SOURCE`. Static-init fail sẽ bắt mọi box khai đủ cả 2 dù không dùng → sai tinh thần.* Riêng live: `assertLiveRuntime()` (gọi lúc startup của `BinanceDataIngestor`/`BinanceOrderTradingManager`) chủ động đọc `AEROSPIKE_READ_CLUSTER` → thiếu là nổ ngay tại live (#6).

### 2. Nhánh đọc ticker mới trong sim (thay ~92-99)
```java
switch (TICKER_SOURCE) {                      // đọc 1 lần, validate giá trị
  case "aerospike":
    time2Tickers = Configs.USE_SMART_CACHE
        ? HPOSmartCache.getDataShort(startTime)              // cache RAM (WFO/HPO)
        : DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(startTime);
    break;
  case "file":
    if (Configs.USE_SMART_CACHE) throw new IllegalStateException("USE_SMART_CACHE chi hop le voi TICKER_SOURCE=aerospike");
    time2Tickers = KaggleDataLoader.loadDailyTickersShort(startTime);
    break;
}
if (time2Tickers == null || time2Tickers.isEmpty())
    throw new RuntimeException("FAIL-FAST: khong co ticker ngay " + yyyymmdd + " tu nguon " + TICKER_SOURCE
        + " — dung ngay, KHONG chay tiep (tranh ZERO_TRADES am tham).");
```
- **GIỮ NGUYÊN** semantics `time2Tickers.size() >= 1440` phía dưới (ngày thiếu phút bị skip lặng — hành vi cũ, đổi nó sẽ phá GATE; chỉ thêm `LOG.warn` khi skip). Đã xác nhận vòng lặp dừng bằng `startTime > endTime` (dòng ~282), KHÔNG dựa vào null → fail-fast không phá vòng đời loop.
- Check mâu thuẫn `USE_SMART_CACHE + file` như trong pseudo-code.

### 3. Mapping env cũ → mới (ghi vào docs khi xong)
| Cũ | Mới |
|---|---|
| `WFO_KAGGLE=1` (env, set IS_KAGGLE_MODE) | bỏ — cluster theo `AEROSPIKE_READ_CLUSTER` trong config box |
| `SENS_KAGGLE=1` | bỏ — như trên |
| `WFO_SMART_CACHE=1` | GIỮ NGUYÊN (tối ưu, chỉ hợp lệ với source=aerospike) |
| set tay `IS_HPO_MODE/IS_KAGGLE_MODE` trong ~25 main() | xóa hết |

### 4. Giá trị per-box sau refactor (checklist migration — Code áp Oracle; các box khác ghi checklist để Uni áp)
- **Oracle:** `AEROSPIKE_READ_CLUSTER=226` (HOST_226=127.0.0.1 local) + `TICKER_SOURCE=aerospike`
- **226:** `AEROSPIKE_READ_CLUSTER=226` + `TICKER_SOURCE=aerospike`
- **242 (live):** `AEROSPIKE_READ_CLUSTER=242` + `TICKER_SOURCE=aerospike` — **Uni tự áp khi deploy live, KHÔNG làm trong task**
- **Kaggle dataset:** `TICKER_SOURCE=file` (không cần `AEROSPIKE_READ_CLUSTER`; nếu code lỡ đụng getReadClient → fail-fast là hành vi đúng)
- Mọi box: xóa dòng `IS_KAGGLE_MODE=...` cũ nếu có.
- Bump `CONFIG_VERSION`.

## GATE hành vi (quan trọng nhất — chỉ đổi wiring, KHÔNG đổi logic)

**Baseline ĐÃ CÓ SẴN** (đo 2026-07-02 15:12, function-test v2): jar `binance-futures-wfo-lf.jar` (git 2cfc3c6 + aerospike-client 6.1.11), dataset `/home/ubuntu/claudedata/wfo_dataset_wf` (manifest `md5_funding=d714390a7b228a59f53c621911ed94e8`), reset `WFO_MAX_WINDOWS=4 WFO_N_SAMPLES=3`, worker env `WFO_KAGGLE=1 WFO_SMART_CACHE=1 WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset_wf`, seed job = 42+i (deterministic, lưu trong job params):

```
[WIN 0] 20220101..20220401 IS=3.2387 OOS=2.4795 WFE=0.0233 pnl=325.0484
[WIN 1] 20220401..20220701 IS=3.0796 OOS=0.0463 WFE=0.0256 pnl=255.5134
[WIN 2] 20220701..20221001 IS=1.5476 OOS=0.5708 WFE=0.0139 pnl=54.5737
[WIN 3] 20221001..20230101 IS=1.9266 OOS=3.1547 WFE=0.1059 pnl=251.5719
```

Quy trình (SAU khi run verdict trên Oracle xong — xem Ràng buộc #1):
1. **Xác nhận determinism trước:** chạy lại baseline y hệt bằng jar CŨ → 4 dòng [WIN] phải khớp số trên. Nếu lệch → **DỪNG, báo Uni** (GATE khớp-số không khả thi, cần Uni chốt cách so khác), KHÔNG tự nới tiêu chí.
2. Sau refactor: thêm `TICKER_SOURCE=aerospike` + `AEROSPIKE_READ_CLUSTER=226` vào `~/java/simulator/config.properties` Oracle, deploy `binance-futures-task112.jar`, chạy cùng reset/worker nhưng env chỉ còn `WFO_SMART_CACHE=1 WFO_DATA_DIR=...` → 4 dòng [WIN] **khớp 100%** baseline.
3. ⚠️ GATE phải cùng nguồn **aerospike** — đã đo: nguồn file vs aerospike cho số KHÁC nhau (WIN0 pnl 340.80 file vs 325.05 aerospike, cùng seed/N) vì 2 nguồn không tương đương dữ liệu. KHÔNG so chéo nguồn.

## Scope

**Trong scope:** toàn bộ bảng rà #1-#11; xóa 2 field Configs; migration checklist; cập nhật docs nhắc mode (`docs/db/aerospike-226.md`, `docs/rules/run-226.md`, `docs/insights/WFO_ROADMAP.md` §4 env worker); bump CONFIG_VERSION.
**Ngoài scope (KHÔNG động):** logic sim/PnL/entry/exit (kể cả semantics size>=1440); format dataset WFO; model/train; deploy/restart 242; jobstore `strategy_window` đang chạy.

## Acceptance criteria (Code tự kiểm trước khi báo done)

- [ ] `grep -rn "IS_KAGGLE_MODE\|IS_HPO_MODE" src/` = 0 (trừ comment lịch sử nếu cố ý giữ).
- [ ] `getReadClient()` khi thiếu `AEROSPIKE_READ_CLUSTER` → IllegalStateException message hướng dẫn (test thực tế: chạy 1 tool đọc Aerospike với config thiếu key).
- [ ] Sim: ticker null/empty 1 ngày → RuntimeException DỪNG (test: `TICKER_SOURCE=file` + range có ngày không có file, ví dụ 2023-01-01 trên Oracle).
- [ ] `USE_SMART_CACHE=true` + `TICKER_SOURCE=file` → fail-fast mâu thuẫn.
- [ ] `assertLiveRuntime()`: config thiếu hoặc !=242 → exit(1) (unit-style test hoặc chạy thử main ingestor local với config sai — KHÔNG trên 242).
- [ ] `Aggregate15m4hBtcEth` vẫn chọn đúng cluster theo arg (đọc code review — gọi thẳng getClient226/242).
- [ ] **GATE:** bước 1 determinism PASS, bước 2 sau-refactor 4 dòng [WIN] khớp 100% baseline. Ghi số thực tế vào phần Kết quả.
- [ ] Compile + build shaded jar sạch. SLF4J, không System.out. Commit lẻ theo cụm (Configs/constants → wiring #1-#7 → tools #8-#9 → docs+migration), mỗi commit message tiếng Việt không dấu theo style repo.
- [ ] Oracle config.properties đã thêm 2 key (sau khi run verdict xong); checklist migration các box khác ghi trong phần Kết quả.

---

## (Code điền) Kết quả

<tóm tắt, commit list, số GATE determinism + trước/sau>

## (Code điền) Phát hiện ngoài scope

<thấy vấn đề nhưng KHÔNG tự sửa>

## (Code điền) Quyết định phát sinh

<ADR mới nếu có>
