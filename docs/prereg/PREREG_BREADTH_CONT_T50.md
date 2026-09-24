# PREREG_BREADTH_CONT_T50.md — TASK B2 Bước 9: gate LIÊN TỤC theo breadth TOP50 (BRCT50)

Khoá TRƯỚC khi sim. Thực thi: executor (session `session_01UoVRjusfNM2USSVNKQrm7z`), branch
`module`, repo `/home/ubuntu/src/BinanceFuturesJava`. Tiền đề: `docs/result/RESULT_BREADTH_CONT.md`
(Bước 7, BRC gate liên tục all-coin) = NULL; `docs/result/RESULT_BREADTH_GATE_SIM.md` (Bước 6, BR
top50 nhị phân) = NULL; `docs/diag/DIAG_BREADTH_SUBSET.md` (Bước 8, subset majors/alts) = NO-GO.
Đây là hoán vị DUY NHẤT chưa chạy của hướng breadth: gate **LIÊN TỤC** dùng breadth **TOP50**
(BR = top50 nhị phân; BRC = all-coin liên tục; BRCT50 = top50 liên tục).

Audit đối kháng (đã xác nhận với MASTER) cho thấy NULL của breadth là THẬT: lệnh mở lúc
breadth-thấp lãi ngang lệnh mở lúc breadth-cao ⇒ gate breadth cắt lệnh KHÔNG phân biệt được
theo lãi/lỗ (coverage thời-gian ≠ discrimination tầng-lệnh). Round này chạy để ĐÓNG DỨT ĐIỂM.

## 1. CƠ CHẾ (khoá, causal)
`breadth_score_top50(t)` = % trong 50 coin (proxy `symId<=50`, ghi rõ là PROXY) đang trên MA200
của chính nó, causal (dùng dữ liệu <= t-1), y ĐỊNH NGHĨA A của DIAG "GO"
(`breadth_regime.py` / `breadth_robust.py` Phần 2). Nguồn:
`research/analysis/out/breadth_score_series.csv` cột `breadth_score_top50` + `gate_top50_ma200`.

`gate(t) = 1.0 + 0.7 * clip((0.50 - breadth_score_top50(t)) / 0.50, 0, 1)`
= `gate_up + (gate_down - gate_up) * clip((thr - score)/thr, 0, 1)` với **gate_up=1.0,
gate_down=1.7, thr=0.50** (KHOÁ, y BRC — chỉ đổi chuỗi breadth all-coin -> top50). breadth>=50%
-> gate 1.0; breadth 0 -> gate 1.7; tuyến tính giữa; cập nhật theo NGÀY, causal. Giá trị đã tính
sẵn ở cột `gate_top50_ma200` (cùng `continuous_gate()` của `breadth_robust.py` — đối chiếu 3
dòng đầu: score 0.14->1.5040, 0.12->1.5320: khớp công thức).

## 2. HẠ TẦNG (dùng lại Bước 7, 0 dòng Java mới kỳ vọng)
- Java: `RegimeSchedule` đọc gate float/ngày ở cột số CSV qua `SIM_REGIME_GATE_VALUE_COL` (int,
  -1 = nhị phân cũ). Jar breadth-cont md5 `06def68b8a0cbc618e9ccd2ae3184ba5` (build Bước 7).
  **0 dòng Java mới round này** — chỉ đổi chuỗi breadth sang top50.
- Sinh CSV: `research/analysis/breadth_cont_csv_t50.py` (bản sao `breadth_cont_csv.py`, đổi cột
  nguồn allcoin->top50, `topn_main` allcoin->top50, output `regime_cont_top50.csv`). Format
  RegimeSchedule: `utcDay,dateUTC,breadth_pct,regime,scale(=gate,cột idx 4),topn_main,ma_window,
  threshold_pct`. Lead-in 30 ngày = gate ngày đầu.
- Profile: `profiles/x1_c3_full_regime_brct50.properties` = bản sao
  `x1_c3_full_regime_brc.properties`, CHỈ đổi `SIM_REGIME_FILE=regime_cont_top50.csv` (giữ
  `SIM_GATE_REGIME_ADAPTIVE=1`, `SIM_REGIME_GATE_VALUE_COL=4`).
- Kaggle: overlay dataset `sim-brc-overlay` (thêm `regime_cont_top50.csv` +
  `prof_x1_c3_full_regime_brct50.properties`, GIỮ jar `06def68b` + file cũ) mount CÙNG bundle lớn
  `sim-x1-2021-bundle` (KHÔNG re-upload 5.3GB). `extra_ds=["sim-brc-overlay"]`.
- **Cổng OFF byte-identical (BẮT BUỘC)**: T170 + jar mới (overlay) + cờ TẮT chạy trên Kaggle
  phải ra md5 `efb793e2468ca3a7318da0f0ad23d4fc`. FAIL -> DỪNG báo MASTER, không sim tiếp.

## 3. BIẾN THỂ (khoá, không thêm bớt)
- **T170** (`X1_GS_T170_2021`): incumbent, n=1089, md5 `efb793e2`, equity 111070. Dùng lại số.
- **gate-1.0 = T100** (`X1_C3_FULL_2021`): base breadth tối đa, n=2559. Dùng lại số Bước 6/7.
- **BR nhị phân** (top-50, `X1_C3_FULL_2021_REGIME_BR`): n=1582. Dùng lại số Bước 6.
- **BRC** (all-coin liên tục, `X1_C3_FULL_2021_REGIME_BRC`): n=1689. Dùng lại số Bước 7.
- **BRCT50 (chính, khoá)**: base = `x1_c3_full` + `SIM_GATE_REGIME_ADAPTIVE=1` +
  `SIM_REGIME_GATE_VALUE_COL=4` + `regime_cont_top50.csv` (gate liên tục top50/MA200/thr50/
  1.0->1.7 causal). Tag `X1_C3_FULL_2021_REGIME_BRCT50`.
- **BRCT50-0 (đối chứng flat, CHỈ chạy NẾU BRCT50 bất ngờ pass u2+u4)**: base `x1_c3_full` +
  `GATE_DYN_SCALE=g0` CỐ ĐỊNH, g0 nội suy log-tuyến tính khớp n(BRCT50) (n(1.00)=2559,
  n(1.70)=1089). KHÔNG sweep chọn winner. Tag `X1_C3_FULL_2021_REGIME_BRCT50_0`.

k phán quyết = 1 (BRCT50).

## 4. TIÊU CHÍ (khoá TRƯỚC; metric `bigdown_struct` icc_anova + `c3_rates`/`x1_rates`)
Cửa sổ 2021-07-01..2025-12-31. n_eff_total = Σ ks/(1+(ks-1)·ICC), ICC = `icc_anova` cohort NGÀY-vào.
- **u1 breadth**: n_eff_total(BRCT50) >= 1.5 × n_eff_total(T170) = **909.38** (T170=606.26 icc_anova).
  Báo cả tỉ số n_eff(BRCT50)/n_eff(T170) cho MASTER (task-prompt nhắc mốc "1364" mâu thuẫn design
  909 — khoá theo CÔNG THỨC 1.5×T170=909.38, báo cả 2 mốc).
- **u2 khẩu vị**: `x1_rates.py --appetite current --k 1` PASS mọi năm (maxDD<=30/UW<=200/quý>=-15;
  coin<=15% KHÔNG đo) VÀ UW<=200 MỌI NĂM VÀ CAGR(BRCT50) >= CI-floor T170 = **14.80%**.
- **u3 vs incumbent**: maxDD(BRCT50) >= **-14.805%** (=1.25×maxDD_T170=-11.844) VÀ UW(BRCT50)
  <= **115** (=1.25×UW_T170=92).
- **u4 giãn đúng**: return-2025(BRCT50) >= **0.95 × return-2025(T170) = 0.95 × 32.7 = 31.065%**
  VÀ (NẾU có flat BRCT50-0) UW(BRCT50) < UW(BRCT50-0). GHI CHÚ: u4 KHÁC BRC — BRC khoá
  ret2025(BRC)>ret2025(BR); ở đây MASTER khoá mốc **T170-tham-chiếu** vì mục tiêu round là "top50
  có giữ 2025 GẦN T170 hơn 2 biến thể kia không".
- **u5 giữ uptrend**: CAGR2023(BRCT50) >= 0.90×CAGR2023(T100)=**54.39%** VÀ CAGR2024(BRCT50) >=
  0.90×CAGR2024(T100)=**40.75%**.

THẮNG = BRCT50 đạt u1-u5. u1 fail nhưng BRCT50 vượt trội T170 rõ (CAGR cao hơn + maxDD/UW trong
khẩu vị + giữ 2025) -> ghi "ứng viên incumbent mạnh" (MASTER phân xử), KHÔNG tự tuyên THẮNG.
CẤM tune tham số sau khi thấy số (chống dredging): BRCT50 không đạt = kết quả, KHÔNG mở biến thể
mới (thr/gate khác) trong CHÍNH round này.

## 5. DỰ BÁO MASTER (khoá trước khi chạy)
BRCT50 loosens 2025 hơn BRC: breadth top50-2025 CAO hơn breadth all-coin-2025 (~11%) vì top50
gồm majors mạnh 2025 -> gate-2025 top50 ~1.33 (vừa) < gate-2025 all-coin 1.42 -> giữ nhiều
uptrend-2025 hơn -> **dự báo BRCT50 GIỮ ret-2025 GẦN T170 NHẤT** trong 3 biến thể (BR 22.9 /
BRC 28.7 / BRCT50 kỳ vọng > 28.7, tiến gần 32.7). NHƯNG:
1. u1 vẫn FAIL (n_eff ×1.5): breadth top50 vẫn <50% phần lớn kỳ -> nới liên tục chưa đủ ×1.5.
2. u3 UW<=115 FAIL: gate top50 liên tục nới hơn -> nhiều lệnh hơn -> UW toàn kỳ vẫn >115 (như BR/BRC).
3. u2 khẩu vị nhiều khả năng FAIL 2025 (UW-2025): nếu top50 nới đủ giữ nhiều lệnh 2025 thì UW-2025
   >200 như BRC (221). Nếu nới VỪA đủ, UW-2025 có thể < BRC (khả năng u2 pass mong manh).
4. u4-ret có thể PASS (ret-2025 >= 31.065) — điểm sáng kỳ vọng DUY NHẤT; u4-UW không đánh giá
   (không chạy flat trừ khi u2+u4 pass).
5. u5-2023 có thể FAIL như BR/BRC (gate chặn phần uptrend 2023 breadth<50%).

**Phán quyết dự báo: NULL "ít tệ nhất"** trong 3 biến thể breadth — giữ ret-2025 gần T170 nhất
nhưng u1+u3 fail (u2 nhiều khả năng fail) -> KHÔNG vượt T170 toàn cục -> **ĐÓNG DỨT ĐIỂM hướng
breadth** (đã 3 biến thể gate BR/BRC/BRCT50 + subset recon + audit đối kháng, đều NULL/NO-GO).

## 6. NỀN SO SÁNH
T170 byte-identical Oracle==Kaggle (md5 `efb793e2`). T100/BR = printDone Oracle Bước 6, BRC =
Kaggle Bước 7 — dùng lại (sim Java xác định, không lệch nền). BRCT50/BRCT50-0 chạy TRÊN KAGGLE
(không đụng shadow-c3). Cổng OFF (T170 jar mới + overlay mới) tái lập `efb793e2` xác nhận thêm
file overlay mới (top50 CSV + profile) KHÔNG đổi nền.

## 7. AN TOÀN
KHÔNG đụng HOLDOUT 2026 (mọi sim `SIM_END_DATE=20251231`) / box 242 / shadow-c3 (không
stop/kill/restart/sửa) / git push. index.lock đợi 30s không xoá. Logging chuẩn (không print).

## 8. QUY TRÌNH
PREREG (file này) commit -> sinh `regime_cont_top50.csv` + profile + metrics + overlay version ->
commit code -> OFFCHECK T170 md5 (Kaggle) -> BRCT50 (Kaggle) -> metric u1-u5 -> (CHỈ nếu pass
u2+u4) BRCT50-0 -> `docs/result/RESULT_BREADTH_CONT_T50.md` + bảng -> commit (KHÔNG push) -> memory.
