# PREREG_UW2025_DIAG — chẩn đoán nguồn UW-2025 (2026-09-21)

Chốt TRƯỚC khi tính số. Tiền đề: `docs/result/RESULT_REGIME_GATE.md` (Bước 2) — MA200-trailing sửa
đúng bear-2022 (R≈T170) nhưng vỡ khẩu vị vì một nguồn UW **thứ hai, độc lập với BTC-trend**, lộ
ra ở 2025 (R UW năm=223, gate-1.0 UW năm=227, đều FAIL >200; R0 gate-cố-định lại PASS UW=126).
Nhiệm vụ này chẩn đoán BẢN CHẤT nguồn UW-2025: concurrency-cao-trong-chop (vá được bằng admission
cap) hay model-drift-alpha (không vá được bằng admission) hay khác. CHỈ đọc `printDone.csv`/
`sim.out` đã có (T170=`X1_GS_T170_2021`, T100/gate-1.0=`X1_C3_FULL_2021`,
R=`X1_C3_FULL_2021_REGIME_R`) + `CLOSES_1H.bin`. KHÔNG sim, KHÔNG xgboost, KHÔNG sửa `.java`.
KHÔNG dùng dữ liệu sau 2025-12-31 (không holdout 2026). Tái dùng nguyên văn
`research/analysis/uw_source.py`/`bigdown_struct.py`/`hedge_overlay_a.py`/`c3_rates.py`
(hàm `uw_streaks`, `btc_daily_regime`, `regime_summary`, `label_core_marginal`, `load_trades_utc`,
`date_to_ms_utc`, `overlap_mask`, `hourly_grid`, `build_bd_flags`, `load_universe_breadth`,
`sum_notional_on_grid`, `equity_at_grid`, `block_boot_mean`, `C.trades`, `C.equity`) — KHÔNG sửa
các file gốc đó, chỉ import.

## Q1 — Định vị chuỗi UW-2025 (khoá TRƯỚC)

- Dùng đúng `uw_streaks(equity_series)` của `uw_source.py` (RLE trên `s < s.cummax()`, không đổi
  công thức) cho 3 tag T170/T100/R.
- **"Chuỗi UW-2025"** = bất kỳ chuỗi nào trong `uw_streaks()` có `[start,end]` GIAO với
  `[2025-01-01, 2025-12-31]`. Báo cáo TOÀN BỘ chuỗi như vậy (không chỉ top-1), sắp theo độ dài
  giảm dần, cho cả 3 tag.
- **Cửa sổ chính** cho Q2-Q5 = chuỗi giao-2025 DÀI NHẤT của mỗi tag (T100_win, R_win); nếu một tag
  có ≥2 chuỗi giao 2025 đáng kể (>=30 ngày), báo cáo cả hai, phân tích riêng chuỗi dài nhất.
- Đối chiếu T170: định vị chuỗi giao-2025 dài nhất của T170 (kỳ vọng ~52 ngày theo brief MASTER)
  và trả lời "vì sao nó thoát" bằng cách so Q2-Q3 của đúng T170 trong CÙNG khung thời gian với
  T100_win/R_win (không phải chuỗi riêng của T170) VÀ trong chuỗi riêng của chính T170.

## Q2 — Môi trường thị trường 2025 trong chuỗi UW (khoá TRƯỚC)

Trong mỗi cửa sổ (T100_win, R_win, và cùng lịch cho T170):
- Tái dùng `btc_daily_regime()`/`regime_summary()` nguyên văn: `pct_below_ma200`,
  `dd_from_peak365_mean/min`, `ret30_mean_pct`, `ret60_mean_pct`, `pct_ret30_negative`,
  `btc_ret_over_window_pct`.
- **Chỉ số MỚI (định nghĩa khoá ở đây)**:
  - `realized_vol_daily_pct` = độ lệch chuẩn (%) của return-ngày BTC-close trong cửa sổ (không
    annualize; báo thêm bản ×√365 để so mặt bằng năm).
  - `range_pct` = `(max(close)-min(close))/close[0] × 100` trong cửa sổ (biên độ đỉnh-đáy, đo
    "sóng" bất kể hướng).
  - `chop_ratio` = `range_pct / |btc_ret_over_window_pct|` (nếu mẫu số ≈0 thì báo `inf`) — tỷ lệ
    biên độ đi-về so với dịch chuyển ròng; CÀNG LỚN càng "chop" (đi nhiều, về ít).
  - `n_sign_flips_per_30d` = số lần đổi dấu return-ngày liên tiếp trong cửa sổ, chuẩn hoá /30 ngày
    (chop cao ⇒ đổi dấu nhiều).
  - `breadth_pct_red_mean` = trung bình (trên lưới giờ trong cửa sổ) của `load_universe_breadth()`
    (% symbol có return-1h âm, toàn universe, tái dùng nguyên văn `bigdown_struct.py`).
- **Luật phân loại khoá TRƯỚC** (áp dụng cơ học sau khi có số, không đổi ngưỡng):
  - `CHOP_KHONG_XUHUONG` nếu `|btc_ret_over_window_pct| < 15` VÀ `chop_ratio ≥ 2.0` VÀ
    `30 ≤ pct_below_ma200 ≤ 70` (MA200 không nghiêng hẳn về phía nào phần lớn thời gian).
  - `DOWNTREND_NHE_MA200_KHONG_BAT` nếu `btc_ret_over_window_pct ≤ -15` VÀ `pct_below_ma200 < 50`
    (BTC thực giảm rõ nhưng MA200 vẫn bị kéo lên bởi giai đoạn tăng trước đó nên không báo NOT-UP).
  - Ngoài 2 điều kiện trên: `KHAC` (ghi rõ số liệu, không ép vào 1 trong 2 nhãn).

## Q3 — Phơi nhiễm đồng thời 2025 (khoá TRƯỚC)

- Hàm MỚI `concurrent_series(d, grid)`: đếm số lệnh đang mở tại mỗi mốc giờ (delta +1 tại
  `s_idx`, −1 tại `e_idx+1`, `cumsum`) — cùng quy ước lưới với `sum_notional_on_grid`/
  `equity_at_grid` (tái dùng nguyên văn từ `hedge_overlay_a.py`/`bigdown_struct.py`).
- Tỷ lệ phơi nhiễm = `sum_notional_on_grid(d,grid) / equity_at_grid(tag,grid)` (đúng công thức
  M3 của `bigdown_struct.py`, không đổi).
- Báo cáo mean/median/p90/max của `k(t)` (số lệnh đồng thời) và tỷ lệ Σnotional/equity, tách 4
  nhóm: (a) T100 TRONG T100_win, (b) T100 NGOÀI 2025 (cả kỳ trừ T100_win), (c) T170 TRONG CÙNG
  LỊCH T100_win, (d) R TRONG R_win. Đối chiếu tham chiếu đã có (TASK A M3: Σnotional/equity
  T170=0.058, T100=0.270 MỌI LÚC; U_MAX=0.60).
- **Luật quyết định khoá TRƯỚC cho giả thuyết "concurrency cao trong chop"**: XÁC NHẬN nếu
  median/p90 của Σnotional/equity (hoặc k(t)) trong T100_win **≥ 80%** giá trị tương ứng đo được
  trong cửa sổ UW-2022 (Bước 1: T100 trong-UW-2022 dùng M3 chung — lấy lại số `0.270` làm mốc so
  sánh chung toàn kỳ vì Bước 1 không tách riêng theo cửa sổ UW mà theo bigdown-flag; ở đây so
  bằng cách tính LẠI M3 kiểu tương tự nhưng theo cửa sổ UW-2022 thực (2021-11-16→2022-07-21) làm
  neo thứ hai). BÁC BỎ (chuyển hướng nghi ngờ sang Q4/drift) nếu median/p90 trong T100_win KHÔNG
  cao hơn rõ rệt (trong khoảng ±20%) so với T100 NGOÀI 2025 (tức 2025 không có gì bất thường về
  khối lượng, chỉ là ROI tệ hơn).

## Q4 — Chất lượng lệnh 2025 / model drift (khoá TRƯỚC)

- Theo NĂM DƯƠNG LỊCH (2021,2022,2023,2024,2025), cho T100 và T170 (đối chiếu) và R: trong số
  lệnh MỞ trong năm đó, tính `n`, ROI trung bình (`block_boot_mean`, CI90, tái dùng nguyên văn),
  `win_rate=(roi>0).mean()`.
- Tách riêng theo nhãn `label_core_marginal()` (tái dùng nguyên văn công thức `EntryGate`,
  KHÔNG khoá key) cho T100: ROI/win-rate của nhóm **marginal** (chỉ qua gate 1.0, alpha selector
  S1 biên) theo từng năm — đây là phép đo TRỰC TIẾP "S1 selector có kém đi theo thời gian không".
- **Luật quyết định khoá TRƯỚC cho giả thuyết "model drift"**: XÁC NHẬN drift nếu ROI trung bình
  của nhóm marginal năm 2025 **THẤP HƠN RÕ RỆT** (điểm ước lượng ≤0 VÀ CI90 không chồng lấn phần
  dương của) ROI marginal trung bình các năm 2021-2024 GỘP; hoặc nếu `win_rate` marginal 2025
  thấp hơn ≥5 điểm phần trăm so với trung bình 2021-2024. BÁC BỎ drift nếu ROI/win-rate marginal
  2025 nằm TRONG khoảng biến động thông thường của các năm khác (CI90 chồng lấn, hoặc còn dương)
  — khi đó UW-2025 phải giải thích bằng cơ chế KHÁC (khối lượng/concurrency hoặc thị trường xấu
  chung mà cả hệ thống hứng chịu, không riêng "chất lượng dự đoán biên tệ đi").
- Đối chiếu T170 cùng năm: nếu T170 CŨNG giảm ROI 2025 (nhưng vẫn PASS appetite nhờ ít lệnh hơn)
  ⇒ ủng hộ "thị trường 2025 khó chung" hơn là "riêng S1 hỏng". Nếu CHỈ T100/marginal giảm còn
  T170/core giữ nguyên ⇒ ủng hộ "alpha biên (marginal) suy giảm riêng, core vẫn ổn".

## Q5 — Thử nghiệm bàn giấy: cap concurrency hồi tố (khoá TRƯỚC)

Phương pháp CRUDE/COUNTERFACTUAL THÔ (không phải sim thật, ghi rõ giới hạn):
1. Lấy `d = load_trades_utc('X1_C3_FULL_2021')` (T100), sort theo `s_ms` tăng dần.
2. Duyệt tuần tự; giữ tập "đang mở" (loại bỏ lệnh đã đóng, `e_ms < s_ms` của ứng viên, khỏi tập
   trước khi xét ứng viên mới).
3. `equity_now` = giá trị THẬT của đường equity T100 gốc tại `s_ms` ứng viên (asof, không tính
   lại — XẤP XỈ bậc-1, bỏ qua hiệu ứng dây chuyền lên sizing/budget của các lệnh còn lại nếu cap
   đã loại bớt lệnh trước đó; ghi rõ đây là hạn chế phương pháp).
4. Hai HỌ cap, đánh giá RIÊNG (không kết hợp):
   - **(a) COUNT cap**: từ chối ứng viên nếu `(số lệnh đang mở + 1) > K`. Quét
     `K ∈ {3,4,5,6,8}` (K=3~4 ≈ kbar T170=3.55; K=8 ≈ đủ rộng để gần như không chặn ngoài 2022).
   - **(b) NOTIONAL cap** (proxy toàn cục cho `CONC_CAP`, KHÁC phạm vi hẹp của guard thật —
     `CONC_CAP_AGG_DCA` chỉ tính DCA-grid, ở đây áp dụng như trần TOÀN BỘ sổ lệnh để đo cận trên
     tiềm năng): từ chối nếu `(Σnotional đang mở + notional ứng viên)/equity_now > X`. Quét
     `X ∈ {0.15, 0.25, 0.35, 0.45}` (0.45 = giá trị `CONC_CAP_AGG_DCA` có sẵn, dùng làm mốc quen
     thuộc dù phạm vi áp dụng khác).
5. Lệnh bị từ chối: LOẠI HOÀN TOÀN (không tính PnL). Lệnh được nhận: giữ nguyên PnL gốc.
6. `synthetic_equity(t) = E0 + cumsum(pnl của lệnh được nhận, ghi nhận tại e_ms)` với `E0` = giá
   trị đầu tiên của đường equity thật (không dựng lại compounding/budget — XẤP XỈ CỘNG THÊM, ghi
   rõ là counterfactual thô theo đúng yêu cầu nhiệm vụ).
7. Chạy lại `uw_streaks(synthetic_equity)`, lấy chuỗi giao-2025 dài nhất mỗi kịch bản.
8. **Luật quyết định khoá TRƯỚC**: "CONC_CAP CÓ TIỀM NĂNG" nếu TỒN TẠI ≥1 kịch bản (trong (a) hoặc
   (b)) đưa UW-2025 (chuỗi giao-2025 dài nhất trên `synthetic_equity`) xuống **≤200 ngày** MÀ số
   lệnh bị loại TOÀN KỲ **≤50%** tổng số lệnh gốc (tránh false-positive kiểu cap cực chặt xoá gần
   hết sổ). Ngược lại ⇒ "KHÔNG có tiềm năng rõ bằng cap đơn giản không điều kiện regime".
9. Báo cáo thêm: n lệnh bị loại TRONG T100_win vs NGOÀI T100_win cho mỗi kịch bản đạt ngưỡng —
   nếu cap chỉ hiệu quả bằng cách xoá ồ ạt lệnh NGOÀI 2025 (vd trong 2022, đã có regime-gate lo)
   thì không phải bằng chứng cap-toàn-cục giải quyết ĐÚNG 2025; cap phải xoá NHIỀU trong chính
   T100_win để được coi là "nhắm đúng".

## Ghi chú phạm vi

Không dùng dữ liệu sau 2025-12-31. Không chạy sim/build. Mọi công thức/ngưỡng ở trên KHÓA trước
khi đọc kết quả; sai lệch phát sinh lúc code (nếu có) ghi rõ TRƯỚC/SAU như các PREREG trước.
