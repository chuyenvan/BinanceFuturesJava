# DATA_ARCHITECTURE — Kiến trúc dữ liệu (đã tách thành pack `docs/db/`)

> Chi tiết đã chuyển sang **`docs/db/`**. File này giữ làm pointer vì nhiều task cũ trỏ tới.
> Nguồn sự thật giờ ở `db/`. Mâu thuẫn file khác → nhánh db/ thắng (trừ khi user đổi).

- Router + nguyên lý + bảng "job đụng gì → chạy đâu": [db/index](db/index.md)
- 242 = SOURCE market (private, chỉ 226 tới): [db/aerospike-242](db/aerospike-242.md)
- 226 = replicate + compute (open internet): [db/aerospike-226](db/aerospike-226.md)
- redis = order queue live + messaging: [db/redis](db/redis.md)

> Tóm 1 dòng: **242 = SOURCE mọi MARKET (realtime + lịch sử, private); 226 = replicate-theo-setname on-demand + kho COMPUTE (train/backtest/wfo/hpo); Kaggle chỉ tới 226.**
