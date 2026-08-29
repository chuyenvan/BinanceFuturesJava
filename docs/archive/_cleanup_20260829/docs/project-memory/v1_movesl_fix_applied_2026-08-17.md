# APPLIED — moveSL live fix 0.03→0.05 (2026-08-17 22:40 +07)

Theo reconcile `v1_live_vs_wfo_param_reconcile_2026-08-17.md`: chỉ 1 param vênh = moveSL. Uni duyệt "áp 0.05 + restart ngay".

## Đã làm
- Thêm `export SIM_RATE_PROFIT_STOP_MARKET=0.05` vào `/home/chuyennd/java/v_t_m/conf/env.sh`
  (section "v1 WFO canonical", cạnh SELECTOR_RANK_TOPK=5 + SIM_MIN_MOMENTUM_15M=0.008).
- Backup: `conf/env.sh.bak_moveSL_20260817_223917`.
- Restart `bin/daemon.sh restart`. OLD_PID=9246 → NEW_PID=7030 (22:40:16).

## Verify
- `/proc/7030/environ`: SIM_RATE_PROFIT_STOP_MARKET=0.05 ✓ (+ SELECTOR_RANK_TOPK=5, SIM_MIN_MOMENTUM_15M=0.008).
- Startup sạch: "Funding AI System Ready", ThreadManagerOrder/DetectEntrySignal2TradeNormal up.
- Reconcile vị thế: "Update all position:58" — đủ 58 lệnh reload từ Binance. Không ERROR mới sau 22:40.
- SL là lệnh thật trên Binance (OrderHelper.stopLoss) → 58 lệnh được bảo vệ suốt downtime restart.

## Ý nghĩa
- Live giờ khớp canonical WFO-best hoàn toàn (grid15/K5/gate0.008/moveSL0.05/fee0.002/lev1/N_entry2/exit-genome default).
- moveSL 0.03→0.05: trailing chỉ siết khi lãi >5% (thay vì >3%) → bớt cắt lãi sớm, đúng hướng chống "ăn ít".
- Rollback nếu cần: xoá dòng export trong env.sh (hoặc dùng backup) + restart.

## Lưu ý theo dõi
- Quan sát vài ngày: turnover giảm (giữ lệnh lâu hơn), avg win tăng? So với trước 22:40.
- config.properties(242) vẫn ghi RATE_PROFIT_STOP_MARKET=0.01 (bẫy, code bỏ qua) — nên sửa file cho khỏi gây nhầm sau này.
