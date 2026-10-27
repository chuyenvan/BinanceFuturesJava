# V12_ROUND3B — CANARY-EARLY (MASTER 10-27, owner duyệt)

Branch `v1.2/c3-live`, agent v12exit, 2026-10-27. Chỉ code + test + script; **không gọi Binance, không đụng 242, không push**. Mọi kiểm thử
trên `MockExchangeGateway` (Java) và "242 giả" trên đĩa Oracle (script). **A1 audit vòng 3 + 3b trước khi chạy**; MASTER tạo
`~/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok` sau khi A1 ĐẠT (thiếu file ⇒ script từ chối).

## 1. Hash, addendum, jar

| mục | giá trị |
|---|---|
| addendum prereg §ADD-1 (commit riêng, TRƯỚC code) | `6bd2ee8d` — `docs/prereg/GCANARY_PREREG.md` sha256 `d87977f56bc27e88e138c2264e43eb7cabe81430bb6e0e09420890a1c009b585` |
| guard env sạch + test cô lập (Java) | `74a87301` |
| script canary-early + test_fake242 mục 15 | `45cb424a` |
| pin jar 3b | `b873ac45` |
| jar dùng chung canary-early + dry | `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3b`, md5 **`5405dfb2d076768ed7d751095818fb07`** (pin `canary_lib.sh` CANARY_JAR_MD5 + `deploy_v12_dry.sh` NJ_MD5). Jar 3 `e702cc2d` đã xoá (code canary đổi). |
| build | 642 test, 0 fail (640 vòng 3 + `canaryRefusesUncleanEnvBeforeLockOrClient` + `CanaryIsolationTest`) |
| test script | `ops/c3live/test/test_fake242.sh` **103/103 PASS** (102/102 khi chạy trong khung giờ: 1 kiểm time_ok chỉ chạy ngoài giờ; mục 15 mới: 26 kiểm canary-early) |
| parity 10-23 (c3_shadow, jar 3b vs dcae2e2b) | **PASS** — out_BT `e0918a33` khớp, out_NEW2 `e0918a33` khớp, fund_BT `a81b3b03` khớp, fund_NEW2 `8dea3f70` khớp; ctl only_ref = only_new = 0; strace AF_INET non-loopback = 0 (`docs/result/round3b/r3b_compare.json`) |

Delta code so với vòng 3 (`47b29566`): **chỉ** `c3live/canary/C3LiveCanary.java` (guard env sạch) + test. Không đổi đường c3_shadow/runtime.

## 2. Canary có dùng symbol_mapper / Aerospike / Redis không?

**KHÔNG** — với env sạch. Có **1 đường ngầm** đã được chặn:

- `c3live/exit/TrailingStopManager.java:147` (`TsMktExt.startIfEnabled()`), `:477`, `:482` gọi X14 `tradecore/selector/TsMktExt.java`.
  X14 bật khi `Cfg(LIVE_TS_MKT_EXT)=1` **và** `LIVE_PROFILE ∈ {c3_shadow, c3_live}` (`TsMktExt.java:81-83`, `decideEnabled`); khi bật,
  `getInstance` (`:151`) đọc kline từ Aerospike 242 qua `DataManagerAerospikeFloatSim.readDataFromAerospikeCustom` (`:172`) — dữ liệu
  phụ thuộc symbol_mapper (đang có id trùng `{1: BTCUSDT, XUSDT}`). **Env của v_t_m có đúng 2 biến này** (`LIVE_PROFILE=c3_shadow`,
  `LIVE_TS_MKT_EXT=1`) ⇒ nếu JVM canary kế thừa env v_t_m thì sẽ đọc Aerospike. `Cfg` còn nạp `TRADING_PROFILE` (`tradecore/Cfg.java:85-120`).
- Chặn 2 lớp:
  1. **Code (fail-closed):** `c3live/canary/C3LiveCanary.java:74` (`FORBIDDEN_ENV`), `:80` (`isolationProblem`), `:99` (gọi đầu `run`) — `C3LiveCanary.run` TU_CHOI (mã 2) cho MỌI lệnh nếu env có `LIVE_PROFILE` / `TRADING_PROFILE` /
     `LIVE_TS_MKT_EXT` khác rỗng, **trước** lock, trước tạo client, trước khi `Cfg` được nạp. 3 biến này là toàn bộ đầu vào của cờ X14
     ⇒ X14 tắt chắc chắn.
  2. **Script:** JVM luôn chạy `env -i PATH HOME LANG CANARY_* LIVE_C3_*` (cả mode chuẩn) ⇒ không kế thừa env nào khác.
- **Bằng chứng chạy:** `CanaryIsolationTest` chạy toàn bộ `CanaryEngineTest` (K0..K8, K6b, K7b, guard) + `CanaryGuardTest` (gồm
  `C3LiveCanary.run`) trong JVM con với `-Xlog:class+load`; khẳng định 0 lớp `com.aerospike.*`, `redis.clients.*`, `io.lettuce.*`,
  `org.redisson.*`, `com.binance.chuyennd.aerospike.*`, `*symbol_mapper*`/`*SymbolMapper*` được nạp (và các lớp canary/c3_live thật sự có
  nạp — đối chứng). Đường client thật (`C3LiveClient`, `UserStream.okHttp`) chỉ import `c3live.api` + okhttp/gson (tĩnh); Telegram qua
  `utils/Utils` (HTTP, static chỉ Gson/SimpleDateFormat).
- Lớp ngoài `c3live` mà canary chạm: `ops.KillSwitchEngine` (chỉ enum `Action.NONE`), `tradecore.selector.C3TrailRate`/`LiveProfileC3`
  (hằng số), X14 (tắt), `utils.Utils` (Telegram). Không Redis, không Aerospike.
- Canary không đọc/ghi gì trong v_t_m. Script đọc (chỉ đọc) của v_t_m: md5 `target/binance-java-sdk-1.2.4.jar`, `conf/env.sh`,
  `bin/start.sh`; PID/cwd/environ process bot; sự tồn tại `run/canary`; và **bản sao** `run/legacy_symbols.csv` (cho luật LEGACY §3, ghi
  vào `c3canary/run/`).

## 3. Guard mới (mode early)

| guard | ở đâu | test |
|---|---|---|
| env sạch (LIVE_PROFILE/TRADING_PROFILE/LIVE_TS_MKT_EXT ⇒ TU_CHOI trước lock/client) | `C3LiveCanary.isolationProblem` | `canaryRefusesUncleanEnvBeforeLockOrClient`, `CanaryIsolationTest`; fake 15b (ENVX=0 dù script được gọi với 3 biến) |
| thư mục RIÊNG `/home/chuyennd/java/c3canary` (700), jar riêng md5 = pin, lock/sổ/state/journal riêng `run/`; CANARY_HOME không được nằm trong v_t_m | `canary_lib.sh` (CANARY_MODE=early), `canary_early_install.sh` | fake 15a/15b |
| v_t_m phải chạy `LIVE_PROFILE=c3_shadow` + `SHADOW_NO_PUSH=true`, không `LIVE_ADAPTER` (process nhận theo cwd = v_t_m, như watchdog) | `cl_check_242 early` | fake 15a |
| MemAvailable ≥ 1 GB trước install/K0 và đầu phiên; ≥ 768 MB trước mỗi bước (hằng số `readonly`) | `cl_ram_check` | fake 15a, 15f |
| v_t_m KHÔNG ĐỔI: md5 jar/env/start + PID + env bot, chụp đầu phiên, so TRƯỚC + SAU mỗi bước (và sau K0, sau flatten, cuối phiên); `v_t_m/run/canary` không được xuất hiện; lệch / không đọc được (3 lần) ⇒ DỪNG + flatten | `cl_vtm_baseline`, `cl_vtm_check` | fake 15b, 15c, 15d (env đổi trong K3), 15e (PID đổi trong K2) |
| điều kiện vào bỏ "dry ≥ 5 ngày" + gate PROMO **chỉ** khi `CANARY_MODE=early`; gate CODE giữ | `canary_lib.sh` GATE_FILES | fake 15a; mục 14 (chuẩn) vẫn đòi đủ |
| K0 phải DAT, < 24 h, phiên chưa có bước giao dịch; phiên cũ có giao dịch ⇒ install TU_CHOI trừ `CANARY_RESET=1` (chỉ khi phẳng; giữ `run/canary_prev_<TS>`) | `canary_early_run.sh`, `canary_early_install.sh` | fake 15d/15e |
| YES hỏi 1 lần; phiên chạy nền `setsid` (đóng terminal không dừng); dừng khẩn cấp: file `~/claude_master/canary/CANARY_STOP` (canary_flatten early tự tạo); STOP còn ⇒ phiên mới TU_CHOI | `canary_early_run.sh`, `canary_flatten.sh` | fake 15c, 15h |
| K1 −2019 ⇒ TRƯỢT + ghi PHƯƠNG ÁN B (nạp 50 USDT) trong file kết quả | `canary_early_run.sh` | fake 15g |
| file kết quả chặn mẫu bí mật (che + TRƯỢT) | `canary_early_run.sh` | fake 15c (không key) |

Guard cứng vòng 3 giữ nguyên (20/25/40 USDT, trần lỗ 2 USDT, 2 symbol theo luật, không chạm symbol khác, lock, chiều lệnh, MỞ-5 1 lần).

## 4. Hai lệnh owner (trên Oracle)

```
YES=1 CANARY_EXPECT_TMB=10000 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_install.sh
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_run.sh        # gõ YES một lần
```

1. `canary_early_install.sh` (~70′, CHỈ ĐỌC trên sàn): kiểm gate CODE, jar Oracle md5, khung giờ; kiểm 242 (v_t_m shadow, RAM, đĩa, không
   JVM canary); chụp v_t_m; tạo `c3canary/`, scp jar + kiểm md5 trên 242, logback, bản sao LEGACY; `keycheck`; K0 65′; so v_t_m.
   Không `YES=1` ⇒ chỉ kiểm, không ghi gì. In 2 symbol đã chọn.
2. `canary_early_run.sh` (~2–3 h): hỏi YES; chạy nền; K1 K2 K3 K4 K5 K6 K6b K7 K7b K8; mỗi bước kiểm STOP / giờ / v_t_m / RAM trước, v_t_m
   sau; TRƯỢT ⇒ flatten + dừng; cuối phiên tự `canary_report` (mode early: tiêu chí 4 = KHONG_AP) + `cleanup`; DAT cả phiên ⇒ đổi tên
   `run/canary_done_<TS>`; xuất **1 file** `~/claude_master/canary/canary_early_result_<TS>.txt` (các bước, v_t_m từng bước, RAM, báo cáo
   §5, cleanup; không key) cho MASTER.
- Phương án B: USDT = 0 và K1 −2019 ⇒ owner nạp 50 USDT vào tài khoản con, báo MASTER (MASTER quyết chạy lại, `CANARY_RESET=1`).
- Khẩn cấp: `touch ~/claude_master/canary/CANARY_STOP` hoặc `CANARY_MODE=early YES=1 bash .../canary_flatten.sh`.

## 5. Điểm mở

1. **LEGACY:** script đọc (chỉ đọc) `v_t_m/run/legacy_symbols.csv` để áp luật LEGACY §3; không có file ⇒ tập rỗng (ghi trong log). Nếu
   MASTER muốn 0 lần đọc nội dung v_t_m thì luật LEGACY không áp được — cần MASTER quyết.
2. **MỞ-5 trong canary-early mặc định TẮT**; muốn kiểm timeout/queryOrder(cid) thì owner chạy `CANARY_INJECT_TIMEOUT=1 bash canary_early_run.sh`
   (MASTER quyết).
3. **PID v_t_m đổi vì watchdog/OOM** (watchdog nhận bot theo main class + cwd = v_t_m, không đụng JVM canary; PAUSE đang có) ⇒ phiên dừng
   (fail-closed) dù canary không gây ra; chạy lại cần MASTER + `CANARY_RESET=1` (mỗi phiên mới có ngân sách lỗ 2 USDT riêng — MASTER quyết).
4. **RAM:** JVM canary `-Xmx384m -XX:+UseSerialGC -XX:MaxMetaspaceSize=256m` (ước ~0,5 GB RSS) cạnh shadow + ingestor; ngưỡng 1 GB / 768 MB.
5. **Chưa có `allOrders`** (giữ từ vòng 3): §5.1 đếm cid từ journal.
6. Kết quả canary-early **không** thay G-CANARY chuẩn nếu jar đổi trước G-MICRO (§5: lặp lại rút gọn sau mọi đổi jar); G-MICRO vẫn cần
   G-PROMO + dry ≥ 7 ngày.
7. `deploy_v12_dry.sh` cũng pin jar 3b (dùng chung) — A1 audit delta `47b29566..HEAD` trước deploy dry.
