# Aerospike 242 + 226 Inventory (TASK-032)

> Đo **2026-06-14 12:35 GMT+7**, chạy `Aerospike242Inventory` (`eddb8e5`, đọc-only, qua `Info.request` + sample key) **TRÊN 226** (226 thấy cả 242). Namespace = `ticker`. Phục vụ chốt `docs/DATA_ARCHITECTURE.md §6` (A/B + replicate).

## A. Namespace stats

| Chỉ số | **242-LIVE** | **226-BACKTEST** |
|---|---|---|
| objects | 2,914,983 | 11,512,403 |
| memory dùng / cấp | 177.9 MB / 1.00 GB (**82.6% free**) | 702.7 MB / 1.00 GB (**31.4% free** ⚠️) |
| disk (device) total | 50.00 GB | 60.00 GB |
| disk used | 22.33 GB | 29.31 GB |
| device_free_pct / avail | 55% / 53% | 51% / 48% |
| stop-writes | false | false |
| replication-factor | 1 | 1 |
| storage-engine | device | device |

**Đọc nhanh:** 242 còn RỘNG (disk 55% free ≈ 27.7GB trống, RAM 82% free). 226 RAM index **chỉ còn 31% free** — cần để mắt khi thêm set lớn (index RAM ~ số object; 226 có 11.5M obj vì gánh train/pred). replication-factor=1 cả hai (KHÔNG có bản sao trong-cụm → mất node = mất data; 242 là live nên đây là rủi ro, cân nhắc backup/replicate ngoài).

## B. Sets

### 242-LIVE (15 set)
| set | objects | disk |
|---|---|---|
| `kline_1m_opt` | 2,865,898 | **22.25 GB** |
| `open_interest` | 622 | 21.73 MB |
| `funding_data` | 754 | 18.54 MB |
| `funding_data_new` | 638 | 17.82 MB |
| `kline_15m_btceth` | 132 | 12.29 MB |
| `ai_pred_1m` | 46,128 | 7.73 MB |
| `kline_4h_btceth` | 132 | 902 KB |
| `price_realtime` | 678 | 53 KB |
| `symbol_mapper` | 1 | 10 KB |
| `dca_pred_1m`, `hpo_queue`, `hpo_tasks`, `funding_tasks_dist_v1`, `funding_task_dist_minute`, `funding_tasks_monthly_v1` | 0 | 0 |

### 226-BACKTEST (set có data; bỏ qua đống 0-object)
| set | objects | disk |
|---|---|---|
| `kline_1m_opt` | 2,855,553 | **22.07 GB** |
| `funding_pred_1m_v5` | 2,827,087 | **5.44 GB** |
| `ai_pred_market_full_basket_v2` | 2,819,841 | 516 MB |
| `market_data_object` | 2,819,802 | 301 MB |
| `kline_15m_opt` | 189,038 | 1006 MB |
| `funding_data` | 729 | 18.36 MB |
| `kline_15m_btceth` | 132 | 12.29 MB |
| `kline_4h_btceth` | 132 | 902 KB |
| `funding_tasks_monthly_v2` | 66 | 8 KB · `funding_file_locks` 22 · `symbol_mapper` 1 |

(Nhiều set `hpo_*`, `funding_pred_1m_v1..v4`, `ai_pred_market*`, `rag_*`, `cache_*` = 0 object — version cũ/scratch.)

## C. Market set chi tiết (range thật)

| set | host | symbol | #điểm/nến | range (GMT+7) |
|---|---|---|---|---|
| `funding_data` | 242 | BTC/ETH | 5974 | 2021-01-01 07:00 → **2026-06-14 07:00** (tươi) |
| `funding_data` | 226 | BTC/ETH | 5954 | 2021-01-01 07:00 → 2026-06-07 15:00 (snapshot) |
| `open_interest` | 242 | BTC | 3081 | **2026-05-13 → 2026-06-14 12:30** (~30 ngày, forward poll) |
| `open_interest` | 226 | — | — | **KHÔNG có** (chỉ-242) |
| `kline_15m_btceth` | 242 & 226 | BTC | 190,273 (66 tháng) | 2021-01-01 07:00 → **2026-06-07 07:45** (đứng — forward 031 chưa deploy) |
| `kline_4h_btceth` | 242 & 226 | BTC | 11,877 (66 tháng) | 2021-01-01 07:00 → 2026-06-07 03:00 |
| `price_realtime` | 242 | BTC | bins=`[price, ts]` | (snapshot giá hiện tại) |
| `kline_1m_opt` | 242 | — | 2,865,898 obj | earliest **~2021-01** (xem ⚠️) → **latest 2026-06-14** (live) |
| `kline_1m_opt` | 226 | — | 2,855,553 obj | earliest ~2021-01 → latest **2026-06-07** (synced, lag 7 ngày) |

⚠️ **kline_1m_opt earliest:** probe heuristic (key `YYYY0101-0000`) báo 2022-01, NHƯNG aggregate 15m/4h (đọc 1m) có nến từ **2021-01-01 07:00** ⇒ 1m thực có từ **~2021-01** (record phút 00:00 ngày 1/1 có thể khuyết nên probe-nửa-đêm trượt). Muốn mốc 1m chính xác cần scan có chủ đích — KHÔNG quét ở đây (nặng).

## D. Đối chiếu 242 vs 226 (set có data)

| set | 242 | 226 | thuộc về |
|---|---|---|---|
| `kline_1m_opt` | 2.87M | 2.86M | **cả hai** (242 live tới 06-14; 226 synced tới 06-07) |
| `kline_15m_btceth` / `kline_4h_btceth` | 132 / 132 | 132 / 132 | **cả hai** (historical replicate khớp ✓) |
| `funding_data` | 754 | 729 | **cả hai** (242 tươi hơn) |
| `price_realtime` | 678 | 0 | thực chất **chỉ-242** (live) |
| `symbol_mapper` | 1 | 1 | cả hai |
| `open_interest` | 622 | — | **CHỈ-242** (forward poll 007-C ghi 242; 226 chưa có) |
| `ai_pred_1m` | 46,128 | — | **CHỈ-242** (pred live) |
| `funding_data_new` | 638 | — | **CHỈ-242** ⚠️ (xem dưới) |
| `funding_pred_1m_v5` | — | 2.83M (5.44GB) | **CHỈ-226** (train/serve pred) |
| `ai_pred_market_full_basket_v2` | — | 2.82M (516MB) | **CHỈ-226** |
| `market_data_object` | — | 2.82M (301MB) | **CHỈ-226** (feature backtest) |
| `kline_15m_opt` | — | 189,038 (1GB) | **CHỈ-226** |

## Kết luận cho A/B + replicate (DATA_ARCHITECTURE §6)
1. **242 còn dư địa lớn** (disk 55% free ≈ 28GB, RAM 82% free) — thêm set market vừa phải OK. 226 RAM chỉ 31% free → tránh dồn thêm set nhiều-object lên 226.
2. **Historical KÉO sâu tới 2021-01** trên cả 1m / 15m / 4h / funding (242 + 226). 242 đã có đủ historical gate cần (15m/4h tới 06-07) — chỉ thiếu **forward 06-07→nay** (TASK-031 + chạy lại Aggregate trước golive).
3. **Chỉ-242 (live-only):** `open_interest`, `ai_pred_1m`, `price_realtime`, `funding_data_new`. **Chỉ-226 (train-only):** `funding_pred_1m_v5`, `ai_pred_market_full_basket_v2`, `market_data_object`, `kline_15m_opt`. ⇒ ranh giới live/train khá rõ; set CẦN cả hai (gate đọc lúc serve@242 + train@226): `kline_1m_opt`, `kline_15m/4h_btceth`, `funding_data` — đang replicate đúng. **`open_interest` mới chỉ ở 242** → nếu train gate dùng OI (013/018) phải replicate 242→226 hoặc backfill 226.
4. ⚠️ **`funding_data_new` (638 obj, chỉ-242)** = set funding THỨ HAI bên cạnh `funding_data` (754). Nghi "mỗi nơi một kiểu" / di sản ingest — **cần soát**: ai ghi, gate/live đọc set nào, có nên gộp/bỏ. (Ngoài phạm vi 032; báo để Desktop xử.)
5. **replication-factor=1** trên 242 (live) → không có bản sao trong-cụm. Rủi ro mất-node = mất data live; cân nhắc backup định kỳ 242→226 hoặc snapshot.
