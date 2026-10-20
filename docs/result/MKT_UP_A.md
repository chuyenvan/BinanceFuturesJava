# MKT_UP tầng A — kết quả (2026-10-20): E1/E2/E3 FAIL ⇒ ĐÓNG

Prereg `docs/prereg/PREREG_MKT_UP.md` (8a4b8b1c). Script/raw Oracle `~/claude_master/mkt_up/{mu_a.py, mu_a.json, mu_a_pred.parquet}` (agent Opus chạy, MASTER duyệt). Chạy đúng 1 lần, không tune.

## Validate
V1 cắt/thay dữ liệu ≥ t: feature không đổi (10 ngày). V2 label (t, t+72h] khớp 1611/1611. V3 42 lần refit, train tới mốc−3d, scaler fit trên train. V4 20 cụm M→ngày UTC→P khớp.

## E1 — AUC (y = ALT_EW 72h > 0): FAIL
| Kỳ | AUC LR | AUC LGB (mô tả) |
|---|---|---|
| DEV-OOS 2022-07→2024-12 | **0,546** (< 0,55) | 0,542 |
| 2022H2 / 2023 / 2024 | 0,445 / 0,549 / 0,592 | 0,441 / 0,572 / 0,581 |
| VAL 2025 | 0,524 | 0,571 |

## E2 — size ×0,5 crash-buy khi P < 0,45: FAIL
ΔPnL thô TB −4 323/seed DEV (0/8 seed dương; 2022H2 −744, 2023 −3 251, 2024 −328), VAL 2025 −2 227. PnL/cụm theo tercile P (DEV): thấp +37,7 · giữa +17,4 · cao +50,4 ⇒ cụm ngày "thị trường yếu" vẫn lãi tốt; giảm size chỉ mất tiền.

## E3 — long ALT_EW 72h khi P > 0,55 (phí 0,10 %/chiều): FAIL
| Kỳ | Sharpe chiến lược | Sharpe hold EW | Bản BTC / hold BTC (mô tả) |
|---|---|---|---|
| DEV-OOS | +1,24 | −0,15 | +1,12 / +1,23 |
| VAL 2025 | **−1,19** (< 0) | −2,00 | −0,03 / −0,16 |
DEV đẹp nhưng VAL 2025 âm (alt sập đồng loạt) ⇒ trượt; giảm lỗ so với hold nhưng vẫn lỗ.

## Kết luận
E1 trượt (sát ngưỡng, ngưỡng đóng băng) và cả E2, E3 trượt ⇒ ĐÓNG hướng "model thị trường đi lên" (không đổi label/H/feature/ngưỡng). Nhất quán với REX S2a/TF/T2-MOM: tín hiệu hướng thị trường alt theo ngày yếu, và năm 2025 phá mọi cách long alt có điều kiện.
