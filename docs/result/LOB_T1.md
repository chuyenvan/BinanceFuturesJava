# LOB_T1 — tín hiệu order book spot BNBUSDT: IC ngoài mẫu và chi phí

Prereg: `docs/prereg/PREREG_LOB_T1.md` @ `7ff68af57f6cfd761da623bc29d4721022610dee` (commit trước khi đo). Kernel: **`chuyendinh/lob-t1-signals`**, CPU, 14.386 GB CSV, 350.7 s.

- Grid 1 s: **604,800 giây** 2026-10-06T06:22:26Z → 2026-10-13T06:22:25Z, tỉ lệ giây có observation 99.26 %.
- Chia: discovery 362,880 s (60 %) → test 241,920 s (40 %), mốc chia **2026-10-10T11:10:26Z**.
- Spread book: median **0.1333 bps**, p10 0.1284, p90 0.1353.
- Chi phí áp: taker 10 bps / vòng, maker 4 bps / vòng (mỗi chiều 5 / 2 bps).

## 1. IC / R² / decile theo horizon (chỉ số trên TEST)

| signal | h | IC disc | IC test | NW t | R² OOS | decile D10−D1 (bps) | net taker | net maker |
|---|---|---|---|---|---|---|---|---|
| imb1 | 1s | 0.3639 | 0.3290 | 121.7 | 0.05885 | 0.560 | -9.44 | -3.44 |
| imb5 | 1s | 0.3421 | 0.3032 | 115.5 | 0.05246 | 0.520 | -9.48 | -3.48 |
| ofi1 | 1s | 0.2545 | 0.2285 | 11.3 | -0.16853 | 0.410 | -9.59 | -3.59 |
| micro_bps | 1s | 0.3635 | 0.3291 | 122.2 | 0.05928 | 0.547 | -9.45 | -3.45 |
| slope_imb | 1s | 0.2995 | 0.2548 | 97.2 | 0.03498 | 0.440 | -9.56 | -3.56 |
| depth_bps5 | 1s | 0.0082 | 0.0100 | 2.4 | 0.00002 | 0.016 | -9.98 | -3.98 |
| imb1 | 10s | 0.2958 | 0.2996 | 56.6 | 0.04546 | 1.432 | -8.57 | -2.57 |
| imb5 | 10s | 0.2854 | 0.2828 | 52.3 | 0.04200 | 1.424 | -8.58 | -2.58 |
| ofi1 | 10s | 0.1547 | 0.1466 | 5.3 | -0.07412 | 0.925 | -9.07 | -3.07 |
| micro_bps | 10s | 0.2955 | 0.2994 | 57.7 | 0.04581 | 1.412 | -8.59 | -2.59 |
| slope_imb | 10s | 0.2514 | 0.2394 | 44.2 | 0.02987 | 1.286 | -8.71 | -2.71 |
| depth_bps5 | 10s | 0.0030 | 0.0012 | 0.2 | -0.00003 | 0.008 | -9.99 | -3.99 |
| imb1 | 60s | 0.1208 | 0.1295 | 17.1 | 0.01027 | 1.663 | -8.34 | -2.34 |
| imb5 | 60s | 0.1147 | 0.1238 | 15.5 | 0.00967 | 1.592 | -8.41 | -2.41 |
| ofi1 | 60s | 0.0599 | 0.0600 | 4.4 | -0.01126 | 1.016 | -8.98 | -2.98 |
| micro_bps | 60s | 0.1204 | 0.1294 | 17.7 | 0.01036 | 1.636 | -8.36 | -2.36 |
| slope_imb | 60s | 0.1033 | 0.1055 | 13.1 | 0.00717 | 1.395 | -8.61 | -2.61 |
| depth_bps5 | 60s | 0.0017 | -0.0135 | -1.5 | -0.00014 | -0.094 | -10.09 | -4.09 |
| imb1 | 300s | 0.0678 | 0.0445 | 3.2 | 0.00199 | 2.848 | -7.15 | -1.15 |
| imb5 | 300s | 0.0599 | 0.0357 | 2.8 | 0.00146 | 3.088 | -6.91 | -0.91 |
| ofi1 | 300s | 0.0402 | 0.0377 | 3.3 | 0.00205 | 2.659 | -7.34 | -1.34 |
| micro_bps | 300s | 0.0677 | 0.0450 | 3.3 | 0.00212 | 2.657 | -7.34 | -1.34 |
| slope_imb | 300s | 0.0513 | 0.0310 | 2.3 | 0.00100 | 1.741 | -8.26 | -2.26 |
| depth_bps5 | 300s | -0.0148 | -0.0676 | -1.6 | -0.00089 | -2.048 | -7.95 | -1.95 |
| imb1 | 900s | 0.0440 | 0.0422 | 1.9 | -0.00171 | 2.623 | -7.38 | -1.38 |
| imb5 | 900s | 0.0325 | 0.0319 | 1.4 | -0.00204 | 3.384 | -6.62 | -0.62 |
| ofi1 | 900s | 0.0279 | 0.0133 | 0.3 | -0.00323 | 1.607 | -8.39 | -2.39 |
| micro_bps | 900s | 0.0431 | 0.0419 | 1.9 | -0.00170 | 2.090 | -7.91 | -1.91 |
| slope_imb | 900s | 0.0269 | 0.0287 | 1.3 | -0.00229 | 1.705 | -8.30 | -2.30 |
| depth_bps5 | 900s | -0.0198 | -0.0950 | -1.6 | -0.00218 | -5.124 | -4.88 | 1.12 |

## 2. Theo regime (h = 10 s, test)

| signal | vol thấp | vol cao | phút sập |
|---|---|---|---|
| imb1 | 0.3494 | 0.2436 | — |
| imb5 | 0.3292 | 0.2307 | — |
| ofi1 | 0.1445 | 0.1493 | — |
| micro_bps | 0.3494 | 0.2431 | — |
| slope_imb | 0.2778 | 0.1975 | — |
| depth_bps5 | 0.0044 | -0.0054 | — |

Ngưỡng phút sập |return 1m| ≥ 37.53 bps (phân vị 99,9 của discovery), chiếm 0.019 % số giây test. n giây: vol thấp 161907, vol cao 80013.

## 3. Kiểm hợp lệ

| kiểm | kết quả |
|---|---|
| V1 placebo (return xáo trộn, 3 lần) | IC gốc 0.2996; |IC| xáo trộn max 0.0029 |
| V2 control ngẫu nhiên (10 vector) | mean 0.00007, sd 0.00173 (lý thuyết 0.00203), n 241,910 |
| V3 IC theo ngày (`imb1`, 10 s) | xem bảng dưới |
| V4 số học chi phí | PASS |
| V5 số mẫu | n_1s 604,800 (kỳ vọng 604,800), n_60s 10,080 |
| V6 parse độc lập (csv thuần vs pandas) | max|Δimb1| 0.0000000000, max|Δmicro| 0.0000000000 trên 2,000 dòng |
| V7 ổn định 4 quý của test (`imb1`, 10 s) | Q0 0.356, Q1 0.351, Q2 0.316, Q3 0.230 |

| ngày UTC | IC imb1 (10 s) | n |
|---|---|---|
| 2026-10-10 | 0.3539 | 46,174 |
| 2026-10-11 | 0.3529 | 86,400 |
| 2026-10-12 | 0.2845 | 86,400 |
| 2026-10-13 | 0.1997 | 22,936 |

## 4. Phân bố feature (toàn bộ grid)

| signal | p1 | median | p99 | autocorr(1 s) |
|---|---|---|---|---|
| imb1 | -0.9988 | 0.0263 | 0.9988 | 0.796 |
| imb5 | -0.9968 | 0.0419 | 0.9967 | 0.816 |
| ofi1 | -2.7268 | 0.0000 | 2.7210 | 0.004 |
| micro_bps | -0.0675 | 0.0017 | 0.0673 | 0.786 |
| slope_imb | -0.9961 | 0.0551 | 0.9962 | 0.806 |
| depth_bps5 | 4.0677 | 14.7788 | 59.0755 | 0.876 |

## 5. Kết luận theo luật prereg §6

**G1** (`|IC_test| ≥ 0,02`, `|NW t| ≥ 3`, cùng dấu discovery) đạt ở:
- h = 1s: `imb1` IC 0.3290 (t 121.7); `imb5` IC 0.3032 (t 115.5); `ofi1` IC 0.2285 (t 11.3); `micro_bps` IC 0.3291 (t 122.2); `slope_imb` IC 0.2548 (t 97.2)
- h = 10s: `imb1` IC 0.2996 (t 56.6); `imb5` IC 0.2828 (t 52.3); `ofi1` IC 0.1466 (t 5.3); `micro_bps` IC 0.2994 (t 57.7); `slope_imb` IC 0.2394 (t 44.2)
- h = 60s: `imb1` IC 0.1295 (t 17.1); `imb5` IC 0.1238 (t 15.5); `ofi1` IC 0.0600 (t 4.4); `micro_bps` IC 0.1294 (t 17.7); `slope_imb` IC 0.1055 (t 13.1)
- h = 300s: `imb1` IC 0.0445 (t 3.2); `ofi1` IC 0.0377 (t 3.3); `micro_bps` IC 0.0450 (t 3.3)

**G2** (`net_taker > 0`): **không feature nào, ở bất kỳ horizon nào**. Net taker tốt nhất trong toàn bộ 30 ô (6 signal × 5 horizon) là **-4.88 bps**.

**G3** (prereg: dấu IC đúng ≥ 5/7 ngày): test chỉ phủ **4 ngày** (10–13/10), nên luật 7 ngày **không áp dụng nguyên văn được** — ghi nhận `imb1` đúng dấu **4/4** ngày (IC 0.354, 0.353, 0.284, 0.200).

**KẾT LUẬN: NO-GO.** Không cấu hình nào đạt G1+G2 ⇒ không đạt "GO (tradeable with taker)". Với maker: ô có net maker cao nhất là `depth_bps5` @ 900s = **1.12 bps**, nhưng NW t = -1.6 (không đạt G1) và đây là hiệu ứng thanh khoản không có dấu tiên nghiệm ⇒ **không đủ cơ sở cho GO-maker-only**; các tín hiệu literature mạnh (imb1/imb5/micro) vẫn âm sau phí maker ở mọi horizon.

Tín hiệu **có thật và mạnh về thống kê** (IC 0,30 ở 10 s, t 57, placebo 0,003, 4/4 ngày đúng dấu, decile đơn điệu), nhưng gross chỉ 0,56–3,4 bps trong khi một vòng lệnh tốn 4–10 bps ⇒ **chi phí lớn hơn edge 3–18 lần**. Đây là bài toán chi phí, không phải bài toán dự báo.

## 6. Vì sao IC rất cao mà vẫn không trade được

| h | gross D10−D1 tốt nhất (bps) | net taker (−10 bps) | net maker (−4 bps) |
|---|---|---|---|
| 1s | `imb1` 0.56 | -9.44 | -3.44 |
| 10s | `imb1` 1.43 | -8.57 | -2.57 |
| 60s | `imb1` 1.66 | -8.34 | -2.34 |
| 300s | `imb5` 3.09 | -6.91 | -0.91 |
| 900s | `imb5` 3.38 | -6.62 | -0.62 |

(`depth_bps5` @900 s có gross +5,1 bps nhưng NW t = −1,6 ⇒ không đáng tin, không đưa vào bảng.)

Edge **tăng theo horizon** (0,56 bps ở 1 s → ~3,4 bps ở 900 s) nhưng **chi phí là hằng số theo vòng lệnh**, nên mọi horizon đều âm sau phí taker; ngay cả sau phí maker 2 bps/chiều, mọi horizon vẫn âm (−0,6 bps ở 900 s đến −3,4 bps ở 1 s). Nói cách khác: tín hiệu **có thật** (IC 0,30 ở 10 s, decile đơn điệu, placebo ~0, IC đúng dấu ở 4/4 ngày test) nhưng **quá nhỏ so với phí** — đây là bài toán chi phí, không phải bài toán dự báo.

Ghi chú quan trọng: book là **spot**, nên giả định 5 bps taker / 2 bps maker là **lạc quan** (spot Binance retail là 10 bps/side; 2 bps maker là mức futures/VIP cao). Ngoài ra mô hình decile giả định **khớp được ở giá tốt nhất**, không mô phỏng xác suất fill và adverse selection của maker ⇒ net maker trong bảng là **cận trên**.

## 7. Cần gì để kiểm chắc hơn (và chi phí)

| thiếu gì | tại sao cần | cách lấy | chi phí ước tính |
|---|---|---|---|
| Event-level book (add/cancel/trade) hoặc L2 diff | mô phỏng queue position + fill maker, tính adverse selection thật | thu forward bằng WS `depth@100ms` + `trade` trên box; hoặc mua dữ liệu L2 lịch sử | tự thu: 0 phí license nhưng cần ~1–2 GB/ngày/symbol (Oracle chỉ còn ~16 GB ⇒ phải dùng object storage); mua: vài chục–vài trăm USD/tháng cho 1 sàn |
| ≥ 3 tháng dữ liệu, nhiều regime | 7 ngày không đủ để nói edge bền | mở rộng dataset (cùng nguồn) hoặc thu tiếp | dung lượng tuyến tính: ~14 GB/tuần/symbol ⇒ 3 tháng ≈ 180 GB/symbol |
| Fee tier thật của tài khoản | quyết định taker/maker nào áp dụng | lấy từ tài khoản Binance của owner | 0 |
| Impact model theo size | decile giả định size vô hạn ở top-of-book | dùng depth 100 level + mô hình impact (v.d. square-root) | 0 (đã có depth) |

**Điều kiện tối thiểu để có thể GO:** gross D10−D1 phải ≥ 2× phí/chiều + spread + buffer adverse selection; với phí maker thực tế ≥ 2 bps/chiều thì cần gross ≥ ~6–8 bps ở horizon giữ được > 1 phút. Hiện tại mức cao nhất là 3,4 bps (900 s) ⇒ còn thiếu ~2×.

## 8. Giới hạn của lần đo này

- Không mô phỏng fill/queue/adverse selection ⇒ cả net taker và net maker đều là **cận trên**.
- `R² OOS` của `ofi1` âm dù IC dương: OFI có đuôi rất dày (p1/p99 ±2,7), OLS tuyến tính không ổn định; IC (hạng) là thống kê đáng tin hơn cho OFI.
- Regime "phút sập" theo prereg (|r1m| ≥ 37,5 bps) chỉ có 45 giây trong test ⇒ **không đủ mẫu, chưa kết luận**; đã thay bằng so sánh vol thấp/cao (bảng §2).
- Grid 1 s làm mất chi tiết trong giây; horizon 1 s vì vậy là **cận trên lạc quan** về tốc độ.
- Chỉ 1 symbol (BNB); 4 symbol còn lại chưa đo tín hiệu.
- **Thứ tự thời gian cần ghi rõ:** số spot trong prereg (|dev| p50 0,067 bps, corr 0,9989) được kiểm cục bộ bằng 16 file kline Vision tải trong `/tmp` **trước** khi commit prereg, vì kernel A4 lúc đó trả 0 phút khớp spot (kline spot Vision đã chuyển sang timestamp micro-giây). Kernel A v4 (sửa chuẩn hoá µs) sau đó cho **đúng cùng con số** (-0,065 / 0,0667 / 0,99887) ⇒ không đổi kết luận.
- Số cuối cùng lấy từ kernel **`chuyendinh/lob-t1-v2`**: 2 lần push vào `lob-t1-signals` trả `status=error` với log rỗng (lỗi phía Kaggle), nên chạy lại bằng kernel mới; code không đổi.

