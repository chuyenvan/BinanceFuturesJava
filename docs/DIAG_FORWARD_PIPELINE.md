# DIAG_FORWARD_PIPELINE — Chẩn đoán pipeline forward (shadow C3 production) + đề xuất fix

- **Ngày**: 2026-09-24 (giờ VN), branch `module`, HEAD lúc chẩn đoán `26bc95c`.
- **Phạm vi**: **READ-ONLY** trên production. Không start/stop/restart service · không sửa
  `config.properties`/`env.sh` · không ghi vào `/home/ubuntu/shadow_c3/` · **không chạm 242** ·
  không đọc/in key · không `pgrep -af`. Chỉ đọc log + trạng thái + source.
- **Nguồn bằng chứng**: `systemctl {status,cat}`, `journalctl -u`, `ps -p` (theo pidfile),
  `shadow_c3/health.log`, `shadow_c3/app/logs/{full,error}.log`, `health.sh`, `daemon.sh`,
  `shadow_c3/{ledger.csv,ledger_open_positions.csv}`, source Java + `docs/`.
- **Không kiểm chứng được trong task này**: ledger trên **242** ("chỉ có header từ 13/09") —
  nằm ngoài ràng buộc READ-ONLY ("KHÔNG chạm 242"), không kết luận.

---

## 1. KẾT LUẬN NGẮN (TL;DR)

**Tiền đề của task ("shadow chết, production không chạy") KHÔNG còn đúng ở thời điểm 24/09.**
Shadow **ĐANG CHẠY** (systemd `shadow-c3.service`, `enabled`, uptime liên tục từ 22/09 00:00Z),
tick tươi 15 phút, đọc được Aerospike (638–668 symbol/tick), đã nạp đủ model AI + S1 + net015.

Nhưng shadow **KHÔNG sinh lệnh mới nào từ 20/09 05:18 giờ VN** — và đây **KHÔNG phải crash**:
đó là hệ quả **cơ học** của việc jar được thay lúc **20/09 22:06** (bỏ đường gate PHẲNG, bật
**gate động `SIM_GATE_DYN_SCALE=1.70`** = config baseline KEEPLEG0). Từ đó tới nay:

- `[GATE]` in **324/324 chu kỳ với `n_pass=0`** — cổng entry từ chối **100%** ứng viên.
- Trần `p15` (market 15M predicted return) quan sát được trên live = **2.30%**, trong khi ngưỡng
  dễ nhất của cổng = **2.31%–4.11%** ⇒ cổng đóng **sát biên**, không có tick nào lọt.

⇒ "Pipeline forward" **không chết vì hạ tầng**; nó **chết vì nhịp lệnh của baseline KEEPLEG0
quá thấp (~0.64 lệnh/ngày theo DEV)** + gate live đang đóng. Nhịp ~13–20 lệnh/ngày thấy trong
18–20/09 là của **jar cũ chạy gate phẳng** (đường 242 trước L6), **không phải** baseline đang đo.

**Hệ quả quan trọng**: baseline nghiên cứu đã đổi sang KEEPLEG0 (0c2a8a5) ⇒ forward evidence
giờ **rất chậm** (ước lượng §6: ~10 tháng mới có 200 lệnh) và **mỗi ngày chạy = 1 ngày holdout
bị tiêu** (runbook §0.8c). Đây là quyết định **cần owner duyệt trực tiếp**, không phải việc của agent.

---

## 2. TRẠNG THÁI HIỆN TẠI (bằng chứng 24/09 13:0x giờ VN)

| Hạng mục | Giá trị | Bằng chứng |
|---|---|---|
| Service | `active (running)`, `enabled`; `Main PID 1801621` | `systemctl status shadow-c3` |
| Uptime | `01:54:22`, start `Thu 2026-09-24 11:06:46 +07` | `ps -o etime -p 1801621` |
| Nguồn restart | **systemd lên lịch** (`Restart=always`, `RestartSec=15`) + **`ThreadAutoRestartProgram` trong app** ⇒ restart mỗi **~4h01m** (counter 9→16, 23/09 02:58 → 24/09 11:06) | `journalctl -u shadow-c3` |
| Tick cuối | `24/09/2026 13:00:06` (`Start check level change of market for trade`) | `full.log` tail |
| Btc ticker | `size: 1000 20260923 20:20 -> 20260924 12:59` | `full.log` |
| Aerospike | OK: `symbols:649` (638–668/chu kỳ) | `full.log` |
| Model | S1 `s1a2x1_cut20251001.onnx` + net015 `g015x26_f15_cut20251001.onnx` nạp OK | `S1RankerLive`, `Net015ValueLive` |
| Redis | **riêng** `127.0.0.1:7301` (single-node cluster), unit `shadow-c3-redis.service` active 5 ngày, 4.1M | `systemctl status shadow-c3-redis`; unit `Requires=shadow-c3-redis.service` |
| Lệnh sinh ra | `wouldBUY=60` · `wouldCLOSE=54` · `createOrder=0` (đúng: SHADOW_NO_PUSH) | `health.log` mỗi giờ |
| **would-BUY cuối** | **20/09/2026 05:18:32** (tổng 60: 18/09=19, 19/09=31, 20/09=10) | grep histogram `full.log` |
| **would-CLOSE cuối** | **22/09/2026 20:52:31** | grep histogram `full.log` |
| Ledger | `ledger.csv` 65 dòng; exit cuối `AINUSDT` `1790085151282` (≈22/09 20:52) | `ledger.csv` |
| Book đang mở | 9 vị thế giả (APLD, SYN, MYX, G, LSK, B2, PATH, AKE, ONE) | `open_positions.csv` |
| **Dừng lệnh mới** | **~4.3 ngày** (20/09 05:18 → 24/09 13:00) | |
| Đĩa | `/` **186G/194G = 96%**, còn **8.4G** | `df -h` (khớp cảnh báo §0.9 "97%") |
| RAM | `free 249Mi`, `available 16Gi`, swap 0; RSS app 2.4–2.7G / `-Xmx4g` | `free -h`, `ps`, unit ExecStart |
| error.log | **đóng băng từ 21/09 21:17:00** (`errLines=4675` không đổi) | `ls -la app/logs/` |

### 2.1 Bảng UP/DOWN theo ngày (`health.log`)

| Ngày | UP | DOWN |
|---|---|---|
| 06/09 | 40 | 8 (chết 16:00Z) |
| 07/09 – 17/09 | 0 | 24/ngày (**DOWN liên tục 11 ngày**) |
| 18/09 | 12 | 12 (revive ~18:19 local) |
| 19/09 | 24 | 0 |
| 20/09 | 8 | 16 (**DOWN 00:00Z–15:00Z** = cửa sổ thay jar) |
| 21/09 | 21 | 3 |
| 22/09 – 24/09 | 24/ngày | 0 |

Nhận xét: **runbook §0.9 ("shadow ĐÃ TẮT", "`DOWN` liên tục từ 2026-09-06 19:00Z", "L4 KHÔNG
khởi động lại")** là **STALE**. Thực tế: DOWN 06/09 16:00Z → 18/09; **đã chạy lại từ 18/09**
(dưới systemd), và **liên tục UP từ 22/09 00:00Z tới nay**.

---

## 3. NGUYÊN NHÂN GỐC (có trích log)

Trục thời gian quyết định: **mtime jar shadow = 2026-09-20 22:06:03 (+07)**, kèm file
`target/binance-java-sdk-1.2.4.jar.bak_20260920_stubkey`. **Dòng `[GATE]` đầu tiên =
20/09 22:19:00** — tức jar trong ảnh hưởng là jar **TRƯỚC** 20/09 22:06 (xem §3.4).

### 3.1 Từ 20/09 22:19 → nay: cổng entry từ chối 100% (NGUYÊN NHÂN #1)

```
24/09/2026 12:49:02.706 INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: [GATE] scale=1.7000 topk=8 base=0.00800 thr=[0.03545..0.03743] n_cand=8 n_rej=8 n_pass=0
24/09/2026 12:49:02.707 INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: 🔕 [PREDICT fail 8] market[15M:0.99% Risk4H:-1.88%] Min15M:0.80% | ONE(0.304) AKE(0.310) ... G(0.321)
24/09/2026 12:49:02.710 INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: Predict: {"return15M":0.009933233,"riskDrawdown4H":-0.018759906}
```

Thống kê toàn `full.log` (từ 18/09 18:20):

- `[GATE]` tổng = **324 dòng**; `n_pass>0` = **0**.
- `thr` (ngưỡng dễ nhất mỗi tick) phân bố: `min=0.02311..0.02998`, `p50=0.03129..0.03566`,
  `max=0.03724..0.04107` → **ngưỡng 2.31%–4.11%**.
- `market[15M:x%]` (p15 dự đoán, 339 mẫu): `min=0.53`, `p50=0.98`, `p90=1.19`, **`max=2.30`**.
- Công thức (`src/main/java/com/binance/chuyennd/tradecore/EntryGate.java`):
  `thr = MIN_MOMENTUM_15M * max(0.26787, (symbolPred/0.15)*1.2876) * SIM_GATE_DYN_SCALE`
  ⇒ cổng cần `predReturn15M >= thr`. Với `symbolPred≈0.30–0.32`, `base=0.008`, `scale=1.70`:
  `0.008*2.606*1.70 = 0.03545` ✔ khớp log.

⇒ **`n_pass=0` không phải bug**: trần p15 live (2.30%) nằm **dưới sàn ngưỡng** (2.31%). Đúng
như rủi ro đã ghi trước ở `docs/L6_GATE_DYN_FIX.md`: *"gate siết cắt ở 4% trên cùng phân phối p15
⇒ khuếch đại lệch p15 live-vs-offline… **chưa đo được**"*. Nay đã có số: **lệch đủ để đóng cổng**.

### 3.2 Vì sao TRƯỚC 20/09 22:06 lại ra lệnh đều (13–20 lệnh/ngày)

`would-BUY` theo ngày trong `full.log`: 18/09 = 19, 19/09 = 31, 20/09 = 10 ⇒ **~35h ra 60 lệnh
≈ 20 lệnh/ngày**. Con số này **không khớp bất kỳ mức gate nào của baseline**: `RESULT_GATESCALE.md`
§4 cho `T170(1.70)=0.64 lệnh/ngày`, `OFF(1.00)=1.55`, `L80(0.80)=2.37`. Nó khớp **đường gate
PHẲNG** (`RESULT_FLATGATE.md`: flat gate ⇒ `n 2,266 → 21,382`, x9.4) — tức nhánh **bypass
`checkSignalDynamic` khi `SELECTOR_RANK_TOPK>0`**, đúng thứ **L6 GATE-DYN FIX (2026-09-11) đã gỡ**.
⇒ jar cũ (trước 11/09) = **gate phẳng**; jar 20/09 22:06 = **gate động scale 1.70**.
**Nghịch lý cần nói rõ: jar MỚI mới là jar đúng baseline — jar CŨ cho số NHIỀU nhưng VÔ GIÁ TRỊ
đối chiếu baseline.**

### 3.3 Chết 06/09 → 17/09 (11 ngày): mất pid + KHÔNG có supervisor

- `health.log` 07–17/09: **24/24 dòng DOWN mỗi ngày**, `pid=-`, `tick_cuoi` đóng băng
  `06/09/2026 22:00:06` (tick chết lúc 06/09 15:00Z).
- `systemd shadow-c3.service` chỉ được tạo **18/09** (journal "Started …" đầu tiên 18/09;
  `shadow-c3-redis.service` active từ `2026-09-18 18:19:03`). Trước đó chỉ có `bin/daemon.sh`
  + pidfile ⇒ **không ai bật lại** khi tiến trình chết.
- Sự cố đĩa đầy **18/09** ghi trong chính unit file: *"18/09 su co: vong lap exception redis-down
  khong backoff ghi 7GB nohup.out lam day /"* ⇒ đã chuyển `StandardOutput=journal`.
- **Kết luận**: chết 06–17/09 = **(a) thiếu supervisor** + (b) vòng lặp exception/đĩa. **Không
  phải OOM** (health ghi `mem` 15–19G avail suốt giai đoạn DOWN).

### 3.4 Cửa sổ DOWN 20/09 00:00Z–15:00Z (16h) = thay jar

Không có tick/lệnh nào trong cửa sổ này; health UP trở lại đúng 16:00Z, jar mtime 15:06Z.
⇒ DOWN này là **thao tác chủ động** (stop → thay jar `stubkey` → start), không phải crash.

### 3.5 Lỗi Aerospike 242 (đã hết) — 21/09 21:17 local

`error.log` (đóng băng từ 21/09 21:17) — trích 2 dòng nguyên văn:

```
2026-09-21 21:16:55.229 ERROR [pool-2-thread-1] c.b.c.a.DataManagerAerospikeFloatSim: ❌ [AEROSPIKE-FAIL] MẤT DATA chunk start=20260921 19:46 keys=45 sau 4 lần retry
2026-09-21 21:16:56.238 ERROR [pool-3-thread-1] c.b.c.a.DataManagerAerospikeFloatSim: ❌ Error Legacy Scan: Error -8: Cluster is empty
2026-09-21 21:17:00.606 ERROR [pool-8-thread-8] c.b.c.a.DataManagerAerospikeFloatSim: ❌ Error getMetricMap set=oi_feat_lsg bin=f_data SANTOSUSDT: Error -16: com.aerospike.client.AerospikeException$InvalidNode: Error -3: Node not found for partition ticker:1163
```

`Error getMetricMap` = **4,668 lần** trong `full.log` (tới 21/09). **Sau đó KHÔNG còn** — hiện
đọc Aerospike bình thường. ⇒ sự cố **transient** phía cluster 242, **không** phải nguyên nhân dừng lệnh.

### 3.6 `Error get position from binance!` — 7,096 lần, ĐANG DIỄN RA

```
24/09/2026 13:01:10.416 INFO  [pool-3-thread-1] c.b.c.t.BinanceOrderTradingManager: Error get position from binance! 20260924 13:01
  at com.binance.connector.futures.client.impl.um_futures.UMAccount.positionInformation(UMAccount.java:160)
  at com.binance.chuyennd.trading.BinanceOrderTradingManager.updatePositionInfo(BinanceOrderTradingManager.java:395)
```
(JVM là jar `..._stubkey` ⇒ lỗi auth là **cố ý/by-design**; stack chỉ ra `updatePositionInfo`
⇒ `bm.marginRunning = marginTotal` (BinanceOrderTradingManager:435) **không bao giờ được cập nhật** từ
vị thế thật.) **KHÔNG phải nguyên nhân dừng lệnh** — cổng `[GATE]` từ chối **trước** khi tới
budget. Nhưng nó làm **guard `managerBudget` (§0.8b) thành code chết** trên shadow ⇒ **không thể
dùng lỗi này làm tín hiệu**, và cần ghi rõ để người sau không "chẩn đoán nhầm" (đúng cái bẫy §0.8b).

---

## 4. VÌ SAO "PIPELINE FORWARD" HAY CHẾT — ĐỐI CHIẾU (a)–(e)

| Giả thuyết | Kết luận | Bằng chứng |
|---|---|---|
| (a) thiếu supervisor/cron | **ĐÚNG cho 06–17/09**; **KHÔNG còn đúng từ 18/09** | systemd `enabled` + `Restart=always` + `ThreadAutoRestartProgram`; DOWN 11 ngày trước khi có unit |
| (b) tràn RAM/đĩa | **RAM: KHÔNG** (available 16Gi, không swap, RSS 2.4–2.7G/4G). **Đĩa: CÓ, rủi ro hệ thống** — `/` **96%**, 8.4G; đã từng đầy 18/09 (7GB `nohup.out`) | `free -h`, `df -h`, comment unit |
| (c) Redis dùng chung / `blpop` cướp lệnh | **KHÔNG** — Redis riêng `127.0.0.1:7301`, unit riêng, `Requires=` | `systemctl status shadow-c3-redis`; unit |
| (d) jar cũ thiếu class | **KHÔNG** — jar shadow **có đủ** class (`LiveBuildMap`, `GateValueSource`, `ConcCapLiveGuard`, `Net015ValueLive`, `S1RankerLive`, `EntryGate`, `LiveProfileC3`). Nhưng jar **LỆCH 4 ngày** so HEAD (`e3bf2d2` vs `c2b0c96`) ⇒ **rủi ro lệch code**, chưa phải nguyên nhân | `unzip -l` hai jar; sha/mtime §7 |
| **(e) khác (ĐÚNG)** | **Gate động scale 1.70 đóng sát biên** (`n_pass=0`, 324/324) + **nhịp baseline KEEPLEG0 thấp (~0.64 lệnh/ngày)** + **jar đổi 20/09 22:06 đổi hẳn cơ chế gate** | §3.1, §3.2, `RESULT_GATESCALE.md` §4 |

**Phân loại lỗi cụ thể đã LOẠI TRỪ**: OOM (không có bằng chứng, không swap, health ghi RAM dư) ·
Aerospike (đã hết 21/09) · `managerBudget` null (không tới được vì gate chặn trước; guard còn bị
vô hiệu bởi stub key) · crash/exception làm thoát tiến trình (không có `Failed with result` /
`Main process exited` bất thường; mọi restart là do `ThreadAutoRestartProgram`/systemd theo lịch).

---

## 5. ĐỀ XUẤT FIX TỪNG BƯỚC (KHÔNG tự chạy)

> ⚠️ Trước mọi bước: **đã chạy rồi thì không "bật lại"** — shadow đang chạy. Bước nào cần
> restart/redeploy ⇒ **dừng ở đây, xin owner duyệt** (§7).

### B0 — Đo lại mức đóng cổng bằng chứng cứ đã có (rẻ nhất, không side-effect)

```bash
# read-only, không sửa gì
grep -a "\[GATE\]"  /home/ubuntu/shadow_c3/app/logs/full.log | tail -1
grep -ac "n_pass=0" /home/ubuntu/shadow_c3/app/logs/full.log
grep -ao "market\[15M:[-0-9.]*%" /home/ubuntu/shadow_c3/app/logs/full.log | sed 's/.*15M://;s/%//' | sort -n | tail -1
```
**Tiêu chí xong**: có (a) số chu kỳ `n_pass=0` liên tiếp, (b) `max p15` vs `min thr`.
→ Nếu `max p15 < min thr` liên tục ≥ 7 ngày: **cổng đóng do lệch phân phối p15**, xem B5.

### B1 — Watchdog phát hiện "cổng đóng im lặng" (không có nó thì không ai biết shadow "chạy mà không sinh lệnh")

Sửa **duy nhất `shadow_c3/bin/health.sh`** (thêm 3 dòng, giữ nguyên phần còn lại):
```bash
# trong health.sh, trước dòng printf:
NP=$(grep -a "\[GATE\]" "$L" 2>/dev/null | tail -144 | grep -ac "n_pass=0" || true)   # ~24h = 96-144 chu kỳ
GATE=$(grep -a "\[GATE\]" "$L" 2>/dev/null | grep -av "n_pass=0" | tail -1 | cut -c1-19)
```
và ghi thêm `gatePassCuoi="%s"` vào dòng `printf` + health.log.
**Tiêu chí xong**: `health.log` có cột `gatePassCuoi`; mỗi giờ chứng minh được cổng có mở hay không.
*(Đây là sửa file cấu hình vận hành ⇒ cần owner duyệt; nếu không duyệt thì B0 bằng tay 1 lần/tuần.)*

### B2 — Làm jar shadow == HEAD (đóng rủi ro lệch code) — **cần owner duyệt, đổi số đối chứng**

```bash
# (không chạy trong task này)
cd /home/ubuntu/src/BinanceFuturesJava && mvn -o -q -DskipTests package
sha256sum target/binance-java-sdk-1.2.4.jar        # so với e3bf2d21cdce72cc... đang chạy
# nếu khác: backup jar cũ rồi mới copy, và GHI MỐC THỜI GIAN ĐỔI ĐỒNG CHỨNG vào doc
```
**Lưu ý bắt buộc**: đổi jar = **đổi đồng chứng**, phải (i) ghi mốc thời gian + sha vào
`DECISION_*`/runbook, (ii) chấp nhận book forward bị chia đoạn. Lệch 4 ngày hiện tại **có thể
không đổi hành vi** (env.sh đã đặt tường minh `CONC_CAP_PERCOIN=15%`, `SIM_GATE_DYN_SCALE=1.70`,
`DCA_GRID_*=1,1,1,1 / 6.0` — **khớp 100%** `profiles/t170_flat_keepleg0.properties`), nhưng
**phải chứng minh bằng parity**, không suy đoán.

### B3 — Ghi rõ trạng thái stub key (đừng để người sau chẩn đoán nhầm)

Thêm mục vào `docs/PLAN_SHADOW_T170_PARALLEL.md`/runbook: **`Error get position from binance!`
là BY-DESIGN trên shadow** (jar stub key, paper mode không push). **Không** dùng nó làm tín hiệu
hỏng. **Không** đặt key vào chat/log — nếu sau này cần key thật thì dùng **host-owned masked
entry**, không qua transcript.

### B4 — Đĩa 96% (rủi ro hệ thống, độc lập với gate) — **cần owner duyệt**

```bash
df -h /                                        # 186G/194G, 8.4G
du -sh /home/ubuntu/shadow_c3/app/logs /home/ubuntu/*/logs 2>/dev/null
journalctl --disk-usage
# đề xuất (KHÔNG chạy): journalctl --vacuum-size=500M
# đề xuất (KHÔNG chạy): chuyển các log cũ > 7 ngày sang archive, KHÔNG xoá thẳng
```
**Tiêu chí xong**: `/` < 90% và có ≥ 15G dự phòng. Dùng `trash`/archive thay vì `rm`.

### B5 — Đo lệch p15 live-vs-offline (điều kiện TIÊN QUYẾT để forward có nghĩa)

Theo `docs/L6_GATE_DYN_FIX.md` ("L4 mục 7 điểm 8, chưa đo được"): trích `market[15M:..]` + `thr`
từ `[GATE]` (đã có B0) rồi so phân phối với p15 nhánh sim cùng cửa sổ.
**Tiêu chí xong**: kết luận CÓ/KHÔNG "p15 live đủ đuôi để cổng 1.70 mở với tần suất ~0.64/ngày".
→ Nếu **KHÔNG**, chạy tiếp shadow **không tạo ra bằng chứng** (chỉ tiêu holdout) ⇒ phải chốt lại
câu hỏi nghiên cứu trước khi chạy tiếp.

### B6 — Cập nhật runbook (tài liệu đang SAI, gây chẩn đoán nhầm)

`docs/AGENT_RUNBOOK.md`:
- §0.9: bỏ "**Shadow C3 Oracle — ĐÃ TẮT**… `DOWN` liên tục từ 2026-09-06 19:00Z… **L4 KHÔNG khởi
  động lại**" → thay bằng: **đang chạy dưới systemd `shadow-c3.service` (enabled) từ 18/09**;
  DOWN 06/09 16:00Z→18/09 (thiếu supervisor); liên tục UP từ 22/09 00:00Z; jar shadow **rời HEAD**.
- §0.8(b): ghi thêm rằng guard `managerBudget` **bị vô hiệu trên shadow** bởi stub key
  (`Error get position from binance!` 7,096 lần) ⇒ đừng dùng nó làm tín hiệu.
**Tiêu chí xong**: `grep -n "DA TAT" docs/AGENT_RUNBOOK.md` không còn mô tả sai trạng thái.

### B7 — KHÔNG đề xuất đổi gate

Đổi `SIM_GATE_DYN_SCALE` (vd 1.70→1.00) **sẽ đổi câu hỏi nghiên cứu** và đã có kết quả
(`RESULT_GATESCALE.md`: mọi scale ≠ 1.70 đều FAIL/NULL trên nền cũ). Muốn nhiều lệnh hơn thì phải
**mở một vòng mới có pre-reg trên baseline KEEPLEG0**, không "vặn gate" trên shadow.

---

## 6. ƯỚC LƯỢNG: BAO LÂU ĐỦ BẰNG CHỨNG FORWARD?

**Nhịp lệnh của baseline đang chạy** (`RESULT_GATESCALE.md` §4, đo trên 1,460 ngày MTM):

| gate scale | lệnh/ngày | lệnh/năm |
|---|---|---|
| 1.70 (**KEEPLEG0/production hiện tại**) | **0.64** | ~234 |
| 1.00 | 1.55 | ~566 |
| 0.80 | 2.37 | ~865 |

**Chuẩn bằng chứng** (`AGENT_RUNBOOK.md` §3): tiêu chí là **RATE trên hàng trăm trade** +
"**≥ 2 rate ngoài CI**" (bootstrap block-72h, 2000 rep) ⇒ **sàn thực dụng ≈ 200–300 lệnh**.

| Mốc | Thời gian ở 0.64 lệnh/ngày |
|---|---|
| 100 lệnh | **~156 ngày (~5,2 tháng)** |
| **200 lệnh** | **~313 ngày (~10,4 tháng)** |
| 300 lệnh | ~469 ngày (~15,6 tháng) |

**Chi phí**: mỗi ngày chạy = **1 ngày holdout bị tiêu** (runbook §0.8c; đã tiêu ~6 ngày kể từ
18/09). ⇒ **~10 tháng chạy ≈ 10 tháng holdout** để đổi lấy 1 lần đọc rate đầu tiên.

**Cảnh báo làm ước lượng này có thể VÔ NGHĨA**: hiện `max p15 = 2.30% < min thr = 2.31%` ⇒ nhịp
thực tế **có thể ≈ 0** chứ không phải 0.64/ngày. **Phải làm B0/B5 trước**; nếu p15 live bị nén
so với offline thì dù chạy 10 tháng vẫn **0 lệnh**. **Điều kiện tiên quyết không phải "thời gian"
mà là "đo lệch p15".**

---

## 7. ⛔ CHỜ OWNER DUYỆT (bắt buộc, không tự làm)

1. **Shadow có tiếp tục chạy?** Mỗi ngày = 1 ngày `holdout` bị tiêu (§0.8c); và ở nhịp 0.64
   lệnh/ngày thì **~10 tháng** mới có 200 lệnh ⇒ owner phải chấp nhận chi phí holdout này.
   *(Không tắt/bật gì trong task này — chỉ báo cáo.)*
2. **Có cho phép rebuild + redeploy jar shadow == HEAD `26bc95c`?** (B2) — đổi **đồng chứng**,
   phải ghi mốc + sha; hiện shadow đang chạy jar **2026-09-20 22:06**, sha **`e3bf2d21cdce72cc…`**,
   HEAD jar **`c2b0c9634526c265…`** (lệch 4 ngày commit, gồm `26bc95c` bật mặc định CONC_CAP và
   `7d85426` đổi cách đo maxDD).
3. **Có cho phép sửa `shadow_c3/bin/health.sh`** thêm watchdog cổng (B1)?
4. **Có cho phép dọn đĩa** (`journalctl --vacuum-size`, archive log cũ) khi `/` = **96%** (B4)?
5. **Có cho phép sửa `docs/AGENT_RUNBOOK.md` §0.8(b) + §0.9** (đang mô tả SAI trạng thái)? (B6)
6. **Sau này**: có `HOLDOUT_UNSEAL` cho đoạn đã trôi qua **18/09 → 24/09** (và các ngày tới) —
   cần owner duyệt trực tiếp, đúng thủ tục, không tự làm.

**Không có hạng mục nào ở trên được agent thực thi.** Task này: chỉ đọc, chỉ ghi 1 file doc, commit.

---

## 8. PHỤ LỤC — SỐ LIỆU THÔ

- `systemctl cat shadow-c3`: `Restart=always`, `RestartSec=15`, `Requires=shadow-c3-redis.service`,
  `StandardOutput=journal` (lý do: "18/09… 7GB nohup.out lam day /").
- `ExecStart`: `java -server -Xms1g -Xmx4g -Duser.timezone=Asia/Ho_Chi_Minh -cp target/binance-java-sdk-1.2.4.jar …`
- Restart counter: 9 (23/09 06:59) → **16 (24/09 11:06)**, mỗi lần cách **~4h01m**.
- `[GATE]` 324 dòng, `n_pass>0` = 0. `PREDICT fail` = 339 dòng.
- `Error get position from binance!` = **7,096**. `Error getMetricMap` = **4,668** (dừng sau 21/09 21:17).
- `would-BUY` theo ngày: 18/09=19, 19/09=31, 20/09=10 (**tổng 60**, dòng cuối 20/09 05:18:32).
- `would-CLOSE` theo ngày: 18/09=10, 19/09=28, 20/09=9, 21/09=5, 22/09=2 (**tổng 54**, dòng cuối 22/09 20:52:31).
- `ledger.csv` = 65 dòng dữ liệu; exit cuối `AINUSDT` ts `1790085151282`.
- Cấu hình shadow **khớp 100%** `profiles/t170_flat_keepleg0.properties` (đối chiếu từng key):
  `SELECTOR_RANK_TOPK=8`, `SELECTOR_ONLY_ENTRY=0`, `SIM_GATE_DYN_SCALE=1.70`, `DCA_GRID_WEIGHTS=1,1,1,1`,
  `DCA_GRID_SCALE=6.0`, `SIM_RATE_PROFIT_STOP_MARKET=0.07`, `SIM_TS_GIVEBACK=1`, `TS_GIVEBACK_RATIO=0.5`,
  `SIM_LOSER_TIME_STOP_HOURS=168`, `SIM_BREAKER_MODE=OFF`, `CONC_CAP_PERCOIN_*=true/0.15`,
  `CAPITAL_START=35000`/`PAPER_EQUITY=35000`, `SIM_MIN_MOMENTUM_15M=0.008`.
- Cảnh báo còn treo (`DECISION_BASELINE_KEEPLEG0.md` + §0.8a): 242/shadow đường LIVE tính
  `symbolPred` bằng model riêng (`Funding_Classifier_Final.onnx`), **không** đọc
  `WFO_FUNDING_PRED_DIR` (bins `predwf_map_s1a2` là artifact OFFLINE). Shadow log cho thấy selector
  **net015-mapped** (`Net015ValueLive` + `S1RankerLive`, model `/home/ubuntu/g3x26/`, `/home/ubuntu/s1_model/`)
  ⇒ **vẫn cần chứng minh parity symbolPred live-vs-offline**, nếu không thì "dán nhãn C3" vẫn là
  **số liệu vô giá trị** (đúng cảnh báo §0.8a). **Chưa kiểm chứng trong task này.**
