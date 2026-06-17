# KAGGLE_RULES.md — Rules bắt buộc khi làm việc với Kaggle

> **CCD phải đọc file này TRƯỚC KHI chạy bất kỳ Kaggle job nào.**
> Cập nhật file này khi phát hiện constraint mới. Các quy tắc đến từ bài học thực tế
> (013: 2-CCD-song-song + System.exit bẫy; 013b: slot-limit + 12h kill; 037: jar-rebuild + chia-năm).

---

## 1. Slot CPU limit

**Giới hạn: 5 kernel CPU chạy đồng thời** trên toàn account `chuyendinh` (tất cả job, không phân biệt mục đích).

Smoke test 2026-06-13 xác nhận `max_concurrent_running=5` (xem `docs/RUNBOOK_kaggle_multi_cpu.md`).

### Kiểm tra slot trước khi push
```bash
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
FREE=$((5 - USED))
echo "Slot dang dung=$USED / con trong=$FREE"
```

### Rules:
- **Tính tổng slot đang dùng BỞI TẤT CẢ JOB** (037 + 013b + bất kỳ job nào khác).
- Push đúng số kernel = số slot còn trống. Ví dụ: 037 chiếm 3 slot → chỉ push 2 kernel 013b.
- **DỪNG + báo user nếu FREE = 0.** Chờ job khác xong bớt slot rồi mới push.
- **KHÔNG push quá 5 tổng** — bài học từ 2 CCD song song tranh slot (013 NEEDS_HUMAN incident).
- Khi 037 giải phóng slot → push thêm kernel còn lại của 013b (idempotent, tái dùng folder).

---

## 2. Session 12h — Kaggle kill kernel

Kaggle kill kernel CPU sau **12 giờ** (hard limit). Task `RUNNING` bị bỏ dở khi kernel chết.

### Worker tự hồi phục (nếu còn worker sống):
Code `BackfillOiWorker` có `STALE_RUNNING_MS=45'`: worker khác tự cướp task bị bỏ dở sau 45 phút.
Điều này chỉ hoạt động khi **ít nhất 1 worker còn sống**. Nếu TẤT CẢ kernel bị kill → mắc kẹt.

### Xử lý khi tất cả kernel COMPLETE/ERROR nhưng chưa xong:
```bash
# Bước A: reset task RUNNING quá hạn về PENDING (không mất data đã ghi)
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g \
  -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar;target/classes" \
  com.binance.chuyennd.research.oibackfill.BackfillOiMaster --reset-stale

# Bước B: kiểm slot + push lại kernel (idempotent)
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
FREE=$((5 - USED))
cd C:/Users/pc/oi-kaggle/kernels
for i in $(seq 1 $FREE); do kaggle kernels push -p oi-backfill-worker-$i; sleep 2; done
```

### Ước tính vòng lặp:
- 894 symbol × ~2.5 phút/symbol / 5 worker ≈ **~7.5 giờ** (dưới 12h nếu 5 worker đủ slot).
- Nếu chỉ có 2-3 worker → có thể cần 2 vòng push lại.
- Mỗi vòng: push → chờ 11-12h → kiểm DONE count → reset-stale + push lại nếu cần.

---

## 3. Network constraints — QUAN TRỌNG

### Kaggle CÓ THỂ tới (khi `enable_internet=true`):
- **Server 226** (103.157.218.226, Aerospike port 3222): **OK** — đây là backbone cho backfill OI (013) và export feature (037). Kaggle worker đọc/ghi Aerospike 226 trực tiếp.
- **data.binance.vision** (S3 public): **OK** — Kaggle download metrics CSV từ đây (013 BackfillOiWorker).
- **Binance REST API** (api.binance.com, fapi.binance.com): **OK** — dùng cho verify/fetch khi cần.

### Kaggle KHÔNG THỂ tới:
- **Server 242** (production live trading): **KHÔNG accessible từ Kaggle**. 242 chỉ accessible từ 226 (internal network). Mọi push/sync 226→242 phải chạy **TRÊN 226** (SSH job), KHÔNG từ Kaggle.
- **Redis** (nếu có): không liên quan Kaggle — không đụng.
- **BinanceOrderTradingManager, BinanceDataIngestor**: KHÔNG đụng từ bất kỳ đâu.

### Implication:
- Mọi job Kaggle chỉ ghi **226**. Sau khi xong → chạy `PushOiSetsTo242` / sync tool **TRÊN 226** để đẩy sang 242.
- Kaggle job cần `enable_internet=true` mới tới được 226 và vision S3.

---

## 4. System.exit(0) — Bắt buộc

Kaggle kernel **KHÔNG tự thoát** khi `main()` kết thúc nếu có non-daemon thread còn sống.
Aerospike client giữ thread pool → kernel chạy đến timeout 12h nếu không có `System.exit(0)`.

**Bắt buộc:** mọi `main()` chạy trên Kaggle phải kết thúc bằng `System.exit(0)` (hoặc `System.exit(1)` khi lỗi). Xem `BackfillOiWorker`, `ExportFeaturesForPythonTool`, `ExportFundingOiPerCoin` làm mẫu.

Dấu hiệu thiếu `System.exit`: kernel status `RUNNING` mãi sau khi log đã in `HOAN TAT` / `DONE`.

---

## 5. Jar & dataset management

### Rebuild sanitized jar (bắt buộc khi HEAD thay đổi):
Jar trên Kaggle dataset (`chuyendinh/java-run-lc`) là **snapshot cố định** — KHÔNG tự cập nhật.
Nếu code thay đổi (thêm feature, fix bug), phải rebuild + upload lại.

```bash
# 1. Build jar từ HEAD (Windows Git Bash)
cd /e/educa/source/github/20260415/BinanceFuturesJava
mvn package -DskipTests -q   # hoặc build script của project

# 2. Sanitize (PrivateConfig → placeholder, loại bỏ secret)
# Xem RUNBOOK_kaggle_multi_cpu.md hoặc docs/reports/013.md phần "sanitize"

# 3. Upload lên Kaggle dataset
cd C:/Users/pc/java-run-lc-stage
kaggle datasets version -p . -m "rebuild HEAD <commit>"
```

### Kiểm tra jar trên dataset:
```bash
kaggle datasets files chuyendinh/java-run-lc 2>&1
```

### Kernel folder convention (`C:\Users\pc\oi-kaggle\kernels\`):
- `oi-backfill-worker-{1..5}/` — 013b OI backfill workers
- Mỗi folder gồm: script `.py` (gọi `java -cp jar MainClass`) + `kernel-metadata.json`
- `kernel-metadata.json`: `enable_internet=true`, `dataset_sources=["chuyendinh/java-run-lc"]`
- `is_private=true` — luôn luôn

---

## 6. Test 1 kernel TRƯỚC khi push fleet

**Bắt buộc** khi lần đầu chạy một loại job mới trên Kaggle (hoặc sau thay đổi lớn).
Lý do: bài học 013 — 2 CCD song song đều test 1 kernel PASS rồi mới hội tụ, tránh nhân lỗi ra fleet.

```bash
# Push 1 kernel test với symbol/range nhỏ
kaggle kernels push -p oi-backfill-worker-1

# Poll trạng thái
kaggle kernels status chuyendinh/oi-backfill-worker-1

# Khi COMPLETE, lấy log kiểm tra
kaggle kernels output chuyendinh/oi-backfill-worker-1 -p /tmp/k1-out
# Log Kaggle là JSON: parse field "data", KHÔNG parse đầu dòng trực tiếp
```

**Tiêu chí pass test 1 kernel:**
- Kernel COMPLETE (không ERROR, không stuck RUNNING mãi).
- Log có `HOAN TAT` / `DONE` với số record/symbol hợp lý.
- `System.exit(0)` hoạt động (kernel COMPLETE đúng thời gian, không kéo đến 12h).
- Kaggle tới được 226 + ghi OK (kiểm Aerospike sau).

---

## 7. Multi-CCD conflict prevention

**Bài học 013:** 2 CCD headless chạy song song cùng task, cả hai test 1 kernel thành công, cả hai sắp push fleet → phát hiện kịp → NEEDS_HUMAN. Nếu không phát hiện sẽ có 10 kernel tranh 5 slot.

### Rules:
- **Chỉ 1 CCD được push fleet cho cùng 1 job.** Không có 2 session làm TASK-013b cùng lúc.
- Trước khi push fleet: kiểm `oi_backfill_done` count trên 226 xem có instance khác đang chạy không.
- Nếu phát hiện có worker khác đang tranh queue → `NEEDS_HUMAN`, báo ngay, KHÔNG tự giải quyết.
- Dùng queue Aerospike làm nguồn sự thật duy nhất (idempotent, generation-lock chống race).

---

## 8. Monitor tiến độ

### Đếm progress (dùng cho job queue-based như 013b):
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 -o BatchMode=yes root@103.157.218.226 'timeout 20 bash -c "
  echo -n DONE=; asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
  echo -n QUEUE=; asinfo -p 3222 -v \"sets/ticker/oi_backfill_queue\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
"' 2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
```

### Đếm kernel status:
```bash
kaggle kernels list --mine --page-size 20 2>&1 | grep -E "oi-backfill|ff40|RUNNING|COMPLETE|ERROR"
```

### Log format cần lưu ý:
- Log Kaggle download về là **JSON** (`[{"stream_name":..., "data":"<nội dung log>"}]`).
- Timestamp nằm **BÊN TRONG field `data`**, KHÔNG ở đầu dòng JSON.
- Parse bằng regex trên nội dung `data`, không split theo newline JSON.

---

## 9. Checklist bắt buộc TRƯỚC KHI push fleet

```
[ ] 1. Đọc KAGGLE_RULES.md (file này) — XONG nếu bạn đang đọc
[ ] 2. Kiểm slot: FREE = 5 - USED >= 1 (DỪNG nếu FREE=0)
[ ] 3. Jar trên chuyendinh/java-run-lc khớp với HEAD cần chạy
[ ] 4. Kernel folder tồn tại + kernel-metadata.json đúng (enable_internet, dataset_sources)
[ ] 5. Test 1 kernel đã PASS (nếu là job type mới hoặc sau thay đổi lớn)
[ ] 6. Không có CCD khác đang chạy cùng job này
[ ] 7. Aerospike 226 state lành (queue rỗng hoặc ở trạng thái kỳ vọng)
[ ] 8. Biết cách xử lý 12h kill (--reset-stale + push lại)
```

---

## 10. Quick reference — Lệnh hay dùng

```bash
# Kiểm slot
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0); echo "USED=$USED FREE=$((5-USED))"

# Push N kernel
for i in $(seq 1 $N); do kaggle kernels push -p oi-backfill-worker-$i; sleep 2; done

# Status fleet
kaggle kernels list --mine --page-size 20 2>&1 | grep -E "oi-backfill|ff40"

# Lấy log 1 kernel
kaggle kernels output chuyendinh/oi-backfill-worker-1 -p /tmp/k1-out

# Reset stale tasks (sau 12h kill)
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar;target/classes" \
  com.binance.chuyennd.research.oibackfill.BackfillOiMaster --reset-stale

# Đếm progress OI backfill
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 -o BatchMode=yes root@103.157.218.226 \
  'timeout 15 bash -c "echo -n DONE=; asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\""' \
  2>&1 | grep -vE "post-quantum|store now"
```

---

## Lịch sử cập nhật

| Ngày | Thay đổi |
|---|---|
| 2026-06-17 | Tạo mới — tổng hợp từ 013/013b/037 + RUNBOOK_kaggle_multi_cpu.md |
| 2026-06-17 | TASK-102: xác nhận slot limit = 0/5 đang dùng (test COMPLETE trong 2s, SLOT_TEST_OK) |
