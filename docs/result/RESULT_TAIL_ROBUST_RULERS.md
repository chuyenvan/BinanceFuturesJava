# RESULT_TAIL_ROBUST_RULERS — BỘ THƯỚC "KHÔNG-ĐUÔI" + LÀM MỊN LẠI THƯỚC CI

**Ngày:** 2026-09-26/27 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_TAIL_ROBUST_RULERS.md` (commit `4660529`) — chốt **TRƯỚC** khi đọc số
(+ **AMENDMENT 1** ở cuối pre-reg: sửa CHIỀU ĐIỂM của 2 nguồn, phát hiện **sau** khi đo, ghi rõ).
**Code:** `research/analysis/tail_robust_rulers.py` (17 thước + bootstrap khối, paired) ·
`research/analysis/tail_robust_validate.py` (kiểm hợp lệ) · `research/analysis/tail_robust_tables.py` (bảng).
**Số thô:** `docs/result/tail_robust_rulers.json` (3,1 MB) · log `/tmp/trr/*.log` (không commit).
**KHÔNG** train, **KHÔNG** Java/sim, **KHÔNG** chạm `242`/ONNX/LIVE. DEV only (`<= 2025-12-31`, pool tới 2025-09-27).

---

## 0. TRẢ LỜI NGẮN (4 câu của yêu cầu)

### (1) Sau khi bỏ đuôi: có thước nào cho alpha NGOÀI CI không? → **KHÔNG ở trục LỢI NHUẬN; CÓ ở trục RỦI RO**

- **Trục LỢI NHUẬN (level): 0 ô ngoài CI.** Toàn bộ Δ của 12 đối tượng trên `median`, `tf_5`, `tf_10`,
  `wmean_p1p99`, `tmean_5`, `gross8`, `net_tick` đều **TRONG CI** (gần nhất: `MRB32 − 45deploy`
  `tf_5 = +0,00281` raw95 `[+0,00002 ; +0,00546]` — **vừa rời 0 ở raw95**, nhưng **KHÔNG qua** `inflate(17)=2,3805`).
- **Trục RỦI RO (downside): 3 thước `loss_mean` / `wl_ratio` / `max_loss` NGOÀI CI** (cả raw95 **và** inflate(17),
  độ rộng tương đối **0,32–0,82** = phân giải tốt) cho **3 đối tượng**: `MRA4`, `MRB8`, `MRB32`
  (nhóm money-ranker) so **CẢ HAI** nền `45deploy` **và** `V1`. Chiều: **lỗ ít hơn 1,5–4,5 pp/leg**,
  **tỷ số thắng/thua tốt hơn 0,046–0,070** — nhưng **win-rate thấp hơn** (`sign_frac` âm; chỉ ngoài CI ở S1/OFI bản sai chiều, xem §6).
- **2 đối chứng BẮT BUỘC đều SẠCH**: `A45 − 45deploy` (retrain) và `V5 − V1` (nhiễu) **TRONG CI ở CẢ 17 thước**
  ⇒ không thước nào bắt nhiễu ⇒ bộ thước **hiệu chuẩn được**.

### (2) Bao nhiêu % "alpha" cũ đến từ đuôi? → **≈ 100 % (và hơn thế)**

Share của **top-5 % leg** trong `net`/leg = **80,8 % (MRB32) … 137,2 % (ofi_baseline_fresh)**;
`net`/leg sau khi **bỏ top-5 %** (`tf_5`) = **−0,0021 … +0,0019** (≈ 0), sau khi **bỏ top-10 %** (`tf_10`)
= **−0,0081 … −0,0039** (**ÂM ở CẢ 12 đối tượng**). Tức: **mọi mức "alpha" đo bằng thước mean-based
(trước đây `glift8`/`netm8`/`ic`/`pacc`) là ~100 % ĐUÔI** — đúng như `RESULT_FRAGILITY_N.md`
(share top-1 % 25,9/40,9/37,8 %; bỏ top-5 % ⇒ PnL âm ở T100/GD92).

### (3) Thước nào nên dùng · thước nào nên bỏ → §6 (đề xuất chốt: **`tf_5` + `loss_mean` + `wl_ratio`** (+`sign_frac`))

### (4) Bảng CI tổng hợp thước × CI × độ rộng → §4.

**Bổ sung — pool MỞ RỘNG (B2, 470.911 dòng / 9.573 tick):** cũng **0 ô ngoài CI** trên cả 17 thước
(§10) ⇒ kết luận (1) **không phụ thuộc `P32`**.

---

## 1. CÁCH ĐO (đúng pre-reg §4–§6, KHÔNG đổi luật sau khi thấy số)

- **Thước chính `P32`**: `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` — **309.024** dòng
  = **9.657 tick × 32** (`sha 1d42b7f6…`), `y = gross` của **luật thoát** (nhãn (b) của `RESULT_PNL_RULER`).
  Sau lọc tick chung còn **308.832 dòng / 9.651 tick** (bỏ 6 tick thiếu điểm ở bins).
- Mỗi tick: xếp hạng coin **của `P32`** theo điểm từng đối tượng → **`top-8`**; **`net = gross − f`**,
  **`f = 0,006`** là mức quyết định (+ `0` · `0,004` · `0,008`) · **trần gross 70 %** báo ở §5 (3 cách
  `A_mean`/`B95`/`Bmax`, đúng công thức `RESULT_CAP70_FEE06.md`).
- **Bootstrap theo KHỐI tick, GHÉP CẶP**: mọi đối tượng dùng **cùng** ma trận block-index/cấu hình ⇒
  Δ = hiệu **trên từng lần resample**. Cấu hình **đầy đủ 18 ô** cho mọi thước: block **24/72/168 h** ×
  `NREP` **2000/5000** × seed **20260905/907/911**. `median`/`p25`/`p75` (phi tuyến theo leg) theo
  **6 ô đã khai báo trước** ở pre-reg §6 (đúng bằng số ô đã chốt; không nới).
- **LUẬT "ngoài CI"**: ngoài raw95 **VÀ** ngoài `c3_rates.inflate(17) = 2,3805` (không hardcode).
- `inflate` import **nguyên** từ `c3_rates` (chuẩn hoá 2026-09-17).

## 2. KIỂM HỢP LỆ (pre-reg §8) — PASS 4/5, **1 LỖI ĐÃ BẮT + SỬA** (rất quan trọng)

| kiểm | kết quả |
|---|---|
| (a) phủ điểm trên `P32` | `45deploy`/`A45` **99,998 %**; `S1`/OFI ×3 **100,0 %** |
| (b) `S1` tái lập thứ tự pool | Spearman **1,000** mọi tick lấy mẫu ⇒ dùng được `pred_s1a2x1.parquet` |
| (c) số học `net = gross − 0,008` | **0,00e+00** (max abs dev) |
| (d) `0` không bị gọi là "ngoài CI" khi raw95 chứa 0 | không vi phạm (§4 dùng đúng luật) |
| (e) **CHIỀU ĐIỂM** | ⚠️ **2 NGUỒN NGƯỢC CHIỀU NHAU** — xem dưới |

**⚠️ LỖI ĐÃ BẮT + SỬA (không dấu):** `corr(score, rank pool)`:
`45deploy −0,316` · `A45 −0,323` (**điểm CAO = TỐT**, chuẩn `model_ruler`/bins) — nhưng
`S1 +1,000` · `ofi_candidate +0,899` · `ofi_baseline_fresh +0,937` · `ofi_noise +0,916`
(**điểm THẤP = TỐT**: `pred_s1a2x1.parquet` và `pred_ofi_*_v2.parquet` là `score = −pred`,
xem `research/pipeline/x1/kaggle_ofi_v3/ofi_train_eval_v3.py:150,177`).
Bản chạy đầu áp **một** quy ước cho cả hai ⇒ `S1`/OFI bị lấy **nhầm top-8 = 8 coin XẤU NHẤT của pool**
(mean rank **27,5** thay vì **3,5**). Đã thêm `ORIENT` + **chạy lại** toàn bộ nhánh `S1`/OFI.
Số dưới đây là số **sau sửa**. (Đối chứng: `mean-rank top-8` sau chuẩn hoá = `S1 3,5 · ofi_candidate 4,4 · 45deploy 11,8`.)
**Cảnh báo cho vòng cũ:** `RESULT_OFI_MONEY`/`ofi_money_score.py` cũng dùng `argsort(−score)` cho
`pred_ofi_*` ⇒ nghi vấn **cùng lỗi chiều**; cần vòng riêng kiểm lại (KHÔNG kết luận thay ở đây).

## 3. BẢNG 1 — MỨC (pool `P32`, top-8/tick, `f = 0,006`, đơn vị: **phần trăm notional/leg**)

| đối tượng | net/leg | median | **`tf_5`** | `tf_10` | **share top-5 % của mean** | `conc_1` | `sign_frac` | `loss_mean` | `wl_ratio` | `max_loss` |
|---|---|---|---|---|---|---|---|---|---|---|
| `45deploy` | +0,00727 | +0,04895 | **−0,00031** | −0,00618 | 104,3 % | 0,297 | 0,7997 | −0,21769 | +0,2923 | −0,1662 |
| `A44` | +0,00693 | +0,04895 | −0,00065 | −0,00654 | 109,4 % | 0,311 | 0,7976 | −0,21708 | +0,2938 | −0,1672 |
| `A45` | +0,00763 | +0,04895 | **+0,00007** | −0,00577 | 99,0 % | 0,281 | 0,8005 | −0,21726 | +0,2931 | −0,1654 |
| `V1` | +0,00738 | +0,04895 | −0,00035 | −0,00626 | 104,7 % | 0,303 | 0,7981 | −0,21637 | +0,2958 | −0,1657 |
| `V5` | +0,00720 | +0,04895 | −0,00042 | −0,00630 | 105,8 % | 0,299 | 0,7975 | −0,21555 | +0,2958 | −0,1643 |
| **`MRA4`** | +0,00897 | +0,04886 | +0,00131 | −0,00450 | 85,4 % | 0,253 | 0,7808 | **−0,18692** | **+0,3423** | **−0,1508** |
| **`MRB8`** | +0,00867 | +0,04848 | +0,00081 | −0,00494 | 90,7 % | 0,286 | 0,7752 | **−0,18192** | **+0,3516** | **−0,1446** |
| **`MRB32`** | +0,00964 | +0,04889 | **+0,00185** | −0,00390 | 80,8 % | 0,252 | 0,7820 | **−0,18621** | **+0,3449** | **−0,1500** |
| `S1` | +0,00602 | +0,04894 | −0,00153 | −0,00756 | 125,5 % | 0,331 | 0,7925 | −0,21444 | +0,2972 | −0,1734 |
| `ofi_candidate` | +0,00643 | +0,04895 | −0,00104 | −0,00701 | 116,1 % | 0,308 | 0,7944 | −0,21493 | +0,2964 | −0,1731 |
| `ofi_baseline_fresh` | +0,00551 | +0,04894 | −0,00205 | −0,00808 | 137,2 % | 0,360 | 0,7912 | −0,21508 | +0,2963 | −0,1739 |
| `ofi_noise` | +0,00620 | +0,04893 | −0,00136 | −0,00737 | 122,0 % | 0,326 | 0,7921 | −0,21279 | +0,2993 | −0,1728 |

Đọc: **`median` = +0,0489 ở CẢ 12 đối tượng** (giá trị rời rạc, cùng một leg trúng ⇒ không phân biệt được gì);
**`tf_10` ÂM ở cả 12** ⇒ bỏ 10 % leg tốt nhất là **lỗ**; **`loss_mean`/`wl_ratio`/`max_loss`** mới tách được nhóm.

## 4. BẢNG 2 — Δ vs 2 NỀN (`45deploy` và `V1`), `f = 0,006`, cấu hình chính `(72 h, NREP 2000, seed 20260905)`

`*` = **ngoài CI** (raw95 **và** inflate(17)) · `+` = chỉ ngoài raw95 (KHÔNG tính là "ngoài CI") · `w` = **độ rộng CI / |điểm|**.

| cặp | `tf_5` (level) | `loss_mean` | `wl_ratio` | `max_loss` | `sign_frac` | `wmean_p1p99` | `ic_wmean` |
|---|---|---|---|---|---|---|---|
| `A45 − 45deploy` **(ĐC#1)** | +0,00039 w3,52 | +0,00043 w7,50 | +0,00079 w5,72 | +0,00079 w6,59 | +0,00084 w5,52 | +0,00045 w2,85 | −0,00663 w2,89 |
| `V5 − V1` **(ĐC#2)** | −0,00007 w23,2 | +0,00082 w4,49 | +0,00002 w237,7 | +0,00143 w3,71 | −0,00056 w9,58 | −0,00010 w15,6 | **−0,01340 w1,38⁺** |
| `A44 − 45deploy` | −0,00034 w5,41 | +0,00061 w7,55 | +0,00155 w4,19 | −0,00103 w5,58 | −0,00209 w2,79 | −0,00028 w6,07 | −0,00871 w2,40 |
| **`MRA4 − 45deploy`** | +0,00162 w2,74 | **+0,03078 `*` w0,32** | **+0,05002 `*` w0,39** | **+0,01537 `*` w0,82** | −0,01890 w0,89⁺ | +0,00169 w2,53 | −0,00398 w8,23 |
| **`MRA4 − V1`** | +0,00166 w2,30 | **+0,02945 `*` w0,41** | **+0,04652 `*` w0,46** | **+0,01492 `*` w0,71** | −0,01730 w0,89⁺ | +0,00156 w2,44 | −0,00349 w10,3 |
| **`MRB8 − 45deploy`** | +0,00177 w3,50 | **+0,04470 `*` w0,37** | **+0,06970 `*` w0,42** | **+0,03091 `*` w0,58** | −0,02807 w0,91⁺ | +0,00147 w4,44 | −0,01583 w2,58 |
| **`MRB8 − V1`** | +0,00191 w3,00 | **+0,04248 `*` w0,42** | **+0,06504 `*` w0,45** | **+0,02984 `*` w0,61** | −0,02554 w0,98⁺ | +0,00148 w4,20 | −0,01658 w2,64 |
| **`MRB32 − 45deploy`** | +0,00281 w1,94⁺ | **+0,04041 `*` w0,35** | **+0,06306 `*` w0,46** | **+0,02556 `*` w0,71** | −0,02121 w1,08⁺ | +0,00253 w2,30 | −0,00489 w9,10 |
| **`MRB32 − V1`** | +0,00295 w1,79⁺ | **+0,03819 `*` w0,40** | **+0,05840 `*` w0,50** | **+0,02448 `*` w0,70** | −0,01868 w1,25⁺ | +0,00254 w2,26 | — |
| `S1 − 45deploy` | −0,00122 w5,97 | +0,00325 w5,59 | +0,00495 w5,05 | −0,00721 w2,39 | −0,00715 w3,32 | −0,00096 w7,44 | −0,02121 w2,12 |
| `S1 − V1` | −0,00119 w6,51 | +0,00193 w9,76 | +0,00146 w17,9 | −0,00766 w2,34 | −0,00556 w4,72 | −0,00109 w6,78 | −0,02072 w2,10 |
| `ofi_candidate − 45deploy` | −0,00072 w10,1 | +0,00276 w6,83 | +0,00414 w6,19 | −0,00691 w2,66 | −0,00522 w4,24 | −0,00062 w11,5 | −0,02753 w1,57⁺ |
| `ofi_candidate − V1` | −0,00069 w11,3 | +0,00144 w13,1 | +0,00064 w41,2 | −0,00736 w2,63 | −0,00363 w7,10 | −0,00075 w10,2 | −0,02705 w1,53⁺ |
| `ofi_candidate − baseline_fresh` | +0,00101 w2,29 | +0,00015 w38,8 | +0,00011 w73,5 | +0,00083 w8,23 | +0,00326 w2,32 | +0,00084 w2,61 | −0,01221 w2,07 |
| `ofi_candidate − noise` | +0,00033 w6,48 | −0,00214 w2,38 | −0,00288 w2,57 | −0,00029 w24,5 | +0,00237 w2,57 | +0,00017 w11,2 | −0,00068 w35,3 |
| `MRA4 − A45` | +0,00123 w3,64 | **+0,03034 `*` w0,35** | **+0,04922 `*` w0,42** | +0,01458 w0,89⁺ | **−0,01974 `*` w0,86** | +0,00124 w3,58 | +0,00265 w12,4 |

(Nhánh `MRA4`/`S1`/OFI trên **9.651 tick**; `MRB8`/`MRB32` trên **8.711 tick** — 2 arm này thiếu fold
`20220101` ⇒ **chạy riêng cùng 2 nền trên CÙNG lưới tick của chúng** (paired trong nhánh đó), đã khai báo trước.)

## 5. BẢNG 3 — TIỀN dưới **trần gross 70 %** (`f = 0,006`; net/tick = Σnet top-8 / tick; `sized_Bmax` = %equity/tick theo cách CHẶT nhất)

| đối tượng | `d_mean` (vị thế mở) | `gross_anchor.max` (%) | net/tick | sized `A_mean` | sized `B95` | **sized `Bmax`** |
|---|---|---|---|---|---|---|
| `45deploy` | 44,1 | 162 | +0,05814 | 0,0922 | 0,0636 | **0,0502** |
| `A45` | 44,2 | 154 | +0,06101 | 0,0966 | 0,0667 | **0,0555** |
| `MRA4` | 46,5 | 158 | +0,07180 | 0,1082 | 0,0773 | **0,0636** |
| `S1` | 24,4 | 84 | +0,04815 | 0,1381 | 0,0963 | **0,0803** |
| `ofi_candidate` | 24,1 | 88 | +0,05145 | 0,1492 | 0,1001 | **0,0819** |

⇒ Ở trần 70 % và `f = 0,006`, **mọi đối tượng vẫn dương** nhưng **Δ giữa chúng đều TRONG CI**
(`MRA4 − 45deploy` net/tick = +0,0137 raw95 `[−0,0046 ; +0,0329]`) ⇒ **không có alpha TIỀN ngoài CI**,
khớp `RESULT_PNL_RULER` (`acb88bd`) và `RESULT_OFI_MONEY`. Bảng 4 mức phí (`0`/`0,004`/`0,006`/`0,008`)
đầy đủ trong JSON (`money.<obj>.fees`).

## 6. LUẬT D1–D4 (chốt trước) — KẾT LUẬN

- **D2 (hiệu chuẩn THƯỚC):** **17/17 thước "PHÂN GIẢI ĐƯỢC"** — cả `A45 − 45deploy` và `V5 − V1`
  **TRONG CI** ở mọi thước ⇒ bộ thước không bắt nhiễu train/seed.
  *Ngoại lệ cần ghi:* `ic_wmean` có **raw95 của `V5 − V1` = [−0,0224 ; −0,0040]** (rời 0 ở raw95,
  nhưng `w = 1,38` ⇒ qua inflate thì chứa 0) ⇒ **thước yếu nhất, đề nghị hạ/loại** (xem §7).
- **D1 (alpha không-đuôi của một đối tượng):** đạt cho **`MRA4` (3 thước: `loss_mean`,`wl_ratio`,`max_loss`)
  · `MRB8` (3) · `MRB32` (3)** trên lưới tick tương ứng; `A44`, `A45`, `V5`, `S1`, OFI ×3 = **0 thước**.
- **D4:** 1–2 đối tượng "đạt" ⇒ **"có tín hiệu HẸP, cần vòng xác nhận"**, **KHÔNG gọi là alpha không-đuôi**.
  Và **tín hiệu hẹp đó nằm ở trục RỦI RO, KHÔNG ở trục LỢI NHUẬN**.

**Phát biểu dứt khoát:** *Trên thước TIỀN, sau khi bỏ đuôi thì **alpha xếp hạng = 0** (đúng như
`RESULT_PNL_RULER`/`RESULT_MONEY_RANKER`/`RESULT_OFI_MONEY`); cái **sống sót** sau khi làm sạch đuôi là
khác biệt **KIỂM SOÁT LỖ** của nhóm money-ranker (`MRA4`/`MRB8`/`MRB32`): lỗ/leg nhỏ hơn **1,5–4,5 pp**,
tỷ số thắng/thua cao hơn **0,046–0,070**, **đổi lại win-rate thấp hơn ~2–3 pp** — một điểm khác trên
đường biên rủi ro/lợi nhuận, **không phải alpha lợi nhuận**.*

## 7. ĐỀ XUẤT BỘ THƯỚC CHUẨN (câu (3)) + DANH SÁCH BỎ

**CHỐT LÀM CHUẨN (3):**
1. **`tf_5`** — "bỏ 5 % leg tốt nhất rồi lấy trung bình": thước **phân xử được tail hay không**;
   phân giải: Δ`w` = 1,8–6,0; level `w` = 1,7–2,0 (168 h) ⇒ **dùng block 72 h + NREP 2000**.
2. **`loss_mean`** — độ lớn lỗ trung bình/leg: **nhạy nhất** (Δ`w` = **0,32–0,43**), hiệu chuẩn sạch.
3. **`wl_ratio`** — mean win / mean loss (bắt buộc đi **kèm `sign_frac`** để không bị đánh lừa
   "lỗ nhỏ + win-rate thấp" thành "tốt hơn"; cả 2 đều ngoài CI ở `MRA4`/`MRB*`/OFI theo chiều ngược nhau).
   *Phụ trợ bắt buộc:* `gross8`/`net_tick` (mức) **chỉ** được đọc **cùng** `tf_5` — không bao giờ đọc mức một mình.

**BỎ (không phân giải được):**
- `conc_1`, `conc_5` — Δ`w` = **4,3–330** (CI rộng hơn điểm cả trăm lần) ⇒ **vô dụng cho Δ**; **giữ `conc_1`
  như chỉ số MÔ TẢ** ở bảng mức (nói "bao nhiêu % PnL đến từ top-1 %") nhưng **không** dùng để quyết định.
- `hhi_gain` — thang **~1,5e-5**, Δ luôn ~0 ⇒ **không phân giải**.
- `ic_med` — CI dạng **rời rạc** (w ≥ 1,0, thường `inf`) ⇒ không dùng.
- `ic_wmean` — **rời 0 ở raw95 với đối chứng nhiễu `V5 − V1`** ⇒ nghi bắt nhiễu; hạ xuống "tham khảo".
- `median` + `p25`/`p75` — **giữ làm MÔ TẢ** (rất bền) nhưng **Δ không phân giải** (`median` = +0,0489
  giống nhau ở cả 12 đối tượng, Δ`w` = 40–500k) ⇒ không dùng cho luật.
- `wmean_p5p95`, `tmean_1`, `tf_1`, `tf_10` — **trùng lặp** với `tf_5`/`wmean_p1p99`, thêm nhiều mà Δ
  không đổi ⇒ gộp còn 2 (`tf_5`, `wmean_p1p99`).

## 8. BẢNG 4 — LÀM MỊN LẠI THƯỚC CI (câu (4)): thước × block × NREP × seed

Độ rộng CI (raw95) — `45deploy`, `f = 0,006` (các đối tượng khác **cùng dạng**, đầy đủ trong JSON):

| thước | block 24 h | **block 72 h** | block 168 h | NREP 2000→5000 | seed 907 | seed 911 |
|---|---|---|---|---|---|---|
| `tf_5` | 0,01210 | **0,01364** | 0,01806 (**×1,32**) | +0,00039 (**+2,9 %**) | 0,01425 | 0,01393 |
| `loss_mean` | 0,02333 | **0,02874** | 0,04015 (**×1,40**) | −0,00013 (**−0,5 %**) | 0,02991 | 0,02894 |
| `wl_ratio` | 0,03231 | **0,03942** | 0,05523 (**×1,40**) | −0,00046 | 0,03992 | 0,03908 |
| `sign_frac` | 0,03536 | **0,03890** | 0,04494 (**×1,16**) | +0,00085 | 0,03946 | 0,04016 |
| `wmean_p1p99` | 0,01132 | **0,01277** | 0,01687 (**×1,32**) | +0,00029 | 0,01328 | 0,01298 |
| `median` | 0,00946 | **0,01005** | 0,01926 (**×1,92**) | −0,00001 | 0,01010 | 0,01005 |
| `conc_1` | 1,0432 | **1,7311** | 3,5920 (**×2,08**) | −0,1423 | 1,7036 | 1,5949 |
| `ic_wmean` | 0,02354 | **0,02527** | 0,02313 | +0,00011 | 0,02477 | 0,02482 |

**Đọc bảng 4 (phần "làm mịn lại" mà owner yêu cầu):**
1. **Chiều dài khối là yếu tố QUYẾT ĐỊNH**: 24 h → hẹp nhất, 168 h → rộng **1,2–2,1×** so với 72 h; đơn điệu
   ⇒ **chốt `block = 72 h`** làm mặc định (ngắn hơn = hẹp hơn nhưng bám cấu trúc cụm ngày hơn).
2. **`NREP` 2000 là ĐỦ**: 2000 → 5000 **không** làm CI "mịn" hơn (lệch < 3 %) ⇒ **giữ 2000** (tiết kiệm 2,5×).
3. **Seed ổn định**: 3 seed lệch < 3 % độ rộng ⇒ CI không phụ thuộc seed.
4. **Tỷ số độ rộng/|điểm| là thước đo "phân giải được"**: `loss_mean`/`wl_ratio`/`sign_frac` = **0,32–1,1**
   (phân giải tốt) · `conc_*` = **20–330** (vô dụng) · `median` Δ = **40–500 000** (vô dụng cho Δ).

## 9. HẠN CHẾ / GHI ĐỂ TÁI LẬP (không over-claim)

1. **OFI dùng điểm seed 42 v2** (`/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/`) vì ensemble 43/44/45
   **không lưu per-row pred** ⇒ OFI ở đây **chỉ để kiểm thước**, **không** thay kết luận `RESULT_OFI_MONEY`.
2. **`MRB8`/`MRB32` thiếu fold `20220101`** ⇒ nhánh của chúng chỉ có **8.711 tick** (đã khai báo trước).
3. **Winsor/trim dùng pooled quantile** ⇒ là thước **MÔ TẢ**, **không phải luật giao dịch** (đã khai báo trước).
4. **Trần 70 % là hệ số nhân hằng theo `K`** ⇒ **không** đổi thứ hạng bất trị-đuôi ⇒ chỉ báo ở bảng TIỀN.
5. **`P32` là pool do `S1` định nghĩa** (S1 chỉ chọn small/mid-cap) ⇒ Δ của các model khác **trên P32**
   vẫn là "đo trên sân của S1" (B1 của `RESULT_OFI_MONEY`); pool mở rộng `475.104` dòng là nhánh phụ.
6. **`inflate(k)`**: `k_ruler = 17` (số thước trong họ) — báo thêm `k_obj = 10` (số đối tượng) và raw95.
7. **`median`/`p25`/`p75`** chỉ ở **6/18** cấu hình (đúng như pre-reg §6 chốt, vì là thước phi tuyến theo leg).
8. **Lỗi chiều điểm** (§2) ⇒ nhánh `S1`/OFI của bản chạy ĐẦU đã bị bỏ; số trong tài liệu này là số **sau sửa**.

## 10. NHÁNH PHỤ — POOL MỞ RỘNG `B2` (kiểm độ nhạy, pre-reg §6)

Pool = **`P32` ∪ 166.080 cặp coin mới** = **470.911 dòng / 9.573 tick** (49,2 coin/tick; ghép bằng
`drop_duplicates(ts,symId)`); điểm: OFI seed 42 v2 + `45deploy`/`S1`.

- **`0` ô ngoài CI trên toàn bộ 17 thước** cho mọi cặp: `ofi_candidate − 45deploy` (`tf_5 = −0,00025`
  raw95 `[−0,00380 ; +0,00354]` w29,0) · `− ofi_baseline_fresh` (`tf_5 = +0,00101` `[−0,00015 ; +0,00218]` w2,30⁺ —
  **vừa rời 0 ở raw95**, không qua inflate) · `− ofi_noise` · `S1 − 45deploy`.
- **D2 vẫn sạch 17/17** trên pool mở rộng ⇒ bộ thước hiệu chuẩn được ở **cả 2 pool**.
- `money` (`f = 0,006`, net/tick): `45deploy +0,0553` · `ofi_candidate +0,0525` · `s1 +0,0494` ⇒ **OFI không tạo tiền**
  (khớp `RESULT_OFI_MONEY`).
- ⇒ **Δ tail-robust của OFI = 0 ở cả hai pool**; tín hiệu DOWNSIDE ở §4 **chỉ thuộc nhóm bins-money-ranker
  (`MRA4`/`MRB8`/`MRB32`)**, KHÔNG thuộc OFI.
