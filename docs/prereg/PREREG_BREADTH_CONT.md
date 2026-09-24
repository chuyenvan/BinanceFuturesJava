# PREREG_BREADTH_CONT.md — TASK B2 Bước 7: gate LIÊN TỤC theo breadth-score (BRC)

Khoá TRƯỚC khi sim. Thiết kế MASTER `TASK_B2_step7_breadth_continuous_gate.md` (2026-09-21).
Thực thi: executor (session `session_01UoVRjusfNM2USSVNKQrm7z`), branch `module`, repo
`/home/ubuntu/src/BinanceFuturesJava`. Tiền đề: `docs/result/RESULT_BREADTH_GATE_SIM.md` (Bước 6, BR
nhị phân) = NULL vì u1 fail (n_eff ×1.224) + cắt quá tay 2025 (return-2025 22.9% < T170 32.7%).

## 1. CƠ CHẾ (khoá, causal)
`breadth_score(t)` = % coin sống trên MA200 của chính nó (all-coin-sống, causal ≤ t−1), lấy từ
`research/analysis/out/breadth_score_series.csv` cột `breadth_score_allcoin` (đã xác nhận 1645
dòng dữ liệu + header; day_id = floorDiv(epoch_ms, 86400000) = UTC-day, trùng quy ước
`RegimeSchedule.scaleForTime`).

`gate(t) = gate_up + (gate_down − gate_up) × clip((thr − breadth_score(t)) / thr, 0, 1)`
với **gate_up=1.0, gate_down=1.7, thr=0.50**. breadth≥50% → gate 1.0; breadth 0 → gate 1.7;
tuyến tính giữa. Cập nhật theo NGÀY, causal. Giá trị này đã tính sẵn trong cột
`gate_allcoin_ma200` của cùng file (đối chiếu công thức từng dòng: khớp).

## 2. HẠ TẦNG (đã khoá cách sửa)
- Java: `RegimeSchedule` hiện NHỊ PHÂN (col regime → UP=1.00 / khác=1.70). Thêm CHẾ ĐỘ đọc một
  giá trị gate float/ngày trực tiếp từ cột số của CSV (mặc định TẮT → giữ đường nhị phân cũ).
  Cờ mới `SIM_REGIME_GATE_VALUE_COL` (int, mặc định −1 = nhị phân). ≥0 → đọc float ở cột đó.
  Đây là thay đổi CỘNG THÊM thuần: T170 có `GATE_REGIME_ADAPTIVE=false` → không gọi
  `RegimeSchedule.load` → OFF byte-identical theo cấu tạo.
- Kaggle: `tools/kaggle_sim.py` thêm resolve `SIM_REGIME_FILE` = đường mount Kaggle của CSV
  regime (glob theo basename, giống cách wire `WFO_FUNDING_PRED_DIR`). No-op khi không truyền.
- Cổng OFF byte-identical (BẮT BUỘC): T170 + jar mới + cờ TẮT phải ra md5
  `efb793e2468ca3a7318da0f0ad23d4fc`. FAIL → DỪNG báo MASTER, không sim tiếp.

## 3. BIẾN THỂ (khoá, không thêm bớt)
- **T170** (`X1_GS_T170_2021`): incumbent, n=1089, md5 `efb793e2`, equity 111070. (baseline)
- **gate-1.0 = T100** (`X1_C3_FULL_2021`): base lấy breadth tối đa, n=2559 (số cũ, dùng lại).
- **BR nhị phân** (`X1_C3_FULL_2021_REGIME_BR`, top-50/MA200/50%): n=1582 (số Bước 6 dùng lại).
  Lưu ý confound: BR dùng breadth **top-50**, BRC dùng **all-coin** (khác định nghĩa breadth —
  theo đúng thiết kế MASTER §1/§3; ghi rõ khi so u4).
- **BRC (chính, khoá)**: base = `x1_c3_full` + `SIM_GATE_REGIME_ADAPTIVE=1` +
  `SIM_REGIME_GATE_VALUE_COL=4` + CSV gate liên tục all-coin/MA200/thr50/1.0→1.7.
  Tag `X1_C3_FULL_2021_REGIME_BRC`.
- **BRC0 (đối chứng)**: base = `x1_c3_full` + `GATE_DYN_SCALE=g0` CỐ ĐỊNH đều, g0 chọn để TỔNG
  n(BRC0) ≈ n(BRC). Tìm g0 bằng nội suy log-tuyến tính n(g): n(1.00)=2559, n(1.70)=1089; nội
  suy 1–2 lần cho khớp n(BRC). KHÔNG sweep chọn winner. Tag `X1_C3_FULL_2021_REGIME_BRC0`.

k phán quyết = 1 (BRC).

## 4. TIÊU CHÍ (khoá TRƯỚC; metric = `bigdown_struct` icc_anova + `c3_rates`/`x1_rates`)
Cửa sổ 2021-07-01..2025-12-31. n_eff_total = Σ ks/(1+(ks−1)·ICC), ICC = icc_anova theo cohort
NGÀY-vào (hàm dùng chung `bigdown_struct.icc_for` = đúng `icc_anova`).
- **u1 breadth**: n_eff_total(BRC) ≥ 1.5 × n_eff_total(T170). T170 = **606.26** (icc_anova) →
  ngưỡng = **909.38**. (GHI CHÚ CHO MASTER: design doc ghi ngưỡng 909; task-prompt lại ghi
  "tức ≥1364" — mâu thuẫn. Tôi khoá theo CÔNG THỨC design-doc 1.5×T170=909.38, và báo cáo tỉ số
  n_eff(BRC)/n_eff(T170) để MASTER phân xử cả 2 mốc.)
- **u2 khẩu vị**: `x1_rates.py --appetite current --k` PASS mọi năm (maxDD≤30/UW≤200/quý≥−15/
  coin≤15%), UW≤200 MỌI NĂM, và CAGR(BRC) ≥ CI-floor T170 = **14.80%**.
- **u3 vs incumbent**: maxDD(BRC) ≥ **−14.805%** (=1.25×maxDD_T170=−11.844) VÀ UW(BRC) ≤ **115**
  (=1.25×UW_T170=92). (dấu: maxDD âm; "≤ −14.8%" nghĩa |maxDD|≤14.805, tức maxDD ≥ −14.805.)
- **u4 giãn đúng**: UW(BRC) < UW(BRC0) toàn kỳ VÀ **return-2025(BRC) > return-2025(BR nhị phân)**.
- **u5 giữ uptrend**: CAGR2023(BRC) ≥ 0.90×CAGR2023(gate-1.0=T100)=**54.39%** VÀ CAGR2024(BRC) ≥
  0.90×CAGR2024(T100)=**40.75%**.

THẮNG = BRC đạt u1–u5. Nếu u1 fail nhưng BRC vượt trội T170 rõ (CAGR cao hơn đáng kể + maxDD/UW
trong khẩu vị + giữ 2025) → ghi "ứng viên incumbent mạnh" (MASTER phân xử), KHÔNG tự tuyên THẮNG.
CẤM tune tham số sau khi thấy số (chống dredging): nếu BRC không đạt, đó là kết quả, không mở
biến thể mới (thr khác, gate_up/down khác) trong CHÍNH round này.

## 5. DỰ BÁO CẢNH BÁO (khoá trước khi chạy)
1. n(BRC) > n(BR)=1582: gate liên tục ≤ gate nhị phân trên MỌI ngày breadth<50% (chỉ chạm 1.7
   khi breadth=0) → ít chặn hơn → nhiều lệnh hơn BR, tiến gần T100=2559.
2. u1 có thể VẪN fail (n_eff < 909.38): breadth thấp phần lớn thời gian (Bước 6: not_up 72%),
   dù nới liên tục vẫn có thể chưa đủ ×1.5.
3. return-2025(BRC) > return-2025(BR): 2025 breadth cho gate liên tục ~1.33 (vừa) thay vì 1.7
   cứng → giữ được nhiều uptrend-2025 hơn BR (kỳ vọng cốt lõi của round này).
4. UW(BRC) nằm giữa BR(180) và T100(248); có thể vẫn > 115 (u3 UW fail) như BR.
5. u5-2023 có thể fail như BR (gate chặn một phần uptrend 2023 breadth<50%).

## 6. NỀN SO SÁNH
T170 byte-identical Oracle==Kaggle (md5 `efb793e2`, đã xác nhận `docs/runbooks/KAGGLE_SIM_48M.md`). T100/
BR/BR0 = printDone Oracle Bước 6 dùng lại (sim Java xác định, không lệch nền — đã chứng minh ở
T170). BRC/BRC0 chạy TRÊN KAGGLE (không đụng shadow-c3). Cổng OFF (T170 jar mới trên Kaggle) tái
lập `efb793e2` xác nhận jar mới + bundle mới không đổi nền.

## 7. QUY TRÌNH
PREREG (file này) commit → sửa Java + kaggle_sim + sinh CSV + profiles commit → build jar
(Oracle, không kill shadow) → bundle Kaggle mới → OFFCHECK T170 md5 → BRC → tìm g0 khớp n →
BRC0 → metric u1–u5 → `docs/result/RESULT_BREADTH_CONT.md` + bảng → commit (KHÔNG push) → memory.
