# ENTRY_CONFIRM tầng A — kết quả (2026-10-20): FAIL ⇒ ĐÓNG hướng 3

Prereg `docs/prereg/PREREG_ENTRY_CONFIRM.md` (99d1c1f8). Script/raw Oracle `~/claude_master/entry_confirm/{ec_a.py, ec_a.json, ec_a_clusters.parquet}`.

## Validate
- V1: ΣPnL 8 seed khớp `ts_mkt_ext.json` OFF lệch 0,00; Σ theo cụm = Σ theo chân; ~3 495 cụm/seed.
- V2: trung vị |P0/close(M) − 1| = 0,000 % (so nến M−1: 0,98 %, M+1: 0,77 %) ⇒ đúng phút, không lệch múi giờ.
- V3: thiếu giá A1/A2 0 %, A3 0,10 % (bỏ phút thiếu).
- Kiểm tay vòng lặp thuần 9 cụm × 3 arm (2023-06): 27/27 khớp.

## Kết quả (TB 8 seed)
| Arm | skip | PnL/cụm bỏ | PnL/cụm xác nhận | %TS bỏ/xác nhận | lost | ΔPnL_thô | chờ trung vị |
|---|---|---|---|---|---|---|---|
| **A1 2 %/4h** | **1,4 %** | −2,8 | +32,0 | 43,6 / 15,1 % | +27,8k | **−27,7k** | 10' |
| A2 1 %/1h | 0,8 % | +8,7 | +31,7 | 25,3 / 15,4 % | +21,1k | −21,3k | 5' |
| A3 3 %/24h | 0,5 % | +1,1 | +31,7 | 62,9 / 15,2 % | +29,8k | −29,8k | 20' |

A1 theo seed: ΔPnL −24,5k…−31,6k (0/8 dương). Theo năm: 2022 −2,5k · 2023 −12,9k · 2024 −5,9k · 2025 −5,4k (0/4 dương).

## Luật (A1)
D1 FAIL (skip 1,4 % < 5 %) · D2 FAIL (PnL_skip < 0 chỉ 5/8) · D3 FAIL (−27,7k, 0/8, 0/4) ⇒ **FAIL, đóng hướng 3, không thử c/W khác**.

## Cơ chế
Chân mở rơi vào phút biến động cực mạnh ⇒ nhịp bật +2 % gần như luôn xuất hiện (trung vị 10', p90 56') nên luật không lọc được gì. Nhóm bị bỏ đúng là xấu hơn (time-stop 43,6 % vs 15,1 %) nhưng chỉ 1,4 % cụm. Cái giá: vào đắt hơn trung vị +1,44 % (TB +0,85 %, 69 % cụm vào cao hơn P0) ⇒ mất ~28k/seed, lớn hơn nhiều sai số của giả định bỏ qua DCA/đường thoát.
Bài học: lợi thế nằm ở việc vào ĐÚNG phút cực trị; mọi độ trễ xác nhận đều trả giá bằng đoạn bật đầu.
