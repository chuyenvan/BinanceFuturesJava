# PREREG_E1_CUT_TOPDECILE — CẮT "THẬP PHÂN VỊ TRÊN" của S1/OFI (đo lại bằng thước TẦNG ENTRY)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi tính bất kỳ số kết quả nào.
**Kế thừa:** `RESULT_ENTRY_RULERS` (`b03ab0a`) · `PREREG_ENTRY_RULERS` (`c24c908`) ·
`RESULT_OFI_MONEY_REORIENT` · `PREREG_OFI_MONEY_REORIENT` (`1a5cc92`).
**Ràng buộc:** thuần **Python offline**, **0 train / 0 sim**; DEV only (**≤ 2025-12-31**, pool kết thúc 2025-09-27);
**KHÔNG** chạm production/`242`/ONNX/LIVE; **KHÔNG** push file dữ liệu. Code: `research/analysis/e1_cut_topdecile.py`.
Kết quả: `docs/result/RESULT_E1_CUT_TOPDECILE.md` (+ JSON nhỏ).

## 0. ĐỘNG CƠ (số đã đo — không diễn giải lại)

`RESULT_ENTRY_RULERS` (`b03ab0a`): `top_decile_lift` của **S1 / ofi_candidate / ofi_baseline_fresh / ofi_noise**
= **ÂM** (−0,0037…+0,0009) trong khi **mọi object BINS đều DƯƠNG** (+0,0018…+0,0024)
⇒ nghi **thập phân vị TRÊN của S1/OFI PHẢN dự báo** (tiền bị bỏ sót vì chỉ cộng PnL top-8).
⚠️ Tín hiệu này **CHƯA có ý nghĩa thống kê** (`top_decile_lift`: **0/10 ngoài CI**, `w 2,2–23`)
⇒ phép đo này là **phép đo RẺ**, PHẢI có **luật chốt TRƯỚC**, không được "thấy đẹp là tin".

## 1. DỮ LIỆU & CHIỀU ĐIỂM (chốt trước)

- **Pool `P32`**: `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (**309.024** dòng =
  **9.657 tick** (nhịp 15') × **32** coin; `gross` = PnL luật thoát; nhãn **`y = gross`**).
- **`S1`**: `/home/ubuntu/ledger/pred_s1a2x1.parquet` (`ts`, `sym`, `score`).
- **3 đối tượng OFI** (candidate / baseline_fresh / noise): các file `pred_ofi_candidate_v2.parquet`,
  `pred_baseline_fresh.parquet`, `pred_ofi_noise_v2.parquet` — **đúng nguồn `entry_rulers.py` đã dùng**
  (`/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/`, họ kernel `ofi-v3`, phiên 2026-09-20) ⇒ mục §5 mới **khớp số** được.
  *(Ghi rõ: bản `pred_*.parquet` của các kernel `ofi-v3-ms-s43/44/45` đã bị DỌN khỏi đĩa sau khi kiểm ở phiên
  multiseed; chỉ còn `ms_diffs_s4*.parquet` = tổng hợp theo tick, KHÔNG có điểm theo (ts,sym) ⇒ không dùng lại được.
  Dùng đúng 4 nguồn của `entry_rulers.py` để bảo toàn sanity §5.)*
- **Chiều điểm (đã kiểm — `ofi_train_eval_v3.py:153,177`)**: `score = −pred` ⇒ **THẤP = TỐT**.
  Chuẩn hoá: `s' = ORIENT · score` với **`ORIENT = −1`** cho `S1` và cả 3 OFI (y hệt `entry_rulers.py:ORIENT`)
  ⇒ **`s'` CAO = TỐT**. **Kiểm chiều TRƯỚC khi cắt** (đúng bài học `RESULT_OFI_MONEY_REORIENT`).
- **Tập tick dùng chung** cho cả 4 đối tượng (điểm đủ trên cả 32 coin) ⇒ Δ ghép cặp thật.

## 2. ĐỊNH NGHĨA "THẬP PHÂN VỊ TRÊN" (theo TICK, số coin cắt — chốt trước)

Cắt = **loại `k_cut` coin ĐIỂM `s'` CAO NHẤT** mỗi tick, `k_cut = ceil(c · 32)`:

| mức cắt `c` | 0 % (nền) | 5 % | 10 % | 20 % |
|---|---|---|---|---|
| `k_cut` (coin bỏ) | **0** | **2** | **4** | **7** |

- `c = 10 %` ⇒ `k_cut = 4` = **đúng `kdec = 4`** của `entry_rulers.py` ⇒ khớp khái niệm "top decile".
- Sau khi bỏ `k_cut`, chọn **`K = 8`** coin điểm `s'` **cao nhất còn lại** (đúng `K = 8` vận hành).

## 3. CHỈ SỐ (trên tập chọn top-8 SAU cắt; `net = gross − f`, **`f = 0,006`**)

1. **`winrate@top-8`** = tỉ lệ leg `net > 0` trên tập chọn (từng tick).
2. **`pnl_vol_norm`** = `mean_leg( net / sigma_sym )`; `sigma_sym` = std `gross` của coin đó trên toàn mẫu.
3. **`net_tick`** = `Σ_leg net / n_tick` (`Σ` trên toàn bộ leg của tập chọn) — **đúng** `tail_robust_rulers.POINT["net_tick"]`.
4. **`TF50`** = tổng `net` của **50 % leg thấp nhất** (bỏ nửa trên theo `net`) — định nghĩa `size_count_score.py:76`.
5. **`asym`** = `mean|net| (net<0) / mean net (net>0)` — định nghĩa `size_count_score.py:82`.

## 4. CI & NHIỀU SO SÁNH (chốt trước)

- **Block bootstrap 72h, PAIRED**, `2000` rep, seed **`20260905`**; **Δ vs mức cắt 0 %** dùng **cùng** ma trận block-index.
- `inflate(k)`: `k=1 → 1,0`; `k ≥ 2 → sqrt(2·ln k)`. Chốt **`k_main = 12`** (= **3 mức cắt × 4 đối tượng**) cho **luật
  quyết định** trên `net_tick`; **báo thêm** CI thô và `k = 3` (multiplicity theo mức cắt). Báo cả `width` / `width_rel`.

## 5. SANITY (bắt buộc)

Ở mức cắt **0 %**, `winrate@top-8` và `pnl_vol_norm` phải **khớp `RESULT_ENTRY_RULERS` §2** cho 4 đối tượng
(`S1` 0,7925 / 0,1067 · `ofi_candidate` 0,7944 / 0,1131 · `ofi_baseline_fresh` 0,7912 / 0,1030 · `ofi_noise` 0,7921 / 0,1075),
sai số **≤ 0,0001**. Không khớp ⇒ **DỪNG**, báo lỗi, không kết luận.

## 6. LUẬT KẾT LUẬN (chốt TRƯỚC — KHÔNG đổi sau khi thấy số)

- **THẬT** (⇒ tiếp tục, đề xuất 1 chặng sim xác nhận): tồn tại mức cắt `c ∈ {5,10,20} %` và đối tượng sao cho
  **(a)** `Δ net_tick (c − 0 %)` **ngoài CẢ CI thô VÀ CI nới `k=12`**, theo hướng **TỐT** (`Δ > 0`); **VÀ**
  **(b)** `winrate@top-8` **và** `pnl_vol_norm` **KHÔNG xấu đi ngoài CI** theo hướng xấu (`Δ ≥ 0`, hoặc trong CI).
- **KHÔNG THẬT** (⇒ **kết luận dứt khoát: đây là NHIỄU**; **bỏ `top_decile_lift`** đúng như đã đề xuất; **dừng**, không sim):
  **không** mức cắt nào / đối tượng nào thoả **(a)**.
- Nếu **(a)** đúng nhưng **(b)** sai ⇒ **KHÔNG kết luận**, báo nguyên trạng cho MASTER (cần sim mới phân xử).

## 7. OUTPUT

`docs/prereg/PREREG_E1_CUT_TOPDECILE.md` + `research/analysis/e1_cut_topdecile.py` +
`docs/result/RESULT_E1_CUT_TOPDECILE.md` (+ `docs/result/e1_cut_topdecile.json` **nhỏ**). Commit + **push**.
