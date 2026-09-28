# AUDIT — DEPLOY NHỊP KHỚP BACKTEST + INSTRUMENT LÊN 242 (TEST) — 2026-09-28

Phạm vi được duyệt (owner 28/09 08:41): *"lại vẫn ko chạy. ko chạy thì audit kiểu gì. **chạy 242 đi** coin như test **vì bản chất chưa golive mà**"*
⇒ **ĐƯỢC PHÉP deploy lên 242** (host live, GIỮ 52 ví thế LEGACY), coi là **TEST** (chưa golive). **`git push` được phép** (rule mở 28/09).

Mục tiêu: đưa 242 chạy **cùng bản jar (byte-identical)** với Shadow Oracle để (a) verify live khớp backtest, (b) audit nhịp tách SELECTOR 15' + MARKET-LEVEL 1', (c) instrument feature dump.

Ràng buộc đã giữ: **KHÔNG** đổi gate · **KHÔNG** chạm ONNX/`NUM_FEATURES`/`extractFeatures45` · **KHÔNG** đọc/in key/token · **KHÔNG** `kill -9` thủ công · **KHÔNG** xoá dữ liệu · **KHÔNG** sửa `config.properties` · **KHÔNG** đổi `SHADOW_NO_PUSH`/`LIVE_PROFILE` · **KHÔNG** chạm cơ chế 52 ví thế LEGACY.

> **KẾT LUẬN: DEPLOY THÀNH CÔNG.** Jar 2 host **byte-identical** (`78387f30…`), process mới sống, `[CADENCE-SPLIT]` xuất hiện, `[GATE]` đúng nhịp 15', nhịp market-level 1 phút, `feat_dump` ghi, **0 ERROR/Exception mới**, 52 LEGACY nguyên, `SHADOW_NO_PUSH=true`/`LIVE_PROFILE=c3_shadow` không đổi. **Cảnh báo: áp lực RAM** do launcher chuẩn `-Xms5g` (xem §5).

---

## 0. BUỘC 0 — ĐỌC TRƯỚC (chỉ đọc, 242) — CƠ CHẾ RESTART CHUẨN

Host 242 = `103.157.218.242:2222` (user `root`, key `~/.ssh/id_rsa_chuyennd`). App dir: **`/home/chuyennd/java/v_t_m`**. **Không có systemd unit** cho app (khác shadow_c3 Oracle). PID chạy trước deploy: **13558** (start 06:01, tự restart qua `ThreadAutoRestartProgram`).

Đọc `bin/daemon.sh` + `env.sh` + `run/*.pid` ⇒ **lệnh restart CHUẨN**:
- pidfile: `run/com.binance.chuyennd.trading.BinanceOrderTradingManager.pid` (`APP_PID_DIR=./run`).
- `bin/daemon.sh {start|stop|restart}`: `stop` = gửi **SIGTERM** (graceful, chờ tối đa 60s) → `start` = `nohup bin/start.sh` (log `logs/nohup.out`).
- `bin/start.sh`: `JAVA_OPTS="-server -Xms5g -Xmx5g"`, `-cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager`.
- Đối chiếu lịch sử lệnh operator (`/root/.bash_history`) + script operator (`/root/deploy_242_l7/deploy.sh`): dùng đúng **`cd /home/chuyennd/java/v_t_m && bin/daemon.sh restart`**.
- Ghi chú: app còn có **tự-restart mỗi 4h** (`Utils.reset` → raw `java -cp …`, không `-Xms5g`); lần tới ~12:46.

Trạng thái trước deploy (đã ghi):

| Đối tượng | sha256 (trước) |
|---|---|
| `target/binance-java-sdk-1.2.4.jar` (đang chạy, `069adc85…`) | `069adc85e8ae051d7602b7e9c9b56ae3d2200b22d81146ec0d2be13209a0f117` |
| `conf/env.sh` | `ba24e82d94f92b45df65a473327b7d1d4bf26cb51ac6eafa8716505156aed62b` |
| `config.properties` (**KHÔNG sửa**) | `2aa62a4d40fa295de05f01d231753b00d62e6b0eb3cfd3294a9f44dea7f7ad55` |
| `df -h /` | 92G · 77G used · **15G avail · 84%** |
| `free -m` | total 7821 · used 4724 · avail 2721 (swap free 7529) |
| `SHADOW_NO_PUSH` / `LIVE_PROFILE` | `true` / `c3_shadow` |

## 1. BUỘC 1 — JAR CHUẨN TỪ SHADOW ORACLE

- Shadow jar: `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar` sha256 **`78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71`** (= "78387f30…" như kỳ vọng).
- Copy **nguyên file** (scp) sang 242 staging: `target/binance-java-sdk-1.2.4.jar.stage_20260928`.
- sha256 tại 242 sau copy: **`78387f30…`** ⇒ **2 host byte-identical**.

## 2. BUỘC 2 — DEPLOY (backup trước)

Backup trên 242 (bản sao `cp -a`):

| Backup | sha256 |
|---|---|
| `target/binance-java-sdk-1.2.4.jar.bak_20260928` | `069adc85e8ae051d7602b7e9c9b56ae3d2200b22d81146ec0d2be13209a0f117` |
| `conf/env.sh.bak_20260928` | `ba24e82d94f92b45df65a473327b7d1d4bf26cb51ac6eafa8716505156aed62b` |
| `logs/nohup.out.bak_20260928` | (giữ lại stdout cũ) |

Thay jar: `cp -f target/…stage_20260928 target/binance-java-sdk-1.2.4.jar` ⇒ sha256 mới **`78387f30…`**.
`config.properties` giữ nguyên (`cfg0 = cfg1 = 2aa62a4d…`).

Thêm vào **`conf/env.sh` của 242** (giữ nguyên `SHADOW_NO_PUSH=true` + `LIVE_PROFILE=c3_shadow`), 3 dòng:

```bash
export MARKET_SCAN_MIN=1
export MARKET_SCAN_PRIORITY=1
export LIVE_FEAT_DUMP=3000
```

`conf/env.sh` sau sửa: `f91ffefe17e982a0ad5b32229b16c3333961cb2997a1f94fbc567a9c4f4c1e6e` (so với `ba24e82d…` trước).
Đoạn `env.sh` liên quan (đã xác nhận sau deploy):

```
68:export LIVE_PROFILE=c3_shadow
69:export SHADOW_NO_PUSH=true
91:export MARKET_SCAN_MIN=1
92:export MARKET_SCAN_PRIORITY=1
93:export LIVE_FEAT_DUMP=3000
```

**Restart** (đúng cơ chế §0): `cd /home/chuyennd/java/v_t_m && bin/daemon.sh restart`
⇒ `stop` graceful 13558 (thoát <1s, **không** `kill -9`), `start` PID mới **5865** (cmd: `java -server -Xms5g -Xmx5g … -cp target/binance-java-sdk-1.2.4.jar …`).

## 3. BUỘC 3 — XÁC MINH (cửa sổ ~33 phút, mốc `OFF0`=85044360 byte)

| Hạng mục | Kết quả |
|---|---|
| Process sau restart | **PID 5865** sống, uptime 32:47 (lúc kiểm) — OK |
| `sha256` jar đang chạy | `78387f30…` = jar shadow ⇒ **2 host GIỐNG** |
| ERROR mới / Exception mới | **0 / 0** |
| `[CADENCE-SPLIT]` | **CÓ** (2 dòng: `MARKET_SCAN_MIN=1 => MARKET-LEVEL(BIG_DOWN/DCA) quet 1 PHUT, SELECTOR luon 15'` + `[CADENCE-SPLIT-V2] MARKET_SCAN_PRIORITY=1 => BAT: SEL luon xep hang (<=1 cho), MKT chi nop khi RAN`) |
| `[GATE]` đúng 15' | **CÓ, 2 lần** trong 33': tại chu kỳ **:00** (log `09:01`) và **:15** (log `09:16`); **không** có ở phút khác (khớp mẫu trước deploy `:00/:16/:31/:45` — lệch +1' do thời điểm log) |
| `Start check level change` | **32 lượt / 32 phút ⇒ ~60 lượt/giờ** (trước: 4 lượt/giờ) — market-level quét **1 phút** đúng thiết kế |
| Đọng hàng đợi | **Không** (không có marker backlog/queue-full/drop) |
| `would-BUY` phút lẻ | **0** (chưa có tín hiệu BIG_DOWN/DCA nào xuất hiện để entry trong cửa sổ) |
| `Create order market` (lệnh thật) | **0** (paper) |
| instrument `feat_dump` | `feat_dump/feat_dump_20260928_084506.csv.gz` — **32 dòng · 36 cột · 6382 byte** (đang ghi tăng dần) |
| `df -h /` sau deploy | 15G avail · **84%** (không đổi, không chạm HARD STOP) |
| 52 ví thế LEGACY | `run/legacy_symbols.csv` = **52 dòng**; log vẫn in `[LEGACY] managed …` (giá trị động, hiện 50). Không có sự kiện SELL/SL legacy mới trong cửa sổ (`=0`) |
| ONNX md5 | **không đổi** — `g015x26_20251001=a39dbe9a…`, `g015x26_20251231=e65e683b…`, `s1a2x1_20251001=afaa2828…`, `s1a2x1_20251231=511add62…` |
| `SHADOW_NO_PUSH` / `LIVE_PROFILE` | **`true` / `c3_shadow` — không đổi** |

## 4. ROLLBACK (nguyên văn — chỉ chạy khi cần)

```bash
D=/home/chuyennd/java/v_t_m
cp -f $D/target/binance-java-sdk-1.2.4.jar.bak_20260928 $D/target/binance-java-sdk-1.2.4.jar
cp -f $D/conf/env.sh.bak_20260928 $D/conf/env.sh
cd $D && bin/daemon.sh restart
# verify: sha256 target/binance-java-sdk-1.2.4.jar = 069adc85e8ae051d7602b7e9c9b56ae3d2200b22d81146ec0d2be13209a0f117
#         grep -c CADENCE-SPLIT logs/full.log (sau restart) = 0
```

## 5. CẢNH BÁO / THEO DÕI

- **Áp lực RAM:** cơ chế chuẩn `bin/start.sh` chạy `-Xms5g -Xmx5g`. Sau restart, RSS app ≈ **4.7 GB**; `free -m` avail tụt còn ~90–100 MB, swap dùng tăng (597 → 846 MB). `dmesg` **từng** có OOM-kill java (rss ~5.5 GB) với cấu hình này. Box 8 GB còn chạy `BinanceDataIngestor` (collectData, ~2.2 GB). **Chưa OOM trong cửa sổ 33'**, nhưng cần theo dõi.
- **Giảm áp lực tự nhiên:** app tự-restart mỗi 4h qua `Utils.reset` bằng **raw java (heap mặc định)**, lần tới **~12:46** ⇒ RSS/`-Xms5g` sẽ được nhả.
- Nhịp `Start check level change` **~60/giờ** (1/phút), cao hơn con số kỳ vọng "16–20/giờ" nêu trong đề bài; đây là hệ quả trực tiếp & đúng của `MARKET_SCAN_MIN=1`. Ghi nhận để đối chiếu kỳ vọng.
- Để verify "live khớp backtest" cần thêm dữ liệu `feat_dump` nhiều giờ + so md5/parity; **ngoài phạm vi** lần deploy này.
