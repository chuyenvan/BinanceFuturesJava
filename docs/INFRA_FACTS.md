# INFRA_FACTS — Đọc ĐẦU TIÊN khi chạy experiment (chống re-discover, cắt token)

> Mục đích: gom facts hạ tầng rải rác (HANDOFF + báo cáo agent) vào 1 nơi để agent không dò lại mỗi lần.
> Nếu fact ở đây sai/cũ → sửa tại đây, đừng để agent tự dò lại.

## Oracle (compute chính)
- Chạm CHỈ qua `orchestrator/ce.cmd` — Git-ssh `C:\Program Files\Git\usr\bin\ssh.exe`, key `C:\Users\pc\.ssh\id_rsa_chuyennd`, `ubuntu@161.118.212.3`. **Windows-OpenSSH raw ssh FAIL exit 255** — đừng dùng.
- ce menu: `sys_health`, `bg_run/bg_status/bg_report`, `wfo_verify <ds> <win> "<env>"`, `wfo_fanout`, `wfo_status`, `wfo_report <tag>`, `wfo_stop`, `sys_zombies kill=true`, `kaggle_*`.
- ⚠️ **ce.cmd gọi TRỰC TIẾP từ main claude-code PowerShell hay TREO** (chờ input / ssh chậm). Chạy trong agent qua Desktop Commander, hoặc `bg_run` detached.
- Disk **89% (~17.6GB free)** — self-gate trước job ghi nhiều (N=30 HPO, build dataset).
- **LUẬT throughput:** KHÔNG chạy 2 WFO nặng cùng lúc trên 1 box (đã tái hiện fail: fanout `trailfan` 9/16 FAILED, zombie JVM). Compute nặng → đẩy Kaggle fleet.

## 5 gotchas ce/Oracle (đã cắn)
1. interact cap ~180s → job dài PHẢI `bg_run` / `setsid ... </dev/null >log 2>&1 &` detached.
2. dataset PHẢI symlink vào cwd jar `~/java/simulator/<ds>`.
3. extra_env **PHẨY-phân tách** (space → chỉ nhận key đầu).
4. remote grep KHÔNG dùng `|` alternation (PowerShell tách) → `grep -e` / pattern đơn.
5. `TICKER_SOURCE=file` (dataset có market.bin) nhanh + né hard-timeout 1800s của wrapper.

## Kaggle (fleet, ĐÃ self-contained)
- CLI: venv sạch `D:\claudedata\kaggle-clean-env` (`kaggle==1.6.17`). CLI 2.2.2 mặc định lỗi `KaggleObject.from_dict()...'token'` khi tạo version (KAGGLE_RULES §5b).
- Self-contained: dataset `chuyendinh/java-run-lc` `config.properties: TICKER_SOURCE=file`. Java hỗ trợ nhánh file sẵn: `SimulatorMarketLevelTicker1MStopLoss.java:116-136`, `KaggleDataLoader.java`.
- **Mount path thật:** `/kaggle/input/datasets/<owner>/<slug>/`.
- Pattern KHÔNG đụng jobstore chung: `VerifyOneWindow` (đồng bộ, KHÔNG claim WfoJobStore). Mẫu: `C:\Users\pc\wfo-verify-file-parity\run_verify.py`.
- Upload jar: đặt tên **DUY NHẤT** (tránh glob generic nhầm jar cũ), vd `binance-countonly-1.2.4.jar`.
- Parity đã verify: w6 file-ticker = oosPnl 437.41 / wfe 1.2052 / trades 56 ≈ Oracle 437/1.21/56.

## Dataset provenance
- `hpo-ticker-daily` = ticker 1m intraday shard-ngày (1826 file `ticker_YYYYMMDD.bin`, ~662 sym×1440'), **v6 2026-07-13 post ghost-clean** — KHÔNG dùng bản 07-04 stale.
- `wfo-ds-ret2-4h-ff` = preds RET2 (sync từ Oracle `wfo_ds_ret2wf_4h_ff`). `wfo-oizgate` = predict_wf oi_z-gate (EV2). Jar chung: `java-run-lc`.
- Datasets Oracle: `wfo_ds_ret2wf_4h_ff` (selector), `wfo_ds_oiz75`/`wfo_ds_oiz2022_75` (oi_z veto CHỒNG — ĐÃ LOẠI). Jar Oracle: `preflight-v42.jar` (verify), `binance-futures-wfo-lf.jar` (leak-free).

## Fitness V4 — ngưỡng constraint (audit 2026-07-30, đừng dò lại)
- 4 ngưỡng `MAX_PCT_HELD_OVER_7D=0.02` / `MAX_DD_PCT=0.65` / min-trade floor / `MIN_POS_YEAR_RATIO=0.80`
  là `public static` **THUẦN** trong `HPOFitnessCalculatorV4.java:36-40` — **KHÔNG có env override**.
  Đổi ngưỡng = rebuild + scp jar. (Đề xuất env-hoá = P5, xem `reports/AUDIT_20260730_*`.)
- `minTrades = max(5, windowDays*0.33)` → IS 12 tháng = 120, OOS 3 tháng = 30. Cùng 1 hàm
  `evaluateDetailed` dùng cho CẢ IS (chọn genome) và OOS (chấm window) → gốc của mọi lệch ngữ nghĩa.
- Thang điểm reject **KHÔNG cùng bậc**: ramp `TOO_FEW` ∈ (−100000, 0) > `CAPITAL_LOCK` ≈ −100002
  > `OVER_MAXDD` ≤ −100065 > `BURN` < −100000. Đây là BUG (L1), không phải thiết kế.
- `TS_GIVEBACK_RATIO` (`Configs.java:254-255`, default 0.5f, đọc từ properties) **KHÔNG phải gene**
  → không vào `bestGenome` → **không có provenance**. SESSION_START ghi 1.0 tối ưu; 1.0 làm arm
  thành stop-breakeven và xoá bước nhảy tại ratchet. Phải surface vào RESULT_JSON (P6).

## Exit machine — số cứng (đọc code 2026-07-30)
- arm threshold = `RATE_PROFIT_STOP_MARKET` = **1.032%** (`OrderTargetInfoTest.java:191-196`).
- ratchet threshold = `× TS_PROFIT_MULTIPLIER 5.21847` = **5.386%** (`:253-255`) → **dead zone 4.35pp**
  SL đóng băng ở +0.5%, và **bước nhảy siết chặt 41%** ngay tại 5.386%.
- `gap = min(peak×g, TS_MAX_GAP)` → tỉ lệ nhả **teo dần** `maxGap/p` khi p lớn (cắt đuôi x2/x3).
- p < 1.032% ⇒ `priceSL == null` và `HARD_STOP_LOSS_RATE`=0, `TIME_STOP_HOURS`=0 ⇒ **KHÔNG có exit nào**.
- Chấm trailing **KHÔNG THỂ** làm từ `maePeak`/`maeLow` (2 scalar) — cần zigzag path (thứ tự đỉnh/đáy).

## Gate / genome (kiến thức thí nghiệm)
- `MIN_MOMENTUM_15M` = **genome gene HPO** range `[0.010, 0.045]` (`StrategyWfoTask.java:60`), KHÔNG phải env cố định mặc định. Ép cố định env-only: `WFO_N_SAMPLES=1` + `SIM_MIN_MOMENTUM_15M=<x>` (+ khoá `WFO_MOM15_LO=WFO_MOM15_HI=<x>`). `ABLATION_MODE=B` = bỏ hết filter (= gate 0).
- `GATE_COUNT_ONLY` (thêm ở `StrategyWfoTask.java`, **chưa commit**) = surface `gatePass`/`gateSeen` ra RESULT_JSON, đếm frequency không sim PnL.

## Two-sources-of-truth (nguồn lệch)
Verify/verdict ghi ở **repo `docs/`** (`SESSION_START §0.1`, `reports/*`, `STRATEGY_ENTRY_ALPHA §9`). `memory.md` là store RIÊNG, **KHÔNG auto-sync từ repo** → session chỉ nạp memory (không đọc repo) sẽ lệch, hỏi lại việc đã verify. Fix: đọc `SESSION_START §0.1` trước, hoặc chạy consolidate-memory fold verdict vào memory.

## Orchestration (bài học vận hành)
- Job dài (WFO/HPO Oracle, kernel Kaggle) = **fire-and-forget**: launch detached → verify bước đầu pass → THOÁT. KHÔNG poll tới khi xong (đốt token).
- Đừng mark task done khi CHƯA thực sự launch agent/job.
- ce/kaggle CLI hay treo khi gọi từ main → giao agent (Desktop Commander) hoặc detached. (ce OK từ main NẾU đặt timeout lớn, vd 180000.)
- **Sweep frequency/ablation nhiều threshold: LOAD mỗi window MỘT lần rồi áp TẤT CẢ threshold trong 1 pass.** `count-only` KHÔNG nhanh nếu bị data-load bound — bottleneck là load ticker/market (~120s/window), KHÔNG phải sim PnL. Lỗi đã cắn (2026-07-28): probe gate×oi_z lặp 6 gate × 12 window, mỗi gate load lại cùng window → 72 cell × ~120s ≈ 2.4h/kernel thay vì ~20 phút.
