# PREP_STAGE2_TRAIN — dọn đường train cho Stage 2 (retrain S1 theo SUBSET feature)

**Ngày:** 2026-09-24 · **Nhánh:** `module` · **Trạng thái:** CHUẨN BỊ (de-risk) — KHÔNG train full, KHÔNG sim,
KHÔNG push. Job này **không** chốt thắng/thua và **không** sửa pre-reg nào.
**Việc đã làm:** xác định đường train thật · cơ chế chọn subset feature · lộ 3 bẫy cơ chế · chạy thử 1 fold
trên Kaggle để chứng minh (a) subset chạy được, (b) dựng lại đủ 45 thì tái lập được model cũ · ước lượng
thời gian/slot cho Stage 2.

---

## 0. ⚠️ ĐỌC TRƯỚC — "S1" trong repo là HAI thứ khác nhau

| tên | số feature | file | sinh ra gì |
|---|---|---|---|
| **S1 ranker** (tên gọi chính thức của repo) | **9** (`KEEP`) | `research/pipeline/x1/x1_s1_rank.py` (+ `x1_s1_5m_train.py`, `x1_s1_save_*`) | `pred_s1a2.parquet` / `pred_s1a2x1.parquet` = **thứ tự** coin trong tick |
| **net015 / G015x26** (bị gọi lẫn là "S1" trong `EVAL_SELECTOR_FEATURES.md`, `PREREG_FEAT_ABLATION.md`) | **45** (`f0..f39` + 5 OI) | `research/pipeline/g015_net_train.py` | `model_f{0..17}_4h.json` + `predict_wf_*.bin` = **giá trị** P(win) theo tick |

Đề bài Stage 2 mô tả **45 cột, 18 fold, `model_f0..f17_4h.json`, `NET_THR`, `predwf_map_s1a2_x1`** ⇒
đối tượng là **mô hình 45-feature net015**, KHÔNG phải S1-ranker 9 feature. Toàn bộ tài liệu này nói về
mô hình 45-feature; các bảng dưới dùng tên **"net015-45"** để tránh lẫn.
(Nhánh 9-feature S1-ranker: nếu Stage 2 muốn subset **nhánh đó** thì đường train là `x1_s1_rank.py` +
`X1_FEAT`, không có `--drop-cols`; **chưa làm** trong job này — xem §7.)

---

## 1. Đường train THẬT của net015-45

### 1.1 Script + luồng

```
research/pipeline/g015_net_train.py       # TRAIN (nguồn: docs/experiment/G015_RECIPE.md)
  └── build_matrix()      # dựng memmap X (N×45): 40 cột Tool1 (gather theo ridx) + 5 cột OI (merge_asof)
  └── load_labels()       # y = (retEnd_4h > 0.015)   [LABEL_MODE=net, NET_THR=0.015]
  └── train_rows()        # chọn dòng: có nhãn & ts < cutoff − 72h
  └── XGBClassifier.fit   # per fold, expanding
  └── write_bin()         # predict OOS -> predict_wf_<cutoff>.bin (26 B/rec)
research/pipeline/g015x26_train.py        # PREDICT lại từ 18 model đã lưu (KHÔNG train) -> bins
research/pipeline/x1/c4_build_map.py s1a2x1 <out>   # bins giá trị -> bins S1-order (predwf_map_s1a2_x1)
research/pipeline/x1/run_c4_sim.sh <TAG> <profile> <bins_dir>   # (Oracle) dataset + sim
research/analysis/x1_rates.py <control> <arm>       # chấm điểm
```

`g015_net_train.py` là **bản dựng lại** của trainer gốc 2026-08-14 (đã mất file; xem `G3_X26_RECOVERY.md` §8,
`G015_RECIPE.md`). Không phải bản khôi phục byte-identical, nhưng đã qua cổng so với model gốc (§1.6).

### 1.2 18 fold (cutoff / thời gian)

- **Expanding WFO**: mỗi fold train trên **toàn bộ** dữ liệu có nhãn trước cutoff, dự đoán block OOS 3 tháng.
- `OOS_MONTHS = 3`; `TZ = +7h` (cutoff đặt 00:00 GMT+7); `FIRST_CUTOFF = 20220101`.
- Danh sách cutoff **bản deploy** (`G015_RECIPE.md` §3): `20220101, 20220401, 20220701, 20221001, 20230101,
  20230401, 20230701, 20231001, 20240101, 20240401, 20240701, 20241001, 20250101, 20250401, 20250701,
  20251001, 20260101, 20260401` (18) — **fold 16/17 (`20260101`, `20260401`) nằm trên HoldoutSeal 2026-01-01**,
  không được dùng cho sim/verdict.
- **Purge**: `PURGE_STEPS = 288` bước × 15m = **72h**; `tr_cut = cutoff − 72h`; có `assert ts.max() < cutoff` mỗi fold.
- 🔴 **BẪY ĐÁNH SỐ FOLD (mới phát hiện, chưa ghi ở đâu):** `model_f<i>_4h.json` lấy `i` = **vị trí trong
  `CUT_DATES`**, mà `CUT_DATES` bản repo hiện tại đã được nối thêm 3 fold DEV2021 + `20251231`:
  `20210401, 20210701, 20211001, 20220101, …` ⇒ **cutoff 20240101 = fidx 11, không phải 8**.
  Chạy nguyên trạng repo hôm nay sẽ ghi `model_f11_4h.json` trong khi bản deploy tên là `model_f8_4h.json`
  (cùng cutoff). ⇒ **mọi bảng so sánh phải khớp theo CUTOFF, không theo số trong tên file**, hoặc phải ghim
  lại `CUT_DATES` của bản deploy.

### 1.3 Seed + nhãn + lọc

| mục | giá trị | nguồn |
|---|---|---|
| seed | **42** (`--seed`, `random_state`) | `G015_RECIPE.md` §2 |
| nhãn | **`y = (retEnd_4h > 0.015)`** (`LABEL_MODE=net`, `NET_THR=0.015`) | log kernel gốc + `G015_RECIPE.md` §2 |
| lọc nhãn | `nBars_4h >= 16` và `retEnd_4h` notna | `load_labels()` |
| base rate 4h | **0.1849** trên 48,724,373 dòng | log gốc, kiểm chứng độc lập bằng cách đếm lại 22 file `.pb` |
| `pos` per fold | 0.2699 → 0.1868 (fold 0 → 17) | bảng `G015_RECIPE.md` §3 |

🔴 **ĐÍNH CHÍNH NHÃN (quan trọng):** `EVAL_SELECTOR_FEATURES.md` §3 ghi nhãn train là `maxFav_4h >= 0.06`
là **SAI** (đã được chính `docs/diag/DIAG_RVOL15M.md` §1 sửa ngày 2026-09-24; gốc của đính chính:
`docs/runbooks/AGENT_RUNBOOK.md:306`). `maxFav_4h >= 0.06` là nhãn của **`predwf_G015_v2` / g72 / họ model LIVE
`Funding_Classifier_Final.onnx`** — model KHÁC. Bằng chứng số: `scale_pos_weight` fold 0 trong JSON =
`2.70527601` ⇒ `pos = 1/(1+spw) = 0.2699` **khớp `pos` của log**, mà `maxFav>=0.06` cho base 0.0457 ⇒ spw
sẽ ≈ 20.9 (không khớp). Không được trộn 2 họ nhãn trong cùng một bảng.

### 1.4 Tham số XGBoost (chốt)

```python
xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                  subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                  scale_pos_weight=(1-pos)/pos,      # pos = tỷ lệ lớp 1 CỦA TỪNG FOLD (không phải toàn cục)
                  eval_metric="auc", n_jobs=-1, tree_method="hist",
                  random_state=42, device=<cuda|gpu>)
```
- `scale_pos_weight` **tính theo từng fold** (fold 0 = 2.70527601 … fold 17 = 4.35441685).
- Device gốc của bản deploy = **`cuda`** (Kaggle GPU). CPU cho kết quả **khác** (một mẫu khác) — `G015_RECIPE.md` §7.1.
- `num_feature = 45`, `objective = binary:logistic`, `num_trees = 400`, xgboost **3.2.0** (đọc từ model JSON).

### 1.5 Nơi lưu model + bins

| thứ | đường dẫn | ghi chú |
|---|---|---|
| model fold | `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` (mtime 2026-08-14) | **KHÔNG được ghi đè** |
| bins giá trị (deploy) | `/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin` (16 fold, `20220101..20251001`) | `p0` = 4h |
| bins S1-order (deploy) | `/home/ubuntu/predwf_map_s1a2_x1/predict_wf_*.bin` (16 fold) | nguồn của sim `X1_C3` |
| với Stage 2 | ghi vào **thư mục mới** (`g4/net015_*_out/`, `predwf_map_s1a2_x1_<tag>`) | theo `PREREG_G015ABL.md` §3 |

### 1.6 Cổng tái lập đã biết (dùng làm mốc cho Stage 2)

- Train lại fold 20240101 (GPU, seed 42, `--drop-cols ""`) vs model gốc: **spearman 0.985997**, và
  **không phân biệt được** với nền nhiễu between-seed cùng máy (s42 vs s43 = **0.984931**).
- vì vậy **mọi variant phải so với Stage 0 retrain-full cùng session**, không so trực tiếp với bins deploy
  (`PREREG_G015ABL.md` §1, `PREREG_FEAT_ABLATION.md` §1).
- `g015x26_train.py` (predict từ model đã lưu) cho **spearman 1.0** so với bins gốc ⇒ dùng khi chỉ cần bins
  mà không train lại.

---

## 2. Cơ chế chọn SUBSET feature — sửa ở ĐÂU

### 2.1 BỎ cột (đã có sẵn, không cần sửa code)

`research/pipeline/g015_net_train.py` đã có tham số **`--drop-cols`** (thêm cho `PREREG_G015ABL.md`):

```bash
--drop-cols "9,26,33,37,38"     # chỉ số cột 0..44, cách nhau dấu phẩy
```
Cơ chế: `keep_idx = [i for i in range(NF) if i not in drop_set]` → **chỉ** cắt ở bước
`Xtr = np.asarray(X[tp])[:, keep_idx]` / `Xoo = np.asarray(X[lo:hi])[:, keep_idx]`.
⇒ **không** đụng `build_matrix` (đường đọc Tool1 + merge OI đã qua leak-audit), **không** đổi tập dòng,
**không** đổi nhãn/split/purge. `--drop-cols ""` = no-op đúng bằng hành vi gốc (đã kiểm chứng:
`RESULT_G015ABL.md` §0 khớp 0.985997).
`num_feature` của model = `len(keep_idx)`; `net_train_summary.json` ghi `drop_cols` + `keep_idx`.

Bảng chỉ số ↔ tên feature: `docs/analysis/EVAL_SELECTOR_FEATURES.md` §4 (0 = `btcMomentum1H` … 44 = `taker_buy`).

### 2.2 THÊM cột — phải sửa 3 tầng (và thứ tự cột LÀ quan trọng)

Vị trí hiện tại của 45 cột **được quyết định ở Java**, không phải Python:
`Xy[:, :40] = F[ridx]` (40 cột Tool1, thứ tự = `convertFeaturesToArray`) + `Xy[:, 40:] = 5 cột OI`.

Muốn thêm cột phải sửa **đồng bộ**:

| tầng | file / dòng | việc |
|---|---|---|
| Nguồn dữ liệu | `src/main/java/…/features/export/fundingv2/ExportFeaturesForPythonTool.java:407-427` (`convertFeaturesToArray`) | **chỉ được APPEND** (comment `#1..#21` giữ nguyên, `#22..#35` append-only). Thêm cột Tool1 ⇒ phải sửa hàm này + `Tool1ColSink` (nCols) |
| Decoder Python | `/home/ubuntu/sel1m_code/tool1_col.py:55` `N_COLS_EXPECT = 40` | header T1C ghi `nCols`; decoder **assert `n_cols == 40`** ⇒ file 41 cột sẽ nổ ngay |
| Trainer | `g015_net_train.py:56` `NF = 45`, `:120-121` `Xy[:, :40]` / `Xy[:, 40:]`, `:54-55` `OI_NAMES`/`OI_DT` | tăng `NF`, thêm khối merge mới, gán vào cột **cuối** |
| (nếu cột mới đi đường Tool1) | export lại 22 quý `.t1c.gz` → dataset Kaggle `funding-tool1-15m` version mới | nặng: phải replay/export lại toàn bộ |
| LIVE | `SelectorOnnxInferenceManager.java:26` `NUM_FEATURES = 45`, `:56-76` `extractFeatures45`; ONNX input `[0,45]` | **không đổi được ở tầng offline** — xem §3.2 |

**Cách RẺ NHẤT (và đúng hướng pre-reg) cho Stage 2:** cột mới đi **đường thứ hai giống 5 cột OI** —
một file nguồn riêng + `merge_asof(on=ts, by=symId, backward, tolerance)` trong `build_matrix`, gán vào
**các cột cuối `NF..NF+k-1`**. Như vậy 45 vị trí cũ **không xê dịch** ⇒ mọi mô hình/phân tích cũ còn so được,
và không phải đụng Java Tool1.

**Kết luận về thứ tự cột: CÓ quan trọng.** Cả `model_f*_4h.json` (`feature_names = None`) lẫn
`Funding_Classifier_Final.onnx` (`metadata_props = {}`, không lưu tên feature) đều **ánh xạ index → feature
theo thứ tự**, không theo tên. Đảo/chèn giữa danh sách = **sai âm thầm** (không lỗi load, chỉ tụt chất lượng).
⇒ Quy ước bắt buộc: **APPEND-ONLY**.

---

## 3. ⚠️ 3 BẪY PHẢI TRÁNH

### 3.1 BẪY 1 — NaN-mask: đổi cột ⇒ đổi mask ⇒ có thể tạo "định danh symbol"

- Đường 45 cột hiện tại **không lọc NaN dòng nào**: mọi dòng có nhãn đều vào train; XGBoost
  (`tree_method=hist`) tự học hướng-mặc-định cho NaN. 5 cột OI vào bằng `merge_asof … tolerance=2h`,
  **không fillna, không drop** (`G015_RECIPE.md` §2).
- **Bẫy:** nếu cột mới chỉ phủ **một subset nhỏ, không ngẫu nhiên** của universe (kiểu OFI 15/>600 symbol),
  thì mask NaN của nó **trùng khớp chính xác** với "có phải symbol trong subset đó hay không" ⇒ XGBoost học
  được một **"định danh symbol" ẩn** trong lớp vỏ của một cột thưa NaN. Đã có tiền lệ THẬT:
  `AUDIT_HARNESS_OFI_2026-09-20.md` §3 + `RESULT_S1_FREE_OFI.md` §4.1 — **đối chứng nhiễu thuần cùng mask
  NaN cũng "thắng"** (+1.69pp [+0.04,+3.93] trên CONFIRM) ⇒ hiệu ứng đo được **không đến từ nội dung feature**.
- **Cách xử lý (bắt buộc cho Stage 2):**
  1. Mọi variant **THÊM** cột phải có **đối chứng nhiễu cùng ĐÚNG mask NaN** (`noise` = NaN đúng những dòng
     cột gốc NaN, giá trị ngẫu nhiên ở các dòng còn lại; assert `isnan` khớp 100% trước khi train) —
     đúng như `PREREG_FEAT_ABLATION.md` §2.
  2. Không được kết luận "feature tốt" nếu đối chứng nhiễu cũng tốt; phải điều tra subset-selection-bias trước.
  3. Variant **BỎ** cột (`--drop-cols`) **không** tạo bẫy này: tập dòng không đổi ⇒ `n_train`/`pos`/`spw`/số
     dòng OOS **phải trùng tuyệt đối** với Stage 0. Đây là phép kiểm rẻ tiền để phát hiện subset bị lệch.

### 3.2 BẪY 2 — ONNX input dim `[0,45]` ⇒ chạm ĐƯỜNG LIVE

- Model LIVE: `/home/ubuntu/shadow_c3/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx`,
  `graph.input = [('input', [0, 45])]`, 1 node, `metadata_props = {}` (RỖNG).
- Hệ quả: **đổi số feature ⇒ BẮT BUỘC đổi ONNX input dim** ⇒ phải retrain + re-export ONNX + sửa
  `SelectorOnnxInferenceManager.NUM_FEATURES = 45` + `extractFeatures45` (thứ tự + cách ghép 5 cột OI).
  Không làm ⇒ đường LIVE vỡ/không tải được, hoặc tệ hơn: tải được nhưng **feed sai số cột**.
- 🔴 **Cảnh báo đúng mức:** Stage 2 (offline) **KHÔNG được** đụng file ONNX/thư mục `shadow_c3` — đây là
  đường LIVE đang chạy. Kết quả Stage 2 chỉ là **bins offline**. Mọi thay đổi dim/ONNX là **bước RIÊNG**,
  phải có user duyệt + kèm kế hoạch rollback.
- Thêm một điểm cần biết: **model LIVE hiện tại KHÔNG thuộc họ net015** — chấm trên 2,134,469 dòng OOS 2024Q1,
  spearman vs net015 = **0.854**, còn vs `G015_v2` (nhãn `maxFav`) = **0.961** (`AGENT_RUNBOOK.md:250-256`).
  Nên "retrain net015 theo subset" và "đổi ONNX live" là **hai việc khác nhau**, đừng gộp.

### 3.3 BẪY 3 — thứ tự cột / scale / expanding giữa train và live

- ONNX không lưu tên feature ⇒ ánh xạ theo **thứ tự Java** (`convertFeaturesToArray` 40 cột + 5 OI).
  Dao thứ tự = sai thầm. Quy ước của chính Java đã là **append-only** (`#1..#21` giữ nguyên) — giữ đúng.
- Các cột **scale/expanding** là bẫy riêng: `f21 fundingPercentileCoin`, `f22 fundingZCoin` (percentile/z
  trên toàn lịch sử `<= t`, expanding), `f23 fundingPersistence` (**proxy thời gian**: mean 22.95 → 223.91
  từ 2022Q1 → 2024Q1), `f18 basketFundingAvg` — nhóm này đã bị ablate 1 lần và cho **NULL**
  (`RESULT_G015ABL.md`: bỏ f23 → 0/5 rate thắng; bỏ thêm f18/f21/f22 → **xấu hơn rõ rệt**).
  ⇒ Nếu Stage 2 **thêm** biến thể cùng họ expanding, phải kiểm drift giữa các fold, không chỉ đọc gain.
- Bỏ cột làm **đổi `num_feature`** ⇒ XGBoost **bắt buộc train lại** (không thể `load_model` rồi cắt cột).
  Mọi so sánh "predict-only" từ model cũ với vector mới là **không hợp lệ**.
- Đường `predict → bins → sim` chỉ dùng `p0` của bins; **thứ tự cột ở tầng sim là vô nghĩa** — thứ tự chỉ
  quan trọng ở tầng model (train) và tầng LIVE (ONNX).

---

## 4. Chạy THỬ 1 fold trên Kaggle (không train full)

Script dựng kernel: `research/pipeline/x1/prep_stage2/make_prep_kernel.py` → sinh 1 kernel Kaggle
`chuyendinh/g015p2-prep-trial-gpu` (GPU, private, offline; dataset: `funding-tool1-15m`,
`funding-label-15m`, `funding-oi-percoin`, `sel1m-code` — **không upload lại gì**).

Kernel nhúng **nguyên văn** `g015_net_train.py` (base64; sha256 in ra trong log) và chạy **2 arm trên CÙNG
fold 20240101 (fold 8 bản deploy)**:

| arm | vector | mục đích |
|---|---|---|
| `A45` | 45 cột (`--drop-cols ""`) | cổng tái lập: `n_train`/`pos`/`spw`/`n_oos` phải khớp bảng `G015_RECIPE.md`, bins so với bins gốc |
| `B40` | 40 cột (`--drop-cols 9,26,33,37,38`) | subset hoá **chạy được không lỗi**; `n_train`/`pos`/`spw`/`n_oos` **phải y hệt A45** |

Kết quả đầy đủ (máy đọc): `research/pipeline/x1/prep_stage2/trial_result.json`.

### 4.1 Kết quả chạy thử — ĐÃ CHẠY (2026-09-24, kernel COMPLETE, ~12.8 phút cho cả 2 arm)

Môi trường: Kaggle **GPU**, `xgboost 3.2.0`, `device=cuda`, `seed=42`, `nest=400`, `fold=20240101`.
Trainer nhúng nguyên văn: sha256 `e8b6798fdb8e3f497e976fb45f5ad801040258902fcea0e8d4e6f6c0fc85aafc`.

| arm | vector | `num_feature` | `n_train` | `pos` | `spw` | `n_oos` | `p_mean` | `p_std` | sha256 bins | phút |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| **A45** | 45 cột | 45 | 14,834,006 | 0.18636 | 4.365823 | 2,140,992 | 0.463536 | 0.127778 | `53750a94…931d` | 7.3 |
| **B40** | 40 cột (`9,26,33,37,38`) | 40 | 14,834,006 | 0.18636 | 4.365823 | 2,140,992 | 0.462473 | 0.127969 | `b16fcc9c…0b27` | 5.3 |

**Cổng tái lập 45 cột (đề bài mục 4b): PASS — mạnh hơn yêu cầu.**

1. `n_train` / `pos` / `spw` / `n_oos` khớp **từng con số** bảng `G015_RECIPE.md` §3 (14,834,006 · 0.1864 ·
   4.365823 · 2,140,992).
2. sha256 bins của A45 = `53750a944acdb10594af20a40ae7f64bfe6d4ebdcdcba34cacfb0559ca13931d` — **trùng đúng
   bằng đã ghi** trong `G015_RECIPE.md` §5 cho "GPU tái dựng" ⇒ trên môi trường Kaggle này bản retrain
   45-cột **byte-identical** với lần tái dựng đã được tài liệu hoá.
3. So với bins **sản xuất** (`predwf_G015/predict_wf_20240101.bin`, sha `e5a684f4…`), đo bằng
   `compare_bin_spearman.py` (chỉ đọc file):

| cặp | spearman | max\|d\| | top-8/tick trùng |
|---|---:|---:|---:|
| **A45 vs bins sản xuất** | **0.985997** | 0.2304 | 0.8296 |
| B40 vs bins sản xuất | 0.981928 | 0.1903 | 0.8161 |
| B40 vs A45 (hiệu ứng bỏ 5 cột, 1 fold) | 0.982579 | 0.2494 | 0.8135 |

   Dòng A45 khớp **chính xác 6 chữ số + 2 chỉ số phụ** với `G015_RECIPE.md` §4 và `RESULT_G015ABL.md` §0
   (0.985997 / 0.2304 / 0.8296) — xác nhận độc lập lần nữa rằng cổng tái lập cũ là **thật** và tái chạy được.

**Subset hoá (đề bài mục 4a): PASS — chạy được, không lỗi.**

- B40 ghi đủ bins + model, không exception; `both_bins_written = true`.
- `n_train` / `pos` / `spw` / `n_oos` của B40 **y hệt** A45 ⇒ `--drop-cols` **không đổi tập dòng** (đúng thiết kế,
  và cũng là phép kiểm rẻ tiền phát hiện subset bị lệch).
- Ghi chú (KHÔNG phải phán quyết, mới 1 fold): B40 lệch khỏi bins sản xuất (0.981928) **nhiều hơn** mức
  lệch của A45 (0.985997), và khoảng cách A45-vs-B40 (0.982579) cũng **thấp hơn** nền nhiễu multi-seed
  cùng máy **0.984931** (`G4_RECIPE_C4.md` §2). Nhưng **không được đọc con số này thành "bỏ 5 cột là hại"** —
  `PREREG_G015ABL.md`/`RESULT_G015ABL.md` đã chỉ ra phải so **qua 18 fold + sim**, không qua venh bins 1 fold.
- ⚠️ **Xác nhận bẫy đánh số fold (§1.2) bằng thực nghiệm:** cả 2 arm đều ghi `model_f11_4h.json` cho cutoff
  `20240101` (không phải `model_f8_4h.json`). Không có gì sai về tính toán — chỉ là tên file phải đọc theo cutoff.

---

## 5. Ước lượng Stage 2 (thời gian / slot Kaggle)

Nguồn mốc: log kernel gốc `selector-15mtr-pred15-net015-gpu.log` = **3108 s ≈ 52 phút cho 18 fold** trên
Kaggle GPU (`PREREG_G015ABL.md` §2.1, dùng luôn cho ước lượng này).

| việc | chi phí | slot |
|---|---|---|
| 1 biến thể × 18 fold (train + predict + ghi bins) | **≈ 52 phút GPU** (1 kernel) | **1 kernel push** = 1 session GPU |
| 3 biến thể (Stage 0 + 2) trong `PREREG_G015ABL` | ≈ 2.6 h GPU | 3 kernel |
| mỗi lần chạy thử 1–2 fold (job này) | ≈ 10–30 phút | 1 kernel |
| `c4_build_map` + sim + chấm (Oracle) | ~15–20 phút/lần (Java) | **KHÔNG chạy trong job này** |

- Quota Kaggle: chỉ **GPU** mới tính quota (kernel CPU không tính — `docs/runbooks/KAGGLE_SIM.md:63`); hạn mức GPU là
  **mức nền tảng của Kaggle (~30 h GPU/tuần)**, không có con số nào chốt trong repo ⇒ coi là ước lượng, không
  phải quy tắc đã xác minh.
- ⇒ **Trong 1 buổi (~4–5 h GPU khả dụng)** chạy được **~5–6 biến thể** (5–6 kernel push, ~4.3–5.2 h GPU).
  Nếu chỉ tính "1 biến thể = 1 kernel": **~5 biến thể/buổi** là con số nên dùng để lập kế hoạch, và luôn
  **để dành ≥1 session** cho Stage 0 (control) chạy **cùng buổi** với các variant cần so.

**Số ĐO THẬT từ job này (thay cho ước lượng cho phần build/label):** 2 arm trên cùng fold = **12.8 phút**
(arm 45 cột 7.3 phút, arm 40 cột 5.3 phút, mỗi arm đều gồm 1 lần `build_matrix` + load label). Trong đó
**train 1 fold chỉ ~2 phút**; phần còn lại gần như cố định (dựng ma trận memmap + đọc label) ⇒ chi phí
**gần như không tăng theo số biến thể trong CÙNG một kernel**, nhưng tăng tuyến tính nếu mỗi biến thể
là một kernel riêng. Nếu quota thật sự eo hẹp: nhét **nhiều arm vào 1 kernel** (như job này) rẻ hơn về
thời-gian-chờ, không rẻ hơn về thời-gian-GPU (vẫn 1 fold × 1 train mỗi arm).
- Thời gian tường (wall-clock) lớn hơn vì mỗi biến thể còn 1 vòng sim trên Oracle (~15–20 phút) — mà
  Oracle sim **không** thuộc job này và **không** được chạy khi đang shadow LIVE.

---

## 6. Checklist trước khi bấm Stage 2

1. Stage 0 (control, `--drop-cols ""`) **cùng buổi + cùng script + cùng seed** đã có chưa? (bắt buộc)
2. Tên file model: kiểm **cutoff**, không tin số `f<i>` (bẫy `CUT_DATES`, §1.2).
3. Nếu BỎ cột: `n_train/pos/spw/n_oos` variant == Stage 0 (assert trong `net_train_summary.json`).
4. Nếu THÊM cột: có `noise` cùng mask NaN + assert `isnan` khớp 100% **trước** khi train.
5. Cột mới gán vào **cuối** vector (`NF..`), không chèn giữa.
6. Không đụng `model_f*_4h.json` gốc, không đụng `shadow_c3/…onnx`, không push.
7. Bins mới ghi ra thư mục riêng; `run_c4_sim.sh` cần **đúng 16 bins** (`20220101..20251001`) — fold 2026 là
   HoldoutSeal, không đưa vào sim.

---

## 7. Mục CHƯA xác định được (ghi rõ, không suy diễn)

1. **Nhánh 9-feature S1-ranker** (`x1_s1_rank.py`): **chưa** soát cơ chế subset (nó không có `--drop-cols`;
   subset hoá phải sửa `KEEP` trong script). Chưa xác nhận script nào đang là "hiện hành" cho nhánh này.
2. **Số biến thể tối đa** phụ thuộc hạn mức GPU Kaggle **hiện tại** — repo không ghi con số; ở đây dùng mức
   nền tảng ~30 h/tuần, **chưa xác minh**.
3. **Mapping fold → cutoff** trong `EVAL_SELECTOR_FEATURES.md` §2 vẫn chưa có file chính thức; bẫy `CUT_DATES`
   (§1.2) làm việc này **không thể** suy ra từ tên file model — mọi so khớp phải theo **cutoff**.
4. Chưa kiểm **`feature_names` giữa các bản xgboost** khi train lại bằng subset (JSON luôn để rỗng) — nên
   mọi so khớp phải dựa trên `keep_idx` ghi trong `net_train_summary.json`.
5. Chưa đo **thời gian 1 biến thể đủ 18 fold** trên môi trường hiện tại (job này chỉ chạy 1 fold × 2 arm);
   con số ~52 phút/18 fold vẫn là **mốc log gốc 2026-08-14**, chưa chạy lại kiểm.
6. **Stage 0 của Stage 2** (control retrain đủ 45 cùng buổi) **chưa chạy** — bắt buộc phải có trước khi so
   bất kỳ variant nào (`PREREG_G015ABL.md` §1, `PREREG_FEAT_ABLATION.md` §1). Job này chỉ chạy 1 fold để
   chứng minh đường, **không** phải Stage 0 (Stage 0 cần 18 fold, và phải chạy cùng buổi với các variant).
