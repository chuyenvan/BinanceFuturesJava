# v1.2/c3-live — Round 4m: A1 R4K MIN-1 + MIN-2 (chỉ ops; không đổi Java/jar)

## MIN-1 — `run/gate_ratio_live.bin` dùng chung v1.1 / dry
- **Deploy** (`deploy_v12_dry_r4.sh`, bước restart): **ngay sau khi v1.1 dừng, trước khi start v1.2**: chép
  `run/gate_ratio_live.bin` → `.bak_v12pre_<TS>`, kiểm md5 bản chép = bản gốc, ghi md5 vào `.bak_v12pre_<TS>.md5`
  (in `OK backup_gate_ratio md5=…`). Chưa có file ⇒ marker `NONE`. Lỗi ⇒ `FAIL` ⇒ rollback tự động (v1.2 chưa start).
- **Rollback** (`rollback_v12.sh`): PRE kiểm md5 bản backup = marker (sai ⇒ DỪNG, không đổi gì). Sau khi dừng bot:
  file của dry đổi tên `.rb_<TS>`; marker có md5 ⇒ chép lại đúng bản backup + kiểm md5 (`OK gate_ratio_khoi_phuc md5=…`);
  `NONE` ⇒ không đặt file (v1.1 bắt đầu buffer rỗng như trước deploy). Không có marker TS (deploy chưa tới restart) ⇒ giữ nguyên.

## MIN-2 — PAUSE watchdog còn lại khi job chết giữa chừng
- PAUSE ghi **token của job**: `C3DEPLOY_V12 TS=<TS> pid=<pid job>`; rollback ghi token riêng `C3ROLLBACK_V12 TS=…`.
- Job bị dừng bằng tín hiệu (TERM/INT/HUP) ⇒ `trap` gỡ PAUSE **chỉ khi** còn đúng token của job, rồi Telegram.
- Job chết cứng (kill -9 / Oracle reboot) ⇒ tiến trình canh trên 242 (`setsid … sleep WD_PAUSE_MAX_S`, mặc định 2700 s
  ≫ deploy dài nhất ~20′) gỡ PAUSE nếu **vẫn** là token của job. PAUSE đã bị rollback/người vận hành ghi đè ⇒ không động tới.
- Exit 2 (rollback tự động lỗi): PAUSE do rollback ghi ⇒ giữ (cần xử lý tay như cũ).

## Pin / test
- `RB_MD5` = md5 `rollback_v12.sh` mới `b03233d45d57e2fed287a80924d4e2a3`.
- fake242 §29 (backup/khôi phục cùng TS, backup sai md5 ⇒ dừng, marker NONE, trap TERM, kill -9 ⇒ tự gỡ, token khác ⇒ không gỡ):
  **TEST PASS 249/249**.
