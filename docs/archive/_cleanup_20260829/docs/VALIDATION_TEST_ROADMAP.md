# VALIDATION & TEST ROADMAP — Implement Preflight Gate + Test framework WFO/HPO (2026-07-11)

> **Quan hệ tài liệu:** `DATA_VALIDATION_FRAMEWORK.md` = **CÁI GÌ** (spec 19 loại lỗi, đã duyệt sơ bộ với Uni 2026-07-11).
> File này = **LÀM THẾ NÀO + AI ĐIỀU PHỐI** (implement từng class, gom code cũ, test framework, re-export, rà model cũ).
> Không chép lại spec — trỏ. Verdict/ngưỡng cuối do Uni chốt (§6).
>
> **Bối cảnh:** đang WFO nhưng dính lỗi dữ liệu → mọi kết luận lớn của dự án đều từ LỖI IM LẶNG
> (`DATA_VALIDATION_FRAMEWORK §5`). Cổng preflight phải chạy TRƯỚC HPO/WFO/backtest, fail-fast.

---

## 0. NGUYÊN TẮC (kế thừa CORE, không lặp)

- **Đo không đoán · fail-fast · Java là nguồn chân lý.** Gate + validator = **Java** (cắm vào `WfoCoordinator`); Python chỉ được dùng cho *validate/compare* đối chiếu (CORE §Thống nhất ngôn ngữ).
- **"Done" = SỐ ĐO**, không phải "lệnh chạy xong". Mỗi validator TRẢ số vào `metrics` để đối chiếu (không PASS suông).
- **Gom trước, viết mới sau.** Đã có ~25 tool validate rời rạc (§2) — WRAP lại vào registry, chỉ code mới ở chỗ GAP.
- **Sửa nhỏ, mỗi thay đổi một mục đích** (codebase ~250 class). KHÔNG refactor hàng loạt.

---

## 1. KIẾN TRÚC — "mỗi loại 1 class + class tổng"

Package mới: `com.binance.chuyennd.ai_ml.validation.preflight` (đã dựng skeleton, chờ `mvn compile` xác nhận).

| Class (skeleton đã có) | Vai trò |
|---|---|
| `Severity` | enum BLOCK / WARN |
| `CheckId` | 19 loại lỗi (A1..F2) + nhóm + severity mặc định + cờ `expensive` (rẻ/đắt) |
| `ValidationResult` | kết quả BẤT BIẾN 1 check: passed + severity + message + **metrics (số đo)**; factory `pass/fail/warn` |
| `DataValidator` (interface) | contract: `id()` + `validate(ctx)`; mỗi loại = 1 class con implement |
| `PreflightContext` | handle dùng chung (AerospikeClient 226, WFO_DATA_DIR, predDir, sampleSize, env, ExpectedRanges) — validator KHÔNG tự lấy riêng (chống lệch nguồn) |
| `ExpectedRanges` | khai báo PRE-REGISTER (range/nguồn, records/tháng, min/max feature, số fold) — §1.4 spec |
| `ValidationReport` | gom kết quả → markdown + verdict (BLOCK-fail nào → FAIL); ghi file (KHÔNG ổ C) |
| `Tier` | FAST (rẻ, inline) / SLOW (đắt, chạy ngoài theo trigger) / ALL |
| `ValidationStamp` | con dấu "dataset đã validate SLOW" (fingerprint md5 + env + gateVersion) — WFO đọc để khỏi chạy lại đắt |
| `PreflightGate` | **class tổng**: register validator, chạy theo tầng, `assertReadyForWfo()` (cổng WFO) + `runFullAndStamp()` (validate ngoài) |

**Cơ chế gắn (Uni chốt 2026-07-11: "nhanh gắn vào, lâu chạy ngoài") — 2 TẦNG:**
- **FAST inline** — đầu `WfoCoordinator.init()/reset()` (trước `buildJobs`) + đầu HPO: `gate.assertReadyForWfo(ctx, fingerprint, env, stampPath, reportPath)`. Chạy check rẻ + đòi có `ValidationStamp` hợp lệ cho (dataset md5, env). Thiếu/lệch → THROW → `System.exit(1)`.
- **SLOW ngoài** — theo TRIGGER (run đầu / data mới / đổi env Oracle→Kaggle / gen mới / bump `GATE_VERSION`): `gate.runFullAndStamp(...)` chạy đắt, PASS thì đóng stamp.
- Kết quả: KHÔNG chạy đắt mỗi lần WFO, nhưng KHÔNG WFO nào chạy trên data chưa validate / đã đổi / sai env.

---

## 2. BẢN ĐỒ CODE HIỆN CÓ → 19 LOẠI (REUSE / WRAP / GAP)

> Cột "Trạng thái": **WRAP** = có tool làm việc này, bọc lại thành `DataValidator`; **GAP** = phải viết mới; **VERIFY** = chỉ cần kiểm cờ/flag.

| Check | Loại | Code hiện có (nguồn) | Trạng thái |
|---|---|---|---|
| A1 | Pred thiếu giai đoạn | `validate_data/predictmarket/CheckGapPredictMarket`, `predictsymbol/CheckGapPredictSymbol`, `CheckLabel6Predictions`, task 156 | WRAP |
| A2 | Lệch range nguồn | `predictmarket/ValidateMarketPredictConsistency` (một phần) | WRAP+GAP |
| A3 | Ghost ticker | `validation/data/CleanTickerGhostAndTail`, `/tmp ScanGhostFull/CheckGhost` (WFO_DATAFLOW §9) | WRAP |
| A4 | Fold WFO thiếu | `wfo/framework/WfoJobStore` + `WfoCoordinator status` | GAP (check nhỏ) |
| B1 | Label từ giá OOS | `validation/predict/funding/ValidateFundingOOS`, `ml/training/gen_funding_wf_predictions.py` (purge) | WRAP+GAP |
| B2 | Feature dùng tương lai (shuffle) | — | GAP (Python compare) |
| B3 | Embargo < max holding | — (embargo 72h hardcode ở pred) | GAP |
| C1 | NaN/Inf | `validation/data/FeatureQualityAnalyzer`, `ValidateFundingOOS` (report 0 NaN) | WRAP |
| C2 | Giá phi lý | `validate_data/marketobject/ValidateMarketObjectConsistency`, `ticker/ValidateAerospikeVsBinance`, bug `DataManagerAerospikeFloatSim:940` | WRAP |
| C3 | Trùng (ts,symbol) | một phần trong `CheckGap*` | GAP |
| C4 | Scale sai | `FeatureQualityAnalyzer`, `data/ProductionFeatureStabilityChecker` | WRAP |
| D1 | Timezone funding | `validation/data/HistoricalFundingCrawlerLocal` (bối cảnh) | GAP |
| D2 | Gap thời gian (1440) | `marketobject/CheckGapMarketObject`, `ticker/CheckGapTicker`, `predict*/CheckGap*` | WRAP (mạnh) |
| D3 | Off-by-one nến | `BacktestIntegrityGuard` (`BLOCK_INTRABAR_LOOKAHEAD`) | VERIFY |
| E1 | Model mất provenance | `wfo/framework/WfoDataset` manifest.txt (một phần) | WRAP+GAP |
| E2 | md5 mismatch | `WfoDataset.load()` verify md5 3 file | WRAP |
| E3 | Cutoff im lặng | — (manifest chưa ghi train range model) | GAP |
| F1 | Env fallback im lặng | — (WFO_SMART_CACHE / WFO_FUNDING_PRED_DIR fallback lặng) | GAP |
| F2 | Config version drift | `RunHpoMaster_Distributed` CONFIG_VERSION | VERIFY |

**Kết luận bản đồ:** phần lớn là **WRAP** (D2/C1/C2/A1/A3/E2 đã có tool tốt) → công thật nằm ở GAP: A4, B2, B3, C3, D1, E3, F1 và bọc-chuẩn-hoá phần WRAP về contract `DataValidator`.

---

## 3. LUỒNG CÔNG VIỆC + PHỤ THUỘC

```
WS0 (nền)  ── skeleton PreflightGate + ExpectedRanges  ──► (đã dựng, chờ compile)
                       │  (blocks WS1)
        ┌──────────────┼───────────────────────────────┐
        ▼              ▼                                 ▼
WS1 validate      WS2 test framework WFO/HPO       (độc lập nền)
19 validator      unit-test WfoDataset/Coordinator
   │  (gate xanh gác WS3/WS4)                            
   ▼                                                     
WS3 re-export data thiếu/sai  ◄── cần Aerospike/226      
   │                                                     
   ▼                                                     
WS4 rà model cũ full-data + validate chặt ◄── cần chạy sim/WFO 226
```

- **WS1 — Validate (21 loại):** phụ thuộc WS0. Fan-out theo 6 nhóm, chia task nhỏ (§4).
- **WS2 — Test framework WFO/HPO:** ĐỘC LẬP với WS1 (chỉ cần WS0 tối thiểu). Unit-test chạy LOCAL, không Aerospike: parse `market.bin/pred.bin/funding.bin`, verify md5, số cửa sổ = 17, embargo/purge, `buildFundingFromWfFiles` decode horizon (score = 1−P(win)), fold count. Dùng fixture bin nhỏ.
- **WS3 — Re-export data thiếu/sai:** GÁC bởi WS1 (validate chỉ ra thiếu gì mới export đúng chỗ). Chạm Aerospike/226 → chạy trên máy bạn/226.
- **WS4 — WFO head-to-head (model cũ vs maxFav3@4h):** GÁC bởi WS1+WS3 (data đủ + sạch mới so công bằng). Chạy WFO cả 2 model trên CÙNG dataset/cửa sổ/config → bảng so sánh (§7 B3-B5). Chạy trên 226.
- **WS5 — Tối ưu model + WFO lại (§7 B7-B8):** GÁC bởi **cổng quyết định B6** (chỉ làm nếu maxFav3@4h ĐẠT ngưỡng). Tối ưu (HPO/feature/target) → model mới → trigger re-validate (stamp) → WFO lại. Chạy trên 226/Kaggle.

---

## 4. TASK BREAKDOWN (tasks/NNN.md — front-matter + acceptance pre-register)

Đánh số nối tiếp dãy hiện tại (…156). Mỗi task theo schema `AGENT_WORKFLOW §3` + acceptance **kiểm-được-bằng-máy**.

| Task | Luồng | Nội dung | resource | depends_on | Acceptance (pre-register) |
|---|---|---|---|---|---|
| 200 | WS0 | Skeleton preflight + compile + hook stub | local | — | `mvn -q compile` PASS; 7 class có; `PreflightGate.main` chạy rỗng exit 0 |
| 201 | WS1-A | Nhóm A Coverage (A1-A5, gồm Survivorship) | local/226 | 200 | 5 validator trả metrics; A1 phát hiện gate 2021-2022 (regression task 156); A5 coin DEAD có mặt trước ngày chết |
| 202 | WS1-C | Nhóm C Values (C1-C4) | local/226 | 200 | C1 NaN=0; C2 bắt giá≤0/nhảy>50%; C3 dup=0; số khớp scan hiện có |
| 203 | WS1-E+F | Provenance E1-E3 + Config F1-F2 | local | 200 | E2 md5 khớp; F1 fail khi thiếu env bắt buộc; F2 khớp CONFIG_VERSION |
| 204 | WS1-B | Leakage B1-B4 (đắt, sample) | 226/kaggle | 200,202 | B1 max(ts_train)<min(ts_oos)−embargo mọi fold; B3 embargo≥max-holding đo thật; B4 population/basket tính ≤t |
| 205 | WS1-D | Time D1-D3 | local/226 | 200 | D2 đếm phút/ngày; D3 verify `BLOCK_INTRABAR_LOOKAHEAD=true` |
| 206 | WS1 | Cắm 21 validator + `assertReadyForWfo` (FAST inline + stamp) + `runFullAndStamp` + hook `WfoCoordinator` | oracle | 201-205 | gate chạy đủ 21; FAST chặn inline; thiếu/lệch stamp SLOW → WFO refuse; PASS ngoài → đóng stamp |
| 210 | WS2 | Unit-test framework WFO (WfoDataset/Coordinator/Worker) | local | 200 | ≥1 test/parse-bin + số-cửa-sổ + horizon-decode; chạy `mvn test` xanh |
| 220 | WS3 | Re-export data thiếu/sai (theo report WS1) | heavy_226 | 206 | records/tháng đạt ngưỡng ExpectedRanges; preflight A1/A2 PASS lại |
| 230 | WS4 | Rà toàn bộ model cũ + full-data, validate chặt | heavy_226 | 206,220 | mỗi model: manifest E1-E3 PASS + WFO leak-free rerun; bảng so sánh với maxFav3@4h |

> **Lưu ý test harness:** repo CHƯA có `src/test` + JUnit chưa khai trong pom. Task 210 phải thêm dependency test + tạo `src/test/java` (thay đổi pom → bump nhẹ, review). Nếu Uni không muốn đụng pom: fallback = test dạng `mainX()` assert tay (kém chuẩn hơn).

---

## 5. ĐIỀU PHỐI (master) — AI CHẠY GÌ, Ở ĐÂU

| Việc | Chạy được trong phiên Cowork này? | Nơi chạy thật |
|---|---|---|
| Viết roadmap + task file + skeleton code | ✅ (đã làm) | — |
| Code 19 validator + unit-test (WS1/WS2) | ✅ subagent viết code | — |
| `mvn compile` / `mvn test` verify | ❌ (sandbox thiếu javac/maven) | **máy bạn** (IntelliJ/maven) |
| Chạy validator/gate trên data thật | ❌ (không tới Aerospike/226) | **226** (qua SSH) |
| WS3 re-export · WS4 rà model | ❌ | **226** |

**Cơ chế Uni chọn:** tôi (CDK) drive trực tiếp bằng **subagent** để VIẾT code + task; phần **chạy/verify** giao máy bạn/226 (hoặc `orchestrator/supervisor.py` nếu bật). Tôi KHÔNG tự tuyên PASS trên data khi chưa có số thật — trả về task NEEDS_HUMAN nếu chưa verify được.

### 5b. CHẠY VALIDATE SONG SONG Oracle + Kaggle (Uni chốt 2026-07-11)
Máy dev KHÔNG có data → KHÔNG chạy validator ở local. Chạy NGAY nơi data ở (data-locality), song song:

| Môi trường | Data có sẵn | Validator chạy | Ghi chú |
|---|---|---|---|
| **Oracle** (Aerospike 127.0.0.1:3222 ns=test) | kline_1m_opt, market_data_object, symbol_lifecycle, funding_data, mapper, gate pred, wfo_jobs | A1,A3,A4,A5, C1-C3, D1-D2, F1-F2, D3 (cheap full-scan `ctx.client()`) | tầng FAST; jar deploy lên Oracle, `java ... PreflightGate` |
| **226 / Kaggle** | wfo_dataset file bin (market/pred/funding + manifest), predict_wf_*.bin, OI mega-merge 138M | A2 (range từ bin), E1-E3 (manifest/md5), B1-B4 (leak, sample), C4 | tầng SLOW + việc cần OI-merge (>23GB RAM → Kaggle 30GB) |

- **Mỗi env validate phần của nó → stamp riêng theo (fingerprint, env).** Dataset "sạch toàn phần" = hợp mọi stamp phủ đủ 21 loại. `ValidationStamp.env` đã hỗ trợ.
- **CẦN tinh chỉnh nhỏ (task 207):** phân biệt "validator thiếu INPUT ở env này" (SKIP, bình thường khi chạy song song) vs "lỗi hạ tầng thật" (NEEDS_HUMAN). Hiện cả hai đều ném → infra-error. Thêm ngữ nghĩa SKIP + gộp stamp nhiều env cho verdict tổng.
- **Local chỉ dùng để:** build jar (`mvn package`) + unit-test framework (`mvn test`, task 210 — KHÔNG cần data). KHÔNG chạy validator data ở local.

---

## 6. QUYẾT ĐỊNH ĐÃ CHỐT (2026-07-11, chi tiết `DATA_VALIDATION_FRAMEWORK §4b`)

1. **Ngưỡng:** F2 nâng WARN→BLOCK. BLOCK = A1-A5, B1, B3, B4, C1-C3, D3, E1-E3, F1-F2. WARN = B2, C4, D1, D2 (D2 escalate BLOCK nếu chạm majors / tụt coverage cửa sổ).
2. **Sample:** N=100/(tháng×tier), tier={majors, top, mid, tail}; cell thưa lấy hết; B1/B4 thêm 100 quanh ±embargo mỗi biên fold.
3. **Bổ sung 2 loại → 21:** A5 Survivorship, B4 Cross-sectional/population leak. Lỗi đo-lường (maeLow/maxDD) → WS2, không phải preflight.
4. **Ưu tiên:** 21 loại song song; review A+E → C → B → D/F.

**Cơ chế:** 2 tầng — FAST inline (đầu WFO/HPO), SLOW ngoài theo trigger + `ValidationStamp`. Trigger re-validate: run đầu · data mới (md5 đổi) · đổi env (Oracle→Kaggle) · gen model/pred mới · bump `GATE_VERSION`.

---

## 7. CHIẾN DỊCH END-TO-END (mục tiêu Uni chốt 2026-07-11) — có CỔNG QUYẾT ĐỊNH

Mục tiêu cuối KHÔNG phải "có tool validate" mà là: **data sạch → so công bằng model cũ vs maxFav3@4h → nếu maxFav3@4h thật sự OK mới đầu tư tối ưu model → rồi WFO lại.** Đi đúng thứ tự, mỗi bước gác cổng bước sau.

| B | Bước | Việc | Task | Gác cổng |
|---|---|---|---|---|
| 1 | Đủ tool validate | 21 validator + gate 2 tầng + hook | 200-206, 210 | compile/test local xanh |
| 2 | Data sạch | chạy validate (SLOW full) → backfill chỗ thiếu/sai → validate lại tới PASS | 220 | **preflight PASS toàn bộ BLOCK + đóng stamp** |
| 3 | WFO model CŨ | WFO leak-free trên data sạch (cùng config/fee/slippage/guard) | 230 | ra số WFE/%OOS-dương/maxDD |
| 4 | WFO maxFav3@4h | WFO trên **CÙNG** dataset + **CÙNG** cửa sổ + **CÙNG** CONFIG_VERSION | 230 | ra số cùng khuôn |
| 5 | So sánh head-to-head | bảng đối chiếu apples-to-apples | 230 | trình Uni, KHÔNG tự kết verdict |
| 6 | **CỔNG QUYẾT ĐỊNH** | maxFav3@4h đạt ngưỡng pre-register? | — | **Uni quyết:** ĐẠT → sang B7; KHÔNG đạt → §6 SOLUTION_FRAMEWORK (đừng nhảy vào tối ưu) |
| 7 | Tối ưu model | HPO/feature/target để edge tốt nhất (chỉ khi B6 ĐẠT) | 240 | edge cải thiện đo được |
| 8 | WFO lại | WFO model tối ưu → model mới = **trigger re-validate** (stamp) trước khi chạy | 250 | preflight PASS + WFO số mới |

**Điều kiện TÍNH TOÀN VẸN so sánh (B3-B5) — nếu vi phạm thì so sánh VÔ NGHĨA:**
- Cùng `wfo_dataset` (cùng md5), cùng 17 cửa sổ, cùng embargo, cùng `CONFIG_VERSION`, cùng fee/slippage/guard bật. Chỉ khác DUY NHẤT model/pred.
- Ngưỡng "OK" cho B6 **pre-register TRƯỚC khi chạy** (validate_criteria.md: WFE median ≥ 0.5, %OOS-dương ≥ 70%, maxDD-OOS xấu nhất ≤ 50% — Uni chốt cuối). Không định ngưỡng sau khi thấy số.
- ⚠️ maxDD trong WFO có thể HIỂU NHẸ (chưa có margin-call thật — ROADMAP Bước 3) → so sánh tương đối OK, nhưng maxDD tuyệt đối phải caveat.
- B7→B8: model tối ưu là artifact MỚI → theo cơ chế stamp, BẮT BUỘC chạy lại validate FULL (provenance E1-E3 + leak B) trước khi WFO — chống overfit lọt lưới.
