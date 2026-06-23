# STATUS_RECON — Dump trạng thái THỰC để Desktop reconcile (TASK-021)

> Sinh bởi CCD-recon, **2026-06-14** (GMT+7). Đọc-only: git + filesystem + test TCP Aerospike. KHÔNG sửa code/commit/deploy/backfill.
> Mỗi mục: `[XONG / DỞ / CHƯA]` + bằng chứng cụ thể. Chỗ nào không đo được từ session này → ghi rõ lý do, **KHÔNG đoán**.

## ⚠️ Giới hạn session (đọc trước khi tin các con số Aerospike)
- Chạy trên **máy dev Windows**, KHÔNG phải 226/242.
- **Test TCP `:3222`:** `242` (LIVE) = **UNREACHABLE** (firewall, khớp ghi chú TASK-019); `226` (BACKTEST) = **REACHABLE**.
- **KHÔNG có CLI Aerospike** (`aql`/`asql`/`asadm` đều NOT FOUND) ⇒ không query set trực tiếp được. Lấy #record/range-ts đòi chạy Java scan = job nặng cần điều phối 226 — task này "nhẹ, đọc-only" nên **KHÔNG chạy**. Mọi con số "set Aerospike có data chưa" bên dưới = **CHƯA ĐO từ session này** (cần chạy trên 226/242), không phải "không có data".
- Log live thật ở **242** (không với tới). `logs/full.log` local (mtime 2026-06-13 21:52) là log **dev**, KHÔNG phản ánh process 242 ⇒ không dùng để kết luận live.

---

## 1. Git
- **Branch:** `module`. (PR thường nhắm `master`.)
- **`git log --oneline` (đỉnh):**
  ```
  f589309 checkpoint: symbol lifecycle (TASK-010) + backfill ext + docs/ADR/tasks (P2 planning)
  eba7934 docs(convention): cam nuot exception cam (CLAUDE.md) + fix repair catch log kem symbol
  3704b6e fix(ingest): TASK-016 clamp limit [1,1500] ...
  72c127a feat(gate): TASK-012 export gate label retMktMedian(t,H) ...
  106baee feat(live): fix REST-ban guard + Reporter(BTC,P2P) + OI ingest + gom log (TASK-007)
  3edb5b1 feat(feature): TASK-009 aggregate 15m+4h BTC/ETH ...
  ```
- **Commit SAU `3704b6e` (016):** chỉ **2** commit — `eba7934` (docs convention + fix repair catch log) và `f589309` (checkpoint TASK-010 + backfill ext + P2 planning). Không có commit 013/015 nào.
- **`git status -s` (uncommitted):**
  ```
   M docs/AGENTS.md
   M src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java
   M src/main/java/com/binance/chuyennd/websocket/FundingIngestor2AerospikeNew.java
   M tasks/019-fix-funding-live-refresh-flush.md
  ?? tasks/020-audit-production-2-process.md
  ?? tasks/021-status-recon-dump.md
  ```
  ⇒ **2 file CODE đang sửa CHƯA commit, đều thuộc TASK-019** (chi tiết §2). Không có file 013/015 uncommitted (đúng với "chưa làm").

---

## 2. Theo từng task

### TASK-019 funding live — **[DỞ — code xong nhưng PHẦN WIRING + B CHƯA COMMIT]**
Đây là phát hiện reconcile quan trọng nhất. 019 bị **tách đôi**: phần lõi A đã committed, nhưng phần kích hoạt + B còn nằm trong working tree.

- **A — `FundingFeeManager` (lõi refresh):** ✅ **ĐÃ COMMIT** trong `f589309`. Có đủ:
  - `setProductionMode(boolean)` → gọi `startProductionRefresh()` (idempotent, `synchronized`, cờ `refreshStarted`).
  - `startProductionRefresh()` khởi `ScheduledExecutorService` daemon tên `FundingFee-Refresh`, chạy `refreshCache()` **mỗi `REFRESH_INTERVAL_MIN = 30` phút**.
  - `refreshCache()` atomic-swap per symbol, bỏ qua symbol đọc rỗng.
- **WIRING — `DetectEntrySignal2TradeNormal.initData()` gọi `setProductionMode(true)`:** ❌ **CHƯA COMMIT** (nằm trong `git diff` working tree). ⇒ **Trong HEAD, `setProductionMode` KHÔNG nơi nào gọi → nhánh refresh vẫn DEAD.** Refresh chỉ sống nếu commit diff hiện tại.
- **B — `FundingIngestor2AerospikeNew` heartbeat idle:** ❌ **CHƯA COMMIT** (working tree). Thêm `idleCycles` + log `💤 ... idle N phút` mỗi ~10 phút; GIỮ nhịp 60s + `writeFundingMap`. Kết luận trong task: **log-thưa-by-design**, không phải ghi-chậm (buffer rỗng→continue→im).
- **Verify ts `funding_data` thật:** ❌ chưa làm — cần đọc set trên 242 (không với tới từ dev).
- **Câu hỏi "log live còn `OI-History-Crawl` không / jar 242 build lúc nào":** ❌ không trả lời được từ session (242 unreachable; log local là dev). **NHƯNG xem TASK-007 §3 dưới** — phần "gỡ-crawl" thực ra CHƯA tồn tại trong code, nên kể cả jar mới nhất vẫn còn crawl.
- **Header task 019:** acceptance A/B đánh `[x]`, "(Code điền)" mô tả DONE — **nhưng git nói 2/3 thay đổi chưa commit**. AGENTS bảng vẫn để `019 = 🟡 TODO ƯU TIÊN`. ⇒ Desktop cần quyết: **commit nốt 2 file working-tree** rồi mới coi 019 code-done.

### TASK-013 OI/LS/taker history — **[BƯỚC 1 XONG (gate) · BƯỚC 2 backfill CHƯA]**
- **BƯỚC 1 VERIFY:** ✅ done (header `[x]`). Tool Python **ngoài repo**: `C:\Users\pc\oi-verify\verify_oi_metrics.py` → `coverage.csv` (896 symbol) + `verify.log`. KHÔNG nằm trong git/`outputs/`.
  - Chốt: granularity 5m UTC; nền metrics thực bắt đầu **~2021-12-01** (chỉ BTC có 2020-09); file CŨ nhân-đôi → bắt buộc dedup; đơn vị `sum_open_interest_value` == API `sumOpenInterestValue` **diff 0.000%** (khớp forward 007-C).
- **BƯỚC 1.5 schema chung:** đề xuất xong (`open_interest` + 4 set LS/taker), **chờ user chốt**.
- **BƯỚC 2 BACKFILL:** ❌ **CHƯA** (header `[ ]`, "(Code điền) B2 = CHƯA làm"). **Không có class backfill OI-history trong repo** — chỉ có `OpenInterestIngestor2AerospikeNew.java` (đó là forward-poll 007-C, không phải backfill vision).
- **Set OI/LS/taker trên 226/242 có data chưa:** ❌ **CHƯA ĐO** (không CLI; 242 unreachable). Forward 007-C có thể đã ghi `open_interest` ít nhiều — cần scan 226/242 để xác nhận.

### TASK-015 feature gate NHÓM A — **[CHƯA BẮT ĐẦU]**
- Header: mọi acceptance `[ ]`, mục "(Code điền)" **rỗng**.
- **Không có class export feature-A trong repo:** `find` chỉ ra `ExportGateReturn.java` — đó là **TASK-012** (label gate_return), KHÔNG phải feature nhóm A.
- **`outputs/`:** có `gate_return.csv` (13MB, mtime 2026-06-13 21:50 = output 012), KHÔNG có file feature nhóm A nào.
- ⇒ 015 = chưa có code, chưa có output, chưa validate.

### TASK-010 lifecycle 3-trạng-thái — **[CODE DONE & COMMITTED · builder CHƯA chạy · set CHƯA có data]**
- **Code:** ✅ cả 2 class committed trong `f589309`:
  - `src/main/java/com/binance/chuyennd/ai_ml/validation/data/SymbolLifecycleBuilder.java`
  - `src/main/java/com/binance/chuyennd/ai_ml/data/SymbolLifecycleManager.java`
- **Builder chạy trên 226 chưa:** ❌ **CHƯA** — `outputs/.run/` **không tồn tại** trên máy dev (đúng vì `.run` ở 226). Không có PID/log builder ở đây. Header task ghi rõ "Builder chưa chạy". Phải chạy trên 226.
- **Set `symbol_lifecycle` (226+242) có data:** ❌ **CHƯA ĐO** (không CLI; 242 unreachable). #LIVE/#DATA_INCOMPLETE/#DEAD = chưa có (builder chưa chạy ⇒ nhiều khả năng set rỗng/chưa tạo).
- **Validate recompute:** ❌ chưa (phụ thuộc builder).
- AGENTS để `010 = 🟣 REVIEW` — khớp: code xong, chờ chạy builder + validate.

---

## 3. Khác

### TASK-009 forward-rolling — **[historical XONG · forward CHƯA bật]**
- Historical ✅ (commit `3edb5b1`): BTC 15m=190 273 / 4h=11 877, ETH 15m=190 238 / 4h=11 874; validate recompute PASS. Tới ~**2026-06-07**.
- **Live có cập nhật nến 15m/4h mới không:** ❌ **CHƯA ĐO** (set `kline_15m_btceth`/`kline_4h_btceth` ở 242, không với tới). Header task + AGENTS đều ghi **forward-rolling CHƯA bật** (historical-only). ⇒ Nhiều khả năng ts mới nhất đứng ~2026-06-07, KHÔNG tự tiến — nhưng cần scan 242 để chốt.

### Phát hiện chéo — `startHistoryCrawl` CHƯA bị gỡ (mâu thuẫn AGENTS)
- AGENTS ghi TASK-007 (`106baee`): "**GỠ startHistoryCrawl** (history→013)".
- **Thực tế code HEAD:** `startHistoryCrawl()` VẪN còn — `OpenInterestIngestor2AerospikeNew.java:49` (gọi) + `:67` (định nghĩa, thread `OI-History-Crawl`). `git show HEAD:` xác nhận đã committed như vậy, không phải sửa local.
- ⇒ **Việc "gỡ-crawl" CHƯA xảy ra trong code.** Bất kỳ jar build từ HEAD vẫn chạy crawl. "Bản gỡ-crawl + 016 + 019" mà deploy đang chờ **chưa tồn tại** — cần viết (gỡ crawl) + commit nốt 019 (2 file) trước khi gộp deploy. (Trả lời gián tiếp câu hỏi 019: nếu log 242 còn `OI-History-Crawl` thì ĐÚNG, vì code chưa gỡ.)

### Task DOING/chưa-đóng khác (theo AGENTS, đã được Desktop cập nhật trong session)
- `016` ✅ DONE (`3704b6e`) nhưng **CHƯA deploy** — chờ gộp với 019 + gỡ-crawl, 1 lần restart 242.
- `020` audit 2-process: 🟡 TODO (giao CCD #3) — chưa có `docs/PRODUCTION_AUDIT.md` (file output chưa tồn tại).
- `022` verify basis 1m: 🟡 TODO (giao CCD #2, Kaggle).
- `017/018` ⏸ chờ (sau 015 / sau 013-backfill). `H1` ghép ⏸ chờ A+B.

---

## 4. Tóm tắt cho Desktop reconcile (việc cần quyết)
1. **019:** commit 2 file working-tree (`DetectEntrySignal2TradeNormal` wiring + `FundingIngestor` heartbeat) — nếu KHÔNG, refresh funding vẫn DEAD trong HEAD dù lõi A đã có. Sau đó mới đúng "019 code-done".
2. **Sửa AGENTS:** note 007 "GỠ startHistoryCrawl" **SAI** — crawl vẫn trong code. Việc gỡ-crawl là TODO trước khi gộp deploy (016+019+gỡ-crawl).
3. **013:** dừng ở gate BƯỚC 1 (chờ user chốt schema 1.5); BƯỚC 2 + class backfill **chưa có** → đừng coi 013 sắp xong.
4. **015:** chưa có code/output/validate — đúng nghĩa "TODO", cần chạy trên 226.
5. **010:** code committed nhưng builder **chưa chạy 226** → set `symbol_lifecycle` chưa có data; giữ REVIEW.
6. **Mọi #record / range-ts / ts-mới-nhất Aerospike (013/010/009/019-ts):** session này KHÔNG đo được (242 firewall, không CLI). Cần 1 lượt scan đọc-only trên **226** (và trên **242** cho live) để điền số thật — KHÔNG suy đoán. → **TASK-023 P2 đã làm phần đo được, xem §5.**

---

## 5. Aerospike — SỐ THẬT ĐO (TASK-023 P2, tool `AerospikeStateScan` commit `ff579a6`)
> Đo **2026-06-14 08:45 GMT+7** từ máy **dev**. Tool scan cả 242+226; **242 = client null (firewall dev không kết nối** — đúng như recon). **226 = đo thật** dưới đây. Số **242** (live) còn TRỐNG → phải chạy lại tool **TRÊN 226** (226 thấy 242).

**226-BACKTEST (đo thật):**
| Set | Kết quả 226 | Ý nghĩa reconcile |
|---|---|---|
| `funding_data` (019) | BTC & ETH: 5954 điểm, **ts-cuối 2026-06-07 15:00** (cách now ~6d17h) | 226 là bản snapshot, **đứng yên** ở 2026-06-07 — không nhận live (live ở 242). Bình thường. |
| `open_interest` (013/007-C) | **#record = 0**, BTC/ETH không có | 226 **KHÔNG có OI**. Forward 007-C ghi 242; 013 backfill chưa làm. Khớp "013-B2 CHƯA". |
| `kline_15m_btceth` (009) | 132 key-tháng; BTCUSDT **startMs-cuối 2026-06-07 07:45** | Historical dừng ~2026-06-07; **không tiến trên 226** (forward-rolling chưa bật, khớp 009). |
| `kline_4h_btceth` (009) | 132 key-tháng; BTCUSDT **startMs-cuối 2026-06-07 03:00** | Như trên. |
| `symbol_lifecycle` (010) | **#record = 0 → RỖNG** | **Xác nhận chắc chắn: builder TASK-010 CHƯA chạy.** |

**242-LIVE (ĐO THẬT 2026-06-14 10:40 GMT+7, chạy `AerospikeStateScan` TRÊN 226 — sees 242):**
| Set | Kết quả 242 | Verdict |
|---|---|---|
| `funding_data` (019) | BTC & ETH: **5974 điểm** (>226: 5954), **ts-cuối 2026-06-14 07:00** (cách now ~3h40m = settlement gần nhất) | ✅ **funding live ghi 242 TƯƠI** — deploy 019 verified live. |
| `open_interest` (007-C) | **#record = 622**; BTC 3065 điểm ts **10:30** (10m trước); ETH 3113 ts **10:35** (5m trước) | ✅ **OI forward poll ghi 242 realtime** (khớp chu kỳ 5'); 622 symbol có OI. |
| `kline_15m_btceth` (009/031) | 132 key-tháng; BTCUSDT **startMs-cuối 2026-06-07 07:45** (đứng yên) | ✅ **historical CÓ ở 242** (2 job Aggregate đã ghi 242); ⚠️ chưa tiến → forward-roller 031 CHƯA deploy (đúng). |
| `kline_4h_btceth` (009/031) | 132 key-tháng; BTCUSDT **startMs-cuối 2026-06-07 03:00** | Như trên. |
| `symbol_lifecycle` (010) | **#record = 0 → RỖNG** | builder 010 CHƯA chạy (xác nhận cả 226 lẫn 242). |

**Chốt verify:** (1) 023-P2 HOÀN TẤT — số 242 đã đo. (2) 031 precondition: **historical kline_15m/4h ĐÃ ở 242** ✓; forward-rolling chưa live (đúng, chưa deploy). ⚠️ **Gap 06-07→nay (~7 ngày)**: khi bật 031, catch-up 15m trần 200 khung (~50h) KHÔNG đủ lấp 7 ngày → **trước/khi golive chạy lại `Aggregate15m4hBtcEth`** (ghi 242) để 242 current rồi forward giữ realtime (4h gap 7 ngày < trần 200 khung×4h nên tự lấp). (3) 019 + 007-C đã verify ghi 242 live.

**Lệnh chạy trên 226** (đọc-only, nhẹ; theo luật DỌN-JOB ghi PID+log riêng):
```bash
# trên 226, sau mvn -o package (jar đã gồm tool). 226 thấy cả 226 lẫn 242.
mkdir -p ~/java/simulator/outputs/.run
nohup java -cp target/binance-java-sdk-1.2.4.jar \
  com.binance.chuyennd.ai_ml.validation.data.AerospikeStateScan \
  > ~/java/simulator/outputs/.run/AerospikeStateScan.log 2>&1 & \
  echo $! > ~/java/simulator/outputs/.run/AerospikeStateScan.pid
# rồi đọc .log: sẽ có cả [242-LIVE] lẫn [226-BACKTEST] đầy đủ.
```
