# GO-LIVE — lệnh thật BẬT (2026-08-21 06:14 GMT+7)

⚠️ TRẠNG THÁI HIỆN TẠI: v_t_m ĐANG ĐẶT LỆNH THẬT (hết shadow). Cập nhật mọi doc/runbook cũ nói "shadow đang bật" — KHÔNG còn đúng.

## Cấu hình live (v_t_m/conf/env.sh, bot pid 14494)
- `SHADOW_NO_PUSH=false`  ← LỆNH THẬT (was true tới 06:14)
- `TS_PRED_GAP=1`         ← pred-gap bật (gap trailing theo selector P(no-pump), weak khi >0.29)
- `SIM_TS_PROFIT_MULTIPLIER=3.0` ← arm ratchet 15% (was 26%)
- `SELECTOR_RANK_TOPK=5`, `SIM_MIN_MOMENTUM_15M=0.008`, `SIM_RATE_PROFIT_STOP_MARKET=0.05` (giữ)
- budget 280/lệnh, balance init 14000.

## Verify go-live (đã chạy)
- Lệnh thật đầu: BUY ONGUSDT entry 0.07997 qty 879 @06:15:24; vị thế 65→66; 0 order-error. Chuyển từ shadow sạch (shadow cuối ONTUSDT 06:00).

## 3 thay đổi cùng lúc (user duyệt, user monitor)
arm 26→15% + pred-gap lần đầu + lệnh thật. Nếu lệch khó tách nguyên nhân — theo dõi kỹ.

## Monitor (v_t_m/logs/full.log)
- Entry thật: `BUY <SYM> entry: ... PREDICT_SYMBOL_TRADE` (KHÔNG `[SHADOW]`).
- pred-gap SL: `Renew price SL:<sym> ... <rate>%` — coin P(no-pump) cao gap~3%, thấp gap~8% (hiện dần khi vị thế đạt arm 15%).
- `Update all position:N`, budget/margin.

## Rollback (nhanh)
- Về shadow: `sed -i s/SHADOW_NO_PUSH=false/SHADOW_NO_PUSH=true/ conf/env.sh` + `bin/daemon.sh restart`.
- Tắt pred-gap: bỏ dòng TS_PRED_GAP=1 + restart. Về arm 26%: bỏ SIM_TS_PROFIT_MULTIPLIER + restart.
- Full revert env: `cp conf/env.sh.bak_golive_20260821 conf/env.sh` + restart (về shadow+arm26, KHÔNG pred-gap). Jar backup: .bak_predgap_20260820 (trước pred-gap), .bak_guard_20260820.

## Việc nền đang chạy (không liên quan go-live)
- OI incremental C1: ingestor collectData pid 1455, OI_USE_ACCUM=1, chạy 60'/lượt, decoupled Oracle lúc chạy. Oracle = kho lạnh re-seed. 226 đã chết.
