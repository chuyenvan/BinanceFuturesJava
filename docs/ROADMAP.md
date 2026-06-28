# ROADMAP.md — Lộ trình kiểm chứng & cải tiến mô hình

> **Quan hệ:** đây là LỘ TRÌNH CHA (6 bước). Chi tiết rebuild model (bước 1) → `REBUILD_ROADMAP.md`. Vận hành định kỳ → `PIPELINE.md` (cadence 3 tháng). Số đo/kết luận → `FINDINGS.md`.

Mục tiêu xuyên suốt: **chứng minh bằng số liệu rằng mô hình có edge thật và sống sót qua cú sập, TRƯỚC khi tối ưu thêm hoặc bật tiền thật.** Làm đúng thứ tự — mỗi bước gác cổng cho bước sau. Không nhảy cóc.

Bối cảnh chiến lược (để mọi quyết định bám vào): đây là bot **long-only, leverage 1, martingale/DCA, không hard stop-loss**. Lớp AI lọc entry; P&L thực tế bị chi phối bởi động lực hồi phục của DCA. Hệ quả: backtest có thiên hướng tâng bốc loại chiến lược này; win rate luôn cao giả tạo; rủi ro nằm ở ĐUÔI (cú sập hiếm), không ở tần suất thắng.

---

## ✅ Bước 0 — Bịt look-ahead & slippage (ĐÃ LÀM, đang là rule)
- `OrderTargetInfoTest.updateStatusNew`: tách đặt-SL khỏi khớp-lệnh, cấm khớp nội-nến (`BLOCK_INTRABAR_LOOKAHEAD`).
- `calTp`: trừ slippage 2 chân (`SLIPPAGE_RATE`, `APPLY_SLIPPAGE`).
- `BacktestIntegrityGuard.assertProductionGrade()` cắm ở **dòng đầu `simulatorWithInitEntry`** (xác minh qua AUDIT/ADR-0002 — KHÔNG phải `BackTestEngineMaster.run`) — tự chặn nếu chạy backtest với look-ahead/slippage/fee tắt.
- **Việc còn lại:** chạy đối chứng (guard bật vs tắt) để đo "ảo giác look-ahead". Nếu PnL sụp khi bật guard → cấu hình cũ chưa từng có lãi thật → **mọi tham số HPO cũ phải bỏ, chạy lại từ đầu.** Bump `CONFIG_VERSION`.

## Bước 1 — Đo chất lượng MODEL độc lập (rẻ nhất, gác cổng mọi thứ)
Câu hỏi: model AI có tín hiệu thật không, hay chỉ khớp dữ liệu train?
- **Chặn trước:** model hiện train trên CẢ 5 năm + có 2 lỗi leak (scaler fit toàn bộ; funding model dùng `train_test_split` random/stratify). ⇒ không có dữ liệu out-of-sample để đo trung thực.
- **Phải làm:** re-train ĐÚNG CÁCH — cắt theo thời gian, scaler fit chỉ trên train, **giữ lại đoạn cuối (vd 6–12 tháng) model TUYỆT ĐỐI không thấy** làm holdout.
- **Đo trên holdout:** ghép `(predicted_15m/24h, realized)` theo `(symbol, time)`, điểm cách nhau ≥ horizon để độc lập, chỉ lấy điểm SAU cutoff train. Tính **IC (Spearman predicted-vs-realized)** và **hit-rate có điều kiện** (trong các lần predicted vượt ngưỡng PASS, % realized cùng dấu), TÁCH THEO REGIME (tăng/sập/đi ngang).
- **Phán quyết:** IC dương & ổn định theo tuần → model có edge, đi tiếp. IC ~ 0 → model rỗng, dừng và build lại model (đổi feature/target/label), mọi HPO phía sau vô nghĩa.
- Tiền đề: feature export phải còn TRỤC THỜI GIAN (timestamp hoặc file sắp theo thời gian). Nếu mất → sửa từ bước export, không sửa được ở train.

## Bước 2 — Ablation: edge đến từ AI hay từ DCA?
> ✅ **PASS (2026-06-23, commit a043317):** `EdgeAttributionReport` cũ KHÔNG tồn tại → dựng mới `AblationStep2Tool`
> (Configs.ABLATION_MODE A/B/C). FULL 2021-2026:
> - A (AI bật):  trades 70711, PnL **+69217**, maxDD 20383, avgMAE **3.36%**, Calmar **3.40**
> - B (no-AI):   trades 56416, PnL **−13703**, avgMAE 6.01%, Calmar −0.45
> - C (placebo): trades 42683, PnL **−10778**, avgMAE 5.10%, Calmar −0.36
> → A MAE nông hơn + Calmar cao hơn placebo C (cùng passRate) ⇒ **AI CÓ EDGE THẬT**. B/C đều LỖ ⇒ DCA một mình
> không cõng nổi; lãi đến từ chất lượng chọn lọc của AI. Đủ điều kiện vào Bước 4.
- Chạy 3 bản cùng mọi thứ, chỉ khác entry: **A=AI bật (control)**, **B=tắt filter AI (mọi tín hiệu PASS)**, **C=entry ngẫu nhiên cùng số lệnh (placebo)**.
- So ở mức LEG ĐẦU, không phải cụm: `firstLegWorstMAE`, `firstLegAvgMAE`, `dcaRescueRate`, `firstLegTotalPnl`.
- **Phán quyết:** AI có edge ⇔ A có MAE nông hơn / rescueRate thấp hơn / first-leg PnL đỡ âm hơn C, ở cùng số vị thế. A≈C (chỉ khác win rate cụm) → AI vô dụng, DCA cõng hết.
- Chạy trên NHIỀU regime (bot long-only tự đẹp trong uptrend → chạy mỗi 1 cửa sổ sẽ kết luận sai).

## Bước 3 — Mô hình hóa "cái chết" trong sim + sửa tư thế rủi ro
> ▶️ **ĐANG LÀM (quay lại 2026-06-28): GÁC Bước 4 (WFO) + framework master-worker.** Lý do: đổ công vào
> tầng tối ưu tham số (WFO/HPO/sensitivity) khi nút thắt kết cấu (DCA-không-giới-hạn + concentration) còn hoãn
> = xếp ghế trên tàu thủng đáy. FINDINGS §5 chẩn đoán thủ phạm rõ ràng ở Bước 3, nên vào thẳng.
> **Tiến độ:** (1) ADR-0008 chốt cap-vs-avgEntry VÔ HIỆU CẤU TRÚC → định nghĩa lại cap theo MỐC CỐ ĐỊNH.
> (2) LunaDcaScenario chứng minh (1 coin): maxCap %vốn/cụm cứu ruin 79%→5-10%; cap cũ veto 4927 lần vẫn mất 79%.
> (3) Gắn `DCA_CAP_MAX_CAPITAL_RATIO` vào engine thật (createOrderBUY), RunDcaCapBacktest đo tác động tổng 5 năm
> (câu hỏi FINDINGS §8: cap biến PnL ÂM→DƯƠNG?). Còn lại: funding cost + margin-call/equity thật.
> **GIỚI HẠN khi đọc lại WFO sau này:** chưa có margin-call thật nên maxDD có thể HIỂU NHẸ.

Để backtest ĐƯỢC PHÉP sụp thì fitness mới trung thực.
- Thêm: margin call / cháy tài khoản (sizing theo equity thật, không phải `balanceBasic` cố định); funding cho lệnh kẹt lâu (`updateFundingFee` đang comment hết); slippage đã có ở Bước 0.
- Sửa tư thế pro-cyclical: đặt **trần tuyệt đối** cho tổng margin / số lần DCA mỗi symbol, đặc biệt trong `BIG_DOWN` (đang `isAll=true` không trần).
- Calibrate chi phí từ log product thật khi có (slippage/fee thực) rồi nạp ngược vào sim.

## Bước 4 — Walk-Forward (WFO) thay cho in-sample tuning
Chỉ làm khi Bước 1–2 PASS.
- Trước hết **giảm gene** bằng sensitivity analysis: quét từng gene, fix cứng gene nào fitness phẳng (nghi ngờ: nhóm `AI_DYNAMIC_*`). **13 → ~8** (genome hiện 13 gene, đã bỏ `MIN_MOMENTUM_24H` — xem ADR-0003). Rồi tối ưu THEO NHÓM tuần tự (market-status → AI → DCA), khóa dần.
- WFO rolling: **train = OOS-test = bước trượt = đúng nhịp re-fit thật của bot.** Với 5 năm: 12/2/2 (~24 cửa sổ). Với 1 năm: 6/1/1 (~6 cửa sổ).
- **Bước trượt PHẢI bằng độ dài OOS** (các đoạn OOS không chồng lấn) — trượt 1 ngày với OOS dài là ảo giác bằng chứng, không độc lập.
- Tiêu chí PASS bằng SỐ, chốt TRƯỚC khi nhìn (không chọn bằng cảm quan): **WFE = PnL_OOS/PnL_IS** (≥0.5 tốt, <0.3 overfit), % cửa sổ OOS dương (≥70%), độ ổn định gene qua các cửa sổ, profitFactor OOS, worst OOS drawdown.
- **Output của WFO KHÔNG phải 1 bộ tham số** mà là PHÁN QUYẾT "pipeline có generalize không". Mỗi cửa sổ ra 1 bộ tham số riêng dùng 1 lần. Nếu PASS → bộ tham số deploy được sinh ở PHA RIÊNG: HPO lần cuối trên dữ liệu gần nhất (đúng độ dài cửa sổ train).
- ⚡ **Tăng tốc generate cho WFO — [TASK-108](../tasks/108-generate-selector-predict-only.md):** mỗi vòng WFO train lại model → phải generate lại set selector predictions. Generate hiện tại vừa extractFeatures vừa predict (~8h full 2021→2026, extract ~95% thời gian). Vì feature đã export sẵn (ff_*.bin) và đã validate khớp generate 45/45 (TASK-109), nên tách đường **predict-only** (đọc ff + chỉ chạy ONNX, bỏ extract) để generate nhanh hơn nhiều lần. LÀM TRƯỚC khi chạy WFO nhiều vòng. (Kaggle 5-CPU KHÔNG hợp cho generate đọc-226-per-ngày: latency mạng Kaggle→226 ~11x Oracle — đo TASK-109; predict-only đọc ff local mới mở được đường Kaggle nếu cần.)

## Bước 5 — Hợp nhất một-bộ-não sim/product
- Rút `EntryDecisionCore.decide(...)` thuần: nhận input đã chuẩn hóa, trả `CREATE/SKIP` + budget. `createOrderBUY` (sim) và `createOrderBuyRequest` (product) chỉ gom input theo môi trường rồi gọi chung hàm này.
- 4 điểm lệch phải thống nhất khi gom: (a) thứ tự cổng AI vs circuit; (b) sim bỏ qua AI trong BIG_DOWN còn product không; (c) ngưỡng budget tối thiểu (`<5` ở product, không có ở sim) → đưa thành `Configs.MIN_BUDGET_PER_ORDER` dùng chung; (d) nguồn predict (sim đọc map vs product ONNX realtime) → đảm bảo cùng giá trị qua cổng consistency.
- Golden test: cùng chuỗi input → cả hai đường ra cùng quyết định.

## Vận hành về sau (sau khi deploy)
- **Tham số HPO:** re-fit định kỳ theo nhịp WFO đã chứng minh (vd mỗi 2 tháng).
- **Model AI:** cập nhật theo TRIGGER drift (IC/hit-rate tụt dưới ngưỡng — dựng dashboard predicted-vs-realized theo tuần) + lịch nền (vd mỗi quý). Mỗi lần đổi model BẮT BUỘC: re-train → export lại predict → chạy lại HPO/WFO → bump CONFIG_VERSION → deploy. KHÔNG thay model mà giữ tham số cũ.
- **Validate product vs backtest:** định kỳ chạy lại backtest trên đúng khoảng + tham số product đã chạy, so PnL/số lệnh/DD; lệch quá ngưỡng → cảnh báo.

---

## Nguyên tắc nền
- Đo ĐUÔI rủi ro (profitFactor, worstSingleLoss, payoff, MAE leg đầu), KHÔNG tin win rate.
- Mọi tập dùng để ĐÁNH GIÁ phải là tập KHÔNG tham gia quyết định nào — kể cả quyết định bằng mắt người. Nhìn một tập nhiều lần để chọn = đã overfit lên nó.
- Tách bạch: đo MODEL (Bước 1) ≠ đo CHIẾN LƯỢC (Bước 2–4). Lẫn hai cái là gốc mọi nhầm lẫn.