# Fix parity K5 live↔backtest + deploy — 2026-08-21

## Vấn đề (đã chứng minh bằng code)
Live "K5" KHÁC backtest "K5" ở 2 chỗ (DetectEntrySignal2TradeNormal vs SimulatorMarketLevelTicker1MStopLoss):
1. **Ngưỡng per-symbol:** live lọc coin qua `maxThres` (predictAllCandidates L451) VÀ `checkSignalDynamic` (createOrderBuyRequest L491) trước khi vào. Backtest RANK-mode (Simulator L349-352) BỎ ngưỡng, lấy top-K theo score. → live đói lệnh/chọn coin khác lúc market yếu.
2. **Thứ tự cap vs skip-held:** live skip coin đang giữ KHÔNG tính slot → đào sâu lấp đủ K coin mới (vào rank>K). Backtest lấy top-K của pool đầy đủ RỒI mới skip held → ≤K, không quá rank K. → live vào coin backtest không vào + tích vị thế nhanh (83 vị thế).

## Fix (4 edit, chỉ ảnh hưởng path selector PREDICT_SYMBOL_TRADE khi SELECTOR_RANK_TOPK>0)
- Thêm `selectorRankPool` (pool đầy đủ, trước lọc maxThres) trong predictAllCandidates.
- Loop selector: rank-mode dùng selectorRankPool + **cap-then-skip** (đếm rank trên toàn pool kể cả held → break tại K → skip held sau). TOPK<=0 giữ byte-identical.
- createOrderBuyRequest: rank-mode KHÔNG gọi checkSignalDynamic → rơi xuống checkSignal (market-only) = backtest.
- GIỮ nguyên cầu dao (is50PercentOrderLossProd) + CoinRankManager tier (bảo vệ, live-only, không thuộc "2 cái").

## Deploy (theo runbook)
- Build mvn (main tree, có PrivateConfig) → jar 99,622,747, verify class có `selectorRankPool`.
- scp → 242, backup `target/...jar.bak_preparity_20260821` + `conf/env.sh.bak_preparity_20260821`.
- **SHADOW verify trước:** restart SHADOW_NO_PUSH=true. Kết quả (tick 16:14, 16:29):
  - Selector (PREDICT_SYMBOL_TRADE): 1 rồi 2 would-BUY/tick → **≤5, cap #2 OK**.
  - **KHÔNG flood** từ #1 (bỏ ngưỡng) ở regime yếu (1–2 selector/tick, như cũ). 0 exception.
  - (Phụ) tick 16:14 có 14 `DCA_LEVEL1` = market-crash DCA của DcaProcessor nhồi vào 14 vị thế đang giữ — KHÔNG phải selector, KHÔNG bị cap, tôi KHÔNG đụng.
- **Bật thật:** SHADOW_NO_PUSH=false + restart. pid 30972, env đúng (K5/arm3/pred-gap/moveSL0.05), 83 vị thế, 0 exception. Parity fix LIVE.

## Rollback
- Jar: `cp target/binance-java-sdk-1.2.4.jar.bak_preparity_20260821 target/binance-java-sdk-1.2.4.jar` + daemon.sh restart.
- env: `cp conf/env.sh.bak_preparity_20260821 conf/env.sh` + restart.
- Source: 4 edit CHƯA commit (checkpoint trước = 463edee). User tự push.

## Cảnh báo / theo dõi (flaws-first)
1. **Flood risk từ #1 CHƯA test ở regime mạnh.** Shadow chỉ bắt regime yếu (1–2 selector/tick). Market broad-pump: bỏ ngưỡng → có thể vào top-5 mỗi tick → cộng 83 vị thế + CHƯA có disaster-exit → phình nhanh. **Cần theo dõi entries/tick vài ngày**; nếu tăng vọt cân nhắc rollback #1 hoặc thêm cap concurrent.
2. **Live đang DCA-down mạnh** (14 DCA_LEVEL1/tick khi dip) — đúng kiểu averaging-down-vào-loser mà doc collapse cảnh báo. Pre-existing, tách riêng để review.
3. Disaster-exit vẫn CHƯA có (83 vị thế ride) — đòn bẩy data ủng hộ mạnh nhất, nên làm tiếp.
