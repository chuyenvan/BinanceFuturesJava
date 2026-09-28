# PRE-REG — P6: ARM A2 KHỚP SIZE (khử confound size) — **CHỐT TRƯỚC**

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Chốt TRƯỚC khi chạy.**
**Nguồn gốc:** `docs/result/RESULT_EXIT_STRUCT.md` (commit `12313b3`) §6 "HẠN CHẾ": confound size —
`DCA_GRID_ENABLED=false` đồng thời TẮT hệ số `DCA_GRID_SCALE=6,0` ⇒ A2/A3 chạy ~1/6 size so với A0.

## 0. CÂU HỎI DUY NHẤT

Sau khi **khớp size lên A0**, A2 (bỏ time-stop 168h + DCA tới chết) còn **kém hơn** A0 không, và
A2 có **PASS rào (a) `%top-1 ≤ 15 %`** / **(b′) bỏ top-50 % > 0** không? ⇒ **Kết luận cũ (FAIL) có giữ không?**

## 1. KEY SIZE + HỆ SỐ (đo, không đoán)

- Key: **`SIM_F_BASE`** → `Configs.F_BASE` (`src/main/java/com/binance/chuyennd/tradecore/Configs.java:864`
  đọc; khai báo `:155` default `0,03f`). Profile nền `x1_gs_t170` **KHÔNG khai** ⇒ chạy `0,03`.
- Công thức size (`TradeUtils.managerBudget:142`): `budget = equity × F_BASE × clamp(1−U/U_MAX) / dcaGridTotalWeight()`.
  Nhánh grid (`SimulatorMarketLevelTicker1MStopLoss.java:1435-1442`) nhân thêm
  `DcaUtils.gridLegWeightRatio = w[leg] × DCA_GRID_SCALE` (`DcaUtils.java:62`, `FIX_B2=true` trong profile).
- Với `DCA_GRID_WEIGHTS=1,1,1,1` (ladder = 4) và `DCA_GRID_SCALE=6,0`:
  A0 leg bất kỳ = `equity×F_BASE×throttle/4×6 = equity×0,045×throttle`;
  A2 (grid OFF) = `equity×F_BASE×throttle/4 = equity×0,0075×throttle` ⇒ **đúng 6,0×**.
- ⇒ **Hệ số chốt: `SIM_F_BASE = 0,18 = 0,03 × 6`.** (Sẽ **đo lại** `margin TB/leg` của A2size vs A0 và **báo cáo
  cả hai** chiều: per-leg và portfolio `gross` — vì `throttle` phi tuyến nên 6× danh nghĩa ≠ 6× thực.)

## 2. CHÂN CHẠY (1 chân Kaggle, tái dùng jar)

- tag **`xs-a2s6`** = A2 (`SIM_LOSER_TIME_STOP_HOURS=0` + `DCA_GRID_ENABLED=false`) **+ `SIM_F_BASE=0,18`**.
- Nền `sel15`: `profile=x1_gs_t170`, `DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6,0`, `SIM_ENTRY_SAMPLE_MIN=15`.
- Jar **TÁI DÙNG** `sim-jar-cadence` sha256 `43888ebd…` — **KHÔNG sửa code, KHÔNG build lại**.
- Bundle `sim-x1-2021-bundle`, `sim_end=20251231`, `ticker_min_days=1826`. **DEV ≤ 2025-12-31, KHÔNG chạm 2026.**

## 3. LUẬT CHẤM (nguyên văn bộ chuẩn đã dùng, KHÔNG đổi)

- Đối chiếu 3 cột: **A0** (`cd-sel15`, dùng lại) · **A2 gốc** (`xs-a2`, dùng lại) · **A2size** (`xs-a2s6`).
- **Rào (a)** `%PnL top-1 % ≤ 15 %` · **rào (b′)** `bỏ top-50 % > 0`. Chấm **cả hai không gian**:
  USDT (`pnl`) và **size-neutral** (`pnl/margin`).
- **4 thước chuẩn** `wl_ratio(asym) · tf_5 · loss_mean · conc_5` + rate `{TSloss% · mP|SM · mP|SL · mMargin}`
  + CI vs A0 (block-72h, 2000 rep, seed `20260905`, `inflate(k=3)`) + **rào cũ** `--appetite latest`
  (maxDD≤40 · UW≤250 · qmin≥−20 · 0 năm âm · conc≤15 %) + **3 chỉ số martingale**.
- **`gross`** = định nghĩa MỚI cụm ledger (`research/analysis/size_count_score.py::gross`): `100 × Σ_t (Σmargin_mở(t)/E_ngày(t))·Δt / Σ_t Δt`
  (TB theo thời gian) và `MAX`. Neo đối chiếu: A0 = **1,74 % / 49,53 %** (`RESULT_GROSS_ASYMMAP.md`).
- **Phí:** sim đã gồm `RATE_FEE 0,002/chân + SLIPPAGE 0,003/chân` (≥ 0,006 chuẩn) ⇒ **không thêm phí**.

## 4. ĐỌC KẾT QUẢ NHƯ THẾ NÀO (chốt trước, chống diễn giải sau)

1. **Khớp size đạt hay không:** so `margin TB/leg` A2size vs A0. **Nếu lệch > 1,25×** ⇒ ghi rõ "khớp size KHÔNG đạt"
   và **không** kết luận như thể đã khử confound.
2. **Còn kém A0 không:** `dCAGR` (CI vs A0) và `%top-1` / `(b′)`. Nếu `dCAGR < 0` **ra ngoài CI** ⇒ kém **có ý nghĩa**.
3. **Rào (a)/(b′):** tính lại nguyên văn; A2 gốc đã biết **FAIL cả hai** ((a) 16,10 %; (b′) −4.622 USDT).
   - Nếu A2size **PASS (b′)** thì **phải** kiểm: có phải chỉ nhờ size lớn hơn nhân cùng tỷ lệ ⇒ xem cột size-neutral.
4. **Cảnh báo sẽ phải nêu:** ở 6× danh nghĩa, `gross_MAX` A2size **có thể vượt `U_MAX=0,60`** ⇒ lệnh bị chặn
   (`managerBudget` trả `null`) ⇒ `n` đổi. **Đây là hệ quả thật, phải báo cáo**, không được coi là lỗi.
5. **Kết luận "FAIL/kém hơn" chỉ giữ được** nếu nó còn đúng khi (i) size đã khớp trong khoảng 1,25×, **hoặc**
   (ii) số size-neutral vẫn xấu hơn A0 rõ rệt.

## 5. RÀNG BUỘC

`git push` được phép. **KHÔNG** chạy Java/sim trên Oracle (Kaggle) · **KHÔNG** chạm production/242/ONNX/LIVE ·
**KHÔNG** push file dữ liệu · `/` đầy 94 % ⇒ file NHỎ · output tool NHỎ · commit sớm + push.
