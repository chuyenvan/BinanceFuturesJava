# PLAN — THIẾT KẾ LẠI THỰC THI NHỊP: SELECTOR 15' + MARKET best-effort 1' (POOL 1 THREAD)

Trạng thái: **CHUẨN BỊ (chưa deploy)** · 2026-09-28 · branch `module` · **KHÔNG push**.
Tiền đề: `docs/audit/DEPLOY_CADENCE_SPLIT_SHADOW_20260927.md` — bản `53c80a1` (`MARKET_SCAN_MIN=1`)
**ĐÃ ROLLBACK** vì `checkMarketLevelChange2Trade()` tốn **~2m48s/lượt** nhưng `executorService` là
**pool 1 thread** (`NUMBER_THREAD_ORDER_MANAGER=1`, `DetectEntrySignal2TradeNormal.java:70`), nộp 1 tick/phút
⇒ FIFO phình vô hạn ⇒ nhịp SELECTOR bị giãn **~15×2,8 ≈ 42 phút**.

Mục tiêu vòng này: **SELECTOR luôn fire đúng mốc 15'** VÀ **MARKET-LEVEL (BIG_DOWN/DCA) best-effort mỗi phút**
— **với pool 1 thread** — mà **không** để hàng đợi phình.

---

## 1. VIỆC 1 — CHỌN THIẾT KẾ: **(A) ƯU TIÊN + HÀNG ĐỢI CÓ CHẶN**

| | (A) Ưu tiên + hàng đợi có chặn | (B) Pool 2 thread | (C) Tách PREP nặng |
|---|---|---|---|
| Thay đổi | nhỏ: 1 cổng ra executor + đếm slot | đổi pool ⇒ đổi `config` prod | refactor lớn |
| Tranh chấp shared state | **KHÔNG** (vẫn 1 task/lúc) | **CÓ (chặn cứng)** | phải chứng minh lại |
| Nguy cơ | selector trễ ≤ 1 lượt (≤2,8') khi đang có lượt chạy | race + deadlock/lock | rủi ro logic cao |

**Chọn (A).** Lý do bằng số + bằng CODE:

- **Pool 1 thread + (A) ⇒ tại mọi thời điểm chỉ có ≤1 task chạy** ⇒ **không phát sinh đồng thời** ⇒
  không thể có tranh chấp. Hàng đợi bị chặn: MKT chỉ nộp khi rảnh; SEL tối đa 1 đang chờ ⇒ **hàng đợi ≤ 1**.
- **(B) có tranh chấp THẬT (đã kiểm code):** `predictAllCandidates()` (chạy ở **CẢ 2 nhịp**, nằm TRÊN ranh
  giới tách, `DetectEntrySignal2TradeNormal.java:620`) làm `selectorRankPool.clear()` / `selPnp.clear()` /
  `selFeat45.clear()` / `selMapPred.clear()` (dòng 623-626) rồi `put(...)`, trong khi khối **SELECTOR**
  (dưới ranh giới) **đọc** `selectorRankPool` (:367) và `selMapPred` (:425). 4 map này là `TreeMap`/`HashMap`
  **thường, KHÔNG `synchronized`** ⇒ 2 thread chạy ⇒ clear/put **đè** lên lúc thread kia đang đọc
  ⇒ hỏng dữ liệu/kết quả sai. Muốn dùng (B) phải bọc khóa toàn bộ phần PREP (≈ nối tiếp hoá = mất lợi ích)
  hoặc refactor chia state theo luồng. ⇒ **(B) bị loại**.
- **(C)** không giải quyết tính ưu tiên (PREP nặng vẫn chung 1 thread); để dành bước sau nếu cần tăng thông lượng.

### Ranh giới nhịp (giữ nguyên như `53c80a1`)
TRÊN ranh giới (chạy CẢ 2 nhịp) = PREP + `levelChange` + `predictAllCandidates` + leg **BIG_DOWN** + **DCA**.
DƯỚI ranh giới (chỉ 15') = xếp hạng pool + mở entry selector + ghi `prediction`.
Tick 1' (`selectorLeg=false`) **early-return** ngay trước khối SELECTOR (`:350-353`).

---

## 2. VIỆC 2 — CÔNG TẮC + "OFF ⇒ Y NGUYÊN"

- Giữ nguyên key **`MARKET_SCAN_MIN`** (`<=0`/không khai ⇒ selector 15', không có market-scan riêng).
- **Thêm key mới `MARKET_SCAN_PRIORITY`** (`Configs.java`, int, **mặc định 0 = OFF**):
  - `<=\ 0` / không khai ⇒ **TẮT**: nộp tick vào `executorService` **y như cũ**, không cổng, không đếm slot
    ⇒ **y nguyên** (đúng đường code HEAD của `53c80a1`).
  - `>0` (dùng `1`) ⇒ **BẬT** cổng: SELECTOR luôn được xếp hàng (≤1 chờ); MARKET chỉ nộp khi rảnh (bận ⇒ bỏ qua).

### Cơ chế (nhỏ nhất, thuần hàm để test)
`DetectEntrySignal2TradeNormal`:
```java
static final class TickGate {                 // AtomicInteger pending + AtomicBoolean selectorWaiting
    boolean acceptSelector(); // luon nhan; toi da 1 cho
    boolean acceptMarket();   // chi khi pending==0 (ranh); ban => false (BO QUA)
    void done(boolean selectorLeg);
}
static boolean shouldSubmit(int priority, TickGate g, boolean sel) {
    if (priority <= 0) return true;                       // OFF => y nguyen
    return sel ? g.acceptSelector() : g.acceptMarket();
}
```
Vòng thread: `if (shouldSubmit(...)) executorService.execute(() -> { try { check(...); } finally { if (priority>0) tickGate.done(sel); } });`
`done(...)` nằm trong `finally` ⇒ slot luôn được trả (kể cả khi task ném lỗi).

### Diff (nhỏ nhất)
- `Configs.java`: **+16 / -0** dòng (field + loader).
- `DetectEntrySignal2TradeNormal.java`: **+82 / -5** dòng (TickGate + `shouldSubmit` + routing + 1 dòng log).
- test mới `CadencePriorityTest.java`: **+131 / -0**.
- **KHÔNG chạm** ONNX / `NUM_FEATURES` / `extractFeatures45` / thuật toán entry-gate / tham số nào khác.

### Bằng chứng "OFF ⇒ y nguyên"
1. **Logic**: OFF ⇒ `shouldSubmit` trả `true` vô điều kiện ⇒ trong `execute` chỉ còn `check(...)` thuần;
   `finally` không chạm gì (`priority<=0`) ⇒ **đường thực thi y hệt `53c80a1`**.
2. **Test** `CadencePriorityTest.tat_thiLuonNop_yNguyen`: OFF mà gate đã "no" (2 slot) vẫn `true` cho cả SEL/MKT.
3. **Parity md5**: xem §5 (kết luận: **không chạy lại được trong vòng này**, chứng minh bằng cấu trúc).

### Test/logic-proof cho 3 điều kiện (VIỆC 2)
`src/test/java/com/binance/chuyennd/trading/CadencePriorityTest.java` — **5/5 PASS** (local):
- `bat_marketKhongBaoGioXepHangKhiBan`: bận ⇒ `acceptMarket` false liên tiếp, `pending` **không tăng**.
- `bat_selectorLuonDuocNhan_toiDa1Cho`: SEL luôn nhận; khi đã có 1 chờ ⇒ chặn slot 2 (**không phình**).
- `moPhong1Gio_selectorFire4Moc_hangDoiKhongPhinh`: mô phỏng **pool 1 thread**, `RUN_SEC=168s`, 1 giờ ⇒
  **SELECTOR enq = 4/4**, **maxQueue = 1**, **maxPending = 1** (≤2), MKT enq = 16.
- `tat_thiLuonNop_yNguyen` + `keyMacDinh_tat_vaKhongChamThamSoKhac`.
`CadenceSplitTest` (cũ) vẫn **5/5 PASS** (không hồi quy nhịp). **Toàn bộ suite: 164 test / 0 fail / 0 error** (local).

---

## 3. VIỆC 3 — NHỊP MARKET THỰC TẾ KHI SKIP-IF-BUSY

- **ĐO ĐƯỢC**: thời gian 1 lượt `checkMarketLevelChange2Trade` = **~2m48s (168s)** — shadow 2026-09-27
  (start 07:38:06→07:40:55→07:43:42), xem `docs/audit/DEPLOY_CADENCE_SPLIT_SHADOW_20260927.md` §3.
- **ƯỚC LƯỢNG** (mô hình hoá, KHÔNG đo live): 1 giờ = 3600s; SELECTOR chiếm `4×168=672s`
  ⇒ còn `2928s / 168 ≈ 17,4` lượt MKT ⇒ **~16-17 lượt/giờ** (mô hình cho **16**), thay vì **60 cơ hội**.
  Mỗi lượt MKT mất ~3' lịch (2,8' chạy + chờ mốc phút) ⇒ MKT chạy ~1 lượt/3', **không bao giờ vượt 60/giờ**.
- Hệ quả: nộp **1 tick/phút** nhưng **thực thi ~16 lượt/giờ** ⇒ trần thông lượng do pool 1 thread, KHÔNG do
  hàng đợi; phần "dư" bị **bỏ qua có chủ đích** (skip-if-busy), **không** tích luỹ.

---

## 4. VIỆC 4 — KẾ HOẠCH DEPLOY 2 BƯỚC (viết, KHÔNG thực hiện)

> ⚠️ **3 BẢN JAR ĐANG TỒN TẠI — PHẢI CHỐT BẢN CHUẨN TRƯỚC KHI DEPLOY:**
> | # | Nơi | sha256 rút gọn | Ghi chú |
> |---|---|---|---|
> | 1 | **242** `v_t_m/target/…jar` | `069adc85…` | live |
> | 2 | **shadow Oracle** | `e3bf2d21…` | build 20/09 22:06 (đang chạy) |
> | 3 | **build HEAD** | `c2b0c963…` | lệch shadow 4 ngày |
>
> ⇒ jar mới **phải là HEAD + patch này** (KHÔNG chỉ patch rời rạc) + ghi sha256 vào `docs/audit/`.
> Bản deploy `53c80a1` trước đây còn **gộp 11 commit nhóm (iii) ngoài phạm vi** ⇒ **lần này phải tách đúng 1 đợt**.

**Thứ tự bắt buộc**: **SHADOW trước** → đo/ổn định → **242 SAU khi owner duyệt riêng**.

**Bước A — tách nhịp + cổng ưu tiên (shadow)**
1. (DEV) build jar HEAD+patch; ghi sha256; đối chiếu jar đã chốt.
2. (OP) backup jar đang chạy + `conf/env.sh` (copy, KHÔNG sửa tại chỗ).
3. (OP) đặt `MARKET_SCAN_MIN=1` và `MARKET_SCAN_PRIORITY=1` (instance shadow **không** có `TRADING_PROFILE`
   ⇒ đọc **env** trong `conf/env.sh`). Không sửa gì khác.
4. (OP) restart `shadow-c3` theo quy trình.
5. **Xác minh A** (dưới). Sai ⇒ **rollback** (dưới).

**Xác minh A** (log shadow, ~1-3 giờ):
- `[CADENCE-SPLIT] MARKET_SCAN_MIN=1 …` + `[CADENCE-SPLIT-V2] MARKET_SCAN_PRIORITY=1 …` ⇒ cổng bật.
- **SELECTOR fire đúng 4 mốc/giờ**: `[GATE] scale=… topk=… n_cand=… n_pass=…` **chỉ** ở phút `:00/:15/:30/:45`
  (≈96/ngày). Nếu `[GATE]` xuất hiện ở phút lẻ ⇒ **SAI, rollback**.
- **MARKET chạy ~16-20 lượt/giờ** (KHÔNG ~21 như bản rollback trước → chứng tỏ skip hoạt động).
- **KHÔNG có hàng đợi phình**: `Start check level change…` / `Finish…(market-only tick)` **không dồn** — số
  `Finish` ≈ số `Start` trong cùng cửa sổ; khoảng cách `Start` ~3' đều, **không co lại rồi bùng**.
- **`[GATE]` vẫn 15'** (gate value KHÔNG đổi trong bước A).
- **would-BUY BIG_DOWN/DCA ở phút lẻ**: log `✅ AI PASS [... BIG_DOWN …]` / `… DCA_LEVEL1 …` xuất hiện ở
  phút **KHÔNG** chia hết 15.
- ONNX md5 + `NUM_FEATURES`/`extractFeatures45` KHÔNG đổi.

**Rollback A** (độc lập): đặt `MARKET_SCAN_MIN=0` **và** `MARKET_SCAN_PRIORITY=0` (hoặc bỏ 2 dòng) trong
`conf/env.sh` ⇒ về hành vi cũ (byte-identical) không cần đổi jar; hoặc khôi phục jar backup rồi restart.
**Tiêu chí rollback ngay**: `[GATE]` ở phút lẻ; entry selector mở ngoài mốc 15'; số entry tăng bất thường;
`Exception` mới trong `checkMarketLevelChange2Trade`; hàng đợi có dấu hiệu dồn.

**Bước B — 242**: **CHỈ sau khi owner duyệt riêng** và bước A ổn định. Áp cùng key; rollback như A.

⚠️ **Lưu ý đĩa**: `predictionSymbol` ghi **theo tick** ⇒ bật nhịp 1' ≈ **150 MB/ngày** (`df /` đang **93%**).
Cần retention ≤12 ngày (xem audit 2026-09-27 §0) trước khi bật.

---

## 5. PARITY "OFF ⇒ Y NGUYÊN" — TRẠNG THÁI

- **Không chạy lại được 2 sim md5 trong vòng này** (mỗi chân ~4,5 năm dữ liệu 1' trên ~800 symbol; chạy
  Kaggle ~hàng chục phút/chân, local hàng giờ; ràng buộc vòng này: build/test **local**, output nhỏ, 1 slot JVM).
- **Chứng minh bằng CẤU TRÚC (đủ mạnh cho patch LIVE-only)**:
  1. `git diff --stat` chỉ chạm `Configs.java`, `DetectEntrySignal2TradeNormal.java`, test mới + docs —
     **KHÔNG** file nào trong `com/binance/chuyennd/research/**` (đường SIM).
  2. Đường SIM `SimulatorMarketLevelTicker1MStopLoss` **không** tham chiếu `MARKET_SCAN_PRIORITY` /
     `TickGate` / `shouldSubmit` / `checkMarketLevelChange2Trade` ⇒ **không chạy** code đã đổi.
  3. OFF ⇒ `Configs.MARKET_SCAN_PRIORITY=0` (đã assert trong test) và `shouldSubmit` trả `true` vô điều kiện
     ⇒ đường LIVE cũng y hệt `53c80a1`.
- ⇒ **Kỳ vọng md5 KHÔNG đổi**: `99e42b75…` (KEEPLEG0, 1085/103.083) và `efb793e2…` (T170, 1089/111.070).
  Baseline còn nguyên local để đối chiếu nếu owner muốn chạy lại (2 chân `par-kg0`/`par-t170` trong
  `research/analysis/family2_tp_run.py`).
- Nếu owner muốn **bằng chứng md5 empirical** trước khi deploy: chạy 2 chân parity trên Kaggle
  (`python3 research/analysis/family2_tp_run.py par`). **Lệch ⇒ DỪNG, báo RÕ.**

---

## 6. CẦN OWNER DUYỆT
1. **Thiết kế (A)** (ưu tiên + hàng đợi có chặn) và **key mới `MARKET_SCAN_PRIORITY`** (mặc định OFF).
2. **Chốt bản jar chuẩn** (HEAD+patch) + sha256 (§4).
3. **Thứ tự deploy: shadow trước — 242 sau** (duyệt riêng).
4. (khuyến nghị) chạy **2 chân parity md5** trước khi bật key.

## 7. KHÔNG LÀM ĐƯỢC TRONG VÒNG NÀY
- Không deploy/restart/sửa config/shadow/242; không chạy gì trên Oracle; **build/test local**.
- Không chạy lại 2 sim md5 (lý do §5) — chỉ có bằng chứng cấu trúc + test logic.
- Nhịp MKT ~16-17/giờ là **ƯỚC LƯỢNG** (mô hình), không phải đo live.
