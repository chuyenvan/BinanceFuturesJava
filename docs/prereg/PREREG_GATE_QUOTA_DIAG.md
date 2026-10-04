# PREREG — GATE_QUOTA_DIAG (Pha D chương trình GATE) — chốt TRƯỚC khi đo

- **Ngày:** 2026-10-04. **Loại:** chẩn đoán offline (Python), 0 Java/sim/Kaggle, 0 PnL mới, DEV ≤ 2025-12-31.
- **Script:** `research/analysis/gate_offline.py` (commit cùng file này, trước khi chạy stage `all`).
- **Dữ liệu:** pred.bin 8 seed (A1=42 `~/wfo_ds_x1_2021/pred.bin`; S7 `gabl/ds_SEED7`; S13/S21/S99/S123/S777/S2024 `gsb/pred_S*`), bins S1 `~/predwf_map_s1a2_x1_2021` (horizonIdx=0, = manifest dataset sim), lưới phút `market.bin`, printDone 8 run (`n700-a1`, `gabl-seed7`, `gsb-s*`), log `[GATE-RATIO]` mỗi run.

## Cơ chế tái lập (đọc code, không suy đoán)
Ứng viên = top-24 sp tăng (bins 15' forward-fill ≤15' ra mọi phút market), bỏ coin đang giữ TRƯỚC gate, cần p15 ở phút đó; `r = p15/(max(0.26787, sp/0.15·1.2876)·1.55)` float32; q_h = phân vị nearest-rank `floor(pct·(m−1))` của r trong [h−90d, h), tính ở truy vấn đầu mỗi giờ; warm-up 7 ngày → q = 0.008; PASS ⇔ !(p15 < (q·factor)·gs). Sau warm-up **không có sàn tuyệt đối 0.008** cho nhánh PREDICT. K-cap và held áp **trước** gate ⇒ không thể có "pass nhưng vượt K24/held" trong sim; lãng phí đo được = pass nhưng không vào lệnh (budget/khác).
**Xấp xỉ khai trước:** held lấy từ printDone của chính run (PREDICT khoá (start,end); level khác [start,end)); `isTickerAvailable` không tái lập; tie sp lexsort ổn định.

## D1 — cổng validate (chốt): arm A1, S21, S777
- recall phút = |phút vào PREDICT thật 2022–25 ∩ phút gate-mở offline| / |phút vào| **≥ 0,95**;
- mỗi năm 2022–25: |phút gate-mở offline / phút vào sim − 1| **≤ 0,10**.
- Phụ (báo, không là cổng): seen/pass theo quý offline vs log `[GATE-RATIO]`; sai lệch sp/p15 tại lệnh.
- Trượt ⇒ ghi nguyên nhân, báo MASTER, vẫn nộp D2–D4 kèm nhãn "chưa validate".

## D2 — lãng phí quota (mỗi seed × năm)
symbol-phút pass; phút riêng biệt; symbol-phút/phút (mean/p50/p90/max); entered = pass khớp lệnh PREDICT thật (phút+symbol); lãng phí = pass − entered; tỷ lệ; held-would-pass (thông tin, không tốn quota). Tương quan Pearson+Spearman (n=8) với CAGR22 (RESULT_GATE_SEEDBAND): phút riêng biệt 2022, lãng phí 2022 (+ pass, symbol-phút/phút). Kết luận "giải thích được" nếu |pearson| ≥ 0,7 cùng dấu kỳ vọng; n=8 ⇒ chỉ là chỉ báo.

## D3 — dyn(sp)
Pass rate theo decile sp (biên decile = ô hợp lệ A1 2022–25 sau warm-up) + theo nhóm rank; ROI lệnh thật A1 (profit % margin, pnl) theo decile sp quần thể và theo quintile trong lệnh; Spearman(sp, ROI); theo năm nửa thấp/cao.

## D4 — 3 cơ chế quota thay thế (CHỈ ĐẾM, không PnL, không tune)
- **(a)** quota theo PHÚT trên p15 (market-level, không sp): mở phút t ⇔ p15_t ≥ q_h(ρ_a), q_h = phân vị (1−ρ_a) của p15 các phút có ứng viên trong [h−90d, h), mỗi giờ. Symbol được nhận = mọi ứng viên hợp lệ (≤ K24).
- **(b)** quota theo PHÚT trên r_max(t) = max r của ứng viên hợp lệ (mỗi phút tốn 1 đơn vị quota bất kể bao nhiêu symbol qua ⇒ "trả quota dư"); mở ⇔ r_max ≥ q_h(ρ_b); symbol nhận = ứng viên có r ≥ q_h (≤ K24).
- **(c)** như G2 (symbol-phút, pct 0,99995083 cố định) nhưng cửa sổ 365d.
- **Hiệu chỉnh (khai):** ρ_a, ρ_b chọn bằng bisection log-ρ ∈ [1e-5, 2e-3] **chỉ trên A1** sao cho số phút mở 2022–25 = số phút vào PREDICT thật của A1 2022–25 (≈146,5/năm); áp nguyên ρ cho 7 seed còn lại. (c) không hiệu chỉnh. Held = printDone của từng seed (xấp xỉ).
- **Chỉ số:** phút mở/năm theo seed (2022: mean, sd, CV), tổng 2022–25, Jaccard phút 2022–25 và 2022 (TB 28 cặp), symbol-phút/phút. So với G2 offline (90d) và SIM (phút vào thật).
- **Tiêu chí (chốt):** cơ chế "ổn định hơn" ⇔ CV phút-mở-2022 qua 8 seed < CV của G2off **và** Jaccard 2022–25 TB > G2off; "không đổi tổng quota" ⇔ TB phút mở 2022–25 trong ±10% của A1 SIM. Không chọn deploy; chỉ đề xuất vòng Java có pre-reg riêng.
