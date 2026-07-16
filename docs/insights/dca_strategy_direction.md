# Hướng model/chiến lược riêng cho tầng DCA (nhồi lệnh)

> Ngày: 2026-07-16 · Task3c · Design doc (KHÔNG sửa code, KHÔNG commit)
> Bot: crypto futures **long-only, DCA/martingale, 1x, không hard-stop, trailing exit**.

## 0. TL;DR — khuyến nghị chốt

- **Bài học chốt (đừng lặp lại):** DCA/mean-reversion đứng riêng có **ZERO edge độc lập**
  (`docs/reports/dca_primary_20260711.md`: DCA-only CAGR −0.01%, 1/22 quý dương). DCA chỉ là
  **cơ chế nuôi vốn (capital-feeding)** cho các lệnh do PST (pump selector) mở. Vì vậy mọi hướng mới
  phải coi DCA là **một lớp CÓ ĐIỀU KIỆN / được GATE**, không phải sleeve độc lập.
- **Ưu tiên #1 đề xuất:** **Hướng (b) — DCA thích ứng regime/volatility + TRẦN MARGIN ĐỘNG chống
  capital-lock.** Đây là hướng rẻ nhất, đánh trúng thứ đang thực sự làm hỏng nhiều window OOS
  (`TOO_MUCH_CAPITAL_LOCK`), và không cần train model mới ngay.
- Hướng (a) gate-by-model và (c) tier-coin là bước 2/3, làm sau khi (b) đã ổn định.

---

## 1. Cơ chế DCA hiện tại (chính xác từ code)

### 1.1 Các file lõi
- `src/main/java/com/binance/chuyennd/tradecore/DcaProcessor.java` — `getDCA(...)` (sim) và
  `getDCAProduction(...)` (live): duyệt các lệnh đang chạy, lọc bằng `DcaUtils.shouldDca`, trả về
  danh sách symbol cần nhồi.
- `src/main/java/com/binance/chuyennd/tradecore/DcaUtils.java` — **logic quyết định lõi** `shouldDca`.
- `src/main/java/com/binance/chuyennd/tradecore/Configs.java` — gene DCA_* (mục "8. NGƯỠNG BÁO ĐỘNG & DCA").
- `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java` — điểm GỌI DCA (~L210-243).
- `src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java` — `isDcaAlt(...)` (~L201).

### 1.2 `DcaUtils.shouldDca` — điều kiện nhồi (chính xác)

Chữ ký: `shouldDca(Float margin, float currentRateLoss, MarketLevelChange orderMarketLevel,
long orderTimeStart, MarketLevelChange marketLevelChange, long currentTime, float budget)`.

Luồng quyết định:
1. `getDcaConfig(marketLevelChange)` chọn cấu hình theo **market level chung** hiện tại:
   - `BIG_DOWN` → `DcaConfig(DCA_TIME_BIG_DOWN=8', DCA_LOSS_BIG_DOWN=−0.15, isAll=TRUE)`
   - `BIG_UP` → **null** khi `OFF_FLAT_HARD=true` (nhánh BIG_UP đã tắt cứng — thuộc cụm gene phẳng);
     nếu bật lại: `DcaConfig(DCA_TIME_BIG_Up=15', DCA_LOSS_BIG_UP=−0.25, isAll=false)`
   - `null` (nhánh isDcaAlt) → `DcaConfig(durationDca=1', rateLoss=−0.4, isAll=FALSE)` ← **de-escalating ladder**
   - còn lại → null (không nhồi)
2. `null` config hoặc `margin==null` → không nhồi.
3. `adjustedRateLoss = calculateAdjustedRateLoss(margin, budget, baseRateLoss, isAll)`:
   - Nếu `isAll` HOẶC `margin < budget` → **giữ nguyên ngưỡng gốc** (baseRateLoss).
   - Ngược lại theo `marginRatio = margin/budget`: ≥3.0→−0.99; ≥2.5→−0.9; ≥2.0→−0.7; ≥1.5→−0.6; else −0.4.
     (Cụm càng nặng vốn thì ngưỡng nhồi càng SÂU → giãn nhồi khi đã ôm nhiều.)
4. Chỉ nhồi khi **lỗ đủ sâu**: `currentRateLoss < adjustedRateLoss`
   (`currentRateLoss = (lastPrice − avgEntry)/avgEntry`, số âm).
5. Điều kiện thời gian `isTimeConditionMet`: nếu leg đang xét là `DCA_LEVEL1` thì phải
   `currentTime > orderTimeStart + durationDca*phút` (giãn cách từ leg gần nhất); level khác → true.

### 1.3 Hai đường GỌI DCA trong Simulator (~L210-243)
- **Path A — theo market level:** `symbolDcaLevel = DcaProcessor.getDCA(levelChange, time, budget, activeOrderMap)`
  → mỗi symbol trả về gọi `createOrderBUY(..., MarketLevelChange.DCA_LEVEL1, ...)`.
  Khi `levelChange==BIG_DOWN`: `isAll=TRUE` ⇒ **ngưỡng nhồi GIỮ CỨNG −0.15 bất kể đã nhồi bao nhiêu leg**.
- **Path B — isDcaAlt (alt panic):** nếu `MarketBigChangeDetector.isDcaAlt(rateDown15MAvg, rateDownAvg, rateUpAvg)`
  = `rateDown15MAvg < MS_DOWN_BIG_AVG (−0.03157) || rateDownAvg < MS_DOWN_BIG_AVG/3` → true,
  thì `getDCA(null, ...)` (config default −0.4, isAll=false) → nhồi khi lỗ sâu theo ladder ở (3).

### 1.4 Gene DCA_* (Configs.java §8)
| Gene | Giá trị hiện tại | Vai trò |
|---|---|---|
| `DCA_TIME_BIG_DOWN` | 8 (phút) | giãn cách nhồi khi BIG_DOWN |
| `DCA_LOSS_BIG_DOWN` | −0.15 | ngưỡng lỗ để nhồi khi BIG_DOWN (isAll ⇒ cố định) |
| `DCA_TIME_BIG_Up` | 15 (phút) | giãn cách nhồi khi BIG_UP (đang OFF cứng) |
| `DCA_LOSS_BIG_UP` | −0.25 | ngưỡng nhồi BIG_UP (gene cụm phẳng, NO-HPO, OFF cứng) |
| `MS_DOWN_BIG_AVG` | −0.03157 | ngưỡng nhận diện alt-panic cho `isDcaAlt` |

### 1.5 Tương tác budget / margin / sizing
- **Sizing giảm dần (de-escalating):** leg sau nhỏ hơn leg trước — vốn co lại khi margin tăng
  (`TradeUtils.managerBudget`: base / DIVIDER theo marginRatio, `× tierMultiplier` từ CoinRankManager).
  ⇒ 1 cụm nhồi liên tục chốt cứng ~99% budget của cụm; "ruin" ràng buộc bởi SỐ LẦN nhồi.
- **Circuit breaker (Configs §7, mặc định BẬT):** `BREAKER_MODE=MARGIN`, `BREAKER_MARGIN_HALT=0.50`
  → **chặn MỞ MỚI** (kể cả leg DCA mới) khi `marginRunning/balanceBasic ≥ 0.50`. KHÔNG force-close (long-only).
  - Đã thử & GỠ: cap %vốn/cụm + cap số leg + cap DD-vs-first-leg → trên danh mục veto chỉ 0–8 lần (vô dụng
    vì budget phân tán qua hàng trăm cụm nhỏ, không cụm nào chạm 5–10% tổng vốn). "Lá chắn thật" là trần
    margin TỔNG (`BREAKER_MARGIN_HALT`), không phải cap per-cluster. LUNA 1-coin cứu được chỉ vì cô lập.
  - `BREAKER_CLUSTER_DD_MAX=−0.30` đã bị **vô hiệu cấu trúc** (ADR-0008) và chỉ dùng khi MODE=DCA/BOTH.

---

## 2. Rủi ro của DCA hiện tại

### 2.1 Martingale → maxDD
- Long-only + không hard-stop + nhồi khi lỗ ⇒ mỗi cụm là một martingale. Với `BIG_DOWN isAll=TRUE`,
  ngưỡng nhồi GIỮ −0.15 suốt đường xuống → nhồi mỗi −15% cho tới khi hết budget cụm. Với coin về 0
  (LUNA 2022) đây là kịch bản ruin — chỉ được cứu khi cô lập 1 coin, KHÔNG đại diện danh mục.

### 2.2 Capital-lock — thứ ĐANG làm hỏng nhiều window OOS
- `HPOFitnessCalculatorV4` có constraint cứng: nếu `pctHeldOver7d > MAX_PCT_HELD_OVER_7D (0.02)`
  → **loại genome**, `note=TOO_MUCH_CAPITAL_LOCK`.
  - `pctHeldOver7d = (#lệnh giữ > HELD_TOO_LONG=7 ngày) / tradeCount`. Chỉ cần >2% số lệnh kẹt quá 7 ngày.
- Cơ chế gây kẹt: DCA nhồi liên tục vào cụm lỗ → avgEntry trôi xuống nhưng trailing exit không kích được
  vì giá không hồi đủ → cụm ôm vốn dài ngày → nhiều window WFO bị `TOO_MUCH_CAPITAL_LOCK` (thấy trong
  `notebooklm_ready/reports_merged.txt`, xen kẽ với `ZERO_TRADES`/`TOO_FEW_TRADES`).
- **Đây là nút thắt chính:** vốn kẹt trong cụm không-hồi ⇒ không mở được lệnh mới ⇒ window OOS chết
  hoặc quá ít lệnh. Không phải maxDD trực tiếp, mà là **cơ hội bị khóa**.

### 2.3 Bài học nền — không có edge độc lập
`docs/reports/dca_primary_20260711.md` (§2, 2026-07-11): tắt PST, chạy DCA-only → CAGR ≈ 0, 1/22 quý
dương. +5295 mà DCA "kiếm" trước đây thực chất là "lãi của việc bình quân giá vào lệnh PUMP đã mở", KHÔNG
phải edge mean-reversion. ⇒ **DCA và PST không độc lập; DCA nuôi PST.** Kết luận vận hành cho task này:
mọi cải tiến DCA phải đo bằng **đóng góp CẬN BIÊN lên hệ full (PST bật)**, tuyệt đối không đo DCA standalone.

---

## 3. Ba hướng để DCA THỰC SỰ tạo giá trị (DCA = lớp có gate, không standalone)

Nguyên tắc chung: DCA không tự sinh alpha; giá trị của nó = **cải thiện chất lượng entry trung bình của
các cụm PST CÓ KHẢ NĂNG HỒI, đồng thời cắt việc nhồi vào cụm sẽ KHÔNG hồi** (nguồn của capital-lock + tail-DD).

### Hướng (a) — DCA có GATE bằng model xác suất hồi (rescue-probability gate)
**Ý tưởng:** thay vì luôn nhồi khi `currentRateLoss < ngưỡng`, thêm một cổng: chỉ nhồi khi
model ước lượng **P(cụm hồi về hòa/lãi trong H giờ) ≥ τ**. Nhồi vào cụm "sẽ hồi", NGỪNG nhồi cụm "sẽ chết".

- **Feature (tại thời điểm cân nhắc nhồi, KHÔNG leak tương lai):** độ sâu lỗ hiện tại (`currentRateLoss`),
  số leg đã nhồi + tuổi cụm, `marginRatio = margin/budget`, market level (BIG_DOWN/isDcaAlt), biến động
  gần đây (ATR/realized vol 15m-4h), rateDown15MAvg/rateDownAvg/rateUpAvg (đã có sẵn), funding, và
  tier coin (CoinRankManager). Có thể tái dùng feature pipeline PST hiện có.
- **Label (leak-free, cắt theo mốc thời gian):** trong H giờ kế tiếp cụm có chạm điểm trailing-exit
  hòa/lãi không? (binary rescued/not). Hoặc regression: MFE (max favorable excursion) trong H giờ.
- **Train:** gradient boosting / logistic; time-based split (KHÔNG shuffle). Threshold τ chọn để tối đa
  đóng góp cận biên lên fitness V4.1 của hệ full, không tối đa accuracy của model.
- **Validate:** cắm gate vào `shouldDca` (thêm 1 điều kiện AND), chạy **WFO trên hệ full (PST bật)**;
  so `TOO_MUCH_CAPITAL_LOCK`, %OOS-dương, calmar với baseline. τ là gene HPO.
- **Rủi ro:** (1) model = một PST thứ hai đội lốt → phải kiểm tính độc lập đóng góp (ablation A/B/C như
  `ABLATION_MODE`); (2) leak nếu label dùng giá tương lai sai mốc; (3) thêm 1 bộ não cần parity live/sim.

### Hướng (b) — DCA thích ứng regime/volatility + TRẦN MARGIN ĐỘNG (ƯU TIÊN)
**Ý tưởng:** không cần model ML. Biến ngưỡng/giãn/trần thành hàm của **regime + volatility**, và thêm
**trần margin ĐỘNG per-regime** để chặn nhồi khi thị trường đang panic sâu (nơi capital-lock sinh ra).

- **Điểm đau cần sửa trực tiếp:** `BIG_DOWN isAll=TRUE` giữ ngưỡng −0.15 CỐ ĐỊNH → nhồi vô hạn xuống đáy.
  Đề xuất: khi BIG_DOWN/alt-panic, **tắt isAll** (cho ladder de-escalating chạy) hoặc thêm bậc thang sâu
  dần theo số leg / theo realized-vol (vol cao → ngưỡng sâu hơn, giãn lâu hơn, budget leg nhỏ hơn).
- **Trần margin động:** `BREAKER_MARGIN_HALT` hiện là hằng 0.50. Cho nó **thấp hơn khi regime = BIG_DOWN/
  alt-panic** (vd 0.30-0.40) để ngừng nhồi sớm trong sập sâu, và giữ/cao hơn khi thị trường bình thường.
  Đây là đòn trực tiếp vào `TOO_MUCH_CAPITAL_LOCK` mà không đụng cấu trúc per-cluster đã chứng minh vô dụng.
- **Feature/label:** không cần label ML. "Regime" = market level sẵn có + realized vol; tối ưu tham số
  bằng HPO/WFO như các gene khác.
- **Validate:** thêm 2-3 gene (vd `DCA_BIG_DOWN_ISALL_OFF`, `BREAKER_MARGIN_HALT_PANIC`, `DCA_VOL_SCALE`),
  đưa vào GENOME, chạy WFO full. Mục tiêu: giảm % window `TOO_MUCH_CAPITAL_LOCK`, giữ hoặc tăng calmar OOS.
- **Rủi ro:** nhồi ít hơn → có thể giảm PnL cụm hồi được (đánh đổi PnL↓ lấy DD/lock↓, giống lần chốt
  MARGIN 0.50 đã chấp nhận PnL −27% để maxDD −58.6%→−29.5%). Cần đo đánh đổi trên bậc thang OOS.

### Hướng (c) — DCA theo TIER coin
**Ý tưởng:** phân biệt được-nhồi theo chất lượng coin. Live đã có mầm mống: `DetectEntrySignal2TradeNormal`
(~L484-492) "Chặn DCA vào đồng Shitcoin" gated trên `DCA_LEVEL1` + `CoinRankManager` tier
(hệ số 1.2 | 1.0 | 0.5). Nhồi mạnh vào tier cao (thanh khoản/mean-revert đáng tin), cấm/nhồi nhẹ tier thấp
(nơi coin-về-0 và không hồi → nguồn capital-lock + tail-DD lớn nhất).

- **Feature/label:** tier tĩnh có sẵn (`ExportCoinTierStatic` + `WFO_COINTIER_FILE`, leak-free per-interval).
  Nhãn (nếu muốn học lại tiering thay vì rank thanh khoản): P(coin không về 0 / hồi sau panic) theo tier.
- **Train:** thường KHÔNG cần ML — chỉ cần chính sách theo tier (multiplier ngưỡng/budget/số-leg per tier)
  + tối ưu bằng HPO. Nếu muốn ML thì train classifier "coin sẽ hồi vs sẽ chết" trên feature thanh
  khoản/tuổi/market-cap-proxy.
- **Validate:** đảm bảo `CoinRankManager` được nạp đúng trong WFO (`WFO_STATIC_RANK`/`loadStaticTier`);
  quét chính sách tier trên WFO full; so tail-DD + capital-lock giữa các mức chặn tier.
- **Rủi ro:** tier tĩnh có thể lệch survivorship (coin từng top rồi chết); cần tier tính leak-free theo
  thời điểm quá khứ (ExportCoinTierStatic đã đi đúng đường live). Chặn tier thấp có thể giảm số lệnh → chạm
  `TOO_FEW_TRADES`.

---

## 4. Khuyến nghị ưu tiên + validate-small-first

**Chốt ưu tiên: (b) trước → (c) → (a).** Lý do: (b) rẻ nhất (không model), đánh trực diện capital-lock —
thứ đang hỏng nhiều window OOS — và có thể tái dùng cơ chế breaker + HPO sẵn có; (c) tận dụng hạ tầng tier
đã có; (a) đắt nhất (cần model + parity live/sim + kiểm độc lập) nên làm sau khi (b)/(c) đã dựng baseline sạch.

### Bước nhỏ, validate-small-first (mỗi bước 1 thay đổi, đo trên hệ FULL — PST bật)
1. **Đo baseline capital-lock:** chạy WFO hiện trạng, ghi lại per-window `oosNote`, đặc biệt đếm
   `TOO_MUCH_CAPITAL_LOCK` và `pctHeldOver7d`, cùng distribution tuổi-cụm. Đây là số đối chứng.
2. **Thử nghiệm cô lập cơ chế `isAll` (b-1):** thêm 1 gene bật/tắt `isAll` cho BIG_DOWN (mặc định giữ hành
   vi cũ = OFF). Chạy 1-2 window đại diện (1 bull, 1 bear/panic) TRƯỚC, xem hướng `pctHeldOver7d` + calmar.
3. **Trần margin động theo regime (b-2):** nếu (2) có dấu hiệu tốt, thêm `BREAKER_MARGIN_HALT_PANIC`
   (áp khi BIG_DOWN/isDcaAlt). Quét 0.30–0.50 trên vài window trước khi full WFO.
4. **Chỉ khi (b) giảm được % window capital-lock mà không sập số lệnh** → mở rộng full WFO, rồi mới sang (c).
5. **Cổng dừng (pre-register):** nếu (b)+(c) không kéo được % window `TOO_MUCH_CAPITAL_LOCK` xuống mà vẫn
   giữ ≥ baseline về calmar/%OOS-dương → không theo (a) vội; ghi nhận và quay lại cải thiện PST (§1 roadmap).

### Nhấn mạnh chống capital-lock (ràng buộc thiết kế xuyên suốt)
- Mọi thay đổi DCA phải **giảm hoặc giữ nguyên** `pctHeldOver7d` (ngưỡng loại 0.02). Nếu một cải tiến tăng
  PnL nhưng đẩy `pctHeldOver7d` qua ngưỡng → genome bị loại, coi như thất bại.
- Cơ chế chống lock hiệu quả đã kiểm chứng = **trần margin TỔNG** (không phải cap per-cluster). Hướng (b)
  đi tiếp đúng trục đó bằng cách làm trần margin **nhạy regime**.
- Không đo DCA standalone. Chỉ đo **đóng góp cận biên trên hệ full**, dùng ablation A/B/C để tránh lặp lại
  cú nhầm attribution 2026-07-11.

---
_Tham chiếu: `DcaUtils.java`, `DcaProcessor.java`, `Configs.java` §7-§8, `SimulatorMarketLevelTicker1MStopLoss.java`
(~L210-243), `MarketBigChangeDetector.isDcaAlt`, `HPOFitnessCalculatorV4` (MAX_PCT_HELD_OVER_7D),
`docs/reports/dca_primary_20260711.md`, `docs/SOLUTION_FRAMEWORK_20260711.md`, `tasks/006.1-dca-scenario-luna.md`._
