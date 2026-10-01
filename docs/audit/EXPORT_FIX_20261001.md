# EXPORT-FIX 2026-10-01 — (D) bug writer GZ + (B)+(C) thêm cột dump ⇒ parity

> Owner duyệt 2026-10-01 12:47 ("ok"). Branch `module`. Ràng buộc giữ đủ: Python thuần · **0 Java/sim trên Oracle** (chỉ `mvn -o package`) · **242 backup trước mọi thay đổi, restart chuẩn (không `kill -9`), không đụng `SHADOW_NO_PUSH`** · 0 secret · 0 push data · 2026 = holdout (chỉ audit).
> Harness: `research/parity/parity_check.py` (v4). Report: `docs/result/parity_report.{json,md}`. Tiền đề: `docs/result/RESULT_PARITY_HARNESS_V3.md`.

## 0. TÓM TẮT

| việc | kết quả |
|---|---|
| **(D)** bug writer gz "cắt cụt" | **ĐÃ SỬA** — shutdown hook + xoay file (key-gated, default cũ). File mới `gzip -t`=0, hết tail `00 00 FF FF`. |
| **(B)** marketparams 4/4 | **ĐÃ THÊM** `rateUpAvg/rateUp15MAvg` vào `feat_dump`. LIVE-side **trực tiếp 4/4** (max\|Δ\|≤7,5e-4). |
| **(C)** selector cùng tick | **ĐÃ THÊM** `sel_dump_*.csv.gz` = `ts,symbol,selectorScore,rank,gateValue,p15`. LIVE đo được **cùng tick**; đối ứng DEV vẫn MISSING (cửa sổ). |
| **Deploy 242** | jar mới + env merge + restart chuẩn; canh 12:54→13:2x: **0 OOM · 0 lệnh thật · [GATE]/phút n_pass=0 · dump mới có trailer**. |
| **Parity** | `config PASS`; `marketparams` **LIVE-direct 4/4 PASS**; `selector input.live_col PASS`; còn `features 27/33` + `entry (0 vs ≥1)` ⇒ overall vẫn **FAIL**. |

**Kết luận: PASS** (đã gỡ đúng 2 nút thắt (B)/(D) + mở đường đo (C) cùng tick; phần FAIL còn lại là đã biết từ v3, không hồi quy). **Không cần rollback.**

---

## 1. (D) SỬA BUG WRITER GZ — `LiveFeatureDump.java`

**Nguyên nhân (v3 §1):** `GZIPOutputStream(counter,16384,true)` (syncFlush) + `flush()` mỗi dòng ⇒ file luôn kết thúc bằng DEFLATE sync-flush block `00 00 FF FF`, nhưng **trailer (CRC32+ISIZE) chỉ ghi khi `close()`** — mà `close()` chỉ gọi khi đủ REMAINING tick/200 MB, **không có shutdown hook** ⇒ JVM restart giữa chừng ⇒ thiếu trailer.

**Patch:**
1. **Shutdown hook** `LiveFeatureDumpFinalize` (giống pattern `LiveGateRollingRatio`): khi JVM dừng ⇒ `close()` cả `feat_dump` + `sel_dump` ⇒ finalize trailer. Đăng ký 1 lần khi `LIVE_FEAT_DUMP>0`.
2. **Xoay file theo phút** qua key mới **`LIVE_FEAT_DUMP_ROTATE_MIN`** (mặc định **0 = TẮT = hành vi cũ**). Khi >0 ⇒ mỗi N phút `close()` file hiện tại rồi mở file mới (mọi file đóng đúng cách).
3. Gộp 2 writer vào `GzSink` (dùng chung cơ chế), 0 đổi logic gate/ONNX.

**Self-test nhỏ (Java, trên Oracle host — không sim):** `DumpSelfTest` gọi `maybeDump`/`maybeDumpSelector` rồi thoát JVM:

| kịch bản | kết quả |
|---|---|
| hook-only (5 dòng < REMAINING) | `feat_dump` trailer=**True**, `sel_dump` trailer=**True**, giải nén OK |
| xoay file (ROTATE_MIN=0,05) | nhiều file, **100% trailer=True** |
| header feat_dump | 40 cột: `ts,symbol,33 feat,p15_out,rateDownAvg,rateUpAvg,rateDown15MAvg,rateUp15MAvg` |

**Bằng chứng trên 242 (file thật):**

| file | `gzip -t` | tail 4 byte | kết |
|---|---|---|---|
| `feat_dump_20261001_110300.csv.gz` (jar CŨ) | **1 (FAIL)** | `0000ffff` | cắt cụt |
| `feat_dump_20261001_125300.csv.gz` (jar MỚI, xoay 13:04) | **0 (OK)** | `c2180000` | **đủ trailer** |
| `sel_dump_20261001_125300.csv.gz` (jar MỚI) | **0 (OK)** | `fd270000` | **đủ trailer** |

---

## 2. (B) MARKETPARAMS 4/4 — thêm `rateUpAvg` + `rateUp15MAvg`

`feat_dump` thêm 4 cột `rateDownAvg,rateUpAvg,rateDown15MAvg,rateUp15MAvg` (từ `MarketDataObject` tại call-site; `rateUp15MAvg` = 0 vì pipeline/`calMarketData`/`market.bin` chỉ có 3 field ⇒ **khớp DEV store**).

Đo **LIVE-direct** (feat_dump ↔ inline cùng phút, v4):

| field | n | max\|Δ\| | corr | kết |
|---|---|---|---|---|
| rateDownAvg | 513 | 7,49e-4 | 0,9949 | PASS |
| rateDown15MAvg | 513 | 7,40e-4 | 0,9996 | PASS |
| **rateUpAvg** | 18 | **4,73e-4** | 0,9471 | **PASS (mới)** |
| rateUp15MAvg | 18 | 0 | 1,0 | PASS |

⇒ **4/4 field đo được TRỰC TIẾP từ LIVE** (thay vì 2/4 như v3). Nguồn p15/selector không đổi.

---

## 3. (C) SELECTOR CÙNG TICK — `sel_dump_*.csv.gz`

Thêm writer `maybeDumpSelector(ts, symbol, selectorScore, rank, gateValue, p15)` gọi **trong vòng selector** (`DetectEntrySignal2TradeNormal`, ngay sau `rank++`). Cùng công tắc `LIVE_FEAT_DUMP` (default TẮT ⇒ 0 đổi khi không bật).

- Header: `ts,symbol,selectorScore,rank,gateValue,p15`.
- Bằng chứng LIVE (242): `sel_dump_20261001_125300.csv.gz` — **10 tick, 160 dòng** (TOPK=16/tick), ví dụ `ARKUSDT,score=-1.00318694,rank=1,gateValue=0.33095,p15=0.008695`.
- Harness v4 thêm `SEL_DUMP_GLOBS` + `load_sel_dump()` ⇒ `selector.input.live_col = PASS` (**cùng tick**: score/rank/gate/p15 trong 1 bản ghi).
- **Còn MISSING:** đối ứng DEV cùng tick — `funding.bin` (≤2025-12-31) không phủ cửa sổ LIVE (2026) ⇒ `selector.output.compare = MISSING` + lý do. Để chốt 100%: **regenerate export DEV (≤2025-12-31) có `selectorScore+rank+p15`** (cần chạy Java/Kaggle).

---

## 4. DEPLOY 242

- **Backup (trước khi thay):** `backup_exportfix_20261001_1253/` gồm `jar.bak` (sha256 `e30358c1…`), `env.sh.bak`, `config.properties.bak`. Jar cũ giữ nguyên trong backup.
- **Jar mới:** sha256 **`8f3ee52ce4ceac8c742950cd585ba5968abd318ae5dfb1fa2748831cf9f4fcf0`** (local=remote khớp), build `mvn -o -q -DskipTests package` EXIT=**0**.
- **Config:** chỉ **append** 1 dòng `export LIVE_FEAT_DUMP_ROTATE_MIN=10` vào `conf/env.sh` (merge, không thay cả file; `SHADOW_NO_PUSH` không đụng).
- **Restart chuẩn:** `bin/daemon.sh restart` (SIGTERM → chờ → start). PID mới `20743`, active. Log `[LIVE_FEAT_DUMP] BAT … xoay=10 phut`.

**Canh 12:54 → 13:2x (≈28'):**

| hạng mục | kết quả |
|---|---|
| OOM | **0** |
| lệnh thật (BUY/createOrder) | **0** |
| `[GATE]` mỗi phút (mode `ratio`) | 12+ dòng, **n_pass=0** (thr 0,033–0,045 > p15_max 0,015) |
| dump mới | xoay 13:04 → `gzip -t`=0 (đủ trailer) |

⇒ **PASS — không rollback.** (Rollback sẵn: copy `backup_exportfix_20261001_1253/jar.bak` đè `target/binance-java-sdk-1.2.4.jar`, khôi phục `env.sh.bak`/`config.properties.bak`, `daemon.sh restart`.)

---

## 5. PARITY SAU FIX (v3 → v4)

| tầng | V3 | **V4** | ghi chú |
|---|---|---|---|
| config | PASS | **PASS** | 27/27 MATCH |
| features | FAIL 27/33 | FAIL 27/33 | không hồi quy; nhóm (i) nhiễu ticker-vs-kline |
| gate | MISSING | MISSING | `mode_parity` PASS; cùng-phút MISSING (cửa sổ) |
| marketparams | MISSING (4/4 đo) | **MISSING; LIVE-direct 4/4 PASS** | (B) đã gỡ |
| selector | MISSING | **MISSING; input.live_col PASS (sel_dump cùng tick)** | (C) đã mở đường đo |
| entry | FAIL (0 vs ≥1) | FAIL (0 vs ≥1) | gate đóng ⇒ 0 entry |
| exit | MISSING | MISSING | không có lệnh đóng |
| selftest | 4/4 PASS | **4/4 PASS** | gồm `gz_writer_finalize` |

**overall = FAIL (exit 2)** — do `features` (27/33) + `entry` (0 vs ≥1). **Còn thiếu để 100%:**
1. **(E)** 27 feature: chốt nhóm (iii) bằng control **cùng-nguồn** trên Kaggle (nạp cùng kline lưu vào cả 2 nhánh); nhóm tỉ số cần ngưỡng liên-thị-trường.
2. **(C)** regenerate export DEV (≤2025-12-31) có `selectorScore+rank+p15` ⇒ có cùng tick để so; + regenerate p15 DEV cùng cửa sổ.
3. **entry/exit**: cửa sổ có ứng viên qua gate ⇒ cần cấu hình gate mở (ngoài phạm vi audit) hoặc so trên cửa sổ DEV có n_pass≥1.

---

## 6. MỤC BỎ / LÝ DO

- **Không** chạy Java/sim/WFO trên Oracle (chỉ build jar + self-test nhỏ); **không** ONNX.
- **Không** bịa PASS cho tầng thiếu đối ứng: giữ MISSING + lý do (cửa sổ 2026 ≠ DEV).
- **Không** sửa/cập nhật dữ liệu trên 242 ngoài: append 1 dòng env + thay jar (có backup); **không** push file dữ liệu (mọi CSV gitignored).
- **Không** dùng 2026 để chọn/tune tham số (chỉ đối chiếu).
