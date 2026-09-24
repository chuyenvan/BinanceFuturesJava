# PREREG_BREADTH_GATE_SIM — Bước 6: sim regime-gate bằng MARKET-BREADTH (2026-09-21)

Chốt: 2026-09-21, commit TRƯỚC khi build/sim. Thiết kế MASTER (`/mnt/user-data/outputs/TASK_B2_step6_breadth_regime_sim.md`, không có trong git — nội dung khoá lại đầy đủ ở đây). Thực thi: agent Sonnet. Chủ quyết định: Uni.

Tiền đề: `docs/diag/DIAG_BREADTH_REGIME.md` (commit `4f4801c`/`dee1672`) — market-breadth (định nghĩa A:
`breadth_top50_MA200(D) < 50%`, causal) là regime DUY NHẤT trong 7 hướng độc lập (TASK B, B2
Bước 2/3/4/5.1, B2 Bước 5.2 A/B/C) phủ được CẢ UW-2022 (92.7%) LẪN UW-2025 (70.9%), cả hai ≥60%.
Nhưng edge độc lập (ROI/loss-rate T100 theo regime) KHÔNG xác nhận "notup" là lệnh xấu — bao phủ
thời gian PASS không đồng nghĩa cắt đúng lệnh trong sim thật. Vòng này SIM để phân giải.

## 0. RECON (đã đọc trước khi khoá luật)

1. **Hạ tầng dùng lại nguyên trạng, 0-diff Java kỳ vọng**: `GATE_REGIME_ADAPTIVE`/
   `RegimeSchedule`/`Configs` đã có từ Bước 2 (`466a68c`→`9c5b74d`), mở rộng ở Bước 4 (`ba3d7ba`,
   thêm `SIM_REGIME_SCALE_UP` không hằng số cho `EntryGate.REGIME_SCALE_UP`, mặc định vẫn
   `1.00f`). `RegimeSchedule.load()` đọc CSV: cột 0=utcDay, cột 3=regime ("UP"→1.00,
   khác→`REGIME_SCALE_NOTUP`=1.70 cố định); các cột khác chỉ audit. **Biến thể BR dùng đúng
   up=1.0/not_up=1.7 — TRÙNG mặc định của `REGIME_SCALE_UP`, nên KHÔNG cần khai báo
   `SIM_REGIME_SCALE_UP` trong profile** ⇒ không đụng nhánh code mới của Bước 4, dùng lại đường
   0-diff nguyên bản của Bước 2. HEAD hiện tại `dee1672` (branch `module`, sạch).
2. **Nguồn breadth**: `research/analysis/breadth_regime.py` (Bước 5.2/5.3, KHÔNG sửa) đọc
   `trend_rank_ic.load_closes()` (CLOSES_1H.bin, lọc `ts<2026-01-01` — HOLDOUT rule nguyên văn)
   + tính `breadth(D) = 100 * mean(up_i(D))` trên symId 1..50 (proxy top-50 theo `map_kaggle.csv`,
   KHÔNG phải rank volume thật — hạn chế đã ghi nhận ở Bước 5.2, không lặp lại ở đây), với
   `up_i(D) = close_i[D-1] >= MA200_i_trailing(D)` (MA200 trên chính coin i, `min_periods=30`,
   dùng dữ liệu ≤ D-1, causal). `not_up(D) = breadth(D) < 50%`. Script này CHƯA xuất CSV theo
   định dạng `RegimeSchedule` — viết script MỚI `research/analysis/breadth_regime_csv.py`
   (KHÔNG sửa `breadth_regime.py`, chỉ `import` các hàm `build_daily_close_by_sym`/`up_matrix`/
   `breadth_from_up_matrix`/`day_id` của nó) để sinh `regime_daily_breadth.csv`, theo đúng khuôn
   cột của `regime_build_ma200.py` (Bước 2): cột 0=utcDay, cột 3=regime — audit thêm breadth_pct/
   n_valid/topn/ma_window/threshold_pct.
3. **Lead-in MA200**: giống Bước 2, `up_matrix` tính rolling-MA trên TOÀN BỘ lịch sử có trong
   `CLOSES_1H.bin` của từng coin (không giới hạn theo `day_range`) rồi mới reindex xuống cửa sổ
   xuất — nên KHÔNG cần chạy lại `DumpBtcDaily` (khác Bước 2, vì nguồn ở đây là `CLOSES_1H.bin`
   qua `trend_rank_ic`, không phải BTC daily close CSV riêng). Xuất CSV từ `2021-06-01` (lead
   30 ngày trước SIM start `2021-07-01`, cùng quy ước với `regime_build_ma200.py`) đến
   `2025-12-31`.
4. **Dataset/run template**: tag đợt trước (`X1_C3_FULL_2021_REGIME_R`/`_R0`/`_RA12`/`_RA14`,
   `X1_GS_T170_2021`) chạy qua `WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1_2021`
   `WFO_SMART_CACHE=1 SIM_END_DATE=20251231 EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json`
   `TRADING_PROFILE=<profile>`, `java -Xmx16g -cp target/binance-java-sdk-1.2.4.jar
   com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss`, config.properties =
   `configs/sim_dev_file.properties` (khuôn `research/pipeline/x1/run_flatgate.sh`, không có
   script commit riêng cho các tag REGIME_* trước — viết mới `research/pipeline/x1/
   run_breadth_gate.sh` theo đúng khuôn này, thêm case `OFFCHECK|BR|BR0`). `SIM_END_DATE=20251231`
   đã tự chặn HOLDOUT 2026 ở mức runner — không đụng seal.

**Không rào cản cứng nào mới** (không lookahead, không cần sửa `.java`) ⇒ tiếp tục khoá luật.

## 1. CƠ CHẾ (khoá — xem TASK gốc §1)

Regime CSV `regime_daily_breadth.csv` sinh từ `breadth_regime_csv.py` (tái dùng hàm của
`breadth_regime.py`, không sửa file gốc): `not_up(D) = breadth_top50_MA200(D) < 50%`, causal.
Nạp qua `GATE_REGIME_ADAPTIVE=1` + `SIM_REGIME_FILE=<csv>`. **BR không cần `SIM_REGIME_SCALE_UP`**
(mặc định 1.00 khớp đúng thiết kế up=1.0). Xác nhận OFF byte-identical TRƯỚC khi tin dùng lại hạ
tầng (môi trường/code đã đổi qua Bước 4 kể từ lần verify gần nhất `9c5b74d`→nay `dee1672`,
dù phần REGIME không đổi từ `ba3d7ba`).

## 2. BIẾN THỂ (khoá — xem TASK gốc §2)

Baseline (không tính k trong CI): **T170** (`X1_GS_T170_2021`, tái dùng, không chạy lại — chỉ
OFF-verify) và **gate-1.0/T100** (`X1_C3_FULL_2021`, tái dùng nguyên vẹn, KHÔNG chạy lại).
- **BR (chính, khoá)**: `SIM_GATE_REGIME_ADAPTIVE=1`, `SIM_REGIME_FILE=/home/ubuntu/regime_work/
  regime_daily_breadth.csv`. Profile `profiles/x1_c3_full_regime_br.properties` =
  `x1_c3_full.properties` + đúng 2 dòng flag trên (không thêm `SIM_REGIME_SCALE_UP`). Tag
  `X1_C3_FULL_2021_REGIME_BR`.
- **BR0 (đối chứng)**: gate CỐ ĐỊNH ĐỀU `SIM_GATE_DYN_SCALE=g0`, `g0` chọn để `n_total(BR0)` ≈
  `n_total(BR)`. **Công thức khoá TRƯỚC (giống hệt Bước 2/4, chỉ thay số sau khi có `n_total(BR)`)**:
  nội suy log-tuyến tính từ 2 điểm neo `gate=1.00→n=2559` (T100), `gate=1.70→n=1089` (T170) trong
  ĐÚNG cửa sổ 2021-07-01..2025-12-31: `b=(ln(1089)-ln(2559))/(1.70-1.00)`, `a=ln(2559)-b*1.00`.
  Sau khi có `n_total(BR)`: `g0=(a-ln(n_total(BR)))/(-b)`, làm tròn 2 chữ số thập phân, kẹp
  `[0.50,2.00]`. Profile `profiles/x1_c3_full_regime_br0.properties` = `x1_c3_full.properties` +
  `SIM_GATE_DYN_SCALE=g0`. Tag `X1_C3_FULL_2021_REGIME_BR0`.
- Nếu `n_eff(BR)` quá thấp (u1 fail vì notup thường xuyên) → đó LÀ kết quả, KHÔNG mở biến thể
  up1.2/ngưỡng khác trong round này (chống dredging — đúng luật khoá của TASK gốc §2).

## 3. TIÊU CHÍ u1–u5 (khoá — xem TASK gốc §3, giữ nguyên văn)

- **u1 breadth**: `n_eff_total(BR) ≥ 1.5 × n_eff_total(T170)` = `1.5 × 606.26 = 909.39`
  (`bigdown_struct.py::n_eff`, tái dùng qua `research/analysis/breadth_gate_metrics.py`).
- **u2 khẩu vị hiện hành**: PASS `x1_rates.py --appetite current --k 2` (maxDD≤30%, UW≤200/năm,
  năm không âm, quý≥−15%) MỌI NĂM, **đặc biệt UW≤200 (kể cả 2025)** VÀ `CAGR(BR) ≥ 14.80%`
  (cận dưới CI95 khối-72h ×`sqrt(2ln2)` (k=2) của T170, đã tính sẵn ở Bước 2: `[14.80,46.23]`,
  KHÔNG tính lại CI baseline).
- **u3 so với T170**: `maxDD(BR) ≥ −14.80%` (`=−11.84×1.25`) VÀ `UW(BR) ≤ 115` (`=92×1.25`).
- **u4 nhắm đúng (BR vs BR0)**: `UW(BR) < UW(BR0)` toàn kỳ VÀ đặc biệt `UW_2025(BR) < UW_2025(BR0)`
  (bằng chứng breadth-regime cắt đúng, không phải giảm-chung).
- **u5 giữ uptrend**: `CAGR_năm(BR,2023) ≥ 0.90×CAGR_năm(gate-1.0,2023)` VÀ
  `CAGR_năm(BR,2024) ≥ 0.90×CAGR_năm(gate-1.0,2024)`.
- **THẮNG** = BR đạt u1∧u2∧u3∧u4∧u5. **NULL** = u1 fail (mất breadth) HOẶC u2 vỡ (UW>200 ở bất kỳ
  năm nào) HOẶC BR0 ngang BR ở u4. **HỖN HỢP** = còn lại.

## 4. DỰ BÁO CẢNH BÁO (khoá TRƯỚC, chống giải-thích-xuôi — nguyên văn từ TASK gốc §"Cảnh báo khoá TRƯỚC")

Phủ thời-gian UW ≠ đánh dấu đúng lệnh xấu. Edge độc lập (`DIAG_BREADTH_REGIME.md`): khi
breadth-notup, ROI sổ T100 vẫn +1.99%, loss-rate/phi KHÔNG cao hơn lúc breadth-up (phi thấp hơn:
1.91 vs 2.18); forward BTC return notup còn > up. VÀ breadth<50% xảy ra >55% ngày mỗi năm (trạng
thái thường, không hiếm). ⇒ dự báo 2 rủi ro: **(i)** notup quá thường xuyên → gate chặt phần lớn
thời gian → hệ về gần T170 → **n_eff không đạt ×1.5 (u1 fail)**; **(ii)** chặt lúc breadth thấp
cắt cả lệnh tốt → **CAGR giảm (u5 fail)**. Có thể NULL. Điểm mới đáng theo dõi: **UW-2025 có thể
lần đầu về ≤200** (breadth chặt nhidều ở 2025: notup 70.9% vs MA200-BTC chỉ 26.6% theo
`MA200_BTC_NOTUP_PCT_REF`). Sim phân giải — sẽ đối chiếu 3 điểm dự báo này ở RESULT §cuối.

## 5. CỔNG BẮT BUỘC — fail thì DỪNG, báo MASTER, KHÔNG chạy tiếp, KHÔNG sửa ngưỡng

- **(a) OFF byte-identical**: build jar từ HEAD hiện tại (`mvn -o package`, không sửa `.java`) →
  chạy lại T170 (tag `X1_C3_FULL_2021_REGIME_BR_OFFCHECK`, profile `x1_gs_t170.properties`, flag
  `GATE_REGIME_ADAPTIVE` mặc định `false`) → `printDone.csv` md5 PHẢI =
  `efb793e2468ca3a7318da0f0ad23d4fc`. Fail ⇒ DỪNG.
- **1 job nặng/lần**: `free -g` ≥12G, `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"` rỗng,
  `pgrep java` rỗng (ngoài trừ shadow-c3 trước khi dừng nó) TRƯỚC mỗi sim.
- **shadow-c3**: dừng TRƯỚC chuỗi sim, bật lại NGAY SAU, verify active + log sạch (không -2014;
  -2015 IP-whitelist đã biết, không chặn), ghi mốc giờ.

## 6. QUY TRÌNH — thứ tự bắt buộc

1. Commit file này (TRƯỚC). 2. Viết + chạy `breadth_regime_csv.py` (0-sim) sinh
`/home/ubuntu/regime_work/regime_daily_breadth.csv`, đọc thống kê %UP/%NOTUP theo năm (đối chiếu
`DIAG_BREADTH_REGIME.md`). 3. `mvn -o package` (không sửa `.java`). 4. `free -g`≥12G +
`pgrep java` rỗng → dừng `shadow-c3`, ghi mốc giờ. 5. Sim tuần tự: (i) T170 OFF-verify (cổng §5a)
— fail thì DỪNG; (ii) BR; (iii) tính `n_total(BR)` → giải `g0` (§2) → sinh profile BR0 → sim BR0.
6. Bật lại `shadow-c3`, verify active + log sạch, ghi mốc giở. 7. Tính u1-u5
(`research/analysis/breadth_gate_metrics.py`, tái dùng `bigdown_struct.py`) +
`x1_rates.py --appetite current --k 2` trên 4 tag T170/gate-1.0/BR/BR0. 8.
`docs/result/RESULT_BREADTH_GATE_SIM.md` verdict + đối chiếu §4. 9. Commit code+docs branch `module`,
KHÔNG push. 10. Dọn tag `OFFCHECK` tạm (giữ `printDone.csv`/`sim.out` của BR/BR0 chính), không
đụng `X1_GS_T170_2021`/`X1_C3_FULL_2021`.

Sửa thiết kế lúc thực thi (nếu có) → ghi rõ TRƯỚC/SAU khi thấy kết quả tương ứng, không hồi tố.
OFF không byte-identical ⇒ DỪNG, báo MASTER, không ép chạy tiếp.

## 7. Ý nghĩa (khoá — nguyên văn TASK gốc §6)

THẮNG (đặc biệt UW-2025 lần đầu ≤200 mà giữ breadth+CAGR) ⇒ ý Uni (market-breadth) giải được cái
7 hướng trước không giải được ⇒ shadow forward ≥1 tháng trước khi bàn đổi incumbent. NULL ⇒
breadth-regime phủ đúng thời gian nhưng không cắt đúng lệnh (như dự báo) ⇒ đóng breadth vĩnh
viễn, TASK D là hướng chính.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
