# RESULT_H72 — MODEL Ở **HORIZON 72h** (ranker sống S1): **2 THƯỚC × 3 NHÃN**

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG phần S1 (offline; **KHÔNG** sim,
**KHÔNG** Java, **KHÔNG** chạm ONNX/LIVE, **KHÔNG** chạm 2026/`HoldoutSeal`) · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_H72.md` (commit `d39d095` + AMEND `648c88b`) — **chốt TRƯỚC** khi đọc số.
**Code:** `research/analysis/h72_s1_measure.py` (dùng lại nguyên `model_ruler.tick_metrics` / `ci_mean`) ·
`research/analysis/h72_h4_delta.py` · chi phí **0 quota Kaggle** cho phần S1.

---

## 0. TRẢ LỜI NGẮN (4 câu)

1. **Model CÓ kỹ năng ở 72h — nhưng CHỈ ở tầng NHÃN, KHÔNG ở tầng TIỀN.** Ở `h = 72h`, `n_tick = 17.349`:
   nhãn `g1lite` (`ic` **+0,167`*`**, `pacc` **0,5557`*`**, `dec_rho` **+0,571`*`**) và nhãn `maxFav_72h`
   (`ic` **+0,277`*`**, `pacc` **0,5964`*`**, `dec_rho` **+0,752`*`**) ⇒ **có**; thước TIỀN `retEnd_72h`:
   `ic` **−0,0869`*`**, `pacc` **0,4689`*`** (< 0,5, ngoài CI), `netm8` −0,011 (trong CI) ⇒ **KHÔNG**,
   và quan hệ với `retEnd_72h` còn **NGƯỢC DẤU** (không phải "≈ 0" mà là "âm có ý nghĩa").
2. **`A44` vs `A45` ở 72h:** xem §5 (arm phải **train đầu 72h** — điểm 72h trong bins = NaN 100 %; xem §1).
3. **"PASS RỖNG":** phần S1 **không** có phép so arm nên **không** có PASS RỖNG; **cảnh báo base** đã ứng
   nghiệm: base `retEnd_72h` đo được **0,4066** (đúng khoảng khai trước 0,39–0,46) ⇒ **`lift@8` ở 72h NHỎ
   hơn hẳn 4h** (−0,028 vs +0,101 ở thước tiền) — **không** được đọc thành "arm tốt hơn".
4. **4h vs 72h:** trên **thước TIỀN**, 72h **KHÔNG** tốt hơn — **xấu hơn** có ý nghĩa (`Δic` **−0,0444`*`**,
   `Δpacc` **−0,0162`*`**, `Δauc8` **−0,1416`*`**, `Δlift8` **−0,1295`*`**, `Δdec_rho_lab` **−0,3565`*`**,
   ghép cặp cùng tick). Trên **thước NHÃN (`maxFav`)**, 4h **nhỉnh hơn nhẹ nhưng có ý nghĩa** ở các chỉ số
   THỨ TỰ (`Δic` −0,0208`*`, `Δpacc` −0,0076`*`, `Δdec_rho` −0,0368`*`) — **còn `auc8` thì `=`
   (Δ không ngoài CI)**. Riêng nhãn `g1lite`: 72h **vượt trội**, **NHƯNG** `g1lite` **chính là nhãn TRAIN
   của S1** ⇒ đây là **hiệu ứng mục tiêu train**, **KHÔNG** phải "horizon 72h dễ hơn" (§4.3).

---

## 1. VIỆC 0 — "RẺ TRƯỚC": **CÓ** ĐIỂM S1 SẴN ⇒ **KHÔNG CẦN TRAIN** ⇒ đo được NGAY 72h

| # | kiểm | kết quả |
|---|---|---|
| **V0-1** | có score theo `(ts, symId)` không? | **CÓ.** `/home/ubuntu/ledger/pred_s1a2x1.parquet` = `6.573.909` dòng `(ts, sym, score)`, `ts` 2021-12-31 → 2025-12-31, `17.349` tick, `378,9` coin/tick. (`score` **THẤP = TỐT`.) Bản sao byte-identical: `/home/ubuntu/claudedata/s1map_scores/pred_s1a2x1.parquet` |
| **V0-2** | ai sinh ra, có phải **walk-forward OOS** không? | `research/pipeline/x1/x1_s1_save_all_folds.py:30-45` — 16 fold `20220101..20251001`, mỗi fold `tr = D[ts < c − PURGE]`, `assert tr.ts.max() < c, "LEAK"` ⇒ mỗi tick OOS được dự báo bởi model **chỉ** train trên dữ liệu `< cutoff − 72h` ⇒ **đo OOS hợp lệ** (không phải refit toàn kỳ) |
| **V0-3** | đây có phải "model 72h" không? | **CÓ.** Nhãn train của S1 là `rel5` hạng ngũ phân vị của **`g1lite`**, mà `g1lite` **định nghĩa ở 72h** (`maxFav_72h` pha `retEnd_72h` — `x1_ledger.py:7,44`) ⇒ S1 **là** model horizon 72h; chấm nó ở 72h là chấm **đúng horizon của nó** |
| **V0-4** | ONNX `s1_model/s1a2x1_cut20251001.onnx` predict lại offline được không? | Được (cổng `manifest.json`: `score_onnx` vs `score_mem` `spearman = 0,999999999998`, `topk8` `6800/6800 = 100 %`) — **nhưng KHÔNG cần**: `pred_s1a2x1.parquet` đã là chính bản đó ở dạng per-fold. **Không** predict lại ⇒ giữ chi phí = 0 |

⇒ **VIỆC 1 (train đầu 72h cho ARM) vẫn phải làm RIÊNG cho câu (2)** — vì điểm 72h trong **bins của arm**
là `z[:,2]` = **NaN 100 %** (`docs/diag/DIAG_SCORE72H.md`, commit `ef72aed`; `model_ruler.ruler_raw` trả
`(None, None)` khi slot 3 toàn NaN — **không bịa số, không lấy `p4h` thay**). Xem §5.

---

## 2. CÁCH ĐO (đúng pre-reg §3–§5)

- **Nguồn nhãn:** `/home/ubuntu/label_15m/funding_label_*.pb`, cột **có sẵn** `retEnd_<h>`, `maxFav_<h>`,
  `nBars_<h>` — **KHÔNG** tính lại từ giá 1m.
- **3 nhãn:** (i) `g1lite_h` = `maxFav_h − min(0,5·maxFav_h; 0,08)` nếu `maxFav_h ≥ 0,05`, ngược lại
  `retEnd_h` · (ii) `retEnd_h` (**thước TIỀN**, net = gross − `FEE_RT` 0,008) · (iii) `maxFav_h` (**CHẠM**).
- **Lọc:** `nBars_h ≥ H/15m` ⇒ `16` (4h) / `288` (72h). `ts ∈ [2022-01-01, 2026-01-01)`.
- **Chỉ số:** dùng **nguyên** `model_ruler.tick_metrics` (`K_SEL = 8`, decile 10, `THR = 0,015`,
  `FEE_RT = 0,008`) — **không** viết lại, **không** đổi `K`/`THR`.
- **CI:** `stage2_score.block_boot_mean`, `BLOCK_H = 72`, `NREP = 2000`, `SEED = 20260905`,
  `inflate(k = 2)` (`c3_rates`) = **1,1774**. "`*`" = ngoài **CẢ HAI** độ rộng.
- **`pacc`/`dec_mono`/`auc8` có mốc "vô dụng" là 0,5** (không phải 0) ⇒ đọc `*` so với **0,5**;
  các chỉ số còn lại (`ic`, `dec_rho`, `glift8`, `netm8`, `lift*`, `dec_rho_lab`) so với **0**.

---

## 3. BẢNG **h = 72h** — S1, 3 NHÃN (`n_tick = 17.349`, `378,9` coin/tick)

| nhãn | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | `lift12` | `lift16` | `base` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **(i) `g1lite`** (nhãn live ranker) | **+0,16694`*`** | **0,55571`*`** | **0,61073`*`** | **+0,57102`*`** | **+0,14278`*`** | **+0,17260`*`** | **0,72264`*`** | +0,16987`*` | +0,16683`*` | +0,16243`*` | 0,62678 |
| **(ii) `retEnd_72h`** (TIỀN) | **−0,08690`*`** | **0,46887`*`** | 0,49680 (ns) | +0,00835 | −0,00546 | −0,01079 | 0,47617 (ns) | −0,02810 | −0,01869 | −0,01242 | **0,40661** |
| **(iii) `maxFav_72h`** (CHẠM) | **+0,27693`*`** | **0,59640`*`** | **0,66546`*`** | **+0,75201`*`** | **+0,16687`*`** | **+0,26884`*`** | **0,75776`*`** | +0,24054`*` | +0,23526`*` | +0,22806`*` | 0,48273 |

CI đầy đủ (block-72h, `k = 2`): `/home/ubuntu/.cache/h72_s1_agg.csv`.

**Đọc:** (i) và (iii) **có kỹ năng xếp hạng rõ** ở 72h (mọi chỉ số chính ngoài CI cùng hướng TỐT).
(ii) `retEnd_72h`: `ic` **âm ngoài CI** + `pacc` **< 0,5 ngoài CI** + `dec_mono` **không** khác 0,5 +
`glift8`/`netm8`/`lift8` **trong CI** ⇒ **KHÔNG có kỹ năng tiền**; `auc8` 0,476 (trong CI) ⇒ **kể cả**
câu hỏi nhị phân "coin nào `retEnd_72h > 1,5 %`" cũng **không** tốt hơn ngẫu nhiên.

> **Q22 ĐÚNG · Q23 ĐÚNG · Q24 ĐÚNG · Q25 ĐÚNG** (base tiền 72h = **0,4066** ∈ [0,39; 0,46]) ·
> **Q26 ĐÚNG** (`n_tick(72h) = 17.349` = **số tick có điểm S1** (pool mở cổng); 4h cũng 17.349 vì
> cùng tập tick ⇒ so được ghép cặp, xem §4).

---

## 4. 4h vs 72h — **CÙNG model, CÙNG code, CÙNG tập tick** (AMEND §11)

### 4.1 Bảng `h = 4h` (S1, y hệt §3 nhưng `h = 4h`; `n_tick = 17.349`)

| nhãn | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | `base` |
|---|---|---|---|---|---|---|---|---|---|
| (i) `g1lite_4h` | −0,00855 (ns) | **0,49616`*`** | **0,51826`*`** | +0,09640`*` | +0,01278`*` | +0,00551`*` | 0,71501`*` | +0,19805`*` | 0,26906 |
| (ii) `retEnd_4h` (TIỀN) | **−0,04243`*`** | **0,48502`*`** | 0,50340 (ns) | +0,02146 | +0,00098 | **−0,00621`*`** | 0,61668`*` | +0,10135`*` | 0,25038 |
| (iii) `maxFav_4h` (CHẠM) | **+0,29777`*`** | **0,60404`*`** | **0,68807`*`** | **+0,78879`*`** | +0,03947`*` | +0,05692`*` | **0,76567`*`** | +0,21372`*` | 0,06363 |

⚠️ **Khai báo lệch nhỏ so với AMEND §11** (ghi rõ, không che): nhãn (i) ở lượt 4h dùng **analogue theo h**
(`g1lite_4h` từ `maxFav_4h`/`retEnd_4h`) chứ không giữ định nghĩa 72h. Lý do: so sánh cùng cấu trúc nhãn.
Lượt 72h (§3) **đã** cho `g1lite_72h` trên **cùng** tập tick ⇒ vẫn có đủ cả hai để so.

### 4.2 `Δ = (h=72h) − (h=4h)`, **ghép cặp theo `ts`** (17.349 tick), CI block-72h `k = 2`

| nhãn | `Δic` | `Δpacc` | `Δdec_mono` | `Δdec_rho` | `Δglift8` | `Δnetm8` | `Δauc8` | `Δlift8` | `Δdec_rho_lab` |
|---|---|---|---|---|---|---|---|---|---|
| (i) `g1lite` | **+0,17549`*`** | **+0,05955`*`** | **+0,09247`*`** | **+0,47462`*`** | **+0,13001`*`** | **+0,16709`*`** | +0,00511 | **−0,02818`*`** | **−0,19300`*`** |
| (ii) `retEnd` (TIỀN) | **−0,04447`*`** | **−0,01615`*`** | −0,00660 | −0,01311 | −0,00644 | −0,00458 | **−0,14159`*`** | **−0,12945`*`** | **−0,35649`*`** |
| (iii) `maxFav` (CHẠM) | **−0,02083`*`** | **−0,00763`*`** | **−0,02262`*`** | **−0,03678`*`** | **+0,12741`*`** | **+0,21192`*`** | −0,00843 | +0,02682 | **−0,10978`*`** |

Bảng đầy đủ: `/home/ubuntu/.cache/h72_vs_h4_s1_agg.csv`.

### 4.3 Đọc — trả lời VIỆC 3-(4)

1. **Thước TIỀN: 4h > 72h** (không có "horizon xa thì mô hình mạnh hơn"). `Δic` **−0,0444`*`**,
   `Δpacc` **−0,0162`*`**, `Δauc8` **−0,1416`*`**, `Δlift8` **−0,1295`*`**, `Δdec_rho_lab` **−0,3565`*`**
   ⇒ ở 72h model **kém hơn** ở mọi chỉ số nhị phân/độ lớn, và **âm sâu hơn** ở chỉ số thứ tự.
   Tiền 4h **cũng đã** không có kỹ năng (`pacc` 0,485`*`, `netm8` −0,0062`*`) ⇒ **cả 2 horizon đều KHÔNG
   có kỹ năng tiền**; 72h **không** phải chỗ để đi tìm.
2. **Thước NHÃN (`maxFav`): 4h nhỉnh hơn nhẹ, có ý nghĩa ở chỉ số THỨ TỰ** (`Δic` −0,0208`*`,
   `Δpacc` −0,0076`*`, `Δdec_rho` −0,0368`*`); **nhưng `Δauc8` không ngoài CI** (−0,0084) và
   `maxFav_72h` **vẫn rất mạnh** (`pacc` 0,596`*`, `ic` 0,277`*`) ⇒ **kỹ năng "chạm" là bền qua horizon**,
   chỉ **giảm nhẹ**.
   ⚠️ `Δglift8`/`Δnetm8` **dương lớn** (+0,127/+0,212) **KHÔNG** phải model giỏi hơn: đó là **hiệu ứng
   độ dài horizon** (`maxFav_72h` lớn hơn `maxFav_4h` theo định nghĩa) — **không so được** giữa 2 horizon.
3. **Nhãn `g1lite`: 72h "vượt trội" nhưng KHÔNG dùng làm bằng chứng horizon.** `g1lite_72h` **chính là
   nhãn TRAIN** của S1 (và `base` đổi 0,269 → 0,627 giữa 2 lượt) ⇒ Δ dương ở đây là **hiệu ứng mục tiêu
   train + thang nhãn khác nhau**, không phải "72h dễ hơn". Ghi rõ để không tự lừa.

---

## 5. `A44` vs `A45` Ở `h = 72h` — (điền sau khi job Kaggle xong)

Điểm 72h trong bins arm = **NaN 100 %** (`DIAG_SCORE72H`) ⇒ **buộc phải train** đầu 72h (VIỆC 1).
Chi tiết + lệnh ở §5.1; kết quả §5.2.

### 5.1 Sửa code + chạy (theo pre-reg §5.1 — **tối thiểu**, `h = 4h` byte-identical)
- `research/pipeline/g015_net_train_add.py`: thêm `--label-h {4,72}` (mặc định **4** = hành vi cũ);
  `H_BASE_MIN = {"4h": 240, "72h": 4320}` ⇒ `NEED = 16` / **`288`**; `load_labels` đọc
  `retEnd_<h>`/`nBars_<h>`; `write_bin(..., slot=H_SLOT[h])` với `H_SLOT = {4: 0, 72: 3}` ⇒ **4h giữ
  nguyên slot 0** (byte-identical), 72h ghi **slot 3** (đúng `H_SLOT` của `model_ruler.py:64`).
  **KHÔNG** chạm ONNX/`NUM_FEATURES`/`extractFeatures45`/LIVE/sim/2026.
- `PURGE_STEPS = 288` (= 72h) **giữ nguyên** ⇒ cửa sổ chống leak **đã đủ** cho nhãn 72h.
- Kernel `chuyendinh/g015p2-h72-gpu` (sinh bởi `/home/ubuntu/kaggle_sim/h72-train/make_h72_kernel.py`
  từ kernel `g015p2-arm44-gpu`): `ARMS = "A45:;A44:36"`, **cùng 16 fold** `20220101..20251001`,
  `--label-h 72`, GPU, **0 job Oracle**.
