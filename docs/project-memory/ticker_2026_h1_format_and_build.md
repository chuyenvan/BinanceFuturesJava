# Ticker 1m 2026-H1: đặc tả format + pipeline build từ Binance Vision

Ngày: 2026-08-08. Mục tiêu: bổ sung ticker 1 phút cho **2026-01-01 → 2026-07-01** vào hệ WFO,
cùng format với `chuyendinh/hpo-ticker-daily` (1826 file 2021→2025-12-31).

## 1. Format file — ĐÃ XÁC ĐỊNH BẰNG CÁCH ĐỌC FILE THẬT

Tải `ticker_20251231.bin` (43.278.020 byte) từ dataset và deserialize bằng chính jar dự án:

| Thuộc tính | Giá trị thật |
|---|---|
| Tên file | `ticker_YYYYMMDD.bin` (KHÔNG nén; loader cũng chấp nhận `.bin.gz`) |
| Nội dung | Java `ObjectOutputStream.writeObject` của `TreeMap<Long, HashMap<String, KlineObjectSimple>>` |
| Key ngoài | epoch **ms**, mốc mở nến phút, đúng **1440** key/ngày, bước 60000 |
| Biên ngày | **UTC midnight** (20251231 → firstKey 1767139200000 = 2025-12-31T00:00Z, lastKey 1767225540000) |
| Key trong | symbol **CÓ hậu tố USDT** (`BTCUSDT`, `1000PEPEUSDT`, `0GUSDT`, `42USDT`) |
| Giá trị | `KlineObjectSimple`: `Long startTime`, `float priceOpen/maxPrice/minPrice/priceClose/totalUsdt` |
| serialVersionUID | 5255767105331914524 (tự sinh → **bắt buộc dùng class từ jar dự án**, không tự khai lại) |
| `totalUsdt` | = cột **7** của kline Binance (quote asset volume), khớp `KlineObjectSimple.convertString2Kline` |

Hệ quả: **không thể sinh file này bằng Python thuần**. Phải chạy Java với
`binance-java-sdk-*-shaded.jar` trên classpath.

## 2. Nguồn dữ liệu & bằng chứng parity

Nguồn: `data.binance.vision`, `data/futures/um/monthly/klines/<SYM>/1m/<SYM>-1m-YYYY-MM.zip`
(fallback `daily/` khi thiếu monthly), có verify SHA-256 qua file `.CHECKSUM`.

**Kiểm chứng quyết định**: dựng lại `ticker_20251231.bin` từ Binance Vision rồi so **từng ô**
với file thật của dataset:

```
universe REF=590  NEW=590   chỉ-có-ở-REF=0   chỉ-có-ở-NEW=0
ô so sánh = 847.995 | khớp-bit OHLC = 847.995 | lệch = 0
khớp-bit totalUsdt = 847.995 | lệch = 0
ô REF có mà NEW thiếu = 0 | ô NEW có mà REF thiếu = 0
```

⇒ Binance Vision tái tạo **chính xác 100%** dữ liệu Aerospike đang dùng cho 2021-2025.

## 3. Quy tắc universe (3 tầng lọc) — điểm dễ gây lỗi WFO nhất

`data.binance.vision` có **832** symbol `*USDT` (futures/um, bỏ delivery). Không dùng thẳng con số này:

1. **Chặn theo `symbol_map`** (`symbol_map.csv` trong `chuyendinh/funding-oi-percoin`, 863 symbol, id 1..863).
   Loại 9 symbol không có trong map: `1000BTTCUSDT, BTCSTUSDT, COCOSUSDT, LENDUSDT, MBLUSDT,
   SNTUSDT, STPTUSDT` + 2 symbol tên tiếng Trung.
   **Lý do kỹ thuật (BẮT BUỘC):** `SimpleSymbolMapper.getId(symbolLạ)` cấp id mới rồi gọi
   `DataManagerAerospikeFloatSim.saveSymbolMapping()` — trên Kaggle `TICKER_SOURCE=file` KHÔNG có
   Aerospike ⇒ lỗi/treo. Thêm nữa `KaggleDataLoader.loadDailyTickersShort()` ghi vào
   `klineArray[symbolId]` kích thước **1000** ⇒ id > 999 là `ArrayIndexOutOfBoundsException`.
   (Hiện max id trong map = 863 → còn an toàn.)

2. **Liên tục với lịch sử**: giữ symbol có trong `ticker_20251231.bin` (590) **cộng** symbol mới list
   sau 2025-12 (222, phát hiện bằng: không có file monthly 2025-12). Loại **20** symbol có thật
   trước 2026 nhưng pipeline Aerospike chưa từng nạp (`BTCDOMUSDT, USDCUSDT, CVCUSDT, CTKUSDT,
   CVXUSDT, SLPUSDT` + 14 coin ghost) — nếu giữ, WFO sẽ đột ngột thấy "coin lạ" từ 2026-01-01.

   → Universe dùng để build: **806 symbol**.

3. **Ghost chỉ GHI NHẬN, KHÔNG loại.** Coin delist nhưng Binance Vision vẫn phát 1440 nến phẳng
   (`o=h=l=c` bất biến, quote-volume = 0). Đã thử loại → tụt 590 xuống 532 symbol và **phá parity**:
   bộ 2021-2025 VẪN GIỮ các coin phẳng này (FTMUSDT, AGIXUSDT, BALUSDT, BAKEUSDT…, 58 coin-ngày
   riêng ngày 2025-12-31). Vì vậy chỉ liệt kê trong báo cáo để selector/gate tự quyết.

⚠️ Trong 222 symbol mới list 2026 có nhiều **cổ phiếu/hàng hoá token hoá**: `AAPLUSDT, NVDAUSDT,
TSLAUSDT, MSFTUSDT, SPYUSDT, QQQUSDT, XAGUSDT, XPTUSDT, NATGASUSDT, COPPERUSDT, HK0700USDT`…
Chúng nằm trong `symbol_map` nên đi qua được 2 tầng lọc trên. Model 2021-2025 chưa từng thấy loại
tài sản này và chúng **không giao dịch 24/7** → sẽ hiện ra ở bảng "coin thiếu nến". Cần quyết định
riêng có cho vào selector/gate hay không.

## 4. Artefact

| Thứ | Vị trí |
|---|---|
| Builder + validator (Java) | `C:\Users\pc\t2026\BuildTickerDaily.java` |
| So sánh parity 2 file .bin | `C:\Users\pc\t2026\CompareTicker.java` |
| Kernel wrapper | `C:\Users\pc\ticker2026-kernel\run.py` + `kernel-metadata.json` |
| Dataset code | `chuyendinh/ticker2026-code` (`ticker2026.jar`, `symbol_map.csv`, source) |
| Kernel | `chuyendinh/ticker2026-build` (private, `enable_internet: true`) |
| Dataset kết quả | `chuyendinh/hpo-ticker-2026` (RIÊNG — **không** đụng `hpo-ticker-daily`) |

**Bẫy Kaggle đã gặp:** dataset Kaggle **cắt bỏ ký tự `$`** khỏi tên file → `BuildTickerDaily$1.class`
biến thành `BuildTickerDaily1.class` → `NoClassDefFoundError`. Phải đóng gói class vào **JAR**.

**Cách WFO nạp:** kernel WFO khai BOTH dataset trong `dataset_sources`
(`chuyendinh/hpo-ticker-daily` + `chuyendinh/hpo-ticker-2026`), symlink/gộp về `kaggle_data_hpo/`.
Tuyệt đối **không** `kaggle datasets version` lên `hpo-ticker-daily` (thay thế toàn bộ 1826 file).
