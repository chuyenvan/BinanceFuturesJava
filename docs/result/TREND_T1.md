# TREND_T1 — họ trend long-only khung ngày (alpha bổ sung cho X14): KẾT QUẢ

Prereg: `docs/prereg/PREREG_TREND_T1.md` (commit 0744f943, sha256 c9f29a4e00829400c457bf3ea3550efece69f33c204c25e529343b6c3c6f435c), commit TRƯỚC mọi PnL. Code: `research/trend_t1/` (t1_resample, t1_x14, t1_core, t1_run, t1_valid, t1_indep, t1_report). Artefact: `docs/result/trend_t1/`.

## Verdict (đa kiểm định: 6 biến thể)
**Cả 6 biến thể NO-GO.** Không có ứng viên. Lý do chung: (i) kỳ KIỂM 2024–25 Sharpe ≤ 0,30 (G1 cần ≥ 0,8) — trend coin ngày lỗ/đi ngang trong 2025; (ii) maxDD −36 % … −58 % ở mọi biến thể (G2 cần ≥ −35 %); (iii) ghép 70/30 làm Sharpe KIỂM tụt từ 3,02 xuống 1,08–1,90 (G5 trượt 8/8 seed X14). Tương quan thấp (G4 đạt, 0,08–0,26) nhưng vô dụng khi alpha không dương ổn định.

| Biến thể | G1 | G2 | G3 | G4 | G5 | G6 | Verdict | seed X14 G4 | seed X14 G5 |
|---|---|---|---|---|---|---|---|---|---|
| V1 SMA100 | Trượt | Trượt | Trượt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |
| V2 SMA50 | Trượt | Trượt | Trượt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |
| V3 Donchian 20/10 | Trượt | Trượt | Đạt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |
| V4 Donchian 55/20 | Trượt | Trượt | Trượt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |
| V5 XS-MOM top5 + BTC>SMA100 | Trượt | Trượt | Trượt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |
| V6 V1 + BTC>SMA100 | Trượt | Trượt | Trượt | Đạt | Trượt | Trượt | **NO-GO** | 8/8 | 0/8 |

## Bảng số chính (net phí 0,10 %/chiều + funding thật; X14 = seed s2024, MTM b+unP)
| Biến thể | Kỳ | Sharpe | maxDD | CAGR | p95 ctrl | med ctrl | corr X14 | Sh ghép 70/30 | Sh X14 | DD ghép | DD X14 | Sh cost×2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | DEV | 0.19 | -55.3% | -2.9% | 0.32 | -0.19 | 0.20 | 1.24 | 1.74 | -17.1% | -17.0% | 0.14 |
| V1 | TEST | 0.01 | -48.7% | -13.2% | 0.45 | 0.00 | 0.15 | 1.29 | 3.02 | -13.0% | -6.4% | -0.02 |
| V2 | DEV | 0.62 | -49.2% | 19.8% | 0.56 | 0.27 | 0.14 | 1.57 | 1.74 | -16.4% | -17.0% | 0.56 |
| V2 | TEST | -0.09 | -51.3% | -15.4% | 0.18 | -0.21 | 0.09 | 1.31 | 3.02 | -13.2% | -6.4% | -0.14 |
| V3 | DEV | 0.98 | -39.2% | 41.7% | 0.71 | 0.45 | 0.12 | 1.84 | 1.74 | -15.2% | -17.0% | 0.94 |
| V3 | TEST | 0.30 | -40.5% | 4.4% | 0.07 | -0.32 | 0.09 | 1.90 | 3.02 | -7.8% | -6.4% | 0.26 |
| V4 | DEV | 0.66 | -36.3% | 20.6% | 0.83 | 0.43 | 0.24 | 1.58 | 1.74 | -18.0% | -17.0% | 0.64 |
| V4 | TEST | 0.08 | -36.7% | -4.4% | 0.27 | -0.22 | 0.10 | 1.70 | 3.02 | -7.9% | -6.4% | 0.06 |
| V5 | DEV | 0.40 | -42.4% | 8.3% | 0.54 | 0.09 | 0.26 | 1.43 | 1.74 | -13.8% | -17.0% | 0.35 |
| V5 | TEST | -0.43 | -57.9% | -26.6% | 0.15 | -0.23 | 0.11 | 1.08 | 3.02 | -15.1% | -6.4% | -0.49 |
| V6 | DEV | 0.97 | -46.0% | 37.2% | 0.93 | 0.67 | 0.08 | 1.88 | 1.74 | -12.0% | -17.0% | 0.93 |
| V6 | TEST | -0.18 | -54.2% | -19.7% | 0.28 | -0.13 | 0.12 | 1.20 | 3.02 | -13.0% | -6.4% | -0.21 |

DEV = 2022-05-01→2023-12-31 (610 ngày), TEST = 2024-01-01→2025-12-31 (731 ngày; X14 có tới 2025-12-29 nên phần so X14 dùng 729 ngày chung).
Ghi chú: V3 và V6 làm ghép 70/30 tốt hơn X14 ở DEV (+0,09…+0,14 Sharpe, DD tốt hơn) nhưng KIỂM đảo ngược mạnh (−1,1…−1,8) — đúng kiểu kết quả không bền, không tune tiếp.

## Mô tả
| Biến thể | Kỳ | exposure ngày % | gross TB | turnover/năm | lệnh/năm | % ngày X14 không leg | trend có vị thế trong các ngày đó % |
|---|---|---|---|---|---|---|---|
| V1 | DEV | 93.6 | 0.58 | 22.0 | 155 | 48.7 | 98.3 |
| V1 | TEST | 98.6 | 0.60 | 13.1 | 99 | 59.8 | 98.4 |
| V2 | DEV | 89.2 | 0.55 | 26.0 | 187 | 48.7 | 92.9 |
| V2 | TEST | 97.7 | 0.58 | 25.0 | 174 | 59.8 | 98.2 |
| V3 | DEV | 82.1 | 0.47 | 18.5 | 118 | 48.7 | 88.6 |
| V3 | TEST | 88.8 | 0.43 | 18.3 | 122 | 59.8 | 92.2 |
| V4 | DEV | 78.5 | 0.36 | 7.8 | 54 | 48.7 | 77.8 |
| V4 | TEST | 86.6 | 0.39 | 8.3 | 53 | 59.8 | 85.8 |
| V5 | DEV | 45.9 | 0.33 | 17.3 | 59 | 48.7 | 35.7 |
| V5 | TEST | 65.1 | 0.43 | 27.8 | 88 | 59.8 | 65.0 |
| V6 | DEV | 45.9 | 0.37 | 15.3 | 100 | 48.7 | 37.7 |
| V6 | TEST | 65.0 | 0.49 | 17.8 | 127 | 59.8 | 66.8 |

Bù độ thưa: X14 (s2024) không có leg ở 48,7 % ngày DEV / 59,8 % ngày TEST; trend lấp 36–98 % số ngày đó — tức "bù thưa" về exposure thì có, nhưng exposure đó không sinh lợi ròng ở KIỂM.

| Biến thể | Sh 2022 (5–12) | Sh 2023 | Sh 2024 | Sh 2025 | n lệnh | thoát cưỡng bức (delist) | lệnh bị thu nhỏ do gross≤1 |
|---|---|---|---|---|---|---|---|
| V1 | -1.93 | 1.32 | 0.46 | -0.59 | 458 | 2 | 2 |
| V2 | -1.02 | 1.58 | 0.08 | -0.28 | 661 | 1 | 13 |
| V3 | -0.84 | 2.05 | 1.14 | -0.97 | 442 | 1 | 4 |
| V4 | -1.25 | 1.69 | 0.60 | -0.71 | 198 | 1 | 4 |
| V5 | -0.31 | 0.68 | -0.62 | -0.23 | 276 | 0 | 0 |
| V6 | -1.53 | 1.46 | 0.07 | -0.51 | 421 | 1 | 0 |

Chỉ 2023 (và 2024 cho V3) là năm dương; 2022 và 2025 âm ở mọi biến thể. PnL theo coin (đơn vị vốn sleeve đầu = 1,0): lợi nhuận tập trung ở vài coin trend lớn (SOL 2023, XRP/DOGE/SUI cuối 2024); lỗ rải ở LTC, LDO, DYDX, WLD, AVAX… Chi tiết top/bottom 5 từng kỳ: `docs/result/trend_t1/report_tables.md`. Ngày tệ nhất: 2025-10-10 (V1 −19,5 % sleeve), 2022-11-08/09 (FTX).

## Validation
- V1 look-ahead: 5 ngày cắt (2022-08-15, 2023-03-31, 2024-01-07, 2024-11-30, 2025-06-15), nhân close/px01/qv sau ngày cắt ×3 ⇒ U, nhật ký quyết định (vào/ra/strength), danh sách lệnh vào/ra có ngày tín hiệu ≤ cắt giống hệt cho cả 6 biến thể: **ĐẠT** (và quyết định sau ngày cắt có thay đổi ⇒ phép thử có cắn).
- V2: ts int64 (day, ts_last, hourly t); ≤ 1440 dòng/sym-ngày; không trùng (sym,ts), ts%60000=0; 415 689 sym-ngày, 537 ngày thiếu phút (ghi nhận, không lấp), 512 ngày px01 không ở phút 1 (dùng dòng kế), lỗ toàn thị trường 2022-02-26..28 và 2022-04-01..02 trong warm-up (ffill close): **ĐẠT**.
- V3 tái lập ĐỘC LẬP (`t1_indep.py`, không import pipeline, đọc thẳng parquet 1m + funding) V1 và V3 đơn coin BTC/ETH/SOL: max |Δ equity ngày| = 0 / 0 / 0 / 0 / 2,2e-16 / 6,7e-16 (< 1e-6), 1 341 ngày: **ĐẠT**.
- V4 funding tay 3 lệnh V1: SOL 2023-10-17→2024-04-18 (535 rate dương/17 âm, long trả +0,026546 vốn); TRB 2023-10-01→2024-01-24 (473 dương/183 âm, long NHẬN −0,019086); TAO 2025-11 (44/28, −4,49e-6). Khớp pipeline sai số tương đối < 1e-9, dấu đúng (rate>0 ⇒ long trả) từng sự kiện: **ĐẠT**.
- V5 10 lệnh ngẫu nhiên (đủ biến thể): giá vào/ra = close nến 1m open 00:01 UTC đọc thẳng parquet, khớp tuyệt đối (|Δ| < 1e-12): **ĐẠT**.
- Funding: 527 074 sự kiện; độ phủ U 1 319/1 320 sym-tháng (thiếu BNXUSDT 2023-01 ⇒ mặc định 0,01 %/8h). Tổng 7 260 sự kiện mặc định cho các sym-tháng (của symbol từng thuộc U) mà file funding thiếu; chỉ 1 sym-tháng trong số đó rơi vào lúc symbol thuộc U.

## Lệch thiết kế (đã ghi trong prereg §11)
1. Loại thêm PAXG, XAU (neo vàng) như stable-like; USTC giữ.
2. Coin rời U khi sang tháng ⇒ thoát 00:01 ngày 1 (V1–V4, V6).
3. Donchian = sự kiện breakout đúng ngày; SMA = trạng thái; incumbents không bị thay.
4. X14 equity = MTM `b+unP` từ sim.out; seed trung vị s2024 chọn theo Sharpe X14 trước khi có PnL trend.
5. Control giữ nguyên ngày vào/ra ⇒ khớp cả timing tổng (gồm regime BTC); G3 chỉ đo giá trị chọn coin.
6. HO 2026 KHÔNG làm (tuỳ chọn; mọi biến thể NO-GO với biên lớn ở G1-TEST/G2, HO mô tả không đổi được verdict).

## Rủi ro / điểm nghi ngờ của chính agent
- Số X14 đo từ sim.out (Sharpe MTM 2022-05→2025-12 ≈ 2,05–2,41, CAGR ≈ 39–45 %, maxDD ≈ −12…−19 %) KHÁC số brief (Sharpe 1,80 / CAGR 27,6 % / maxDD −22,9 %): CHƯA GIẢI THÍCH (có thể khác kỳ/định nghĩa/vốn). Verdict không phụ thuộc: trend tự nó trượt G1/G2.
- Ghép 70/30 = cộng return ngày (ngầm rebalance ngày, không phí rebalance) — có lợi cho ghép; dù vậy vẫn trượt KIỂM.
- 2 824 sự kiện funding (0,5 %) không có giá giờ ⇒ fallback close ngày (với T trong ngày là close cuối ngày — sai lệch nhỏ chỉ ở số tiền funding, không ảnh hưởng tín hiệu); hầu hết là coin đã ngừng dữ liệu (MATIC, EOS, HNT, TOMO…) khi không giữ.
- Resample tháng lớn nhất peak RSS 5,2 GB (vượt nhẹ khuyến nghị 5 GB); chạy xong không lỗi, không bị kill.
- Kết quả rất nhạy theo năm (2023 tốt, 2022/2025 xấu): cỡ mẫu 3,7 năm/2 kỳ ⇒ không đủ để kết luận trend "không bao giờ" có ích; chỉ kết luận: 6 cấu hình đã prereg KHÔNG đạt cổng.
