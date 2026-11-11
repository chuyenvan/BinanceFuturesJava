# PREREG_PARITY_V12_DRY — ADDENDUM 20: S1V tính feature trên close float32 như live/sim (2026-11-11, TRƯỚC khi sửa code)

Quyết định MASTER (hướng sim float32). **Khai:** viết SAU khi thấy K5 = 57 phút ngày 11-09 (19:00–19:59 +07, nguồn S1V, lệch hạng
f2 rk_dd_7d / f5 rk_ret_3d ở GOAT, PROVE, SPELL, COW, FET). Điểm S1 và top-24 trùng 100 %.

## 1. Nguồn chuẩn
- **Sim/B0:** pipeline feature S1 `research/pipeline/x1/x1_feat_v2_build.py:29` đọc `CLOSES_1H.bin` với close
  **`>f4` (float32)**: `DT=np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")])`. Dòng `:30` ép sang float64, rồi tính `ret`/`dd` (`:39-45`) và
  `rank(axis=1, pct=True)` (`:107`, trung bình cho hoà). Đây là nguồn của bins S1-map.
- **Live:** `S1FeatureLive.java:158-178` xếp hạng trung bình như pandas, tính trên close float32 (ticker) ép sang double.
- **Harness:** `day_s1v.py:100` đọc close Vision bằng **float64** (giá thập phân đúng) ⇒ khác cả live lẫn sim.

## 2. Bằng chứng (scratch, chỉ đọc)
- Ngày 11-09, giờ 19:00 +07: close float64 cho dd(SPELL) = dd(PROVE) và ret72(COW) = ret72(FET) trùng tới bit, nên harness chia đều hạng.
  Ép close về float32 thì 5 giá trị này khác nhau.
- Kết quả 60 phút: lệch f2 175 → **0**, lệch f5 120 → **0**.

## 3. Sửa
- **Phạm vi:** chỉ đổi bước nạp close cho các feature S1V tính từ close. `day_s1v.build_closes`:
  close = `float64(float32(close Vision))`, như sim (`x1_feat_v2_build.py:29-30`).
- **Không** đổi ngưỡng, cửa sổ hay cách xếp hạng. Không đổi luật K5, K6 hay tie_split (ADD2/ADD3). Không đụng code Java.
- Test:
  - Tái lập 11-09 19:00 (COW/FET, GOAT/PROVE/SPELL) cho 0 lệch f2/f5.
  - Một ngày ĐẠT cũ không sinh lệch mới.

## 4. Phạm vi chấm lại
- S1V và K5 (labels / kprime / kpp) của **MỌI** ngày đã chấm từ 11-04 tới 11-09, không chọn ngày. Áp nhãn mới bất kể kết quả, kể cả ngày
  nào xấu đi.
- Đây là lỗi tái lập (harness ≠ sim ≠ live, cùng loại ADD17), không phải chọn tham số. MASTER đã thấy ngày 11-09.

## 5. Rủi ro
- Ép float32 có thể làm lộ ra các ca hoà/lệch khác ở những ngày đang ĐẠT (hoà mới do float32). Chấm lại sẽ áp nhãn bất kể kết quả.
- `ret`/`vol` có thể đổi ở cỡ 1e-8; tiêu chí 1e-6 hiện có đủ rộng.

## Phương án thay thế (KHÔNG chọn, chỉ ghi lại)
- Nếu sim là float64: không sửa harness. Mở rộng lớp tie_split (K6) cho cụm hoà ≥ 3 coin, với điều kiện giá trị gốc hai bên chênh ≤ 1 ulp
  float32 và top-24/score trùng 100 %. Ghi vào danh sách lệch live/sim đã biết (D14).
- Rủi ro của phương án này: nới K6 có thể che lệch thật cùng cỡ.
- Phương án này không áp dụng: §1 cho thấy sim dùng float32.
