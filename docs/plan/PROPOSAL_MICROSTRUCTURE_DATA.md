# PROPOSAL — Mua dữ liệu microstructure lịch sử (order book L2 / trade-by-trade) cho S1

Ngày: 2026-09-20. Tác giả: agent khảo sát (đề xuất, KHÔNG phải quyết định mua).
Trạng thái: **CHỜ MASTER + Uni duyệt**. Không có budget nào được cam kết trong tài liệu này.

## 0. Rủi ro nói thẳng TRƯỚC (theo luật §0.4 AGENT_RUNBOOK)

1. **Rủi ro licence**: hầu hết nhà cung cấp (Tardis, Kaiko, CoinAPI, Amberdata) cấm resell dữ
   liệu thô hoặc derived data ở độ phân giải cao; Tardis cho phép redistribute OHLCV ≥10 phút
   nhưng KHÔNG cho AI/foundation-model training tổng quát (chỉ cho phép "task-specific
   quantitative/statistical models" — XGBoost ranker S1 khớp diện này, nhưng phải đọc kỹ ToS
   bản mới nhất tại thời điểm ký, không dựa vào bản agent đọc hôm nay).
2. **Rủi ro chất lượng dữ liệu bên thứ 3**: cả 4 nhà cung cấp đều lấy lại từ WebSocket/REST
   Binance — nghĩa là họ CŨNG bị gap khi Binance rate-limit/disconnect. Không có nhà cung cấp
   nào công khai SLA "0 gap" cho giai đoạn 2022-2023 (thanh khoản altcoin thấp, nhiều đợt
   halt/maintenance). Phải tự viết script kiểm tra gap/duplicate/timestamp-out-of-order trước
   khi tin dữ liệu.
3. **Rủi ro survivorship bias**: KHÔNG nhà cung cấp nào trong 4 cái được khảo sát công khai
   cam kết bằng văn bản là giữ lịch sử của symbol đã bị Binance delist khỏi futures (ví dụ
   các coin đã bị gỡ niêm yết 2022-2024). Đây là câu hỏi PHẢI hỏi sales trước khi ký — nếu
   không, list top-60 sẽ bị lệch về phía "coin còn sống", đúng loại bias mà `PREREG_FS` vẫn
   luôn cảnh giác.
4. **Rủi ro thời điểm phủ lịch sử không khớp DEV window**: DEV hiện tại = 2022-01 → 2025-12
   (48 tháng, luật §0.1). Một số nhà cung cấp (Kaiko top-of-book) chỉ có lịch sử từ cuối
   2022 — KHÔNG phủ hết Q1-Q3/2022 của DEV. Nếu mua phải kiểm tra đúng field lịch sử theo
   symbol, không tin số "since 20xx" chung chung trên trang marketing.
5. **Rủi ro chi phí chìm nếu lại NULL**: toàn bộ các vòng feature-selection trên OHLCV/funding/OI
   trước đó đều NULL. Không có gì đảm bảo order-flow/depth-imbalance features sẽ khác — đây
   vẫn là một giả thuyết, không phải kết quả đã kiểm chứng. Đề xuất mua chỉ nên chạy như một
   THÍ NGHIỆM có ngân sách trần rõ ràng (subset nhỏ, xem mục 2), không mua "cho chắc" toàn bộ
   universe.
6. **Phát hiện quan trọng làm giảm phạm vi cần mua**: `data.binance.vision` (MIỄN PHÍ) đã
   verify là có field `m` (`isBuyerMaker`) trong toàn bộ trade/aggTrades bulk CSV cho futures —
   tức là **trade-by-trade CÓ aggressor flag cho TOÀN BỘ universe futures, từ ngày symbol niêm
   yết, đã có sẵn miễn phí**, không cần mua. Cái thực sự thiếu và phải trả tiền chỉ là **L2
   order book depth** (bulk `bookDepth` free chỉ là snapshot phần trăm quanh mid-price, KHÔNG
   phải sổ lệnh L2 thật — xem mục 1.5).

## 1. Bảng so sánh nhà cung cấp

| Tiêu chí | **Tardis.dev** | **Kaiko** | **CoinAPI** | **Amberdata** | **Binance Vision (free)** |
|---|---|---|---|---|---|
| L2 depth (Binance USDS-M futures) | **Có** — `incremental_book_L2` (đủ update, không phải snapshot rời rạc), từ 2019-11-17 (2020-01-07 trở về sau ở granularity ~0ms, trước đó `depth@100ms`) | Có "raw order book snapshot + L2 aggregations"; best-bid/ask (top-of-book) chỉ từ **12/2022**; raw snapshot sâu hơn nói "từ 2015" nhưng KHÔNG xác nhận riêng cho Binance futures — cần hỏi sales | Không rõ — trang docs công khai chỉ liệt kê aggTrades/klines/trades cho futures, "Order Books" chỉ nhắc chung chung không xác nhận L2 đầy đủ Binance futures | Có `futures-order-book-snapshots` API, `maxLevel` cấu hình được, nhưng **mỗi request giới hạn tối đa 18 tháng** (phải chia nhiều lần gọi để phủ hết 4.5 năm) | KHÔNG — `bookDepth` chỉ là % depth quanh mid-price (band cố định 0.1/0.25/0.5/1/2/5%), sample rời rạc, không phải L2 thật |
| Trade-by-trade + aggressor flag | Có, `trades` channel, field `side` | Có ("All trades" feed) | Có (REST `/trades`) | Có | **CÓ SẴN MIỄN PHÍ** — aggTrades bulk CSV có cột `is_buyer_maker` |
| Độ phân giải | Tick-level thật (mọi update sổ lệnh) | Tick-level (stream) / snapshot 1s-1min cho aggregation | Không rõ — REST rate-limited, không phải bulk tick file | Snapshot theo request (không phải update liên tục) | aggTrades: tick thật; bookDepth: rời rạc theo band % |
| Universe (futures symbol) | Toàn bộ USDS-M futures Binance (kể cả delisted — **CHƯA XÁC NHẬN** bằng văn bản, cần hỏi) | "100+ exchanges" nói chung, số symbol Binance futures cụ thể không nêu trên trang sản phẩm | "300+ exchanges" nói chung, không có số cụ thể cho Binance futures | Không nêu số symbol cụ thể | Toàn bộ symbol còn niêm yết + có thể còn file của symbol đã delist (chưa kiểm chứng) |
| Giá | Perpetuals data plan: **Academic $350-650/mo, Solo $700-1,200/mo, Professional $1,000-2,200/mo, Business $3,000-6,000/mo** (billing năm; Academic/Solo/Pro giới hạn lịch sử **4 năm**, chỉ Business mới "all available" — quan trọng vì DEV cần ~4-4.5 năm, sát ranh giới) | L1 aggregations **~$1,000/mo**, L2 tick-level **~$2,500/mo** (số tham khảo trên trang sản phẩm, thực tế theo quote) | Startup $79/mo, Streamer $249/mo, Pro $599/mo + overage $0.50-1/GiB (Tier 1), không có gói "mua trọn lịch sử" rõ ràng | Không công khai — "mua online" qua landing page riêng, phải request quote | $0 |
| Format | `.csv.gz` bulk (daily), HTTP API, hoặc replay bằng `tardis-machine` (Docker/npm) ra lại đúng format WebSocket gốc | REST API, S3/Azure/GCS daily CSV export, Snowflake/BigQuery | JSON qua REST API (không phải bulk file) | REST API (JSON), không thấy bulk file option công khai | `.zip` (CSV bên trong), daily/monthly, tải trực tiếp qua HTTPS hoặc S3 |
| Bulk historical download | **Có**, đây là thế mạnh chính (file tải thẳng theo ngày/symbol) | Có qua object storage (S3 v.v.) | Không — REST endpoint, phải tự đóng gói bằng nhiều lần gọi | Không có bulk file rõ ràng — API theo request, giới hạn 18 tháng/lần | Có — đây là cơ chế chính |
| Licence cho nghiên cứu nội bộ/backtest | **Cho phép rõ ràng** (ToS Clause 9.5): "task-specific quantitative or statistical models ... market research, backtesting, trading execution, risk management". Cấm dùng cho AI/foundation-model tổng quát. Redistribute chỉ cho phép OHLCV ≥10 phút, không lộ raw data | Không công khai trên trang sản phẩm — cần hỏi sales / đọc MSA | Không công khai chi tiết trên trang pricing — cần đọc ToS/AUP riêng | Không công khai — cần hỏi sales | Public data Binance, dùng nghiên cứu nội bộ không vấn đề (đã dùng rồi) |

Ghi chú độ tin cậy: các con số giá lấy từ trang web công khai ngày 2026-09-20 qua WebFetch/WebSearch
(model tóm tắt tự động, không phải đọc nguyên văn HTML) — **PHẢI xác nhận lại bằng email/quote
trực tiếp với sales trước khi ký**, đặc biệt Kaiko/Amberdata/CoinAPI không có bảng giá bulk-historical
rõ ràng công khai.

## 2. Subset đề xuất mua + ước lượng dung lượng & chi phí

### 2.1 Danh sách 60 symbol (trích xuất THẬT từ Oracle, không phải ước lượng)

Lấy từ `printDone.csv` của hai run `X1_GS_T170_2021` (1,089 lệnh) và `X1_C3_FULL_2021`
(2,559 lệnh) trên Oracle, gộp theo cột `sym`, 503 symbol duy nhất, xếp theo tổng số lệnh giảm dần.
Top-60 (số lệnh gộp 2 run trong ngoặc): AIA(50), PEOPLE(45), UNFI(44), ALCH(41), MASK(38),
FARTCOIN(37), MYX(33), BLZ(30), ALICE(29), PIPPIN(27), COAI(27), EVAA(26), RSR(26), 1000PEPE(26),
WIF(25), CHR(25), SOL(25), ANC(25), 1000RATS(24), GMT(24), FTM(24), ARC(23), GALA(23), CELR(22),
LINA(21), FTT(21), BEL(20), TRB(20), CRV(19), ALPINE(19), XVG(19), OM(19), LPT(19), JELLYJELLY(18),
AI16Z(18), ACT(18), RUNE(18), PNUT(18), 1000FLOKI(18), 1000SHIB(18), OGN(18), TNSR(17), FLM(17),
GTC(17), MYRO(17), YGG(17), INJ(17), AVAX(17), SWARMS(16), ATA(16), MTL(16), SXP(16), LUNA(16),
BLESS(15), ZEREBRO(15), CHILLGUY(15), MOODENG(15), TOMO(15), DYDX(15).

Lưu ý: trong dữ liệu thô có một dòng `sym="4"` (19 lệnh) — rõ ràng là artifact lỗi parse/dữ liệu
bẩn (không phải symbol thật), đã loại khỏi danh sách trên; danh sách trên là 60 symbol hợp lệ kế
tiếp sau khi loại dòng đó. Danh sách này phản ánh symbol có NHIỀU LỆNH nhất trong backtest 2 chiến
lược — không nhất thiết là symbol thanh khoản cao nhất trên sàn thật (một số như FARTCOIN, PIPPIN,
COAI, JELLYJELLY, ZEREBRO, CHILLGUY, MOODENG, SWARMS, BLESS là memecoin mới niêm yết cuối 2024/2025,
lịch sử L2 của chúng sẽ ngắn hơn nhiều so với 4.5 năm — cần lọc lại theo ngày niêm yết thật khi mua).

### 2.2 Subset đề xuất

**(a) Trade-by-trade + aggressor flag, toàn universe (~300-500 symbol futures)**
→ **KHÔNG CẦN MUA** — đã có miễn phí qua `data.binance.vision/data/futures/um/{daily,monthly}/aggTrades/`
(cột `is_buyer_maker`). Việc cần làm là VIẾT PIPELINE tải + tổng hợp bulk aggTrades này (dữ liệu đã
tồn tại từ lâu, hệ thống hiện tại có thể chưa dùng hết). Đề xuất làm bước này TRƯỚC, miễn phí, để
kiểm tra xem order-flow-imbalance/aggressive-buy-ratio ở lưới giờ tính từ tick thật có khác gì so
với feature `taker_buy` hiện có hay không — nếu vẫn NULL thì tiết kiệm được toàn bộ ngân sách mua L2.

**(b) L2 depth top-20 level, snapshot 1s, CHỈ 60 symbol (danh sách mục 2.1, lọc lại theo ngày niêm
yết thật), DEV window 2022-01 → 2025-12 (48 tháng) + buffer đến hiện tại**
→ Đây là phần THỰC SỰ cần mua, vì không có nguồn miễn phí nào thay thế.

### 2.3 Ước lượng dung lượng (GB, nén)

Ước lượng THÔ, sai số có thể ±3x — không có provider nào công khai bảng size/symbol/ngày, cần
tải sample thật (1 ngày, 1 symbol) trước khi cam kết mua để tính lại chính xác.

- L2 top-20, snapshot 1s: 20 mức × 2 phía × (giá+khối lượng) = 80 số/snapshot × 86,400
  snapshot/ngày. Với nén tốt (delta-encode giá liền kề, gzip) ước ~10-50MB/symbol/ngày tuỳ thanh
  khoản (BTC/ETH/SOL ở mức cao của range, symbol memecoin thấp thanh khoản ở mức thấp).
  → 60 symbol × ~1,460 ngày (48 tháng DEV) × trung bình ~25MB/ngày ≈ **~2.2 TB nén**
  (dải hợp lý 1-4.5 TB tuỳ nén thực tế và có bao nhiêu symbol trong 60 cái đã niêm yết đủ lâu).
- Nếu tăng buffer đến 2026-09 (thêm ~9 tháng, KHÔNG dùng để train vì là HOLDOUT, chỉ để pipeline
  sẵn sàng chạy live sau này): thêm ~15% dung lượng.
- Trade-by-trade (a) không tính vào ngân sách mua vì đã miễn phí, nhưng vẫn tốn chỗ tải/giải nén
  tạm thời: aggTrades toàn universe 4.5 năm ước ~500GB-1.5TB nén (đã có sẵn trên Binance Vision,
  không phải trả tiền, chỉ tốn băng thông + đĩa tạm).

**Tổng ước lượng cần xử lý tạm thời**: ~3-4 TB (L2 mua + aggTrades free) trong giai đoạn backfill.

### 2.4 Chi phí lưu trữ & xử lý

Oracle hiện tại chỉ còn **~26GB đĩa trống** — KHÔNG đủ chứa dù chỉ 1 ngày dữ liệu L2 đầy đủ.
Bắt buộc phải xử lý theo mô hình **streaming-through, không giữ raw lâu dài**:

1. Object storage trung gian (không đặt trên Oracle boot disk):
   - **Backblaze B2**: $6.95/TB/tháng lưu trữ, egress miễn phí tới 3x dung lượng lưu trung bình/
     tháng, vượt mức $0.01/GB. Với ~3-4TB lưu tạm trong 1-2 tháng xử lý: ước **$25-30/tháng**
     storage, egress gần như miễn phí nếu tải về Oracle 1 lần rồi xoá.
   - Hoặc **Oracle OCI Object Storage** (cùng nhà cung cấp compute hiện tại) — cần kiểm tra xem
     tài khoản Oracle Cloud đang dùng có quota/free-tier Object Storage sẵn không (free tier OCI
     thường có 10-20GB free, không đủ — vẫn phải trả thêm, giá chuẩn OCI Standard Storage khoảng
     $0.0255/GB/tháng tại thời điểm khảo sát, RẺ HƠN B2 nhưng cần verify giá hiện hành và egress
     OCI trước khi chọn — không có số chính xác trong bản khảo sát này).
2. Quy trình xử lý đề xuất (để KHÔNG giữ raw L2/trade thô lâu dài):
   - Tải raw theo lô nhỏ (1 symbol × 1 tháng) từ provider → giải nén tạm trên Oracle hoặc một VM
     xử lý riêng (KHÔNG dùng RAM/CPU của box đang chạy sim/live) → chạy script tổng hợp ra feature
     15m/1h (order-flow imbalance, depth imbalance, spread, v.v. — xem mục 3) → ghi feature đã
     tổng hợp (nhỏ, vài trăm MB cho cả 60 symbol × 4.5 năm) vào kho feature hiện có → XOÁ raw lô đó.
   - Raw gốc vẫn lưu bên object storage (B2/OCI) làm cold archive để có thể tái tạo lại nếu cần
     đổi công thức feature — không xoá hẳn khỏi mọi nơi, chỉ xoá khỏi Oracle boot disk.
3. Chi phí tổng ước lượng: **storage cold archive dài hạn (giữ mãi trên B2)**: nếu giữ nguyên
   3-4TB mãi mãi ≈ $25-30/tháng ≈ $300-360/năm — khoản này nhỏ so với chi phí mua data, nhưng
   nên cân nhắc chỉ giữ archive cho SUBSET đã chứng minh có ích sau vòng thí nghiệm đầu, không
   giữ mãi toàn bộ 60 symbol nếu kết quả null.

## 3. Danh sách feature dự kiến sinh ra

| Feature dự kiến | Hệ thống ĐÃ CÓ bản thô lưới giờ chưa? | Vì sao bản fine-grained có thể mang thông tin khác |
|---|---|---|
| Order-flow imbalance (1m/5m/1h, từ aggressor flag tick) | **Đã có gần đúng** — hệ thống hiện dùng `taker_buy` ratio ở lưới giờ (tổng hợp từ klines `taker_buy_base_volume`, vốn cũng suy ra từ aggTrades nhưng đã bị Binance tổng hợp sẵn ở granularity 1 nến). | Tính lại trực tiếp từ tick (đã miễn phí, xem mục 2.2a) cho phép windows ngắn hơn (1-5 phút) và bắt được asymmetry trong-nến mà `taker_buy` per-candle không thấy (ví dụ: mua dồn dập rồi bán tháo trong cùng 1 giờ sẽ triệt tiêu nhau ở lưới giờ nhưng để lại dấu vết ở tick). |
| Depth imbalance (top-5, top-20 level) | **CHƯA CÓ** — hệ thống không có tick sổ lệnh, chỉ có `bookDepth` % band (nếu đã dùng) hoặc không dùng gì từ order book. | Đây là loại thông tin hoàn toàn mới: áp lực cung/cầu TRÊN sổ lệnh (chưa khớp) khác về bản chất với thông tin GIÁ ĐÃ KHỚP (klines/OHLCV) — có thể dẫn giá vài phút, đúng giả thuyết "thông tin mới chỉ nằm ở microstructure". |
| Spread & spread-volatility | **CHƯA CÓ** — không có bid/ask lịch sử. | Spread rộng bất thường thường báo hiệu thanh khoản mỏng/risk-off cục bộ ở coin đó trước khi phản ánh vào giá — tín hiệu sớm không có trong OHLCV. |
| Phân phối kích thước lệnh (trade-size distribution) | **CHƯA CÓ** ở dạng phân phối — hệ thống chỉ có tổng `volume`/`quantity` mỗi giờ, không có phân phối theo kích thước lệnh. | Tỷ trọng lệnh lớn (khả năng là "cá voi"/smart money) so với lệnh nhỏ (retail) trong cùng volume tổng có thể mang thông tin hướng đi khác với volume thô. |
| Tỷ lệ mua chủ động (aggressive buy ratio, fine-grain) | Tương tự order-flow imbalance ở trên — đã có bản thô lưới giờ. | Giống lý do order-flow imbalance: window ngắn hơn, không bị trung bình hoá trong 1 giờ. |
| Book-pressure trước pump (đổi book imbalance ngay trước biến động giá mạnh) | **CHƯA CÓ**. | Đặc thù: chỉ có ý nghĩa NẾU sổ lệnh dịch chuyển TRƯỚC khi giá dịch chuyển (leading indicator) — đây chính là giả thuyết cốt lõi cần kiểm chứng, klines không thể trả lời câu hỏi "cái gì đến trước". |
| Cụm thanh lý (liquidation cluster, từ forceOrder) | **CHƯA CÓ và KHÔNG lấy được miễn phí dạng lịch sử** — Binance chỉ phát `forceOrder` qua WebSocket real-time, xác nhận qua forum dev.binance.vision KHÔNG có REST lịch sử. Collector tự viết trên Oracle (`derivs_store/`, chạy 8 ngày) đang thu thập real-time từ nay, nhưng lịch sử quá khứ chỉ có thể mua lại từ Tardis (nếu họ có lưu channel `forceOrder`/`liquidation` — CẦN XÁC NHẬN riêng, chưa kiểm tra trong khảo sát này). | Cụm thanh lý là nguồn biến động giá KHÔNG liên quan đến thông tin cơ bản — mang tính cơ học (margin call chain), có thể là edge thực sự khác biệt hoàn toàn so với price-based feature. |
| Spot-perp basis (nếu mua thêm data spot) | **Có một phần** — hệ thống có `funding` ở lưới giờ (funding rate đã phản ánh basis dài hạn), nhưng basis tức thời (spot mid vs perp mid) không có. | Funding rate là basis đã "làm mượt" qua công thức TWAP 8h của Binance; basis tức thời dao động nhanh hơn nhiều và có thể dẫn funding rate — thêm thông tin sớm hơn. |

## 4. Kế hoạch sử dụng nếu mua (theo khung `PREREG_FS`)

1. **Pre-registration bắt buộc TRƯỚC khi chạy** bất kỳ đánh giá nào trên feature mới — viết
   `docs/PREREG_MICROSTRUCTURE_<TEN>.md`, commit, KHÔNG sửa sau khi thấy kết quả (luật §0.2).
2. **k = số feature mới thêm vào** một lần thử nghiệm — đếm CHÍNH XÁC trước khi chạy (ví dụ nếu
   thử 6 nhóm feature ở bảng mục 3 cùng lúc với vài biến thể window mỗi nhóm, k có thể lên 15-20 —
   phải khai báo con số cụ thể trong pre-reg, không phải khai báo "một vài feature").
3. **Ngưỡng CI dùng `inflate(k) = sqrt(2·ln(k))`** đúng công thức đã dùng ở các vòng feature-
   selection OHLCV trước — áp dụng y hệt, không nới lỏng chỉ vì đây là "nguồn dữ liệu mới, có vẻ
   hứa hẹn hơn". Nguồn dữ liệu mới không phải lý do hạ chuẩn thống kê.
4. **Đối chứng nhiễu (noise control feature)** — thêm ít nhất 1-2 feature nhiễu ngẫu nhiên
   (permutation của feature thật, hoặc random walk cùng phân phối) vào CÙNG batch thử nghiệm để
   có baseline "nhiễu artifact do mẫu nhỏ".
5. **Chấm điểm noise control PHẢI trên tập CONFIRM, không phải SELECT** — đúng bài học rút ra từ
   các vòng FS trước (feature selection trên SELECT rồi confirm trên CONFIRM để tránh overfit tập
   chọn feature).
6. **Đo rank-IC/edge5 OOS TRƯỚC khi thử sim đầy đủ** — không nhảy thẳng vào chạy sim tốn tài
   nguyên Oracle nếu rank-IC/edge5 đã không vượt ngưỡng CI đã inflate.
7. Chỉ khi (3)-(6) pass mới đưa feature vào pool train XGBoost S1 chính thức và chạy sim so sánh
   với incumbent T170.

## 5. Timeline ước tính

| Giai đoạn | Thời gian ước tính | Ghi chú |
|---|---|---|
| Khảo sát (tài liệu này) | Đã xong (2026-09-20) | Chờ MASTER/Uni duyệt |
| Thí nghiệm free trước (aggTrades order-flow, mục 2.2a) | 1-2 tuần | KHÔNG tốn tiền mua data, chỉ tốn compute — nên làm TRƯỚC khi quyết định mua L2, có thể loại bớt rủi ro "mua rồi vẫn null" |
| Nếu free-experiment có tín hiệu → đàm phán quote thật với 1-2 nhà cung cấp (ưu tiên Tardis) | 1-2 tuần (chờ sales phản hồi, xin sample data để verify gap/format) | Bắt buộc tải sample 1 symbol × vài ngày để verify chất lượng trước khi ký |
| Mua + backfill L2 subset 60 symbol × 48 tháng | 2-4 tuần (tuỳ tốc độ tải, rate-limit từ provider, băng thông Oracle) | Không chiếm RAM/CPU của box đang chạy sim/live — nên dùng máy xử lý riêng nếu có |
| Xử lý raw → feature 15m/1h + xoá raw khỏi Oracle | 1-2 tuần | Pipeline streaming-through như mục 2.4 |
| Pre-registration + đánh giá rank-IC/edge5 OOS theo khung PREREG_FS | 1-2 tuần | Có thể null — đây là kết quả hợp lệ, phải báo cáo dù null |
| **Tổng (nếu đi hết, có kết quả đầu tiên)**: | **~6-11 tuần kể từ ngày duyệt mua** | Không tính thời gian chờ nếu MASTER/Uni cần thời gian cân nhắc quyết định mua |

## 6. Tóm tắt khuyến nghị

- **Làm miễn phí trước**: tận dụng `is_buyer_maker` trong aggTrades bulk (đã có sẵn, free) để
  build lại order-flow-imbalance/aggressive-buy-ratio ở window ngắn (1-5 phút) cho TOÀN universe,
  test theo khung PREREG_FS. Nếu null → tiết kiệm toàn bộ ngân sách mua L2, và cũng là bằng chứng
  mạnh hơn cho giả thuyết "cạn kiệt thông tin" áp dụng cả cho microstructure, không chỉ OHLCV.
- **Nếu cần mua L2**: **Tardis.dev, gói Perpetuals, tier Academic hoặc Solo** là lựa chọn đáng cân
  nhắc nhất trong 4 nhà cung cấp — vì (a) có bulk download `.csv.gz` sẵn (khớp mô hình xử lý
  streaming-through đề xuất), (b) licence cho phép rõ ràng "task-specific quantitative models"
  cho backtesting, (c) giá thấp nhất trong nhóm có bulk historical thật ($350-1,200/tháng tuỳ
  tier, billing năm). Cảnh báo: tier Academic/Solo/Professional giới hạn lịch sử 4 năm — cần
  xác nhận với sales liệu 4 năm đó đủ phủ DEV 2022-01→2025-12 tại thời điểm mua hay phải nâng
  lên Business ("all available").
- **Chi phí ước tính tổng** (nếu mua Tardis Academic/Solo, billing năm, cho subset 60 symbol L2):
  **~$4,200-14,400/năm** cho data (tuỳ tier, tuỳ có cần "All Exchanges" hay chỉ "Perpetuals"),
  cộng **~$300-360/năm** lưu trữ cold archive B2 — TỔNG ƯỚC LƯỢNG THÔ **~$4,500-14,800/năm**.
  Đây là số RẤT thô dựa trên trang giá công khai, chưa qua quote thật — sai số có thể lớn theo
  cả 2 chiều tuỳ discount/negotiation và tuỳ có cần thêm gói Spot (cho spot-perp basis) hay không.
  Kaiko/Amberdata/CoinAPI hiện không đủ thông tin công khai để ước lượng chi phí đáng tin cậy,
  cần request quote riêng nếu muốn so sánh thêm.
- **Quyết định mua hay không KHÔNG nằm trong thẩm quyền agent này** — tài liệu này chỉ để
  MASTER và Uni tham khảo.
