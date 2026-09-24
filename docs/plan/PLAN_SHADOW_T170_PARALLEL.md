# PLAN — Shadow T170 song song (paper, đề xuất, CHƯA deploy) (2026-09-20)

> **Trạng thái tài liệu này: CHỈ LÀ KẾ HOẠCH.** Không có gì trong task sinh ra tài liệu này
> được deploy, khởi động hay sửa trên Oracle/242. Mọi lệnh `systemctl`, `daemon.sh start`,
> file `.service` thật trong `/etc/systemd/system/` đều **CHƯA chạy** — đây là bản nháp để
> Uni đọc và tự quyết có triển khai hay không, triển khai khi nào, bằng cách nào.
> Không SSH vào box 242 (live tiền thật) ở bất kỳ bước nào trong plan này.

## 0. Vì sao cần thêm một shadow instance thứ hai

- Incumbent nghiên cứu hiện tại là **T170** (`profiles/x1_gs_t170.properties`,
  `SIM_GATE_DYN_SCALE=1.70`, DCA `1,1,3,8` / scale `19.5`) — xác nhận qua backtest là
  ALPHA (`docs/BETA_DECOMP_T170.md`: pct_beta=3.9%, |t(a)|=4.37) nhưng **chưa từng chạy
  forward** đúng cấu hình này.
- Shadow production hiện tại (`/home/ubuntu/shadow_c3/`) đã bị đổi sang **FLATGRID
  KEEPLEG0** từ 2026-09-19 (`docs/decisions/DECISION_SHADOW_FLATGRID_KEEPLEG0.md`): DCA `1,1,1,1` /
  scale `6.0` — một quyết định khẩu vị rủi ro khác, KHÔNG PHẢI T170. Từ ngày đó, shadow hiện
  tại không còn tích luỹ bằng chứng forward nào cho T170 gốc.
- Cách duy nhất có bằng chứng forward thật (không phải backtest) cho T170 là chạy **một
  instance thứ hai** khớp đúng T170, song song với shadow FLATGRID KEEPLEG0 đang chạy,
  không đụng vào nó.

## 1. Cấu trúc instance riêng biệt

### 1.1 Thư mục — hoàn toàn tách khỏi `shadow_c3/`

```
/home/ubuntu/shadow_t170/
├── app/
│   ├── bin/{daemon.sh, run_foreground.sh, start.sh}   # copy nguyên mẫu từ shadow_c3/app/bin/*
│   ├── conf/env.sh                                     # env T170 THẬT (mục 1.3), KHÔNG copy KEEPLEG0
│   ├── config.properties                               # copy shadow_c3/app/config.properties,
│   │                                                    #   đổi phần hạ tầng (mục 1.2)
│   ├── target/binance-java-sdk-1.2.4.jar               # copy jar đang chạy trên shadow_c3
│   ├── logs/ (rỗng, log thật ra journald)
│   ├── run/  (pidfile nếu chạy daemon.sh thủ công)
│   └── storage/
├── bin/health.sh          # bản sao health.sh của shadow_c3, đổi biến B= sang shadow_t170
├── redis/redis-shadow-t170.conf
├── health.log
├── ledger.csv             # ShadowBookC3 ghi ra đây — KHÔNG trùng ledger.csv của shadow_c3
├── ledger_from_log.csv
└── open_positions.csv
```

Không sửa bất kỳ file nào trong `/home/ubuntu/shadow_c3/`. Hai cây thư mục độc lập hoàn toàn.

### 1.2 Redis riêng — port riêng, không chung key-space

Shadow hiện tại dùng cluster Redis 1-node tại `127.0.0.1:7301` (bus port cluster tự động
`17301`). Instance mới phải dùng **port khác hẳn**, ví dụ:

```
port 7302
bind 127.0.0.1
cluster-enabled yes
cluster-config-file /home/ubuntu/shadow_t170/redis/nodes-7302.conf
cluster-node-timeout 5000
appendonly no
save ""
dir /home/ubuntu/shadow_t170/redis
pidfile /home/ubuntu/shadow_t170/redis/redis-7302.pid
logfile /home/ubuntu/shadow_t170/redis/redis-7302.log
daemonize yes
maxmemory 512mb
maxmemory-policy noeviction
```

Bus port cluster sẽ tự là `17302` (data port + 10000, theo quy ước Redis Cluster — giống
7301→17301 hiện tại). Đã kiểm `ss -tln` trên Oracle: 7302/17302 hiện **chưa ai dùng** (danh
sách cổng đang mở: 22, 111, 3222, 3225, 3226, 7301, 17301, 18789, 46705 — không có 7302).

🔴 **Vì sao bắt buộc port + instance Redis riêng**: `docs/experiment/L1_SHADOW_C3.md` mục 8(b) đã cảnh
báo trỏ vào Redis 242 sẽ `blpop` cướp lệnh của bot live. Cùng lý do đó áp dụng chéo giữa hai
shadow: nếu hai instance dùng chung một Redis (dù cùng là paper), state paper của T170 và của
FLATGRID KEEPLEG0 sẽ ghi đè/lẫn key-space của nhau, làm hỏng cả hai bộ số liệu.

### 1.3 Env — khớp CHÍNH XÁC `profiles/x1_gs_t170.properties`

`SHADOW_NO_PUSH=true` là **bắt buộc, không được đổi** (paper, không gửi lệnh thật) — giữ
nguyên style hiện tại: set trong `env.sh` VÀ vẫn hardcode `true` trong `LiveProfileC3` khi
`LIVE_PROFILE=c3_shadow` được bật (an toàn hai lớp).

Bảng env đề xuất cho `shadow_t170/app/conf/env.sh` (nguồn: `profiles/x1_gs_t170.properties`,
đối chiếu game plan đã dùng khi fix shadow hiện tại — `docs/result/RESULT_SHADOW_T170_FIX.md`):

| Param | Giá trị (= T170 gốc) |
|---|---|
| `LIVE_PROFILE` | `c3_shadow` |
| `SHADOW_NO_PUSH` | `true` (BẮT BUỘC) |
| `PAPER_EQUITY` | `35000` |
| `CAPITAL_START` | `35000` |
| `SELECTOR_RANK_TOPK` | `8` |
| `SELECTOR_ONLY_ENTRY` | `0` |
| `SIM_MIN_MOMENTUM_15M` | `0.008` |
| `SIM_RATE_PROFIT_STOP_MARKET` | `0.07` |
| `SIM_TS_GIVEBACK` | `1` |
| `TS_GIVEBACK_RATIO` | `0.5` |
| `SIM_LOSER_TIME_STOP_HOURS` | `168` |
| `TIER_FLAT` | `1` |
| `SIM_GATE_DYN_SCALE` | `1.70` |
| `DCA_GRID_ENABLED` | `true` |
| `DCA_GRID_WEIGHTS` | `1,1,3,8` (**KHÔNG phải `1,1,1,1` của KEEPLEG0**) |
| `DCA_GRID_SCALE` | `19.5` (**KHÔNG phải `6.0` của KEEPLEG0**) |
| `SIM_FIX_B1/B2/B3` | `true` |
| `SIM_BREAKER_MODE` | `OFF` |
| `SIM_APPLY_FUNDING` / `SIM_FUNDING_MARK` | `true` |
| `SHADOW_C3_DIR` | `/home/ubuntu/shadow_t170` (đổi, KHÔNG trỏ vào dir instance kia) |
| `S1_MODEL_ONNX` | giữ nguyên đường dẫn model hiện dùng |

⚠️ **Bẫy đã xảy ra với instance hiện tại** (ghi trong `docs/decisions/DECISION_SHADOW_FLATGRID_KEEPLEG0.md`):
copy nhầm cả hai dòng DCA từ file KEEPLEG0 thay vì từ `x1_gs_t170.properties` sẽ âm thầm biến
instance mới thành bản sao thứ hai của FLATGRID chứ không phải T170. Bước verify ở dưới tồn
tại chính là để bắt lỗi này.

### 1.4 Verify env khớp T170 — KHÔNG cần chạy lại full backtest

Nguồn sự thật: `profiles/x1_gs_t170.properties`, gắn với run backtest T170 chuẩn
md5 `printDone.csv` = **`efb793e2468ca3a7318da0f0ad23d4fc`** (1089 legs, đã chạy và ghi trong
`docs/result/RESULT_SHADOW_T170_FIX.md`). Chạy lại backtest để verify env là dư thừa — hash đó đã tồn
tại rồi, cái cần kiểm là **giá trị đang chạy có khớp file profile đã sinh ra hash đó không**.
Hai bước rẻ, đã dùng thành công khi fix shadow hiện tại lần trước:

1. **Diff cấu hình dạng bảng** (tĩnh, trước khi chạy): so từng dòng `env.sh` mới với
   `profiles/x1_gs_t170.properties`, liệt kê type bảng như mục 1.3. Làm bằng tay hoặc
   `diff <(grep -oP '(?<=export )[A-Z_0-9]+=.*' shadow_t170/app/conf/env.sh | sort) \
        <(grep -oP '^[A-Z_0-9]+=.*' profiles/x1_gs_t170.properties | sort)` — lệch dòng nào
   hiện ra dòng đó.
2. **Đối chiếu runtime qua `/proc/<pid>/environ`** (sau khi start, xem mục 3): đúng kỹ thuật
   đã dùng ở `docs/result/RESULT_SHADOW_T170_FIX.md` Bước 4 — `cat /proc/<pid>/environ | tr '\0' '\n'
   | grep -E 'SIM_GATE_DYN_SCALE|DCA_GRID_WEIGHTS|DCA_GRID_SCALE|SELECTOR_ONLY_ENTRY|
   SIM_LOSER_TIME_STOP_HOURS|SHADOW_NO_PUSH'` rồi so với bảng 1.3. Đây là bằng chứng process
   **thật sự đang** chạy với env đó (khác diff tĩnh chỉ chứng minh file đúng, không chứng
   minh process đã nạp đúng file).

Cả hai bước đều **đọc, không backtest, không cần Xmx14g**, chạy trong vài giây.

## 2. systemd unit riêng (bản nháp — CHƯA cài vào `/etc/systemd/system/`)

Bản tham chiếu version-control nên đặt tại `deploy/shadow_t170/` trong repo (song song
`deploy/shadow_c3/` đã có), gồm 4 file mirror 1:1 cấu trúc hiện tại, chỉ đổi tên/đường dẫn:

**`shadow-t170.service`** (nháp):
```ini
[Unit]
Description=Shadow T170 (paper, SHADOW_NO_PUSH=true) BinanceOrderTradingManager
After=network-online.target shadow-t170-redis.service
Wants=network-online.target
Requires=shadow-t170-redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/shadow_t170/app
ExecStart=/home/ubuntu/shadow_t170/app/bin/run_foreground.sh
Restart=always
RestartSec=15
# stdout/err -> journald RIÊNG (đơn vị riêng => `journalctl -u shadow-t170` tách hẳn khỏi
# `journalctl -u shadow-c3`, không lẫn log khi phân tích sau này).
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**`shadow-t170-redis.service`** (nháp):
```ini
[Unit]
Description=Shadow T170 Redis (port 7302 single-node cluster, paper state store)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/bin/redis-server /home/ubuntu/shadow_t170/redis/redis-shadow-t170.conf --daemonize no
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`run_foreground.sh` mirror nguyên mẫu, chỉ đổi `cd /home/ubuntu/shadow_t170/app`.
`start.sh` mirror nguyên mẫu (`-Xms1g -Xmx4g`, xem mục 3 vì sao giữ nguyên số này).

Log tách biệt hoàn toàn qua **tên unit khác nhau** (`shadow-t170` vs `shadow-c3`) —
`journalctl -u shadow-t170` và `journalctl -u shadow-c3` không lẫn nhau, không cần cấu hình
gì thêm ở tầng journald.

## 3. Ước lượng RAM/CPU cần thêm

Số đo thật trên Oracle lúc soạn plan này (2026-09-20 ~09:15 UTC+7, `free -g` + `health.log`):

- **Máy: 4 core / 23G RAM** (xác nhận qua `nproc` + `free -g`).
- `free -g` hiện tại: `total=23G used=3G free=14G buff/cache=5G available=19G` (đo lúc
  shadow-c3 đang **DOWN** — xem cảnh báo mục 5; số `available` này sẽ thấp hơn khi shadow-c3
  chạy bình thường).
- RSS thực đo của **một** instance shadow qua `health.log` 12 giờ gần nhất: dao động
  **2.6G – 3.2G** (KHÔNG phải 1.7G như ghi chú cũ trong `AGENT_RUNBOOK.md` §0 mục 9 — số đó
  đã lỗi thời, RSS đã tăng theo số vị thế paper mở song song, ví dụ `open_positions.csv` hiện
  có 17 dòng vị thế mở). JVM cap `-Xmx4g` (`start.sh`), nên **trần lý thuyết per-instance =
  4G**, thực tế quan sát ~2.6-3.2G.
- Redis instance hiện tại: `maxmemory 512mb` (trần cấu hình), dữ liệu paper rất nhỏ (không
  phải sổ lệnh thật) — RSS Redis quan sát không đáng kể so với JVM.
- **Sim nghiên cứu nặng dùng `-Xmx14g`** (AGENT_RUNBOOK §2).

### 3.1 Cộng dồn khi CẢ HAI shadow + sim nghiên cứu chạy cùng lúc

| Thành phần | RAM (trần cấu hình) | RAM (RSS thực đo/ước lượng) |
|---|---|---|
| shadow-c3 (FLATGRID KEEPLEG0) JVM | 4G | ~2.6-3.2G |
| shadow-c3 Redis (7301) | 0.5G | nhỏ, <0.1G thực tế |
| shadow-t170 (mới) JVM | 4G | ~2.6-3.2G (cùng loại workload) |
| shadow-t170 Redis (7302, mới) | 0.5G | nhỏ, <0.1G thực tế |
| collector nhỏ (liq_ws.py, collect_derivs.py) | — | <0.1G |
| **Cộng 2 shadow + collector (trần / thực tế)** | **~9G** | **~5.5-6.5G** |
| Sim nghiên cứu (`-Xmx14g`) | 14G | tuỳ workload, có thể chạm gần trần |
| **TỔNG nếu chạy đồng thời (trần / thực tế)** | **~23G** | **~19.5-20.5G** |
| RAM máy | 23G | 23G |

**Kết luận bằng số đo RSS thực tế**: 2 shadow cộng dồn ~5.5-6.5G, cộng sim 14G ≈ 20G / 23G —
**còn dư ~3G cho OS/buffer/cache**, khá sát. Nếu tính theo **trần cấu hình** (`-Xmx` cả ba
tiến trình chạm đỉnh cùng lúc — kịch bản xấu nhất, ít khả năng nhưng không loại trừ), tổng
chạm ~23G, **gần như không còn dư cho OS** — rủi ro OOM-kill hoặc swap (máy hiện có 0
swap, xem `free -g`).

🔴 **Nhưng đây KHÔNG phải nút thắt thật**: `AGENT_RUNBOOK.md` §2 mục 4 nói rõ **"Chỉ 1 slot
JVM. `pgrep java` phải rỗng. Chạy TUẦN TỰ"** cho sim nghiên cứu — nghĩa là quy tắc vận hành
hiện tại **đã** yêu cầu dừng mọi tiến trình Java khác (kể cả shadow) trước khi chạy sim nặng,
bất kể RAM có đủ hay không (lý do ghi trong runbook có vẻ liên quan quyết định luận/CPU-sharing
nhiều hơn là chỉ RAM). Nếu quy tắc đó vẫn còn hiệu lực nguyên văn, thêm shadow thứ hai **không
đổi bản chất vấn đề**, chỉ đổi từ "dừng 1 shadow trước khi chạy sim" thành "dừng 2 shadow
trước khi chạy sim" — cần một script gộp `shadow_stop_all.sh` / `shadow_start_all.sh` (dừng/mở
cả `shadow-c3` + `shadow-t170` bằng một lệnh) để không quên mất một instance, gây khoảng trống
âm thầm trong bằng chứng forward của instance bị quên.

**Uni cần xác nhận 1 trong 2 phương án** trước khi deploy:

- **(a) Giảm `-Xmx` sim nghiên cứu xuống, ví dụ `10g`**, khi cần chạy sim đồng thời với cả
  hai shadow (không dừng shadow) — đổi lại thời gian chạy sim có thể chậm hơn hoặc một số sim
  rất nặng có thể không đủ heap; cần thử nghiệm lại xem `10g` có đủ cho các sim 48-tháng hiện
  tại hay không (chưa đo — nằm ngoài phạm vi plan này).
- **(b) Chạy shadow instance thứ hai trên một máy KHÁC** — đây CHỈ LÀ GỢI Ý, **không giả định
  có máy nào sẵn có**. Agent này không có thông tin gì về việc có server thứ hai khả dụng hay
  không. **Cần Uni xác nhận có máy khác hay không** trước khi cân nhắc phương án này.
- (Phương án ngầm định thứ ba, giữ nguyên hiện trạng): tiếp tục áp dụng "dừng cả hai shadow
  trước khi chạy sim nặng, mở lại sau" — không cần đổi gì về RAM, chỉ cần script gộp dừng/mở
  hai instance cho gọn và một checklist để không quên mở lại.

**CPU**: 4 core. Cả hai shadow là workload nhẹ, tick 15 phút/lần, không phải workload CPU-bound
liên tục (giống hệt shadow hiện tại đang chạy chung máy với các collector cron mà không có
than phiền CPU nào ghi nhận). Sim nghiên cứu mới là workload CPU-bound nặng — quy tắc "chạy
TUẦN TỰ, `pgrep java` rỗng" ở trên đã che luôn rủi ro tranh CPU giữa sim và shadow, miễn Uni
vẫn giữ quy tắc đó.

## 4. Đo MTM (mark-to-market) định kỳ — KHÔNG cần SSH vào box 242

Nguyên tắc: instance mới tự ghi "sổ giấy" cục bộ trên Oracle, không truy vấn bất kỳ hệ thống
tiền thật nào. Cơ chế đã có sẵn (dùng lại nguyên mẫu, không cần phát minh mới):

### 4.1 Những gì đã có sẵn ở shadow hiện tại (đọc, xác nhận đang hoạt động)
- `ShadowBookC3` tự ghi `ledger.csv` (mỗi lệnh đóng: exit + pnl thật đã tính từ giá paper)
  và `open_positions.csv` (vị thế đang mở: `sym,ts_open,entry,qty,rank,symbol_pred,price_sl,
  peak_rate`, cộng dòng `#realized,<tổng PnL đã chốt>` ở đầu file).
- Khi khởi động, log in ra dòng tổng: `[SHADOW] so vi the giay khoi tao ... open=N
  realized=<X> paperEquity=<Y>` — đã xác nhận thấy dòng này trong journal thật
  (`Sep 20 04:14:01 ... open=17 realized=1456.9377046332 paperEquity=35000.0`).
- `bin/health.sh` (cron mỗi giờ) đã ghi `health.log` gồm RSS, RAM/disk còn trống, tick cuối,
  đếm would-BUY/would-CLOSE/ledgerRows — nhưng **chưa có equity MTM tổng hợp** (chỉ có
  realized tại thời điểm khởi động trong log, không phải mỗi giờ).

### 4.2 Đề xuất cho `shadow_t170` — 2 phương án, không phương án nào đụng 242

**Phương án A (không cần sửa code, làm được ngay, ghi trước)**: viết `shadow_t170/bin/
health.sh` (bản sao `shadow_c3/bin/health.sh`, đổi biến `B=`), cộng thêm một script Python
nhỏ chạy trong cùng cron giờ đó:
1. Đọc `open_positions.csv` (entry, qty, symbol) — dữ liệu local, không cần 242.
2. Lấy giá mark hiện tại của từng symbol từ **cache ticker cục bộ** mà chính app
   `shadow_t170` đang dùng để tick (file dưới `app/storage/ticker/...` hoặc đọc lại
   Aerospike **namespace `ticker` chỉ-đọc** mà shadow vốn đã dùng để lấy feed — đây là đọc dữ
   liệu THỊ TRƯỜNG công khai qua Aerospike, không phải SSH/đọc trạng thái tài khoản của 242,
   đúng như shadow hiện tại đã làm từ trước, không phải cách truy cập mới).
3. Tính `unrealized_i = qty_i * (mark_i - entry_i)` mỗi vị thế, cộng `realized` (đọc từ dòng
   `#realized` của `open_positions.csv`) + `PAPER_EQUITY` (hằng số 35000, đọc từ env) ⇒
   `mtm_equity ≈ PAPER_EQUITY + realized + Σunrealized_i`.
4. Ghi một dòng mỗi giờ vào `shadow_t170/mtm.log`:
   `ts=... mtm_equity=... realized=... unrealized_sum=... n_open=...`.

Đây là ước lượng gần đúng (không tính phí funding/slippage tick-by-tick), đủ để theo dõi xu
hướng equity paper theo thời gian mà không phải chờ lệnh đóng mới thấy PnL.

**Phương án B (chính xác hơn, cần một dòng code nhỏ trong `ShadowBookC3`, KHÔNG làm trong
task này — chỉ đề xuất)**: vì app đã tính `unProfit`/mark price nội bộ mỗi tick để phục vụ
trailing-stop, thêm MỘT dòng log INFO mỗi tick (hoặc mỗi giờ, chặn bằng timestamp) xuất thẳng
`mtm_equity` đã tính sẵn trong bộ nhớ, rồi `health.sh` chỉ cần `tail`/`grep` dòng đó ra
`mtm.log` — chính xác hơn Phương án A (dùng đúng logic PnL nội bộ, không tính lại bằng tay) và
tốn ít hơn 10 dòng code. Đánh đổi: cần sửa code + build lại jar + deploy jar mới, nằm ngoài
phạm vi "chỉ đọc" của task này — **Uni quyết định nếu muốn**, có thể làm cùng lúc lần đầu
build jar cho `shadow_t170` (jar giống hệt jar `shadow_c3` đang chạy nếu không làm B).

Khuyến nghị: bắt đầu bằng **Phương án A** (deploy ngay, dùng jar hiện có, không rebuild), cân
nhắc B sau nếu A cho sai số quá lớn khi đối chiếu với `ledger.csv` (lệnh đã đóng thật).

## 5. Lỗi vận hành đang treo

### 5.1 `-2014 API-key format invalid` — XÁC NHẬN LẠI, còn xảy ra

Đọc `journalctl -u shadow-c3` (2000 dòng gần nhất, tính đến 2026-09-20 ~09:1x UTC+7):
**117 dòng** lỗi `com.binance.connector.futures.client.exceptions.BinanceClientException:
{"code":-2014,"msg":"API-key format invalid."}`, lần cuối lúc **06:13:10** (ngay trước khi
service dừng — xem mục 5.2). Đúng như `docs/result/RESULT_SHADOW_T170_FIX.md` đã ghi nhận: lỗi này
đến từ poll `positionRisk`/`account` bằng API key hardcode trong `PrivateConfig.java` không
hợp lệ, **không chặn shadow paper** (entry sinh từ feed ticker + selector + gate, độc lập REST
key; sổ giấy là `ShadowBookC3`).

**Ghi vào plan**: nếu deploy `shadow_t170` bằng jar hiện tại (copy nguyên từ `shadow_c3`), lỗi
`-2014` này **sẽ lặp lại y hệt** trên instance mới, vì cùng jar = cùng key hardcode. Đây không
phải lỗi mới do cấu hình T170 sinh ra. **Uni cần tự cập nhật API key** (sửa
`PrivateConfig.java` + `mvn package` + deploy jar mới vào cả hai instance nếu muốn hết -2014)
**trước khi deploy shadow T170 mới, nếu không sẽ gặp lỗi tương tự** — agent này KHÔNG tự sửa
key hay bất kỳ cấu hình nào liên quan đến key.

### 5.2 Phát hiện phụ (ngoài phạm vi sửa của task này, chỉ ghi nhận): shadow-c3 hiện đang DOWN

Tại thời điểm đọc log cho plan này, `systemctl is-active shadow-c3` = **`failed`** (dừng sạch
lúc **2026-09-20 06:13:46 +07**, `status=143` = nhận SIGTERM từ `systemctl stop`, tức có ai đó
hoặc script nào đó chủ động dừng — không phải crash). `shadow-c3-redis` vẫn `active`.
`health.log` xác nhận 3 lần cron liên tiếp sau đó (`00:00`, `01:00`, `02:00` UTC — tương ứng
07:00/08:00/09:00 giờ +07) đều ghi `pid=- DOWN`. Tức là **shadow production (FLATGRID
KEEPLEG0) đã ngừng tích luỹ bằng chứng forward khoảng 3 giờ** tại thời điểm soạn plan này.

Task này là **chỉ đọc** — agent **không khởi động lại** `shadow-c3`. Ghi nhận ở đây để Uni
biết và tự quyết có cần `sudo systemctl start shadow-c3` lại hay không; đây không phải hệ quả
của việc soạn plan này (mọi lệnh trong quá trình soạn plan chỉ là `cat`/`free`/`journalctl`/
`git status`, không có lệnh `systemctl start/stop/restart` nào được agent này chạy).

## 6. Checklist trước khi (nếu) deploy — để Uni tick khi quyết định làm

- [ ] Xác nhận phương án RAM (mục 3.1: (a) hạ `-Xmx` sim, (b) máy khác, hoặc giữ nguyên +
      script dừng/mở gộp 2 shadow).
- [ ] Xác nhận phương án MTM logging (mục 4.2: Phương án A ngay, hay B cần rebuild jar).
- [ ] Cập nhật API key nếu muốn hết `-2014` (mục 5.1) — không bắt buộc cho paper.
- [ ] Kiểm tra lại `shadow-c3` đang DOWN hay UP (mục 5.2) trước khi bắt đầu, để không nhầm
      trạng thái nền khi so sánh hai shadow sau này.
- [ ] Tạo `deploy/shadow_t170/{env.sh, run_foreground.sh, shadow-t170.service,
      shadow-t170-redis.service, README.md}` trong repo (bản tham chiếu, mirror
      `deploy/shadow_c3/`).
- [ ] Copy `shadow_c3/app/target/*.jar` → `shadow_t170/app/target/` (cùng jar, không rebuild,
      trừ khi chọn Phương án B ở mục 4.2).
- [ ] Diff tĩnh env.sh mới vs `profiles/x1_gs_t170.properties` (mục 1.4 bước 1) — PASS trước
      khi start.
- [ ] `sudo cp` 2 file `.service` vào `/etc/systemd/system/`, `daemon-reload`, `enable --now`
      **redis trước, app sau** (giống thứ tự `Requires=` đã khai báo).
- [ ] Verify `/proc/<pid>/environ` (mục 1.4 bước 2) — đối chiếu đủ các key ở bảng 1.3.
- [ ] Kill-test watchdog (giống `docs/result/RESULT_SHADOW_T170_FIX.md` Bước 2): `kill -9 <PID>`,
      xác nhận systemd tự bật lại trong <1 phút, `NRestarts` tăng đúng 1.
- [ ] Xác nhận `SHADOW_NO_PUSH=true` trong `/proc/<pid>/environ` VÀ `createOrder(` = 0 trong
      log sau ít nhất 1 tick — trước khi coi instance là "đang chạy đúng".
- [ ] Xác nhận `redis-cli -p 7302 ping` = `PONG`, và `redis-cli -p 7302 keys '*'` không trùng
      bất kỳ key nào đang có trên `redis-cli -p 7301 keys '*'` (key-space thật sự tách biệt).

## 7. Việc KHÔNG nằm trong phạm vi plan này

- Không quyết định sẵn phương án RAM/máy khác — để Uni chọn.
- Không sửa API key hay `PrivateConfig.java`.
- Không khởi động lại `shadow-c3` đang DOWN.
- Không tạo file `.service` thật, không `systemctl enable/start` gì, không chạy Java/Python
  nào cho `shadow_t170`.
- Không đụng box 242 dưới bất kỳ hình thức nào (kể cả đọc).
