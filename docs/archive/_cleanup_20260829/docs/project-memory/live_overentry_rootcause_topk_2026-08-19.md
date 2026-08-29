# Gốc "vào lệnh liên tục" của live = THIẾU cap SELECTOR_RANK_TOPK — 2026-08-19

## Kết luận (bug thật, high-value)
Live vào lệnh nhiều hơn backtest vì **leg selector của live KHÔNG áp cap top-K**, trong khi backtest cap 5.
- Backtest `SimulatorMarketLevelTicker1MStopLoss:349`: `if (SELECTOR_RANK_TOPK>0) nSel=min(TOPK,len); lấy nSel coin score thấp nhất`
  → tối đa 5 coin/tick (rank-based, bỏ qua ngưỡng tuyệt đối, tự chuẩn hoá theo regime).
- Live `DetectEntrySignal2TradeNormal` vòng PREDICT_SYMBOL_TRADE: `for (entry : sortedCandidates) { if held continue; createOrderBuyRequest(...) }`
  → vào MỌI coin qua gate + ngưỡng per-symbol (checkSignalDynamic), KHÔNG break tại K.
- `grep SELECTOR_RANK_TOPK` toàn repo: chỉ có ở research(sim) + probe + Configs; **KHÔNG có trong package trading (live)**.

## Hệ quả
- Thị trường pump rộng → nhiều coin qua ngưỡng → live vào hết → 72–75 vị thế đồng thời + stacking dày (BTW×7).
- Backtest (top-5 cap) chỉ ~1.2 lệnh/ngày, 2230 lệnh/5 năm; live vào dày hơn hẳn. Đây là divergence THỰC THI, không phải
  bug entry-price/gate (những cái đó đã verify khớp). Edge backtest được validate VỚI cap 5 → live uncapped = ngoài phân phối đã test.

## Fix (đề xuất, cần patch cẩn thận + shadow verify)
- Áp top-K vào vòng selector live: sortedCandidates là TreeMap<Float score asc> = tốt nhất trước. Lấy K coin
  not-held đầu tiên (mirror sim rank-mode: bỏ qua ngưỡng tuyệt đối, chỉ lấy best-K; gate market-level vẫn áp riêng),
  break sau khi đã tạo K entry. K = Configs.SELECTOR_RANK_TOPK (env=5).
- Sắc thái phải khớp sim: sim rank-mode BỎ ngưỡng maxThres, chỉ rank; live hiện áp checkSignalDynamic per-coin.
  → quyết định: giữ gate + bỏ per-symbol-abs-threshold khi rank-mode? hay giữ cả hai rồi cap K? Phải đối chiếu để
  live == backtest. (Cần đọc kỹ checkSignalDynamic + sim gate path trước khi vá.)
- Verify bằng shadow: sau fix, đếm `would-BUY`/tick phải ≤ K(5); nhịp vào lệnh/ngày về gần backtest.

## Trạng thái
- Shadow-mode đang BẬT (SHADOW_NO_PUSH=true) → an toàn để deploy fix + đối chiếu trước khi mở lại push lệnh.
- CHƯA vá. Chờ user duyệt hướng fix (semantics rank-mode) rồi patch + build + deploy + verify.
