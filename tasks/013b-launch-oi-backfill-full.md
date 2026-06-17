---
id: 013b
status: TODO
depends_on: [013]
touches_live_process: false
writes_242_data: false
resource: kaggle_distributed
checkpoint: true
max_retry: 1
report: docs/reports/013.md
require_review: false
---

# TASK-013b: Launch full TASK-013 — backfill OI 5 set cho ~886 symbol còn lại

## Bối cảnh
TASK-013 đã qua toàn bộ VERIFY + TEST + gate review. Mọi tiền đề ĐÃ SẴN SÀNG:
- `oi_backfill_done` = 8 symbol (BTC/LUNA dev cũ + 6 test) → ~886 symbol còn lại.
- Dataset Kaggle `chuyendinh/java-run-lc` (jar oibackfill sanitized) ✅
- Kernel folder `C:\Users\pc\oi-kaggle\kernels\oi-backfill-worker-{1..5}` ✅
- Test 1 kernel Kaggle PASS 2 lần độc lập ✅ (System.exit OK, Kaggle→vision+226 OK, queue OK)
- `oi_backfill_queue` = rỗng, state 226 lành (idempotent — rerun chỉ làm symbol chưa DONE)

**Lý do launch:** Tool 2 (`ExportFundingOiPerCoin`) trong TASK-037 đang chạy Kaggle — OI empty
cho mọi năm vì chỉ có 8 symbol trong Aerospike 226. Cần backfill đủ trước khi merge+train 039.

## Việc (CCD) — theo đúng thứ tự, KHÔNG đảo

### Bước 1: Kiểm state 226 trước khi enqueue
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 'timeout 20 bash -c "
asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -E \"objects|n_objects\"
asinfo -p 3222 -v \"sets/ticker/oi_backfill_queue\" 2>/dev/null | grep -E \"objects|n_objects\"
"' 2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
```
Kỳ vọng: `oi_backfill_done` ~8, `oi_backfill_queue` = 0. Nếu queue > 0 từ test cũ → master sẽ skip
symbol đã DONE, tự điền tiếp (idempotent). OK tiếp.

### Bước 2: Enqueue ~886 symbol còn lại (BackfillOiMaster no-args)
Chạy trên **DEV (local)** — master không cần ở trong Kaggle, chỉ cần thông 226:3222.
```bash
# Trong IntelliJ terminal (hay Git Bash), tại thư mục project
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g \
  -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar;target/classes" \
  com.binance.chuyennd.research.oibackfill.BackfillOiMaster 2>&1 | tail -20
```
> Hoặc dùng jar đã có trên dev nếu `target/classes` chưa build. Master tự skip 8 symbol DONE.
> Kỳ vọng: log "Enqueued N symbol" (N ~ 886), rồi master poll queue và tự exit khi đủ DONE.
> **KHÔNG kill master** — để chạy nền (nó poll + in dashboard, exit khi queue cạn).

### Bước 3: Push 5 kernel Kaggle
```bash
cd C:/Users/pc/oi-kaggle/kernels
for i in 1 2 3 4 5; do
  kaggle kernels push -p oi-backfill-worker-$i 2>&1
  sleep 2
done
```
Kỳ vọng: 5 kernel status RUNNING. Mỗi worker poll queue@226, tải vision, ghi 226, mark DONE.
**Không push thêm** — 5 kernel + 5 Kaggle slot; push thêm sẽ tranh slot (bài học 2 CCD song song).

### Bước 4: Monitor tiến độ (poll mỗi ~10 phút)
```bash
# Đếm done/queue trên 226
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 'timeout 20 bash -c "
echo -n \"DONE=\"; asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
echo -n \"QUEUE=\"; asinfo -p 3222 -v \"sets/ticker/oi_backfill_queue\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
"' 2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
# Kaggle kernel status
kaggle kernels list --mine --page-size 10 2>&1 | grep -E "oi-backfill|RUNNING|COMPLETE|ERROR"
```
Ước tính thời gian: 894 symbol × ~2.5 phút/symbol / 5 worker ≈ **~7.5 giờ**. Để chạy overnight.

### Bước 5: Khi DONE = ~894 + queue = 0 — PushOiSetsTo242
Chạy `PushOiSetsTo242` **TRÊN 226** (KHÔNG từ Kaggle, không từ dev — 242 chỉ accessible từ 226):
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx8g -cp /root/java-run/binance-futures-java.jar \
   com.binance.chuyennd.research.oibackfill.PushOiSetsTo242 2>&1 | tail -20"
```
> Nếu jar trên 226 cũ (thiếu class oibackfill) → scp jar mới lên 226 trước.

### Bước 6: Validate cuối + ghi report
```bash
# 1. Coverage: đọc số set records trên 226 (OI 5 set)
ssh ... 'asinfo -p 3222 -v "sets/ticker/open_interest" | grep n_objects;
         asinfo -p 3222 -v "sets/ticker/oi_ls_toptrader_acc" | grep n_objects;
         asinfo -p 3222 -v "sets/ticker/oi_ls_global_acc" | grep n_objects;
         asinfo -p 3222 -v "sets/ticker/oi_taker_vol" | grep n_objects'
# 2. Cross-check OI tụt quanh LUNA crash (2022-05): coin LUNAUSDT, tháng 2022-05
#    → OI phải giảm mạnh (Binance ghi nhận unwind)
# 3. BackfillOiVerify BTCUSDT ETHUSDT SOLUSDT → recompute vs data gốc
```

Ghi số vào `docs/reports/013.md` (thêm mục "LAUNCH FULL"):
- #symbol DONE, #chunk ghi (per set), thời gian, kết quả cross-check OI crash, verify pass/fail.
- Set status task 013 → **REVIEW** (hoặc DONE nếu validate sạch).

## An toàn
- Master chạy dev, chỉ ghi queue@226 (Aerospike). KHÔNG đụng live/ingest.
- Worker chạy Kaggle, chỉ tải vision + ghi 5 set OI@226. KHÔNG đụng set khác.
- PushOiSetsTo242 chạy TRÊN 226: đẩy 5 set OI 226→242. Merge-guard (không ghi đè).
  ⚠️ chạy ngoài giờ cao điểm (tránh tranh RAM với live ingest trên 242).
- KHÔNG scp/push secret (PrivateConfig.java on-disk LIVE, untracked).

## Ghi chú jar
- Jar oibackfill sanitized ở `chuyendinh/java-run-lc` đã build từ HEAD có `BackfillOiWorker`.
- Nếu cần rebuild (có thay đổi mới ở HEAD): xem RUNBOOK trong docs/reports/013.md.

## (CCD điền sau khi xong)
- Bước 1 — state 226 trước enqueue: DONE=? QUEUE=?
- Bước 2 — master enqueued N=?
- Bước 3 — 5 kernel pushed, status ban đầu: ?
- Bước 4 — thời gian chạy, snapshot DONE count giữa chừng: ?
- Bước 5 — PushOiSetsTo242 result: ?
- Bước 6 — validate: #chunk/set, cross-check crash, verify: ?
