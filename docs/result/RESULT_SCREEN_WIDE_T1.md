# RESULT SCREEN_WIDE tầng 1 — sàng 24 anomaly đã công bố trên Binance (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_SCREEN_WIDE.md`, commit 3e701549. Addendum 1 thêm họ G (fc9bed24). Addendum 2 về thực thi nằm trong docstring (4577aa95).
- **Code:** `research/screen/sw_data.py`, `sw_run.py`, `sw_diag.py`.
- **Output:** `~/claude_master/1016/screen/screen_result.json` và `sw_run.log`, `sw_diag.log`.
- **Kỳ:** E = 2021–2023, C = 2024–2026-09.
- **Phí chính:** taker 0,05 %/chiều. Bản phí maker là phần chẩn đoán.
- **Kiểm dữ liệu:**
  - D1: phút 1m đủ 100 %.
  - D2: close nến 1d trùng close phút cuối ngày ở 100 % số ngày.
  - Dữ liệu gồm 892 symbol.

## Kết quả (Sharpe ròng; E | C)

**Họ TS — BTC (ETH ghi chú cuối bảng)**

| Mã | E | C | Ghi chú |
|---|---|---|---|
| S1 21→23 UTC | −0,98 | −0,93 | Gross dương nhưng phí taker 0,1 %/ngày ăn hết. Bản maker: +0,20 \| +0,78 (+10 %/năm ở C) |
| S2 S1 + vol cao | +0,16 | −1,18 | |
| S3 S1 + trend | −0,93 | −1,46 | |
| S4 ONFH | −2,46 | −3,84 | Chết |
| S5 SLH | −2,62 | −3,23 | Chết |
| S6 overnight MAX10 | **+1,04** | +0,13 | Mạnh trong kỳ có paper, gần như tắt sau công bố. Bản maker: +1,13 \| +0,28 |
| S7 cuối tuần | +0,30 | +0,43 | Khoảng +10 %/năm cả hai kỳ. Bản maker: +0,39 \| +0,56 (+13 %/năm). Ổn định nhưng yếu |
| S8 quarter-hour | −3,2 | −5,6 | Phí giết |

ETH cho hình ảnh tương tự BTC: S6 +0,72 \| +0,24; S7 +0,22 \| +0,33.

**Họ X — cắt ngang, decile trên. LO = long-only vượt rổ; LS = long-short**

| Mã | LO E \| C | LS E \| C |
|---|---|---|
| X1 momentum 21 ngày | +0,46 \| **+1,00** | +0,41 \| **+1,81** |
| X2 momentum 7 ngày | −0,11 \| +1,21 | −0,28 \| +1,89 |
| X3 đảo chiều 7 ngày | +0,11 \| −1,67 | 0,00 \| −2,13 |
| X4 size nhỏ | +0,32 \| −0,17 | +0,59 \| −0,85 |
| X5 funding thấp | +0,66 \| +0,26 | **+1,80** \| −0,04 |
| X6 vol thấp | −0,38 \| +0,69 | −0,53 \| +0,23 |
| X7 MAX thấp | −0,40 \| +1,12 | −0,64 \| +0,32 |
| X8 sốc volume | +0,26 \| +0,49 | −0,24 \| +0,71 |
| X9 gần đỉnh 52 tuần | **+0,56 \| +0,83** ⇒ sống sót duy nhất | +0,11 \| +1,18 |
| X10 beta thấp | −0,20 \| −0,33 | −0,58 \| −0,26 |

**Họ G — grid long sau khi giảm dài (ý owner)**

| Mã | E Sharpe / năm / DD | C Sharpe / năm / DD | Thoát (trong đó stop) |
|---|---|---|---|
| G1 | −0,09 / −1,7 % / −25 % | −0,06 / −1,3 % / −38 % | 205 lần (105 stop) |
| G1b (không chờ đảo chiều) | −1,9 % / −36 % | −3,2 % / −55 % | |
| G1c (không stop) | −4,6 % / −43 % | −7,9 % / −59 % | |

- Thứ tự G1 > G1b > G1c cho thấy tín hiệu đảo chiều và stop đều có giúp.
- Nhưng cả ba bản đều không có edge: coin đã giảm 65 % trở lên thường vẫn tiếp tục chảy máu.

## Sống sót theo pre-reg: chỉ X9_LO, và nó KHÔNG bền

Chẩn đoán `sw_diag.py` (mô tả, không phải phép thử mới):

**X9:**
- Lùi lệnh vào trễ 1 ngày (thay vì vào ngay ở close dùng để tính tín hiệu): Sharpe vượt rổ ở E giảm 0,56 → **0,19**, ở C giảm 0,83 → 0,54.
- Lợi suất **tuyệt đối** long-only ≈ 0 ở E, +0,22 ở C.
- ⇒ Phần "edge" chủ yếu đến từ việc rổ alt chảy máu (bench 2022 −138 %, 2025 −97 %, tính tổng lợi suất tuần) và từ việc khớp ngay tại nến tín hiệu. Không đưa lên tầng 2 dưới dạng long-only.

**X1 (momentum 21 ngày) — trượt E sát nút (0,46), nhưng bền với độ trễ:**
- Vào trễ 1 ngày: vượt rổ E 0,25, C **0,98**; tuyệt đối E 0,35, C 0,47.
- Theo năm (tổng lợi suất tuần vượt rổ):

  | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|
  | +0,87 | −0,53 | +0,32 | −0,18 | **+1,05** | **+1,00** |

- Rất biến động. Thua ở 2022 và 2024 (momentum crash).

**Phí maker:** đổi rất ít với họ X (turnover 0,3–0,8/tuần). Với họ TS thì đổi lớn, vì S1/S7 chuyển sang dương.

## Đọc

1. Hầu hết anomaly giờ-trong-ngày của BTC (S1–S5, S8) **chết sau khi trừ phí thật**, hoặc đã tắt sau khi được công bố (S6).
2. Duy nhất hiệu ứng **cuối tuần (S7)** dương ổn định ở cả hai kỳ, khoảng +10–13 %/năm, Sharpe 0,3–0,56. Yếu, nhưng không đổi dấu.
3. **Momentum cắt ngang trên alt (X1/X2) rất mạnh trong 2024–2026.** LS Sharpe C 1,8–1,9; long top-decile vượt rổ Sharpe 1,0–1,2. Đây là dòng lợi nhuận *mua sức mạnh*, ngược chiều với hệ hiện tại (*mua sập*). Rủi ro momentum crash là có thật (2022, 2024).
4. Grid long sau giảm dài: KHÔNG có edge trên dữ liệu ngày. Không theo đuổi.

## Đưa lên tầng 2 (pre-reg chặt riêng)

- **T2-MOM (X1, có thể gộp X2):** vào lệnh trễ 1 ngày ở open; hedge bằng short BTC perp hoặc short rổ. Kiểm thêm:
  - capacity (decile trên chỉ khoảng 5–15 coin);
  - tương quan với hệ mua đáy;
  - hành vi khi momentum crash;
  - phí và slippage;
  - funding.
- **T2-WKND (S7):** chỉ khi có thể khớp maker. Ưu tiên thấp.

Ledger +24 (họ S 8, họ X 10 × 2 dạng tính là 10, họ G 3, tổng tính tròn 24 theo pre-reg).
