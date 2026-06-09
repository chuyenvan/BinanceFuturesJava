# Reconcile report — đối chiếu workflow-docs vs codebase thật

> Read-only. KHÔNG sửa code/CLAUDE.md/roadmap/index. Chỉ ĐỀ XUẤT. Ngày: 2026-06-09.
> Hiện trạng cấu trúc: Maven (pom.xml, shade fat jar + protobuf, Java 11). Package gốc
> `com.binance.chuyennd.*`; `com.binance.client.*` = connector vendored (coi như lib).
> Entry-point live: `websocket/BinanceDataIngestor.main`, `trading/BinanceOrderTradingManager.main`.
> **KHÔNG có `src/test`** → "test" = các class `main()` đứng riêng (tools/validators/benchmark).
> Top dirs: `docs/ logs/ python/ src/ storage/ target/ tasks/`.

---

## A. Tài liệu cũ cần gom

> Hiện đã kéo vào `docs/` nhưng còn RỜI RẠC (chưa nằm `docs/insights/`, chưa có pointer ở `index.md`).
> Đề xuất tạo `docs/insights/` và mỗi file để lại đúng 1 dòng pointer ở `docs/index.md`.

- `docs/FINDINGS.md` → `docs/insights/findings.md` — tổng hợp phát hiện model/backtest; CLAUDE.md cảnh báo "findings hay đánh rơi LÝ DO" → nên rã các quyết định trong đây thành ADR, phần còn lại làm insight.
- `docs/AUDIT_filter_ablation.md` → `docs/insights/filter-ablation.md` — kết quả ablation entry-filter (gắn Bước 2 roadmap: edge AI vs DCA).
- `docs/TRACE_backtest_drift.md` → `docs/insights/backtest-drift.md` — trace lệch product-vs-backtest; gắn "Validate product vs backtest" của roadmap.
- `docs/PIPELINE.md` → `docs/insights/pipeline.md` — mô tả luồng data→feature→ONNX→signal; là kiến trúc nền, đáng giữ làm insight chính.
- `docs/LIB_BINANCE_OLD.md` → `docs/insights/lib-binance-old.md` — ghi chú connector cũ vendored (liên quan migration `io.github.binance`).
- `docs/BO_CODE_DIGEST.md` → `docs/insights/b0-exit-survivorship-digest.md` — digest exit-booking + survivorship (read-only digest vừa tạo).
- `docs/README.md` → giữ tại chỗ HOẶC gộp 1 dòng vào `index.md` — README docs ngắn, không phải insight.
- `ProjectPipeLines` (root, không đuôi) → `docs/insights/` nếu là notes (cần liếc nội dung trước khi gom).
- `python/tool/*.py` (`train_market_xgboost_optuna.py`, `train_fundingfee_xgboost_optuna.py`, …) → KHÔNG phải doc, nhưng là nơi chứa 2 lỗi leak ở Bước 1 (xem C) — chỉ trỏ tới, không gom.

## B. Quyết định đã có trong code nhưng thiếu ADR

> Quan sát ở mức cấu trúc; mỗi cái là quyết định kiến trúc/thuật toán ĐÃ neo trong code, chưa có ADR ghi WHY.

- **Bịt look-ahead nội-nến** (`BLOCK_INTRABAR_LOOKAHEAD`) @ `OrderTargetInfoTest.updateStatusNew` + `BacktestIntegrityGuard.assertProductionGrade()` — vì sao tách đặt-SL khỏi khớp-lệnh; đây là rule gác cổng mọi backtest.
- **Kẹp giá chốt trailing-stop** `priceTP = Math.min(priceSL, ticker.maxPrice)` @ `OrderTargetInfoTest.java:158,173` — sửa PnL "thổi" khi nến gap thủng SL; quyết định kẹp theo HIGH (không phải open).
- **maxDD nguồn THẬT per-tick** `trueUnrealizedMin` (bar.low) thay `Σ profitMin` @ `BudgetManagerSimple` + `BalanceIndex`; nuôi `HPOFitnessCalculatorV3` — đổi bản chất fitness (DD ~ -56% thay vì -35%).
- **maeLow = MAE thật** (không reset như `minPrice`) @ `OrderTargetInfoTest` — vì sao tách field đo-lường khỏi field trailing.
- **Ngưỡng phạt DD fitness 15/30/40% + kill-switch >40%** @ `HPOFitnessCalculatorV3` — calibrate vùng phạt; đang áp lên DD thật (chọn "nghiêm").
- **CONFIG_VERSION discipline (v5→v8)** @ `RunHpoMaster_Distributed` — quy tắc bump khi đổi thứ ngoài genome; lý do từng version nằm trong comment, nên nâng thành ADR.
- **Định tuyến đọc 226 vs 242** `getReadClient()` (kaggle/hpo→226) @ `DataManagerAerospikeFloatSim` — vì 242 khóa firewall; ai đọc set nào ở đâu.
- **Task lifecycle có trạng thái** (PENDING/RUNNING/DONE, reclaim stale 3h, CAS generation) @ `AerospikeTaskCoordinator` — thay cơ chế delete-on-claim; chống mất task khi worker chết.
- **Funding gen: chỉ lưu pred[0] (len=1) + async write + reset HistoryManager/CoinRankManager mỗi task** @ `GenerateFundingPredictionsTool` — quyết định format set + chống contamination shuffle.
- **Genome HPO 13 gene (bỏ MIN_MOMENTUM_24H), gỡ predReturn24H/MOM24 toàn hệ** @ `RunHpoMaster_Distributed` + filter — quyết định loại feature.
- **Inference funding bị chặn 4-core (tree 262MB), không 10x bằng config** @ benchmark `FundingInferenceBenchmark` — quyết định scale ngang thay vì tối ưu engine.

## C. Việc đang dở nên thành task

> Phần lớn bắt nguồn từ chính `docs/ROADMAP.md` (các bước chưa làm) + 1 TODO trong code.

- **Đối chứng look-ahead guard bật/tắt** (Bước 0 "việc còn lại") @ `BacktestIntegrityGuard`/`Simulator` → `tasks/001-lookahead-ab-check.md`.
- **Re-train model đúng cách** (cắt thời gian, scaler fit train-only, holdout) — sửa 2 leak @ `python/tool/train_market_xgboost_optuna.py`, `train_fundingfee_xgboost_optuna.py` → `tasks/002-retrain-no-leak-holdout.md`.
- **Đo IC/hit-rate model trên holdout** (Bước 1) → `tasks/003-model-ic-holdout.md`.
- **Ablation AI vs DCA** (Bước 2, dùng `EdgeAttributionReport` đã có, MAE đã sửa) → `tasks/004-ablation-ai-vs-dca.md`.
- **Mô hình hóa cháy tài khoản + trần DCA + funding fee** (Bước 3; `updateFundingFee` đang comment toàn bộ @ `OrderTargetInfoTest:222`) → `tasks/005-risk-death-model.md`.
- **WFO + giảm gene** (Bước 4) → `tasks/006-wfo.md`.
- **Hợp nhất EntryDecisionCore sim/product** (Bước 5) → `tasks/007-unify-entry-core.md`.
- **Regen funding v6 + validate v5 vs v6** (dùng `CompareFundingSetV5V6` đã có) → `tasks/008-funding-v6-validate.md`.
- **TODO verify label6 prediction** @ `CheckLabel6Predictions.java:102` → `tasks/009-checklabel6.md` (nhỏ).
- **Dọn nợ logging trên đường live/core** (xem E) → `tasks/010-logging-debt.md`.

## D. Roadmap không khớp thực tế (CHỈ BÁO — roadmap thuộc quyền bạn)

- Roadmap Bước 0 ghi guard "cắm trong `BackTestEngineMaster.run`", nhưng thực tế (và CLAUDE.md) guard cắm ở **NÚT CHẶN DUY NHẤT `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry()`** — lệch vị trí.
- Roadmap Bước 0 "việc còn lại / bump CONFIG_VERSION" đã bị THỰC TẾ vượt qua: `CONFIG_VERSION` hiện **v8** (đã qua nhiều thay đổi: maxDD-thật, kẹp exit). Roadmap chưa phản ánh các fix backtest đã làm phiên gần đây (maxDD per-tick, exit clamp, MAE maeLow).
- Roadmap Bước 4 nói "14 → ~8 gene", nhưng genome **đã là 13** (đã bỏ MIN_MOMENTUM_24H ở v6). Mốc "14" đã cũ.
- Roadmap Bước 3 liệt kê slippage "đã có ở Bước 0" (đúng) nhưng KHÔNG nhắc maxDD-thật/exit-clamp vốn cũng phục vụ "để backtest được phép sụp trung thực" — nên bổ sung hoặc trỏ ADR.
- `docs/index.md` trỏ `[Roadmap](ROADMAP.md)` → file thật `docs/ROADMAP.md` (OK trên FS case-insensitive, nhưng nên thống nhất hoa/thường để chuẩn). Mục insight ví dụ `insights/measurement-bugs.md` chưa tồn tại (mới là placeholder).

## E. Vi phạm ràng buộc CLAUDE.md trong code (nợ kỹ thuật — KHÔNG tự sửa)

> CLAUDE.md: chỉ SLF4J, cấm `System.out`/`System.err`/`printStackTrace`. Đây là refactor NGOÀI scope phiên này.
> Loại trừ `com.binance.client.*` (connector vendored — coi như lib, không thuộc rule).

- `printStackTrace`: **~59 lần / 30 file**. Trên đường LIVE/CORE (ưu tiên dọn): `trading/BinanceOrderTradingManager.java`, `trading/DetectEntrySignal2TradeNormal.java`, `trading/BudgetManager.java`, `research/SimulatorMarketLevelTicker1MStopLoss.java`, `research/BudgetManagerSimple.java`, `research/FundingFeeManager.java`, `tradecore/Configs.java`, `tradecore/MarketBigChangeDetector.java`, `ai_ml/hpo/master/BackTestEngineMaster.java`, `ai_ml/hpo/master/RunWorkerKaggle.java`, `ai_ml/features/export/funding/FundingDataCollectionManager.java` (3).
- `System.out`/`System.err`: **~139 lần / 30 file**. Trên core/live: `utils/Utils.java` (11 — shared), `aerospike/DataManagerAerospikeFloatSim.java` (3), `tradecore/Configs.java`, `tradecore/TradeUtils.java`, `trading/BinanceOrderTradingManager.java`. Phần lớn còn lại ở tool/benchmark/validator (`MemoryAnalyzerTool` 22, `TickerReadSpeedTest` 13, `Test` 10, `DataMigrator` 8, `AerospikeCheckData` 7…) — ưu tiên thấp.
- TODO chưa làm: `aerospike/validate_data/predictsymbol/CheckLabel6Predictions.java:102`.
- Ghi chú: nhiều `printStackTrace` nằm trong catch của vòng lặp bar Simulator → nuốt lỗi âm thầm (rủi ro: lỗi 1 phút bị bỏ qua, kết quả thiếu mà không báo). Đáng nâng lên LOG.error có ngữ cảnh khi dọn.

---

## Đề xuất thứ tự xử lý

1. **(D) Sửa lệch roadmap nhỏ** (vị trí guard, gene 14→13, CONFIG_VERSION v8) — bạn quyết, nhanh, để mọi việc sau bám đúng thực tế.
2. **(B) Viết ADR cho các quyết định backtest cốt lõi vừa làm** (exit-clamp, maxDD-thật, maeLow, CONFIG_VERSION discipline, task-lifecycle) — neo WHY trước khi tri thức trôi khỏi chat.
3. **(A) Tạo `docs/insights/` + gom FINDINGS/AUDIT/TRACE/PIPELINE/digest + thêm pointer ở `index.md`** — dọn doc rời, rã FINDINGS thành ADR/insight.
4. **(C) Mở task Bước 0 đối chứng look-ahead** (gác cổng) → rồi **Bước 1 re-train no-leak + IC holdout** (gác cổng mọi HPO).
5. **(C) Task Bước 2 ablation AI-vs-DCA** (công cụ đã sẵn, MAE đã đúng) — rẻ, quyết định model có edge.
6. **(C) Task funding v6 validate + regen** (đang dở, có worker + tool so sánh).
7. **(C) Bước 3 risk-death + Bước 4 WFO + Bước 5 unify** — nặng, chỉ làm khi 1–2 PASS.
8. **(E) Task dọn nợ logging** — làm dần theo file, ưu tiên đường live/core; mỗi lần là 1 task nhỏ có scope rõ (tránh refactor hàng loạt).

---

## File đã đọc
- `CLAUDE.md` (hướng dẫn dự án — đã có sẵn trong context phiên)
- `docs/index.md`
- `docs/ROADMAP.md`
- (khảo sát cấu trúc, KHÔNG đọc sâu) `pom.xml` layout, `src/main/java/**`, `python/tool/*`, root files
- (grep) TODO/FIXME/XXX, `printStackTrace`, `System.out`/`System.err`
- (liệt kê) `docs/*.md`, root `*.md` + `ProjectPipeLines`
