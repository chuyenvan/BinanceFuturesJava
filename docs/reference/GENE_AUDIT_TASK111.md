# RÀ GENE THEO BACKTEST THẬT — TASK-111 (rà 2026-06-25 đêm, để Uni duyệt sáng 26)

> 📌BẢN ĐỒ GENE 6 TẦNG (reference). Genome **CHỐT** đã sang [ADR-0012](../decisions/0012-genome-18-gene-off-cung-cum-C.md)
> (18 gene + OFF cứng 9 gene cụm C). File này giữ làm **bản đồ tra cứu tham số→tầng→vai-trò**; giá trị Configs trích ở đây là SNAPSHOT @2026-06-25 (có thể cũ) — KHÔNG dùng làm nguồn sự thật cho số.

> **Cách rà:** đọc THẲNG engine backtest `SimulatorMarketLevelTicker1MStopLoss` + các lớp nó GỌI THẬT khi
> chạy (`AIRejectFilter`, `TradeUtils.managerBudget`, `DcaUtils.shouldDca`, `OrderTargetInfoTest.updateTPSL/updateStatusNew`,
> `MarketBigChangeDetector.getMarketStatus1M`, `CoinRankManager`). KHÔNG rà theo code HPO (Uni xác nhận HPO code
> hiện toàn rác + phân mảnh: `RunOptimizationCombined`=12 gene, `RunHpoMaster_Distributed`=bộ khác,
> `WFOTier1/2/3`=comment chết hết). Đây là tham số THẬT điều khiển hành vi backtest, theo luồng chuẩn.

---

## A. BẢN ĐỒ THAM SỐ THẬT theo TẦNG (Configs engine đọc khi chạy)

### Tầng 1 — ENTRY FILTER (AIRejectFilter.checkSignal / checkSignalDynamic)
| Config | Giá trị hiện tại | Vai trò | Trong HPO cũ? |
|---|---|---|---|
| `FILTER_MODE` | "A" | chọn nhánh filter (mode) | không (categorical) |
| `MIN_MOMENTUM_15M` | 0.02284 | sàn momentum 15m để PASS | có (gene 7 Combined) |
| `HARD_RISK_LIMIT_4H` | -0.2 | trần rủi ro 4h (predRisk) reject | có (gene 4) |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | 0.15 | ngưỡng cắt điểm classifier (P_fail) | có (gene 3) ⚠️ ĐÂY là gene bị đảo-dấu khi đổi sang selector |
| `AI_DYNAMIC_MULTIPLIER` | 1.28760 | hệ số nhân ngưỡng động | một phần |
| `AI_DYNAMIC_MIN` | 0.26787 | sàn ngưỡng động | một phần |
| `AI_DYNAMIC_MAX` | 2.14135 | trần ngưỡng động | một phần |

### Tầng 2 — MARKET STATUS DETECT (MarketBigChangeDetector.getMarketStatus1M → sinh BIG_DOWN/SMALL/BIG_UP)
| Config | Giá trị | Vai trò |
|---|---|---|
| `MS_UP_BIG_THRES` | 0.02046 | ngưỡng BIG_UP |
| `MS_DOWN_BIG_AVG` | -0.03157 | ngưỡng BIG_DOWN (và /3 cho isDcaAlt) |
| `MS_UP_SMALL_THRES` | 0.00442 | ngưỡng SMALL_UP |
| `MS_DOWN_SMALL_AVG_OR_15M` | -0.02069 | ngưỡng SMALL_DOWN |
| `PREDICT_SYMBOL_RATE_DOWN_15M` | -0.03234 | ngưỡng tín hiệu vào (PREDICT_SYMBOL_TRADE) |
| `PREDICT_SYMBOL_RATE_UP_AVG` | 0.00454 | nt |
| `PREDICT_SYMBOL_RATE_DOWN_AVG` | -0.00503 | nt |

### Tầng 3 — DCA NHỒI LỆNH (DcaUtils.shouldDca + getDcaConfig)
| Config | Giá trị | Vai trò |
|---|---|---|
| `DCA_TIME_BIG_DOWN` | 8 (phút) | giãn cách nhồi khi BIG_DOWN |
| `DCA_LOSS_BIG_DOWN` | -0.15 | ngưỡng lỗ để nhồi BIG_DOWN |
| `DCA_TIME_BIG_Up` | 15 | giãn cách nhồi BIG_UP |
| `DCA_LOSS_BIG_UP` | -0.25 | ngưỡng lỗ nhồi BIG_UP |
| **HARDCODE chưa gene** (DcaUtils.calculateAdjustedRateLoss): | | **DCA margin ladder** |
| marginRatio≥3.0 → -0.99 | hardcode | nhồi sâu hơn khi margin lớn |
| ≥2.5 → -0.9, ≥2.0 → -0.7, ≥1.5 → -0.6, else -0.4 | hardcode | (4 bậc — chính là phần WFOTier2 chết định tối ưu) |

### Tầng 4 — TRAILING EXIT / CHỐT LỜI (OrderTargetInfoTest.updateTPSL + TradeUtils.calRateLossDynamicBuy / calRateMinWith...)
| Config | Giá trị | Vai trò |
|---|---|---|
| `RATE_PROFIT_STOP_MARKET` | 0.01032 | ngưỡng lãi tối thiểu để bắt đầu dời SL (base) |
| `TS_PROFIT_MULTIPLIER` | 5.21847 | hệ số kích hoạt trailing |
| `TS_DYNAMIC_K` | 0.29774 | hệ số nhân volatility để dời SL |
| `TS_MAX_GAP` | 0.08 | gap trailing tối đa (momentum thường) |
| `TS_MAX_GAP_WEAK` | 0.03 | gap khi momentum yếu |
| `TS_WEAK_MOMENTUM_THRES` | 0.004 | ngưỡng coi momentum yếu |
| **HARDCODE** (calRateLossDynamicBuy): nhả nửa lãi `*0.5f`, làm tròn `step 0.005f` | hardcode | |

### Tầng 5 — BUDGET / SIZING (TradeUtils.managerBudget + createOrderBUY)
| Config | Giá trị | Vai trò |
|---|---|---|
| `NUMBER_ENTRY_EACH_SIGNAL` | 2 | số lệnh mỗi tín hiệu |
| `LEVERAGE_ORDER` | 1 | đòn bẩy (KHÓA = 1, KHÔNG tối ưu — ràng buộc chiến lược) |
| `BUDGET_MARGIN_RATIO_1` | 0.4820 | ngưỡng margin để giảm budget (mức 1) |
| `BUDGET_DIVIDER_1` | 1.5578 | hệ số chia budget mức 1 |
| `BUDGET_MARGIN_RATIO_2` | 0.7475 | ngưỡng margin mức 2 |
| `BUDGET_DIVIDER_2` | 1.5984 | hệ số chia budget mức 2 |
| **HARDCODE** (managerBudget): marginRatio≥0.9 → /4; ≥0.99 → null (chặn); switch level → /3 | hardcode | |
| + `CoinRankManager.getBudgetMultiplier` (tier multiplier), `getCoinTier` (TIER_3 chặn DCA_LEVEL1) | data-driven | tier-based sizing |

### Tầng 6 — CIRCUIT BREAKER (mặc định OFF — chỉ đo, đã có ADR)
| `BREAKER_MODE` OFF/MARGIN/DCA/BOTH; `BREAKER_MARGIN_HALT` 0.70; `BREAKER_CLUSTER_DD_MAX` -0.30 |
> Memory: MARGIN mode cho risk-adjusted tốt nhất (return/maxDD 3.99). Cân nhắc đưa BREAKER vào genome/bật mặc định.

---

## B. ĐÁNH GIÁ — THÊM / BỚT / GHÉP / GIỮ (đề xuất để Uni duyệt)

### B1. GENE THIẾU NGHIÊM TRỌNG (đang hardcode mà ảnh hưởng PnL lớn — NÊN THÊM)
1. **DCA margin ladder** (DcaUtils 4 bậc: 1.5/2.0/2.5/3.0 → -0.6/-0.7/-0.9/-0.99). Đây là phần điều khiển NHỒI SÂU BAO NHIÊU khi đã lỗ — quyết định trực tiếp rủi ro đuôi của bot DCA. Đang hardcode hoàn toàn. **Đây là 4-8 gene quan trọng nhất đang thiếu.** (WFOTier2 chết đã từng định làm — đúng hướng nhưng bị bỏ.)
2. **Trailing gap "nhả nửa lãi" `0.5f`** (calRateLossDynamicBuy) — quyết định giữ lãi vs để chạy. Nên thành gene (vd 0.3–0.7).
3. **managerBudget hardcode** (≥0.9→/4, switch→/3) — các bậc giảm budget. Nên gene-hóa hoặc ít nhất rà xem có hợp lý.

### B2. GENE NÊN GIỮ (cốt lõi, ảnh hưởng rõ)
- Tầng 4 trailing (RATE_PROFIT_STOP_MARKET, TS_PROFIT_MULTIPLIER, TS_DYNAMIC_K, TS_MAX_GAP*) — bot không stop-loss nên EXIT là sống còn. Phải nằm trong genome.
- Tầng 3 DCA (DCA_TIME/DCA_LOSS BIG_DOWN/UP) — lõi DCA.
- Tầng 1 entry (MIN_MOMENTUM_15M, HARD_RISK_LIMIT_4H, PREDICT_SYMBOL_RATE_MAX_THRESHOLD).

### B3. GENE NGHI PHẲNG / GHÉP / XEM LẠI (cần sensitivity đo)
- `AI_DYNAMIC_MULTIPLIER/MIN/MAX` (3 gene) — nhóm AI_DYNAMIC roadmap nghi "fitness phẳng". Cần quét sensitivity; nếu phẳng → fix cứng, giảm 3→0-1.
- `PREDICT_SYMBOL_RATE_DOWN_15M/UP_AVG/DOWN_AVG` (3 gene) vs `MS_*` (4 gene): CÓ THỂ TRÙNG vai trò (cùng là ngưỡng phân loại market state từ rate). Cần xem 2 nhóm này có chồng chức năng → ghép.
- `MS_DOWN_SMALL_AVG_OR_15M` dùng cho cả 2 điều kiện (avg và 15m) — có thể tách hoặc giữ.

### B4. KHÓA (KHÔNG tối ưu)
- `LEVERAGE_ORDER = 1` — ràng buộc chiến lược cứng của Uni, KHÔNG đưa vào genome.
- `FILTER_MODE`, `BREAKER_MODE` — categorical, chọn bằng tay/ADR không phải gene liên tục.

### B5. VẤN ĐỀ HÀM MỤC TIÊU LIÊN QUAN GENE (Uni đã nêu)
- Genome HIỆN HÀNH (12 gene Combined) **THIẾU TOÀN BỘ tầng 3-4-5** (DCA ladder, trailing, budget). Tức HPO cũ chỉ tinh chỉnh ENTRY, để nguyên phần cõng PnL (DCA/exit) ở giá trị tay. → fitness tối ưu trên không gian thiếu → kết quả lệch.
- Đề xuất genome MỚI gom đủ tầng: ~ Entry(3-4) + DCA(4 + ladder 4) + Trailing(4-5) + Budget(2-4) ≈ **18-22 gene** (nhiều hơn 12 hiện tại). Nhưng cần sensitivity để cắt xuống ~12-15 thực sự nhạy trước khi HPO (tránh không gian quá lớn).

---

## C. CÂU HỎI ĐỂ UNI QUYẾT (sáng 26)
1. Có đưa **DCA margin ladder** (B1.1) thành gene không? (Tôi nghĩ ĐÂY là thiếu sót lớn nhất — phần điều khiển rủi ro đuôi.)
2. 2 nhóm `PREDICT_SYMBOL_RATE_*` và `MS_*` có ghép được không, hay giữ riêng? (cần Uni xác nhận ý nghĩa nghiệp vụ.)
3. Genome đích ~18-22 gene rồi sensitivity cắt, hay Uni muốn giữ nhỏ từ đầu?
4. Có bật `BREAKER_MODE=MARGIN` mặc định (memory: risk-adjusted tốt nhất) + đưa BREAKER_* vào genome không?

> Sensitivity analysis (quét từng gene đo fitness phẳng/nhạy) CHƯA chạy — cần hàm mục tiêu chốt trước
> (đang làm song song). Sau khi Uni duyệt danh sách gene + hàm mục tiêu → chạy sensitivity → chốt genome → HPO/WFO.
