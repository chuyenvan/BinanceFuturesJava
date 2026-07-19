# HANDOFF 2026-07-19 (consolidated) — đọc file này + docs/rules/ce-buttons.md là đủ.
> Supersede các append rải rác ở 20260718.md. R1 (CE-first) + R2 (handoff-luôn): xem ce-buttons.md.

## KIẾN TRÚC ĐÃ CHỐT
Bỏ DCA + bỏ gate-cứng + **selector EV2** (classifier P(HIT) + reg E(ret|miss)) n6. Edge **THẬT nhưng
regime-gated** (bull dương, chop breakeven). **Faithfulness PASS** (entry-match 100%, placebo PASS,
proxy−ma-sát≈WFO) → số ĐÁNG TIN. Sim ma sát: fee 0.2% + slippage 0.6% = 0.8% (funding OFF). Slippage
thật CHƯA đo (hoãn; bot 242 không lưu giá khớp → cần userTrades API hoặc thêm log).

## NÚT THẮT XUYÊN SUỐT = OPPORTUNITY FREQUENCY (không phải edge)
- **oi_z veto (long) = lever CHẤT LƯỢNG thật:** WFE 0.20→1.5, BURN 6→2, maxDD 9→6%. NHƯNG Q0.5 & Q0.75
  đều **FAIL vì frequency** (4 ZERO 2022-coverage + 6 TOO_FEW). Nới Q không giúp (bệnh không phải oi_z).
- → 3 đường giải FREQUENCY: (a) **2022 coverage** (EV2 export FIRST_OOS về sớm hơn), (b) **horizon 12h**
  (1152 kèo/quý), (c) **thêm SHORT** (nhân đôi cơ hội + lấp regime chop).
- Đang chạy: `oiz_gateon` WFO (oi_z Q0.5 + gate-ON, quality-max) → nếu VẪN fail = chốt frequency là wall.

## SHORT (đòn bẩy #2, lấp chop)
- Alpha THẬT: classifier AUC 0.85(4h)/0.77(12h)/0.71(24h). Mechanics sim: `ENABLE_SHORT` +
  `createOrderSELL` + hard-SL `SHORT_SL_PCT`(0.25) + time-stop + PnL đảo dấu. **JUnit 6/6 PASS**
  (commit df542c5) — default OFF byte-identical. DCA tắt khi short.
- **Feature short KHÁC long (short-featscreen 12h):** conditioning = **crowding** `ls_toptrader`(+1.61,
  mono1.0) + `ls_global`(+1.45) — top-trader long đông → dump. → veto short cụ thể.
- **Grid (target{3,6,9,15}×horizon{4,12,24,72}×stop{8,15,20,30}):** 4 kernel Kaggle. grid-24h: net_bull
  dương & tăng theo target (t15 bull +6.24) NHƯNG **net_chop âm = ARTIFACT** (grid có nhánh chốt-+t cap
  winner; v2 let-dump-run cho chop +12). → **CẦN re-run grid với let-run accounting (bỏ chốt +t).**
- **Calibration:** ps short thấp (max 0.67, base-rate 1.3%) → gate long (ps≥0.68) cho 0 lệnh →
  dùng **rank/top-K** thay ngưỡng tuyệt đối. predict_wf_short + jar short (preflight-v42-short.jar) đã dựng.

## HẠ TẦNG / CE (R1 đã trả nợ)
- Nút mới: **`pred_convert` / `wfo_build_ds` / `wfo_verify`** + pipeline `wfo_from_preds.json` (commit 2d544e6,
  bg_selftest 6/6). Từ giờ WFO-from-preds = nút bấm, không SSH thô.
- Jar Oracle `preflight-v42.jar` = có TRAIL_PEAK_MODE + entry-log + short(gated off). Backup .bak_*.
- Datasets: wfo_ds_ev2 (long), wfo_ds_oiz (Q0.5), wfo_ds_oiz75, wfo_ds_short. Ticker daily có ở Oracle.

## ĐANG CHẠY (2026-18 tối)
- Oracle: `oiz_gateon` WFO (4/16). Kaggle: short-grid 4h/12h/72h (24h xong), short-featscreen xong.

## NEXT (ưu tiên)
1. Đọc verdict oiz_gateon (quality-max fail? → frequency là wall).
2. **Fix grid accounting (let-run, bỏ chốt +t)** → re-run 4 horizon → chọn winner short (net+winrate+tpq,
   chop theo let-run).
3. Short winner → **re-export Java label chính xác** (time-to-level cho +stop; CSV hiện chỉ có cực-trị) →
   validate. Short veto = ls_toptrader.
4. Long frequency: thử 12h horizon + 2022 coverage.
5. **Validate 2 tầng khi bật short thật:** real-data 1 tháng → Excel → recompute code khác đối chiếu (Uni dặn).
6. Slippage thật (sát go-live). Funding: bật lại + dấu SHORT-nhận-khi-funding+ (Uni: tính tổng rồi trừ, nhỏ, tạm bỏ).

---

## ĐÊM 18→19 TIẾN ĐỘ (orchestrator tự chạy, ~23:00 tối 18)

### Trạng thái lúc vào ca (poll thật qua CE)
- Oracle `oiz_gateon` WFO: **12/16 DONE**, 2 RUNNING (w12/w13, lease ~27-30′), 2 PENDING (w14/w15). CHƯA xong → jobstore + 12G RAM còn bận.
- Kaggle (poll `kaggle_status`, KHÔNG tin `kaggle_slots` — nó chỉ đếm slot session này):
  - `short-grid-72h` **COMPLETE** ✓ · `short-grid-24h`/`12h`/`4h` **RUNNING** (chưa đủ 4 để chọn winner).
  - `ev2-export-2022` (GPU) **COMPLETE** ✓ → đã `kaggle_output` về `/home/ubuntu/claudedata/kout/ev2-export-2022/ev2_preds_n6_2022.csv.gz` (18 win, 3.485M row, cột p6/p9/oi_z/oi_delta24h, first_oos=202201, n_p6≥0.7=6888).
  - `ev2-export-12h` (GPU) **RUNNING** (cho bước LONG-12h sau).
- Pipeline cũ treo (KHÔNG phải việc đêm, để nguyên): `ladder_1784297380` = WAITING_LLM (8/9). `ladder_peak` STOPPED 2/9.

### Bước 1+2 — ĐÃ DISPATCH tự động (pipeline chuỗi, an toàn drain-gate)
- Tạo + sync pipeline mới **`orchestrator/pipelines/wfo_long_full.json`** → `pipe_run` →
  **pipe_id = `wfo_long_full_1784390404`** (runner_pid 3147030, RUNNING, đang ở step0 `wait_oiz_drain`).
- Chuỗi 8 step tự chạy: `wait_oiz_drain` (chờ oiz_gateon RUNNING=0&PENDING=0&DONE≥16 → KHÔNG đụng 12G RAM khi WFO còn chạy) → `report_oiz` (CHỤP verdict bước 1 TRƯỚC khi fanout reset jobstore) → `pred_convert oiz 0.75` → `wfo_build_ds wfo_ds_oiz2022_75` → `wait_build` → `wfo_fanout` (Oracle-only 2 worker, KAGGLE_KERNELS=0 vì extra_env ABLATION_MODE không tới Kaggle) → `wait_fanout` → `wfo_report long_full`.
- Config LONG full: preds ev2-2022 (gỡ 2022 coverage + oi_z), veto oi_z Q0.75, gate-ON, `extra_env=ABLATION_MODE=A,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24`, N=30 seed=42, tag=**long_full**. Đây là ứng viên PASS long #1.
- **SÁNG UNI ĐỌC:** `ce pipe_status wfo_long_full_1784390404`. Report bước1 (oiz_gateon) + bước2 (long_full) nằm trong step summary + `ce wfo_report oiz_gateon` / `ce wfo_report long_full`. So pass-criteria: %OOS-dương≥70% · WFE median≥0.5 · maxDD≤50%. Nếu long_full vẫn FAIL do TOO_FEW/ZERO → xác nhận **frequency là wall**.
- Nếu pipeline abort giữa chừng: `ce pipe_status <id>` xem step fail → `ce pipe_resume <id>` (checkpoint từng step, không làm lại).

### Bước 3 — LONG 12h (CHỜ ev2-export-12h xong)
- Khi `ce kaggle_status chuyendinh/ev2-export-12h` = COMPLETE → `ce kaggle_output chuyendinh/ev2-export-12h /home/ubuntu/claudedata/kout/ev2-export-12h` → copy `wfo_long_full.json` sửa csv=…/ev2_preds_n6_12h.csv.gz, out_ds=wfo_ds_oiz12h_75, build_job=buildds_wfo_ds_oiz12h_75, tag=long_12h, extra_env=…,TIME_STOP_HOURS=12 → `pipe_run`. (CHỈ 1 WFO/lúc — chờ long_full DONE trước.)

### Bước 4 — SHORT winner (CHỜ đủ 4 grid; cần LLM chọn — KHÔNG tự động được)
- Refs: `chuyendinh/short-grid-{4h,12h,24h,72h}`. Poll `ce kaggle_status <ref>` tới COMPLETE cả 4.
- Fetch: `ce kaggle_output chuyendinh/short-grid-<H> /home/ubuntu/claudedata/kout/short-grid-<H>` cho từng H → đọc file `SHORTGRID_<H>_RESULT` (acct=**let-run**, grid v2 đã bỏ chốt +t cap winner — commit 8b63fcd).
- CHỌN winner: **max net_chop (let-run) với tpq≥30 và winrate hợp lý** → ghi (target t, horizon H, stop s). (Kaggle giữ output bền, không mất — defer an toàn.)
- Rồi bước 5 (SHORT-only WFO): converter short dùng RANK/top-K (ps thấp, base-rate 1.3%) → predict_wf_short → wfo_ds_short_win → `wfo_fanout` jar **preflight-v42-short.jar** env `ENABLE_SHORT=1,WFO_DISABLE_DCA=1,SHORT_SL_PCT=<s/100>,SHORT_TIME_STOP_HOURS=<H>`.

---

## MAX-DEPLOYMENT (long) — code XONG, CHỜ build+run (07-19)
> Câu hỏi: hạ ngưỡng entry (p6 0.68→0.5) + GIỮ oi_z veto + 2022 coverage → annual return có scale ~20% không, hay edge pha loãng? Trực diện đánh FREQUENCY wall.

### ĐÃ SỬA (default OFF = byte-identical; CHƯA build/commit — sandbox thiếu mvn+SSH Oracle)
1. `orchestrator/tools/ev2_csv_to_predictwf_oiz.py`: P6_MIN = **ENV P6_MIN > argv[4] > 0.7**. ENV thắng nên
   nút pred_convert (ép positional 0.7) vẫn hạ 0.5 mà KHÔNG sửa button: chạy `P6_MIN=0.5` trước lệnh.
2. `Configs.java` (sau PREDICT_SYMBOL_RATE_MAX_THRESHOLD): thêm `SELECTOR_SCORE_MAX` (env, default **-1f=OFF**).
3. `SimulatorMarketLevelTicker1MStopLoss.java` (~L258): nếu `SELECTOR_SCORE_MAX>=0` → ép trực tiếp `maxThres`.
   - Gate cũ: `maxThres = 0.15 * AI_DYNAMIC_MAX(2.14135) = 0.3212`; symbolPred=1-p6, admit khi ≤maxThres →
     admit p6≥**0.6788**. Set `SELECTOR_SCORE_MAX=0.5` → admit p6≥**0.5** (KHÔNG dính AI_DYNAMIC_MAX genome-coupled).

### RUNBOOK (chạy trên máy Uni + Oracle — 1 WFO/lúc, chờ jobstore FREE)
1. Build: `mvn -q -DskipTests package` → backup Oracle jar (`.bak_*`) → scp jar mới tên **`preflight-v42-maxdep.jar`** → md5 verify (KHÔNG đè jar WFO khác đang chạy — kiểm `ce wfo_status` trước).
2. Convert (P6_MIN=0.5, OIZ_Q=0.75): trên Oracle `P6_MIN=0.5 python3 <CE_PRED_TOOLS_DIR>/ev2_csv_to_predictwf_oiz.py /home/ubuntu/claudedata/kout/ev2-export-2022/ev2_preds_n6_2022.csv.gz <symbol_map> <out=predict_wf_maxdep> 0.7 0.75` → `ce wfo_build_ds predict_wf_maxdep wfo_ds_maxdep <jar-maxdep>`.
   - (Tùy chọn productize: thêm param P6_MIN cho nút pred_convert — R4 bắt `ce --sync bg_selftest` 6/6, chưa test được ở sandbox nên để nút nguyên, dùng env one-off.)
3. `ce wfo_fanout wfo_ds_maxdep preflight-v42-maxdep.jar 30 42 2 0 long_maxdep "ABLATION_MODE=A,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24,SELECTOR_SCORE_MAX=0.5"` → poll `ce wfo_status` DONE≥16 (300s).
   - ⚠️ Task template ghi `ABLATION_MODE=B` — long_full dùng **A**. Để so apples-to-apples (chỉ đổi tần suất) NÊN giữ **A**. Xác nhận trước khi chạy.
4. `ce wfo_report long_maxdep` → tính full-cycle per-year (2022/23/24/25) → total%/CAGR/năm-dương so long_full (CAGR +2.2%, 4/4 dương). Đo tần suất tăng (tpq/SUCCESS windows). Verdict: scale ~20% hay edge pha loãng?

### CHƯA làm (hết ưu tiên/tài nguyên tuần tự — 1 WFO/lúc)
- Bước 6 (short-gate classifier) · Bước 7 (multi-sleeve dual-channel Java — CODE MỚI PnL-critical, chỉ DRAFT+flag, KHÔNG trust khi chưa cross-check 2 tầng).
- Blocker cứng: **Oracle 1 WFO/lúc + wfo_build_ds 12G RAM** ⇒ long_full → long_12h → short_win chạy TUẦN TỰ, mỗi cái ~2.5h. Đêm chỉ đủ 1-2 WFO. Short winner + long_12h phụ thuộc Kaggle export xong.
