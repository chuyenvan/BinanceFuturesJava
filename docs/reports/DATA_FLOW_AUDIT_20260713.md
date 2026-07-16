# DATA FLOW AUDIT — WFO/Backtest (2026-07-13)

Mục tiêu: rà TOÀN BỘ luồng của MỌI loại dữ liệu dùng trong backtest/WFO — từ **nguồn → export → nạp → dùng trong engine** — và chỉ rõ loại nào có **nguy cơ cadence-mismatch** (kiểu "thiếu ngầm" giống bug funding vừa phát hiện, xem `BUGHUNT_WFO_20260713.md` BUG 4).

File đọc chính:
- `src/main/java/com/binance/chuyennd/ai_ml/wfo/framework/WfoDataset.java` (export/load offline-bin)
- `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java` (engine sim)
- `src/main/java/com/binance/chuyennd/aerospike/DataManagerAerospikeFloatSim.java` (đọc Aerospike)
- `src/main/java/com/binance/chuyennd/research/FundingFeeManager.java` (funding fee)

---

## 1. Nguyên lý bắt bug (vì sao cadence-mismatch nguy hiểm)

Engine sim chạy theo **lưới ticker 1 phút** (master clock). Mỗi phút `time`, engine TRA các map phụ trợ. Cách tra quyết định loại nào "thiếu ngầm":

- **`map.get(time)` KHỚP CHÍNH XÁC phút** → nếu map thưa hơn 1 phút (vd chỉ có mốc 15m), thì 14/15 phút trả `null` → tín hiệu biến mất **âm thầm**, KHÔNG có lỗi ném ra. → **NGUY CƠ CAO**.
- **`floorEntry(time)` (carry-forward)** → mốc gần nhất ≤ time vẫn tra được → cadence thưa vẫn dùng được (miễn không quá hạn). → **tolerant, nguy cơ THẤP**.

Bug funding vừa rồi: `funding.bin` mất forward-fill 15p→phút, engine tra bằng `time2SymbolPred.get(time)` (khớp chính xác) → chỉ 1/15 phút có selector → tần suất sập, BIG_DOWN 159→9.

---

## 2. Bảng audit theo từng loại

| Loại | Nguồn | Cadence kỳ vọng | Export | Nạp (field engine) | Engine tra cứu | Nguy cơ cadence-mismatch |
|---|---|---|---|---|---|---|
| **market data** (`MarketDataObject`: rateDownAvg/rateUpAvg/rateDown15MAvg) | Aerospike set `market_data` (env `WFO_SET_MARKET`) | **1 phút** (per-minute) | `WfoDataset.export()` → `market.bin` | `WfoDataset.load()` → `ds.market` → `time2MarketData` | `time2MarketData.get(time)` **EXACT** (dòng 182, 214, 220, 235) | **THẤP** (nguồn vốn per-minute; là backbone). Vẫn nên đếm vì nếu export lỗi thì gãy âm thầm. |
| **gate pred** (`AiPredictionData`: predReturn15M/predRisk4H) | Aerospike set `ai_pred_market_gate_wfo` / `ai_pred_market_full_basket_v2` (env `WFO_SET_PRED`) | **1 phút** (per-minute) | `WfoDataset.export()` → `pred.bin` | `WfoDataset.load()` → `ds.pred` → `predictionMap` | `predictionMap.get(time)` **EXACT** (dòng 185, 530, 619) | **TRUNG BÌNH** — nếu nguồn gate đổi sang cadence khác (vd 15m) sẽ tái diễn đúng bug funding. Phải đếm. |
| **funding/selector pred** (`long[]` per ts, encode (symId<<32)\|floatBits(score)) | Kaggle files `predict_wf_*.bin` (26B) qua `buildFundingFromWfFiles` + `forwardFillToGrid`; HOẶC Aerospike `funding_selector_pred_1m_v2` | **1 phút SAU forward-fill** (gốc Kaggle = **15 phút**) | `WfoDataset.export()` → `funding.bin` | `WfoDataset.load()` → `ds.funding` → `time2SymbolPred` | `time2SymbolPred.get(time)` **EXACT** (dòng 202, 245) + BIG_DOWN chọn symbol qua cùng map | **CAO — ĐÂY LÀ BUG ĐÃ XẢY RA.** Gốc 15m, nếu quên forward-fill → coverage ~6.7% → tần suất + BIG_DOWN sập. |
| **ticker 1m** (kline per symbol, `KlineObjectSimple[]`) | Aerospike set `kline_1m_opt` (`AEROSPIKE_SET_NAME_TICKER`), đọc 1440 key/ngày dạng `yyyyMMdd-HHmm`; HOẶC Kaggle `KaggleDataLoader.loadDailyTickersShort` | **1 phút, 1440/ngày** | KHÔNG export (đọc trực tiếp lúc sim, theo ngày) | đọc từng ngày trong vòng lặp `simulatorWithInitEntry` | Iterate `entrySet()` (drive vòng lặp) + guard `size()>=1440` else SKIP ngày | **THẤP cho .get-mismatch** (nó LÀ master clock, không bị tra thiếu). Ngày <1440 phút bị SKIP âm thầm → thuộc D2 (time-gap), không phải A6. |
| **funding fee** (settlement rate per symbol) | Aerospike funding map per symbol (`getAllFundingMap`/`getFundingMap`) | **8 giờ** (settlement) | KHÔNG export (nạp qua `FundingFeeManager`) | `FundingFeeManager.symbol2FundingFee` | `time2RateFunding.floorEntry(timestamp)` (dòng 119) — carry-forward, có staleness | **THẤP** — dùng `floorEntry` nên **tolerant** với cadence thưa. Đây là ĐỐI CHỨNG: vì funding fee đã dùng floorEntry nên không gãy; còn funding-selector dùng `.get()` exact nên gãy. |

---

## 3. Kết luận nguy cơ + phạm vi validator A6

**3 loại tra bằng `.get(time)` EXACT trên lưới per-minute** → cùng lớp nguy cơ cadence-mismatch:
- `market` (thấp), `gate` (trung bình), `funding-selector` (**cao — đã dính**).

Validator đếm số lượng (A6) đo coverage per-minute cho **đúng 3 loại này** (nằm trong `WfoDataset`), vì chúng dùng `.get()` exact và đều nạp từ offline-bin — nơi bug export dễ phát sinh.

**Ngoài phạm vi A6 (có lý do):**
- **ticker 1m**: là master clock (không bị tra thiếu); ngày <1440 đã có guard fail-fast + thuộc check D2.
- **funding fee**: dùng `floorEntry` (tolerant cadence 8h) → không thể "thiếu ngầm" kiểu này; nếu cần vẫn có thể thêm nhánh cadence `/8h` sau (đã chừa hằng số ý niệm trong doc validator).

**Điểm mấu chốt để nhớ:** rủi ro cadence-mismatch = (nguồn có cadence THÔ hơn lưới sim) × (engine tra bằng `.get()` khớp-chính-xác). Cả hai điều kiện đúng ⇒ thiếu ngầm. funding-selector thỏa cả hai.

---

## 4. Validator đã thêm — A6CountByCadenceValidator

- **Ý tưởng (Uni chốt):** "counter số phút sẽ dùng ra dữ liệu cần lấy = số cần validate".
- Với mỗi loại, cho range `[start,end]` (mặc định = span riêng `[firstKey,lastKey]` của loại đó; hoặc `ExpectedRanges.source(type)` nếu pre-register) + cadence per-minute:
  - `expected = (end-start)/60000 + 1`
  - `actual = TreeMap size trong [start,end]`
  - `coverage = actual/expected`
- **Ngưỡng:** `coverage < 0.95` ⇒ **BLOCK**; `0.95 ≤ coverage < 0.99` ⇒ **WARN**; `≥ 0.99` ⇒ **PASS**. Cấu hình qua env `WFO_COUNT_BLOCK_BELOW` / `WFO_COUNT_WARN_BELOW`.
- **Bắt bug funding 15m:** trong span riêng của funding, mật độ 15m = ~1/15 per-minute ⇒ coverage ~0.067 ⇒ **BLOCK**. Đo trong span RIÊNG (không dùng span market) nên KHÔNG dính false-positive khi selector kết thúc sớm hơn market (GIỚI HẠN 3).
- **Nguồn:** đọc offline-bin qua `WfoDataset.load(ctx.wfoDataDir())`. Nếu `WFO_DATA_DIR` rỗng ⇒ PASS-skip (không phải run offline-bin; đường Aerospike dùng set `*_1m_v2` vốn per-minute) — tránh biến run khác thành NEEDS_HUMAN.
- Đăng ký vào `PreflightValidators.buildDefault()` (tổng 22 validator). CheckId mới: `A6` (group A, BLOCK).

Ghi chú quyết định (chỗ mơ hồ đã tự chốt):
1. Tên `A5` đã dùng cho Survivorship ⇒ đặt `A6`.
2. Range mặc định = span riêng từng loại (thay vì span market) để tránh false-positive khi funding hết sớm hơn market.
3. `wfoDataDir` rỗng ⇒ skip-PASS thay vì NEEDS_HUMAN, để không phá các run đang chạy (task re-export song song).
