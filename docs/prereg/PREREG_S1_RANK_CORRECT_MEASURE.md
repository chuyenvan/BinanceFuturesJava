# PRE-REG — S1 RANKING QUALITY (CORRECT MEASURE: đúng horizon + đúng mốc quyết định)

**Ngày viết (pre-reg TRƯỚC khi chạy):** 2026-09-17
**Trạng thái:** KHÓA — chạy ĐÚNG MỘT lần, KHÔNG sửa thiết kế sau khi thấy kết quả.
**Động cơ:** `docs/result/RESULT_S1_RANK_QUALITY.md` (commit `57223a0`) đo S1 với rank-IC ÂM cả 3
horizon (1h/4h/24h) và kết luận "S1 KHÔNG có năng lực xếp hạng forward-return". Nhưng lần đo
đó có **2 LỆCH CẤU TRÚC**: (i) S1 được train trên nhãn `g1lite` (**72h**), lại đo ở 1/4/24h;
(ii) đo ở **MỌI snapshot 1h**, không phải các **mốc hệ thống thực sự ra quyết định**. Lần này
đo lại ĐÚNG: đúng horizon (72h) + đúng mốc quyết định + **test đảo dấu** (yêu cầu của user).

**Câu hỏi:** tại đúng horizon 72h và đúng mốc quyết định, S1 (chiều hiện tại) có năng lực xếp
hạng forward-return không? Nếu đảo dấu (chọn score CAO nhất) thì có ra giá trị dương không?

---

## 0. ĐỊNH NGHĨA NHÃN `g1lite` (xác minh, không suy diễn)

Grep toàn repo cho `g1lite` → định nghĩa DUY NHẤT tại `research/pipeline/ledger.py:40`:

```python
D["g1lite"] = np.where(D.maxFav_72h >= 0.05,
                       D.maxFav_72h - np.minimum(0.5 * D.maxFav_72h, 0.08),
                       D.retEnd_72h)
```

- `maxFav_72h` = favorable excursion lớn nhất trong 72h; `retEnd_72h` = return cuối kỳ 72h.
- **`g1lite` = nhãn forward-return 72h có trailing-stop xấp xỉ**: nếu `maxFav_72h >= 5%` thì lấy
  `maxFav_72h - min(0.5*maxFav_72h, 0.08)` (khóa lời ~8% hoặc 50% đỉnh), ngược lại lấy
  `retEnd_72h`. Đây là nhãn **72h**, KHÔNG phải 1h/4h/24h.
- S1 (XGBRanker `rank:ndcg`) được train để xếp hạng theo **quintile của `g1lite − median_tick`
  (`rel5`, xem `docs/experiment/S1_PROVENANCE.md:96`)**.

⇒ **Horizon đúng = 72h.** Lần này đo forward-return 72h (proxy horizon-khớp từ close 1h; phần
trailing của `g1lite` là chi tiết phụ, ghi ở GIOI HẠN). Đo thêm **24h** để so sánh trực tiếp
với lần đo cũ (lần cũ có 24h = −0.0693).

## 1. QUY ƯỚC DẤU (khóa, không đọc nhầm dấu)

- S1 `score = -pred`, `pred = P(win)` ⇒ **score THẤP = tốt**. Hệ thống chọn top-K = K coin
  score THẤP nhất (`SELECTOR_RANK_TOPK = 8`).
- **Chiều hiện tại (xuôi):** `rank_ic = Spearman(-score, ret)`. `rank_ic > 0` = S1 làm đúng.
  (trùng `s1 = -score` trong `trend_rank_ic.add_s1`; top-8 xuôi = 8 `-score` cao nhất.)
- **Chiều đảo dấu (ngược):** `rank_ic_inv = Spearman(score, ret)` = `-rank_ic`. top-8 ngược =
  8 `score` CAO nhất (= 8 `-score` thấp nhất).

## 2. MỐC QUYẾT ĐỊNH THẬT (khóa nguồn TRƯỚC)

- **Nguồn:** `/home/ubuntu/simbundle/market.bin` (big-endian `[count:i4]` rồi `count ×
  [ts:long, down:f4, up:f4, down15m:f4]`; format xác nhận tại `WfoDataset.java:25` +
  `writeInt/writeLong/writeFloat` big-endian).
- **Mốc quyết định = các ts mà `MarketBigChangeDetector.getMarketStatus1M(...) != null`.**
  Code hiện tại chỉ còn một nhánh: `BIG_DOWN` khi `rateDownAvg < MS_DOWN_BIG_AVG`
  (`Configs.java:392`, `MS_DOWN_BIG_AVG = -0.03157f`). So sánh float32 exact.
- **Phạm vi DEV:** 2022-01-01 .. 2025-12-31 (2021 loại vì S1 bắt đầu 2021-12-31; 2026 seal).
- **Đếm trước (metadata, không phải kết quả):** 108 phút quyết định trong 2022-2025 →
  **59 bucket giờ duy nhất** (sau khi map xuống lưới close 1h). Ghi rõ trong RESULT.

### Map mốc 1-phút → lưới close 1h (khóa, causal)

- `ctime = ceil(t_dec / 1h) * 1h` = close_time của cây nến chứa `t_dec` (giá vào ≈ close cuối
  giờ đó). `ret_h(t) = close(ctime + h*1h) / close(ctime) - 1`.
- **S1 score forward-fill đến ĐÚNG `t_dec`** (không phải `ctime`) để tránh nhìn score phát
  hành sau mốc quyết định (lookahead ≤ 55 phút). Mỗi bucket giờ lấy `t_dec` SỚM NHẤT trong giờ
  đó để forward-fill S1.

## 3. DỮ LIỆU per-coin (xác minh, không suy diễn)

- `/home/ubuntu/java/fsrun/CLOSES_1H.bin` — big-endian `[ts>i8, sym>i2, c>f4]`, close 1h,
  2021-01-01 → 2026-01-01 (2026 loại, seal). `ctime = ts + 1h`.
- `/home/ubuntu/ledger/pred_s1a2x1.parquet` — `ts,sym,score` (float32), 6.573.909 dòng,
  620 symbol, 2021-12-31 → 2025-12-31, mỗi ~15 phút. forward-fill theo `ts <= t`.
- Map id→tên: `/home/ubuntu/selector_pred_out/symbol_map.csv`.

## 4. METRIC (khóa trước)

Tại mỗi bucket giờ quyết định, cross-section = các coin có S1 score (ff tới `t_dec`) **và**
forward-return hợp lệ. `min_n = 10` coin/bucket.

1. **(a) rank_ic xuôi** = `Spearman(-score, ret_h)` per-bucket → mean + **CI block-72h**.
2. **(b) rank_ic ngược (ĐẢO DẤU)** = `Spearman(score, ret_h)` per-bucket → mean + CI.
3. **(c) top-8 xuôi vs universe** = `mean(ret top-8 theo score THẤP) − mean(ret universe)`.
4. **(d) top-8 ngược vs universe** = `mean(ret top-8 theo score CAO) − mean(ret universe)`.
5. **(e) coverage** = số phút quyết định / số bucket giờ / số coin (median) / theo năm.

CI = block-72h bootstrap (2000 rep, seed `20260905`, percentile 2.5/97.5, inflate **x1.21**),
tái sử dụng `trend_rank_ic.block_ci` nguyên bản. Với mốc quyết định thưa (event-driven), các
block 72h hầu như chứa 0–1 mốc ⇒ bootstrap ≈ iid/cluster theo mốc (ghi rõ trong RESULT).

## 5. TIÊU CHÍ KẾT LUẬN + KỶ LUẬT (khóa trước)

- **S1 "đúng ở horizon của nó"** nếu `rank_ic(-score, ret_72h) > 0` VÀ CI(72h) không chứa 0.
- **Đảo dấu là ứng viên RIÊNG, chọn SAU khi đã nhìn kết quả DEV** ⇒ **post-hoc, multiplicity
  k=2** (2 hướng dấu × 1 lần đo). **KHÔNG được đề xuất áp dụng** chỉ vì dương trên DEV — chỉ
  được đề xuất nếu xác nhận ở **forward (2026 seal)**.
- Nếu đảo dấu dương ⇒ kết luận đúng: **"raw score mang thông tin nhưng NGƯỢC dấu so với luật
  chọn hiện tại"** — đây là phát hiện lớn, phải nói rõ.

## 6. GIOI HẠN (ghi sẵn, không biện hộ)

1. **Mốc rất ít**: 108 phút / 59 bucket giờ trong 2022-2025; CI block-72h ≈ iid (thưa).
2. **`g1lite` là trailing-stop 72h**, lần này đo proxy `ret_72h` thuần (close 1h) — không tái
   lập đầy đủ công thức trailing. (Trailing làm `g1lite` ≠ `retEnd_72h` thuần.)
3. `maxFav_72h`/`retEnd_72h` thật cần đường giá 1m/15m; lần này chỉ có close 1h ⇒ nếu cần đo
   đúng `g1lite` phải có label file riêng (ngoài phạm vi).
4. |IC| dự kiến nhỏ; "significance" do mẫu, không đồng nghĩa edge kinh tế sau phí/slippage.
5. S1 chỉ có 2022-2025; 2026 seal ⇒ KHÔNG có forward xác nhận trong lần đo này.
6. KHÔNG sửa `.java`, KHÔNG chạy sim T170, KHÔNG tune. DEV only.

## 7. Script

`research/analysis/s1_correct_measure.py` — tái sử dụng `trend_rank_ic.py`
(`load_closes`, `block_ci`, cấu trúc `_ic_series`), chỉ thêm: đọc `market.bin`, map mốc quyết
định, forward-return 24h/72h, top-8 xuôi/ngược. Dùng module `logging` (KHÔNG `print`). Ghi
JSON/CSV ra `research/analysis/out/`.
