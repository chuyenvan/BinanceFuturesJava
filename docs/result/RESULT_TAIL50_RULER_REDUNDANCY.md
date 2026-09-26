# RESULT_TAIL50_RULER_REDUNDANCY — RÀO (b′) BỎ TOP-50 % + KIỂM TRÙNG LẶP 17 THƯỚC TAIL-ROBUST

Thực thi `docs/prereg/PREREG_TAIL50_RULER_REDUNDANCY.md` (commit `deb5b0c`, chốt **TRƯỚC** khi đo).
Thuần **Python offline** trên `printDone.csv` **đã có** (`research/analysis/tail50_ruler_redundancy.py`,
`docs/result/TAIL50_RULER_REDUNDANCY.json`, số thô `/tmp/t50/`). **KHÔNG** train/sim/Java, **KHÔNG** chạm
production/242/ONNX/LIVE, **KHÔNG** push. DEV only: mọi leg `start ≤ 2025-12-31`, **không đọc 2026**.
Corpus: **448 run DEV** (khối A) + **1 800 ô run×năm** (khối B). **Không** chạy lại vòng tail-robust
(phiên khác đang chạy) — chỉ đọc định nghĩa.

## 0. KẾT LUẬN NGAY (verdict)

1. **RÀO (b′) bỏ top-50 % ⇒ 0/8 biến thể DƯƠNG.** Tất cả **âm sâu** (từ **−3 357** đến **−155 919**).
   Ở bước 40 % cũng **0/8**; ở bước 30 % có **1/8** (`kg0-q998-15m` **+2 328**).
2. **Rào (a) `%PnL từ top-1 %` ≤ 15 %: 1/8 PASS** — chỉ `kg0-q998-15m` (**12,91 %**); 7 biến thể còn lại
   **20,70 – 40,85 %** đều FAIL.
3. **`median` PnL/leg DƯƠNG ở CẢ 8 biến thể** (+59,1 … +74,6) **nhưng** `TF(50 %)` **ÂM ở cả 8** ⇒
   **`median > 0` KHÔNG suy ra rào (b′)**. Điều kiện thật = *lãi TRUNG BÌNH của nửa dưới > 0*.
4. **NGƯỠNG GÃY `q*`** (bỏ-top nhỏ nhất làm `TF ≤ 0`): `T100` **5,5 %** · `GD92` **7,0 %** · `KEEPLEG0`
   **19,0 %** · `T170` **19,0 %** · `kg0-q995` **21,0 %** · `kg0-q999` **22,5 %** · `kg0-q998` **23,5 %** ·
   `kg0-q998-15m` **38,0 %**.
5. **TRÙNG LẶP 17 THƯỚC:** **0 đồng nhất thức đại số**; **1 cụm trùng thống kê** gồm **7 thước vị trí**
   (`wmean_p1p99`·`wmean_p5p95`·`tmean_1`·`tmean_5`·`tf_1`·`tf_5`·`tf_10`, **18 cặp** đạt `|ρ|≥0,9` ở
   **cả 2 khối**); **duy nhất 1 cặp `≥0,99`: `tmean_1`↔`tf_1`** (**0,996**).
6. **⚠️ PHÁT HIỆN QUAN TRỌNG — 2 thước BỊ TRÙNG CHÉO với bộ rate đã chốt:** `sign_frac` (tần suất
   `net>0`) ≡ `win%` (**ρ 0,999/0,993**) và ≈ `TSloss%` (**−0,990/−0,919**) ⇒ **trùng thước đã bị hạ cấp**;
   `loss_mean` ≈ `mP|SL` (**−0,959/−0,890** · B **−0,911/−0,932**) ⇒ **trùng `mP|SL`**. **Cả 2 KHÔNG được**
   vào bộ chuẩn tail-robust. ⇒ **bộ chuẩn tối thiểu đề xuất = `median` · `wl_ratio` · `conc_5`** (3 thước).
7. **KHÔNG biến thể nào đủ go-live** dưới rào (a)+(b′). **Mắt xích phải đổi = MẤT CÂN XỨNG LỚN/THUA**
   (`mean |pnl| leg lỗ` = **2,9–3,6×** `mean` leg lãi, TB **≈3,1×**) — tức **luật thoát / cấu trúc lại**, không
   phải chỉnh ngưỡng `q`.

---

## 1. VIỆC 1 — RÀO (a)/(b′) BỎ TOP-30/40/50 % (toàn kỳ)

`TF(x %)` = `Σpnl` sau khi bỏ `k = max(1, ⌈x·n/100⌉)` leg **tốt nhất** (`pnl` = USDT/leg ròng, DEV).

| biến thể | n | `top-1 %`(a) | PASS a | `median`/leg | **TF30** | **TF40** | **TF50** | PASS b′ 30/40/50 | `q*` |
|---|---:|---:|:--:|---:|---:|---:|---:|:--:|---:|
| `KEEPLEG0` | 1 085 | 23,74 % | FAIL | +70,0 | −14 532 | −24 768 | **−33 196** | F/F/F | 19,0 % |
| `T100` | 2 559 | 40,85 % | FAIL | +70,6 | −109 754 | −135 493 | **−155 919** | F/F/F | 5,5 % |
| `GD92` | 2 632 | 37,75 % | FAIL | +63,7 | −91 761 | −115 581 | **−134 390** | F/F/F | 7,0 % |
| `kg0-q995` | 1 021 | 21,58 % | FAIL | +71,7 | −11 554 | −21 369 | **−29 512** | F/F/F | 21,0 % |
| `kg0-q998` | 954 | 20,70 % | FAIL | +72,5 | −7 515 | −16 820 | **−24 511** | F/F/F | 23,5 % |
| `kg0-q999` | 868 | 21,04 % | FAIL | +74,6 | −7 726 | −16 256 | **−23 257** | F/F/F | 22,5 % |
| `T170` | 1 089 | 25,90 % | FAIL | +74,2 | −15 529 | −26 503 | **−35 416** | F/F/F | 19,0 % |
| `kg0-q998-15m` | 420 | **12,91 %** | **PASS** | +59,1 | **+2 328** | −686 | **−3 357** | **P**/F/F | 38,0 % |

**Đồng nhất thức kiểm đúng 8/8:** `TF50 % ≡ Σ pnl` của `n−k` leg **nhỏ nhất** ("nửa dưới"), lệch **0**.
⇒ **0/8 PASS (b′)-50 %; 0/8 PASS (b′)-40 %; 1/8 PASS (b′)-30 %.**

### 1b. Đường cong `TF(x)` — PnL sau khi bỏ `x %` (đơn vị USDT)

| biến thể | x0 | x5 | x10 | x20 | x30 | x40 | x50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `KEEPLEG0` | 68 083 | 30 416 | 16 360 | −1 575 | −14 532 | −24 768 | −33 196 |
| `T100` | 86 770 | 2 771 | −31 294 | −76 850 | −109 754 | −135 493 | −155 919 |
| `GD92` | 98 944 | 14 794 | −18 167 | −61 183 | −91 761 | −115 581 | −134 390 |
| `kg0-q995` | 64 531 | 31 099 | 17 918 | +772 | −11 554 | −21 369 | −29 512 |
| `kg0-q998` | 62 674 | 32 292 | 19 999 | +4 180 | −7 515 | −16 820 | −24 511 |
| `kg0-q999` | 55 699 | 28 379 | 17 449 | +2 901 | −7 726 | −16 255 | −23 257 |
| `T170` | 76 070 | 32 922 | 17 650 | −1 723 | −15 529 | −26 503 | −35 416 |
| `kg0-q998-15m` | 21 149 | 14 043 | 10 512 | +5 848 | +2 328 | −686 | −3 357 |

### 1c. `TF30/40/50` theo TỪNG NĂM (`end.year`, năm ≥ 5 leg)

| biến thể | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| `KEEPLEG0` | T30 +465 · T50 −873 | T50 −5 094 | T30 +1 801 · T40 +348 · T50 −950 | T50 −5 633 | T50 −18 171 |
| `T100` | T50 −7 137 | T50 −12 452 | T30 +2 975 · T50 −3 222 | T50 −29 579 | T50 −96 186 |
| `GD92` | T50 −7 452 | T50 −13 828 | T30 −606 · T50 −8 544 | T50 −39 027 | T50 −57 385 |
| `kg0-q995` | T30 +637 · T50 −763 | T50 −4 179 | T30 +1 858 · T40 +360 · T50 −980 | T50 −5 738 | T50 −15 448 |
| `kg0-q998` | **T30/T40/T50 +** (1 559/901/325) | T50 −3 538 | T30/T40 + · T50 −981 | T50 −5 819 | T50 −12 761 |
| `kg0-q999` | **T30/T40/T50 +** (1 260/657/134) | T50 −2 933 | T30/T40 + · T50 −973 | T50 −5 416 | T50 −12 660 |
| `T170` | T30 +465 · T50 −873 | T50 −4 199 | T30 +1 913 · T40 +370 · T50 −1 009 | T50 −5 983 | T50 −20 478 |
| `kg0-q998-15m` | T30/T40 + · T50 −371 | T30/T40 + · T50 −227 | **T30/T40/T50 +** (623/449/214) | T50 −1 957 | T30 +261 · T50 −909 |

**Năm duy nhất có `TF50 > 0`:** `kg0-q998` 2021 (+325) · `kg0-q999` 2021 (+134) · `kg0-q998-15m` 2023 (+214).
**Không biến thể nào `TF50 > 0` ở ≥ 2 năm.** `2025` (năm mới nhất) **âm ở cả 8**.

---

## 2. VIỆC 2 — MA TRẬN TRÙNG LẶP 15/17 THƯỚC TAIL-ROBUST (448 run DEV)

`net_leg = pnl/margin` (lợi suất trên ký quỹ/leg, không đơn vị — khớp "phân số" của prereg gốc).
**17 thước:** 15 tính được trên run; **`ic_wmean`/`ic_med` KHÔNG tính được** (cần **điểm đối tượng** căn pool;
`pred15m` là 1 feature cố định, không phải điểm đang chấm) ⇒ **loại khỏi ma trận** (vẫn được vòng
`PREREG_TAIL_ROBUST_RULERS` đo trên pool P32).

### 2a. Trùng ĐẠI SỐ: **0 cặp** (không cặp nào là hàm affine `u=a·v+b`, `rel_resid ≤ 1e-6` trên ≥95 % run).

### 2b. Trùng THỐNG KÊ — **18 cặp đạt `|ρ|≥0,9` ở CẢ 2 khối** (đều nằm trong **CỤM VỊ TRÍ 7 thước**)

| # | u | v | Pearson A | Spearman A | Pearson B | Spearman B |
|---|---|---|--:|--:|--:|--:|
| 1 | `tmean_1` | `tf_1` | **0,996** | **0,997** | **0,996** | **0,994** |
| 2 | `wmean_p1p99` | `tf_1` | 0,994 | 0,988 | 0,990 | 0,988 |
| 3 | `wmean_p1p99` | `tmean_1` | 0,991 | 0,988 | 0,993 | 0,992 |
| 4 | `wmean_p5p95` | `tmean_1` | 0,988 | 0,990 | 0,991 | 0,987 |
| 5 | `tf_5` | `tf_10` | 0,988 | 0,992 | 0,994 | 0,993 |
| 6 | `wmean_p5p95` | `tf_1` | 0,982 | 0,987 | 0,988 | 0,985 |
| 7 | `wmean_p1p99` | `wmean_p5p95` | 0,968 | 0,971 | 0,974 | 0,969 |
| 8 | `wmean_p5p95` | `tf_5` | 0,962 | 0,964 | 0,972 | 0,961 |
| 9 | `tf_1` | `tf_5` | 0,958 | 0,964 | 0,975 | 0,962 |
| 10 | `tmean_1` | `tf_5` | 0,952 | 0,960 | 0,961 | 0,946 |
| 11 | `tmean_1` | `tmean_5` | 0,937 | 0,968 | 0,968 | 0,963 |
| 12 | `wmean_p5p95` | `tmean_5` | 0,933 | 0,974 | 0,976 | 0,971 |
| 13 | `tmean_5` | `tf_5` | 0,925 | 0,978 | 0,961 | 0,953 |
| 14 | `wmean_p1p99` | `tf_5` | 0,923 | 0,930 | 0,938 | 0,916 |
| 15 | `wmean_p5p95` | `tf_10` | 0,914 | 0,935 | 0,946 | 0,932 |
| 16 | `tmean_5` | `tf_1` | 0,912 | 0,964 | 0,959 | 0,955 |
| 17 | `tf_1` | `tf_10` | 0,906 | 0,935 | 0,949 | 0,934 |
| 18 | `tmean_5` | `tf_10` | 0,904 | 0,963 | 0,947 | 0,935 |

**`|ρ| ≥ 0,99` (cả 2 khối): DUY NHẤT 1 cặp — `tmean_1`↔`tf_1` (0,996 / 0,997 · 0,996 / 0,994).**
⇒ **Cả cụm 7 thước VỊ TRÍ chỉ mang ~1 lượng thông tin**; giữ **tối đa 1**.
**`conc_1`↔`conc_5`**: `|ρ|≥0,9` **chỉ ở khối A** (0,988/0,902) — khối B `Spearman 0,820 < 0,9` ⇒
theo luật (đạt **cả 2 khối**) **KHÔNG** gọi trùng, nhưng **giữ tối đa 1** (`conc_5`).
**`median`** và **`sign_frac`**: `Pearson A 0,925` nhưng **`Spearman A 0,266`** ⇒ **KHÔNG trùng** (Median
và tần suất là 2 lượng khác nhau — `median` bền đuôi, không bị tần suất chi phối).

### 2c. ⚠️ TRÙNG **CHÉO** với bộ rate đã chốt `{TSloss %, mP|SM, mP|SL, mMargin}`

| thước tail | rate | Pearson A | Spearman A | Pearson B | Spearman B | kết luận |
|---|---|--:|--:|--:|--:|---|
| `sign_frac` | `win %` | **0,999** | **0,993** | **0,998** | **0,992** | **≡ win %** ⇒ DÙNG LẠI thước đã hạ cấp |
| `sign_frac` | `TSloss %` | **−0,990** | **−0,919** | **−0,969** | −0,796 | phụ thuộc gần-tuyệt-đối (cấp run) |
| `loss_mean` | `mP\|SL` | **−0,959** | −0,890 | **−0,911** | **−0,932** | **≈ phản ảnh của `mP\|SL`** |
| `median` | `TSloss %` | −0,907 | −0,213 | −0,857 | −0,115 | **OK** (Spearman thấp ⇒ không trùng) |
| `wl_ratio` | `TSloss %` | 0,911 | 0,006 | 0,815 | 0,097 | **OK** |
| `max_loss` | (mọi rate) | ≤0,46 | ≤0,46 | ≤0,60 | ≤0,60 | **OK, độc lập nhất** |
| `conc_5`/`conc_1`/`hhi_gain` | (mọi rate) | ≤0,29 | ≤0,67 | ≤0,35 | ≤0,41 | **OK** |
| `tf_5` | (mọi rate) | ≤0,69 | ≤0,69 | ≤0,49 | ≤0,51 | **OK** |

⇒ Bộ rate đã chốt **đã bao trùm** khía cạnh **tần suất thắng** (`TSloss %`/`win %`) và **độ lớn thua
trung bình** (`mP|SL`). Vì vậy **`sign_frac` và `loss_mean` KHÔNG được tính là bằng chứng mới**.

### 2d. ĐỀ XUẤT — **BỘ CHUẨN TAIL-ROBUST TỐI THIỂU** (luật B1–B4, chốt trước)

Chạy luật: (B2) loại thước trùng chéo bộ rate → **loại `sign_frac`, `loss_mean`**; (B1/B3) mỗi khía cạnh lấy
thước ưu tiên cao nhất, không trùng trong họ; (B4) phủ ≥3 khía cạnh.

> ### BỘ CHUẨN = **`median` · `wl_ratio` · `conc_5`** (3 thước)
>
> | khía cạnh | thước | lý do |
> |---|---|---|
> | **vị trí** (bền đuôi) | **`median`** | ưu tiên #1 (D3); độc lập mọi thước/cụm (ρ&lt;0,71) |
> | **bất đối xứng lãi/lỗ** | **`wl_ratio`** | độc lập với rate (Spearman ≈0); `loss_mean` bị loại vì trùng `mP\|SL` |
> | **tập trung lợi nhuận** | **`conc_5`** | độc lập rate; giữ nó, bỏ `conc_1` (trùng cấp run) |
>
> Cặp trong bộ (đều **KHÔNG** đạt `|ρ|≥0,9` cả 2 khối):
> `median`↔`wl_ratio` (−0,88/**−0,01** · −0,76/0,16) · `median`↔`conc_5` (−0,02/−0,70 · −0,03/−0,33) ·
> `wl_ratio`↔`conc_5` (0,04/−0,02 · 0,03/−0,13).
>
> **Khía cạnh "tần suất thắng" KHÔNG có thước độc lập** (ứng viên duy nhất `sign_frac` đã trùng `TSloss %`)
> ⇒ khía cạnh này **để bộ rate lo** — đúng luật B2.
> **Phương án thay thế (nếu muốn 1 thước "tail-free mean"):** thêm **`tf_5`** (độc lập với cả 3: ρ≤0,69) ⇒
> bộ 4. **Loại khỏi bộ chuẩn:** `wmean_p1p99`·`wmean_p5p95`·`tmean_1`·`tmean_5`·`tf_1`·`tf_10` (trùng `tf_5`),
> `sign_frac`+`loss_mean` (trùng chéo rate), `conc_1` (trùng `conc_5` cấp run), `hhi_gain` (chỉ khi cần
> khía cạnh tập trung thứ 2). **`ic_wmean`/`ic_med`**: chưa chấm được ở panel run (xem §2).

---

## 3. TRẢ LỜI (1)–(4)

**(1) Rào (b′) bỏ-50 %: biến thể nào DƯƠNG?** **KHÔNG có biến thể nào — 0/8.** Âm sâu nhất `T100`
(−155 919), nhẹ nhất `kg0-q998-15m` (−3 357). Ở bước 40 % cũng **0/8**; bước 30 % có **1/8**
(`kg0-q998-15m` +2 328). Theo từng năm, `TF50 > 0` chỉ ở **3 ô lẻ** (2021×2, 2023×1) — không biến thể nào
dương ở 2+ năm.

**(2) `q*` + `median` PnL/leg:** `T100` `q*` **5,5 %** · `GD92` **7,0 %** · `KEEPLEG0`/`T170` **19,0 %** ·
`kg0-q995` **21,0 %** · `kg0-q999` **22,5 %** · `kg0-q998` **23,5 %** · `kg0-q998-15m` **38,0 %**.
`median`/leg: **+59,1 … +74,6 USDT (DƯƠNG cả 8)** — nhưng `TF50` âm cả 8 ⇒ **`median>0` ≠ rào (b′)**.

**(3) Cặp thước tail-robust TRÙNG ⇒ bộ tối thiểu:** **18 cặp `|ρ|≥0,9`** (cả 2 khối) đều trong **cụm vị trí
7 thước**; `≥0,99` chỉ **`tmean_1`↔`tf_1`**. **Trùng chéo bộ rate:** `sign_frac`↔`win %`/`TSloss %`,
`loss_mean`↔`mP|SL`. ⇒ **Bộ chuẩn tối thiểu = `median` · `wl_ratio` · `conc_5`** (+`tf_5` nếu muốn 4),
**không giao** với `{TSloss %, mP|SM, mP|SL, mMargin}`.

**(4) Dưới rào (a)+(b′) có biến thể nào đủ go-live?** **KHÔNG.** (a) giết 7/8; (b′)-50 % giết 8/8; biến thể
duy nhất qua được (a) là `kg0-q998-15m` cũng **âm ở (b′) 50 %** (và nhịp 15′ **không tái lập được** nhịp
live 1′). **Mắt xích phải thay đổi (theo số, không phải theo cảm nhận):** **MẤT CÂN XỨNG ĐỘ LỚN** —
`mean|pnl| leg lỗ` = **2,9–3,6×** `mean` leg lãi (TB **≈3,1×**) ⇒ **nửa dưới lệnh âm nặng**. Muốn qua (b′) phải **cấu trúc lại
luật thoát / nhóm lệnh** (cắt lỗ ngắn hơn **hoặc** để lãi chạy dài hơn), **KHÔNG** phải hạ/tinh chỉnh ngưỡng
`q` (mọi `q` đều gãy trước 50 %, `q*` = 5,5–38 %).

---

## 4. RÀNG BUỘC ĐÃ TUÂN THỦ

Offline Python, **không** train/sim/Java; **không** chạm production/242/ONNX/đường LIVE; **không** push git.
DEV `≤ 2025-12-31`, **không** đọc 2026. Không chạy lại vòng `PREREG_TAIL_ROBUST_RULERS` (phiên khác đang
chạy) — chỉ **đọc** định nghĩa. JSON **58,7 KB**.
