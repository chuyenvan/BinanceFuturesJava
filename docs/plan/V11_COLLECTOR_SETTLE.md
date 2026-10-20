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
