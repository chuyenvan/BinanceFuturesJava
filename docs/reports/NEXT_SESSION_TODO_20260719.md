# HANDOFF 2026-07-19 (consolidated) — đọc file này + docs/rules/ce-buttons.md là đủ.
> Supersede các append rải rác ở 20260718.md. R1 (CE-first) + R2 (handoff-luôn): xem ce-buttons.md.

## KIẾN TRÚC ĐÃ CHỐT
Bỏ DCA + bỏ gate-cứng + **selector EV2** (classifier P(HIT) + reg E(ret|miss)) n6. Edge **THẬT nhưng
regime-gated** (bull dương, chop breakeven). **Faithfulness PASS** (entry-match 100%, placebo PASS,
proxy−ma-sát≈WFO) → số ĐÁNG TIN. Sim ma sát: fee 0.2% + slippage 0.6% = 0.8% (funding OFF). Slippage
thật CHƯA đo (hoãn; bot 242 không lưu giá khớp → cần userTrades API hoặc thêm log).

## NÚT THẮT XUYÊN SUỐT = OPPORTUNITY FREQUENCY (không phải edge)
- **oi_z veto (long) = lever CHẤT LƯỢNG thật:** WFE 0.20→1.5, BURN 6→2, maxDD 9→6%. NHƯNG Q0.5 & Q0.75
  đều **FAIL vì frequency** (4 ZERO 2022-coverage + 6 TOO_FEW). Nới Q không giúp (bệnh không phải oi_z).
- → 3 đường giải FREQUENCY: (a) **2022 coverage** (EV2 export FIRST_OOS về sớm hơn), (b) **horizon 12h**
  (1152 kèo/quý), (c) **thêm SHORT** (nhân đôi cơ hội + lấp regime chop).
- Đang chạy: `oiz_gateon` WFO (oi_z Q0.5 + gate-ON, quality-max) → nếu VẪN fail = chốt frequency là wall.

## SHORT (đòn bẩy #2, lấp chop)
- Alpha THẬT: classifier AUC 0.85(4h)/0.77(12h)/0.71(24h). Mechanics sim: `ENABLE_SHORT` +
  `createOrderSELL` + hard-SL `SHORT_SL_PCT`(0.25) + time-stop + PnL đảo dấu. **JUnit 6/6 PASS**
  (commit df542c5) — default OFF byte-identical. DCA tắt khi short.
- **Feature short KHÁC long (short-featscreen 12h):** conditioning = **crowding** `ls_toptrader`(+1.61,
  mono1.0) + `ls_global`(+1.45) — top-trader long đông → dump. → veto short cụ thể.
- **Grid (target{3,6,9,15}×horizon{4,12,24,72}×stop{8,15,20,30}):** 4 kernel Kaggle. grid-24h: net_bull
  dương & tăng theo target (t15 bull +6.24) NHƯNG **net_chop âm = ARTIFACT** (grid có nhánh chốt-+t cap
  winner; v2 let-dump-run cho chop +12). → **CẦN re-run grid với let-run accounting (bỏ chốt +t).**
- **Calibration:** ps short thấp (max 0.67, base-rate 1.3%) → gate long (ps≥0.68) cho 0 lệnh →
  dùng **rank/top-K** thay ngưỡng tuyệt đối. predict_wf_short + jar short (preflight-v42-short.jar) đã dựng.

## HẠ TẦNG / CE (R1 đã trả nợ)
- Nút mới: **`pred_convert` / `wfo_build_ds` / `wfo_verify`** + pipeline `wfo_from_preds.json` (commit 2d544e6,
  bg_selftest 6/6). Từ giờ WFO-from-preds = nút bấm, không SSH thô.
- Jar Oracle `preflight-v42.jar` = có TRAIL_PEAK_MODE + entry-log + short(gated off). Backup .bak_*.
- Datasets: wfo_ds_ev2 (long), wfo_ds_oiz (Q0.5), wfo_ds_oiz75, wfo_ds_short. Ticker daily có ở Oracle.

## ĐANG CHẠY (2026-18 tối)
- Oracle: `oiz_gateon` WFO (4/16). Kaggle: short-grid 4h/12h/72h (24h xong), short-featscreen xong.

## NEXT (ưu tiên)
1. Đọc verdict oiz_gateon (quality-max fail? → frequency là wall).
2. **Fix grid accounting (let-run, bỏ chốt +t)** → re-run 4 horizon → chọn winner short (net+winrate+tpq,
   chop theo let-run).
3. Short winner → **re-export Java label chính xác** (time-to-level cho +stop; CSV hiện chỉ có cực-trị) →
   validate. Short veto = ls_toptrader.
4. Long frequency: thử 12h horizon + 2022 coverage.
5. **Validate 2 tầng khi bật short thật:** real-data 1 tháng → Excel → recompute code khác đối chiếu (Uni dặn).
6. Slippage thật (sát go-live). Funding: bật lại + dấu SHORT-nhận-khi-funding+ (Uni: tính tổng rồi trừ, nhỏ, tạm bỏ).
