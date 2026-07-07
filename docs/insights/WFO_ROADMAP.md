# WFO_ROADMAP — sub-roadmap + HIỆN TRẠNG SỐNG (Walk-Forward)

> **Quan hệ:** đây là CHI TIẾT của [ROADMAP](../ROADMAP.md) **Bước 4 (WFO)**. ROADMAP giữ Bước 4 = 2 dòng pointer;
> mọi chi tiết + trạng thái live nằm ở đây để KHÔNG phình context tổng.
> **Hub file WFO:** kiến trúc → [WFO_FRAMEWORK_DESIGN](WFO_FRAMEWORK_DESIGN.md) · leak L0–L5 → [WFO_LEAKS_TODO](WFO_LEAKS_TODO.md)
> · hàm mục tiêu/ngưỡng → [WFO_OBJECTIVE_RESEARCH](WFO_OBJECTIVE_RESEARCH.md) · runbook thao tác → [reports/LEAKFREE_WFO_RUNBOOK](../reports/LEAKFREE_WFO_RUNBOOK.md)
> · verdict báo cáo → [reports/wfo_leakfree_funding_v2_report.md](../reports/wfo_leakfree_funding_v2_report.md) *(coordinator sinh `wfo_strategy_window.md` trên Oracle; bản repo đổi tên theo vòng chạy)* · nhật ký phiên → [reports/overnight_worklog](../reports/overnight_worklog.md).

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
| ⚠️ Full run #1 (17w, 2026-07-02 sáng) | ❌ **VÔ HIỆU** — 13/17 window ZERO_TRADES âm thầm. Root-cause (Uni soi ra từ log): thiếu env `WFO_SMART_CACHE=1` → sim rơi nhánh `IS_KAGGLE_MODE` đọc ticker FILE `kaggle_data_hpo/` (chỉ có 2021-01→2022-06). KHÔNG phải lỗi funding.bin (đã verify align 100% market ts + p24h khoẻ mọi fold). Đã đo: **Aerospike Oracle-local CÓ kline đầy đủ 2021→2026** (sample 5 mốc) → không cần sinh/sync ticker file. ⚠️ **RÀ 2026-07-07 SỬA:** đo lại đầy đủ (scan toàn set, không sample) cho thấy Aerospike ns=test lúc đó chỉ ~13 ngày (5/2022) — có thể đã reset giữa chừng; nguồn ĐẦY ĐỦ 1886 ngày thực ra ở FILE kaggle_data_hpo/daily/. Đã nạp file→Aerospike lại 2026-07-07. Xem [DATA_STATE](../DATA_STATE.md). Diệt tận gốc → [TASK-112](../../tasks/112-bo-mode-kaggle-hpo-config-tuong-minh.md) (bỏ 2 mode, config tường minh + fail-fast, Uni duyệt). |
| Function-test v2 (4w × N=3, `WFO_SMART_CACHE=1`) | ✅ PASS — WIN 2 (OOS=0.57 pnl=+54.6) + WIN 3 (OOS=3.15 pnl=+251.6) từng zero-trade giờ có lệnh; 0 ZERO_TRADES; RAM ổn. |
| Full WFO v2: 17 window × N=30 | ✅ XONG 2026-07-02 18:20. **VERDICT: ❌ FAIL/REVIEW** — WFE median **0.098** (FAIL <0.5) · %OOS-dương **76.5%** (13/17, PASS) · worst ddPct **30.7%** (PASS). Report: [wfo_leakfree_funding_v2_report.md](../reports/wfo_leakfree_funding_v2_report.md). Đọc kèm caveat: (i) 4 window gần-zero-lệnh (2023Q1 0, 2023Q4 8, 2025Q2 0, 2025Q3 4 lệnh) — pnl thật bị V4 che ([TASK-113](../../tasks/113-fitness-v41-do-du-metrics-mintrade-window-that.md)); (ii) WIN 8-10 reject 27-29/30 mẫu → best chọn từ 1-3 mẫu sống = selection noise lớn (N=30/18-gene mỏng); (iii) so cb0032b (WFE 0.205, 88.2%, 48.1%) KHẬP KHIỄNG — khác điều kiện, chờ leaked-rerun. |
| **Leaked re-run (cặp so sánh V4)** | 🔄 ĐANG CHẠY (launch 18:22): dataset cũ `wfo_dataset` (manifest 06-29 ghi `funding_selector_pred_1m_v2`, KHÔNG có dòng provenance LEAKFREE; nhãn set cần verify vì read-set hardcode — provenance-rot đã biết) — CÙNG jar/seed/ticker-aerospike/fitness-V4 với run leak-free v2 → phép so leaked-vs-leakfree đầu tiên cùng điều kiện. |

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

### V4.1 — Fitness thay đổi ngữ nghĩa (TASK-113, pre-registered 2026-07-02)
Ngưỡng verdict GIỮ NGUYÊN (WFE_median≥0.5 · %dương≥70% · worst ddPct≤50%). Ba thay đổi so V4:
1. **WFE median trung thực:** window LOW_TRADES (vd WIN7-8 lệnh OOS) nay đóng góp WFE thật thay vì 0 do
   pnl bị che (V4 return-sớm trước khối thống kê). Median sẽ khác — đây là **chủ đích**, không phải số drift.
2. **%OOS-dương tường minh theo note:** chỉ đếm `oosNote=SUCCESS && oosPnl>0` (kết quả đếm KHÔNG đổi
   với data cũ — window sentinel có pnl thật nhưng note≠SUCCESS nên không được đếm).
3. **Min-trade theo window THẬT:** caller truyền `windowDaysActual` từ range backtest thực; bỏ suy từ
   span lệnh (V4 cũ: 10 lệnh dồn 3 ngày / window 90 ngày → span=3 → minTrades=5 → PASS ngược đời).

**Mốc V4 cũ (leak-free v2: FAIL, WFE 0.098, 76.5%, 30.7%) giữ làm LịCH SỬ** — KHÔNG so trực tiếp
số-với-số với V4.1 (thay đổi semantics nên con số KHÔNG tương đương).

## 3. KIẾN TRÚC TỔNG + LỘ TRÌNH RA WFO HOÀN CHỈNH (master rà 2026-07-02 tối)

### 3a. Kiến trúc 6 lớp (trạng thái đo thật)
```
L1 DỮ LIỆU GỐC    : Aerospike Oracle-local kline/funding/OI 2021→26 ✅ · universe/survivorship ❌ (sống-sót bias)
L2 MODEL PER-FOLD : funding WF 17-fold leak-assert ✅ · gate/market WF ❌ (wfo_gate_pred.csv chưa nạp — vẫn LEAKED)
L3 DATASET OFFLINE: WfoDataset market/pred/funding.bin + manifest md5 ✅ (đã lên cả Kaggle, md5 verify PASS)
L4 THỰC THI       : JobStore CAS+lease ✅ · worker Oracle ✅ · worker Kaggle ✅ (smoke PASS 2026-07-02)
L5 ĐO LƯỜNG       : fitness V4.1 🔄 (TASK-113) · maxDD margin-call ❌ · exit clamp bar.open ❌ (duyệt chưa áp)
L6 VERDICT        : 3 tiêu chí pre-registered ✅ · cặp so leaked/leak-free 🔄 (V4 tham khảo → V4.1 chính thức)
```
Ghi chú phương pháp (đã rà code): window IS/OOS chặn cứng theo range, KHÔNG cần embargo tầng strategy
(embargo thật nằm ở tầng model per-fold — gen_funding_wf leak-assert đã giữ; cần xác nhận horizon-gap trong script).
Caveat thống kê giữ vĩnh viễn: IS 12m trượt 3m → IS chồng lấn 9/12 tháng → 17 window KHÔNG độc lập;
N=30 mẫu/18 gene mỏng → WFE thấp có thể là selection-noise. Tăng N là đòn bẩy chính (Kaggle).

### 3b. 5 giai đoạn (tuần tự theo phụ thuộc; trong mỗi GĐ có việc song song — xem 3c)
- **GĐ0 (đang chạy):** cặp so V4 (leaked re-run) + GATE-112 → jar chuẩn config-tường-minh. [TASK-115]
- **GĐ1 — Đo lường sạch:** TASK-113 → fitness V4.1 + pre-register lại → chạy **cặp so V4.1 = phép so CHÍNH THỨC**
  trả lời iteration-1 ("bỏ funding-leak mất bao nhiêu edge"). 2 vế cùng Oracle/cùng nguồn.
- **GĐ2 — Input sạch hoàn toàn:** nạp `wfo_gate_pred.csv` → Aerospike Oracle-local → export dataset v3
  (funding WF + gate WF) → run **fully-leak-free**. Song song: coverage audit theo quý (giải thích 4 window
  gần-zero: regime hay thiếu data — thấy cả "Date data error 2025xx" trong log leaked) + survivorship audit
  (SurvivorshipScanTool + crawler data.binance.vision) + read-set env-configurable (hết provenance rot).
- **GĐ3 — Sim & thống kê vững:** maxDD margin-call thật (Bước 3 mảnh cuối) + exit clamp `bar.open` (GATE riêng
  từng cái) + scale N bằng Kaggle fleet (state chung = 226 thật qua WFO_STATE_HOST; quy tắc CỨNG:
  **1 experiment = 1 loại node** vì ticker Kaggle đọc 226 ≠ Oracle-local, đã đo file≠aerospike lệch số).
- **GĐ4 — WFO chuẩn cuối:** full run fully-leak-free + universe đúng + metrics thật + N đủ → verdict
  pre-registered quyết: PASS → Golden backtest (funding ON) → go-live nhỏ; FAIL → quay lại câu hỏi edge
  (economic rationale — ai bị ép trade bất lợi và vì sao).

### 3c. Ma trận song song (việc × tài nguyên × phụ thuộc)
| Việc | Node | Phụ thuộc | Đụng jobstore? |
|---|---|---|---|
| TASK-113 code + unit (CCD) | local | 112 merged ✅ | KHÔNG (gate mới đụng) |
| GATE-112 rồi GATE-113 (tuần tự) | Oracle | leaked run xong | CÓ → xếp lịch độc quyền |
| Nạp gate csv + export dataset v3 | Oracle | leaked run xong (RAM) | KHÔNG |
| Coverage audit theo quý (script đọc bin) | local/Kaggle | không | KHÔNG — chạy NGAY |
| Survivorship crawler binance.vision | Kaggle | không | KHÔNG — chạy NGAY |
| Exit clamp + margin-call code (CCD 2) | local | không (khác file 113) | gate xếp sau 113 |
| Kernel folders wfo-worker-{1..5} | local/Oracle | jar ✅ dataset ✅ | KHÔNG — chạy NGAY |

Nguyên tắc điều phối: jobstore `strategy_window` Oracle là tài nguyên ĐỘC QUYỀN — mọi GATE/run xếp hàng;
mọi việc không đụng nó đẩy song song tối đa.

## 4. HẠ TẦNG CHẠY (tóm tắt — chi tiết ở LEAKFREE_WFO_RUNBOOK)
- jar export/worker leak-free: `~/java/simulator/binance-futures-wfo-lf.jar` trên Oracle (client 6.1.11, MD5-verify khi deploy).
- 1 lệnh: `WfoCoordinator init|reset|status|report strategy_window` (JobStore = Aerospike **LOCAL Oracle** ns=test qua getClient226,
  host=127.0.0.1). ⇒ **Kaggle worker KHÔNG poll được jobstore này**; nếu sau này chạy WFO đa-node có Kaggle thì phải
  set `WFO_STATE_HOST` về 226 thật (Kaggle tới được 226) — và nhớ 2 vế 1 phép so sánh phải cùng 1 nguồn dữ liệu (đã đo file≠aerospike).
  Worker: `WfoWorker` — TASK-112: env chỉ còn `WFO_SMART_CACHE=1 WFO_DATA_DIR=<dataset>` (`WFO_KAGGLE` ĐÃ BỎ); nguồn dữ liệu theo `config.properties` của box: `AEROSPIKE_READ_CLUSTER=226` + `TICKER_SOURCE=aerospike` — thiếu/sai key → fail-fast NGAY (hết zero-trade âm thầm kiểu sự cố 2026-07-02). ⚠️ jar CŨ `binance-futures-wfo-lf.jar` (trước TASK-112) vẫn cần env 3 cái cũ. Function-test: `WFO_MAX_WINDOWS`, `WFO_N_SAMPLES`.
- Dataset build funding.bin: `~/claudedata/build_funding_bin.py` (HZ_IDX=2=24h, forward-fill 15p→phút) + patch manifest md5.
