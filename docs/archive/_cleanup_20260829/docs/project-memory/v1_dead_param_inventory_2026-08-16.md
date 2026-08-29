# Dọn rác param — inventory (step 1 của v1, 2026-08-16)

Mục tiêu: cắt param chết để giảm bề mặt lệch backtest↔live trước khi sửa code live. Phân theo **độ chắc chắn**.

## A. CHẾT chắc chắn (code-gated OFF ở config worker hiện tại) — cắt được ngay
Bằng chứng: `Configs.java` (decompiled) + env worker.

- **DCA grid**: `DCA_GRID_LEVELS, DCA_GRID_WEIGHTS, DCA_GRID_L1, DCA_GRID_STEP, DCA_GRID_LEGS, DCA_GRID_W_RATIO, DCA_GRID_SCALE, DCA_GRID_SCALAR` — gated bởi `DCA_GRID_ENABLED` (env không set → false). Cả nhánh DCA-grid dead.
- **DCA tier**: `DCA_TIER_MARGIN_CAPS, DCA_TIER_CAP_BASE, DCA_TIER_CAP_STEP` — gated `DCA_TIER_MARGIN_ENABLED=false`.
- **DCA market-crash genes**: `DCA_TIME_BIG_DOWN, DCA_LOSS_BIG_DOWN, DCA_TIME_BIG_Up, DCA_LOSS_BIG_UP` — DCA tắt (runbook + `WFO_DISABLE_DCA`). (xác nhận cuối qua `shouldDca`).
- **Breaker**: `BREAKER_MODE, BREAKER_MARGIN_HALT, BREAKER_CLUSTER_DD_MAX` — worker set `SIM_BREAKER_MODE=OFF`; SensitivityTool cũng force OFF.
- **Short**: `SHORT_SL_PCT, SHORT_TIME_STOP_HOURS` — `ENABLE_SHORT=false` (không mở short).
- **Time-stop**: `TIME_STOP_HOURS=0` (không cắt theo giờ) → dead.
- **Hard SL %**: `HARD_SL_PCT=0` → dùng `HARD_RISK_LIMIT_4H` thay, HARD_SL_PCT dead.

→ ~20 param cắt được với độ chắc cao (đều nằm sau feature đã tắt).

## B. SỐNG (xác nhận đang dùng ở config hiện tại) — giữ
- `MIN_MOMENTUM_15M` (gate chính, `SIM_MIN_MOMENTUM_15M=0.008`) — AIRejectFilter đọc 5×.
- `SELECTOR_RANK_TOPK=5` (K5), `HARD_RISK_LIMIT_4H=−0.2` (SL rộng), `RATE_PROFIT_STOP_MARKET` (moveSL 0.05).
- TS trailing family: `TS_MAX_GAP, TS_DYNAMIC_K, TS_PROFIT_MULTIPLIER, TS_GIVEBACK_RATIO`.
- `AI_DYNAMIC_MIN/MULTIPLIER/MAX` — AIRejectFilter dùng để scale ngưỡng động (nhánh checkSignalDynamic) → sống.
- `SIM_APPLY_FUNDING`, capital, leverage=1.

## C. PHẲNG/marginal (sweep file-based, đúng data) — pin về 1 giá trị, bỏ khỏi search
- `TS_MAX_GAP`: PnL swing <9% qua dải 0.05→1.0 (đỉnh ~0.30). Pin ~0.30.
- `RATE_PROFIT_STOP_MARKET`: sweep đang chạy (đóng Gate 0). Kỳ vọng cũng phẳng.

## D. MƠ HỒ — cần xác nhận empiric trên ĐÚNG data (chưa chốt)
`PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `PREDICT_SYMBOL_RATE_DOWN_15M/UP_AVG/DOWN_AVG` (market), `MS_UP_BIG/DOWN_BIG/UP_SMALL/DOWN_SMALL` (market-state), `TS_MAX_GAP_WEAK`, `TS_WEAK_MOMENTUM_THRES`, `BUDGET_MARGIN_RATIO_1/2, BUDGET_DIVIDER_1/2`.

**Vấn đề công cụ**: `SensitivityTool` (jar) sweep đủ 26 gene qua reflection NHƯNG đọc data từ **Aerospike** (host 242 ns=test — provenance không chắc khớp selector hiện tại) → chạy mù rủi ro sai. `ExitParamSweepProbe` đọc **wfo_ds file** (đúng data) nhưng chỉ sweep 4 exit param.

**Cách chuẩn để hoàn tất mục D** (2 lựa chọn):
1. Xác minh Aerospike (242 ns=test) có đúng market+pred+funding khớp wfo_ds → chạy SensitivityTool; dùng nhóm DCA/breaker (đã biết chết) làm sanity-check range≈0. Nếu chúng phẳng → tin ranking các gene còn lại.
2. Sửa SensitivityTool đọc wfo_ds file (như ExitParamSweepProbe) rồi chạy — sạch nhất, cần build lại jar.

## Kết luận step 1
Nhóm A (~20 param) cắt được ngay với độ chắc cao — đó là phần lớn "rác". Nhóm D cần 1 lượt sensitivity trên đúng data để chốt. Sau khi chốt A+D → config gọn (~12-15 gene sống) → sang step 2 (rà ingress).
