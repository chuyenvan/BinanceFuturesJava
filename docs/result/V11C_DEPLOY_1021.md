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
