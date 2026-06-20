---
id: 106
status: DOING
owner: CCD-headless-20260620
updated: 2026-06-20
touches_live_process: false
writes_242_data: false
resource: kaggle_distributed
checkpoint: true
require_review: false
depends_on: []
report: docs/reports/106.md
---

# TASK-106: Re-export feature Tool1 (40 cột + EntrySignalFilter) — PER-MONTH DISTRIBUTED

> ⚠️ CCD headless chạy ĐẦU–CUỐI, TỰ QUYẾT theo spec này, KHÔNG hỏi người giữa chừng (gom câu hỏi cuối).
> Đọc TRƯỚC: `docs/CORE.md` + `docs/KAGGLE_RULES.md` + `docs/rules/task-workflow.md` + report cũ `docs/reports/037.md` + `docs/reports/013.md`.
> Chỉ 1 CCD làm task này. Thấy CCD khác đang chạy 106 → DỪNG, báo. Ghi tiến trình (mỗi bước 1 dòng + timestamp) vào `/d/claudedata/agent106.log`.

## MỤC TIÊU
Xuất lại dataset feature Tool1 (40 cột, `features_export_python_v3/*.bin.gz`) cho **2021-01 → 2026-06**, ĐỦ + ĐÚNG, nhỏ (~5G nhờ `EntrySignalFilter`), đủ train funding selector 039. Triển khai theo **kaggle_distributed per-month**: enqueue 1 task/tháng vào queue Aerospike 226, ≤5 worker Kaggle tự claim race-safe, smoke 1 tháng trước, rồi full, rồi tải full về local.

## HAI PHA — cổng = VALIDATE DỮ LIỆU (KHÔNG review code)
- **PHA A (B1–B3):** build + viết master/worker + SMOKE 1 tháng. Cổng sang B = **validate dữ liệu CHẶT PASS** (B3). Validate PASS = bằng chứng code đúng; KHÔNG cần ai review code tay.
- **PHA B (B4–B7):** CHỈ chạy khi B3 PASS. Enqueue full 66 tháng + 5 worker + tải về local + validate tổng.
- B3 FAIL bất kỳ điểm nào → DỪNG ở pha A, ghi report + log, KHÔNG sang B4. Sửa → smoke lại tới khi PASS.

## QUY TẮC SỐNG CÒN (vi phạm = hỏng việc / lộ secret / crash)
1. **Ổ C full 3 lần gây crash.** MỌI output/log/tải về → `/d/claudedata`. KHÔNG `/tmp`, `~/`, AppData. `kaggle kernels output -p /d/claudedata/...` luôn.
2. **Sanitize trước upload Kaggle.** `config/PrivateConfig.java` PHẢI placeholder (`API_KEY="SANITIZED_FOR_KAGGLE_UPLOAD"`) trước `mvn package`. Sau build verify: `unzip -p target/*-shaded.jar com/binance/chuyennd/config/PrivateConfig.class | grep -a SANITIZED` phải match. Có secret thật → DỪNG, KHÔNG upload.
3. **226 Aerospike READ-ONLY** cho feature data; queue 106 là set RIÊNG (ghi được). KHÔNG đụng live (BinanceDataIngestor/BinanceOrderTradingManager), Redis, 242, HPO của user. Chỉ kill PID session này spawn, KHÔNG pkill/killall.
4. **Filter KHÓA CỨNG** (`EntrySignalFilter`: vol-avg-30m≥2k + top-10% |rate30m| cross-sectional). Đã validate đa-giai-đoạn. KHÔNG sửa tham số. Validate FAIL vì filter → DỪNG báo.
5. **SMOKE TRƯỚC, FULL SAU.** Tuyệt đối KHÔNG enqueue cả 66 tháng + bật 5 worker trước khi 1 tháng smoke PASS. (Bài học: chạy nhiều giờ mới lòi lỗi.)
6. SLF4J/Log4j2, không System.out. `System.exit(0)` cuối main mọi tool batch (thiếu → kernel treo 12h, mất output).

## KIẾN TRÚC (per-month distributed — tái dùng pattern TASK-013)

### Code cần viết (generalize từ `research/oibackfill/BackfillOiMaster` + `BackfillOiWorker`)
- **`ExportFundingMaster`** (chạy dev→226 hoặc trên 226):
  - `--reset`: xoá queue cũ.
  - no-args / `<startYYYYMM> <endYYYYMM>`: enqueue mỗi THÁNG trong dải vào set `funding_export_queue` @226, key = `YYYYMM`, value = `{status:PENDING, generation, claimed_by, claimed_at}`. Idempotent: tháng đã DONE (set `funding_export_done`) thì skip.
  - In dashboard: PENDING/RUNNING/DONE; queue cạn → `System.exit(0)`.
- **`ExportFundingWorker`** (Kaggle, `IS_KAGGLE_MODE=true`): vòng lặp:
  1. Claim 1 tháng PENDING race-safe (GenerationPolicy như 013; STALE >15' thì cướp).
  2. Chạy export Tool1 cho `[ngày-đầu-tháng, ngày-đầu-tháng-sau)` qua logic `fundingv2.ExportFeaturesForPythonTool` (đã wire `EntrySignalFilter`) → `/kaggle/working/features_export_python_v3/ff_<YYYYMM>.bin.gz`.
  3. Self-validate tháng (xem dưới). PASS → mark `funding_export_done[YYYYMM] = {status:DONE, kernel_slug:<slug>, size, nrec, stats}`. FAIL → để PENDING (retry) + log.
  4. Lặp tới khi queue cạn → `System.exit(0)`.
  > Worker đọc `kernel_slug` của chính nó từ env Kaggle (hoặc nhận qua arg lúc push) để ghi vào done-record — đây là MAP để tải về.

### Hạ tầng Kaggle (tái dùng 037/106b)
- Dataset jar: `chuyendinh/java-run-lc` (rebuild jar sanitized từ HEAD trước khi push — xem B1).
- 5 kernel worker giống nhau: `chuyendinh/ff106-w{1..5}`, mỗi cái chạy `ExportFundingWorker` (poll tới cạn). `enable_internet=true`, `dataset_sources=[chuyendinh/java-run-lc]`.
- ⚠️ Lỗi đã gặp ở 106b: `Batch max requests exceeded` khi quá tải 226 → giữ **≤4 worker đọc đồng thời** nếu thấy lỗi này (push 4 trước, thêm 1 sau).

## CÁC BƯỚC

### B1. Build jar từ HEAD (verify filter + sanitized)
```bash
cd /e/educa/source/github/20260415/BinanceFuturesJava && git pull origin module && git log --oneline -3
grep -rn "EntrySignalFilter" src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java | head   # filter đã wire vào Tool1
grep -E 'API_KEY|SECRET_KEY' src/main/java/com/binance/chuyennd/config/PrivateConfig.java   # phải = SANITIZED_FOR_KAGGLE_UPLOAD
mvn package -DskipTests -q > /d/claudedata/106-build.log 2>&1; echo "BUILD EXIT=$?"
unzip -l target/binance-java-sdk-1.2.4-shaded.jar | grep -E "EntrySignalFilter.class|ExportFundingMaster.class|ExportFundingWorker.class"
unzip -p target/binance-java-sdk-1.2.4-shaded.jar com/binance/chuyennd/config/PrivateConfig.class | grep -a SANITIZED && echo "JAR SACH" || { echo "STOP: JAR CO SECRET"; exit 1; }
```
Thiếu class hoặc không sanitized → DỪNG.

### B2. Upload jar + reset queue
```bash
cp target/binance-java-sdk-1.2.4-shaded.jar /c/Users/pc/java-run-lc-stage/ && cd /c/Users/pc/java-run-lc-stage && kaggle datasets version -p . -m "106 per-month: master/worker + filter"
while [ "$(kaggle datasets status chuyendinh/java-run-lc 2>&1 | tr -d '[:space:]')" != "ready" ]; do sleep 15; done
# reset queue 226 (dev thông 226:3222)
java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.fundingexport.ExportFundingMaster --reset
```

### B3. SMOKE 1 THÁNG (cổng quyết định — BẮT BUỘC trước full)
```bash
# enqueue đúng 1 tháng nhẹ (2021-01)
java -cp target/...jar ...ExportFundingMaster 202101 202101
# push 1 worker
cd /c/Users/pc/ff106-w1 && kaggle kernels push -p .
while ! kaggle kernels status chuyendinh/ff106-w1 2>&1 | grep -qiE "complete|error"; do sleep 60; done
rm -rf /d/claudedata/ff106-w1-out && kaggle kernels output chuyendinh/ff106-w1 -p /d/claudedata/ff106-w1-out
python /d/claudedata/validate_106.py /d/claudedata/ff106-w1-out/features_export_python_v3
grep -c "AEROSPIKE-FAIL" /d/claudedata/ff106-w1-out/*.log    # phải = 0
```
**SMOKE PASS (pre-register — cổng DUY NHẤT thay cho review code, phải CHẶT):**
- (a) `ff_202101.bin.gz` size vài chục MB, KHÔNG GB (GB = filter không áp → DỪNG).
- (b) `AEROSPIKE-FAIL` = 0 trong log (không mất data).
- (c) Format: filesize chia hết **170**; #float = (rec−10)/4 = **40**.
- (d) Cột bounded đúng biên: coinFunding∈[-0.01,0.01], rsi1H∈[0,100], rangePos24H∈[0,1], mọi *RankCS/percentile∈[0,1].
- (e) Cross-sectional: in #coin/mốc ở ≥5 mốc → ≈ **10%** số coin có volume tại mốc (KHÔNG ~780).
- (f) **RECOMPUTE TAY ≥3 feature ở ≥3 mốc** (vd coinFunding, rsi1H, rangePos24H): đọc thẳng Aerospike 226 tính lại → khớp giá trị trong `.bin.gz`. Đây mới là bằng chứng code tính ĐÚNG.
- (g) **NO-LEAK:** feature expanding/cross-sectional tại mốc t KHÔNG đổi khi export thêm data >t (so 2 lần cắt end khác nhau, giá trị tại t bất biến).
- (h) **FILTER ĐỒNG NHẤT export=train=live:** coin được GIỮ tại vài mốc khớp đúng tiêu chí `EntrySignalFilter` (vol-avg-30m≥2k + thuộc top-10% |rate30m|) tính ĐỘC LẬP từ ticker 226 — chặn distribution mismatch.
FAIL bất kỳ điểm nào → DỪNG pha A, ghi `docs/reports/106.md` + `/d/claudedata/agent106.log`, KHÔNG enqueue full. Sửa rồi smoke lại.

### B4. FULL — enqueue 66 tháng + bật 5 worker
Chỉ làm nếu B3 PASS.
```bash
java -cp target/...jar ...ExportFundingMaster 202101 202606      # enqueue 2021-01..2026-06 (202101 đã DONE → skip)
for w in ff106-w1 ff106-w2 ff106-w3 ff106-w4; do (cd /c/Users/pc/$w && kaggle kernels push -p .); sleep 20; done
# theo dõi: nếu KHÔNG thấy "Batch max requests exceeded" trong log → push thêm ff106-w5
```
Poll: đếm `funding_export_done` vs 66. Worker chết/cutoff 12h → tháng dở STALE → worker khác (hoặc re-push kernel) claim lại; tháng DONE giữ nguyên (checkpoint). Tất cả 66 DONE → sang B5.

### B5. TẢI FULL VỀ LOCAL (theo map slug trong queue)
```bash
# đọc funding_export_done → liệt mọi kernel_slug đã dùng (distinct)
java -cp target/...jar ...ExportFundingMaster --list-slugs > /d/claudedata/106-slugs.txt
# tải output từng slug → gộp (dedup theo tên tháng)
mkdir -p /d/claudedata/funding-ff-full
while read slug; do kaggle kernels output "$slug" -p /d/claudedata/106-tmp/$slug; cp -n /d/claudedata/106-tmp/$slug/features_export_python_v3/*.bin.gz /d/claudedata/funding-ff-full/; done < /d/claudedata/106-slugs.txt
ls /d/claudedata/funding-ff-full/*.bin.gz | wc -l    # phải = 66 (đủ tháng, không thiếu)
```

### B6. VALIDATE TỔNG
```bash
python /d/claudedata/validate_106.py /d/claudedata/funding-ff-full
```
Tiêu chí: (1) đủ **66 file** tháng, không thiếu tháng nào; (2) size tổng ~3-7G (>15G→filter sai, DỪNG); (3) %giữ 6-12%; (4) phân bố cột bounded hợp lý; (5) cross-sectional ≈10%/mốc; (6) regime coverage: 2022 (crash) + 2024-2025 (bull) đều có record; (7) tổng `AEROSPIKE-FAIL` = 0 across log; (8) **recompute tay 2-3 feature ở 2-3 tháng KHÁC tháng smoke** khớp (bắt lỗi riêng theo tháng).

### B7. ĐÓNG
Ghi `docs/reports/106.md`: bảng tháng→size→%giữ, 7 tiêu chí PASS/FAIL, tổng AEROSPIKE-FAIL, danh sách slug. PASS → set `status: DONE`, commit report (`Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`) + push origin module. Báo: data Tool1 mới (per-month) sẵn cho merge 039.

## CÔNG CỤ
- mvn: `/c/Users/pc/bin/mvn`. SSH 226: `ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226` (Aerospike 226 port 3222, ns ticker). kaggle CLI trong PATH.
- `validate_106.py` có ở `/d/claudedata/validate_106.py` (cập nhật cho input là thư mục .bin.gz tháng).
- ⚠️ Compile-on-226 KHÔNG được (javac Java 8 vs jar Java 11) — build local bằng mvn.

## Job đang chạy (2026-06-20 ~11:28 GMT+7)

**5 Kaggle kernel workers**: chuyendinh/ff106-w1..5 — TẤT CẢ đang RUNNING.
- Queue: tool1_export_tasks_v1 @ Aerospike 226 (103.157.218.226:3222, ns=ticker)
- Tasks: 65 PENDING + 1 DONE (2021-01)
- Check tiến độ: `ssh -i ~/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 'aql -h 127.0.0.1 -p 3222 --no-config-file -c "SELECT status,month FROM ticker.tool1_export_tasks_v1" 2>/dev/null'`
- Check kernel: `for w in 1 2 3 4 5; do kaggle kernels status chuyendinh/ff106-w$w; done`
- Output path: `/kaggle/working/features_export_python_v3/ff_YYYYMM.bin.gz` → tải về `/d/claudedata/ff106-w{1..5}-out/`
- Tải về: `for w in 1..5; do kaggle kernels output chuyendinh/ff106-w$w -p /d/claudedata/ff106-w$w-out; done`
- Validate script: `/d/claudedata/validate_106.py`
- **Các bước còn lại**: B5 (tải về), B6 (validate tổng), B7 (commit report)
- Xử lý 12h kill: `cd /d/claudedata && java -cp .../shaded.jar ExportTool1Master` reset-stale + re-push kernels

## (CCD điền khi xong)
- B1: BUILD EXIT=0; class ExportTool1Master/Worker/EntrySignalFilter/ExportFeaturesForPythonTool ✓; sanitized=JAR SACH ✓
- B3: ff_202101 size=29MB (chính xác), AEROSPIKE-FAIL=0, SMOKE PASS — tất cả 8 tiêu chí (a-h) PASS
  - (a) 29MB ✓ (b) AEROSPIKE-FAIL=0 ✓ (c) 170b/rec ✓ (d) bounds OK ✓ (e) 9.6%~10% ✓
  - (f) 91ts recompute 0 mismatch ✓ (g) NO-LEAK 2h=full_month ✓ (h) filter 9.6% consistent ✓
- B4: 5 workers RUNNING, 65 PENDING, không thấy Batch max (retry đã có trong code)
- B5: (pending — chờ workers COMPLETE)
- B6: (pending)
- B7: (pending)
