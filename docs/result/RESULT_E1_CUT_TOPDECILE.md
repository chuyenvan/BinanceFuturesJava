# RESULT_E1_CUT_TOPDECILE — CẮT "THẬP PHÂN VỊ TRÊN" của S1/OFI (đo lại bằng thước tầng ENTRY)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG
**Pre-reg:** `docs/prereg/PREREG_E1_CUT_TOPDECILE.md` (chốt **TRƯỚC** khi tính số).
**Code:** `research/analysis/e1_cut_topdecile.py`. **Số thô:** `docs/result/e1_cut_topdecile.json` (28 KB).
**Kế thừa:** `RESULT_ENTRY_RULERS` (`b03ab0a`) · `PREREG_ENTRY_RULERS` (`c24c908`) · `PREREG_OFI_MONEY_REORIENT` (`1a5cc92`).
Thuần **Python offline**, **0 train / 0 sim**; DEV only (**≤ 2025-12-31**; pool `P32` hết 2025-09-27);
**KHÔNG** chạm `242`/ONNX/LIVE; **KHÔNG** push file dữ liệu.

**Mẫu:** `P32` = **9.651 tick dùng chung** (nhịp 15') × 32 coin = **308.832 leg** — đúng tập tick mà
`entry_rulers.py` dùng (tái lập bằng mask 10 đối tượng, bỏ **6** tick). `f = 0,006`, `K = 8`.
CI block-72h **paired**, **2000 rep**, seed **20260905**; `k_main = 12` (3 mức cắt × 4 đối tượng) ⇒
`inflate = 2,2293`; `k_alt = 3` ⇒ `1,4823`. `k_cut = ceil(c·32)` = **0 / 2 / 4 / 7** coin cho `c = 0 / 5 / 10 / 20 %`.

## 1. CHIỀU ĐIỂM ĐÃ KIỂM (ĐÚNG)

`score = −pred` ⇒ **THẤP = TỐT**; chuẩn hoá `s' = ORIENT·score`, **`ORIENT = −1`** cho `S1` + cả 3 OFI
(y hệt `entry_rulers.py:ORIENT`) ⇒ **`s'` CAO = TỐT**; cắt = bỏ `k_cut` coin `s'` **CAO NHẤT** mỗi tick.
**Bằng chứng chiều ĐÚNG:** hai sanity dưới đây khớp **tuyệt đối**. Nếu chiều sai, top-8 sẽ là "8 coin tệ nhất"
và số sẽ lệch hoàn toàn.

## 2. SANITY — MỨC CẮT 0 % TÁI LẬP ĐÚNG

| đối tượng | `winrate@top-8` (đo / `RESULT_ENTRY_RULERS`) | `pnl_vol_norm` (đo / `RESULT_ENTRY_RULERS`) | `net_tick` (đo / `tail_robust_rulers.json`) |
|---|---|---|---|
| S1 | **0,792509** / 0,7925 ✅ | **0,106665** / 0,1067 ✅ | **0,048154** / 0,048154 ✅ |
| ofi_candidate | **0,794438** / 0,7944 ✅ | **0,113121** / 0,1131 ✅ | **0,051455** / 0,051455 ✅ |
| ofi_baseline_fresh | **0,791174** / 0,7912 ✅ | **0,102954** / 0,1030 ✅ | **0,044056** / 0,044056 ✅ |
| ofi_noise | **0,792068** / 0,7921 ✅ | **0,107492** / 0,1075 ✅ | **0,049599** / 0,049599 ✅ |

⇒ Khớp cả **tầng entry** (sai số ≤ 1e-4) **và tầng tiền** `net_tick` (khớp 6 chữ số) ⇒ phép đo hợp lệ.
*(Nguồn điểm: `pred_s1a2x1.parquet` + `pred_ofi_candidate_v2 / pred_baseline_fresh / pred_ofi_noise_v2`
tại `/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/` — **đúng 4 nguồn `entry_rulers.py` đã dùng**; bản `pred_*`
của kernel `ofi-v3-ms-s43/44/45` đã bị DỌN khỏi đĩa sau phiên multiseed (chỉ còn `ms_diffs_s4*.parquet` =
tổng hợp theo tick), nên dùng đúng nguồn cũ để **tái lập được** §2.)*

## 3. MỨC (cut × chỉ số) — điểm

| cut | `k_cut` | đối tượng | `net_tick` | `winrate@top-8` | `pnl_vol_norm` | `TF50` | `asym` |
|---|---|---|---|---|---|---|---|
| 0 % | 0 | S1 | +0,04815 | +0,79251 | +0,10666 | −2549,04 | +3,364 |
| 0 % | 0 | ofi_candidate | +0,05145 | +0,79444 | +0,11312 | −2515,54 | +3,374 |
| 0 % | 0 | ofi_baseline_fresh | +0,04406 | +0,79117 | +0,10295 | −2585,25 | +3,375 |
| 0 % | 0 | ofi_noise | +0,04960 | +0,79207 | +0,10749 | −2531,67 | +3,341 |
| 5 % | 2 | S1 | +0,05854 | +0,78708 | +0,12348 | −2437,94 | +3,157 |
| 5 % | 2 | ofi_candidate | +0,06677 | +0,79133 | +0,13491 | −2359,73 | +3,164 |
| 5 % | 2 | ofi_baseline_fresh | +0,05713 | +0,78721 | +0,12351 | −2444,76 | +3,172 |
| 5 % | 2 | ofi_noise | +0,06578 | +0,79015 | +0,13160 | −2381,40 | +3,152 |
| 10 % | 4 | S1 | +0,06503 | +0,78286 | +0,13416 | −2368,65 | +3,017 |
| 10 % | 4 | ofi_candidate | +0,06737 | +0,78540 | +0,14203 | −2351,92 | +3,044 |
| 10 % | 4 | ofi_baseline_fresh | +0,06367 | +0,78303 | +0,13673 | −2378,97 | +3,033 |
| 10 % | 4 | ofi_noise | +0,07508 | +0,78693 | +0,14761 | −2297,06 | +3,005 |
| 20 % | 7 | S1 | +0,05966 | +0,77565 | +0,13501 | −2413,86 | +2,936 |
| 20 % | 7 | ofi_candidate | +0,06119 | +0,77732 | +0,14029 | −2404,08 | +2,952 |
| 20 % | 7 | ofi_baseline_fresh | +0,06503 | +0,77948 | +0,14224 | −2362,00 | +2,955 |
| 20 % | 7 | ofi_noise | +0,06505 | +0,77934 | +0,14335 | −2371,43 | +2,954 |

## 4. Δ vs mức cắt 0 % — `[CI nới k=12]` · `*` = NGOÀI CI nới

| đối tượng · cut | Δ`net_tick` | Δ`winrate` | Δ`pnl_vol_norm` | Δ`TF50` | Δ`asym` |
|---|---|---|---|---|---|
| S1 · 5 % | +0,0104 [−0,0348,+0,0594] | −0,0054 [−0,0221,+0,0108] | +0,0168 [−0,0300,+0,0650] | +111,1 [−273,5,+513,9] | **−0,207 [`OUT`]** |
| S1 · 10 % | +0,0169 [−0,0529,+0,0900] | −0,0097 [−0,0363,+0,0156] | +0,0275 [−0,0539,+0,1036] | +180,4 [−413,0,+799,8] | **−0,347 [`OUT`]** |
| S1 · 20 % | +0,0115 [−0,0905,+0,1065] | −0,0169 [−0,0546,+0,0179] | +0,0284 [−0,0843,+0,1308] | +135,2 [−726,6,+953,2] | **−0,429 [`OUT`]** |
| ofi_candidate · 5 % | +0,0153 [−0,0304,+0,0676] | −0,0031 [−0,0201,+0,0134] | +0,0218 [−0,0255,+0,0695] | +155,8 [−243,4,+599,0] | **−0,210 [`OUT`]** |
| ofi_candidate · 10 % | +0,0159 [−0,0505,+0,0838] | −0,0090 [−0,0357,+0,0166] | +0,0289 [−0,0466,+0,1009] | +163,6 [−388,6,+738,1] | **−0,330 [`OUT`]** |
| ofi_candidate · 20 % | +0,0097 [−0,0857,+0,1061] | −0,0171 [−0,0520,+0,0168] | +0,0272 [−0,0782,+0,1293] | +111,5 [−703,2,+914,1] | **−0,422 [`OUT`]** |
| ofi_baseline_fresh · 5 % | +0,0131 [−0,0315,+0,0624] | −0,0040 [−0,0207,+0,0123] | +0,0205 [−0,0273,+0,0678] | +140,5 [−232,9,+550,8] | **−0,203 [`OUT`]** |
| ofi_baseline_fresh · 10 % | +0,0196 [−0,0492,+0,0971] | −0,0082 [−0,0333,+0,0175] | +0,0338 [−0,0439,+0,1126] | +206,3 [−355,4,+853,5] | **−0,342 [`OUT`]** |
| ofi_baseline_fresh · 20 % | +0,0210 [−0,0682,+0,1114] | −0,0117 [−0,0449,+0,0212] | +0,0393 [−0,0642,+0,1394] | +223,2 [−521,0,+999,4] | **−0,420 [`OUT`]** |
| ofi_noise · 5 % | +0,0162 [−0,0275,+0,0659] | −0,0019 [−0,0188,+0,0162] | +0,0241 [−0,0241,+0,0744] | +150,3 [−217,0,+548,3] | **−0,190 [`OUT`]** |
| ofi_noise · 10 % | +0,0255 [−0,0433,+0,0966] | −0,0051 [−0,0314,+0,0208] | +0,0401 [−0,0408,+0,1172] | +234,6 [−319,0,+811,3] | **−0,336 [`OUT`]** |
| ofi_noise · 20 % | +0,0155 [−0,0730,+0,1027] | −0,0127 [−0,0449,+0,0204] | +0,0359 [−0,0691,+0,1351] | +160,2 [−606,3,+908,8] | −0,387 [−0,810,+0,024] |

**Không ô `net_tick` / `winrate` / `pnl_vol_norm` / `TF50` nào NGOÀI CI (nới) ở cả 12 ô.** CI thô ⊃ 0 cho
`net_tick`/`TF50` ở mọi ô; `winrate` ngoài CI **thô** chỉ ở `c=20 %` (S1, ofi_candidate) — nới thì chứa 0;
`pnl_vol_norm` ngoài CI **thô** chỉ ở `ofi_candidate@5 %` và `ofi_noise@5 %/10 %` — nới thì chứa 0.
**Ô NGOÀI CI (raw & nới): CHỈ `asym` — 11/12 ô** (trừ `ofi_noise@20 %`), đều **giảm** (đuôi lỗ bớt xấu so với lãi).

## 5. TRẢ LỜI (4 câu bắt buộc)

**(1) Cắt top decile có làm `net_tick` TỐT hơn NGOÀI CI không? → KHÔNG.**
Điểm Δ **dương ở CẢ 12 ô** (+0,0097…+0,0255, tức **+19 %…+51 %** của nền), nhưng **0/12 ô ngoài CI**
(`width_rel 2,5–8,8`) ⇒ **không phân giải được ở tầng này**. Mức: `net_tick` *(0 → 5 → 10 → 20 %)*:
S1 0,0482 → 0,0585 → 0,0650 → 0,0597 · `ofi_candidate` 0,0515 → 0,0668 → 0,0674 → 0,0612 ·
`ofi_baseline_fresh` 0,0441 → 0,0571 → 0,0637 → 0,0650 · `ofi_noise` 0,0496 → 0,0658 → 0,0751 → 0,0651.

**(2) `winrate` / `pnl_vol_norm` tốt hơn hay xấu đi?** — **ngược chiều nhau, cả hai đều KHÔNG phân giải (nới):**
- `winrate@top-8` **XẤU ĐI**: Δ −0,0019…−0,0171; ngoài CI **thô** chỉ ở `c=20 %` (S1, ofi_candidate), nới thì chứa 0.
- `pnl_vol_norm` **TỐT LÊN**: Δ +0,0168…+0,0401; ngoài CI **thô** ở `ofi_candidate@5 %` + `ofi_noise@5/10 %`, nới thì chứa 0.
⇒ Cắt top-decile **đổi hình dạng** (bớt lỗ đuôi: `TF50` tăng, `asym` giảm rõ) nhưng **tỉ lệ thắng giảm**;
không có chỉ số nào vượt CI nới ⇒ **không có "tín hiệu thật" ở tầng entry**.

**(3) Có phải tiếp tục không (theo luật đã chốt §6/PREREG)? → KHÔNG.**
Luật: chỉ coi là **THẬT** nếu **(a)** Δ`net_tick` **ngoài CI (thô & nới `k=12`) theo hướng TỐT**; **(a)** sai ở
**cả 12 ô** (0/12) ⇒ **KHÔNG thoả** ⇒ **không đề xuất chặng Kaggle/sim nào** (tiết kiệm chi phí + rủi ro).
Ghi chú cho MASTER (ngoài luật, không hành động): tín hiệu **phân giải được DUY NHẤT** là **`asym`** (11/12 ô
ngoài CI, đuôi bớt xấu) — nhưng đi **kèm** `winrate` xấu đi và `net_tick` không phân giải ⇒ **không đủ cơ sở**.

**(4) Kết luận dứt khoát:** đây là **NHIỄU ở tầng đo được** (không phân giải), **đúng như cảnh báo
"chưa có ý nghĩa thống kê"** của `RESULT_ENTRY_RULERS` (§0: `top_decile_lift` **0/10 ngoài CI**, `w 2,2–23`).
⇒ **BỎ `top_decile_lift`** khỏi mọi bộ chuẩn, **giữ nguyên đề xuất bộ chuẩn ENTRY 2 thước
`winrate@top-8` + `pnl_vol_norm@top-8`**; **DỪNG** (không sim, không đổi vận hành).

## 6. MỤC BỎ + LÝ DO

- **BỎ `top_decile_lift`** (đuôi-trên S1/OFI): Δ`net_tick` 0/12 ngoài CI; `winrate` không tốt lên; `pvn` không phân giải
  ⇒ không có bằng chứng "thập phân vị trên phản dự báo" **đo được**; giữ lời cảnh báo pre-reg, không đổi vận hành.
- **KHÔNG cắt đuôi-trên ở vận hành** (không có cơ sở ngoài CI) ⇒ **không** chạm production/`242`/ONNX.
- **KHÔNG dùng `pnl_vol_norm` làm thước entry ĐỘC LẬP** (ρ 0,99 với tầng tiền `net_tick` — như `RESULT_ENTRY_RULERS`).
- **`asym`**: ghi nhận là ô ngoài CI duy nhất nhưng **không** vào bộ chuẩn (không phải thước entry; kèm winrate xấu đi).
- **KHÔNG đọc 2026**, KHÔNG chạm `242`/ONNX/LIVE, **KHÔNG push file dữ liệu**.
