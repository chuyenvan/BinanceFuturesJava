# TASK-113: Fitness V4 → V4.1 — đo đủ metrics mọi nhánh + min-trade theo window thật + aggregate đếm tường minh

- **status:** todo
- **depends_on:** TASK-112 (⚠️ cùng sửa `StrategyWfoTask.java` và cùng cần GATE trên jobstore `strategy_window` Oracle — chạy TUẦN TỰ SAU 112, không song song cùng working-tree)
- **Milestone:** [docs/insights/WFO_ROADMAP.md](../docs/insights/WFO_ROADMAP.md) — chất lượng đo lường WFO
- **require_review:** true (đổi semantics fitness → mọi số HPO/WFO sau này; Uni đã duyệt thiết kế 2026-07-02)
- **touches_live_process:** không (fitness chỉ dùng backtest/HPO/WFO)

## ⛔ RÀNG BUỘC MÔI TRƯỜNG

1. Trên Oracle có thể đang có run WFO (kiểm `pgrep -f "[W]foWorker"` — chú ý bracket-trick, pattern trần sẽ tự match). CẤM reset jobstore `strategy_window` / kill java / đè jar đang chạy khi run chưa xong (`WfoCoordinator status strategy_window` DONE=17 + pgrep rỗng).
2. Code local Windows branch `module`; build `JAVA_HOME=/c/Users/pc/.jdks/corretto-17.0.9 /c/Users/pc/bin/mvn -q -DskipTests package`; deploy Oracle bằng jar tên riêng `binance-futures-task113.jar`, md5 verify. KHÔNG `git add .`.

## Mục tiêu (1 câu)

Fitness V4 hiện **che mất PnL/metrics thật của các nhánh bị loại sớm** và **min-trade tính theo span lệnh (ngược đời: càng dồn cục càng dễ qua)** — sửa thành V4.1: tính đủ metrics mọi nhánh, min-trade theo độ dài window thật, aggregate đếm %OOS-dương **tường minh theo note** (kết quả đếm GIỮ NGUYÊN semantics hiện tại), rồi pre-register lại.

## Bằng chứng (run leak-free v2, 2026-07-02 — `docs/reports/wfo_leakfree_funding_v2_report.md`)

- WIN 7 có **8 lệnh OOS** nhưng report ghi `OOS_pnl=0, WFE=0` — PnL thật của 8 lệnh bị `TOO_FEW_TRADES` return-sớm nuốt (V4 dòng 73-75 return TRƯỚC khối thống kê dòng 77+). WIN 14 (4 lệnh) tương tự. → mất thông tin chẩn đoán + WFE median méo.
- min-trade: `windowDays` suy từ `lastKey−firstKey` của lệnh done (V4 dòng 67-71) → genome dồn 10 lệnh trong 3 ngày của window 90 ngày: span=3 → minTrades=5 → **PASS**; genome rải 8 lệnh/80 ngày → FAIL. Ngược mục đích "đủ mật độ để metric đáng tin" → lỗ **selection** trong IS.
- %OOS-dương hiện đếm `oosPnl>0` — đúng KẾT QUẢ hiện tại chỉ vì pnl sentinel-window bị che thành 0. Sau khi pnl hiện số thật, nếu không đổi cách đếm thì "8 lệnh may mắn dương" thành cửa-sổ-thành-công → nới verdict ngầm.

## Thiết kế chốt (Uni duyệt 2026-07-02)

### 1. `HPOFitnessCalculatorV4.evaluateDetailed` — signature + reorder
- Signature mới: `evaluateDetailed(TreeMap<Long,OrderTargetInfoTest> allOrderDone, int windowDaysActual)`; bỏ hoàn toàn suy-windowDays-từ-span. `minTrades = max(5, windowDaysActual*0.33)`.
- **Reorder:** tính ĐỦ khối thống kê (totalProfit, pctHeldOver7d, ddPct/maxDrawdown từ BudgetManager, posYearRatio, calmar, sortino) TRƯỚC chuỗi constraint. Chuỗi constraint giữ NGUYÊN thứ tự + CÔNG THỨC fitness: ZERO_TRADES(=REJECT_BASE) → TOO_FEW_TRADES(=REJECT_BASE+tradeCount) → BURN_ACCOUNT(=REJECT_BASE+totalProfit) → OVER_MAXDD(=REJECT_BASE−ddPct·100) → TOO_MUCH_CAPITAL_LOCK(=REJECT_BASE−pctHeld·100) → UNSTABLE_ACROSS_YEARS (span điều kiện giờ dùng `windowDaysActual/365.0`) → SUCCESS(=calmar).
- Bất biến GATE-unit: **với cùng input + cùng windowDays, `finalFitness` V4.1 ≡ V4** (chỉ FitnessReport có thêm số thật ở nhánh sentinel). Khác biệt duy nhất được phép: các case min-trade mà windowDaysActual ≠ span-lệnh (đó chính là fix #2, chứng minh bằng unit case C).
- Cập nhật **6 caller V4** (đã grep 2026-07-02): `WFORunner:215`, `StrategyWfoTask:228`, `AblationClusterTool:138`, `FitnessBaselineTool:127`, `MetricDistributionTool:134`, `SensitivityTool:187` — mỗi chỗ truyền `windowDays = max(1,(end−start)/Utils.TIME_DAY)` từ range backtest THẬT của chính nó. KHÔNG đụng V3/HPOFitnessCalculator cũ (BackTestEngineMaster, BenchmarkSpeedTest... dùng V3 — ngoài scope).

### 2. `StrategyWfoTask`
- `runJob`: result JSON thêm `"oosNote": rep.note` (và `"isNote"` nếu tiện). oosPnl/oosDdPct/oosMaxDD/oosCalmar tự nhiên có số thật sau reorder.
- `aggregate`: `posCount` đếm khi `"SUCCESS".equals(oosNote) && oosPnl > 0` (đọc `optString("oosNote","SUCCESS")` để tương thích result cũ). → **Kết quả đếm %dương GIỮ NGUYÊN semantics hiện tại** (window sentinel không bao giờ đếm dương — có chủ đích thay vì do số bị che). WFE giữ công thức `oosPnl/bestIsPnl` — giờ trung thực vì oosPnl thật (LOW_TRADES pnl âm → WFE âm, đúng bản chất).
- Bảng report thêm cột `oosNote`.

### 3. Pre-register V4.1 (docs)
- Ghi vào `WFO_ROADMAP.md` §2 + `WFO_FRAMEWORK_DESIGN.md` §6: ngưỡng verdict GIỮ NGUYÊN (WFE_median≥0.5 · %dương≥70% đếm-SUCCESS-only · worst ddPct≤50%); thay đổi so V4: (i) WFE median trung thực (LOW_TRADES windows đóng góp WFE thật thay vì 0), (ii) %dương tường minh theo note (kết quả đếm không đổi), (iii) min-trade theo window thật (đổi selection — có chủ đích). Verdict V4 cũ (leak-free v2: FAIL, WFE 0.098, 76.5%, 30.7%) giữ làm mốc lịch sử, KHÔNG so trực tiếp số-với-số với V4.1.

## GATE (2 tầng — khớp-số kiểu TASK-112 KHÔNG khả thi ở đây vì #2 đổi selection có chủ đích)

1. **Unit determinism (local, bắt buộc):** viết tool `ml`-style `TestFitnessV41.java` (main, SLF4J) với order tổng hợp:
   - A: 60 lệnh rải 90 ngày, profit dương, DD nhỏ → SUCCESS, fitness = calmar (so tính tay ±1e-3).
   - B: 8 lệnh window 90d → TOO_FEW, fitness = −100000+8, **totalProfit = tổng thật ≠ 0** (điểm fix #1).
   - C: 10 lệnh dồn 3 ngày, windowDaysActual=90 → V4-cũ logic span sẽ PASS min-trade; V4.1 → TOO_FEW (chứng minh fix #2).
   - D: profit ≤ 0 → BURN với fitness = −100000+profit và ddPct vẫn được điền.
   - E: pctHeld>2% profit dương → CAPITAL_LOCK, totalProfit thật được điền.
2. **Function-test Oracle (sau khi run trên Oracle xong, jar task113):** chạy 4 window N=3 (reset `WFO_MAX_WINDOWS=4 WFO_N_SAMPLES=3`, env như TASK-112 mô tả sau refactor) → ghi 4 dòng [WIN] làm **BASELINE V4.1 MỚI** vào phần Kết quả (không so khớp V4). Sanity: report có cột oosNote, LOW_TRADES window (nếu có) hiện pnl thật.

## Scope
**Trong:** V4→V4.1 như trên; 6 caller; StrategyWfoTask runJob/aggregate/report; TestFitnessV41; docs pre-register. **Ngoài (KHÔNG động):** V3/HPOFitnessCalculator cũ; ngưỡng constraint (MAX_DD_PCT 0.65, CAP_LOCK 0.02 — việc chỉnh cap là task đo riêng); sim/PnL logic; deploy 242.

## Acceptance criteria
- [ ] Unit A-E pass (log số thật trong output).
- [ ] `grep -rn "evaluateDetailed(sim.allOrderDone)" src/` → 0 (mọi caller V4 đã truyền windowDays); V3 caller không đổi.
- [ ] Compile + shaded jar sạch; SLF4J; commit lẻ theo cụm (V4.1+unit → callers → StrategyWfoTask → docs).
- [ ] Function-test Oracle ghi baseline V4.1 + report có oosNote.
- [ ] Docs pre-register V4.1 cập nhật (2 file).

---
## (Code điền) Kết quả
<commit list, output unit A-E, 4 dòng [WIN] baseline V4.1>

## (Code điền) Phát hiện ngoài scope
<.>

## (Code điền) Quyết định phát sinh
<.>
