# Index — Bản đồ tri thức

> Router: mỗi mục là pointer + 1 dòng tóm tắt. Không nhồi nội dung ở đây.
> Mục phình to → tách file riêng, để lại 1 dòng pointer.

## Tài liệu sống chính (đọc trước khi làm)
- [ROADMAP](ROADMAP.md) — lộ trình kiểm chứng 6 bước (0 look-ahead → 5 hợp nhất sim/product). Mục tiêu + thứ tự gác cổng.
- [PIPELINE](PIPELINE.md) — vận hành Walk-Forward 3 tháng: 2 pha, 9 bước, 2 cổng gác. Tài liệu vận hành chính thức.
- [REBUILD_ROADMAP](REBUILD_ROADMAP.md) — bản đồ rebuild (ADR-0009): P1 backfill coin die → cụm hạ tầng (lifecycle/validate/15m-4h) → P2 model (gate=0010 + funding=0011) qua 2-harness → P3 tích hợp. Trạng thái sống.
- [AGENTS](AGENTS.md) — **bản đồ CCD đang chạy** (owner/status/heartbeat mỗi task). Đọc TRƯỚC khi nhận task để không hai CCD đụng một việc / mất vết khi reset.
- [RUNBOOK_kaggle_multi_cpu](RUNBOOK_kaggle_multi_cpu.md) — **đã verify (2026-06-13): máy cá nhân push được 5 kernel CPU Kaggle chạy ĐỒNG THỜI** (max_concurrent=5). Quy trình push→poll(cầu dao 20')→lấy log→verify + snippet tái dùng. Dùng luôn, không cần smoke test lại.
- [FINDINGS](FINDINGS.md) — **NGUỒN SỰ THẬT**: mọi kết luận đã ĐO kèm số + lý do (edge entry vs DCA tự hủy, 3 target market model, funding P-fail, nguồn lỗ đuôi, filter mode C...). Đọc file này là nắm toàn bộ.

## Code-map / audit chi tiết (tham chiếu khi đụng code)
- [AUDIT_filter_ablation](AUDIT_filter_ablation.md) — luồng filter (AIRejectFilter, nhánh EARLY, FILTER_MODE) + code nguyên văn. ⚠️ giá trị Configs trong file là snapshot lúc viết (vd SLIPPAGE 0.0005) — giá trị chốt hiện tại xem FINDINGS/TRACE.
- [BO_CODE_DIGEST](BO_CODE_DIGEST.md) — code-map exit booking (calTp, kẹp priceTP, closeOrder) + survivorship/delist (updateSymbolDeListed, symbol_mapper, universe). ⚠️ là snapshot dòng code.
- [TRACE_backtest_drift](TRACE_backtest_drift.md) — truy vết vì sao backtest không tái lập + quy trình chống drift (commit trước khi chạy, ghi commit/giai đoạn/Configs/set Aerospike).

## Nợ kỹ thuật
- [LIB_BINANCE_OLD](LIB_BINANCE_OLD.md) — dual-connector (com.binance.client cũ vs io.github.binance 3.0.4 mới), migration đang dở; bản cũ trên đường đặt lệnh live. Đề xuất gom về 1 connector (phased, chưa làm).
- [DEFERRED](DEFERRED.md) — hoãn tới khi có CI/CD: fix parser Configs `split("=",2)`, tách DIED_SYMBOLS SIM/LIVE, soi coin lọt backtest.

## Quyết định (ADR) — đã chốt, chống sửa-ngược
- [0001](decisions/0001-do-luong-exit-maxdd-mae.md) — đo lường: exit booking, maxDD per-tick, MAE (vì sao KHÔNG revert).
- [0002](decisions/0002-look-ahead-guard.md) — look-ahead guard: vị trí thật + đảm bảo.
- [0003](decisions/0003-genome-13-gene.md) — genome 13 gene (bỏ MIN_MOMENTUM_24H).
- [0004](decisions/0004-ky-luat-config-version.md) — kỷ luật CONFIG_VERSION (hiện v8).
- [0005](decisions/0005-tran-inference-funding.md) — trần inference funding: scale ngang / đổi engine, không tuning node.
- [0006](decisions/0006-quy-trinh-golden-backtest-regression.md) — quy trình golden backtest regression (fast/full + fingerprint + chống drift khi thay đổi).
- [0007](decisions/0007-survivorship-backfill.md) — survivorship nặng: backtest thiếu 39 coin delist (LUNA/FTT/RAY…, dd TB −60.9%) → phải backfill + đo impact bằng golden.
- [0008](decisions/0008-circuit-breaker.md) — breaker: MARGIN halt 0.70 hiệu quả (DD −58%→−43%); DCA cap (DD vs avgEntry) VÔ HIỆU cấu trúc → bỏ, redefine theo vốn/concentration.
- [0009](decisions/0009-pivot-rebuild-data-model.md) — **PIVOT**: training data méo (thiếu coin die) + ONNX không tái tạo được → rebuild: backfill đủ data → model mới (ONNX=baseline) → gen + chụp lại toàn bộ baseline → tối ưu. Dừng tune breaker.
- [0010](decisions/0010-market-model-gate-design.md) — market = **GATE**: label 3-lớp forward-return (bỏ label cũ 15M/4H), bỏ time-feature, candidate SMA/alignment/regime/ETH; phải THẮNG rule trần mới giữ ML.
- [0011](decisions/0011-funding-model-selector.md) — funding = **SELECTOR** per-coin: label triple-barrier (bỏ peak-touch một chiều), thêm funding-deep/volume-z/cross-sectional, OI/LS forward-ingest (chưa có history); symbolPred=pred[0]=P(fail). Đang phân tích, chưa chốt.

## Tasks
- Xem thư mục [../tasks/](../tasks/). **Quy ước số: theo thứ tự LOGIC (phụ thuộc/thực hiện), không theo thứ tự tạo. Chèn giữa = thập phân (vd `003.1`). Xen ngang / lật lại = tạo task số đúng vị trí + update, KHÔNG đánh lại cả dãy.**
- Trạng thái: `001` (done) · `002` (done) · `003-golden-backtest-tool` (done — baseline FAST @ `df28a5b`) · `003.1-golden-multirange` (done — Recent/Crash/Bull) · `003.2-golden-full-baseline` (done — baseline-FULL @ `571b9b2`) · `004-backfill-pilot` (closed/deferred) · `006-circuit-breaker` (done — MARGIN đáng áp DD −58%→−43%; DCA cap chưa kết được vì thiếu coin chết).
- `005-backfill-coin-die-training` (todo — P1 pivot: fill coin die cho training) · `006.1-dca-scenario-luna` (done — DCA-không-giới-hạn mất 99% vốn; cap −0.30 vs avgEntry VÔ HIỆU cấu trúc; ADR-0008) · `006.2` KHÔNG mở (dừng tune breaker tới khi model mới final).
- **PIVOT — ADR-0009: rebuild trên data đầy đủ + model mới (ONNX=baseline).** Next = **P1 backfill `005`** (ticker coin die: 226→audit→242→re-export 100% training). Rồi P2 làm model (chọn label/chiến lược), P3 gen prediction + chụp lại TOÀN BỘ golden baseline + tối ưu dần. ⚠️ backfill đổi data nền ⇒ baseline cũ (FAST/CRASH/BULL/FULL) + 006/006.1 phải làm lại.

## Archive (stale, giữ để truy vết)
- [archive/](archive/) — README lib upstream, ProjectPipeLines fragment.

---
## Quyết định-chốt còn nằm trong FINDINGS/TRACE, NÊN tách ADR (chưa làm)
> Đề xuất ADR 0006+ để tham chiếu nhanh:
- SLIPPAGE_RATE=0.003 + quy trình tái lập backtest (từ TRACE + FINDINGS §7).
- Filter mode C / bỏ predReturn24H khỏi filter (A=C, vô dụng) — FINDINGS §4.
- Bỏ 24H model, giữ insight "giữ lâu → chạm mục tiêu cao" — FINDINGS §2b.
- dd4h là volatility proxy nhưng giữ trong nhánh RISK (+31% PnL) — FINDINGS §2c, §4.
- AI filter KHÔNG chặn được cú sập → chống sập là tầng breaker riêng — FINDINGS §4, §10.
- Funding symbolPred = pred[0] = P(fail) + cạm bẫy decode (đổi thứ tự output = sai âm thầm) — FINDINGS §3.
