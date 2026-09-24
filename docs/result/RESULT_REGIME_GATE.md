# RESULT_REGIME_GATE — Bước 2: gate regime-adaptive MA200-trailing (2026-09-21)

Kết quả cho `docs/prereg/PREREG_REGIME_GATE.md` (commit `9c5b74d`, chốt TRƯỚC build/sim). Thay thế bản
2026-09-14 (`466a68c`, regime=ret30, VERDICT NULL) — lịch sử cũ nguyên vẹn trong `git log`. Không
đổi ngưỡng/công thức sau khi thấy số; mọi phát hiện ngoài dự kiến ghi rõ là "phát hiện lúc chạy".

## 0. Cổng an toàn — PASS

- **OFF byte-identical**: build jar mới từ HEAD (`9c5b74d`, không sửa `.java`) → chạy lại T170
  (`X1_C3_FULL_2021_REGIME_OFFCHECK`, profile `x1_gs_t170.properties`) → `printDone.csv` md5 =
  `efb793e2468ca3a7318da0f0ad23d4fc` — **KHỚP CHÍNH XÁC** tham chiếu. **PASS.**
- **shadow-c3**: dừng lúc **07:10:32** (2026-09-21, +07), chạy tuần tự 1 JVM/lần: T170 OFF-verify
  (07:12:58→07:26:xx, n=1089) → R (07:27:33→~07:41:xx, n=2051) → R0 (07:42:28→~07:56:xx, n=1908).
  Khởi động lại `shadow-c3` lúc **07:57:00**, verify `active` lúc 07:57:05; kiểm log 3 phút gần
  nhất: **0 lỗi -2014**, 3 lỗi -2015 (IP-whitelist, đã biết trước, không ảnh hưởng vòng lệnh
  chính — `[SHADOW] so vi the giay khoi tao ... open=14 realized=1513.74 paperEquity=35000.0` nạp
  lại đúng). Tổng thời gian dừng ~46.5 phút.
- **Định nghĩa regime của `RegimeSchedule.java`**: KHÔNG hardcode lịch — nạp causal từ file CSV
  ngoài (`SIM_REGIME_FILE`), scale xác định theo ngày UTC với `floorEntry` (thiếu ngày dùng giá
  trị ngày liền trước, causal tuyệt đối). Tính causal/lookahead phụ thuộc script sinh CSV — script
  MỚI `regime_build_ma200.py` dùng đúng `close[D-1]` (không dùng dữ liệu ngày D trở đi).
  **0 dòng diff `.java`** (hạ tầng dùng nguyên trạng từ vòng 09-14, chỉ build lại + re-verify).

## 1. Bảng chính (2021-07-01..2025-12-31, Oracle ARM64)

| Tag | n lệnh | n_eff_total | ICC(roi,ngày) | maxDD% | UW (ngày, toàn cửa sổ) | CAGR% | CAGR CI95×1.1774(k=2) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **T170** (mốc) | 1089 | 606.26 | 0.0516 | −11.84 | 92 | 29.27 | [14.80, 46.23] |
| **gate-1.0** (T100) | 2559 | 1103.86 | 0.1016 | −16.13 | 248 | 31.94 | [11.72, 56.94] |
| **R** (regime MA200) | 2051 | 943.79 | 0.0898 | −11.84 | 223 | 32.95 | [14.86, 54.60] |
| **R0** (đối chứng, gate=1.18 đều) | 1908 | 828.17 | 0.1033 | −13.13 | 229 | 29.75 | [11.62, 51.34] |

Ghi chú: `n_eff_total`/ICC/maxDD: `regime_gate_metrics.py` (tái dùng `bigdown_struct.py` nguyên
văn). CAGR+CI: `cagr_ci_t170.py --k 2` (bootstrap khối-72h, 2000 rep, seed 20260905, k=2 — 2 ứng
viên R/R0 so với baseline T170). `g0=1.18` cho R0: nội suy log-tuyến tính khoá trong PREREG §3
(`b=-1.22051, a=9.06788` tính lại chính xác từ 2 điểm neo — bản PREREG ghi `b=-1.22166,a=9.06946`
do làm tròn tay lúc soạn, sai số ~0.001, KHÔNG đổi `g0` làm tròn 2 chữ số — vẫn ra 1.18 — đã dùng
công thức CHÍNH XÁC hơn khi thực thi, ghi minh bạch sai lệch nhỏ này).

## 2. Khẩu vị hiện hành THEO NĂM (`x1_rates.py --appetite current --k 2`: maxDD≤30%, UW≤200/năm,
năm không âm, quý≥−15%)

| Tag | 2021 | 2022 | 2023 | 2024 | 2025 | Kết luận |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS toàn kỳ** |
| gate-1.0 (T100) | PASS | PASS | PASS | PASS | **FAIL** (UW=227) | FAIL |
| R | PASS | PASS | PASS | PASS (UW=200, sát biên) | **FAIL** (UW=223) | FAIL |
| R0 | PASS | PASS | PASS | PASS | PASS (UW=126) | **PASS toàn kỳ** |

**Phát hiện quan trọng nhất của vòng này**: năm **2022, R khớp GẦN NHƯ TUYỆT ĐỐI với T170**
(maxDD −11.84 = −11.84, UW 72 = 72, ret 19.59% ≈ 19.58%) — vì MA200-trailing phân loại **100%
ngày 2022 là NOT-UP** (regime đúng bear tuyệt đối), nên suốt năm 2022 gate của R luôn = 1.70,
R **về mặt cơ học trở thành chính T170** trong đúng năm bear mà Bước 1 chẩn đoán. Đây là bằng
chứng THỰC NGHIỆM mạnh nhất cho thấy cơ chế regime-adaptive **hoạt động ĐÚNG như thiết kế** cho
đúng loại rủi ro nó nhắm tới (bear-multi-month LUNA/2022).

**Nhưng năm 2025 lộ ra MỘT NGUỒN UW KHÁC, KHÔNG liên quan BTC-trend**: MA200 phân loại 2025 là
**73.4% ngày UP** (không phải bear) — nên gate của R phần lớn thời gian = 1.00 (lỏng) trong năm
này, y hệt gate-1.0/T100 (cũng lỏng 1.0 suốt) — và **cả hai đều FAIL UW năm 2025** (R=223,
T100=227, gần bằng nhau). Trong khi đó **R0 (gate cố định 1.18, không đổi theo regime) lại PASS
2025 dễ dàng (UW=126)** — vì nó không bao giờ nới hẳn về 1.00 dù BTC "uptrend" theo MA200.
⇒ **Kết luận cơ chế**: 2025 có một yếu tố gây UW dài **KHÔNG tương quan với xu hướng BTC** (BTC
"lên" theo MA200 nhưng chiến lược vẫn kẹt dưới nước lâu) — hoàn toàn khác cơ chế 2022 (LUNA, BTC
giảm sâu kéo dài). Do regime-adaptive CHỈ nhắm đúng loại rủi ro "BTC bear kéo dài", nó **sửa
được ĐÚNG mảnh 2022 nhưng để lộ/không sửa được mảnh 2025** — và vì nới về đúng 1.00 vào lúc
2025 "trông có vẻ uptrend", R còn tệ hơn một gate cố định trung bình ở đúng năm đó. Đây KHÔNG phải
lỗi thiết kế mà là giới hạn phạm vi: tín hiệu BTC-macro không bắt được nguồn rủi ro thứ hai này.

## 3. Đánh giá u1–u5 (khoá trong PREREG §4)

| Tiêu chí | Ngưỡng | Giá trị R | Kết quả |
|---|---|---|---|
| **u1** breadth | `n_eff_total ≥ 909.39` (=1.5×606.26) | 943.79 (×1.557) | **✅ PASS** |
| **u2** khẩu vị + CAGR floor | PASS mọi năm (đặc biệt UW≤200) + CAGR≥14.80% | FAIL 2025 (UW=223>200); CAGR=32.95%✅ | **❌ FAIL** (vỡ vì UW) |
| **u3** vs T170 | `maxDD≥−14.80%` ∧ `UW≤115` | maxDD=−11.84✅ / UW=223❌ | **❌ FAIL** (vỡ vì UW) |
| **u4** nhắm-bear đúng | `UW(R)<UW(R0)` ∧ chuỗi UW dài nhất R ngắn hơn R0 | 223<229 ✅ ∧ 223<229 ✅ | **✅ PASS** (nhưng xem lưu ý dưới) |
| **u5** không phá uptrend | CAGR năm 2023&2024 của R ≥90% gate-1.0 | 2023: 60.97/60.43=100.9%✅; 2024: 42.65/45.28=94.2%✅ | **✅ PASS** |

**Lưu ý quan trọng cho u4**: PASS về mặt SỐ (223<229) nhưng **chuỗi UW dài nhất của R và R0 nằm ở
HAI GIAI ĐOẠN KHÁC HẲN NHAU** — R0's dài nhất là **2021-12-05→2022-07-21** (đúng bear LUNA, y hệt
gate-1.0), còn R's dài nhất là **2025-03-04→2025-10-12** (không phải bear BTC). Nghĩa là cơ chế
regime CÓ nhắm đúng và RÚT NGẮN được vấn đề 2022 (nếu so trực tiếp riêng năm 2022: R giữ UW=72
ngày y hệt T170, R0 vẫn để lộ UW=145 ngày năm đó) — u4 PASS đúng theo nghĩa "nhắm-bear khớp thiết
kế". Nhưng vì R lại "mở" đúng lúc 2025 (mà MA200 gọi nhầm là uptrend), nó tạo ra một chuỗi UW MỚI
tệ ngang whatever R0 còn sót — nên lợi ích ròng toàn cửa sổ chỉ nhỉnh hơn R0 một chút (223 vs 229),
không đủ để kéo UW toàn kỳ về dưới ngưỡng khẩu vị (200) hay ngưỡng so-T170 (115).

## 4. Phán quyết — theo luật khoá PREREG §4

**NULL** — theo đúng điều kiện đã khoá "*NULL = UW(R) vỡ khẩu vị (>200)*": UW(R)=223>200 (toàn cửa
sổ) và FAIL rõ ràng ở năm 2025 (UW=223>200) trong bảng khẩu vị-theo-năm. (Điều kiện NULL còn lại,
"R0 ngang R ở u4", KHÔNG xảy ra — R0 KHÔNG ngang R, u4 PASS rõ — nhưng chỉ cần MỘT trong hai điều
kiện NULL là đủ, và điều kiện UW>200 đã tự nó kích hoạt NULL.) R đạt u1∧u4∧u5 (3/5) nhưng FAIL
u2∧u3 (đều vì UW, không phải vì maxDD hay breadth hay CAGR) ⇒ không đạt điều kiện THẮNG (cần cả 5).

**Đây là NULL "có cấu trúc", khác NULL của TASK B**: TASK B (pacing theo size) NULL vì pacing
hoàn toàn KHÔNG chạm được UW (maxDD giảm nhưng UW y nguyên/tệ hơn cả 2 biến thể). Ở đây,
regime-adaptive gate **THỰC SỰ sửa được UW của ĐÚNG loại bear nó nhắm tới** (2022: R=T170 gần như
tuyệt đối, tốt hơn hẳn so với TASK B P0/P3 không hề tách biệt được cơ chế) — nhưng vẫn NULL vì
**tồn tại một nguồn UW-dài THỨ HAI, độc lập với BTC-trend, xuất hiện ở 2025** mà không cơ chế nào
trong 2 vòng (B lẫn B2-Bước-2) nhắm tới. u1 (breadth ×1.56) và u5 (giữ ≥94-101% CAGR uptrend
2023/2024) cho thấy cách tiếp cận "regime-adaptive theo BTC-macro" là ĐÚNG HƯỚNG và không hề phá
uptrend — chỉ chưa đủ để bao trùm rủi ro UW ở MỌI năm.

## 5. Khuyến nghị

- **KHÔNG đưa R (regime-adaptive MA200, gate 1.0/1.70 theo BTC) vào production** — vỡ khẩu vị UW
  ở năm 2025 (223>200), dù đã giải quyết đúng bear 2022 mà Bước 1 chẩn đoán.
- **Giữ T170 làm incumbent.**
- **Hướng tiếp theo (ngoài phạm vi vòng này, cần PREREG riêng)**: 2025 cần một chẩn đoán UW-source
  RIÊNG (tương tự `DIAG_UW_SOURCE.md` của Bước 1 nhưng cho đúng cửa sổ 2025) — vì đã loại trừ được
  "BTC bear" (MA200 nói 2025 là uptrend 73.4%) làm nguyên nhân, nghi vấn còn lại là: suy giảm
  alpha/chất lượng tín hiệu theo thời gian (model drift), thay đổi cấu trúc vi mô thị trường
  (crowding/thanh khoản 2025 khác 2021-2024), hoặc một dạng "chop dài không xu hướng" mà MA200 (vốn
  chỉ phân biệt lên/xuống, không phân biệt "xu hướng có cấu trúc" khỏi "đi ngang nhiễu") không bắt
  được. Nếu xác định được, có thể thêm MỘT lớp regime thứ hai (không phải BTC-trend) để nhắm đúng
  2025, hoặc chấp nhận đóng hướng "breadth long-only toàn kỳ" và chuyển sang TASK D (alpha mới)
  hoặc admission-filter theo tín hiệu nội tại (không phải macro BTC).
- Việc regime R đạt gần-tuyệt-đối hiệu năng T170 ở 2022 (u4) là bằng chứng hạ tầng
  `GATE_REGIME_ADAPTIVE`/`RegimeSchedule` hoạt động chính xác — nên GIỮ code này (đã 0-diff, OFF
  byte-identical) để tái sử dụng cho bất kỳ định nghĩa regime nào khác trong tương lai (chỉ cần
  thay file CSV, không cần sửa `.java`).

## 6. Thay đổi code

- **`.java`: 0 dòng diff.** Hạ tầng `GATE_REGIME_ADAPTIVE`/`EntryGate`/`RegimeSchedule`/
  `Configs`/`SimulatorMarketLevelTicker1MStopLoss` đã có sẵn từ vòng 2026-09-14 (`466a68c`), giữ
  nguyên trạng — chỉ build lại (`mvn -o package`) và re-verify OFF byte-identical (§0).
- `research/analysis/regime_build_ma200.py` (mới, 119 dòng): sinh regime CSV causal MA200-trailing
  + dd365 robustness, KHÔNG sửa `regime_build.py` cũ (ret30).
- `research/analysis/regime_gate_metrics.py` (mới, ~127 dòng): tính u1/u3/u4 cho 4 tag, tái dùng
  nguyên văn hàm của `bigdown_struct.py`/`c3_rates.py`, không sửa 2 file gốc.
- `profiles/x1_c3_full_regime_r.properties`, `profiles/x1_c3_full_regime_r0.properties` (mới):
  mỗi file = `x1_c3_full.properties` + 2-3 dòng flag (regime file hoặc `SIM_GATE_DYN_SCALE=1.18`).
- Dữ liệu mới (ngoài git, trên Oracle): `/home/ubuntu/regime_work/btc_daily_close_2021full.csv`
  (mở rộng BTC daily close về 2021-01-01, sớm nhất `kaggle_data_hpo` có),
  `/home/ubuntu/regime_work/regime_daily_ma200_x1_2021.csv` (file regime nạp vào sim qua
  `SIM_REGIME_FILE`).
- **Cổng OFF byte-identical: PASS** (md5 khớp tuyệt đối `efb793e2468ca3a7318da0f0ad23d4fc`).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
