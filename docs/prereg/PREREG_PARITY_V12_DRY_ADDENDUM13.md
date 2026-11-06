# PREREG_PARITY_V12_DRY — ADDENDUM 13: S1V lấp ngày 10-28 bằng REST ADD7 + cửa sổ theo thời gian, fail-closed (2026-11-06, TRƯỚC khi sửa)

Quyết định MASTER. **Khai:** viết SAU khi thấy S1V ngày 11-04 (score khớp 12 %, K5 = 1440 phút nguồn S1V) và chẩn đoán
(`parity_v12w/diag_s1v`). Chưa sửa code, chưa chấm lại.

## 1. Gốc lỗi (harness, không phải live)
- Vision `klines_1m/2026-10-28` chỉ có 1/747 file. Monthly 2026-10 cũng không có ngày 10-28 (đã kiểm BTCUSDT, PREDICTUSDT: có
  10-27 và 10-29, thiếu 10-28).
- `day_s1v.py:136-153` tính ret / vol / roll_max theo **vị trí** trong mảng giờ, nên thiếu 24 giờ thì cửa sổ trượt mà không báo.
- Chạy lại với 10-28 từ REST ADD7 (643 symbol, cổng R PASS): f0 khớp 0,8 % → 100 % trên mọi symbol có dữ liệu, spearman 0,9999.
  Phần lệch còn lại chỉ ở 5 symbol không có REST: CTUSDT, DOSUSDT, MARSCOINUSDT, PONSUSDT, PREDICTUSDT.

## 2. Sửa (cố định trước)
1. **Dữ liệu:** S1V đọc ngày 10-28 từ `gst1030/k1028/zips/<SYM>-1m-2026-10-28.zip` (REST ADD7, đúng định dạng Vision) khi Vision
   thiếu file. Chỉ áp cho S1V, chỉ ngày 10-28.
   - Tải thêm REST 10-28 cho đúng 5 symbol trên, bằng `rest1028.py`, từ Oracle. Throttle như ADD7 (≤ 300 weight/phút, 429/418
     dừng ngay). Chạy lại cổng R như cũ (REST 10-27 trùng từng byte với Vision 10-27, 5 symbol cố định). Cổng R TRƯỢT thì không tải.
2. **Cửa sổ theo THỜI GIAN:** ret72 / ret336 / vol 168 h / roll_max 168 h / hrs_since_high xét theo mốc giờ.
   - Giờ trước niêm yết (trước giờ dữ liệu đầu tiên) là NaN, như live.
   - Giờ **thiếu** sau giờ đầu tiên, nằm trong cửa sổ cần dùng: symbol đó là **KHÔNG ĐO ĐƯỢC** (fail-closed), không trượt cửa sổ.
   - Feature xếp hạng (f2, f5) phụ thuộc cả tập, nên **cả giờ** có ≥ 1 symbol KĐĐ là KĐĐ cho S1V. Giờ đó bị loại khỏi so sánh và khỏi
     nguồn K5. Số giờ KĐĐ ghi vào `s1v_<tag>.json` (`kdd_hours`, `kdd_syms`).
   - `day_report_v12`: `kdd_hours > 0` thì ngày có thêm "KHÔNG ĐO ĐƯỢC (S1V)", và không phải SẠCH-T (ADD12 §1.4).
3. **Test:** `test_s1v_time.py`: dữ liệu liền mạch thì bản thời gian = bản vị trí (bit); có giờ thiếu thì ra KĐĐ, không ra số.

## 3. Sau sửa
- Chấm lại 11-04 (xoá cache `closes_cache.pkl`), rồi để watcher chấm các ngày sau. Tiêu chí S1V / K5 không đổi.
- Lỗ 10-28 còn ảnh hưởng tới hết ngày 11-11 (cửa sổ ret336).
