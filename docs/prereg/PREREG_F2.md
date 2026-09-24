# PREREG F2 — Conditional exit: cắt lệnh KHÔNG CHẠY tại giờ H

Commit TRƯỚC khi chạy sim. Không sửa sau khi thấy kết quả (luật cứng #2).

## 1. Giả thuyết

Thời gian không phải biến quyết định — **việc coin có chạy hay không** mới là.
Cắt phẳng theo giờ (E1) cắt cả lệnh đang chạy; cắt **có điều kiện** (`maxFav < θ` tại giờ `H`)
chỉ chạm nhóm đã chết. Nếu đúng, margin được giải phóng sớm và tái triển khai sẽ bù thừa
phần lãi bị cắt oan.

Đo offline (`docs/experiment/F2_COND_EXIT_MEASURE.md`, commit `7bf80d3`, join nhãn **100.00%**):

| ô | %loser cắt (/147) | %winner cắt oan (/823) | lợi/hại | Δpnl_tot ước lượng |
|---|---|---|---|---|
| (72, 0.05) | 72.79 | 4.74 | 2.74 | −514 |
| (72, 0.04) | 58.50 | 3.52 | 2.97 | −307 |
| (24, 0.03) | 44.22 | 8.51 | 0.93 | −3243 |

Cổng Giai đoạn 1 (≥40% loser, ≤10% winner) **PASS**.

## 2. RỦI RO đã biết TRƯỚC khi chạy

1. **`Δpnl_tot` ước lượng ÂM ở cả 3 ô GO.** Ước lượng đó bỏ qua đúng kênh lợi duy nhất
   (tái triển khai margin) nên không kết luận được, nhưng nó KHÔNG ủng hộ giả thuyết.
   Xác suất null cao.
2. **`TSloss%` bị lệch TĂNG một cách cơ học**: lệnh bị cond-exit cũng mang status
   `STOP_LOSS_DONE` (cùng kênh "đóng lỗ khi chưa arm"), nên 39 lệnh thắng bị cắt oan sẽ
   nhảy vào tử số. Ta CỐ Ý không tạo status mới để tránh giấu lệnh sang xô khác. Vẫn giữ
   `TSloss%` là PRIMARY như đã đăng ký; nếu nó tăng thì phán quyết là NULL.
3. **`win%` cũng lệch GIẢM cơ học** cùng lý do. Giữ nguyên tiêu chí.
4. Nhãn dùng ở Giai đoạn 1 đo từ close của tick 15m chứa entry, không phải giá entry thật
   ⇒ ranh giới ô (H, θ) là xấp xỉ, không phải điểm tối ưu.
5. Lưới 24 ô ⇒ có chọn lọc; 3 ô GO cùng họ H=72 nên coi như ~2 giả thuyết độc lập.

## 3. Cơ chế

Trong `SimulatorMarketLevelTicker1MStopLoss.startUpdateOldOrderTrading`, ngay sau khối
`LOSER_TIME_STOP_HOURS` (cùng chỗ, TRƯỚC cổng profit-arm):

> nếu lệnh **chưa arm** (`priceSL == null`) **và** đã giữ > `COND_EXIT_HOURS` giờ kể từ leg đầu
> **và** `(maePeak − priceEntry)/priceEntry < COND_EXIT_MIN_FAV`
> ⇒ đóng market tại `min(open, close)`, status `STOP_LOSS_DONE`.

`maePeak` là đỉnh THẬT của cụm mà simulator đã theo dõi sẵn (chỉ đi lên, không reset qua
merge) — **tái dùng, không thêm state**. Ghi chú: trước F2 `maePeak` là đo-lường-only;
từ F2 nó tham gia quyết định **chỉ khi** cond-exit bật.

Hai tham số đọc qua `Cfg` (đặt trong **profile**, KHÔNG qua env — bẫy #2):
`SIM_COND_EXIT_HOURS` (0 = tắt, mặc định) và `SIM_COND_EXIT_MIN_FAV`.

## 4. Runs — ĐÚNG 3, không hơn

| tag | profile | COND_EXIT_HOURS | COND_EXIT_MIN_FAV |
|---|---|---|---|
| `F2_parity` | `profiles/c2b_min.properties` | (không khai) = 0, tắt | — |
| `F2_a` | `profiles/f2_a.properties` | 72 | 0.05 |
| `F2_b` | `profiles/f2_b.properties` | 72 | 0.04 |

Mọi tham số khác giữ y nguyên `c2b_min`. 1 dataset build dùng chung, chạy TUẦN TỰ (1 slot JVM).

## 5. Parity gate

`F2_parity` phải byte-identical C2b: md5 `printDone.csv` = `8f7afdfb27b15f5b6d4c886700def93c`,
`b:60390`, 970 lệnh. **Fail ⇒ dừng cả batch**, không chấm F2_a/F2_b.

## 6. PRIMARY (rate, n lớn) — chốt trước

1. `TSloss%` phải **GIẢM** so với C2b (15.15% = 147/970).
2. `mean(profit | STOP_MARKET_DONE)` **không được giảm quá 0.3pp** so với C2b (7.48%).
3. `win%` (tỉ lệ lệnh `profit > 0`) phải **TĂNG** so với C2b.

## 7. Ràng buộc CỨNG (vi phạm 1 cái ⇒ LOẠI)

- `maxDD ≤ 15%`
- underwater dài nhất `≤ 120 ngày`
- không năm âm
- không quý `< −5%`
- tổng số lệnh `≥ 600`

## 8. Equity KHÔNG phải tiêu chí

`sd(ΔCAGR)` exit params = 2.57pp; `E[max nhiễu]` N=50 = +7.2pp; DEV đã ~125 run.
Equity/CAGR báo cáo trong **mục riêng, dán nhãn "không phải tiêu chí"**.

## 9. Quy tắc quyết định

Chọn ô thoả **toàn bộ** PRIMARY **và** toàn bộ ràng buộc cứng. Nếu cả hai ô cùng thoả,
lấy ô cắt nhiều loser hơn (`F2_a`). Không ô nào thoả ⇒ **NULL, đóng hướng**, ghi vào QUEUE.
