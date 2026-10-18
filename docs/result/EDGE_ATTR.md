# EDGE_ATTR — edge K24+skipFull đến từ đâu, chịu chi phí thanh khoản tới đâu

Ngày 2026-10-18. Pre-reg `docs/prereg/PREREG_EDGE_ATTR.md` commit **4852f57e** (trước mọi phép join/đo; sau đó không đổi định nghĩa,
bucket hay luật). Script `research/edge_attr/edge_attr_{build,score}.py` + `ea_post1.py` (mô tả bổ sung). JSON `docs/result/edge_attr/`.
Chỉ đo: 0 sim Java, 0 đổi 242/shadow, 0 Binance REST, 0 đụng 2026 để chọn (HO4 W9 không đo được — kline 2026 không có trên Oracle).

## 0. Kết luận

1. **R1 = "edge rộng" (PASS).** Tập S0 = đợt ≤ 12 lệnh ∩ L24 ≥ 20M có ΣPnL **47 221 USD/seed**, CI95 [43 881; 50 561], 8/8 seed dương,
   PnL/lệnh = **0,96×** mức chung. Edge KHÔNG chỉ nằm ở đợt lớn hay coin kém thanh khoản.
2. **R2 = "phần lớn không phải beta" (PASS).** β với giỏ alt EW ≈ **0,85**, α ≈ **+2,35 %/lệnh**; tỉ trọng alpha A_alt **0,66 ± 0,02**
   (8/8 seed ≥ 0,63; theo BTC 0,81). Khoảng 1/3 lợi nhuận là beta hồi phục của thị trường alt trong lúc giữ lệnh.
3. **R3 / Q2 — KHÔNG "nhạy chi phí".** Nhóm L24 < 20M chỉ chiếm **10 %** ΣPnL (PnL/lệnh 44 USD, cao hơn trung bình 29).
   Impact √ (Y=1) làm ΣPnL giảm **−2,1 %** (vốn 10k), **−3,9 %** (35k), **−12,5 %** (350k); nhóm < 20M vẫn dương ở mọi kịch bản.
   Chi phí cộng thêm khứ hồi để nhóm < 20M hoà vốn ≈ **530 bps** (450–560 theo seed).
4. **Điểm yếu thật nằm ở thời gian, không ở thanh khoản:** ΣPnL theo năm (mean/seed) 2021 (từ 07) 5,9k · **2022 3,1k (sd 2,4k; nhóm ≥100M −0,4k)** ·
   2023 28,3k · 2024 31,0k · 2025 32,6k. Năm bear 2022 edge ≈ 0. Cùng chiều HO4 Q3 âm (ECMEAS).
5. Hệ quả cho owner: lo ngại "edge chỉ là coin kém thanh khoản + đợt bùng nổ" **không được dữ liệu ủng hộ** ở quy mô pilot.
   Rủi ro chính cần quản trị là **regime** (giai đoạn kéo dài edge ≈ 0 hoặc âm) và đuôi đợt lớn (BURST_RISK_1016) ⇒ kill-switch/DD bậc.
   Theo pre-reg §6: không chọn ngưỡng lọc nào từ kết quả này.

## 1. Kiểm hợp lệ

| kiểm | ngưỡng | đo | kết |
|---|---|---|---|
| V1 entry/close(M) | ≥ 99 % lệch ≤ 0,35 % | 99,32 %; 0 thiếu close(M) | PASS |
| V2 ΣPnL theo `end` vs ECMEAS | ≤ 1 USD/seed | max 4e-10 USD (8/8 seed) | PASS |
| V3 đủ 24h dữ liệu | ≥ 98 % | 98,08 %; có M,E trong ALT_EW 100 % | PASS |
| V4 đóng kín bucket | ≤ 1e-6 | 1,5e-16 | PASS |

- Bị loại theo V3: 543 chân (~68/seed), ΣPnL 4 424 USD/seed (**4,2 %** tổng), PnL/lệnh 65, thắng 90 %. Gần như toàn bộ là coin mới
  niêm yết < 24h (nbar trung vị 809; YB, MELANIA, MON, MOODENG, …), volume phần có được rất lớn (trung vị 171M) ⇒ không phải nhóm kém thanh khoản.
- HO4 W9 (mô tả): bỏ qua — Oracle không có kline 2026 (`~/vz_e1/raw` hết 2025-12). Không tải thêm để giữ phạm vi pre-reg.

## 2. Q1 — phân bố ΣPnL (mean qua 8 seed; tổng sau loại V3 = 100 934 ± 4 054)

| L24 lúc vào | n/seed | ΣPnL | tỉ trọng | PnL/lệnh | ROI trung vị | thắng |
|---|---|---|---|---|---|---|
| < 5M | 4 | 93 | 0,1 % | 22,5 | 2,7 % | 57 % |
| 5–20M | 230 | 10 264 | 10,2 % | 44,8 | 5,6 % | 93 % |
| 20–100M | 1 190 | 27 676 | 27,4 % | 23,3 | 5,4 % | 83 % |
| ≥ 100M | 2 052 | 62 901 | 62,3 % | 30,7 | 5,4 % | 84 % |

| cỡ đợt | n/seed | ΣPnL | tỉ trọng | PnL/lệnh |
|---|---|---|---|---|
| 1–5 | 1 053 | 23 689 | 23,4 % | 22,4 |
| 6–12 | 738 | 28 337 | 28,1 % | 38,3 |
| 13–24 | 1 685 | 48 909 | 48,4 % | 29,1 |

- L24 tại thời điểm vào bị đẩy lên bởi chính sự kiện (đợt vào lệnh trùng phút sập/biến động): trung vị L24 ~128–160M theo cỡ đợt.
  Đây là thanh khoản có thật lúc khớp, nhưng khác với "universe thanh khoản" dài hạn của P2-D (43 % ngoài universe REX).

## 3. Q2 — impact √ (c = Y·σd·√(N·s/L24), mỗi chân vào + ra)

| kịch bản | ΣPnL | Δ | nhóm < 20M | maxDD realized | cost/chân trung vị |
|---|---|---|---|---|---|
| gốc | 100 934 | — | 10 357 | −14,60 % | — |
| Y=0,5 · 10k | 99 871 | −1,1 % | 10 054 | −14,62 % | 0,7 bps |
| Y=1 · 10k | 98 808 | −2,1 % | 9 751 | −14,64 % | 1,4 bps |
| Y=1 · 35k | 96 956 | −3,9 % | 9 223 | −14,67 % | 2,6 bps |
| Y=1 · 350k | 88 354 | −12,5 % | 6 771 | −14,84 % | 8,2 bps |

Lưới phẳng chỉ cho nhóm < 20M: +25/50/100/200 bps ⇒ ΣPnL 100 445 / 99 956 / 98 978 / 97 022. Hoà vốn nhóm < 20M ≈ 531 bps;
để ΣPnL toàn bộ giảm 50 % phải cộng ≈ 2 584 bps riêng cho nhóm này.

Giới hạn (pre-reg §6): √-impact chưa hiệu chuẩn cho alt; chân thoát SL trong phút sập có thể trượt hơn mô hình; hậu kiểm bậc 1
(không tính lại sizing/MTM). Kết quả là độ nhạy — chỉ pilot tiền thật đo được chi phí thật.
