# RESULT — Shadow T170 fix + watchdog (2026-09-18)

## Bối cảnh
Shadow C3 (`/home/ubuntu/shadow_c3/`) là instance **paper** (`SHADOW_NO_PUSH=true`,
`LIVE_PROFILE=c3_shadow`) dùng để chạy song song cấu hình **T170** trên dữ liệu live.
T170 = C3 baseline + gate `SIM_GATE_DYN_SCALE=1.70` (nguồn chuẩn:
`profiles/x1_gs_t170.properties`, run md5 `efb793e2468ca3a7318da0f0ad23d4fc`, 1089 legs).

Trước khi sửa, shadow **không sinh entry nào**. Chẩn đoán: hai vấn đề độc lập:
1. **Process chết & không tự bật lại** — java chết ~06/09 22:05 (local), host reboot 09/09,
   không có cơ chế auto-restart ⇒ DOWN ~12 ngày.
2. **Cấu hình lệch T170** — gate mặc định 1.0 (= T100), `SELECTOR_ONLY_ENTRY=1` (tắt
   market-signal/BIG_DOWN leg), DCA tắt. Kể cả khi sống, entry cũng sai/hiếm.

Task này sửa cả hai: (1) env.sh trung thực T170, (2) watchdog systemd (auto-restart khi
process chết + khi host reboot), (3) restart & verify. **Không đổi** `SHADOW_NO_PUSH=true`.

## Bước 0 + 1 — Bảng đối chiếu cấu hình (trước/sau)
Nguồn chuẩn T170: `profiles/x1_gs_t170.properties`. Env shadow đọc theo **live path**
(`Cfg.get()` → env; `Configs` static block "SIM ABLATION" áp env `SIM_*` vào field kể cả
trên live). File sửa: `/home/ubuntu/shadow_c3/app/conf/env.sh` (backup `env.sh.bak_20260918`).

| Param | T170 (chuẩn) | Shadow TRƯỚC | Shadow SAU | Ảnh hưởng |
|---|---|---|---|---|
| `SIM_GATE_DYN_SCALE` | 1.70 | *unset* → **1.0 (=T100)** | **1.70** | Gate entry — sai bản chất nếu 1.0 |
| `SELECTOR_ONLY_ENTRY` | 0 | **1** (tắt market/BIG_DOWN) | **0** | Bật lại market-signal + BIG_DOWN leg |
| `DCA_GRID_ENABLED` | true | *unset* → **false** | **true** | Bật DCA grid |
| `DCA_GRID_WEIGHTS` | 1,1,3,8 | **1,0,0,0** | **1,1,3,8** | Trọng số các bậc DCA |
| `DCA_GRID_SCALE` | 19.5 | *unset* → **1.0** | **19.5** | Khoảng cách grid |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | *unset* → **0** | **168** | Time-stop cho lệnh lỗ |
| `CAPITAL_START` | 35000 | *unset* (fallback config.properties=35000) | **35000** (ghi rõ) | Gốc tính size lệnh; hành vi không đổi |
| `SIM_APPLY_FUNDING` | true | *unset* | **true** | Kế toán funding (PnL paper, không ảnh hưởng entry) |
| `SIM_FUNDING_MARK` | true | *unset* | **true** | nt |
| `SIM_FIX_B1/B2/B3` | true | *unset* (default true) | **true** (ghi rõ) | 3 bug-fix; default đã true |
| `SIM_BREAKER_MODE` | OFF | *unset* (default OFF) | **OFF** (ghi rõ) | default đã OFF |
| `SELECTOR_RANK_TOPK` | 8 | 8 | 8 | không đổi |
| `SIM_MIN_MOMENTUM_15M` | 0.008 | 0.008 | 0.008 | không đổi |
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 | 0.07 | 0.07 | không đổi |
| `SIM_TS_GIVEBACK` | 1 | 1 | 1 | không đổi |
| `TS_GIVEBACK_RATIO` | 0.5 | 0.5 | 0.5 | không đổi |
| `TIER_FLAT` | 1 | 1 | 1 | không đổi |
| `LIVE_PROFILE` | (shadow) | c3_shadow | c3_shadow | **GIỮ NGUYÊN** |
| `SHADOW_NO_PUSH` | (shadow) | true | **true** | **GIỮ NGUYÊN — paper, không ra lệnh thật** |
| `PAPER_EQUITY` | (shadow) | 35000 | 35000 | **GIỮ NGUYÊN** |

Không param nào của T170 có giá trị "không rõ" → không cần STOP. Mọi giá trị lấy trực tiếp
từ `x1_gs_t170.properties`.

## Bước 2 — Watchdog (systemd)
Hai unit systemd đã cài & enable (persist qua reboot vì `WantedBy=multi-user.target`):

- **`/etc/systemd/system/shadow-c3.service`** — chạy java foreground qua
  `bin/run_foreground.sh` (source env.sh rồi exec start.sh). `Restart=always`,
  `RestartSec=15`, `Requires=shadow-c3-redis.service` (Redis lên trước). Log ra **journald**
  (đã bỏ `append:nohup.out` — xem sự cố đĩa bên dưới).
- **`/etc/systemd/system/shadow-c3-redis.service`** — Redis port 7301 (single-node cluster,
  paper state store). `Restart=always`, `RestartSec=5`.

**Kill-test (bắt buộc):** `kill -9 <MainPID>` → sau ~20s systemd tự bật lại:
`OLD_PID=1141990 → NEW_PID=1142340`, `NRestarts 0→1`, `is-active=active`. **PASS** (<1 phút).
Reboot-persistence: `is-enabled shadow-c3 = enabled`, `is-enabled shadow-c3-redis = enabled`.

## Bước 3 — Binance API key (KHÔNG tự điền)
Shadow đọc key từ **`src/main/java/com/binance/chuyennd/config/PrivateConfig.java`**
(`API_KEY` / `SECRET_KEY`, **hardcode**, biên dịch vào jar — không có override qua env/file).
Jar shadow đang chạy: `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar`.

Log hiện có lỗi lặp `Error get position from binance! ... -2014` mỗi 60s: key trong jar
không hợp lệ/hết hạn nên poll `positionRisk` / `account` fail. **Với shadow paper điều này
KHÔNG chặn**: entry sinh từ feed ticker (Aerospike) + selector + gate, hoàn toàn độc lập REST
key; book of record là `ShadowBookC3` (paper), không cần vị thế thật từ Binance. Đã xác nhận
shadow vẫn tick & sinh would-BUY dù có -2014 (xem Bước 4).

**Để user cập nhật key** (nếu muốn hết -2014 — không bắt buộc cho paper):
1. Sửa `API_KEY`/`SECRET_KEY` trong `PrivateConfig.java`.
2. Rebuild jar (`mvn package`) → deploy vào `/home/ubuntu/shadow_c3/app/target/`.
3. `sudo systemctl restart shadow-c3`.

Kể cả khi key hợp lệ, lệnh thật vẫn bị chặn bởi `SHADOW_NO_PUSH=true` (hardcode trong
`LiveProfileC3` + env) — không ra lệnh thật.

## Bước 4 — Verify (đã restart qua watchdog)
| Mục | Kết quả |
|---|---|
| (a) Process sống | `systemctl is-active shadow-c3 = active`, MainPID 1143857 |
| (b) Đang tick | Tick `Start check level change of market` lúc 11:30:06 UTC; BTC ticker 1000 nến tới 11:29 (data tươi). Tick chạy đúng lưới 15m (`ENTRY_GRID_MIN=15`, giây 06–10) — nên khoảng vài phút mới thấy 1 tick là bình thường, không phải stall |
| (c) Gate 1.70 loaded | `/proc/<pid>/environ`: `SIM_GATE_DYN_SCALE=1.70` (Configs static block áp vào `EntryGate.GATE_DYN_SCALE`) |
| (d) Selector/EntryGate chạy | Tại tick 11:30:06: `[S1] score`=1, **would-BUY=8** ứng viên paper sinh ra (SELECTOR_ONLY_ENTRY=0 + DCA on + gate 1.70) |
| (e) SHADOW_NO_PUSH & lệnh thật | `SHADOW_NO_PUSH=true` trong environ; `createOrder(`=0; real order=0 |

Toàn bộ env T170 xác nhận trong `/proc/<pid>/environ` (gate 1.70, SELECTOR_ONLY_ENTRY=0,
DCA 1,1,3,8 / 19.5, LOSER_TIME_STOP=168, CAPITAL_START=35000, SHADOW_NO_PUSH=true).

## Sự cố đĩa (đã xử lý)
Phiên bản unit đầu dùng `StandardOutput=append:.../nohup.out`; cộng với vòng lặp exception
"Redis down" **không backoff** đã ghi ~7.1GB `nohup.out` + ~2GB `full.log` xoay vòng trong
~10 phút → `/` đầy 100%. Đã: dừng service, truncate/xoá log runaway (giải phóng ~9.3G), đổi
unit sang `StandardOutput=journal`/`StandardError=journal` (có cap), thêm
`Requires=shadow-c3-redis` để Redis luôn lên trước ⇒ không còn vòng exception khi khởi động.
Hiện `/` còn ~9.2G free.

## Artifact triển khai (bản tham chiếu trong repo)
File live nằm ngoài repo (`/home/ubuntu/shadow_c3/...`, `/etc/systemd/system/...`). Bản
tham chiếu version-control tại `deploy/shadow_c3/`:
- `env.sh` — env T170 trung thực (không chứa secret).
- `run_foreground.sh` — launcher systemd.
- `shadow-c3.service`, `shadow-c3-redis.service` — 2 unit systemd.
- `README.md` — cách deploy.
