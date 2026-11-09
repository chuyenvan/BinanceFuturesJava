# PREREG_PARITY_V12_DRY — ADDENDUM 16: TSX lấp ngày 10-28 bằng REST ADD7/ADD13 (2026-11-09, TRƯỚC khi sửa code)

Quyết định MASTER.

## 1. Vấn đề
- Vision không có kline 1m ngày 2026-10-28 (daily 404, monthly 2026-10 thiếu ngày này). Vì vậy không có `S_2026-10-28`.
- Cờ TSX ngày F dùng S từ F−30 đến F−1. Mọi ngày F trong **10-29..11-27** ra `state=NaN` ("missing 2026-10-28"), và TSX bị ghi KHÔNG ĐO ĐƯỢC.
- Kèm theo: `S_2026-10-29` (bin 10-28, 10-29) thiếu phút đầu, chỉ có 1439 phút.

## 2. Sửa
- `day_tsx.build_bin` (và phép đếm phủ trong `s_day`): ngày Vision thiếu file mà có trong `VIS_GAP` (ADD13) thì đọc REST 10-28 của
  ADD7/ADD13. Cùng nguồn `gst1030/k1028/zips`, cùng cổng R (REST 10-27 trùng từng byte Vision 10-27, gồm cột 4 close và cột 7 quote_volume).
  S chỉ dùng close và quote_volume.
- **Không** đổi ngưỡng, định nghĩa, cửa sổ hay bất kỳ tham số TSX nào.
- Xoá cache `tsx/S_2026-10-28.csv` và `tsx/S_2026-10-29.csv`, rồi dựng lại.

## 3. Phạm vi chấm lại
- TSX của **MỌI** ngày đã chấm từ 2026-11-04 đến nay. Áp nhãn mới bất kể kết quả, không chọn ngày.

## 4. Ràng buộc nhãn
- Ngày nào TSX TRƯỢT thì nhãn hạ theo quy tắc hiện có (PREREG gốc / §5).
- Ngày SẠCH-T chỉ lên SẠCH nếu TSX ĐẠT, và mọi điều kiện SẠCH khác vẫn giữ.
- Lượt M (Vision monthly, funding chính thức) vẫn giữ nguyên với các thành phần khác (ADD12 §3).

## 5. Minh bạch
- MASTER đã thấy kết quả chẩn đoán trong scratch `parity_v12w/diag_tsx`: TSX 11-07 ĐẠT, cờ OFF trùng live.
- Cách sửa là lấp dữ liệu, không chọn tham số, và dùng cùng phương án đã prereg ở ADD13 cho S1V.

## 6. Rủi ro
- REST của 513 symbol còn lại chỉ được cổng R kiểm qua mẫu 5 symbol.
- `S_2026-10-29` đổi nhẹ (chẩn đoán: −0,083783 → −0,083353, 1439 → 1440 phút), ảnh hưởng mọi cờ có cửa sổ chứa ngày này.

## 7. Nếu không sửa
- TSX chỉ tự đo lại được từ 11-28, chặn lượt M trước G-PILOT.
