# KAGGLE_FANOUT_RESULT — Full fan-out ret2 (Oracle 2 worker + Kaggle 5 node) + benchmark

> Ngày: 2026-07-13. Nối tiếp `KAGGLE_FANOUT_PHASE1.md` (hạ tầng). Đây là kết quả CHẠY FULL + so sánh.
> Trạng thái khi ghi (14:41): ticker regen XONG+verify; upload Kaggle DÍNH 502 (đang retry); fan-out ĐANG CHẠY,
> tự report qua `report_watch.sh`. Các mục verdict/tốc-độ/độ-chính-xác auto-điền khi run xong (đọc cách ở §7).

---
## ✅ CẬP NHẬT 20:2x (phiên GIẢI QUYẾT: archive upload THÀNH CÔNG + fan-out 7 node CHẠY THẬT)

> Phiên này de-risk toàn bộ nút chặn cũ. Ticker sạch ĐÃ lên Kaggle, 5 kernel Kaggle + 2 Oracle ĐÃ join thật.

### 0. TL;DR
- **Kaggle CLI**: `pip install -U kaggle` = **1.7.4.5** trong venv SẠCH (`~/kaggle_latest_venv`) commit READY OK,
  **KHÔNG lỗi 'type'**. Bug 'type' cũ là do dependency cũ trong `~/envs/xgb-env`, KHÔNG phải bản client. Server=2.2.2.
- **Ticker lên Kaggle = XONG bằng ARCHIVE 1-file**: tar toàn bộ `ticker_regen` → 1 file `ticker_all.tar` (10.76GB) →
  `kaggle datasets version -p <dir> -m ...` (venv latest) → **Upload successful, rc=0, KHÔNG 502**.
  **PHÁT HIỆN QUAN TRỌNG: Kaggle TỰ giải nén .tar VÀ .gz** → dataset `chuyendinh/hpo-ticker-daily` **version 6 READY**
  = **1826 file `ticker_YYYYMMDD.bin` (uncompressed, ~31.5GB)**, phủ đủ `20210101..20251231` (verify có 31 file Dec-2025),
  date hôm nay = **ghost-clean của phiên này** (KHÔNG phải bản stale 07-04). `KaggleDataLoader` đọc `.bin` (ưu tiên 1) → dùng thẳng.
- **Fan-out 7 node CHẠY THẬT** (reset 20:19:58): coordinator 226/ticker 16 window, **RUNNING=7** =
  **2 Oracle** (`instance-20260622-1647`) **+ 5 Kaggle** (owner hex 12-ký-tự: `73277849c613`,`719f57f6dee4`,`6153bfde8410`,`bbd25fcd227f`,`19d46a807d3c`).
  ⇒ mục tiêu ">2 Kaggle node đọc file" ĐẠT.

### 1. Nút chặn thật đã khử — vì sao 2 lần trước fail
- **Bug 'type' (1.7.4.5)**: KHÔNG phải bản client — là env `xgb-env` có kagglesdk/protobuf lệch. Cài SẠCH `pip install -U kaggle` → hết.
- **502 finalize per-file (1826 file)** + **"10GB single-file không finalize trong 25' nếu nghĩ theo hướng cũ"**: thực ra **KHÔNG có lỗi finalize**
  cho archive — chỉ là mình HIỂU NHẦM. Kaggle nhận `ticker_all.tar`, xử lý async (giải nén tar+gz) ~vài phút→chục phút cho 10GB→31.5GB,
  trong lúc xử lý `datasets files` hiện version cũ. Sau xử lý xong: **1826 `.bin` extracted, version 6, tải được** (`ticker_20251231.bin` HTTP 302).
  `ticker_all.tar` trả 404 vì Kaggle KHÔNG giữ tar (đã bung). ⇒ **đây là cách BỀN để đẩy data lớn: 1 tar → 1 upload → Kaggle bung.**
- Bằng chứng auto-extract: probe throwaway (upload 1 file `ticker_probe.tar` 486MB) → dataset hiện thành các file `ticker_*.bin` riêng lẻ.

### 2. Cách làm ticker (RUNBOOK bền cho lần sau)
```bash
# 1 lần / khi kline nguồn đổi:
cd /home/ubuntu/claudedata/ticker_regen/kaggle_data_hpo && tar cf /home/ubuntu/claudedata/ticker_archive/ticker_all.tar .
#   (dataset-metadata.json id=chuyendinh/hpo-ticker-daily đặt trong ticker_archive/)
source ~/kaggle_latest_venv/bin/activate
kaggle datasets version -p /home/ubuntu/claudedata/ticker_archive -m "ticker single-archive" -r skip
#   → chờ Kaggle bung tar+gz; verify: python API dataset_list_files thấy 1826 ticker_*.bin + ticker_20251231.bin tải được (302).
```
- Disk Oracle vừa dọn còn ~14G → tar 10.76GB vừa đủ (kiểm `df` trước). Upload ~8.5' @ ~20MB/s. **KHÔNG cần per-file, KHÔNG cần 226.**
- Kernel đọc: `kernel_run_worker.py` glob `ticker_2*.bin*` → symlink dir → `kaggle_data_hpo/` (đã có sẵn nhánh này; tar tự-bung nên
  KHÔNG cần giải nén trong kernel). Đã thêm nhánh phòng-hờ giải-nén-tar (chỉ chạy nếu Kaggle KHÔNG bung — hiện không dùng tới).

### 3. Launch fan-out — lệnh + bug đã sửa
```bash
WFO_MAX_OOS_DATE=20260101 bash /home/ubuntu/claudedata/.run/launch_fanout.sh \
   /home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff 2 1 30 /home/ubuntu/claudedata/ticker_regen
# arg3=1 BẮT BUỘC để push Kaggle.
```
- **Bug launcher slot-check (đã sửa)**: `USED=$(... grep -cE "running|queued" || echo 0)` → khi grep -c trả "0" + exit≠0 →
  `|| echo 0` chạy thêm → `USED="0\n0"` → `$((5-USED))` **syntax error** → FREE rỗng → **push KHÔNG chạy**.
  Sửa: `USED=$(kaggle kernels list --mine 2>/dev/null | grep -cE "running|queued" | head -1); USED=${USED:-0}`.
  Phiên này workaround bằng **push 5 kernel thủ công** (`kaggle kernels push` từng folder) → cả 5 RUNNING.
- Launcher đã đổi push sang `~/kaggle_latest_venv` (thay `~/kaggle_venv`).

### 4. Trạng thái run (self-completing) + cách đọc kết quả cuối
- reset epoch = **20:19:58** (`.run/fanout_reset_epoch.txt`). Kernels push ~20:22. Cả 5 kernel Kaggle join lúc **20:23** (RUNNING 2→7).
- `report_watch.sh` (nền) poll 226 tới 16 window terminal → ghi `WfoCoordinator report` vào `.run/report_watch.log` (mốc `RW_ALL_TERMINAL`).
- **Đọc verdict + wall-clock cuối**: `cat /home/ubuntu/claudedata/.run/report_watch.log` (RW_ALL_TERMINAL time − 20:19:58 = wall-clock).
- Verdict/tốc-độ/accuracy: §5b bên dưới auto-điền khi xong (phiên này để chạy nền, KHÔNG babysit).

### 5b. Verdict + so sánh (điền khi 16 window DONE — đọc report_watch.log)
- _Đang chạy: 7 node, N=30/window, WFO_MAX_OOS_DATE=20260101._
- Baseline Oracle-only ret2 (tham chiếu §4/§8 cũ): VERDICT FAIL/REVIEW, %OOS+ 43.8% (7/16), WFE median 0.307, maxDD OOS xấu nhất 32.4%.
- So tốc độ: Oracle-only 2-worker file-ticker phiên trước = 10/16 window trong ~5h (14:28→19:32, chậm vì file KHÔNG cache).
  Fan-out 7-node kỳ vọng nhanh hơn NHIỀU. Accuracy: Oracle đọc `.bin.gz` (ticker_regen) + Kaggle đọc `.bin` (bung từ cùng tar) —
  **cùng data ghost-clean** ⇒ kỳ vọng KHỚP (chỉ khác nén/giải-nén, nội dung y hệt).

---
## CẬP NHẬT 17:5x (phiên fix CLI + upload bền vững + orchestrator self-completing)

### A. Sửa Kaggle CLI — XONG (đây là nút chặn thật)
- **Nguyên nhân gốc**: venv `~/envs/xgb-env` dùng **kaggle 1.7.4.5** → mỗi file lớn báo
  `ApiStartBlobUploadRequest.__init__() got an unexpected keyword argument 'type'` (bug tương thích proto/kagglesdk 1.7.x).
  Trước đó cũng dính 502 ở bước finalize ⇒ version KHÔNG commit.
- **Fix**: tạo venv riêng SẠCH `~/kaggle_venv` (python3.10) + `pip install kaggle==1.6.17` (không đụng xgb-env đang dùng cho việc khác).
  1.6.17 dùng REST-upload cũ. Lưu ý: với FILE LỚN 1.6.17 vẫn in warning benign
  `StartBlobUploadRequest ... 'contentLength'` ở nhánh *resume/load-upload-info* (dòng 241) → rồi **upload tươi thành công**
  ("Upload successful"). File nhỏ (<vài chục KB) upload thẳng, KHÔNG có warning.
- **Verify sạch**: smoke `kaggle datasets create` 1 file 42B → `Your private Dataset is being created` + `status=ready`,
  **KHÔNG lỗi 'type'**, finalize commit OK. (dataset smoke throwaway, không đụng dataset thật).
- **Kết luận**: bug 'type' ĐÃ khử. Chỉ còn warning benign trên file lớn (fallback vẫn upload đúng). CLI dùng cho mọi việc Kaggle
  từ nay = `source ~/kaggle_venv/bin/activate`.

### B. Launcher fix (để Kaggle THỰC SỰ join)
- **Bug tee-hang (nút thật khiến Kaggle chưa từng join)**: `launch_fanout.sh` step-3 spawn worker bằng
  `( ... nohup java ... & echo ... ) | tee -a $LOG` → pipe không nhận EOF → launch_fanout TREO ở step-3 ⇒
  **step-4 (push 5 kernel Kaggle) KHÔNG BAO GIỜ chạy**. Đã sửa: ghi thẳng `echo ... >> "$LOG"`, bỏ `| tee`. `bash -n` OK.
- **Arg push-kaggle**: logic `PUSHK=${3:-1}` **đúng sẵn** — chỉ push khi arg3=`1`. Lỗi run trước là GỌI SAI
  (truyền `5` vào vị trí arg3). Lệnh đúng: `launch_fanout.sh <DS> 2 1 30 <TICKER_BASE>`.
- **Cải tiến bền vững**: đổi bước `kernels push` trong launcher sang `~/kaggle_venv` (CLI 1.6.17 đã sửa) thay vì xgb-env 1.7.4.5.

### C. Trạng thái chạy (self-completing, KHÔNG cần babysit)
- `ticker_upload_v2.sh` (nền): upload 1826 `.bin.gz` lên `hpo-ticker-daily` bằng kaggle 1.6.17 → log `ticker_upload_v2.log`
  (marker `TUV2_VERSION_RC` / `TUV2_COMMITTED` / `TUV2_READY`). ETA ~2h (per-file, disk 99% nên KHÔNG zip được → stream từng file).
- `fanout_when_ready.sh` (nền, orchestrator): chờ ticker commit sạch (≥1800 `.bin.gz` remote + status ready) →
  **kill run Oracle-only cũ** (2 WfoWorker + report_watch của tôi) → `launch_fanout.sh ... 2 1 30 ...`
  (reset 226/ticker + 2 Oracle + push 5 Kaggle) → `report_watch2.sh` (tự report khi 16 window terminal).
  **Failsafe**: nếu ticker KHÔNG commit sạch sau timeout → KHÔNG đụng run cũ (giữ verdict Oracle-only), ghi `FWR_ABORT`.
- Đọc kết quả: `tail -f .run/fanout_when_ready.log` (mốc `FWR_TICKER_READY`/`FWR_RESET_EPOCH`), `.run/report_watch2.log` (`RW_ALL_TERMINAL`+report).

## 1. Ticker regen full — XONG + VERIFY (TRÒN)
- **Kết quả: 1826 file `.bin.gz`, 11GB, dải `20210101..20251231`, 0 file rỗng, liên tục đủ 1826 ngày** (5 năm gồm leap 2024).
- Thư mục: `/home/ubuntu/claudedata/ticker_regen/kaggle_data_hpo/`. Nguồn: Oracle-local `kline_1m_opt` (đã ghost-clean 07-07).
- Tool: `ExportHpoDataKaggle START END ticker` (tái dùng, không viết mới). ~2.6-3s/ngày.
- **Sự cố disk-full (đã xử lý):** lần regen nền trước CHẾT lúc 12:36 tại ngày 20251123 với `java.io.IOException: No space left on device`
  (đĩa `/dev/sda1` 146G = 100%). Export tới 2025-11-22 OK rồi hết chỗ; các ngày sau thành file 0-byte; JVM treo (no System.exit).
  - Xử lý: kill đúng PID JVM treo (2289693) + wrapper; dọn `ticker_smoke` (1.4G, subset smoke đã bị ticker_regen thay thế)
    + `wfo_feature_store.csv.bak_20260711_2333` (996M, backup dư — bản chính còn nguyên, CSV tái sinh được); xoá 91 file 0-byte;
    xoá file 20251123 ghi-dở (9.4MB vs ~14MB) rồi **export bù `20251123..20260101`** vào cùng thư mục (không rm 1788 file tốt).
  - Marker "🎉 All data exported" xác nhận 12:57; file cuối 20251231 (20260101 không có data — đúng, OOS window cuối cần tới hết 2025-12).

## 2. Upload Kaggle `chuyendinh/hpo-ticker-daily` — ⚠️ DÍNH 502 (đang retry)
- Đĩa còn ~1.4-1.8G sau dọn ⇒ KHÔNG thể tạo zip 11GB ⇒ upload **từng file** (`kaggle datasets version --dir-mode skip`, streaming, không phình temp).
- **1826/1826 file upload OK** (~21 file/phút, ~90 phút, 12:58→14:28). NHƯNG bước tạo version CUỐI:
  `502 Server Error: Bad Gateway for url: .../datasets/create/version/chuyendinh/hpo-ticker-daily`.
  ⇒ **version MỚI KHÔNG commit.** Dataset vẫn là bản CŨ stale `2026-07-04` (file `.bin` không nén, pre-ghost-clean).
- Cảnh báo "ApiStartBlobUploadRequest ... unexpected keyword 'type'" mỗi file = vô hại (kaggle CLI 1.7.4.5 fallback, file vẫn "Upload successful").
- **Retry đang chạy nền** (`kaggle_join.sh`, tối đa 3 lần): re-upload → khi thấy file `.bin.gz` mới commit + READY thì push 5 kernel.
  → 502 là lỗi server Kaggle (transient). Nếu retry vẫn 502 3 lần → Kaggle-side BLOCK, báo rõ (không bịa).

## 3. Fan-out ret2 — ĐANG CHẠY (self-completing)
- `WfoCoordinator reset strategy_window` → **16 window PENDING** trên REAL 226 (`103.157.218.226:3222 ns=ticker`), `WFO_MAX_OOS_DATE=20260101`, N=30.
  Window OOS khớp baseline: w0 `20220101..20220401` … **w15 `20251001..20260101`** (loại window 2026).
- **2 Oracle worker** (`TICKER_SOURCE=file`, đọc ticker_regen SẠCH) — XÁC NHẬN chạy đúng: w1 log
  `[BT 20210101..20220101] note=SUCCESS trades=533 pnl=5709 ddPct=0.080 maxDD=2788 fit=2.05`. Coord: RUNNING=2.
- **5 kernel Kaggle: CHƯA push.** 2 lý do: (a) ticker version mới chưa commit (502); (b) **lỗi arg launcher**: ví dụ trong đề
  `launch_fanout.sh DS 2 5 30 ticker` map thành `N_ORACLE=2 PUSH_KAGGLE=5 N_SAMPLES=30`, nhưng script push chỉ khi `PUSHK==1`
  ⇒ với `5` KHÔNG push. **Đúng phải là `... 2 1 30 ...`.** `kaggle_join.sh` sẽ push 5 kernel khi version sẵn sàng.
- **Bug launch_fanout tee-hang (đã workaround):** step-3 `for ... nohup java ... & echo | tee -a $LOG` bị treo (worker nohup giữ pipe,
  `tee` không nhận EOF) ⇒ launch_fanout KHÔNG return ⇒ orchestrator kẹt, phase report không chạy. Đã tách **`report_watch.sh`**
  (poll coord tới terminal → `WfoCoordinator report`), kill orchestrator+launch_fanout kẹt (worker KHÔNG đụng). → run tự report.
- Wall-clock start (reset) = **14:28:54**. Đo tới đủ 16 window terminal.
- ⚠️ **Rủi ro RAM:** máy 23GB, 2 worker `-Xmx8g` + python upload ⇒ available ~5GB. Window 2024+ (~600 coin/ngày) có thể OOM
  (bài học TASK-039). Nếu OOM → window FAILED trong coord (report_watch vẫn thoát khi PENDING=RUNNING=0).

## 4. Baseline so sánh — Oracle-only ret2 (aerospike-ticker, N=30) [đã có]
Nguồn `/home/ubuntu/claudedata/wfo_report_final_ret2wf.md`:
- **VERDICT: FAIL/REVIEW** | %OOS dương **43.8% (7/16)** | WFE median **0.307** | maxDD OOS xấu nhất **32.4%** (abs 11331).
- Ngưỡng pre-reg: WFE≥0.5, %OOS+≥70%, maxDD≤50%.
- Đặc điểm: w0/w2/w4/w13 ZERO_TRADES; nhiều window TOO_FEW_TRADES; **w15 (2025Q4) áp đảo**: SUCCESS 1154 trades, pnl 11727, maxDD 32.4%.

## 5. SO SÁNH tốc độ (điền khi xong) — PENDING
| Cấu hình | Nguồn ticker | #node hiệu dụng | Wall-clock 16 window | Ghi chú |
|---|---|---|---|---|
| Oracle-only baseline | aerospike + SMART_CACHE | 1 (tuần tự) | ~90'/model (tham chiếu) | có cache RAM |
| Fan-out (run này) | **file** (ticker_regen) | 2 Oracle (+5 Kaggle nếu join) | _(auto)_ | file-ticker KHÔNG cache → chậm/ window |
> Phase1 đo: Oracle 1 window N=5 = 407s; file-ticker chậm ~2× aerospike-cache (đọc+gunzip lại mỗi sample).

## 6. SO SÁNH độ chính xác (điền khi xong) — PENDING
- Verdict fan-out (clean file-ticker) vs baseline (aerospike): khớp PASS/FAIL? %OOS+ / WFE median / maxDD lệch bao nhiêu?
- Per-window (oosPnl/WFE/oosNote/trades): khớp xu hướng? **Confound đã biết:** fan-out dùng ticker FILE + đã ghost-clean
  vs baseline aerospike ⇒ có thể lệch số; cần đọc theo xu hướng, không kỳ vọng trùng khít.

## 7. Cách đọc kết quả cuối (khi run xong, KHÔNG cần phiên này)
```
# Trạng thái / verdict cuối (auto-ghi):
cat /home/ubuntu/claudedata/.run/report_watch.log        # RW_ALL_TERMINAL <time> + full report + RW_COMPLETE
# Hoặc chủ động:
cd /home/ubuntu/java/simulator; WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker \
  java -cp binance-futures-preflight.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window
# Kaggle join / upload retry:
cat /home/ubuntu/claudedata/.run/kaggle_join.log         # NEW_VERSION_COMMITTED / PUSH_KERNELS / KJOIN_DONE | KJOIN_ABORT
# Worker Oracle (lỗi/OOM):
grep -iE "OutOfMemory|Exception|FAILED|note=" /home/ubuntu/claudedata/.run/fanout_oracle_w{1,2}.log | tail
# Wall-clock = (RW_ALL_TERMINAL) - (14:28:54 reset). Nếu Kaggle join muộn → ghi rõ mốc node ramp.
```
Process nền còn sống: 2 worker (2312427,2312430) · reporter report_watch (2314212) · kaggle_join (2313074).

## 8. RUNBOOK tái dùng WFO/pred lần sau (hạ tầng BỀN VỮNG)
> Mục tiêu đạt: ticker dataset ổn định trên Kaggle → mỗi run chỉ launch là 5 Kaggle + Oracle cùng chạy.

**Điều kiện tiên quyết CLI (1 lần):** luôn dùng `source ~/kaggle_venv/bin/activate` (kaggle **1.6.17**) cho MỌI lệnh Kaggle.
KHÔNG dùng `~/envs/xgb-env` (kaggle 1.7.4.5 dính bug 'type', không commit được version).

**Ticker (BỀN VỮNG — chỉ re-version khi kline NGUỒN đổi):**
- Dataset `chuyendinh/hpo-ticker-daily` = 1826 file `.bin.gz` (2021-01-01..2025-12-31), ghost-clean. KHÔNG upload lại mỗi run.
- Chỉ khi kline nguồn đổi: `bash .run/regen_ticker.sh <START> <END> /home/ubuntu/claudedata/ticker_regen 0` (regen file),
  rồi `source ~/kaggle_venv/bin/activate && cd ticker_regen/kaggle_data_hpo && kaggle datasets version -p . -m "..." --dir-mode skip`.

**Mỗi run WFO/pred mới — các bước TỐI THIỂU:**
1. (chỉ khi model/data _ff đổi) `bash .run/sync_ff_kaggle.sh <DS_DIR> <SLUG>` — sync _ff ~570MB (nhanh).
2. `WFO_MAX_OOS_DATE=<yyyymmdd> bash .run/launch_fanout.sh <DS_DIR> 2 1 30 /home/ubuntu/claudedata/ticker_regen`
   → tự: A6 fail-fast → reset 226/ticker → 2 Oracle worker (ticker=file) → **push 5 kernel Kaggle** → status.
   (arg3=**1** BẮT BUỘC để push Kaggle; tee-hang đã fix nên push chạy thật.)
3. `nohup bash .run/report_watch.sh &` → tự poll tới 16 window terminal rồi ghi `WfoCoordinator report` vào `report_watch.log`.
4. Kaggle join xác nhận: owner window = hex container 10+ ký tự (khác hostname Oracle `instance-*`).

**Nút còn lại / bẫy đã biết:**
- Disk Oracle `/dev/sda1` 99% (1.7G trống) → KHÔNG zip 11GB được, upload ticker phải per-file (~2h). Nên dọn disk khi rảnh.
- RAM 23GB: 2 Oracle `-Xmx8g` + việc khác → window 2024+ (~600 coin/ngày) có nguy cơ OOM. Nếu FAILED → giảm N hoặc 1 worker.
- File-ticker KHÔNG cache RAM (đọc+gunzip lại mỗi sample) → chậm ~2× aerospike-cache/window. Đề xuất Phase1: thêm cache theo ngày.

---

## 9. ĐÁNH GIÁ hướng "ticker chung qua aerospike mạng" (phiên 2026-07-13, CCD eval — CHƯA thực thi mở port)

> Bối cảnh: upload 11GB lên Kaggle từng fail (CLI + 502) → user đề xuất cho node đọc ticker TỪ AEROSPIKE
> CHUNG qua mạng thay vì upload file. Phiên này chỉ ĐÁNH GIÁ + soạn lệnh an toàn; KHÔNG mở port (chờ user OK).
> Ghi chú môi trường CCD: chạy trong sandbox KHÔNG có mạng ra ngoài + KHÔNG có SSH key → mọi bước cần
> SSH Oracle/226/Kaggle được soạn thành lệnh sẵn để user/CCD-có-mạng chạy (đánh dấu ⏳ CHỜ CHẠY).

### 9.1 Host có ticker 1m SẠCH (ghost-clean 07-07) — XÁC ĐỊNH TỪ CODE/DOC
- **Set = `kline_1m_opt`**, namespace = `ticker` (`config.properties: AEROSPIKE_NAMESPACE=ticker`;
  `DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER="kline_1m_opt"`).
- Backtest/sim đọc ticker qua `getReadClient()` → chọn cluster theo `AEROSPIKE_READ_CLUSTER` (config).
  Trên Oracle: `AEROSPIKE_READ_CLUSTER=226` **nhưng** `AEROSPIKE_HOST_226=127.0.0.1` (per `db/index.md` §6)
  ⇒ "226" trong code khi chạy TRÊN Oracle = **Aerospike LOCAL Oracle 127.0.0.1:3222**. `TICKER_SOURCE=aerospike`.
- **Bản SẠCH đầy đủ (2021-01-01..2025-12-31, ghost-clean 07-07) sống ở 2 nơi:**
  1. **Aerospike LOCAL Oracle** `127.0.0.1:3222` ns=`test`/`ticker` set `kline_1m_opt` (nguồn ExportHpoDataKaggle đọc ra).
  2. **FILE** `/home/ubuntu/claudedata/ticker_regen/kaggle_data_hpo/` = **1826 file `.bin.gz`, 11GB** (§1 ở trên — đã verify liên tục đủ 1826 ngày).
- **REAL 226 (103.157.218.226:3222 ns=ticker)** — nơi Kaggle TỚI ĐƯỢC — hiện **KHÔNG có bản ticker sạch đầy đủ**:
  ticker set ở đây chỉ phủ tới **~2024-04-01** và là bản pre-ghost-clean (§3d KAGGLE_RULES). Đây là mấu chốt.
- **242** = live source, KHÔNG ghost-clean (clean chỉ làm ở Oracle-local) ⇒ `CopyTicker242To226` sẽ mang bản KHÔNG sạch → KHÔNG dùng cho mục tiêu này.

### 9.2 ⚠️ PHÁT HIỆN CHẶN CHUNG cho CẢ A và B (phản biện — CORE §phản-biện)
Đọc ticker qua **aerospike-mạng từ Kaggle bị cap ~2 worker đồng thời** (KAGGLE_RULES §3d, đo 2026-07-04):
5 worker SMART_CACHE → 226 (RAM ~15GB) drop connection (`Connection Error -8`/`EOFException`) → 9/17 job FAIL;
1 worker OK (744s/window), 2 worker OK (315s/window). ⇒ **Cả A lẫn B đều KHÔNG mở khoá được fan-out 5 node**
nếu node đọc ticker qua aerospike mạng — trần vẫn ~2 Kaggle reader. Muốn >2 → BẮT BUỘC ticker vào **dataset FILE**.
Kết luận sớm: hướng "aerospike chung" chỉ hợp cho **≤2 Kaggle worker** hoặc cho **worker Oracle-local** (đọc localhost, không qua mạng).

### 9.3 Phương án A — Mở Oracle-local aerospike ra internet
Các bước (⏳ CHỜ USER OK — vi phạm luật "không tự mở port DB"):
1. `aerospike.conf`: network.service `address any` + `access-address <public_ip>` (mặc định bind 127.0.0.1) → restart aerospike Oracle.
2. Mở firewall Oracle Cloud (Security List/NSG) + iptables/ufw cho TCP 3222.
3. Chặn truy cập: **Aerospike Community KHÔNG có auth** (auth chỉ Enterprise) ⇒ chỉ còn allowlist IP.
**Rủi ro / vướng:**
- **Kaggle egress IP KHÔNG cố định** (chạy trên GCP, dải IP động, Kaggle không công bố IP tĩnh) ⇒ **allowlist IP bất khả thi** → phải mở rộng → phơi DB không-auth ra internet = rủi ro rất cao.
- Oracle-local là box COMPUTE + chứa aerospike DATA-TEST (nguồn gốc dataset). Phơi port = tăng bề mặt tấn công lên chính máy đang cày.
- Không giải quyết được cap ~2 reader (§9.2). Restart aerospike có rủi ro ảnh hưởng job đang chạy.
- ⇒ **A: rủi ro cao, lợi ích thấp, KHÔNG khuyến nghị.**

### 9.4 Phương án B — Nạp ticker sạch → REAL 226 (đã mở sẵn cho Kaggle, KHÔNG port mới)
Cách nạp TỐT NHẤT: dùng **`IngestTickerFileToAerospike`** (đã có sẵn; args `start end [host] [port] [ns] [tickerDir]`)
đọc thẳng file sạch `ticker_regen` → ghi 226. **KHÔNG dùng `CopyTicker242To226`** (nguồn 242 chưa ghost-clean).
Lệnh (⏳ CHỜ CHẠY — chạy trên Oracle, đích 226 công khai; 226 đã mở nên không cần port mới):
```bash
cd /home/ubuntu/java/simulator
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g \
  -cp binance-futures-preflight.jar \
  com.binance.chuyennd.ai_ml.validation.data.IngestTickerFileToAerospike \
  20210101 20251231 103.157.218.226 3222 ticker \
  /home/ubuntu/claudedata/ticker_regen/kaggle_data_hpo
# tool GHI ĐÈ (UPDATE), idempotent theo key phút; System.exit(0) sẵn.
```
**Ước lượng:** ~2.63M record (1826×1440), bytes gốc ~20-22GB (242 `kline_1m_opt`=22.25GB). Copy nội-bộ 242→226
được ước ~15-30' (CopyTicker doc); nạp-từ-file (read+gunzip+parse+put) chậm hơn, **ước ~1-2h**.
**Vướng cần KIỂM (⏳):**
- **Disk 226 còn đủ ~22GB không?** 226 "tài nguyên YẾU" — phải `df -h` trước khi nạp (⏳). Nếu thiếu → phải dọn 226 trước.
- Vẫn dính cap ~2 Kaggle reader (§9.2) ⇒ B chỉ hữu ích khi fan-out ≤2 Kaggle worker + Oracle.
- Sau nạp: xoá được giới hạn "ticker 226 chỉ tới 2024-04" ⇒ window 2024+ đọc-mạng không còn FAIL-FAST thiếu ticker.
- ⇒ **B: KHÔNG cần mở port (an toàn hơn A rõ rệt), bền hơn, nhưng vẫn không phá được trần 2 reader.**

### 9.5 KHUYẾN NGHỊ (ít rủi ro + bền nhất)
1. **KHÔNG chọn A** (mở Oracle ra internet): rủi ro bảo mật cao, Kaggle IP không tĩnh nên allowlist bất khả thi,
   aerospike CE không auth, và vẫn không mở khoá fan-out.
2. **Đường CHÍNH vẫn là dataset FILE `hpo-ticker-daily`** — ĐÂY là cách DUY NHẤT hỗ trợ 5+ Kaggle node
   với ticker sạch đầy đủ và ZERO phơi port. Nút chặn cũ (CLI 1.7.4.5 lỗi 'type' + 502) **đã de-risk**:
   §A ở trên xác nhận kaggle **1.6.17** (`~/kaggle_venv`) khử được lỗi 'type' + retry self-completing đang chạy.
   ⇒ Ưu tiên để `ticker_upload_v2.sh`/`kaggle_join.sh` chạy xong; verify `kaggle datasets files chuyendinh/hpo-ticker-daily`
   thấy ~1826 file `.bin.gz` ngày mới + status ready.
3. **B (nạp file→226) chỉ làm khi cần "aerospike chung" cho ≤2 Kaggle worker HOẶC cho worker Oracle-local**
   — là fallback bền, không port mới. Chạy `IngestTickerFileToAerospike` như §9.4 sau khi `df -h` 226 OK.
4. Nếu bắt buộc muốn >2 Kaggle node đọc ticker-mạng: cần CODE thêm cache theo-ngày phía worker
   (giảm số connection/round-trip) + đo lại cap — chưa có, không hứa.

### 9.6 Smoke throughput/accuracy — TRẠNG THÁI
- **KHÔNG chạy được trong phiên này** (sandbox không mạng, không SSH key). ⏳ CHỜ.
- **Đã có số đo sẵn (không cần chạy lại):** đọc ticker 226 qua aerospike-mạng từ Kaggle —
  1 worker **744s/window**, 2 worker **315s/window** (§3d). Accuracy: cùng nguồn aerospike ⇒ kỳ vọng KHỚP.
- **ĐIỀU KIỆN để smoke "đọc ticker sạch đầy đủ qua mạng":** phải làm B trước (nạp ticker sạch → 226),
  vì hiện 226 chỉ có ticker tới 2024-04 → smoke window muộn sẽ FAIL-FAST thiếu ticker (đúng thiết kế TASK-112).
- Smoke ĐỀ XUẤT sau khi B xong (1 window, N nhỏ, ≤2 worker):
```bash
# so số Oracle-local vs Kaggle-đọc-226 cùng 1 window → kỳ vọng khớp xu hướng (cùng ticker sạch)
cd /home/ubuntu/java/simulator; WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker \
  java -cp binance-futures-preflight.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window
```

### 9.7 Disk cleanup Oracle — LỆNH AN TOÀN (⏳ CHỜ CHẠY, verify-trước-khi-xoá)
> CCD không có SSH → soạn lệnh; user/CCD-có-mạng chạy. TUYỆT ĐỐI không đụng file 2 process live.
```bash
# B1. ĐO trước (không xoá gì)
ssh -i ~/.ssh/id_rsa_chuyennd ubuntu@161.118.212.3 'df -h /; echo "---"; \
  du -sh ~/kaggle_selector_ds ~/kaggle_up_v3 ~/kaggle_ablation_ds ~/.cache ~/task156 \
         ~/envs/xgb-env ~/ticker_smoke 2>/dev/null; echo "--- *.bak/nohup ---"; \
  ls -lah ~/*.bak ~/nohup.out ~/*.log 2>/dev/null; echo "--- venv ---"; ls ~/envs 2>/dev/null'
# B2. XOÁ các ứng viên rõ-ràng-bỏ-được (chỉ chạy sau khi B1 xác nhận không đang dùng):
#   kaggle_selector_ds (9.3G) · kaggle_up_v3 (539M) · kaggle_ablation_ds (341M) · task156 (1.1G)
#   ~/.cache (1.1G, tái tạo được) · ticker_smoke (subset đã bị ticker_regen thay) · *.bak/nohup cũ
# GIỮ LẠI nếu nghi ngờ: envs/xgb-env (kaggle CLI cũ) — nhưng đã chuyển sang ~/kaggle_venv nên có thể bỏ,
#   XÁC MINH `pip -V` không ai dùng trước khi rm; ticker_regen (nguồn sạch 11GB — GIỮ); wfo_ds_*_ff (dataset — GIỮ).
# Mục tiêu: free ≥25G. KHÔNG rm khi chưa chắc — cái nào nghi ngờ để lại + báo.
```

### 9.8 Verdict run Oracle-only (tham chiếu — từ §4)
- Run Oracle-only ret2 baseline: **VERDICT FAIL/REVIEW** | %OOS+ **43.8% (7/16)** | WFE median **0.307** |
  maxDD OOS xấu nhất **32.4%**. Ngưỡng pre-reg (WFE≥0.5, %OOS+≥70%, maxDD≤50%) → KHÔNG đạt.
- Run fan-out hiện tại (self-completing) CCD phiên này KHÔNG poll được (không mạng) → để chạy xong, đọc
  verdict theo §7. KHÔNG phá run.
