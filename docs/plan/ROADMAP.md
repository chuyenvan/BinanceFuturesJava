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
> ▶️ **TRẠNG THÁI (cập nhật 2026-06-29) — 2 TRACK SONG SONG:**
> • **Track A — Bước 3 (ruin):** ✅ circuit breaker MARGIN 0.50 CHỐT + COMMIT (`3041257`, CONFIG_VERSION v10).
>   ✅ funding fee code lại (tính 1 lượt khi đóng) + GATE PASS (OFF totalPnl=50311, trades=35774 khớp baseline)
>   + mặc định OFF (`APPLY_FUNDING_FEE=false`, bật ở HPO/Golden cuối). ⏳ CÒN LẠI: margin-call/equity thật
>   (mảnh cuối) — user chốt TẠM BỎ QUA để chạy WFO song song. *(funding code uncommitted, chờ user duyệt commit.)*
> • **Track B — Bước 4 (WFO):** sensitivity giảm gene XONG ([ADR-0012](decisions/0012-genome-18-gene-off-cung-cum-C.md): 18 gene); WFO framework ĐÃ DUYỆT + 5 quyết định chốt (`insights/WFO_FRAMEWORK_DESIGN.md` mục 6, 2026-06-29) → bắt đầu code.
> — Hai track KHÔNG tuần tự: WFO không còn "gác" sau Bước 3 (sensitivity là tiền đề đã xong). ⚠️ maxDD trong WFO có thể BỊ HIỂU NHẸ vì chưa có margin-call thật (Bước 3 chưa tròn).
> — *(Lịch sử: 2026-06-28 từng chốt "gác Bước 4 để vào thẳng Bước 3"; cap %vốn/cụm + RunDcaCapBacktest đã GỠ — vô dụng trên danh mục, lá chắn thật là trần margin tổng.)*
> **GIỚI HẠN khi đọc lại WFO sau này:** chưa có margin-call thật nên maxDD có thể HIỂU NHẸ.

Để backtest ĐƯỢC PHÉP sụp thì fitness mới trung thực.
- ❌ **Circuit breaker — CO CHE DA BI XOA KHOI SIM (dinh chinh 2026-09-03, M2).**
  Ban cu cua dong nay ghi "✅ `BREAKER_MODE=MARGIN`, `BREAKER_MARGIN_HALT=0.50` chan MO MOI khi
  marginRunning/balanceBasic >= 0.50" — **khong con dung cho duong SIM**. Commit `5f40a90`
  (2026-09-03) xoa `RunBreakerBacktest.java` (185 dong) + `RunMarginHaltSweep.java` (195 dong)
  va -136 dong o `MarketBigChangeDetector.java`; `Configs.java:509-512` ghi ro **"co che
  circuit-breaker DA BI XOA 2026-09-03. Chi ho tro SIM_BREAKER_MODE=OFF"**. Gia tri `MARGIN` /
  `DCA` / `BOTH` khong con chay duoc. BR1/BR2/BR3 khong the chay lai ma khong viet lai code.
  EV cung da bi phu dinh doc lap: `BR1_margin` 60,272 · `BR2_both` 60,272 (giong het BR1) ·
  `BR3_mg006` 59,542 DD -20.9 — **khong cai thien gi** so voi C2b 60,390 / K0 DD -21.0.
  Co che maxDD la "gia chay nguoc tren lenh DA MO", khong phai "mo qua nhieu lenh".
  **CON DUNG:** `evaluateCircuitBreakerCore` VAN ton tai va VAN bat tren duong **LIVE**
  (`MarketBigChangeDetector.java:196`, `DetectEntrySignal2TradeNormal.java:543-544`) — la 1
  trong 4 kill-switch da khoi phuc o `637513c`. Tuc: **live co breaker cung, sim thi khong.**
- ✅ **Funding** cho lệnh kẹt lâu: `computeFundingOnClose` tính 1 lượt khi đóng (Σ rate × quantity × avgEntry).
  Trước đây comment hết → PnL lạc quan; nay đo được (hệ được thưởng ròng -918, ~1.8% PnL, maxDD không đổi).
- ⏳ **Margin call / cháy tài khoản (CHƯA làm):** sizing theo equity thật thay `balanceBasic` cố định. User
  tạm bỏ qua để chạy WFO. Đây là mảnh cuối làm fitness trung thực hoàn toàn.
- Calibrate chi phí từ log product thật khi có (slippage/fee thực) rồi nạp ngược vào sim.

## Bước 4 — Walk-Forward (WFO) thay cho in-sample tuning
Chỉ làm khi Bước 1–2 PASS. **Chi tiết + TRẠNG THÁI LIVE + sub-roadmap → [insights/WFO_ROADMAP](insights/WFO_ROADMAP.md)** (Bước 4 giữ gọn ở đây để không phình context tổng).
- Nguyên tắc bất biến: WFO rolling **train = OOS = bước trượt** (các đoạn OOS KHÔNG chồng lấn — trượt ngắn = ảo giác bằng chứng); **output là PHÁN QUYẾT "pipeline có generalize không"**, KHÔNG phải 1 bộ tham số (bộ deploy sinh ở pha HPO-cuối riêng nếu PASS).
- PASS pre-registered (chốt TRƯỚC khi nhìn): **WFE_median ≥ 0.5 · %OOS-dương ≥ 70% · worst OOS maxDD ≤ 50%**. ⚠️ maxDD HIỂU NHẸ khi Bước 3 (margin-call) chưa tròn.
- Tiền đề đã xong: genome 18 gene ([ADR-0012](decisions/0012-genome-18-gene-off-cung-cum-C.md)); generate predict-only ([TASK-108](../tasks/108-generate-selector-predict-only.md)).

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