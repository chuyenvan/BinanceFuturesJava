# V11C_DEPLOY_1021 — kiểm sau restart owner 10-21 05:55 (chỉ đọc 242 qua ssh+pipe)

Kết luận lần 1 (05:55): **gói v1.1 (v11c) CHƯA được deploy.** — ĐÃ deploy ở lần 2 07:53:59, xem cuối file. Owner đã restart, nhưng jar đang chạy vẫn là **v11b `d7824f6d`**. Lý do: file `target/*v11c*`
không có trên 242, tức bước 1 của runbook (scp jar) chưa chạy. Key `LIVE_TS_MKT_EXT=1` đã có trong env, nhưng v11b bỏ qua key này
⇒ hành vi hiện tại = v11b, an toàn, không cần rollback. **Cửa sổ promotion chính thức CHƯA bắt đầu.**

## 1. Xác minh (05:56–05:58 +07)
| mục | kết quả |
|---|---|
| jar chạy (`target/binance-java-sdk-1.2.4.jar`, fd của PID mở đúng file này) | md5 **d7824f6d…** (mtime 10-20 20:32:55) — **KHÔNG phải eea5adec** |
| file v11c trên 242 | **không có** (`target/*v11c*`) |
| backup | `target/…jar.bak_v11b_d7824f6d_20261021` md5 d7824f6d ✔; `conf/env.sh.bak_v11b_20261021` ✔ (05:55:09) |
| diff env | chỉ `+export LIVE_TS_MKT_EXT=1` ✔ |
| PID / start | **26221**, `ps lstart` **2026-10-21 05:55:29**; log `MainClass` 05:55:31.018; `ThreadAutoRestartProgram` 05:55:41.626 |
| env process | `LIVE_TS_MKT_EXT=1`, `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, 6 key v11b; `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -Xlog:gc:file=logs/gc.log…` ✔ (RSS 3,19G lúc 1' sau start) |
| profile | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true (hardcode)` ✔ |
| LEGACY | `[LEGACY] managed 44` trước (05:55:10) và sau (05:57:10) ✔ |
| sổ giấy | sau start: open=4 realized=88,0877. Trước đó, lúc deploy v11b, là open=5 / 112,18. Chênh lệch giải thích được: 10-20 22:21 time-stop `SUSDT` pnl −24,09 (ledger + log) ✔ |
| gate buffer | nạp 662 040 record, armed ✔ |
| v11b | `[FEAT-PIPE] LIVE_FEAT_INPUT=snapshot … md_died=[BTCDOMUSDT, USDCUSDT]`, seed 2000' 738 symbol ✔; `[S1-DUMP]` mở file ✔; S1 warm-up đọc kline_1m_opt 242 (như v11b) |
| PASS-TIMING | tick đầu 28,8 s (warm-up, như các lần trước 22–28 s), tick kế 1,29 s ✔ |
| lỗi | 0 ERROR, 0 Exception sau start ✔ |
| `[TS-EXT]` | 0 dòng (đúng với jar v11b) |

**Giờ restart:** 05:55:29 hợp lệ (ngoài mọi khung cấm, nhưng chỉ cách khung xx:57 có 1,5'). Tự-restart 12h:
- lần 1 ~**10-21 17:56**: hợp lệ;
- lần 2 ~**10-22 05:57**: **rơi vào khung ±3'**, và các lần sau trôi sâu hơn (05:58, 17:59…).

Deploy v11c lại ở giờ đề xuất sẽ đặt lại chu kỳ này.

## 2. Checklist TS-EXT
**Không áp dụng được** vì jar v11c chưa chạy: không có `[TS-EXT] BAT`, không có dòng `day`, không có `run/ts_ext_daily.csv`.

Runbook đã sửa (`docs/runbooks/DEPLOY_V11_TS_MKT_EXT_242.md`):
- thêm mục trạng thái: chỉ cần chạy bước 1 rồi bước 4;
- thêm chốt chặn: không stop app nếu file v11c thiếu hoặc md5 sai;
- §2 lọc log theo dòng `MainClass` cuối, vì log 242 có dạng `21/10/2026 05:55:31`, không phải `2026-10-…` như lệnh cũ giả định (lệnh cũ sai).

## 3. Đối chiếu cờ — Vision (giá trị kỳ vọng cho log live khi v11c chạy)
Nguồn: Kaggle monthly cho 2026-08/09, Vision UM 1m **daily** (data.binance.vision, file tĩnh) cho 10-01..10-19. Tải 16 611 file ×200, 71 ×404
(symbol không có trong tháng). Tính bằng code live (`AltEwIndex`, jar eea5adec).
- Cờ ngày 2026-09-20 → 10-20: **0 ngày ON**. dd(EOD 10-19) = −0,1648 (cờ ngày 10-20); đỉnh 30 ngày là EOD 2026-09-19; dd đang giảm dần (10-13 −0,092 → 10-19 −0,172).
  Universe kiểu live (bỏ symbol không có ở 242) cho |Δdd| ≤ 0,0025, cờ trùng.
- **Cờ 2026-10-21 = "chưa có"**: file Vision 10-20 chưa phát hành (404 lúc 05:58 +07).
- **Store 242 vs Vision cùng ngày**, dùng record kline_1m_opt 242 đã cache từ trước trên Oracle (không đọc 242 mới):

  | ngày | S_j 242 | S_j Vision (float32, universe live) | Δ |
  |---|---|---|---|
  | 10-14 | −0,038786676 | −0,038786676 | 0 |
  | 10-15 | +0,001176837 | +0,001176837 | 1e-16 |
  | 10-16 | −0,014789719 | −0,014789719 | 0 |

  ⇒ giá 242 = Vision float32 **bit-exact** trên 3 ngày. Chênh lệch chỉ đến từ universe: thêm 140 symbol có trong Vision 10-2026 mà 242 không có,
  phần lớn không có volume; với universe Vision đầy đủ, |ΔS| 1,6e-4…6,1e-4 mỗi ngày.
- 30 dòng `[TS-EXT] day` của live: chưa có (v11c chưa chạy). Bảng trên là giá trị để so khi có.

## 5. Đề xuất parity feature định kỳ KHÔNG đọc Aerospike 242 (chưa chạy)
1. **Dữ liệu:** dựng cache phút (`TreeMap<Long, Map<String, KlineObjectSimple>>`, đúng format `cache_*.ser.gz` mà `V11FeatHarness.load` đọc)
   từ Vision UM 1m daily (phát hành D+1), ép float32, universe = danh sách symbol của live lấy qua pipe từ `s1_dump`/`feat_dump` của 242
   (738). Bằng chứng §3: giá và tập phút có qv>0 khớp bit-exact với store 242 trên 3 ngày. Sai khác còn lại:
   - (a) `totalUsdt` chưa kiểm từng giá trị (EW chỉ dùng điều kiện qv>0);
   - (b) symbol mới niêm yết sau ngày lấy danh sách;
   - (c) phút collector ghi lại sau quyết định (PARITY_1020: 2/88 phút) — Vision là dữ liệu cuối, không tái lập được "unsettled".
2. **Chặn cứng mọi đọc Aerospike trong harness:**
   - chạy với `AEROSPIKE_READ_CLUSTER=226` giả;
   - đặt trước jar trên classpath một stub `DataManagerAerospikeFloatSim` / `AerospikeClient` ném lỗi ngay khi được tạo client (fail-closed). Lần chạy đầu sẽ liệt kê đúng các chỗ đọc còn lại.
3. **Thay 3 nguồn đang đọc 242 bằng file cục bộ:**
   - `SimpleSymbolMapper`: snapshot mapper từ log/`sel_dump` hoặc map cố định theo thứ tự symbol;
   - `FundingFeeManager.getAllFundingMap`: lịch sử funding từ Vision `fundingRate` monthly + daily;
   - OI #41–45 (`oi_feat_*` 242): tính lại từ Vision `metrics` 5m daily, hoặc bỏ khỏi phạm vi parity như PARITY_1020.
   Cần sửa harness: inject 3 provider này qua flag (ví dụ `HARNESS_OFFLINE=1`).
4. **So sánh:** đọc `feat_dump`/`sel_dump`/`s1_dump` của 242 qua pipe (`ssh … zcat …`, không ghi file lên 242), so feature 33 cột/p15/rank
   theo thước của PARITY_1020. Lịch chạy: mỗi ngày D+1 sau khi Vision phát hành.

## Ghi chú
Mục 1–3 không có lệnh nào ghi file lên 242. Không chạy harness hay Java nào trỏ vào 242; không đọc Aerospike 242.

---

## DEPLOY LẦN 2 — 10-21 07:53:59: v11c ĐÃ CHẠY (kiểm 07:56–08:01, chỉ đọc)

### A. Xác minh
| mục | kết quả |
|---|---|
| PID / start | **7535**, `ps lstart` **2026-10-21 07:53:59**; log `MainClass` 07:54:01.267; `ThreadAutoRestartProgram` 07:54:12.532 |
| jar process mở (`/proc/7535/fd` → `target/binance-java-sdk-1.2.4.jar`) | md5 **eea5adecaff93d3fc350e4d13b3ecb2a** ✔ |
| env | `export LIVE_TS_MKT_EXT=1` có đúng 1 dòng trong `conf/env.sh`. Env của process có `LIVE_TS_MKT_EXT=1` và đủ 6 key v11b ✔ |
| heap/gc | `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -Xlog:gc:file=logs/gc.log…` ✔; gc.log mới bắt đầu lúc 07:54:00 |
| profile | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true` ✔ |
| LEGACY | `[LEGACY] managed 44` trước (07:53:10) và sau (3/3 dòng) ✔ |
| sổ giấy | open=4, realized 88,0877 — không đổi so với 05:55 ✔ |
| v11b | `[FEAT-PIPE] snapshot … md_died=[BTCDOMUSDT, USDCUSDT]`, seed 2000' 738 symbol; S1-DUMP; `q_t9` ✔ |
| lỗi | 1 ERROR lúc 07:54:12.843: `[FEAT-PIPE] khong co feature snapshot phut nay`, xảy ra ở tick đầu, **trước** khi TS-EXT khởi động (07:54:13). Toàn file full.log chỉ có 1 lần này, không lặp lại. Đây là race lúc warm-up, không thuộc TS-EXT. 0 Exception khác |

**Giờ start 07:53:59: hợp lệ.**

**Tự-restart.** Cơ chế: `sleep` 12h, sau đó chờ tới giây 30–45 của phút. Lịch sử log cho thấy mỗi chu kỳ trôi +8…+52 s, trung bình ~+32 s. Dự kiến:

| chu kỳ | thời điểm |
|---|---|
| 1 | 10-21 19:54:3x |
| 2 | 10-22 07:54:4x |
| 3 | 10-22 19:55:3x |
| 4 | 10-23 07:55:4x |
| 5 | 10-23 19:56:3x |
| 6 | 10-24 07:56:4x |
| 7 | **10-24 ~19:57:3x ⇒ rơi vào khung ±3' đầu giờ** |

Như vậy sau khoảng 7 chu kỳ (~3,5 ngày) sẽ chạm khung cấm. Các khung 00:50–01:20 / 12:50–13:20 / 06:57–07:25 / 18:57–19:25 không bị chạm trong tuần tới.

### B. Checklist TS-EXT
- `[TS-EXT] BAT LIVE_TS_MKT_EXT=1 profile=c3_shadow baseH=168 extH=336 thr=-0.3 minN=1296 file=/home/chuyennd/java/v_t_m/run/ts_ext_daily.csv days_loaded=0` ✔ (07:54:13).
- **Seed:** 30 dòng `[TS-EXT] day 2026-09-21 … 2026-10-20 src=aero`, chạy 07:54:19 → 07:57:09 (~5,8 s/ngày, tổng **2'50"**). n_min = 1440, riêng 10-01 = 1439 và **10-10 = 1436** (store 242 thiếu 4 phút so với Vision); mọi ngày ≥ 1296 ✔.
  `run/ts_ext_daily.csv` = **31 dòng** ✔.
- **Cờ:** `[TS-EXT] flag day=2026-10-21 flag=OFF dd=-0.137179 altEwIdx=0.862821 P=-0.055820 max30=0.091729 max30Day=2026-09-27 minN=1436 src=aero:30d final=true` (07:57:09).
  Final pass là do start lúc 00:54 UTC, sau hạn 00:20 UTC — đúng spec. Trong 2'50" seed cờ ở trạng thái PENDING, nhưng không có cụm nào nằm trong cửa sổ hoãn (`deferring=0`).
- **Đối chiếu từng ngày với Vision** (`live242/cmp_days.csv`):
  - 10-06…10-19, trừ 10-10: S_j live = Vision float32 cùng universe live, **bit-exact** (13 ngày, |Δ| ≤ 2e-16).
  - 10-10: Δ 4,6e-4, do thiếu 4 phút.
  - 09-21…10-05: |Δ| ≤ 1,5e-3 so với universe live-10-16 (universe tháng 9 của 242 khác) và ≤ 2,1e-3 so với Vision full.
  - dd cho cờ 10-21: live **−0,13718**; tính bằng Vision + S_live(10-20) cho −0,13838 (universe live) / −0,13969 (full) ⇒ |Δdd| ≤ 0,0025; cả hai đều OFF ✔.
  - Lưu ý: kỳ vọng "−0,16…−0,18" mà tôi đưa trước đó là dd(EOD 10-19), tức cờ của ngày 10-20. Ngày 10-20 S = +0,0297, nên dd(EOD 10-20) cải thiện lên −0,137.
  - Vision 10-20 chưa phát hành (404 lúc 08:00), nên cờ 10-21 offline = "chưa có" (bản trên đã dùng S_live cho riêng ngày 10-20).
- **PASS-TIMING:** tick đầu 27,1 s (warm-up, như mọi lần start). Trong lúc seed: 1,05 / 1,34 / 0,69 s ⇒ seed không làm chậm tick ✔.
- **Cụm giấy:** 4 cụm mở cùng neo 1792031340000 (10-15 02:29 UTC) sẽ chạm 168h lúc **10-22 09:29 +07**. Cờ 10-22 được tính lúc ~07:03 +07 cùng ngày; nếu OFF thì 4 cụm này bị cắt đúng như v11b.

### C. Sổ
Đã ghi sổ C+ và ADDENDUM c mục D: **cửa sổ promotion chính thức gói v1.1 bắt đầu 2026-10-21 07:53:59 (+07)**.

### D. Reset định kỳ 12h — chỉ đo, không đổi gì
**1. Code**
- `BinanceOrderTradingManager.java:103-125`: thread `ThreadAutoRestartProgram` chạy `while(true) { Thread.sleep(Utils.TIME_HOUR * 12) (:112); Utils.reset("Reset by Schedule") (:117) }`. Chu kỳ 12h hard-code, **không có env/cờ nào tắt được** — muốn bỏ phải sửa code.
- `Utils.java:543-586` (`reset`):
  1. chờ tới giây 30–45;
  2. log `Restart:`;
  3. tạo JVM mới bằng `ProcessBuilder(java.home/bin/java -cp <classpath> <sun.java.command>)`, chép toàn bộ env (nên `JAVA_TOOL_OPTIONS` — heap 3G và gc.log — vẫn giữ; còn `-server` và `-D` trên dòng lệnh thì mất, nhưng `JAVA_TOOL_OPTIONS` đã có lại `-D`), `inheritIO`;
  4. `System.exit(0)` ⇒ chạy shutdown hook (flush buffer gate `GateRatioPersistFlush`).

  Hàm này không flush gì khác, không đóng vị thế, không có reconnect riêng. Sổ giấy, LEGACY và cache TS-EXT đều được ghi đĩa ngay mỗi khi thay đổi, nên restart không mất state. JVM mới ghi lại pidfile (`Utils.java:595`).
- Còn 1 đường reset khác: `Reporter.java:28-33` reset khi Redis `LAST_TIME_CHECK_MARKET` cũ hơn 15', chạy ở nhịp report 30'. Số lần xảy ra trong log 10-18 → nay: **0**.
- `Utils.printMemoryUsage` (`Utils.java:654`) gọi `System.gc()` ở mỗi report 30', nên cứ 30' có một **Full GC 0,6–1,37 s stop-the-world** (lúc xx:00:34 / xx:30:34).

**2. Dữ liệu.** gc.log của 5 process gần nhất (các process trước 10-19 14:52 đã bị rotation `filecount=5` xoá). Heap sau Full GC (System.gc) — thước đo trực tiếp của live set:

| process | h≈1 | h≈6 | h≈11 | n Full | pause max |
|---|---|---|---|---|---|
| 10-19 14:52 → 02:53 | 659 M | 583 M | 572 M | 22 | 1,37 s |
| 10-20 02:53 → 14:53 | 650 M | 586 M | 571 M | 23 | 1,24 s |
| 10-20 14:53 → 20:32 (5,6h) | 624 M | 585 M | — | 12 | 1,15 s |
| 10-20 20:33 → 05:55 (9,4h) | 567 M | 581 M | 573 M (h 9) | 16 | 1,35 s |
| 10-21 05:55 → 07:53 | 616 M | — | — | 4 | 1,30 s |

- Log `RAM SAU KHI [Total ram used]` (134 điểm, 10-18 08:00 → nay): 567–701 MB. Các đỉnh 650–700 M chỉ xuất hiện ngay sau start; sau đó **phẳng/giảm nhẹ** trong mỗi chu kỳ, không trôi lên qua 3,5 ngày.
- Committed heap 1,9–2,5 G; Xmx 3 G.
- RSS: chỉ có ảnh chụp hiện tại — 3,35 G sau 4'. Log không ghi RSS, nên **chưa đo được xu hướng RSS (native)** trong một chu kỳ.
- Host: MemTotal 7,8 G, **MemAvailable 1,37 G**, swap đã dùng 225 M; collector `BinanceDataIngestor` RSS 2,27 G; cùng máy còn Aerospike + Redis.
- Kết luận:
  - **Không có dấu hiệu leak heap** (live set ~570–600 M, không tăng). Nếu bỏ reset, nguy cơ OOM trong heap thấp (live set ≈ 20 % Xmx).
  - **Native/RSS chưa biết.** Ràng buộc thật là RAM host: chỉ 1,37 G trống; RSS tăng ~1 G là host bắt đầu swap hoặc bị OOM-killer.
  - Đề xuất trước khi bỏ reset: lấy mẫu `ps -o rss` mỗi giờ qua pipe (chỉ đọc) trong ≥ 1 chu kỳ 12h; RSS phẳng thì bỏ được.
  - Bỏ reset còn có lợi: tránh 1 lần tick hụt + warm-up 27 s mỗi 12h, và tránh lịch trôi vào khung cấm.

**3. Cơ chế tự khởi động lại**
- `h242-trading.service` / `h242-ingest.service`: `Type=oneshot`, `RemainAfterExit=yes`, `KillMode=none` — chỉ là boot starter, systemd **không theo dõi PID, không có `Restart=`**.
- crontab root trống; `/etc/cron.hourly` chỉ có `0anacron`; không thấy healthcheck/watchdog nào.
- JVM **không có** `-XX:+ExitOnOutOfMemoryError` hay `-XX:+HeapDumpOnOutOfMemoryError`.
- Hệ quả: nếu JVM chết (OOM, crash, bị OOM-killer) thì **không có gì tự bật lại**. Reset 12h hiện tại không đóng vai watchdog. Nếu bỏ reset nên kèm watchdog (cron kiểm pid) và `ExitOnOutOfMemoryError`.

---

## RSS — lần đo #1 (10-21 13:41:45 +07, giờ thứ ~5,8 của PID 7535; chỉ đọc qua ssh+pipe)

| | PID | RSS | VSZ | etimes | start |
|---|---|---|---|---|---|
| trading v_t_m (v11c) | 7535 | **2 706 588 kB (2,58 GiB)** | 7,48 G | 20 866 s (5,80 h) | 07:53:59 |
| collector `BinanceDataIngestor` | 17517 | 2 192 012 kB (2,09 GiB) | 5,92 G | 16 875 s (4,69 h) | 09:00:30 (tự-restart 12h của collector) |

- So với mốc 4' sau start (RSS 3,35 G, heap committed 2,6 G ngay sau warm-up): RSS hiện **thấp hơn ~0,64 G**, vì G1 trả bớt bộ nhớ sau các lần Full GC. Chưa có điểm đo cùng pha để kết luận về xu hướng native — cần các lần đo tiếp theo.
- Host: Mem 7 821 M, used 5 469 M, buff/cache 2 233 M, **MemAvailable 2 006 M** (lúc 08:00 là 1 370 M); swap dùng 227 M / 8 063 M.
- Full GC (System.gc mỗi 30') trong process này: 11 lần, từ 08:00:34 đến 13:00:33.

| giờ | before→after (committed) | pause |
|---|---|---|
| 08:00:34 | 1622→**671** M (2247) | 1,59 s |
| 08:30:34 | 1012→603 (2020) | 1,41 s |
| 09:00:33 | 1461→603 (2020) | 1,02 s |
| 09:30:32 | 734→593 (1987) | 0,82 s |
| 10:00:33 | 1357→591 (1984) | 1,21 s |
| 10:30:33 | 1185→589 (1977) | 1,17 s |
| 11:00:33 | 1357→588 (1974) | 1,32 s |
| 11:30:33 | 735→587 (1970) | 0,79 s |
| 12:00:33 | 1364→587 (1967) | 0,92 s |
| 12:30:33 | 742→585 (1964) | 0,94 s |
| 13:00:33 | 1354→**583** M (1957) | 0,82 s |

  Live set **giảm đơn điệu** 671 → 583 M, committed heap 2 247 → 1 957 M ⇒ không thấy leak heap; pause max 1,59 s.
- **Healthcheck 242:**
  - `systemctl list-timers --all` chỉ có `systemd-tmpfiles-clean.timer` và `systemd-readahead-done.timer`; không có timer h242-*.
  - `h242-ingest.service` / `h242-trading.service` đều enabled, oneshot, không có `Restart=`, không có timer.
  - `/etc/cron.d` chỉ có `0hourly` (01 * * * * run-parts cron.hourly → `0anacron`); `/etc/cron.daily` có `logrotate`, `man-db.cron`.
  - `crontab -l -u root`: trống. App chạy bằng **root**, nên không có crontab user riêng.
  - `/usr/local/sbin` chỉ có `h242-prestart.sh`.
  - ⇒ **Không tìm thấy "healthcheck cron */5 + Telegram"** như ghi chú harden242 mô tả. Hoặc nó chưa từng được cài, hoặc nằm ở chỗ khác (máy khác / Oracle) — cần owner xác nhận.
  - Telegram hiện chỉ đến từ `Reporter` trong app mỗi 30'. Nếu app chết thì báo cáo này cũng ngừng: không có cảnh báo, không có gì tự bật lại.

---

## Tự-restart 19:54 (kiểm 21:13 +07, chỉ đọc qua ssh+pipe)
| mục | kết quả |
|---|---|
| reset | `Restart: Reset by Schedule` 19:54:31.590 (process cũ 7535); JVM mới **PID 27434**, `ps lstart` **2026-10-21 19:54:30**, ppid 1; log `MainClass` 19:54:32.266; `ThreadAutoRestartProgram` 19:54:43.098 |
| jar (`/proc/27434/fd`) | md5 **eea5adecaff93d3fc350e4d13b3ecb2a** ✔ |
| env | `LIVE_TS_MKT_EXT=1` + 6 key v11b, `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -Xlog:gc…` ✔ (Utils.reset chép toàn bộ env) |
| profile / LEGACY | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true` ✔; `[LEGACY] managed 44` 80/80 dòng ✔ (trước reset 19:54:10 cũng 44) |
| sổ giấy | open=4, realized 88,0877 — không đổi ✔ |
| TS-EXT | `nap 30 ngay tu …/run/ts_ext_daily.csv`, `BAT … days_loaded=30`, rồi `flag day=2026-10-21 flag=OFF dd=-0.137179 … src=file final=true` tại 19:54:43.711 (6 ms sau BAT, **0 lần đọc Aerospike**, kết quả bit-exact với lần tính 07:57 từ aero) ✔. Status 20:00 và 21:00: `flagToday=OFF deferring=0`. Cache 31 dòng (dòng cuối 2026-10-20, 1440 phút) |
| lỗi | **0 ERROR, 0 Exception** từ lúc start; lần này không có race ở tick đầu |
| tick | lần đầu 28,4 s (warm-up), sau đó 1,41 / 0,86 / 0,94 / 0,56 s ✔ |

**Lịch tự-restart kế tiếp:** thread bắt đầu lúc 19:54:43, cộng 12h ra giây 43 — nằm trong khoảng 30–45 nên reset ngay.

| chu kỳ (tính từ bây giờ) | thời điểm |
|---|---|
| 1 | **10-22 ~07:54:4x** |
| 2 | 10-22 ~19:55:3x |
| 3 | 10-23 ~07:55:4x |
| 4 | 10-23 ~19:56:3x |
| 5 | 10-24 ~07:56:4x |
| 6 | **10-24 ~19:57:3x ⇒ rơi khung ±3' đầu giờ** |

Lịch này khớp với dự kiến đã ghi ở phần "DEPLOY LẦN 2" (chu kỳ 7 tính từ lần deploy).

## RSS — lần đo #2 (21:13:38 +07)
| | PID | RSS | VSZ | etimes |
|---|---|---|---|---|
| trading (mới, start 19:54:30) | 27434 | **2 769 828 kB (2,64 GiB)** | 7,48 G | 4 747 s (1,32 h) |
| collector (tự-restart 21:06:30) | 4217 | 1 547 876 kB (1,48 GiB) | 5,91 G | 427 s |

- Host: Mem used 4 845 M, buff/cache 2 801 M, **MemAvailable 2 656 M**; swap dùng 240 M / 8 063 M.
- **RSS của PID 7535 ngay trước reset KHÔNG đo được.** Log không ghi RSS và process đã thoát. Điểm duy nhất có là 13:41 (h 5,8) = 2,58 GiB.
  So sánh cùng pha giữa 2 process: 7535 ở h 5,8 là 2,58 GiB; 27434 ở h 1,3 là 2,64 GiB. Chưa đủ để kết luận về xu hướng native; cần đo 27434 ở h 6 và h 11 (khoảng 01:54 và 06:54 +07, 10-22).
- **Process cũ 7535 (07:53:59 → 19:54:16), gc.log.0** — 2 333 GC, 21 Full GC (System.gc). Heap sau Full GC:
  671 (08:00) → 603 → 603 → 593 → 591 → 589 → 588 → 587 → 587 → 585 → 583 (13:00) → 582 → 580 → 579 → 578 → 576 → 573 → 569 → 569 → 569 → **568 M (19:30, Full GC cuối)**.
  Committed heap 2 247 → 1 907 M. Pause max 1,59 s; các lần sau 12:00 đều ≤ 1,13 s.
  Log `Total ram used` cả chu kỳ khớp số trên (671 → 568 MB).
  ⇒ **live set giảm đơn điệu −103 M trong 12h, không có dấu hiệu leak heap.**
- **Process mới 27434:** Full GC 20:00:34 1771→677 M (2270), 20:30:33 814→599 (2007), 21:00:33 1417→599 (2007); pause max 0,94 s. Cùng mẫu với process cũ: đỉnh sau warm-up rồi giảm dần.

---

## RSS — lần đo #3 (10-22 01:56:35 +07, PID 27434 giờ thứ ~6,0; chỉ đọc qua ssh+pipe)
| | PID | RSS | VSZ | etimes |
|---|---|---|---|---|
| trading (start 10-21 19:54:30) | 27434 | **2 732 700 kB (2,61 GiB)** | 7,48 G | 21 724 s (6,03 h) |
| collector (start 10-21 21:06:30) | 4217 | 2 204 616 kB (2,10 GiB) | 5,92 G | 17 404 s (4,83 h) |

- Host: used 5 463 M, buff/cache 2 216 M, **MemAvailable 2 039 M**; swap dùng 243 M / 8 063 M.
- Full GC (System.gc) của PID 27434, 11 lần (after / committed / pause):

  | giờ | after | committed | pause |
  |---|---|---|---|
  | 20:00:34 | 677 M | 2 270 M | 0,94 s |
  | 20:30:33 | 599 | 2 007 | 0,94 s |
  | 21:00:33 | 599 | 2 007 | 0,85 s |
  | 22:00:33 | 593 | 1 990 | 0,63 s |
  | 22:30:33 | 592 | 1 990 | 0,73 s |
  | 23:00:33 | 591 | 1 987 | 1,14 s |
  | 23:30:34 | 590 | 1 980 | 0,71 s |
  | 00:00:33 | 588 | 1 974 | 0,75 s |
  | 00:30:33 | 587 | 1 967 | 0,95 s |
  | 01:00:33 | 585 | 1 964 | 0,69 s |
  | 01:30:33 | **584** | **1 960** | 0,87 s |

  Pause max 1,14 s.
- **So với #2** (h 1,3: RSS 2 769 828 kB, heap sau GC 599 M, committed 2 007 M):
  - RSS **−37 MB** (2,64 → 2,61 GiB);
  - heap sau Full GC **−15 M** (599 → 584);
  - committed **−47 M** (2 007 → 1 960).
- Cùng pha h≈6 với PID 7535 (lần đo #1, 13:41): RSS 2,58 → 2,61 GiB (+26 MB), live set 583 → 584 M ⇒ hai chu kỳ gần như trùng nhau.
- ⇒ Từ h 1,3 tới h 6, cả heap lẫn RSS đều **phẳng/giảm nhẹ**: chưa thấy dấu hiệu leak heap hay native. Lần đo #4 nên làm ở giờ ~11 (khoảng 06:54 +07), **trước** tự-restart ~07:54:4x.

---

## RSS — lần đo #4 + trạng thái 10-23 (10-23 01:23:46 +07; chỉ đọc qua ssh+pipe)

### 1. 242 hiện tại
| mục | kết quả |
|---|---|
| PID trading | **20596**, ppid 1, `ps lstart` **2026-10-22 19:55:30** (log `MainClass` 19:55:32.351) |
| jar (`/proc/20596/fd`) | md5 **eea5adecaff93d3fc350e4d13b3ecb2a** = v11c. **Không phải** 7767a560/dcae2e2b — v11d/exec-probe **chưa deploy**. `target/` không có file v11d/probe |
| env LIVE_* / SIM_* | `LIVE_TS_MKT_EXT=1`; 6 key v11b (`FEAT_INPUT=snapshot`, `FEAT_MD=inline`, `MD_DIED_SYMBOLS=BTCDOM,USDC`, `MD_SOURCE=inline`, `RANK_TIEBREAK=symbol`, `FUNDING_REFRESH_HOURLY=1`); `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`; `LIVE_ENTRY_GRID_MIN=1`, `LIVE_FEAT_DUMP=3000`, `LIVE_FEAT_DUMP_ROTATE_MIN=10`, `LIVE_GATE_ROLLING_{DAYS=90,MODE=ratio,PCT=0.999950829}`; `SIM_BREAKER_MODE=OFF`, `SIM_FIX_B1/B2/B3=true`, `SIM_F_BASE=0.015`, `SIM_GATE_DYN_SCALE=1.55`, `SIM_LOSER_TIME_STOP_HOURS=168`, `SIM_MIN_MOMENTUM_15M=0.008`, `SIM_RATE_FEE=0.000982`, `SIM_RATE_PROFIT_STOP_MARKET=0.07`, `SIM_SLIPPAGE_RATE=0.000067`, `SIM_TS_GIVEBACK=1`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`, `SIM_TS_PROFIT_MULTIPLIER=3.0`; `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -Xlog:gc…` |
| watchdog | **không có**: crontab root trống, `/etc/cron.d` chỉ có `0hourly`, không có timer h242-*, `h242-trading.service` Type=oneshot, không có `Restart=` |
| LEGACY | `[LEGACY] managed 44` — 1 526/1 526 dòng từ 10-22 tới nay ✔ |
| sổ giấy | 10-22 09:29:01: cả 4 cụm (WAL, TRUTH, APR, SNPS; neo 10-15 02:29 UTC) bị cắt `TIME_STOP_168H` (pnl −43,78 / −17,10 / −59,13 / −5,52), đúng như dự kiến vì cờ 10-22 = OFF. Hiện open=0, realized **−37,45** |
| ERROR/Exception từ 10-22 | **0** |
| TS-EXT | cờ 10-22 tính lúc **07:03:49** (`src=aero:1d final=false`, đúng lịch 00:03 UTC): **OFF dd=−0,130332**, P=−0,0936, max30=0,0461 (09-27), minN 1436. Lần tính lại từ file lúc 07:54:54 và 19:55:42 cho kết quả trùng. Cờ 10-23 **chưa tới lịch** (ngày UTC 10-23 bắt đầu 07:00 +07; tính lúc ~07:03 +07). Cache 32 dòng (đã thêm 10-21 S=+0,0079, 1440 phút). `deferring=0` suốt |

**Các lần restart từ 10-21 19:54 tới nay** (đều là tự-restart `Reset by Schedule`, không có restart tay, không có watchdog):
- 10-21 19:54:31 → PID 27434;
- 10-22 07:54:43 → PID của chu kỳ 10-22 07:54;
- 10-22 19:55:31 → PID 20596.

**Tự-restart kế tiếp:** thread bắt đầu 19:55:41.994.

| chu kỳ (tính từ bây giờ) | thời điểm |
|---|---|
| 1 | **10-23 ~07:55:42** |
| 2 | 10-23 ~19:56:31 |
| 3 | 10-24 ~07:56:43 |
| 4 | **10-24 ~19:57:31 ⇒ rơi khung ±3' đầu giờ** |

Collector `BinanceDataIngestor` restart 10-22 09:12:31 và 21:18:39 (Schedule), và **23:49:42 do `Reset by Price Error Count 54`** (PID 6186 hiện tại).

### 2. RSS #4
Lần đo giờ 11 của PID 27434 đã lỡ (process thoát lúc 10-22 07:54:43). Không có RSS nào trước reset.

| | PID | RSS | VSZ | etimes |
|---|---|---|---|---|
| trading | 20596 | **2 708 544 kB (2,58 GiB)** | 7,48 G | 19 695 s (5,47 h) |
| collector | 6186 | 2 192 132 kB (2,09 GiB) | 5,92 G | 5 644 s |

Host: MemAvailable **2 067 M**; swap dùng 251 M / 8 063 M.

**Heap sau Full GC theo từng chu kỳ** (gc.log* đọc qua pipe, lưu ở Oracle `~/claude_master/v11_tsx/off/live242/gc3/`):
| process (chu kỳ) | n Full | đầu → cuối (after) | committed | pause max |
|---|---|---|---|---|
| 7535 (10-21 07:54→19:54) | 21 | 671 → 568 M | 2 247 → 1 907 | 1,59 s |
| 27434 (10-21 19:54→10-22 07:54) | 22 | 677 → 599 (20:30) → 568 M (07:30) | 2 270 → 1 907 | 1,20 s |
| 10-22 07:54→19:55 | 21 | 722 → 596 (08:30) → 570 M (19:30) | 2 417 → 1 914 | **1,81 s** |
| 20596 (10-22 19:55→nay, h 5,5) | 9 | 645 → 598 → 586 M | 2 167 → 1 967 | 1,18 s |

`Total ram used` trong log khớp với các số trên. Mỗi chu kỳ đều có cùng mẫu: đỉnh 645–727 M ngay sau start, rồi giảm đơn điệu về 568–570 M ở cuối chu kỳ.

**Tổng hợp #1–#4:**
| lần đo | PID | giờ trong chu kỳ | RSS |
|---|---|---|---|
| #1 | 7535 | h 5,8 | 2,58 GiB |
| #2 | 27434 | h 1,3 | 2,64 GiB |
| #3 | 27434 | h 6,0 | 2,61 GiB |
| #4 | 20596 | h 5,5 | 2,58 GiB |

⇒ **Không có dấu hiệu tăng heap theo chu kỳ** (live set cuối chu kỳ 568–570 M qua 3 chu kỳ), và **RSS ở giờ ~6 ổn định 2,58–2,61 GiB** giữa 3 process. Phần còn thiếu: RSS ở giờ 11–12 (cuối chu kỳ) **chưa có điểm đo nào**. Muốn khẳng định chắc về native trước khi bỏ reset cần đo 1 lần ở h≈11 (ví dụ 10-23 ~06:55, trước 07:55).

### 3. gc.log trên 242
| file | process | mtime | size |
|---|---|---|---|
| `gc.log` | 10-22 19:55 (hiện tại) | 10-23 01:23 | 178 316 |
| `gc.log.0` | **10-21 07:53:59 (PID 7535, deploy v11c)** | 10-21 19:54 | 341 598 |
| `gc.log.1` | 10-21 19:54 (27434) | 10-22 07:54 | 363 705 |
| `gc.log.2` | 10-22 07:54 | 10-22 19:55 | 371 589 |
| `gc.log.3` | 10-20 20:33 (v11b) | 10-21 05:55 | 253 078 |
| `gc.log.4` | 10-21 05:55 (v11b + env thừa) | 10-21 07:53 | 58 099 |

Rotation `filecount=5` ghi đè xoay vòng tại mỗi lần start JVM:
- 10-23 ~07:55 ghi đè `.3`;
- 10-23 ~19:56 ghi đè `.4`;
- **10-24 ~07:56 ghi đè `.0` = gc log của process 10-21 07:53:59 sẽ mất lúc đó.**

Bản sao đã có trên Oracle: `live242/gc2/gc.log.0_7535`, `live242/gc/` (5 file 10-19…10-21), `live242/gc3/` (3 file 10-21 19:54…nay).

### 4. Oracle — tiến trình nghiên cứu chạy lâu (chỉ liệt kê, KHÔNG kill)
**PID 758938** — `python3 …/research/tsx_v2_sim/run.py run`
- cwd `~/claude_master/tsx2sim`, start **10-22 07:03:48**, ppid 1 (nohup).
- Đã xong 65/66. Đang poll **1 kernel `tsx2-ho-v420-s7`**: nhận **404 liên tục từ 10-22 12:26:21** (47 lần; lần cuối 10-23 01:24:30), xen 7 lần 429.
- Dòng `PUSHED tsx2-ho-v420-s7` lúc 12:21:16 **không có URL kernel** (các kernel khác có) ⇒ nhiều khả năng push không tạo được kernel ⇒ **treo ~13h**.

**PID 766935** — `python3 …/research/tsx_v3/run.py run`
- cha 766933 `bash /tmp/tsxv3_commit_1022.sh`, cwd `~/claude_master/tsx_v3`, start **10-22 10:30:31**.
- state: 5/9 xong. 4 kernel ở trạng thái PUSHED nhưng nhận 404:
  - `tsx3-v2-a1`: 58 lần;
  - `tsx3-v2-s7`: 55 lần;
  - `tsx3-v2-s13`: 46 lần;
  - `tsx3-v2-s2024`: 25 lần, từ 12:48:37.
- Kèm 429. ⇒ **treo ~12,5h**.

**PID 768034** — `bash …/research/tsx_v3/pipe.sh`
- cha 768032 `bash /tmp/tsxv3_launch_1022.sh`, start 10-22 10:40:05.
- `need.txt` đang chờ 5 kernel trên (gồm cả `tsx2-ho-v420-s7`).

Ngoài ra còn chạy `liq_ws.py` (PID 2178, collector liq, từ 10-15).

## Oracle 10-23: kill pipeline treo (owner duyệt)
- 10-23 07:33:56 (+07) SIGTERM PID 758938 (tsx_v2_sim run.py, treo poll 404 `tsx2-ho-v420-s7` từ 10-22 12:26), 766935 (tsx_v3 run.py, 404 a1/s7/s13/s2024 từ ~12:48), 768034 (tsx_v3 pipe.sh) + con 810437 (`sleep 300`); sau 8 s cả 4 đã thoát, không cần SIGKILL; cha 766933/768032 tự thoát; không còn tiến trình nào poll kernel tsx2-*/tsx3-*; không xoá file/state (`~/claude_master/tsx2sim/state.json` 65/66, `~/claude_master/tsx_v3/state.json` 5/9 giữ nguyên).

---

## Deploy dcae2e2b (10-23, owner chạy `deploy_dcae2e2b.sh`; agent kiểm chỉ đọc lúc 09:42:24)

### Log deploy (Oracle `~/claude_master/deploy/`)
- `deploy_20261023_0926.log` (bản b73378bb): mọi kiểm OK, nhưng **FAIL cu_phap_JVM** là false-FAIL do script — `grep -i error` tự khớp
  `ExitOnOutOfMemoryError`. Script đã khôi phục env.sh + start.sh, không restart. Sửa thành bản c5c1b0dd (bỏ dòng `Picked up` trước khi tìm lỗi,
  backup bằng `cp -p`).
- `deploy_20261023_0936.log`: dừng tay ở bước scp jar, không đổi gì.
- `deploy_20261023_0937.log` (c5c1b0dd), toàn bộ **OK**:
  - kiểm 242 (eea5adec, 1 process, env chưa có key mới, start.sh đúng mẫu, chưa có cron, có curl/flock);
  - scp; backup; env +5 dòng (comment + 4 key); start.sh đổi đúng 1 dòng; `cu_phap_JVM` OK;
  - YES lúc 09:37:28; `da_stop`, `jar_da_thay`, **`OK started pid=18743 lstart=Fri Oct 23 09:37:29 2026`**;
  - kiểm sau start lần 1 ĐẠT (09:39:40);
  - watchdog: cú pháp OK, dry-run `OK_GRACE pid=18743`, **telegram test 2/2**, **cron đã cài**;
  - dòng cuối `=== XONG. OK started pid=18743 lstart=Fri Oct 23 09:37:29 2026`.

### Kiểm độc lập trên 242 (09:42:24, chỉ đọc)
| mục | kết quả |
|---|---|
| process | **PID 18743**, ppid 1, **1 process**, `lstart` **2026-10-23 09:37:29**, log `MainClass` 09:37:31.240; RSS 3,12 G ở 294 s |
| jar (`/proc/18743/fd`) | **dcae2e2bbb1a357bc15703b416d4dccb** ✔ |
| env process | `LIVE_HEARTBEAT=1`, `LIVE_KILLSW_MODE=log`, `LIVE_PERIODIC_RESET_HOURS=0`, `LIVE_EXEC_PROBE=1`, `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `LIVE_TS_MKT_EXT=1` + 6 key v11b; `JAVA_TOOL_OPTIONS=-Xms1g -Xmx3g -XX:+ExitOnOutOfMemoryError -Xlog:gc:file=logs/gc_%p_%t.log:…` ✔ |
| diff env | đúng 5 dòng (`# [v11d+exec-probe 20261023_0937] …` + 4 export) ✔ |
| diff start.sh | đúng 1 dòng (JAVA_TOOL_OPTIONS) ✔ |
| quyền | `bin/start.sh` `-rwxrwxrwx root` — giống bản gốc (backup `cp -p` cũng 777, mtime gốc 09:26:33) |
| `[OPS] v11d` | `LIVE_PERIODIC_RESET_HOURS=0h … LIVE_HEARTBEAT=1 file=run/heartbeat LIVE_KILLSW_MODE=log => hieu luc=log profile=c3_shadow` ✔ |
| reset | `[OPS-RESET] LIVE_PERIODIC_RESET_HOURS=0 => TAT reset dinh ky` ✔; không có `TU CHOI` ✔ |
| `[KILLSW] BAT` | `mode=log CHI LOG …` ✔. WOULD_TRIGGER: **0** (mọi mã); HOURLY chưa tới giờ đầu |
| `[HEARTBEAT] BAT` | có (09:38:06); `run/heartbeat` 0 byte, **tuổi 19 s** ✔ |
| c3_shadow | `[LIVE_PROFILE=c3_shadow] BAT … SHADOW_NO_PUSH=true` ✔ |
| LEGACY | `managed 44` 6/6 dòng ✔ |
| TS-EXT | `BAT … days_loaded=32` + `flag day=2026-10-23 flag=OFF dd=-0.173328 … max30Day=2026-09-27 minN=1436 src=file final=true` ✔ |
| EXEC-PROBE | 0 dòng — đúng thiết kế (engine khởi động lười, chờ leg giấy đầu tiên; sổ giấy đang open=0) |
| lỗi | **0 ERROR, 0 Exception** ✔ |
| PASS-TIMING | 30,9 s (tick đầu, warm-up) → 0,87 / 0,43 / 0,47 / 0,39 s ✔ |
| gc log | `logs/gc_18743_2026-10-23_09-37-30.log` (đúng PID) ✔; 2 file 48 byte của JVM thử (`gc_6955…`, `gc_18471…`) vô hại; `gc.log*` cũ để nguyên |
| watchdog | crontab root `*/2 * * * * /usr/local/sbin/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1`; script md5 **cf221b97…** ✔; `tg.env` 600; `watchdog.log`: 09:40:01 `OK_GRACE pid=18743 up=152s`, 09:42:02 `OK_GRACE … up=272s` (grace 10') |
| sổ giấy | open=0, realized **−37,4455** (không đổi so với trước deploy) ✔ |

⇒ **ĐẠT.** Đã ghi sổ C (ADDENDUM d). **Cửa sổ promotion 10-21 07:53:59 không reset.** Từ PID 18743 không còn tự-restart 12h.
Việc cần theo dõi: HOURLY và WOULD_TRIGGER (C1–C6) sau 24–48h; dòng `[EXEC-PROBE] BAT` khi có leg giấy đầu tiên; watchdog chuyển từ
`OK_GRACE` sang `OK` sau 09:47; RSS theo thời gian (không còn reset 12h).

## 24h sau dcae2e2b (MASTER 10-24 ~10:15 +07; nguon: pull242/2026-10-23 full.log toi 10-24 08:25:30 + health242 Oracle; KHONG ssh 242)
- Process: khong restart tu deploy 10-23 09:37:31 (MainClass cuoi = 09:37:31; truoc do 07:55:42 la tu-restart v11c cu). health242 trading_n=1 lien tuc toi 10-24 09:30.
- 0 dong ERROR/Exception/OutOfMemory tu 09:37 10-23 toi 08:25 10-24.
- RSS/GC: CHUA DO TRUC TIEP (gc_18743_*.log va ps tren 242 khong co trong pull242; doc 242 bi classifier chan). Proxy: mem_avail 242 on dinh 1 898–2 098 MB (khong giam dan), heap ExecProbe-STAT 850–1 053 MB.
- [KILLSW] HOURLY mode=log: C1–C6 = 0/0 moi gio, C2=NA, 0 WOULD_TRIGGER; lag_s=6 miss=0/741; so giay eq 34 886–34 942, peak 35 015, dd ~0; open 19–23, U 0,066–0,080.
- Dot crash-buy dau tien sau deploy: 10-24 02:25 +07 [GATE] n_pass=24 (thr thuc 0,02281..0,03645, u=0,0805) + 02:28 n_pass=1.
- [EXEC-PROBE] BAT 02:25; STAT 08:25: offered=31 lines=31 dropped=0 no_book=0 rate_capped=0 avg_snap_ms=524.
- So giay: dong TRAILING_STOP AVA/ARIA/APR (+7,8…+10,0 USD); realized 50,57.
- LEGACY 44 (health242 legacy_n=44 lien tuc); [SHADOW] skip-LEGACY SOXSUSDT moi phut (binh thuong).
- TS-EXT: co 10-23 OFF (dd −0,173), 10-24 OFF (dd −0,168, final=false luc 07:03).
- health242: 0 dong khong-OK tu 09:30 10-23.
