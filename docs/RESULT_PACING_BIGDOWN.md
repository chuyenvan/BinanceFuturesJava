# RESULT_PACING_BIGDOWN — TASK B: hạ gate 1.70→1.0 + pacing bigdown (2026-09-21)

> Kết quả cho `docs/PREREG_PACING_BIGDOWN.md` (commit `aa3c4aa`). Không sửa ngưỡng/công thức sau khi
> thấy số — mọi lệch (nếu có) được ghi rõ là "phát hiện lúc chạy", không hồi tố PREREG.

## 0. Cổng an toàn — kết quả

- **OFF byte-identical**: build mới (flag `SIZE_PACING_MODE` mặc định `OFF`) chạy lại T170 →
  `printDone.csv` md5 = `efb793e2468ca3a7318da0f0ad23d4fc` — **KHỚP CHÍNH XÁC** md5 tham chiếu đã chốt
  trong PREREG. **PASS.**
- **T100 verify**: `X1_C3_FULL_2021` (dùng lại từ TASK A) nguyên vẹn — 2559 dòng, maxDD −16.13%,
  khớp số đã công bố trước đó. Không cần chạy lại.
- **shadow-c3**: dừng trước chuỗi sim (~03:08), chạy tuần tự OFF-verify → P0 → P3 (1 JVM/lần, tổng
  ~47 phút), khởi động lại lúc **03:55:29**, verify `active (running)` + log sạch (không lỗi -2014;
  chỉ có -2015 IP-whitelist đã biết trước trên 1 call phụ, không ảnh hưởng vòng lệnh chính; book
  state nạp lại đúng). Đã xác nhận lại `systemctl is-active shadow-c3` = `active` ở thời điểm viết
  báo cáo này.

## 1. Bảng chính (T170 / T100 / P0 / P3)

| Tag | n lệnh | ICC(roi,ngày) | n_eff_total | maxDD% | UW (ngày) | CAGR% | CAGR CI95 x1.1774 (k=2) | %depth-maxDD-trong-bigdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **T170** (mốc, không tính k) | 1089 | 0.0516 | 606.26 | −11.84 | 92 | 29.27 | [14.80, 46.23] | 100.00% |
| **T100** (gate 1.0, không pacing) | 2559 | 0.1016 | 1103.86 | −16.13 | 248 | 31.94 | — | 74.85% |
| **P0** (gate 1.0 + giảm size ĐỀU ×0.2146) | 2579 | 0.1112 | 1057.04 | −4.64 | 221 | 12.14 | — | 72.67% |
| **P3** (gate 1.0 + pacing bigdown BD1a, γ=0.5) | 2562 | 0.1045 | 1089.23 | −14.28 | 248 | 34.17 | — | 74.77% |

Ghi chú:
- `n_eff_total`, ICC, maxDD-decomp: `bigdown_struct.py` (hàm gốc, tái dùng nguyên vẹn qua
  `research/analysis/pacing_taskb_metrics.py`) — file `research/analysis/out/pacing_taskb_metrics.json`.
- CAGR + CI: `research/analysis/cagr_ci_t170.py` (bootstrap khối 72h, nrep=2000, seed=20260905,
  inflate k=2 = ×1.177410) — chỉ tính CI cho T170 (mốc so sánh theo t2); CAGR điểm của T100/P0/P3 lấy
  từ `x1_rates.py` (khớp với equity cuối kỳ trong `printDone.csv`).
- UW ở bảng này là cột `UW` (chuỗi ngày âm liên tục dài nhất, toàn cửa sổ) của `x1_rates.py::BANG
  CHINH` — **không phải** `uw_days_total` (tổng số ngày dưới đỉnh cũ) của `bigdown_struct.py`
  (T170=1062, T100=1286, P0=1302, P3=1284 — chỉ mang tính tham khảo, không dùng cho t2/t3 vì PREREG
  chốt ngưỡng UW theo định nghĩa của `x1_rates.py`, khớp mốc T170=92 đã nêu trong khung thiết kế).

## 2. Ràng buộc khẩu vị hiện hành theo năm (`x1_rates.py --appetite current --k 2`)

maxDD≤30%, UW≤200 (mỗi năm), quý≥−15%:

| Tag | 2021 | 2022 | 2023 | 2024 | 2025 | Kết luận |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS toàn kỳ** |
| T100 | PASS | PASS | PASS | PASS | **FAIL** (UW=227) | FAIL |
| P0 | PASS | PASS | PASS | PASS | **FAIL** (UW=221) | FAIL |
| P3 | PASS | PASS | PASS | PASS | **FAIL** (UW=232) | FAIL |

Cả P0 và P3 đều **không** đưa gate 1.0 về đạt khẩu vị hiện hành — vỡ đúng ở năm 2025 (UW vượt 200),
giống hệt điểm vỡ của T100 gốc.

## 3. Đánh giá t1–t4

Mốc: `n_eff_total(T170)=606.26` → ngưỡng t1 = `1.5×606.26=909.39`. Cận dưới CAGR floor (t2) =
`14.80%` (CI95 x1.1774 của T170).

| Tiêu chí | Ngưỡng | P0 | P3 |
|---|---|---|---|
| **t1** breadth | `n_eff_total ≥ 909.39` | 1057.04 (×1.744) **✅ PASS** | 1089.23 (×1.797) **✅ PASS** |
| **t2a** khẩu vị (theo năm) | PASS mọi năm | FAIL (2025 UW=221) **❌ FAIL** | FAIL (2025 UW=232) **❌ FAIL** |
| **t2b** CAGR floor | CAGR ≥ 14.80% | 12.14% **❌ FAIL** | 34.17% **✅ PASS** |
| **t2** (a∧b) | | **❌ FAIL** | **❌ FAIL** (vỡ vì t2a) |
| **t3** risk vs T170 | maxDD≥−14.8% ∧ UW≤115 | maxDD −4.64% ✅ / UW=221 ❌ → **❌ FAIL** | maxDD −14.28% ✅ (sát biên) / UW=248 ❌ → **❌ FAIL** |
| **t4** cơ chế (bd_share P3 < P0) | 74.77% < 72.67%? | — | **❌ FAIL** (74.77% > 72.67%, NGƯỢC hướng kỳ vọng) |

## 4. Phán quyết

Theo luật đã khoá trong PREREG §3: *"NULL = không biến thể nào đạt t1-t3"*. Cả P0 và P3 đều KHÔNG
đạt đồng thời t1∧t2∧t3 (cả hai đều fail t2 và t3) ⇒ **VERDICT = NULL.**

H_B (hạ gate 1.70→1.0 + pacing bigdown đưa risk về đạt khẩu vị hiện hành mà vẫn giữ breadth) **bị
bác bỏ** với thiết kế hiện tại. Điểm mấu chốt:

1. **Breadth đạt dễ dàng** (t1 PASS mạnh cho cả P0 và P3, ×1.74–1.80 so T170) — hạ gate xuống 1.0
   luôn luôn tăng số lệnh/n_eff, không phụ thuộc pacing.
2. **Risk KHÔNG được kéo đủ về khẩu vị**: cả hai cách giảm size (đều-P0 lẫn theo-regime-P3) đều chỉ
   sửa được `maxDD` (P0 xuống hẳn −4.64%, P3 xuống −14.28% từ −16.13% của T100) nhưng **không sửa
   được `UW`** — cả hai vẫn có chuỗi ngày âm liên tục dài (221–248 ngày) vượt xa ngưỡng khẩu vị
   (≤200) lẫn ngưỡng so-với-T170 (≤115). Nguyên nhân: pacing chỉ giảm KÍCH THƯỚC lệnh, không giảm
   TẦN SUẤT hay THỜI GIAN của các chuỗi thua — chuỗi underwater dài của gate-1.0 đến từ nhịp
   độ/khoảng cách giữa các đợt hồi vốn (nhiều lệnh nhỏ, hồi chậm), không phải từ biên độ lỗ mỗi
   ngày, nên hạ biên độ (size) không rút ngắn được chuỗi.
3. **Cơ chế regime-targeting KHÔNG hoạt động như kỳ vọng ở t4**: P3 (chỉ giảm size khi bigdown) có
   `%depth-maxDD-trong-bigdown` = 74.77%, CAO HƠN P0 (giảm đều, không điều kiện) = 72.67% — ngược
   hướng giả thuyết. Diễn giải: vì P3 giữ nguyên size (×1.0) ngoài bigdown, phần lớn kịch bản kéo
   dài `maxDD` xảy ra NGOÀI cửa sổ bigdown-BD1a (rớt giá từ từ, không đủ mạnh để BTC ret24h≤−5% kích
   hoạt cờ) vẫn giữ size đầy đủ ⇒ đóng góp tuyệt đối vào depth vẫn lớn, trong khi P0 giảm đều nên cả
   phần trong lẫn ngoài bigdown đều bị "pha loãng" tương tự nhau — kết quả tỷ trọng% bigdown của P3
   không thấp hơn P0. Đây là bằng chứng khá rõ rằng bigdown BD1a (BTC ret24h≤−5%, 1h) không phải là
   "cửa sổ" chứa phần lớn rủi ro đuôi của gate-1.0 trong bộ dữ liệu này — ít nhất không đủ để làm cho
   việc nhắm mục tiêu regime này tốt hơn một unconditional size cut.
4. Điểm khả quan duy nhất: **P3 giữ được CAGR cao nhất trong 4 biến thể (34.17%, vượt cả T170 và
   T100)** và vượt CAGR-floor của T170 — tức phần breadth thêm vào (khi không đứt gate ở bigdown)
   nhìn chung có phẩm chất tốt, KHÔNG phải noise thuần (bác bỏ một phần rủi ro nêu ở PREREG §1 dựa
   trên TASK A M7). Nhưng CAGR tốt không đủ để bù cho UW vỡ khẩu vị.

## 5. Khuyến nghị

- **Không đưa gate 1.0 (kèm pacing P0/P3 theo thiết kế này) vào production** — cả hai biến thể đều
  vỡ khẩu vị hiện hành (UW) và vỡ ngưỡng risk-vs-T170 (t3), dù đã hạ maxDD đáng kể.
- Nếu muốn tiếp tục hướng "hạ gate lấy breadth", vấn đề cần giải là **UW (thời gian)**, không phải
  biên độ (`maxDD`) — pacing theo kích thước không đúng đòn bẩy cho biến này. Hướng khả dĩ cho vòng
  sau (ngoài phạm vi TASK B, cần PREREG riêng): (a) admission-tier rate-limit (P2 đã loại khỏi vòng
  này theo khung thiết kế §3) để giảm TẦN SUẤT chuỗi lệnh thua liên tiếp thay vì giảm SIZE; (b) mở
  rộng định nghĩa bigdown (BD1b/c/q hoặc breadth-based BD2_70/80/90) để bắt được nhiều hơn phần đuôi
  rủi ro gây UW dài — hiện BD1a (BTC ret24h≤−5%) không cho thấy ưu thế so với unconditional ở t4.
  Nên đo `uw_days` phân rã theo regime (tương tự `maxdd_decomp`) trước khi chọn hướng tiếp theo.
- Giữ nguyên T170 (gate 1.70) làm production incumbent.

## 6. Tóm tắt thay đổi code

- `Configs.java`: +12 dòng, thêm `SIZE_PACING_MODE` (String, mặc định `"OFF"`) — thuần cộng thêm,
  không đụng dòng cũ.
- `SimulatorMarketLevelTicker1MStopLoss.java`: +8 dòng, thêm nhánh `if (PacingSizing.ACTIVE) budget
  *= PacingSizing.multiplier(currentTs);` ngay sau khối `VolTargetSizing`, trước tỷ trọng DCA-grid —
  thuần cộng thêm.
- `PacingSizing.java` (mới, 149 dòng): `P0_MULT=0.2146f` (cố định, tính từ median Σnotional/equity
  trong-bigdown T170/T100), `P3_GAMMA=0.5f`, `BD_RET24H_THRESHOLD=-0.05f`; cờ BD1a causal tự viết
  (không tái dùng `MarketBigChangeDetector` — định nghĩa khác), đọc `CLOSES_1H.bin` (BTCUSDT), dùng
  nến ĐÃ ĐÓNG gần nhất (nghiêm ngặt hơn 1h so với cách `VolTargetSizing.COIN_MODE` đang làm, để đảm
  bảo không lookahead). `multiplier()` không bao giờ trả null/NaN/≤0 (fallback 1.0f).
- `profiles/x1_c3_full_p0.properties`, `profiles/x1_c3_full_p3.properties` (mới): mỗi file =
  `x1_c3_full.properties` + đúng 1 dòng `SIZE_PACING_MODE=P0`/`P3`.
- **Cổng OFF byte-identical: PASS** (md5 khớp tuyệt đối) — xác nhận thay đổi không ảnh hưởng T170 khi
  flag tắt.
- Script phân tích mới (0 sim, tái dùng hàm gốc, không sửa `bigdown_struct.py`/`x1_rates.py`):
  `research/analysis/compute_p0_mult2.py`, `research/analysis/cagr_ci_t170.py`,
  `research/analysis/pacing_taskb_metrics.py` (+ output `research/analysis/out/pacing_taskb_metrics.json`).
