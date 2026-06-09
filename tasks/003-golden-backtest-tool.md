# TASK-003: Dựng tool GoldenBacktest (regression harness)

- **status:** done (FAST) — bước 0 determinism PASS; fingerprint FAST đã ghi (`outputs/golden/FAST-55973e3.json`). Còn chờ user DUYỆT promote baseline (`docs/golden/baseline-FAST.json`) + (tuỳ chọn) profile FULL.
- **Milestone:** Change control cho backtest — hiện thực hóa ADR-0006. Độc lập với chuỗi survivorship (001/002).
- **Thực thi bởi:** Claude Code (**Java**, chạy trên 226).
- **Quyết định nền:** ADR-0006 (quy trình) + ADR-0004 (CONFIG_VERSION) + TRACE_backtest_drift (reproducibility).

## Mục tiêu (1 câu)
Tool Java chạy backtest ở cấu hình cố định (FAST/FULL), xuất fingerprint, so baseline trong repo, in diff, và BÁO ĐỎ khi input-stamp không đổi mà metric đổi.

## Scope
**Trong scope:** Java thuần GỌI `SimulatorMarketLevelTicker1MStopLoss` qua `BacktestIntegrityGuard`; thu metric; stamp; ghi/so fingerprint.
**Ngoài scope:** KHÔNG sửa engine core (chỉ gọi), KHÔNG sửa logic vào/đóng lệnh, KHÔNG ingest Aerospike.

## Các bước
0. **Verify determinism (CỔNG TIÊN QUYẾT):** chạy FAST 2 lần cùng commit/config/data → fingerprint phải KHỚP HỆT. Nếu lệch → BÁO nguồn nghi (thứ tự HashMap, parallel, tz…), DỪNG. Không dựng tiếp khi sim chưa deterministic.
1. **Hai profile:**
   - FAST: `START=20251001, END=20260430`.
   - FULL: `START=` mốc data đầu (vd 20210101) `END=` hiện tại.
2. **Thu metrics:** PnL (FULL: từng năm + tổng; FAST: đoạn) · maxDD = `unProfitMin` · `numTrades` · số cụm giữ > 30 ngày (`timeUpdate − timeStart > 30*TIME_DAY`) · `worstSingleLoss` · `nearLiq`.
3. **Stamp:** `commit` (git rev-parse HEAD) · `CONFIG_VERSION` · set Aerospike market + funding · `SLIPPAGE_RATE/RATE_FEE/APPLY_SLIPPAGE/BLOCK_INTRABAR_LOOKAHEAD/FILTER_MODE`. Cảnh báo nếu working-tree bẩn (theo TRACE).
4. **Ghi fingerprint:** `outputs/golden/{profile}-{commit}.json` (mỗi lần chạy). Baseline duyệt: commit vào repo tại `docs/golden/baseline-{profile}.json` (KHÔNG để trong outputs/ bị gitignore).
5. **So baseline + phán quyết:**
   - STAMP-input KHỚP baseline mà metric đổi → in REGRESSION + exit code ≠ 0 (đỏ). `numTrades` & số-cụm-găm khớp tuyệt đối; PnL/maxDD epsilon float.
   - STAMP-input KHÁC baseline → in diff report (Δ theo thứ tự ưu tiên), exit 0, KHÔNG tự ghi đè baseline — chờ người duyệt.

## Acceptance criteria (Code tự kiểm trước khi báo done)
- [ ] Bước 0 determinism PASS (2 lần khớp). Nếu FAIL → báo rõ + dừng, KHÔNG bịa qua.
- [ ] Fingerprint gồm đủ STAMP + 6 nhóm metric trên.
- [ ] Phân biệt REGRESSION (đỏ) vs baseline-update (review) bằng STAMP-input.
- [ ] `numTrades` + số-cụm-găm so khớp tuyệt đối khi input không đổi.
- [ ] Chạy qua `BacktestIntegrityGuard`; KHÔNG sửa engine core.
- [ ] Java, log SLF4J/Log4j2, KHÔNG `System.out`/`printStackTrace`.
- [ ] Baseline ghi vào `docs/golden/` (commit được), không phải outputs/.

---
## (Code điền) Kết quả

- Tool: `src/main/java/com/binance/chuyennd/ai_ml/validation/GoldenBacktest.java` (Java, SLF4J, gọi `SimulatorMarketLevelTicker1MStopLoss` qua `BacktestIntegrityGuard`; KHÔNG sửa engine core). Modes: `verify` | `FAST` | `FULL`. Chạy trên **226**, đọc data từ **Aerospike** (`IS_HPO_MODE=IS_KAGGLE_MODE=false`, `-Xmx12g`).
- **BƯỚC 0 — DETERMINISM GATE: ✅ PASS** (2026-06-09 13:41). Chạy FAST 2 lần cùng commit/config/data → fingerprint KHỚP TUYỆT ĐỐI. Metric khớp 2 lần:
  - PnL (FAST 20251001→20260430) = **6510.72**
  - maxDD (`unProfitMin`, đáy thật) = **−19613.02**
  - worstSingleLoss = **−808.87**
  - numTrades = **14154**
  - clusters held >30d = **19**
  - nearLiq = **0**
  - PRE-FLIGHT: `lookahead_block=true · slippage_apply=true · SLIPPAGE_RATE=0.003 · RATE_FEE=0.002 · FILTER_MODE=A · CONFIG_VERSION=v8`. Funding pred set = `funding_pred_1m_v5` (2.827M records), market 2.804M, ai_pred 2.819M. → sim TẤT ĐỊNH, đủ điều kiện dựng tiếp regression harness.
- **BƯỚC 1-4 (FAST fingerprint) — ✅ XONG** (2026-06-09 16:00, sau khi user fix `config.properties` `DIED_SYMBOLS=BTCDOM` hết rỗng). File: `226:/home/chuyennd/java/simulator/outputs/golden/FAST-55973e3.json` (đã kéo về `outputs/golden/` local). Nội dung:
  - profile=FAST start=20251001 end=20260430 · stamp: commit=55973e3 **dirty=true** cfg=v8 · sets[mkt=`market_data_object` funding=`funding_pred_1m_v5` ticker=`kline_1m_opt`] readCluster=242 · slip=0.003 fee=0.002 applySlippage=true blockLookahead=true filter=A.
  - metrics: PnL=**6510.72** (2025=5809.70 / 2026=701.02) · maxDD=**−19613.02** · worstSingleLoss=**−808.87** · numTrades=**14154** · clustersHeld30d=**19** · nearLiq=**0** — KHỚP TUYỆT ĐỐI với determinism run.
- **BƯỚC 5 (so baseline) — chưa có baseline:** tool cảnh báo `docs/golden/baseline-FAST.json` chưa tồn tại → đây là fingerprint ĐẦU, KHÔNG tự promote (đúng thiết kế: chờ người duyệt). Lệnh promote khi duyệt: `cp outputs/golden/FAST-55973e3.json docs/golden/baseline-FAST.json` rồi commit.
  - ⚠️ stamp **dirty=true** (working-tree bẩn, tool GoldenBacktest + docs/tasks chưa commit) → baseline từ commit-bẩn KHÔNG tái lập chắc từ 1 commit. Khuyến nghị: commit tool TRƯỚC, chạy lại FAST trên commit-sạch, rồi mới promote baseline.

## (Code điền) Phát hiện ngoài scope

- **BUG PARSER `Configs.java:38` (ảnh hưởng cả LIVE):** dòng `KEY=` (value rỗng) làm `line.split("=")[1]` ném AIOOBE → toàn bộ app `System.exit(0)`, không khởi động được. Mọi process (live trading, ingest, HPO, sim) đều qua `Configs.<clinit>`. Fix tối thiểu: `split("=", 2)` + chấp nhận value rỗng. Không đổi giá trị nào → KHÔNG bump CONFIG_VERSION.
- **`DIED_SYMBOLS` là bộ lọc loại trừ ở lõi dùng chung (liên quan TASK-004 bước 0b):** `Constants.diedSymbol` được dùng tại `MarketBigChangeDetector:63` (SIM+LIVE), ingestor, feature export, `DetectEntrySignal2TradeNormal:133`. ⇒ backfill ticker coin chết KHÔNG đủ để arm-B thấy chúng — phải bỏ chúng khỏi `DIED_SYMBOLS`. (Đã ghi chi tiết để TASK-004 dùng.)

## (Code điền) Quyết định phát sinh

- **Configs `:38`:** user đã xử lý bằng sửa FILE config trên server (bỏ value rỗng) — KHÔNG sửa parser. ⚠️ Bug `split("=")` vẫn TIỀM ẨN: value rỗng (hoặc value chứa `=`) trong tương lai sẽ lại làm app `System.exit(0)`, kể cả LIVE. Khuyến nghị fix tận gốc `split("=", 2)` — chưa làm theo ý user.
- **Baseline FAST:** vẫn chưa promote. Fingerprint hiện tại `55973e3` là commit **dirty** (tool GoldenBacktest + docs/tasks chưa commit). Cần: commit sạch → chạy lại FAST → khớp 6510.72 → `cp outputs/golden/FAST-<sha>.json docs/golden/baseline-FAST.json` + commit.
