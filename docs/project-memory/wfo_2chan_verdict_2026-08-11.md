# VERDICT 2 CHÂN + NET_THR sweep (per-quarter) — 2026-08-11 (FINAL v2, đã sửa)

> Selector leak-free (unfiltered **15m grid**, FIRST_CUTOFF=2023, HORIZONS=4h, XGBoost), sim engine **tick 1m**
> (pred snapshot refresh mỗi 15m, forward-fill). build_ds Oracle → fanout Kaggle-fleet (5 worker),
> jobstore Aerospike Oracle-local ns=test (BỎ 226). Frozen loose_k8 (DCA-on, verified worker GENOME 21 gene
> dcaGrid=true givebackFloor=true). 12 window 2023Q1–2025Q4, WFO_MAX_OOS_DATE=20260101.

## 0. NET_THR "0.008/0.02" nghĩa là gì
NET_THR = ngưỡng lợi nhuận ròng close-to-close trong horizon 4h dùng để **gán nhãn train selector**:
`y = 1 (đáng vào) nếu retEnd_4h > NET_THR`. 0.008 = "coin sẽ lãi ròng > 0.8%/4h"; 0.02 = "> 2.0%/4h".
NET_THR cao → định nghĩa "coin tốt" khắt khe → model chỉ học pick coin kỳ vọng bật MẠNH → ít nhãn dương, vào ít lệnh, kén coin biến động lớn.

## 1. Sweep per-QUARTER (12w, OOS PnL) — số THẬT từ sweep/DONE_*.txt
| Quý | 0.005 | 0.008 | 0.012 | 0.02 |
|---|---:|---:|---:|---:|
| 2023Q1 | 156 | 199 | 343 | 600 |
| 2023Q2 | 414 | 997 | −68 | 714 |
| 2023Q3 | 12 | 309 | 226 | 936 |
| 2023Q4 | 683 | 810 | 761 | 1052 |
| 2024Q1 | 1898 | 2593 | 2541 | 3375 |
| 2024Q2 | 183 | −30 | 1208 | 153 |
| 2024Q3 | 1239 | 1316 | 1328 | 2014 |
| 2024Q4 | 1247 | 1363 | 1201 | 2272 |
| **2025Q1 (crash)** | **+1134** | **+1397** | **−2755** | **−1469** |
| 2025Q2 | 297 | 418 | 728 | 1479 |
| 2025Q3 | −92 | −129 | 80 | −605 |
| 2025Q4 | 2737 | 1698 | 3121 | 1219 |
| **TỔNG 12w** | **+9,908** | **+10,942** | **+8,714** | **+11,738** |
| Σ2023 | 1,265 | 2,315 | 1,262 | 3,301 |
| Σ2024 (bull) | 4,567 | 5,242 | 6,277 | **7,813** |
| Σ2025 | **4,076** | **3,384** | 1,175 | **624** |
| posRatio lenient | **69%** | 63% | 63% | 63% |

## 2. PHÁT HIỆN CHÍNH — tăng NET_THR = đuổi cú bật lớn = ăn bull, chết crash (đơn điệu)
- Σ2024 (bull) **tăng đơn điệu** theo NET_THR: 4,567→5,242→6,277→7,813.
- Σ2025 **giảm đơn điệu**: 4,076→3,384→1,175→624. **2025Q1 (crash) LẬT ÂM ở ngưỡng ≥0.012** (+1134/+1397 → −2755/−1469).
- ⇒ **0.02 tổng cao nhất (+11,738) CHỈ vì dồn 2024 bull (67% tổng)**, và **hy sinh đúng cái ta cần**: sống qua downtrend.
  Đúng linh cảm Uni: 0.02 "dồn 1 giai đoạn" (2024). Cú "≥2%" trong crash toàn bẫy reverse → vào là lỗ.

## 3. KHUYẾN NGHỊ (SỬA lại "0.02 best" hôm qua — SAI)
- Mục tiêu của việc đổi label net = **sống qua downtrend**. Theo tiêu chí đó, **band robust = 0.005–0.008**, KHÔNG phải 0.02/0.012.
- **0.005**: robust nhất (posRatio 69%, 2025 đều nhất +4,076, crash +1134, chỉ 1 window âm nhỏ). Tổng thấp hơn 0.008 ~1k.
- **0.008**: cân bằng tốt (tổng +10,942, crash +1397, 2025 +3,384). Ứng viên deploy mặc định.
- 0.02 = "đẹp trên giấy" nhưng là bull-chaser, bỏ.
- Tất cả net vẫn thắng maxFav (−7,030) và không cái nào sập kiểu maxFav (2025Q1 maxFav −11,255).

## 4. Đối chiếu concentration vs baseline
- ret2 cũ +14,225: dồn **2025Q4 +4,646 = 33%** (đúng quý thanh lý $19B Oct-2025).
- net@0.008: quý lớn nhất 24Q1 +2,593 = 24%, rải đều 3 năm. net@0.005 còn đều hơn (2025 +4,076).
- ⇒ net (band thấp) kiếm ĐỀU, không phụ thuộc 1 sự kiện hiếm → đáng tin hơn dù tổng thấp hơn.

## 5. CAVEAT đo lường (đọc trước khi tin report md trực tiếp)
- File `docs/reports/wfo_strategy_window.md` trên Oracle bị một lần `report` sau đó GHI ĐÈ → hiện KHÔNG phải run t02
  (win15=9801/1652 lệnh là số lạc). **Số per-window đúng nằm ở `sweep/DONE_*.txt`** (drive_tag parse ngay lúc mỗi tag xong).
- **CHƯA lấy được trades/window (độ phủ lệnh) của các chân net** vì report md đã bị đè. Cần regen report đúng WFO_DATA_DIR để có.

## 6. 15m vs 1m (Uni chốt hướng: pred+wfo lại ở 1m)
- 2 lưới khác nhau: (a) lưới TRAIN/label selector; (b) lưới PRED (tần suất selector đổi quyết định). Sim đã tick 1m.
- Hiện tại (a)=(b)=15m. "627M" = train UNFILTERED ở 1m → OOM (đã đụng, có thật, không chỉ là "lọc feature").
- Muốn pred+wfo ở 1m mà GIỮ unfiltered: phải **tách 2 lưới** (train stride 15m, predict stride 1m) — cần sửa gen script + ~15× disk/compute cho predict_wf 1m.
- ⛔ **Blocker disk**: Oracle 7.6G free; predict_wf 1m ≈ ~15G + dataset build lớn → KHÔNG chứa nổi trên Oracle. Cần build trên Kaggle / thêm disk / dọn.
- wfo_ds_net_t02 (4.4G) + predwf_net_t02 (1006M) còn trên Oracle — có thể dọn để lấy ~5.4G nếu chốt bỏ nhánh 0.02.
