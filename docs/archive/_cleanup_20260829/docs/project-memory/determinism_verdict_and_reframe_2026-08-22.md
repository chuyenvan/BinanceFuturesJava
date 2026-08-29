# Determinism verdict + reframe "vđ thật ở đâu" — 2026-08-22

## TL;DR
Engine backtest là **DETERMINISTIC** (chứng minh bằng code, session này). Do đó gap
FULL≈19840 (aerospike-mode) ↔ ≈10000 (file-mode) **KHÔNG phải** non-determinism — nó là
**chênh lệch INPUT DATA** giữa 2 nguồn ticker. Baseline-pinning vô nghĩa không phải vì
"số nhảy loạn", mà vì ta đang so 2 run đứng trên 2 nền dữ liệu khác nhau. Vấn đề lớn nhất
KHÔNG nằm ở harness (harness fixable ngay) mà ở **thiết kế chiến lược** (pump + lướt → đuôi
maxDD lớn, ăn ít) — đúng như project instructions.

## Bằng chứng engine deterministic (đọc code, không suy đoán)
File: `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java`
và `.../wfo/framework/tasks/StrategyWfoTask.java`, `.../wfo/VerifyOneWindow.java`.

1. **Chronological iteration**: `time2Tickers` là `TreeMap<Long,KlineObjectSimple[]>`
   (cả 3 loader `loadDailyTickersShort` / `getDataShortFromFile` /
   `readDataFromAerospike1M_ShortKey` đều trả TreeMap). `entrySet()` duyệt theo key tăng dần
   = đúng thứ tự phút. Không có HashMap-order bug.
2. **Seed cố định per window**: `StrategyWfoTask` L167 `p.put("seed", SEED_BASE+i)`, L250
   `Random rnd = new Random(seed)`. Cùng window → cùng chuỗi random.
3. **Window độc lập**: L357-359 mỗi job `BudgetManagerSimple.resetInstance()`,
   `HistoryManager.resetCache()`, `CoinRankManager.resetCache()`. Không carry capital giữa
   window → thứ tự worker chạy KHÔNG ảnh hưởng kết quả từng window (loại giả thuyết
   "capital chảy giữa window theo completion order").
4. **parallelStream an toàn**: chỉ 1 chỗ `time2FundingPre.values().parallelStream()`
   (L1147) — mỗi `long[] preds` sort in-place độc lập bằng `quickSortByFloatPred` (pivot=high,
   single-thread mỗi mảng). Không shared mutable state, không float-reduction order-dependent.
   Cùng input → cùng output bất kể số core.
5. **Selection ổn định**: `symbol2BUY` là `HashSet<Short>` — `Short.hashCode()==value` nên
   thứ tự duyệt ổn định run-to-run; top-N lấy từ `TreeMap<Float,Short> predict2Symbol` đã sort.
6. **Tiền đề của chính team**: `VerifyOneWindow` (TASK-142) javadoc: "số PHẢI trùng khít
   (cache chỉ đổi IO, không đổi kết quả)". Team đã thiết kế với giả định deterministic.

Kết luận suy diễn: cùng config + cùng data → cùng số. Rerun SAME input KHÔNG lệch.

## Vậy 19k ↔ 10k là gì
Engine deterministic ⇒ toàn bộ gap quy về **khác input**:
- aerospike-mode đọc local ns=test (kline_1m_opt = 2,952,455 record).
- file-mode đọc .bin — từng có 44 ngày thiếu phút (đã fix nhưng fix KHÔNG đóng gap ⇒ còn
  chênh ở nhiều ngày/phút khác, khớp log "Date data error / SKIP" user paste: 20240303...).
- 2 store aerospike cũng lệch: ns=test 2,952,455 vs .226 ns=ticker 2,909,486 (~43k record).
Gap ≈2x đến từ file-mode **thiếu/khác data ở nhiều phiên** → ít/khác trade → PnL thấp.
Đây là **data-hygiene**, không phải bí ẩn engine.

## "10w đạt 1.02 chạy trực tiếp Oracle" phản ánh gì
Gần như KHÔNG gì hữu ích: chỉ 2 leg (không phải 18), lại chạy trên file-mode có gap.
Per-window đã diverge, total 1.02 chỉ khớp do cancellation ngẫu nhiên. Không đọc được edge.

## Reframe: đâu là "vđ đúng"
Có 2 tầng, phải tách và xếp thứ tự:
- **Tầng harness (blocker, fixable NGAY)**: khóa MỘT nền data đã verify, freeze, reproducible.
  Vì engine deterministic nên chỉ cần 1 nguồn ticker đúng → mọi rerun trùng khít → A/B tin được.
  KHÔNG cần đi tìm "non-determinism" nữa — đã loại.
- **Tầng chiến lược (vđ LỚN NHẤT, đúng ý user "vđ nằm chỗ khác")**: model chọn coin pump
  nhưng label 6% = lướt → cắt lãi sớm, ôm đuôi dump → maxDD lớn, ăn ít. Baseline 19k hay 10k
  đều không trả lời được câu này. Đây mới là chỗ tạo/giết edge.

## Khuyến nghị (không chốt baseline)
1. Ngừng săn non-determinism (đã đóng) và ngừng chốt baseline 19k/10k.
2. Freeze 1 data foundation: chọn nguồn ticker đã verify == Binance (đã xác nhận 20240115
   identical), export .bin đầy đủ 1440'/ngày cho toàn universe, checksum, dùng CHUNG cho mọi
   run. Sau đó chạy VerifyOneWindow 2 lần cùng window → phải trùng byte (empirical proof).
3. Chỉ khi harness reproducible mới chạy A/B TIME_STOP {off,120,168,240}.
4. Song song, mở mặt trận chiến lược: đo edge thật (pump-selection có edge gì, label 6% lướt
   đúng/sai), thiết kế SL/TP theo tư duy "chặn lỗ khi có lãi, nuôi lãi" — xem project instructions.
