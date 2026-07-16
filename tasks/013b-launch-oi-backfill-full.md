---
id: 013b
status: CANCELLED
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
- **Kaggle slot:** TASK-102 xác nhận FREE=5 (USED=0), kernel test COMPLETE trong 2 giây ✅

**Update 2026-06-17 (TASK-101):** DiagnoseOiRange chạy trên 226 xác nhận data OI **ĐÃ có đầy đủ**
cho 5 coin lớn: BTC(608k mốc 2020-09→nay), ETH/BNB/XRP/SOL (~477k mốc 2021-12→nay), 2023 = ~105k
mốc/năm (đúng granularity 5m). Tức là backfill phần lớn đã chạy (có thể từ trước, không qua queue
hiện tại). Lý do "OI 2023 empty" ở TASK-037 là **phương án B: bug filter `[start,end)` trong
`ExportFundingOiPerCoin`** — data có trong Aerospike nhưng tool không emit ra file. Bug này cần fix
riêng (TASK-101 phần tiếp theo). **013b vẫn cần** để đảm bảo coin nhỏ/delist cũng có đủ data.

**Lý do launch:** TASK-037 Tool 2 báo empty do bug filter (không phải thiếu data). Nhưng cần backfill
coin nhỏ/delist chưa có data trước khi validate cuối + merge 039.

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

### Bước 3: Kiểm slot Kaggle trước — DỪNG nếu không đủ 5 slot
```bash
# Đếm slot đang bị chiếm (RUNNING + QUEUED) trên account chuyendinh
kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0
```
Kaggle CPU giới hạn **5 slot đồng thời** (tất cả kernel của account). Hiện TASK-037 có thể đang
chiếm vài slot (`ff40-*`). **Tính toán:**
- Đếm slot đang dùng = N_RUNNING.
- Slot khả dụng = 5 - N_RUNNING.
- Nếu slot < 5: push đúng số slot còn trống (vd slot còn 2 → push 2 kernel worker trước).
- **DỪNG + báo user** nếu slot = 0 (không thể push gì, chờ 037 xong bớt slot).
- Ghi lại: N_RUNNING khi bắt đầu push, số kernel worker thực sự push được.

```bash
# Push đúng số slot còn trống
cd C:/Users/pc/oi-kaggle/kernels
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
FREE=$((5 - USED))
echo "Slot dang dung=$USED, con trong=$FREE"
if [ "$FREE" -le 0 ]; then
  echo "DUNG: khong con slot. Cho 037 xong bot slot roi push."
  exit 1
fi
for i in $(seq 1 $FREE); do
  kaggle kernels push -p oi-backfill-worker-$i 2>&1
  sleep 2
done
echo "Da push $FREE kernel worker (oi-backfill-worker-1..$FREE)"
```

> **Nếu chỉ push được < 5:** không sao — số worker ít hơn, chạy lâu hơn, nhưng queue vẫn đúng.
> Khi 037 giải phóng thêm slot, push tiếp các kernel còn lại (worker-{N+1..5}).
> **Không push thêm quá 5 tổng** — push thêm sẽ tranh slot (bài học 2 CCD song song).

### Bước 4: Monitor tiến độ + xử lý kernel bị kill sau 12h
```bash
# Đếm done/queue trên 226
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 'timeout 20 bash -c "
echo -n \"DONE=\"; asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
echo -n \"QUEUE=\"; asinfo -p 3222 -v \"sets/ticker/oi_backfill_queue\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
"' 2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
# Kaggle kernel status
kaggle kernels list --mine --page-size 20 2>&1 | grep -E "oi-backfill|RUNNING|COMPLETE|ERROR"
```
Ước tính thời gian: 894 symbol × ~2.5 phút/symbol / 5 worker ≈ **~7.5 giờ**. Để chạy overnight.

#### Xử lý kernel bị kill sau 12h (giới hạn Kaggle CPU session)
Kaggle kill kernel sau **12 giờ**. Nếu queue chưa cạn lúc đó, task đang `RUNNING` bị bỏ dở:
- Worker code (`STALE_RUNNING_MS = 45 phút`) sẽ tự cướp task bị bỏ dở — **nhưng chỉ khi có worker còn sống**.
- Nếu tất cả 5 kernel bị kill cùng lúc → không còn ai cướp → task mắc kẹt `RUNNING` mãi.

**Cách xử lý khi phát hiện tất cả kernel COMPLETE/ERROR nhưng DONE < 894:**
```bash
# Bước A: reset task bị stuck RUNNING về PENDING (không mất data đã ghi)
# BackfillOiMaster --reset-stale chạy trên DEV: scan queue, task RUNNING > 45' → set về PENDING
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g \
  -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar;target/classes" \
  com.binance.chuyennd.research.oibackfill.BackfillOiMaster --reset-stale 2>&1 | tail -5

# Bước B: kiểm slot còn trống
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
echo "Slot trong: $((5 - USED))"

# Bước C: push lại số kernel theo slot còn trống (tái dùng folder, idempotent)
cd C:/Users/pc/oi-kaggle/kernels
FREE=$((5 - USED)); [ "$FREE" -le 0 ] && echo "DUNG: cho slot" && exit 1
for i in $(seq 1 $FREE); do
  kaggle kernels push -p oi-backfill-worker-$i 2>&1; sleep 2
done
```

> **Tóm tắt vòng lặp:** mỗi ~11-12 giờ kiểm DONE count. Nếu chưa xong → reset-stale + push lại.
> Lặp lại cho đến khi DONE = ~894. Idempotent: worker tự skip symbol đã DONE (isDone check đầu tiên).
> Tối đa 2-3 lần push lại là xong hết 894 symbol.

> **Lưu ý `--reset-stale` trong BackfillOiMaster:** cần kiểm xem master code đã có flag này chưa.
> Nếu chưa có, CCD thêm vào: scan QUEUE_SET, record nào status=RUNNING và
> (currentTime - startTime) > STALE_RUNNING_MS → update về PENDING. Idempotent, an toàn.

### Bước 5: Khi DONE = ~894 + queue = 0 — PushOiSetsTo242
Chạy `PushOiSetsTo242` **TRÊN 226** (KHÔNG từ Kaggle, không từ dev — 242 chỉ accessible từ 226):
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx8g -cp /root/java-run/binance-futures-java.jar \
   com.binance.chuyennd.research.oibackfill.PushOiSetsTo242 2>&1 | tail -20"
```
> Nếu jar trên 226 cũ (thiếu class oibackfill) → scp jar mới lên 226 trước.

### Bước 6: Validate DỨT KHOÁT — DU + DUNG — dùng ValidateOiData.java

> **Mục tiêu:** 1 lần chạy dứt khoát, output PASS/FAIL. Nếu PASS toàn bộ → **không cần kiểm lại bao giờ nữa**.
> Nếu sau này đọc OI ra kết quả bất thường → vấn đề ở code ĐỌC hoặc XỬ LÝ, **không phải data 226**.

Tool: `src/main/java/com/binance/chuyennd/research/oibackfill/ValidateOiData.java` (đã code, compile PASS).

```bash
# Deploy jar mới (có ValidateOiData) lên 226
# Sau đó chạy FULL validate:
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx8g -cp /root/java-run/binance-futures-java.jar \
   com.binance.chuyennd.research.oibackfill.ValidateOiData 2>&1" \
  | grep -E "CHECK|PASS|FAIL|WARN|====="
```

**4 checks được kiểm:**
1. **DU — Coverage:** >= 300 coin có OI trong 2023, phân bố theo năm (phát hiện gap năm).
2. **DU — Granularity:** BTC 2023 >= 80k mốc, gap lớn nhất < 30 phút (granularity 5m đủ dày).
3. **DUNG — Giá trị OI:** BTC OI không NaN/Inf/<=0; LUNA OI giảm >50% trong crash 2022-05
   (cross-check economic signal — đây là check "đúng" quan trọng nhất, dữ liệu phải phản ánh thực tế).
4. **DUNG — LS + taker:** lsGlobal ∈ [0.05, 20], taker ∈ [0, 50] cho BTC + LUNA.

**Output PASS ví dụ:**
```
[PASS-1] coverage ok
[PASS-2] granularity ok
[PASS-3a] BTC OI range sanity OK
[PASS-3b] LUNA crash signal OK (OI giam >50%)
[PASS-4] LS + taker range sanity OK
VALIDATE PASS (FULL failures=0) — OI data DU + DUNG, KHONG can kiem lai.
```

**Ghi số + output vào `docs/reports/013.md`** (mục "VALIDATE FINAL").
Set task 013 + 013b → **DONE** nếu VALIDATE PASS.

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
