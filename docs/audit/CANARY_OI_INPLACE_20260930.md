# CANARY OI-INPLACE + R4 1' — shadow-c3 (Oracle, PAPER) — 2026-09-30

**Pham vi:** CHI `shadow-c3` tren Oracle `/home/ubuntu`. KHONG cham 242 / production / ONNX / LIVE secret.
**Owner duyet:** 2026-09-30 ("chay verify tren oracle ok roi lam tren 242").
**Muc tieu:** verify FIX OOM OI-LIVE (`OI_LIVE_REFRESH_MODE=inplace`) + config R4-1M (TOPK=16, GRID_MIN=1, CASCADE=0)
chay that tren box Oracle PAPER truoc khi ap len 242.

## 1. Trang thai TRUOC

| Muc | Gia tri |
|---|---|
| `systemctl is-active shadow-c3` | active |
| MainPID (truoc) | 2193330 (start 2026-09-30 12:04:46) |
| Jar dang chay | `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar` (99.716.708 B, 30/09 12:04) |
| sha256 jar cu | `78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71` |
| `JAVA_OPTS` | `-server -Xms1g -Xmx4g ...` (GIU NGUYEN, khong tang) |
| env cu | `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `SELECTOR_RANK_TOPK=8` |
| VmRSS/VmHWM truoc restart | 3.170.580 kB (~3.02 GiB) |

Nguyen nhan da biet (truoc fix): reader OI khong cat cua so 24h + double-buffer => peak ~4,4-5,0 GB > `-Xmx4g`
=> OOM + retry-storm 10s. `docs/audit/FIX_OOM_OI_LIVE.md` (`59521a56`), bench `docs/audit/FIX_OOM_OI_LIVE_BENCH.md` (`0f783e36`).

## 2. Backup (BAT BUOC)

`TS=20260930_145728`

| File | Duong dan |
|---|---|
| Jar cu | `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar.bak_20260930_145728` |
| env.sh cu | `/home/ubuntu/shadow_c3/app/conf/env.sh.bak_20260930_145728` |

**sha256 jar cu (rollback target):** `78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71`

## 3. Deploy

1. Copy jar moi: `/home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar`
   -> `shadow_c3/app/target/binance-java-sdk-1.2.4.jar`.
   **sha256 sau copy:** `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15` (khop nguon).
2. Sua `conf/env.sh` (chi them/doi key; GIU `SHADOW_NO_PUSH=true` + `LIVE_PROFILE=c3_shadow`).

### env diff (chi 4 dong)

```diff
- export SELECTOR_RANK_TOPK=8
+ export SELECTOR_RANK_TOPK=16
+ export LIVE_ENTRY_GRID_MIN=1
+ export ENTRY_CASCADE=0
+ export OI_LIVE_REFRESH_MODE=inplace
```

3. Restart bang co che chuan: `sudo systemctl restart shadow-c3` (KHONG `kill -9`).
   - `is-active` = **active**; **MainPID moi = 2201049** (start 2026-09-30 14:57:49).
4. Xac nhan env cua tien trinh dang chay (`/proc/<pid>/environ`):

```
SELECTOR_RANK_TOPK=16
LIVE_ENTRY_GRID_MIN=1
ENTRY_CASCADE=0
OI_LIVE_REFRESH_MODE=inplace
SHADOW_NO_PUSH=true
LIVE_PROFILE=c3_shadow
```

## 4. Canh 15-30' dau — TAT CA DAT

| Tieu chi | Ket qua |
|---|---|
| `[OI-LIVE] ... inplace` | **CO** — `14:58:31.171 [OI-LIVE] inplace cold-load 640 coin ...` |
| `reload nền lỗi` (retry-storm) | **0** (truoc day lap OOM moi ~2') |
| Header `[R4-1M] LIVE_ENTRY_GRID_MIN=1` | **CO** — `14:57:55.709 [R4-1M] LIVE_ENTRY_GRID_MIN=1 => SELECTOR quet moi 1 phut` |
| `[GATE]` moi phut (topk=16) | **CO** |
| `OutOfMemoryError` | **0** |
| `[S1] warm-up CHUA DU` | **0** |

## 5. RSS timeline (0/15/30/60/120')

(xem bang ben duoi — cap nhat trong qua trinh canh)

## 6. Ket luan

(cap nhat sau khi du 2h)
