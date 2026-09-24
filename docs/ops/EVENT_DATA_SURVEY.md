# EVENT_DATA_SURVEY — khảo sát nguồn dữ liệu sự kiện rời rạc (2026-09-20)

> **Phạm vi**: đây CHỈ LÀ khảo sát nguồn dữ liệu bên ngoài cho giả thuyết "driver cấu trúc
> pump/dump altcoin là các sự kiện rời rạc (unlock, listing/delisting, leverage tier change,
> funding cực trị chéo sàn) chứ không phải hình chiếu liên tục của giá/volume". KHÔNG có
> feature nào được sinh ra, KHÔNG có pre-registration thí nghiệm nào được viết trong task này.
> Bước sinh `feat_events_x1.parquet` + `docs/PREREG_FS_EVENTS.md` (nếu được quyết định làm)
> phải là một task RIÊNG ở vòng sau, chờ kết quả phân rã alpha/beta của incumbent hiện tại.
>
> Ba câu hỏi chuẩn áp cho mọi nguồn: **(a)** phủ lịch sử tới năm nào, **(b)** ước lượng % symbol
> trong universe futures Binance USDT-M (~300 symbol) có dữ liệu khớp, **(c)** độ chính xác
> timestamp (ngày/giờ) và có phân biệt announcement-date vs effective-date không.

## 0. Kết luận tổng thể (đọc trước)

🔴 **Không có nguồn miễn phí nào phủ lịch sử unlock đáng tin cậy từ trước 2023 với đủ
số symbol, và nguồn duy nhất có vẻ đủ sâu (CryptoRank Pro, Tokenomist) đều KHÔNG phân biệt
announcement-date vs effective-date trong dữ liệu trả về** — đây là rủi ro lookahead-bias
nghiêm trọng nhất nêu ở mục 1.4. Listing/delisting trên Binance có nguồn miễn phí tốt
(announcement archive, có ngày công bố rõ ràng, archive sâu nhiều năm) nhưng chỉ giải quyết
1/4 loại sự kiện. Leverage tier change không có nguồn lịch sử có cấu trúc (chỉ có tin tức rời
rạc, phải tự crawl). Funding rate cực trị chéo sàn thì dữ liệu nguồn (funding rate lịch sử)
sẵn có và miễn phí trên cả 3 sàn — nhưng đây là bước "tính lại từ chuỗi liên tục", không phải
một nguồn sự kiện rời rạc độc lập, nên rủi ro thấp nhưng cũng ít có prior cao như 3 loại kia.

**Khuyến nghị**: DỪNG ở khảo sát cho nhánh unlock (rủi ro lookahead + chi phí trả phí +
độ phủ không rõ ràng trước khi kiểm chứng thủ công). Nhánh listing/delisting là ứng viên khả
thi nhất để làm tiếp (nguồn miễn phí, đáng tin, announcement date rõ ràng) — nhưng việc sinh
feature thật (`feat_events_x1.parquet`) và viết `docs/PREREG_FS_EVENTS.md` phải chờ quyết định
ở vòng sau, sau khi có kết quả phân rã alpha/beta của incumbent. Task này không tự làm tiếp.

---

## 1. Token unlock schedule

### 1.1 DefiLlama `/unlocks`

| Câu hỏi | Trả lời |
|---|---|
| (a) Lịch sử tới năm nào | **Không rõ / có khả năng KHÔNG có lịch sử sâu qua web UI miễn phí.** Trang `defillama.com/unlocks` (đọc 2026-09-20) chủ yếu hiển thị **upcoming unlocks** ("Upcoming Unlocks 7d/30d") và "Past 24h Top Unlocks" — tức tầm nhìn ngược chỉ khoảng 24h trên trang tổng. Trang chi tiết từng token (vd. `defillama.com/unlocks/arbitrum`) có đếm ngược sự kiện tương lai và một bộ đếm "70/74 events" gợi ý có pagination cho lịch sử đầy đủ, nhưng không xác nhận được độ sâu quá khứ (không thấy ngày lịch sử cụ thể trong lần đọc). Cần kiểm tra thủ công thêm bằng cách nhấp qua UI hoặc gọi endpoint thật.|
| (b) % symbol khớp universe | Trang liệt kê tổng **370 protocol** được theo dõi lịch unlock. Universe futures Binance USDT-M ~300 symbol gồm nhiều memecoin/token cũ không có vesting schedule chính thức (không unlock theo lịch, đã full-circulating từ lâu) — ước lượng khớp thực tế nhiều khả năng **~20-40%** (cần đối chiếu danh sách cụ thể, chưa làm ở bước này).|
| (c) Độ chính xác timestamp / announcement vs effective | API (`/api/emissions`, `/api/emission/{protocol}`) là **Pro API only** ($300/tháng, base `pro-api.llama.fi/{API_KEY}/...`), và tài liệu công khai không mô tả rõ schema trả về (field timestamp, category). **Không có bằng chứng nào cho thấy DefiLlama phân biệt "ngày công bố lịch vesting" (thường là ngày TGE/whitepaper) với "ngày unlock hiệu lực"** — đây là dữ liệu tokenomics tĩnh (lịch cố định định nghĩa từ đầu dự án), nên về lý thuyết ngày công bố ban đầu ≠ ngày mỗi lần unlock xảy ra, nhưng cả hai đều có thể đã biết công khai từ lâu trước khi unlock effective — **KHÔNG có trường announcement_date riêng trong dữ liệu quan sát được**. |

**Đánh giá**: Có tiềm năng (nhiều protocol, brand uy tín, dùng rộng rãi trong ngành) nhưng
(1) endpoint có cấu trúc bị khoá sau Pro paywall $300/mo, (2) độ sâu lịch sử thực tế của
web UI miễn phí không xác nhận được là đủ xa (2021-2022), (3) không có cột phân biệt
announcement/effective. Cần một bước kiểm chứng thủ công (đăng ký thử Pro 1 tháng, hoặc
xin sample data) trước khi tin tưởng dùng làm nguồn chính — KHÔNG làm ở bước này.

### 1.2 CryptoRank

| Câu hỏi | Trả lời |
|---|---|
| (a) Lịch sử tới năm nào | Theo trang pricing chính thức (`cryptorank.io/public-api/pricing`, đọc 2026-09-20): tier **Sandbox (free)** không có "Token unlocks & vesting" (chỉ market data cơ bản). Tính năng **"Token unlocks & vesting"** chỉ mở khoá từ tier **Pro** trở lên, với độ sâu lịch sử "**up to 5 years (daily)**"; tier **Business** cho "up to 10 years". Không nêu rõ mốc năm tuyệt đối, chỉ nêu "N năm ngược từ hiện tại" — với hiện tại 2026, 5 năm = **~2021**, nhưng đây là suy luận từ % mô tả marketing, chưa xác nhận thực tế dữ liệu unlock của một token cụ thể có tồn tại đến 2021 hay không.|
| (b) % symbol khớp universe | Trang public liệt kê "hundreds of cryptocurrencies" có vesting data — không có số liệu overlap cụ thể với universe futures Binance. Chưa kiểm chứng.|
| (c) Độ chính xác timestamp / announcement vs effective | Không tìm thấy tài liệu kỹ thuật (docs.cryptorank.io) mô tả rõ schema endpoint unlock — cố gắng fetch trang giới thiệu API v3 chỉ xác nhận "API v3 covers funding rounds, token unlocks, funds, and market data" mà không có chi tiết field. **Không có bằng chứng phân biệt announcement vs effective date.**|
| Giá | Tier Pro (tier thấp nhất có unlock data): **$4,750/năm**. Đây là mức giá đáng kể cho một nguồn chưa kiểm chứng được độ phủ/độ chính xác thực tế.|

**Đánh giá**: Giá cao, chưa kiểm chứng được nội dung trả về thực tế (chỉ có trang marketing).
Không nên mua trước khi có xác nhận rõ ràng hơn về schema và độ phủ.

### 1.3 Tokenomist (trước đây là TokenUnlocks.app / unlocks.app)

`unlocks.app/pricing` redirect sang `tokenomist.ai/pricing` — đổi thương hiệu, xác nhận đọc
2026-09-20:

| Câu hỏi | Trả lời |
|---|---|
| (a) Lịch sử tới năm nào | Tier **Standard API** ($249.95/tháng): "4 years of supply data (-2, +2 year)" — tức chỉ **2 năm về trước** từ thời điểm gọi API (2026 → **~2024**), KHÔNG sâu tới 2021/2022. Tier **Elite API** ($449.95/tháng): "6 years of supply data (-3, +3 year)" — **3 năm về trước** (2026 → **~2023**). **Không tier nào phủ lịch sử về 2021/2022** theo mô tả pricing.|
| (b) % symbol khớp universe | Không nêu số lượng token cụ thể trên trang pricing. Cần tra cứu riêng, chưa làm ở bước này.|
| (c) Độ chính xác timestamp / announcement vs effective | Có nhắc "Future Unlock Events (Second Timestamp)" — tức timestamp cấp giây cho sự kiện *tương lai*, dự báo 1 năm. Không có mô tả field riêng cho ngày công bố lịch (announcement) so với ngày hiệu lực (effective) của các sự kiện *quá khứ* đã xảy ra.|

**Đánh giá**: Rẻ hơn CryptoRank nhưng độ sâu lịch sử ("-2/+2" hay "-3/+3 year" tính từ NAY,
không phải một mốc tuyệt đối) theo mô tả **không đạt tới 2021-2022** — tức không đủ cho vùng
DEV hiện tại của dự án (2022-01 → 2025-12, theo `AGENT_RUNBOOK.md` §0.1). Đây là điểm loại
trừ quan trọng: nếu DEV window cần 2022 mà nguồn chỉ lùi được ~2-3 năm từ hiện tại, thì tại
thời điểm mua (2026) nguồn chỉ tới ~2023-2024, không phủ đủ 2022.

### 1.4 🔴 Rủi ro kỹ thuật quan trọng nhất — Lookahead bias (announcement vs effective date)

Cả 3 nguồn khảo sát (DefiLlama, CryptoRank, Tokenomist) đều trình bày dữ liệu unlock dưới
dạng **một ngày/giờ duy nhất cho mỗi sự kiện unlock** — không thấy trường nào tách riêng
"ngày lịch vesting này được công bố/biết công khai lần đầu" khỏi "ngày token thực sự unlock".
Về bản chất, lịch vesting thường được công bố **một lần, từ đầu dự án** (TGE / whitepaper /
smart contract vesting), rồi các mốc unlock diễn ra theo lịch đã biết trước rất lâu — nên nếu
dùng đúng lịch gốc, rủi ro lookahead thấp. Nhưng có **hai lớp rủi ro cụ thể** mà 3 nguồn trên
không cho cách kiểm tra:

1. **Retroactive correction**: các nền tảng này thường xuyên **cập nhật lại** lịch vesting khi
   phát hiện sai lệch on-chain (dự án trì hoãn/đẩy nhanh unlock, thay đổi tokenomics qua vote
   quản trị, sáp nhập/token swap...). Snapshot dữ liệu tải về **hôm nay (2026)** có thể đã được
   "sửa" để khớp với những gì thực sự xảy ra trên chain, khác với những gì thị trường **thực sự
   biết** tại thời điểm quá khứ tương ứng. Nếu dùng thẳng "effective date" trong dữ liệu tải về
   hiện tại làm feature cho một mốc thời gian quá khứ, đây chính là rò rỉ thông tin tương lai.
2. Không nguồn nào trong 3 nguồn công khai một trường `announcement_ts` / `first_seen_ts` để
   validate: nếu không tự lưu snapshot lịch sử của chính nguồn dữ liệu (vd. crawl định kỳ và
   lưu lại "tại ngày X, nguồn nói lịch unlock của token Y là gì"), **không thể chứng minh được**
   rằng feature dùng trong backtest chỉ dùng thông tin đã biết tại thời điểm đó.

**=> Bất kỳ ai làm bước sinh feature sau này PHẢI coi đây là rủi ro chặn cứng**: cần hoặc (i)
tìm được nguồn có trường announcement-date tường minh (chưa tìm thấy ở bước khảo sát này), hoặc
(ii) tự crawl + lưu snapshot theo thời gian từ hôm nay trở đi (không backtest được lịch sử quá
khứ một cách an toàn — chỉ dùng được cho tương lai), hoặc (iii) chấp nhận rủi ro và đo mức độ
lệch bằng cách so sánh vài trường hợp unlock nổi tiếng đã biết ngày công bố gốc (từ tin tức) với
ngày trong dữ liệu nguồn.

---

## 2. Listing / Delisting trên Binance Futures

### 2.1 Binance Announcement Archive (miễn phí, khảo sát 2026-09-20)

| Câu hỏi | Trả lời |
|---|---|
| (a) Lịch sử tới năm nào | Category **"New Cryptocurrency Listing"** (`binance.com/en/support/announcement/c-48` — id thực tế cần xác nhận lại khi crawl, đọc được nội dung nhưng URL id có thể lệch giữa các lần Binance đổi cấu trúc site) hiển thị **227 trang** phân trang; category delisting (`.../announcement/list/161`, tựa "New Coin Listings/Trading Pairs/Airdrops/Updates") hiển thị **44 trang**. Binance Futures đã "official launch" từ 2019 — announcement archive về mặt cấu trúc site nhiều khả năng phủ **từ 2019-2020** cho listing (spot+futures gộp một luồng thông báo), nhưng CẦN kiểm chứng thủ công bằng cách lật tới trang cuối để xác nhận ngày sớm nhất — bước này KHÔNG crawl hết 227 trang, chỉ xác nhận archive tồn tại và có pagination sâu.|
| (b) % symbol khớp universe | Về nguyên tắc **100%** — mọi symbol từng listed/delisted trên Binance Futures đều phải có announcement tương ứng (đây là kênh công bố chính thức duy nhất của sàn), miễn là archive đủ sâu và tìm đúng category (Futures-specific announcement như "Binance Futures Will Launch USDⓈ-Margined XXXUSDT Perpetual Contract" xuất hiện tách biệt khỏi spot listing, ví dụ tìm thấy `binance.com/en/support/announcement/detail/e7a10ca855524655ab3dea73add40ef4`).|
| (c) Độ chính xác timestamp / announcement vs effective | **Đây là điểm mạnh nhất của nguồn này**: mỗi announcement có ngày công bố rõ ràng (vd "2026-09-16" quan sát được), và với listing/delisting futures, **announcement date luôn ĐI TRƯỚC effective date** một khoảng thời gian được công bố tường minh trong chính announcement (ví dụ "Binance Will Delist USDP on 2026-09-24" — announcement ngày X nói rõ ngày hiệu lực tương lai Y). Do đó nguồn này **tự nhiên phân biệt được** hai mốc: `announcement_ts` = ngày đăng bài, `effective_ts` = ngày nêu trong nội dung bài (cần parse text, không có API JSON structured). Độ chính xác timestamp: **ngày** (không thấy giờ:phút cụ thể trên trang danh sách; trang chi tiết từng announcement có thể có giờ, chưa xác nhận).|

**Đánh giá**: Đây là nguồn khả thi nhất trong 4 loại sự kiện — miễn phí, đáng tin (nguồn chính
chủ), tự nhiên tách được announcement vs effective date, độ phủ 100% symbol về mặt lý thuyết.
Hạn chế duy nhất: cần tự crawl HTML (không có API JSON chính thức công khai cho announcement
archive) và parse ngày hiệu lực từ văn bản tự nhiên (không chuẩn hoá 100% qua các năm — cách viết
announcement có thể đổi định dạng).

### 2.2 Snapshot lịch sử `exchangeInfo` (chỉ nêu, không tự đi tìm trên Oracle)

Theo yêu cầu nhiệm vụ: nếu dự án có lưu snapshot định kỳ của `GET /fapi/v1/exchangeInfo`
(danh sách symbol `TRADING` tại mỗi thời điểm) trong quá khứ, đây sẽ là nguồn **tái tạo được
chính xác effective date** của việc một symbol chuyển trạng thái (xuất hiện lần đầu ở trạng
thái TRADING = ngày list hiệu lực; biến mất / chuyển `BREAK`/`DELISTED` = ngày delist hiệu
lực), độc lập với announcement text. Đây là nguồn **tiềm năng bổ sung** cho effective-date
chính xác tới timestamp snapshot (không phải "ngày lý thuyết" ghi trong announcement mà là
trạng thái thực tế API). Việc kiểm tra Oracle có lưu snapshot này từ khi nào (`EXCHANGE_INFO_PATH`
xuất hiện trong `AGENT_RUNBOOK.md` §2 dùng file `exchange_info_pin.json` — hiện chỉ là 1 file
"pin" tại một thời điểm, không rõ có phải chuỗi snapshot lịch sử hay không) cần MASTER hoặc
agent khác kiểm tra trực tiếp trên Oracle — nằm ngoài phạm vi khảo sát web thuần của task này.

---

## 3. Leverage tier / margin bracket changes

| Câu hỏi | Trả lời |
|---|---|
| (a) Lịch sử tới năm nào | **Không tìm thấy một nguồn có cấu trúc (dataset/API) lưu lịch sử thay đổi leverage bracket theo thời gian.** Chỉ tìm thấy các bài báo/tin tức rời rạc từng đợt Binance công bố thay đổi (ví dụ các bài từ blockchain.news, chaincatcher, panewslab, mexc.com đưa tin lại các đợt "Binance Futures Adjusts Leverage and Margin Tiers" — quan sát được các đợt tin từ 2023-10 và nhiều đợt rải rác 2024). Đây là tin tức republish lẫn nhau, không phải một index có cấu trúc theo symbol+ngày.|
| (b) % symbol khớp universe | Không ước lượng được — cần tự tổng hợp thủ công từ announcement archive của Binance (category riêng cho "Notices"/"Trading Rules Updates", khác category listing) rồi parse. Endpoint `GET /fapi/v1/leverageBracket` chỉ trả về giá trị **hiện tại**, không có lịch sử.|
| (c) Độ chính xác timestamp / announcement vs effective | Các bài announcement gốc trên Binance (dạng "Binance Futures Adjusts Leverage and Margin Tiers for Multiple USDⓈ-M Perpetual Contracts") **có ngày công bố rõ** và thường nêu rõ ngày/giờ hiệu lực cụ thể (tới UTC time trong nhiều trường hợp quan sát qua tiêu đề tin tức) — tương tự listing/delisting, announcement luôn đi trước effective. Nhưng vì KHÔNG có index tập trung, việc tổng hợp đủ để dùng làm feature đòi hỏi tự crawl toàn bộ category announcement liên quan (cần xác định đúng category id trên `binance.com/en/support/announcement/...`) và parse — khối lượng công việc crawl+parse đáng kể, độ tin cậy phủ toàn bộ ~300 symbol × nhiều năm KHÔNG được đảm bảo (rủi ro bỏ sót announcement nếu category bị nhầm hoặc Binance đổi định dạng tiêu đề qua các năm).|

**Đánh giá**: Nguồn tồn tại về nguyên tắc (announcement archive của chính Binance, giống mục 2)
nhưng KHÔNG có sẵn dưới dạng tổng hợp/structured — phải tự crawl từ đầu, độ phủ và độ tin cậy
chưa kiểm chứng được ở mức khảo sát này. Rủi ro cao hơn listing/delisting vì không rõ category
id chính xác và định dạng tiêu đề không đồng nhất.

---

## 4. Funding rate cực trị chéo sàn (nêu ngắn gọn — không phải nguồn khó tìm)

Đây không phải một "nguồn sự kiện" độc lập mà là dữ liệu **tính lại được** từ chuỗi funding
rate liên tục trên nhiều sàn — nguồn công khai, miễn phí, đã xác nhận tồn tại:

- **Binance**: `GET /fapi/v1/fundingRate` (USDⓈ-M) — funding rate history theo symbol, miễn phí,
  không cần API key cho dữ liệu public. Độ sâu lịch sử: theo symbol, từ ngày symbol đó listed
  (BTC/ETH funding có từ ~2019-2020 khi Binance Futures ra mắt).
- **Bybit**: `GET /v5/market/history-fund-rate` — tương tự, miễn phí, public.
- **OKX**: `GET /api/v5/public/funding-rate-history` (v5 API) — tương tự, miễn phí, public.

Vì đây là chuỗi liên tục (funding rate mỗi 8h) chứ không phải sự kiện công bố rời rạc, KHÔNG
có vấn đề announcement-vs-effective (funding rate là số đã settle, biết ngay tại thời điểm đó,
không có độ trễ công bố). Rủi ro chính là **kỹ thuật** (đồng bộ timestamp/symbol-mapping chéo 3
sàn, ký hiệu symbol khác nhau giữa các sàn) chứ không phải rủi ro nguồn dữ liệu — không cần đào
sâu thêm theo đúng phạm vi task.

---

## 5. Bảng tổng hợp nguồn theo 3 câu hỏi chuẩn

| Loại sự kiện | Nguồn | (a) Lịch sử tới | (b) % symbol khớp (ước lượng) | (c) Độ chính xác + announcement/effective |
|---|---|---|---|---|
| Unlock | DefiLlama free UI | Không rõ, có thể chỉ 24h-30d nhìn ngược | ~20-40% (370 protocol, nhiều không khớp memecoin futures) | Ngày; KHÔNG phân biệt announcement/effective |
| Unlock | DefiLlama Pro API ($300/mo) | Không xác nhận được (docs không mô tả) | Chưa kiểm chứng | Chưa kiểm chứng; khả năng KHÔNG phân biệt |
| Unlock | CryptoRank Pro ($4,750/năm) | Mô tả "5 năm" từ hiện tại (~2021, chưa xác nhận thực tế) | Chưa kiểm chứng ("hundreds") | Chưa kiểm chứng; khả năng KHÔNG phân biệt |
| Unlock | Tokenomist Standard/Elite ($250-450/mo) | "-2/+2" hoặc "-3/+3 năm" từ NAY → **~2023-2024, KHÔNG tới 2021-2022** | Chưa kiểm chứng | Có timestamp giây cho sự kiện tương lai; KHÔNG có announcement-date cho sự kiện quá khứ |
| Listing/Delisting Futures | Binance Announcement Archive (miễn phí) | Có khả năng từ 2019-2020 (chưa crawl xác nhận trang cuối) | ~100% (nguồn chính chủ duy nhất) | Ngày; **CÓ** phân biệt tự nhiên announcement vs effective (announcement luôn nêu ngày hiệu lực tương lai) |
| Listing/Delisting Futures | Snapshot lịch sử `exchangeInfo` (nội bộ, cần MASTER kiểm tra trên Oracle) | Tuỳ độ dài lịch sử snapshot đã lưu (chưa biết) | Tuỳ độ phủ snapshot | Timestamp snapshot = effective thực tế, không phụ thuộc văn bản announcement |
| Leverage tier change | Binance Announcement (miễn phí, không có index tổng hợp) | Rải rác từ ít nhất 2023 (theo tin tức tìm được), chưa rõ sớm hơn | Chưa ước lượng — cần tự crawl toàn bộ | Ngày, có thể có giờ; CÓ phân biệt announcement vs effective (giống mục listing) nhưng công sức crawl/parse lớn |
| Funding rate cực trị chéo sàn | Binance/Bybit/OKX funding rate history API | Theo ngày listing từng symbol từng sàn (BTC/ETH ~2019-2020) | ~100% cho symbol có future trên cả 3 sàn | Có timestamp settle chính xác; không có vấn đề announcement/effective (dữ liệu settle tức thời) |

---

## 6. Khuyến nghị hành động (KHÔNG tự làm trong task này)

1. **Unlock**: KHÔNG đủ căn cứ để tin tưởng bất kỳ nguồn nào (miễn phí lẫn trả phí) phủ lịch sử
   đáng tin cậy từ 2021-2022 với đủ symbol, và rủi ro lookahead-bias (announcement vs effective)
   chưa có nguồn nào giải quyết được rõ ràng. **Khuyến nghị: KHÔNG mua/tích hợp nguồn unlock nào
   ở vòng này.** Nếu vòng sau vẫn muốn theo hướng này, bước đầu tiên phải là xin sample data thật
   (không chỉ đọc trang pricing) từ DefiLlama Pro hoặc CryptoRank để kiểm chứng trực tiếp 3 câu hỏi
   chuẩn trên một vài token cụ thể đã biết lịch sử unlock (đối chiếu tay với tin tức gốc).
2. **Listing/Delisting**: Nguồn khả thi nhất — miễn phí, đáng tin, tự nhiên có announcement date.
   Nếu vòng sau được duyệt tiếp, việc **crawl** Binance announcement archive (futures-specific
   category) + đối chiếu với snapshot `exchangeInfo` nội bộ (nếu có) nên là bước đầu của một task
   sinh feature riêng — không làm ở đây.
3. **Leverage tier change**: Cần thêm một vòng khảo sát nhỏ để xác định đúng category id
   announcement và ước lượng khối lượng crawl/parse trước khi quyết định có đáng làm hay không —
   hiện tại độ tin cậy phủ thấp hơn listing/delisting.
4. **Funding rate cực trị chéo sàn**: Nguồn dữ liệu gốc (funding rate lịch sử 3 sàn) không phải
   vấn đề — nếu theo hướng này, việc còn lại thuần là kỹ thuật đồng bộ symbol/timestamp, để dành
   cho task sinh feature nếu được duyệt.
5. **Quyết định go/no-go tổng thể** cho việc sinh feature sự kiện (bất kỳ loại nào) nên **chờ kết
   quả phân rã alpha/beta của incumbent hiện tại** như đã thống nhất trước khi bắt đầu task này —
   khảo sát này chỉ cung cấp input cho quyết định đó, không tự đưa ra quyết định go/no-go.

---

*Khảo sát thực hiện 2026-09-20 bằng WebSearch/WebFetch (không dựa vào kiến thức huấn luyện cũ
về các API này vì chính sách/giá/tier hay đổi). Các số liệu "đọc được ngày X" phản ánh nội dung
trang web tại thời điểm khảo sát; cần xác minh lại nếu dùng để ra quyết định lớn, đặc biệt các
trang pricing có thể đổi mà không báo trước.*
