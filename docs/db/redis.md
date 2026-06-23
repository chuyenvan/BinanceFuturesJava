# db/redis — Order queue live + messaging

> Đọc cùng [db/index](index.md).

- `redis/` (Jedis cluster) = order queue live + messaging. Config đọc từ `redis.config` ở CWD (`redis/RedisConst.java`, static-init).
- Chỉ liên quan LIVE/trading. Kaggle KHÔNG đụng Redis.
- ⛔ KHÔNG kill Redis (xem [CORE](../CORE.md)).
