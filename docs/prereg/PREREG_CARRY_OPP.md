# PRE-REG — CARRY_OPP: carry funding theo cơ hội, delta-neutral (long spot + short perp Binance) (MASTER 2026-10-16)

## Nguồn và bối cảnh

- Ngày 10-16, owner cho phép giao dịch Binance spot cùng chân short perp có hedge. Mục tiêu là một **dòng lợi nhuận mới, không chung nhịp** với hệ mua đáy.
- Nghiên cứu cũ ngày 08-31 (memory `carry-funding-verdict.md`, không có trong repo; file `_wfotmp/carry` không tìm thấy trên Oracle lẫn máy Windows) dùng 25 coin, 2019-09 → 2026-08. Kết luận khi đó:
  - Carry thường trực đã bị arbitrage gần hết: 2025–26 chỉ khoảng +1 %/năm.
  - Bản "bật khi TB funding 30 ngày > 0,01 %/8h" cho khoảng +6,9 %/năm, tính trên toàn kỳ, và chỉ ở trong thị trường khoảng 25 % thời gian.
  - Bản đó được chọn sau khi thử **5 biến thể**, chưa có pre-reg và chưa có holdout.
- ⇒ File này là **lần thử có pre-reg đầu tiên** cho biến thể cơ hội. Luật được giữ y nguyên luật tốt nhất của 08-31, không chỉnh. Phần đánh giá sạch gồm:
  - (i) universe ngoài nhóm thanh khoản lớn nhất, để gần như không trùng 25 coin cũ;
  - (ii) holdout 2026-01 → 09;
  - (iii) forward.
- File này commit TRƯỚC khi tải dữ liệu.

## Dữ liệu

- **Funding:** lake `vz-funding` (Vision fundingRate UM; tiêu chí causal là theo fundingTime thật).
- **Kline:** Vision `klines/1d` cho spot (`data/spot/monthly/klines/<S>/1d`) và cho perp UM (`data/futures/um/monthly/klines/<S>/1d`).
- **Symbol hợp lệ:** có cả spot `XXXUSDT` lẫn perp `XXXUSDT`, và đã niêm yết ≥ 60 ngày ở cả hai. Loại stablecoin và coin gắn tỉ giá (USDC, FDUSD, TUSD, BUSD, DAI, EUR, PAXG, WBTC…).
- **Kỳ:**
  - DEV 2021-01-01 → 2025-12-31 (trùng thời kỳ với nghiên cứu 08-31, nên ghi rõ: universe chính sẽ trùng một phần với 25 coin cũ);
  - HO 2026-01-01 → 2026-09-30.

## Luật (cố định, đánh giá hằng ngày lúc 00:00 UTC, mọi dữ liệu dùng có thời điểm < 00:00)

| Thành phần | Quy định |
|---|---|
| Tín hiệu | s(i,t) = Σ funding(i) trong 30 ngày trước t ÷ 90 (quy về /8h). Chỉ dùng funding đã settle |
| Thanh khoản | trung vị quote volume 30 ngày của perp ≥ 20 tr USD **và** của spot ≥ 5 tr USD |
| Bật | s > 0,0001 và đạt thanh khoản ⇒ mở cặp: long spot + short perp, notional bằng nhau |
| Tắt | s ≤ 0,0001 hoặc trượt khỏi điều kiện thanh khoản ⇒ đóng cả hai chân |
| Danh mục | tối đa 10 cặp, ưu tiên s cao nhất. Equal-weight trên vốn: mỗi cặp dùng vốn = 1/10 × Vốn |
| Vốn mỗi cặp | notional × **2,0** (chính; tức margin chân perp = 100 % notional) và × 1,5 (báo kèm) |
| Phí | cả 4 chân, tính khứ hồi: taker spot 0,10 % + taker perp 0,05 % mỗi chiều ⇒ **0,30 %** notional mỗi vòng (chính). Bản maker 0,15 % chỉ báo kèm |
| PnL ngày của cặp | funding nhận trong ngày (short nhận khi funding > 0, trả khi < 0) + (ret_spot − ret_perp) × notional theo close ngày − phí |
| Cân lại margin | lỗ chân perp từ lúc vào > 50 % margin ⇒ cân lại: tốn phí 0,15 % notional, ghi số lần. Nếu lỗ vượt 100 % margin trong một ngày (dùng high ngày) ⇒ coi là **thanh lý**: mất margin, ghi sự kiện |
| Phần vốn chưa dùng | lãi 0 |

## Thước đo (tính trên Vốn)

- CAGR, Sharpe (theo ngày, nhân √365).
- maxDD theo MTM ngày.
- % ngày có vị thế, số vòng giao dịch, số lần cân lại / thanh lý.
- Lợi nhuận theo năm.
- Tương quan PnL ngày với hệ mua đáy (gqsf-a1, PnL realized theo ngày đóng). Báo thêm PnL carry trong các tháng hệ mua đáy có 0 lệnh.

## Tiêu chí GO (tất cả phải đạt)

| | Tiêu chí |
|---|---|
| G1 | DEV (universe chính, vốn ×2,0, phí 0,30 %): CAGR ≥ 5 %/năm **và** Sharpe ≥ 1,5 |
| G2 | DEV maxDD ≥ −10 %, và không năm nào < −2 % |
| G3 | **Universe độc lập:** loại 30 symbol có quote volume perp trung bình 2021 lớn nhất (thay cho 25 coin cũ), phần còn lại có DEV CAGR > 0 và Sharpe ≥ 1,0 |
| G4 | HO 2026: CAGR > 0. Nếu HO không mở vị thế nào ⇒ G4 = "chưa quan sát", không chặn, nhưng phải ghi rõ |
| G5 | Tương quan ngày với hệ mua đáy ≤ 0,3 |
| G6 | 0 sự kiện thanh lý ở vốn ×2,0 |

- Đạt cả 6 ⇒ đề xuất làm executor thật: spot + perp, paper trước trên 242 hoặc Oracle (chỉ khi owner duyệt).
- Thiếu bất kỳ điều kiện nào ⇒ NO-GO. Không tune lại ngưỡng s, cửa sổ 30 ngày, N, hay ngưỡng thanh khoản.

## Kiểm dữ liệu

- **C1 funding:** trên BTC/ETH, tổng funding mỗi năm khớp số của 08-31 (BTC +11,6 %/năm gộp toàn kỳ ± 2 điểm %).
- **C2 kline:** close perp và close spot lệch nhau ≤ 2 % ở ≥ 99 % số ngày.
- **C3 tín hiệu causal:** mọi funding dùng có fundingTime < t.
- **C4 phủ:** có số liệu cho mọi ngày của mọi symbol hợp lệ, hoặc báo rõ chỗ thiếu.

## Addendum 1 (2026-10-16, viết TRƯỚC khi chạy `run`; chưa tính outcome nào)

**Kết quả kiểm C1–C2:**
- C1 PASS: tổng funding BTC trung bình 11,9 %/năm cho 2021–2025, so với 11,6 % ở nghiên cứu 08-31.
- C2 FAIL: chỉ 94,9 % số ngày có close perp và close spot lệch nhau ≤ 2 %.

**Chẩn đoán** (`co_diag.py`, không đọc PnL):
- Lỗi tập trung ở 17/410 symbol, mỗi symbol lệch > 2 % ở hơn 20 % số ngày: BTCST, BTS, CTK, CVC, CVX, DGB, FTT, GLMR, IDEX, MDT, RAD, RAY, SC, SLP, SNT, STPT, STRAX.
- Nguyên nhân: perp đã bị delist nên giá đứng yên, ticker bị tái sử dụng, hoặc spot và perp là hai tài sản khác nhau.
- Bỏ 17 symbol này thì C2 = **99,74 %** ⇒ PASS.
- Phần lệch còn sót lại đa số là giá perp stale sau delist (ví dụ A2Z, CHESS, ALPACA).

**Sửa (không đổi tín hiệu, ngưỡng hay tiêu chí GO):**
1. Loại 17 symbol trên khỏi universe.
2. Chỉ được vào cặp trong ngày hợp lệ: quote volume perp > 0, quote volume spot > 0, và |perp/spot − 1| ≤ 2 %.
3. Nếu cặp đang giữ gặp ngày không hợp lệ (qv perp = 0 hoặc lệch > 10 %): đóng cặp theo giá ngày trước, tính phí, và đếm vào `n_invalid_close`. Đây là xấp xỉ cho rủi ro delist; ghi rõ là xấp xỉ.

Chi tiết thực thi cũng nằm trong docstring của `co_bt.py` (commit a0947f84).
