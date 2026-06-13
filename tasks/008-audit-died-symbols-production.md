# TASK-008: Audit & dọn DIED_SYMBOLS production (mở lại coin còn sống)

- **status:** APPROVED-A (user chốt phương án A 2026-06-13; chờ ops áp lên 226 + restart). Code KHÔNG tự sửa config/restart live. Giao CCD #3.
- **owner:** CCD #3 · **updated:** 2026-06-13 (audit xong, chờ user duyệt) — đồng bộ `docs/AGENTS.md`
- **Mục tiêu (user):** (1) dọn gọn `DIED_SYMBOLS` (đang phình + có trùng lặp); (2) **mở lại coin còn sống** để live ingest tiếp (tránh thiếu data theo thời gian + golive ít phát sinh).
- **Liên hệ:** nối "DIED_SYMBOLS-live re-ingest" (REBUILD_ROADMAP) + là đầu vào cho lifecycle 3-trạng-thái (ADR-0011/roadmap). KHÔNG trùng đợt B (đợt B chỉ backfill history; task này quyết coin nào live ingest tiếp).

## ⚠️ AN TOÀN — đọc trước
- `DIED_SYMBOLS` là **PRODUCTION config** (`Configs.getString("DIED_SYMBOLS")` → `Constants.diedSymbol`, nạp 1 lần lúc start). Sửa = sửa config + **restart** ingester.
- ⚠️ **TÁC ĐỘNG KÉP:** `diedSymbol` dùng chung cho CẢ **ingest** (FundingIngestor/Ticker skip) lẫn **trade** (DetectEntrySignal skip). Gỡ 1 coin khỏi đây = vừa ingest lại VỪA cho trade lại. → phải cảnh báo, KHÔNG tự ý gỡ.
- Task này **CHỈ phân loại + đề xuất + báo user duyệt**. KHÔNG tự sửa config live, KHÔNG restart. SLF4J.

## Bối cảnh (đã đọc code)
- `Constants` static block: `DIED_SYMBOLS` split `,`, thiếu `USDT` thì tự nối → `diedSymbol` (Set). 
- Dùng `Constants.diedSymbol.contains(symbol)` để skip ở: `FundingIngestor2AerospikeNew`, `DetectEntrySignal2TradeNormal`, … (CCD grep toàn bộ nơi dùng để biết đủ tác động trước khi đề xuất gỡ).
- `DIED_SYMBOLS` hiện tại (đã có TRÙNG LẶP cần dọn: LOOM×2, ORBS×2, FLM×3, SXP×2, VFY×2, 1000WHY×2, BDXN×2, IDEX×2, MDT×2):
  GAIB,STPT,SNT,MBL,RAD,CVX,IDEX,SLP,GLMR,MDT,AUDIO,BLUEBIRD,FOOTBALL,ANT,CTK,DGB,STRAX,COCOS,RAY,FTT,SC,HNT,BTCST,BTS,TOMO,SRM,CVC,USDC,BTCDOM,WAVES,GAL,RNDR,FRONT,MATIC,XEM,ORBS,LOOM,OCEAN,DAR,KEY,SONIC,STMX,AGIX,LOOM,COMBO,BOND,UNFI,REN,REEF,BNX,ORBS,AERGO,CELO,LINA,BLZ,LIT,KLAY,OMG,FTM,AMB,XEM,VIDT,NULS,TROY,BAL,BADGER,ALPACA,EOS,NEIROETH,UXLINK,HIFI,BAKE,SLERF,FLM,KDA,PERP,MYRO,1000X,XCN,FLM,FLM,PONKE,SWELL,QUICK,SXP,MILK,OBOL,TOKEN,SKATE,REI,FIS,VOXEL,BID,DMC,ZRC,TANSSI,42,COMMON,CUDIS,EPT,ACA,CHESS,DATA,DF,GHST,NKN,RVV,YALA,VFY,1000WHY,BDXN,A2Z,FORTH,HOOK,IDEX,LRC,NTRN,RDNT,SXP,VFY,1000WHY,BDXN,UTK,BIFI,FIO,FUN,MDT,OXT,WAN,DEGO,DENT,TRU,B3,DEGEN,ZKJ,IR,DAM,VINE,AI,ATA,FARM,MLN,PHB,SYS,COS,D,HIGH,MBOX

## Yêu cầu
1. **Lấy universe đang TRADING** từ Binance: `GET /fapi/v1/exchangeInfo` → lọc `contractType == PERPETUAL` && `quoteAsset == USDT` && `status == TRADING`. (Qua `BinanceRestGuard` nếu task-007 đã có; nếu chưa, 1 call exchangeInfo weight thấp — vẫn cẩn thận ban.) → tập `LIVE_SET`.
2. **Chuẩn hoá DIED hiện tại:** uppercase + nối `USDT` nếu thiếu + **DỌN TRÙNG** (set). Báo các mục trùng đã gộp.
3. **Phân loại mỗi symbol trong DIED:**
   - **CÒN SỐNG** = có trong `LIVE_SET` (status TRADING) → đề xuất **GỠ** (để live ingest lại). Gồm cả 10 coin đợt B (RAY/WAVES/FTT/DGB/SC/GLMR/MDT/IDEX/RAD/STRAX) nếu chúng còn TRADING.
   - **CHẾT/không niêm yết** = không trong `LIVE_SET` → **GIỮ**. Phân nhóm con: (a) delist thật; (b) **rebrand** (ticker cũ ngừng, coin sống dưới ticker mới — nghi: MATIC→POL, FTM→S, RNDR→RENDER, AGIX/OCEAN→FET…) — đánh dấu NGHI để user xem; (c) index/stable cố ý giữ: `BTCDOM` (index), `USDC` (stable).
4. **Output (KHÔNG áp):**
   - **Bảng phân loại** 4 nhóm: GỠ (sống) / GIỮ-delist / GIỮ-rebrand-nghi / GIỮ-index-stable; + danh sách trùng đã dọn.
   - **Chuỗi `DIED_SYMBOLS` mới đề xuất** (đã dọn trùng + bỏ nhóm GỠ) — dạng paste thẳng vào config.
   - **Cảnh báo cho từng coin GỠ:** khi gỡ, live ingest lại TỪ GIỜ; history trước đó có thể thủng (như đợt B) → nếu cần lịch sử thì backfill riêng sau.
5. **Nêu rõ quyết định cho user (tác động kép):** mỗi coin GỠ sẽ được **ingest lại + trade lại**. Nếu user chỉ muốn DATA mà chưa muốn TRADE nhóm này → đề xuất phương án **tách set** (`DIED_INGEST` chỉ coin chết thật / `DIED_TRADE` rộng hơn) — mô tả chi phí refactor, để user chọn: (A) gỡ hẳn (ingest+trade), hay (B) tách set data-only. KHÔNG tự refactor; chỉ trình phương án.

## Acceptance
- [ ] Bảng phân loại đầy đủ (GỠ / GIỮ-delist / GIỮ-rebrand-nghi / GIỮ-index-stable) + danh sách trùng đã dọn.
- [ ] Chuỗi `DIED_SYMBOLS` mới (dọn trùng + bỏ coin sống) sẵn để paste.
- [ ] Liệt kê mọi nơi code dùng `Constants.diedSymbol` (tác động khi gỡ).
- [ ] Trình 2 phương án xử lý tác động kép (gỡ hẳn vs tách set) cho user chọn.
- [ ] KHÔNG sửa config/restart live; chờ user duyệt.

## (Code điền) — KẾT QUẢ AUDIT (2026-06-13, exchangeInfo live)

### ⚠️ Phát hiện sớm: repo config ≠ production
`config.properties:25` trong repo CHỈ có **30 symbol** (STPT…BNX, không có duplicate, không có GAIB và cả trăm coin kia). Danh sách "hiện tại" ở mục Bối cảnh (148 token / 137 unique) là **giá trị production trên server 226** mà user đưa. Repo config là bản cũ/dev. ⇒ Audit này chạy trên **danh sách production (137 unique)** đúng theo task. Khi user duyệt, sửa config production trên 226, KHÔNG phải file repo.

### LIVE_SET từ exchangeInfo (số symbol TRADING)
**527** symbol PERPETUAL & quoteAsset=USDT & status=TRADING.

### Chuẩn hoá DIED + DỌN TRÙNG
148 token thô → **137 unique** sau khi uppercase + nối USDT + gộp set. 10 mục trùng đã gộp:
`1000WHY×2, BDXN×2, FLM×3, IDEX×2, LOOM×2, MDT×2, ORBS×2, SXP×2, VFY×2, XEM×2` (= 11 token thừa).

### Bảng phân loại 4 nhóm

**NHÓM 1 — GỠ (còn TRADING, là perpetual giao dịch thật): 8 coin**
`CVXUSDT, SLPUSDT, CTKUSDT, CVCUSDT, SONICUSDT, AERGOUSDT, CELOUSDT, LITUSDT`
→ đề xuất GỠ để live ingest lại (và — cảnh báo — trade lại, xem tác động kép).

**NHÓM 2 — GIỮ-index/stable (đang TRADING nhưng cố ý chặn): 2 coin**
`USDCUSDT` (stablecoin pair), `BTCDOMUSDT` (index perpetual). → GIỮ trong DIED dù còn sống.

**NHÓM 3 — GIỮ-rebrand-NGHI (ticker cũ ngừng, coin sống dưới ticker mới — user xem): 6 coin**
| Ticker cũ (DIED) | Coin sống mới (đã verify LIVE) |
|---|---|
| MATICUSDT | → POLUSDT ✅ |
| FTMUSDT | → SUSDT ✅ (Sonic) |
| RNDRUSDT | → RENDERUSDT ✅ |
| AGIXUSDT | → FETUSDT ✅ (merge ASI) |
| OCEANUSDT | → FETUSDT ✅ (merge ASI) |
| TOMOUSDT | → VICUSDT ✅ (Viction) |
→ GIỮ ticker cũ; nếu muốn data/trade coin mới thì thêm ticker MỚI vào universe, KHÔNG gỡ ticker cũ.

**NHÓM 4 — GIỮ-delist thật (không còn trong LIVE_SET): 121 coin còn lại**
Gồm cả **10 coin đợt B** (RAY/WAVES/FTT/DGB/SC/GLMR/MDT/IDEX/RAD/STRAX) — kiểm tra exchangeInfo: **tất cả 10 đều KHÔNG còn TRADING** → đợt B chỉ backfill history, KHÔNG mở live (đúng kỳ vọng). Phần còn lại là các coin delist/ngừng niêm yết Binance Futures.

### Chuỗi DIED_SYMBOLS mới đề xuất (đã dọn trùng + bỏ 8 coin NHÓM 1) — 129 symbol, paste thẳng:
```
GAIBUSDT,STPTUSDT,SNTUSDT,MBLUSDT,RADUSDT,IDEXUSDT,GLMRUSDT,MDTUSDT,AUDIOUSDT,BLUEBIRDUSDT,FOOTBALLUSDT,ANTUSDT,DGBUSDT,STRAXUSDT,COCOSUSDT,RAYUSDT,FTTUSDT,SCUSDT,HNTUSDT,BTCSTUSDT,BTSUSDT,TOMOUSDT,SRMUSDT,USDCUSDT,BTCDOMUSDT,WAVESUSDT,GALUSDT,RNDRUSDT,FRONTUSDT,MATICUSDT,XEMUSDT,ORBSUSDT,LOOMUSDT,OCEANUSDT,DARUSDT,KEYUSDT,STMXUSDT,AGIXUSDT,COMBOUSDT,BONDUSDT,UNFIUSDT,RENUSDT,REEFUSDT,BNXUSDT,LINAUSDT,BLZUSDT,KLAYUSDT,OMGUSDT,FTMUSDT,AMBUSDT,VIDTUSDT,NULSUSDT,TROYUSDT,BALUSDT,BADGERUSDT,ALPACAUSDT,EOSUSDT,NEIROETHUSDT,UXLINKUSDT,HIFIUSDT,BAKEUSDT,SLERFUSDT,FLMUSDT,KDAUSDT,PERPUSDT,MYROUSDT,1000XUSDT,XCNUSDT,PONKEUSDT,SWELLUSDT,QUICKUSDT,SXPUSDT,MILKUSDT,OBOLUSDT,TOKENUSDT,SKATEUSDT,REIUSDT,FISUSDT,VOXELUSDT,BIDUSDT,DMCUSDT,ZRCUSDT,TANSSIUSDT,42USDT,COMMONUSDT,CUDISUSDT,EPTUSDT,ACAUSDT,CHESSUSDT,DATAUSDT,DFUSDT,GHSTUSDT,NKNUSDT,RVVUSDT,YALAUSDT,VFYUSDT,1000WHYUSDT,BDXNUSDT,A2ZUSDT,FORTHUSDT,HOOKUSDT,LRCUSDT,NTRNUSDT,RDNTUSDT,UTKUSDT,BIFIUSDT,FIOUSDT,FUNUSDT,OXTUSDT,WANUSDT,DEGOUSDT,DENTUSDT,TRUUSDT,B3USDT,DEGENUSDT,ZKJUSDT,IRUSDT,DAMUSDT,VINEUSDT,AIUSDT,ATAUSDT,FARMUSDT,MLNUSDT,PHBUSDT,SYSUSDT,COSUSDT,DUSDT,HIGHUSDT,MBOXUSDT
```
(137 unique − 8 GỠ = 129. USDC/BTCDOM giữ lại có chủ đích.)

### ⚠️ Cảnh báo cho 8 coin GỠ
Gỡ khỏi DIED = live ingest lại **TỪ THỜI ĐIỂM RESTART**; history funding/ticker trước đó **thủng** (như đợt B). Nếu cần lịch sử → backfill riêng sau (đợt riêng), không tự sinh ra.

### Nơi dùng Constants.diedSymbol (grep) — tác động khi gỡ
| File:line | Vai trò | Tác động khi gỡ 1 coin |
|---|---|---|
| `websocket/TickerIngestor2AerospikeNew.java:151,384` | skip ingest ticker | **INGEST lại** ticker coin đó |
| `websocket/FundingIngestor2AerospikeNew.java:62` | skip ingest funding | **INGEST lại** funding |
| `trading/DetectEntrySignal2TradeNormal.java:133` | skip entry signal | **TRADE lại** (mở lệnh) coin đó ⚠️ |
| `tradecore/MarketBigChangeDetector.java:63` | lõi chung SIM+LIVE | ảnh hưởng cả backtest lẫn live detect |
| `ai_ml/features/export/MarketDataInlineGenerator.java:63` | export feature | coin vào lại tập feature export |
| `research/ExportMarketData2File.java:86` | export market data | tương tự |
| `research/HistoricalFundingCrawler.java:32` | crawler history | crawl lại history |
| `websocket/checkdata/{PriceRealtimeValidator,FundingValidator,AdvancedDataValidator}.java` | validator | đưa coin vào diện validate |

→ Điểm nóng: **dòng `DetectEntrySignal2TradeNormal:133`** = tác động kép TRADE.

### 2 phương án tác động kép + khuyến nghị
- **(A) Gỡ hẳn** 8 coin khỏi DIED: ingest lại + **trade lại** ngay sau restart. Đơn giản, 0 refactor. Rủi ro: cho phép mở lệnh 8 coin thanh khoản thấp/biến động mạnh khi chưa có data lịch sử đủ.
- **(B) Tách 2 set** `DIED_INGEST` (chỉ coin chết thật, dùng ở ingestor/validator/export) và `DIED_TRADE` (rộng hơn, dùng ở `DetectEntrySignal:133` + `MarketBigChangeDetector:63`). Gỡ 8 coin khỏi `DIED_INGEST` để **chỉ thu data**, vẫn giữ trong `DIED_TRADE` để CHƯA cho trade. Chi phí: thêm 1 config key + 1 Set trong `Constants` + sửa ~9 call-site phân loại đúng (ingest-only vs trade-only), bump `CONFIG_VERSION` nếu đụng nhánh SIM (`MarketBigChangeDetector`). Vài giờ refactor + test.

**Khuyến nghị (ban đầu):** Phương án (B). **→ USER CHỐT (2026-06-13): chọn (A) gỡ hẳn.** Lý do user: (B) tách `DIED_INGEST`/`DIED_TRADE` làm SIM/LIVE **vênh** — phạm luật "MỘT BỘ NÃO sim/product". Giữ MỘT danh sách dùng chung.

### ✅ QUYẾT ĐỊNH ÁP — Phương án A
- Gỡ hẳn 8 coin NHÓM 1 (`CVX, SLP, CTK, CVC, SONIC, AERGO, CELO, LIT`) khỏi `DIED_SYMBOLS` → vừa **ingest lại** vừa **trade lại** sau restart. Chấp nhận rủi ro mở lệnh khi history chưa đủ (8 coin này thanh khoản OK, đều TRADING).
- Giữ USDC/BTCDOM (index/stable), giữ 6 rebrand (ticker cũ), giữ 121 delist.
- **Config production mới = chuỗi 129 symbol ở trên.**

### Các bước áp (user/ops thực hiện trên 226 — Code KHÔNG tự đụng live)
1. Sửa key `DIED_SYMBOLS` trong **config.properties production trên 226** = chuỗi 129 symbol ở trên (mục "Chuỗi DIED_SYMBOLS mới đề xuất").
2. **Restart ingester** (`BinanceDataIngestor`) — `Constants` nạp 1 lần lúc start nên bắt buộc restart mới ăn.
3. **Restart trading** (`BinanceOrderTradingManager`) — để `DetectEntrySignal2TradeNormal:133` thôi skip 8 coin.
4. Sau restart, theo dõi: 8 coin bắt đầu có ticker/funding mới trong Aerospike (history trước đó vẫn thủng — backfill riêng nếu cần).

### ⚠️ Lưu ý đồng bộ repo (KHÔNG tự sửa — chờ xác nhận)
`config.properties` trong repo đang là bản KHÁC (30 symbol). Docs `DEFERRED.md`/`INGEST_FORMAT.md` còn ghi state SIM rút `diedSymbol` còn `BTCDOMUSDT` cho survivorship. ⇒ Đang tồn tại tới 3 giá trị (repo 30 / prod 137 / SIM-survivorship 1). Đây là nguồn "vênh" tiềm ẩn KHÁC, ngoài phạm vi gỡ-8-coin. Không sửa repo config trong task này để khỏi vỡ survivorship backtest; cần 1 task riêng thống nhất nguồn config.
