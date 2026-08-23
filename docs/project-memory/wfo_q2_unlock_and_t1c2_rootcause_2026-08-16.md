# 2026Q2 unlock + T1C2 root cause (2026-08-16)

Hai phát hiện then chốt trong phiên này. Cả hai đều là **root cause thật**, không phải workaround.

## 1. 2026Q2 bị chặn KHÔNG phải do thiếu data — do hardcode `DATA_END`

Trước đây pad đủ thứ (selector predwf, gate pred.bin, market.bin tới 2026-08-13, funding qua Q2) mà fanout vẫn chỉ 17 window. Lý do thật:

`com/binance/chuyennd/ai_ml/wfo/framework/tasks/StrategyWfoTask.class` trong `gatecount.jar` có:
```
private static final String DATA_START = "20210101";
private static final String DATA_END   = "20260601";   // HARDCODED — cap thật
```
`buildWindows()` dùng hằng `DATA_END` (KHÔNG dùng độ phủ data thực). Vòng lặp `if (oosEnd > dataEnd) break;` → win Q2 (oosEnd 2026-07-01) bị cắt. Vì vậy **mọi thao tác pad data đều vô ích** — chỉ sửa `DATA_END` mới mở được window.

### Fix đã áp dụng
- Binary-patch `.class` trong jar: `"20260601"` → `"20260701"` (cùng 8 ký tự ASCII, offset-safe). Chỉ có đúng 1 occurrence.
- Backup: `/home/ubuntu/java/simulator/gatecount.jar.bak_datend` (rollback = copy đè lại).
- Verify: `javap` xác nhận `DATA_END = "20260701"`; coordinator `reset` → `total=18` window (w00..w17), w17 = 2026Q2. Trước patch = 17 (w00..w16).

### Q3 (bonus) cần thêm gì
- Patch `DATA_END` → `"20261001"` (đủ 8 ký tự).
- VÀ cần selector fold thật `predict_wf_20260701` (hiện chưa có). Data chỉ tới 2026-08-13 nên Q3 sẽ là **partial** (Jul–mid Aug). Chạy CANON với `CUTOFFS=20260701` để sinh fold này trước.

### Fanout Q2 đang chạy
`drive_exp18.sh G015x26e 0` (predwf_G015x26e = 18 fold THẬT, tới predict_wf_20260401 = Q2, 4.89M rec 4h thật). Kết quả K5 per-quarter gồm 2026Q2 sẽ nằm ở `claudedata/sweep/DONE_G015x26e.txt`.

## 2. 5m/1m grid fail: data Tool1 là format T1C2 columnar (KHÔNG phải raw 170B)

Dataset `funding-tool1-5m` (và 1m) build lại 2026-08-13 ở định dạng **T1C2** (magic `"T1C2"`), KHÔNG phải row-major float32 big-endian 170B/record như 15m cũ.

- T1C2 = columnar + quantize int16 (cột đuôi xa dùng int32 "wide") + byte-split + delta cumsum, **little-endian**. Header: `magic(4)+rowCount(4)+nCols(4)+baseMs(8)+stepMin(4)+wideMask(8)`. Lý do đổi: giảm entropy → tiết kiệm quota private Kaggle (~3.8×).
- Reader chuẩn: `/home/ubuntu/sel1m_code/tool1_col.py` → `read_tool1(path_or_glob, grid_ms=)`, trả structured array `[(ts,<i8),(sym,<i2),(f,<f4,40)]` y hệt format cũ.

`gen_wf_pred_stream_gpu.py` đọc raw 170B từ byte 0 → parse rác → sau ts-filter còn rỗng → `a0["ts"].min()` crash (`zero-size array to reduction`). Đây là root cause `ValueError` của kernel 5m, tách biệt với "grid bug" (GRID_MS vs label step) trước đó.

### Fix đã áp dụng
- Patch `gen_wf_pred_stream_gpu.py`: `from tool1_col import read_tool1`; thay 3 chỗ đọc Tool1 (`_merge_chunk`, a0, aN) từ `_read_struct_stream(...)` → `read_tool1(..., grid_ms=GRID_MS)`; thêm pre-filter ts trước khi dựng DataFrame (giảm peak RAM). Backup: `gen_wf_pred_stream_gpu.py.bak_raw`.
- Re-version dataset `chuyendinh/sel1m-code` (kèm tool1_col.py), push kernel `selector-5m-stream-gpu` v3. Đang RUNNING.
- OI (`oi_percoin_full.bin`) và label (.pb) KHÔNG phải T1C2 → giữ reader cũ (đã chạy đúng).

### Hệ quả cho 1m
1m cũng cùng exporter T1C2 → cùng fix áp dụng được ngay khi test grid 1m.

## Trạng thái cuối phiên
- Q2 fanout: đang chạy (build xong, upload funding.bin ~58%). Chờ workers + report.
- 5m kernel v3: RUNNING (fix T1C2). Chờ xác nhận qua được a0 read và train.
