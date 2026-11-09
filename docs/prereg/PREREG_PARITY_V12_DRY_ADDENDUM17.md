# PREREG_PARITY_V12_DRY — ADDENDUM 17: PCT của P3 trong harness = float32 như sim/live (2026-11-09, TRƯỚC khi sửa code)

Quyết định MASTER.

## 1. Nguồn chuẩn của q
- Nguồn chuẩn là code sim `GateRollingRatio.java:75`: `pct = Float.parseFloat(...)` (float), rồi `GateRatioBuffer.java:80` tính
  `k = floor((double) pct * (m − 1))`. PCT thực dùng là 0,99995082616806 (float32 của 0,999950829 ép sang double).
- Live (`LiveGateRollingRatio.java:93`) làm giống hệt.
- Harness v12 (`day_eval.py:182`, và `indep_check.py:52`) dùng double 0,99995083, khác sim.

## 2. Sửa
- Harness tính `PCT = float(np.float32(0.999950829))`, đúng hệt sim.
- **Không** đổi ngưỡng hay dung sai của P3 (rel ≤ 1e-6), không đổi cách tính k hay quantile, chỉ đổi giá trị PCT.
- Không đụng code Java của live/sim.

## 3. Phạm vi chấm lại
- P3 của **MỌI** ngày đã chấm theo harness v12 (11-03 trở đi), kể cả ngày đã TRƯỢT hay XÁM. Áp nhãn mới bất kể kết quả.
- Chạy trong scratch trước, rồi mới ghi chính thức.

## 4. Minh bạch
- MASTER đã thấy lệch ở 11-08 09:00Z (bản chạy sớm trong scratch, chưa có nhãn chính thức) trước khi viết addendum này.
- Đây là lỗi tái lập (harness ≠ sim), không phải chọn tham số.
- Tần suất ước tính khoảng mỗi 200 giờ một lần: chỉ lệch khi m đầu giờ rơi vào dải khoảng 97 phần tử giữa hai PCT.

## 5. Bằng chứng
- Tại m = 1260874 (11-08 09:00Z): sim/live cho k = 1260810 (q = 0,009816479, trùng log), harness cũ cho k = 1260811 (q = 0,009854580).

## 6. Test
- k(m = 1260874) = 1260810.
- Replay q cả ngày 11-08 khớp log ≤ 1e-6 ở mọi giờ.
- P3 ngày 11-06 và 11-07 không đổi.
