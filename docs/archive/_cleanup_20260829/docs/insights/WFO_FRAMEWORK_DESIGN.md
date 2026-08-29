# WFO Framework — thiết kế "chạy là chạy, không cần nghĩ thêm"

> **Mục tiêu (Uni đặt):** một quy trình/framework mà khi cần chạy WFO chỉ việc khởi động, KHÔNG phải
> phân tích/chia tay/ghép kết quả thủ công nữa. Dùng **mọi tài nguyên trừ 242** (Oracle + 226 + Kaggle
> + Local điều phối). 242 TUYỆT ĐỐI không đụng (chỉ live).
>
> Trạng thái: **ĐÃ DUYỆT (2026-06-29) — bắt đầu code.** 5 quyết định chốt ở mục 6. Kim chỉ nam hàm mục tiêu: WFO_OBJECTIVE_RESEARCH.md.

---

## −1. SỬA THEO PHẢN BIỆN Uni (điểm 3 cũ SAI)

Thiết kế cũ chia "Oracle nhiều job / 226 ít / Kaggle tuỳ chọn" — SAI. Uni chốt: **mọi node coi NHƯ NHAU**
(cùng giành job tự do), chỉ khác **cách lấy dataset**:
- VPS (Oracle/226): đọc **file tĩnh** offline (đã export sẵn).
- Kaggle: đọc **Kaggle Dataset** tương ứng (cùng nội dung, đóng gói cho Kaggle).
- Aerospike: dùng **giống hệt nhau ở mọi node** cho phần state nhỏ (jobs).
→ Worker là MỘT entrypoint chung, env quyết định nguồn dataset. Không phân vai cứng node nào. Cân tải
tự nhiên qua state machine + lease (node rảnh giành job kế tiếp).

---

## −0.5. ⭐ PHÂN TÍCH LUỒNG DỮ LIỆU WFO (Uni yêu cầu phân tích kỹ) — CỐT LÕI

### A. Có HAI loại WFO, luồng dữ liệu KHÁC HẲN NHAU. Phải tách bạch.

**WFO loại 1 — STRATEGY WFO (WFORunner tôi vừa viết):** tối ưu 18 gene chiến lược. Luồng dữ liệu NGẮN:
```
[market + AI-pred + funding ĐÃ CÓ SẴN, BẤT BIẾN] → backtest(genome) → fitness
```
Chỉ ĐỌC 3 khối dữ liệu bất biến + vặn tham số chiến lược. KHÔNG train lại model. Đây là cái mục 1 (offline
file) giải quyết gọn — dữ liệu thực sự bất biến.

**WFO loại 2 — MODEL WFO (WFOGateRunner ĐÃ TỒN TẠI, đã thiết kế rất tốt):** tối ưu/validate MODEL. Luồng
dữ liệu DÀI — đúng cái Uni lo:
```
features (replay extract) → train (Python→ONNX) → model → predict (tại chính features đó) → pred set → backtest
```
Đây là luồng "thay đổi nhưng khá bất biến nếu thiết kế tốt" Uni nói. Nó dài, nhiều mắt xích, RỦI RO LỆCH
INPUT làm hỏng cả chuỗi sau.

### B. WFOGateRunner đã giải quyết luồng dài thế nào (đọc code — đây là MẪU để theo)

Rà `WFOGateRunner.java` + `train_gate_fold.py` + `OnnxInferenceManager.java`, các cơ chế chống-lệch ĐÃ CÓ:

1. **Tách REPLAY khỏi PREDICT (1 lần replay, giữ RAM):** replay mọi phút 1 lần → `featureStore` +
   `labelStore` trong RAM + xuất CSV cho train. Nút cổ chai là replay (~30-45s/ngày), KHÔNG phải train (3s).
   → KHÔNG replay lại mỗi fold. Mọi fold predict từ CÙNG featureStore RAM. **Đảm bảo input nhất quán.**

2. **Feature extract + predict ĐỀU Java, CÙNG class** (`ComprehensiveMarketFeatureExtractor` +
   `OnnxInferenceManager`) đã verify Java↔Python **0.000000**. Python CHỈ train thuần XGBoost→ONNX,
   KHÔNG có nhánh logic feature/backtest nào. → loại nguồn lệch lớn nhất (feature tính 2 nơi khác nhau).

3. **Thứ tự feature KHÓA CỨNG (V3FULL):** `train_gate_fold.py` đọc feature theo thứ tự V3FULL copy chính
   xác từ `OnnxInferenceManager.extractFeaturesV3Full`, KHÔNG theo thứ tự cột CSV, có `assert` thiếu cột.
   → chống lệch "cột CSV xáo thứ tự khi train" — lỗi kinh điển làm model học sai map feature.

4. **featChecksum:** tổng checksum feature in ra để so 2 lần chạy → phát hiện non-determinism.

5. **WFO đúng nguyên tắc:** expanding train từ ANCHOR, OOS=step=3 tháng KHÔNG chồng lấn, mỗi đoạn OOS do
   model CHƯA thấy nó dự báo (không leak). Train < cutoff, predict [cutoff, cutoff+3m).

6. **Ghi FILE thay Aerospike:** ghi pred ra file local (ghi 226 qua mạng = 65 rec/s, nghẽn 99%). Khớp đúng
   nguyên tắc Uni: dữ liệu lớn → file, không nhồi Aerospike.

→ **KẾT LUẬN QUAN TRỌNG:** luồng dữ liệu dài mà Uni lo ĐÃ được giải đúng trong WFOGateRunner cho model
gate 15m. Nguyên tắc toàn vẹn đã có. Framework KHÔNG cần phát minh lại — cần CHUẨN HÓA mẫu này.

### C. Rủi ro lệch input còn lại (điểm Uni cảnh báo "lệch input → cả mớ sau vô nghĩa")

Các điểm CÒN có thể lệch, cần framework chốt chặn:
1. **Snapshot dữ liệu nguồn khác nhau giữa các lần/máy:** nếu Oracle replay từ market_data hôm nay, Kaggle
   từ bản copy cũ → feature khác → model khác. → **BẮT BUỘC manifest md5 + version cho mọi nguồn**, mọi node
   fail-fast nếu md5 lệch. (Đã từng dính: "stale Kaggle ff/OI source mismatch".)
2. **Feature order / schema drift:** V3FULL khóa cứng ở 1 nơi (OnnxInferenceManager) là nguồn-sự-thật;
   train script COPY. Nếu sửa feature mà quên đồng bộ 2 chỗ → lệch. → framework nên SINH danh sách feature
   từ 1 nguồn (generate file thứ tự, train đọc file đó) thay vì copy tay.
3. **predRisk4H lấy từ set CŨ** (WFOGateRunner giữ predRisk4H từ ai_pred_market_full_basket_v2 để isolate
   biến predReturn15M): đúng cho thí nghiệm isolate, nhưng phải GHI RÕ provenance — pred set nào ghép từ đâu.
4. **Label leakage qua thời gian:** label dùng future (basketMaxGain nhìn 15m tới). Phải chắc train CHỈ tới
   cutoff, label của phút sát cutoff không nhìn quá cutoff vào vùng OOS. (WFOGateRunner: train < cutoff —
   nhưng label phút cuối train nhìn 15m tới có thể chạm cutoff. Cần kiểm: purge/embargo quanh cutoff.)

→ ⚠️ Điểm 4 (embargo quanh cutoff) là rủi ro leak TINH VI chưa thấy WFOGateRunner xử lý rõ — cần kiểm.

### D. Hệ quả cho framework: PHẢI hỗ trợ CẢ HAI loại, chung hạ tầng

| | Strategy WFO (loại 1) | Model WFO (loại 2) |
|---|---|---|
| Đơn vị job | 1 cửa sổ × random-search genome | 1 fold: train→ONNX→predict OOS |
| Dữ liệu vào | 3 khối bất biến (offline file) | featureStore replay + train CSV |
| Tính nặng | N backtest/cửa sổ | 1 replay + train + predict/fold |
| Lệch input? | thấp (chỉ đọc) | CAO (replay→train→predict, đã giải trong WFOGateRunner) |
| Output | best genome + WFE | pred set OOS ghép + backtest + WFE |
| Trạng thái code | WFORunner (mới, chưa test) | WFOGateRunner (đã có, đã thiết kế tốt) |

Framework master-worker + offline + state-machine PHẢI bọc được cả hai dạng job. Mỗi job khai báo "type"
(strategy_window | model_fold) + tham số. Worker chung dispatch theo type. Verdict gom chung (WFE, %dương).

---

## 0. HAI YÊU CẦU CỐT LÕI Uni chốt (định hình toàn bộ)

1. **Dữ liệu OFFLINE** (không Aerospike trên đường chạy). Aerospike chỉ dùng cho dữ liệu nhỏ + thay
   đổi nhiều. Dữ liệu WFO lớn + BẤT BIẾN + đọc-lại-trăm-lần → phải thành FILE offline bất biến, mỗi
   node đọc cục bộ. Aerospike chỉ xuất hiện ở bước EXPORT 1 lần.
2. **Master–worker CÓ TRẠNG THÁI + lease/TTL** (không phải queue thuần). Phải phân biệt rõ: chưa-chạy
   / đang-chạy / xong / chết-giữa-chừng. Worker chết → job tự được giành lại sau khi lease hết hạn.

---

## 1. TẦNG DỮ LIỆU OFFLINE

> **ĐO THỰC (2026-06-28, test export đầu tiên):** scanAll market data 2.8M records từ Aerospike 226 mất
> **~66 PHÚT** (06:38→07:44) — chậm bất thường (trước từng ~25-40s; có thể 226 đang tải nặng/network).
> Dù lý do gì, con số này CHỨNG MINH MẠNH thiết kế offline: nếu mỗi worker scanAll tốn ~1h chỉ riêng
> market, phân tán 5-7 worker đọc 226 là BẤT KHẢ THI. Export 1 lần (chậm, chấp nhận) → file → mọi
> worker đọc cục bộ (nhanh). Đây chính là lý do Uni yêu cầu offline. [cần điều tra vì sao 226 chậm —
> note riêng, không chặn framework.]

### 1.1. Hiện trạng (đã rà)
3 khối WFO cần, đều BẤT BIẾN suốt WFO, hiện mỗi JVM `scanAll` lại từ Aerospike 226 (~25-40s/lần):
| Khối | set 226 | ~records | serialize/record |
|---|---|---|---|
| Market data | market_data | ~2.8M | `MarketDataObject.endCode()` / `decodeMarketDataFromBinary()` (đã có) |
| AI pred (market) | ai_pred_market_full_basket_v2 | ~2.8M | 3 field: long+float+float = 20 byte (Serializable) |
| Funding pred | funding_selector_pred_1m_v2 | toàn set | `long[]` packed (Snappy) |

**Vấn đề phân tán:** 5-7 worker (Oracle+226+5 Kaggle) cùng scanAll đập vào 226 (yếu 15GB) → nghẽn/OOM/
nuốt lỗi. Kaggle đọc 226 qua internet còn chậm ~11×. → KHÔNG scale nếu giữ Aerospike trên đường chạy.

### 1.2. Thiết kế offline
- **`ExportWfoDataset` (chạy 1 lần trên Oracle):** scanAll 3 khối → ghi 3 file binary tuần tự
  `[ts:8][len:4][bytes]...` + manifest (md5, #records, dải thời gian, schema-version). Output
  `/d/claudedata/wfo_dataset/{market.bin, pred.bin, funding.bin, manifest.json}`.
- **Loader offline trong WFORunner:** nếu env `WFO_DATA_DIR` set → đọc 3 file (mmap/buffered) thay
  scanAll. Kiểm md5 manifest trước khi chạy (fail-fast nếu file hỏng/thiếu). Aerospike CHỈ còn ở export.
- **Phân phát file (bất biến → 1 lần):** Oracle giữ gốc → scp 226 → Kaggle upload thành **Kaggle Dataset**
  (cache sẵn, không đọc 226 qua net). Manifest md5 đảm bảo mọi node chạy CÙNG dữ liệu (chống "data drift").
- **Lợi ích:** loại Aerospike khỏi đường chạy; worker đọc file cục bộ (nhanh, không nghẽn 226); Kaggle
  hết phụ thuộc mạng 226; mọi node CÙNG 1 snapshot bất biến (tái lập được — provenance rõ).

> ⚠️ provenance: manifest ghi rõ snapshot từ set nào + ngày export. Model/dữ liệu drift → export lại
> snapshot mới (Direction A), KHÔNG sửa file tay.

---

## 2. MASTER–WORKER CÓ TRẠNG THÁI (không queue thuần)

### 2.1. Vì sao không queue thuần
Queue (pop/push) không lưu "job này đang ai làm, bắt đầu khi nào, đã chết chưa". Worker chết giữa chừng
→ job biến mất hoặc bị làm 2 lần. Cần STATE MACHINE per-job + LEASE.

### 2.2. State machine mỗi job (1 job = 1 cửa sổ WFO)
```
PENDING ──claim(lease)──► RUNNING ──report OK──► DONE
   ▲                         │
   └──lease hết hạn (TTL)────┘   (worker chết → job về PENDING, worker khác giành)
                             │
                             └──report FAIL (n lần)──► FAILED (cần người)
```
- **PENDING**: chưa ai làm.
- **RUNNING**: worker X giữ, có `lease_until = now + TTL`. Worker phải **heartbeat** (gia hạn lease)
  định kỳ. Hết lease mà không gia hạn → master coi worker chết → job về PENDING.
- **DONE**: có kết quả hợp lệ (WFE, OOS fit...). Bất biến.
- **FAILED**: lỗi quá `max_retry` → chờ người.

### 2.3. Store trạng thái — Ở ĐÂU? (quyết định quan trọng)
Vì Uni muốn offline + dữ liệu nhỏ-hay-đổi mới dùng Aerospike: **state nhỏ + đổi liên tục → ĐÂY là chỗ
HỢP cho Aerospike** (ngược với dữ liệu WFO lớn-bất-biến). 2 phương án:
- **(A) State trên Aerospike 226** (set riêng `wfo_jobs`): mỗi job 1 record {state, owner, lease_until,
  result}. claim = `operate` CAS (generation check) — atomic, chống 2 worker giành 1 job. Mọi node
  (kể cả Kaggle) đọc/ghi được qua 226. **Hợp vì state nhỏ + đổi nhiều.**
- **(B) State trên file + master tập trung**: master giữ `jobs.json`, worker xin việc qua master (HTTP/
  SSH). Phức tạp hơn (cần master luôn sống), không tự nhiên với Kaggle.
→ **Nghiêng (A)**: Aerospike đúng vai "dữ liệu nhỏ thay đổi nhiều", CAS sẵn có, mọi node với được.
  Dữ liệu LỚN (market/pred/funding) vẫn offline file. Tách bạch đúng tinh thần Uni: lớn-bất-biến→file,
  nhỏ-hay-đổi→Aerospike.

### 2.4. Chống các lỗi đã gặp
- **Worker chết (Kaggle 12h kill, mất mạng):** lease TTL hết → job tự về PENDING. Không mất job.
- **2 worker giành 1 job:** CAS generation (chỉ 1 thắng). Đã có tiền lệ GenerationPolicy.
- **Job treo (chạy mãi không xong):** lease không gia hạn được vì worker thật sự treo → vẫn về PENDING
  sau TTL; worker mới chạy lại từ đầu job đó (idempotent — mỗi cửa sổ độc lập, seed cố định).
- **Steal job stale:** worker rảnh quét job RUNNING có lease quá hạn → CAS về PENDING rồi claim.

---

## 3. ĐƠN VỊ CÔNG VIỆC & GOM KẾT QUẢ

- **1 job = 1 cửa sổ WFO** (train 12 tháng + OOS 3 tháng). ~18 job cho 2021→2026. Mỗi job độc lập,
  seed cố định theo winIdx → idempotent (chạy lại cho cùng kết quả).
- **Worker làm job:** đọc dữ liệu offline (1 lần/JVM, tái dùng cho nhiều job), random search N mẫu trên
  train → best theo fitness V4 → đo OOS → ghi {bestGenome, IS_fit, OOS_fit, WFE, OOS_pnl, OOS_maxDD}
  vào record job (state→DONE).
- **Gom tự động:** khi tất cả job DONE, master (hoặc 1 lệnh gom) đọc toàn bộ record → dựng bảng WFO +
  tính tổng hợp: **% cửa-sổ-OOS-dương, WFE trung vị, maxDD OOS xấu nhất, độ ổn định gene qua cửa sổ** →
  ghi report `docs/reports/wfo_<timestamp>.md`.
- **Verdict tự động (pre-registered, chốt TRƯỚC khi nhìn):** PASS nếu WFE trung vị ≥ 0.5 + %cửa-sổ-dương
  ≥ 70% + maxDD OOS xấu nhất trong ngưỡng. FAIL/REVIEW ngược lại. In verdict ở đầu report.

---

## 4. PHÂN BỔ TÀI NGUYÊN (mọi node trừ 242)

| Node | Vai trò | Ghi chú |
|---|---|---|
| Oracle 23GB | worker chính (nhiều job) + giữ dataset gốc + chạy export | mạnh nhất, -Xmx18g |
| 226 15GB | worker phụ (ít job) | yếu; đọc dataset file CỤC BỘ (không scanAll chính nó) tránh tải kép |
| Kaggle ×5 | worker song song | dataset = Kaggle Dataset; 12h kill → lease cứu job; KHÔNG với 242 (OK, không cần) |
| Local | điều phối (supervisor) + build + gom report | không chạy backtest nặng |

- Worker là 1 entrypoint chung `WfoWorker` chạy mọi node: nhận `WFO_DATA_DIR` + toạ độ Aerospike-state
  → loop {claim job → làm → ghi → heartbeat}. Cùng 1 jar, khác env.
- Số worker/node = cap (Oracle nhiều, 226 ít, Kaggle 5). Master không cần chia cửa sổ tay — worker tự
  giành job rảnh (cân tải tự nhiên).

---

## 5. "MỘT LỆNH CHẠY" — trình tự không-cần-nghĩ

```
1. (1 lần khi dữ liệu đổi) ExportWfoDataset trên Oracle → 3 file + manifest → phân phát.
2. wfo_init: nạp ~18 job PENDING vào Aerospike-state (set wfo_jobs), ghi config (genome, N, ngưỡng).
3. Khởi động worker mọi node (supervisor task / lệnh ssh): mỗi node chạy WfoWorker loop.
4. wfo_status: 1 lệnh xem bảng trạng thái (PENDING/RUNNING/DONE/FAILED + lease).
5. wfo_report: khi all DONE → gom + verdict tự động → docs/reports/wfo_*.md.
```
Sau lần dựng đầu, mỗi lần chạy WFO chỉ là bước 2→5 (bước 1 chỉ khi dữ liệu đổi).

---

## 6. QUYẾT ĐỊNH ĐÃ CHỐT (Uni duyệt 2026-06-29 — pre-registered, KHÔNG đổi sau khi xem kết quả)

1. **State store:** ✅ Aerospike 226 cho STATE nhỏ (jobs: state/owner/lease_until/result) + file offline cho
   DATA lớn (market/pred/funding). Đúng tách lớn-bất-biến↔nhỏ-hay-đổi.
   *(Annotation 2026-07-02, không đổi quyết định: triển khai THỰC TẾ dùng Aerospike **LOCAL Oracle** ns=test —
   `getClient226()` với `AEROSPIKE_HOST_226=127.0.0.1` — thay vì server 226; nguyên tắc tách state-nhỏ↔data-lớn giữ nguyên.)*
2. **Khởi động worker:** ✅ ssh trực tiếp (KHÔNG qua supervisor.py vòng đầu — đơn giản, dễ debug).
3. **Verdict ngưỡng — PRE-REGISTERED, chốt TRƯỚC khi chạy/xem kết quả:**
   - WFE trung vị ≥ **0.5** (OOS giữ ≥ nửa hiệu năng in-sample)
   - % cửa-sổ-OOS-dương ≥ **70%**
   - maxDD-OOS xấu nhất ≤ **50%** (tức không cửa sổ OOS nào drawdown quá -50%)
   - PASS = thỏa CẢ BA. Không-thỏa-một → FAIL/REVIEW. In verdict đầu report.
4. **N mẫu/cửa sổ:** ✅ function-test nhỏ TRƯỚC (5 mẫu × 2 cửa sổ) → validate done → mới chạy full N.
   Chốt N sau khi test đo thời gian thật.
5. **Tài nguyên — MỘT quy tắc duy nhất:** ưu tiên **Oracle → 226 → Kaggle** (Kaggle ưu tiên CUỐI).
   Worker rảnh giành job theo thứ tự này. BẮT BUỘC test Kaggle (file dữ liệu + môi trường khác VPS) trước
   khi tin Kaggle worker. KHÔNG đẻ thêm quy tắc con — chỉ 1 thứ tự ưu tiên này.

### Ghi chú liên quan (chốt cùng ngày, ngoài 5 câu trên)
- **Funding mặc định OFF** trong HPO/WFO (`Configs.APPLY_FUNDING_FEE=false`); CHỈ bật ở vòng HPO/Golden
  backtest CUỐI trước go-live. Lý do: tác động funding nhỏ (~**1.8%** PnL theo FINDINGS Σfunding=-918 — số 0.9% cũ ghi nhầm, sửa 2026-07-02; maxDD không đổi) nhưng làm chậm
  vòng chạy → không đáng gánh trong hàng nghìn lần eval. Đo: RunFundingImpact (tính-1-lượt-khi-đóng).

### Fitness V4.1 — thay đổi semantics (TASK-113, pre-registered 2026-07-02)
Thay đổi **`HPOFitnessCalculatorV4.evaluateDetailed`** so V4 (ngưỡng verdict §6 điểm 3 GIỮ NGUYÊN):
- **Signature mới:** `evaluateDetailed(allOrderDone, windowDaysActual)` — caller truyền độ dài THẬT của
  range backtest; bỏ suy `windowDays` từ span lệnh (logic cũ cho kết quả ngược đời khi lệnh dồn cục).
- **Reorder thống kê trước constraint:** `totalProfit/ddPct/pctHeldOver7d/calmar/sortino` tính TRƯỚC chuỗi
  TOO_FEW→BURN→OVER_MAXDD→… → nhánh bị loại sớm vẫn có số thật trong `FitnessReport`.
- **6 caller đã cập nhật** (TASK-113): `WFORunner`, `StrategyWfoTask`, `AblationClusterTool`, `FitnessBaselineTool`,
  `MetricDistributionTool`, `SensitivityTool` — mỗi chỗ truyền `windowDays = max(1,(end−start)/TIME_DAY)`.
- **`StrategyWfoTask.aggregate`**: đếm `%OOS-dương` khi `oosNote=SUCCESS && oosPnl>0` (tường minh); bảng
  report thêm cột `oosNote`. V3/HPOFitnessCalculator cũ KHÔNG đổi.
- **Unit GATE A-E local PASS** (TestFitnessV41.java, 2026-07-02): SUCCESS calmar=3.0 ✓; TOO_FEW pnl=160≠0 ✓;
  10lệnh/3d window90d→TOO_FEW(V4 PASS ngược đời→fix) ✓; BURN ddPct>0 ✓; CAPITAL_LOCK pnl=150≠0 ✓.
