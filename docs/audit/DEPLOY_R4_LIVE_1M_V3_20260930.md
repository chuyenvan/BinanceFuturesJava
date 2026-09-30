# DEPLOY R4 LIVE 1' V3 — shadow-c3 (Oracle, PAPER) — 2026-09-30

Plan: docs/plan/PLAN_DEPLOY_R4_1M_V3.md. Thuc thi boi agent (MASTER Opus audit 2h sau). KHONG dung 242 / KHONG ssh 242.

## Deploy
- Restart shadow-c3: 2026-09-30 02:38:17Z (09:38 local). HEAD `557bf3f9` (chua B6 3305f43). Build: `mvn -o package -DskipTests` EXIT=0 (mvn o /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn; KHONG chay `mvn test` — chi package).
- jar moi sha256: `01eb271a2c43f9b6cee16ce19a0947c85bb2089dbf74ae1c5ae24e2a7db032f5`
- LUU Y: KHAC jar B6 trong plan (`31a24f90...`) vi HEAD co them commit 84d4335a (G2_LIVE_PORT, `LiveGateRollingRatio`, sau key `LIVE_GATE_ROLLING_*`, mac dinh TAT; env.sh khong co key nao => no-op). Da doi chieu diff src/main 3305f43..HEAD.
- jar cu (shadow dang chay truoc do): `78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71`
- Backup jar: `/home/ubuntu/shadow_c3/app/target/binance-java-sdk-1.2.4.jar.bak_20260930_093731`
- Backup env: `/home/ubuntu/shadow_c3/app/conf/env.sh.bak_20260930_093731`

## Diff env (conf/env.sh, khong co secret)
```
- export SELECTOR_RANK_TOPK=8
+ export SELECTOR_RANK_TOPK=16
+ export LIVE_ENTRY_GRID_MIN=1
+ export ENTRY_CASCADE=0
```
Giu nguyen: `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true` (grep xac nhan sau sua + sau 15').

## Sanity 15' (02:38:17Z -> 02:53:42Z) — PASS toan bo
| tieu chi | ket qua |
|---|---|
| [R4-1M] header | `LIVE_ENTRY_GRID_MIN=1 => SELECTOR quet moi 1 phut` |
| [GATE] moi phut | 14/14 phut lien tuc tu 09:40 (tick dau 09:40:13 tre do warm-up 68s), `topk=16` |
| S1 score | min 631 coin/tick (~653-660), MAP n_coins=653 |
| warm-up CHUA DU | 0 |
| ERROR moi | 0 (nen truoc restart: 4713 dong ERROR trong full.log) |
| selector tick (ms) | 4172, 989, 716, 686, 1160, 567, 673, 598, 700, 408, 648, 389, 410 (sau tick warm-up 67783ms) |
| free mem | avail 14.7G / free 5.8G |
| RSS shadow | ~4.78G (cao hon 2.6-3.2G trong plan — theo doi) |
| Lenh that | grep N_ORDER/PLACE_ORDER/newOrder = 0 (SHADOW_NO_PUSH=true) |

Ghi chu: n_pass=0 (n_cand=16, n_rej=16) o cac tick da xem — gate dynamic scale 1.70, thr ~0.037-0.046. S1 warm-up doc Aerospike 103.157.218.242 (read-only, cau hinh co san cua shadow, co ca truoc deploy) — MASTER xem lai neu can tach khoi 242.

Rollback (neu can): cp -f 2 file .bak_20260930_093731 ve cho, `sudo systemctl restart shadow-c3`, xac nhan TOPK=8.
Trang thai: DANG CHAY, cho MASTER audit 2h.
