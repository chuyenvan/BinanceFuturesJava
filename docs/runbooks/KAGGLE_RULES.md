# KAGGLE_RULES.md — Rules bắt buộc khi làm việc với Kaggle

> **CCD phải đọc file này TRƯỚC KHI chạy bất kỳ Kaggle job nào.**
> Cập nhật file này khi phát hiện constraint mới. Các quy tắc đến từ bài học thực tế
> (013: 2-CCD-song-song + System.exit bẫy; 013b: slot-limit + 12h kill; 037: jar-rebuild + chia-năm).

---

## 0. LOG/OUTPUT — LƯU VÀO `D:\claudedata` (KHÔNG lưu ổ C)

**Quy tắc bắt buộc cho MỌI task (không chỉ Kaggle):** mọi log file, output trung gian, file tải về
khi xử lý → lưu vào **`D:\claudedata`** (Git Bash: `/d/claudedata`). **KHÔNG lưu vào ổ C** — ổ C
là ổ cài Windows, đã bị full 2 lần → MCP chết, máy phải restart, job đang chạy bị kill.

```bash
# Đường dẫn CÓ DẤU CÁCH → luôn QUOTE:
LOGDIR="/d/claudedata"
mkdir -p "$LOGDIR"
# ví dụ: tải kernel output / log ablation / log validate
... > "$LOGDIR/ablation_104.log" 2>&1
kaggle kernels output chuyendinh/ff40-2023 -p "$LOGDIR/ff40-2023-out"
```

- KHÔNG dùng `/tmp`, `C:\Users\...\AppData\...\Temp`, hay `~/` cho file lớn (đều nằm ổ C).
- File trên 226 thì lưu trên 226 (vd `/home/chuyennd/java/simulator/*.log`) — không kéo về ổ C.
- Chỉ kéo về `D:\claudedata` khi cần đọc/phân tích ở máy local.

---

## 0b. Kaggle CLI TRÊN 226 (upload thẳng, không kéo file lớn về local)

226 CÓ kaggle CLI, nhưng **nằm trong venv** — phải activate trước:

```bash
source ~/envs/xgb-env/bin/activate   # bật venv mới có lệnh kaggle
kaggle --version                     # Kaggle API 1.7.4.5
```

- Credential `~/.kaggle/kaggle.json` (user `chuyendinh`) đã có sẵn trên 226.
- Dùng để **upload dataset lớn thẳng 226 → Kaggle** (vd label ~9GB), tránh scp về máy local rồi mới upload.
- Cú pháp tránh lỗi path: `cd <dir> && kaggle datasets create -p . --dir-mode zip` (dùng `-p .` tương đối).
- **Lưu ý bug path trên LOCAL Windows**: kaggle CLI dựng path tạm lai `D:/...` → `D_/...` làm fail mọi file. Cách sửa ở máy local: `cd /d/claudedata/<dir> && kaggle datasets create -p . --dir-mode zip` (KHÔNG truyền path tuyệt đối `-p D:/...`). Trên 226 (Linux) không dính bug này.

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

## 3b. Mount layout MỚI (đo 2026-07-02, kernel `wfo-env-test`)

Dataset KHÔNG còn mount thẳng `/kaggle/input/<slug>` mà ở **`/kaggle/input/datasets/<user>/<slug>/`**.
Script kernel PHẢI tìm file bằng glob recursive (pattern worker 013 đã đúng sẵn):

```python
manis = glob.glob("/kaggle/input/**/manifest.txt", recursive=True)
jars  = glob.glob("/kaggle/input/**/*.jar", recursive=True)
```

KHÔNG hardcode path tuyệt đối theo slug — layout đã đổi 1 lần, có thể đổi tiếp.

## 3b-bis. Bổ sung mount (đo 2026-07-04, kernel ticker-file-smoke)
- Kaggle dùng SONG SONG 2 layout: dataset cũ ở `/kaggle/input/datasets/<user>/<slug>/`, dataset MỚI TẠO ở
  `/kaggle/input/<slug>/` — TUYỆT ĐỐI không assume prefix, luôn glob recursive từ `/kaggle/input`.
- File `.gz` trong dataset bị **auto-unzip** khi mount → glob phải dùng đuôi `.bin*`; KaggleDataLoader đã
  lường sẵn (ưu tiên .bin rồi .bin.gz).
- Dataset mới tạo: `status ready` + `files` hiện ≠ mount được ngay — có độ trễ vài phút, kernel push sớm sẽ thiếu mount.
- Mọi kernel chạy class Java: PHẢI copy `config.properties` vào CWD trước (Configs static-init đọc CWD, thiếu = NoSuchFileException).
- Loader ticker-file đọc relative `kaggle_data_hpo/` trong CWD → kernel symlink: `os.symlink(<dir mount>, "/kaggle/working/kaggle_data_hpo")` — đã smoke PASS (1440 phút, 1000 symbols).

## 3c. Môi trường Kaggle CPU (đo 2026-07-02)

- Java: **OpenJDK 17.0.18** có sẵn trong image (jar build `--release 11` chạy thẳng, không cần cài).
- RAM 31GB · 4 CPU · `/kaggle/working` 20GB.
- Dataset WFO leak-free đã lên: `chuyendinh/wfo-dataset-wf-leakfree` (market+pred+funding+manifest,
  **md5 cả 3 bin MATCH manifest trên Kaggle** — verify bằng kernel `wfo-env-test` ENV_TEST_PASS).
- TCP 103.157.218.226:3222 từ kernel: OK (tái xác nhận).
- ⚠️ Jobstore WFO hiện tại là Aerospike **LOCAL Oracle** → Kaggle KHÔNG poll được; muốn Kaggle làm WFO worker
  phải set `WFO_STATE_HOST` về 226 thật (xem WFO_ROADMAP §4).

## 3d. GIỚI HẠN concurrency đọc ticker 226 từ Kaggle (đo 2026-07-04)

5 worker SMART_CACHE đồng thời → 226 (15GB RAM) drop connection: AerospikeException Connection Error -8 / EOFException
→ 9/17 job FAIL. 1 worker: OK (test-1, 744s/window). **Quy tắc: tối đa 2 worker Kaggle đọc ticker 226 đồng thời**
(2 đã kiểm chứng OK: DONE 315s/window). Muốn >2 phải chuyển ticker vào dataset file.
**QUAN TRỌNG (đo 2026-07-04): ticker 226 chỉ phủ tới ~2024-04-01** — window cần dữ liệu muộn hơn sẽ
FAIL-FAST "khong co ticker ngay X" (cơ chế TASK-112, đúng thiết kế — thay vì ZERO_TRADES âm thầm).
Đính chính chẩn đoán đợt fleet-5: FAIL gồm CẢ 2 nguyên nhân (quá tải connection + thiếu ticker muộn).
Replication WFO trên Kaggle vì vậy giới hạn w00–w08 (WFO_MAX_WINDOWS=9) chừng nào ticker chưa vào dataset.
Worker hiện xay job FAIL 3s/lần khi thiếu ticker (claim→fail→claim) — cần code: FAIL-FAST thì worker exit (ghi TASK).
Ghi chú thêm: Binance API bị chặn địa lý từ IP Kaggle (restricted location) — exchange-info fetch lỗi nhưng
KHÔNG chặn job (đã có 8 job DONE vượt qua); không được thêm bước nào phụ thuộc Binance API trong kernel.

---

## 3e. HAI DUONG DOC TICKER KHONG BIT-EXACT (do 2026-09-03, GS wave-1)

`TICKER_SOURCE=aerospike` (Oracle doc Aerospike local) va `TICKER_SOURCE=file` (Kaggle doc
`kaggle_data_hpo/ticker_YYYYMMDD.bin*`) **KHONG cho ket qua giong tung byte**, du comment trong
`SimulatorMarketLevelTicker1MStopLoss` ghi "Ket qua Y HET duong doc thang". Da do truc tiep, cung
jar (`f51fd17`), cung profile, cung dataset `wfo_ds_clean`, cung `predwf_map_s1a2`:

| moi truong | TICKER_SOURCE | equity cuoi (C2b, DEV 2022-01..2024-06) |
|---|---|---|
| Oracle | aerospike | **60390** |
| Oracle | file | **60395** |
| Kaggle | file | **60395** |

**Oracle+file == Kaggle+file** (printDone.csv giong het tung dong, PROFILE_HASH `7081c357ca12bdd6`)
=> chenh lech den TU DUONG DOC TICKER, **moi truong Kaggle (JVM/OS/float) VO CAN**.

### Lech bao nhieu va o dau
- **970/970 lenh khop tuyet doi** ve so luong; **dung 1 lenh** khac nhau.
- Lenh do: `FTT BUY` vao `2022-11-09 01:00` (dot FTX sup, data ticker rach nhat).
  Duong aerospike cham SL luc `2022-11-14 11:00` (giu 130h). Duong file KHONG cham nen lenh song tiep
  den loser-time-stop 168h, dong `2022-11-16 01:01`. PnL `-1084.85` vs `-1080.39`.
- Sai lech day len cuoi ky: **+5 USDT / 60390 = 0.008%**. 8/10 quy khop tro 2 chu so thap phan;
  2 quy lech 0.01pp (2022Q4: -3.73 vs -3.72; 2024Q2: -1.42 vs -1.41). maxDD -13.1% va underwater
  93 ngay khong doi.

### Quy tac rut ra — BAT BUOC
1. **Moi so sanh so hoc giua run Oracle va run Kaggle chi tin duoc toi ~0.01%.** Chenh lech nho hon
   nguong nay KHONG duoc coi la tin hieu (khong ket luan "cau hinh A tot hon B" o muc do do).
2. **Muon so byte-identity thi hai run PHAI cung `TICKER_SOURCE`.** Cong `tools/parity_clean.sh` chay
   tren Oracle voi `aerospike` — dung no de so voi run Oracle, KHONG dung de so voi run Kaggle.
3. **Diem neo cua mot vong Kaggle phai duoc do TREN KAGGLE**, khong lay lai so cua Oracle. Vd GS
   wave-1: neo la `id=-1` = **60395**, khong phai 60390.
4. Khi mot fleet Kaggle ra so "lech nhe" so voi Oracle, **kiem gia thuyet ticker-path TRUOC** (chay
   lai tren Oracle voi `TICKER_SOURCE=file`, ticker local o
   `/home/ubuntu/java/simulator/kaggle_data_hpo/daily/`) truoc khi nghi ha tang sai. Phep thu nay
   ton 1 sim ~6 phut.

Bang chung: `/home/ubuntu/java/logs/gs_filetest.log`, `devrun/GS_FILE15/`, `devrun/GS_FILE24/`,
`devrun/C2b/`, kernel `chuyendinh/gs-w1-smoke`.

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

## 5b. Upload dataset LỚN — 2 đòn bẩy (đo thực)

**(1) Đóng gói TAR 1-file** thay vì upload hàng nghìn `.bin.gz`:
- Upload rời hàng nghìn file → lỗi `finalize 502` + rất chậm.
- Cách làm: nén CẢ thư mục thành **1 file `.tar`** (vd `ticker_all.tar` ~10GB) rồi push lên Kaggle.
- Kaggle **tự giải nén** `.tar` thành **1826 file `.bin` uncompressed (~31GB)** trong vài phút.

**(2) Bịt lỗi `'type'` của kaggle CLI 1.7.4.5:**
- CLI `1.7.4.5` dùng blob-upload mới → lỗi `'type'` khi upload.
- Cách sửa: tạo **venv riêng SẠCH** với **`kaggle==1.6.17`** (REST-upload cũ, triệt lỗi blob upload).
- ⚠️ **KHÔNG dùng chung `xgb-env`** — tạo venv riêng để không đụng version gói khác.

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
kaggle kernels output chuyendinh/oi-backfill-worker-1 -p /d/claudedata/k1-out
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
kaggle kernels output chuyendinh/oi-backfill-worker-1 -p /d/claudedata/k1-out

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
| 2026-06-18 | §0 mới: log/output lưu `D:\claudedata`, KHÔNG lưu ổ C (full 2 lần → MCP chết). |
| 2026-06-18 | kaggle CLI đã cấu hình vào PATH ổn định — gọi `kaggle ...` trực tiếp, không cần full path nữa. |
| 2026-07-02 | §3b mount layout mới `/kaggle/input/datasets/<user>/<slug>` + §3c môi trường đo thật (Java 17 sẵn, 31GB/4CPU) — kernel `wfo-env-test` PASS. Kaggle CLI trên Oracle: key trùng 226, auth OK. |
| 2026-09-03 | §3e moi: `TICKER_SOURCE` aerospike vs file KHONG bit-exact (60390 vs 60395, 1/970 lenh) — do bang GS wave-1; nguong tin cay so sanh Oracle-vs-Kaggle ~0.01%. |
