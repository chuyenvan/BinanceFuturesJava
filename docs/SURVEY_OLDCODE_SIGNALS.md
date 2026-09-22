# SURVEY — Tín hiệu era BIG_DOWN (code cũ ~2025-09/10) vs T170 hiện tại

Agent: SURVEY/RECON (0-sim, read-only). Nguồn: repo mounted local (remote `oracle`),
branch `module`, đọc bằng `git show/log/grep`. SSH Oracle KHÔNG dùng được (VM báo
`Network is unreachable` port 22 + key không có trên VM) → fallback mounted theo đúng runbook.
Neo lịch sử: `157cf4d` (2025-10-08). Mục tiêu: tìm trigger KHÁC cơ chế MOM15, fire khi MOM15 im,
để tăng số cược ĐỘC LẬP (n_eff) cho T170.

## 1. Thời BIG_DOWN ra đời + file detector era đó
- Enum chứa BIG_DOWN: `src/main/java/com/binance/chuyennd/bigchange/market/MarketLevelChange.java`
  (era 157cf4d). File này xuất hiện dạng hiện tại tại commit `d484bff` (2025-09-28, "chuẩn hóa
  lại thư mục code src/main/java" — reorg; concept BIG_DOWN có trước reorg).
- Detector lõi tính tín hiệu: `src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java`
  (first-add `62439ce`, 2025-10-02).
- Entry detector live: `src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java`.
- Phụ trợ: `TrendDetector` (SMA gate), `FundingFeeManagerProduction`, `DcaProcessor/DcaUtils`, `TradeUtils`.

### Sự thật quan trọng về đầu vào (MarketBigChangeDetector.calMarketData / getMarketStatus1M)
TẤT CẢ các "market level" được suy từ đúng 4 scalar cross-sectional:
- `rateDownAvg`  = avg(close/open) của ~100 symbol giảm mạnh nhất (nến 1M) — breadth kẻ thua.
- `rateUpAvg`    = avg(close/open) của ~100 symbol tăng mạnh nhất — breadth kẻ thắng.
- `btcRateChange`= close/open BTC (1M).
- `rateDown15MAvg`= avg( close / max(15×1M) ) của ~100 symbol — sụt so với đỉnh 15 phút.
  `NUMBER_TICKER_CAL_RATE_CHANGE=15` ⇒ "15M" = 15 nến 1M. **Đây chính là lõi MOM15.**

## 2. Bảng MỌI tín hiệu era 157cf4d (ngoài MOM15 & BD) + logic THẬT + phân loại

Ký hiệu: TF=timeframe; T170=còn dùng trong HEAD?; Indep=độc lập MOM15?; Data=data offline
backtest; Causal=causal-safe; Prior=prior plausibility.

| Tín hiệu | Cơ chế THẬT (từ code) | TF | T170 hiện tại | Indep MOM15? | Data | Causal | Prior |
|---|---|---|---|---|---|---|---|
| BIG_UP | rateUpAvg>0.025 | 1M x-sec | Còn (enum) | Khác chiều nhưng vẫn momentum breadth; chủ yếu để chặn/đảo, entry buy-dip lạ | 1M ticker (Aerospike) | Có | Yếu |
| MEDIUM_UP | rateUpAvg>0.015 | 1M | BỎ | Như trên | 1M | Có | Yếu |
| SMALL_UP | rateUpAvg>0.008 & rateDownAvg>0 | 1M | Còn | Momentum-up, đợt khác crash nhưng vẫn momentum | 1M | Có | Yếu |
| MEDIUM_DOWN | rateDownAvg<-0.030 OR (rateDownAvg<-0.014 & rateDown15MAvg<-0.07) | 1M | Còn | KHÔNG — cùng đợt/cùng chiều selloff với MOM15 | 1M | Có | (đã dùng) |
| SMALL_DOWN | rateDownAvg<-0.006 & rateUpAvg<0 & rateDown15MAvg<-0.025 | 1M | BỎ | KHÔNG — biến thể breadth-down, dính rateDown15M | 1M | Có | (đã dùng) |
| MEDIUM_DOWN_15M | rateDown15MAvg<-0.045 | 15M | BỎ | = MOM15 (bản medium) | 1M | Có | (đã dùng) |
| SMALL_DOWN_15M | rateDown15MAvg<-0.028 | 15M | Còn (=MOM15 live) | = MOM15 | 1M | Có | (đã dùng) |
| DCA_LEVEL1/2/3 | quản trị vị thế theo callMargin/rateLoss (isDcaAlt: rateDown15MAvg<-0.035 OR rateUpAvg>0.01 OR rateDownAvg<-0.01) | 1M | LEVEL1 còn | KHÔNG — không phải cược mới độc lập, là nạp thêm vào vị thế correlated | 1M | Có | n/a |
| BTC_TREND_REVERSE | isBtcTrendReverse: sau khi giá tụt >=rateTrend so với đỉnh 15m/30m (mốc minute%15==14), giá HIỆN bật LÊN qua priceReverse ⇒ long bounce/đảo chiều; chỉ `specialSymbol` | 15m-align/1M | BỎ (không còn enum/wiring) | CÓ (về timing/chiều — fire lúc đảo lên, MOM15 fire lúc đang rơi) | 1M closes (Aerospike) | Có | Trung bình |
| FUNDING_FEE_BUY | isFundingFeeTrade (gate momentum permissive) × chọn symbol từ FundingFeeManager.fundingBuy (funding rate rất âm/qua ngưỡng) | funding 8h + 1M | BỎ khỏi Java; ĐÃ chuyển sang ML `funding_selector` | Một phần (chọn symbol theo funding ~ orthogonal) nhưng gate timing dính momentum | funding history + 1M | Có | ĐÃ ĐO → FAIL |
| FUNDING_FEE_BUY_SPECIAL | extremeNegative funding + isSellingExhausted (capitulation) | funding+1M | BỎ | Có (idiosyncratic) nhưng đã bị FORCED_SELLER/funding-ML thay | funding+1M | Có | trùng lặp |
| isSellingExhausted (helper) | 20 nến 1M: >=70% nến đỏ & sụt >=4.5% so đỉnh chuỗi & volume nến cuối < 0.6× avg volume nến đỏ (lực bán cạn) | 1M | BỎ khỏi live | CÓ (timing: cuối đợt bán, khác đỉnh momentum) | 1M OHLCV+volume(totalUsdt) | Có | trùng FORCED_SELLER |
| SMA_SIGNAL / RSI_SIGNAL | enum tồn tại nhưng KHÔNG có producer nào (dead enum) | — | BỎ | n/a — chưa từng wired | — | — | n/a |
| ORDER_PROFIT | nhãn exit/chốt lời, không phải entry | — | Còn | n/a (exit) | — | — | n/a |
| BTC_TREND (TrendDetector) | isBtc/EthTrendBuyProduction: SMA7 vs SMA100 trên 1D VÀ 4H, OR (TÊN GÂY NHẦM) | 1D+4H | Còn (gate) | KHÔNG phải trigger entry — chỉ là gate budget/limit | 1D/4H closes | Có | n/a (gate) |

## 3. Xếp hạng theo ƯU TIÊN ĐỘC LẬP MOM15
1. **Reversal-bounce (BTC_TREND_REVERSE, tổng quát hóa)** — độc lập TIMING/CHIỀU rõ nhất trong
   nhóm chưa-đo-lại; data 1M sẵn; causal-safe; prior trung bình.
2. Volume-dry-up capitulation (isSellingExhausted) — độc lập timing nhưng TRÙNG với FORCED_SELLER
   đang chạy sim.
3. Funding cross-section — độc lập symbol nhưng ĐÃ ĐO (WFO leakfree v2 = FAIL/REVIEW, WFE med 0.098).
4-…: down-breadth family (MEDIUM_DOWN/SMALL_DOWN/MEDIUM_DOWN_15M), up-momentum, DCA — loại (xem §4).

## 4. LOẠI THẲNG + lý do
- **MEDIUM_DOWN, SMALL_DOWN, MEDIUM_DOWN_15M**: bản chất là breadth-down/MOM15 biến thể, fire CÙNG
  đợt & CÙNG chiều selloff ⇒ correlated MOM15, không thêm n_eff. (Đúng hướng breadth đã đóng.)
- **BIG_UP/MEDIUM_UP/SMALL_UP**: momentum-up breadth, prior yếu cho long-buy-dip, chủ yếu vai trò gate.
- **DCA_LEVEL1/2/3 + isDcaAlt**: nạp thêm vào vị thế đang có → không phải cược độc lập.
- **SMA_SIGNAL, RSI_SIGNAL**: dead enum, không có logic ⇒ không có gì để đo.
- **TrendDetector (SMA7/SMA100 1D+4H OR)**: là GATE, không phải trigger entry. Tên gây nhầm (đã rõ).
- **FUNDING_FEE_BUY(_SPECIAL)**: ĐÃ chuyển ML funding_selector + ĐÃ đo WFO (FAIL/REVIEW). Không "mới".
- **ORDER_PROFIT**: nhãn exit.

## 5. SHORTLIST (1 GO + 1 điều kiện)

### GO — Reversal-bounce long (tổng quát hóa isBtcTrendReverse)
- Cơ chế: sau một chân giảm (giá tụt >= ngưỡng so đỉnh 15m/30m), long khi giá bật lên vượt mốc
  đáy-đảo. Fire ở PHA ĐẢO LÊN — đúng lúc MOM15 (đang-rơi) im/tắt.
- Vì sao GO: (a) độc lập timing+chiều rõ nhất trong các lead CHƯA đo lại; (b) data 1M closes có sẵn
  trong Aerospike/WFO dataset (cùng nguồn BD/MOM15); (c) causal-safe (mốc 15m-aligned, chỉ nhìn nến
  đã đóng quá khứ + close hiện tại; không lookahead); (d) prior trung bình (mean-reversion bounce
  ngắn hạn có cơ sở).
- CAVEAT TRUNG THỰC (bắt buộc kiểm khi đo): tuy độc lập về PHA, các cược này vẫn CỤM quanh CÙNG
  các đợt selloff mà MOM15 giao dịch ⇒ ICC theo EPISODE có thể chỉ giảm VỪA, không về ~0. Phải đo
  ICC/overlap thời gian với MOM15 trước khi tin là "độc lập thật".
- Khung đo edge đề xuất (tầng xếp-hạng TIẾP THEO, chưa làm ở task này):
  1) Định nghĩa trigger tham số hóa (ngưỡng tụt, cửa sổ 15/30m, ngưỡng bật lên, universe: mở rộng
     từ specialSymbol → cross-section symbol bật off local low).
  2) Sinh chuỗi tín hiệu trên WFO dataset leak-free, HOLD cố định (vd 24h như FORCED_SELLER) để
     so sánh táo-với-táo.
  3) Đo: hit-rate/expectancy OOS, VÀ quan trọng nhất **overlap-in-time & ICC với MOM15** (điều kiện
     tiên quyết): nếu ngày fire ≈ trùng MOM15 ⇒ NO-GO dù edge dương.
  4) Gate GO tầng sau: edge OOS>0 sau phí + ICC-với-MOM15 đủ thấp (fire ở ngày MOM15 im) +
     causal-safe khẳng định trên harness.

### ĐIỀU KIỆN (NO-GO standalone / GO chỉ dạng feature) — Volume-dry-up capitulation
- Từ isSellingExhausted: micro-feature "volume nến cuối < 0.6× avg volume nến đỏ" (lực bán cạn).
- NO-GO như alpha độc lập: TRÙNG khái niệm với FORCED_SELLER (mean-reversion sau forced selling,
  3σ/30d + ML selector) ĐANG chạy sim. Thêm một dòng cược cùng họ = correlated với FORCED_SELLER,
  không với MOM15 thì có nhưng dẫm chân nhánh đang làm.
- GO hẹp: đề xuất như 1 FEATURE bổ sung cho selector FORCED_SELLER/PREDICT (lọc volume-dry-up),
  không phải luồng cược mới.

## Kết luận trung thực
Phần lớn "tín hiệu độc lập" của code cũ ĐÃ được thu hoạch: funding→ML funding_selector (đã đo, FAIL),
capitulation→FORCED_SELLER (đang sim). Nhóm down-breadth = correlated MOM15 (không tính). Lead
CHƯA-đo-lại và độc-lập-nhất còn lại là **reversal-bounce (BTC_TREND_REVERSE tổng quát)** — đáng đo
edge ở tầng sau, NHƯNG với cảnh báo ICC-theo-episode: có thể vẫn cụm quanh cùng đợt selloff MOM15;
phải đo overlap trước khi coi là cược độc lập thật.
