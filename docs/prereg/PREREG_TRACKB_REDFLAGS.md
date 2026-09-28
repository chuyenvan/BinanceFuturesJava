# PREREG_TRACKB_REDFLAGS — gỡ 3 cờ đỏ Track B (0 sim)

Ngày chốt: **2026-09-28** (D4). **CHỐT TRƯỚC khi đo bất kỳ số nào của D4.**
Sau khi đo **không sửa thiết kế**; mọi thứ không có trong file này là **post-hoc** (dán nhãn).

Ràng buộc thi hành: thuần **Python offline**; **0 train / 0 sim**; **không** chạm production /
`242` / ONNX / đường LIVE; **không push file dữ liệu** (chỉ `.md`/`.json`/`.py`/`.pyc` sinh ra);
**DEV ≤ 2025-12-31** (không chạm 2026); file trung gian **nhỏ**, **dọn sau commit**.
Code: `research/trackb/redflags_trackb.py` (dùng lại `run_trackb.py`/`build_panel.py`).
Kết quả: `docs/result/RESULT_TRACKB_REDFLAGS.md` (+ `docs/result/trackb_redflags.json`).

---

## 0. BỐI CẢNH (số ĐÃ đo — không tính lại)

`RESULT_TRACKB_STEP1` §3 + `RESULT_BOOK_COST2` §4:

- `BOOK_EW` (4 tín hiệu, band 2) gross **+0,1398 %/ngày**, TO **0,351/ngày**;
  ở phí có hướng `0,112 %/vòng` net **+0,1059 %/ngày** (`CI95 [+0,0615;+0,1502]`).
- **Đối chứng coin ngẫu nhiên**: gross **+0,0642 %/ngày**, TO **0,872/ngày**.
- 3 cờ đỏ phải gỡ: **(#1)** đối chứng neutral-ngẫu-nhiên phải ~0 lại có gross `+0,064`;
  **(#2)** đối chứng KHÔNG cùng turnover (0,872 vs 0,351); **(#3)** `vol` có thể là **beta alt**, không alpha.

---

## 1. VIỆC 1 — GỠ CỜ ĐỎ #1 (bias harness): TÁI LẬP + PHÂN RÃ 3 NGUỒN

**Tái lập (bắt buộc):** đối chứng ngẫu nhiên `n=200`, seed `20260928`, universe **TĨNH** top-200 theo
`dv_med` toàn kỳ, cùng stop −10 %, cùng harness ⇒ kỳ vọng tái lập **gross `+0,064 %/ngày` (±0,010)**.

**Phân rã bằng THIẾT KẾ 2×2** (mọi ô cùng `n=200`, seed `20260928`, cùng 1 460 ngày 2022-01-01…2025-12-30):

| ô | universe | stop −10 % | tên |
|---|---|---|---|
| A | TĨNH (`dv_med` toàn kỳ) | CÓ | **A = tái lập** |
| B | TĨNH | KHÔNG | B |
| C | **AS-OF** (chỉ mẫu dv `< t`) | CÓ | C |
| D | AS-OF | KHÔNG | D |

- **(b) stop −10 %**: đóng góp `= A − B` (tại TĨNH) và `= C − D` (tại AS-OF); báo cả hai.
- **(a) universe tĩnh**: đóng góp `= A − C` (có stop) và `= B − D` (không stop); báo cả hai.
- **(c) trọng số L/S lệch**: đo **trực tiếp** bằng 2 ô phụ (cùng TĨNH, CÓ stop):
  `c1` = long/short **lệch SỐ chân** (n_long = 2·n_short) nhưng **vẫn dollar-neutral** (mỗi chân gross 0,5);
  `c2` = lệch **GROSS** (long 0,55 / short 0,45). Báo `gross(c1) − gross(A)` và `gross(c2) − gross(A)`.

**Định nghĩa AS-OF (chốt trước, CAUSAL):** tại ngày `t` (00:00 UTC), universe = top-200 theo **trung vị
`dv` của các mẫu ngày-15 có ngày `< t`**; cần **`≥ 12` mẫu quá khứ**; nếu `< 12` ⇒ ngày đó **không giao dịch**.
(Lưu ý: `dv` mẫu tháng `m` được coi là có sẵn từ **00:00 ngày-15 tháng `m`** — ngày-15 là mốc đã chốt ở
step 1; dùng `sample_date < t` để **không nhìn tương lai**.)

**TIÊU CHÍ GỠ ĐƯỢC CỜ ĐỎ #1** (cả ba):
1. Tái lập `|A − 0,0642| ≤ 0,010 %/ngày`;
2. **giải thích được ≥ 75 %** của `0,0642 %/ngày` bằng tổng đóng góp **có tên** của (a)+(b)+(c)
   (dấu đúng; tổng ≥ `0,048 %/ngày`);
3. sau khi áp BẢN SỬA (universe AS-OF **và** control được xử lý để đối xứng), **`|gross(control)| ≤ 0,020 %/ngày`**.

---

## 2. VIỆC 2 — GỠ CỜ ĐỎ #2 (turnover): CONTROL CÙNG BAND/HYSTERESIS

Control **cùng cơ chế** với book thật: dùng **cùng decile + cùng hysteresis `band=2` + cùng trần squeeze +
cùng stop**, chỉ thay tín hiệu thật bằng **tín hiệu NGẪU NHIÊN** (i.i.d. và AR(1)).

- `RAND_iid`: mỗi ngày, mỗi coin một `u ~ Uniform(0,1)` độc lập (seed `20260928`).
- `RAND_ar1(ρ)`: `z[t] = ρ·z[t−1] + √(1−ρ²)·ε[t]`, `ε ~ N(0,1)`; **`ρ` hiệu chỉnh (chốt 1 giá trị) sao cho
  turnover trung bình khớp book ±10 %**; nếu không đạt trong `ρ ∈ {0,0,05,…,0,98}` ⇒ báo `ρ*` gần nhất.
- `n` control cho mỗi loại: **200** book độc lập (seed cố định).

**Báo cáo:** `TO/ngày`, `gross/ngày`, `net/ngày` cho book và cho 2 control; **chênh gross `book − control`**
ở **cùng turnover** (khớp ±10 %) **+ CI block**.

**TIÊU CHÍ GỠ ĐƯỢC CỜ ĐỎ #2** (cả hai):
1. `|TO(control) − TO(book)| / TO(book) ≤ 10 %`;
2. **chênh gross (`book − control`, cùng turnover) có `CI95` raw95 (khối **3 ngày = 72h**) `> 0`.
   Đồng thời báo thêm khối **10 ngày** (giữ tương thích step 1).

---

## 3. VIỆC 3 — GỠ CỜ ĐỎ #3 (`vol` = beta?): HỒI QUY THEO BETA

Hồi quy **PnL NGÀY** (cả `gross` và `net` @ phí `0,112 %`) của book (`vol` riêng + `BOOK_EW`) trên:

- `r_btc[t] = close_btc[t+24h]/close_btc[t] − 1` (BTC trong panel),
- `r_altEW[t] = mean_{i ∈ eligible(t)} (close_i[t+24h]/close_i[t] − 1)` (chỉ số alt EW, **cùng universe**).

Mô hình: `pnl[t] = α + β_btc·r_btc[t] + β_alt·r_altEW[t] + ε[t]`.
Hệ số **`α`** = phần **alpha sau khi trừ beta**. CI của `α`, `β` bằng **block bootstrap khối 3 ngày (72h)**,
NREP 2000, seed `20260905`; báo thêm khối 10 ngày. Báo `R²`, `β_btc`, `β_alt` **đã chuẩn hoá** (beta trên 1 đơn vị).

**TIÊU CHÍ GỠ ĐƯỢC CỜ ĐỎ #3:** **`α > 0`** và **`CI95(α)` (khối 3 ngày) `> 0`** ⇒ alpha không phải beta.
Nếu **`α ≈ 0`** (CI chứa 0) ⇒ **`vol` là BETA/regime**, **KHÔNG** phải alpha ⇒ nói rõ và **không** tính alpha.

---

## 4. THAM SỐ CỐ ĐỊNH (chốt trước)

`NREP = 2000` · `seed_boot = 20260905` · `seed_control = 20260928` · `k (inflate) = 8` (`inflate(8)=2,0393`) ·
`block_72h = 3 ngày` (**chính** cho D4) + `block_10d` (phụ) · `n_control = 200` · phí: **`0,112 %/vòng`**
(chi phí có hướng, `C(2 000)` median) làm chính; báo thêm `0,414 %` (hoà vốn) · cửa sổ
**2022-01-01 … 2025-12-30** (1 460 ngày) · stop `−10 %`, slip `0,5 %` · decile `10 %`, `band=2` ·
trần squeeze `2×`.

## 5. LUẬT KẾT LUẬN (chốt TRƯỚC)

**Track B ĐƯỢC lên bước 2** ⟺ **cả 3 cờ đỏ GỠ ĐƯỢC** theo tiêu chí §1/§2/§3 ở trên.
**KHÔNG** lên bước 2 nếu bất kỳ cờ đỏ nào còn. Mọi kết luận dừng ở **nghiên cứu DEV**, **không deploy**.

## 6. OUTPUT

`docs/prereg/PREREG_TRACKB_REDFLAGS.md` + `research/trackb/redflags_trackb.py` +
`docs/result/RESULT_TRACKB_REDFLAGS.md` + `docs/result/trackb_redflags.json` (**nhỏ**). Commit + **push**.
