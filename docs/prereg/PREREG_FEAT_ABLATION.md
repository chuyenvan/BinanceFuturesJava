# PREREG_FEAT_ABLATION — bỏ nhóm NGẮT CHẮC (5/45 feature) của selector S1

**Ngày chốt:** 2026-09-24 · **Chi nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC — **CHƯA CHẠY**
**Phụ thuộc:** `docs/analysis/EVAL_SELECTOR_FEATURES.md` (commit `025767f`) — nguồn của mọi con số nhóm/feature ở đây.
**Pre-reg này khoá:** biến thể, chỉ số, CI, luật quyết định, trần số vòng. **Không sửa sau khi xem số.**

---

## 0. Câu hỏi và biến thể

**Câu hỏi:** 5 feature `NGẮT CHẮC` (#9 `rsi1H`, #26 `volumeZCoin`, #33 `volumeZRankCS`, #37 `volumeZ5m`,
#38 `closePosRange15m` — tổng share **1,61%** gain / 18 fold, có ràng buộc trùng lặp `|rho| ≥ 0,8` với
partner mạnh hơn ≥2,5× hoặc share < 0,40%) có thể bỏ khỏi vector 45 mà **không làm hại** selector S1 không?

**Biến thể (đúng 3 lần train, 1 vòng):**

| id | Vector feature | Mục đích |
|---|---|---|
| `baseline_fresh` | **45** cột (đủ) | Đối chứng 0 — train lại trong CÙNG session |
| `cut5` (candidate) | **40** cột = 45 trừ {9, 26, 33, 37, 38} | Biến thể cần phán xử |
| `noise5` (đối chứng nhiễu) | **40** cột = 45 trừ {9,26,33,37,38} **rồi chèn lại 5 cột nhiễu thuần** vào đúng 5 vị trí đó, với **ĐÚNG NaN-mask** của 5 cột gốc | Tách "hiệu ứng nội dung feature" khỏi "hiệu ứng bỏ/thêm cột + mask" (bài học `RESULT_S1_FREE_OFI.md`) |

**KHÔNG** thử thêm biến thể nào khác trong vòng này. Nhóm `CÂN NHẮC` (18 feature) và các cặp trùng lặp
(`ls_global`–`ls_toptrader`, `f19`–`f24`, `f17`–`f21`, `f8`–`f31`, `f12`–`f15`) **thuộc vòng sau** và cần
pre-reg riêng.

---

## 1. Bước 0 — tái lập baseline + tính tất định (bắt buộc, TRƯỚC mọi so sánh)

1. `baseline_fresh` phải được train **mới, trong cùng kernel/session** với `cut5`/`noise5` (cùng code,
   cùng seed, cùng `n_jobs`). **Không** so trực tiếp với `predwf_G015/model_f*_4h.json` (2026-08-14) —
   retrain từ đầu không byte-identical.
2. Chạy `baseline_fresh` **2 lần**; yêu cầu `max|d| = 0` trên toàn bộ trường dự đoán OOS.
   Nếu khác → **DỪNG**, không đọc kết quả vòng này.
3. Kiểm tra số dòng/pool của cả 3 nhánh **trùng tuyệt đối** (`assert` trên `(ts_h, sym)`), `score`
   không NaN/Inf.
4. Cổng tái lập dữ liệu: số dòng/tick phải khớp **đúng mốc mà harness hiện hành ghi ra** (script
   pre-reg phải in mốc trước khi train; ví dụ mốc cùng họ ở `RESULT_S1_HPO_BAG_FEATGRP.md`:
   `n_b18 = n_split = n_join = 6.685.957`, 18.283 tick OOS — **dùng làm tham chiếu, không mặc định
   trùng**, vì pool của vòng này còn phụ thuộc cửa sổ/kernel thực chạy). Lệch mốc → DỪNG.

---

## 2. Đối chứng nhiễu — BẮT BUỘC, dùng ĐÚNG ĐÚNG NaN-mask của candidate

> Bài học `RESULT_S1_FREE_OFI.md`: một cột **nhiễu thuần** (`noise_ofi_check`) **cùng mask NaN** với
> candidate vượt ngưỡng trên CẢ SELECT lẫn CONFIRM (`+1,69pp [+0,04, +3,93]`) ⇒ hiệu ứng đo được
> **không đến từ nội dung feature**. Biên độ nhiễu khi train mới là **~1–3pp edge5**, lớn hơn mọi hiệu
> ứng feature thực đã đo. Vì vậy **không có đối chứng nhiễu thì vòng này vô giá trị.**

Cách dựng `noise5` cho ablation **bỏ** cột:

- Lấy vector 45 cột như `baseline_fresh`; bỏ 5 cột {9,26,33,37,38}.
- Sinh 5 cột nhiễu **hoàn toàn ngẫu nhiên** (seed ghi rõ trong log, khác seed 42 của train; ví dụ
  `np.random.default_rng(20260924)`), **chuẩn hoá về cùng phân vị/thang** của cột gốc là KHÔNG cần —
  chỉ cần **mask** đúng:

  `noise[:,j] = NaN` tại **đúng những dòng** mà cột gốc `j` là NaN, và là giá trị ngẫu nhiên ở các dòng còn lại.
- **Assert bằng số trước khi train:** `isnan(noise_j) == isnan(orig_j)` trên **100%** dòng cho cả 5 cột
  (`nan_rate` gốc để đối chiếu: `f9/f37/f38` ≤ 0,01%; `f26` ~0%; không có NaN hệ thống).
- Nếu mask không khớp tuyệt đối → sửa, **không** train.

**Diễn giải:** nếu `|Δ(cut5 − baseline_fresh)|` ở cùng độ lớn với `|Δ(noise5 − baseline_fresh)|` và
`Δ(cut5 − noise5)` có CI chứa 0 ⇒ **không phân biệt được** ⇒ kết luận **NULL / không đo được**,
**giữ nguyên 45 feature**.

---

## 3. Cùng fold / seed / cửa sổ / nhãn (không đổi gì ngoài vector feature)

- **Model:** S1 selector XGBoost (`binary:logistic`, `scale_pos_weight` như bản deploy), fold **expanding**
  như `predwf_G015` (18 model `model_f0..f17_4h.json`, cutoff cách nhau ~1 quý theo cách đặt tên).
  Hyperparameter **đọc nguyên từ kernel/config đã sinh ra `model_f*_4h.json`**
  (`chuyendinh/selector-15mtr-pred15-net015-gpu`) và giữ y nguyên — **không tune**. Tham chiếu bộ số
  cùng họ ở `train_funding_selector_wfo.py:186` (`n_estimators=400`, `max_depth=5`,
  `learning_rate=0.05`) — **phải xác minh lại** là đúng của model S1 trước khi chạy, không mặc định.
- **Nhãn:** `y = (maxFav_4h ≥ 0.06)` (WIN 6%), khung 4h. **Không** đổi nhãn (nhãn `retEnd_4h` chỉ dùng cho
  đo mô tả ở `EVAL_SELECTOR_FEATURES.md` §3).
- **Nguồn feature:** ma trận Tool1 (`ds_feat15m`, `read_tool1`) + 5 cột OI, merge `merge_asof backward`
  `(symId, ts)` tol 2h — y nguyên pipeline gốc. Nếu có sẵn `feat_v2_x1.parquet`-style CSV thì nạp 1 lần
  vào RAM, **không** replay Aerospike.
- **Purge/embargo:** giữ như bản gốc (purge = horizon giữa train/OOS).
- **Cửa sổ:** DEV only — 16 fold `2022-01-01 .. 2025-12-31`, **tuyệt đối không chạm 2026** (holdout seal).
- **Chi phí:** trần **1 vòng** (3 lần train). Ghi lại slot/thời gian/các lần chạy bị huỷ.

---

## 4. Chỉ số và CI

| # | Chỉ số | Vai trò | Cách đo |
|---|---|---|---|
| P | **rank-IC** (Spearman trong tick, de-overlap 15m) theo từng fold + trung bình | CHÍNH | như `wfo_selector_results.json` (mốc tham chiếu 4h: median 0,2899) |
| S | **edge5** = edge của 5% điểm tốt nhất vs nền | PHỤ (quyết định) | theo fold, rồi CONFIRM |
| C | LIFT top-decile, hit_top, base_rate, N | chẩn đoán | per fold, xuất chuỗi |

- **CI:** block-bootstrap khối **72h**, `NREP=2000`, `seed=20260905`, **hiệu chỉnh `inflate(k)`** quanh tâm,
  `k` = **số ứng viên của pre-reg này**.
- **Lệnh CI chuẩn (bắt buộc dùng, không tự viết lại):**
  `python3 research/analysis/x1_rates.py --k <so_ung_vien> <arm_A> <arm_B>`
  → dùng để chấm `cut5` vs `baseline_fresh` và `noise5` vs `baseline_fresh`.
- **`k` khai báo trước:** `k = 3` (2 cắt-thật-nhiễu là `baseline_fresh`/`cut5`/`noise5` ⇒ 2 phép so sánh
  quyết định + 1 đối chứng nền). Nếu phải chạy lại Stage 0 hoặc chạy thêm lần nào → **tăng `k`** và ghi rõ.
- **Multiplicity (đếm biến thể đã thử):** vòng này `n_variant = 3`; báo cáo **toàn bộ** (không giấu nhánh
  nào), kèm `n_variant` trong doc RESULT. Nhiều vòng ⇒ cộng dồn và ghi vào bảng cuối.

---

## 5. Luật quyết định (chốt trước, không diễn giải lại sau)

1. **Cổng 0:** §1 PASS (tất định + mốc dòng/tick khớp). Fail ⇒ DỪNG.
2. **Cổng nhiễu:** bắt buộc có `noise5`. Nếu `Δ(cut5 − noise5)` có **CI chứa 0** ⇒
   **kết luận = "NULL/không phân biệt được"** ⇒ **GIỮ 45 feature**, đóng trục này.
3. **Cổng quyết định:** bỏ 5 feature **chỉ được chấp nhận** khi **đồng thời**:
   - (a) `cut5` **không thua** `baseline_fresh` ngoài CI ở **cả** rank-IC (P) **và** edge5 (S) —
     tức `Δ` có CI chứa 0 **hoặc** nghiêng về `cut5`; **VÀ**
   - (b) `cut5` **khác** `noise5` ngoài CI theo hướng tốt hơn (chứng minh 5 cột có nội dung thật);
     **VÀ**
   - (c) không vi phạm ràng buộc cứng nào (không NaN/Inf; `n` leg không đổi bất thường).
4. Nếu (a) đúng nhưng (b) sai ⇒ **NULL** (giữ). Nếu (a) sai (cut5 **kém** ngoài CI) ⇒ **GIỮ** và ghi rõ
   "5 feature này có đóng góp cộng hưởng dù đơn biến vô dụng" — tương ứng cảnh báo trong
   `wfo-feature-ablation` bước 7 (**không dùng IC đơn biến làm tiêu chí cắt**).
5. **Kết quả tồi tệ nhất phải ghi:** candidate ≈ noise. Khi đó mọi "cải thiện" đều là artifact harness.

**DỰ ĐOÁN KHOÁ TRƯỚC (ghi để chống diễn giải lại):** với tổng share chỉ **1,61%** và biên độ nhiễu
retrain đã đo **~1–3pp edge5**, dự đoán **NULL** (không phân biệt được `cut5` vs `baseline_fresh`);
kỳ vọng cao nhất là "không hại" chứ không phải "tốt hơn".

---

## 6. Ràng buộc và những gì KHÔNG làm trong vòng này

- Không chạy job/Java/sim trên máy nào trong bước viết pre-reg; không tune hyperparameter; không đổi nhãn.
- Không dùng 2026; không push; không dùng `claude-run`/Claude Code.
- **Không tự chạy sim** khi có kết quả IC tốt hơn: theo `wfo-feature-ablation` bước 8, muốn chạy sim phải
  có pre-reg **riêng** (hoặc phụ lục ghi xác nhận trong chat của user) — IC tốt hơn **không** tự động là
  lý do đổi gate/selector production.
- Điều kiện "đóng trục": nếu Cổng nhiễu ⇒ NULL ở vòng này, **không** thử thêm biến thể cắt-lẻ khác của
  cùng 5 feature (multiplicity); muốn thử nhóm `CÂN NHẮC`/cặp trùng lặp ⇒ pre-reg mới, `k` mới.

---

## 7. Bảng kết quả (append-only — điền khi RESULT ra đời)

| vòng | candidate | vector | rank-IC Δ [CI] | edge5 Δ [CI] | vs noise | verdict | commit RESULT |
|---|---|---|---|---|---|---|---|
| 1 | `cut5` (bỏ #9,26,33,37,38) | 40/45 | — | — | — | — | — |

**Danh sách cột GIỮ trong `cut5` (40 index):** 0,1,2,3,4,5,6,7,8,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,27,28,29,30,31,32,34,35,36,39,40,41,42,43,44.
**Cột BỎ:** 9 (`rsi1H`), 26 (`volumeZCoin`), 33 (`volumeZRankCS`), 37 (`volumeZ5m`), 38 (`closePosRange15m`).
