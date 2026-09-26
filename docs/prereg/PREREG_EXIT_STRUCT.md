# PRE-REG: VÒNG CẤU TRÚC LUẬT THOÁT — **BỎ TIME-STOP 168h + "DCA TỚI CHẾT"** (A0/A1/A2/A3)

Pre-registration **CHỐT TRƯỚC** khi chạy. **KHÔNG sửa sau khi thấy kết quả.** Repo `BinanceFuturesJava`,
branch `module`. Sim: `com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss`.

**Yêu cầu owner (26/09 23:18, nguyên văn — nguồn chân lý):**
> *"có khi bỏ SL cứng 168h ấy. quay lại dca tới chết nhưng cần xem kết quả khi b mà ok thì có thể giữ"*

⇒ Mục đích: xem biến thể **bỏ time-stop 168h** + **DCA phản xạ (tới chết)** có **PASS rào (b′) bỏ-top-50% > 0**
không; **nếu OK thì GIỮ**.

---

## 1. NỀN (BẮT BUỘC — không chạy trên cấu hình khác)

Nền = **`sel15`** = KEEPLEG0 production flatgrid + `SIM_ENTRY_SAMPLE_MIN=15` (**đã chứng minh khớp thiết kế**,
`docs/result/RESULT_SIM_CADENCE_MATCH.md`, commit `8aedde8` / code `3b6c6e9` / AMENDMENT `30e5f4d`):
`SIM_ENTRY_SAMPLE_MIN` **chỉ chặn leg selector**; `BIG_DOWN`/`DCA_LEVEL1` giữ nhịp **1′**.

- Profile nền: `profiles/x1_gs_t170.properties` (= PRODUCTION FLATGRID) + override
  `DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0` (**KEEPLEG0**).
- Cửa sổ: **DEV 2021-07-01 .. 2025-12-31** (1.644 ngày). **KHÔNG chạm 2026** (holdout nguyên vẹn).
- Jar: **TÁI DÙNG** `sim-jar-cadence` (build từ commit `3b6c6e9`), sha256 `43888ebd…`.
  ⇒ **KHÔNG sửa code, KHÔNG build lại** (mọi công tắc đã tồn tại, xem §2).
- `sel15` (A0) **đã có sẵn** (`cd-sel15`: n=744 · 0,453 entry/ngày · CAGR **+17,29%** · UW 166 · conc 6,77%) ⇒ dùng lại.

## 2. CÔNG TẮC (VIỆC 1 — chốt TRƯỚC, `file:line`)

- **Time-stop 168h đang chạy** = `SIM_LOSER_TIME_STOP_HOURS` → `Configs.LOSER_TIME_STOP_HOURS`
  (`src/main/java/com/binance/chuyennd/tradecore/Configs.java:433`), cài đặt tại
  `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:1016-1030`
  (trong `startUpdateOldOrderTrading`): cụm **CHƯA arm** (`priceSL==null`) giữ quá 168h kể từ
  `clusterFirstLegTime` ⇒ đóng tại `min(open, close)`. Profile nền khai `=168`.
  **TẮT = override `SIM_LOSER_TIME_STOP_HOURS=0`** (đúng default code; nhánh `loserTsHours > 0` không chạy).
- ⚠️ Ghi rõ để không nhầm: key `TIME_STOP_HOURS` (profile nền khai `=0`) là **CƠ CHẾ ĐÃ CHẾT** — cơ chế
  "theta-expiry" trong `updateStatusNew` đã bị **XÓA** ở commit `5f40a90` (2026-09-03, chính commit ghi:
  *"HARD_SL_PCT (0), HARD_STOP_LOSS_RATE (0), TIME_STOP_HOURS (0) — chỉ còn LOSER_TIME_STOP_HOURS=168"*).
  Hiện **không có reader** cho `TIME_STOP_HOURS` ⇒ **time-stop 168h sống duy nhất = LOSER_TIME_STOP_HOURS**.
- **"DCA tới chết"** = `DCA_GRID_ENABLED=false` (`Configs.java:186`) ⇒ quay về **DCA phản xạ**
  `DcaUtils.shouldDca` (via `DcaProcessor.getDCA`, `DcaProcessor.java:46`), **KHÔNG có trần số leg**
  (khác grid có `dcaGridLegs()` chặn).
- **⇒ KHÔNG cần sửa code ⇒ KHÔNG cần chạy lại công parity.** (Parity "TẮT = y nguyên" đã PASS ở
  `RESULT_SIM_CADENCE_MATCH` §0 với jar này: `99e42b75…`/1085/103083 và `efb793e2…`/1089/111070.)

## 3. 4 ARM (k = 3 biến thể mới so với A0)

| arm | DCA | time-stop 168h | tag Kaggle | trạng thái |
|---|---|---|---|---|
| **A0** | grid (như hiện tại) | **GIỮ** | `cd-sel15` | **đã có — dùng lại** nếu khớp (n=744/0,453/+17,29%) |
| **A1** | grid | **BỎ** (`SIM_LOSER_TIME_STOP_HOURS=0`) | `xs-a1` | chạy |
| **A2** | **phản xạ "tới chết"** (`DCA_GRID_ENABLED=false`) | **BỎ** | `xs-a2` | chạy ← cái owner muốn xem |
| **A3** | phản xạ | GIỮ | `xs-a3` | chạy |

Tất cả arm GIỮ `SIM_ENTRY_SAMPLE_MIN=15` (nền) + KEEPLEG0 weights/scale.

**Thứ tự ưu tiên (nếu phải cắt):** **A2 > A1 > A3** (A2 là câu hỏi owner; A1 tách đóng góp của
time-stop; A3 tách đóng góp của DCA-phản-xạ khi còn time-stop).

## 4. KỲ VỌNG GHI TRƯỚC (bắt buộc; theo chẩn đoán MẤT CÂN XỨNG)

Chẩn đoán mới nhất (`RESULT_TAIL_ROBUST_RULERS.md`, `3a3ec4f`): mắt xích = **MẤT CÂN XỨNG ĐỘ LỚN**
`mean|lỗ|/mean lãi = 2,9–3,6×` (TB ~3,1×), `sign%>0 = 83–91%`; `tf_5≈0`, `tf_10<0`;
lãi đến ~80–137% từ top-5% leg. Hướng đúng = **cắt lỗ ngắn hơn / để lãi chạy**, **KHÔNG** phải nhồi thêm.

- **A2 (DCA tới chết + bỏ TS168) DỰ KIẾN FAIL rào (b′)** — nhồi thêm vào cụm đang lỗ ⇒ **TĂNG** `mean|lỗ|`
  và **TĂNG lỗ lớn nhất 1 coin**, làm **mất cân xứng NẶNG HƠN** (kỳ vọng `> 3,6×`) ⇒ `bỏ-50%` **âm sâu hơn A0**.
- **A1 (chỉ bỏ TS168) dự kiến FAIL (b′)**, xấu hơn hoặc xấp xỉ A0 về (b′): bỏ time-stop ⇒ zombie leg giữ lâu,
  nhưng grid **có trần leg** nên DCA không nhồi vô hạn ⇒ tác động nhỏ hơn A2.
- **A3 (phản xạ + giữ TS168) dự kiến FAIL (b′)**; có thể giảm nhẹ lỗ lớn nhờ TS168 cắt zombie.
- **Kỳ vọng chung:** **CRÓ KHẢ NĂNG CAO cả 3 arm FAIL (a) và (b′)**; nếu cả 3 FAIL ⇒ **kết luận hướng đúng
  là cắt lỗ ngắn hơn / để lãi chạy**, không phải nhồi thêm (đúng như owner đã thoả thuận trước).

## 5. CHỈ SỐ + CÁCH CHẤM (chốt trước)

1. **Rào (a):** `%PnL từ top-1% lệnh ≤ 15%` ⇒ PASS/FAIL.
2. **Rào (b′):** `bỏ top-50% lệnh ⇒ PnL > 0` ⇒ PASS/FAIL + độ âm/dương.
3. **`q*`** (bỏ bao nhiêu % thì hết lãi) + **`median` PnL/leg** + `tf_5` / `tf_10`.
4. **MẤT CÂN XỨNG (chỉ số QUYẾT ĐỊNH của vòng này):** `mean|lỗ|/mean lãi` + `sign%>0`.
5. **3 chỉ số martingale (BẮT BUỘC):** ① **lỗ lớn nhất trên 1 vị thế/1 coin** (từng năm) ② **conc 1 coin có
   vượt 15% không** khi DCA nhồi thêm leg ③ **số coin "chết" hoàn toàn** (không hồi).
6. **Rào cũ** bằng `--appetite latest`: maxDD ≤40 · UW ≤250 · quý ≥−20 · **0 năm âm (CỨNG)**; + **trần gross
   70%** (báo cả 2 cách áp) + phí `0,006`.
7. **Bộ thước chuẩn đề xuất** (chấm CẢ 2 bộ để owner chốt): `{tf_5, loss_mean, wl_ratio, median, conc_5}`
   + bộ rate `{TSloss%, mP|SM, mP|SL, mMargin}` (tối đa 1 rate nhóm tần suất, **KHÔNG** tính `meanP`).
8. **CI block-72h, 2000 rep, seed `20260905`, `inflate(k=3)=1,4823`**; so **A_x vs A0** (paired).
   Δ vs 2 đối chứng (retrain `A45−45deploy`, nhiễu `V5−V1`) **không áp dụng** ở đây (vòng này không so model).

## 6. RÀNG BUỘC CỨNG

1. **KHÔNG chạy Java/sim trên Oracle** ⇒ **Kaggle** (chi phí 0). 2. **KHÔNG chạm** production/242/ONNX/
   `NUM_FEATURES`/`extractFeatures45`/đường LIVE — **chỉ đường SIM**. 3. **KHÔNG push git**, commit sớm.
4. **DEV only ≤ 2025-12-31**; **KHÔNG chạm 2026**. 5. File NHỎ, dọn ngay (`df` ~93%). 6. Output tool THẬT NHỎ.

## 7. NGÂN SÁCH

3 arm × ~11,6–21,7 phút = **1 đợt Kaggle CPU song song (3/5 slot)**, chi phí **0**. Báo owner trước khi chạy.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
