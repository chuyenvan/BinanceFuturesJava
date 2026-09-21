# RECON_EVENT_ALPHA — Bước 1 TASK D: recon nguồn dữ liệu event listing/delisting (2026-09-21)

Thực thi theo `TASK_D_new_alpha_events_design.md` §3 (executor Sonnet). Nguồn nền: `docs/EVENT_DATA_SURVEY.md`
(commit `c9c5c23`, TASK4 bước 1, khảo sát web thuần — KHÔNG tự crawl/tải số liệu mới). Bổ sung mới ở
bước này: đọc số liệu **NỘI BỘ đã có sẵn trên Oracle** (`claudedata/universe_birth_death.csv` +
`printDone.csv` của T170) để định lượng coverage và độc lập-MOM15 — hai câu hỏi mà EVENT_DATA_SURVEY
chỉ trả lời được bằng định tính (không có số liệu Oracle thật). 0-sim, không build, không xgboost.

## 1. Nguồn listing/delisting cho universe — có 2 nguồn, bổ sung nhau

### 1a. Binance Announcement Archive (external, đã khảo sát ở EVENT_DATA_SURVEY §2.1)
FREE, chính chủ, phủ lý thuyết 100% symbol (mọi listing/delisting futures đều phải công bố qua kênh
này). Category riêng cho futures ("Binance Futures Will Launch/Delist ...") tách biệt spot. Announcement
list có phân trang sâu (227 trang listing, 44 trang delisting) — khả năng phủ từ 2019-2020 nhưng
**CHƯA crawl xác nhận trang cuối** (việc của khảo sát trước, không lặp lại ở đây). Hạn chế: không có
API JSON structured, phải tự crawl HTML + parse ngày hiệu lực từ văn bản tự nhiên (không chuẩn hoá
100% qua các năm).

### 1b. 🆕 `claudedata/universe_birth_death.csv` (nội bộ, đã có sẵn trên Oracle, MIỄN PHÍ — 0 crawl)
Phát hiện mới ở bước này: Oracle đã có sẵn file 937 symbol, cột `symbol,first_month,last_month,n_months`
— sinh ra từ chính dữ liệu kline/funding đang dùng cho sim (đối chiếu `docs/archive/.../
wfo_data_validation_20260704.md` dòng 152: dùng để đối chiếu `SymbolConsistency` với `funding.bin`).
Đây KHÔNG phải dữ liệu từ announcement mà là **ngày quan sát dữ liệu giao dịch đầu/cuối thật của
chính hệ thống** (kline THẬT bắt đầu/kết thúc) — về bản chất là "effective date" tự nhiên, không phụ
thuộc lời văn announcement, và **không có rủi ro retroactive-correction** kiểu DefiLlama/CryptoRank/
Tokenomist (§1.4 EVENT_DATA_SURVEY) vì nó phản ánh trực tiếp dữ liệu giao dịch lịch sử đã đóng băng,
không phải một trường "lịch vesting" có thể bị nhà cung cấp sửa lại sau.
**Hạn chế duy nhất**: granularity THÁNG (không phải ngày) — đủ cho recon coverage/độc lập ở Bước 1,
nhưng KHÔNG đủ cho feature ngày-cụ-thể ở Bước 2 (xem mục 6).
Raw hơn nữa (ngày chính xác) khả thi: `kaggle_data_hpo` (symlink →
`java/simulator/kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz`) có file NGÀY từ 2021-01-01 — scan
symbol-ID xuất hiện lần đầu/cuối trong các file này sẽ cho ngày chính xác, KHÔNG cần dữ liệu trả phí,
nhưng cần code Java/parser đọc format `.bin.gz` (chưa làm ở bước 0-sim này, để dành Bước 2 nếu GO).

## 2. Timestamp — causal-safe cho LISTING, cần thêm nguồn cho DELISTING-sớm

- **Listing**: hiệu lực (effective) trùng ngày symbol có dữ liệu giao dịch đầu tiên — dùng ngay ngày
  đó làm mốc "ngày 0" của cửa sổ đo (vào sau khi symbol đã bắt đầu giao dịch) là **causal tuyệt đối**,
  không cần biết ngày announcement (Binance luôn thông báo TRƯỚC khi contract mở, nên biết trước ngày
  hiệu lực không phải lookahead — ngày hiệu lực chính là ngày sự kiện xảy ra).
- **Delisting** — có 2 dạng giả thuyết, causal-safe khác nhau:
  - (i) *post-delisting* (không áp dụng — sau khi delist thì không còn giao dịch được, vô nghĩa).
  - (ii) *pre-delisting dump* (short trước khi hiệu lực, trong cửa sổ announcement→effective đã biết
    công khai) — đây MỚI cần `announcement_ts` tách biệt `effective_ts`, và nguồn 1b (birth_death)
    KHÔNG có trường này (chỉ có effective/last-trade-month). Phải dùng nguồn 1a (Binance Announcement
    Archive, đã xác nhận announcement luôn đi trước effective, tường minh trong văn bản) — CHƯA crawl
    thật ở bước này.
- ⇒ **GO ngay cho nhánh listing** (chỉ cần nguồn 1b, nội bộ, 0 crawl); **delisting cần crawl thêm
  nguồn 1a trước khi build feature** — không phải NO-GO nhưng có thêm một bước tiền đề (khác token
  unlock: unlock KHÔNG có nguồn nào tách được announcement/effective dù trả phí, delisting THÌ CÓ,
  chỉ chưa crawl).

## 3. Coverage (đo trên `universe_birth_death.csv`, DEV window 2021-07→2025-12, script `research/analysis/recon_event_coverage.py`)

| Chỉ số | Giá trị |
|---|---|
| Tổng symbol trong file | 937 |
| Symbol có birth (listing) rơi trong DEV window | **648 / 937 (69.2%)** |
| Symbol có "true death" (last_month lệch ≥2 tháng so mốc dữ liệu mới nhất 2026-06, tức không phải "còn sống") | 128/937 (13.7%) toàn kỳ, **113 rơi trong DEV window** |
| Tổng symbol-tháng có giao dịch trong DEV window (mẫu số coverage) | 16,307 |
| % symbol-tháng có birth-event | **3.97%** |
| % symbol-tháng có death-event | **0.69%** |

Birth theo năm: 2021=79, 2022=69, 2023=112, 2024=166, 2025=270 (tăng tốc — universe futures Binance mở
rộng nhanh). Death (true) theo năm: 2021=12, 2022=19, 2023=49, 2024=25, 2025=15.

⇒ **Coverage đủ để đo** (648 listing event trong 4.5 năm, mật độ 3.97% symbol-tháng — cao hơn hẳn
tần suất vào lệnh trung bình của MOM15/T170, xem mục 5). Đây là subset không ngẫu nhiên (chỉ symbol
mới/symbol chết mới có event) — **RÀNG BUỘC 2 (missingness-as-subset-indicator, bài học OFI) áp dụng
bắt buộc**: mọi noise control ở Bước 2 phải dùng đúng NaN-mask 3.97%/0.69% này.

## 4. Giả thuyết alpha đo được

- **Listing → pump/vol tăng sớm**: symbol mới list thường thiếu thanh khoản + narrative-driven (FOMO
  listing), giả thuyết chuẩn trong ngành là "pump ngắn hạn N ngày đầu, dump sau đó" (nêu trong nhiều
  case-study định tính, EVENT_DATA_SURVEY không đo được vì không có dữ liệu). Cửa sổ đo hợp lý: forward
  return 1D/3D/7D kể từ ngày birth (ngày dữ liệu đầu tiên). Đo được trực tiếp bằng `CLOSES_1H.bin`/kline
  đã có, KHÔNG cần dữ liệu mới.
- **Delisting → dump trước hiệu lực**: giả thuyết thanh khoản rút + tránh-rủi-ro trước ngày đóng
  contract. Cửa sổ đo: forward return trong N ngày TRƯỚC last-trade-date (dùng birth_death nội bộ để
  xác định ngày cuối, nhưng để BIẾT TRƯỚC ngày này khi giao dịch — cần announcement date từ nguồn 1a,
  xem mục 2).
- Cả hai đo được bằng rank-IC/forward-return CPU trên CONFIRM theo đúng RÀNG BUỘC 3 (power_wall: tầng
  xếp hạng trước, không tầng equity).

## 5. Độc lập MOM15 — bằng chứng thực đo, KHÔNG PHẢI ước lượng định tính

Đối chiếu (symbol, tháng) của 1089 lệnh T170 thật (`X1_GS_T170_2021/storage/printDone.csv`, 709 cặp
(symbol,tháng) phân biệt, 110 ngày vào lệnh phân biệt trên 1644 ngày) với (symbol,tháng) của 648 birth-
event và 113 death-event trong DEV window:

| Overlap | Số cặp trùng | % trong T170 | % trong birth/death events |
|---|---:|---:|---:|
| T170-entry-month ∩ birth-month | **0** | 0.00% | 0.00% |
| T170-entry-month ∩ death-month | **0** | 0.00% | 0.00% |

**Overlap = 0 tuyệt đối** (ở granularity tháng — mức thô nhất, nên nếu có overlap thật ở tháng thì mới
đáng lo; 0 ở tháng ⇒ chắc chắn 0 ở ngày). Diễn giải: T170 (selector S1 + gate MOM15) chọn symbol đã
thanh khoản/đã có lịch sử đủ dài để tính feature xếp hạng — symbol MỚI list (chưa có 15+ ngày dữ liệu
cho feature rk_dd_7d/ret_14d) hoặc symbol SẮP delist (thanh khoản cạn, dễ bị loại bởi bộ lọc universe)
tự nhiên KHÔNG lọt vào tập MOM15 chọn. Đây CHÍNH XÁC là cơ chế TASK D kỳ vọng (§0 file thiết kế):
trigger mới thêm cược ở symbol/ngày nơi MOM15 hoàn toàn im lặng — bằng chứng ở đây mạnh hơn "overlap
thấp", là **overlap-zero đo thật trên dữ liệu**, không phải suy luận.

Rủi ro cần lưu ý cho Bước 2/3 (không phải lý do NO-GO): (i) symbol mới list có thể KHÔNG đủ điều kiện
admit của engine sim hiện tại (MIN_NOTIONAL/precision/liquidity filter) — cần kiểm trước khi thiết kế
trigger admission thật; (ii) 648 listing event trải trên 937 symbol nhưng phần lớn KHÔNG NẰM TRONG
universe hiện hành của T170's selector (S1 chỉ rank symbol có đủ lịch sử feature) — nghĩa là trigger
mới này về cấu trúc là một ĐƯỜNG ADMISSION SONG SONG hoàn toàn tách biệt (đúng thiết kế §6 TASK D:
"admission SONG SONG với MOM15"), không phải một biến thể của gate hiện tại.

## 6. Hạn chế phải giải quyết TRƯỚC Bước 2 (không phải NO-GO, là điều kiện kèm theo GO)

1. **Granularity ngày**: `universe_birth_death.csv` chỉ có tháng. Bước 2 cần ngày chính xác (đo
   forward-return 1D/3D/7D không thể dùng mốc tháng). Việc cần làm: viết script quét
   `kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` (đã có, 2021-01-01→nay) để lấy ngày xuất hiện/biến
   mất đầu tiên của mỗi symbol-ID — thuần đọc dữ liệu đã có, không cần crawl/mua gì thêm. Đây là công
   việc đầu của Bước 2, không phải một task riêng.
2. **Delisting cần announcement_ts** nếu muốn đo giả thuyết "dump TRƯỚC hiệu lực" — cần crawl Binance
   Announcement Archive (nguồn 1a) cho danh sách + ngày công bố. Nếu Bước 2 chỉ làm nhánh LISTING
   trước (không cần announcement), có thể bỏ qua bước này tạm thời.
3. **Noise control NaN-mask**: bắt buộc theo RÀNG BUỘC 2 — control phải dùng đúng subset 3.97%/0.69%
   symbol-tháng, không dùng toàn universe làm baseline.
4. Chưa kiểm symbol mới-list có bị loại bởi bộ lọc admission cơ bản của sim (xem mục 5 rủi ro (i)) —
   nên kiểm nhanh (đọc code, không sim) trước khi PREREG Bước 2.

## 7. CỔNG GO/NO-GO (theo §3 TASK D)

| Điều kiện | Kết quả |
|---|---|
| Nguồn causal-safe | **CÓ** cho listing (effective date = ngày dữ liệu đầu, không lookahead); delisting cần thêm nguồn 1a cho nhánh "dump trước hiệu lực" cụ thể, nhưng nguồn đó đã xác nhận TỒN TẠI và causal-safe (mục 2 EVENT_DATA_SURVEY) |
| Coverage đủ | **CÓ** — 648 listing event / 4.5 năm, 3.97% symbol-tháng, tăng tốc theo năm (270 event riêng 2025) |
| Giả thuyết đo được | **CÓ** — forward-return sau ngày list (đã có kline, đo bằng CPU, không cần dữ liệu mới) |
| Độc lập MOM15 | **CÓ, mạnh** — overlap = 0/709 đo thật (không phải ước lượng) |

## ✅ VERDICT: **GO** cho TASK D Bước 2 — ưu tiên nhánh LISTING trước (0 crawl ngoài, chỉ cần rebuild
birth-date xuống granularity ngày từ dữ liệu kline đã có). Nhánh DELISTING-sớm (trước hiệu lực) là mở
rộng khả thi nhưng cần crawl thêm Binance Announcement Archive (nguồn 1a) — để MASTER quyết có làm
song song hay để sau khi có kết quả nhánh listing.

Script/số liệu: `research/analysis/recon_event_coverage.py` (mới), input `claudedata/
universe_birth_death.csv` + `java/devrun/X1_GS_T170_2021/storage/printDone.csv` (đọc, không sửa).
