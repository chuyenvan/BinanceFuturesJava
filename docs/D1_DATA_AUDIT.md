# D1 — DATA AUDIT + RECIPE MO DEV VE 2021

Do ngay 2026-09-04 tren Oracle (instance-20260622-1647). Chi DO va DOC, khong chay Java,
khong train, khong xoa file. Moi so trong tai lieu nay la so DO THUC; cho nao khong do duoc
ghi ro "khong tim thay".

Nguon do: python aerospike client tu 127.0.0.1:3222 (khong co binary asinfo/aql tren box),
`du`/`df`/`stat`, doc truc tiep parquet/csv bang pandas.

---

## BLOCKER / RUI RO — DOC TRUOC

1. **`wfo_gate_pred.csv` bat dau 2021-03-31 17:00** (2,500,260 dong, den 2025-12-31 23:59).
   Day la nguon `p15` (market gate) dinh nghia POOL cua ledger. Vi vay `T0=2021-04-01` trong
   `ledger.py` KHONG phai lua chon tuy y — do la MEP DU LIEU.
   => **Fold OOS 2021Q2 (cut `20210401`) KHONG kha thi**: train = `D[ts < 20210401 - 72h]` = **0 dong**,
   guard `len(tr)<5000` se skip. Muon co fold 2021Q1/Q2 phai sinh lai `wfo_gate_pred.csv` tu 2021-01
   (job WFO gate phia Java) — ngoai pham vi phien nay.
2. **OI 2021-01..2021-11 KHONG TON TAI o bat ky cum nao** (ke ca 242). Khong the copy ve. Xem muc A.
3. **`predwf_G015x26` khong co `predict_wf_2021*.bin`** (som nhat = `20220101`).
   => duong Java sim khong the bat dau truoc 2022-01-01 ma khong rebuild WFO fold G015 cho 2021.
   Duong Python-only (S1 rank-IC + edge5 tren ledger) thi KHONG bi chan.
4. **Dia con 16G / 194G (92%)**. `tools/run_c2b_dev.sh` buoc 1 build `$DS` roi `rm -rf $DS` cuoi script;
   khong tim thay so do dung luong `$DS`. Rebuild dataset WFO co the dung het cho trong.

---

## A. AUDIT AEROSPIKE LOCAL

### A.1 Cluster local
- `asd --foreground` PID 1455, uptime 9d01h, build **8.1.2.3**, LISTEN `0.0.0.0:3222`, node `C9AD9DB01170002`.
- Namespaces: **`test`** va **`ticker`**.
- File dat: `/home/ubuntu/aerospike-data/test.dat` = 96,636,764,160 B (90 GiB allocated),
  `ticker.dat` = 16,106,127,360 B (15 GiB allocated). Tong dir 56G thuc dung.
- Duong backtest doc namespace **`test`** (`Configs.AEROSPIKE_NAMESPACE`); `NS_242="ticker"` chi la
  namespace THAT cua cum 242 khi doc-only (xem `CopyAuxSets242To226.java:39-45`).

### A.2 Sets trong ns `test` (28 set)

| set | objects | data_used_bytes | ghi chu |
|---|---:|---:|---|
| kline_1m_opt | 2,952,455 | 25,277,828,576 | ticker source cua sim |
| funding_pred_1m_v5 | 2,827,087 | 5,805,023,552 | |
| market_data_object | 2,947,861 | 330,051,840 | |
| ai_pred_market_full_basket_v2 | 2,819,841 | 503,066,064 | |
| ai_pred_market_gate_wfo | 2,500,260 | 440,043,888 | `WFO_SET_PRED` trong run_c2b_dev.sh |
| gate_dev | 2,500,260 | 400,041,408 | |
| ai_pred_market_gate_ab_retall24h | 2,500,260 | 453,455,680 | A/B leftover |
| ai_pred_market_gate_ab_retall60m | 2,500,260 | 442,369,696 | A/B leftover |
| ai_pred_market_gate_ab_max24h | 2,500,260 | 440,047,696 | A/B leftover |
| ai_pred_market_gate_ab_oldbasket | 2,500,260 | 440,335,088 | A/B leftover |
| ai_pred_market_gate_ab_ret15m | 2,500,260 | 440,046,000 | A/B leftover |
| ai_pred_market_gate_ab_ret60m | 2,500,260 | 440,046,704 | A/B leftover |
| ai_pred_market_gate_ab_retall15m | 2,500,260 | 441,259,024 | A/B leftover |
| funding_selector_pred_1m_v3wf | 350,557 | 294,097,904 | |
| funding_selector_pred_1m_v2 | 323,142 | 273,926,160 | |
| kline_15m_opt | 189,038 | 1,052,641,264 | |
| oi_taker_vol | 19,297 | 1,988,440,736 | key `SYM_YYYYMM` |
| open_interest | 19,987 | 1,943,665,904 | key `SYM_YYYYMM` |
| oi_ls_global_acc | 19,818 | 1,891,669,440 | key `SYM_YYYYMM` |
| oi_ls_toptrader_pos | 18,610 | 1,628,136,704 | key `SYM_YYYYMM` |
| oi_ls_toptrader_acc | 18,591 | 1,666,278,416 | key `SYM_YYYYMM` |
| wfo_jobs | 3,220 | 3,766,080 | |
| ai_pred_market_gate_wfo_smoke2 | 5,000 | 880,016 | smoke |
| **funding_data** | **831** | **22,425,808** | pipeline backtest doc set nay |
| symbol_lifecycle | 698 | 103,328 | |
| kline_15m_btceth | 126 | 12,259,136 | |
| kline_4h_btceth | 126 | 880,864 | |
| symbol_mapper | 1 | 11,040 | aux set |

### A.3 Sets trong ns `ticker` (local, 7 set) — ~8.4 GB
`oi_taker_vol` 17,811 / 1.84 GB · `open_interest` 18,501 / 1.81 GB · `oi_ls_global_acc` 18,332 / 1.76 GB ·
`oi_ls_toptrader_acc` 17,105 / 1.54 GB · `oi_ls_toptrader_pos` 17,124 / 1.50 GB ·
`oi_backfill_queue` 832 / 110 KB · `oi_backfill_done` 895 / 146 KB.

Day la ban SONG DOI cua cac OI set trong ns `test`, IT object hon (18,501 vs 19,987). Duong backtest
KHONG doc ns nay. `oi_backfill_queue/done` CHI ton tai o day => co job backfill OI dang dung.

### A.4 `funding_data` — CO DU 2021 KHONG? **CO.**

Full scan 831/831 record, **0 record khong decode duoc**.
Format: `key = <SYMBOL>` (send_key = true), bin `f_data` = `snappy.decompress_raw` -> JSON
`{settle_ts_ms(str): funding_rate(float)}`. Dung y nguyen cach `feat_v2_build.py:67` doc.

So COIN co >=1 ky settle trong thang:

| thang | coin | thang | coin |
|---|---:|---|---:|
| 2021-01 | **88** | 2021-07 | 116 |
| 2021-02 | **93** | 2021-08 | 122 |
| 2021-03 | **106** | 2021-09 | 127 |
| 2021-04 | **110** | 2021-10 | 131 |
| 2021-05 | **112** | 2021-11 | **133** |
| 2021-06 | **115** | 2021-12 | 136 |
| 2022-01 | 136 | 2022-04 | 144 |
| 2022-02 | 138 | 2022-05 | 144 |
| 2022-03 | 140 | 2022-06 | 141 |

Coverage tong: min 2021-01 (bo qua rac), max **2026-08-05 12:00**, 70 thang.
So coin/thang KHOP voi `CLOSES_1H.bin` (84 coin @2021-01 -> 132 @2021-12).

=> **`funding_data` phu du 2021-01..2021-11. KHONG phai blocker.**

Loi nho (khong chan gi): 3-4 record co key timestamp ~0 (parse ra 1969-12 / 1970-01).
`feat_v2_build.py:73` da loc `s.index > P.index[0]-30d` nen rac nay bi bo tu dong.

### A.5 OI sets — 2021 KHONG CO O DAU

Key = `SYMBOL_YYYYMM`, 1 record = 1 blob thang cua 1 coin (`oi_data`/`m_data` ~90-107 KB).
Local ns `test` KHONG luu key string (send_key=false) nen khong doc duoc thang tu key —
nhung `oi_percoin_full.bin` (dan xuat tu chinh cac set nay) da xac lap: 1 coin/thang
2021-01..2021-11, nhay len 137 coin tu 2021-12.

Do TRUC TIEP tren 242 (`ticker/open_interest`, 20,601 object, mau scan 4,000 ~19%):

| thang | record trong mau | thang | record trong mau |
|---|---:|---|---:|
| 2020-09 | 1 | 2021-12 | 26 |
| 2021-06 | 1 | 2022-01 | 28 |
| 2021-11 | 1 | 2022-02 | 25 |

`ticker/oi_ls_global_acc` (20,435 obj) giong het: 2020-12=1, 2021-04=1, 2021-08=1, 2021-09=1,
**2021-12=29**, 2022-01=28...

=> **242 cung khong co OI 2021-01..2021-11.** Khong the copy ve. OI thuc su bat dau 2021-12.

### A.6 So sanh 226 / 242 — set nao Oracle THIEU

`CopyAuxSets242To226.java` xac dinh aux set = **`funding_data`** (`SET_FUNDINGFEE`) + **`symbol_mapper`**
(`SET_MAPPER`). `CopyTicker242To226.java` copy **`kline_1m_opt`** (`SET_TICKER`), START_DATE default `20210101`.

| set | Oracle `test` | 226 `ticker` | 242 `ticker` | ket luan |
|---|---:|---:|---:|---|
| funding_data | 831 | 754 | 854 | Oracle thieu 23 symbol so 242 — la coin list moi 2026, KHONG anh huong DEV 2021-2024 |
| symbol_mapper | 1 | 1 | 1 | dong bo |
| kline_1m_opt | 2,952,455 | 2,909,486 | 2,984,694 | Oracle thieu ~32k phut so 242 (duoi ticker gan nhat) |
| open_interest | 19,987 | 18,501 | 20,601 | Oracle > 226; 242 nhieu nhat (coin moi 2026) |
| oi_ls_global_acc | 19,818 | 18,332 | 20,435 | idem |
| oi_ls_toptrader_acc | 18,591 | 17,105 | 19,217 | idem |
| oi_ls_toptrader_pos | 18,610 | 17,124 | 19,236 | idem |
| oi_taker_vol | 19,297 | 17,811 | 19,914 | idem |

Set CHI co tren 242, Oracle khong co:
- `oi_feat_delta24h`, `oi_feat_z`, `oi_feat_lsg`, `oi_feat_lst`, `oi_feat_takerbuy`: 1,413 obj/set,
  key `SYM_YYYYMM`, **chi 2026-08 (705) va 2026-09 (708)** => cache live rolling, KHONG co gia tri lich su.
- `oi_feat_accum`: 863 obj, key = `SYMBOL`, `a_data` 63-69 B => state accumulator live.
- `funding_data_new`: 638 obj — khong tim thay tham chieu nao trong repo.
- `ai_pred_1m` 139,190 · `dca_pred_1m` 0 · `hpo_queue`/`hpo_tasks`/`funding_tasks_*` 0 => duong prod live.

=> **Khong co set nao thieu ma can copy ve de mo DEV 2021.** Chay `CopyAuxSets242To226` chi de dong bo
23 symbol funding moi (2026) — khong lien quan nhiem vu B.

**TRA LOI A: Aerospike CO du du lieu 2021 cho duong funding (`funding_data`, 88->133 coin/thang
2021-01..2021-11). Cai THIEU khong phai Aerospike set nao ca — la OI (khong ton tai o Oracle,
226 lan 242) va `wfo_gate_pred.csv` (bat dau 2021-03-31).**

---

## B. RECIPE MO DEV TU 2022-01 VE 2021

### B.0 Moc som nhat kha thi — DO THUC

Do tren `/home/ubuntu/ledger/cand_dev.parquet` (1,220,490 dong, `g1lite` notna = 100%,
2021-03-31 20:00 -> 2024-06-24 20:45 GMT+7). PURGE = 72h. Guard: `len(tr) < 5000` -> skip.

| cut | train rows | oos 90d | verdict |
|---|---:|---:|---|
| `20210401` (2021Q2) | **0** | 332,412 | **SKIP — khong kha thi** |
| `20210501` | 64,134 | 280,474 | OK nhung train chi ~1 thang calendar |
| `20210601` | 210,118 | 129,236 | OK |
| **`20210701` (2021Q3)** | **329,882** | 55,773 | **OK — quarter-aligned, CHON** |
| `20211001` (2021Q4) | 389,583 | 55,777 | OK |
| `20220101` (hien tai) | 445,068 | 123,211 | baseline |

Rows/thang cua ledger 2021: 2021-03=101, 04=66,577, 05=161,044, 06=106,450, 07=13,200,
08=10,163, 09=32,652, 10=11,115, 11=17,741, 12=27,435. Tick distinct: 2021=**4,049**
(nhieu hon 2022=2,926, 2023=510, 2024=1,157).

=> **Moc som nhat hop le, quarter-aligned = `20210701`.** Them 2 fold (2021Q3, 2021Q4) => 12 fold.
Neu chap nhan cut khong quarter-aligned, `20210501` chay duoc nhung train chi 1 thang — ghi ro la fold yeu.
`2021Q2` nhu de bai neu la KHONG kha thi (train = 0).

### B.1 Cat 2 OI feature khoi KEEP — CHI SUA CONFIG

`$R/research/pipeline/s1_rank.py:22`

Truoc:
```
KEEP=["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d","ret_14d","ls_global","rk_oi_delta24h"]
```
Sau (7 feature thuan gia):
```
KEEP=["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d","ret_14d"]
```
Loai: **chi sua config**. Khong rebuild artifact nao. `featv2` van giu du 42 cot (S1 chi chon cot theo KEEP).

### B.2 Mo cut_days — CHI SUA CONFIG

`$R/research/pipeline/s1_rank.py:39`

Truoc:
```
cut_days=["20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001","20240101","20240401"]
```
Sau:
```
cut_days=["20210701","20211001","20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001","20240101","20240401"]
```
Loai: **chi sua config**.

### B.3 Cac cho khac hardcode 2022 / T_END / T_START

Ket qua `grep -rn "2022\|20220101\|T_END\|T_START"` tren `research/pipeline/`, `research/analysis/`, `tools/`
— da loc ra cai THUC SU chan:

| # | file:line | hien tai | doi thanh | co chan? | loai |
|---|---|---|---|---|---|
| 1 | `s1_rank.py:22` | KEEP 9 feat | 7 feat | — (muc B.1) | config |
| 2 | `s1_rank.py:39` | cut_days tu 20220101 | tu 20210701 | **CHAN** | config |
| 3 | `s1_rank.py:37` | `IC[[2022,2023,2024]]` | `IC[[2021,2022,2023,2024]]` | khong chan (cot 2021 da co san trong pool_rankic.csv) | config, chi diagnostic |
| 4 | `s1_rank.py:51` | `if i in (0,5,9)` (shuffle control theo INDEX fold) | `(0,6,11)` cho 12 fold | khong chan nhung lech y nghia | config |
| 5 | `s1_rank.py:60` | log tong ket chi in 2022/2023/2024 | them `2021 {100*E[yr==2021].mean():+.2f}` | khong chan, chi log | config |
| 6 | `s1_eval.py:30` | `for yy in (2022,2023,2024)` | them 2021 | khong chan, chi bang ket qua | config |
| 7 | `feat_v2_build.py:21` | `T_END=1719792000000` (2024-07-01) | giu nguyen | **KHONG chan** — T_END chi cat DUOI. featv2 thuc te 2021-01-31 -> 2024-07-01, 4,884,420 dong | khong doi |
| 8 | `ledger.py:14` | `T0=pd.Timestamp("2021-04-01")` | **khong ha duoc** | **CHAN CUNG** — dung mep `wfo_gate_pred.csv` (2021-03-31 17:00) | can rebuild `wfo_gate_pred.csv` |
| 9 | `ledger.py:21` | file filter `"2022" in f or "2023" ...` | them `"2021"` | vo hai nhung VO ICH: `predwf_G015x26` khong co bin 2021 | can rebuild bins G015 2021 |
| 10 | `build_map.py:30` | `if yr not in ("2022","2023","2024")` | them `"2021"` | **CHAN duong Java sim** — thieu bin 2021 nguon | can rebuild bins G015 2021 |
| 11 | `ledger3.py:28` | da co `"2021"` trong filter | giu nguyen | khong chan | khong doi |
| 12 | `configs/sim_dev.properties:39` | `TIME_RUN=20220101` | `20210701` | **CHAN duong Java sim** (xem B.4) | config + can bins |
| 13 | `research/analysis/*` (qret_ladder.py:14 QS list, g015cut_folddiag.py:13, labelh2.py:30, g015_rebuild.py:38 CUT_DATES, s1prov_sha.py:36 DEVF, regime_probe.py, ci_b4.py:30, nbets_step3_crosssec.py:43-44,96) | cut list / nhan nam 2022+ | doi khi chay lai phan tich tuong ung | KHONG chan S1 | config, tung script |

Luu y: `research/analysis/*.json` va `BINS_MANIFEST.md` la BAN GHI PROVENANCE (sha256 cua bins da pin) —
**KHONG sua tay**, se duoc sinh lai boi `s1prov_sha.py` / `g015_rebuild.py` khi co bins moi.

### B.4 Phia Java sim — bien nao quy dinh ngay BAT DAU DEV

**Khong co `SIM_START_DATE`.** Doi xung cua `SIM_END_DATE` la config key `TIME_RUN`:

- `SimulatorMarketLevelTicker1MStopLoss.java:113`
  `Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;`
- `Configs.TIME_RUN` doc tu `config.properties`, ma `tools/run_c2b_dev.sh:39` copy tu
  **`$R/configs/sim_dev.properties`** -> dong **39: `TIME_RUN=20220101`**. **DAY la moc BAT DAU DEV.**
- Ngay ket thuc: `SIM_END_DATE=20240630` dat qua env tai `tools/run_c2b_dev.sh:53`
  (cung o `research/analysis/g015_c3run.sh:24`, `tools/parity_clean.sh:39`, `tools/run_ticklog_pair.sh:33`).
  `SIM_END_DATE` co trong whitelist `Cfg.java:50`; `TIME_RUN` thi KHONG => `TIME_RUN` **chi doi duoc qua
  file config**, khong override bang env.
- Sau `SIM_END_DATE` con `HoldoutSeal.clampEnd()` — chi chan DUOI, khong lien quan ngay bat dau.

Doi `TIME_RUN=20210701` la **chi sua config**, NHUNG sim se chay 2021H2 ma khong co selector bins
=> phai co `predict_wf_20210701.bin` / `predict_wf_20211001.bin` trong `$DS`. Xem B.5.

### B.5 Rebuild can thiet — theo tung duong

**Duong 1 (khuyen nghi cho nhiem vu nay): Python-only, S1 rank tren ledger.**
Chi B.1 + B.2 (+ B.3 muc 3/4/5/6 cho dep log). **0 rebuild artifact.**
- Chay lai: `python3 $R/research/pipeline/s1_rank.py <suffix>`
- Dau ra: `/home/ubuntu/ledger/pred_s1a<suffix>.parquet` + ghi de `pool_rankic.csv`
- Dia them: ~7 MB (pred_s1a hien tai 6.16 MB cho 10 fold; 12 fold ~7.4 MB)
- Thoi gian: **khong tim thay so do** trong repo. Uoc theo quy mo (1.22M dong x 12 fold,
  XGBRanker 300 cay depth 4 + 3 fold shuffle-control, `n_jobs=4`) = vai chuc phut CPU.
- Rui ro: ghi de `pool_rankic.csv` (nen backup truoc, 2.4 KB).

**Duong 2: mo den ca Java sim DEV tu 2021H2.** Can thang tu:

| Buoc | Input | Da co? | Thoi gian | Dia |
|---|---|---|---|---|
| a. WFO fold G015 cho `20210701`, `20211001` -> `predict_wf_2021*.bin` | `ds_feat15m/features_20210401_to_20210701.t1c.gz`, `..._20210701_to_20211001...`, `label_15m/funding_label_20210401_to_20210701.pb`, `..._20210701_to_20211001.pb` | **CO du ca 4** (ds_feat15m co window tu `20210101_to_20210401`; label_15m tu `20210101_to_20210401`) | scoring lai: ~3.3 min/fold (do tu mtime `predwf_G015_v2`: 10 fold trong 06:08->06:41 = 33 min). **Train moi tu dau: khong tim thay so do** | 2 bin x ~28 MB = **~56 MB** |
| b. `build_map.py` map S1 score -> bins | `pred_s1a*.parquet` + bins G015 (buoc a) | script co | ~1-2 min ca 12 fold (`predwf_map_s1a2` 10 file cung mtime 22:50) | 12 bin x ~33 MB = **~400 MB** |
| c. Rebuild ledger `cand_dev.parquet` | `wfo_gate_pred.csv` + `label_15m` + bins G015 | gate CSV **chi tu 2021-04** -> `T0` van 2021-04-01 | ~5-10 min (uoc; 1.22M dong tu 4 file .pb) | 30 MB (ghi de) |
| d. `ExportWfoDataset $DS` (dataset WFO cho sim) | `tools/run_c2b_dev.sh` buoc 1, `-Xmx14g` | script co | **khong tim thay so do** | **khong tim thay** — script tu in `du -sh $DS` roi `rm -rf $DS`. **Rui ro: dia con 16G** |
| e. Sim C2b DEV | JVM slot duy nhat (`run_c2b_dev.sh:27` fail-fast neu co JVM khac) | — | **khong tim thay so do** | printDone.csv nho |

**Khong can rebuild `featv2/feat_v2.parquet`** (1.2G): da phu 2021-01-31 -> 2024-07-01, `vol_7d`
notna 99% tu 2021-01. Chi phai rebuild neu muon **bo hang cot OI khoi parquet** — khong can, vi S1
chon cot theo KEEP. Neu van rebuild: doc `CLOSES_1H.bin` + full scan `funding_data` + memmap
`oi_percoin_full.bin` 4.2G, dia ~1.2G (ghi de), thoi gian khong tim thay so do.

**Khong the rebuild trong pham vi hien tai**: `wfo_gate_pred.csv` cho 2021-01..2021-03 (can job WFO
gate phia Java + JVM slot). Do la thu duy nhat chan fold 2021Q1/Q2.

### B.6 CHECKLIST

1. Backup `cp /home/ubuntu/ledger/pool_rankic.csv{,.bak}` va `cp .../pred_s1a.parquet{,.bak}` — 6 MB, 5 s.
2. `s1_rank.py:22` -> KEEP 7 feature (bo `ls_global`, `rk_oi_delta24h`). Config.
3. `s1_rank.py:39` -> `cut_days` bat dau `20210701` (12 fold). Config.
4. `s1_rank.py:37` -> `IC[[2021,2022,2023,2024]]`; `:51` -> `(0,6,11)`; `:60` -> them cot 2021. Config, tuy chon.
5. `s1_eval.py:30` -> them 2021. Config, tuy chon.
6. Chay `s1_rank.py` 1 lan. So sanh `edge5` 12-fold-7-feat vs 10-fold-9-feat da ghi
   (`pred_s1a`: nguong pre-reg +6.0%, duong 3 nam, t>=10; G015 baseline +4.55%).
7. CHI KHI can Java sim tu 2021H2: buoc a-e o B.5 + `configs/sim_dev.properties:39` -> `TIME_RUN=20210701`
   + `build_map.py:30` va `ledger.py:21` them `"2021"`.

**Tong (buoc 1-6, duong Python-only): 0 rebuild artifact, dia them ~7 MB, thoi gian = 1 lan chay
`s1_rank.py` (khong tim thay so do; uoc vai chuc phut).**
**Tong (them buoc 7, duong Java sim): dia them ~500 MB cho bins + `$DS` khong tim thay so do
(rui ro voi 16G con lai); thoi gian buoc a khong tim thay so do neu phai train moi.**

---

## C. CHI PHI THUC CUA VIEC CAT 2 OI FEATURE

Nguon: **`/home/ubuntu/ledger/pool_rankic.csv`** (da co san, mtime 2026-09-04 08:09, 2,434 B).
Sinh boi `s1_rank.py:38`. Da chua san cot **2021**, tuc dien do da chay tren ledger co 2021.
Dinh nghia: `rel = g1lite - median(g1lite) trong tick`; `rank-IC = spearmanr(feat, rel)` tren pool
`cand_dev.parquet` da join `featv2`, tach theo nam, chi tinh khi `notna > 1000` dong.

### C.1 9 feature trong KEEP

| feature | 2021 | 2022 | 2023 | 2024 | mean | dau nhat quan 22-24 |
|---|---:|---:|---:|---:|---:|:--:|
| `vol_7d` | 0.0575 | 0.0929 | 0.1709 | 0.1471 | **0.1171** | CO |
| `rk_dd_7d` | -0.0984 | -0.1368 | -0.1001 | -0.0694 | **-0.1012** | CO |
| `dd_7d` | -0.0372 | -0.0602 | -0.0524 | -0.0344 | **-0.0460** | CO |
| **`ls_global`** (OI) | **-0.0052** | **-0.0416** | **-0.0493** | **-0.0622** | **-0.0396** | **CO** |
| `rk_ret_3d` | -0.0502 | -0.0790 | 0.0547 | 0.0031 | -0.0179 | khong |
| `hrs_since_high_7d` | -0.0235 | 0.0027 | -0.0118 | -0.0053 | -0.0095 | khong |
| `ret_3d` | -0.0104 | -0.0245 | 0.0446 | 0.0140 | 0.0059 | khong |
| `ret_14d` | -0.0066 | -0.0416 | 0.0266 | 0.0429 | 0.0053 | khong |
| **`rk_oi_delta24h`** (OI) | **-0.0067** | **-0.0165** | **0.0146** | **0.0086** | **-0.0000** | **khong** |
| _moc noise_0_ | -0.0007 | 0.0008 | -0.0033 | -0.0033 | -0.0016 | khong |
| _moc noise_1_ | -0.0001 | -0.0002 | 0.0013 | 0.0015 | 0.0006 | khong |
| _moc noise_2_ | 0.0030 | -0.0003 | -0.0005 | -0.0002 | 0.0005 | (CO, do trung hop) |

### C.2 Ket luan

- **`rk_oi_delta24h`: cat = mat gan bang 0.** mean IC = -4.3e-19 (~0.0000). Doi dau giua 2022 (-0.0165)
  va 2023/2024 (+0.0146/+0.0086). |IC| lon nhat 0.0165, chi nhich tren moc noise (|IC| noise 0.0002-0.0033).
  Khong nhat quan dau => khong dat tieu chi cua chinh repo.
- **`ls_global`: cat = mat THAT.** |IC| 0.0416 / 0.0493 / 0.0622 (tang deu theo nam), dau NHAT QUAN
  ca 3 nam, mean |0.0396|. Trong 9 feature KEEP no la:
  - manh thu **4/9** ve |mean IC|;
  - **1 trong 4 feature duy nhat co dau nhat quan** (cung `vol_7d` 0.1171, `rk_dd_7d` -0.1012, `dd_7d` -0.0460);
  - `|ls_global|` = 0.0396 tren tong |IC| cua 4 feature nhat quan = 0.3039 => **~13%**;
  - lon hon **toan bo 4 feature momentum con lai** (`ret_3d` 0.0059, `ret_14d` 0.0053, `rk_ret_3d` -0.0179,
    `hrs_since_high_7d` -0.0095) ca ve |IC| VA ve tinh nhat quan (4 cai kia deu doi dau).
  - Sau khi cat: 7 feature con lai chi con **3 feature nhat quan dau** (`vol_7d`, `rk_dd_7d`, `dd_7d`,
    tong |IC| 0.2643) + 4 feature doi dau. Tuc **model 7-feature gan nhu la model volatility/drawdown thuan**.
- **Trong 2021 (vung ta muon mo): CA HAI feature OI = noise.** `ls_global` 2021 = -0.0052,
  `rk_oi_delta24h` 2021 = -0.0067 — cung bac do lon voi noise. Ly do: OI chi co 1 coin/thang toi 2021-11
  (`featv2`: `ls_global`/`oi_z`/`rk_oi_delta24h` notna ~1% toi 2021-11, roi 96-100% tu 2021-12).
  => **Giu 2 feature nay khi mo DEV ve 2021H2 se nap ~gan het NaN vao train fold 2021Q3 — te hon la cat.**
- Tra loi truc tiep "cat OI mat gi": mat **1 trong 4 tin hieu nhat quan** (`ls_global`, ~13% tong |IC|
  cua nhom nhat quan) + mat 0 tu `rk_oi_delta24h`. Doi lai duoc **2 fold OOS moi (2021Q3, 2021Q4)** va
  **+4,049 tick 2021** vao pham vi do.
- **Khong co phep do `edge5` / nDCG cho bien the 7-feature** => **khong tim thay**. Phai chay
  `s1_rank.py` (buoc 6 o B.6) moi ket luan duoc chi phi cuoi cung theo don vi edge, khong phai chi IC.

---

## D. DANH SACH UNG VIEN GIAI PHONG DIA — CHI LIET KE, KHONG XOA

`df -h /`: **194G total, 179G used, 16G avail, 92%**.

### D.1 An toan cao — trung lap / ban cu da bi thay the

| path | dung luong | dung de lam gi | tai sao an toan / rui ro |
|---|---:|---|---|
| `/home/ubuntu/java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz` | 3,150,638,338 B (2.93 GiB) | export OI per-coin cho sim | **Ban CU** cua `..._to_20260701.bin.gz` (3,210,547,898 B, mtime Aug 5 > Jul 7). Ban moi bao trum ca khoang. Rui ro: gan nhu 0 |
| `/home/ubuntu/claudedata/oi/funding-oi-percoin.zip` | 3,199,825,925 B (2.98 GiB) | zip nguon cua `oi_percoin_full.bin` | `oi_percoin_full.bin` (4,227,723,300 B) da giai nen va la thu `feat_v2_build.py:93` doc truc tiep; con 2 ban `.bin.gz` o `features_oi_percoin_v1`. Rui ro: mat nguon zip neu bin hong |
| `/home/ubuntu/tickexport/up_zip/ticker_2021.zip` | 1,130,971,089 B (1.05 GiB) | zip tick 2021 de upload Kaggle | Ban **KHAC** (inode 781901, nlink=1) va NHO hon `up5/2021/ticker_2021.zip` (inode 781936, 1,133,259,885 B). Trung lap that. Rui ro: neu 2 file khac noi dung chu khong chi khac nen — **can `md5sum` truoc khi xoa** |
| `/home/ubuntu/ledger/cand_dev3_OLDCLAMP.parquet` | 412,835,429 B (394 MiB) | ledger v3 truoc khi sua clamp | Da bi `cand_dev3.parquet` thay the (cung mtime Sep 3 17:53). Ten tu ghi la OLD |
| `/home/ubuntu/ledger/cand_dev_OLDCLAMP.parquet` | 24,419,995 B (23 MiB) | idem cho ledger v2 | idem |
| `/home/ubuntu/oi_compute.jar`, `oi_compute_ab.jar`, `oi_compute_ab_24h.jar`, `reconcile_v1.jar` | 4 x ~95 MiB = **380 MiB** | jar chay 1 lan (Aug 17-18) tinh OI / reconcile | Tai tao bang `mvn package`. Rui ro: mat reproduce byte-identical neu code da doi |
| `/home/ubuntu/label_5m_q2tmp` | 776 MiB | ten tu ghi la `tmp` (label 5m quarter 2) | Khong tim thay tham chieu nao trong `tools/`/`research/`. Rui ro: neu con job 5m dang cho |
| `/home/ubuntu/aerospike-wfo.conf.bak_accessaddr_20260821`, `.bak_afix_20260822_111421`, `.bak_prticker_20260820`, `bt_gate_old.log`, `metric_dist_gateold.log`, `phase1_coldtest.log`, `C2B_SPEC_OLD.md`, `drive_exp18.sh.bak_slugfix` | vai MB tong | backup config / log cu | An toan; nen giu 1 ban `.bak` config Aerospike moi nhat |

**Tong D.1: ~9.5 GiB.**

### D.2 Can xac nhan — jar snapshot va dataset da dung xong

| path | dung luong | dung de lam gi | rui ro |
|---|---:|---|---|
| `/home/ubuntu/java/simulator/*.jar` (~20+ file: `preflight-v4x`, `gatecount_*`, `mom15probe`, `selrank-v1`, `binance-khungv1-20260824`, `*.jar.bak`) | ~**5G** (suy ra: `simulator` 26G − `kaggle_data_hpo` 15G − `features_oi_percoin_v1` 6.0G) | snapshot build cho tung thi nghiem (Aug 2026) | Tai tao bang `mvn package` NEU code chua doi. **Rui ro: mat kha nang reproduce baseline byte-identical** ma `run_c2b_dev.sh:67` doi hoi. Chi xoa jar KHONG duoc PIN trong `docs/`. Can user xac nhan tung file |
| `/home/ubuntu/cmp/ds_base/funding.bin` (+ ca `cmp/` 5.1G) | 5,302,996,256 B (4.94 GiB) | dataset WFO da build cho so sanh | `/home/ubuntu/cmp` KHONG xuat hien trong grep `tools/`+`research/`. Tai tao bang `ExportWfoDataset`. Rui ro: rebuild ton thoi gian + dia |
| `/home/ubuntu/cpcv/` | 4.2G (`kag` 2.5G gom `kag/ds/funding.bin` 2,371,947,300 B; `preds_001/0015/002/003` 269M x4; `kag_v5` 102M; `kg` 96M; `jartrail` 96M) | nghien cuu CPCV (da xong) | Khong duoc `tools/` tham chieu. Rui ro: mat ket qua CPCV goc |
| `/home/ubuntu/ds_feat5m` + `/home/ubuntu/ds_label5m` | 4.6G + 5.7G = **10.3G** | dataset 5m (features + label) | Repo dang chay 15m: `ds_feat15m` duoc tham chieu **15 lan**, `ds_feat5m`/`ds_label5m` **0 lan**. Rui ro: neu co nhanh 5m dang cho. Tai tao duoc nhung rat lau |
| `/home/ubuntu/claudedata/gate_ab_full` 1.4G + `gate_ab_full2` 1.3G + `wfo_feature_store_24h.csv` 1,238,681,361 B + `gate15m_v2_full.csv` 1,238,681,360 B + `gate_dataset_full.csv.gz` 340M | ~**5.3G** | A/B gate cu (feature store 24h, gate 15m v2) | Tuong ung cac set `ai_pred_market_gate_ab_*` trong Aerospike (cung la leftover). Rui ro: mat kha nang chay lai A/B gate |
| `/home/ubuntu/team_success` 98M + `team_fail` 97M + `team_path` 95M | 290 MiB | ket qua team run | Khong tim thay tham chieu |

**Tong D.2: ~30 GiB** (5 + 4.94 + 4.2 + 10.3 + 5.3 + 0.29).

### D.3 Rui ro cao — tick history va HPO data

| path | dung luong | dung de lam gi | rui ro |
|---|---:|---|---|
| `/home/ubuntu/java/simulator/kaggle_data_hpo/daily` | 13G | tick daily `.bin.gz` cho HPO tren Kaggle | Tai tao tu Aerospike `kline_1m_opt` bang tickexport job. **Rui ro: co job HPO/Kaggle dang dung** |
| `/home/ubuntu/tickexport/up_hist` | 11G | tick daily `.bin.gz` lich su (den 2025-12) | idem; trung y nghia voi `kaggle_data_hpo/daily` |
| `/home/ubuntu/tickexport/uphalf` | 6.4G (`2025h2` 2.36G, `2025h1` 1.85G, `2024h2` 1.42G, `2024h1` 1.23G — tat ca nlink=1, KHONG trung) | tick nua nam de upload | Trung noi dung voi `up5/ticker_20xx.zip` (ca nam). Rui ro: cat nho hon co the la dang duy nhat Kaggle nhan |
| `/home/ubuntu/tickexport/up5/` + `up_zip/` (2022-2025) | **9.9G do MOT LAN** | zip tick theo nam | **CANH BAO: `ticker_2022/2023/2024/2025.zip` co `nlink=2`, CUNG INODE o ca `up5` va `up_zip`** (inode 781903/781904/781905/781906). Xoa 1 ben = **giai phong 0 byte**. Chi giai phong khi xoa CA HAI ben |
| `/home/ubuntu/tickexport/up2026/ticker_2026.tar` | 3,346,821,120 B (3.12 GiB) | tar tick 2026 | nlink=1. Trung voi `up26pf` 3.2G? — khong do duoc, can `md5sum` |
| `/home/ubuntu/gs/ds` | 2.2G (gom `funding.bin` 1,826,293,736 B) | dataset grid-search | `/home/ubuntu/gs` duoc scripts tham chieu **5 lan** => **co the dang dung**. Chi xoa `gs/ds` neu grid-search da xong |
| `/home/ubuntu/wfo_ds_clean/funding.bin` | 1,826,293,736 B (1.70 GiB) | dataset WFO clean | `wfo_ds_clean` duoc tham chieu 2 lan trong scripts => co the dang dung |

### D.4 Aerospike — KHONG khuyen nghi xoa

| path / doi tuong | dung luong | ghi chu |
|---|---:|---|
| `/home/ubuntu/aerospike-data` | 56G (`test.dat` 90 GiB allocated, `ticker.dat` 15 GiB allocated) | **KHONG de xuat xoa** (theo yeu cau) |
| ns `ticker` local (7 set, ~8.4 GB data) | file `ticker.dat` 15 GiB | Ban song doi cua OI set trong ns `test`, IT object hon. Duong backtest doc ns `test`, KHONG doc ns nay. **Nhung** `oi_backfill_queue` (832) / `oi_backfill_done` (895) CHI ton tai o day => co job backfill OI dang dung. Truncate can restart `asd` (pha JVM/pipeline dang chay). **KHONG khuyen nghi** |
| 7 set `test/ai_pred_market_gate_ab_*` | 7 x 2,500,260 obj, tong **3,097,560,000 B (2.88 GiB)** data_used | A/B gate leftover (`retall24h`, `retall60m`, `max24h`, `oldbasket`, `ret15m`, `ret60m`, `retall15m`). Truncate duoc bang client, khong can restart. **NHUNG Aerospike KHONG shrink file** — chi thanh free space noi bo, `test.dat` van 90 GiB. **=> giai phong 0 byte tren `df`** |
| `test/ai_pred_market_gate_wfo_smoke2` (5,000 obj) | 880,016 B | smoke test leftover; cung khong shrink file |

**Diem quan trong: truncate set Aerospike KHONG tra dia lai cho `df`.** Muon thu hoi phai
`asd` defrag/re-provision — ngoai pham vi va can dung service.

### D.5 Tong ket dung luong

| tier | tong | ghi chu |
|---|---:|---|
| D.1 an toan cao | **~9.5 GiB** | co the xoa ngay sau khi `md5sum` xac nhan `up_zip/ticker_2021.zip` |
| D.2 can xac nhan | ~30 GiB | jar snapshot + dataset da dung xong |
| D.3 rui ro cao | ~46 GiB | tick history / HPO — **luu y 9.9G la hardlink, xoa 1 ben = 0 byte** |
| D.4 Aerospike | 0 GiB thuc te | truncate khong shrink file |

**Giai phong AN TOAN (D.1) = ~9.5 GiB** => dia tu 16G len ~25.5G (87%).
**D.1 + D.2 = ~39.5 GiB** => ~55G free (72%), du cho rebuild `$DS`.

---

## PHU LUC — LENH DO DA DUNG

Tat ca chay qua channel `runsh.ps1` (script bash `D1_*.sh` -> Oracle), khong chay Java.

- Aerospike: `aerospike.client({"hosts":[("127.0.0.1",3222)]})` + `info_all("namespaces"|"sets"|"build")`;
  `client.scan(ns,set).foreach(cb)` (full scan chi voi `funding_data` = 831 rec / 22 MB;
  cac OI set dung `foreach(cb,{"max_records":4000})` de KHONG scan het 56G).
- 226 / 242: cung client, `hosts=[("103.157.218.226"|"103.157.218.242",3222)]`, `info_all("sets")`.
- Parquet/CSV: `pandas.read_parquet` / `read_csv` voi `usecols` han che.
- Dia: `df -h /`, `du -sh`, `find -size +1G -printf`, `stat -c '%i %h %s %n'` (de phat hien hardlink).
