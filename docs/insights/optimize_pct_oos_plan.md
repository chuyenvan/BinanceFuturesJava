# Kế hoạch đẩy %OOS-dương ≥ 70% (baseline: maxfav3 + objective V4.2)

## Trạng thái đo (WFO N=30, ticker sạch)
- maxfav3: **%OOS 43.8% (7/16)**, WFE median 1.009, maxDD 38.7% → FAIL (chỉ vướng %OOS<70%).
- ret2: 37.5% (6/16), WFE ~0.54 → FAIL. maxfav3 dẫn → chọn **maxfav3**.
- **Gốc rễ FAIL:** ~9/16 window là sentinel — chủ yếu `TOO_FEW_TRADES`/`ZERO_TRADES` (hệ không đủ cơ hội vào lệnh), vài `TOO_MUCH_CAPITAL_LOCK` (kẹt vốn do DCA). Đây là ràng buộc **tần suất cơ hội**, không phải sizing.

## Đòn bẩy theo thứ tự ưu tiên (validate-small-first, mỗi bước A/B đo cận biên)

1. **Objective V4.2** (ĐÃ áp, đang A/B) — thưởng tần-suất-lệnh (calmar×freq-factor + ramp thay cliff TOO_FEW). Kỳ vọng: HPO chọn genome nhiều lệnh hơn → giảm TOO_FEW. **Đo trước/sau bằng `ab_v41_v42_summary.txt`.** Nếu tăng %OOS → baseline mới.

2. **Chống capital-lock cho DCA** (theo `dca_strategy_direction.md`, hướng b) — trần margin động theo regime + bỏ `isAll` ngưỡng cứng −0.15 ở BIG_DOWN. Cứu các window `TOO_MUCH_CAPITAL_LOCK` (nhiều lệnh + pnl dương nhưng bị loại). Đây là "quả treo thấp" — vài window có thể chuyển sang SUCCESS ngay.

3. **Nới cổng vào lệnh (tần suất)** — sweep rộng các gene chặn entry: `MIN_MOMENTUM_15M`, `PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `AI_DYNAMIC_MIN`, ngưỡng gate/selector. Mục tiêu: các quý ZERO/TOO_FEW có ít nhất ≥ sàn lệnh. Rủi ro: nới quá → nhiễu, giảm WFE → phải giữ WFE≥0.5.

4. **Trailing riêng** (theo `trailing_stop_strategy_direction.md`, hướng a) — ATR-scaling gap thích ứng vol → giữ lệnh thắng lâu hơn, tăng PnL/window SUCCESS → nâng WFE, gián tiếp giữ %OOS ổn định khi nới entry.

5. **(Sau cùng) đa sleeve / model gate** — tách sleeve entry theo nguồn tín hiệu; DCA/trailing gate bằng model xác suất. Chỉ làm khi 1-4 chưa đủ.

## Cách chạy (button đã sẵn: orchestrator điều phối / script)
- `optimize_maxfav3.sh` (trên Oracle, `.run/`): WFO tham-số-hoá, file-ticker, 2-worker. Env: `JAR N SEED DS TAG`.
  - Chốt V4.2 baseline: `bash optimize_maxfav3.sh` (mặc định maxfav3+V4.2, N=30, seed=42).
  - Kiểm ổn định (chống selection-noise): chạy thêm `SEED=7` và `SEED=123`, so %OOS/WFE.
- Mỗi đòn bẩy = 1 thay đổi CÔ LẬP → A/B với baseline hiện tại; chỉ nhận nếu %OOS tăng mà WFE≥0.5, maxDD≤50% (pre-registered, không đổi ngữ nghĩa).

## Ngưỡng pass (pre-registered — KHÔNG đổi)
%OOS-dương ≥ 70%, WFE median ≥ 0.5, maxDD-OOS xấu nhất ≤ 50% vốn.
