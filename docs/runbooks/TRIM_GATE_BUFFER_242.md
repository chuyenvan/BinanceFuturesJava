# Runbook — lọc buffer gate rolling 242 (`run/gate_ratio_live.bin`)

Mục tiêu: bỏ 19 168 record (1 198 tick, 2026-09-30 17:01 → 10-01 12:59 +07) là r của cấu hình cũ khỏi buffer GRR1 của app 242
(`/home/chuyennd/java/v_t_m`), để q₀.₉₉₉₉₅₀₈₃ = quần thể sạch (~0,0065) thay vì ~0,0111.
Script: `research/parity/trim_gate_buffer.py` (chạy trên **Oracle**, cần python-snappy — KHÔNG cài gì lên 242).
Test trên bản sao 10-05: `docs/result/trim_gate_buffer_test_20261005.json`. Người chạy: MASTER (agent prep KHÔNG chạy gì ở đây).

## 0. CHẶN — KHÔNG chạy trước 2026-10-08 13:00:00 +07 (đọc kỹ)

`LiveGateRollingRatio.loadPersistedAndSeed` (`:179-208`): nếu `persistedStart > now − 7d` ⇒ `seedHistory(now−90d, persistedStart)`
rồi `GateRatioPersist.writeFresh` (**ghi lại toàn bộ file**). File đã lọc có `persistedStart = 2026-10-01 13:00:00`.
- Start app **trước 10-08 13:00:00** ⇒ seed chạy. Mô phỏng trên bản sao (`predictionSymbol/<ngày>/<ts>` căn phút từ 09-30 17:01, p15 từ
  `prediction/`): seed tái tạo **đúng 1 198 tick / 19 168 record 09-30 17:01 → 10-01 12:59**, r p50 0,00269 / max 0,01399
  (gốc 0,00256 / 0,01401) ⇒ q sau seed = **0,011118** ≈ chưa lọc (0,011143). File bị ghi lại ⇒ **việc lọc mất tác dụng, im lặng**
  (chỉ thấy dòng log `[GATE-RATIO] seed lịch sử: 19168 record (20260930 17:01..20261001 12:59)`).
  (Giả định: Aerospike `ai_pred_1m` còn p15 các tick đó — chưa kiểm được; nếu không còn ⇒ seed rỗng ⇒ fallback 0,008 tới 10-08 13:00.)
- Áp dụng cho **mọi** lần start sau khi chép file lọc, kể cả auto-restart 12h (`ThreadAutoRestartProgram` → `Utils.reset`, ~01:0x / ~13:0x).
- ⇒ **Đề xuất dời sang 10-08, cửa sổ 13:05–14:00 +07** (sau mốc, tránh auto-restart ~13:0x: chạy sau khi đã thấy dòng
  `Restart: Reset by Schedule` của chu kỳ đó hoặc ≥ 13:10). Khi đó: không seed, firstTs = 10-01 13:00 ⇒ **armed ngay** ở giờ đầu.
- Hệ quả giữ file cũ tới 10-08: 242 tự arm lúc **10-07 18:00** với q ≈ 0,0111 (gate chặt hơn sạch ~0,0065; shadow `SHADOW_NO_PUSH=true`).
- Muốn làm 10-07 thì chỉ có cách đụng dữ liệu 242 (tạm dời `storage/data/predictionSymbol/20260930`, `.../20261001` khỏi chỗ) hoặc sửa Java — cần owner duyệt riêng; runbook này KHÔNG làm.

## 1. App 242 chạy thế nào (đọc-only 10-05)
- Process: `java -server -Xms5g -Xmx5g … -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager`,
  cwd `/home/chuyennd/java/v_t_m`, ppid 1, **không systemd / supervisor / cron**. Khởi động bằng `bin/daemon.sh start` (source `conf/env.sh`,
  `nohup bin/start.sh > logs/nohup.out`), pidfile `./run/com.binance.chuyennd.trading.BinanceOrderTradingManager.pid` (`APP_PID_DIR=./run`
  tương đối ⇒ **phải `cd` vào app dir**). Auto-restart 12h tự spawn JVM mới + `System.exit(0)` (pid mới tự ghi pidfile).
- Stop: `bin/daemon.sh stop` = SIGTERM, chờ ≤60 s rồi `kill -9`. **KHÔNG tự `kill -9`.**
- Cùng máy có `BinanceDataIngestor` (cwd `/home/chuyennd/java/collectData`) — KHÔNG đụng.
- App quản trailing 48 vị thế THẬT `[LEGACY]` ⇒ giữ thời gian dừng ngắn (< 5 phút).

## 2. Flush lúc shutdown — quyết định thứ tự
- Live gom record vào `pending`, flush 1 chunk mỗi 4 096 record (`appendRecord`/`flush`), và **shutdown hook `GateRatioPersistFlush` append
  phần pending (< 4 096) vào file khi JVM thoát** (SIGTERM từ `daemon.sh stop`, hoặc `System.exit` của auto-restart). `kill -9` ⇒ mất pending
  (có thể để lại chunk cuối ghi dở — Java bỏ qua im lặng; script báo `truncated_tail`).
- ⇒ **Phải STOP trước rồi mới lấy bản cuối để lọc**; nếu chép file lọc vào lúc app còn chạy, hook sẽ append vào file mới (append theo path) và
  mọi record mới phát sinh trước đó trong file cũ bị mất.
- File không có header; Java nạp: magic sai / CRC lệch ⇒ `IOException` ⇒ coi persist rỗng ⇒ seed + `writeFresh` (**mất toàn bộ buffer**) ⇒
  script từ chối mọi chunk hỏng; chunk cuối ghi dở chỉ chấp nhận với `--allow-truncated-tail` (dùng cho lượt 1 khi app đang chạy).

## 3. Lệnh (chạy trên Oracle, `bash`; KHÔNG chạy trong vòng prep)

```bash
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
SCP="scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"
A=/home/chuyennd/java/v_t_m
R=/home/ubuntu/src/BinanceFuturesJava            # git pull --ff-only trước
TS=$(date +%Y%m%d_%H%M); W=/home/ubuntu/claude_master/trim242_$TS; mkdir -p $W && cd $W
# 0) chặn giờ (mục 0)
[ $(date +%s) -ge $(date -d '2026-10-08 13:00:00 +0700' +%s) ] || { echo "CHUA DEN 10-08 13:00 +07 — DUNG"; exit 1; }
$S "cd $A && cat run/*.pid; pgrep -fa BinanceOrderTradingManager; grep 'GATE-RATIO' logs/full.log | tail -3; grep 'Reset by Schedule' logs/full.log | tail -1"
# 1) lượt 1 (app đang chạy) — chỉ để kiểm trước
$S "cat $A/run/gate_ratio_live.bin" > live_pass1.bin
python3 $R/research/parity/trim_gate_buffer.py --in live_pass1.bin --out pass1_trim.bin --cutoff "2026-10-01 13:00" --tz +07:00 \
  --restart-at "$(date -d '+10 min' '+%Y-%m-%d %H:%M')" --allow-truncated-tail --dry-run --report pass1.json
#    kỳ vọng: after.first_ts 2026-10-01 13:00, after.q_at_h_eval ~0.0064–0.0066, "seedHistory khong", armed ngay; before.q ~0.011
# 2) STOP (SIGTERM → hook flush pending)
$S "cd $A && bin/daemon.sh stop; sleep 2; pgrep -fa BinanceOrderTradingManager || echo STOPPED; ls -la --time-style=+%T run/"
# 3) lượt 2: bản cuối sau flush
$S "cd $A && sha256sum run/gate_ratio_live.bin"; $S "cat $A/run/gate_ratio_live.bin" > live_final.bin; sha256sum live_final.bin  # 2 sha phải trùng
# 4) lọc thật (KHÔNG --allow-truncated-tail; nếu báo truncated_tail ⇒ stop đã rơi vào kill -9: xem nohup.out rồi mới quyết)
python3 $R/research/parity/trim_gate_buffer.py --in live_final.bin --out trim_final.bin --cutoff "2026-10-01 13:00" --tz +07:00 \
  --restart-at "$(date -d '+5 min' '+%Y-%m-%d %H:%M')"         # exit 0; report trim_final.bin.report.json; "seedHistory khong"
# 5) nạp bằng Java (jar shadow2 20d412e8: GateRatioPersist/GateRatioBuffer .class md5 TRÙNG jar 242 8f3ee52c)
JAR=/home/ubuntu/claude_master/1005/shadow2/jar/binance-java-sdk-1.2.4.jar
mkdir -p jout && javac -nowarn -cp $JAR -d jout $R/research/parity/java/com/binance/chuyennd/ai_ml/onnx/entry/TrimGateBufferCheck.java
HE=$(python3 -c "import json;print(json.load(open('trim_final.bin.report.json'))['after']['h_eval_ms'])")
java -Xmx1g -cp jout:$JAR com.binance.chuyennd.ai_ml.onnx.entry.TrimGateBufferCheck trim_final.bin 0.999950829 90 $HE
#    qbits Java == after.q_at_h_eval_f32_bits; n == after.n; fallback=false
# 6) backup + chép (mv nguyên tử cùng FS)
$S "cd $A && cp -p run/gate_ratio_live.bin run/gate_ratio_live.bin.bak_$TS"
$SCP trim_final.bin root@103.157.218.242:$A/run/gate_ratio_live.bin.trim_$TS
$S "cd $A && sha256sum run/gate_ratio_live.bin.trim_$TS && mv run/gate_ratio_live.bin.trim_$TS run/gate_ratio_live.bin"; cat trim_final.bin.sha256
# 7) START
$S "cd $A && bin/daemon.sh start; sleep 60; pgrep -fa BinanceOrderTradingManager"
```

## 4. Kiểm sau start
```bash
$S "cd $A && grep -E 'GATE-RATIO' logs/full.log | tail -5; grep -E '\[GATE\] ' logs/full.log | tail -2; grep '\[LEGACY\] managed' logs/full.log | tail -1; grep -c ' ERROR ' logs/full.log"
```
- PASS: `LIVE BAT … pct=0.99995083 window=90d`; **KHÔNG có** dòng `seed lịch sử` (có ⇒ lọc bị ghi đè ⇒ mục 5);
  `nạp buffer: size=<after.n> firstTs=20261001 13:00 (warm-up=armed)`; **không** có `truy vấn TRƯỚC khi đủ 7 ngày`.
- Đầu giờ kế tiếp: `[GATE-RATIO] q_t=` ≈ `after.q_at_h_eval` (lệch nhỏ vì r mới); `[GATE] … thr=[…]` dựng trên q_t, không còn base 0,008;
  `[LEGACY] managed 48` mỗi phút; ERROR không tăng bất thường.
- Sau ≥1 giờ: kéo file + log về, `python3 $R/research/parity/gate_arm_check.py <bin> --log full.log` ⇒ exit 0 (q_t log = q tính lại).

## 5. Rollback
```bash
$S "cd $A && bin/daemon.sh stop && cp -p run/gate_ratio_live.bin run/gate_ratio_live.bin.failed_$TS && cp -p run/gate_ratio_live.bin.bak_$TS run/gate_ratio_live.bin && bin/daemon.sh start"
```
- Record live phát sinh giữa start và rollback không có trong `.bak` (mất vài giờ r — chấp nhận; hoặc nối từ `.failed_` bằng script nếu cần).
- Không xoá `.bak_*`/`.failed_*` (dọn sau khi MASTER xác nhận).
