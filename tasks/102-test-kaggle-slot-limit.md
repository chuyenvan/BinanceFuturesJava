---
id: 102
status: TODO
touches_live_process: false
writes_242_data: false
resource: kaggle
---

# TASK-102: Test + xác nhận Kaggle CPU slot limit hiện tại

## Mục đích
Trước khi launch fleet (013b hoặc bất kỳ multi-kernel job), xác nhận số slot thực tế
hiện tại của account `chuyendinh`. Slot limit đã test 2026-06-13 = 5, nhưng có thể thay đổi
theo thời gian (Kaggle điều chỉnh quota). Test này rẻ (1 kernel nhỏ) + cập nhật KAGGLE_RULES.md.

## Việc làm (CCD)

### Bước 1: Đếm slot đang dùng
```bash
# Đếm tổng kernel đang RUNNING hoặc QUEUED
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
FREE=$((5 - USED))
echo "Slot dang dung: $USED / Slot con trong: $FREE"
kaggle kernels list --mine --page-size 20 2>&1
```

### Bước 2: Tạo + push 1 kernel test nhỏ (chỉ echo + exit)
```bash
mkdir -p /tmp/slot-test-1
cat > /tmp/slot-test-1/test.py << 'EOF'
import logging, time, os
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("slot-test")
log.info("SLOT_TEST_START")
log.info("SLOT_TEST_OK")
EOF

cat > /tmp/slot-test-1/kernel-metadata.json << 'EOF'
{
  "id": "chuyendinh/slot-test-1",
  "title": "slot-test-1",
  "code_file": "test.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": false,
  "enable_tpu": false,
  "enable_internet": false,
  "dataset_sources": [], "competition_sources": [], "kernel_sources": []
}
EOF

kaggle kernels push -p /tmp/slot-test-1 2>&1
```

### Bước 3: Poll + verify
```bash
# Poll đến COMPLETE hoặc ERROR (tối đa 5 phút)
for i in $(seq 1 30); do
  STATUS=$(kaggle kernels status chuyendinh/slot-test-1 2>&1 | grep -oE "RUNNING|COMPLETE|ERROR|QUEUED" | head -1)
  echo "$(date) STATUS=$STATUS"
  [ "$STATUS" = "COMPLETE" ] || [ "$STATUS" = "ERROR" ] && break
  sleep 10
done

# Lấy log
kaggle kernels output chuyendinh/slot-test-1 -p /tmp/slot-test-out 2>&1
cat /tmp/slot-test-out/*.json 2>/dev/null | python3 -c "
import json, sys
for item in json.load(sys.stdin): print(item.get('data',''))
" | grep -E "SLOT_TEST"
```

### Bước 4: Dọn dẹp
```bash
yes | kaggle kernels delete chuyendinh/slot-test-1 2>&1 || true
rm -rf /tmp/slot-test-1 /tmp/slot-test-out
```

## Báo lại (CCD điền — 2026-06-17 GMT+7)
- Slot đang dùng khi test: `USED=0`
- Slot còn trống: `FREE=5`
- Kernel push OK? **COMPLETE**
- Log có `SLOT_TEST_OK`? **Y** (`2026-06-17 15:27:29,666 INFO SLOT_TEST_OK`)
- Thời gian kernel COMPLETE (giây): **2 s** (push xong poll ngay đã COMPLETE)

## Sau khi xong — cập nhật KAGGLE_RULES.md
Thêm vào mục "Lịch sử cập nhật":
```
| 2026-06-?? | TASK-102: xác nhận slot limit = N/5 (test COMPLETE trong Xs) |
```

## An toàn
- Kernel offline (enable_internet=false), không đụng 226/242.
- Script chỉ log 2 dòng rồi exit — COMPLETE trong < 1 phút.
- Xóa kernel sau khi test (không chiếm slot).
