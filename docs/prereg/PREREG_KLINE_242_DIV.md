# PRE-REG — KLINE_242_DIV: điều tra lệch kline 1m Aerospike 242 vs Binance (agent KDIV, 2026-10-10)

Chốt TRƯỚC khi đo. Đã nhìn trước khi chốt: số HO3 (e79dbe9b) / AUD26 (885f2b5e); code ingest (git); probe 5 key (gen/LUT, không giá trị). CHỈ ĐỌC 242 (Aerospike `ticker.kline_1m_opt`, log, file đang chạy); không sửa/restart; 0 sim, 0 Kaggle, 0 Java.

## Nguồn / định nghĩa
- 242: key `yyyyMMdd-HHmm` (+07), bin `data` (snappy proto) = open, high, low, close, totalUsdt (float32). Meta: `gen`, LUT (`exp.LastUpdateTime`). volume base / trades KHÔNG lưu ⇒ báo N/A.
- Vision: `data.binance.vision/.../futures/um/{monthly|daily}/klines/<S>/1m/` (tháng 2026-04..09; ngày 10-01..10-09). quoteVolume (cột 7) ↔ totalUsdt.
- REST: `fapi/v1/klines` công khai, 1 call/(symbol, ngày UTC) limit 1500, ≥ 1 s giữa call, tổng ≤ 120 call.
- KHỚP trường ⇔ float32(a)==float32(b) hoặc |a−b| ≤ 1e-8·|b| (như HO3). Ô = (symbol, phút) có ở cả 2 nguồn. Thiếu/thừa đếm riêng.
- Mẫu symbol: top-50 theo totalUsdt 242 trên 2026-03-10..03-16 (mỗi 10′; trước điểm gãy, 242≡Vision theo HO3) ∪ mọi symbol có dòng printDone `ho26-k24-s-s42` hoặc `ho26-b0-s-s42` với start ∈ [2026-01-01, 2026-07-01) +07. Cửa sổ D1: 2026-04-01 00:00 → 2026-10-10 00:00 +07.

## D1 — đo (không tham số tự do)
- Theo ngày +07: % ô lệch từng trường O/H/L/C/Q, % ô lệch ≥1 trường; độ lớn |a/b−1| p50/p99 trên ô lệch (histogram log, sai số bin ≤ 2,4%).
- Theo biến động phút Vision v=(H−L)/O: bậc [0, 0.1%, 0.2%, 0.5%, 1%, 2%, 5%, ∞).
- Theo thời điểm ghi: off = LUT − (phút + 60 s) theo bậc (<−30, −30..0, 0..2, 2..5, 5..10, 10..20, 20..60, ≥60 s) và gen; key có LUT thuộc đợt ghi lại hàng loạt (nếu có) báo riêng.
- Phân loại ô lệch (chốt trước): OPENEQ_VOLLOW (O khớp, Q242 < 0,99·QV), VOL0 (Q242=0), INSIDE (H242≤HV và L242≥LV), CLOSE_ONLY, SHIFT (242 phút t khớp OHLC Vision t±1), OTHER.
- Điểm gãy: chuỗi % ô khớp-đủ-5-trường theo phút (mẫu) 2026-04-24→04-26 +07; điểm gãy = phút đầu tiên mà trung bình 60′ kế tiếp < 99% và mọi giờ sau đến 04-26 00:00 < 99%; kèm phút lệch đầu tiên và bước nhảy gen/LUT.

## D2 — ai đúng
- 40 (symbol, ngày UTC) có nhiều ô lệch nhất (≤ 2 /symbol, rải tháng 4..10) + 20 ngẫu nhiên (seed 20261010) trong (symbol, ngày) có ≥ 1 ô lệch. REST cả ngày ⇒ % khớp REST↔Vision, REST↔242. Nguồn "đúng" ⇔ khớp REST ≥ 99,99%; nguồn kia "sai".

## D3 — nguyên nhân: đọc code/git/log (không đo). Giả thuyết đã thấy trước khi đo: 2cbf27c9 (2026-04-25 09:25) đổi `BinanceDataIngestor` từ websocket `TickerIngestor2Aerospike` sang REST-polling `TickerIngestor2AerospikeNew`; kiểm bằng D1 (mẫu OPENEQ_VOLLOW, LUT trong phút) + log.

## D4 — ảnh hưởng
- (a) live 2026-05-01→06-30: 33 feature gate (port `devexport_202609`, md INLINE cả 2 nhánh, funding 242 chung) từ kline 242 vs kline Vision (toàn bộ symbol 242) ⇒ p15 = ONNX fold_20 (`Model_Regressor_Return15M.onnx`, md5 8ec99757). Ứng viên = top-24 sp bins HO26 (`bins2026Ax`, ffill ≤ 15′); r, q_h (90 ngày, pct 0.999950829, warm-up 7 ngày) như `gate_offline`; q mỗi nhánh từ r nhánh đó, lịch sử trước 04-01 dùng chung nhánh 242 (≡Vision). Báo: % (phút, ứng viên) đổi PASS, % phút có ≥ 1 đổi, phân bố |Δp15|. Hạng ứng viên (S1) KHÔNG tính lại (cần pipeline S1); proxy: Jaccard top-24 theo return 60′ từ close 242 vs Vision.
- (b) DEV: nguồn `kaggle_data_hpo/ticker_*.bin.gz` (ghi provenance từ code/docs); kiểm mẫu 2025: ngày 01, 15 của 2025-03/06/09/12 × mẫu symbol vs Vision (cùng định nghĩa khớp).
- (c) HO26 T5–T6: % ô lệch trên symbol giao dịch HO26 (D1 lọc) + số chân vào/thoát rơi vào ô lệch.
- Không tune, không đổi định nghĩa sau khi thấy số; lỗi code sửa trước khi chốt thì ghi provenance.
