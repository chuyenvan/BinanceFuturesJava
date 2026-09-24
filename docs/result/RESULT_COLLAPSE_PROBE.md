# RESULT_COLLAPSE_PROBE — feature entry-time KHONG du doan duoc collapse: DONG, khong xay model filter

Pre-reg `docs/prereg/PREREG_COLLAPSE_PROBE.md` commit `7e1bbf6` (2026-09-11 16:46:30 +07), chay 18:3x cung ngay. Script
`research/analysis/collapse_probe.py`, log `/home/ubuntu/x1log/collapse_probe.out`. Khong sim, khong model luu, khong 2026.

## 1. Du lieu
1,996 lenh PREDICT_SYMBOL_TRADE cua X1_C3_FULL canonical. Nhan PRIMARY `collapse` (time-stop & ret <= -20%) = **123 (6.2%)**;
SECONDARY `sl` = 285 (14.3%). Join featv2 (39 feature gio): symId 100%, feature row **92.2%** (8% NaN = coin moi/thieu lich su,
xgb tu xu ly, logreg impute median). n_oos = 1,738 (fold 0-2 thieu train/positive => skip theo luat).

## 2. AUC walk-forward pooled OOS (16 fold X1, purge theo `end` - 72h)
| look | all | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| **M2 xgb, collapse (PRIMARY)** | **0.566** | 0.295 | **0.504** | **0.524** | **0.602** |
| M1 logreg, collapse | 0.549 | 0.537 | 0.454 | 0.484 | 0.575 |
| M2 xgb, sl | 0.542 | 0.368 | 0.466 | 0.467 | 0.628 |
| M1 logreg, sl | 0.555 | 0.588 | 0.498 | 0.508 | 0.607 |
Kiem soat H0 (xao nhan train x10, M2): AUC mean 0.452, sd 0.032, max 0.522 => PRIMARY 0.566 cao hon nhieu ~3.5 sd,
tuc CO mot chut tin hieu, nhung **xa nguong 0.65** va 2023/2024 ~0.50.

## 3. PHAN QUYET (PREREG muc 5)
> PRIMARY all=0.566 (< 0.65); 2023=0.504, 2024=0.524 (< 0.60); 2025=0.602. => **DONG: khong co tin hieu collapse entry-time
> ngoai thu selector da dung. KHONG xay model collapse-filter.**

## 4. Mo ta (khong quyet dinh)
- AUC don-feature: `dd_7d` 0.591 (+), `n_open_at_entry` 0.581 (**huong -**: book cang dong cang it collapse per-lenh — nguoc voi
  gia thuyet BOOKCAP, khop RESULT_BOOKCAP 0/3 PASS), `vol_7d` 0.577, `symbolPred` 0.572, `age_days` 0.505. Model 48 feature (0.566)
  **khong hon** feature don tot nhat (0.591) => khong co tuong tac nao dang hoc.
- Importance top: oi_z, rs_btc_7d, hour, dow, rs_mkt_7d, vol_7d — phan tan, khong feature nao troi.
- Fold 3-10 AUC dung 0.500: M2 voi `min_child_weight=20` khong tach duoc khi train chi co 5-30 positive => du doan hang so. Day la
  tham so da chot; M1 (khong bi) cho 0.549 nen ket luan khong doi. Ghi de lan sau khong chon min_child_weight lon voi nhan hiem.
- Counterfactual "bo top-10%/quy" **KHONG HOP LE**: du doan hang so lam quantile 0.9 chon ca fold (n=858/1738). Thanh phan lenh bi bo
  SL 15.2% vs nen 14.0% — model gan nhu khong lam giau loser. Net -35,773 (mat SM nhieu hon tranh SL) — chan tren, khong dung.

## 5. Y nghia
Dung nhu ky vong ghi truoc: collapse va winner la cung tap coin (dd_7d/vol_7d cao); thong tin entry-time da nam trong selector.
Collapse la hien tuong CUM (regime), khong doc duoc per-lenh. Khong con co so de ban "train them model" cho van de nay.
