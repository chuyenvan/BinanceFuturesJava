# PRE-REG — SCREEN_WIDE: sàng rộng các anomaly đã công bố trên dữ liệu Binance (MASTER 2026-10-16)

**Bối cảnh.** Ngày 10-16, owner nhận xét cách làm hiện tại "đang chui vào tư duy cứng/đóng" và đề nghị tham khảo paper và mã nguồn mở, thử cả những thứ ít tiềm năng.

**Cách làm là một phễu hai tầng:**
- **Tầng 1 (file này):** sàng RỘNG và rẻ, chạy trên dữ liệu đã có hoặc dữ liệu Vision. Không có sim, không tune tham số; mọi tham số lấy đúng như paper.
- **Tầng 2:** chỉ dành cho các ứng viên sống sót ở tầng 1. Mỗi ứng viên có pre-reg chặt riêng, chạy sim hoặc forward.

**Sàng trên giai đoạn sau khi paper công bố.** Hầu hết paper dùng dữ liệu kết thúc trong 2020–2023. Vì vậy giai đoạn 2024-01 → 2026-09 vừa là thước đo out-of-sample đúng nghĩa, vừa cho thấy anomaly có bị bào mòn sau khi công bố hay không.

File này commit TRƯỚC khi tải dữ liệu.

## Nguồn tham khảo

- Quantpedia "The Seasonality of Bitcoin": 22:00–23:00 UTC là khung giờ mạnh nhất. Luật mua 21:00 bán 23:00 UTC cho 40,6 %/năm, Calmar 1,79 trên Gemini 2015-10 → 2023-06. Hiệu ứng mạnh hơn khi xu hướng tăng hoặc khi vol cao.
- Shen, Urquhart & Wang (2022, *Financial Review*) "Bitcoin intraday time-series momentum", dữ liệu tới 2020:
  - Lợi suất nửa giờ đầu sau khi Mỹ mở cửa (ONFH) dự báo cùng chiều lợi suất nửa giờ cuối (LH, 16:30–17:00 ET).
  - Lợi suất nửa giờ áp chót (SLH, 16:00–16:30 ET) dự báo ngược chiều.
  - Điểm hoà vốn 3–10 bps.
- Quantpedia "How to profitably trade Bitcoin's overnight sessions": phiên đêm ngoài 10:00–16:00 ET, luật MAX(10) (BTC ở đỉnh 10 ngày lúc 16:00 ET thì giữ qua đêm), giới hạn đêm Thứ Sáu→Thứ Hai, Thứ Hai→Thứ Ba, Thứ Ba→Thứ Tư. Dữ liệu tới 2024-10.
- Liu, Tsyvinski & Wu (2019/2020) "Common risk factors in cryptocurrency": market, size, momentum theo tuần.
- Các anomaly cắt ngang khác được nhắc nhiều trong văn liệu crypto: đảo chiều ngắn hạn, low-vol, MAX/lottery, cú sốc volume, khoảng cách tới đỉnh 52 tuần, beta thấp, funding.

## Dữ liệu

- **BTCUSDT và ETHUSDT perp 1m:** Vision UM monthly klines, 2021-01 → 2026-09.
- **Mọi perp USDT 1d:** Vision UM monthly klines.
- **Funding:** lake `vz-funding`.
- **Cách chia kỳ (thô, cố định):**
  - **E** (khám phá / kỳ có paper) = 2021-01-01 → 2023-12-31.
  - **C** (kiểm, sau công bố) = 2024-01-01 → 2026-09-30.

## Danh sách tín hiệu (cố định; với B/E: BTC là chính, ETH báo kèm)

**Chuỗi thời gian (TS) trên BTC/ETH.** Long-only nếu không ghi khác. Vào và ra theo giá close của phút.

| Mã | Luật |
|---|---|
| S1 | Long 21:00 → 23:00 UTC, mỗi ngày |
| S2 | S1, chỉ khi vol 30 ngày (lợi suất ngày) > trung vị 365 ngày của chính nó |
| S3 | S1, chỉ khi close 00:00 UTC > MA20 ngày |
| S4 | ONFH: r = lợi suất từ 16:00 ET ngày trước tới 10:00 ET (khung mở cửa Mỹ, có tính DST). Long 16:30 → 17:00 ET nếu r > 0, chỉ vào ngày NYSE mở cửa (thứ Hai–Sáu) |
| S5 | SLH: long 16:30 → 17:00 ET nếu lợi suất 16:00 → 16:30 ET < 0, chỉ ngày thứ Hai–Sáu |
| S6 | Overnight MAX10: lúc 16:00 ET các ngày thứ Sáu, Hai, Ba, nếu close ≥ max close 16:00 ET của 10 ngày trước thì long tới 10:00 ET ngày giao dịch kế tiếp |
| S7 | Cuối tuần: long từ 16:00 ET thứ Sáu tới 10:00 ET thứ Hai, không điều kiện |
| S8 | Quarter-hour imbalance (Kim & Hansen 2026): ở mỗi nến :00, imb = (2·taker_buy − vol)/vol. Long nếu imb > 0, short nếu < 0, giữ 4h, chỉ dùng các nến 00/04/08/12/16/20 UTC (lưới 4h, không chồng lệnh). Paper không nói dấu, nên báo cả hai dấu; lấy dấu theo kỳ E |

**Cắt ngang (X) trên perp USDT.**
- Universe tính point-in-time: trung vị quote volume 30 ngày ≥ 20 tr USD, đã niêm yết ≥ 60 ngày, không gồm stablecoin, có ≥ 30 coin.
- Cân lại mỗi thứ Hai 00:00 UTC.
- Báo hai dạng: (a) **long-only** decile trên, tính lợi suất vượt rổ equal-weight; (b) **L/S** decile trên trừ decile dưới.

| Mã | Tiêu chí xếp hạng decile trên |
|---|---|
| X1 | Momentum 21 ngày cao |
| X2 | Momentum 7 ngày cao |
| X3 | Đảo chiều 7 ngày: lợi suất 7 ngày THẤP |
| X4 | "Size" nhỏ, dùng quote volume 30 ngày thấp nhất trong universe |
| X5 | Funding 7 ngày thấp nhất (squeeze) |
| X6 | Vol 30 ngày thấp (low-vol) |
| X7 | MAX thấp: lợi suất ngày lớn nhất trong 30 ngày, thấp (né "xổ số") |
| X8 | Sốc volume cao: volume 7 ngày ÷ volume 90 ngày |
| X9 | Gần đỉnh 52 tuần (close / max 365 ngày cao) |
| X10 | Beta thấp so với BTC (90 ngày) |

## Chi phí

- Chính: taker perp 0,05 % mỗi chiều, tức 0,10 % mỗi vòng, tính trên turnover thực tế.
- Báo kèm: maker 0,02 % mỗi chiều.
- Không tính funding cho TS ngắn hạn (giữ ≤ 4h; riêng S6/S7 qua đêm có cộng funding thật).
- X tính cả funding: long trả funding, short nhận.

## Sống sót (đưa lên tầng 2)

Một tín hiệu sống sót khi đạt cả 4 điều kiện, dùng chi phí chính:

1. Sharpe ròng (tính theo ngày, nhân √365) ở kỳ E > 0,5.
2. Sharpe ròng ở kỳ C > 0,5.
3. Cùng dấu ở E và C.
4. Lợi nhuận ròng/năm ở C > 0.

Lưu ý:
- Có khoảng 18 tín hiệu × 2 dạng, nên dự kiến 1–2 tín hiệu sống sót chỉ do may rủi. Vì vậy sống sót **chỉ cho phép lên tầng 2**, không có nghĩa là GO.
- Báo **toàn bộ** kết quả, gồm cả tín hiệu chết. Ledger cộng 18.

## Kiểm dữ liệu

- **D1:** BTC 1m đủ phút ở ≥ 99,9 % số phút.
- **D2:** close 1d bằng close của phút 23:59 trong ngày (lệch ≤ 1e-6 tương đối).
- **D3:** universe X theo ngày có ≥ 30 symbol, áp dụng từ 2021-03.
