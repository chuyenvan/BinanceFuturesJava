# PREREG_PARITY_V12_DRY — ADDENDUM 11: đếm ngày sạch khi dry đổi jar r4n → r4q, và cổng G-MICRO (2026-11-05, TRƯỚC mọi nhãn ngày sau swap)

Quyết định MASTER. Bối cảnh: dry đổi jar r4n (fb6711ef) → r4q dự kiến khoảng 11-06. Phía tín hiệu chỉ khác ở việc loại PREMARKET
(ADD10, hiện chỉ 1 symbol là PREDICTUSDT), cộng env C11. Viết trước khi có nhãn của bất kỳ ngày nào sau swap.

## 1. Ngày swap
- Ngày có JVM restart để nạp r4q = **XÁM** (như ngày deploy/restart, §5.2 / ADD6 / ADD10). Không tính vào ngày SẠCH.
- Harness chỉ chấm phần sau swap của ngày đó: T0 = tick quyết định đầu tiên sau restart r4q, giống cách làm với ngày deploy 11-03
  (WINDOW_START). Phần trước swap không chấm.

## 2. Quy tắc PREMARKET theo jar của từng ngày, không hồi tố
- Mỗi ngày D chấm theo jar **đang chạy tại T1 của D**, lấy từ sổ `parity_v12w/jars.json` (tên, đường dẫn, md5, mốc start JVM ms,
  premarket_excl):
  - Ngày r4n (từ 11-03 tới trước swap): A1 = TRADFI + INDEX, **giữ PREMARKET** (PREDICT nằm trong U_D^A1). Harness Java build trên r4n.
  - Ngày r4q (từ swap trở đi): A1 = TRADFI + INDEX + **PREMARKET**. Harness Java build trên jar r4q (`build_r4q`), `a1cls` loại PREMARKET.
- Không chấm lại ngày r4n theo luật r4q, và ngược lại.
- Ngày sau swap chưa có r4q trong `jars.json` thì không được chấm. Phải đăng ký jar r4q (md5 + mốc start) trước.

## 3. Ngày SẠCH và các nhãn khác (cửa sổ từ 2026-11-04)
- **SẠCH** ⇔ kết luận ngày = ĐẠT **và** ngày sạch §5 = SẠCH (mọi kiểm §5, gồm §5.5 collectData).
- Ngày XÁM do restart/deploy/swap: **không phá chuỗi**, không được tính.
- XÁM vì lý do khác, KHÔNG ĐO ĐƯỢC, hoặc CHƯA XÁC ĐỊNH: không tính, không phá chuỗi, ghi rõ lý do.
- Ngày **TRƯỢT** bất kỳ: **dừng đếm** G-MICRO, MASTER chẩn đoán. Đếm lại theo quyết định của MASTER (văn bản riêng).

## 4. Cổng G-MICRO (đủ CẢ HAI)
- (i) Tổng **≥ 7 ngày SẠCH** trong cửa sổ từ 11-04. Ngày r4n và ngày r4q đều được đếm.
- (ii) **≥ 1 ngày SẠCH trọn vẹn trên r4q** (không phải ngày swap), **và** smoke **24 h** sau swap: 0 dòng `ERROR` và 0 dòng `LATCH`
  trong log app 242, khoảng [start JVM r4q, start + 24 h], đọc từ log cửa sổ đã pull, chỉ đọc.
- `day_report_v12` ghi trạng thái G-MICRO (đếm, danh sách ngày, smoke, DỪNG nếu có TRƯỢT) vào
  `docs/result/parity_v12_gmicro.json` sau mỗi ngày chấm.

## 5. Không đổi
- Tiêu chí ĐẠT/XÁM/TRƯỢT từng phép đo (PREREG gốc, ADD1–ADD10), R4–R6, KPI/T-BOOK "không so được" (ADD6/ADD9).
- Nhóm K vẫn chờ MASTER quyết (ADD9 §1).
