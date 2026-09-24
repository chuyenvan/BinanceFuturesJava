# F2 — Conditional exit: đo offline trên nhãn (Giai đoạn 1)

**Luật đo:** nếu tại giờ `H` lệnh chưa đạt lãi `θ` (`maxFav_H < θ`) thì cắt tại giờ `H`;
ngược lại giữ nguyên hành vi hiện tại (arm +7% → trailing, time-stop 168h).

**Vì sao hướng này** (3 phép đo độc lập hội tụ): `E0_EXIT_CF.md` — 147 lệnh time-stop
chết vì *không bao giờ chạy* (66.6% chưa từng vượt +3%, `maxFav` median 1.83% đạt ở giờ 4);
`E1_EXIT_RESULT.md` — cắt time-stop PHẲNG cải thiện đơn điệu nhưng cắt mù;
`F1_FLOW_RESULT.md` — `medP`=5.50 bất biến ở mọi độ sâu rank, chỉ `TSloss%` đổi.
⇒ Biến duy nhất là **xác suất coin có CHẠY hay không**, nên exit phải **có điều kiện**.

## Dữ liệu & join

- Nhãn: `/home/ubuntu/label_15m/funding_label_*.pb` (lưới 15m, horizon **4h/12h/24h/72h**,
  `maxFav_h` / `maxAdv_h` / `retEnd_h`), đọc qua `funding_label_pb.read_label` — **tái dùng**,
  không dựng lại giá từ `CLOSES_1H.bin` (E0 đã fail gate: spearman 0.77, lệch pnl −17.7%).
- Lệnh: `/home/ubuntu/java/devrun/C2b/storage/printDone.csv`, 970 lệnh `PREDICT_SYMBOL_TRADE`,
  toàn bộ `side=BUY`; 147 `STOP_LOSS_DONE` (= time-stop 168h) + 823 `STOP_MARKET_DONE`.
- Căn tick (theo `fsrun/label_align.py`): `ts = ((ms_GMT7 − 7h) // 900000) * 900000`.

**JOIN RATE = 970/970 = 100.00%** (ngưỡng dừng 95% — pass).

Hệ số quy đổi `K = median(pnl / (margin·profit/100)) = 0.8825` (n=964) dùng để ước lượng
pnl phản thực: `Δpnl ≈ margin · K · (retEnd_H − profit/100)`.

## Phân bố `maxFav` của nhóm time-stop (147 lệnh)

| H | median | p25 | p75 | %<3% |
|---|---|---|---|---|
| 4h | 0.0252 | 0.0135 | 0.0400 | 59.2 |
| 12h | 0.0303 | 0.0164 | 0.0456 | 49.0 |
| 24h | 0.0320 | 0.0182 | 0.0485 | 44.9 |
| 72h | 0.0336 | 0.0196 | 0.0515 | 40.1 |

Đọc: nhóm chết gần như **đứng yên sau giờ thứ 4** — median `maxFav` chỉ bò từ 2.52% (4h)
lên 3.36% (72h). Đó là chỗ luật có điều kiện bám vào.

## Lưới (H, θ)

Điều kiện cắt: `time_order > H` **và** `maxFav_H < θ`. Mẫu số: loser=147, winner=823.
`Δpnl` = ước lượng thay đổi pnl nếu cắt tại H (**KHÔNG** tính tái sử dụng margin được giải phóng).

| H | θ | n_cut_loser | %loser | n_cut_winner | %winner | lợi/hại | Δpnl_loser | Δpnl_winner | Δpnl_tot | GO |
|---|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.005 | 13 | 8.84 | 15 | 1.82 | 0.87 | +1116 | −1471 | −355 | |
| 4 | 0.010 | 27 | 18.37 | 44 | 5.35 | 0.61 | +3096 | −3446 | −351 | |
| 4 | 0.020 | 64 | 43.54 | 134 | 16.28 | 0.48 | +8272 | −10641 | −2368 | |
| 4 | 0.030 | 87 | 59.18 | 219 | 26.61 | 0.40 | +11530 | −16853 | −5323 | |
| 4 | 0.040 | 109 | 74.15 | 303 | 36.82 | 0.36 | +14051 | −21713 | −7662 | |
| 4 | 0.050 | 123 | 83.67 | 360 | 43.74 | 0.34 | +16202 | −24541 | −8339 | |
| 12 | 0.005 | 8 | 5.44 | 8 | 0.97 | 1.00 | +558 | −981 | −423 | |
| 12 | 0.010 | 18 | 12.24 | 22 | 2.67 | 0.82 | +2291 | −2486 | −195 | |
| 12 | 0.020 | 47 | 31.97 | 61 | 7.41 | 0.77 | +6173 | −6252 | −78 | |
| 12 | 0.030 | 72 | 48.98 | 100 | 12.15 | 0.72 | +8694 | −10171 | −1477 | |
| 12 | 0.040 | 100 | 68.03 | 150 | 18.23 | 0.67 | +10878 | −13820 | −2942 | |
| 12 | 0.050 | 114 | 77.55 | 191 | 23.21 | 0.60 | +11965 | −16061 | −4096 | |
| 24 | 0.005 | 7 | 4.76 | 5 | 0.61 | 1.40 | +186 | −817 | −631 | |
| 24 | 0.010 | 17 | 11.56 | 14 | 1.70 | 1.21 | +1603 | −2109 | −507 | |
| 24 | 0.020 | 42 | 28.57 | 40 | 4.86 | 1.05 | +3950 | −5231 | −1282 | |
| 24 | 0.030 | 65 | 44.22 | 70 | 8.51 | 0.93 | +5459 | −8702 | −3243 | **GO** |
| 24 | 0.040 | 93 | 63.27 | 91 | 11.06 | 1.02 | +6904 | −10905 | −4001 | |
| 24 | 0.050 | 111 | 75.51 | 119 | 14.46 | 0.93 | +7879 | −12683 | −4804 | |
| 72 | 0.005 | 5 | 3.40 | 1 | 0.12 | 5.00 | +210 | −290 | −80 | |
| 72 | 0.010 | 12 | 8.16 | 4 | 0.49 | 3.00 | +773 | −753 | +19 | |
| 72 | 0.020 | 37 | 25.17 | 11 | 1.34 | 3.36 | +2284 | −1554 | +730 | |
| 72 | 0.030 | 58 | 39.46 | 21 | 2.55 | 2.76 | +2815 | −2990 | −175 | |
| 72 | 0.040 | 86 | 58.50 | 29 | 3.52 | 2.97 | +3369 | −3676 | −307 | **GO** |
| 72 | 0.050 | 107 | 72.79 | 39 | 4.74 | 2.74 | +4055 | −4569 | −514 | **GO** |

## Cổng GO/NO-GO (chốt TRƯỚC khi nhìn số)

Điều kiện: tồn tại ô cắt **≥40%** lệnh time-stop trong khi cắt oan **≤10%** lệnh thắng.

**KẾT QUẢ: PASS** — 3 ô thoả: `(24, 0.03)`, `(72, 0.04)`, `(72, 0.05)`.

## RỦI RO — đọc trước khi tin lưới này

1. **`Δpnl_tot` âm ở gần như MỌI ô, kể cả 3 ô GO** (−307 / −514 / −3243 trên equity 60,390).
   Ước lượng first-order này **không** tính phần lợi thật của cơ chế: margin được giải phóng
   sớm và tái triển khai vào lệnh mới. Đó chính là kênh mà chỉ sim mới đo được. Nếu sim cũng
   ra âm ⇒ hướng này chết.
2. Cổng đã pre-register là cổng **tỉ lệ cắt**, không phải cổng pnl. Không sửa cổng sau khi
   thấy số (luật cứng #2) ⇒ vẫn sang Giai đoạn 2, nhưng kỳ vọng phải hạ.
3. Nhãn đo từ **close của tick 15m** chứa entry, không phải giá entry thật; có DCA
   (`lastentry` ≠ `entry`) làm lệch basis. `maxFav_H` là xấp xỉ, không phải peak thật của lệnh.
4. `H=4` và `H=12` bị loại vì **hại > lợi** (ratio 0.34–1.00): cắt sớm giết lệnh thắng nhanh
   hơn giết lệnh chết. Chỉ họ `H=72` có ratio ≈ 2.7–3.0.
5. Lưới 24 ô ⇒ có chọn lọc. 3 ô GO không độc lập (cùng họ H=72), nên đây là ~2 giả thuyết
   độc lập, không phải 24.

## Chọn ô cho Giai đoạn 2

Họ `H=72` áp đảo về tỉ số lợi/hại (2.74–2.97 vs 0.93 của `(24, 0.03)`).
- **F2_a** = ô tốt nhất `(H=72, θ=0.05)` — cắt 72.79% loser, oan 4.74% winner.
- **F2_b** = ô liền kề bảo thủ hơn `(H=72, θ=0.04)` — cắt 58.50% loser, oan 3.52% winner.

## Tái lập

```bash
python3 research/analysis/f2_cond_exit.py C2b   # -> /home/ubuntu/java/fsrun/f2_grid_C2b.csv
```
