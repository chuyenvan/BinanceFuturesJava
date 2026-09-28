# RESULT — EXPORT DEV PHỦ 2026-07 → 2026-09 (AUDIT-ONLY)

> ## ⛔ 2026 VẪN LÀ HOLDOUT
> Toàn bộ dữ liệu 2026 (đặc biệt 2026-07 → 2026-09) trong tài liệu này **CHỈ DÙNG CHO AUDIT / ĐỐI CHIẾU**
> (so feature LIVE vs OFFLINE tại cùng `(ts,symbol)`, tìm nghi phạm lệch). **TUYỆT ĐỐI KHÔNG** dùng để
> chọn/hiệu chuẩn ngưỡng, chọn tham số, chọn feature, hay bất kỳ quyết định thiết kế nào.
> **2026 CHƯA UNSEAL.**

- Pre-reg chốt TRƯỚC khi tính số: `docs/prereg/PREREG_DEVEXPORT_202609_AUDIT.md` (`0a0e5d5`), bổ sung §5b
  (`2010e64`) **ghi TRƯỚC khi chạy cửa sổ 2026**. Owner duyệt 28/09 14:30 ("Ok").
- JSON nhỏ: `docs/result/RESULT_DEVEXPORT_202609_AUDIT.json`. Ngày chạy: 2026-09-28.

---

## 1. KẾT LUẬN MỘT CÂU

**Đã tái lập được pipeline export DEV bằng Python (KHÔNG chạy Java) và xác minh trên vùng giao nhau:
30/33 feature KHỚP TUYỆT ĐỐI (`max|Δ| ≤ 1e-8`, kể cả `volatilityRegime` chuỗi = 1,0000); 3 feature còn lại
(`momentum1M`, `momentum15M`, `momentumAcceleration`) chỉ lệch ở ~30/1.440 dòng do nguồn
`market_data_object` (a) đã bị ghi thêm SAU ngày sinh file DEV và (b) mất hẳn từ 2026-08-14 ⇒ nguồn trôi,
không phải sai logic. File export đã sinh và ghép được 385 phút `(ts,BTCUSDT)` với `feat_dump` LIVE;
nghi phạm lệch mạnh nhất (đã loại các feature có nguồn offline lỗi) là `basketVolSpike`, họ
`volatility15M/1H/termStructure`, `volumeSpike`, `volumeRatioUpDown`.**

## 2. PIPELINE GỐC (file:line) — VÀ ĐÍNH CHÍNH

| việc | bằng chứng |
|---|---|
| File export DEV | `~/claudedata/gate15m_v2_full.csv` — 42 cột, 2.846.461 dòng, ts **2021-01-01 00:00 → 2026-06-01 00:00 (+07)**, mtime 2026-08-29 |
| **Sinh bởi** | `src/main/java/com/binance/chuyennd/ai_ml/features/export/gate/ExportGateDataset.java`: header `csvHeader()` dòng **129**; replay `replayToCsv()` dòng **138**; entry `main()` dòng **75** (args `[start][end][outFile]`) |
| Feature / ring / xếp hạng | `.../features/export/entry/ComprehensiveMarketFeatureExtractor.java` · `.../features/export/HistoryManager.java` · `.../tradecore/CoinRankManager.java` |
| Nguồn | Aerospike `kline_1m_opt` (key `yyyyMMdd-HHmm` GMT+7, bin `data` = snappy(proto `MinuteDataFinal`: map short-symbol → 5 float32)); `market_data_object` (3 float32 **big-endian**); `funding_data` (bin `f_data` = snappy(JSON ts→rate)); `symbol_mapper` |
| **ĐÍNH CHÍNH** | `docs/archive/_cleanup_20260829/docs/PIPELINE_PROVENANCE.md` ghi nguồn là `ExportGate15mV2` — **SAI**. Header file DEV = `timestamp` + 34 cột `MarketFeatures` + 7 label (`label_oldbasket,label_ret15m,label_ret60m,label_retall15m,label_retall60m,label_max24h,label_retall24h`) = **đúng `ExportGateDataset.csvHeader()`**; `ExportGate15mV2` có thêm `label_selector,nBasketOld,nBasketSel` ⇒ khác. |

**Chạy lại bản gốc cho 2026-07→09?** Không theo đường cũ được: pipeline là **Java + Aerospike** và task
**CẤM chạy Java** ⇒ đã port sang Python `research/analysis/devexport_202609.py` (giữ nguyên công thức /
thứ tự / NaN-policy / tần suất 1 phút / warmup 48h / bucket ngày UTC như `Utils.getDate`), rồi kiểm chứng
lại trên vùng giao nhau (§3).

Nguồn đọc (READ-ONLY): kline — **242 `103.157.218.242` ns `ticker`** (có cả 2026-09) và bản sao local
`127.0.0.1:3222` ns `test` (**giống BYTE** với 242 ở vùng giao nhau: 30/30 record md5 trùng);
`market_data_object` — **chỉ có** trên local ns `test`, **mới nhất 2026-08-13**; funding — ưu tiên
**242 ns `ticker`** (store sống, đúng store hệ LIVE đang đọc), fallback local ns `test`.

## 3. KIỂM CHỨNG TÁI LẬP TRÊN VÙNG GIAO NHAU

| cửa sổ | nguồn | ghép | feature khớp tuyệt đối `max\|Δ\| ≤ 1e-8` | ngoại lệ |
|---|---|---|---|---|
| 2026-03-10 00:00 → 03-11 00:00 (+07) | local (kline+funding) | 1.440/1.440 | **30/33** | 3 (momentum×3) |
| 2026-03-10 00:00 → 03-11 00:00 (+07) | **242** (kline+funding) | 1.440/1.440 | 27/33 | momentum×3 **+ funding×3** |
| 2026-05-01 00:00 → 05-02 00:00 (+07) | local | 1.440/1.440 | **30/33** | 3 (momentum×3) |

- **Cách đúng cho phần 2026 đã chọn: funding lấy từ 242** (store sống; bản sao local **ngừng cập nhật từ
  2026-07-07** — đo được: settlement cuối của BTCUSDT ở local là `2026-07-07 23:00`, ở 242 là
  `2026-09-28 15:00`). Hệ quả: **3 feature funding chỉ khớp tuyệt đối khi dùng CÙNG store local**
  (`max|Δ| = 0,0` vs DEV) — bằng chứng DEV đã dùng store kiểu local/226; **hai store funding KHÁC NHAU**
  (đổi sang 242 thì funding lệch `max|Δ| = 9,3e-5`, corr 0,72) ⇒ ghi nhận là **sự kiện provenance**, không
  phải lỗi port.
- 3 ngoại lệ momentum: lệch ở **30/1.440 dòng**, **28 dòng DEV = 0** trong khi store hiện có giá trị;
  chạy lại cùng cửa sổ sau ~20 phút thấy `mean(momentum1M)` đổi `-0,00187589 → -0,00193070` (**store đang
  trôi tiếp**) ⇒ loại khỏi bảng nghi phạm (§5b pre-reg). `momentumAcceleration = momentum5M − momentum15M`
  kế thừa đúng sai số này.
- **Lỗi port đã gặp và ĐÃ SỬA** (ghi lại để tái lập): (a) `getAverageVolume` phải lấy bar vị trí **1..20**
  (bỏ bar hiện tại, `startIndex = head-2`), không phải 0..19; (b) proto3 **bỏ field = 0** ⇒ parser phải
  field-walk thật, khớp mẫu tag cố định sẽ **mất ~20–40% symbol**; (c) symbol trong Aerospike là **short**
  ("BTC") phải nối `"USDT"`; (d) `market_data` = float32 **big-endian**; (e) `ma20` phải **cộng float32
  tuần tự** như Java — dùng pairwise sum của numpy thì `percentAboveMA20` (một **phép đếm**) lệch 5/286
  symbol vì margin `|close−ma20|/ma20 ≈ 5e-8`.

## 4. FILE XUẤT

| mục | giá trị |
|---|---|
| đường dẫn | `~/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` (**NGOÀI repo**) |
| cửa sổ | **2026-07-01 00:00 (+07) → 2026-09-28 16:16 (+07)** (mốc cuối = phút có dữ liệu mới nhất khi chạy) |
| số dòng data | **129.137** (liên tục, **0** chỗ trống > 1 phút; 89 ngày 16h16 phút) |
| số cột | **36** = `ts` + **34 cột feature GIỐNG HỆT bản DEV** (33 số + `volatilityRegime`, cùng tên, cùng thứ tự) + `md_src` |
| tần suất | 1 dòng/1 phút, **KHÔNG de-overlap** (giống `ExportGateDataset` "MỌI PHÚT") |
| **sha256** | `3c328e54fc316bb1ca45388b1a7af687cec5433ebf008038b61a10a4f2d59daa` |
| kích thước | 14.610.639 B (gz) |
| `md_src = 0` | **68.902 / 129.137 dòng (53,4%)** ⇒ `momentum1M` = `momentum15M` = 0 do **THIẾU NGUỒN** (`market_data_object` không có record từ 2026-08-14), không phải do code |
| script + commit | `research/analysis/devexport_202609.py` @ `3f8e512` (bản chạy cuối); verify: `devexport_verify.py`; ghép: `devexport_join_live.py` |
| nguồn dữ liệu | kline + funding: **242 ns `ticker`**; `market_data_object`: local ns `test` |
| thời gian chạy | 93 ngày replay (warmup 48h), ~1.313 s |
| ghi chú tái lập | Tiến trình bị **timeout phiên shell** giết giữa chừng ở bản chạy đầu ⇒ bản chạy cuối được chạy lại **1 mạch 93 ngày** (đã tách khỏi phiên shell). File cũ (funding lấy từ local, **cùng cửa sổ**) giữ tại `~/claudedata/devexport_202609/OLD_20260701_20260928_local_funding.csv.gz` để đối chiếu. |

⚠️ **`momentum1M`/`momentum15M` của cửa sổ này KHÔNG dùng được**: 53,4% dòng = 0 do thiếu nguồn. Kéo theo
`momentumAcceleration`. Muốn dùng 3 feature này phải **backfill `market_data_object` cho 2026-08-14 → nay**.

## 5. GHÉP CẶP `(ts,symbol)` VỚI `feat_dump` + BẢNG NGHI PHẠM

- Dump LIVE (CHỈ ĐỌC): shadow `~/shadow_c3/app/feat_dump/*.csv.gz` (**111** dòng) + 242
  `/home/chuyennd/java/v_t_m/feat_dump/*.csv.gz` (**358** dòng, kéo về bằng 1 lệnh `scp`), tất cả
  **BTCUSDT**, ts 2026-09-28 08:40:06 → 15:11:06 (+07). `ts` dump là **mốc tick** (không tròn phút) ⇒
  **floor về đầu phút** khi ghép.
- **Số cặp `(ts,symbol)` ghép được: 469 dòng live ⇒ 385 phút PHÂN BIỆT** (ngưỡng pre-reg ≥ 200 ⇒ **ĐỦ MẪU**).

**Bảng so 33 feature LIVE vs EXPORT** (chỉ in các feature có |shift_sd| ≥ 0,05; `shift_sd = |Δmean|/std_export`,
`tail_ratio = max_live/p99_export`; n = 469 dòng):

| # | feature | mean_live | mean_export | shift_sd | tail_ratio | rank_corr | ghi chú |
|---|---|---|---|---|---|---|---|
| 1 | **basketVolSpike** | 1,535 | 1,161 | **+0,588** | **25,0** | **0,134** | live đuôi xa (25× p99), **không tương quan** ⇒ nghi phạm mạnh nhất |
| 2 | **volatility1H** | 5,37e-4 | 4,75e-4 | +0,515 | 1,34 | 0,527 | live cao hơn |
| 3 | **volatilityTermStructure** | **1,431** | **1,262** | +0,479 | 1,13 | 0,581 | cùng hướng PASS 1 (live > offline) |
| 4 | **volatility15M** | 5,21e-4 | 4,47e-4 | +0,428 | 1,34 | 0,585 | live cao hơn |
| 5 | **volumeSpike** | 1,607 | 1,084 | +0,388 | **21,7** | 0,668 | đuôi live rất xa |
| 6 | **basketMomentum15M** | 3,6e-5 | −1,50e-3 | +0,389 | 3,55 | 0,534 | lệch dấu |
| 7 | **volumeRatioUpDown** | 4,32 | 2,57 | +0,313 | **10,5** | 0,700 | |
| 8 | basketMomentum1H | −4,27e-3 | −5,75e-3 | +0,254 | 3,38 | 0,675 | |
| 9 | volatility1M | 4,11e-4 | 3,52e-4 | +0,177 | 1,90 | 0,561 | |
| 10 | distMA20 | −4,33e-4 | −3,01e-4 | −0,133 | 1,62 | 0,871 | |
| 11 | percentAboveMA20 | 0,3788 | 0,4035 | −0,092 | 1,03 | 0,920 | |
| 12 | rsi14 / basketRsi14 | 44,37 / 44,89 | 45,46 / 45,68 | −0,075 / −0,072 | 1,08 / 1,03 | 0,886 / 0,887 | live thấp hơn |
| 13 | advanceDeclineRatio | 1,976 | 1,913 | +0,023 | 1,62 | 0,985 | |
| 14 | marketBreadthStrength | 0,4293 | 0,4237 | +0,023 | 1,04 | 0,993 | |

**Đã KHỚP (không phải nghi phạm):** `momentum24H` (rank_corr **0,9998**), `momentum4H` (**0,9997**),
`momentum1H` (**0,9969**), `trendStrengthETH` (**0,9975**), `volatility24H` (**0,9874**),
`advanceDeclineRatio` (0,985), `marketBreadthStrength` (0,993), `trendConsistency`, `btcDominance`,
`hourOfDay/dayOfWeek/weekOfMonth/monthOfYear` (khớp tuyệt đối — instrument OK).

**Đã LOẠI khỏi bảng nghi phạm (có lý do, không phải bằng chứng lệch):**
- `momentumAcceleration` — |shift_sd| = 12,67 NHƯNG export = 0 do `momentum15M` = 0 **thiếu nguồn**;
- `momentum1M`, `momentum15M` — export = 0 (thiếu nguồn `market_data_object`; live tính nội tuyến từ chính
  batch kline — xem `DetectEntrySignal2TradeNormal.java:254-257`, khác đường với `ExportGateDataset:139`);
- `fundingRateRaw / fundingRateAvg24H / fundingRateTrend` — |shift_sd| 3,35/1,29/0,89 NHƯNG **giá trị tuyệt
  đối cực nhỏ** (|Δmean| ~ 7e-6 ÷ 1e-5 ≈ 0,001%) và hai store funding khác nhau (§3) ⇒ **chưa kết luận**,
  cần đối chiếu lại bằng đúng store mà LIVE đọc (**đã dùng 242**, vẫn lệch ⇒ đáng theo dõi, xem §6).

## 6. CẦN THÊM GÌ

1. **Backfill `market_data_object`** cho 2026-08-14 → nay (hiện thiếu 100%) ⇒ mới dùng được 3 feature
   `momentum1M/15M/acceleratio`: cần tối thiểu **phủ 08:40 → 15:11 ngày 2026-09-28** để ghép cùng dump.
2. **Dài hoá dump LIVE**: hiện 385 phút trong 1 ngày (BTCUSDT). Đề nghị ≥ **7 ngày** (1 chu kỳ funding đầy
   đủ + nhiều regime) và ≥ 2.000 dòng để tách "lệch do regime 1 ngày" khỏi "lệch do pipeline".
3. **Đối chiếu funding**: chạy 1 lần đọc CÙNG store với hệ LIVE (242) và log lại `fundingRate*` từng phút
   của live để xác định lệch do basket hay do giá trị funding.
4. Nếu muốn kiểm định sâu `basketVolSpike/volatility*`: instrument thêm `nBasket` + đầu mối `getSumVolume`
   cho live (dump hiện không có) — không cần cho kết luận hiện tại.

## 7. MỤC BỎ / KHÔNG LÀM (và lý do)

- **KHÔNG** dùng số 2026 cho bất kỳ quyết định thiết kế nào. **2026 vẫn holdout** (chưa unseal).
- **KHÔNG** chạy Java / sim / WFO. **KHÔNG** ghi/sửa/restart/kill trên Oracle/242; chỉ `get` (Aerospike
  READ-ONLY) + 1 lệnh `scp` kéo dump.
- **KHÔNG** xuất 7 cột label (`label_*`) — không cần cho audit, lại cần dữ liệu ngày kế tiếp.
- **BỎ** `volatilityRegime` khỏi bảng so 33 feature (chuỗi, không thuộc V3FULL) nhưng VẪN ghi ra file và đã
  kiểm match **1,0000**.
- **Loại** khỏi nghi phạm: `momentum1M/15M/acceleration` + (chờ xác minh) `fundingRate*` — xem §5.
- **KHÔNG** kết luận "feature bị CUT" — mẫu vẫn là **1 ngày / 1 symbol**; đây là **đề nghị**, chưa phải kết
  luận nhân quả.

## 8. PROVENANCE

- Code: `research/analysis/devexport_202609.py`, `devexport_verify.py`, `devexport_join_live.py`,
  `devexport_merge.py`, `devexport_finalize.py`.
- Commit chuỗi: `0a0e5d5` (prereg) → `2010e64` (§5b) → `b859aa7` (port+verify) → `215b713` (fix ma20 +
  join tool) → `3f8e512` (funding 242 + cache + pool) → commit của tài liệu này.
- File xuất: sha256 `3c328e54fc316bb1ca45388b1a7af687cec5433ebf008038b61a10a4f2d59daa`, 129.137 dòng, 36 cột.
- JSON: `docs/result/RESULT_DEVEXPORT_202609_AUDIT.json` (sha256/ranges/kết quả verify + join).
- **Không** đưa file dữ liệu vào repo (để ngoài, `~/claudedata/devexport_202609/`).
