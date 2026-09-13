# AUDIT — OI FEATURE PARITY (LIVE vs TRAINING) cho S1

Ngày: 2026-09-13. Read-only. Box do: 161.118.212.3 (Oracle repo). KHONG ghi 242, KHONG sua logic.

## 0. Boi canh
S1 dung 9 feature; 2 feature OI: **ls_global** va **rk_oi_delta24h** (rank cross-section cua oi_delta24h).
- TRAINING doc: `/home/ubuntu/featv2/feat_v2_x1.parquet` (cot `ls_global`, `oi_delta24h`, `rk_oi_delta24h`).
- LIVE doc: Aerospike-242 set `oi_feat_delta24h`, `oi_feat_lsg` (LiveOiFeatProvider.lookup, merge_asof backward 2h),
  duoc ghi boi `ComputeOiFeat2Live242` (formula) tu OI/LS raw.

## 1. PARITY CONG THUC — KHOP (identical, code-level)
`ComputeOiFeat2Live242.walkSeries` (writer LIVE) la BAN COPY nguyen van cua `ExportFundingOiPerCoin.writeCoin`
(exporter TRAINING). Ca hai:
- `oi_delta24h = oi[t] / oi.floorEntry(t-24h) - 1`, guard `(t-24h - pastKey) <= 1h` (STALE_MS), past != 0.
- `ls_global  = floorStale(lsg_raw, t)` trong 1h — gia tri RAW cua `oi_ls_global_acc` (long/short global-account),
  KHONG bien doi don vi.
- Cung set raw: OI=`open_interest/oi_data`, LSG=`oi_ls_global_acc/m_data`. Cung STALE=1h, DAY=24h.
- oiZ expanding identical (khong dung cho S1).

TRAINING (`x1_feat_v2_build.py`) KHONG tinh lai oi_delta24h/ls_global: no NAP thang output cua ExportFundingOiPerCoin
(.bin 5m), chi giu moc `ts % 1h == 0` roi `ffill(limit=2)` = dung sai so 2h. LIVE `LiveOiFeatProvider.lookup` =
merge_asof backward `MERGE_TOL_MS = 2h`. `rk_oi_delta24h`: ca hai = `rank(axis=1, pct=True)` cross-section
(method='average') == `S1FeatureLive.rankPct`. => Cong thuc + don vi + window 24h + rank: KHOP.

## 2. PARITY GIA TRI — KHOP (do tren join THAT)
Do khong co overlap thoi gian giua 2 artifact PRECOMPUTE (featv2 <= 2026-01-01; 242 oi_feat >= 2026-08-03),
dung OI/LS RAW tren 242 (co DU 6 nam: 2020-09 -> nay) tinh lai bang DUNG formula, join voi featv2 o cua so trung.

### 2a. featv2  vs  recompute-tu-242-raw  (2025-11-01..2026-01-01, 42 coin, 53,405 dong gio)
| feature | spearman | pearson | max\|d\| | mean\|d\| |
|---|---|---|---|---|
| oi_delta24h | 1.000000 | 1.000000 | 3.15e-07 | 2.29e-08 |
| ls_global   | 1.000000 | 1.000000 | 2.26e-07 | 2.47e-08 |
| rk_oi_delta24h (rank/tick, coin chung) | 1.000000 | - | 0.0143 | 5.3e-07 |

rk_oi_delta24h: **%khop rank (<1e-6) = 99.996%** (max\|d\|=0.0143 = 1 bac rank tren ~36-42 coin, chi o so tick
hiem do float-tie doi thu tu). => featv2 == formula(242-raw) toi sai so float. **Khong co "nguon OI khac".**

### 2b. Dong vong: precompute 242 (cai LIVE THUC doc)  vs  recompute-tu-242-raw  (2026-08-03..09-13, 412,646 dong 5m)
| feature | spearman | mean\|d\| | %>1e-4 | %>0.01 | max\|d\| |
|---|---|---|---|---|---|
| oi_delta24h | 0.999995 | 2.46e-06 | 0.0002% (1/412k) | 0.0002% | 1.007 |
| ls_global   | 0.999999 | 1.28e-05 | 0.2305% | 0.0339% | 0.0805 |

Outlier cuc hiem, KHONG he thong: precompute doc raw `226 ∪ 242` (merged) con recompute chi `242-only`;
lech chi o vai diem BIEN GAP (delta: 1 tick / 412k; lsg: 0.03% dong lech >0.01, max 0.08). Rank cua S1 hap thu het.

## 3. RETENTION 242
- `oi_feat_delta24h` / `oi_feat_lsg` (PRECOMPUTE, cai live doc): **2026-08-03 13:15 -> 2026-09-13 00:50 UTC
  = 40.5 ngay (~1.3 thang, KHONG phai 2 thang)**. 593 coin co data. Du cho live (chi can gan day).
- OI/LS RAW (`open_interest`, `oi_ls_global_acc`) tren 242: **DU 6 nam (2020-09 -> nay)** — dung de audit nay.

## 4. VERDICT: **KHONG VENH**
2 feature OI cua S1 (`ls_global`, `rk_oi_delta24h`) parity giua TRAINING (featv2) va LIVE (242) toi sai so float.
Khong lech cong thuc, khong lech don vi, khong lech nguon OI, timestamp khop tai moc gio. => KHONG can fix.

## 5. Ghi chu (immaterial, khong phai bug)
- Alignment: TRAINING gioi han OI ve moc `ts%1h==0` roi ffill<=2h; LIVE floorKey lay diem 5m BAT KY <= t trong 2h
  (ke ca intra-hour :05..:55). Khi co diem dung moc gio (thuong le) -> identical (da xac nhan 99.996% khop rank).
  Chi lech neu moc gio thieu ma co diem intra-hour -> live FRESHER hon chut. Khong dang ke voi rank.
- Precompute doc `226∪242` merge; vai tick bien-gap lech so voi 242-only (muc 2b). Non-systematic.

## 6. Blocker / gioi han
- **226 (Aerospike Oracle DB 103.157.218.226) UNREACHABLE tu box nay** (connect timeout). Khong doc truc tiep nguon
  goc 226 cua training; dung 242-raw lam proxy (hop le: 242-raw == featv2 o overlap, muc 2a, da chung minh source khop).
- **Khong overlap** giua 2 artifact PRECOMPUTE -> khong join truc tiep duoc; da dung 242-RAW (full 6y) recompute =
  phep so sanh dung va manh hon.
- Raw dump gioi han **42 coin** (bridge 60s SIGHUP cat giua chung dump full); day la cac id thanh khoan cao nhat
  (BTC/ETH/majors) — sat S1 nhat. So parity o tren tren 42 coin nay.

## Phu luc — probe (read-only, /tmp, KHONG commit vao repo)
- `OiFeatDump242` (dump oi_feat_* 242), `RawDump242` (dump OI/LS raw 242), `Probe226` (test 226 - fail).
- Python: `/tmp/parity.py` (2a), `/tmp/loop2.py` (2b). CSV: `/tmp/oi_feat_242.csv`, `/tmp/oi_raw_242.csv`.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
