# PREREG_SHAPE1_EARLY_CUT — Hình dạng #1: CẮT LỖ SỚM (3 giá trị CHƯA THỬ)

**Ngày chốt:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi chạy sim · **KHÔNG push**
**Nguồn dữ liệu chỉ hướng (đã chốt, KHÔNG đo lại):** `docs/result/RESULT_GROSS_ASYMMAP.md` (`42a48cd`, quét **461 run**).

## 0. ĐỊNH VỊ VÒNG NÀY (đọc trước)

`RESULT_GROSS_ASYMMAP` (461 run) cho:
- **PASS (a)** `%PnL top-1% ≤ 15 %` = **3/461** · **PASS (b′)** `bỏ top-50 % > 0` = **0/461** · **cả hai = 0**.
- **`asym<1` có 32 run NHƯNG TẤT CẢ fail** (win-rate 29–42 %, top-1 35–96 %, `TF50<0`) ⇒ **`asym<1` + PnL dương = CHƯA TỒN TẠI (đã thử)**.
- Cấu trúc ép `asym` xuống: **win-rate thấp ≤45 %** · **cắt lỗ sớm/ngắn** (`SIM_PRE_ARM_SL=-0,03` ⇒ `asym` **0,705**) · `loss_mean` nhỏ
  (corr `asym~loss_mean` **−0,47**, `~sign%` **+0,25**).

⇒ Vòng này là **phép thử CUỐI trong HỌ chiến lược hiện tại** (arm +7 % → trailing + DCA grid).
3 giá trị dưới đây được liệt kê là **CHƯA TỪNG THỬ** (`RESULT_GROSS_ASYMMAP` §3): `PRE_ARM_SL=-0,05`; `PRE_ARM_SL=-0,03`+`K=16`; `LOSER_TIME_STOP=8h`.

### KỲ VỌNG (ghi TRƯỚC, không đổi sau khi thấy số)
- **Kỳ vọng chính:** 3 giá trị này **có thể kéo `asym` xuống <1 nhưng nhiều khả năng GIỮ/ĐẨY (a)/(b′) FAIL** — đúng như 32 run `asym<1` đã thử.
  Lý do cơ học: kênh "win-rate thấp + cắt lỗ sớm" vốn **làm `TF50` âm thêm** (bỏ top-50 % thì nửa dưới vẫn lỗ) và **tăng `%top-1`** (lãi dồn vào ít winner).
- **Phán quyết chốt trước:** **NẾU 0 arm PASS (a) VÀ (b′) ⇒ kết luận cứng: trong HỌ hiện tại KHÔNG THỂ đạt (a)+(b′) bằng chỉnh tham số ⇒ phải ĐỔI HỌ chiến lược**
  (họ mới phải có: win-rate thấp + lỗ nhỏ + **có winner không lồ**) — không phải tinh chỉnh thêm `PRE_ARM_SL`/`K`/`TIME_STOP`.
- **Ngưỡng bác bỏ kỳ vọng:** chỉ khi có **≥1 arm PASS CẢ (a) VÀ (b′)** thì kỳ vọng "phải đổi họ" mới bị bác bỏ.

## 1. NỀN (cố định, KHÔNG đo lại)

`KEEPLEG0` (= profile `x1_gs_t170` + `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0`)
+ **nhịp THIẾT KẾ** `SIM_ENTRY_SAMPLE_MIN=15` (selector 15′, BIG_DOWN/DCA 1′; code `3b6c6e9`, result `8aedde8`).
Bundle `sim-x1-2021-bundle`, jar `sim-jar-cadence`, `SIM_END_DATE=20251231`, `ticker_min_days=1826` (DEV ≤ 2025-12-31).

**Baseline `S0` = `cd-sel15` (DÙNG LẠI, KHÔNG chạy lại):** n=744 · 0,453 entry/ngày · 13,77 entry/tháng ·
CAGR **+17,29 %** · maxDD −6,27 % · UW 166 · qmin −3,36 % · conc 6,77 % · `%top-1` **19,13** · `TF50` **−17.551** (USDT) ·
`asym` **3,38** · `sign%` 88,44 · md5 `printDone.csv` = `1317191624d316d955223311ae693228`, equity 71.718.

## 2. ARM (CHỐT TRƯỚC — không đổi sau khi thấy số)

Base mỗi arm = `KEEPLEG0` + `SIM_ENTRY_SAMPLE_MIN=15` + `SIM_F_BASE=0,03` + `SELECTOR_RANK_TOPK=8` khai **tường minh**
(cổng knob `sc-par` đã chứng minh 2 knob này ở default **VÔ HẠI** — md5 = `cd-sel15`, xem `RESULT_SIZE_COUNT` §0)
+ knob arm.

| arm | thay đổi (override) | tag Kaggle | ưu tiên |
|---|---|---|---|
| **S0** | baseline `cd-sel15` (dùng lại) | `cd-sel15` | — |
| **S1** | `SIM_PRE_ARM_SL=-0.05` (K=8) | `sh1-s1-sl05` | 1 |
| **S2** | `SIM_PRE_ARM_SL=-0.03` **+** `SELECTOR_RANK_TOPK=16` | `sh1-s2-sl03k16` | 2 |
| **S3** | `SIM_LOSER_TIME_STOP_HOURS=8` | `sh1-s3-ts8` | 3 |
| **S4** | `SIM_PRE_ARM_SL=-0.03` (K=8, tách riêng tác động SL cứng) | `sh1-s4-sl03` | 4 |

**Ngân sách:** mỗi chặn ~12–22′. ≤5 slot ⇒ chạy **S1,S2,S3,S4 song song 1 lượt**.
Nếu thiếu slot/thời gian: **cắt S4 TRƯỚC**, rồi **S3** (giữ S1,S2 vì là 2 giá trị trọng tâm "chưa thử").

## 3. KNOB — XÁC NHẬN `file:line`, ĐƠN VỊ, MẶC ĐỊNH (VIỆC 1)

| knob | key | field (`file:line`) | đọc env | đơn vị | mặc định |
|---|---|---|---|---|---|
| SL cứng TRƯỚC arm | `SIM_PRE_ARM_SL` | `Configs.PRE_ARM_SL` — `Configs.java:455` | `Configs.java:849` | **ÂM**; `-0.20` = cắt ở **−20 %**; đặt trên **`firstEntryPrice`** (BẤT BIẾN qua DCA) | `0f` = **TẮT** |
| time-box lỗ | `SIM_LOSER_TIME_STOP_HOURS` | `Configs.LOSER_TIME_STOP_HOURS` — `Configs.java:442` | `Configs.java:846` | **số GIỜ** (int); cụm **chưa arm** quá N giờ → đóng tại `min(open,close)` | `0` = **TẮT** |

⚠️ **KHÁC** `TIME_STOP_HOURS` (đã **CHẾT** ở `updateStatusNew` — chỉ chạy khi `maxPrice ≥ entry·(1+RATE_PROFIT_STOP_MARKET)`, **không bao giờ chạm cụm lỗ thuần**).
Logic thuần ở `PreArmSlUtils.java:19-56`; nhánh sim ở `SimulatorMarketLevelTicker1MStopLine.java:984-1030`
(`PRE_ARM_SL` **đặt TRƯỚC** `LOSER_TIME_STOP` — cùng nến cả hai thì SL thắng).
Mặc định 0 ⇒ nhánh không chạy ⇒ **byte-identical** (parity `TẮT = y nguyên` đã có ở `RESULT_SIM_CADENCE_MATCH` §0).

## 4. CHẤM (bộ đã chốt — KHÔNG đổi)

1. **Rào (a)** `%PnL top-1 % ≤ 15 %` ⇒ PASS/FAIL (chỉ tính khi `ΣPnL>0`).
2. **Rào (b′)** `bỏ top-50 % > 0` ⇒ PASS/FAIL + **`TF50` USDT cụ thể**.
3. **`asym = mean|lỗ|/mean lãi`** · `sign%` · `q*` · `median`/leg · `tf_5` · `tf_10`.
4. **4 thước chuẩn:** `wl_ratio` · `tf_5` · `loss_mean` · `conc_5`.
5. **Rào cũ `--appetite latest`:** maxDD ≤ 40 · UW ≤ 250 · qmin ≥ −20 · **0 năm âm** · conc 1 coin ≤ 15 %.
   **Trần gross 70 % theo định nghĩa LEDGER** (errata `RULERS_CURRENT.md` §11 — `gross()` từ `margin` ledger + equity ngày; **KHÔNG** dùng `G_old[pool]`).
6. **5 rate + CI** (block-72h, 2000 rep, seed `20260905`, `inflate(k)`) vs **S0**, luật siết §10.2:
   **≥2 rate ngoài CI cùng hướng TỐT, tối đa 1 rate nhóm tần suất {win%, TSloss%}, KHÔNG tính `meanP`**.
7. **3 chỉ số martingale:** (i) **lỗ lớn nhất 1 vị thế / 1 coin (từng năm)**; (ii) **conc 1 coin có vượt 15 %**; (iii) **số coin "chết"** (coin có ΣPnL < 0).

**`k` cho inflate:** số arm so với S0 = **4** ⇒ `inflate(4) = sqrt(2·ln 4)` = **1,6651** (đồng bộ `RESULT_GROSS_ASYMMAP`).

## 5. HẠN CHẾ ĐÃ BIẾT (ghi trước)

- `gross` là **hậu kiểm** từ ledger + equity **ngày** (chưa mô hình nội ngày); `UW`/`maxDD` theo **năm**.
- CI rate: `mP|SM`/`mP|SL`/`mMargin` **nhân theo size** (USDT) ⇒ phần lớn chênh là **artifact**; chỉ `win%`/`TSloss%` là so sánh sạch.
- Không sửa Java ⇒ không cần parity lại (chỉ cần cổng knob đã có).
