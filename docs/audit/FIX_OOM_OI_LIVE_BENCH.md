# BENCH KIỂM CHỨNG FIX OOM OI-LIVE (Kaggle, JVM heap chặn) — 2026-09-30

Phạm vi: **CHỈ bench/heap + parity + doc**. KHÔNG deploy/restart/ghi env; KHÔNG chạm production/242/ONNX/LIVE;
KHÔNG chạy Java/sim trên Oracle (mọi JVM chạy trên **Kaggle**, JDK 17.0.18). Branch `module`.

- Kernel: <https://www.kaggle.com/code/chuyendinh/oi-heap-bench-o512> (v3), nguồn: `orchestrator/kernels_oi_bench/`.
- Số liệu máy đọc: `docs/audit/FIX_OOM_OI_LIVE_BENCH.json`; log gọn: `docs/audit/FIX_OOM_OI_LIVE_BENCH.log`.
- Jar fix giữ **nguyên** sha256 `c389b4be…ca1e15` (không build lại). Bench compile từ source, sha in trong log
  khớp file repo: `OiReloadHeapBench.java` = `40ff61f2…dd8be` (đúng bản nằm trong jar).

## 0. KẾT LUẬN (một dòng)

> `legacy` **OOM thật** ở cả `-Xmx512m` **và** `-Xmx4g` (1 bản sống ~**2.194 MB**, double-buffer > 4g ⇒ tái hiện đúng OOM
> production); `inplace` **PASS, không OOM**, retained sau `System.gc()` = **73–74 MB** (~**30× thấp hơn**), `lookup`
> **trùng legacy** trong cửa sổ 24h (`980/980` check). ⇒ bench **chứng minh được fix** (mô hình bộ nhớ + parity cắt 24h)
> ⇒ **đủ điều kiện đề xuất canary shadow** (cần owner duyệt deploy).

## 1. VIỆC 1 — đọc `OiReloadHeapBench` (không phụ thuộc Aerospike)

`src/main/java/.../research/passspeed/OiReloadHeapBench.java` (124 dòng), **thuần `java.util`** ⇒ **KHÔNG cần Aerospike**,
chạy được trên Kaggle (không cần tách phần thuần bộ nhớ).

- Tham số: `mode` (`legacy`|`inplace`), `nCoins=653`, `cycles=3`, `pointsPerSet=8640` (~1 tháng 5m/set), `chunk=64`.
- Mô hình hoá: 1 chunk-tháng = 5 set × 8640 điểm 5m; `legacy` = dựng map MỚI toàn universe khi map CŨ còn sống (double-buffer);
  `inplace` = dựng chunk-tháng rồi CẮT 24h (288 điểm/set) và `put` vào CHÍNH map đang sống.
- Đo peak: `peakUsed = max(totalMemory-freeMemory)` — lấy mẫu **sau mỗi chu kỳ** (`legacy` còn `sample()` giữa lúc build).
  PASS = hoàn tất mọi chu kỳ **không OOM** **và** `peakUsed ≤ BENCH_BUDGET_MB` (nếu đặt).
- **Cảnh báo đo lường:** `peakUsed` gồm **rác chưa GC** (GC-lag) ⇒ phụ thuộc kích thước heap, KHÔNG phải "bộ nhớ sống".
  Vì vậy tôi thêm `OiReloadHeapBenchExt` tách **peakUsed** khỏi **retained-sau-GC** (đại lượng quyết định OOM).

## 2. Cách chạy (Kaggle, heap chặn)

Kernel script tự-đóng-gói (nhúng 3 file `.java` base64 → `javac` → `java`), không cần dataset:
`java -Xmx512m -cp classes … OiReloadHeapBench {legacy|inplace} 653 3 8640` (và `OiReloadHeapBenchExt`,
`OiReloadParityCheck 20 8640`). Lượt `@4g` chạy `-Xmx4g` để **trùng heap production**.

## 3. KẾT QUẢ (thật, từ log)

| run | heap | rc | OOM? | peakUsed | **retained (sau GC)** | entries | verdict |
|---|---|---|---|---|---|---|---|
| `legacy` (bench) | 512m | 1 | **CÓ** (`OutOfMemoryError: Java heap space`) | 0* | – | 0 | FAIL |
| `inplace` (bench) | 512m | 1 | không | **405 MB** | – | 653 coin | FAIL* |
| `legacy` (ext) | 512m | 1 | **CÓ** | 0 | 1 MB | 0 | FAIL |
| `inplace` (ext) | 512m | 0 | không | 350 MB | **73 MB** | 943.585 | **PASS** |
| `inplace_slice` (ext) | 512m | 0 | không | 222 MB | **73 MB** | 940.320 | **PASS** |
| `legacy` (ext) | **4g** | 1 | **CÓ** | **2.194 MB** | 2.155 MB | 28.209.600 | FAIL |
| `inplace` (ext) | **4g** | 0 | không | 770 MB | **74 MB** | 943.585 | **PASS** |
| `parity` | 512m | 0 | – | – | – | 980 check | **PASS** (0 lệch) |

`*` `legacy` OOM ngay chu kỳ 1 nên chưa kịp `sample()` ⇒ `peakUsed=0` (đúng như thiết kế bench: chết trước khi đo).
`*` `inplace` (bench) **không** OOM; FAIL chỉ vì tiêu chí PASS của bench dùng **peakUsed (rác chưa GC) > 200 MB**.
Bảng `ext` dùng **retained-sau-GC** ⇒ PASS (73 MB). `usedNow` mỗi chu kỳ tăng (98→256→350 MB) là **GC-lag của rác tạm
full-month/coin**, KHÔNG phải leak: sau `System.gc()` retained **phẳng 73–74 MB** ở mọi cấu hình.

## 4. TRẢ LỜI (4)

1. **`legacy @-Xmx512m` OOM thật?** **CÓ.** Log: `[BENCH] coins=0 cycles=3 peakUsed=0MB err=OutOfMemoryError: Java heap space`
   → `VERDICT FAIL` (rc=1). Nặng hơn: `legacy @-Xmx4g` **cũng OOM** — 1 bản sống **2.194 MB** (28,2M entry) ⇒ double-buffer > 4 g,
   **tái hiện đúng** OOM production.
2. **`inplace @-Xmx512m` PASS? peak MB?** **PASS, không OOM** (rc=0). **retained-sau-GC = 73 MB** (≈ 653×5×289 entry ≈ 940 k,
   khớp `~85 MB` trong `FIX_OOM_OI_LIVE.md`, đo được thấp hơn). `peakUsed`-dưới-churn: **350 MB @512m / 770 MB @4g** (rác chưa GC,
   không phải bộ nhớ sống). **Giảm ~30×** so legacy (2.194 → 73 MB sống).
3. **Kiểm đúng đắn `lookup` inplace == legacy?** **CÓ.** `OiReloadParityCheck`: `checks=980, mismatches=0` → `VERDICT PASS`
   (cắt 24h không đổi `lookup` với mọi `t` trong cửa sổ; merge_asof-backward tol 2h, 1 mốc ref set#1↔set#0).
4. **Kết luận / đủ điều kiện đề xuất (a) canary shadow?** **ĐỦ.** Fix **chứng minh được bằng bench**: (i) OOM tái hiện ở legacy
   cả 512m lẫn 4g; (ii) inplace bounded ~73–74 MB, không OOM; (iii) parity giữ trong cửa sổ 24h → đề xuất **canary shadow
   (owner duyệt)**. **Lưu ý giới hạn:** bench là **mô hình bộ nhớ thuần**, KHÔNG chạy code production
   (`LiveOiFeatProvider`/`getMetricMap242RecentBatchInto`, không Aerospike) ⇒ canary vẫn **bắt buộc** để xác nhận:
   `0` dòng OOM, RSS không tăng đơn điệu, dòng `inplace refresh … evicted=… size=…` xuất hiện, `[GATE]` ≥ 90 %, parity
   `n_pass`/symbol với 1 tick đối chứng jar cũ; theo dõi 15–30' đầu (điểm chết) **và** đủ 2 h; rollback = gỡ key + restart.

## 5. GHI CHÚ / CHƯA LÀM

- Ghi nhận: PASS nên dùng **retained-sau-GC** (đã làm trong `OiReloadHeapBenchExt`), không dùng `peakUsed` (nhiễm rác GC).
- Giữ nguyên jar `c389b4be…`; file bench nguồn khớp jar. Thêm 2 lớp dev-only: `OiReloadParityCheck`, `OiReloadHeapBenchExt`.
- KHÔNG deploy/restart/env; KHÔNG chạm 242/ONNX/LIVE/production; KHÔNG commit file dữ liệu; không chạm 2026.
- Slot Kaggle: chỉ dùng trong account; kernel private, CPU, ~1–3 phút/lần chạy.
