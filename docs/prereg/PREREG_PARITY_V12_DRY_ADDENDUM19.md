# PREREG_PARITY_V12_DRY — ADDENDUM 19: G-MICRO (ii) và smoke chuyển sang jar r4u-final (2026-11-10, trước swap r4u)

Quyết định MASTER, giống ADD15 nhưng cho r4u. Lý do: r4u sửa cách chọn coin BIG_DOWN cho khớp sim (ADD18), và r4u sẽ lên live.

## 1. (ii) và smoke
- (ii) cần ≥ 1 ngày SẠCH hoặc SẠCH-T chạy trọn trên jar **r4u-final** (md5 `15f9e14f246f5667aade7a1647574384`). Ngày swap không tính.
- Smoke ≥ 24 h, 0 `ERROR` / 0 `LATCH`, tính từ `SMOKE_START` = giờ start thật của r4u trên 242. Giờ này điền lúc swap vào file
  cấu hình `parity_v12w/gmicro_target.json`, không hard-code.
- Khi `smoke_start_ms` chưa điền thì smoke = CHƯA ĐO. Khi md5 trong `jars.json` của jar đích khác md5 trên thì (ii) = false, có ghi chú.

## 2. (i)
- Vẫn đếm tổng số ngày như ADD11 §3: SẠCH hoặc SẠCH-T (ADD12), ngày swap XÁM không tính, TRƯỢT thì dừng đếm.
- Ngày SẠCH trên r4t (và r4n, r4q) vẫn tính.
- **Ngoại lệ:** ngày chạy jar cũ (r4n/r4q/r4t) mà có ≥ 1 sự kiện BIG_DOWN thì **không tính** cho (i), vì jar cũ chọn coin BIG_DOWN khác sim
  (số sự kiện lấy từ phép BIG_DOWN-SEL, ADD18 §3).

## 3. Code
- `gmicro.py` đọc `TARGET_JAR`, `TARGET_MD5`, `SMOKE_START_MS` từ `parity_v12w/gmicro_target.json`. File thiếu thì dùng giá trị ADD15 (r4t).
- ADD15 bị thay ở phần đích (ii)/smoke kể từ khi file cấu hình trỏ sang r4u.

## ERRATA (2026-11-10): jar đích r4u3, tập loại trừ BIG_DOWN-SEL giống sim

- **(ii) và smoke** chuyển từ r4u-final sang **r4u3**: md5 `b1f12c3eeaeed72cb17afbe5b4da06cf`, commit c3live `4479b158`.
  Thêm so với r4u-final: env `C3_EXCLUDE_LEGACY_HELD` (tk con SUB = false, chỉ loại coin c3 như sim, đóng lệch L-1), và guard jar ép `true`
  khi live với key tk chính. `SMOKE_START` = giờ start thật của r4u3, do script swap ghi vào `parity_v12w/gmicro_target.json`.
- **ADD18 BIG_DOWN-SEL:** tập tính lại offline dùng tập loại trừ giống sim, tức **chỉ** loại coin c3 đang giữ (sổ c3, ADD1), **không** loại
  coin LEGACY. `day_bigdown.py` bản trước có loại thêm LEGACY; bản này đã bỏ, kèm test.
- jar r4u3 đăng ký vào `jars.json` (`register_jar.sh`) **sau swap**, vì cần mốc start JVM thật (t0_tick).
