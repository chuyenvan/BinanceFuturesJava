# Runbook — deploy v11d (= v11c + thay đổi CHỈ VẬN HÀNH) lên 242 (OWNER tự chạy)

Căn cứ: `docs/prereg/PREREG_SHADOW2_PROMOTION.md` ADDENDUM d (c49024c1, nhánh research/vz-e1): thay đổi chỉ vận hành **không reset**
cửa sổ promotion 2026-10-21 07:53:59 nếu (1) so bytecode + legacy-equivalence harness offline, (2) ghi sổ C, (3) restart = tự-restart.
Agent KHÔNG chạy gì trong runbook này (không đọc/ghi 242). Lệnh chạy từ **Oracle** (`bash`), giống runbook v11c.

| | |
|---|---|
| Jar mới | `/home/ubuntu/claude_master/v11d/jar/binance-java-sdk-1.2.4.jar_v11d_7767a560` — md5 **`7767a560baac8e3bfb925c85503d032b`** |
| Nguồn | nhánh `v1.1/ops-v11d`, commit code **`2f82b6a4`** (cha `627e9b34` = v11c) — KHÔNG push |
| Jar đang chạy 242 | v11c `eea5adecaff93d3fc350e4d13b3ecb2a` (PID 27434 từ 10-21 19:54:30, tự-restart kế tiếp **10-22 ~07:54:4x**, rồi ~19:55:3x) |
| Mặc định | mọi cờ mới TẮT ⇒ hành vi = v11c y hệt (đã kiểm, §1) |

## 0. Thay đổi (chỉ vận hành)
| cờ env | mặc định | tác dụng | chỗ code |
|---|---|---|---|
| `LIVE_PERIODIC_RESET_HOURS` | 12 (= v11c) | 0 = tắt reset định kỳ 12h; sai/âm/>720 ⇒ 12 + WARN. Đường reset của Reporter (market check trễ >15') giữ nguyên, chỉ log thêm `[OPS-RESET] cause=MARKET_CHECK_STALE …` | `BinanceOrderTradingManager.startThreadAutoRestartProgram`, `ops/OpsConfig`, `Reporter.buildReport` |
| `LIVE_HEARTBEAT` | 0 | 1 = mỗi tick quyết định (đầu `checkMarketLevelChange2Trade`, ~1/phút) chạm mtime file rỗng `run/heartbeat` (`LIVE_HEARTBEAT_FILE`) | `ops/OpsHeartbeat`, `ops/OpsHooks.onTickStart` |
| `LIVE_KILLSW_MODE` | off | `log` = A40+C1–C6 chỉ ghi `[KILLSW] WOULD_TRIGGER code=Cx …` + `[KILLSW] HOURLY …`, không đổi quyết định nào. `act` ở c3_shadow ⇒ **từ chối + WARN, chạy log**; ở c3_live ⇒ v11d chưa cài hành động ⇒ log + WARN | `ops/KillSwitchEngine`, `ops/OpsHooks` |
| (đề xuất env) `-XX:+ExitOnOutOfMemoryError` | — | OOM ⇒ JVM chết hẳn ⇒ watchdog bật lại | `conf/env.sh` |
| (đề xuất env) gc log `logs/gc_%p_%t.log` | — | mỗi JVM 1 file riêng, không bị xoay mất khi start | `conf/env.sh` |
| watchdog `ops/h242_watchdog.sh` | chưa cài | cron */2 trên 242: không có process hoặc heartbeat cũ ⇒ cảnh báo Telegram + start lại | §4 |

Detector kill-switch (log; ngưỡng owner duyệt 10-21, `docs/result/KILLSW_MENU.md` §4 + A40):
- **C1 dữ liệu**: nến BTC mới nhất trong cửa sổ ticker cũ > 180 s (tính từ lúc nến đóng), HOẶC > 10 % symbol "đang sống" (nến cuối trong 60') thiếu nến phút hiện tại, HOẶC không có dữ liệu thị trường > 240 s (tick bỏ vòng vì thiếu BTC).
- **C2 trượt giá** > 2,5 %: sổ GIẤY không có fill thật (giá vào = close nến quyết định) ⇒ **N/A** (HOURLY in `C2=NA`). Hàm có sẵn cho c3_live, chưa nối.
- **C3 API** ≥ 5 lỗi liên tiếp: c3_shadow không có API đặt lệnh ⇒ đo trên REST đồng bộ vị thế `getAllPositionInfos` mỗi phút (null/rỗng = lỗi; có 44 vị thế LEGACY nên rỗng = lỗi).
- **C4 phơi nhiễm**: vị thế GIẤY mở > 90 HOẶC U = margin/equity ≥ `U_MAX` (trần margin). **LEGACY không tính.**
- **C5 sống**: không có tick quyết định > 300 s (trong JVM; JVM chết/treo ⇒ watchdog).
- **C6/A40**: DD MTM sổ giấy (PAPER_EQUITY + realized + MTM cụm mở; đỉnh = max(PAPER_EQUITY, đỉnh lưu `run/killsw_peak`, equity đã thấy)) ≤ −40 %. **LEGACY không tính.**
- Đặc tả `act` (cho c3_live sau này, CHƯA cài): C1–C5 ⇒ dừng mở lệnh mới + Telegram, vẫn quản lý vị thế; C6/A40 ⇒ đóng hết + dừng, chờ owner.
- Log: cạnh lên `edge=START`, lặp tối đa 1 dòng/phút/mã khi còn đạt (`edge=CONT`), hết đạt `[KILLSW] CLEAR`; mỗi giờ 1 dòng `HOURLY` (met/edge theo mã).
  Lưu ý: C1 MISSING đo lúc tick (giây 3–10) — nếu collector ghi nến muộn cho một phần symbol, C1 có thể đạt thường xuyên. Đây là đo, không hành động; MASTER đọc sau 24–48h rồi mới bàn `act`.

## 1. Kết quả kiểm offline (Oracle, 10-21 22:15–22:48, không chạm 242)
- **Tái lập build**: build lại 627e9b34 không sửa ⇒ 8198/8198 entry trùng CRC với eea5adec ⇒ so sánh dưới đây chính xác.
- **Unit test** (`mvn -o package`): 393 test, 0 fail, 1 skip có sẵn; mới 32: `KillSwitchEngineTest` 21 (mode, mọi detector ở biên, máy trạng thái, lưu đỉnh, đếm giờ), `OpsConfigTest` 6 (reset 0/12/biên, mặc định = `Utils.TIME_HOUR*12`), `OpsHeartbeatTest` 4, `OpsHooksTest` 1 (cờ tắt ⇒ no-op, không file).
- **Jar** v11d vs eea5adec: 8193 entry trùng CRC; **5 class khác**: `BinanceOrderTradingManager`, `DetectEntrySignal2TradeNormal`, `DetectEntrySignal2TradeNormal$1`, `$TickGate`, `monitor/Reporter`; **9 class mới** `com/binance/chuyennd/ops/*` (KillSwitchEngine + 4 lớp con, OpsConfig, OpsHeartbeat, OpsHooks + 1 lớp con). Không resource nào khác.
- **Bytecode mức method** (chuẩn hoá chỉ số constant pool, ldc_w→ldc, offset→thứ tự lệnh; kiểm nhảy/exception table khớp):
  - `$1`, `$TickGate`: 100 % method IDENTICAL (khác CRC chỉ do LineNumberTable dời dòng).
  - `DetectEntrySignal2TradeNormal`: 62 IDENTICAL; `checkMarketLevelChange2Trade` ADDITIVE_OK — chỉ chèn `invokestatic OpsHooks.onTickStart()` và `aload; invokestatic OpsHooks.onMarketData(Map)`.
  - `BinanceOrderTradingManager`: 31 IDENTICAL; ADDITIVE_OK `start` (+`OpsHooks.start()`), `shadowTickC3` (+`onPaperBook`, +`onPaperTick`), `updatePositionInfo` (+`onApiResult("positionRisk", positions!=null && !isEmpty())`); thay thế duy nhất: `lambda$startThreadAutoRestartProgram$1` — `ldc2_w 43200000` ⇒ `OpsConfig.periodicResetMs()` + nhánh `<=0 ⇒ WARN, return` (đây chính là reset 12h).
  - `Reporter`: 5 IDENTICAL; `buildReport` ADDITIVE_OK (+1 `LOG.warn [OPS-RESET] cause=…` trước `Utils.reset`).
- **Legacy-equivalence harness OFFLINE** (`research/parity_v11` của research/vz-e1, build riêng `~/claude_master/v11d/parity_build` trên jar v11d, `HARNESS_OFFLINE=1`, stub Aerospike, strace `connect()` = 4 lần/lượt, 0 tới 242, 0 AF_INET), 2 cửa sổ cũ (w1 720 phút, w2 411 phút), so với output eea5adec `parity_v11w/runs/r1`:

  | lượt | w1 gate 33 / fund 45 | w2 gate 33 / fund 45 |
  |---|---|---|
  | BT, cờ mặc định | 720/720 bit, fund 24 051/24 051 bit, **byte-identical** | 411/411, 9 985/9 985, **byte-identical** |
  | NEW2 (đường prod v1.1), cờ mặc định | **byte-identical** | **byte-identical** |
  | BT + 3 cờ bật (+LIVE_PROFILE=c3_shadow) | **byte-identical** | **byte-identical** |
  | NEW2 + `LIVE_KILLSW_MODE=log LIVE_HEARTBEAT=1 LIVE_PERIODIC_RESET_HOURS=0`, harness GỌI `OpsHooks.onTickStart/onMarketData` mỗi phút như live | **byte-identical**; `[OPS]`, `[KILLSW] BAT`, `[HEARTBEAT] BAT` có; C1 WOULD_TRIGGER (đúng: dữ liệu lịch sử ⇒ lag lớn, miss=0/738); `run/heartbeat` 0 byte | **byte-identical**, như w1 |

  p15 = ONNX(33 feature): feature byte-identical và mọi class/resource ONNX trong jar trùng CRC; file model trên đĩa 242 không đổi ⇒ p15 trùng (không chạy ORT riêng — model không có trên Oracle).
- **Watchdog** (`ops/test/h242_watchdog_test.sh`, process giả + heartbeat giả + daemon.sh giả + stub Telegram 127.0.0.1): **42/42 PASS** — dry-run không hành động; DOWN ⇒ cảnh báo + start + START_OK; HB 6' ⇒ chỉ cảnh báo; HB 11' + đã cảnh báo ⇒ stop + start (pid mới); HB 11' lần đầu ⇒ chỉ cảnh báo; thiếu file HB ⇒ không bao giờ kill; grace; 2 JVM ⇒ chỉ cảnh báo (lần 2), cửa sổ reset ⇒ DOUBLE_TRANSIENT; process ở thư mục khác (shadow Oracle) không bị đếm/đụng; start thất bại ⇒ START_FAIL rồi backoff; prestart rc=1 ⇒ không start; flock; JVM con không giữ fd lock; PAUSE; SIGTERM bị bỏ qua ⇒ TERM rồi KILL đúng PID; không có tg.env ⇒ ALERT_PENDING; token không xuất hiện trong log/state; process thật (`/home/ubuntu/shadow_c3/app`) không bị đụng.

## 2. Giờ restart hợp lệ (+07)
- CẤM: 00:50–01:20, 12:50–13:20, 06:57–07:25, 18:57–19:25, ±3' quanh mỗi giờ (xx:57–xx:03).
- KHÔNG đụng ±10' quanh tự-restart: **10-22 07:45–08:05** (tự-restart ~07:54:4x) và **10-22 19:45–20:05** (~19:55:3x).
- Đề xuất: **10-22 08:10–08:50, 09:10–11:50 hoặc 14:10–17:40**, phút trong khoảng **:10–:45** (phương án A giữ reset 12h: chu kỳ mới = T+12h, trôi ~+32 s/lần ⇒ chọn phút giữa giờ để ≥ 10 ngày không trôi vào khung ±3').
- Restart này = 1 tự-restart (ADDENDUM d (3)) ⇒ ghi sổ C (§7).

## 3. Hai phương án env
- **A (mặc định, làm được ngay):** `LIVE_HEARTBEAT=1`, `LIVE_KILLSW_MODE=log`, JAVA_TOOL_OPTIONS + `-XX:+ExitOnOutOfMemoryError` + gc log theo pid/giờ. Reset 12h GIỮ NGUYÊN.
- **B (chỉ khi MASTER xác nhận RSS phẳng):** A + `LIVE_PERIODIC_RESET_HOURS=0`. Điều kiện: đo RSS PID 27434 ở h≈6 và h≈11 (10-22 ~01:54 và ~06:54) phẳng/giảm so với h1,3 = 2,64 GiB, và MemAvailable host ≥ 2 GiB. Không có xác nhận ⇒ dùng A. Đổi A→B sau này = sửa env + restart = 1 sự kiện vận hành mới (sổ C), không cần jar mới.
- Với B bắt buộc có watchdog (§4) + ExitOnOutOfMemoryError (không còn reset 12h làm "lưới").

## 4. Lệnh (chạy từ Oracle)
```bash
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"
A=/home/chuyennd/java/v_t_m
NJ=/home/ubuntu/claude_master/v11d/jar/binance-java-sdk-1.2.4.jar_v11d_7767a560
WDS=/home/ubuntu/claude_master/v11d/wt/ops/h242_watchdog.sh
TS=$(date +%Y%m%d_%H%M)
# 0) kiểm trước (chỉ đọc): md5 chạy = eea5adec…; 0 dòng LIVE_HEARTBEAT/LIVE_KILLSW_MODE/LIVE_PERIODIC_RESET_HOURS; dòng JAVA_TOOL_OPTIONS hiện tại
md5sum $NJ   # 7767a560baac8e3bfb925c85503d032b
$S "cd $A && md5sum target/binance-java-sdk-1.2.4.jar; cat run/*.pid; pgrep -fa BinanceOrderTradingManager | cut -c1-100; grep -c '^export LIVE_HEARTBEAT\|^export LIVE_KILLSW_MODE\|^export LIVE_PERIODIC_RESET_HOURS' conf/env.sh; grep -n '^export JAVA_TOOL_OPTIONS' conf/env.sh; crontab -l 2>&1 | head -3; date '+%F %T'"
# 1) chép jar mới cạnh jar cũ (KHÔNG ghi đè) + md5
$SCP $NJ root@103.157.218.242:$A/target/binance-java-sdk-1.2.4.jar.v11d_7767a560
$S "cd $A && md5sum target/binance-java-sdk-1.2.4.jar.v11d_7767a560"      # 7767a560…
# 2) backup jar eea5adec + env
$S "cd $A && \cp -f target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_v11c_eea5adec_$TS && \cp -f conf/env.sh conf/env.sh.bak_v11c_$TS && md5sum target/binance-java-sdk-1.2.4.jar.bak_v11c_eea5adec_$TS"
# 3) env — phương án A (B: thêm dòng LIVE_PERIODIC_RESET_HOURS=0, xem dưới)
$S "cd $A && printf '%s\n' '# [v11d $TS] chi van hanh (ADDENDUM d)' 'export LIVE_HEARTBEAT=1' 'export LIVE_KILLSW_MODE=log' >> conf/env.sh"
#    B (CHỈ khi MASTER xác nhận RSS phẳng):
#    $S "cd $A && echo 'export LIVE_PERIODIC_RESET_HOURS=0' >> conf/env.sh"
#    JAVA_TOOL_OPTIONS: thêm ExitOnOutOfMemoryError sau -Xmx3g, gc log theo pid+giờ start (không bị xoay mất)
$S "cd $A && sed -i -E '/^export JAVA_TOOL_OPTIONS=/ { s#-Xmx3g#-Xmx3g -XX:+ExitOnOutOfMemoryError#; s#file=logs/gc\.log#file=logs/gc_%p_%t.log# }' conf/env.sh && grep -n '^export JAVA_TOOL_OPTIONS' conf/env.sh"
#    PHẢI thấy đúng 1 dòng có CẢ '-XX:+ExitOnOutOfMemoryError' VÀ 'file=logs/gc_%p_%t.log'. Thiếu 1 trong 2 (dòng gốc khác mẫu) ⇒ KHÔNG đi tiếp:
#    khôi phục `\cp -f conf/env.sh.bak_v11c_$TS conf/env.sh` và báo MASTER kèm dòng gốc.
$S "cd $A && diff conf/env.sh.bak_v11c_$TS conf/env.sh"   # chỉ: dòng JAVA_TOOL_OPTIONS đổi + 3 dòng thêm (B: 4)
#    kiểm cú pháp JVM (KHÔNG đụng app): java -version với env mới — lỗi -Xlog/-XX ⇒ dừng, khôi phục env
$S "cd $A && bash -c 'set -a; . conf/env.sh; set +a; java -version' 2>&1 | head -4"   # 'Picked up JAVA_TOOL_OPTIONS: …' + version, không 'Error'
#    (lệnh này tạo 1 file logs/gc_<pid>_<giờ>.log nhỏ của JVM thử — vô hại. 'java: command not found' ⇒ thay `java` bằng
#     đường dẫn JVM đang chạy: $S "readlink -f /proc/\$(pgrep -f BinanceOrderTradingManager)/exe")
# 4) KIỂM GIỜ (§2) rồi stop → thay jar → start. CHẶN: thiếu file v11d hoặc md5 sai ⇒ KHÔNG stop
$S "cd $A && [ \"\$(md5sum < target/binance-java-sdk-1.2.4.jar.v11d_7767a560 | cut -c1-32)\" = 7767a560baac8e3bfb925c85503d032b ]" || { echo "THIEU/SAI v11d - DUNG"; exit 1; }
$S "cd $A && bin/daemon.sh stop && \cp -f target/binance-java-sdk-1.2.4.jar.v11d_7767a560 target/binance-java-sdk-1.2.4.jar && md5sum target/binance-java-sdk-1.2.4.jar && bin/daemon.sh start && sleep 5 && pgrep -fa BinanceOrderTradingManager | cut -c1-100; date '+%F %T'"
```
Ghi lại giờ start (`ps -o lstart`) cho sổ C.

### 4b. Watchdog — cài SAU khi §5 PASS (15')
```bash
# script ghim (không dùng bản trong git trực tiếp)
$SCP $WDS root@103.157.218.242:/usr/local/sbin/h242_watchdog.sh
$S "chmod 755 /usr/local/sbin/h242_watchdog.sh && bash -n /usr/local/sbin/h242_watchdog.sh && md5sum /usr/local/sbin/h242_watchdog.sh"
# kênh Telegram: DÙNG LẠI file tg.env của health_242 trên Oracle (tele-token:/tele-chat-id: hoặc TG_TOKEN=/TG_CHAT=) — KHÔNG in nội dung
$S "mkdir -p -m 700 /root/.config/h242_watchdog"
$SCP -p /home/ubuntu/.config/health242/tg.env root@103.157.218.242:/root/.config/h242_watchdog/tg.env
$S "chmod 600 /root/.config/h242_watchdog/tg.env; ls -l /root/.config/h242_watchdog/tg.env"
# chạy khô với app thật: PHẢI là 'OK pid=<PID mới> up=…s hb_age=<60s' (trong 10' đầu: OK_GRACE)
$S "/usr/local/sbin/h242_watchdog.sh --dry-run"
# thử kênh (tin gắn nhãn TEST; APP giả không tồn tại ⇒ TRADING_DOWN + START_FAIL; KHÔNG đụng app thật)
$S "WD_TAG=' TEST' WD_STATE_DIR=/var/lib/h242_watchdog_test WD_APP=/nonexistent_v11d_test WD_PRESTART=/nonexistent WD_START_CMD=true WD_START_WAIT_SEC=2 /usr/local/sbin/h242_watchdog.sh; tail -4 /var/lib/h242_watchdog_test/watchdog.log"
#   PASS: 2 dòng 'SENT http=200 [242-WATCHDOG TEST] …' và owner nhận 2 tin TEST. (Thư mục test để lại vô hại.)
# cron root */2 (crontab root hiện trống)
$S "( crontab -l 2>/dev/null; echo '*/2 * * * * /usr/local/sbin/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1' ) | crontab - && crontab -l | grep -c h242_watchdog"   # 1
# sau 5': có 1 dòng OK trong /var/lib/h242_watchdog/watchdog.log, cron.out rỗng hoặc không lỗi
$S "tail -3 /var/lib/h242_watchdog/watchdog.log; tail -3 /var/lib/h242_watchdog/cron.out 2>/dev/null"
```
- **Restart tay sau này** (deploy/rollback): `$S "touch /var/lib/h242_watchdog/PAUSE"` TRƯỚC khi stop, `rm -f` SAU khi kiểm xong — tránh watchdog start chen (chạy đôi JVM).
- Watchdog tự restart (DOWN / HB_STALE_KILL) có thể rơi vào khung cấm — app chết thì bật lại ngay vẫn tốt hơn (44 vị thế LEGACY thật cần quản lý). Mỗi lần như vậy = 1 sự kiện vận hành ⇒ ghi sổ C (giờ lấy từ `watchdog.log`).

## 5. Kiểm 15 phút (chỉ đọc qua pipe — KHÔNG ghi file tạm lên 242)
```bash
$S "bash -s" <<'EOF'
cd /home/chuyennd/java/v_t_m
L=logs/full.log
N=$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $L | tail -1 | cut -d: -f1)
echo "== jar (PHAI 7767a560)"; md5sum target/binance-java-sdk-1.2.4.jar; P=$(pgrep -f BinanceOrderTradingManager); ps -o pid,lstart,rss -p $P
echo "== env process (chi cac key nay)"; tr '\0' '\n' < /proc/$P/environ | grep -E '^(LIVE_HEARTBEAT|LIVE_KILLSW_MODE|LIVE_PERIODIC_RESET_HOURS|LIVE_PROFILE|SHADOW_NO_PUSH|LIVE_TS_MKT_EXT|JAVA_TOOL_OPTIONS)='
echo "== ops"; tail -n +$N $L | grep -a '\[OPS\] v11d\|\[KILLSW\] BAT\|\[HEARTBEAT\] BAT\|\[OPS-RESET\]\|TU CHOI\|Start thread ThreadAutoRestartProgram' | cut -c1-260
echo "== heartbeat"; stat -c '%s bytes  %y' run/heartbeat; echo "tuoi=$(( $(date +%s) - $(stat -c %Y run/heartbeat) ))s"
echo "== killsw"; tail -n +$N $L | grep -a -c 'WOULD_TRIGGER'; tail -n +$N $L | grep -a 'WOULD_TRIGGER\|\[KILLSW\] CLEAR\|HOURLY' | tail -6 | cut -c1-260
echo "== gc log"; ls -la logs/gc_* 2>&1 | tail -3
echo "== v11c giu nguyen"; tail -n +$N $L | grep -a 'LIVE_PROFILE=c3_shadow\] BAT' | tail -1 | cut -c1-160
tail -n +$N $L | grep -a '\[LEGACY\] managed' | tail -1 | cut -c1-60
tail -n +$N $L | grep -a '\[TS-EXT\] BAT\|\[TS-EXT\] flag day' | tail -2 | cut -c1-200
tail -n +$N $L | grep -a '\[SHADOW\] so vi the giay khoi tao' | tail -1 | cut -c1-220
echo "== loi"; tail -n +$N $L | grep -a -c ' ERROR '; tail -n +$N $L | grep -a 'Exception\|\[OPS\] loi hook' | tail -5 | cut -c1-200
echo "== tick"; tail -n +$N $L | grep -a 'PASS-TIMING\] selector tick total' | tail -4 | cut -c1-140
EOF
```
PASS khi đủ:
1. md5 = 7767a560…; env process có `LIVE_HEARTBEAT=1`, `LIVE_KILLSW_MODE=log`, JAVA_TOOL_OPTIONS có `-XX:+ExitOnOutOfMemoryError` và `gc_%p_%t.log`; (B: `LIVE_PERIODIC_RESET_HOURS=0`).
2. `[OPS] v11d LIVE_PERIODIC_RESET_HOURS=12h … LIVE_HEARTBEAT=1 … LIVE_KILLSW_MODE=log => hieu luc=log profile=c3_shadow`; `[KILLSW] BAT mode=log CHI LOG …`; `[HEARTBEAT] BAT file=/home/chuyennd/java/v_t_m/run/heartbeat`;
   KHÔNG có `TU CHOI`; `Start thread ThreadAutoRestartProgram` có (B: thêm `[OPS-RESET] LIVE_PERIODIC_RESET_HOURS=0 => TAT reset dinh ky`).
3. `run/heartbeat` 0 byte, tuổi < 90 s.
4. `logs/gc_<pid>_<ngày>.log` mới (đúng PID); file `logs/gc.log*` cũ để nguyên.
5. Như v11c: `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true`; `[LEGACY] managed 44`; `[TS-EXT] BAT … days_loaded=30/31` + `flag … src=file` (không đọc aero); sổ giấy open/realized như trước restart.
6. 0 Exception mới, không có `[OPS] loi hook`; tick (sau tick đầu ~27 s) ≤ ~1,5 s như v11c.
7. `WOULD_TRIGGER`: ghi số lượng và mã vào sổ C (không phải lỗi — chế độ log). Nếu có `code=C3` hoặc `code=C6` ngay đầu ⇒ báo MASTER (C3 = REST vị thế lỗi liên tục; C6 = đỉnh/equity bất thường).

## 6. Rollback (về v11c eea5adec + env cũ)
```bash
$S "touch /var/lib/h242_watchdog/PAUSE 2>/dev/null; crontab -l 2>/dev/null | grep -v h242_watchdog | crontab -; crontab -l | grep -c h242_watchdog"   # 0
$S "cd $A && bin/daemon.sh stop && \cp -f target/binance-java-sdk-1.2.4.jar.bak_v11c_eea5adec_$TS target/binance-java-sdk-1.2.4.jar && \cp -f conf/env.sh.bak_v11c_$TS conf/env.sh && md5sum target/binance-java-sdk-1.2.4.jar && grep -c '^export LIVE_HEARTBEAT\|^export LIVE_KILLSW_MODE' conf/env.sh; bin/daemon.sh start && sleep 5 && pgrep -fa BinanceOrderTradingManager | cut -c1-100; date '+%F %T'"
```
- md5 phải = eea5adec…, grep = 0. `run/heartbeat`, `run/killsw_peak`, `logs/gc_*` để lại vô hại (v11c không đọc). Không xoá backup.
- Rollback cũng là 1 sự kiện vận hành (sổ C).

## 7. Sổ C (ADDENDUM d) — điền khi deploy
| mục | giá trị |
|---|---|
| giờ stop / start (`ps lstart`) | … / … (+07) |
| PID cũ → mới | 27434 (hoặc PID sau tự-restart 10-22 07:54) → … |
| md5 cũ → mới | `eea5adecaff93d3fc350e4d13b3ecb2a` → `7767a560baac8e3bfb925c85503d032b` |
| diff env | `+export LIVE_HEARTBEAT=1`, `+export LIVE_KILLSW_MODE=log`, (B: `+export LIVE_PERIODIC_RESET_HOURS=0`); JAVA_TOOL_OPTIONS: `+ -XX:+ExitOnOutOfMemoryError`, `file=logs/gc.log` → `file=logs/gc_%p_%t.log` |
| watchdog | cron `*/2` cài lúc …, md5 script … |
| lý do | ADDENDUM d: chỉ vận hành — heartbeat + watchdog (không có gì tự bật lại khi JVM chết), ExitOnOutOfMemoryError, gc log không mất khi xoay, kill-switch chế độ log để đo trước khi bàn act; (B) tắt reset 12h sau khi RSS phẳng |
| bằng chứng (1) | §1: 5 class khác (+9 class ops mới), method-level chỉ chèn hook (trừ lambda reset 12h); harness offline 2 cửa sổ × {BT, NEW2} × {mặc định, cờ bật + hook} byte-identical với eea5adec |
| (3) | restart này = 1 tự-restart; cửa sổ promotion KHÔNG reset |

## 8. Dung lượng / rủi ro vận hành
- `run/heartbeat`: 0 byte, chỉ mtime. `run/killsw_peak`: 1 dòng, ghi khi có đỉnh mới (≤ 1 lần/phút). Reset/đổi `PAPER_EQUITY`/sổ giấy ⇒ đổi tên file này (đỉnh cũ sẽ làm C6 sai).
- Log `[KILLSW]`: HOURLY 24 dòng/ngày; WOULD_TRIGGER ≤ 1 dòng/phút/mã ⇒ trần ~8 640 dòng/ngày (~1,7 MB) nếu 6 mã đạt liên tục — logback xoay như cũ.
- gc log: `-Xlog:gc` hiện ghi ~2 300 sự kiện/12h (gc.log.0 PID 7535) ≈ 0,3–0,4 MB/12h. Với `gc_%p_%t.log`: A ⇒ 2 file/ngày ≈ 0,7 MB/ngày ≈ 21 MB/tháng; B ⇒ 1 file lớn dần ~0,7 MB/ngày, tự xoay theo filesize (mặc định 20 MB × filecount hiện có). Dọn tay hằng tháng: `find logs -name 'gc_*.log*' -mtime +30 -delete`.
- watchdog.log: chỉ ghi sự kiện + 1 dòng OK/giờ (~2 KB/ngày), tự xoay ở 5 MB.
- Chạy đôi JVM: watchdog chỉ start khi đếm 0 process (main class + cwd) NGAY trước start, có prestart chặn khi đang chạy, flock, backoff 10'; không bao giờ kill khi thấy 2 JVM. Owner restart tay ⇒ dùng PAUSE.
- Watchdog restart sai lúc: chỉ khi DOWN, hoặc heartbeat > 10' VÀ đã cảnh báo ở lần trước (≥ 2' sau) — tick thật 1/phút, warm-up ~28 s, grace 10' sau start. Thiếu file heartbeat (quên `LIVE_HEARTBEAT=1`) ⇒ chỉ cảnh báo.
