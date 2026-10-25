# SYMLIFE_AUDIT — vòng đời symbol: backtest X14 và live 242 (2026-10-25)

Phạm vi: chỉ đọc và đo, KHÔNG sửa code. Code = `v1.1/exec-probe` @16de49a6 (jar đang chạy trên 242). Dữ liệu: Binance Vision (listing S3 + file kline 1m tải về rồi bỏ), `~/vz_e1/raw` (2021-12→2025-12), printDone X14 8 seed, pull242 10-21..10-24.
Agent: symlife. Bối cảnh: owner 10-25 yêu cầu “backtest phải có time-life symbol; live phải lấy FULL symbol not-died”.

## 0. TL;DR (xếp theo rủi ro)

| # | Mức | Phát hiện | Số đo | Ảnh hưởng |
|---|---|---|---|---|
| L1 | **CAO (live, mới)** | Universe live hiện có **TradFi perps** (cổ phiếu/ETF/FX/KRX/HK) mà backtest DEV 2022–25 chưa bao giờ thấy | 274 symbol niêm yết 2026 đang TRADING; ≥113 symbol có <1200 phút giao dịch/ngày (gần như toàn bộ TradFi niêm yết 2025-12+); 36–40/206–234 ứng viên psym mỗi ngày là loại này; **shadow C3 đã mở IBKRUSDT ngày 10-24** (cổ phiếu Interactive Brokers, niêm yết 10-21) | Lệch phân phối với mô hình + market level; chưa có backtest nào cho loại tài sản này |
| L2 | TB (live) | `DIED_SYMBOLS` tĩnh **chặn nhầm symbol còn sống**, ngay tại ingest | 4/143 còn TRADING ngày 10-23: BTCDOM, USDC (cố ý), **POWR** (sống từ 2023-10), **MDT** (relist 2026-10-21 sau SETTLED 10-13) | Live mất 2 coin hợp lệ; trong DEV hai coin này có 66 leg, PnL +1 202 (0,13 %) |
| L3 | TB (live) | Regex `^[A-Z0-9]+$` loại mọi symbol tên không phải ASCII | 5 symbol đang TRADING: 哈基米, 币安人生, 我踏马来了, 牛来, 龙虾 (USDT) | Mất 5 coin meme; 0 leg trong DEV (CHƯA XÁC MINH sim có loại chúng không) |
| L4 | TB (live, vận hành) | Paper book bỏ qua cụm vị thế khi thiếu giá: không time-stop, không đóng | `ShadowBookC3.java:388-389` `if (pxObj == null …) continue;` | Nếu symbol bị delist giữa lúc giữ thì cụm kẹt mãi, vẫn tính vào exposure; vị thế thật chưa có reconcile (C9) |
| L5 | TB (live) | Không có cơ chế nhận biết delist sắp xảy ra (không đọc exchangeInfo `status`/`deliveryDate`) | — | Live vẫn mua coin đã có thông báo delist; trong DEV 389 leg (1,65 %) vào ≤7 ngày trước delist |
| B1 | THẤP (backtest) | **Không có lỗi vòng đời**: 0 leg vào trước niêm yết, sau delist, trong khoảng relist hoặc vào ngày 0 giao dịch | 23 583 leg DEV × 8 seed | Sim đúng PIT nhờ “có ticker tại t”, không nhờ danh sách |
| B2 | THẤP (backtest) | Vị thế giữ qua delist được đóng ở **giá cuối đóng băng** (nến zombie) khi time-stop chạy, không phải lúc delist | 100 leg (0,42 %), 9 symbol, PnL −8 850 (−0,96 % tổng PnL), giữ thêm 2,3–381 giờ sau giao dịch cuối | PnL gần đúng (Binance settle ≈ giá cuối), nhưng vốn bị khoá thêm nhiều ngày |
| B3 | TB (độ tin kết quả) | **Alpha dựa nhiều vào coin mới niêm yết** | Vào <24h sau niêm yết: 1,53 % leg, 3,17 % PnL, pnl/notional 5,6 % (so với 3,7 % khi ≥30 ngày). <7 ngày: 7,8 % leg / **10,3 % PnL**. <30 ngày: 19,4 % leg / **28,0 % PnL** | Trượt giá và thanh khoản lúc mới niêm yết không được mô hình hoá; đợt 2025-10-10 riêng 260 leg <7 ngày đóng góp +22 756 |
| D1 | ghi chú | `20,3 % leg / 17,7 % PnL rơi vào DIED live` (D2B) tách được: **19,95 % / 17,44 % là coin đã delist nhưng lúc vào còn sống (ĐÚNG, không phải lỗi)**; 0,28 % / 0,13 % là coin vẫn sống (POWR, MDT) | — | Không cần sửa số X14 vì lý do này |
| D2 | ghi chú (dữ liệu research) | Raw `~/vz_e1/raw` thiếu giao dịch 2022-02-26..28 ở 48 symbol cũ, dù Vision có file | — | Chỉ ảnh hưởng nghiên cứu dùng raw; sim không bị (0 leg trong khoảng này). Nguyên nhân CHƯA GIẢI THÍCH |

Kết luận: **backtest X14 không có lỗi vòng đời làm phồng kết quả**. Nhóm 20,3 % đã báo là survivorship-free đúng thiết kế. Rủi ro thật nằm ở **live**: universe lấy từ `/fapi/v1/ticker/price`, rồi lọc bằng regex và DIED tĩnh. Kết quả là live bỏ nhầm 2 coin sống và 5 coin tên non-ASCII. Đồng thời live **tự động nạp TradFi perps** mà không có chính sách và không có backtest cho loại này. Ngoài ra live không có guard khi delist.

## 1. Phương pháp và validation

- **Vision listing** (`research/symlife/vl.py`): 1 069 thư mục daily kline UM, 747 343 file ngày (+1 056 thư mục monthly), chụp lúc 2026-10-25 04:03 UTC. File cuối của BTC là 2026-10-23, nghĩa là 10-24 chưa phát hành.
- **Phát hiện quan trọng về Vision**: sau khi delist, Vision **vẫn tiếp tục phát hành file kline “zombie”**: nến phẳng, `count=0`, khoảng 8 KB so với khoảng 50 KB của ngày thật. 151/164 symbol đã ngừng giao dịch vẫn có file đến 10-23 (FTM, OCEAN, RAD…). ⇒ **“có file” không có nghĩa là “còn sống”**. Vì vậy lifecycle được đo theo **phút có `n_trades>0`**:
  - 2021-12→2025-12: lấy từ raw (`rl.py`, `rl2.py`), chính xác đến phút.
  - 2026: tải file Vision (`dl.py`). Gồm 2 643 file của các ngày 10-21..23, binary search ngày giao dịch cuối cho 137 symbol đã chết và file ngày đầu cho 276 symbol niêm yết từ 2025-12-31. Tổng 4 027 file, 0 lỗi.
  - Trước 2021-12: dùng biên theo ngày của Vision. Mức này đủ cho DEV 2022–25.
- **V1** raw so với Vision: ngày niêm yết khớp 500/501 symbol (1 symbol lệch 1 ngày). Ngày file cuối khớp 25/25 symbol có file dừng trước 2025-12.
- **V2** (độc lập, dùng curl+awk, không qua pipeline) kiểm 7 biên delist: FXS 01-06, STG 09-24, EPIC 10-20, TON 06-23, 1000000BOB 10-05 đều có ngày cuối còn trade và ngày sau 0 trade. POWR 10-23 có 1 436 phút trade. MDT có 10-12 = 0 trade, 10-14 = 404, 10-21 = 588 phút trade. **7/7 khớp**.
- **V3** danh sách DIED: md5 dòng `DIED_SYMBOLS` (143 symbol) = bản `v11_settle/harness/config.properties`, là bản harness dùng cho parity. Đây là bản sao config 242 theo D2B. Chưa đối chiếu được file đang chạy trên 242 (luật cứng: không đụng 242), xem §9.
- **V4** tính lại tỉ lệ DIED trong DEV: 20,23 % leg / 17,57 % PnL, khớp con số 20,3 / 17,7 của D2B (khác nhỏ do định nghĩa cửa sổ DEV: entry 2022-01-01..2025-12-31 UTC). Theo từng seed: 19,97–21,02 % leg, 15,90–19,08 % PnL.
- **V5** live: universe S1 theo ngày (union) không chứa symbol nào ngoài tập Vision TRADING (THỪA = 0). Điều này xác nhận `/fapi/v1/ticker/price` không trả symbol đã delist.
- ts luôn là int64 ms. printDone `start/end` ở giờ +07, đã trừ 7h. notional = quantity×entry (lev 1).

## 2. A1 — Bảng lifecycle PIT

File `docs/result/symlife/lifecycle_usdt.csv` (912 USDT-M perp). Bản đầy đủ có ts: `~/claude_master/symlife_wk/lifecycle.parquet`. Các cột: `first_utc`/`last_utc` là phút giao dịch đầu/cuối (để trống nếu còn sống), `status_now` (TRADING khi file 10-23 có trade), `zombie_files_after_last`, `trade_gaps_ge3_raw`, `settled_events`.

- 912 perp USDT: **748 TRADING**, **164 STOPPED** (theo năm: 2020:1, 2021:2, 2022:14, 2023:3, 2024:29, 2025:47, 2026:68). Đa số delist vào **~09:00 UTC**.
- **Ticker tái dùng / relist** (khoảng 0 giao dịch ≥3 ngày nằm giữa đời, trong raw): AERGO (2025-03-28..04-15), BNX (2023-02-01..21), CTK (2024-04-02..2025-04-29, 393 ngày), CVC (2022-11-30..2025-05-15, 898 ngày), CVX (2024-05-15..2025-07-22), ICP (2022-06-11..09-26), LIT (2025-02-01..12-22), MAVIA (2024-12-17..2025-03-25), PUMP (2025-06-14..07-09), SLP (2024-05-16..2025-07-22), TLM (2022-06-10..2023-03-29). Vision đánh dấu bằng thư mục `*SETTLED` (17 sự kiện, gồm cả 2026: AIA 01-20, BDXN 04-28, SXP 06-02, AERGO 07-24, BTCST 07-30, **MDT 10-13**).
- Non-ASCII: 5 symbol, cả 5 đều TRADING.

## 3. A2 — Code sim: universe và delist (file:dòng, `research/SimulatorMarketLevelTicker1MStopLoss.java` = SIM)

- Ticker mỗi ngày: SIM:216-233. `TICKER_SOURCE=aerospike` → `readDataFromAerospike1M_ShortKey`, `file` → `KaggleDataLoader.loadDailyTickersShort` (KaggleDataLoader.java:101-124, map tên→id qua `SimpleSymbolMapper`). **Universe tại t = mọi symbol có record phút t** trong dữ liệu. Không có danh sách cố định, không gọi lifecycle.
- Chọn mua: SIM:376-379 → `MarketBigChangeDetector.getTopSymbolArray` (MarketBigChangeDetector.java:132-152). Hàm duyệt `predict2Symbol` theo điểm và chỉ cần `symbol2FinalTicker[id] != null`. Không kiểm `isAlive`, không kiểm `isTickerAvailable` (nến zombie phẳng vẫn khác null). Trên thực tế thì 0 leg vào ngày 0 giao dịch, vì không có prediction hoặc không vượt ngưỡng (bằng chứng ở §4), nhưng code không chặn.
- DIED trong sim: `DIED_SYMBOLS=BTCDOM,USDC` (config tsx-x14), cố ý chống survivorship.
- Cập nhật vị thế: SIM:262-266 chỉ chạy `startUpdateOldOrderTrading` khi `ticker != null`. Time-stop thua lỗ 168h ở SIM:1153-1168. TS_MKT_EXT hoãn time-stop tối đa +336h.
- Delist: SIM:497-505 kiểm mỗi giờ (trừ phút 00:00 UTC): `!Utils.isTickerAvailable(ticker)` (Utils.java:457-463: min==max và totalUsdt==0) dẫn tới `updateSymbolDeListed` (SIM:1025-1033). Hàm này **chỉ đóng nếu `timeUpdate < time − 2 ngày`**, với giá `lastPrice`, trạng thái STOP_LOSS_DONE. Khi dữ liệu có nến zombie (ticker khác null), `startUpdateOldOrderTrading` vẫn chạy và làm mới `timeUpdate`, nên nhánh delist không bao giờ kích hoạt. Vị thế được đóng bởi time-stop ở giá đóng băng. Số đo khớp: giữ 159–167h sau leg đầu (MATIC, PERP, FLM, STRAX); FTT/RAY 374–381h do TS_MKT_EXT hoãn.
- Có sẵn nhưng sim/live không dùng: `ai_ml/data/SymbolLifecycleManager` (`isAlive(symbol,t)` dòng 132, `getStatus` dòng 161/174, set Aerospike `symbol_lifecycle` dòng 30), chỉ `ExportFundingLabel` dùng. Builder (TASK-010) đo bằng data 226 + exchangeInfo.

## 4. A3 — Đo trên printDone X14 (DEV 2022–25, 8 seed cộng gộp, 23 583 leg, notional 24,34 M, PnL +925 538)

| Kiểm | leg | % leg | % notional | PnL | % PnL | n sym |
|---|---|---|---|---|---|---|
| Symbol không có trên Vision | 0 | 0 | 0 | 0 | 0 | 0 |
| **LỖI entry < first_trade_ts** | **0** | 0 | 0 | 0 | 0 | 0 |
| **LỖI entry > last_trade_ts** | **0** | 0 | 0 | 0 | 0 | 0 |
| **LỖI entry trong gap relist ≥3 ngày** | **0** | 0 | 0 | 0 | 0 | 0 |
| Giữ vị thế qua gap relist | 0 | 0 | 0 | 0 | 0 | 0 |
| Entry vào ngày symbol 0 giao dịch | 0 | 0 | 0 | 0 | 0 | 0 |
| Exit sau last_trade (giữ qua delist) | 100 | 0,42 | 0,24 | −8 850 | −0,96 | 9 |
| Entry ≤1 ngày trước delist | 74 | 0,31 | – | −924 | −0,10 | 8 |
| Entry ≤7 ngày trước delist | 389 | 1,65 | – | +2 167 | 0,23 | 18 |
| Symbol thuộc DIED live (143) | 4 771 | 20,23 | 17,75 | +162 629 | 17,57 | 107 |
| ↳ đã delist (lúc vào còn sống: ĐÚNG) | 4 705 | 19,95 | 17,45 | +161 427 | 17,44 | 105 |
| ↳ vẫn TRADING (POWR, MDT) | 66 | 0,28 | 0,29 | +1 202 | 0,13 | 2 |
| Đã ngừng nhưng KHÔNG thuộc DIED | 937 | 3,97 | 3,52 | +33 642 | 3,63 | 23 |
| Entry <24h sau niêm yết | 360 | 1,53 | – | +29 341 | 3,17 | 32 |
| Entry <7 ngày sau niêm yết | 1 845 | 7,82 | 10,58 | +95 541 | 10,32 | 164 |
| Entry <30 ngày sau niêm yết | 4 581 | 19,43 | 25,30 | +259 558 | 28,04 | 301 |

- Exit sau delist: AKRO, ANC, FLM, FTT, LUNA, MATIC, PERP, RAY, STRAX. Chi tiết ở `legs_exit_after_delist.csv`. FLM/PERP được mua ngày 2025-11-21 lúc 07:36 UTC, tức **1h23′ trước delist 09:00**. Đây là loại lệnh mà trader thật đã biết trước qua thông báo.
- Coin mới niêm yết: winrate 0–24h 93,9 %, pnl/notional 5,6 %; 24–72h 3,2 %; 72–168h 3,2 %; 7–30 ngày 4,6 %; ≥30 ngày 3,7 %. Tỉ trọng PnL từ coin <7 ngày khá ổn định giữa các seed (9,8–11,1 %). Ví dụ: GAL được mua 68′ sau khi niêm yết (2022-05-05). Đợt 2025-10-10 mua 4, YB, KGEN, GIGGLE, MON, LYN chỉ vài giờ đến vài ngày sau niêm yết.
- Danh sách theo symbol: `legs_died_live_by_symbol.csv`. Đứng đầu: BLZ 186 leg, UNFI 151, FTM 133, REN 116, TOMO 110. Toàn bộ đều đã delist và được mua khi còn sống.

## 5. B1 — Code live: universe lấy từ đâu (file:dòng)

1. **Collector** `websocket/TickerIngestor2AerospikeNew.java`: mỗi nhịp gọi `GET /fapi/v1/ticker/price` (dòng 104). Symbol được giữ nếu `endsWith("USDT") && matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains` (dòng 134), sau đó dựng nến phút và ghi Aerospike 242. Repair dùng tập Redis `REDIS_KEY_BINANCE_ALL_SYMBOLS` với cùng bộ lọc (dòng 511-520). Symbol mới được ghi Redis và đặt leverage ở `initNewSymbolConfig` (dòng 583-588). Funding (`FundingIngestor2AerospikeNew:76`) và OI (`OpenInterestIngestor2AerospikeNew:126`) cũng lọc DIED, nên POWR/MDT không có funding/OI.
2. `Constants.java:59-65`: `DIED_SYMBOLS` nạp **một lần trong static init** (thêm hậu tố USDT). Muốn đổi phải restart từng process.
3. **App trading**: `LiveTickerWindow` đọc record phút từ Aerospike (`DetectEntrySignal2TradeNormal`, viết tắt DES, dòng 84 và 206). DES:226 bỏ DIED thêm lần nữa. DES:237 bỏ coin giảm >15 %/phút khi BTC không giảm (heuristic “delist/warning”). DES:306 log `symbols:N`. `TickWeakBlock.java:183` lọc DIED. `MarketBigChangeDetector.java:50` gọi `calMarketData(…, Constants.diedSymbol)`.
4. `LiveFeaturePipeline.java:37-39,171`: MarketDataObject của feature dùng `LIVE_MD_DIED_SYMBOLS` (mặc định `BTCDOM,USDC`), giống nguồn train. Tuy nhiên snapshot đầu vào **đã thiếu các DIED** từ lúc ingest (bước 1), nên POWR/MDT vẫn không xuất hiện.
5. **Không có chỗ nào đọc exchangeInfo `status`/`deliveryDate`** trong luồng live. `BudgetManager.getAllSymbol()` (BudgetManager.java:117-125, dùng exchangeInfo + `TRADING`) là private và không có caller. `ClientSingleton.getAllSymbol()` lấy từ cache LOT_SIZE.
6. Cập nhật: symbol mới vào universe **tự động, không cần restart**, vì ticker/price được gọi mỗi nhịp và mapper cấp id động (`SimpleSymbolMapper.getId`, CAS). Độ trễ đo được từ niêm yết đến lúc vào S1 (s1 dump): BAC 55′, CEG 60′, IBKR 50′ (cùng ngày 10-21). Symbol delist biến mất khỏi ticker/price, nên cũng biến mất khỏi universe (THỪA = 0).

## 6. B2 — Đo thiếu/thừa 10-21..10-23 (Vision 10-24 chưa phát hành)

| Ngày UTC | Vision TRADING | live S1 (union) | THIẾU | THỪA |
|---|---|---|---|---|
| 10-21 | 748 | 739 | 9 | 0 |
| 10-22 | 748 | 739 | 9 | 0 |
| 10-23 | 748 (746 còn trade giờ cuối) | 739 | 9 | 0 |

THIẾU (giống nhau cả 3 ngày). Chi tiết ở `live_vs_vision_1021_1023.csv`.

| Symbol | Lý do | Đúng/sai | Leg sim DEV (8 seed) |
|---|---|---|---|
| BTCDOMUSDT | DIED (index) | đúng (chủ ý) | 0 |
| USDCUSDT | DIED (stable) | đúng (chủ ý) | 0 |
| **POWRUSDT** | DIED, nhưng giao dịch liên tục từ 2023-10-27 (1 413–1 436 phút/ngày) | **SAI** | 31 leg, −144 |
| **MDTUSDT** | DIED; Vision SETTLED 10-13, relist 10-21 (588/779/681 phút) | **SAI** (sau relist) | 35 leg, +1 346 |
| 哈基米 / 币安人生 / 我踏马来了 / 牛来 / 龙虾 USDT | regex `^[A-Z0-9]+$` | **SAI** nếu owner muốn FULL | 0 |

- Ngày 10-24, live S1 có 737 symbol: MITO và PTB không xuất hiện cả ngày nhưng vẫn TRADING trên Vision lifecycle. Đây là 2 coin rất ít giao dịch (khoảng 530–540 phút/ngày ngày 10-23). Có thể không có trade nên bị `isTickerAvailable` bỏ: CHƯA XÁC MINH (cần Vision 10-24).
- Số symbol mỗi phút trong S1 dao động 592–739. Khoảng 115 symbol có <1200 phút/ngày trong S1, vì TradFi chỉ có trade trong giờ thị trường. Đây là chuyện bình thường của dữ liệu, không phải ingest lỗi.
- DIED hygiene: 10/143 tên **không tồn tại trên Vision UM** (ACA, BIFI, BTTC, DATA, FARM, GAIB, PIVX, PYR, UTK, WAN), vô hại. 23 symbol đã ngừng từ 2024 trở đi nhưng KHÔNG có trong DIED (vd LOKA, MKR, OM, TON, STG, EPIC 10-20). Với live thì vô hại vì ticker/price đã tự bỏ. ⇒ **DIED không phải nguồn lifecycle, chỉ là danh sách loại trừ và đang lỗi thời theo cả hai chiều.**
- **TradFi (L1)**: `live_low_activity_1023.csv` có 116 symbol <1200 phút trade ngày 10-23. 113 trong số đó niêm yết từ 2025-12 trở đi: BITO, NAVER, SNPS, KODEX200, USDBRL, PYPL, UBER, JPM, WMT, TENCENT, SAMSUNGEM, HK0625, IBKR, BAC… Ứng viên psym chứa 36–40 symbol loại này mỗi ngày, và shadow C3 đã mở IBKRUSDT ngày 10-24. Danh sách “TradFi” ở đây là proxy theo hoạt động. Phân loại chuẩn cần exchangeInfo (`contractType`/`underlyingType`) từ 242: CHƯA XÁC MINH.

## 7. B3 — Rủi ro vận hành khi delist

- **Paper (ShadowBookC3)**: giá lấy từ `DataManagerAerospikeFloatSim.getAllPriceRealtimeLegacy` (`BinanceOrderTradingManager.java:305-307`). Trong `tick()` (ShadowBookC3.java:383-390), thiếu giá thì `continue`: cụm không arm, không ratchet, **không time-stop (dòng 402)**, không đóng. Nếu record giá realtime của symbol delist vẫn còn trong Aerospike (giá đóng băng), cụm sẽ time-stop ở giá cuối, giống sim. Nếu record bị xoá hoặc hết TTL, cụm kẹt vĩnh viễn và chiếm hạn mức. Trường hợp nào xảy ra: CHƯA XÁC MINH (TTL realtime-price trên 242).
- **Vị thế thật (LEGACY / v1.2)**: Binance tự settle ở giá delist. Code chưa có reconcile positionRisk ↔ sổ local (C9 trong GOLIVE_SCENARIO), chưa có xử lý tường minh cho “symbol biến mất”, và không biết trước lịch delist. Không trace hết luồng LEGACY: CHƯA XÁC MINH.
- Không có guard “không mở mới coin đã có thông báo delist”. Trong DEV, 1,65 % leg (PnL +0,23 %) vào ≤7 ngày trước delist, 0,31 % leg vào ≤1 ngày. Số nhỏ nhưng ở live thật đây là lệnh dễ bị thanh khoản kém / giá sập trước giờ settle.

## 8. C — Đề xuất “symbol universe chuẩn” (v1.2, chưa code)

Nguyên tắc: **một định nghĩa universe** dùng chung cho live và sim: `U(t) = { s : alive(s,t) ∧ policy(s) } \ EXCLUDE`.
- `alive`: live lấy từ exchangeInfo; sim lấy từ lifecycle PIT.
- `policy`: quote USDT, PERPETUAL, cờ cho TradFi, cờ cho non-ASCII.
- `EXCLUDE`: danh sách ngắn có chủ đích (BTCDOM, USDC) và phải kiểm tự động.

**P0 (trước go-live, gắn vào nhánh `v1.2/c3-live`)**
1. **P0-U1 `SymbolUniverseLive`** (process trên 242, chỉ 242 gọi REST):
   - Nguồn: `GET /fapi/v1/exchangeInfo` mỗi 15′ và lúc start. Giữ `status=TRADING`, `contractType=PERPETUAL` (TradFi theo P0-U3), `quoteAsset=USDT`. Lưu `onboardDate`, `deliveryDate`.
   - Ghi Redis/Aerospike `universe_live{symbol→{status,onboard,delivery,ts}}`.
   - Collector (TickerIngestor/Funding/OI) và DES đọc tập này **thay cho** regex + `Constants.diedSymbol`.
   - `DIED_SYMBOLS` đổi tên thành `UNIVERSE_EXCLUDE` và chỉ còn các mục có lý do.
   - Kiểm tự động, cảnh báo Telegram khi: (a) symbol trong EXCLUDE đang TRADING mà không có cờ `intentional`; (b) symbol TRADING nhưng không có nến ingest quá 10′; (c) symbol có nến nhưng không TRADING.
   - Test: fixture exchangeInfo JSON (TRADING, SETTLING, CLOSE, PENDING_TRADING, quarterly `_`, TradFi, non-ASCII, relist sau SETTLED) → assert tập; fixture DIED có POWR/MDT → assert cảnh báo.
2. **P0-U2 Delist guard**:
   - Không mở mới khi `deliveryDate − now < 7 ngày` hoặc `status≠TRADING`.
   - Với cụm đang mở: khi nhận thông báo, log `[DELIST]` và cảnh báo. Khi thiếu giá > N phút, paper đóng ở giá cuối với lý do `DELIST`. Vị thế thật: reconcile positionRisk (gộp vào C9).
   - Sửa `ShadowBookC3.tick` để thiếu giá không còn `continue` im lặng: đếm số phút thiếu giá, cảnh báo, và khi >2h thì đóng tại giá cuối đã biết.
   - Test: cụm có giá biến mất 3h → đóng + cảnh báo; time-stop vẫn chạy khi giá đóng băng.
3. **P0-U3 Chính sách TradFi (cần MASTER/owner quyết)**: mặc định **loại TradFi khỏi universe mua và khỏi tính market level** cho đến khi có backtest HO 2026 có TradFi. Áp đồng thời cho sim và live (parity). Test: fixture có `contractType=TRADIFI_PERPETUAL` hoặc `underlyingType` không phải COIN → bị loại; log số bị loại mỗi lần refresh.
4. **P0-U4 Non-ASCII**: hoặc cho vào universe (kiểm key Aerospike/Redis, mapper và log UTF-8), hoặc loại có chủ đích và ghi log. Không để regex loại âm thầm.

**P1 (backtest / research)**
5. **P1-L1 Lifecycle cho sim**:
   - Nạp `lifecycle.parquet` (artefact này, cập nhật định kỳ từ Vision theo **giao dịch**, không theo file) vào `SymbolLifecycleManager` (TICKER_SOURCE=file).
   - `getTopSymbolArray` thêm `isAlive(sym,t) && isTickerAvailable(ticker)`.
   - Tại `t > last_trade_ts`, đóng vị thế ở giá cuối với status `DELIST_DONE` và cảnh báo, thay cho cách chờ time-stop trên nến zombie.
   - Test: symbol giả có nến zombie sau last_trade → 0 entry, đóng tại last_trade. Khi cờ TẮT thì kết quả byte-identical X14 8 seed.
   - Ảnh hưởng X14 dự kiến nhỏ: 100 leg, −0,96 % PnL, đổi giờ đóng.
6. **P1-L2 Độ nhạy coin mới niêm yết** (pre-reg trước khi chạy): X14 với tuổi niêm yết tối thiểu 0 / 1 / 7 ngày, kèm stress trượt giá cho coin <7 ngày. Lý do: 10,3 % PnL đến từ coin <7 ngày, 28 % từ coin <30 ngày.
7. **P1-L3 Job audit định kỳ (Oracle, offline)**: chạy lại `research/symlife/*` hằng tuần (Vision listing → lifecycle → so DIED/EXCLUDE và live S1 từ pull242) rồi báo cáo. Đây cũng là đầu vào cho P0-U1(a).
8. **P1-L4** Sửa lỗ raw 2022-02-26..28 (48 symbol) trong `~/vz_e1/raw` nếu còn dùng cho nghiên cứu.

**Việc owner** (KHÔNG làm trong cửa sổ promotion; MASTER quyết):
- Bỏ POWR, MDT khỏi `DIED_SYMBOLS` trên 242 sẽ **đổi universe live giữa cửa sổ parity (đến 11-18)**, làm lệch so với harness. Đề xuất gộp vào lúc deploy v1.2.
- Script đã soạn sẵn, chỉ 1 lệnh, mặc định chạy thử (dry-run): `research/symlife/owner_died_fix_242.sh`. Script backup config, chỉ sửa dòng `^DIED_SYMBOLS=`, không in secret và không restart. Muốn có hiệu lực thì cần restart **cả collector lẫn app**. Đường dẫn config của collector: CHƯA XÁC MINH.

## 9. CHƯA XÁC MINH / giới hạn

1. Dòng DIED đang chạy trên 242. Báo cáo này dùng bản harness `v11_settle/harness/config.properties` (md5 dòng khớp mọi run parity). Chưa đọc file trên 242 (luật cứng). Collector có thể có config riêng.
2. Phân loại TradFi chuẩn (exchangeInfo `contractType`/`underlyingType`). Hiện chỉ dùng proxy theo hoạt động (<1200 phút/ngày) và tên.
3. Sim có loại symbol non-ASCII không: 0 leg 币安人生 dù niêm yết 2025-10-20. Nguyên nhân chưa trace (dữ liệu 226 / mapper / prediction).
4. TTL của record giá realtime trên Aerospike 242 sau delist, quyết định paper cụm kẹt hay time-stop ở giá đóng băng. Luồng LEGACY khi vị thế thật bị Binance settle.
5. MITO/PTB vắng trong S1 ngày 10-24: chờ Vision 10-24.
6. Lỗ raw 2022-02-26..28 (48 symbol): CHƯA GIẢI THÍCH.
7. Biên first_trade của symbol niêm yết trước 2021-12 chỉ chính xác đến ngày (dùng ngày Vision). Không ảnh hưởng DEV 2022–25.
8. Delist ngay trong ngày cuối: lấy theo phút trade cuối (raw/Vision). Giá settle thật của Binance có thể khác giá trade cuối.

## 10. Artefact và cách chạy lại

- Repo `docs/result/symlife/`: `lifecycle_usdt.csv`, `legs_checks.csv`, `legs_exit_after_delist.csv`, `legs_violations.csv` (rỗng = 0 vi phạm), `legs_died_live_by_symbol.csv`, `live_vs_vision_1021_1023.csv`, `live_low_activity_1023.csv`.
- Code `research/symlife/` chạy theo thứ tự: `vl.py` (listing) → `rl.py` (raw day-cov) → `life.py` (v1 theo file, đầu vào cho dl) → `dl.py` (tải file Vision 2026, binary search) → `rl2.py` (ts trade raw) → `life2.py` (lifecycle v2 theo giao dịch, ghi đè `lifecycle.parquet`) → `legs.py` (printDone) → `live.py` (pull242 s1/psym) → `lcmp.py` (live so với Vision) → `extra.py` (pre-delist, coin mới, TradFi). `died.py` = 143 DIED. Toàn bộ là code độc lập, không import pipeline.
- Trên Oracle giữ `~/claude_master/symlife_wk/lifecycle.parquet` (+ `vision_act.parquet`, `raw_trade_ts.parquet`, `live_syms.parquet`). Các file trung gian lớn đã xoá.
