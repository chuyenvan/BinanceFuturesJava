# PREREG_VOL_TARGET — TASK 5: VOL_TARGET sizing (2026-09-20)

> Pre-register TRƯỚC khi chạy biến thể COIN/PORTFOLIO. KHÔNG sửa file này sau khi thấy số
> (AGENT_RUNBOOK §0.2). Mọi số liệu kết quả nằm ở `docs/RESULT_VOL_TARGET.md` (viết SAU).

## 0. Lý do & khung nhiệm vụ

`docs/GS_WAVE1_RESULT.md` kết luận trục duy nhất còn ảnh hưởng trong sim là size/leverage,
và AGENT_RUNBOOK §4 đã ghi rõ: *"Sizing (F_BASE / U_MAX / DCA_GRID_SCALE) KHÔNG đo được trên
DEV... đây là nút RISK PREFERENCE user đặt, không phải bài toán tối ưu. ĐỪNG đốt sim run vào
đây."* — nhưng cảnh báo đó nói về việc **quét hằng số sizing để tìm CAGR/maxDD tốt hơn bằng
may rủi** (data dredging trên nhiễu single-realization). TASK 5 KHÁC về bản chất: đây là kiểm
định MỘT kỹ thuật quản trị rủi ro chuẩn ngành (vol-targeting) với đúng HAI biến thể chốt trước
(k=2), không quét thêm hằng số nào sau khi thấy số, và tiêu chí thắng/thua vẫn là RATE chất
lượng ngoài CI (không phải equity/CAGR).

**Đây KHÔNG PHẢI thử nghiệm tìm alpha.** Vol-targeting chỉnh KÍCH THƯỚC lệnh theo biến động
thực tế — nó không đổi coin nào được chọn, không đổi gate/selector/exit, không đổi lệnh nào
được vào hay ra. Dự đoán ghi trước ở mục 5.

## 1. Recon (code hiện trạng, đọc trước khi sửa)

- `BudgetManagerSimple.equityNow()` (research/BudgetManagerSimple.java:171-175): equity dùng
  làm gốc sizing = `balanceCurrent + unProfit` (compound, sau fix B3), fallback `balanceCurrent`
  nếu equity ≤ 0.
- `TradeUtils.managerBudget()` (tradecore/TradeUtils.java:78-96): công thức sizing hiện tại —
  `throttle = clamp(1 − marginRunning/equity/U_MAX, 0, 1)`, `budget = equity × F_BASE × throttle
  / dcaGridTotalWeight()`. `SIM_F_BASE` mặc định 0.03 (`Configs.java:664`), `DCA_GRID_SCALE=19.5`
  và `CAPITAL_START=35000` khai trong `profiles/x1_gs_t170.properties`.
- Call-site duy nhất áp dụng cho SIM: `SimulatorMarketLevelTicker1MStopLoss.java:~1294-1302`
  — `budget = TradeUtils.managerBudget(...)` rồi `budget *= tierMultiplier` rồi mới vào nhánh
  DCA-grid (`DcaUtils.gridLegWeightRatio`) và `BdSizeAdapt` (leg BIG_DOWN theo severity — tiền lệ
  gần nhất cho một multiplier causal-rolling áp lên `budget`, xem `tradecore/BdSizeAdapt.java`).
- `grep -rniE "\bvol(atility)?\b|\bsigma\b|\batr\b" src/main/java`: **KHÔNG có knob sizing nào là
  hàm của volatility trong đường live/sim hiện tại.** Các chỗ có "vol"/"sigma" là: (a)
  `S1FeatureLive.vol7d()` — feature CỦA SELECTOR S1 (xếp hạng coin vào lệnh, không phải sizing);
  (b) `SimulatorForcedSeller.java` — một tool RIÊNG (forced-seller detector), không dùng trong
  đường sizing T170; (c) `atrSqueeze` trong `FundingMarketFeatures` — feature export, không phải
  sizing. => Không trùng lặp với thiết kế dưới đây. **Tái sử dụng `S1FeatureLive.vol7d(double[],
  int)` nguyên văn** cho COIN mode (đã khớp `research/pipeline/feat_v2_build.py` từng dòng,
  không viết lại công thức).

## 2. Thiết kế (CHỐT TRƯỚC KHI CHẠY)

### 2.1 Flag

`Configs.SIZE_VOL_TARGET_MODE` (String, đọc qua `Cfg.getOr("SIZE_VOL_TARGET_MODE","OFF")`):
`OFF` (mặc định) | `COIN` | `PORTFOLIO`. Đặt trực tiếp trong file profile (không phải env
`SIM_*`), giống style `DCA_GRID_SCALE`/`TIER_FLAT`/`CAPITAL_START`.

**Cổng bắt buộc**: khi `OFF`, `VolTargetSizing.ACTIVE=false` → nhánh gọi multiplier trong
Simulator (`if (VolTargetSizing.ACTIVE) { budget *= ... }`) KHÔNG được thực thi (không phải chỉ
nhân với 1.0f — bỏ qua hẳn nhánh) → T170 phải ra **md5 `printDone.csv` =
`efb793e2468ca3a7318da0f0ad23d4fc`** với jar MỚI (code có thêm nhánh nhưng mặc định tắt). Đây là
điều kiện PHẢI PASS trước khi tin bất kỳ số nào của COIN/PORTFOLIO.

Vị trí nhân: **SAU `tierMultiplier`, TRƯỚC tỷ trọng DCA-grid** (`DcaUtils.gridLegWeightRatio`)
— multiplier áp cho TOÀN BỘ suất budget của cụm, mọi leg DCA sau đó ăn theo tỷ lệ ladder như cũ.
Multiplier được tính LẠI ở MỖI lần gọi `managerBudget` (mỗi entry mới VÀ mỗi leg DCA), dùng
thời điểm hiện tại của chính lần gọi đó — nhất quán với cách `tierMultiplier`/`BdSizeAdapt` đã
áp dụng (không "khoá" multiplier tại thời điểm mở cụm).

### 2.2 COIN mode

```
multiplier_coin(symbol, t) = clamp( SIGMA_REF / sigma_coin_7d(symbol, t), 0.5, 2.0 )
```

- `sigma_coin_7d(symbol, t)` = độ lệch chuẩn (ddof=1) của return 1h của CHÍNH coin đó, cửa sổ
  rolling 168h, `min_periods=84` — **công thức + code y hệt** `S1FeatureLive.vol7d(double[], int)`
  (đã dùng cho feature S1 live, khớp từng dòng với `research/pipeline/feat_v2_build.py`).
- **Causal**: giá đóng cửa 1h nạp từ `CLOSES_1H.bin` (`/home/ubuntu/java/fsrun/CLOSES_1H.bin`,
  dataset sẵn có, dùng chung với pipeline feature — không sinh dữ liệu mới). Tại thời điểm tick
  `t` (ms), chỉ dùng giờ `hourTs = floor(t / 3_600_000) × 3_600_000` — tức giờ ĐÃ BẮT ĐẦU
  (`hourTs ≤ t`), KHÔNG BAO GIỜ đọc giờ tương lai. Cửa sổ 168h tính lùi từ `hourTs`.
- **σ_REF (hằng số cố định, TÍNH TRƯỚC khi chạy variant, KHÔNG đổi sau)**: trung vị của
  `vol_7d` trên TOÀN BỘ universe lịch sử trong `CLOSES_1H.bin` (2021-01-01 .. 2026-01-01, 627
  coin, 10,283,808 ô hợp lệ sau rolling 168h/min_periods=84) — đo 2026-09-20 bằng script pandas
  độc lập (rolling std y hệt `feat_v2_build.py:55`):
  **`SIGMA_REF = 0.010657`** (return 1h, đơn vị tỷ lệ — không phải %). Các phân vị tham khảo:
  p10=0.005872, p25=0.008000, p50=0.010657 (=median, dùng làm SIGMA_REF), p75=0.014464,
  p90=0.019813, mean=0.012122.
- Kẹp `[0.5, 2.0]` — coin biến động gấp đôi trung vị bị giảm size còn 50%; coin biến động bằng
  nửa trung vị được tăng size gấp đôi. Chọn khoảng đối xứng log2 quanh 1.0, không quét giá trị
  khác.
- **Fallback = 1.0** (không đổi so với OFF) khi: coin không có trong `CLOSES_1H.bin`; thời điểm
  tra cứu nằm trước dữ liệu đầu tiên của coin (`idx < 0`) hoặc sau dữ liệu cuối; hoặc
  `vol7d()` trả NaN (thiếu warmup, < 84/168 giờ hợp lệ). KHÔNG BAO GIỜ trả null/NaN/≤0 ra ngoài.

### 2.3 PORTFOLIO mode

```
multiplier_portfolio(t) = clamp( targetDailyVol / sigma_equity_20d(t), 0.5, 2.0 )
targetDailyVol = TARGET_ANNUAL_VOL / sqrt(365)
```

- **TARGET_ANNUAL_VOL = 0.25 (25%/năm), CHỐT TRƯỚC — không quét nhiều giá trị.**
  Annualize bằng `sqrt(365)` (crypto giao dịch 24/7, không dùng 252 ngày làm việc).
- `sigma_equity_20d(t)` = độ lệch chuẩn mẫu (ddof=1) của 20 log-return NGÀY gần nhất của CHÍNH
  equity chiến lược (`BudgetManagerSimple.equityNow()`, tức `balanceCurrent+unProfit`, mark-to-
  market — cùng đại lượng dùng cho maxDD/UW), lấy từ 21 điểm equity NGÀY **ĐÃ HOÀN TẤT**.
- **Causal, không dùng ngày đang chạy**: lịch equity ngày ghi trong
  `BudgetManagerSimple.date2EquityLastVT` (`TreeMap<Long dayKey, Float equity>`, cập nhật MỖI
  lần `updateBalance()` chạy — tick giờ + tick nửa đêm — với giá trị equity MỚI NHẤT trong ngày
  đó; chỉ ghi khi `VolTargetSizing.PORTFOLIO_MODE`). Khi cần multiplier tại thời điểm `t`, lấy
  `hist.headMap(Utils.getDate(t))` — **chỉ những ngày có dayKey < ngày hôm nay** — rồi dùng 21
  điểm cuối cùng (20 log-return). Không dùng bất kỳ giá trị nào của ngày đang chạy.
- **Warmup**: cần ≥ 21 điểm ngày hoàn tất trước hôm nay; DEV bắt đầu 2021-07-01 nên ~20 ngày đầu
  chạy ở multiplier=1.0 (fallback), sau đó vào chế độ thật.
- **Fallback = 1.0** khi: chưa đủ 21 ngày lịch sử; một trong các equity ≤ 0 (không nên xảy ra
  trong DEV này); `sigmaDaily` NaN hoặc ≤ 0.

### 2.4 Số biến thể & kỷ luật chống data-dredging

- **k = 2**: đúng hai biến thể COIN và PORTFOLIO, chấm bằng `x1_rates.py --k 2 <BASELINE> <VARIANT>`
  (gọi 2 lần, mỗi lần 1 variant so T170 — baseline không tính vào k, đúng quy ước
  `docs/AUDIT_CI_INFLATE_STANDARDIZATION.md`).
- **CẤM** mở thêm biến thể thứ 3 (khác σ_REF, khác target-vol, khác cận clamp) sau khi thấy kết
  quả của COIN/PORTFOLIO, kể cả khi cả hai NULL/THUA. Nếu muốn thử tham số khác, phải là một
  pre-reg MỚI, round MỚI.

### 2.5 Rào cứng theo năm (khẩu vị MỚI, `docs/RISK_APPETITE.md`, chốt 2026-09-16/17)

`maxDD` (theo năm) ≤ 30% · `UW` ≤ 200 ngày · năm không âm · quý xấu nhất ≥ −15% · tập trung
1 coin ≤ 15% equity. Luật thắng: ≥2/4 rate chất lượng (win%, TSloss%, meanP, mP|SL) ngoài CI
**cùng hướng tốt** VÀ PASS rào cứng mọi năm ⇒ THẮNG. ≥2 rate hướng xấu ⇒ THUA. Còn lại ⇒ NULL.
Equity/CAGR chỉ báo cáo, không phải tiêu chí.

> Lưu ý: `research/analysis/x1_rates.py` in bảng `hard_by_year()` bằng ngưỡng CŨ hard-code
> (`HARD_DD=15, HARD_UW=120, HARD_Q=-5`) — script CHƯA cập nhật theo `RISK_APPETITE.md`. Số thô
> (`maxDD%`, `UW`, `quy_min%`) in ra vẫn đúng; PASS/FAIL trong `docs/RESULT_VOL_TARGET.md` được
> TỰ chấm lại bằng ngưỡng MỚI (30/200/-15) từ các số thô đó, không dùng cột PASS/**FAIL** in sẵn
> của script.

### 2.6 Metric phụ (báo thêm, không phải tiêu chí quyết định)

- `sd(return ngày)` — độ lệch chuẩn log-return ngày của equity, toàn cửa sổ DEV.
- Calmar ratio = CAGR / |maxDD| (toàn cửa sổ, maxDD lấy từ chuỗi equity).
- CV (coefficient of variation) của ROI theo quý = `sd(quarterly_return) / mean(quarterly_return)`.

## 3. Dự đoán ghi trước (MASTER, chép nguyên văn — KHÔNG đổi sau khi thấy số)

> "NULL ở các rate chất lượng chuẩn (win%, TSloss%, meanP, mP|SL) — đúng vì sizing không làm đổi
> lệnh nào được chọn vào/ra, chỉ đổi kích thước. Kỳ vọng cải thiện ở maxDD/UW/CV — đây là CẢI
> THIỆN RỦI RO, KHÔNG PHẢI bằng chứng alpha, phải ghi rõ như vậy trong RESULT."

## 4. Baseline & cổng repro bắt buộc

Incumbent: `profiles/x1_gs_t170.properties` (`SIM_GATE_DYN_SCALE=1.70`), devrun
`/home/ubuntu/java/devrun/X1_GS_T170_2021`, md5 `printDone.csv` =
`efb793e2468ca3a7318da0f0ad23d4fc` (n=1089, equity 111.070, CAGR 29.27%, maxDD −11.84%, UW 92). Dataset:
`/home/ubuntu/wfo_ds_x1_2021` (WFO_DATA_DIR), ticker `/home/ubuntu/java/simulator/kaggle_data_hpo`
(symlink `kaggle_data_hpo` trong mỗi thư mục run), `SIM_END_DATE=20251231`,
`configs/sim_dev_file_2021.properties`, `-Xmx16g`.

**Cổng OFF byte-identical PHẢI PASS trước khi chạy/tin COIN hoặc PORTFOLIO** (mục 2.1).

## 5. Kế hoạch chạy (tuần tự, 1 job JVM/lần, kiểm `free -g`≥12 và `pgrep` rỗng trước mỗi run)

1. `X1_GS_T170_2021_VT_PARITY` — profile `x1_gs_t170.properties` KHÔNG sửa (flag mặc định OFF
   qua code default, không cần khai trong profile) → so md5 với `efb793e2468ca3a7318da0f0ad23d4fc`.
2. `X1_GS_T170_2021_VT_COIN` — profile clone `x1_gs_t170_vt_coin.properties` (base + 1 dòng
   `SIZE_VOL_TARGET_MODE=COIN`).
3. `X1_GS_T170_2021_VT_PORTFOLIO` — profile clone `x1_gs_t170_vt_portfolio.properties` (base + 1
   dòng `SIZE_VOL_TARGET_MODE=PORTFOLIO`).
4. Chấm điểm: `python3 research/analysis/x1_rates.py --k 2 X1_GS_T170_2021_VT_PARITY
   X1_GS_T170_2021_VT_COIN` và tương tự cho PORTFOLIO (baseline dùng lại PARITY vì nó là bản
   T170 byte-identical, đứng vai trò A=T170 gốc).
5. Ghi `docs/RESULT_VOL_TARGET.md`, commit sau khi có đủ số.
