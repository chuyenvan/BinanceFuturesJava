# RESULT_PNL_RULER — Chấm **TRỰC TIẾP** trên PnL của LUẬT THOÁT: có lift KINH TẾ ngoài CI không?

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_PNL_RULER.md` (commit `a0d46fa`) — chốt **TRƯỚC** khi đọc số.
**Code:** `research/analysis/mr_pnl_score.py` (mới) · dùng **NGUYÊN** `model_ruler.tick_metrics` /
`summarize` / `delta` / `ci_mean` → `stage2_score.block_boot_mean` + `c3_rates` (`BLOCK_H=72`, `NREP=2000`,
`SEED=20260905`, `inflate(k)=sqrt(2 ln k)`) · **KHÔNG** viết lại chỉ số nào, **KHÔNG** train, **KHÔNG** sim.
**Số thô:** `docs/result/mr_pnl_score.json` (249 KB).

---

## 0. TRẢ LỜI NGẮN (3 câu của PREREG §1)

### (1) **KHÔNG** — không mô hình nào có **LIFT KINH TẾ ngoài CI** trên thước PnL luật thoát

| Δ so đối chứng (thước **`P32`**, `y = gross` luật thoát) | `Δglift8` ≡ `Δgross8` | trong/ngoài CI |
|---|---|---|
| `MRA4 − 45deploy` | **+0,00170** | **TRONG CI** (raw95 [−0,00063 ; +0,00392]) |
| `MRA4 − A45` | +0,00135 | TRONG CI |
| `MRA4 − V5` | +0,00178 | TRONG CI |
| `MRB8 − 45deploy` | +0,00194 | TRONG CI |
| `MRB8 − A45` | +0,00159 | TRONG CI |
| `MRB8 − V5` | +0,00204 | TRONG CI |
| `MRB32 − 45deploy` | +0,00291 | TRONG CI |
| `MRB32 − A45` | +0,00256 | TRONG CI |
| `MRB32 − V5` | **+0,00301** | **TRONG CI** ở chuẩn vòng (1,21); raw95 [+0,00033 ; +0,00565] **chỉ vừa** rời 0 |

**Toàn bộ JSON: 0 (không) chỉ số Δ nào ngoài CI ở chuẩn 1,21** — kể cả `k=3` và `k=6`. Best case
(`MRB32 − V5`) **không tái lập** được ở đối chứng còn lại (`− A45` cùng chỉ số trong CI) ⇒ **không có tín hiệu**.

**Đảo chiều so với vòng trước:** trên thước **TIỀN trực tiếp**, các mô hình mới **KHÔNG vượt** đối chứng:
`Δic` = **−0,0096 … −0,0227**, `Δpacc` = **−0,0020 … −0,0075** (mọi cặp, đều trong CI). Vòng trước chúng
*vượt ngoài CI* trên `retEnd_h` ⇒ phần vượt đó là **khớp mục tiêu train**, đúng như vòng trước kết luận.

### (2) **Phí HOÀ VỐN ≈ 1,27 %/vòng cho rổ cả pool, 1,33–1,56 %/vòng cho rổ `top-8`** (≠ 0,8 % hiện hành)

Từ bảng phí §3: `BE = mean(gross)` của rổ. Đây là **MỨC của CHIẾN LƯỢC** (rổ S1 + luật thoát), **KHÔNG**
phải kỹ năng xếp hạng — kèm cảnh báo §6.4. Ở mức phí hiện hành 0,8 %: `netm8 = +0,53 % … +0,76 %/lượt`
(**dương**), **nhưng** CI raw95 vẫn **chạm 0** (cận dưới −0,01 % … −0,14 %).

### (3) Nhánh "mọi mức phí đều âm" **KHÔNG** xảy ra ⇒ kết luận dứt khoát phải phát biểu khác

**Mức thì có lãi (mọi mức phí tới 1,2 %), LIFT thì bằng 0.** Nói dứt khoát: **alpha XẾP HẠNG trên 45
feature = 0 ngoài CI, ở CẢ 2 thước** ((a) `retEnd_h`, (b) PnL luật thoát) ⇒ **KHÔNG đổi model**; muốn có tiền
thì đòn bẩy **duy nhất còn đo được** là **MỨC của rổ** (kiểm chứng luật thoát/chi phí, không phải xếp hạng).

---

## 1. CÁCH ĐO

- **Nhãn (b) — DÙNG LẠI, KHÔNG build lại:** `y = gross` của luật thoát từ
  **`/tmp/mrout/mrout/label_b_pnl.parquet`** (309.024 dòng, `sha256 1d42b7f6…`; bản sao khớp sha ở
  `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_K32.parquet`). Không dùng cột `net` (cột đó = `gross − 0,008`
  = **một** mức phí); mọi mức phí áp **sau** ở §3.
- **2 thước** (pool = tập có nhãn (b), **không** do mô hình đang chấm chọn):
  **`P32`** = pool top-32 S1 (**9.658 tick × đúng 32 coin**) — **CHÍNH**, chọn `top-8` **thật**;
  **`P8`** = pool top-8 (**9.658 × 8**) — **PHỤ**, `top-8` = cả tick ⇒ `glift8 ≡ 0` **theo cấu trúc**.
- **`yb = (y > 0)`** (nhãn nhị phân "coin thắng gross"); `glift8 = mean(y | top-8) − mean(y | tick)`
  (**bất biến với phí**); `gross8 = mean(y | top-8)`; `netm8(f) = gross8 − f`.
- **CI:** khối 72h, `NREP=2000`, `SEED=20260905`; **LUẬT dùng bản CHẶT 1,21** (không nới); phụ `inflate(k)`
  = 1,4823 (`k=3`) và 1,8930 (`k=6`). `*` = ngoài CI 1,21; `+` = ngoài CI `k=3`.
- **Mô hình chấm:** `45deploy` (không retrain) · `MRA4` · `MRB8` · `MRB32` (2 mô hình sau **train trên nhãn
  (b)**) · đối chứng `A45` (retrain) · `V5` (nhiễu) · `V1`. Slot 0 của bins (`p`).
- **Ghép cặp theo tick chung** (`MRB8/MRB32` thiếu fold `20220101` ⇒ `n_common = 8.718` vs `9.658`).
- **CHI PHÍ ĐO:** 1 lượt, **~105 giây** (đọc ~6,5 GB bins **một lần**, 1 fold/lần → không giữ 2 fold),
  `free -g` trước khi chạy = 23 GB tổng / 16 GB rảnh ⇒ **không** cần Kaggle, **không** chạy Java/sim.

## 2. BẢNG CHÍNH — `P32` (mức, `*` = ngoài CI 1,21)

| arm | n_tick | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `auc8c` | `gross8` | `gross_tick` |
|---|---|---|---|---|---|---|---|---|---|
| **45deploy** | 9.658 | +0,02739 | **+0,50930`*`** | **+0,50361`*`** | +0,02871 | +0,00060 | **0,62157`*`** | +0,01327 | +0,01268 |
| A45 | 9.658 | +0,03240 | **+0,51097`*`** | **+0,50380`*`** | +0,03857 | +0,00095 | **0,62356`*`** | +0,01363 | +0,01268 |
| **MRA4** | 9.658 | +0,01776 | **+0,50620`*`** | **+0,50419`*`** | +0,03583 | +0,00229 | **0,59147`*`** | +0,01497 | +0,01268 |
| **MRB8** | 8.718 | +0,01497 | **+0,50522`*`** | **+0,50300`*`** | +0,04137 | +0,00254 | **0,58849`*`** | +0,01466 | +0,01212 |
| **MRB32** | 8.718 | +0,01579 | **+0,50549`*`** | **+0,50229`*`** | +0,04071 | +0,00351 | **0,59093`*`** | +0,01563 | +0,01212 |
| V1 | 9.658 | +0,02679 | **+0,50888`*`** | **+0,50549`*`** | +0,03571 | +0,00070 | **0,62214`*`** | +0,01338 | +0,01268 |
| V5 | 9.658 | +0,02431 | **+0,50816`*`** | **+0,50324`*`** | +0,03020 | +0,00052 | **0,62271`*`** | +0,01319 | +0,01268 |

**Đọc:** (i) **Thước HỢP LỆ** — nó tìm được kỹ năng đã biết: `pacc`/`dec_mono` ngoài CI cho **mọi** arm,
`auc8c` **0,62** (≫ 0,5) cho đối chứng ⇒ thước không "mù". (ii) **Nhưng** `glift8` của **mọi** arm **TRONG
CI** (CI của `glift8` rộng gấp ~4–5 lần chính mức `glift8`); `ic` **không** arm nào ngoài CI 1,21
(raw95 **dương ở 6/7** arm: `MRA4` [+0,00715 ; +0,02860], `MRB8` **chỉ vừa** [+0,00015 ; +0,03020],
`MRB32` **chạm 0** ở cận dưới [−0,00010 ; +0,03285]). (iii) Mô hình mới **kém hơn** đối chứng ở `ic`/`pacc`/`auc8c` (xem §4).

## 3. BẢNG PHÍ — `net = gross8 − f` (%/lượt) + **PHÍ HOÀ VỐN**

`netm8(f)` (chọn `top-8` theo mô hình, `P32`):

| arm | `gross8` | f = 0 (gross) | **f = 0,004** | **f = 0,008 (HIỆN HÀNH)** | **f = 0,012** | **BE_top8** |
|---|---|---|---|---|---|---|
| 45deploy | 1,3273 % | +1,3273 % | +0,9273 % | **+0,5273 %** | +0,1273 % | **1,3273 %** |
| A45 | 1,3625 % | +1,3625 % | +0,9625 % | **+0,5625 %** | +0,1625 % | 1,3625 % |
| **MRA4** | 1,4971 % | +1,4971 % | +1,0971 % | **+0,6971 %** | +0,2971 % | **1,4971 %** |
| **MRB8** | 1,4660 % | +1,4660 % | +1,0660 % | **+0,6660 %** | +0,2660 % | 1,4660 % |
| **MRB32** | 1,5629 % | +1,5629 % | +1,1629 % | **+0,7629 %** | +0,3629 % | **1,5629 %** |
| *rổ cả pool (mọi arm 9.658 tick)* | 1,2677 % | +1,2677 % | +0,8677 % | **+0,4677 %** | +0,0677 % | **1,2677 %** |

`P8` (phụ): `gross8 = gross_tick = 1,2005 %` (rổ 8 coin của S1; nhánh `MRB*` trên 8.718 tick = 1,1129 %)
⇒ net 0,8005 / 0,4005 / **0,0005** / −0,0871 ⇒ **BE = 1,20 %**.

**CI của MỨC (raw95) — quan trọng, đọc kèm:** `gross8` **dương ngoài raw95** cho mọi arm
(vd `MRB32` [+0,00778 ; +0,02293]) **nhưng `netm8(0,008)` chỉ vừa dương và CI vẫn chạm 0**:
45deploy [−0,00140 ; +0,01192] · MRA4 [−0,00011 ; +0,01376] · MRB8 [−0,00114 ; +0,01366] ·
MRB32 [−0,00022 ; +0,01493] ⇒ **"có lãi ở 0,8 %" CHƯA đạt chuẩn ngoài CI**.

**Khai báo cấu trúc (chốt trước, giữ nguyên):** `Δglift8 ≡ Δgross8` với **mọi** `f` (phí là hằng số mỗi
lượt) ⇒ **bảng phí KHÔNG thể "cứu" một lift bằng 0**; nó chỉ trả lời **mức** và **hoà vốn**.

## 4. Δ vs ĐỐI CHỨNG (ghép cặp tick chung) + KIỂM HỢP LỆ

Δ `MRA4/MRB8/MRB32` vs **cả 4** đối chứng trên `P32` (`glift8` ≡ `gross8`):

| cặp | n_common | `Δglift8` | raw95 | CI? | `Δic` | `Δpacc` | `Δdec_mono` |
|---|---|---|---|---|---|---|---|
| MRA4 − 45deploy | 9.658 | +0,00170 | [−0,00063 ; +0,00392] | **TRONG** | −0,00964 | −0,00310 | +0,00059 |
| MRA4 − A45 | 9.658 | +0,00135 | [−0,00105 ; +0,00356] | **TRONG** | −0,01464 | −0,00477 | +0,00039 |
| MRA4 − V5 | 9.658 | +0,00178 | [−0,00042 ; +0,00397] | **TRONG** | −0,00655 | −0,00196 | +0,00096 |
| MRB8 − 45deploy | 8.718 | +0,00194 | [−0,00163 ; +0,00529] | **TRONG** | −0,01672 | −0,00550 | −0,00129 |
| MRB8 − A45 | 8.718 | +0,00159 | [−0,00187 ; +0,00481] | **TRONG** | −0,02270 | −0,00752 | −0,00145 |
| MRB8 − V5 | 8.718 | +0,00204 | [−0,00123 ; +0,00500] | **TRONG** | −0,01278 | −0,00416 | −0,00149 |
| MRB32 − 45deploy | 8.718 | +0,00291 | [−0,00015 ; +0,00601] | **TRONG** | −0,01590 | −0,00524 | −0,00200 |
| MRB32 − A45 | 8.718 | +0,00256 | [−0,00047 ; +0,00557] | **TRONG** | −0,02187 | −0,00726 | −0,00217 |
| MRB32 − V5 | 8.718 | **+0,00301** | [+0,00033 ; +0,00565] | **TRONG** (raw vừa rời 0) | −0,01196 | −0,00390 | −0,00220 |

`Δnetm8` với **mọi** `f` **≡** `Δglift8` ⇒ không in lại. **Tổng số chỉ số Δ ngoài CI 1,21 trong toàn JSON
(kể cả vs `V1`, cả `P8`): 0.**

**Kiểm hợp lệ (bắt buộc §6 pre-reg) — ĐẠT:**

| Δ | n | `ic` | `pacc` | `dec_mono` | `glift8` |
|---|---|---|---|---|---|
| **A45 − 45deploy** (`P32`) | 9.658 | +0,00501 | +0,00167 | +0,00020 | +0,00035 |
| **V5 − V1** (`P32`) | 9.658 | −0,00248 | −0,00072 | −0,00226 | −0,00018 |
| A45 − 45deploy / V5 − V1 (`P8`) | 9.658 | +0,00039 / −0,00755 | −0,00001 / −0,00290 | −0,00193 / +0,00036 | 0 / 0 |

⇒ 3 chỉ số LUẬT ~0 và **TRONG CI** ở cả 2 bước × 2 thước ⇒ **thước/ghép cặp hợp lệ đúng chỗ dùng để quyết định**.

## 5. BẢNG PHỤ `P8` (khai báo trước: `glift8 ≡ 0` do cấu trúc)

| arm | n_tick | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `auc8c` |
|---|---|---|---|---|---|---|---|
| 45deploy | 9.658 | +0,02860 | +0,51074`*` | +0,50589`*` | +0,02861 | 0 (cấu trúc) | 0,56027`*` |
| A45 | 9.658 | +0,02899 | +0,51073`*` | +0,50396`*` | +0,02899 | 0 | 0,56269`*` |
| **MRA4** | 9.658 | +0,01242 | +0,50467`*` | +0,50156`*` | +0,01245 | 0 | 0,50716`*` |
| **MRB8** | 8.718 | +0,02305 | +0,50826`*` | +0,50069`*` | +0,02304 | 0 | 0,51363`*` |
| **MRB32** | 8.718 | +0,03070 | +0,51154`*` | +0,50301`*` | +0,03070 | 0 | 0,52110`*` |
| V1 / V5 | 9.658 | +0,02417 / +0,01662 | +0,50908`*` / +0,50618`*` | +0,50218`*` / +0,50253`*` | … | 0 | … |

## 6. KHAI BÁO TRUNG THỰC — **KHÔNG** ĐƯỢC NÓI GÌ

1. **KHÔNG** được nói "có alpha/lift kinh tế": **0** chỉ số Δ ngoài CI; best case `MRB32 − V5` **không tái lập**
   ở `− A45` (và vs `45deploy`), ở **cả** 1,21 / `k=3` / `k=6`.
2. **KHÔNG** được nói `netm8 = +0,53…+0,76 %` là "ranker kiếm được tiền": đó là **MỨC của RỔ** (rổ S1 + luật
   thoát), và CI raw95 của mức vẫn **chạm 0**; phần gia tăng so đối chứng **trong CI**.
3. **KHÔNG** được nói mô hình mới "tốt hơn" trên thước tiền: `Δic`/`Δpacc` **âm** ở mọi cặp (trong CI).
4. **KHÔNG** được gọi `P8` là "không có kỹ năng" khi `glift8 = 0`: đó là **suy biến cấu trúc** (`top-8` = cả
   tick) — đã khai ở pre-reg §3.
5. `y` là **gross** luật thoát **WEAK `cap=0,03`**, 1 leg, **không funding**, **không** DCA/gate/sizing,
   bỏ **6,9 %** cặp nhãn (chia khối 90 ngày) ⇒ **KHÔNG** phải PnL/equity của LIVE.
6. Vòng trước (thước `retEnd_h`) kết luận "kinh tế = 0"; vòng này **xác nhận trực tiếp** trên chính giá trị
   tiền — nhưng **đảo chiều** phần thống kê (`Δic`/`Δpacc` âm trên thước tiền) ⇒ phần "vượt" của vòng trước
   là **khớp mục tiêu train**.
7. `P8`/`P32` **không** độc lập (`K=8 ⊂ K=32`, 1 lần sim) ⇒ chỉ là **2 thước của cùng 1 nhãn**.

## 7. LUẬT §8 pre-reg — KẾT QUẢ TỪNG BIẾN THỂ

| biến thể (`P32`) | `Δglift8` > 0 ngoài CI vs **A45** | vs **V5** | `glift8` mức ngoài CI | `netm8(0,008)` > 0 ngoài CI | **LIFT KINH TẾ** |
|---|---|---|---|---|---|
| `MRA4` | ✗ (trong CI) | ✗ | ✗ | ✗ | **KHÔNG** |
| `MRB8` | ✗ | ✗ | ✗ | ✗ | **KHÔNG** |
| `MRB32` | ✗ | ✗ (raw vừa rời 0) | ✗ | ✗ | **KHÔNG** |

Kết quả **giống nhau ở cả 3 độ rộng CI** (1,21 · `k=3` · `k=6`) ⇒ **không** phụ thuộc độ rộng.

## 8. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Score trực tiếp `y = gross` trên `P32`/`P8` (3 arm + 4 đối chứng) | ✅ XONG (105 s) | đúng câu hỏi vòng này |
| 2 | Bảng phí 4 mức + phí hoà vốn | ✅ XONG | phí quyết định; `Δglift8 ≡ Δgross8` nên bảng phí chỉ có nghĩa cho **mức** |
| 3 | Kiểm hợp lệ `A45−45deploy`, `V5−V1` | ✅ XONG, ĐẠT | bắt buộc §6 pre-reg |
| 4 | Thước `y = net` tại từng mức phí (thước thứ hai) | ⛔ BỎ | ≡ thước gross + **dịch hằng số** ⇒ 2 bảng mà 1 bằng chứng (pre-reg §9) |
| 5 | `MRA72`, horizon khác, funding, `rank:pairwise` | ⛔ BỎ | ngoài phạm vi đã chốt; mọi hướng đều cho cùng hình (lift = 0) |
| 6 | Thêm arm **S1** làm ranker-trong-pool | ⛔ BỎ (đề xuất vòng sau) | **không** có trong pre-reg ⇒ thêm bây giờ = post-hoc; xem §9-(3) |

## 9. KẾT LUẬN + BƯỚC TIẾP

1. **Dứt khoát:** trên **chính PnL của luật thoát**, **không** mô hình nào có lift kinh tế **ngoài CI** — kể cả
   `MRB8`/`MRB32` (train trên đúng nhãn đó). Ở tầng thống kê, trên thước tiền chúng còn **kém** `45deploy`.
2. **Phí hoà vốn 1,27 %/vòng (rổ pool) → 1,56 %/vòng (rổ `top-8` MRB32)**; phí hiện hành 0,8 % ⇒ **rổ có
   mức lãi dương ở mọi mức phí tới 1,2 %**, nhưng **CI của mức vẫn chạm 0** (chưa đạt chuẩn) và **không** đến
   từ xếp hạng.
3. **Đề xuất bước tiếp (theo thứ tự):**
   (i) **Đóng trục ranker 45-feature** (3 hướng nhãn: `retEnd_h`, 2 cách nhãn tiền, PnL trực tiếp — tất cả
   lift = 0). **Không** đổi model, **không** tinh chỉnh loss/hyperparam.
   (ii) Nếu muốn tìm tiền: đòn bẩy duy nhất còn **mức** ⇒ (a) kiểm chứng độc lập **giả định của nhãn (b)**
   (WEAK `cap=0,03`, funding, 6,9 % cặp bị bỏ, giả định khớp `min(priceSL, open)`) bằng audit chi phí thật;
   (b) thêm arm **S1** làm ranker-trong-pool (rẻ, đo được: S1 có *xếp hạng* trong pool tốt hơn cân bằng không).
   (iii) **Đổi cấu trúc**: chọn rổ bằng chính luật thoát/horizon khác thay vì xếp hạng 45 feature.
4. **KHÔNG** chạm ONNX/LIVE/2026/`HoldoutSeal` · **KHÔNG** push.

---

**Tệp vòng này:** `docs/prereg/PREREG_PNL_RULER.md` (`a0d46fa`) · `research/analysis/mr_pnl_score.py` ·
`docs/result/mr_pnl_score.json` · `docs/result/RESULT_PNL_RULER.md` (commit cuối vòng).
**Tái lập:** `python3 research/analysis/mr_pnl_score.py --out docs/result/mr_pnl_score.json`
(cache 1 fold ở `/tmp/mrpnp/cache`).

## ERRATA (2026-09-25) — §0(1): câu **"0 chỉ số Δ ngoài CI"** là **SAI cách viết**, KẾT LUẬN KHÔNG ĐỔI

Audit độc lập (`docs/result/RESULT_AUDIT_PNL.md`, commit `43968cc`) mở lại **JSON của chính vòng này** và đếm được **38 mục `out_both`** — **TẤT CẢ ÂM** (`auc8` · `auc8c` · `lift8` · `ic` · `pacc` …), **không mục nào là chỉ số KINH TẾ**.

⇒ Câu đúng: **"0 chỉ số Δ *kinh tế dương* ngoài CI"** — KHÔNG phải "0 chỉ số Δ ngoài CI".
⇒ Kết luận giữ nguyên, thực ra **MẠNH HƠN**: model mới **KÉM** ở 38 mục ngoài CI; chúng chỉ **không kém** ở các chỉ số kinh tế (và cũng không hơn).
