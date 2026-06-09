# Index — Bản đồ tri thức

> Router: mỗi mục là pointer + 1 dòng tóm tắt. Không nhồi nội dung ở đây.
> Mục phình to → tách file riêng, để lại 1 dòng pointer.

## Tài liệu sống chính (đọc trước khi làm)
- [ROADMAP](ROADMAP.md) — lộ trình kiểm chứng 6 bước (0 look-ahead → 5 hợp nhất sim/product). Mục tiêu + thứ tự gác cổng.
- [PIPELINE](PIPELINE.md) — vận hành Walk-Forward 3 tháng: 2 pha, 9 bước, 2 cổng gác. Tài liệu vận hành chính thức.
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

## Tasks
- Xem thư mục [../tasks/](../tasks/). Trạng thái: `001` (done — 39 coin thiếu) · `002` (done) · `003-golden-backtest-tool` (done FAST — chờ commit sạch + promote baseline) · `004-backfill-pilot` (todo) · `005` full backfill (sẽ mở) · `006-golden-multirange` (todo — 3 range Crash/Bull/Recent, sau khi baseline gốc chốt).

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
