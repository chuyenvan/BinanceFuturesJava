# PLAN — Port gate GDV2 (G2) sang LIVE sau key, mặc định TẮT (code + test, KHÔNG deploy)

Pre-reg: commit này (chốt TRƯỚC khi code). Ngày 2026-09-29. Task E1.

## 0. Mục tiêu & verdict

G2 = quantile cuộn `pct=0.99995083` (W=90 ngày) trên tỉ số `r = p15 / (max(0.26787, sp/0.15×1.2876) × SCALE)`
của MỌI lần đánh giá ứng viên PREDICT; `pass ⇔ r > q_t`. Verdict hiện tại: **G2 ≈ R4, CHƯA thay**
(`RESULT_GDV2_EVEN.md`, `RESULT_GDV2_P3.md`). Mục tiêu task: **có sẵn đường LIVE để BẬT khi owner/holdout
quyết, KHÔNG phải làm lại** — mặc định TẮT, không deploy/restart shadow-c3, không chạm 242/holdout 2026.

## 1. Phạm vi & nguyên tắc

- Đưa class gate ratio từ worktree `wt_gdv2` vào `module`, **KHÔNG merge nhánh gd92-recheck nguyên khối**
  (tức **KHÔNG** đưa `GateRollingThreshold` = GD92; chỉ đưa `GateRollingRatio` = GDV2).
- Sim giữ nguyên key `SIM_GATE_ROLLING_*` (GDV2). Live thêm key MỚI `LIVE_GATE_ROLLING_*`.
- **Key vắng ⇒ live byte-identical HEAD** (`3305f43`, live src không đổi đến `cca1e7ed`): mọi nối sống
  phải nằm sau `LIVE_GATE_ROLLING_MODE=ratio` không khai báo ⇒ không đổi 1 bit quyết định.
- SLF4J duy nhất, cấm `System.out`/`printStackTrace` trong code MỚI. `mvn test` 0 fail.
- DEV ≤ 2025-12-31; 2026 = HOLDOUT (chỉ dùng cho replay test, KHÔNG dùng để chọn/tune).

## 2. Key cấu hình (mới, LIVE)

| key | ý nghĩa | default |
|---|---|---|
| `LIVE_GATE_ROLLING_MODE` | `ratio` = bật; vắng/khác = TẮT | TẮT |
| `LIVE_GATE_ROLLING_PCT` | phân vị (0..1); thiếu/ngoài (0,1) = TẮT | — |
| `LIVE_GATE_ROLLING_DAYS` | W ngày cửa sổ cuộn | 90 |
| `LIVE_GATE_ROLLING_FILE` | file persist (append-only) | `run/gate_ratio_live.bin` |

Đọc qua `Cfg.get` (prefix `LIVE_` đã nằm trong `TRADING_PREFIXES` ⇒ được profile kiểm soát, `auditProfile`
bắt key sai tên). Sim key `SIM_GATE_ROLLING_MODE/PCT/DAYS` giữ nguyên, không đổi.

## 3. Kiến trúc class (chia lõi chung để parity bit-identical)

1. **`GateRatioBuffer`** (package-private, mới): lõi THUẦN quantile-cuộn-trên-r, instance-based, không config,
   không log. Chứa buffer `(ts,r)` + `computeQ`/`kthSmallest` (quickselect median-of-3, fallback sort) +
   warm-up 7 ngày + `addAndQuery`. **Trích NGUYÊN VĂN** thuật toán từ `GateRollingRatio` của worktree.
   → đảm bảo q_t và quyết định **bit-identical** giữa sim và live (một nguồn sự thật).
2. **`GateRollingRatio`** (SIM, `SIM_*` key): đưa từ worktree, refactor để dùng `GateRatioBuffer`; giữ nguyên
   public API (`init/isOn/threshold/noteCandidate/notePass/stats/quarterOf`) + bộ đếm ρ per-quarter.
3. **`LiveGateRollingRatio`** (LIVE, `LIVE_*` key): cùng `GateRatioBuffer`; thêm persist + warm-up seed +
   log `[GATE-RATIO]` mỗi giờ.
4. **`GateRatioPersist`** (package-private): file append-only, nén Snappy, có CRC32.

### 3.1 Công thức r (giữ NGUYÊN phép nhân float, đúng L7)

```
factor = max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT)
gs     = GATE_REGIME_ADAPTIVE ? CURRENT_REGIME_SCALE : GATE_DYN_SCALE
r      = p15 / (factor * gs)
thrBase = q_t (hoặc MIN_MOMENTUM_15M khi warm-up)
PASS   ⇔ p15 >= thrBase * factor * gs   (tức r >= q_t)
```

Cả sim và live đều gọi `EntryGate.threshold(thrBase, sp)` sau khi có `thrBase` — cùng biểu thức gate như HEAD.

### 3.2 Điểm nối (1 chỗ, đúng triết lý L7 "một gate")

`AIRejectFilter.entryGate` (dùng chung sim + live) thêm hai nhánh:
```
if (LiveGateRollingRatio.isOn() && sp != null)      thrBase = LiveGateRollingRatio.threshold(...)
else if (GateRollingRatio.isOn() && sp != null)      thrBase = GateRollingRatio.threshold(...)
else                                                 thrBase = Configs.MIN_MOMENTUM_15M
```
`noteCandidate/notePass` của live là no-op khi TẮT ⇒ sim (Kaggle, không có `LIVE_*`) không đổi hành vi;
live (không có `LIVE_*`) byte-identical HEAD.

## 4. Live: buffer + q_t + persist + warm-up

### 4.1 Buffer & q_t (causal)
- Buffer `r` cho từng ứng viên PREDICT ở block SELECTOR (gọi `entryGate`). Nhịp theo `LIVE_ENTRY_GRID_MIN`
  (mặc định 15'; khi owner chốt 1' thì key đó đổi, không cần sửa class này).
- q_t tính **lười** theo giờ (giống sim): lần đánh giá đầu tiên của giờ H ⇒ `computeQ(H)` chỉ dùng `r` có
  `ts < H` (CAUSAL, không dùng chính ứng viên giờ H). Warm-up < 7 ngày ⇒ fallback `MIN_MOMENTUM_15M`.

### 4.2 Persist (sống qua restart `ThreadAutoRestartProgram`, JVM restart 4h/lần)
- File `run/gate_ratio_live.bin`, **append-only**, chia chunk: `MAGIC(4B) | LEN(4B) | CRC32(4B) | Snappy(RAW)`.
  RAW = chuỗi record `TS(8B BE) | R(4B float-bits BE)` (12B/record).
- Append buffer trong RAM, flush chunk khi đủ `FLUSH_BATCH` (4096 record) hoặc khi đổi giờ hoặc khi shutdown
  (shutdown hook). CRC32 trên bytes nén ⇒ phát hiện hỏng.
- **Load** (restart): đọc tuần tự, verify CRC32, giải nén, nạp (ts,r); giữ lại ≤ `days` ngày gần nhất
  (compact: ghi lại file mới nếu có dữ liệu già quá cửa sổ). ⇒ **restart không mất 90 ngày**.

### 4.3 Warm-up seed (nguồn + sai khác khai rõ)
- **p15**: CHÍNH XÁC, đọc theo phút từ Aerospike set `ai_pred_1m` (do `saveAiPrediction1M` ghi, qua
  `DataManagerAerospikeFloatSim.getAiPredictionAtTime`).
- **sp (symbolPred)**: tái tạo từ `storage/data/predictionSymbol/yyyyMMdd/<ts>` (bản đồ per-coin `preds[0]` =
  P(no-pump) do `predictAllCandidates` ghi mỗi tick selector). Sắp theo `preds[0]` tăng, lấy top-K
  (`SELECTOR_RANK_TOPK`, mặc định 16), tính `r` cho từng coin.
- **Sai khác vs sim (khai rõ):**
  1. **Không tái tạo loại coin đang giữ** (held-symbol bị skip ở live; vị thế lịch sử không lưu lại được đầy đủ)
     ⇒ seed có thể gồm/thiếu vài coin so với tập ứng viên thật. Ảnh hưởng nhỏ (ít coin giữ đồng thời).
  2. **Tick thiếu** (predictionSymbol/p15 rỗng) ⇒ bỏ qua tick đó.
  3. `preds[0]` = P(no-pump) Funding; đúng là `symbolPred` của đường R4 (không C3). Nếu sau này bật C3/net015
     thì `symbolPred` khác ⇒ seed này không đúng cho C3 (không phải phạm vi task).
- **Chưa đủ 7 ngày dữ liệu** (thiếu Aerospike/file) ⇒ fallback base `MIN_MOMENTUM_15M` (= 0,008 trong R4/G2)
  đúng như sim. Seed chạy **best-effort**, lỗi ⇒ bỏ tick, không fail-fast.

## 5. Parity sim ↔ live

- Cùng chuỗi `(ts, r)` đầu vào ⇒ `q_t` và quyết định pass **bit-identical** (dùng chung `GateRatioBuffer`).
- Unit test: feed chuỗi giống nhau cho `GateRollingRatio` (sim) và `LiveGateRollingRatio` (live), assert
  `q_t` bằng đúng float và quyết định pass bằng nhau.
- Replay ≥1 tháng DEV: chạy `GateRatioBuffer` trên chuỗi `(ts, r)` tái lập từ 1 tháng DEV, đối chiếu q_t giữa
  hai class (đảm bảo không drift, kể cả warm-up → armed).
- LƯU Ý phạm vi: parity là **cấp class** (cùng input ⇒ cùng output), KHÔNG phải parity toàn pipeline sim↔live
  (đầu vào `r` của live sinh từ selector live, khác sim — đã khai ở §4.3).

## 6. Log `[GATE-RATIO]` mỗi giờ

Mỗi giờ (lần đánh giá đầu tiên của giờ mới): `[GATE-RATIO] q_t=<float> size=<n buffer> eval=<n> pass=<n>`
(eval/pass = số đánh giá/pass PREDICT trong giờ vừa rồi). Chỉ chạy khi ON. Dùng theo dõi độ đều trên shadow sau.

## 7. Kiểm hợp lệ (cổng DỪNG)

1. `mvn test` 0 fail (thêm `GateRollingRatioTest` từ worktree + `LiveGateRollingRatioTest` + `GateRatioPersistTest`).
2. **Byte-identical HEAD**: unit test chứng minh `LiveGateRollingRatio.isOn()==false` khi key vắng ⇒ nhánh
   `entryGate` trả `Configs.MIN_MOMENTUM_15M` y hệt (parity cấp quyết định).
3. Không chạy sim Java trên Oracle (chỉ unit test). Không build lại jar sim. Không deploy.

## 8. Rủi ro (khai trước)

1. **Seed không byte-exact vs sim** (§4.3): là khác biệt THỪA NHẬN, chỉ ảnh hưởng q_t khởi đầu; live sẽ tự
   hiệu chỉnh khi tích lũy `r` thật. q_t khởi đầu của seed là [SUY LUẬN] chất lượng, không phải [ĐO].
2. **Nhịp 15' vs 1'**: seed & buffer theo `LIVE_ENTRY_GRID_MIN` (mặc định 15'), trong khi sim G2 chạy 1' ⇒
   mật độ mẫu khác, q_t có thể lệch nhẹ so sim. Đây là câu treo owner (RULERS §13.4), KHÔNG giải quyết ở task này.
3. Đọc Aerospike/file khi seed là IO nặng (1 lần khởi động), có thể chậm; best-effort, không chặn khởi động.
4. E2 (CRASH_PENALTY) chạy song song, chạm Simulator ở worktree riêng — mình chỉ `git add` đúng file của mình,
   đẩy conflict nếu có.

## 9. File sẽ tạo/sửa

- Tạo: `ai_ml/onnx/entry/{GateRatioBuffer,GateRollingRatio,LiveGateRollingRatio,GateRatioPersist}.java`
- Sửa: `AIRejectFilter.java` (nối gate), `DetectEntrySignal2TradeNormal.java` (init live),
  `SimulatorMarketLevelTicker1MStopLoss.java` (init + log sim, tối thiểu như worktree).
- Test: `GateRollingRatioTest.java` (đưa từ worktree), `LiveGateRollingRatioTest.java`, `GateRatioPersistTest.java`.
- Doc: file này.
- Commit + push (owner cho phép từ 28/09). KHÔNG push file dữ liệu.
