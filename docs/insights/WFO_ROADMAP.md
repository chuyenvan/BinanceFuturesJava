# WFO_ROADMAP — sub-roadmap + HIỆN TRẠNG SỐNG (Walk-Forward)

> **Quan hệ:** đây là CHI TIẾT của [ROADMAP](../ROADMAP.md) **Bước 4 (WFO)**. ROADMAP giữ Bước 4 = 2 dòng pointer;
> mọi chi tiết + trạng thái live nằm ở đây để KHÔNG phình context tổng.
> **Hub file WFO:** kiến trúc → [WFO_FRAMEWORK_DESIGN](WFO_FRAMEWORK_DESIGN.md) · leak L0–L5 → [WFO_LEAKS_TODO](WFO_LEAKS_TODO.md)
> · hàm mục tiêu/ngưỡng → [WFO_OBJECTIVE_RESEARCH](WFO_OBJECTIVE_RESEARCH.md) · runbook thao tác → [reports/LEAKFREE_WFO_RUNBOOK](../reports/LEAKFREE_WFO_RUNBOOK.md)
> · verdict báo cáo → [reports/wfo_strategy_window.md](../reports/wfo_strategy_window.md) · nhật ký phiên → [reports/overnight_worklog](../reports/overnight_worklog.md).

## 1. HIỆN TRẠNG LIVE (cập nhật 2026-07-02) — vòng lặp "leak-free WFO iteration-1 (funding)"

Mục tiêu vòng này: chạy WFO với **funding leak-free** (giữ market/pred hiện tại) → so verdict với bản rò rỉ,
để đo "edge funding còn lại bao nhiêu khi bỏ leak". Cô lập đúng 1 biến (funding).

**Topology (đã đo, sửa hiểu nhầm cũ):** pipeline WFO đọc/ghi Aerospike **LOCAL trên Oracle** (127.0.0.1:3222, ns=test)
qua `getClient226()` — config `AEROSPIKE_HOST_226=127.0.0.1`. KHÔNG dùng server 226. *(Khúc phiên trước từng
nghi "226 disk 97% chặn" là SAI — nhầm server; Oracle disk 65G trống.)*

| Việc | Trạng thái |
|---|---|
| Fix scanAll cho Aerospike 8 | ✅ nâng `aerospike-client 5.1.6→6.1.11` (partition-query), commit **f43a1aa**. Đo: scanAll market=2,804,363 + pred=2,819,841 sạch. *(client cũ dùng scan legacy → server 8 trả "Unsupported Server Feature"; jar cũ cũng lỗi → không phải do build.)* |
| Funding leak-free (predictions) | ✅ `gen_funding_wf_predictions.py` (commit 57ddb49) — 17 fold walk-forward, per-fold train<cutoff→predict OOS, leak-assert giữ mọi fold. Output `~/claudedata/wf_pred/*.bin` (26B/rec, 3,718,490 rec). Horizon Uni chốt = **24h**. |
| Dataset leak-free `wfo_dataset_wf` (Oracle) | ✅ market.bin+pred.bin từ scanAll (client 6.1.11, giữ nguyên set cũ); **funding.bin tự dựng** từ predict_wf: 24h, `score=1−P(win)` (khớp `decodeSelectorMapToPrimitiveArray` + engine "điểm thấp=ưu tiên"), forward-fill 15-phút→**per-phút** (khớp sim tra `time2SymbolPred.get(time)` exact per-phút). 2,758,365 entry. `WfoDataset.load()` verify md5 PASS. |
| Function-test 2 window × N=3 | ✅ sim chạy sạch với funding leak-free (WIN0 WFE=0.024 pnl=+340; WIN1 WFE=−0.005 pnl=−53). Sơ bộ, chưa kết luận. |
| Full WFO 17 window × N=30 | 🔄 ĐANG CHẠY (2 worker Oracle, train-12/oos-3). **Verdict PENDING.** |

**Caveat phải giữ khi đọc verdict vòng này:**
- **Coverage funding khác:** leak-free ~20 coin/tick (chỉ coin đủ feature+label 24h) vs set v5 cũ ~72–150/tick.
  ⇒ verdict phản ánh CẢ (bỏ-leak) LẪN (giảm coverage) — không tách được 2 cái trong vòng này.
- **maxDD hiểu nhẹ:** chưa có margin-call thật (ROADMAP Bước 3 chưa tròn).
- **market/pred vẫn là bản cũ** (`ai_pred_market_full_basket_v2`, có thể leak) → đây KHÔNG phải fully-leak-free;
  chỉ funding leak-free. Fully-leak-free = vòng sau (gate leak-free).

**Phát hiện provenance (đã ghi PIPELINE_PROVENANCE):** set ĐỌC THẬT của export là HẰNG SỐ hardcode trong
`DataManagerAerospikeFloatSim` (`funding_pred_1m_v5`, `market_data_object`, `ai_pred_market_full_basket_v2`) —
KHÁC nhãn manifest (`WfoDataset.SET_*` env chỉ đổi nhãn manifest, KHÔNG đổi read thật). Vòng này né vấn đề đó
bằng cách **dựng funding.bin trực tiếp từ file** (không qua read-set constant), nên đúng bất kể.

## 2. PRE-REGISTERED VERDICT (chốt TRƯỚC khi nhìn — [FRAMEWORK_DESIGN §6](WFO_FRAMEWORK_DESIGN.md), [OBJECTIVE](WFO_OBJECTIVE_RESEARCH.md))
PASS cần CẢ 3: `WFE_median ≥ 0.5` · `%OOS-dương ≥ 70%` · `worst OOS maxDD ≤ 50%` (theo tỷ lệ vốn, KHÔNG abs USD).
- **Mốc so sánh (bản RÒ RỈ, commit cb0032b):** WFE median 0.205 (FAIL), %OOS+ 88.2% (PASS), worst maxDD 48.1% (PASS).
- **Loại WFO đang chạy = "loại 1" (pred cố định):** hợp lệ cho câu hỏi hẹp "tham số có generalize không";
  số OOS tuyệt đối các window <2025-06 bị tâng vì pred sinh in-sample (khung này giữ trong mọi kết luận WFO).

## 3. SUB-ROADMAP (thứ tự việc còn lại)
1. 🔄 **Đọc verdict vòng funding-leak-free** (đang chạy) → ghi `reports/wfo_strategy_window.md` + FINDINGS, so cb0032b.
2. ⏭ **Vòng fully-leak-free:** thêm gate/market leak-free (`ai_pred_market_gate_wfo` — hiện chỉ có bản `_smoke`;
   full ở `wfo_gate_pred.csv`, cần nạp đúng format/loader). Khi đó mới trả lời "pipeline có edge thật không".
3. ⏭ **Làm read-set env-configurable thật** (`AEROSPIKE_SET_NAME_FUNDING_PRED`... trong DataManager) để export
   đọc đúng set leak-free, thay vì dựng bin tay — hết provenance rot.
4. ⏭ **Survivorship audit** (SurvivorshipScanTool + crawler data.binance.vision) — universe đúng, hết sống-sót-bias.
5. ⏭ **maxDD trung thực:** margin-call/equity thật (ROADMAP Bước 3 mảnh cuối) rồi đọc lại maxDD WFO.

## 4. HẠ TẦNG CHẠY (tóm tắt — chi tiết ở LEAKFREE_WFO_RUNBOOK)
- jar export/worker leak-free: `~/java/simulator/binance-futures-wfo-lf.jar` trên Oracle (client 6.1.11, MD5-verify khi deploy).
- 1 lệnh: `WfoCoordinator init|reset|status|report strategy_window` (JobStore = Aerospike local qua getClient226).
  Worker: `WfoWorker` (env `WFO_KAGGLE=1 WFO_DATA_DIR=<dataset>`). Function-test: `WFO_MAX_WINDOWS`, `WFO_N_SAMPLES`.
- Dataset build funding.bin: `~/claudedata/build_funding_bin.py` (HZ_IDX=2=24h, forward-fill 15p→phút) + patch manifest md5.
