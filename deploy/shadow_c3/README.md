# deploy/shadow_c3 — bản tham chiếu triển khai Shadow C3 (paper)

Đây là **bản version-control** của các file triển khai shadow C3. File **live** thực tế nằm
ngoài repo:

| File repo | Vị trí live trên Oracle |
|---|---|
| `env.sh` | `/home/ubuntu/shadow_c3/app/conf/env.sh` |
| `run_foreground.sh` | `/home/ubuntu/shadow_c3/app/bin/run_foreground.sh` |
| `shadow-c3.service` | `/etc/systemd/system/shadow-c3.service` |
| `shadow-c3-redis.service` | `/etc/systemd/system/shadow-c3-redis.service` |

Chi tiết + bảng cấu hình + kết quả verify: `docs/RESULT_SHADOW_T170_FIX.md`.
Quyết định chuyển sang FLATGRID KEEPLEG0 (2026-09-19): `docs/DECISION_SHADOW_FLATGRID_KEEPLEG0.md`.

## Đặc điểm
- **Paper only**: `SHADOW_NO_PUSH=true` (hardcode trong `LiveProfileC3` + đặt lại trong env.sh).
  TUYỆT ĐỐI không tắt.
- **Cấu hình chạy hiện tại = FLATGRID KEEPLEG0** (từ 2026-09-19): base T170 (gate
  `SIM_GATE_DYN_SCALE=1.70`, `SELECTOR_ONLY_ENTRY=0`, loser time-stop 168h) NHƯNG DCA grid
  `1,1,1,1` / scale `6.0` (thay `1,1,3,8` / `19.5` của T170 gốc). Nguồn: `profiles/t170_flat_keepleg0.properties`.
  PHẢI đổi CẢ HAI dòng WEIGHTS+SCALE — đổi mình WEIGHTS = KEEPSCALE (phóng to 3.25x, SAI).
- **Watchdog**: systemd `Restart=always` (chết → bật lại ~15s) + `WantedBy=multi-user.target`
  (reboot host → tự lên). `shadow-c3` `Requires` `shadow-c3-redis` (Redis lên trước).
- Log ra **journald** (không append file — tránh runaway đầy đĩa).

## Deploy lại (nếu cần)
```
# env + launcher
cp env.sh            /home/ubuntu/shadow_c3/app/conf/env.sh
cp run_foreground.sh /home/ubuntu/shadow_c3/app/bin/run_foreground.sh
chmod +x /home/ubuntu/shadow_c3/app/bin/run_foreground.sh
# systemd units
sudo cp shadow-c3.service shadow-c3-redis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now shadow-c3-redis.service
sudo systemctl enable --now shadow-c3.service
```

## API key
Key Binance hardcode trong `src/main/java/com/binance/chuyennd/config/PrivateConfig.java`
(biên dịch vào jar). Cập nhật = sửa file đó + rebuild jar + deploy jar + restart service.
Với paper, key không hợp lệ (lỗi -2014 khi poll vị thế) KHÔNG chặn sinh entry.
