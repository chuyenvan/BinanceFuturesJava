# RUNBOOK — Fan-out worker CPU lên Kaggle (máy cá nhân → Kaggle)

> **TL;DR (đã verify, dùng luôn — KHÔNG cần smoke test lại):** Từ máy cá nhân `kaggle` CLI push được **5 kernel CPU chạy ĐỒNG THỜI** (đo trực tiếp `max_concurrent_running = 5`, 5 node khác nhau, 5 khoảng [START..DONE] chồng lấn hoàn toàn). Luồng push → poll trạng thái → lấy log → verify hoạt động end-to-end. Đây là nền để fan-out 5 worker song song trên Kaggle.

## Kết quả smoke test (2026-06-13, GMT+7)

| Bằng chứng | Giá trị |
|---|---|
| `max_concurrent_running` | **5/5** (đo khi poll) |
| Node riêng biệt | da75…, c76c…, c283…, 9d72…, f83f… (5 host khác nhau) |
| Khoảng chạy (UTC) | cả 5 nằm trong 07:35:51 → 07:40:00, **chồng lấn hoàn toàn** |
| Mỗi kernel | `START` + đúng **5×TICK** (1 phút/lần) + `DONE` |
| Verdict | **PASS** |

Kết luận: Kaggle cho phép ≥5 kernel CPU private chạy song song cùng lúc cho 1 account → an toàn dùng 5 worker đồng thời.

## Tiền đề (1 lần)
- `kaggle` CLI đã cài + token đã config (`~/.kaggle/kaggle.json`). Kiểm tra nhanh: `kaggle kernels list --mine -p 1` (lỗi auth → token chưa sẵn sàng, dừng).
- **KHÔNG hardcode** username/key. Lấy động: `python -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.json')))['username'])"`.
- Mọi log dùng `logging`, không `print`.

## Cấu trúc 1 kernel
Mỗi worker là 1 thư mục gồm 2 file:

**`smoke.py`** (hoặc thay bằng job thật):
```python
import logging, socket, time, os
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("smoke")
node = socket.gethostname(); pid = os.getpid()
log.info(f"START node={node} pid={pid}")
for i in range(5):
    log.info(f"TICK node={node} pid={pid} iter={i+1}/5")
    if i < 4: time.sleep(60)
log.info(f"DONE node={node} pid={pid}")
```

**`kernel-metadata.json`** (thay `{USERNAME}`, `{N}`):
```json
{
  "id": "{USERNAME}/smoke-cpu-{N}",
  "title": "smoke-cpu-{N}",
  "code_file": "smoke.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": false,
  "enable_tpu": false,
  "enable_internet": false,
  "dataset_sources": [], "competition_sources": [], "kernel_sources": []
}
```
> CPU = `enable_gpu/tpu=false`. `enable_internet=false` cho an toàn (job offline). Cần mạng/dataset → bật `enable_internet` / điền `dataset_sources`.

## Quy trình vận hành
1. **Tạo** N thư mục `smoke-cpu-1..N` với 2 file trên (thay USERNAME/N).
2. **Push** gần như đồng thời: `kaggle kernels push -p ./smoke-cpu-{N}` cho từng N. Push lỗi → ghi nhận, đánh dấu FAIL, tiếp cái còn lại.
3. **Poll có cầu dao** (≤20 phút, ~20s/nhịp): `kaggle kernels status {USERNAME}/smoke-cpu-{N}`.
   Output dạng `... has status "KernelWorkerStatus.RUNNING"` → parse chuỗi trong `"..."`, gom về `queued/running/complete/error`.
   - Đếm số `running` mỗi nhịp → giữ `max_concurrent_running` lớn nhất (bằng chứng song song chính).
   - Quá 20 phút chưa xong → DỪNG, đánh dấu chưa-xong = TIMEOUT. **KHÔNG poll vô hạn.**
4. **Lấy log & verify**: `kaggle kernels output {USERNAME}/smoke-cpu-{N} -p ./out/smoke-cpu-{N}`.
   - ⚠️ Log Kaggle là **JSON** `[{"stream_name":...,"data":"<ts> INFO ..."}]` — timestamp nằm TRONG field `data`, KHÔNG ở đầu dòng. Parse START/TICK/DONE bằng regex trên nội dung `data`, đừng giả định "đầu dòng".
   - Verify mỗi log: có `START`, đúng số `TICK`, có `DONE`; trích `node` + timestamp để kiểm chồng lấn.
5. **Dọn dẹp**: `yes | kaggle kernels delete {USERNAME}/smoke-cpu-{N}` (CLI hỗ trợ `delete`). Hỏi user trước khi xóa.

## Tiêu chí PASS
Cả N kernel push được + đạt `complete` + mỗi log đủ `START`+N×`TICK`+`DONE` + `max_concurrent_running == N` (hoặc các khoảng [START..DONE] chồng lấn). `max_concurrent < N` = **PASS một phần** → đó chính là trần concurrency thực tế của account.

## Orchestrator tái dùng
Script Python tự chứa làm trọn 5 bước (tạo→push→poll cầu dao→lấy log→verify→báo cáo bảng + `result.json`) đã được kiểm chứng. Tái tạo: copy các snippet trên vào `orchestrator.py`, hoặc xin lại từ lịch sử chat smoke test 2026-06-13. Lưu ý sửa `verify_log` để parse timestamp BÊN TRONG JSON `data` (bản smoke test gốc để `start_ts/done_ts=null` vì giả định sai vị trí timestamp — không ảnh hưởng verdict nhưng nên fix nếu cần mốc thời gian).
