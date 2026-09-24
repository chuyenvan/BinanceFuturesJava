# RESULT — S1 RANKING QUALITY (CORRECT MEASURE: đúng horizon + đúng mốc quyết định + đảo dấu)

**Ngày:** 2026-09-17
**Pre-reg:** `docs/prereg/PREREG_S1_RANK_CORRECT_MEASURE.md` (commit `69fb2d1`)
**Script:** `research/analysis/s1_correct_measure.py` (tái sử dụng `trend_rank_ic.py`)
**Trạng thái:** DESCRIPTIVE MEASUREMENT — sửa 2 lệch cấu trúc của `RESULT_S1_RANK_QUALITY.md`
(commit `57223a0`). Chạy MỘT lần, không tune. KHÔNG phải bằng chứng alpha, KHÔNG phải bước tich hop.

---

## 0. ĐỊNH NGHĨA NHÃN `g1lite` (xác minh)

`research/pipeline/ledger.py:40` — **nhãn forward-return 72h có trailing-stop xấp xỉ**:
`g1lite = maxFav_72h - min(0.5*maxFav_72h, 0.08)` nếu `maxFav_72h >= 0.05`, ngược lại
`retEnd_72h`. ⇒ Horizon đúng của S1 = **72h** (KHÔNG phải 1h/4h/24h như lần đo cũ).

## 1. Nguồn + mốc quyết định

- Giá close 1h: `CLOSES_1H.bin` (627 symbol, 2021→2026, 2026 seal loại).
- S1: `pred_s1a2x1.parquet` (`ts,sym,score`, 15-phút, 2022-2025, 620 symbol).
- **Mốc quyết định = `market.bin`** (`/home/ubuntu/simbundle/market.bin`), các ts mà
  `getMarketStatus1M(...) != null` = `rateDownAvg < -0.03157f` (BIG_DOWN, `Configs.java:392`).
- **Coverage: 108 phút quyết định → 59 bucket giờ** trong 2022-2025.

| năm | phút quyết định | bucket giờ |
|---|---|---|
| 2022 | 10 | 7 |
| 2023 | 25 | 18 |
| 2024 | 35 | 23 |
| 2025 | 38 | 11 |

Median **253 coin/bucket**. Map 1-phút → `ctime = ceil(t/1h)*1h`; S1 forward-fill tới ĐÚNG
`t_dec` (không nhìn score phát hành sau mốc).

## 2. QUY ƯỚC DẤU (khóa)

`s1 = -score`; `rank_ic xuôi = Spearman(-score, ret)` (>0 = S1 đúng). `rank_ic ngược =
Spearman(score, ret) = -rank_ic xuôi`. top-8 xuôi = 8 `score` THẤP nhất; top-8 ngược = 8
`score` CAO nhất. CI block-72h (2000 rep, seed 20260905, inflate x1.21).

## 3. Bảng chính — rank_ic xuôi vs ngược (có CI)

n = 59 bucket giờ.

| horizon | rank_ic XUÔI (−score) | CI95 | chứa 0 | rank_ic NGƯỢC (score) | CI95 | chứa 0 |
|---|---|---|---|---|---|---|
| 24h | **+0.0190** | [−0.0333, +0.0664] | CÓ | −0.0190 | [−0.0664, +0.0333] | CÓ |
| 72h (g1lite) | **−0.0192** | [−0.0662, +0.0208] | CÓ | +0.0192 | [−0.0208, +0.0662] | CÓ |

**Cả 4 rank_ic đều có CI CHỨA 0.** rank_ic ngược = −rank_ic xuôi (đảo dấu thuần, đối xứng).
⇒ Ở đúng horizon 72h: **S1 KHÔNG thể hiện năng lực xếp hạng có ý nghĩa thống kê**, dấu hơi âm
(−0.019) nhưng nhiễu. **Đảo dấu KHÔNG ra giá trị dương có ý nghĩa** (+0.019 nhưng CI chứa 0).

## 4. Metric quyết định — top-8 vs universe (xuôi vs ngược)

`diff = mean(ret top-8) − mean(ret universe cung bucket)`.

| horizon | top-8 XUÔI (score thấp) | CI95 | chứa 0 | top-8 NGƯỢC (score cao) | CI95 | chứa 0 | universe mean |
|---|---|---|---|---|---|---|---|
| 24h | **+0.0340%** | [+0.0052%, +0.0738%] | KHÔNG (+) | −0.0066% | [−0.0136%, +0.0008%] | CÓ | −3.96% |
| 72h | **+0.0205%** | [−0.0034%, +0.0464%] | CÓ | **−0.0118%** | [−0.0213%, −0.0026%] | KHÔNG (−) | −1.83% |

- **top-8 XUÔI** (luật hiện tại: chọn score THẤP) **dương ở cả 2 horizon**; 24h có ý nghĩa
  (+3.4 bps/bucket, CI ngoài 0). Ở mốc BIG_DOWN universe đang giảm (mean −3.96%/24h), top-8
  xuôi giảm ÍT hơn.
- **top-8 NGƯỢC** (đảo dấu: chọn score CAO) **âm cả 2**; 72h có ý nghĩa (−1.18 bps, CI ngoài
  0, âm). Chọn 8 coin "tệ nhất" thực sự cho return tệ hơn universe.

## 5. So sánh lần đo cũ (24h, snapshot mỗi giờ)

| 24h | lần cũ (`57223a0`, mọi snapshot 1h) | lần này (mốc quyết định) |
|---|---|---|
| rank_ic xuôi | **−0.0693** (âm, CI ngoài 0) | **+0.0190** (CI chứa 0) |
| top-8 xuôi | +0.1004% (CI chứa 0) | **+0.0340%** (CI ngoài 0, +) |

**Kết luận "reversal" (rank_ic âm) của lần cũ KHÔNG tái lập khi đo đúng mốc + đúng horizon.**
Dấu 24h lật từ −0.069 → +0.019, và top-8 xuôi từ "không edge" → dương có ý nghĩa (nhỏ).

## 6. KẾT LUẬN (theo tiêu chí pre-reg)

1. **"S1 đúng ở horizon của nó (72h)"** = `rank_ic(−score, 72h) > 0` VÀ CI ngoài 0 ⇒
   **KHÔNG ĐẠT** (−0.0192, CI chứa 0). Ở 72h S1 ≈ trung tính, không chứng minh năng lực xếp
   hạng forward-return (cũng KHÔNG còn "reversal" như lần cũ).
2. **Test đảo dấu (post-hoc, multiplicity k=2):** `rank_ic ngược(72h) = +0.0192` nhưng **CI
   CHỨA 0** ⇒ **KHÔNG ra giá trị dương có ý nghĩa**. KHÔNG có bằng chứng "raw score mang thông
   tin nhưng ngược dấu so với luật chọn hiện tại". ⇒ **KHÔNG đề xuất áp dụng đảo dấu.**
3. **Phát hiện lớn (khác dự đoán trước):** kết luận cũ "S1 là reversal" là **artifact của đo
   sai horizon (1/4/24h) + sai mốc (mọi snapshot giờ)**. Đo đúng thì dấu xuôi (score thấp =
   tốt) là **đúng hướng** — top-8 xuôi dương có ý nghĩa ở 24h (+3.4 bps), top-8 ngược âm có ý
   nghĩa ở 72h (−1.18 bps). Nhưng hiệu ứng **rất nhỏ** và rank_ic không đạt ý nghĩa thống kê.

**Tóm lại:** ở đúng horizon + đúng mốc, S1 **xuôi (chiều hiện tại) yếu-hơn-nhiễu nhưng không
sai hướng**; đảo dấu **không** cho giá trị dương. Không có cơ sở đổi luật chọn; cũng không có
cơ sở tuyên bố S1 có alpha xếp hạng 72h.

## 7. Gioi han

1. **Mốc rất ít**: 59 bucket giờ trong 2022-2025; CI block-72h ≈ iid/cluster (thưa, 44 block).
2. **`g1lite` là trailing-stop 72h**, lần này đo proxy `ret_72h` thuần từ close 1h (không tái
   lập công thức trailing; cần đường giá 1m/15m + label file để đo đúng `g1lite`).
3. |IC| rất nhỏ (≤0.02); top-8 diff cỡ bps ⇒ sau phí/slippage gần chắc không còn edge kinh tế.
4. S1 chỉ 2022-2025; 2026 seal ⇒ KHÔNG có forward xác nhận trong lần đo này.
5. KHÔNG sửa `.java`, KHÔNG chạy sim T170, KHÔNG tune. DEV only.
