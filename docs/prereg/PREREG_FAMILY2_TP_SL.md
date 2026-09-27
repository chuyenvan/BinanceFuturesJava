# PREREG_FAMILY2_TP_SL — HỌ MỚI #1: BỎ MÁY SINH-ĐUÔI (TP nhỏ + SL nhỏ, KHÔNG DCA)

**Ngày chốt:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC khi chạy sim · **KHÔNG push**
**Nguồn chỉ hướng (đã chốt, KHÔNG đo lại):** `RESULT_SHAPE1_EARLY_CUT` (`3b8b0d4`) 0/4 PASS (a)+(b′);
`RESULT_GROSS_ASYMMAP` (`42a48cd`) quét 461 run ⇒ PASS(a)=3/461 · PASS(b′)=0/461 · cả hai=0;
`asym<1` luôn kèm lỗ ⇒ **trong HỌ hiện tại (arm +7% → trailing + DCA grid) KHÔNG thể đạt (a)+(b′) bằng
tinh chỉnh tham số ⇒ PHẢI ĐỔI HỌ.** Hai rào owner mô tả = một họ **PnL KHÔNG phụ thuộc đuôi**
(win-rate thấp hơn + lỗ nhỏ + KHÔNG có winner khổng lồ).

## 0. ĐỊNH VỊ VÒNG NÀY
Probe ĐẦU TIÊN của họ mới: **tắt máy sinh-đuôi** (bỏ arm/trailing, bỏ DCA) và dùng **TP nhỏ + SL nhỏ**
(mean-reversion/scalp — đối lập bản chất với trend-riding). Nền = `KEEPLEG0` + **nhịp THIẾT KẾ**
(`sel15`; code `3b6c6e9`). Baseline **`N0` = `cd-sel15`** (744 lệnh · CAGR +17,29 % · asym 3,375 ·
`%top-1` 19,13 · `TF50` −17.551) — **DÙNG LẠI, KHÔNG chạy lại**.

## 1. CÔNG TẮC (VIỆC 0 — `file:line`, đơn vị, mặc định)
| # | việc | key (profile) | field (`file:line`) | đọc env | đơn vị | mặc định |
|---|---|---|---|---|---|---|
| i | **ngưỡng ARM** | `SIM_RATE_PROFIT_STOP_MARKET` | `Configs.RATE_PROFIT_STOP_MARKET` — `Configs.java:169` | `Configs.java:842` | rate (dimensionless); arm khi `peak ≥ entry·(1+arm)` | `0.03f`; profile `x1_gs_t170` khai **`=0.07`** |
| ii | **TP (take-profit cố định)** | — | **KHÔNG CÓ FIELD/KEY NÀO** | — | — | **KHÔNG TỒN TẠI** |
| iii | **SL cứng trước arm** | `SIM_PRE_ARM_SL` | `Configs.PRE_ARM_SL` — `Configs.java:455` | `Configs.java:849` | **ÂM**; `-0.01` = cắt ở −1 %; trên `firstEntryPrice` | `0f` = **TẮT** |
| iv | **DCA OFF** | `WFO_DISABLE_DCA=1` | `Configs.WFO_DISABLE_DCA` — `Configs.java:338` | (env trực tiếp) | boolean `"1"`=tắt hẳn nhồi lệnh | `false` |
| v | **time-box lỗ** | `SIM_LOSER_TIME_STOP_HOURS` | `Configs.LOSER_TIME_STOP_HOURS` — `Configs.java:442` | `Configs.java:846` | **số GIỜ** (int); cụm chưa arm quá N giờ → đóng `min(open,close)` | `0` = TẮT; profile nền khai **`=168`** |
| — | ratchet trailing | `SIM_TS_GIVEBACK` (bắt buộc `=1`) | `Configs.java:900-903` | — | boolean; đường trailing cũ đã XÓA 2026-09-03 | — |
| — | tỉ lệ nhả đỉnh | `TS_GIVEBACK_RATIO` | `Configs.java:173` | env | rate; `gap=min(peak·ratio, maxGap)` | `0.5f` |
| — | gate look-ahead nội-nến | — | `Configs.BLOCK_INTRABAR_LOOKAHEAD` — `Configs.java:122` | — | boolean | **`true`** (⇒ nhánh `TAKE_PROFIT_DONE` chết) |

## 2. CƠ CHẾ THOÁT THẬT TRONG SIM (chứng cứ)
- `SimulatorMarketLevelTicker1MStopLoss.java:1049` `armRate = Configs.RATE_PROFIT_STOP_MARKET` (hoặc SL_ADAPT);
  `:1054` arm khi `peakPrice ≥ priceEntry·(1+armRate)`; `:1057` `updateStatusNew`; `:1058-1060` đóng **chỉ khi**
  `TAKE_PROFIT_DONE` / `STOP_LOSS_DONE` / `STOP_MARKET_DONE`; `:1062` ngược lại `updateTPSL` (ratchet).
- `OrderTargetInfoTest.java:185-243` `updateStatusNew`: khi đã arm chỉ **đặt SL trailing** (`priceSL`); nhánh
  `TAKE_PROFIT_DONE` (`:206`) nằm TRONG `if (lastPrice ≤ priceSLNew)` **sau** `if (BLOCK_INTRABAR_LOOKAHEAD) return;`
  ⇒ **BẤT HOẠT** (mặc định guard `true`).
- Mọi điểm gán `priceTP` trong sim = SL/time-stop/forced-close, KHÔNG có mốc lãi:
  `:1000` (PRE_ARM_SL) · `:1025` (LOSER_TIME_STOP) · `:1042` (COND_EXIT) · `:551` (đóng cuối kỳ tại `lastPrice`) ·
  `:892` (symbol de-list) · `:1091` (propagate trong `closeOrder`).
- `DumpConfig.java:71-72` khai thẳng: *"Trailing: đường DUY NHẤT là `TradeUtils.calRateLossDynamicBuyPNoPump`"*.
- Quét toàn bộ key `SIM_*` (`Configs.java`): **KHÔNG có key nào chứa TP / take-profit**.

## 3. ĐIỀU KIỆN ABORT (chốt TRƯỚC — không đổi sau khi thấy số)
> **NẾU KHÔNG có công tắc bật một mốc **TP cố định** (và/hoặc không tắt được arm/trailing mà vẫn còn
> đường thoát cho lệnh thắng) ⇒ DỪNG NGAY, báo BLOCKER. KHÔNG tự ý viết lại state machine.**

Lý do: họ mới định nghĩa bằng **thoát ở TP nhỏ cố định**; sim chỉ có **thoát bằng trailing** đã arm ở +7 %.
Đặt arm vô cực (armRate lớn) chỉ làm **lệnh thắng không bao giờ đóng** (không phải "TP nhỏ"); đặt arm nhỏ vẫn
là **trailing của HỌ cũ**. Cả hai KHÔNG tạo ra họ yêu cầu.

## 4. KẾT QUẢ KIỂM (VIỆC 0) — **BLOCKER**
- (i) arm **LÀ key** (`SIM_RATE_PROFIT_STOP_MARKET`) ⇒ đổi được, nhưng đổi nó KHÔNG sinh TP.
- (ii) **TP cố định: KHÔNG TỒN TẠI** ⇒ **KHÔNG thể dựng "TP nhỏ"** ⇒ **BLOCKER**.
- (iii)(iv)(v) đều là key sẵn có (SL/DCA/time-stop) — cần thiết nhưng KHÔNG đủ.
- ⇒ **KHÔNG sửa Java ⇒ KHÔNG đổi code ⇒ KHÔNG cần parity lại** (md5 `99e42b75…` KEEPLEG0 ·
  `efb793e2…` T170 giữ nguyên; xem `RESULT_EXIT_STRUCT` §0).

## 5. ARM — KẾ HOẠCH GỐC (GIỮ để tham chiếu, nay **VOID** do BLOCKER §4)
| arm | cấu hình | ưu tiên |
|---|---|---|
| **N0** | baseline `cd-sel15` (dùng lại) | — |
| **N1** | arm/trailing OFF + TP 2 % / SL −1 % + DCA OFF | 1 |
| **N2** | arm/trailing OFF + TP 1 % / SL −1 % + DCA OFF | 2 |
| **N3** | arm/trailing OFF + TP 3 % / SL −1,5 % + DCA OFF | 3 |
| **N4** | như N1 + `SIM_LOSER_TIME_STOP_HOURS=24` | 4 (cắt trước) |
> **N1..N4 VOID**: không có công tắc TP. Nếu cưỡng chế chạy thì chỉ lặp lại HỌ cũ (trailing) ⇒ vô nghĩa.

## 6. CHẤM (bộ đã chốt — giữ nguyên cho vòng sau, KHÔNG đổi)
(a) `%PnL top-1% ≤ 15 %` · (b′) `bỏ top-50 % > 0` (+ `TF50` USDT) · `asym` · `sign%` · win-rate · `q*` ·
`median`/leg · `tf_5`/`tf_10`; 4 thước chuẩn (`wl_ratio`·`tf_5`·`loss_mean`·`conc_5`); rào cũ `--appetite latest`
(maxDD≤40 · UW≤250 · qmin≥−20 · 0 năm âm · conc≤15 %) + trần gross **theo định nghĩa LEDGER** (`RULERS_CURRENT.md` §11)
+ phí 0,006; 5 rate + CI (block-72h · 2000 rep · seed `20260905` · `inflate(k)`); 3 chỉ số martingale;
**4 chỉ số họ mới**: `asym` (mục tiêu <1) · `conc_5` (thấp) · `sign%` · `mean|lỗ|` — so trực tiếp N0 vs N1..N4.

## 7. HẠN CHẾ / GHI CHÚ
- KHÔNG chạm production / 242 / ONNX / `NUM_FEATURES` / `extractFeatures45` / đường LIVE. DEV ≤ 2025-12-31, 0 sim Oracle.
- Bước kế khả thi (ngoài phạm vi vòng này, xem RESULT §4): hoặc (A) thêm **một nhánh TP cố định** vào
  `updateStatusNew`/`startUpdateOldOrderTrading` (mặc định OFF = byte-identical) — cần owner duyệt vì đụng
  state machine; hoặc (B) đổi **nhãn train** mục tiêu nhỏ / đổi **khung thời gian** / đổi **cách chọn coin**.

---

# AMENDMENT — 2026-09-27 (viết TRƯỚC khi chạy arm; KHÔNG xóa mục cũ)

**Trạng thái:** AMENDMENT này được viết **TRƯỚC** khi chạy bất kỳ arm nào (chưa fetch số arm).
**Lý do:** BLOCKER §4 cũ (`RESULT_FAMILY2_TP_SL.md` @ `372317b`) đã được **GỠ** bằng cách thêm **một key GATED**
vào đường SIM. KHÔNG có arm nào chạy trước bản amendment này.

## A1. BLOCKER đã gỡ — key mới (gated, byte-identical khi OFF)
| key | field | đơn vị | mặc định | nghĩa |
|---|---|---|---|---|
| `SIM_TAKE_PROFIT_RATE` | `Configs.TAKE_PROFIT_RATE` | rate (>0) | **`0f` = OFF** | `>0`: cum đóng khi **giá chạm `entry·(1+TP)`** |
| `SIM_TAKE_PROFIT_ONLY` | `Configs.TAKE_PROFIT_ONLY` | bool | **`false`** | `true` (chỉ khi TP>0): **BỎ arm/trailing**, chỉ còn TP + SL/time-stop |

- **KHÔNG khai / `<=0` ⇒ OFF ⇒ hành vi Y NGUYÊN (byte-identical)** — bắt buộc, đã kiểm bằng cổng parity (A3).
- Commit code: `04f4039` (nhánh `module`). Diff tối thiểu: `Configs.java` (+11 dòng) ·
  `SimulatorMarketLevelTicker1MStopLoss.java` (+24 dòng) · `tools/kaggle_sim.py` (+6, thêm `extra_env` cho
  `WFO_DISABLE_DCA` — key INFRA đọc từ env, KHÔNG đặt được qua profile; default rỗng ⇒ không đổi hành vi cũ).

## A2. ĐỊNH NGHĨA TP — CAUSAL, KHÔNG LOOK-AHEAD
- **Giá dùng:** **`priceClose` của nến 1m** (logic đóng nến như đường thoát hiện có). **KHÔNG** dùng `high`/`low`
  trong nến ⇒ tuân thủ `BLOCK_INTRABAR_LOOKAHEAD=true`.
- **Ngưỡng:** `tpLevel = firstEntryPrice·(1+TAKE_PROFIT_RATE)` (đo trên giá vào **leg đầu**, bất biến qua DCA —
  cùng mốc với `PRE_ARM_SL`). Khi `WFO_DISABLE_DCA=1` thì `firstEntryPrice == priceEntry`.
- **Giá đóng:** **= `tpLevel`** (KHÔNG BAO GIỜ tốt hơn mức TP). Vì điều kiện là `close ≥ tpLevel` (giá đã ở
  ≥ TP lúc đóng nến), bán tại `tpLevel` là **khả thi và bảo thủ** ⇒ không look-ahead.
- **Thứ tự / xung đột:** khối TP đặt **SAU** các cổng cắt lỗ (`PRE_ARM_SL` → `LOSER_TIME_STOP` → `COND_EXIT`) và
  **TRƯỚC cổng arm**: trong **cùng một nến** nếu cả SL lẫn TP cùng điều kiện ⇒ **SL thắng** (nhất quán quy ước X2
  "cổng chặt hơn thắng", không ngẫu nhiên). **TP đóng TRƯỚC trailing; trailing là FALLBACK** (đúng đề xuất mặc
  định). Status = `TAKE_PROFIT_DONE`; giá/PnL đi qua `closeOrder` như mọi đường khác (phí 0,006 + slippage sẵn có).
- `SIM_TAKE_PROFIT_ONLY=true` ⇒ cổng arm bị bỏ hẳn (`tpOnly`), cụm không bao giờ arm/trailing.

## A3. CỔNG PARITY (VIỆC 2 — chạy TRƯỚC mọi arm)
Key TP **KHÔNG khai** + jar mới (`sim-jar-tpsl`) phải khớp **CẢ HAI**:
`tp-par-kg0` → `99e42b75cf1a2142f9cd14dc72e371ba` (KEEPLEG0, n=1.085, eq=103.083) ·
`tp-par-t170` → `efb793e2468ca3a7318da0f0ad23d4fc` (T170, n=1.089, eq=111.070).
**Lệch ⇒ DỪNG NGAY, KHÔNG chạy arm nào.**

## A4. ARM (nền `cd-sel15` = KEEPLEG0 + `SIM_ENTRY_SAMPLE_MIN=15`; `N0` DÙNG LẠI)
| arm | cấu hình | ưu tiên |
|---|---|---|
| **N0** | `cd-sel15` (đã có, `md5 1317191624d316d955223311ae693228`, n=744, eq=71.718) | — |
| **N1** | `SIM_TAKE_PROFIT_RATE=0.02` + `SIM_PRE_ARM_SL=-0.01` + `WFO_DISABLE_DCA=1` | 1 |
| **N2** | `SIM_TAKE_PROFIT_RATE=0.01` + `SIM_PRE_ARM_SL=-0.01` + `WFO_DISABLE_DCA=1` | 2 |
| **N3** | `SIM_TAKE_PROFIT_RATE=0.03` + `SIM_PRE_ARM_SL=-0.015` + `WFO_DISABLE_DCA=1` | 3 |
| **N4** | như N1 + `SIM_LOSER_TIME_STOP_HOURS=24` | 4 (CẮT TRƯỚC nếu thiếu ngân sách) |

- **Ngân sách:** ≤5 slot Kaggle; chạy parity (2 chặn) trước, sau đó N1–N4 (4 chặn). **N4 cắt trước, rồi N3.**
- **k = 4** (N1..N4) cho `inflate(k)` của CI (chốt trước; nếu cắt arm vẫn báo cáo theo k=4 cho bảo thủ).
- Arm dùng **trailing còn bật** (mặc định `TP_ONLY=false`) như bảng: TP đóng trước, trailing fallback.
- 1 chặn bất thường (`n ≈ 0`, mapper <800, lệch KEEPLEG0) ⇒ **báo RÕ, KHÔNG tự đổi tham số**.

## A5. CHẤM (không đổi bộ đã chốt §6) + KỲ VỌNG ghi TRƯỚC
Chấm: (a)`%top-1≤15` · (b′)`TF50>0` · `asym` · `sign%` · win-rate · `q*` · `median`/leg · `tf_5`/`tf_10`; 4 thước
chuẩn; rào cũ `--appetite latest` + trần gross 70 % (định nghĩa LEDGER) + phí 0,006; 5 rate + CI (block-72h, 2000
rep, seed `20260905`, inflate(k=4)=1,6651); 3 chỉ số martingale. **"Dương" = equity cuối > 35.000.**

**KỲ VỌNG (ghi TRƯỚC khi thấy số):**
1. **(a):** TP nhỏ cắt winner sớm ⇒ `%top-1` **GIẢM MẠNH** so N0 (19,13) — đây là **kỳ vọng chính** của họ mới.
2. **(b′):** khó nhất. Nếu PnL vẫn dồn về đuôi thì `TF50` **vẫn âm**; kỳ vọng **TP nhỏ + bỏ DCA làm `TF50` bớt âm**
   (có thể chưa dương).
3. **`asym`:** TP nhỏ + SL nhỏ ⇒ `asym` **giảm <1** là hợp lý — **câu hỏi trung tâm là `asym<1` có ĐI KÈM PnL
   DƯƠNG hay không**. TP chốt lãi sớm ⇒ **win-rate tăng**, lỗ nhỏ ⇒ `sign%` tăng. **Rủi ro:** `TP` nhỏ < chi phí
   round-trip (~0,8 %) ⇒ các lệnh "thắng" có thể **lỗ sau phí** ⇒ PnL âm (như `RESULT_SHAPE1`).
4. **Nếu 0 arm PASS (a)+(b′) và không có `asym<1` + PnL dương** ⇒ kết luận **họ mới (phía thoát) chưa đủ**; bước
   tiếp = **đổi phía TÍN HIỆU/nhãn train** (mục tiêu nhỏ, horizon ngắn) hoặc khung thời gian / cách chọn coin.
