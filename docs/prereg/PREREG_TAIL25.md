# PREREG_TAIL25 — ĐO LẠI RÀO (b′) ĐÚNG MỨC **BỎ TOP-25 %** + TỔNG HỢP PASS/FAIL (a)+(b′)

Chốt **TRƯỚC khi đo** (2026-09-28 16:0x GMT+7, sau quyết định owner 15:51). Thuần **Python offline**
trên Oracle; **KHÔNG** train, **KHÔNG** sim/Java, **KHÔNG** chạm production/`242`/ONNX/LIVE, **KHÔNG push
file dữ liệu**. DEV only: mọi leg **`start <= 2025-12-31 23:59`**, **không đọc 2026**. Code:
`research/analysis/tail25_ruler.py`. Kết quả: `docs/result/RESULT_TAIL25.md`
(+ `docs/result/TAIL25_RULER.json`). Số thô: `/tmp/t25/`. Output **NHỎ** (`df -h /` ~93 %).

## 0. ĐỘNG CƠ (quyết định owner — nguồn chân lý)

> *"a. giữ 15 %  b giảm 50 % về 25 nhé"* — owner 28/09 15:51 (`RULERS_CURRENT.md` §12, `b3d18b0`).

- **(a)** `%PnL từ top-1 % lệnh ≤ 15 %` — **GIỮ NGUYÊN**.
- **(b′)** **BỎ TOP-25 % lệnh ⇒ PnL vẫn phải DƯƠNG** (thay cho bỏ top-50 %).
- Mốc đã đo (`76cc051`): bỏ **20 %** = 4/8 dương · bỏ **30 %** = 1/8 · bỏ **50 %** = 0/8.
  Mức **25 % nằm giữa 20 % và 30 %** ⇒ **phải đo đúng 25 %**, **KHÔNG** suy diễn nội suy.

## 1. ĐỐI TƯỢNG & NGUỒN (khai báo trước, không đổi)

- **Tám biến thể** (đúng `TARGETS` của `tail50_ruler_redundancy.py` / `rate_redundancy.py`):
  `KEEPLEG0` · `T170` · `T100` · `GD92` · `kg0-q995` · `kg0-q998` · `kg0-q999` · `kg0-q998-15m`;
  thư mục tại `/home/ubuntu/kaggle_sim/out` (hoặc `/home/ubuntu/java/devrun`), dữ liệu `storage/printDone.csv`.
- **Nguồn leg = artifact `printDone.csv` từng biến thể** — **đúng nguồn đã sinh `76cc051`**, để sanity
  bước 20 %/30 % phải tái lập khớp. **KHÔNG** build lại, **KHÔNG** sim.
- **Pool `P32` = `label_b_pnl.parquet`** (32 leg/tick, KHÔNG gate): là pool **không mã hoá cấu hình** của 8
  biến thể (không cột nào tái tạo được gate `q995/q998/q999/15m/T100/GD92`), nên **không thể** tái lập
  `76cc051`. ⇒ Vòng này **KHÔNG** dùng `P32` làm nguồn leg; ghi rõ để khỏi hiểu nhầm. (Pool mở rộng cũng vậy.)
- **Thang đo tiền:** cột **`pnl` (USDT/leg, ròng)** — đúng cột đã dùng cho rào vòng trước.

## 2. VIỆC 1 — RÀO (b′) & (a) (định nghĩa chốt trước)

Với vector `P = pnl` của `n` leg, sắp `o = sort(P)` giảm dần.
**`TF(x %)` = `Σ o[k:]`**, `k = max(1, ⌈x·n/100⌉)` ⇒ **bỏ `k` leg TỐT NHẤT**. **PASS (b′)** ⟺ `TF(25 %) > 0`.

- **Bước đo `x` = {0, 5, 10, 15, 20, 25, 30} %** — **toàn kỳ** và **TỪNG NĂM** (`end.year`, năm ≥ 5 leg).
  Ghi **dấu** từng mức.
- **Mức 25 % chính xác:** giá trị + **CI**. **CI = bootstrap KHỐI `72 h`** (khối `ts//(72·3.600.000)`),
  **2000 rep**, **seed `20260905`**, mỗi rep: resample khối có hoàn lại → ghép leg → **bỏ top-25 % của rep → Σ**.
  **`inflate(k)`** import từ `c3_rates.inflate`, **`k = 8`** (8 biến thể trong vòng này) ⇒ `inflate(8)=√(2·ln8)=2,0393`.
  Báo thêm `raw95`. **Kết luận "ngoài CI"** ⟺ **ngoài `raw95`** **VÀ** **ngoài `inflate(8)`**.
- **`q*`** = bước **0,5 %** nhỏ nhất làm `TF(x) ≤ 0` (binh pháp vòng trước).
- **Rào (a):** `share_top1_pct = Σ(k=⌈0,01n⌉ leg tốt nhất)/Σpnl · 100`; **PASS** ⟺ `≤ 15 %`.
- **Sanity (BẮT BUỘC):** `TF(20 %)` và `TF(30 %)` phải **tái lập đúng** số `76cc051` (`rate_redundancy`):
  TF20 = `q995 +772` · `q998 +4180` · `q999 +2901` · `q998-15m +5848`; `KEEPLEG0 −1575` · `T170 −1723` ·
  `GD92 −61183` · `T100 −76850`; TF30 = `q998-15m +2328` + 7 mức âm. **Lệch ⇒ DỪNG và báo rõ.**

## 3. VIỆC 2 — BẢNG TỔNG HỢP PASS/FAIL

Bảng **8 biến thể × [(a) PASS/FAIL · giá trị · (b′) 25 % PASS/FAIL · giá trị + CI · `q*`]**.
**Kết luận: có biến thể nào PASS CẢ HAI không.** Nếu **có** ⇒ kiểm thêm **bài kiểm nhịp**
(`q998-15m` nhịp 15′ **không** tái lập nhịp live 1′, tỷ lệ **0,440 < 0,60** ⇒ **có thể vẫn KHÔNG deploy được**).
Nếu **0** ⇒ nói rõ dưới **(a)=15 % + (b′)=25 %** không cấu hình nào đủ go-live, và nêu **2 lựa chọn**:

1. **Nâng (a)** lên mức nào đó **vừa đủ** bao các arm hiện có (dùng đúng số đã đo: (a) các arm `q995/q998/q999`
   ≈ `20,7–23,5 %` ⇒ nâng (a) lên **~24 %** mới phủ hết `kg0-q99x`; `T170` 25,9 % · `KEEPLEG0` 23,74 % ·
   `GD92` 37,75 % · `T100` 40,85 % vẫn ngoài tầm ⇒ chỉ cứu được nhóm `kg0-q99x`).
2. **Đổi họ chiến lược ở phía TÍN HIỆU** (không chỉnh ngưỡng `q`) — như kết luận `76cc051` §(4):
   mắt xích phải đổi = **mất cân xứng độ lớn** (`|loss|/win = 2,9–3,6×`).

## 4. KHAI BÁO TRƯỚC KỲ VỌNG

Theo số đã đo: `TF(20 %)` có **4/8** dương, `TF(30 %)` có **1/8**. `TF(25 %)` **dự kiến** nằm trong
`[1/8 ; 4/8]` — **không** suy diễn thêm. Rào **(a)** giết `q995/q998/q999` (≈ 20,7–23,5 %) ⇒ **dự kiến
PASS CẢ HAI ≈ 0–1** (chỉ có thể là `kg0-q998-15m` — nhưng đã biết **trượt bài kiểm nhịp**).
