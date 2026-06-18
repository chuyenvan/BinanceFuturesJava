---
id: 103f
status: TODO
owner: MOT-CCD-DUY-NHAT
updated: 2026-06-18
touches_live_process: false
writes_242_data: false
resource: 226+kaggle
require_review: true
---

# TASK-103f: ĐÓNG NỐT 037 + validate OI (giao 1 CCD DUY NHẤT)

> ⚠️ **CHỈ 1 CCD làm task này.** Trước đó 2 CCD cùng nhảy vào 103 → trùng việc.
> Nếu bạn thấy CCD khác đang chạy task 103/103f → DỪNG, báo user, KHÔNG chạy song song.
> `git pull` (branch module) trước khi bắt đầu. Đọc `docs/KAGGLE_RULES.md`.
>
> ⚠️ **Sau mất điện / restart môi trường:** `kaggle` có thể không còn trong PATH
> (báo `kaggle: command not found`). Dùng full path:
> `KG="/c/Users/pc/AppData/Local/Programs/Python/Python311/Scripts/kaggle.exe"` rồi `"$KG" kernels ...`.
> Trạng thái đã verify (2026-06-18 sau mất điện lần 2): 226 DONE=896/QUEUE=0/OI=18498,
> 3 kernel oi-only (2023/2025h2x/2026x) đều COMPLETE — KHÔNG cần chạy lại các phần này.

## Trạng thái đã xong (ĐỪNG làm lại)
- **Nhánh A (013b backfill):** ✅ DONE — `oi_backfill_done=896`, queue rỗng, 5 worker COMPLETE.
  Data OI đã verify có trong Aerospike 226 (OI=18.498 / LS=18.332 / taker=17.811 chunk-record).
- **Fix reconnect (B1):** ✅ trong HEAD + jar v4 (`a0745d5`). Ping BTC trước Tool2 loop.
- **Tool2 đã re-run xong (jar v4):** 2023 (19.8M rec), 2025h2x (26.45M/571 coin), 2026x (14.2M/582 coin).

## Việc CÒN LẠI — làm tuần tự

### Bước 1: Xác định Tool2 năm nào CÒN empty (5 năm cũ)
Các năm 2021/2022/2024h1/2024h2/2025h1 chạy Tool2 trong kernel GỐC (cùng Tool1).
Vì Tool1 chạy lâu (~24 phút) làm Aerospike stale, Tool2 các năm này CÓ THỂ đã empty
(đúng bug Error-8 như 2023). Kiểm nhanh — tải Tool2 output từng kernel, đọc dòng "HOAN TAT":
```bash
LOGDIR="/d/claudedata"; mkdir -p "$LOGDIR"   # luu o D:, KHONG o C (da full 2 lan)
for k in ff40-2021 ff40-2022 ff40-2024h1 ff40-2024h2 ff40-2025h1; do
  kaggle kernels output chuyendinh/$k -p "$LOGDIR/oi-$k" 2>/dev/null
  echo "=== $k ==="
  cat "$LOGDIR/oi-$k"/*.log 2>/dev/null | grep -o '"data":"[^"]*"' | sed 's/"data":"//;s/"$//' \
    | grep -iE "HOAN TAT.*coin co OI|0/780|oi_percoin" | head -2
done
```
→ Năm nào "0/780 coin co OI" = EMPTY, cần re-run. Năm nào ">0 coin" = OK, bỏ qua.

### Bước 2: Re-run Tool2-ONLY cho các năm empty (jar v4)
Với MỖI năm empty, tạo kernel `ff40-<năm>-oi-only` (giống ff40-2023-oi-only CCD đã làm):
chỉ chạy Tool2 (KHÔNG Tool1), dùng jar v4, dataset java-run-lc.
**Kiểm slot trước (KAGGLE_RULES §1):** push tối đa = số slot trống. Mỗi kernel ~10-15 phút.
> Nếu cả 5 năm đều empty → 5 kernel (vừa đủ 5 slot). Nếu vài năm OK → ít kernel hơn.

### Bước 3: VALIDATE cuối — ValidateOiData trên 226 (CỔNG đủ+đúng)
Đây là cổng quyết định, KHÔNG bỏ qua. Build jar HEAD (có ValidateOiData) lên 226, chạy:
```bash
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx8g -cp /root/java-run/<jar> \
   com.binance.chuyennd.research.oibackfill.ValidateOiData --quick 2>&1" \
  | grep -E "CHECK|PASS|FAIL|WARN|====="
```
4 check: coverage ≥300 coin 2023 / granularity BTC 2023 / **OI BTC no-NaN + LUNA crash 2022-05 giảm >50%** / LS+taker range.
- PASS toàn bộ → data OI 226 ĐỦ+ĐÚNG, không kiểm lại nữa.
- FAIL → đọc check nào fail, báo user, KHÔNG tự đoán.

### Bước 4: Gộp report + đóng task
- Điền `docs/reports/037.md` + `038.md`: bảng 8 kỳ (Tool1 rec / Tool2 rec / #coin OI / PASS-FAIL).
- ValidateOiData PASS → set 037 + 013b → **DONE**. Commit + push.
- Báo user: "037 + OI đóng xong, unblock 039" + dán bảng kết quả + dòng ValidateOiData.

## An toàn
- 226: đọc Aerospike read-only (Tool2 + Validate). KHÔNG đụng live/ingest/Redis/242.
- Kaggle: chỉ kernel oi-only đọc 226. Kiểm slot trước khi push.
- 1 CCD duy nhất. SLF4J, không System.out.

## (CCD điền)
- Bước 1: năm empty = ?
- Bước 2: kernel re-run = ?, kết quả rec/coin = ?
- Bước 3: ValidateOiData = PASS/FAIL (dán dòng tổng kết)
- Bước 4: commit hash + status 037/013b
