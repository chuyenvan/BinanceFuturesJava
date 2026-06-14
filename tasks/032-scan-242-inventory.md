# TASK-032: Scan TOÀN DIỆN Aerospike 242 → file log (để phân tích kiến trúc dữ liệu)

- **status:** TODO — chạy NGAY (đọc-only, nhẹ). Phục vụ chốt `docs/DATA_ARCHITECTURE.md` §6 (A/B + replicate).
- **owner:** CCD #1 · **status:** DONE · **updated:** 2026-06-14
- **Vì sao:** cả user lẫn Desktop KHÔNG connect được 242 (private). Chỉ CCD chạy TRÊN 226 mới thấy 242. Cần ảnh chụp đầy đủ 242 thực có gì để quyết kiến trúc (242 đã phình chưa, historical đã ở 242 chưa, set nào cần replicate).

## Chạy ở đâu
**TRÊN 226** (226 connect 242). Đọc-only. Nối/nâng tool `AerospikeStateScan` (`ff579a6`) đã có.

## Lấy TOÀN BỘ thông số (ghi ra file)
### A. Namespace-level (242) — dùng Aerospike `info`/`asinfo` (nhẹ, KHÔNG scan-all)
- Tổng objects, memory used/free, disk used/free, %free, stop-writes, eviction. → biết 242 còn bao nhiêu chỗ (quyết A/B).
- Cấu hình namespace (replication-factor, storage-engine, RAM vs disk).

### B. Liệt kê MỌI set trong 242 (không bỏ sót — kể cả set lạ/compute lẫn vào)
Mỗi set: **tên set · #record (objects) · memory/disk bytes ước tính**. Lấy từ `sets/<ns>` info command (nhẹ, không quét record).

### C. Chi tiết từng set MARKET (sample, KHÔNG quét toàn bộ)
Với mỗi set market (`kline_1m_opt`, `kline_15m_btceth`, `kline_4h_btceth`, `funding_data`, `open_interest`, `price_realtime`, basis nếu có):
- #symbol (số key), range thời gian: ts **cũ nhất → mới nhất** (lấy vài key đại diện BTC/ETH + 2-3 alt, đọc min/max ts trong value).
- Kích thước trung bình/record + tổng ước tính.
- Sample 1 record: schema bin (cấu trúc value) — để xác nhận format.
- Đặc biệt: `kline_15m/4h_btceth` ts mới nhất (031 forward đã tiến chưa); `funding_data` ts mới nhất (019 refresh tươi chưa); `open_interest` #record + range (forward 242 ghi gì); `kline_1m_opt` range (historical 242 sâu tới đâu — 2020? hay chỉ gần đây).

### D. Đối chiếu nhanh với 226
- Cùng các set đó trên 226 (#record, range) — để thấy 242 vs 226 lệch gì (cái nào chỉ-242, chỉ-226, cả hai).

## Output
- File **`docs/aerospike_242_inventory.md`**: bảng A (namespace stats) + B (mọi set + #record + bytes) + C (market set chi tiết ts-range/schema) + D (so 226). Số liệu thật, có timestamp scan.
- → Desktop + user đọc, phân tích để chốt DATA_ARCHITECTURE §6.

## An toàn
- Đọc-only tuyệt đối. Ưu tiên `info`/`asinfo` (metadata, nhẹ) thay vì scan toàn bộ record. Sample chỉ vài key/set. KHÔNG ghi, KHÔNG xóa. Chạy nhẹ, không đụng job live trên 242.

## Acceptance
- [x] File inventory đủ A+B+C+D, số thật + timestamp → `docs/aerospike_242_inventory.md` (đo 2026-06-14 12:35).
- [x] Trả lời được: 242 dung lượng (disk 50GB, **55% free**; RAM 82% free); historical 1m@242 sâu **~2021-01** (latest live 06-14); set chỉ-242 (open_interest/ai_pred_1m/price_realtime/funding_data_new) vs chỉ-226 (funding_pred_v5 5.44GB/market_data_object/ai_pred_basket_v2/kline_15m_opt). → đủ chốt A/B + replicate.

## (Code điền)
- **Tool:** `ai_ml/validation/data/Aerospike242Inventory.java` (`eddb8e5`), đọc-only qua `Info.request` (namespace/sets) + sample key (range). Chạy TRÊN 226 (scp class compile-sẵn vào `.recon_classes`, java 11).
- **A namespace 242:** 2.91M obj; RAM 178MB/1GB (82% free); disk 22.33GB/50GB (55% free, 53% avail); repl-factor=1; storage=device; stop-writes=false. (226: 11.5M obj, RAM **chỉ 31% free** ⚠️.)
- **B sets 242:** 15 set; `kline_1m_opt` 22.25GB (2.87M), `open_interest` 21.7MB, `funding_data` 18.5MB, `funding_data_new` 17.8MB ⚠️, `kline_15m_btceth` 12.3MB, `ai_pred_1m` 7.7MB, `kline_4h_btceth` 902KB, `price_realtime` 53KB, còn lại 0.
- **C market 242:** funding 5974đ tới 06-14 07:00 (tươi); OI BTC 3081đ ~30 ngày tới 06-14 12:30; kline 15m/4h 66 tháng tới 06-07 (forward chưa); kline_1m_opt latest 06-14 (226 lag 06-07). earliest 1m **~2021-01** (probe-midnight báo 2022 nhưng 15m-aggregate chứng minh 2021-01).
- **D so 226:** chỉ-242 = open_interest/ai_pred_1m/price_realtime/funding_data_new; chỉ-226 = funding_pred_1m_v5(5.44GB)/ai_pred_market_full_basket_v2/market_data_object/kline_15m_opt; cả hai (replicate) = kline_1m_opt/kline_15m_4h_btceth/funding_data/symbol_mapper.
- **PHÁT HIỆN cần soát (ngoài 032):** (1) `funding_data_new` = set funding THỨ HAI trên 242 (nghi di sản/“mỗi nơi một kiểu”). (2) `open_interest` mới chỉ-242 → train gate (013/018) cần thì phải replicate 226. (3) repl-factor=1 trên live 242 → rủi ro mất-node, nên backup.
