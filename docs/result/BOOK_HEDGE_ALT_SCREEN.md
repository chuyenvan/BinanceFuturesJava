# BOOK_HEDGE_ALT_SCREEN — screen tương quan 2024 (dữ liệu THIẾT KẾ, không phải outcome)

Ngày 2026-10-19. Chạy **trước** pre-reg `bf2a53d7`, chỉ dùng **2024** (năm khám phá); không đọc 2025/2026.
Nguồn: `~/vz_e1/raw/kline1m-2024-MM.parquet` (12 tháng, Vision), return ngày = log(close cuối ngày UTC).
Nhân tố so: **EW** = equal-weight alt (từ `~/claude_master/edge_attr/index.npz`, `ew_r`), **BTC** = `bt_r`.

Lọc: ≥ 350 ngày có ≥ 1 000 phút dữ liệu; median quote_volume ngày ≥ 1 triệu USD (bảng đầy đủ) —
luật chọn công cụ trong pre-reg dùng ngưỡng **10 triệu USD**.

## Top 20 theo corr(return ngày, EW) — 253 symbol đủ điều kiện
| hạng | sym | corr_ew | corr_btc | n_days | med_qv ($/ngày) | vol ngày % | beta_ew |
|---|---|---|---|---|---|---|---|
| 1 | **DEFIUSDT** | **0,959** | 0,721 | 365 | 1,6 M | 4,24 | 0,95 |
| 2 | ICXUSDT | 0,911 | 0,668 | 365 | 6,6 M | 4,53 | 0,96 |
| 3 | **ZILUSDT** | **0,908** | 0,673 | 365 | **11,9 M** | 4,69 | 0,99 |
| 4 | LITUSDT | 0,905 | 0,650 | 365 | 8,9 M | 5,32 | 1,12 |
| 5 | KAVAUSDT | 0,901 | 0,688 | 365 | 14,4 M | 4,60 | 0,96 |
| 6 | DENTUSDT | 0,900 | 0,701 | 365 | 6,4 M | 5,33 | 1,11 |
| 7 | IOSTUSDT | 0,898 | 0,664 | 365 | 6,7 M | 4,54 | 0,95 |
| 8 | FLOWUSDT | 0,897 | 0,671 | 365 | 17,0 M | 4,69 | 0,98 |
| 9 | C98USDT | 0,895 | 0,621 | 365 | 9,5 M | 5,01 | 1,04 |
| 10 | AXSUSDT | 0,894 | 0,658 | 365 | 37,7 M | 4,75 | 0,99 |
| 11 | FLMUSDT | 0,893 | 0,646 | 365 | 9,9 M | 5,44 | 1,13 |
| 12 | LINAUSDT | 0,889 | 0,615 | 365 | 17,8 M | 5,90 | 1,22 |
| 13 | HFTUSDT | 0,889 | 0,606 | 365 | 5,2 M | 4,83 | 1,00 |
| 14 | SNXUSDT | 0,888 | 0,640 | 365 | 18,9 M | 5,16 | 1,06 |
| 15 | ALPHAUSDT | 0,887 | 0,640 | 365 | 7,5 M | 5,22 | 1,08 |
| 16 | LRCUSDT | 0,882 | 0,625 | 365 | 9,3 M | 5,00 | 1,02 |
| 17 | BNTUSDT | 0,882 | 0,746 | 365 | 4,2 M | 3,80 | 0,78 |
| 18 | EGLDUSDT | 0,881 | 0,643 | 365 | 17,4 M | 4,46 | 0,91 |
| 19 | PORTALUSDT | 0,881 | 0,609 | 306 | 21,5 M | 6,42 | 1,26 |
| 20 | METISUSDT | 0,880 | 0,713 | 294 | 8,7 M | 6,18 | 1,21 |

## Đối chứng
| sym | corr_ew | corr_btc | med_qv ($/ngày) | ghi chú |
|---|---|---|---|---|
| ETHUSDT | 0,829 | 0,798 | 7 492 M | đã test: NO-GO |
| BTCUSDT | 0,750 | 1,000 | 16 239 M | đã test: NO-GO |
| BTCDOMUSDT | **−0,474** | 0,069 | 3,7 M | chỉ số dominance — **ngược chiều**, không dùng làm hedge |

## Đọc
- **BTC là công cụ tương quan kém nhất trong nhóm thanh khoản lớn** (0,750) — đúng trực giác "coin khác bám alt tốt hơn".
- `DEFIUSDT` cao nhất (0,959) nhưng thanh khoản chỉ **1,6 M/ngày** ⇒ loại theo luật ≥ 10 M.
- Sau lọc ≥ 10 M: **ZILUSDT 0,908** đứng đầu ⇒ chọn làm công cụ trong pre-reg.
- Toàn bộ 253 dòng: `~/claude_master/bookhedge_alt/screen_2024.json`, script `screen.py` (đã copy vào `research/analysis/`).
