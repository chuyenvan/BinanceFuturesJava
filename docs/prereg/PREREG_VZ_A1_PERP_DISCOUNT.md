# PRE-REG (khám phá) — A1 "perp discount / perp-led flush" tại tick vào đợt (MASTER 2026-10-16)

Nền: `docs/result/MASTER_REVIEW_1016.md` §2, §5.3 và `docs/result/BURST_RISK_1016.md`.
- Câu hỏi đúng tầng là "đợt nào xấu?", đo trên quyết định của hệ, không đo trên sự kiện thô.
- E1-T5 đã đo basis trên sự kiện thô (đóng). R2 (bookDepth) chỉ có dữ liệu từ 2023, n = 44 đợt, không ra ứng viên.
- File này commit TRƯỚC khi tải dữ liệu hay tính outcome. Đây là KHÁM PHÁ, không phải GO.

## Giả thuyết cơ chế (chốt dấu trước)

Hệ mua đáy theo đợt.

- **Đợt tốt:** cú sập do thanh lý đòn bẩy trên perp. Perp bị bán ép, giá rơi xuống dưới index spot (premium âm sâu). Spot rơi ít hơn perp. Sau đó giá hồi.
- **Đợt xấu:** sụp đổ cơ bản, kiểu LUNA 2022-05 hay FTX 2022-11. Bên bán dẫn đầu là spot nên spot rơi bằng hoặc hơn perp. Premium không âm sâu, và giá không hồi.

Dự kiến dấu:
- Premium càng âm so với nền 24h ⇒ ret càng tốt.
- Perp rơi càng nhiều hơn spot ⇒ ret càng tốt.

## Dữ liệu

- **Chân lệnh:** từ printDone của sim `gqsf-a1` (K24 + skipFull, `~/kaggle_sim/out/gqsf-a1/storage/printDone.csv`).
  - Cột `start` theo giờ GMT+7, đổi sang UTC.
  - Bỏ chân `level = DCA_LEVEL1`, vì đó là lệnh nhồi, không phải quyết định vào lệnh.
  - Một "đợt" là các chân cùng phút `start`. Chỉ giữ đợt có ≥ 6 chân.
  - Một seed (A1). Báo kèm seed s7 và s21 làm độ bền (mô tả, không chấm).
- **Năm khám phá:** 2022 và 2024 (UTC).
  - Lý do chọn: đủ power, và có các cú sụp đổ hệ thống (LUNA, FTX). Không có các cú này thì giả thuyết không đo được.
  - Năm 2021, 2023, 2025 để dành cho bước xác nhận DEV. **Không tính outcome trên các năm này trong lần chạy này.**
- **Lake Vision**, đọc trên Kaggle kernel (dataset attach, không tải về Oracle):
  - `vz-basis1m-{2022,2024}`: các cột `ts, sym, prem_close, mark_close, index_close`.
  - `vz-kline1m-{2022,2024}`: các cột `ts, sym, open, high, low, close`.
- **Nến quyết định b:** nến có open time = t0 (= `start` UTC), đóng lúc t0 + 60 s. Mọi feature chỉ dùng nến có open time ≤ t0.

## Feature (cố định)

- **F1 `prem_dis`** = prem_close[b] − trung vị prem_close trên các nến [t0 − 1440′, t0 − 60′].
  - Cần ≥ 600 nến có dữ liệu, nếu không thì NaN.
  - Dấu cơ chế: F1 âm ⇒ ret tốt hơn, tức IC < 0.
- **F2 `perp_lead60`** = (close[b] / close[b − 60′] − 1) − (index_close[b] / index_close[b − 60′] − 1).
  - Dấu cơ chế: F2 âm (perp rơi nhiều hơn spot) ⇒ ret tốt hơn, tức IC < 0.
- **Feature của đợt** = trung vị feature trên các chân có giá trị.

## Outcome

- Chân: `ret = pnl / margin` (giữ tới khi thoát, đã gồm phí và funding theo sim).
- Đợt: Σpnl / Σmargin.

## Phép thử (4, ledger 54 → 58)

| | Loại | Thước đo |
|---|---|---|
| T1 | Veto đợt | Spearman(F1 đợt, ret đợt), tính qua các đợt |
| T2 | Veto đợt | Spearman(F2 đợt, ret đợt) |
| T3 | Chọn trong đợt | Trung bình qua đợt của Spearman(F1 chân, ret chân). Chỉ tính đợt có ≥ 6 chân có feature |
| T4 | Chọn trong đợt | Như T3, với F2 |

- CI dùng block bootstrap theo ngày UTC: block 5 ngày, NREP 2000, seed 20261016. Các đợt cùng ngày luôn đi cùng nhau.
- Báo kèm:
  - CI Bonferroni với k = 4 (hai phía 98,75 %);
  - dấu tách riêng từng năm 2022 và 2024;
  - spread ret giữa nửa trên và nửa dưới của feature (với T1/T2: chia đợt theo trung vị; với T3/T4: chia trong từng đợt).
- **Ứng viên** khi đồng thời:
  1. CI Bonferroni không chứa 0;
  2. dấu đúng cơ chế (IC < 0);
  3. cùng dấu ở cả 2022 và 2024.
- Nếu chỉ CI95 thường không chứa 0 thì ghi là "tín hiệu yếu", **không** đưa đi xác nhận.
- Ngược dấu thì ghi nhận, không theo đuổi.
- Mô tả thêm (không chấm): F1 và F2 của 10 đợt tệ nhất DEV trong 2022/2024, kèm thứ hạng của chúng.

## Xác nhận (khai luôn bây giờ; chỉ chạy nếu có ứng viên)

1. Cùng thống kê, cùng dấu, trên DEV 2021 + 2023 + 2025: một phía 95 %, CI không chứa 0.
2. Nếu bước 1 đạt: HO 2026 (sim `ho4-k24-*` trên Vision 2026) và backcast 2020 (niêm phong). Hai bước này chỉ báo cáo, vì n nhỏ.
3. Đổi thành luật giao dịch (ví dụ veto đợt khi F2 > ngưỡng) cần pre-reg riêng kèm sim 8 seed. Không chọn ngưỡng trong file này.

## Kiểm dữ liệu (bắt buộc trước khi tính outcome)

- **V1 causal:** mọi nến dùng có open time ≤ t0.
- **V2 khớp giá:** giá `entry` trong printDone nằm trong [low · 0,998; high · 1,002] của nến b hoặc b + 1 ở ≥ 95 % số chân.
- **V3 ngữ nghĩa:** trên các nến của chân, corr((mark_close − index_close) / index_close, prem_close) ≥ 0,8. FAIL thì dừng và chẩn đoán, không đổi feature.
- **V4 phủ:** ≥ 90 % số chân có cả F1 và F2. Báo danh sách symbol thiếu.
- **Map symbol:** printDone ghi `GRASS`, lake dùng `sym`. Thử thêm hậu tố `USDT` nếu tên gốc không có. Báo tỉ lệ map được.

## Quy trình

1. Kernel Kaggle (CPU) chỉ xuất feature theo chân `(sym, t0, F1, F2, V2, V3)`. Kernel không đọc pnl.
2. Ghép outcome trên Oracle bằng `research/vz/a1/a1_test.py`.
3. Kết quả ghi `docs/result/VZ_A1_PERP_DISCOUNT_EXPLORE.md` + json, kèm cập nhật ledger.
