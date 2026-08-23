# WFO HANDOFF — 2026-08-10 (chiều/tối) — ĐỌC FILE NÀY TRƯỚC cho session mới

> Nối tiếp `wfo_handoff_2026-08-10.md` (sáng). Session chiều đã CHẨN ĐOÁN XONG "sao 1m tệ hơn 15m" và đang
> dở 1 pipeline train selector. File này = mục tiêu + kết luận + việc đang dở + runbook nối tiếp + note scheduled task.
> Chi tiết số: `wfo_diff_15m_vs_1m_2026-08-10.md` + `wfo_goforward_design_2026-08-10.md` (§0 có bảng universe).

## 1. MỤC TIÊU (không đổi)
Model chọn coin pump nhưng "ăn ít đuôi lớn". Câu hỏi phiên này: **vì sao canon 1m (08-10) LỖ (−1,945) trong khi
run 2.8 15m THẮNG (+12,761)?** Uni yêu cầu: đừng hỏi lòng vòng, tự đo, Kaggle+Oracle đều rảnh.

## 2. ✅ CÂU TRẢ LỜI (đã chốt bằng số, cùng engine) — THỦ PHẠM = UNIVERSE FILTER TOP-10%
Test sạch `wfo_ds_unf_h4h` (predict UNFILTERED `wf_pred_ret2wf` 2023-2025 + CÙNG gate+market+genome+engine-1m như canon,
chỉ khác universe): **UNFILTERED +14,225 vs canon filtered −1,945.** 2 window thảm hoạ lật: 2025Q1 −9906→+1095 (DD 38→11%),
2025Q4 −3646→+4646 (DD 48→20%). %OOS+ 11/12.
- Attribution kín nhờ control **g15** (filtered + 15m-cadence = −3354): bản unfiltered khác g15 ĐÚNG 1 biến universe → swing 100% do universe.
- **1m KHÔNG hỏng.** Filter top-10% (bó vào coin pump-dump dữ nhất) bị bundle vào lúc rebuild canonical (tránh OOM 1m) chính là thủ phạm.

### Chuỗi loại trừ (đều đã bác bằng số, đừng đo lại)
- **Grid 1m**: g15 (canon data chạy nhịp 15m) vẫn −9139 ở 2025Q1 → grid KHÔNG phải thủ phạm.
- **Selector**: edge 1m ≡ 15m (đo predict vs label: maxFav IC ~0.3 cả hai, retEnd âm 2025 cả hai). Không suy biến.
- **Label maxFav≥6%**: dùng cho CẢ 2.8 lẫn canon → bệnh nền CHUNG, không phải chỗ khác nhau. (Là mục tiêu LƯỚT: bắt "chạm +6%" tốt nhưng cú chạm reverse.)
- **Exit/sizing**: sweep 5 A/B (hard-SL −25% = −18,670; RANK_TOPK 3 = −6,804; MAX_CONCURRENT 10 = −4,887; g15 cadence = −3,354; predRisk4H-brake pctl20 = −5,191) — TẤT CẢ tệ hơn baseline −1,945. Không phải cách trade.
- **predRisk4H brake**: gỡ 08-08; có signal đơn điệu trên tail nhưng global-gate quá cùn → net âm. Không cứu.
- **Bất đối xứng horizon**: bull pump giữ&chạy (retEnd 4h→72h +0.08→+1.93%), crash pump reverse&dump tiếp (−0.28→−4.34%). Frozen không thắng cả 2 → entry phải biết regime.

## 3. THIẾT KẾ GO-FORWARD (ưu tiên)
- **Trụ 1 (đã chứng minh): bỏ filter top-10%, đi UNFILTERED/rộng.** Đây là fix chính, đã +14k.
- Trụ 2 (chưa chắc): đổi label maxFav→net-return/sustain. ⚠️ base-rate net-label ~phẳng 35% mọi regime → KHÔNG tự tạo abstain; phải train mới biết có tốt hơn không (separability). Optional.
- Trụ 3: gate regime thật (thay predRisk4H mù). Ưu tiên thấp.

## 4. 🔴 ĐANG DỞ (in-flight) — HOÀN TẤT selector unfiltered leak-free deploy-grade
Đang train bản selector UNFILTERED **leak-free chuẩn** (current code) để deploy (bản +14k trước dùng `wf_pred_ret2wf`
cũ còn fold-0-leak). Kernel Kaggle **`chuyendinh/selector-unf15-maxfav` — RUNNING** lúc 22:21 (WF 14 fold, 15m-unfiltered,
FIRST_CUTOFF=2023, maxFav WIN=0.06). Kernel dir `C:\Users\pc\sel1m_kernel_unf15\` (đã fix 4 landmine — xem §6).

### RUNBOOK nối tiếp (session mới chạy khi kernel xong):
1. `kaggle kernels status chuyendinh/selector-unf15-maxfav`. RUNNING→chờ. ERROR→`kaggle kernels output ... -p C:\Users\pc\unf15_out` đọc log (snag: join rớt/grid, OOM, label schema) → fix → `cd C:\Users\pc\sel1m_kernel_unf15 && kaggle kernels push`. COMPLETE→output, đếm predict_wf_*.bin (~14).
2. scp predict 2023-2025 lên Oracle: mkdir `/home/ubuntu/claudedata/predwf_unf15/`; scp git `C:\Users\pc\unf15_out\predict_wf_202[345]*.bin` → đó.
3. build_ds: `cd /home/ubuntu/claudedata/.run/oracle_worker_cwd; WFO_CODE_SHA=8741f85154e04d57c48da9c55472cea7e55eed2a WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/predwf_unf15 WFO_SEL_HORIZON_IDX=0 WFO_SET_PRED=ai_pred_market_gate_wfo java -Xmx18g -cp /home/ubuntu/java/simulator/binance-fresh-20260809.jar com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/claudedata/wfo_ds_unf15clean` (nohup </dev/null; chờ 'EXPORT xong').
4. fanout: `export CE_RUN_DIR=/home/ubuntu/claudedata/.run/ce_run CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/ce_locks; cd /home/ubuntu/claudedata/.run; python3 mcp_tools-v3.py wfo_fanout /home/ubuntu/claudedata/wfo_ds_unf15clean /home/ubuntu/java/simulator/gatecount.jar 1 42 1 0 unf15clean "JAVA_TOOL_OPTIONS=-Xmx16g,TS_GIVEBACK_FLOOR=true,SELECTOR_RANK_TOPK=8,SIM_MIN_MOMENTUM_15M=0.008,DCA_GRID_ENABLED=true,DCA_GRID_SCALAR=true,DCA_GRID_L1=-0.30,DCA_GRID_STEP=0.20,DCA_GRID_LEGS=3,DCA_GRID_W_RATIO=1.0,DCA_GRID_SCALE=4,DCA_TIER_MARGIN_ENABLED=true,DCA_TIER_CAP_BASE=0.50,DCA_TIER_CAP_STEP=0.10,SIM_BREAKER_MODE=OFF,SIM_APPLY_FUNDING=true,WFO_HARNESS_FIX=true"`. Chờ DONE=16.
5. Đọc verdict: `cd oracle_worker_cwd && WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker WFO_HARNESS_FIX=true java -cp /home/ubuntu/java/simulator/gatecount.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window`; table ở `.run/oracle_worker_cwd/docs/reports/wfo_strategy_window.md` (cột 7=OOS_pnl, 13=DD, 10=trades). **So vs +14,225** (kỳ vọng ~bằng → xác nhận deploy-grade). Cập nhật `wfo_goforward_design §0`, báo Uni.

### FOLLOW-UP optional (nếu Uni muốn): net-label variant (Trụ 2)
Copy kernel dir → sửa gen `gen_funding_wf_predictions_1m.py`: load thêm cột `retEnd_4h`, đổi `y=((retEnd_4h-0.008)>0).astype(int8)`. slug `selector-unf15-net`. Train song song (Kaggle 5 slot). build_ds+fanout tag unf15net. So vs maxFav.
Và bản **pure-1m** (selector train grid 1m, không phải 15m): OOM-hard (636M) → dùng top-20/25% (fit Kaggle) hoặc bỏ.

## 5. ⏰ SCHEDULED TASK — ĐÃ XÓA, session mới TỰ TẠO LẠI
- Trigger send_later `trig_01GjGt3smXqhuaxFoQAeiUf9` (fire 16:10Z, nối tiếp pipeline) **ĐÃ XÓA** — vì nó bind vào session CŨ (`session_01NwYmR12LTN1uNqTfL78isF`), fire vào đó thì session mới không nhận.
- **Session mới**: sau khi đọc handoff này, nếu kernel còn RUNNING thì tự tạo `send_later` MỚI (bind session mới) để nối tiếp — nội dung = RUNBOOK §4. Đừng dùng lại trigger cũ (không còn + sai session).
- Các trigger khác trong list đều `run_once_fired` (đã tắt) — bỏ qua.

## 6. PLUMBING / GOTCHAS (session chiều)
- **SSH Oracle** (161.118.212.3): git ssh `"/c/Program Files/Git/usr/bin/ssh.exe" -o BatchMode=yes -i /c/Users/pc/.ssh/id_rsa_chuyennd ubuntu@161.118.212.3`. scp git tương tự. nohup kèm `</dev/null`. ⚠️ Bridge cap lệnh ~60s — lệnh nặng (mv/cp GB, sleep) vẫn chạy server-side sau timeout, cứ check lại.
- **Kaggle CLI**: Windows `kaggle` (2.2.2) HOẶC Oracle `/home/ubuntu/kaggle_latest_venv/bin/kaggle` (push dataset thẳng từ Oracle, khỏi vòng 6GB qua Windows). ⚠️ Kaggle **auto-giải nén .gz** khi upload → `features_*.bin.gz` thành `features_*.bin` (reader read_tool1 có `_decode_legacy` đọc đúng).
- **Jars Oracle** `/home/ubuntu/java/simulator/`: `gatecount.jar` (WFO framework + sim + ExportFeaturesForPythonTool — đã javap xác nhận CÓ, đừng tin unzip|grep), `binance-fresh-20260809.jar` (ExportWfoDataset/build_ds, code_sha 8741f85).
- **Jobstore** 226 (103.157.218.226:3222 ns=ticker) ALIVE — dùng cho fanout (reset mỗi lần, autosnap tự lưu report trước). Oracle-local 127.0.0.1:3222 cũng alive (dự phòng).
- **Disk Oracle 86%/22G free** — dọn nếu export lớn. `wfo_ds_unf_h4h` (test universe) + `unf15_kag` (6GB, features+label đã push Kaggle → xóa được sau khi kernel xong) đang chiếm chỗ.
- **Feature export**: node CE `tool1_export <out_dir> <grid_min> <start> <end> <jar> <ram>` — PHẢI truyền start/end tường minh (rỗng → shell nuốt → path parse thành date, lỗi). FF_UNFILTERED=1 tự set. Output = `<out_dir>features_*.bin.gz` (out_dir thành prefix nếu không / cuối).
- **shadow-compile pattern** (patch sim nhẹ, không rebuild fat-jar): sửa .java → `javac -cp gatecount.jar -d /tmp/patch X.java` → chạy `-cp /tmp/patch:gatecount.jar`. Đã dùng cho predRisk4H-brake (`SIM_RISK4H_PCTL`, Configs+Sim tại `/tmp/patch`).
- **Datasets/kernels tạo phiên này**: Kaggle `chuyendinh/funding-unf15-data` (features 15m-unf .bin + label 15m .pb), kernel `chuyendinh/selector-unf15-maxfav`. Oracle datasets: `wfo_ds_canon_1m_h4h` (canon filtered 10%, baseline −1945), `wfo_ds_unf_h4h` (unfiltered test +14,225). preds: `predwf_canon` (canon 1m filtered), `wf_pred_ret2wf` (15m unfiltered, 2022-2025), `/tmp/predwf_unf` (2023+ subset dùng build wfo_ds_unf_h4h).
- **Landmine đã trả giá**: (1) grid features/label/SELECTOR_GRID_MIN PHẢI khớp (lệch=mất 93% join âm thầm) — unf15 dùng 15 hết. (2) PURGE_STEPS theo grid (72h@15m=288, @1m=4320). (3) worker heap default ~5.75g → OOM window 1m 2025H2 → `JAVA_TOOL_OPTIONS=-Xmx16g` (RobustJobController ram_limit chỉ là cổng pre-flight, KHÔNG inject -Xmx). (4) WFE vô nghĩa cho frozen — verdict đọc %OOS+ & maxDD & tổng PnL.

## 7. 1 dòng cho Uni
Xong chẩn đoán: **1m không hỏng — filter universe top-10% là thủ phạm (+14,225 vs −1,945 khi bỏ filter)**. Đang dở: train
selector unfiltered leak-free deploy-grade (kernel Kaggle RUNNING) → build_ds → fanout → xác nhận ~+14k. Trigger cũ đã xóa; session mới đọc §4 runbook + tự tạo checkpoint mới.
