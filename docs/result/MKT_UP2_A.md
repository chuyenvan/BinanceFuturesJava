# MKT_UP2 tầng A — kết quả (2026-10-20): L1/L2/L3 đều FAIL ⇒ ĐÓNG họ "gate dự báo hướng giỏ"

Prereg `docs/prereg/PREREG_MKT_UP2.md` (233d9679 + addendum 1 9c326745). Raw Oracle `~/claude_master/mkt_up2/{mv_a.py, mv_a.json, mv_a_pred.parquet}` (agent Opus, MASTER duyệt). 1 lần chạy đủ (+1 chạy thử 5 tháng chỉ để kiểm code).

## Validate
V1 look-ahead: cắt/phá dữ liệu sau mốc ⇒ 27 feature không đổi. V2 y3/mom1/mom7 panel khớp kline1m (28 phép so, sai số 0); y3 là simple return, feature ngày t dùng close ≤ 00:00 UTC t+1. V3 purge (114 refit). V4 giỏ đúng hạng. V5 không dữ liệu 2026 (label cuối 2025-12-28).

## Kết quả (LR chính)
| | L1 LIQ30>0 | L2 S1TOP10>0 | L3 S1TOP10−LIQ30>0 |
|---|---|---|---|
| AUC DEV (>0,55) | 0,523 | 0,534 | 0,531 |
| AUC VAL 2025 | 0,517 | 0,539 | 0,465 |
| E1 | FAIL | FAIL | FAIL |
| E3 Sharpe DEV / luôn mở / BTC / VAL | +0,80 / +0,24 / +1,53 / −1,43 | +1,62 / +0,91 / +2,05 / −0,27 | +0,23 / +0,91 / +2,05 / −0,80 |
| E5 market-neutral DEV / luôn mở / VAL | – | – | −0,37 / −1,10 / −1,52 |
| E2 size crash-buy ΔPnL DEV/seed | −5 964 (0/8) | −4 306 (0/8) | – |
| E4 corr ngày / % PnL sau ngày đợt | −0,02 / 24,8 % | +0,01 / **50,5 % (TRÙNG)** | −0,02 / 34,2 % |
| Tổng | FAIL | FAIL | FAIL |

Mô tả: corr return 3 ngày B1–ALT_EW 0,952, B2–ALT_EW 0,955, B1–B2 0,925 ⇒ giỏ top-K thanh khoản/selector ≈ cả thị trường; đổi label sang top-K không thoát được beta thị trường.

## Giới hạn / quyết định của agent (MASTER duyệt)
Train từ 2022-01 cho cả 3 label (feature giỏ B2 cần S1, có từ 2022-01) ⇒ L1 2022H2 ít mẫu; kể cả bỏ 2022H2 L1 vẫn FAIL (DEV 0,523, VAL 0,517). pred_s1 = winner REX C1 (đã NO-GO bên REX). E5 bỏ funding.

## Kết luận
Hướng thị trường/giỏ thanh khoản/alpha selector ở khung 3 ngày gần như không dự báo được bằng feature giá (AUC 0,52–0,55, VAL ≤ 0,54). Cùng MKT_UP (9c878b9c) ⇒ ĐÓNG họ gate dự báo hướng (không đổi label/H/feature).
