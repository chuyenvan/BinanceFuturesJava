# RESULT PASS 2 — DIFF 33 FEATURE: SO SÁNH **REGIME-MATCHED** (LIVE vs EXPORT DEV)

> ## ⛔ 2026 VẪN LÀ HOLDOUT
> Toàn bộ số 2026 trong tài liệu này **CHỈ DÙNG ĐỂ AUDIT / ĐỐI CHIẾU**. **TUYỆT ĐỐI KHÔNG** dùng để
> chọn/hiệu chuẩn ngưỡng, chọn tham số, chọn feature, hay bất kỳ quyết định thiết kế nào. **2026 CHƯA UNSEAL.**

- Pre-reg chốt TRƯỚC khi tính số: `docs/prereg/PREREG_FEATDIFF_PASS2.md` (`2f24fe1`).
- Ngày chạy 2026-09-28. **CHỈ ĐỌC** Oracle + 242 (không ghi/sửa/restart/kill); **KHÔNG** chạy Java/sim/WFO.
- Tool: `research/analysis/md_inline.py` (`1c0516b`), `featdiff_pass2.py`, `featdiff_pass2_p15.py`.
- JSON: `docs/result/RESULT_FEATDIFF_PASS2.json`.

---

## 1. KẾT LUẬN MỘT CÂU

**Bịt được CẢ HAI khoảng trống nguồn**: (i) `momentum1M/15M/acceleration` **tái tạo INLINE từ dòng kline**
(không cần store `market_data_object` đã chết) — kiểm với LIVE: corr **0,9949 / 0,9995 / 0,9958**, mean khớp
6 chữ số; (ii) **store funding ĐÚNG = `103.157.218.242:3222 / ns=ticker / set=funding_data`** (đường LIVE
đang đọc, xác nhận từ `~/shadow_c3/app/config.properties`). **Kết luận quan trọng nhất:** sau khi **kiểm soát
regime** (ghép cặp **CÙNG PHÚT** live↔DEV), **p15 của LIVE gần như TRÙNG p15 của DEV tái tạo** (0,9426 % vs
0,9484 %; lệch **0,0058 pp**) ⇒ **KHÔNG có feature nào gây "cut đuôi p15"**. Chênh p15 live-vs-DEV nhìn thấy
trước đây **là do regime/cửa sổ**, đúng như cảnh báo phương pháp ở pre-reg §0. Nghi phạm còn lại chỉ là các
feature **lệch GIÁ TRỊ thật tại cùng phút** (`volatility15M/1H/termStructure`, `volumeSpike`, `basketVolSpike`,
`volumeRatioUpDown`, `funding×3`, `rsi14/basketRsi14`, `btcDominance`, `trendConsistency`) nhưng **tổng hiệu
ứng lên p15 ≤ 0,006 pp** ⇒ không phải nguyên nhân gate không pass.

## 2. VIỆC 1 — BỊT KHOẢNG TRỐNG NGUỒN

### 2.1 `momentum×3` — nguồn thật là **dòng kline**, không phải store

**Kiểm 3 cụm Aerospike (READ-ONLY, chỉ `get` key cố định)** — tìm `market_data_object` sau 2026-08-14:

| cụm | namespace | key 2026-08-13 | key 2026-08-14+ |
|---|---|---|---|
| local `127.0.0.1:3222` | `test` | **CÓ** | không có |
| 226 `161.118.212.3:3222` | `test` | **CÓ** | không có |
| 242 `103.157.218.242:3222` | `ticker` | không có | không có |

⇒ **KHÔNG có store nào còn cập nhật `market_data_object`** (chết từ 2026-08-14 ở mọi cụm; namespace `test`
không tồn tại trên 242). Đường ghi duy nhất (`DataManagerAerospikeFloatSim.saveMarketDataBatch` →
`getClientOracle()` = `AEROSPIKE_HOST_226`) **đã ngừng**.

⇒ Nguồn thật của `MarketDataObject` là **chính dòng ticker/kline**: đường LIVE tự tính **inline** trong tick
loop (`DetectEntrySignal2TradeNormal.java:254-257` → `MarketBigChangeDetector.calMarketData`); bản export đã
có sẵn `MarketDataInlineGenerator` với chú thích *"bỏ phụ thuộc ngầm vào set Aerospike `market_data_object`
(có thể thiếu/cũ)"*. Đây chính là **cách bịt đúng**: sinh inline thay vì đọc store chết.

**Đã port & KIỂM CHỨNG** (`research/analysis/md_inline.py`: `calMarketData` + `calRateChangeAvg` + `InlineMD`,
WINDOW = `NUMBER_TICKER_CAL_RATE_CHANGE` = 15):

| kiểm | n | momentum1M | momentum15M |
|---|---|---|---|
| (A) inline vs **store md** 2026-08-13 | 859 | meanAbsDiff 1,4e-5 · corr **0,9961** | 1,1e-4 · corr **0,9816** |
| (A) inline vs **store md** 2026-03-10 | 1.426 | 1,3e-4 · corr **0,9755** | 4,5e-4 · corr **0,9734** |
| (B) inline vs **LIVE dump** 2026-09-28 | **563** | meanAbsDiff 4,68e-5 · corr **0,9949** (mean live −0,002128 = inline −0,002128) | 5,59e-5 · corr **0,9995** (live −0,012550 / inline −0,012578) |

`momentumAcceleration` (= `momentum5M − momentum15M`): corr **0,9958**, meanAbsDiff 1,4e-4.
⇒ **BỊT ĐƯỢC**: 3 feature này **không còn là "chưa so được"**, và **không lệch** — độ lệch ~5e-5 là nhiễu
ticker-vs-kline, **nhỏ hơn 1 bậc** so với độ lệch thật của nhóm volatility/volume (§3).
**Cách sửa cụ thể (ĐÃ LÀM, chưa chạy lại 89 ngày — giữ box NHẸ):** thêm nhánh `--md-inline` vào
`devexport_202609.py` (gọi `InlineMD` thay `get_market_data_day`) rồi chạy lại 1 lệnh. **KIỂM END-TO-END**
qua ĐÚNG đường export: `python3 research/analysis/devexport_202609.py --start 20260928 --end 20260928
--cluster 242 --md-inline --out …` ⇒ 992 dòng, `momentum1M` **khác 0 100 %**; đối chiếu với LIVE dump
(n=565): `momentum1M` corr **0,9949** / meanAbsDiff 4,7e-5 (mean −0,002129 = −0,002129); `momentum15M` corr
**0,9995** (live −0,012560 / export-inline −0,012589). ⇒ **nhánh sửa chạy đúng, chỉ cần áp cho cả cửa sổ.**

### 2.2 `funding×3` — **đường dẫn store ĐÚNG**

- LIVE đọc (từ `~/shadow_c3/app/config.properties`): `AEROSPIKE_HOST=103.157.218.242`,
  `AEROSPIKE_PORT=3222`, `AEROSPIKE_NAMESPACE=ticker`, `AEROSPIKE_READ_CLUSTER=242`. Config 242 giống.
- **ĐƯỜNG DẪN ĐÚNG:** **`103.157.218.242:3222` / namespace `ticker` / set `funding_data` / bin `f_data`**
  (= snappy(JSON `ts→rate`), key = symbol vd `BTCUSDT`).
- Kiểm READ-ONLY: 242 `funding_data/BTCUSDT` **last ts 2026-09-28 15:00** (sống); bản sao local ns `test`
  **last 2026-07-07 23:00** (đã chết). ⇒ bản export **đã** ưu tiên 242 (commit `3f8e512`) là ĐÚNG.
- **Nghịch lý còn lại:** dù dùng 242, `funding×3` **vẫn lệch tại cùng phút** (mad 1,0e-5 ÷ 1,7e-5; tương quan
  0,891 / 0,255 / 0,897). Nghi do LIVE tính qua `fundingExtractor` nội bộ (`NUMBER_HOUR_FUNDING_CAL=30`) khác
  đường đọc store, và/hoặc 2 store funding khác nhau. **Biên độ tuyệt đối ~1,7e-5 (0,0017 %)** ⇒ vô nghĩa với p15.

## 3. VIỆC 2 — BẢNG 33 FEATURE, CÓ KIỂM SOÁT REGIME

**Dữ liệu:** LIVE **563 dòng / 457 phút** (shadow + 242, BTCUSDT, 2026-09-28); DEV `devexport_…_FULL.csv.gz`
**129.137 dòng**. **P0 — ghép cặp CHÍNH XÁC `(ts)` = 556 cặp** (cửa sổ LIVE nằm TRONG export).
**Regime decile `volatility24H` (pool chung):** LIVE chỉ ở **decile 2-4** (89/441/33 dòng); DEV trải **0-9**
(~12.900/decile) ⇒ **xác nhận LIVE = 1 regime hẹp**.

Chỉ số: **`madP`** = |Δ| trung bình **TẠI CÙNG PHÚT** (P0 — regime bị giữ CỐ ĐỊNH), `sd_pair`/`sp_pair` = shift/spearman
trên cặp P0, `cdfDev` = vị trí trung bình của giá trị LIVE trong phân bố DEV (regime-normalised, 0,5 = trung tâm),
`d_dec`/`d_hour` = FALLBACK ghép decile / decile+hour (n_hour = số dòng LIVE khớp).

| feature | madP | sd_pair | sp_pair | cdfDev | rankShfP | d_dec | d_hour | ratio |
|---|---|---|---|---|---|---|---|---|
| momentum1M | 2,1e-03 | – | −0,088 | 0,213 | −0,147 | 0,843 | 0,747 | 2,36 |
| momentum5M | 1,3e-04 | 0,014 | 0,942 | 0,445 | 0,054 | 0,153 | 0,184 | −10,2 |
| momentum15M | 1,3e-02 | – | −0,212 | 0,193 | −0,163 | 0,885 | 0,782 | 2,36 |
| momentum1H | 7,6e-05 | 0,001 | **0,995** | 0,297 | 0,201 | 0,642 | 0,621 | −11,3 |
| momentum4H | 2,9e-05 | 0,000 | **1,000** | 0,100 | 0,396 | 1,435 | 1,505 | −12,0 |
| momentum24H | 2,9e-05 | 0,000 | **1,000** | 0,134 | 0,370 | 1,145 | 1,019 | −3,75 |
| momentumAcceleration | 1,3e-02 | 12,31 | −0,230 | 0,806 | 0,267 | 0,865 | 0,758 | 2,32 |
| trendStrengthETH | 8,7e-05 | 0,001 | **0,995** | 0,388 | 0,111 | 0,318 | 0,449 | −5,24 |
| trendConsistency | 1,0e-01 | 0,018 | 0,917 | 0,780 | 0,115 | 0,080 | 0,136 | 1,57 |
| volatility1M | 1,5e-04 | 0,147 | 0,705 | 0,584 | −0,063 | 0,498 | 0,707 | 1,28 |
| **volatility15M** | 8,7e-05 | **0,371** | 0,699 | 0,687 | −0,135 | 0,944 | 1,438 | 1,28 |
| **volatility1H** | 6,5e-05 | **0,465** | 0,621 | 0,707 | −0,159 | 1,111 | 1,617 | 1,25 |
| volatility24H | 2,8e-06 | 0,108 | 0,988 | 0,348 | 0,142 | 0,490 | 1,166 | 0,82 |
| **volatilityTermStructure** | **1,7e-01** | **0,432** | 0,661 | **0,809** | −0,267 | 1,078 | 1,614 | **1,49** |
| advanceDeclineRatio | 2,0e-01 | 0,020 | 0,989 | 0,454 | 0,043 | 0,679 | 0,595 | 1,51 |
| percentAboveMA20 | 4,4e-02 | 0,082 | 0,937 | 0,363 | 0,112 | 0,593 | 0,581 | 0,79 |
| **volumeRatioUpDown** | **2,1e+00** | 0,318 | 0,942 | 0,463 | 0,042 | 0,293 | 0,514 | 1,50 |
| marketBreadthStrength | 1,7e-02 | 0,020 | 0,990 | 0,494 | 0,011 | 0,167 | 0,240 | 1,05 |
| btcDominance | 5,8e-02 | 0,029 | 0,652 | 0,528 | −0,067 | 0,264 | 0,366 | 1,08 |
| rsi14 | 3,2e+00 | 0,067 | 0,897 | 0,415 | 0,067 | 0,279 | 0,280 | 0,90 |
| **volumeSpike** | **1,1e+00** | 0,339 | 0,530 | 0,425 | −0,031 | 0,242 | 0,387 | 1,36 |
| distMA20 | 2,4e-04 | 0,115 | 0,909 | 0,408 | 0,075 | 0,391 | 0,541 | −15,0 |
| **fundingRateRaw** | 1,7e-05 | 1,202 | 0,891 | 0,716 | −0,342 | 0,786 | 0,721 | −0,04 |
| **fundingRateAvg24H** | 7,3e-06 | 2,697 | 0,255 | 0,778 | −0,334 | 0,955 | 1,213 | −0,13 |
| **fundingRateTrend** | 1,0e-05 | 0,831 | 0,897 | 0,446 | −0,078 | 0,128 | 1,015 | 30,0 |
| hourOfDay | **0,0** | 0,000 | **1,000** | 0,547 | −0,024 | 0,136 | – | 1,05 |
| dayOfWeek | **0,0** | – | **1,000** | 0,286 | 0,244 | 1,095 | 1,338 | 0,50 |
| weekOfMonth | **0,0** | – | **1,000** | 0,978 | −0,324 | 1,691 | 1,414 | 1,58 |
| monthOfYear | **0,0** | – | **1,000** | 1,000 | −0,296 | 1,523 | 1,739 | 1,13 |
| basketMomentum15M | 2,0e-03 | 0,342 | 0,791 | 0,403 | 0,136 | 0,591 | 0,869 | −1,28 |
| basketMomentum1H | 1,9e-03 | 0,216 | 0,801 | 0,275 | 0,275 | 1,079 | 0,873 | −40,7 |
| basketRsi14 | 2,2e+00 | 0,065 | 0,893 | 0,365 | 0,115 | 0,641 | 0,544 | 0,91 |
| **basketVolSpike** | **9,1e-01** | **0,460** | **0,345** | 0,438 | 0,078 | 0,224 | 0,912 | 1,17 |

**Đọc bảng:**
- **4 feature thời gian**: `madP = 0` TUYỆT ĐỐI tại cùng phút ⇒ instrument ĐÚNG. (`cdfDev` của chúng ≈ 0,98-1,00
  chỉ vì LIVE = 1 ngày — 09/2026, thứ Hai, tuần 5 — **artifact lịch, KHÔNG phải lỗi**.)
- **Khớp gần tuyệt đối tại cùng phút** (`madP` ≤ 3e-4, `sp_pair` ≥ 0,94): `momentum5M/1H/4H/24H`,
  `trendStrengthETH`, `volatility24H`, `distMA20`, `marketBreadthStrength`, `advanceDeclineRatio`.
- **Lệch giá trị THẬT tại cùng phút** (`madP` lớn theo thang feature): `volatilityTermStructure` (0,17 / giá
  trị 1,39 = **12 %**), `volumeSpike` (**~73 %**), `basketVolSpike` (**~61 %**), `volumeRatioUpDown` (**~50 %**),
  `btcDominance` (~28 %), `trendConsistency` (~42 %), `rsi14`/`basketRsi14` (~7 %/5 %), `percentAboveMA20` (~11 %),
  `volatility1H/15M/1M` (~12-37 %), `funding×3` (tuyệt đối ~1e-5).
- **`rankShfP`/`cdfDev` lớn nhưng `madP≈0`** (vd `momentum4H`: cdfDev 0,10, madP 2,9e-5) ⇒ **thuần REGIME**:
  giá trị khớp nhưng nằm ở vị trí phân bố khác ⇒ đây chính là "độ lệch giả" mà pre-reg §0 cảnh báo.
- `momentum1M/15M/acceleration`: `madP` lớn CHỈ vì DEV gốc = 0 (thiếu nguồn); **sau khi tái tạo inline, khớp
  (corr 0,9949/0,9995/0,9958)** ⇒ KHÔNG lệch.

## 4. VIỆC 3 — KẾT LUẬN PASS 2

### (1) DANH SÁCH NGHI PHẠM CHỐT (xếp hạng theo hiệu ứng regime-controlled; `n` = 556 cặp P0)

| # | feature | độ lệch tại cùng phút | có kiểm soát regime? | còn lệch? |
|---|---|---|---|---|
| 1 | `basketVolSpike` | madP 0,91 · sd_pair 0,460 · spear **0,345** | có (cùng phút) | **CÓ** (mạnh nhất) |
| 2 | `volatilityTermStructure` | madP 0,17 (**12 %**) · spear 0,661 | có | **CÓ** |
| 3 | `volatility1H` | madP 6,5e-5 (**~12 %**) · spear 0,621 | có | **CÓ** |
| 4 | `volatility15M` | madP 8,7e-5 (**~17 %**) · spear 0,699 | có | **CÓ** |
| 5 | `volumeSpike` | madP 1,1 (**~73 %**) · spear 0,530 | có | **CÓ** |
| 6 | `volumeRatioUpDown` | madP 2,1 (**~50 %**) · spear 0,942 | có | **CÓ** |
| 7 | `fundingRateRaw/Avg24H/Trend` | madP 1e-5..1,7e-5 · spear 0,891/0,255/0,897 | có | **CÓ** (biên độ vô nghĩa) |
| 8 | `rsi14` / `basketRsi14` | madP 3,2 / 2,2 (~7 %/5 %) | có | có (nhẹ) |
| 9 | `btcDominance` / `trendConsistency` / `percentAboveMA20` | 5,8e-2 / 1,0e-1 / 4,4e-2 | có | có (nhẹ) |
| – | `momentum1M/15M/acceleration` | sau khi bịt nguồn: corr ≥ 0,995 | có | **KHÔNG** (chỉ là gap) |

### (2) FEATURE LỆCH **THẬT** + KIỂU LỆCH (không do regime)

- **`volatilityTermStructure`** — live **1,39** vs DEV **0,93** ⇒ **không phải hằng số, không phải sai đơn vị
  cố định** (không phải scale); do `volatility1H` live hơi CAO (tỉ lệ 1,25) mà `volatility24H` live hơi THẤP
  (0,82) ⇒ tỉ số bị **phóng đại ~1,5×**. Kiểu lệch: **lệch có cấu trúc theo tỉ số** (khác cửa sổ/lịch sử tính).
- **`volumeSpike` / `basketVolSpike` / `volumeRatioUpDown`** — lệch mức 50-73 % tương đối nhưng tương quan
  vẫn 0,53-0,94 ⇒ kiểu **lệch mẫu số** (avgVol / basket-membership), không phải feature chết.
- **`funding×3`** — **lệch thật nhưng tuyệt đối ~0,0017 %** ⇒ nhiều khả năng là **nguồn khác** (2 store /
  `fundingExtractor` nội bộ), KHÔNG phải sai công thức.
- **`momentum×3`** — **KHÔNG lệch** (đã bịt §2.1); trước đây bị liệt oan do DEV = 0.

### (3) FEATURE NÀO LÀ NGUYÊN NHÂN KHẢ DĨ NHẤT LÀM p15 CUT DƯỚI? — **KHÔNG CÓ**

Phân bố p15 bằng đúng model fold_20 (`Model_Regressor_Return15M.onnx`; sanity: `y_live` == cột `p15_out`
của dump, **maxAbsDiff 5,6e-7 pp, corr 1,000000**):

| | p15 (mean) | p15 (max) |
|---|---|---|
| LIVE 2026-09-28 (n=556) | **0,9426 %** | **1,2633 %** |
| DEV tái tạo **cùng phút** (30 feature export + momentum inline) | **0,9484 %** | **1,2994 %** |
| **chênh** | **+0,0058 pp** | +0,036 pp |

- **Đổi từng feature sang giá trị DEV (cùng phút):** tổng dịch chuyển p15 = **0,0058 pp**; đóng góp lớn nhất:
  `basketMomentum15M` **−0,0059 pp**, `basketRsi14` +0,0041, `percentAboveMA20` +0,0035, `basketVolSpike` +0,0023;
  `volatilityTermStructure` **< 0,0002 pp**. ⇒ **không feature nào dịch p15 đáng kể.**
- **Cơ chế:** p15 LIVE ≈ p15 DEV **trên cùng phút** ⇒ **pipeline p15 KHÔNG bị cut**. Chênh p15 "lớn" trước đây
  là **so p15(1 ngày) với p15(toàn cửa sổ DEV 2021-2026)**: p15 EXPORT 2026-07→09 n=129.137 ⇒ p50 **0,594 %** /
  p90 1,006 % / p99 **1,244 %** / max 3,570 %; mẫu gate15m (2021→2026-06) p99 1,346 % / max **54,854 %**.
  p15 LIVE (max 1,26 %) **≈ p99 của chính giai đoạn 2026-Q3** ⇒ **LIVE bình thường, chỉ là 1 ngày thị trường
  YÊN ẮNG**, không phải lỗi feature.
- ⇒ **`H_cut` (feature bị kẹp làm p15 kẹp dưới) KHÔNG được ủng hộ.** "Shadow đóng băng" (gate không pass) là
  hệ quả **thống kê của regime**: ngưỡng 2,947 % ở xa đuôi phải ⇒ tần suất ~0,07 %/dòng (PASS1) ⇒ ~0,4 dòng
  kỳ vọng/556 dòng ⇒ **quan sát 0 là BÌNH THƯỜNG**.

### (4) BƯỚC TIẾP + RỦI RO

1. **Dữ liệu:** hiện **563 dòng / 457 phút / 1 ngày** (đủ cho regime-match 1 ngày). Cần **≥ 2.000 dòng / ≥ 7
   ngày / ≥ 2-3 regime** để chốt "lệch do pipeline" vs "lệch do regime" — dump đang chạy tiếp (đã tự tăng từ
   469 → 563 dòng trong buổi). Pre-reg §4 ghi rõ ngưỡng cứng.
2. **Sửa được ngay?** **CÓ**, phần nguồn: (a) `momentum×3` → bật nhánh **inline** trong export (không đụng
   ONNX/LIVE, chỉ đổi *đường lấy dữ liệu để train/đối chiếu*); (b) `funding×3` → dùng **242 ns ticker** (đã đúng).
   Điều tra sâu `volatilityTermStructure`/`volume*` cần thêm ngày + instrument `nBasket/avgVol` cho live.
3. **Rủi ro khi sửa:** mọi thay đổi **đường LIVE / ONNX / `NUM_FEATURES` / `extractFeatures45`** ⇒ **PHẢI owner
   duyệt** (đụng hệ đang chạy). Sửa **chỉ phía export/audit** (inline md, chọn store funding) là **an toàn**,
   không ảnh hưởng shadow. **KHÔNG** hạ ngưỡng gate dựa trên số 2026 (2026 = holdout).

## 5. MỤC BỎ / KHÔNG LÀM (khai RÕ)

- **KHÔNG** chạy lại toàn bộ 89 ngày export với md inline (giữ box Oracle **NHẸ** — shadow đang chạy); chỉ tái
  tạo md cho ngày có dump (2026-09-28). Lệnh chạy lại đã nêu ở §2.1.
- **`d_dec`/`d_hour`** = **FALLBACK** ghép decile (không cặp) — nhiễu vì LIVE chỉ ở decile 2-4; **KHÔNG** dùng
  để kết luận cứng (chỉ để đối chiếu xu hướng).
- **Diễn giải `cdfDev`/`rankShfP` cho 4 feature lịch** bị loại khỏi kết luận (LIVE = 1 ngày ⇒ vô nghĩa).
- **KHÔNG** kết luận nhân quả về p15 từ `shift_sd` phân bố (chỉ số đó bị nhiễu regime) — chỉ dùng **P0 cùng phút**
  + **phân bố p15 theo feature**.
- **KHÔNG** dùng 2026 cho ngưỡng/tham số/thiết kế; **KHÔNG** deploy/hiệu chuẩn lại. **2026 holdout.**
- **KHÔNG** ghi/sửa/restart/kill trên Oracle/242; chỉ `get` Aerospike READ-ONLY + `scp` kéo dump + đọc file local.
- **KHÔNG** chạm ONNX/`NUM_FEATURES`/`extractFeatures45`/đường LIVE (chỉ **đọc** model để chẩn đoán).
- **KHÔNG** push file dữ liệu (chỉ code/doc + JSON nhỏ).
