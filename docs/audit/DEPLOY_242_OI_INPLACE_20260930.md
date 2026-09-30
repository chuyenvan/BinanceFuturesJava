# DEPLOY 242 — FIX OOM OI-LIVE (`inplace`) + config R4 1' — PAPER — 2026-09-30

**Pham vi:** CHI host **242** (`3stech.vn`, `103.157.218.242`, app `/home/chuyennd/java/v_t_m`), PAPER/shadow.
KHONG cham box khac, KHONG doi `SHADOW_NO_PUSH`, KHONG bat lenh that, KHONG cham 2026/HOLDOUT.
**Tien de:** canary `shadow-c3` (Oracle) **PASS** `docs/audit/CANARY_OI_INPLACE_20260930.md` (`da56927a` deploy · `f24b51c4` ket qua).
**Fix:** `OI_LIVE_REFRESH_MODE=inplace` (`docs/audit/FIX_OOM_OI_LIVE.md`, `59521a56`) + bench (`0f783e36`).
**Owner duyet:** 2026-09-30 *"ok chay verify tren oracle ok roi lam tren 242"*.

## 0. Inspect (read-only) — co che restart CHUAN

| Muc | Gia tri |
|---|---|
| Restart | `cd /home/chuyennd/java/v_t_m && bin/daemon.sh (start\|stop\|restart)` — **KHONG systemd** |
| `bin/daemon.sh` | `stop`=`kill` (SIGTERM) + doi toi 60s roi moi `kill -9`; `start`=`nohup bin/start.sh > logs/nohup.out &`; PID file `run/<MAIN_CLASS>.pid` |
| `bin/start.sh` | `java -server -Xms5g -Xmx5g -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager` (heap **GIU NGUYEN**, khong tang) |
| `conf/env.sh` (truoc) | `LIVE_PROFILE=c3_shadow` · `SHADOW_NO_PUSH=true` · `PAPER_EQUITY=35000` · `SELECTOR_RANK_TOPK=8` ⇒ **PAPER xac nhan** |
| Jar dang chay (truoc) | `target/binance-java-sdk-1.2.4.jar` sha256 `78387f30…` |
| Process | `BinanceOrderTradingManager` PID 26568 (RSS ~1.76 GB) + `BinanceDataIngestor` PID 25042 tu **cwd khac** (`/home/chuyennd/java/collectData`) => doi jar cua `v_t_m` KHONG anh huong ingestor |

Nhan dinh: box 8 GB (`Mem total 7821`) — launcher chuan 242 la `-Xms5g -Xmx5g` (xem `DEPLOY_CADENCE_V2_242_20260928.md` §5: RSS ~4.7 GB, tung co dmesg OOM-kill java rss ~5.5 GB).

## 1. Backup (BAT BUOC) — `TS=20260930_170043`

| File | Duong dan |
|---|---|
| Jar cu | `target/binance-java-sdk-1.2.4.jar.bak_20260930_170043` |
| env.sh cu | `conf/env.sh.bak_20260930_170043` |

**sha256 jar cu (rollback target):** `78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71`
sha256 env.sh cu: `f91ffefe17e982a0ad5b32229b16c3333961cb2997a1f94fbc567a9c4f4c1e6e`

## 2. Deploy

1. scp jar moi `c389b4be…` -> `target/binance-java-sdk-1.2.4.jar.new`; verify sha256 = `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15` (khop nguon), roi `mv` (atomic) -> `target/binance-java-sdk-1.2.4.jar`.
   **sha256 sau copy (dang chay):** `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15`
2. Sua `conf/env.sh` (chi them/doi key; GIU `SHADOW_NO_PUSH=true` + `LIVE_PROFILE=c3_shadow` + `PAPER_EQUITY=35000`):

```diff
- export SELECTOR_RANK_TOPK=8
+ export SELECTOR_RANK_TOPK=16
+ export LIVE_ENTRY_GRID_MIN=1
+ export ENTRY_CASCADE=0
+ export OI_LIVE_REFRESH_MODE=inplace
```

3. Restart bang co che CHUAN: `bin/daemon.sh stop` -> `mv` jar -> `bin/daemon.sh start`.
   - `stop` graceful (SIGTERM, khong `kill -9`), **PID moi = 4064** (start 2026-09-30 17:01:07).
4. Env cua tien trinh dang chay (`/proc/4064/environ`, chi key non-secret):

```
LIVE_PROFILE=c3_shadow
SHADOW_NO_PUSH=true
PAPER_EQUITY=35000
SELECTOR_RANK_TOPK=16
LIVE_ENTRY_GRID_MIN=1
ENTRY_CASCADE=0
OI_LIVE_REFRESH_MODE=inplace
```

## 3. Canh 15-30' dau (17:01:07 -> 17:30) — TAT CA DAT

| Tieu chi | Ket qua |
|---|---|
| `[OI-LIVE] … inplace` | **CO** — `17:02:29.609 [OI-LIVE] inplace cold-load 663 coin …` |
| `[OI-LIVE] reload nền lỗi` (retry-storm) | **0** |
| Header `[R4-1M] LIVE_ENTRY_GRID_MIN=1` | **CO** — `17:01:13.723 … => SELECTOR quet moi 1 phut` |
| `[GATE]` moi phut (`topk=16`) | **CO** — tu `17:02:42` (vd `topk=16 base=0.00800 n_cand=16 n_rej=16 n_pass=0`) |
| `OutOfMemoryError` | **0** |
| `[S1] warm-up CHUA DU` | **0** |
| Lenh THAT | **0** (`SHADOW_NO_PUSH=true` hardcode; khong co dong dat lenh) |

## 4. RSS timeline (kB) — /proc/4064/status VmRSS

| Moc | Gio | RSS (kB) | RSS (MiB) | GATE luy ke | OOM |
|---|---|---|---|---|---|
| 0' | 17:01:56 | 1.438.624 | 1405 | 0 | 0 |
| ~5' | 17:06:29 | 5.295.208 | 5171 | 5 | 0 |
| ~10' | 17:11:30 | 5.198.444 | 5076 | 10 | 0 |

**Doc dien:** ban dau nhay len ~5,2 GB ngay (heap `-Xms5g` commit + ONNX/off-heap + OI cold-load 663 coin), roi **di ngang/giam nhe** (5295 -> 5198). Tren box 8 GB, `Mem available` thap (~84-132 MB) va swap da dung ~1.9 GB. **CAN THEO DOI** (nguong rui ro lich su ~5,5 GB => dmesg tung OOM-kill).

## 5. Canh du 2h (17:01 -> 19:01) — DANG CHAY

> Cho du 2h de chot KET LUAN PASS/ROLLBACK. Xem bang RSS/GATE/OOM cap nhat duoi day.

<!-- CAPNHAT:1 -->

## 6. KET LUAN

<!-- CAPNHAT:2 -->

### Rollback (neu can)
```bash
cd /home/chuyennd/java/v_t_m
cp -p target/binance-java-sdk-1.2.4.jar.bak_20260930_170043 target/binance-java-sdk-1.2.4.jar
cp -p conf/env.sh.bak_20260930_170043 conf/env.sh
bin/daemon.sh stop ; bin/daemon.sh start   # xac nhan SELECTOR_RANK_TOPK=8 + chay sach
```
