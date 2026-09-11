# PREREG_COLLAPSE_PROBE — probe OFFLINE: feature tai thoi diem VAO co du doan duoc "collapse" khong?

Chot: 2026-09-11, commit TRUOC khi chay. Khong sim, khong Kaggle, khong train model san xuat, khong 2026.
Muc dich: tra loi CO/KHONG cho cau "co nen train mot model cham collapse-risk lam filter" — bang AUC walk-forward,
truoc khi bo cong xay bat cu thu gi. Ky vong ghi truoc (DEV_COLLAPSE_CHECK muc 3): AUC ~0.55-0.60, vi tap coin
collapse = tap coin S1 xep len (cung low-cap bien dong manh). Probe KHONG duoc dung de chon feature/nguong cho filter.

## 1. Du lieu
- `devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv` (canonical X1_C3_FULL, md5 2478e90d..., 2,266 lenh, 2022-01..2025-12).
- CHI lenh `level == PREDICT_SYMBOL_TRADE` (1,996) — leg DCA/BIG_DOWN khong di qua selector, ngoai pham vi.
- Feature entry-time: (F1) tu printDone: `symbolPred, pred15m, risk4h, dow, up, dow15m`, gio trong ngay (GMT+7),
  `n_open_at_entry` (so lenh dang mo luc vao — cau noi sang PREREG_BOOKCAP), `is_reentry_24h` (cung sym, lenh truoc dong <=24h).
  (F2) 39 feature `featv2/feat_v2_x1.parquet` (bo `noise_0..2`) tai `ts_h = floor(start, 1h)`, join (ts_h, symId) qua
  `selector_pred_out/symbol_map.csv`. Quy uoc VISION: feature tai ts_h chi dung du lieu <= ts_h < start => khong nhin truoc.
- CAM dung (leak/post-entry hoac la output sizing): `funding, pnl, profit, margin, volume, quantity, tp, end, time_order, status`.

## 2. Nhan
- PRIMARY `collapse` = `status == STOP_LOSS_DONE` VA `profit <= -20`.  SECONDARY `sl` = `status == STOP_LOSS_DONE`.

## 3. Mo hinh (tham so CO DINH, khong tune)
- M1: LogisticRegression(C=1.0), chuan hoa z-score, impute median (fit tren train fold).
- M2: XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
  min_child_weight=20, random_state=42), NaN de xgboost tu xu ly.
- PRIMARY look = (M2, `collapse`). 3 to hop con lai chi mo ta.

## 4. Walk-forward
- 16 cut X1: 20220101 ... 20251001 (quy). Test fold i = lenh co `start` trong [cut_i, cut_i + 3 thang).
  Train = lenh co `end < cut_i - 72h` (nhan chi biet luc DONG => purge theo `end`, khong theo `start`).
- Bao cao: AUC pooled OOS toan cua so; AUC pooled theo NAM 2022/2023/2024/2025; AUC tung fold; kiem soat: 10 lan
  xao nhan (cung fold) => phan phoi AUC duoi H0.

## 5. QUY TAC QUYET DINH (chot)
> "DANG PRE-REG FILTER" <=> AUC pooled OOS cua PRIMARY look >= **0.65** toan cua so VA >= **0.60** o MOI nam 2023, 2024, 2025.
> Nguoc lai => "DONG: khong co tin hieu collapse entry-time ngoai thu selector da dung" — KHONG xay model.
Khong doi nguong, khong doi nhan, khong them feature/model sau khi thay so. 2022 (fold 0 it train) bao cao nhung khong quyet.

## 6. Mo ta bo sung (KHONG quyet dinh)
- Importance top-10 (M2). AUC don-feature cua `n_open_at_entry` va `symbolPred` (de biet selector/book da mang bao nhieu tin hieu).
- Counterfactual CHAN TREN: bo 10% lenh/fold co P(collapse) cao nhat => pnl SL tranh duoc vs pnl SM mat di (khong re-sim sizing).

## 7. Khong lam
Khong luu model, khong doi profile, khong cham 242, khong `git push`. Script: `research/analysis/collapse_probe.py` (logging).
