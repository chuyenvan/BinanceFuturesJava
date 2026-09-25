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
2. **`A44` vs `A45` ở 72h:** **vẫn THUA Ở TẦNG NHÃN**, **`≈` Ở TẦNG TIỀN** — Δ(A44−A45) trên **nhãn 72h**
   = **13/13 chỉ số âm `out_both`**; trên **`retEnd_72h`** = **0/13 âm `out_both`** (2/13 còn **dương** `out_both`).
   Ghi rõ: đây là **cross-horizon (điểm 4h × nhãn 72h)** — bản **đầu 72h thật** của arm **đang chạy** trên
   Kaggle, **chưa xong** trong ngân sách phiên này (§5.2/§5.4).
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

## 5. `A44` vs `A45` Ở `h = 72h`

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

### 5.2 (a) **CROSS-HORIZON** (điểm **4h** của arm × nhãn **72h**) — bổ sung, có NGAY, `n_tick = 140.237`

Tên gọi bắt buộc: **"cross-horizon (điểm 4h × nhãn 72h)"**. **KHÔNG** phải "đầu 72h của arm".

| thước | arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | `lift12` | `lift16` | `dec_rho_lab` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TIỀN** `retEnd_72h` | `A45` | −0,08509 | 0,47022 | 0,48978 | −0,05164 | +0,00429 | −0,00494 | 0,48075 | −0,01289 | −0,01136 | −0,01024 | +0,08034 |
| | `A44` | −0,08247 | 0,47125 | 0,49016 | −0,04844 | +0,00435 | −0,00488 | 0,48288 | −0,01218 | −0,01117 | −0,01023 | +0,07748 |
| | `45deploy` | −0,08557 | 0,47006 | 0,48917 | −0,05237 | +0,00393 | −0,00531 | 0,47911 | −0,01406 | −0,01237 | −0,01099 | +0,07996 |
| **NHÃN** `maxFav_72h` | `A45` | **+0,24288** | **0,58448** | **0,63225** | **+0,66388** | +0,09905 | +0,17331 | **0,73548** | +0,21510 | +0,19553 | +0,18050 | +0,53716 |
| | `A44` | +0,23197 | 0,58058 | 0,62742 | +0,64910 | +0,09619 | +0,17045 | 0,73048 | +0,21026 | +0,19034 | +0,17549 | +0,52138 |
| | `45deploy` | +0,24342 | 0,58468 | 0,63211 | +0,66406 | +0,09882 | +0,17308 | 0,73495 | +0,21470 | +0,19528 | +0,18015 | +0,53807 |

`base(yb)` ở 72h trên tập này: TIỀN **0,38900** · NHÃN **0,38354** (khớp khoảng khai trước 0,39–0,46/xấp xỉ).

**`Δ = A44 − A45`** (ghép cặp `ts`, CI block-72h `k = 2`; `*` = ngoài **CẢ HAI** độ rộng):

| thước | `Δic` | `Δpacc` | `Δdec_mono` | `Δdec_rho` | `Δglift8` | `Δnetm8` | `Δauc8` | `Δlift8` | `Δlift12` | `Δlift16` | `Δdec_rho_lab` | đếm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **TIỀN** | **+0,002616`*`** | **+0,001029`*`** | +0,000375 | +0,003199 | +0,000054 | +0,000054 | +0,002131 | +0,000715 | +0,000195 | +0,000002 | −0,002862 | **Δ<0 `out_both`: 0/13** · Δ>0: 2/13 |
| **NHÃN** | **−0,010912`*`** | **−0,003899`*`** | **−0,004829`*`** | **−0,014787`*`** | **−0,002862`*`** | **−0,002862`*`** | **−0,005001`*`** | **−0,004844`*`** | **−0,005186`*`** | **−0,005007`*`** | **−0,015777`*`** | **Δ<0 `out_both`: 13/13** |

**Đối chứng retrain `Δ = A45 − 45deploy`** (cross-horizon 72h): TIỀN **0/12** âm `out_both`
(1/12 dương `out_both`: `Δlift12` = **+0,001011`*`**, cỡ 1,0e−3); NHÃN **0/12** âm `out_both`, cũng **0/12** dương
`out_both` ⇒ **đối chứng còn đúng chức năng** (retrain ≈ deploy).

**NHÃN — so với 4h (`RESULT_MODEL_RULER` §14.3) cùng chỉ số:** `Δic` −0,017143`*` → **−0,010912`*`**;
`Δpacc` −0,006312`*` → **−0,003899`*`**; `Δdec_mono` −0,008076`*` → −0,004829`*`; `Δdec_rho` −0,019270`*` →
−0,014787`*`; `Δglift8` −0,000420`*` → **−0,002862`*`**. ⇒ **cùng DẤU (A44 vẫn thua ở tầng NHÃN)**, biên độ
**nhỏ hơn** ở chỉ số thứ tự (hợp với "base 72h cao hơn ⇒ Δ nhỏ hơn", §7-6) nhưng **lớn hơn** ở `glift8/netm8`.

### 5.3 (b) **ĐẦU 72h THẬT** của arm — **CHẠY CHƯA XONG** (ghi rõ, không bịa)

| mục | trạng thái |
|---|---|
| Kernel | `chuyendinh/g015p2-h72-gpu` (private, GPU) — **`running`** lúc **13:01** (đẩy 12:41) |
| Cấu hình | `ARMS = "A45:;A44:36"` · **16 fold** `20220101..20251001` · `--label-h 72` · `write_bin(slot=3)` · seed 42 · `PURGE = 288 bước` |
| Chi phí (mốc ĐO ĐƯỢC của cùng kernel ở 4h) | **79,0 phút** / 2 arm / 16 fold (`DONE 75.8 phut` bản gốc) ⇒ **≈1,3 GPU-giờ**, **1 phiên kernel**, quota Kaggle 30 h/tuần ⇒ **lọt** |
| **Số arm xong** | **0/2** (chưa trả kết quả trong ngân sách phiên) ⇒ **KHÔNG có** bảng `A44`/`A45` đầu-72h |
| Bù lại | §5.2 **cross-horizon** đã cho câu trả lời tầng NHÃN/TIỀN; **đối chứng retrain** đã chạy; **đối chứng nhiễu `V5−V1` CHƯA chạy** (ngắt vì áp lực RAM trên máy shadow — xem §6-3) |

**Đường hoàn tất (đã tự động hoá 1 nửa):** `wait_dl.sh` đang chạy nền trên Oracle sẽ **tự tải** output
kernel về `/home/ubuntu/kaggle_sim/out/h72/` khi job xong. Khi có bins, chạy:
```bash
for A in A45 A44; do python3 -u research/analysis/model_ruler.py ruler --name ${A}h72 \
  --bins /home/ubuntu/kaggle_sim/out/h72/stage2/$A --horizon 72h --k 2 \
  --per-tick /home/ubuntu/.cache/h72head_${A}_ticks.parquet --out /home/ubuntu/.cache/h72head_${A}.json; done
# roi doi `--y-kind maxfav --label-kind y1` cho thuoc NHAN, va tinh Delta(A44-A45) nhu xh_arm_delta.py
```
**LƯU Ý khi đó:** `model_ruler --horizon 72h` đọc điểm ở **slot 3** — đúng cái `write_bin(slot=3)` đã ghi.

---

## 6. TRẢ LỜI BẮT BUỘC (VIỆC 3)

### (1) Model có **kỹ năng ở 72h** không — ở **thước NHÃN** và ở **thước TIỀN**?

| tầng | ở 72h | bằng chứng |
|---|---|---|
| **NHÃN** (`g1lite`, `maxFav_72h`) | **CÓ — mạnh** | S1: `g1lite` `ic` **+0,167`*`**, `pacc` **0,556`*`**, `dec_rho` **+0,571`*`**, `netm8` **+0,173`*`**; `maxFav_72h` `ic` **+0,277`*`**, `pacc` **0,596`*`**, `dec_rho` **+0,752`*`**, `netm8` **+0,269`*`**. Cross-horizon arm `A45`: `maxFav_72h` `ic` +0,243, `pacc` 0,584 |
| **TIỀN** (`retEnd_72h` net) | **KHÔNG — và còn NGƯỢC DẤU** | S1: `ic` **−0,0869`*`**, `pacc` **0,4689`*`** (< 0,5), `dec_mono` 0,4968 (ns), `glift8`/`netm8`/`lift8` **trong CI**; `auc8` 0,476 (ns) ⇒ **kể cả** câu hỏi nhị phân `retEnd_72h > 1,5 %` **cũng không** hơn ngẫu nhiên. Cross-horizon arm `A45`/`A44`/`45deploy`: `ic` −0,083…−0,086, `pacc` 0,470 |

⇒ **"Có kỹ năng" ĐÚNG nhưng CHỈ ở tầng NHÃN.** Câu này **giống hệt** kết luận 4h (§14.4), chỉ **khác độ lớn**:
ở tầng TIỀN, model **không** có kỹ năng **và** xếp hạng của nó **âm** so với `retEnd_72h` (không phải "≈ 0",
mà là "**ngược dấu có ý nghĩa**"). Nói thẳng: **không có tín hiệu TIỀN ở 72h** — không tô hồng.

### (2) `A44` vs `A45` ở 72h: thua ở **tầng nào**?

**Thua ở TẦNG NHÃN. `≈` (không thua) ở TẦNG TIỀN.** (cross-horizon, `n_tick = 140.237`):
- TẦNG NHÃN `maxFav_72h`: `Δ(A44−A45)` = **13/13 chỉ số âm `out_both`** (`ic` −0,0109`*`, `pacc` −0,0039`*`,
  `dec_rho` −0,0148`*`, `glift8` −0,0029`*`, `auc8` −0,0050`*`, `dec_rho_lab` −0,0158`*` …).
- TẦNG TIỀN `retEnd_72h`: **0/13 âm `out_both`**; 2 chỉ số **dương** `out_both` (`ic` +0,0026`*`,
  `pacc` +0,0010`*`) ⇒ `A44` **không thua** (nhỉnh **không đáng kể**).
- ⇒ **BƯỚC SAI = MỤC TIÊU (NHÃN)** — **bất kể horizon**. `rvol15m` giúp *"coin nào LÊN/CHẠM mạnh"*,
  **không** giúp *"coin nào LÃI RÒNG nhiều hơn"* — và ở 72h, **không arm nào** có kỹ năng lãi ròng.
- **Cảnh báo đúng mức:** đây là **cross-horizon** (điểm **4h** của arm × nhãn 72h). Nó trả lời *"xếp hạng
  arm đang deploy, chấm bằng nhãn 72h"* — **KHÔNG** trả lời *"arm train riêng cho 72h thì sao"*
  (job §5.3 chưa xong). Không được trích §5.2 như "kết quả đầu 72h".

### (3) Có **"PASS RỖNG"** không (Δ≈0 vì base 72h 0,39–0,46)?

**KHÔNG có bằng chứng PASS RỖNG ở đây.**
- Tầng **NHÃN** 72h **không hề** Δ≈0: 13/13 âm `out_both` ⇒ có **kết luận thật**, không phải "pass".
  (Biên độ **nhỏ hơn** 4h ở chỉ số thứ tự — **đúng** như khai trước vì base 72h cao hơn — nhưng vẫn **ngoài CI**.)
- Tầng **TIỀN** `Δ ≈ 0` **KHÔNG do base cao**: **4h** (base `retEnd_4h` = **0,250**) đã `Δ ≈ 0` y hệt
  (`§14.3`: 0/4 âm `out_both`), và base 4h **thấp**, không thể là nguyên nhân. ⇒ `Δ ≈ 0` ở tầng tiền là
  **hiện tượng thật, bất biến theo base/horizon**, không phải artefact của base 72h.
- Vẫn ghi **`base(yb)`** kèm mọi bảng (§3: 0,4066 · §5.2: 0,389 / 0,3835) và **`Δ` thô** để thấy độ lớn.

### (4) So **4h** và **72h**: horizon nào model mạnh hơn?

Trả lời bằng **Δ ghép cặp cùng model/cùng tick** (S1, §4.2) — chứ **không** đem 2 bảng khác universe ra so:
| tầng | 4h vs 72h | kết luận |
|---|---|---|
| **TIỀN** `retEnd` | `Δic` **−0,0444`*`**, `Δpacc` **−0,0162`*`**, `Δauc8` **−0,1416`*`**, `Δlift8` **−0,1295`*`**, `Δdec_rho_lab` **−0,3565`*`**; `Δdec_mono/Δdec_rho/Δglift8/Δnetm8` = ns | **4h > 72h** (rõ). Cả 2 horizon **đều không có kỹ năng tiền** |
| **NHÃN** `maxFav` | `Δic` **−0,0208`*`**, `Δpacc` **−0,0076`*`**, `Δdec_mono` **−0,0226`*`**, `Δdec_rho` **−0,0368`*`**; **`Δauc8` = ns (−0,0084)**; `Δlift8` ns | **4h nhỉnh hơn nhẹ nhưng có ý nghĩa** ở chỉ số THỨ TỰ; ở chỉ số **NHỊ PHÂN (`auc8`)** thì **`=`**. `maxFav_72h` vẫn **rất mạnh** (`pacc` 0,596`*`) ⇒ kỹ năng "chạm" **bền qua horizon**, chỉ **giảm nhẹ** |
| (i) `g1lite` | `Δic` **+0,1755`*`** (72h "thắng") | ⚠️ **KHÔNG** được đọc là "72h mạnh hơn": `g1lite` **chính là nhãn TRAIN của S1** (và `base` đổi 0,269 → 0,627) ⇒ **hiệu ứng mục tiêu train**, không phải độ dễ của horizon |

⇒ **Kết luận gọn:** model **mạnh nhất ở 4h trên cả hai tầng đo được**, và ở **cả hai** horizon **kỹ năng
TIỀN đều bằng 0 (thậm chí âm)**. **72h KHÔNG phải hướng để đi tìm** — chỉ là nơi **kỹ năng NHÃN còn sống
nhưng yếu hơn**.

---

## 7. HẠN CHẾ / KHÔNG ĐO ĐƯỢC (ghi rõ, KHÔNG suy diễn)

1. **Đầu-72h THẬT của arm: CHƯA có số** (§5.3) — job Kaggle `chuyendinh/g015p2-h72-gpu` **`running`** khi
   hết ngân sách phiên. **KHÔNG** bịa, **KHÔNG** lấy cross-horizon thay.
2. **Đối chứng nhiễu `V5 − V1`** (72h) **CHƯA chạy**; đối chứng **retrain** `A45 − 45deploy` **đã chạy**
   (cross-horizon) và **còn đúng chức năng** (§5.2).
3. **Phải ngắt 3 lượt chạy** (`V5`,`V1`,`45deploy` ban đầu chạy song song) vì RAM còn **2 GB** trên máy
   đang chạy **shadow LIVE** — **ưu tiên an toàn cho LIVE** hơn dữ liệu bổ sung. Đã chạy lại `45deploy`
   đơn lẻ sau đó (thành công).
4. **Universe khác nhau, KHÔNG so chéo:** S1 chấm trên **pool tick của nó** (`17.349` tick, `378,9`
   coin/tick — ledger chỉ có tick cổng mở); arm chấm trên `140.237` tick × ~255 coin (bins full-universe).
   Vì vậy **số của S1 (§3/§4) và số của arm (§5.2) là HAI SÀN khác nhau** — chỉ so **trong** cùng sàn.
   *Điều này KHÔNG ảnh hưởng Δ(A44−A45) (cùng sàn) hay Δ(72h−4h) của S1 (cùng tick, đã kiểm tra `ts` trùng
   khít).*
5. `retEnd` là **GROSS**; `net` trừ đúng `FEE_RT = 0,008` theo code, **CHƯA** trừ funding.
6. Lượt `h = 4h` của S1 dùng **analogue theo h** cho nhãn (i) (`g1lite_4h`) — **lệch nhỏ** so với AMEND §11
   (đã khai ở §4.1). Không đổi nhãn (ii)/(iii).

---

## 8. MỤC KẾT LUẬN KHÔNG ĐỔI

Kết luận `NOT GO` của `RESULT_MODEL_RULER` §13.3 dựa trên điều kiện (i) ở **4h** ⇒ **72h không thể đảo**.
Vòng này **thêm** một dữ kiện **cùng chiều XẤU** (không phải cùng chiều tốt): ở **72h**,
- **không** arm/model nào có kỹ năng **TIỀN** (S1 `pacc` 0,469`*`; arm cross-horizon `pacc` 0,470);
- `A44` **vẫn thua** `A45` ở **tầng NHÃN** (13/13 âm `out_both`);
- kỹ năng NHÃN ở 72h **yếu hơn** 4h.
