# Phương pháp verify dữ liệu Kaggle KHÔNG lệch Oracle (3 tầng)

Mục tiêu: chắc chắn node Kaggle đọc CÙNG dữ liệu + cho CÙNG số như Oracle, không lệch ngầm.

## Tầng 1 — A6 count (ĐÃ CÓ, tự chạy mỗi kernel) ✅
`RunA6Check` chạy đầu mỗi kernel Kaggle: đếm record market/gate/funding trong dataset mount, so expected theo cadence. Bằng chứng run 2026-07-13: Kaggle đếm market=2.774.140, gate=2.717.280, funding=2.553.812 — KHỚP Oracle. BLOCK nếu <0.95. → bắt được lệch SỐ LƯỢNG, fail-fast trước khi chạy.
**Hạn chế:** chỉ so COUNT, không so GIÁ TRỊ (2 file cùng số record vẫn có thể khác nội dung).

## Tầng 2 — Deterministic single-window cross-node (ĐÃ CHẠY 2026-07-14) ✅⚠️
Chạy CÙNG 1 window (cùng seed/genome/data) trên Oracle vs Kaggle → diff isFit/oosFit/oosPnl/trades/bestGenome. Backtest tất định → phải trùng khít. Lệch = có vấn đề data hoặc môi trường. → bắt lệch ở mức KẾT QUẢ.

### Kết quả tầng-2 (window w10, run fan-out ret2 226:3222 ns=ticker, N=30, WFO_MAX_OOS_DATE=20260101, jar preflight 18-gene)

**Xác định owner:** owner-bin xoá rỗng khi DONE → dùng chéo `jobdump_snapshot.txt` (chụp giữa run 21:20, window còn RUNNING)
+ log 2 Oracle worker (`fanout_oracle_w{1,2}.log`). ⇒ **Oracle tính w00,w01,w08,w09,w15; Kaggle tính 11 window còn lại (w02–w07, w10–w14).**
Chọn **w10** (OOS 20240701..20241001, SUCCESS, nhiều trade) do **Kaggle** kernel `wfo-worker-1` (container `73277849c613`) tính —
xác nhận Kaggle-only: `RUN strat-w10` 21:04:38 → `DONE (4624s)` 22:21:42, không node khác RUN/STEAL.
Rerun trên Oracle bằng entrypoint read-only `VerifyOneWindow` (seed=52, cùng dataset `_ff` ret2 md5-verified, CWD=`oracle_worker_cwd` TICKER_SOURCE=file trỏ `ticker_regen`).

| Chỉ số | Kaggle-gốc (`73277849c613`) | Oracle-rerun (file) | Lệch |
|---|---|---|---|
| **bestGenome (18 gene)** | — | — | **TRÙNG KHÍT 100% (18/18)** |
| isFit | 3.3885 | 3.3829 | −0.17% |
| isPnl | 2223.9604 | 2218.7173 | −0.24% |
| oosFit | 0.5175 | 0.4969 | −0.0206 |
| **oosPnl** | **883.6589** | **847.0321** | **−4.15%** |
| WFE | 0.3973 | 0.3818 | −3.9% |
| **oosTrades** | **158** | **142** | **−16** |
| oosMaxDD | 1707.4572 | 1704.5934 | −0.17% |
| oosNote | SUCCESS | SUCCESS | = |

**KẾT LUẬN:** ✅ Chọn genome tất định cross-node HOÀN HẢO (18/18 gene y hệt → HPO/RNG/áp-gene không lệch Oracle↔Kaggle).
⚠️ Metric backtest LỆCH NHẸ (~4% oosPnl, 158→142 trade). IS gần khớp (isFit −0.17%).

**Nguyên nhân (có bằng chứng): CONFIG DRIFT giữa 2 node** — KHÔNG phải seed/dataset/ticker-file:
- Dataset `market/pred/funding` md5-verified giống hệt; seed=52 cả 2 (genome khớp tuyệt đối ⇒ RNG khớp).
- `config.properties` kernel Kaggle ≠ Oracle-worker: `DIED_SYMBOLS` Kaggle=30 coin survivorship (gồm WAVES/BNX/BTCDOM/USDC…)
  vs Oracle=`BTCDOM,USDC` (2) → vũ trụ coin khác → khác trade. Kaggle THIẾU `NUMBER_ENTRY_EACH_SIGNAL` (Oracle=4; default code=2),
  `NUMBER_HOUR_FUNDING_CAL`, `FUNDING_MAX/MIN_TRADE`, `BTC_TREND_REVERSE_*` → Kaggle dùng default code.
  (`RATE_FEE` là `final=0.002f` trong Configs.java → không nạp từ config, KHÔNG phải thủ phạm.)
- Lệch NHỎ vì phần lớn 30 coin died đã delist trước 2024 (không có data window 2024Q3) → chênh vũ trụ thực chỉ vài coin,
  không đủ đổi ranking genome. Chưa loại trừ 100%: nội dung ticker `.bin` vs `.bin.gz` chưa byte-compare; non-determinism budget-contention đa luồng.

**Timing per-window (cùng file-ticker, no RAM cache):** Kaggle 4624s (~77m04s) vs Oracle-rerun 4640s (~77m20s) → **gần y hệt (chênh 0.3%)**.
⇒ Kaggle KHÔNG chậm hơn Oracle khi cùng nguồn file.

**Hành động chốt trùng-khít tuyệt đối:** (1) SYNC `config.properties` Kaggle = Oracle-worker (ưu tiên `DIED_SYMBOLS`+`NUMBER_ENTRY_EACH_SIGNAL`)
trong `gen_kernels.sh`/`launch_fanout.sh` (đừng bundle bản stale); (2) rerun w10 Oracle với ĐÚNG config Kaggle → kỳ vọng tái lập 883.66/158;
(3) tùy: byte-compare ticker 2024Q3 `.bin` vs gunzip `.bin.gz`.

## Tầng 3 — Direct data read + đối chiếu lượng & chất (CHƯA CÓ — NOTE ĐỂ LÀM)
Ý tưởng (Uni đề xuất 2026-07-13): đọc THẲNG dữ liệu trên node Kaggle, so cả:
- **Lượng**: số file ticker (1826), số record mỗi bin (market/pred/funding), số ngày ticker liên tục.
- **Chất**: checksum NỘI DUNG (không phải byte thô, vì ticker Kaggle là `.bin` đã bung còn Oracle giữ `.bin.gz`):
  - `_ff` bins (market/pred/funding.bin): **md5 trực tiếp** — cùng file upload nên PHẢI trùng md5 Oracle↔Kaggle.
  - ticker: **gunzip Oracle `.bin.gz` → md5** vs Kaggle `.bin` md5, lấy mẫu ~10-20 ngày rải đều + vài ngày mép (2021-01, 2025-12). Trùng = nội dung khớp.
  - (tùy) decode vài giá trị mẫu (giá close 1 symbol tại 1 ts) 2 bên in ra so mắt.

### Khi nào làm
- **Lần đầu sau khi ticker/_ff mới lên Kaggle** (như bây giờ — nên chạy 1 lần để chốt baseline tin cậy).
- **Mỗi khi re-version ticker/_ff** trên Kaggle (kline nguồn đổi / re-export).
- Định kỳ nhẹ (vd hàng tháng) hoặc khi số WFO Kaggle nghi lệch Oracle.

### Môi trường cần (HIỆN ĐANG THIẾU → chưa chạy ngay được)
- Cần 1 **"data-audit kernel" Kaggle** riêng (chưa build): mount `wfo-ds-ret2-4h-ff` + `hpo-ticker-daily`, chạy script tính md5 các bin + md5 mẫu ticker `.bin` + count → in ra output kernel.
- Phía Oracle: script tính md5 `_ff` bins + `gunzip|md5` mẫu ticker tương ứng (rẻ, chạy được ngay).
- Đối chiếu 2 bảng md5. **Chưa có kernel-audit** → xây khi cần (ước ~30' công), hoặc nhét bước md5 vào `RunA6Check` để mỗi kernel tự in md5 (tiện, không cần kernel riêng).

### Ghi chú
Tầng 1+2 hiện đủ để tin run này. Tầng 3 là "để chắc + tái dùng lâu dài" — làm khi ổn định pipeline, không chặn tiến độ. Ưu tiên nhét md5 vào RunA6Check (rẻ, tự động mỗi run) hơn là kernel-audit rời.
