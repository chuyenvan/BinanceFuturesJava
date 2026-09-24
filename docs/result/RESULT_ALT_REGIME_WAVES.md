# RESULT_ALT_REGIME_WAVES — đo hành vi ALT (MO TẢ, 0-sim)

Thực thi 2026-09-23, branch `module`, repo `/home/ubuntu/src/BinanceFuturesJava`.
Prereg: **`docs/prereg/PREREG_ALT_REGIME_WAVES.md`** (commit **`b0e91fa`**, commit TRƯỚC khi đo).
Script: `research/analysis/alt_regime_waves.py` (+ `altdata.py`, `jbin.py`, `extract_day.py`,
`aprobe.py`, `check_align.py`). Output: `research/analysis/out/alt_regime_waves.json`,
`alt_breadth30.csv`, `alt_windows.csv`, `alt_comove.csv`.
Không chạy Java/JVM, không sim, không sửa `.java`, không tune tham số nào, **không push**.

---

## 0. TÓM TẮT

**VERDICT: DUNG MOT PHAN** (A: 2/3 · B: 1/3).

| mục | nội dung | kết quả | đạt |
|---|---|---|---|
| A1 | median `ret_365d` của alt < 0 tại ≥3/5 mốc cuối năm | **3/4 mốc đo được** (2022 −84.5%, 2024 −20.7%, 2025 −80.9%; 2023 +72.4%) | ✅ |
| A2 | đuôi dày (excess kurt > 0 ở 1d/7d/30d) | **+370.9 / +1964.0 / +878.3** | ✅ |
| A3 | "7 ngày +30% rồi âm trong 30 ngày sau" > baseline, CI không chứa 0 | 61.60% vs baseline **60.42%** (diff +1.18pp, CI90 infl **[−4.11, +6.46]** → chứa 0) | ❌ |
| B1 | mỗi năm DEV có ≥1 cửa sổ tăng đồng loạt | **có** (2021:4, 2022:4, 2023:6, 2024:6, 2025:2) | ✅ |
| B2 | số cửa sổ/năm ∈ [1,3] ("~1 lần/năm") | trung bình **4.4/năm** (2→6) | ❌ |
| B3 | corr & beta trong cửa sổ CAO HƠN ngoài cửa sổ | corr30 **0.488 vs 0.620**, beta30 **1.02 vs 1.36** → **THẤP HƠN**, CI không chứa 0 | ❌ |

**Đọc gọn:** (i) đúng là alt **đi xuống dài hạn** sau các nhịp pump ngắn (A1, A2 ✅) — nhưng "pump rồi
dump" **không** tách được khỏi nền (A3 ❌: bản thân alt vốn đã âm 30 ngày 60.4% số quan sát trong DEV);
(ii) đúng là **mỗi năm đều có giai đoạn tất cả alt tăng đều** (B1 ✅), nhưng không phải "1 lần/năm" mà
**4.4 lần/năm** (B2 ❌), và **sai** ở chỗ coi cửa sổ đó là lúc "đồng pha với BTC" nhất — thực tế
tương quan/beta với BTC **thấp hơn** trong cửa sổ (B3 ❌). Hai ví dụ Uni nêu đều trúng cửa sổ
(2025-07-13→07-31; 2026-08-26→09-06).

---

## 1. Coverage & kiểm nguồn (đã đo)

| nguồn | khoảng THẬT SỰ có | quy mô |
|---|---|---|
| `CLOSES_1H.bin` (close 1h) | 2021-01-01T01:00Z → 2026-01-01T00:00Z | 10.322.386 bản ghi, **627 symId** |
| `kaggle_data_hpo/ticker_YYYYMMDD.bin.gz` (OHLCV 1m, Java-serialized) | **2021-01-01 → 2026-08-12** | 2050 file; 78 → 685 symbol |
| Aerospike `ticker.kline_1m_opt` (cụm 242) | key **tới 2026-09-23** | 685-730 symbol |

- **Đọc file `.bin.gz` bằng Python thuần**: viết parser Java-ObjectOutputStream
  (`research/analysis/jbin.py`) — giải được `TreeMap<Long minute, Map<String,KlineObjectSimple>>`,
  1440 phút/ngày, 0.5s (file 2021) → 4.6s (file 2026). **Không cần JVM.**
- **Key Aerospike = giờ local UTC+7** (kiểm chéo: key `20260813-0659` == phút UTC `2026-08-12T23:59Z`,
  giá BTC/ETH trùng khít file `ticker_20260812.bin.gz`). Chỉ đọc **~1 key/ngày** (phút 23:59 UTC),
  read-only ⇒ 41 key cho 2026-08-13…2026-09-22 (không đụng shadow).
- **Kiểm chéo 2 nguồn (24 ngày mẫu seed 20260923, 2021-2025)**: phát hiện `ts` trong `CLOSES_1H.bin`
  là **close time** (giá trị tại `ts` = giá đóng tại `ts`), không phải open_time: chọn `ts = (D+1) 00:00Z`
  ⇒ daily close(D) khớp **tuyệt đối** (median |rel diff| = 6.7e-11, 0% symbol lệch >1%) với phút 23:59
  của corpus ticker bins ⇒ **hai nguồn cùng gốc dữ liệu**. (Lưu ý: loader `trend_rank_ic.load_closes`
  hiểu `ts` là open_time ⇒ lệch 1h và còn mất luôn ngày 2025-12-31 do `ts < SEAL`.)
- **Không có dữ liệu 2026-09-23 sau ~03:23Z** (ngày đang chạy) ⇒ mọi metric dừng ở **2026-09-22**.
- Ma trận cuối: **2091 ngày × 876 symbol** (2021-01-01 → 2026-09-22).

## 2. Kết quả theo prereg

### 2.1 (1) Drift dài hạn — bảng tại các mốc cuối năm (alt = universe − 15 majors)

| mốc | h | n alt | median | mean | % alt dưới giá | BTC |
|---|---|---|---|---|---|---|
| 2021-12-31 | 90d | 108 | −19.3% | +10.5% | 73.1% | −3.0% |
| 2021-12-31 | 180d | 97 | **+18.3%** | +105.3% | 39.2% | +31.0% |
| 2022-12-31 | 90d | 127 | −37.4% | −33.3% | 91.3% | −13.2% |
| 2022-12-31 | 365d | 108 | **−84.5%** | −81.9% | **100.0%** | −64.2% |
| 2023-12-31 | 90d | 189 | +60.6% | +74.5% | 3.2% | +54.0% |
| 2023-12-31 | 365d | 130 | **+72.4%** | +120.4% | 11.5% | +155.9% |
| 2023-12-31 | 730d | 108 | **−71.5%** | −62.9% | 98.1% | −8.4% |
| 2024-12-31 | 90d | 279 | +25.7% | +35.0% | 18.3% | +54.3% |
| 2024-12-31 | 365d | 205 | **−20.7%** | +7.7% | 69.8% | +111.5% |
| 2024-12-31 | 730d | 118 | +59.0% | +102.5% | 17.8% | +463.2% |
| 2025-12-31 | 90d | 524 | −55.8% | −42.1% | 88.5% | −27.3% |
| 2025-12-31 | 365d | 333 | **−80.9%** | −67.2% | 94.0% | −6.4% |
| 2025-12-31 | 730d | 205 | **−80.5%** | −56.2% | 92.7% | **+98.1%** |

- **`h365` tại 2021-12-31 KHÔNG đo được** (dữ liệu bắt đầu 2021-01-01) ⇒ A1 chỉ có 4 mốc khả dụng
  (3 mốc âm, 1 dương).
- Trung vị âm sâu & phổ quát (2022: 100% alt dưới giá 12 tháng trước; 2025: 94%) ⇒ **"alt đi xuống
  dài hạn" là mô tả đúng cho 2 chu kỳ bear (2022, 2025)**, nhưng KHÔNG phải quy luật mọi năm
  (2023 +72%, 2024 dương 90d/180d). Mean > median ở hầu hết mốc ⇒ nhịp tăng ngắn nhưng cực mạnh
  bù lại.
- So với BTC: cùng cửa sổ 24 tháng 2024-2025, alt median **−80.5%** trong khi BTC **+98.1%**.

### 2.2 (2) Pump/dump ngắn hạn — phân bố return alt (pooled, DEV)

| horizon | n | median | mean | sd | skew | excess kurt | p01 | p05 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1d | 403.735 | 0.00% | +0.32% | 7.28% | **+7.67** | **+370.9** | −16.5% | −9.4% | +9.6% | +20.3% |
| 7d | 400.096 | −1.08% | −0.04% | 22.0% | **+24.4** | **+1964** | −36.6% | −23.9% | +26.5% | +59.4% |
| 30d | 386.601 | **−7.02%** | +0.00% | 52.9% | **+18.95** | **+878** | −58.8% | −43.3% | +63.4% | **+152.7%** |

- **Skew dương lớn + đuôi rất dày** ở mọi horizon; median 30d **âm** ⇒ hình dạng "pump mạnh nhưng
  thiểu số, phần còn lại trôi xuống".
- **Luật "7 ngày ≥ +30% rồi 30 ngày sau âm"**: n = **15.511** quan sát ⇒ **61.60%** có fwd 30d âm,
  so baseline toàn bộ alt **60.42%** ⇒ **+1.18pp**, CI90 inflated **[−4.11, +6.46]** ⇒ **chứa 0 ⇒ KHÔNG
  kết luận được**. Điểm quan trọng: nền đã 60.4% âm ⇒ "pump rồi dump" không phải dấu hiệu phân biệt.

### 2.3 (3)+(4) Breadth & cửa sổ tăng đồng loạt

`breadth30(D)` = % alt có close(D) > close(D−30). Cửa sổ = run ≥5 ngày có breadth30 ≥ 70.

| năm | số cửa sổ | ngày | % ngày trong năm thuộc cửa sổ | các cửa sổ |
|---|---|---|---|---|
| 2021 | **4** | 128 | 35.1% | 01-31→03-12 (b≈95.7), 03-26→04-17 (85.8), 08-04→09-09 (97.1), 10-20→11-15 (85.1) |
| 2022 | **4** | 52 | 14.3% | 03-23→04-10 (94.1), 04-12→04-16 (80.7), 07-16→07-22 (86.0), 07-28→08-17 (94.0) |
| 2023 | **6** | 132 | 36.2% | 01-13→02-24 (94.3), 04-07→04-12, 04-14→04-18, 07-10→07-20, 10-23→12-10 (89.3), 12-16→01-02/24 (85.1) |
| 2024 | **6** | 89 | 24.3% | 02-16→03-18 (92.0), 03-20→03-31, 09-25→10-01, 10-03→10-08, 11-08→11-12, 11-21→12-17 (91.0) |
| 2025 | **2** | 36 | 9.9% | 05-06→05-22 (85.6), 07-13→07-31 (81.7) |
| *2026 (post-DEV)* | *3* | *38* | *14.3%* | *01-13→01-18, 04-25→05-14 (79.1), 08-26→09-06 (73.8)* |

- **B1 ✅**: mọi năm DEV đều có ≥1 cửa sổ. **B2 ❌**: trung bình **4.4 cửa sổ/năm** (2→6), không phải ~1.
- Sensitivity (mô tả, không dùng kết luận): ngưỡng 65/75 (≥5 ngày) ⇒ 24/20 cửa sổ 2021-2025;
  bỏ yêu cầu ≥5 ngày (thr 70, ≥3 ngày) ⇒ 22 cửa sổ. Không đổi kết luận B1/B2.

### 2.4 (5) Đồng pha với BTC — TRONG vs NGOÀI cửa sổ (DEV, 437 ngày trong / 1359 ngày ngoài)

| metric | trong cửa sổ | ngoài cửa sổ | hiệu | CI90 inflated | chứa 0? |
|---|---|---|---|---|---|
| `corr30` (mean pairwise corr của daily return alt) | **0.488** | **0.620** | −0.133 | **[−0.160, −0.105]** | không |
| `beta30` (mean beta của alt với BTC) | **1.02** | **1.36** | −0.34 | **[−0.427, −0.252]** | không |

⇒ **Ngược với kỳ vọng**: trong cửa sổ "tất cả alt tăng", alt **ít đồng pha với BTC và ít tương quan
với nhau hơn** so với phần còn lại. Diễn giải: các đợt bán tháo/điều chỉnh mới là lúc alt co-move
mạnh & beta cao (mọi thứ rơi cùng nhau); còn "sóng tăng đồng loạt" là giai đoạn **luân chuyển
idiosyncratic** (rải vốn), tương quan thấp hơn. Nói cách khác "cùng tăng" ≠ "cùng pha".

### 2.5 (6) Kiểm 2 ví dụ cụ thể

| kỳ | mean breadth30 | đỉnh | số ngày ≥70 | cửa sổ chồng lấn | BTC kỳ đó | median alt kỳ đó |
|---|---|---|---|---|---|---|
| 2025-07-01→08-31 | 50.7 | 89.2 | 24/62 | **2025-07-13→07-31** | +2.4% | +9.6% |
| 2026-08-01→09-22 | 56.7 | 78.4 | 16/53 | **2026-08-26→09-06** | **+37.2%** | **+30.6%** |
| 2026-09-01→09-22 | 66.6 | 74.4 | 8/22 | 2026-08-26→09-06 | +11.3% | +16.8% |

- Cả hai kỳ Uni nêu **đều trúng cửa sổ**: 2025-07 (không phải tháng 8: breadth30 tháng 8/2025 tụt
  còn 43.6, tháng 9 còn 32.3); 2026-08-26→09-06 (tháng 9/2026 breadth30 TB **66.6%** — cao nhất năm 2026).
- **Trạng thái "hiện tại" (đến 2026-09-22)**: BTC +37.2% kể từ 2026-08-01, alt median +30.6%, breadth30
  đang ở vùng cao nhất năm ⇒ mô tả "một giai đoạn tất cả alt tăng theo sóng BTC" **đang đúng** cho
  tháng 8-9/2026. (Lưu ý: BTC 2026-08-12 = 63.46k → 2026-09-22 = 86.38k; đây là *forward observation*,
  KHÔNG dùng để suy luận/threshold.)

### 2.6 (7) Liên hệ T170 (mô tả, KHÔNG dùng để chọn)

Book `devrun/X1_GS_T170_2021/storage/printDone.csv` (n=**1089** lệnh, 2021-07→2025-12):
PnL các tháng có chồng cửa sổ = **+36.612** (18 tháng) vs các tháng còn lại = **+39.458** ⇒ PnL
**KHÔNG tập trung** vào cửa sổ (≈48% PnL ở ~34% số tháng; chênh nhẹ, không kết luận). Book shadow
`fsrun/storage/printDone.csv` (n=3215, 2021-01→2026-08-13) không dùng cho verdict.

---

## 3. Verdict & diễn giải

**DUNG MOT PHAN.** Insight đúng ở:
- **"alt đi xuống dài hạn"**: median 365d âm sâu ở 3/4 mốc đo được (−84.5% / −20.7% / −80.9%;
  2022 có 100% alt dưới giá 12 tháng trước), và 24 tháng 2024-2025 alt −80.5% trong khi BTC +98.1%;
  phân bố return lệch phải cực mạnh + đuôi dày (kurt 371-1964).
- **"mỗi năm có giai đoạn tất cả alt tăng đều theo sóng"**: đúng — 2021:4, 2022:4, 2023:6, 2024:6,
  2025:2 cửa sổ (breadth30 ≥70 kéo ≥5 ngày), chiếm 10-36% số ngày mỗi năm.

Insight sai / không được ủng hộ ở:
- **"~1 lần/năm"**: thực tế **4.4 cửa sổ/năm** (thr 70 ≥5 ngày); kể cả nới/thắt (65/75, ≥3 ngày)
  vẫn 20-24 cửa sổ cho 5 năm.
- **"theo sóng BTC"** (ngụ ý cửa sổ = lúc đồng pha BTC nhất): **sai hướng** — corr30 trong cửa sổ
  0.488 < 0.620 ngoài; beta30 1.02 < 1.36 ngoài; cả hai hiệu đều CI90 không chứa 0. Co-movement cao
  nhất xảy ra ở các pha bán tháo, không phải pha tăng đồng loạt.
- **"pump/dump ngắn hạn rồi đi xuống"** như một *quy luật dự báo được*: **không có bằng chứng** —
  xác suất âm 30 ngày sau một tuần +30% (61.60%) ≈ nền (60.42%), CI chứa 0. Cái đúng chỉ là
  *hình dạng phân bố* (thiểu số pump cực mạnh + đa số trôi xuống), không phải điều kiện "pump ⇒ dump".

## 4. Hạn chế / điều KHÔNG đo được (không suy diễn)

- `h365` tại 2021-12-31 không đo được (thiếu giá trước 2021-01-01); A1 chỉ dựa trên 4/5 mốc.
- Ngày **2026-09-23** (và các ngày sau) chưa có dữ liệu tại thời điểm chạy ⇒ "hiện tại" = tới 2026-09-22.
- Universe khác nhau theo thời gian (2021: ~110 alt sống → 2025: ~580) và có **thành kiến sống sót nhẹ**
  ở phần ticker corpus so với listing Vision (không backfill coin đã delist).
- `corr30`/`beta30` là ước lượng available-case trên cửa sổ 30 ngày (min 25 ngày chung, ≥15 alt):
  so sánh in/out mang tính mô tả, không phải mô hình nhân quả.
- Kết quả 2026 là **post-DEV/forward observation**, không tham gia verdict và không được dùng để tune.

## 5. Artifacts

- Prereg: `docs/prereg/PREREG_ALT_REGIME_WAVES.md` — commit **`b0e91fa`**.
- Result này + scripts: commit cùng branch `module`, message bắt đầu
  `result(alt-regime-waves):` (hash sẽ tự đổi nếu amend — kiểm bằng `git log --oneline -1`).
- Dữ liệu trung gian (ngoài repo, resume được): `/home/ubuntu/altregime/`
  (`daily/*.csv` 265 ngày, `daily_val/*.csv` 24 ngày kiểm chéo, `align_check.csv`).
- Output trong repo: `research/analysis/out/alt_regime_waves.json` (đã commit). Các CSV
  (`alt_breadth30.csv`, `alt_windows.csv`, `alt_comove.csv`, `align_check.csv`) **bị `.gitignore` chặn
  (`*.csv`)** — có trên đĩa, cùng thư mục, tái sinh bằng script; giữ nguyên quy ước repo.
- Kiểm chéo nguồn (24 ngày): `align_check.csv` — median |rel diff| = 6.7e-11, 0% symbol lệch >1%.
