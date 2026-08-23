# Rà lại GATE (WFO runtime) — 2026-08-13

Đọc trực tiếp code hiện tại (không dựa trí nhớ). File: `AIRejectFilter.java`,
`SimulatorMarketLevelTicker1MStopLoss.java` (sim WFO dùng), `Configs.java`,
`wfo-worker-1/run_worker.py` (env runtime).

## 1. Gate hiện tại là gì — ĐÃ XÁC MINH

- **Chỉ còn 1 nhánh: MOM15** (predReturn15M). Nhánh RISK/DD4H (`predRisk4H`) **đã bỏ hẳn 2026-08-08**
  (comment ngay trong file: cột này không còn model đứng sau, chỉ carry-forward từ gate cũ → làm lá chắn
  live là "rủi ro giả"). `setConfig(risk,...)` vẫn ghi `HARD_RISK_LIMIT_4H` nhưng **không dùng để lọc**
  (chỉ cho HPO/log đọc, giữ để không lệch index gene).
- Vậy: **gate = return15m-only, KHÔNG còn risk4h.** Đúng như nghi vấn.

## 2. WFO đi nhánh nào — DYNAMIC, không phải static

`WFORunner` → `SimulatorMarketLevelTicker1MStopLoss`. Entry của WFO đến từ **selector loop**
(rank top-K8), tạo lệnh với `MarketLevelChange.PREDICT_SYMBOL_TRADE` + `symbolPred` (=1−p6, thấp=tốt).
Tại gate (dòng 1013-1017):

```
if (levelChange == PREDICT_SYMBOL_TRADE)  filterResult = checkSignalDynamic(predict, symbolPred);
if (filterResult == null)                  filterResult = checkSignal(predict);   // fallback
```

→ WFO **luôn đi `checkSignalDynamic`** (vì mọi entry là PREDICT_SYMBOL_TRADE). Static chỉ là fallback khi symbolPred null.

### Công thức dynamic (đã ráp số runtime)
Env worker: `SIM_MIN_MOMENTUM_15M=0.008`, `SELECTOR_RANK_TOPK=8`. Các cái khác dùng default Configs:
`FILTER_MODE=A` (gate BẬT), `OFF_FLAT_HARD=true`, `AI_DYNAMIC_MIN=0.26787`, `AI_DYNAMIC_MULTIPLIER=1.2876`,
`PREDICT_SYMBOL_RATE_MAX_THRESHOLD=0.15`.

- **Early hard reject:** nếu `predReturn15M < 0.008` **VÀ** `symbolPred > 0.15` → REJECT.
- **Ngưỡng động:** `thr = 0.008 × max(0.26787, (symbolPred/0.15)×1.2876)` — **không có trần** (OFF_FLAT_HARD bỏ clamp trên).
  PASS nếu `predReturn15M ≥ thr`.
  - Coin top (symbolPred thấp → chạm sàn 0.26787): `thr = 0.008×0.26787 = 0.00214` = **0.21%**.
  - Điểm hòa (scaleFactor=1): `symbolPred = 0.15/1.2876 = 0.1165`. symbolPred < 0.1165 → thr < 0.008.

## 3. Đánh giá — GATE YẾU cho tập THỰC SỰ vào lệnh, và MÙ với đuôi

1. **Tín hiệu momentum là MARKET-LEVEL, không per-symbol.** `predReturn15M` là **1 số/timestamp** dùng chung
   cho mọi coin ứng viên. Khác biệt per-symbol chỉ vào qua việc **scale ngưỡng theo symbolPred (selector)**,
   không phải qua model momentum riêng của từng coin pump. Gate không "đọc" động lượng riêng của coin đang xét.
2. **Với coin được trade (top-K8, symbolPred thấp) ngưỡng ~0.21%** → gần như **no-op**: chỉ cần market
   momentum dự đoán hơi dương là qua. Gate siết mạnh cho coin hạng xấu (symbolPred cao) nhưng **những coin đó
   không được trade** (chỉ top-8 vào) → gate **hiếm khi bind** trên tập thực sự vào lệnh. ⇒ **gate yếu ở đúng chỗ quan trọng.**
3. **KHÔNG có chiều rủi ro/đuôi.** Gate chỉ check upside (return15m). Không có cơ chế nào nhìn downside/maxDD.
   ⇒ **Đây chính là lý do cấu trúc** khiến vấn đề của project vẫn còn: "chọn coin pump nhưng đuôi lớn (maxDD)".
   Gate hiện tại **không có đòn bẩy nào** để chặn 1 cú pump có tail risk cao.

## 4. Hệ quả cho Phase 5 (gate v2) — hướng cụ thể

- Vấn đề pump/tail **không sửa được bằng cách chỉnh ngưỡng momentum** — vì gate không có chiều đuôi.
  Cần **thêm 1 chiều rủi ro/đuôi WF-clean** (cái cũ risk4h bị bỏ vì leaky, không có model → phải làm đúng).
- **Nguyên liệu đã có sẵn:** label 5m mới export kèm **`maxFav`/`maxAdv` theo từng horizon**. Đây đúng là
  thứ để train 1 predictor đuôi WF-clean (vd dự đoán `maxAdv_4h` = mức lỗ ngược tối đa kỳ vọng per-symbol),
  rồi gate reject entry có tail dự đoán lớn. Đây là con đường Phase 5 nên đi.
- Cân nhắc thêm: cho ngưỡng momentum **có trần lại** cho coin top (bỏ OFF_FLAT_HARD hoặc set AI_DYNAMIC_MIN cao hơn)
  để gate không rơi về 0.21% — nhưng đây chỉ là vá nhỏ, **không thay được chiều đuôi**.

## 5. Việc gate đã full lưới 1m đủ data chưa (Phase 0 câu hỏi cũ)
- Gate ăn `predReturn15M` = **market-level 15m model**, độc lập selector grid. Việc "full lưới 1m đủ data"
  áp cho **selector features** (đang đóng gói 5m), không phải cho gate. Gate v2 (Phase 5) sẽ cần thêm
  label `maxAdv/maxFav` (đã có trong label 5m) — coi như đủ nguyên liệu, không phải chờ export 1m.
