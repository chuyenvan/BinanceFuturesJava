# PREREG_PARITY_V12_DRY — ADDENDUM 15: G-MICRO (ii) và smoke tính theo jar go-live r4t (2026-11-07)

Quyết định MASTER. **Khai:** viết sau khi đã có nhãn 11-04 và 11-05 (đều không tính), trước nhãn 11-06 và các ngày sau.
Bối cảnh: dry đổi r4q (11-05 17:41:52 +07) → r4t (11-06 22:10:34 +07). Không có ngày r4q nào chạy trọn.

## Sửa ADD11 §4 (ii)
- (ii) cần **≥ 1 ngày SẠCH hoặc SẠCH-T (ADD12) chạy trọn trên r4t**, là jar sẽ lên live. Ngày swap r4t (11-06) không tính.
- **Smoke ≥ 24 h** tính từ **2026-11-06 22:10:34 +07** (1793977834000 ms), cửa sổ [mốc, mốc + 24 h]: 0 `ERROR`, 0 `LATCH` trong log app
  242 (log cửa sổ đã pull, chỉ đọc).
- (i) giữ ADD11/ADD12: ngày r4n, r4q, r4t đều đếm (SẠCH hoặc SẠCH-T), ngày swap là XÁM và không tính.
- TRƯỢT ở bất kỳ phép cơ học nào thì dừng đếm (ADD11 §3).

## Code
- `gmicro.py`: `TARGET_JAR = "r4t"`, `SMOKE_START_MS = 1793977834000`; (ii) lọc theo `jar == TARGET_JAR` và không phải ngày swap.
- `day_report_v12.py`: smoke dùng `SMOKE_START_MS` thay cho mốc start của jar khác r4n đầu tiên.
