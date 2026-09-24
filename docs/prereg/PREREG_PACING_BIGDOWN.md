# PREREG_PACING_BIGDOWN — TASK B: hạ gate 1.70→1.0 + pacing bigdown (2026-09-21)

> Pre-register TRƯỚC khi build/chạy bất kỳ biến thể nào. KHÔNG sửa file này sau khi thấy số
> (AGENT_RUNBOOK §0.2). Khung nguồn: `TASK_B_pacing_bigdown_design.md` (MASTER, 2026-09-21, Uni đã
> chọn hướng "Hạ gate + pacing bigdown"). Đầu vào đã đọc: `docs/analysis/ANALYSIS_BIGDOWN_STRUCT.md`
> (`dc63488`), `docs/analysis/RECON_ADMISSION_PACING.md` (`4268254`), `docs/result/RESULT_VOL_TARGET.md`, project
> memory `round_2026-09-20_beta_decomp_and_data_survey.md` (mục TASK A + A-recon).

## 0. Luật (không nới, xem AGENT_RUNBOOK §0 + khung thiết kế §0)

An toàn: KHÔNG HOLDOUT 2026 (`SIM_END_DATE=20251231` giữ nguyên, không đụng seal); KHÔNG ssh 242;
KHÔNG `git push`; KHÔNG xoá thư mục bảo vệ. Job nặng 1 sim/lần: trước MỖI sim kiểm `free -g`
available ≥12G VÀ `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"` rỗng VÀ `pgrep java` rỗng —
`shadow-c3` đang chạy (java) nên **`sudo systemctl stop shadow-c3` TRƯỚC chuỗi sim**, **`sudo
systemctl start shadow-c3` NGAY SAU** khi chạy xong toàn bộ chuỗi, verify active + log sạch. Cổng
OFF byte-identical bắt buộc cho flag pacing mới. Khẩu vị hiện hành: maxDD≤30, UW≤200, quý≥−15
(`x1_rates.py --appetite current --k 2`).

## 1. Giả thuyết (H_B / H0) — nguyên văn khung thiết kế §1

H_B: Hạ gate 1.70→1.0 (lấy breadth) làm risk xấu (T100 hiện FAIL: maxDD −16.13%, đồng-thua bigdown
cao). Thêm pacing regime-conditional nhắm bigdown (giảm size khi thị trường đang sập) kéo risk về
ĐẠT khẩu vị hiện hành, trong khi vẫn giữ được phần lớn breadth ⇒ `n_eff_total` tăng ≥1.5× T170 mà
maxDD/UW không thua T170 quá 25%.

H0 (NULL): pacing không kéo được risk về đạt khẩu vị ở gate 1.0; HOẶC phần cải thiện risk chỉ do
giảm size đều (P0 đạt bằng P3) chứ không do nhắm bigdown.

Rủi ro đã biết (TASK A M7): lệnh biên T100∖T170 có ROI +1.9% nhưng match_rate chỉ 32.6% — không
đáng tin để khẳng định "breadth có alpha" chắc chắn; tiêu chí t2 có CAGR floor để bắt trường hợp
breadth chỉ thêm cược nhiễu.

## 2. Thiết kế kỹ thuật (CHỐT TRƯỚC KHI CHẠY)

### 2.1 Nền

Nền gate 1.0 = **T100** (`X1_C3_FULL_2021`, profile `profiles/x1_c3_full.properties`, printDone.csv
2559 dòng đã có sẵn từ TASK A — dùng lại làm "gate 1.0 không pacing" nếu nguyên vẹn; sẽ verify lại
trước khi trích số). Baseline so sánh (không tính vào k): **T170** (`X1_GS_T170_2021`).

### 2.2 Flag mới

`Configs.SIZE_PACING_MODE` (String, `Cfg.getOr("SIZE_PACING_MODE","OFF")`): `OFF` (mặc định) | `P0`
| `P3`. Đặt trực tiếp trong file profile (giống style `SIZE_VOL_TARGET_MODE`), không phải env
`SIM_*`.

**Điểm cắm**: tầng SIZING, class mới `PacingSizing` (mẫu `VolTargetSizing`), gọi tại
`SimulatorMarketLevelTicker1MStopLoss.java` **NGAY SAU** khối `VolTargetSizing.multiplier(...)`,
**TRƯỚC** tỷ trọng DCA-grid (đúng điểm cắm 5.1 mà `RECON_ADMISSION_PACING.md` xác nhận GO — an
toàn, KHÔNG đổi tập lệnh được admit, chỉ đổi kích thước):

```java
if (VolTargetSizing.ACTIVE) { budget *= VolTargetSizing.multiplier(vtSymbol, currentTs); }

if (PacingSizing.ACTIVE) { budget *= PacingSizing.multiplier(currentTs); }
```

**Cổng bắt buộc**: khi `OFF`, `PacingSizing.ACTIVE=false` → nhánh gọi multiplier KHÔNG được thực
thi → T170 (build mới, flag mặc định OFF) phải ra md5 `printDone.csv` = `efb793e2468ca3a7318da0f0ad23d4fc`.
Đây là điều kiện PHẢI PASS trước khi tin bất kỳ số nào của P0/P3.

### 2.3 P0 — đối chứng "giảm size đều" (BẮT BUỘC)

`multiplier = P0_MULT` cố định, mọi lúc, không điều kiện regime.

**P0_MULT — tính từ dữ liệu, chốt 1 giá trị TRƯỚC khi chạy**: tỉ lệ
`median(Σnotional/equity | bigdown BD1a, T170) / median(Σnotional/equity | bigdown BD1a, T100)`,
tính bằng ĐÚNG công thức M3 của `research/analysis/bigdown_struct.py` (hourly grid, `sum_notional_
on_grid`, `equity_at_grid`, flag BD1a = BTC ret24h ≤ −5%) trên cửa sổ 2021-07-01..2025-12-31 —
khớp với số A-recon đã trích dẫn (T170 median≈0.058, T100 median≈0.27 → hệ số ~0.2). Đo lại chính
xác 2026-09-21 (`research/analysis/compute_p0_mult2.py`, TÁI DÙNG hàm của `bigdown_struct.py`, 0
sim):

| | median(Σnotional/equity \| bigdown BD1a) | n giờ bigdown |
|---|---|---|
| T170 | 0.0579653 | 1332 |
| T100 | 0.2701007 | 1332 |

`P0_MULT = 0.0579653 / 0.2701007 = 0.214603` → **chốt = 0.2146** (float, 4 chữ số thập phân, khớp
phong cách hằng số của `VolTargetSizing`).

Lý do dùng median-trong-bigdown (thay vì mean toàn kỳ, vốn bị kéo về 0 vì >50% số giờ không có vị
thế ở cả hai run — đã thử, median toàn kỳ = 0.0/0.0, không dùng được; mean toàn kỳ cho tỉ lệ khác
= 0.340, xem chú thích minh bạch bên dưới): đây đúng là con số A-recon đã trích dẫn để đề xuất "hệ
số ~0.2", và là phép hiệu chỉnh có ý nghĩa nhất cho câu hỏi t4 (so P0 vs P3 ở % depth maxDD-trong-
bigdown) — mục tiêu của P0 là mô phỏng "điều gì xảy ra nếu size luôn thấp đều đặn cỡ mức mà T170
tình cờ có trong bigdown", để so với P3 (chỉ hạ size KHI bigdown).

**Minh bạch (ghi trước khi chạy)**: một cách tính khác — tỉ lệ MEAN của Σnotional/equity trên TOÀN
BỘ 39.480 giờ lưới (không điều kiện bigdown) — cho ra 0.3404 (khác `P0_MULT` đã chốt ở trên).
KHÔNG dùng số này vì nó không khớp với con số A-recon đã trích dẫn làm cơ sở thiết kế và vì nó
không phản ánh đúng câu hỏi t4 (đo TRONG bigdown). Ghi rõ ở đây để minh bạch, KHÔNG đổi `P0_MULT`
đã chốt sau khi thấy sự khác biệt này.

### 2.4 P3 — pacing regime-conditional nhắm bigdown (CHÍNH)

`multiplier = P3_GAMMA` khi cờ BD1a causal đang BẬT, `= 1.0` khi TẮT. `P3_GAMMA = 0.5` (chốt trước,
KHÔNG quét).

**Cờ BD1a causal trong engine — xác nhận thiết kế TRƯỚC khi build**:
`MarketBigChangeDetector.getMarketStatus1M()` hiện có ĐÃ TỒN TẠI trong engine nhưng là một ĐỊNH
NGHĨA KHÁC: breadth trung bình 1-phút của ~100 coin giảm mạnh nhất trong tick đó (`rateDownAvg <
Configs.MS_DOWN_BIG_AVG`, ngưỡng riêng, per-tick, không phải BTC 24h) — dùng cho nhánh candidate
BIG_DOWN (bắt đáy DCA), KHÔNG khớp định nghĩa BD1a (BTC ret24h ≤ −5%) mà TASK A dùng làm headline.
⇒ **KHÔNG tái dùng `MarketBigChangeDetector` cho P3** — tự viết flag BD1a riêng trong class mới
`PacingSizing`, đọc giá đóng BTC từ `CLOSES_1H.bin` (dataset đã dùng cho `VolTargetSizing.COIN_MODE`
và cho chính `bigdown_struct.py`/`trend_rank_ic.py` — KHÔNG sinh dữ liệu mới), symbol `BTCUSDT`.

**Tính causal chính xác (quan trọng — phát hiện khi đọc code)**: `CLOSES_1H.bin` lưu
`(ts=open_time cây nến 1h, c=close)` (xác nhận từ `research/analysis/trend_rank_ic.py::load_closes`:
`ctime = ts + H`, tức giá đóng chỉ "biết" được tại `ts+1h`). Nếu lấy thẳng `floor(tsMs/1h)*1h` làm
mốc (như `VolTargetSizing.coinMultiplier` đang làm cho COIN mode) thì đó là giá đóng của cây nến
**ĐANG chạy, CHƯA đóng** tại `tsMs` — một dạng lookahead nhẹ (ẩn trong code đã có từ TASK 5, không
sửa ở đây, chỉ ghi nhận). Để đúng yêu cầu "tính tới t−1, KHÔNG lookahead" của khung thiết kế, `P3`
dùng nghiêm ngặt hơn: nến HOÀN TẤT gần nhất có `open_time = floor(tsMs/1h)×1h − 1h` (đóng đúng lúc
`floor(tsMs/1h)×1h ≤ tsMs`), so với nến 24h trước đó (cùng quy ước open_time). Thiếu dữ liệu (đầu
kỳ DEV, <25h lịch sử) → trả `false` (không pacing), không bao giờ NaN/lỗi.

`ret24h = close(t−1h) / close(t−25h) − 1`; BD1a BẬT khi `ret24h ≤ BD_RET24H_THRESHOLD = −0.05`
(khớp headline BD1a của `docs/analysis/ANALYSIS_BIGDOWN_STRUCT.md` mục 0).

### 2.5 Profile

`profiles/x1_c3_full_p0.properties` = `x1_c3_full.properties` + 1 dòng `SIZE_PACING_MODE=P0`.
`profiles/x1_c3_full_p3.properties` = `x1_c3_full.properties` + 1 dòng `SIZE_PACING_MODE=P3`.
`git diff` xác nhận chỉ thêm đúng 1 dòng mỗi file so với `x1_c3_full.properties`.

### 2.6 Không làm P1/P2 (tầng admission)

Theo khung thiết kế §3: chỉ P0+P3 (k=2). Không mở biến thể admission-based (P2 rate-limit) trong
vòng này — giữ đúng phạm vi đã chốt.

## 3. Tiêu chí (khoá TRƯỚC khi chạy) — nguyên văn khung thiết kế §4

Mốc T170: maxDD −11.84%, UW 92, CAGR 29.27%, n_eff_total(T170) tính bằng `bigdown_struct.py`.

- **t1 breadth**: `n_eff_total(biến thể) ≥ 1.5 × n_eff_total(T170)`. (`n_eff_total = Σ_j
  k_j/(1+(k_j−1)·ICC_ROI)`, cohort ngày ≥2 — đúng `bigdown_struct.py::n_eff`.)
- **t2 khẩu vị**: PASS toàn bộ ràng buộc hiện hành (maxDD≤30, UW≤200, quý≥−15) theo
  `x1_rates.py --appetite current --k 2`. VÀ CAGR floor: CAGR biến thể ≥ cận dưới CI-72h (k=2) của
  T170 (chặn trường hợp breadth chỉ thêm cược nhiễu làm loãng CAGR).
- **t3 risk vs incumbent**: maxDD ≥ −14.8% (không xấu hơn T170 quá 25% tương đối) VÀ UW ≤ 115.
- **t4 cơ chế đúng (then chốt P3 vs P0)**: `% depth maxDD-trong-bigdown` của P3 THẤP HƠN của P0
  (đo bằng `bigdown_struct.py::maxdd_decomp`, field `bd_share_of_maxdd_depth_pct`, áp cho sim mới).

**Phán quyết**: THẮNG = P3 đạt t1∧t2∧t3∧t4 VÀ vượt P0 ở t1 hoặc t4. NULL = không biến thể nào đạt
t1-t3, HOẶC P0 đạt ngang P3 ở t3/t4 (phần thắng chỉ là giảm size). HỖN HỢP = còn lại.

## 4. Đo — tránh confound match_rate (khung thiết kế §5)

KHÔNG dùng khoá `(sym,start)` để so tập lệnh giữa các run (M7 TASK A: match chỉ 32.6% dù chỉ khác 1
tham số). So bằng metric tổng hợp/phân phối: n_eff_total, ICC(roi,ngày), phân rã maxDD theo bigdown,
CAGR+CI, số lệnh/ngày, k̄, Σnotional/equity phân phối. Cùng cửa sổ 2021-07-01..2025-12-31, cùng
kiến trúc (Oracle ARM64).

## 5. Quy trình chạy

1. PREREG này commit TRƯỚC khi build/chạy sim.
2. Build (`mvn -o -q -DskipTests package`) sau khi `pgrep java` rỗng (dừng `shadow-c3` trước).
3. Cổng OFF byte-identical: chạy lại T170 (`x1_gs_t170.properties`, flag pacing mặc định OFF) →
   `md5 printDone.csv` phải = `efb793e2468ca3a7318da0f0ad23d4fc`. Không đạt → DỪNG, báo MASTER.
4. Verify T100 (gate 1.0 no-pacing) — dùng lại printDone.csv/sim.out cũ nếu nguyên vẹn+khớp số đã
   công bố (2559 dòng, maxDD −16.13%); nếu lệch, chạy lại 1 lần.
5. Chạy P0, rồi P3 (tuần tự, 1 JVM/lần).
6. `systemctl start shadow-c3` ngay sau chuỗi sim, verify active + log sạch.
7. Tính t1-t4 bằng `bigdown_struct.py` (mở rộng qua wrapper tái dùng hàm, không sửa file gốc) +
   `x1_rates.py --appetite current --k 2`. Bảng T170/T100/P0/P3.
8. `docs/result/RESULT_PACING_BIGDOWN.md`: 4 tiêu chí ✅/❌ mỗi biến thể + verdict + khuyến nghị. Commit
   code+doc branch `module` (KHÔNG push).

## 6. Giới hạn đã biết trước

1. `PacingSizing` dùng chính xác cùng nguồn dữ liệu BTC (`CLOSES_1H.bin`) mà `bigdown_struct.py`
   dùng để định nghĩa BD1a headline — cùng symbol, cùng file — nhưng granularity 1h (giống mọi
   phân tích TASK A), không bắt được biến động trong-giờ.
2. `P0_MULT` hiệu chỉnh trên chỉ tiêu bigdown-conditional (không phải mean/median toàn kỳ) — xem
   minh bạch ở mục 2.3; nếu quan hệ margin/equity không tuyến tính quanh `U_MAX` throttle, hệ số cố
   định 0.2146 có thể không tái tạo chính xác median 0.058 khi áp cho T100 (throttle phi tuyến ở
   gần U_MAX=0.60) — sẽ đo lại SAU khi chạy, không điều chỉnh ngược `P0_MULT`.
3. Không mở biến thể P1 (capital-availability)/P2 (admission rate-limit) — ngoài phạm vi k=2 đã
   chốt.
