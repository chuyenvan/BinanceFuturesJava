# V11_COLLECTOR_SETTLE — sửa đường input feature live cho v1.1 (thiết kế, trước khi code)

Ngày 2026-10-20. Owner 10-20 đã quyết: sửa "collector" ở v1.1 rồi reset cửa sổ promotion. Tài liệu này ghi
(1) điều tra lại nguyên nhân gốc, (2) thiết kế fix, (3) kế hoạch kiểm offline + deploy. Chỉ đọc 242, không deploy.
Nhánh code: `v1.1/collector-settle` từ `98e5b919` (= jar live `dc839568`, đã so 737/737 class bit-identical).
Thư mục làm việc Oracle: `~/claude_master/v11_settle/` (harness, raw, kết quả).

## 1. Kết luận điều tra (thay giả thuyết của PARITY_1020 §2)

**Không phải collector chốt thiếu.** Live đọc phút M ở giây 6 của M+1 và lúc đó đã đủ 738/738 symbol ở MỌI phút.
"Total ~300/738" trong log collector là ảo giác do cách đếm:

- `TickerIngestor2AerospikeNew.startFinalizerLoop` (`:305-371`): ở giây 2, nếu >50 % symbol chưa có WS final
  (`:324-328`) thì gọi REST sớm ngay; `earlyPass` (`:374-392`) log `Total = wsHave + nClosed` với `wsHave` chụp ở
  giây 2.0. `KlineIngestCore.earlyRest` (`:263-295`) bỏ các nến REST mà WS final đã tới trong lúc fetch
  (`:285-286`). Phút "thiếu" có `rest_som=0 rest_loi=0` (cả 400 REST trả nến M nhưng WS đã tới hết trong ~1,6 s),
  log ở giây 3,5-3,9 → mọi WS final đã có trước khi log. Phút "đủ" log ở giây 4,0x.
- Thống kê log collector 10-16..10-20 (6 720 phút): tỉ lệ phút "thiếu" 46,5 / 66,6 / 60,2 / 52,8 / 62,3 %;
  `rest_loi` tổng = 0; giây log (cận trên lúc đủ 738 WS final) p50 4,02 · p90 4,13 · p99 4,84 · max 43 (phút restart).
  `[KLINE-INGEST]` 10 phút/lần: `ws_final +7380` (=738/phút), `ws_late` ~3-4,5k/10' (ổn định 10-15→10-17, không đổi
  chế độ ở 10-17 02h), `rewritten_diff` gần như 0, `ws_conn=5/5`.
- Đo trực tiếp phía live (`LiveKlineAudit`, log `[LIVE-KLINE]` 10'/lần, 10-15..10-20, 8 169 phút quyết định):
  số ô (symbol, phút) trong ảnh chụp lúc quyết định = 738 × số phút ở **100 %** cửa sổ (0 cửa sổ thiếu);
  ô lệch so với bản đọc lại sau 3' = 0,01-0,5 %/ngày, tập trung thành đợt (WS reconnect / settle ghi đè).
- Không có restart live lúc 10-17 02:51. Restart (log `MainClass`): 10-16 16:03, 16:18, 17:22, 20:00:05;
  10-17 08:00:32, 14:51:18; từ đó 02:5x/14:5x. Collector (process riêng `BinanceDataIngestor`, `collectData`) restart
  08:4x/20:4x. Lệch P1 bắt đầu "10-17 03h" là do p15 (cây) chỉ đổi khi feature vượt ngưỡng tách; feature chéo
  lệch ~1 % ở **mọi** phút mọi ngày, kể cả 10-16.

**Nguyên nhân gốc = đường dựng input feature của live KHÁC backtest (code), không phải thời điểm dữ liệu.**

| | Live hiện tại | Backtest (`ExportGateDataset.replayToCsv` `:141-255`, `GenerateGate15mV2Predictions`) |
|---|---|---|
| Snapshot phút M đưa vào `HistoryManager`/`CoinRankManager`/extractor | `symbol2FinalTicker`: bỏ `diedSymbol` (`DetectEntrySignal2TradeNormal:216`) + bỏ nến phẳng không volume `!isTickerAvailable` (`:221`), last-ticker của cửa sổ 1000' → 635-737 symbol/phút | toàn bộ record phút M (738), không lọc |
| Ring `HistoryManager` (index-based, `processKline :102-116`) | thiếu nến các phút symbol bị lọc → MA20/RSI/sumVolume(720) lệch | đủ mọi phút |
| Universe xếp hạng `CoinRankManager.updateRanking :185-263` (`getAllSymbolsShort` = khoá snapshot cuối) | ~700 → basket top-50 % median 361 | 738 → 369 |
| Hạng giờ đầu sau restart | tính ngay tick đầu (`symbolTiers.isEmpty()` `:136`) trên ring seed | tính ở mốc giờ |
| Seed khởi động (`initData :1399-1418`) | 2000' không lọc, nạp 2 lượt (extractor + funding, cùng singleton) | replay liên tục 48h |
| `MarketDataObject` (momentum1M/15M) | tính từ cửa sổ live (`:213-266`, 15 entry cuối của list có cả nến phẳng) | `market_data_object` lưu sẵn (store chết từ 08-14) / `MarketDataInlineGenerator` |
| Funding giỏ (`FundingFeeManager`) | nạp lúc start + refresh 30' theo pha restart (`startProductionRefresh`) | toàn bộ lịch sử |

Bằng chứng tái lập (harness `V11FeatHarness`, Java, cùng class jar live, dữ liệu 1m ĐÃ settle đọc từ Aerospike 242,
cửa sổ 10-16 20:00 → 10-17 07:59 = 720 phút, seed theo restart 10-16 20:00:05):

| So sánh | ALL 33 feature ≤1e-6 | p15 ≤1e-6 | ghi chú |
|---|---|---|---|
| LIVE-emul vs feat_dump live | **92,2 %** | 95,7 % | `nsym` = `symbols:` trong log live 99,9 %; phần lệch nằm hết trong 10-17 07:00-07:55 (bên dưới) |
| BT (replayToCsv) vs feat_dump live | 0 % | 37,2 % (≤1e-3: 39,4 %) | basket trùng 0 %; = hiện tượng P1 |
| NEW (đường sửa) vs BT | **100 %** | **100 %** | basket trùng 100 % |
| BT Java vs Python devexport (offline parity) | 6,3 % | 65,4 % | breadth/basket/funding ≥ 99,9 %; **momentum15M 6,5 %**, rsi14 99,7 % |

Phần dư LIVE-emul vs live (đều giải thích được): 10-17 07:00-07:29 funding lệch (settlement 00:00 UTC ghi sau lần
refresh 07:00:12, refresh kế 07:30:11); 07:28-07:55 nhiều feature lệch do WS reconnect 07:29:00 → settle 07:29:33
ghi đè 14/25/18/19 nến các phút 07:28/07:29/07:30/07:35 sau khi live đã quyết định (đúng "unsettled" thật, hiếm:
8 lần settle ghi đè trong 10-16..10-20) và ring giữ bản cũ ~20'.

Phát hiện phụ: (a) Python `md_inline.py` (offline parity) ≠ Java `MarketDataInlineGenerator`: Python không lọc
`isTickerAvailable` khi nuôi buffer 15' và tính float64 (Java float32, TreeMap<Float> dedupe) → momentum15M chỉ khớp
6,5 %. (b) Store `market_data_object` chết từ 08-14 ⇒ tool Java đọc store (`GenerateGate15mV2Predictions:78`,
`ExportGate15mV2:73`, `WfoDataset`) cho kỳ gần đây nhận `rate=null` ⇒ momentum1M/15M = 0. ⇒ Nguồn sự thật của
MarketDataObject cho backtest CHƯA được chốt — MASTER cần chốt (đề xuất: Java `MarketDataInlineGenerator`, sửa
md_inline.py cho khớp).

## 2. Thiết kế fix (mọi thay đổi sau cờ; mặc định = hành vi cũ byte-identical)

### F-input (cờ `LIVE_FEAT_INPUT=legacy|snapshot`, mặc định `legacy`)
Khi `snapshot`, đường feature (HistoryManager + CoinRankManager + ComprehensiveMarketFeatureExtractor) được nuôi
**đúng như `replayToCsv`**: mỗi phút mới M (theo thứ tự, kể cả phút bị lỡ tick) lấy snapshot ĐẦY ĐỦ của record phút M
(từ cache `LiveTickerWindow`, cùng object), gọi `updateHistory(snap)` + `getTopCoin(M)`; phút quyết định gọi
`extractAllFeatures(M, snap, md)`. Khởi động: seed 2000' bằng replay từng phút (1 lượt, có `getTopCoin` từng phút)
→ hạng giờ đầu sau restart = backtest. Không gọi `fundingExtractor.updateMarketHistory(symbol2FinalTicker)` nữa
(pipeline đã nuôi cùng singleton). **Không đổi** tập ứng viên giao dịch (`symbol2FinalTicker`, cascade, selector).
Lớp mới: `LiveFeaturePipeline` (thuần, test được).

### F-md (cờ `LIVE_FEAT_MD=inline|legacy`, mặc định `inline` khi snapshot) + (cờ `LIVE_MD_SOURCE=legacy|inline`, mặc định `legacy`)
Feature momentum1M/15M lấy từ `MarketDataInlineGenerator` nuôi bằng cùng snapshot (cùng `calMarketData`).
`LIVE_MD_SOURCE=inline` mới thay rate dùng cho `levelChange`/`predictAllCandidates` (đổi quyết định market-level ⇒
mặc định TẮT, MASTER quyết riêng). Generator trả null (guard) ⇒ dùng rate legacy cho phút đó + WARN đếm.

### F-settle (chỉ khi snapshot)
Trước khi tính phút M: `LiveTickerWindow.awaitMinuteComplete(M, expected, timeout, poll)`; `expected` = số symbol
phút M-1 − `LIVE_FEAT_SETTLE_TOL` (mặc định 3, cho delist). Thiếu ⇒ đọc lại record M mỗi `LIVE_FEAT_SETTLE_POLL_MS`
(250) tới khi đủ hoặc hết `LIVE_FEAT_SETTLE_TIMEOUT_MS` (mặc định 3000 ⇒ xong trước giây ~9-10, trong lưới 6-10).
Hết timeout ⇒ tính trên dữ liệu đang có + `WARN [FEAT-SETTLE] partial=true` + đếm; INFO tổng mỗi 60'.
Timeout chọn theo đo: đủ 738 WS final p99 4,84 s, live đọc ở 6 s, 0/8 169 phút thiếu ⇒ bình thường không chờ.
**Không** chờ tới settle REST 30 s: sim vào lệnh bằng close nến quyết định (`EntryCost`: giá vào = close × (1+cost));
live đã trễ 6-10 s; chờ 30 s làm lệch giả định vào lệnh + cost bucket đã đo. Thay vào đó:

### F-repair (chỉ khi snapshot)
`LiveTickerWindow` đọc lại 3' (KFIX-B): nến khác ⇒ **ghi đè tại chỗ** object đang có (thay vì thay object) ⇒ ring
HistoryManager, buffer MarketDataInlineGenerator cùng nhìn bản settle từ phút M+2 trở đi (đúng như backtest).
`LiveKlineAudit` chụp bản sao giá trị (không giữ tham chiếu) để thước vẫn đúng.

### F-fund (cờ `LIVE_FUNDING_REFRESH_HOURLY=0|1`, mặc định 0)
Bật: ngoài refresh 30', refresh thêm ở hh:00:50, hh:01:50, hh:02:50 (ingester poll 30 s + flush 60 s ⇒ record
settlement có trong ≤ ~90 s). Lệch funding còn ≤ 1-2 phút quyết định/settlement thay vì tới 30'.

### Tie-break xác định
- Live: `TieSafeRank.build(Map<sym,score>)` — thứ tự (score tăng, symbol tăng), KHÔNG mất coin; khoá TreeMap tăng
  ngặt (trùng ⇒ `Math.nextUp` của khoá trước, lệch ≤ vài ulp) để giữ nguyên kiểu `TreeMap<Float,String>` downstream.
  Áp cho `buildS1Pool` (S1) và `selectorRankPool` (tier-1), cờ `LIVE_RANK_TIEBREAK=legacy|symbol` (mặc định legacy).
- Backtest Python (`s1_off.py rank_first`, `build_map.py` rank "first" trên danh sách symbol đã sort) = (score, symbol) ⇒ khớp.
- Sim Java (`SimulatorMarketLevelTicker1MStopLoss.quickSortByFloatPred/partition :1888-1918`) = quicksort KHÔNG ổn
  định chỉ theo float ⇒ trùng score phụ thuộc thứ tự mảng vào. Sửa sau cờ `SIM_RANK_TIEBREAK_SYMBOL` (mặc định 0):
  sort (score, tên symbol).
- KHÔNG đổi các TreeMap rate (`rateDown2Symbols`…): backtest `calMarketData` có cùng ngữ nghĩa dedupe.

### Log / dump
- `[GATE-RATIO]` giữ `q_t=%.6f` (không vỡ parser) + thêm `q_t9=%.9g`.
- `S1FeatDump` (cờ `LIVE_S1_DUMP`=N phút/lần; mặc định = 1 nếu `LIVE_FEAT_DUMP>0` (shadow) ngược lại 0):
  `s1_dump/s1_dump_<yyyyMMdd_HH>.csv.gz` cột `ts,symbol,f0..f8,score,oi_ref_ts,oi_hour,oi_loaded_ms,oi_src`,
  xoay theo giờ, trần 200 MB/file. Ước tính ~676 dòng × ~150 B ≈ 100 KB/phút thô ⇒ ~140 MB/ngày thô, ~35-45 MB/ngày nén.

## 3. Kiểm
- Unit: TieSafeRank (trùng score, nextUp dây chuyền, NaN), sim tie sort, LiveTickerWindow await/timeout/in-place,
  format q_t9, dòng S1 dump.
- Offline: harness gọi CHÍNH `LiveFeaturePipeline` của jar mới trên 720 phút (+ cửa sổ thứ 2) vs `replayToCsv`:
  tiêu chí ALL33 ≤1e-6 ở 100 % phút, basket trùng 100 %. Đã đạt với bản mô phỏng (bảng §1).
- Chưa kiểm: 45 feature funding/net015 so backtest (cần tool train export), md_inline Python (ngoài phạm vi jar).

## 4. Rủi ro deploy
- CPU/bộ nhớ: +1 Map/phút (738 tham chiếu), MarketDataInlineGenerator ~738 list ≤100 nến; seed 2000' thêm getTopCoin
  từng phút (~33 lần updateRanking). Không thêm đọc Aerospike khi đủ; thiếu ⇒ ≤12 lần đọc 1 record/phút.
- Hành vi đổi khi bật: p15/gate/S1-funding-45 đổi giá trị (về phía backtest) ⇒ reset cửa sổ promotion như owner đã quyết.
- Funding refresh hourly: +3 × 887 get/giờ.

## 5. Kết quả code + kiểm (2026-10-20, sau commit thiết kế 6d301418)

- Code: nhánh `v1.1/collector-settle` commit `90482c38` (worktree Oracle `~/claude_master/v11_settle/wt`, không push).
  Jar `2069db61e86e0c77afc03f87b6447b31` (bản sao `~/claude_master/v11_settle/jar/`). So với `dc839568`: chỉ đổi
  LiveTickerWindow, LiveKlineAudit, LiveGateRollingRatio, FundingFeeManager, Simulator…StopLoss, S1RankerLive,
  DetectEntrySignal2TradeNormal(+TickGate, +$1) và thêm LiveFeaturePipeline, TieSafeRank, S1FeatDump.
- `mvn -o package`: 343 test, 0 fail, 1 skip (có sẵn). Test mới: LiveFeaturePipelineTest 4, LiveTickerWindowSettleTest 5,
  TieSafeRankTest 4, V11SmallTest 4.
- Kiểm offline (harness `V11FeatHarness` mode NEW2 = gọi CHÍNH LiveFeaturePipeline + LiveTickerWindow(in-place, await)
  của jar mới, dữ liệu settle 242):

| cửa sổ | NEW2 vs replayToCsv: ALL33 ≤1e-6 | p15 ≤1e-6 | basket | LIVE-emul vs live dump ALL33 / p15 | BT vs live dump p15 ≤1e-3 |
|---|---|---|---|---|---|
| 10-16 20:00 → 10-17 07:59 (720', restart 20:00:05) | 100 % | 100 % | 100 % | 92,2 % / 95,7 % | 39,4 % |
| 10-17 08:00 → 14:50 (411', restart 08:00:32) | 100 % | 100 % | 100 % | 94,2 % / 99,5 % | 24,6 % |

- Chưa kiểm: 45 feature funding/net015 so backtest; md_inline.py (Python) vẫn lệch Java (momentum15M 6,5 % / 26 %).
- Không bật cờ nào ⇒ hành vi giao dịch như cũ; khác duy nhất: dòng `[GATE-RATIO]` có thêm `q_t9`, và S1 dump TỰ BẬT khi
  `LIVE_FEAT_DUMP>0` (đặt `LIVE_S1_DUMP=0` để tắt).
- Cờ đề xuất khi deploy v1.1: `LIVE_FEAT_INPUT=snapshot`, `LIVE_RANK_TIEBREAK=symbol`, `LIVE_FUNDING_REFRESH_HOURLY=1`;
  `LIVE_MD_SOURCE` để mặc định (legacy) chờ MASTER quyết; backtest đối chiếu chạy với `SIM_RANK_TIEBREAK_SYMBOL=1`.

## 6. Ba kiểm tra trước deploy (yêu cầu MASTER 2026-10-20, chỉ đọc 242)

Code: nhánh `v1.1/collector-settle` commit `66cb6196` (trên `90482c38`), jar **`d7824f6d1a622d013c4579e70c85691a`**
(`~/claude_master/v11_settle/jar/binance-java-sdk-1.2.4.jar_v11b_d7824f6d`); `mvn -o package` 345 test, 0 fail.
Kết quả máy đọc: `~/claude_master/v11_settle/harness/md_cmp.json`, `md_py_validate.json`, `s6/fund_cmp.json`.

### 6.1 Nguồn chuẩn MarketDataObject (momentum1M/15M, rate levelChange)

Truy ngược:

| tiêu thụ | đọc từ | sinh bởi |
|---|---|---|
| sim DEV/HO (`market.bin` của `wfo_ds_override`, md5 `0fcc44d8…`, 2.947.528 dòng 2021-01 → 2026-09-30) | ts < 2026-01-01: = DEV bundle `~/wfo_ds_x1_2021/market.bin` md5 `4ab691c9…` (bit-exact 100 %, 2.554.408 dòng); 2026: 393.120 phút regen từ Vision (`docs/result/ho4/HO4_P1.md` §market) | DEV bundle = `WfoDataset.export` (`:66` `getAllMarketDataFromAerospike()`) = store `market_data_object` (Oracle `aerospike-wfo`, ns `test`); store ghi bởi `ExportMarketData2File.exportMarketEntries` (Java: bỏ `diedSymbol` + `!isTickerAvailable`, buffer liên tục 15 nến, `calMarketData` float32) |
| train gate p15 (`fold_20`, md5 `8ec99757…`) | `WFOGateRunner` → `ExportGateDataset.replayToCsv` (`:143` `getAllMarketDataFromAerospike()`) | cùng store |
| train funding Tool1 (net015) | `ExportTool1Worker:59` `getAllMarketDataFromAerospike()` → `ExportFeaturesForPythonTool.extractFeatures(..., time2MarketData.get(time), ...)` | cùng store |

Đo trực tiếp (harness `V11MdHarness`: Java `MarketDataInlineGenerator` trên ticker 242, bỏ 60′ warm-up):

| ngày | died = `BTCDOM,USDC` vs store / DEV / sim | died = DIED_SYMBOLS dài của live 242 | md_inline.py CŨ | md_inline.py MỚI vs Java |
|---|---|---|---|---|
| 2021-03-01 (1.378′) | **100 % / 100 % / 100 %** bit-exact | 0 % | 85,8 % (≤1e-7) | **100 %** bit-exact |
| 2024-06-01 (1.374′) | **99,85 % / 99,78 % / 99,78 %** | 0 % | 53,1 % | **100 %** bit-exact |
| 2026-08-08..12 (6.907′) | store 0,01 % / sim(Vision) 49 % | 0 % / 1,3 % | — | — |

(2026-08: ticker 242 trước KFIX 10-10 khác ticker đã sinh store/Vision — lệch do dữ liệu, không do công thức.)

**Kết luận:** chuẩn = Java `calMarketData` / `MarketDataInlineGenerator` với died **{BTCDOM, USDC}**, lọc
`isTickerAvailable`, float32, buffer liên tục. Train (gate + Tool1) và sim đọc **cùng một store** ⇒ ở cấp code nguồn train = nguồn sim.
Live 242 khai DIED_SYMBOLS dài ⇒ cả rate legacy lẫn inline-mặc-định của live đều ≠ nguồn ⇒ v1.1 thêm
`LIVE_MD_DIED_SYMBOLS` (mặc định `BTCDOM,USDC`) chỉ cho đường snapshot. `md_inline.py` KHÔNG phải nguồn (port audit,
thiếu lọc isTickerAvailable + float64) ⇒ đã sửa (exact mặc định; 4 cột cũ ⇒ ValueError có chủ đích; `exact=False` = số cũ);
3 caller devexport truyền 5 cột.

Rủi ro provenance (chưa đóng): bản sao `gate15m_v2_full.csv` duy nhất còn lại (D:\claudedata\_TO_DELETE_20260810, 06-23,
md5 `7ef6f92b…`, 189.765 dòng 15′) khớp store ở 2025 99,4 % nhưng 2021–2023 ≈ 0,1 %, 2024 34 % ⇒ store 2021–2024 đã được
sinh lại sau 06-23. Store huấn luyện thật của `fold_20` (WFOGateRunner 08-06/08-18, `fs_full.csv`) không có trên Oracle/Windows
⇒ chưa xác nhận fold_20 học momentum 2021–2024 từ bản store nào. Đề xuất: kiểm `fs_full.csv` trên Kaggle với `md_inline` mới.

Phải tính lại (dùng md_inline cũ và/hoặc died 242): PARITY_1020 (`devexport_1020 --md-inline --died-config raw242`:
momentum1M/15M/Acceleration + p15 offline ⇒ bảng P1), SHADOW_PARITY_FEAT_1016 (`devexport_1016`), kết quả dùng
`devexport_202609 --md-inline` (RESULT_FEATDIFF_PASS2), HO3_B1B2 (`ho3_b2_market.py`, died đúng nhưng chưa lọc
isTickerAvailable), KDOSE (`kdose_run.py` tự kiểm với md_inline cũ), `parity_check.py`, PARITY_242_VS_G2FLAT3,
RESULT_PARITY_HARNESS_V2. Sim/backtest Java KHÔNG phải tính lại.

### 6.2 45 feature funding / net015 ở chế độ snapshot

v1.1 bổ sung (chỉ khi `LIVE_FEAT_INPUT=snapshot`): `extractFeatures` + `EntrySignalFilter.selectCoins` dùng snapshot đầy đủ
+ rate feature (inline, died nguồn); hạng cross-sectional #33–#35 tính trên TOÀN BỘ coin qua filter như
`ExportFeaturesForPythonTool` (live trước đây chỉ xếp trên ứng viên). Backtest so sánh = vòng Tool1 (updateMarketHistory full
→ getTopCoin → selectCoins → extractFeatures(store-equivalent md) → applyCrossSectional), mỗi phút. OI #41–45 = NaN ở cả hai.

| cửa sổ | NEW2 vs Tool1: dòng (phút, coin) #1–#40 ≤1e-6 | phút khớp toàn bộ | net015 1−P(win) ≤1e-6 | legacy vs Tool1 (dòng / phút / net015) |
|---|---|---|---|---|
| 10-16 20:00 → 10-17 07:59 | **100 %** (24.051/24.051) | **100 %** (720) | **100 %** | 0 % / 0 % / 37,7 % (p99 |Δ| 0,025) |
| 10-17 08:00 → 14:50 | **100 %** (9.985/9.985) | **100 %** (411) | **100 %** | 0 % / 0 % / 36,4 % (p99 0,021) |

Mọi coin Tool1 đều là ứng viên live trong 2 cửa sổ (không coin nào cần thêm chỉ để xếp hạng). 33 feature gate NEW2 vs
backtest (md nguồn): 100 %, p15 bit-exact 100 %, basket 100 %. **Chưa đo:** (a) OI #41–45 (live tra set `oi_feat_*` 242 tính
sẵn; Tool1 dùng `ExportFundingOiPerCoin` trên metric thô 226 — hai pipeline khác, ngoài phạm vi snapshot); (b) gateValue
sau quantile-map (phụ thuộc thứ tự S1, đo riêng với tie-break); (c) độ trễ cache funding live (harness dùng lịch sử đầy đủ;
`LIVE_FUNDING_REFRESH_HOURLY=1` còn dư ≤1–2 phút/settlement).

### 6.3 Legacy jar mới ≡ jar dc839568

Harness LIVE (đường live hiện tại) build trên jar cũ vs jar mới, không bật cờ: 33 feature **bit-exact 100 %**, p15
bit-exact 100 %, basket 100 %, funding-45 bit-exact 100 % (24.163 + 10.034 dòng), cả 2 cửa sổ. Khác biệt duy nhất khi không bật
cờ: dòng `[GATE-RATIO]` thêm `q_t9`; S1 dump tự bật nếu `LIVE_FEAT_DUMP>0` (tắt bằng `LIVE_S1_DUMP=0`).

### 6.4 Env đề xuất cuối (`/home/chuyennd/java/v_t_m/conf/env.sh`)

```
export LIVE_FEAT_INPUT=snapshot
export LIVE_FEAT_MD=inline
export LIVE_MD_DIED_SYMBOLS=BTCDOM,USDC
export LIVE_MD_SOURCE=inline            # rate cho levelChange/BIG_DOWN/DCA = nguồn sim (đổi quyết định market-level)
export LIVE_RANK_TIEBREAK=symbol
export LIVE_FUNDING_REFRESH_HOURLY=1
# LIVE_S1_DUMP: để mặc định (theo LIVE_FEAT_DUMP)
```
Backtest đối chiếu: `SIM_RANK_TIEBREAK_SYMBOL=1`. Nếu MASTER chưa muốn đổi quyết định market-level: `LIVE_MD_SOURCE=legacy`
(feature vẫn khớp nguồn; BIG_DOWN/DCA giữ rate live cũ, KHÁC sim).

### 6.5 Rủi ro mới
- `LIVE_MD_SOURCE=inline` đổi tín hiệu BIG_DOWN/DCA về phía sim (rate tính trên 738 symbol với died nguồn).
- Provenance train 2021–2024 (6.1) chưa đóng.
- OI #41–45 và gateValue sau quantile-map chưa đo parity.
- `md_inline.py` exact: caller 4 cột (ho3_b2_market, kdose_run, kline_242_div, featdiff_pass2_p15, parity_check) sẽ lỗi rõ cho tới khi truyền totalUsdt.
- Thêm CPU nhỏ: funding cho coin qua filter nhưng không là ứng viên (0 coin trong 2 cửa sổ đo).
