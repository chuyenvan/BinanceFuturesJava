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

## ĐÃ LÀM (Desktop, 2026-06-18 — ĐỪNG làm lại)
- Dọn /tmp: 55G → 527M (ổ C 21G→75G free).
- Sửa chỗ ghi LỚN nguy hiểm: task 103 (kernel output 2025h2x/2026x), task 100 (ff40-2022-out),
  KAGGLE_RULES §10 (k1-out) → `/d/claudedata`.
- KAGGLE_RULES §0 đã có quy tắc cấm ghi ổ C.

## VIỆC CÒN LẠI (ít — chủ yếu chống tái diễn tận gốc)

### Bước 0 (QUAN TRỌNG NHẤT): đưa quy tắc vào CLAUDE.md
CLAUDE.md là file CCD LUÔN đọc đầu phiên. Thêm 1 mục ngắn, nổi bật ở đầu:
> **CẤM GHI Ổ C.** Mọi log/output/file tải về → `/d/claudedata` hoặc ổ E.
> KHÔNG `/tmp`, KHÔNG `~/`, KHÔNG AppData/Temp (đều ổ C). Ổ C full 3 lần → MCP chết, restart máy.
> File trên 226 giữ trên 226. Chi tiết: KAGGLE_RULES §0 + tasks/105.
Đây là việc giá trị nhất của task — quy tắc chỉ hiệu lực nếu CCD thấy nó mà không cần mở task.

### Bước 1: Đổi nốt vài /tmp NHỎ còn sót (ít hại, làm cho nhất quán)
- `tasks/038` dòng 45: `javac ... -d /tmp/c038` → `-d /d/claudedata/build/c038`
- `tasks/102` dòng 30-67: `/tmp/slot-test-*` → `/d/claudedata/slot-test-*`
(File nhỏ vài KB, KHÔNG gây full ổ — đổi để nhất quán, không gấp.)

### Bước 2 (nếu /tmp lại đầy): dọn rác kernel output
```bash
du -sh /tmp 2>/dev/null
rm -rf /tmp/ff40-* /tmp/oi-* /tmp/oichk-* /tmp/k1-out /tmp/slot-test-* /tmp/chk-* /tmp/c0* /tmp/c1* 2>/dev/null
df -h /c | tail -1
```

### Bước 3: grep soát còn /tmp ghi LỚN nào sót không
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
