# NSEL — IMPLEMENT + KHỚP NỐI (vòng 1: J-A + jar; J-B/J-C CHƯA CHẠY)

Ngày 2026-10-08. Pre-reg `docs/prereg/PREREG_NSEL.md` (9986c929) §2/§3; thiết kế `NSEL_P0_CODE_20261008.md` (23e4204a), `NSEL_P0B_ADDLEG_20261008.md` (15ea876b).
Branch `feat/nsel` (từ module 9986c929). Commit code `094fd7c0`, test `df021437`. Phạm vi vòng này (MASTER): implement + unit test + jar + dataset. **KHÔNG** đẩy kernel, **KHÔNG** merge module. 0 Java sim trên Oracle, 0 chạm 242/shadow.

## 1. Kết quả
| khớp nối | trạng thái | số |
|---|---|---|
| J-A unit test | **PASS** | `mvn -o test` toàn module: 240 → **259** test (42 → 44 lớp), 0 fail. Mới: `NselGateTest` 12, `NselCoreAddTest` 7 |
| Build jar | OK | `target/binance-java-sdk-1.2.4.jar` sha256 `b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2` (build từ HEAD df021437, cây sạch) |
| Dataset | đã tạo | `chuyendinh/sim-jar-nsel` (sim.jar + prof_r4_kg0_k16_f015_g155.properties md5 0e0caef0) |
| J-B OFF byte-identical (gqsf-a1 / gqsf-s7) | **CHƯA CHẠY** | out dự kiến `nsel-jb-s42`, `nsel-jb-s7`; md5 đích = md5 printDone của gqsf-a1 / gqsf-s7 |
| J-C port penalty (flat3-cp-p1) | **CHƯA CHẠY** | out dự kiến `nsel-jc` |
| Merge module | **KHÔNG** (chờ J-B/J-C) | |

## 2. Key (mọi key mặc định ⇒ hành vi cũ)
| key | mặc định | đọc ở | ý nghĩa |
|---|---|---|---|
| `NSEL_ADD_ENABLED` | false | `Configs.java:168`, parse `:929` | bật tầng THÊM |
| `NSEL_ADD_TOPK` | 32 | Configs | hạng tối đa tầng THÊM; selector xét tới max(K_LÕI, K_THÊM), **không** đổi `SELECTOR_RANK_TOPK` (final) |
| `SIM_NSEL_ADD_ROLLING_PCT` | (vắng; bắt buộc khi bật) | `NselGate.init` | pct buffer THÊM (pre-reg 0,999915) |
| `SIM_NSEL_ADD_ROLLING_DAYS` | 90 | `NselGate.init` | cửa sổ buffer THÊM (warm-up 7 ngày như LÕI) |
| `NSEL_ADD_F1_MIN_BARRET` | NaN (tắt) | Configs | F1: leg0 THÊM chỉ vào khi `(close−open)/open > ngưỡng` nến quyết định (M2: −0,01) |
| `SIM_NSEL_CORE_ADD` | false | Configs (`NSEL_CORE_ADD`) | CORE_ADD |
| `NSEL_CORE_ADD_MAX_PER_CLUSTER` | 1 | Configs | trần CORE_ADD/cụm |
| `SIM_CRASH_ENTRY_PENALTY` | 0 | `Configs.java:121`, parse `:959` | port efd85d6d: giá vào ×(1+pen) nếu nến quyết định ≤ −1%, mọi loại chân |
| `GATE_BUFFER_TOPK` | **ĐÃ BỎ** | — | còn khai ⇒ fail-fast (sim + live) |
| `LIVE_NSEL_*` | — | — | live chưa hỗ trợ ⇒ fail-fast |

## 3. Thay đổi code (file:line tại df021437; `SIM` = research/SimulatorMarketLevelTicker1MStopLoss.java)
- **NselGate.java (mới, 248 dòng)** `ai_ml/onnx/entry`: `GateRatioBuffer` thứ 2 + pct/days riêng; `init` `:56` (đọc key + fail-fast, gọi SAU `GateRollingRatio.init`); `validate` `:83`; `failIfLive` `:124`; `addThreshold` `:196`; `decide` `:208` — nạp r THÊM cho mọi hạng ≤ K_THÊM khi sổ không đầy (kể cả ứng viên đã qua LÕI); LÕI pass ⇒ TIER_CORE; ngược lại q_add ⇒ F1 ⇒ TIER_ADD. Không nạp/không đọc buffer LÕI.
- **AIRejectFilter.java**: `FilterResult.nselTier` `:38`; bỏ nhánh `checkOnly`/GATE_BUFFER_TOPK (chuỗi `if` LIVE/GRR/base nguyên văn `:108`); `entryGateNsel` `:136` (hạng ≤ K_LÕI đi NGUYÊN `entryGate` 5 tham số ⇒ buffer LÕI/noteCandidate/skipFull y nền; hạng > K_LÕI không chạm LÕI); `corePeekPass` `:161` (queryOnly, không nạp, không đếm).
- **GateRollingRatio.java**: `thresholdCheckOnly` → `thresholdQueryOnly` `:133` (giữ helper queryOnly); `ratio()` `:138` cùng biểu thức r với `threshold`.
- **SIM**: counter `:100-113`; selector K tường minh khi NSEL bật `:429`; nhánh coin đang giữ `nselOnHeld` `:460` → `:828` (đếm would bằng queryOnly — chạy cả khi NSEL OFF; CORE_ADD khi cụm leg0 THÊM và < max/cụm); log `[CRASH-PENALTY] SUMMARY` `:667`, `[NSEL]` `:672` (luôn in); `gridLegCount` loại chân CORE_ADD `:771`; `selectCands(pred,k)` `:783`; `coreAddClusterEligible` `:807`; `isCrashBar` `:816`; `createOrder(..., nselMode)` `:1447`; CORE_ADD bỏ qua entryGate `:1476`; gate 2 tầng `:1492`; penalty `:1547`; CORE_ADD bậc grid 0 `:1614`; type CORE_ADD + nselTier `:1701`; counter tầng/loại + `[CRASH-PENALTY]` từng chân SAU mọi return `:1744`; `NselGate.init()` `:1057`, `:1787`.
- **Configs.java**: `CRASH_ENTRY_PENALTY` `:121`; key NSEL `:168-177` (thay field GATE_BUFFER_TOPK); parse `:929-933`, `:959`.
- **MarketLevelChange.java** `:43` `CORE_ADD` thêm CUỐI enum (ordinal cũ giữ). **OrderTargetInfoTest.java** `:61` `nselTier` (0 LÕI mặc định, 1 THÊM, 2 CORE_ADD; không ghi printDone).
- **DetectEntrySignal2TradeNormal.java** `:1376` `NselGate.failIfLive()` sau `LiveGateRollingRatio.init()` (live không đổi hành vi khi profile sạch).

## 4. Nhận diện trong printDone
- Chân CORE_ADD: cột `type` (marketLevelChange) = **`CORE_ADD`**. Logic bên trong createOrder chạy như `PREDICT_SYMBOL_TRADE` (sizing/U_MAX/CONC-PC/penalty/grid bậc 0). Cụm gộp lấy level chân cuối; `DcaUtils.getDcaConfig(CORE_ADD)` = null như PREDICT ⇒ DCA không đổi.
- Leg0 tầng THÊM: type vẫn `PREDICT_SYMBOL_TRADE` (giữ script chấm); tầng lấy từ dòng SLF4J `NSEL_LEG sym tOpen tMs type tier rank` (chỉ in khi NSEL bật) — ghép theo (sym, start) như `SELRANK`.
- Chân bị phạt: dòng `[CRASH-PENALTY] leg sap ... type=<type:tier>`; SUMMARY có `byTypeTier`.

## 5. Quyết định thiết kế / sai khác cần MASTER biết
1. CORE_ADD gate LÕI dùng **queryOnly** (theo pre-reg §2, khác P0B §3.1 "r được nạp"). `queryOnly` chỉ có thể tính trước q của giờ từ CÙNG tập r có ts < giờ ⇒ cùng q với `addAndQuery` (test `corePeekDoesNotChangeCoreDecisions`, `corePeekMatchesGateDecision`). Phụ: bộ đếm log `beforeFirst` của `[GATE-RATIO]` có thể lệch (không vào printDone).
2. Counter `core_on_held_would` chạy **cả khi mọi key NSEL OFF** (để J-B kiểm không side-effect); `core_on_held_by_add_would` chỉ > 0 khi THÊM bật (OFF không có cụm leg0 THÊM). Would không xét bookFull.
3. `add_rej_cap` = add_pass − leg0 THÊM thật mở; `core_add_rej_cap` = core_add_attempt − core_add_done (mọi lý do sau gate: budget/U_MAX, CONC-PC, grid, D3D4, ENTRY_SAMPLE, pred null).
4. Chưa làm "cập nhật mốc lệnh LÕI của cụm" / `lastLeg0Ts` (chỉ cần cho F2 — không có trong pre-reg arm M1/M2).
5. Penalty: biểu thức float32 y efd85d6d; counter dời ra sau mọi return ⇒ `[CRASH-PENALTY] SUMMARY total` sẽ THẤP hơn log flat3-cp-p1 (1096) — dự kiến ≈ số chân sập trong printDone (1074). J-C so md5 printDone, không so counter.
6. `LiveGateRollingRatio.thresholdCheckOnly` để nguyên (dead code, không gọi) — không sửa class live.
7. Build cần `config/PrivateConfig.java` (gitignored) — copy từ repo chính như các worktree trước; KHÔNG commit.

## 6. Còn thiếu (vòng sau, MASTER giao)
- J-B: 2 kernel jar mới, mọi NSEL OFF, penalty 0, override copy từ log gqsf-a1 (seed 42) / gqsf-s7 (seed 7) ⇒ md5 printDone phải trùng; đọc `[NSEL] core_on_held_would` (> 0 kỳ vọng) để xác nhận queryOnly chạy mà không đổi kết quả.
- J-C: 1 kernel cấu hình flat3-cp-p1 (penalty 0,0069) ⇒ md5 printDone trùng; khác ⇒ diff printDone.
- Merge `feat/nsel` → module (--no-ff) chỉ khi J-A/J-B/J-C PASS.

JSON: `docs/result/NSEL_IMPL_JOINTS.json`.
