# MARKETDATA_REGISTRY — dump Aerospike `market_data_object` → Kaggle

Ngày: **2026-10-14 (GMT+7)**. Món "còn nợ (i)" trong `docs/result/RESULT_BD_CHAIN_CHAIN2.md §4`
("dump Aerospike market_data read-only → dataset Kaggle (parity f=0)").

## Dataset
- **Slug (PRIVATE)**: `chuyendinh/vz-marketdata`
- **URL**: https://www.kaggle.com/datasets/chuyendinh/vz-marketdata
- title `vz-marketdata`, license `CC0-1.0`, files: `market.bin`, `market.parquet`.

## Nguồn (đã kiểm, không đoán)
- Container docker **`aerospike-wfo`** (image `aerospike/aerospike-server:latest`), network **host**,
  Aerospike ở **`127.0.0.1:3222`**.
- namespace **`test`**, set **`market_data_object`**; asinfo: `objects=2947861`, `data_used_bytes=330051840`.
- **Khóa đọc = bin `time`** (epoch ms), KHÔNG phải user_key: đúng theo
  `DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike()` → `record.getLong("time")` rồi
  `results.put(timestamp, …)` vào `TreeMap<Long,…>`; `WfoDataset` (dòng 66) dùng chính hàm này rồi `writeMarket`.
- `data` bin (12 byte) = 3 float **BIG-ENDIAN** = `(down, up, down15)` =
  `(rateDownAvg, rateUpAvg, rateDown15MAvg)` (khớp `MarketDataObject.decodeMarketDataFromBinary`).
- `market.bin` đúng format `WfoDataset.writeMarket`: `writeInt(count)` rồi mỗi dòng
  `writeLong(ts)`,`writeFloat(down)`,`writeFloat(up)`,`writeFloat(down15)` — tất cả BIG-ENDIAN, ts tăng dần.

## Số liệu dump
| mục | giá trị |
|---|---|
| Object scan được | **2.947.861** (= asinfo ✓) |
| Dòng ghi ra (`market.bin`/parquet, unique ts) | **2.867.134** |
| Dải ts (GMT+7) | **2021-01-01 07:00 → 2026-08-13 15:12** |
| ts tăng nghiêm ngặt | true (`n_non_increasing=0`) |
| NaN | 0 |
| `market.bin` | **57.342.684 B** |
| `market.parquet` | **45.268.888 B** |
| sha256 `market.bin` | `0e5af868c958147498f897dffc404cb888f3e91b4cda5d11953ae36f709f40d3` |
| sha256 `market.parquet` | `5a242672f67ce0f1f97441e30a11b50c04f5c6a79dffa197a0a3664081b0ed50` |
| Round-trip Kaggle | sha256 tải về **==** local (cả 2 file) ✓ |

Spot-check (đọc lại trực tiếp `get(('test','market_data_object',key))`, so với parquet) — 3/3 khớp:
`20230924-0911`, `20250919-1847`, `20240707-0554` (float bit-exact, `time` bin == ts parquet).

## Sai khác & cảnh báo (BẮT BUỘC đọc)
- **Lệch số dòng**: 2.947.861 object → **2.867.134 dòng** (−80.727) vì bin `time` **trùng giữa nhiều
  record**; Java `TreeMap<Long,…>` gộp lại (bản ghi scan sau thắng). Dump tất định: trong 1 phút ưu tiên
  record **CÓ user_key**, rồi `(down,up,down15)`.
- **80.727** phút trùng; trong đó **2.350** phút có `data` **KHÁC nhau** giữa các bản ghi (xung đột) ⇒ với
  các phút này thứ tự scan của Java ảnh hưởng kết quả (không tất định). Ví dụ trong `market_dump_summary.json`.
- **6.787** record **không có user_key** (`None`) — vẫn đủ `time`+`data` nên vẫn dump được (dùng `time`).
- **86.584** record có `parse(user_key) != bin time` (di chứng lỗi format key, xem fix HO4-P1 trong
  `DataManagerAerospikeFloatSim.saveMarketDataBatch`).
- `WfoDataset` còn gọi `HoldoutSeal.trimMap(mkt)` để **cắt bỏ ts ≥ 2026-01-01** trước `writeMarket`. Dump này
  là **TOÀN BỘ store** (chưa cắt seal) — khi so parity phải áp cùng seal cho cả hai phía.

## Tái lập
```bash
git -C ~/src/BinanceFuturesJava worktree add ~/claude_master/mktdump_wt -b research/mktdump origin/module
python3 ~/claude_master/mktdump_wt/research/data/marketdump/export_market_aerospike.py --out-dir ~/marketdump
# READ-ONLY (chỉ scan/get); tự upload Kaggle private + chờ ready + tải ngược so sha256.
# --skip-upload để chỉ dump; --skip-download-verify để bỏ round-trip.
```
Log: `~/marketdump/logs/run.log` + `~/marketdump/logs/export.log`; tóm tắt máy đọc: `~/marketdump/market_dump_summary.json`.

**Kaggle CLI quirks (1.6.17, server 2.2.2):** `datasets status` có thể trả 403 thoáng qua ngay sau khi tạo
(thử lại là được); tải **cả** dataset đôi khi 404 `No gcs url found` → tải từng file bằng `-f <name>`.
