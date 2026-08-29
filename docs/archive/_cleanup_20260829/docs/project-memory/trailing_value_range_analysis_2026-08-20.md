# Trailing — phân tích khoảng giá trị (roadmap #8) — 2026-08-20

## Công thức (source TradeUtils)
- ARM (dời SL bắt đầu): `arm = TS_PROFIT_MULTIPLIER × max(RATE_PROFIT_STOP_MARKET, pred×TS_DYNAMIC_K)`.
  Live: 5.21847 × max(0.05, pred×0.29774).
- GAP (SL cách đỉnh): `gap = TS_GIVEBACK_FLOOR ? max(mp×RATIO, TS_MIN_GAP) : min(mp×RATIO, TS_MAX_GAP)`;
  weak (pred<TS_WEAK_MOMENTUM_THRES 0.004) → TS_MAX_GAP_WEAK 0.03. SL = mp − gap, round 0.005.
- Defaults: TS_PROFIT_MULTIPLIER 5.21847, RATE_PROFIT_STOP_MARKET 0.05(live)/0.03(code), TS_DYNAMIC_K 0.29774,
  TS_GIVEBACK_RATIO 0.5, TS_MAX_GAP 0.08, TS_MAX_GAP_WEAK 0.03, TS_WEAK_MOMENTUM_THRES 0.004.

## Phân tích 2881 entry thật (entry_paths + entry_pathstats maxFav + wfo_gate_pred)
### 1. ARM 26% QUÁ CAO — 84% lệnh không bao giờ arm
- maxProfit đỉnh 24h: median 11.5%, p90 33%. Chỉ **16% lệnh chạm arm 26%** → 84% trailing KHÔNG kích hoạt.
- arm 10% → 57% arm; 15% → 38%; 20% → 25%. → arm là lever chính, đang quá cao.
### 2. TS_DYNAMIC_K = code chết
- pred15m entry: median 0.022, max 0.111. pred×0.29774 max 0.033 < base 0.05 → arm LUÔN = mult×base. Bỏ K.
### 3. Weak-gap không trigger tại entry (pred<0.004 = 0%; gate yêu cầu pred≥0.008). Chỉ strong branch.
### 4. Gap: maxProfit median 11.5% → gap phần lớn = mp×0.5 (chưa cap); chỉ 35% (đỉnh>16%) cap 0.08.
### Hold tới đỉnh: median 735min(12h), p90 1410min(23h) → path cần ~24h/entry.

## Lưới sweep chốt
- arm hiệu dụng (mult×base): {5, 7.5, 10, 12.5, 15, 20, 26}% (nghi tối ưu 10–15%).
- TS_GIVEBACK_RATIO: {0.3, 0.5, 0.7}. TS_MAX_GAP: {0.05, 0.08, 0.12}.

## Bước tiếp: compute 5-min-high (chưa build)
Per entry: path 5m-high (Binance klines ~288 bar/24h) → replay trailing (arm→trail gap) → P&L → sweep lưới.
5m lấy high xấp xỉ live 10s-loop-takes-high. Không cần backtest đầy đủ. Nguồn entry+pred có sẵn.
Files: entry_paths.csv, entry_pathstats_g008.csv, wfo_gate_pred.csv (Oracle claudedata).
