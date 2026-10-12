# PREREG_BACKCAST_RESERVOIR — kho holdout backcast trước DEV (agent BCAST, 2026-10-12)

**TRẠNG THÁI: BẢN NHÁP — CHƯA HIỆU LỰC. B0 phát hiện RÒ RỈ MODEL ở 2021-01..2021-06 ⇒ DỪNG trước B1, chờ MASTER chọn phương án (§4).** Chưa dựng dữ liệu, chưa đẩy kernel Kaggle nào, chưa chạy sim nào trên 2020–2021H1. Kết quả B0: `docs/result/bcast/BCAST_B0.md` (+ `.json`).

## 1. Phạm vi đề nghị ban đầu (MASTER)
- Kho niêm phong 2020-01-01 → 2021-06-30 (trước DEV 2021-07-01), dựng từ Binance Vision `futures/um` bằng công cụ gốc như HO4-P1 (exporter jar `99c5f040`, dataset `ho4p1-jar-exp`; jar sim `b7c89f09`; chuỗi hạ nguồn `ho4p1_chain.py`; OI; funding Vision; CLOSES_1H từ 1m; universe point-in-time).
- Mục đích DUY NHẤT: XÁC NHẬN ý tưởng đã chốt trên DEV. Không dùng để tìm/tune.

## 2. Nguồn + luật universe (giữ nguyên HO4, ADDENDUM-6 §6.2 + quyết định MASTER HO4-P0b #1)
- klines 1m monthly Vision (có từ 2020-01; 2019-12 KHÔNG có file nào), fundingRate monthly Vision (từ 2020-01), metrics daily Vision (OI: CHỈ BTCUSDT từ 2020-09-01, mọi symbol khác từ 2021-12-01 ⇒ 5 cột OI net015 + `rk_oi_delta24h` S1 = NaN toàn kho, như DEV 2021-07..11).
- Universe = bộ lọc LIVE `TickerIngestor2AerospikeNew` (USDT, `^[A-Z0-9]+$`, không BTCDOM/USDC) ∩ mapper 863, áp point-in-time; đuôi settle (volume 0 ≥ 1 440 phút tới kline cuối) cắt; thiếu mapper ⇒ drop + liệt kê (KHÔNG cấp id mới; nếu MASTER muốn giữ: id lỗ 752/753 trong bản mapper CỤC BỘ của sim, assert duy nhất và < 1000, KHÔNG ghi Aerospike 242); thiếu funding Vision ⇒ ở lại dữ liệu, loại khỏi giao dịch.
- Model đóng băng y HO4: gate 8 seed cut20260101, net015 ONNX `7921ceaf`, S1 `af706dc6`. Không retrain (trừ khi MASTER chọn §4-P2).

## 3. Luật mở kho (áp khi có hiệu lực)
1. Mỗi ý tưởng có pre-reg riêng commit TRƯỚC khi mở: giả thuyết, cấu hình nền (b0/k24 như HO4), thước (E0/H-A kiểu PREREG_HOLDOUT2026H1 §1), ngưỡng, k biến thể (inflate √(2 ln k)), 8 seed ghép cặp, scorer commit trước.
2. Mỗi ý tưởng mở kho ĐÚNG 1 lần; chạy lại chỉ khi lỗi hạ tầng với cfg y hệt. Kết quả FAIL không được "sửa rồi mở lại" trên cùng kho.
3. Sổ mở kho (`docs/plan/BACKCAST_RESERVOIR.md` §log): ngày, ý tưởng, hash pre-reg, kernel, người đọc số. Kho coi như "đã tiêu" cho mọi ý tưởng cùng họ sau ~3–5 lần mở (MASTER chốt số).
4. Trong vòng dựng: KHÔNG sim chiến lược để xem kết quả; KHÔNG PnL/tín hiệu thắng-thua; chỉ md5/NaN/phủ/khớp nguồn; 1 sim kỹ thuật, printDone niêm phong (chmod 700, chỉ md5 + số dòng + exit code).

## 4. RÒ RỈ (B0) + phương án chờ MASTER chọn
Đo (chỉ đọc meta/manifest/tài liệu, không đọc giá trị dự đoán):
| Model đóng băng | Dữ liệu train sớm nhất | Nguồn bằng chứng | Chồng kho 2020-01→2021-06 |
|---|---|---|---|
| gate p15 8 seed cut20260101 | `train_ts_min` = 2021-01-01 07:00 +07 (= 00:00 UTC), nhãn năm 2021–2025, n 2 629 005 | `~/claude_master/1003/ho1/gate/manifest_gate.json` (cả 8 seed) | **2021-01-01 → 2021-06-30 (6 tháng)** |
| net015 ONNX f15 `7921ceaf` (cut20251001) | Tool1 export bắt đầu `features_20210101_to_20210401.t1c` (sha `eca5b024…`), fold đầu dự đoán 2022-01 ⇒ train expanding từ 2021-01 | `docs/experiment/G3_X26_RECOVERY.md` §3.4, `G015X26_PROVENANCE.md` | **2021-01 → 2021-06** |
| S1 `af706dc6` (cut20251231) | ledger `cand_dev_x1` T0 = 2021-04-01 (`x1_ledger.py:19`) | `RESULT_S1REFRESH.md` | **2021-04 → 2021-06** |
| pred.bin DEV (đoạn sim) | 2 499 840 dòng = 1 736 ngày ⇒ từ 2021-04-01 +07 | manifest_gate.json | (không phải train) |
| store/ticker DEV | ticker 1 826 ngày = 2021-01-01..2025-12-31; store gate từ 2021-01-01 | b2.log, `ticker_min_days` | không có 2020 |

⇒ **2021H1 KHÔNG sạch** (nhãn/outcome đã vào train của cả 3 họ model). **2020-01-01 → 2020-12-31 UTC sạch về model** (không model nào thấy outcome 2020; chỉ dòng train 2021-01 đầu tiên dùng giá 2020-12 làm lookback feature, ≤ 30 ngày).

- **P1 (đề xuất): thu kho về 2020.** Dựng dữ liệu 2020-01-01 → 2021-01-03 UTC (72 h lookahead nhãn pool S1); **cửa sổ chấm 2020-05-01 00:00 → 2020-12-31 23:59 +07** (≈ 8 tháng; 23:59 +07 = 16:59 UTC < `train_ts_min` gate). Biến thể chặt (MASTER chọn): kết thúc 2020-11-30 để tránh cả phần giá 2020-12 làm lookback cho dòng train 2021-01. 2021H1: KHÔNG niêm phong, chỉ dựng nếu cần nối tiếp sim sang DEV, không bao giờ chấm.
- **P2 (không đề xuất): retrain 3 họ model với train ≥ 2021-07-01** (recipe gate có; S1 cần env T0; trainer net015 08-14 mất, phải viết lại nhãn `retEnd_4h > 0.015`) ⇒ kho xác nhận "bộ model bcast", không phải model live; 2021H1 vẫn nhiễm tầng thiết kế (FS đọc giá từ 2020-12, feat_v2 DEV từ 2021-01, store gate 2021-01).
- **P3 (không đề xuất):** giữ 2021H1, khai "in-sample model" — vô giá trị cho xác nhận.

## 5. Ai đã nhìn gì trên 2020-01 → 2021-06 (tính tới commit này)
| Ai / job | Đã nhìn | Mức |
|---|---|---|
| Train gate (DEV WFO, HO1 B2), net015 G015x26, S1 x1 | feature + NHÃN 2021-01..06 (S1 từ 2021-04) | outcome ⇒ rò |
| DATA_EXTENT_SURVEY (2026-06) | thống kê BTC theo năm 2020 (return +302 %, vol 76 %, ngày tệ nhất −40 % 2020-03-12), độ phủ Vision | chế độ thị trường, KHÔNG chiến lược |
| FS (PREREG_FS) | giá 1h 2020-12.. để dựng feature; chấm chỉ 2022-01..2024-06 | lookback, KHÔNG chấm |
| NBETS / GS / G015CUT / S1CUT | tính MDE / bàn khả năng lùi DEV về 2020-01 | không số chiến lược |
| AUDIT_OI_FEAT_PARITY, D1_DATA_AUDIT | độ phủ OI/LS raw 242 từ 2020-09 | dữ liệu |
| BCAST (agent này) | liệt kê file Vision (tên/tháng), meta train model | dữ liệu |
Không job nào (theo grep docs `2020-0x/1x`, `TIME_RUN=2020`) chạy sim/PnL chiến lược trên 2020.

## 6. Rủi ro khai trước (nếu P1)
- Universe nhỏ: 24–25 symbol (2020-04/05) → 80 (2020-12) so với 117+ DEV đầu, 600 cuối ⇒ breadth/basket/rank lệch phân phối train; K24 (top-24) gần như = toàn universe ở 2020-05 ⇒ H-A kiểu k24-vs-b0 mất sức phân biệt đầu kho.
- OI NaN toàn kho (như DEV 2021-07..11). COVID 2020-03-12 nằm trong warm-up, không chấm.
- Vision có thể thiếu symbol đã niêm yết 2019–20 (DATA_EXTENT: REST có 3 symbol từ 2019-09-08) — không kiểm được (cấm REST).
- Chế độ 2020 (bull, vol cao) khác DEV ⇒ kho đo độ bền theo chế độ, không thay holdout 2026.
