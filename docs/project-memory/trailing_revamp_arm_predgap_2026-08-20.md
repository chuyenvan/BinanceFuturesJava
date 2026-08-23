# Trailing revamp: hạ arm (LIVE) + pred-gap (deployed OFF) — 2026-08-20

Dựa trên Tier-1/Tier-2 (doc trailing_pred_gap_tier1/tier2). User duyệt: gộp hạ arm + pred-gap, verify semantics trước.

## Phase A — hạ arm: ĐÃ LIVE
- `arm = TS_PROFIT_MULTIPLIER × RATE_PROFIT_STOP_MARKET`. Cũ 5.21847×0.05=0.26 (26%, trange: 84% never arm).
- Set env `SIM_TS_PROFIT_MULTIPLIER=3.0` (hook Configs L666, có trong jar) → **arm ratchet 26%→15%** trên vị thế thật (site2 processDynamicTP_SL). Site1 (initial SL) vẫn 0.05.
- v_t_m/conf/env.sh (backup .bak_arm_20260820). Bot pid 6129→12119. ⚠️ Trailing/SL là LIVE (KHÔNG shadow — SHADOW_NO_PUSH chỉ chặn BUY mới); đây là thay đổi tiền thật trên 65 vị thế.
- Rollback: xoá dòng SIM_TS_PROFIT_MULTIPLIER=3.0 (về default 5.21847=arm26%) + daemon restart.

## Phase B — pred-gap: CODE DEPLOYED, FLAG OFF
### Semantics ĐÃ XÁC MINH (provenance v1_reconcile_and_model_provenance)
Live `Funding_Classifier_Final.onnx` = `selector_wfo_4h.onnx` (WFO selector). ONNX out `prob[batch,2]`, **prob[0]=P(no-pump)**. Nên `symbol2FundingPred`(live)=prob[0]=**P(no-pump)=1−sel** (sel=P(maxFav≥6%) đã validate). Dấu: **weak/tight gap khi P(no-pump) CAO** (coin khó pump→chốt sớm); gap lỏng khi thấp (nuôi).
### Code (build clean, jar 99622659, backup jar .bak_predgap_20260820)
- `DetectEntrySignal2TradeNormal`: static `LATEST_SEL_PNOPUMP` (ConcurrentHashMap) cập nhật mỗi tick entry (15m, duyệt mọi symbol) = prob[0] per-coin.
- `TradeUtils.calRateLossDynamicBuyPNoPump(mp, pNoPump, thr)`: gap giống calRateLossDynamicBuy, weak khi pNoPump>thr.
- `BinanceOrderTradingManager.tsGap(rateLoss, gatePred, symbol)`: nếu env `TS_PRED_GAP=1` & có pNoPump → gap theo pred; else gap cũ (gate). Wire cả 2 site SL (L286 initial, L414 ratchet).
### Bật (khi duyệt)
`echo export TS_PRED_GAP=1 | tee -a /home/chuyennd/java/v_t_m/conf/env.sh` (+ tùy chọn `export TS_PNOPUMP_WEAK_THR=0.29`; weak khi P(no-pump)>0.29 ≈ sel<0.71 ≈ p25) → `bin/daemon.sh restart`. Verify env có TS_PRED_GAP=1. Rollback: xoá dòng + restart (flag off = byte-identical hành vi cũ).

## Kỳ vọng (flaws-first)
- Phase A (arm): lever chính, tác động rõ (SL bám đỉnh từ 15% thay 26%).
- Phase B (pred-gap): modest (+2-4% captured-profit của winners trailing-active ở arm thấp, từ Tier-2). Caveat: Tier-2 dùng predwf_B015 (per-fold); live dùng model_wfo_last (1 model) ≈ nhưng không byte-identical. Đo tác động thật chỉ thấy khi bật + theo dõi log 'Renew price SL' / exit thực.
- Cả 2 đều LIVE (SL tiền thật). Theo dõi: 'Renew price SL:{sym} ... {rate}%' trong v_t_m/logs/full.log; so gap coin P(no-pump) cao (nên ~3%) vs thấp (nên ~8%).
