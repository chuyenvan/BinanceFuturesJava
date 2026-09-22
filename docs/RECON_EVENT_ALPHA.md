# RECON_EVENT_ALPHA — nguồn dữ liệu listing/delisting cho trigger độc lập MOM15 (BƯỚC 1, 0-sim)

> **Loại tài liệu:** RECON đọc-code + web (0-sim, 0-build, 0-Java). KHÔNG sinh feature, KHÔNG backtest.
> Mục đích: ra cổng GO/NO-GO cho việc thiết kế một feature/trigger sự kiện listing/delisting làm
> nguồn admission SONG SONG, không tương quan gate MOM15 (T170 = SIM_GATE_DYN_SCALE=1.70 trên
> SIM_MIN_MOMENTUM_15M=0.008). Kế thừa `docs/EVENT_DATA_SURVEY.md` (c9c5c23) + `docs/TASK_D...design.md`.
> Thực thi: agent RECON (Opus). Review: MASTER. Chủ quyết định: Uni.

## 0. TL;DR — VERDICT: **GO CÓ ĐIỀU KIỆN** (đi tiếp BƯỚC 2, đo forward-return trước khi build)

- **Nguồn:** FREE + causal-safe + coverage DƯ. Nội bộ dự án ĐÃ CÓ sẵn timestamp sự kiện dạng data-observed
  (không cần crawl để lấy effective date). Ba tiêu chí cổng data (causal / coverage / free) đều PASS.
- **RED FLAG chặn (mới, từ project memory):** Uni **long-only 1x, cực kỳ né short**. Điều này giết
  nhánh alpha rõ ràng nhất (delisting→dump→SHORT) — không dùng được. Nhánh DÙNG được (listing→pump→LONG)
  có prior YẾU/dấu KHÔNG chắc cho perp (nhiều perp mới bơm rồi xả). Vì vậy GO chỉ để **đo dấu (sign) của
  forward-return post-listing ở BƯỚC 2** — rẻ (CPU, 0-sim) và ĐÚNG là chỗ để bác/nhận giả thuyết. Nếu
  BƯỚC 2 cho forward-return listing-long ≤ 0 sau cost → NO-GO tại đó, ghi power_wall.
- **Không phải NO-GO ở recon** vì data tốt thật (free, causal, dư event); chặn ở đây là phí data tốt.
  Nhưng dấu alpha là RỦI RO số 1, không phải nguồn dữ liệu.

---

## 1. Nguồn listing/delisting (câu hỏi 1) — FREE, và nội bộ đã có sẵn

Có **BA lớp nguồn**, xếp theo độ hữu dụng cho backtest causal:

### 1.1 (TỐT NHẤT, đã có sẵn) `symbol_lifecycle` nội bộ — data-observed, causal by construction
- TASK-010 (RAN-DONE, Kaggle 2026-06-14) đã build set Aerospike `symbol_lifecycle` (ns `ticker`): **809 record**,
  mỗi symbol có `{firstSeen, lastSeen, status, delistTs?}`, phân loại LIVE/DATA_INCOMPLETE=629/**DEAD=180**.
  Nguồn: quét `kline_1m_opt` (firstSeen/lastSeen thực tế có data) + đối chiếu `exchangeInfo` (TRADING vs delist).
- `firstSeen` = **ngày listing HIỆU LỰC quan sát từ data** (phút kline đầu tiên). `delistTs≈lastSeen` = **ngày
  delist hiệu lực**. Đây là timestamp **causal by construction**: ta chỉ "biết" symbol tồn tại khi kline của nó
  xuất hiện — không thể rò rỉ tương lai.
- Full backfill đã làm (TASK-001/003/004): coverage 750 symbol USDT-perp vs universe data.vision 732 → **survivorship
  đã xử lý**, coin chết (LUNA/FTT/RAY/SRM/WAVES…) CÓ trong dataset → delist event có data để đo.
- ⚠️ set nằm trên Aerospike (226/242) — recon này KHÔNG query trực tiếp được (VM không SSH tới Oracle được, xem §7).
  Số liệu trích từ tài liệu TASK-010.

### 1.2 (FREE, public) `GET /fapi/v1/exchangeInfo` — có `onboardDate`
- Xác nhận qua docs Binance (2026-09-22): mỗi symbol có **`onboardDate`** (vd 1598252400000), **`status`** (TRADING…),
  **`deliveryDate`**. Endpoint **PUBLIC, không cần API key, IP weight 1** (giống aggTrades/openInterest đã dùng ở TASK3).
- `onboardDate` = **effective listing date** (KHÔNG phải announcement). Hạn chế: chỉ là **snapshot HIỆN TẠI** →
  symbol đã delist KHÔNG còn trong exchangeInfo hiện tại (cần lifecycle §1.1 hoặc announcement §1.3 cho delist).

### 1.3 (FREE, public) Binance Announcement Archive — có CẢ announcement date + effective date
- Kế thừa EVENT_DATA_SURVEY §2: category "New Cryptocurrency Listing" + category delisting là **miễn phí**, archive
  sâu (khả năng từ 2019-2020), **~100% symbol** (kênh công bố chính chủ duy nhất). Mỗi bài **tự nhiên tách 2 mốc**:
  `announcement_ts` = ngày đăng, `effective_ts` = ngày nêu trong nội dung ("Will delist … on YYYY-MM-DD").
- Web xác nhận 2026-09: delisting announcement khiến giá **rớt trước ngày hiệu lực** ("traders rush for the exit"),
  và Binance có FAQ delisting công khai. Hạn chế: phải crawl HTML + parse ngày từ văn bản (không có API JSON chuẩn).

**Kết luận nguồn:** dùng §1.1 (lifecycle, effective causal) làm xương sống cho backtest; §1.2 bổ sung onboardDate cho
symbol còn sống; §1.3 chỉ cần khi muốn có **announcement_ts** (chỉ hữu ích cho nhánh delist-avoid, xem §4). **Tất cả FREE.**

## 2. Coverage lịch sử 2021-2025 (câu hỏi 2) — DƯ

| Loại event | Số lượng (từ lifecycle/coverage) | Đủ ý nghĩa thống kê? |
|---|---|---|
| **Listing** (firstSeen trong cửa sổ) | universe tăng ~140 (2021) → ~750 (2025) ⇒ **~600 listing thật** trong 2021-2025 (loại left-censored firstSeen≈2021-01) | Dư (hàng trăm) |
| **Delisting** | **DEAD=180** (delistTs≈lastSeen) | Dư (hàng trăm) |

Cửa sổ phủ: 2021-01 → nay (data.vision monthly klines, đã full backfill). Đủ trùng DEV window (2022-01→2025-12).
⚠️ CAVEAT xác minh ở BƯỚC 2: symbol listing 2022-2025 có klines từ chính firstSeen (tốt); cần confirm early-days data
(giờ/ngày đầu sau listing) đủ dày để đo edge — kiểm khi build.

## 3. Timestamp causal (câu hỏi 3)

- **Listing-LONG (nhánh dùng được):** rủi ro lookahead ≈ **0 by construction**. Perp KHÔNG tồn tại trước effective →
  không thể trade trước đó; vào lệnh AT/AFTER `firstSeen` (hoặc onboardDate) là causal tuyệt đối. announcement date
  KHÔNG liên quan cho việc trade perp (chỉ liên quan pump SPOT trước đó, không trade được bằng perp).
  ⇒ RÀNG BUỘC 1 (design) **thoả** cho listing-long mà không cần announcement_ts.
- **Delisting:** `delistTs`/`effective_ts` biết trước từ announcement (announcement→effective có gap công bố tường minh).
  Nếu chỉ trade SAU effective thì causal; nhưng edge delist nằm Ở TRƯỚC effective (dump) → muốn khai thác phải dùng
  announcement_ts (§1.3) làm mốc causal. Với long-only, xem §4 (chỉ dùng làm avoid-filter).
- **Missingness (RÀNG BUỘC 2):** event chỉ phủ subset symbol-ngày (ngày quanh firstSeen/delistTs) → NaN-mask tự thành
  chỉ báo. Ghi nhận: BƯỚC 2 phải chạy noise-control với **cùng NaN-mask** như candidate (bài học OFI) — nếu noise cũng
  "thắng" thì không quy cho nội dung event.

## 4. Giả thuyết alpha đo được (câu hỏi 4) — méo vì long-only

**RÀNG BUỘC KHẨU VỊ (project memory):** Uni long-only 1x, né short (unlimited pump risk, stop-hunt). ⇒

- **H_list (LONG, nhánh DÙNG được):** sau `firstSeen` một cửa sổ ngắn (candidate: t+1h…t+72h, đo nhiều horizon),
  perp mới có **drift/momentum dương** (hype listing) → vào LONG sớm. Hình dạng edge kỳ vọng: dương những giờ/ngày đầu
  rồi phân rã. **Prior YẾU/không chắc:** literature "listing pump" chủ yếu là SPOT (pump lúc announcement, không trade
  được bằng perp); nhiều perp altcoin mới **xả sau hype** → dấu forward-return long CÓ THỂ ≤ 0. ĐÂY LÀ GIẢ THUYẾT
  PHẢI TEST DẤU TRƯỚC ở BƯỚC 2.
- **H_delist (SHORT → KHÔNG dùng được):** trước `effective_ts`, symbol delist **dump** → short. Web xác nhận dump có
  thật. Nhưng **long-only ⇒ loại**. Chỉ còn giá trị **avoid-filter**: không mở/không giữ LONG vào symbol sắp delist
  (dùng announcement_ts causal). Đây là **risk filter trên lệnh đã/đang có**, KHÔNG phải nguồn cược ĐỘC LẬP MỚI ở
  ngày MOM15 im ⇒ **không đạt mục tiêu "tăng số cược độc lập"**.

**Hệ quả:** mục tiêu "thêm cược độc lập ở ngày MOM15 im" **chỉ khả thi qua H_list (listing-long)**. Toàn bộ GO/NO-GO
thực chất treo vào dấu của H_list.

## 5. Độc lập MOM15 thật (câu hỏi 5) — rất khả năng CAO, chưa recompute được

- **Không recompute được overlap ở recon này:** `printDone.csv` T170 ở `/home/ubuntu/java/devrun/X1_GS_T170_2021_REPRO/`
  trên Oracle — VM không SSH tới được (port 22 unreachable, §7). Không có bản T170 entry-day trong repo mounted.
- **Lập luận cấu trúc (mạnh):** T170 entry = selector top-8 theo rank 15m momentum TRÊN coin đã có lịch sử/thanh khoản.
  Symbol NGÀY LISTING = coin mới toanh, chưa có lịch sử 15m, gần như không lọt selector. ⇒ event-day (quanh firstSeen)
  và T170-entry-day gần như rời nhau. Khớp kết quả prior **0/709 overlap** (task nêu). Cơ chế khác hẳn (momentum-15m
  vs sự-kiện-vòng-đời) ⇒ ICC kỳ vọng thấp → cược độc lập THẬT (khác breadth = cùng cơ chế → correlated).
- **BƯỚC 2 phải làm:** trên Oracle, lấy danh sách firstSeen (lifecycle) + printDone entry-day T170 → tính lại chính xác
  #event-day KHÔNG trùng T170-entry-day (mở rộng xác nhận 0/709), báo tỷ lệ ngày MOM15-im mà có listing.

## 6. CỔNG GO/NO-GO

| Tiêu chí cổng | Kết quả |
|---|---|
| Nguồn causal-safe | ✅ listing-long causal by construction (trade sau effective); lifecycle firstSeen data-observed |
| Coverage đủ | ✅ ~600 listing + 180 delisting, 2021-2025 |
| FREE | ✅ lifecycle nội bộ + exchangeInfo(onboardDate) + announcement archive đều free |
| Giả thuyết đo được | ✅ forward-return post-firstSeen theo horizon (rank/timing tier) |
| Độc lập MOM15 | ✅ (lập luận + prior 0/709); recompute ở BƯỚC 2 |
| **Khẩu vị (long-only)** | ⚠️ delist-short loại; listing-long dấu KHÔNG chắc → **rủi ro alpha #1** |

**VERDICT: GO CÓ ĐIỀU KIỆN** — đi BƯỚC 2 để ĐO DẤU listing-long trước khi build feature. Điều kiện dừng (NO-GO tại
BƯỚC 2): forward-return listing-long ≤ 0 sau cost, HOẶC không sống qua noise-control cùng NaN-mask, HOẶC early-days
data quá thủng để đo.

### Khung đề xuất BƯỚC 2 (đo edge tầng xếp hạng, CHƯA chạy — PREREG trước)
1. **Lấy mốc event (Oracle, 0-sim):** từ `symbol_lifecycle` xuất (firstSeen, delistTs) cho toàn universe → CSV event-day.
2. **Đo forward-return TIMING (trọng tâm):** với mỗi listing, tính forward-return LONG của chính symbol đó ở các horizon
   {t+1h, 4h, 12h, 24h, 72h} kể từ firstSeen (CPU, không GPU, không equity-sim). Baseline: forward-return trung bình
   universe cùng cửa sổ (loại beta thị trường). Block-bootstrap-72h CI. **Cổng: CI loại 0 và dấu dương** thì mới tiếp.
3. **Noise-control (RÀNG BUỘC 2):** lặp lại với ngày-giả cùng NaN-mask (random symbol-day không-listing) → nếu noise cũng
   dương thì bác.
4. **Overlap MOM15 (RÀNG BUỘC độc lập):** join event-day với printDone T170 entry-day → #trùng/#không-trùng, %ngày
   MOM15-im có listing (xác nhận 0/709, mở rộng full window).
5. **Delist chỉ đo như avoid-filter** (không short): forward-return LONG của symbol trong cửa sổ [announcement, effective]
   để định lượng thiệt hại nếu lỡ giữ long — phục vụ risk, không phải cược mới.
- Verdict BƯỚC 2: có edge (dấu dương + CI loại 0 + noise không thắng + overlap thấp) → BƯỚC 3 sim admission song song;
  NULL → dừng, ghi power_wall (đường power qua data free coi như hẹp lại: còn L2 depth trả phí hoặc tích cược thật shadow).

## 7. Ghi chú thực thi / an toàn
- SSH Oracle (ubuntu@161.118.212.3): **network unreachable từ VM** (egress không mở port 22) + không có key trong VM →
  recon làm trên **bản mounted local `E:\...\BinanceFuturesJava` branch `module`** (cùng repo, remote `oracle` cấu hình sẵn).
  Không đụng shadow_c3/box242/HOLDOUT; không push; không xoá thư mục bảo vệ. `.git/index.lock` (cũ, 2026-09-21) — đợi/không xoá.
- WebFetch/WebSearch OK (đã dùng, không dùng curl/wget fetch data).
