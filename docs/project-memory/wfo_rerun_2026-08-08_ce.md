> ⚠️ **CẬP NHẬT LỚN ~20:40 ICT 08/08: Oracle CRASH (OOM) → PIVOT sang chạy label export TRÊN KAGGLE.**
> Job label chạy trên Oracle qua `ce bg_run` (mục 1–8 bên dưới) **ĐÃ CHẾT theo box** — không còn giá
> trị. Trạng thái mới nhất ở **mục 9 (đọc mục này TRƯỚC)**. Mục 1–8 giữ lại làm hồ sơ lỗi.
> Liên quan: `claude/wfo_data_status.md`, `claude/wfo_label_merge_bug.md`, `claude/wfo_kaggle_parallel_plan_2026-08-08.md`.

---

## 9. 🟢 PIVOT KAGGLE — label export sharded (mới nhất, 08/08 ~22:10 ICT)

### 9.1. Vì sao pivot
Uni báo Oracle **lại crash, khả năng OOM RAM** dù chỉ có 2 job compute chạy ("khả năng xử lý RAM
không tốt"). Xác nhận gián tiếp: lúc ~20:15 đo `TCP 161.118.212.3:22` = FAIL nhưng ping OK = box đang
reboot (KHÔNG phải lỗi CRLF `ce.cmd` — đã đo lại ce.cmd vẫn 39 CRLF/0 LF). ⇒ Job label `bg_run` trên
Oracle **chết theo box**, không phải "vẫn chạy" như phỏng đoán ở mục 8.

**Quyết định (Uni chốt):** đưa TOÀN BỘ compute label sang Kaggle, Oracle **chỉ phục vụ Aerospike read**.
Lý do kỹ thuật: crash là do **Java heap 12GB tại chỗ** (compute), KHÔNG phải do serving read (probe
4 luồng đọc Oracle 0 lỗi). Chạy shard trên Oracle = đắp lại đúng heap đã làm sập ⇒ loại. Không dùng
Oracle cho compute nữa kỳ này.

### 9.2. Bằng chứng probe (đo thật, không suy đoán)
Kernel `chuyendinh/label-export-probe` (dataset `chuyendinh/label-export-jar`, jar
`binance-label-1.2.4.jar` 99.6MB) chạy XONG từ Kaggle đọc thẳng Aerospike Oracle `161.118.212.3:3222`:
- range 1 tháng 20210101→20210201: **wall 426s (7.1 phút)**, 3.461.567 dòng, 82 coin, **8121 rec/s**.
- **0 dòng log lỗi/timeout Aerospike** ⇒ kết nối qua internet ỔN ĐỊNH (với 1 kernel/4 luồng).
- `java exit=0`, merge quý sạch: `"3461567 dòng ĐÃ ĐỐI CHIẾU KHỚP"`, KHÔNG còn `.partN.pb` mồ côi.
  ⇒ **jar `binance-label-1.2.4.jar` ĐÃ có bản vá merge race** (countRowsInPb reconcile chạy đúng).
- lifecycle nạp **698 symbol** OK từ Kaggle. NO_VALIDATE=1, LABEL_THREADS=4, LABEL_STEP_MIN=1, horizon short {4h,12h,24h,72h}.

### 9.3. 🔴 Full range KHÔNG vừa 12h hard-kill của Kaggle ⇒ BẮT BUỘC shard
Oracle full = 636.5M dòng / 12.8h *(Aerospike local)*. Qua internet ở 8121 rec/s: `636.5M/8121 ≈ 21.8h`
→ 1 kernel full range chắc chắn bị Kaggle giết ở 12h, mất output. **Đã shard theo NĂM: 6 kernel.**

| kernel id (Kaggle) | range [start, end) | thư mục máy Uni |
|---|---|---|
| `chuyendinh/label-export-2021`   | 20210101 → 20220101 | `C:\Users\pc\label-shards\label-export-2021` |
| `chuyendinh/label-export-2022`   | 20220101 → 20230101 | `...\label-export-2022` |
| `chuyendinh/label-export-2023`   | 20230101 → 20240101 | `...\label-export-2023` |
| `chuyendinh/label-export-2024`   | 20240101 → 20250101 | `...\label-export-2024` |
| `chuyendinh/label-export-2025`   | 20250101 → 20260101 | `...\label-export-2025` |
| `chuyendinh/label-export-2026h1` | 20260101 → 20260701 | `...\label-export-2026h1` |

Mỗi folder = `run.py` (copy từ `label-export-kernel/run.py`, chỉ đổi 2 default `LABEL_START`/`LABEL_END`)
+ `kernel-metadata.json` (id riêng, `dataset_sources=["chuyendinh/label-export-jar"]`, internet=on, CPU).
⚠️ **BOM bẫy:** Windows PowerShell `Set-Content -Encoding UTF8` chèn BOM ⇒ kaggle push lỗi
`Unexpected UTF-8 BOM`. Phải ghi bằng `[System.IO.File]::WriteAllText(path,txt,New UTF8Encoding($false))`.

### 9.4. 🔴 BÀI HỌC LỚN: Oracle Aerospike chỉ chịu ~3 kernel ĐỒNG THỜI (không phải số luồng)
Push cả 6 lúc ~20:40: Kaggle cap **5 session CPU đồng thời** (2026h1 bị chặn
`Maximum batch CPU session count of 5 reached`) ⇒ 5 kernel RUNNING = **20 luồng batch-read** đập Oracle.
Lúc ~21:42 ICT **2023 và 2024 FAIL**, đọc error.log:

```
Aerospikeexception$Connection: Error -8 ... 161.118.212.3 3222: java.io.EOFException
batch read failed after 4 retries: chunk start=... keys=720
```

`EOFException` = **server Aerospike đóng socket** khi bị quá tải connection. Đặc điểm quyết định:
- 2 kernel FAIL đều chết ở **chunk ĐẦU TIÊN** chúng đọc (2024: 20240101 07:00, wall 15s; 2023: 20230104).
- **2021/2022/2025 (đã kết nối trước) vẫn RUNNING bình thường.**
- Re-push 2024 với **LABEL_THREADS=2** (thay vì 4) → **VẪN fail y hệt** ở chunk đầu, cả 2 luồng EOF
  ngay retry 1/4. ⇒ **Giảm số luồng KHÔNG cứu được.**

**Kết luận (đo được, không suy đoán):** giới hạn là **SỐ KERNEL đồng thời**, không phải luồng/kernel.
Oracle Aerospike chịu được đúng **~3 kernel đang bám** (12 luồng đã mở); kernel **thứ 4 vào bị drop
connection ngay** (không mở nổi thêm — nghi cạn proto-fd / RAM index / connection cap phía server).
⇒ **CAP CỨNG = 3 kernel RUNNING đồng thời.** Muốn chạy shard mới phải **CHỜ 1 kernel xong** (serial),
không thả khi đang có 3. Luồng để nguyên 4/kernel (nhanh, tránh chạm 12h) miễn là ≤3 kernel.

### 9.5. Trạng thái + cơ chế tự thả (chốt lúc ~22:10 ICT) — ⚠️ XEM 9.9, KẾ HOẠCH NÀY HỎNG
- **RUNNING (3, đúng cap) lúc 22:10:** `label-export-2021`, `-2022`, `-2025`.
- **Cần chạy lại/chưa chạy (3):** `-2023` (ERROR), `-2024` (ERROR), `-2026h1` (chưa push). Đã trả
  LABEL_THREADS về 4. **KHÔNG push ngay** vì đang đủ 3 RUNNING.
- ~~**Launcher tự động** (scheduled task `Launcher label shards Kaggle (cap 3 đồng thời)`, cron mỗi giờ
  phút :17): mỗi lần fire → nếu Oracle 3222 sống VÀ RUNNING<3 VÀ còn shard chưa xong → push ĐÚNG 1
  shard (ưu tiên năm nặng). Idempotent (không đụng RUNNING/COMPLETE). Khi đủ 6 COMPLETE → tự xoá.~~
  **→ SAI, xem 9.9: launcher này KHÔNG THỂ chạm máy Uni, không bao giờ push được.**
- **Oracle:** `TCP 3222 = open`, `TCP 22 = open` (box đã reboot xong). Ping=False chỉ là ICMP bị chặn.
- **Trigger verify 07:00 ICT 09/08** (`Verify + gộp label export...`): sáng mai verify+gộp (xem 9.6).
  ⚠️ Trigger verify **cũng chạy dưới dạng scheduled task trong cloud** ⇒ nhiều khả năng **cũng không
  chạm được máy Uni** để `kaggle kernels output` — xem 9.9, cần kiểm lại trước 07:00.

### 9.6. VIỆC CÒN LẠI (theo thứ tự) — cái "đi tiếp"
1. ~~Launcher tự đưa nốt 2023/2024/2026h1 chạy theo cap 3 (không cần tay).~~ **KHÔNG XẢY RA** — xem 9.9.
   Uni cần tự push tay (hoặc chạy Cowork task "on your computer") 2023/2024/2026h1 khi RUNNING<3.
2. Với mỗi kernel **COMPLETE**: `kaggle kernels output <id> -p <thư mục>`. **VERIFY bằng SỐ**
   (KHÔNG tin log "✅ Xong toàn bộ" — bài học mục 2.4/6):
   - log kernel `java exit : 0` và `dong log co dau hieu loi/timeout Aerospike: 0`.
   - output **KHÔNG còn `.partN.pb`** (còn part = lệch dòng, shard FAIL).
   - đủ file quý (2021→2025 mỗi năm 4 file, 2026h1 = 2 file), **không file 0 byte**.
   - `.meta.json` → `emittedRows`; cộng 6 shard kỳ vọng ~636 triệu dòng.
3. Đủ **6 shard PASS** → gộp 22 file quý `.pb` (~27GB, probe cho ~42 byte/dòng) thành dataset
   `funding-label-full-1m`, **bump version**, push. ⚠️ quota ~63.8/100GB → +27GB sát cap; có thể phải
   dọn dataset cũ / xoá output kernel sau khi gộp.
4. Xong label → STAGE 1 selector-predict-1m (xem `wfo_kaggle_parallel_plan`).

### 9.7. Cách chạm hạ tầng kỳ này (KHÔNG dùng Oracle CE/SSH cho label)
- Compute label = **Kaggle kernel**, điều khiển bằng `kaggle` CLI **trên máy Uni** qua Desktop Commander
  (`start_process` shell `powershell.exe`, timeout≤55000ms). KHÔNG cần Oracle SSH/CE cho label.
- Oracle chỉ là **nguồn Aerospike read** (`161.118.212.3:3222`, key config `AEROSPIKE_HOST_226` vì
  `AEROSPIKE_READ_CLUSTER=226`). `run.py` tự ép `AEROSPIKE_HOST_226`=IP public Oracle + preflight TCP
  fail-fast nếu Aerospike chết ⇒ không chạy vô ích 12h.
- ⚠️ Theo dõi Oracle: `Test-NetConnection 161.118.212.3 -Port 3222`. Nếu nhiều shard cùng EOFException
  → đang vượt cap 3, giảm số kernel đồng thời.

### 9.8. Các việc treo KHÁC (vẫn phải xử TRƯỚC khi chạy WFO thật) — xem mục 5
`ExportFundingLabel` exit 0 khi BLOCKED (2.2, chưa sửa — probe/shard này lifecycle nạp OK nên không kích
hoạt, nhưng bug vẫn còn); WFO jobstore bẩn + trỏ box 226 retire; Oracle repo không phải git ⇒
`code_sha=unknown` làm `WfoDataset.export()` throw ở bước build_ds. 3 cái này thuộc STAGE build_ds/WFO,
KHÔNG chặn label.

### 9.9. 🔴 PHÁT HIỆN 09/08 ~04:19 ICT (chạy launcher lần đầu): scheduled task KHÔNG BAO GIỜ chạm được máy Uni — kế hoạch 9.5/9.6-mục-1 SAI TỪ GỐC

**Đo được, không suy đoán:** Launcher `Launcher label shards Kaggle (cap 3 đồng thời)` (trig
`trig_0139FAS8yLz6QYh6m9a2GQnK`, cron `17 * * * *`, tạo lúc 15:17:31 UTC = 22:17 ICT 08/08) đã tới ít
nhất phiên fire lúc ~21:19 UTC (~04:19 ICT 09/08) — tức đã fire ~6 lần (22:17→03:17 ICT) mà KHÔNG lần
nào push được gì. Lý do gốc: **session được tạo bởi scheduled task chạy trong cloud KHÔNG BAO GIỜ có
device bridge tới máy Uni** — không phải do Uni tắt máy/đóng app như giả định sai ở 9.6 cũ. Kiểm bằng
`ToolSearch` (không tìm thấy công cụ `mcp__remote-devices__*` nào) và `RefreshMcpTools` (server
`remote-devices` không xuất hiện trong danh sách server đã kết nối) — cả hai đều trống, xác nhận đây
là giới hạn CỐ ĐỊNH của mọi scheduled task chạy trong cloud, KHÔNG phải trạng thái tạm (app đóng/mở).
Cloud sandbox này cũng không có `kaggle` CLI/credentials cài sẵn (`which kaggle` rỗng, không có
`~/.kaggle`) nên không có đường vòng nào để tự push từ cloud.

**Hệ quả:** 3 shard `-2023`, `-2024`, `-2026h1` **CHƯA được ai push lại** từ lúc chốt 22:10 ICT 08/08
tới giờ (~6 giờ đứng yên). Trigger verify 07:00 ICT 09/08 (`Verify + gộp label export...`) — nếu cũng
là scheduled task cloud thuần — **cũng sẽ không chạm được máy Uni** để chạy `kaggle kernels output`,
nên khả năng cao sáng mai cũng báo "không chạm được" thay vì verify+gộp thật.

**Kết luận / việc cần Uni quyết:**
- Cơ chế "launcher tự thả shard qua scheduled task + Desktop Commander" **không khả thi trên nền tảng
  hiện tại**, không phải bug sửa được — cần đổi cách làm, không phải đổi cron hay retry thêm.
- Lựa chọn khả thi: (a) Uni tự mở Claude desktop app và chạy tay lệnh push khi rảnh (dựa theo mục 9.6
  bước 1 + bảng cap 3 ở 9.4); (b) Uni tự bấm push kernel Kaggle trực tiếp (không qua Claude) theo đúng
  thứ tự ưu tiên 2024>2025>2023>2022>2021>2026h1, tôn trọng cap 3 RUNNING; (c) hỏi rõ nếu có cách chạy
  Cowork "on your computer" theo lịch thật (không phải scheduled-task-in-cloud) thì dùng cách đó.
- **Đã KHÔNG xoá trigger launcher** (chưa được Uni xác nhận) — nhưng nó sẽ tiếp tục fire vô nghĩa mỗi
  giờ, tốn quota, cho tới khi Uni tắt (`update_trigger enabled=false`) hoặc xoá hẳn.
