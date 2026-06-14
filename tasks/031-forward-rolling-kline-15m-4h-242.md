# TASK-031: Forward-rolling kline_15m/4h BTC/ETH ghi 242 (live) — chuẩn bị golive gate

- **status:** TODO. Nối TASK-009 (historical xong). CẦN trước khi gate model mới golive.
- **owner:** CCD #1 · **status:** REVIEW (code DONE `dd883f9`, javac11 PASS; verify ts-tiến + historical@242 chờ chạy TRÊN 226/242; gộp deploy 242 có soát) · **updated:** 2026-06-14

## Bối cảnh (đã soi)
- `Aggregate15m4hBtcEth` (009) là job HISTORICAL one-shot: `writeSeries` ghi **CẢ 226+242** (đúng), `IS_KAGGLE_MODE=true` chỉ ảnh hưởng ĐỌC (`kline_1m_opt` từ 226). → 242 đã có kline_15m/4h historical tới ~06-07.
- **Thiếu: FORWARD-rolling.** Không thread nào cập nhật kline_15m/4h realtime → sau 06-07 hai set đứng yên. Gate mới đọc kline_15m/4h@242 lúc golive sẽ thiếu data hiện tại.

## Mục tiêu
Thread forward trong **`BinanceDataIngestor`** (chạy trên 242), khi một khung 15m/4h vừa đóng (biên UTC) → aggregate từ `kline_1m_opt` **LIVE (242)** → ghi `kline_15m_btceth`/`kline_4h_btceth` **242**.

## Chi tiết
- **Trigger:** mỗi phút check; khi qua biên `epoch % MS_15M == 0` (khung trước vừa đủ) → gom 15 nến 1m của khung đó (BTC/ETH) → ghi. Tương tự 4h (MS_4H).
- **Nguồn đọc:** `kline_1m_opt` trên **242** (live), KHÔNG đọc 226 (không bật IS_KAGGLE_MODE trong path live).
- **Ghi:** đúng client **242** (getClient242 / getWriteClient chuẩn live). Key `SYMBOL-YYYYMM`, append khung mới vào record-tháng (đọc record tháng hiện tại → thêm khung → ghi lại). Chỉ 1 thread forward nên read-modify-write không race; vẫn nên guard.
- **Format KHỚP historical:** `Snappy(gson(TreeMap<startMs, float[o,h,l,c,v]>))`, cùng quy tắc o=1m đầu/h=max/l=min/c=1m cuối/v=Σ. Để gate đọc liền mạch historical+forward.
- **Khung thiếu phút (<15 / <240) → skip** (như historical, không tạo nến nửa vời).

## Xác minh trước khi code
- Chạy `AerospikeStateScan` **TRÊN 226** đo `kline_15m/4h_btceth@242`: historical đã thực sự ở 242 chưa (writeSeries ghi cả 242 nhưng xác nhận, vì 2 process Aggregate trùng + có thể lỗi). Nếu 242 thiếu → chạy lại Aggregate (ghi cả 242) hoặc backfill 242 trước.

## An toàn
- Ghi 242 (live) → chạy ON 242/226. Thread trong process live `BinanceDataIngestor` → **test riêng kỹ** (đừng làm hỏng ingest đang chạy). Gộp deploy có soát. SLF4J.

## Acceptance
- [x] Xác nhận historical kline_15m/4h ở 242 — **ĐÃ XÁC NHẬN** (scan TRÊN 226, 2026-06-14 10:40): `kline_15m_btceth`/`kline_4h_btceth`@242 mỗi set 132 key-tháng, BTCUSDT tới 2026-06-07. ⚠️ **Gap 06-07→nay ~7 ngày**: khi bật forward, catch-up 15m trần 200 khung (~50h) không đủ lấp 7 ngày → **chạy lại `Aggregate15m4hBtcEth` (ghi 242) ngay trước golive** rồi forward giữ realtime.
- [x] Thread forward aggregate từ kline_1m_opt@242 → ghi kline_15m/4h@242 khi đóng khung; **format khớp historical** (một bộ não). → `dd883f9`, javac 11 PASS.
- [~] Verify ts tiến realtime — cần chạy TRÊN 242/226 (test riêng), CHƯA chạy (firewall dev).
- [x] Test riêng (`main()` standalone 1 vòng), KHÔNG tự deploy.

## (Code điền)
- **Xác minh 242 historical:** dev không tới 242 (firewall). 226 (TASK-023 §5) historical 2 set dừng 2026-06-07. Trước/khi golive: chạy `AerospikeStateScan` TRÊN 226 đọc `kline_15m/4h_btceth@242`; nếu 242 thiếu → chạy lại `Aggregate15m4hBtcEth` (writeSeries ghi cả 242) backfill trước. Roller đã guard: init đọc record 242 rỗng → log cảnh báo "cần Aggregate ghi 242".
- **Thread forward + ghi 242:** class `websocket/Kline15m4hForwardRoller.java` (commit `dd883f9`), wire trong `BinanceDataIngestor.main()`. Loop 60s → `rollOnce`: mỗi interval (15m/4h) × {BTC,ETH}, khung "sẵn sàng" = `floor((now-frameMs-GRACE)/frameMs)*frameMs` (GRACE=120s chờ nến 1m cuối ghi xong), catch-up từ `lastWritten`+1 tới đó (trần 200 khung, gap lớn → nhảy+cảnh báo). Gom 1m@242 (`readDataFromAerospikeCustom`, live=242), đủ phút mới ghi (thiếu→skip), append vào record-tháng 242 (`getClient242`). Quy tắc/format/key Y HỆT `Aggregate15m4hBtcEth`. `lastWritten` resume từ record 242 (qua restart 12h).
- **Verify ts tiến:** CHƯA — chạy `AerospikeStateScan` TRÊN 226 trước/sau bật roller: `kline_15m/4h@242` startMs-cuối phải tiến qua mốc 15m/4h gần nhất (cách now ≤ ~17m cho 15m). Hoặc chạy `main()` standalone của roller trên 242 → 1 khung mới xuất hiện.
