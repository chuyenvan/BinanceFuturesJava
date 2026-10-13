# VZ — PHASE 1 (MASTER duyệt pilot 2024-08, 2026-10-13)

Bổ sung cho `docs/plan/VZ_DATA_LAKE.md`. Mục nào không nhắc ở đây giữ nguyên runbook gốc.

## 0. Đánh giá pilot (commit data/vz-lake 0fe26864, dataset `chuyendinh/vz-pilot-202408` v1)
- Đạt: V1–V6 PASS; V4 khớp CLOSES_1H 183/183 (≤ 5,3e-8); dup 0; tải ngược sha256 trùng; RAM đỉnh 508 MB; allowlist host trong code.
- Vấn đề 1 — dung lượng: parquet ≈ zip (kline 33,6 B/dòng, basis 40 B/dòng) ⇒ nén chưa tối ưu; ngoại suy 75 GB > cổng 60 GB. Nguyên nhân chính: float64 nén zstd thường kém khi không có byte-stream-split; basis giữ cột thừa.
- Vấn đề 2 — đĩa Oracle 37 GB < 40 GB.
- Chấp nhận các lệch: (3) V5 tính trên dòng active; (4) layout flat `<ds>-<YYYY-MM>.parquet`; (5) `vz_common.py`; (6) giữ zip tới sau V6; (7) ~300 symbol có dữ liệu 2024-08 là đúng (symbol niêm yết theo thời gian).

## 1. Quyết định MASTER
1. KHÔNG cắt symbol (giữ cả symbol đã gỡ ⇒ tránh survivorship bias), KHÔNG cắt thời kỳ (2020-01 → 2026-09). Giảm dung lượng bằng mã hoá parquet + bỏ cột thừa.
2. Mã hoá parquet mới (áp mọi dataset):
   - `ts`: `DELTA_BINARY_PACKED` (file sort `sym, ts` ⇒ delta gần hằng 60 000); tắt dictionary cho `ts`.
   - mọi cột float: `use_byte_stream_split`, giữ float64 (không mất chính xác).
   - `sym`: dictionary; row group = 1 symbol (giữ như pilot).
   - zstd level 9.
   - Kiểm tương thích: đọc lại bằng pandas/pyarrow trên Kaggle kernel image hiện hành (pyarrow trong kernel có thể cũ hơn 25.0.1) — làm ở bước 1a.
3. basis1m giữ 5 cột giá: `prem_high, prem_low, prem_close, mark_close, index_close` (bỏ `prem_open`). Thêm cột `active: bool` = kline cùng phút có `volume > 0`.
4. kline1m thêm cột `active: bool` (= `volume > 0`). KHÔNG xoá dòng stale — chỉ đánh cờ.
5. V5 chốt: p99 |mark_close/kline_close − 1| < 1% và p99 |prem_close| < 2% **trên dòng active**; báo thêm số dòng stale + danh sách symbol stale mỗi tháng (thông tin, không FAIL).
6. Cổng dung lượng mới: sau 1a, ngoại suy tổng ≤ 55 GB **và** (dung lượng private Kaggle hiện dùng + tổng VZ ngoại suy + 40 GB dự phòng Phase 2) ≤ 180 GB. Vượt ⇒ DỪNG, báo.
7. Đĩa: chạy TỪNG NĂM; trước mỗi tháng kiểm `df` ≥ 30 GB; sau khi năm upload xong + tải ngược khớp sha256 TOÀN BỘ file của năm ⇒ được xoá `~/vz/out/<ds>/<YYYY>` (MASTER cho phép; ghi vào registry). Không xoá gì khác.
8. Năm 2020 (`…-2020s`, kho niêm phong): chỉ chạy V1, V2, V3, V5, V6 (bỏ V4 — CLOSES_1H nội bộ bắt đầu 2021); KHÔNG tính/đưa bất kỳ thống kê nào khác của 2020 vào báo cáo hay log (chỉ số dòng/byte/PASS-FAIL). README ghi: "SEALED — chỉ dùng theo docs/plan/BACKCAST_RESERVOIR.md".
9. Năm 2026: dataset `…-2026` có version, phủ 2026-01 → 2026-09 (tháng hoàn chỉnh cuối). README ghi: "HOLDOUT ĐÃ DÙNG (HO4) — không dùng để chọn/tune".

## 2. Các bước

**1a — tối ưu + đo lại (pilot lại 2024-08, chỉ kline1m + basis1m)**
- Tải lại zip 2024-08 (≈ 1,1 GB), build với mã hoá mới.
- So nội dung với pilot v1: đọc cả hai, mọi giá trị (ts, sym, các cột chung) phải trùng tuyệt đối (so bit float64); chỉ khác cột mới `active` và cột bỏ `prem_open`.
- Báo B/dòng mới, ngoại suy tổng mới, thời gian build. Tạo version 2 của `vz-pilot-202408` với file mới; trong 1 kernel Kaggle nhỏ (CPU, không phải kernel sim — được phép 1 kernel, kiểm slot ≤ 2 toàn tài khoản trước khi đẩy) đọc 2 file bằng pandas, in schema + số dòng + md5 cột ts ⇒ xác nhận đọc được trên Kaggle.
- Ghi dung lượng private Kaggle hiện dùng (`kaggle datasets list --mine` + size từng dataset).
- Kiểm cổng §1.6. Đạt ⇒ tự sang 1b, không cần chờ; không đạt ⇒ DỪNG báo.

**1b — chạy theo năm**: 2024 → 2025 → 2023 → 2022 → 2021 → 2026 → 2020s. Mỗi năm, mỗi dataset (kline1m, basis1m; metrics5m & funding gom file theo năm vào dataset chung `vz-metrics5m`, `vz-funding`):
1. fetch + verify sha256 từng zip (≤ 4 luồng) → build → V1–V6 (2020s theo §1.8).
2. upload: năm đã đóng = `datasets create` (1 lần, bất biến); `vz-metrics5m`, `vz-funding`, `…-2026` = `datasets version`. Lưu ý: version mới phải chứa ĐỦ mọi file đã có (Kaggle thay toàn bộ) ⇒ với `vz-metrics5m`/`vz-funding` giữ local bản đầy đủ (nhỏ, ~8 GB) đến hết Phase 1.
3. tải ngược toàn bộ file của năm, so sha256 = local ⇒ cập nhật `docs/data/VZ_REGISTRY.md` (slug, version, khoảng ts, n file, byte, sha256/md5 từng file, validate) ⇒ commit ⇒ xoá local năm đó (§1.7).
4. Báo tiến độ mỗi năm (1 đoạn ngắn): byte, rows, symbol, phút thiếu %, V1–V6, thời gian.
- Dừng ngay nếu: bất kỳ V nào FAIL; checksum lệch > 0,1% zip; đĩa < 30 GB; Vision trả 403/429 liên tục > 10′; cổng §1.6 vượt theo số thật tích luỹ.

**1c — `vz-symbols`** (sau khi hết các năm): mỗi symbol: first/last ngày có dữ liệu theo từng loại, số ngày thiếu, cờ stable/index/quarterly, số tháng stale. 1 file parquet + README.

## 3. Sau Phase 1 (MASTER làm, không giao claw)
- E1 — bộ đo theo sự kiện (event-study engine) trên Kaggle kernel đọc `vz-*`: định nghĩa sự kiện, cửa sổ, đích lợi nhuận sau chi phí bucket EXEC, bootstrap theo ngày; tái lập 1 kết quả đã biết (vd. phân bố chân sập EXEC) trước khi dùng cho giả thuyết mới.
- Giả thuyết đầu tiên dùng dữ liệu mới (pre-reg trước): taker-sell burst/cạn kiệt trong nến sập (taker_buy_quote/quote_volume) và basis cực âm tại nến sập → lợi nhuận hồi 15′/1h/4h trên DEV 2022–25.
- Phase 2 (aggev 1s quanh sự kiện) chỉ mở nếu E1 cho thấy tín hiệu cấp phút cần vi cấu trúc để tách.

## 4. Lệnh giao OpenClaw (owner dán)
> Đọc `~/src/BinanceFuturesJava/docs/plan/VZ_DATA_LAKE.md` và `docs/plan/VZ_PHASE1.md`. Làm Phase 1 đúng §1–§2 của VZ_PHASE1 (1a → kiểm cổng → 1b theo năm → 1c), tuân luật §5 của VZ_DATA_LAKE. Báo ngắn sau 1a và sau mỗi năm; dừng ngay khi gặp điều kiện dừng ở §2. Không làm Phase 2.
