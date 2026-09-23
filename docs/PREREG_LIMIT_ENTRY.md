# PREREG_LIMIT_ENTRY — (1) TRUY LẠI QUY ƯỚC DẤU FUNDING, (2) TEST LIMIT-ENTRY 15 PHÚT (fill-or-fail)

Chốt: 2026-09-23, **TRƯỚC khi chạy bất kỳ phép đo nào**. Commit file này phải có **TRƯỚC** commit kết quả.
Nếu thứ tự commit ngược → kết quả bị coi là **VOID**.

**Tuân thủ (không đổi sau khi thấy số):**
- **Thuần Python** (0-sim). **KHÔNG** Java trên Oracle (shadow đang chạy) · **KHÔNG** `claude-run`/Claude Code · **KHÔNG push**.
- **KHÔNG chạm HOLDOUT 2026**: mọi mốc dữ liệu `< 2026-01-01`. Nguồn 1m = `raw/*.f32` (627 symbol, `kline_1m_opt` đã extract),
  funding = Aerospike `test.funding_data` (**chỉ đọc**).
- Dữ liệu **DEV (CHÍNH)** = `2022-01-01 .. 2025-12-31`. **ALL** = `2021-01-01 .. 2025-12-31` (**phụ + dán nhãn**).
- Trung gian ghi **ngoài repo** (`/home/ubuntu/claudedata/limit_entry/`, `/home/ubuntu/claudedata/funding_sign/`) để **resume được**; dọn sau khi commit.
- Không tune tham số sau khi thấy số. Mọi thứ "lật" chỉ là **POST-HOC / ứng viên forward**, không phải quyết định áp dụng.

---

# PHẦN 1 — TRUY LẠI & CHỐT QUY ƯỚC DẤU FUNDING (đo lại 2 tầng, độc lập)

## 1.0 Vấn đề cần giải

`RESULT_COST_REAL_AUDIT.md` §2.3 báo: trên 673/1089 lệnh có ≥1 kỳ settle, **đa số lệnh TRẢ** funding
(459 lệnh = 68,2%; THU 214 = 31,8%), nhưng **mean = −0,2518 %/lệnh** (âm = *thu ròng*), median **+0,0109 %**.
Owner nhớ có lần đo ra hệ **"được NHẬN về"**. Hai cách phát biểu (đa số TRẢ vs net THU) **nhìn như mâu thuẫn**.
Phần này **đo lại bằng dữ liệu**, không sửa/hồi tố văn bản cũ, và chốt **một** quy ước dấu.

## 1.1 Quy ước dấu KHOÁ (Binance USDⓈ-M perp, vị thế LONG)

Chuẩn Binance (`/fapi/v1/fundingRate`, `fundingRate`): **`rate > 0` ⇒ LONG TRẢ, SHORT NHẬN**;
`rate < 0` ⇒ LONG NHẬN. Aerospike `funding_data` (key=symbol, bin `f_data` = Snappy(JSON `{fundingTime_ms: rate}`))
lưu **đúng giá trị `fundingRate`** (crawler `HistoricalFundingCrawlerLocal.java:75` không đổi dấu).
⇒ KHOÁ: **`rate>0` = long trả; `rate<0` = long nhận** (trùng `PREREG_LEVEL_SENSITIVITY.md:51`, `PREREG_REVERSAL_BOUNCE.md:81`).

Khoá luôn 2 đại lượng tách bạch (đơn vị **%/notional**, `notional = quantity × entry`):
- `f_pp := 100 × Σ_{T ∈ (t_in, t_out]} rate(T)`  → **quy ước CHI PHÍ**: `f_pp > 0` = **TRẢ**, `f_pp < 0` = **THU**.
- `pnl_fund_pp := −f_pp` → **quy ước PnL**: `> 0` = **được nhận**, `< 0` = **bị trừ**.

## 1.2 Hai tầng đo (BẮT BUỘC, ghi rõ quy ước từng tầng)

- **Tầng A — PHÂN BỐ FUNDING RATE (unconditional, toàn universe, theo thời gian)**: scan `funding_data`,
  mọi cặp `(symbol, T)` có `T < 2026-01-01`. Báo: `n`, **% rate>0**, % rate<0, % =0, **mean/median rate (bp)**,
  p01/p25/p75/p99, **theo từng năm**; và **cross-sectional**: mỗi mốc `T` lấy mean rate qua các symbol ⇒
  phân bố của mean đó + **% số mốc T có mean cross-sectional > 0**. (đây là "thời tiết" funding của thị trường)
- **Tầng B — PnL FUNDING CỦA LONG (conditional trên cửa sổ giữ lệnh thật)**: trên **1089 lệnh** canonical
  `X1_GS_T170_2021/storage/printDone.csv` (md5 `efb793e2468ca3a7318da0f0ad23d4fc`), cửa sổ `(t_entry, t_exit]`,
  tính `f_pp` theo §1.1; báo **% THU / % TRẢ / % =0**, **mean/median `f_pp`**, **mean `pnl_fund_pp`**,
  phân rã `mean = P(trả)·E[|f_pp| | trả] − P(thu)·E[|f_pp| | thu]`, và **mean/median per-settle**
  (`f_pp / n_settle`). Đối chiếu với cột `funding` **của sim** (suy từ `pnl`, quy ước y hệt: âm = thu) và với
  fund_rate tổng quát của **chính các symbol/window đó** (bản thể đối chứng: dùng cột `funding` sẵn có).

## 1.3 Truy vết văn bản cũ (bắt buộc nêu file + số + quy ước)

Lập bảng: mọi nơi trong `docs/` (kể cả `docs/archive/`, `docs/decisions/`) kết luận về **dấu** funding, ghi
**file · số · quy ước dấu của nó**. Trọng tâm: các vòng đã kết luận "được NHẬN về".

## 1.4 Luật kết luận Phần 1

- Nếu Tầng A (unconditional) và Tầng B (conditional) **cùng dấu** → mâu thuẫn chỉ là **cách phát biểu**, ghi rõ.
- Nếu **khác dấu** → phải chỉ ra **đâu là khác biệt có nguyên nhân** (chọn mẫu/thời kỳ/dài ngắn cửa sổ/đơn vị/`n`),
  và **con số ĐÚNG** là con số nào, kèm **giới hạn**. Không tự mô hoá, không viết lại lịch sử.

---

# PHẦN 2 — TEST LIMIT-ENTRY (mô hình 15 phút, fill-or-fail)

## 2.0 Câu hỏi + tiên lượng ghi trước

Hỏi: với ứng viên **gross > 0 nhưng net ≤ 0** (bị phí ăn hết), cơ chế **entry LIMIT** (maker) có "lật" được
net thành **> 0** với CI ngoài 0 không? **Tiên lượng ghi trước: KHÔNG lật được một cách bền vững.** Lý do:
(a) phần tiết kiệm được chỉ là **fee 0,10% → 0,07%** (−0,03pp) — **nhỏ hơn MDE** của các ứng viên này;
(b) **adverse selection là thật và cùng dấu với bất lợi**: lệnh khớp là lệnh giá **đã đi ngược** (phải hạ
đủ δ mới khớp) ⇒ tập khớp **xấu hơn** tập fail; (c) mọi kết quả dương (nếu có) là **POST-HOC** (đổi thước đo).

## 2.1 Chọn ứng viên — KHOÁ TRƯỚC, k ≤ 2

Tiêu chí chọn (áp trước khi đo, `docs/RESULT_*` cũ là nguồn duy nhất): **raw/gross dương, net ≤ 0 (hoặc ≈0 trong
độ phân giải)**, từ vòng đã đo. KHOÁ:
- **C1 = REVERSAL-BOUNCE** (`docs/RESULT_REVERSAL_BOUNCE.md`; trigger khoá nguyên bản `PREREG_REVERSAL_BOUNCE.md`,
  commit `a68dc88`): DEV net −0,080% vs raw +0,22% (ALL +0,31%) ⇒ **đúng tiêu chí**. **Ứng viên CHÍNH.**
- **C2 = BIG_UP** (`docs/RESULT_BIGUP_MEDIUPDOWN.md`; trigger khoá nguyên bản `PREREG_BIGUP_MEDIUPDOWN.md`,
  commit `5102899`): DEV net **+0,87%** ⇒ **KHÔNG đạt tiêu chí "net ≤ 0"**; chỉ vào vòng này như **đối chứng
  phụ có dán nhãn** (net nằm trong CI chứa 0 ở DEV). **Chỉ chạy C2 nếu ngân sách thời gian cho phép**; nếu
  không chạy, ghi rõ lý do trong RESULT (không thay bằng ứng viên khác, không hạ tiêu chí).
- **KHÔNG** thêm ứng viên thứ 3, không đổi trigger/ngưỡng/HOLD của cả 2.

Tham số khoá của C1 (nguyên bản): `DROP_THRESH=0.01`, mốc 15m-aligned `epoch_min%15==14`, `max15/max30` cửa sổ,
`priceReverse=open[j−14]`, fire tại nến đầu `t>j` có `close[t]>priceReverse`, **HOLD 24h (1440 phút)**, exit =
nến có mặt cuối cùng trong `(fire, fire+1440]` (nến bị cắt biên `fire+1440 > span−1` ⇒ loại).
Tham số khoá của C2 (nguyên bản): `rateUpAvg>0.025`, chọn **2 symbol rớt 15M sâu nhất**, HOLD 24h.

## 2.2 Mô hình entry LIMIT (KHOÁ, causal)

Tại tín hiệu ở nến `f` (nến **đã đóng**) với giá `p0 = close[f]`:
1. Đặt **limit BUY** tại `L = p0` (**δ = 0**) — biến thể khoá thứ hai: `L = p0 × (1 − δ)`, **δ = 0,15%**.
2. **Cửa sổ khớp = 15 nến kế tiếp** `f+1 .. f+15` (nến 1m đã đóng, causal). Nếu `min(low[f+1..f+15]) ≤ L`
   ⇒ **KHỚP** tại nến khớp **đầu tiên** `m` (min `m` với `low[f+m] ≤ L`), **giá khớp = L**, phí = **MAKER**.
   Nếu không chạm ⇒ **FAIL ⇒ BỎ LỆNH** (không vào, không có lệnh).
3. **KHÔNG** mô hình hoá "tỉ lệ khớp khi thoát": exit là **MARKET** nên **luôn khớp** (giả định thận trọng
   chuẩn của repo) và **chịu đầy đủ** phí taker + số hạng slip (xem §2.3).
4. Đồng hồ giữ lệnh (KHOÁ): exit **giữ nguyên mốc của baseline** `E = nến có mặt cuối cùng trong (f, f+1440]`
   ⇒ với variant limit, thời gian giữ = `1440 − m` phút. (Biến thể phụ: exit tại `f+m+1440` — báo riêng.)

**Chống look-ahead:** chỉ dùng `low/high/close` của nến **đã đóng**; khớp limit xét nến `> f`; không dùng
thông tin giá của chính nến tín hiệu sau khi đã biết.

## 2.3 Mô hình chi phí (KHOÁ) — 4 hàng, có 1 hàng GATE tái tạo

| # | Tên | fee | slip | funding | tập mẫu |
|---|---|---|---|---|---|
| **A0** | **BASELINE-REPRO** (bản đăng `RESULT_REVERSAL_BOUNCE`) | taker 0,10% (2 chân) | `0,5·(H−L)/C` tại **nến tín hiệu** | Σrate `(f, E]` | tất cả fire |
| **A1** | market/market đối xứng | taker 0,10% | **entry** `0,5(H−L)/C`@f **+ exit** `0,5(H−L)/C`@E | Σrate `(f, E]` | tất cả fire **và** tập-khớp |
| **B** | **LIMIT entry + MARKET exit** | **maker 0,02%** + taker 0,05% | entry **0** (khớp tại L) + exit `0,5(H−L)/C`@E | Σrate `(fill, E]` | tập-khớp |
| **C** | như B, **slip = 0** ⇒ **trần trên** | maker 0,02% + taker 0,05% | 0 | Σrate `(fill, E]` | tập-khớp |

- `raw_A1 = C[E]/p0 − 1`; `raw_B/C = C[E]/L − 1` (**tính từ GIÁ KHỚP**, không phải từ `p0`).
- **GATE**: A0 phải tái tạo số đã đăng của `RESULT_REVERSAL_BOUNCE` (ALL +0,003%, DEV −0,080% trên cửa sổ DEV **cũ**
  2022-01..2024-06; sai số cho phép ≤ 0,002pp). Không khớp ⇒ **DỪNG, không đọc số tiếp**.

## 2.4 ADVERSE SELECTION (BẮT BUỘC, không được bỏ)

1. Mọi chỉ tiêu của B/C tính **từ giá khớp `L`** (§2.3), **không** từ `p0`.
2. Báo **so sánh riêng 2 nhóm** trên cùng một thước: `mean raw_signal := C[E]/p0 − 1` của **nhóm KHỚP** vs
   **nhóm FAIL** ⇒ `AS1 = mean(raw_signal | khớp) − mean(raw_signal | fail)`. `AS1 < 0` = **adverse selection**
   (lệnh khớp là lệnh xấu hơn). Báo kèm `AS2 = mean(raw_fill | khớp) − mean(raw_signal | khớp)` (thành phần cơ học của δ).
3. Báo **tỉ lệ khớp** theo `δ` (số + % trên fire dùng được) và **thời gian-khớp** (phân bố `m`), cùng phân bố
   `|raw_signal|` 2 nhóm. Nếu vì lý do kỹ thuật mà **không tách được** nhóm fail ⇒ **ghi rõ** "không tách được".

## 2.5 Chỉ số + thống kê (KHOÁ; dùng nguyên harness của repo)

`N`, **tỉ lệ khớp**, `mean net`, `win%`, `median`, **meanP**, CI **block-72h** (`entry_ts//(72·60)`) theo **cả
×1,21 (legacy)** và **×1,0**, `p(mean>0)`, **null test** (block sign-flip 72h, `seed 20260905`, `NREP=2000`),
**MDE80** (ghi 2 cách: nửa-độ-rộng CI ×1,0 và `2,8 × sd(null)`), `N_blk`, **dấu theo từng năm** (nhất quán dấu).
Đơn vị: **%/lệnh**.

## 2.6 Cổng kết luận (KHOÁ, áp cho cả C1 và C2)

"**LẬT ĐƯỢC**" chỉ khi **đồng thời**: (a) `mean net(B) > 0` trên **DEV**; (b) CI72h×1,21 **ngoài 0** (cận dưới > 0);
(c) `|net| ≥ MDE80`; (d) **≥ 60% số năm** cùng dấu dương (và 2025 không âm); (e) `win%` không sụp so với A1.
Thiếu bất kỳ điều kiện ⇒ **KHÔNG LẬT ĐƯỢC**.
**Dù đạt cả 5**: kết quả vẫn chỉ là **POST-HOC / ỨNG VIÊN** (vì đổi mô hình chi phí sau khi đã biết gross/net cũ)
⇒ **không đề xuất áp dụng**, chỉ ghi "cần forward".

## 2.7 Nếu KHÔNG lật được thì phải trả lời cái gì

- **Chênh lệch B − A1** (cùng tập-khớp) = phần **thực sự** đến từ fee/entry; so với **MDE** ⇒ kết luận
  "nhỏ hơn ngưỡng phát hiện", **không** kết luận "không có tác dụng".
- **C − B** = phần do **slip exit** ⇒ tách "lợi ích cơ học" khỏi "lợi ích biến động".
- **AS1** phải được nêu như **cơ chế** giải thích (nếu B/C vẫn ≤ 0).

---

## 3. Sản phẩm (KHOÁ)

| File | Nội dung |
|---|---|
| `docs/PREREG_LIMIT_ENTRY.md` | file này (chốt trước) |
| `docs/RESULT_FUNDING_SIGN.md` | Phần 1 — truy vết + đo lại 2 tầng + chốt quy ước + số đúng |
| `docs/RESULT_LIMIT_ENTRY.md` | Phần 2 — tỉ lệ khớp, 4 hàng chi phí, CI/null/MDE, adverse selection, kết luận |
| `research/analysis/funding_sign_reconcile.py` | script Phần 1 (thuần Python, chỉ đọc) |
| `research/analysis/limit_entry.py` | script Phần 2 (thuần Python, chỉ đọc) |
| `/home/ubuntu/claudedata/funding_sign/`, `/home/ubuntu/claudedata/limit_entry/` | trung gian (ngoài repo, resume được) — **dọn sau commit** |
