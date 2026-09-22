# PREREG_REGIME_GATE — Bước 2: gate regime-adaptive MA200-trailing (2026-09-21)

Chốt: 2026-09-21, commit TRƯỚC khi build/chạy sim. Agent thực thi (Sonnet), thiết kế MASTER
(`TASK_B2_step2_regime_gate.md`). RULE CỐ ĐỊNH THEO CHUẨN NGÀNH, KHÔNG fit. Tiền đề:
`docs/DIAG_UW_SOURCE.md` (commit `9b10742`, TASK B2 Bước 1) — UW của gate-1.0 (248 ngày) nằm
GỌN trong bear-multi-month thật (LUNA/2022, BTC<MA200 89.1% ngày, dd trung bình −44% từ đỉnh-365d),
trong khi T170 không hề "tự lọc" hành vi vào/ra trong đúng giai đoạn đó — nó chỉ LUÔN có phơi
nhiễm đồng thời thấp hơn. Cơ chế đúng = admission-filter theo SỐ LƯỢNG lệnh đồng thời, điều kiện
theo regime bear-multi-week (không phải size — đã NULL ở TASK B; không phải exit — đã nhanh sẵn).

## 0. ⚠️ PHÁT HIỆN RECON QUAN TRỌNG — đã có MỘT VÒNG THỬ TRƯỚC (2026-09-14), VERDICT NULL

Trước khi viết PREREG này, đọc `EntryGate.java`/`RegimeSchedule.java`/`Configs.java` phát hiện
hạ tầng `GATE_REGIME_ADAPTIVE` **đã được xây dựng và chạy thử một lần** ở vòng 2026-09-14
(commit `466a68c`, tác giả "Claude Opus 5", **là tổ tiên của HEAD hiện tại trên branch `module`**
— không phải nhánh khác, không bị revert). Hồ sơ cũ: `docs/PREREG_REGIME_GATE.md` /
`docs/RESULT_REGIME_GATE.md` (bản 2026-09-14, nội dung được thay thế bởi file này — lịch sử cũ
vẫn nguyên vẹn trong `git log`, xem `git show 466a68c`).

**Vòng cũ dùng ĐỊNH NGHĨA REGIME KHÁC**: `ret30(D) = C[D-1]/C[D-31]-1`, UP nếu `ret30>0`. Đây
CŨNG LÀ causal/trailing (không lookahead) nhưng là tín hiệu ngắn hạn (30 ngày), không phải
MA200/dd-365-trailing mà chẩn đoán Bước 1 xác định là khớp đúng "bear-multi-week". **Kết quả vòng
cũ (tham khảo, KHÔNG dùng lại số vì appetite/tiêu chí khác)**: REGIME(ret30) n=1810, CAGR=30.73%
(T170=29.27, T100=31.94), maxDD=−9.74% (tốt nhất trong 3), **UW=189 ngày** (T170=92, T100=248).
Dưới appetite CŨ (UW≤120) → FAIL → NULL, giữ T170. Dưới appetite HIỆN HÀNH (UW≤200, dùng trong
vòng này) UW=189 sẽ **PASS** — nhưng vòng cũ còn FAIL thêm: CAGR +1.46pp so T170 có CI95 ÔM 0
(không phân biệt được với nhiễu), và 3 rate chất lượng (win%/TSloss%/meanP) THUA T170 ngoài CI
(gate nới lúc UP nạp lại lệnh marginal, pha loãng chất lượng). Bài học rút ra cho vòng này:
(i) hạ tầng Java **đã parity-test PASS đầy đủ** (cổng OFF const + 2 cực FORCE UP/NOTUP), không
cần sửa `.java` gì thêm — chỉ cần build lại jar từ HEAD hiện tại và re-verify OFF byte-identical
(môi trường/commit đã đổi từ 09-14 do TASK A/B/B2-Bước1 chèn vào giữa); (ii) tín hiệu ret30 KHÔNG
đủ chọn lọc — nó không phân biệt "bear thật kéo dài nhiều tháng" khỏi "điều chỉnh ngắn hạn", nên
UW vẫn dài và không tăng CAGR có ý nghĩa; (iii) đây chính là động lực chọn MA200-trailing/dd365
(chẩn đoán Bước 1) làm định nghĩa MỚI cho vòng này — một tín hiệu "chậm" hơn, đúng dịch bear-multi-
month hơn ret30.

## 1. RECON (§2 thiết kế) — trả lời trước khi viết luật

1. **Định nghĩa regime HIỆN TẠI của `RegimeSchedule.java`**: **KHÔNG hardcode bất kỳ lịch nào**.
   `RegimeSchedule` chỉ là một `TreeMap<utcDay,scale>` NẠP TỪ FILE NGOÀI (`SIM_REGIME_FILE`, cột
   0=utcDay, cột 3=regime — "UP"→`EntryGate.REGIME_SCALE_UP`, khác→`REGIME_SCALE_NOTUP`); các cột
   khác (vd `ret30` cũ) chỉ để audit, KHÔNG được Java đọc. `scaleForTime(ms)`: `floorEntry` theo
   ngày UTC (thiếu ngày → dùng giá trị ngày gần nhất TRƯỚC đó, causal). Vậy tính causal/lookahead
   **phụ thuộc hoàn toàn vào script sinh file CSV**, không phải vào `RegimeSchedule` — đã audit
   `regime_build.py` cũ (ret30, causal, dùng đúng `C[D-1]`) và sẽ viết script MỚI
   `regime_build_ma200.py` (KHÔNG sửa file cũ) theo đúng nguyên tắc causal đó cho MA200/dd365.
   ⇒ **KẾT LUẬN: hạ tầng là TRAILING/CAUSAL theo thiết kế, không phải lookahead/hardcode.** Không
   cần sửa `RegimeSchedule.java`/`EntryGate.java`/`Configs.java`/`Simulator...java` — dùng nguyên
   trạng (0 dòng diff).
2. **`GATE_REGIME_ADAPTIVE` bật → gate = SCALE_UP(1.00) khi UP, SCALE_NOTUP(1.70) khi NOT-UP**:
   xác nhận đúng qua đọc `EntryGate.threshold()`: `gateScale = GATE_REGIME_ADAPTIVE ?
   CURRENT_REGIME_SCALE : GATE_DYN_SCALE`. **OFF (mặc định, flag=false) → biểu thức
   `x*GATE_DYN_SCALE` giống hệt bản gốc** (IEEE-exact) ⇒ byte-identical theo thiết kế; đã PASS ở
   vòng 09-14 (md5 `efb793e2...`=T170, `dc16e4da...`=T100) và **sẽ re-verify bằng jar build lại
   từ HEAD hiện tại** ở §5 trước khi tin dùng (môi trường/code đã đổi qua TASK A/B/B2-Bước1).
3. **Nguồn dữ liệu regime online**: BTC daily close lấy từ `kaggle_data_hpo` (đúng nguồn giá sim
   giao dịch, qua `DumpBtcDaily.java` có sẵn — không sửa) — **PHÁT HIỆN GIỚI HẠN DỮ LIỆU**: file
   close hiện có (`btc_daily_close.csv`) chỉ bắt đầu 2021-05-01, và bản thân `kaggle_data_hpo`
   chỉ có dữ liệu từ **2021-01-01** (không có gì trước đó). MA200-trailing cần 200 ngày đóng trước
   mỗi ngày quyết định; với dữ liệu sớm nhất 2021-01-01, ngày đầu có ĐỦ 200 quan sát là
   ~2021-07-19. Cửa sổ sim bắt đầu 2021-07-01 ⇒ có một khoảng **~18-19 ngày đầu cửa sổ
   (2021-07-01→2021-07-19), tức 18/1645 ngày = 1.1% cửa sổ**, MA200 chỉ tính được trên SỐ NGÀY ÍT
   HƠN 200 (tối thiểu 30, vẫn causal — không nhìn tới dữ liệu ≥ ngày quyết định, chỉ là trung bình
   trên cửa sổ ngắn hơn). Xử lý: (a) chạy lại `DumpBtcDaily` với khoảng NGÀY RỘNG HƠN
   (2021-01-01→2025-12-31, thay vì 2021-05-01 hiện có) để tối đa hoá dữ liệu lead-in sẵn có (0-sim,
   không sửa `.java`, chỉ chạy lại đúng utility đã có với tham số ngày khác); (b) với ~18-19 ngày
   đầu còn thiếu, dùng MA trên số ngày có sẵn (min 30) — hạn chế nhỏ, ghi rõ, KHÔNG ảnh hưởng tính
   causal, chỉ ảnh hưởng ĐỘ DÀI cửa sổ trung bình trong 1.1% đầu cửa sổ sim.

**Không có rào cản cứng nào** (không lookahead, không cần sửa `.java`) ⇒ tiếp tục viết luật.

## 2. ĐỊNH NGHĨA REGIME — khoá trước, theo chuẩn ngành, KHÔNG tinh chỉnh

- **Chính (quyết định gate)**: `not_up(D)` = `close[D-1] < MA200_trailing(D)`, với
  `MA200_trailing(D) = mean(close[D-200 .. D-1])` (hoặc ít hơn nếu chưa đủ 200 quan sát, tối thiểu
  30 — chỉ ảnh hưởng ~18-19 ngày đầu cửa sổ, xem §1.3). MA200 = chuẩn trend-following phổ biến,
  KHÔNG quét/tinh chỉnh ngưỡng nào khác.
- **Phụ (robustness, chỉ báo cáo, KHÔNG dùng để quyết định gate/không đổi phán quyết)**:
  `dd_from_peak365(D) = close[D-1]/max(close[D-365..D-1]) - 1 <= -25%`.
- `regime(D)` = `NOTUP` nếu `not_up(D)` (định nghĩa CHÍNH) else `UP`. `gate(D)` = `1.70` nếu
  `NOTUP` else `1.00` (= `EntryGate.REGIME_SCALE_NOTUP`/`REGIME_SCALE_UP`, hằng số có sẵn, KHÔNG
  fit — đúng như thiết kế MASTER). Cập nhật theo ngày UTC, hoàn toàn causal (không dùng dữ liệu
  của ngày D trở đi để quyết định gate áp dụng CHO ngày D).
- Script mới `research/analysis/regime_build_ma200.py` (KHÔNG sửa `regime_build.py` cũ) sinh file
  `regime_daily_ma200_x1_2021.csv` (cột `utcDay,dateUTC,ma200,regime,scale,close_prevday,dd365,
  not_up_dd25,n_obs_ma` — `RegimeSchedule.java` chỉ đọc cột 0 và 3, còn lại để audit).

## 3. BIẾN THỂ

- **T170** (mốc, gate 1.70 đều) — dùng lại `X1_GS_T170_2021` nếu md5 re-verify khớp
  `efb793e2468ca3a7318da0f0ad23d4fc`; nếu không khớp raise báo động, KHÔNG chạy tiếp (xem §5).
- **gate-1.0** (T100, đều 1.00) — dùng lại nguyên vẹn `X1_C3_FULL_2021` (không chạy lại).
- **R (chính)**: `SIM_GATE_REGIME_ADAPTIVE=1`, `SIM_REGIME_FILE=regime_daily_ma200_x1_2021.csv`
  (định nghĩa §2). Profile `profiles/x1_c3_full_regime_r.properties` = `x1_c3_full.properties` +
  đúng 2 dòng flag trên. Tag `X1_C3_FULL_2021_REGIME_R`.
- **R0 (đối chứng, tách nhắm-bear khỏi giảm-chung)**: gate CỐ ĐỊNH ĐỀU
  `SIM_GATE_DYN_SCALE=g0`, với `g0` chọn để tổng số lệnh toàn kỳ (`n_rows` trong `printDone.csv`)
  của R0 ≈ của R. **Phương pháp chọn `g0` (khoá TRƯỚC khi chạy R0, chỉ tính SỐ sau khi có kết quả
  R)**: nội suy log-tuyến tính từ 2 điểm neo đã có trong ĐÚNG cửa sổ 2021-07-01..2025-12-31 —
  `gate=1.00 → n=2559` (gate-1.0/T100), `gate=1.70 → n=1089` (T170). Giải
  `ln(n) = a + b*gate` với `b = (ln(1089)-ln(2559))/(1.70-1.00) = -1.22166`,
  `a = ln(2559) - b*1.00 = 9.06946`. Sau khi có `n_total(R)` từ sim R, tính
  `g0 = (a - ln(n_total(R))) / (-b)`, làm tròn 2 chữ số thập phân, kẹp trong `[0.50, 2.00]` (biên
  an toàn tránh ngoại suy quá xa 2 điểm neo). Đây là NỘI SUY THEO SỐ LỆNH, không tinh chỉnh theo
  hướng có lợi cho R — công thức cố định trước, chỉ thay số `n_total(R)` vào sau. Profile
  `profiles/x1_c3_full_regime_r0.properties` = `x1_c3_full.properties` + `SIM_GATE_DYN_SCALE=g0`.
  Tag `X1_C3_FULL_2021_REGIME_R0`.

## 4. TIÊU CHÍ — khoá trước (u1-u5, MASTER đã cho trong khung nhiệm vụ, k=2 — 2 ứng viên R/R0
so với baseline T170 trong vòng này)

- **u1 breadth**: `n_eff_total(R) ≥ 1.5 × n_eff_total(T170)` = `1.5 × 606.26 = 909.39`
  (`research/analysis/bigdown_struct.py::n_eff`, tái dùng qua script mới `regime_gate_metrics.py`).
- **u2 khẩu vị hiện hành**: PASS toàn bộ ràng buộc `x1_rates.py --appetite current --k 2` (maxDD
  ≤30%, UW≤200/năm, quý≥−15%, năm không âm) MỌI NĂM, **đặc biệt UW≤200** (chỉ số chính của vòng
  này); VÀ `CAGR(R) ≥ 14.80%` (cận dưới CI95 khối-72h ×1.1774 (k=2) của T170, đã tính sẵn ở TASK B
  — `research/analysis/cagr_ci_t170.py --k 2 X1_GS_T170_2021` → `[14.80,46.23]`, không tính lại
  CI cho R do baseline không đổi).
- **u3 so với T170**: `maxDD(R) ≥ -14.8%` (không tệ hơn T170 quá 25%: `-11.84×1.25=-14.8`) VÀ
  `UW(R) ≤ 115` (`92×1.25=115`).
- **u4 nhắm-bear đúng (tách khỏi giảm-chung)**: `UW(R) < UW(R0)` VÀ chuỗi UW dài nhất của R có
  **độ dài ngắn hơn** chuỗi UW dài nhất của R0 (cả hai đo bằng `x1_rates.py`/hàm UW của
  `c3_rates.py::stats`, cùng định nghĩa với bảng chính TASK B).
- **u5 không phá uptrend (chống overfit)**: `CAGR_năm(R, 2023) ≥ 0.90 × CAGR_năm(gate-1.0, 2023)`
  VÀ `CAGR_năm(R, 2024) ≥ 0.90 × CAGR_năm(gate-1.0, 2024)` (return theo năm dương lịch — 1 năm
  tròn nên return năm = CAGR năm đó; lấy từ `c3_rates.py::stats()['yr']` hoặc bảng
  `hard_by_year` của `x1_rates.py`, cột `ret_nam%`).
- **THẮNG** = R đạt u1 ∧ u2 ∧ u3 ∧ u4 ∧ u5. **NULL** = UW(R) vỡ khẩu vị (>200) HOẶC R0 ngang R ở
  u4 (không tách được nhắm-bear khỏi giảm-chung). **HỖN HỢP** = còn lại (đạt một phần, không đủ
  cả 5 hoặc không đủ điều kiện NULL).

## 5. CỔNG BẮT BUỘC — fail thì DỪNG, báo MASTER, KHÔNG chạy tiếp, KHÔNG sửa ngưỡng

- **(a) OFF byte-identical**: build jar mới từ HEAD hiện tại (`mvn -o package`, không sửa
  `.java`) → chạy lại T170 (`X1_C3_FULL_2021_REGIME_OFFCHECK`, profile `x1_gs_t170.properties`,
  flag `GATE_REGIME_ADAPTIVE` vẫn mặc định `false`) → `printDone.csv` md5 PHẢI =
  `efb793e2468ca3a7318da0f0ad23d4fc`. Fail ⇒ DỪNG (không tin hạ tầng cũ nữa dù đã parity ở 09-14).
- Không lặp lại 2 cực FORCE UP/NOTUP của vòng 09-14 (đã PASS, 0 dòng code đổi từ đó tới nay —
  quyết định GIẢM 1 lượt sim để tiết kiệm tài nguyên, ghi rõ đây là sai lệch có chủ đích so khung
  §7 gốc, KHÔNG ảnh hưởng an toàn vì (a) đã đủ để xác nhận OFF byte-identical với code hiện tại,
  và cơ chế 2 cực chỉ kiểm tra WIRING không đổi giữa hai vòng — không có commit nào chạm
  `RegimeSchedule.java`/`EntryGate.java`/`Configs.java` phần REGIME kể từ `466a68c`).

## 6. QUY TRÌNH — thứ tự bắt buộc

1. Commit file này (TRƯỚC). 2. Chạy `DumpBtcDaily` (mở rộng khoảng ngày, không sửa code) sinh
`btc_daily_close_2021full.csv`. 3. Viết + chạy `regime_build_ma200.py` (0-sim) sinh
`regime_daily_ma200_x1_2021.csv`, đọc thống kê %UP/%NOTUP theo năm. 4. `mvn -o package` (không
sửa `.java`). 5. Dừng `shadow-c3`, ghi mốc giờ. 6. Sim tuần tự: (i) T170 OFF-verify (cổng §5a) —
fail thì DỪNG; (ii) R; (iii) tính `n_total(R)` → giải `g0` (§3) → sim R0. 7. Bật lại `shadow-c3`,
verify active + log sạch, ghi mốc giờ. 8. Tính u1-u5 (`regime_gate_metrics.py` tái dùng
`bigdown_struct.py` + `x1_rates.py --appetite current --k 2` trên 4 tag T170/gate-1.0/R/R0).
9. `docs/RESULT_REGIME_GATE.md` (thay thế bản 2026-09-14, giữ tham chiếu ở §0 phía trên) với
verdict. 10. Commit code+docs branch `module`, KHÔNG push. 11. Dọn tag `OFFCHECK` tạm (giữ
`printDone.csv`/`sim.out` của T170/R/R0 chính), không đụng `X1_GS_T170_2021`/`X1_C3_FULL_2021`.

Sửa thiết kế lúc thực thi (nếu có) → ghi rõ TRƯỚC/SAU khi thấy kết quả tương ứng, không hồi tố.
OFF không byte-identical / regime hoá ra lookahead ⇒ DỪNG, báo MASTER, không ép chạy tiếp.

## 7. Ý nghĩa — theo khung MASTER (không đổi)

THẮNG ⇒ shadow paper song song ≥1 tháng trước khi bàn đổi incumbent. NULL/HỖN HỢP ⇒ ghi thêm vào
`power_wall.md`: regime-adaptive gate (cả 2 định nghĩa ret30 và MA200-trailing) không cứu được
UW-trong-bear mà giữ breadth ⇒ hướng breadth long-only đóng ở mức admission-filter theo BTC-macro;
chuyển alpha mới (TASK D) hoặc timing-exit là hướng còn lại.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
