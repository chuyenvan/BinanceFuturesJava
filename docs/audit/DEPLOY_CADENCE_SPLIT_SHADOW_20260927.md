# AUDIT — DEPLOY TÁCH NHỊP LÊN SHADOW (Oracle) — 2026-09-27

Phạm vi được duyệt (owner 27/09 07:32): *"Ok vẫn shadow triển khai đi. Bao giờ golive tôi làm"*
⇒ Chỉ deploy lên **SHADOW** (`shadow-c3.service`, paper). **KHÔNG** chạm 242 · **KHÔNG** đổi gate · **KHÔNG** chạm ONNX/`NUM_FEATURES` · **KHÔNG** push git.
Bản sửa deploy: commit `53c80a1` (branch `module`, không push), jar `target/binance-java-sdk-1.2.4.jar` sha256 `640398c8ed05dc86249a695285166414554fb8ad749bd0b41c38a184105783e3`.

> **KẾT LUẬN: ĐÃ ROLLBACK.** Bản deploy (jar mới + `MARKET_SCAN_MIN=1`) **KHÔNG đạt mục tiêu thiết kế** và **làm xấu nhịp SELECTOR** → đã khôi phục nguyên trạng trong ~9 phút. Xem §3 "PHÁT HIỆN GỐC".
>
> **THÊM (due diligence §1b):** jar mới còn **gộp 11 commit nhóm (iii) ngoài patch tách nhịp** (gate/entry/exit/sizing) ⇒ theo quy tắc **lẽ ra KHÔNG được deploy** ngay từ đầu; verdict **DỪNG**. Do bản deploy đã ROLLBACK nên **hiện không có thay đổi gộp nào đang chạy**.

---

## 0. BUỘC 0 — KHÓA ĐĨA

| | Trước | Sau retention |
|---|---|---|
| `df -h /` | 194G size · 179G used · **15G avail · 93%** | 15G avail · 93% |
| `df -i /` | 25.9M inode · 427104 used · 2% | 426987 · 2% |

**Không chạm HARD STOP** (HARD STOP = free < 10G; thực tế 15G).

Đo `storage/data/` (app shadow: `/home/ubuntu/shadow_c3/app/storage/data/`):
- `predictionSymbol` 74M / 1514 file (11 thư mục ngày) — ghi mỗi tick (`<ts>` + `<ts>.features`).
- `prediction` 6.1M / 1512 file; `order` 380K.

**Tốc độ tăng hiện tại** (nhịp 15'): 22–26/09 đều **96 tick/ngày**, riêng `predictionSymbol` ≈ **9–10 MB/ngày** (~104 KB/tick).
⇒ nếu bật nhịp 1' (1440 tick/ngày) thì ≈ **150 MB/ngày ⇒ ~4,4 GB/30 ngày** (vượt mục tiêu ≤2 GB).
⇒ Retention 12 ngày ⇒ ổn định ≈ **1,8 GB** (≈1,8 GB/30 ngày, đạt mục tiêu).

**Đã áp:** thêm block retention 12 ngày vào `bin/health.sh` (backup `health.sh.bak_20260927`, `bash -n` PASS, test logic trên fixture PASS), và xoá thủ công thư mục ngày cũ hơn 12 ngày:

- Đã xoá: `prediction/20260906` (236 KB) + `predictionSymbol/20260906` (2668 KB) = **116 file / 2904 KB (~2,9 MB)**. Chỉ xoá thư mục NGÀY trong `prediction`/`predictionSymbol` (derived); không xoá gì khác (giữ `order/`).

> ⚠️ **Do đã rollback deploy (xem §3), block retention trong `health.sh` cũng đã được HOÀN NGUYÊN** (`health.sh` về sha `7bf10654…`), vì lý do 15× không còn. File đã xoá (2,9 MB) không khôi phục lại (dữ liệu derived cũ). Đĩa vẫn ở 93% — đây là **rủi ro sẵn có**, độc lập với task này.

---

## 1. BUỘC 1 — BACKUP (trước mọi thay đổi)

| Đối tượng | sha256 | Backup |
|---|---|---|
| jar đang chạy | `e3bf2d21cdce72cc81c72f0d917c15642afba28348beb316b94b651f6a6b79d0` (= build 20/09 22:06) | `target/binance-java-sdk-1.2.4.jar.bak_20260927` |
| `conf/env.sh` | `cfe2c8fdc812d22797bbdaa62bb899a7fd9acffc28fc459f26eecc8b6e7992c6` | `conf/env.sh.bak_20260927` |
| `bin/health.sh` | `7bf106544baa19ff3dafb89b2eaa5a6e353db3b02a5637a405c015025259b491` | `bin/health.sh.bak_20260927` |
| `config.properties` (**không sửa**) | `d8d5e87a4964ba292703dc03d6d544d494b009db1613685333d7ffd36b0b1b28` | — |
| ONNX `s1a2x1_cut20251001.onnx` | md5 `afaa2828a6d8c73e4b32c3f9a6d0c79b` | (baseline) |

- **TRADING_PROFILE**: env **KHÔNG đặt** ⇒ instance này đọc tham số từ **env** (`conf/env.sh`, `set -a`). Vì vậy `MARKET_SCAN_MIN` phải đặt trong `conf/env.sh`, không phải profile. (Đúng như `PLAN_LIVE_CADENCE_SPLIT.md` §4 cảnh báo: không có profile ⇒ đọc env.)
- `systemctl show shadow-c3 -p MainPID,ExecMainStartTimestamp`: **MainPID=1977283 · 2026-09-27 07:23:47** · `is-active`=**active**.
- Ghi chú: shadow đã tự restart lúc 03:22:47 và 07:23:47 (do `ThreadAutoRestartProgram` nội bộ app; restart counter 33) — **không phải** do task này.

---

## 1b. DUE DILIGENCE (bổ sung: jar gộp nhiều thay đổi 20/09 → nay)

**Bối cảnh:** jar mới build từ HEAD `3f6993b` + patch `53c80a1`, còn jar đang chạy là build **20/09 22:06** (`e3bf2d21…`). ⇒ Deploy mang theo **toàn bộ thay đổi `src/main` từ mốc 20/09 → nay**, không chỉ patch tách nhịp.

**(1) Điểm build jar đang chạy:** `mtime jar shadow = 2026-09-20 22:06:03 (+07)` (nguồn `docs/diag/DIAG_FORWARD_PIPELINE.md:81`). Commit gần nhất ≤ mốc = **`38691b6` (2026-09-20 19:28:00)**; `git log --since=2026-09-20 19:28:01 --until=2026-09-20 22:06:00` = **rỗng** ⇒ không có commit nào giữa mốc và thời điểm build.
> ⚠️ Không thể loại trừ jar được build kèm thay đổi **working tree chưa commit** ⇒ mốc là **suy đoán tốt nhất**, không phải bằng chứng tuyệt đối.

**(2) `git diff --stat 38691b6..53c80a1 -- src/main` (nguyên văn):**
```
 .../aerospike/DataManagerAerospikeFloatSim.java    |   2 +-
 .../chuyennd/ai_ml/onnx/entry/AIRejectFilter.java  |   4 +-
 .../chuyennd/ai_ml/wfo/framework/WfoDataset.java   |   2 +-
 .../chuyennd/bigchange/test/TraceOrderDone.java    |  44 ++++
 .../chuyennd/research/BudgetManagerSimple.java     |   4 +-
 .../binance/chuyennd/research/DumpBtcDaily.java    |   2 +-
 .../research/ExportSelectorPred1mToAerospike.java  |   2 +-
 .../chuyennd/research/OrderTargetInfoTest.java     |  25 +-
 .../SimulatorMarketLevelTicker1MStopLoss.java      | 147 ++++++++---
 .../binance/chuyennd/research/TickDecisionLog.java |   4 +-
 .../chuyennd/research/l4/L4ReplayHarness.java      |   2 +-
 .../binance/chuyennd/tradecore/BdSelection.java    |   2 +-
 .../binance/chuyennd/tradecore/BdSizeAdapt.java    |   2 +-
 .../java/com/binance/chuyennd/tradecore/Cfg.java   |   4 +-
 .../chuyennd/tradecore/ConcCapLiveGuard.java       |   4 +-
 .../com/binance/chuyennd/tradecore/Configs.java    | 214 ++++++++++++++--
 .../binance/chuyennd/tradecore/DcaProcessor.java   |   2 +-
 .../com/binance/chuyennd/tradecore/DcaUtils.java   |   2 +-
 .../binance/chuyennd/tradecore/DumpConfig.java     |   2 +-
 .../com/binance/chuyennd/tradecore/EntryGate.java  | 131 +++++++++-
 .../binance/chuyennd/tradecore/PacingSizing.java   | 206 ++++++++++++++++
 .../binance/chuyennd/tradecore/PreArmSlUtils.java  |   2 +-
 .../binance/chuyennd/tradecore/PumpDumpFilter.java |   2 +-
 .../com/binance/chuyennd/tradecore/RegimeSchedule.java |  21 +-
 .../com/binance/chuyennd/tradecore/TickWeakBlock.java | 271 +++++++++++++++++++++
 .../com/binance/chuyennd/tradecore/TradeUtils.java |  47 ++++
 .../chuyennd/tradecore/VolTargetSizing.java        |   4 +-
 .../tradecore/selector/GateValueSource.java        |   2 +-
 .../chuyennd/tradecore/selector/LiveBuildMap.java  |   2 +-
 .../chuyennd/tradecore/selector/LiveProfileC3.java |   2 +-
 .../chuyennd/tradecore/selector/S1RankerLive.java  |   2 +-
 .../tradecore/selector/SelectorTier1Source.java    |   2 +-
 .../chuyennd/tradecore/selector/ShadowBookC3.java  |   6 +-
 .../tradecore/selector/TrailHingeSource.java       |   2 +-
 .../trading/DetectEntrySignal2TradeNormal.java     |  67 ++++-
 35 files changed, 1126 insertions(+), 113 deletions(-)
```

**(2b) 13 commit trong mốc..HEAD (chỉ `src/main`):** `53c80a1`, `3b6c6e9`, `fec652e`, `37fd502`, `dca07ce`, `a7b7725`, `4d8d9c5`, `079a897`, `2cb7f78`, `a224e88`, `ba3d7ba`, `50f7ff0`, `0ca2c62`.

**(3) Phân loại:**
- **(i) CHỈ patch tách nhịp:** `53c80a1` (duy nhất thay đổi trong `DetectEntrySignal2TradeNormal.java` ngoài `37fd502`).
- **(ii) An toàn:** `37fd502` chore(docs) (chỉ tổ chức lại `docs/`).
- **(iii) ĐỤNG ĐƯỜNG LIVE CÓ RỦI RO — 11 commit, NGOÀI patch:** `fec652e` + `ba3d7ba` (EntryGate / gate), `3b6c6e9` (phạm vi `SIM_ENTRY_SAMPLE_MIN` — entry-leg), `dca07ce` (TS_PEAK_MODE — exit/trail, TradeUtils), `a7b7725` (TS_LADDER — trail, TradeUtils), `079a897`+`4d8d9c5` (TickWeakBlock — chặn entry), `2cb7f78` (SELECTOR_LEG_CUT — selector entry), `a224e88` (RegimeSchedule gate liên tục), `50f7ff0`+`0ca2c62` (PacingSizing — sizing/BIG_DOWN). Thêm **2 class MỚI**: `PacingSizing.java`, `TickWeakBlock.java`.
- Ghi chú: phần lớn key mới **default OFF/byte-identical** (`SIM_GATE_P15_Q` chỉ nhận khi `0<q<1`; `SIM_TICK_BLOCK_IND` default `""`; `SELECTOR_LEG_CUT` default `"1".equals(...)` ⇒ false; `SIM_REGIME_GATE_VALUE_COL` default `-1`; `SIZE_PACING_MODE` default `OFF ⇒ ACTIVE=false`; `PacingSizing`/`TickWeakBlock` **chỉ được gọi từ `SimulatorMarketLevelTicker1MStopLoss` — KHÔNG có call-site trong đường live**). NHƯNG không thể chứng minh byte-identical cho toàn bộ 35 file (vài file khác như `DcaProcessor`, `ShadowBookC3`, `ConcCapLiveGuard`, `LiveProfileC3` cũng bị sửa) trong phạm vi này.

**(4) 🛑 KẾT LUẬN 1b: DỪNG — KHÔNG deploy gộp.** Có **nhóm (iii) ngoài patch tách nhịp** ⇒ theo đúng quy tắc: **không deploy**, báo owner quyết. Deploy gộp nhiều thay đổi sẽ **không quy được nguyên nhân** khi có sự cố, phá nguyên tắc "1 đợt 1 thay đổi" của `PLAN_LIVE_CADENCE_SPLIT.md` §7.
> Thực tế: bản deploy (mục 2–4) **đã được chạy rồi ROLLBACK trước khi nhận được yêu cầu 1b**, nên **hiện KHÔNG có thay đổi gộp nào đang chạy**. Nếu muốn thử lại nhịp, cách đúng là **build một jar CHỈ chứa `53c80a1`** (cherry-pick patch tách nhịp lên đúng mốc `38691b6`) rồi mới deploy.

---

## 2. BUỘC 2 — DEPLOY (chỉ shadow)

1. Copy jar mới vào đúng chỗ unit dùng (`ExecStart=/home/ubuntu/shadow_c3/app/bin/run_foreground.sh` → `cd app` → `bin/start.sh` → `-cp target/binance-java-sdk-1.2.4.jar`):
   `target/binance-java-sdk-1.2.4.jar`: `e3bf2d21…` → **`640398c8ed05…`** (jar cũ giữ ở `.bak_20260927`). Kiểm: jar chứa chuỗi `CADENCE-SPLIT` ✓.
2. Thêm `export MARKET_SCAN_MIN=1` vào `conf/env.sh` (có comment rollback). `env.sh`: `cfe2c8fd…` → `5fbc8c54…`. **Không** sửa `config.properties`.
3. `sudo systemctl restart shadow-c3` lúc **07:37:08** → `is-active`=active, MainPID **1980739**.
4. Service lên trong <1 phút (không cần rollback vì lỗi khởi động).

Log khởi động: `[CADENCE-SPLIT] MARKET_SCAN_MIN=1 => MARKET-LEVEL(BIG_DOWN/DCA) quet 1 PHUT, SELECTOR luon 15'` (07:37:15) ✓.

**KHÔNG chạm 242.**

---

## 3. BUỘC 3 — XÁC MINH (và PHÁT HIỆN GỐC → ROLLBACK)

Xác minh chạy từ 07:37:08 → 07:45:54 (~8m47s):

- `is-active`=active ✓ · `error.log` **không đổi** (4675 dòng, mtime 2026-09-21 21:17) ✓ · **0** dòng ERROR/Exception mới trong `full.log` ✓ · ONNX md5 không đổi · RSS ~2,6G, CPU ~20% (4 core) — **I/O-bound**, không phải CPU.
- **PHÁT HIỆN GỐC (không đạt mục tiêu):**
  - Mỗi lượt `checkMarketLevelChange2Trade()` mất **~2m48s** (đo: start 07:38:06 → 07:40:55 → 07:43:42, cách nhau 2m49 / 2m47). Cùng độ dài với các lượt 15' trước đó (06:00:06→06:02:53, 07:30:06→07:33:30).
  - `executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER)` với `NUMBER_THREAD_ORDER_MANAGER=1` (config.properties:18) ⇒ **pool 1 thread**; và chỉ dùng tại `DetectEntrySignal2TradeNormal.java:140` ⇒ mọi tick **xếp hàng tuần tự**.
  - Nộp mới **1 tick/phút** nhưng thực thi **1 tick/2,8 phút** ⇒ **hàng đợi phình vô hạn** (~+0,64 tick/phút ⇒ ~925 tick/ngày). `Start check` chỉ tăng ~21/giờ thay vì 60/giờ ⇒ **KHÔNG thể đạt 1440/ngày**.
  - Vì FIFO và giữa 2 tick SELECTOR luôn có ~15 tick MARKET, nhịp thực thi SELECTOR bị giãn thành **~15 × 2,8 ≈ 42 phút** (thay vì 15') ⇒ mục tiêu "SELECTOR luôn 15'" **bị phá vỡ**. Độ trễ pha tăng vô hạn theo thời gian.
- Do đó `[CADENCE-SPLIT]` có xuất hiện (fast-path hoạt động) nhưng **nhịp 1' không khả thi**; tiêu chí xác minh #2 (1440/ngày) và #4 (`[GATE]` đúng mốc 15') **FAIL**. `[GATE]` chưa kịp xuất hiện ở mốc nào sau deploy (tick 07:45 còn kẹt trong queue).
- Ghi chú hiện trạng trước deploy (không phải do task): watchdog `health.log` đã báo `ALERT: GATE_DONG_BANG gatePassCuoi=NEVER gateRejStreak=583` (gate chưa từng PASS) — **trạng thái sẵn có**, đợt A không dự kiến đổi gate value.

⇒ Kết luận: cần **thiết kế lại phần thực thi** (ví dụ pool >1 có kiểm soát đồng thời, hoặc chuyển phần prep nặng sang một đường riêng) **trước khi** bật nhịp 1'. Không nằm trong phạm vi được duyệt → **ROLLBACK**.

---

## 4. BUỘC 4 — ROLLBACK (đã chạy, thành công)

Lệnh rollback (nguyên văn, chỉ dùng khi cần):

```bash
# 1) khôi phục jar cũ + bỏ key + khôi phục health.sh
cp -p /home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar.bak_20260927 \
      /home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar
cp -p /home/ubuntu/shadow_c3/app/conf/env.sh.bak_20260927 \
      /home/ubuntu/shadow_c3/app/conf/env.sh          # (hoặc sửa MARKET_SCAN_MIN=0 / bỏ dòng)
cp -p /home/ubuntu/shadow_c3/bin/health.sh.bak_20260927 /home/ubuntu/shadow_c3/bin/health.sh
bash -n /home/ubuntu/shadow_c3/bin/health.sh
# 2) restart
sudo systemctl restart shadow-c3
# 3) xác minh về trạng thái cũ
sha256sum /home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar   # phải = e3bf2d21…
grep -c "MARKET_SCAN_MIN" /home/ubuntu/shadow_c3/app/conf/env.sh         # phải = 0
systemctl is-active shadow-c3
```

Đã thực thi lúc **07:45:54**: jar về `e3bf2d21…`, `env.sh` về `cfe2c8fd…`, `health.sh` về `7bf10654…`, `MARKET_SCAN_MIN` không còn, MainPID **1982408**, `is-active`=active, `error.log` vẫn 4675 dòng.
**Xác minh nhịp cũ (07:46 → 08:01):** **0** tick `Start check level change` trong 15 phút (nếu key còn bật 1' sẽ có ~15 tick); tick duy nhất xuất hiện tại **08:00:06** đúng mốc lưới 15' ✓; `[CADENCE-SPLIT]` **0** dòng sau rollback ✓; jar `e3bf2d21…` ✓; `MARKET_SCAN_MIN` count=0 ✓; `df /` 15G · `error.log` 4675 ✓.

---

## 5. 242 — XÁC NHẬN KHÔNG CHẠM

Chỉ ĐỌC (không thao tác): `ssh -p 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242` → hostname `3stech.vn`, java pid **21616** etime **8h31m** (đang chạy `target/binance-java-sdk-1.2.4.jar`), **không đổi**. Từ phía task này **không có lệnh nào gửi tới 242**.

---

## 6. PHẦN KHÔNG LÀM ĐƯỢC / GAP

- Nhịp 1' cho MARKET-LEVEL: **không khả thi** với pool 1 thread + prep ~2m48s (đã rollback).
- `systemctl is-active v_t_m` trên 242 trả `unknown` (tên unit khác) — chỉ xác nhận tiến trình java còn nguyên qua `ps`.
- Không đo được queue depth trực tiếp (không có JMX/API) — suy từ khoảng cách `Start` và cấu hình pool.
- `df /` vẫn 93% (rủi ro sẵn có, ngoài phạm vi).
