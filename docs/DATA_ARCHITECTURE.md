# DATA_ARCHITECTURE — Kiến trúc dữ liệu 242 / 226 (CHUẨN — mọi task/giải pháp follow)

> Nguồn sự thật về "data nào ở đâu, ghi đâu, đọc đâu, chạy ở đâu". Mọi task mới + refactor PHẢI theo file này. Mâu thuẫn với file khác → file này thắng (trừ khi user đổi).
> Chốt: 2026-06-14 (user). Trạng thái: v1 — còn vài điểm chờ user chốt ở §6.

---

## 1. Nguyên lý cốt lõi

1. **242 = SOURCE OF TRUTH cho MỌI dữ liệu MARKET** (realtime + lịch sử). Không có market data "chính chủ" nào sống ngoài 242.
2. **242 PRIVATE**: chỉ **226** kết nối được 242. Kaggle/dev/máy ngoài **KHÔNG** tới 242.
3. **226 = (a) REPLICATE của 242 theo SETNAME, ON-DEMAND** + **(b) kho COMPUTE** (backtest/train/wfo/hpo). 226 KHÔNG sync toàn bộ — chỉ copy set nào cần, khi cần.
4. **226 internet mở** (Kaggle/dev tới được); **226 tài nguyên YẾU** → tránh dồn job nặng.
5. **Kaggle nhiều CPU nhưng chỉ tới 226** → việc chỉ-đụng-226 đẩy Kaggle; việc cần-242 bắt buộc 226.

---

## 2. Phân loại set Aerospike

### 2.1 MARKET — source ở **242** (replicate sang 226 khi train cần)
- `kline_1m_opt` (realtime + historical)
- `kline_15m_btceth`, `kline_4h_btceth`
- `funding_data`
- `open_interest` (+ long/short, taker khi có)
- `price_realtime`
- `basis`/`premiumIndex` (nếu chốt dùng)

### 2.2 COMPUTE — chỉ ở **226** (KHÔNG ghi 242)
- `ai_pred_market` / predict, `predictionSymbol`
- `marketobject` (MarketDataObject dẫn xuất)
- `symbol_lifecycle`
- `gate_return` (label), `gate_features` (A/B), `funding_label`
- `distributed_task` (AerospikeTaskCoordinator), kết quả wfo/hpo

> Quy tắc nhớ nhanh: **dữ liệu THỊ TRƯỜNG → 242 là gốc; dữ liệu TÍNH TOÁN/HUẤN LUYỆN → 226.**

---

## 3. Luồng dữ liệu

1. **LIVE → 242:** `BinanceDataIngestor` + `BinanceOrderTradingManager` chạy trên **242**, ghi realtime thẳng 242 (`kline_1m_opt`, `funding_data`, `open_interest`, `price_realtime`). Forward `kline_15m/4h` (TASK-031) ghi 242.
2. **CÀO LỊCH SỬ → 242:** job cào (Binance API / data.binance.vision) chạy **TRÊN 226** (226 có internet + nối 242) → đích ghi = **242**. Tải rất nặng thì Kaggle tải → 226 tạm → 226 đẩy lên 242 (Kaggle không ghi 242 trực tiếp).
3. **REPLICATE 242→226 (theo setname, on-demand):** trước khi train/backtest, dùng tool replicate copy đúng set MARKET cần từ 242 → 226 (vì Kaggle/dev chỉ đọc 226).
4. **TRAIN/BACKTEST/WFO/HPO → 226:** chạy trên Kaggle/dev/226, đọc MARKET (đã replicate) + COMPUTE từ 226; ghi COMPUTE (features/label/predict/lifecycle...) vào **226**.

---

## 4. Nơi chạy job (suy ra từ kết nối)

| Job đụng tới | Chạy ở đâu |
|---|---|
| GHI 242 (realtime / historical market) | **226** (hoặc 242). KHÔNG Kaggle |
| Chỉ ĐỌC/GHI 226 (train/backtest/compute) | **Kaggle** (ưu tiên, nhiều CPU) hoặc dev/226 |
| Tải internet nặng | **Kaggle** → 226 (→ đẩy 242 nếu là market) |
| Sửa code thuần (không Aerospike nặng) | máy nào cũng được |

**Bẫy chí mạng:** job chạy Kaggle mà code lỡ `getClient242()` → **lỗi/treo** (Kaggle không tới 242). Trước khi launch Kaggle phải chắc job chỉ touch 226.

---

## 5. Hệ quả — điều chỉnh các thành phần hiện tại

- **031 forward `kline_15m/4h`** → ghi **242**. ✅ Đúng nguyên lý (đang làm).
- **009 `Aggregate15m4hBtcEth`** → đang ghi CẢ 226+242 (`getClient226()+getClient242()`). Theo chuẩn: **đích là 242** (source); 226 nhận qua **replicate** khi train cần, KHÔNG ghi thẳng 226 trong job aggregate. (Cần refactor — xem §6.)
- **015 `gate_features`, 024 `funding_label`, 010 `symbol_lifecycle`, 012 `gate_return`** → COMPUTE, ghi **226**. ✅ Đọc market từ 226 (bản replicate). Chạy Kaggle OK miễn KHÔNG ghi 242.
- **CẦN TOOL REPLICATE** `242 → 226` theo setname (chạy trên 226). Hiện CHƯA có → task mới.
- **Market historical** (kline_1m 2020+...) hiện đang nằm ở 226 (cào cũ). Theo chuẩn nó phải có ở **242** (source). Cần xác minh/di trú — xem §6.

---

## 6. ĐÃ CHỐT (2026-06-14, user) — khoá

1. **CHỐT PHƯƠNG ÁN A: 242 giữ TẤT CẢ market kể cả historical sâu.** Căn cứ TASK-032: `kline_1m_opt`@242 = 22.25GB từ ~2021-01 → nay; disk 22.3/50GB (**55% free**), RAM 82% free → 242 ĐÃ ôm full historical và còn nửa ổ. KHÔNG tách historical sang 226. 226 chỉ replicate set market khi train cần (on-demand).
2. **`market_data_object` (marketobject) = COMPUTE → 226** (032 xác nhận chỉ sống ở 226). Đúng §2.2.
3. **⚠️ Backup (repl=1):** 242 replication-factor=1, KHÔNG có bản sao. Set chỉ-sống-242 (`open_interest`, `price_realtime`, `ai_pred`, `funding`) sẽ MẤT nếu hỏng ổ. → 226 replicate các set 242 quan trọng làm **BACKUP** (kiêm nguồn train). Tool: **TASK-034**.
4. **Replicate tool 242→226 theo setname (on-demand):** **TASK-034** — chạy trên 226 (ĐỌC-ONLY 242, ghi 226), copy set chỉ định, lọc theo thời gian nếu cần. Vừa phục vụ train (market ở 226 cho Kaggle/dev) vừa làm backup.
5. **✅ Đã soát + backup (TASK-034 DONE):** live dùng `funding_data`; `funding_data_new` = MỒ CÔI (không code nào ghi/đọc) → không replicate, có thể xoá khỏi 242 sau (user tay). Tool `ReplicateSet242To226` (`cc927e8`) đã đẩy `open_interest`/`price_realtime`/`funding_data` → 226 → repl=1 đã có bản sao backup.

---

## 7. Việc đang chạy có bị ảnh hưởng?

KHÔNG gián đoạn. 015/024/builder-010 trên Kaggle vẫn đọc `kline_1m` historical **đang có sẵn ở 226** → chạy bình thường. Kiến trúc này áp dụng cho thiết kế/refactor TỪ NAY: 009 ghi-đích-242, tool replicate, và mọi job mới chọn nơi ghi/chạy theo §2–§4.
