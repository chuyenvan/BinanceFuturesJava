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

## 5. RSS timeline (2h, mau ~2-5')

| Moc | Gio | RSS (MiB) | GATE (luy ke) | OOM |
|---|---|---|---|---|
| 0' | 14:59 | 2874 | 2 | 0 |
| ~7' | 15:05 | 3291 | 7 | 0 |
| 15' | 15:14 | 3319 | 17 | 0 |
| 30' | 15:27 | 3321 | 30 | 0 |
| 45' | 15:44 | 3324 | 47 | 0 |
| 60' | 15:57 | 3322 | 60 | 0 |
| 65' | 16:03 | 3630 | 66 | 0 |
| 75' | 16:12 | 3635 | 75 | 0 |
| 90' | 16:27 | 3635 | 90 | 0 |
| 105' | 16:42 | 3636 | 105 | 0 |
| **120'** | **16:58** | **3637** | **121** | **0** |

**Doc dien:** 2 lan tang bac thang (2874 -> ~3320 tai ~7'; ~3322 -> ~3630 tai 65'), sau moi lan **phang** (khong tang don dieu).
RSS dinh **3637 MiB** < `-Xmx4g` (4096 MiB), bien an toan ~450 MiB.
So sanh: ban cu (legacy) dinh **~4,4-5,0 GB > 4g => OOM**; ban cu dang chay truoc restart RSS ~3096 MiB va da co OOM.

## 6. Canh du 2h (14:57:49 -> 16:58)

| Tieu chi | Ket qua | Ket luan |
|---|---|---|
| `OutOfMemoryError` | **0** | DAT |
| `[OI-LIVE] reload nền lỗi` (retry-storm) | **0** | DAT |
| RSS tang don dieu | **KHONG** (2 bac thang roi phang) | DAT |
| RSS dinh | 3637 MiB < 4096 | DAT |
| `[OI-LIVE] inplace` | **3** (cold-load 14:58 + refresh 15:32 + refresh 16:32) | DAT |
| `[GATE]` | **121** dong / 14:59:01 -> 16:58:06 (~100% so phut, >= 90%) | DAT |
| `topk=16` trong `[GATE]` | 121/121 | DAT |
| `[S1] warm-up CHUA DU` | **0** | DAT |
| Lenh that | **0** (SHADOW_NO_PUSH=true) | DAT |
| `systemctl is-active` | active (MainPID 2201049) | DAT |

## 7. KET LUAN: **PASS**

Fix `OI_LIVE_REFRESH_MODE=inplace` giu OI reader trong bien (cat 24h + nap tung lo + bound RAM):
qua 2h lien tuc **0 OOM**, RSS phang ~3,6 GB, `[GATE]` giu nhịp 1 phut (~100%), TOPK=16 dung.
Config R4-1M (TOPK=16, LIVE_ENTRY_GRID_MIN=1, ENTRY_CASCADE=0) chay on dinh tren Oracle PAPER.
**KHONG rollback.** Giu nguyen de chuyen sang 242 theo yeu cau owner.

### Rollback (neu can)
```bash
cd /home/ubuntu/shadow_c3/app
cp -p target/binance-java-sdk-1.2.4.jar.bak_20260930_145728 target/binance-java-sdk-1.2.4.jar
cp -p conf/env.sh.bak_20260930_145728 conf/env.sh
sudo systemctl restart shadow-c3   # xac nhan SELECTOR_RANK_TOPK=8 + active
```

