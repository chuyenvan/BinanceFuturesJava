# DEPLOY_242 — ĐỢT 2 (gộp 027 + 028 + 029 + 030 + 031) [TASK-033]

> ⛔ **CCD KHÔNG tự deploy/restart 2 process live.** Runbook để **user duyệt + tự bấm**.
> Cơ chế backup/copy/restart/rollback **Y HỆT đợt 1** — xem `docs/DEPLOY_242.md §3–5,7`. Đây chỉ ghi PHẦN KHÁC của đợt 2.
> ⚠️ Đợt 1 (016 + 019 + gỡ-crawl) **ĐÃ deploy live** — KHÔNG gồm lại, KHÔNG rollback về trước đợt 1.

## 0. Trong jar đợt 2 (build từ working tree branch `module`)
| Task | Commit | Đụng process | Tóm tắt |
|---|---|---|---|
| 027 entry | **working tree** (chưa commit — CCD-audit) | Trading | #6 gỡ V4 dead (giữ V3), #7 size theo price_realtime+tuổi 30s, #8 aiBrain null→alert+fail-fast, NPE BTC |
| 028 ingest | `1697198` | Ingest | #1 funding qua BinanceRestGuard, #2 watchdog bật lại+counter, #3 HttpRequest classifyError |
| 029 concurrency | `409ab7e` | Ingest + Trading | striped-lock writeMinuteBatch, ForkJoinPool chung, swap-map+removeLock try/finally |
| 030 parity/config | `b2728db` | Trading (+sim) | sim reject pred==null (**CONFIG_VERSION v8→v9**), `assertLiveRuntime()` đầu 2 live main |
| 031 forward kline | `dd883f9` | Ingest | `Kline15m4hForwardRoller` wire BinanceDataIngestor (forward 15m/4h@242) |

⇒ **Restart CẢ HAI process** (`BinanceDataIngestor` + `BinanceOrderTradingManager`).
⚠️ **027 chưa commit** (OnnxInferenceManager/DetectEntry ở working tree). Build từ working tree GỒM 027; nếu build từ commit sạch → THIẾU 027. CCD-audit nên commit 027 trước build chính thức.

### Build (ĐÃ làm, verified — TASK-033)
- `mvn -o package` PASS (jar 94.2MB). Jar chứa đủ class: OnnxInferenceManager, DetectEntrySignal2TradeNormal (027), BinanceOrderTradingManager, TickerIngestor2AerospikeNew (029), SimulatorMarketLevelTicker1MStopLoss, Configs, RunHpoMaster_Distributed (030 v9), Kline15m4hForwardRoller (031).
- Soát Configs chung: có `assertLiveRuntime()` (030) + `PRICE_REALTIME_MAX_AGE_MS` (027). RunHpoMaster `CONFIG_VERSION="v9"`.

## 1. ⚠️ TIỀN ĐỀ BẮT BUỘC trước khi restart (đặc thù đợt 2)

### 1a. LẤP GAP 15m/4h@242 (chạy TRÊN 226 — job DATA, KHÔNG phải deploy)
`kline_15m/4h@242` dừng 06-07; gap >7 ngày > catch-up của roller 031 (200 khung 15m ≈ 50h). Phải lấp TRƯỚC khi bật 031, nếu không 15m sẽ thủng đoạn 06-07→nay.

**⚠️ KIỂM TRA AN TOÀN TRƯỚC KHI CHẠY** (tránh ghi đè mất dữ liệu lịch sử 15m/4h@242):
- `Aggregate15m4hBtcEth 242` đọc **1m@242** rồi GHI ĐÈ month-record 15m/4h ở CẢ 226+242. Tháng 242 KHÔNG có 1m → không đụng; tháng 242 có 1m ĐẦY ĐỦ → ghi đè bằng series đầy đủ (an toàn/đúng); **THÁNG BIÊN (242 có 1m một phần)** → ghi đè bằng series một-phần ⇒ **MẤT phần cũ tháng đó**.
- ⇒ **Verify độ sâu `kline_1m_opt@242` trước:** chạy `Aerospike242Inventory` (TASK-032) hoặc `AerospikeStateScan` TRÊN 226 → xem ts-min của 1m@242.
  - Nếu 1m@242 **liên tục 2021→nay** → full-rebuild an toàn (mọi tháng đầy đủ). Chạy lệnh dưới.
  - Nếu 1m@242 **chỉ gần đây** (vd từ 2024/2025) → full-rebuild sẽ ghi đè đúng các tháng có 1m (đầy đủ) + KHÔNG đụng tháng cũ (242 thiếu 1m → 226 historical giữ nguyên). Chỉ rủi ro 1 THÁNG BIÊN. Chấp nhận được cho gap gần đây; nếu cần tuyệt đối an toàn → backup set 15m/4h@242 (TASK-034 ReplicateSet242To226) trước.

```bash
# TRÊN 226 (226 thông 242). Ghi PID/log theo luật dọn-job 226.
cd <run_dir_226>   # CWD có config.properties (TASK-112: arg "242" tự ép đọc 242, không phụ thuộc AEROSPIKE_READ_CLUSTER)
mkdir -p outputs/.run
nohup java -cp <run_dir_226>/binance-java-sdk-1.2.4.jar \
  com.binance.chuyennd.ai_ml.features.export.Aggregate15m4hBtcEth 242 \
  > outputs/.run/Aggregate242.log 2>&1 & echo $! > outputs/.run/Aggregate242.pid
# theo dõi: log "đọc 1m từ 242 LIVE" + "{n} record-tháng → 226+242" + dòng VALIDATE "KHỚP ✅"
```
- [ ] Log validate khớp; `kline_15m/4h@242` có tháng 202606 (và sau) **TIẾN tới gần nay**.
- [ ] (khuyến nghị) backup 15m/4h@242 trước nếu chọn full-rebuild có tháng biên.

### 1b. ⚠️ CONFIG_VERSION v8→v9 (030) — BÁO USER nếu có HPO đang chạy
`RunHpoMaster_Distributed.CONFIG_VERSION="v9"` → cache `hpo_results_v8` thành **vô nghĩa** (điểm cũ tính bằng luật sim cũ: sim cũ vào lệnh khi pred==null). Nếu đang có HPO chạy dở → confirm với user; run mới dùng set `hpo_queue_v9`/`hpo_results_v9`. (v9 KHÔNG ảnh hưởng 2 process live — chỉ HPO/backtest.)

### 1c. Baseline trước restart
- [ ] Chạy `AerospikeStateScan`/`Aerospike242Inventory` TRÊN 226 → ghi mốc TRƯỚC của `kline_15m/4h`, `funding_data`, `open_interest`, `price_realtime`@242 (so sau restart biết deploy có tác dụng).

## 2. Backup + copy + restart → theo `DEPLOY_242.md §3–5` (KHÔNG đổi)
- Backup jar đang chạy → `.bak.<ts>`; copy jar mới + md5 2 đầu khớp; restart **ingest trước, trading sau** theo **pid-file** (⛔ KHÔNG `pkill/killall java` — tránh Aerospike/Redis/HPO).

## 3. VERIFY sau restart (đọc log 242 ~10–15') — theo TỪNG fix
**Chung / còn-đúng từ đợt 1:** `-1130` vẫn hết; `FundingFee-Refresh` log "cập nhật N symbol" mỗi 30' (N>0); `price_realtime`/`open_interest`/`kline_1m`/`funding_data`@242 vẫn ghi; Reporter/Telegram sống; không exception lặp trong `error.log`.

- [ ] **030 #12 (fail-fast):** 2 process LÊN ĐƯỢC (không exit ngay) → xác nhận `AEROSPIKE_READ_CLUSTER=242` trong config.properties@242 (TASK-112). Nếu thấy log `⛔ FATAL (audit #12 / TASK-112) ... DỪNG` → config thiếu/sai key này → thêm `AEROSPIKE_READ_CLUSTER=242` rồi restart lại.
- [ ] **031 (forward kline):** sau lấp-gap, `kline_15m@242` ts TIẾN qua mỗi biên 15m (log `Kline15m4hForwardRoller` ~60s; record-tháng 202606 cập nhật). `kline_4h` tiến mỗi 4h (catch-up 200×4h tự lấp).
- [ ] **028 #1 (funding guard):** funding-poll qua `BinanceRestGuard` (đang ban → bỏ qua, không spam); **#2 watchdog:** thread `ThreadAutoRestartProgram` sống, counterMinutes tiến (không còn DEAD); **#3 HttpRequest:** lỗi REST log WARN có phân loại (TIMEOUT/DNS/SSL) thay vì câm.
- [ ] **029 (concurrency):** ingest — `Rest-Kline-Loop` chốt phút đủ ~554 symbol (không mất nến do race #4); không bùng luồng (ForkJoinPool chung #5). Trading — log `Update all position:{n} {ms}ms` đều, không kẹt lock 3s (#9); position/trailing không "mất sạch tạm thời".
- [ ] **027 #6/#7/#8:** entry log size dùng `price_realtime` (tuổi ≤30s, quá → fallback nến đóng + cảnh báo); V4 dead đã gỡ (predReturn15M chạy V3 nhất quán); aiBrain init OK (nếu null → có Telegram alert + fail-fast, soi log init).

## 4. Rollback → `DEPLOY_242.md §7` (restore `.bak` + restart). Ghi lý do.

## 5. Sau deploy thành công
- [ ] AGENTS: 027/028/029/030/031 → ✅ DONE + deployed; 033 → DONE.
- [ ] Điền số 242 sau-deploy vào `STATUS_RECON.md §5` / `aerospike_242_inventory.md`.
- [ ] (CCD-audit) commit 027 nếu build chính thức cần commit sạch.

---
### An toàn (CLAUDE.md)
- ⛔ Deploy jar + restart 2 process live = **CHỈ user tay**. Lấp-gap data@242 (qua 226) = CCD làm được (job data).
- ⛔ KHÔNG `pkill/killall java`. Chỉ kill đúng PID pid-file.
- `config/PrivateConfig.java` chứa key live (SECURITY) — KHÔNG echo secret khi thao tác/log.
