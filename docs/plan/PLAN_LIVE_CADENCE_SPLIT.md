# PLAN — TÁCH NHỊP QUÉT LIVE: SELECTOR 15' · BIG_DOWN/DCA 1'

Trạng thái: **CHUẨN BỊ (chưa deploy)** · ngày 2026-09-27 · branch `module` · KHÔNG push.
Mục tiêu: LIVE khớp thiết kế sim `sel15` — **SELECTOR 15'**, **BIG_DOWN/DCA 1'**.
Hiện LIVE chạy **cả hai ở 15'** (một cổng duy nhất ở đầu thread).

---

## 1. Sự thật code + RANH GIỚI TÁCH

`src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java`

| Vùng | Dòng (HEAD) | Dòng (sau patch) | Số dòng | Bản chất |
|---|---|---|---|---|
| Cổng nhịp | `:122-141` `startThreadDetectMarketLevel2Trader()` | `:126-151` | 20 | `while(true){ if (isTimeProcessData()) executor.execute(checkMarketLevelChange2Trade()); }` |
| Cổng 15' | `:991-1005` `isTimeProcessData()` + `:988 ENTRY_GRID_MIN=15` | `:1018-1032` | 15 | Chỉ TRUE tại mốc lưới 15' (`second 6..10 && curMin%15==0`) |
| **PREP dùng chung** | `:147-269` | `:157-279` | 123 | Đọc Aerospike, build `symbol2FinalTicker`, `rateDown/Up*`, `symbol2Max15m`; `levelChange = getMarketStatus1M(...)` (`:226`); funding history `:237-239`; **ONNX entry predict** `:241-266`; `sortedCandidates = predictAllCandidates(...)` `:268` |
| **MARKET-LEVEL** | `:270-330` | `:281-341` | 61 | **E1** `if(levelChange!=null)` + `symbol2BUY=getTopSymbol(...)` + mở leg theo `levelChange` (**BIG_DOWN**) `:270-295`; **E2** `DcaProcessor.getDCAProduction(levelChange,...)` `:296-311`; **E3** `isDcaAlt(...)` -> `getDCAProduction(null,...)` `:313-330` |
| **SELECTOR** | `:332-441` | `:344-463` | 110 | build pool S1/rank (`:341-384`), vòng entry `PREDICT_SYMBOL_TRADE` (`:390-413`), log `[GATE]` (`:419-427`), ghi `prediction` (`:439-440`) |

**Ranh giới tách đề xuất = ngay TRƯỚC dòng `List<String> predictRejects = new ArrayList<>();` (HEAD `:335`, sau patch `:357`).**
Mọi thứ TRÊN ranh giới (prep + levelChange + BIG_DOWN + DCA) là **MARKET-LEVEL → chạy ở cả 2 nhịp**;
mọi thứ DƯỚI ranh giới (xếp hạng + mở entry selector + ghi prediction) là **SELECTOR → chỉ 15'**.

Lưu ý phụ thuộc: MARKET-LEVEL **cần** `predictData` (ONNX entry, vì `createOrderBuyRequest` `:747-750` return nếu `prediction==null`) và `sortedCandidates` (E1 xếp hạng) → 2 thứ này **phải** chạy ở nhịp 1' (giống sim, sim tính lại candidate mỗi phút).

---

## 2. Patch dev-side (tối thiểu)

Key mới: **`MARKET_SCAN_MIN`** (int) — `Configs.java` (field `:417-426`, đọc trong `static{}` `:797-802`).
`0`/không khai/`<=0` → **giữ nguyên** (chỉ 15'). `>0` (dùng `1`) → MARKET-LEVEL quét mỗi phút.

- `Configs.java`: **+15 dòng** (biến + doc + loader).
- `DetectEntrySignal2TradeNormal.java`: **+50 / -4 dòng**
  - thread: thêm `selectorTick` (cũ) + `marketTick` (mới, chỉ khi key>0) + 1 dòng log xác minh nhịp;
  - `checkMarketLevelChange2Trade()` → `checkMarketLevelChange2Trade(boolean selectorLeg)`;
  - **early-return** `if (!selectorLeg) return;` ngay trước khối SELECTOR (`:350-353`);
  - tách 2 cổng thành **hàm thuần** `selectorGrid(...)` / `marketScanGrid(...)` (logic Y NGUYÊN).
- **KHÔNG chạm** ONNX / `NUM_FEATURES` / `extractFeatures45` / thuật toán entry-gate / tham số nào khác.

Diff nhỏ nhất: **+63 / -4 dòng** (2 file main) + test mới.

### Bằng chứng "không khai key ⇒ y nguyên"
1. **Logic**: key chưa khai → `Configs.MARKET_SCAN_MIN = 0` → `marketScanGrid(...,0) == false` với mọi giây/phút ⇒ `marketTick` luôn false ⇒ thread chỉ còn nhánh `selectorTick` (chính là `isTimeProcessData()` cũ) ⇒ `selectorLeg = true` ⇒ early-return không kích hoạt ⇒ thân hàm y hệt HEAD.
2. **Test**: `src/test/java/com/binance/chuyennd/trading/CadenceSplitTest.java` — 5/5 PASS:
   `keyKhongKhai_thiKhongBaoGioCoNhip1Phut` (quét 60×60 mốc), `congSelector_vanChiChayTaiMocLuoi15Phut`,
   `keyBang1_thiMarketLevelChayMoiPhut` (60/60), `keyBang1_vanDung1LanMoiPhut_vaNgoaiCuaSoThiKhong`,
   `moPhongThread_1Gio_demCoHoiMarketLevel` (key=1 ⇒ 60; key=0 ⇒ 4 mốc 15').

### Build (local, không deploy)
`mvn -o -q package -DskipTests` → **OK** (exit 0, jar `target/binance-java-sdk-1.2.4.jar`).
`mvn -o -q surefire:test -Dtest=CadenceSplitTest` → **Tests run: 5, Failures: 0, Errors: 0**.

---

## 3. ⚠️ BA BẢN JAR ĐANG TỒN TẠI — CHỐT BẢN CHUẨN TRƯỚC KHI DEPLOY

| # | Nơi | sha256 (rút gọn) | Ghi chú |
|---|---|---|---|
| 1 | **242** `v_t_m/target/binance-java-sdk-1.2.4.jar` | `069adc85e8ae…` | `docs/audit/AUDIT_LIVE_242_20260926.md` |
| 2 | **shadow Oracle** (đang chạy) | `e3bf2d21cdce…` | build 20/09 22:06 · `docs/diag/DIAG_FORWARD_PIPELINE.md:302` |
| 3 | **build HEAD** (`c2b0c963…`) | `c2b0c9634526c2…` | lệch bản shadow 4 ngày commit |

⇒ **Owner phải chốt 1 bản chuẩn** (khuyến nghị: build mới từ patch này, ghi sha256 vào `docs/audit/`).
Patch này được áp trên HEAD `3f6993b` (jar HEAD cũ `c2b0c963…`).

---

## 4. KẾ HOẠCH DEPLOY (từng bước — KHÔNG thực hiện trong vòng này)

Điều kiện tiên quyết: mã hoá nhịp **chỉ bật qua key `MARKET_SCAN_MIN`**.
`MARKET_SCAN_MIN` **không** khớp `TRADING_PREFIXES`/`TRADING_KEYS` ⇒ khi có `TRADING_PROFILE` thì đọc từ **file profile**, KHÔNG đọc env. ⇒ **Đặt `MARKET_SCAN_MIN=1` trong file `TRADING_PROFILE` đang dùng** (hoặc env nếu không dùng profile).

**Đợt A — TÁCH NHỊP (key `MARKET_SCAN_MIN`)**
1. (DEV) build jar; ghi sha256; đối chiếu sha == jar đã chốt ở §3.
2. (OP) backup jar đang chạy + `config.properties`/profile (copy, không sửa tại chỗ).
3. (OP) thêm `MARKET_SCAN_MIN=1` vào file profile đang dùng. **Không** sửa gì khác.
4. (OP) restart service shadow/live theo quy trình hiện hành (owner thực hiện).
5. **Verify A** (xem §5). Sai ⇒ **rollback A** (§6).

**Đợt B — ĐỔI GATE (việc riêng, xem §7)** — làm sau khi A ổn định ≥ 1 tuần.

---

## 5. XÁC MINH SAU DEPLOY (Đợt A)

1. **Nhịp hệu lực**: log có `[CADENCE-SPLIT] MARKET_SCAN_MIN=1 => MARKET-LEVEL(BIG_DOWN/DCA) quet 1 PHUT, SELECTOR luon 15'`.
2. **MARKET-LEVEL ở nhịp 1'**: đếm dòng `Start check level change of market for trade!` ≈ **1440/ngày** (trước: 96/ngày) và `Finish ... (market-only tick)` ≈ 1344/ngày.
3. **Lệnh BIG_DOWN/DCA ở nhịp 1'**: xuất hiện `✅ AI PASS [... BIG_DOWN ...]` / `... DCA_LEVEL1 ...` ở các **phút KHÔNG chia hết 15** (bằng chứng leg 1' đã chạy).
4. **SELECTOR vẫn 15'**: dòng `[GATE] scale=... topk=... n_cand=... n_pass=...` **chỉ** xuất hiện tại phút `:00/:15/:30/:45` (đếm ≈ 96/ngày). Nếu `[GATE]` xuất hiện mỗi phút ⇒ patch sai, rollback.
5. **Số entry/tháng**: kỳ vọng tăng lên **~13,8 entry/tháng** (mốc owner đặt). Lưu ý entry mới của selector vẫn chỉ mở ở 15' ⇒ phần tăng chủ yếu là **BIG_DOWN + DCA**.
6. **Gate pass**: watchdog `bin/health.sh` field `gatePassCuoi` / `gateRejStreak` không đổi xu hướng (gate value `symbolPred` KHÔNG đổi trong đợt A).
7. **ONNX**: `md5` model + `NUM_FEATURES`/`extractFeatures45` KHÔNG đổi (đợt A không chạm).

---

## 6. ROLLBACK

- **A**: xoá/đặt `MARKET_SCAN_MIN=0` (hoặc bỏ key) trong profile ⇒ code trở về đúng hành vi cũ; hoặc khôi phục jar backup §4.2 rồi restart theo quy trình.
- Rollback A **độc lập** với B (không phụ thuộc).
- Tiêu chí rollback ngay: `[GATE]` xuất hiện ở phút lẻ; entry selector mở ngoài mốc 15'; số entry tăng bất thường (> 2–3× kỳ vọng); lỗi `Exception` mới trong `checkMarketLevelChange2Trade`.

---

## 7. ĐỀ XUẤT CHIẾN LƯỢC: 2 ĐỢT DEPLOY RIÊNG

Trong 1 lần deploy HEAD có **2 thay đổi độc lập**: (1) **tách nhịp** selector 15' / BIG_DOWN-DCA 1'; (2) **đổi gate**. ⇒ Khuyến nghị tách **2 đợt**, mỗi đợt 1 thay đổi + rollback riêng:
- **Đợt A (tách nhịp)**: bật `MARKET_SCAN_MIN=1`; gate giữ nguyên. Đo được tác động riêng của nhịp lên số entry/tháng & BIG_DOWN/DCA.
- **Đợt B (đổi gate)**: chỉ sau khi A ổn định (≥7 ngày, không lỗi, chỉ số hợp lý). Nếu gộp chung mà kết quả xấu thì **không biết nguyên nhân do nhịp hay do gate** ⇒ rollback mất cả 2, tốn 1 chu kỳ đo.

---

## 8. ẢNH HƯỞNG ĐÃ BIẾT / ĐIỀU KIỆN (đọc trước khi deploy)

- **ONNX chạy 15× nhiều hơn** ở nhịp 1' (entry predict + funding candidates cho MARKET-LEVEL), đúng như nghiệp vụ sim nhưng **tăng tải**.
- **`↳` Ghi file 15×**: `predictAllCandidates` ghi `storage/data/predictionSymbol/<date>/<ts>` mỗi tick ⇒ ~1440 thư mục/ngày thay vì 96. ⚠️ `df -h /` đang **~93%** ⇒ **phải dọn/giới hạn `predictionSymbol` TRƯỚC khi bật key** (khối ghi `storage/data/prediction/` vẫn chỉ 15' vì nằm trong SELECTOR).
- `MARKET_SCAN_MIN` khi có profile chỉ đọc từ **file profile** (không đọc env) — nếu đặt sai chỗ, key **im lặng không có tác dụng** ⇒ luôn verify §5.1.

## 9. KHÔNG LÀM ĐƯỢC (trong vòng này)
- Không deploy / restart / sửa profile / chạm 242 / sửa `config.properties` / đọc-in key (theo ràng buộc).
- Không chạy `mvn`/sim trên Oracle; build & test chạy **local**. Không push git (commit sót).
