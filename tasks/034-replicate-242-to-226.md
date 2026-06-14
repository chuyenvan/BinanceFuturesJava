# TASK-034: Tool replicate 242→226 theo setname (+ backup repl=1 + soát funding_data_new) [CCD1]

- **status:** DONE (tool `cc927e8`+fix; backup OI/price_realtime/funding_data chạy TRÊN 226 verified; soát funding xong). · **owner:** CCD #1 · **updated:** 2026-06-14
- **Căn cứ:** `docs/DATA_ARCHITECTURE.md` §6 (chốt A) — 226 = replicate-242-theo-setname (on-demand) + backup cho repl=1.

## Chạy ở đâu
**TRÊN 226.** ĐỌC-ONLY 242 (chỉ đọc, KHÔNG ghi/sửa 242 — đúng luật "242 user-only") → ghi **226**.

## Mục đích (2 trong 1)
1. **Replicate market 242→226** theo setname để train/backtest (Kaggle/dev chỉ tới 226) có market data.
2. **Backup**: 242 repl=1 không bản sao; set chỉ-sống-242 (`open_interest`, `price_realtime`, `ai_pred`, funding) mất nếu hỏng ổ → copy sang 226.

## Tool (Java, SLF4J)
- Input: danh sách setname (1..n), nguồn=242, đích=226, tùy chọn khoảng thời gian.
- Scan set 242 (đọc-only) → ghi 226 giữ NGUYÊN key + bin (không biến đổi).
- **Idempotent**: chạy lại không nhân đôi (overwrite theo key).
- **Incremental**: chỉ copy record mới theo ts/last-checkpoint — KHÔNG copy lại toàn bộ mỗi lần (đặc biệt `kline_1m_opt` 22GB). Checkpoint theo luật CLAUDE.md #5 nếu set lớn.
- Log #record copied + tiến độ.

## ⚠️ Soát TRƯỚC khi replicate funding (032 lòi ra)
- Có `funding_data` VÀ `funding_data_new` (2 set funding) trên 242. Xác minh **live ghi/đọc set nào** (đọc code ingest + `FundingFeeManager` + scan ts cả 2 set). Báo cái nào là thật → chỉ replicate cái đó, ghi rõ cái kia là gì (cũ/rác/đang chuyển).

## Set ưu tiên (gợi ý — chốt sau khi soát)
- Nhẹ, backup ngay: `open_interest`, `price_realtime`, funding (cái đúng).
- Lớn, incremental: `kline_1m_opt` (chỉ khi train cần phần 226 mới hơn bản cào cũ 06-07).

## An toàn
- ĐỌC-ONLY 242 tuyệt đối (KHÔNG ghi/xóa/sửa 242). Ghi 226. Ghi PID/.run theo luật dọn-job 226; KHÔNG dồn với builder-010/015/024 đang chạy. Incremental + checkpoint cho set lớn.

## Acceptance
- [x] Tool copy set 242→226 idempotent (ghi theo digest gốc, UPDATE; chạy 2 lần #record không đổi) — verify #record + sample BTC/ETH ts khớp 242. Incremental: per-symbol map set ghi-đè cả record = tự cập nhật điểm mới; `kline_1m_opt` (22GB) chặn trừ `--allow-large` (incremental theo ts là việc riêng nếu cần).
- [x] Soát funding: **live dùng `funding_data`** (FUNDINGFEE const; FundingIngestor `writeFundingMap` + FundingFeeManager `getFundingMap`). `funding_data_new` (638 obj@242) = **mồ côi** — literal KHÔNG có trong code (grep: chỉ log "OLD vs NEW" không liên quan) → KHÔNG replicate; báo Desktop cân nhắc dọn (KHÔNG xoá 242 — read-only + quyết định của user).
- [x] Backup set chỉ-242 chạy: open_interest (622), price_realtime (678) → MỚI trên 226; funding_data 729→754 (tươi 06-14). errors=0.
- [x] KHÔNG đụng ghi 242 (chỉ scanAll đọc; mọi put → 226).

## (Code điền)
- **Tool replicate (commit):** `ai_ml/validation/data/ReplicateSet242To226.java` `cc927e8` (+ fix per-record sendKey: price_realtime ghi digest-only → userKey null → sendKey=true gây NPE; tách wpKey/wpNoKey theo userKey). Dùng: `java ... ReplicateSet242To226 <set...> [--allow-large]`. scanAll 242 → put 226 giữ digest+key+bin.
- **Soát funding_data vs _new:** live = `funding_data`. `funding_data_new` mồ côi (không writer/reader trong code).
- **Set đã backup 226 (chạy TRÊN 226, 2026-06-14 13:00):** open_interest 622 · price_realtime 678 · funding_data 754. Sample-verify (`AerospikeStateScan`@226 sau copy): funding BTC/ETH 5974đ ts 06-14 07:00; OI BTC 3084đ/ETH 3141đ ts 06-14 12:55 — khớp 242.
