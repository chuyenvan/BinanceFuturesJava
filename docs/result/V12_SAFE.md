# V12_SAFE — v1.2/safe: C10 fail-closed · C8 kill-switch ACT + C2 có dấu · C11 race seed

Branch `v1.2/safe` (worktree `~/claude_master/v12/safe`) từ `16de49a6` (v1.1/exec-probe). Không push, không merge, không deploy.
Agent v12safe, 2026-10-25. Không tạo file trong `c3live.*` (thuộc v12lib).

| Commit | Nội dung |
|---|---|
| `3ecbf625` | C10: áp nguyên văn `audit_oc1023/audD/failclosed.patch` |
| `65b556e3` | C11: cờ `LIVE_SEED_EXCLUDE_DECISION_MIN` + test |
| `ab191197` | C8 + C2 có dấu: kill-switch ACT, latch persist, reset owner, `EquitySource`, script `ops/killsw_reset.sh` + test |
| (commit doc này) | `OpsHooks.onBook(...)` (hook sổ lệnh thật cho vòng 2, chưa có call site) + tài liệu |

## 1. Risk-first

1. **Toàn bộ API mới CHƯA có call site.** Kill-switch ACT chỉ chặn được lệnh khi vòng 2 gọi `allowNewEntry` ở `createOrderBuyRequest`
   (trước push) VÀ ở cửa gửi lệnh, và thực thi `requiredAction()==FLATTEN` (đóng reduce-only chia lô). Trước khi nối: FLATTEN chỉ là cờ.
2. **C1–C5 latch VĨNH VIỄN tới khi owner chạy script** (đúng spec GOLIVE C8). Một nhịp mất dữ liệu > 3′ hoặc không tick > 5′ ⇒
   dừng mở mới tới khi owner reset. Dữ liệu shadow 242 (log-only từ 10-23 09:37:42 tới 10-25 08:00, ~46 h): **0** sự kiện
   `WOULD_TRIGGER` (mọi mã) ⇒ tần suất thấp nhưng cửa sổ ngắn — MASTER cân nhắc cho C1/C5 tự xoá sau N phút sạch (chưa làm).
3. **A40 phụ thuộc `EquitySource`** (vòng 2). Không gắn ⇒ không có A40. Equity `null`/lỗi ⇒ giữ trạng thái cũ + WARN, KHÔNG latch;
   lỗi REST phải báo qua `OpsHooks.onApiResult` để C3 bắt. Đỉnh equity A40 lưu trong file latch; sau FLATTEN do A40, reset thường
   sẽ latch lại ngay (DD vẫn ≤ −40 %) — owner phải `RESET_PEAK=1` có chủ đích.
4. **C6 dùng `onPaper`/`onBook`** (đỉnh sàn = PAPER_EQUITY). Nếu c3_live vẫn đưa sổ GIẤY vào `onPaperTick`, DD giấy −40 % sẽ
   FLATTEN tài khoản thật. Vòng 2: chỉ một nguồn sổ (sổ thật qua `onBook`).
5. **Xoá tay file latch khi JVM tắt ⇒ mất latch** (không chặn được ở mức file). Khi JVM chạy: xoá file ⇒ engine ghi lại + WARN.
   File latch hỏng ⇒ FAIL-CLOSED `NO_NEW_ENTRY code=STATE` (sao lưu `.corrupt_<ms>`).
6. **C10 đổi hành vi c3_shadow khi có NaN** (ngoại lệ có khai, ADDENDUM d): replay buffer 242 = **0 record không hữu hạn**
   (tới 10-25 07:07 +07) — cửa sổ chạy tới 11-18 ⇒ phải replay lại cuối cửa sổ. Dòng log `[GATE] n_pass` đổi (=0) ở phút
   `predictData==null` — script đọc log nào dùng n_pass cần biết.
7. Cờ mới đều **mặc định 0**; c3_live phải đặt trong env (mục 5). Khi `LIVE_PROFILE=c3_live` mà kill-switch không ở `act` hoặc
   `LIVE_SEED_EXCLUDE_DECISION_MIN=0` ⇒ chỉ WARN lúc khởi động (không chặn khởi động) — vòng 2 nên từ chối push khi `killSwitchArmed()=false`.

## 2. Theo mã việc

### C10 — fail-closed NaN/Inf (patch audD, nguyên văn)
- `AIRejectFilter.evaluate`: khi `LiveGateRollingRatio.isOn()` và p15 NaN/±Inf hoặc thr NaN/−Inf ⇒ REJECT `FAIL-CLOSED`
  (+ đếm `nonFiniteRejectCount`). Sim/backtest không có key LIVE ⇒ nhánh không chạy ⇒ không đổi.
- `LiveGateRollingRatio.threshold`: r không hữu hạn ⇒ trả NaN, KHÔNG nạp buffer, KHÔNG append persist; q không hữu hạn ⇒ NaN (REJECT).
- `DetectEntrySignal2TradeNormal`: `predictData==null` ⇒ WARN `[FAIL-CLOSED] tick ... KHONG co prediction`, dòng `[GATE]` in
  `n_rej=n_cand` ⇒ **`n_pass=0`** (trước: in n_pass=n_cand); WARN `[FAIL-CLOSED] [GATE] k ung vien REJECT vi p15/thr ...`.
- Test `FailClosedGateTest` (6): NaN/+Inf/−Inf p15 ⇒ REJECT, buffer 0, pending persist 0; sp NaN ⇒ REJECT; `threshold` không hữu hạn
  ⇒ NaN không nạp, hữu hạn ⇒ nạp như cũ; thr NaN/−Inf ⇒ REJECT; **key LIVE tắt ⇒ hành vi cũ (NaN ⇒ PASS), bộ đếm không tăng**.
  `GateLineNoPredTest` (1): `gateLine(nCand=24, nRej=24)` ⇒ `n_pass=0`.
- **Replay buffer (ADDENDUM d)**: `~/claude_master/pull242/{10-21,10-22,10-23,10-24}/run/gate_ratio_live.bin.gz`, đọc bằng CHÍNH
  reader production `GateRatioPersist.load` và độc lập bằng `grr_lib.load` (python):

| bản kéo | n record | NaN | +Inf | −Inf | chunk hỏng | ts max |
|---|---|---|---|---|---|---|
| 10-21 / 10-22 / 10-23 (cùng 1 file kéo 10-24 08:25) | 769 232 | 0 | 0 | 0 | 0 | 1792804920000 (10-24 08:22 +07) |
| 10-24 (kéo 10-25 08:23) | 802 000 | 0 | 0 | 0 | 0 | 1792886820000 (10-25 07:07 +07) |

  ⇒ **0 record không hữu hạn** (Java = python). r ∈ [6,11e-4; 0,01175].

### C8 + C2 có dấu — `ops/KillSwitchEngine`
- `ACT_IMPLEMENTED = true`; `resolve("act","c3_live") ⇒ ACT`; mọi profile khác (c3_shadow) act vẫn **bị từ chối ⇒ log** (không đổi).
- ACT: C1–C5 đạt ⇒ latch `NO_NEW_ENTRY`; C6 hoặc A40 đạt ⇒ latch `FLATTEN` (bao hàm chặn mở mới). Chỉ nâng mức, không hạ.
  Latch đánh giá MỖI lần mã đạt (không chỉ cạnh lên) ⇒ sau reset mà điều kiện còn đạt ⇒ latch lại ngay.
- Persist `run/killsw_latch.json` (JSON, ghi atomic tmp+move, engine là người ghi DUY NHẤT): latch, codes, since, detail,
  mốc sự kiện C2 trong cửa sổ, đỉnh equity A40, last_reset. Nạp lúc khởi động (latch sống qua restart, kể cả restart 12h).
- Reset: `ops/killsw_reset.sh` ghi `run/killsw_reset.req` → thread periodic (15 s) áp dụng ĐẦU lượt (rồi đánh giá lại) → đổi tên
  `.done_<ms>`. JVM tắt ⇒ áp dụng lúc khởi động. File yêu cầu hỏng ⇒ bỏ qua (`.bad_<ms>`), latch giữ.
- C2: cờ `LIVE_KILLSW_C2_SIGNED` (mặc định 0 ⇒ công thức v1.1 `|fill/ref−1| > 2,5 %` NGUYÊN TRẠNG). =1: trượt bất lợi
  (mua `fill/ref−1`, bán `1−fill/ref`) `> 1,7 %` ⇒ WARN `[KILLSW] C2_WARN` (+ alert); `> 2,5 %` lần thứ 3 trong 24h ⇒ C2 đạt.
  Ngưỡng config (mục 5). Có lợi (âm) không tính.
- A40: `attachEquitySource(EquitySource)` ⇒ periodic poll `totalMarginBalance()`; đỉnh = max(đỉnh lưu, equity thấy);
  `eq/đỉnh − 1 ≤ −40 %` ⇒ FLATTEN. Không gắn ⇒ không có cột A40 (dòng HOURLY y v1.1).
- Mode LOG (c3_shadow): không đọc/ghi file latch/reset, `allowNewEntry` = true, `requiredAction` = NONE, chữ log `WOULD_TRIGGER`
  giữ nguyên (ACT in `TRIGGER`).
- Script `ops/killsw_reset.sh` (bash thuần — 242 không có python): `DRY=1` mặc định chỉ in trạng thái; `DRY=0` phải gõ `YES`
  (khác ⇒ thoát 3, không ghi); ghi log `run/killsw_reset.log`; `RESET_PEAK=1` tuỳ chọn; KHÔNG restart, KHÔNG gọi sàn; chờ ≤30 s xem bot áp dụng.
- Test `KillSwitchActTest` (21): mỗi C1, C2(có dấu, 3 lần/24h, cửa sổ hết hạn, có lợi bỏ qua, cờ 0 = công thức cũ), C3, C4, C5,
  C6, A40 (kể cả equity null) một kịch bản ⇒ đúng hành động; leo thang NO_NEW_ENTRY→FLATTEN không hạ; **c3_shadow: cả 7 mã đạt ⇒
  0 hành động, 0 file latch, chỉ WOULD_TRIGGER**; latch/C2/đỉnh A40 sống qua restart; reset không restart + relatch khi còn đạt;
  reset_peak; reset lúc khởi động; file latch hỏng ⇒ fail-closed; file reset hỏng bị bỏ qua; alert lỗi không làm hỏng engine;
  HOURLY mode log không đổi. `KillSwitchResetScriptTest` (1, chạy script thật): DRY không ghi; `yes` ⇒ thoát 3; `YES` ⇒ ghi req
  + log; engine đang chạy áp dụng ⇒ NONE. `KillSwitchEngineTest` (21, sửa 1 test v11d: act ở c3_live nay = ACT).

### C11 — race seed/tick đầu sau restart
- Cờ `LIVE_SEED_EXCLUDE_DECISION_MIN` (mặc định 0 = hành vi cũ, đường code cũ không đổi). =1: `seed()` GIỮ LẠI phút hợp lệ cuối
  của map seed; tick đầu: phút giữ lại < phút quyết định ⇒ nuôi (y hệt cũ), ≥ ⇒ bỏ (phút quyết định tính từ snapshot cửa sổ như
  mọi tick). Không phụ thuộc đồng hồ ⇒ tái lập offline.
- Gốc lỗi thật: 10-21 07:54:10 init xong SAU mốc phút ⇒ seed tới 07:53 = phút quyết định đầu ⇒ `[FEAT-PIPE] ... (clock lui?)`
  ⇒ mất tick. Restart 10-23 09:37:31 thật KHÔNG dính race (init xong 09:37:41, seed tới 09:36) ⇒ harness mô phỏng ca xấu bằng
  bản COPY harness (`HARNESS_SEED_INCL_FIRST=1` ⇒ seed gồm cả phút rFloor = phút quyết định đầu 09:37).
- Test `LiveFeaturePipelineSeedExclTest` (5 mock): race cờ 0 mất tick/cờ 1 có; không race cờ 1 = cờ 0 từng bước; tick đầu trễ;
  cửa sổ trễ hơn seed; mặc định tắt.
- **Harness NEW2 OFFLINE** (seg 3 của segs 10-23: restart 1792723051000 = 10-23 09:37:31 +07, first 09:37, last 10-24 07:00
  +07; dữ liệu Vision; strace 0 kết nối AF_INET ra ngoài, 0 tới 242):

| biến thể | jar | seed gồm phút quyết định đầu | cờ | số phút có feature | phút đầu | out md5 |
|---|---|---|---|---|---|---|
| b_std | dcae2e2b | không (= harness chính thức) | – | 1283 | 09:37 | 58ce0eca… |
| b_race | dcae2e2b | CÓ | – | **1282** (mất 09:37, WARN clock lui) | 09:38 | 50e2883c… |
| s_std0 | v1.2/safe | không | 0 | 1283 | 09:37 | 58ce0eca… (= b_std) |
| s_race0 | v1.2/safe | CÓ | 0 | 1282 | 09:38 | 50e2883c… (= b_race) |
| s_race1 | v1.2/safe | CÓ | **1** | **1283** | **09:37** | 58ce0eca… (= b_std) |
| s_std1 | v1.2/safe | không | 1 | 1283 | 09:37 | 58ce0eca… (= b_std) |

  ⇒ cờ 0 byte-identical bản cũ (cả out gate lẫn fund, cả 2 kịch bản); cờ 1 + race: tick đầu CÓ feature; các tick sau trùng bản
  cũ **1282/1282** dòng gate, **44 110/44 110** dòng fund (100 %); toàn bộ file = kịch bản không race.

## 3. Validation

- `mvn -o package -DskipTests=false`: BUILD SUCCESS, **445 test, 0 fail, 0 error, 1 skip** (skip có sẵn:
  `SymbolMapperSnapshotRepairTest`). Test mới/sửa: KillSwitchActTest 21, KillSwitchResetScriptTest 1, KillSwitchEngineTest 21
  (1 sửa), FailClosedGateTest 6, GateLineNoPredTest 1, LiveFeaturePipelineSeedExclTest 5.
- **Parity offline 2026-10-22** (driver riêng `~/claude_master/v12/safe_parity/drv.py`: gọi `day_harness.main` chính thức, chỉ
  thay classpath jar + thư mục ghi; harness/segs/Vision/univ chỉ đọc; ra `~/claude_master/v12/safe_parity/d22_{base,safe}`):
  CTL gate **1440/1440 phút bit** cả jar `dcae2e2b` lẫn v1.2/safe (`ab191197`, md5 jar 3193d5ff…); 4 file kết quả
  (`out_BT`, `out_NEW2`, `fund_BT`, `fund_NEW2`, giải nén) **md5 trùng 100 %** safe = dcae2e2b = lượt chính thức (eea5adec).
  CTL fund 0,9443 (79 phút, cột f3) là sẵn có, giống hệt ở jar gốc. strace: 0 kết nối ra ngoài.
- **Bytecode diff** jar dcae2e2b ↔ `ab191197`: chỉ class của 6 file nguồn đã sửa (`AIRejectFilter`, `LiveGateRollingRatio`,
  `DetectEntrySignal2TradeNormal`, `LiveFeaturePipeline`, `ops/KillSwitchEngine|OpsConfig|OpsHooks` (+ inner)) + 3 class mới
  (`EquitySource`, `KillSwitchEngine$Action`, `$Params`). Commit cuối chỉ thêm `OpsHooks.onBook` (không call site).
- Tiêu chí GOLIVE_SCENARIO: C10 — `git apply --check` + build ✓, unit test NaN/±Inf ✓, sim byte-identical (key LIVE tắt: test +
  parity) ✓, replay buffer 0 không hữu hạn ✓ (tới 10-25 07:07), `n_pass=0` ✓. C8 — mỗi C1–C6 + A40 mock ✓, c3_shadow 0 hành động ✓,
  latch persist + chỉ script owner xoá ✓; **chặn ở createOrderBuyRequest/cửa gửi lệnh + đóng reduce-only + Telegram: CHƯA (vòng 2)**.
  C11 — cờ, harness giờ restart thật, tick đầu có feature, tick sau trùng 100 % ✓.

## 4. API công khai cho vòng 2

```java
// com.binance.chuyennd.ops.EquitySource
@FunctionalInterface public interface EquitySource { Double totalMarginBalance(); }   // null = khong co so

// com.binance.chuyennd.ops.KillSwitchEngine
public enum Action { NONE, NO_NEW_ENTRY, FLATTEN }
public synchronized boolean allowNewEntry(String symbol);          // ACT: false khi latch; mode khac: true
public synchronized Action requiredAction();                       // mode khac ACT: NONE
public synchronized java.util.Set<String> latchCodes();
public synchronized void attachEquitySource(EquitySource src);     // A40 (poll trong periodic 15 s)
public synchronized void onAccountEquity(long nowMs, Double equity);   // day equity thay vi poll
public synchronized void onFill(long nowMs, String symbol, boolean isBuy, Double fillPx, Double refPx);  // C2; ref = close nen 1m quyet dinh
public synchronized void setAlert(java.util.function.Consumer<String> alert);   // Telegram
public KillSwitchEngine(Mode, String, Sink, File peakFile, DoubleSupplier paperEquity, Supplier<Float> uMax, long nowMs, Params prm);

// com.binance.chuyennd.ops.OpsHooks (static, khong bao gio nem; KS tat => no-op / true / NONE)
public static boolean killSwitchArmed();                 // true iff mode ACT (c3_live) — tu choi push khi false
public static boolean allowNewEntry(String symbol);      // loi noi bo o ACT => false (fail-closed)
public static KillSwitchEngine.Action requiredAction();  // loi noi bo o ACT => NO_NEW_ENTRY
public static void onFill(String symbol, boolean isBuy, Double fillPx, Double refPx);
public static void attachEquitySource(EquitySource src);
public static void setAlert(java.util.function.Consumer<String> alert);
public static void onBook(int openPos, float margin, float equity);   // so lenh THAT: C4/C6
public static void onApiResult(String api, boolean ok);               // (co san) moi REST tai khoan con: C3

// com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline
public synchronized void setSeedExcludeDecisionMin(boolean on);       // forProd() da doc co tu config
```
Điểm nối vòng 2: `allowNewEntry` ở `createOrderBuyRequest` TRƯỚC push và ở adapter gửi lệnh (entry + DCA); vòng quản lý vị thế
đọc `requiredAction()` mỗi nhịp, FLATTEN ⇒ đóng hết reduce-only chia lô (idempotent, C3) + dừng; `attachEquitySource` =
totalMarginBalance tài khoản con (Q1b); `setAlert` = Telegram; `onApiResult` cho mọi call REST signed; `onFill` cho mọi fill thật.

## 5. Cấu hình mới (đọc qua `Cfg`, mặc định = hành vi cũ)

| key | mặc định | c3_live |
|---|---|---|
| `LIVE_KILLSW_MODE` (có sẵn) | off | `act` (cần `LIVE_PROFILE=c3_live`) |
| `LIVE_KILLSW_C2_SIGNED` | 0 | 1 |
| `LIVE_KILLSW_C2_WARN` / `_SLIP` / `_COUNT` / `_WINDOW_H` | 0.017 / 0.025 / 3 / 24 | giữ (chốt lại sau exec-probe ~100 leg) |
| `LIVE_KILLSW_LATCH_FILE` / `LIVE_KILLSW_RESET_FILE` | `run/killsw_latch.json` / `run/killsw_reset.req` | giữ (script dùng cùng env) |
| `LIVE_SEED_EXCLUDE_DECISION_MIN` | 0 | 1 |

Giá trị sai ⇒ mặc định + WARN. Không có key nào chạm logic quyết định của c3_shadow/sim khi để mặc định.

## 6. CHƯA LÀM / CHƯA XÁC MINH

- Call site vòng 2 (chặn trước push, cửa gửi lệnh, FLATTEN reduce-only chia lô, Telegram, EquitySource thật, onFill/onApiResult thật).
- Đối chiếu equity hằng giờ > 1 % ⇒ chặn mở mới (Q1b, thuộc C9) — không nằm trong latch này.
- Replay buffer NaN cho phần cửa sổ sau 10-25 07:07 (tới 11-18) — chạy lại `V12BufCheck` trên bản kéo mới.
- Script reset chỉ test local (Oracle, JUnit + bash); chưa chạy trên 242 (đúng phạm vi).
- C1/C5 tự xoá sau thời gian sạch: không làm (spec yêu cầu latch); đề xuất MASTER cân nhắc.

## 7. File đổi

`src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/{AIRejectFilter,LiveGateRollingRatio}.java`,
`.../trading/DetectEntrySignal2TradeNormal.java` (C10, patch nguyên văn) ·
`.../ai_ml/features/export/entry/LiveFeaturePipeline.java` (C11) ·
`.../ops/{KillSwitchEngine,OpsConfig,OpsHooks}.java`, `.../ops/EquitySource.java` (mới), `ops/killsw_reset.sh` (mới) (C8) ·
test: `ops/{KillSwitchActTest,KillSwitchResetScriptTest}.java` (mới), `ops/KillSwitchEngineTest.java` (1 test),
`ai_ml/onnx/entry/FailClosedGateTest.java`, `tradecore/selector/GateLineNoPredTest.java`,
`ai_ml/features/export/entry/LiveFeaturePipelineSeedExclTest.java` (mới) · `docs/result/V12_SAFE.md`.

Artefact kiểm (Oracle, ngoài repo): `~/claude_master/v12/safe_parity/{d22_compare.json, c11/c11_result.json, drv.py, c11drv.py,
tools/…/V12BufCheck.java}`.
