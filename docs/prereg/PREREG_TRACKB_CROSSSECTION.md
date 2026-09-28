# PREREG_TRACKB_CROSSSECTION — harness Python cho SLEEVE market-neutral cross-section

Ngày chốt: **2026-09-28** (19:25 GMT+7). **CHỐT TRƯỚC khi đo bất kỳ số kết quả nào.**
Sau khi đo **không sửa thiết kế**; mọi thứ không có trong file này là **post-hoc** và phải dán nhãn.

Ràng buộc thi hành: thuần **Python offline**; **0 train / 0 sim**; **không** chạy job nặng trên Oracle
(shadow đang chạy); **không** chạm production / `242` (chỉ đọc nếu cần) / ONNX / đường LIVE;
**không push file dữ liệu**; **DEV ≤ 2025-12-31** (không chạm 2026); file trung gian **nhỏ**, dọn ngay.
Code: `research/trackb/`. Kết quả: `docs/result/RESULT_TRACKB_STEP1.md` (+ JSON nhỏ).

---

## 0. ĐỘNG CƠ (số ĐÃ đo ở các vòng trước — nguồn chân lý)

| đo được | nguồn | cảnh báo |
|---|---|---|
| `vol` IC **−0,09** (rank-IC cross-section, dấu ổn định) | `RESULT_PRESCREEN_FEAT` / các vòng featsearch | dấu ổn định nhưng độ lớn nhỏ |
| **nhóm `ΔOI` cao nhất (Q9) là nhóm TỆ NHẤT** | `RESULT_OI_STUDY` | H2 cross-section **NULL** ở long-only; ở đây dùng **L/S** |
| **funding `D10−D1` = −0,25 %/24h** (CI72h×1,21 `[−0,3974 %, −0,1076 %]`) | `RESULT_FUNDING_FACTOR` | dấu chỉ đúng **54,9 %** số phút ⇒ yếu |
| **`spread S1 L/S` lowK−highK f72 = +0,83 %/72h, `t = 6,47`** | `RESEARCH_SHORT` §2.3 | ⚠️ **`t` nghi PHỒNG do cửa sổ chồng lấn** ⇒ **PHẢI tính lại bằng CI block** |

### 0.1 ⚠ CẢNH BÁO KỸ THUẬT BẮT BUỘC (đưa vào thiết kế)

Độ lớn tín hiệu đo được (`funding D10−D1 = −0,25 %/24h`) **NHỎ HƠN phí `0,76 %/vòng`**.
⇒ **TURNOVER là biến quyết định**, không phải độ mạnh tín hiệu.

Trong này:
1. Mọi bảng **BẮT BUỘC** báo **net sau phí theo TỪNG mức turnover / hysteresis** (không chỉ gross).
2. **NÊU RÕ NGƯỠNG**: cần giữ **≥ N ngày**, hoặc chỉ vào khi **dislocation ≥ ngưỡng**; nếu phí ăn hết
   ⇒ **nói rõ phí hoà vốn** và **turnover trần** để book còn dương.
3. **Hệ quả kiểm định**: nếu doanh thu gross/ngày < phí/ngày tại turnover thực ⇒ kết luận **NULL**,
   bất kể `t` của tín hiệu.

---

## 1. DỮ LIỆU (nguồn chốt trước; đã verify sự tồn tại)

| khối | nguồn | dạng | cửa sổ |
|---|---|---|---|
| **GIÁ** | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | `>i8 ts`, `>i2 symId`, `>f4 close`, 10 322 386 dòng, **627 sym**, `ts` step **đúng 1h**, `2021-01-01 01:00 → 2026-01-01 00:00 UTC` | dùng `< 2026-01-01` |
| **FUNDING** | Aerospike local `test.funding_data`, bin `f_data` = Snappy(JSON `{ts_ms: rate}`) | 627 sym, `2021-01-01 → 2026-07-07` | `< 2026-01-01` |
| **ΔOI** | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` (**sha256 `e3887f63…b305ec`**, 140 924 110 × 30 B) | cột 0 = `oi_delta24h`, cột 1 = `oi_z`; mốc 5 phút, CAUSAL | `< 2026-01-01` |
| **THANH KHOẢN** | Aerospike local `test.kline_1m_opt` (key `YYYYMMDD-HHMM`, bin `data` = protobuf Snappy `{sym: [o,h,l,c,usdt]}`) | lấy **1 ngày/mẫu** | `< 2026-01-01` |
| **S1** | `/home/ubuntu/ledger/pred_s1a2x1.parquet` (`ts`, `sym`, `score`) | 6 573 909 dòng | pool ≤ 2025 |

**Quy ước causality giá:** `close[t]` = giá đóng của nến có `open_time = t − 1h` (đã verify ở
`FS_RESULT` §0.1) ⇒ tín hiệu tại `t` **CHỈ** dùng `close[≤ t]`.

### 1.1 UNIVERSE (tiêu chí cụ thể)

- **Ứng viên**: 627 USDT-perp có trong `CLOSES_1H.bin`.
- **Điểm thanh khoản `dv_med`**: với **60 ngày mẫu** (ngày 15 mỗi tháng `YYYY-MM-15`, `2021-01…2025-12`;
  nếu thiếu thì lấy ngày gần nhất có dữ liệu trong tháng), tính **USD-quote volume 1 ngày** =
  `Σ_{1440 phút} totalUsdt` (từ `kline_1m_opt`), rồi lấy **trung vị theo các ngày mẫu**.
- **UNIVERSE TĨNH** = **top 200 symbol theo `dv_med`** (loại bỏ symbol có `< 12` ngày mẫu).
  ⇒ **CÓ chứa major** (BTC/ETH nằm sẵn trong top 200) — chốt: **giữ major**, không loại.
- **ĐIỀU KIỆN TẠI NGÀY `t`** (động): symbol ∈ top-200 **VÀ** có `close[t]`, `close[t−24h]` **VÀ** có
  **≥ 30 ngày** lịch sử giá **VÀ** có record OI tại `t` **VÀ** có record funding tại `t`.
- **Số coin tối thiểu**: `N_elig ≥ 50`; nếu không ⇒ **ngày đó không giao dịch** (bỏ, không nội suy).
- **Không lọc survivorship**: coin delist vẫn nằm trong mẫu tới ngày cuối còn giá.

---

## 2. NHỊP REBALANCE + HYSTERESIS (chốt trước)

- **Nhịp**: **hàng NGÀY**, tại **00:00 UTC**, dùng **chỉ** dữ liệu `≤ 00:00 UTC`.
- **Hold**: **24h** (từ `close[t]` tới `close[t+24h]`). Chuỗi PnL = **1 điểm/ngày**, **không chồng lấn**.
- **UNIVERSE dùng chung** cho **cả 4 tín hiệu** và **cả book ghép** (để ghép cặp được).
- **Decile**: `n_dec = max(1, round(0,10 · N_elig))` coin mỗi đầu.
- **Hysteresis (mặc định `band = 2` decile)**: với tín hiệu đã định chiều sao cho **THẤP = long**:
  - **VÀO long** ⟺ rank chuẩn hoá `u < 0,10` (decile thấp nhất); **Ở LẠI long** ⟺ `u < 0,30`.
  - **VÀO short** ⟺ `u > 0,90`; **Ở LẠI short** ⟺ `u > 0,70`.
  - Tập long/tại ngày `t` = `(long(t−1) ∩ {u<0,30}) ∪ {u<0,10}`; short đối xứng.
  - **Trọng số equal-weight trong từng chân**: chân long tổng gross **+0,5**, chân short tổng gross **−0,5**
    (book **dollar-neutral**, gross 1,0).
  - Độ nhạy bắt buộc: `band ∈ {1 (= không hysteresis), 2 (chính), 3}`.

---

## 3. BỐN TÍN HIỆU (định nghĩa chính xác — chốt trước)

Tất cả tính tại `t = 00:00 UTC`, chỉ dùng dữ liệu `≤ t`. **Đã định chiều sao cho THẤP ⇒ LONG, CAO ⇒ SHORT**
(đúng yêu cầu "*long nhóm THẤP / short nhóm CAO*"). Chia nhóm: **decile** của rank cross-section.

| # | tín hiệu | công thức | đơn vị | chiều | cơ chế kỳ vọng |
|---|---|---|---|---|---|
| **f1** | `funding` | `f_sum24` = `Σ` funding rate trong `(t−24h, t]` (3 mốc 8h) | **%/24h** (thập phân) | **cao = SHORT** | crowded-long trả phí ⇒ high-funding kém |
| **f2** | `ΔOI` | `oi_delta24h` (cột 0 OI bin) tại `t` | **tỷ lệ** (thập phân/24h) | **cao = SHORT** | Q9 ΔOI cao nhất là nhóm tệ nhất |
| **f3** | `vol` | `σ_168h` = std của log-return **1h** trên **168h** gần nhất | **thập phân/h** | **cao = SHORT** | vol IC **−0,09** |
| **f4** | `reversal` | `ret_168h` = `close[t]/close[t−168h] − 1` | **thập phân/7 ngày** | **cao = SHORT** | đảo chiều (loser long) |

*(ghi rõ: `reversal` = "momentum 7 ngày đảo dấu". Phía long = coin **giảm 7 ngày**.)*

**IC sanity (bắt buộc):** tại mỗi ngày, rank-IC Spearman(factor, `fwd_24h`); báo **IC trung bình**.
Kỳ vọng: `vol` IC ≈ **−0,09**; các tín hiệu khác ghi số thật (không ép).

---

## 4. BOOK GHÉP (4 tín hiệu)

- **BOOK_EW (chính)**: book = **trung bình cộng 4 book con** (mỗi book con = 1 tín hiệu, như §3).
  Mỗi book con tự có hysteresis riêng, tự tính phí trên turnover riêng; **book ghép = EW của 4 chuỗi
  net-return/ngày** (đúng tinh thần "**một sleeve có nhiều cược độc lập**").
- **BOOK_RANK (phụ)**: gộp 4 factor thành **điểm rank trung bình** `ū = mean(u_f1..u_f4)` rồi decile
  như §2 (một book duy nhất). Báo `Sharpe` để so, **không dùng làm chính**.
- Book con luôn báo riêng (gross/net/turnover/Rào).

---

## 5. PHÍ + TRƯỢT GIÁ (khai RÕ)

- **`fee_rt` (khứ hồi) = 0,76 %** trên **một vòng đổi 100 % book**. Khai báo thành phần:
  **taker 0,05 % × 2 chân = 0,10 %** + **trượt giá 0,33 % × 2 chân = 0,66 %** ⇒ `0,76 %`.
- **Turnover (one-way)** tại `t`: `TO_t = ½ · Σ_i |w_i(t) − w_i(t−1)|` (book gross = 1,0 ⇒ đổi toàn bộ = 1,0).
- **Phí/ngày** = `fee_rt × TO_t`. (Đổi 100 % book ⇒ 0,76 %.)
- **FUNDING tính vào net**: `P_fund(t) = − Σ_i w_i(t) · f_i(t)` với `f_i` = tổng funding rate của coin `i`
  trong 24h nắm giữ. **SHORT coin funding dương ⇒ THU** (đúng `RESULT_FUNDING_SIGN`).
- **`net = gross + funding − fee`**. `gross` = PnL giá thuần (đã dollar-neutral ⇒ beta≈0).
- **Độ nhạy phí (bắt buộc)**: `fee_rt ∈ {0,30 %, 0,50 %, 0,76 %, 1,00 %}` ⇒ báo **phí hoà vốn**
  (mức `fee_rt` mà `net/ngày = 0`).

---

## 6. TRẦN SQUEEZE (chốt trước)

1. **Trần exposure 1 coin**: `|w_i| ≤ 2 × |w_nominal|` với `w_nominal = 0,5/n_dec`. Sau khi cắt, **re-normalize**
   trong từng chân về gross 0,5 (nếu chân rỗng ⇒ chân đó gross 0).

   *(Loại trừ trần nhiễu: nếu `n_dec ≥ 5` thì `w_nominal ≤ 0,1`, trần `≤ 0,2` — thực tế không bao giờ chạm
   vì bằng nhau; giá trị thật của trần là khi `n_dec ≤ 3`.)*
2. **Trần lỗ 1 coin/ngày (stop 24h)**: `s_i = sgn_i · (close[t+24h]/close[t] − 1)`.
   Nếu `s_i < −0,10` ⇒ `s_i' = −0,105` (stop 10 % + **0,5 % trượt giá khi khớp stop**, khai rõ là lý tưởng hoá
   vì dùng close 1h). `sgn_i = +1` (long) / `−1` (short).
3. **Loại coin funding cực đoan**: **KHÔNG** áp trong cấu hình chính; **CHỈ** trong biến thể độ nhạy
   `nofundx`: loại khỏi universe ngày `t` mọi coin có `max|rate| ≥ 0,30 %` trong `(t−24h, t]`.

---

## 7. ĐỐI CHỨNG COIN NGẪU NHIÊN (bắt buộc)

- Cùng ngày rebalance, cùng universe, cùng **số coin mỗi chân** bằng **trung vị của book chính**, chọn **ngẫu nhiên**.
- **`n_rand = 200`** book ngẫu nhiên độc lập; mỗi book: cùng phí `0,76 %`, cùng trần squeeze (mục 6.1–6.2),
  **không** hysteresis (chọn lại ngẫu nhiên mỗi ngày). Seed `20260928`.
- Báo **mean / p5 / p95** của `net/ngày` và **chênh `book − control`**.
- **Điều kiện giá trị**: book thật phải **> p95 của control**. Không ⇒ tín hiệu **không có giá trị**.

---

## 8. CHỈ SỐ (chốt trước — dùng đúng định nghĩa repo)

Trên **vector leg-PnL** (mỗi leg = 1 (ngày × tín hiệu × coin) net-PnL, đơn vị %):

1. **`gross/ngày`**, **`net/ngày`**, **`turnover/ngày`** + **`turnover/tháng`** (×30).
2. **`Sharpe`** = `mean(net_daily)/std(net_daily) × √365`; **`maxDD`** trên chuỗi luỹ kế `net_daily`.
3. **Rào (a)**: `share_top1_pct = Σ(⌈0,01·n⌉ leg TỐT nhất)/Σpnl × 100`; **PASS ⟺ ≤ 15 %**.
4. **Rào (b′)**: `TF(25 %) = Σ` phần còn lại sau khi bỏ `⌈0,25·n⌉` leg tốt nhất; **PASS ⟺ > 0** (+ CI).
5. **`q*`** = bước **0,5 %** nhỏ nhất làm `TF(x) ≤ 0`.
6. **`asym`** = `mean|net|(net<0) / mean net(net>0)`.
7. **`winrate_ngày`** = tỉ lệ ngày `net_daily > 0`.
8. **`pnl_vol_norm`** = `mean_leg(net_leg / σ_sym)`; `σ_sym` = std `gross` của coin đó trên toàn mẫu.

---

## 9. CI + MDE (chốt trước)

- **Block bootstrap**, **NREP = 2000**, **seed `20260905`**, khối = **10 ngày** cho chuỗi daily
  (chuỗi daily không chồng lấn; khối 10 ngày để giữ cấu trúc regime tuần).
- **`inflate(k)`**: `k = 1 → 1,0`; `k ≥ 2 → √(2·ln k)` (chuẩn `AUDIT_CI_INFLATE_STANDARDIZATION`).
  Chốt **`k_main = 8`** (= **4 tín hiệu × 2 book con/gộp** kiểm định so với control) ⇒
  `inflate(8) = 2,0393`. Báo **thêm CI thô (`raw95`)**.
  **"Ngoài CI" ⟺ ngoài CẢ `raw95` VÀ `inflate(8)`.**
- **Null test**: block **sign-flip** 10 ngày, 2000 rep, seed `20260905` ⇒ `p(mean>0)`.
- **MDE(p80)** = **p80 của nửa-độ-rộng** trên **500 chuỗi null sign-flip** (cùng cấu trúc khối),
  báo kèm **`2,8 × SD(null)`**.
- **Câu (1) bắt buộc — `spread S1 L/S`**: tái lập đúng phép đo `RESEARCH_SHORT` §2.3
  (mỗi `decision-ts` nhịp 15′, long **top-8 điểm thấp** vs short **bot-8 điểm cao**, `f72` =
  `close[t+72h]/close[t] − 1`), rồi thay **`t` iid** bằng **CI block với khối = 288 tick (= 72h)**,
  NREP 2000, seed `20260905`. **Kết luận `t = 6,47` còn dùng được hay không.**

---

## 10. LUẬT KẾT LUẬN (chốt TRƯỚC — không đổi sau khi thấy số)

- **GO bước 2** ⟺ **(i)** `BOOK_EW` net/ngày **> 0** và **ngoài CẢ `raw95` + `inflate(8)`**; **VÀ**
  **(ii)** `BOOK_EW > p95(control ngẫu nhiên)`; **VÀ** **(iii)** Rào **(a) PASS** và **(b′) PASS**;
  **VÀ** **(iv)** `|net/ngày| > MDE80`. (Tất cả ở `fee_rt = 0,76 %`.)
- **NULL** ⟺ `BOOK_EW` net/ngày **≤ 0**, **hoặc** ≤ `p95(control)`, **hoặc** Rào FAIL.
- **THIẾU POWER** ⟺ dấu dương nhưng `|net/ngày| ≤ MDE80` ⇒ **nói rõ là thiếu power**, không tuyên bố edge
  (bài học 28/09).
- Báo **bắt buộc**: **turnover trần** để `net/ngày > 0` và **phí hoà vốn**; **số ngày giữ tối thiểu**
  (`≥ N ngày`) hoặc **ngưỡng dislocation** cần để book còn dương sau phí.

---

## 11. OUTPUT

`docs/prereg/PREREG_TRACKB_CROSSSECTION.md` + `research/trackb/*.py` +
`docs/result/RESULT_TRACKB_STEP1.md` (+ `docs/result/trackb_step1.json` **nhỏ**). Commit + **push**.
