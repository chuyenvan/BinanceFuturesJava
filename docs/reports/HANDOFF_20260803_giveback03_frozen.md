# HANDOFF 2026-08-03 — chốt TS_GIVEBACK_RATIO=0.3 + DCA bỏ + instrument MFE — ĐỌC TRƯỚC

> Nối từ START_HERE_20260802 + HANDOFF_20260802b. Phiên này: giết DCA bằng số, đo winner MFE,
> sweep giveback → chốt 0.3, bypass 226 flaky bằng jobstore local.

## 1. FROZEN CONFIG MỚI (thay 0.5 → 0.3)
DCA-off frozen, đổi DUY NHẤT `TS_GIVEBACK_RATIO=0.3`:
`TS_GIVEBACK_FLOOR=true TS_MIN_GAP=0.01 TS_GIVEBACK_RATIO=0.3 SELECTOR_RANK_TOPK=8`
`SIM_MIN_MOMENTUM_15M=0.008 DCA_GRID_ENABLED=false DCA_GRID_SCALAR=false DCA_TIER_MARGIN_ENABLED=false`
`SIM_BREAKER_MODE=OFF SIM_APPLY_FUNDING=true WFO_HARNESS_FIX=true`
Dataset `wfo_ds_ret2wf_4h_ff`, jar `gatecount.jar` (report-only patch ở /tmp/patch).

## 2. Bằng chứng giveback sweep (full-16, DCA-off, n=1, jobstore local)
| ratio | Total 16w | 2022-23 | Holdout 2024-25 | %OOS+ | keepRatio |
|---|---:|---:|---:|---:|---:|
| **0.3** | **18,683** | 6,209 | 12,474 | 14/16 | 0.54 |
| 0.4 | 17,485 | 5,653 | 11,831 | 14/16 | 0.46 |
| 0.5 (cũ) | 16,826 | 4,546 | 12,280 | 14/16 | 0.38 |

- 0.3 tốt nhất tổng (+11% vs 0.5), monotonic 0.3>0.4>0.5.
- CAVEAT: ưu thế **tập trung 2022-23 (+37%)**; holdout 2024-25 gần như HÒA (12,474 vs 12,280 = +1.6%).
  → chọn 0.3 vì **không bao giờ tệ hơn trên tổng + tốt ở vol cao**, KHÔNG kỳ vọng +37% forward.
- 2 window âm w9(2024Q2)+w14(2025Q3) KHÔNG đổi qua mọi ratio — trần thật là loser-exit (đã gác hard-SL).

## 3. Logic TS_GIVEBACK_RATIO (FLOOR=true)
`gap = max(peakProfit × RATIO, TS_MIN_GAP)`; `SL = peakProfit − gap = peakProfit×(1−RATIO)`, ratchet 1 chiều,
chỉ arm sau lãi ≥ RATE_PROFIT_STOP_MARKET(~3%). RATIO thấp = nhả ít = trail chặt = giữ nhiều % đỉnh, cắt
sớm khi dip. Chỉ tác động WINNER (đã arm), không đụng loser.

## 4. DCA — bỏ (chốt bằng số 5 mặt)
Test 3 mức fire (off / grid-30 bất động / shallow-10 fire mạnh), cùng frozen n=1:
- off: PnL 16,826 | grid-30: 14,192 | shallow-10: 13,079 — càng nhiều DCA càng THẤP PnL, maxDD cao hơn,
  %OOS y nguyên 88%. Holding-time on≈off (~53-58h), winRate không cải thiện. DCA không cộng ròng trên
  PnL/%OOS/maxDD/winRate/holding-time. Root: grid mới fire ở −30% (selector thoát trước), khác DCA cũ −8..−22%.
  → **bỏ DCA cho gọn.** (Chưa test DCA-cũ market-gated `shouldDca` — biến thể duy nhất chưa đo.)

## 5. Hạ tầng + code phiên này
- **Commit `1a25a63`**: guard autosnap trong wfo_fanout (chống reset đè mất verdict — vụ confirm_n30).
- **Commit `fe00232`**: instrument avgHoldHours + winner MFE/give-back (p50/p75/p90 + keepRatio + gvbackMean),
  report-only byte-identical. + **FIX bug**: maePeak chưa từng copy sang done-order (closeOrder/flush/mergeOrder
  chỉ copy maeLow) → mọi đo peak-retention trước = 0. Log `[METRIC-HOLD]` + `[METRIC-MFE]` per-window.
- **Commit `4195c03`**: Configs env-fallback cho TS_GIVEBACK_RATIO (trước chỉ đọc properties → không sweep
  qua env được; sibling TS_MIN_GAP thì có).
- **226 Aerospike flaky** (connect timed out / Cluster empty, giết 2 run). Bypass: jobstore LOCAL Oracle
  `WFO_STATE_HOST=127.0.0.1 ns=test` — chạy 5 fanout không flake. Dùng khi 226 bất ổn.
- Shadow-compile: 4 class patch (Configs/Sim/V4/StrategyWfoTask) ở /tmp/src → /tmp/patch, chạy
  `-cp /tmp/patch:gatecount.jar` (KHÔNG rebuild fat-jar). javac 11 trên Oracle.
- Winner MFE (frozen): keepRatio ~0.38 (giữ 38% đỉnh, nhả 62%), đỉnh median ~4.5% p90 10-40% → có room.
- Script tái dùng: /tmp/run_gvb.sh, /tmp/run_gvb_full.sh, /tmp/driver_*.sh (reset+spawn worker local).

## 6. ĐANG LÀM: rank-K entry sweep (STEP 3)
Trên frozen giveback-0.3, sweep `SELECTOR_RANK_TOPK` {5,8,12} (offset 0) full-16, jobstore local.
Đo: total PnL + %OOS + holdout + **số trades/window (tần suất entry)** + capital-lock — kiểm giả thuyết Uni
"còn room cho entry". Tags rk05/rk08/rk12. Xong đọc `wfo_rk*_w*.log`.
