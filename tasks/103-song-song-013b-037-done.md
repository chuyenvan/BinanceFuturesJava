---
id: 103
status: DOING
owner: CCD-103A
updated: 2026-06-18
touches_live_process: false
writes_242_data: false
resource: kaggle_distributed+226
checkpoint: false
max_retry: 2
require_review: true
---

# TASK-103: Song song 013b (OI backfill) + 037 (fix Tool2 2023 + done export)

## Bối cảnh & mục tiêu
Chạy **song song** 2 nhánh độc lập, mục tiêu đóng cả 013b + 037 cùng lúc:
- **Nhánh A (013b):** backfill OI Kaggle cho ~886 symbol chưa có.
- **Nhánh B (037):** fix Aerospike reconnect + re-run Tool2 năm 2023 → 8/8 năm DONE.

Sau khi cả hai xong → chạy `ValidateOiData --quick` trên 226 (compile PASS) → nếu PASS:
**data OI được coi là đủ + đúng**, đóng 013b + 037, unblock 039.

---

## NHÁNH A — 013b: Launch OI backfill Kaggle (5 worker, ~886 symbol)

> Tiền đề đã đủ (docs/KAGGLE_RULES.md §9): slot FREE=5, jar sanitized sẵn, folder kernel sẵn.
> Chi tiết từng bước: `tasks/013b-launch-oi-backfill-full.md` (đọc trước).

### A1. Kiểm state 226
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 -o BatchMode=yes root@103.157.218.226 'timeout 20 bash -c "
  echo -n DONE=; asinfo -p 3222 -v \"sets/ticker/oi_backfill_done\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
  echo -n \" QUEUE=\"; asinfo -p 3222 -v \"sets/ticker/oi_backfill_queue\" 2>/dev/null | grep -oP \"n_objects=\K[0-9]+\"
"' 2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
```

### A2. Enqueue + push kernel (đọc KAGGLE_RULES trước)
Xem `tasks/013b-launch-oi-backfill-full.md` bước 1-4. Tóm tắt:
```bash
# Enqueue (dev local, thông 226:3222)
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx4g \
  -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar;target/classes" \
  com.binance.chuyennd.research.oibackfill.BackfillOiMaster

# Push kernel (SAU khi nhánh B đã chiếm slot nào thì tính lại FREE)
USED=$(kaggle kernels list --mine --page-size 20 2>&1 | grep -cE "running|queued" || echo 0)
FREE=$((5 - USED)); echo "FREE=$FREE"
cd C:/Users/pc/oi-kaggle/kernels
for i in $(seq 1 $FREE); do kaggle kernels push -p oi-backfill-worker-$i; sleep 2; done
```

### A3. Xử lý 12h kill (nếu cần)
Nếu tất cả kernel COMPLETE nhưng DONE < 894:
```bash
java ... BackfillOiMaster --reset-stale  # reset RUNNING về PENDING
# rồi push lại kernel theo slot còn trống
```

---

## NHÁNH B — 037: Fix Aerospike reconnect + re-run Tool2 năm 2023

### B0. Root cause xác nhận (TASK-103 phân tích)
Log `chuyendinh/ff40-2023` (đã tải về `/tmp/ff40-2023-out/`) xác nhận:
```
11:34:46 ERROR DataManagerAerospikeFloatSim: Error -8: Cluster is empty (x nhiều lần)
11:34:48 HOAN TAT: 0 dong x5 feat, 0/780 coin co OI
```
**Nguyên nhân:** Tool1 chạy ~24 phút → Aerospike client connection stale → Tool2 gọi `getMetricMap226()`
trả về rỗng vì cluster disconnected. **KHÔNG phải** bug filter timezone hay jar cũ.

**Fix cần làm:** trong `ExportFundingOiPerCoin.writeCoin()`, trước vòng loop coin, thêm ping/reconnect
để detect connection stale và force reconnect. Hoặc đơn giản hơn: **tách Tool2 thành kernel riêng**
(kernel con chạy sau Tool1 xong — không dùng chung Aerospike client đã stale).

### B1. Fix code — thêm reconnect guard trong ExportFundingOiPerCoin
File: `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFundingOiPerCoin.java`

Trong `main()`, TRƯỚC vòng loop coin, thêm ping để force reconnect nếu cần:
```java
// TASK-103 fix: ping Aerospike truoc khi chay Tool2 de tranh connection stale tu Tool1
// (Tool1 chay ~24 phut lam client stale -> Error -8 Cluster empty cho moi getMetricMap226 call)
try {
    DataManagerAerospikeFloatSim.getClient226().isConnected();
    // force reconnect bang 1 dummy read
    DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.OI.set, OiMetricSets.OI.bin, "BTCUSDT");
    LOG.info("Aerospike 226 ping OK truoc Tool2");
} catch (Exception ex) {
    LOG.warn("Aerospike 226 ping loi, thu reconnect: {}", ex.getMessage());
    // DataManagerAerospikeFloatSim se tu reconnect o lan goi tiep theo
}
```

Compile: `javac --release 11 -cp shaded.jar ...ExportFundingOiPerCoin.java` — PASS trước khi deploy.

### B2. Rebuild jar + update dataset Kaggle
```bash
# Rebuild jar HEAD (co fix B1)
# Update dataset chuyendinh/java-run-lc
cd C:/Users/pc/java-run-lc-stage
kaggle datasets version -p . -m "TASK-103 fix Aerospike reconnect Tool2"
```

### B3. Lấy stats 2025h2x + 2026x (đã export OK)
Hai kernel đã re-run v3 để fix validate OOM. Kiểm status + lấy log:
```bash
kaggle kernels status chuyendinh/ff40-2025h2x
kaggle kernels status chuyendinh/ff40-2026x

# Neu COMPLETE, lay log validate:
kaggle kernels output chuyendinh/ff40-2025h2x -p /tmp/ff40-2025h2x-out
kaggle kernels output chuyendinh/ff40-2026x -p /tmp/ff40-2026x-out
# Parse: grep Tool1 rec, Tool2 rec, #coin OI, PASS/FAIL
```

### B4. Re-run Tool2 năm 2023 (jar mới từ B2)
**KHÔNG re-run Tool1** (Tool1 năm 2023 = 38.374.777 rec đã OK, output đã lưu trên Kaggle).
Chỉ cần chạy Tool2 lại cho 2023. Cách đơn giản nhất: tạo kernel nhỏ chỉ chạy Tool2:

```python
# ff40-2023-oi-only.py (kernel mới, dùng jar mới + dataset ff40-2023 làm input để có Tool1 output)
# Chạy B0 dump mapper -> Tool2 thôi (bỏ Tool1)
```

Kernel này chỉ mất ~10-15 phút (OI 2023 = 105k mốc × 780 coin × 5 metric). Output: `oi_percoin_20230101_to_20240101.bin.gz`. Validate trong kernel.

**Lưu ý slot:** nhánh A đang dùng tối đa 5 slot → B4 cần chờ hoặc chạy sau khi A3 xong 1 slot.

### B5. Gộp số vào report 037 + 038
Sau khi có đủ 8 năm Tool1 + Tool2 (kể cả 2023 sửa):
- Điền bảng kết quả (rec Tool1, rec Tool2, #coin OI) cho tất cả 8 kỳ.
- Ghi PASS/FAIL validate từng năm.
- Set task 037 → REVIEW + commit.

---

## VALIDATE CUỐI (sau khi cả 2 nhánh xong)

```bash
# Chạy ValidateOiData --quick trên 226 (đủ để xác nhận BTC+LUNA+SOL)
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 -o BatchMode=yes root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx8g \
   -cp /root/java-run/binance-futures-java.jar \
   com.binance.chuyennd.research.oibackfill.ValidateOiData --quick 2>&1" \
  | grep -E "CHECK|PASS|FAIL|WARN|=====" \
  2>&1 | grep -vE "post-quantum|store now|upgraded|openssh"
```

PASS toàn bộ → **013b + 037 DONE**. Unblock 039.

---

## Thứ tự khuyến nghị
1. Start nhánh A (enqueue + push kernel) — chạy background overnight.
2. Làm nhánh B song song: fix code B1 → rebuild jar B2 → lấy stats B3 → re-run Tool2 B4.
3. Khi A xong (DONE ~894) + B xong (8/8 năm validate OK) → chạy ValidateOiData.
4. PASS → ghi report + set DONE + commit.

## An toàn
- Nhánh A: Kaggle worker chỉ ghi OI@226, không đụng data khác.
- Nhánh B: fix code + rebuild jar + re-run Tool2 (đọc Aerospike 226, không ghi).
- ValidateOiData: đọc-only.
- KHÔNG đụng 242, BinanceOrderTradingManager, BinanceDataIngestor, Redis.
