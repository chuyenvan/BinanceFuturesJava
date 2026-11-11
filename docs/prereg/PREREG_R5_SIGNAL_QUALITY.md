# PREREG R5_SIGNAL_QUALITY — đo chất lượng tín hiệu p15 thô so với các biến thể làm mượt (không gate, không quota, không sim)

Ngày 2026-11-11. Commit TRƯỚC khi tính bất kỳ số nào của R5. Owner đề xuất, MASTER chốt: tách "tín hiệu có nhiều thông tin hơn không" khỏi "luật gate có dùng tốt không".

## 0. Khai báo số đã thấy
- R3 P1 (quota MEAN15 1,70 / MEAN60 1,64 / MTF-OR 1,05 / LATCH 1,37), R3b (MEAN15 quota 2023–25 1,30; MEAN60 1,13), R3_FUTILITY (MEAN60 iso-count ΔCAGR −21…−25 pp, leg −36…−39 %; MTF-OR ΔCAGR −5,6…−8,2 pp), GATE_SMART S4 FALSE, R4 sàng (C1/C2/C3 LOẠI ở quota; mô tả Δfwd72 THÊM−BỚT: C1 −5,6 pp, C2 −6,3 pp, C3 +3,3 pp CI chứa 0).
- Proxy market-level (R2/R4 PHA0, pred DEV): ACF p15 0,955/0,83/0,69 (1′/15′/60′); top-phút mean15/mean60/mean240 trễ 9/34/92′ và chỉ trúng 33/23/10 trên 72 đợt; surprise60 ACF15 0,30, 90 vs 42 đợt; 22,7 % phút top là đỉnh mới 15′.
- Tiên nghiệm: biến thể làm mượt (trễ) KÉM thô; surprise/max có thể ngang. Họ gate đã thử ≥12 biến thể.

## 1. Dữ liệu và chia tập
- p15 theo phút 8 seed: `~/claude_master/res1109/r3_gate/pred/pred_s{42,7,13,21,99,123,777,2024}.bin` (pred n4f-b0).
- Phút xét = phút có ứng viên trong `gate_offline` (`cand_base.npz`, có p15). Năm theo +07.
- KHÁM PHÁ: 2022-01-01 → 2024-01-01. XÁC NHẬN: 2024-01-01 → 2026-01-01. HO 2026 KHÔNG đụng.

## 2. Kết cục Y(t)
- Rổ(t) = top-24 theo sp tại phút t (hàng `SY15[fi]` cột 0..23 của `cand_base.npz`, bỏ cột sp NaN) — TRƯỚC khi loại coin đang giữ (coin giữ phụ thuộc đường đi). Giống nhau cho mọi seed.
- ret_H(coin, t) = close(t+1′+H)/close(t+1′) − 1 − 0,002; giá = bản ghi kline1m cuối ≤ mốc, cách ≤5′ (như `s4k.py`/r4s-fwd), nguồn `vz-kline1m-2022..2026`.
- Y_H(t) = trung bình đều ret_H trên các coin của rổ có giá; cần ≥12 coin, thiếu ⇒ Y NaN (phút bị bỏ khỏi trung bình, KHÔNG bỏ khỏi xếp hạng). H = 72h (chính), 24h (phụ).
- Tính Y cho MỌI phút xét 2022–2025 (không lấy mẫu): 1 kernel Kaggle `r5q-fwd`, `enable_internet=false`, vector hoá theo tháng.

## 3. Thư viện 12 biến thể (causal, cửa sổ theo thời gian thật, độ phủ ≥80 % cửa sổ, thiếu ⇒ NaN = không đủ điều kiện xếp hạng)
| # | tên | định nghĩa tại phút t |
|---|---|---|
| 1 | RAW | p15(t) |
| 2–5 | MEAN5/15/60/240 | TB p15 trên [t−W+1′, t], cần ≥4/12/48/192 giá trị |
| 6–8 | EWMA5/15/60 | EWMA half-life 5/15/60 phút trên chuỗi phút (pandas `ewm(halflife=h, adjust=True, ignore_na=True)`), khởi tạo từ đầu chuỗi pred |
| 9 | MED15 | trung vị [t−14′, t], ≥12 |
| 10 | MAX15 | max [t−14′, t], ≥12 |
| 11 | MIN15 | min [t−14′, t], ≥12 (độ bền) |
| 12 | SUR60 | p15(t) − TB [t−60′, t−1′], ≥48 |
Không thêm biến thể sau khi thấy số.

## 4. Chỉ số chính
- K(seed, giai đoạn) = số phút B0 pass (gate_offline `run_g2`, ≥1 ô pass) của seed đó trong giai đoạn (iso-count cấp phút).
- Với mỗi seed, biến thể: lấy top-K phút theo giá trị biến thể trong giai đoạn (giảm dần).
  - (a) không khử cụm: TB Y72 trên top-K phút.
  - (b) khử cụm (CHÍNH): sắp top-K theo thời gian, phút cách nhau ≤60′ gộp một đợt, lấy phút ĐẦU mỗi đợt; TB Y72 trên các phút đầu đợt.
- Gộp 8 seed: thống kê = TB 8 seed của TB theo seed. Hiệu (biến thể − RAW) = TB 8 seed của hiệu theo seed.
- CI: bootstrap cụm NGÀY (+07) trên mọi ngày của giai đoạn, 2 000 lần, rng seed 20261112; cùng bộ trọng số ngày cho mọi seed/biến thể; trong mỗi lần, TB theo seed = Σ w_d·ΣY_d / Σ w_d·n_d.

## 5. Chỉ số phụ (mô tả)
- Lift theo K × {0,25; 0,5; 1; 2; 4} cho (a) và (b).
- Spearman(biến thể, Y72) toàn mẫu phút và trong top 5 % phút của biến thể (median 8 seed).
- Độ trễ: với mỗi đợt (b) của RAW (phút đầu s), phút đầu tiên trong top-K của biến thể thuộc [s−60′, s+240′]; báo trung vị (phút) và tỉ lệ đợt RAW bắt được.
- Y24 cho chỉ số chính.

## 6. Luật quyết định
- KHÁM PHÁ (2022–23): chọn tối đa 2 biến thể (≠ RAW) có chỉ số (b) cao nhất VÀ (b) > RAW (điểm). Không có ⇒ ĐÓNG ngay, không chạy xác nhận.
- GHI + COMMIT lựa chọn TRƯỚC khi tính bất kỳ số nào trên 2024–25.
- XÁC NHẬN (2024–25): biến thể ĐẠT ⇔ cận dưới CI90 (phân vị 5 %) của (biến thể − RAW) theo (b) > 0 VÀ hiệu điểm (b) > 0 riêng năm 2024 và riêng năm 2025 (K = số phút B0 pass của từng năm).
- Không biến thể nào ĐẠT ⇒ kết luận "p15 thô đã là cách dùng tốt nhất trong thư viện này", ĐÓNG. Có ⇒ MASTER viết prereg Pha 2 (luật gate với ngưỡng cập nhật theo phút).
- Không đổi luật/tham số sau khi thấy số; lỗi code ⇒ addendum, chạy lại toàn bộ.

## 7. Thực thi
- Oracle (`flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10`, đĩa ≥15 GB, RAM ≥4 GB): `research/r5_quality/r5_signal.py` (biến thể + K + bảng rổ cho kernel). Kaggle 1 kernel `r5q-fwd` (dataset `r5q-basket`). Chấm `r5_score.py discover|confirm`. Vòng tự chờ `r5_loop.sh` có file STOP + log; thứ tự: tín hiệu → kernel → khám phá → commit lựa chọn → xác nhận → commit.
