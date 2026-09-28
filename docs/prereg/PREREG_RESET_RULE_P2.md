# PREREG_RESET_RULE_P2 — SIM KAGGLE k=5 (R0–R4, nhịp 1') @`base 0,112` và `stress 0,150` (%/vòng)

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-28 (D3, `PLAN_OPENCLAW_ADDENDUM_20260928.md` §D3).
Nhánh `module`, HEAD `a7016b0`. Nguồn yêu cầu: `Claude outputs/PLAN_OPENCLAW_BASELINE_RESET_20260928.md` **§Phase 2**.
Chi phí: `docs/result/RESULT_COST_TRUTH.md` (D1, `d059cc3`) ⇒ `base 0,112` / `stress 0,150` / `legacy 0,800` (%/vòng).
Công cụ chấm: `research/analysis/reset_rule_score.py` (D2, **dùng lại NGUYÊN, không viết lại**) + **luật 4 tầng** (`RESULT_RESET_RULE_P1.md` §4).

Ràng buộc cứng: **sim chạy TRÊN KAGGLE** (KHÔNG Java/sim trên Oracle) · KHÔNG chạm production/`242`/ONNX/LIVE ·
KHÔNG push file dữ liệu · **DEV ≤ 2025-12-31** · không sửa Java (mọi knob đã có; nếu phải sửa ⇒ key gated + parity 2 md5 + báo trước) · output tool nhỏ.

---

## 0. MỤC ĐÍCH (1 câu)

Chạy **5 arm KHOÁ TRƯỚC** (R0–R4, tất cả nhịp **1'**, nền `KEEPLEG0 + CONC_CAP 15%`, chỉ đổi knob có sẵn
`SIM_F_BASE` / `SELECTOR_RANK_TOPK` / `SIM_GATE_DYN_SCALE`) trên **cùng cửa sổ DEV 2021-07-01..2025-12-31** ở **2 mức phí**
`base 0,112` và `stress 0,150` (%/vòng), rồi chấm bằng **công cụ D2** theo **luật 4 tầng**, để trả lời dứt khoát:
**có arm nào qua CẢ 4 TẦNG không — nếu không, giữ `B*`.**

---

## 1. 5 ARM (khoá trước — GỒM mốc `B*` = R0)

Nền chung MỌI arm: `KEEPLEG0` (`DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0`) + `CONC_CAP_PERCOIN_ENABLED=1`,
`CONC_CAP_PERCOIN_PCT=0.15`, nhịp 1' (`SIM_ENTRY_SAMPLE_MIN=1` ≤1 = no-op). Profile trong bundle: `x1_gs_t170`.

| arm | `SIM_F_BASE` | `SELECTOR_RANK_TOPK` | `SIM_GATE_DYN_SCALE` | ý nghĩa |
|---|---|---|---|---|
| **R0** | 0.03 (×1) | 8 | 1.70 | = `B*` (parity **md5 `99e42b75`** ở cost legacy) |
| **R1** | 0.015 (×0,5) | 16 | 1.70 | B2 ở nhịp 1' |
| **R2** | 0.015 (×0,5) | 32 | 1.70 | B4 ở nhịp 1' |
| **R3** | 0.0099 (×0,33) | 24 | 1.70 | "giảm margin ~3×" của owner |
| **R4** | 0.015 (×0,5) | 16 | 1.55 | kiểm 1 bước nới gate nhẹ khi đã phân tán |

## 2. CHI PHÍ (KHÔNG sửa Java — key có sẵn: `Configs.java:901-902`)

`total = RATE_FEE + 2·SLIPPAGE_RATE`. Chốt **TRƯỚC**:

| mức | `SIM_RATE_FEE` | `SIM_SLIPPAGE_RATE` | total (%/vòng) |
|---|---|---|---|
| **base** | 0.000982 | 0.000067 | **0,1116** |
| **stress** | 0.000982 | 0.000259 | **0,1500** |
| **legacy** (chỉ parity R0) | (không khai) | (không khai) | 0,800 (2·0.003+0.002) |

**10 run** = 5 arm × 2 mức phí, **+ 1 run R0 ở legacy** để xác nhận parity (tổng 11). Chạy Kaggle, song song trong hạn mức slot.

## 3. CÔNG CỤ & KHOÁ ĐO (khoá trước)

Cùng `research/analysis/reset_rule_score.py` (D2) — **dùng lại nguyên**: `core_metrics` (equity/CAGR/maxDD/q*/top-1%/episode/gross/conc),
`ci_pair` (bootstrap khối-72h paired), `run_mtm` (maxDD/UW **MTM phút** từ ticker 1m, khung `intraday_dd.py`), `tier1..tier4`.
**Khác P1 duy nhất ở tham số khoá:** `k = 5` ứng viên ⇒ **`inflate(5) = sqrt(2·ln 5) = 1,7941`**;
`SEED = 20260905`, `NREP = 2000`, block **72 h**; ngưỡng tầng giữ nguyên.
Vì arm nay là **artifact THẬT ở đúng mức phí** (không hậu kiểm tuyến tính): mỗi mức phí chấm trên **artifact của chính mức đó**
(driver gọi công cụ D2 ở chế độ "as-is", `cost = legacy 0,008`, tức KHÔNG hiệu chỉnh lại pnl).

`B*` để so **tầng 3/tầng 4** = **R0 ở CÙNG mức phí** (R0-base khi chấm base; R0-stress khi chấm stress),
vì tầng 3 (`win%`/`TSloss%`/`mP|SM`/`mP|SL` trên `profit` %) và sizing đều theo mức phí của chính run.

## 4. LUẬT 4 TẦNG (y nguyên PLAN §3)

- **TẦNG 1 — RÀO RỦI RO:** maxDD **MTM phút** năm xấu nhất **≤ 40 %** · `UW ≤ 250` ngày · quý xấu nhất **≥ −20 %** ·
  **0 năm âm** · `conc/coin ≤ 15 %` · `gross ≤ 70 %`.
- **TẦNG 2 — RÀO ĐỘ BỀN:** `q* ≥ 15 %` · `%PnL top-1 % ≤ 25 %` · **bỏ top-3 EPISODE** (ngày có lệnh, nối khoảng trống ≤ 2 ngày) ⇒ ΣPnL **> 0**.
- **TẦNG 3 — NON-INFERIORITY vs `B*`** (CI khối-72h, 2000 rep, seed `20260905`, `inflate(5)=1,7941`):
  `win%` không kém quá **−2,0 pp** · `TSloss%` không tệ quá **+2,5 pp** · `mP|SM%` và `mP|SL%` **không tệ ngoài CI** (CI hiệu hoàn toàn < 0 = kém có ý nghĩa). KHÔNG tính `meanP`.
- **TẦNG 4 — MỤC TIÊU (điểm):** `Calmar_MTM = CAGR/|maxDD MTM phút|` ≥ `B*` **VÀ** `n ≥ 1,3×n(B*)` **VÀ** `conc/coin ≤ B*`.

**LUẬT KẾT LUẬN (chốt trước):** arm qua **cả 4 tầng** ⇒ ứng viên; nhiều arm qua ⇒ chọn `Calmar_MTM` cao nhất (hoà ⇒ `n` lớn hơn).
**Không arm nào qua cả 4 tầng ⇒ GIỮ `B*`.** Chỉ báo cáo, không mở biến thể quanh arm thắng (chống dredging).

## 5. KIỂM HỢP LỆ (cổng DỪNG — bắt buộc trước khi chấm)

1. **Parity R0 @legacy:** `md5(printDone) = 99e42b75` và `n = 1085`, `equity_final = 103083` (khớp `kg0-g170`/`FG_KEEPLEG0`).
   Lệch ⇒ **DỪNG**, không chấm.
2. **Neo Kaggle:** Kaggle luôn `TICKER_SOURCE=file` ⇒ neo riêng của cửa sổ này là `kg0-g170` (`md5 99e42b75`, equity `103083`),
   **không** dùng neo `c2b_min 60395` (profile/cửa sổ khác — chỉ nhắc để không lẫn). Mọi so sánh tin ~0,01 %.
3. **`gross MAX < U_MAX = 0,60`** ở MỌI arm (⇒ throttle `clamp(1−U/U_MAX)` ≈ 1, `U_MAX` KHÔNG bind ngầm); **báo số lệnh bị chặn**
   (`[CONC-PC] SUMMARY blocked=` + `[GATE] n_cand/n_pass`).

## 6. DỰ BÁO GHI TRƯỚC (đối chiếu, KHÔNG sửa sau)

1. `B*` = R0 qua tầng 1–2 (đã biết: MTM phút −19,96 %, `q*` 19,0 %, `top-1` 23,74 %, `conc` 7,12 %, 0 năm âm).
2. **R1/R3 qua tầng 1–3**, `n ×1,4–2,2` so `B*`, `Calmar_MTM ≈ B* ±15 %`.
3. **R2 rủi ro `UW > 250`** (K rộng ⇒ nhiều vị thế ⇒ đuôi dưới đỉnh dài).
4. **R4 FAIL tầng 3** (nới gate 1.70→1.55 khi đã phân tán K=16 ⇒ chất lượng leg biên kém hơn `B*`: theo D2, bước 1.55 vẫn non-inferior trên nền KEEPLEG0 K=8, nhưng ở đây K rộng hơn ⇒ kỳ vọng vượt trần `win% −2,0 pp` / `TSloss% +2,5 pp`).

## 7. OUTPUT

`docs/prereg/PREREG_RESET_RULE_P2.md` (file này) · `docs/result/RESULT_RESET_RULE_P2.md` + `docs/result/reset_rule_p2.json`
· driver mỏng `research/analysis/reset_rule_p2_driver.py` (chỉ gọi lại hàm của công cụ D2). Commit + push (chỉ code/doc; KHÔNG push dữ liệu).
