---
id: 105
status: TODO
owner: MOT-CCD
updated: 2026-06-18
touches_live_process: false
writes_242_data: false
resource: local
require_review: false
---

# TASK-105: Chuyển TẤT CẢ dữ liệu làm việc sang `D:\claudedata` — TUYỆT ĐỐI không ghi ổ C

> ⚠️⚠️ **QUY TẮC NGHIÊM NGẶT — đọc trước mọi việc:**
> **KHÔNG BAO GIỜ ghi file/log/output ra ổ C.** Luôn ghi vào **`D:\claudedata`** (`/d/claudedata`)
> hoặc ổ **E** (`/e/...`). Ổ C là ổ cài Windows — đã bị FULL **3 lần** vì CCD ghi vào `/tmp`,
> mỗi lần làm MCP chết + phải restart máy + mất job đang chạy. ĐÂY LÀ LỖI NGHIÊM TRỌNG NHẤT.

## Vì sao
- `/tmp`, `~/`, `C:\Users\...\AppData\...\Temp` trong Git Bash trên Windows **đều nằm trên ổ C**.
- CCD tải kernel output (`kaggle kernels output -p /tmp/...`) — mỗi file feature cả năm ~5-6GB.
  Tải 8-10 kernel → 50GB+ → ổ C full → MCP crash → restart máy → job kill giữa chừng.
- Sự cố thực tế: `/tmp` từng chiếm **55GB** (ff40-*-out). Đã dọn 2026-06-18.

## QUY TẮC (áp dụng VĨNH VIỄN cho mọi task, mọi CCD)

| Loại file | Ghi vào | TUYỆT ĐỐI KHÔNG |
|---|---|---|
| Kaggle kernel output | `/d/claudedata/<tên>` | `/tmp`, `~/`, AppData |
| Log job (ablation, validate, backfill) | `/d/claudedata/*.log` hoặc trên 226 | `/tmp`, stdout-only |
| File trung gian / tải về | `/d/claudedata/` | ổ C bất kỳ đâu |
| Compile output (`javac -d`) | `/d/claudedata/build/` hoặc `target/` (ổ E) | `/tmp/cXXX` |
| File trên server 226 | giữ trên 226 (`/home/chuyennd/...`) | KHÔNG kéo về ổ C |

**Mẫu chuẩn:**
```bash
LOGDIR=/d/claudedata; mkdir -p "$LOGDIR"
kaggle kernels output chuyendinh/<kernel> -p "$LOGDIR/<ten>-out"
java ... > "$LOGDIR/<job>.log" 2>&1
javac --release 11 -cp "$JAR" -d "$LOGDIR/build" <file>
```

## Việc làm

### Bước 1: Dọn /tmp hiện tại (nếu còn rác)
```bash
du -sh /tmp 2>/dev/null
# Neu > 1GB, xoa rac kernel output (deu tai lai duoc tu Kaggle cloud):
rm -rf /tmp/ff40-* /tmp/oi-* /tmp/oichk-* /tmp/k1-out /tmp/slot-test-* /tmp/chk-* /tmp/c0* /tmp/c1* 2>/dev/null
df -h /c | tail -1   # xac nhan o C da thoang
```

### Bước 2: Sửa các task/doc còn trỏ /tmp (ghi file LỚN) → /d/claudedata
Các chỗ cần sửa (CCD grep lại để chắc, vì task có thể đã sửa 1 phần):
```bash
grep -rn "kaggle kernels output.*-p /tmp\|> /tmp\|-o /tmp" tasks/ docs/ python/
```
Đổi `-p /tmp/...` → `-p /d/claudedata/...`. CHỪA `/tmp/oisyms.txt` trong task 037
(đó là /tmp TRÊN SERVER 226, không phải ổ C local — KHÔNG đổi).
Compile dir `/tmp/cXXX` (nhỏ, ít hại) đổi sang `/d/claudedata/build` cho nhất quán.

### Bước 3: Tạo D:\claudedata + xác nhận
```bash
mkdir -p /d/claudedata
df -h /d | tail -1   # xac nhan o D con cho (429G free)
echo "OK" > /d/claudedata/.keep
```

### Bước 4: Commit
- Commit các task/doc đã sửa. Message: "TASK-105: chuyen data lam viec sang D:\claudedata, cam ghi o C".

## An toàn
- KHÔNG xóa file ngoài /tmp. KHÔNG đụng D:\claudedata data thật của user.
- Chỉ xóa rác kernel output trong /tmp (tải lại được).
- Đây là task local, không đụng 226/242/Kaggle job đang chạy.

## (CCD điền)
- Bước 1: /tmp trước = ?GB, sau = ?GB, ổ C free = ?
- Bước 2: số chỗ /tmp đã sửa = ?
- Bước 4: commit hash
