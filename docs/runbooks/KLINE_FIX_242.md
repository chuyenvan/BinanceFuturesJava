# Runbook — sửa ingest kline 1m 242 (`ticker.kline_1m_opt`) + backfill + dựng lại buffer gate + healthcheck

Agent KFIX 2026-10-10. Branch `fix/kline-ingest` (KHÔNG merge module — MASTER review). Người thực thi: **MASTER**.
Audit gốc: `docs/audit/KLINE_242_DIVERGENCE.md` (bb43ce5b). Bằng chứng KFIX: `docs/audit/KLINE_FIX_242_EVIDENCE.md`.
Giữ nguyên `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` (runbook này không đụng 2 key đó).

## 0. Tóm tắt (rủi ro trước)
- **Nguyên nhân (đo trực tiếp 2026-10-10 13:32–13:46, 29 symbol × 15 phút = 435 ô):** V8.1 `Rest-Kline-Loop` chụp
  `fapi/v1/klines limit=2` ở giây 2–6 của phút M+1 (`TickerIngestor2AerospikeNew.java:164,235`) rồi ghi "chốt vĩnh viễn" +
  `timeBuffer.remove` (`:288-293`). REST trả nến M **chưa settle** (replica REST trễ, không đơn điệu): snapshot = final
  45% ở +1 s, 61% +2 s, 72% +3 s, 86% +4 s, 97% +5 s, 99,5% +6 s, **100% từ +8 s**. 242 ≠ final 65/435 = **14,9%** (audit 15,7%);
  65/65 open đúng, Q242 ≤ Qfinal 100%, **49/65 trùng bit với snapshot REST chính tay probe chụp ở +1…+4 s**, 12/16 còn lại có Q nằm
  giữa 2 snapshot kề nhau. Lệch tăng theo biên độ phút: 12,1% (H−L<0,1%) → 13,5% → 26,0% (≥0,3%).
- **Race thứ hai (live đọc trước khi ingest ghi xong):** trading 242 đọc nến M ở giây **6,00–6,11** (`isTimeProcessMarket1M`,
  `LiveTickerWindow` chỉ đọc phút MỚI rồi cache vĩnh viễn); ingest log chốt M ở giây p50 5,59 / p99 7,36. 08–10/10: **12,5%** phút
  live đọc TRƯỚC khi M được chốt (shadow #1 12,4%, #2 13,6%) ⇒ đọc nến "nặn" từ ticker/price (Q chỉ vài giây đầu phút) và giữ
  trong RAM tới lần restart (12 h) ⇒ dữ liệu live ≠ Aerospike ≠ sàn.
- **Websocket cũ:** `wss://fstream.binance.com/stream` và `/ws` hiện KẾT NỐI ĐƯỢC NHƯNG IM LẶNG (0 msg/8 s); stream thị trường
  nay ở `/market/stream` (33 msg/8 s). WS `x=true` qua `/market` (30 symbol × 8 phút): 240/240 đủ, **232/232 = 100% trùng REST
  final** (O/H/L/C/Q + số trade); tới sau đóng nến p50 0,52 s, ~22% symbol (ít giao dịch) tới ở ~3,04 s mỗi phút, 0 sau 3,5 s.
- **Sửa (mặc định `KLINE_INGEST_MODE=ws_settle`):** WS `<sym>@kline_1m` x=true (bản cuối của sàn) ghi ở giây 1,5 (tới muộn ⇒ ghi
  ngay khi tới); symbol vẫn thiếu WS ở giây 4 ⇒ REST sớm (WS suy giảm > 50% thiếu ở giây 2 ⇒ REST ngay, như V8.1);
  **pass settle giây 30** (REST limit=3, nến đã đóng ≥ 20 s) so với Aerospike, khác ⇒ ghi đè
  (`rewritten_diff`), thiếu ⇒ ghi; pass đầu sau start limit=30 (lấp lỗ restart). Chặn vòng ticker/price ghi đè phút đã chốt.
  Trễ quyết định **không đổi** (live vẫn đọc ở giây 6) nhưng nến M đã là bản cuối (WS) thay vì ảnh chụp +2…6 s.
- **Rollback không đổi jar:** `KLINE_INGEST_MODE=legacy` (V8.1 y nguyên) + restart ingest. Rollback jar: bản backup.

## 1. Thành phần đọc `kline_1m_opt` và thời điểm đọc nến M (F2)
| Bộ đọc | Nơi | Khi nào đọc nến M | Cache |
|---|---|---|---|
| Gate live + feature market + BIG_DOWN/DCA | `DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade` → `LiveTickerWindow.read(now,1000)` | giây 6–10 của M+1 (đo 6,00–6,11 s) mỗi phút (`MARKET_SCAN_MIN`) | phút đã đọc **không đọc lại** tới restart |
| Selector S1 (lưới 15′) | cùng tick `isTimeProcessData` (giây 6–10, phút %15) | như trên | như trên |
| S1 close 1h | `S1RankerLive.refresh` → key `t−1m` của giờ vừa đóng | tick đầu giờ (giây 6–10) | `hist` theo giờ, không đọc lại |
| Buffer gate rolling | `LiveGateRollingRatio.threshold` (r từ p15 của tick) → `run/gate_ratio_live.bin` | mỗi tick | persist GRR1 |
| Shadow #1 / #2 (Oracle) | `~/shadow_c3/app`, `~/shadow_c3b/app`, cùng code, `AEROSPIKE_READ_CLUSTER=242` | giây 6 (đồng hồ Oracle) | như live |
- Sim giả định vào lệnh ở close nến M. Trước sửa: quyết định ở ~M+1:06 trên nến M là ảnh chụp +2…6 s (14,9% ô sai) hoặc nến nặn
  (12,5% phút). Sau sửa (ws_settle): vẫn ~M+1:06 (0 s trễ thêm), nến M = WS final (tới p50 0,5 s, tối đa ~3,05 s sau đóng nến — vẫn trước giây 6). Phương án chỉ-REST
  muốn đúng phải đọc ≥ +8 s (mất ≥ 2 s và phải dời tick live từ giây 6 lên ≥ 10) — không chọn.
- Rủi ro còn lại: symbol thiếu WS final ở giây 4 vẫn nhận REST sớm (có thể chưa settle); pass settle sửa trong Aerospike ở giây 30
  nhưng live đã cache bản sớm (đếm qua `ws_late` + `early_fetched` trong `[KLINE-INGEST]`). Muốn triệt để: `LiveTickerWindow` đọc lại
  2–3 phút cuối mỗi tick (thay đổi jar trading — đề xuất, KHÔNG làm trong vòng này).

## 2. Thứ tự tổng (ngoài cửa sổ cấm 12:50–13:20, 00:50–01:20 +07; kiểm `grep 'Restart: ' logs/full.log | tail -1`)
| # | Việc | Dừng | Thời gian | Điều kiện đi tiếp |
|---|---|---|---|---|
| A | Deploy jar ingest (h242-ingest) | ingest ~1–2′ (trading KHÔNG dừng) | 10′ | E1–E3 PASS |
| B | Backfill `--apply` 2026-04-25 09:00 → now−10′ | 0 | ~3–4 h | dry-run sau apply = 0 ô đổi |
| C | Dựng buffer gate (live K16, shadow #1 K16, #2 K24) từ nến đã sửa | 0 (chuẩn bị) | 1–2 h | q mới/q cũ trong [0,9; 1,1] |
| D | Restart trading 242 + 2 shadow, chép buffer mới khi app DỪNG | trading ~1–2′ | 15′ | `[TICKER-CACHE] full reload`, `[GATE-RATIO] armed` |
| E | Cron healthcheck mỗi giờ (Oracle) | 0 | 5′ | lần chạy đầu `OK` |
Vì sao phải restart trading (D): RAM live giữ 1000 phút nến cũ (sai + nặn) và buffer r cũ; chỉ full reload mới đọc nến đã sửa.

## A. Deploy jar ingest (`/home/chuyennd/java/collectData`, unit `h242-ingest`)
Jar đang chạy: `target/binance-java-sdk-1.2.4.jar` 2026-08-20 21:25, sha256 `c00d6052d6e23f9e64aabff6815d03b652c19bc976f529b28f4b94ea4ce907e3`.
Jar mới: build trên Oracle từ commit trong báo cáo KFIX (sha256 ghi ở báo cáo; build lại phải ra cùng nội dung lớp, sha có thể khác do timestamp).
```bash
# Oracle
cd /home/ubuntu/claude_master/1010/kfix_wt && git log --oneline -1          # = hash trong báo cáo
/home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -q package -DskipTests && sha256sum target/binance-java-sdk-1.2.4.jar
S="ssh -p 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd target/binance-java-sdk-1.2.4.jar \
    root@103.157.218.242:/home/chuyennd/java/collectData/target/binance-java-sdk-1.2.4.jar.kfix_new
# 242
C=/home/chuyennd/java/collectData; TS=$(date +%Y%m%d_%H%M); cd $C
sha256sum target/binance-java-sdk-1.2.4.jar.kfix_new                       # = sha Oracle
cp -p target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_kfix_$TS   # sha c00d6052…
cp -p conf/env.sh conf/env.sh.bak_kfix_$TS
grep -q '^export KLINE_INGEST_MODE=' conf/env.sh || echo 'export KLINE_INGEST_MODE=ws_settle' >> conf/env.sh
systemctl is-active h242-ingest                                             # active (exited)
systemctl stop h242-ingest        # ExecStop = daemon.sh stop (SIGTERM, ≤ 60 s) — shutdown hook ingest không có state cần flush
pgrep -fc -- '-cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.websocket.BinanceDataIngestor'   # 0
mv target/binance-java-sdk-1.2.4.jar.kfix_new target/binance-java-sdk-1.2.4.jar
systemctl start h242-ingest       # prestart: deps ok, không có bản đang chạy → daemon.sh start
```
- Thời gian dừng ingest: stop ≤ 60 s + start ~10 s ⇒ 1–2 phút không ghi nến. Lỗ được lấp tự động: pass settle ĐẦU TIÊN sau start dùng
  `KLINE_SETTLE_LIMIT_STARTUP=30` (30 phút gần nhất, weight 1/symbol) + `startDataRepair` cũ.
- Ảnh hưởng trong lúc dừng: trading đọc phút thiếu ở giây 6 ⇒ phút đó **rỗng trong cache live** tới khi restart trading (bước D
  xử lý). `price_realtime` dừng cập nhật ~1–2′ ⇒ `checkAndComparePriceDiff`/Reporter không reset (ngưỡng 15′). Funding/OI ingester
  cùng JVM dừng cùng lúc (forward-loop tự bù).
- Weight REST 242 (ước lượng, giới hạn 2400/phút/IP): ws_settle ≈ settle 734 + REST sớm (chỉ symbol thiếu WS, thường ~0) + ticker/price
  40 + premiumIndex 20 ≈ **~800/phút** (V8.1 ≈ 734 + 60 ≈ 800). rest_settle ≈ 734 + 734 + 60 ≈ 1 530/phút. Pass khởi động
  limit=30 vẫn weight 1/symbol. `/futures/data` (OI) tính hạn mức riêng.

### A-E. Kiểm sau deploy (PASS hết mới sang B)
```bash
# 242 (chỉ đọc log)
L=/home/chuyennd/java/collectData/logs/full.log
grep -a 'Started! \[KLINE-INGEST\] mode=' $L | tail -1          # E1: mode=ws_settle, startupLimit=30
grep -a '\[KLINE-WS\] mo ket noi' $L | tail -6                  # E1: 5 kết nối (734/150), không có "dong ket noi" lặp
grep -a 'Chốt nến phút' $L | tail -3                             # E2: mỗi phút 1 dòng (giây 4), ws_final≈số symbol, ws_flush_1s5≈75%, rest_som≈0, thieu_ws≈0
grep -a '\[KLINE-INGEST\] mode=' $L | tail -2                   # E2: sau 10′: failed(+)≈0, open_write_blocked nhỏ, ws_conn=5/5
grep -a '\[KLINE-INGEST\] settle phut' $L | tail -5             # pass đầu: filled_missing = lỗ lúc dừng; sau đó rewritten_diff ≈ 0
# Oracle — E3: REST check phải 0 lệch liên tục 60 phút (chạy tay 3 lần cách nhau 20′ trước khi cài cron)
python3 /home/ubuntu/claude_master/1010/kfix_wt/research/ops/kline_rest_check_242.py --dry-run   # "OK cells=100 lech=0"
# Trading 242 vẫn chạy: "[LEGACY] managed 47" / "Update all position" mỗi phút; health_242.sh --dry-run = OK
```
Nếu `rewritten_diff(+)` > 0,5% số ô/phút kéo dài hoặc `ws_conn` < 5 kéo dài ⇒ đọc log `[KLINE-WS]`; WS hỏng hoàn toàn vẫn KHÔNG mất
nến (REST sớm + settle phủ) nhưng chất lượng nến tại giây 6 quay về như V8.1 ⇒ cân nhắc rollback F1.

## B. Backfill nến lịch sử (`research/ops/kline_backfill_242.py`, chạy trên Oracle, ghi Aerospike 242 qua 3222)
Định dạng ghi đọc từ code thật (`DataManagerAerospikeFloatSim.writeMinuteBatch:192`): key `yyyyMMdd-HHmm` (+07), bin `data` =
Snappy-raw(`MinuteDataFinal{map<string,KlineObjectOptimized> tickers=1}`), symbol ngắn, float32 O=1 H=2 L=3 C=4 Q=5. Script chỉ sửa ô
(phút, symbol) **đã có** trên 242 và có trên nguồn chuẩn (Vision daily; REST cho ngày Vision chưa phát hành), bỏ khác ≤ 1 ulp,
không đụng phút ≥ now−10′, không thêm symbol (`--fill-missing` mới thêm). Ghi bằng `put` có điều kiện generation (record bị ingest
ghi chen ⇒ đọc lại, tính lại). Idempotent: chạy lại ⇒ 0 ô đổi. REST tuần tự, trần `--rest-max-weight 300`/phút, gặp 429/418 DỪNG NGAY.
```bash
cd /home/ubuntu/claude_master/1010/kfix_wt
# B1 dry-run toàn kỳ (chỉ đọc) → số ô đổi theo ngày + ước lượng backup
python3 research/ops/kline_backfill_242.py --from 20260425-0900 --to now --report ~/kline_backfill_dry_all.json > ~/kline_backfill_dry_all.log 2>&1
# B2 apply theo THÁNG (backup trước mỗi ghi: ~/kline_backfill_bak/kline_bak_<ngày>.jsonl.gz, ô cũ+mới+gen)
python3 research/ops/kline_backfill_242.py --from 20260425-0900 --to 20260501-0000 --apply --backup-dir /home/ubuntu/kline_backfill_bak
#    ... lặp 05, 06, 07, 08, 09, 10 (đến now). Sau mỗi tháng: chép backup sang 242 /root/kline_backfill_bak/ (13 G trống) rồi xoá
#    bản Oracle nếu đĩa < 1 G (Oracle / còn ~2 G).
# B3 kiểm: dry-run lại cùng kỳ ⇒ diff=0 mọi ngày; research/analysis/kline_242_div.py d1 trên mẫu ⇒ ≥ 99,99% ô khớp 5 trường
```
- Dung lượng backup (đo dry-run): ~2,1 MB/ngày toàn universe ở mức lệch 7% (09-15); ngày T5–T6 ~2–3× ⇒ **~0,4–0,6 GB** cả kỳ (gzip).
- Thời gian: dry-run 1 ngày toàn universe 38 s (1 442 file Vision); apply ~1 phút/ngày ⇒ ~3 h cho 168 ngày. Tải ghi 242: 1 440 put/ngày.
- Rollback B: `python3 research/ops/kline_backfill_242.py --restore /home/ubuntu/kline_backfill_bak/kline_bak_<ngày>.jsonl.gz`
  (chỉ trả ô còn đúng giá trị backfill đã ghi; ô ingest đã ghi mới hơn giữ nguyên).

## C. Dựng lại buffer gate rolling từ nến đã sửa (`research/ops/kline_gate_buffer_rebuild.py`, Oracle, KHÔNG ghi 242)
Buffer thật (GRR1 = `GateRatioPersist`: chunk `MAGIC 0x47525231|LEN|CRC32|Snappy(ts>i8, r>f4…)`), đọc 2026-10-10 14:04:
| Đích | File | K | n / tick | first_ts | armed | q_now |
|---|---|---|---|---|---|---|
| live 242 | `/home/chuyennd/java/v_t_m/run/gate_ratio_live.bin` | 16 | 194 656 / 12 164 | 10-01 13:00 | từ 10-08 13:00 | 0,006511 |
| shadow #1 | `/home/ubuntu/shadow_c3/app/run/gate_ratio_live.bin` | 16 | 192 112 / 12 001 | 10-01 13:00 | từ 10-08 13:00 | 0,009113 |
| shadow #2 | `/home/ubuntu/shadow_c3b/app/run/gate_ratio_live.bin` | 24 | 294 720 / 12 276 | 10-01 13:00 | từ 10-08 13:00 | 0,009145 |
Cả 3 chỉ chứa r từ **2026-10-01 13:00** (cấu hình G2; r trước đó đã bị lọc — `TRIM_GATE_BUFFER_242.md`) ⇒ "90 ngày" thực tế =
cùng tập tick đó; không tạo r trước 10-01 13:00 (sp của cấu hình hiện tại cho tick cũ không có ở live). Cách dựng: **giữ nguyên tick
và sp_k (thống kê thứ tự pwin của chính tick live), thay p15 bằng p15 tính lại từ nến đã sửa** (ONNX fold_20 trên 33 feature gate,
port `devexport_202609` — đã kiểm 99,84% p15 trùng tuyệt đối với nhánh 242 trước điểm gãy, audit D4a).
Sai khác khai rõ: sp_k (45 feature/coin) vẫn tính từ nến cũ (bậc 2); tick live bị bỏ (uni<20) không tái tạo.
```bash
cd /home/ubuntu/claude_master/1010/kfix_wt; G=/home/ubuntu/kfix_gate; mkdir -p $G
R=research/ops/kline_gate_buffer_rebuild.py; NOW=$(date +%Y%m%d-%H%M)
# C1 feature gate từ Aerospike 242 SAU backfill (warm-up 48h nội bộ), ~20′
python3 $R feat --arm 242 --lo 20260929 --hi $(date -d tomorrow +%Y%m%d) --wd $G
# C2 sp cache: shadow (local) + live (kéo storage 242 TỪNG NGÀY vào thư mục tạm ≤ 500 MB rồi xoá — Oracle chỉ còn ~2 G)
M=<model net015 như lần dựng buffer #2: docs/audit/DEPLOY_SHADOW2_K24_20261008.md:20>
python3 research/parity/build_gate_buffer_k24.py extract --data /home/ubuntu/shadow_c3/app/storage/data  --model $M --cache $G/cache_s1
python3 research/parity/build_gate_buffer_k24.py extract --data /home/ubuntu/shadow_c3b/app/storage/data --model $M --cache $G/cache_s2
for d in 20261001 20261002 20261003 20261004 20261005 20261006 20261007 20261008 20261009 20261010; do   # + ngày hiện tại
  T=$G/tmp_live; rm -rf $T; mkdir -p $T/predictionSymbol $T/prediction
  scp -r -P 2222 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242:/home/chuyennd/java/v_t_m/storage/data/predictionSymbol/$d $T/predictionSymbol/
  scp -r -P 2222 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242:/home/chuyennd/java/v_t_m/storage/data/prediction/$d $T/prediction/
  python3 research/parity/build_gate_buffer_k24.py extract --data $T --model $M --cache $G/cache_live; rm -rf $T
done
# C3 build + so với file đang chạy (bản sao)
scp -P 2222 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242:/home/chuyennd/java/v_t_m/run/gate_ratio_live.bin $G/live_cur.bin
cp -p /home/ubuntu/shadow_c3/app/run/gate_ratio_live.bin $G/s1_cur.bin; cp -p /home/ubuntu/shadow_c3b/app/run/gate_ratio_live.bin $G/s2_cur.bin
F="$G/kdiv_gate_242_20260929_*.csv.gz"
python3 $R build --feat "$F" --sp cache:$G/cache_live --k 16 --now $NOW --out $G/live_new.bin --ref $G/live_cur.bin --json $G/live_new.json
python3 $R build --feat "$F" --sp cache:$G/cache_s1   --k 16 --now $NOW --out $G/s1_new.bin   --ref $G/s1_cur.bin   --json $G/s1_new.json
python3 $R build --feat "$F" --sp cache:$G/cache_s2   --k 24 --now $NOW --out $G/s2_new.bin   --ref $G/s2_cur.bin   --json $G/s2_new.json
```
PASS C: `ticks_matched/ticks_live ≥ 0,99`; `align_chosen_off_min` giống nhau ở 3 đích; `analyse.armed=true`, `first_ts` = 10-01 13:00;
`q_ratio_new_over_ref_30d_6h.p50` ∈ [0,9; 1,1] (kiểm quá khứ bên dưới: 0,967). Lệch ngoài khoảng ⇒ DỪNG, giữ buffer cũ.
**Kiểm quá khứ đã chạy (2026-10-10, Oracle):** cùng sp HO26 (K24), feature gate 04-01→06-30 từ nến 242 (lệch) vs Vision:
mốc 2026-06-30 23:00 cả hai armed (arm 04-08 23:00), n 3 109 176, q_242 = 0,011087, q_vis = 0,010642; tỉ số q mỗi 6 h 30 ngày cuối
p1 0,950 / p50 0,967 / p99 1,0005; mốc 05-15 tỉ số 1,000 (cửa sổ còn chủ yếu tháng 4 trước gãy) ⇒ logic armed/q đúng, nến sửa làm
q thấp hơn ~3–5% vào T6.

## D. Restart trading (242 + 2 shadow) và chép buffer mới — chỉ khi app ĐÃ DỪNG
Shutdown hook `GateRatioPersistFlush` append r đang chờ vào file khi dừng ⇒ chép SAU khi dừng, TRƯỚC khi start. File mới có
`persistedStart` = 10-01 13:00 (> 7 ngày) ⇒ không seed, không `writeFresh`, armed ngay.
```bash
# 242 (47 vị thế LEGACY không quản lý trong lúc dừng — giữ < 2′)
scp -P 2222 -i /home/ubuntu/.ssh/id_rsa_chuyennd /home/ubuntu/kfix_gate/live_new.bin root@103.157.218.242:/home/chuyennd/java/v_t_m/run/gate_ratio_live.bin.kfix_new
V=/home/chuyennd/java/v_t_m; TS=$(date +%Y%m%d_%H%M)
systemctl stop h242-trading && cp -p $V/run/gate_ratio_live.bin $V/run/gate_ratio_live.bin.bak_kfix_$TS \
  && mv $V/run/gate_ratio_live.bin.kfix_new $V/run/gate_ratio_live.bin && systemctl start h242-trading
grep -a -E 'TICKER-CACHE\] full reload|GATE-RATIO\]' $V/logs/full.log | tail -4     # full reload 1000′; armed, không "seed lịch sử"
# Oracle shadows (cùng mẫu): systemctl stop shadow-c3 → cp -p run/gate_ratio_live.bin …bak_kfix_$TS → cp s1_new.bin → start; shadow-c3b với s2_new.bin
```
Sau D: `python3 research/parity/gate_arm_check.py <file đang chạy> --log logs/full.log` ⇒ PASS (q_t log = q tính lại ±1 ULP).

## E. Cron healthcheck REST (Oracle, mỗi giờ) — `research/ops/kline_rest_check_242.py`
Mỗi lần: 5 phút đã đóng gần nhất (now−7′..now−3′, đã qua pass settle) × 20 symbol (10 totalUsdt lớn nhất + 10 ngẫu nhiên theo giờ),
so REST (limit 10, weight 1/symbol ≈ 20/giờ, gặp 418/429 dừng ngay), cho phép 1 ulp. Lệch > 0 ô ⇒ Telegram qua `tg.env` của
`health_242.sh` (parse `TG_TOKEN=/TG_CHAT=` hoặc `tele-token:/tele-chat-id:`; không in token/chat id). Log `~/claude_master/health242/kline_check.log`.
```bash
cp -p /home/ubuntu/claude_master/1010/kfix_wt/research/ops/kline_rest_check_242.py /home/ubuntu/claude_master/1010/kfix_wt/research/ops/kline_backfill_242.py /home/ubuntu/ops/
python3 /home/ubuntu/ops/kline_rest_check_242.py --dry-run          # PASS sau deploy: "OK cells=100 lech=0"
( crontab -l; echo '17 * * * * /usr/bin/python3 /home/ubuntu/ops/kline_rest_check_242.py >> /home/ubuntu/claude_master/health242/kline_cron.out 2>&1' ) | crontab -
crontab -l | grep kline_rest_check                                  # 1 dòng
```
Đã thử khô 2026-10-10 13:54 (TRƯỚC sửa): `FAIL cells=100 lech=17 (17.00%)` + `WOULD_SEND` (đúng — đang lỗi); `tg.env` parse được (token/chat có).
Mục tiêu sau deploy: 0 lệch trong ≥ 60′ (3 lần chạy tay) rồi mới cài cron. Rollback E: `crontab -l | grep -v kline_rest_check | crontab -`.

## F. ROLLBACK từng bước (ngược thứ tự)
| Bước | Rollback | Dừng |
|---|---|---|
| E cron | `crontab -l \| grep -v kline_rest_check \| crontab -` | 0 |
| D buffer | dừng app → `cp -p run/gate_ratio_live.bin.bak_kfix_<TS> run/gate_ratio_live.bin` → start (r mới append sau đó mất — chấp nhận) | ~1′/app |
| C | không ghi gì ⇒ không cần | 0 |
| B backfill | `kline_backfill_242.py --restore <kline_bak_<ngày>.jsonl.gz>` từng ngày (ô ingest ghi sau không bị đụng) | 0 |
| A1 (nhanh, không đổi jar) | 242: `sed -i 's/^export KLINE_INGEST_MODE=.*/export KLINE_INGEST_MODE=legacy/' conf/env.sh; systemctl stop h242-ingest; systemctl start h242-ingest` ⇒ log `mode=legacy`, `[KLINE V8.1] Chốt nến phút` | ingest 1–2′ |
| A2 (jar cũ) | `systemctl stop h242-ingest; cp -p target/binance-java-sdk-1.2.4.jar.bak_kfix_<TS> target/binance-java-sdk-1.2.4.jar; cp -p conf/env.sh.bak_kfix_<TS> conf/env.sh; systemctl start h242-ingest`; sha = `c00d6052…` | ingest 1–2′ |
Lưu ý: `Utils.reset` (auto-restart 12 h) chép env của JVM cha ⇒ mode giữ nguyên qua restart; đổi mode phải restart qua systemd.

## G. Rủi ro deploy
1. WS `/market` là đường mới của Binance (đường cũ im lặng không báo lỗi) — nếu Binance đổi lại: watchdog 75 s đóng/mở lại liên tục,
   nến vẫn có nhờ REST sớm + settle (chất lượng giây 6 như V8.1). Đổi URL không cần build: `KLINE_WS_BASE`.
2. Pass settle có thể ghi đè bản WS bằng REST nếu replica REST còn trễ ở +30 s (probe: 100% settle từ +8 s, n=435) — theo dõi
   `rewritten_diff`; nếu > 0 thường xuyên, tăng `KLINE_SETTLE_SEC`/`KLINE_SETTLE_MIN_AGE_SEC`.
3. Live vẫn cache nến M đọc ở giây 6 (đề xuất sửa `LiveTickerWindow` đọc lại 2–3 phút cuối — ngoài phạm vi, cần review riêng).
4. Backfill đổi nến lịch sử mà feature/selector/gate đã dùng (HO26 = dữ liệu 242 lệch) ⇒ kết quả nghiên cứu trên `ticker_2026*.bin.gz`
   KHÔNG còn khớp Aerospike sau backfill; export lại = biến thể mới, pre-reg riêng.
5. IP Oracle dùng chung (shadow + script): REST script luôn tuần tự + trần weight + dừng khi 429/418 (sự cố 2026-10-10 13:55: probe
   backfill bản đầu song song 16 luồng limit=1500 ⇒ 48×429 rồi IP Oracle bị ban 418 tới 14:11:58 — đã sửa script).

## H. Deploy jar TRADING — đọc lại nến + thước `[LIVE-KLINE]` (branch `fix/live-ticker-reread`, live 242 + 2 shadow)
Thay đổi: `LiveTickerWindow` mỗi tick đọc lại `KLINE_LIVE_REREAD_MIN` (mặc định 3, 0 = tắt = hành vi cũ) phút ĐÃ nạp gần nhất,
nến khác ⇒ ghi đè cache; `S1RankerLive` đọc lại close giờ vừa nạp 1 lần (≥ 2′ sau mốc giờ); `LiveKlineAudit` đo độ đúng nến lúc
quyết định. Không đổi quyết định/công thức nào (chỉ dữ liệu nến trong cache được sửa cho tick SAU). Làm SAU mục A (ingest ws_settle),
gộp được với lần restart ở mục D (chép buffer cùng lúc). Jar = cùng artifact `target/binance-java-sdk-1.2.4.jar` (chứa cả ingest:
bản này chỉ thêm tên symbol thiếu WS vào dòng `Chốt nến phút` — deploy cho ingest cũng được, không bắt buộc).
```bash
# Oracle: build (sha trong báo cáo KFIX-B)
cd /home/ubuntu/claude_master/1010/kreread_wt && git log --oneline -1 && /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -q package -DskipTests && sha256sum target/binance-java-sdk-1.2.4.jar
scp -P 2222 -i /home/ubuntu/.ssh/id_rsa_chuyennd target/binance-java-sdk-1.2.4.jar root@103.157.218.242:/home/chuyennd/java/v_t_m/target/binance-java-sdk-1.2.4.jar.kreread_new
# 242 (47 vị thế LEGACY không quản lý trong lúc dừng, giữ < 2′)
V=/home/chuyennd/java/v_t_m; TS=$(date +%Y%m%d_%H%M); cd $V
sha256sum target/binance-java-sdk-1.2.4.jar | tee target/sha_before_kreread_$TS.txt; sha256sum target/binance-java-sdk-1.2.4.jar.kreread_new
cp -p target/binance-java-sdk-1.2.4.jar target/binance-java-sdk-1.2.4.jar.bak_kreread_$TS
systemctl stop h242-trading && mv target/binance-java-sdk-1.2.4.jar.kreread_new target/binance-java-sdk-1.2.4.jar && systemctl start h242-trading
# Shadow #1/#2 (Oracle): cùng mẫu trong ~/shadow_c3/app và ~/shadow_c3b/app — backup jar .bak_kreread_$TS, systemctl stop shadow-c3 / shadow-c3b, thay jar, start
```
**Đọc counter** (mỗi 10′, phút chẵn 10; phút đầu tiên được chốt ~3′ sau start):
`grep -a '\[LIVE-KLINE\]' logs/full.log | tail -3` ⇒
`[LIVE-KLINE] reread=3' win{minutes=10 decided_on_unsettled=a/b correct=x% | topK c/d correct=y% | pass e/f correct=z% | reread_overwritten=n s1_close_rewritten=s} cum{…}`.
- `decided_on_unsettled` = số (symbol, phút quyết định) mà nến đọc lúc quyết định (giây 6) ≠ nến đọc lại 1–2 tick sau (≥ 66 s, đã qua
  pass settle +30 s). `correct = 1 − a/b`. `topK` = symbol vào top-K selector của tick; `pass` = symbol không bị gate REJECT (xấp xỉ:
  `createOrderBuyRequest` không thêm vào `predictRejects`; lệnh bị chặn vì lý do khác vẫn tính là pass). `reread_overwritten` = ô cache sửa.
- Kỳ vọng: trước sửa ingest ≈ 85% (14,9% ô sai + 12,5% phút nặn); sau ws_settle ≥ 99%.
**Ngưỡng:** `cum correct` (all) < 99% sau ≥ 6 h, hoặc `win correct` < 97% 3 cửa sổ liên tiếp, hoặc `pass` < 99% sau ≥ 24 h (mẫu nhỏ) ⇒ chẩn đoán:
1. Ingest dùng WS chưa: `grep -a 'Chốt nến phút' collectData/logs/full.log | tail -20` — `ws_final` ≈ số symbol, `thieu_ws`, `rest_som`;
   **tỉ lệ REST fallback giây 4 = rest_som / Total** (> 1% là bất thường); `vd_thieu_ws=[…]` = symbol thiếu WS (tối đa 10).
2. `grep -a '\[KLINE-INGEST\] mode=' … | tail -3` — `ws_conn` < số kết nối, `ws_reconnects` tăng, `ws_late`, `early_failed`, `rewritten_diff(+)`.
3. `grep -a '\[KLINE-WS\]' … | tail` — kết nối đóng/mở lặp (Binance đổi đường ⇒ `KLINE_WS_BASE`).
4. Thời điểm: `research/analysis/kfix_race_read_vs_flush.py` (log trading vs log chốt) — live đọc trước khi chốt ở bao nhiêu % phút.
**Rollback:** nhanh (không đổi jar): thêm `export KLINE_LIVE_REREAD_MIN=0` vào `conf/env.sh` (shadow: Environment của unit) + restart
⇒ hành vi cũ (thước vô nghĩa). Đầy đủ: `systemctl stop h242-trading; cp -p target/binance-java-sdk-1.2.4.jar.bak_kreread_<TS> target/binance-java-sdk-1.2.4.jar; systemctl start h242-trading`
(sha = `sha_before_kreread_<TS>.txt`). Chi phí: +≤ 3 phút đọc Aerospike/tick (~60 KB, vài ms); RAM không đổi.
