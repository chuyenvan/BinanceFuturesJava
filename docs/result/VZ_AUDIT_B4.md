# VZ_AUDIT_B4 — rà soát B4 NO-GO (A→B→C→D)

MASTER 2026-10-15. Rà soát theo `docs/plan/VZ_AUDIT_B4_NEXT.md` — **commit `65a540f6`** (2026-10-15 15:22:05 +07),
branch `research/vz-e1`, worktree `~/claude_master/vz_e1_wt`. Luật §0: chỉ được lật Q6 nếu tìm ra **LỖI THỰC THI / LỖI DỮ LIỆU**;
cấm đổi chân trời / biên quintile / định nghĩa sự kiện-feature / bỏ năm / tách regime; mọi kiểm ghi ở đây + commit.

**Code/artefact audit (chỉ THÊM, không đổi logic đánh giá):**
- `research/vz/e1/e1_confirm.py` + cờ `--audit-2024` (guard: chỉ năm khám phá 2024 đi qua đường confirmation; log rõ
  "AUDIT, KHÔNG phải xác nhận"; output tách `e1_confirm_B4_AUDIT.json`; từ chối trộn 2024 với 2022/2023/2025).
- `research/vz/e1/e1_audit_b4_data.py` (B1/B2-unit/B3), `e1_audit_b4_events.py` (B2-outcome/B4/B5/C1–C3),
  `e1_audit_b4_repro.py` (A1/A2 engine vs khám phá), `e1_audit_b4_a2.py`, `e1_audit_b4_defs.py` (C4/D1).
- JSON: `~/vz_e1/reports/audit_b4_data.json`, `audit_b4_events.json`, `audit_b4_repro.json`, `audit_b4_a2.json`,
  `audit_b4_defs.json`, `e1_confirm_B4_AUDIT.json`.

## 0. Bảng tổng hợp

| mục | nội dung | PASS/FAIL | số chính |
|---|---|---|---|
| **A1** | tái lập B4-2024 của T9 bằng runner xác nhận (`--years 2024 --audit-2024`) | **FAIL theo ngưỡng 1e-9** (n, mono PASS) | n **65 886** = 65 886 ✓ · mono **−1,00** ✓ · spread **−0,013057010** vs **−0,013059224** (T9) ⇒ Δ **+2,214e-6**; nếu dùng đúng convention tháng 1 của khám phá ⇒ Δ **0** |
| **A2** | diff logic `tss_reversal` / cụm 30′ / `net_1440` (khám phá vs xác nhận) | PASS (đã liệt kê hết) | event set **66 058 = 66 058**; bucket mismatch **0**; max\|Δ\| `net_240`/`net_1440`/stress = **0,0**; `tss_reversal` lệch đúng **6 dòng** (2024-01-01) |
| **B1** | phân phối `taker_buy_quote/quote_volume` theo tháng 2021-12→2025-12 | PASS | median **0,4855–0,5016** suốt 49 tháng (không nhảy bậc); fz 0,19–4,86 %, fe 0,17–5,04 % — bám theo tỉ lệ phút qv=0 (0,75 %→12,7 %) |
| **B2** | đơn vị thời gian + khớp outcome (1000 sự kiện/năm) | PASS | ts **ms 100 %** từ 2021-12→2025-12 (KHÔNG đổi sang µs); so 3 978 sự kiện/năm: max\|Δ gross_1440\| = **0,0**, n_mismatch giá trị = **0** |
| **B3** | thứ tự cột kline theo năm | PASS | mọi tháng 12 cột; cột 10 (1-idx) = `taker_buy_base`, cột 11 = `taker_buy_quote` (`taker_buy_quote_idx`=10 0-idx) |
| **B4** | số sự kiện 2022/2023/2024/2025 | PASS | **38 049 · 36 626 · 65 886 · 153 973** (đúng) — 2025 = **4,19×** 2023 do universe ×2,44 và sự kiện/symbol ×1,71 |
| **B5** | anomalies bị loại theo năm | PASS | 2021:0 · 2022:0 · **2023:1** · 2024:0 · 2025:0 (`LRCUSDT` 2023-09-19 15:23, tbq>qv) |
| **C1** | % sự kiện mỗi quintile/năm (biên 2024 áp lên) | PASS (ghi là giới hạn thiết kế) | q5: **24,0 % / 15,5 % / 20,0 % / 23,1 %**; q1: 18,2 / 23,0 / 20,0 / 20,9 |
| **C2** | tỉ lệ bỏ vì thiếu close+1440′ theo năm × quintile | PASS | toàn cục 0,26 %–0,70 %; lớn nhất 2023 q5 **1,11 %** (không dồn mạnh vào quintile cao) |
| **C3** | cụm sự kiện cùng phút (báo kèm, không quyết) | PASS | max 1 phút = 143/206/302/351 sự kiện; spread 1 sự kiện/phút = +0,0062 / +0,0049 / −0,0001 / +0,0080 |
| **C4** | bootstrap block 5 ngày UTC, NREP 2000, seed pre-reg | PASS | code = pre-reg (`5/2000/20261014`), 2 lần gọi cho kết quả bit-identical |
| **D1** | pre-reg `997f18f3` trước Q6 + YAML == markdown | PASS | pre-reg **2026-10-14 21:48:38** < Q6 **2026-10-15 14:23:56**; md5 Q6 tái tạo được |
| **D2** | ghi nhận thiên lệch chọn chân trời 24h | PASS (ghi nhận, không phải lỗi) | 24h mạnh nhất ở khám phá; CI đã nở theo k=38 ⇒ √(2 ln 38)=**2,697** |

## A. Tái lập

### A1 — runner xác nhận chạy trên 2024

`python3 e1_confirm.py --prereg docs/prereg/PREREG_VZ_B4.md --years 2024 --audit-2024 --fetch`
→ `~/vz_e1/reports/e1_confirm_B4_AUDIT.json`, **md5 `1c7881deb0418b5b8269c893ec1c8ee1`** (2 lần chạy độc lập cho cùng md5).

| chỉ tiêu | T9 (khám phá, 2026-10-14) | runner xác nhận (`prior_lookback=True`, đúng như Q6) | lệch | ngưỡng 1e-9 |
|---|---|---|---|---|
| n có đủ 24h | 65 886 | 65 886 | **0** | **PASS** |
| mono (Spearman) | −1,00 | −1,00 | **0** | **PASS** |
| spread `net_1440` | −0,013059224306063 | **−0,013057010321130** | **+2,214e-6** | **FAIL** |
| CI95 `net_1440` | [−0,022539466789624384, −0,003636535919742213] | [−0,022539466789624384, −0,003633867983734852] | cận dưới giống hệt | — |
| n_level_assigned | 66 015 | 66 020 | +5 | — |

Đối chứng: cùng engine, chỉ đổi **một tham số** cửa sổ lookback tháng 1 về đúng convention của khám phá:

| biến thể | spread `net_1440` | Δ vs T9 | n |
|---|---|---|---|
| khám phá dựng lại (`e1_events_2024.parquet` + `e1_t9_events_net1440.parquet`) | −0,013059224306063011 | **0** | 65 886 |
| engine `prior_lookback=False` | −0,013059224306063011 | **0** | 65 886 |
| engine `prior_lookback=True` (= đường Q6) | −0,013057010321130342 | **+2,214e-6** | 65 886 |

**Nguyên nhân (đo được, không suy đoán):** event set / `bucket` / `net_60` / `net_240` / `net_1440` / `net_stress_1440`
khớp **tuyệt đối** (max\|Δ\| = 0,0; n so 65 886; không lệch NaN). Chỉ `tss_reversal` khác, đúng **6 dòng**, tất cả ở
**2024-01-01 00:00–00:02**:
- 5 dòng `ts=1704067200000` (00:00): khám phá = **NaN** (tháng 1 được dựng **không** có tháng 12 năm trước),
  runner = có giá trị (0,081–0,272) ⇒ được gán quintile;
- 1 dòng `RADUSDT ts=1704067320000` (00:02): 0,20791 (khám phá) vs 0,14184 (runner), Δ=0,0661.

Cơ chế: `tss_5` là rolling 5′ của chuỗi `shift(1)` ⇒ chỉ ~3 phút đầu năm bị ảnh hưởng. Đường **khám phá**
(`e1_core.build`) dựng tháng 1 với `prev=None`; đường **xác nhận** (`build_year_events(prior_lookback=True)`, đúng
pre-reg *"feature dùng ≤30 ngày cuối năm trước"*) nạp thêm tháng 12 → 6 sự kiện đổi feature → 6 sự kiện đổi quintile
→ spread dịch 2,2e-6.

**Phân loại theo §0:** KHÔNG phải LỖI DỮ LIỆU (giá, sự kiện, bucket, outcome giống tới bit) và KHÔNG phải lỗi thực thi
làm mất hiệu lực Q6 (đường xác nhận áp đúng convention pre-reg cho cả 3 năm 2022/2023/2025; sai lệch chỉ nằm ở rìa năm
1/1). §0 **cấm đổi định nghĩa feature**, nên không tồn tại "bản sửa" hợp lệ để chạy lại Q6 — đổi lookback tháng 1
chính là đổi feature, và còn làm spread 2024 **nghiêng về phía B4 hơn** (−0,0130592 < −0,0130570), tức đúng loại thay
đổi bị cấm để "cứu B4". Ảnh hưởng lên chính Q6 bị chặn bằng số: số sự kiện trong 5 phút đầu 1/1 của **năm xác nhận** là
**2022: 0 · 2023: 0 · 2025: 3** (0,002 % của 153 973) ⇒ không thể lật bất kỳ điều kiện GO nào (biên nhỏ nhất trong Q6 là
2022 **+0,00107**, lớn hơn hiệu ứng rìa cỡ ≥10×).

⇒ **Kết luận A1 = FAIL theo ngưỡng 1e-9 (đã định vị nguyên nhân) nhưng KHÔNG phải lỗi thực thi / lỗi dữ liệu ⇒ KHÔNG chạy lại Q6.**
(Nếu MASTER đọc §0 theo nghĩa cứng ">1e-9 ⇒ buộc chạy lại 1 lần", thì lần chạy lại duy nhất tự-đồng-nhất sẽ là chạy với
convention tháng 1 đã đồng bộ — tức phải đổi định nghĩa feature (bị cấm) — và trên 2022/2023 exposure = 0 sự kiện nên
kết quả không thể khác. Đây là điểm cần MASTER quyết; audit không tự ý đổi định nghĩa.)

### A2 — liệt kê MỌI khác biệt logic (khám phá `e1_t9.py` ↔ xác nhận `e1_confirm.py`)

1. **Nguồn sự kiện**: T9 đọc `e1_events_2024.parquet` (do `e1_core.build` dựng, merge thêm basis1m + metrics5m + funding,
   ghi panel/DOI/volz/prem_z7); runner dựng lại **chỉ từ kline1m** qua `build_year_events`→`month_events_year`
   (các cột basis = NaN, B4 không dùng). Cùng `candidates` + cùng `compute_features`.
2. **Cửa sổ lookback feature**: `e1_core.build` = 7 ngày (`LOOKBACK_MS`) và **tháng 1 không có tháng trước**;
   `build_year_events` = 30 ngày và `prior_lookback=True` (tháng 1 nạp thêm 12 năm trước). → khác biệt duy nhất có tác
   dụng, đúng 6 dòng ở 2024-01-01 (mục A1).
3. **Cụm 30′**: cả hai dùng **cùng hàm `e1_core.candidates`** (active & quote_volume ≥ 50 000 & bar_ret float32 ≤ −1 %;
   gộp phút ứng viên cùng symbol cách < 30′, giữ phút đầu). Không khác. (`e1_t9` còn dựng một `cluster_map` thứ hai
   **chỉ cho mẫu (a) chân EXEC** — không liên quan B4/mẫu (b).)
4. **`net_1440`**: T9 tính **ngoài builder** bằng `e1_t9.frame_for` (`pq.read_table` thẳng trên parquet tháng, **không lọc
   anomalies.csv**), `asof_exact` đòi đúng phút `ts` và `ts+1440′`, close>0 hai đầu, rồi left-join `(sym,ts)`; runner tính
   **trong builder** qua `SymIndex` (**có** lọc anomalies.csv của dataset) với cùng điều kiện exact-minute (`_asof` =
   searchsorted−1 + so khớp). Cùng công thức `log(close(ts+1440)/close(ts))`.
5. **`bucket`**: T9 lấy cột `bucket` có sẵn trong `e1_events_2024.parquet`; runner tính lại `bucket_of(close,open)` trên
   cùng hàng — **cùng hàm float32**; `bucket_mismatch = 0`.
6. **Biên quintile**: T9 đọc `configs/t9_config.json` (B4: hi=5, lo=1); runner lấy `e1_t3.VAR_BY_NAME` (V2: 5/1) và
   `check_frozen` ép edges == `configs/t3_thresholds.json` == YAML pre-reg. Trị số edges **trùng khít**.
7. **Lọc mẫu trước khi đánh giá**: T9 giữ mọi sự kiện (net NaN để `day_level_boot` tự bỏ); runner lọc
   `np.isfinite(net_1440)` trước. Cùng tập hữu hạn ⇒ cùng kết quả.
8. **Thống kê**: cùng `e1_stats.day_level_boot` + `spread_ci` + `monotonicity`; thứ tự hàng cả hai đều sort `(ts, sym)`
   trước khi tra; bootstrap theo **ngày UTC** nên thứ tự trong ngày không ảnh hưởng. Runner **thêm** `se` và CI nở
   `mean + √(2 ln 38)·se` (không đổi giá trị spread/mono).
9. **Định tuyến**: `run()` cũ đẩy `--years 2024` vào nhánh smoke T3 (không dựng lại từ lake) — đây là lý do phải thêm
   `--audit-2024`; không phải khác biệt logic.

Kiểm số (A2): event set **66 058 = 66 058** (chỉ-in-khám-phá 0, chỉ-in-xác-nhận 0); `bucket_mismatch` **0**;
`net_240`, `net_stress_240`, `net_1440`, `net_stress_1440` max\|Δ\| = **0,0**, NaN mismatch **0**; `tss_reversal` max\|Δ\|
= 0,0661 trên đúng 6 dòng (5 NaN→giá trị + 1 đổi giá trị).

## B. Dữ liệu năm xác nhận

### B1 — `taker_buy_quote/quote_volume` theo tháng (49 tháng, 2021-12 → 2025-12)

| tháng | unit ts | taker_buy_quote (idx) | n_rows | n_syms | median | p1 | p99 | fz (tbq=0) | fe (tbq=qv) | qv=0 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021-12 | ms | 10 | 6,027,280 | 138 | 0.4855 | 0.0363 | 0.9467 | 0.0023 | 0.0008 | 0.0075 |
| 2022-01 | ms | 10 | 6,151,955 | 139 | 0.4874 | 0.0242 | 0.9630 | 0.0036 | 0.0019 | 0.0104 |
| 2022-02 | ms | 10 | 5,379,456 | 141 | 0.4914 | 0.0149 | 0.9746 | 0.0052 | 0.0031 | 0.0079 |
| 2022-03 | ms | 10 | 6,284,250 | 142 | 0.4873 | 0.0089 | 0.9842 | 0.0062 | 0.0045 | 0.0077 |
| 2022-04 | ms | 10 | 6,053,794 | 147 | 0.4868 | 0.0056 | 0.9897 | 0.0080 | 0.0069 | 0.0083 |
| 2022-05 | ms | 10 | 6,443,646 | 146 | 0.4955 | 0.0187 | 0.9764 | 0.0049 | 0.0044 | 0.0092 |
| 2022-06 | ms | 10 | 6,175,319 | 143 | 0.4958 | 0.0159 | 0.9807 | 0.0055 | 0.0050 | 0.0207 |
| 2022-07 | ms | 10 | 6,383,520 | 143 | 0.4953 | 0.0029 | 0.9970 | 0.0089 | 0.0090 | 0.0291 |
| 2022-08 | ms | 10 | 6,409,995 | 145 | 0.4928 | 0.0058 | 0.9954 | 0.0078 | 0.0083 | 0.0318 |
| 2022-09 | ms | 10 | 6,390,135 | 151 | 0.4959 | 0.0000 | 1.0000 | 0.0151 | 0.0166 | 0.0295 |
| 2022-10 | ms | 10 | 6,776,370 | 153 | 0.4956 | 0.0000 | 1.0000 | 0.0248 | 0.0252 | 0.0304 |
| 2022-11 | ms | 10 | 6,650,640 | 154 | 0.4957 | 0.0000 | 1.0000 | 0.0149 | 0.0146 | 0.0391 |
| 2022-12 | ms | 10 | 6,874,560 | 154 | 0.4949 | 0.0000 | 1.0000 | 0.0399 | 0.0371 | 0.0605 |
| 2023-01 | ms | 10 | 6,935,790 | 158 | 0.4952 | 0.0000 | 1.0000 | 0.0195 | 0.0184 | 0.0548 |
| 2023-02 | ms | 10 | 6,602,175 | 172 | 0.4916 | 0.0000 | 0.9984 | 0.0102 | 0.0095 | 0.0506 |
| 2023-03 | ms | 10 | 7,798,352 | 181 | 0.4950 | 0.0000 | 1.0000 | 0.0126 | 0.0104 | 0.0441 |
| 2023-04 | ms | 10 | 7,921,290 | 186 | 0.4929 | 0.0000 | 1.0000 | 0.0200 | 0.0187 | 0.0472 |
| 2023-05 | ms | 10 | 8,531,910 | 193 | 0.4953 | 0.0000 | 1.0000 | 0.0346 | 0.0305 | 0.0504 |
| 2023-06 | ms | 10 | 8,393,760 | 197 | 0.5004 | 0.0000 | 1.0000 | 0.0306 | 0.0296 | 0.0534 |
| 2023-07 | ms | 10 | 8,858,415 | 202 | 0.4948 | 0.0000 | 1.0000 | 0.0332 | 0.0296 | 0.0534 |
| 2023-08 | ms | 10 | 9,186,840 | 208 | 0.4952 | 0.0000 | 1.0000 | 0.0467 | 0.0418 | 0.0554 |
| 2023-09 | ms | 10 | 9,045,417 | 213 | 0.4949 | 0.0000 | 1.0000 | 0.0471 | 0.0428 | 0.0555 |
| 2023-10 | ms | 10 | 9,738,570 | 227 | 0.4969 | 0.0000 | 1.0000 | 0.0405 | 0.0396 | 0.0510 |
| 2023-11 | ms | 10 | 10,264,035 | 246 | 0.4939 | 0.0000 | 1.0000 | 0.0179 | 0.0186 | 0.0437 |
| 2023-12 | ms | 10 | 11,124,539 | 253 | 0.4918 | 0.0000 | 1.0000 | 0.0159 | 0.0160 | 0.0429 |
| 2024-01 | ms | 10 | 11,433,930 | 261 | 0.4939 | 0.0000 | 1.0000 | 0.0171 | 0.0179 | 0.0419 |
| 2024-02 | ms | 10 | 11,081,940 | 270 | 0.4951 | 0.0000 | 1.0000 | 0.0230 | 0.0263 | 0.0435 |
| 2024-03 | ms | 10 | 12,301,439 | 278 | 0.4956 | 0.0445 | 0.9649 | 0.0028 | 0.0036 | 0.0398 |
| 2024-04 | ms | 10 | 12,201,000 | 285 | 0.4982 | 0.0155 | 0.9898 | 0.0063 | 0.0072 | 0.0573 |
| 2024-05 | ms | 10 | 12,719,885 | 288 | 0.4981 | 0.0000 | 1.0000 | 0.0179 | 0.0187 | 0.0745 |
| 2024-06 | ms | 10 | 12,106,433 | 283 | 0.4984 | 0.0000 | 1.0000 | 0.0210 | 0.0212 | 0.0647 |
| 2024-07 | ms | 10 | 12,636,154 | 284 | 0.4973 | 0.0000 | 1.0000 | 0.0231 | 0.0228 | 0.0750 |
| 2024-08 | ms | 10 | 12,812,300 | 297 | 0.4971 | 0.0000 | 1.0000 | 0.0238 | 0.0231 | 0.0709 |
| 2024-09 | ms | 10 | 13,168,462 | 316 | 0.4968 | 0.0000 | 1.0000 | 0.0320 | 0.0325 | 0.0704 |
| 2024-10 | ms | 10 | 14,167,680 | 323 | 0.4956 | 0.0000 | 1.0000 | 0.0274 | 0.0287 | 0.0679 |
| 2024-11 | ms | 10 | 14,415,374 | 344 | 0.4948 | 0.0076 | 0.9936 | 0.0074 | 0.0077 | 0.0638 |
| 2024-12 | ms | 10 | 15,970,514 | 370 | 0.4954 | 0.0377 | 0.9634 | 0.0019 | 0.0022 | 0.0742 |
| 2025-01 | ms | 10 | 17,053,649 | 391 | 0.4991 | 0.0085 | 0.9950 | 0.0063 | 0.0078 | 0.0825 |
| 2025-02 | ms | 10 | 15,961,890 | 400 | 0.5001 | 0.0000 | 1.0000 | 0.0102 | 0.0120 | 0.0885 |
| 2025-03 | ms | 10 | 18,170,865 | 422 | 0.5005 | 0.0000 | 1.0000 | 0.0224 | 0.0251 | 0.0935 |
| 2025-04 | ms | 10 | 18,623,430 | 443 | 0.5016 | 0.0000 | 1.0000 | 0.0246 | 0.0287 | 0.1001 |
| 2025-05 | ms | 10 | 20,329,413 | 466 | 0.5003 | 0.0000 | 1.0000 | 0.0162 | 0.0177 | 0.0954 |
| 2025-06 | ms | 10 | 20,553,435 | 484 | 0.5010 | 0.0000 | 1.0000 | 0.0307 | 0.0324 | 0.0946 |
| 2025-07 | ms | 10 | 21,995,880 | 504 | 0.5001 | 0.0000 | 1.0000 | 0.0202 | 0.0239 | 0.0886 |
| 2025-08 | ms | 10 | 22,905,000 | 523 | 0.5011 | 0.0000 | 1.0000 | 0.0209 | 0.0237 | 0.0855 |
| 2025-09 | ms | 10 | 23,219,607 | 555 | 0.5000 | 0.0000 | 1.0000 | 0.0306 | 0.0345 | 0.0904 |
| 2025-10 | ms | 10 | 25,449,112 | 584 | 0.4990 | 0.0000 | 1.0000 | 0.0249 | 0.0266 | 0.0953 |
| 2025-11 | ms | 10 | 25,588,004 | 597 | 0.4996 | 0.0000 | 1.0000 | 0.0261 | 0.0257 | 0.1002 |
| 2025-12 | ms | 10 | 26,951,035 | 611 | 0.5014 | 0.0000 | 1.0000 | 0.0486 | 0.0504 | 0.1268 |

**Đọc bảng:** median **ổn định 0,4855–0,5016** suốt 5 năm (nhảy tháng-lớn-nhất chỉ **0,0087**, 2022-04→2022-05) ⇒
**không có nhảy bậc nguồn**. p1/p99 trôi về 0/1 đúng lúc `fz`/`fe` tăng — cả hai bám theo tỉ lệ phút `quote_volume=0`
(0,75 % → 12,68 %) tức tỉ lệ phút chết tăng theo số symbol niêm yết (138 → 611). Không có tháng nào lệch khỏi quy luật
này ⇒ **không phải đổi định dạng nguồn**.

### B2 — đơn vị thời gian + khớp outcome

- **ts**: **ms** ở **toàn bộ 49 tháng** 2021-12→2025-12 (`ts_min` ≈ 1,6e12–1,7e12, khớp mốc đầu tháng), **không tháng
  nào dùng µs**. Giả thuyết "µs đổi từ 2025+" **không đúng với lake này** (đã kiểm 12/12 tháng 2025).
- **Khớp outcome**: 1 000 sự kiện ngẫu nhiên/năm, đọc `close(ts)` và `close(ts+1440′)` **trực tiếp từ parquet** bằng
  reader độc lập (không dùng `e1_core`/`e1_data`/`SymIndex`) rồi so với `gross_1440` của runner:
  2022: 995 so / 2023: 992 / 2024: 995 / 2025: 996, **max\|Δ\| = 0,0 mọi năm**, **0 mismatch giá trị**.
  Các dòng còn lại là sự kiện **cuối tháng 12** mà `ts+1440′` rơi sang năm sau: runner trả **NaN** đúng luật pre-reg
  ("không đọc năm sau"), còn reader tay đọc được ⇒ chênh chỉ ở phía reader (2022: 5, 2023: 8, 2024: 5, 2025: 4 dòng).

### B3 — thứ tự cột kline

Cả 49 tháng: **12 cột**, không đổi thứ tự, có header tên cột:
`ts, sym, open, high, low, close, volume, quote_volume, n_trades, taker_buy_base, taker_buy_quote, active`.
Cột **10 (1-index)** = `taker_buy_base` (chính là "taker_buy_volume" theo base), cột **11** = `taker_buy_quote`
(`taker_buy_quote_idx` = 10 theo 0-index). **Không có cột tên `taker_buy_volume`** — trường base-volume nằm ở tên
`taker_buy_base`. Mọi năm giống nhau ⇒ PASS.

### B4 — số sự kiện theo năm và nguyên nhân 2025 = 4× 2023

| năm | n sự kiện | n đủ 24h | symbol/tháng (min–max, mean) | sự kiện/symbol (mean) | symbol có sự kiện | top-20 symbol share |
|---|---|---|---|---|---|---|
| 2022 | 38 189 | **38 049** | 139–154 (146,3) | 260,7 | 162 | 24,0 % |
| 2023 | 36 884 | **36 626** | 158–253 (205,5) | 181,7 | 246 | 17,8 % |
| 2024 | 66 058 | **65 886** | 261–370 (307,8) | 220,3 | 373 | 14,7 % |
| 2025 | 154 614 | **153 973** | 391–611 (501,0) | 310,3 | 585 | 12,8 % |

Bốn con số n đủ 24h **đúng** kỳ vọng của plan (38 049 · 36 626 · 65 886 · 153 973).
Phân rã 2025/2023 = **4,19×**: universe **×2,44** (205,5 → 501,0 symbol/tháng) × sự kiện/symbol **×1,71** (181,7 → 310,3).
Số phút-có-sự-kiện: 20 162 (2023) → 101 808 (2025). **Không có dấu hiệu "nhóm symbol rác"**: share của top-20 symbol
**giảm** (17,8 % → 12,8 %), số symbol có sự kiện tăng 246 → 585, tức sự kiện **trải rộng ra** theo universe chứ không dồn
vào vài symbol. ⇒ nguyên nhân = niêm yết nhiều hơn + tần suất sập −1 %/phút cao hơn trên các symbol nhỏ, không phải
một cụm dữ liệu giả.

### B5 — anomalies bị loại theo năm

| năm | dòng trong `anomalies.csv` | ghi chú |
|---|---|---|
| 2021 | 0 | dataset không có file |
| 2022 | 0 | dataset không có file |
| 2023 | **1** | `LRCUSDT, 1695139380000, taker_buy_quote_gt_quote_volume(source_quote_volume_glitch)` → **bị reader bỏ** |
| 2024 | 0 | dataset không có file |
| 2025 | 0 | dataset không có file |

## C. Định nghĩa / thống kê

### C1 — biên quintile 2024 áp lên từng năm (% sự kiện mỗi quintile)

| năm | q1 | q2 | q3 | q4 | q5 |
|---|---|---|---|---|---|
| 2022 | 18,19 % | 18,20 % | 18,74 % | 20,86 % | **24,01 %** |
| 2023 | 22,99 % | 23,17 % | 20,22 % | 18,15 % | **15,47 %** |
| 2024 | 20,00 % | 20,00 % | 20,00 % | 20,00 % | 20,00 % |
| 2025 | 20,94 % | 18,73 % | 18,06 % | 19,16 % | **23,11 %** |

Lệch khỏi 20 % là **vừa phải, có hướng** (2023 nghiêng thấp, 2022/2025 nghiêng cao) ⇒ **giới hạn thiết kế** của việc
đóng băng biên 2024 (đúng như plan dự liệu). **KHÔNG đổi biên.**

### C2 — tỉ lệ bỏ vì thiếu `close+1440′` theo năm × quintile

| năm | q1 | q2 | q3 | q4 | q5 | toàn cục | sự kiện không có feature |
|---|---|---|---|---|---|---|---|
| 2022 | 0,29 % | 0,37 % | 0,53 % | 0,25 % | 0,39 % | 0,37 % | 18 |
| 2023 | 0,81 % | 0,47 % | 0,54 % | 0,69 % | **1,11 %** | 0,70 % | 33 |
| 2024 | 0,20 % | 0,29 % | 0,26 % | 0,30 % | 0,25 % | 0,26 % | 38 |
| 2025 | 0,47 % | 0,45 % | 0,36 % | 0,35 % | 0,43 % | 0,41 % | 106 |

Không dồn mạnh vào quintile cao (chỉ 2023 hơi cao ở q5: 1,11 % vs 0,47 % ở q2) ⇒ **không có thiên lệch sống sót đáng kể**;
ghi lại làm giới hạn nhỏ (≤ ~0,7 %/năm).

### C3 — cụm sự kiện cùng phút (báo kèm, KHÔNG quyết)

| năm | số phút có sự kiện | max sự kiện/1 phút | số phút > 1 sự kiện | spread `net_1440` nếu chỉ lấy 1 sự kiện/phút | mono |
|---|---|---|---|---|---|
| 2022 | 16 768 | 143 | 2 800 | +0,00623 | +0,40 |
| 2023 | 20 162 | 206 | 2 166 | +0,00490 | +0,70 |
| 2024 | 38 091 | 302 | 5 122 | −0,00014 | 0,00 |
| 2025 | 101 808 | 351 | 19 400 | +0,00797 | +0,70 |

Sập toàn thị trường gây cụm rõ (tối đa 143–351 sự kiện trong **một** phút) nhưng chỉ chiếm thiểu số phút; lấy 1 sự kiện/phút
cho spread **dương** ở 2022/2023/2025 (2024 ≈ 0) — **chỉ báo kèm**, không dùng để quyết.

### C4 — bootstrap

`e1_common.BOOT_BLOCK_DAYS=5`, `BOOT_NREP=2000`, `SEED=20261014`; `e1_stats.day_level_boot` dùng đúng các mặc định này,
block = 5 **ngày UTC** liên tiếp, resample có hoàn lại. Pre-reg YAML: `{block_days: 5, nrep: 2000, seed: 20261014}` ⇒ **khớp**.
Hai lần gọi độc lập trên cùng input cho replicate **bit-identical** (CI tái lập được).

## D. Pre-reg

### D1 — pre-reg `997f18f3` trước Q6 + YAML == markdown

- `997f18f32405ea22eccfd1ba41e26113ff558569`, **2026-10-14 21:48:38 +07** (Addendum 1, fee-fix) — file `docs/prereg/PREREG_VZ_B4.md`
  **sạch**, working tree == commit (không sửa sau khi chạy).
- Q6 chạy **2026-10-15 14:23:56 +07** (`~/vz_e1/logs/q6_confirm.out`, dòng đầu) ⇒ pre-reg đứng **trước ~16h35m**.
- YAML (máy đọc) == markdown: variant `V2_tss_reversal_q5`; `measure.primary=net_1440`; `k_tests 38` & "√(2 ln 38) = 2,70";
  `years [2022,2023,2025]`; `cost.fee_2leg 0,000982` & "phí khứ hồi cộng một lần"; `bootstrap 5/2000/20261014`;
  edges == `configs/t3_thresholds.json`.
- Output Q6 `e1_confirm_B4.json` md5 `e9b6560cc292dc1bcb52425deccfc1ff` **tái tạo được từ chính JSON đã lưu** (report not edited after the run).

### D2 — ghi nhận (KHÔNG phải lỗi)

Chân trời **24h được CHỌN** vì mạnh nhất ở khám phá 2024 (B4_tssrev_h24 spread −1,31 % [−2,25; −0,36], mono −1,00 —
mạnh hơn 60′/240′) ⇒ **thiên lệch chọn (selection bias)**. Đã bù bằng cách nở CI theo số phép thử `k=38`:
`√(2 ln 38) = **2,697**`, tức ngưỡng xác nhận dùng `mean + 2,697·se`, không dùng CI95 thường. Ghi nhận, không tính là lỗi.

## KẾT LUẬN RÀ SOÁT

1. **KHÔNG có LỖI DỮ LIỆU**: giá/sự kiện/bucket/outcome khớp tới bit (A2), ts đơn vị ms nhất quán (B2), cột kline đúng (B3),
   không đổi định dạng nguồn theo tháng (B1), anomalies chỉ 1 dòng (B5).
2. **A1 lệch 2,214e-6 (> 1e-9) nhưng KHÔNG phải lỗi thực thi**: đã định vị đúng **6 sự kiện 2024-01-01 00:00–00:02** do cửa sổ
   lookback tháng 1 khác nhau giữa đường *khám phá* (`prev=None`) và đường *xác nhận* (đúng pre-reg "≤30 ngày cuối năm trước").
   Với convention tháng 1 đồng bộ, engine cho **Δ = 0 tuyệt đối**. Q6 (2022/2023/2025) có exposure rìa năm = **0 / 0 / 3** sự kiện
   ⇒ không thể lật điều kiện GO nào. §0 lại cấm đổi định nghĩa feature ⇒ không có bản sửa hợp lệ.
3. ⇒ **NO-GO GIỮ NGUYÊN**. **Q6 KHÔNG chạy lại** (không có lỗi thực thi/lỗi dữ liệu để sửa; "chạy lại" chỉ có nghĩa nếu đổi
   định nghĩa feature — điều §0 cấm, và còn nghiêng về phía B4).
4. Các mục B/C khác đều PASS và **không đụng** chân trời/biên/định nghĩa/năm.

## Tệp tham chiếu

- `~/vz_e1/reports/audit_b4_data.json` (B1/B2-unit/B3, 49 tháng)
- `~/vz_e1/reports/audit_b4_events.json` (B2-outcome/B4/B5/C1/C2/C3)
- `~/vz_e1/reports/audit_b4_repro.json` (A1/A2, 3 biến thể convention)
- `~/vz_e1/reports/audit_b4_a2.json`, `~/vz_e1/reports/audit_b4_defs.json` (C4/D1)
- `~/vz_e1/reports/e1_confirm_B4_AUDIT.json` md5 `1c7881deb0418b5b8269c893ec1c8ee1` (A1, có cờ `audit: true`)
- log: `~/vz_e1/logs/audit_b4_driver.out`, `audit_b4_events4.out`, `audit_b4_repro.out`, `q6_confirm.out`
