# Runbook — exec-probe (đo chi phí thực thi, CHỈ LOG) trên 242 (OWNER tự chạy)

Căn cứ: ADDENDUM d `PREREG_SHADOW2_PROMOTION.md` (nhánh research/vz-e1) — thay đổi chỉ vận hành không reset cửa sổ promotion nếu
(1) bytecode + legacy-equivalence harness offline đạt, (2) ghi sổ C, (3) restart = tự-restart. Agent KHÔNG chạy gì ở đây (không
đọc/ghi 242). Pre-reg đo: `docs/prereg/PREREG_EXEC_PROBE.md`. Thiết kế: `docs/plan/GOLIVE_GAP_C3LIVE.md` §4.

| | |
|---|---|
| Jar | `/home/ubuntu/claude_master/exec_probe/jar/binance-java-sdk-1.2.4.jar_xp_dcae2e2b` — md5 **`dcae2e2bbb1a357bc15703b416d4dccb`** |
| Nguồn | nhánh `v1.1/exec-probe` (cha `2f82b6a4` = v11d code) — KHÔNG push. Jar này ⊃ v11d: cờ `LIVE_EXEC_PROBE=0` ⇒ hành vi = v11d |
| Đề xuất | **gộp vào lần deploy SAU v11d** (v11d chạy ổn ≥ 24h, watchdog đã cài) — hoặc thay luôn jar v11d ở lần deploy v11d nếu owner muốn 1 lần restart |

## 0. Thay đổi
| cờ env | mặc định | tác dụng |
|---|---|---|
| `LIVE_EXEC_PROBE` | 0 | 1 = mỗi leg giấy (vào/DCA) và mỗi lần sổ giấy đóng cụm ⇒ 1 dòng `[EXEC-PROBE] …` (CSV, header dòng `#hdr`); mỗi giờ `[EXEC-PROBE-STAT]` |
| `EXEC_PROBE_WS_BASES` | `wss://fstream.binance.com/public/stream?streams=,wss://fstream.binance.com/market/stream?streams=` | xoay base khi 2 lô liên tiếp không nhận được message |
| `EXEC_PROBE_DEPTH` / `_MAX_STREAMS` / `_TIMEOUT_MS` / `_BATCH_MS` / `_MAX_CONN_5M` | 20 / 20 / 3000 / 500 / 30 | giới hạn tải; không cần đặt |
| `EXEC_PROBE_SOURCE` | ws | **KHÔNG đặt trên 242** (`mock` chỉ cho harness) |

Không REST, không API key, không ghi Aerospike/Redis, không đặt lệnh. Mỗi lô = 1 kết nối websocket public ngắn (đóng ngay khi đủ).

## 1. Kiểm offline đã đạt (Oracle 10-21, không chạm 242)
- Unit test `mvn -o package`: 411 test, 0 fail (mới 18: ExecProbeBookTest 8, ExecProbeTest 9, ExecProbeShadowEquivTest 1).
- Bytecode vs v11d `7767a560`: 3 class khác CRC (`DetectEntrySignal2TradeNormal`: 62 IDENTICAL + `createOrderBuyRequest` ADDITIVE_OK;
  `ShadowBookC3`: 35 IDENTICAL + `tick` ADDITIVE_OK; `$TickGate`: 7 IDENTICAL, chỉ LineNumberTable), 13 class mới `ops/ExecProbe*`.
- Harness OFFLINE `ops/verify/harness_xp.sh`: xem báo cáo commit (out/fund byte-identical với eea5adec; ledger/state XP1 == XP0).

## 2. Lệnh (từ Oracle; giờ restart theo `DEPLOY_V11D_242.md` §2)
```bash
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"
A=/home/chuyennd/java/v_t_m
NJ=/home/ubuntu/claude_master/exec_probe/jar/binance-java-sdk-1.2.4.jar_xp_dcae2e2b
TS=$(date +%Y%m%d_%H%M)
md5sum $NJ    # dcae2e2bbb1a357bc15703b416d4dccb
$S "cd $A && md5sum target/binance-java-sdk-1.2.4.jar; grep -c '^export LIVE_EXEC_PROBE' conf/env.sh"   # jar = 7767a560… (v11d); 0
$SCP $NJ root@103.157.218.242:$A/target/binance-java-sdk-1.2.4.jar.xp_dcae2e2b
$S "cd $A && \cp -f target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_v11d_$TS && \cp -f conf/env.sh conf/env.sh.bak_v11d_$TS"
$S "cd $A && printf '%s\n' '# [exec-probe $TS] chi log (ADDENDUM d)' 'export LIVE_EXEC_PROBE=1' >> conf/env.sh && diff conf/env.sh.bak_v11d_$TS conf/env.sh"
$S "cd $A && [ \"\$(md5sum < target/binance-java-sdk-1.2.4.jar.xp_dcae2e2b | cut -c1-32)\" = dcae2e2bbb1a357bc15703b416d4dccb ]" || { echo "SAI MD5 - DUNG"; exit 1; }
$S "cd $A && bin/daemon.sh stop && \cp -f target/binance-java-sdk-1.2.4.jar.xp_dcae2e2b target/binance-java-sdk-1.2.4.jar && md5sum target/binance-java-sdk-1.2.4.jar && bin/daemon.sh start && sleep 5 && pgrep -fa BinanceOrderTradingManager | cut -c1-100; date '+%F %T'"
```

## 3. Kiểm sau start (chỉ đọc; file log app như runbook v11d)
- Ngay: KHÔNG có dòng `[EXEC-PROBE] BAT` cho tới leg giấy đầu tiên (engine khởi động lười). Khi có leg đầu: 1 dòng
  `[EXEC-PROBE] BAT (CHI LOG…) source=ws …`, 1 dòng `#hdr`, rồi 1 dòng/sự kiện.
- Mỗi dòng sự kiện cột áp chót `status` phải đa số `ok`/`short`. Nếu 2 lô đầu `no_book` ⇒ log `doi base websocket -> …` là đúng thiết kế;
  nếu mọi base đều `no_book` sau 1h ⇒ báo MASTER (không ảnh hưởng giao dịch).
- `[EXEC-PROBE-STAT]` mỗi giờ: `dropped=0`, `worker_cpu_ms` nhỏ (kỳ vọng < 1 000/giờ), `heap_used_mb` không tăng dần bất thường.
- Số dòng ENTRY+DCA ≈ số dòng `[SHADOW] open|add-leg` cùng giờ (V5 pre-reg).

## 4. Rollback
`LIVE_EXEC_PROBE=0` (xoá dòng env) + restart ⇒ = v11d (không cần đổi jar). Hoặc khôi phục `jar.bak_v11d_$TS` + `env.sh.bak_v11d_$TS`.

## 5. Sổ C (ADDENDUM d)
`<giờ start> | exec-probe dcae2e2b (= v11d + LIVE_EXEC_PROBE hook) | cờ LIVE_EXEC_PROBE=1 | bằng chứng: methdiff3 ADDITIVE_OK 2 method, harness_xp out/fund byte-identical + ledger XP1==XP0 | restart = 1 tự-restart`.
Trích dữ liệu cho MASTER khi đủ ≥ 100 leg: `grep -a '\[EXEC-PROBE\]' <log app> > xp_242_<ngày>.log`, kèm `PAPER_EQUITY` trong env.
