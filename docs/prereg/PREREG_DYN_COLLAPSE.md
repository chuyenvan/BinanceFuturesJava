# PREREG_DYN_COLLAPSE — Dynamic (path) collapse probe

Chot TRUOC khi chay. CHI DO (khong sim, khong overlay, khong deploy, khong tune).
Khong cham 242/push. Holdout 2026 nguyen (loai lenh entry>=2026; featv2/closes lookup <=2025-12-31).

## Cau hoi
Voi moi lenh, tai t = entry + D (D in {4h,12h,24h}), CHI lay lenh CON MO tai t (te_ms > t),
tinh feature PATH (do lai tai t + delta ke tu entry) va hoi: co du bao SOM duoc lenh do CUOI CUNG
collapse khong? Dac biet: tin hieu OI/funding co VUOT gia (price-path) khong?

Nhan: collapse = (status==STOP_LOSS_DONE) & (profit<=-20). Vi chi lay lenh con mo tai t nen exit
(gom SL) luon xay ra SAU t => nhan la "collapse-sau-t", khong leak.

## Du lieu
- Ledger: printDone.csv X1_C3_FULL_PARITY_R canonical, level==PREDICT_SYMBOL_TRADE, entry<=2025 (n=1996, all BUY).
- Gia: CLOSES_1H.bin dtype [(ts>i8)(sym>i2)(c>f4)], nhan qua: close[t] = close kline dong luc t (causal tai t).
- featv2: /home/ubuntu/featv2/feat_v2_x1.parquet (panel gio), join theo (ts_h, symId) tai t VA tai entry_hour.
- Coverage da kiem: close_t + featv2_t = 100% cho ca 3 D (open_at_t: 4h=1418, 12h=1004, 24h=720).

## Feature PATH (tinh tai t)
PRICE-PATH (A): unrealized_ret_at_t = close_t/entry_price - 1; dd_since_entry = min_{h in [entry,t]} close_h/entry - 1;
  max_fav_so_far = max_{h} close_h/entry - 1; dd_velocity = dd_since_entry / D_hours; ret_last_bar = close_t/close_{t-1h} - 1.
OI/FUNDING-PATH (B): tai t = oi_z, oi_delta24h, oi_delta_3d, ls_global, ls_toptrader, taker_buy, fund_last,
  fund_sum_3d, fund_z_30d, fund_trend; delta-ke-tu-entry = d_oi_z, d_ls_global, d_ls_toptrader,
  d_fund_sum_3d (proxy funding_since_entry), fund_flip = sign(fund_last_t)!=sign(fund_last_entry).
  LUU Y: featv2 khong co OI LEVEL raw -> "deltaOI" dung oi_delta24h/oi_delta_3d (OI momentum causal tai t) + d_oi_z (proxy). Ghi ro trong ket qua.
(tham chieu) entry-time single-feature AUC (symbolPred, vol_7d, dd_7d, oi_z_entry...) chi de mo ta.

## 3 mo hinh (moi D), model = XGB (max_depth3, n200, lr0.05, min_child_weight20) — giong probe cu
- (A) PRICE-PATH only
- (B) OI/FUNDING-PATH only
- (C) PRICE + OI/FUNDING (full)
Do: AUC walk-forward, cuts quy 2022Q1..2025Q4, purge 72h (tr: te_ms < c-72h), test [c, c+3thang).
H0: xao nhan train x10 -> mean/sd AUC.

## QUYET DINH (chot truoc)
GREEN (OI/funding dang theo, them gia tri NGOAI gia) khi:
  AUC(C) >= 0.65  VA  AUC(C) - AUC(A) >= 0.03  VA  AUC(C) tren H0 (> mean_null + 3sd).
DONG khi: chi (A) cao (gia da du) HOAC (B) ~ 0.5 (OI/funding khong dan) => trailing da xu gia,
  cat-theo-gia khong giup them tren T170; OI/funding khong dan.
Ngoai pham vi: sim/overlay (chi lam neu GREEN, la follow-up), 2026, tune.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
