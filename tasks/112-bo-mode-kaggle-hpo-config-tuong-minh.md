# TASK-112: Bỏ IS_KAGGLE_MODE / IS_HPO_MODE — nguồn dữ liệu tường minh per-box + fail-fast

- **status:** todo
- **Milestone:** hạ tầng backtest/WFO — [docs/insights/WFO_ROADMAP.md](../docs/insights/WFO_ROADMAP.md)
- **Ưu tiên:** cao — lỗi do 2 flag này đã gây hỏng 2 lần chạy (Uni xác nhận), lần gần nhất làm VÔ HIỆU cả full WFO 17 window (2026-07-02).
- **require_review:** true (đụng routing Aerospike dùng chung với live 242 — KHÔNG deploy 242 trong task này)
- **touches_live_process:** code-only (build chung jar, nhưng cấm deploy/restart 242)

## Mục tiêu (1 câu)

Xóa 2 flag runtime `Configs.IS_KAGGLE_MODE` / `Configs.IS_HPO_MODE` (hiện ~25 tool tự set tay ở `main()`, trộn 3 quyết định độc lập), thay bằng config **tường minh per-box** trong `config.properties` + **fail-fast khi thiếu data/config**, để không bao giờ còn "quên set mode → âm thầm đọc sai nguồn → kết quả rác".

## Bối cảnh — vì sao (2 sự cố đã đo)

1. **2026-07-02 (sự cố mới nhất):** chạy `WfoWorker` với `WFO_KAGGLE=1` nhưng THIẾU `WFO_SMART_CACHE=1` → sim rơi vào nhánh `IS_KAGGLE_MODE` đọc ticker từ FILE `kaggle_data_hpo/` (chỉ có 2021-01→2022-06) → **13/17 window ZERO_TRADES âm thầm** (sim log "File data error" rồi CHẠY TIẾP, fitness −100000) → full verdict WFO vô hiệu. Đã xác nhận: Aerospike Oracle-local CÓ kline đầy đủ 2021→2026 (sample 5 mốc đều có data) — chạy lại với `WFO_SMART_CACHE=1` thì 4/4 window function-test có lệnh bình thường.
2. Trước đó đã 1 lần lỗi tương tự do set nhầm/quên mode (Uni xác nhận "đã gặp lỗi đó 2 lần").

**Bản chất:** 2 flag boolean trộn 3 quyết định độc lập — (a) đọc Aerospike cluster nào, (b) ticker lấy từ nguồn nào, (c) tinh chỉnh log/storage — và không có fail-fast.

## Bảng rà đầy đủ các điểm rẽ nhánh (đã đo 2026-07-02)

| # | Vị trí | Hành vi hiện tại | Việc phải làm |
|---|---|---|---|
| 1 | `DataManagerAerospikeFloatSim.getReadClient()` (~dòng 2445) | mode→`getClient226()`, else→`getClient242()` (LIVE) | đọc theo `AEROSPIKE_READ_CLUSTER` |
| 2 | `SymbolLifecycleManager` (~dòng 57) | y hệt #1 | y hệt #1 (gom về 1 chỗ: gọi `getReadClient()` thay vì tự if) |
| 3 | `SimulatorMarketLevelTicker1MStopLoss` ~dòng 92-99 | `USE_SMART_CACHE`→cache-Aerospike; elif `IS_KAGGLE_MODE`→FILE `KaggleDataLoader`; else→Aerospike trực tiếp | rẽ theo `TICKER_SOURCE` (file/aerospike); SMART_CACHE chỉ là tối ưu trên nguồn aerospike. **FAIL-FAST** (xem dưới) |
| 4 | Sim ~dòng 240 (`IS_HPO_MODE`) | chỉ đổi `isPrintBalance` (log) + System.gc — đã xác nhận param, KHÔNG đổi PnL | hợp nhất về 1 nhánh (log mỗi nửa đêm như nhánh else hiện tại); xóa if |
| 5 | Sim ~dòng 315 (`!IS_KAGGLE_MODE`) | ghi `storage/*.data` + `printDone.csv` | config mới `WRITE_SIM_STORAGE` (default `false`) |
| 6 | `Configs.assertLiveRuntime()` (~dòng 97, guard #12/TASK-030) | fail nếu mode bật trên live | đổi thành: fail nếu `AEROSPIKE_READ_CLUSTER != 242` trên live (giữ nguyên tinh thần guard) |
| 7 | `GoldenBacktest` ~dòng 342 | metadata `"226"/"242"` | đọc từ config mới (cosmetic) |
| 8 | ~25 tool `main()` set tay 2 flag (WfoWorker/Coordinator, ExportWfoDataset, Ablation*, Run*, Export*, SensitivityTool, ExportHpoDataKaggle, ExportTool1*, ...) | nguồn lỗi "quên set" | **xóa toàn bộ** các dòng set flag |
| 9 | `Configs.java:78-79` | 2 field + IS_KAGGLE_MODE còn đọc được từ properties | xóa 2 field |
| 10 | Kaggle-thật: `RunWorkerKaggle`, `RunHpoPhase1_MarketThresholds`, `BenchmarkSpeedTest` đọc file core+ticker | lý do tồn tại gốc của mode (Kaggle không có Aerospike) | giữ đường file, chạy bằng `TICKER_SOURCE=file` trong config của Kaggle dataset |

## Thiết kế chốt (Uni đã duyệt 2026-07-02)

1. **2 config mới trong `config.properties`, KHÔNG set trong code, KHÔNG có default ngầm:**
   - `AEROSPIKE_READ_CLUSTER=226|242` — thiếu → **fail-fast lúc khởi động** với message chỉ rõ phải thêm dòng nào. (Không default: default 242 nguy hiểm cho box backtest — backtest âm thầm đọc live; default 226 nguy hiểm cho live. Tường minh 100%.)
   - `TICKER_SOURCE=aerospike|file` — thiếu → fail-fast tương tự.
2. **Fail-fast dữ liệu trong sim:** `TICKER_SOURCE=file` mà thiếu file ngày trong range, hoặc `aerospike` mà đọc về null/rỗng cho 1 ngày trong range → **throw RuntimeException DỪNG NGAY** (kèm ngày + nguồn). Cấm log-rồi-chạy-tiếp (chính nó tạo ZERO_TRADES âm thầm).
3. Giá trị per-box sau refactor (ghi vào docs/db + checklist migration):
   - Oracle: `AEROSPIKE_READ_CLUSTER=226` (=127.0.0.1 local) + `TICKER_SOURCE=aerospike`
   - 226: `AEROSPIKE_READ_CLUSTER=226` + `TICKER_SOURCE=aerospike`
   - 242 (live): `AEROSPIKE_READ_CLUSTER=242` + `TICKER_SOURCE=aerospike` (guard #6 enforce)
   - Kaggle dataset: `AEROSPIKE_READ_CLUSTER` không dùng tới khi mọi nguồn là file; `TICKER_SOURCE=file` (worker Kaggle không được gọi Aerospike — nếu code đụng tới getReadClient khi cluster config thiếu thì fail-fast là đúng hành vi mong muốn)
4. `USE_SMART_CACHE` giữ nguyên (tối ưu hóa, chỉ hợp lệ khi `TICKER_SOURCE=aerospike`; nếu bật cùng `file` → fail-fast config mâu thuẫn).
5. `WRITE_SIM_STORAGE` (default false) thay cho `!IS_KAGGLE_MODE` ở #5.

## Scope

**Trong scope:** toàn bộ bảng rà #1-#10; xóa 2 field khỏi Configs; sửa ~25 tool main(); migration note + cập nhật `docs/db/aerospike-226.md`/`aerospike-242.md` + `docs/rules/run-226.md` nếu nhắc mode; bump `CONFIG_VERSION`.

**Ngoài scope (KHÔNG động):** logic sim/PnL/entry/exit; format dataset WFO; model/train; **KHÔNG deploy/restart 242** (chỉ code + build + test trên Oracle/local; deploy live là quyết định riêng của Uni sau golden).

## Acceptance criteria (Code phải tự kiểm trước khi báo done)

- [ ] `grep -r "IS_KAGGLE_MODE\|IS_HPO_MODE" src/` = 0 kết quả (ngoài comment lịch sử nếu giữ).
- [ ] Thiếu `AEROSPIKE_READ_CLUSTER`/`TICKER_SOURCE` trong config → process DỪNG ngay khởi động với message rõ (test thực tế).
- [ ] Sim: thiếu ticker 1 ngày trong range (cả 2 nguồn) → RuntimeException dừng, KHÔNG chạy tiếp (test thực tế 1 ngày cố tình thiếu).
- [ ] `WFO_SMART_CACHE=1` + `TICKER_SOURCE=file` → fail-fast config mâu thuẫn.
- [ ] **GATE hành vi (quan trọng nhất):** trên Oracle, 1 backtest chuẩn (cùng range/params/dataset, ví dụ function-test 4 window N=3 seed cố định) chạy TRƯỚC và SAU refactor phải **khớp PnL + số trades từng window** (chỉ đổi wiring, không đổi logic). Ghi số vào phần Kết quả.
- [ ] `assertLiveRuntime()` mới: giả lập config sai trên live-entry (`BinanceDataIngestor`) → exit(1).
- [ ] Compile + build shaded jar sạch. SLF4J log, không System.out. Commit lẻ theo cụm (constants → wiring → tools → docs), KHÔNG `git add .`.
- [ ] Cập nhật config.properties trên Oracle (226+aerospike) như checklist §3 — các box khác ghi checklist để Uni tự áp.

---

## (Code điền) Kết quả

<tóm tắt đã làm gì, commit nào, số GATE trước-sau>

## (Code điền) Phát hiện ngoài scope

<thấy vấn đề nhưng KHÔNG tự sửa>

## (Code điền) Quyết định phát sinh

<ADR mới nếu có>
