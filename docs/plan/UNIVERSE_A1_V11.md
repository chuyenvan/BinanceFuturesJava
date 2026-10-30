# UNIVERSE_A1_V11 — bộ lọc TradFi+INDEX cho v1.1 / shadow (CHUẨN BỊ, CHƯA DEPLOY)

Ngày 2026-10-30. Nhánh `v1.1/universe-a1` tạo từ `16de49a6` (`v1.1/exec-probe`), worktree
`~/claude_master/v11_univ`. Mục tiêu: đưa universe v1.1 về đúng universe go-live A1 (không TradFi, không INDEX)
ở **mọi tầng** — universe giao dịch, market features (ALT_EW, `calMarketData`, gate input) — cho **cả live lẫn
sim/replay**, để parity live↔offline đo trên cùng một universe.

## 1. Thay đổi (file:line)

| # | File:line | Nội dung |
|---|---|---|
| 1 | `src/main/java/com/binance/chuyennd/tradecore/selector/UniverseA1Filter.java:44-231` | Lớp lọc duy nhất: cờ `UNIVERSE_A1` (mặc định 0), đọc `exchangeInfo` từ file, định nghĩa TradFi/INDEX, `isExcluded`, `filter(Map)`, `filterMinutes(TreeMap)`, stats, test hooks |
| 2 | `.../websocket/TickerIngestor2AerospikeNew.java:136` | Universe live: bỏ symbol bị loại ngay khi nhận `/ticker/price` (=> không vào ticker cache, S1 pool, feature, gate, order) |
| 3 | `.../websocket/TickerIngestor2AerospikeNew.java:520` | Đường repair/collect symbol từ Redis: cùng bộ lọc |
| 4 | `.../tradecore/selector/AltEwIndex.java:109` | ALT_EW (X14): `excluded[i]` thêm TF/INDEX; live + replay dùng chung lớp |
| 5 | `.../tradecore/MarketBigChangeDetector.java:61` | `calMarketData`: lọc snapshot trước khi tính `rateDownAvg/rateUpAvg/rateDown15MAvg` và breadth |
| 6 | `.../ai_ml/features/export/gate/ExportGateDataset.java:170-171` | BT replay (`replayToCsv`): lọc `today`/`tomorrow` trước `lookup`, `updateHistory`, `extractAllFeatures`, label all-market |
| 7 | `.../ai_ml/features/export/entry/LiveFeaturePipeline.java:212,253,269` | Live + NEW2: lọc `seed`, catch-up, snapshot phút quyết định (=> history/selector, market features, gate input, `Result.snapshot`) |
| 8 | `.../tradecore/Cfg.java:58-59,77-79` | Khai báo key: `UNIVERSE_A1` = tham số giao dịch; `UNIVERSE_A1_EXCHANGE_INFO`, `UNIVERSE_A1_INDEX_LIST` = hạ tầng (được đặt qua env kể cả khi có profile) |
| 9 | `src/test/java/com/binance/chuyennd/tradecore/selector/UniverseA1FilterTest.java` + `src/test/resources/universe_a1_exchange_info.json` | 4 unit test với fixture exchangeInfo: cờ TẮT không lọc; TF theo contractType/underlyingType; INDEX theo underlyingType + danh sách; PREMARKET/COIN/thiếu underlyingType không bị loại; chuẩn hoá tên ngắn; filter giữ map gốc; filterMinutes |

**Định nghĩa (nguyên văn HO2026_TRADFI_AUDIT §2):** TF ⇔ `contractType` chứa `TRADIFI`/`TRADFI` HOẶC
`underlyingType` ∉ {COIN, INDEX, PREMARKET}. INDEX ⇔ `underlyingType=INDEX` HOẶC symbol trong
`UNIVERSE_A1_INDEX_LIST` (mặc định `ALLUSDT,BTCDOMUSDT,DEFIUSDT`). `underlyingType` thiếu ⇒ **không** coi là TF
(giống TradFiClassifier: `verified=false`), ghi nhận trong code `UniverseA1Filter.java:217-219`.

## 2. Cờ cấu hình

| key | mặc định | ý nghĩa |
|---|---|---|
| `UNIVERSE_A1` | `0` (TẮT) | `1` = bật lọc ở mọi điểm 1,2,4,5,6,7 |
| `UNIVERSE_A1_EXCHANGE_INFO` | `EXCHANGE_INFO_PATH` hoặc `/kaggle/input/datasets/chuyendinh/java-run/exchange_info.data` | file exchangeInfo JSON (có `symbols[].symbol/contractType/underlyingType`) |
| `UNIVERSE_A1_INDEX_LIST` | `ALLUSDT,BTCDOMUSDT,DEFIUSDT` | danh sách INDEX bổ sung |

Bật: đặt `UNIVERSE_A1=1` + trỏ `UNIVERSE_A1_EXCHANGE_INFO` tới file có trên host (KHÔNG gọi Binance API).
Nếu cờ bật mà file thiếu/hỏng ⇒ **fail-fast** `IllegalStateException` lúc khởi động — không chạy nửa vời với
universe không xác định (`UniverseA1Filter.java:78-82`).

## 3. Vì sao đủ "live + sim/replay (parity)"

- Live và harness offline dùng **cùng class** đã sửa: `ExportGateDataset` (OFF-BT), `LiveFeaturePipeline`
  (live + OFF-NEW2), `AltEwIndex`, `MarketBigChangeDetector`. Trong `CP_OFF`, `build/cls` đứng trước jar nên
  class đã biên dịch ghi đè class cùng tên trong jar `eea5adec`.
- Cache Vision có thể vẫn chứa TF/INDEX; việc lọc xảy ra **trước** `updateHistory`/`getTopCoin`/extractor nên
  selector pool, market features, gate input và label all-market đều chỉ thấy universe A1.
- Live: symbol bị loại không vào ticker cache ⇒ `LiveTickerWindow` không có ⇒ settle `prevCount` cũng chỉ đếm
  universe A1 (không lệch `partial`).

## 4. Rủi ro / điều kiện

1. **Phải reset cửa sổ parity** khi deploy: mọi ngày trước thời điểm bật là A0 (có TF/INDEX), không so sánh trực
   tiếp với ngày A1. Cửa sổ promotion v1.1 hiện tại (từ 2026-10-21) phải **đóng sổ**; mở cửa sổ mới từ nến quyết
   định đầu tiên sau restart có `UNIVERSE_A1=1`, và ghi mốc đó vào prereg.
2. File exchangeInfo là ảnh chụp; symbol niêm yết mới sau ảnh chụp sẽ **không** bị phân loại (mặc định crypto).
   Cần refresh file + restart có kiểm soát; không tự gọi API.
3. `contractType/underlyingType` thiếu ⇒ không loại (an toàn cho crypto mới, nhưng TF thiếu nhãn sẽ lọt). Đếm
   `verified=false` chưa được log; nếu cần, bổ sung ở lần sau.
4. Bỏ TF/INDEX làm **đổi** breadth/basket/gate/p15 và do đó đổi quyết định — đây là thay đổi hành vi có chủ đích,
   không phải bug. Không được trộn kết quả A0/A1 trong cùng một bảng verdict.
5. `AltEwIndex` loại thêm TF/INDEX ⇒ cờ X14 có thể đổi (HO2026_TRADFI_AUDIT §4.1: noTFIDX 18 ngày vs 15 ngày
   2026). Trong live, lịch sử ALT_EW đã tích luỹ theo A0 sẽ **không** tự sửa; cần dựng lại state ALT_EW A1
   (replay Vision) trước khi bật, nếu không flag 30 ngày đầu là hỗn hợp.
6. Chưa áp cho sim HO2026 (repo/kernel khác): A1 sim phải dựng universe A1 ở tầng dữ liệu (`PREREG_HO2026_NOTF`
   §7). Lớp này chỉ bảo đảm v1.1 live/replay parity.
7. Chưa deploy, chưa sửa 242, chưa push. Không copy `PrivateConfig`; build dùng stub `STUB_KEY/STUB_SECRET`
   (file bị `.gitignore`, không commit).

## 5. Kiểm chứng

- `mvn -o -Dtest=UniverseA1FilterTest test`: **4/4 PASS** (fixture exchangeInfo, cờ TẮT/BẬT, TF/INDEX/PREMARKET/thiếu trường).
- `mvn -o package`: **BUILD SUCCESS**, **415 test / 0 fail / 0 error / 1 skip** (37 s), jar
  `target/binance-java-sdk-1.2.4.jar` (chưa dùng để deploy).
- Chưa chạy harness end-to-end với `UNIVERSE_A1=1` (không nằm trong phạm vi "chuẩn bị code"); đề xuất một lượt
  R3/CTL trước khi deploy thật.
