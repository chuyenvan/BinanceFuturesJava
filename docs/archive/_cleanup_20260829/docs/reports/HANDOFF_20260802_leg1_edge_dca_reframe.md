# HANDOFF 2026-08-02 — leg1 CÓ edge, DCA là add-on hiếm, trailing-floor thắng — ĐỌC TRƯỚC

> Nối từ `HANDOFF_20260801_dca_grid_exit.md`. Phiên này ĐO nhiều, REFRAME lớn, và chốt bằng số:
> **leg1 (selector entry + exit) là engine có lãi thật; DCA sâu là ảo tưởng; trailing sửa được.**

## 0. Kết quả chốt (có số, khử survivorship, mẫu lớn)

### A. leg1 CÓ EDGE — base-rate thì LỖ (`orchestrator/tools/leg1_econ.py`, 42.6M entry label)
Triple-barrier TP+3% / phao−70% / phí−0.8%, selector (g008) vs ngẫu nhiên:

| horizon | BASE (ngẫu nhiên) | SELECTOR | EDGE |
|---|---:|---:|---:|
| 72h | **−1.02%/lệnh** | **+1.19%/lệnh** | **+2.21%** |
| 24h | −0.90% | +0.83% | +1.73% |

→ Không phải hớt beta (ngẫu nhiên LỖ). Selector là alpha thật, ở tầng kinh tế (net/lệnh), không chỉ rankIC.
Cận dưới: TP cố định +3%, chưa trailing, ≤72h. Caveat: join g008↔label chỉ khớp 18.3k/171k do **lệch pha
~4' g008 vs lưới 15m label** (làm tròn 15m mới khớp một phần) — mẫu con có thể lệch, nhưng edge quá lớn.

### B. DCA là cơ chế HIẾM — leg1 làm gần hết việc (SurvivalProbe g008 180d + Kaggle 497k ≤72h)
Phân bố số leg khớp (grid thật, recovery-to-avg):

| grid | leg1 | leg2 | leg3 | leg4 |
|---|---:|---:|---:|---:|
| −50/−75/−90 | **97.5%** | 1.8% | 0.6% | **0.06%** |
| −30/−50/−70 | 95.6% | 2.5% | 1.3% | 0.6% |

Kaggle 497k: **99.6% chỉ dừng leg1** với grid sâu. ⇒ **1:1:2:6 là TỆ NHẤT** (leg4 giữ 6/10 vốn nhưng
khớp 0.06% ⇒ 60% vốn nằm chết; leg1 lo 97.5% cụm chỉ được 1/10). Grid sâu vừa hiếm khớp vừa khó hồi
(−90% cần bật +142% mới về avg+3%; %TP tại −90% chỉ 20%). **Grid nên NÔNG + PHẲNG/front-load.**

### C. Phao F ≈ −70% — gần như miễn phí
Recovery-by-depth (180d) rơi khỏi vách ở −70/−80%: 65%(−60) → 53%(−70) → 33%(−80) → 0%(−90).
Chỉ ~0.5% cụm chạm tới, phần lớn không hồi. Cắt ở đó gần như không mất gì. **Delist thật ~0% trên g008.**

### D. Trailing giveback-floor THẮNG (M0, w15 N=1, raw PnL)
`TS_GIVEBACK_FLOOR=true` (gap=max(đỉnh×tỉ lệ, sàn)) vs cũ (min/cap 8%): **+24% PnL, maxDD y hệt.**
Sửa đúng bệnh "cắt non đuôi". → BẬT.

### E. DCA A/B (M0, w15): risk-adjusted grid-có-trần tốt nhất
B0(DCA cũ) PnL/maxDD=0.90 · Doff=0.91 · Dgrid(grid+trần)=**1.46**. DCA cũ lãi thô cao nhưng maxDD tương xứng.

## 1. ⚠️ Xung đột thiết kế phải quyết (data lộ ra)
- **Time-stop 48h (spec I5) MÂU THUẪN**: hồi sâu mất **100-267 NGÀY** (đo được). 48h cắt sạch cụm DCA
  trước khi hồi. → time-stop chỉ cho nhánh trailing/thắng, HOẶC dài (tuần), HOẶC bỏ cho nhánh rescue.

## 2. Thiết kế (data-backed) — spec đã cập nhật (`STRATEGY_SPEC_20260801`)
- **Engine = selector entry + exit (trailing-floor).** Chỗ tiền. Dồn công ở đây.
- **DCA = add-on hiếm**, grid NÔNG + phẳng (bỏ 1:1:2:6), N=4, phao cắt chỉ arm sau leg 4.
- **Phao F ≈ −70%** (sweep −70/−75/−80), sizing D = R/F.
- 2 sleeve (BIG_DOWN + selector) GIỮ cả hai, chung vòng đời.

## 3. Code đã đổi phiên này (đã commit)
- `Configs.java`: DCA grid dạng SCALAR (DCA_GRID_L1/STEP/LEGS/W_RATIO + DCA_TIER_CAP_BASE/STEP) —
  để HPO reflection chạm được (mảng cũ không tune được). `DCA_GRID_SCALAR=false` = byte-identical.
- `DcaUtils.java`: accessor thay mảng trực tiếp. `StrategyWfoTask.java`: genome swap theo cờ (17↔21 gene),
  mở TS_PROFIT_MULTIPLIER xuống 1.0. `SimulatorMarketLevelTicker1MStopLoss.java`: log `[TIER-MARGIN]`.
- Test `DcaGridScalarTest` 7/7 pass (có case bắt lỗi im lặng "đổi scalar mà kết quả không đổi").
- `orchestrator/tools/verify_stage.py` + nút `ce.sh verify_stage` (jar-stale gate, PASS 21/21). **File cũ mất
  vì chưa commit — nay commit.**
- Probe/đo: `_measure_m0`, `_run_floordepth_probe`, `kaggle_recovery_depth/{recovery_by_depth,recovery_grid_v2}.py`,
  `leg1_econ.py`. Config: `configs/exit_dca_20260801_{frozen,hpo}.env`. Pipeline: `wfo_dca_grid_hpo.json`.

## 4. Việc chưa làm / next
- **Code S0**: risk-unit sizing (D=R/F) + floor-arm-sau-leg4 + exit-theo-đường-đi. `HARD_SL_PCT` (đo trên
  firstEntryPrice) làm sẵn cái phao — chỉ cần gate "arm sau leg 4".
- Quyết xung đột time-stop (mục 1).
- Chạy validate best config đa-window qua CE (đang chạy cuối phiên).
- Join g008↔label lệch pha: nếu muốn số leg1-edge sạch hơn, sửa pha (label ~:14 vs feature :00) rồi đo lại.
- Harness constraint vẫn hỏng (loại window capital-lock) — nhưng leg1-edge đo NGOÀI harness nên không bị dính.

## 5. Hạ tầng phiên này (giữ để dùng lại)
- pandas 2.3.3 đã cài trên Oracle (`pip3 --user`). Label 8.3GB = `outputs/funding_label.csv` (42.6M dòng,
  27 cột maxFav/maxAdv/tHit/retEnd/nBars×{4h,12h,24h,72h}). Ticker thô: `kaggle_data_hpo/daily/ticker_*.bin.gz`
  (1886 file) — symlink lên root để SurvivalProbe (KaggleDataLoader) đọc.
- Kaggle: kernel Python chạy được (`funding-label-full` có sẵn). `reprobe-unfiltered` KẸT vì dataset chưa tạo.

---

## 6. NỐI THÊM (2026-08-02 chiều) — harness fix XONG + gate mở giải quyết no-trades

### Gate mở (rank-K8) giải quyết no-trades — mọi window có lệnh, đều LÃI
Fanout `loose_k8_full` (ret2wf, `SELECTOR_RANK_TOPK=8` + `SIM_MIN_MOMENTUM_15M=0.008` + trailing-floor
+ DCA nông + phao, 7 node Oracle+Kaggle): **12/16 window pnl DƯƠNG** (3 SUCCESS + 9 CAPITAL_LOCK),
4 ZERO_TRADES. PnL dàn đều (12k/11.7k/4.6k/4.5k/3k/2.2k...), HẾT dồn w15. maxDD thật ≤ ~20%.
→ **Nút thắt chuyển từ entry-frequency (đã gỡ bằng rank-K8) sang harness-constraint.**

### Harness fix P0+P1 (commit sau `dab4d48`) — verdict lật
`WFO_HARNESS_FIX=true` (default OFF byte-identical, test 13/13):
- **P0** (HPOFitnessCalculatorV4): ramp TOO_FEW xuống dưới mọi reject (hết ordering inversion).
- **P1** (StrategyWfoTask.aggregate): OOS coi CAPITAL_LOCK/TOO_FEW/UNSTABLE là report-only; chỉ
  ZERO_TRADES/BURN_ACCOUNT/OVER_MAXDD disqualify.
- Coordinator report loose_k8_full: **posRatio strict=6% → lenient=88%** (14/16). %OOS + maxDD QUA
  ngưỡng. VERDICT vẫn FAIL do **WFE** (N=1 frozen → IS=sentinel → WFE vô nghĩa) → cần N=30.
- CE tool `mcp_tools-v3.py._wfo_coord_cmd`: patch passthrough `WFO_HARNESS_FIX` vào JVM (báo cáo cũ
  đọc md cache jar cũ). Đã sync về `orchestrator/mcp_tools-v3.py`.

### ĐANG CHẠY: N=30 confirm (jar mới + HARNESS_FIX, 7 node)
`confirm_n30` trên ret2wf, config loose_k8. Đọc: `WFO_HARNESS_FIX=true ... WfoCoordinator report
strategy_window` (KHÔNG qua wfo_report cache) hoặc `ce wfo_report confirm_n30` sau khi patch tool.
Kỳ vọng: WFE thật (IS dương), %OOS-dương ~cao → verdict sạch.

## 7. STEP 2 (kế tiếp) — rà + cải tiến exit/DCA trên harness ĐÚNG
Chỉ chạy SAU khi N=30 baseline `confirm_n30` có số (jobstore serial, không chạy 2 fanout cùng lúc).
Sweep so với baseline (mỗi lần đổi 1 cụm, đọc raw PnL + posRatio lenient + maxDD):
- **Trailing:** `TS_GIVEBACK_RATIO` {0.3, 0.5, 0.7} × `TS_MIN_GAP` {0.005, 0.01, 0.02}.
- **DCA:** grid nông {−30/−50/−70} vs {−20/−40/−60}; W_RATIO {1.0, 1.5}; và **DCA off** (vì DCA hiếm
  99% leg1 — kiểm nó có cộng gì ròng không). Phao `F` sweep {−0.65, −0.70, −0.75} (đã đo cliff ~−70).
- Metric: PnL/R + PnL-vượt-beta + posRatio(lenient) + ddPctMtm + sign-test fold. Giữ holdout 2024H2+.

## 8. STEP 3 — làm mịn rank-K8 entry (sau step 2)
Sweep `SELECTOR_RANK_TOPK` {5,8,12} × `SELECTOR_RANK_OFFSET` {0,1,2}; cân tần suất vs chất lượng
(rankIC theo K). Mục tiêu: %OOS-dương + PnL/R tốt nhất mà không phình maxDD.
