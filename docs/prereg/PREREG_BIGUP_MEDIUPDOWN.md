# PREREG_BIGUP_MEDIUPDOWN — đo lại BIG_UP / MEDIUM_UP / MEDIUM_DOWN (logic cũ ~1 năm) vs BIG_DOWN hiện tại

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** Commit file này phải có TRƯỚC commit
kết quả. Nếu thứ tự commit ngược → toàn bộ kết quả **VOID** (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2).

Phạm vi: **DEV only**. Headline = `2022-01-01 .. 2024-06-30` (khớp `PREREG_REVERSAL_BOUNCE.md` để
so táo-với-táo). Đối chiếu trung thực thêm 2021 và `2024-07-01 .. 2025-12-31`.
**KHÔNG chạm HOLDOUT 2026** (dữ liệu chặn ≤ `2025-12-31`).

Nhiệm vụ (owner): lấy lại tín hiệu **BIG_UP / MEDIUM_UP / MEDIUM_DOWN** code cách ~1 năm, xác
định logic vào lệnh khác gì BIG_DOWN hiện tại, đo lại (không chép kết luận cũ), rồi tìm cách áp
vào mô hình hiện tại.

Nguồn gốc code cũ: commit `157cf4da1b7778b5476ac5371c6467381c43b8ba` (2025-10-08), snapshot
`/home/ubuntu/trend_review/old_era/` (`tradecore/` + `trading/`); file còn thiếu đọc bằng
`git show <sha>:<path>` (read-only).

---

## 0. Tiên lượng ghi trước (không sửa sau khi thấy số)

1. **MEDIUM_DOWN**: nhiều khả năng **NO-GO** — cùng chiều & cùng đợt selloff với MOM15
   (`rateDown15MAvg`), tức đã correlated; `SURVEY_OLDCODE_SIGNALS.md` §4 xếp nó vào "LOẠI vì
   correlated MOM15" **nhưng kết luận đó CHƯA được đo lại** → phép đo này xác nhận hoặc phủ định.
2. **BIG_UP / MEDIUM_UP**: nhiều khả năng **NO-GO** — breadth-up momentum, prior yếu cho
   long-buy-dip; và chọn coin theo "15M drop sâu nhất" trong lúc thị trường đang XANH là selection
   nghịch pha (mua coin yếu nhất trong ngày mạnh).
3. Kỳ vọng phí (0.10% + slip) ăn phần lớn edge thô, như đã thấy ở reversal-bounce.
4. Kỳ vọng overlap-in-time với MOM15: BIG_UP/MEDIUM_UP **thấp** (khác chiều); MEDIUM_DOWN **cao**.

Đây là tiên lượng, KHÔNG phải kết luận. NULL thì báo NULL.

---

## 1. Logic cũ — xác định CHÍNH XÁC (file:line)

### 1.1 Trigger — `tradecore/MarketBigChangeDetector.java:288-322` (`getMarketStatus1M`)

Tham số vào (tất cả scalar cross-sectional, tính từ nến 1M đã đóng):
`rateDownAvg`, `rateUpAvg` (avg close/open của ~100 coin giảm/tăng mạnh nhất), `btcRateChange`
(close/open BTC), `rateDown15MAvg` (avg `close/max(15×1M) − 1` của ~100 coin sụt sâu nhất).

Thứ tự if-else **loại trừ nhau** (một phút chỉ một nhãn):

| Level | Điều kiện (nguyên văn code) | Dòng |
|---|---|---|
| `BIG_UP` | `rateUpAvg > 0.025` | :290-291 |
| `BIG_DOWN` | `rateDownAvg < -0.032 && btcRateChange < -0.01` | :293-296 |
| `MEDIUM_UP` | `rateUpAvg > 0.015` | :299-300 |
| `MEDIUM_DOWN` | `rateDownAvg < -0.030 \|\| (rateDownAvg < -0.014 && rateDown15MAvg < -0.07)` | :302-307 |
| `SMALL_UP` | `rateUpAvg > 0.008 && rateDownAvg > 0` | :309 |
| `SMALL_DOWN` | `rateDownAvg < -0.006 && rateUpAvg < 0 && rateDown15MAvg < -0.025` | :312 |
| `MEDIUM_DOWN_15M` | `rateDown15MAvg < -0.045` | :316-317 |
| `SMALL_DOWN_15M` | `rateDown15MAvg < -0.028` | :318-319 |

Biến thể `_15M`: chỉ có `MEDIUM_DOWN_15M` và `SMALL_DOWN_15M` (không có `BIG_UP_15M` /
`MEDIUM_UP_15M` / `BIG_DOWN_15M`). `MEDIUM_DOWN_15M` = `rateDown15MAvg < -0.045`.

Các scalar tính ở `trading/DetectEntrySignal2TradeNormal.java:167-172`:
`rateDownAvg = calRateChangeAvg(rateDown2Symbols,100)`;
`rateUpAvg = -calRateChangeAvg(rateUp2Symbols,100)`;
`rateDown15MAvg = calRateChangeAvg(rateDown15M2Symbols,100)`. `calRateChangeAvg`
(`MarketBigChangeDetector.java:268-286`) lấy trung bình của **100 phần tử đầu** khi duyệt
`TreeMap` **tăng dần** → với `rateDown2Symbols` (key = close/open−1, âm) = 100 coin rớt sâu nhất;
với `rateUp2Symbols` (key = −rateChange) = 100 coin tăng mạnh nhất. `k = min(100, ⌊n·4/5⌋)`.

### 1.2 Chọn symbol — `DetectEntrySignal2TradeNormal.java:191-206`

- `numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL` = **2** (`config.properties:7`).
- Chỉ halve (`/2`) cho `SMALL_DOWN`, `SMALL_UP`, `MEDIUM_DOWN_15M`, `SMALL_DOWN_15M`.
  ⇒ **BIG_UP / MEDIUM_UP / MEDIUM_DOWN giữ nguyên 2 coin/lần.**
- Chọn bằng `MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols, 2, symbol2FinalTicker,
  symbolLocked)` (`:246-266`): duyệt `rateDown15M2Symbols` **tăng dần** (rớt 15M sâu nhất trước),
  bỏ coin đang có vị thế (`symbolLocked = BudgetManager.symbol2Pos.keySet()`), lấy 2 coin đầu.
  ⇒ **MỌI level dùng CÙNG một cách chọn: 2 coin rớt sâu nhất so đỉnh 15 phút.** Không phân biệt
  level up hay down.
- Cộng thêm `addSpecialSymbol` (`:394-406`): các `specialSymbol`/`stableSymbol` (BTC, ETH…) có
  `close/open < -0.013` trong phút đó → cũng mua.
- Lọc thêm `TradeUtils.shouldAvoidEntry` (`TradeUtils.java:65-…`): bỏ nếu symbol gần đây biến động
  yếu/volume thấp.

### 1.3 Sizing — `TradeUtils.managerBudget` (`TradeUtils.java:119-…`)

Gốc `budget` = `BudgetManager.getBudget()`; `marginRatio = marginRunning/balanceBasic`.
`isNormalLevel = !(DCA_LEVEL1/2) && !level chứa chuỗi "big"`.
- Nhánh margin-ratio (`/2` tại 0.2; `/3` tại 0.25; `/2` tại 0.35; `/4` tại 0.5; `null` tại ≥0.6)
  **chỉ áp cho `isNormalLevel`**.
- Switch theo level: `MEDIUM_DOWN` / `MEDIUM_UP` / `DCA_LEVEL1` → `budget /= 2` (`:153-156`).
- `BIG_UP` và `BIG_DOWN` **không có case** ⇒ không chia.
- Sau đó `×1.2` nếu `isTrendBuyETH`, `×0.8` nếu không.

⇒ **BIG_UP = full budget; MEDIUM_UP = MEDIUM_DOWN = ½ budget**; cả hai medium đều là "normal level".
Không có gate trend chặn BIG_UP/MEDIUM_UP/MEDIUM_DOWN ở bước này. (`managerBudget` chỉ trả `null`
cho `SMALL_UP`/`SMALL_DOWN_15M` khi không có trend BTC buy, và khi `marginRatio ≥ 0.6`.)

### 1.4 Gate — KHÔNG có ở era này

`createOrderBuyRequest` (`:409-448`) **không** gọi `AIRejectFilter`/gate 15M: chỉ
`managerBudget` → `calQuantity` → push Redis. ⇒ Ở era `157cf4d`, cả 4 level **không qua gate nào
ngoài `shouldAvoidEntry` + `managerBudget`**.

### 1.5 Exit

`createOrderBuyRequest` đặt `orderTrade.priceTP = priceMax15M` (đỉnh 15 phút của symbol) — TP, không
phải time-stop. Không có nhánh exit riêng theo level trong code cũ. DCA (nạp thêm vị thế lỗ) có
config riêng theo level — `DcaUtils.getDcaConfig` (`DcaUtils.java:47-63`): `BIG_UP`/`MEDIUM_DOWN` →
`(15, -0.08, false)`; `MEDIUM_UP` → `(15, -0.15, false)`; `BIG_DOWN` → `(8, -0.05, true)`. DCA không
phải luật exit.

### 1.6 HEAD hiện tại

`tradecore/MarketBigChangeDetector.getMarketStatus1M` (HEAD) **chỉ còn một nhánh**:
`if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) return BIG_DOWN;` (`MS_DOWN_BIG_AVG = -0.03157f`,
`Configs.java:394`). **BIG_UP / MEDIUM_UP / MEDIUM_DOWN / SMALL_*** / `*_15M` đã bị XOÁ.**

Khác biệt bản chất (không chỉ ngưỡng):

| | BIG_UP (cũ) | MEDIUM_UP (cũ) | MEDIUM_DOWN (cũ) | **BIG_DOWN hiện tại** |
|---|---|---|---|---|
| trigger | `rateUpAvg>0.025` | `rateUpAvg>0.015` | `rateDownAvg<-0.030` ∨ (`<-0.014` ∧ `rateDown15MAvg<-0.07`) | `rateDownAvg < -0.03157` (không cần BTC) |
| điều kiện BTC | không | không | không | cũ có `btcRateChange<-0.01`, **HEAD bỏ** |
| chọn symbol | top-2 rớt 15M sâu nhất | như BIG_UP | như BIG_UP | `getTopSymbolArray` (HEAD) = xếp theo **pNoPump tăng** (predict) — nếu `BD_SEL_MODE=off` (default) ; hoặc `BdSelection` drop/mix |
| số coin | 2 | 2 | 2 | 2 |
| sizing | full (≤1.2×) | ½ (≤1.2×) | ½ (≤1.2×) | full + BdSizeAdapt/tier/vol/pacing (mặc định off) |
| gate 15M | không | không | không | **KHÔNG** (nhánh `if (!levelChange.equals(BIG_DOWN))` mới qua `EntryGate`) |
| exit | chung (TP priceMax15M) | chung | chung | chung |
| DCA config | (15,−0.08) | (15,−0.15) | (15,−0.08) | (8,−0.05,isAll=true) |
| cap phụ | — | — | — | `ConcCapLiveGuard` (trần leg BIG_DOWN/60′), `HoldoutSeal` |

Khác bản chất rõ nhất: (a) HEAD **bỏ neo BTC** khỏi BIG_DOWN; (b) đổi **tiêu chí chọn coin** khỏi
"rớt 15M sâu nhất"; (c) **bỏ toàn bộ họ level**, kể cả trigger up-momentum.

---

## 2. Chuỗi tín hiệu đo lại — sinh causal, LEAK-FREE, thuần Python

### 2.1 Nguồn dữ liệu

`raw/<sym>.f32` — 627 USDT-perp, 1 nến 1M/dòng, layout `int32 epoch_minute, float32 O/H/L/C/V`
(UTC), dải `2021-01-01 .. 2025-12-31`. Dẫn xuất của Aerospike set `kline_1m_opt`
(127.0.0.1:3222) — **cùng nguồn BD/MOM15** (SURVEY §1; `PREREG_REVERSAL_BOUNCE.md` §3).
Chỉ dùng nến **đã đóng** ⇒ causal. Không ghi Aerospike trong phép đo này (trừ funding, chỉ ĐỌC).

Kiểm causal: mọi scalar của phút `m` chỉ dùng nến `≤ m`; scan thời gian tăng dần; không nhìn tương lai.

### 2.2 Scalar cross-sectional (tái tạo đúng `calRateChangeAvg` k=100, ⌊n·4/5⌋)

Trên lưới 1M, với mọi symbol có nến đã đóng tại `m`:
- `rateChange_i = close_i(m)/open_i(m) − 1`
- `rateDownAvg(m)` = mean 100 giá trị **nhỏ nhất** của `rateChange_i`
- `rateUpAvg(m)`   = mean 100 giá trị **lớn nhất**
- `max15_i(m) = max(high_i(m−14..m))`; `drop15_i = close_i/max15_i − 1`
- `rateDown15MAvg(m)` = mean 100 giá trị **nhỏ nhất** của `drop15_i`
- lọc `diedSymbol`/delist-outlier như code cũ (`calMarketData:160`): bỏ symbol nếu
  `btcRateChange(m) > -0.004 && rateChange_i < -0.15`.
- `btcRateChange(m)` = `close/open − 1` của BTCUSDT (1M, nến đã đóng).
- Yêu cầu n tối thiểu: `n ≥ 50` symbol/phút, không thì không gán level.

### 2.3 Nhãn level (tái tạo nguyên thứ tự if-else loại trừ nhau §1.1)

Sinh **nhãn đơn** mỗi phút theo đúng thứ tự code cũ (BIG_UP → BIG_DOWN → MEDIUM_UP →
MEDIUM_DOWN → SMALL_UP → SMALL_DOWN → MEDIUM_DOWN_15M → SMALL_DOWN_15M → `null`).

**Tập quyết định k = 3**: `{BIG_UP, MEDIUM_UP, MEDIUM_DOWN}`. Thêm **1 dòng tham chiếu
BIG_DOWN-cũ** (`rateDownAvg < -0.032 && btcRateChange < -0.01`) để so với BIG_DOWN hiện tại — dòng
này **descriptive**, không nằm trong tập GO/NO-GO của 3 level được yêu cầu (ghi rõ để tránh
multiple-comparison len lỏi). `MEDIUM_DOWN_15M`/`SMALL_*` được sinh nhãn (để loại trừ đúng) nhưng
**không đo** (giữ k=3, theo chỉ dẫn "tối đa k=3").

### 2.4 Fire + chọn symbol + lock (đúng cơ chế live cũ)

- Mỗi phút `m` có nhãn level: chọn tối đa **2 symbol rớt 15M sâu nhất** (`drop15` tăng dần), bỏ
  symbol đang **lock**.
- **Lock**: sau khi fire (m, s), `s` bị khoá tới `m + HOLD` — mô phỏng `symbolLocked =
  symbol2Pos.keySet()` của code cũ (coin đang có vị thế không được chọn lại). Đây là abstraction
  ghi trước: lock = HOLD cố định (live thực tế unlock khi vị thế đóng theo TP/SL — không tái tạo
  được trong harness 0-sim; lệch này được ghi nhận, không sửa sau khi thấy số).
- Event = `(m, s)`. `HOLD = 1440` phút (24h) — cùng HOLD với FORCED_SELLER/reversal-bounce để
  so táo-với-táo. Không tune HOLD.
- Universe = **toàn bộ 627 symbol** (gồm coin delist; không lọc survivorship).
- KHÔNG áp gate 15M/selector (đúng era `157cf4d` — §1.4); KHÔNG áp `managerBudget` (đo tín hiệu,
  không đo sizing).

### 2.5 Chi phí (giống FORCED_SELLER / reversal-bounce)

- taker fee `0.0005 × 2 = 0.10%` (mở+đóng).
- slippage `0.5 × (high(m) − low(m)) / entry`.
- funding: tổng funding rate trong `(m, exit]` (Aerospike `funding_data`, per-symbol, 8h cadence) —
  long trả funding dương.
- `net_ret = raw_ret − fee − slip − funding`; entry = `close(m)`, exit = `close(m+HOLD)` (causal).
- Censoring y hệt reversal-bounce: `m+HOLD` vượt cuối dải ⇒ loại (edge-censored); hết dữ liệu
  trước HOLD ⇒ exit nến cuối, gắn `short_delist`, GIỮ trong mẫu.

---

## 3. ĐIỀU KIỆN TIÊN QUYẾT — overlap-in-time & ICC với MOM15

**Định nghĩa MOM15 trong repo (ghi rõ cả hai dạng tìm được):**
1. Nhánh momentum 15m của mô hình hiện tại = cổng `tradecore/EntryGate` trên `predReturn15M`
   (prediction model) với `thrBase = Configs.MIN_MOMENTUM_15M = 0.02284f`; PASS ⇔ `!(pred15M < thr)`
   (`EntryGate.java`, dùng chung sim+live). `pred15M` là **output model** → **không tính được thuần
   Python**, và 2026 không dùng.
2. Dạng market-level tương đương đã được repo thiết lập: **MOM15 = `rateDown15MAvg < -0.028`**
   (`SMALL_DOWN_15M` = "bản live của MOM15") — `SURVEY_OLDCODE_SIGNALS.md` §1–§2,
   `PREREG_REVERSAL_BOUNCE.md` §4.

Phép đo này dùng **dạng (2) làm primary** (tính được causal từ chính `raw/*.f32`, cùng định nghĩa
`rateDown15MAvg` với trigger — nên overlap là "so cùng thước"), và **dạng (1) qua proxy** = ngày có
lệnh MOM15 thật trong `printDone.csv` run C2b DEV (`/home/ubuntu/java/devrun/C2b/storage/printDone.csv`).

Đo:
- **Tầng phút (primary)**: fire có MOM15 firing (`rateDown15MAvg < -0.028` tại mốc 15m-aligned gần
  nhất ≤ `m`) không → % fire / % quiet; edge tách 2 tập con.
- **Tầng ngày (secondary)**: % fire rơi vào ngày MOM15 có giao dịch; % fire trùng `(symbol, ngày)`
  với một lệnh MOM15.
- **ICC(net_ret)** theo ngày entry và theo episode 72h.

**Điều kiện tiên quyết**: nếu phần lớn fire trùng MOM15 (overlap cao) ⇒ **NO-GO dù edge dương**
(SURVEY §5). Nếu độc lập về timing nhưng phần độc lập **không có edge** ⇒ cũng **NO-GO**.

---

## 4. Phép đo thống kê (khoá trước khi chạy)

- Headline: `mean(net_ret)`, hit-rate = `P(net_ret > 0)` trên DEV (headline window §0).
- **CI**: block-bootstrap circular moving-block, **block = 72h**, **2000 rep**, **seed 20260905**;
  percentile 2.5/97.5 rồi **×1.21** (`CI_INFLATE_LEGACY`), báo kèm `p(mean>0)` và CI chưa inflate.
  (Ghi chú: `AUDIT_CI_INFLATE_STANDARDIZATION` nói 1 ứng viên đơn ⇒ `inflate(1)=1.0`; ×1.21 là
  legacy → báo CẢ HAI như reversal-bounce.)
- **Null test**: block sign-flip permutation (72h), 2000 rep, seed 20260905 → `p(null ≥ obs)`.
- Decay theo năm (2021..2025) phát hiện sign-flip.
- `%coin+` = tỉ lệ symbol có `mean(net_ret) > 0` (≥1 / ≥5 / ≥10 trade).
- Descriptive (không dùng để quyết định): tập con onset (phút đầu mỗi episode level liên tục).

---

## 5. GATE GO/NO-GO (mỗi level quyết riêng)

GO khi **ĐỒNG THỜI**:
1. `mean(net_ret) > 0` trên DEV và CI block-72h ×1.21 **loại 0** (`p(mean>0)` cao).
2. ICC theo episode **đủ thấp** (không vài episode quyết định toàn bộ).
3. **Overlap MOM15 thấp** + phần độc lập (MOM15-quiet) **có edge dương**.
4. Ổn định: không sign-flip theo năm, `%coin+ ≥ 50%`.

Không đạt bất kỳ điều nào → **NO-GO**, ghi rõ nguyên nhân. Không thêm biến thể, không đổi ngưỡng,
không nới HOLD sau khi thấy số (chống leak L2 / multiple-comparison). **k = 3** level.

## 6. Apply (chỉ nếu có level GO)

KHÔNG tự tích hợp vào code sản xuất. Chỉ **đề xuất**: level làm trigger entry / gate / sizing, kèm
(flag mới default OFF + parity gate + pre-reg riêng cho bước tích hợp + đo trên harness Java).
BIG_DOWN hiện tại đi nhánh không-gate và chọn coin theo predict — nếu một level GO thì phải nêu rõ
nó đi nhánh nào và có đụng BIG_DOWN không.

## 7. Ràng buộc tuân thủ

- KHÔNG `claude-run`/Claude Code. KHÔNG chạy Java trên Oracle. **Thuần Python** (đọc `raw/*.f32` +
  Aerospike funding chỉ-đọc). Không push. 2026 không đụng.
- Pre-reg commit TRƯỚC; sau khi chạy không sửa thiết kế.
