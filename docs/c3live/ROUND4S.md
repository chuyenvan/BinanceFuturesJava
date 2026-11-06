# ROUND 4s — sửa A1 4r (MIN-1/2/3) trên guard độ đủ phút, jar r4s (2026-11-06)

r4r (`bd85ca94`) **không** lên 242. Swap đi thẳng r4q → r4s. Nền tảng xem `ROUND4R.md`.

## Thay đổi
- **MIN-3**: tham chiếu của `MinuteCompletenessGuard` là trung vị của **60 phút ĐỦ gần nhất**. Phút MI không được đưa vào, và tham
  chiếu không hết hạn theo thời gian. Mầm lúc khởi động lấy từ cache 60′. Sự cố kéo dài vì vậy không tự hạ ngưỡng.
  Trước đây ngưỡng là trung vị 60′ của cache, nên tụt sau khoảng 31′ sự cố.
- **MIN-2**: MI liên tiếp ≥ 3, hoặc ≥ 5 phút MI trong 60′ ⇒ log `[MINUTE-GUARD] KHAN …` và gửi Telegram (`Utils.sendSms2Telegram`,
  thread daemon riêng). Chống spam: tối đa 1 tin / 30′.
- **MIN-1**: chỉ ghi vào vz_e1 ADD14 §5, không sửa code. Phút MI không nạp r vào buffer GDV2; số đo 10-30 cho thấy 0 phút MI.
- Phút đủ ⇒ không đổi gì so với r4q (0 đọc thêm). Dòng log đổi tên trường `trung_vi60=` thành `trung_vi60du=`.

## Test
- `MinuteCompletenessGuardTest` 12/12. Ngoài các test của r4r, có thêm:
  - sự cố 35′ ở 627/752: cả 35 phút đều MI, `can` giữ 745, đúng 2 tin KHẨN (phút MI thứ 3, rồi phút thứ 33 sau 30′);
  - 5 MI không liên tiếp trong 60′ ⇒ KHẨN đúng 1 tin;
  - 2 MI liên tiếp ⇒ không KHẨN;
  - ngày sập ⇒ có KHẨN, tối đa 1 tin / 30′.
- Full `mvn package`: 945 test, 0 fail (1 skip có sẵn).
- fake242: §34 chuyển sang r4q → r4s, mặc định tag r4s.

## Jar
`~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4s`, md5 `304697108dbe6be639fad570e7b766b3`. Đã pin r4s ở:
- `swap_v12_dry_jar.sh`: OLD = r4q `8c81e6b5`, NEW = r4s;
- `golive_lib.sh`;
- `deploy_v12_dry_r4.sh`;
- `restart_v12_dry_reseed.sh`.

## Lệnh owner (trên Oracle) — CHƯA chạy
```
DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh   # chỉ kiểm (242 CHỈ ĐỌC)
bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh         # gõ YES => JOB NỀN; theo dõi: tail -f <job_log in ra>
```
- Hậu kiểm gồm các mục của r4q, cộng `[MINUTE-GUARD] BAT`. LEGACY được so với số chụp ngay trước stop: giảm thì WARN, tăng thì FAIL.
- Trượt ⇒ rollback tự động về r4q. Đạt ⇒ `register_jar.sh r4s …`.
