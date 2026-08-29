# Arm-sweep dừng: phát hiện WFO không optimize + cơ chế arm đúng (2026-08-20)

## TL;DR
Định sweep arm (TS_PROFIT_MULTIPLIER) qua Kaggle WFO full-18w K=8. Attempt đầu **sai cơ chế + hỏng jar**, đã dừng và revert sạch. Trong lúc debug lộ 3 sự thật quan trọng hơn cả arm.

## 3 phát hiện (theo thứ tự quan trọng)

### 1. WFO KHÔNG optimize — nó eval config frozen
Report K-grid K8 (`REPORT_G015K8v26b.md`, mục "Độ ổn định gene qua cửa sổ") cho thấy **cả 17 gene đều min==max**, đứng đúng default Configs qua cả 18 window:
- TS_PROFIT_MULTIPLIER: 5.2185 .. 5.2185 (= live frozen 5.21847)
- RATE_PROFIT_STOP_MARKET: 0.0500 .. 0.0500 (kịch trần range [0.03,0.05])
- MIN_MOMENTUM_15M 0.0080, TS_DYNAMIC_K 0.2977, ... tất cả = default.

Nguyên nhân: mọi window `IS_fit ≈ -100000` (= -vốn ban đầu, oosNote `TOO_MUCH_CAPITAL_LOCK`/`BURN_ACCOUNT`). Fitness in-sample phẳng → HPO không phân biệt được candidate → trả về seed=default. **"HPO trong WFO" thực chất non-functional với config hiện tại.**

Hệ quả: mọi kết luận WFO lâu nay (K-grid, gate, v.v.) là **walk-forward EVAL của config frozen**, arm cố định 26% = live. Không có per-window tuning. → Arm CHƯA TỪNG được thử giá trị khác. Instinct sweep arm là đúng; WFO không tự làm hộ.

### 2. Verdict K8 thật ra là ❌ FAIL/REVIEW
Bảng ngưỡng pre-registered: WFE_median≥0.5, %OOS-dương≥70%, maxDD≤50%.
K8 thực tế: WFE median **0.325** (<0.5 → overfit-ish), %OOS-dương 88.9% (16/18, nhưng strict=0%), maxDD 25.7%. 2 window BURN_ACCOUNT (w12 -2450, w14 -319). "K=8 optimal" trước đây chỉ đúng trên tổng PnL (FULL_18w/TOTAL_12w), KHÔNG đúng trên metric ổn định.

### 3. Cơ chế arm đúng (cho sweep sau này)
`arm = TS_PROFIT_MULTIPLIER × RATE_PROFIT_STOP_MARKET`. Trong WFO cả 2 là gene:
- `StrategyWfoTask:104-106`: `put("TS_PROFIT_MULTIPLIER", envDouble("WFO_TSMULT_LO", FLOOR?1.0:4.0), envDouble("WFO_TSMULT_HI", 8.0))`
- `put("RATE_PROFIT_STOP_MARKET", 0.03, 0.05)` — KHÔNG có env pin.

→ Knob đúng để ép arm = **`WFO_TSMULT_LO=WFO_TSMULT_HI=X`** (range degenerate [X,X] ép gene = X, kể cả khi HPO không search). rate-min giữ 0.05 (winner luôn chọn trần). arm = X×0.05.
Grid đề xuất: mult {2,3,4,5.2185,6,7,8} → arm {10,15,20,26,30,35,40}%. arm=26% (mult 5.2185) = mỏ neo reconcile với K-grid K8 (FULL_18w~20247, TOTAL_12w~15571). **Không cần rebuild jar** (env đã có sẵn trong jar Aug 2).

## Sai lầm attempt đầu (đã sửa)
- Dùng env tĩnh `SIM_TS_PROFIT_MULTIPLIER` (tôi tự thêm hook) — SAI: gene bị bound bởi range [4,8], giá trị 1.0 out-of-range → ignored/clamped. Bằng chứng: genome in `tsMult=[4.0,8.0]` phớt lờ hoàn toàn env. (Trùng khớp: K-grid K8 cũng in genome y hệt → env vô tác dụng.)
- Surgical-swap Configs@Aug19 vào jar@Aug2: giữa Aug2→Aug19 commit 8741f85 đổi tên field `AEROSPIKE_HOST_226`→`AEROSPIKE_HOST_ORACLE` → class Aug2 khác gọi tên cũ → `NoSuchFieldError` runtime → `FAILED=3`. (Sim-default trailing KHÔNG đổi, nên lỗi thuần do rename infra.)

## Trạng thái infra sau dọn (đã verify)
- `java-run-lc` Kaggle: **revert về pristine Aug2** (hook=False, aero_226=True, size 99527023) — verify RESTORE_CLEAN. Khôi phục từ `armjar/java-run-lc.zip` (bản download đầu, mtime Aug 2).
- `run_worker.py` (5 worker): restore về `sl03bak` = K5 baseline, không SIM_TS injection.
- Không process kgarm/drive_exp18 nào chạy.
- Windows source: Configs.java còn thêm 1 dòng hook `SIM_TS_PROFIT_MULTIPLIER` (git diff HEAD = đúng 1 dòng) + backup `Configs.java.bak_armhook_20260820`. Hook vô hại (env unset) — có thể giữ hoặc git checkout bỏ.

## Quyết định đang chờ user
Ưu tiên cái nào:
- (A) Chạy arm sweep ĐÚNG (WFO_TSMULT_LO/HI, 7 mult) — rẻ, không rebuild, trả lời trực tiếp "26% có quá cao không".
- (B) Sửa HPO degenerate trước (IS_fit -100000 / TOO_MUCH_CAPITAL_LOCK) để WFO thực sự optimize — cấu trúc, lớn hơn; nếu không sửa thì kết quả arm vẫn dính confound capital-lock.
- (C) Điều tra TOO_MUCH_CAPITAL_LOCK (budget khoá hết vốn) — có thể là gốc làm mọi thứ degenerate + BURN_ACCOUNT.
