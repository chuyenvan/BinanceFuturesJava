# PREREG_LIQ_PROXY — chỉ báo THANH LÝ gián tiếp (OI rơi + giá sập + taker bán) cho entry crash-buy

- Ngày chốt: 2026-10-23, **TRƯỚC** khi dựng proxy, trước khi đọc bất kỳ kết quả nào của kỳ kiểm.
- Repo: `~/claude_master/vz_e1_wt`, nhánh `research/vz-e1`. Kết quả: `docs/result/LIQ_PROXY.md` + `docs/result/liq_proxy/`.
- Phạm vi: nghiên cứu. KHÔNG đổi luật sim/live, KHÔNG chạy lại sim, KHÔNG chạm 242, KHÔNG gọi REST Binance, KHÔNG dùng 2020/2021H1.
- Nếu sửa bất kỳ định nghĩa nào sau commit này ⇒ phải viết ADDENDUM trước khi xem số bị ảnh hưởng.

## 1. Câu hỏi

Vision UM **không có** lịch sử liquidation (`forceOrder`). Dựng proxy từ dữ liệu sẵn có — metrics 5m (`sum_open_interest`, `sum_open_interest_value`) + kline 1m (`taker_buy_base/quote`, `quote_volume`) — để trả lời:

> Khi thanh lý dây chuyền **đã cạn** (OI đã xả xong, taker bán hạ nhiệt), entry crash-buy có tốt hơn / lọc được đợt sập tiếp không?

Đây là kiểm **giá trị thêm**, không phải kiểm lại OI đã có: S1 (`ls_global`, `rk_oi_delta24h`), net015 (5 feature OI) và gate 33 feature đã dùng OI/LS/taker. Proxy phải chứng minh **IC tăng thêm** sau khi trừ p15 và các feature OI hiện có.

## 2. Kỳ

| Kỳ | Cửa sổ (UTC) | Dùng để |
|---|---|---|
| Khám phá | 2022-01-01 → 2023-12-31 | đo, chọn dấu/ngưỡng mô tả |
| Kiểm | 2024-01-01 → 2025-12-31 | **không đọc** cho tới khi mã phân tích được đóng băng (hash ghi trong result) |
| HO 2026 | 2026-01-01 → 2026-09-30 | **chỉ mô tả sau cùng**, không dùng để chấm |

Không dùng 2020, không dùng 2021 (kể cả 2021H2). printDone `start` là **+07**; metrics/kline Vision là **UTC**. Mọi phép join đổi `start` sang UTC bằng `ts_utc = start_local − 7h`.

## 3. Dữ liệu & chống rò rỉ thời gian OI

Nguồn:
- metrics 5m: `/home/ubuntu/vz/out/metrics5m/<year>/<yyyy-mm>.parquet` (Vision UM, `ts` = `create_time` **nguyên xi**, UTC ms; cột `oi` = `sum_open_interest`, `oi_value` = `sum_open_interest_value`, `ls_cnt`, `toptrader_ls_cnt`, `toptrader_ls_sum`, `taker_ls_vol`).
- kline 1m: `/home/ubuntu/vz_e1/raw/kline1m-<yyyy-mm>.parquet` (Vision UM; `open_time` UTC ms; `taker_buy_quote`, `quote_volume`, `high`, `low`, `close`).
- printDone X14 8 seed: `/home/ubuntu/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv`.

**Quy ước `create_time`** (`docs/ops/OI_SCOPE_REPORT.md`, `docs/ops/OI_FIX_LOG.md`): trước 2024-03-04 (và một số ít symbol sau đó) `create_time` = **CUỐI** cửa sổ 5m; từ 2024-03-04 với đa số symbol = **ĐẦU** cửa sổ (snapshot ở `t+5m`). Không hardcode mốc; không dò quy ước per-(symbol,ngày) trong vòng này.

**Quy tắc an toàn chọn trước (không tune):** coi **mọi** bản ghi là quy ước NEW (xấu nhất), đặt `avail_ts = create_time + 5m`; khi đánh giá tại phút vào `t` chỉ dùng bản ghi có `avail_ts ≤ g`, với

```
g = floor((t − 10 phút) / 5 phút) × 5 phút
```

⇒ trễ **≥ 10 phút tính từ `create_time`**, tức **≥ 5 phút sau khi kỳ 5m kết thúc** theo cả hai quy ước. Giá/khối lượng 1m chỉ dùng nến đã đóng: open_time ≤ `g − 1`. Đây là **lag chọn: 10 phút** (không phải tham số để tune).

Hệ quả: proxy tại `t` không đổi nếu mọi dữ liệu sau `t` bị sửa (kiểm V1).

## 4. Proxy (cố định, không tune)

Ký hiệu tại phút vào `t` (UTC), `g` như trên:

- `px(c)` = close nến 1m open_time `c`; `r60 = px(g−1)/px(g−61) − 1`; `r15(c) = px(c−1)/px(c−16) − 1`.
- `oi(c)` = `sum_open_interest_value` (USD) của bản ghi có `avail_ts = c`; `oic(c)` = `sum_open_interest` (contracts).
- `tbq(u), qv(u)` = `taker_buy_quote`, `quote_volume` nến 1m open_time `u`.

Định nghĩa (dùng đúng các giá trị tại `g`, không nội suy, không fill):

1. **L1 — OI xả 60′ khi giá giảm**
   `L1 = −(oi(g)/oi(g−60) − 1)` nếu `r60 < 0`, ngược lại `L1 = 0`.
   Thiếu `oi(g)`, `oi(g−60)`, `px` ⇒ NaN (không thay 0).

2. **L2 — taker bán 15′ so median 7 ngày**
   `sell15 = 1 − Σ_{u=g−15}^{g−1} tbq(u) / Σ_{u=g−15}^{g−1} qv(u)`.
   `base7 = median{ sell_day(d) : d = 7 ngày UTC đã đóng trước ngày của g }`, `sell_day(d) = 1 − Σ_d tbq/Σ_d qv`.
   `L2 = sell15 − base7`.
   Yêu cầu `Σ qv > 0`; thiếu ⇒ NaN.

3. **L3 — gia tốc / "cạn"**
   `L1_15(c) = −(oi(c)/oi(c−15) − 1)` nếu `r15(c) < 0`, ngược lại 0.
   `L3 = L1_15(g) − L1_15(g−15)`.
   Âm = tốc độ xả OI 15′ gần nhất **chậm hơn** 15′ trước ⇒ thanh lý đang cạn.

4. **LM — chỉ số thị trường**
   Tại `g`, universe `U(g)` = các symbol có tổng `quote_volume` **ngày UTC trước** ≥ **20.000.000 USD**, có `oi_s(g)` hữu hạn.
   `LM = Σ_{s∈U} L1_s(g) × oi_s(g) / Σ_{s∈U} oi_s(g)`.
   (L1_s = 0 nếu giá 60′ của s không giảm — đúng định nghĩa L1.)

Không winsorize, không đổi dấu, không thêm biến thể. Bốn proxy là 4 phép thử; không có phép thử thứ 5.

## 5. Mẫu

Đơn vị mẫu chính = **cụm crash-buy**:
- leg = 1 dòng printDone; cụm = `(sym, giờ đóng end)`; anchor = leg có `start` nhỏ nhất; `entry` = entry của anchor.
- Chỉ cụm có anchor (UTC) trong kỳ; gộp 8 seed, khử trùng theo `(sym, anchor minute)`.
- `PnL cụm` = trung bình cộng PnL các seed khớp cùng `(sym, anchor)` (USD, đúng đơn vị printDone).

Mẫu phụ = **gate PASS legs** (theo định nghĩa "phút gate-mở" của `RESULT_GATE_ABLATION` §4: phút phân biệt có ≥1 entry `PREDICT_SYMBOL_TRADE`):
- tất cả leg trong X14 8 seed DEV, khử trùng theo `(sym, start, entry)`; PnL = trung bình các seed khớp.
- Mẫu phụ chỉ dùng để kiểm độ vững; tiêu chí chấm dùng **mẫu chính**.

## 6. Kết quả (outcome)

Với mỗi mẫu, từ kline 1m (UTC), tính từ phút `t`:

1. `arm168` ∈ {0,1}: `max(high[t, t+168h)) ≥ entry × 1.07` (arm rate 0,07 của profile X14). Nến `t` tính từ open_time `t`.
2. `PnL` (USD) như mục 5.
3. `MFE24 = max(high[t, t+24h))/entry − 1`; `MAE24 = min(low[t, t+24h))/entry − 1`.

Không dùng PnL@168h suy diễn, không dùng funding cho outcome.

## 7. Thước đo

- **IC** = Spearman(proxy tại `t`, outcome) trong kỳ (với `arm168` là tương quan hạng điểm-nhị phân).
- **IC tăng thêm** = partial Spearman của `(proxy, outcome)` sau khi trừ hạng của các control:
  `p15` (pred15m trong printDone), `oi_delta24h = oi(g)/oi(g−288) − 1`, `oi_z` (z-score expanding của `oic` từ 2021-12-01), `ls_global = ls_cnt(g)`, `ls_toptrader = toptrader_ls_cnt(g)`, `taker_buy15 = Σtbq/Σqv` trên `[g−15,g)`.
  Partial Spearman = Spearman của residual sau hồi quy OLS hạng-của-biến lên hạng-của-control.
- **CI 95%** = bootstrap theo **đợt sập**, 2.000 lần: đợt = khoảng flag X14 chứa ngày UTC của anchor (42 khoảng DEV, `~/claude_master/tsx/flags.json`); anchor ngoài flag ⇒ đợt = tháng UTC `YYYY-MM`. Resample đợt có hoàn lại, giữ toàn bộ cụm trong đợt.
- Báo cáo bảng: kỳ × proxy × outcome (IC, IC tăng thêm, CI, n, số đợt).

## 8. Tiêu chí "có cửa" (chốt trước)

Một proxy được coi là **có cửa** khi **tất cả**:
1. `|IC| ≥ 0,10` và **cùng dấu** ở khám phá và kiểm (với ít nhất một outcome trong {arm168, PnL}).
2. CI 95% bootstrap theo đợt của IC kỳ kiểm **không chứa 0**.
3. `|IC tăng thêm| ≥ 0,07` ở kỳ kiểm, cùng dấu IC.
4. Luật size thô (chốt trước, áp mechanical theo dấu IC kỳ khám phá) cho ước tính **≥ +5.000 USD/seed direct** ở kỳ kiểm:
   - Quintile 20% "thuận" = đuôi proxy cùng dấu IC khám phá; 20% "nghịch" = đuôi ngược.
   - `w = 1,5` nếu thuận, `0,5` nếu nghịch, `1,0` còn lại.
   - `Δdirect/seed = [Σ_mẫu (w−1) × PnL_cụm] / 8`.
   - Công thức này chỉ để ước lượng thô; không phải kết quả sim.

Không đạt ⇒ **đóng proxy**. Nếu thiếu dữ liệu (không đủ phủ, không có 2026) ⇒ ghi rõ cần mua gì (lịch sử `forceOrder` UM) để kiểm thật.

Nếu đạt ⇒ chỉ **ĐỀ XUẤT 1 luật** cho vòng sau (sim Java đầy đủ), không tự chấm, không tuyên bố GO.

## 9. Kiểm vệ sinh (phải PASS trước khi đọc IC)

- **V1 không look-ahead:** chọn 3 cụm; nhân 3× mọi `oi_value`, `oi`, `tbq`, `qv`, `high/low/close` có timestamp > `t`; proxy tại `t` phải **không đổi** (sai số 0).
- **V2 căn múi giờ:** in 3 cụm với `start` local +07, UTC sau đổi, và return 60′ tại hai cách hiểu; xác nhận dùng UTC. Kiểm thêm: nến 1m tại `t−1` phải tồn tại cho ≥ 99% cụm.
- **V3 phủ dữ liệu:** % cụm có đủ `oi(g), oi(g−60)`, `px`, `sell15`, và thuộc universe LM, theo năm.
- **V4 tái lập tay:** in đủ nguyên liệu thô và phép tính cho 3 cụm (1 mỗi kỳ + 1 mẫu phụ), so với pipeline.

## 10. Đầu ra

`docs/result/LIQ_PROXY.md` + `docs/result/liq_proxy/`:
- `build_proxies.py`, `score_liq_proxy.py` (hash trong result), `liq_proxy_samples.csv` (mẫu + proxy + outcome), `liq_proxy_ic.json`, `liq_proxy_v1v4.json`.
- Payload cuối: hash prereg/result, lag OI chọn, phủ dữ liệu, bảng IC & IC tăng thêm theo kỳ × proxy, verdict, đề xuất (nếu có) hoặc dữ liệu cần mua, bất thường.

## 11. Giới hạn đã biết

- Proxy từ OI 5m + taker 1m **không phải** liquidation thật; OI giảm có thể do đóng vị thế chủ động, không chỉ bị thanh lý.
- `create_time` không đồng nhất theo symbol; quy tắc lag 10′ là **bảo thủ**, làm proxy trễ hơn thực tế 5′ ở nhóm NEW.
- Cụm X14 là mẫu **có điều kiện** (gate đã PASS, selector đã chọn), không đại diện cho mọi phút thị trường.
- 8 seed không độc lập; bootstrap theo đợt (không theo seed) để tránh CI giả hẹp.
