# RESULT_K_SWEEP — Nới `K` (top-K theo S1 mỗi tick) trên **thước TIỀN**: 8 → 10 → 12 (+ 16/32 bối cảnh)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_K_SWEEP.md` (commit `f368ffe`) — chốt **TRƯỚC** khi đọc số.
**Code:** `research/analysis/k_sweep_score.py` (mới) · dùng **NGUYÊN** `model_ruler.ci_mean` →
`stage2_score.block_boot_mean` + `c3_rates` (`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`).
**Số thô:** `docs/result/k_sweep.json` (46 KB).
**Đường RE — KHÔNG build lại gì:** pool **P32 đã là top-32 theo S1 mỗi tick** ⇒ `top-K = rank < K` cắt ra
**từ chính pool**. **KHÔNG** chạy lại exit engine, **KHÔNG** train, **KHÔNG** sim/Java, **KHÔNG** đọc bins.
**CHI PHÍ ĐO: 6 giây** (1 lần đọc 10,7 MB parquet; `free -g` trước khi chạy = 23 GB tổng / 15 GB rảnh) ⇒
**không** cần Kaggle.

**Kiểm nguồn (đã làm):** `/tmp/mrout/mrout/label_b_pnl.parquet` **CÓ** (`sha256 1d42b7f6…` = sha ghi trong
PREREG) ⇒ **không phải build lại** (đúng điều kiện PREREG §9). Vì `/tmp` có thể bị xoá, đã **copy bền** sang
`/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (**sha khớp** `1d42b7f6…`).
**Cross-check độc lập:** tập `rank < 8` của pool = **đúng** `label_b_K8.parquet` (77.256 dòng, **tập
`(ts, symId)` khớp 100 %**, `y` khớp tới **3e-8** = làm tròn float32) ⇒ định nghĩa `top-K = rank < K` là
**đúng** định nghĩa đã dùng ở vòng build nhãn.

---

## 0. TRẢ LỜI NGẮN (4 câu của đề bài)

### (1) Nới `K` lên 10 / 12 có làm **net trên 1 đơn vị gross exposure** tốt hơn **ngoài CI** không? → **KHÔNG**

`Δnet_gross = R_K(f) − R_8(f)`, **bootstrap tỉ số ghép cặp** cùng khối 72h. **KHÔNG** mức phí nào,
**KHÔNG** `K` nào **ngoài CI** — kể cả `raw95` (bảng đầy đủ §3):

| `Δ` (×10⁻⁴) | f = 0 (gross) | f = 0,004 | f = 0,008 (HIỆN HÀNH) | f = 0,012 | CI5 (rộng nhất) |
|---|---|---|---|---|---|
| **K = 10 − 8** | +0,007 | +0,014 | +0,021 | +0,027 | [−0,39 ; +0,43] |
| **K = 12 − 8** | +0,057 | +0,072 | **+0,087** | +0,101 | [−0,60 ; +0,73] |
| **K = 16 − 8** | +0,033 | +0,063 | +0,093 | +0,123 | [−0,97 ; +1,05] |
| **K = 32 − 8** | **−0,128** | −0,047 | +0,035 | +0,117 | [−1,47 ; +1,35] |

**Đọc:** điểm ước lượng **dương nhưng nhỏ hơn cận CI ~8–10 lần** ⇒ **không phân biệt được với 0**. Ở
`f = 0,012` các `K > 8` **nhích** dương (gross hoà vốn cao hơn ~0,06–0,12 pp/1đv) nhưng vẫn **trong CI**.
Thêm một sự thật **quan trọng cho câu (2):** **`K = 32` ÂM** ở `f = 0` (`−0,128e-4`) ⇒ quan hệ **KHÔNG đơn điệu**.

### (2) Có **điểm `K` tối ưu** không? → **KHÔNG phân biệt được**; quan hệ **gần PHẲNG, hơi gồ lên ở `K = 12`**

`net_gross_K(f) = net_tick_K(f) / Ē_K` (%/tick/1 đơn vị gross), 4 mức phí (bảng §2):

| `K` | 8 | 10 | **12** | 16 | 32 |
|---|---|---|---|---|---|
| `f = 0` | 0,0234 | 0,0235 | **0,0240** | 0,0237 | 0,0221 |
| `f = 0,008` | 0,0078 | 0,0080 | **0,0087** | 0,0087 | 0,0082 |

**KHÔNG đơn điệu:** tăng tới `K = 12` (đỉnh), đi ngang `16`, **rơi** ở `32`. Nhưng cả 4 `Δ` so `K = 8` đều
**trong CI** (CI5 rộng **±0,4…1,5e-4** so với điểm **0,007…0,123e-4** ⇒ **độ rộng CI gấp ~10 lần hiệu ứng**)
⇒ **`K*` nếu có thì không đo được ở cỡ mẫu này**; **"hơi gồ ở 12" là GỢI Ý, KHÔNG phải kết quả ngoài CI**
(khai rõ để không hoá post-hoc).

### (3) Nới `K` có **làm lift tụt** không? → **KHÔNG — nới `K` làm lift `ĐỠ ÂM` (tiến về 0); và `lift@8` vốn ĐÃ ÂM**

| `K` | 8 | 10 | 12 | 16 | 32 |
|---|---|---|---|---|---|
| `lift@K` (%/vòng) | **−0,0671** | −0,0530 | −0,0141 | −0,0015 | **0,0000** *(cấu trúc)* |
| CI5 | [−0,476 ; +0,347] | [−0,378 ; +0,266] | [−0,293 ; +0,240] | [−0,180 ; +0,171] | — |

`Δlift(K − 8)` = `+0,014pp · +0,053pp · +0,066pp · +0,067pp` — **TRONG CI, mọi `K`** (và
`Δlift ≡ Δnet_coin` **theo cấu trúc** — mốc pool là hằng số ⇒ **KHÔNG** được đếm 2 lần như 2 bằng chứng).
**Phát hiện phụ (đọc thẳng, không phải suy luận):** **`lift@8 = −0,067 %` ÂM** ⇒ chọn `top-8` theo S1 có
mean gross **thấp hơn** mean cả pool 32 — **cùng chiều** với kết luận cũ "alpha XẾP HẠNG = 0"
(`RESULT_PNL_RULER` `acb88bd`): **không có chất lượng nào để mất** khi nới `K`. ⇒ **Không có trade-off
chất lượng ↔ số lượng ở dữ liệu này.**

### (4) KẾT LUẬN DỨT KHOÁT theo **LUẬT ĐÃ CHỐT TRƯỚC** (PREREG §8) → **GIỮ `K = 8`**

- LUẬT §8: **NÂNG K** ⟺ `Δnet_gross > 0` **ngoài CI k=5** ở **`f = 0,008` VÀ `f = 0`** (và lift không tụt).
  **Điều kiện KHÔNG đạt ở mọi `K ∈ {10,12,16,32}`** (mọi `Δ` trong CI) ⇒ **kết luận tự động: GIỮ `K = 8`**
  (không phải "chọn 8 vì thích 8" — mà vì **không có bằng chứng ngoài CI** cho bất kỳ `K` khác).
- **CẢNH BÁO GROSS EXPOSURE (lý do mạnh nhất để KHÔNG tự ý nới):**

| `K` | 8 | 10 | **12** | 16 | 32 |
|---|---|---|---|---|---|
| `Ē_K` (vị thế đồng thời, TB) | 410,3 | 517,4 | **627,5** | 853,5 | 1.833,6 |
| `e_max` | 1.543 | 1.967 | **2.417** | 3.218 | 6.555 |
| **coin PHÂN BIỆT mở cùng lúc (TB / p95 / max)** | 24,4 / 35 / 42 | 29,2 / 40 / 46 | **33,7 / 46 / 53** | 41,7 / 55 / 67 | 72,1 / 91 / 103 |
| **gross %equity (POST-HOC, neo `2,0 %/lệnh`, trên coin phân biệt)** | 48,8 / 70 / 84 | 58,5 / 80 / 92 | **67,4 / 92 / 106** | 83,3 / 110 / 134 | 144 / 182 / 206 |
| **size phải co để GIỮ NGUYÊN gross như `K = 8`** | **1,00** | 0,79 | **0,65** | 0,48 | 0,22 |

  ⇒ **`K = 12` làm gross exposure +38 % (TB 24,4 → 33,7 coin đồng thời)**: mốc TB **67 %** và **đỉnh 106 %**
  **vượt** mức đang quan sát (**54–58 %**). Muốn giữ gross như hiện hành thì **size mỗi lệnh phải GIẢM còn
  0,65×** — và **giảm size đúng bằng hệ số đó CHÍNH LÀ** điều kiện mà thước (iii) đã đo: **không thu được gì**.
- **Trần tập trung 1 coin `CONC_CAP_PERCOIN_PCT = 0,15` KHÔNG bị nới `K` làm xấu đi** (tỉ trọng 1 coin
  ≈ `1/số coin phân biệt`: **4,1 % → 3,0 %** khi 8 → 12) ⇒ ràng buộc **bind** là **gross**, không phải conc.
  (⚠️ Bản đo này **KHÔNG** mô hình hoá de-dup live / DCA nhiều chân / trần gross — xem §7.)

---

## 1. CÁCH ĐO (nguyên PREREG §3–§6, không thêm bớt)

- **Nhãn (b): dùng lại, KHÔNG build lại** — `y = gross` (KHÔNG dùng cột `net` = `gross − 0,008`, một mức phí).
  Pool **P32 = 9.657 tick × đúng 32 coin = 309.024 dòng**; `rank` = **0..31 đủ mỗi tick**, `rank = 0` = S1 tốt
  nhất (score S1 **thấp = tốt**). `mean(gross)` pool = **+0,012678** = `1,2678 %` (khớp `RESULT_PNL_RULER`).
- **`top-K` = `rank < K`** (cắt từ pool, **không xếp lại, không chấm mô hình nào**).
- **3 chỉ số × 4 mức phí** `f ∈ {0 · 0,004 · 0,008 · 0,012}`: `net_coin` (net/coin/vòng) · `net_tick`
  (net/tick, tổng RO) · **`net_gross = net_tick/Ē_K`** (**net trên 1 đơn vị gross exposure — CHỈ SỐ QUYẾT ĐỊNH**).
- `e_t` = số vị thế đang mở tại tick `t` (`ts_i ≤ t < exit_ts_i`); `Ē_K = mean_t e_t`.
- **CI:** khối **72h**, `NREP = 2000`, `SEED = 20260905`. Chuỗi **trung bình** → `ci_mean` (nguyên hàm).
  **`net_gross` (tỉ số)** → **bootstrap tỉ số ghép cặp** (cùng `BI`, `R = Σn_sum/Σe`), điểm =
  `Σ_t/Σ_t` toàn mẫu (chốt trước). **Luật `inflate(k = 5) = 1,7941`** (5 mức `K` đã thử) + `1,21` legacy.
- **Độ nhạy (chốt trước §5):** bản **mẫu số cố định** `r_t = n_sum_t/Ē_K` — **điểm ước lượng TRÙNG KHÍT**
  (đại số: `mean(n_sum)/Ē ≡ Σn_sum/Σe`), **chỉ CI khác**:
  `K = 8, f = 0`: tỉ số `[+0,000096 ; +0,000375]` (ngoài raw95) vs mẫu-số-cố-định `[−0,000021 ; +0,000482]`
  (**chạm 0**); `f = 0,008`: `[−0,000066 ; +0,000214]` vs `[−0,000177 ; +0,000326]` (**CẢ HAI trong CI**).
  ⇒ **2 bản LỆCH nhau ở `f = 0` (mức, không phải Δ)** — **khai rõ**; **mọi kết luận Δ và mọi kết luận ở
  `f = 0,008` GIỐNG NHAU ở cả 2 bản** ⇒ kết luận không phụ thuộc cách bootstrap.
- **KHÔNG** train · **KHÔNG** Java/sim · **KHÔNG** claude-run · **KHÔNG** push · **DEV only**.

---

## 2. BẢNG CHÍNH — `K` × 4 mức phí (`*` = ngoài CI vs `K = 8`; ở đây **KHÔNG ô nào có `*`**)

**a) `net_coin_K(f)` — net/coin/vòng (%)** (bất biến phí ⇒ Δ giống nhau ở mọi `f`)

| `K` | `f = 0` (gross = **hoà vốn**) | `f = 0,004` | **`f = 0,008` (HIỆN HÀNH)** | `f = 0,012` |
|---|---|---|---|---|
| **8** | **1,2006** | 0,8006 | **+0,4006** | 0,0006 |
| 10 | 1,2148 | 0,8148 | +0,4148 | 0,0148 |
| **12** | **1,2537** | 0,8537 | **+0,4537** | 0,0537 |
| 16 | 1,2663 | 0,8663 | +0,4663 | 0,0663 |
| 32 | 1,2678 | 0,8678 | +0,4678 | 0,0678 |
| *Δ(12−8)* | +0,0531 | +0,0531 | **+0,0531** | +0,0531 |

*CI5 của `Δnet_coin(12−8)` = `[−0,1375 ; +0,2287] pp` (điểm `0,053` **nhỏ hơn nửa CI ~3,4 lần**) ⇒ **TRONG CI**; các `K` khác cũng vậy.*

**b) `net_tick_K(f)` — net/tick (%)** (tổng RO; **ĐỌC KÈM hệ số phối** — nhân lên vì **nhiều lệnh hơn**)

| `K` | `f = 0` | `f = 0,004` | **`f = 0,008`** | `f = 0,012` | `Δ(f=0,008)` vs 8 | CI5 của Δ |
|---|---|---|---|---|---|---|
| **8** | 9,605 | 6,405 | **3,205** | +0,005 | — | — |
| 10 | 12,148 | 8,148 | 4,148 | +0,148 | +0,943 | [−0,66 ; +2,33] |
| **12** | 15,044 | 10,244 | **5,444** | +0,644 | **+2,239** | [−0,96 ; +5,05] |
| 16 | 20,261 | 13,861 | 7,461 | +1,061 | +4,256 | [−2,18 ; +9,94] |
| 32 | 40,569 | 27,769 | 14,969 | +2,169 | +11,764 | [−6,64 ; +28,35] |

**⚠️ ĐỌC ĐÚNG:** `net/tick` **TĂNG là MÁY MÓC** (nhiều lệnh hơn ⇒ nhiều gross hơn), **TRONG CI**, và
vòng **`RESULT_PNL_RULER`** đã chốt: **mức tuyệt đối là edge của RỔ, không phải của xếp hạng**. Con số này
**KHÔNG** được dùng để biện minh nới `K`.

**c) `net_gross_K(f)` — net trên 1 ĐƠN VỊ gross exposure (%/tick/1đv) → CHỈ SỐ QUYẾT ĐỊNH**

| `K` | `f = 0` | `f = 0,004` | **`f = 0,008`** | `f = 0,012` |
|---|---|---|---|---|
| **8** | **+0,0234** \*  | +0,0156 | **+0,0078** | +0,0000 |
| 10 | +0,0235 \* | +0,0157 | +0,0080 | +0,0003 |
| **12** | **+0,0240** \* | +0,0163 | **+0,0087** | +0,0010 |
| 16 | +0,0237 \* | +0,0162 | +0,0087 | +0,0012 |
| 32 | +0,0221 \* | +0,0151 | +0,0082 | +0,0012 |

(`*` ở cột `f = 0` = **MỨC** dương ngoài `raw95` cho **mọi** `K`; **KHÔNG** ô nào **ngoài CI vs `K = 8`**.
⚠️ Ở **`f = 0,008` (phí hiện hành), MỨC của mọi `K` vẫn CHẠM 0**: `K = 8` CI5 `[−0,000066 ; +0,000214]`,
`K = 12` `[−0,000046 ; +0,000214]` ⇒ **"có lãi trên 1 đơn vị gross" CHƯA đạt chuẩn ngoài CI ở BẤT KỲ `K`**.)

---

## 3. `Δ` vs `K = 8` (ghép cặp theo tick chung, **9.657 tick cho mọi** `K`) — bảng đầy đủ

`Δnet_gross` (×10⁻⁴, tỉ số ghép cặp; CI5 = `inflate(5)`; `*` = ngoài CI, `+` = ngoài raw95 — **KHÔNG ô nào**):

| `K − 8` | `f` | `Δ` ×10⁻⁴ | CI5 ×10⁻⁴ | kết luận |
|---|---|---|---|---|
| 10 | 0 / 0,004 / 0,008 / 0,012 | +0,007 / +0,014 / +0,021 / +0,027 | [−0,39,+0,43] … [−0,36,+0,44] | trong CI |
| **12** | 0 / 0,004 / **0,008** / 0,012 | +0,057 / +0,072 / **+0,087** / +0,101 | [−0,61,+0,73] … [−0,54,+0,76] | **trong CI** |
| 16 | 0 / 0,004 / 0,008 / 0,012 | +0,033 / +0,063 / +0,093 / +0,123 | [−0,97,+1,05] … [−0,88,+1,15] | trong CI |
| 32 | 0 / 0,004 / 0,008 / 0,012 | **−0,128** / −0,047 / +0,035 / +0,117 | [−1,47,+1,35] … [−1,23,+1,65] | trong CI (âm ở `f` thấp) |

`Δnet_coin` (`≡ Δlift`, f = 0 và f = 0,008): 10 `+0,0142pp` [−0,0986,+0,1252] · **12 `+0,0530pp`
[−0,1375,+0,2287]** · 16 `+0,0657pp` [−0,2390,+0,3416] · 32 `+0,0671pp` [−0,3467,+0,4762] — **TRONG CI hết**.
`Δnet_tick`: có `+` (**raw95**) ở mọi `K` (10 `+0,94pp`, 12 `+2,24pp`, 16 `+4,26pp`, 32 `+11,76pp`) nhưng
**KHÔNG ngoài CI5** ⇒ đúng như cảnh báo **"đừng đếm gross tăng như bằng chứng"** (`RESULT_PNL_RULER` §6.4).
`Δe_t`: `+107,1 · +217,1 · +443,1 · +1.423,3` vị thế, **ngoài CI mọi `K`** — **đây là CHI PHÍ RỦI RO**, thước
phải trả để lấy `Δnet_tick`, và nó **không** tạo ra `Δnet_gross` ngoài CI.

**Kiểm hợp lệ nội bộ:** chạy lại với **mẫu số cố định** (§1) cho **cùng dấu, cùng kết luận** ở **mọi `Δ`**;
bản **`K = 32`** cho `lift ≡ 0,0000` **đúng như cấu trúc** (kiểm the harness) ⇒ thước không hỏng.

---

## 4. QUÉT `lift@K` (nhãn bổ sung — chất lượng ↔ số lượng)

`lift@8 = −0,0671 %` · `lift@10 = −0,0530 %` · `lift@12 = −0,0141 %` · `lift@16 = −0,0015 %` ·
`lift@32 ≡ 0` (**cấu trúc**). **Đơn điệu TĂNG về 0** khi nới `K` ⇒ **KHÔNG có "tụt lift"**;
nói mạnh hơn: **"xếp hạng S1 chọn 8 coin ĐẦU lại cho gross THẤP hơn chọn ngẫu nhiên trong pool"** — một
cách đọc nữa của **alpha xếp hạng = 0** (`RESULT_PNL_RULER` `acb88bd`). **`K = 32` không được đọc như
"lift = 0 vì mất kỹ năng"** — nó **bằng 0 theo cấu trúc** (rổ = cả pool).

---

## 5. RỦI RO / GROSS EXPOSURE (chốt trước §7) + một phép quy đổi **POST-HOC**

| chỉ số | `K = 8` | 10 | **12** | 16 | 32 |
|---|---|---|---|---|---|
| `Ē_K` (TB vị thế đồng thời) | 410,3 | 517,4 | **627,5** | 853,5 | 1.833,6 |
| `e_max` / `e_p95` | 1.543 / 1.036 | 1.967 / 1.299 | **2.417 / 1.544** | 3.218 / 2.096 | 6.555 / 4.547 |
| coin PHÂN BIỆT TB/max | 24,4 / 42 | 29,2 / 46 | **33,7 / 53** | 41,7 / 67 | 72,1 / 103 |
| độ trùng (vị thế/coin) | 16,0× | 16,7× | **17,7×** | 19,5× | 24,3× |
| **gross %equity — neo A (`2,0 %/lệnh` = 700 USDT/35.000), TRÊN `e`** | 821 / 3.086 | 1.035 / 3.934 | **1.255 / 4.834** | 1.707 / 6.436 | 3.667 / 13.110 |
| **gross %equity — neo B (canh `e_max(8) = 56 %`)** | 14,9 / **56,0** | 18,8 / 71,4 | **23,6 / 87,7** | 32,2 / 116,8 | 68,9 / 237,9 |
| **POST-HOC: gross %equity — neo A TRÊN coin phân biệt** | **48,8 / 84** | 58,5 / 92 | **67,4 / 106** | 83,3 / 134 | 144 / 206 |
| **size giữ nguyên gross như `K = 8`** | **1,00** | 0,79 | **0,65** | 0,48 | 0,22 |

**Ba điều phải nói rõ:**

1. **Neo A trên `e` cho gross 821 %–13.110 %** — **vô lý** so với **54–58 %** đang quan sát ⇒ **số VỊ THẾ
   của sim KHÔNG phải sổ LIVE** (sim **không de-dup 1 coin/1 vị thế**, **không trần gross**, vào lại mỗi tick).
   Vì thế **KHÔNG** được đọc "nới `K` ⇒ gross 4.834 %".
2. **POST-HOC (KHAI RÕ — không có trong PREREG):** nếu thay `e_t` bằng **số COIN PHÂN BIỆT** (gần với sổ
   live có khoá symbol hơn), neo A cho `K = 8`: **TB 48,8 % / p95 70 % / đỉnh 84 %** — **khớp bậc** với mốc
   **54–58 % đang quan sát**. Theo phép quy đổi **này**: `K = 12` ⇒ **TB 67,4 %** (+38 %) và **đỉnh 106 %**.
   ⚠️ **Đây là SUY LUẬN POST-HOC hợp lý hoá một con số dùng tin — KHÔNG phải đo trên sổ LIVE**, và **KHÔNG**
   tham gia vào quyết định §8 (quyết định dùng thước `e`-based đã chốt trước).
3. **Hệ quả vận hành bất kể neo nào:** nới `K` làm **gross +~tuyến tính theo `K`** (`Ē`: 410 → 627 (+53 %)
   ở `K = 12`). Nếu **giữ trần gross hiện hành**, **size phải co còn `0,65×`** — và **hệ số co đó CHÍNH LÀ**
   phép chuẩn hoá mà chỉ số (iii) đã đo: **`net_gross` gần như không đổi** ⇒ **co size để nới số coin là
   ĐỔI RỦI RO LẤY 0**. Về **trần 1-coin 15 %**: **không xấu đi** (tỉ trọng 1 coin `≈ 1/24,4 = 4,1 %` →
   `1/33,7 = 3,0 %`); ràng buộc **bind thật** là **trần gross**, không phải conc.

---

## 6. LUẬT ĐÃ CHỐT TRƯỚC + NHỮNG GÌ BỎ / KHÔNG LÀM

| `K` | (1) `Δnet_gross > 0` ngoài CI ở **cả** `f = 0` và `f = 0,008`? | (3) lift tụt ngoài CI? | LUẬT §8 ⇒ |
|---|---|---|---|
| 10 | **KHÔNG** | không | **GIỮ `K = 8`** |
| 12 | **KHÔNG** | không | **GIỮ `K = 8`** |
| 16 | **KHÔNG** | không | **GIỮ `K = 8`** |
| 32 | **KHÔNG** (âm ở `f = 0`) | không | **GIỮ `K = 8`** |

**Bỏ / không làm (và lý do):**

- **KHÔNG** chạy lại exit engine / **KHÔNG** build lại nhãn (b): **không cần** — pool P32 đã có, **sha khớp**,
  và `rank < 8` **tái lập `label_b_K8.parquet` khớp 100 %** (đường RE đúng như PREREG §2).
- **KHÔNG** dùng Kaggle CPU: **6 giây, 15 GB rảnh** (`free -g`) ⇒ chạy tại chỗ (đúng ràng buộc 6).
- **KHÔNG** bỏ mức phí nào: **báo đủ 4 mức** (đúng "chốt trước 4 mức"). **KHÔNG** bỏ `K` nào trong
  `{8,10,12,16,32}` — `16/32` là **bối cảnh**, giữ vì **miễn phí** (cùng phép cắt).
- **Bỏ duy nhất:** **`K > 32` không tồn tại trong pool** (pool chỉ có top-32 S1) — nếu muốn `K = 64/128` thì
  **phải build lại nhãn (b)** trên top-64/128; **KHÔNG** làm ở vòng này (ngoài ngân sách + không cần để trả
  lời câu hỏi 8/10/12).
- **KHÔNG** chọn `K` theo kết quả: verdict **do LUẬT §8 đã commit `f368ffe`** sinh ra (`GIỮ 8` ở mọi `K`),
  **không** có lựa chọn post-hoc nào được đưa vào kết luận.

---

## 7. GIỚI HẠN (đọc kèm để không overclaim)

1. **Sim ≠ sổ LIVE:** không de-dup theo symbol, không trần gross, không funding, không DCA nhiều chân; vào
   lại mỗi tick. `e_t` là **số VỊ THẾ của sim**; chỉ **tỉ lệ giữa các `K`** là đọc được, **mức tuyệt đối thì không**.
2. **Nhãn (b) không có funding** (`RESULT_AUDIT_PNL`: funding **thu ròng +0,15…0,25 %/lệnh** ⇒ nếu có, net
   **nhích lên**, không xuống). Mốc phí **0,008 = 0,002 + 2×0,003**; **phí thực biết chắc 0,001/vòng** ⇒
   theo `RESULT_AUDIT_PNL`, ở **phí thật** net **rõ ràng dương ngoài CI** — **nhưng điều đó đúng
   (gần) như nhau cho MỌI `K`** ⇒ **không** làm đổi câu trả lời (1)(2)(3)(4).
3. **CI rất rộng** (±40–60 % tương đối cho `net_gross`): kết luận đúng là **"không phân biệt được"**, KHÔNG
   phải "`K = 12` tệ". Nếu cần "gồ ở 12" thành bằng chứng thì phải **tăng số tick / thêm nhãn (b) cho
   top-64** — **không** kết luận từ dữ liệu này.
4. **`Δlift ≡ Δnet_coin`** theo cấu trúc (mốc pool hằng số) ⇒ **một bằng chứng**, không phải hai.

---

## 8. KHUYẾN NGHỊ (1 dòng)

**GIỮ `K = 8`** — nới lên 10/12 **không** cải thiện net trên 1 đơn vị gross exposure **ngoài CI**, **không**
có `K*` đo được, **không** có trade-off lift, nhưng **+38 % gross exposure** ở `K = 12`; muốn nới thì **bắt
buộc** kèm **size `×0,65`** để giữ gross ≈ hiện hành — và khi đó **lợi ích đo được = 0**.
