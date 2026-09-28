# PREREG_ENTRY_RULERS — BỘ THƯỚC "TẦNG ENTRY" (vi mô) + LÀM MỊN LẠI

Chốt **TRƯỚC khi đo** (2026-09-28 ~15:50 GMT+7). Thuần **Python offline**; **KHÔNG** train,
**KHÔNG** sim, **KHÔNG** chạm production/242/ONNX/LIVE. DEV only: mọi dữ liệu **`<= 2025-12-31`**
(`P32` kết thúc 2025-09-27, không đọc 2026). Code: `research/analysis/entry_rulers.py`.
Kết quả: `docs/result/RESULT_ENTRY_RULERS.md` (+ `docs/result/entry_rulers.json`). Scratch: `/tmp/er/`.

## 0. Động cơ (số đã đo — KHÔNG diễn giải lại)

Tầng **TIỀN/CAGR** thiếu power: `MDE 3,6–19pp` vs cải thiện thực `1,7–5,4pp`; `N_eff ≈ 76 tuần`;
edge dồn ~9 đợt. ⇒ **~30% số vòng là "thiếu power", không kết luận được**. Vòng này **đo ở TẦNG ENTRY**
(cross-section trong pool tại mỗi quyết định vào lệnh) thay vì tầng tiền ⇒ mẫu **DÀY**: **9657 tick × 32
coin = 309.024 leg** (so với ~76 "sự kiện" của tầng CAGR).

## 1. CÂU HỎI CHỐT TRƯỚC (trả lời sau, không đổi luật)

**(1)** 4 thước mới cho kết quả gì (điểm + CI + độ rộng)? Có đối tượng nào **THẮNG ngoài CI** vs **CẢ 2**
đối chứng (kiểm chứng #1 `45deploy`, #2 `V1`) không?
**(2)** Có **đổi thứ tự xếp hạng** so với tầng TIỀN (cùng 10 đối tượng) không?
**(3)** Thước nào **PHÂN GIẢI được** (độ rộng CI/điểm nhỏ) và thước nào **không** ⇒ **đề xuất bộ chuẩn
TẦNG ENTRY (2–4 cái, không trùng)**.
**(4)** Có **tận dụng được ngay** không ⇒ **1–2 vòng xác nhận** + chi phí.

## 2. DỮ LIỆU (dùng lại, KHÔNG build lại)

- **Pool chính `P32`**: `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet`
  (**309.024** dòng = **9.657 tick** (nhịp **15 phút**) × **32** coin; `sha256 1d42b7f6…`).
  Nhãn **`y = gross`** (PnL của luật thoát). **KHÔNG** dùng `E`/`tp` (đo được: 2 cột này gần trùng
  nhau ρ=0,992 và **không** tương quan với `gross`, ρ≈−0,006 ⇒ **không** phải nhãn forward return).
- **Điểm các đối tượng**: đọc lại `/tmp/trr/scores_pool_p32.npz` (do `tail_robust_rulers.py`
  commit `4660529` xuất, đã kiểm phủ; các đối tượng, nguồn, và CHIỀU điểm **y hệt** PREREG_TAIL_ROBUST_RULERS §3).
  `S1` gốc = `/home/ubuntu/ledger/pred_s1a2x1.parquet` (6.573.909 dòng — điểm cho **toàn bộ vũ trụ**;
  nhưng **nhãn chỉ có ở pool P32** ⇒ thước entry đo trên P32, file 6,57M chỉ là nguồn điểm cho `S1`).
  OFI = seed-42 v2 proxy (`/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_*.parquet`), như vòng trước.
- **Tầng TIỀN (để so thứ tự)**: `docs/result/tail_robust_rulers.json` → `runs.p32.money[*].fees["0.006"]`
  (khoá chốt: **`net_tick`** và **`sized_A_mean`**, f=0,006 theo owner 26/09).
- **KHÔNG** chạm `242`, ONNX, LIVE.

## 3. ĐỐI TƯỢNG (10, y hệt vòng tail-robust) VÀ ĐỐI CHỨNG (2)

Đối tượng: `45deploy` · `A44` · `A45` · `V1` · `V5` · `MRA4` · `S1` · OFI `candidate` · OFI `baseline_fresh`
· OFI `noise`. Đối chứng **bắt buộc**: **#1 `45deploy`** (nền deploy) và **#2 `V1`** (nền nhiễu).
Hiệu chuẩn thước: cặp `A45−45deploy` (retrain) và `V5−V1` (nhiễu) ⇒ Δ ≈ 0, **không** được ngoài CI.
Chuẩn hoá CHIỀU: điểm CAO = TỐT cho mọi đối tượng (×−1 cho nhóm `S1`/`ofi_*`), **y hệt** vòng trước.

## 4. BỐN THƯỚC TẦNG ENTRY (chốt TRƯỚC — công thức nguyên văn)

Mọi thước tính trên **toàn bộ pool 32 coin/tick** (KHÔNG lọc top-K, KHÔNG cắt đuôi). Nhịp tick `t`.

1. **`rank_ic`** (theo tick, thước DÀY, bất trị đuôi — rank-based, bị chặn `[−1,1]`):
   `IC_t = Spearman( score_t , gross_t )` trên 32 coin của tick `t`; **điểm = trung bình các `IC_t`**.
2. **`top_decile_lift`** (lift thập phân vị trên):
   `dec_t = top ⌈0,1·32⌉ = 4` coin theo `score_t`; `lift_t = mean(gross | dec_t) − mean(gross | cả tick)`;
   **điểm = trung bình các `lift_t`**.
3. **`winrate`** (trong **cửa sổ CỐ ĐỊNH**, KHÔNG phụ thuộc đuôi):
   `net = gross − f`, `f = 0,006`; **tỉ lệ leg có `net > 0` trên TOÀN BỘ 309.024 leg pool**
   (vũ trụ cố định = mọi quyết định vào lệnh, không lọc gì).
4. **`pnl_vol_norm`** (PnL/lệnh CHUẨN HOÁ theo volatility):
   `sigma_sym` = độ lệch chuẩn `gross` của **coin đó** trên toàn mẫu (proxy vol mỗi coin, KHÔNG có ATR
   trong artifact ⇒ dùng sigma thực nghiệm, khai báo trước);
   **điểm = `mean_leg( net_leg / sigma_sym )`** trên toàn bộ leg pool.

**Thước PHỤ (thêm, "nếu hợp lý"; KHÔNG vào bộ chuẩn, chỉ để kiểm):**

5. **`edge5`** (đang dùng): `edge5_t = mean(gross | top-5 theo score_t) − mean(gross | cả tick)`;
   điểm = trung bình các `edge5_t`. (top-5/32 ≈ 16%, thô hơn lift thập phân vị.)
6. **`med_lift`** (median-based): `medlift_t = median(gross | dec_t) − median(gross | tick)`;
   điểm = trung bình các `medlift_t` (bản median của #2 ⇒ bất trị đuôi).

**BỎ có lý do (chốt trước):** **`turnover-adjusted`** — KHÔNG hợp lý ở tầng pool: mỗi tick pool nạp
**đúng 32 leg mới**, turnover **hằng** giữa mọi đối tượng ⇒ chuẩn hoá theo turnover là **hằng số nhân**,
**không đổi được thứ hạng** ⇒ vô nghĩa, bỏ (ghi rõ để không over-claim).

## 5. CI (chốt TRƯỚC) VÀ NHIỀU SO SÁNH

- **Block bootstrap theo KHỐI tick, PAIRED**: block = **72h** (`ts // (72·3600e3)`; 362 khối),
  **2000 rep**, seed **`20260905`**. Mọi đối tượng dùng **cùng** ma trận block-index (Δ ghép cặp thật).
- **`inflate(k)`**: `k=1 → 1,0`; `k≥2 → sqrt(2·ln k)`. Chốt:
  **`k_ruler = 6`** (4 thước chính + 2 phụ, đều được xét) · **`k_obj = 10`**.
  Báo **CẢ** CI thô và CI đã nới; `out = (CI thô ngoài 0) AND (CI nới ngoài 0)`.
- **Bắt buộc báo ĐỘ RỘNG**: `width` (hiệu) và `width_rel = width/|point|` cho **từng** ô ⇒ thước nào
  phân giải được. `width_rel ≥ 1` coi như **không phân giải** (CI chứa cả 0 lẫn gấp đôi điểm).
- Tập tick dùng chung cho **mọi** đối tượng (mọi coin có điểm đủ) ⇒ Δ ghép cặp thật.

## 6. LUẬT KẾT LUẬN (chốt TRƯỚC)

- **W (thắng):** đối tượng `X` (≠ 2 đối chứng) **THẮNG** nếu trên **≥ 2 thước chính** có
  Δ vs **`45deploy`** VÀ vs **`V1`** đều **ngoài CI thô & CI nới**, **cùng dấu** (dấu = hướng tốt).
- **So thứ hạng tầng TIỀN:** xếp 10 đối tượng theo `net_tick` (f=0,006) và theo `sized_A_mean`;
  xếp theo từng thước entry ⇒ tính **Spearman giữa 2 bảng xếp hạng**; báo các cặp đổi chỗ.
- **Trùng lặp giữa các thước:** Pearson + Spearman **giữa các bộ điểm của 10 đối tượng**
  (thước × thước). Cặp nào `|ρ| ≥ 0,9` ⇒ **nói RÕ là trùng** (bài học `RESULT_TAIL50_RULER_REDUNDANCY`:
  `meanP ≡ đồng nhất thức`; `win% ↔ TSloss%` ρ = −0,99) ⇒ **loại khỏi bộ chuẩn**.
- **Đề xuất bộ chuẩn ENTRY (2–4 cái, KHÔNG trùng):** giữ các thước vừa **phân giải được** vừa
  **không trùng** VÀ **phát hiện đúng cặp hiệu chuẩn là Δ≈0** (không tạo dương tính giả).

## 7. OUTPUT

`docs/prereg/PREREG_ENTRY_RULERS.md` + `research/analysis/entry_rulers.py` +
`docs/result/RESULT_ENTRY_RULERS.md` (+ `docs/result/entry_rulers.json` **nhỏ**). Commit + **push**.
