# DIAG_UW2025_SOURCE — chẩn đoán nguồn UW-2025 (2026-09-21)

Kết quả cho `docs/PREREG_UW2025_DIAG.md` (commit `84ba4ac`, chốt TRƯỚC khi tính số). Script:
`research/analysis/uw2025_source.py` (tái dùng nguyên văn `uw_source.py`/`bigdown_struct.py`/
`hedge_overlay_a.py`/`c3_rates.py` — KHÔNG sửa 4 file đó). Output đầy đủ:
`research/analysis/out/uw2025_source.json`. 0-sim, 0-xgboost, 0-diff `.java`. Dữ liệu tới
2025-12-31 (không đụng 2026).

## Q1 — Định vị chuỗi UW-2025

| Tag | Cửa sổ chính | Độ dài | Đáy | Trough |
|---|---|---:|---:|---|
| **T100 (gate-1.0)** | 2025-03-04 → 2025-10-16 | 227 ngày | −9.20% | 2025-10-03 |
| **R (regime MA200)** | 2025-03-04 → 2025-10-12 | 223 ngày | −6.54% | 2025-10-03 |
| **T170** | 2025-11-09 → 2025-12-30 | **chỉ 52 ngày** | −4.23% | 2025-11-23 |

T100 có 12 chuỗi giao 2025 (chuỗi phụ đáng kể: 2025-10-31→2025-12-30, 61 ngày, đáy −10.60%).
R có 14 chuỗi giao 2025 — đáng chú ý **chuỗi #2 của R trùng khớp gần như tuyệt đối chuỗi của T170**
(2025-11-09→2025-12-30, 52 ngày) vì đây đúng là đoạn MA200 phân loại **100% NOT-UP** nên gate
của R xiết về 1.70 giống T170. T170 cũng có mặt ở đoạn Mar-Apr (35 ngày, đáy −2.37%) nhưng NGẮN
và NÔNG hơn nhiều so với T100/R (227/223 ngày, −9.2%/−6.5%).

**Vì sao T170 thoát**: (a) T170 KHÔNG hề kẹt trong đúng cửa sổ 2025-03-04→2025-10 mà T100/R vỡ —
chuỗi tương ứng của nó ở đó chỉ 35 ngày/−2.37% (thoát nhanh, không đào sâu); (b) cửa sổ TỆ NHẤT
của chính T170 (Nov-Dec) là một downtrend NGẮN+NÔNG mà MA200 bắt đúng (100% NOT-UP), nhưng không
đủ dài/sâu để vỡ khẩu vị. R (regime) cũng xiết đúng ở đoạn Nov-Dec này (khớp T170) — nhưng R KHÔNG
xiết được ở đoạn Mar-Oct vì MA200 gọi đó là "uptrend" (xem Q2).

## Q2 — Môi trường thị trường 2025 trong chuỗi UW: KHÔNG PHẢI bear, KHÔNG PHẢI chop-không-hướng —
LÀ MỘT "BULL RUN CÓ SÓNG LỚN" mà PREREG không dự đoán trước

| Chỉ số (T100_win, 2025-03-04→10-16) | Giá trị |
|---|---:|
| BTC ret over window | **+32.84%** (R_win: +35.00%) |
| % ngày BTC < MA200 | 15.86% (rõ ràng UPTREND theo MA200) |
| dd_from_peak365 trung bình / thấp nhất | −8.95% / −29.00% |
| range_pct (biên độ đỉnh-đáy) | **57.28%** |
| chop_ratio (range/|net move|) | **1.74** |
| realized_vol ngày / năm hoá | 1.86% / 35.59% |
| n_sign_flips/30d | 13.35 |
| breadth %coin đỏ trung bình | 46.70% (khá cân bằng) |
| **Nhãn khoá TRƯỚC** | **KHAC** (không khớp CHOP_KHONG_XUHUONG lẫn DOWNTREND_NHE) |

T170_own_2025_window (Nov-Dec, 52 ngày): pct_below_ma200=**100%**, ret30 TB=−10.97%, ret_window=
−13.75% — đây LÀ downtrend thật (MA200 bắt đúng), chỉ là ngắn/nông nên không vỡ khẩu vị.

**Phát hiện chính Q2**: cửa sổ UW-2025 của T100/R xảy ra ĐÚNG LÚC BTC ĐANG TĂNG MẠNH (+33-35%,
$83,157→$110-112k), không phải bear/downtrend nào cả — MA200 phân loại đúng là uptrend (chỉ
15.9-16.1% ngày dưới MA200). Nhưng biên độ đỉnh-đáy trong cửa sổ (57.3%) gần gấp đôi dịch chuyển
ròng (33%) ⇒ đây là một **uptrend NHIỄU/GIẰNG CO ("choppy/volatile bull")**: đi lên nhưng bằng
những cú sóng lớn cả hai chiều, không phải một đường trend mượt. Đây là trường hợp NGOÀI 2 nhãn
đã khoá trong PREREG (không phải chop-không-hướng-thuần-tuý vì net move quá lớn 33%>15%; không
phải downtrend-nhẹ vì net move DƯƠNG) — ghi nhận trung thực là phát hiện thứ BA, không ép vào
khung có sẵn.

## Q3 — Phơi nhiễm đồng thời 2025: CAO NGANG-HOẶC-HƠN 2022 VỀ TRỊ TUYỆT ĐỐI, nhưng KHÔNG PHẢI
một đợt bùng phát bất thường so với hành vi thường-trực của chính gate-1.0

| Nhóm | k trung bình (median/p90/max) | Σnotional/equity trung bình (median/p90/max) |
|---|---|---|
| T100 TRONG T100_win (2025) | 3.28 (1.0/9.0/76) | 0.0857 (0.045/0.253/0.498) |
| T100 NGOÀI 2025 (baseline cả kỳ) | 2.62 (0.0/9.0/45) | 0.0678 (0.0/0.234/0.571) |
| T100 TRONG UW-2022 (Bước 1, mốc đối chiếu) | 3.03 (0.0/11.0/45) | 0.0701 (0.0/0.279/0.568) |
| T170 CÙNG LỊCH T100_win | 0.735 (0.0/1.0/74) | 0.0172 (0.0/0.038/0.483) |
| R TRONG R_win (2025) | 2.32 (1.0/6.0/76) | 0.0656 (0.033/0.189/0.498) |

**Đối chiếu 2022 (luật khoá "≥80% mốc 2022 ⇒ XÁC NHẬN")**: p90 k = 9.0/11.0 = **81.8%** PASS;
p90 notional = 0.253/0.279 = **90.6%** PASS. Theo TRUNG BÌNH, 2025 còn CAO HƠN 2022 (k: 108%,
notional: 122%). ⇒ **XÁC NHẬN phơi nhiễm 2025 không hề thấp hơn crisis 2022** về giá trị tuyệt đối.

**Đối chiếu baseline riêng của T100 (luật khoá "trong ±20% ⇒ BÁC BỎ đột biến")**: p90 k =
9.0/9.0 = **100%** (BÁC BỎ — hoàn toàn không đổi); p90 notional = 0.253/0.234 = **108%** (BÁC BỎ,
trong dải ±20%). Theo TRUNG BÌNH: k +25.2%, notional +26.4% (NGOÀI dải ±20%, không kích hoạt BÁC
BỎ, hơi nghiêng phía "cao hơn"). ⇒ Kết quả HỖN HỢP theo thước đo, nhưng nhìn chung: **T100 2025
không phải một đợt "nhồi ồ ạt" đặc biệt so với chính lịch sử vận hành của nó** (median/p90 gần
như giống hệt phần còn lại của lịch sử) — gate-1.0 vốn LUÔN chạy exposure cao hơn T170 4-5 LẦN
mọi lúc (k: 3.28 vs 0.735; notional: 0.086 vs 0.017 trong đúng cùng lịch), đây là ĐẶC TÍNH CẤU
TRÚC có sẵn quanh năm, không phải điều MỚI PHÁT SINH riêng ở 2025.

**Kết luận Q3**: concurrency cao là ĐIỀU KIỆN NỀN thường trực của gate-1.0 (không đổi theo năm),
KHÔNG PHẢI biến giải thích sự khác biệt GIỮA 2022 và 2025 — vì cả hai năm đều có exposure
tương đương nhau, trong khi 2022 sụp (BTC −63%) còn 2025 lại TĂNG (+33%). Giả thuyết
"concurrency-cao-trong-chop" ở dạng ĐƠN GIẢN (chỉ do khối lượng đột biến) **không được xác nhận
là yếu tố PHÂN BIỆT** — cần Q4 để tìm biến thực sự phân biệt.

## Q4 — Chất lượng lệnh 2025: KHÔNG PHẢI model drift cổ điển — hit-rate ổn định, T170/core vẫn
xuất sắc, chỉ ROI-mỗi-lệnh của nhóm MARGINAL bị nén trong đúng 2025

| Năm | T100 ROI TB (CI90) / win% | T170 ROI TB (CI90) / win% | T100-marginal ROI TB (CI90) / win% |
|---|---|---|---|
| 2021 | 1.32% [−0.91,3.49] / 81.6% | 3.60% [2.01,4.91] / 92.6% | 0.22% [−2.29,2.92] / 76.7% |
| 2022 | 1.70% [−0.64,3.81] / 82.0% | 3.45% [1.89,5.11] / 83.8% | 0.85% [−2.11,3.40] / 82.8% |
| 2023 | 5.07% [3.19,7.45] / 87.7% | 7.42% [3.35,13.01] / 86.5% | 3.69% [2.53,4.70] / 88.6% |
| 2024 | 3.10% [2.14,3.96] / 86.2% | 3.94% [2.59,5.32] / 90.0% | 2.97% [1.84,3.97] / 86.0% |
| **2025** | **2.01%** [−0.31,4.12] / 83.0% | **5.10%** [2.39,6.55] / **87.2%** | **0.54%** [−0.54,1.63] / 83.6% |
| gộp 2021-2024 (marginal) | — | — | 2.11% [1.10,3.10] / 84.05% |

**T170/core KHÔNG suy giảm ở 2025 — ngược lại, 2025 là năm TỐT THỨ HAI của T170 (5.10%, chỉ sau
2023's 7.42%)**, win-rate 87.2% cũng cao. Nếu S1 selector "hỏng" theo thời gian thì core cũng
phải tệ đi — nhưng không hề.

**Marginal (alpha biên, chỉ qua gate 1.0)**: ROI trung bình 2025 (0.54%) chỉ bằng ~1/4 mức gộp
2021-2024 (2.11%) — một sự SUY GIẢM RÕ RỆT VỀ ĐIỂM SỐ. Nhưng theo luật quyết định KHOÁ TRƯỚC
(cần điểm ước lượng ≤0 VÀ CI90 không chồng lấn phần dương của lịch sử, HOẶC win-rate giảm ≥5pp):
**KHÔNG đạt ngưỡng "drift XÁC NHẬN"** — điểm ước lượng 2025 vẫn dương (0.54%>0), CI90 [−0.54%,
1.63%] vẫn chồng lấn với phần dưới của CI90 gộp [1.10%,3.10%] (biên trên 1.63%>biên dưới 1.10%),
và win-rate hầu như không đổi (83.6% vs 84.05%, chênh <1pp).

**Quan trọng — marginal dao động mạnh theo năm, không có xu hướng suy thoái đơn điệu**:
2021=0.22%, 2022=0.85%, 2023=3.69%, 2024=2.97%, **2025=0.54%** — 2025 thấp nhưng TƯƠNG ĐƯƠNG mức
2021/2022 (0.22-0.85%), không phải mức thấp CHƯA TỪNG THẤY; 2023-2024 mới là bất thường (cao vượt
trội). Win-rate marginal ổn định 76.7-88.6% suốt 5 năm, KHÔNG có xu hướng giảm dần.

**Kết luận Q4**: BÁC BỎ giả thuyết "model drift"/S1 suy giảm liên tục theo thời gian (hit-rate ổn
định, core vẫn khỏe). Có tồn tại một sự NÉN BIÊN ĐỘ LỢI NHUẬN mỗi-lệnh của riêng nhóm marginal ở
2025 (điểm ước lượng giảm rõ, dù không qua ngưỡng thống kê khoá trước) — khớp với Q2: trong chế độ
"bull-nhiễu-sóng-lớn", các lệnh biên (marginal, độ tin cậy thấp hơn) vẫn được chọn ĐÚNG HƯỚNG
nhiều hơn sai (hit-rate không đổi) nhưng bị "chốt/đảo chiều" sớm giữa các đợt sóng lên-xuống dồn
dập nên mỗi lần thắng ăn ít hơn hẳn — không phải chọn sai nhiều hơn.

## Q5 — Thử nghiệm bàn giấy CONC_CAP: KHÔNG kịch bản nào đạt, cap càng chặt càng phản tác dụng

| Kịch bản | % lệnh bị loại toàn kỳ | UW-2025 sau cap (ngày) | % lệnh loại TRONG T100_win |
|---|---:|---:|---:|
| count K=3 | 75.6% | 299 (XẤU HƠN gốc 227!) | 338/1934 = 17.5% |
| count K=4 | 69.1% | 299 | 312/1767 = 17.7% |
| count K=5 | 62.0% | 299 | 283/1586 = 17.8% |
| count K=6 | 55.6% | 299 | 245/1422 = 17.2% |
| **count K=8** | 42.6% | **243** (gần nhất) | 190/1090 = 17.4% |
| notional X=0.15 | 62.0% | 243 | 256/1587 = 16.1% |
| **notional X=0.25** | 39.6% | **242** (gần nhất) | 161/1014 = 15.9% |
| notional X=0.35 | 21.6% | 299 | 84/553 = 15.2% |
| notional X=0.45 (=CONC_CAP_AGG_DCA hiện có) | 9.1% | 243 | 34/234 = 14.5% |

**KHÔNG kịch bản nào đưa UW-2025 về ≤200 ngày** (gần nhất: 242-243, vẫn FAIL). Đáng chú ý: cap
CÀNG CHẶT (K=3-6, cắt 55.6-75.6% TOÀN BỘ sổ lệnh) lại làm UW-2025 **XẤU HƠN** (299 ngày, so gốc
227!) vì cắt bừa cả lệnh tốt ở những giai đoạn khác làm hỏng cả đường equity tổng thể (counterfactual
thô cộng-thêm không mô phỏng lại được hiệu ứng bù trừ vốn — hạn chế phương pháp đã ghi rõ trong
PREREG). Ở MỌI kịch bản, **chỉ 14.5-17.8% số lệnh bị loại nằm TRONG chính T100_win** — phần lớn
(82-86%) lệnh bị cắt nằm NGOÀI 2025 (chủ yếu 2022) — tức cap không hề "nhắm đúng" 2025, nó cắt
tràn lan toàn lịch sử theo cùng một ngưỡng cứng.

**Verdict khoá TRƯỚC**: `conc_cap_has_potential = **False**` (0/9 kịch bản đạt ≤200 ngày trong
ngân sách ≤50% lệnh loại).

## KẾT LUẬN CHO MASTER

**(i) Bản chất nguồn UW-2025**: KHÔNG khớp gọn với 1 trong 2 giả thuyết ban đầu.
- KHÔNG phải "concurrency-cao-trong-chop" kiểu ĐỘT BIẾN (Q3: exposure 2025 chỉ cao hơn baseline
  riêng của T100 khiêm tốn 8-25%, không phải bùng phát; concurrency cao là đặc tính CẤU TRÚC luôn
  có của gate-1.0, không phải biến MỚI của 2025 — 2022 có exposure tương đương nhưng giá SỤP,
  2025 giá TĂNG).
- KHÔNG phải "model-drift-alpha" cổ điển (Q4: hit-rate marginal ổn định 5 năm, T170/core làm rất
  tốt 2025 — năm tốt thứ nhì).
- **PHÁT HIỆN THỰC SỰ**: 2025 (Mar-Oct) là một **BULL RUN CÓ SÓNG LỚN** (BTC +33%, range đỉnh-đáy
  57%, chop_ratio 1.7, vol năm hoá 35.6%) — MA200 gọi đúng là uptrend nên gate lỏng (T100 luôn
  1.0, R hầu như luôn 1.0) admit đầy đủ lệnh biên; trong chế độ "uptrend-nhiễu" này, nhóm
  **marginal** (đã LUÔN chiếm khối lượng lớn nhờ exposure cấu trúc cao của gate-1.0) bị **NÉN
  BIÊN ĐỘ LỢI NHUẬN mỗi-lệnh** (không phải nén hit-rate) đủ để không bù được khối lượng, tạo
  chuỗi dưới nước 227 ngày dù không ngày nào sụp thực sự (đáy chỉ −9.2%, nông hơn nhiều so 2022's
  −16.1%). Đây là dạng **"nén alpha-biên theo chế độ thị trường (bull-nhiễu-sóng-lớn)"**, khác cả
  concurrency-thuần lẫn drift-thuần — gần với "khác" hơn là khớp gọn 1 trong 2 nhãn MASTER đưa ra.

**(ii) Ước lượng bàn giấy**: CONC_CAP (count hoặc notional, áp dụng đều không điều kiện regime)
**KHÔNG có tiềm năng rõ** kéo UW-2025 về ≤200 ngày — 0/9 kịch bản đạt, kịch bản chặt nhất còn
PHẢN TÁC DỤNG, và mọi kịch bản đều cắt tràn lan (chỉ 14-18% số lệnh bị cắt thực sự nằm trong cửa
sổ 2025). Kết quả này nhất quán với (i): vì exposure không phải biến bất thường ĐẶC THÙ của 2025,
một ngưỡng cắt cứng-đều-toàn-kỳ không thể "nhắm" đúng vấn đề.

**(iii) Khuyến nghị: NO-GO cho CONC_CAP đơn giản/không điều kiện regime** — bằng chứng bàn giấy
đủ mạnh (9/9 FAIL, kịch bản chặt nhất phản tác dụng) để không cần tốn sim thật kiểm chứng riêng
hướng "regime-gate + CONC_CAP kết hợp" như đề xuất ban đầu, vì phần CONC_CAP của tổ hợp đó đã cho
thấy không có cửa thắng ở dạng đơn giản. KHÔNG phải NO-GO tuyệt đối cho toàn bộ hướng breadth:
nguồn gốc thật là nén ROI-biên THEO CHẾ ĐỘ (bull-nhiễu-sóng-lớn), không phải khối lượng hay drift
vĩnh viễn — nếu muốn tiếp tục (PREREG riêng, ngoài phạm vi nhiệm vụ này), hướng khả dĩ duy nhất
còn lại là một **lớp regime THỨ HAI đo "chop/whipsaw-trong-uptrend"** (vd range/net-move ratio,
realized-vol so lịch sử — KHÔNG PHẢI MA200-hướng, vì MA200 gọi đúng đây là uptrend) để hạ
gate/giảm nhận biên ĐÚNG lúc thị trường vào chế độ sóng-lớn dù đang uptrend; nếu chi phí thiết
kế+sim vòng đó không đáng, khuyến nghị ĐÓNG hướng breadth-toàn-kỳ và chuyển TASK D (alpha mới).
**Cảnh báo T170 live**: KHÔNG cần cảnh báo drift alpha (T170/core vẫn khỏe 2025) — nhưng NÊN LƯU
Ý "bull-nhiễu-sóng-lớn" là một CHẾ ĐỘ THỰC có thể tái diễn; nếu sau này mở rộng breadth (hạ gate),
cần theo dõi chỉ báo range/chop chứ không chỉ MA200-trend.

## Phụ lục — code/data

- `docs/PREREG_UW2025_DIAG.md` (commit `84ba4ac`, khoá định nghĩa/công thức/ngưỡng TRƯỚC khi
  tính số).
- `research/analysis/uw2025_source.py` (mới, ~314 dòng): tái dùng nguyên văn
  `uw_streaks`/`btc_daily_regime`/`regime_summary`/`label_core_marginal`/`date_to_ms_utc` của
  `uw_source.py`, `hourly_grid`/`build_bd_flags`/`load_universe_breadth`/`equity_at_grid`/
  `block_boot_mean`/`load_trades_utc` của `bigdown_struct.py`, `sum_notional_on_grid` của
  `hedge_overlay_a.py`, `trades`/`equity` của `c3_rates.py` — KHÔNG sửa 4 file gốc. Hàm MỚI:
  `market_env_window` (Q2, các chỉ số realized_vol/range/chop_ratio/sign_flips/breadth mới),
  `concurrent_series`/`exposure_stats` (Q3), `year_quality`/`year_quality_marginal` (Q4),
  `retroactive_cap` (Q5, counterfactual thô).
- `research/analysis/out/uw2025_source.json` (đầy đủ số).
- Dữ liệu đọc: `printDone.csv`/`sim.out` của `X1_GS_T170_2021` (T170), `X1_C3_FULL_2021` (T100/
  gate-1.0), `X1_C3_FULL_2021_REGIME_R` (R) + `CLOSES_1H.bin` (breadth universe). KHÔNG chạy sim,
  KHÔNG xgboost, KHÔNG build, KHÔNG đụng shadow-c3, KHÔNG dữ liệu sau 2025-12-31.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
